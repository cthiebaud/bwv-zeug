#!/usr/bin/env python3
"""
align_pitch_by_geometry_simplified.py

Musical Score Alignment Pipeline
================================

This script aligns MIDI note events with SVG noteheads from LilyPond-generated 
musical scores, creating a synchronized dataset for score animation. It handles
complex musical notation including ties, accidentals, and octave variations.

Input Files Required:
- MIDI timing and pitch data CSV
- SVG notehead positions and LilyPond snippets CSV
- Tie relationships between notes CSV

Output:
- Aligned notes with timing, pitch, and SVG references JSON

The alignment process ensures that visual noteheads in the SVG match their
corresponding MIDI events for precise animated score following.
"""

import pandas as pd
import json

def main():
    """Main function with project context support."""
    
    print("📁 Loading input data files...")
    
    try:
        # Try to use project context system
        from _scripts_utils import get_project_name
        
        project_name = get_project_name()
        midi_csv = f"{project_name}_note_events.csv" 
        svg_csv = f"{project_name}_note_heads.csv"
        ties_csv = f"{project_name}_ties.csv"
        output_json = f"exports/{project_name}_json_notes.json"
        
    except ImportError:
        # Fallback for standalone use
        print("⚠️  _scripts_utils not available - using default file names")
        midi_csv = "bwv1006_note_events.csv"
        svg_csv = "bwv1006_note_heads.csv" 
        ties_csv = "bwv1006_ties.csv"
        output_json = "exports/bwv1006_json_notes.json"
    
    # Load data files
    midi_df = pd.read_csv(midi_csv)
    svg_df = pd.read_csv(svg_csv) 
    ties_df = pd.read_csv(ties_csv)

    # =================================================================
    # STEP 1: CLEAN SVG HREF PATHS
    # =================================================================

    # Remove LilyPond editor artifacts from href paths to normalize references
    # Example: "textedit:///work/file.ly:10:5" -> "file.ly:10:5"
    print("🧹 Normalizing SVG href paths...")
    svg_df["href"] = (
        svg_df["href"]
        .str.replace("textedit://", "", regex=False)  # Remove protocol prefix
        .str.replace("/work/", "", regex=False)       # Remove workspace path
    )

    # =================================================================
    # STEP 2: HANDLE TIED NOTES
    # =================================================================

    # In musical notation, tied notes connect multiple noteheads but represent
    # a single sustained sound. We only want the primary (first) notehead for
    # alignment, so we filter out secondary tied noteheads.
    print("🎵 Filtering out secondary tied noteheads...")
    secondary_hrefs = set(ties_df["secondary"])
    original_count = len(svg_df)
    svg_df = svg_df[~svg_df["href"].isin(secondary_hrefs)].copy()
    filtered_count = len(svg_df)
    print(f"   Removed {original_count - filtered_count} secondary noteheads")

    # =================================================================
    # STEP 3: SORT DATASETS FOR ALIGNMENT
    # =================================================================

    # Sort MIDI events chronologically with tie-breaking rules:
    # 1. Primary: onset time (ascending)
    # 2. Secondary: channel (descending - higher channels first)  
    # 3. Tertiary: pitch (ascending)
    print("📊 Sorting datasets for geometric alignment...")
    midi_df = midi_df.sort_values(
        by=["on", "channel", "pitch"], 
        ascending=[True, False, True]
    ).reset_index(drop=True)

    # Sort SVG noteheads by visual position:
    # 1. Primary: x-coordinate (left to right)
    # 2. Secondary: y-coordinate (top to bottom, hence descending)
    svg_df = svg_df.sort_values(
        by=["x", "y"], 
        ascending=[True, False]
    ).reset_index(drop=True)

    # =================================================================
    # LILYPOND PITCH PARSING
    # =================================================================

    def parse_lilypond_note(note_str):
        """
        Convert LilyPond note notation to MIDI pitch value.
        
        LilyPond Notation System:
        ========================
        - Base notes: c, d, e, f, g, a, b (letter names)
        - Sharps: add 'is' (cis = C#, fis = F#)
        - Flats: add 'es' or 's' (bes = Bb, as = Ab) 
        - Double sharps: add 'isis' (cisis = C##)
        - Double flats: add 'eses' (ceses = Cbb)
        - Octaves up: add apostrophes (c' = C4, c'' = C5)
        - Octaves down: add commas (c, = C2, c,, = C1)
        
        Args:
            note_str (str): LilyPond notation (e.g., "cis'", "bes,,", "f")
            
        Returns:
            int: MIDI pitch number (0-127), or -1 if parsing failed
            
        Examples:
            "c" -> 36 (C3 in MIDI)
            "cis'" -> 49 (C#4)  
            "bes,," -> 22 (Bb1)
        """
        # Base MIDI values for middle octave (C3=36 to B3=47)
        # This octave choice aligns with typical LilyPond default octave
        base_notes = {
            # Natural notes
            'c': 36, 'd': 38, 'e': 40, 'f': 41, 'g': 43, 'a': 45, 'b': 47,
            
            # Single accidentals (sharps)
            'cis': 37, 'dis': 39, 'fis': 42, 'gis': 44, 'ais': 46,
            
            # Single accidentals (flats) - multiple spellings supported
            'des': 37, 'es': 39, 'ees': 39, 'ges': 42, 'aes': 44, 'as': 44, 'bes': 46,
            
            # Enharmonic edge cases (rare but valid)
            'eis': 41,  # E# = F
            'bis': 48,  # B# = C (next octave)
            'ces': 35,  # Cb = B (previous octave) 
            'fes': 40,  # Fb = E
            
            # Double accidentals (very rare in practice)
            'cisis': 38, 'disis': 40, 'eisis': 42, 'fisis': 43, 'gisis': 45,
            'aisis': 47, 'bisis': 49,
            'ceses': 34, 'deses': 36, 'eses': 38, 'feses': 39, 'geses': 41, 
            'aeses': 43, 'beses': 45
        }
        
        # Generate octave variations - lower octaves (commas)
        # Each comma drops the pitch by one octave (12 semitones)
        base_notes_copy = dict(base_notes)  # Avoid modifying during iteration
        for comma_count in range(1, 4):  # Support up to 3 octaves down
            for base_note, base_pitch in base_notes_copy.items():
                octave_note = base_note + (',' * comma_count)
                octave_pitch = base_pitch - (comma_count * 12)
                if octave_pitch >= 0:  # Stay within MIDI range
                    base_notes[octave_note] = octave_pitch
        
        # Generate octave variations - higher octaves (apostrophes)  
        # Each apostrophe raises the pitch by one octave (12 semitones)
        for apostrophe_count in range(1, 8):  # Support up to 7 octaves up
            for base_note, base_pitch in base_notes_copy.items():
                octave_note = base_note + ("'" * apostrophe_count)
                octave_pitch = base_pitch + (apostrophe_count * 12)
                if octave_pitch <= 127:  # Stay within MIDI range
                    base_notes[octave_note] = octave_pitch
        
        # Look up the note, returning -1 if not found
        cleaned_note = note_str.strip()
        return base_notes.get(cleaned_note, -1)

    # =================================================================
    # TIE GROUP PROCESSING
    # =================================================================

    def collect_full_tie_group(primary_href, ties_df):
        """
        Collect all noteheads connected by ties, starting from a primary notehead.
        
        Musical ties can form chains: Note A -> Note B -> Note C, where each
        arrow represents a tie. This function follows the entire chain to collect
        all connected noteheads for a single sustained musical event.
        
        Args:
            primary_href (str): Starting notehead reference
            ties_df (DataFrame): Tie relationships with 'primary' and 'secondary' columns
            
        Returns:
            list: All href references in the tie group, including the starting primary
            
        Example:
            If Note A ties to B, and B ties to C:
            collect_full_tie_group("A", ties_df) -> ["A", "B", "C"]
        """
        tie_group = [primary_href]  # Start with the primary notehead
        visited = set(tie_group)    # Track visited notes to prevent infinite loops
        processing_queue = [primary_href]  # Notes whose ties we still need to check

        # Breadth-first search through the tie network
        while processing_queue:
            current_href = processing_queue.pop(0)
            
            # Find all notes that this current note ties TO
            tied_secondaries = ties_df.loc[
                ties_df["primary"] == current_href, 
                "secondary"
            ].tolist()
            
            # Add newly discovered tied notes to our group
            for secondary_href in tied_secondaries:
                if secondary_href not in visited:
                    tie_group.append(secondary_href)
                    visited.add(secondary_href)
                    processing_queue.append(secondary_href)  # Check its ties too

        return tie_group

    # =================================================================
    # MAIN ALIGNMENT PROCESS
    # =================================================================

    print("🎯 Aligning MIDI events with SVG noteheads...")
    aligned_notes = []
    mismatch_count = 0

    # Process each MIDI-SVG pair in synchronized order
    for index, (midi_row, svg_row) in enumerate(zip(midi_df.itertuples(), svg_df.itertuples())):
        
        # Extract pitch information from both sources
        lilypond_pitch = parse_lilypond_note(svg_row.snippet)
        midi_pitch_class = midi_row.pitch % 12  # Reduce to pitch class (0-11)
        
        # Convert LilyPond pitch to pitch class for comparison
        if lilypond_pitch != -1:
            lilypond_pitch_class = lilypond_pitch % 12
        else:
            lilypond_pitch_class = -1  # Parsing failed
        
        # Verify pitch class alignment
        if lilypond_pitch_class != midi_pitch_class:
            print(f"⚠️  Pitch mismatch at position {index}:")
            print(f"    MIDI: pitch={midi_row.pitch} (class={midi_pitch_class})")
            print(f"    LilyPond: '{svg_row.snippet}' -> pitch={lilypond_pitch} (class={lilypond_pitch_class})")
            print(f"    SVG href: {svg_row.href}")
            mismatch_count += 1
            exit(1)  # Stop on first mismatch for debugging

        # Collect all noteheads connected by ties to this primary notehead
        complete_tie_group = collect_full_tie_group(svg_row.href, ties_df)

        # Create aligned note entry with all necessary information for animation
        aligned_note = {
            "hrefs": complete_tie_group,      # All SVG noteheads for this musical event
            "on": midi_row.on,                # Start time in seconds
            "off": midi_row.off,              # End time in seconds  
            "pitch": midi_row.pitch,          # MIDI pitch number
            "channel": midi_row.channel       # MIDI channel (for multi-voice music)
        }
        
        aligned_notes.append(aligned_note)

    # =================================================================
    # OUTPUT GENERATION
    # =================================================================

    print(f"💾 Writing aligned data to {output_json}...")

    with open(output_json, "w") as output_file:
        json.dump(aligned_notes, output_file, indent=2)

    # Summary statistics
    note_count = len(aligned_notes)
    total_hrefs = sum(len(note["hrefs"]) for note in aligned_notes)
    tie_count = total_hrefs - note_count

    print(f"✅ Successfully aligned {note_count} musical events")
    print(f"   📊 {total_hrefs} total SVG noteheads")
    print(f"   🔗 {tie_count} tied noteheads")
    print(f"   💾 Saved: {output_json}")

    if mismatch_count > 0:
        print(f"⚠️  {mismatch_count} pitch mismatches detected")

if __name__ == "__main__":
    main()


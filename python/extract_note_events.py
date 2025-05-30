#!/usr/bin/env python3
"""
midi_map.py

MIDI-to-Audio Timeline Synchronization
======================================

This module extracts note events from MIDI files and synchronizes their timing
with real audio recordings. It's specifically designed for cases where MIDI 
tempo doesn't match the actual performance tempo of an audio recording.

Key Features:
- Extracts note on/off events with precise timing
- Handles overlapping notes and note stacking
- Synchronizes MIDI timeline to match actual audio duration
- Converts MIDI pitches to LilyPond notation (with proper CSV quoting for comma-containing notation)
- Outputs timing data suitable for score animation
- Project-aware file naming with fallback to explicit arguments

Workflow:
1. Parse MIDI file to extract all note events
2. Calculate total MIDI duration in ticks
3. Compute tempo adjustment to match known audio duration
4. Convert all timing from MIDI ticks to real seconds
5. Convert MIDI pitches to LilyPond notation (properly quoted for CSV format)
6. Export synchronized timing data as CSV

Example CSV Output:
pitch,midi,channel,on,off
"c",60,1,0.0,1.5
"cis",61,1,1.5,3.0
"c,",48,1,3.0,4.5
"""

from mido import MidiFile, tick2second
import pandas as pd
import csv
from _scripts_utils import midi_pitch_to_lilypond

def extract_note_intervals(midi_path):
    """
    Extract note events from a MIDI file and synchronize timing with audio.
    
    This function processes a MIDI file to create a timeline of note events
    that matches the timing of a real audio performance. It handles the
    common scenario where MIDI files have arbitrary tempo but need to align
    with recorded audio of a specific duration.
    
    Args:
        midi_path (str): Path to the MIDI file to process
        
    Returns:
        pandas.DataFrame: Note events with columns:
            - pitch: LilyPond notation string (e.g., "cis'", "f,,") - quoted in CSV due to commas
            - midi: Original MIDI note number (0-127)
            - on: Start time in seconds (float)
            - off: End time in seconds (float) 
            - channel: MIDI channel number
            
    Algorithm Details:
    - Uses a note stack to handle overlapping notes of the same pitch
    - Calculates tempo dynamically to match known audio duration
    - Handles both note_on (velocity > 0) and note_off events
    - Treats note_on with velocity=0 as note_off (MIDI standard)
    - Converts MIDI pitches to LilyPond notation for score alignment
    """
    
    print(f"🎵 Loading MIDI file: {midi_path}")
    
    # =================================================================
    # STEP 1: LOAD MIDI FILE AND EXTRACT TIMING INFORMATION
    # =================================================================
    
    midi_file = MidiFile(midi_path)
    ticks_per_beat = midi_file.ticks_per_beat  # MIDI timing resolution
    
    print(f"   📊 MIDI resolution: {ticks_per_beat} ticks per beat")
    
    # Data structures for note tracking
    note_stack = {}      # Track overlapping notes: {pitch: [(start_tick, channel), ...]}
    note_events = []     # Final list of completed note events
    current_tick = 0     # Running total of elapsed MIDI ticks
    max_tick = 0         # Total duration of MIDI file in ticks
    
    print("🔍 Analyzing MIDI events...")
    
    # =================================================================
    # STEP 2: PROCESS ALL MIDI MESSAGES SEQUENTIALLY  
    # =================================================================
    
    for message in midi_file:
        # Advance timeline by message's delta time
        current_tick += message.time
        
        # Handle note start events
        if message.type == 'note_on' and message.velocity > 0:
            # Push note onto stack (handles multiple simultaneous notes of same pitch)
            if message.note not in note_stack:
                note_stack[message.note] = []
            note_stack[message.note].append((current_tick, message.channel))
            
        # Handle note end events (note_off OR note_on with velocity=0)
        elif message.type in ('note_off', 'note_on') and message.velocity == 0:
            # Pop matching note from stack (FIFO order for overlapping notes)
            if note_stack.get(message.note):
                start_tick, channel = note_stack[message.note].pop(0)
                
                # Create completed note event
                note_event = {
                    "midi": message.note,           # Original MIDI pitch number
                    "on_tick": start_tick,          # Temporary tick-based timing
                    "off_tick": current_tick,       # Will convert to seconds later
                    "channel": channel
                }
                note_events.append(note_event)
        
        # Track maximum tick value to determine total MIDI duration
        max_tick = max(max_tick, current_tick)
    
    print(f"   🎹 Extracted {len(note_events)} note events")
    print(f"   ⏱️  MIDI duration: {max_tick} ticks")
    
    # =================================================================
    # STEP 3: SYNCHRONIZE WITH AUDIO DURATION
    # =================================================================
    
    # *** CRITICAL SYNCHRONIZATION PARAMETER ***
    # This is the actual duration of the audio recording in seconds.
    # Adjust this value to match your specific audio file.
    audio_duration_seconds = 207.10
    
    print(f"🎧 Target audio duration: {audio_duration_seconds} seconds")
    
    # Calculate the tempo needed to stretch MIDI timeline to match audio
    # Formula: tempo = (audio_seconds * microseconds_per_second * ticks_per_beat) / max_ticks
    # Result is in microseconds per beat (MIDI tempo format)
    calculated_tempo = int(audio_duration_seconds * 1_000_000 * ticks_per_beat / max_tick)
    
    print(f"🎯 Calculated tempo: {calculated_tempo} μs per beat")
    print(f"   (≈ {60_000_000 / calculated_tempo:.1f} BPM)")
    
    # =================================================================
    # STEP 4: CONVERT TICK TIMING TO REAL SECONDS AND MIDI TO LILYPOND
    # =================================================================
    
    print("🕐 Converting timing from MIDI ticks to seconds...")
    print("🎼 Converting MIDI pitches to LilyPond notation...")
    
    for note_event in note_events:
        # Convert start and end times using the calculated tempo
        note_event["on"] = tick2second(note_event["on_tick"], ticks_per_beat, calculated_tempo)
        note_event["off"] = tick2second(note_event["off_tick"], ticks_per_beat, calculated_tempo)
        
        # Convert MIDI pitch to LilyPond notation
        note_event["pitch"] = midi_pitch_to_lilypond(note_event["midi"])
        
        # Remove temporary tick-based timing (no longer needed)
        del note_event["on_tick"]
        del note_event["off_tick"]
    
    # =================================================================
    # STEP 5: SORT AND ORGANIZE RESULTS
    # =================================================================
    
    # Convert to DataFrame for easier manipulation and export
    note_events_df = pd.DataFrame(note_events)
    
    # Reorder columns to match requested format: pitch, midi, channel, on, off
    note_events_df = note_events_df[["pitch", "midi", "channel", "on", "off"]]
    
    # Sort by musical priority:
    # 1. Start time (chronological order)
    # 2. Channel (higher channels first - often melody vs accompaniment)
    # 3. MIDI pitch (ascending - bass to treble within simultaneous events)
    note_events_df = note_events_df.sort_values(
        by=["on", "channel", "midi"], 
        ascending=[True, False, True]
    )
    
    print(f"✅ Synchronized {len(note_events_df)} notes to audio timeline")
    
    # Timing validation
    if len(note_events_df) > 0:
        actual_duration = note_events_df["off"].max()
        print(f"   📏 Actual final timing: {actual_duration:.2f} seconds")
        print(f"   🎯 Target duration: {audio_duration_seconds} seconds")
        print(f"   📊 Timing accuracy: {abs(actual_duration - audio_duration_seconds):.2f}s difference")
        
        # Show some examples of the pitch conversion
        print("   🎼 Sample pitch conversions:")
        sample_notes = note_events_df.head(5)
        for _, note in sample_notes.iterrows():
            print(f"      MIDI {note['midi']} -> '{note['pitch']}'")
    
    return note_events_df

# =============================================================================
# MAIN EXECUTION
# =============================================================================

def main():
    """Main function with project context support."""
    print("🚀 Starting MIDI-to-Audio synchronization pipeline")
    print("=" * 60)
    
    try:
        # Try to use project context system
        from _scripts_utils import get_io_files
        
        midi_file_path, output_file_path = get_io_files(
            "Extract MIDI note events and synchronize with audio timeline",
            "{project}_ly_one_line.midi",
            "{project}_note_events.csv"
        )
        
    except ImportError:
        # Fallback for standalone use
        print("⚠️  _scripts_utils not available - using default file names")
        midi_file_path = "bwv1006_ly_one_line.midi"
        output_file_path = "bwv1006_note_events.csv"
    
    # Process MIDI file
    try:
        synchronized_notes_df = extract_note_intervals(midi_file_path)
        
        # Export results
        print(f"\n💾 Saving synchronized data...")
        # Use QUOTE_NONNUMERIC to properly handle LilyPond notation with commas (e.g., "c,", "c,,")
        # This ensures pitch column values like "c," are quoted as "c," in the CSV
        synchronized_notes_df.to_csv(output_file_path, index=False, quoting=csv.QUOTE_NONNUMERIC)
        
        # Summary statistics
        total_notes = len(synchronized_notes_df)
        duration = synchronized_notes_df["off"].max() if total_notes > 0 else 0
        unique_pitches = synchronized_notes_df["pitch"].nunique() if total_notes > 0 else 0
        unique_midi_pitches = synchronized_notes_df["midi"].nunique() if total_notes > 0 else 0
        channels_used = synchronized_notes_df["channel"].nunique() if total_notes > 0 else 0
        
        print(f"✅ Export complete!")
        print(f"   📁 File: {output_file_path}")
        print(f"   🎵 Notes: {total_notes}")
        print(f"   ⏱️  Duration: {duration:.1f} seconds")
        print(f"   🎹 MIDI pitch range: {unique_midi_pitches} unique pitches")
        print(f"   🎼 LilyPond notation: {unique_pitches} unique representations")
        print(f"   🎚️  Channels: {channels_used}")
        
    except Exception as e:
        print(f"❌ Error processing MIDI file: {e}")
        raise

if __name__ == "__main__":
    main()
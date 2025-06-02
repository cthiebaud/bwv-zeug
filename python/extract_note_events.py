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
import argparse
import sys
import os
from _scripts_utils import midi_pitch_to_lilypond, get_project_name, get_project_config

def extract_note_intervals(midi_path, audio_duration_seconds, total_bars):
    """
    Extract note events from a MIDI file and synchronize timing with audio.
    
    This function processes a MIDI file to create a timeline of note events
    that matches the timing of a real audio performance. It handles the
    common scenario where MIDI files have arbitrary tempo but need to align
    with recorded audio of a specific duration.
    
    Args:
        midi_path (str): Path to the MIDI file to process
        audio_duration_seconds (float): Duration of the target audio recording in seconds
        total_bars (int): Total number of bars in the musical structure
        
    Returns:
        pandas.DataFrame: Note events with columns:
            - pitch: LilyPond notation string (e.g., "cis'", "f,,") - quoted in CSV due to commas
            - midi: Original MIDI note number (0-127)
            - on: Start time in seconds (float)
            - off: End time in seconds (float) 
            - channel: MIDI channel number
            
    Algorithm Details:
    - Uses a note stack to handle overlapping notes of the same pitch
    - Uses linear mapping to distribute notes across correct duration (ignores MIDI tempo)
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
    # STEP 3: SYNCHRONIZE WITH AUDIO DURATION USING LINEAR MAPPING
    # =================================================================
    
    print(f"🎧 Target audio duration: {audio_duration_seconds} seconds")
    print(f"🎼 Target bars: {total_bars} bars")
    print(f"📊 Using linear mapping (ignoring MIDI tempo - may be corrupted)")
    
    # Instead of using MIDI tempo (which may be wrong), use linear mapping
    # This distributes all note events evenly across the correct duration
    time_per_bar = audio_duration_seconds / total_bars
    
    print(f"⏱️ Time per bar: {time_per_bar:.3f} seconds")
    print(f"💡 Linear mapping: tick position → time position")
    
    # =================================================================
    # STEP 4: CONVERT TICK TIMING TO REAL SECONDS USING LINEAR MAPPING
    # =================================================================
    
    print("🕐 Converting timing using linear mapping...")
    print("🎼 Converting MIDI pitches to LilyPond notation...")
    
    for note_event in note_events:
        # Use linear mapping: (tick_position / max_tick) * total_duration
        # This ignores MIDI tempo and distributes events evenly
        note_event["on"] = (note_event["on_tick"] / max_tick) * audio_duration_seconds
        note_event["off"] = (note_event["off_tick"] / max_tick) * audio_duration_seconds
        
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

def setup_argument_parser():
    """Setup command line argument parser."""
    parser = argparse.ArgumentParser(
        description="Extract MIDI note events and synchronize with audio timeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract_note_events.py -i music.midi -o note_events.csv
  python extract_note_events.py --input bwv1006.midi --output bwv1006_notes.csv
        """
    )
    
    parser.add_argument('-i', '--input', 
                       required=True,
                       help='Input MIDI file path (required)')
    
    parser.add_argument('-o', '--output',
                       required=True, 
                       help='Output CSV file path for note events (required)')
    
    return parser.parse_args()

def main():
    """Main function with command line argument support."""
    print("🚀 Starting MIDI-to-Audio synchronization pipeline")
    print("=" * 60)
    
    # Parse arguments
    args = setup_argument_parser()
    
    midi_file_path = args.input
    output_file_path = args.output
    
    # Load audio duration and bar count from project configuration
    config = get_project_config(get_project_name())
    audio_duration_seconds = config.get('musicalStructure', {}).get('totalDurationSeconds')
    total_bars = config.get('musicalStructure', {}).get('totalBars')
    
    if audio_duration_seconds is None:
        print(f"❌ Error: musicalStructure.totalDurationSeconds not found in project configuration")
        print(f"   Make sure the project config file exists in exports/ directory with the correct structure")
        sys.exit(1)
        
    if total_bars is None:
        print(f"❌ Error: musicalStructure.totalBars not found in project configuration")
        print(f"   Make sure the project config file exists in exports/ directory with the correct structure")
        sys.exit(1)
    
    print(f"📄 Input MIDI: {midi_file_path}")
    print(f"📊 Output CSV: {output_file_path}")
    print(f"⏱️ Target duration: {audio_duration_seconds} seconds (from config)")
    print(f"🎼 Total bars: {total_bars} bars (from config)")
    print()
    
    # Validate input file exists
    if not os.path.exists(midi_file_path):
        print(f"❌ Error: Input MIDI file not found: {midi_file_path}")
        sys.exit(1)
    
    # Validate duration is positive
    if audio_duration_seconds <= 0:
        print(f"❌ Error: Duration must be positive, got: {audio_duration_seconds}")
        sys.exit(1)
    
    # Process MIDI file
    try:
        synchronized_notes_df = extract_note_intervals(midi_file_path, audio_duration_seconds, total_bars)
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
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
        
        print()
        print("🎉 MIDI note extraction completed successfully!")
        
    except Exception as e:
        print(f"❌ Error processing MIDI file: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
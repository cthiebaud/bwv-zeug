#!/usr/bin/env python3
"""
BWV Processing Tasks - Complete build system for Bach scores

Usage:
  invoke build_pdf
  invoke build_svg
  invoke status
"""

from invoke import task
from pathlib import Path
from tasks_utils import *

# Import all generated tasks from the auto-generated file
try:
    from tasks_generated import *
    print("✅ Loaded generated tasks from tasks_generated.py")
except ImportError as e:
    print("⚠️  Warning: Could not import tasks_generated.py")
    print("   Generate it with: python tasks_mermaid_utils.py tasks.mmd --generate-tasks")
    print(f"   Error: {e}")

# =============================================================================
# MANUAL/CUSTOM TASKS (not in the Mermaid diagram)
# =============================================================================

@task
def status(c):
    """Show build status of all files."""
    project_name = detect_project_name()
    
    files = [
        (f"{project_name}.pdf", "PDF Score"),
        (f"{project_name}.svg", "Main SVG"),
        (f"{project_name}_ly_one_line.svg", "One-line SVG"),
        (f"{project_name}_ly_one_line.midi", "MIDI Data"),
        (f"exports/{project_name}_optimized.svg", "Final SVG"),
        (f"exports/{project_name}_json_notes.json", "Animation Data"),
    ]
    
    print_build_status(files)

@task
def clean(c):
    """Clean all generated files."""
    project_name = detect_project_name()
    
    remove_outputs(
        f"{project_name}.pdf",
        f"{project_name}.svg", 
        f"{project_name}_ly_one_line.svg",
        f"{project_name}_ly_one_line.midi",
        f"{project_name}_no_hrefs_in_tabs.svg",
        f"{project_name}_no_hrefs_in_tabs_swellable.svg",
        f"{project_name}_note_heads.csv",
        f"{project_name}_note_events.csv",
        f"exports/{project_name}_optimized.svg",
        f"exports/{project_name}_json_notes.json",
        ".build_cache.json"
    )

@task
def regenerate_tasks(c):
    """Regenerate tasks_generated.py from tasks.mmd."""
    print("🔄 Regenerating tasks from tasks.mmd...")
    c.run("python tasks_mermaid_utils.py tasks.mmd --generate-tasks")
    print("✅ Regenerated tasks_generated.py")
    print("   Restart invoke or reimport to use updated tasks")

@task
def full_build(c):
    """Complete build pipeline - all tasks in dependency order."""
    print("🚀 Starting full build pipeline...")
    
    # The generated tasks will handle dependencies automatically
    # Just run the final export task and it will trigger the full chain
    # Note: Use underscores for function names, not hyphens
    try:
        # Try to run align_data which should be the final task
        align_data(c)
    except NameError:
        print("⚠️  Task 'align_data' not found in generated tasks")
        print("   Available tasks should include the final pipeline task")
        print("   Check tasks_generated.py or run: invoke --list")
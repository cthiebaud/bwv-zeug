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
from tasks_mermaid_utils import get_all_target_files, get_status_file_info, get_final_tasks

# Import all generated tasks from the auto-generated file
try:
    from tasks_generated import *
    print("✅ Loaded generated tasks from tasks_generated.py")
except ImportError as e:
    print("⚠️  Warning: Could not import tasks_generated.py")
    print("   Generate it with: python tasks_mermaid_utils.py tasks.mmd --generate-tasks")
    print(f"   Error: {e}")

# Cache project name
PROJECT_NAME = detect_project_name()

# =============================================================================
# MANUAL/CUSTOM TASKS (not in the Mermaid diagram)
# =============================================================================

#!/usr/bin/env python3
"""
BWV Processing Tasks - Main task file

This file imports auto-generated tasks and provides meta-tasks.
"""

@task
def status(c):
    """Show build status of all files."""
    print(f"🎼 Detected project: {PROJECT_NAME}")
    
    # Get file information from mermaid diagram
    mermaid_path = Path(__file__).parent / 'tasks.mmd'  # tasks.mmd is in same dir as tasks.py
    status_files = get_status_file_info(str(mermaid_path))
    
    if not status_files:
        print("❌ Could not read file information from tasks.mmd")
        return
    
    # Replace PROJECT_NAME placeholder and get file info
    file_infos = []
    for category, description, filename_template in status_files:
        filename = filename_template.replace('{PROJECT_NAME}', PROJECT_NAME)
        file_infos.append(get_file_info(filename, description))
    
    # Sort by timestamp (missing files first, then by modification time)
    file_infos.sort(key=lambda x: x[0])
    
    print("📊 Build Status:")
    for mtime, name, filename, size, exists in file_infos:
        if exists:
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   ✅ {name:<18}: {filename:<75} ({size:>10,} bytes, {mtime_str})")
        else:
            print(f"   ❌ {name:<18}: {filename:<75} (missing)")

@task  
def clean(c):
    """Delete all generated output files."""
    print(f"🎼 Detected project: {PROJECT_NAME}")
    
    # Get target files from mermaid diagram
    # Get target files from mermaid diagram  
    mermaid_path = Path(__file__).parent / 'tasks.mmd'
    target_templates = get_all_target_files(str(mermaid_path))

    if not target_templates:
        print("❌ Could not read target files from tasks.mmd")
        return
    
    # Replace PROJECT_NAME placeholder
    targets = []
    for template in target_templates:
        filename = template.replace('{PROJECT_NAME}', PROJECT_NAME)
        targets.append(filename)
    
    # Delete files
    deleted = []
    for target in targets:
        path = Path(target)
        if path.exists():
            path.unlink()
            deleted.append(path.name)
    
    print("🗑️ Deleted:", end="")
    if deleted:
        print()
        for d in deleted:
            print(f"   └── {d}")
    else:
        print(" ∅")
    
    # Also clean build cache
    cache_file = Path('.build_cache.json')
    if cache_file.exists():
        cache_file.unlink()
        print("🗑️ Deleted build cache")

@task
def info(c):
    """Show information about the build system."""
    print("🚀 BWV Build System")
    print("=" * 50)
    print(f"🎼 Project: {PROJECT_NAME}")
    print(f"📄 Pipeline: tasks.mmd")
    print(f"🤖 Generated: tasks_generated.py")
    print(f"📋 Available tasks:")
    print("   📊 status  - Show file status")
    print("   🗑️ clean   - Delete outputs") 
    print("   ℹ️  info    - This information")
    print("   🔧 Pipeline tasks from tasks.mmd:")
    
    # Show generated tasks
    from tasks_mermaid_utils import get_nodes_by_type, get_all_file_nodes
    file_info = get_all_file_nodes('tasks.mmd')
    
    # This is a bit hacky - we'd need to parse the mermaid again to get task names
    # For now, just show a few key ones
    key_tasks = ['build_pdf', 'build_svg', 'extract_noteheads', 'align_data']
    for task_name in key_tasks:
        print(f"      • {task_name}")


@task
def regenerate_tasks(c):
    """Regenerate tasks_generated.py from tasks.mmd."""
    print("🔄 Regenerating tasks from tasks.mmd...")
    c.run("python tasks_mermaid_utils.py tasks.mmd --generate-tasks")
    print("✅ Regenerated tasks_generated.py")
    print("   Restart invoke or reimport to use updated tasks")

@task
def all(c, force=False):
    """Build all final outputs by running the complete pipeline."""
    print(f"🚀 Building all outputs for {PROJECT_NAME}")
    
    # Get final tasks from mermaid diagram
    mermaid_path = Path(__file__).parent / 'tasks.mmd'
    final_task_names = get_final_tasks(str(mermaid_path))
    
    if not final_task_names:
        print("❌ Could not determine final tasks from pipeline")
        return
    
    print(f"📋 Running final tasks: {', '.join(final_task_names)}")
    
    # Import the task functions dynamically
    import tasks_generated
    
    for task_name in final_task_names:
        print(f"\n🔄 Running {task_name}...")
        try:
            # Get the function from the module
            task_func = getattr(tasks_generated, task_name)
            task_func(c, force=force)
            print(f"✅ {task_name} completed")
        except AttributeError:
            print(f"❌ Task function {task_name} not found in tasks_generated")
            return
        except Exception as e:
            print(f"❌ {task_name} failed: {e}")
            return
    
    print("\n🎉 All pipeline outputs built successfully!")
    print("📊 Run 'invoke status' to see results")
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
    print("   • status  - Show file status")
    print("   • clean   - Delete outputs") 
    print("   • info    - This information")
    print("   🔧 Pipeline tasks from tasks.mmd:")
    
    # Get task names from mermaid file
    from tasks_mermaid_utils import get_all_file_nodes, parse_and_display_mermaid
    from pathlib import Path
    from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
    from MermaidPipelineLexer import MermaidPipelineLexer
    from MermaidPipelineParser import MermaidPipelineParser
    from tasks_mermaid_utils import MermaidDisplayListener, get_nodes_by_type
    
    try:
        mermaid_path = Path(__file__).parent / 'tasks.mmd'
        if mermaid_path.exists():
            content = mermaid_path.read_text()
            input_stream = InputStream(content)
            lexer = MermaidPipelineLexer(input_stream)
            lexer.removeErrorListeners()
            
            stream = CommonTokenStream(lexer)
            parser = MermaidPipelineParser(stream)
            parser.removeErrorListeners()
            
            tree = parser.diagram()
            
            listener = MermaidDisplayListener()
            walker = ParseTreeWalker()
            walker.walk(listener, tree)
            
            # Get all task nodes and display them
            task_nodes = get_nodes_by_type(listener.nodes, 'T')
            for task_node in task_nodes:
                task_name = task_node['content']
                description = task_node.get('description', '').strip()
                if description:
                    print(f"      • {task_name} - {description}")
                else:
                    print(f"      • {task_name}")
        else:
            print("      • tasks.mmd not found")
            
    except Exception as e:
        print(f"      • Error reading tasks from mermaid: {e}")
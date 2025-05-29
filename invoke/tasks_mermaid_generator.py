#!/usr/bin/env python3
"""
Tasks Mermaid Generator - Focused on task generation from mermaid files
"""

import argparse
import sys
from pathlib import Path
from antlr4 import *

# Import generated ANTLR classes
try:
    from MermaidPipelineLexer import MermaidPipelineLexer
    from MermaidPipelineParser import MermaidPipelineParser
    from MermaidPipelineParserListener import MermaidPipelineParserListener
except ImportError as e:
    print(f"❌ Error importing ANTLR classes: {e}")
    sys.exit(1)

# Import the existing listener from tasks_mermaid_utils
try:
    from tasks_mermaid_utils import MermaidDisplayListener
except ImportError as e:
    print(f"❌ Error importing MermaidDisplayListener: {e}")
    print("   Make sure tasks_mermaid_utils.py is in the same directory")
    sys.exit(1)

# =============================================================================
# TASK GENERATION FUNCTIONS
# =============================================================================

def get_node_by_id(nodes, node_id):
    """Get node by its ID."""
    return next((n for n in nodes if n['id'] == node_id), None)

def get_nodes_by_type(nodes, node_type):
    """Get all nodes of a specific type."""
    return [n for n in nodes if n['type'] == node_type]

def get_final_tasks_from_listener(listener):
    """Get list of task names that produce final exports from a parsed listener."""
    final_tasks = []
    
    # Find all export nodes (E*)
    export_nodes = [node['id'] for node in listener.nodes if node['type'] == 'E']
    
    # For each export, trace back to find the task that produces it
    for export_id in export_nodes:
        # Find runnable that produces this export (R -> E)
        producing_runnable = None
        for from_node, to_node in listener.edges:
            if to_node == export_id and from_node.startswith('R'):
                producing_runnable = from_node
                break
        
        if producing_runnable:
            # Find task that produces this runnable (T -> R)
            for from_node, to_node in listener.edges:
                if to_node == producing_runnable and from_node.startswith('T'):
                    task_node = get_node_by_id(listener.nodes, from_node)
                    if task_node:
                        final_tasks.append(task_node['content'])
                    break
    
    # Remove duplicates and return
    return list(set(final_tasks))

# =============================================================================
# TEMPLATE GENERATION FUNCTIONS
# =============================================================================

def generate_status_task(listener):
    """Generate the status task based on parsed mermaid content."""
    # Extract file information from nodes
    status_files = []
    
    # Get export nodes
    export_nodes = get_nodes_by_type(listener.nodes, 'E')
    for node in export_nodes:
        filename = node['content'].replace('BWV000', '{PROJECT_NAME}')
        description = node.get('description', node['content'])
        status_files.append(('Export', description, filename))
    
    # Get output nodes
    output_nodes = get_nodes_by_type(listener.nodes, 'O')
    for node in output_nodes:
        filename = node['content'].replace('BWV000', '{PROJECT_NAME}')
        description = node.get('description', node['content'])
        status_files.append(('Output', description, filename))
    
    # Get input nodes that are generated (like ties.csv)
    input_nodes = get_nodes_by_type(listener.nodes, 'I')
    for node in input_nodes:
        filename = node['content'].replace('BWV000', '{PROJECT_NAME}')
        # Only include generated input files (not source files)
        if filename.endswith('.csv') or 'generated' in filename.lower():
            description = node.get('description', node['content'])
            status_files.append(('Input', description, filename))
    
    # Generate status_files list entries
    status_entries = []
    for category, description, filename in status_files:
        status_entries.append(f"        ('{category}', '{description}', f'{filename}'),")
    status_list = '\n'.join(status_entries)
    
    return f"""@task
def status(c):
    \"\"\"Show build status of all files.\"\"\"
    print(f"🎼 Detected project: {{PROJECT_NAME}}")
    
    # File information extracted from mermaid diagram
    status_files = [
{status_list}
    ]
    
    # Get file info and sort by timestamp
    file_infos = []
    for category, description, filename in status_files:
        file_infos.append(get_file_info(filename, description))
    
    # Sort by timestamp (missing files first, then by modification time)
    file_infos.sort(key=lambda x: x[0])
    
    print("📊 Build Status:")
    for mtime, name, filename, size, exists in file_infos:
        if exists:
            mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            print(f"   ✅ {{name:<18}}: {{filename:<75}} ({{size:>10,}} bytes, {{mtime_str}})")
        else:
            print(f"   ❌ {{name:<18}}: {{filename:<75}} (missing)")"""

def generate_clean_task(listener):
    """Generate the clean task based on parsed mermaid content."""
    # Get all target files (outputs and exports)
    target_files = []
    
    # Get export nodes
    export_nodes = get_nodes_by_type(listener.nodes, 'E')
    for node in export_nodes:
        filename = node['content'].replace('BWV000', '{PROJECT_NAME}')
        target_files.append(filename)
    
    # Get output nodes
    output_nodes = get_nodes_by_type(listener.nodes, 'O')
    for node in output_nodes:
        filename = node['content'].replace('BWV000', '{PROJECT_NAME}')
        target_files.append(filename)
    
    # Get generated input files (like ties.csv)
    input_nodes = get_nodes_by_type(listener.nodes, 'I')
    for node in input_nodes:
        filename = node['content'].replace('BWV000', '{PROJECT_NAME}')
        # Only include generated input files
        if filename.endswith('.csv') or 'generated' in filename.lower():
            target_files.append(filename)
    
    # Generate target_files list entries
    target_entries = []
    for filename in target_files:
        target_entries.append(f"        f'{filename}',")
    target_list = '\n'.join(target_entries)
    
    return f"""@task
def clean(c):
    \"\"\"Delete all generated output files.\"\"\"
    print(f"🎼 Detected project: {{PROJECT_NAME}}")
    
    # Target files extracted from mermaid diagram
    target_files = [
{target_list}
    ]
    
    # Delete files
    deleted = []
    for filename in target_files:
        path = Path(filename)
        if path.exists():
            path.unlink()
            deleted.append(path.name)
    
    print("🗑️ Deleted:", end="")
    if deleted:
        print()
        for d in deleted:
            print(f"   └── {{d}}")
    else:
        print(" ∅")
    
    # Also clean build cache
    cache_file = Path('.build_cache.json')
    if cache_file.exists():
        cache_file.unlink()
        print("🗑️ Deleted build cache")"""

def generate_all_task(listener):
    """Generate the 'all' task that runs final export tasks."""
    final_tasks = get_final_tasks_from_listener(listener)
    
    if not final_tasks:
        return ""
    
    final_tasks_list = ', '.join(f"'{task}'" for task in final_tasks)
    
    # Generate task calls
    task_calls = []
    for task_name in final_tasks:
        task_calls.append(f"    {task_name}(c, force=force)")
    task_calls_code = '\n'.join(task_calls)
    
    return f"""@task
def all(c, force=False):
    \"\"\"Build all final outputs by running the complete pipeline.\"\"\"
    print(f"🎼 Building all outputs for project: {{PROJECT_NAME}}")
    
    # Final tasks that produce exports: {final_tasks_list}
    print("🔄 Running final pipeline tasks...")
    
{task_calls_code}
    
    print("🎉 All pipeline outputs completed!")"""

def generate_info_task(listener):
    """Generate the info task with pipeline information."""
    # Get all task nodes for listing
    task_nodes = get_nodes_by_type(listener.nodes, 'T')
    
    # Generate pipeline tasks list entries
    pipeline_entries = []
    for task_node in task_nodes:
        task_name = task_node['content']
        description = task_node.get('description', task_name.replace('_', ' ').title())
        pipeline_entries.append(f"        ('{task_name}', '{description}'),")
    pipeline_list = '\n'.join(pipeline_entries)
    
    return f"""@task
def info(c):
    \"\"\"Show information about the build system.\"\"\"
    print("🚀 BWV Build System")
    print("=" * 50)
    print(f"🎼 Project: {{PROJECT_NAME}}")
    print(f"📄 Pipeline: tasks.mmd")
    print(f"🤖 Generated: tasks_generated.py")
    print(f"📋 Available tasks:")
    print("   • status     - Show file status")
    print("   • clean      - Delete outputs") 
    print("   • all        - Build all final outputs")
    print("   • info       - This information")
    print("   🔧 Pipeline tasks (from tasks.mmd):")
    
    # Pipeline tasks extracted from mermaid diagram
    pipeline_tasks = [
{pipeline_list}
    ]
    
    for task_name, description in pipeline_tasks:
        print(f"      • {{task_name:<20}} - {{description}}")"""

# =============================================================================
# FILE HEADER GENERATION
# =============================================================================

def generate_file_header():
    """Generate the file header with imports and common functions."""
    return '''#!/usr/bin/env python3
"""
Generated Meta Tasks - Auto-generated from mermaid diagram

DO NOT EDIT MANUALLY - This file is auto-generated
Regenerate with: python tasks_mermaid_generator.py -i tasks.mmd -o meta_tasks.py
"""

from invoke import task
from pathlib import Path
from datetime import datetime
from tasks_utils import get_file_info, detect_project_name

# Cache project name at module level - detected only once
PROJECT_NAME = detect_project_name()

'''

# =============================================================================
# MAIN GENERATION FUNCTION
# =============================================================================

def generate_meta_tasks(mermaid_file):
    """Generate meta tasks from mermaid file and return as string."""
    print(f"📄 Processing mermaid file: {mermaid_file}")
    
    mermaid_path = Path(mermaid_file)
    if not mermaid_path.exists():
        print(f"❌ Mermaid file not found: {mermaid_path}")
        return ""
    
    try:
        # Read and parse with ANTLR
        content = mermaid_path.read_text()
        input_stream = InputStream(content)
        lexer = MermaidPipelineLexer(input_stream)
        lexer.removeErrorListeners()
        
        stream = CommonTokenStream(lexer)
        parser = MermaidPipelineParser(stream)
        parser.removeErrorListeners()
        
        tree = parser.diagram()
        
        # Extract information using listener
        listener = MermaidDisplayListener()
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        
        print(f"✅ Parsed {len(listener.nodes)} nodes and {len(listener.edges)} edges")
        
        # Generate all meta-tasks
        status_task = generate_status_task(listener)
        clean_task = generate_clean_task(listener)
        all_task = generate_all_task(listener)
        info_task = generate_info_task(listener)
        
        # Generate complete file content
        header = generate_file_header()
        meta_tasks = f"""{header}
{status_task}


{clean_task}


{all_task}


{info_task}
"""
        
        return meta_tasks
        
    except Exception as e:
        print(f"❌ Error parsing mermaid file: {e}")
        import traceback
        traceback.print_exc()
        return ""

# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate meta tasks from mermaid pipeline diagrams',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python tasks_mermaid_generator.py -i tasks.mmd -o meta_tasks.py
  python tasks_mermaid_generator.py --input tasks.mmd --output generated_tasks.py
        ''')
    
    parser.add_argument('-i', '--input', 
                        required=True,
                        help='Input mermaid file (.mmd)')
    
    parser.add_argument('-o', '--output', 
                        required=True,
                        help='Output Python file (.py)')
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Input file not found: {input_path}")
        sys.exit(1)
    
    if not input_path.suffix.lower() in ['.mmd', '.md']:
        print(f"⚠️  Warning: Input file doesn't have .mmd extension: {input_path}")
    
    # Validate output file
    output_path = Path(args.output)
    if not output_path.suffix.lower() == '.py':
        print(f"⚠️  Warning: Output file doesn't have .py extension: {output_path}")
    
    # Generate meta tasks
    print(f"🚀 Generating meta tasks...")
    print(f"   Input:  {input_path}")
    print(f"   Output: {output_path}")
    
    meta_tasks_content = generate_meta_tasks(args.input)
    
    if meta_tasks_content:
        # Write to output file
        try:
            output_path.write_text(meta_tasks_content)
            print(f"✅ Successfully generated: {output_path}")
            print(f"📊 File size: {len(meta_tasks_content):,} characters")
            
            # Count lines for summary
            line_count = len(meta_tasks_content.splitlines())
            print(f"📏 Lines generated: {line_count}")
            
        except Exception as e:
            print(f"❌ Error writing output file: {e}")
            sys.exit(1)
    else:
        print("❌ Failed to generate meta-tasks")
        sys.exit(1)

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Minimal Mermaid Utils - Parse .mmd files and generate Invoke tasks

Version: 3.7.0 - Fixed list concatenation syntax for sources

Usage:
  python tasks_mermaid_utils.py tasks.mmd
  python tasks_mermaid_utils.py tasks.mmd --generate-tasks

Requirements: 
  pip install antlr4-python3-runtime
  Generate ANTLR classes: source build_antlr.sh

Changes in v3.3.0:
  - Fixed sources list concatenation: [Path("file.ly")] + shared_ly_sources()
  - Improved sources generation logic for proper Python syntax

Changes in v3.2.0:
  - Fixed all f-string interpolations to properly use {PROJECT_NAME}
  - Ensured consistent variable interpolation in generated commands and targets

Changes in v3.1.0:
  - Added project name caching at module level for better performance
  - Fixed f-string generation for targets and commands
  - Only call detect_project_name() once when module loads

Changes in v3.0.0:
  - Implemented separate lexer/parser grammars with lexer modes
  - Fixed Docker command parsing with preserved spaces
  - Enhanced content extraction with multiple fallback methods
  - Maintains all original functionality from v2.9.0
"""

VERSION = "3.7.0"

import sys
from pathlib import Path
import antlr4
from antlr4 import *

# Import generated ANTLR classes
try:
    from MermaidPipelineLexer import MermaidPipelineLexer
    from MermaidPipelineParser import MermaidPipelineParser
    from MermaidPipelineParserListener import MermaidPipelineParserListener
except ImportError as e:
    print(f"❌ Error importing ANTLR classes: {e}")
    print("💡 Make sure you have generated the ANTLR classes with:")
    print("   source build_antlr.sh")
    print("")
    print("📁 Required files:")
    print("   - MermaidPipelineLexer.py")
    print("   - MermaidPipelineParser.py") 
    print("   - MermaidPipelineParserListener.py")
    sys.exit(1)

# =============================================================================
# ANTLR LISTENER WITH LEXER MODE SUPPORT
# =============================================================================

class MermaidDisplayListener(MermaidPipelineParserListener):
    """ANTLR listener that extracts mermaid content with proper whitespace preservation."""
    
    def __init__(self):
        self.nodes = []
        self.edges = []
        self.class_defs = []
        self.class_assignments = []
        self.graph_direction = None
        self.init_content = None
    
    def enterGraphDeclaration(self, ctx):
        """Extract graph direction."""
        try:
            if hasattr(ctx, 'direction') and ctx.direction():
                self.graph_direction = ctx.direction().getText()
        except Exception as e:
            print(f"⚠️ Warning in enterGraphDeclaration: {e}")
    
    def enterInitBlock(self, ctx):
        """Extract init block content."""
        try:
            if hasattr(ctx, 'initContent') and ctx.initContent():
                self.init_content = ctx.initContent().getText()
        except Exception as e:
            print(f"⚠️ Warning in enterInitBlock: {e}")
    
    def enterNodeDeclaration(self, ctx):
        """Extract node declarations with preserved whitespace from lexer modes."""
        try:
            # Get node ID
            node_id = None
            if hasattr(ctx, 'nodeId') and ctx.nodeId():
                node_id = ctx.nodeId().getText()
            else:
                print(f"⚠️ No nodeId found")
                return
            
            # Get node content from the shape (brackets, parens, braces)
            content = ""
            shape_type = "none"
            
            if hasattr(ctx, 'nodeShape') and ctx.nodeShape():
                shape_ctx = ctx.nodeShape()
                
                # The content should be available via nodeContent()
                if hasattr(shape_ctx, 'nodeContent') and shape_ctx.nodeContent():
                    content_ctx = shape_ctx.nodeContent()
                    content = content_ctx.getText()  # This should now preserve whitespace!
                    
                    # Detect shape type from the shape context
                    if hasattr(shape_ctx, 'LSQUARE') and shape_ctx.LSQUARE():
                        shape_type = "square"
                    elif hasattr(shape_ctx, 'LPAREN') and shape_ctx.LPAREN():
                        shape_type = "round"  
                    elif hasattr(shape_ctx, 'LBRACE') and shape_ctx.LBRACE():
                        shape_type = "diamond"
                else:
                    print("⚠️ No nodeContent found in nodeShape")
            else:
                # Node without explicit shape - just the ID
                content = node_id
            
            # Split content by <br/> if present
            if '<br/>' in content:
                parts = content.split('<br/>')
                main_content = parts[0].strip()
                description = parts[1].strip() if len(parts) > 1 else ""
            else:
                main_content = content.strip()
                description = ""
            
            self.nodes.append({
                'id': node_id,
                'type': node_id[0] if node_id else 'U',
                'content': main_content,
                'description': description
            })
            
        except Exception as e:
            print(f"❌ Error processing node {ctx.getText()}: {e}")
            import traceback
            traceback.print_exc()
    
    def enterEdge(self, ctx):
        """Extract edge relationships."""
        try:
            if hasattr(ctx, 'nodeId'):
                # Get the two node IDs
                node_ids = []
                for i in range(ctx.getChildCount()):
                    child = ctx.getChild(i)
                    if hasattr(child, 'getText'):
                        child_text = child.getText()
                        # Check if this looks like a node ID
                        if len(child_text) > 0 and child_text[0] in 'ITORE':
                            node_ids.append(child_text)
                
                if len(node_ids) >= 2:
                    from_node = node_ids[0]
                    to_node = node_ids[1]
                    self.edges.append((from_node, to_node))
                
        except Exception as e:
            print(f"❌ Error processing edge: {e}")
    
    def enterClassDef(self, ctx):
        """Extract classDef statements."""
        try:
            class_name = ""
            properties = ""
            
            if hasattr(ctx, 'IDENTIFIER') and ctx.IDENTIFIER():
                class_name = ctx.IDENTIFIER().getText()
            
            if hasattr(ctx, 'cssContent') and ctx.cssContent():
                properties = ctx.cssContent().getText()
            
            if class_name:
                self.class_defs.append((class_name, properties))
                
        except Exception as e:
            print(f"❌ Error processing classDef: {e}")
    
    def enterClassAssignment(self, ctx):
        """Extract class assignments."""
        try:
            class_name = ""
            nodes = []
            
            if hasattr(ctx, 'classNodeList') and ctx.classNodeList():
                node_list = ctx.classNodeList()
                # Get all node IDs from the list
                for child in node_list.getChildren():
                    if hasattr(child, 'getText') and child.getText() not in [',']:
                        text = child.getText()
                        if len(text) > 0 and text[0] in 'ITORE':
                            nodes.append(text)
            
            if hasattr(ctx, 'IDENTIFIER') and ctx.IDENTIFIER():
                class_name = ctx.IDENTIFIER().getText()
            
            if class_name and nodes:
                self.class_assignments.append((nodes, class_name))
                
        except Exception as e:
            print(f"❌ Error processing class assignment: {e}")
    
    def enterComment(self, ctx):
        """Handle comments (mostly ignore but could log)."""
        pass

# =============================================================================
# TASK GENERATION FUNCTIONS (same as v2.9.0)
# =============================================================================

def get_node_by_id(nodes, node_id):
    """Get node by its ID."""
    return next((n for n in nodes if n['id'] == node_id), None)

def get_nodes_by_type(nodes, node_type):
    """Get all nodes of a specific type."""
    return [n for n in nodes if n['type'] == node_type]

def trace_task_dependencies(task_id, edges, nodes):
    """
    Trace task dependencies by following the graph.
    Returns list of task function names that this task depends on.
    """
    dependencies = []
    
    # Strategy: Follow the pipeline flow backwards
    # For each task, find what it needs to run before it
    
    # Method 1: Direct task dependencies (T -> T)
    for from_node, to_node in edges:
        if to_node == task_id and from_node.startswith('T'):
            dep_task = get_node_by_id(nodes, from_node)
            if dep_task:
                dependencies.append(dep_task['content'])
    
    # Method 2: Dependencies through outputs (O -> T means T depends on whatever creates O)
    for from_node, to_node in edges:
        if to_node == task_id and from_node.startswith('O'):
            # Find what runnable creates this output
            for r_from, r_to in edges:
                if r_to == from_node and r_from.startswith('R'):
                    # Find what task creates this runnable
                    for t_from, t_to in edges:
                        if t_to == r_from and t_from.startswith('T'):
                            dep_task = get_node_by_id(nodes, t_from)
                            if dep_task:
                                dependencies.append(dep_task['content'])
    
    # Remove duplicates and return
    return list(set(dependencies))

def get_task_sources(task_id, edges, nodes):
   """
   Determine source files for a task based on input dependencies.
   Returns the complete sources expression as a string for direct use in code generation.
   """
   path_sources = []
   
   # Find inputs that flow to this task
   for from_node, to_node in edges:
       if to_node == task_id and from_node.startswith('I'):
           input_node = get_node_by_id(nodes, from_node)
           if input_node:
               # Extract filename from content and fix BWV000 placeholder
               filename = input_node['content']
               if 'BWV000' in filename:
                   # Generate f-string version for runtime interpolation
                   filename = filename.replace('BWV000', '{PROJECT_NAME}')
                   path_sources.append(f'Path(f"{filename}")')
               else:
                   # Regular filename
                   path_sources.append(f'Path("{filename}")')
   
   # Check if we have .ly files to determine if we need shared sources
   has_ly_files = any('.ly' in src for src in path_sources)
   
   # Build the complete sources expression as a string
   if path_sources and has_ly_files:
       path_list = ', '.join(path_sources)
       return f'[{path_list}] + shared_ly_sources()'
   elif path_sources:
       path_list = ', '.join(path_sources)
       return f'[{path_list}]'
   elif has_ly_files:
       return 'shared_ly_sources()'
   else:
       return '[]'
   
def get_task_targets(task_id, edges, nodes):
    """
    Determine target files for a task based on runnable->output dependencies.
    """
    targets = []
    
    # Find the runnable that this task produces (T -> R)
    runnable_id = None
    for from_node, to_node in edges:
        if from_node == task_id and to_node.startswith('R'):
            runnable_id = to_node
            break
    
    # Find outputs that this runnable produces (R -> O)
    if runnable_id:
        for from_node, to_node in edges:
            if from_node == runnable_id and to_node.startswith('O'):
                output_node = get_node_by_id(nodes, to_node)
                if output_node:
                    # Extract filename from content and fix BWV000 placeholder
                    filename = output_node['content']
                    filename = filename.replace('BWV000', '{PROJECT_NAME}')
                    targets.append(f'f"{filename}"')
    
    return targets

def get_task_command(task_id, edges, nodes):
    """
    Get the command for a task by finding its corresponding runnable.
    """
    # Find the runnable that this task maps to (T -> R)
    for from_node, to_node in edges:
        if from_node == task_id and to_node.startswith('R'):
            runnable_node = get_node_by_id(nodes, to_node)
            if runnable_node:
                command = runnable_node['content']
                print(f"   Raw command: '{command}'")
                
                # Check if it's a Docker command or Python script
                if 'docker' in command.lower() and 'run' in command.lower():
                    # Handle Docker command (fix spacing issues if needed)
                    # Replace project name placeholder and fix path
                    command = command.replace('BWV000', '{PROJECT_NAME}')
                    command = command.replace('PWD', f'{{Path.cwd()}}')
                    return f'f"{command}"'
                elif command.startswith('bwv_script:'):
                    # Extract script name and arguments  
                    # Format: "bwv_script:script_name.py arg1 arg2 ..."
                    parts = command.split()
                    script_part = parts[0]  # "bwv_script:script_name.py"
                    script_name = script_part.replace('bwv_script:', '')
                    args = parts[1:] if len(parts) > 1 else []
                    
                    # Replace project name in arguments
                    args = [arg.replace('BWV000', '{PROJECT_NAME}') for arg in args]
                    
                    if args:
                        args_str = ', '.join(f'f"{arg}"' for arg in args)
                        return f'run_bwv_script("{script_name}", {args_str})'
                    else:
                        return f'run_bwv_script("{script_name}")'
    
    return None

def debug_task_mapping(task_id, edges, nodes):
    """Debug function to see what's happening with task mapping."""
    print(f"\n🔍 Debug task {task_id}:")
    
    # Show edges from this task
    task_edges = [(f, t) for f, t in edges if f == task_id]
    print(f"   Edges from {task_id}: {task_edges}")
    
    # Show edges to this task  
    to_task_edges = [(f, t) for f, t in edges if t == task_id]
    print(f"   Edges to {task_id}: {to_task_edges}")
    
    # Try to find runnable
    runnable = None
    for from_node, to_node in edges:
        if from_node == task_id and to_node.startswith('R'):
            runnable = get_node_by_id(nodes, to_node)
            break
    
    print(f"   Found runnable: {runnable['id'] if runnable else 'None'}")
    if runnable:
        print(f"   Runnable content: {runnable['content']}")
    
    return runnable

def generate_tasks_file(listener):
    """Generate the tasks_generated.py file."""
    
    # Get all task nodes
    task_nodes = get_nodes_by_type(listener.nodes, 'T')
    
    # Debug: Print what we found
    print(f"🔍 Found {len(task_nodes)} task nodes:")
    for task in task_nodes:
        print(f"   {task['id']}: {task['content']}")
    
    print(f"🔍 Found {len(listener.edges)} edges")
    
    # Start building the file content
    content = []
    content.append('#!/usr/bin/env python3')
    content.append('"""')
    content.append('Generated Invoke Tasks - Auto-generated from tasks.mmd')
    content.append('')
    content.append('DO NOT EDIT MANUALLY - This file is auto-generated')
    content.append('Regenerate with: python tasks_mermaid_utils.py tasks.mmd --generate-tasks')
    content.append('"""')
    content.append('')
    content.append('from invoke import task')
    content.append('from pathlib import Path')
    content.append('from tasks_utils import smart_task, detect_project_name, flatten_tree, get_shared_ly_sources_tree, run_bwv_script')
    content.append('')
    content.append('# Cache project name at module level - detected only once')
    content.append('PROJECT_NAME = detect_project_name()')
    content.append('')
    content.append('')
    content.append('def shared_ly_sources():')
    content.append('    """Get shared LilyPond source dependencies."""')
    content.append('    return [Path(p) for p in flatten_tree(get_shared_ly_sources_tree(PROJECT_NAME))]')
    content.append('')
    content.append('')
    
    # Generate each task
    for task_node in task_nodes:
        task_id = task_node['id']
        task_name = task_node['content']
        task_description = task_node.get('description', task_name.replace('_', ' ').title())
        
        # Debug this specific task
        debug_task_mapping(task_id, listener.edges, listener.nodes)
        
        # Get task dependencies
        dependencies = trace_task_dependencies(task_id, listener.edges, listener.nodes)
        print(f"   Dependencies: {dependencies}")
        
        # Get sources, targets, and commands
        sources = get_task_sources(task_id, listener.edges, listener.nodes)
        targets = get_task_targets(task_id, listener.edges, listener.nodes)
        command = get_task_command(task_id, listener.edges, listener.nodes)
        
        print(f"   Sources: {sources}")
        print(f"   Targets: {targets}")
        print(f"   Command: {command}")
        
        # Generate task decorator
        if dependencies:
            dep_names = ', '.join(dependencies)
            content.append(f'@task(pre=[{dep_names}])')
        else:
            content.append('@task')
        
        # Generate task function
        content.append(f'def {task_name}(c, force=False):')
        content.append(f'    """{task_description}."""')
        content.append('    ')
        
        # Handle commands
        if command:
            if command.startswith('run_bwv_script'):
                # Python script command
                content.append('    # Run BWV Python script')
                content.append(f'    {command}')
            else:
                # Docker or other shell command
                content.append('    smart_task(')
                content.append('        c,')
                content.append(f'        sources={sources},')
                
                if targets:
                    targets_str = ', '.join(targets)
                    content.append(f'        targets=[{targets_str}],')
                else:
                    content.append('        targets=[],')
                
                content.append('        commands=[')
                content.append(f'            {command}')
                content.append('        ],')
                content.append('        force=force,')
                content.append('    )')
        else:
            content.append('    # TODO: Add implementation - no command found')
            content.append('    pass')
        
        content.append('')
        content.append('')
    
    return '\n'.join(content)

# =============================================================================
# PARSER FUNCTIONS
# =============================================================================

def parse_and_display_mermaid(mermaid_file: str, generate_tasks: bool = False):
    """Parse mermaid file and display its contents using ANTLR."""
    print(f"🚀 Mermaid Utils v{VERSION}")
    print(f"📄 Processing file: {mermaid_file}")
    
    mermaid_path = Path(mermaid_file)
    
    if not mermaid_path.exists():
        print(f"❌ Mermaid file not found: {mermaid_path}")
        return
    
    try:
        # Read and parse with ANTLR
        content = mermaid_path.read_text()
        print(f"📏 File size: {len(content)} characters")
        
        # Create ANTLR input stream
        input_stream = InputStream(content)
        lexer = MermaidPipelineLexer(input_stream)
        
        # Set up error handling
        lexer.removeErrorListeners()
        
        stream = CommonTokenStream(lexer)
        parser = MermaidPipelineParser(stream)
        
        # Remove default error listeners to avoid spam
        parser.removeErrorListeners()
        
        # Parse the content
        tree = parser.diagram()
        
        # Extract information using listener
        listener = MermaidDisplayListener()
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        
        if generate_tasks:
            # Generate tasks file
            tasks_content = generate_tasks_file(listener)
            tasks_file = Path('tasks_generated.py')
            tasks_file.write_text(tasks_content)
            print(f"✅ Generated: {tasks_file}")
            print(f"📋 Contains {len(get_nodes_by_type(listener.nodes, 'T'))} task definitions")
        else:
            # Display results
            display_full_parsed_content(listener)
        
    except Exception as e:
        print(f"❌ Error parsing mermaid file: {e}")
        import traceback
        traceback.print_exc()

def display_full_parsed_content(listener):
    """Display complete parsed content including styles."""
    print("🔍 Complete Mermaid Analysis")
    print("=" * 60)
    
    # Graph info
    if listener.graph_direction:
        print(f"📊 Graph Direction: {listener.graph_direction}")
    
    if listener.init_content:
        print(f"⚙️ Init Config: {listener.init_content}")
    
    # Nodes by type
    node_types = {'I': 'Inputs', 'T': 'Tasks', 'O': 'Outputs', 'R': 'Runnables', 'E': 'Exports'}
    
    for node_type, type_name in node_types.items():
        type_nodes = [n for n in listener.nodes if n['type'] == node_type]
        if type_nodes:
            print(f"\n📋 {type_name}:")
            for node in type_nodes:
                print(f"   {node['id']}: {node['content']}")
                if node['description']:
                    print(f"      └─ {node['description']}")
    
    # Edges
    if listener.edges:
        print(f"\n🔗 Relationships:")
        for from_node, to_node in listener.edges:
            print(f"   {from_node} --> {to_node}")
    
    # Class definitions
    if listener.class_defs:
        print(f"\n🎨 Style Definitions:")
        for class_name, properties in listener.class_defs:
            print(f"   {class_name}: {properties}")
    
    # Class assignments
    if listener.class_assignments:
        print(f"\n🏷️ Style Assignments:")
        for nodes, class_name in listener.class_assignments:
            print(f"   {class_name}: {', '.join(nodes)}")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total nodes: {len(listener.nodes)}")
    print(f"   Total edges: {len(listener.edges)}")
    print(f"   Style definitions: {len(listener.class_defs)}")
    print(f"   Style assignments: {len(listener.class_assignments)}")
    for node_type, type_name in node_types.items():
        count = len([n for n in listener.nodes if n['type'] == node_type])
        if count > 0:
            print(f"   {type_name}: {count}")

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python tasks_mermaid_utils.py <mermaid_file.mmd> [--generate-tasks]")
        sys.exit(1)
    
    mermaid_file = sys.argv[1]
    generate_tasks = '--generate-tasks' in sys.argv
    
    parse_and_display_mermaid(mermaid_file, generate_tasks)
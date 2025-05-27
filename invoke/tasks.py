"""
BWV Processing Tasks - Generic build system for Bach scores

Usage from any BWV project:
  invoke --search-root /Users/christophe.thiebaud/github.com/musicollator/bwv-zeug/invoke
"""

from datetime import datetime
from invoke import task
from pathlib import Path
from tasks_mermaid import (get_task_info, analyze_pipeline, get_task_execution_order)
from tasks_utils import run_bwv_script

# Import all utilities from separate module
from tasks_utils import (
    detect_project_name,
    get_shared_ly_sources_tree,
    flatten_tree,
    print_build_status,
    remove_outputs,
    smart_task
)

# =============================================================================
# PROJECT-SPECIFIC CONFIGURATION
# =============================================================================

class ProjectFiles:
    """Centralized project file management with caching."""
    
    def __init__(self):
        self._project_name = None
        self._ly_sources_tree = None
    
    @property
    def name(self):
        """Get project name (cached after first access)."""
        if self._project_name is None:
            self._project_name = detect_project_name()
        return self._project_name
    
    @property
    def ly_sources_tree(self):
        """Get LilyPond sources tree (cached after first access)."""
        if self._ly_sources_tree is None:
            self._ly_sources_tree = get_shared_ly_sources_tree(self.name)
        return self._ly_sources_tree
    
    @property
    def lilypond_outputs(self):
        """Get all LilyPond output files with display names."""
        return [
            (f"{self.name}.pdf", "PDF"),
        ]
    
    @property
    def lilypond_output_files(self):
        """Just the filenames for build system."""
        return [filename for filename, _ in self.lilypond_outputs]
    
    @property
    def all_generated_files(self):
        """Get all generated files including build cache."""
        return self.lilypond_output_files + [".build_cache.json"]

# Create singleton instance
project = ProjectFiles()    

# =============================================================================
# LILYPOND BUILD TASKS
# =============================================================================

@task
def sources(c):
    """Display LilyPond source dependencies in tree and flat format."""

    print(f"🎼 LilyPond Source Dependencies\n")
    
    # Get the tree structure
    tree = project.ly_sources_tree
    
    if not tree:
        print("📄 No include dependencies found")
        return
    
    # Display tree structure (skip the header since we already know the project)
    print("📁 Tree Structure:")
    root_file = Path(f"{project.name}.ly")
    print(f"└── {root_file.name} ({root_file.stat().st_size:,} bytes)")
    
    # Print the tree 
    def print_tree_part(file_path, prefix="    "):
        children = tree.get(file_path, [])
        for i, child in enumerate(children):
            is_last = (i == len(children) - 1)
            connector = "└── " if is_last else "├── "
            size = child.stat().st_size if child.exists() else 0
            print(f"{prefix}{connector}{child.name} ({size:,} bytes)")
    
    print_tree_part(root_file)
    
    # Display flattened structure for verification
    flat_sources = flatten_tree(tree)
    
    print(f"\n📋 Flattened Sources ({len(flat_sources)} files):")
    print("   (This is what gets passed to smart_task for caching)")
    
    for source in sorted(flat_sources, key=lambda p: str(p)):
        if source.exists():
            size = source.stat().st_size
            # Show relative path if it's under current directory, otherwise absolute
            try:
                rel_path = source.relative_to(Path.cwd())
                display_path = rel_path
            except ValueError:
                display_path = source
            print(f"   ✅ {display_path} ({size:,} bytes)")
        else:
            print(f"   ❌ {source} (missing)")
    
    print()

@task
def build_pdf(c, force=False):
    """Generate PDF with LilyPond."""
    
    smart_task(
        c,
        sources=flatten_tree(project.ly_sources_tree), # to be flatten
        targets=[f"{project.name}.pdf"],
        commands=[
            f'docker run -v "{Path.cwd()}:/work" codello/lilypond:dev {project.name}.ly'
        ],
        force=force,
    )

@task
def clean(c):
    """Clean all generated files and build cache."""
    
    remove_outputs(*project.all_generated_files)
    print("🧹 Cleaned all generated files and build cache")

@task
def status(c):
    """Show status of all build targets."""

    files = [
        (f"{project.name}.pdf", "PDF"),
    ]
    
    print_build_status(files)
@task
def all(c, force=False):
    """Run the full build and post-processing pipeline."""
    sources(c)
    build_pdf(c, force=force)
    print(f"\n✅✅✅ All steps completed successfully at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ✅✅✅")


# =============================================================================
# MERMAID EXPERIMENT
# =============================================================================

@task
def mermaid_analysis(c):
    """Show Mermaid pipeline analysis."""
    try:
        analyze_pipeline(project)
    except ImportError:
        print("⚠️  Mermaid module not available")    

# Update your mermaid_run task:
@task
def mermaid_run(c, task_name, force=False):
    """Run any task from the Mermaid pipeline."""
    
    if task_name == "all":
        # Get tasks in dependency order using topological sort
        print("🔄 Analyzing pipeline dependencies...")
        task_order = get_task_execution_order(project)
        
        if not task_order:
            print("❌ No tasks found in pipeline")
            return
        
        print(f"📋 Executing {len(task_order)} tasks in dependency order:")
        for i, task in enumerate(task_order, 1):
            print(f"   {i}. {task}")
        print()
        
        # Execute tasks in order
        for i, task in enumerate(task_order, 1):
            print(f"\n🔄 [{i}/{len(task_order)}] Running {task}...")
            
            # Custom execution for each task
            _run_single_mermaid_task(c, task, force)
        
        print(f"\n✅✅✅ All {len(task_order)} tasks completed successfully! ✅✅✅")
        return
    
    # Normal single task execution
    _run_single_mermaid_task(c, task_name, force)

def _run_single_mermaid_task(c, task_name, force=False):
    """Run a single mermaid task with BWV script support."""
    task_info = get_task_info(project, task_name)
    if not task_info:
        print(f"❌ Task '{task_name}' not found")
        return
    
    sources, targets, commands = task_info
    
    # Debug: print what we got
    print(f"🔍 Debug - Raw commands: {commands}")
    
    # Handle commands manually instead of trying to be clever
    for cmd in commands:
        print(f"🔍 Debug - Processing command: {cmd}")
        
        if cmd.startswith('BWV_SCRIPT:'):
            # Parse: "BWV_SCRIPT:script.py:arg1:arg2:..."
            parts = cmd.split(':', 2)
            script_name = parts[1]
            args = parts[2].split(':') if len(parts) > 2 and parts[2] else []
            
            print(f"🔍 Debug - Script: {script_name}, Args: {args}")
            
            # Use run_bwv_script directly
            try:
                run_bwv_script(script_name, *args)
            except Exception as e:
                print(f"❌ BWV script failed: {e}")
                raise
        else:
            # Regular command
            print(f"🔍 Debug - Running regular command: {cmd}")
            c.run(cmd)
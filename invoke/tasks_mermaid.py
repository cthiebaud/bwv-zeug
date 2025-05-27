#!/usr/bin/env python3
"""
Mermaid Pipeline Parser - Parse .mmd files into executable build pipelines

Usage from tasks.py:
  from mermaid import create_pipeline_from_mermaid, show_pipeline_analysis
"""

import re
from dataclasses import dataclass
from typing import List, Dict, Set, Optional
from pathlib import Path

# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Input:
    """Input node (I1, I2, I3...)."""
    id: str
    filename: str
    description: str

@dataclass
class Task:
    """Task node (T1, T2, T3...)."""
    id: str
    name: str
    description: str

@dataclass
class Output:
    """Output node (O1, O2, O3...)."""
    id: str
    filename: str
    description: str

@dataclass
class Runnable:
    """Runnable node (R1, R2, R3...) - Docker or Python script."""
    id: str
    command: str
    script_file: Optional[str]  # For dependencies
    description: str

@dataclass
class Export:
    """Export node (E1, E2, E3...)."""
    id: str
    filename: str
    description: str

@dataclass
class Pipeline:
    """Complete pipeline structure."""
    inputs: Dict[str, Input]
    tasks: Dict[str, Task]
    outputs: Dict[str, Output]
    runnables: Dict[str, Runnable]
    exports: Dict[str, Export]
    edges: List[tuple]  # (from_id, to_id) relationships

# =============================================================================
# MERMAID PARSER
# =============================================================================

class MermaidParser:
    """Parse systematic Mermaid diagrams into pipeline structures."""
    
    def __init__(self, project):
        self.project = project
    
    def parse_file(self, mermaid_path: Path) -> Pipeline:
        """Parse .mmd file into Pipeline structure."""
        if not mermaid_path.exists():
            print(f"⚠️  Mermaid file not found: {mermaid_path}")
            return Pipeline({}, {}, {}, {}, {}, [])
        
        content = mermaid_path.read_text()
        
        # Parse all nodes first
        inputs = self._parse_inputs(content)
        tasks = self._parse_tasks(content)
        outputs = self._parse_outputs(content)
        runnables = self._parse_runnables(content)
        exports = self._parse_exports(content)
        
        # Parse edges
        edges = self._parse_edges(content)
        
        return Pipeline(inputs, tasks, outputs, runnables, exports, edges)
    
    def _parse_inputs(self, content: str) -> Dict[str, Input]:
        """Parse Input nodes (I1, I2, I3...)."""
        inputs = {}
        # More flexible pattern to handle multiline content
        pattern = r'(I\d+)\[([^\]]+)\]'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            node_id, full_content = match.groups()
            
            # Split by <br/> and take first line as filename
            lines = full_content.split('<br/>')
            filename = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            # Replace BWV000 with actual project name
            actual_filename = filename.replace('BWV000', self.project.name)
            
            inputs[node_id] = Input(
                id=node_id,
                filename=actual_filename,
                description=description
            )
        
        return inputs
    
    def _parse_tasks(self, content: str) -> Dict[str, Task]:
        """Parse Task nodes (T1, T2, T3...)."""
        tasks = {}
        pattern = r'(T\d+)\[([^\]]+)\]'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            node_id, full_content = match.groups()
            
            # Split by <br/> and take first line as name
            lines = full_content.split('<br/>')
            name = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            tasks[node_id] = Task(
                id=node_id,
                name=name,
                description=description
            )
        
        return tasks
    
    def _parse_outputs(self, content: str) -> Dict[str, Output]:
        """Parse Output nodes (O1, O2, O3...)."""
        outputs = {}
        pattern = r'(O\d+)\[([^\]]+)\]'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            node_id, full_content = match.groups()
            
            # Split by <br/> and take first line as filename
            lines = full_content.split('<br/>')
            filename = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            # Replace BWV000 with actual project name
            actual_filename = filename.replace('BWV000', self.project.name)
            
            outputs[node_id] = Output(
                id=node_id,
                filename=actual_filename,
                description=description
            )
        
        return outputs
    
    def _parse_runnables(self, content: str) -> Dict[str, Runnable]:
        """Parse Runnable nodes (R1, R2, R3...)."""
        runnables = {}
        pattern = r'(R\d+)\[([^\]]+)\]'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            node_id, full_content = match.groups()
            
            # Split by <br/> and take first line as command
            lines = full_content.split('<br/>')
            command = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            # Handle BWV script syntax
            if command.startswith('bwv_script:'):
                # Extract script and args: "bwv_script:script.py arg1 arg2"
                parts = command[11:].split()  # Remove "bwv_script:" prefix
                script_name = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                # Replace BWV000 in arguments
                args = [arg.replace('BWV000', self.project.name) for arg in args]
                
                # Create special command that will be handled by smart_task
                actual_command = f"BWV_SCRIPT:{script_name}:{':'.join(args)}"
                script_file = script_name  # For dependencies
            else:
                # Regular command - replace placeholders with actual values
                actual_command = command.replace('BWV000', self.project.name)
                actual_command = actual_command.replace('PWD', '.')  # Use relative path for Docker
                
                # Determine script file for dependencies (if it's a Python script)
                script_file = None
                if actual_command.startswith('python3 '):
                    parts = actual_command.split()
                    if len(parts) >= 2 and parts[1].endswith('.py'):
                        script_file = parts[1]  # Keep the full path for dependencies
            
            runnables[node_id] = Runnable(
                id=node_id,
                command=actual_command,
                script_file=script_file,
                description=description
            )
        
        return runnables
    
    def _parse_exports(self, content: str) -> Dict[str, Export]:
        """Parse Export nodes (E1, E2, E3...)."""
        exports = {}
        pattern = r'(E\d+)\[([^\]]+)\]'
        
        for match in re.finditer(pattern, content, re.DOTALL):
            node_id, full_content = match.groups()
            
            # Split by <br/> and take first line as filename
            lines = full_content.split('<br/>')
            filename = lines[0].strip()
            description = lines[1].strip() if len(lines) > 1 else ""
            
            # Replace BWV000 with actual project name
            actual_filename = filename.replace('BWV000', self.project.name)
            
            exports[node_id] = Export(
                id=node_id,
                filename=actual_filename,
                description=description
            )
        
        return exports
    
    def _parse_edges(self, content: str) -> List[tuple]:
        """Parse all edges from the diagram."""
        edges = []
        pattern = r'(\w+)\s*-->\s*(\w+)'
        
        for match in re.finditer(pattern, content):
            from_node, to_node = match.groups()
            edges.append((from_node, to_node))
        
        return edges

# =============================================================================
# PIPELINE ANALYSIS
# =============================================================================

def topological_sort_tasks(pipeline: Pipeline) -> List[str]:
    """
    Return tasks in dependency order using topological sort.
    
    Returns:
        List of task names in execution order
    """
    # Build dependency graph: task -> list of tasks it depends on
    dependencies = {}
    all_tasks = set(pipeline.tasks.keys())
    
    for task_id in all_tasks:
        dependencies[task_id] = []
    
    # Find dependencies by tracing backwards through the graph
    for task_id in all_tasks:
        # Find what this task needs as input
        for from_node, to_node in pipeline.edges:
            if to_node == task_id:
                # Check if the input comes from another task's output
                for from_task, to_runnable in pipeline.edges:
                    if from_task in all_tasks:
                        # Find what this source task produces
                        for r_from, r_to in pipeline.edges:
                            if r_from in pipeline.runnables and r_to == from_node:
                                # Found: source_task -> runnable -> output -> current_task
                                for t_from, t_to in pipeline.edges:
                                    if t_to == r_from and t_from == from_task:
                                        if from_task != task_id:
                                            dependencies[task_id].append(from_task)
    
    # Kahn's algorithm for topological sorting
    in_degree = {task: 0 for task in all_tasks}
    
    # Calculate in-degrees
    for task in all_tasks:
        for dep in dependencies[task]:
            in_degree[task] += 1
    
    # Start with tasks that have no dependencies
    queue = [task for task in all_tasks if in_degree[task] == 0]
    result = []
    
    while queue:
        # Sort queue to ensure deterministic output
        queue.sort()
        current = queue.pop(0)
        result.append(current)
        
        # Remove this task from dependencies of others
        for task in all_tasks:
            if current in dependencies[task]:
                in_degree[task] -= 1
                if in_degree[task] == 0:
                    queue.append(task)
    
    # Convert task IDs to task names
    task_names = []
    for task_id in result:
        if task_id in pipeline.tasks:
            task_names.append(pipeline.tasks[task_id].name)
    
    return task_names

def analyze_task_dependencies(pipeline: Pipeline, task_id: str) -> tuple:
    """Analyze what a task needs and produces."""
    inputs = []
    outputs = []
    runnable_cmd = ""
    dependencies = []
    
    # Find inputs: Input/Output -> Task
    for from_node, to_node in pipeline.edges:
        if to_node == task_id:
            if from_node in pipeline.inputs:
                inputs.append(pipeline.inputs[from_node].filename)
            elif from_node in pipeline.outputs:
                inputs.append(pipeline.outputs[from_node].filename)
    
    # Find runnable: Task -> Runnable
    for from_node, to_node in pipeline.edges:
        if from_node == task_id and to_node in pipeline.runnables:
            runnable = pipeline.runnables[to_node]
            runnable_cmd = runnable.command
            if runnable.script_file:
                dependencies.append(runnable.script_file)
    
    # Find outputs: Runnable -> Output/Export
    task_runnable_id = None
    for from_node, to_node in pipeline.edges:
        if from_node == task_id and to_node in pipeline.runnables:
            task_runnable_id = to_node
            break
    
    if task_runnable_id:
        for from_node, to_node in pipeline.edges:
            if from_node == task_runnable_id:
                if to_node in pipeline.outputs:
                    outputs.append(pipeline.outputs[to_node].filename)
                elif to_node in pipeline.exports:
                    outputs.append(pipeline.exports[to_node].filename)
    
    return inputs, outputs, runnable_cmd, dependencies

# =============================================================================
# PUBLIC API FUNCTIONS
# =============================================================================

def create_pipeline_from_mermaid(project_instance, mermaid_file: str = "tasks.mmd") -> Pipeline:
    """Create pipeline from Mermaid file."""
    parser = MermaidParser(project_instance)
    
    # Look for mermaid file relative to this module's directory
    if not Path(mermaid_file).is_absolute():
        module_dir = Path(__file__).parent
        mermaid_path = module_dir / mermaid_file
    else:
        mermaid_path = Path(mermaid_file)
    
    return parser.parse_file(mermaid_path)

def get_task_execution_order(project_instance, mermaid_file: str = "tasks.mmd") -> List[str]:
    """Get all tasks in dependency execution order."""
    pipeline = create_pipeline_from_mermaid(project_instance, mermaid_file)
    return topological_sort_tasks(pipeline)

def get_task_info(project_instance, task_name: str, mermaid_file: str = "tasks.mmd") -> Optional[tuple]:
    """Get task information for smart_task integration."""
    pipeline = create_pipeline_from_mermaid(project_instance, mermaid_file)
    
    # Find task by name
    task_id = None
    for tid, task in pipeline.tasks.items():
        if task.name == task_name:
            task_id = tid
            break
    
    if not task_id:
        return None
    
    inputs, outputs, runnable_cmd, dependencies = analyze_task_dependencies(pipeline, task_id)
    
    # Convert to Path objects for smart_task
    source_paths = [Path(f) for f in inputs + dependencies]
    
    return source_paths, outputs, [runnable_cmd] if runnable_cmd else []

def analyze_pipeline(project_instance, mermaid_file: str = "tasks.mmd"):
    """Show complete pipeline analysis."""
    pipeline = create_pipeline_from_mermaid(project_instance, mermaid_file)
    
    print("📊 Pipeline Analysis:")
    print(f"   📥 Inputs: {len(pipeline.inputs)}")
    print(f"   🔧 Tasks: {len(pipeline.tasks)}")
    print(f"   📤 Outputs: {len(pipeline.outputs)}")
    print(f"   ⚙️  Runnables: {len(pipeline.runnables)}")
    print(f"   🎯 Exports: {len(pipeline.exports)}")
    print()
    
    # Show task details
    for task_id, task in pipeline.tasks.items():
        inputs, outputs, runnable_cmd, dependencies = analyze_task_dependencies(pipeline, task_id)
        print(f"📋 {task.name} ({task_id}):")
        print(f"   📥 Inputs: {inputs}")
        print(f"   📤 Outputs: {outputs}")
        print(f"   ⚙️  Command: {runnable_cmd}")
        if dependencies:
            print(f"   🔗 Dependencies: {dependencies}")
        print()

def list_pipeline_tasks(project_instance, mermaid_file: str = "tasks.mmd") -> List[str]:
    """List all available task names."""
    pipeline = create_pipeline_from_mermaid(project_instance, mermaid_file)
    return [task.name for task in pipeline.tasks.values()]
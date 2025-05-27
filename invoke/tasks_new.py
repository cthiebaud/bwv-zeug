import re
from dataclasses import dataclass
from typing import List, Dict, Set
from pathlib import Path
from invoke import task

@dataclass
class TaskNode:
    """Represents a task in the pipeline."""
    name: str
    inputs: List[str]
    outputs: List[str] 
    runnable: str
    dependencies: List[str]  # Script sources that trigger rebuilds
    description: str = ""
    
    @property
    def is_file_node(self) -> bool:
        """Check if this is a file node (not a task)."""
        return '.' in self.name and not self.runnable

@dataclass  
class PipelineGraph:
    """Complete pipeline parsed from Mermaid."""
    tasks: Dict[str, TaskNode]
    edges: List[tuple]  # (from_node, to_node) relationships
    
    @property
    def intermediates(self) -> Set[str]:
        """Files that are outputs of one task and inputs of another."""
        all_outputs = set()
        all_inputs = set()
        
        for task in self.tasks.values():
            if not task.is_file_node:
                all_outputs.update(task.outputs)
                all_inputs.update(task.inputs)
        
        return all_outputs & all_inputs
    
    @property 
    def exports(self) -> Set[str]:
        """Final outputs (have no consumers)."""
        all_outputs = set()
        consumed = set()
        
        for task in self.tasks.values():
            if not task.is_file_node:
                all_outputs.update(task.outputs)
                consumed.update(task.inputs)
        
        return all_outputs - consumed
    
    @property
    def orphans(self) -> Set[str]:
        """Outputs that are neither exports nor intermediates."""
        all_outputs = set()
        for task in self.tasks.values():
            if not task.is_file_node:
                all_outputs.update(task.outputs)
        
        return all_outputs - self.intermediates - self.exports

class MermaidParser:
    """Parse Mermaid diagrams into pipeline graphs."""
    
    def __init__(self, project):
        self.project = project
    
    def parse_file(self, mermaid_path: Path) -> PipelineGraph:
        """Parse a .mmd file into a PipelineGraph."""
        content = mermaid_path.read_text()
        
        # Extract task definitions using naming conventions
        tasks = {}
        edges = []
        
        # Parse graph edges: A --> B, A1 --> D[task_name], etc.
        edge_pattern = r'(\w+)(?:\[([^\]]+)\])?\s*-->\s*(\w+)(?:\[([^\]]+)\])?'
        
        for match in re.finditer(edge_pattern, content):
            from_node, from_label, to_node, to_label = match.groups()
            edges.append((from_node, to_node))
            
            # Create task nodes based on conventions
            if from_label and self._is_task_node(from_label):
                tasks[from_node] = self._parse_task_node(from_node, from_label)
            elif to_label and self._is_task_node(to_label):
                tasks[to_node] = self._parse_task_node(to_node, to_label)
        
        # Build input/output relationships from edges
        self._build_task_relationships(tasks, edges, content)
        
        return PipelineGraph(tasks=tasks, edges=edges)
    
    def _is_task_node(self, label: str) -> bool:
        """Determine if a label represents a task (vs file)."""
        # Convention: tasks don't have file extensions
        return '.' not in label or any(keyword in label.lower() for keyword in 
                                     ['build', 'extract', 'postprocess', 'align'])
    
    def _parse_task_node(self, node_id: str, label: str) -> TaskNode:
        """Parse a task node from its label."""
        lines = label.split('<br/>')
        name = lines[0].strip()
        
        # Extract runnable and dependencies using conventions
        runnable = ""
        dependencies = []
        description = ""
        
        # Convention: look for script names ending in .py
        for line in lines[1:]:
            if line.endswith('.py'):
                runnable = f"python3 {line}"
                dependencies.append(line)
            elif 'docker' in line.lower():
                runnable = self._build_docker_command(line)
            else:
                description += line + " "
        
        return TaskNode(
            name=name,
            inputs=[],  # Will be filled by _build_task_relationships
            outputs=[],
            runnable=runnable.strip(),
            dependencies=dependencies,
            description=description.strip()
        )
    
    def _build_docker_command(self, line: str) -> str:
        """Build docker command based on context."""
        if 'pdf' in line.lower():
            return f'docker run -v "{Path.cwd()}:/work" codello/lilypond:dev {self.project.name}.ly'
        elif 'svg' in line.lower():
            return f'docker run -v "{Path.cwd()}:/work" codello/lilypond:dev --svg {self.project.name}.ly'
        return f'docker run -v "{Path.cwd()}:/work" codello/lilypond:dev'
    
    def _build_task_relationships(self, tasks: Dict[str, TaskNode], edges: List[tuple], content: str):
        """Build input/output relationships from graph edges."""
        # Map file nodes to their actual filenames
        file_nodes = self._extract_file_nodes(content)
        
        for from_node, to_node in edges:
            if from_node in file_nodes and to_node in tasks:
                # File -> Task: file is input
                tasks[to_node].inputs.append(file_nodes[from_node])
            elif from_node in tasks and to_node in file_nodes:
                # Task -> File: file is output  
                tasks[from_node].outputs.append(file_nodes[to_node])
            elif from_node in tasks and to_node in tasks:
                # Task -> Task: outputs of first become inputs of second
                # This requires intermediate file inference
                pass
    
    def _extract_file_nodes(self, content: str) -> Dict[str, str]:
        """Extract file nodes and their actual filenames."""
        file_nodes = {}
        
        # Pattern: A[filename.ext<br/>description]
        file_pattern = r'(\w+)\[([^<\]]+)(?:<br/>([^\]]+))?\]'
        
        for match in re.finditer(file_pattern, content):
            node_id, filename, description = match.groups()
            
            if '.' in filename:  # Has file extension
                # Replace project placeholder
                actual_filename = filename.replace('bwv1006', self.project.name)
                file_nodes[node_id] = actual_filename
        
        return file_nodes

# Usage example:
def create_pipeline_from_mermaid(project_instance, mermaid_file: str = "tasks.mmd") -> PipelineGraph:
    """Create pipeline graph from Mermaid file."""
    parser = MermaidParser(project_instance)
    return parser.parse_file(Path(mermaid_file))

# Integration with existing smart_task:
@task
def run_pipeline_task(c, task_name: str, force=False):
    """Run any task defined in the Mermaid pipeline."""
    # Import here to avoid circular imports
    from tasks import project
    pipeline = create_pipeline_from_mermaid(project)
    
    if task_name not in pipeline.tasks:
        print(f"❌ Task '{task_name}' not found in pipeline")
        return
    
    task_node = pipeline.tasks[task_name]
    
    # Get all dependencies (inputs + script dependencies)
    all_sources = []
    for input_file in task_node.inputs:
        all_sources.append(Path(input_file))
    for dep_script in task_node.dependencies:
        all_sources.append(Path(dep_script))
    
    smart_task(
        c,
        sources=all_sources,
        targets=task_node.outputs,
        commands=[task_node.runnable] if task_node.runnable else [],
        force=force
    )

@task
def show_pipeline_analysis(c):
    """Analyze the pipeline from Mermaid file."""
    from tasks import project
    pipeline = create_pipeline_from_mermaid(project)
    
    print("📊 Pipeline Analysis:")
    print(f"   🔧 Tasks: {len([t for t in pipeline.tasks.values() if not t.is_file_node])}")
    print(f"   📁 Files: {len([t for t in pipeline.tasks.values() if t.is_file_node])}")
    print(f"   🔄 Intermediates: {len(pipeline.intermediates)}")
    print(f"   📤 Exports: {len(pipeline.exports)}")
    print(f"   ⚠️  Orphans: {len(pipeline.orphans)}")
    
    if pipeline.orphans:
        print(f"\n⚠️  Orphan outputs (consider cleanup): {list(pipeline.orphans)}")
    
    print(f"\n📤 Export targets: {list(pipeline.exports)}")
    print(f"🔄 Intermediate files: {list(pipeline.intermediates)}")
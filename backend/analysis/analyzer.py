"""Module for analyzing Python project structure and dependencies."""

import ast
import logging
from pathlib import Path
from typing import Dict, List, Set, Any, Union, Optional
import networkx as nx

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Directories to exclude from analysis
EXCLUDE_DIRS = {'.venv', 'node_modules', '__pycache__', '.git', '.mypy_cache', '.pytest_cache'}

def analyze_project(root_path: Union[str, Path]) -> Dict[str, Any]:
    """Analyze a Python project structure and its dependencies.
    
    Args:
        root_path: Path to the root directory of the project
        
    Returns:
        Dict containing:
        - 'files': Dict mapping file paths to their analysis
        - 'graph': Dependency graph between modules
        - 'error': Optional error message if the path doesn't exist
    """
    root = Path(root_path).resolve()
    
    if not root.exists():
        error_msg = f"Path not found: {root}"
        logger.error(error_msg)
        return {'error': error_msg}
    
    if not root.is_dir():
        error_msg = f"Path is not a directory: {root}"
        logger.error(error_msg)
        return {'error': error_msg}
    
    py_files: List[Path] = []
    try:
        # Find all Python files, excluding certain directories
        for p in root.rglob('*.py'):
            # Skip files in excluded directories
            if not any(part in p.parts for part in EXCLUDE_DIRS):
                py_files.append(p)
    except Exception as e:
        error_msg = f"Error searching for Python files: {e}"
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}
    
    modules: Dict[str, Dict[str, Any]] = {}
    dep_graph = nx.DiGraph()
    
    for file_path in py_files:
        file_path_str = str(file_path)
        try:
            # Read file content with explicit encoding
            try:
                code = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError as e:
                logger.warning(f"Could not decode {file_path}: {e}")
                modules[file_path_str] = {'error': f'Decode error: {e}'}
                continue
                
            # Parse the AST
            try:
                tree = ast.parse(code, filename=file_path_str)
            except SyntaxError as e:
                logger.warning(f"Syntax error in {file_path}: {e}")
                modules[file_path_str] = {
                    'error': f'Syntax error: {e.msg}',
                    'line': e.lineno,
                    'col': e.offset
                }
                continue
                
            # Single pass through the AST for better performance
            funcs: List[str] = []
            classes: List[str] = []
            imports: List[str] = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    funcs.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    if isinstance(node, ast.Import):
                        imports.extend(alias.name for alias in node.names)
                    else:  # ImportFrom
                        if node.module:  # Could be None for 'from . import x'
                            imports.append(node.module)
            
            # Store module information
            modules[file_path_str] = {
                'functions': funcs,
                'classes': classes,
                'num_lines': len(code.splitlines()),
                'imports': imports
            }
            
            # Add to dependency graph
            dep_graph.add_node(file_path_str)
            for imp in imports:
                dep_graph.add_edge(file_path_str, imp)
                
        except Exception as e:
            logger.error(f"Error analyzing {file_path}: {e}", exc_info=True)
            modules[file_path_str] = {
                'error': str(e),
                'type': type(e).__name__
            }
    
    # Convert graph to adjacency list
    adj = {n: list(dep_graph.successors(n)) for n in dep_graph.nodes()}
    
    return {
        'files': modules,
        'graph': adj,
        'stats': {
            'num_files': len(py_files),
            'num_modules': len(modules),
            'num_edges': len(dep_graph.edges())
        }
    }

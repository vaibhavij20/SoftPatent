import ast
from pathlib import Path
import networkx as nx

def analyze_project(root_path):
    root = Path(root_path)
    if not root.exists():
        return {'error': 'path not found'}
    py_files = list(root.rglob('*.py'))
    modules = {}
    G = nx.DiGraph()
    for p in py_files:
        try:
            code = p.read_text(encoding='utf-8')
            tree = ast.parse(code)
            funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
            modules[str(p)] = {
                'functions': [f.name for f in funcs],
                'classes': [c.name for c in classes],
                'num_lines': len(code.splitlines())
            }
            G.add_node(str(p))
            for imp in [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]:
                if isinstance(imp, ast.Import):
                    for nm in imp.names:
                        G.add_edge(str(p), nm.name)
                else:
                    mod = imp.module
                    if mod:
                        G.add_edge(str(p), mod)
        except Exception as e:
            modules[str(p)] = {'error': str(e)}
    adj = {n: list(G.successors(n)) for n in G.nodes()}
    return {'files': modules, 'graph': adj}

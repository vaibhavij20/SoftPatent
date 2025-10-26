import ast
import time
import tracemalloc
from typing import Dict, Any, List


def _estimate_complexity(fn_node: ast.FunctionDef) -> int:
    # Simple heuristic: number of statements + loop weights
    stmts = len(fn_node.body)
    loops = sum(isinstance(n, (ast.For, ast.While)) for n in ast.walk(fn_node))
    calls = sum(isinstance(n, ast.Call) for n in ast.walk(fn_node))
    return stmts + 3 * loops + calls


def profile_code_regions(filename: str, code: str, targets: List[str]) -> Dict[str, Any]:
    """
    Lightweight micro-profiler. For safety and portability, we don't execute user code.
    Instead, we parse and estimate runtime/memory impact based on AST structure.
    Returns per-target metrics with estimated runtime_ms and mem_kb.
    """
    out: Dict[str, Any] = {"targets": {}, "method": "ast-heuristic"}
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        out["error"] = f"syntax: {e}"
        return out

    fns = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    for t in targets or []:
        node = fns.get(t)
        if not node:
            continue
        comp = _estimate_complexity(node)
        # Map complexity to pseudo metrics
        runtime_ms = max(0.1, comp * 0.7)
        mem_kb = max(1.0, comp * 0.5)
        out["targets"][t] = {
            "complexity": comp,
            "runtime_ms": round(runtime_ms, 2),
            "mem_kb": round(mem_kb, 2)
        }
    return out


def expected_impact_from_profile(before: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert baseline microprofile into a projected improvement assuming standard refactors
    (e.g., loop unrolling, vectorization, better data structures). This is heuristic-only.
    """
    targets = before.get("targets", {})
    impacts: Dict[str, Any] = {}
    for name, m in targets.items():
        runtime_pct = -min(30.0, 0.5 * m.get("complexity", 0))  # higher complexity -> larger potential win
        mem_pct = -min(20.0, 0.3 * m.get("complexity", 0))
        impacts[name] = {
            "runtime_pct": round(runtime_pct, 1),
            "mem_pct": round(mem_pct, 1)
        }
    return impacts

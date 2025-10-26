import ast
from typing import List, Dict, Any

try:
    from .openai_integration import call_ai
except Exception:
    call_ai = None
try:
    from . import microprofiler
except Exception:
    microprofiler = None
try:
    from .arch_guard import check_patch as arch_check
except Exception:
    arch_check = None
try:
    from .gnn_invariant_classifier import classify as gnn_classify
except Exception:
    gnn_classify = None
try:
    from .compliance import check_compliance
except Exception:
    check_compliance = None
try:
    from .analyzer import analyze_project
except Exception:
    analyze_project = None

def _compute_ast_metrics(tree: ast.AST) -> Dict[str, Any]:
    functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    max_func_len = 0
    for fn in functions:
        max_func_len = max(max_func_len, len(fn.body))
    return {
        "function_count": len(functions),
        "class_count": len(classes),
        "call_sites": len(calls),
        "max_function_statements": max_func_len,
    }

def _domain_rationale(domain: str) -> str:
    d = (domain or "").lower()
    mapping = {
        "gaming": (
            "Rendering/engine path: focus on frame pacing (stutter reduction), batching, and memory locality. "
            "Refactors that reduce per-frame allocations or state changes translate to more stable FPS."
        ),
        "robotics": (
            "Real-time control loop impact: prioritize deterministic latency and bounded jitter. "
            "Prefer preallocation, lock-free queues, and predictable scheduling to keep loop frequencies stable."
        ),
        "hpc": (
            "Throughput focus: ensure vectorization, contiguous memory, and cache-friendly access; avoid branchy code in hot loops. "
            "Refactors can increase FLOPS and reduce cache misses."
        ),
        "medical": (
            "Safety/compliance: reduce end-to-end latency on critical paths, improve traceability (structured logging) and determinate behavior. "
            "Avoid unstructured I/O and ensure auditable changes."
        ),
    }
    return mapping.get(d, "")


def _generate_java_suggestions(filename: str, code: str) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    # Basic heuristics without a Java parser
    # 1) Detect very long methods by counting braces and lines between method signatures and closing brace
    lines = code.split("\n")
    brace_stack = []
    current_method = None
    current_len = 0
    for ln in lines:
        # naive method signature detection
        if current_method is None and (" void " in ln or " int " in ln or " String " in ln or " boolean " in ln or " public " in ln or " private " in ln or " protected " in ln) and "(" in ln and ")" in ln and "class " not in ln:
            current_method = ln.strip()
            current_len = 0
        if current_method is not None:
            current_len += 1
        for ch in ln:
            if ch == '{':
                brace_stack.append('{')
            elif ch == '}':
                if brace_stack:
                    brace_stack.pop()
                # end of a potential block/method
                if current_method is not None and not brace_stack:
                    if current_len > 50:
                        suggestions.append({
                            "message": "Method may be too long.",
                            "patch": "Consider extracting helper methods to reduce method length.",
                            "reason": f"Detected a long method (~{current_len} lines).",
                            "audit": {"rule": "long_method", "lines": current_len}
                        })
                    current_method = None
                    current_len = 0
    # 2) System.out.println usage
    if "System.out.println" in code or "System.err.println" in code:
        suggestions.append({
            "message": "Avoid System.out.println in production.",
            "patch": "Replace with a logging framework (e.g., java.util.logging or SLF4J).",
            "reason": "Console prints are not configurable and hinder observability.",
            "audit": {"rule": "println_usage"}
        })
    # 3) Unused imports (very naive): import lines not referenced elsewhere
    import_lines = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("import ") and s.endswith(";"):
            imp = s[len("import "):-1].strip()
            import_lines.append(imp)
    lower = code
    for imp in import_lines:
        simple = imp.split('.')[-1]
        # skip wildcard
        if simple == '*':
            continue
        if simple and (simple not in lower):
            suggestions.append({
                "message": f"Unused import: {imp}",
                "patch": f"Remove unused import '{imp}'.",
                "reason": f"Import '{imp}' appears to be unused.",
                "audit": {"rule": "unused_import", "import": imp}
            })
    if not suggestions:
        suggestions.append({
            "message": "✅ No obvious issues found — code looks clean!",
            "patch": "",
            "reason": "No long methods, println, or unused imports detected.",
            "audit": {"rule": "clean"}
        })
    return suggestions


def _generate_cpp_suggestions(filename: str, code: str) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    lines = code.split("\n")
    # 1) Very long functions (heuristic)
    brace_depth = 0
    func_len = 0
    in_func = False
    for ln in lines:
        # naive function signature detection: line with '(' and ')' and not a control statement
        if not in_func and '(' in ln and ')' in ln and not any(k in ln for k in ["if ", "for ", "while ", "switch ", "catch "]):
            in_func = True
            func_len = 0
        if in_func:
            func_len += 1
        for ch in ln:
            if ch == '{':
                brace_depth += 1
            elif ch == '}':
                brace_depth = max(0, brace_depth - 1)
                if in_func and brace_depth == 0:
                    if func_len > 50:
                        suggestions.append({
                            "message": "Function may be too long.",
                            "patch": "Consider splitting into smaller functions or using helper utilities.",
                            "reason": f"Detected a long function (~{func_len} lines).",
                            "audit": {"rule": "long_function", "lines": func_len}
                        })
                    in_func = False
                    func_len = 0
    # 2) std::cout/printf usage
    if "std::cout" in code or "printf(" in code:
        suggestions.append({
            "message": "Prefer structured logging over direct std::cout/printf in production.",
            "patch": "Replace with a logging facility (e.g., spdlog, glog) or conditionally compile debug prints.",
            "reason": "Direct prints are noisy and not configurable.",
            "audit": {"rule": "print_usage"}
        })
    # 3) Unused includes (heuristic): header included but token not seen
    includes = []
    for ln in lines:
        s = ln.strip()
        if s.startswith('#include'):
            includes.append(s)
    for inc in includes:
        # try to extract header name token
        tok = None
        if '"' in inc:
            try:
                tok = inc.split('"')[1]
            except Exception:
                tok = None
        elif '<' in inc and '>' in inc:
            try:
                tok = inc.split('<')[1].split('>')[0]
            except Exception:
                tok = None
        if tok and tok not in code:
            suggestions.append({
                "message": f"Possibly unused include: {tok}",
                "patch": f"Review and remove '#include <{tok}>' if unused.",
                "reason": f"Header '{tok}' may be unused (heuristic).",
                "audit": {"rule": "unused_include", "include": tok}
            })
    if not suggestions:
        suggestions.append({
            "message": "✅ No obvious issues found — code looks clean!",
            "patch": "",
            "reason": "No long functions, direct prints, or unused includes detected.",
            "audit": {"rule": "clean"}
        })
    return suggestions


def generate_suggestions(filename: str, code: str, domain: str = None, path: str = None, targets: List[str] = None, compliance_targets: List[str] = None) -> List[Dict[str, Any]]:
    """
    Analyze Python code and return a list of suggestion dicts.
    Each suggestion: {"message": str, "patch": str, "reason": str, "audit": {...}}
    """

    suggestions = []
    # Normalize line endings and strip BOM if present
    code = code.replace('\r\n', '\n').replace('\r', '\n').lstrip('\ufeff')
    # Log code for debugging
    try:
        with open('code_debug.log', 'w', encoding='utf-8') as dbg:
            dbg.write(repr(code))
    except Exception:
        pass
    # Language routing based on filename extension
    try:
        import os
        ext = os.path.splitext(filename or "")[1].lower()
    except Exception:
        ext = ""

    # Java
    if ext == ".java":
        suggestions = _generate_java_suggestions(filename, code)
        # Tailor and attach domain info later in common post-processing
        # Architecture/compliance checks still apply below
        metrics = {"language": "java"}
    # C/C++
    elif ext in (".cpp", ".cc", ".cxx", ".c", ".hpp", ".hh", ".hxx", ".h"):
        suggestions = _generate_cpp_suggestions(filename, code)
        metrics = {"language": "cpp"}
    else:
        # Default: Python path
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            out = [{
                    "message": f" Syntax error: {e}",
                    "patch": "",
                    "reason": f"Code could not be parsed. Error: {e}",
                    "audit": {"type": "syntax_error"}
                }]
            return out

        metrics = _compute_ast_metrics(tree)

        # Determine profiling targets: provided targets or all top-level functions
        fn_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        fn_names = [n.name for n in fn_defs]
        prof_targets = targets or fn_names[:5]
        baseline_profile = {}
        expected_impact = {}
        if microprofiler and prof_targets:
            try:
                baseline_profile = microprofiler.profile_code_regions(filename, code, prof_targets)
                expected_impact = microprofiler.expected_impact_from_profile(baseline_profile)
            except Exception:
                baseline_profile = {"error": "microprofiler-failed"}

        # Rule 1: Long functions
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                loc = len(node.body)
                if loc > 10:
                    suggestions.append({
                        "message": f"Function '{node.name}' is too long.",
                        "patch": f"Consider splitting '{node.name}' into smaller functions.",
                        "reason": f"Function '{node.name}' has {loc} statements — long functions are harder to maintain.",
                        "audit": {"rule": "long_function", "function": node.name, "statements": loc}
                    })

        # Rule 2: Unused imports
        imports = [n for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))]
        names_used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        for imp in imports:
            for alias in imp.names:
                name = alias.asname or alias.name.split(".")[0]
                if name not in names_used:
                    suggestions.append({
                        "message": f"Unused import: {alias.name}",
                        "patch": f"Remove unused import '{alias.name}'.",
                        "reason": f"Import '{alias.name}' is never referenced in the code.",
                        "audit": {"rule": "unused_import", "import": alias.name}
                    })

        # Rule 3: print() usage
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
                suggestions.append({
                    "message": "Avoid using print() in production code.",
                    "patch": "Replace print() with the logging module.",
                    "reason": "print() calls are not configurable and pollute output logs.",
                    "audit": {"rule": "print_usage"}
                })

        # Adaptive AI: if code is relatively complex, ask AI to propose a patch
        try:
            if call_ai and (metrics.get("max_function_statements", 0) > 15 or metrics.get("function_count", 0) > 10):
                prompt = (
                    "Suggest a minimal, safe patch for the following Python code. "
                    "Return a short 'patch' and an explanatory 'reason'.\n\n" + code
                )
                ai = call_ai(prompt, provider="gemini")
                if isinstance(ai, dict) and ai.get("text"):
                    suggestions.append({
                        "message": "AI-proposed refactor",
                        "patch": ai.get("text", ""),
                        "reason": "Generated by Gemini based on detected complexity (large functions/many functions).",
                        "audit": {"provider": "gemini", "metrics": metrics}
                    })
        except Exception:
            # Non-fatal if AI integration fails
            pass

    # Fallback
    if not suggestions:
        suggestions.append({
            "message": "✅ No issues found — code looks clean!",
            "patch": "",
            "reason": "No long functions, unused imports, or print() calls detected.",
            "audit": {"rule": "clean"}
        })

    # Tailor reasoning based on domain, if provided
    if domain:
        tail = _domain_rationale(domain)
        if tail:
            for s in suggestions:
                if s.get("reason"):
                    s["reason"] = f"{s['reason']} {tail}"
                # attach domain impact cues
                s.setdefault("audit", {})
                s["audit"]["domain_impact"] = {
                    "domain": domain,
                    "notes": tail,
                }

    # Attach expected impact from microprofiler, if available (Python only)
    try:
        if 'expected_impact' in locals() and expected_impact:
            for s in suggestions:
                s.setdefault("audit", {})
                s["audit"]["expected_impact"] = expected_impact
    except Exception:
        pass

    # Architecture and compliance checks to decide automerge
    project_path = path
    if not project_path and filename:
        try:
            # use parent folder of file as project root by default
            import os
            project_path = os.path.dirname(filename)
        except Exception:
            project_path = None
    analysis_graph = None
    if analyze_project and project_path:
        try:
            analysis = analyze_project(project_path)
            analysis_graph = analysis.get("graph") if isinstance(analysis, dict) else None
        except Exception:
            analysis_graph = None

    for s in suggestions:
        s.setdefault("audit", {})
        s.setdefault("can_automerge", True)
        # Arch guard
        if arch_check and analysis_graph:
            try:
                arch_res = arch_check(analysis_graph, s.get("patch", ""), domain or "")
                s["audit"]["arch"] = arch_res
                if not arch_res.get("ok", True):
                    s["can_automerge"] = False
            except Exception:
                pass
        # GNN invariant classifier (pluggable)
        if gnn_classify and analysis_graph:
            try:
                gnn_res = gnn_classify(analysis_graph, s.get("patch", ""), domain)
                s["audit"]["gnn_invariant"] = gnn_res
                # disable automerge on high risk
                if isinstance(gnn_res, dict):
                    risk = gnn_res.get("risk_score")
                    ok = gnn_res.get("ok", True)
                    if (risk is not None and float(risk) >= 0.5) or (ok is False):
                        s["can_automerge"] = False
            except Exception:
                pass
        # Compliance
        if check_compliance and project_path and domain:
            try:
                comp = check_compliance(domain, project_path, targets=compliance_targets)
                s["audit"]["compliance"] = comp
                if isinstance(comp, dict) and comp.get("summary", {}).get("warn", 0) > 0:
                    s["can_automerge"] = False
            except Exception:
                pass

    return suggestions

# Wrapper for app.py compatibility
def generate_suggestion_patch(filename, code):
    """
    Returns (patch, reason) for the first suggestion, or empty strings if none.
    """
    suggestions = generate_suggestions(filename, code)
    if suggestions:
        first = suggestions[0]
        return first.get("patch", ""), first.get("reason", "")
    return "", ""

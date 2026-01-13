import ast
import os
from typing import List, Dict, Any, Optional

# Optional imports – each feature degrades gracefully if missing
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


SUPPORTED_COMPLIANCE_DOMAINS = {
    "gaming",
    "hpc",
    "medical",
    "robotics",
    "satellite",
    "sustainability",
    "speech_therapy",
}


# --------------------------
# Helpers
# --------------------------
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


def _domain_rationale(domain: Optional[str]) -> str:
    if not domain:
        return ""

    d = domain.lower()
    mapping = {
        "gaming": (
            "Rendering/engine path: prioritize frame pacing, batching and memory locality. "
            "Reduce per-frame allocations and state changes to stabilize FPS."
        ),
        "robotics": (
            "Real-time control loops: prioritize deterministic latency and bounded jitter. "
            "Use preallocation, lock-free queues and predictable scheduling."
        ),
        "hpc": (
            "Throughput focus: favor vectorization, contiguous memory and cache-friendly access; "
            "avoid branchy code in hot loops to improve FLOPS and reduce cache misses."
        ),
        "medical": (
            "Safety/compliance: minimize end-to-end latency on critical paths, ensure structured logging "
            "for traceability, and favor deterministic behavior over cleverness."
        ),
        "satellite": (
            "Space-constrained environment: minimize memory footprint and CPU usage, and design for "
            "fault tolerance and predictable behavior over raw performance."
        ),
        "sustainability": (
            "Energy efficiency: target lower algorithmic complexity and reduced memory footprint to "
            "decrease power consumption and resource usage."
        ),
        "speech_therapy": (
            "Real-time audio: ensure low-latency processing, avoid allocations in the hot path and keep "
            "signal-processing pipelines efficient and stable."
        ),
    }
    return mapping.get(
        d,
        "General optimization: balance clarity, maintainability and performance; lean on standard best practices.",
    )


# --------------------------
# Domain-specific rules
# --------------------------
def _apply_domain_specific_rules(
    tree: ast.AST, domain: Optional[str], function_defs: List[ast.FunctionDef]
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    if not domain:
        return suggestions

    d = domain.lower()

    if d == "gaming":
        # Avoid print() in loops over "frame"
        for node in ast.walk(tree):
            if isinstance(node, ast.For) and isinstance(node.target, ast.Name) and node.target.id == "frame":
                for child in ast.walk(node):
                    if (
                        isinstance(child, ast.Call)
                        and isinstance(child.func, ast.Name)
                        and child.func.id == "print"
                    ):
                        suggestions.append(
                            {
                                "message": "Avoid print() inside the frame loop.",
                                "patch": "Use a logging system or debug HUD instead of print() in render/update loops.",
                                "reason": "Print in a frame loop can introduce stutter and unstable frame times.",
                                "audit": {
                                    "rule": "gaming_print_in_loop",
                                    "severity": "high",
                                },
                            }
                        )
                        break

    elif d == "robotics":
        # Avoid blocking sleeps in ROS callbacks
        for fn in function_defs:
            for stmt in fn.body:
                if (
                    isinstance(stmt, ast.Expr)
                    and isinstance(stmt.value, ast.Call)
                    and isinstance(stmt.value.func, ast.Attribute)
                    and isinstance(stmt.value.func.value, ast.Name)
                    and stmt.value.func.attr in ("sleep", "time")
                ):
                    suggestions.append(
                        {
                            "message": f"Avoid blocking sleep() in callback '{fn.name}'.",
                            "patch": "Use ROS timers, rate.sleep() or non-blocking patterns instead of time.sleep().",
                            "reason": "Blocking calls in callbacks can break real-time constraints.",
                            "audit": {
                                "rule": "robotics_blocking_in_callback",
                                "function": fn.name,
                                "severity": "high",
                            },
                        }
                    )

    # You can extend further domains here if needed
    return suggestions


# --------------------------
# Performance analysis
# --------------------------
def _analyze_performance_metrics(
    profile: Dict[str, Any], impact: Dict[str, Any], domain: Optional[str]
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    # High memory usage
    if isinstance(profile, dict):
        mem = profile.get("memory") or {}
        peak = mem.get("peak_memory_mb")
        if isinstance(peak, (int, float)) and peak > 100:
            suggestions.append(
                {
                    "message": f"High memory usage detected (~{peak:.1f} MB peak).",
                    "patch": "Process data in smaller batches or use more compact data structures.",
                    "reason": "High memory usage can cause performance regressions and OOM failures.",
                    "audit": {
                        "rule": "high_memory_usage",
                        "peak_memory_mb": peak,
                        "severity": "medium",
                    },
                }
            )

    # Long-running functions
    functions = profile.get("functions") if isinstance(profile, dict) else None
    if isinstance(functions, dict):
        for fn_name, data in functions.items():
            total_time = data.get("total_time") if isinstance(data, dict) else None
            if isinstance(total_time, (int, float)) and total_time > 1.0:
                suggestions.append(
                    {
                        "message": f"Function '{fn_name}' is slow ({total_time:.2f}s).",
                        "patch": f"Optimize '{fn_name}' (profiling, algorithmic improvements, or caching).",
                        "reason": "Long-running functions are potential performance bottlenecks.",
                        "audit": {
                            "rule": "long_running_function",
                            "function": fn_name,
                            "time_seconds": total_time,
                            "severity": "high",
                        },
                    }
                )

    return suggestions


# --------------------------
# Code quality checks (Python)
# --------------------------
def _run_python_quality_checks(
    tree: ast.AST, code: str, filename: str
) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []

    # Long functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            body_stmts = [
                n
                for n in node.body
                if not (
                    isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Str)
                )
            ]
            loc = len(body_stmts)
            if loc > 50:
                suggestions.append(
                    {
                        "message": f"Function '{node.name}' is too long ({loc} statements).",
                        "patch": f"Split '{node.name}' into smaller, focused helpers.",
                        "reason": "Shorter functions are easier to understand, test and maintain.",
                        "audit": {
                            "rule": "long_function",
                            "function": node.name,
                            "line_count": loc,
                            "severity": "low",
                        },
                    }
                )

    # Unused imports
    imports: Dict[str, int] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for name in node.names:
                imports[name.asname or name.name] = node.lineno

    used_names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    for name, lineno in imports.items():
        if name not in used_names and not name.startswith("_"):
            suggestions.append(
                {
                    "message": f"Unused import '{name}'.",
                    "patch": f"Remove unused import '{name}'.",
                    "reason": "Unused imports add noise and small overhead.",
                    "audit": {
                        "rule": "unused_import",
                        "import": name,
                        "line": lineno,
                        "severity": "low",
                    },
                }
            )

    # Print usage
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
            suggestions.append(
                {
                    "message": "Avoid using print() in production code.",
                    "patch": "Use the logging module with appropriate log levels instead of print().",
                    "reason": "logging allows structured, filterable, and routed output; print() does not.",
                    "audit": {
                        "rule": "print_usage",
                        "severity": "low",
                    },
                }
            )

    return suggestions


# --------------------------
# Java & C/C++ heuristics
# --------------------------
def _generate_java_suggestions(filename: str, code: str) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    lines = code.splitlines()

    # Long methods (very naive)
    brace_stack: List[str] = []
    current_method: Optional[str] = None
    current_len = 0
    for ln in lines:
        if (
            current_method is None
            and "(" in ln
            and ")" in ln
            and "class " not in ln
            and any(
                kw in ln
                for kw in (" void ", " int ", " String ", " boolean ", " public ", " private ", " protected ")
            )
        ):
            current_method = ln.strip()
            current_len = 0

        if current_method is not None:
            current_len += 1

        for ch in ln:
            if ch == "{":
                brace_stack.append("{")
            elif ch == "}":
                if brace_stack:
                    brace_stack.pop()
                if current_method is not None and not brace_stack:
                    if current_len > 50:
                        suggestions.append(
                            {
                                "message": "Method may be too long.",
                                "patch": "Extract helper methods to reduce method length.",
                                "reason": f"Detected a long method (~{current_len} lines).",
                                "audit": {"rule": "long_method", "lines": current_len},
                            }
                        )
                    current_method = None
                    current_len = 0

    # System.out.println usage
    if "System.out.println" in code or "System.err.println" in code:
        suggestions.append(
            {
                "message": "Avoid System.out.println in production.",
                "patch": "Use a logging framework (java.util.logging, SLF4J, etc.) instead.",
                "reason": "Console prints are not configurable and hinder observability.",
                "audit": {"rule": "println_usage"},
            }
        )

    # Unused imports (very naive)
    imports: List[str] = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("import ") and s.endswith(";"):
            imports.append(s[len("import ") : -1].strip())

    for imp in imports:
        simple = imp.split(".")[-1]
        if simple != "*" and simple not in code:
            suggestions.append(
                {
                    "message": f"Unused import: {imp}",
                    "patch": f"Remove unused import '{imp}'.",
                    "reason": f"Import '{imp}' appears unused.",
                    "audit": {"rule": "unused_import", "import": imp},
                }
            )

    if not suggestions:
        suggestions.append(
            {
                "message": "✅ No obvious issues found — code looks clean!",
                "patch": "",
                "reason": "No long methods, println or unused imports detected.",
                "audit": {"rule": "clean"},
            }
        )
    return suggestions


def _generate_cpp_suggestions(filename: str, code: str) -> List[Dict[str, Any]]:
    suggestions: List[Dict[str, Any]] = []
    lines = code.splitlines()

    # Long functions heuristic
    brace_depth = 0
    func_len = 0
    in_func = False
    for ln in lines:
        if (
            not in_func
            and "(" in ln
            and ")" in ln
            and not any(kw in ln for kw in ("if ", "for ", "while ", "switch ", "catch "))
        ):
            in_func = True
            func_len = 0
        if in_func:
            func_len += 1
        for ch in ln:
            if ch == "{":
                brace_depth += 1
            elif ch == "}":
                brace_depth = max(0, brace_depth - 1)
                if in_func and brace_depth == 0:
                    if func_len > 50:
                        suggestions.append(
                            {
                                "message": "Function may be too long.",
                                "patch": "Split into smaller helper functions or utilities.",
                                "reason": f"Detected a long function (~{func_len} lines).",
                                "audit": {"rule": "long_function", "lines": func_len},
                            }
                        )
                    in_func = False
                    func_len = 0

    # std::cout / printf
    if "std::cout" in code or "printf(" in code:
        suggestions.append(
            {
                "message": "Prefer structured logging over std::cout/printf in production.",
                "patch": "Use a logging library (spdlog, glog, etc.) or conditionally compiled debug prints.",
                "reason": "Direct prints are noisy and not configurable.",
                "audit": {"rule": "print_usage"},
            }
        )

    # Possibly unused includes (very naive)
    includes: List[str] = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("#include"):
            includes.append(s)

    for inc in includes:
        token = None
        if '"' in inc:
            parts = inc.split('"')
            if len(parts) >= 3:
                token = parts[1]
        elif "<" in inc and ">" in inc:
            try:
                token = inc.split("<")[1].split(">")[0]
            except Exception:
                token = None
        if token and token not in code:
            suggestions.append(
                {
                    "message": f"Possibly unused include: {token}",
                    "patch": f"Review and remove '#include <{token}>' if unused.",
                    "reason": f"Header '{token}' may be unused.",
                    "audit": {"rule": "unused_include", "include": token},
                }
            )

    if not suggestions:
        suggestions.append(
            {
                "message": "✅ No obvious issues found — code looks clean!",
                "patch": "",
                "reason": "No long functions, direct prints or unused includes detected.",
                "audit": {"rule": "clean"},
            }
        )
    return suggestions


# --------------------------
# Core API
# --------------------------
def generate_suggestions(
    filename: str,
    code: str,
    domain: Optional[str] = None,
    path: Optional[str] = None,
    targets: Optional[List[str]] = None,
    compliance_targets: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Main suggestion generator. Returns a list of suggestion dicts with:
      - message
      - patch
      - reason
      - audit
      - can_automerge
    """
    if not isinstance(code, str) or not code.strip():
        return [
            {
                "message": "No code provided to analyze.",
                "patch": "",
                "reason": "The code string was empty or invalid.",
                "audit": {"type": "input_error"},
                "can_automerge": False,
            }
        ]

    compliance_targets = compliance_targets or []
    suggestions: List[Dict[str, Any]] = []
    expected_impact: Dict[str, Any] = {}
    baseline_profile: Dict[str, Any] = {}
    metrics: Dict[str, Any] = {}

    # Normalize
    code = code.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")

    # Detect language via extension
    try:
        ext = os.path.splitext(filename or "")[1].lower()
    except Exception:
        ext = ""

    # --------------------
    # Java / C++ routes
    # --------------------
    if ext == ".java":
        suggestions = _generate_java_suggestions(filename, code)
    elif ext in (".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"):
        suggestions = _generate_cpp_suggestions(filename, code)
    else:
        # --------------------
        # Python route
        # --------------------
        try:
            tree = ast.parse(code, filename=filename)
        except SyntaxError as e:
            return [
                {
                    "message": f"Syntax error: {e}",
                    "patch": "",
                    "reason": f"Code cannot be parsed. Error: {e}",
                    "audit": {"type": "syntax_error", "error": str(e)},
                    "can_automerge": False,
                }
            ]
        except Exception as e:
            return [
                {
                    "message": "Error analyzing code.",
                    "patch": "",
                    "reason": f"Unexpected error in parser: {str(e)[:200]}",
                    "audit": {"type": "analysis_error", "error": str(e)[:200]},
                    "can_automerge": False,
                }
            ]

        metrics = _compute_ast_metrics(tree)
        fn_defs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        fn_names = [n.name for n in fn_defs]
        prof_targets = targets or fn_names[:5]

        # Domain-specific rules
        suggestions.extend(_apply_domain_specific_rules(tree, domain, fn_defs))

        # Microprofiler (if available)
        if microprofiler and prof_targets and len(code) < 100_000:
            try:
                baseline_profile = microprofiler.profile_code_regions(
                    filename, code, prof_targets
                )
                expected_impact = microprofiler.expected_impact_from_profile(
                    baseline_profile
                )
                suggestions.extend(
                    _analyze_performance_metrics(
                        baseline_profile, expected_impact, domain
                    )
                )
            except Exception as e:
                suggestions.append(
                    {
                        "message": "Performance analysis unavailable.",
                        "patch": "",
                        "reason": f"Microprofiler failed: {str(e)[:200]}",
                        "audit": {
                            "type": "profiling_error",
                            "error": str(e)[:200],
                        },
                    }
                )

        # Standard Python checks
        suggestions.extend(_run_python_quality_checks(tree, code, filename))

        # AI patch for complex code
        try:
            if call_ai and (
                metrics.get("max_function_statements", 0) > 15
                or metrics.get("function_count", 0) > 10
            ):
                prompt = (
                    "Suggest a minimal, safe refactor patch for the following Python code. "
                    "Return ONLY a unified diff or code snippet; keep changes small and clear.\n\n"
                    + code
                )
                ai_res = call_ai(prompt, provider="gemini")
                ai_text = ""
                if isinstance(ai_res, dict):
                    ai_text = ai_res.get("text") or ""
                elif isinstance(ai_res, str):
                    ai_text = ai_res

                if ai_text.strip():
                    suggestions.append(
                        {
                            "message": "AI-proposed refactor.",
                            "patch": ai_text.strip(),
                            "reason": "Generated by Gemini based on detected code complexity.",
                            "audit": {
                                "provider": "gemini",
                                "metrics": metrics,
                            },
                        }
                    )
        except Exception:
            # AI failures are non-fatal
            pass

    # Fallback
    if not suggestions:
        suggestions.append(
            {
                "message": "✅ No issues found — code looks clean!",
                "patch": "",
                "reason": "No long functions, print() calls or unused imports/includes detected.",
                "audit": {"rule": "clean"},
            }
        )

    # --------------------------
    # Decorate suggestions
    # --------------------------
    # Domain rationale
    rationale = _domain_rationale(domain)
    for s in suggestions:
        s.setdefault("audit", {})
        if rationale:
            # Attach domain impact
            s["audit"]["domain_impact"] = {
                "domain": domain or "general",
                "notes": rationale,
            }
            # Enrich reason
            if s.get("reason"):
                s["reason"] = f"{s['reason']} {rationale}"

        # Attach expected impact, if available (Python only)
        if expected_impact:
            s["audit"]["expected_impact"] = expected_impact

        # Placeholder flags; will be refined below
        s.setdefault("can_automerge", True)

    # Project-level analysis graph (for arch/GNN/compliance)
    project_path: Optional[str] = path
    if not project_path and filename:
        try:
            project_path = os.path.dirname(filename)
        except Exception:
            project_path = None

    analysis_graph = None
    if analyze_project and project_path:
        try:
            analysis = analyze_project(project_path)
            if isinstance(analysis, dict):
                analysis_graph = analysis.get("graph")
        except Exception:
            analysis_graph = None

    # Single compliance check per project/domain
    compliance_result: Optional[Dict[str, Any]] = None
    eff_domain = (domain or "").lower()
    if (
        check_compliance
        and project_path
        and eff_domain in SUPPORTED_COMPLIANCE_DOMAINS
    ):
        try:
            compliance_result = check_compliance(
                eff_domain, project_path, targets=compliance_targets
            )
        except Exception:
            compliance_result = None

    # Architecture, GNN, compliance -> can_automerge
    for s in suggestions:
        audit = s.setdefault("audit", {})

        # Arch guard
        if arch_check and analysis_graph:
            try:
                arch_res = arch_check(analysis_graph, s.get("patch", ""), domain or "")
                if hasattr(arch_res, "__dict__") and not isinstance(arch_res, dict):
                    arch_res = arch_res.__dict__
                audit["arch"] = arch_res
                if not arch_res.get("ok", True):
                    s["can_automerge"] = False
            except Exception:
                pass

        # GNN invariants
        if gnn_classify and analysis_graph:
            try:
                gnn_res = gnn_classify(analysis_graph, s.get("patch", ""), domain)
                if hasattr(gnn_res, "__dict__") and not isinstance(gnn_res, dict):
                    gnn_res = gnn_res.__dict__
                audit["gnn_invariant"] = gnn_res
                if isinstance(gnn_res, dict):
                    risk = gnn_res.get("risk_score")
                    ok = gnn_res.get("ok", True)
                    if (risk is not None and float(risk) >= 0.5) or ok is False:
                        s["can_automerge"] = False
            except Exception:
                pass

        # Compliance
        if compliance_result is not None:
            audit["compliance"] = compliance_result
            try:
                summary = compliance_result.get("summary", {}) or {}
                status = compliance_result.get("status")
                warn = int(summary.get("warn", 0))
                failed = int(summary.get("failed", 0))
                if status in ("warn", "error") or warn > 0 or failed > 0:
                    s["can_automerge"] = False
            except Exception:
                pass

    # --------------------------
    # Deduplicate suggestions
    # --------------------------
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for s in suggestions:
        audit = s.get("audit") or {}
        key = (
            s.get("message"),
            s.get("patch"),
            audit.get("rule"),
            audit.get("provider"),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(s)

    return deduped


def generate_suggestion_patch(filename: str, code: str) -> tuple[str, str]:
    """
    Compatibility helper: returns (patch, reason) for the first suggestion.
    """
    suggestions = generate_suggestions(filename, code)
    if suggestions:
        first = suggestions[0]
        return first.get("patch", "") or "", first.get("reason", "") or ""
    return "", ""

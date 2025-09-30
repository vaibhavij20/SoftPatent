import ast

def generate_suggestions(filename: str, code: str):
    """
    Analyze Python code and return a list of suggestion dicts.
    Each suggestion: {"message": str, "patch": str, "reason": str}
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
    try:
        tree = ast.parse(code, filename=filename)
    except SyntaxError as e:
        return [{
            "message": f"⚠️ Syntax error: {e}",
            "patch": "",
            "reason": f"Code could not be parsed. Error: {e}"
        }]

    # Rule 1: Long functions
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            loc = len(node.body)
            if loc > 10:
                suggestions.append({
                    "message": f"Function '{node.name}' is too long.",
                    "patch": f"Consider splitting '{node.name}' into smaller functions.",
                    "reason": f"Function '{node.name}' has {loc} statements — long functions are harder to maintain."
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
                    "reason": f"Import '{alias.name}' is never referenced in the code."
                })

    # Rule 3: print() usage
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "print":
            suggestions.append({
                "message": "Avoid using print() in production code.",
                "patch": "Replace print() with the logging module.",
                "reason": "print() calls are not configurable and pollute output logs."
            })

    # Fallback
    if not suggestions:
        suggestions.append({
            "message": "✅ No issues found — code looks clean!",
            "patch": "",
            "reason": "No long functions, unused imports, or print() calls detected."
        })

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

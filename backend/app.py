from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse, JSONResponse
import os, json, time
from pathlib import Path

# import analysis modules
from analysis.analyzer import analyze_project
from analysis.suggestion import generate_suggestion_patch, generate_suggestions
from analysis.profiler import run_profile_on_example
from analysis.benchmark import run_benchmark, compare_results, record_result
from analysis.feedback import store_feedback
from analysis.compliance import check_compliance
from analysis.validation_packs import runner as validation_runner
try:
    from analysis.openai_integration import _configure_gemini, call_ai as call_ai_provider
except Exception:
    _configure_gemini = None
    call_ai_provider = None
try:
    from analysis.domain_detect import detect_domain
except Exception:
    detect_domain = None
from analysis import timeline as timeline_mod
from analysis import tuning as tuning_mod

# --------------------------------------------------
# Initialize app FIRST
# --------------------------------------------------
app = FastAPI()
BASE = Path(__file__).resolve().parent
EVENT_LOG = BASE / "events.log"
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

if not EVENT_LOG.exists():
    EVENT_LOG.write_text("")

events = []
clients = set()

# --------------------------------------------------
# Event endpoint
# --------------------------------------------------
@app.post("/event")
async def receive_event(request: Request):
    payload = await request.json()
    payload["_received_at"] = time.time()
    events.append(payload)
    with open(EVENT_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")
    return JSONResponse({"status": "ok"})

# --------------------------------------------------
# WebSocket
# --------------------------------------------------
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            with open(EVENT_LOG, "a", encoding="utf-8") as fh:
                fh.write(data + "\n")
    except WebSocketDisconnect:
        clients.remove(ws)

# --------------------------------------------------
# Root page
# --------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    lines = []
    if EVENT_LOG.exists():
        lines = EVENT_LOG.read_text().splitlines()[-50:]
    items = "".join(f"<li><pre>{line}</pre></li>" for line in lines[::-1])
    return HTMLResponse(f"""
    <h1>AI Refactor Backend</h1>
    <p>Endpoints: /event, /analyze, /suggest, /feedback, /profile, /ws</p>
    <ul>{items}</ul>
    """)

# --------------------------------------------------
# Analyzer
# --------------------------------------------------
@app.post("/analyze")
async def analyze(req: Request):
    body = await req.json()
    proj = body.get("path")
    if not proj:
        raise HTTPException(status_code=400, detail="Provide 'path' in JSON body")
    result = analyze_project(proj)
    out = DATA_DIR / "last_analysis.json"
    out.write_text(json.dumps(result, indent=2))
    return JSONResponse({"status": "ok", "result": result})

# --------------------------------------------------
# Suggestion
# --------------------------------------------------
@app.post("/suggest")
async def suggest(req: Request):
    body = await req.json()
    file = body.get("file")
    text = body.get("text")
    domain = body.get("domain")
    compliance_targets = body.get("complianceTargets") or []
    path = body.get("path")
    targets = body.get("targets")
    compliance_targets = body.get("complianceTargets") or []
    if not file or not text:
        raise HTTPException(status_code=400, detail="Provide 'file' and 'text'")
    # Auto-detect domain if not provided
    detected = None
    if (not domain) and detect_domain:
        try:
            proj = path or (Path(file).parent.as_posix() if file else None)
            detected = detect_domain(proj)
            if detected:
                domain = detected
        except Exception:
            detected = None
    try:
        suggestions = generate_suggestions(file, text, domain=domain, path=path, targets=targets, compliance_targets=compliance_targets)
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

    # Optional: tuning-aware ordering if project path provided
    try:
        import hashlib
        proj = path or (Path(file).parent.as_posix() if file else None)
        if proj:
            pid = hashlib.sha256(proj.encode('utf-8')).hexdigest()[:16]
            state = tuning_mod.load_state(DATA_DIR, pid)
            if state.get('enabled', True):
                w = state.get('weights', {})
                def score(s):
                    audit = s.get('audit') if isinstance(s, dict) else None
                    exp = audit.get('expected_impact') if isinstance(audit, dict) else None
                    # Aggregate runtime impact across targets (negative is good)
                    rts = [v.get('runtime_pct', 0) for v in exp.values()] if isinstance(exp, dict) else []
                    rt = (sum(rts)/len(rts)) if rts else 0
                    mems = [v.get('mem_pct', 0) for v in exp.values()] if isinstance(exp, dict) else []
                    mem = (sum(mems)/len(mems)) if mems else 0
                    # Lower (more negative) is better; flip sign for sorting descending
                    sc = -(w.get('runtime',1.0)*rt + 0.5*w.get('memory',1.0)*mem)
                    # Penalize compliance warns and arch violations
                    comp = audit.get('compliance') if isinstance(audit, dict) else None
                    comp_warn = comp.get('summary', {}).get('warn', 0) if isinstance(comp, dict) else 0
                    if comp_warn:
                        sc -= 10.0 * w.get('compliance',1.0)
                    arch = audit.get('arch') if isinstance(audit, dict) else None
                    arch_ok = arch.get('ok', True) if isinstance(arch, dict) else True
                    if not arch_ok:
                        sc -= 5.0 * w.get('architecture',1.0)
                    return sc
                suggestions = sorted(suggestions, key=score, reverse=True)
    except Exception:
        pass
    first_patch, first_reason = ("", "")
    if suggestions:
        first = suggestions[0]
        first_patch = first.get("patch", "")
        first_reason = first.get("reason", "")
    # annotate detection in audits
    if detected:
        try:
            for s in suggestions:
                s.setdefault('audit', {})
                s['audit']['domain_detected'] = detected
        except Exception:
            pass
    return JSONResponse({
        "status": "ok",
        "suggestions": suggestions,
        "patch": first_patch,
        "reason": first_reason
    })

# --------------------------------------------------
# Apply Patch + Timeline
# --------------------------------------------------
@app.post("/apply_patch")
async def apply_patch(req: Request):
    body = await req.json()
    file = body.get("file")
    new_text = body.get("newText")  # optional
    patch_note = body.get("patch")   # textual suggestion, for logging
    domain = body.get("domain")
    project_path = body.get("projectPath") or (str(Path(file).parent) if file else str(BASE.parent))
    compliance_targets = body.get("complianceTargets") or []
    if not file:
        raise HTTPException(status_code=400, detail="Provide 'file'")

    # Pre-apply cues (compliance/arch)
    try:
        analysis = analyze_project(project_path)
    except Exception:
        analysis = {}
    arch = None
    if patch_note:
        try:
            arch = {"ok": True}
            if analysis and isinstance(analysis, dict):
                graph = analysis.get("graph")
                if graph:
                    from analysis.arch_guard import check_patch as arch_check
                    arch = arch_check(graph, patch_note, domain or "")
        except Exception:
            arch = {"ok": True}

    before_text = Path(file).read_text(encoding="utf-8") if Path(file).exists() else ""

    # Apply (MVP: overwrite with newText if provided)
    backup_path = DATA_DIR / "backups" / (Path(file).name + ".bak")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(before_text, encoding="utf-8")
    if isinstance(new_text, str):
        Path(file).write_text(new_text, encoding="utf-8")

    # Post-apply: benchmark and compliance (guarded)
    try:
        bench_after = run_benchmark((domain or "gaming"), project_path)
    except Exception as e:
        return JSONResponse({"status": "error", "stage": "benchmark", "detail": str(e)}, status_code=500)
    try:
        comp = check_compliance(domain or "gaming", project_path, targets=compliance_targets)
    except Exception as e:
        return JSONResponse({"status": "error", "stage": "compliance", "detail": str(e)}, status_code=500)

    # Timeline
    try:
        event = timeline_mod.append_event(DATA_DIR, project_path, {
            "type": "APPLIED",
            "file": file,
            "domain": domain,
            "message": patch_note or "",
            "cues": {"arch": arch},
            "result": {"benchmark": bench_after, "compliance": comp},
            "backup": str(backup_path)
        })
    except Exception as e:
        return JSONResponse({"status": "error", "stage": "timeline", "detail": str(e)}, status_code=500)

    return JSONResponse({"status": "ok", "event": event})

@app.get("/timeline")
async def timeline(project_path: str):
    return JSONResponse({"status": "ok", **timeline_mod.list_events(DATA_DIR, project_path)})

@app.post("/flag_step")
async def flag_step(req: Request):
    body = await req.json()
    project_path = body.get("projectPath")
    file = body.get("file")
    reason = body.get("reason")
    ev = timeline_mod.append_event(DATA_DIR, project_path or str(BASE.parent), {
        "type": "FLAGGED", "file": file, "message": reason or ""
    })
    return JSONResponse({"status": "ok", "event": ev})

@app.post("/revert_step")
async def revert_step(req: Request):
    body = await req.json()
    project_path = body.get("projectPath") or str(BASE.parent)
    file = body.get("file")
    backup = body.get("backupPath")
    if backup and Path(backup).exists() and file:
        Path(file).write_text(Path(backup).read_text(encoding="utf-8"), encoding="utf-8")
    ev = timeline_mod.append_event(DATA_DIR, project_path, {"type": "REVERTED", "file": file, "backup": backup})
    return JSONResponse({"status": "ok", "event": ev})

# --------------------------------------------------
# Tuning endpoints
# --------------------------------------------------
@app.get("/tuning_state")
async def tuning_state(project_path: str):
    import hashlib
    pid = hashlib.sha256(project_path.encode('utf-8')).hexdigest()[:16]
    return JSONResponse({"status": "ok", "state": tuning_mod.load_state(DATA_DIR, pid)})

@app.post("/tuning_toggle")
async def tuning_toggle(req: Request):
    body = await req.json()
    project_path = body.get("projectPath")
    enabled = bool(body.get("enabled", True))
    import hashlib
    pid = hashlib.sha256(project_path.encode('utf-8')).hexdigest()[:16]
    return JSONResponse({"status": "ok", "state": tuning_mod.toggle(DATA_DIR, pid, enabled)})

@app.post("/tuning_reset")
async def tuning_reset(req: Request):
    body = await req.json()
    project_path = body.get("projectPath")
    import hashlib
    pid = hashlib.sha256(project_path.encode('utf-8')).hexdigest()[:16]
    return JSONResponse({"status": "ok", "state": tuning_mod.reset(DATA_DIR, pid)})

# --------------------------------------------------
# CI analyze
# --------------------------------------------------
@app.post("/ci/analyze")
async def ci_analyze(req: Request):
    body = await req.json()
    path = body.get("path") or str(BASE.parent)
    domain = body.get("domain") or "gaming"
    comp_targets = body.get("complianceTargets") or []
    # Orchestrate
    analysis = analyze_project(path)
    before = run_benchmark(domain, path)
    comp = check_compliance(domain, path)
    # Placeholder: we do not auto-apply; run validation pack
    out_dir = DATA_DIR / "ci" / str(int(time.time()))
    out_dir.mkdir(parents=True, exist_ok=True)
    val = validation_runner.run_validation_pack(domain, path, out_dir)
    after = run_benchmark(domain, path)
    cmp = compare_results(before, after)
    report = {"analysis": analysis, "benchmark": {"before": before, "after": after, "compare": cmp}, "compliance": comp, "validation": val}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))
    return JSONResponse({"status": "ok", "report_path": str(out_dir / 'report.json')})

# --------------------------------------------------
# Gemini status
# --------------------------------------------------
@app.get("/gemini_status")
async def gemini_status():
    try:
        if not _configure_gemini:
            return JSONResponse({"status": "ok", "configured": False, "error": "module not available"})
        genai, api_key = _configure_gemini()
        if not genai or not api_key:
            return JSONResponse({"status": "ok", "configured": False})
        # Minimal test
        if call_ai_provider:
            res = call_ai_provider("Say hello", provider="gemini")
        else:
            res = {"info": "configured", "note": "call_ai not available"}
        return JSONResponse({"status": "ok", "configured": True, "test": res})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

# --------------------------------------------------
# Feedback
# --------------------------------------------------
@app.post("/feedback")
async def feedback(req: Request):
    body = await req.json()
    store_feedback(body, DATA_DIR / "feedback.jsonl")
    return JSONResponse({"status": "ok"})

# --------------------------------------------------
# Profiler
# --------------------------------------------------
@app.post("/profile")
async def profile(req: Request):
    body = await req.json()
    target = body.get("path") or str(BASE.parent / "example_repo")
    res = run_profile_on_example(target)
    out = DATA_DIR / "last_profile.json"
    out.write_text(json.dumps(res, indent=2))
    return JSONResponse({"status": "ok", "profile": res})

# --------------------------------------------------
# Benchmarking
# --------------------------------------------------
@app.post("/benchmark")
async def benchmark(req: Request):
    body = await req.json()
    domain = body.get("domain")
    project_path = body.get("path") or str(BASE.parent / "example_repo")
    baseline_path = body.get("baselinePath")
    if not domain:
        raise HTTPException(status_code=400, detail="Provide 'domain' (gaming|hpc|robotics)")

    try:
        after = run_benchmark(domain, project_path, baseline_path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    rec_path = DATA_DIR / "benchmarks.jsonl"
    record = {"timestamp": time.time(), "domain": domain, "path": project_path, "result": after}
    record_result(rec_path, record)

    cmp = None
    before = body.get("before")
    if isinstance(before, dict):
        cmp = compare_results(before, after)

    return JSONResponse({"status": "ok", "benchmark": after, "compare": cmp})

# --------------------------------------------------
# Validation packs
# --------------------------------------------------
@app.post("/validate_pack")
async def validate_pack(req: Request):
    body = await req.json()
    domain = body.get("domain")
    project_path = body.get("path") or str(BASE.parent)
    series_id = body.get("seriesId") or str(int(time.time()))
    if not domain:
        raise HTTPException(status_code=400, detail="Provide 'domain'")
    out_dir = DATA_DIR / "validation" / series_id
    out_dir.mkdir(parents=True, exist_ok=True)
    result = validation_runner.run_validation_pack(domain, project_path, out_dir)
    index = {
        "seriesId": series_id,
        "artifacts": result.get("artifacts", []),
        "summary": result.get("summary", {}),
        "out_dir": str(out_dir)
    }
    (out_dir / "index.json").write_text(json.dumps(index, indent=2))
    return JSONResponse({"status": "ok", "index": index})

# --------------------------------------------------
# Compliance
# --------------------------------------------------
@app.post("/compliance")
async def compliance(req: Request):
    body = await req.json()
    domain = body.get("domain")
    project_path = body.get("path") or str(BASE.parent)
    if not domain:
        raise HTTPException(status_code=400, detail="Provide 'domain'")
    result = check_compliance(domain, project_path)
    out = DATA_DIR / "last_compliance.json"
    out.write_text(json.dumps(result, indent=2))
    return JSONResponse({"status": "ok", "compliance": result})

# --------------------------------------------------
# Workspace-wide Analysis Orchestrator
# --------------------------------------------------
@app.post("/workspace_analysis")
async def workspace_analysis(req: Request):
    try:
        body = await req.json()
        path = body.get("path") or str(BASE.parent)
        domain = body.get("domain")
        benchmark_domain = body.get("benchmarkDomain") or domain or "gaming"

        # 1) Analyze
        analysis = analyze_project(path)

        # 2) Profile (example) — use example_repo to ensure a stable target
        profile_target = str(BASE.parent / "example_repo")
        profile_res = run_profile_on_example(profile_target)

        # 3) Compliance
        compliance_res = check_compliance(benchmark_domain, path)

        # 4) Benchmark BEFORE
        before = run_benchmark(benchmark_domain, path)

        # 5) Suggestions (sample: use a simple file from example or provided)
        sample_file = str(BASE.parent / "example_repo" / "main.py")
        sample_text = Path(sample_file).read_text(encoding="utf-8") if Path(sample_file).exists() else ""
        suggestions = generate_suggestions(sample_file, sample_text, domain=benchmark_domain) if sample_text else []

        # 6) Benchmark AFTER (no automatic patch application here; placeholder)
        after = run_benchmark(benchmark_domain, path)
        comparison = compare_results(before, after)

        report = {
            "analysis": analysis,
            "profile": profile_res,
            "compliance": compliance_res,
            "benchmark": {"before": before, "after": after, "compare": comparison},
            "suggestions": suggestions,
        }
        reports_dir = DATA_DIR / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / "last_workspace_report.json"
        report_path.write_text(json.dumps(report, indent=2))

        # Build lightweight summary
        files_count = len(analysis.get("files", {})) if isinstance(analysis, dict) else 0
        suggest_count = len(suggestions)
        comp_warn = compliance_res.get("summary", {}).get("warn") if isinstance(compliance_res, dict) else None
        cmp = comparison if isinstance(comparison, dict) else {}
        summary = {
            "files_analyzed": files_count,
            "suggestions": suggest_count,
            "compliance_warn": comp_warn,
            "benchmark_metric": cmp.get("metric"),
            "benchmark_delta": cmp.get("delta"),
            "benchmark_improved": cmp.get("improved"),
        }
        return JSONResponse({"status": "ok", "report_path": str(report_path), "summary": summary})
    except Exception as e:
        return JSONResponse({"status": "error", "detail": str(e)}, status_code=500)

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.encoders import jsonable_encoder

import json
import os
import time
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

# ------------------------------
# Optional / best-effort imports
# ------------------------------
from analysis.analyzer import analyze_project
from analysis.suggestion import generate_suggestions, generate_suggestion_patch
from analysis.profiler import run_profile_on_example
from analysis.benchmark import run_benchmark, compare_results, record_result
from analysis.feedback import store_feedback
from analysis.compliance import check_compliance
from analysis.validation_packs import runner as validation_runner
from analysis import timeline as timeline_mod
from analysis import tuning as tuning_mod

try:
    from analysis.openai_integration import _configure_gemini, call_ai as call_ai_provider
except Exception:
    _configure_gemini = None
    call_ai_provider = None

try:
    from analysis.domain_detect import detect_domain
except Exception:
    detect_domain = None

try:
    from analysis.arch_guard import check_patch as arch_check
except Exception:
    arch_check = None


# ------------------------------
# App & paths
# ------------------------------
app = FastAPI()

BASE = Path(__file__).resolve().parent
EVENT_LOG = BASE / "events.log"
DATA_DIR = BASE / "data"
DATA_DIR.mkdir(exist_ok=True)

if not EVENT_LOG.exists():
    EVENT_LOG.write_text("")

events: List[Dict[str, Any]] = []
clients: set[WebSocket] = set()


def jresponse(payload: Dict[str, Any], status_code: int = 200) -> JSONResponse:
    """JSONResponse with jsonable_encoder so custom objects are safe."""
    return JSONResponse(content=jsonable_encoder(payload), status_code=status_code)


# ------------------------------
# Event & WebSocket
# ------------------------------
@app.post("/event")
async def receive_event(request: Request):
    payload = await request.json()
    payload["_received_at"] = time.time()
    events.append(payload)
    with EVENT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")
    return jresponse({"status": "ok"})


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            with EVENT_LOG.open("a", encoding="utf-8") as fh:
                fh.write(data + "\n")
    except WebSocketDisconnect:
        clients.discard(ws)


# ------------------------------
# Root page
# ------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    lines: List[str] = []
    if EVENT_LOG.exists():
        lines = EVENT_LOG.read_text().splitlines()[-50:]
    items = "".join(f"<li><pre>{line}</pre></li>" for line in lines[::-1])
    return HTMLResponse(
        f"""
        <h1>AI Refactor Backend</h1>
        <p>Endpoints: /event, /analyze, /suggest, /apply_patch, /timeline, /validate_pack, /workspace_analysis, ...</p>
        <ul>{items}</ul>
        """
    )


# ------------------------------
# /analyze
# ------------------------------
@app.post("/analyze")
async def analyze(req: Request):
    body = await req.json()
    proj = body.get("path")
    if not proj:
        raise HTTPException(status_code=400, detail="Provide 'path' in JSON body")

    result = analyze_project(proj)
    out = DATA_DIR / "last_analysis.json"
    out.write_text(json.dumps(jsonable_encoder(result), indent=2))
    return jresponse({"status": "ok", "result": result})


# ------------------------------
# /suggest
# ------------------------------
@app.post("/suggest")
async def suggest(req: Request):
    try:
        body = await req.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON in request body")

    file: Optional[str] = body.get("file")
    text: Optional[str] = body.get("text")
    domain: Optional[str] = body.get("domain")
    path: Optional[str] = body.get("path")
    targets: Optional[List[str]] = body.get("targets")
    compliance_targets: List[str] = body.get("complianceTargets") or []

    if not file or text is None:
        raise HTTPException(status_code=400, detail="Provide 'file' and 'text'")

    # Auto-detect domain if not provided
    detected_domain: Optional[str] = None
    if not domain and detect_domain:
        try:
            proj = path or (Path(file).parent.as_posix() if file else None)
            if proj:
                detected_domain = detect_domain(proj)
                if detected_domain:
                    domain = detected_domain
        except Exception:
            detected_domain = None

    # Default if still None
    if not domain:
        domain = "general"

    # Generate suggestions
    try:
        suggestions = generate_suggestions(
            filename=file,
            code=text,
            domain=domain,
            path=path,
            targets=targets,
            compliance_targets=compliance_targets,
        )
        if not isinstance(suggestions, list):
            suggestions = []
    except Exception as e:
        traceback.print_exc()
        return jresponse(
            {"status": "error", "detail": f"Error generating suggestions: {str(e)}"},
            status_code=500,
        )

    # Annotate detected_domain if present
    if detected_domain:
        for s in suggestions:
            s.setdefault("audit", {})
            s["audit"]["domain_detected"] = detected_domain

    # Tuning-based ordering (if enabled for this project)
    try:
        proj_root = path or (Path(file).parent.as_posix() if file else None)
        if proj_root:
            import hashlib

            pid = hashlib.sha256(proj_root.encode("utf-8")).hexdigest()[:16]
            state = tuning_mod.load_state(DATA_DIR, pid)
            if state.get("enabled", True):

                def score(sug: Dict[str, Any]) -> float:
                    audit = sug.get("audit") or {}
                    exp = audit.get("expected_impact") or {}
                    if isinstance(exp, dict) and exp:
                        rts = [
                            float(v.get("runtime_pct", 0.0))
                            for v in exp.values()
                            if isinstance(v, dict)
                        ]
                        mems = [
                            float(v.get("mem_pct", 0.0))
                            for v in exp.values()
                            if isinstance(v, dict)
                        ]
                        rt = sum(rts) / len(rts) if rts else 0.0
                        mem = sum(mems) / len(mems) if mems else 0.0
                    else:
                        rt = mem = 0.0

                    w = state.get("weights", {})
                    sc = -(
                        w.get("runtime", 1.0) * rt
                        + 0.5 * w.get("memory", 1.0) * mem
                    )

                    comp = audit.get("compliance") or {}
                    warn = (comp.get("summary") or {}).get("warn", 0)
                    if warn:
                        sc -= 10.0 * w.get("compliance", 1.0)

                    arch = audit.get("arch") or {}
                    if not arch.get("ok", True):
                        sc -= 5.0 * w.get("architecture", 1.0)

                    return sc

                suggestions = sorted(suggestions, key=score, reverse=True)
    except Exception:
        # Tuning errors should never break endpoint
        traceback.print_exc()

    # First suggestion summary (for quick UI)
    first_patch = ""
    first_reason = ""
    if suggestions:
        first = suggestions[0]
        if isinstance(first, dict):
            first_patch = first.get("patch") or ""
            first_reason = first.get("reason") or ""

    return jresponse(
        {
            "status": "ok",
            "suggestions": suggestions,
            "patch": first_patch,
            "reason": first_reason,
            "domain": domain,
        }
    )


# ------------------------------
# /apply_patch + timeline
# ------------------------------
@app.post("/apply_patch")
async def apply_patch(req: Request):
    body = await req.json()
    file: Optional[str] = body.get("file")
    new_text: Optional[str] = body.get("newText")
    patch_note: Optional[str] = body.get("patch")
    domain: Optional[str] = body.get("domain")
    project_path: str = (
        body.get("projectPath")
        or (str(Path(file).parent) if file else str(BASE.parent))
    )
    compliance_targets: List[str] = body.get("complianceTargets") or []

    if not file:
        raise HTTPException(status_code=400, detail="Provide 'file'")

    # Pre-apply architecture cues
    try:
        analysis = analyze_project(project_path)
    except Exception:
        analysis = {}
    arch_result: Optional[Dict[str, Any]] = None
    if patch_note and arch_check:
        try:
            graph = analysis.get("graph") if isinstance(analysis, dict) else None
            if graph:
                arch_raw = arch_check(graph, patch_note, domain or "")
                if hasattr(arch_raw, "__dict__") and not isinstance(arch_raw, dict):
                    arch_result = arch_raw.__dict__
                else:
                    arch_result = arch_raw
        except Exception:
            arch_result = {"ok": True}
    else:
        arch_result = {"ok": True}

    # Backup old text
    before_text = ""
    file_path = Path(file)
    if file_path.exists():
        before_text = file_path.read_text(encoding="utf-8")

    backup_path = DATA_DIR / "backups" / (file_path.name + ".bak")
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    backup_path.write_text(before_text, encoding="utf-8")

    # Apply new text
    if isinstance(new_text, str):
        file_path.write_text(new_text, encoding="utf-8")

    # Post-apply benchmark + compliance
    try:
        bench_after = run_benchmark(domain or "gaming", project_path)
    except Exception as e:
        return jresponse(
            {
                "status": "error",
                "stage": "benchmark",
                "detail": str(e),
            },
            status_code=500,
        )

    try:
        comp = check_compliance(
            domain or "gaming", project_path, targets=compliance_targets
        )
    except Exception as e:
        return jresponse(
            {
                "status": "error",
                "stage": "compliance",
                "detail": str(e),
            },
            status_code=500,
        )

    # Timeline event
    try:
        event = timeline_mod.append_event(
            DATA_DIR,
            project_path,
            {
                "type": "APPLIED",
                "file": file,
                "domain": domain,
                "message": patch_note or "",
                "cues": {"arch": arch_result},
                "result": {"benchmark": bench_after, "compliance": comp},
                "backup": str(backup_path),
            },
        )
    except Exception as e:
        return jresponse(
            {
                "status": "error",
                "stage": "timeline",
                "detail": str(e),
            },
            status_code=500,
        )

    return jresponse({"status": "ok", "event": event})


@app.get("/timeline")
async def timeline(project_path: str):
    data = timeline_mod.list_events(DATA_DIR, project_path)
    return jresponse({"status": "ok", **data})


@app.post("/flag_step")
async def flag_step(req: Request):
    body = await req.json()
    project_path = body.get("projectPath") or str(BASE.parent)
    file = body.get("file")
    reason = body.get("reason")
    ev = timeline_mod.append_event(
        DATA_DIR,
        project_path,
        {"type": "FLAGGED", "file": file, "message": reason or ""},
    )
    return jresponse({"status": "ok", "event": ev})


@app.post("/revert_step")
async def revert_step(req: Request):
    body = await req.json()
    project_path = body.get("projectPath") or str(BASE.parent)
    file = body.get("file")
    backup = body.get("backupPath")

    if backup and file and Path(backup).exists():
        Path(file).write_text(Path(backup).read_text(encoding="utf-8"), encoding="utf-8")

    ev = timeline_mod.append_event(
        DATA_DIR,
        project_path,
        {"type": "REVERTED", "file": file, "backup": backup},
    )
    return jresponse({"status": "ok", "event": ev})


# ------------------------------
# Tuning endpoints
# ------------------------------
@app.get("/tuning_state")
async def tuning_state(project_path: str):
    import hashlib

    pid = hashlib.sha256(project_path.encode("utf-8")).hexdigest()[:16]
    state = tuning_mod.load_state(DATA_DIR, pid)
    return jresponse({"status": "ok", "state": state})


@app.post("/tuning_toggle")
async def tuning_toggle(req: Request):
    body = await req.json()
    project_path = body.get("projectPath")
    enabled = bool(body.get("enabled", True))
    import hashlib

    pid = hashlib.sha256(project_path.encode("utf-8")).hexdigest()[:16]
    state = tuning_mod.toggle(DATA_DIR, pid, enabled)
    return jresponse({"status": "ok", "state": state})


@app.post("/tuning_reset")
async def tuning_reset(req: Request):
    body = await req.json()
    project_path = body.get("projectPath")
    import hashlib

    pid = hashlib.sha256(project_path.encode("utf-8")).hexdigest()[:16]
    state = tuning_mod.reset(DATA_DIR, pid)
    return jresponse({"status": "ok", "state": state})


# ------------------------------
# CI / analyze
# ------------------------------
@app.post("/ci/analyze")
async def ci_analyze(req: Request):
    body = await req.json()
    path = body.get("path") or str(BASE.parent)
    domain = body.get("domain") or "gaming"
    comp_targets = body.get("complianceTargets") or []

    analysis = analyze_project(path)
    before = run_benchmark(domain, path)
    comp = check_compliance(domain, path)
    out_dir = DATA_DIR / "ci" / str(int(time.time()))
    out_dir.mkdir(parents=True, exist_ok=True)
    val = validation_runner.run_validation_pack(domain, path, out_dir)
    after = run_benchmark(domain, path)
    cmp = compare_results(before, after)

    report = {
        "analysis": analysis,
        "benchmark": {"before": before, "after": after, "compare": cmp},
        "compliance": comp,
        "validation": val,
    }
    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(jsonable_encoder(report), indent=2))

    return jresponse({"status": "ok", "report_path": str(report_path)})


# ------------------------------
# Gemini status
# ------------------------------
@app.get("/gemini_status")
async def gemini_status():
    try:
        if not _configure_gemini:
            return jresponse(
                {
                    "status": "ok",
                    "configured": False,
                    "error": "module not available",
                }
            )

        genai, api_key = _configure_gemini()
        if not genai or not api_key:
            return jresponse({"status": "ok", "configured": False})

        if call_ai_provider:
            res = call_ai_provider("Say hello", provider="gemini")
        else:
            res = {"info": "configured", "note": "call_ai not available"}

        return jresponse({"status": "ok", "configured": True, "test": res})
    except Exception as e:
        traceback.print_exc()
        return jresponse(
            {"status": "error", "detail": str(e)},
            status_code=500,
        )


# ------------------------------
# Feedback
# ------------------------------
@app.post("/feedback")
async def feedback(req: Request):
    body = await req.json()
    store_feedback(body, DATA_DIR / "feedback.jsonl")
    return jresponse({"status": "ok"})


# ------------------------------
# Profiler
# ------------------------------
@app.post("/profile")
async def profile(req: Request):
    body = await req.json()
    target = body.get("path") or str(BASE.parent / "example_repo")
    res = run_profile_on_example(target)
    out = DATA_DIR / "last_profile.json"
    out.write_text(json.dumps(jsonable_encoder(res), indent=2))
    return jresponse({"status": "ok", "profile": res})


# ------------------------------
# Benchmark
# ------------------------------
@app.post("/benchmark")
async def benchmark(req: Request):
    body = await req.json()
    domain = body.get("domain")
    project_path = body.get("path") or str(BASE.parent / "example_repo")
    baseline_path = body.get("baselinePath")

    if not domain:
        raise HTTPException(
            status_code=400, detail="Provide 'domain' (gaming|hpc|robotics|...)"
        )

    after = run_benchmark(domain, project_path, baseline_path)
    rec_path = DATA_DIR / "benchmarks.jsonl"
    record = {
        "timestamp": time.time(),
        "domain": domain,
        "path": project_path,
        "result": after,
    }
    record_result(rec_path, record)

    cmp = None
    before = body.get("before")
    if isinstance(before, dict):
        cmp = compare_results(before, after)

    return jresponse({"status": "ok", "benchmark": after, "compare": cmp})


# ------------------------------
# Validation packs
# ------------------------------
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
        "out_dir": str(out_dir),
    }
    (out_dir / "index.json").write_text(json.dumps(jsonable_encoder(index), indent=2))
    return jresponse({"status": "ok", "index": index})


# ------------------------------
# Compliance
# ------------------------------
@app.post("/compliance")
async def compliance(req: Request):
    body = await req.json()
    domain = body.get("domain")
    project_path = body.get("path") or str(BASE.parent)

    if not domain:
        raise HTTPException(status_code=400, detail="Provide 'domain'")

    result = check_compliance(domain, project_path)
    out = DATA_DIR / "last_compliance.json"
    out.write_text(json.dumps(jsonable_encoder(result), indent=2))
    return jresponse({"status": "ok", "compliance": result})


# ------------------------------
# Workspace-wide Orchestrator
# ------------------------------
@app.post("/workspace_analysis")
async def workspace_analysis(req: Request):
    try:
        body = await req.json()
        path = body.get("path") or str(BASE.parent)
        domain = body.get("domain")
        benchmark_domain = body.get("benchmarkDomain") or domain or "gaming"

        # 1) Analyze
        analysis = analyze_project(path)

        # 2) Profile on example_repo for stability
        profile_target = str(BASE.parent / "example_repo")
        profile_res = run_profile_on_example(profile_target)

        # 3) Compliance
        compliance_res = check_compliance(benchmark_domain, path)

        # 4) Benchmark BEFORE
        before = run_benchmark(benchmark_domain, path)

        # 5) Suggestions on example file (if exists)
        sample_file = str(BASE.parent / "example_repo" / "main.py")
        sample_text = (
            Path(sample_file).read_text(encoding="utf-8")
            if Path(sample_file).exists()
            else ""
        )
        suggestions: List[Dict[str, Any]] = []
        if sample_text:
            suggestions = generate_suggestions(
                sample_file, sample_text, domain=benchmark_domain
            )

        # 6) Benchmark AFTER — no actual patch here, just repeat
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
        report_path.write_text(json.dumps(jsonable_encoder(report), indent=2))

        files_count = len(analysis.get("files", {})) if isinstance(analysis, dict) else 0
        suggest_count = len(suggestions)
        comp_warn = (
            compliance_res.get("summary", {}).get("warn")
            if isinstance(compliance_res, dict)
            else None
        )
        cmp = comparison if isinstance(comparison, dict) else {}

        summary = {
            "files_analyzed": files_count,
            "suggestions": suggest_count,
            "compliance_warn": comp_warn,
            "benchmark_metric": cmp.get("metric"),
            "benchmark_delta": cmp.get("delta"),
            "benchmark_improved": cmp.get("improved"),
        }

        return jresponse(
            {
                "status": "ok",
                "report_path": str(report_path),
                "summary": summary,
            }
        )

    except Exception as e:
        traceback.print_exc()
        return jresponse(
            {"status": "error", "detail": str(e)},
            status_code=500,
        )

from fastapi import FastAPI, Request, HTTPException, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse, JSONResponse
import os, json, time
from pathlib import Path

# import analysis modules
from analysis.analyzer import analyze_project
from analysis.suggestion import generate_suggestion_patch
from analysis.profiler import run_profile_on_example
from analysis.feedback import store_feedback

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
    if not file or not text:
        raise HTTPException(status_code=400, detail="Provide 'file' and 'text'")
    patch, reason = generate_suggestion_patch(file, text)
    return JSONResponse({"status": "ok", "patch": patch, "reason": reason})

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

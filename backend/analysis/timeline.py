import hashlib
import json
import time
from pathlib import Path
from typing import Dict, Any


def _project_id(project_path: str) -> str:
    return hashlib.sha256(project_path.encode("utf-8")).hexdigest()[:16]


def _chain_hash(prev_hash: str, payload: Dict[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((prev_hash or "").encode("utf-8"))
    h.update(json.dumps(payload, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def append_event(data_dir: Path, project_path: str, event: Dict[str, Any]) -> Dict[str, Any]:
    pid = _project_id(project_path)
    tdir = data_dir / "timeline"
    tdir.mkdir(parents=True, exist_ok=True)
    log = tdir / f"{pid}.jsonl"

    prev_hash = ""
    if log.exists():
        try:
            *_, last = log.read_text(encoding="utf-8").strip().splitlines()
            prev = json.loads(last)
            prev_hash = prev.get("chain_hash", "")
        except Exception:
            prev_hash = ""

    event = dict(event)
    event["timestamp"] = time.time()
    payload = {k: v for k, v in event.items() if k != "chain_hash"}
    event["chain_hash"] = _chain_hash(prev_hash, payload)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event) + "\n")
    return event


essential_fields = ["type", "file", "domain", "cues", "result"]


def list_events(data_dir: Path, project_path: str) -> Dict[str, Any]:
    pid = _project_id(project_path)
    log = data_dir / "timeline" / f"{pid}.jsonl"
    events = []
    if log.exists():
        for line in log.read_text(encoding="utf-8").splitlines():
            try:
                events.append(json.loads(line))
            except Exception:
                continue
    # Summarize lightweight for UI
    summary = [{
        "ts": e.get("timestamp"),
        "type": e.get("type"),
        "file": e.get("file"),
        "message": e.get("message"),
        "chain_hash": e.get("chain_hash")
    } for e in events]
    return {"events": events, "summary": summary}

import json
from pathlib import Path
from typing import Dict, Any

DEFAULT = {
    "enabled": True,
    "weights": {
        "runtime": 1.0,
        "memory": 1.0,
        "compliance": 1.0,
        "architecture": 1.0
    }
}


def _path(data_dir: Path, project_id: str) -> Path:
    p = data_dir / "tuning"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{project_id}.json"


def load_state(data_dir: Path, project_id: str) -> Dict[str, Any]:
    f = _path(data_dir, project_id)
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return dict(DEFAULT)


def save_state(data_dir: Path, project_id: str, state: Dict[str, Any]) -> None:
    f = _path(data_dir, project_id)
    f.write_text(json.dumps(state, indent=2))


def toggle(data_dir: Path, project_id: str, enabled: bool) -> Dict[str, Any]:
    s = load_state(data_dir, project_id)
    s["enabled"] = bool(enabled)
    save_state(data_dir, project_id, s)
    return s


def reset(data_dir: Path, project_id: str) -> Dict[str, Any]:
    save_state(data_dir, project_id, DEFAULT)
    return dict(DEFAULT)


def update_from_feedback(data_dir: Path, project_id: str, feedback: Dict[str, Any]) -> Dict[str, Any]:
    """
    feedback: {accepted: bool, benchmark_delta: float, compliance_warn: int}
    Adjust weights slightly based on feedback.
    """
    s = load_state(data_dir, project_id)
    if not s.get("enabled", True):
        return s
    w = s.get("weights", {})
    if feedback.get("accepted"):
        # Reward runtime improvements
        delta = feedback.get("benchmark_delta")
        if isinstance(delta, (int, float)):
            if delta and delta > 0:
                w["runtime"] = min(2.0, w.get("runtime", 1.0) + 0.05)
            elif delta and delta < 0:
                w["runtime"] = max(0.5, w.get("runtime", 1.0) - 0.05)
        # Penalize if compliance warns
        warns = feedback.get("compliance_warn") or 0
        if warns > 0:
            w["compliance"] = min(2.0, w.get("compliance", 1.0) + 0.1)
            w["runtime"] = max(0.5, w.get("runtime", 1.0) - 0.05)
    else:
        # If rejected, slightly reduce runtime bias
        w["runtime"] = max(0.5, w.get("runtime", 1.0) - 0.02)
    s["weights"] = w
    save_state(data_dir, project_id, s)
    return s

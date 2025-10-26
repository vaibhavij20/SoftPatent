from pathlib import Path
from typing import Dict, Any, List
import json
import random
import time

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except Exception:
    plt = None


def _simulate_fps_series(n: int = 60) -> List[float]:
    base = random.uniform(45.0, 60.0)
    return [round(base + random.uniform(-3.0, 3.0), 2) for _ in range(n)]


def run(project_path: str, out_dir: Path) -> Dict[str, Any]:
    ts = int(time.time())
    series = _simulate_fps_series(120)
    data_path = out_dir / f"gaming_fps_{ts}.json"
    data = {"metric": "fps", "series": series, "avg": round(sum(series)/len(series), 2)}
    data_path.write_text(json.dumps(data, indent=2))

    artifacts = [str(data_path)]
    if plt:
        fig = plt.figure(figsize=(6, 3))
        plt.plot(series)
        plt.title("Gaming FPS (simulated)")
        plt.xlabel("Frame")
        plt.ylabel("FPS")
        img_path = out_dir / f"gaming_fps_{ts}.png"
        fig.tight_layout()
        fig.savefig(img_path)
        plt.close(fig)
        artifacts.append(str(img_path))

    summary = {"avg_fps": data["avg"], "frames": len(series)}
    return {"artifacts": artifacts, "summary": summary}

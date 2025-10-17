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


def _simulate_ate_series(n: int = 60) -> List[float]:
    base = random.uniform(0.3, 0.8)  # meters, lower is better
    return [round(max(0.05, base + random.uniform(-0.1, 0.1)), 3) for _ in range(n)]


def run(project_path: str, out_dir: Path) -> Dict[str, Any]:
    ts = int(time.time())
    series = _simulate_ate_series(120)
    data_path = out_dir / f"robotics_slam_ate_{ts}.json"
    data = {"metric": "slam_ate_m", "series": series, "avg": round(sum(series)/len(series), 3)}
    data_path.write_text(json.dumps(data, indent=2))

    artifacts = [str(data_path)]
    if plt:
        fig = plt.figure(figsize=(6, 3))
        plt.plot(series)
        plt.title("Robotics SLAM ATE (simulated)")
        plt.xlabel("Frame")
        plt.ylabel("ATE (m)")
        img_path = out_dir / f"robotics_slam_ate_{ts}.png"
        fig.tight_layout()
        fig.savefig(img_path)
        plt.close(fig)
        artifacts.append(str(img_path))

    summary = {"avg_slam_ate_m": data["avg"], "frames": len(series)}
    return {"artifacts": artifacts, "summary": summary}

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


def _simulate_latency_series(n: int = 60) -> List[float]:
    base = random.uniform(80.0, 150.0)  # ms
    return [round(base + random.uniform(-15.0, 15.0), 1) for _ in range(n)]


def run(project_path: str, out_dir: Path) -> Dict[str, Any]:
    ts = int(time.time())
    series = _simulate_latency_series(120)
    data_path = out_dir / f"speech_therapy_latency_{ts}.json"
    data = {"metric": "inference_latency_ms", "series": series, "avg": round(sum(series)/len(series), 1)}
    data_path.write_text(json.dumps(data, indent=2))

    artifacts = [str(data_path)]
    if plt:
        fig = plt.figure(figsize=(6, 3))
        plt.plot(series)
        plt.title("Speech Therapy Inference Latency (simulated)")
        plt.xlabel("Frame")
        plt.ylabel("Latency (ms)")
        img_path = out_dir / f"speech_therapy_latency_{ts}.png"
        fig.tight_layout()
        fig.savefig(img_path)
        plt.close(fig)
        artifacts.append(str(img_path))

    summary = {"avg_inference_latency_ms": data["avg"], "frames": len(series)}
    return {"artifacts": artifacts, "summary": summary}

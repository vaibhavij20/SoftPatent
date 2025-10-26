from pathlib import Path
from typing import Dict, Any
import json
import random
import time

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
except Exception:
    plt = None


def _simulate_gflops_series(n: int = 30) -> list[float]:
    base = random.uniform(20.0, 80.0)
    return [round(base + random.uniform(-5.0, 5.0), 2) for _ in range(n)]


def run(project_path: str, out_dir: Path) -> Dict[str, Any]:
    ts = int(time.time())
    series = _simulate_gflops_series(60)
    data_path = out_dir / f"hpc_linpack_{ts}.json"
    data = {"metric": "linpack_gflops", "series": series, "avg": round(sum(series)/len(series), 2)}
    data_path.write_text(json.dumps(data, indent=2))

    artifacts = [str(data_path)]
    if plt:
        fig = plt.figure(figsize=(6, 3))
        plt.plot(series)
        plt.title("HPC LINPACK GFLOPS (simulated)")
        plt.xlabel("Trial")
        plt.ylabel("GFLOPS")
        img_path = out_dir / f"hpc_linpack_{ts}.png"
        fig.tight_layout()
        fig.savefig(img_path)
        plt.close(fig)
        artifacts.append(str(img_path))

    summary = {"avg_gflops": data["avg"], "trials": len(series)}
    return {"artifacts": artifacts, "summary": summary}

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


def _simulate_telemetry_series(n: int = 100) -> list[float]:
    base = random.uniform(0.0, 1.0)
    return [round(base + random.uniform(-0.2, 0.2), 3) for _ in range(n)]


def run(project_path: str, out_dir: Path) -> Dict[str, Any]:
    ts = int(time.time())
    series = _simulate_telemetry_series(200)
    data_path = out_dir / f"satellite_telemetry_{ts}.json"
    data = {"metric": "telemetry_signal", "series": series, "std": round((sum((x - sum(series)/len(series))**2 for x in series)/len(series))**0.5, 4)}
    data_path.write_text(json.dumps(data, indent=2))

    artifacts = [str(data_path)]
    if plt:
        fig = plt.figure(figsize=(6, 3))
        plt.plot(series)
        plt.title("Satellite Telemetry Simulation (simulated)")
        plt.xlabel("Tick")
        plt.ylabel("Signal")
        img_path = out_dir / f"satellite_telemetry_{ts}.png"
        fig.tight_layout()
        fig.savefig(img_path)
        plt.close(fig)
        artifacts.append(str(img_path))

    summary = {"std": data["std"], "samples": len(series)}
    return {"artifacts": artifacts, "summary": summary}

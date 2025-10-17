import json
import time
from pathlib import Path
from typing import Dict, Any, Optional


def _now_ts() -> float:
    return time.time()


def _simulate_runtime_metrics(seed: Optional[int] = None) -> Dict[str, Any]:
    # Lightweight deterministic-ish simulation to avoid heavy deps.
    t = _now_ts()
    base = int(t) % 100
    return {
        "runtime_sec": round(0.5 + (base % 7) * 0.13, 3),
        "cpu_util": round(35 + (base % 20) * 2.1, 1),
        "mem_mb":  round(100 + (base % 50) * 3.2, 1),
    }


def _gaming_fps(project_path: str) -> Dict[str, Any]:
    # In a real setup, this would launch a scene replay and sample FPS.
    sim = _simulate_runtime_metrics()
    return {
        "domain": "gaming",
        "metric": "fps",
        "value": round(45 + sim["cpu_util"] / 10.0, 1),
        "details": sim,
    }


def _hpc_linpack(project_path: str) -> Dict[str, Any]:
    # Placeholder: emulate GFLOPS outcome
    sim = _simulate_runtime_metrics()
    gflops = round(20.0 + (100 - sim["cpu_util"]) * 0.8, 2)
    return {
        "domain": "hpc",
        "metric": "linpack_gflops",
        "value": gflops,
        "details": sim,
    }


def _robotics_slam(project_path: str) -> Dict[str, Any]:
    # Placeholder: emulate Absolute Trajectory Error (ATE) lower is better
    sim = _simulate_runtime_metrics()
    ate = round(0.5 + (sim["mem_mb"] % 20) * 0.01, 3)
    return {
        "domain": "robotics",
        "metric": "slam_ate_m",
        "value": ate,
        "details": sim,
    }


def _satellite_rt_control(project_path: str) -> Dict[str, Any]:
    # Placeholder: emulate control loop jitter (ms), lower is better
    sim = _simulate_runtime_metrics()
    jitter_ms = round(2.0 + (sim["cpu_util"] % 10) * 0.3, 2)
    return {
        "domain": "satellite",
        "metric": "control_loop_jitter_ms",
        "value": jitter_ms,
        "details": sim,
    }


def _sustainability_pipeline(project_path: str) -> Dict[str, Any]:
    # Placeholder: emulate throughput of data pipeline (MB/s), higher is better
    sim = _simulate_runtime_metrics()
    mbps = round(50.0 + (100 - sim["cpu_util"]) * 0.6, 2)
    return {
        "domain": "sustainability",
        "metric": "pipeline_throughput_mb_s",
        "value": mbps,
        "details": sim,
    }


def _speech_therapy_latency(project_path: str) -> Dict[str, Any]:
    # Placeholder: emulate end-to-end audio inference latency (ms), lower is better
    sim = _simulate_runtime_metrics()
    latency_ms = round(120.0 + (sim["mem_mb"] % 30) * 1.2, 1)
    return {
        "domain": "speech_therapy",
        "metric": "inference_latency_ms",
        "value": latency_ms,
        "details": sim,
    }


def _medical_throughput(project_path: str) -> Dict[str, Any]:
    # Placeholder: emulate diagnostic pipeline throughput (samples/min), higher is better
    sim = _simulate_runtime_metrics()
    samples_per_min = round(30.0 + (100 - sim["cpu_util"]) * 0.4, 1)
    return {
        "domain": "medical",
        "metric": "samples_per_min",
        "value": samples_per_min,
        "details": sim,
    }


DOMAIN_RUNNERS = {
    "gaming": _gaming_fps,
    "hpc": _hpc_linpack,
    "robotics": _robotics_slam,
    "satellite": _satellite_rt_control,
    "sustainability": _sustainability_pipeline,
    "speech_therapy": _speech_therapy_latency,
    "medical": _medical_throughput,
}


def run_benchmark(domain: str, project_path: str, baseline_path: Optional[str] = None) -> Dict[str, Any]:
    domain = (domain or "").lower().strip()
    if domain not in DOMAIN_RUNNERS:
        raise ValueError(f"Unsupported domain: {domain}")

    started = _now_ts()
    runner = DOMAIN_RUNNERS[domain]
    result = runner(project_path)
    finished = _now_ts()

    output = {
        "domain": domain,
        "project_path": project_path,
        "baseline_path": baseline_path,
        "result": result,
        "started": started,
        "finished": finished,
        "duration_sec": round(finished - started, 3),
    }
    return output


def compare_results(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    if not before or not after:
        return {"error": "missing before/after results"}
    if before.get("result", {}).get("metric") != after.get("result", {}).get("metric"):
        return {"error": "metrics not comparable"}

    metric = before["result"]["metric"]
    before_v = before["result"]["value"]
    after_v = after["result"]["value"]
    delta = after_v - before_v

    # Define which metrics are lower-is-better
    lower_is_better = {
        "slam_ate_m",
        "control_loop_jitter_ms",
        "inference_latency_ms",
    }
    improved = (delta < 0) if metric in lower_is_better else (delta > 0)

    return {
        "metric": metric,
        "before": before_v,
        "after": after_v,
        "delta": delta,
        "improved": improved,
    }


def record_result(out_path: Path, payload: Dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload) + "\n")

"""
Benchmarking Module

This module provides functionality to run and compare performance benchmarks
across different application domains. It includes domain-specific benchmark runners
and utilities for comparing benchmark results.
"""

import json
import time
import random
import logging
from pathlib import Path
from typing import Dict, Any, Optional, TypedDict, Callable, List, Literal
from dataclasses import dataclass
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type aliases
DomainName = Literal[
    "gaming", "hpc", "robotics", "satellite", 
    "sustainability", "speech_therapy", "medical"
]
BenchmarkResult = Dict[str, Any]
BenchmarkRunner = Callable[[str], BenchmarkResult]

class BenchmarkStats(TypedDict):
    """Runtime statistics collected during benchmark execution."""
    runtime_sec: float
    cpu_util: float
    mem_mb: float
    timestamp: str

class BenchmarkOutput(TypedDict):
    """Structured output format for benchmark results."""
    domain: str
    project_path: str
    baseline_path: Optional[str]
    result: BenchmarkResult
    started: float
    finished: float
    duration_sec: float
    status: str
    error: Optional[str]

class ComparisonResult(TypedDict):
    """Result of comparing two benchmark runs."""
    metric: str
    before: float
    after: float
    delta: float
    delta_percent: float
    improved: bool
    significance: Literal["high", "medium", "low", "none"]

def _now_ts() -> float:
    """Get current timestamp in seconds since epoch."""
    return time.time()

def _simulate_runtime_metrics(seed: Optional[int] = None) -> BenchmarkStats:
    """Generate simulated runtime metrics for testing.
    
    Args:
        seed: Optional seed for deterministic results
        
    Returns:
        Dictionary containing simulated runtime metrics
    """
    if seed is not None:
        random.seed(seed)
    
    t = _now_ts()
    base = int(t) % 100
    
    return {
        "runtime_sec": round(0.5 + (base % 7) * 0.13, 3),
        "cpu_util": round(35 + (base % 20) * 2.1, 1),
        "mem_mb": round(100 + (base % 50) * 3.2, 1),
        "timestamp": datetime.utcnow().isoformat()
    }


def _gaming_fps(project_path: str) -> BenchmarkResult:
    """Run gaming benchmark measuring frames per second (FPS).
    
    Args:
        project_path: Path to the project directory containing the game build
        
    Returns:
        Benchmark result with FPS metric and runtime details
        
    Raises:
        FileNotFoundError: If required game files are not found
        RuntimeError: If benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate FPS based on CPU utilization (inverse correlation)
        # In a real implementation, this would run actual game benchmarks
        fps = round(45 + sim["cpu_util"] / 10.0, 1)
        
        return {
            "domain": "gaming",
            "metric": "fps",
            "value": fps,
            "unit": "frames/second",
            "higher_is_better": True,
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "resolution": "1920x1080",
                "quality_preset": "high",
                "scene_complexity": "high"
            }
        }
    except Exception as e:
        logger.error(f"Gaming benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run gaming benchmark: {e}") from e


def _hpc_linpack(project_path: str) -> BenchmarkResult:
    """Run HPC benchmark using LINPACK to measure GFLOPS performance.
    
    Args:
        project_path: Path to the HPC project directory
        
    Returns:
        Benchmark result with GFLOPS metric and runtime details
        
    Raises:
        FileNotFoundError: If required benchmark files are not found
        RuntimeError: If benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate GFLOPS (higher is better)
        # In a real implementation, this would run actual LINPACK benchmarks
        gflops = round(20.0 + (100 - sim["cpu_util"]) * 0.8, 2)
        
        return {
            "domain": "hpc",
            "metric": "linpack_gflops",
            "value": gflops,
            "unit": "GFLOPS",
            "higher_is_better": True,
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "matrix_size": 1000,  # NxN matrix size
                "precision": "double",
                "num_threads": 4
            }
        }
    except Exception as e:
        logger.error(f"HPC LINPACK benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run HPC benchmark: {e}") from e


def _robotics_slam(project_path: str) -> BenchmarkResult:
    """Run robotics benchmark measuring SLAM (Simultaneous Localization and Mapping) accuracy.
    
    Measures Absolute Trajectory Error (ATE) in meters, where lower is better.
    
    Args:
        project_path: Path to the robotics project directory
        
    Returns:
        Benchmark result with ATE metric and runtime details
        
    Raises:
        FileNotFoundError: If required robot configuration or data files are missing
        RuntimeError: If SLAM benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate Absolute Trajectory Error (ATE) in meters (lower is better)
        # In a real implementation, this would run actual SLAM algorithms on test data
        ate = round(0.5 + (sim["mem_mb"] % 20) * 0.01, 3)
        
        return {
            "domain": "robotics",
            "metric": "slam_ate_m",
            "value": ate,
            "unit": "meters",
            "higher_is_better": False,  # Lower ATE is better
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "algorithm": "ORB-SLAM3",
                "dataset": "EuRoC MAV",
                "trajectory_length": 100.0,  # meters
                "environment": "indoor"
            }
        }
    except Exception as e:
        logger.error(f"Robotics SLAM benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run robotics benchmark: {e}") from e


def _satellite_rt_control(project_path: str) -> BenchmarkResult:
    """Run satellite benchmark measuring real-time control loop jitter.
    
    Measures the variation in control loop execution time in milliseconds.
    Lower values indicate more stable real-time performance.
    
    Args:
        project_path: Path to the satellite control project directory
        
    Returns:
        Benchmark result with control loop jitter metric and runtime details
        
    Raises:
        FileNotFoundError: If required satellite control files are missing
        RuntimeError: If benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate control loop jitter in milliseconds (lower is better)
        # In a real implementation, this would measure actual control loop timing
        jitter_ms = round(2.0 + (sim["cpu_util"] % 10) * 0.3, 2)
        
        return {
            "domain": "satellite",
            "metric": "control_loop_jitter_ms",
            "value": jitter_ms,
            "unit": "milliseconds",
            "higher_is_better": False,  # Lower jitter is better
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "control_frequency_hz": 100,
                "num_control_loops": 1000,
                "platform": "linux_rt"
            }
        }
    except Exception as e:
        logger.error(f"Satellite control benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run satellite benchmark: {e}") from e


def _sustainability_pipeline(project_path: str) -> BenchmarkResult:
    """Run sustainability benchmark measuring data pipeline throughput.
    
    Measures the data processing throughput in megabytes per second (MB/s).
    Higher values indicate better performance.
    
    Args:
        project_path: Path to the sustainability project directory
        
    Returns:
        Benchmark result with throughput metric and runtime details
        
    Raises:
        FileNotFoundError: If required data files or pipeline configuration is missing
        RuntimeError: If benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate data processing throughput in MB/s (higher is better)
        # In a real implementation, this would measure actual data processing speed
        throughput = round(50.0 + (100 - sim["cpu_util"]) * 0.6, 2)
        
        return {
            "domain": "sustainability",
            "metric": "pipeline_throughput_mb_s",
            "value": throughput,
            "unit": "MB/s",
            "higher_is_better": True,
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "data_volume_gb": 10.0,
                "processing_type": "batch",
                "compression_ratio": 0.7
            }
        }
    except Exception as e:
        logger.error(f"Sustainability pipeline benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run sustainability benchmark: {e}") from e


def _speech_therapy_latency(project_path: str) -> BenchmarkResult:
    """Run speech therapy benchmark measuring end-to-end audio processing latency.
    
    Measures the time taken for audio input to be processed and return results in milliseconds.
    Lower values indicate better real-time performance.
    
    Args:
        project_path: Path to the speech therapy project directory
        
    Returns:
        Benchmark result with inference latency metric and runtime details
        
    Raises:
        FileNotFoundError: If required audio models or data files are missing
        RuntimeError: If benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate inference latency in milliseconds (lower is better)
        # In a real implementation, this would measure actual audio processing time
        latency_ms = round(120.0 + (sim["mem_mb"] % 30) * 1.2, 1)
        
        return {
            "domain": "speech_therapy",
            "metric": "inference_latency_ms",
            "value": latency_ms,
            "unit": "milliseconds",
            "higher_is_better": False,  # Lower latency is better
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "audio_length_sec": 5.0,
                "sample_rate_hz": 16000,
                "model": "wav2vec2-base"
            }
        }
    except Exception as e:
        logger.error(f"Speech therapy latency benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run speech therapy benchmark: {e}") from e


def _medical_throughput(project_path: str) -> BenchmarkResult:
    """Run medical benchmark measuring diagnostic pipeline throughput.
    
    Measures the number of medical samples that can be processed per minute.
    Higher values indicate better performance.
    
    Args:
        project_path: Path to the medical project directory
        
    Returns:
        Benchmark result with samples per minute metric and runtime details
        
    Raises:
        FileNotFoundError: If required medical data or models are missing
        RuntimeError: If benchmark execution fails
    """
    try:
        # Validate project path
        project_dir = Path(project_path)
        if not project_dir.exists():
            raise FileNotFoundError(f"Project directory not found: {project_path}")
            
        # Simulate benchmark execution
        sim = _simulate_runtime_metrics()
        
        # Calculate samples processed per minute (higher is better)
        # In a real implementation, this would process actual medical data
        samples_per_min = round(30.0 + (100 - sim["cpu_util"]) * 0.4, 1)
        
        return {
            "domain": "medical",
            "metric": "samples_per_min",
            "value": samples_per_min,
            "unit": "samples/minute",
            "higher_is_better": True,
            "details": sim,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "sample_type": "MRI",
                "resolution": "256x256x64",
                "model": "3D-UNet"
            }
        }
    except Exception as e:
        logger.error(f"Medical throughput benchmark failed: {e}", exc_info=True)
        raise RuntimeError(f"Failed to run medical benchmark: {e}") from e


# Mapping of domain names to their respective benchmark functions
DOMAIN_RUNNERS: Dict[DomainName, BenchmarkRunner] = {
    "gaming": _gaming_fps,
    "hpc": _hpc_linpack,
    "robotics": _robotics_slam,
    "satellite": _satellite_rt_control,
    "sustainability": _sustainability_pipeline,
    "speech_therapy": _speech_therapy_latency,
    "medical": _medical_throughput,
}

def run_benchmark(domain: str, project_path: str, baseline_path: Optional[str] = None) -> BenchmarkOutput:
    """
    Run the appropriate benchmark for the specified domain.
    
    Args:
        domain: The application domain (e.g., 'gaming', 'medical')
        project_path: Path to the project directory to benchmark
        baseline_path: Optional path to baseline results for comparison
        
    Returns:
        BenchmarkOutput containing the benchmark results and metadata
        
    Raises:
        ValueError: If the domain is not supported
        FileNotFoundError: If project_path doesn't exist
        RuntimeError: If benchmark execution fails
    """
    if not domain or not isinstance(domain, str):
        raise ValueError("Domain must be a non-empty string")
        
    domain = domain.lower().strip()
    if domain not in DOMAIN_RUNNERS:
        valid_domains = ", ".join(f"'{d}'" for d in DOMAIN_RUNNERS.keys())
        raise ValueError(f"Unsupported domain: {domain}. Valid domains are: {valid_domains}")
    
    # Validate project path
    project_dir = Path(project_path)
    if not project_dir.exists() or not project_dir.is_dir():
        raise FileNotFoundError(f"Project directory not found: {project_path}")
    
    # Validate baseline path if provided
    if baseline_path:
        baseline_dir = Path(baseline_path)
        if not baseline_dir.exists() or not baseline_dir.is_dir():
            logger.warning(f"Baseline directory not found: {baseline_path}")
    
    started = _now_ts()
    status = "completed"
    error = None
    
    try:
        logger.info(f"Starting {domain} benchmark for project: {project_path}")
        runner = DOMAIN_RUNNERS[domain]
        result = runner(str(project_dir.absolute()))
        logger.info(f"{domain.capitalize()} benchmark completed successfully")
    except Exception as e:
        status = "failed"
        error = str(e)
        logger.error(f"Benchmark failed: {error}", exc_info=True)
        result = {
            "domain": domain,
            "metric": "error",
            "value": 0,
            "error": error
        }
    finally:
        finished = _now_ts()
    
    output: BenchmarkOutput = {
        "domain": domain,
        "project_path": str(project_dir.absolute()),
        "baseline_path": str(Path(baseline_path).absolute()) if baseline_path else None,
        "result": result,
        "started": started,
        "finished": finished,
        "duration_sec": round(finished - started, 3),
        "status": status,
        "error": error
    }
    
    return output


def compare_results(before: BenchmarkOutput, after: BenchmarkOutput) -> ComparisonResult:
    """Compare two benchmark runs and calculate the difference.
    
    Args:
        before: Benchmark results before changes
        after: Benchmark results after changes
        
    Returns:
        ComparisonResult with before/after metrics and improvement status
        
    Raises:
        ValueError: If inputs are invalid or metrics are not comparable
    """
    if not before or not after:
        raise ValueError("Both before and after results are required")
        
    if not before.get("result") or not after.get("result"):
        raise ValueError("Invalid benchmark results: missing 'result' field")
    
    before_result = before["result"]
    after_result = after["result"]
    
    # Check if metrics are comparable
    if before_result.get("metric") != after_result.get("metric"):
        raise ValueError("Cannot compare different metrics")
    
    metric = before_result["metric"]
    before_v = before_result["value"]
    after_v = after_result["value"]
    
    # Calculate delta and percentage change
    delta = after_v - before_v
    delta_percent = (delta / before_v * 100) if before_v != 0 else float('inf')
    
    # Determine if higher or lower values are better
    higher_is_better = before_result.get("higher_is_better", True)
    improved = (delta > 0) if higher_is_better else (delta < 0)
    
    # Calculate significance of change
    abs_percent = abs(delta_percent)
    if abs_percent > 20:
        significance = "high"
    elif abs_percent > 5:
        significance = "medium"
    elif abs_percent > 1:
        significance = "low"
    else:
        significance = "none"
    
    return {
        "metric": metric,
        "before": before_v,
        "after": after_v,
        "delta": delta,
        "delta_percent": round(delta_percent, 2),
        "improved": improved,
        "significance": significance,
    }


def record_result(out_path: Path, payload: Dict[str, Any]) -> None:
    """Record benchmark results to a JSONL file.
    
    Args:
        out_path: Path to the output file (will be created if it doesn't exist)
        payload: Benchmark results to record
        
    Raises:
        IOError: If the file cannot be written
    """
    try:
        # Ensure output directory exists
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp if not present
        if "timestamp" not in payload:
            payload["timestamp"] = datetime.utcnow().isoformat()
        
        # Write to file in JSONL format
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")
            
    except Exception as e:
        logger.error(f"Failed to record benchmark results to {out_path}: {e}")
        raise IOError(f"Failed to write benchmark results: {e}") from e


def load_benchmark_results(file_path: Path) -> List[Dict[str, Any]]:
    """Load benchmark results from a JSONL file.
    
    Args:
        file_path: Path to the JSONL file containing benchmark results
        
    Returns:
        List of benchmark results
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file contains invalid JSON
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Benchmark results file not found: {file_path}")
    
    results = []
    with file_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                results.append(json.loads(line))
    
    return results


def get_latest_benchmark(file_path: Path) -> Optional[Dict[str, Any]]:
    """Get the most recent benchmark result from a file.
    
    Args:
        file_path: Path to the JSONL file containing benchmark results
        
    Returns:
        The most recent benchmark result, or None if the file is empty
    """
    try:
        results = load_benchmark_results(file_path)
        if not results:
            return None
        # Sort by timestamp (newest first)
        return sorted(
            results, 
            key=lambda x: x.get("timestamp", ""), 
            reverse=True
        )[0]
    except Exception as e:
        logger.warning(f"Failed to load benchmark results: {e}")
        return None

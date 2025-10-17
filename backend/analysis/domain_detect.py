import os
from pathlib import Path
from typing import Optional

CUES = {
    "gaming": ["render", "shader", "opengl", "vulkan", "godot", "unity", "unreal", "fps"],
    "robotics": ["ros", "rclpy", "rospy", "navigation", "gazebo", "sensor", "urdf"],
    "hpc": ["blas", "openmp", "cuda", "cupy", "numba", "vectorize", "simd"],
    "medical": ["iec62304", "hl7", "dicom", "device", "patient", "audit", "compliance"],
    "satellite": ["telemetry", "attitude", "orbit", "aocs", "rtos", "stm32", "canbus", "flight"],
    "sustainability": ["climate", "weather", "meteorology", "sensor", "ingestion", "pipeline", "forecast"],
    "speech_therapy": ["audio", "speech", "asr", "stt", "latency", "phoneme", "therapy"],
}


def detect_domain(project_path: Optional[str]) -> Optional[str]:
    if not project_path:
        return None
    p = Path(project_path)
    if not p.exists():
        return None
    # search directory names and some files for cues
    try:
        for root, dirs, files in os.walk(p):
            lowroot = root.lower()
            # directory name cues
            for k, words in CUES.items():
                if any(w in lowroot for w in words):
                    return k
            # file name cues
            for f in files:
                lf = f.lower()
                for k, words in CUES.items():
                    if any(w in lf for w in words):
                        return k
            # Limit scan depth
            if root != str(p) and root.count(os.sep) - str(p).count(os.sep) > 2:
                del dirs[:]  # prune deeper
    except Exception:
        return None
    return None

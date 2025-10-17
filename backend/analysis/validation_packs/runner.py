from pathlib import Path
from typing import Dict, Any
from . import gaming, hpc, satellite
from . import sustainability, speech_therapy, medical
try:
    from . import robotics
except Exception:
    robotics = None

PACKS = {
    "gaming": gaming.run,
    "hpc": hpc.run,
    "satellite": satellite.run,
    "sustainability": sustainability.run,
    "speech_therapy": speech_therapy.run,
    "medical": medical.run,
}
if robotics is not None:
    PACKS["robotics"] = robotics.run


def run_validation_pack(domain: str, project_path: str, out_dir: Path) -> Dict[str, Any]:
    domain = (domain or "").lower()
    fn = PACKS.get(domain)
    if not fn:
        return {"error": f"unsupported domain: {domain}", "artifacts": [], "summary": {}}
    out_dir.mkdir(parents=True, exist_ok=True)
    return fn(project_path, out_dir)

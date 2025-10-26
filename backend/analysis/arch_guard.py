from typing import Dict, Any, List

# Simple rule-based architecture guard. Replaceable with GNN later.
# Rules are expressed as forbidden dependency edges: (source_pattern, target_pattern)
DOMAIN_INVARIANTS = {
    "gaming": [
        ("graphics", "ai"),  # e.g., graphics -> ai forbidden
    ],
    "medical": [
        ("ui", "device"),    # UI should not talk to device drivers directly
    ],
    "robotics": [
        ("perception", "control"),  # enforce middleware boundaries
    ],
    "hpc": []
}


def check_patch(analysis_graph: Dict[str, List[str]], patch_text: str, domain: str) -> Dict[str, Any]:
    """
    Inspect patch text for hints of modules being linked and compare to domain invariants.
    analysis_graph: adjacency list {node: [deps...]}
    patch_text: suggested patch (string)
    domain: domain string
    Returns {ok: bool, violations: [...]} where violations list rules violated.
    """
    invariants = DOMAIN_INVARIANTS.get((domain or "").lower(), [])
    vio: List[Dict[str, str]] = []
    text = (patch_text or "").lower()
    for src_pat, dst_pat in invariants:
        if src_pat in text and dst_pat in text:
            vio.append({"rule": f"forbid {src_pat}->{dst_pat}", "evidence": f"found in patch text"})
    return {"ok": len(vio) == 0, "violations": vio}

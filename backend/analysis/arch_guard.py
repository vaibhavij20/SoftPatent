"""
Architecture Guard Module

This module provides functionality to enforce architectural invariants and constraints
for different application domains. It checks proposed code changes against domain-specific
rules to prevent architectural violations.
"""

from typing import Dict, List, TypedDict, Literal, Optional
from dataclasses import dataclass
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type aliases
DomainName = Literal["gaming", "medical", "robotics", "hpc", "satellite", 
                     "sustainability", "speech_therapy"]
Violation = Dict[str, str]
ArchitectureGraph = Dict[str, List[str]]

@dataclass
class PatchCheckResult:
    """Result of checking a patch against architectural rules."""
    ok: bool
    violations: List[Violation]

# Simple rule-based architecture guard. Replaceable with GNN later.
# Rules are expressed as forbidden dependency edges: (source_pattern, target_pattern)
DOMAIN_INVARIANTS: Dict[DomainName, List[tuple[str, str]]] = {
    "gaming": [
        ("graphics", "ai"),  # e.g., graphics -> ai forbidden
        ("ui", "physics"),   # UI should not directly depend on physics
    ],
    "medical": [
        ("ui", "device"),    # UI should not talk to device drivers directly
        ("api", "database"), # API should not directly access database
    ],
    "robotics": [
        ("perception", "control"),  # enforce middleware boundaries
        ("sensors", "actuators"),   # sensors should not directly control actuators
    ],
    "hpc": [
        ("io", "computation"),      # IO and computation should be separated
    ],
    "satellite": [
        ("telemetry", "control"),   # Telemetry should not directly affect control
    ],
    "sustainability": [
        ("monitoring", "actuation"), # Monitoring should be separate from actuation
    ],
    "speech_therapy": [
        ("ui", "audio_processing"), # UI should not directly process audio
    ]
}

def check_patch(
    analysis_graph: Optional[ArchitectureGraph],
    patch_text: Optional[str],
    domain: Optional[str]
) -> PatchCheckResult:
    """
    Inspect patch text for hints of modules being linked and compare to domain invariants.

    Args:
        analysis_graph: Adjacency list representing the module dependencies as {node: [deps...]}
        patch_text: The suggested patch content to be analyzed
        domain: The application domain (e.g., 'gaming', 'medical')

    Returns:
        PatchCheckResult: An object containing:
            - ok: bool indicating if the patch passes all architectural checks
            - violations: List of violations found, each with rule and evidence

    Example:
        >>> result = check_patch(
        ...     {"graphics": ["rendering"], "ai": ["pathfinding"]},
        ...     "graphics.render() -> ai.find_path()",
        ...     "gaming"
        ... )
        >>> assert not result.ok
        >>> assert "graphics->ai" in result.violations[0]["rule"]
    """
    if not domain or not isinstance(domain, str):
        logger.warning("No domain specified for architecture validation")
        return PatchCheckResult(ok=True, violations=[])

    domain = domain.lower()
    if domain not in DOMAIN_INVARIANTS:
        logger.warning(f"Unknown domain: {domain}")
        return PatchCheckResult(ok=True, violations=[])

    if not patch_text or not isinstance(patch_text, str):
        logger.debug("Empty or invalid patch text provided")
        return PatchCheckResult(ok=True, violations=[])

    invariants = DOMAIN_INVARIANTS[domain]
    violations: List[Violation] = []
    text = patch_text.lower()

    for src_pat, dst_pat in invariants:
        try:
            if src_pat in text and dst_pat in text:
                # Check if they appear in a way that suggests a dependency
                src_pos = text.find(src_pat)
                dst_pos = text.find(dst_pat, src_pos)  # Look for dst after src
                
                if src_pos != -1 and dst_pos != -1:
                    violations.append({
                        "rule": f"forbid {src_pat} -> {dst_pat}",
                        "evidence": f"Potential dependency from '{src_pat}' to '{dst_pat}' found in patch",
                        "severity": "high"
                    })
        except Exception as e:
            logger.error(f"Error checking invariant {src_pat}->{dst_pat}: {e}", 
                        exc_info=True)

    # If analysis_graph is provided, check for architectural violations there too
    if analysis_graph and isinstance(analysis_graph, dict):
        for src, deps in analysis_graph.items():
            if not isinstance(deps, list):
                continue
                
            for dep in deps:
                if not isinstance(dep, str):
                    continue
                    
                for src_pat, dst_pat in invariants:
                    if src_pat in src.lower() and dst_pat in dep.lower():
                        violations.append({
                            "rule": f"forbid {src_pat} -> {dst_pat}",
                            "evidence": f"Dependency from '{src}' to '{dep}' violates architectural rule",
                            "severity": "high"
                        })

    return PatchCheckResult(ok=len(violations) == 0, violations=violations)

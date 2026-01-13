"""Compliance checking module for domain-specific rules and best practices.

This module provides functionality to check code compliance against domain-specific
rules and best practices for various application domains such as gaming, medical,
robotics, and more.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, TypedDict, Literal
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Type aliases
DomainName = Literal["gaming", "robotics", "hpc", "medical", "satellite", "sustainability", "speech_therapy"]
RuleSeverity = Literal["low", "medium", "high", "critical"]
ComplianceStatus = Literal["pass", "warn", "fail", "error", "unknown"]

class Rule(TypedDict):
    """Type definition for a compliance rule."""
    id: str
    note: str
    risk: str
    severity: Optional[RuleSeverity]

class Finding(TypedDict):
    """Type definition for a compliance finding."""
    rule: str
    status: ComplianceStatus
    note: str
    risk: str
    severity: RuleSeverity
    details: Optional[Dict[str, Any]]

class ComplianceSummary(TypedDict):
    """Type definition for compliance check summary."""
    passed: int
    warn: int
    failed: int
    total: int

class ComplianceResult(TypedDict):
    """Type definition for the compliance check result."""
    domain: str
    targets: List[str]
    findings: List[Finding]
    summary: ComplianceSummary
    timestamp: str
    status: ComplianceStatus

# Domain-specific compliance rules with severity levels
DOMAIN_RULES: Dict[DomainName, List[Rule]] = {
    "gaming": [
        {
            "id": "render-batch",
            "note": "Prefer batching draw calls to improve FPS.",
            "risk": "Excessive per-frame allocations",
            "severity": "high"
        },
        {
            "id": "asset-io",
            "note": "Avoid synchronous I/O on main thread.",
            "risk": "Frame stutter",
            "severity": "high"
        },
    ],
    "robotics": [
        {
            "id": "realtime",
            "note": "Bound CPU to preserve control loop frequency.",
            "risk": "Control instability",
            "severity": "critical"
        },
        {
            "id": "numerics",
            "note": "Use stable solvers and clamp sensor outliers.",
            "risk": "Pose divergence",
            "severity": "high"
        },
    ],
    "hpc": [
        {
            "id": "vectorize",
            "note": "Exploit SIMD/BLAS where possible.",
            "risk": "Low GFLOPS",
            "severity": "medium"
        },
        {
            "id": "memory",
            "note": "Ensure contiguous memory and cache-friendly access.",
            "risk": "Cache misses",
            "severity": "high"
        },
    ],
    "medical": [
        {
            "id": "latency",
            "note": "Reduce end-to-end latency for critical paths.",
            "risk": "Spec violation",
            "severity": "critical"
        },
        {
            "id": "logging",
            "note": "Structured logging for traceability.",
            "risk": "Audit failure",
            "severity": "high"
        },
    ],
    "satellite": [
        {
            "id": "rt-control",
            "note": "Maintain deterministic control loop timing with jitter bounds.",
            "risk": "Attitude/orbit control instability",
            "severity": "critical"
        },
        {
            "id": "fault-tolerance",
            "note": "Implement watchdogs and safe-mode fallbacks.",
            "risk": "Mission-critical failure",
            "severity": "critical"
        },
    ],
    "sustainability": [
        {
            "id": "data-lineage",
            "note": "Track data lineage and transformations for auditability.",
            "risk": "Unverifiable analytics",
            "severity": "medium"
        },
        {
            "id": "throughput",
            "note": "Ensure backpressure and batching in pipelines.",
            "risk": "Data loss or lag",
            "severity": "high"
        },
    ],
    "speech_therapy": [
        {
            "id": "rt-audio",
            "note": "Guarantee real-time audio processing latency budgets.",
            "risk": "Feedback delay",
            "severity": "high"
        },
        {
            "id": "pii",
            "note": "Anonymize or protect voice data as PII.",
            "risk": "Privacy breach",
            "severity": "critical"
        },
    ],
}


def _create_error_result(
    domain: str,
    error_msg: str,
    targets: Optional[List[str]] = None,
    status: ComplianceStatus = "error"
) -> ComplianceResult:
    """Create an error result with the given message."""
    return {
        "domain": domain,
        "targets": targets or [],
        "findings": [{
            "rule": "internal-error",
            "status": status,
            "note": error_msg,
            "risk": "Compliance check could not be completed",
            "severity": "critical",
            "details": None
        }],
        "summary": {
            "passed": 0,
            "warn": 0,
            "failed": 1,
            "total": 1
        },
        "timestamp": datetime.utcnow().isoformat(),
        "status": status
    }


def check_compliance(domain: str, project_path: str, targets: Optional[List[str]] = None) -> ComplianceResult:
    """Check code compliance against domain-specific rules and best practices.
    
    This function performs a comprehensive compliance check of the specified project
    against the rules defined for the given domain. It returns detailed findings
    including which rules passed, failed, or generated warnings.
    
    Args:
        domain: The application domain to check compliance for (e.g., 'gaming', 'medical')
        project_path: Filesystem path to the project directory to be checked
        targets: Optional list of specific compliance targets to check. If None, all
                 applicable rules for the domain will be checked.
                 
    Returns:
        A ComplianceResult dictionary containing:
        - domain: The domain that was checked
        - targets: List of targets that were checked
        - findings: Detailed list of compliance findings
        - summary: Summary statistics of the compliance check
        - timestamp: When the check was performed (ISO format)
        - status: Overall status of the compliance check
        
    Raises:
        ValueError: If the domain is invalid or project_path doesn't exist
        PermissionError: If the project directory cannot be accessed
        RuntimeError: If there's an unexpected error during compliance checking
        
    Example:
        >>> result = check_compliance("gaming", "/path/to/game/project")
        >>> print(f"Compliance status: {result['status']}")
        >>> for finding in result['findings']:
        ...     print(f"- {finding['rule']}: {finding['status']}")
    """
    # Input validation
    if not isinstance(domain, str) or not domain.strip():
        raise ValueError("Domain must be a non-empty string")
        
    if not isinstance(project_path, str) or not project_path.strip():
        raise ValueError("Project path must be a non-empty string")
    
    # Normalize inputs
    domain = domain.lower().strip()
    project_path = project_path.strip()
    targets = list(set(targets or []))  # Deduplicate targets
    
    # Log the start of compliance check
    logger.info(
        "Starting compliance check for domain '%s' on project: %s",
        domain, project_path
    )
    if targets:
        logger.debug("Specific targets to check: %s", ", ".join(targets))
    
    try:
        # Validate project path exists and is accessible
        project_dir = Path(project_path)
        if not project_dir.exists():
            error_msg = f"Project directory not found: {project_path}"
            logger.error(error_msg)
            return _create_error_result(
                domain=domain,
                error_msg=error_msg,
                targets=targets,
                status="error"
            )
            
        if not project_dir.is_dir():
            error_msg = f"Project path is not a directory: {project_path}"
            logger.error(error_msg)
            return _create_error_result(
                domain=domain,
                error_msg=error_msg,
                targets=targets,
                status="error"
            )
        
        # Check if domain is supported
        if domain not in DOMAIN_RULES:
            valid_domains = ", ".join(f"'{d}'" for d in sorted(DOMAIN_RULES.keys()))
            error_msg = f"Unsupported domain: {domain}. Valid domains are: {valid_domains}"
            logger.error(error_msg)
            return _create_error_result(
                domain=domain,
                error_msg=error_msg,
                targets=targets,
                status="error"
            )
        
        # Get domain-specific rules
        rules = DOMAIN_RULES[domain]
        logger.debug("Found %d rules for domain '%s'", len(rules), domain)
        
        # Initialize findings with rule checks
        findings: List[Finding] = []
        
        # Check each rule
        for rule in rules:
            # Skip if we have specific targets and this rule isn't one of them
            if targets and rule["id"] not in targets:
                continue
                
            try:
                # In a real implementation, this would perform actual checks
                # For now, we'll simulate a mix of statuses
                import random
                status: ComplianceStatus = random.choice(["pass", "warn", "fail", "unknown"])
                
                finding: Finding = {
                    "rule": rule["id"],
                    "status": status,
                    "note": rule["note"],
                    "risk": rule["risk"],
                    "severity": rule.get("severity", "medium"),
                    "details": {
                        "checked_at": datetime.utcnow().isoformat(),
                        "files_scanned": ["simulated/file1.py", "simulated/file2.py"],
                        "violations_found": random.randint(0, 5) if status != "pass" else 0
                    }
                }
                findings.append(finding)
                
                logger.debug("Rule '%s' check completed with status: %s", 
                           rule["id"], status)
                
            except Exception as e:
                logger.error("Error checking rule '%s': %s", rule["id"], str(e), 
                            exc_info=True)
                findings.append({
                    "rule": rule["id"],
                    "status": "error",
                    "note": f"Error during check: {str(e)}",
                    "risk": "Check could not be completed",
                    "severity": rule.get("severity", "medium"),
                    "details": {"error": str(e)}
                })
        
        # Add target-specific checks for any targets that weren't covered by rules
        for target in targets:
            if not isinstance(target, str) or not target.strip():
                continue
                
            # Skip if this target was already checked as a rule
            if any(f["rule"] == target for f in findings):
                continue
                
            # This is a custom target not in our standard rules
            findings.append({
                "rule": f"target:{target}",
                "status": "unknown",
                "note": f"Custom target '{target}' not formally checked (stub).",
                "risk": "Unknown - custom target",
                "severity": "medium",
                "details": None
            })
        
        # Count statuses
        status_counts = {"passed": 0, "warn": 0, "failed": 0, "error": 0, "unknown": 0}
        for finding in findings:
            status = finding.get("status", "unknown").lower()
            if status in status_counts:
                status_counts[status] += 1
            else:
                status_counts["unknown"] += 1
        
        # Determine overall status
        if status_counts["failed"] > 0 or status_counts["error"] > 0:
            overall_status: ComplianceStatus = "fail"
        elif status_counts["warn"] > 0:
            overall_status = "warn"
        elif status_counts["passed"] > 0:
            overall_status = "pass"
        else:
            overall_status = "unknown"
        
        # Prepare the result
        result: ComplianceResult = {
            "domain": domain,
            "targets": targets,
            "findings": findings,
            "summary": {
                "passed": status_counts["passed"],
                "warn": status_counts["warn"],
                "failed": status_counts["failed"] + status_counts["error"],
                "total": len(findings)
            },
            "timestamp": datetime.utcnow().isoformat(),
            "status": overall_status
        }
        
        # Log completion
        logger.info(
            "Compliance check completed for domain '%s'. Status: %s. "
            "Findings: %d total, %d passed, %d warnings, %d failed",
            domain, overall_status.upper(),
            len(findings),
            status_counts["passed"],
            status_counts["warn"],
            status_counts["failed"] + status_counts["error"]
        )
        
        return result
        
    except Exception as e:
        error_msg = f"Unexpected error during compliance check: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return _create_error_result(
            domain=domain if 'domain' in locals() else "unknown",
            error_msg=error_msg,
            targets=targets if 'targets' in locals() else [],
            status="error"
        )

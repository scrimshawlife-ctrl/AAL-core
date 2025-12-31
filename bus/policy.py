from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .types import Phase

@dataclass(frozen=True)
class PolicyDecision:
    """Result of a policy enforcement check."""
    ok: bool
    reason: str = ""

# Phase-based permission rules with granular capability enforcement
PHASE_RULES = {
    "OPEN":   {"allow_external_io": True,  "allow_writes": True,  "allow_exec": False},
    "ALIGN":  {"allow_external_io": True,  "allow_writes": True,  "allow_exec": False},
    "ASCEND": {"allow_external_io": True,  "allow_writes": True,  "allow_exec": True},
    "CLEAR":  {"allow_external_io": False, "allow_writes": False, "allow_exec": False},
    "SEAL":   {"allow_external_io": False, "allow_writes": True,  "allow_exec": False},
}

# Phase capability requirements (belt-and-suspenders enforcement)
PHASE_REQUIREMENTS = {
    "OPEN": [],  # No special caps needed
    "ALIGN": [],
    "ASCEND": ["exec"],  # ASCEND requires exec capability
    "CLEAR": [],
    "SEAL": [],
}

def enforce_phase_policy(phase: Phase, overlay_caps: List[str]) -> PolicyDecision:
    """
    Enforce phase-based capability policy with granular permission checks.

    Args:
        phase: The phase being invoked
        overlay_caps: List of capabilities declared by the overlay

    Returns:
        PolicyDecision indicating if the invocation is allowed
    """
    # Check granular permissions
    rules = PHASE_RULES.get(phase, {})

    if "external_io" in overlay_caps and not rules.get("allow_external_io", False):
        return PolicyDecision(False, f"Phase {phase} forbids external_io")

    if "writes" in overlay_caps and not rules.get("allow_writes", False):
        return PolicyDecision(False, f"Phase {phase} forbids writes")

    if "exec" in overlay_caps and not rules.get("allow_exec", False):
        return PolicyDecision(False, f"Phase {phase} forbids exec")

    # Check required capabilities
    if phase == "ASCEND" and "exec" not in overlay_caps:
        return PolicyDecision(False, "ASCEND requires explicit 'exec' capability")

    required = PHASE_REQUIREMENTS.get(phase, [])
    missing = [cap for cap in required if cap not in overlay_caps]

    if missing:
        return PolicyDecision(
            False,
            f"Phase '{phase}' requires missing capabilities: {missing}"
        )

    return PolicyDecision(True, "Policy check passed")

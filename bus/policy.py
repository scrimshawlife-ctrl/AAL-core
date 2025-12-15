from __future__ import annotations
from dataclasses import dataclass
from typing import List

from .types import Phase

@dataclass(frozen=True)
class PolicyDecision:
    """Result of a policy enforcement check."""
    ok: bool
    reason: str = ""

# Phase capability requirements (belt-and-suspenders enforcement)
PHASE_REQUIREMENTS = {
    "OPEN": [],  # No special caps needed
    "ALIGN": [],
    "ASCEND": ["exec"],  # ASCEND requires exec capability
    "CLEAR": [],
    "SEAL": [],
}

def enforce_phase_policy(phase: Phase, capabilities: List[str]) -> PolicyDecision:
    """
    Enforce phase-based capability policy.

    Args:
        phase: The phase being invoked
        capabilities: List of capabilities (overlay caps + op-required caps)

    Returns:
        PolicyDecision indicating if the invocation is allowed
    """
    required = PHASE_REQUIREMENTS.get(phase, [])

    # Check if all required capabilities are present
    missing = [cap for cap in required if cap not in capabilities]

    if missing:
        return PolicyDecision(
            ok=False,
            reason=f"Phase '{phase}' requires missing capabilities: {missing}"
        )

    return PolicyDecision(ok=True, reason="Policy check passed")

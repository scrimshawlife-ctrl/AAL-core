from __future__ import annotations
from dataclasses import dataclass
from typing import List, Literal

Phase = Literal["OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"]

@dataclass(frozen=True)
class PolicyDecision:
    ok: bool
    reason: str

PHASE_RULES = {
    "OPEN":   {"allow_external_io": True,  "allow_writes": True,  "allow_exec": False},
    "ALIGN":  {"allow_external_io": True,  "allow_writes": True,  "allow_exec": False},
    "ASCEND": {"allow_external_io": True,  "allow_writes": True,  "allow_exec": True},
    "CLEAR":  {"allow_external_io": False, "allow_writes": False, "allow_exec": False},
    "SEAL":   {"allow_external_io": False, "allow_writes": True,  "allow_exec": False},
}

def enforce_phase_policy(phase: Phase, overlay_caps: List[str]) -> PolicyDecision:
    rules = PHASE_RULES[phase]

    if "external_io" in overlay_caps and not rules["allow_external_io"]:
        return PolicyDecision(False, f"Phase {phase} forbids external_io")

    if "writes" in overlay_caps and not rules["allow_writes"]:
        return PolicyDecision(False, f"Phase {phase} forbids writes")

    if "exec" in overlay_caps and not rules["allow_exec"]:
        return PolicyDecision(False, f"Phase {phase} forbids exec")

    if phase == "ASCEND" and "exec" not in overlay_caps:
        return PolicyDecision(False, "ASCEND requires explicit 'exec' capability")

    return PolicyDecision(True, "ok")

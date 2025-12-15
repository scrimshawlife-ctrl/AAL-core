from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

Phase = Literal["OPEN", "ALIGN", "ASCEND", "CLEAR", "SEAL"]

@dataclass(frozen=True)
class OverlayManifest:
    name: str
    version: str
    status: str
    phases: List[Phase]
    entrypoint: str  # e.g. "python run.py"
    timeout_ms: int = 2500
    capabilities: Optional[List[str]] = None  # Optional declared capabilities

@dataclass(frozen=True)
class InvocationRequest:
    overlay: str
    phase: Phase
    payload: Dict[str, Any]

@dataclass(frozen=True)
class InvocationResult:
    ok: bool
    overlay: str
    phase: Phase
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    provenance_hash: str
    # Optional structured output if overlay emits JSON on stdout
    output_json: Optional[Dict[str, Any]] = None
    policy_checked: bool = False  # Whether policy enforcement ran
    policy_violation: Optional[str] = None  # Policy violation details if any

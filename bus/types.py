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
    entrypoint: str
    capabilities: List[str]
    op_policy: Dict[str, List[str]]  # NEW: op -> required capabilities
    timeout_ms: int = 2500

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
    output_json: Optional[Dict[str, Any]] = None

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RollbackIR:
    """
    Rollback attribution record.

    v1.5 contract: rollback-ir/0.2 carries the exact attempted knob/value(s) and
    a minimal tuning_ir linkage stub for queryability.
    """

    schema_version: str  # rollback-ir/0.2
    rollback_hash: str
    source_cycle_id: str
    module_id: str
    baseline_signature: Dict[str, str]
    tuning_ir_hash: str
    tuning_ir_stub: Dict[str, Any]
    attempted_assignments: Dict[str, Any]
    reason: Dict[str, Any]
    reverted_assignments: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RollbackIR:
    schema_version: str
    rollback_hash: str
    source_cycle_id: str
    module_id: str
    baseline_signature: Dict[str, str]
    tuning_ir_hash: str
    reason: Dict[str, Any]
    reverted_assignments: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


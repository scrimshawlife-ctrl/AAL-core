from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class PromotionProposalIR:
    schema_version: str
    proposal_hash: str
    source_cycle_id: str
    target: Dict[str, Any]
    baseline_signature: Dict[str, str]
    metric_name: str
    stats: Dict[str, Any]
    rollback_rate: float
    evidence_window: Dict[str, Any]
    recommendation: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


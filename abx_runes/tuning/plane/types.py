from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class TuningPlaneBundleIR:
    """
    v1.0 unified tuning plane artifact.
    """

    schema_version: str
    bundle_hash: str
    source_cycle_id: str
    baseline_signature: Dict[str, str]
    policy: Dict[str, Any]
    portfolio: Dict[str, Any]
    experiments: List[Dict[str, Any]]
    decisions: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


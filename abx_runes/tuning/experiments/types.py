from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class ExperimentIR:
    """
    Deterministic artifact describing an experiment plan.
    """

    schema_version: str
    experiment_hash: str
    source_cycle_id: str
    module_id: str
    node_id: str
    baseline_signature: Dict[str, str]
    knob_name: str
    candidate_values: List[Any]
    trial_plan: Dict[str, Any]
    budgets: Dict[str, Any]
    mode: str
    notes: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


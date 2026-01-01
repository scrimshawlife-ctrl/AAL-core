from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from .tuning_apply import HotApplyResult, hot_apply_tuning_ir


@dataclass(frozen=True)
class RollbackResult:
    attempted: Dict[str, Any]
    applied: Dict[str, Any]
    rejected: Dict[str, str]


def rollback_to_previous(
    *,
    module_id: str,
    source_cycle_id: str,
    node_id: str,
    tuning_envelope: Dict[str, Any],
    capability,
    stabilization_state,
    prev_assignments: Dict[str, Any],
    revert_keys: Dict[str, Any],
    cycle_boundary: bool = True,
    apply_fn: Optional[Callable[..., HotApplyResult]] = None,
) -> RollbackResult:
    """
    First-class ERS rollback action.

    revert_keys are the keys we want to revert (typically the canary-applied keys).
    prev_assignments provides the prior values to restore.
    """
    reverted: Dict[str, Any] = {}
    for k in (revert_keys or {}).keys():
        if k in (prev_assignments or {}):
            reverted[k] = prev_assignments[k]

    rb_ir = {
        "schema_version": "tuning-ir/0.1",
        "ir_hash": "",
        "source_cycle_id": source_cycle_id,
        "mode": "applied_tune",
        "module_id": module_id,
        "node_id": node_id,
        "assignments": reverted,
        "reason_tags": ["rollback_v1.2"],
    }

    fn = hot_apply_tuning_ir if apply_fn is None else apply_fn
    res = fn(
        tuning_ir=rb_ir,
        tuning_envelope=tuning_envelope,
        capability=capability,
        stab=stabilization_state,
        cycle_boundary=cycle_boundary,
    )
    return RollbackResult(attempted=reverted, applied=res.applied, rejected=res.rejected)


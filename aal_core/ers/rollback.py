from __future__ import annotations

from typing import Any, Dict, Optional

from .tuning_apply import HotApplyResult, hot_apply_tuning_ir


def rollback_to_previous(
    *,
    source_cycle_id: str,
    module_id: str,
    node_id: str,
    reverted_assignments: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    capability,
    stabilization_state,
    cycle_boundary: bool = True,
    reason_tags: Optional[list[str]] = None,
) -> HotApplyResult:
    """
    ERS v1.2: explicit rollback action (first-class).
    """
    tags = list(reason_tags or [])
    if "rollback_v1.2" not in tags:
        tags.append("rollback_v1.2")

    rb_ir = {
        "schema_version": "tuning-ir/0.1",
        "ir_hash": "rollback-placeholder",
        "source_cycle_id": str(source_cycle_id),
        "mode": "applied_tune",
        "module_id": str(module_id),
        "node_id": str(node_id),
        "assignments": dict(reverted_assignments or {}),
        "reason_tags": tags,
    }
    return hot_apply_tuning_ir(
        tuning_ir=rb_ir,
        tuning_envelope=tuning_envelope,
        capability=capability,
        stab=stabilization_state,
        cycle_boundary=cycle_boundary,
    )


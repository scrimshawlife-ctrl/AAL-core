from __future__ import annotations

from typing import Any, Dict

from abx_runes.tuning.hashing import content_hash


def build_rollback_ir_dict(
    *,
    module_id: str,
    tuning_ir: Dict[str, Any],
    baseline_signature: Dict[str, str],
    attempted_assignments: Dict[str, Any],
    reverted_assignments: Dict[str, Any],
    reason: Dict[str, Any],
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> Dict[str, Any]:
    """
    v1.5: Build a rollback record with precise attempted assignment attribution.

    This repository does not yet have a full "canary apply" runtime; this helper
    produces the canonical rollback payload shape used by the ledger + scanner.
    """

    rb: Dict[str, Any] = {
        "schema_version": "rollback-ir/0.2",
        "rollback_hash": "",
        "source_cycle_id": str(tuning_ir.get("source_cycle_id", "")),
        "module_id": str(module_id),
        "baseline_signature": dict(baseline_signature or {}),
        "tuning_ir_hash": str(tuning_ir.get("ir_hash", "")),
        "tuning_ir_stub": {
            "module_id": str(module_id),
            "node_id": str(tuning_ir.get("node_id", "")),
            "reason_tags": list(tuning_ir.get("reason_tags") or []),
        },
        "attempted_assignments": dict(attempted_assignments or {}),
        "reason": dict(reason or {}),
        "reverted_assignments": dict(reverted_assignments or {}),
        "provenance": {
            "before_hash": content_hash(before or {}),
            "after_hash": content_hash(after or {}),
        },
    }
    # Deterministic hash with rollback_hash blanked.
    rb["rollback_hash"] = content_hash(rb, blank_fields=("rollback_hash",))
    return rb


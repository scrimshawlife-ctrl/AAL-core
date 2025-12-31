from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from abx_runes.tuning.validator import validate_tuning_ir_against_envelope

from .capabilities import CapabilityToken, can_apply
from .stabilization import StabilizationState, note_change, allowed_by_stabilization


@dataclass(frozen=True)
class HotApplyResult:
    applied: Dict[str, Any]
    rejected: Dict[str, str]  # knob_name -> reason


def load_json(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def hot_apply_tuning_ir(
    *,
    tuning_ir: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    capability: CapabilityToken,
    stab: StabilizationState,
    cycle_boundary: bool = True,
) -> HotApplyResult:
    """
    Applies tuning at cycle boundary only.
    - Validates tuning_ir vs envelope (typed + bounds)
    - Checks capability_required per knob
    - Checks stabilization gate for knobs that require it
    - If tuning mode == shadow_tune: does not apply, only returns what WOULD apply
    """
    if not cycle_boundary:
        return HotApplyResult(applied={}, rejected={"__all__": "not_cycle_boundary"})

    ok, reason = validate_tuning_ir_against_envelope(tuning_ir, tuning_envelope)
    if not ok:
        return HotApplyResult(applied={}, rejected={"__all__": f"invalid_ir:{reason}"})

    mode = str(tuning_ir.get("mode"))
    assigns: Dict[str, Any] = tuning_ir.get("assignments") or {}
    knob_specs = {k["name"]: k for k in (tuning_envelope.get("knobs") or [])}

    applied: Dict[str, Any] = {}
    rejected: Dict[str, str] = {}

    for name, val in assigns.items():
        spec = knob_specs[name]
        req_cap = str(spec.get("capability_required", "")).strip()
        hot = bool(spec.get("hot_apply", False))
        stab_cycles = int(spec.get("stabilization_cycles", 0) or 0)

        if not hot:
            rejected[name] = "not_hot_apply"
            continue
        if req_cap and not can_apply(capability, req_cap):
            rejected[name] = "capability_denied"
            continue
        if not allowed_by_stabilization(stab, tuning_ir["module_id"], name, stab_cycles):
            rejected[name] = "stabilization_block"
            continue

        # shadow_tune is a dry-run
        if mode == "shadow_tune":
            applied[name] = val
            continue

        applied[name] = val
        note_change(stab, tuning_ir["module_id"], name)

    return HotApplyResult(applied=applied, rejected=rejected)

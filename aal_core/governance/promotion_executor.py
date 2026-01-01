from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from abx_runes.tuning.hashing import content_hash

from aal_core.ers.budgets import BudgetState
from aal_core.ers.canary_apply import canary_apply_tuning_ir
from aal_core.governance.promotion_policy import DEFAULT_PATH as DEFAULT_PROMOTIONS_PATH
from aal_core.governance.promotion_policy import PromotionPolicy
from aal_core.ledger.ledger import DEFAULT_LEDGER_PATH
from aal_core.ledger.ledger import EvidenceLedger


def apply_approved_promotions(
    *,
    approved_proposals: List[Dict[str, Any]],
    registry: Any,
    effects_store: Any,
    get_metrics_snapshot: Any,
    get_current_assignments: Any,
    policy: Optional[Dict[str, Any]] = None,
    promotions_path: Optional[Path] = None,
    ledger_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    v2.0: Execute explicitly approved promotions.

    Contract:
    - Approval is explicit input (approved_proposals)
    - Apply as canaries (mode="promotion_canary") with strict budgets
    - On success: write/merge into canonical .aal/promotions.json (deterministic)
    - On failure: rollback and revoke (mark revoked_at_idx if present)
    - Always emit evidence ledger entries: promotion_applied, promotion_canary_ok, promotion_rolled_back
    """
    policy = policy or {}
    ledger = EvidenceLedger(path=ledger_path or DEFAULT_LEDGER_PATH)
    prom = PromotionPolicy.load(path=promotions_path or DEFAULT_PROMOTIONS_PATH)

    budgets = BudgetState(
        canary_remaining=int(policy.get("promotion_canary_budget", 2)),
        risk_units_remaining=float(policy.get("promotion_risk_budget", 1.0)),
        global_active_perturbations=0,
        global_active_cap=int(policy.get("promotion_concurrency_cap", 1)),
    )

    applied: List[Dict[str, Any]] = []
    rolled_back: List[Dict[str, Any]] = []

    proposals = sorted(
        approved_proposals,
        key=lambda p: (
            (p.get("target") or {}).get("module_id", ""),
            (p.get("target") or {}).get("knob_name", ""),
        ),
    )

    for p in proposals:
        if budgets.canary_remaining <= 0:
            break

        tgt = p.get("target") or {}
        module_id = str(tgt.get("module_id", ""))
        knob = str(tgt.get("knob_name", ""))
        value = tgt.get("value")
        baseline = p.get("baseline_signature") or {}
        metric_name = str(p.get("metric_name", policy.get("canary_metric_name", "latency_ms_p95")))
        proposal_hash = str(p.get("proposal_hash", ""))

        tuning_ir: Dict[str, Any] = {
            "schema_version": "tuning-ir/0.1",
            "mode": "promotion_canary",
            "module_id": module_id,
            "node_id": "promotion",
            "assignments": {knob: value},
            "reason_tags": ["promotion_v2.0"],
            "metric_name": metric_name,
            "source_cycle_id": str(p.get("source_cycle_id", "")),
        }
        tuning_ir["ir_hash"] = content_hash(tuning_ir, blank_fields=("ir_hash",))

        ledger.append(
            entry_type="promotion_applied",
            payload={
                "proposal_hash": proposal_hash,
                "tuning_ir": tuning_ir,
                "baseline_signature": baseline,
            },
            provenance={"policy_hash": content_hash(policy)},
        )

        budgets.charge_canary(1)
        if not budgets.begin_perturbation():
            break

        desc = registry.get_module_descriptor(module_id)
        cres = canary_apply_tuning_ir(
            tuning_ir=tuning_ir,
            tuning_envelope=desc.tuning_envelope,
            capability=desc.capability,
            effects_store=effects_store,
            get_metrics_snapshot=get_metrics_snapshot,
            get_current_assignments=get_current_assignments,
            stab=getattr(desc, "stabilization_state", None),
            cycle_boundary=True,
            policy=policy,
        )

        budgets.end_perturbation()

        if cres.rolled_back:
            tail = ledger.read_tail(1)
            idx = int(tail[-1]["idx"]) if tail else 0
            prom.revoke(
                module_id=module_id,
                knob=knob,
                value=value,
                baseline_signature=baseline,
                revoked_at_idx=idx,
            )
            rolled_back.append({"proposal_hash": proposal_hash, "rollback": cres.rollback_ir})
            ledger.append(
                entry_type="promotion_rolled_back",
                payload={"proposal_hash": proposal_hash, "rollback": cres.rollback_ir},
                provenance={},
            )
        else:
            tail = ledger.read_tail(1)
            idx = int(tail[-1]["idx"]) if tail else 0
            item = {
                "module_id": module_id,
                "knob": knob,
                "value": value,
                "baseline_signature": baseline,
                "metric_name": metric_name,
                "promoted_at_idx": idx,
                "proposal_hash": proposal_hash,
            }
            prom.upsert(item)
            applied.append(item)
            ledger.append(
                entry_type="promotion_canary_ok",
                payload={"proposal_hash": proposal_hash, "item": item},
                provenance={},
            )

    prom.save(path=promotions_path or DEFAULT_PROMOTIONS_PATH)
    return {"applied": applied, "rolled_back": rolled_back, "remaining_canary": budgets.canary_remaining}


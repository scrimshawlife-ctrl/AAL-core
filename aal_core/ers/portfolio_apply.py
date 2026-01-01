from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from .canary_apply import CanaryResult, canary_apply_tuning_ir
from .effects_store import EffectStore
from .tuning_apply import HotApplyResult, hot_apply_tuning_ir


@dataclass(frozen=True)
class PortfolioApplyResult:
    """
    Minimal portfolio apply wrapper for ERS.

    `applied`: list of per-item apply outcomes
    `rejected`: list of per-item rejection / rollback artifacts
    """

    applied: List[Dict[str, Any]] = field(default_factory=list)
    rejected: List[Dict[str, Any]] = field(default_factory=list)


def _portfolio_items(portfolio_ir: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Accept a couple of reasonable shapes; keep deterministic ordering regardless.
    raw = portfolio_ir.get("items")
    if raw is None:
        raw = portfolio_ir.get("tuning_irs")
    items = list(raw or [])
    return sorted(items, key=lambda d: str((d or {}).get("ir_hash", "")))


def apply_portfolio_tuning_ir(
    *,
    portfolio_ir: Dict[str, Any],
    tuning_envelope: Dict[str, Any],
    capability,
    stabilization_state,
    cycle_boundary: bool = True,
    # v1.2 canary plumbing:
    effects_store: Optional[EffectStore] = None,
    get_metrics_snapshot: Optional[Callable[[], Dict[str, Dict[str, Any]]]] = None,
    get_current_assignments: Optional[Callable[[str], Dict[str, Any]]] = None,
    policy: Optional[Dict[str, Any]] = None,
) -> PortfolioApplyResult:
    """
    ERS v1.2 portfolio apply:
    - Deterministic canary schedule (sorted by ir_hash)
    - Explicit policy-controlled rollback thresholds
    - Rollback returns a RollbackIR artifact (ledger continuity)
    """
    pol = dict(policy or {})
    enable_canary = bool(pol.get("enable_canary", True))

    applied: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for tir in _portfolio_items(portfolio_ir):
        ir_hash = str((tir or {}).get("ir_hash", ""))

        canary_deps_ok = (
            enable_canary
            and effects_store is not None
            and get_metrics_snapshot is not None
            and get_current_assignments is not None
        )

        if canary_deps_ok:
            cres: CanaryResult = canary_apply_tuning_ir(
                tuning_ir=tir,
                tuning_envelope=tuning_envelope,
                capability=capability,
                stabilization_state=stabilization_state,
                effects_store=effects_store,  # type: ignore[arg-type]
                get_metrics_snapshot=get_metrics_snapshot,  # type: ignore[arg-type]
                get_current_assignments=get_current_assignments,  # type: ignore[arg-type]
                cycle_boundary=cycle_boundary,
                policy=pol,
            )
            applied.append({"ir_hash": ir_hash, "canary": True, "rolled_back": bool(cres.rolled_back)})
            if cres.rollback_ir is not None:
                rejected.append({"ir_hash": ir_hash, "reason": "rollback", "rollback": cres.rollback_ir})
            continue

        # fallback: direct hot-apply (v0.1 behavior)
        res: HotApplyResult = hot_apply_tuning_ir(
            tuning_ir=tir,
            tuning_envelope=tuning_envelope,
            capability=capability,
            stab=stabilization_state,
            cycle_boundary=cycle_boundary,
        )
        applied.append({"ir_hash": ir_hash, "canary": False, "applied": dict(res.applied), "rejected": dict(res.rejected)})

    return PortfolioApplyResult(applied=applied, rejected=rejected)


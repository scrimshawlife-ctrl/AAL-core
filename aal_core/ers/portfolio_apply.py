from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from aal_core.ers.capabilities import CapabilityToken
from aal_core.ers.stabilization import StabilizationState
from aal_core.ers.tuning_apply import HotApplyResult, hot_apply_tuning_ir


@dataclass(frozen=True)
class PortfolioHotApplyResult:
    """
    Portfolio apply result: per-module HotApplyResult plus portfolio-level rejection.
    """

    per_module: Dict[str, HotApplyResult]
    rejected: Dict[str, str]  # "__all__" -> reason


def hot_apply_portfolio_tuning_ir(
    *,
    portfolio_tuning_ir: Dict[str, Any],
    tuning_envelopes: Dict[str, Dict[str, Any]],
    capabilities: Dict[str, CapabilityToken],
    stab: StabilizationState,
    cycle_boundary: bool = True,
) -> PortfolioHotApplyResult:
    """
    Apply a portfolio at the cycle boundary with two-phase semantics:
      1) validate/pre-check every contained module TuningIR (no stab mutation)
      2) apply only those eligible using the real stabilization state

    This prevents "half-applied because we discovered an invalid IR mid-loop".

    Notes:
    - v0.4 does NOT auto-promote; module IRs control their own mode.
    - If the portfolio is structurally invalid (bad schema / duplicate modules), nothing is applied.
    """
    if not cycle_boundary:
        return PortfolioHotApplyResult(per_module={}, rejected={"__all__": "not_cycle_boundary"})

    if portfolio_tuning_ir.get("schema_version") != "portfolio-tuning-ir/0.4":
        return PortfolioHotApplyResult(per_module={}, rejected={"__all__": "bad_schema_version"})

    modules = list(portfolio_tuning_ir.get("modules") or [])
    seen = set()
    for m in modules:
        mid = str(m.get("module_id") or "")
        if not mid:
            return PortfolioHotApplyResult(per_module={}, rejected={"__all__": "missing_module_id"})
        if mid in seen:
            return PortfolioHotApplyResult(per_module={}, rejected={"__all__": f"duplicate_module:{mid}"})
        seen.add(mid)

    # Phase 1: pre-check each module IR without mutating stab.
    prechecked: Dict[str, HotApplyResult] = {}
    eligible_modules: Dict[str, Dict[str, Any]] = {}
    for m in modules:
        mid = str(m.get("module_id"))
        tuning_ir = dict(m.get("tuning_ir") or {})
        env = tuning_envelopes.get(mid)
        cap = capabilities.get(mid)

        if env is None:
            prechecked[mid] = HotApplyResult(applied={}, rejected={"__all__": "missing_envelope"})
            continue
        if cap is None:
            prechecked[mid] = HotApplyResult(applied={}, rejected={"__all__": "missing_capability"})
            continue

        stab_copy = StabilizationState(cycles_since_change=dict(stab.cycles_since_change))
        r = hot_apply_tuning_ir(
            tuning_ir=tuning_ir,
            tuning_envelope=env,
            capability=cap,
            stab=stab_copy,
            cycle_boundary=True,
        )
        prechecked[mid] = r
        # Eligible if the IR itself validated and there exists at least one knob that would apply.
        if "__all__" not in (r.rejected or {}) and (r.applied or {}):
            eligible_modules[mid] = tuning_ir

    # Phase 2: apply eligible subset using the real stabilization state.
    applied_results: Dict[str, HotApplyResult] = dict(prechecked)
    for mid, tuning_ir in eligible_modules.items():
        env = tuning_envelopes[mid]
        cap = capabilities[mid]
        applied_results[mid] = hot_apply_tuning_ir(
            tuning_ir=tuning_ir,
            tuning_envelope=env,
            capability=cap,
            stab=stab,
            cycle_boundary=True,
        )

    return PortfolioHotApplyResult(per_module=applied_results, rejected={})


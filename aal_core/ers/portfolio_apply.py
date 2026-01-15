from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .canary_apply import CanaryResult, canary_apply_tuning_ir
from .tuning_apply import HotApplyResult, hot_apply_tuning_ir


@dataclass(frozen=True)
class PortfolioHotApplyResult:
    """Result of applying a portfolio tuning IR."""
    rejected: Dict[str, str]  # Portfolio-level rejections
    per_module: Dict[str, HotApplyResult]  # Module-level results


def hot_apply_portfolio_tuning_ir(
    *,
    portfolio_tuning_ir: Dict[str, Any],
    tuning_envelopes: Dict[str, Dict[str, Any]],
    capabilities: Dict[str, Any],
    stab: Any,
    cycle_boundary: bool = True,
) -> PortfolioHotApplyResult:
    """
    Apply a portfolio tuning IR to multiple modules.

    Args:
        portfolio_tuning_ir: Portfolio structure with modules list
        tuning_envelopes: Dict of module_id -> tuning_envelope
        capabilities: Dict of module_id -> CapabilityToken
        stab: StabilizationState
        cycle_boundary: Whether this is a cycle boundary

    Returns:
        PortfolioHotApplyResult with rejected dict and per_module results
    """
    modules = portfolio_tuning_ir.get("modules", [])

    # Validate for duplicate module IDs
    seen_module_ids = set()
    for mod in modules:
        module_id = mod.get("module_id", "")
        if module_id in seen_module_ids:
            return PortfolioHotApplyResult(
                rejected={"__all__": f"duplicate_module_id:{module_id}"},
                per_module={},
            )
        seen_module_ids.add(module_id)

    # Apply each module's tuning IR
    per_module: Dict[str, HotApplyResult] = {}

    for mod in modules:
        module_id = str(mod.get("module_id", ""))
        tuning_ir = mod.get("tuning_ir", {})

        # Get envelope and capability for this module
        envelope = tuning_envelopes.get(module_id, {})
        capability = capabilities.get(module_id)

        if not envelope or capability is None:
            per_module[module_id] = HotApplyResult(
                applied={},
                rejected={"__all__": "missing_envelope_or_capability"},
            )
            continue

        # Apply the tuning IR
        result = hot_apply_tuning_ir(
            tuning_ir=tuning_ir,
            tuning_envelope=envelope,
            capability=capability,
            stab=stab,
            cycle_boundary=cycle_boundary,
        )
        per_module[module_id] = result

    return PortfolioHotApplyResult(rejected={}, per_module=per_module)


@dataclass(frozen=True)
class PortfolioApplyResult:
    applied: List[Dict[str, Any]]
    rejected: List[Dict[str, Any]]


def _extract_items(portfolio_ir: Dict[str, Any]) -> List[Dict[str, Any]]:
    # v0.7/v1.2 compatibility: accept several shapes.
    if isinstance(portfolio_ir.get("items"), list):
        return list(portfolio_ir["items"])
    if isinstance(portfolio_ir.get("tuning_irs"), list):
        return list(portfolio_ir["tuning_irs"])
    if isinstance(portfolio_ir.get("tuning_ir_items"), list):
        return list(portfolio_ir["tuning_ir_items"])
    return []


def apply_portfolio_tuning_ir(
    *,
    portfolio_ir: Dict[str, Any],
    resolve: Callable[[str], Tuple[Dict[str, Any], Any]],
    stabilization_state,
    effects_store=None,
    get_metrics_snapshot=None,
    get_current_assignments=None,
    policy: Optional[Dict[str, Any]] = None,
    cycle_boundary: bool = True,
) -> PortfolioApplyResult:
    """
    Apply each selected tuning IR item, optionally via canary apply + rollback.

    resolve(module_id) -> (tuning_envelope, capability_token)
    """
    pol = policy or {}
    enable_canary = bool(pol.get("enable_canary", True))

    applied: List[Dict[str, Any]] = []
    rejected: List[Dict[str, Any]] = []

    for tir in _extract_items(portfolio_ir):
        module_id = str(tir.get("module_id", ""))
        env, cap = resolve(module_id)

        if enable_canary:
            if effects_store is None or get_metrics_snapshot is None or get_current_assignments is None:
                rejected.append({"ir_hash": tir.get("ir_hash", ""), "reason": "missing_canary_dependencies"})
                continue
            cres: CanaryResult = canary_apply_tuning_ir(
                tuning_ir=tir,
                tuning_envelope=env,
                capability=cap,
                stabilization_state=stabilization_state,
                effects_store=effects_store,
                get_metrics_snapshot=get_metrics_snapshot,
                get_current_assignments=get_current_assignments,
                cycle_boundary=cycle_boundary,
                policy=pol,
            )
            applied.append(
                {
                    "ir_hash": tir.get("ir_hash", ""),
                    "canary": True,
                    "rolled_back": cres.rolled_back,
                }
            )
            if cres.rollback_ir is not None:
                rejected.append(
                    {
                        "ir_hash": tir.get("ir_hash", ""),
                        "reason": "rollback",
                        "rollback": cres.rollback_ir,
                    }
                )
        else:
            res: HotApplyResult = hot_apply_tuning_ir(
                tuning_ir=tir,
                tuning_envelope=env,
                capability=cap,
                stab=stabilization_state,
                cycle_boundary=cycle_boundary,
            )
            applied.append({"ir_hash": tir.get("ir_hash", ""), "canary": False, "applied": res.applied})
            if res.rejected:
                rejected.append({"ir_hash": tir.get("ir_hash", ""), "reason": "rejected", "details": dict(res.rejected)})

    return PortfolioApplyResult(applied=applied, rejected=rejected)


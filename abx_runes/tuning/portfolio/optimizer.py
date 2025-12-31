from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from aal_core.ers.capabilities import CapabilityToken, can_apply
from aal_core.ers.stabilization import StabilizationState, allowed_by_stabilization

from abx_runes.tuning.emit import lock_tuning_ir
from abx_runes.tuning.validator import validate_tuning_ir_against_envelope

from .types import (
    ImpactVector,
    PortfolioBudgets,
    PortfolioCandidate,
    PortfolioObjectiveWeights,
    PortfolioSelection,
)


def _stable_value_key(v: Any) -> str:
    # Deterministic string key for tie-breaking.
    if isinstance(v, bool):
        return "bool:true" if v else "bool:false"
    if isinstance(v, int) and not isinstance(v, bool):
        return f"int:{v}"
    if isinstance(v, float):
        # repr(float) is deterministic in CPython, but we still tag the type.
        return f"float:{repr(v)}"
    return f"str:{str(v)}"


def score_candidate(c: PortfolioCandidate, w: PortfolioObjectiveWeights) -> float:
    """
    score = wL*Δlatency + wC*Δcost + wE*Δerror + wT*Δthroughput
    """
    iv = c.impact
    return (
        float(w.w_latency) * float(iv.delta_latency_ms_p95)
        + float(w.w_cost) * float(iv.delta_cost_units)
        + float(w.w_error) * float(iv.delta_error_rate)
        + float(w.w_throughput) * float(iv.delta_throughput_per_s)
    )


def _budget_spend(iv: ImpactVector) -> Tuple[float, float]:
    """
    Converts impact to a conservative "spend" against budgets.
    v0.4 rule: only positive deltas consume budget (no "refunds").
    """
    spend_cost = max(0.0, float(iv.delta_cost_units))
    spend_lat = max(0.0, float(iv.delta_latency_ms_p95))
    return spend_cost, spend_lat


@dataclass(frozen=True)
class _ValidatedCandidate:
    cand: PortfolioCandidate
    score: float
    spend_cost: float
    spend_lat: float


def _candidate_is_envelope_eligible(
    *,
    cand: PortfolioCandidate,
    tuning_envelope: Dict[str, Any],
    capability: CapabilityToken,
    stab: StabilizationState,
) -> bool:
    knobs = {k.get("name"): k for k in (tuning_envelope.get("knobs") or [])}
    spec = knobs.get(cand.knob_name)
    if not spec:
        return False
    if not bool(spec.get("hot_apply", False)):
        return False
    req_cap = str(spec.get("capability_required", "")).strip()
    if req_cap and not can_apply(capability, req_cap):
        return False
    stab_cycles = int(spec.get("stabilization_cycles", 0) or 0)
    if not allowed_by_stabilization(stab, cand.module_id, cand.knob_name, stab_cycles):
        return False
    return True


def _candidate_is_ir_valid(
    *,
    cand: PortfolioCandidate,
    tuning_envelope: Dict[str, Any],
    source_cycle_id: str,
    mode: str,
) -> bool:
    """
    Reuse the existing IR validator (typed + bounds).
    """
    ir = {
        "schema_version": "tuning-ir/0.1",
        "ir_hash": "",
        "source_cycle_id": source_cycle_id,
        "mode": mode,
        "module_id": cand.module_id,
        "node_id": cand.node_id,
        "assignments": {cand.knob_name: cand.proposed_value},
        "reason_tags": list(cand.reason_tags),
    }
    ok, _ = validate_tuning_ir_against_envelope(ir, tuning_envelope)
    return bool(ok)


def select_portfolio(
    *,
    candidates: Iterable[PortfolioCandidate],
    tuning_envelopes: Dict[str, Dict[str, Any]],
    capabilities: Dict[str, CapabilityToken],
    stabilization: StabilizationState,
    source_cycle_id: str,
    mode: str = "applied_tune",
    objective_weights: PortfolioObjectiveWeights,
    budgets: PortfolioBudgets,
) -> PortfolioSelection:
    """
    Deterministic "knapsack-lite" optimizer (v0.4):
    - validate each candidate against envelope + capability + stabilization
    - compute scalar score using objective weights
    - stable sort (score desc, then stable id) and greedily pick until budgets/caps are hit
    - assemble module-level tuning IRs (one per module_id) with merged assignments
    """
    # Phase 1: validate and score candidates (filtering out anything not publishable/applicable).
    validated: List[_ValidatedCandidate] = []
    for c in candidates:
        env = tuning_envelopes.get(c.module_id)
        cap = capabilities.get(c.module_id)
        if env is None or cap is None:
            continue
        if not _candidate_is_envelope_eligible(cand=c, tuning_envelope=env, capability=cap, stab=stabilization):
            continue
        if not _candidate_is_ir_valid(cand=c, tuning_envelope=env, source_cycle_id=source_cycle_id, mode=mode):
            continue

        sc = float(score_candidate(c, objective_weights))
        spend_cost, spend_lat = _budget_spend(c.impact)
        validated.append(_ValidatedCandidate(cand=c, score=sc, spend_cost=spend_cost, spend_lat=spend_lat))

    # Deterministic stable ordering.
    # Higher score is "better" (desc), tie-break by (module_id, node_id, knob_name, proposed_value).
    validated.sort(
        key=lambda vc: (
            -vc.score,
            vc.cand.module_id,
            vc.cand.node_id,
            vc.cand.knob_name,
            _stable_value_key(vc.cand.proposed_value),
        )
    )

    # Phase 2: greedy selection under budgets/caps.
    selected: List[PortfolioCandidate] = []
    total_score = 0.0
    # Budget spend accumulators (positive-only deltas).
    spent_lat = 0.0
    spent_cost = 0.0

    # Raw impact totals (can be negative).
    tot_lat = 0.0
    tot_cost = 0.0
    tot_err = 0.0
    tot_thr = 0.0

    def _fits(cost_spend: float, lat_spend: float) -> bool:
        if budgets.max_total_cost_units is not None and (spent_cost + cost_spend) > float(
            budgets.max_total_cost_units
        ):
            return False
        if budgets.max_total_latency_ms_p95 is not None and (spent_lat + lat_spend) > float(
            budgets.max_total_latency_ms_p95
        ):
            return False
        return True

    for vc in validated:
        if len(selected) >= int(budgets.max_changes_per_cycle):
            break
        if not _fits(vc.spend_cost, vc.spend_lat):
            continue
        selected.append(vc.cand)
        total_score += vc.score
        spent_cost += float(vc.spend_cost)
        spent_lat += float(vc.spend_lat)
        # totals are the raw impact sums (not the spend-only sums)
        tot_lat += float(vc.cand.impact.delta_latency_ms_p95)
        tot_cost += float(vc.cand.impact.delta_cost_units)
        tot_err += float(vc.cand.impact.delta_error_rate)
        tot_thr += float(vc.cand.impact.delta_throughput_per_s)

    # Phase 3: assemble per-module tuning IRs (merge knob assignments).
    by_module: Dict[str, Dict[str, Any]] = {}
    for c in selected:
        ir = by_module.get(c.module_id)
        if ir is None:
            ir = {
                "schema_version": "tuning-ir/0.1",
                "ir_hash": "",
                "source_cycle_id": source_cycle_id,
                "mode": mode,
                "module_id": c.module_id,
                "node_id": c.node_id,
                "assignments": {},
                "reason_tags": [],
            }
            by_module[c.module_id] = ir

        # Merge assignments; if the same knob appears twice, keep the first by deterministic order.
        assigns: Dict[str, Any] = ir["assignments"]
        if c.knob_name not in assigns:
            assigns[c.knob_name] = c.proposed_value
        # Merge reason tags deterministically.
        rt = set(ir.get("reason_tags") or [])
        rt.update(c.reason_tags)
        ir["reason_tags"] = sorted(rt)

    # Lock each tuning IR deterministically.
    locked_by_module = {mid: lock_tuning_ir(ir) for mid, ir in sorted(by_module.items(), key=lambda kv: kv[0])}

    return PortfolioSelection(
        selected_candidates=tuple(selected),
        module_tuning_irs=locked_by_module,
        totals=ImpactVector(
            delta_latency_ms_p95=float(tot_lat),
            delta_cost_units=float(tot_cost),
            delta_error_rate=float(tot_err),
            delta_throughput_per_s=float(tot_thr),
        ),
        total_score=float(total_score),
    )


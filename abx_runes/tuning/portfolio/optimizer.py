from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from abx_runes.tuning.emit import lock_tuning_ir
from abx_runes.tuning.validator import validate_tuning_ir_against_envelope
from aal_core.ers.stabilization import allowed_by_stabilization
from aal_core.ers.effects_store import EffectStore, EffectStats, get_effect_mean

from .types import PortfolioPolicy


@dataclass(frozen=True)
class Candidate:
    module_id: str
    node_id: str
    knob: str
    value: Any
    score: float
    est_cost_units: float
    est_latency_ms_p95: float
    reason: str


def _capability_allows(capability: Any, required: str) -> bool:
    if not required:
        return True
    if capability is None:
        return False
    if isinstance(capability, dict):
        allowed = capability.get("allowed") or []
        return required in allowed
    return False


def _unique_stable(xs: List[Any]) -> List[Any]:
    seen: set[str] = set()
    out: List[Any] = []
    for x in xs:
        k = str(x)
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


def _enumerate_values(spec: Dict[str, Any]) -> List[Any]:
    kind = str(spec.get("kind", "")).strip()
    if kind == "bool":
        return [False, True]
    if kind == "enum":
        ev = [str(x) for x in (spec.get("enum_values") or [])]
        return sorted(_unique_stable(ev))

    if kind in ("int", "duration_ms"):
        vals: List[int] = []
        mn = spec.get("min_value")
        mx = spec.get("max_value")
        if mn is not None:
            vals.append(int(mn))
        if mx is not None:
            vals.append(int(mx))
        d = spec.get("default")
        if d is not None:
            try:
                vals.append(int(d))
            except Exception:
                pass
        vals = _unique_stable(vals)
        return sorted(vals)

    if kind == "float":
        vals2: List[float] = []
        mn2 = spec.get("min_value")
        mx2 = spec.get("max_value")
        if mn2 is not None:
            vals2.append(float(mn2))
        if mx2 is not None:
            vals2.append(float(mx2))
        d2 = spec.get("default")
        if d2 is not None:
            try:
                vals2.append(float(d2))
            except Exception:
                pass
        vals2 = _unique_stable(vals2)
        return sorted(vals2)

    return []


def _sig(st: Optional[EffectStats], min_n: int, min_abs: float) -> bool:
    if st is None:
        return True
    if st.n < int(min_n):
        return False
    return abs(float(st.mean)) >= float(min_abs)


def _enumerate_candidates(
    *,
    policy: PortfolioPolicy,
    registry_snapshot: Dict[str, Any],
    metrics_snapshot: Dict[str, Any],
    stabilization_state: Any,
    effects_store: EffectStore,
    min_samples: int,
    min_abs_latency_ms_p95: float,
    min_abs_cost_units: float,
    min_abs_error_rate: float,
    min_abs_throughput_per_s: float,
    allow_unknown_effects_shadow_only: bool,
) -> Tuple[List[Candidate], List[Dict[str, Any]]]:
    """
    v0.5: Candidate impacts come from measured deltas in EffectStore.
    If insufficient samples or below significance thresholds, candidate is excluded.

    Optional: unknown effects may be emitted as shadow-only suggestions (not applied).
    """

    out: List[Candidate] = []
    shadow_only: List[Dict[str, Any]] = []

    for module_id in sorted((registry_snapshot or {}).keys()):
        entry = (registry_snapshot or {}).get(module_id) or {}
        env = entry.get("tuning_envelope") or {}
        if env.get("schema_version") != "tuning-envelope/0.1":
            continue
        knobs = env.get("knobs") or []
        capability = entry.get("capability")

        node_id = str(entry.get("node_id") or module_id)
        mod_metrics = (metrics_snapshot or {}).get(module_id) or {}
        if not isinstance(mod_metrics, dict):
            mod_metrics = {}

        for spec in knobs:
            name = str(spec.get("name", "")).strip()
            if not name:
                continue
            req_cap = str(spec.get("capability_required", "")).strip()
            if req_cap and not _capability_allows(capability, req_cap):
                continue

            stab_cycles = int(spec.get("stabilization_cycles", 0) or 0)
            if not allowed_by_stabilization(stabilization_state, module_id, name, stab_cycles):
                continue

            for v in _enumerate_values(spec):
                # measured deltas: after - before (negative latency delta is good)
                lat = get_effect_mean(
                    effects_store,
                    module_id=module_id,
                    knob=name,
                    value=v,
                    metric_name="latency_ms_p95",
                )
                cost = get_effect_mean(
                    effects_store,
                    module_id=module_id,
                    knob=name,
                    value=v,
                    metric_name="cost_units",
                )
                err = get_effect_mean(
                    effects_store,
                    module_id=module_id,
                    knob=name,
                    value=v,
                    metric_name="error_rate",
                )
                thr = get_effect_mean(
                    effects_store,
                    module_id=module_id,
                    knob=name,
                    value=v,
                    metric_name="throughput_per_s",
                )

                if lat is None and cost is None and err is None and thr is None:
                    if allow_unknown_effects_shadow_only:
                        shadow_only.append(
                            {
                                "module_id": module_id,
                                "node_id": node_id,
                                "knob": name,
                                "value": v,
                                "reason": "unknown_effect_shadow",
                            }
                        )
                    continue

                # significance/noise gates (only apply per metric when present)
                if not _sig(lat, min_samples, min_abs_latency_ms_p95):
                    continue
                if not _sig(cost, min_samples, min_abs_cost_units):
                    continue
                if not _sig(err, min_samples, min_abs_error_rate):
                    continue
                if not _sig(thr, min_samples, min_abs_throughput_per_s):
                    continue

                est_lat = float(lat.mean) if lat else 0.0
                est_cost = float(cost.mean) if cost else 0.0
                est_err = float(err.mean) if err else 0.0
                est_thr = float(thr.mean) if thr else 0.0

                score = (
                    policy.w_latency * (-est_lat)
                    + policy.w_cost * (-est_cost)
                    + policy.w_error * (-est_err)
                    + policy.w_throughput * (est_thr)
                )

                out.append(
                    Candidate(
                        module_id=module_id,
                        node_id=node_id,
                        knob=name,
                        value=v,
                        score=float(score),
                        est_cost_units=max(0.0, float(est_cost)),
                        est_latency_ms_p95=max(0.0, float(est_lat)),
                        reason="measured_effect",
                    )
                )

    return out, shadow_only


def build_portfolio(
    *,
    policy: PortfolioPolicy,
    registry_snapshot: Dict[str, Any],
    metrics_snapshot: Dict[str, Any],
    stabilization_state: Any,
    effects_store: EffectStore,
    # significance / noise gates
    min_samples: int = 3,
    min_abs_latency_ms_p95: float = 1.0,
    min_abs_cost_units: float = 0.05,
    min_abs_error_rate: float = 0.001,
    min_abs_throughput_per_s: float = 0.2,
    allow_unknown_effects_shadow_only: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Deterministic greedy knapsack-lite:
    - score candidates using measured effect sizes
    - stable ordering
    - enforce max_changes and optional budgets
    """

    rejected: List[Dict[str, Any]] = []

    cands, shadow_only = _enumerate_candidates(
        policy=policy,
        registry_snapshot=registry_snapshot,
        metrics_snapshot=metrics_snapshot,
        stabilization_state=stabilization_state,
        effects_store=effects_store,
        min_samples=min_samples,
        min_abs_latency_ms_p95=min_abs_latency_ms_p95,
        min_abs_cost_units=min_abs_cost_units,
        min_abs_error_rate=min_abs_error_rate,
        min_abs_throughput_per_s=min_abs_throughput_per_s,
        allow_unknown_effects_shadow_only=allow_unknown_effects_shadow_only,
    )

    # Noise guard: don't select non-positive expected benefit.
    good: List[Candidate] = []
    for c in cands:
        if c.score <= 0.0:
            rejected.append(
                {
                    "module_id": c.module_id,
                    "knob": c.knob,
                    "value": c.value,
                    "reason": "non_positive_score",
                }
            )
            continue
        good.append(c)

    # Stable ordering: highest score first, then canonical identifiers.
    good.sort(key=lambda c: (-c.score, c.module_id, c.node_id, c.knob, str(c.value)))

    out_irs: List[Dict[str, Any]] = []
    used_cost = 0.0
    used_lat = 0.0

    budget_cost = policy.budget_cost_units
    budget_lat = policy.budget_latency_ms_p95

    for c in good:
        if len(out_irs) >= int(policy.max_changes_per_cycle):
            rejected.append(
                {"module_id": c.module_id, "knob": c.knob, "value": c.value, "reason": "max_changes"}
            )
            continue

        next_cost = used_cost + float(c.est_cost_units)
        next_lat = used_lat + float(c.est_latency_ms_p95)

        if budget_cost is not None and next_cost > float(budget_cost):
            rejected.append(
                {"module_id": c.module_id, "knob": c.knob, "value": c.value, "reason": "budget_cost"}
            )
            continue
        if budget_lat is not None and next_lat > float(budget_lat):
            rejected.append(
                {"module_id": c.module_id, "knob": c.knob, "value": c.value, "reason": "budget_latency"}
            )
            continue

        entry = (registry_snapshot or {}).get(c.module_id) or {}
        env = entry.get("tuning_envelope") or {}

        ir = lock_tuning_ir(
            {
                "schema_version": "tuning-ir/0.1",
                "ir_hash": "",
                "source_cycle_id": policy.source_cycle_id,
                "mode": "applied_tune",
                "module_id": c.module_id,
                "node_id": c.node_id,
                "assignments": {c.knob: c.value},
                "reason_tags": ["portfolio/v0.5", "measured_effect"],
            }
        )

        ok, reason = validate_tuning_ir_against_envelope(ir, env)
        if not ok:
            rejected.append(
                {
                    "module_id": c.module_id,
                    "knob": c.knob,
                    "value": c.value,
                    "reason": f"invalid_ir:{reason}",
                }
            )
            continue

        out_irs.append(ir)
        used_cost = next_cost
        used_lat = next_lat

    notes: Dict[str, Any] = {
        "chosen_count": len(out_irs),
        "emitted_count": len(out_irs),
        "rejected": rejected,
        "shadow_only": shadow_only,
        "budget_used_cost_units": used_cost,
        "budget_used_latency_ms_p95": used_lat,
        "v0.5": {
            "min_samples": min_samples,
            "min_abs_latency_ms_p95": min_abs_latency_ms_p95,
            "min_abs_cost_units": min_abs_cost_units,
            "min_abs_error_rate": min_abs_error_rate,
            "min_abs_throughput_per_s": min_abs_throughput_per_s,
            "allow_unknown_effects_shadow_only": allow_unknown_effects_shadow_only,
        },
    }
    return out_irs, notes


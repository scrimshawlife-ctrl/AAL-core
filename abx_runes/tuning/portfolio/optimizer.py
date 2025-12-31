from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from abx_runes.tuning.emit import lock_tuning_ir
from abx_runes.tuning.validator import validate_tuning_ir_against_envelope
from aal_core.ers.stabilization import allowed_by_stabilization
from aal_core.ers.effects_store import EffectStore, get_effect_stats, stderr

from .types import PortfolioPolicy


@dataclass(frozen=True)
class Candidate:
    module_id: str
    node_id: str
    knob: str
    value: Any
    score: float
    reason: str


def _enumerate_values(knob_spec: Dict[str, Any]) -> List[Any]:
    kind = str(knob_spec.get("kind"))
    if kind == "bool":
        return [False, True]
    if kind == "enum":
        ev = knob_spec.get("enum_values") or []
        return list(ev)
    if kind in ("int", "duration_ms"):
        uniq: List[Any] = []
        for v in (knob_spec.get("min_value"), knob_spec.get("default"), knob_spec.get("max_value")):
            if v is None:
                continue
            try:
                iv = int(v)
            except Exception:
                continue
            if iv not in uniq:
                uniq.append(iv)
        return uniq
    if kind == "float":
        uniq2: List[Any] = []
        for v in (knob_spec.get("min_value"), knob_spec.get("default"), knob_spec.get("max_value")):
            if v is None:
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            if fv not in uniq2:
                uniq2.append(fv)
        return uniq2
    return []


def _enumerate_candidates(
    *,
    registry_snapshot: Dict[str, Any],
    stabilization_state: Any,
    effects_store: EffectStore,
    min_samples: int,
    min_abs_latency_ms_p95: float,
    min_abs_cost_units: float,
    min_abs_error_rate: float,
    min_abs_throughput_per_s: float,
    z_threshold: float,
    allow_unknown_effects_shadow_only: bool,
) -> List[Candidate]:
    out: List[Candidate] = []

    def _sig(st, min_n, min_abs) -> bool:
        if st is None:
            return True
        if st.n < int(min_n):
            return False
        if abs(float(st.mean)) < float(min_abs):
            return False
        se = stderr(st)
        if se is None:
            return False
        if se <= 0.0:
            # zero variance observed: treat as significant if mean passes abs threshold
            return True
        z = abs(float(st.mean)) / float(se)
        return z >= float(z_threshold)

    for module_id, entry in sorted((registry_snapshot or {}).items(), key=lambda kv: str(kv[0])):
        env = (entry or {}).get("tuning_envelope") or {}
        knobs = env.get("knobs") or []
        node_id = str(env.get("node_id") or module_id)

        for kspec in knobs:
            name = str(kspec.get("name"))
            stab_cycles = int(kspec.get("stabilization_cycles", 0) or 0)
            if not allowed_by_stabilization(stabilization_state, str(module_id), name, stab_cycles):
                continue

            for v in _enumerate_values(kspec):
                lat = get_effect_stats(
                    effects_store, module_id=str(module_id), knob=name, value=v, metric_name="latency_ms_p95"
                )
                cost = get_effect_stats(
                    effects_store, module_id=str(module_id), knob=name, value=v, metric_name="cost_units"
                )
                err = get_effect_stats(
                    effects_store, module_id=str(module_id), knob=name, value=v, metric_name="error_rate"
                )
                thr = get_effect_stats(
                    effects_store, module_id=str(module_id), knob=name, value=v, metric_name="throughput_per_s"
                )

                if lat is None and cost is None and err is None and thr is None:
                    if allow_unknown_effects_shadow_only:
                        out.append(
                            Candidate(
                                module_id=str(module_id),
                                node_id=node_id,
                                knob=name,
                                value=v,
                                score=0.0,
                                reason="unknown_effect_shadow",
                            )
                        )
                    continue

                if not _sig(lat, min_samples, min_abs_latency_ms_p95):
                    continue
                if not _sig(cost, min_samples, min_abs_cost_units):
                    continue
                if not _sig(err, min_samples, min_abs_error_rate):
                    continue
                if not _sig(thr, min_samples, min_abs_throughput_per_s):
                    continue

                score = 0.0
                if lat is not None:
                    score += -float(lat.mean)
                if cost is not None:
                    score += -float(cost.mean)
                if err is not None:
                    score += -float(err.mean)
                if thr is not None:
                    score += float(thr.mean)

                out.append(
                    Candidate(
                        module_id=str(module_id),
                        node_id=node_id,
                        knob=name,
                        value=v,
                        score=float(score),
                        reason="measured_effect_significant",
                    )
                )

    return out


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
    z_threshold: float = 2.0,
    allow_unknown_effects_shadow_only: bool = False,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    _ = metrics_snapshot  # v0.6 keeps signature; v0.7 will use for bucketing/attribution

    cands = _enumerate_candidates(
        registry_snapshot=registry_snapshot,
        stabilization_state=stabilization_state,
        effects_store=effects_store,
        min_samples=min_samples,
        min_abs_latency_ms_p95=min_abs_latency_ms_p95,
        min_abs_cost_units=min_abs_cost_units,
        min_abs_error_rate=min_abs_error_rate,
        min_abs_throughput_per_s=min_abs_throughput_per_s,
        z_threshold=z_threshold,
        allow_unknown_effects_shadow_only=allow_unknown_effects_shadow_only,
    )

    # Deterministic ordering: best score desc, then stable tie-breakers.
    cands2 = sorted(
        cands,
        key=lambda c: (-float(c.score), c.module_id, c.node_id, c.knob, str(c.value)),
    )

    out_irs: List[Dict[str, Any]] = []
    for cand in cands2[: max(0, int(policy.max_changes_per_cycle))]:
        env = ((registry_snapshot or {}).get(cand.module_id) or {}).get("tuning_envelope") or {}
        ir = {
            "schema_version": "tuning-ir/0.1",
            "ir_hash": "",
            "source_cycle_id": policy.source_cycle_id,
            "mode": "applied_tune",
            "module_id": cand.module_id,
            "node_id": cand.node_id,
            "assignments": {cand.knob: cand.value},
            "reason_tags": ["portfolio_optimizer_v0.6", cand.reason],
        }
        ir2 = lock_tuning_ir(ir)
        ok, _reason = validate_tuning_ir_against_envelope(ir2, env)
        if not ok:
            continue
        out_irs.append(ir2)

    notes = {
        "schema_version": "portfolio-notes/0.1",
        "optimizer_version": "v0.6",
        "significance_gate": {
            "min_samples": int(min_samples),
            "min_abs_latency_ms_p95": float(min_abs_latency_ms_p95),
            "min_abs_cost_units": float(min_abs_cost_units),
            "min_abs_error_rate": float(min_abs_error_rate),
            "min_abs_throughput_per_s": float(min_abs_throughput_per_s),
            "z_threshold": float(z_threshold),
            "allow_unknown_effects_shadow_only": bool(allow_unknown_effects_shadow_only),
        },
    }
    return out_irs, notes


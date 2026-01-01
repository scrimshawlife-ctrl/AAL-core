from __future__ import annotations

from typing import Any, Dict, List, Tuple

from abx_runes.tuning.hashing import content_hash
from aal_core.ers.effects_store import EffectStore, get_effect_stats


def _stable_key(x: Tuple[Any, ...]) -> Tuple[Any, ...]:
    # tuple ordering is deterministic in Python for comparable types
    return x


def propose_experiments(
    *,
    registry_snapshot: Dict[str, Any],
    effects_store: EffectStore,
    baseline_signature: Dict[str, str],
    source_cycle_id: str,
    max_experiments: int = 2,
    max_risk_units: float = 2.0,
    max_latency_bump_ms_p95: float = 10.0,
    degraded_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Deterministic experiment proposer.

    Constraints:
    - only knobs marked experimentable:true
    - only one knob per module per cycle
    - per-experiment bounds: risk_units <= max_risk_units and expected_latency_bump_ms_p95 <= max_latency_bump_ms_p95
    - global bounds: at most max_experiments and total risk_units <= max_risk_units
    - no proposals in degraded mode

    Scoring (higher is better):
      score = uncertainty + exploration_priority - (risk_units * 0.25) - (latency_bump_ms_p95 / 100)

    Uncertainty is a cheap proxy:
      unc = 1/(n+1) + min(1, variance/100) when variance is available
    """
    if degraded_mode:
        return []

    cands: List[Tuple[float, str, str, str, List[Any], float, float, float, float]] = []
    for module_id, desc in (registry_snapshot or {}).items():
        env = (desc or {}).get("tuning_envelope") or {}
        if env.get("schema_version") != "tuning-envelope/0.1":
            continue
        knobs = env.get("knobs") or []
        node_id = f"node::{module_id}"
        for k in knobs:
            if not bool((k or {}).get("experimentable", False)):
                continue
            name = str((k or {}).get("name", ""))
            kind = str((k or {}).get("kind", ""))
            risk = float((k or {}).get("risk_units", 1.0) or 1.0)
            bump = float((k or {}).get("expected_latency_bump_ms_p95", 0.0) or 0.0)
            priority = float((k or {}).get("exploration_priority", 0.0) or 0.0)

            # Per-experiment safety cap.
            if risk > max_risk_units or bump > max_latency_bump_ms_p95:
                continue

            # Candidate values (cheap/deterministic).
            values: List[Any] = []
            if kind == "enum":
                values = list((k or {}).get("enum_values") or [])
            elif kind == "bool":
                values = [True, False]
            elif kind in ("int", "duration_ms", "float"):
                mn = (k or {}).get("min_value")
                mx = (k or {}).get("max_value")
                if mn is not None:
                    values.append(mn)
                if mx is not None:
                    values.append(mx)
            else:
                continue

            # Need >=2 arms to learn anything.
            if len(values) < 2:
                continue

            best_unc = 0.0
            for v in values:
                st = get_effect_stats(
                    effects_store,
                    module_id=module_id,
                    knob=name,
                    value=v,
                    baseline_signature=baseline_signature,
                    metric_name="latency_ms_p95",
                )
                n = st.n if st else 0
                unc = 1.0 / (n + 1.0)
                if st:
                    vlat = st.variance()
                    if vlat is not None and vlat > 0:
                        unc += min(1.0, vlat / 100.0)
                best_unc = max(best_unc, unc)

            score = best_unc + priority - (risk * 0.25) - (bump / 100.0)
            cands.append((-score, str(module_id), str(node_id), name, values, risk, bump, priority, best_unc))

    cands = sorted(cands, key=_stable_key)

    out: List[Dict[str, Any]] = []
    used_risk = 0.0
    used_modules = set()

    for neg_score, module_id, node_id, name, values, risk, bump, priority, best_unc in cands:
        if len(out) >= max_experiments:
            break
        if module_id in used_modules:
            continue
        if used_risk + risk > max_risk_units:
            continue

        used_risk += risk
        used_modules.add(module_id)

        ir: Dict[str, Any] = {
            "schema_version": "experiment-ir/0.1",
            "experiment_hash": "",
            "source_cycle_id": source_cycle_id,
            "module_id": module_id,
            "node_id": node_id,
            "baseline_signature": dict(baseline_signature),
            "knob_name": name,
            "candidate_values": list(values),
            "trial_plan": {"type": "A/B", "cycles_per_arm": 2, "revert": True},
            "budgets": {"risk_units": risk, "expected_latency_bump_ms_p95": bump},
            "mode": "shadow_experiment",
            "notes": {"uncertainty": best_unc, "priority": priority},
        }
        ir["experiment_hash"] = content_hash(ir, blank_fields=("experiment_hash",))
        out.append(ir)

    return out


from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Optional, Tuple

from aal_core.ers.effects_store import EffectStore, load_effects
from aal_core.ledger.ledger import EvidenceLedger


def _baseline_key(baseline_signature: Dict[str, str]) -> str:
    base = baseline_signature or {}
    return ",".join(f"{k}={base[k]}" for k in sorted(base))


def _extract_baseline_signature(payload: Dict[str, Any]) -> Optional[Dict[str, str]]:
    if not payload:
        return None
    if isinstance(payload.get("baseline_signature"), dict):
        return payload.get("baseline_signature")  # type: ignore[return-value]
    bundle = payload.get("bundle")
    if isinstance(bundle, dict) and isinstance(bundle.get("baseline_signature"), dict):
        return bundle.get("baseline_signature")  # type: ignore[return-value]
    return None


def _iter_effect_keys(store: EffectStore, *, metric_name: str) -> List[Tuple[str, str, str, str]]:
    """
    Returns tuples of (module_id, knob, value_str, baseline_items_str) for keys
    in the v0.7 bucketed format.
    """
    out: List[Tuple[str, str, str, str]] = []
    for k in store.stats_by_key.keys():
        parts = str(k).split("::")
        # v0.7 key: module::knob::value::baseline_items::metric
        if len(parts) != 5:
            continue
        module_id, knob, value_s, baseline_items, metric = parts
        if metric != metric_name:
            continue
        out.append((module_id, knob, value_s, baseline_items))
    # Deterministic ordering
    out.sort(key=lambda t: (t[0], t[1], t[2], t[3]))
    return out


def scan_for_promotions(
    *,
    source_cycle_id: str,
    ledger: EvidenceLedger,
    tail_n: int,
    policy: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Compute promotion proposals with rollback veto, v1.5 exact attribution:
      rollbacks are counted against exact (module, knob, value, baseline_key)

    Note: denominator (trial_counts) is still baseline-wide here (v1.6 makes it exact).
    """

    # --- load effects store (defaults to sibling effects.json next to the ledger)
    effects_path = Path(str(policy.get("effects_path") or (ledger.ledger_path.parent / "effects.json")))
    store = load_effects(effects_path)

    metric_name = str(policy.get("metric_name") or "latency_ms_p95")
    direction = str(policy.get("direction") or "minimize")  # "minimize" or "maximize"

    # IMPORTANT: don't use `or` for numeric policy fields; 0 / 0.0 are valid.
    min_samples = int(policy.get("min_samples", 0) or 0)
    z_threshold = float(policy.get("z_threshold", 0.0) or 0.0)
    min_abs_effect = float(policy.get("min_abs_effect", 0.0) or 0.0)
    max_rollback_rate = float(policy.get("max_rollback_rate", 1.0))

    # --- ledger attribution counts
    tail = ledger.read_tail(int(tail_n))
    rollback_counts: DefaultDict[Tuple[str, str, str, str], int] = defaultdict(int)
    trial_counts: DefaultDict[Tuple[str, str, str, str], int] = defaultdict(int)

    for ent in tail:
        et = ent.get("type")
        payload = ent.get("payload") or {}

        if et == "rollback_emitted":
            rb = (payload or {}).get("rollback") or {}
            mid = str(rb.get("module_id", ""))
            base_key = _baseline_key(rb.get("baseline_signature") or {})
            attempted = rb.get("attempted_assignments") or {}
            if isinstance(attempted, dict):
                for knob, val in attempted.items():
                    rollback_counts[(mid, str(knob), str(val), base_key)] += 1
        elif et in ("bundle_emitted", "portfolio_applied", "experiment_executed"):
            base = _extract_baseline_signature(payload)
            if base is None:
                continue
            base_key = _baseline_key(base)
            # v1.5 minimal denominator: baseline-wide opportunities
            trial_counts[("*", "*", "*", base_key)] += 1

    # --- select best candidate per (module, knob, baseline_items)
    best_by_mkb: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for module_id, knob, value_s, baseline_items in _iter_effect_keys(store, metric_name=metric_name):
        stats = store.stats_by_key.get(f"{module_id}::{knob}::{value_s}::{baseline_items}::{metric_name}")
        if stats is None:
            continue
        if stats.n < min_samples:
            continue

        mean = stats.mean()
        if mean is None:
            continue
        if abs(float(mean)) < min_abs_effect:
            continue

        var = stats.variance()
        if var is None or var <= 0.0:
            z = float("inf") if mean != 0 else 0.0
        else:
            se = math.sqrt(var / float(stats.n))
            z = abs(float(mean)) / se if se > 0 else float("inf")
        if z < z_threshold:
            continue

        # score: higher is better
        score = (-float(mean)) if direction == "minimize" else float(mean)
        key = (module_id, knob, baseline_items)
        cur = best_by_mkb.get(key)
        if cur is None or score > float(cur["score"]) or (score == float(cur["score"]) and value_s < str(cur["value"])):
            best_by_mkb[key] = {
                "module_id": module_id,
                "knob": knob,
                "value": value_s,
                "baseline_items": baseline_items,
                "metric_name": metric_name,
                "mean_delta": float(mean),
                "z": float(z),
                "n": int(stats.n),
                "score": float(score),
            }

    proposals: List[Dict[str, Any]] = []
    for _, cand in sorted(best_by_mkb.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2])):
        module_id = str(cand["module_id"])
        knob = str(cand["knob"])
        value = str(cand["value"])
        baseline_key = str(cand["baseline_items"])

        rb = rollback_counts.get((module_id, knob, value, baseline_key), 0)
        tr = trial_counts.get(("*", "*", "*", baseline_key), 0)
        rr = float(rb) / float(tr) if tr > 0 else 0.0
        if rr > max_rollback_rate:
            continue

        proposals.append(
            {
                "source_cycle_id": str(source_cycle_id),
                "module_id": module_id,
                "knob": knob,
                "value": value,
                "baseline_key": baseline_key,
                "metric_name": str(cand["metric_name"]),
                "mean_delta": float(cand["mean_delta"]),
                "z": float(cand["z"]),
                "n": int(cand["n"]),
                "rollback_rate": float(rr),
            }
        )

    return proposals


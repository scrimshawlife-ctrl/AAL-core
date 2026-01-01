from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from aal_core.ers.effects_store import EffectStore, get_effect_stats
from aal_core.ers.baseline_similarity import similarity


def _candidate_values_for_knob(spec: Dict[str, Any]) -> List[Any]:
    kind = str(spec.get("kind"))
    default = spec.get("default")

    if kind == "enum":
        vals = spec.get("enum_values") or []
        return list(vals)
    if kind == "bool":
        return [False, True]

    # numeric kinds
    mn = spec.get("min_value")
    mx = spec.get("max_value")
    out: List[Any] = []
    if mn is not None:
        out.append(int(mn) if kind in ("int", "duration_ms") else float(mn))
    if mx is not None:
        out.append(int(mx) if kind in ("int", "duration_ms") else float(mx))
    if default is not None:
        out.append(default)

    # Deduplicate deterministically by string form
    seen = set()
    uniq: List[Any] = []
    for v in out:
        k = str(v)
        if k in seen:
            continue
        seen.add(k)
        uniq.append(v)
    return uniq


def _parse_baseline_items(items: str) -> Dict[str, str]:
    if not items:
        return {}
    parts = [p for p in str(items).split(",") if p]
    out: Dict[str, str] = {}
    for p in parts:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        out[str(k)] = str(v)
    return out


def _stderr(rs: Any) -> Optional[float]:
    """
    Standard error of the mean from RunningStats.
    Returns None if not computable.
    """
    try:
        n = int(getattr(rs, "n"))
    except Exception:
        return None
    if n <= 1:
        return None
    var = rs.variance()
    if var is None:
        return None
    var = float(var)
    if var <= 0.0:
        return None
    return math.sqrt(var / float(n))


def build_portfolio(
    *,
    effects_store: EffectStore,
    tuning_envelope: Dict[str, Any],
    baseline_signature: Dict[str, str],
    metric_name: str = "latency_ms_p95",
    allow_shadow_only: bool = False,
    enable_cross_bucket_shadow: bool = True,
    min_similarity: float = 0.75,
    shadow_penalty: float = 0.5,
    z_threshold_shadow: float = 3.0,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Bucket-aware portfolio selection (v0.8).

    - Uses only effects from (module, knob, value, baseline_signature, metric_name)
    - If no bucket-specific stats exist for a knob, optional shadow-only selection:
      - If enabled, may generalize shadow-only from similar buckets with penalties and stricter z
      - Never applies cross-bucket; applied tuning remains bucket-local
    """
    module_id = str(tuning_envelope.get("module_id"))
    knobs = list(tuning_envelope.get("knobs") or [])

    applied: Dict[str, Any] = {}
    shadow_only: Dict[str, Any] = {}
    excluded: Dict[str, str] = {}
    shadow_cross_bucket: Dict[str, Any] = {}

    # Deterministic traversal
    for spec in sorted(knobs, key=lambda k: str(k.get("name"))):
        name = str(spec.get("name"))
        candidates = _candidate_values_for_knob(spec)
        if not candidates:
            excluded[name] = "no_candidates"
            continue

        best_val: Optional[Any] = None
        best_score: Optional[float] = None

        any_bucket_local = False
        for v in candidates:
            st = get_effect_stats(
                effects_store,
                module_id=module_id,
                knob=name,
                value=v,
                baseline_signature=baseline_signature,
                metric_name=metric_name,
            )
            if st is None:
                continue
            any_bucket_local = True
            m = st.mean()
            if m is None:
                continue
            # minimize mean delta (negative is better if latency decreases)
            if best_score is None or m < best_score or (m == best_score and str(v) < str(best_val)):
                best_score = m
                best_val = v

        if best_val is None:
            # v0.8: optional cross-bucket shadow generalization (still never applied)
            if enable_cross_bucket_shadow:
                best_shadow_val: Optional[Any] = None
                best_shadow_est: Optional[float] = None
                best_explain: Optional[Dict[str, Any]] = None

                for v in candidates:
                    buckets = effects_store.buckets_for(module_id=module_id, knob=name, value=v)
                    donors: List[Dict[str, Any]] = []
                    weighted_sum = 0.0
                    weight_total = 0.0

                    for baseline_items, metrics in sorted(buckets.items(), key=lambda x: x[0]):
                        donor_sig = _parse_baseline_items(baseline_items)
                        sim = similarity(baseline_signature, donor_sig)
                        if sim < float(min_similarity):
                            continue
                        rs = (metrics or {}).get(metric_name)
                        if rs is None:
                            continue
                        m = rs.mean()
                        if m is None:
                            continue
                        se = _stderr(rs)
                        if se is None or se <= 0.0:
                            continue
                        z = abs(float(m)) / float(se)
                        if z < float(z_threshold_shadow):
                            continue

                        w = float(sim)
                        weighted_sum += w * float(m)
                        weight_total += w
                        donors.append(
                            {
                                "baseline_items": baseline_items,
                                "baseline_signature": dict(donor_sig),
                                "similarity": float(sim),
                                "weight": float(w),
                                "donor_n": int(rs.n),
                                "donor_mean": float(m),
                                "donor_stderr": float(se),
                                "donor_z": float(z),
                            }
                        )

                    if not donors or weight_total <= 0.0:
                        continue

                    # Similarity-weighted estimate, then apply penalty to magnitude (shadow-only).
                    est = (weighted_sum / weight_total) * float(shadow_penalty)
                    if best_shadow_est is None or est < best_shadow_est or (est == best_shadow_est and str(v) < str(best_shadow_val)):
                        best_shadow_est = float(est)
                        best_shadow_val = v
                        best_explain = {
                            "metric_name": metric_name,
                            "estimated_effect_mean": float(est),
                            "penalty_applied": float(shadow_penalty),
                            "min_similarity": float(min_similarity),
                            "z_threshold_shadow": float(z_threshold_shadow),
                            "donors": donors,
                            "why_shadow_only": "cross_bucket_shadow_inference (never applied; bucket-local promotion still evidence-gated)",
                        }

                if best_shadow_val is not None and best_explain is not None:
                    shadow_cross_bucket[name] = {"suggested_value": best_shadow_val, **best_explain}
                    if allow_shadow_only:
                        shadow_only[name] = best_shadow_val
                        excluded[name] = "cross_bucket_shadow"
                    else:
                        # Keep v0.7 exclusion semantics, but preserve explainability in notes.
                        excluded[name] = "no_bucket_stats" if not any_bucket_local else "no_usable_bucket_stats"
                    continue

            if allow_shadow_only:
                shadow_only[name] = spec.get("default")
                excluded[name] = "shadow_only_no_bucket_stats"
            else:
                excluded[name] = "no_bucket_stats"
            continue

        applied[name] = best_val

    notes = {
        "module_id": module_id,
        "metric_name": metric_name,
        "baseline_signature": dict(baseline_signature),
        "excluded": excluded,
        "shadow_only": shadow_only,
        "shadow_cross_bucket": shadow_cross_bucket,
    }
    return applied, notes


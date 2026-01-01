from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aal_core.ers.effects_store import EffectStore, get_effect_stats
from aal_core.runtime.promotion_overlay import PromotionOverlay, apply_promoted_defaults


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


def build_portfolio(
    *,
    effects_store: EffectStore,
    tuning_envelope: Dict[str, Any],
    baseline_signature: Dict[str, str],
    metric_name: str = "latency_ms_p95",
    allow_shadow_only: bool = False,
    promotion_overlay: PromotionOverlay | None = None,
    policy: Dict[str, Any] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Bucket-aware portfolio selection (v0.7).

    - Uses only effects from (module, knob, value, baseline_signature, metric_name)
    - If no bucket-specific stats exist for a knob:
      - default: exclude
      - optional: return it as shadow-only (not applied) so learning can begin
    """
    module_id = str(tuning_envelope.get("module_id"))
    knobs = list(tuning_envelope.get("knobs") or [])

    policy = policy or {}
    promotion_overlay = promotion_overlay or PromotionOverlay.load(
        bias_weight=float(policy.get("promotion_bias_weight", 0.15))
    )

    applied: Dict[str, Any] = {}
    shadow_only: Dict[str, Any] = {}
    excluded: Dict[str, str] = {}
    promotion_candidates_boosted = 0
    promotion_knobs_selected = 0

    # Deterministic traversal
    for spec in sorted(knobs, key=lambda k: str(k.get("name"))):
        name = str(spec.get("name"))
        candidates = _candidate_values_for_knob(spec)
        if not candidates:
            excluded[name] = "no_candidates"
            continue

        best_val: Optional[Any] = None
        best_score: Optional[float] = None

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
            m = st.mean()
            if m is None:
                continue
            # minimize mean delta (negative is better if latency decreases)
            bias = promotion_overlay.score_bias(
                module_id=module_id,
                knob=name,
                value=v,
                baseline_signature=baseline_signature,
            )
            if bias:
                promotion_candidates_boosted += 1
            score = float(m) - float(bias)

            if best_score is None or score < best_score or (score == best_score and str(v) < str(best_val)):
                best_score = score
                best_val = v

        if best_val is None:
            if allow_shadow_only:
                shadow_only[name] = spec.get("default")
                excluded[name] = "shadow_only_no_bucket_stats"
            else:
                excluded[name] = "no_bucket_stats"
            continue

        applied[name] = best_val
        pv = promotion_overlay.get_promoted_value(
            module_id=module_id,
            knob=name,
            baseline_signature=baseline_signature,
        )
        if pv is not None and str(pv) == str(best_val):
            promotion_knobs_selected += 1

    # Default starting assignments (baseline-scoped, does not override explicit picks)
    applied_with_defaults = apply_promoted_defaults(
        module_id=module_id,
        baseline_signature=baseline_signature,
        current_assignments=applied,
        knobs=knobs,
        overlay=promotion_overlay,
    )
    promoted_defaults_applied = sorted(list(set(applied_with_defaults.keys()) - set(applied.keys())))
    # If we ended up applying a promoted default, it's no longer "excluded" or "shadow-only" for that knob.
    for name in promoted_defaults_applied:
        excluded.pop(name, None)
        shadow_only.pop(name, None)
    applied = applied_with_defaults

    notes = {
        "module_id": module_id,
        "metric_name": metric_name,
        "baseline_signature": dict(baseline_signature),
        "excluded": excluded,
        "shadow_only": shadow_only,
        "promotion_candidates_boosted": int(promotion_candidates_boosted),
        "promotion_knobs_selected": int(promotion_knobs_selected),
        "promoted_defaults_applied": promoted_defaults_applied,
    }
    return applied, notes


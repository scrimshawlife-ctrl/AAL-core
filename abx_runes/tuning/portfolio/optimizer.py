from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from aal_core.ers.effects_store import EffectStore, get_effect_stats
from aal_core.ers.safe_set_store import SafeSetStore, safe_set_key


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
    safe_set_mode: bool = False,
    safe_set_store: SafeSetStore | None = None,
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

    applied: Dict[str, Any] = {}
    shadow_only: Dict[str, Any] = {}
    excluded: Dict[str, str] = {}

    safe_set_store = safe_set_store or SafeSetStore.load()

    # Deterministic traversal
    for spec in sorted(knobs, key=lambda k: str(k.get("name"))):
        name = str(spec.get("name"))
        candidates = _candidate_values_for_knob(spec)
        if not candidates:
            excluded[name] = "no_candidates"
            continue

        # Optional safe-set bias: if a derived safe-set exists for this knob/bucket,
        # prefer candidates inside it.
        if safe_set_mode:
            skey = safe_set_key(module_id=module_id, knob=name, baseline_signature=baseline_signature)
            derived = safe_set_store.get(skey, now_idx=0)
            if derived:
                filtered = list(candidates)
                if derived.get("kind") == "enum":
                    allowed = {str(v) for v in (derived.get("safe_values") or [])}
                    filtered = [v for v in candidates if str(v) in allowed]
                elif derived.get("kind") == "numeric":
                    mn = derived.get("safe_min")
                    mx = derived.get("safe_max")
                    try:
                        filtered = [v for v in candidates if float(mn) <= float(v) <= float(mx)]
                    except Exception:
                        filtered = []
                if filtered:
                    candidates = filtered

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
            if best_score is None or m < best_score or (m == best_score and str(v) < str(best_val)):
                best_score = m
                best_val = v

        if best_val is None:
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
    }
    return applied, notes


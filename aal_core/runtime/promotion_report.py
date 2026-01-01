from __future__ import annotations

from typing import Any, Dict, List, Optional

from aal_core.ers.safe_set_store import SafeSetStore, safe_set_key
from aal_core.runtime.promotion_overlay import PromotionOverlay


def _omit_if_none(d: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None}


def build_promotion_report(
    *,
    module_id: str,
    baseline_signature: Dict[str, str],
    candidates: List[Dict[str, Any]],
    selected: List[Dict[str, Any]],
    overlay: PromotionOverlay,
    safe_set_store: Optional[SafeSetStore] = None,
    attempt_stats: Optional[Dict[str, Dict[str, float]]] = None,
    promotion_bias_weight: float,
) -> Dict[str, Any]:
    """
    candidates/selected items are lightweight dicts with at least:
      - knob (str)
      - value (Any)
    attempt_stats (optional):
      {
        "promoted": {"attempts": int, "rollbacks": int},
        "unpromoted": {"attempts": int, "rollbacks": int}
      }
    """
    safe_set_store = safe_set_store or SafeSetStore.load()

    cand_total = len(candidates)
    sel_total = len(selected)

    cand_with_promo = 0
    sel_with_promo = 0

    # Safe-set intersection counts
    ss_sel_promoted = 0
    ss_sel_unpromoted = 0
    sel_promoted = 0
    sel_unpromoted = 0

    for c in candidates:
        k = str(c.get("knob", ""))
        pv = overlay.get_promoted_value(
            module_id=module_id, knob=k, baseline_signature=baseline_signature
        )
        if pv is not None:
            cand_with_promo += 1

    for s in selected:
        k = str(s.get("knob", ""))
        v = s.get("value")
        pv = overlay.get_promoted_value(
            module_id=module_id, knob=k, baseline_signature=baseline_signature
        )
        promoted = pv is not None and str(pv) == str(v)
        if promoted:
            sel_with_promo += 1
            sel_promoted += 1
        else:
            sel_unpromoted += 1

        # safe-set intersection (if derived safe-set exists)
        skey = safe_set_key(module_id=module_id, knob=k, baseline_signature=baseline_signature)
        ss = safe_set_store.get(skey, now_idx=10**18)
        if ss:
            if ss.get("kind") == "enum":
                ok = str(v) in set(ss.get("safe_values") or [])
            else:
                try:
                    ok = float(ss.get("safe_min")) <= float(v) <= float(ss.get("safe_max"))
                except Exception:
                    ok = False
            if promoted and ok:
                ss_sel_promoted += 1
            if (not promoted) and ok:
                ss_sel_unpromoted += 1

    # rollback rates (optional)
    rr_promoted = None
    rr_unpromoted = None
    if attempt_stats:
        ap = attempt_stats.get("promoted") or {}
        au = attempt_stats.get("unpromoted") or {}
        if ap.get("attempts", 0) > 0:
            rr_promoted = float(ap.get("rollbacks", 0)) / float(ap.get("attempts"))
        if au.get("attempts", 0) > 0:
            rr_unpromoted = float(au.get("rollbacks", 0)) / float(au.get("attempts"))

    report = {
        "candidates_total": cand_total,
        "candidates_with_promotion_available": cand_with_promo,
        "selected_total": sel_total,
        "selected_with_promotion": sel_with_promo,
        "promotion_bias_weight": float(promotion_bias_weight),
        "rollback_rate_promoted": rr_promoted,
        "rollback_rate_unpromoted": rr_unpromoted,
        "safe_set_intersection_rate_promoted": (
            (ss_sel_promoted / sel_promoted) if sel_promoted > 0 else None
        ),
        "safe_set_intersection_rate_unpromoted": (
            (ss_sel_unpromoted / sel_unpromoted) if sel_unpromoted > 0 else None
        ),
    }

    return _omit_if_none(report)


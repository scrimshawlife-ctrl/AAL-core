from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from aal_core.governance.promotion_policy import PromotionPolicy


def _baseline_key(sig: Dict[str, str]) -> str:
    return ",".join(f"{k}={sig[k]}" for k in sorted(sig))


@dataclass(frozen=True)
class PromotionOverlay:
    """
    Baseline-scoped overlay of promoted knob values.
    Promotions are *preferences*, not hard locks.
    """

    by_module_and_base: Dict[Tuple[str, str], Dict[str, Any]]
    bias_weight: float

    @classmethod
    def load(cls, *, bias_weight: float = 0.15) -> "PromotionOverlay":
        pol = PromotionPolicy.load()

        # Deterministic merge: sort by stable keys and let later items win.
        indexed = list(enumerate(pol.items))

        def _sort_key(pair: tuple[int, Dict[str, Any]]):
            i, it = pair
            mid = str(it.get("module_id", ""))
            knob = str(it.get("knob", ""))
            base = it.get("baseline_signature") or {}
            bkey = _baseline_key(base if isinstance(base, dict) else {})
            at_idx = it.get("at_idx")
            at = int(at_idx) if isinstance(at_idx, int) or (isinstance(at_idx, str) and at_idx.isdigit()) else -1
            return (mid, bkey, knob, at, i)

        by: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for _, it in sorted(indexed, key=_sort_key):
            if it.get("revoked_at_idx") is not None:
                continue
            mid = str(it.get("module_id", ""))
            knob = str(it.get("knob", ""))
            val = it.get("value")
            base = it.get("baseline_signature") or {}
            bkey = _baseline_key(base if isinstance(base, dict) else {})
            key = (mid, bkey)
            if key not in by:
                by[key] = {}
            by[key][knob] = val

        return cls(by_module_and_base=by, bias_weight=float(bias_weight))

    def get_promoted_value(
        self,
        *,
        module_id: str,
        knob: str,
        baseline_signature: Dict[str, str],
    ) -> Optional[Any]:
        key = (str(module_id), _baseline_key(baseline_signature or {}))
        d = self.by_module_and_base.get(key)
        if not d:
            return None
        return d.get(str(knob))

    def score_bias(
        self,
        *,
        module_id: str,
        knob: str,
        value: Any,
        baseline_signature: Dict[str, str],
    ) -> float:
        pv = self.get_promoted_value(module_id=module_id, knob=knob, baseline_signature=baseline_signature)
        if pv is None:
            return 0.0
        return self.bias_weight if str(pv) == str(value) else 0.0


def apply_promoted_defaults(
    *,
    module_id: str,
    baseline_signature: Dict[str, str],
    current_assignments: Dict[str, Any],
    knobs: list[Dict[str, Any]],
    overlay: PromotionOverlay,
) -> Dict[str, Any]:
    """
    Fill missing knob assignments with promoted values (baseline-scoped).
    Does not override explicit current values.
    """
    out = dict(current_assignments or {})
    for k in knobs or []:
        name = str(k.get("name", ""))
        if not name:
            continue
        if name in out:
            continue
        pv = overlay.get_promoted_value(module_id=module_id, knob=name, baseline_signature=baseline_signature)
        if pv is not None:
            out[name] = pv
    return out


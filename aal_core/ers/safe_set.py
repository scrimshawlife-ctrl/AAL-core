from __future__ import annotations

from typing import Any, Dict


def value_in_safe_set(spec: Dict[str, Any], value: Any) -> bool:
    """
    v1.8 compatibility: interpret "safe set" fields on a knob spec.

    - enum: safe_values (preferred) else enum_values
    - numeric: safe_min/safe_max (preferred) else min_value/max_value
    """
    kind = str(spec.get("kind"))

    if kind == "enum":
        allowed = spec.get("safe_values")
        if allowed is None:
            allowed = spec.get("enum_values") or []
        return str(value) in {str(v) for v in (allowed or [])}

    if kind == "bool":
        # both values are always safe unless explicitly constrained
        allowed = spec.get("safe_values")
        if allowed is not None:
            return str(value) in {str(v) for v in (allowed or [])}
        return isinstance(value, bool)

    # numeric kinds
    mn = spec.get("safe_min")
    mx = spec.get("safe_max")
    if mn is None:
        mn = spec.get("min_value")
    if mx is None:
        mx = spec.get("max_value")
    try:
        fv = float(value)
    except Exception:
        return False

    if mn is not None and fv < float(mn):
        return False
    if mx is not None and fv > float(mx):
        return False
    return True


def knob_risk_units(spec: Dict[str, Any], value: Any) -> float:
    """
    Placeholder risk metric used by experimental planners.
    Kept deterministic and conservative.
    """
    _ = (spec, value)
    return 1.0


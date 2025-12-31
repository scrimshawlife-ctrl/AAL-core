from __future__ import annotations

from typing import Any, Dict, Tuple

from .types import TuningEnvelope, KnobSpec, TuningIR


class TuningValidationError(ValueError):
    pass


def _index_knobs(env: TuningEnvelope) -> Dict[str, KnobSpec]:
    idx: Dict[str, KnobSpec] = {}
    for k in env.knobs:
        if k.name in idx:
            raise TuningValidationError(f"duplicate_knob:{k.name}")
        idx[k.name] = k
    return idx


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise TuningValidationError(msg)


def validate_tuning_ir_against_envelope(ir: Dict[str, Any], env: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Pure-dict validator (no runtime class requirement).
    Used by ERS + tests.
    """
    try:
        _require(ir.get("schema_version") == "tuning-ir/0.1", "bad_schema_version:ir")
        _require(env.get("schema_version") == "tuning-envelope/0.1", "bad_schema_version:env")
        _require(ir.get("module_id") == env.get("module_id"), "module_mismatch")

        knobs = {k["name"]: k for k in (env.get("knobs") or [])}
        assigns: Dict[str, Any] = ir.get("assignments") or {}

        # no unknown knobs
        for name in assigns.keys():
            _require(name in knobs, f"unknown_knob:{name}")

        for name, val in assigns.items():
            spec = knobs[name]
            kind = spec.get("kind")

            if kind == "bool":
                _require(isinstance(val, bool), f"type_mismatch:{name}")
            elif kind in ("int", "duration_ms"):
                _require(isinstance(val, int) and not isinstance(val, bool), f"type_mismatch:{name}")
                mn = spec.get("min_value")
                mx = spec.get("max_value")
                if mn is not None:
                    _require(val >= int(mn), f"below_min:{name}")
                if mx is not None:
                    _require(val <= int(mx), f"above_max:{name}")
            elif kind == "float":
                _require((isinstance(val, int) and not isinstance(val, bool)) or isinstance(val, float), f"type_mismatch:{name}")
                fval = float(val)
                mn = spec.get("min_value")
                mx = spec.get("max_value")
                if mn is not None:
                    _require(fval >= float(mn), f"below_min:{name}")
                if mx is not None:
                    _require(fval <= float(mx), f"above_max:{name}")
            elif kind == "enum":
                _require(isinstance(val, str), f"type_mismatch:{name}")
                ev = spec.get("enum_values") or []
                _require(val in ev, f"enum_invalid:{name}")
            else:
                raise TuningValidationError(f"unknown_kind:{name}:{kind}")

        return True, "ok"
    except Exception as e:
        return False, str(e)

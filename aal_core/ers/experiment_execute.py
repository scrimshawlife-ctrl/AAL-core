from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from aal_core.ers.baseline import compute_baseline_signature
from aal_core.ers.safe_set import value_in_safe_set, knob_risk_units
from aal_core.ers.safe_set_store import SafeSetStore, safe_set_key


@dataclass(frozen=True)
class ExperimentResult:
    status: str  # "ok" | "skipped"
    reason: str
    candidates: List[Any]


def _candidate_values_for_knob(spec: Dict[str, Any]) -> List[Any]:
    kind = str(spec.get("kind"))
    default = spec.get("default")

    if kind == "enum":
        return list(spec.get("enum_values") or [])
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


def execute_experiment_ir(
    *,
    module_id: str,
    knob: str,
    knob_spec: Dict[str, Any],
    metrics_snapshot: Dict[str, Any],
    safe_set_mode: bool = False,
    safe_set_store: Optional[SafeSetStore] = None,
) -> ExperimentResult:
    """
    Minimal experiment executor shim.

    It produces candidate values for a knob and applies safe-set gating when enabled:
    - Prefer derived safe sets from SafeSetStore keyed by (module, knob, baseline_bucket)
    - Fall back to knob_spec's static safe fields (v1.8) if no derived entry exists
    """
    _ = knob_risk_units(knob_spec, knob_spec.get("default"))

    vals = _candidate_values_for_knob(knob_spec)
    baseline = compute_baseline_signature(metrics_snapshot or {})

    if safe_set_mode:
        safe_set_store = safe_set_store or SafeSetStore.load()
        skey = safe_set_key(module_id=str(module_id), knob=str(knob), baseline_signature=baseline)

        # Executor does not know the current ledger idx; builder prunes expired entries.
        derived = safe_set_store.get(skey, now_idx=0)
        if derived:
            if derived.get("kind") == "enum":
                allowed = {str(v) for v in (derived.get("safe_values") or [])}
                vals = [v for v in vals if str(v) in allowed]
            elif derived.get("kind") == "numeric":
                mn = derived.get("safe_min")
                mx = derived.get("safe_max")
                try:
                    vals = [v for v in vals if float(mn) <= float(v) <= float(mx)]
                except Exception:
                    vals = []
        else:
            vals = [v for v in vals if value_in_safe_set(knob_spec, v)]

        if len(vals) < 2:
            return ExperimentResult(status="skipped", reason="safe_set_blocked", candidates=vals)

    return ExperimentResult(status="ok", reason="ok", candidates=vals)


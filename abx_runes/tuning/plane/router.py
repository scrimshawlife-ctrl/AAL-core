from __future__ import annotations

from typing import Any, Dict, List, Tuple

from abx_runes.tuning.emit import lock_tuning_ir
from abx_runes.tuning.hashing import content_hash
from abx_runes.tuning.portfolio.optimizer import build_portfolio

from aal_core.ers.baseline import compute_baseline_signature
from aal_core.ers.effects_store import EffectStore


def _root_metrics(metrics_snapshot: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically choose a representative metrics dict for baseline derivation.
    """
    root = metrics_snapshot.get("__global__")
    if isinstance(root, dict):
        return root
    if metrics_snapshot:
        first = sorted(str(k) for k in metrics_snapshot.keys())[0]
        v = metrics_snapshot.get(first)
        if isinstance(v, dict):
            return v
    return {}


def _lock_portfolio_ir(portfolio_ir: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(portfolio_ir)
    d["portfolio_hash"] = ""
    out = dict(d)
    out["portfolio_hash"] = content_hash(d)
    return out


def _lock_experiment_ir(experiment_ir: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(experiment_ir)
    d["experiment_hash"] = ""
    out = dict(d)
    out["experiment_hash"] = content_hash(d)
    return out


def _count_assignments(tuning_ir: Dict[str, Any]) -> int:
    assigns = tuning_ir.get("assignments") or {}
    if not isinstance(assigns, dict):
        return 0
    return len(assigns)


def _budget_cap_assignments(
    *,
    applied: Dict[str, Any],
    remaining: int,
) -> Tuple[Dict[str, Any], int]:
    """
    Deterministically cap knob assignments to remaining budget.
    """
    if remaining <= 0 or not applied:
        return {}, remaining
    out: Dict[str, Any] = {}
    for k in sorted(applied.keys()):
        if remaining <= 0:
            break
        out[k] = applied[k]
        remaining -= 1
    return out, remaining


def build_tuning_plane_bundle(
    *,
    source_cycle_id: str,
    registry_snapshot: Dict[str, Any],
    metrics_snapshot: Dict[str, Any],
    effects_store: EffectStore,
    stabilization_state: Any,  # reserved for v1.1 risk/stability logic
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    """
    v1.0 unified router: emits one bundle with exploit + explore.

    Determinism:
    - stable iteration ordering
    - canonical hashing for provenance locks
    """
    _ = stabilization_state  # v1.0: not used for routing decisions

    baseline = compute_baseline_signature(_root_metrics(metrics_snapshot))

    degraded = bool(policy.get("degraded_mode", False))
    enable_explore = bool(policy.get("enable_explore", True)) and not degraded

    # shared budgets (v1.0 minimal): total knob assignments across exploit+explore
    max_changes = int(policy.get("max_changes_per_cycle", 6))
    remaining = max_changes

    portfolio_items: List[Dict[str, Any]] = []
    portfolio_notes: Dict[str, Any] = {"modules": {}}

    # Exploit: per-module applied tuning IRs (bucket-local effects)
    for module_id in sorted(str(k) for k in (registry_snapshot or {}).keys()):
        entry = (registry_snapshot or {}).get(module_id) or {}
        tuning_envelope = entry.get("tuning_envelope") or {}
        if not isinstance(tuning_envelope, dict) or not tuning_envelope:
            portfolio_notes["modules"][module_id] = {"skipped": "missing_tuning_envelope"}
            continue

        # module-local metrics preferred; fallback to root metrics for baseline compatibility
        mod_metrics = metrics_snapshot.get(module_id)
        if not isinstance(mod_metrics, dict):
            mod_metrics = _root_metrics(metrics_snapshot)

        applied, notes = build_portfolio(
            effects_store=effects_store,
            tuning_envelope=tuning_envelope,
            baseline_signature=baseline,
            metric_name=str(policy.get("portfolio_metric_name", "latency_ms_p95")),
            allow_shadow_only=False,  # golden: no bucket stats => no exploit
        )

        # enforce shared budget; exploit has priority
        capped, remaining = _budget_cap_assignments(applied=applied, remaining=remaining)
        if not capped:
            portfolio_notes["modules"][module_id] = {"notes": notes, "skipped": "no_exploit_items"}
            continue

        node_id = str(entry.get("node_id") or module_id)
        tuning_ir = lock_tuning_ir(
            {
                "schema_version": "tuning-ir/0.1",
                "ir_hash": "",
                "source_cycle_id": source_cycle_id,
                "mode": "applied_tune",
                "module_id": module_id,
                "node_id": node_id,
                "assignments": capped,
                "reason_tags": ["portfolio_exploit_v1"],
            }
        )
        portfolio_items.append(tuning_ir)
        portfolio_notes["modules"][module_id] = {"notes": notes, "applied_knobs": sorted(capped.keys())}

        if remaining <= 0:
            break

    portfolio_ir = _lock_portfolio_ir(
        {
            "schema_version": "portfolio-tuning-ir/0.1",
            "portfolio_hash": "",
            "source_cycle_id": source_cycle_id,
            "baseline_signature": dict(baseline),
            "policy": dict(policy),
            "items": portfolio_items,
            "notes": portfolio_notes,
        }
    )

    # Explore: propose shadow experiments for knobs without bucket stats (defaults)
    experiments: List[Dict[str, Any]] = []
    if enable_explore and remaining > 0:
        max_experiments = int(policy.get("max_experiments", 2))

        for module_id in sorted(str(k) for k in (registry_snapshot or {}).keys()):
            if len(experiments) >= max_experiments or remaining <= 0:
                break

            entry = (registry_snapshot or {}).get(module_id) or {}
            tuning_envelope = entry.get("tuning_envelope") or {}
            if not isinstance(tuning_envelope, dict) or not tuning_envelope:
                continue

            # Identify shadow-only knobs deterministically by reusing the portfolio helper
            _applied_ignored, notes = build_portfolio(
                effects_store=effects_store,
                tuning_envelope=tuning_envelope,
                baseline_signature=baseline,
                metric_name=str(policy.get("portfolio_metric_name", "latency_ms_p95")),
                allow_shadow_only=True,
            )
            shadow_only = (notes or {}).get("shadow_only") or {}
            if not isinstance(shadow_only, dict) or not shadow_only:
                continue

            # Do not experiment on knobs already used by exploit in this bundle
            exploit_knobs: set[str] = set()
            for it in portfolio_items:
                if it.get("module_id") != module_id:
                    continue
                assigns = it.get("assignments") or {}
                if isinstance(assigns, dict):
                    exploit_knobs |= set(str(k) for k in assigns.keys())

            filtered = {k: v for k, v in shadow_only.items() if str(k) not in exploit_knobs}
            capped, remaining = _budget_cap_assignments(applied=filtered, remaining=remaining)
            if not capped:
                continue

            node_id = str(entry.get("node_id") or module_id)
            tuning_ir = lock_tuning_ir(
                {
                    "schema_version": "tuning-ir/0.1",
                    "ir_hash": "",
                    "source_cycle_id": source_cycle_id,
                    "mode": "shadow_tune",
                    "module_id": module_id,
                    "node_id": node_id,
                    "assignments": capped,
                    "reason_tags": ["explore_shadow_v1"],
                }
            )
            exp = _lock_experiment_ir(
                {
                    "schema_version": "experiment-ir/0.1",
                    "experiment_hash": "",
                    "source_cycle_id": source_cycle_id,
                    "mode": "shadow_experiment",
                    "tuning_ir": tuning_ir,
                    "notes": {"baseline_signature": dict(baseline)},
                }
            )
            experiments.append(exp)

    decisions = {
        "enable_explore": enable_explore,
        "degraded_mode": degraded,
        "shared_budget": {"max_changes_per_cycle": max_changes, "remaining_after": remaining},
        "exploit_item_count": len(portfolio_items),
        "exploit_assignment_count": sum(_count_assignments(it) for it in portfolio_items),
        "explore_count": len(experiments),
        "explore_assignment_count": sum(_count_assignments((e.get("tuning_ir") or {})) for e in experiments),
    }

    bundle = {
        "schema_version": "tuning-plane-bundle/1.0",
        "bundle_hash": "",
        "source_cycle_id": source_cycle_id,
        "baseline_signature": baseline,
        "policy": dict(policy),
        "portfolio": portfolio_ir,
        "experiments": experiments,
        "decisions": decisions,
        "provenance": {
            "registry_hash": content_hash(registry_snapshot or {}),
            "metrics_hash": content_hash(metrics_snapshot or {}),
            "effects_hash": content_hash(effects_store.to_dict()),
            "children": {
                "portfolio_hash": portfolio_ir.get("portfolio_hash", ""),
                "experiment_hashes": [e.get("experiment_hash", "") for e in experiments],
            },
        },
    }
    bundle["bundle_hash"] = content_hash({**bundle, "bundle_hash": ""})
    return bundle


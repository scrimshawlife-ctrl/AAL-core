from __future__ import annotations

from typing import Any, Dict, List, Tuple

from aal_core.ers.baseline import compute_baseline_signature
from aal_core.ers.drift_sentinel import DriftReport, compute_drift
from aal_core.ers.effects_store import EffectStore
from aal_core.ers.risk_governor import RiskPolicy, clamp_exploit_assignments, clamp_policy
from aal_core.ers.stabilization import StabilizationState
from aal_core.ledger.ledger import EvidenceLedger
from aal_core.runtime.promotion_overlay import PromotionOverlay
from aal_core.runtime.promotion_report import build_promotion_report
from abx_runes.tuning.emit import lock_tuning_ir
from abx_runes.tuning.hashing import content_hash
from abx_runes.tuning.portfolio.optimizer import build_portfolio


def _pick_root_metrics(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(snapshot, dict) or not snapshot:
        return {}
    if isinstance(snapshot.get("__global__"), dict):
        return snapshot.get("__global__") or {}
    # deterministic fallback: first key (sorted)
    k = sorted(snapshot.keys())[0]
    v = snapshot.get(k)
    return v if isinstance(v, dict) else {}


def _lock_bundle(bundle: Dict[str, Any]) -> Dict[str, Any]:
    b = dict(bundle)
    b["bundle_hash"] = ""
    b["bundle_hash"] = content_hash(b, blank_fields=())
    return b


def _module_entries(registry_snapshot: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    if not isinstance(registry_snapshot, dict):
        return []
    out: List[Tuple[str, Dict[str, Any]]] = []
    for mid in sorted(registry_snapshot.keys()):
        v = registry_snapshot.get(mid) or {}
        out.append((str(mid), v if isinstance(v, dict) else {}))
    return out


def build_tuning_plane_bundle(
    *,
    source_cycle_id: str,
    registry_snapshot: Dict[str, Any],
    metrics_snapshot: Dict[str, Any],
    effects_store: EffectStore,
    stabilization_state: StabilizationState,
    policy: Dict[str, Any],
) -> Dict[str, Any]:
    """
    v1.1 tuning-plane router:
    1) compute drift/degraded
    2) clamp effective policy via Risk Governor
    3) if stop condition -> emit deterministic do-nothing bundle
    4) otherwise emit deterministic exploit tuning IRs (+ explore flag only)
    """
    root_metrics = _pick_root_metrics(metrics_snapshot)
    baseline = compute_baseline_signature(root_metrics)

    prev = policy.get("prev_metrics_snapshot") or {}
    prev_root = _pick_root_metrics(prev) if isinstance(prev, dict) else {}

    drift: DriftReport = compute_drift(
        prev_metrics=prev_root,
        now_metrics=root_metrics,
        latency_spike_ratio=float(policy.get("latency_spike_ratio", 1.25)),
        error_spike_ratio=float(policy.get("error_spike_ratio", 1.50)),
        cost_spike_ratio=float(policy.get("cost_spike_ratio", 1.25)),
        throughput_drop_ratio=float(policy.get("throughput_drop_ratio", 0.80)),
        degraded_score_threshold=float(policy.get("degraded_score_threshold", 0.60)),
    )

    rp: RiskPolicy = clamp_policy(
        base_policy=policy,
        drift_score=float(drift.drift_score),
        degraded_mode=bool(drift.degraded_mode) or bool(policy.get("degraded_mode", False)),
    )

    overlay = PromotionOverlay.load(bias_weight=float(policy.get("promotion_bias_weight", 0.15)))

    provenance = {
        "registry_hash": content_hash(registry_snapshot or {}, blank_fields=()),
        "metrics_hash": content_hash(metrics_snapshot or {}, blank_fields=()),
        "effects_hash": content_hash(
            (effects_store.to_dict() if isinstance(effects_store, EffectStore) else {}),
            blank_fields=(),
        ),
    }

    if rp.do_nothing:
        bundle = {
            "schema_version": "tuning-plane-bundle/1.1",
            "bundle_hash": "",
            "source_cycle_id": str(source_cycle_id),
            "baseline_signature": dict(baseline),
            "policy": dict(policy or {}),
            "tuning_irs": [],
            "decisions": {
                "do_nothing": True,
                "reasons": list(rp.reasons),
                "drift": drift.__dict__,
                "risk_policy": rp.__dict__,
            },
            "provenance": provenance,
        }

        # Promotion influence report (shadow-only)
        try:
            report = build_promotion_report(
                module_id=str(bundle.get("module_id", "")),
                baseline_signature=dict(baseline),
                candidates=bundle.get("candidates") or [],
                selected=bundle.get("selected") or [],
                overlay=overlay,
                promotion_bias_weight=float(policy.get("promotion_bias_weight", 0.15)),
            )
            bundle["decisions"]["promotion_report"] = report
            EvidenceLedger().append(
                entry_type="promotion_influence_reported",
                payload=report,
                provenance={"policy_hash": content_hash(policy)},
            )
        except Exception:
            # observability must never fail the run
            pass

        return _lock_bundle(bundle)

    degraded = bool(drift.degraded_mode) or bool(policy.get("degraded_mode", False))
    enable_explore = bool(rp.allow_explore) and (not degraded)

    tuning_irs: List[Dict[str, Any]] = []
    per_module: Dict[str, Any] = {}

    for module_id, entry in _module_entries(registry_snapshot):
        env = (entry or {}).get("tuning_envelope") or {}
        if not isinstance(env, dict):
            env = {}

        # portfolio optimization (deterministic)
        proposed, notes = build_portfolio(
            effects_store=effects_store,
            tuning_envelope=env,
            baseline_signature=baseline,
            metric_name=str(policy.get("optimize_metric_name", "latency_ms_p95")),
            allow_shadow_only=bool(policy.get("allow_shadow_only", False)),
        )

        clamped, clamp_report = clamp_exploit_assignments(
            assignments=proposed, tuning_envelope=env, risk_policy=rp
        )

        # Convert to tuning IR (exploit only; explore is just a flag in v1.1 here)
        ir = {
            "schema_version": "tuning-ir/0.1",
            "ir_hash": "",
            "source_cycle_id": str(source_cycle_id),
            "mode": "applied_tune",
            "module_id": str(env.get("module_id") or module_id),
            "node_id": str(entry.get("node_id") or module_id),
            "assignments": dict(clamped),
            "reason_tags": ["risk_governed_exploit"],
        }
        tuning_irs.append(lock_tuning_ir(ir))

        per_module[str(module_id)] = {
            "proposed_knobs": sorted(list(proposed.keys())),
            "allowed_knobs": list(clamp_report.get("allowed_knobs") or []),
            "rejected": dict(clamp_report.get("rejected") or {}),
            "portfolio_notes": notes,
        }

    bundle = {
        "schema_version": "tuning-plane-bundle/1.1",
        "bundle_hash": "",
        "source_cycle_id": str(source_cycle_id),
        "baseline_signature": dict(baseline),
        "policy": dict(policy or {}),
        "tuning_irs": list(tuning_irs),
        "decisions": {
            "do_nothing": False,
            "enable_explore": bool(enable_explore),
            "degraded_mode": bool(degraded),
            "drift": drift.__dict__,
            "risk_policy": rp.__dict__,
            "modules": per_module,
        },
        "provenance": provenance,
    }

    # Promotion influence report (shadow-only)
    try:
        report = build_promotion_report(
            module_id=str(bundle.get("module_id", "")),
            baseline_signature=dict(baseline),
            candidates=bundle.get("candidates") or [],
            selected=bundle.get("selected") or [],
            overlay=overlay,
            promotion_bias_weight=float(policy.get("promotion_bias_weight", 0.15)),
        )
        bundle["decisions"]["promotion_report"] = report
        EvidenceLedger().append(
            entry_type="promotion_influence_reported",
            payload=report,
            provenance={"policy_hash": content_hash(policy)},
        )
    except Exception:
        # observability must never fail the run
        pass

    return _lock_bundle(bundle)


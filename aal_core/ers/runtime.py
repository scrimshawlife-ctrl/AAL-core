from __future__ import annotations

from typing import Any, Dict, Tuple

from abx_runes.tuning.portfolio.optimizer import build_portfolio

from .baseline import compute_baseline_signature
from .effects_store import EffectStore, record_effect


def ers_cycle_boundary_baseline(metrics_snapshot: Dict[str, Any]) -> Dict[str, str]:
    """
    ERS v0.7: compute the baseline signature at cycle boundary.
    """
    return compute_baseline_signature(metrics_snapshot or {})


def ers_record_effects(
    *,
    effects_store: EffectStore,
    module_id: str,
    knob: str,
    value: Any,
    metrics_snapshot: Dict[str, Any],
    before_metrics: Dict[str, Any],
    after_metrics: Dict[str, Any],
) -> Dict[str, str]:
    """
    ERS v0.7: compute baseline signature and record deltas bucket-locally.

    Returns the baseline signature used for recording.
    """
    baseline = ers_cycle_boundary_baseline(metrics_snapshot)
    record_effect(
        effects_store,
        module_id=module_id,
        knob=knob,
        value=value,
        baseline_signature=baseline,
        before_metrics=before_metrics,
        after_metrics=after_metrics,
    )
    return baseline


def ers_optimize_portfolio(
    *,
    effects_store: EffectStore,
    tuning_envelope: Dict[str, Any],
    metrics_snapshot: Dict[str, Any],
    metric_name: str = "latency_ms_p95",
    allow_shadow_only: bool = False,
    enable_cross_bucket_shadow: bool = True,
    min_similarity: float = 0.75,
    shadow_penalty: float = 0.5,
    z_threshold_shadow: float = 3.0,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    ERS v0.7: compute baseline signature and optimize using bucket-local effects.
    """
    baseline = ers_cycle_boundary_baseline(metrics_snapshot)
    return build_portfolio(
        effects_store=effects_store,
        tuning_envelope=tuning_envelope,
        baseline_signature=baseline,
        metric_name=metric_name,
        allow_shadow_only=allow_shadow_only,
        enable_cross_bucket_shadow=enable_cross_bucket_shadow,
        min_similarity=min_similarity,
        shadow_penalty=shadow_penalty,
        z_threshold_shadow=z_threshold_shadow,
    )


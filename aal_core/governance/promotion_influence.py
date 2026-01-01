from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from aal_core.governance.promotion_policy import PromotionPolicy


@dataclass(frozen=True)
class PromotionInfluenceReport:
    """
    Read-only, shadow-only measurement of promotion effects per cycle.

    Non-Negotiable Constraints:
    - Zero feedback into optimization
    - Deterministic
    - Cheap to compute
    """

    schema_version: str
    candidates_total: int
    promotion_biased: int
    selected_with_promotion: int
    rollback_rate_promoted: float
    rollback_rate_unpromoted: float
    modules_with_promotions: List[str]
    dormant_promotions: int
    promotion_lift: Optional[Dict[str, float]]


def compute_promotion_influence(
    *,
    portfolio: Dict[str, Any],
    notes: Dict[str, Any],
    promotion_policy: PromotionPolicy,
    effects_store,
    baseline_signature: Dict[str, str],
    rollback_ledger: Optional[List[Dict[str, Any]]] = None,
) -> PromotionInfluenceReport:
    """
    Compute promotion influence metrics for a single tuning cycle.

    Args:
        portfolio: Applied knob assignments from optimizer
        notes: Optimizer notes (excluded, shadow_only, etc.)
        promotion_policy: Active promotion policy
        effects_store: Effect stats for lift calculation
        baseline_signature: Current baseline bucket
        rollback_ledger: Recent rollback events (optional)

    Returns:
        Compact influence report (one per cycle)
    """
    module_id = str(notes.get("module_id", ""))
    excluded = dict(notes.get("excluded") or {})
    shadow_only = dict(notes.get("shadow_only") or {})

    # Step 1: Identify promotion-biased candidates
    promotion_items = _load_active_promotions(promotion_policy, module_id, baseline_signature)

    # Build promoted (knob, value) pairs
    promoted_pairs = {(item["knob"], item["value"]) for item in promotion_items}

    # Step 2: Count candidates and selections
    candidates_total = len(portfolio) + len(excluded) + len(shadow_only)

    # Count promotion-biased: knob+value must match a promotion
    promotion_biased = sum(
        1 for k, v in portfolio.items() if (k, v) in promoted_pairs
    ) + sum(
        1 for k, v in shadow_only.items() if (k, v) in promoted_pairs
    )

    selected_with_promotion = sum(1 for k, v in portfolio.items() if (k, v) in promoted_pairs)

    # Step 3: Compute rollback rates (if ledger available)
    rollback_rate_promoted = 0.0
    rollback_rate_unpromoted = 0.0
    if rollback_ledger:
        rollback_rate_promoted, rollback_rate_unpromoted = _compute_rollback_rates(
            rollback_ledger, module_id, promoted_pairs
        )

    # Step 4: Identify modules using promotions
    modules_with_promotions = [module_id] if selected_with_promotion > 0 else []

    # Step 5: Count dormant promotions (loaded but unused)
    dormant_promotions = len(promoted_pairs) - selected_with_promotion

    # Step 6: Compute promotion lift (descriptive, not causal)
    promotion_lift = _compute_promotion_lift(
        portfolio=portfolio,
        promoted_pairs=promoted_pairs,
        effects_store=effects_store,
        module_id=module_id,
        baseline_signature=baseline_signature,
        metric_name=str(notes.get("metric_name", "latency_ms_p95")),
    )

    return PromotionInfluenceReport(
        schema_version="promotion-influence-report/0.1",
        candidates_total=candidates_total,
        promotion_biased=promotion_biased,
        selected_with_promotion=selected_with_promotion,
        rollback_rate_promoted=rollback_rate_promoted,
        rollback_rate_unpromoted=rollback_rate_unpromoted,
        modules_with_promotions=modules_with_promotions,
        dormant_promotions=dormant_promotions,
        promotion_lift=promotion_lift,
    )


def _load_active_promotions(
    policy: PromotionPolicy, module_id: str, baseline_signature: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Filter promotion policy items for current module/baseline."""
    base_key = ",".join(f"{k}={baseline_signature[k]}" for k in sorted(baseline_signature))
    out: List[Dict[str, Any]] = []
    for item in policy.items:
        if str(item.get("module_id")) != module_id:
            continue
        item_base = item.get("baseline_signature") or {}
        item_base_key = ",".join(f"{k}={item_base[k]}" for k in sorted(item_base))
        if item_base_key != base_key:
            continue
        # Skip revoked promotions
        if item.get("revoked_at_idx") is not None:
            continue
        out.append(item)
    return out


def _compute_rollback_rates(
    ledger: List[Dict[str, Any]], module_id: str, promoted_pairs: Set[tuple]
) -> tuple[float, float]:
    """
    Calculate rollback rates for promoted vs unpromoted attempts.

    Returns: (rollback_rate_promoted, rollback_rate_unpromoted)
    """
    promoted_attempts = 0
    promoted_rollbacks = 0
    unpromoted_attempts = 0
    unpromoted_rollbacks = 0

    for entry in ledger:
        payload = entry.get("payload") or {}
        if str(payload.get("module_id")) != module_id:
            continue

        entry_type = str(entry.get("entry_type", ""))
        if entry_type not in ("tuning_attempt", "rollback"):
            continue

        knob = str(payload.get("knob", ""))
        value = payload.get("value")
        is_promoted = (knob, value) in promoted_pairs

        if entry_type == "tuning_attempt":
            if is_promoted:
                promoted_attempts += 1
            else:
                unpromoted_attempts += 1
        elif entry_type == "rollback":
            if is_promoted:
                promoted_rollbacks += 1
            else:
                unpromoted_rollbacks += 1

    # Compute rates
    rate_promoted = float(promoted_rollbacks) / float(promoted_attempts) if promoted_attempts > 0 else 0.0
    rate_unpromoted = (
        float(unpromoted_rollbacks) / float(unpromoted_attempts) if unpromoted_attempts > 0 else 0.0
    )

    return rate_promoted, rate_unpromoted


def _compute_promotion_lift(
    *,
    portfolio: Dict[str, Any],
    promoted_pairs: Set[tuple],
    effects_store,
    module_id: str,
    baseline_signature: Dict[str, str],
    metric_name: str,
) -> Optional[Dict[str, float]]:
    """
    Compare mean effect deltas: promoted selections vs non-promoted selections.

    Descriptive only. No causal claims.
    """
    from aal_core.ers.effects_store import get_effect_stats

    promoted_deltas: List[float] = []
    unpromoted_deltas: List[float] = []

    for knob, value in portfolio.items():
        stats = get_effect_stats(
            effects_store,
            module_id=module_id,
            knob=knob,
            value=value,
            baseline_signature=baseline_signature,
            metric_name=metric_name,
        )
        if stats is None:
            continue
        m = stats.mean()
        if m is None:
            continue

        if (knob, value) in promoted_pairs:
            promoted_deltas.append(float(m))
        else:
            unpromoted_deltas.append(float(m))

    if not promoted_deltas and not unpromoted_deltas:
        return None

    mean_promoted = sum(promoted_deltas) / len(promoted_deltas) if promoted_deltas else 0.0
    mean_unpromoted = sum(unpromoted_deltas) / len(unpromoted_deltas) if unpromoted_deltas else 0.0

    return {
        "mean_promoted": float(mean_promoted),
        "mean_unpromoted": float(mean_unpromoted),
        "delta": float(mean_promoted - mean_unpromoted),
        "n_promoted": len(promoted_deltas),
        "n_unpromoted": len(unpromoted_deltas),
    }

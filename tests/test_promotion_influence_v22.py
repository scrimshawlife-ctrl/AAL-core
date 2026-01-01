"""
Test promotion influence reporting (v2.2).

Constraints:
- Read-only
- Shadow-only
- Zero feedback into optimization
- Deterministic
- Cheap to compute
"""
from __future__ import annotations

from aal_core.ers.effects_store import EffectStore, RunningStats, record_effect
from aal_core.governance.promotion_influence import compute_promotion_influence
from aal_core.governance.promotion_policy import PromotionPolicy


def test_promotion_influence_basic():
    """Test basic promotion influence computation."""
    # Setup: effect store with some data
    effects_store = EffectStore()
    baseline = {"tier": "prod", "region": "us-west"}

    # Record some effects (promoted and unpromoted)
    record_effect(
        effects_store,
        module_id="mod1",
        knob="batch_size",
        value=32,
        baseline_signature=baseline,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 90.0},  # -10ms improvement
    )

    record_effect(
        effects_store,
        module_id="mod1",
        knob="timeout_ms",
        value=5000,
        baseline_signature=baseline,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 105.0},  # +5ms degradation
    )

    # Setup: promotion policy with one promoted value
    promotion_policy = PromotionPolicy(
        items=[
            {
                "module_id": "mod1",
                "knob": "batch_size",
                "value": 32,
                "baseline_signature": baseline,
                "promoted_at_idx": 1,
            }
        ]
    )

    # Portfolio: selected batch_size=32 (promoted), timeout_ms=5000 (not promoted)
    portfolio = {"batch_size": 32, "timeout_ms": 5000}
    notes = {
        "module_id": "mod1",
        "metric_name": "latency_ms_p95",
        "excluded": {},
        "shadow_only": {},
    }

    # Compute influence
    report = compute_promotion_influence(
        portfolio=portfolio,
        notes=notes,
        promotion_policy=promotion_policy,
        effects_store=effects_store,
        baseline_signature=baseline,
        rollback_ledger=None,
    )

    # Assertions
    assert report.schema_version == "promotion-influence-report/0.1"
    assert report.candidates_total == 2
    assert report.promotion_biased == 1
    assert report.selected_with_promotion == 1
    assert report.dormant_promotions == 0

    # Check promotion lift
    assert report.promotion_lift is not None
    assert report.promotion_lift["n_promoted"] == 1
    assert report.promotion_lift["n_unpromoted"] == 1
    assert report.promotion_lift["mean_promoted"] == -10.0  # batch_size improved
    assert report.promotion_lift["mean_unpromoted"] == 5.0  # timeout_ms degraded
    assert report.promotion_lift["delta"] == -15.0  # promoted was 15ms better

    print("✅ test_promotion_influence_basic passed")


def test_promotion_influence_no_promotions():
    """Test influence reporting when no promotions are active."""
    effects_store = EffectStore()
    baseline = {"tier": "staging"}

    promotion_policy = PromotionPolicy(items=[])

    portfolio = {"batch_size": 16}
    notes = {
        "module_id": "mod1",
        "metric_name": "latency_ms_p95",
        "excluded": {},
        "shadow_only": {},
    }

    report = compute_promotion_influence(
        portfolio=portfolio,
        notes=notes,
        promotion_policy=promotion_policy,
        effects_store=effects_store,
        baseline_signature=baseline,
    )

    assert report.candidates_total == 1
    assert report.promotion_biased == 0
    assert report.selected_with_promotion == 0
    assert report.dormant_promotions == 0

    print("✅ test_promotion_influence_no_promotions passed")


def test_promotion_influence_dormant():
    """Test reporting of dormant promotions (loaded but unused)."""
    effects_store = EffectStore()
    baseline = {"tier": "prod"}

    # Promotion exists for batch_size=64, but we selected batch_size=32
    promotion_policy = PromotionPolicy(
        items=[
            {
                "module_id": "mod1",
                "knob": "batch_size",
                "value": 64,
                "baseline_signature": baseline,
                "promoted_at_idx": 1,
            }
        ]
    )

    portfolio = {"batch_size": 32}  # Different value
    notes = {
        "module_id": "mod1",
        "metric_name": "latency_ms_p95",
        "excluded": {},
        "shadow_only": {},
    }

    report = compute_promotion_influence(
        portfolio=portfolio,
        notes=notes,
        promotion_policy=promotion_policy,
        effects_store=effects_store,
        baseline_signature=baseline,
    )

    assert report.candidates_total == 1
    assert report.promotion_biased == 0  # batch_size=64 not a candidate
    assert report.selected_with_promotion == 0
    assert report.dormant_promotions == 1  # promotion exists but unused

    print("✅ test_promotion_influence_dormant passed")


def test_promotion_influence_rollback_rates():
    """Test rollback rate calculation."""
    effects_store = EffectStore()
    baseline = {"tier": "prod"}

    promotion_policy = PromotionPolicy(
        items=[
            {
                "module_id": "mod1",
                "knob": "batch_size",
                "value": 32,
                "baseline_signature": baseline,
                "promoted_at_idx": 1,
            }
        ]
    )

    portfolio = {"batch_size": 32}
    notes = {
        "module_id": "mod1",
        "metric_name": "latency_ms_p95",
        "excluded": {},
        "shadow_only": {},
    }

    # Simulate ledger with rollback events
    rollback_ledger = [
        {
            "entry_type": "tuning_attempt",
            "payload": {"module_id": "mod1", "knob": "batch_size", "value": 32},
        },
        {
            "entry_type": "tuning_attempt",
            "payload": {"module_id": "mod1", "knob": "timeout_ms", "value": 5000},
        },
        {
            "entry_type": "rollback",
            "payload": {"module_id": "mod1", "knob": "batch_size", "value": 32},
        },
    ]

    report = compute_promotion_influence(
        portfolio=portfolio,
        notes=notes,
        promotion_policy=promotion_policy,
        effects_store=effects_store,
        baseline_signature=baseline,
        rollback_ledger=rollback_ledger,
    )

    # 1 promoted attempt, 1 promoted rollback = 100% rollback rate
    # 1 unpromoted attempt, 0 unpromoted rollbacks = 0% rollback rate
    assert report.rollback_rate_promoted == 1.0
    assert report.rollback_rate_unpromoted == 0.0

    print("✅ test_promotion_influence_rollback_rates passed")


def test_promotion_influence_deterministic():
    """Test that influence computation is deterministic."""
    effects_store = EffectStore()
    baseline = {"tier": "prod"}

    promotion_policy = PromotionPolicy(
        items=[
            {
                "module_id": "mod1",
                "knob": "batch_size",
                "value": 32,
                "baseline_signature": baseline,
                "promoted_at_idx": 1,
            }
        ]
    )

    portfolio = {"batch_size": 32}
    notes = {
        "module_id": "mod1",
        "metric_name": "latency_ms_p95",
        "excluded": {},
        "shadow_only": {},
    }

    # Compute twice
    report1 = compute_promotion_influence(
        portfolio=portfolio,
        notes=notes,
        promotion_policy=promotion_policy,
        effects_store=effects_store,
        baseline_signature=baseline,
    )

    report2 = compute_promotion_influence(
        portfolio=portfolio,
        notes=notes,
        promotion_policy=promotion_policy,
        effects_store=effects_store,
        baseline_signature=baseline,
    )

    # Must be identical
    assert report1.candidates_total == report2.candidates_total
    assert report1.promotion_biased == report2.promotion_biased
    assert report1.selected_with_promotion == report2.selected_with_promotion
    assert report1.rollback_rate_promoted == report2.rollback_rate_promoted
    assert report1.rollback_rate_unpromoted == report2.rollback_rate_unpromoted

    print("✅ test_promotion_influence_deterministic passed")


if __name__ == "__main__":
    test_promotion_influence_basic()
    test_promotion_influence_no_promotions()
    test_promotion_influence_dormant()
    test_promotion_influence_rollback_rates()
    test_promotion_influence_deterministic()
    print("\n✅ All promotion influence tests passed")

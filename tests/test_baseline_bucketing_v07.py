from aal_core.ers.baseline import compute_baseline_signature
from aal_core.ers.effects_store import EffectStore, get_effect_stats, record_effect
from abx_runes.tuning.portfolio.optimizer import build_portfolio


def test_baseline_signature_deterministic_and_bucketed():
    m1 = {"queue_depth": 11, "input_size": 500, "mode": "fast", "time_window": "peak"}
    m2 = {"time_window": "peak", "mode": "fast", "input_size": 500, "queue_depth": 11}

    s1 = compute_baseline_signature(m1)
    s2 = compute_baseline_signature(m2)
    assert s1 == s2
    assert s1 == {
        "queue_depth_bucket": "<= 50",
        "input_size_bucket": "<= 1000.0",
        "mode": "fast",
        "time_window": "peak",
    }


def test_effects_are_isolated_per_baseline_bucket():
    store = EffectStore()

    baseline_a = {"queue_depth_bucket": "<= 10", "time_window": "offpeak"}
    baseline_b = {"queue_depth_bucket": "> 50", "time_window": "peak"}

    # Record "good" delta in bucket A
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_a,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 90.0},
    )

    # Record "bad" delta in bucket B
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_b,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 110.0},
    )

    a = get_effect_stats(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_a,
        metric_name="latency_ms_p95",
    )
    b = get_effect_stats(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_b,
        metric_name="latency_ms_p95",
    )
    assert a is not None and b is not None
    assert a.n == 1 and b.n == 1
    assert a.mean == -10.0
    assert b.mean == 10.0


def test_portfolio_uses_only_current_bucket_stats_and_never_cross_contaminates():
    store = EffectStore()
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [
            {
                "name": "mode",
                "kind": "enum",
                "enum_values": ["fast", "safe"],
                "default": "safe",
                "hot_apply": True,
                "stabilization_cycles": 0,
                "capability_required": "tune.mode",
            }
        ],
    }

    baseline_a = {"queue_depth_bucket": "<= 10", "time_window": "offpeak"}
    baseline_b = {"queue_depth_bucket": "> 50", "time_window": "peak"}

    # Only bucket A has stats: "fast" improves latency, "safe" is neutral.
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_a,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 90.0},
    )
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="safe",
        baseline_signature=baseline_a,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 100.0},
    )

    applied_a, notes_a = build_portfolio(
        effects_store=store,
        tuning_envelope=env,
        baseline_signature=baseline_a,
        metric_name="latency_ms_p95",
        allow_shadow_only=False,
    )
    assert applied_a["mode"] == "fast"
    assert notes_a["baseline_signature"] == baseline_a

    applied_b, notes_b = build_portfolio(
        effects_store=store,
        tuning_envelope=env,
        baseline_signature=baseline_b,
        metric_name="latency_ms_p95",
        allow_shadow_only=False,
    )
    assert applied_b == {}
    assert notes_b["excluded"]["mode"] == "no_bucket_stats"

    applied_b2, notes_b2 = build_portfolio(
        effects_store=store,
        tuning_envelope=env,
        baseline_signature=baseline_b,
        metric_name="latency_ms_p95",
        allow_shadow_only=True,
    )
    assert applied_b2 == {}
    assert notes_b2["excluded"]["mode"] == "shadow_only_no_bucket_stats"
    assert notes_b2["shadow_only"]["mode"] == "safe"


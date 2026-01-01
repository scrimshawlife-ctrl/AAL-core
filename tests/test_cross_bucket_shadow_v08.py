from aal_core.ers.baseline_similarity import similarity
from aal_core.ers.effects_store import EffectStore, record_effect
from abx_runes.tuning.portfolio.optimizer import build_portfolio


def test_baseline_similarity_exact_and_adjacent_scoring():
    a = {"queue_depth_bucket": "<= 10", "time_window": "peak"}
    b = {"queue_depth_bucket": "<= 50", "time_window": "peak"}
    c = {"queue_depth_bucket": "> 50", "time_window": "offpeak"}

    assert similarity(a, a) == 1.0
    assert similarity(a, b) == 0.75  # (adjacent 0.5 + exact 1.0) / 2
    assert similarity(a, c) == 0.0


def test_cross_bucket_shadow_suggests_but_never_applies():
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

    # Current bucket has no stats; donor bucket is similar enough (0.75).
    baseline_current = {"queue_depth_bucket": "<= 10", "time_window": "peak"}
    baseline_donor = {"queue_depth_bucket": "<= 50", "time_window": "peak"}

    # Record two non-identical deltas so variance > 0 and z is computable/high.
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_donor,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 90.0},
    )
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_donor,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 88.0},
    )

    applied, notes = build_portfolio(
        effects_store=store,
        tuning_envelope=env,
        baseline_signature=baseline_current,
        metric_name="latency_ms_p95",
        allow_shadow_only=True,
        enable_cross_bucket_shadow=True,
        min_similarity=0.75,
        shadow_penalty=0.5,
        z_threshold_shadow=3.0,
    )

    # Never applied cross-bucket.
    assert applied == {}

    # But we surface a shadow-only suggestion plus explainability.
    assert notes["excluded"]["mode"] == "cross_bucket_shadow"
    assert notes["shadow_only"]["mode"] == "fast"
    assert notes["shadow_cross_bucket"]["mode"]["suggested_value"] == "fast"
    assert notes["shadow_cross_bucket"]["mode"]["penalty_applied"] == 0.5
    assert notes["shadow_cross_bucket"]["mode"]["donors"]


def test_cross_bucket_shadow_can_populate_notes_even_if_shadow_only_disabled():
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

    baseline_current = {"queue_depth_bucket": "<= 10", "time_window": "peak"}
    baseline_donor = {"queue_depth_bucket": "<= 50", "time_window": "peak"}

    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_donor,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 90.0},
    )
    record_effect(
        store,
        module_id="mod.alpha",
        knob="mode",
        value="fast",
        baseline_signature=baseline_donor,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 88.0},
    )

    applied, notes = build_portfolio(
        effects_store=store,
        tuning_envelope=env,
        baseline_signature=baseline_current,
        metric_name="latency_ms_p95",
        allow_shadow_only=False,
        enable_cross_bucket_shadow=True,
        min_similarity=0.75,
        shadow_penalty=0.5,
        z_threshold_shadow=3.0,
    )

    assert applied == {}
    assert notes["shadow_only"] == {}
    assert notes["excluded"]["mode"] in ("no_bucket_stats", "no_usable_bucket_stats")
    assert notes["shadow_cross_bucket"]["mode"]["suggested_value"] == "fast"


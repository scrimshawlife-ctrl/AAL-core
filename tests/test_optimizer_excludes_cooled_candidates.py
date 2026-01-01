from aal_core.ers.cooldown import CooldownEntry, CooldownStore, cooldown_key
from aal_core.ers.effects_store import EffectStore, record_effect
from abx_runes.tuning.portfolio.optimizer import build_portfolio


def test_optimizer_excludes_cooled_candidates() -> None:
    baseline_signature = {"bucket": "A"}
    module_id = "m"

    # Create bucketed effect stats:
    # - value=1 has better (lower) mean delta but is cooled down
    # - value=0 is worse but should be selected due to cooldown exclusion
    store = EffectStore()
    record_effect(
        store,
        module_id=module_id,
        knob="k",
        value=0,
        baseline_signature=baseline_signature,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 100.0},
    )
    record_effect(
        store,
        module_id=module_id,
        knob="k",
        value=1,
        baseline_signature=baseline_signature,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 99.0},
    )

    cstore = CooldownStore(entries={})
    ck = cooldown_key(module_id=module_id, knob="k", value=1, baseline_signature=baseline_signature)
    cstore.set(
        ck,
        CooldownEntry(set_idx=10, until_idx=999999, reason="test", stats_snapshot={"x": 1}),
    )

    tuning_envelope = {
        "module_id": module_id,
        "knobs": [{"name": "k", "kind": "int", "min_value": 0, "max_value": 1, "default": 0}],
    }

    applied, notes = build_portfolio(
        effects_store=store,
        tuning_envelope=tuning_envelope,
        baseline_signature=baseline_signature,
        cooldown_store=cstore,
        metric_name="latency_ms_p95",
    )

    assert applied["k"] == 0
    assert notes["excluded"] == {}


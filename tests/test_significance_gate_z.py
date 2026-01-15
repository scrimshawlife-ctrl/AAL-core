from abx_runes.tuning.portfolio.types import PortfolioPolicy
from abx_runes.tuning.portfolio.optimizer import build_portfolio
from aal_core.ers.effects_store import EffectStore, record_effect


def test_z_gate_blocks_noisy_small_effect():
    reg = {
        "m": {
            "tuning_envelope": {
                "schema_version": "tuning-envelope/0.1",
                "module_id": "m",
                "knobs": [
                    {
                        "name": "cache_enabled",
                        "kind": "bool",
                        "hot_apply": True,
                        "stabilization_cycles": 0,
                        "capability_required": "tune.cache",
                    },
                ],
            },
            "capability": {"module_id": "m", "allowed": ["tune.cache"]},
        }
    }
    met = {"m": {"latency_ms_p95": 100.0}}
    policy = PortfolioPolicy(schema_version="portfolio-policy/0.1", source_cycle_id="c", max_changes_per_cycle=1)

    class _Dummy:
        cycles_since_change = {}

    stab = _Dummy()
    effects = EffectStore(stats={})

    # Noisy deltas around -1ms and +1ms => mean ~(-0.33ms), variance nonzero => z small
    record_effect(
        effects,
        module_id="m",
        knob="cache_enabled",
        value=True,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 99.0},
    )
    record_effect(
        effects,
        module_id="m",
        knob="cache_enabled",
        value=True,
        before_metrics={"latency_ms_p95": 99.0},
        after_metrics={"latency_ms_p95": 100.0},
    )
    record_effect(
        effects,
        module_id="m",
        knob="cache_enabled",
        value=True,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 99.0},
    )

    items, notes = build_portfolio(
        policy=policy,
        registry_snapshot=reg,
        metrics_snapshot=met,
        stabilization_state=stab,
        effects_store=effects,
        min_samples=3,
        min_abs_latency_ms_p95=0.5,
        z_threshold=2.0,
    )
    assert items == []
    assert notes["optimizer_version"] == "v0.6"


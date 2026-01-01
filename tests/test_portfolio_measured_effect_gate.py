from abx_runes.tuning.portfolio.types import PortfolioPolicy
from abx_runes.tuning.portfolio.optimizer import build_portfolio
from aal_core.ers.effects_store import EffectStore, record_effect


def test_portfolio_excludes_unknown_effects_by_default():
    reg = {
        "m": {
            "tuning_envelope": {
                "schema_version": "tuning-envelope/0.1",
                "module_id": "m",
                "knobs": [
                    {
                        "name": "batch_size",
                        "kind": "int",
                        "min_value": 1,
                        "max_value": 128,
                        "hot_apply": True,
                        "stabilization_cycles": 0,
                        "capability_required": "tune.batch",
                    },
                ],
            },
            "capability": {"module_id": "m", "allowed": ["tune.batch"]},
        }
    }
    met = {"m": {"latency_ms_p95": 100.0}}
    policy = PortfolioPolicy(schema_version="portfolio-policy/0.1", source_cycle_id="c", max_changes_per_cycle=2)

    class _Dummy:
        cycles_since_change = {}

    stab = _Dummy()
    effects = EffectStore(stats={})

    items, notes = build_portfolio(
        policy=policy,
        registry_snapshot=reg,
        metrics_snapshot=met,
        stabilization_state=stab,
        effects_store=effects,
    )
    assert items == []


def test_portfolio_selects_when_effect_is_measured_and_significant():
    reg = {
        "m": {
            "tuning_envelope": {
                "schema_version": "tuning-envelope/0.1",
                "module_id": "m",
                "knobs": [
                    {
                        "name": "batch_size",
                        "kind": "int",
                        "min_value": 1,
                        "max_value": 128,
                        "hot_apply": True,
                        "stabilization_cycles": 0,
                        "capability_required": "tune.batch",
                    },
                ],
            },
            "capability": {"module_id": "m", "allowed": ["tune.batch"]},
        }
    }
    met = {"m": {"latency_ms_p95": 100.0}}
    policy = PortfolioPolicy(schema_version="portfolio-policy/0.1", source_cycle_id="c", max_changes_per_cycle=2)

    class _Dummy:
        cycles_since_change = {}

    stab = _Dummy()
    effects = EffectStore(stats={})
    # record two samples for value=128: latency improves by -5 each time
    record_effect(
        effects,
        module_id="m",
        knob="batch_size",
        value=128,
        before_metrics={"latency_ms_p95": 100.0},
        after_metrics={"latency_ms_p95": 95.0},
    )
    record_effect(
        effects,
        module_id="m",
        knob="batch_size",
        value=128,
        before_metrics={"latency_ms_p95": 95.0},
        after_metrics={"latency_ms_p95": 90.0},
    )

    items, notes = build_portfolio(
        policy=policy,
        registry_snapshot=reg,
        metrics_snapshot=met,
        stabilization_state=stab,
        effects_store=effects,
        min_samples=2,
        min_abs_latency_ms_p95=1.0,
    )
    assert len(items) == 1
    assert items[0]["module_id"] == "m"


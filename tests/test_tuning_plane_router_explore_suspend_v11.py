from aal_core.ers.effects_store import EffectStore
from aal_core.ers.stabilization import new_state
from abx_runes.tuning.plane.router import build_tuning_plane_bundle


def test_explore_suspended_when_drift_high():
    reg = {
        "m": {
            "tuning_envelope": {"schema_version": "tuning-envelope/0.1", "module_id": "m", "knobs": []},
            "node_id": "n",
        }
    }
    prev = {"__global__": {"latency_ms_p95": 100.0, "error_rate": 0.01, "cost_units": 10.0, "throughput_per_s": 100.0}}
    now = {"__global__": {"latency_ms_p95": 140.0, "error_rate": 0.02, "cost_units": 11.0, "throughput_per_s": 95.0}}

    effects = EffectStore()
    stab = new_state()

    policy = {
        "prev_metrics_snapshot": prev,
        "enable_explore": True,
        "drift_high_threshold": 0.01,  # force "high"
        "drift_extreme_threshold": 0.99,  # avoid do-nothing
    }

    b = build_tuning_plane_bundle(
        source_cycle_id="c",
        registry_snapshot=reg,
        metrics_snapshot=now,
        effects_store=effects,
        stabilization_state=stab,
        policy=policy,
    )

    assert b["decisions"]["do_nothing"] is False
    assert b["decisions"]["enable_explore"] is False
    assert b["decisions"]["risk_policy"]["allow_explore"] is False


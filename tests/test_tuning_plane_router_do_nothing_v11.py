from aal_core.ers.effects_store import EffectStore
from aal_core.ers.stabilization import new_state
from abx_runes.tuning.plane.router import build_tuning_plane_bundle


def test_do_nothing_bundle_when_drift_extreme():
    reg = {
        "m": {
            "tuning_envelope": {"schema_version": "tuning-envelope/0.1", "module_id": "m", "knobs": []},
            "node_id": "n",
        }
    }
    now = {"__global__": {"latency_ms_p95": 200.0, "error_rate": 0.05, "cost_units": 10.0, "throughput_per_s": 5.0}}
    prev = {"__global__": {"latency_ms_p95": 50.0, "error_rate": 0.01, "cost_units": 5.0, "throughput_per_s": 10.0}}

    effects = EffectStore()
    stab = new_state()

    policy = {"prev_metrics_snapshot": prev, "drift_extreme_threshold": 0.10}  # force extreme quickly

    b1 = build_tuning_plane_bundle(
        source_cycle_id="c",
        registry_snapshot=reg,
        metrics_snapshot=now,
        effects_store=effects,
        stabilization_state=stab,
        policy=policy,
    )
    b2 = build_tuning_plane_bundle(
        source_cycle_id="c",
        registry_snapshot=reg,
        metrics_snapshot=now,
        effects_store=effects,
        stabilization_state=stab,
        policy=policy,
    )

    assert b1["schema_version"] == "tuning-plane-bundle/1.1"
    assert b1["decisions"]["do_nothing"] is True
    assert b1["tuning_irs"] == []
    assert isinstance(b1["bundle_hash"], str) and len(b1["bundle_hash"]) > 0
    assert b1["bundle_hash"] == b2["bundle_hash"]
    assert set(b1["provenance"].keys()) == {"registry_hash", "metrics_hash", "effects_hash"}


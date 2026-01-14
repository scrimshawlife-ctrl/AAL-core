from aal_core.ers.canary_apply import canary_apply_tuning_ir
from aal_core.ers.effects_store import EffectStore, get_effect_stats
from aal_core.ers.stabilization import new_state
from aal_core.ers.capabilities import CapabilityToken


def test_canary_rolls_back_on_drift_and_records_negative_evidence():
    effects = EffectStore()
    stab = new_state()
    cap = CapabilityToken(module_id="m", allowed=set([""]))

    tuning_ir = {
        "schema_version": "tuning-ir/0.1",
        "module_id": "m",
        "node_id": "n",
        "assignments": {"k": 1},
        "source_cycle_id": "c",
        "ir_hash": "h",
        "mode": "applied_tune",
        "reason_tags": [],
    }
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "m",
        "knobs": [
            {
                "name": "k",
                "kind": "int",
                "min_value": 0,
                "max_value": 2,
                "hot_apply": True,
                "stabilization_cycles": 0,
                "capability_required": "",
            }
        ],
    }

    snaps = [
        {"m": {"latency_ms_p95": 100.0, "error_rate": 0.01, "cost_units": 1.0, "throughput_per_s": 10.0}},
        {"m": {"latency_ms_p95": 140.0, "error_rate": 0.03, "cost_units": 1.2, "throughput_per_s": 9.0}},
    ]
    i = {"idx": 0}

    def get_metrics():
        j = snaps[min(i["idx"], len(snaps) - 1)]
        i["idx"] += 1
        return j

    def get_assignments(_mid):
        # previous assignments so rollback has something to revert to
        return {"k": 0}

    res = canary_apply_tuning_ir(
        tuning_ir=tuning_ir,
        tuning_envelope=env,
        capability=cap,
        stabilization_state=stab,
        effects_store=effects,
        get_metrics_snapshot=get_metrics,
        get_current_assignments=get_assignments,
        cycle_boundary=True,
        # Make rollback easy to trigger deterministically.
        policy={"canary_cycles": 1, "rollback_degraded_score_threshold": 0.01},
    )
    assert res.rolled_back is True
    assert res.rollback_ir is not None
    assert res.rollback_ir["schema_version"] == "rollback-ir/0.1"
    assert res.rollback_ir["reverted_assignments"] == {"k": 0}

    # Negative evidence is stored as observed deltas for the attempted value.
    st = get_effect_stats(
        effects,
        module_id="m",
        knob="k",
        value=1,
        baseline_signature={},  # baseline signature is empty for these metrics
        metric_name="latency_ms_p95",
    )
    assert st is not None
    assert st.n == 1
    assert st.mean == 40.0


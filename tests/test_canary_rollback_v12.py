from __future__ import annotations

from aal_core.ers.canary_apply import canary_apply_tuning_ir
from aal_core.ers.effects_store import EffectStore, get_effect_stats
from aal_core.ers.stabilization import new_state


def test_canary_rolls_back_on_drift_and_records_artifact_and_penalty():
    effects = EffectStore()

    tuning_ir = {
        "schema_version": "tuning-ir/0.1",
        "module_id": "m",
        "node_id": "n",
        "assignments": {"k": 1},
        "source_cycle_id": "c",
        "ir_hash": "h",
        "mode": "applied_tune",
        "reason_tags": ["test"],
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
    cap = type("Cap", (), {"allowed": set([""]), "module_id": "m"})()  # minimal stand-in; req cap is blank

    snaps = [
        {"m": {"latency_ms_p95": 100.0, "error_rate": 0.01, "cost_units": 1.0, "throughput_per_s": 10.0}},
        {"m": {"latency_ms_p95": 140.0, "error_rate": 0.03, "cost_units": 1.2, "throughput_per_s": 9.0}},
    ]
    idx = {"i": 0}

    def get_metrics():
        j = snaps[min(idx["i"], len(snaps) - 1)]
        idx["i"] += 1
        return j

    def get_assignments(_mid: str):
        return {"k": 0}

    applied_calls = []

    def apply_fn(*, tuning_ir, tuning_envelope, capability, stab, cycle_boundary=True):
        applied_calls.append(dict(tuning_ir.get("assignments") or {}))
        # emulate hot_apply result shape
        return type("R", (), {"applied": dict(tuning_ir.get("assignments") or {}), "rejected": {}})()

    res = canary_apply_tuning_ir(
        tuning_ir=tuning_ir,
        tuning_envelope=env,
        capability=cap,
        stabilization_state=new_state(),
        effects_store=effects,
        get_metrics_snapshot=get_metrics,
        get_current_assignments=get_assignments,
        cycle_boundary=True,
        policy={"canary_cycles": 1, "rollback_degraded_score_threshold": 0.01},
        apply_fn=apply_fn,
    )

    assert res.rolled_back is True
    assert res.rollback_ir is not None
    assert res.rollback_ir["schema_version"] == "rollback-ir/0.1"
    assert res.rollback_ir["reverted_assignments"] == {"k": 0}
    assert effects.artifacts and effects.artifacts[-1]["rollback_hash"] == res.rollback_ir["rollback_hash"]

    # rollback is a first-class action: canary apply then rollback apply
    assert applied_calls == [{"k": 1}, {"k": 0}]

    # Negative evidence: penalty metric is recorded for the attempted value.
    st = get_effect_stats(
        effects,
        module_id="m",
        knob="k",
        value=1,
        baseline_signature={},  # baseline is empty because our metrics don't include baseline bucketing fields
        metric_name="rollback_penalty",
    )
    assert st is not None
    assert st.n == 1
    assert st.mean() == 1.0


def test_canary_deterministic_rollback_hash():
    effects1 = EffectStore()
    effects2 = EffectStore()

    tuning_ir = {
        "schema_version": "tuning-ir/0.1",
        "module_id": "m",
        "node_id": "n",
        "assignments": {"k": 1},
        "source_cycle_id": "c",
        "ir_hash": "h",
        "mode": "applied_tune",
        "reason_tags": ["test"],
    }
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "m",
        "knobs": [{"name": "k", "kind": "int", "min_value": 0, "max_value": 2, "hot_apply": True, "stabilization_cycles": 0, "capability_required": ""}],
    }
    cap = type("Cap", (), {"allowed": set([""]), "module_id": "m"})()

    snaps = [
        {"m": {"latency_ms_p95": 100.0}},
        {"m": {"latency_ms_p95": 200.0}},
    ]

    def mk_get_metrics():
        idx = {"i": 0}

        def _g():
            j = snaps[min(idx["i"], len(snaps) - 1)]
            idx["i"] += 1
            return j

        return _g

    def get_assignments(_mid: str):
        return {"k": 0}

    def apply_fn(*, tuning_ir, tuning_envelope, capability, stab, cycle_boundary=True):
        return type("R", (), {"applied": dict(tuning_ir.get("assignments") or {}), "rejected": {}})()

    r1 = canary_apply_tuning_ir(
        tuning_ir=tuning_ir,
        tuning_envelope=env,
        capability=cap,
        stabilization_state=new_state(),
        effects_store=effects1,
        get_metrics_snapshot=mk_get_metrics(),
        get_current_assignments=get_assignments,
        cycle_boundary=True,
        policy={"canary_cycles": 1, "rollback_degraded_score_threshold": 0.01},
        apply_fn=apply_fn,
    )
    r2 = canary_apply_tuning_ir(
        tuning_ir=tuning_ir,
        tuning_envelope=env,
        capability=cap,
        stabilization_state=new_state(),
        effects_store=effects2,
        get_metrics_snapshot=mk_get_metrics(),
        get_current_assignments=get_assignments,
        cycle_boundary=True,
        policy={"canary_cycles": 1, "rollback_degraded_score_threshold": 0.01},
        apply_fn=apply_fn,
    )

    assert r1.rollback_ir is not None and r2.rollback_ir is not None
    assert r1.rollback_ir["rollback_hash"] == r2.rollback_ir["rollback_hash"]


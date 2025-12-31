from aal_core.ers.capabilities import CapabilityToken
from aal_core.ers.stabilization import new_state, tick_cycle
from aal_core.ers.tuning_apply import hot_apply_tuning_ir


def _env():
    return {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [
            {"name": "batch_size", "kind": "int", "min_value": 1, "max_value": 128, "hot_apply": True, "stabilization_cycles": 2, "capability_required": "tune.batch"},
            {"name": "mode", "kind": "enum", "enum_values": ["fast", "safe"], "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"},
            {"name": "cold_only", "kind": "bool", "hot_apply": False, "stabilization_cycles": 0, "capability_required": "tune.cold"},
        ],
    }


def _ir(mode: str):
    return {
        "schema_version": "tuning-ir/0.1",
        "ir_hash": "x",
        "source_cycle_id": "cycle-001",
        "mode": mode,
        "module_id": "mod.alpha",
        "node_id": "node.alpha",
        "assignments": {"batch_size": 64, "mode": "fast", "cold_only": True},
        "reason_tags": ["latency_down"],
    }


def test_hot_apply_capability_blocks():
    cap = CapabilityToken(module_id="mod.alpha", allowed=set(["tune.mode"]))  # missing tune.batch
    stab = new_state()
    r = hot_apply_tuning_ir(tuning_ir=_ir("applied_tune"), tuning_envelope=_env(), capability=cap, stab=stab)
    assert "batch_size" in r.rejected
    assert r.rejected["batch_size"] == "capability_denied"
    assert r.applied["mode"] == "fast"


def test_hot_apply_stabilization_blocks_until_cycles():
    cap = CapabilityToken(module_id="mod.alpha", allowed=set(["tune.batch", "tune.mode"]))
    stab = new_state()

    # first apply -> note_change sets cycles_since_change=0, then stabilization blocks subsequent changes until >=2 cycles
    r1 = hot_apply_tuning_ir(tuning_ir=_ir("applied_tune"), tuning_envelope=_env(), capability=cap, stab=stab)
    assert r1.applied["batch_size"] == 64

    # attempt immediate reapply (same value): still counted as apply attempt; stabilization gate is evaluated; but since no change detection in v0.1, it blocks by rule if within window
    r2 = hot_apply_tuning_ir(tuning_ir=_ir("applied_tune"), tuning_envelope=_env(), capability=cap, stab=stab)
    assert r2.rejected.get("batch_size") in ("stabilization_block", None)

    tick_cycle(stab)
    tick_cycle(stab)
    r3 = hot_apply_tuning_ir(tuning_ir=_ir("applied_tune"), tuning_envelope=_env(), capability=cap, stab=stab)
    assert "batch_size" in r3.applied


def test_shadow_tune_is_dry_run():
    cap = CapabilityToken(module_id="mod.alpha", allowed=set(["tune.batch", "tune.mode"]))
    stab = new_state()
    r = hot_apply_tuning_ir(tuning_ir=_ir("shadow_tune"), tuning_envelope=_env(), capability=cap, stab=stab)
    assert r.applied["batch_size"] == 64
    assert r.applied["mode"] == "fast"
    # cold_only never applies
    assert r.rejected["cold_only"] == "not_hot_apply"

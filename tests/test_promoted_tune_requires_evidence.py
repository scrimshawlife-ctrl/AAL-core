from aal_core.ers.capabilities import CapabilityToken
from aal_core.ers.stabilization import new_state
from aal_core.ers.tuning_apply import hot_apply_tuning_ir


def test_promoted_tune_requires_evidence_bundle_hash():
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [
            {"name": "mode", "kind": "enum", "enum_values": ["fast", "safe"], "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"},
        ],
    }
    ir = {
        "schema_version": "tuning-ir/0.1",
        "ir_hash": "x",
        "source_cycle_id": "cycle-001",
        "mode": "promoted_tune",
        "module_id": "mod.alpha",
        "node_id": "node.alpha",
        "assignments": {"mode": "safe"},
        "reason_tags": ["rent_paid"],
        "evidence_bundle_hash": "",
    }
    cap = CapabilityToken(module_id="mod.alpha", allowed=set(["tune.mode"]))
    stab = new_state()
    r = hot_apply_tuning_ir(tuning_ir=ir, tuning_envelope=env, capability=cap, stab=stab)
    assert r.rejected["__all__"] == "missing_promotion_evidence"

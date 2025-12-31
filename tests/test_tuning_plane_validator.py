from abx_runes.tuning.validator import validate_tuning_ir_against_envelope


def test_validate_tuning_ir_against_envelope_ok():
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "mod.alpha",
        "knobs": [
            {"name": "batch_size", "kind": "int", "min_value": 1, "max_value": 128, "hot_apply": True, "stabilization_cycles": 2, "capability_required": "tune.batch"},
            {"name": "mode", "kind": "enum", "enum_values": ["fast", "safe"], "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"},
            {"name": "dropout", "kind": "float", "min_value": 0.0, "max_value": 1.0, "hot_apply": False, "stabilization_cycles": 0, "capability_required": "tune.dropout"},
        ],
    }
    ir = {
        "schema_version": "tuning-ir/0.1",
        "ir_hash": "x",
        "source_cycle_id": "cycle-001",
        "mode": "shadow_tune",
        "module_id": "mod.alpha",
        "node_id": "node.alpha",
        "assignments": {"batch_size": 64, "mode": "fast"},
        "reason_tags": ["latency_down"],
    }
    ok, reason = validate_tuning_ir_against_envelope(ir, env)
    assert ok is True, reason


def test_validate_rejects_unknown_knob():
    env = {"schema_version": "tuning-envelope/0.1", "module_id": "m", "knobs": []}
    ir = {"schema_version": "tuning-ir/0.1", "module_id": "m", "node_id": "n", "mode": "shadow_tune", "ir_hash": "", "source_cycle_id": "c", "assignments": {"nope": 1}}
    ok, reason = validate_tuning_ir_against_envelope(ir, env)
    assert ok is False
    assert "unknown_knob" in reason


def test_validate_rejects_out_of_bounds():
    env = {
        "schema_version": "tuning-envelope/0.1",
        "module_id": "m",
        "knobs": [{"name": "k", "kind": "int", "min_value": 1, "max_value": 2, "hot_apply": True, "stabilization_cycles": 0, "capability_required": "cap"}],
    }
    ir = {"schema_version": "tuning-ir/0.1", "module_id": "m", "node_id": "n", "mode": "shadow_tune", "ir_hash": "", "source_cycle_id": "c", "assignments": {"k": 3}}
    ok, reason = validate_tuning_ir_against_envelope(ir, env)
    assert ok is False
    assert "above_max" in reason

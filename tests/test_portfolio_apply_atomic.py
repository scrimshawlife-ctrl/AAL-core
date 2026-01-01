from aal_core.ers.capabilities import CapabilityToken
from aal_core.ers.portfolio_apply import hot_apply_portfolio_tuning_ir
from aal_core.ers.stabilization import new_state, note_change


def _env(module_id: str, cap: str):
    return {
        "schema_version": "tuning-envelope/0.1",
        "module_id": module_id,
        "knobs": [
            {"name": "k", "kind": "int", "min_value": 1, "max_value": 10, "hot_apply": True, "stabilization_cycles": 2, "capability_required": cap},
        ],
    }


def test_portfolio_apply_is_two_phase_and_applies_only_eligible_subset():
    envs = {"m1": _env("m1", "cap.k"), "m2": _env("m2", "cap.k")}
    caps = {
        "m1": CapabilityToken(module_id="m1", allowed=set(["cap.k"])),
        "m2": CapabilityToken(module_id="m2", allowed=set([])),  # denied
    }
    stab = new_state()

    # Put m1:k into stabilization window (cycles_since_change=0), so it is ineligible this cycle.
    note_change(stab, "m1", "k")

    portfolio = {
        "schema_version": "portfolio-tuning-ir/0.4",
        "portfolio_hash": "x",
        "source_cycle_id": "c1",
        "mode": "applied_tune",
        "objective_weights": {"w_latency": -1.0, "w_cost": -1.0, "w_error": -1.0, "w_throughput": 1.0},
        "budgets": {"max_total_cost_units": None, "max_total_latency_ms_p95": None, "max_changes_per_cycle": 10},
        "modules": [
            {
                "module_id": "m1",
                "node_id": "n1",
                "tuning_ir": {
                    "schema_version": "tuning-ir/0.1",
                    "ir_hash": "x",
                    "source_cycle_id": "c1",
                    "mode": "applied_tune",
                    "module_id": "m1",
                    "node_id": "n1",
                    "assignments": {"k": 2},
                    "reason_tags": [],
                },
                "selected_knobs": ["k"],
                "estimated_impact": {"delta_latency_ms_p95": 0.0, "delta_cost_units": 0.0, "delta_error_rate": 0.0, "delta_throughput_per_s": 0.0},
                "total_score": 0.0,
                "promotion_candidates": [],
            },
            {
                "module_id": "m2",
                "node_id": "n2",
                "tuning_ir": {
                    "schema_version": "tuning-ir/0.1",
                    "ir_hash": "x",
                    "source_cycle_id": "c1",
                    "mode": "applied_tune",
                    "module_id": "m2",
                    "node_id": "n2",
                    "assignments": {"k": 2},
                    "reason_tags": [],
                },
                "selected_knobs": ["k"],
                "estimated_impact": {"delta_latency_ms_p95": 0.0, "delta_cost_units": 0.0, "delta_error_rate": 0.0, "delta_throughput_per_s": 0.0},
                "total_score": 0.0,
                "promotion_candidates": [],
            },
        ],
        "reason_tags": [],
    }

    r = hot_apply_portfolio_tuning_ir(
        portfolio_tuning_ir=portfolio,
        tuning_envelopes=envs,
        capabilities=caps,
        stab=stab,
    )
    assert r.rejected == {}
    assert "m1" in r.per_module
    assert "m2" in r.per_module
    # m1 blocked by stabilization
    assert r.per_module["m1"].rejected.get("k") in ("stabilization_block", None)
    # m2 blocked by capability
    assert r.per_module["m2"].rejected.get("k") == "capability_denied"
    assert r.per_module["m2"].applied == {}


def test_portfolio_apply_rejects_structural_errors_and_applies_nothing():
    envs = {"m1": _env("m1", "cap.k")}
    caps = {"m1": CapabilityToken(module_id="m1", allowed=set(["cap.k"]))}
    stab = new_state()

    # duplicate module id -> portfolio-level rejection
    portfolio = {
        "schema_version": "portfolio-tuning-ir/0.4",
        "portfolio_hash": "x",
        "source_cycle_id": "c1",
        "mode": "applied_tune",
        "objective_weights": {"w_latency": -1.0, "w_cost": -1.0, "w_error": -1.0, "w_throughput": 1.0},
        "budgets": {"max_total_cost_units": None, "max_total_latency_ms_p95": None, "max_changes_per_cycle": 10},
        "modules": [
            {"module_id": "m1", "node_id": "n1", "tuning_ir": {}, "selected_knobs": [], "estimated_impact": {"delta_latency_ms_p95": 0, "delta_cost_units": 0, "delta_error_rate": 0, "delta_throughput_per_s": 0}, "total_score": 0, "promotion_candidates": []},
            {"module_id": "m1", "node_id": "n1", "tuning_ir": {}, "selected_knobs": [], "estimated_impact": {"delta_latency_ms_p95": 0, "delta_cost_units": 0, "delta_error_rate": 0, "delta_throughput_per_s": 0}, "total_score": 0, "promotion_candidates": []},
        ],
        "reason_tags": [],
    }

    r = hot_apply_portfolio_tuning_ir(
        portfolio_tuning_ir=portfolio,
        tuning_envelopes=envs,
        capabilities=caps,
        stab=stab,
    )
    assert r.rejected.get("__all__", "").startswith("duplicate_module")
    assert r.per_module == {}


from aal_core.ers.capabilities import CapabilityToken
from aal_core.ers.stabilization import new_state

from abx_runes.tuning.portfolio.emit import lock_portfolio_tuning_ir
from abx_runes.tuning.portfolio.optimizer import select_portfolio
from abx_runes.tuning.portfolio.types import (
    ImpactVector,
    PortfolioBudgets,
    PortfolioCandidate,
    PortfolioObjectiveWeights,
)


def _env(module_id: str):
    return {
        "schema_version": "tuning-envelope/0.1",
        "module_id": module_id,
        "knobs": [
            {"name": "batch_size", "kind": "int", "min_value": 1, "max_value": 128, "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.batch"},
            {"name": "mode", "kind": "enum", "enum_values": ["fast", "safe"], "hot_apply": True, "stabilization_cycles": 0, "capability_required": "tune.mode"},
        ],
    }


def test_portfolio_optimizer_is_deterministic_and_hash_stable():
    envs = {"mod.a": _env("mod.a"), "mod.b": _env("mod.b")}
    caps = {
        "mod.a": CapabilityToken(module_id="mod.a", allowed=set(["tune.batch", "tune.mode"])),
        "mod.b": CapabilityToken(module_id="mod.b", allowed=set(["tune.batch", "tune.mode"])),
    }
    stab = new_state()

    # Intentionally unsorted inputs with tied scores to exercise tie-breakers.
    candidates = [
        PortfolioCandidate(
            module_id="mod.b",
            node_id="node.b",
            knob_name="mode",
            proposed_value="fast",
            impact=ImpactVector(delta_latency_ms_p95=-1.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
            reason_tags=("latency_down",),
        ),
        PortfolioCandidate(
            module_id="mod.a",
            node_id="node.a",
            knob_name="mode",
            proposed_value="fast",
            impact=ImpactVector(delta_latency_ms_p95=-1.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
            reason_tags=("latency_down",),
        ),
        PortfolioCandidate(
            module_id="mod.a",
            node_id="node.a",
            knob_name="batch_size",
            proposed_value=64,
            impact=ImpactVector(delta_latency_ms_p95=-1.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
            reason_tags=("latency_down",),
        ),
    ]

    weights = PortfolioObjectiveWeights(w_latency=-1.0, w_cost=-1.0, w_error=-1.0, w_throughput=1.0)
    budgets = PortfolioBudgets(max_total_cost_units=None, max_total_latency_ms_p95=None, max_changes_per_cycle=10)

    sel1 = select_portfolio(
        candidates=candidates,
        tuning_envelopes=envs,
        capabilities=caps,
        stabilization=stab,
        source_cycle_id="cycle-001",
        objective_weights=weights,
        budgets=budgets,
    )
    sel2 = select_portfolio(
        candidates=list(reversed(candidates)),
        tuning_envelopes=envs,
        capabilities=caps,
        stabilization=stab,
        source_cycle_id="cycle-001",
        objective_weights=weights,
        budgets=budgets,
    )

    assert [c.module_id + ":" + c.knob_name for c in sel1.selected_candidates] == [
        c.module_id + ":" + c.knob_name for c in sel2.selected_candidates
    ]
    assert list(sel1.module_tuning_irs.keys()) == list(sel2.module_tuning_irs.keys())
    assert sel1.module_tuning_irs == sel2.module_tuning_irs

    portfolio_ir = {
        "schema_version": "portfolio-tuning-ir/0.4",
        "portfolio_hash": "",
        "source_cycle_id": "cycle-001",
        "mode": "applied_tune",
        "objective_weights": weights.to_dict(),
        "budgets": budgets.to_dict(),
        "modules": [
            # stable module ordering
            {"module_id": mid, "node_id": ir["node_id"], "tuning_ir": ir, "selected_knobs": sorted(list(ir["assignments"].keys())), "estimated_impact": sel1.totals.to_dict(), "total_score": sel1.total_score, "promotion_candidates": []}
            for mid, ir in sorted(sel1.module_tuning_irs.items(), key=lambda kv: kv[0])
        ],
        "reason_tags": ["determinism_golden"],
    }
    locked1 = lock_portfolio_tuning_ir(portfolio_ir)
    locked2 = lock_portfolio_tuning_ir(portfolio_ir)
    assert locked1["portfolio_hash"] == locked2["portfolio_hash"]


from aal_core.ers.capabilities import CapabilityToken
from aal_core.ers.stabilization import new_state

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
            {"name": "k1", "kind": "int", "min_value": 1, "max_value": 10, "hot_apply": True, "stabilization_cycles": 0, "capability_required": "cap.k1"},
            {"name": "k2", "kind": "int", "min_value": 1, "max_value": 10, "hot_apply": True, "stabilization_cycles": 0, "capability_required": "cap.k2"},
            {"name": "k3", "kind": "int", "min_value": 1, "max_value": 10, "hot_apply": True, "stabilization_cycles": 0, "capability_required": "cap.k3"},
        ],
    }


def test_portfolio_budget_enforcement_cost_and_change_cap():
    envs = {"m": _env("m")}
    caps = {"m": CapabilityToken(module_id="m", allowed=set(["cap.k1", "cap.k2", "cap.k3"]))}
    stab = new_state()

    candidates = [
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k1",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=0.0, delta_cost_units=5.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
            reason_tags=("spend5",),
        ),
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k2",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=0.0, delta_cost_units=4.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
            reason_tags=("spend4",),
        ),
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k3",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=0.0, delta_cost_units=3.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
            reason_tags=("spend3",),
        ),
    ]

    # Max 2 changes and max cost spend=7 => should pick k3 (3) + k2 (4), skip k1 (5).
    weights = PortfolioObjectiveWeights(w_latency=0.0, w_cost=-1.0, w_error=0.0, w_throughput=0.0)
    budgets = PortfolioBudgets(max_total_cost_units=7.0, max_total_latency_ms_p95=None, max_changes_per_cycle=2)

    sel = select_portfolio(
        candidates=candidates,
        tuning_envelopes=envs,
        capabilities=caps,
        stabilization=stab,
        source_cycle_id="c",
        objective_weights=weights,
        budgets=budgets,
    )
    chosen = [c.knob_name for c in sel.selected_candidates]
    assert chosen == ["k3", "k2"]


def test_portfolio_budget_enforcement_latency_budget_spend_only_positive():
    envs = {"m": _env("m")}
    caps = {"m": CapabilityToken(module_id="m", allowed=set(["cap.k1", "cap.k2", "cap.k3"]))}
    stab = new_state()

    candidates = [
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k1",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=10.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
        ),
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k2",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=-100.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
        ),
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k3",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=5.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
        ),
    ]

    weights = PortfolioObjectiveWeights(w_latency=-1.0, w_cost=0.0, w_error=0.0, w_throughput=0.0)
    budgets = PortfolioBudgets(max_total_cost_units=None, max_total_latency_ms_p95=12.0, max_changes_per_cycle=10)

    sel = select_portfolio(
        candidates=candidates,
        tuning_envelopes=envs,
        capabilities=caps,
        stabilization=stab,
        source_cycle_id="c",
        objective_weights=weights,
        budgets=budgets,
    )
    # k2 has negative delta latency (good) and consumes 0 budget spend; should always be included.
    assert "k2" in [c.knob_name for c in sel.selected_candidates]
    # Positive latency deltas spend budget; can include both k3(5) and k1(10)? No (would exceed 12).
    assert sum(max(0.0, c.impact.delta_latency_ms_p95) for c in sel.selected_candidates) <= 12.0


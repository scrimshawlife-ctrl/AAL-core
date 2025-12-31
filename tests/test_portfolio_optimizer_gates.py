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
            {"name": "k", "kind": "int", "min_value": 1, "max_value": 10, "hot_apply": True, "stabilization_cycles": 0, "capability_required": "cap.k"},
        ],
    }


def test_no_envelope_means_no_candidate():
    envs = {"has_env": _env("has_env")}
    caps = {"has_env": CapabilityToken(module_id="has_env", allowed=set(["cap.k"]))}
    stab = new_state()

    candidates = [
        PortfolioCandidate(
            module_id="missing_env",
            node_id="n0",
            knob_name="k",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=-1.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
        )
    ]
    sel = select_portfolio(
        candidates=candidates,
        tuning_envelopes=envs,
        capabilities=caps,
        stabilization=stab,
        source_cycle_id="c",
        objective_weights=PortfolioObjectiveWeights(w_latency=-1.0, w_cost=0.0, w_error=0.0, w_throughput=0.0),
        budgets=PortfolioBudgets(max_total_cost_units=None, max_total_latency_ms_p95=None, max_changes_per_cycle=10),
    )
    assert sel.selected_candidates == ()


def test_capability_denied_excludes_candidate():
    envs = {"m": _env("m")}
    caps = {"m": CapabilityToken(module_id="m", allowed=set([]))}
    stab = new_state()

    candidates = [
        PortfolioCandidate(
            module_id="m",
            node_id="n",
            knob_name="k",
            proposed_value=2,
            impact=ImpactVector(delta_latency_ms_p95=-1.0, delta_cost_units=0.0, delta_error_rate=0.0, delta_throughput_per_s=0.0),
        )
    ]
    sel = select_portfolio(
        candidates=candidates,
        tuning_envelopes=envs,
        capabilities=caps,
        stabilization=stab,
        source_cycle_id="c",
        objective_weights=PortfolioObjectiveWeights(w_latency=-1.0, w_cost=0.0, w_error=0.0, w_throughput=0.0),
        budgets=PortfolioBudgets(max_total_cost_units=None, max_total_latency_ms_p95=None, max_changes_per_cycle=10),
    )
    assert sel.selected_candidates == ()


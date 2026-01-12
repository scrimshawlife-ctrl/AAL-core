from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ImpactVector:
    """
    Structured impact metrics for portfolio optimization.
    """
    delta_latency_ms_p95: float = 0.0
    delta_cost_units: float = 0.0
    delta_error_rate: float = 0.0
    delta_throughput_per_s: float = 0.0


@dataclass(frozen=True)
class PortfolioBudgets:
    """
    Budget constraints for portfolio optimization.
    """
    cost_units: Optional[float] = None
    latency_ms_p95: Optional[float] = None


@dataclass(frozen=True)
class PortfolioCandidate:
    """
    Candidate tuning configuration for portfolio selection.
    """
    module_id: str
    knob: str
    value: Any
    impact: ImpactVector


@dataclass(frozen=True)
class PortfolioObjectiveWeights:
    """
    Objective function weights for portfolio optimization.
    """
    w_latency: float = 1.0
    w_cost: float = 1.0
    w_error: float = 1.0
    w_throughput: float = 1.0


@dataclass(frozen=True)
class PortfolioPolicy:
    """
    Deterministic selection policy for portfolio optimization.
    """

    schema_version: str
    source_cycle_id: str
    max_changes_per_cycle: int

    # Shared budgets (rent-style constraints)
    budget_cost_units: Optional[float] = None
    budget_latency_ms_p95: Optional[float] = None

    # Objective weights
    w_latency: float = 1.0
    w_cost: float = 1.0
    w_error: float = 1.0
    w_throughput: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


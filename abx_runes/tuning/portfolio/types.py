from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional


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


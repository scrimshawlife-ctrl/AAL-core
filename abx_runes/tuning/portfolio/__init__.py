"""
Portfolio tuning plane (v0.4)

This package adds a "portfolio" layer on top of module-level TuningIRs:
- a single PortfolioTuningIR bundles multiple module TuningIRs + global metadata
- a deterministic greedy optimizer selects knob-change candidates under budgets
"""

from .types import (
    PortfolioTuningIR,
    PortfolioBudgets,
    PortfolioObjectiveWeights,
    PortfolioCandidate,
    PortfolioSelection,
)
from .optimizer import select_portfolio


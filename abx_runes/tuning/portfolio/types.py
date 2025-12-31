from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

from abx_runes.tuning.types import KnobValue, TuningMode


PORTFOLIO_SCHEMA_VERSION = "portfolio-tuning-ir/0.4"


@dataclass(frozen=True)
class PortfolioObjectiveWeights:
    """
    Converts an impact vector to a scalar score.

    Note: the optimizer is agnostic to sign conventions, but the default
    interpretation is:
      - negative Δlatency/Δcost/Δerror is "good"
      - positive Δthroughput is "good"
    """

    w_latency: float
    w_cost: float
    w_error: float
    w_throughput: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioBudgets:
    """
    Global budgets/caps for a single optimization cycle.
    """

    max_total_cost_units: Optional[float]
    max_total_latency_ms_p95: Optional[float]
    max_changes_per_cycle: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactVector:
    delta_latency_ms_p95: float
    delta_cost_units: float
    delta_error_rate: float
    delta_throughput_per_s: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PortfolioCandidate:
    """
    A single knob change candidate considered by the optimizer.

    The optimizer will validate this candidate against the module's tuning envelope
    (hot_apply/bounds/type) and capability/stabilization gates before selection.
    """

    module_id: str
    node_id: str
    knob_name: str
    proposed_value: KnobValue
    impact: ImpactVector
    reason_tags: Tuple[str, ...] = ()
    # If True, this candidate represents a "promotion suggestion" only. v0.4 does not auto-promote.
    promotion_candidate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "node_id": self.node_id,
            "knob_name": self.knob_name,
            "proposed_value": self.proposed_value,
            "impact": self.impact.to_dict(),
            "reason_tags": list(self.reason_tags),
            "promotion_candidate": bool(self.promotion_candidate),
        }


@dataclass(frozen=True)
class PortfolioModuleEntry:
    module_id: str
    node_id: str
    tuning_ir: Dict[str, Any]  # module-level tuning-ir/0.1 dict (locked)
    selected_knobs: Tuple[str, ...]
    estimated_impact: ImpactVector
    total_score: float
    promotion_candidates: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module_id": self.module_id,
            "node_id": self.node_id,
            "tuning_ir": dict(self.tuning_ir),
            "selected_knobs": list(self.selected_knobs),
            "estimated_impact": self.estimated_impact.to_dict(),
            "total_score": float(self.total_score),
            "promotion_candidates": list(self.promotion_candidates),
        }


@dataclass(frozen=True)
class PortfolioTuningIR:
    """
    Single artifact bundling multiple module-level TuningIR entries, plus global metadata.
    """

    schema_version: str
    portfolio_hash: str
    source_cycle_id: str
    mode: TuningMode  # portfolio-level intent; individual module tuning IRs carry their own mode too.
    objective_weights: PortfolioObjectiveWeights
    budgets: PortfolioBudgets
    modules: Tuple[PortfolioModuleEntry, ...]
    reason_tags: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "portfolio_hash": self.portfolio_hash,
            "source_cycle_id": self.source_cycle_id,
            "mode": self.mode,
            "objective_weights": self.objective_weights.to_dict(),
            "budgets": self.budgets.to_dict(),
            "modules": [m.to_dict() for m in self.modules],
            "reason_tags": list(self.reason_tags),
        }


@dataclass(frozen=True)
class PortfolioSelection:
    """
    Optimizer output: selected candidates + assembled per-module tuning IRs.
    """

    selected_candidates: Tuple[PortfolioCandidate, ...]
    module_tuning_irs: Dict[str, Dict[str, Any]]  # module_id -> tuning ir dict
    totals: ImpactVector
    total_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_candidates": [c.to_dict() for c in self.selected_candidates],
            "module_tuning_irs": {k: dict(v) for k, v in self.module_tuning_irs.items()},
            "totals": self.totals.to_dict(),
            "total_score": float(self.total_score),
        }


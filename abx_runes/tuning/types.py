from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Literal, Union, Tuple


KnobKind = Literal["int", "float", "bool", "enum", "duration_ms"]
TuningMode = Literal["shadow_tune", "applied_tune", "promoted_tune"]


@dataclass(frozen=True)
class KnobSpec:
    """
    Declares a single tunable knob surface.
    """
    name: str
    kind: KnobKind
    hot_apply: bool
    stabilization_cycles: int
    capability_required: str

    # Bounds / domain
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    enum_values: Optional[Tuple[str, ...]] = None
    default: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.enum_values is not None:
            d["enum_values"] = list(self.enum_values)
        return d


@dataclass(frozen=True)
class TuningEnvelope:
    """
    Declares the entire tuning surface for a module/node.
    """
    schema_version: str
    module_id: str
    knobs: Tuple[KnobSpec, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "module_id": self.module_id,
            "knobs": [k.to_dict() for k in self.knobs],
        }


@dataclass(frozen=True)
class MetricsEnvelope:
    schema_version: str
    module_id: str
    # normalized metrics
    latency_ms_p50: Optional[float] = None
    latency_ms_p95: Optional[float] = None
    cost_units: Optional[float] = None
    throughput_per_s: Optional[float] = None
    error_rate: Optional[float] = None
    drift_score: Optional[float] = None
    entropy_proxy: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


KnobValue = Union[int, float, bool, str]


@dataclass(frozen=True)
class TuningIR:
    """
    ABX-Runes output artifact: knob assignments for a module/node.
    Deterministic, provenance-embedded.
    """
    schema_version: str
    ir_hash: str
    source_cycle_id: str
    mode: TuningMode

    module_id: str
    node_id: str
    assignments: Dict[str, KnobValue]
    reason_tags: Tuple[str, ...] = ()
    evidence_bundle_hash: str = ""  # v0.2: required by ERS if mode==promoted_tune

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "ir_hash": self.ir_hash,
            "source_cycle_id": self.source_cycle_id,
            "mode": self.mode,
            "module_id": self.module_id,
            "node_id": self.node_id,
            "assignments": dict(self.assignments),
            "reason_tags": list(self.reason_tags),
            "evidence_bundle_hash": self.evidence_bundle_hash,
        }

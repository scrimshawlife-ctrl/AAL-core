from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Tuple

from ..contracts.enums import PatternKind
from ..contracts.provenance import sha256_hex
from ..contracts.scene_ir import (
    AnimationPlan,
    PatternInstance,
    SceneEdge,
    SceneEntity,
    SceneField,
    TimeAxis,
)


@dataclass(frozen=True)
class PatternBuildResult:
    instance: PatternInstance
    entities: Tuple[SceneEntity, ...]
    edges: Tuple[SceneEdge, ...]
    fields: Tuple[SceneField, ...]
    time_axis: TimeAxis | str
    animation_plan: AnimationPlan | str
    semantic_map_patch: Mapping[str, Any]
    constraints_patch: Mapping[str, Any]


class BasePattern:
    """
    Pattern contract.

    Patterns are composable *semantic* projections. They must be deterministic.
    """

    kind: PatternKind

    def input_contract(self) -> Mapping[str, Any]:
        raise NotImplementedError

    def required_metrics(self) -> Tuple[str, ...]:
        return ()

    def failure_modes(self) -> Tuple[str, ...]:
        return ("not_computable",)

    def affordances(self) -> Tuple[str, ...]:
        return ()

    def build(self, *, frame_payload: Mapping[str, Any], seed: int) -> PatternBuildResult:
        raise NotImplementedError

    def _instance(
        self, *, pattern_id: str, inputs: Mapping[str, Any], failure_mode: str
    ) -> PatternInstance:
        return PatternInstance(
            kind=self.kind,
            pattern_id=pattern_id,
            inputs_sha256=sha256_hex(inputs),
            failure_mode=failure_mode,
            affordances=tuple(self.affordances()),
        )

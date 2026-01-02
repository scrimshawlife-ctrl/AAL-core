from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from typing import Any, Dict, Mapping, Tuple, Union

from .enums import NotComputable, PatternKind
from .provenance import SourceFrameProvenance, canonical_dumps, sha256_hex

NC = NotComputable.VALUE.value


@dataclass(frozen=True)
class SceneEntity:
    entity_id: str
    kind: str
    label: str
    domain: str
    glyph_rune_id: str  # ABX-Runes only; else "not_computable"
    metrics: Mapping[str, Union[float, str]]  # numeric or "not_computable"
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SceneEdge:
    edge_id: str
    source_id: str
    target_id: str
    kind: str
    domain: str
    resonance_magnitude: Union[float, str]  # numeric or "not_computable"
    uncertainty: Union[float, str]  # 0..1 or "not_computable"


@dataclass(frozen=True)
class SceneField:
    field_id: str
    kind: str
    domain: str
    grid_w: int
    grid_h: int
    values: Union[Tuple[float, ...], str]  # flattened row-major or "not_computable"
    uncertainty: Union[Tuple[float, ...], str]  # per-cell 0..1 or "not_computable"


@dataclass(frozen=True)
class TimeAxis:
    kind: str  # "discrete" | "continuous"
    t0_utc: str
    steps: Union[Tuple[str, ...], str]  # ISO timestamps or "not_computable"


@dataclass(frozen=True)
class AnimationPlan:
    kind: str  # "none" | "timeline"
    steps: Union[Tuple[Mapping[str, Any], ...], str]  # structured plan or "not_computable"


@dataclass(frozen=True)
class PatternInstance:
    kind: PatternKind
    pattern_id: str
    inputs_sha256: str
    failure_mode: str  # "none" or explicit reason
    affordances: Tuple[str, ...]


@dataclass(frozen=True)
class LumaSceneIR:
    """
    Deterministic intermediate representation describing *what* is visualized.
    """

    scene_id: str
    source_frame_provenance: SourceFrameProvenance
    patterns: Tuple[PatternInstance, ...]
    entities: Union[Tuple[SceneEntity, ...], str]
    edges: Union[Tuple[SceneEdge, ...], str]
    fields: Union[Tuple[SceneField, ...], str]
    time_axis: Union[TimeAxis, str]
    animation_plan: Union[AnimationPlan, str]
    semantic_map: Mapping[str, Any]
    constraints: Mapping[str, Any]
    seed: int
    hash: str

    def to_canonical_dict(self, include_hash: bool = True) -> Dict[str, Any]:
        """
        Canonical, hash-stable dict representation.
        """

        def _ent(e: SceneEntity) -> Dict[str, Any]:
            out = {
                "entity_id": e.entity_id,
                "kind": e.kind,
                "label": e.label,
                "domain": e.domain,
                "glyph_rune_id": e.glyph_rune_id,
                "metrics": dict(sorted((str(k), v) for k, v in e.metrics.items())),
            }
            # Optional: preserve backwards-compatible hashes when empty.
            if e.attributes:
                out["attributes"] = dict(sorted((str(k), v) for k, v in e.attributes.items()))
            return out

        def _edge(e: SceneEdge) -> Dict[str, Any]:
            return {
                "edge_id": e.edge_id,
                "source_id": e.source_id,
                "target_id": e.target_id,
                "kind": e.kind,
                "domain": e.domain,
                "resonance_magnitude": e.resonance_magnitude,
                "uncertainty": e.uncertainty,
            }

        def _field(f: SceneField) -> Dict[str, Any]:
            return {
                "field_id": f.field_id,
                "kind": f.kind,
                "domain": f.domain,
                "grid_w": int(f.grid_w),
                "grid_h": int(f.grid_h),
                "values": list(f.values) if isinstance(f.values, tuple) else f.values,
                "uncertainty": list(f.uncertainty)
                if isinstance(f.uncertainty, tuple)
                else f.uncertainty,
            }

        def _time(t: TimeAxis) -> Dict[str, Any]:
            return {
                "kind": t.kind,
                "t0_utc": t.t0_utc,
                "steps": list(t.steps) if isinstance(t.steps, tuple) else t.steps,
            }

        def _anim(a: AnimationPlan) -> Dict[str, Any]:
            return {
                "kind": a.kind,
                "steps": list(a.steps) if isinstance(a.steps, tuple) else a.steps,
            }

        patterns = tuple(sorted(self.patterns, key=lambda p: (p.kind.value, p.pattern_id)))
        out: Dict[str, Any] = {
            "scene_id": self.scene_id,
            "source_frame_provenance": {
                "module": self.source_frame_provenance.module,
                "utc": self.source_frame_provenance.utc,
                "payload_sha256": self.source_frame_provenance.payload_sha256,
                "vendor_lock_sha256": self.source_frame_provenance.vendor_lock_sha256,
                "manifest_sha256": self.source_frame_provenance.manifest_sha256,
                "abx_runes_used": list(self.source_frame_provenance.abx_runes_used),
                "abx_runes_gate_state": self.source_frame_provenance.abx_runes_gate_state,
            },
            "patterns": [
                {
                    "kind": p.kind.value,
                    "pattern_id": p.pattern_id,
                    "inputs_sha256": p.inputs_sha256,
                    "failure_mode": p.failure_mode,
                    "affordances": list(p.affordances),
                }
                for p in patterns
            ],
            "entities": (
                NC
                if isinstance(self.entities, str)
                else [_ent(e) for e in sorted(self.entities, key=lambda e: e.entity_id)]
            ),
            "edges": (
                NC
                if isinstance(self.edges, str)
                else [_edge(e) for e in sorted(self.edges, key=lambda e: e.edge_id)]
            ),
            "fields": (
                NC
                if isinstance(self.fields, str)
                else [_field(f) for f in sorted(self.fields, key=lambda f: f.field_id)]
            ),
            "time_axis": NC if isinstance(self.time_axis, str) else _time(self.time_axis),
            "animation_plan": NC
            if isinstance(self.animation_plan, str)
            else _anim(self.animation_plan),
            "semantic_map": dict(sorted((str(k), v) for k, v in self.semantic_map.items())),
            "constraints": dict(sorted((str(k), v) for k, v in self.constraints.items())),
            "seed": int(self.seed),
        }
        if include_hash:
            out["hash"] = self.hash
        return out

    @staticmethod
    def compute_hash(scene: "LumaSceneIR") -> str:
        d = scene.to_canonical_dict(include_hash=False)
        return sha256_hex(d)

    def to_json(self) -> str:
        return canonical_dumps(self.to_canonical_dict(include_hash=True))

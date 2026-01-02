from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..contracts.enums import NotComputable, PatternKind
from ..contracts.provenance import SourceFrameProvenance, stable_scene_seed
from ..contracts.scene_ir import AnimationPlan, LumaSceneIR, PatternInstance, TimeAxis
from ..ideation.constraints import IdeationConstraints
from ..ideation.proposer import propose
from ..registry import default_registry

NC = NotComputable.VALUE.value


def _frame_payload(frame: Any) -> Mapping[str, Any]:
    if hasattr(frame, "model_dump"):
        f = frame.model_dump()
        return f.get("payload") or f.get("attachments") or {}
    if isinstance(frame, Mapping):
        return frame.get("payload") or {}
    raise TypeError(f"Unsupported frame type: {type(frame)!r}")


def _select_patterns(
    payload: Mapping[str, Any], overrides: Optional[Sequence[str]]
) -> Tuple[PatternKind, ...]:
    if overrides:
        out: List[PatternKind] = []
        for s in overrides:
            try:
                out.append(PatternKind(str(s)))
            except Exception:
                continue
        return tuple(out)

    kinds: List[PatternKind] = []
    if isinstance(payload.get("motifs"), list):
        kinds.extend([PatternKind.MOTIF_GRAPH, PatternKind.CLUSTER_BLOOM])
    if isinstance(payload.get("timeline"), list):
        kinds.append(PatternKind.TEMPORAL_BRAID)
    if isinstance(payload.get("domains"), list):
        kinds.append(PatternKind.DOMAIN_LATTICE)
    if isinstance(payload.get("flows"), list):
        kinds.append(PatternKind.SANKEY_TRANSFER)
    if isinstance(payload.get("field"), Mapping):
        kinds.append(PatternKind.RESONANCE_FIELD)

    if not kinds:
        # Always include at least one pattern instance with explicit failure modes.
        kinds = [PatternKind.MOTIF_GRAPH]
    return tuple(kinds)


def compile_scene(
    resonance_frame: Any,
    *,
    pattern_overrides: Optional[Sequence[str]] = None,
    exploration: bool = False,
) -> LumaSceneIR:
    """
    ResonanceFrame -> LumaSceneIR
    """

    frame_prov = SourceFrameProvenance.from_resonance_frame(resonance_frame)
    payload = _frame_payload(resonance_frame)
    seed = stable_scene_seed(frame_prov)

    reg = default_registry()
    kinds = _select_patterns(payload, pattern_overrides)

    pattern_instances: List[PatternInstance] = []
    entities_by_id: Dict[str, Any] = {}
    edges_by_id: Dict[str, Any] = {}
    fields_by_id: Dict[str, Any] = {}
    semantic_map: Dict[str, Any] = {}
    constraints: Dict[str, Any] = {
        "visualization_non_influential": True,
        "evidence_gated_interpretation": True,
        "incremental_patch_only": True,
        "glyphs": "abx_runes_only",
    }

    time_axis: TimeAxis | str = NC
    animation_plan: AnimationPlan | str = NC

    failures: List[str] = []
    for kind in kinds:
        p = reg.patterns.get(kind)
        if p is None:
            failures.append(f"missing_pattern:{kind.value}")
            continue
        r = p.build(frame_payload=payload, seed=seed)
        pattern_instances.append(r.instance)
        if r.instance.failure_mode != "none":
            failures.append(r.instance.failure_mode)

        # merge (first-wins) deterministically in the provided kinds order
        for e in r.entities:
            entities_by_id.setdefault(e.entity_id, e)
        for ed in r.edges:
            edges_by_id.setdefault(ed.edge_id, ed)
        for f in r.fields:
            fields_by_id.setdefault(f.field_id, f)
        if time_axis == NC and r.time_axis != NC:
            time_axis = r.time_axis
        if animation_plan == NC and r.animation_plan != NC:
            animation_plan = r.animation_plan
        semantic_map.update(dict(r.semantic_map_patch))
        constraints.update(dict(r.constraints_patch))

    if exploration:
        ideation_constraints = IdeationConstraints.v1_default()
        props = propose(
            constraints=ideation_constraints,
            available_patterns=list(reg.patterns.keys()),
            baseline_semantics=semantic_map,
            failure_signals=failures,
        )
        semantic_map["ideation_proposals"] = [
            {
                "proposal_id": p.proposal_id,
                "composed_of": [k.value for k in p.composed_of],
                "semantic_justification": p.semantic_justification,
                "readability_risks": list(p.readability_risks),
                "score": {
                    "information_gain": p.score.information_gain,
                    "cognitive_load": p.score.cognitive_load,
                    "redundancy": p.score.redundancy,
                    "total": p.score.total,
                },
                "required_inputs": list(p.required_inputs),
            }
            for p in props
        ]
        constraints["ideation_constraints"] = ideation_constraints.as_dict()
        constraints["exploration"] = True
    else:
        constraints["exploration"] = False

    entities = tuple(sorted(entities_by_id.values(), key=lambda x: x.entity_id))
    edges = tuple(sorted(edges_by_id.values(), key=lambda x: x.edge_id))
    fields = tuple(sorted(fields_by_id.values(), key=lambda x: x.field_id))

    scene_id = f"luma:{frame_prov.payload_sha256[:12]}"
    scene = LumaSceneIR(
        scene_id=scene_id,
        source_frame_provenance=frame_prov,
        patterns=tuple(pattern_instances),
        entities=entities if entities else NC,
        edges=edges if edges else NC,
        fields=fields if fields else NC,
        time_axis=time_axis,
        animation_plan=animation_plan,
        semantic_map=semantic_map,
        constraints=constraints,
        seed=seed,
        hash="",
    )
    scene_hash = LumaSceneIR.compute_hash(scene)
    return LumaSceneIR(
        scene_id=scene.scene_id,
        source_frame_provenance=scene.source_frame_provenance,
        patterns=scene.patterns,
        entities=scene.entities,
        edges=scene.edges,
        fields=scene.fields,
        time_axis=scene.time_axis,
        animation_plan=scene.animation_plan,
        semantic_map=scene.semantic_map,
        constraints=scene.constraints,
        seed=scene.seed,
        hash=scene_hash,
    )

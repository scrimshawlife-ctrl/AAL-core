from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR

NC = NotComputable.VALUE.value


def render_animation_plan(scene: LumaSceneIR) -> RenderArtifact:
    if isinstance(scene.animation_plan, str):
        return RenderArtifact.not_computable(
            kind=ArtifactKind.ANIMATION_PLAN_JSON,
            mode=LumaMode.ANIMATED,
            scene_hash=scene.hash,
            mime_type="application/json",
            provenance={"scene_hash": scene.hash},
            backend="animation_plan/v1",
            reason="scene.animation_plan is not_computable",
        )

    heatmap = _build_heatmap_module(scene)

    payload: Dict[str, Any] = {
        "scene_hash": scene.hash,
        "time_axis": (
            scene.time_axis if isinstance(scene.time_axis, str) else scene.time_axis.__dict__
        ),
        "animation_plan": scene.animation_plan.__dict__,
        "modules": {
            "heatmap": heatmap,
        },
        "semantic_map": dict(scene.semantic_map),
        "constraints": dict(scene.constraints),
        "source_frame_provenance": scene.to_canonical_dict(True)["source_frame_provenance"],
    }
    prov = {
        "scene_hash": scene.hash,
        "source_frame_provenance": scene.to_canonical_dict(True)["source_frame_provenance"],
    }
    return RenderArtifact.from_text(
        kind=ArtifactKind.ANIMATION_PLAN_JSON,
        mode=LumaMode.ANIMATED,
        scene_hash=scene.hash,
        mime_type="application/json",
        text=canonical_dumps(payload),
        provenance=prov,
        backend="animation_plan/v1",
        warnings=tuple(),
    )


def _build_heatmap_module(scene: LumaSceneIR) -> Dict[str, Any]:
    heatmap: Dict[str, Any] = {"enabled": False, "cells": []}
    if isinstance(scene.entities, str):
        return heatmap

    motifs = [e for e in scene.entities if e.kind == "motif"]
    domains = [e for e in scene.entities if e.kind == "domain"]
    if not motifs or not domains:
        return heatmap

    domain_ids: Set[str] = set()
    for d in domains:
        if d.domain != NC:
            domain_ids.add(d.domain)

    mapped: List[Tuple[str, str]] = []
    for m in motifs:
        dom = m.domain
        if isinstance(dom, str) and dom in domain_ids:
            mapped.append((m.entity_id, dom))
    mapped = sorted(mapped)

    if mapped:
        heatmap["enabled"] = True
        heatmap["cells"] = [
            {
                "id": f"heat.{mid}.{did}",
                "type": "heatmap_cell",
                "target": {"motif_id": mid, "domain_id": did},
                "hooks": {"decay_from": mid, "pulse_from": "edges"},
            }
            for mid, did in mapped
        ]
    return heatmap

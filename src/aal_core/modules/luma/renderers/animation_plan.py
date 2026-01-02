from __future__ import annotations

from typing import Any, Dict

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

    payload: Dict[str, Any] = {
        "scene_hash": scene.hash,
        "time_axis": (
            scene.time_axis if isinstance(scene.time_axis, str) else scene.time_axis.__dict__
        ),
        "animation_plan": scene.animation_plan.__dict__,
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

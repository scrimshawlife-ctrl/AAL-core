from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import AnimationPlan, LumaSceneIR, TimeAxis

NC = NotComputable.VALUE.value


def render_animation_plan(scene: LumaSceneIR) -> RenderArtifact:
    """
    Deterministic IR-level motion plan.

    This is an exportable artifact (JSON), derived from:
      - edge resonance magnitudes (pulse)
      - constraints.halflife_seconds (decay)
      - temporal braid (if present) for replay steps
    """

    # parameters (deterministic)
    halflife = scene.constraints.get("halflife_seconds", NC)
    if halflife == NC:
        halflife = scene.semantic_map.get("halflife_seconds", 86400)
    try:
        hl = float(halflife)
    except Exception:
        hl = 86400.0
    if hl <= 0:
        hl = 86400.0

    # pulses from resonance/synch edges
    pulses: List[Dict[str, Any]] = []
    if not isinstance(scene.edges, str):
        edges = [e for e in scene.edges if e.kind in ("resonance", "synch", "synchronicity")]
        edges = sorted(edges, key=lambda e: (e.kind, e.source_id, e.target_id, e.edge_id))
        for i, e in enumerate(edges):
            strength = (
                float(e.resonance_magnitude)
                if isinstance(e.resonance_magnitude, (int, float))
                else 0.0
            )
            strength = max(0.0, strength)
            pulses.append(
                {
                    "id": f"pulse.{i}",
                    "type": "edge_pulse",
                    "edge": {
                        "source": e.source_id,
                        "target": e.target_id,
                        "kind": e.kind,
                        "domain": e.domain,
                    },
                    "strength": strength,
                    "curve": "ease_in_out",
                    "period_seconds": max(1.0, 6.0 - 4.0 * min(1.0, strength)),
                }
            )

    # decays apply to motifs by default
    decays: List[Dict[str, Any]] = []
    if not isinstance(scene.entities, str):
        motifs = sorted([e.entity_id for e in scene.entities if e.kind == "motif"])
        for mid in motifs:
            decays.append(
                {
                    "id": f"decay.{mid}",
                    "type": "opacity_decay",
                    "target": {"entity_id": mid},
                    "halflife_seconds": hl,
                }
            )

    # replay derived from temporal braid (if present)
    replay_enabled = False
    replay_steps: Tuple[Mapping[str, Any], ...] = tuple()
    if isinstance(scene.time_axis, TimeAxis) and isinstance(scene.animation_plan, AnimationPlan):
        if scene.animation_plan.kind == "timeline" and not isinstance(scene.animation_plan.steps, str):
            replay_enabled = True
            replay_steps = tuple(scene.animation_plan.steps)

    plan: Dict[str, Any] = {
        "schema": "LumaAnimationPlan.v0",
        "scene_hash": scene.hash,
        "fps": 30,
        "modules": {
            "pulse": {"enabled": True, "items": pulses},
            "decay": {"enabled": True, "items": decays},
            "replay": {"enabled": replay_enabled, "steps": list(replay_steps)},
        },
        "provenance": {
            "scene_hash": scene.hash,
            "source_frame_provenance": scene.to_canonical_dict(True)["source_frame_provenance"],
            "constraints": dict(scene.constraints),
        },
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
        text=canonical_dumps(plan),
        provenance=prov,
        backend="animation_plan/v2",
        warnings=tuple(),
    )

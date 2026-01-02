from __future__ import annotations

from typing import Any, List, Optional, Sequence, Tuple

from ..contracts.enums import ArtifactKind, LumaMode
from ..contracts.render_artifact import RenderArtifact
from ..renderers.animation_plan import render_animation_plan
from ..renderers.svg_static import render_svg
from ..renderers.web_canvas import render_html_canvas
from .compile_scene import compile_scene
from .validate_scene import validate_scene


def render(
    resonance_frame: Any,
    *,
    mode: str = "static",
    pattern_overrides: Optional[Sequence[str]] = None,
    exploration: bool = False,
) -> Tuple[RenderArtifact, ...]:
    """
    Integration contract:

        ResonanceFrame -> LumaSceneIR -> RenderArtifacts
    """

    m = LumaMode(mode)
    scene = compile_scene(
        resonance_frame, pattern_overrides=pattern_overrides, exploration=exploration
    )
    v = validate_scene(scene)
    if not v.ok:
        # Keep deterministic: encode errors as a not-computable artifact in the requested mode.
        desired = {
            LumaMode.STATIC: ArtifactKind.SVG,
            LumaMode.INTERACTIVE: ArtifactKind.HTML_CANVAS,
            LumaMode.ANIMATED: ArtifactKind.ANIMATION_PLAN_JSON,
        }[m]
        return (
            RenderArtifact.not_computable(
                kind=desired,
                mode=m,
                scene_hash=scene.hash,
                mime_type="application/json",
                provenance={"scene_hash": scene.hash, "errors": list(v.errors)},
                backend="luma/validate_scene",
                reason="scene validation failed",
            ),
        )

    artifacts: List[RenderArtifact] = []
    if m == LumaMode.STATIC:
        artifacts.append(render_svg(scene))
    elif m == LumaMode.INTERACTIVE:
        artifacts.append(render_html_canvas(scene))
    elif m == LumaMode.ANIMATED:
        artifacts.append(render_animation_plan(scene))
    else:
        raise ValueError(f"Unsupported mode: {mode!r}")
    return tuple(artifacts)

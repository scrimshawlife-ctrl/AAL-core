from __future__ import annotations

import html

from ..contracts.enums import ArtifactKind, LumaMode
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR


def render_html_canvas(scene: LumaSceneIR) -> RenderArtifact:
    """
    Interactive stub: embed scene IR + a minimal, deterministic JS viewer.
    """

    scene_json = scene.to_json()
    # Deterministic HTML (no timestamps).
    html_doc = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="luma-scene-hash" content="{html.escape(scene.hash)}" />
    <title>LUMA Canvas</title>
    <style>
      body {{ margin: 0; background: #0b0f14; color: #e6eef7; font-family: monospace; }}
      #wrap {{ padding: 12px; }}
      canvas {{ border: 1px solid #223; background: #0b0f14; }}
      pre {{ white-space: pre-wrap; }}
    </style>
  </head>
  <body>
    <div id="wrap">
      <div><b>LUMA</b> scene_hash=<span id="h"></span></div>
      <canvas id="c" width="480" height="360"></canvas>
      <pre id="dbg"></pre>
    </div>
    <script>
      const SCENE = {scene_json};
      document.getElementById("h").textContent = SCENE.hash;
      const entitiesN = (
        SCENE.entities === "not_computable" ? "not_computable" : SCENE.entities.length
      );
      const edgesN = (
        SCENE.edges === "not_computable" ? "not_computable" : SCENE.edges.length
      );
      const fieldsN = (
        SCENE.fields === "not_computable" ? "not_computable" : SCENE.fields.length
      );
      document.getElementById("dbg").textContent = JSON.stringify({{
        patterns: SCENE.patterns,
        entities_n: entitiesN,
        edges_n: edgesN,
        fields_n: fieldsN,
      }}, null, 2);
      // Rendering is intentionally minimal in v1; LUMA semantics are in the IR.
      const canvas = document.getElementById("c");
      const ctx = canvas.getContext("2d");
      ctx.fillStyle = "#0b0f14";
      ctx.fillRect(0,0,canvas.width,canvas.height);
      ctx.fillStyle = "#e6eef7";
      ctx.fillText("Interactive canvas stub (v1)", 12, 24);
    </script>
  </body>
</html>
"""
    prov = {
        "scene_hash": scene.hash,
        "source_frame_provenance": scene.to_canonical_dict(True)["source_frame_provenance"],
    }
    return RenderArtifact.from_text(
        kind=ArtifactKind.HTML_CANVAS,
        mode=LumaMode.INTERACTIVE,
        scene_hash=scene.hash,
        mime_type="text/html; charset=utf-8",
        text=html_doc,
        provenance=prov,
        backend="web_canvas/v1",
        warnings=("interactive renderer is a stub in v1",),
    )

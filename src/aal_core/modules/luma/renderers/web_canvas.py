from __future__ import annotations

import html

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR
from .base import alpha_from_uncertainty, domain_color, stable_layout_points, thickness_from_magnitude

NC = NotComputable.VALUE.value


def render_html_canvas(scene: LumaSceneIR) -> RenderArtifact:
    """
    Interactive deterministic canvas render of the LumaSceneIR.
    """

    scene_json = scene.to_json()
    layout_points = stable_layout_points(scene)
    layout = {
        eid: {"x": layout_points[eid].x, "y": layout_points[eid].y}
        for eid in sorted(layout_points)
    }

    entities_draw = []
    if not isinstance(scene.entities, str):
        for ent in sorted(scene.entities, key=lambda e: e.entity_id):
            sal = ent.metrics.get("salience", 0.0)
            if isinstance(sal, (int, float)):
                radius = 6.0 + min(10.0, max(0.0, float(sal)) ** 0.5 * 6.0)
            else:
                radius = 8.0 if ent.kind in ("motif", "subdomain") else 9.5
            entities_draw.append(
                {
                    "id": ent.entity_id,
                    "label": ent.label,
                    "kind": ent.kind,
                    "domain": ent.domain,
                    "glyph_rune_id": ent.glyph_rune_id,
                    "color": domain_color(ent.domain),
                    "radius": radius,
                }
            )

    edges_draw = []
    if not isinstance(scene.edges, str):
        for edge in sorted(scene.edges, key=lambda e: e.edge_id):
            if edge.source_id not in layout_points or edge.target_id not in layout_points:
                continue
            thickness = (
                thickness_from_magnitude(float(edge.resonance_magnitude))
                if isinstance(edge.resonance_magnitude, (int, float))
                else 1.0
            )
            alpha = (
                alpha_from_uncertainty(float(edge.uncertainty))
                if isinstance(edge.uncertainty, (int, float))
                else 0.65
            )
            edges_draw.append(
                {
                    "source_id": edge.source_id,
                    "target_id": edge.target_id,
                    "kind": edge.kind,
                    "domain": edge.domain,
                    "color": domain_color(edge.domain),
                    "thickness": thickness,
                    "alpha": alpha,
                }
            )

    fields_draw = []
    if not isinstance(scene.fields, str):
        for field in sorted(scene.fields, key=lambda f: f.field_id):
            values = list(field.values) if isinstance(field.values, tuple) else field.values
            uncertainty = (
                list(field.uncertainty) if isinstance(field.uncertainty, tuple) else field.uncertainty
            )
            fields_draw.append(
                {
                    "id": field.field_id,
                    "kind": field.kind,
                    "domain": field.domain,
                    "color": domain_color(field.domain),
                    "grid_w": int(field.grid_w),
                    "grid_h": int(field.grid_h),
                    "values": values,
                    "uncertainty": uncertainty,
                }
            )

    layout_json = canonical_dumps(layout)
    draw_json = canonical_dumps(
        {"entities": entities_draw, "edges": edges_draw, "fields": fields_draw}
    )
    provenance_payload = {
        "scene_hash": scene.hash,
        "source_frame_provenance": scene.to_canonical_dict(True)["source_frame_provenance"],
    }
    provenance_json = canonical_dumps(provenance_payload)
    # Deterministic HTML (no timestamps).
    html_doc = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="luma-scene-hash" content="{html.escape(scene.hash)}" />
    <meta name="luma-source-frame-provenance" content="{html.escape(provenance_json)}" />
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
      <canvas id="c" width="640" height="420"></canvas>
      <pre id="dbg"></pre>
    </div>
    <script>
      const SCENE = {scene_json};
      const LAYOUT = {layout_json};
      const DRAW = {draw_json};
      const NC = "{NC}";
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
        layout_n: Object.keys(LAYOUT).length,
      }}, null, 2);

      const canvas = document.getElementById("c");
      const ctx = canvas.getContext("2d");

      const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
      const hexToRgb = (hex) => {{
        const h = hex.replace("#", "");
        if (h.length !== 6) return {{ r: 180, g: 188, b: 196 }};
        return {{
          r: parseInt(h.substring(0, 2), 16),
          g: parseInt(h.substring(2, 4), 16),
          b: parseInt(h.substring(4, 6), 16),
        }};
      }};
      const withAlpha = (hex, a) => {{
        const rgb = hexToRgb(hex);
        return `rgba(${{rgb.r}},${{rgb.g}},${{rgb.b}},${{a.toFixed(3)}})`;
      }};

      const panelW = 190;
      const graphW = canvas.width - panelW;
      const graphCenter = {{ x: graphW * 0.5, y: canvas.height * 0.5 }};
      const fieldX = graphW + 12;
      const fieldW = panelW - 24;

      ctx.fillStyle = "#0b0f14";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "#121a22";
      ctx.fillRect(graphW, 0, panelW, canvas.height);
      ctx.fillStyle = "#223";
      ctx.fillRect(graphW, 0, 1, canvas.height);

      const posFor = (id) => {{
        const p = LAYOUT[id];
        if (!p) return null;
        return {{ x: graphCenter.x + p.x, y: graphCenter.y + p.y }};
      }};

      const fields = DRAW.fields || [];
      if (fields.length) {{
        const padY = 16;
        const gapY = 14;
        const availableH = canvas.height - padY * 2 - gapY * (fields.length - 1);
        const blockH = Math.max(60, Math.min(120, availableH / Math.max(1, fields.length)));
        fields.forEach((field, idx) => {{
          const gx = fieldX;
          const gy = padY + idx * (blockH + gapY);
          const gridW = field.grid_w || 0;
          const gridH = field.grid_h || 0;
          const values = Array.isArray(field.values) ? field.values : [];
          const uncert = Array.isArray(field.uncertainty) ? field.uncertainty : [];
          const vmax = values.length ? Math.max(...values.map(v => Number(v) || 0)) : 1.0;

          ctx.fillStyle = "#0f161d";
          ctx.fillRect(gx, gy, fieldW, blockH);
          ctx.strokeStyle = "#223";
          ctx.strokeRect(gx, gy, fieldW, blockH);

          ctx.fillStyle = "#c2cad4";
          ctx.font = "10px monospace";
          const label = field.id || "field";
          ctx.fillText(label, gx + 6, gy + 12);

          if (gridW > 0 && gridH > 0 && values.length >= gridW * gridH) {{
            const cellW = fieldW / gridW;
            const cellH = (blockH - 18) / gridH;
            const color = field.color || "#7f8a99";
            for (let iy = 0; iy < gridH; iy += 1) {{
              for (let ix = 0; ix < gridW; ix += 1) {{
                const i = iy * gridW + ix;
                const v = Number(values[i]) || 0;
                const base = vmax > 0 ? clamp(v / vmax, 0, 1) : 0;
                let alpha = 0.08 + 0.86 * base;
                if (uncert.length > i && Number.isFinite(uncert[i])) {{
                  const u = clamp(Number(uncert[i]), 0, 1);
                  alpha *= (1.0 - 0.75 * u);
                }}
                ctx.fillStyle = withAlpha(color, alpha);
                ctx.fillRect(gx + ix * cellW, gy + 18 + iy * cellH, cellW, cellH);
              }}
            }}
          }}
        }});
      }}

      const edges = DRAW.edges || [];
      edges.forEach((edge) => {{
        const p1 = posFor(edge.source_id);
        const p2 = posFor(edge.target_id);
        if (!p1 || !p2) return;
        const alpha = Number.isFinite(edge.alpha) ? edge.alpha : 0.65;
        ctx.strokeStyle = withAlpha(edge.color || "#7f8a99", alpha);
        ctx.lineWidth = Number.isFinite(edge.thickness) ? edge.thickness : 1.0;
        ctx.beginPath();
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
        ctx.stroke();
      }});

      const entities = DRAW.entities || [];
      entities.forEach((ent) => {{
        const p = posFor(ent.id);
        if (!p) return;
        const radius = Number.isFinite(ent.radius) ? ent.radius : 8;
        ctx.fillStyle = withAlpha(ent.color || "#7f8a99", 0.92);
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = "#0b0f14";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        ctx.fillStyle = "#e6eef7";
        ctx.font = "11px monospace";
        const label = (ent.label || ent.id || "").slice(0, 24);
        ctx.fillText(label, p.x + radius + 4, p.y + 4);
      }});
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
        warnings=tuple(),
    )

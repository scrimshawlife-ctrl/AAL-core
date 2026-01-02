from __future__ import annotations

import html

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR
from .base import (
    alpha_from_uncertainty,
    domain_color,
    stable_layout_points,
    thickness_from_magnitude,
)

NC = NotComputable.VALUE.value


def render_svg(scene: LumaSceneIR) -> RenderArtifact:
    pts = stable_layout_points(scene)

    # SVG canvas is centered; translate by +150 to keep positive coords.
    w, h = 360, 360
    cx, cy = w / 2.0, h / 2.0

    # Metadata must carry full provenance anchors.
    meta = {
        "luma": "LUMA",
        "scene_hash": scene.hash,
        "source_frame_provenance": scene.to_canonical_dict(include_hash=True)[
            "source_frame_provenance"
        ],
        "patterns": scene.to_canonical_dict(include_hash=True)["patterns"],
    }

    lines = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
    )
    lines.append("<metadata>")
    lines.append(html.escape(canonical_dumps(meta)))
    lines.append("</metadata>")
    lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#0b0f14"/>')

    # edges first
    if not isinstance(scene.edges, str):
        for e in sorted(scene.edges, key=lambda x: x.edge_id):
            p1 = pts.get(e.source_id)
            p2 = pts.get(e.target_id)
            if p1 is None or p2 is None:
                continue
            col = domain_color(e.domain)
            sw = 1.0
            if isinstance(e.resonance_magnitude, (int, float)):
                sw = thickness_from_magnitude(float(e.resonance_magnitude))
            alpha = 0.9
            if isinstance(e.uncertainty, (int, float)):
                alpha = alpha_from_uncertainty(float(e.uncertainty))
            x1 = cx + p1.x
            y1 = cy + p1.y
            x2 = cx + p2.x
            y2 = cy + p2.y
            lines.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{col}" stroke-width="{sw:.2f}" stroke-opacity="{alpha:.3f}"/>'
            )

    # nodes
    if not isinstance(scene.entities, str):
        for ent in sorted(scene.entities, key=lambda x: x.entity_id):
            p = pts.get(ent.entity_id)
            if p is None:
                continue
            col = domain_color(ent.domain)
            r = 7.5 if ent.kind in ("motif", "subdomain") else 9.5
            x = cx + p.x
            y = cy + p.y
            lines.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r:.2f}" fill="{col}" fill-opacity="0.95"/>'
            )
            label = html.escape(ent.label[:28])
            lines.append(
                f'<text x="{x + 10.0:.2f}" y="{y + 4.0:.2f}" font-family="monospace" '
                f'font-size="10" fill="#e6eef7" fill-opacity="0.92">{label}</text>'
            )

    lines.append("</svg>")
    svg = "\n".join(lines)
    prov = {
        "scene_hash": scene.hash,
        "source_frame_provenance": scene.to_canonical_dict(True)["source_frame_provenance"],
    }
    return RenderArtifact.from_text(
        kind=ArtifactKind.SVG,
        mode=LumaMode.STATIC,
        scene_hash=scene.hash,
        mime_type="image/svg+xml",
        text=svg,
        provenance=prov,
        backend="svg_static/v1",
        warnings=tuple(),
    )

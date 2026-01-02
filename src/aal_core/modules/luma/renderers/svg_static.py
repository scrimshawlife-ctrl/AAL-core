from __future__ import annotations

from datetime import datetime, timezone
import html
from typing import Any, Iterable, List, Mapping, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import AnimationPlan, LumaSceneIR, SceneEntity
from .base import (
    alpha_from_uncertainty,
    domain_color,
    stable_layout_points,
    thickness_from_magnitude,
)

NC = NotComputable.VALUE.value


def _parse_ts(v: Any) -> float:
    """
    Deterministic timestamp parser:
    - int/float => epoch seconds
    - ISO string => parsed as UTC if no tz
    Raises on failure.
    """
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip()
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    raise ValueError(f"invalid timestamp type: {type(v)}")


def _lane_order_key(ent: SceneEntity) -> Tuple[float, str]:
    o = ent.metrics.get("order") if isinstance(ent.metrics, Mapping) else None
    try:
        order = float(o) if isinstance(o, (int, float, str)) else 0.0
    except Exception:
        order = 0.0
    return (order, ent.entity_id)


def _render_temporal_braid(
    *, scene: LumaSceneIR, w: float, h: float, font_family: str = "monospace"
) -> List[str]:
    """
    Bottom-panel timeline braid:
    - lanes: motif entities (ordered deterministically)
    - knots: timeline steps from scene.animation_plan(kind="timeline")
    """
    if isinstance(scene.entities, str):
        return []
    if isinstance(scene.animation_plan, str):
        return []
    if not isinstance(scene.animation_plan, AnimationPlan) or scene.animation_plan.kind != "timeline":
        return []
    if not isinstance(scene.animation_plan.steps, tuple):
        return []

    steps: List[Mapping[str, Any]] = [
        s for s in scene.animation_plan.steps if isinstance(s, Mapping)
    ]
    if not steps:
        return []

    motifs = [e for e in scene.entities if e.kind == "motif"]
    motifs_s = sorted(motifs, key=_lane_order_key)
    lanes = [m.label for m in motifs_s]
    lane_index = {m: i for i, m in enumerate(lanes)}

    # Parse and order steps deterministically.
    parsed: List[Tuple[float, int, str, Tuple[str, ...]]] = []
    for i, s in enumerate(steps):
        t_raw = s.get("t")
        t_key = str(t_raw) if t_raw is not None else NC
        if t_key == NC:
            # still deterministic but will be rendered on ordinal axis
            ts = float(i)
        else:
            try:
                ts = _parse_ts(t_raw)
            except Exception:
                ts = float(i)
        motifs_raw = s.get("motifs")
        ms = (
            tuple(sorted(str(m) for m in motifs_raw))
            if isinstance(motifs_raw, list)
            else tuple()
        )
        parsed.append((ts, i, t_key, ms))
    parsed.sort(key=lambda x: (x[0], x[1]))

    t0 = parsed[0][0]
    t1 = parsed[-1][0]
    if t1 <= t0:
        t1 = t0 + 1.0

    # Geometry (simple + deterministic)
    pad = 18.0
    band_h = 160.0
    x0 = pad
    x1 = w - pad
    y1 = h - pad
    y0 = y1 - band_h

    lane_top = y0 + 38.0
    lane_bot = y1 - 16.0
    n = max(1, len(lanes))
    lane_h = (lane_bot - lane_top) / n

    def tx(t: float) -> float:
        u = (t - t0) / (t1 - t0)
        u = 0.0 if u < 0.0 else (1.0 if u > 1.0 else u)
        return x0 + u * (x1 - x0)

    parts: List[str] = []
    parts.append('<g id="temporal_braid" opacity="0.9">')
    parts.append(
        f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{(x1 - x0):.2f}" height="{band_h:.2f}" '
        f'fill="none" stroke="#000" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{x0 + 8:.2f}" y="{y0 + 22:.2f}" font-family="{font_family}" '
        f'font-size="11" opacity="0.8">Temporal Braid</text>'
    )
    parts.append(
        f'<text x="{x0 + 132:.2f}" y="{y0 + 22:.2f}" font-family="{font_family}" '
        f'font-size="9" opacity="0.6">t=[{t0:.0f}..{t1:.0f}]</text>'
    )

    # Lanes
    for i, mid in enumerate(lanes):
        y = lane_top + i * lane_h
        parts.append(
            f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
            f'stroke="#000" stroke-width="0.6" opacity="0.30"/>'
        )
        parts.append(
            f'<text x="{x0 + 6:.2f}" y="{(y + lane_h * 0.65):.2f}" font-family="{font_family}" '
            f'font-size="9" opacity="0.75">{html.escape(str(mid)[:28])}</text>'
        )

    # Knots: event markers and per-lane motif ticks
    for ts, idx, t_key, ms in parsed:
        ex = tx(ts)
        # vertical event line
        parts.append(
            f'<line x1="{ex:.2f}" y1="{y0 + 30:.2f}" x2="{ex:.2f}" y2="{y1 - 6:.2f}" '
            f'stroke="#000" stroke-width="0.8" opacity="0.16"/>'
        )
        # top label (t_key)
        parts.append(
            f'<text x="{ex + 4:.2f}" y="{y0 + 34:.2f}" font-family="{font_family}" '
            f'font-size="9" opacity="0.72">{html.escape(str(t_key)[:32])}</text>'
        )
        # per-lane motif tick
        for m in ms:
            i = lane_index.get(m)
            if i is None:
                continue
            y = lane_top + i * lane_h + lane_h * 0.18
            parts.append(
                f'<rect x="{ex - 2.0:.2f}" y="{y:.2f}" width="4.0" '
                f'height="{max(6.0, lane_h * 0.55):.2f}" fill="#000" opacity="0.55"/>'
            )

    parts.append("</g>")
    return parts


def render_svg(scene: LumaSceneIR) -> RenderArtifact:
    pts = stable_layout_points(scene)

    # SVG canvas is centered; translate by +150 to keep positive coords.
    w, h = 720, 520
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

    # Temporal braid band (bottom panel) if timeline present.
    lines.extend(_render_temporal_braid(scene=scene, w=float(w), h=float(h)))

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

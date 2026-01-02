from __future__ import annotations

import html
import math

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR
from ..contracts.provenance import sha256_hex
from .base import (
    alpha_from_uncertainty,
    domain_color,
    stable_layout_points,
    thickness_from_magnitude,
)

NC = NotComputable.VALUE.value


def _domain_column_geometry(
    *, domain_entity_ids: tuple[str, ...], w: float, h: float
) -> dict[str, tuple[float, float, float, float]]:
    """
    Deterministic lattice geometry for domain columns.

    Returns:
        domain_entity_id -> (x_left, x_right, y_top, y_bottom)
    """
    pad = 24.0
    top = pad + 30.0
    bottom = h - pad
    left = pad
    right = w - pad

    height = max(1.0, bottom - top)
    width = max(1.0, right - left)

    n_dom = max(1, len(domain_entity_ids))
    col_w = width / float(n_dom)

    geo: dict[str, tuple[float, float, float, float]] = {}
    for i, dom_eid in enumerate(domain_entity_ids):
        x_left = left + float(i) * col_w
        x_right = x_left + col_w
        geo[dom_eid] = (x_left, x_right, top, top + height)
    return geo


def _render_domain_lattice(
    *,
    domain_entity_ids: tuple[str, ...],
    w: float,
    h: float,
    labels: dict[str, str],
) -> list[str]:
    """
    Lightweight visual coordinate system: vertical domain columns + labels.
    """
    geo = _domain_column_geometry(domain_entity_ids=domain_entity_ids, w=w, h=h)
    parts: list[str] = []
    parts.append('<g id="domain_lattice" opacity="0.9">')
    parts.append(
        f'<rect x="0" y="0" width="{w:.2f}" height="{h:.2f}" fill="#0b0f14"/>'
    )
    for i, dom_eid in enumerate(domain_entity_ids):
        x_left, x_right, y_top, y_bottom = geo[dom_eid]
        # alternating subtle fill to make columns legible
        fill = "#0d1218" if (i % 2 == 0) else "#0b0f14"
        parts.append(
            f'<rect x="{x_left:.2f}" y="{y_top:.2f}" width="{(x_right-x_left):.2f}" height="{(y_bottom-y_top):.2f}" '
            f'fill="{fill}" opacity="0.85"/>'
        )
        parts.append(
            f'<line x1="{x_left:.2f}" y1="{y_top:.2f}" x2="{x_left:.2f}" y2="{y_bottom:.2f}" '
            f'stroke="#1d2a38" stroke-width="1" stroke-opacity="0.9"/>'
        )
        lab = html.escape((labels.get(dom_eid) or dom_eid).replace("domain:", "")[:26])
        parts.append(
            f'<text x="{(x_left+8.0):.2f}" y="{(y_top-10.0):.2f}" font-family="monospace" '
            f'font-size="11" fill="#e6eef7" fill-opacity="0.92">{lab}</text>'
        )

    # right boundary
    if domain_entity_ids:
        x_left, x_right, y_top, y_bottom = geo[domain_entity_ids[-1]]
        parts.append(
            f'<line x1="{x_right:.2f}" y1="{y_top:.2f}" x2="{x_right:.2f}" y2="{y_bottom:.2f}" '
            f'stroke="#1d2a38" stroke-width="1" stroke-opacity="0.9"/>'
        )
    parts.append("</g>")
    return parts


def _render_sankey_transfer(
    *,
    domain_entity_ids: tuple[str, ...],
    w: float,
    h: float,
    flows: list[tuple[str, str, float]],
) -> list[str]:
    """
    Draw transfer flows between domain columns as cubic Beziers.
    """
    geo = _domain_column_geometry(domain_entity_ids=domain_entity_ids, w=w, h=h)
    parts: list[str] = []
    parts.append('<g id="sankey_transfer" opacity="0.55">')

    if not flows:
        parts.append("</g>")
        return parts

    vmax = max((v for _, _, v in flows), default=1.0)
    vmax = vmax if vmax > 0.0 else 1.0

    # vertical bounds (match lattice)
    pad = 24.0
    y_top = pad + 30.0
    y_bottom = h - pad
    usable = max(1.0, (y_bottom - y_top) - 80.0)

    for (sd_eid, td_eid, v) in flows:
        if sd_eid not in geo or td_eid not in geo:
            continue

        sxL, sxR, syT, syB = geo[sd_eid]
        txL, txR, tyT, tyB = geo[td_eid]

        # anchor points: right edge of source, left edge of target
        x1 = sxR - 6.0
        x2 = txL + 6.0

        # stable per-flow y positions (avoid nondeterminism; avoid perfect overlap)
        hh = sha256_hex({"flow": f"{sd_eid}->{td_eid}"})
        a = int(hh[0:8], 16) / float(0xFFFFFFFF)
        b = int(hh[8:16], 16) / float(0xFFFFFFFF)
        y1 = syT + 40.0 + (a * usable)
        y2 = tyT + 40.0 + (b * usable)

        # control points for smooth curve
        dx = x2 - x1
        cx1 = x1 + dx * 0.35
        cx2 = x1 + dx * 0.65

        t = 1.0 + 10.0 * (float(v) / vmax)  # 1..11
        t = max(1.0, min(12.0, t))

        # simple deterministic stroke (dark, readable)
        stroke = "#111"
        d = (
            f"M {x1:.2f},{y1:.2f} "
            f"C {cx1:.2f},{y1:.2f} {cx2:.2f},{y2:.2f} {x2:.2f},{y2:.2f}"
        )
        parts.append(
            f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{t:.2f}" stroke-linecap="round" opacity="0.45"/>'
        )

    parts.append("</g>")
    return parts


def render_svg(scene: LumaSceneIR) -> RenderArtifact:
    pts = stable_layout_points(scene)

    # SVG canvas is centered; translate by +150 to keep positive coords.
    w, h = 1000, 650
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

    # --- Layer 1: Domain Lattice (coordinate system) ---
    domain_entity_ids: tuple[str, ...] = tuple()
    domain_labels: dict[str, str] = {}
    has_domain_lattice = any(
        p.kind.value == "domain_lattice" and p.failure_mode == "none" for p in scene.patterns
    )
    if has_domain_lattice and not isinstance(scene.entities, str):
        doms = [e for e in scene.entities if e.kind == "domain" and e.entity_id.startswith("domain:")]
        doms_s = sorted(
            doms,
            key=lambda e: (
                float(e.metrics.get("order", 0.0))
                if isinstance(e.metrics.get("order", 0.0), (int, float))
                else 0.0,
                e.entity_id,
            ),
        )
        domain_entity_ids = tuple(e.entity_id for e in doms_s)
        domain_labels = {e.entity_id: e.label for e in doms_s}

    if domain_entity_ids:
        lines.extend(
            _render_domain_lattice(
                domain_entity_ids=domain_entity_ids, w=float(w), h=float(h), labels=domain_labels
            )
        )
    else:
        # fallback background
        lines.append('<rect x="0" y="0" width="100%" height="100%" fill="#0b0f14"/>')

    # --- Layer 2: Sankey Transfer (cross-domain movement) ---
    has_sankey = any(
        p.kind.value == "sankey_transfer" and p.failure_mode == "none" for p in scene.patterns
    )
    if has_sankey and domain_entity_ids and not isinstance(scene.edges, str):
        agg: dict[tuple[str, str], float] = {}
        for e in scene.edges:
            if e.kind != "transfer":
                continue
            if not isinstance(e.resonance_magnitude, (int, float)):
                continue
            k = (e.source_id, e.target_id)
            agg[k] = agg.get(k, 0.0) + float(e.resonance_magnitude)

        flows = sorted(
            [(sd, td, v) for (sd, td), v in agg.items()],
            key=lambda t: (t[0], t[1], float(t[2])),
        )
        lines.extend(_render_sankey_transfer(domain_entity_ids=domain_entity_ids, w=float(w), h=float(h), flows=flows))

    # edges first
    if not isinstance(scene.edges, str):
        for e in sorted(scene.edges, key=lambda x: x.edge_id):
            # If sankey is active, avoid double-drawing transfer edges as straight lines.
            if has_sankey and domain_entity_ids and e.kind == "transfer":
                continue
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

from __future__ import annotations

import html
import math
from collections import defaultdict
from typing import Any, Dict, Mapping, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR
from .base import (
    alpha_from_uncertainty,
    domain_color,
    LayoutPoint,
    stable_layout_points,
    thickness_from_magnitude,
)

NC = NotComputable.VALUE.value


def _compute_lattice_cells(
    *,
    w: float,
    h: float,
    pad: float,
    domain_ids: Tuple[str, ...],
    subdomain_ids_by_domain: Mapping[str, Tuple[str, ...]],
) -> Dict[str, Dict[str, Tuple[float, float, float, float]]]:
    """
    Returns cell geometry:
      cells[domain_id]["__domain__"] = (xL,xR,yT,yB)
      cells[domain_id][subdomain_id] = (xL,xR,yT,yB) row box

    Deterministic mirror of the lattice render geometry.
    """
    top = pad + 30.0
    bottom = h - pad
    left = pad
    right = w - pad
    height = max(1.0, bottom - top)
    width = max(1.0, right - left)

    doms = list(domain_ids)
    n_dom = max(1, len(doms))
    col_w = width / float(n_dom)

    cells: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {}
    for i, dom_id in enumerate(doms):
        xL = left + float(i) * col_w
        xR = xL + col_w
        yT = top
        yB = top + height
        cells.setdefault(dom_id, {})
        cells[dom_id]["__domain__"] = (xL, xR, yT, yB)

        subs = list(subdomain_ids_by_domain.get(dom_id, ()))
        subs = sorted(subs)
        if subs:
            row_h = (height - 30.0) / max(1.0, float(len(subs)))
            for j, sid in enumerate(subs):
                syT = yT + 30.0 + float(j) * row_h
                syB = syT + row_h
                cells[dom_id][sid] = (xL, xR, syT, syB)

    return cells


def _place_motifs_in_lattice(scene: LumaSceneIR, *, w: float, h: float) -> Tuple[
    Mapping[str, LayoutPoint],
    Dict[str, Dict[str, Tuple[float, float, float, float]]],
]:
    """
    Deterministic motif placement:
    - motifs with attributes.domain_id/subdomain_id snap into cell centers
    - multiple motifs in same cell are arranged in a small deterministic grid

    Returns (positions_relative_to_center, cells_geometry).
    """
    if isinstance(scene.entities, str):
        return {}, {}

    pad = 18.0
    cx, cy = w / 2.0, h / 2.0

    domains = [e for e in scene.entities if e.kind == "domain"]
    subdomains = [e for e in scene.entities if e.kind == "subdomain"]

    def _order_key(e: Any) -> Tuple[float, str]:
        o = e.metrics.get("order")
        try:
            of = float(o) if isinstance(o, (int, float, str)) else 0.0
        except Exception:
            of = 0.0
        return (of, e.entity_id)

    domain_ids = tuple(e.entity_id for e in sorted(domains, key=_order_key))
    sub_by_dom: Dict[str, Tuple[str, ...]] = {}
    for sd in sorted(subdomains, key=_order_key):
        # subdomain entity ids are expected to be "subdomain:{dom}:{sub}"
        # domain id is inferred as "domain:{dom}"
        parts = sd.entity_id.split(":")
        if len(parts) >= 3 and parts[0] == "subdomain":
            dom = parts[1]
            dom_id = f"domain:{dom}"
            sub_by_dom.setdefault(dom_id, [])
            sub_by_dom[dom_id].append(sd.entity_id)
    sub_by_dom_t = {k: tuple(sorted(v)) for k, v in sub_by_dom.items()}

    cells = _compute_lattice_cells(
        w=w,
        h=h,
        pad=pad,
        domain_ids=domain_ids,
        subdomain_ids_by_domain=sub_by_dom_t,
    )

    motifs = sorted([e for e in scene.entities if e.kind == "motif"], key=lambda e: e.entity_id)

    buckets: Dict[Tuple[str, str], list[str]] = {}
    fallback: list[str] = []

    for m in motifs:
        attrs = dict(m.attributes) if isinstance(m.attributes, Mapping) else {}
        dom = attrs.get("domain_id")
        sub = attrs.get("subdomain_id")

        # light inference fallback: allow snapping via motif.domain if it matches a domain entity id
        if not isinstance(dom, str) and m.domain and m.domain != NC:
            guess = f"domain:{m.domain}"
            if guess in cells:
                dom = guess

        if isinstance(dom, str) and dom in cells:
            sub_key = sub if isinstance(sub, str) and sub in cells[dom] else "__domain__"
            buckets.setdefault((dom, sub_key), []).append(m.entity_id)
        else:
            fallback.append(m.entity_id)

    positions: Dict[str, LayoutPoint] = {}

    # place each bucket
    for (dom, cell_key), ids in sorted(buckets.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        ids = sorted(ids)
        xL, xR, yT, yB = cells[dom][cell_key]
        cell_cx = (xL + xR) / 2.0
        cell_cy = (yT + yB) / 2.0

        n = len(ids)
        if n == 1:
            positions[ids[0]] = LayoutPoint(x=cell_cx - cx, y=cell_cy - cy)
            continue

        cols = 1
        while cols * cols < n:
            cols += 1
        rows = (n + cols - 1) // cols

        dx = min(24.0, (xR - xL) / max(3.0, float(cols + 1)))
        dy = min(20.0, (yB - yT) / max(3.0, float(rows + 1)))

        start_x = cell_cx - dx * float(cols - 1) / 2.0
        start_y = cell_cy - dy * float(rows - 1) / 2.0

        for idx, mid in enumerate(ids):
            r = idx // cols
            c = idx % cols
            px = start_x + float(c) * dx
            py = start_y + float(r) * dy
            positions[mid] = LayoutPoint(x=px - cx, y=py - cy)

    # fallback motifs: place in circle layout (but only among themselves)
    if fallback:
        n = len(fallback)
        rot = 0.0
        r = 120.0
        for i, mid in enumerate(sorted(fallback)):
            theta = rot + (2.0 * math.pi * float(i) / max(1.0, float(n)))
            positions[mid] = LayoutPoint(x=r * math.cos(theta), y=r * math.sin(theta))

    return positions, cells


def render_svg(scene: LumaSceneIR) -> RenderArtifact:
    pts = dict(stable_layout_points(scene))

    # SVG canvas is centered; translate by +150 to keep positive coords.
    w, h = 360, 360
    cx, cy = w / 2.0, h / 2.0

    # If a domain lattice exists, snap motifs deterministically into domain/subdomain cells.
    lattice_present = any(
        (p.kind.value == "domain_lattice" and p.failure_mode == "none") for p in scene.patterns
    )
    layout_used = "circle_v0"
    lattice_cells: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {}
    if lattice_present and not isinstance(scene.entities, str):
        snapped, lattice_cells = _place_motifs_in_lattice(scene, w=w, h=h)
        if snapped:
            pts.update(dict(snapped))
            layout_used = "lattice_snap_v0"

    # Metadata must carry full provenance anchors.
    meta = {
        "luma": "LUMA",
        "scene_hash": scene.hash,
        "layout": layout_used,
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

    # lattice (if present)
    if layout_used == "lattice_snap_v0" and lattice_cells:
        pad = 18.0
        top = pad + 30.0
        lines.append(
            f'<text x="{pad:.2f}" y="{(top - 10.0):.2f}" font-family="monospace" '
            f'font-size="11" fill="#e6eef7" fill-opacity="0.86">Domain Lattice</text>'
        )
        for dom_id, subcells in sorted(lattice_cells.items(), key=lambda kv: kv[0]):
            xL, xR, yT, yB = subcells["__domain__"]
            lines.append(
                f'<rect x="{xL:.2f}" y="{yT:.2f}" width="{(xR-xL):.2f}" height="{(yB-yT):.2f}" '
                f'fill="none" stroke="#223" stroke-width="1.0" opacity="0.75"/>'
            )
            lines.append(
                f'<text x="{(xL + 6.0):.2f}" y="{(yT + 16.0):.2f}" font-family="monospace" '
                f'font-size="10" fill="#e6eef7" fill-opacity="0.82">{html.escape(dom_id)}</text>'
            )
            for sid, (sxL, sxR, syT, syB) in sorted(subcells.items(), key=lambda kv: kv[0]):
                if sid == "__domain__":
                    continue
                lines.append(
                    f'<rect x="{sxL:.2f}" y="{syT:.2f}" width="{(sxR-sxL):.2f}" height="{(syB-syT):.2f}" '
                    f'fill="none" stroke="#1a2430" stroke-width="1.0" opacity="0.55"/>'
                )

    # edges first
    if not isinstance(scene.edges, str):
        # deterministic curved routing + parallel separation
        pair_groups = defaultdict(list)
        for ed in scene.edges:
            if ed.source_id in pts and ed.target_id in pts:
                a, b = sorted([ed.source_id, ed.target_id])
                pair_groups[(a, b)].append(ed)

        for (a, b), group in sorted(pair_groups.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            group = sorted(group, key=lambda ed: (ed.kind, ed.source_id, ed.target_id, ed.edge_id))
            k = len(group)

            for idx, e in enumerate(group):
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

                # bend offset: symmetric around 0
                center = (k - 1) / 2.0
                bend = (float(idx) - center) * 14.0

                mx = (x1 + x2) / 2.0
                my = (y1 + y2) / 2.0
                dx = x2 - x1
                dy = y2 - y1
                norm = math.hypot(dx, dy)
                if norm < 1e-6:
                    cxp, cyp = mx, my
                else:
                    px = -dy / norm
                    py = dx / norm
                    cxp = mx + px * bend
                    cyp = my + py * bend

                d = f'M {x1:.2f},{y1:.2f} Q {cxp:.2f},{cyp:.2f} {x2:.2f},{y2:.2f}'
                lines.append(
                    f'<path d="{d}" fill="none" stroke="{col}" stroke-width="{sw:.2f}" '
                    f'opacity="{alpha:.3f}"/>'
                )

    # nodes
    if not isinstance(scene.entities, str):
        for ent in sorted(scene.entities, key=lambda x: x.entity_id):
            if layout_used == "lattice_snap_v0" and ent.kind in ("domain", "subdomain"):
                # These are represented as lattice frames/rows instead of circles.
                continue
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

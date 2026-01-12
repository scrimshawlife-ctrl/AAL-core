from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import html
import math
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Mapping, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable, PatternKind
from ..contracts.provenance import canonical_dumps, sha256_hex
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import AnimationPlan, LumaSceneIR, SceneEntity
from ..ideation.auto_lens import AutoLens, AutoLensConfig
from .svg_auto import AutoSvgConfig, SvgAutoRenderer
from .base import (
    alpha_from_uncertainty,
    domain_color,
    LayoutPoint,
    stable_layout_points,
    thickness_from_magnitude,
)

NC = NotComputable.VALUE.value
KNOWN_PATTERN_IDS = {
    "motif_graph/v1",
    "domain_lattice/v1",
    "temporal_braid/v1",
    "resonance_field/v1",
    "sankey_transfer/v1",
    "cluster_bloom/v1",
    "motif_domain_heatmap/v1",
    "transfer_chord/v1",
}


def _build_heatmap_plan(scene: LumaSceneIR) -> dict | None:
    if isinstance(scene.entities, str):
        return None

    motifs = [e for e in scene.entities if e.kind == "motif"]
    domains = [e for e in scene.entities if e.kind == "domain"]
    if not motifs or not domains:
        return None

    motifs_s = sorted(
        motifs,
        key=lambda e: (
            -float(e.metrics.get("salience", 0.0))
            if isinstance(e.metrics.get("salience"), (int, float))
            else 0.0,
            e.entity_id,
        ),
    )
    domains_s = sorted(domains, key=lambda e: e.domain or e.entity_id)

    domain_ids = [d.domain or d.entity_id for d in domains_s]
    domain_labels = {d.domain or d.entity_id: d.label for d in domains_s}

    cells: dict[str, dict[str, float]] = {}
    vmax = 0.0
    for m in motifs_s:
        sal = m.metrics.get("salience", 0.0)
        salience = float(sal) if isinstance(sal, (int, float)) else 0.0
        cells[m.entity_id] = {}
        for d in domain_ids:
            v = salience if m.domain == d else 0.0
            cells[m.entity_id][d] = v
            vmax = max(vmax, v)

    return {
        "layout": "motif_domain_heatmap_v0",
        "motifs": [
            {"id": m.entity_id, "label": m.label}
            for m in motifs_s
        ],
        "domains": [
            {"id": d_id, "label": domain_labels.get(d_id, d_id)}
            for d_id in domain_ids
        ],
        "cells": cells,
        "value_max": vmax if vmax > 0 else 1.0,
    }


def _render_motif_domain_heatmap(plan: dict, *, width: float, height: float) -> list[str]:
    pad = 14.0
    panel_w = 360.0
    x0 = width - pad - panel_w
    x1 = width - pad
    y0 = pad + 34.0
    y1 = height - pad

    motifs = plan["motifs"]
    domains = plan["domains"]
    cells = plan["cells"]
    vmax = float(plan.get("value_max", 1.0)) or 1.0

    n_rows = max(1, len(motifs))
    n_cols = max(1, len(domains))
    cell_w = (x1 - x0) / n_cols
    cell_h = (y1 - y0) / n_rows

    parts: list[str] = []
    parts.append('<g id="motif_domain_heatmap">')
    parts.append(
        f'<rect x="{x0:.2f}" y="{y0 - 28:.2f}" '
        f'width="{panel_w:.2f}" height="{(y1 - y0) + 28:.2f}" '
        'fill="none" stroke="#2c333a" stroke-width="1"/>'
    )
    parts.append(
        f'<text x="{x0 + 6:.2f}" y="{y0 - 10:.2f}" '
        'font-family="monospace" font-size="10" fill="#c2cad4" opacity="0.85">'
        "Motif×Domain Heatmap</text>"
    )

    for j, d in enumerate(domains):
        cx = x0 + j * cell_w + cell_w / 2
        label = html.escape(str(d["label"]))
        parts.append(
            f'<text x="{cx:.2f}" y="{y0 - 2:.2f}" text-anchor="middle" '
            'font-size="9" fill="#c2cad4" opacity="0.7">'
            f"{label}</text>"
        )

    for i, m in enumerate(motifs):
        ry = y0 + i * cell_h
        mlabel = html.escape(str(m["label"]))
        parts.append(
            f'<text x="{x0 - 6:.2f}" y="{ry + cell_h * 0.65:.2f}" '
            'text-anchor="end" font-size="9" fill="#c2cad4" opacity="0.75">'
            f"{mlabel}</text>"
        )
        row = cells.get(m["id"], {})
        for j, d in enumerate(domains):
            v = float(row.get(d["id"], 0.0))
            a = 0.05 + 0.85 * (v / vmax) if v > 0 else 0.05
            x = x0 + j * cell_w
            y = ry
            motif_id = html.escape(str(m["id"]))
            domain_id = html.escape(str(d["id"]))
            parts.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w:.2f}" '
                f'height="{cell_h:.2f}" fill="#dbe2ea" opacity="{a:.3f}" '
                f'data-heatmap="1" data-motif="{motif_id}" data-domain="{domain_id}"/>'
            )

    parts.append("</g>")
    return parts


def _build_chord_plan(scene: LumaSceneIR) -> dict | None:
    if isinstance(scene.entities, str) or isinstance(scene.edges, str):
        return None

    domains = [e for e in scene.entities if e.kind == "domain"]
    if not domains:
        return None
    domain_entities = sorted(domains, key=lambda e: e.entity_id)
    domain_ids = [d.entity_id for d in domain_entities]
    domain_labels = {d.entity_id: d.label for d in domain_entities}

    edges = [e for e in scene.edges if e.kind == "transfer"]
    if not edges:
        return None

    agg: dict[tuple[str, str], float] = {}
    vmax = 0.0
    for e in edges:
        if e.source_id not in domain_ids or e.target_id not in domain_ids:
            continue
        if not isinstance(e.resonance_magnitude, (int, float)):
            continue
        key = (e.source_id, e.target_id)
        agg[key] = agg.get(key, 0.0) + float(e.resonance_magnitude)
        vmax = max(vmax, agg[key])

    flows = [
        {"source_domain": src, "target_domain": tgt, "weight": float(w)}
        for (src, tgt), w in sorted(agg.items(), key=lambda kv: (kv[0][0], kv[0][1]))
    ]
    if not flows:
        return None

    return {
        "layout": "transfer_chord_v0",
        "domains": [
            {"id": d_id, "label": domain_labels.get(d_id, d_id)} for d_id in domain_ids
        ],
        "flows": flows,
        "weight_max": vmax if vmax > 0 else 1.0,
    }


def _render_transfer_chord(
    plan: dict, *, width: float, height: float, left_panel: float
) -> list[str]:
    pad = 18.0
    panel_w = max(260.0, left_panel - pad * 2)
    cx = pad + panel_w * 0.5
    cy = height * 0.5
    radius = min(panel_w, height) * 0.36

    domains = list(plan.get("domains", []))
    flows = list(plan.get("flows", []))
    vmax = float(plan.get("weight_max", 1.0)) or 1.0

    n = max(1, len(domains))
    angles = {}
    for i, d in enumerate(domains):
        theta = (2 * math.pi * i) / n - math.pi / 2
        angles[d["id"]] = theta

    def pt(d_id: str, r: float = radius) -> tuple[float, float]:
        t = angles[d_id]
        return (cx + r * math.cos(t), cy + r * math.sin(t))

    flow_map = {
        (f["source_domain"], f["target_domain"]): float(f["weight"]) for f in flows
    }

    parts: list[str] = []
    parts.append('<g id="transfer_chord" opacity="0.92">')
    parts.append(
        f'<text x="{cx - radius:.2f}" y="{cy - radius - 10:.2f}" '
        'font-family="monospace" font-size="10" fill="#c2cad4" opacity="0.85">'
        "Transfer Chord</text>"
    )
    parts.append(
        f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" '
        'fill="none" stroke="#2c333a" stroke-width="1" opacity="0.55"/>'
    )

    for d in domains:
        x, y = pt(d["id"], radius)
        parts.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.0" fill="#c2cad4" opacity="0.85"/>'
        )
        lx, ly = pt(d["id"], radius + 18)
        anchor = "middle"
        t = angles[d["id"]]
        if math.cos(t) > 0.35:
            anchor = "start"
        elif math.cos(t) < -0.35:
            anchor = "end"
        label = html.escape(str(d["label"]))
        parts.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}" '
            'font-family="monospace" font-size="9" fill="#c2cad4" opacity="0.75">'
            f"{label}</text>"
        )

    flows = sorted(flows, key=lambda f: (f["source_domain"], f["target_domain"]))
    for f in flows:
        sd = f["source_domain"]
        td = f["target_domain"]
        wgt = float(f["weight"])
        norm = wgt / vmax

        x1, y1 = pt(sd, radius)
        x2, y2 = pt(td, radius)

        reciprocal = (td, sd) in flow_map
        bend_sign = -1.0 if reciprocal and sd < td else 1.0

        mx, my = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        dx, dy = (x2 - x1), (y2 - y1)
        dist = math.hypot(dx, dy)
        if dist < 1e-6:
            continue
        px, py = (-dy / dist), (dx / dist)

        bend = bend_sign * min(radius * 0.55, 0.18 * dist + 40.0 * norm)
        cx1, cy1 = mx + px * bend, my + py * bend

        thickness = 1.0 + 7.0 * norm
        opacity = 0.12 + 0.75 * norm

        dpath = f"M {x1:.2f},{y1:.2f} Q {cx1:.2f},{cy1:.2f} {x2:.2f},{y2:.2f}"
        src_label = html.escape(str(sd))
        tgt_label = html.escape(str(td))
        parts.append(
            f'<path d="{dpath}" fill="none" stroke="#c2cad4" '
            f'stroke-width="{thickness:.2f}" opacity="{opacity:.3f}" '
            f'data-edge="transfer" data-src="{src_label}" data-tgt="{tgt_label}"/>'
        )

    parts.append("</g>")
    return parts


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


def _render_sankey_domain_lattice(
    *,
    domain_entity_ids: tuple[str, ...],
    w: float,
    h: float,
    labels: dict[str, str],
) -> list[str]:
    """
    Lightweight visual coordinate system: vertical domain columns + labels.
    Specifically for sankey transfer visualization.
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
    pts = dict(stable_layout_points(scene))
    heatmap_plan = None
    chord_plan = None
    auto_plan = None
    auto_used = False
    requested: list[str] = []
    if not isinstance(scene.patterns, str):
        requested = [p.pattern_id for p in scene.patterns]
        for p in scene.patterns:
            if p.kind == PatternKind.MOTIF_DOMAIN_HEATMAP:
                heatmap_plan = _build_heatmap_plan(scene)
            if p.kind == PatternKind.TRANSFER_CHORD:
                chord_plan = _build_chord_plan(scene)
    unknown = sorted([pid for pid in requested if pid not in KNOWN_PATTERN_IDS])

    base_w, base_h = 360.0, 360.0
    left_panel = 380.0 if chord_plan else 0.0
    right_panel = 380.0 if heatmap_plan else 0.0
    w, h = base_w + left_panel + right_panel, base_h
    cx, cy = left_panel + base_w / 2.0, base_h / 2.0

    if (not requested) or unknown:
        lens = AutoLens()
        auto_plan = lens.plan(scene, AutoLensConfig())
        auto_used = True

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
            _render_sankey_domain_lattice(
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

    # Temporal braid band (bottom panel) if timeline present.
    lines.extend(_render_temporal_braid(scene=scene, w=float(w), h=float(h)))

    # edges first
    if not isinstance(scene.edges, str):
        # deterministic curved routing + parallel separation
        pair_groups = defaultdict(list)
        for ed in scene.edges:
            # If sankey is active, avoid double-drawing transfer edges
            if has_sankey and domain_entity_ids and ed.kind == "transfer":
                continue
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

    if chord_plan and chord_plan.get("layout") == "transfer_chord_v0":
        lines.extend(
            _render_transfer_chord(
                chord_plan, width=w, height=h, left_panel=left_panel
            )
        )

    if heatmap_plan and heatmap_plan.get("layout") == "motif_domain_heatmap_v0":
        lines.extend(_render_motif_domain_heatmap(heatmap_plan, width=w, height=h))

    if auto_plan is not None and auto_used:
        lines.append('<g id="auto_view_fallback" opacity="0.95">')
        lines.append(
            f'<text x="{14.0:.2f}" y="{18.0:.2f}" opacity="0.7">'
            f"Auto-Lens fallback: {html.escape(auto_plan.view_id)}</text>"
        )
        auto = SvgAutoRenderer()
        cfg = AutoSvgConfig(width=w, height=h, padding=14.0, font_size=10)
        lines.extend(auto.render_into_parts(cfg, auto_plan))
        lines.append("</g>")

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


def _wants_domain_lattice(scene: LumaSceneIR) -> bool:
    for p in scene.patterns:
        if p.kind == PatternKind.DOMAIN_LATTICE and p.failure_mode == "none":
            return True
    return False


def _domain_and_subdomain_entities(
    scene: LumaSceneIR,
) -> Tuple[Tuple[SceneEntity, ...], Tuple[SceneEntity, ...]]:
    if isinstance(scene.entities, str):
        return (tuple(), tuple())
    domains: List[SceneEntity] = []
    subs: List[SceneEntity] = []
    for e in scene.entities:
        if e.kind == "domain":
            domains.append(e)
        elif e.kind == "subdomain":
            subs.append(e)
    return (tuple(domains), tuple(subs))


def _render_domain_lattice(*, scene: LumaSceneIR, w: int, h: int) -> List[str]:
    """
    Render a deterministic domain/subdomain lattice as a background "map".

    Ordering semantics:
    - Prefer `scene.constraints["domain_order"]` / `scene.constraints["subdomain_order"]` when present.
    - Otherwise sort deterministically (domains by id; subdomains by rank then id when rank is present).
    """

    domains, subdomains = _domain_and_subdomain_entities(scene)
    if not domains:
        return []

    constraints = scene.constraints or {}
    domain_order = constraints.get("domain_order")
    subdomain_order = constraints.get("subdomain_order")

    domains_by_id: Dict[str, SceneEntity] = {d.entity_id: d for d in domains}
    all_domain_ids = sorted(domains_by_id.keys())

    domain_ids: List[str] = []
    if isinstance(domain_order, list) and domain_order:
        for did in domain_order:
            did_s = str(did)
            if did_s in domains_by_id and did_s not in domain_ids:
                domain_ids.append(did_s)
        for did in all_domain_ids:
            if did not in domain_ids:
                domain_ids.append(did)
    else:
        domain_ids = all_domain_ids

    # Group subdomains by owning domain_id.
    subs_by_domain: Dict[str, List[SceneEntity]] = {did: [] for did in domain_ids}
    for sd in subdomains:
        dom_id = _subdomain_domain_id(sd)
        subs_by_domain.setdefault(dom_id, []).append(sd)

    ordered_sub_ids: Dict[str, List[str]] = {}
    for dom_id, subs in subs_by_domain.items():
        subs_by_id = {s.entity_id: s for s in subs}
        all_sub_ids = sorted(subs_by_id.keys())
        ids: List[str] = []

        forced = None
        if isinstance(subdomain_order, Mapping):
            forced = subdomain_order.get(dom_id)
        if isinstance(forced, list) and forced:
            for sid in forced:
                sid_s = str(sid)
                if sid_s in subs_by_id and sid_s not in ids:
                    ids.append(sid_s)
            for sid in all_sub_ids:
                if sid not in ids:
                    ids.append(sid)
        else:
            def _k(sid: str) -> Tuple[int, str]:
                e = subs_by_id[sid]
                r = e.metrics.get("rank") if isinstance(e.metrics, Mapping) else None
                try:
                    r_int = int(r) if r is not None else 10**9
                except Exception:
                    r_int = 10**9
                return (r_int, sid)

            ids = sorted(all_sub_ids, key=_k)

        ordered_sub_ids[dom_id] = ids

    # Deterministic geometry.
    pad = 14
    top = pad + 30
    bottom = h - pad
    left = pad
    right = w - pad
    height = max(1.0, float(bottom - top))
    width = max(1.0, float(right - left))

    n_dom = max(1, len(domain_ids))
    col_w = width / float(n_dom)

    parts: List[str] = []
    parts.append('<g id="domain_lattice" opacity="0.18">')

    for i, dom_id in enumerate(domain_ids):
        x = float(left) + float(i) * col_w
        y = float(top)
        parts.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{col_w:.2f}" height="{height:.2f}" '
            f'fill="none" stroke="#e6eef7" stroke-width="1"/>'
        )

        dom_label = html.escape((domains_by_id.get(dom_id).label if dom_id in domains_by_id else dom_id)[:48])
        parts.append(
            f'<text x="{x + 8.0:.2f}" y="{y + 18.0:.2f}" font-family="monospace" '
            f'font-size="10" fill="#e6eef7" fill-opacity="0.90">{dom_label}</text>'
        )

        subs = list(ordered_sub_ids.get(dom_id, ()))
        # compile already orders, but keep deterministic defense
        # (no mutation of the intended order if it's already stable)
        if subs and not (isinstance(subdomain_order, Mapping) and isinstance(subdomain_order.get(dom_id), list)):
            subs = list(subs)

        if subs:
            row_h = (height - 30.0) / float(max(1, len(subs)))
            for j, sid in enumerate(subs):
                sy = y + 30.0 + float(j) * row_h
                parts.append(
                    f'<rect x="{x:.2f}" y="{sy:.2f}" width="{col_w:.2f}" height="{row_h:.2f}" '
                    f'fill="none" stroke="#e6eef7" stroke-width="0.6"/>'
                )
                slabel = html.escape(_subdomain_label(scene=scene, subdomain_id=sid)[:48])
                parts.append(
                    f'<text x="{x + 10.0:.2f}" y="{sy + 16.0:.2f}" font-family="monospace" '
                    f'font-size="9" fill="#e6eef7" fill-opacity="0.85">{slabel}</text>'
                )

    parts.append("</g>")
    return parts


def _subdomain_domain_id(sd: SceneEntity) -> str:
    """
    Best-effort mapping of a subdomain entity to its owning domain_id.

    Canonical: subdomain.domain == domain_id (as produced by DomainLatticePattern).
    Back-compat: parse entity_id shaped like "subdomain:<domain>:<sub>".
    """

    if sd.domain and sd.domain != NC:
        return sd.domain
    eid = sd.entity_id or ""
    if eid.startswith("subdomain:"):
        parts = eid.split(":", 2)
        if len(parts) >= 2 and parts[1]:
            return parts[1]
    return "not_computable"


def _subdomain_label(*, scene: LumaSceneIR, subdomain_id: str) -> str:
    if isinstance(scene.entities, str):
        return subdomain_id
    for e in scene.entities:
        if e.entity_id == subdomain_id:
            return e.label or subdomain_id
    return subdomain_id


@dataclass
class SvgRenderConfig:
    """Configuration for SVG static renderer."""
    width: int = 1200
    height: int = 800


class SvgStaticRenderer:
    """Static SVG renderer for LumaSceneIR."""

    def render(self, scene: LumaSceneIR, config: SvgRenderConfig | None = None) -> RenderArtifact:
        """Render a scene to SVG artifact.

        Note: config parameter is accepted for API compatibility but currently unused.
        Width/height are determined by render_svg implementation.
        """
        return render_svg(scene)

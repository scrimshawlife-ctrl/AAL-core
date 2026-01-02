from __future__ import annotations

import html
import math
from typing import Dict, List, Mapping, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable, PatternKind
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR, SceneEntity
from ..ideation.auto_lens import AutoLens, AutoLensConfig
from .svg_auto import AutoSvgConfig, SvgAutoRenderer
from .base import (
    alpha_from_uncertainty,
    domain_color,
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


def render_svg(scene: LumaSceneIR) -> RenderArtifact:
    pts = stable_layout_points(scene)
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

    # Lattice background layer (deterministic, additive).
    if _wants_domain_lattice(scene):
        lines.extend(_render_domain_lattice(scene=scene, w=w, h=h))

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

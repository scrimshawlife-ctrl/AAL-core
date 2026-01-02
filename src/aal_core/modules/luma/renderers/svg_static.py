from __future__ import annotations

import html

from typing import Dict, List, Mapping, Tuple

from ..contracts.enums import ArtifactKind, LumaMode, NotComputable, PatternKind
from ..contracts.provenance import canonical_dumps
from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR, SceneEntity
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

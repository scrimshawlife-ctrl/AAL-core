from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List
import math

from ..contracts.auto_view_ir import AutoViewPlan


@dataclass(frozen=True)
class AutoSvgConfig:
    width: float
    height: float
    padding: float = 14.0
    font_size: int = 10
    font_family: str = "monospace"


class SvgAutoRenderer:
    renderer_id = "luma.svg_auto"
    renderer_version = "0.1.0"

    def render_into_parts(self, cfg: AutoSvgConfig, plan: AutoViewPlan) -> List[str]:
        parts: List[str] = []
        kind = (plan.layout or {}).get("layout_kind", "")

        if plan.view_id.startswith("auto.matrix") or kind == "incidence":
            parts.extend(self._render_matrix(cfg, plan.layout))
        elif plan.view_id.startswith("auto.flow") or kind == "domain_flow":
            preferred = (plan.layout or {}).get("preferred_flow_view", "chord")
            if preferred == "sankey":
                parts.extend(self._render_flow_sankeyish(cfg, plan.layout))
            else:
                parts.extend(self._render_flow_chordish(cfg, plan.layout))
        elif plan.view_id.startswith("auto.timeline") or kind == "timeline_events":
            parts.extend(self._render_timeline(cfg, plan.layout))
        elif plan.view_id.startswith("auto.graph") or kind == "circle":
            parts.extend(self._render_graph(cfg, plan.layout))
        else:
            parts.append(
                '<g id="auto_view_empty"><text x="20" y="40" '
                'opacity="0.7">AutoView: no renderable primitives</text></g>'
            )
        return parts

    def _render_matrix(self, cfg: AutoSvgConfig, layout: Dict[str, Any]) -> List[str]:
        w, h = cfg.width, cfg.height
        pad = cfg.padding
        x0, y0 = pad + 40, pad + 60
        x1, y1 = w - pad - 40, h - pad - 40

        rows = list(layout.get("rows", []))[:32]
        cols = list(layout.get("cols", []))[:16]
        cells = layout.get("cells", {}) or {}
        vmax = float(layout.get("value_max", 1.0)) or 1.0

        n_r = max(1, len(rows))
        n_c = max(1, len(cols))
        cw = (x1 - x0) / n_c
        ch = (y1 - y0) / n_r

        parts = ['<g id="auto_view_matrix">']
        parts.append(
            f'<text x="{x0:.2f}" y="{y0-20:.2f}" '
            'opacity="0.85">AutoView: Matrix</text>'
        )

        for j, c in enumerate(cols):
            cx = x0 + j * cw + cw / 2
            parts.append(
                f'<text x="{cx:.2f}" y="{y0-6:.2f}" text-anchor="middle" '
                f'font-size="{cfg.font_size-2}" opacity="0.65">{self._esc(c)}</text>'
            )

        for i, r in enumerate(rows):
            ry = y0 + i * ch
            parts.append(
                f'<text x="{x0-6:.2f}" y="{ry+ch*0.65:.2f}" text-anchor="end" '
                f'font-size="{cfg.font_size-2}" opacity="0.65">{self._esc(r)}</text>'
            )
            row = cells.get(r, {})
            for j, c in enumerate(cols):
                v = float(row.get(c, 0.0))
                a = 0.05 + 0.85 * (v / vmax) if v > 0 else 0.05
                x = x0 + j * cw
                y = ry
                parts.append(
                    f'<rect x="{x:.2f}" y="{y:.2f}" width="{cw:.2f}" '
                    f'height="{ch:.2f}" fill="#000" opacity="{a:.3f}" '
                    f'data-heatmap="1" data-motif="{self._esc(r)}" '
                    f'data-domain="{self._esc(c)}"/>'
                )

        parts.append('</g>')
        return parts

    def _render_flow_chordish(self, cfg: AutoSvgConfig, layout: Dict[str, Any]) -> List[str]:
        w, h = cfg.width, cfg.height
        pad = cfg.padding
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.32

        domains = list(layout.get("domains", []))
        flows = list(layout.get("flows", []))
        vmax = float(layout.get("weight_max", 1.0)) or 1.0

        n = max(1, len(domains))
        angles = {}
        for i, d in enumerate(domains):
            angles[d] = (2 * math.pi * i) / n - math.pi / 2

        def pt(d: str, r: float = radius) -> tuple[float, float]:
            t = angles[d]
            return (cx + r * math.cos(t), cy + r * math.sin(t))

        parts = ['<g id="auto_view_flow">']
        parts.append(
            f'<text x="{cx-radius:.2f}" y="{cy-radius-12:.2f}" '
            'opacity="0.85">AutoView: Flow (Chordish)</text>'
        )
        parts.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{radius:.2f}" '
            'fill="none" stroke="#000" stroke-width="1" opacity="0.35"/>'
        )

        for d in domains:
            x, y = pt(d, radius)
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#000" opacity="0.8"/>'
            )

        flows = sorted(flows, key=lambda f: (f["source_domain"], f["target_domain"]))
        for f in flows:
            sd, td = f["source_domain"], f["target_domain"]
            wgt = float(f["weight"])
            norm = wgt / vmax
            x1, y1 = pt(sd, radius)
            x2, y2 = pt(td, radius)
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            dx, dy = x2 - x1, y2 - y1
            dist = math.hypot(dx, dy)
            if dist < 1e-6:
                continue
            px, py = (-dy / dist), (dx / dist)
            bend = min(radius * 0.55, 0.18 * dist + 40.0 * norm)
            cx1, cy1 = mx + px * bend, my + py * bend

            thickness = 1.0 + 7.0 * norm
            opacity = 0.12 + 0.75 * norm
            dpath = (
                f'M {x1:.2f},{y1:.2f} Q {cx1:.2f},{cy1:.2f} {x2:.2f},{y2:.2f}'
            )
            parts.append(
                f'<path d="{dpath}" fill="none" stroke="#000" '
                f'stroke-width="{thickness:.2f}" opacity="{opacity:.3f}" '
                f'data-edge="transfer" data-src="{self._esc(sd)}" '
                f'data-tgt="{self._esc(td)}"/>'
            )

        parts.append('</g>')
        return parts

    def _render_flow_sankeyish(self, cfg: AutoSvgConfig, layout: Dict[str, Any]) -> List[str]:
        w, h = cfg.width, cfg.height
        pad = cfg.padding
        x0, x1 = pad + 60, w - pad - 60
        y0, y1 = pad + 80, h - pad - 60

        domains = list(layout.get("domains", []))
        flows = list(layout.get("flows", []))
        vmax = float(layout.get("weight_max", 1.0)) or 1.0

        n = max(1, len(domains))
        col_w = (x1 - x0) / n
        dom_x = {d: (x0 + i * col_w + col_w / 2) for i, d in enumerate(domains)}

        parts = ['<g id="auto_view_flow_sankey">']
        parts.append(
            f'<text x="{x0:.2f}" y="{y0-18:.2f}" '
            'opacity="0.85">AutoView: Flow (Sankeyish)</text>'
        )

        for d in domains:
            x = dom_x[d]
            parts.append(
                f'<circle cx="{x:.2f}" cy="{(y0+y1)/2:.2f}" r="4" '
                'fill="#000" opacity="0.8"/>'
            )

        flows = sorted(flows, key=lambda f: (f["source_domain"], f["target_domain"]))
        for i, f in enumerate(flows):
            sd, td = f["source_domain"], f["target_domain"]
            wgt = float(f["weight"])
            norm = wgt / vmax
            x1p, x2p = dom_x[sd], dom_x[td]
            ymid = y0 + (i + 1) * (y1 - y0) / (len(flows) + 1)
            thickness = 1.0 + 10.0 * norm
            opacity = 0.12 + 0.75 * norm
            c1x, c2x = (x1p * 0.7 + x2p * 0.3), (x1p * 0.3 + x2p * 0.7)
            dpath = (
                f'M {x1p:.2f},{ymid:.2f} C {c1x:.2f},{ymid:.2f} '
                f'{c2x:.2f},{ymid:.2f} {x2p:.2f},{ymid:.2f}'
            )
            parts.append(
                f'<path d="{dpath}" fill="none" stroke="#000" '
                f'stroke-width="{thickness:.2f}" opacity="{opacity:.3f}" '
                f'data-edge="transfer" data-src="{self._esc(sd)}" '
                f'data-tgt="{self._esc(td)}"/>'
            )

        parts.append('</g>')
        return parts

    def _render_timeline(self, cfg: AutoSvgConfig, layout: Dict[str, Any]) -> List[str]:
        w, h = cfg.width, cfg.height
        pad = cfg.padding
        x0, x1 = pad + 60, w - pad - 60
        y = pad + 120

        events = list(layout.get("events", []))[:64]
        parts = ['<g id="auto_view_timeline">']
        parts.append(
            f'<text x="{x0:.2f}" y="{y-40:.2f}" '
            'opacity="0.85">AutoView: Timeline</text>'
        )
        parts.append(
            f'<line x1="{x0:.2f}" y1="{y:.2f}" x2="{x1:.2f}" y2="{y:.2f}" '
            'stroke="#000" opacity="0.35"/>'
        )

        n = max(1, len(events))
        for i, ev in enumerate(events):
            x = x0 + (x1 - x0) * (i / (n - 1)) if n > 1 else (x0 + x1) / 2
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#000" '
                f'opacity="0.8" data-entity="{self._esc(ev.get("id", ""))}"/>'
            )
            ts = ev.get("timestamp", "")
            parts.append(
                f'<text x="{x:.2f}" y="{y+18:.2f}" text-anchor="middle" '
                f'font-size="{cfg.font_size-2}" opacity="0.65">{self._esc(ts)[:18]}</text>'
            )

        parts.append('</g>')
        return parts

    def _render_graph(self, cfg: AutoSvgConfig, layout: Dict[str, Any]) -> List[str]:
        w, h = cfg.width, cfg.height
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.33

        nodes = list(layout.get("nodes", []))[:32]
        edges = list(layout.get("edges", []))[:128]

        pos = {}
        for n in nodes:
            mid = n["id"]
            t = float(n.get("theta", 0.0))
            pos[mid] = (cx + radius * math.cos(t), cy + radius * math.sin(t))

        parts = ['<g id="auto_view_graph">']
        parts.append(
            f'<text x="{cx-radius:.2f}" y="{cy-radius-12:.2f}" '
            'opacity="0.85">AutoView: Graph</text>'
        )

        for ed in edges:
            a, b = ed["source"], ed["target"]
            if a not in pos or b not in pos:
                continue
            x1, y1 = pos[a]
            x2, y2 = pos[b]
            wgt = float(ed.get("weight", 0.0))
            thickness = 1.0 + 6.0 * max(0.0, min(1.0, wgt))
            opacity = 0.15 + 0.7 * max(0.0, min(1.0, wgt))
            parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="#000" stroke-width="{thickness:.2f}" opacity="{opacity:.3f}"/>'
            )

        for mid, (x, y) in sorted(pos.items(), key=lambda kv: kv[0]):
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="#000" '
                f'opacity="0.85" data-entity="{self._esc(mid)}"/>'
            )
            parts.append(
                f'<text x="{x:.2f}" y="{y-10:.2f}" text-anchor="middle" '
                f'font-size="{cfg.font_size-2}" opacity="0.70">{self._esc(mid)}</text>'
            )

        parts.append('</g>')
        return parts

    def _esc(self, s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

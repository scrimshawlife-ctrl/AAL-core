from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import hashlib

from ..contracts.render_artifact import RenderArtifact
from ..contracts.scene_ir import LumaSceneIR
from ..pipeline.validate_scene import validate_scene


@dataclass(frozen=True)
class SvgRenderConfig:
    width: int = 1200
    height: int = 800
    padding: int = 60
    node_radius: int = 10
    font_family: str = "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto"
    font_size: int = 12


class SvgStaticRenderer:
    renderer_id = "luma.svg_static"
    renderer_version = "0.1.0"

    def render(self, scene: LumaSceneIR, config: SvgRenderConfig | None = None) -> RenderArtifact:
        validate_scene(scene)
        cfg = config or SvgRenderConfig()

        # deterministic ordering
        motifs = [e for e in scene.entities if e.entity_type == "motif"]
        motifs = sorted(motifs, key=lambda e: e.entity_id)

        # simple deterministic circular layout (force-directed later; this is stable + testable)
        positions = self._circle_layout(motifs, cfg)

        # edges filtered for motif graph semantics
        edges = [ed for ed in scene.edges if ed.edge_type in ("resonance", "synch")]
        edges = sorted(edges, key=lambda ed: (ed.edge_type, ed.source, ed.target, float(ed.weight)))

        svg = self._build_svg(scene, cfg, positions, edges)
        payload = svg.encode("utf-8")
        bytes_sha = hashlib.sha256(payload).hexdigest()

        scene_hash = scene.stable_hash()
        artifact_id = f"{scene.scene_id}:{scene_hash[:12]}:{self.renderer_id}"

        return RenderArtifact(
            artifact_id=artifact_id,
            artifact_type="svg",
            scene_hash=scene_hash,
            renderer_id=self.renderer_id,
            renderer_version=self.renderer_version,
            bytes_sha256=bytes_sha,
            media_mime="image/svg+xml",
            payload_bytes=payload,
            provenance={
                "scene_provenance": scene.provenance,
                "constraints": scene.constraints,
                "seed": scene.seed,
                "renderer": {"id": self.renderer_id, "version": self.renderer_version},
            },
            meta={"width": cfg.width, "height": cfg.height, "layout": "circle_v0"},
            warnings=None,
        )

    def _circle_layout(self, motifs, cfg: SvgRenderConfig) -> Dict[str, Tuple[float, float]]:
        import math

        cx, cy = cfg.width / 2, cfg.height / 2
        r = min(cfg.width, cfg.height) / 2 - cfg.padding
        n = max(1, len(motifs))
        pos: Dict[str, Tuple[float, float]] = {}
        for i, e in enumerate(motifs):
            theta = (2 * math.pi * i) / n
            x = cx + r * math.cos(theta)
            y = cy + r * math.sin(theta)
            pos[e.entity_id] = (x, y)
        return pos

    def _build_svg(
        self,
        scene: LumaSceneIR,
        cfg: SvgRenderConfig,
        positions: Dict[str, Tuple[float, float]],
        edges,
    ) -> str:
        # Build deterministic SVG (no random ids)
        w, h = cfg.width, cfg.height
        title = f"LUMA: {scene.scene_id}"

        def esc(s: str) -> str:
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
            )

        # background + legend space
        parts: List[str] = []
        parts.append(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
        )
        parts.append(f'<rect x="0" y="0" width="{w}" height="{h}" fill="white"/>')
        parts.append(
            f'<text x="{cfg.padding}" y="{cfg.padding-20}" font-family="{cfg.font_family}" font-size="{cfg.font_size+4}">{esc(title)}</text>'
        )
        parts.append(
            f'<text x="{cfg.padding}" y="{cfg.padding}" font-family="{cfg.font_family}" font-size="{cfg.font_size}" opacity="0.7">scene_hash={scene.stable_hash()[:16]}…</text>'
        )

        # edges
        for ed in edges:
            if ed.source not in positions or ed.target not in positions:
                continue
            x1, y1 = positions[ed.source]
            x2, y2 = positions[ed.target]
            # thickness maps to weight (bounded)
            thickness = max(1.0, min(8.0, 1.0 + 7.0 * float(ed.weight)))
            opacity = max(0.15, min(0.9, 0.15 + 0.75 * float(ed.weight)))
            stroke = "#111" if ed.edge_type == "resonance" else "#444"
            parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{stroke}" stroke-width="{thickness:.2f}" opacity="{opacity:.3f}"/>'
            )

        # nodes + labels
        for eid, (x, y) in sorted(positions.items(), key=lambda kv: kv[0]):
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{cfg.node_radius}" fill="#000"/>')
            parts.append(
                f'<text x="{x + cfg.node_radius + 6:.2f}" y="{y + cfg.font_size/2:.2f}" '
                f'font-family="{cfg.font_family}" font-size="{cfg.font_size}" opacity="0.85">{esc(eid)}</text>'
            )

        # footer provenance stamp (light)
        parts.append(
            f'<text x="{cfg.padding}" y="{h - cfg.padding/2:.2f}" font-family="{cfg.font_family}" font-size="{cfg.font_size-2}" opacity="0.55">'
            f"renderer={self.renderer_id}@{self.renderer_version}"
            f"</text>"
        )

        parts.append("</svg>")
        return "\n".join(parts)

import type { BaseItem } from "../types/vizir";
import type { GlyphSpec } from "./types";

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function polar(cx: number, cy: number, r: number, a: number): { x: number; y: number } {
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

const ANG = [
  -Math.PI / 2,
  -Math.PI / 6,
  Math.PI / 6,
  Math.PI / 2,
  (5 * Math.PI) / 6,
  (7 * Math.PI) / 6
];

export function resonanceGlyphItems(spec: GlyphSpec): BaseItem[] {
  const R = clamp01(spec.channels.R);
  const S = clamp01(spec.channels.S);
  const N = clamp01(spec.channels.N);
  const K = clamp01(spec.channels.K);

  const C = (spec.channels.C || []).slice(0, 6).map(clamp01);
  while (C.length < 6) C.push(0);

  const cx = spec.cx;
  const cy = spec.cy;
  const size = Math.max(4, spec.size);

  const ringW = lerp(1.2, 4.2, R);
  const ringR = size;

  const coreOp = lerp(0.08, 0.4, K);

  const items: BaseItem[] = [];

  items.push({
    id: `${spec.id}.ring`,
    type: "circle",
    style: { stroke: "rgba(0,0,0,0.55)", stroke_w: ringW, fill: "none" },
    geom: { cx, cy, r: ringR },
    data: { kind: "glyph_ring", ...spec.data }
  });

  items.push({
    id: `${spec.id}.core`,
    type: "circle",
    style: { fill: `rgba(0,0,0,${coreOp.toFixed(3)})`, stroke: "none" },
    geom: { cx, cy, r: ringR * 0.45 },
    data: { kind: "glyph_core", ...spec.data }
  });

  for (let i = 0; i < 6; i += 1) {
    const v = C[i];
    const a = ANG[i];

    const r0 = ringR * 0.52;
    const r1 = ringR * lerp(0.6, 1.05, v);

    const p0 = polar(cx, cy, r0, a);
    const p1 = polar(cx, cy, r1, a);

    items.push({
      id: `${spec.id}.spoke.${i}`,
      type: "line",
      style: {
        stroke: "rgba(0,0,0,0.55)",
        stroke_w: lerp(1.0, 2.8, v),
        opacity: lerp(0.25, 0.95, v)
      },
      geom: { x1: p0.x, y1: p0.y, x2: p1.x, y2: p1.y },
      data: { kind: "glyph_spoke", i, v, ...spec.data }
    });
  }

  const dots = Math.round(lerp(0, 6, S));
  for (let d = 0; d < dots; d += 1) {
    const rr = ringR * lerp(0.65, 1.15, (d + 1) / 6);
    const p = polar(cx, cy, rr, -Math.PI / 2);
    items.push({
      id: `${spec.id}.dot.${d}`,
      type: "circle",
      style: { fill: "rgba(0,0,0,0.55)", stroke: "none", opacity: 0.65 },
      geom: { cx: p.x, cy: p.y, r: 1.6 },
      data: { kind: "glyph_dot", d, ...spec.data }
    });
  }

  const notchLen = lerp(0, ringR * 0.55, N);
  if (notchLen > 0.5) {
    const a = Math.PI;
    const pA = polar(cx, cy, ringR, a);
    const pB = polar(cx, cy, ringR - notchLen, a);
    items.push({
      id: `${spec.id}.notch`,
      type: "line",
      style: { stroke: "rgba(0,0,0,0.70)", stroke_w: 2.0, opacity: lerp(0.2, 0.9, N) },
      geom: { x1: pA.x, y1: pA.y, x2: pB.x, y2: pB.y },
      data: { kind: "glyph_notch", novelty: N, ...spec.data }
    });
  }

  if (spec.label) {
    items.push({
      id: `${spec.id}.label`,
      type: "text",
      style: {
        font_family: "ui-monospace, Menlo, Consolas, monospace",
        font_size: 11,
        fill: "rgba(0,0,0,0.65)",
        text_anchor: "start"
      },
      geom: { x: cx + ringR + 6, y: cy + 4, text: spec.label },
      data: { kind: "glyph_label", ...spec.data }
    });
  }

  return items;
}

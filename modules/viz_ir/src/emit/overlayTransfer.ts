import type { Layer, BaseItem, VizIR, Style } from "../types/vizir";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { roundN } from "../utils/round";

type XY = { x: number; y: number };

export type TransferEdge = {
  edge_type?: string;
  source: string;
  target: string;
  weight?: number | null;
  attributes?: Record<string, unknown>;
};

export type TransferOverlayInput = {
  edges?: TransferEdge[];
  scene?: { edges: TransferEdge[]; [k: string]: unknown };
  pos: Record<string, XY>;
  provenance?: Record<string, unknown>;
};

export type TransferOverlayOptions = {
  canvas_w?: number;
  canvas_h?: number;
  title?: string;
  curvature?: number;
  bend?: "left" | "right" | "auto";
  min_opacity?: number;
  max_opacity?: number;
  min_stroke_w?: number;
  max_stroke_w?: number;
  min_abs_weight?: number;
};

function clamp(x: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, x));
}

function stableKey(e: TransferEdge): string {
  const t = e.edge_type ?? "transfer";
  return `${t}|${e.source}|${e.target}`;
}

function edgeStyle(opacity: number, strokeW: number): Style {
  return {
    stroke: "rgba(0,0,0,0.85)",
    fill: "none",
    opacity,
    stroke_w: strokeW
  };
}

function norm2(x: number, y: number): number {
  return Math.sqrt(x * x + y * y);
}

function bendSign(source: string, target: string, mode: "left" | "right" | "auto"): number {
  if (mode === "left") return -1;
  if (mode === "right") return 1;

  const s = source + "|" + target;
  let h = 0;
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0;
  return (h % 2 === 0) ? 1 : -1;
}

function quadPath(s: XY, t: XY, curvatureFrac: number, sign: number): { d: string; cx: number; cy: number } {
  const dx = t.x - s.x;
  const dy = t.y - s.y;
  const dist = norm2(dx, dy);

  const ux = dist > 0 ? (-dy / dist) : 0;
  const uy = dist > 0 ? (dx / dist) : 0;

  const k = dist * curvatureFrac * sign;
  const mx = (s.x + t.x) / 2;
  const my = (s.y + t.y) / 2;

  const cx = mx + ux * k;
  const cy = my + uy * k;

  const d = `M ${s.x.toFixed(2)} ${s.y.toFixed(2)} Q ${cx.toFixed(2)} ${cy.toFixed(2)} ${t.x.toFixed(2)} ${t.y.toFixed(2)}`;
  return { d, cx, cy };
}

function weights(edges: TransferEdge[]): number[] {
  const ws: number[] = [];
  for (const e of edges) {
    const w = typeof e.weight === "number" && Number.isFinite(e.weight) ? e.weight : 0;
    ws.push(Math.abs(w));
  }
  return ws;
}

function minMax(vals: number[], fallbackMin = 0, fallbackMax = 1) {
  if (!vals.length) return { min: fallbackMin, max: fallbackMax };
  let mn = vals[0];
  let mx = vals[0];
  for (const v of vals) {
    if (v < mn) mn = v;
    if (v > mx) mx = v;
  }
  if (mn === mx) {
    mn -= 1e-6;
    mx += 1e-6;
  }
  return { min: mn, max: mx };
}

function scale01(v: number, min: number, max: number): number {
  return clamp((v - min) / (max - min), 0, 1);
}

export function vizIrTransferOverlay(inp: TransferOverlayInput, opts: TransferOverlayOptions = {}): VizIR {
  const w = opts.canvas_w ?? 1200;
  const h = opts.canvas_h ?? 800;
  const title = opts.title ?? "overlay_transfer";

  const curvature = opts.curvature ?? 0.18;
  const bendMode = opts.bend ?? "auto";

  const minOp = opts.min_opacity ?? 0.25;
  const maxOp = opts.max_opacity ?? 0.9;
  const minSW = opts.min_stroke_w ?? 1.0;
  const maxSW = opts.max_stroke_w ?? 4.0;

  const minAbs = opts.min_abs_weight ?? 0;

  const edgesRaw = inp.edges
    ? inp.edges.slice()
    : (inp.scene?.edges ? inp.scene.edges.slice() : []);

  const edges = edgesRaw
    .filter(e => (e.edge_type ?? "transfer") === "transfer")
    .sort((a, b) => {
      const ka = stableKey(a);
      const kb = stableKey(b);
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });

  const absW = weights(edges);
  const mm = minMax(absW, 0, 1);

  const items: BaseItem[] = [];

  items.push({
    id: "trf.title",
    type: "text",
    style: { font_family: "ui-monospace, Menlo, Consolas, monospace", font_size: 12, fill: "rgba(0,0,0,0.85)" },
    geom: { x: 30, y: 30, text: `${title} • curvature=${curvature}` },
    data: { kind: "transfer_title" }
  });

  for (const e of edges) {
    const s = inp.pos[e.source];
    const t = inp.pos[e.target];
    if (!s || !t) continue;

    const w0 = typeof e.weight === "number" && Number.isFinite(e.weight) ? e.weight : 0;
    const aw = Math.abs(w0);
    if (aw < minAbs) continue;

    const t01 = scale01(aw, mm.min, mm.max);
    const opacity = minOp + t01 * (maxOp - minOp);
    const strokeW = minSW + t01 * (maxSW - minSW);

    const sign = bendSign(e.source, e.target, bendMode);
    const { d, cx, cy } = quadPath(s, t, curvature, sign);

    items.push({
      id: `trf.edge.${e.source}.${e.target}`,
      type: "edge",
      style: edgeStyle(opacity, strokeW),
      geom: { d, cx, cy },
      data: {
        kind: "transfer_arc",
        edge_type: "transfer",
        src: e.source,
        tgt: e.target,
        weight: w0,
        abs_weight: aw,
        curvature,
        bend: bendMode,
        sign,
        ...(e.attributes ? { attributes: e.attributes } : {})
      },
      a11y: { title: "transfer", desc: `${e.source} → ${e.target} (w=${w0})` }
    });
  }

  const layer: Layer = {
    id: "overlay_transfer",
    z: 30,
    items: sortItemsDeterministic(items).map(it => ({
      ...it,
      geom: roundN(it.geom, 6) as Record<string, unknown>
    }))
  };

  return {
    schema: "VizIR.v0.1",
    meta: { title, provenance: inp.provenance ?? null },
    canvas: { w, h, unit: "px" },
    layers: sortLayersDeterministic([layer])
  };
}

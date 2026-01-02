import type { Layer, BaseItem, VizIR, Style } from "../types/vizir";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { roundN } from "../utils/round";

export type TrendPackKind = "motif" | "domain";

export type MotifTrendPoint = {
  run_id: string;
  label?: string | null;
  salience: number | null;
  neighbor_jaccard_prev: number | null;
  neighbor_count: number;
};

export type DomainTrendPoint = {
  run_id: string;
  label?: string | null;
  inbound: number | null;
  outbound: number | null;
  net: number | null;
};

export type TrendPackV0 =
  | { kind: "motif"; target: string; points: MotifTrendPoint[]; provenance?: Record<string, unknown> }
  | { kind: "domain"; target: string; points: DomainTrendPoint[]; provenance?: Record<string, unknown> };

export type TrendVizOptions = {
  canvas_w?: number;
  canvas_h?: number;
  title?: string;
  origin_x?: number;
  origin_y?: number;
  gap_y?: number;
  chart_w?: number;
  chart_h?: number;
};

type Rect = { x: number; y: number; w: number; h: number };

function escId(s: string): string {
  return String(s).replaceAll(" ", "_");
}

function minMax(vals: Array<number | null>, fallbackMin = 0, fallbackMax = 1) {
  const f = vals.filter(v => typeof v === "number" && Number.isFinite(v)) as number[];
  if (!f.length) return { min: fallbackMin, max: fallbackMax };
  let mn = f[0];
  let mx = f[0];
  for (const v of f) {
    if (v < mn) mn = v;
    if (v > mx) mx = v;
  }
  if (mn === mx) {
    mn -= 1e-6;
    mx += 1e-6;
  }
  return { min: mn, max: mx };
}

function xScale(i: number, n: number, r: Rect): number {
  if (n <= 1) return r.x + r.w / 2;
  return r.x + (i / (n - 1)) * r.w;
}

function yScale(v: number, vmin: number, vmax: number, r: Rect): number {
  const t = (v - vmin) / (vmax - vmin);
  return r.y + (1 - t) * r.h;
}

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function monoTextStyle(): Style {
  return { font_family: "ui-monospace, Menlo, Consolas, monospace", font_size: 10, fill: "rgba(0,0,0,0.75)" };
}

function frameItems(prefix: string, r: Rect, title: string): BaseItem[] {
  const items: BaseItem[] = [];

  items.push({
    id: `${prefix}.title`,
    type: "text",
    style: { ...monoTextStyle(), font_size: 12, fill: "rgba(0,0,0,0.85)" },
    geom: { x: r.x, y: r.y - 10, text: title },
    data: { kind: "chart_title" }
  });

  items.push({
    id: `${prefix}.frame`,
    type: "rect",
    style: { stroke: "rgba(0,0,0,0.18)", fill: "rgba(0,0,0,0.02)", stroke_w: 1 },
    geom: { x: r.x, y: r.y, w: r.w, h: r.h },
    data: { kind: "chart_frame" }
  });

  return items;
}

function axisLabels(prefix: string, r: Rect, leftTop: string, leftBottom: string, bottomLeft: string, bottomRight: string): BaseItem[] {
  const st = monoTextStyle();
  return [
    { id: `${prefix}.lab.max`, type: "text", style: st, geom: { x: r.x - 6, y: r.y + 10, text: leftTop, text_anchor: "end" }, data: { kind: "axis" } },
    { id: `${prefix}.lab.min`, type: "text", style: st, geom: { x: r.x - 6, y: r.y + r.h, text: leftBottom, text_anchor: "end" }, data: { kind: "axis" } },
    { id: `${prefix}.lab.l`, type: "text", style: st, geom: { x: r.x, y: r.y + r.h + 16, text: bottomLeft, text_anchor: "start" }, data: { kind: "axis" } },
    { id: `${prefix}.lab.r`, type: "text", style: st, geom: { x: r.x + r.w, y: r.y + r.h + 16, text: bottomRight, text_anchor: "end" }, data: { kind: "axis" } }
  ];
}

function pathFromSeries(series: Array<number | null>, vmin: number, vmax: number, r: Rect): string {
  let d = "";
  let pen = false;
  for (let i = 0; i < series.length; i += 1) {
    const v = series[i];
    if (typeof v !== "number" || !Number.isFinite(v)) {
      pen = false;
      continue;
    }
    const x = xScale(i, series.length, r);
    const y = yScale(v, vmin, vmax, r);
    if (!pen) {
      d += `M ${x.toFixed(2)} ${y.toFixed(2)} `;
      pen = true;
    } else {
      d += `L ${x.toFixed(2)} ${y.toFixed(2)} `;
    }
  }
  return d.trim();
}

function dotItems(prefix: string, series: Array<number | null>, vmin: number, vmax: number, r: Rect, radius = 2.2): BaseItem[] {
  const items: BaseItem[] = [];
  for (let i = 0; i < series.length; i += 1) {
    const v = series[i];
    if (typeof v !== "number" || !Number.isFinite(v)) continue;
    const x = xScale(i, series.length, r);
    const y = yScale(v, vmin, vmax, r);
    items.push({
      id: `${prefix}.dot.${i}`,
      type: "circle",
      style: { fill: "rgba(0,0,0,0.85)", stroke: null },
      geom: { cx: x, cy: y, r: radius },
      data: { kind: "dot", i, v }
    });
  }
  return items;
}

function churnStrip(prefix: string, series: Array<number | null>, r: Rect): BaseItem[] {
  const items: BaseItem[] = [];
  for (let i = 1; i < series.length; i += 1) {
    const v = series[i];
    if (typeof v !== "number" || !Number.isFinite(v)) continue;
    const h = clamp01(v) * r.h;
    const x = xScale(i, series.length, r) - 2;
    const y = r.y + (r.h - h);
    items.push({
      id: `${prefix}.bar.${i}`,
      type: "rect",
      style: { fill: "rgba(0,0,0,0.65)", stroke: null },
      geom: { x, y, w: 4, h },
      data: { kind: "churn_bar", i, v }
    });
  }
  return items;
}

function flowNetDots(prefix: string, net: Array<number | null>, maxAbs: number, r: Rect): BaseItem[] {
  const items: BaseItem[] = [];
  const midY = r.y + r.h / 2;
  for (let i = 0; i < net.length; i += 1) {
    const v = net[i];
    if (typeof v !== "number" || !Number.isFinite(v)) continue;
    const x = xScale(i, net.length, r);
    const y = midY - (v / maxAbs) * (r.h / 2);
    items.push({
      id: `${prefix}.net.${i}`,
      type: "circle",
      style: { fill: "rgba(0,0,0,0.85)", stroke: null },
      geom: { cx: x, cy: y, r: 2.2 },
      data: { kind: "net_dot", i, v }
    });
  }
  items.push({
    id: `${prefix}.mid`,
    type: "line",
    style: { stroke: "rgba(0,0,0,0.18)", stroke_w: 1 },
    geom: { x1: r.x, y1: midY, x2: r.x + r.w, y2: midY },
    data: { kind: "net_midline" }
  });
  return items;
}

export function vizIrFromTrendPack(tp: TrendPackV0, opts: TrendVizOptions = {}): VizIR {
  const w = opts.canvas_w ?? 540;
  const h = opts.canvas_h ?? 420;
  const ox = opts.origin_x ?? 30;
  const oy = opts.origin_y ?? 40;
  const gapY = opts.gap_y ?? 18;
  const cw = opts.chart_w ?? 420;
  const ch = opts.chart_h ?? 160;

  const title = opts.title ?? `TrendPack → VizIR • ${tp.target}`;
  const items: BaseItem[] = [];

  if (tp.kind === "motif") {
    const pts = tp.points || [];
    const sal = pts.map(p => p.salience);
    const jac = pts.map(p => p.neighbor_jaccard_prev);

    const r1: Rect = { x: ox, y: oy, w: cw, h: ch };
    const mm = minMax(sal, 0, 1);

    items.push(...frameItems("tr.sal", r1, `salience • ${tp.target}`));
    items.push(...axisLabels(
      "tr.sal",
      r1,
      mm.max.toFixed(2),
      mm.min.toFixed(2),
      (pts[0]?.run_id ?? "start").slice(0, 10),
      (pts[pts.length - 1]?.run_id ?? "end").slice(0, 10)
    ));

    const d = pathFromSeries(sal, mm.min, mm.max, r1);
    items.push({
      id: "tr.sal.path",
      type: "path",
      style: { stroke: "rgba(0,0,0,0.85)", fill: "none", stroke_w: 1.5 },
      geom: { d },
      data: { kind: "salience_path", target: tp.target }
    });
    items.push(...dotItems("tr.sal", sal, mm.min, mm.max, r1, 2.2));

    const r2: Rect = { x: ox, y: oy + ch + 40 + gapY, w: cw, h: 90 };
    items.push(...frameItems("tr.churn", r2, `churn • ${tp.target} (jaccard prev)`));
    items.push(...axisLabels("tr.churn", r2, "1.00", "0.00", "stable", "volatile"));
    items.push(...churnStrip("tr.churn", jac, r2));
  } else {
    const pts = tp.points || [];
    const inbound = pts.map(p => p.inbound);
    const outbound = pts.map(p => p.outbound);
    const net = pts.map(p => p.net);

    const all: number[] = [];
    for (const v of inbound) if (typeof v === "number" && Number.isFinite(v)) all.push(v);
    for (const v of outbound) if (typeof v === "number" && Number.isFinite(v)) all.push(v);
    for (const v of net) if (typeof v === "number" && Number.isFinite(v)) all.push(Math.abs(v));
    const mm = minMax(all.length ? all : [0], 0, 1);
    const maxAbs = mm.max;

    const r1: Rect = { x: ox, y: oy, w: cw, h: ch };
    items.push(...frameItems("tr.flow", r1, `flow • ${tp.target} (transfer)`));
    items.push(...axisLabels("tr.flow", r1, maxAbs.toFixed(2), "0.00", "in/out", "net(dots)"));

    items.push({
      id: "tr.flow.out",
      type: "path",
      style: { stroke: "rgba(0,0,0,0.85)", fill: "none", stroke_w: 1.6 },
      geom: { d: pathFromSeries(outbound, 0, maxAbs, r1) },
      data: { kind: "outbound_path", target: tp.target }
    });

    items.push({
      id: "tr.flow.in",
      type: "path",
      style: { stroke: "rgba(0,0,0,0.55)", fill: "none", stroke_w: 1.3, dash: "3 3" },
      geom: { d: pathFromSeries(inbound, 0, maxAbs, r1) },
      data: { kind: "inbound_path", target: tp.target }
    });

    items.push(...flowNetDots("tr.flow", net, maxAbs || 1, r1));

    items.push({
      id: "tr.flow.legend",
      type: "text",
      style: { ...monoTextStyle(), fill: "rgba(0,0,0,0.75)" },
      geom: { x: r1.x, y: r1.y + r1.h + 16, text: "out=solid  in=dashed  net=dots" },
      data: { kind: "legend" }
    });
  }

  const layer: Layer = {
    id: `trend.${escId(tp.target)}`,
    z: 50,
    items: sortItemsDeterministic(items).map(it => ({
      ...it,
      geom: roundN(it.geom, 6) as Record<string, unknown>,
      data: { ...(it.data || {}), trend_target: tp.target, trend_kind: tp.kind }
    }))
  };

  return {
    schema: "VizIR.v0.1",
    meta: { title, provenance: (tp as { provenance?: Record<string, unknown> }).provenance ?? null },
    canvas: { w, h, unit: "px" },
    layers: sortLayersDeterministic([layer])
  };
}

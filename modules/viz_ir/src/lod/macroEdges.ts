import type { VizIR, Layer, BaseItem } from "../types/vizir";
import type { LayoutIR } from "../layout/types";
import { normalizeVizIR } from "../utils/normalize";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { groupKey, buildGroupAnchors } from "./grouping";

export type MacroEdgeOptions = {
  layer_id?: string;
  z?: number;

  spine_x?: number;
  default_x_left?: number;
  default_x_right?: number;

  min_opacity?: number;
  max_opacity?: number;
  min_stroke_w?: number;
  max_stroke_w?: number;

  top_k?: number;
};

type FineEdge = {
  id: string;
  src: string;
  tgt: string;
  weight: number;
};

type MacroStats = {
  src_group: string;
  tgt_group: string;
  count: number;
  sum_abs: number;
  max_abs: number;
  contributors: Array<{ edge_id: string; abs_w: number; src: string; tgt: string }>;
};

function clamp(x: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, x));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function stableSortBy<T>(xs: T[], key: (t: T) => string): T[] {
  return xs.slice().sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
}

function extractFineEdges(ir: VizIR): FineEdge[] {
  const out: FineEdge[] = [];
  for (const layer of ir.layers || []) {
    for (const it of layer.items || []) {
      if (it.type !== "edge") continue;
      const d = it.data as { src?: unknown; source?: unknown; tgt?: unknown; target?: unknown; weight?: unknown } | undefined;
      const src = d?.src ?? d?.source ?? null;
      const tgt = d?.tgt ?? d?.target ?? null;
      if (!src || !tgt) continue;
      const w = typeof d?.weight === "number" && Number.isFinite(d.weight) ? d.weight : 0;
      out.push({ id: it.id, src: String(src), tgt: String(tgt), weight: w });
    }
  }
  return stableSortBy(out, e => e.id);
}

function macroPath(ax: number, ay: number, bx: number, by: number, spineX: number): string {
  const exit = { x: spineX, y: ay };
  const enter = { x: spineX, y: by };
  const c1 = { x: (ax + spineX) / 2, y: ay };
  const c2 = { x: (ax + spineX) / 2, y: ay };
  const d1 = `M ${ax.toFixed(2)} ${ay.toFixed(2)} C ${c1.x.toFixed(2)} ${c1.y.toFixed(2)} ${c2.x.toFixed(2)} ${c2.y.toFixed(2)} ${exit.x.toFixed(2)} ${exit.y.toFixed(2)}`;
  const midY = (ay + by) / 2;
  const d2 = `M ${exit.x.toFixed(2)} ${exit.y.toFixed(2)} Q ${spineX.toFixed(2)} ${midY.toFixed(2)} ${enter.x.toFixed(2)} ${enter.y.toFixed(2)}`;
  const c3 = { x: (bx + spineX) / 2, y: by };
  const c4 = { x: (bx + spineX) / 2, y: by };
  const d3 = `M ${enter.x.toFixed(2)} ${enter.y.toFixed(2)} C ${c3.x.toFixed(2)} ${c3.y.toFixed(2)} ${c4.x.toFixed(2)} ${c4.y.toFixed(2)} ${bx.toFixed(2)} ${by.toFixed(2)}`;
  return `${d1} ${d2} ${d3}`.trim();
}

export function emitMacroEdges(
  base: VizIR,
  opts: MacroEdgeOptions = {},
  layout?: LayoutIR | null,
  entityTypeMap?: Record<string, string> | null
): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });
  const fine = extractFineEdges(ir);

  const anchors = buildGroupAnchors(layout);
  const spineX = opts.spine_x ?? 60;
  for (const k of Object.keys(anchors)) anchors[k].ax = spineX;

  const statsMap = new Map<string, MacroStats>();

  for (const e of fine) {
    const sg = groupKey(e.src, layout, entityTypeMap);
    const tg = groupKey(e.tgt, layout, entityTypeMap);
    if (sg === tg) continue;

    const key = `${sg}→${tg}`;
    const absw = Math.abs(e.weight);

    const cur = statsMap.get(key) || {
      src_group: sg,
      tgt_group: tg,
      count: 0,
      sum_abs: 0,
      max_abs: 0,
      contributors: [] as Array<{ edge_id: string; abs_w: number; src: string; tgt: string }>
    };
    cur.count += 1;
    cur.sum_abs += absw;
    cur.max_abs = Math.max(cur.max_abs, absw);
    cur.contributors.push({ edge_id: e.id, abs_w: absw, src: e.src, tgt: e.tgt });
    statsMap.set(key, cur);
  }

  const stats = Array.from(statsMap.values()).sort((a, b) => {
    const ka = `${a.src_group}|${a.tgt_group}`;
    const kb = `${b.src_group}|${b.tgt_group}`;
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });

  const counts = stats.map(s => s.count);
  const avgs = stats.map(s => (s.count ? s.sum_abs / s.count : 0));

  const cMin = counts.length ? Math.min(...counts) : 1;
  const cMax = counts.length ? Math.max(...counts) : 1;
  const aMin = avgs.length ? Math.min(...avgs) : 0;
  const aMax = avgs.length ? Math.max(...avgs) : 1;

  const topK = opts.top_k ?? 5;

  const items: BaseItem[] = [];

  const leftX = opts.default_x_left ?? 220;
  const rightX = opts.default_x_right ?? Math.max(leftX + 200, ir.canvas.w - 220);

  function anchorFor(groupId: string, side: "left" | "right"): { x: number; y: number; label: string } {
    const g = anchors[groupId];
    if (g) return { x: g.ax, y: g.ay, label: g.label };
    let h = 0;
    for (let i = 0; i < groupId.length; i += 1) h = (h * 33 + groupId.charCodeAt(i)) >>> 0;
    const y = 80 + (h % Math.max(1, Math.floor(ir.canvas.h - 160)));
    return { x: side === "left" ? leftX : rightX, y, label: groupId };
  }

  for (const s of stats) {
    const avg = s.count ? s.sum_abs / s.count : 0;

    const tC = cMax === cMin ? 0 : (s.count - cMin) / (cMax - cMin);
    const tA = aMax === aMin ? 0 : (avg - aMin) / (aMax - aMin);

    const strokeW = lerp(opts.min_stroke_w ?? 1.5, opts.max_stroke_w ?? 10, clamp(tC, 0, 1));
    const opacity = lerp(opts.min_opacity ?? 0.2, opts.max_opacity ?? 0.9, clamp(tA, 0, 1));

    const A = anchorFor(s.src_group, "left");
    const B = anchorFor(s.tgt_group, "right");

    const d = macroPath(A.x, A.y, B.x, B.y, spineX);

    const contributors = s.contributors
      .slice()
      .sort((u, v) => v.abs_w - u.abs_w || (u.edge_id < v.edge_id ? -1 : 1))
      .slice(0, topK)
      .map(c => ({ edge_id: c.edge_id, abs_w: c.abs_w, src: c.src, tgt: c.tgt }));

    items.push({
      id: `macro.${s.src_group}→${s.tgt_group}`,
      type: "edge",
      style: { stroke: "rgba(0,0,0,0.85)", fill: "none", opacity, stroke_w: strokeW },
      geom: { d },
      data: {
        kind: "macroedge",
        src_group: s.src_group,
        tgt_group: s.tgt_group,
        count: s.count,
        sum_abs_weight: s.sum_abs,
        avg_abs_weight: avg,
        max_abs_weight: s.max_abs,
        top: contributors
      },
      a11y: {
        title: "macroedge",
        desc: `${s.src_group} → ${s.tgt_group} (n=${s.count}, avg=${avg.toFixed(3)})`
      }
    });
  }

  const layer: Layer = {
    id: opts.layer_id ?? "overlay_macro",
    z: opts.z ?? 25,
    items: sortItemsDeterministic(items)
  };

  return {
    schema: "VizIR.v0.1",
    meta: { title: "macro_edges", provenance: ir.meta?.provenance ?? null },
    canvas: ir.canvas,
    layers: sortLayersDeterministic([layer])
  };
}

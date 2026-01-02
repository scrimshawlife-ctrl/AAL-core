import type { Layer, BaseItem, VizIR, Style } from "../types/vizir";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { roundN } from "../utils/round";

export type HeatmapMatrix = {
  rows: string[];
  cols: string[];
  values: Array<Array<number | null>>;
  provenance?: Record<string, unknown>;
};

export type HeatmapEdge = { row: string; col: string; value: number; meta?: Record<string, unknown> };
export type HeatmapEdges = { edges: HeatmapEdge[]; provenance?: Record<string, unknown> };

export type HeatmapInput = HeatmapMatrix | HeatmapEdges;

export type HeatmapOptions = {
  canvas_w?: number;
  canvas_h?: number;
  title?: string;
  origin_x?: number;
  origin_y?: number;
  cell_w?: number;
  cell_h?: number;
  gap?: number;
  label_rows?: boolean;
  label_cols?: boolean;
  label_limit?: number;
  bins?: number;
  clamp_min?: number | null;
  clamp_max?: number | null;
  base_opacity?: number;
  max_opacity?: number;
};

function stableSort(xs: string[]): string[] {
  return xs.slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

function clamp(x: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, x));
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

function trunc(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, Math.max(0, n - 1)) + "…";
}

function monoTextStyle(): Style {
  return { font_family: "ui-monospace, Menlo, Consolas, monospace", font_size: 10, fill: "rgba(0,0,0,0.75)" };
}

function isMatrix(x: HeatmapInput): x is HeatmapMatrix {
  return (x as HeatmapMatrix).rows !== undefined && (x as HeatmapMatrix).cols !== undefined;
}

function edgesToMatrix(inp: HeatmapEdges): HeatmapMatrix {
  const rows = stableSort(Array.from(new Set(inp.edges.map(e => e.row))));
  const cols = stableSort(Array.from(new Set(inp.edges.map(e => e.col))));
  const rIndex = new Map(rows.map((r, i) => [r, i]));
  const cIndex = new Map(cols.map((c, i) => [c, i]));
  const values: Array<Array<number | null>> = rows.map(() => cols.map(() => null));

  for (const e of inp.edges) {
    const i = rIndex.get(e.row);
    const j = cIndex.get(e.col);
    if (i == null || j == null) continue;
    values[i][j] = e.value;
  }

  return { rows, cols, values, provenance: inp.provenance };
}

function quantize(v: number, min: number, max: number, bins: number): number {
  const t = (v - min) / (max - min);
  const q = Math.floor(clamp(t, 0, 0.999999) * bins);
  return clamp(q, 0, bins - 1);
}

export function vizIrHeatmapOverlay(input: HeatmapInput, opts: HeatmapOptions = {}): VizIR {
  const w = opts.canvas_w ?? 1200;
  const h = opts.canvas_h ?? 800;

  const ox = opts.origin_x ?? 80;
  const oy = opts.origin_y ?? 60;
  const cw = opts.cell_w ?? 18;
  const ch = opts.cell_h ?? 18;
  const gap = opts.gap ?? 2;

  const bins = opts.bins ?? 8;
  const baseOp = opts.base_opacity ?? 0.08;
  const maxOp = opts.max_opacity ?? 0.85;

  const title = opts.title ?? "overlay_heatmap";

  const matrix = isMatrix(input) ? input : edgesToMatrix(input as HeatmapEdges);
  const rows = stableSort(matrix.rows);
  const cols = stableSort(matrix.cols);

  const rOld = new Map(matrix.rows.map((r, i) => [r, i]));
  const cOld = new Map(matrix.cols.map((c, i) => [c, i]));
  const values: Array<Array<number | null>> = rows.map(r => cols.map(c => {
    const i = rOld.get(r);
    const j = cOld.get(c);
    if (i == null || j == null) return null;
    const v = matrix.values?.[i]?.[j];
    return (typeof v === "number" && Number.isFinite(v)) ? v : null;
  }));

  const finite: number[] = [];
  for (let i = 0; i < rows.length; i += 1) {
    for (let j = 0; j < cols.length; j += 1) {
      const v = values[i][j];
      if (typeof v === "number" && Number.isFinite(v)) finite.push(v);
    }
  }

  let { min, max } = minMax(finite, 0, 1);
  if (typeof opts.clamp_min === "number") min = opts.clamp_min;
  if (typeof opts.clamp_max === "number") max = opts.clamp_max;
  if (min === max) {
    min -= 1e-6;
    max += 1e-6;
  }

  const items: BaseItem[] = [];

  items.push({
    id: "hm.title",
    type: "text",
    style: { ...monoTextStyle(), font_size: 12, fill: "rgba(0,0,0,0.85)" },
    geom: { x: ox, y: oy - 24, text: `${title} • bins=${bins}` },
    data: { kind: "heatmap_title" }
  });

  const frameW = cols.length * (cw + gap) + gap;
  const frameH = rows.length * (ch + gap) + gap;
  items.push({
    id: "hm.frame",
    type: "rect",
    style: { stroke: "rgba(0,0,0,0.18)", fill: "rgba(0,0,0,0.02)", stroke_w: 1 },
    geom: { x: ox - gap, y: oy - gap, w: frameW, h: frameH },
    data: { kind: "heatmap_frame" }
  });

  for (let i = 0; i < rows.length; i += 1) {
    for (let j = 0; j < cols.length; j += 1) {
      const v = values[i][j];
      if (typeof v !== "number" || !Number.isFinite(v)) continue;

      const q = quantize(v, min, max, bins);
      const t = (bins <= 1) ? 1 : (q / (bins - 1));
      const op = baseOp + t * (maxOp - baseOp);

      const x = ox + j * (cw + gap);
      const y = oy + i * (ch + gap);

      items.push({
        id: `hm.cell.${rows[i]}.${cols[j]}`,
        type: "heatcell",
        style: { fill: "rgba(0,0,0,1.0)", stroke: null, opacity: op },
        geom: { x, y, w: cw, h: ch },
        data: {
          kind: "heatcell",
          row: rows[i],
          col: cols[j],
          value: v,
          bin: q,
          bins,
          scale_min: min,
          scale_max: max
        },
        a11y: { title: `${rows[i]} × ${cols[j]}`, desc: `v=${v} bin=${q}/${bins - 1}` }
      });
    }
  }

  const labelLimit = opts.label_limit ?? 22;
  const doRow = opts.label_rows ?? true;
  const doCol = opts.label_cols ?? true;

  if (doRow) {
    for (let i = 0; i < rows.length; i += 1) {
      const y = oy + i * (ch + gap) + ch * 0.75;
      items.push({
        id: `hm.row.${rows[i]}`,
        type: "text",
        style: { ...monoTextStyle(), text_anchor: "end" },
        geom: { x: ox - 8, y, text: trunc(rows[i], labelLimit) },
        data: { kind: "row_label", row: rows[i] }
      });
    }
  }

  if (doCol) {
    for (let j = 0; j < cols.length; j += 1) {
      const x = ox + j * (cw + gap) + cw * 0.5;
      items.push({
        id: `hm.col.${cols[j]}`,
        type: "text",
        style: { ...monoTextStyle(), text_anchor: "middle", font_size: 9 },
        geom: { x, y: oy - 10, text: trunc(cols[j], 10) },
        data: { kind: "col_label", col: cols[j] }
      });
    }
  }

  const layer: Layer = {
    id: "overlay_heatmap",
    z: 20,
    items: sortItemsDeterministic(items).map(it => ({
      ...it,
      geom: roundN(it.geom, 6) as Record<string, unknown>
    }))
  };

  return {
    schema: "VizIR.v0.1",
    meta: { title, provenance: matrix.provenance ?? null },
    canvas: { w, h, unit: "px" },
    layers: sortLayersDeterministic([layer])
  };
}

import type { VizIR, Layer, BaseItem } from "../types/vizir";
import type { LayoutIR } from "../layout/types";
import { normalizeVizIR } from "../utils/normalize";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { extractPosFromVizIR } from "../utils/extractPos";
import { groupKey, buildGroupAnchors } from "./grouping";

export type SupernodeOptions = {
  layer_id?: string;
  z?: number;

  // geometry scaling
  min_r?: number;
  max_r?: number;

  // style
  fill?: string;
  stroke?: string;
  stroke_w?: number;

  // label
  show_labels?: boolean;
  label_font?: string;
  label_size?: number;

  // gating: only emit groups with >= this many members
  min_members?: number;
};

type FineEdge = { src: string; tgt: string };
type MacroEdge = { src_group: string; tgt_group: string };

function clamp(x: number, a: number, b: number): number {
  return Math.max(a, Math.min(b, x));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function stableSort<T>(xs: T[], key: (t: T) => string): T[] {
  return xs.slice().sort((a, b) => {
    const ka = key(a);
    const kb = key(b);
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });
}

function extractEdges(ir: VizIR): FineEdge[] {
  const out: FineEdge[] = [];
  for (const layer of ir.layers || []) {
    for (const it of layer.items || []) {
      if (it.type !== "edge") continue;
      const d = it.data as { src?: unknown; source?: unknown; tgt?: unknown; target?: unknown } | undefined;
      const src = d?.src ?? d?.source ?? null;
      const tgt = d?.tgt ?? d?.target ?? null;
      if (!src || !tgt) continue;
      out.push({ src: String(src), tgt: String(tgt) });
    }
  }
  return out;
}

function extractMacroEdges(ir: VizIR): MacroEdge[] {
  const out: MacroEdge[] = [];
  for (const layer of ir.layers || []) {
    for (const it of layer.items || []) {
      if (it.type !== "edge") continue;
      const d = it.data as { kind?: unknown; src_group?: unknown; tgt_group?: unknown } | undefined;
      if (d?.kind !== "macroedge") continue;
      if (d.src_group && d.tgt_group) {
        out.push({ src_group: String(d.src_group), tgt_group: String(d.tgt_group) });
      }
    }
  }
  return out;
}

export function emitSupernodes(
  base: VizIR,
  opts: SupernodeOptions = {},
  layout?: LayoutIR | null,
  entityTypeMap?: Record<string, string> | null
): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });
  const pos = extractPosFromVizIR(ir);

  const anchors = buildGroupAnchors(layout);
  const edges = extractEdges(ir);
  const macroEdges = extractMacroEdges(ir);

  const groups: Record<string, string[]> = {};
  const entityIds = Object.keys(pos).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  for (const eid of entityIds) {
    const g = groupKey(eid, layout, entityTypeMap);
    (groups[g] = groups[g] || []).push(eid);
  }

  const internalEdgeCount: Record<string, number> = {};
  const inboundMacro: Record<string, number> = {};
  const outboundMacro: Record<string, number> = {};
  for (const g of Object.keys(groups)) internalEdgeCount[g] = 0;

  const gOf: Record<string, string> = {};
  for (const g of Object.keys(groups)) {
    for (const eid of groups[g]) gOf[eid] = g;
  }

  for (const e of edges) {
    const gs = gOf[e.src];
    const gt = gOf[e.tgt];
    if (gs && gt && gs === gt) internalEdgeCount[gs] = (internalEdgeCount[gs] || 0) + 1;
  }

  for (const me of macroEdges) {
    inboundMacro[me.tgt_group] = (inboundMacro[me.tgt_group] || 0) + 1;
    outboundMacro[me.src_group] = (outboundMacro[me.src_group] || 0) + 1;
  }

  const memberCounts = Object.keys(groups).map(g => groups[g].length);
  const minC = memberCounts.length ? Math.min(...memberCounts) : 1;
  const maxC = memberCounts.length ? Math.max(...memberCounts) : 1;

  const minR = opts.min_r ?? 10;
  const maxR = opts.max_r ?? 60;

  const minMembers = opts.min_members ?? 3;

  const items: BaseItem[] = [];

  const superGroups = stableSort(Object.keys(groups), g => g);

  for (const g of superGroups) {
    const members = groups[g];
    if (!members || members.length < minMembers) continue;

    let cx: number;
    let cy: number;
    const A = anchors[g];
    if (A) {
      cx = A.ax;
      cy = A.ay;
    } else {
      const xs = members.map(id => pos[id].x).sort((a, b) => a - b);
      const ys = members.map(id => pos[id].y).sort((a, b) => a - b);
      cx = xs[Math.floor(xs.length / 2)];
      cy = ys[Math.floor(ys.length / 2)];
    }

    const count = members.length;
    const tC = maxC === minC ? 0 : (count - minC) / (maxC - minC);

    const eInt = internalEdgeCount[g] || 0;
    const possible = count * (count - 1);
    const density = possible > 0 ? eInt / possible : 0;
    const tD = clamp(density * 5, 0, 1);
    const resonance = tD;

    const r = lerp(minR, maxR, clamp(0.75 * tC + 0.25 * tD, 0, 1));

    items.push({
      id: `super.${g}`,
      type: "circle",
      style: {
        fill: opts.fill ?? "rgba(0,0,0,0.04)",
        stroke: opts.stroke ?? "rgba(0,0,0,0.18)",
        stroke_w: opts.stroke_w ?? 2
      },
      geom: { cx, cy, r },
      data: {
        kind: "supernode",
        group_id: g,
        member_count: count,
        internal_edge_count: eInt,
        inbound_macro_edges: inboundMacro[g] || 0,
        outbound_macro_edges: outboundMacro[g] || 0,
        density_proxy: density,
        resonance_proxy: resonance,
        members: members.slice(0, 50)
      },
      a11y: { title: "supernode", desc: `${g} (${count})` }
    });

    if (opts.show_labels ?? true) {
      const label = `${A?.label ?? g} (${count})`;
      items.push({
        id: `super.label.${g}`,
        type: "text",
        style: {
          font_family: opts.label_font ?? "ui-monospace, Menlo, Consolas, monospace",
          font_size: opts.label_size ?? 12,
          fill: "rgba(0,0,0,0.65)",
          text_anchor: "start"
        },
        geom: { x: cx + r + 8, y: cy + 4, text: label },
        data: { kind: "supernode_label", group_id: g }
      });
    }
  }

  const layer: Layer = {
    id: opts.layer_id ?? "overlay_supernodes",
    z: opts.z ?? 15,
    items: sortItemsDeterministic(items)
  };

  return {
    schema: "VizIR.v0.1",
    meta: { title: "supernodes", provenance: ir.meta?.provenance ?? null },
    canvas: ir.canvas,
    layers: sortLayersDeterministic([layer])
  };
}

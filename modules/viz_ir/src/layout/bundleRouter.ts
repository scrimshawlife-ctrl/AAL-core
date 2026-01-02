import type { LayoutIR } from "./types";

type XY = { x: number; y: number };

export type BundleEdge = { edge_id: string; source: string; target: string; weight?: number | null };

export type BundleRouterOptions = {
  spine_x?: number;
  lane_spine_offset?: number;
};

function byId(nodes: LayoutIR["nodes"]): Record<string, XY & { lane?: string | null }> {
  const m: Record<string, XY & { lane?: string | null }> = {};
  for (const n of nodes) m[n.entity_id] = { x: n.x, y: n.y, lane: n.lane ?? null };
  return m;
}

function midY(laneId: string, layout: LayoutIR): number | null {
  const lanes = layout.lanes || [];
  const lane = lanes.find(l => l.id === laneId);
  if (!lane) return null;
  return lane.y + lane.h / 2;
}

function cubicPath(p0: XY, c1: XY, c2: XY, p1: XY): string {
  return `M ${p0.x.toFixed(2)} ${p0.y.toFixed(2)} C ${c1.x.toFixed(2)} ${c1.y.toFixed(2)} ${c2.x.toFixed(2)} ${c2.y.toFixed(2)} ${p1.x.toFixed(2)} ${p1.y.toFixed(2)}`;
}

export function routeBundled(
  layout: LayoutIR,
  edges: BundleEdge[],
  opts: BundleRouterOptions = {}
): Array<{ edge_id: string; d: string; via: string[] }> {
  const nmap = byId(layout.nodes);
  const spineX = opts.spine_x ?? 60;

  const out: Array<{ edge_id: string; d: string; via: string[] }> = [];

  for (const e of edges.slice().sort((a, b) => (a.edge_id < b.edge_id ? -1 : a.edge_id > b.edge_id ? 1 : 0))) {
    const s = nmap[e.source];
    const t = nmap[e.target];
    if (!s || !t) continue;

    const sl = s.lane ?? "";
    const tl = t.lane ?? "";
    const sMid = sl ? midY(sl, layout) : null;
    const tMid = tl ? midY(tl, layout) : null;

    if (sl && tl && sl === tl) {
      const dx = t.x - s.x;
      const c1 = { x: s.x + dx * 0.35, y: s.y };
      const c2 = { x: s.x + dx * 0.65, y: t.y };
      out.push({ edge_id: e.edge_id, d: cubicPath(s, c1, c2, t), via: [sl] });
      continue;
    }

    const exit = { x: spineX, y: sMid ?? s.y };
    const enter = { x: spineX, y: tMid ?? t.y };

    const c1 = { x: (s.x + exit.x) / 2, y: s.y };
    const c2 = { x: (s.x + exit.x) / 2, y: exit.y };
    const d1 = cubicPath(s, c1, c2, exit);

    const c3 = { x: spineX, y: (exit.y + enter.y) / 2 };
    const d2 = `M ${exit.x.toFixed(2)} ${exit.y.toFixed(2)} Q ${c3.x.toFixed(2)} ${c3.y.toFixed(2)} ${enter.x.toFixed(2)} ${enter.y.toFixed(2)}`;

    const c4 = { x: (t.x + enter.x) / 2, y: enter.y };
    const c5 = { x: (t.x + enter.x) / 2, y: t.y };
    const d3 = cubicPath(enter, c4, c5, t);

    const d = `${d1} ${d2} ${d3}`.trim();
    out.push({ edge_id: e.edge_id, d, via: [sl || "?", "spine", tl || "?"] });
  }

  return out;
}

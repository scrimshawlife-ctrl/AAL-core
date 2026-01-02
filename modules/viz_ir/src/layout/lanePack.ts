import type { LayoutIR } from "./types";

type SceneEntity = { entity_id: string; entity_type: string; attributes?: Record<string, unknown> };

export type LanePackOptions = {
  canvas_w?: number;
  canvas_h?: number;
  title?: string;

  // lane control
  lane_order?: string[];
  lane_h?: number;
  lane_gap?: number;
  pad_x?: number;
  pad_y?: number;

  // within-lane grid
  cols?: number;
  cell_w?: number;
  cell_h?: number;
};

function stableSort(xs: string[]): string[] {
  return xs.slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export function layoutLanePack(entities: SceneEntity[], opts: LanePackOptions = {}): LayoutIR {
  const w = opts.canvas_w ?? 1400;
  const h = opts.canvas_h ?? 900;

  const laneH = opts.lane_h ?? 120;
  const laneGap = opts.lane_gap ?? 20;
  const padX = opts.pad_x ?? 90;
  const padY = opts.pad_y ?? 70;

  const cols = opts.cols ?? 10;
  const cellW = opts.cell_w ?? 90;
  const cellH = opts.cell_h ?? 46;

  const typesSet = new Set(entities.map(e => e.entity_type));
  let laneOrder = opts.lane_order ? opts.lane_order.slice() : stableSort(Array.from(typesSet));
  const missing = stableSort(Array.from(typesSet)).filter(t => !laneOrder.includes(t));
  laneOrder = laneOrder.concat(missing);

  const byType: Record<string, SceneEntity[]> = {};
  for (const e of entities) (byType[e.entity_type] = byType[e.entity_type] || []).push(e);
  for (const t of Object.keys(byType)) {
    byType[t] = byType[t].slice().sort((a, b) => (a.entity_id < b.entity_id ? -1 : a.entity_id > b.entity_id ? 1 : 0));
  }

  const lanes = laneOrder.map((t, i) => ({
    id: `lane.${t}`,
    label: t,
    y: padY + i * (laneH + laneGap),
    h: laneH
  }));

  const nodes: LayoutIR["nodes"] = [];

  for (let ti = 0; ti < laneOrder.length; ti += 1) {
    const t = laneOrder[ti];
    const lane = lanes[ti];
    const list = byType[t] || [];

    for (let i = 0; i < list.length; i += 1) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      nodes.push({
        entity_id: list[i].entity_id,
        lane: lane.id,
        order: i,
        x: padX + col * cellW,
        y: lane.y + 24 + row * cellH
      });
    }
  }

  return {
    schema: "LayoutIR.v0.1",
    canvas: { w, h, unit: "px" },
    meta: { title: opts.title ?? "layout • lane_pack", provenance: null },
    lanes,
    nodes,
    routes: null
  };
}

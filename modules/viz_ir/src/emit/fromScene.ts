import type { VizIR, Layer, BaseItem, Style } from "../types/vizir";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { roundN } from "../utils/round";

type SceneEntity = {
  entity_id: string;
  entity_type: string;
  attributes?: Record<string, unknown>;
};

type SceneEdge = {
  edge_type: string;
  source: string;
  target: string;
  weight?: number;
  attributes?: Record<string, unknown>;
};

export type SceneV0 = {
  entities: SceneEntity[];
  edges: SceneEdge[];
  [k: string]: unknown;
};

export type FromSceneOptions = {
  canvas_w?: number;
  canvas_h?: number;
  title?: string;
  layout?: "provided" | "grid" | "lane";
  grid?: {
    cols?: number;
    cell_w?: number;
    cell_h?: number;
    pad_x?: number;
    pad_y?: number;
  };
  lane?: {
    type_order?: string[];
    lane_h?: number;
    pad_x?: number;
    pad_y?: number;
    cols?: number;
    cell_w?: number;
  };
  node?: {
    r?: number;
    show_labels?: boolean;
  };
  edge?: {
    straight?: boolean;
  };
};

type XY = { x: number; y: number };

type PositionAttrs = {
  x?: unknown;
  y?: unknown;
  pos?: { x?: unknown; y?: unknown };
};

function stableStr(x: unknown): string {
  return String(x ?? "");
}

function stableSortIds(ids: string[]): string[] {
  return ids.slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

function num(v: unknown): number | null {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

function getProvidedPos(e: SceneEntity): XY | null {
  const a = (e.attributes || {}) as PositionAttrs;
  const x = num(a.x ?? a.pos?.x);
  const y = num(a.y ?? a.pos?.y);
  if (x === null || y === null) return null;
  return { x, y };
}

function defaultCanvas(opts: FromSceneOptions) {
  return {
    w: opts.canvas_w ?? 1200,
    h: opts.canvas_h ?? 800
  };
}

function gridLayout(entities: SceneEntity[], opts: FromSceneOptions): Record<string, XY> {
  const { w } = defaultCanvas(opts);
  const g = opts.grid || {};
  const cellW = g.cell_w ?? 90;
  const cellH = g.cell_h ?? 70;
  const padX = g.pad_x ?? 60;
  const padY = g.pad_y ?? 60;

  const ids = stableSortIds(entities.map(e => e.entity_id));
  const cols = g.cols ?? Math.max(6, Math.floor((w - padX * 2) / cellW));
  const pos: Record<string, XY> = {};

  for (let i = 0; i < ids.length; i += 1) {
    const col = i % cols;
    const row = Math.floor(i / cols);
    pos[ids[i]] = {
      x: padX + col * cellW,
      y: padY + row * cellH
    };
  }
  return pos;
}

function laneLayout(entities: SceneEntity[], opts: FromSceneOptions): Record<string, XY> {
  const lane = opts.lane || {};
  const padX = lane.pad_x ?? 70;
  const padY = lane.pad_y ?? 60;
  const laneH = lane.lane_h ?? 110;
  const cols = lane.cols ?? 10;
  const cellW = lane.cell_w ?? 90;

  const typesSet = new Set(entities.map(e => e.entity_type));
  let typeOrder = lane.type_order ? lane.type_order.slice() : Array.from(typesSet).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const missing = Array.from(typesSet).filter(t => !typeOrder.includes(t)).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  typeOrder = typeOrder.concat(missing);

  const byType: Record<string, SceneEntity[]> = {};
  for (const e of entities) {
    (byType[e.entity_type] = byType[e.entity_type] || []).push(e);
  }
  for (const t of Object.keys(byType)) {
    byType[t] = byType[t].slice().sort((a, b) => (a.entity_id < b.entity_id ? -1 : a.entity_id > b.entity_id ? 1 : 0));
  }

  const pos: Record<string, XY> = {};
  for (let ti = 0; ti < typeOrder.length; ti += 1) {
    const t = typeOrder[ti];
    const list = byType[t] || [];
    for (let i = 0; i < list.length; i += 1) {
      const col = i % cols;
      const row = Math.floor(i / cols);
      pos[list[i].entity_id] = {
        x: padX + col * cellW,
        y: padY + ti * laneH + row * 40
      };
    }
  }
  return pos;
}

function nodeStyle(_entityType: string): Style {
  return {
    stroke: "rgba(0,0,0,0.85)",
    fill: "rgba(255,255,255,0.95)",
    stroke_w: 1.2,
    opacity: 1.0,
    font_family: "ui-monospace, Menlo, Consolas, monospace",
    font_size: 10
  };
}

function edgeStyle(edgeType: string): Style {
  const base: Style = {
    stroke: "rgba(0,0,0,0.55)",
    fill: "none",
    stroke_w: 1.1,
    opacity: 1.0
  };
  if (edgeType === "synch") base.dash = "3 3";
  if (edgeType === "resonance") base.dash = null;
  if (edgeType === "transfer") {
    base.stroke_w = 1.4;
    base.opacity = 0.9;
  }
  return base;
}

function labelOf(e: SceneEntity): string {
  const a = e.attributes || {};
  const label = (a as { label?: unknown; name?: unknown }).label ?? (a as { name?: unknown }).name ?? e.entity_id;
  return stableStr(label);
}

function toDataAttrsEntity(e: SceneEntity) {
  return {
    entity_id: e.entity_id,
    entity_type: e.entity_type,
    ...(e.attributes ? { attributes: e.attributes } : {})
  };
}

function toDataAttrsEdge(ed: SceneEdge) {
  return {
    edge_type: ed.edge_type,
    src: ed.source,
    tgt: ed.target,
    weight: ed.weight ?? null,
    ...(ed.attributes ? { attributes: ed.attributes } : {})
  };
}

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

export function vizIrFromScene(scene: SceneV0, opts: FromSceneOptions = {}): VizIR {
  const { w, h } = defaultCanvas(opts);

  const title = opts.title ?? "Scene → VizIR";
  const layoutMode = opts.layout ?? "provided";
  const nodeR = opts.node?.r ?? 10;
  const showLabels = opts.node?.show_labels ?? true;

  const pos: Record<string, XY> = {};
  const entities = (scene.entities || []).slice().sort((a, b) => (a.entity_id < b.entity_id ? -1 : a.entity_id > b.entity_id ? 1 : 0));

  for (const e of entities) {
    const p = getProvidedPos(e);
    if (p) pos[e.entity_id] = p;
  }

  const missing = entities.filter(e => !pos[e.entity_id]);
  if (missing.length) {
    let fill: Record<string, XY> = {};
    if (layoutMode === "lane") fill = laneLayout(missing, opts);
    else if (layoutMode === "grid") fill = gridLayout(missing, opts);
    else fill = gridLayout(missing, opts);
    for (const e of missing) pos[e.entity_id] = fill[e.entity_id];
  }

  const nodeItems: BaseItem[] = [];
  for (const e of entities) {
    const p = pos[e.entity_id] || { x: 0, y: 0 };
    nodeItems.push({
      id: `node.${e.entity_id}`,
      type: "node",
      style: nodeStyle(e.entity_type),
      geom: {
        cx: p.x,
        cy: p.y,
        r: nodeR,
        label: showLabels ? labelOf(e) : null,
        lx: p.x + nodeR + 6,
        ly: p.y + 4
      },
      data: {
        ...toDataAttrsEntity(e),
        tags: [e.entity_type]
      },
      a11y: { title: e.entity_id, desc: e.entity_type }
    });
  }

  const edges = (scene.edges || []).slice().sort((a, b) => {
    const ka = `${a.edge_type}|${a.source}|${a.target}`;
    const kb = `${b.edge_type}|${b.source}|${b.target}`;
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });

  const edgeItems: BaseItem[] = [];
  for (const ed of edges) {
    const s = pos[ed.source];
    const t = pos[ed.target];
    if (!s || !t) continue;

    const wgt = typeof ed.weight === "number" && Number.isFinite(ed.weight) ? ed.weight : 0;
    const sw = edgeStyle(ed.edge_type);
    sw.opacity = clamp01(0.25 + Math.abs(wgt) * 0.75);

    edgeItems.push({
      id: `edge.${ed.edge_type}.${ed.source}.${ed.target}`,
      type: "edge",
      style: sw,
      geom: { x1: s.x, y1: s.y, x2: t.x, y2: t.y },
      data: toDataAttrsEdge(ed),
      a11y: { title: ed.edge_type, desc: `${ed.source} → ${ed.target}` }
    });
  }

  const baseLayer: Layer = {
    id: "base_scene",
    z: 10,
    items: sortItemsDeterministic(edgeItems).concat(sortItemsDeterministic(nodeItems))
  };

  const ir: VizIR = {
    schema: "VizIR.v0.1",
    meta: { title },
    canvas: { w, h, unit: "px" },
    layers: sortLayersDeterministic([baseLayer])
  };

  for (const layer of ir.layers) {
    for (const it of layer.items) {
      it.geom = roundN(it.geom, 6) as Record<string, unknown>;
    }
  }

  return ir;
}

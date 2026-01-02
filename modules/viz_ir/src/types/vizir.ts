export type VizSchema = "VizIR.v0.1";

export type Canvas = { w: number; h: number; unit: "px" };

export type VizMeta = {
  title: string;
  run_id?: string | null;
  provenance?: Record<string, unknown> | null;
  [k: string]: unknown;
};

export type Style = {
  stroke?: string | null;
  fill?: string | null;
  stroke_w?: number | null;
  opacity?: number | null;
  dash?: string | null;
  font_size?: number | null;
  font_family?: string | null;
  text_anchor?: "start" | "middle" | "end" | null;
  [k: string]: unknown;
};

export type A11y = { title?: string | null; desc?: string | null };

export type ItemType =
  | "rect"
  | "circle"
  | "line"
  | "path"
  | "text"
  | "group"
  | "node"
  | "edge"
  | "heatcell";

export type BaseItem = {
  id: string;
  type: ItemType;
  style?: Style;
  geom: Record<string, unknown>;
  data?: Record<string, unknown>;
  a11y?: A11y;
  [k: string]: unknown;
};

export type Layer = {
  id: string;
  z: number;
  opacity?: number | null;
  items: BaseItem[];
};

export type VizIR = {
  schema: VizSchema;
  meta: VizMeta;
  canvas: Canvas;
  layers: Layer[];
  legend?: Record<string, unknown>[];
  interactions?: Record<string, unknown> | null;
};

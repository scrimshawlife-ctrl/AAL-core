export type LayoutIR = {
  schema: "LayoutIR.v0.1";
  canvas: { w: number; h: number; unit: "px" | string };
  meta?: { title?: string | null; provenance?: Record<string, unknown> | null; [k: string]: unknown };
  lanes?: Array<{ id: string; label?: string | null; y: number; h: number; [k: string]: unknown }> | null;
  nodes: Array<{ entity_id: string; x: number; y: number; lane?: string | null; order?: number | null; label?: any }>;
  routes?: Array<{ edge_id: string; d: string; via?: string[] | null }> | null;
};

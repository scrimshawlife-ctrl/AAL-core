import type { VizIR } from "../types/vizir";

type XY = { x: number; y: number };

export function extractPosFromVizIR(ir: VizIR): Record<string, XY> {
  const pos: Record<string, XY> = {};
  for (const layer of ir.layers || []) {
    for (const item of layer.items || []) {
      if (item.type !== "node") continue;
      const id = item.data?.entity_id;
      const geom = item.geom || {};
      const cx = geom["cx"];
      const cy = geom["cy"];
      if (typeof id === "string" && typeof cx === "number" && typeof cy === "number") {
        pos[id] = { x: cx, y: cy };
      }
    }
  }
  return pos;
}

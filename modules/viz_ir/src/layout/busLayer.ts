import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";

export type BusLayerOptions = {
  layer_id?: string;
  z?: number;
  x?: number;
  stroke?: string;
  stroke_w?: number;
  opacity?: number;
};

export function addBusLayer(base: VizIR, opts: BusLayerOptions = {}): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });
  const x = opts.x ?? 60;

  const item: BaseItem = {
    id: "bus.spine",
    type: "line",
    style: {
      stroke: opts.stroke ?? "rgba(0,0,0,0.10)",
      stroke_w: opts.stroke_w ?? 6,
      opacity: opts.opacity ?? 0.18
    },
    geom: { x1: x, y1: 0, x2: x, y2: ir.canvas.h },
    data: { kind: "bus" }
  };

  const layer: Layer = { id: opts.layer_id ?? "layout_bus", z: opts.z ?? 6, items: [item] };
  return { ...ir, layers: [...ir.layers, layer] };
}

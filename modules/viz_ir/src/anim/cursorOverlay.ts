import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";

export type CursorOverlayOptions = {
  layer_id?: string;
  z?: number;
  x0?: number;
  x1?: number;
  y0?: number;
  y1?: number;
  stroke?: string;
  stroke_w?: number;
};

export function cursorOverlayAtFrame(
  base: VizIR,
  frameIndex: number,
  frameCount: number,
  opts: CursorOverlayOptions = {}
): VizIR {
  const nir = normalizeVizIR(base, { round: 6, sort_keys: false });
  const w = nir.canvas.w;
  const h = nir.canvas.h;

  const x0 = opts.x0 ?? 0;
  const x1 = opts.x1 ?? w;
  const y0 = opts.y0 ?? 0;
  const y1 = opts.y1 ?? h;

  const t01 = frameCount <= 1 ? 0 : frameIndex / (frameCount - 1);
  const x = x0 + (x1 - x0) * t01;

  const item: BaseItem = {
    id: `cursor.line.${frameIndex}`,
    type: "line",
    style: { stroke: opts.stroke ?? "rgba(0,0,0,0.55)", stroke_w: opts.stroke_w ?? 1.2 },
    geom: { x1: x, y1: y0, x2: x, y2: y1 },
    data: { kind: "cursor", frame: frameIndex, t01 }
  };

  const layer: Layer = {
    id: opts.layer_id ?? "overlay_cursor",
    z: opts.z ?? 90,
    items: [item]
  };

  return {
    ...nir,
    layers: [...nir.layers, layer]
  };
}

import type { VizIR, Layer } from "../types/vizir";
import { sortLayersDeterministic } from "../utils/sort";

export function mergeVizIR(base: VizIR, overlays: VizIR[], title?: string): VizIR {
  const layers: Layer[] = [];
  layers.push(...(base.layers || []));
  for (const o of overlays) layers.push(...(o.layers || []));

  return {
    schema: "VizIR.v0.1",
    meta: { ...(base.meta || {}), title: title ?? base.meta?.title ?? "VizIR merged" },
    canvas: base.canvas,
    layers: sortLayersDeterministic(layers)
  };
}

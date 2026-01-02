import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";
import { ease, type Easing } from "./timeline";

export type FadeSpec = {
  layer_id: string;
  start: number;
  end: number;
  from: number;
  to: number;
  easing?: Easing;
};

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function applyOpacityToItem(it: BaseItem, mult: number): BaseItem {
  const st = it.style || {};
  const op = typeof st.opacity === "number" && Number.isFinite(st.opacity) ? st.opacity : 1.0;
  return { ...it, style: { ...st, opacity: clamp01(op * mult) } };
}

function applyOpacityToLayer(layer: Layer, mult: number): Layer {
  const lop = layer.opacity ?? 1.0;
  const layerMult = clamp01(lop * mult);
  return {
    ...layer,
    opacity: layerMult,
    items: (layer.items || []).map(it => applyOpacityToItem(it, mult))
  };
}

export function fadeLayersAtFrame(base: VizIR, frameIndex: number, specs: FadeSpec[]): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });

  const specById = new Map(specs.map(s => [s.layer_id, s]));

  const layers = (ir.layers || []).map(layer => {
    const s = specById.get(layer.id);
    if (!s) return layer;

    const start = Math.min(s.start, s.end);
    const end = Math.max(s.start, s.end);

    if (frameIndex <= start) return applyOpacityToLayer(layer, clamp01(s.from));
    if (frameIndex >= end) return applyOpacityToLayer(layer, clamp01(s.to));

    const t01 = (frameIndex - start) / Math.max(1, end - start);
    const e = ease(t01, s.easing ?? "smoothstep");
    const op = clamp01(lerp(s.from, s.to, e));

    return applyOpacityToLayer(layer, op);
  });

  return { ...ir, layers };
}

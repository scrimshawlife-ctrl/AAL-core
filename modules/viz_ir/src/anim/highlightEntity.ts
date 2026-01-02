import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";
import { extractPosFromVizIR } from "../utils/extractPos";

export type HighlightSpec = {
  entity_id: string;
  start: number;
  end: number;
  layer_id?: string;
  z?: number;
  base_r?: number;
  pulse_r?: number;
  pulse_period?: number;
  stroke?: string;
  stroke_w?: number;
  min_opacity?: number;
  max_opacity?: number;
};

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function triWave(frame: number, period: number): number {
  const p = Math.max(2, period);
  const t = frame % p;
  const x = t / (p - 1);
  return x < 0.5 ? x * 2 : 2 - x * 2;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function highlightEntityAtFrame(base: VizIR, frameIndex: number, spec: HighlightSpec): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });

  const start = Math.min(spec.start, spec.end);
  const end = Math.max(spec.start, spec.end);
  if (frameIndex < start || frameIndex > end) {
    return ir;
  }

  const pos = extractPosFromVizIR(ir);
  const p = pos[spec.entity_id];
  if (!p) return ir;

  const layerId = spec.layer_id ?? "overlay_highlight";
  const z = spec.z ?? 95;

  const period = spec.pulse_period ?? 24;
  const wave = triWave(frameIndex - start, period);
  const radius = (spec.base_r ?? 14) + wave * (spec.pulse_r ?? 10);
  const opacity = clamp01(lerp(spec.min_opacity ?? 0.10, spec.max_opacity ?? 0.75, wave));

  const item: BaseItem = {
    id: `hl.${spec.entity_id}.${frameIndex}`,
    type: "circle",
    style: {
      stroke: spec.stroke ?? "rgba(0,0,0,0.85)",
      fill: "none",
      stroke_w: spec.stroke_w ?? 2,
      opacity
    },
    geom: { cx: p.x, cy: p.y, r: radius },
    data: { kind: "highlight", entity_id: spec.entity_id, frame: frameIndex, wave },
    a11y: { title: "highlight", desc: spec.entity_id }
  };

  const layer: Layer = { id: layerId, z, items: [item] };

  return { ...ir, layers: [...ir.layers, layer] };
}

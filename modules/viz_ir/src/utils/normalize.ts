import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { sortLayersDeterministic, sortItemsDeterministic } from "./sort";
import { roundN } from "./round";

function stripUndefined(x: unknown): unknown {
  if (x === undefined) return undefined;
  if (x === null) return null;

  if (Array.isArray(x)) {
    const arr = x.map(stripUndefined).filter(v => v !== undefined);
    return arr;
  }

  if (typeof x === "object") {
    const obj = x as Record<string, unknown>;
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(obj)) {
      const v = stripUndefined(obj[k]);
      if (v !== undefined) out[k] = v;
    }
    return out;
  }

  return x;
}

function stableKeys(x: unknown): unknown {
  if (x === null || x === undefined) return x;
  if (Array.isArray(x)) return x.map(stableKeys);
  if (typeof x === "object") {
    const obj = x as Record<string, unknown>;
    const keys = Object.keys(obj).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    const out: Record<string, unknown> = {};
    for (const k of keys) out[k] = stableKeys(obj[k]);
    return out;
  }
  return x;
}

export type NormalizeOptions = {
  round?: number;
  sort_keys?: boolean;
  round_style_numbers?: boolean;
};

function normalizeItem(it: BaseItem, roundDigits: number, roundStyle: boolean): BaseItem {
  const out: BaseItem = { ...it };

  out.geom = roundN(out.geom, roundDigits) as Record<string, unknown>;

  if (roundStyle && out.style) {
    out.style = roundN(out.style, roundDigits) as BaseItem["style"];
  }

  return stripUndefined(out) as BaseItem;
}

function normalizeLayer(layer: Layer, roundDigits: number, roundStyle: boolean): Layer {
  const items = sortItemsDeterministic(layer.items ?? []).map(it =>
    normalizeItem(it, roundDigits, roundStyle)
  );
  const out: Layer = {
    id: layer.id,
    z: layer.z,
    ...(layer.opacity !== undefined ? { opacity: layer.opacity } : {}),
    items
  };
  return stripUndefined(out) as Layer;
}

export function normalizeVizIR(ir: VizIR, opts: NormalizeOptions = {}): VizIR {
  const roundDigits = opts.round ?? 6;
  const sortKeys = opts.sort_keys ?? true;
  const roundStyle = opts.round_style_numbers ?? true;

  const layers = sortLayersDeterministic(ir.layers ?? []).map(layer =>
    normalizeLayer(layer, roundDigits, roundStyle)
  );

  const out: VizIR = {
    schema: ir.schema,
    meta: stripUndefined(roundN(ir.meta, roundDigits)) as VizIR["meta"],
    canvas: stripUndefined(roundN(ir.canvas, roundDigits)) as VizIR["canvas"],
    layers,
    ...(ir.legend ? { legend: stripUndefined(roundN(ir.legend, roundDigits)) as VizIR["legend"] } : {}),
    ...(ir.interactions
      ? { interactions: stripUndefined(roundN(ir.interactions, roundDigits)) as VizIR["interactions"] }
      : {})
  };

  const stripped = stripUndefined(out) as VizIR;
  return (sortKeys ? (stableKeys(stripped) as VizIR) : stripped);
}

export function stableStringify(x: unknown): string {
  return JSON.stringify(stableKeys(stripUndefined(x)), null, 2);
}

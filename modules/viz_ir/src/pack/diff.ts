import type { VizPack } from "./types";
import { stableStringify } from "../utils/stableStringify";

type DeltaStr = { a: string | null; b: string | null; changed: boolean };
type DeltaInt = { a: number; b: number; delta: number };
type DeltaBool = { a: boolean | null; b: boolean | null; changed: boolean };
type DeltaObj = { a: any | null; b: any | null; changed: boolean };

type BindDelta = {
  metric_key: DeltaStr;
  used_fallback: DeltaBool;
  transform: DeltaObj;
  changed: boolean;
};

export type VizPackDiff = {
  schema: "VizPackDiff.v0.1";
  a_id: string;
  b_id: string;
  integrity: {
    viz_ir_hash: DeltaStr;
    policy_hash: DeltaStr;
    binding_report_hash: DeltaStr;
    registry_version: DeltaStr;
  };
  structure: {
    layers: DeltaInt;
    items: DeltaInt;
    item_types: Record<string, DeltaInt>;
    layer_ids: { added: string[]; removed: string[] };
  };
  binding: {
    channels: { R: BindDelta; S: BindDelta; N: BindDelta; K: BindDelta; C: BindDelta };
  };
  drift: { risk: number; reasons: string[] };
};

function dStr(a: string | null | undefined, b: string | null | undefined): DeltaStr {
  const aa = a ?? null;
  const bb = b ?? null;
  return { a: aa, b: bb, changed: aa !== bb };
}

function dInt(a: number, b: number): DeltaInt {
  return { a, b, delta: b - a };
}

function dBool(a: boolean | null | undefined, b: boolean | null | undefined): DeltaBool {
  const aa = a === undefined ? null : a;
  const bb = b === undefined ? null : b;
  return { a: aa, b: bb, changed: aa !== bb };
}

function dObj(a: any, b: any): DeltaObj {
  const aa = a ?? null;
  const bb = b ?? null;
  const changed = stableStringify(aa) !== stableStringify(bb);
  return { a: aa, b: bb, changed };
}

function countStructure(pack: VizPack): { layers: number; items: number; types: Record<string, number>; layerIds: string[] } {
  const layers = (pack.payload?.viz_ir as { layers?: Array<{ id?: string; items?: Array<{ type?: string }> }> })?.layers || [];
  let itemCount = 0;
  const types: Record<string, number> = {};
  const layerIds: string[] = [];

  for (const layer of layers) {
    layerIds.push(String(layer.id));
    const items = layer.items || [];
    itemCount += items.length;
    for (const it of items) {
      const t = String(it.type || "unknown");
      types[t] = (types[t] || 0) + 1;
    }
  }
  layerIds.sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  return { layers: layers.length, items: itemCount, types, layerIds };
}

function bindDelta(aRep: any, bRep: any, ch: "R" | "S" | "N" | "K" | "C"): BindDelta {
  const ar = aRep?.resolved?.[ch] ?? null;
  const br = bRep?.resolved?.[ch] ?? null;

  const mk = dStr(ar?.metric_key ?? null, br?.metric_key ?? null);
  const uf = dBool(ar?.used_fallback ?? null, br?.used_fallback ?? null);
  const tr = dObj(ar?.transform ?? null, br?.transform ?? null);

  const changed = mk.changed || uf.changed || tr.changed;
  return { metric_key: mk, used_fallback: uf, transform: tr, changed };
}

export function diffVizPacks(a: VizPack, b: VizPack): VizPackDiff {
  const a_id = a.id;
  const b_id = b.id;

  const integrity = {
    viz_ir_hash: dStr(a.integrity?.viz_ir_hash ?? null, b.integrity?.viz_ir_hash ?? null),
    policy_hash: dStr(a.integrity?.policy_hash ?? null, b.integrity?.policy_hash ?? null),
    binding_report_hash: dStr(a.integrity?.binding_report_hash ?? null, b.integrity?.binding_report_hash ?? null),
    registry_version: dStr(a.payload?.metric_registry?.version ?? null, b.payload?.metric_registry?.version ?? null)
  };

  const A = countStructure(a);
  const B = countStructure(b);

  const allTypes = Array.from(new Set([...Object.keys(A.types), ...Object.keys(B.types)])).sort((x, y) =>
    x < y ? -1 : x > y ? 1 : 0
  );
  const item_types: Record<string, DeltaInt> = {};
  for (const t of allTypes) item_types[t] = dInt(A.types[t] || 0, B.types[t] || 0);

  const aSet = new Set(A.layerIds);
  const bSet = new Set(B.layerIds);
  const added = B.layerIds.filter(x => !aSet.has(x));
  const removed = A.layerIds.filter(x => !bSet.has(x));

  const aRep = (a.payload as { binding_report?: unknown } | undefined)?.binding_report ?? null;
  const bRep = (b.payload as { binding_report?: unknown } | undefined)?.binding_report ?? null;

  const channels = {
    R: bindDelta(aRep, bRep, "R"),
    S: bindDelta(aRep, bRep, "S"),
    N: bindDelta(aRep, bRep, "N"),
    K: bindDelta(aRep, bRep, "K"),
    C: bindDelta(aRep, bRep, "C")
  };

  let risk = 0;
  const reasons: string[] = [];

  if (integrity.policy_hash.changed) {
    risk += 0.4;
    reasons.push("policy_hash_changed");
  }
  if (integrity.registry_version.changed && !integrity.policy_hash.changed) {
    risk += 0.1;
    reasons.push("registry_version_changed");
  }

  const rebinds = Object.entries(channels).filter(([_, d]) => d.metric_key.changed);
  if (rebinds.length) {
    risk += 0.3;
    reasons.push(`metric_rebind:${rebinds.map(([k]) => k).join(",")}`);
  }

  const fallbackFlips = Object.entries(channels).filter(([_, d]) => d.used_fallback.changed);
  if (fallbackFlips.length) {
    risk += 0.2;
    reasons.push(`fallback_flip:${fallbackFlips.map(([k]) => k).join(",")}`);
  }

  if (A.items !== B.items) reasons.push(`items_delta:${B.items - A.items}`);
  if (A.layers !== B.layers) reasons.push(`layers_delta:${B.layers - A.layers}`);

  risk = Math.max(0, Math.min(1, risk));

  return {
    schema: "VizPackDiff.v0.1",
    a_id,
    b_id,
    integrity,
    structure: {
      layers: dInt(A.layers, B.layers),
      items: dInt(A.items, B.items),
      item_types,
      layer_ids: { added, removed }
    },
    binding: { channels },
    drift: { risk, reasons }
  };
}

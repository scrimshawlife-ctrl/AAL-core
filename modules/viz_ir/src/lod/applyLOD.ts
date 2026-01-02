import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";
import type { ViewState, LODPolicy } from "./types";

function matches(rule: LODPolicy["rules"][number], zoom: number, maxItems: number): boolean {
  const w = rule.when || {};
  if (typeof w.zoom_lte === "number" && !(zoom <= w.zoom_lte)) return false;
  if (typeof w.zoom_gte === "number" && !(zoom >= w.zoom_gte)) return false;
  if (typeof w.max_items_gte === "number" && !(maxItems >= w.max_items_gte)) return false;
  return true;
}

function layerMatch(layerId: string, pattern: string): boolean {
  if (pattern.endsWith(".*")) {
    const pref = pattern.slice(0, -2);
    return layerId.startsWith(pref);
  }
  return layerId === pattern;
}

function trunc(s: string, n: number): string {
  if (s.length <= n) return s;
  return s.slice(0, Math.max(0, n - 1)) + "…";
}

function compactLabel(it: BaseItem): BaseItem {
  if (it.type !== "text") return it;
  const geom = it.geom || {};
  const text = (geom as { text?: unknown }).text;
  if (typeof text !== "string") return it;
  return { ...it, geom: { ...geom, text: trunc(text, 14) } };
}

export function applyLOD(base: VizIR, view: ViewState, policy: LODPolicy): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });

  let maxItems = 0;
  for (const layer of ir.layers || []) maxItems += layer.items?.length ?? 0;

  const rule = policy.rules.find(r => matches(r, view.zoom, maxItems));
  if (!rule) return ir;

  const hideLayers = rule.actions.hide_layers ?? [];
  const hideTypes = new Set(rule.actions.hide_item_types ?? []);
  const labelMode = rule.actions.labels ?? "all";
  const edgeMode = rule.actions.edge_mode ?? "full";

  const layers: Layer[] = (ir.layers || [])
    .filter(layer => !hideLayers.some(p => layerMatch(layer.id, p)))
    .map(layer => {
      let items = (layer.items || []).filter(it => !hideTypes.has(it.type));

      if (labelMode === "none") {
        items = items.filter(it => it.type !== "text");
      } else if (labelMode === "compact") {
        items = items.map(compactLabel);
      }

      return { ...layer, items };
    });

  const meta = {
    ...(ir.meta || {}),
    lod: {
      rule_id: rule.id,
      edge_mode: edgeMode,
      zoom: view.zoom,
      max_items: maxItems
    }
  };

  return { ...ir, meta, layers };
}

import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";

export type RouteOverride = { edge_id: string; d: string; via?: string[] | null };

export type ApplyRoutesOptions = {
  // which layers to apply to; empty means "all"
  layer_ids?: string[] | null;

  // match rules
  match_on_item_id?: boolean;
  match_on_data_edge_id?: boolean;

  // tag route provenance into item.data
  annotate?: boolean;
};

function toMap(routes: RouteOverride[]): Map<string, RouteOverride> {
  const m = new Map<string, RouteOverride>();
  for (const r of routes) m.set(r.edge_id, r);
  return m;
}

function applyToItem(it: BaseItem, r: RouteOverride, annotate: boolean): BaseItem {
  const geom = { ...(it.geom || {}), d: r.d };
  const data = annotate
    ? { ...(it.data || {}), route: { edge_id: r.edge_id, via: r.via ?? null } }
    : (it.data || {});

  return { ...it, geom, data };
}

export function applyRouteOverrides(base: VizIR, routes: RouteOverride[], opts: ApplyRoutesOptions = {}): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });

  const layerIds = opts.layer_ids ?? null;
  const matchItemId = opts.match_on_item_id ?? true;
  const matchDataId = opts.match_on_data_edge_id ?? true;
  const annotate = opts.annotate ?? true;

  const rmap = toMap(routes);

  const layers: Layer[] = (ir.layers || []).map(layer => {
    if (layerIds && layerIds.length && !layerIds.includes(layer.id)) return layer;

    const items = (layer.items || []).map(it => {
      let key: string | null = null;

      if (matchItemId && it.id && rmap.has(it.id)) key = it.id;

      if (!key && matchDataId && it.data && (it.data as { edge_id?: unknown }).edge_id) {
        const edgeId = String((it.data as { edge_id?: unknown }).edge_id);
        if (rmap.has(edgeId)) key = edgeId;
      }

      if (!key) return it;

      const r = rmap.get(key);
      if (!r) return it;
      return applyToItem(it, r, annotate);
    });

    return { ...layer, items };
  });

  return { ...ir, layers };
}

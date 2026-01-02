import type { VizIR } from "../types/vizir";
import type { ViewState, LODPolicy } from "./types";
import type { LayoutIR } from "../layout/types";
import { applyLOD } from "./applyLOD";
import { emitMacroEdges } from "./macroEdges";
import { mergeVizIR } from "../emit/compose";

export function applyLODWithMacros(
  base: VizIR,
  view: ViewState,
  policy: LODPolicy,
  layout?: LayoutIR | null,
  entityTypeMap?: Record<string, string> | null
): VizIR {
  const lod = applyLOD(base, view, policy);
  const edgeMode = (lod.meta as { lod?: { edge_mode?: string } } | undefined)?.lod?.edge_mode ?? "full";

  if (edgeMode !== "macro") return lod;

  const stripped: VizIR = {
    ...lod,
    layers: (lod.layers || []).map(layer => ({
      ...layer,
      items: (layer.items || []).filter(it => it.type !== "edge")
    }))
  };

  const macro = emitMacroEdges(lod, { layer_id: "overlay_macro", z: 25 }, layout, entityTypeMap);
  return mergeVizIR(stripped, [macro], "lod+macro");
}

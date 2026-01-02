import type { VizIR } from "../types/vizir";
import type { ViewState, LODPolicy } from "./types";
import type { LayoutIR } from "../layout/types";
import { applyLOD } from "./applyLOD";
import { emitMacroEdges } from "./macroEdges";
import { emitSupernodes } from "./supernodes";
import { mergeVizIR } from "../emit/compose";

export function applyLODWithMacroGraph(
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
    layers: (lod.layers || []).map(layer => {
      if (layer.id === "layout_guides" || layer.id === "layout_bus") return layer;
      return {
        ...layer,
        items: (layer.items || []).filter(
          it => it.type !== "edge" && it.type !== "node" && it.type !== "circle" && it.type !== "text"
        )
      };
    })
  };

  const supernodes = emitSupernodes(lod, { show_labels: true, min_members: 3 }, layout, entityTypeMap);
  const macro = emitMacroEdges(lod, { layer_id: "overlay_macro", z: 25 }, layout, entityTypeMap);

  return mergeVizIR(stripped, [supernodes, macro], "lod+macro_graph");
}

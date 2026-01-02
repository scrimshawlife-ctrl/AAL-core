import type { LODPolicy } from "./types";

export function defaultLODPolicy(): LODPolicy {
  return {
    schema: "LODPolicy.v0.1",
    rules: [
      {
        id: "far_macro",
        when: { zoom_lte: 0.45, max_items_gte: 400 },
        actions: { labels: "none", edge_mode: "macro", hide_item_types: ["heatcell"] }
      },
      {
        id: "zoomed_out_hide_trends",
        when: { zoom_lte: 0.7, max_items_gte: 1500 },
        actions: {
          hide_layers: ["trend.*"],
          hide_item_types: ["heatcell"],
          labels: "none",
          edge_mode: "bundled"
        }
      },
      {
        id: "mid_hide_labels",
        when: { zoom_lte: 1.0, max_items_gte: 800 },
        actions: {
          labels: "compact",
          edge_mode: "bundled"
        }
      },
      {
        id: "zoomed_in_full",
        when: { zoom_gte: 1.01 },
        actions: {
          labels: "all",
          edge_mode: "full"
        }
      }
    ]
  };
}

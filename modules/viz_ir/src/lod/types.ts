export type ViewState = {
  schema: "ViewState.v0.1";
  zoom: number;
  pan_x: number;
  pan_y: number;
  viewport_w: number;
  viewport_h: number;
};

export type LODPolicy = {
  schema: "LODPolicy.v0.1";
  rules: Array<{
    id: string;
    when: {
      zoom_lte?: number | null;
      zoom_gte?: number | null;
      max_items_gte?: number | null;
    };
    actions: {
      hide_layers?: string[] | null;
      hide_item_types?: string[] | null;
      labels?: "all" | "none" | "compact";
      edge_mode?: "full" | "bundled" | "macro";
    };
  }>;
};

export const VIZ_LAYER_ORDER = [
  "base_scene",
  "overlay_heatmap",
  "overlay_transfer",
  "overlay_trendpack"
] as const;

export type VizLayerId = typeof VIZ_LAYER_ORDER[number];

export function isKnownLayerId(id: string): id is VizLayerId {
  return (VIZ_LAYER_ORDER as readonly string[]).includes(id);
}

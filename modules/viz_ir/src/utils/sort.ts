import type { Layer, BaseItem } from "../types/vizir";

export function sortLayersDeterministic(layers: Layer[]): Layer[] {
  return layers.slice().sort((a, b) => {
    if (a.z !== b.z) return a.z - b.z;
    return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
  });
}

export function sortItemsDeterministic(items: BaseItem[]): BaseItem[] {
  return items.slice().sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

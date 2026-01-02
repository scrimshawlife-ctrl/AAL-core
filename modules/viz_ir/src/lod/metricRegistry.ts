import type { MetricRegistry, MetricDescriptor } from "./metricRegistryTypes";

export type MetricRegistryIndex = {
  byKey: Record<string, MetricDescriptor>;
  byTag: Record<string, string[]>;
};

function stableSort(xs: string[]): string[] {
  return xs.slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

export function indexRegistry(reg: MetricRegistry | null | undefined): MetricRegistryIndex {
  const byKey: Record<string, MetricDescriptor> = {};
  const byTag: Record<string, string[]> = {};

  if (!reg) return { byKey, byTag };

  const descs = (reg.descriptors || []).slice().sort((a, b) => (a.key < b.key ? -1 : a.key > b.key ? 1 : 0));

  for (const d of descs) {
    byKey[d.key] = d;
    const tags = (d.tags || []).slice().sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    for (const t of tags) {
      byTag[t] = byTag[t] || [];
      byTag[t].push(d.key);
    }
  }

  for (const t of Object.keys(byTag)) byTag[t] = stableSort(byTag[t]);
  return { byKey, byTag };
}

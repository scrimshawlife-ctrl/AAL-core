export type MetricDescriptor = {
  schema: "MetricDescriptor.v0.1";
  key: string;
  value_type: "scalar" | "vector";
  tags?: string[] | null;
  units?: string | null;
  notes?: string | null;
  normalization?: { recommended_op?: "identity" | "clip01" | "minmax" | "log1p" | "sigmoid" | "zscore_if_stats"; min?: number | null; max?: number | null } | null;
  stats_hint?: { min?: number | null; max?: number | null; mean?: number | null; std?: number | null } | null;
  vector_hint?: { length?: number | null; labels?: string[] | null } | null;
};

export type MetricRegistry = {
  schema: "MetricRegistry.v0.1";
  version: string;
  descriptors: MetricDescriptor[];
};

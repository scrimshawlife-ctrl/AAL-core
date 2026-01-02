export type MetricValue =
  | {
      type: "scalar";
      v: number;
      tags?: string[];
      stats?: { min?: number; max?: number; mean?: number; std?: number };
    }
  | {
      type: "vector";
      v: number[];
      tags?: string[];
      stats?: { min?: number; max?: number; mean?: number; std?: number };
    };

export type MetricBindingSpec = {
  schema: "MetricBindingSpec.v0.1";
  defaults?: { R: number; S: number; N: number; K: number; C: number[] };
  channels: {
    R: ChannelRule;
    S: ChannelRule;
    N: ChannelRule;
    K: ChannelRule;
    C: VectorRule;
  };
};

export type Selector = { type: "name" | "pattern" | "tag"; value: string; path?: string | null };

export type Transform = {
  op: "identity" | "clip01" | "minmax" | "log1p" | "sigmoid" | "zscore_if_stats";
  min?: number | null;
  max?: number | null;
};

export type ChannelRule = { candidates: Selector[]; transform?: Transform; fallback?: number };
export type VectorRule = { length: 6; candidates: Selector[]; transform?: Transform; fallback?: number[] };

export type BindingReport = {
  schema: "MetricBindingReport.v0.1";
  resolved: {
    R: Resolved;
    S: Resolved;
    N: Resolved;
    K: Resolved;
    C: Resolved;
  };
};

export type Resolved = {
  metric_key: string | null;
  selector: Selector | null;
  used_fallback: boolean;
  transform: Transform | null;
  notes?: string[] | null;
};

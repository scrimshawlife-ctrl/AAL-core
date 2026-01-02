import type { MetricBindingSpec } from "./metricBindingTypes";

export function defaultMetricBindingSpec(): MetricBindingSpec {
  return {
    schema: "MetricBindingSpec.v0.1",
    defaults: { R: 0.2, S: 0.2, N: 0.2, K: 0.2, C: [0, 0, 0, 0, 0, 0] },
    channels: {
      R: {
        candidates: [
          { type: "name", value: "MSI" },
          { type: "name", value: "RFR" },
          { type: "pattern", value: "resonance.*" }
        ],
        transform: { op: "clip01" },
        fallback: 0.2
      },
      S: {
        candidates: [
          { type: "name", value: "synch.count" },
          { type: "pattern", value: "synch.*" }
        ],
        transform: { op: "minmax", min: 0, max: 50 },
        fallback: 0.2
      },
      N: {
        candidates: [
          { type: "name", value: "lambdaN" },
          { type: "name", value: "novelty" },
          { type: "pattern", value: "novel.*" }
        ],
        transform: { op: "clip01" },
        fallback: 0.2
      },
      K: {
        candidates: [
          { type: "name", value: "Hsigma" },
          { type: "name", value: "confidence" },
          { type: "pattern", value: "stability.*" }
        ],
        transform: { op: "clip01" },
        fallback: 0.2
      },
      C: {
        length: 6,
        candidates: [
          { type: "name", value: "coupling.vec6" },
          { type: "name", value: "ITC.vec6" },
          { type: "pattern", value: "coupling.*" }
        ],
        transform: { op: "clip01" },
        fallback: [0, 0, 0, 0, 0, 0]
      }
    }
  };
}

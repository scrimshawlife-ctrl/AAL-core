import { makeVizPack } from "../src/pack/makeVizPack";
import { hashVizPackPayload } from "../src/pack/hashVizPack";
import { stableStringify } from "../src/utils/stableStringify";
import { sha256Hex } from "../src/utils/sha256";
import { defaultLODPolicy } from "../src/lod/defaultPolicy";
import { defaultMetricBindingSpec } from "../src/lod/defaultMetricBinding";
import { indexRegistry } from "../src/lod/metricRegistry";
import { bindMetricsToGlyphV2 } from "../src/lod/bindMetricsToGlyph.v2";
import { diffVizPacks } from "../src/pack/diff";
import { attachBindingReport } from "../src/pack/attachBindingReport";

function minimalVizIR() {
  return {
    schema: "VizIR.v0.1",
    meta: { title: "test" },
    canvas: { w: 400, h: 240, unit: "px" },
    layers: [
      {
        id: "overlay_supernodes",
        z: 10,
        items: [
          {
            id: "super.lane:core",
            type: "circle",
            style: { fill: "none", stroke: "rgba(0,0,0,0.2)", stroke_w: 2 },
            geom: { cx: 100, cy: 120, r: 30 },
            data: {
              kind: "supernode",
              group_id: "lane:core",
              metrics: {
                MSI: { type: "scalar", v: 0.75, tags: ["resonance"], stats: { min: 0, max: 1 } },
                "synch.count": { type: "scalar", v: 12, tags: ["synch"], stats: { min: 0, max: 50 } },
                "coupling.vec6": { type: "vector", v: [0.2, 0.1, 0.8, 0.0, 0.3, 0.4], tags: ["coupling"] }
              }
            }
          }
        ]
      }
    ]
  };
}

function minimalRegistry() {
  return {
    schema: "MetricRegistry.v0.1",
    version: "test-reg-1",
    descriptors: [
      {
        schema: "MetricDescriptor.v0.1",
        key: "MSI",
        value_type: "scalar",
        tags: ["resonance"],
        normalization: { recommended_op: "clip01" }
      },
      {
        schema: "MetricDescriptor.v0.1",
        key: "synch.count",
        value_type: "scalar",
        tags: ["synch"],
        normalization: { recommended_op: "minmax", min: 0, max: 50 }
      },
      {
        schema: "MetricDescriptor.v0.1",
        key: "coupling.vec6",
        value_type: "vector",
        tags: ["coupling"],
        vector_hint: { length: 6 },
        normalization: { recommended_op: "clip01" }
      }
    ]
  };
}

describe("VizPack determinism", () => {
  test("policy_hash and viz_ir_hash remain stable for identical inputs", () => {
    const viz_ir = minimalVizIR();
    const policy = defaultLODPolicy();
    const binding = defaultMetricBindingSpec();
    const registry = minimalRegistry();

    const pack = makeVizPack({
      id: "golden-1",
      engine: { name: "aal-viz", version: "0.3.0" },
      payload: { viz_ir, lod_policy: policy, binding_spec: binding, metric_registry: registry, renders: { svg: "<svg/>" } },
      provenance: {
        inputs: [{ name: "viz_ir", hash: sha256Hex(stableStringify(viz_ir)) }],
        build: { deterministic: true, seed: "fixed:0", platform: "node" }
      }
    });

    const h1 = hashVizPackPayload(pack);
    const h2 = hashVizPackPayload(pack);

    expect(h1.policy_hash).toBe(h2.policy_hash);
    expect(h1.viz_ir_hash).toBe(h2.viz_ir_hash);
    expect(h1.svg_hash).toBe(h2.svg_hash);
  });

  test("missing metrics -> fallback is explicit in binding report", () => {
    const spec = defaultMetricBindingSpec();
    const regIndex = indexRegistry(minimalRegistry() as any);

    const metrics = {
      "synch.count": { type: "scalar", v: 2, tags: ["synch"], stats: { min: 0, max: 50 } }
    } as any;

    const { channels, report } = bindMetricsToGlyphV2(metrics, spec as any, regIndex);

    expect(channels.R).toBeGreaterThanOrEqual(0);
    expect(channels.R).toBeLessThanOrEqual(1);
    expect(report.resolved.R.used_fallback).toBe(true);
    expect(report.resolved.S.used_fallback).toBe(false);
  });

  test("diff detects rebinds and raises drift risk", () => {
    const base = makeVizPack({
      id: "golden-1",
      engine: { name: "aal-viz", version: "0.3.0" },
      payload: { viz_ir: minimalVizIR(), renders: { svg: "<svg/>" } },
      provenance: { inputs: [], build: { deterministic: true, seed: "fixed:0", platform: "node" } }
    });

    const a = attachBindingReport(base, {
      schema: "MetricBindingReport.v0.1",
      resolved: {
        R: { metric_key: "MSI", selector: { type: "name", value: "MSI" }, used_fallback: false, transform: { op: "clip01" } },
        S: { metric_key: "synch.count", selector: { type: "name", value: "synch.count" }, used_fallback: false, transform: { op: "minmax", min: 0, max: 50 } },
        N: { metric_key: null, selector: null, used_fallback: true, transform: null, notes: ["fallback"] },
        K: { metric_key: null, selector: null, used_fallback: true, transform: null, notes: ["fallback"] },
        C: { metric_key: "coupling.vec6", selector: { type: "name", value: "coupling.vec6" }, used_fallback: false, transform: { op: "clip01" } }
      }
    } as any);

    const b = attachBindingReport({ ...base, id: "golden-2" }, {
      schema: "MetricBindingReport.v0.1",
      resolved: {
        ...((a as any).payload.binding_report.resolved),
        R: { metric_key: "RFR", selector: { type: "name", value: "RFR" }, used_fallback: false, transform: { op: "clip01" } }
      }
    } as any);

    const d = diffVizPacks(a as any, b as any);
    expect(d.binding.channels.R.metric_key.changed).toBe(true);
    expect(d.drift.risk).toBeGreaterThan(0.2);
  });
});

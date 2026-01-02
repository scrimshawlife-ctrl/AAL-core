import type { VizPack } from "./types";
import { stableStringify } from "../utils/stableStringify";
import { sha256Hex } from "../utils/sha256";

export type MakeVizPackArgs = {
  id: string;
  engine: { name: string; version: string };
  payload: VizPack["payload"];
  provenance: VizPack["provenance"];
  integrity?: Partial<VizPack["integrity"]>;
};

export function makeVizPack(args: MakeVizPackArgs): VizPack {
  const created_at = new Date().toISOString();

  const viz_ir_hash = args.payload?.viz_ir ? sha256Hex(stableStringify(args.payload.viz_ir)) : null;
  const layout_ir_hash = args.payload?.layout_ir ? sha256Hex(stableStringify(args.payload.layout_ir)) : null;

  const policyComposite = {
    lod_policy: args.payload?.lod_policy ?? null,
    binding_spec: args.payload?.binding_spec ?? null,
    metric_registry: args.payload?.metric_registry
      ? { schema: args.payload.metric_registry.schema, version: args.payload.metric_registry.version }
      : null
  };
  const policy_hash = sha256Hex(stableStringify(policyComposite));

  return {
    schema: "VizPack.v0.1",
    id: args.id,
    created_at,
    engine: args.engine,
    payload: args.payload,
    integrity: {
      viz_ir_hash,
      layout_ir_hash,
      policy_hash,
      binding_report_hash: args.integrity?.binding_report_hash ?? null
    },
    provenance: args.provenance
  };
}

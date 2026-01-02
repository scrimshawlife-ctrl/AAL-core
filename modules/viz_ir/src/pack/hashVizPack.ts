import type { VizPack } from "./types";
import { stableStringify } from "../utils/stableStringify";
import { sha256Hex } from "../utils/sha256";

export function hashSvg(svg: string | null | undefined): string | null {
  if (!svg) return null;
  return sha256Hex(svg);
}

export function hashVizPackPayload(pack: VizPack): {
  viz_ir_hash: string | null;
  policy_hash: string | null;
  svg_hash: string | null;
} {
  const viz = pack.payload?.viz_ir ? sha256Hex(stableStringify(pack.payload.viz_ir)) : null;

  const policyComposite = {
    lod_policy: pack.payload?.lod_policy ?? null,
    binding_spec: pack.payload?.binding_spec ?? null,
    metric_registry: pack.payload?.metric_registry
      ? { schema: pack.payload.metric_registry.schema, version: pack.payload.metric_registry.version }
      : null
  };

  const policy = sha256Hex(stableStringify(policyComposite));
  const svg = hashSvg(pack.payload?.renders?.svg ?? null);

  return { viz_ir_hash: viz, policy_hash: policy, svg_hash: svg };
}

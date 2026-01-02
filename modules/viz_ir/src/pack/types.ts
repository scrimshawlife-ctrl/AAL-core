export type VizPack = {
  schema: "VizPack.v0.1";
  id: string;
  created_at: string;
  engine: { name: string; version: string };
  payload: {
    viz_ir: any;
    layout_ir?: any | null;
    view_state?: any | null;
    lod_policy?: any | null;
    binding_spec?: any | null;
    metric_registry?: any | null;
    frame_pack?: any | null;
    renders?: { svg?: string | null; png_ref?: string | null } | null;
  };
  integrity?: {
    binding_report_hash?: string | null;
    viz_ir_hash?: string | null;
    layout_ir_hash?: string | null;
    policy_hash?: string | null;
  };
  provenance: {
    inputs: Array<{ name: string; hash: string; notes?: string | null }>;
    build: { deterministic: boolean; seed: string; platform?: string | null };
  };
};

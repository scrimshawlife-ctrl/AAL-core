import type { TimelineIR } from "./timeline";

export type FramePackMode = "svg_inline" | "svg_ref" | "vizir_inline";

export type FramePack = {
  schema: "FramePack.v0.1";
  meta: {
    title: string;
    run_id?: string | null;
    provenance?: Record<string, unknown> | null;
    [k: string]: unknown;
  };
  timeline: TimelineIR;
  frames: {
    mode: FramePackMode;
    count: number;
    hash_alg: "sha256";
    hashes: string[];
    svg_inline?: string[] | null;
    svg_ref?: Array<{ path: string; mime?: string | null }> | null;
    vizir_inline?: Array<Record<string, unknown>> | null;
  };
};

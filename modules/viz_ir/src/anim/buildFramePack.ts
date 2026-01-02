import crypto from "node:crypto";

import type { VizIR } from "../types/vizir";
import type { TimelineIR } from "./timeline";
import type { FramePack, FramePackMode } from "./framePack";
import { normalizeVizIR, stableStringify } from "../utils/normalize";
import { vizIrToSvg } from "../render/toSvg";

export type BuildFramePackOptions = {
  title: string;
  run_id?: string | null;
  provenance?: Record<string, unknown> | null;
  mode: FramePackMode;
  timeline: TimelineIR;
  frames: VizIR[];
  svg_paths?: string[];
};

function sha256(s: string): string {
  return crypto.createHash("sha256").update(s, "utf8").digest("hex");
}

export function buildFramePack(opts: BuildFramePackOptions): FramePack {
  const framesN = opts.frames.map(frame => normalizeVizIR(frame, { round: 6, sort_keys: true }));
  const hashes: string[] = [];

  if (opts.mode === "vizir_inline") {
    for (const frame of framesN) {
      const canon = stableStringify(frame);
      hashes.push(sha256(canon));
    }
    return {
      schema: "FramePack.v0.1",
      meta: { title: opts.title, run_id: opts.run_id ?? null, provenance: opts.provenance ?? null },
      timeline: opts.timeline,
      frames: {
        mode: "vizir_inline",
        count: framesN.length,
        hash_alg: "sha256",
        hashes,
        vizir_inline: framesN as Array<Record<string, unknown>>
      }
    };
  }

  const svgFrames: string[] = [];
  for (const frame of framesN) {
    const svg = vizIrToSvg(frame);
    svgFrames.push(svg);
    hashes.push(sha256(svg));
  }

  if (opts.mode === "svg_inline") {
    return {
      schema: "FramePack.v0.1",
      meta: { title: opts.title, run_id: opts.run_id ?? null, provenance: opts.provenance ?? null },
      timeline: opts.timeline,
      frames: {
        mode: "svg_inline",
        count: svgFrames.length,
        hash_alg: "sha256",
        hashes,
        svg_inline: svgFrames
      }
    };
  }

  const paths = opts.svg_paths ?? [];
  if (paths.length !== svgFrames.length) {
    throw new Error(`svg_ref mode requires svg_paths length=${svgFrames.length}, got ${paths.length}`);
  }

  return {
    schema: "FramePack.v0.1",
    meta: { title: opts.title, run_id: opts.run_id ?? null, provenance: opts.provenance ?? null },
    timeline: opts.timeline,
    frames: {
      mode: "svg_ref",
      count: svgFrames.length,
      hash_alg: "sha256",
      hashes,
      svg_ref: paths.map(path => ({ path, mime: "image/svg+xml" }))
    }
  };
}

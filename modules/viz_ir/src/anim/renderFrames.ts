import type { VizIR } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";
import { vizIrToSvg } from "../render/toSvg";

export type FrameMode = "vizir" | "svg";

export type RenderFramesOptions = {
  frame_count: number;
  mode: FrameMode;
  frameTransform?: (base: VizIR, frameIndex: number, frameCount: number) => VizIR;
};

export function renderFrames(base: VizIR, opts: RenderFramesOptions): Array<VizIR | string> {
  const nbase = normalizeVizIR(base, { round: 6, sort_keys: false });
  const out: Array<VizIR | string> = [];
  const count = Math.max(1, opts.frame_count);

  for (let i = 0; i < count; i += 1) {
    const frameIR = opts.frameTransform ? opts.frameTransform(nbase, i, count) : nbase;
    const nframe = normalizeVizIR(frameIR, { round: 6, sort_keys: false });

    if (opts.mode === "vizir") out.push(nframe);
    else out.push(vizIrToSvg(nframe));
  }

  return out;
}

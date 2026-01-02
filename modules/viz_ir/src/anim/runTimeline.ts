import type { TimelineIR } from "./timeline";

export type RunTimeline = {
  timeline: TimelineIR;
  run_ids: string[];
  frame_to_run: Array<{ frame: number; run_id: string; run_index: number }>;
  run_to_frame: Record<string, number>;
};

export type BuildRunTimelineOptions = {
  fps?: number;
  frames_per_run?: number;
  title?: string;
};

export function buildRunTimeline(runIds: string[], opts: BuildRunTimelineOptions = {}): RunTimeline {
  const fps = opts.fps ?? 30;
  const framesPerRun = Math.max(1, opts.frames_per_run ?? 6);
  const run_ids = runIds.slice();

  const count = Math.max(1, run_ids.length * framesPerRun);

  const frame_to_run: Array<{ frame: number; run_id: string; run_index: number }> = [];
  const run_to_frame: Record<string, number> = {};

  let frame = 0;
  for (let i = 0; i < run_ids.length; i += 1) {
    run_to_frame[run_ids[i]] = frame;
    for (let k = 0; k < framesPerRun; k += 1) {
      frame_to_run.push({ frame, run_id: run_ids[i], run_index: i });
      frame += 1;
    }
  }

  const timeline: TimelineIR = {
    schema: "TimelineIR.v0.1",
    frames: { count, fps },
    cursor: { mode: "index", index: 0 },
    segments: run_ids.map((rid, i) => ({
      id: `run.${i}`,
      start: i * framesPerRun,
      end: (i + 1) * framesPerRun - 1,
      label: rid
    }))
  };

  return { timeline, run_ids, frame_to_run, run_to_frame };
}

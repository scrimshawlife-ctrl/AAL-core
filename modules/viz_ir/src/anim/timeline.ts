export type TimelineSchema = "TimelineIR.v0.1";

export type TimelineIR = {
  schema: TimelineSchema;
  frames: { count: number; fps: number };
  cursor: { mode: "index" | "time"; index?: number | null; time_s?: number | null };
  segments?: Array<{ id: string; start: number; end: number; label?: string | null }>;
};

export type Easing = "linear" | "step" | "smoothstep";

export function ease(t01: number, mode: Easing): number {
  const t = Math.max(0, Math.min(1, t01));
  if (mode === "step") return t >= 1 ? 1 : 0;
  if (mode === "smoothstep") return t * t * (3 - 2 * t);
  return t;
}

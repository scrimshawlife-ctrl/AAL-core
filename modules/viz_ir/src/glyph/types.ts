export type GlyphSpec = {
  schema: "GlyphSpec.v0.1";
  id: string;
  cx: number;
  cy: number;
  size: number;
  channels: {
    R: number;
    C: number[];
    S: number;
    N: number;
    K: number;
  };
  label?: string | null;
  data?: Record<string, unknown> | null;
};

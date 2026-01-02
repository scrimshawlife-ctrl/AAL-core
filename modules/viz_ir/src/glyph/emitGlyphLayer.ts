import type { VizIR, Layer, BaseItem } from "../types/vizir";
import { normalizeVizIR } from "../utils/normalize";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import type { GlyphSpec } from "./types";
import { resonanceGlyphItems } from "./render";

export type GlyphAttachOptions = {
  layer_id?: string;
  z?: number;
  size?: number;
  attach_kind?: "supernode" | "node";
  show_labels?: boolean;
  report_sink?: (id: string, report: Record<string, unknown>) => void;
};

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

export type GlyphChannelFn = (
  it: BaseItem,
  ir: VizIR
) => { R: number; C: number[]; S: number; N: number; K: number; report?: Record<string, unknown> | null };

export function emitResonanceGlyphLayer(
  base: VizIR,
  channelFn: GlyphChannelFn,
  opts: GlyphAttachOptions = {}
): VizIR {
  const ir = normalizeVizIR(base, { round: 6, sort_keys: false });

  const attachKind = opts.attach_kind ?? "supernode";
  const size = opts.size ?? 14;

  const glyphItems: BaseItem[] = [];

  for (const layer of ir.layers || []) {
    for (const it of layer.items || []) {
      const kind = (it.data as { kind?: unknown } | undefined)?.kind ?? null;

      if (attachKind === "supernode" && kind !== "supernode") continue;
      if (attachKind === "node" && it.type !== "node") continue;

      const g = it.geom as { cx?: number; cy?: number; x?: number; y?: number } | undefined;
      const cx = typeof g?.cx === "number" ? g.cx : typeof g?.x === "number" ? g.x : null;
      const cy = typeof g?.cy === "number" ? g.cy : typeof g?.y === "number" ? g.y : null;
      if (cx == null || cy == null) continue;

      const ch = channelFn(it, ir);
      const C = (ch.C || []).slice(0, 6).map(clamp01);
      while (C.length < 6) C.push(0);

      const label = opts.show_labels
        ? kind === "supernode"
          ? String((it.data as { group_id?: unknown } | undefined)?.group_id ?? "")
          : String((it.data as { entity_id?: unknown } | undefined)?.entity_id ?? "")
        : null;

      const spec: GlyphSpec = {
        schema: "GlyphSpec.v0.1",
        id: `glyph.${it.id}`,
        cx,
        cy,
        size,
        channels: {
          R: clamp01(ch.R),
          C,
          S: clamp01(ch.S),
          N: clamp01(ch.N),
          K: clamp01(ch.K)
        },
        label,
        data: { attach_to: it.id, kind: "resonance_glyph" }
      };

      if (opts.report_sink && ch.report) {
        opts.report_sink(spec.id, ch.report);
      }

      glyphItems.push(...resonanceGlyphItems(spec));
    }
  }

  const layer: Layer = {
    id: opts.layer_id ?? "overlay_glyphs",
    z: opts.z ?? 40,
    items: sortItemsDeterministic(glyphItems)
  };

  return {
    schema: "VizIR.v0.1",
    meta: { ...(ir.meta || {}), glyphs: { schema: "GlyphSpec.v0.1", attach_kind: attachKind } },
    canvas: ir.canvas,
    layers: sortLayersDeterministic([layer])
  };
}

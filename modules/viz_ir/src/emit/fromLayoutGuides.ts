import type { VizIR, Layer, BaseItem, Style } from "../types/vizir";
import type { LayoutIR } from "../layout/types";
import { sortItemsDeterministic, sortLayersDeterministic } from "../utils/sort";
import { roundN } from "../utils/round";

export type LayoutGuidesOptions = {
  title?: string;
  layer_id?: string;
  z?: number;

  // lane band style
  band_fill?: string;
  band_stroke?: string;
  band_stroke_w?: number;

  // label style
  label_fill?: string;
  label_font?: string;
  label_size?: number;
  label_pad_x?: number;
  label_pad_y?: number;

  // spine / bus
  show_spine?: boolean;
  spine_x?: number;
  spine_stroke?: string;
  spine_stroke_w?: number;
  tick_every?: number;
  tick_len?: number;
};

function monoStyle(opts: LayoutGuidesOptions): Style {
  return {
    font_family: opts.label_font ?? "ui-monospace, Menlo, Consolas, monospace",
    font_size: opts.label_size ?? 12,
    fill: opts.label_fill ?? "rgba(0,0,0,0.60)"
  };
}

export function vizIrFromLayoutGuides(layout: LayoutIR, opts: LayoutGuidesOptions = {}): VizIR {
  const w = layout.canvas.w;
  const h = layout.canvas.h;
  const unit: "px" = "px";

  const layerId = opts.layer_id ?? "layout_guides";
  const z = opts.z ?? 5;

  const items: BaseItem[] = [];

  const lanes = (layout.lanes || []).slice().sort((a, b) => (a.y < b.y ? -1 : a.y > b.y ? 1 : 0));

  const title = opts.title ?? layout.meta?.title ?? null;
  if (title) {
    items.push({
      id: "lg.title",
      type: "text",
      style: { ...monoStyle(opts), font_size: (opts.label_size ?? 12) + 2, fill: "rgba(0,0,0,0.75)" },
      geom: { x: 20, y: 26, text: title },
      data: { kind: "layout_title" }
    });
  }

  const bandFill = opts.band_fill ?? "rgba(0,0,0,0.02)";
  const bandStroke = opts.band_stroke ?? "rgba(0,0,0,0.08)";
  const bandSW = opts.band_stroke_w ?? 1;

  const lpX = opts.label_pad_x ?? 18;
  const lpY = opts.label_pad_y ?? 18;

  for (const lane of lanes) {
    items.push({
      id: `lg.band.${lane.id}`,
      type: "rect",
      style: { fill: bandFill, stroke: bandStroke, stroke_w: bandSW },
      geom: { x: 0, y: lane.y, w, h: lane.h },
      data: { kind: "lane_band", lane_id: lane.id, label: lane.label ?? null }
    });

    items.push({
      id: `lg.label.${lane.id}`,
      type: "text",
      style: { ...monoStyle(opts), text_anchor: "start" },
      geom: { x: lpX, y: lane.y + lpY, text: lane.label ?? lane.id },
      data: { kind: "lane_label", lane_id: lane.id }
    });

    items.push({
      id: `lg.sep.${lane.id}`,
      type: "line",
      style: { stroke: "rgba(0,0,0,0.06)", stroke_w: 1 },
      geom: { x1: 0, y1: lane.y + lane.h, x2: w, y2: lane.y + lane.h },
      data: { kind: "lane_sep", lane_id: lane.id }
    });
  }

  const showSpine = opts.show_spine ?? true;
  if (showSpine) {
    const sx = opts.spine_x ?? 60;
    const spineStroke = opts.spine_stroke ?? "rgba(0,0,0,0.10)";
    const spineSW = opts.spine_stroke_w ?? 2;

    items.push({
      id: "lg.spine",
      type: "line",
      style: { stroke: spineStroke, stroke_w: spineSW },
      geom: { x1: sx, y1: 0, x2: sx, y2: h },
      data: { kind: "spine" }
    });

    const tickEvery = Math.max(1, opts.tick_every ?? 1);
    const tickLen = opts.tick_len ?? 10;

    for (let i = 0; i < lanes.length; i += 1) {
      if (i % tickEvery !== 0) continue;
      const lane = lanes[i];
      const mid = lane.y + lane.h / 2;
      items.push({
        id: `lg.tick.${i}`,
        type: "line",
        style: { stroke: spineStroke, stroke_w: 2 },
        geom: { x1: sx, y1: mid, x2: sx + tickLen, y2: mid },
        data: { kind: "spine_tick", lane_id: lane.id }
      });
    }
  }

  const layer: Layer = {
    id: layerId,
    z,
    items: sortItemsDeterministic(items).map(it => ({
      ...it,
      geom: roundN(it.geom, 6) as Record<string, unknown>
    }))
  };

  return {
    schema: "VizIR.v0.1",
    meta: { title: title ?? "layout_guides", provenance: layout.meta?.provenance ?? null },
    canvas: { w, h, unit },
    layers: sortLayersDeterministic([layer])
  };
}

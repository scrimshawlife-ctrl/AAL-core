import type { VizIR, Layer, BaseItem, Style } from "../types/vizir";
import { sortLayersDeterministic, sortItemsDeterministic } from "../utils/sort";
import { roundN } from "../utils/round";
import { normalizeVizIR } from "../utils/normalize";
import { renderFallback } from "./fallback";

function esc(s: unknown): string {
  const str = String(s ?? "");
  return str
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;");
}

function styleToAttrs(st?: Style): string {
  if (!st) return "";
  const parts: string[] = [];
  if (st.stroke != null) parts.push(`stroke="${esc(st.stroke)}"`);
  if (st.fill != null) parts.push(`fill="${esc(st.fill)}"`);
  if (st.stroke_w != null) parts.push(`stroke-width="${esc(st.stroke_w)}"`);
  if (st.opacity != null) parts.push(`opacity="${esc(st.opacity)}"`);
  if (st.dash != null) parts.push(`stroke-dasharray="${esc(st.dash)}"`);
  if (st.font_size != null) parts.push(`font-size="${esc(st.font_size)}"`);
  if (st.font_family != null) parts.push(`font-family="${esc(st.font_family)}"`);
  if (st.text_anchor != null) parts.push(`text-anchor="${esc(st.text_anchor)}"`);
  return parts.length ? " " + parts.join(" ") : "";
}

function dataAttrs(data?: Record<string, unknown>): string {
  if (!data) return "";
  const keys = Object.keys(data).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
  const parts: string[] = [];
  for (const k of keys) {
    const v = data[k];
    if (v === undefined) continue;
    const val = typeof v === "string" ? v : JSON.stringify(v);
    parts.push(`data-${esc(k)}="${esc(val)}"`);
  }
  return parts.length ? " " + parts.join(" ") : "";
}

function a11yBlock(a11y?: { title?: string | null; desc?: string | null }): string {
  if (!a11y) return "";
  const t = a11y.title ? `<title>${esc(a11y.title)}</title>` : "";
  const d = a11y.desc ? `<desc>${esc(a11y.desc)}</desc>` : "";
  return (t || d) ? (t + d) : "";
}

function renderItem(it: BaseItem): string {
  const style = styleToAttrs(it.style);
  const data = dataAttrs(it.data);
  const a11y = a11yBlock(it.a11y);
  const geom = roundN(it.geom, 6) as Record<string, unknown>;

  switch (it.type) {
    case "rect": {
      const x = esc(geom.x ?? 0);
      const y = esc(geom.y ?? 0);
      const w = esc(geom.w ?? geom.width ?? 0);
      const h = esc(geom.h ?? geom.height ?? 0);
      const rx = geom.rx != null ? ` rx="${esc(geom.rx)}"` : "";
      const ry = geom.ry != null ? ` ry="${esc(geom.ry)}"` : "";
      return `<rect id="${esc(it.id)}"${style}${data} x="${x}" y="${y}" width="${w}" height="${h}"${rx}${ry}>${a11y}</rect>`;
    }
    case "circle": {
      const cx = esc(geom.cx ?? 0);
      const cy = esc(geom.cy ?? 0);
      const r = esc(geom.r ?? 0);
      return `<circle id="${esc(it.id)}"${style}${data} cx="${cx}" cy="${cy}" r="${r}">${a11y}</circle>`;
    }
    case "line": {
      const x1 = esc(geom.x1 ?? 0);
      const y1 = esc(geom.y1 ?? 0);
      const x2 = esc(geom.x2 ?? 0);
      const y2 = esc(geom.y2 ?? 0);
      return `<line id="${esc(it.id)}"${style}${data} x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">${a11y}</line>`;
    }
    case "path": {
      const d = esc(geom.d ?? "");
      return `<path id="${esc(it.id)}"${style}${data} d="${d}">${a11y}</path>`;
    }
    case "text": {
      const x = esc(geom.x ?? 0);
      const y = esc(geom.y ?? 0);
      const txt = esc(geom.text ?? "");
      return `<text id="${esc(it.id)}"${style}${data} x="${x}" y="${y}">${a11y}${txt}</text>`;
    }
    case "group": {
      const items = Array.isArray((it as BaseItem).items) ? ((it as BaseItem).items as BaseItem[]) : [];
      const inner = sortItemsDeterministic(items).map(renderItem).join("");
      return `<g id="${esc(it.id)}"${style}${data}>${a11y}${inner}</g>`;
    }
    case "node": {
      const cx = esc(geom.cx ?? 0);
      const cy = esc(geom.cy ?? 0);
      const r = esc(geom.r ?? 4);
      const label = geom.label != null ? String(geom.label) : null;

      const circ = `<circle id="${esc(it.id)}"${style}${data} cx="${cx}" cy="${cy}" r="${r}">${a11y}</circle>`;
      if (!label) return circ;

      const tx = esc(geom.lx ?? geom.cx ?? 0);
      const ty = esc(geom.ly ?? (typeof geom.cy === "number" ? (geom.cy as number) + 12 : 12));
      const tstyle = styleToAttrs({
        ...(it.style || {}),
        fill: it.style?.stroke ?? "#000",
        stroke: null,
        font_size: it.style?.font_size ?? 10
      });
      const text = `<text id="${esc(it.id)}.label"${tstyle}${data} x="${tx}" y="${ty}">${esc(label)}</text>`;
      return `<g id="${esc(it.id)}.g">${circ}${text}</g>`;
    }
    case "edge": {
      if (geom.d != null) {
        const d = esc(geom.d);
        return `<path id="${esc(it.id)}"${style}${data} d="${d}">${a11y}</path>`;
      }
      const x1 = esc(geom.x1 ?? 0);
      const y1 = esc(geom.y1 ?? 0);
      const x2 = esc(geom.x2 ?? 0);
      const y2 = esc(geom.y2 ?? 0);
      return `<line id="${esc(it.id)}"${style}${data} x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">${a11y}</line>`;
    }
    case "heatcell": {
      const x = esc(geom.x ?? 0);
      const y = esc(geom.y ?? 0);
      const w = esc(geom.w ?? 0);
      const h = esc(geom.h ?? 0);
      return `<rect id="${esc(it.id)}"${style}${data} x="${x}" y="${y}" width="${w}" height="${h}">${a11y}</rect>`;
    }
    default:
      return renderFallback(it);
  }
}

function renderLayer(layer: Layer): string {
  const opacity = layer.opacity != null ? ` opacity="${esc(layer.opacity)}"` : "";
  const items = sortItemsDeterministic(layer.items).map(renderItem).join("");
  return `<g id="${esc(layer.id)}"${opacity}>${items}</g>`;
}

export function vizIrToSvg(ir: VizIR): string {
  const nir = normalizeVizIR(ir, { round: 6, sort_keys: false });
  const w = nir.canvas.w;
  const h = nir.canvas.h;

  const prov = nir.meta?.provenance ? esc(JSON.stringify(nir.meta.provenance)) : "";
  const comments =
    `<!-- aal-viz-ir: ${esc(nir.schema)} -->` +
    (prov ? `<!-- provenance: ${prov} -->` : "");

  const layers = sortLayersDeterministic(nir.layers).map(renderLayer).join("");

  return [
    comments,
    `<svg xmlns="http://www.w3.org/2000/svg" width="${esc(w)}" height="${esc(h)}" viewBox="0 0 ${esc(w)} ${esc(h)}">`,
    `<g id="viz_root">`,
    layers,
    `</g>`,
    `</svg>`
  ].join("");
}

import type { BaseItem } from "../types/vizir";

export function renderFallback(it: BaseItem): string {
  const id = it.id.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  return `<g id="${id}">
    <line x1="0" y1="0" x2="10" y2="10" stroke="rgba(0,0,0,0.35)" stroke-width="1"/>
    <line x1="10" y1="0" x2="0" y2="10" stroke="rgba(0,0,0,0.35)" stroke-width="1"/>
  </g>`;
}

import type { LayoutIR } from "../layout/types";

export type GroupBy = "lane" | "entity_type";

export type GroupInfo = {
  group_id: string;
  label: string;
  ax: number;
  ay: number;
};

export function groupKey(
  entityId: string,
  layout?: LayoutIR | null,
  entityTypeMap?: Record<string, string> | null
): string {
  if (layout?.nodes) {
    const n = layout.nodes.find(x => x.entity_id === entityId);
    if (n?.lane) return `lane:${n.lane}`;
  }
  const t = entityTypeMap?.[entityId];
  if (t) return `type:${t}`;
  const p = entityId.includes(".") ? entityId.split(".")[0] : entityId;
  return `pfx:${p}`;
}

export function buildGroupAnchors(layout?: LayoutIR | null): Record<string, GroupInfo> {
  const out: Record<string, GroupInfo> = {};
  if (!layout) return out;

  const lanes = (layout.lanes || []).slice();
  for (const lane of lanes) {
    const gid = `lane:${lane.id}`;
    out[gid] = {
      group_id: gid,
      label: lane.label ?? lane.id,
      ax: 60,
      ay: lane.y + lane.h / 2
    };
  }
  return out;
}

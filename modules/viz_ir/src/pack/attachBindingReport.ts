import type { VizPack } from "./types";
import type { BindingReport } from "../lod/metricBindingTypes";
import { stableStringify } from "../utils/stableStringify";
import { sha256Hex } from "../utils/sha256";

export function attachBindingReport(pack: VizPack, report: BindingReport): VizPack {
  const hash = sha256Hex(stableStringify(report));
  return {
    ...pack,
    payload: { ...(pack.payload as VizPack["payload"]), binding_report: report },
    integrity: { ...(pack.integrity || {}), binding_report_hash: hash }
  };
}

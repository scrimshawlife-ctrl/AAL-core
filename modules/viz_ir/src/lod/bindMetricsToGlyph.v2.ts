import type { MetricValue, MetricBindingSpec, Transform, Selector, BindingReport, Resolved } from "./metricBindingTypes";
import type { MetricRegistryIndex } from "./metricRegistry";

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function sigmoid(x: number): number {
  return 1 / (1 + Math.exp(-x));
}

function matchPattern(key: string, pattern: string): boolean {
  if (pattern.endsWith(".*")) return key.startsWith(pattern.slice(0, -2));
  return key === pattern;
}

function applyTransformScalar(v: number, t?: Transform, stats?: { mean?: number; std?: number } | null): number {
  if (!t) return clamp01(v);

  if (t.op === "zscore_if_stats") {
    const mean = stats?.mean;
    const std = stats?.std;
    if (typeof mean === "number" && typeof std === "number" && std !== 0) {
      const z = (v - mean) / std;
      return clamp01(sigmoid(z));
    }
    return clamp01(v);
  }

  if (t.op === "identity") return clamp01(v);
  if (t.op === "clip01") return clamp01(v);
  if (t.op === "log1p") return clamp01(Math.log1p(Math.max(0, v)));
  if (t.op === "sigmoid") return clamp01(sigmoid(v));
  if (t.op === "minmax") {
    const mn = typeof t.min === "number" ? t.min : 0;
    const mx = typeof t.max === "number" ? t.max : 1;
    if (mx === mn) return 0;
    return clamp01((v - mn) / (mx - mn));
  }
  return clamp01(v);
}

function applyTransformVector(vec: number[], t?: Transform, stats?: { mean?: number; std?: number } | null): number[] {
  return vec.map(x => applyTransformScalar(x, t, stats));
}

function resolveSelector(metrics: Record<string, MetricValue>, sel: Selector, reg?: MetricRegistryIndex): string | null {
  if (sel.type === "name") return metrics[sel.value] ? sel.value : null;

  if (sel.type === "pattern") {
    const keys = Object.keys(metrics).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    for (const k of keys) if (matchPattern(k, sel.value)) return k;
    return null;
  }

  if (sel.type === "tag") {
    const keysFromReg = reg?.byTag?.[sel.value] || null;
    if (keysFromReg) {
      for (const k of keysFromReg) if (metrics[k]) return k;
    }
    const keys = Object.keys(metrics).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    for (const k of keys) {
      const mv = metrics[k] as { tags?: unknown };
      const tags = mv?.tags || [];
      if (Array.isArray(tags) && tags.includes(sel.value)) return k;
    }
    return null;
  }

  return null;
}

function pickMetric(
  metrics: Record<string, MetricValue>,
  candidates: Selector[],
  reg?: MetricRegistryIndex
): { key: string | null; selector: Selector | null } {
  for (const sel of candidates) {
    const k = resolveSelector(metrics, sel, reg);
    if (k) return { key: k, selector: sel };
  }
  return { key: null, selector: null };
}

function resolved(
  metric_key: string | null,
  selector: Selector | null,
  used_fallback: boolean,
  transform: Transform | null,
  notes?: string[]
): Resolved {
  return { metric_key, selector, used_fallback, transform, notes: notes?.length ? notes : null };
}

function deriveTransform(
  specT: Transform | undefined,
  desc: { normalization?: { recommended_op?: Transform["op"]; min?: number | null; max?: number | null }; stats_hint?: { min?: number | null; max?: number | null } } | null,
  fallbackOp: Transform["op"]
): Transform {
  if (specT) return specT;

  const op = (desc?.normalization?.recommended_op as Transform["op"]) || fallbackOp;
  const mn = desc?.normalization?.min ?? desc?.stats_hint?.min ?? null;
  const mx = desc?.normalization?.max ?? desc?.stats_hint?.max ?? null;

  const t: Transform = { op };
  if (typeof mn === "number") t.min = mn;
  if (typeof mx === "number") t.max = mx;
  return t;
}

export function bindMetricsToGlyphV2(
  metrics: Record<string, MetricValue>,
  spec: MetricBindingSpec,
  reg?: MetricRegistryIndex
): { channels: { R: number; S: number; N: number; K: number; C: number[] }; report: BindingReport } {
  const defaults = spec.defaults ?? { R: 0.2, S: 0.2, N: 0.2, K: 0.2, C: [0, 0, 0, 0, 0, 0] };

  function bindScalar(name: "R" | "S" | "N" | "K") {
    const rule = spec.channels[name];
    const pick = pickMetric(metrics, rule.candidates, reg);

    if (!pick.key) {
      const fb = typeof rule.fallback === "number" ? rule.fallback : defaults[name];
      return { v: clamp01(fb), res: resolved(null, null, true, rule.transform ?? null, ["fallback"]) };
    }

    const mv = metrics[pick.key];
    const desc = reg?.byKey?.[pick.key] || null;

    if (!mv || mv.type !== "scalar" || !Number.isFinite(mv.v)) {
      const fb = typeof rule.fallback === "number" ? rule.fallback : defaults[name];
      return {
        v: clamp01(fb),
        res: resolved(pick.key, pick.selector, true, rule.transform ?? null, ["missing_or_non_scalar"])
      };
    }

    const t = deriveTransform(rule.transform, desc, "clip01");
    const stats = (mv as { stats?: { mean?: number; std?: number } }).stats || desc?.stats_hint || null;

    const v = applyTransformScalar(mv.v, t, stats);
    return { v, res: resolved(pick.key, pick.selector, false, t) };
  }

  function bindVectorC() {
    const rule = spec.channels.C;
    const pick = pickMetric(metrics, rule.candidates, reg);

    if (!pick.key) {
      const fb = Array.isArray(rule.fallback) ? rule.fallback : defaults.C;
      return { v: fb.slice(0, 6).map(clamp01), res: resolved(null, null, true, rule.transform ?? null, ["fallback"]) };
    }

    const mv = metrics[pick.key];
    const desc = reg?.byKey?.[pick.key] || null;

    if (!mv || mv.type !== "vector" || !Array.isArray(mv.v)) {
      const fb = Array.isArray(rule.fallback) ? rule.fallback : defaults.C;
      return {
        v: fb.slice(0, 6).map(clamp01),
        res: resolved(pick.key, pick.selector, true, rule.transform ?? null, ["missing_or_non_vector"])
      };
    }

    const raw = mv.v.slice(0, 6);
    while (raw.length < 6) raw.push(0);

    const t = deriveTransform(rule.transform, desc, "clip01");
    const stats = (mv as { stats?: { mean?: number; std?: number } }).stats || desc?.stats_hint || null;

    const vec = applyTransformVector(raw, t, stats).map(clamp01);
    return { v: vec, res: resolved(pick.key, pick.selector, false, t) };
  }

  const R = bindScalar("R");
  const S = bindScalar("S");
  const N = bindScalar("N");
  const K = bindScalar("K");
  const C = bindVectorC();

  const report: BindingReport = {
    schema: "MetricBindingReport.v0.1",
    resolved: { R: R.res, S: S.res, N: N.res, K: K.res, C: C.res }
  };

  return { channels: { R: R.v, S: S.v, N: N.v, K: K.v, C: C.v }, report };
}

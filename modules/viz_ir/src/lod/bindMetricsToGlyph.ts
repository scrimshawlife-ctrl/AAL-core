import type {
  MetricValue,
  MetricBindingSpec,
  Selector,
  Transform,
  BindingReport,
  Resolved
} from "./metricBindingTypes";

function clamp01(x: number): number {
  return Math.max(0, Math.min(1, x));
}

function sigmoid(x: number): number {
  return 1 / (1 + Math.exp(-x));
}

function applyTransformScalar(v: number, t?: Transform): number {
  if (!t) return v;
  if (t.op === "identity") return v;
  if (t.op === "clip01") return clamp01(v);
  if (t.op === "log1p") return clamp01(Math.log1p(Math.max(0, v)));
  if (t.op === "sigmoid") return clamp01(sigmoid(v));
  if (t.op === "minmax") {
    const mn = typeof t.min === "number" ? t.min : 0;
    const mx = typeof t.max === "number" ? t.max : 1;
    if (mx === mn) return 0;
    return clamp01((v - mn) / (mx - mn));
  }
  if (t.op === "zscore_if_stats") {
    return v;
  }
  return v;
}

function applyTransformVector(vec: number[], t?: Transform): number[] {
  if (!t) return vec;
  return vec.map(x => applyTransformScalar(x, t));
}

function matchPattern(key: string, pattern: string): boolean {
  if (pattern.endsWith(".*")) return key.startsWith(pattern.slice(0, -2));
  return key === pattern;
}

function resolveSelector(metrics: Record<string, MetricValue>, sel: Selector): string | null {
  if (sel.type === "name") return metrics[sel.value] ? sel.value : null;

  if (sel.type === "pattern") {
    const keys = Object.keys(metrics).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    for (const k of keys) if (matchPattern(k, sel.value)) return k;
    return null;
  }

  if (sel.type === "tag") {
    const keys = Object.keys(metrics).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    for (const k of keys) {
      const mv = metrics[k];
      const tags = (mv as { tags?: unknown }).tags || [];
      if (Array.isArray(tags) && tags.includes(sel.value)) return k;
    }
    return null;
  }

  return null;
}

function pickMetric(
  metrics: Record<string, MetricValue>,
  candidates: Selector[]
): { key: string | null; selector: Selector | null } {
  for (const sel of candidates) {
    const key = resolveSelector(metrics, sel);
    if (key) return { key, selector: sel };
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

export function bindMetricsToGlyph(
  metrics: Record<string, MetricValue>,
  spec: MetricBindingSpec
): { channels: { R: number; S: number; N: number; K: number; C: number[] }; report: BindingReport } {
  const d = spec.defaults ?? { R: 0.2, S: 0.2, N: 0.2, K: 0.2, C: [0, 0, 0, 0, 0, 0] };

  function bindScalar(name: "R" | "S" | "N" | "K") {
    const rule = spec.channels[name];
    const pick = pickMetric(metrics, rule.candidates);
    if (!pick.key) {
      const fb = typeof rule.fallback === "number" ? rule.fallback : d[name];
      return { v: clamp01(fb), res: resolved(null, null, true, rule.transform ?? null, ["fallback"]) };
    }

    const mv = metrics[pick.key];
    if (!mv || mv.type !== "scalar" || !Number.isFinite(mv.v)) {
      const fb = typeof rule.fallback === "number" ? rule.fallback : d[name];
      return {
        v: clamp01(fb),
        res: resolved(pick.key, pick.selector, true, rule.transform ?? null, ["missing_or_non_scalar"])
      };
    }

    let v = mv.v;
    if (rule.transform?.op === "zscore_if_stats" && mv.stats?.mean != null && mv.stats?.std != null && mv.stats.std !== 0) {
      const z = (v - mv.stats.mean) / mv.stats.std;
      v = clamp01(sigmoid(z));
    } else {
      v = applyTransformScalar(v, rule.transform);
      v = clamp01(v);
    }

    return { v, res: resolved(pick.key, pick.selector, false, rule.transform ?? null) };
  }

  function bindVectorC() {
    const rule = spec.channels.C;
    const pick = pickMetric(metrics, rule.candidates);
    if (!pick.key) {
      const fb = Array.isArray(rule.fallback) ? rule.fallback : d.C;
      return { v: fb.slice(0, 6).map(clamp01), res: resolved(null, null, true, rule.transform ?? null, ["fallback"]) };
    }

    const mv = metrics[pick.key];
    if (!mv || mv.type !== "vector" || !Array.isArray(mv.v)) {
      const fb = Array.isArray(rule.fallback) ? rule.fallback : d.C;
      return {
        v: fb.slice(0, 6).map(clamp01),
        res: resolved(pick.key, pick.selector, true, rule.transform ?? null, ["missing_or_non_vector"])
      };
    }

    const raw = mv.v.slice(0, 6);
    while (raw.length < 6) raw.push(0);

    let vec = raw;
    if (rule.transform?.op === "zscore_if_stats" && mv.stats?.mean != null && mv.stats?.std != null && mv.stats.std !== 0) {
      vec = vec.map(x => clamp01(sigmoid((x - mv.stats.mean) / mv.stats.std)));
    } else {
      vec = applyTransformVector(vec, rule.transform);
      vec = vec.map(clamp01);
    }

    return { v: vec, res: resolved(pick.key, pick.selector, false, rule.transform ?? null) };
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

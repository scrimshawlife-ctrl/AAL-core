export function roundN(x: unknown, n = 6): unknown {
  if (typeof x === "number" && Number.isFinite(x)) {
    const f = Math.pow(10, n);
    return Math.round(x * f) / f;
  }
  if (Array.isArray(x)) return x.map(v => roundN(v, n));
  if (x && typeof x === "object") {
    const out: Record<string, unknown> = {};
    for (const k of Object.keys(x as Record<string, unknown>)) {
      out[k] = roundN((x as Record<string, unknown>)[k], n);
    }
    return out;
  }
  return x;
}

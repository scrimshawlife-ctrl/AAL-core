export function stableStringify(x: any): string {
  const seen = new WeakSet();

  function sortObj(o: any): any {
    if (o === null || typeof o !== "object") return o;
    if (seen.has(o)) return "[[CYCLE]]";
    seen.add(o);

    if (Array.isArray(o)) return o.map(sortObj);

    const keys = Object.keys(o).sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
    const out: Record<string, unknown> = {};
    for (const k of keys) out[k] = sortObj(o[k]);
    return out;
  }

  return JSON.stringify(sortObj(x));
}

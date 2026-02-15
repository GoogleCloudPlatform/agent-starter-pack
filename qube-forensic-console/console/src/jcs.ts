// Canonical JSON (RFC8785-ish): stable key ordering, no whitespace.
// Must match Python canonical_json semantics.
export function canonicalJson(obj: any): string {
  const sortKeys = (x: any): any => {
    if (Array.isArray(x)) return x.map(sortKeys);
    if (x && typeof x === "object") {
      return Object.keys(x).sort().reduce((acc: any, k) => {
        acc[k] = sortKeys(x[k]);
        return acc;
      }, {});
    }
    return x;
  };
  return JSON.stringify(sortKeys(obj));
}

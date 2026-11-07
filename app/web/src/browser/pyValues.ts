// Moving values across the Pyodide boundary and between workers.
//
// Python -> JS: a dict, list or bytes arrives as a PyProxy. `fromPy` copies it into plain
// objects, arrays and Uint8Arrays. Pyodide frees the proxies it passes as arguments itself
// (destroying one by hand is a fatal error), so only a proxy JS owns (a call's result) is
// destroyed, with `takePy`. Python None becomes `undefined`; `nullify` turns it into the
// `null` the UI's JSON-shaped data expects.
//
// JS -> Python: `undefined` becomes None but `null` becomes `pyodide.ffi.jsnull`, which
// json.dump refuses, so `denull` turns every null into undefined first (a tree's root has
// "parent": null).

type Proxy = { toJs(o: object): unknown; destroy(): void };

const isProxy = (x: unknown): x is Proxy => typeof (x as Proxy | null)?.toJs === "function";

const plain = (x: unknown): x is Record<string, unknown> =>
  typeof x === "object" && x !== null && (Object.getPrototypeOf(x) === Object.prototype || Object.getPrototypeOf(x) === null);

const toJsOptions = { dict_converter: Object.fromEntries, create_pyproxies: false };

/** A value Python passed to JS, as plain JS (the proxy stays Pyodide's to free). */
export function fromPy(x: unknown): any {
  return isProxy(x) ? x.toJs(toJsOptions) : x;
}

/** A message jobchild posted ([kind, stage, info, files?]) as plain JS, each file's bytes
 *  read back from the worker's filesystem (`read(path)`), which holds them as written.
 *  Converted bytes can be wrong: Pyodide 314.0.7's toJs copies a bytes object with
 *  HEAP8.slice(ptr, ...) and passes ptr as a signed int, so an object lying above 2 GiB
 *  of wasm heap (a large fold's) comes back as other heap memory of the same length
 *  (fixed upstream by pyodide#6495, in no release yet; scripts/pyodide-high-heap.mjs). */
export function jobMessage(msg: unknown, outDir: string, read: (path: string) => Uint8Array): unknown[] {
  const m = fromPy(msg) as unknown[];
  if (plain(m[3])) m[3] = Object.fromEntries(Object.keys(m[3]).map((rel) => [rel, read(`${outDir}/${rel}`)]));
  return m;
}

/** A Python call's result, as plain JS; the proxy is destroyed. */
export function takePy(x: unknown): any {
  if (!isProxy(x)) return x;
  try { return x.toJs(toJsOptions); } finally { x.destroy(); }
}

function mapLeaves(x: unknown, leaf: (v: unknown) => unknown): unknown {
  if (Array.isArray(x)) return x.map((v) => mapLeaves(v, leaf));
  if (plain(x)) return Object.fromEntries(Object.entries(x).map(([k, v]) => [k, mapLeaves(v, leaf)]));
  return leaf(x);
}

/** Every undefined inside arrays and plain objects as null (bytes are left alone). */
export const nullify = <T>(x: T): T => mapLeaves(x, (v) => (v === undefined ? null : v)) as T;

/** Every null inside arrays and plain objects as undefined, which Python reads as None. */
export const denull = <T>(x: T): T => mapLeaves(x, (v) => (v === null ? undefined : v)) as T;

/** The distinct ArrayBuffers under x, for postMessage's transfer list. */
export function buffersOf(x: unknown): ArrayBuffer[] {
  const out = new Set<ArrayBuffer>();
  const walk = (v: unknown) => {
    if (ArrayBuffer.isView(v)) { if (v.buffer instanceof ArrayBuffer) out.add(v.buffer); }
    else if (Array.isArray(v)) v.forEach(walk);
    else if (plain(v)) Object.values(v).forEach(walk);
  };
  walk(x);
  return [...out];
}

/** An error as one line: a Python traceback's last line ("KeyError: 'run_id'"), else the
 *  message's first (Pyodide's own errors end in a "See https://pyodide.org/…" line). */
export function errorText(e: unknown): string {
  const text = e instanceof Error ? e.message : String(e);
  const lines = text.split("\n").map((l) => l.trim()).filter(Boolean);
  const line = (e as Error | null)?.name === "PythonError" ? lines.at(-1) : lines[0];
  return line ?? (e instanceof Error ? e.name : "unknown error");
}

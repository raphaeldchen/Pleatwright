/// <reference lib="webworker" />
// The browser build's service worker: it answers the run-file URLs the UI already loads
// (`fileUrl` in api.ts, `<base>runs/{id}/files/{rel}`) in place of the server. Browser runs
// are read from the IndexedDB store; `gallery-*` runs are static files the site ships at
// `<base>gallery/<id>/<rel>` (the UI loads those directly; this mapping is a fallback). It
// also gives the worker scripts their Content-Security-Policy (`WORKER_CSP`). Task 11's
// site build bundles this file into a classic script at `<base>sw.js`, so it has only
// static imports. The app's tsconfig leaves this file out
// (the DOM and webworker libs clash); tsconfig.sw.json checks it with the webworker lib.
import { StorageUnavailable, getFile } from "./runFiles";

declare const self: ServiceWorkerGlobalScope;

const RUN_ID = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;

/** The run file a URL asks for, or null when it is not a run-file URL under `base`
 *  (`base` ends in "/"). Segments are decoded; ".." segments and bad ids are rejected. */
export function resolveFileRequest(url: URL, base: string): { runId: string; rel: string } | null {
  if (!url.pathname.startsWith(base)) return null;
  const parts = url.pathname.slice(base.length).split("/");
  if (parts.length < 4 || parts[0] !== "runs" || parts[2] !== "files") return null;
  let segs: string[];
  try { segs = parts.slice(1).map(decodeURIComponent); } catch { return null; }
  const [runId, , ...rel] = segs;
  if (!RUN_ID.test(runId)) return null;
  for (const s of rel) if (s === "" || s === "." || s === ".." || s.includes("/") || s.includes("\\")) return null;
  return { runId, rel: rel.join("/") };
}

const TYPES: Record<string, string> = {
  svg: "image/svg+xml", png: "image/png", json: "application/json", jsonl: "application/x-ndjson",
  fold: "application/json", zip: "application/zip", glb: "model/gltf-binary",
};

const contentType = (rel: string) => {
  const dot = rel.lastIndexOf(".");
  return (dot < 0 && TYPES[rel]) || TYPES[rel.slice(dot + 1).toLowerCase()] || "application/octet-stream";
};

export interface Deps {
  getFile: (runId: string, rel: string) => Promise<Blob | null>;
  fetch: (input: URL) => Promise<Response>;
}

/** The response for a request URL, or null when the worker should leave it alone.
 *  `StorageUnavailable` is a 503; any other store error propagates. */
export async function respond(url: URL, base: string, deps: Deps): Promise<Response | null> {
  const hit = resolveFileRequest(url, base);
  if (!hit) return null;
  const { runId, rel } = hit;
  if (runId.startsWith("gallery-")) {
    const enc = rel.split("/").map(encodeURIComponent).join("/");
    return deps.fetch(new URL(`${base}gallery/${runId}/${enc}`, url.origin));
  }
  let blob: Blob | null;
  try { blob = await deps.getFile(runId, rel); } catch (e) {
    if (e instanceof StorageUnavailable) return new Response(e.message, { status: 503 });
    throw e;
  }
  if (!blob) return new Response("not found", { status: 404 });
  const headers: Record<string, string> = { "Content-Type": contentType(rel), "X-Content-Type-Options": "nosniff" };
  // As api.py's file route: a run's SVG is never a script-running document of this origin.
  if (rel.toLowerCase().endsWith(".svg")) headers["Content-Security-Policy"] = "sandbox";
  return new Response(blob, { status: 200, headers });
}

// A worker's Content-Security-Policy is the one on its own script's response, not the page's,
// and a static host (GitHub Pages) sends none: so this worker adds it to the manager and job
// worker scripts. The workers boot Pyodide from this origin, which needs WebAssembly
// compilation ('wasm-unsafe-eval') and no other origin. A page this worker does not control
// (its first load before the claim, or a browser without service workers) starts its workers
// without this policy: spec browser build §4.2.
export const WORKER_CSP = ["default-src 'self'", "script-src 'self' 'wasm-unsafe-eval'", "connect-src 'self'"].join("; ");

/** `res` with the worker policy added (its status, other headers and body unchanged). */
export function withWorkerPolicy(res: Response): Response {
  const headers = new Headers(res.headers);
  headers.set("Content-Security-Policy", WORKER_CSP);
  return new Response(res.body, { status: res.status, statusText: res.statusText, headers });
}

// Only a real service worker registers handlers; the tests import this module in node.
if (typeof self !== "undefined" && "registration" in self) {
  const base = new URL(self.registration.scope).pathname;
  const deps: Deps = { getFile, fetch: (u) => fetch(u) };
  self.addEventListener("install", () => { void self.skipWaiting(); });
  self.addEventListener("activate", (e) => e.waitUntil(self.clients.claim()));
  self.addEventListener("fetch", (e) => {
    if (e.request.method !== "GET") return;
    const url = new URL(e.request.url);
    if (url.origin !== self.location.origin) return;
    if (e.request.destination === "worker") {
      e.respondWith(fetch(e.request).then(withWorkerPolicy));
      return;
    }
    if (!resolveFileRequest(url, base)) return;
    e.respondWith(respond(url, base, deps).then((r) => r ?? fetch(e.request)));
  });
}

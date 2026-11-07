// The UI seam (api.ts) in the static website: no server. Examples are static files under
// <base>gallery/, loaded straight from there; a visitor's own runs live in the manager worker
// behind the run host (browser/runHost.ts), with their files in IndexedDB, served by the
// service worker.

import type { Command } from "./apiServer";
import { runHost, type HandleResult } from "./browser/runHost";
import { listRunIds, storageOk } from "./browser/runFiles";
import type { PwEvent, RunSummary, Status } from "./types";

export type { Command };

const BASE = import.meta.env.BASE_URL;
const GALLERY = "gallery-";
export const NO_LLM = "Design your own arrives with sign-in";
export const STORAGE_BANNER =
  "This browser isn't saving runs (private window or storage full); folds still work but vanish when you close the tab.";
const READ_ONLY_EXAMPLE = "examples are read-only";

const isGallery = (id: string) => id.startsWith(GALLERY);
const encRel = (rel: string) => rel.split("/").map(encodeURIComponent).join("/");
const galleryUrl = (id: string, rel: string) => `${BASE}gallery/${encodeURIComponent(id)}/${encRel(rel)}`;

// A StorageUnavailable from the engine's storage, as its error text reaches the page.
const STORAGE_ERROR = /StorageUnavailable|browser storage|IndexedDB/;

// The status poll (every 3 s) asks whether runs are being saved. A probe is a real write, so
// one that passed holds for the page's life; a failed one, or a storage error since, probes again.
let storageGood = false;
async function stored(): Promise<boolean> {
  if (!storageGood) storageGood = await storageOk();
  return storageGood;
}

/** The engine's answer to `cmd`, throwing its error when the command was not taken. The
 *  host boots on its first command (a fold, or opening a browser run). */
async function call(cmd: Record<string, unknown>): Promise<HandleResult> {
  const r = await runHost().handle(cmd);
  if (!r.ok) {
    if (STORAGE_ERROR.test(r.error ?? "")) storageGood = false;
    throw new Error(r.error ?? "the folding engine refused");
  }
  return r;
}

// The engine is a ~40 MB download: a visit to the examples alone never loads it. Runs
// stored here load it at page load (getStatus's first call), so recover() can mark the
// ones a closed tab left mid-stage.
let bootChecked = false;
function bootIfStoredRuns(): void {
  if (bootChecked) return;
  bootChecked = true;
  listRunIds().then((ids) => { if (ids.length) void runHost().boot(); },
                    () => { storageGood = false; });          // nothing readable is stored
}

async function galleryRows(): Promise<RunSummary[]> {
  try {
    const r = await fetch(`${BASE}gallery/index.json`);
    if (!r.ok) return [];                          // a build without examples
    return ((await r.json()) as RunSummary[]).map((row) => ({ ...row, kind: "gallery" }));
  } catch {
    return [];
  }
}

export async function getStatus(): Promise<Status> {
  bootIfStoredRuns();
  const h = runHost();
  const st = h.state();
  const [saving, live] = await Promise.all([
    stored(),
    st.phase === "ready" ? h.handle({ op: "status" }).catch(() => null) : null,
  ]);
  return {
    llm_ok: false,
    llm_error: live?.ok ? live.llm_error ?? NO_LLM : NO_LLM,
    busy: live?.ok ? live.busy ?? null : null,      // nothing runs before the engine is up
    read_only: st.read_only,
    banner: st.banner ?? (saving ? undefined : STORAGE_BANNER),
  };
}

/** The examples, then this browser's runs (none until the engine is up, or in a read-only tab). */
export async function listRuns(): Promise<RunSummary[]> {
  const h = runHost();
  const [gallery, mine] = await Promise.all([
    galleryRows(),
    h.state().phase === "ready" ? h.handle({ op: "list" }).catch(() => null) : null,
  ]);
  const runs = mine?.ok ? (mine.runs as RunSummary[]) : [];
  return [...gallery, ...runs.map((row) => ({ ...row, kind: "browser" as const }))];
}

export function createRun(_prompt: string, _model?: string): Promise<{ id: string }> {
  return Promise.reject(new Error(NO_LLM));
}

/** Re-fold an example here from its raw tree.json (its roll and subject name the folder). */
export async function foldTree(galleryId: string): Promise<{ id: string }> {
  const [rows, tree] = await Promise.all([galleryRows(), fetch(galleryUrl(galleryId, "tree.json")).then((r) => {
    if (!r.ok) throw new Error(`HTTP ${r.status} from the example's tree.json`);
    return r.json();
  })]);
  const row = rows.find((r) => r.id === galleryId);
  const label = `${row?.prompt || galleryId.slice(GALLERY.length)} (folded in your browser)`;
  const r = await call({ op: "fold_tree", tree, label });
  return { id: String(r.id) };
}

export async function deleteRun(runId: string): Promise<void> {
  if (isGallery(runId)) throw new Error(READ_ONLY_EXAMPLE);
  await call({ op: "delete", run_id: runId });
}

/** Save a finished run's `<Subject>_<grid>/` folder as a zip. */
export async function downloadRun(runId: string): Promise<void> {
  const r = await call({ op: "zip", run_id: runId });
  const url = URL.createObjectURL(new Blob([r.bytes as BlobPart], { type: "application/zip" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = String(r.name);
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}

/** An example's file is its static copy, so examples load without a service worker
 *  (blocked, Shift+Reload); a browser run's file is the service worker's run-file URL. */
export function fileUrl(runId: string, rel: string): string {
  if (isGallery(runId)) return galleryUrl(runId, rel);
  return `${BASE}runs/${encodeURIComponent(runId)}/files/${encRel(rel)}`;
}

export function downloadName(runId: string, rel: string): string {
  return `${runId}_${rel.split("/").pop()}`;
}

/** An example replays its static events.jsonl once; a browser run gets the `after` backlog,
 *  then live events. Same shape as the server's connectRun. */
export function connectRun(runId: string, onEvent: (e: PwEvent) => void,
                           onError: (message: string) => void) {
  let closed = false;
  let last = -1;
  const deliver = (e: PwEvent) => {
    if (closed || typeof e.seq !== "number" || e.seq <= last) return;
    last = e.seq;
    onEvent(e);
  };

  if (isGallery(runId)) {
    fetch(galleryUrl(runId, "events.jsonl"))
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const lines = (await r.text()).split("\n").filter((l) => l.trim());
        for (const l of lines) deliver(JSON.parse(l) as PwEvent);
      })
      .catch((e) => { if (!closed) onError(`cannot open this run: ${(e as Error).message}`); });
    return {
      send(_cmd: Command) { onError(READ_ONLY_EXAMPLE); },
      close() { closed = true; },
    };
  }

  // Live events that arrive while the backlog is on its way wait here, then go after it.
  let early: PwEvent[] | null = [];
  const off = runHost().subscribe((m) => {
    if (m.type !== "event" || m.run_id !== runId) return;
    if (early) early.push(m.event);
    else deliver(m.event);
  });
  runHost().handle({ op: "after", run_id: runId, seq: -1 })
    .then((r) => {
      if (!r.ok) throw new Error(r.error);
      for (const e of r.events as PwEvent[]) deliver(e);
    })
    .catch((e) => { if (!closed) onError(`cannot open this run: ${(e as Error).message}`); })
    .finally(() => {
      const queued = early ?? [];
      early = null;
      for (const e of queued) deliver(e);
    });

  return {
    send(cmd: Command) {
      if (closed) return onError("connection closed");
      if (cmd.type === "message") return onError(NO_LLM);
      const op: Record<string, unknown> = { op: cmd.type, run_id: runId };
      if (cmd.type === "approve" && cmd.choice) op.choice = cmd.choice;
      call(op).catch((e) => onError((e as Error).message));
    },
    close() {
      closed = true;
      off();
    },
  };
}

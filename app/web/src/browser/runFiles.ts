// The browser build's run store: a run is a folder of files (events.jsonl, tree.json,
// layout/*, <Subject>_<grid>/*, model.fold), and here each file is one ArrayBuffer in
// IndexedDB under the key `${runId}/${rel}`. Not a Blob: Safari private windows open
// IndexedDB but refuse Blob values ("Error preparing Blob/File data to be stored"). No DOM
// APIs, so the window, dedicated workers and the service worker can all use it. A run id
// never contains "/".

/** IndexedDB is missing or refused to open (Firefox private windows), or it is full. */
export class StorageUnavailable extends Error {
  constructor(message: string) {
    super(message);
    this.name = "StorageUnavailable";
  }
}

const DB_NAME = "pleatwright";
const STORE = "files";

// The keys of one run: "a/" up to (not including) "a0", since "0" is the character after "/".
// A run "a" therefore never reaches "ab/..." or "a-b/...".
const runRange = (runId: string) => IDBKeyRange.bound(`${runId}/`, `${runId}0`, false, true);

// storageOk()'s test write: a key with no "/", so it is never part of a run (listRunIds skips it).
const PROBE = "storage-probe";

/** A copy of exactly the view's bytes (a view may cover part of a larger buffer). */
const own = (data: Uint8Array): ArrayBuffer => data.slice().buffer as ArrayBuffer;

const unavailable = (e: unknown) => {
  if (e instanceof StorageUnavailable) return e;
  const err = e as { name?: string; message?: string } | null;
  const quota = err?.name === "QuotaExceededError";
  const detail = err?.message ?? (e == null ? "" : String(e));
  return new StorageUnavailable(`${quota ? "browser storage is full" : "browser storage failed"}${detail ? `: ${detail}` : ""}`);
};

let opened: Promise<IDBDatabase> | null = null;

/** The database, opened lazily once per realm (version 1, one object store). A failed open
 *  is not remembered, so storageOk() can succeed after the user leaves private mode. */
function db(): Promise<IDBDatabase> {
  if (opened) return opened;
  const p = new Promise<IDBDatabase>((resolve, reject) => {
    if (typeof indexedDB === "undefined" || !indexedDB) {
      reject(new StorageUnavailable("IndexedDB is not available"));
      return;
    }
    let req: IDBOpenDBRequest;
    try { req = indexedDB.open(DB_NAME, 1); } catch (e) { reject(unavailable(e)); return; }
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => {
      const d = req.result;
      const forget = () => { if (opened === p) opened = null; };
      d.onversionchange = () => { d.close(); forget(); };
      d.onclose = forget; // the browser closed it, e.g. site data was cleared
      resolve(d);
    };
    req.onerror = () => reject(unavailable(req.error));
    req.onblocked = () => reject(new StorageUnavailable("IndexedDB open is blocked"));
  });
  opened = p;
  p.catch(() => { if (opened === p) opened = null; });
  return p;
}

/** Runs `use` on the files store in one transaction and resolves with its result once the
 *  transaction has committed. Any failure, including a quota abort, is a StorageUnavailable. */
async function tx<T>(mode: IDBTransactionMode, use: (s: IDBObjectStore) => IDBRequest<T> | void): Promise<T | undefined> {
  const d = await db();
  return new Promise<T | undefined>((resolve, reject) => {
    let t: IDBTransaction | undefined;
    try {
      t = d.transaction(STORE, mode);
      const req = use(t.objectStore(STORE));
      t.oncomplete = () => resolve(req ? req.result : undefined);
      t.onerror = () => reject(unavailable(t?.error ?? req?.error));
      t.onabort = () => reject(unavailable(t?.error));
    } catch (e) {
      // A request that threw (a full disk) must not leave the earlier puts to commit.
      try { t?.abort(); } catch { /* already finished */ }
      reject(unavailable(e));
    }
  });
}

/** Stores `files` (path inside the run -> bytes) as run `runId`, replacing same-named files,
 *  in one transaction: either every file lands or none does. */
export async function putFiles(runId: string, files: Record<string, Uint8Array>): Promise<void> {
  await tx("readwrite", (s) => {
    for (const [rel, data] of Object.entries(files)) s.put(own(data), `${runId}/${rel}`);
  });
}

export async function getFile(runId: string, rel: string): Promise<Blob | null> {
  const buf = await tx<ArrayBuffer | undefined>("readonly", (s) => s.get(`${runId}/${rel}`));
  return buf ? new Blob([buf]) : null;
}

/** Every file of the run, keyed by its path inside the run ({} for an unknown run). Keys and
 *  values are read in one transaction, so a concurrent put cannot leave them out of step. */
export async function readRun(runId: string): Promise<Record<string, Uint8Array>> {
  const prefix = `${runId}/`;
  let keys: IDBRequest<IDBValidKey[]>;
  const bufs = await tx<ArrayBuffer[]>("readonly", (s) => {
    keys = s.getAllKeys(runRange(runId));
    return s.getAll(runRange(runId));
  });
  const out: Record<string, Uint8Array> = {};
  for (const [i, buf] of (bufs ?? []).entries()) out[String(keys!.result[i]).slice(prefix.length)] = new Uint8Array(buf);
  return out;
}

/** The ids of the stored runs, in key order. Walks the keys only (no file is loaded), jumping
 *  over each run's remaining keys once its id is seen. */
export async function listRunIds(): Promise<string[]> {
  const d = await db();
  return new Promise<string[]>((resolve, reject) => {
    const ids: string[] = [];
    try {
      const t = d.transaction(STORE, "readonly");
      const cur = t.objectStore(STORE).openKeyCursor();
      cur.onsuccess = () => {
        const c = cur.result;
        if (!c) return;
        const key = String(c.key);
        const slash = key.indexOf("/");
        if (slash < 0) { c.continue(); return; }
        const id = key.slice(0, slash);
        ids.push(id);
        c.continue(`${id}0`);
      };
      t.oncomplete = () => resolve(ids);
      t.onerror = () => reject(unavailable(t.error ?? cur.error));
      t.onabort = () => reject(unavailable(t.error));
    } catch (e) {
      reject(unavailable(e));
    }
  });
}

/** Deletes every file of run `runId` and nothing of any other run. */
export async function deleteRun(runId: string): Promise<void> {
  await tx("readwrite", (s) => s.delete(runRange(runId)));
}

/** Whether runs can be stored here: a real write, since a store can open and still refuse
 *  values (Safari private windows refused Blobs). Never throws. */
export async function storageOk(): Promise<boolean> {
  try {
    await tx("readwrite", (s) => { s.put(new ArrayBuffer(1), PROBE); s.delete(PROBE); });
    return true;
  } catch {
    return false;
  }
}

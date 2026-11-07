// The JS side pwbrowser.py calls (its `bridge`), in the manager worker: run files in
// IndexedDB (runFiles.ts), events to the page, and job messages queued per job until
// `pwbrowser.BrowserJob` asks for the next one. The bridge contract:
//   post(msg)                        sync
//   async run_ids()                  the stored runs
//   async hydrate(run_id)            {rel: bytes}
//   async put_files(run_id, files)
//   start_job(job_id, kind, out_dir, files, kwargs)
//                                    sync and never throws; a job that cannot start gets a
//                                    ["dead", null, reason] message instead
//   async next_job_message(job_id)   [kind, stage, info, files?]
//   cancel_job(job_id)               idempotent

import { buffersOf, denull, errorText, fromPy, nullify } from "./pyValues";

export interface StoreLike {
  listRunIds(): Promise<string[]>;
  readRun(runId: string): Promise<Record<string, Uint8Array>>;
  putFiles(runId: string, files: Record<string, Uint8Array>): Promise<void>;
  deleteRun(runId: string): Promise<void>;
}

export type Send = (msg: unknown, transfer?: Transferable[]) => void;

interface Queue { items: unknown[][]; waiters: ((m: unknown[]) => void)[] }

export function createManagerBridge(store: StoreLike, send: Send) {
  const queues = new Map<string, Queue>();
  // One run's storage writes happen in the order they were asked for, so deleting a run
  // erases every put issued before it, even one still in flight (R14). A put issued after
  // it belongs to a new run that reused the id (dated ids repeat within a minute) and stays.
  const chains = new Map<string, Promise<void>>();
  const inOrder = (runId: string, op: () => Promise<void>): Promise<void> => {
    const p = (chains.get(runId) ?? Promise.resolve()).catch(() => {}).then(op);
    chains.set(runId, p);
    const forget = () => { if (chains.get(runId) === p) chains.delete(runId); };
    p.then(forget, forget);
    return p;
  };

  /** A job worker's message (relayed by the page), for that job's queue. */
  function deliver(jobId: string, msg: unknown[]): void {
    const q = queues.get(jobId);
    if (!q) return;                                // cancelled or unknown: dropped
    const waiter = q.waiters.shift();
    if (waiter) waiter(msg);
    else q.items.push(msg);
  }

  const bridge = {
    post(msg: unknown): void {
      send({ type: "post", msg: nullify(fromPy(msg)) });
    },
    async run_ids(): Promise<string[]> {
      try { return await store.listRunIds(); } catch (e) {
        console.warn("no stored runs:", errorText(e));
        return [];
      }
    },
    async hydrate(runId: string): Promise<Record<string, Uint8Array>> {
      try { return await store.readRun(runId); } catch (e) {
        console.warn(`run ${runId} could not be read:`, errorText(e));
        return {};
      }
    },
    put_files(runId: string, files: unknown): Promise<void> {
      const copy = fromPy(files) as Record<string, Uint8Array>;   // before Pyodide frees the proxy
      return inOrder(runId, () => store.putFiles(runId, copy));
    },
    start_job(jobId: string, kind: string, outDir: string, files: unknown, kwargs: unknown): void {
      queues.set(jobId, { items: [], waiters: [] });
      try {
        const f = fromPy(files) as Record<string, Uint8Array>;
        send({ type: "start_job", job_id: jobId, kind, out_dir: outDir, files: f, kwargs: fromPy(kwargs) },
             buffersOf(f));
      } catch (e) {
        deliver(jobId, ["dead", null, errorText(e)]);
      }
    },
    next_job_message(jobId: string): Promise<unknown[]> {
      const q = queues.get(jobId);
      // JS null would reach Python as jsnull (json.dump refuses it): undefined is None
      if (!q) return Promise.resolve(denull(["dead", null, `no such job: ${jobId}`]));
      const head = q.items.shift();
      if (head) return Promise.resolve(denull(head));
      return new Promise<unknown[]>((resolve) => q.waiters.push((m) => resolve(denull(m))));
    },
    cancel_job(jobId: string): void {
      const q = queues.get(jobId);
      if (!q) return;
      queues.delete(jobId);
      for (const w of q.waiters) w(["dead", null, "cancelled"]);
      send({ type: "cancel_job", job_id: jobId });
    },
  };

  return {
    bridge,
    deliver,
    /** Drops a deleted run's files, after every put of it asked for so far. */
    eraseRun: (runId: string) => inOrder(runId, () => store.deleteRun(runId)),
  };
}

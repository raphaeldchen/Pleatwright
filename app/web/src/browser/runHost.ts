// The browser build's run host, on the main thread (spec: browser build §4.1). It takes
// the single-tab lock, boots the manager worker (guided.Manager in Pyodide, pwbrowser.py),
// sends it the UI's commands, hands its posts (run events) to subscribers, and runs its
// pack/fold jobs in job workers (jobRelay.ts).
//
// Messages to the manager worker: {type: "handle", id, cmd} and job_message (jobRelay).
// From it: booted | boot_failed {reason} | reply {id, result} | post {msg} |
// start_job {...} | cancel_job {job_id}.

import { createJobRelay, type HeapRecord, type StartJob, type WorkerLike } from "./jobRelay";
import type { PwEvent } from "../types";

export type { WorkerLike } from "./jobRelay";

export const LOCK_NAME = "pleatwright-manager";
export const READ_ONLY_BANNER = "Pleatwright is open in another tab; this tab can browse but not fold.";
export const engineBanner = (reason: string) => `Couldn't load the folding engine: ${reason}`;

/** What the host needs of `navigator.locks`. */
export interface LocksLike {
  request(name: string, options: { ifAvailable: true }, cb: (lock: unknown | null) => unknown): Promise<unknown>;
}

export interface HostDeps {
  manager: () => WorkerLike;
  job: () => WorkerLike;
  /** null or absent: no Web Locks here, so the tab runs without the single-tab guard. */
  locks?: LocksLike | null;
}

export interface HostState {
  phase: "idle" | "booting" | "ready" | "read_only" | "failed";
  read_only: boolean;
  banner?: string;
}

/** A pwbrowser `post`: so far only a run's event. */
export interface PostMessage { type: "event"; run_id: string; event: PwEvent }

/** A pwbrowser `handle` result: {ok: true, ...} or {ok: false, error}. */
export type HandleResult = { ok: boolean; error?: string; [k: string]: any };

export interface RunHost {
  boot(): Promise<void>;
  state(): HostState;
  /** Rejects when this tab has no engine (read-only, or it failed to load). */
  handle(cmd: Record<string, unknown>): Promise<HandleResult>;
  subscribe(fn: (m: PostMessage) => void): () => void;
  heaps(): HeapRecord[];
}

export function createRunHost(deps: HostDeps): RunHost {
  let phase: HostState["phase"] = "idle";
  let reason = "";
  let booting: Promise<void> | null = null;
  let manager: WorkerLike | null = null;
  let nextId = 0;
  const pending = new Map<number, { resolve: (r: HandleResult) => void; reject: (e: Error) => void }>();
  const listeners = new Set<(m: PostMessage) => void>();
  const jobs = createJobRelay(deps.job, (m, transfer) => manager?.postMessage(m, transfer));

  const banner = () => (phase === "read_only" ? READ_ONLY_BANNER : phase === "failed" ? engineBanner(reason) : undefined);

  /** Resolves true once this tab holds the lock, which it keeps until the page goes away
   *  (the callback's promise never settles; the browser frees the lock on unload). */
  function takeLock(): Promise<boolean> {
    const locks = deps.locks;
    if (!locks) return Promise.resolve(true);
    return new Promise<boolean>((resolve) => {
      locks.request(LOCK_NAME, { ifAvailable: true }, (lock) => {
        if (!lock) { resolve(false); return; }
        resolve(true);
        return new Promise<never>(() => {});
      }).catch(() => resolve(true));               // no usable lock API: run unguarded
    });
  }

  function fail(why: string) {
    phase = "failed";
    reason = why;
    for (const p of pending.values()) p.reject(new Error(engineBanner(why)));
    pending.clear();
  }

  function startManager(): Promise<void> {
    return new Promise<void>((done) => {
      let w: WorkerLike;
      try { w = deps.manager(); } catch (e) { fail(e instanceof Error ? e.message : String(e)); done(); return; }
      manager = w;
      w.onmessage = ({ data }) => {
        switch (data?.type) {
          case "booted": phase = "ready"; done(); break;
          case "boot_failed": fail(String(data.reason)); done(); break;
          case "reply": {
            const p = pending.get(data.id);
            pending.delete(data.id);
            p?.resolve(data.result);
            break;
          }
          case "post": for (const fn of [...listeners]) fn(data.msg); break;
          case "start_job": jobs.start(data as StartJob); break;
          case "cancel_job": jobs.cancel(String(data.job_id)); break;
        }
      };
      w.onerror = (e) => {
        e.preventDefault?.();
        fail(e.message || "the engine stopped");
        done();
      };
    });
  }

  function boot(): Promise<void> {
    booting ??= (async () => {
      phase = "booting";
      if (!(await takeLock())) { phase = "read_only"; return; }
      await startManager();
    })();
    return booting;
  }

  return {
    boot,
    state() {
      const b = banner();
      return { phase, read_only: phase === "read_only", ...(b ? { banner: b } : {}) };
    },
    async handle(cmd) {
      await boot();
      if (phase !== "ready" || !manager) throw new Error(banner() ?? "the folding engine is not running");
      const id = nextId++;
      const reply = new Promise<HandleResult>((resolve, reject) => pending.set(id, { resolve, reject }));
      manager.postMessage({ type: "handle", id, cmd });
      return reply;
    },
    subscribe(fn) {
      listeners.add(fn);
      return () => { listeners.delete(fn); };
    },
    heaps: () => jobs.heaps(),
  };
}

let shared: RunHost | null = null;

// A Worker's handlers take full events; the host reads only data/message from them.
const asWorker = (w: Worker) => w as unknown as WorkerLike;

/** This page's run host, with the real workers (created on first use). */
export function runHost(): RunHost {
  shared ??= createRunHost({
    manager: () => asWorker(new Worker(new URL("./managerWorker.ts", import.meta.url), { type: "module" })),
    job: () => asWorker(new Worker(new URL("./jobWorker.ts", import.meta.url), { type: "module" })),
    locks: typeof navigator !== "undefined" ? (navigator.locks as unknown as LocksLike | undefined) ?? null : null,
  });
  return shared;
}

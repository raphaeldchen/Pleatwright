import { describe, expect, it, vi } from "vitest";
import { createRunHost, READ_ONLY_BANNER, type LocksLike, type WorkerLike } from "./runHost";

class FakeWorker implements WorkerLike {
  onmessage: ((e: { data: unknown }) => void) | null = null;
  onerror: ((e: { message?: string; preventDefault?: () => void }) => void) | null = null;
  onmessageerror: (() => void) | null = null;
  posted: { msg: any; transfer?: Transferable[] }[] = [];
  terminated = false;
  postMessage(msg: unknown, transfer?: Transferable[]) { this.posted.push({ msg, transfer }); }
  terminate() { this.terminated = true; }
  // test helpers
  emit(data: unknown) { this.onmessage?.({ data }); }
  fail(message: string) { this.onerror?.({ message, preventDefault: () => {} }); }
}

const held: LocksLike = { request: async (_n, _o, cb) => cb({ name: "pleatwright-manager" }) };
const taken: LocksLike = { request: async (_n, _o, cb) => cb(null) };

function setup(locks: LocksLike | null = held) {
  const manager = new FakeWorker();
  const jobs: FakeWorker[] = [];
  const makeManager = vi.fn(() => manager);
  const host = createRunHost({ manager: makeManager, job: () => { const j = new FakeWorker(); jobs.push(j); return j; }, locks });
  return { host, manager, jobs, makeManager };
}

/** Boots a host whose manager worker reports success, then returns it. */
async function booted() {
  const s = setup();
  const p = s.host.boot();
  await vi.waitFor(() => expect(s.makeManager).toHaveBeenCalled());
  s.manager.emit({ type: "booted" });
  await p;
  return s;
}

const toManager = (m: FakeWorker) => m.posted.map((p) => p.msg).filter((d) => d.type === "job_message");

describe("runHost", () => {
  it("second_tab_is_read_only", async () => {
    const { host, makeManager } = setup(taken);
    await host.boot();
    expect(makeManager).not.toHaveBeenCalled();
    expect(host.state()).toEqual({ phase: "read_only", read_only: true, banner: READ_ONLY_BANNER });
    expect(READ_ONLY_BANNER).toBe("Pleatwright is open in another tab; this tab can browse but not fold.");
    await expect(host.handle({ op: "list" })).rejects.toThrow(READ_ONLY_BANNER);
  });

  it("holds the lock for the page's lifetime once it boots", async () => {
    let released = false;
    const locks: LocksLike = {
      request: (_n, opts, cb) => {
        expect(opts).toEqual({ ifAvailable: true });
        return Promise.resolve(cb({ name: "pleatwright-manager" })).then(() => { released = true; });
      },
    };
    const s = setup(locks);
    const p = s.host.boot();
    await vi.waitFor(() => expect(s.makeManager).toHaveBeenCalled());
    s.manager.emit({ type: "booted" });
    await p;
    await new Promise((r) => setTimeout(r, 5));
    expect(released).toBe(false);
    expect(s.host.state()).toEqual({ phase: "ready", read_only: false });
  });

  it("engine_boot_failure_shows_banner", async () => {
    const s = setup();
    const p = s.host.boot();
    await vi.waitFor(() => expect(s.makeManager).toHaveBeenCalled());
    s.manager.emit({ type: "boot_failed", reason: "Failed to fetch" });
    await p;
    expect(s.host.state()).toEqual({ phase: "failed", read_only: false,
                                     banner: "Couldn't load the folding engine: Failed to fetch" });
    await expect(s.host.handle({ op: "list" })).rejects.toThrow("Couldn't load the folding engine: Failed to fetch");
  });

  it("a manager worker that cannot even load also shows the banner", async () => {
    const s = setup();
    const p = s.host.boot();
    await vi.waitFor(() => expect(s.makeManager).toHaveBeenCalled());
    s.manager.fail("SyntaxError: Unexpected token");
    await p;
    expect(s.host.state().banner).toBe("Couldn't load the folding engine: SyntaxError: Unexpected token");
  });

  it("handle round-trips a command to the manager worker", async () => {
    const { host, manager } = await booted();
    const r = host.handle({ op: "list" });
    await vi.waitFor(() => expect(manager.posted).toHaveLength(1));
    const req = manager.posted[0].msg;
    expect(req).toMatchObject({ type: "handle", cmd: { op: "list" } });
    manager.emit({ type: "reply", id: req.id, result: { ok: true, runs: [] } });
    await expect(r).resolves.toEqual({ ok: true, runs: [] });
  });

  it("posts from the manager reach subscribers", async () => {
    const { host, manager } = await booted();
    const seen: unknown[] = [];
    const off = host.subscribe((m) => seen.push(m));
    manager.emit({ type: "post", msg: { type: "event", run_id: "r", event: { seq: 0 } } });
    off();
    manager.emit({ type: "post", msg: { type: "event", run_id: "r", event: { seq: 1 } } });
    expect(seen).toEqual([{ type: "event", run_id: "r", event: { seq: 0 } }]);
  });

  it("relays job messages with their bytes and ends the worker after a terminal one", async () => {
    const { host, manager, jobs } = await booted();
    const tree = new Uint8Array([1, 2, 3]);
    manager.emit({ type: "start_job", job_id: "j1", kind: "fold", out_dir: "/runs/r",
                   files: { "tree.json": tree }, kwargs: { certify_global: true } });
    expect(jobs).toHaveLength(1);
    expect(jobs[0].posted[0].msg).toEqual({ type: "start", kind: "fold", out_dir: "/runs/r",
                                            files: { "tree.json": tree }, kwargs: { certify_global: true } });
    expect(jobs[0].posted[0].transfer).toEqual([tree.buffer]);
    const svg = new Uint8Array([9]);
    jobs[0].emit({ type: "msg", msg: ["stage", "solving", { files: [] }, { "a.svg": svg }] });
    jobs[0].emit({ type: "msg", msg: ["done", null, { grid: 46 }, {}], heap_mb: 812.5 });
    jobs[0].emit({ type: "msg", msg: ["stage", "late", {}, {}] });
    expect(toManager(manager)).toEqual([
      { type: "job_message", job_id: "j1", msg: ["stage", "solving", { files: [] }, { "a.svg": svg }] },
      { type: "job_message", job_id: "j1", msg: ["done", null, { grid: 46 }, {}], heap_mb: 812.5 },
    ]);
    expect(manager.posted.find((p) => p.msg.msg?.[0] === "stage")!.transfer).toEqual([svg.buffer]);
    expect(jobs[0].terminated).toBe(true);
    expect(host.heaps()).toEqual([{ job_id: "j1", kind: "fold", heap_mb: 812.5 }]);
  });

  it("job_worker_error_becomes_dead_message", async () => {
    const { manager, jobs } = await booted();
    manager.emit({ type: "start_job", job_id: "j1", kind: "fold", out_dir: "/runs/r", files: {}, kwargs: {} });
    jobs[0].fail("RangeError: Out of memory");
    jobs[0].fail("again");
    expect(toManager(manager)).toEqual([
      { type: "job_message", job_id: "j1", msg: ["dead", null, "RangeError: Out of memory"] }]);
    expect(jobs[0].terminated).toBe(true);
  });

  it("a job worker that ends without a result, or whose message cannot be read, is dead", async () => {
    const { manager, jobs } = await booted();
    manager.emit({ type: "start_job", job_id: "j1", kind: "pack", out_dir: "/runs/r", files: {}, kwargs: {} });
    manager.emit({ type: "start_job", job_id: "j2", kind: "pack", out_dir: "/runs/r", files: {}, kwargs: {} });
    jobs[0].emit({ type: "dead", reason: "the job ended without a result" });
    jobs[1].onmessageerror?.();
    expect(toManager(manager)).toEqual([
      { type: "job_message", job_id: "j1", msg: ["dead", null, "the job ended without a result"] },
      { type: "job_message", job_id: "j2", msg: ["dead", null, "a message from the job worker could not be read"] }]);
    expect(jobs.every((j) => j.terminated)).toBe(true);
  });

  it("a job worker that cannot be created is dead, not an exception", async () => {
    const manager = new FakeWorker();
    const host = createRunHost({ manager: () => manager, job: () => { throw new Error("no workers here"); }, locks: held });
    const p = host.boot();
    await vi.waitFor(() => expect(manager.onmessage).not.toBeNull());
    manager.emit({ type: "booted" });
    await p;
    manager.emit({ type: "start_job", job_id: "j1", kind: "fold", out_dir: "/r", files: {}, kwargs: {} });
    expect(toManager(manager)).toEqual([{ type: "job_message", job_id: "j1", msg: ["dead", null, "no workers here"] }]);
  });

  it("cancel_terminates_the_job_worker", async () => {
    const { manager, jobs } = await booted();
    manager.emit({ type: "start_job", job_id: "j1", kind: "fold", out_dir: "/runs/r", files: {}, kwargs: {} });
    manager.emit({ type: "cancel_job", job_id: "j1" });
    expect(jobs[0].terminated).toBe(true);
    jobs[0].emit({ type: "msg", msg: ["stage", "solving", {}, {}] });
    jobs[0].fail("terminated");
    manager.emit({ type: "cancel_job", job_id: "j1" });             // idempotent
    expect(toManager(manager)).toEqual([]);
  });
});

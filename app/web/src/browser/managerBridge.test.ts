import { describe, expect, it, vi } from "vitest";
import { createManagerBridge, type StoreLike } from "./managerBridge";

/** A store whose putFiles resolve only when the test says so, logging each write as it lands. */
function slowStore() {
  const landed: string[] = [];
  const gates: (() => void)[] = [];
  const store: StoreLike = {
    listRunIds: vi.fn(async () => ["r1"]),
    readRun: vi.fn(async () => ({ "events.jsonl": new Uint8Array([1]) })),
    putFiles: vi.fn((id: string, files: Record<string, Uint8Array>) =>
      new Promise<void>((resolve) => gates.push(() => { landed.push(`put ${id} ${Object.keys(files)}`); resolve(); }))),
    deleteRun: vi.fn(async (id: string) => { landed.push(`delete ${id}`); }),
  };
  return { store, landed, gates };
}

const flush = () => new Promise((r) => setTimeout(r, 0));

describe("managerBridge", () => {
  it("queues a job's messages until they are asked for, in order, with None as undefined", async () => {
    const { store } = slowStore();
    const { bridge, deliver } = createManagerBridge(store, vi.fn());
    bridge.start_job("j1", "fold", "/runs/r1", {}, {});
    deliver("j1", ["stage", "packing", { a: null }, {}]);
    expect(await bridge.next_job_message("j1")).toEqual(["stage", "packing", { a: undefined }, {}]);
    const next = bridge.next_job_message("j1");
    deliver("j1", ["done", null, { grid: 46 }, {}]);
    expect(await next).toEqual(["done", undefined, { grid: 46 }, {}]);
    deliver("other", ["done", null, {}, {}]);                        // no such job: dropped
  });

  it("start_job sends the job to the page with its bytes transferred", () => {
    const send = vi.fn();
    const { bridge } = createManagerBridge(slowStore().store, send);
    const tree = new Uint8Array([7]);
    bridge.start_job("j1", "pack", "/runs/r1", { "tree.json": tree }, { certify_global: true });
    expect(send).toHaveBeenCalledWith(
      { type: "start_job", job_id: "j1", kind: "pack", out_dir: "/runs/r1", files: { "tree.json": tree },
        kwargs: { certify_global: true } }, [tree.buffer]);
  });

  it("a job that cannot be sent is a dead message, never an exception", async () => {
    const { bridge } = createManagerBridge(slowStore().store, () => { throw new Error("DataCloneError"); });
    expect(() => bridge.start_job("j1", "fold", "/r", {}, {})).not.toThrow();
    expect(await bridge.next_job_message("j1")).toEqual(["dead", undefined, "DataCloneError"]);
  });

  it("cancel tells the page once, frees a waiter and drops later messages", async () => {
    const send = vi.fn();
    const { bridge, deliver } = createManagerBridge(slowStore().store, send);
    bridge.start_job("j1", "fold", "/r", {}, {});
    const waiting = bridge.next_job_message("j1");
    bridge.cancel_job("j1");
    bridge.cancel_job("j1");
    expect(await waiting).toEqual(["dead", undefined, "cancelled"]);
    deliver("j1", ["stage", "solving", {}, {}]);
    expect(send.mock.calls.filter((c) => c[0].type === "cancel_job")).toEqual([[{ type: "cancel_job", job_id: "j1" }]]);
  });

  it("a delete erases the puts issued before it; a run that reuses the id keeps its files", async () => {
    const { store, landed, gates } = slowStore();
    const { bridge, eraseRun } = createManagerBridge(store, vi.fn());
    const put = bridge.put_files("r1", { "a.svg": new Uint8Array([1]) });    // in flight
    const erased = eraseRun("r1");
    const reused = bridge.put_files("r1", { "b.svg": new Uint8Array([2]) });
    await flush();
    gates.shift()!();
    await put;
    await erased;
    await flush();
    gates.shift()!();
    await reused;
    expect(landed).toEqual(["put r1 a.svg", "delete r1", "put r1 b.svg"]);
  });

  it("posts reach the page with None as null; unreadable storage boots with no runs", async () => {
    const send = vi.fn();
    const { store } = slowStore();
    store.listRunIds = vi.fn(async () => { throw new Error("IndexedDB is not available"); });
    const warn = vi.spyOn(console, "warn").mockImplementation(() => {});
    const { bridge } = createManagerBridge(store, send);
    bridge.post({ type: "event", run_id: "r1", event: { seq: 0, retry: undefined } });
    expect(send).toHaveBeenCalledWith({ type: "post", msg: { type: "event", run_id: "r1", event: { seq: 0, retry: null } } });
    expect(await bridge.run_ids()).toEqual([]);
    warn.mockRestore();
  });
});

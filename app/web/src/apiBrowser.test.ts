import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HostState } from "./browser/runHost";

// A fake run host: `handle` answers from `replies`, `emit` plays a post from the manager.
const fake = vi.hoisted(() => {
  const listeners = new Set<(m: unknown) => void>();
  const host = {
    st: { phase: "ready", read_only: false } as HostState,
    replies: {} as Record<string, unknown>,
    boot: vi.fn(async () => {}),
    state() { return host.st; },
    handle: vi.fn(async (cmd: { op: string }) => host.replies[cmd.op] ?? { ok: true }),
    subscribe(fn: (m: unknown) => void) { listeners.add(fn); return () => listeners.delete(fn); },
    emit(m: unknown) { for (const fn of [...listeners]) fn(m); },
    listeners,
  };
  class StorageUnavailable extends Error {}
  return { host, storageOk: vi.fn(async () => true), listRunIds: vi.fn(async (): Promise<string[]> => []), StorageUnavailable };
});
vi.mock("./browser/runHost", async (orig) => ({ ...(await orig<object>()), runHost: () => fake.host }));
vi.mock("./browser/runFiles", () => ({ storageOk: fake.storageOk, listRunIds: fake.listRunIds,
                                       StorageUnavailable: fake.StorageUnavailable }));

// A fresh module per test: the boot check and the storage probe's result last a page's life.
let api: typeof import("./apiBrowser");

const galleryRow = { id: "gallery-dog_0", prompt: "dog roll 0", subject: "dog_roll", created: "2026-10-25T10:00:00",
                     status: "done", kind: "gallery", browser_foldable: true };
const treeText = '{"roll": "dog_0", "subject": "dog", "nodes": [{"name": "body", "parent": null, "length": 2}]}';
const files: Record<string, string> = {
  "/gallery/index.json": JSON.stringify([galleryRow]),
  "/gallery/gallery-dog_0/tree.json": treeText,
  "/gallery/gallery-dog_0/events.jsonl":
    ['{"seq": 0, "t": "a", "type": "run_created"}', '{"seq": 1, "t": "b", "type": "user_message", "text": "dog roll 0"}',
     '{"seq": 2, "t": "c", "type": "run_finished"}', ""].join("\n"),
};
const fetchMock = vi.fn(async (url: string) =>
  url in files ? new Response(files[url]) : new Response("not found", { status: 404 }));

beforeEach(async () => {
  fake.host.st = { phase: "ready", read_only: false };
  fake.host.replies = {};
  fake.host.handle.mockClear();
  fake.host.boot.mockClear();
  fake.host.listeners.clear();
  fake.storageOk.mockReset().mockResolvedValue(true);
  fake.listRunIds.mockReset().mockResolvedValue([]);
  fetchMock.mockClear();
  vi.stubGlobal("fetch", fetchMock);
  vi.resetModules();
  api = await import("./apiBrowser");
});
afterEach(() => vi.unstubAllGlobals());

const flush = () => new Promise((r) => setTimeout(r, 0));

describe("apiBrowser", () => {
  it("list_merges_gallery_then_browser_runs", async () => {
    fake.host.replies.list = { ok: true, runs: [{ id: "2026-10-26-0900-dog_roll", prompt: "dog roll 0 (folded in your browser)",
                                                  subject: "dog_roll", created: "2026-10-26T09:00:00", status: "running" }] };
    const runs = await api.listRuns();
    expect(runs.map((r) => [r.id, r.kind])).toEqual([["gallery-dog_0", "gallery"], ["2026-10-26-0900-dog_roll", "browser"]]);
    expect(runs[0].browser_foldable).toBe(true);
    expect(fake.host.handle).toHaveBeenCalledWith({ op: "list" });
  });

  it("lists the gallery alone while the engine is loading, or with no gallery built", async () => {
    fake.host.st = { phase: "booting", read_only: false };
    expect((await api.listRuns()).map((r) => r.id)).toEqual(["gallery-dog_0"]);
    expect(fake.host.handle).not.toHaveBeenCalled();
    fetchMock.mockImplementationOnce(async () => new Response("", { status: 404 }));
    fake.host.st = { phase: "ready", read_only: false };
    fake.host.replies.list = { ok: true, runs: [] };
    expect(await api.listRuns()).toEqual([]);
  });

  it("create_run_is_refused_in_free_tier", async () => {
    await expect(api.createRun("a dog")).rejects.toThrow("Design your own arrives with sign-in");
    expect(fake.host.handle).not.toHaveBeenCalled();
  });

  it("gallery_connect_replays_static_log_once", async () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    const c = api.connectRun("gallery-dog_0", onEvent, onError);
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(3));
    await flush();
    expect(onEvent.mock.calls.map((a) => a[0].seq)).toEqual([0, 1, 2]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/gallery/gallery-dog_0/events.jsonl");
    expect(fake.host.handle).not.toHaveBeenCalled();
    c.send({ type: "retry" });
    expect(onError).toHaveBeenCalledWith("examples are read-only");
    expect(fake.host.handle).not.toHaveBeenCalled();
    c.close();
  });

  it("a gallery run closed before its log arrives delivers nothing", async () => {
    const onEvent = vi.fn();
    api.connectRun("gallery-dog_0", onEvent, vi.fn()).close();
    await flush();
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("a browser run gets its backlog, then live events, each once", async () => {
    fake.host.replies.after = { ok: true, events: [{ seq: 0, t: "", type: "run_created" }, { seq: 1, t: "", type: "stage_started" }] };
    const onEvent = vi.fn();
    const c = api.connectRun("r1", onEvent, vi.fn());
    await vi.waitFor(() => expect(onEvent).toHaveBeenCalledTimes(2));
    expect(fake.host.handle).toHaveBeenCalledWith({ op: "after", run_id: "r1", seq: -1 });
    fake.host.emit({ type: "event", run_id: "r1", event: { seq: 1, t: "", type: "stage_started" } });   // already seen
    fake.host.emit({ type: "event", run_id: "other", event: { seq: 2, t: "", type: "x" } });
    fake.host.emit({ type: "event", run_id: "r1", event: { seq: 2, t: "", type: "stage_output" } });
    expect(onEvent.mock.calls.map((a) => a[0].seq)).toEqual([0, 1, 2]);
    c.close();
    fake.host.emit({ type: "event", run_id: "r1", event: { seq: 3, t: "", type: "run_finished" } });
    expect(onEvent).toHaveBeenCalledTimes(3);
  });

  it("send_maps_commands_to_handle_ops", async () => {
    fake.host.replies.after = { ok: true, events: [] };
    const onError = vi.fn();
    const c = api.connectRun("r1", vi.fn(), onError);
    await flush();
    c.send({ type: "approve", choice: "smaller", model: "sonnet" });
    c.send({ type: "approve" });
    c.send({ type: "retry", model: "sonnet" });
    c.send({ type: "cancel" });
    await flush();
    expect(fake.host.handle.mock.calls.slice(1).map((a) => a[0])).toEqual([
      { op: "approve", run_id: "r1", choice: "smaller" },
      { op: "approve", run_id: "r1" },
      { op: "retry", run_id: "r1" },
      { op: "cancel", run_id: "r1" },
    ]);
    c.send({ type: "message", text: "longer legs" });
    expect(onError).toHaveBeenLastCalledWith("Design your own arrives with sign-in");
    expect(fake.host.handle).toHaveBeenCalledTimes(5);
    fake.host.replies.cancel = { ok: false, error: "nothing is running in this run" };
    c.send({ type: "cancel" });
    await vi.waitFor(() => expect(onError).toHaveBeenLastCalledWith("nothing is running in this run"));
  });

  it("fold_tree_sends_gallery_tree_and_label", async () => {
    fake.host.replies.fold_tree = { ok: true, id: "2026-10-26-0900-dog_roll" };
    await expect(api.foldTree("gallery-dog_0")).resolves.toEqual({ id: "2026-10-26-0900-dog_roll" });
    expect(fetchMock).toHaveBeenCalledWith("/gallery/gallery-dog_0/tree.json");
    expect(fake.host.handle).toHaveBeenCalledWith({ op: "fold_tree", tree: JSON.parse(treeText),
                                                    label: "dog roll 0 (folded in your browser)" });
    fake.host.replies.fold_tree = { ok: false, error: "another run is already running (x); wait or cancel it" };
    await expect(api.foldTree("gallery-dog_0")).rejects.toThrow("another run is already running");
  });

  it("storage_unavailable_sets_banner", async () => {
    fake.host.replies.status = { ok: true, llm_ok: false, llm_error: "Design your own arrives with sign-in", busy: null };
    fake.storageOk.mockResolvedValue(false);
    expect(await api.getStatus()).toEqual({
      llm_ok: false, llm_error: "Design your own arrives with sign-in", busy: null, read_only: false,
      banner: "This browser isn't saving runs (private window or storage full); folds still work but vanish when you close the tab.",
    });
    fake.storageOk.mockResolvedValue(true);
    expect((await api.getStatus()).banner).toBeUndefined();
  });

  it("an engine or tab banner outranks the storage banner, and status resolves before boot", async () => {
    fake.storageOk.mockResolvedValue(false);
    fake.host.st = { phase: "read_only", read_only: true, banner: "Pleatwright is open in another tab; this tab can browse but not fold." };
    expect(await api.getStatus()).toMatchObject({ read_only: true, busy: null,
                                              banner: "Pleatwright is open in another tab; this tab can browse but not fold." });
    fake.host.st = { phase: "booting", read_only: false };
    fake.storageOk.mockResolvedValue(true);
    expect(await api.getStatus()).toEqual({ llm_ok: false, llm_error: "Design your own arrives with sign-in", busy: null,
                                        read_only: false, banner: undefined });
    expect(fake.host.handle).not.toHaveBeenCalled();
  });

  it("a visit with no stored runs never loads the engine", async () => {
    fake.host.st = { phase: "idle", read_only: false };
    expect(await api.getStatus()).toEqual({ llm_ok: false, llm_error: "Design your own arrives with sign-in", busy: null,
                                        read_only: false, banner: undefined });
    expect((await api.listRuns()).map((r) => r.id)).toEqual(["gallery-dog_0"]);
    await api.getStatus();
    await flush();
    expect(fake.listRunIds).toHaveBeenCalledTimes(1);
    expect(fake.host.boot).not.toHaveBeenCalled();
    expect(fake.host.handle).not.toHaveBeenCalled();
  });

  it("stored runs load the engine at page load", async () => {
    fake.host.st = { phase: "idle", read_only: false };
    fake.listRunIds.mockResolvedValue(["2026-10-26-0900-dog_roll"]);
    await api.getStatus();
    await vi.waitFor(() => expect(fake.host.boot).toHaveBeenCalledTimes(1));
    await api.getStatus();
    await flush();
    expect(fake.host.boot).toHaveBeenCalledTimes(1);
  });

  it("unreadable storage is no stored runs", async () => {
    fake.host.st = { phase: "idle", read_only: false };
    fake.listRunIds.mockRejectedValue(new fake.StorageUnavailable("IndexedDB is not available"));
    await api.getStatus();
    await flush();
    expect(fake.host.boot).not.toHaveBeenCalled();
  });

  it("a storage probe that passed is not repeated on every status poll", async () => {
    for (let i = 0; i < 3; i++) expect((await api.getStatus()).banner).toBeUndefined();
    expect(fake.storageOk).toHaveBeenCalledTimes(1);
  });

  it("a failed probe, or a storage error since, probes again", async () => {
    fake.storageOk.mockResolvedValue(false);
    await api.getStatus();
    await api.getStatus();
    expect(fake.storageOk).toHaveBeenCalledTimes(2);
    fake.storageOk.mockResolvedValue(true);
    await api.getStatus();
    await api.getStatus();
    expect(fake.storageOk).toHaveBeenCalledTimes(3);
    fake.host.replies.delete = { ok: false, error: "StorageUnavailable: browser storage is full: QuotaExceededError" };
    await expect(api.deleteRun("r1")).rejects.toThrow("browser storage is full");
    fake.storageOk.mockResolvedValue(false);
    expect((await api.getStatus()).banner).toMatch(/^This browser isn't saving runs/);
    expect(fake.storageOk).toHaveBeenCalledTimes(4);
  });

  it("examples cannot be deleted; a browser run is deleted through the manager", async () => {
    await expect(api.deleteRun("gallery-dog_0")).rejects.toThrow("examples are read-only");
    await api.deleteRun("r1");
    expect(fake.host.handle).toHaveBeenCalledWith({ op: "delete", run_id: "r1" });
    fake.host.replies.delete = { ok: false, error: "this run is still running; cancel it first" };
    await expect(api.deleteRun("r1")).rejects.toThrow("this run is still running");
  });

  it("file URLs live under the site base, served by the service worker", () => {
    expect(api.fileUrl("2026-10-26 dog", "Dog roll 0_46/solving cp.svg"))
      .toBe("/runs/2026-10-26%20dog/files/Dog%20roll%200_46/solving%20cp.svg");
  });

  it("an example's file URLs are its static files, which need no service worker", () => {
    expect(api.fileUrl("gallery-dog_0", "Dog roll 0_46/solving_cp.svg"))
      .toBe("/gallery/gallery-dog_0/Dog%20roll%200_46/solving_cp.svg");
    expect(api.downloadName("gallery-dog_0", "Dog roll 0_46/solving_cp.svg")).toBe("gallery-dog_0_solving_cp.svg");
  });
});

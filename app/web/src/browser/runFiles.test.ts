import "fake-indexeddb/auto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { StorageUnavailable, deleteRun, getFile, listRunIds, putFiles, readRun, storageOk } from "./runFiles";

const bytes = (...n: number[]) => new Uint8Array(n);
const clear = async () => { for (const id of await listRunIds()) await deleteRun(id); };

afterEach(async () => { vi.restoreAllMocks(); vi.unstubAllGlobals(); await clear(); });

describe("runFiles", () => {
  it("round_trips_files", async () => {
    await putFiles("dog_0", { "events.jsonl": bytes(1, 2), "Dog_54/packing_cp.svg": bytes(3, 4, 5) });
    expect(await readRun("dog_0")).toEqual({ "events.jsonl": bytes(1, 2), "Dog_54/packing_cp.svg": bytes(3, 4, 5) });
    const blob = await getFile("dog_0", "Dog_54/packing_cp.svg");
    expect(new Uint8Array(await blob!.arrayBuffer())).toEqual(bytes(3, 4, 5));
    expect(await getFile("dog_0", "nope.json")).toBeNull();
    expect(await readRun("cat_0")).toEqual({});
  });

  it("overwrites a file put twice", async () => {
    await putFiles("dog_0", { "tree.json": bytes(1) });
    await putFiles("dog_0", { "tree.json": bytes(9) });
    expect(await readRun("dog_0")).toEqual({ "tree.json": bytes(9) });
  });

  it("lists_run_ids_once", async () => {
    await putFiles("b_1", { "events.jsonl": bytes(1), "tree.json": bytes(2), "layout/x.svg": bytes(3) });
    await putFiles("a_0", { "events.jsonl": bytes(1) });
    await putFiles("b_1", { "model.fold": bytes(4) });
    expect(await listRunIds()).toEqual(["a_0", "b_1"]);
  });

  it("delete_removes_every_file_of_the_run_only", async () => {
    await putFiles("a", { "events.jsonl": bytes(1), "layout/x.svg": bytes(2), "M_9/overview.png": bytes(3) });
    await putFiles("ab", { "events.jsonl": bytes(4) });
    await putFiles("a-b", { "events.jsonl": bytes(5) });
    await deleteRun("a");
    expect(await readRun("a")).toEqual({});
    expect(await readRun("ab")).toEqual({ "events.jsonl": bytes(4) });
    expect(await readRun("a-b")).toEqual({ "events.jsonl": bytes(5) });
    expect(await listRunIds()).toEqual(["a-b", "ab"]);
  });

  it("put_quota_error_is_reported", async () => {
    const quota = new DOMException("full", "QuotaExceededError");
    vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(() => { throw quota; });
    await expect(putFiles("dog_0", { "events.jsonl": bytes(1) })).rejects.toBeInstanceOf(StorageUnavailable);
  });

  it("put_quota_error_midway_commits_nothing", async () => {
    const real = IDBObjectStore.prototype.put;
    let n = 0;
    vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(function (this: IDBObjectStore, ...a: Parameters<typeof real>) {
      if (++n === 2) throw new DOMException("full", "QuotaExceededError");
      return real.apply(this, a);
    });
    await expect(putFiles("dog_0", { "a": bytes(1), "b": bytes(2), "c": bytes(3) }))
      .rejects.toBeInstanceOf(StorageUnavailable);
    vi.restoreAllMocks();
    expect(await readRun("dog_0")).toEqual({});
    expect(await listRunIds()).toEqual([]);
  });

  it("reports a quota abort raised by the transaction as storage full", async () => {
    const real = IDBObjectStore.prototype.put;
    vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(function (this: IDBObjectStore, ...a: Parameters<typeof real>) {
      const req = real.apply(this, a);
      queueMicrotask(() => {
        // What a browser reports when the disk fills while the transaction commits.
        Object.defineProperty(this.transaction, "error", { value: new DOMException("full", "QuotaExceededError") });
        this.transaction.abort();
      });
      return req;
    });
    const err = await putFiles("dog_0", { "events.jsonl": bytes(1) }).catch((e) => e);
    expect(err).toBeInstanceOf(StorageUnavailable);
    expect(err.message).toContain("full");
  });

  it("keeps lookalike run ids and awkward paths exact", async () => {
    const ids = ["a", "a0", "a.b", "a_b"];
    const rel = "Dog roll 0_46/solving_cp.svg";
    for (const [i, id] of ids.entries()) await putFiles(id, { [rel]: bytes(i), "events.jsonl": bytes(i) });
    expect((await listRunIds()).sort()).toEqual([...ids].sort());
    for (const [i, id] of ids.entries()) expect(await readRun(id)).toEqual({ [rel]: bytes(i), "events.jsonl": bytes(i) });
    await deleteRun("a");
    expect((await listRunIds()).sort()).toEqual(["a.b", "a0", "a_b"]);
    for (const id of ["a0", "a.b", "a_b"]) expect(Object.keys(await readRun(id)).sort()).toEqual(["events.jsonl", rel].sort());
    await deleteRun("a.b");
    expect((await listRunIds()).sort()).toEqual(["a0", "a_b"]);
  });

  it("storageOk is true when IndexedDB works", async () => {
    expect(await storageOk()).toBe(true);
  });

  // Safari private windows (and Playwright's WebKit) open IndexedDB but refuse Blob values:
  // "UnknownError: Error preparing Blob/File data to be stored in object store".
  const refuseBlobs = () => {
    const real = IDBObjectStore.prototype.put;
    vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(function (this: IDBObjectStore, ...a: Parameters<typeof real>) {
      if (a[0] instanceof Blob) throw new DOMException("Error preparing Blob/File data to be stored in object store", "UnknownError");
      return real.apply(this, a);
    });
  };

  it("stores each file as an ArrayBuffer of exactly its bytes, so a store that refuses Blobs works", async () => {
    refuseBlobs();
    const view = bytes(9, 1, 2, 9).subarray(1, 3);           // a view into a larger buffer
    await putFiles("dog_0", { "tree.json": view });
    const raw = await new Promise<unknown>((resolve, reject) => {
      const open = indexedDB.open("pleatwright", 1);
      open.onsuccess = () => {
        const req = open.result.transaction("files", "readonly").objectStore("files").get("dog_0/tree.json");
        req.onsuccess = () => { resolve(req.result); open.result.close(); };
        req.onerror = () => reject(req.error);
      };
      open.onerror = () => reject(open.error);
    });
    expect(raw).toBeInstanceOf(ArrayBuffer);
    expect(new Uint8Array(raw as ArrayBuffer)).toEqual(bytes(1, 2));
    expect(await readRun("dog_0")).toEqual({ "tree.json": bytes(1, 2) });
    const blob = await getFile("dog_0", "tree.json");
    expect(blob).toBeInstanceOf(Blob);
    expect(new Uint8Array(await blob!.arrayBuffer())).toEqual(bytes(1, 2));
  });

  it("storageOk is false when the store opens but cannot write", async () => {
    vi.spyOn(IDBObjectStore.prototype, "put").mockImplementation(() => {
      throw new DOMException("Error preparing Blob/File data to be stored in object store", "UnknownError");
    });
    expect(await storageOk()).toBe(false);
  });

  it("storageOk's probe write leaves no run and no key behind", async () => {
    await putFiles("dog_0", { "tree.json": bytes(1) });
    expect(await storageOk()).toBe(true);
    expect(await listRunIds()).toEqual(["dog_0"]);
    const keys = await new Promise<IDBValidKey[]>((resolve, reject) => {
      const open = indexedDB.open("pleatwright", 1);
      open.onsuccess = () => {
        const req = open.result.transaction("files", "readonly").objectStore("files").getAllKeys();
        req.onsuccess = () => { resolve(req.result); open.result.close(); };
        req.onerror = () => reject(req.error);
      };
      open.onerror = () => reject(open.error);
    });
    expect(keys).toEqual(["dog_0/tree.json"]);
  });
});

describe("runFiles without IndexedDB", () => {
  it("is StorageUnavailable and storageOk is false, never throwing", async () => {
    vi.resetModules();
    vi.stubGlobal("indexedDB", undefined);
    const m = await import("./runFiles");
    expect(await m.storageOk()).toBe(false);
    await expect(m.putFiles("a", { "x": bytes(1) })).rejects.toBeInstanceOf(m.StorageUnavailable);
    await expect(m.listRunIds()).rejects.toBeInstanceOf(m.StorageUnavailable);
  });

  it("is StorageUnavailable when open errors, as in a Firefox private window", async () => {
    vi.resetModules();
    vi.stubGlobal("indexedDB", { open: () => {
      const req: Partial<IDBOpenDBRequest> = { error: new DOMException("denied", "InvalidStateError") };
      queueMicrotask(() => req.onerror?.(new Event("error")));
      return req;
    } });
    const m = await import("./runFiles");
    expect(await m.storageOk()).toBe(false);
    await expect(m.readRun("a")).rejects.toBeInstanceOf(m.StorageUnavailable);
  });
});

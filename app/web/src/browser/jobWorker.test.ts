import { afterEach, describe, expect, it, vi } from "vitest";

// The job worker module installs its handler on `self` when imported: a fake scope, and a
// fake Python whose job posts `script` in order.
const fake = vi.hoisted(() => ({ script: [] as unknown[][] }));
vi.mock("./pyodideBoot", () => ({
  heapMb: () => 7,
  bootPython: async () => ({
    FS: { mkdirTree() {}, writeFile() {}, readFile: () => new Uint8Array() },
    toPy: () => ({ destroy() {} }),
    pyimport: () => ({ run_job: (_k: string, _o: string, _kw: unknown, post: (m: unknown) => void) => {
      for (const m of fake.script) post(m);
    } }),
  }),
}));

/** The worker's posts; `refuse(m)` makes that postMessage throw (a message that cannot be cloned). */
async function startJob(script: unknown[][], refuse: (m: any) => boolean) {
  fake.script = script;
  const sent: any[] = [];
  const scope = {
    onmessage: null as ((e: { data: unknown }) => Promise<void>) | null,
    postMessage(m: any) {
      if (refuse(m)) throw new DOMException("could not be cloned", "DataCloneError");
      sent.push(m);
    },
  };
  vi.stubGlobal("self", scope);
  vi.resetModules();
  await import("./jobWorker");
  await scope.onmessage!({ data: { type: "start", kind: "fold", out_dir: "/runs/r", files: {}, kwargs: {} } });
  return sent;
}

afterEach(() => vi.unstubAllGlobals());

describe("jobWorker", () => {
  it("posts each message, the terminal one with the heap size", async () => {
    const sent = await startJob([["stage", "packing", {}, null], ["done", null, {}, null]], () => false);
    expect(sent).toEqual([
      { type: "msg", msg: ["stage", "packing", {}, null] },
      { type: "msg", msg: ["done", null, {}, null], heap_mb: 7 },
    ]);
  });

  it("a terminal message that cannot be sent is a dead job, not silence", async () => {
    const sent = await startJob([["stage", "packing", {}, null], ["done", null, {}, null]],
                                (m) => m.type === "msg" && m.msg[0] === "done");
    expect(sent).toEqual([
      { type: "msg", msg: ["stage", "packing", {}, null] },
      { type: "dead", reason: "could not be cloned" },
    ]);
  });
});

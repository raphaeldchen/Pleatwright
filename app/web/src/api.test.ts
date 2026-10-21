import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { connectRun, createRun, deleteRun, downloadName } from "./api";
import type { PwEvent } from "./types";

class FakeWS {
  static OPEN = 1;
  static instances: FakeWS[] = [];
  readyState = 0;
  onmessage: ((m: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number; reason: string }) => void) | null = null;
  onopen: (() => void) | null = null;
  sent: string[] = [];
  closeCalled = false;
  constructor(public url: string) { FakeWS.instances.push(this); }
  send(s: string) { this.sent.push(s); }
  close() { this.closeCalled = true; }
  // test helpers
  open() { this.readyState = 1; this.onopen?.(); }
  emit(d: unknown) { this.onmessage?.({ data: typeof d === "string" ? d : JSON.stringify(d) }); }
  drop(code = 1006, reason = "") { this.readyState = 3; this.onclose?.({ code, reason }); }
}

beforeEach(() => {
  FakeWS.instances = [];
  vi.useFakeTimers();
  vi.stubGlobal("WebSocket", FakeWS);
  vi.stubGlobal("location", { protocol: "http:", host: "127.0.0.1:8000" });
});
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

const ev = (seq: number): PwEvent => ({ seq, t: "", type: "assistant_message", text: "x" });

describe("connectRun", () => {
  it("close() inside the reconnect window creates no new socket", () => {
    const c = connectRun("r1", vi.fn(), vi.fn());
    FakeWS.instances[0].drop(1006);
    c.close();
    vi.advanceTimersByTime(60_000);
    expect(FakeWS.instances.length).toBe(1);
  });

  it("a 1008 close is terminal: onError, no reconnect", () => {
    const onError = vi.fn();
    connectRun("r1", vi.fn(), onError);
    FakeWS.instances[0].drop(1008, "origin not allowed");
    vi.advanceTimersByTime(60_000);
    expect(FakeWS.instances.length).toBe(1);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBe("cannot open this run: origin not allowed");
  });

  it("a normal close reconnects with ?after=<last seq seen>", () => {
    const onEvent = vi.fn();
    connectRun("r1", onEvent, vi.fn());
    expect(FakeWS.instances[0].url).toBe("ws://127.0.0.1:8000/ws/runs/r1?after=-1");
    FakeWS.instances[0].emit(ev(3));
    FakeWS.instances[0].emit(ev(4));
    FakeWS.instances[0].drop(1006);
    vi.advanceTimersByTime(1000);
    expect(FakeWS.instances.length).toBe(2);
    expect(FakeWS.instances[1].url).toBe("ws://127.0.0.1:8000/ws/runs/r1?after=4");
    expect(onEvent).toHaveBeenCalledTimes(2);
  });

  it("backs off 1s, 2s, 4s ... capped at 10s, and resets after a message", () => {
    const onError = vi.fn();
    connectRun("r1", vi.fn(), onError);
    FakeWS.instances[0].open();                 // once opened, reconnect never gives up
    const gaps: number[] = [];
    for (let i = 0; i < 6; i++) {
      FakeWS.instances.at(-1)!.drop(1006);
      let waited = 0;
      const n = FakeWS.instances.length;
      while (FakeWS.instances.length === n) { vi.advanceTimersByTime(100); waited += 100; }
      gaps.push(waited);
    }
    expect(gaps).toEqual([1000, 2000, 4000, 8000, 10000, 10000]);
    expect(onError).not.toHaveBeenCalled();
    FakeWS.instances.at(-1)!.emit(ev(1));
    FakeWS.instances.at(-1)!.drop(1006);
    const n = FakeWS.instances.length;
    vi.advanceTimersByTime(1000);
    expect(FakeWS.instances.length).toBe(n + 1);
  });

  it("never opened: gives up after 3 failed handshakes with exactly one onError", () => {
    const onError = vi.fn();
    connectRun("r1", vi.fn(), onError);
    for (let i = 0; i < 3; i++) {
      FakeWS.instances.at(-1)!.drop(1006);       // browsers report a rejected handshake as 1006
      vi.advanceTimersByTime(10_000);
    }
    vi.advanceTimersByTime(120_000);
    expect(FakeWS.instances.length).toBe(3);
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith("cannot open this run (unknown run or not allowed)");
  });

  it("opened once: keeps reconnecting past 3 drops with no onError (server restart)", () => {
    const onError = vi.fn();
    connectRun("r1", vi.fn(), onError);
    FakeWS.instances[0].open();
    for (let i = 0; i < 6; i++) {
      FakeWS.instances.at(-1)!.drop(1006);
      vi.advanceTimersByTime(10_000);
    }
    expect(FakeWS.instances.length).toBe(7);
    expect(onError).not.toHaveBeenCalled();
  });

  it("a message counts as having opened", () => {
    const onError = vi.fn();
    connectRun("r1", vi.fn(), onError);
    FakeWS.instances[0].emit(ev(0));
    for (let i = 0; i < 5; i++) {
      FakeWS.instances.at(-1)!.drop(1006);
      vi.advanceTimersByTime(10_000);
    }
    expect(FakeWS.instances.length).toBe(6);
    expect(onError).not.toHaveBeenCalled();
  });

  it("send() after close() reports 'connection closed'", () => {
    const onError = vi.fn();
    const c = connectRun("r1", vi.fn(), onError);
    FakeWS.instances[0].open();
    c.close();
    c.send({ type: "approve" });
    expect(onError).toHaveBeenCalledWith("connection closed");
    expect(FakeWS.instances[0].sent).toEqual([]);
  });

  it("error frames without a seq go to onError, not onEvent", () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    connectRun("r1", onEvent, onError);
    FakeWS.instances[0].emit({ type: "error", message: "bad command" });
    expect(onError).toHaveBeenCalledWith("bad command");
    expect(onEvent).not.toHaveBeenCalled();
  });

  it("a malformed frame calls onError and the stream continues", () => {
    const onEvent = vi.fn();
    const onError = vi.fn();
    connectRun("r1", onEvent, onError);
    FakeWS.instances[0].emit("not json{");
    FakeWS.instances[0].emit(ev(0));
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onEvent).toHaveBeenCalledTimes(1);
  });
});

describe("createRun", () => {
  const stubFetch = (status: number, body: string) =>
    vi.stubGlobal("fetch", vi.fn(async () => new Response(body, { status })));

  it("returns the id on success", async () => {
    stubFetch(200, '{"id":"abc"}');
    await expect(createRun("a bird")).resolves.toEqual({ id: "abc" });
  });
  it("surfaces the server's detail on 409", async () => {
    stubFetch(409, '{"detail":"a run is already active"}');
    await expect(createRun("a bird")).rejects.toThrow("a run is already active");
  });
  it("falls back to HTTP <status> for a non-JSON error body", async () => {
    stubFetch(502, "<html>bad gateway</html>");
    await expect(createRun("a bird")).rejects.toThrow("HTTP 502");
  });
});

describe("downloadName", () => {
  it("prefixes the run id so downloads from different runs never collide", () => {
    expect(downloadName("2026-10-07-1739-bird", "Bird_40/solving_cp.svg")).toBe("2026-10-07-1739-bird_solving_cp.svg");
    expect(downloadName("2026-10-07-1739-bird", "Bird_40/overview.png")).toBe("2026-10-07-1739-bird_overview.png");
    expect(downloadName("r", "model.fold")).toBe("r_model.fold");
  });
});

describe("deleteRun", () => {
  it("DELETEs the run and throws the server's reason when refused", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "this run is still running; cancel it first" }),
                                          { status: 409 }))
      .mockResolvedValueOnce(new Response("oops", { status: 500 }));
    vi.stubGlobal("fetch", fetchMock);
    await deleteRun("2026-10-11-0900-moose");
    expect(fetchMock).toHaveBeenCalledWith("/runs/2026-10-11-0900-moose", { method: "DELETE" });
    await expect(deleteRun("2026-10-11-0900-moose")).rejects.toThrow("cancel it first");
    await expect(deleteRun("2026-10-11-0900-moose")).rejects.toThrow("HTTP 500");
  });
});

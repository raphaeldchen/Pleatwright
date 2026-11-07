import { describe, expect, it, vi } from "vitest";
import { ensureControlled, RELOAD_FLAG, type ControlDeps } from "./swControl";

class FakeSw extends EventTarget {
  constructor(public state: string) { super(); }
  become(state: string) { this.state = state; this.dispatchEvent(new Event("statechange")); }
}

class FakeContainer extends EventTarget {
  controller: object | null = null;
  constructor(public ready: Promise<{ active: FakeSw | null }>) { super(); }
  claim() { this.controller = {}; this.dispatchEvent(new Event("controllerchange")); }
}

function setup(sw: FakeSw, flag: string | null = null) {
  const container = new FakeContainer(Promise.resolve({ active: sw }));
  const store = new Map<string, string>(flag === null ? [] : [[RELOAD_FLAG, flag]]);
  const storage = {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, v); },
    removeItem: (k: string) => { store.delete(k); },
  };
  const reload = vi.fn();
  const deps: ControlDeps = { container, storage, reload, graceMs: 20 };
  return { container, store, reload, deps };
}

describe("ensureControlled", () => {
  it("a controlled page stays, and clears the reload flag", async () => {
    const s = setup(new FakeSw("activated"), "1");
    s.container.controller = {};
    await expect(ensureControlled(s.deps)).resolves.toBe("controlled");
    expect(s.reload).not.toHaveBeenCalled();
    expect(s.store.has(RELOAD_FLAG)).toBe(false);
  });

  it("a first visit waits for the new worker's claim instead of reloading", async () => {
    const sw = new FakeSw("activating");
    const s = setup(sw);
    const p = ensureControlled(s.deps);
    await new Promise((r) => setTimeout(r, 5));
    s.container.claim();
    sw.become("activated");
    await expect(p).resolves.toBe("controlled");
    expect(s.reload).not.toHaveBeenCalled();
  });

  it("an uncontrolled page under an active worker (Shift+Reload) reloads once", async () => {
    const s = setup(new FakeSw("activated"));
    await expect(ensureControlled(s.deps)).resolves.toBe("reloaded");
    expect(s.reload).toHaveBeenCalledTimes(1);
    expect(s.store.get(RELOAD_FLAG)).toBe("1");
  });

  it("never reloads twice: a page still uncontrolled after its reload stays as it is", async () => {
    const s = setup(new FakeSw("activated"), "1");
    await expect(ensureControlled(s.deps)).resolves.toBe("gave_up");
    expect(s.reload).not.toHaveBeenCalled();
  });

  it("without session storage there is no guard, so no reload", async () => {
    const s = setup(new FakeSw("activated"));
    await expect(ensureControlled({ ...s.deps, storage: null })).resolves.toBe("gave_up");
    const throwing = { getItem: () => null, setItem: () => { throw new Error("SecurityError"); }, removeItem: () => {} };
    await expect(ensureControlled({ ...s.deps, storage: throwing })).resolves.toBe("gave_up");
    expect(s.reload).not.toHaveBeenCalled();
  });
});

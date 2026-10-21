import { describe, expect, it } from "vitest";
import { applyPref, HEAD_SCRIPT, nextPref, readPref, STORAGE_KEY, type PrefStore } from "./theme";

function memStore(init: Record<string, string> = {}): PrefStore & { data: Record<string, string> } {
  const data = { ...init };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = v; },
    removeItem: (k) => { delete data[k]; },
  };
}
const throwing: PrefStore = {
  getItem: () => { throw new Error("blocked"); },
  setItem: () => { throw new Error("blocked"); },
  removeItem: () => { throw new Error("blocked"); },
};
function fakeRoot() {
  const attrs: Record<string, string> = {};
  return { attrs,
           setAttribute: (n: string, v: string) => { attrs[n] = v; },
           removeAttribute: (n: string) => { delete attrs[n]; } };
}

describe("readPref", () => {
  it.each([["light", "light"], ["dark", "dark"], ["system", "system"], ["blue", "system"]])(
    "stored %s reads as %s", (stored, want) => {
      expect(readPref(memStore({ [STORAGE_KEY]: stored }))).toBe(want);
    });
  it("a missing key, no storage and a throwing storage all read as system", () => {
    expect(readPref(memStore())).toBe("system");
    expect(readPref(null)).toBe("system");
    expect(readPref(throwing)).toBe("system");
  });
});

describe("nextPref", () => {
  it("cycles system → light → dark → system", () => {
    expect(nextPref("system")).toBe("light");
    expect(nextPref("light")).toBe("dark");
    expect(nextPref("dark")).toBe("system");
  });
});

describe("applyPref", () => {
  it("light/dark set the attribute and store the choice", () => {
    const root = fakeRoot(), s = memStore();
    applyPref("dark", root, s);
    expect(root.attrs["data-theme"]).toBe("dark");
    expect(s.data[STORAGE_KEY]).toBe("dark");
  });
  it("system removes both the attribute and the key", () => {
    const root = fakeRoot(), s = memStore({ [STORAGE_KEY]: "light" });
    root.setAttribute("data-theme", "light");
    applyPref("system", root, s);
    expect(root.attrs).toEqual({});
    expect(s.data).toEqual({});
  });
  it("still sets the attribute when storage throws", () => {
    const root = fakeRoot();
    expect(() => applyPref("light", root, throwing)).not.toThrow();
    expect(root.attrs["data-theme"]).toBe("light");
  });
});

describe("HEAD_SCRIPT agrees with readPref + applyPref", () => {
  const viaHead = (storage: PrefStore) => {
    const root = fakeRoot();
    new Function("localStorage", "document", HEAD_SCRIPT)(storage, { documentElement: root });
    return root.attrs["data-theme"] ?? null;
  };
  const viaModule = (storage: PrefStore) => {
    const root = fakeRoot();
    applyPref(readPref(storage), root, memStore());
    return root.attrs["data-theme"] ?? null;
  };
  it.each([["light"], ["dark"], ["system"], ["junk"], [null]])("stored %s", (stored) => {
    const init = stored == null ? {} : { [STORAGE_KEY]: stored };
    expect(viaHead(memStore(init))).toBe(viaModule(memStore(init)));
  });
  it("a throwing storage leaves no attribute either way", () => {
    expect(viaHead(throwing)).toBe(null);
    expect(viaModule(throwing)).toBe(null);
  });
});

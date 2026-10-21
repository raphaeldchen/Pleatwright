import { describe, expect, it } from "vitest";
import { MODEL_KEY, nextModel, readModel, saveModel } from "./model";
import type { PrefStore } from "./theme";

const MODELS = [{ key: "haiku", id: "claude-haiku-5-5", label: "Haiku 5.5" },
                { key: "sonnet", id: "claude-sonnet-5", label: "Sonnet 5" }];
const mem = (init: Record<string, string> = {}): PrefStore & { data: Record<string, string> } => {
  const data = { ...init };
  return { data, getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = v; },
           removeItem: (k) => { delete data[k]; } };
};
const throwing: PrefStore = { getItem: () => { throw new Error("x"); }, setItem: () => { throw new Error("x"); },
                              removeItem: () => { throw new Error("x"); } };

describe("model choice", () => {
  it("uses the server's default until a known choice is stored", () => {
    expect(readModel(mem(), MODELS, "haiku")).toBe("haiku");
    expect(readModel(mem({ [MODEL_KEY]: "sonnet" }), MODELS, "haiku")).toBe("sonnet");
    expect(readModel(mem({ [MODEL_KEY]: "gpt-9" }), MODELS, "haiku")).toBe("haiku");   // no longer offered
    expect(readModel(throwing, MODELS, "haiku")).toBe("haiku");
    expect(readModel(null, MODELS, "haiku")).toBe("haiku");
  });
  it("cycles through the offered models", () => {
    expect(nextModel(MODELS, "haiku")).toBe("sonnet");
    expect(nextModel(MODELS, "sonnet")).toBe("haiku");
    expect(nextModel(MODELS, "unknown")).toBe("haiku");
    expect(nextModel([], "haiku")).toBe("haiku");
  });
  it("remembers the choice and survives blocked storage", () => {
    const s = mem();
    saveModel(s, "sonnet");
    expect(s.data[MODEL_KEY]).toBe("sonnet");
    expect(() => saveModel(throwing, "sonnet")).not.toThrow();
  });
});

import { describe, expect, it, vi } from "vitest";
import { buffersOf, denull, errorText, jobMessage, nullify } from "./pyValues";

describe("pyValues", () => {
  it("nullify and denull swap null and undefined deep inside data, leaving bytes alone", () => {
    const bytes = new Uint8Array([1]);
    expect(nullify({ a: undefined, b: [1, undefined], c: bytes })).toEqual({ a: null, b: [1, null], c: bytes });
    expect(denull({ nodes: [{ parent: null }], c: bytes })).toEqual({ nodes: [{ parent: undefined }], c: bytes });
    expect(nullify({ c: bytes }).c).toBe(bytes);
  });

  it("buffersOf lists each buffer once", () => {
    const a = new Uint8Array([1]);
    const b = new Uint8Array([2]);
    expect(buffersOf(["done", null, {}, { x: a, y: b, z: a }])).toEqual([a.buffer, b.buffer]);
  });

  it("jobMessage reads a message's files back from the filesystem, not from the converted bytes", () => {
    const read = vi.fn((path: string) => new TextEncoder().encode(`<svg>${path}</svg>`));
    const garbage = new Uint8Array([0, 0, 0, 0xef]);   // what toJs gives for a bytes object above 2 GiB
    const info = { files: ["/runs/r/A_1/shaping_cp.svg"] };
    const m = jobMessage(["stage", "shaping", info, { "A_1/shaping_cp.svg": garbage }], "/runs/r", read);
    expect(m.slice(0, 3)).toEqual(["stage", "shaping", info]);
    expect(new TextDecoder().decode((m[3] as Record<string, Uint8Array>)["A_1/shaping_cp.svg"]))
      .toBe("<svg>/runs/r/A_1/shaping_cp.svg</svg>");
    expect(read).toHaveBeenCalledTimes(1);
    expect(jobMessage(["failed", "solving", "boom"], "/runs/r", read)).toEqual(["failed", "solving", "boom"]);
    expect(read).toHaveBeenCalledTimes(1);
  });

  it("errorText: a Python traceback's last line, else an error's first line", () => {
    const py = Object.assign(new Error("Traceback (most recent call last):\n  File \"x\", line 1\nKeyError: 'run_id'\n"),
                             { name: "PythonError" });
    expect(errorText(py)).toBe("KeyError: 'run_id'");
    expect(errorText(new Error("Failed to load Pillow\nSee https://pyodide.org/en/stable/usage/loading-packages.html")))
      .toBe("Failed to load Pillow");
    expect(errorText("plain")).toBe("plain");
  });
});

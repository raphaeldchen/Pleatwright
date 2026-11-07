// Node check that a job's files reach JS intact when Python's wasm heap is past 2 GiB, as a
// large fold's is (scorpion_0 peaks at 2464 MB). Pyodide 314.0.7 converts a bytes object
// that lies above 2 GiB as other heap memory of the same length (PyProxy.toJs reads
// HEAP8.slice(ptr) with ptr signed), which stored scorpion_0's shaping_cp.svg as binary
// (Task 15b). This fills the heap past 2 GiB, then has jobchild's queue read and post a
// file, converting the message as the job worker does (`jobMessage`).
// Run `npm run fetch-pyodide && npm run bundle-py` first, then
// `node scripts/pyodide-high-heap.mjs` (a few seconds, about 2.2 GB of memory).
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";
import { fromPy, jobMessage } from "../src/browser/pyValues.ts";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const py = await loadPyodide({ indexURL: join(web, "public-site", "pyodide") + "/", stdout: () => {}, stderr: () => {} });
py.unpackArchive(new Uint8Array(readFileSync(join(web, "public-site", "py.zip"))), "zip", { extractDir: "/repo" });

const out = "/runs/high";
const rel = "A_1/shaping_cp.svg";
let converted = null;
let viaJobMessage = null;
py.globals.set("post", (msg) => {
  converted = fromPy(msg)[3][rel];
  viaJobMessage = jobMessage(msg, out, (path) => py.FS.readFile(path))[3][rel];
});
const highId = py.runPython(`
import os, sys
sys.path[:0] = ["/repo/app/browser/py"]
import jobchild

out = "${out}"
os.makedirs(out + "/A_1")
q = jobchild._Queue(out, post)
# fill the heap below 2 GiB (freeing nothing), so the bytes jobchild reads next land above it
ballast = [bytes(1 << 20)]
while id(ballast[-1]) < 2**31:
    ballast += [bytearray(64 << 20), bytes(1 << 20)]
content = b"<svg>" + bytes(range(256)) * 4096 + b"</svg>"
with open(out + "/${rel}", "wb") as f:
    f.write(content)
q.put(("stage", "shaping", {"files": [out + "/${rel}"]}))
id(ballast[-1])
`);
// built here, not converted from Python: that conversion is the one under test
const enc = new TextEncoder();
const expected = new Uint8Array(5 + (1 << 20) + 6);
expected.set(enc.encode("<svg>"));
for (let i = 0; i < 1 << 20; i++) expected[5 + i] = i & 255;
expected.set(enc.encode("</svg>"), 5 + (1 << 20));

const same = (a) => a?.length === expected.length && a.every((v, i) => v === expected[i]);
const heap = py._module.HEAP8.length / 2 ** 20;
console.log(`heap ${heap.toFixed(0)} MB; ballast reaches 0x${highId.toString(16)}; toJs bytes ${same(converted) ? "right" : "WRONG"}`);
if (same(converted)) {
  throw new Error("toJs converted the bytes correctly, so this check did not reach the defect "
                  + "(a newer Pyodide may have fixed it; then jobMessage's read-back can go)");
}
if (!same(viaJobMessage)) throw new Error("jobMessage's file bytes differ from the file jobchild posted");
console.log("high heap ok");

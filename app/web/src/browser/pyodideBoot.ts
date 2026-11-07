// Starts Python in a worker, as scripts/pyodide-smoke.mjs does in Node: the self-hosted
// Pyodide from <base>pyodide/, its four packages, and the runtime modules unpacked from
// <base>py.zip. Nothing comes from another origin.

import type { PyodideInterface } from "pyodide";

const PACKAGES = ["numpy", "matplotlib", "python-sat", "pillow"];
const ROOT = "/repo";

export async function bootPython(): Promise<PyodideInterface> {
  const base = new URL(import.meta.env.BASE_URL, self.location.href).href;
  // A runtime URL, so Vite neither bundles Pyodide nor rewrites the import.
  const { loadPyodide } = await import(/* @vite-ignore */ `${base}pyodide/pyodide.mjs`);
  const py: PyodideInterface = await loadPyodide({ indexURL: `${base}pyodide/` });
  await py.loadPackage(PACKAGES);
  const zip = await fetch(`${base}py.zip`);
  if (!zip.ok) throw new Error(`HTTP ${zip.status} from py.zip`);
  py.unpackArchive(await zip.arrayBuffer(), "zip", { extractDir: ROOT });
  py.runPython(`
import sys
sys.dont_write_bytecode = True
import matplotlib
matplotlib.use("Agg")
sys.path[:0] = ["${ROOT}/mcp_harness", "${ROOT}/app/server", "${ROOT}/app/browser/py"]
`);
  return py;
}

/** The size of Python's wasm heap in MB (it grows and never shrinks; spec §7.3). */
export function heapMb(py: PyodideInterface): number {
  const heap = (py as unknown as { _module?: { HEAP8?: Uint8Array } })._module?.HEAP8;
  return heap ? heap.length / 2 ** 20 : NaN;
}

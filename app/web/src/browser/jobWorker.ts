// A job worker: one pack or fold (jobchild.run_job), the browser's spawned FoldJob/PackJob
// process. The page sends {type: "start", kind, out_dir, files, kwargs}; the files are the
// run's inputs, written at the same absolute out_dir the manager uses. Each message the job
// posts goes back as {type: "msg", msg: [kind, stage, info, files]} (the files read back from
// the worker's filesystem: see `jobMessage`), the terminal one with
// the wasm heap size (`heap_mb`). A job that cannot run, or that ends without a terminal
// message, sends {type: "dead", reason}. The page terminates this worker afterwards.

import { bootPython, heapMb } from "./pyodideBoot";
import { buffersOf, denull, errorText, jobMessage } from "./pyValues";

type Scope = { postMessage(m: unknown, transfer?: Transferable[]): void; onmessage: ((e: MessageEvent) => void) | null };
const scope = self as unknown as Scope;
const send = (m: unknown) => scope.postMessage(m, buffersOf(m));

scope.onmessage = async ({ data }) => {
  if (data?.type !== "start") return;
  scope.onmessage = null;                          // one job per worker
  const { kind, out_dir: outDir, files, kwargs } = data as {
    kind: string; out_dir: string; files: Record<string, Uint8Array>; kwargs: Record<string, unknown> };
  let ended = false;
  try {
    const py = await bootPython();
    for (const [rel, bytes] of Object.entries(files)) {
      if (rel.startsWith("/") || rel.split("/").includes("..")) continue;   // stays inside out_dir
      const path = `${outDir}/${rel}`;
      py.FS.mkdirTree(path.slice(0, path.lastIndexOf("/")));
      py.FS.writeFile(path, bytes);
    }
    const post = (msg: unknown) => {
      if (ended) return;
      const m = jobMessage(msg, outDir, (path) => py.FS.readFile(path));
      const out: Record<string, unknown> = { type: "msg", msg: m };
      const terminal = m[0] === "done" || m[0] === "failed";
      if (terminal) out.heap_mb = heapMb(py);
      send(out);
      if (terminal) ended = true;                  // only once sent: a failed send ends as "dead"
    };
    const pyKwargs = py.toPy(denull(kwargs));
    try {
      py.pyimport("jobchild").run_job(kind, outDir, pyKwargs, post);
    } finally {
      pyKwargs.destroy();
    }
    if (!ended) send({ type: "dead", reason: "the job ended without a result" });
  } catch (e) {
    if (!ended) send({ type: "dead", reason: errorText(e) });
  }
  ended = true;
};

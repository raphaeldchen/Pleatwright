// The manager worker: guided.Manager in Pyodide (pwbrowser.py) over an in-memory runs
// folder filled from IndexedDB. The page (runHost.ts) sends {type: "handle", id, cmd} and
// relays job messages; this worker answers with booted | boot_failed, reply, post,
// start_job and cancel_job.

import { createManagerBridge } from "./managerBridge";
import { bootPython } from "./pyodideBoot";
import { buffersOf, denull, errorText, nullify, takePy } from "./pyValues";
import * as runFiles from "./runFiles";

type Scope = { postMessage(m: unknown, transfer?: Transferable[]): void; onmessage: ((e: MessageEvent) => void) | null };
const scope = self as unknown as Scope;
const send = (m: unknown, transfer: Transferable[] = []) => scope.postMessage(m, transfer);

const { bridge, deliver, eraseRun } = createManagerBridge(runFiles, send);
let handle: ((cmd: unknown) => Promise<unknown>) | null = null;

const ready = (async () => {
  try {
    const py = await bootPython();
    const pw = py.pyimport("pwbrowser");
    await pw.boot(bridge, "/runs");
    handle = pw.handle;
    send({ type: "booted" });
  } catch (e) {
    send({ type: "boot_failed", reason: errorText(e) });
  }
})();

/** pwbrowser.handle(cmd) as plain JS; an exception (anything but Refused) is {ok: false, error}. */
async function run(cmd: Record<string, unknown>): Promise<Record<string, unknown>> {
  await ready;
  if (!handle) return { ok: false, error: "the folding engine is not running" };
  let result: Record<string, unknown>;
  try {
    result = nullify(takePy(await handle(denull(cmd))));
  } catch (e) {
    return { ok: false, error: errorText(e) };
  }
  if (cmd.op === "delete" && result.ok) {
    try { await eraseRun(String(cmd.run_id)); } catch (e) {
      console.warn(`run ${cmd.run_id} is deleted but its stored files remain:`, errorText(e));
    }
  }
  return result;
}

scope.onmessage = async ({ data }) => {
  if (data?.type === "job_message") deliver(data.job_id, data.msg);
  else if (data?.type === "handle") {
    const result = await run(data.cmd);
    send({ type: "reply", id: data.id, result }, buffersOf(result));
  }
};

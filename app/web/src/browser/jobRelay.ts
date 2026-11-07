// The job workers, on the main thread: the browser's spawned FoldJob/PackJob processes.
// Each `start_job` from the manager worker gets a fresh job worker (a fold's Pyodide heap
// never shrinks), whose messages go back to the manager, which queues them for
// `pwbrowser.BrowserJob`. The worker is terminated after its terminal message or on
// `cancel_job` (as the server kills the process). A worker that fails without a terminal
// message is relayed as ["dead", null, reason], the analogue of a process exiting.

import { buffersOf } from "./pyValues";

/** What the run host needs of a Worker (a real one, or a test fake). */
export interface WorkerLike {
  postMessage(message: unknown, transfer?: Transferable[]): void;
  terminate(): void;
  onmessage: ((e: { data: any }) => void) | null;
  onerror: ((e: { message?: string; preventDefault?: () => void }) => void) | null;
  onmessageerror: ((e?: unknown) => void) | null;
}

export interface StartJob {
  type: "start_job"; job_id: string; kind: "fold" | "pack"; out_dir: string;
  files: Record<string, Uint8Array>; kwargs: Record<string, unknown>;
}

/** A job message on its way to the manager worker; `heap_mb` rides on the terminal one. */
export interface JobMessage { type: "job_message"; job_id: string; msg: unknown[]; heap_mb?: number }

export interface HeapRecord { job_id: string; kind: string; heap_mb: number }

export function createJobRelay(makeJob: () => WorkerLike, toManager: (m: JobMessage, transfer: Transferable[]) => void) {
  const live = new Map<string, WorkerLike>();
  const heaps: HeapRecord[] = [];

  /** Ends the job: later messages and errors from its worker are dropped. */
  const end = (jobId: string) => {
    const w = live.get(jobId);
    live.delete(jobId);
    w?.terminate();
  };
  const dead = (jobId: string, reason: string) => {
    toManager({ type: "job_message", job_id: jobId, msg: ["dead", null, reason] }, []);
  };

  function start(req: StartJob): void {
    const { job_id: jobId, kind, out_dir, files, kwargs } = req;
    let w: WorkerLike;
    try {
      w = makeJob();
    } catch (e) {
      dead(jobId, e instanceof Error ? e.message : String(e));
      return;
    }
    live.set(jobId, w);
    const mine = () => live.get(jobId) === w;
    w.onmessage = ({ data }) => {
      if (!mine()) return;
      if (data?.type === "dead") {
        end(jobId);
        dead(jobId, String(data.reason));
        return;
      }
      if (data?.type !== "msg") return;
      const out: JobMessage = { type: "job_message", job_id: jobId, msg: data.msg };
      const terminal = data.msg[0] === "done" || data.msg[0] === "failed";
      if (terminal && typeof data.heap_mb === "number") {
        out.heap_mb = data.heap_mb;
        heaps.push({ job_id: jobId, kind, heap_mb: data.heap_mb });
      }
      if (terminal) end(jobId);
      toManager(out, buffersOf(data.msg));
    };
    w.onerror = (e) => {
      e.preventDefault?.();                         // reported here, not as an uncaught page error
      if (!mine()) return;
      end(jobId);
      dead(jobId, e.message || "the job worker failed");
    };
    w.onmessageerror = () => {
      if (!mine()) return;
      end(jobId);
      dead(jobId, "a message from the job worker could not be read");
    };
    const msg = { type: "start", kind, out_dir, files, kwargs };
    try {
      w.postMessage(msg, buffersOf(files));
    } catch (e) {
      end(jobId);
      dead(jobId, e instanceof Error ? e.message : String(e));
    }
  }

  return {
    start,
    /** Terminates the job's worker; a job that already ended (or never started) is a no-op. */
    cancel: (jobId: string) => end(jobId),
    /** The wasm heap each finished job reached, in MB (spec §7.3 measurements). */
    heaps: (): HeapRecord[] => heaps.slice(),
  };
}

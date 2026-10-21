import type { PwEvent, RunSummary, Status } from "./types";

export type Command = { type: "message"; text: string; model?: string } | { type: "approve"; model?: string; choice?: string }
  | { type: "retry"; model?: string } | { type: "cancel" };

async function getJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} from ${url}`);
  return r.json();
}

export function getStatus(): Promise<Status> {
  return getJson<Status>("/status");
}

export function listRuns(): Promise<RunSummary[]> {
  return getJson<RunSummary[]>("/runs");
}

/** A response's JSON body (null if it has none), throwing the server's `detail` when not ok. */
async function bodyOf(r: Response): Promise<unknown> {
  const text = await r.text();
  let body: unknown = null;
  try { body = JSON.parse(text); } catch { /* not JSON: fall through to the status */ }
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (!r.ok) throw new Error(typeof detail === "string" ? detail : `HTTP ${r.status}`);
  return body;
}

export async function createRun(prompt: string, model?: string): Promise<{ id: string }> {
  const r = await fetch("/runs", { method: "POST", headers: { "content-type": "application/json" },
                                   body: JSON.stringify({ prompt, model }) });
  const body = await bodyOf(r);
  if (!body || typeof (body as { id?: unknown }).id !== "string") {
    throw new Error(`HTTP ${r.status}: unexpected response`);
  }
  return body as { id: string };
}

/** Delete a run's folder for good; the server refuses (409) the run that is still running. */
export async function deleteRun(runId: string): Promise<void> {
  await bodyOf(await fetch(`/runs/${encodeURIComponent(runId)}`, { method: "DELETE" }));
}

export function fileUrl(runId: string, rel: string): string {
  return `/runs/${encodeURIComponent(runId)}/files/${rel.split("/").map(encodeURIComponent).join("/")}`;
}

/** The name a downloaded run file is saved under: the run id, then the file's own name
 *  ("2026-10-07-1739-bird_solving_cp.svg"), so downloads from different runs never collide. */
export function downloadName(runId: string, rel: string): string {
  return `${runId}_${rel.split("/").pop()}`;
}

/** Streams a run's events. Reconnects from the last seq seen with a capped backoff
 *  (1 s, 2 s, 4 s ... 10 s; reset to 1 s by any message). A server that rejects the
 *  handshake (unknown run, disallowed origin: HTTP 403) shows up in a browser as a plain
 *  1006 close, so a connection that has NEVER opened gives up after 3 closes; one that
 *  has opened keeps retrying (a server restart refuses for a while). 1008 is terminal.
 */
export function connectRun(runId: string, onEvent: (e: PwEvent) => void,
                           onError: (message: string) => void) {
  let ws: WebSocket | null = null;
  let last = -1;
  let closed = false;
  let timer: ReturnType<typeof setTimeout> | null = null;
  let delay = 1000;
  let everOpened = false;
  let failedHandshakes = 0;
  const open = () => {
    if (closed) return;
    timer = null;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const sock = new WebSocket(
      `${proto}://${location.host}/ws/runs/${encodeURIComponent(runId)}?after=${last}`);
    ws = sock;
    sock.onopen = () => { everOpened = true; };
    sock.onmessage = (m) => {
      everOpened = true;
      delay = 1000;
      let d: { type?: string; seq?: unknown; message?: string };
      try { d = JSON.parse(m.data); } catch { return onError("malformed message from server"); }
      if (d.type === "error" && d.seq === undefined) return onError(String(d.message));
      if (typeof d.seq !== "number") return;
      last = Math.max(last, d.seq);
      onEvent(d as unknown as PwEvent);
    };
    sock.onclose = (ev) => {
      if (closed || ws !== sock) return;
      if (ev.code === 1008) {
        closed = true;
        return onError(`cannot open this run: ${ev.reason || ev.code}`);
      }
      if (!everOpened && ++failedHandshakes >= 3) {
        closed = true;
        return onError("cannot open this run (unknown run or not allowed)");
      }
      timer = setTimeout(open, delay);
      delay = Math.min(delay * 2, 10_000);
    };
  };
  open();
  return {
    send(cmd: Command) {
      if (closed) return onError("connection closed");
      if (ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify(cmd));
      else onError("not connected; retrying");
    },
    close() {
      closed = true;
      if (timer) clearTimeout(timer);
      timer = null;
      if (ws) { ws.onmessage = null; ws.close(); }   // no stale events after close
    },
  };
}

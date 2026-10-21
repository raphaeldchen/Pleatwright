import { useEffect, useReducer, useRef, useState } from "react";
import { connectRun, createRun, deleteRun, getStatus, listRuns, type Command } from "./api";
import { Chat } from "./components/Chat";
import { RunsSidebar, removeRun } from "./components/RunsSidebar";
import { Stepper } from "./components/Stepper";
import { Viewer } from "./components/Viewer";
import { ToolSlot, ViewerHeader } from "./components/ViewerHeader";
import { emptyView, reduce, selectedOutput } from "./runStore";
import { isNewRunKey } from "./shortcuts";
import { readModel, saveModel } from "./model";
import { safeStorage } from "./theme";
import type { Action, RunSummary, RunView, Status } from "./types";

const hashRun = () => new URLSearchParams(location.hash.slice(1)).get("run");

function viewReducer(v: RunView | null, a: Action | { type: "reset"; id: string | null }) {
  if (a.type === "reset") return a.id ? emptyView(a.id) : null;
  return v ? reduce(v, a) : v;
}

export function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runId, setRunId] = useState<string | null>(hashRun());
  const [view, dispatch] = useReducer(viewReducer, runId ? emptyView(runId) : null);
  const [toast, setToast] = useState<{ message: string; reconnect: boolean } | null>(null);
  // Bumping this forces a fresh connectRun for the same run (connectRun gives up for good
  // after 3 closes of a connection that never opened).
  const [connectNonce, setConnectNonce] = useState(0);
  const [slot, setSlot] = useState<HTMLDivElement | null>(null);
  // The VLM for the next authoring action (first tree, revision, retry). Until the user picks
  // one, the remembered choice or the server's default; the server validates it either way.
  const [picked, setPicked] = useState<string | null>(null);
  const models = status?.models ?? [];
  const model = picked && models.some((m) => m.key === picked)
    ? picked : readModel(safeStorage(), models, status?.default_model ?? "sonnet");
  const pickModel = (k: string) => { setPicked(k); saveModel(safeStorage(), k); };
  const sock = useRef<ReturnType<typeof connectRun> | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const refresh = async () => {
    try {
      const [s, r] = await Promise.all([getStatus(), listRuns()]);
      setStatus(s);
      setRuns(r);
    } catch { /* a server blip: keep the last known state, the next tick retries */ }
  };
  useEffect(() => { refresh(); const i = setInterval(refresh, 3000); return () => clearInterval(i); }, []);
  useEffect(() => {
    const on = () => setRunId(hashRun());
    addEventListener("hashchange", on);
    return () => removeEventListener("hashchange", on);
  }, []);
  useEffect(() => {
    dispatch({ type: "reset", id: runId });
    sock.current?.close();
    sock.current = runId ? connectRun(runId, (event) => dispatch({ type: "event", event }), flash) : null;
    return () => sock.current?.close();
  }, [runId, connectNonce]);
  useEffect(() => () => { if (toastTimer.current) clearTimeout(toastTimer.current); }, []);

  function flash(message: string) {
    const reconnect = message.includes("cannot open this run");
    if (toastTimer.current) clearTimeout(toastTimer.current);
    setToast({ message, reconnect });
    // A give-up toast stays until the user reconnects or dismisses it.
    toastTimer.current = reconnect ? null : setTimeout(() => setToast(null), 4000);
  }
  const reconnect = () => { setToast(null); setConnectNonce((n) => n + 1); };
  const open = (id: string | null) => {
    if (id === runId) { if (id) reconnect(); return; }
    location.hash = id ? `run=${id}` : "";
    setRunId(id);
  };
  const send = (c: Command) => sock.current?.send(c);
  const start = async (prompt: string) => {
    try { const { id } = await createRun(prompt, model); open(id); refresh(); }
    catch (e) { flash((e as Error).message); }
  };
  const select = (key: string) => dispatch({ type: "select", key });
  // "N" starts a new run (see shortcuts.ts). A ref so the once-registered listener calls the current `open`.
  const openRef = useRef(open);
  openRef.current = open;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (isNewRunKey(e)) { e.preventDefault(); openRef.current(null); } };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="shell">
      {status && !status.llm_ok &&
        <div className="banner">{status.llm_error
          ? `Authoring is disabled: ${status.llm_error} — fix .env and restart the app.`
          : "Authoring is disabled — fix .env and restart the app."}</div>}
      <div className="app">
        <RunsSidebar runs={runs} current={runId} onOpen={open} onNew={() => open(null)}
                     onDelete={(r) => removeRun(r, runId, { confirm: (m) => window.confirm(m), del: deleteRun,
                                                            leave: () => open(null), refresh, flash })} />
        <Chat view={view} send={send} onSelect={select} onNewRun={() => open(null)}
              canStart={!!status?.llm_ok && !status?.busy} onStart={start}
              models={models} model={model} onModel={pickModel} />
        <div className="out">
          <div className="viewer">
            <ViewerHeader output={view ? selectedOutput(view) : null} following={!view || view.followLatest}
                          onFollow={() => dispatch({ type: "follow" })} slotRef={setSlot} />
            <div className="canvas">
              <ToolSlot.Provider value={slot}>
                {view
                  ? <Viewer key={selectedOutput(view)?.key ?? "none"} runId={view.id}
                            output={selectedOutput(view)} allOutputs={view.outputs} onSelect={select} />
                  : <div className="viewer-empty">Start a run to see its outputs.</div>}
              </ToolSlot.Provider>
            </div>
          </div>
          {view && <Stepper view={view} onSelect={select} />}
        </div>
      </div>
      {toast && (
        <div className="toast">
          <span>{toast.message}</span>
          {toast.reconnect && runId && <button className="btn" onClick={reconnect}>Reconnect</button>}
          {toast.reconnect && <button className="btn ghost" onClick={() => setToast(null)}>Dismiss</button>}
        </div>)}
    </div>
  );
}

import type { RunSummary } from "../types";
import { ThemeToggle } from "./ThemeToggle";

/** "— TODAY", "— YESTERDAY", else "— YYYY-MM-DD" (local time). */
export function dayLabel(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (d.toDateString() === now.toDateString()) return "— TODAY";
  if (d.toDateString() === y.toDateString()) return "— YESTERDAY";
  const p = (n: number) => String(n).padStart(2, "0");
  return `— ${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

const MARK: Record<RunSummary["status"], string> = { done: "✓", running: "…", waiting: "⏸", failed: "✕", new: "·" };

/** Delete a run after asking; leave it first if it is the one open. Errors (e.g. the run
 *  is still running) are shown, and the run stays. */
export async function removeRun(run: RunSummary, current: string | null, d: {
  confirm: (message: string) => boolean; del: (id: string) => Promise<void>;
  leave: () => void; refresh: () => void; flash: (message: string) => void;
}): Promise<void> {
  if (!d.confirm(`Delete “${run.subject}”? Its folder and every model in it are removed for good.`)) return;
  try { await d.del(run.id); } catch (e) { d.flash((e as Error).message); return; }
  if (run.id === current) d.leave();
  d.refresh();
}

export function RunsSidebar({ runs, current, onOpen, onNew, onDelete }: {
  runs: RunSummary[]; current: string | null; onOpen: (id: string) => void; onNew: () => void;
  onDelete: (run: RunSummary) => void;
}) {
  let lastDay = "";
  return (
    <div className="sidebar">
      <div className="runs">
        <button className="new" onClick={onNew} title="New run (N)">
          <span>[+] New run</span><span className="hint" aria-hidden="true">N</span>
        </button>
        {runs.map((r) => {
          const d = dayLabel(r.created);
          const head = d !== lastDay ? <div className="day">{(lastDay = d)}</div> : null;
          return (
            <div key={r.id}>
              {head}
              <div className="row">
                <button className={`run${r.id === current ? " on" : ""}`} onClick={() => onOpen(r.id)}
                        title={r.prompt} aria-current={r.id === current ? "true" : undefined}>
                  <span>{r.subject}</span>
                  <span className={`mark ${r.status}`} role="img" aria-label={r.status}>{MARK[r.status]}</span>
                </button>
                <button className="del" onClick={() => onDelete(r)} title="Delete run"
                        aria-label={`Delete run ${r.subject}`}>del</button>
              </div>
            </div>);
        })}
      </div>
      <div className="sidebar-foot"><ThemeToggle /></div>
    </div>
  );
}

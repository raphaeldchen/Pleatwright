import { Fragment } from "react";
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

export interface RunGroup { heading: string | null; runs: RunSummary[]; deletable: boolean }

/** The site build marks every row with a `kind`: its examples go under "Examples" (read-only,
 *  so no delete), the visitor's own runs under "Your runs". With no `kind` on any row (the
 *  local server) the list is one ungrouped, deletable group, as it always was. */
export function groupRuns(runs: RunSummary[]): RunGroup[] {
  if (!runs.some((r) => r.kind)) return [{ heading: null, runs, deletable: true }];
  const groups: RunGroup[] = [
    { heading: "Examples", runs: runs.filter((r) => r.kind === "gallery"), deletable: false },
    { heading: "Your runs", runs: runs.filter((r) => r.kind !== "gallery"), deletable: true },
  ];
  return groups.filter((g) => g.runs.length);
}

export function RunsSidebar({ runs, current, onOpen, onNew, onDelete }: {
  runs: RunSummary[]; current: string | null; onOpen: (id: string) => void; onNew: () => void;
  onDelete: (run: RunSummary) => void;
}) {
  return (
    <div className="sidebar">
      <div className="runs">
        <button className="new" onClick={onNew} title="New run (N)">
          <span>[+] New run</span><span className="hint" aria-hidden="true">N</span>
        </button>
        {groupRuns(runs).map((g) => {
          let lastDay = "";
          return (
            <Fragment key={g.heading ?? "all"}>
              {g.heading && <div className="group">{g.heading}</div>}
              {g.runs.map((r) => {
                // Examples share one date, so only the user's own runs get day headings.
                const d = g.deletable ? dayLabel(r.created) : "";
                const head = d && d !== lastDay ? <div className="day">{(lastDay = d)}</div> : null;
                return (
                  <div key={r.id}>
                    {head}
                    <div className="row">
                      <button className={`run${r.id === current ? " on" : ""}`} onClick={() => onOpen(r.id)}
                              title={r.prompt} aria-current={r.id === current ? "true" : undefined}>
                        <span>{r.subject}</span>
                        <span className={`mark ${r.status}`} role="img" aria-label={r.status}>{MARK[r.status]}</span>
                      </button>
                      {g.deletable && (
                        <button className="del" onClick={() => onDelete(r)} title="Delete run"
                                aria-label={`Delete run ${r.subject}`}>del</button>)}
                    </div>
                  </div>);
              })}
            </Fragment>);
        })}
      </div>
      <div className="sidebar-foot"><ThemeToggle /></div>
    </div>
  );
}

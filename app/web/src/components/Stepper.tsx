import { useEffect, useState } from "react";
import { latestByStage } from "../runStore";
import { STAGES, stageLabel, type RunView, type StageStatus } from "../types";

const ICON: Record<StageStatus, string> = { done: "✓", running: "", waiting: "⏸", failed: "✕", skipped: "", todo: "" };

export function Stepper({ view, onSelect }: { view: RunView; onSelect: (k: string) => void }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    if (!view.running) return;
    const i = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(i);
  }, [view.running]);
  const latest = latestByStage(view);
  return (
    <div className="stepper">
      {STAGES.map((s) => {
        const st = view.stages[s];
        const since = view.startedAt[s];
        const secs = st === "running" && since ? Math.max(0, Math.round((now - Date.parse(since)) / 1000)) : null;
        return (
          <button key={s} className={`step ${st}`} disabled={!latest[s]} title={st}
                  aria-label={`${stageLabel(s)}: ${st}`}
                  onClick={() => latest[s] && onSelect(latest[s]!.key)}>
            {ICON[st] && <span className="ic" aria-hidden="true">{ICON[st]}</span>}
            {stageLabel(s)}{secs != null ? ` ${secs}s` : ""}
          </button>);
      })}
    </div>
  );
}

import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { outputLabel, summaryPairs } from "../runStore";
import type { Output, RunSummary } from "../types";

/** The header's tool area; views render their buttons into it through <Tools>. */
export const ToolSlot = createContext<HTMLElement | null>(null);

/** A view's own buttons, shown in the viewer header (nothing until the header has mounted). */
export function Tools({ children }: { children: ReactNode }) {
  const el = useContext(ToolSlot);
  return el ? createPortal(children, el) : null;
}

export const FOLD_TOO_LARGE = "Too large to fold in this browser — this is the pre-built result";

export const FOLD_READ_ONLY = "This tab is read-only — Pleatwright is open in another tab.";
export const FOLD_BUSY = "Another fold is running — wait for it or cancel it.";

export interface RunActions {
  /** Provenance of a run folded here. */
  label: string | null;
  /** "Fold it here" on an example; `reason`, shown beside it, says why it is disabled. */
  fold: { disabled: boolean; reason: string | undefined } | null;
  /** "Download" on a finished browser run. */
  download: boolean;
}

/** Which run-level controls the header offers (site build only: server runs have no `kind`). */
export function runActions(run: RunSummary | null, readOnly: boolean, folding: boolean,
                           busy: boolean): RunActions {
  if (run?.kind === "gallery") {
    // Why "Fold it here" is off, most specific first: no reason while this tab is starting a fold.
    const reason = run.browser_foldable === false ? FOLD_TOO_LARGE
      : readOnly ? FOLD_READ_ONLY : busy ? FOLD_BUSY : undefined;
    return { label: null, download: false, fold: { disabled: !!reason || folding, reason } };
  }
  if (run?.kind === "browser") {
    return { label: "Folded in your browser", fold: null, download: run.status === "done" };
  }
  return { label: null, fold: null, download: false };
}

export function ViewerHeader({ output, following, onFollow, slotRef, actions, onFold, onDownload }: {
  output: Output | null; following: boolean; onFollow: () => void;
  slotRef: (el: HTMLDivElement | null) => void;
  actions: RunActions; onFold: () => void; onDownload: () => void;
}) {
  return (
    <div className="vhead">
      <span className="vh-info">
        <span className="vh-title">{output ? outputLabel(output) : "—"}</span>
        {output && summaryPairs(output).map(([k, v]) => (
          <span key={k} className="vh-pair"><span className="muted">{k}</span>{v}</span>))}
      </span>
      {actions.label && <span className="vh-label">{actions.label}</span>}
      {!following && <button className="vh-follow" onClick={onFollow}>● follow latest</button>}
      {(actions.fold || actions.download) && (
        <div className="vh-run">
          {actions.fold?.reason && <span className="vh-why" id="fold-why">{actions.fold.reason}</span>}
          {actions.fold && (
            <button onClick={onFold} disabled={actions.fold.disabled}
                    aria-describedby={actions.fold.reason ? "fold-why" : undefined}>Fold it here</button>)}
          {actions.download && <button onClick={onDownload}>Download</button>}
        </div>)}
      <div className="vh-tools" ref={slotRef} />
    </div>
  );
}

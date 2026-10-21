import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { outputLabel, summaryPairs } from "../runStore";
import type { Output } from "../types";

/** The header's tool area; views render their buttons into it through <Tools>. */
export const ToolSlot = createContext<HTMLElement | null>(null);

/** A view's own buttons, shown in the viewer header (nothing until the header has mounted). */
export function Tools({ children }: { children: ReactNode }) {
  const el = useContext(ToolSlot);
  return el ? createPortal(children, el) : null;
}

export function ViewerHeader({ output, following, onFollow, slotRef }: {
  output: Output | null; following: boolean; onFollow: () => void;
  slotRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <div className="vhead">
      <span className="vh-info">
        <span className="vh-title">{output ? outputLabel(output) : "—"}</span>
        {output && summaryPairs(output).map(([k, v]) => (
          <span key={k} className="vh-pair"><span className="muted">{k}</span>{v}</span>))}
      </span>
      {!following && <button className="vh-follow" onClick={onFollow}>● follow latest</button>}
      <div className="vh-tools" ref={slotRef} />
    </div>
  );
}

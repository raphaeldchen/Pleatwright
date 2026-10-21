import { useState } from "react";
import { fileUrl } from "../api";
import { isCard, sizeRatio } from "../runStore";
import type { Output } from "../types";
import { CPView } from "./CPView";
import { Tools } from "./ViewerHeader";

/** The packing stage while a layout is being chosen: both packings side by side, and the folded
 *  size each gives from the same sheet (a smaller grid has bigger cells, so a bigger model). */
export function LayoutCompare({ runId, output }: { runId: string; output: Output }) {
  const [hinges, setHinges] = useState(true);
  const [mv, setMv] = useState(true);
  const card = output.summary.layout_choice;
  if (!isCard(card)) return <div className="viewer-empty">could not read the layout choice</div>;
  const shown = card.options.flatMap((o) => {
    const f = output.files.find((x) => x.endsWith(`${o.id}_packing_cp.svg`));
    return f ? [{ o, f }] : [];
  });
  const nMin = Math.min(...card.options.map((o) => o.grid));
  return (
    <div className="compare">
      <Tools>
        <button className={hinges ? "on" : ""} aria-pressed={hinges} onClick={() => setHinges(!hinges)}>hinges</button>
        <button className={mv ? "on" : ""} aria-pressed={mv} onClick={() => setMv(!mv)}>M/V colours</button>
      </Tools>
      <div className="cmp-cps">
        {shown.map(({ o, f }) => (
          <figure key={o.id} className="cmp-pane">
            <div className="cmp-cp"><CPView src={fileUrl(runId, f)} controls={{ hinges, mv }} /></div>
            <figcaption>{o.label}: {o.grid} × {o.grid}</figcaption>
          </figure>))}
      </div>
      <div className="cmp-sizes">
        <div className="cmp-sizes-h">Folded size from the same sheet</div>
        <div className="cmp-squares">
          {card.options.map((o) => (
            <figure key={o.id} className="cmp-size">
              <div className="cmp-box">
                {/* the smallest grid fills 65% of the sheet's side; a larger grid, in proportion */}
                <div className="cmp-fill" style={{ width: `${65 / sizeRatio(nMin, o.grid)}%`,
                                                   height: `${65 / sizeRatio(nMin, o.grid)}%` }} />
              </div>
              <figcaption>grid {o.grid}</figcaption>
            </figure>))}
        </div>
      </div>
    </div>
  );
}

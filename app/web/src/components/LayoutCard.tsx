import type { LayoutCard as Card } from "../types";

/** "Choose Smaller grid, grid 32 (recommended)": what a screen reader says for an option button. */
export const optionName = (o: Card["options"][number]): string =>
  `Choose ${o.label}, grid ${o.grid}${o.recommended ? " (recommended)" : ""}`;

/** One card per review: a new run, or a new event in the same run, remounts the card. */
export const layoutCardKey = (runId: string, lastSeq: number): string => `${runId}:${lastSeq}`;

/** The packing stage's question: two layouts, each a button, the recommended one first. The VLM's
 *  explanation and the note come from a model and from the server: they are untrusted, so they are
 *  rendered only as React text nodes. */
export function LayoutCard({ card, explanation, note, canChoose = true, onChoose }: {
  card: Card; explanation?: string; note?: string | null; canChoose?: boolean; onChoose: (id: string) => void;
}) {
  const options = [...card.options].sort((a, b) => Number(b.recommended) - Number(a.recommended));
  return (
    <div className="layout-card" role="group" aria-label={card.question}>
      <div className="lc-q">{card.question}</div>
      {note && <div className="lc-note">{note}</div>}
      {explanation && <div className="lc-why">{explanation}</div>}
      {options.map((o) => (
        <button key={o.id} className={`lc-opt${o.recommended ? " rec" : ""}`} disabled={!canChoose}
                aria-label={optionName(o)}
                onClick={() => onChoose(o.id)}>
          <span className="lc-title">{o.label} <span className="muted">· grid {o.grid}</span>
            {o.recommended && <span className="lc-badge">(Recommended)</span>}</span>
          <ul>
            {o.pros.map((t, i) => <li key={`p${i}`}><b>Pro:</b> {t}</li>)}
            {o.cons.map((t, i) => <li key={`c${i}`}><b>Con:</b> {t}</li>)}
          </ul>
        </button>))}
    </div>
  );
}

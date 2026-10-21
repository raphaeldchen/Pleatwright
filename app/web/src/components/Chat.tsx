import { useEffect, useRef, useState } from "react";
import type { Command } from "../api";
import { nextModel } from "../model";
import { reviewCopy } from "../runStore";
import type { ModelOption, RunView } from "../types";
import { LayoutCard, layoutCardKey } from "./LayoutCard";
import { StageBlock } from "./StageBlock";

/** Which VLM authors the next tree (first draft, revision or retry); one click cycles. */
function ModelPill({ models, model, onModel }: {
  models: ModelOption[]; model: string; onModel: (k: string) => void;
}) {
  if (models.length < 2) return null;
  const label = (k: string) => models.find((m) => m.key === k)?.label ?? k;
  const next = nextModel(models, model);
  return (
    <button className="model-pill" onClick={() => onModel(next)} title="Model for the next tree or mesh feedback"
            aria-label={`Model: ${label(model)}. Switch to ${label(next)}.`}>{label(model)}</button>
  );
}

export function Chat({ view, send, onSelect, onNewRun, canStart, onStart, models, model, onModel }: {
  view: RunView | null; send: (c: Command) => void; onSelect: (k: string) => void;
  onNewRun: () => void; canStart: boolean; onStart: (prompt: string) => void;
  models: ModelOption[]; model: string; onModel: (k: string) => void;
}) {
  const pill = <ModelPill models={models} model={model} onModel={onModel} />;
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { end.current?.scrollIntoView({ block: "end" }); }, [view?.lastSeq]);

  if (!view) {
    const go = () => { if (text.trim()) { onStart(text.trim()); setText(""); } };
    return (
      <div className="chat">
        <div className="msgs"><div className="empty-run"><h3>What should we fold?</h3>
          <p>Describe an animal or object, e.g. “a dog”.</p></div></div>
        <div className="composer">
          <span className="prompt" aria-hidden="true">&gt;</span>
          <textarea rows={2} value={text} disabled={!canStart} placeholder="a dog"
                    aria-label="What should we fold?"
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); go(); } }} />
          {pill}
          <button className="btn" disabled={!canStart || !text.trim()} onClick={go}>Fold</button>
        </div>
      </div>
    );
  }
  const ended = !!view.finished;
  const reviewing = !!view.review && !view.running;
  const copy = reviewCopy(view.review?.stage ?? "tree");
  const choosing = reviewing && view.review!.stage === "packing" && !!view.review!.card;   // the layout card, not a tree to approve
  const submit = () => {
    if (!text.trim() || !reviewing || choosing) return;
    send({ type: "message", text: text.trim(), model });
    setText("");
  };
  return (
    <div className="chat">
      <div className="msgs">
        {view.chat.map((c) => {
          if (c.kind === "user") return <div key={c.seq} className="user">{c.text}</div>;
          if (c.kind === "assistant") return <div key={c.seq} className="assistant">{c.text}</div>;
          if (c.kind === "failed") return (
            <div key={c.seq} className="failed">
              <b>{c.stage} {c.reason === "error" ? "failed" : c.reason}</b>: {c.error}
              {c.retry && view.failure && c.seq === Math.max(...view.chat.filter((x) => x.kind === "failed").map((x) => x.seq)) &&
                <div className="actions"><button className="btn ghost" onClick={() => send({ type: "retry", model })}>
                  {c.retry === "review" ? "Back to the tree" : c.retry === "review_mesh" ? "Back to the mesh"
                    : c.retry === "layout" ? "Back to the layouts" : "Retry"}</button></div>}
            </div>);
          const o = view.outputs.find((x) => x.key === c.key)!;
          return <StageBlock key={c.seq} runId={view.id} o={o} selected={view.selected === o.key}
                             onClick={() => onSelect(o.key)} />;
        })}
        {choosing &&
          <LayoutCard key={layoutCardKey(view.id, view.lastSeq)} card={view.review!.card!} canChoose={view.review!.canApprove} explanation={view.review!.explanation} note={view.review!.note}
                      onChoose={(choice) => send({ type: "approve", choice, model })} />}
        {reviewing && !choosing && (
          <div className="review">
            <button className="btn" disabled={!view.review!.canApprove}
                    onClick={() => send({ type: "approve", model })}>{copy.approve}</button>
            <span className="muted">{copy.hint}</span>
          </div>)}
        <div ref={end} />
      </div>
      {ended ? (
        <div className="composer"><button className="btn" onClick={onNewRun}>[+] New run</button></div>
      ) : (
        <div className="composer">
          <span className="prompt" aria-hidden="true">&gt;</span>
          <textarea rows={2} value={text} disabled={!reviewing || choosing} aria-label={copy.aria}
                    placeholder={reviewing ? copy.placeholder : view.running ? "Working…" : ""}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }} />
          {!view.running && pill}
          {view.running
            ? <button className="btn ghost" onClick={() => send({ type: "cancel" })}>Cancel</button>
            : <button className="btn" disabled={!reviewing || choosing || !text.trim()} onClick={submit}>Send</button>}
        </div>
      )}
    </div>
  );
}

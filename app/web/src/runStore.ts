import { STAGES, stageLabel, type Action, type LayoutCard, type Output, type PwEvent, type RunView, type StageId,
         type StageStatus } from "./types";

export function emptyView(id: string): RunView {
  return {
    id, prompt: "", lastSeq: -1,
    stages: Object.fromEntries(STAGES.map((s) => [s, "todo"])) as Record<StageId, StageStatus>,
    startedAt: {}, outputs: [], chat: [], review: null, finished: null, failure: null,
    running: false, selected: null, followLatest: true,
  };
}

const ROUNDED: StageId[] = ["image", "mesh", "tree"];
const keyOf = (e: PwEvent) =>
  ROUNDED.includes(e.stage!) && typeof e.round === "number" ? `${e.stage}:${e.round}` : String(e.stage);

export const isCard = (x: unknown): x is LayoutCard =>
  !!x && typeof x === "object" && Array.isArray((x as LayoutCard).options);

function applyEvent(v: RunView, e: PwEvent): RunView {
  if (e.seq <= v.lastSeq) return v;                     // replay overlap: already applied
  const n: RunView = { ...v, lastSeq: e.seq, stages: { ...v.stages },
                       startedAt: { ...v.startedAt }, outputs: [...v.outputs], chat: [...v.chat] };
  switch (e.type) {
    case "run_created":
      n.prompt = String(e.prompt ?? "");
      break;
    case "user_message":
      n.chat.push({ kind: "user", text: String(e.text ?? ""), seq: e.seq });
      n.review = null;
      n.failure = null;
      break;
    case "assistant_message":
      n.chat.push({ kind: "assistant", text: String(e.text ?? ""), seq: e.seq });
      break;
    case "stage_started":
      n.stages[e.stage!] = "running";
      n.startedAt[e.stage!] = e.t;
      n.running = true;
      n.failure = null;
      break;
    case "stage_output": {
      const o: Output = { key: keyOf(e), stage: e.stage!, files: (e.files as string[]) ?? [],
                          summary: (e.summary as Record<string, unknown>) ?? {}, seq: e.seq,
                          ...(typeof e.round === "number" ? { round: e.round } : {}) };
      const i = n.outputs.findIndex((x) => x.key === o.key);
      if (i >= 0) n.outputs[i] = o;                     // approval updates the round in place
      else {
        n.outputs.push(o);
        n.chat.push({ kind: "output", key: o.key, seq: e.seq });
      }
      n.stages[e.stage!] = o.summary.skipped ? "skipped" : "done";
      if (n.followLatest) n.selected = o.key;
      break;
    }
    case "awaiting_review": {
      const stage = (e.stage as StageId | undefined) ?? "tree";
      n.stages[stage] = "waiting";
      n.review = { round: Number(e.round), canApprove: Boolean(e.can_approve), stage,
                   ...(isCard(e.card) ? { card: e.card, explanation: String(e.explanation ?? ""),
                                          note: typeof e.note === "string" ? e.note : null } : {}) };
      n.failure = null;                    // a failed rewrite returns here; its Retry no longer applies
      n.running = false;
      break;
    }
    case "stage_failed":
      if (e.reason === "exhausted") {
        // A run stopped at the 3-revision cap (removed 2026-10-11) is back in review on its
        // last tree; the cap's note was already shown as an assistant message.
        const trees = n.outputs.filter((o) => o.stage === "tree");
        n.stages.tree = "waiting";
        n.review = { round: trees.length ? (trees[trees.length - 1].round ?? 0) : 0, canApprove: true, stage: "tree" };
        n.failure = null;
        n.running = false;
        break;
      }
      n.stages[e.stage!] = "failed";
      n.failure = { stage: e.stage!, reason: String(e.reason), retry: (e.retry as string) ?? null };
      n.chat.push({ kind: "failed", stage: e.stage!, error: String(e.error ?? ""),
                    reason: String(e.reason), retry: (e.retry as string) ?? null, seq: e.seq });
      n.review = null;
      n.running = false;
      break;
    case "run_finished":
      for (const s of STAGES) if (n.stages[s] !== "skipped") n.stages[s] = "done";
      n.finished = { ...e };
      n.running = false;
      break;
  }
  return n;
}

export function reduce(v: RunView, a: Action): RunView {
  if (a.type === "event") return applyEvent(v, a.event);
  if (a.type === "select") return { ...v, selected: a.key, followLatest: false };
  const last = v.outputs[v.outputs.length - 1];
  return { ...v, followLatest: true, selected: last ? last.key : null };
}

export function selectedOutput(v: RunView): Output | null {
  return v.outputs.find((o) => o.key === v.selected) ?? null;
}

export function latestByStage(v: RunView): Partial<Record<StageId, Output>> {
  const m: Partial<Record<StageId, Output>> = {};
  for (const o of v.outputs) m[o.stage] = o;
  return m;
}

const ff = (x: unknown) => (Array.isArray(x) ? `${x[0]}/${x[1]} vertices flat-foldable` : "");

const rec = (x: unknown): Record<string, unknown> | null =>
  x && typeof x === "object" && !Array.isArray(x) ? (x as Record<string, unknown>) : null;

/** The folded size of grid A against grid B from the same sheet: a model packed on a
 *  smaller grid has bigger cells, so 32 against 50 is 50/32 = 1.5625 times larger. */
export const sizeRatio = (nA: number, nB: number): number => nB / nA;

/** The packing stage's chat line. The pair of layouts awaiting a choice has no grid yet; a
 *  fold's packing adds the layout chosen and the sheet's efficiency (absent in older runs). */
function packingLine(s: Record<string, unknown>): string {
  const card = rec(s.layout_choice);
  if (card) return `${(card.options as unknown[] | undefined)?.length ?? 2} layouts to choose from`;
  const lay = rec(s.layout), eff = rec(s.efficiency);
  if (!lay && !eff) return `grid ${s.grid} · ${s.rung} · ${s.tried} tried`;
  const slack = typeof eff?.slack_fraction === "number" ? `slack ${Math.round(eff.slack_fraction * 100)}%` : "";
  const layers = typeof eff?.mean_layers === "number" ? `~${eff.mean_layers.toFixed(1)} layers` : "";
  return [`grid ${s.grid ?? eff?.grid}`, lay?.chosen ? `${lay.chosen}${lay.reason ? ` (${lay.reason})` : ""}` : "",
          slack, layers].filter(Boolean).join(" · ");
}

export function summaryLine(o: Output): string {
  const s = o.summary;
  switch (o.stage) {
    case "image": return s.skipped ? String(s.note)
      : [s.provider, s.image_model].filter(Boolean).join(" · ");
    case "mesh": return [s.provider, s.faces != null ? `${Number(s.faces).toLocaleString()} faces` : "",
      s.served === "best_rated" ? `best-rated · ${s.approvals}/${s.votes} approved`
        : s.description ? `“${s.description}”` : "",
      s.approved ? "approved" : ""].filter(Boolean).join(" · ");
    case "tree": return s.approved ? "approved"
      : `${s.flaps} flaps, ${s.pairs} pairs${s.model ? ` · ${s.model}` : ""}`;
    case "packing": return packingLine(s);
    case "solve": return [ff(s.flat_foldable), s.global_verdict ? `global: ${s.global_verdict}` : ""]
      .filter(Boolean).join(" · ");
    case "shape": return ff(s.flat_foldable);
    case "model": return "folded model";
  }
}

export function outputTitle(o: Output): string {
  const names: Record<StageId, string> = { image: "Concept image", mesh: "Mesh", tree: "Tree",
    packing: "Packing", solve: "Solved CP", shape: "Shaped CP", model: "Folded model" };
  return o.round != null ? `${names[o.stage]} · round ${o.round + 1}` : names[o.stage];
}

const frac = (x: unknown) => (Array.isArray(x) && x.length === 2 ? `${x[0]}/${x[1]}` : null);

/** A stage summary as label/value pairs for the viewer header. Missing keys are skipped: old runs'
 *  events are never rewritten, so a summary may predate a key. */
export function summaryPairs(o: Output): [string, string][] {
  const s = o.summary;
  const out: [string, string][] = [];
  const add = (k: string, v: unknown) => { if (v != null && v !== "") out.push([k, String(v)]); };
  switch (o.stage) {
    case "image":
      if (s.skipped) add("note", s.note);
      else { add("provider", s.provider); add("image model", s.image_model); }
      break;
    case "mesh":
      add("provider", s.provider);
      add("faces", s.faces != null ? Number(s.faces).toLocaleString() : null);
      if (s.served === "best_rated") add("rating", `${s.approvals}/${s.votes}`);
      add("description", s.description);
      add("seed", s.seed);
      if (s.approved) add("status", "approved");
      break;
    case "tree":
      if (s.approved) add("status", "approved");
      else { add("flaps", s.flaps); add("pairs", s.pairs); add("model", s.model); }
      break;
    case "packing": {
      const opts = rec(s.layout_choice)?.options;
      if (Array.isArray(opts)) add("grids", opts.map((x) => rec(x)?.grid).join(" or "));
      add("grid", s.grid); add("rung", s.rung); add("tried", s.tried);
      break;
    }
    case "solve": add("flat-foldable", frac(s.flat_foldable)); add("global", s.global_verdict); break;
    case "shape": add("flat-foldable", frac(s.flat_foldable)); break;
    case "model":
      add("folder", typeof s.folder === "string" ? s.folder.split("/").filter(Boolean).pop() : null);
      break;
  }
  return out;
}

/** "03 TREE · R2" for a round, else the stage label. */
export function outputLabel(o: Output): string {
  return stageLabel(o.stage) + (o.round != null ? ` · R${o.round + 1}` : "");
}

/** The review controls' words for the stage under review. */
export function reviewCopy(stage: StageId): { approve: string; hint: string; placeholder: string; aria: string } {
  if (stage === "packing")
    return { approve: "Choose a layout", hint: "pick one of the two layouts above",
             placeholder: "Choose a layout above…", aria: "Message (choose a layout first)" };
  const noun = stage === "mesh" ? "mesh" : "tree";
  return { approve: stage === "mesh" ? "Approve mesh" : "Approve", hint: `or type what is wrong with the ${noun} ↓`,
           placeholder: `Describe what is wrong with the ${noun}…`, aria: `Message about the ${noun}` };
}

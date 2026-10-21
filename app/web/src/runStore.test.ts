import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { emptyView, isCard, latestByStage, outputLabel, reduce, reviewCopy, selectedOutput, sizeRatio, summaryLine, summaryPairs } from "./runStore";
import type { Output, PwEvent, RunView } from "./types";

const events: PwEvent[] = readFileSync(
  new URL("./__fixtures__/bird_run.events.jsonl", import.meta.url), "utf8")
  .trim().split("\n").map((l) => JSON.parse(l));

const replay = (n = events.length, v: RunView = emptyView("r")) =>
  events.slice(0, n).reduce((acc, e) => reduce(acc, { type: "event", event: e }), v);

const upTo = (pred: (e: PwEvent) => boolean, nth = 1) => {
  let k = 0;
  return events.findIndex((e) => pred(e) && ++k === nth) + 1;
};

describe("runStore over a recorded fake-provider run (bird_1)", () => {
  it("pauses at tree review with the first round selected", () => {
    const v = replay(upTo((e) => e.type === "awaiting_review" && e.stage === "tree"));
    expect(v.stages.image).toBe("skipped");          // fake provider draws no concept
    expect(v.stages.mesh).toBe("done");
    expect(v.stages.tree).toBe("waiting");
    expect(v.stages.packing).toBe("todo");
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "tree" });
    expect(selectedOutput(v)?.key).toBe("tree:0");
    expect(v.prompt).toBe("a bird");
  });

  it("a revision adds round 1 and follows it", () => {
    const v = replay(upTo((e) => e.type === "awaiting_review" && e.stage === "tree", 2));
    expect(v.outputs.filter((o) => o.stage === "tree").map((o) => o.round)).toEqual([0, 1]);
    expect(selectedOutput(v)?.key).toBe("tree:1");
    expect(v.chat.filter((c) => c.kind === "user").length).toBe(3);   // prompt, mesh approval, revision
  });

  it("approval updates round 1 in place and the fold fills every stage", () => {
    const v = replay();
    expect(v.outputs.filter((o) => o.stage === "tree").length).toBe(2);
    expect(v.stages).toEqual({ image: "skipped", mesh: "done", tree: "done", packing: "done",
                               solve: "done", shape: "done", model: "done" });
    expect(v.finished?.grid).toBe(40);
    expect(selectedOutput(v)?.stage).toBe("model");
    expect(latestByStage(v).packing?.files[0]).toMatch(/packing_cp\.svg$/);
    expect(v.running).toBe(false);
  });

  it("selecting an older output pins it until follow", () => {
    const mid = upTo((e) => e.type === "stage_output" && e.stage === "packing");
    let v = replay(mid);
    v = reduce(v, { type: "select", key: "mesh:0" });
    v = events.slice(mid).reduce((a, e) => reduce(a, { type: "event", event: e }), v);
    expect(selectedOutput(v)?.key).toBe("mesh:0");
    expect(v.followLatest).toBe(false);
    v = reduce(v, { type: "follow" });
    expect(selectedOutput(v)?.stage).toBe("model");
  });

  it("is idempotent for replayed events (reconnect overlap)", () => {
    const once = replay();
    const twice = events.reduce((a, e) => reduce(a, { type: "event", event: e }), once);
    expect(twice).toEqual(once);
  });

  it("a failure marks the stage and records the retry", () => {
    const n = upTo((e) => e.type === "stage_started" && e.stage === "packing");
    const v = reduce(replay(n), { type: "event", event: {
      seq: 999, t: "", type: "stage_failed", stage: "packing", error: "cancelled",
      reason: "cancelled", retry: "fold" } });
    expect(v.stages.packing).toBe("failed");
    expect(v.failure).toEqual({ stage: "packing", reason: "cancelled", retry: "fold" });
    expect(v.running).toBe(false);
  });

  it("a run stopped at the old revision cap (before 2026-10-11) is back in review", () => {
    const n = upTo((e) => e.type === "awaiting_review" && e.stage === "tree");
    let v = replay(n);
    for (const event of [
      { seq: 997, t: "", type: "user_message", text: "fourth" },
      { seq: 998, t: "", type: "stage_started", stage: "tree" },
      { seq: 999, t: "", type: "stage_failed", stage: "tree", error: "3 revisions were used",
        reason: "exhausted", retry: null }] as PwEvent[]) v = reduce(v, { type: "event", event });
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "tree" });
    expect(v.failure).toBeNull();
    expect(v.stages.tree).toBe("waiting");
    expect(v.running).toBe(false);
    expect(v.chat.some((c) => c.kind === "failed")).toBe(false);
  });

  it("summary lines", () => {
    const v = replay();
    const tree0 = v.outputs.find((o) => o.key === "tree:0")!;
    expect(summaryLine(tree0)).toMatch(/^\d+ flaps, \d+ pairs · haiku$/);
    expect(summaryLine(latestByStage(v).packing!)).toMatch(/^grid 40/);
  });

  it("approval: tree goes running (review cleared) then done", () => {
    const approve = events.findLastIndex((e) => e.type === "user_message" && e.text === "Approve");   // the tree approval; the first one approved the mesh
    expect(approve).toBeGreaterThan(0);
    const started = events.findIndex((e, i) => i > approve && e.type === "stage_started" && e.stage === "tree");
    const output = events.findIndex((e, i) => i > started && e.type === "stage_output" && e.stage === "tree");
    const before = replay(approve + 1);
    expect(before.stages.tree).toBe("waiting");
    expect(before.review).toBeNull();                 // the user message clears the review
    const running = replay(started + 1);
    expect(running.stages.tree).toBe("running");
    expect(running.review).toBeNull();
    expect(running.running).toBe(true);
    const done = replay(output + 1);
    expect(done.stages.tree).toBe("done");
    expect(done.outputs.find((o) => o.key === "tree:1")?.summary).toEqual({ approved: true });
  });
});

describe("summaryPairs / outputLabel over the recorded run", () => {
  const v = replay();
  const by = (key: string) => v.outputs.find((o) => o.key === key)!;
  const mk = (stage: Output["stage"], summary: Record<string, unknown>): Output =>
    ({ key: stage, stage, files: [], summary, seq: 0 });

  it("gives each recorded stage its pairs", () => {
    expect(summaryPairs(by("image:0"))).toEqual([["note", "no concept image (fake)"]]);
    expect(summaryPairs(by("mesh:0"))).toEqual([["provider", "fake"], ["faces", (608).toLocaleString()], ["status", "approved"]]);
    expect(summaryPairs(by("tree:0"))).toEqual([["flaps", "6"], ["pairs", "2"], ["model", "haiku"]]);
    expect(summaryPairs(by("tree:1"))).toEqual([["status", "approved"]]);
    expect(summaryPairs(by("packing"))).toEqual([["grid", "40"], ["rung", "symmetric"], ["tried", "1"]]);
    expect(summaryPairs(by("solve"))).toEqual([["flat-foldable", "187/187"], ["global", "CERTIFIED"]]);
    expect(summaryPairs(by("shape"))).toEqual([["flat-foldable", "792/792"]]);
    expect(summaryPairs(by("model"))).toEqual([]);
  });

  it("never shows undefined or null", () => {
    for (const o of v.outputs) for (const [, val] of summaryPairs(o)) expect(val).not.toMatch(/undefined|null/);
  });

  it("covers a provider image, a model folder, and skips missing or malformed keys", () => {
    expect(summaryPairs(mk("image", { provider: "hf2" }))).toEqual([["provider", "hf2"]]);
    expect(summaryPairs(mk("model", { folder: "Dog_54" }))).toEqual([["folder", "Dog_54"]]);
    expect(summaryPairs(mk("model", { folder: "runs/x/Dog_54/" }))).toEqual([["folder", "Dog_54"]]);
    expect(summaryPairs(mk("packing", { grid: 54 }))).toEqual([["grid", "54"]]);
    expect(summaryPairs(mk("solve", { flat_foldable: "weird" }))).toEqual([]);
    expect(summaryPairs(mk("tree", {}))).toEqual([]);
  });

  it("names the model that wrote a tree round", () => {
    const t = mk("tree", { flaps: 6, pairs: 2, model: "sonnet" });
    expect(summaryPairs(t)).toEqual([["flaps", "6"], ["pairs", "2"], ["model", "sonnet"]]);
    expect(summaryLine(t)).toBe("6 flaps, 2 pairs · sonnet");
    expect(summaryLine(mk("tree", { flaps: 6, pairs: 2 }))).toBe("6 flaps, 2 pairs");   // runs before the switch
  });

  it("labels outputs with stage number and tree round", () => {
    expect(outputLabel(by("tree:0"))).toBe("03 TREE · R1");
    expect(outputLabel(by("tree:1"))).toBe("03 TREE · R2");
    expect(outputLabel(by("packing"))).toBe("04 PACK");
    expect(outputLabel(by("model"))).toBe("07 MODEL");
  });
});

describe("mesh review", () => {
  it("the recorded run reviews its mesh first, keyed by round", () => {
    const v = replay(upTo((e) => e.type === "awaiting_review"));
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "mesh" });
    expect(v.stages.mesh).toBe("waiting");
    expect(v.outputs.map((o) => o.key)).toEqual(["image:0", "mesh:0"]);
    expect(outputLabel(v.outputs[1])).toBe("02 MESH · R1");
  });
  it("an old run's image and mesh outputs keep their plain keys", () => {
    const v = reduce(emptyView("old"), { type: "event", event: {
      seq: 1, t: "", type: "stage_output", stage: "mesh", files: ["author/mesh.glb"], summary: {} } });
    expect(v.outputs[0].key).toBe("mesh");
  });
  it("an old awaiting_review without a stage is a tree review", () => {
    const v = reduce(emptyView("old"), { type: "event", event: {
      seq: 1, t: "", type: "awaiting_review", round: 0, can_approve: true } });
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "tree" });
  });
  it("a mesh review returned after a failed rewrite clears the failure", () => {
    const ev = (e: Partial<PwEvent>): PwEvent => ({ seq: 1, t: "", ...e } as PwEvent);
    let v = reduce(emptyView("r"), { type: "event", event: ev({
      type: "stage_failed", stage: "mesh", error: "could not rewrite", reason: "error", retry: "review_mesh" }) });
    expect(v.failure).toEqual({ stage: "mesh", reason: "error", retry: "review_mesh" });
    v = reduce(v, { type: "event", event: ev({ seq: 2, type: "awaiting_review", stage: "mesh", round: 0, can_approve: true }) });
    expect(v.failure).toBeNull();
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "mesh" });
  });
  it("labels the review by stage", () => {
    expect(reviewCopy("mesh")).toEqual({ approve: "Approve mesh", hint: "or type what is wrong with the mesh ↓",
      placeholder: "Describe what is wrong with the mesh…", aria: "Message about the mesh" });
    expect(reviewCopy("tree").approve).toBe("Approve");
  });
  it("a redrawn mesh shows its description; a served one its rating", () => {
    const o = (summary: Record<string, unknown>): Output =>
      ({ key: "mesh:1", stage: "mesh", round: 1, files: [], summary, seq: 0 });
    expect(summaryLine(o({ provider: "hf2", faces: 1000, description: "bull moose, long legs" })))
      .toBe("hf2 · 1,000 faces · “bull moose, long legs”");
    expect(summaryLine(o({ provider: "hf2", served: "best_rated", approvals: 3, votes: 4 })))
      .toBe("hf2 · best-rated · 3/4 approved");
    expect(summaryLine(o({ provider: "hf2", approved: true }))).toBe("hf2 · approved");
  });
  it("a concept image names the model that drew it (spec 2026-10-19)", () => {
    const img = (summary: Record<string, unknown>): Output =>
      ({ key: "image:0", stage: "image", round: 0, files: ["author/concept_r0.jpg"], summary, seq: 0 });
    expect(summaryLine(img({ provider: "hf2", image_model: "gemini-nano-banana-2.1" })))
      .toBe("hf2 · gemini-nano-banana-2.1");
    expect(summaryLine(img({ provider: "hf2" }))).toBe("hf2");
    expect(summaryPairs(img({ provider: "hf2", image_model: "m" })))
      .toEqual([["provider", "hf2"], ["image model", "m"]]);
  });
});

describe("layout card over a recorded dolphin run (paused at packing)", () => {
  const dolphin: PwEvent[] = readFileSync(
    new URL("./__fixtures__/dolphin_layout.events.jsonl", import.meta.url), "utf8")
    .trim().split("\n").map((l) => JSON.parse(l));
  const play = (evs: PwEvent[], v: RunView = emptyView("d")) =>
    evs.reduce((acc, e) => reduce(acc, { type: "event", event: e }), v);

  it("waits at packing with the card, its explanation and no note", () => {
    const v = play(dolphin);
    expect(v.review?.stage).toBe("packing");
    expect(v.review?.canApprove).toBe(true);
    expect(v.review?.card?.options.map((o) => o.id)).toEqual(["smaller", "symmetric"]);
    expect(v.review?.card?.options[0]).toMatchObject({ grid: 32, recommended: true });
    expect(v.review?.explanation).toBe("e");
    expect(v.review?.note).toBeNull();
    expect(v.stages.packing).toBe("waiting");
    expect(v.running).toBe(false);
  });

  it("the card stage output carries both packings and the viewer shows it", () => {
    const v = play(dolphin);
    const out = latestByStage(v).packing!;
    expect(out.files).toEqual(["layout/smaller_packing_cp.svg", "layout/symmetric_packing_cp.svg"]);
    expect(selectedOutput(v)?.key).toBe("packing");
  });

  it("replaying from scratch gives an equal view (reload)", () => {
    expect(play(dolphin, play(dolphin))).toEqual(play(dolphin));
  });

  it("choosing clears the review", () => {
    const v = play([{ seq: 100, t: "", type: "user_message", text: "Smaller grid" } as PwEvent], play(dolphin));
    expect(v.review).toBeNull();
  });

  it("a review without a card carries none", () => {
    const v = play(dolphin.filter((e) => e.type !== "awaiting_review" || e.stage !== "packing"));
    expect(v.review).toBeNull();
    const t = play([{ seq: 1, t: "", type: "awaiting_review", stage: "tree", round: 0, can_approve: true } as PwEvent]);
    expect(t.review).toEqual({ round: 0, canApprove: true, stage: "tree" });
    expect(t.review).not.toHaveProperty("card");
  });

  it("the packing review's words", () => {
    expect(reviewCopy("packing").approve).toBe("Choose a layout");
  });

  it("sizeRatio is the folded size of grid A against grid B", () => {
    expect(sizeRatio(32, 50)).toBe(1.5625);
    expect(sizeRatio(50, 50)).toBe(1);
  });

  it("the card's packing output and a fold's packing output have their own lines", () => {
    const card = latestByStage(play(dolphin)).packing!;
    expect(summaryLine(card)).toBe("2 layouts to choose from");
    expect(summaryPairs(card)).toEqual([["grids", "32 or 50"]]);
    const fold = (summary: Record<string, unknown>): Output => ({ key: "packing", stage: "packing", files: [], summary, seq: 0 });
    expect(summaryLine(fold({ grid: 32, rung: "smaller", tried: 3,
      layout: { chosen: "smaller", reason: "user", n_symmetric: 50, n_smaller: 32, gain: 1.5625, threshold: 1.1 },
      efficiency: { grid: 32, slack_fraction: 0.1623, mean_layers: 16.64 } })))
      .toBe("grid 32 · smaller (user) · slack 16% · ~16.6 layers");
    expect(summaryLine(fold({ grid: 54, layout: { chosen: "doubled", reason: "only_option" } })))
      .toBe("grid 54 · doubled (only_option)");
    expect(summaryLine(fold({ grid: 40, rung: "symmetric", tried: 1 }))).toBe("grid 40 · symmetric · 1 tried");   // before layouts
  });

  it("isCard accepts the recorded card and rejects malformed ones", () => {
    expect(isCard(play(dolphin).review?.card)).toBe(true);
    for (const bad of [null, undefined, "x", {}, { options: "no" }]) expect(isCard(bad)).toBe(false);
  });
});

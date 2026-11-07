import { describe, expect, it, vi } from "vitest";
import type { RunSummary } from "../types";
import { dayLabel, groupRuns, removeRun } from "./RunsSidebar";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { FOLD_BUSY, FOLD_READ_ONLY, FOLD_TOO_LARGE, runActions, ViewerHeader, type RunActions } from "./ViewerHeader";

describe("dayLabel (local time)", () => {
  const now = new Date(2026, 9, 8, 15, 0);
  it("names today and yesterday", () => {
    expect(dayLabel(new Date(2026, 9, 8, 0, 5).toISOString(), now)).toBe("— TODAY");
    expect(dayLabel(new Date(2026, 9, 7, 23, 59).toISOString(), now)).toBe("— YESTERDAY");
  });
  it("gives older runs an ISO date", () => {
    expect(dayLabel(new Date(2026, 9, 6, 12, 0).toISOString(), now)).toBe("— 2026-10-06");
    expect(dayLabel(new Date(2025, 0, 2, 12, 0).toISOString(), now)).toBe("— 2025-01-02");
  });
});

describe("removeRun", () => {
  const run: RunSummary = { id: "2026-10-11-0900-moose", prompt: "a moose", subject: "moose",
                            created: "2026-10-11T09:00:00", status: "done" };
  const deps = (ok: boolean, del = vi.fn().mockResolvedValue(undefined)) => ({
    confirm: vi.fn().mockReturnValue(ok), del, leave: vi.fn(), refresh: vi.fn(), flash: vi.fn() });

  it("asks first, naming the run; cancelling deletes nothing", async () => {
    const d = deps(false);
    await removeRun(run, null, d);
    expect(d.confirm.mock.calls[0][0]).toContain("moose");
    expect(d.del).not.toHaveBeenCalled();
    expect(d.refresh).not.toHaveBeenCalled();
  });
  it("deletes and refreshes; leaves the run only if it is the one open", async () => {
    const open = deps(true);
    await removeRun(run, run.id, open);
    expect(open.del).toHaveBeenCalledWith(run.id);
    expect(open.leave).toHaveBeenCalled();
    expect(open.refresh).toHaveBeenCalled();
    const other = deps(true);
    await removeRun(run, "another-run", other);
    expect(other.del).toHaveBeenCalledWith(run.id);
    expect(other.leave).not.toHaveBeenCalled();
  });
  it("shows a refusal and stays on the run", async () => {
    const d = deps(true, vi.fn().mockRejectedValue(new Error("this run is still running; cancel it first")));
    await removeRun(run, run.id, d);
    expect(d.flash).toHaveBeenCalledWith("this run is still running; cancel it first");
    expect(d.leave).not.toHaveBeenCalled();
  });
});

describe("gallery grouping", () => {
  const row = (id: string, extra: Partial<RunSummary> = {}): RunSummary => ({
    id, prompt: id, subject: id, created: "2026-10-11T09:00:00", status: "done", ...extra });

  it("gallery_rows_render_above_browser_runs_without_delete", () => {
    // A browser run is listed after the examples, but the sidebar groups by kind either way.
    const runs = [row("mine", { kind: "browser" }), row("gallery-dog_0", { kind: "gallery" }),
                  row("gallery-cat_1", { kind: "gallery" })];
    const groups = groupRuns(runs);
    expect(groups.map((g) => g.heading)).toEqual(["Examples", "Your runs"]);
    expect(groups[0].runs.map((r) => r.id)).toEqual(["gallery-dog_0", "gallery-cat_1"]);
    expect(groups[0].deletable).toBe(false);
    expect(groups[1].runs.map((r) => r.id)).toEqual(["mine"]);
    expect(groups[1].deletable).toBe(true);
  });
  it("leaves out an empty group", () => {
    expect(groupRuns([row("gallery-dog_0", { kind: "gallery" })]).map((g) => g.heading)).toEqual(["Examples"]);
    expect(groupRuns([row("mine", { kind: "browser" })]).map((g) => g.heading)).toEqual(["Your runs"]);
  });
  it("renders the server build's runs as one ungrouped, deletable list", () => {
    const runs = [row("a"), row("b")];
    expect(groupRuns(runs)).toEqual([{ heading: null, runs, deletable: true }]);
    expect(groupRuns([])).toEqual([{ heading: null, runs: [], deletable: true }]);
  });
});

describe("viewer header run actions", () => {
  const run = (extra: Partial<RunSummary>): RunSummary => ({
    id: "gallery-dog_0", prompt: "a dog", subject: "dog", created: "2026-10-11T09:00:00",
    status: "done", ...extra });

  it("offers Fold it here on an example, enabled when it can be folded", () => {
    const a = runActions(run({ kind: "gallery", browser_foldable: true }), false, false, false);
    expect(a.fold).toEqual({ disabled: false, reason: undefined });
    expect(a.label).toBeNull();
    expect(a.download).toBe(false);
  });
  it("fold_here_disabled_when_not_browser_foldable", () => {
    const big = runActions(run({ kind: "gallery", browser_foldable: false }), false, false, false);
    expect(big.fold).toEqual({ disabled: true, reason: FOLD_TOO_LARGE });
    expect(FOLD_TOO_LARGE).toBe("Too large to fold in this browser — this is the pre-built result");
  });
  it("gives a read-only tab, and a busy engine, their own reasons", () => {
    const small = run({ kind: "gallery", browser_foldable: true });
    expect(FOLD_READ_ONLY).toBe("This tab is read-only — Pleatwright is open in another tab.");
    expect(FOLD_BUSY).toBe("Another fold is running — wait for it or cancel it.");
    expect(runActions(small, true, false, false).fold).toEqual({ disabled: true, reason: FOLD_READ_ONLY });
    expect(runActions(small, false, false, true).fold).toEqual({ disabled: true, reason: FOLD_BUSY });
  });
  it("explains the first reason that applies: too large, then read-only, then busy", () => {
    const big = run({ kind: "gallery", browser_foldable: false });
    const small = run({ kind: "gallery", browser_foldable: true });
    expect(runActions(big, true, false, true).fold?.reason).toBe(FOLD_TOO_LARGE);
    expect(runActions(small, true, false, true).fold?.reason).toBe(FOLD_READ_ONLY);
  });
  it("shows why Fold it here is off as text beside it, not only on hover", () => {
    const header = (fold: RunActions["fold"]) => renderToStaticMarkup(createElement(ViewerHeader, {
      output: null, following: true, onFollow() {}, slotRef() {}, onFold() {}, onDownload() {},
      actions: { label: null, download: false, fold } }));
    for (const reason of [FOLD_TOO_LARGE, FOLD_READ_ONLY, FOLD_BUSY]) {
      const html = header({ disabled: true, reason });
      expect(html).toContain(`<span class="vh-why" id="fold-why">${reason}</span>`);
      expect(html).toMatch(/<button disabled="" aria-describedby="fold-why">Fold it here<\/button>/);
    }
    const open = header({ disabled: false, reason: undefined });
    expect(open).not.toContain("vh-why");
    expect(open).toContain("<button>Fold it here</button>");
  });
  it("disables Fold it here while a fold is starting, without a reason", () => {
    expect(runActions(run({ kind: "gallery", browser_foldable: true }), false, true, false).fold)
      .toEqual({ disabled: true, reason: undefined });
  });
  it("labels a browser run and offers Download only once it is done", () => {
    const done = runActions(run({ id: "r1", kind: "browser" }), false, false, false);
    expect(done).toEqual({ label: "Folded in your browser", fold: null, download: true });
    expect(runActions(run({ id: "r1", kind: "browser", status: "running" }), false, false, false).download).toBe(false);
    expect(runActions(run({ id: "r1", kind: "browser", status: "failed" }), false, false, false).download).toBe(false);
  });
  it("shows nothing extra on the server build or with no run open", () => {
    const none = { label: null, fold: null, download: false };
    expect(runActions(run({ id: "2026-10-11-0900-dog" }), false, false, false)).toEqual(none);
    expect(runActions(null, false, false, false)).toEqual(none);
  });
});

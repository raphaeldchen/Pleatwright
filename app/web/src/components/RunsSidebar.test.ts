import { describe, expect, it, vi } from "vitest";
import type { RunSummary } from "../types";
import { dayLabel, removeRun } from "./RunsSidebar";

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

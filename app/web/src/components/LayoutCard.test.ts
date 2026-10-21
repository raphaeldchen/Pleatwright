import { describe, expect, it } from "vitest";
import { layoutCardKey, optionName } from "./LayoutCard";

describe("optionName", () => {
  it("names each option for a screen reader", () => {
    expect(optionName({ id: "smaller", label: "Smaller grid", grid: 32, recommended: true, pros: [], cons: [] }))
      .toBe("Choose Smaller grid, grid 32 (recommended)");
    expect(optionName({ id: "symmetric", label: "Mirror-symmetric", grid: 50, recommended: false, pros: [], cons: [] }))
      .toBe("Choose Mirror-symmetric, grid 50");
  });
});

describe("layoutCardKey", () => {
  it("changes with the run and with each new event, so a card never carries state across reviews", () => {
    expect(layoutCardKey("r1", 19)).toBe(layoutCardKey("r1", 19));
    expect(layoutCardKey("r1", 19)).not.toBe(layoutCardKey("r2", 19));
    expect(layoutCardKey("r1", 19)).not.toBe(layoutCardKey("r1", 25));
  });
});

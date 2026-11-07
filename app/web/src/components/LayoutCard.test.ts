import { readFileSync } from "node:fs";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { LayoutCard as Card, PwEvent } from "../types";
import { LayoutCard, layoutCardKey, optionName } from "./LayoutCard";

describe("optionName", () => {
  it("names each option for a screen reader", () => {
    expect(optionName({ id: "smaller", label: "Smaller grid", grid: 32, recommended: true, pros: [], cons: [] }))
      .toBe("Choose Smaller grid, grid 32 (recommended)");
    expect(optionName({ id: "symmetric", label: "Mirror-symmetric", grid: 50, recommended: false, pros: [], cons: [] }))
      .toBe("Choose Mirror-symmetric, grid 50");
    expect(optionName({ id: "stretched", label: "Mirror-symmetric, stretched", grid: 62, recommended: false, pros: [], cons: [] }))
      .toBe("Choose Mirror-symmetric, stretched, grid 62");
  });
});

describe("layoutCardKey", () => {
  it("changes with the run and with each new event, so a card never carries state across reviews", () => {
    expect(layoutCardKey("r1", 19)).toBe(layoutCardKey("r1", 19));
    expect(layoutCardKey("r1", 19)).not.toBe(layoutCardKey("r2", 19));
    expect(layoutCardKey("r1", 19)).not.toBe(layoutCardKey("r1", 25));
  });
});

describe("the three-option card (spec 2026-10-22 §8.2)", () => {
  const events: PwEvent[] = readFileSync(
    new URL("../__fixtures__/dog_three_layouts.events.jsonl", import.meta.url), "utf8")
    .trim().split("\n").map((l) => JSON.parse(l));
  const card = events.filter((e) => e.type === "awaiting_review").pop()!.card as Card;
  const html = renderToStaticMarkup(createElement(LayoutCard, { card, explanation: "why", onChoose: () => {} }));
  const buttons = html.match(/<button[^>]*>/g) ?? [];

  it("renders three options, the stretched one first and marked recommended", () => {
    expect(card.options.map((o) => o.id)).toEqual(["stretched", "smaller", "symmetric"]);
    expect(buttons).toHaveLength(3);
    expect(buttons[0]).toContain("Choose Mirror-symmetric, stretched, grid ");
    expect(buttons[0]).toContain("(recommended)");
    expect(buttons.filter((b) => b.includes("(recommended)"))).toHaveLength(1);
    expect(html.match(/\(Recommended\)/g)).toHaveLength(1);
    expect(html).toContain("Mirror-symmetric, stretched");
    expect(html).toContain("Smaller grid");
  });

  it("states what the stretched layout costs, in the user's terms", () => {
    expect(html).toContain("some creases are off the grid, at angles below 45°, so it is harder to precrease and collapse");
    expect(html).toMatch(/folds a model [\d.]+× larger than the plain symmetric layout/);
  });
});

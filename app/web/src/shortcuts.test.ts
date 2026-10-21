import { describe, expect, it } from "vitest";
import { isNewRunKey, type KeyLike } from "./shortcuts";

const k = (over: Partial<KeyLike> = {}): KeyLike =>
  ({ key: "n", metaKey: false, ctrlKey: false, altKey: false, target: null, ...over });
const el = (tagName: string, isContentEditable = false) =>
  ({ tagName, isContentEditable }) as unknown as EventTarget;

describe("isNewRunKey", () => {
  it("fires on a plain n or N from the page", () => {
    expect(isNewRunKey(k())).toBe(true);
    expect(isNewRunKey(k({ key: "N" }))).toBe(true);
    expect(isNewRunKey(k({ target: el("BODY") }))).toBe(true);
    expect(isNewRunKey(k({ target: el("BUTTON") }))).toBe(true);
  });
  it("ignores modified presses and other keys", () => {
    expect(isNewRunKey(k({ metaKey: true }))).toBe(false);
    expect(isNewRunKey(k({ ctrlKey: true }))).toBe(false);
    expect(isNewRunKey(k({ altKey: true }))).toBe(false);
    expect(isNewRunKey(k({ key: "m" }))).toBe(false);
  });
  it("never fires while typing", () => {
    for (const t of ["TEXTAREA", "INPUT", "SELECT"]) expect(isNewRunKey(k({ target: el(t) }))).toBe(false);
    expect(isNewRunKey(k({ target: el("DIV", true) }))).toBe(false);
  });
});

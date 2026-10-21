import { describe, expect, it } from "vitest";
import { STAGES, stageLabel, stageNum } from "./types";

describe("stage labels", () => {
  it("number and name every stage in pipeline order", () => {
    expect(STAGES.map((s) => stageLabel(s))).toEqual(
      ["01 IMAGE", "02 MESH", "03 TREE", "04 PACK", "05 SOLVE", "06 SHAPE", "07 MODEL"]);
    expect(STAGES.map((s) => stageNum(s))).toEqual(["01", "02", "03", "04", "05", "06", "07"]);
  });
});

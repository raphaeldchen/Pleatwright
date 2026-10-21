import { describe, expect, it } from "vitest";
import { downloadFiles, viewFiles } from "./viewerFiles";
import type { Output } from "./types";

const out = (stage: Output["stage"], files: string[], round?: number): Output =>
  ({ key: round === undefined ? stage : `${stage}:${round}`, stage, files, summary: {}, seq: 0,
     ...(round === undefined ? {} : { round }) });

const solve = out("solve", ["Moose_62/solving_cp.svg"]);
const model = out("model", ["model.fold", "Moose_62/overview.png"]);
const all = [out("tree", ["author/tree_round6.png"], 6), out("packing", ["Moose_62/packing_cp.svg"]), solve, model];

describe("downloadFiles", () => {
  it("offers nothing on a tree round: the sheet is a review aid, not an output", () => {
    expect(downloadFiles(all[0], "author/tree_round6.png", all)).toEqual([]);
  });
  it("offers the crease pattern on show", () => {
    expect(downloadFiles(all[1], "Moose_62/packing_cp.svg", all)).toEqual(["Moose_62/packing_cp.svg"]);
  });
  it("offers overview, solved CP and the .fold for the folded model", () => {
    expect(downloadFiles(model, "model.fold", all))
      .toEqual(["Moose_62/overview.png", "Moose_62/solving_cp.svg", "model.fold"]);
  });
});

describe("viewFiles", () => {
  it("a review round shows only its tree sheet, not the mesh views the model read", () => {
    // every unapproved round lists [tree_roundN.png, mesh_views.png]; two files made the
    // header show a file switcher whose second button was pushed off-screen (2026-10-11)
    const r = out("tree", ["author/tree_round6.png", "author/mesh_views.png"], 6);
    expect(viewFiles(r)).toEqual(["author/tree_round6.png"]);
  });
  it("the approved round shows its sheet, never tree.json", () => {
    expect(viewFiles(out("tree", ["author/tree_round7.png", "tree.json"], 7))).toEqual(["author/tree_round7.png"]);
  });
  it("the model shows model.fold (overview is ModelView's own toggle); without a .fold, the overview", () => {
    expect(viewFiles(model)).toEqual(["model.fold"]);
    expect(viewFiles(out("model", ["Moose_62/overview.png"]))).toEqual(["Moose_62/overview.png"]);
  });
  it("other stages show every non-JSON file", () => {
    expect(viewFiles(out("mesh", ["author/mesh.glb", "author/state.json"]))).toEqual(["author/mesh.glb"]);
  });
});

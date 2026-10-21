import type { Output } from "./types";

const ext = (f: string) => f.slice(f.lastIndexOf(".")).toLowerCase();

/** The files the viewer can show for `output`, in order (the first is shown first).
 *  JSON is never shown. A tree round shows only its tree sheet: an unapproved round also
 *  lists mesh_views.png (the render the model read), which made the header grow a file
 *  switcher whose second button fell off-screen. A model output shows model.fold;
 *  ModelView offers overview.png through its own toggle, so the overview is shown only
 *  when there is no .fold. */
export function viewFiles(output: Output): string[] {
  const hasFold = output.files.some((x) => ext(x) === ".fold");
  return output.files.filter((f) => ext(f) !== ".json"
    && !(output.stage === "tree" && f.endsWith("mesh_views.png"))
    && !(output.stage === "model" && hasFold && f.endsWith("overview.png")));
}

/** The run files the viewer header offers for download while `shown` (a file of `output`)
 *  is on screen. A tree round offers none: its sheet is a review aid, not an output, and
 *  its file name counts rounds from 0 while the round buttons count from 1. The 3-D model
 *  view is not a file; for it, the COrigami overview, the solved crease pattern to fold
 *  (from the solve stage's output) and the .fold itself. Otherwise the file on show. */
export function downloadFiles(output: Output, shown: string, allOutputs: Output[]): string[] {
  if (output.stage === "tree") return [];
  if (shown.toLowerCase().endsWith(".fold")) {
    const overview = output.files.find((x) => x.endsWith("overview.png"));
    const solvedCP = allOutputs.find((o) => o.stage === "solve")?.files.find((x) => x.endsWith("solving_cp.svg"));
    return [overview, solvedCP, shown].filter((x): x is string => !!x);
  }
  return [shown];
}

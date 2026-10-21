# Handoff: B5 slice 3 (asymmetric star probe + pose fit) — outcome

**Spec:** docs/superpowers/specs/2026-07-08-b5-pose-fit-slice3-design.md
**Plan:** docs/superpowers/plans/2026-07-08-b5-pose-fit-slice3.md

## What shipped
- `mcp_harness/probe_star_asym.py` — 20-cell (b, h) map: stage-1 EMPTY (no
  noop cells — every asymmetric cell needs squaring); winner b=0.95 h=0.40
  (stage 2, split 0.4724, head_hub_dist 0.3800, maxDisp 1.2859).
- `mcp_harness/pose_target.py` `group_tips_by_head` + 3 tests — pure
  front/back split, ambiguity guard now pytest-pinned.
- `mcp_harness/starhead.py` — parameterized (back_len, head_len);
  head==hub explicit guard; `winner_base()`; default args still reproduce
  the slice-2 halt.
- `probe_angle_range.py` — gates 2+3: fox targets {front 134.8316, back
  138.6544, head 137.7186} deg; per-group achievable ranges at f=0.5 —
  front 22.4729, back 9.8918, head 13.3707 (floor 3.0); best-achievable
  front 49.4863@θ87.5 (gap 85.3452, tol 13.7617), back 62.8255@θ142.5 (gap
  75.8289, tol 2.4549), head 27.1264@θ170.0 (gap 110.5922, tol 2.0817);
  verdict PROCEED (exit 0).
- `probe_pose_fit.py` — gate 4: baseline error 285.9107, final error
  276.2131 (improved); fitted params front (73.75, 0.575), back (73.75,
  0.8), head (73.75, 0.35); per-group gaps vs bounds — front achieved
  73.2749 vs 134.8316 (gap 61.5566, bound 99.1069) OK, back achieved
  22.9936 vs 138.6544 (gap 115.6607, bound 78.2838) MISS, head achieved
  38.7229 vs 137.7186 (gap 98.9958, bound 112.6740) OK; FIT FAIL (exit 1).

## Findings
Stage 1 of the asymmetric (b, h) sweep was empty — no cell packed cleanly
without squaring, so every candidate needed the stage-2 sim rescue. Three
stage-2 rescues were sim-tested and all folded (disp > 1.0), refuting the
"squared folds don't fold" lore for this family; the winner is
b=0.95/h=0.40 (split 0.4724, head_hub_dist 0.3800, maxDisp 1.2859).
Asymmetric stars pack a hub PATH (3 tied degree-6 vertices) rather than a
unique hub, and the head packs on the paper edge (1.0, 0.518).

The head angle — unmeasurable in slice 2 because the head tip coincided
with the axial hub — was finally measurable and actuatable this slice:
monotone in θ, reaching 27.1264 deg @ θ170.0 (gap 110.5922 short of the
fox target 137.7186, tol 2.0817). The front angle was non-monotone in θ,
peaking at 49.4863 @ θ87.5 (gap 85.3452, tol 13.7617); back reached
62.8255 @ θ142.5 (gap 75.8289, tol 2.4549). All three per-group ranges
fell well short of the fox targets, foreshadowing the fit outcome.

The sequential coordinate descent did NOT close on the real-mesh (fox)
target: total error improved from baseline 285.9107 to 276.2131, but the
per-group breakdown shows the fit is not uniform. Front and head landed
within their achievable bounds (OK), but back MISSED badly — the
back-stage achieved 79.1928 in isolation, but by the time the head fold
was applied afterward, the head fold moved the head bone vector and the
final joint capture re-measured back at only 22.9936. This is the root
mechanism: sequential coordinate descent fits each group against a
reference that the next group later moves, so an earlier "good" fit can
be silently undone by a later stage's fold. The landscape was not
unimodal the way slice 1's was — 45/150 cells were inf (unreachable):
head is viable ONLY at f=0.35 (other depths hit flat-equilibrium
maxDisp 0.0, caught by the anti-vacuous guard; f=0.8 was refused because
"wedge arm crosses a real crease"), and the entire back f=0.2 row was
flat-equilibrium. JSONL captured 114 lines (105 evals: front 50 / back 40
/ head 15).

## Slice 4 entry point
The FIT FAIL breaks down into two independent causes, both visible in the
measured numbers:
1. **Cross-group coupling** — the back MISS (79.1928 achieved-in-isolation
   vs 22.9936 final) is caused by later stages (head) moving the
   reference frame the earlier stage (back) was fit against. Candidate
   fix: a second coordinate-descent pass (front→back→head→front→back) on
   the same base — re-fit earlier groups after later ones have moved
   them, or add a final re-pass on top of the already-coded per-stage
   joint scoring. This is the cheapest un-stick: no new code beyond a
   loop, ~50 more captures.
2. **Reachability** — even in isolation, single reverse folds top out
   76–111 deg short of the fox targets (front gap 85.3452, back gap
   75.8289, head gap 110.5922 at their best-achievable θ). A richer op
   vocabulary (e.g. crimp for knee bends, to add a second bend per limb)
   is the other candidate, orthogonal to the coupling fix.

Recommended order: try the cheap second-pass coordinate descent first
(directly addresses the measured back-MISS mechanism) before investing in
new fold primitives, since front and head are already within bounds and
only back needs the re-fit.

## Gotchas carried forward
- All slice-1/2 gotchas still hold (headed SimSession, deterministic
  solver — never 0.0 tolerances, nohup for subagent probes, playwright
  venv-only, scene-frame flat_coords / index-based tracking, spawn workers
  need real script files, probe outputs uncommitted).
- Asymmetric star packing yields a hub PATH (3 tied degree-6 vertices),
  not a unique hub — StarHeadBase must key tips/hub off the squared (sq)
  frame, not raw, because stage-2 squaring snaps boundary floats and raw
  keys get 0 matches.
- Stage-2 squared bases DO fold (disp > 1.0 on all 3 tested) — refutes
  "squared folds don't fold" for this family; don't assume squaring kills
  foldability without testing.
- Head-flap f-viability is narrow: only f=0.35 is reachable; f=0.8 is
  refused by a real-crease-crossing check, and other depths hit
  flat-equilibrium (maxDisp 0.0), caught by the anti-vacuous guard.
- New capture nondeterminism caveat: ~1e-5 deg between baseline and Task 3
  captures, and 0.0201 deg between the head fine-score capture and an
  identical-params final capture — "solver exactly deterministic" needs
  this caveat going forward (don't assert bit-exact repeatability across
  separate capture calls).
- Sequential coordinate descent is not safe against cross-group coupling:
  fitting group A, then group B, can silently undo group A's fit if B's
  fold moves A's reference frame. Any future fitter needs either a
  re-pass or joint (simultaneous) optimization to avoid this.

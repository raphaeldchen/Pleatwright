# Outcome: legibility calibration of `pose_target.angle_error` — **FAIL**

**Run 2026-08-07.** Pre-registration: `2026-08-07-legibility-calibration-prereg.md`,
committed `5598b12` **before** any capture or render existed. Criterion not edited
after the fact.

## Result

| pair | contents | judge's call | type |
|---|---|---|---|
| P1 | BASE vs BASE | No difference | **NULL (control)** |
| P2 | BASE vs SHAPED#3 | No difference | test |
| P3 | SHAPED#2 vs BASE | No difference | test |
| P4 | BASE vs SHAPED#1 | No difference | test |

`k = 0` (test pairs where SHAPED was picked as more dog-like).
Pinned criterion: **FAIL** at `k <= 1`.

**Not VOID.** The null pair was called "no difference" — the control behaved
exactly as a working control should. The judge did not manufacture a preference
between two captures of the same fold, which is what makes the three test-pair
readings trustworthy rather than indifference.

> **A 153-point improvement in `angle_error` (272.49 -> 119.14, -56%, the single
> best measured result of the whole shaping arc) is not visible to a human.**

## Execution record

**Step 0 (sim-free) — PASS.** The incumbent site binds to itself:
`bind_distance = 1.0e-09` against a 1e-6 bound, vertex 18, `find_tip_agrees`.
`front_v18` sits at its pinned reference coords. No silent mis-target — the
hazard the adversary flagged (`_find_tip` is unbounded-nearest,
`shaping.py:123-127` computes `dist` and returns only the vertex) did not fire.

Incidentally confirmed on the way: **`n_tips_raw = 16` -> `n_tips_served = 8`.**
`complete_square` halves the addressable tip set exactly as the research
reported.

**Step 1 — 5/5 captures, zero retries, zero parks.** All above `DISP_GATE`
(0.10). `front_v18`'s known park risk did not materialise.

| capture | maxDisplacement |
|---|---|
| BASE x2 | 1.5950, 1.5908 |
| SHAPED x3 | 0.9418, 0.9216, 0.9390 |

The shaped folds displace consistently *less* (~0.93 vs ~1.59) because the
incumbent op replaces full +/-180 creases with partials (wedge arms -142.5,
tip axial +105 = 180 - 2*142.5).

Op used, verbatim from `2026-07-12-handoff-b5-prime-outcome.md`:
`outside:0.0,0.46801304:0.12398308661620648:142.5`

**Step 2 — dependency-free SVG renderer.** matplotlib is absent from the venv
and that venv is symlinked to the MAIN repo, so installing would have mutated
the user's main environment and its CI-pinned deps. Wrote a numpy-only
orthographic renderer with painter's-algorithm depth sort and fixed Lambert
shading instead. 7 fixed views, one shared scale from the union bounding box,
identical lighting/edge weight/panel size across conditions.

## Deviations from the pre-registration (disclosed, none affecting the criterion)

1. **A/B presented as top/bottom rows, not left/right.** Randomisation intact;
   only the axis changed.
2. **The null pair was presented as P1, not P4.** The prereg's section 6 table
   listed a fixed pair->id mapping while section 5 specified a seeded shuffle;
   the implementation shuffled presentation order as well as within-pair
   position, so the null moved. `BLIND_KEY.json` is the authoritative record and
   marks it `is_null: true`. The criterion is defined on "the NULL pair",
   identified by the key, so it is unaffected. The prereg was internally
   inconsistent on this point and that is a defect in the prereg, not in the run.
3. **Claude was unblinded** by the key printing to the terminal during rendering.
   The judge's blinding was unaffected. Claude gave no read before the answers
   were recorded, per prereg section 5.
4. **The limb-naming question (`g`) was not separately answered.** Moot: `k = 0`
   triggers FAIL on its own branch of the criterion.

## Routing consequence (pinned in prereg section 9, applied unchanged)

> FAIL -> the entire measured shaping ladder is un-anchored. Routes B-E stop:
> none can be evaluated, because the number they move has no product meaning.
> The honest successor is to change *what* is shaped rather than how it is
> searched.

Concretely, this retires as **unevaluable**:

- **Route A** — shipping the 119.14 pose. Its value was the assumption this
  experiment tested, and the assumption is false. Do not ship it as a product
  feature. (Two platform chips + kick-hardening were never the real blocker.)
- **Route B** — composed-move kappa-descent. Already refuted arithmetically
  (needs 22,600x; best measured composition 28.75x); now also pointless, since
  the objective it would unlock is not visible.
- **Route C** — off-flat serve state. Already refuted by measurement (no rigid
  off-flat state exists; global closure minimum is the fully flat state).
- **Route D** — more direction-changing ops. The ceiling is an anchor problem,
  and every op in the family moves the same invisible needle.
- **Route E** — silhouette/chamfer objective. Its premise was that a richer
  objective sees structure the 3-scalar projection hides. That premise is now
  *more* interesting, not less — but it cannot be evaluated against
  `angle_error`, and it needs a registration step that does not exist.

## Post-hoc: the change is ENORMOUS, and still invisible

"No difference" has two very different causes — (a) a real, substantial change
that is not legible, or (b) a change barely above solver noise. These route
oppositely, so it was measured. SO(3)-restricted Kabsch fit (reflection
forbidden: memory records that `orthogonal_procrustes` optimises over O(n) and
a reflection would flatter the fit), over the shared vertex prefix.

| comparison | rms | max | max / model extent |
|---|---|---|---|
| **noise** — BASE#1 vs BASE#2 | 0.0020 | 0.0082 | 0.52% |
| **drift** — SHAPED re-reads (3 pairs) | 0.0046–0.0058 | ≤0.0244 | ≤1.30% |
| **signal** — BASE vs SHAPED (3) | 0.2964–0.2973 | **1.3541** | **72.5%** |

**Signal-to-noise: 55.6x.** The most-moved vertex travels **72.5% of the
model's entire extent**; **38 of 39 vertices move more than 5%**. The three
shaped reads agree to ~1% of extent, so the +/-7 deg shaped-read drift never
dominated this comparison.

> **The op is not weak. It rearranges the model massively and reproducibly,
> and the result is still indistinguishable from the unshaped base.**

This is a stronger result than a null effect, and it settles a question the
route adversary explicitly left open. The prior base-inspection finding — "a
uniaxial base CANNOT show anatomy" — was measured on *unshaped* bases, and the
adversary correctly flagged that extending it to *shaped* models would be
over-application. It now extends, measured: for this op class, shaping a
uniaxial base produces a differently-shaped illegible object, not a more
legible one.

**Routing force:** "do more of the same, harder" is dead in a way that a
weak-effect result would not have killed. More ops, better search, a finer
objective, or a bigger angle change all move the same axis, and that axis has
now been measured invisible at 55x signal-to-noise. The vocabulary has to change
in KIND — the two candidates the research surfaced are width/narrowing (which
`grep -i "narrow|taper|width" shaping.py` confirms we entirely lack, and which
COrigami names as what let their models "deviate from the rigid skeleton") and
Lang's own tree-side constructions, which sit inside CLAUDE.md section 2 and are
upstream of all five walls.

## Objection answered: "was this measured on a STALE base?"

Raised by the user, and correct on provenance: `tests/goldens/dog.fold` was last
touched **2026-07-03** — before the perfect-base slices (S1–S8, Jul 25–31) and
before goals 1 & 2 existed. Memory records its source tree as unrecoverable and
that perfect-base S4 found it "concealed 2 of 3 blockers". A legibility verdict
measured only on that artifact would be open to exactly this challenge.

**Re-tested on a base compiled by today's pipeline.** A `quadruped` template
compiled through `server.draft_and_compile_full_base` — the REAL serve path
including the rescue ladder (memory: bare `HeadlessTreemaker` is NOT the serve
path; that has bitten this repo three times) — then squared, shaped with the
same recipe family, and captured.

| base | hull coverage | source |
|---|---|---|
| golden dog (2026-07-03) | 0.6636 | `boundary_cycle` |
| **fresh quadruped (today, real serve path)** | **0.6810** | `boundary_cycle` |

**Judge's verdict on the fresh base: still no nameable body parts** — the same
as the golden. +1.7pp of coverage changes nothing about legibility.

**Why goals 1 & 2 cannot fix this, structurally.** *Uniaxial* means every flap
tip lies on one line — that is the definition, and it is what makes the base
flat-foldable. Goal 1 makes more of the square creased; Goal 2 makes the crease
pattern mirror-symmetric. **Neither separates the flaps in space.** A base can
have 100% coverage and perfect mirror symmetry and still collapse every limb
onto a single axis. That is corroborated by the goals' own instrument:
COORDINATION.md §1's frozen-scorecard check records "no goal-owned axis
moved — `hull_coverage` is unchanged on all five."

**What this does NOT say:** that base generation is the wrong place to fix
legibility. It says the two axes *currently in flight* do not touch it. A third
base-side axis does — Lang's **plan-view base** (TreeMkr40 pp.38–40: force the
active paths onto the symmetry line with pinned auxiliary nodes, so the
silhouette reads from above rather than edge-on). That is a tree-side change,
inside CLAUDE.md §2's contract, upstream of all five shaping walls, and blocked
on `ProjectActivePaths` refusing any axis but 45°.

## What this does NOT establish

- Nothing about **other subjects** (one subject, one op, one theta).
- Nothing about **narrowing/width**, which the vocabulary entirely lacks
  (`grep -i "narrow|taper|width" shaping.py` returns nothing). COrigami states
  that stick figures cannot represent appendage width and that narrowing is
  what let their models "deviate from the rigid skeleton". This experiment says
  the *direction* axis is invisible; it says nothing about the *width* axis.
- Nothing about whether a **larger** angle_error change would be visible. n = 3
  test pairs is a screening design: well-powered for FAIL (two illegible objects
  are visible at n = 1), under-powered for a marginal PASS. That asymmetry was
  declared in advance and it points the right way here.
- It does **not** show the shaping code is broken. The op applied cleanly, the
  captures folded, the control worked. The geometry did what it was told. The
  finding is that what it was told to do does not matter to a viewer.

## POST-HOC (2026-08-07, after the verdict): a real, view-specific signal

**The pre-registered verdict is unchanged and stays FAIL.** `k = 0`, criterion
pinned at `5598b12` before any image existed. It is not being relabelled after
seeing data — doing so would devalue every future gate in this repo. What
follows is a separate, post-hoc observation with its own (weaker) status.

**Observation.** Reviewing the sheets *after* answering, the judge flagged that
panel 6 of 7 (view index 5: elevation −25°, azimuth −125°, the from-below
isometric) shows what reads as a side view of a dog with front and hind legs.
They named it in **P2 row B, P3 row A, and P4 row B**, plus the "squared
shaped" row of the slab diagnostic.

**Those are all, and only, the SHAPED condition** — and they are three
*independent* solver captures plus a fourth from a separate run. The judge had
no access to `BLIND_KEY.json` when identifying them. Four-for-four on shaped,
zero on the two BASE captures.

**Confirmed on an enlarged render** of view 5 alone at a shared scale, both
BASE captures beside all three SHAPED: the structure is present in shaped and
absent in base.

### Correction to this document's own interpretation

The sections above say the improvement is "invisible". That overreaches what
was measured. The measured claim is narrower and should be read as:

> **No difference in a whole-sheet, seven-views-at-once preference comparison.**

A signal confined to one camera can wash out when a judge weighs one entire row
against another. It did.

### The protocol flaw, named

The design averaged seven views into one verdict per row. The repo already knew
legibility here is violently view-dependent — memory records a uniaxial base is
"a triangle face-on and a SINGLE LINE edge-on". COrigami shows its VLM seven
views and *scores them*; it never asks for a single whole-sheet preference. That
difference now looks load-bearing rather than incidental.

### What this re-opens

- **A per-view re-test** is warranted, properly pre-registered, judged
  per-camera with a BASE-vs-BASE null at the same camera. **Zero new captures** —
  the geometry is already on disk.
- **Route E (silhouette/projection objective) gains positive evidence.** The
  route adversary noted that rank-1 share 0.915 was computed on a
  *3-dimensional* readout (front/back/head) and "says nothing about the rank of
  the true response in a 100-dim silhouette space", so E's premise was
  unrefuted. There is now evidence *for* it: a projected-silhouette signal
  exists that `angle_error`'s three scalars do not capture.
- **A candidate for the missing deterministic acceptor:** count limb-like
  protrusions in the projected 2-D silhouette, per view. Computable without a
  browser, it is what the eye is doing in view 5, and it would supply the
  arithmetic instrument the standing rule demands.

## Artifacts

`captures.json` (5 raw captures incl. `vertices_coords` / `faces_vertices` /
`flat_coords`), `pair_P1..P4.svg`, `BLIND_KEY.json`, `step0_bind.py`,
`step1_capture.py`, `step2_render.py` — session scratchpad.
Cost: 5 headed captures, ~4 min of browser, ~1 h wall clock.

# Goal 1 — Whole-square design: the projection, the axis, and the corner ceiling

**Date:** 2026-08-04
**Status:** design, approved for planning
**Base commit:** `1c9abe0`
**Author:** Goal 1 planning session (Claude + raphaeldchen)
**Companion:** the S1 cp-mirror spec (`2026-08-04-cp-mirror-metric-design.md`),
whose §9.2 named S4a/S4b/S5 and whose `mirror_verdict(axis_degrees=…)` this
slice is the first real caller of. Goal 2 runs in parallel; see
`docs/superpowers/goals/COORDINATION.md`.

> **Supersedes** `2026-08-02-boundary-placement-conditions-design.md` (revision
> 2, never executed, 0 of 55 plan checkboxes). What that spec got right is
> carried forward with attribution in §2 and §9. What it got wrong is corrected
> in §3.3 and §9 — including one risk (R8) this session **measured and
> falsified**, and one mechanism claim it inferred correctly but for a reason
> that turns out not to be the operative one.

---

## 1. Why this slice exists

CLAUDE.md §1.1 is binding: **every model folds from one uncut square, and the
folder receives the whole sheet.** Today the crease pattern reaches only the
convex hull of the leaf positions. Measured at `1c9abe0` on the frozen
scorecard:

| bird | humanoid | quadruped | insect | fish |
|---|---|---|---|---|
| **0.5000** | 0.6319 | 0.7161 | 0.8595 | 0.9077 |

A third to a half of the sheet arrives with no creases and no instructions, and
`square_complete` hides it from the 3-D viewer because the squared fold reads
coverage `1.0000` by construction.

**Done means:** models reach more of the square, AND the system can state how
much, AND it can argue that against design scale instead of moving it silently.

### 1.1 The premise this slice had to correct first

CLAUDE.md §1.1(2) asserts *"Corner occupancy is the open axis."* That bullet
bundles three separable claims, and they do not share a fate. §3 rules on each
against measurement taken this session and committed at
`docs/superpowers/evidence/2026-08-04-axis-corner-capacity/`.

The short version: **corner occupancy is real and reachable, and the thing that
blocks it is our own symmetry axis.** The diagonal axis this engine hard-codes
supplies exactly **two** pairable corners. Book symmetry supplies **four**. On
all five production subjects the optimizer finds a four-corner, leaf-hull
`1.000000` solution at book — four of them at *higher* design scale — and every
one of those is unreachable today because `ProjectActivePaths` re-symmetrizes
about `y = x` regardless of the requested angle.

---

## 2. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| **Lang, `tmConditionNodesPaired` + `PairFn1A`/`PairFn1B`** (`tmConstraintFns.cpp`) | The optimizer's mirror constraint is already fully general in the axis: two linear equalities parameterized by `mSymLoc` and `mSymAngle` — segment ⟂ axis, midpoint on axis | **Adopted as the specification of S4b₀.** We do not invent rows; we evaluate Lang's at the angles we support. §4.2 |
| Lang, TreeMaker 4.0 manual §2.2 | Works an example where diagonal symmetry *drops* the scale and is less efficient than book; "either can win", and TreeMaker lets you check both | **Adopted.** We never checked; §3.4 is the first check on this corpus |
| Lang, same manual §3.3 (pp. 49-52) | 5 equal flaps: 0.323 all-on-edge vs **0.353** with one middle flap; "the most efficient crease pattern will have at least one middle flap" for ≥5 flaps | **Adopted, with the example's arms corrected** — §3.2 shows this engine's *unconstrained* solve lands on 0.323556 and corner-pinning reaches 0.353553. The rule survives; CLAUDE.md §1.1(4)'s reading of it does not |
| COrigami (arXiv:2606.26299, incl. R. J. Lang), Appendix A | Names "forcing leaf nodes to paper edges to reduce layer count" as one of four manual interventions their 1.1%-success automated baseline bypassed | **Adopted as motive** (layer count, not efficiency); the automation of *selection* remains the novel part |
| `2026-08-02-boundary-placement-conditions-design.md` §1.1 | Boundary conditions cannot raise the global optimum: `tmScaleOptimizer` already bounds leaves to the paper rectangle, maximises `-u[0]`, and has no coverage term | **Adopted and re-derived.** This is the regime-independent argument CLAUDE.md §1.1(2) should have made instead of the 83%-on-boundary sample |
| Same spec, §4.6 / R8 | *"`ProjectActivePaths` moves the node off the boundary"* — boundary equalities are exact, the projection advertises ~1e-5 of movement as safe | **REJECTED — measured false.** §3.5. Inferred from reading the routine, never measured; the clamp protects a pin at 0 or `w` |
| Same spec, §4.2 rule 2 | Corner policy as a **mirror-class partition** | **Adopted and explained.** §3.4 gives the structural reason the partition exists and why the diagonal's class count is 2 |
| "Is Self-Repair a Silver Bullet?" (ICLR'24, arXiv:2306.09896) | Breadth over depth at a fixed budget | **Adopted** — S4b₀ is a two-angle branch, not a search |
| `packer-two-basins-scale-lever` (project memory) | ALM's exit is a *stalling* test, not an optimality test; max-scale packs sit near tangency, where 1-ULP platform differences flip outcomes | **Adopted as the governing caution.** Book raises scale on 4 of 5 subjects, i.e. toward the cliff. §5.3 makes margin-to-cliff a reported quantity, not an afterthought |
| MCTS over feasibility-checked edit moves (IJCAI'23, arXiv:2211.13219) | Search over a discrete constrained action space | **Rejected** — no measured failure asks for search over axes; there are three |

**Not found:** no prior work automating symmetry-axis *selection* per model in a
tree-theory packer. Asserted from the surveys in project memory
(`origami-landscape-survey`), not from a fresh systematic search.

---

## 3. What was measured, and what it settles

All measurements this session, on this worktree's engine `.so`, committed at
`docs/superpowers/evidence/2026-08-04-axis-corner-capacity/`. Each probe runs
every arm in an isolated child process (the engine can SIGSEGV).

> **These are bare-`HeadlessTreemaker` measurements, deliberately.** A variant ×
> angle grid wanting attribution is exactly the case where the bare compile is
> the right instrument; the serve path is not. Every *acceptance* pin in the
> plan compiles through `server.draft_and_compile_full_base` instead.

### 3.1 The three claims inside CLAUDE.md §1.1(2)

**Claim A — "boundary-forcing is not a lever."** Right conclusion, wrong
evidence. The 83%-on-boundary figure is equal-flap-only (69.7% unequal, k=3 →
0/3), so it cannot carry the conclusion. The conclusion survives on the
objective-side argument instead (§2, row 5), which holds at every k and every
flap distribution.

**Claim B — "coverage IS corner occupancy."** Right about *where* the loss is,
wrong about what moves it. For a convex outline touching all four sides the
missing area is exactly the corner regions — bird's 0.5000 is arithmetically
the inscribed diamond. The error is the implied inverse.

**Claim C — "corner occupancy is the open axis."** The bullet's own supporting
example refutes it. *"k=4 puts 4/4 at the corners and scores coverage 1.000"* is
true of the **unpaired** `star(4)` (measured: coverage `1.000000`). Add the
bilateral pairing every production tree carries and the same 4-leaf star gives
**coverage `0.500000`, zero corners**:

| star-4 arm | scale | coverage | corners |
|---|---|---|---|
| `star(4)` unpaired, free | 0.500000 | **1.000000** | 4 |
| `symmetric_pairs_star(4)`, free | 0.353553 | **0.500000** | 0 |
| `symmetric_pairs_star(4)`, pair → (1,0)/(0,1) | 0.292893 | 0.414214 | 2 |

The headline is unpaired-only; the product is paired. That last row is the
record's *"pinning corners cost 17.2% of both scale and coverage"* — both ratios
are `0.828427`, i.e. **−17.16% on each axis, to six digits.** The number is
real; §3.4 shows what it is actually a measurement of.

### 3.2 Corner pinning on unpaired stars, and Lang's example

| k | free scale | free coverage | corner-pinned scale | corner-pinned coverage |
|---|---|---|---|---|
| 5 | 0.323556 | 0.703897 | **0.353553** (+9.3%) | **1.000000** |
| 6 | 0.292893 | 0.828427 | 0.274292 (−6.4%) | **1.000000** |
| 7 | *build FAILS* | — | 0.258819 (rescue) | **1.000000** |
| 8 | 0.255983 | 0.924501 | **0.258819** (+1.1%) | **1.000000** |

Coverage reaches **exactly `1.000000` on all four**; three of four are
scale-neutral-or-better.

**`0.323556` and `0.353553` are Lang's §3.3 numbers, and CLAUDE.md §1.1(4)
attaches them to the wrong arms.** In the manual, 0.323 is the *constrained*
all-on-edge case and 0.353 the freer one. On this engine the **unconstrained**
solve lands on 0.323556 — Lang's worse basin — and pinning four of five corners
forces the fifth leaf into the middle, producing `0.353553 = 1/(2√2)`, Lang's
preferred one-middle-flap optimum, **with coverage 1.000**.

Lang's example therefore contains no coverage/scale trade at all. The trade was
read into it. **The rule in §1.1(4) — argue the trade explicitly — survives and
gets stronger**, because §3.3 shows the trade has no fixed sign.

> **k=7 is a rescue, and this slice does not chase it.** A constraint that makes
> an unpackable tree pack is a rescue rung; the recorded lesson
> (`rescue-ladder-vs-alignment-tool`) is that two specs were already built as
> rescue rungs when the ask was alignment tools for models that pack fine.
> Recorded, not pursued.

### 3.3 Coverage and scale are independent

All three sign combinations occur:

| arm | scale | coverage |
|---|---|---|
| star-5, 4 corners | **+9.3%** | **+42.1%** |
| star-4-sym, pair → corners | −17.2% | −17.2% |
| HUMANOID, 4 edges (1-equality) | **+1.5%** | **−12.7%** |

`bbox_area = 1.000000` on **every** packing arm across all five probes.
Coverage is purely outline shape, never pattern size — so any "the pattern got
smaller" mechanism is excluded.

**Consequence for the goal's framing:** the scale dividend the ladder discards
(`rescue_ladder.Rung.admissibility` has no scale term; `_search_first_clean`
returns on first clean; dog-raw reaches 0.651163 and never compares the
0.733734 it builds) is **not** a coverage lever and must never be scoped as
one. It remains real and worth taking, justified on scale alone.

### 3.4 ★ The finding this slice is built on: the axis sets a corner ceiling

A paired leaf can only occupy a corner whose mirror image is also a corner.
About the **diagonal**, only `(1,0) ↔ (0,1)` qualifies; `(0,0)` and `(1,1)` lie
**on** the axis and are available to unpaired axial leaves only. **The diagonal
supplies exactly two pairable corners.** About **book**, the mirror is
horizontal: `(0,0) ↔ (0,1)` and `(1,0) ↔ (1,1)` — **four.**

Measured at the optimizer only (`run_scale_optimization`, never
`build_and_export`, so the projection never runs), two pairs → four corners:

| subject | diag45 | book0 | scale vs diag45 free | leaf hull vs diag45 free |
|---|---|---|---|---|
| star-4-sym | **FAIL** | 0.500000 / hull 1.000000 / 4 cnr | **+41.4%** | 0.500 → 1.000 |
| QUADRUPED | **FAIL** | 0.720456 / 1.000000 / 4 cnr | **+7.9%** | 0.681 → 1.000 |
| BIRD | **FAIL** | 0.726750 / 1.000000 / 4 cnr | **+11.4%** | 0.669 → 1.000 |
| HUMANOID | **FAIL** | 0.769231 / 1.000000 / 4 cnr | **+22.2%** | 0.559 → 1.000 |
| INSECT | **FAIL** | 0.683946 / 1.000000 / 4 cnr | −10.4% | 0.789 → 1.000 |

**Perfect separation, 5 of 5 both ways.** Every diagonal arm fails identically
(`scale optimization did not converge (reason code 1)`). star-4-sym's +41.4% is
`√2` and reproduces memory's independently-measured figure to five digits.

So the earlier *"8 of 8 corner arms fail on the production templates"* is **not
a fact about corner pinning.** It is a fact about asking the diagonal for four
corners when it structurally has two. And the discriminator is **not** constraint
count — it is **mirror-consistency of the requested position with the active
axis**. Count mattered only because a one-equality pin (`set_node_on_x/y`) is
easier to satisfy consistently than a two-equality pin (`set_node_at`): 4 of 12
paired arms survived the former, 0 of 8 the latter.

#### What this does NOT claim

- **These are optimizer readings, not packs.** `BuildTreePolys` /
  `IsPolygonValid` / `BuildPolysAndCreasePattern` never ran. Several arms
  optimize cleanly and die at the polygon stage.
- **Leaf hull ≠ `hull_coverage`.** `hull_coverage` reads B-assigned vertices of
  the *exported* fold; this is the hull of leaf positions. Related, not equal.
- The 49-cell sweep records 7 cells dying in the molecule build *downstream* of
  the projection, so a corrected projection does not deliver all of this.

**Honest statement: a measured lower bound on the potential, not a guarantee of
the outcome.** Converting it is exactly what S4b₀ exists to do, at Sonnet cost
rather than Opus.

#### The one-equality edge policy, and where its ceiling actually is

At the diagonal's two legal corners the one-equality policy does produce wins —
INSECT reaches scale 0.842724 (**+10.4%**) and leaf hull 0.971593. But the
export-level run of that same arm dies at `polygon network is not valid after
optimization (scale=0.842724)` — the same scale to six digits, and inside the
dead band memory already records for INSECT (packs 0.763400; fails 0.801475 and
0.873705). **Its ceiling is the tangency cliff, not the projection.** It is
therefore folded into the 0α measurement, not built as a slice.

### 3.5 R8 falsified: the projection does not drop boundary pins

Displacement of the pinned coordinate, optimizer → post-projection:

| arm | worst \|post − requested\| |
|---|---|
| star-5 4 corners (2-eq), star-6 1 corner (2-eq), HUMANOID 4 edges (1-eq) | 0.00e+00 |
| BIRD pair0 edge | 1.13e-10 |
| QUADRUPED pair0 edge | 4.38e-09 |
| star-6 4 edges (1-eq) | 6.63e-10 |
| **star-7 4 edges (1-eq)** | **5.83e-07** |

**Record the closure narrowly.** Boundary pins survive **for a clamp-specific
reason**: the projection is a *damped* least-squares step starting from the ALM
solution, and its per-iteration clamp holds `x ∈ [0,w]`, `y ∈ [0,h]`, so a pin
at exactly 0 or `w` sits **on the clamp**, which the step cannot push outward
and has no incentive to pull inward. This does **not** generalize to interior
pins, and emphatically **not** to "the projection preserves constraints" — the
symmetry rows are the standing counterexample, since they preserve the *wrong*
mirror perfectly.

**Consequences:** the previously-proposed "add boundary rows to the projection"
slice is cancelled. And S4a′ must **verify and report** boundary pins rather
than refuse them; refusal would reject configurations measured to work.

star-7 — 5.83e-07, two orders above every other arm, on the one tree that only
builds when pinned — is the margin-to-cliff signal §5.3 adopts.

---

## 4. Design

### 4.1 S4a′ — the projection refuses what it cannot represent

`ProjectActivePaths` (`mcp_harness/TreemakerWrapper.cpp`) builds mirror rows as
literally `x[b] − y[a] = 0` and `y[b] − x[a] = 0`. It reads `mSymAngle`
**nowhere**. `w` and `h` *are* read, and used only for the on-paper clamp —
never in the mirror rows.

Three changes, all inside that routine plus one error-vocabulary entry:

1. **Refuse a non-45° axis.** Gate on `!syms.empty()`, **not** on
   `HasSymmetry()` — `set_symmetry_angle` can set an angle with zero pairs, the
   routine emits no mirror rows in that case, and a non-45° angle is genuinely
   harmless there. Gating on `HasSymmetry()` is a false positive that breaks
   unpaired trees.
2. **Refuse non-square paper** when `!syms.empty()`. The mirror
   `(x,y) → (y,x)` is the reflection about `y = x`, which is the paper's centre
   diagonal only when `w == h`; `server.py` exposes `paper_width`/`paper_height`
   as caller-settable with `1.0` defaults, so a non-square sheet desynchronises
   the optimizer's mirror from the projection's **at 45° too**. Fix the
   routine's own comment in the same edit — it says *"the 45-degree axis y=x
   through the paper center (0.5,0.5)"*, which is self-inconsistent for `w ≠ h`.
3. **Verify, do not refuse, boundary pins.** Post-projection, assert each
   `tmConditionNodeCombo` X/Y-fixed value is honoured, and report. §3.5.

Plus: **expose `outIters`/`outCons` at the production call site.** The signature
already carries them; only `debug_active_path_report` passes them, and
`BuildAndExport` discards both. And **add the projection failure string to
`error_recipes`** — `_MATCHERS` carries five codes, `_RECIPES` is keyed on the
exact string `"polygon network is not valid"`, and the projection message says
`"became invalid after active-path projection"`, so `classify()` returns `None`
and every projection failure on record has landed unclassified.

**This is also the cheapest possible ODR pre-flight.** `GetSymAngle()` exists in
both vendored `tmTree.h` twins at different offsets
(`treemaker/Source/tmTree.h` and
`treemaker/Source/tmModel/tmTreeClasses/tmTree.h`; memory
`treemaker-odr-tmtree-header`). If the accessor reads the wrong member through
the wrong header, the guard fires on every 45° compile and every golden goes red
on the first run. That is a feature, and it de-risks S4b₀ for free.

### 4.2 S4b₀ — book and 90° as exact rows

`tmConditionNodesPaired::AddConstraints` emits `PairFn1A` and `PairFn1B` per
pair, both parameterized by `mSymLoc` and `mSymAngle`:

```
1A:  (xi − xj)·ca + (yi − yj)·sa = 0                  segment ⟂ axis
1B:  (−xi − xj + 2px)·sa + (yi + yj − 2py)·ca = 0     midpoint ON axis
```

Evaluated at the three angles we support, on square paper with
`p = (w/2, h/2)`, these reduce to exact integer rows:

| angle | mirror | row 1 | row 2 | form |
|---|---|---|---|---|
| **45° (shipped)** | `(x,y) → (y,x)` | `xj − yi = 0` | `yj − xi = 0` | homogeneous |
| **0° (book)** | `(x,y) → (x, h−y)` | `xi − xj = 0` | **`yi + yj − h = 0`** | **inhomogeneous** |
| **90°** | `(x,y) → (w−x, y)` | `yi − yj = 0` | **`xi + xj − w = 0`** | **inhomogeneous** |

The 45° pair is Lang's rows exactly: at `ca = sa = √2/2, p = (0.5,0.5)`, 1A and
1B give `xi + yi = xj + yj` and `yi + yj = xi + xj`; adding and subtracting
yields `yi = xj` and `xi = yj` — the two rows already shipped. **An identity,
not an approximation.** Independently re-derived by the reviewer before
approval.

**Implementation: branch on the angle, emit the exact rows per case. No `cos`,
no `sin`, at any supported angle.** The 45° branch is the existing code path
untouched, so goldens cannot move at 45° by construction — which the plan still
verifies by running, not by asserting. S4b₀ therefore carries **none** of
S4b-general's exposure: no trig in a `tol = 1e-13` loop, no new roundoff, no
platform-epsilon surface.

#### ⚠ The sign hazard this table conceals

**At 45° both rows are homogeneous — coefficients `{+1, −1}`, RHS zero. At 0°
and 90° one row is inhomogeneous.** An implementer pattern-matching off the
existing rows will write `yi − yj = 0` where `yi + yj − h = 0` belongs.

That mistake **does not crash and does not fail to converge.** It enforces
*translational* symmetry (same y) instead of *reflective* symmetry (mirrored y),
and returns PACK on a base that is not mirror-symmetric at all — the identical
silent-wrongness failure this entire goal exists to close, reintroduced by the
slice meant to fix it. The existing assembly machinery absorbs it cleanly:
`r1 = y[a] + y[b] − h` with `c1 = {1.0, 1.0}` needs no structural change, which
is exactly why the sign error is invisible at the call site.

**The new branches are structurally different from the 45° branch, not variants
of it.** §6 makes that a tested property, not a warning.

#### Non-square: refuse, and record the constants

Solving Lang's rows at 45° with `p = (w/2, h/2)` gives
`xj = yi + (w−h)/2` and `yj = xi − (w−h)/2` — the shipped rows with the
constants dropped, provably zero on every current caller and wrong for any
other. **S4a′ refuses `w ≠ h`; the constants are recorded here so a later slice
lifts the refusal deliberately rather than re-deriving them.** The refusal is
testable today (`init_paper(1.0, 2.0)` + a pair → expect throw); the fix is not,
because no caller exists to exercise it.

### 4.3 0α — the premise probe and its fixture

The five probes in
`docs/superpowers/evidence/2026-08-04-axis-corner-capacity/` are committed
evidence-of-record. 0α hardens them into a single reproducible probe under
`mcp_harness/` writing a `fixtures/` JSON, following `probe_symmetry_axis.py`
(which already imports `paper_coverage` and already writes a fixture — a fork
of a working instrument, not a new one), and adds:

- the **paired/unpaired split** as the reported discriminator (§3.4);
- the **one-equality edge-pin arms** — this is where the boundary policy lives
  now, as measurement rather than as a slice;
- a **non-vacuous order-restart control on an unequal-length tree.** The
  planner's own control was run on `star(5)`, whose five leaves are identical, so
  permuting them is a relabeling and 12/12 identical results were
  near-guaranteed. That is the "measured in the regime where it cannot fail"
  error, committed by this session and recorded rather than buried;
- **margin-to-cliff**, calibrated against `QUAD`'s two basins (macOS 0.717008 vs
  Linux 0.714406, which flip the symmetry verdict and not merely coordinates) as
  the existing "how close is too close" reference point.

**The CLAUDE.md §1.1(2)+(4) edit is NOT part of 0α's implementation session.**
It is drafted by the planning session as its own small commit citing the
committed fixture — it reverses two numbered claims in the document that governs
every future session's premises, and it turns on history (how §1.1(4) came to
attach Lang's numbers to the wrong arms, and why the rule survives the example)
that does not transfer through a spec.

### 4.4 Phase-0 instrument work

- **`design_scale` column.** The value ships in `frame_title`;
  `pose_base` already regex-parses `scale=([0-9.]+)`. **Extract one shared
  parser and make `pose_base` its caller** — two independent parsers of the same
  string is how this project gets bitten. The regex is unsafe on the tail:
  `[0-9.]+` silently captures `1` from `1e-07`, which is precisely when the
  column most needs to be honest. With all three sign combinations occurring
  (§3.3), no scorecard row can be read without this column.
- **`paper_coverage.hull_coverage` → true polygon area.** `_hull()` is convex +
  shoelace, and a convex hull can only *overstate* a non-convex outline. Reuse
  `pose_base._border_cycle` — the B-edge traversal is already written and
  exercised. Fallback must be **named, never silent**: extend the existing
  `source` field. **Honest expectation: this moves nothing today**, because the
  committed outlines are already convex; it is a pre-registration for
  experiments that have not run, and the PR should say so in those words.
  **Lands standalone — Goal 2 rebases onto it before reporting any coverage
  number.**
- **Display.** Nothing in the frontend shows `hull_coverage`, and it is only
  meaningful *pre*-`square_complete`, so any A/B must read `json`, not
  `display_json` (`web/server.py::_send_frames`). Goal 1's user-facing trigger
  is the older *"a triangle, not a square"* report, which `square_complete`
  answered **display-only** — so the user already looks at a square whose second
  half has no creases. One read-only badge, computed server-side from the
  existing Python, worded as the A-3 ACCEPT teaching already in the repo.
  Counter-argument on the record: a number the system cannot yet move invites
  *"why is it 50%?"*, survivable only because 0α lands first with the answer.

---

## 5. Measurement and the frozen baseline

### 5.1 The protocol, binding on both goals

`mcp_harness/fixtures/scorecard_baseline.jsonl` is **FROZEN at `1c9abe0`** for
the duration of both goals. That file has been re-blessed six times, `--out`
**appends** so regenerating means replacing it wholesale, and its own `_meta`
records `quadruped` deltas it can only label `NOT_attributable` because the
prior baseline was two shipped slices stale — with one branch in flight.

```
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python \
    benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl
```

- Every PR reports that delta table and attributes each moved row to a slice.
- **A row that cannot be attributed is a FINDING, not noise** — say so in the PR.
- **One combined re-bless at the very end of both goals**, with a full
  attribution table in `_meta`. Not before.
- Its `_COLS` carries **both** goals' columns in the same rows —
  `hull_coverage` and `design_scale` are Goal 1's, `cp_symmetric` /
  `cp_mirror_residual` / `cp_mv_broken` are Goal 2's. Coordinate every `_COLS`
  edit in `COORDINATION.md`.

**Verified consequence of adding a column:** `_diff` reads both sides with
`.get(c)`, so a new column renders as `None -> 0.717008` on **every** row. The
delta table will fire five times for a slice that changed no geometry. The PR
must label that as column-addition, not movement.

### 5.2 S4a′ can move `error_codes`

Adding the projection string to the vocabulary means previously-unclassified
failures become named, and `error_codes` is a diffed column. **Attribute it; do
not absorb it.**

### 5.3 Margin-to-cliff is reported, not assumed

Book raises scale on 4 of 5 subjects (§3.4), and memory records that max-scale
packs sit near tangency where 1-ULP platform differences flip outcomes. S4b₀
**reports the projection's iteration count and residual** (§4.1) on every arm.
Without it, a book0 failure cannot be told apart from "book geometry is
rejected" — and that distinction is the whole result.

---

## 6. Acceptance criteria

**S4a′**

1. A non-45° angle **with pairs** raises a named error; **without pairs** it does
   not (gated on `syms`, not `HasSymmetry()`). Both directions tested.
2. `init_paper(1.0, 2.0)` + a pair raises a named error.
3. A boundary pin is **verified and reported**, not refused; the reported
   displacement reproduces §3.5's table to within an order of magnitude.
4. `classify()` returns a code for the projection failure string. Verified by
   **deleting** the vocabulary entry and watching a test go red.
5. The nine committed goldens are **byte-identical**. Verified by running.
6. `outIters`/`outCons` are non-`None` at the production call site. Verified by
   deleting the argument pass-through, not by a count assertion.
7. Full suite from a correctly built worktree: **2241 passed, 11 skipped, 0
   failed** at `1c9abe0`, ± only rows this slice attributes.
8. Verified on Linux in the `ci-amd64-run` container **before** merge.

**S4b₀**

9. **`cp_mirror.mirror_verdict(fold, axis_degrees=0.0)["symmetric"] is True` on
   all five subjects, through `build_and_export`.** This is `mirror_verdict`'s
   first use off 45° — it was built with `axis_degrees` as a parameter in S1 and
   never exercised. It is the direct refutation of §4.2's sign hazard and of
   every other way a book0 base could come back mirrored about the wrong thing.
   (`axis_reflector`'s `centre` defaults to `(0.5, 0.5)`, matching
   `set_symmetry_angle`'s `tmPoint(0.5w, 0.5h)` on square paper — which S4a′
   makes mandatory.)
10. **Negative control:** a tree whose pairs satisfy `yi = yj` but **not**
    `yi + yj = h` is **moved** by the projection, not left alone. This is the
    test that fails if row 2 is written homogeneously.
11. The 45° branch is byte-identical: goldens unmoved, and the 45° code path
    provably untouched by diff inspection **and** by test.
12. Every book0 arm reports its margin proxy (§5.3), so a failure is
    attributable to the cliff or to the geometry.
13. Linux container run before merge.

**0α**

14. A committed probe reproduces §3.1–§3.5's tables from a clean checkout, and
    writes a `fixtures/` JSON.
15. The order-restart control runs on an **unequal-length** tree and its result
    is reported whichever way it falls.

---

## 7. Sequence and gates

| slice | what | model | gate |
|---|---|---|---|
| **S4a′** | verify pins; refuse non-45° and non-square; classify the projection error; expose the margin proxy | Sonnet, high | **none — go now.** Goal 2's S3 is blocked on it |
| **S4b₀** | book + 90° as exact ±1 rows; non-square guard rides along | Sonnet, high | immediately after S4a′ merges |
| **0α** | four probe rounds → fixture; edge-pin arms; unequal-tree order control; margin-to-cliff | Sonnet, medium | parallel throughout |
| CLAUDE.md §1.1 edit | planning session drafts it | — | after 0α's fixture lands |
| **S5** | axis selection; coverage vs scale as an argued trade | Opus, high | **S4b₀ reported AND Goal 2's S3 merged AND re-measured** |
| **S4b-general** | arbitrary angle: trig, ODR, cross-platform | Opus, max | only if S5 shows an angle outside {0, 45, 90} pays |

**The S5 gate is a double gate and only `COORDINATION.md` can enforce it.** S3
pins unpaired axial leaves and was measured to move bird coverage
0.5206 → 0.6612 and scale 1.3093 → 1.3518. S5's entire deliverable is the
coverage-versus-scale argument; running it before S3 lands argues against
numbers about to move ~27% on the subject with the lowest coverage in the
corpus. Git cannot warn about this.

**The C++ file is strictly serial:** Goal 1's S4a′ → Goal 2's S3 → Goal 1's
S4b₀. Claim `mcp_harness/TreemakerWrapper.cpp` in `COORDINATION.md` before
dispatching; release on merge.

---

## 8. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **The inhomogeneous-row sign error** — silent, returns PACK, reintroduces this goal's own defect class | §4.2's hazard note; criteria 9 and 10. Criterion 10 is the one that fails if it happens |
| R2 | **Book0 geometry is rejected downstream** by the molecule build (7 of 49 sweep cells died there) | This is why S4b₀ is Sonnet-high and not Opus-max: we learn it cheaply. §5.3's margin proxy separates "cliff" from "rejected" |
| R3 | **Book raises scale toward the tangency cliff** on 4 of 5 subjects | §5.3; `QUAD`'s two basins as the calibration reference |
| R4 | **ODR twins** — `GetSymAngle()` reads through the wrong header | S4a′ is the pre-flight: a bad read turns every 45° golden red on the first run |
| R5 | **Scorecard churn across two parallel goals** | §5.1's frozen protocol; one combined re-bless at the end |
| R6 | **The 45° branch is disturbed** | It is the existing code path untouched. Criterion 11 verifies rather than assumes |
| R7 | **`design_scale` regex captures `1` from `1e-07`** | §4.4; one shared parser with a test on scientific notation |
| R8 | ~~`ProjectActivePaths` moves the node off the boundary~~ | **Falsified by measurement**, §3.5. Closed narrowly: boundary pins survive *for a clamp-specific reason*, which does not generalize to interior pins or to constraint preservation in general |
| R9 | **A worktree without the three build artifacts fakes `FAIL-LINT` on every verdict** | Build in place. **`build.sh` defaults to `PYTHON=python3`**, which on this machine resolves to a Homebrew interpreter without `pybind11` and **exits without producing a `.so` and without an obvious failure**; the worktree has no `.venv` of its own. Use `PYTHON=<main-checkout>/mcp_harness/.venv/bin/python ./build.sh` |

---

## 9. Out of scope

- **S4b-general** (arbitrary angle) until S5 justifies it.
- **A boundary-condition rung in the rescue ladder.** §3.4's one-equality policy
  is measurement in 0α, not a slice; its ceiling is the tangency cliff.
- **Adding boundary rows to `ProjectActivePaths`** — cancelled by §3.5.
- **The k=7 rescue** (§3.2). Recorded, not chased.
- **Scale-ranking the ladder.** Real and worth taking; justified on scale alone
  (§3.3), never as a coverage lever, and not in this goal.
- Reworking `square_complete.py`.
- Any change to `_audit_score`, `lint_verdict`, or the acceptance ratchet.
- Goal 2's S2/S3, and the gate retrain.

---

## 10. Owed, not closed

- The 49-cell axis sweep that reordered this goal is **not in the repository** —
  `fixtures/` holds only `symmetry_axis_evidence.json` from 2026-08-02. This
  spec's own §3 tables are committed at
  `docs/superpowers/evidence/2026-08-04-axis-corner-capacity/`; the sweep itself
  is still uncommitted prose and should be regenerated or retired.
- §3.4's readings are optimizer-only; the export-path confirmation is S4b₀'s
  deliverable, not a claim made here.
- `QUAD`'s Linux/OpenBLAS basin still has no Linux-measured `cardinality` /
  `n_vertices` (carried from the S1 spec §10) — which bears on §5.3's use of it
  as a calibration point.

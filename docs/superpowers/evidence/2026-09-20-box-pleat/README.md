# Box-pleating compiler vs TreeMaker on the 17 committed trees (2026-09-20)

Regenerate: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python probe_box_pleat.py --out ../docs/superpowers/evidence/2026-09-20-box-pleat`

**2026-09-23 provenance note:** `results.json` and `table.md` were **hand-patched** for the Task 8 update below, not produced by that regenerate command. A full re-run would recompile `dog`, `rabbit` and `spider` — `dog` alone costs ~21 s of box-pleat pack plus a full TreeMaker compile, `rabbit` costs tens of minutes at the search budgets in play, and `spider` is the run that did not finish in 60 minutes (see "Layer order" below) — so the untouched columns were carried over byte-for-byte from the 2026-09-22 run and only `layer_order`, `layers_tried`, `stage_reached` and the fold-derived columns were hand-edited per subject, as itemized below. Regenerating from scratch will not reproduce this file's `spider` row (still the pre-feature `contradiction` reading) or `rabbit`'s row (see its caveat below) without also re-running those two subjects.

Spec: docs/superpowers/specs/2026-09-20-box-pleat-compiler-design.md §6 (pre-registered bar), §11 (execution amendments); docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md (pleat reassignment, the feature this file's Task 8 update reports on).

Run: 2026-09-22, one pass over all 17 subjects, `--out docs/superpowers/evidence/2026-09-20-box-pleat` with TreeMaker and the JVM lint both enabled (no `--no-treemaker`/`--no-lint`). Wall clock ~13m30s dominated by `dog` (21.1 s box-pleat pack + TreeMaker) and `scorpion` (109.9 s box-pleat pack alone, at the `max_N=76`/`pack_budget=200_000` override carried over from `tests/test_box_pleat_e2e.py`). No TreeMaker compile failed, timed out, or SIGSEGV'd on any of the 17 subjects — every row has both a `scale_bp` and (except `crab`, which never reaches `pack`) a `scale_tm`.

**2026-09-23 update (Task 8): pleat reassignment landed and was measured on this same corpus.** `compile_tree` now searches M/V labellings of the fixed crease set for one whose layer order is globally consistent (spec `2026-09-22-pleat-reassignment-design.md`), and is wired in by default. **"Globally consistent" here means no contradiction this propagation found, not a proven flat-foldability certificate** — see the fuller caveat under "Coverage" and in "Layer order" below. This file's `layer_order` and `layers_tried` columns, the **Bar** counts and the **Coverage** section below are updated to the new measurement **where a new measurement exists** — every subject except `spider`, whose row is carried over unchanged from the 2026-09-22 run and flagged in place (its `layer_order` cell says so). Every other column (`N`, `scale_bp`, `scale_tm`, `hull_coverage`, `tip_hull_coverage`, `pack_ms`, and all 7 `contours`/`tree`-stage failures), on every subject, is **carried over unchanged** from the 2026-09-22 run rather than re-measured, because the packing, the elevation field and the folded base are byte-identical by this feature's own invariant (Global Constraints, pleat-reassignment spec) — re-running TreeMaker and the JVM linter on inputs that provably cannot have changed would only add cost, not information. The one exception is `rabbit`, whose `stage_reached` moved from `emit` to `assign`; its fold-derived columns (`hull_coverage`, `maekawa_defects`, `lint_class`, `flat_fold_ok`) are cleared to empty because it no longer has a fold, and its `failure` cell carries a caveat about the budget it was actually measured at (see the table below). See "Layer order" below for the full per-subject accounting and `docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md` §11 for the measured costs behind these numbers.

## Bar

- reached `emit`: **8/17** (dog, horse, guinea_pig, lizard, frog, bird, starfish, octopus) — down from 10/17 in the 2026-09-22 run. `rabbit` no longer reaches `emit`: at `compile_tree`'s default budgets it now refuses honestly at stage `assign` rather than emitting a base that cannot physically stack (see "Layer order" below). `spider`'s own pleat-reassignment measurement did not resolve within 60 minutes at `layer_budget=25` and was stopped (see "Layer order" below) — its pre-feature 2026-09-22 row (`emit`, unchecked `contradiction`) is excluded from this count rather than assumed to still hold, since this feature's own point is that an unchecked `contradiction` is not a shown-foldable base.
- `maekawa_defects == 0`: **8 confirmed post-feature** (9 rows below read 0, including `spider`'s excluded stale row, which still carries its pre-feature reading because that row was carried over unchanged rather than re-measured — see the provenance note above)
- `lint_class ∈ {PASS, BENIGN}`: **8 confirmed post-feature** (9 rows below read `PASS`, same caveat: `spider`'s row is the carried-over stale one)
- `flat_fold_ok`: **8 confirmed post-feature** (9 rows below read `True`, same caveat; `max_error` is on the order of 1e-15, matching the ≤2.6e-15 closure figure recorded in the task-7 report)

These four counts land on the same subjects in every column — the bar is met or missed as a unit here, not partially. This is unchanged from 2026-09-22 in kind, only in count. (`lint_class`/`maekawa_defects`/`flat_fold_ok` are independent oracles; the certification verdict, folded into the `emit` count above, carries the caveats spelled out in "Certification bar" and "Layer order" below.)

**Provenance of the lint verdicts, because lint is LABEL-dependent and this feature moves labels.** The byte-identical-base invariant justifies carrying over the geometry columns, but not these: Oriedita lints the M/V assignment, and 13 of `lizard`'s 41 assignments moved. So every emitting subject's lint row is a post-feature reading, measured on the labelling it now emits — `horse`, `lizard`, `frog`, `octopus` (plus the unchanged `starfish`, `bird`) in the 2026-09-23 final review, and `dog` and `guinea_pig` in a dedicated 12m52s run of the lint tier the same day, specifically because they were the two the review had left carried over. `spider`'s row is the stale 2026-09-22 one and is excluded from the counts above.

## Scale penalty (ratio = scale_bp / scale_tm, both paper-per-grid-unit)

16 subjects carry both scales (`crab` refuses at stage `tree`, before a layout — and therefore a `scale_bp` — exists).

min **0.732** (spider), median **0.8845**, mean **0.9523**, max **1.297** (lizard). Full column, sorted:

| subject | ratio |
|---|---|
| spider | 0.732 |
| dolphin | 0.744 |
| rabbit | 0.814 |
| dog | 0.838 |
| bat | 0.85 |
| bird | 0.852 |
| starfish | 0.854 |
| scorpion | 0.859 |
| octopus | 0.91 |
| horse | 0.986 |
| elephant | 1.037 |
| guinea_pig | 1.056 |
| cat | 1.089 |
| ant | 1.139 |
| frog | 1.18 |
| lizard | 1.297 |

**Lang makes no percentage claim, and the one this project previously attributed to him ("up to 40%") was an error, now retracted in the spec (§11.18).** What Ch. 13 (p. 573) says is that circle/river packing is provably the most efficient uniaxial packing, so box pleating "must be, by definition, less efficient" — and that "the penalty is often very small, and uniaxial box-pleated structures can still be surprisingly efficient."

The measurement confirms the qualitative claim and is stronger than "very small": the mean penalty is **4.8%** (mean ratio 0.9523), the median is 11.6% (0.8845), and **6 of 16 subjects read ratio ≥ 1.0** — cat, elephant, guinea_pig, ant, frog and lizard get *longer* flaps per unit of anatomy from this compiler than from TreeMaker. The worst case is spider at 0.732 (a 26.8% penalty).

Both quantities are paper length per grid unit of tree length (`scale_bp = 1/N`; `scale_tm = design_scale × unit`), so they are directly comparable as "how much paper one unit of anatomy buys" — which is what a designer feels as flap length. They are not a packing-area efficiency, and nothing here is evidence about area. Two honest caveats on the six ratios ≥ 1.0: five of those subjects (cat, elephant, ant — plus dolphin, bat, scorpion among the losers) never produced a valid crease pattern, so their `N` is the first layout that packed rather than one that also survived the contour stage; restricted to the 10 subjects that emit a validated fold, the mean is **0.9519** and only guinea_pig, frog and lizard exceed 1.0.

## Coverage

`hull_coverage` reads exactly **1.000** on every currently-emitted fold (the B border is the square; measured, not assumed) — no exceptions. This was measured on 10 folds in the 2026-09-22 run; neither `rabbit` nor `spider` contributes one under this feature's own measurement (see "Layer order" below), so the current count is 8 — the figure has not changed, only how many subjects supply it.

**This is the result the exercise was for.** TreeMaker creases only the convex hull of the leaf nodes, which is structural rather than a tuning gap: the creased region is built as that hull (`tmTree::CalcBorderNodesAndPaths`) and the optimizer's objective is scale alone with no coverage term, so Lang & Demaine simply "assume that the paper P and the convex hull of the leaf node vertices P_H are one and the same" (*Facet Ordering and Crease Assignment in Uniaxial Bases*, Origami⁴, §2.2 p. 193). The project's own committed readings of that path: `hull_coverage` mean **0.7230 → 0.8591** across the five serve-path subjects after the root wave (bird 0.9848, fish 0.9077, insect 0.8595, quadruped 0.8797, humanoid 0.6638), and **0.46–0.66** on the older goldens (CLAUDE.md §1.1). Polygon packing's rule 4 — every cell belongs to some polygon — makes 1.000 the *construction*, not an optimization target, and it holds on every subject that emits. The ~5% mean scale cost above is what that buys.

**Layer order is now part of the bar, though only half the old gap is closed.** The 2026-09-22 gap this paragraph used to describe — an unchecked `contradiction` verdict not failing the bar — is closed by the pleat-reassignment feature (`docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md`): `compile_tree` now searches M/V labellings of the fixed crease set and refuses at stage `assign`/`layers` rather than emit a base whose layer order contradicts itself. Measured 2026-09-23 on this corpus: every subject that still reaches `emit` reads `layer_order = consistent`, by construction — this is now an invariant of the reported bar, not a separately-tracked field. **But `consistent` is not a certificate of flat-foldability** — `layer_order._propagate` is not confluent (spec §10) and the module under-refutes further via `AREA_EPS`-dropped cells (its own docstring) — so the 8 emitted bases below have been shown only to have no contradiction that this traversal found, not to be free of layer self-intersection. See "Layer order" below for the full per-subject accounting, including `rabbit`, which stopped emitting.

## Layer order (pleat reassignment, measured 2026-09-23)

Headline: **before this feature, 2 of the 10 emitting subjects read
`consistent` — no layer-order contradiction found (`bird`, `starfish`). After
pleat reassignment landed, 8 of the (then) 10 read `consistent`. As of
2026-09-23's layer certification (measured below, in "Certification bar"),
all 8 of the 8 currently-emitting subjects are `CERTIFIED` — `compile_tree`
no longer reports a two-valued layer-order reading at all: `Result.verdict`
is three-valued (CERTIFIED / REFUTED / UNDECIDED).** A `consistent` verdict meant only that no
contradiction was found by this propagation, never a proof of
flat-foldability: `layer_order._propagate` is not confluent (spec §10), and
the module under-refutes for a second, independent reason
(`AREA_EPS`-dropped cells, per its own docstring). Only the negative
direction is sound — `contradiction` ⇒ cannot stack — so a `contradiction`
verdict is a real finding while a `consistent` one reads "none found," not a
certificate. Per the plan's own binding rule (spec §10's 2026-09-23
correction and §11 item 2): pin **verdicts**, never witness strings — two witnesses
on this same corpus changed under a Task 2 closure change with no verdict
change, so a witness is a traversal artefact, not a stable identifier. Only
`layers_tried` and the verdict/kind are reported here as facts; no witness
crease is quoted as if it were reproducible.

**How large is that hedge? Measured 2026-09-23 — see "Oracle completeness
census" below.** On 5 of the 8 emitting subjects propagation forces *every*
overlapping face pair (`dog` all 30,697), so the hedge there is about
cross-checking a complete relation, not about unexplored search. On `starfish`
it is wide open: 236 of the 561 pairs in its deepest cell are undetermined.

| subject | outcome | `layers_tried` | note |
|---|---|---:|---|
| starfish | consistent (unchanged) | 1 | already consistent before this feature; first candidate accepted, byte-identical fold |
| bird | consistent (unchanged) | 1 | already consistent before this feature; first candidate accepted, byte-identical fold |
| octopus | **consistent (repaired)** | 2 | was `contradiction` in the 2026-09-22 run |
| horse | **consistent (repaired)** | 5 | was `contradiction` |
| lizard | **consistent (repaired)** | 9 | was `contradiction` |
| dog | **consistent (repaired)** | 10 | was `contradiction`; 565.5 s (contended host) |
| guinea_pig | **consistent (repaired)** | 20 | was `contradiction` |
| frog | **consistent (repaired)** | 22 | was `contradiction` |
| rabbit | **refused — budget, stage `assign`** | 56 | see below; was `contradiction`-but-emitting in the 2026-09-22 run |
| spider | **stopped after 60 min at `layer_budget=25`, no verdict reached** | unknown (run stopped, not exhausted) | was `contradiction`-but-emitting in the 2026-09-22 run; see note below |

Every subject that resolves does so in at most 22 candidates — an order of
magnitude below the `layer_budget=200` default, which is therefore a
give-up threshold rather than a capacity knob that any solvable subject
actually needs (spec §11, item 9).

**`rabbit` stopped emitting, and that is a finding, not a regression** (owner
ruling, 2026-09-22: "refuse — it's a finding, not a regression"). Before this
feature, `rabbit` reached `emit` carrying an unchecked layer-order
contradiction — a base that had never been shown to be foldable. It now
refuses honestly: at `compile_tree`'s default budgets it reaches stage
`assign`, not `layers`, because `assign_budget` (500,000 local-CSP search
nodes) is exhausted at 56 layers-stage candidates before `layer_budget`
(200) can even bind — measured directly at `layer_budget=100` (same
stopping point, `1765` s; `1be01b0`), and inferred to hold at the actual
default `layer_budget=200` because the node budget, not the layer budget,
is what binds (56 « 100 « 200). **This does not establish that `rabbit`'s
crease set admits no consistent labelling** — only a `layer_unsat` verdict
(the search space genuinely exhausted) would establish that, and `rabbit`
never reaches the `layers` stage at all under default budgets. (`lizard`
reaches `layer_unsat` at 11 candidates only under a probe that forces every
candidate to be rejected, to characterize the per-rejection cost; `lizard`'s
actual recorded outcome, in the table above, is `consistent (repaired)` at 9
candidates.) So `rabbit`'s refusal localises the
defect in this search's own weakness (a no-good clause covering 125 of 249
variables prunes almost nothing — spec §11 item 8), not in the packing, and
not in an established absence of a foldable labelling.

**`spider` did not resolve in 60 minutes at `layer_budget=25`, and the run
was stopped.** This is a bounded negative — a measurement in its own right,
not an absence of one — and it is the strongest single illustration of this
design's own named plan risk #1 (spec §9, "search blow-up on dog and
spider") measured anywhere in this corpus. The controller's cost-model
script (`compile_tree(..., layer_budget=25)` over the full corpus,
sequential) ran `spider` — the largest subject here, 146 faces — for a full
hour with no verdict reached (no `emit`, no `LayerFail`, no `AssignFail`)
before the run was stopped. Every other subject in the corpus finished in at
most **9.4 minutes** (`dog`, 565.5 s, contended host, 10 candidates); the
next most expensive was `guinea_pig`, 272.9 s (4.55 min). Because the run was stopped rather
than left to terminate, **`spider`'s `layers_tried` at the stop point is
unknown, and no try count should be extrapolated from this** — do not
present this as an outcome, and do not infer `emit`/`refuse`/`exhausted`
from it. Per this task's instructions `spider` was not compiled a second
time in parallel while that run was in flight, and once it was stopped, was
not re-run under this task's own time budget either. `spider` carries no
outcome in the per-subject table above — it appears there only as a
labelled non-outcome row — and is deliberately absent from
`LAYERS_EXPECTED` in `tests/test_box_pleat_e2e.py` for this reason — see
`docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md`'s matching
note for the full accounting. Re-run
`probe_box_pleat.py --subjects spider` (budgeted, and expect it to run well
past `dog`'s cost) to fill this row in.

## Oracle completeness census (`oracle-census/`)

**Why this exists.** Everything above hedges the `consistent` verdict — "no
contradiction found", never a proof. That hedge was never *sized*. This census
measures the two independent deficits behind it, on the 8 emitting subjects at
their shipped labelling, and they turn out to have opposite profiles.
Regenerate: `PYTHONPATH=. ../.venv/bin/python
../docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/unforced_census.py
OUT.json` from `mcp_harness/` (~17 min; `dog` 524 s, `guinea_pig` 354 s).

| subject | faces | cells | max cover | pairs | unforced | widest cell | non-confluence |
|---|---|---|---|---|---|---|---|
| starfish | 38 | 6 | 34 | 671 | **252 (37.6%)** | **236** | none found |
| bird | 104 | 94 | 76 | 4012 | 8 (0.2%) | 8 | none found |
| lizard | 20 | 7 | 12 | 158 | 8 (5.1%) | 8 | none found |
| horse | 166 | 82 | 124 | 12407 | **0** | 0 | none found |
| octopus | 144 | 134 | 114 | 8036 | **0** | 0 | none found |
| frog | 28 | 29 | 20 | 290 | **0** | 0 | none found |
| guinea_pig | 28 | 27 | 20 | 290 | **0** | 0 | none found |
| dog | 298 | 150 | 180 | 30697 | **0** | 0 | none found |

`pairs` is `cons.pairs`, the canonical overlapping face pairs from the
arrangement cells. `unforced` is how many of them propagation leaves `None` at
its fixpoint. `widest cell` is the most unforced pairs inside a single
arrangement cell — the local search width, since the total-order requirement is
per cell. `non-confluence` re-runs propagation under FIFO drain and two
seeded-random worklist orders and reports pairs whose value disagrees, pairs
only one order decides, and verdict flips; all three were 0 on all 8.

**Reading 1 — the search is nearly empty, so the follow-up §10 names is the
whole of it.** On 5 of 8 subjects, including all the large ones, propagation
forces **every** overlapping pair: `dog` decides all 30,697 across a 180-face
stack, `horse` all 12,407. The relation is complete — a total order on every
cell. `bird` and `lizard` leave 8 pairs, which is 256 completions before any
pruning. Only `starfish` has a real search instance. So the expensive half of
Akitaya-Demaine-Ku (DFS backtracking over the undecided variables, §10's
"satisfiability result") is **not what this corpus needs**; what it needs is the
cross-check §10 already identifies as "the *correct* fix" and defers. On a
complete relation that check is search-free and polynomial.

**Reading 2 — the widest gap is on the smallest subject, and nothing we report
would have shown it.** `starfish` is the 4-grid toy that passes in 1 try with 0
flips, and 236 of the 561 pairs in its deepest cell (42%) are undetermined. Its
`consistent` is close to vacuous. The cause is structural, not a size effect:
it has only **6 arrangement cells** and 34 of its 38 faces stack over one of
them, so there are few constraints per pair. Compact bases stack deeply over
few cells and get *less* forcing, not more — the opposite of the intuition that
small subjects are the safe ones. Cover-size histogram `{2:1, 6:1, 10:1, 14:1,
30:1, 34:1}`; the 34-face cell holds 236 unforced pairs, the 30-face cell 140,
the 14-face cell 28, and the three shallower cells 0. Those per-cell counts
**overlap** — a pair lies in every cell both its faces cover, so they do not
sum to the 252 distinct unforced pairs. The 236 is the figure that sizes the
search, because the total order has to be decided per cell.

**Reading 3 — non-confluence has no measured exposure here, which relocates
that follow-up rather than closing it.** Spec §10 proves the rule is
order-dependent by flipping `mesh-humanoid`'s verdict. Nothing on this corpus
moved under three alternative orders. Those are compatible: §10's flip is on
serve-path geometry. **Do not read the zeros as "the rule is confluent"** — the
probe permutes the closure worklist and neighbour walk, not the order the other
families are applied, and three orders are not all orders. The value of the
confluence follow-up is on the serve path (`mv_symmetrize`, `mv_repair`,
`root_rank`, and `server.py`'s serve gate all call `layer_order`), not here.

**What this does not measure.** `AREA_EPS`-dropped sliver cells, the other
independent under-refutation reason, are invisible to this census by
construction: a dropped cell removes pairs from `cons.pairs` before it is
counted, so the denominator already excludes them. A 0 in the `unforced` column
says the pairs that *survived* `AREA_EPS` are all forced, nothing more.

### Certification bar (`layer_certify`, measured 2026-09-23)

The census above sized the `consistent` hedge but never closed it. This
module (`mcp_harness/layer_certify.py`, wired into `compile_tree` in
`box_pleat/compile.py`) closes it by checking Akitaya-Demaine-Ku's clauses
against the complete relation `layer_order` derives, and searching for a
labelling of the free variables it leaves undecided (`decide`, node-budgeted
at `CERTIFY_BUDGET = 50_000`). `compile_tree` now reports one of three
verdicts — `CERTIFIED`, `REFUTED`, `UNDECIDED` — in `Result.verdict`, in
place of the old `consistent`/`contradiction` reading. **`compile_tree` no
longer reports a two-valued layer-order reading at all** — it named "no
contradiction this propagation found," which the Oracle completeness census
above showed was close to vacuous on `starfish` (252 of 561 pairs in its
deepest cell undetermined); `CERTIFIED` names a stronger, checked claim
instead. (`consistent` itself is still reported, independently, by
`probe_box_pleat.py` — see the main results table's preamble below.)

Measured against the pre-registered bar (`docs/superpowers/specs/2026-09-23-layer-certify-design.md`
§6), regenerate with `oracle-census/certify_corpus.py` (~16.4 min wall clock;
the eight per-subject times sum to 15.7 min, the rest being interpreter startup
and imports — `dog` 537 s and `guinea_pig` 285 s dominate):

| subject | kind | nodes | free | stage_reached | tried | secs |
|---|---|---:|---:|---|---:|---:|
| starfish | CERTIFIED | 12 | 114 | emit | 1 | 0.1 |
| bird | CERTIFIED | 3 | 2 | emit | 1 | 3.6 |
| lizard | CERTIFIED | 3 | 2 | emit | 9 | 6.8 |
| horse | CERTIFIED | 1 | 0 | emit | 5 | 15.4 |
| octopus | CERTIFIED | 1 | 0 | emit | 2 | 36.5 |
| frog | CERTIFIED | 1 | 0 | emit | 22 | 55.5 |
| guinea_pig | CERTIFIED | 1 | 0 | emit | 20 | 285.1 |
| dog | CERTIFIED | 1 | 0 | emit | 10 | 537.3 |

Every bar item held on this run: `horse`/`octopus`/`frog`/`guinea_pig`/`dog`
CERTIFIED with `free == 0` and `nodes == 1` (bar item 1); `bird`/`lizard`
decided with `free == 2` and `nodes <= 8` (bar item 2, both at `nodes == 3`);
`starfish` — the one subject the bar does not pin — reads CERTIFIED with
`nodes == 12` against `free == 114` independent variables (after the
equality quotient `layer_certify.decide` applies to the census's
252-unforced-pairs reading), resolved inside the `CERTIFY_BUDGET = 50_000`
node budget (bar item 3); `git diff` for `mcp_harness/layer_order.py` is
empty (bar item 5). Because every subject CERTIFIED, `starfish`'s golden
fold (`tests/data/starfish-v1.fold`) still matches and needed no
re-fixturing.

**Bar item 4 (every emitted `.fold` byte-identical to commit `46e2750`'s
output) was measured directly, not inferred from the code.** `46e2750` is
the commit immediately before this feature's first line of code.
`compile_tree` was run twice on the same `rule6_serve.json` input for all 8
subjects: once against the working tree at `46e2750` (obtained by
`git archive 46e2750 | tar -x` into a scratch directory — a read-only export
of that commit's tree, done without `git stash`, without moving `HEAD`, and
without checking out another commit in this worktree — then run with
`PYTHONPATH` pointed at that extracted copy) and once against current `HEAD`.
The two resulting fold dumps (`old_folds.json`, `new_folds.json`) have
identical sha256 `3492e4b0c8fe333f794252cde25db25457d0065f32612eb817d21494cf2dc784`,
and all 8 subjects compare field-for-field identical. Bar item 4 holds.

**Two results worth stating past the table.** `starfish` resolving its 114
free variables in 12 search nodes is the measurement that justifies
searching for ONE satisfying order (`decide`) instead of enumerating all
folded states the way ADK's algorithm does: its 252 unforced pairs form a
single component, so enumeration there costs 2^114, while satisfiability
took twelve decisions. The five `free == 0` rows (`horse`, `octopus`,
`frog`, `guinea_pig`, `dog`) are the verifier working with *no search at
all* — `dog` decides all 30,697 overlapping pairs across a 180-face stack by
propagation alone, and certifying it is then a polynomial pass over a
complete relation. That gap between "propagation already decides
everything" and "one real search instance" is why `verify` is a separate,
search-free function from `decide`.

**A stale expectation this wave's full test run surfaced, unrelated to
certification.** `mcp_harness/tests/test_box_pleat_e2e.py` ran in full
(not the filtered `-k` selections earlier waves used) for the first time
since pleat reassignment landed, and `spider` failed both
`test_subject_reaches_emit_and_audits_clean` and
`test_subject_lints_pass_or_benign`: it exhausts `assign_budget` (500,000
local-CSP search nodes) at the `assign` stage and never reaches `layers`,
measured 2026-09-24 at 1:23:45 wall clock. `layer_certify.certify` is
reached only after `assign` accepts a candidate, so no line this task
added or changed ran for `spider` — this is not a consequence of layer
certification. It was already stale: the 2026-09-22 pleat-reassignment
wave had already recorded `spider` as a bounded negative (no outcome in 60
minutes at `layer_budget=25`, see "Layer order" above) and excluded it
from `LAYERS_EXPECTED` for exactly that reason, but left
`FAST_EXPECTED["spider"]`/`LINT_EXPECTED["spider"]` at `None` in
`test_box_pleat_e2e.py`, still asserting spider emits cleanly — a
contradiction that wave's own filtered verification never exercised.
Recorded now as a strict xfail (`_SPIDER_BUDGET`) in both tables, following
the same pattern already used for `rabbit`'s `_RABBIT_BUDGET`. This does
**not** establish that no consistent labelling or layer order exists for
`spider`.

**The surviving caveat: CERTIFIED is not flat-foldable.** `CERTIFIED` means
certified against the constraint set that survived `AREA_EPS` —
`layer_order.AREA_EPS` drops sliver arrangement cells before `cons.pairs` is
built, and a dropped cell only ever *removes* constraints, never adds one.
This census (and `layer_certify` itself) cannot see that deficit by
construction: a dropped cell removes its pairs before they are counted, so
every denominator above already excludes them. Closing that is separate,
undone work.

## Crease-pattern gallery (`cp-gallery/`)

`cp-gallery/gallery.html` renders all 8 emitting subjects: the crease pattern
beside its flat-folded base. Open it from that directory — the page references
the SVGs rather than inlining them, so the two travel together (inlining cost
408 KB of duplicated content for no benefit in a committed artifact).

**What is being shown, and why it is not a before/after.** Pleat reassignment
changes no geometry: same vertices, same edges, same count of folded creases,
same folded base. A side-by-side of v1 and the repaired pattern would be two
indistinguishable pictures. So the page marks in **amber every crease whose M/V
label the search changed**, against `assign()`'s own output with the
`global_check` hook switched off — which is exactly v1's labelling, verified
byte-identical to `mcp_harness/tests/data/lizard-v1.fold` on the one subject
that has a committed golden.

| subject | grid N | creases | relabelled | candidates |
|---|---:|---:|---:|---:|
| starfish | 4 | 55 | 0 | 1 |
| bird | 54 | 184 | 0 | 1 |
| octopus | 74 | 257 | 10 | 2 |
| horse | 46 | 307 | 56 | 5 |
| lizard | 34 | 27 | 13 | 9 |
| dog | 74 | 569 | 129 | 10 |
| guinea_pig | 64 | 43 | 15 | 20 |
| frog | 38 | 43 | 15 | 22 |

Three readings the table alone does not give:

* **The relabelled set is connected, not scattered.** `lizard`'s is a spine with
  two kites; `horse`'s is two full-width bands plus mirrored corner segments.
  That follows from the CSP's structure — a pleat path is a chain of pieces
  Maekawa forces to share a label, so a flip propagates along the whole path and
  cannot be one isolated crease.
* **It respects the mirror.** `horse`'s relabelled set is bilaterally symmetric,
  because mirrored pieces share a solver variable.
* **Search effort and repair size are unrelated.** `horse` moved 56 labels in 5
  candidates; `frog` moved 15 in 22. `dog` moved 129 — 23% of its 569 creases —
  in 10.

`starfish` and `bird` relabel **nothing**: they were already consistent, and the
spec requires their emitted FOLD to stay byte-identical. That requirement is
asserted by `test_already_consistent_subjects_emit_byte_identical_folds`; the
gallery is what it looks like.

`rabbit` and `spider` are absent because neither emits: `rabbit` exhausts the
500,000-node `assign_budget` after 56 candidates, and `spider` produced no
verdict in 60 minutes. See "Layer order" above.

⚠ A pattern appearing here means it was CERTIFIED by `layer_certify` — **no
contradictions were found by propagation and the module verified a satisfying
M/V labelling**, but not an unconditional flat-foldability certificate (see
the caveat under "Coverage" and "Certification bar" above).

Regenerate (from `mcp_harness/`, ~16 min, dominated by `dog` at 578 s and
`guinea_pig` at 295 s):

```
PYTHONPATH=.:tests ../.venv/bin/python \
  ../docs/superpowers/evidence/2026-09-20-box-pleat/cp-gallery/render_cp_gallery.py OUTDIR
PYTHONPATH=.:tests ../.venv/bin/python \
  ../docs/superpowers/evidence/2026-09-20-box-pleat/cp-gallery/build_page.py OUTDIR
```

## Failures, by stage

All 6 `contours`-stage failures are `ContourFail("collision", ...)` at a point on the paper edge — exactly the level-shifter site Lang §14.1 describes (two mismatched elevation families meeting head-on at the boundary), and each is the B macro seam this v1 compiler defers by design (spec §8, §9):

- **cat** — collision at (2, 92): level-shifter site (Lang §14.1).
- **elephant** — collision at (4, 0): level-shifter site (Lang §14.1).
- **bat** — collision at (34, 0): level-shifter site (Lang §14.1).
- **dolphin** — collision at (10, 0): level-shifter site (Lang §14.1).
- **scorpion** — collision at (0, 96), at N=70 (the sweep's first valid layout under the `max_N=76`/`pack_budget=200_000` override): level-shifter site (Lang §14.1).
- **ant** — collision at (0, 58): level-shifter site (Lang §14.1).

The one `tree`-stage failure is structural, not a level-shifter site:

- **crab** — refused at stage `tree` with `AsymmetricPair`, declared pair (4, 6) at radii 13 vs 9 (hub 1 both): a mirrored half-square layout cannot honour an asymmetric declared pair — the two leaves of a declared symmetric pair must have identical radius and hub after contraction (spec §5.1/§11.1), and crab's claw pair does not.

**2026-09-23 addition — one `assign`-stage failure, new since pleat reassignment landed:**

- **rabbit** — refused at stage `assign` with `AssignFail('budget', 500000)`: `assign_budget` (500,000 local-CSP search nodes) exhausted at 56 layers-stage candidates, before `layer_budget` could bind. Not a level-shifter site and not (yet) a proof of unfoldability — a search-budget refusal, not an emptiness result. See "Layer order" above.

## Table

This table's `layer_order` column is **not** `compile_tree`'s verdict. It is
`probe_box_pleat.py`'s own, independent `layer_order.layer_order(ff)` call
(`mcp_harness/probe_box_pleat.py:184-198`) against the fold `compile_tree`
already emitted, carrying no `verdict`/CERTIFIED-REFUTED-UNDECIDED reading of
its own. That independence is exactly why the column is kept rather than
dropped: it is the only oracle reading of these emitted bases anywhere in
this repository that was computed by a second, independent call rather than
read off `Result.verdict`. **Follow-up, deliberately left out of this plan's
scope:** adding a `verdict` column to `probe_box_pleat.py` (calling
`layer_certify.decide` the same way `layers.certify` does) and regenerating
this table would make it match its own headline above; nobody has done that
yet.

| subject | leaves | rivers | unit | N_lb | N | scale_bp | scale_tm | ratio | hull_coverage | tip_hull_coverage | tm_tip_hull_coverage | flap_width_units | stage_reached | layers_tried | maekawa_defects | lint_class | flat_fold_ok | layer_order | pack_ms | failure | tm_error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dog | 6 | 1 | 0.044444 | 46 | 74 | 0.013514 | 0.016131 | 0.838 | 1.0 | 1.0 |  | 1 | emit | 10 | 0 | PASS | True | consistent | 21083.8 |  |  |
| cat | 6 | 1 | 0.08 | 34 | 46 | 0.021739 | 0.019971 | 1.089 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 2272.8 | ContourFail: ContourFail(kind='collision', site=((2, 92), Fraction(0, 1), Fraction(1, 1))) |  |
| horse | 7 | 1 | 0.05 | 32 | 46 | 0.021739 | 0.022057 | 0.986 | 1.0 | 1.0 |  | 1 | emit | 5 | 0 | PASS | True | consistent | 2676.2 |  |  |
| rabbit | 6 | 1 | 0.05 | 34 | 54 | 0.018519 | 0.022751 | 0.814 |  | 1.0 |  | 1 | assign | 56 |  |  |  |  | 5284.7 | AssignFail: AssignFail(kind='budget', site=500000) (measured 2026-09-23 at layer_budget=100, 1be01b0; not independently re-measured at the shipped default layer_budget=200 -- 56 << 100 << 200 means the node budget, not the layer budget, binds either way -- see spec 2026-09-22-pleat-reassignment-design.md sec 11) |  |
| guinea_pig | 5 | 1 | 0.033333 | 54 | 64 | 0.015625 | 0.014799 | 1.056 | 1.0 | 1.0 |  | 1 | emit | 20 | 0 | PASS | True | consistent | 4005.9 |  |  |
| elephant | 6 | 1 | 0.033333 | 44 | 56 | 0.017857 | 0.017213 | 1.037 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 3681.3 | ContourFail: ContourFail(kind='collision', site=((4, 0), Fraction(0, 1), Fraction(1, 1))) |  |
| lizard | 6 | 1 | 0.066667 | 34 | 34 | 0.029412 | 0.022673 | 1.297 | 1.0 | 1.0 |  | 1 | emit | 9 | 0 | PASS | True | consistent | 23.1 |  |  |
| frog | 5 | 1 | 0.057143 | 36 | 38 | 0.026316 | 0.022306 | 1.18 | 1.0 | 1.0 |  | 1 | emit | 22 | 0 | PASS | True | consistent | 154.4 |  |  |
| bird | 6 | 0 | 0.044444 | 36 | 54 | 0.018519 | 0.021727 | 0.852 | 1.0 | 0.7407407407407407 |  | 1 | emit | 1 | 0 | PASS | True | consistent | 156.4 |  |  |
| bat | 6 | 1 | 0.036364 | 28 | 40 | 0.025 | 0.029426 | 0.85 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 1677.2 | ContourFail: ContourFail(kind='collision', site=((34, 0), Fraction(0, 1), Fraction(1, 1))) |  |
| dolphin | 5 | 1 | 0.036364 | 36 | 48 | 0.020833 | 0.027998 | 0.744 |  | 0.5 |  | 1 | contours | 0 |  |  |  |  | 2339.4 | ContourFail: ContourFail(kind='collision', site=((10, 0), Fraction(0, 1), Fraction(1, 1))) |  |
| starfish | 5 | 0 | 0.4 | 4 | 4 | 0.25 | 0.292893 | 0.854 | 1.0 | 0.75 |  | 1 | emit | 1 | 0 | PASS | True | consistent | 3.4 |  |  |
| octopus | 9 | 0 | 0.026667 | 52 | 74 | 0.013514 | 0.014854 | 0.91 | 1.0 | 1.0 |  | 1 | emit | 2 | 0 | PASS | True | consistent | 1456.0 |  |  |
| crab |  |  |  |  |  |  |  |  |  |  |  |  | tree | 0 |  |  |  |  | 0.0 | AsymmetricPair: pair (4, 6): r 13 vs 9, hub 1 vs 1 | no contracted tree (stage=tree failure) |
| spider | 9 | 0 | 0.05 | 54 | 90 | 0.011111 | 0.015186 | 0.732 | 1.0 | 1.0 |  | 1 | emit |  | 0 | PASS | True | contradiction (2026-09-22, pre-pleat-reassignment; 2026-09-23 re-measurement at layer_budget=25 did not resolve in 60 min and was stopped -- no post-feature verdict) | 402.4 |  |  |
| scorpion | 11 | 1 | 0.066667 | 48 | 70 | 0.014286 | 0.01663 | 0.859 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 109873.3 | ContourFail: ContourFail(kind='collision', site=((0, 96), Fraction(0, 1), Fraction(1, 1))) |  |
| ant | 8 | 0 | 0.04 | 46 | 56 | 0.017857 | 0.015675 | 1.139 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 3196.2 | ContourFail: ContourFail(kind='collision', site=((0, 58), Fraction(0, 1), Fraction(1, 1))) |  |

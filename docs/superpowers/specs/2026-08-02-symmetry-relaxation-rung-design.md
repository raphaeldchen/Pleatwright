# Minimal symmetry relaxation — a rescue rung that spends the least symmetry it can

**Date:** 2026-08-02
**Status:** ⛔ **WITHDRAWN, same day, before implementation.** Read §0 first.
**Author:** brainstorming session (Claude + raphaeldchen)

---

## 0. WITHDRAWN — the evidence was confounded

**Do not implement this. Its central premise is backwards.**

Everything below rests on "relaxing the bilateral pairing condition packs 13/24
cohort rows". That measurement is real. Its *interpretation* is not, because
**the cohort's declared pairs are not bilateral pairs at all.**

Verified 2026-08-02, `feasibility/corpus_wide.jsonl`:

- **0 of 7502 declared pairs across 2600 rows are equal-length. Zero.**
- Every pair in all six residual rows is mismatched, several by ~2×
  (row 353: `0.211768` vs `0.414412`; row 830: `0.540978` vs `0.279437`).
- Every pair in all four body-plan templates is **exactly** equal
  (0.4/0.4, 0.35/0.35, 0.2/0.2, 0.3/0.3).

Mechanism, at source: `feasibility/tree_generator.py:_pair_leaves` calls
`rng.shuffle(leaves)` and pairs adjacent shuffled leaves, while lengths are
drawn independently. It labels random leaf couplings "symmetry pairs".

That makes the constraint a geometric contradiction. `tmConditionNodesPaired`
forces two leaves to mirror positions about the axis, which implies equal
distance from it — while the tree demands unequal flap lengths. The packer
cannot satisfy both, so it fails. **The cohort/template split I measured tracks
pair-length equality, not the pairing condition.**

### The controlled experiment that settles it

8-leaf stars, **identical length multiset in every cell**, only the pairing
*assignment* differing, n=40:

| cell | packs | vs unpaired |
|---|---|---|
| **equal-paired** (genuine bilateral) | **17/40 — 42.5%** | **+12.5 points** |
| arbitrary-paired (corpus-style) | **0/40 — 0.0%** | −30.0 points |
| unpaired | 12/40 — 30.0% | — |

**Pairing genuine bilateral pairs HELPS packing.** It is not a constraint to
relax; it is a constraint that earns its place. Only *mismatched* pairs are
catastrophic, and they are catastrophic absolutely — 0/40.

### What is actually true, and what to build instead

1. **A declared bilateral pair whose two flap lengths differ is very likely
   unpackable.** That is a cheap, decidable, pre-execution property — exactly
   the class `tree_contract.py` was built for (its cited prior art, symbolic
   pre-execution contract checking in EDA agent loops, took multi-step pass
   rate 30% → 84% by rejecting malformed calls before the backend saw them).
2. **This is a production risk, not only a synthetic-corpus artifact.**
   `mesh_to_tree.detect_symmetry` *prefers* equal-length candidates — the hub
   bonus decays with the length ratio (`mesh_to_tree.py:301-304`) — but it
   never **equalizes** them, and a 2:1 pair still scores half the bonus and can
   win. A real extracted tree can therefore carry a mismatched pair straight
   into a doomed compile.
3. **`corpus_wide.jsonl` cannot be used to evaluate anything symmetry-related.**
   Its `pairs` field is noise. Compile-rescue numbers that never manipulated
   pairing (S1–S5's cohort rates) are unaffected; any *symmetry* conclusion
   drawn from it is void.

**The replacement slice:** detect mismatched declared pairs and repair them
(equalize to the pair mean, disclosed as a proportion change) or reject them at
contract time. Symmetry-preserving, cheap, and it targets a defect measured at
0/40 packability. That needs its own spec.

### Kept, because it is still good

§2.2's congruence instrument and its control (9/9 paired template pairs at
folded tip gap `0.000000`; 0/40 unpaired) is valid and reusable — it measures
the product rather than the constraint. §2.4's two falsifications (boundary
placement, book symmetry) stand on independent evidence. §2.5's warning about
the flat-CP crease-structure proxy stands.

**Everything from §1 onward is preserved as the record of a wrong turn. It is
not a plan.**

---

## 1. The one-paragraph version *(as written before the confound was found)*

The bilateral pairing condition is what blocks the cohort residual four rescue
slices could not move. Relaxing it entirely packs **13 of 24** cohort rows,
including **5 of the 6** residual — but it produces **visibly lopsided bases**:
paired flaps that fold to *exactly* the same point today land **12% to 78% of
the model's own length apart** without it. So "relax and serve" buys packs with
a product defect. This slice proposes relaxing the **minimum number of pairs**
instead, and gating the serve on **measured folded congruence** rather than on
the presence of a constraint. The instrument for that gate was built and
validated in the course of this measurement.

---

## 2. What was measured (2026-08-02, all reproducible)

Everything here is committed evidence, not recollection. Reproduce from the
MAIN checkout, or from a worktree after `./build.sh`.

### 2.1 The buy

`mcp_harness/probe_symmetry_relax.py` → `fixtures/symmetry_relax_evidence.json`.
Full committed 24-row cohort, paired vs unpaired, each compile isolated:

| arm | packs |
|---|---|
| paired | **0/24** — expected; the cohort *is* the attempt-0 failures |
| unpaired | **13/24** |

- **Rescued only by relaxing:** `[90, 97, 316, 353, 385, 500, 812, 830, 865, 1012, 2029, 2174, 2425]`
- **Lost if always relaxed:** `[]` — nothing in the cohort packs paired-only.
- Five of the thirteen are the S5b residual `[90, 353, 500, 830, 865]`, so the
  ladder would go **18/24 → 23/24**. `2099` packs under no arm at all.

**It must be a rung, not a default.** All four body-plan templates pack **only**
paired and fail unpaired (`fixtures/symmetry_axis_evidence.json`). Pairing
rescues well-conditioned trees and over-constrains high-k ones — the cohort
rows are 8-leaf, three of them pure 8-point stars.

### 2.2 The cost, measured on what a person actually perceives

Leaf-position mirroring in the flat CP is a proxy. The thing a folder sees is
where the flaps end up **in the folded base**. Measured with `flat_fold()`
(pure Python, matches the simulator to 7e-6, honest domain = raw hull folds),
as the distance between bilaterally paired flap tips in the folded state:

| | folded tip gap |
|---|---|
| **Paired (control): 9 pairs across 4 templates** | **0.000000 — all nine** |
| Unpaired: 40 pairs across the 13 packing rows | 0/40 congruent; min 0.0001, mean 0.0952, max 0.4968 |

Absolute gaps are not readable on their own, so normalise by each base's own
axial span:

| row | worst gap | % of span | row | worst gap | % of span |
|---|---|---|---|---|---|
| 90 | 0.0690 | **12.2%** | 865 | 0.1225 | 25.8% |
| 1012 | 0.0701 | 14.0% | 316 | 0.2122 | 31.2% |
| 812 | 0.0749 | 15.9% | 353 | 0.1452 | 35.4% |
| 830 | 0.1208 | 18.6% | 2174 | 0.2092 | 46.6% |
| 385 | 0.1219 | 19.8% | 2029 | 0.2359 | 51.5% |
| 500 | 0.0959 | 20.7% | 97 | 0.2388 | 61.8% |
| | | | 2425 | 0.4968 | **77.7%** |

**Nothing lands under 12%.** The best available row still gives one limb 12%
longer than its partner. A blanket "relax and serve" rung ships that.

### 2.3 The finding that makes a smarter rung possible

Within a single unpaired compile, **per-pair congruence varies enormously**:
row 812 reads `0.0001, 0.0673, 0.0749`; row 865 reads `0.0010, 0.1225`; row
1012 reads `0.0701, 0.0098`. The packer is perfectly capable of keeping *some*
pairs congruent while breaking others — it simply has no reason to prefer
that when no constraint asks.

That is the whole basis for §4: relax the fewest pairs that unblock the pack,
and keep the rest enforced.

### 2.4 Two claims retired by measurement

- **Boundary placement (the previous slice).** The unconstrained solver already
  parks 83% of leaves exactly on the paper boundary (k=4 puts 4/4 at corners).
  Its premise — "force leaves to the boundary because they are not there" — is
  false. Shelved.
- **Book symmetry.** `fixtures/symmetry_axis_evidence.json`: `book0` packs
  **0/10**, `book90` 2/10, against `diag45`'s 4/10, and book also *lowers* mean
  hull coverage (0.550 vs 0.675). The hard-coded 45° axis is defensible, not an
  oversight. **Do not re-propose axis selection without new evidence.**

### 2.5 One instrument correction, recorded so it is not re-derived

An earlier proxy — comparing the multiset of creases incident to each paired
flap tip — reported 40/40 mismatches. **It is not trustworthy.** Its control on
properly-paired templates reports mismatches on humanoid (2/2) and insect (3/3)
despite mirror residuals of 2e-09. Diagnosed on humanoid pair (3,4): residual
1.9e-09, crease *assignments* identical (`B,B,V` both sides), but the first
interior crease length differs 0.3116 vs 0.1902.

So `tmConditionNodesPaired` constrains **leaf node positions only** — the
molecule filling between them is not mirrored. That is a true statement about
the flat CP and a **misleading** one about the product: those same bases fold
to tip gap 0.000000. **Measure folded congruence, never flat-CP crease
structure.**

---

## 3. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| **Feasibility restoration / ℓ₁ relaxation** ([arXiv:2406.13454](https://arxiv.org/pdf/2406.13454)) | Standard response to an infeasible constrained solve: minimise total infeasibility, then restore | **Adopted in shape** — §4 relaxes the smallest infeasibility rather than the whole constraint |
| **Geometric constraint repair / two-phase optimization** | Given an infeasible solution, convert it to a feasible one minimising Euclidean distance to the original | **Adopted as the §7 escalation**, not the primary design — see R3 for why repair is likely to fail here |
| Lang, TreeMaker 4.0 manual §2.2 | Diagonal and book symmetry give very different patterns; either can win; "with TreeMaker, you can easily check them both" | **Checked, and rejected** — §2.4. Our sample favours diagonal decisively |
| Our own stub stage (S5) | The precedent for a rung that trades an acceptance axis for a pack: it *invents anatomy*, is excluded from `PRESERVING_STAGES`, sits in `INVENTS_ANATOMY`, and discloses via `STUB_MARKER` | **Adopted wholesale** as the classification and disclosure model. A symmetry-relaxing rung is the same kind of act on a different axis |
| Symmetry breaking in constraint programming | Symmetry constraints are normally added to *shrink* a search space | **Noted as an inversion.** Ours is the reverse — a symmetry constraint that *excludes* the feasible region. Worth stating plainly because the CP literature's intuition points the wrong way here |
| "Is Self-Repair a Silver Bullet?" (ICLR'24, arXiv:2306.09896) | Breadth over depth at fixed budget | **Adopted** — §4's subset search is bounded and shallow, not a deep ladder |
| S8 outcome (project memory) | ">8 leaves is a PACKER problem, not a gate problem" | **Adopted as the targeting argument** — this slice acts on the packer, for exactly that population |

**No competitor does this.** TreeMaker exposes symmetry as a manual on/off
condition; automating *which pairs to relax, and how little* is the novel part.

---

## 4. Design

### 4.1 The rule

> Relax the **fewest** bilateral pairs that let the tree pack, then **serve only
> if the surviving pairs are measurably congruent in the folded base**. Never
> relax as a default; never serve on the absence of a constraint alone.

Two halves, and the second is the one that makes this shippable. A rung that
only relaxed would ship the §2.2 table.

### 4.2 The congruence instrument (`mcp_harness/fold_congruence.py`, new)

Pure Python, no engine:

```python
def paired_tip_gaps(fold, leaf_locs, pairs) -> dict
```

For each pair `(a, b)`: locate each leaf tip's vertex in the exported FOLD by
coordinate match against `leaf_node_locations()`, fold with
`flat_fold.flat_fold`, take each tip's image via
`folded_vertices[face][slot]`, and return the distance between them — plus the
base's own axial span, so the caller can normalise.

Returns `None` per pair, never a fabricated number, when a tip is not
resolvable to a face or `flat_fold` is outside its raw-hull domain.

**Validated by its control**: 9/9 pairs at exactly `0.000000` on the four
paired templates, against 0/40 congruent unpaired. A metric that cannot
separate those two populations is not worth having; this one separates them
completely.

### 4.3 The subset search (`mcp_harness/symmetry_relax.py`, new)

```python
def relaxation_plan(pairs, *, max_relaxed=None) -> list[frozenset]
```

Emits candidate subsets of pairs to relax, **smallest first**:

1. `∅` — the paired attempt, which the ladder already made. Never re-run.
2. every single pair, ordered by longest flap first (ties by node id — node
   list order must never decide, per `body-plan-templates-and-node-order`).
3. every pair of pairs, same ordering.
4. …up to `max_relaxed`, defaulting to `len(pairs) - 1`.

**The full-relaxation subset is deliberately NOT the last resort — it is
excluded entirely.** §2.2 measured what it produces. If no proper subset packs,
the rung declines and the ladder moves on.

Breadth is bounded: for the cohort's 2–4 pairs that is at most 14 subsets, and
the rung stops at the first that packs *and* passes §4.4.

### 4.4 The acceptance gate

A relaxed serve is admissible only if **every surviving pair** has folded tip
gap ≤ `CONGRUENCE_TOL × axial_span`.

`CONGRUENCE_TOL` is **not specified here**, deliberately. §2.2 shows blanket
relaxation produces 12–78%, so any honest tolerance rejects most of it, and
picking the number from that same table would be fitting the threshold to the
data it must judge. **Phase B sets it from the subset search's own
distribution, on a split fixed before the search runs** (§5).

The relaxed pairs themselves are exempt from the gate — they are the price, and
they are disclosed (§4.5).

### 4.5 Classification and disclosure

Following the stub stage exactly, because it is the same kind of act:

| Set | Member? | Why |
|---|---|---|
| `PRESERVING_STAGES` | **No** | It does not preserve what the caller asked for. Lengths survive, but an *enforced output property* is dropped |
| `INVENTS_ANATOMY` | **No** | No flap is created |
| `STAGE_HONESTY` | **1** | Below `order`/`placement`/`boundary` (2), above `jitter` (0). Every requested length and flap survives exactly; a bilateral relationship does not |

**`ASYM_MARKER` must not be reused, and this is now settled rather than
cautioned.** `benchmark_subjects.py:41` defines it as
`"[ide: bilateral pairs were nudged independently"` — it is about the **length**
domain, a jitter fallback that drew per-pair factors independently. This slice
touches the **position** domain and changes no length. Overloading one marker
across both would make two materially different serves indistinguishable in
`fold_str`, and the `asymmetric` scorecard column reads that marker.

So: a new `RELAX_MARKER = "[ide: rescued by relaxing N bilateral pair(s):"`
naming the count and the pair ids, satisfying the three invariants pinned at
`rescue_ladder.py:145-152`. The existing `asymmetric` column keeps its current
meaning untouched; §4.7's `relaxed_pairs` carries the new one.

Disclosure is **not optional and not generic**. The user asked for a bilaterally
symmetric animal and is getting one that is not, by a measured amount. The
serve must carry the measured worst gap as a percentage of span, not a
boolean — `anatomy_oracle.py`'s discipline (inform-only, one synthetic retry,
never a standing imperative) is the model.

### 4.6 Ordering and the six coordinated edits

Ordered **last among rescue rungs, after `stub`**: it is the only stage that
degrades a property of the *output* rather than conditioning the *input*, so
everything cheaper should have been tried.

Adding a stage touches **six** sites, two of which fail silently
(`mesh_to_tree.served_stage` falls through to `STAGE_EXACT`;
`benchmark_subjects`' chain falls through to `"none"`), plus
`server._ALL_LADDER_STAGES`, `mesh_to_tree._STAGE_INTEGRITY` (pinned dict-equal
to `STAGE_HONESTY`), and `feasibility/tree_labeler.PERTURB_ERA_REVISION`
(7 → 8). `mesh_to_tree.py:733-735` states the hazard in its own source: *"a
missing marker here is therefore a silent WRONG SERVE, not a red test."*
Verify the list against the code before implementing; an earlier audit also
flagged `server._annotate_rung`'s dispatch tuple, which I have not confirmed.

### 4.7 Scorecard

Two columns beside the existing `asymmetric`:

- `relaxed_pairs` — `"<n_relaxed>/<n_total>"`, or `null`.
- `worst_tip_gap` — the measured worst surviving-pair gap as a fraction of
  axial span, or `null`. **This is the honesty column**, and it must be
  populated for *every* served row, not only relaxed ones, so the paired
  baseline (0.0000) stays visible beside it.

---

## 5. Phasing, with pre-registered stops

**Phase A — the instrument.** `fold_congruence.py` plus its control test: 9/9
paired template pairs at 0.000000, and a clear separation from the unpaired
population. No engine change.
> **STOP IF** the control does not reproduce. The gate is the slice; an
> instrument that cannot tell congruent from lopsided makes everything
> downstream unmeasurable.

**Phase B — the subset search, offline.** Run `relaxation_plan` over the 13
rows that pack under full relaxation, plus the 11 that do not, recording for
each subset: packs?, worst surviving gap, scale, `hull_coverage`. Set
`CONGRUENCE_TOL` from this distribution on a **split fixed before the run**:
the 6 residual rows are held out; the tolerance is chosen on the other 18.
> **STOP IF** no proper subset packs any row that full relaxation packs. That
> would mean relaxation is all-or-nothing, and §2.2 already priced
> all-or-nothing as unshippable.
> **STOP IF** fewer than 2 held-out residual rows survive the gate. One row is
> not worth six coordinated edit sites and a new acceptance axis.

**Phase C — the rung.** Marker, classification, the six edits, worker wiring,
disclosure.

**Phase D — measurement and re-bless.** Scorecard columns, cohort re-measure
from the MAIN checkout, one coordinated re-bless.

---

## 6. Testing

| Test | Asserts |
|---|---|
| `test_fold_congruence_control` | 9/9 paired template pairs at gap < 1e-6; the metric separates them from a known-unpaired base |
| `test_fold_congruence_none_not_zero` | returns `None`, never `0.0`, when a tip is unresolvable or `flat_fold` is out of domain |
| `test_relaxation_plan_order` | subsets emitted smallest-first; `∅` never emitted; the full set never emitted; deterministic under input reordering |
| `test_relaxation_plan_bounds` | ≤ `2^n - 2` subsets; respects `max_relaxed` |
| `test_gate_rejects_lopsided` | a base with a surviving pair over tolerance is refused, using a recorded fixture from §2.2's table |
| `test_attempt0_unchanged` | **byte-identical** attempt-0 output for all four templates |
| `test_stage_chains_agree` | both marker→stage derivations return the new stage; neither falls through |
| `test_stage_sets` | ∉ `PRESERVING_STAGES`, ∉ `INVENTS_ANATOMY`, honesty 1, `_STAGE_INTEGRITY` dict-equal to `STAGE_HONESTY` |
| `test_marker_invariants` | the three invariants at `rescue_ladder.py:145-152`; `ASYM_MARKER` not reused |
| `test_disclosure_carries_a_number` | the served note states the measured gap, not a boolean |
| Regression | full suite from the **MAIN** checkout |

Per memory: `--timeout=420`; bare `make test` never terminates on macOS; check
host CPU for orphans before timing; all builds and blesses from the MAIN
checkout.

---

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **The gate rejects everything** and the rung rescues nothing | Phase B is exactly this question, on a held-out split, with a pre-registered stop at <2 rows |
| R2 | **Tolerance fitted to the data it judges** | Split fixed before the search; residual held out; the number comes from the 18 non-residual rows |
| R3 | **The §3 "repair" escalation does not work.** Restoring mirror symmetry post-hoc means moving nodes by the mirror residual, measured at ~1.0 on a unit square — three orders larger than the ~1e-5 `ProjectActivePaths` currently applies. It will almost certainly destroy the polygon network | Kept as a §7 escalation only, explicitly *not* the design. Cheap to falsify if anyone wants it: add mirror rows to the existing projection and see |
| R4 | **A silent stage-registry miss** serves a relaxed base scored as attempt-0 exact | §4.6; `test_stage_chains_agree` |
| R5 | **`flat_fold` domain** — raw hull folds only, so the gate cannot judge squared or shaped output | Gate returns `None` and the rung declines. Never serve on an unmeasured gate |
| R6 | **Disclosure is ignored by the agent** and the user is told nothing | `anatomy_oracle.py`'s inform-only discipline; the disclosure carries a number, which is harder to drop than an adjective |
| R7 | **2099 never packs** under any arm, so the ceiling is 5/6 of the residual and the gate will cut that further | Stated in the metric, not discovered later |
| R8 | Subset search cost — 2ⁿ compiles per rung | Bounded by `max_relaxed` and by first-success exit; cohort pairs are 2–4, so ≤14 subsets |

---

## 8. Out of scope

- Boundary placement / corner forcing (shelved, §2.4). Its §4.2 mirror-class
  corner partition remains correct and reusable if coverage is ever attacked.
- Symmetry **axis** selection (falsified, §2.4).
- The visual-feedback loop (its own spec).
- Changing what `detect_symmetry` infers. This slice relaxes enforcement of
  the pairs it is given; it never re-decides which pairs exist.
- Scale-ranking the ladder — a separate, possibly cheaper lever noted in
  project memory ("the ladder never ranks by scale; dog-raw discards +12.7% on
  the path it already runs"). Worth its own slice and untouched here.

---

## 9. Open questions

1. **Is a 12%-lopsided quadruped better or worse than no quadruped?** This is a
   product judgement, not a measurement, and it sets `CONGRUENCE_TOL`'s upper
   bound. Phase B can supply the distribution; it cannot answer this.
2. **Should the agent choose which pairs to relax?** Proposed: no — the parent
   plan rejected interactive topology tools because no measured failure needed
   an LLM decision. The subset search is deterministic.
3. **Does `hull_coverage` move under relaxation?** The unpaired packs read
   0.632–1.000 (mean 0.901) against paired templates' 0.559–0.789. If
   relaxation reliably raises coverage too, that changes the trade — and it is
   free to record in Phase B.
4. ~~What does `ASYM_MARKER` mean today?~~ **Answered** — `benchmark_subjects.py:41`,
   it is the length-domain jitter fallback. Do not reuse it (§4.5).
5. **Does relaxing interact with the stub stage?** Both are last-resort rungs
   that trade an acceptance axis, and this slice orders itself after `stub`.
   If a tree needs both, the serve carries two disclosures on two different
   axes — untested, and worth one Phase B row.

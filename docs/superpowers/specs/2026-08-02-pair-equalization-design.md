# Pair equalization — reconcile a declared bilateral pair with its own measurements

**Date:** 2026-08-02
**Status:** design, awaiting review
**Author:** brainstorming session (Claude + raphaeldchen)

---

## 1. The defect

When `detect_symmetry` declares two leaves a bilateral pair, it asserts *these
two flaps are mirror images of each other*. Mirror images have equal length —
that is what mirroring means. But each flap's length is measured independently
off a voxelized mesh, so the two numbers disagree, and **both are passed
through to the engine unchanged**.

`apply_symmetry` then applies `tmConditionNodesPaired`, which constrains the
two leaves to mirror *positions* — hence equal distance from the axis — while
the tree simultaneously says their flaps are different lengths. The two demands
cannot both hold. The packer resolves it as best it can, and the model folds
lopsided.

**This is a user-visible product defect**, reported from a live run and then
reproduced: the shipped dog's pair (7,8) is **13.60%** mismatched, and its two
flap tips land **3.8% of the model's own length** apart in the folded base.

---

## 2. What was measured (2026-08-02, reproducible)

`mcp_harness/probe_pair_gap.py` → `fixtures/pair_gap_evidence.json`. Every pair
the extractor emits, across all five committed meshes × 3 voxel resolutions ×
4 prune fractions. Gap is `|La − Lb| / max(La, Lb)`.

**115 declared pairs. Zero are equal.**

| min | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|
| 0.13% | 3.32% | **6.50%** | 19.45% | 29.78% | 42.34% |

| threshold | pairs over it |
|---|---|
| > 1% | 104/115 |
| > 5% | 65/115 |
| > 10% | 41/115 |
| > 20% | 27/115 |
| > 30% | 11/115 |

### 2.1 The defect is universal, and it enters at extraction

Surveying `tests/cases.py`: **4 of 23 declared pairs are mismatched, and all
four are the dog** — the only mesh-derived case. Every hand-authored tree
(`star-4-sym`, `star-6-sym`, `hshape`, all four templates, `insect-knife-024`)
is **exactly** equal, because a human writing "two front legs" types the same
number twice. Only *measured* trees disagree with themselves. That is the
signature of extraction noise, not of anatomy.

### 2.2 The negative result that shapes the design

**There is no threshold in the data.** The distribution is continuous from
0.13% to 42.34% with no bimodality — nothing separates "measurement noise" from
"these are not really a pair". Any cutoff must be anchored to something outside
this measurement. §4.2 anchors it to an existing project tolerance rather than
fitting it to this table.

### 2.3 The fix works, and its cost is measured

Equalizing the dog's two declared pairs to their means:

| | pair (7,8) | pair (1,3) | scale | `hull_coverage` |
|---|---|---|---|---|
| as shipped | 3.8% of span apart | 0.6% apart | 0.6585 | 0.657 |
| equalized | **0.0%** | **0.0%** | 0.6550 | 0.657 |
| template control (equal by construction) | 0.0% | 0.0% | 0.6680 | 0.681 |

Exact folded congruence, for **0.5% of scale** and no coverage change.

---

## 3. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| **Data reconciliation** ([Grokipedia overview](https://grokipedia.com/page/Data_validation_and_reconciliation); [general framework, linear constraints](https://www.sciencedirect.com/science/article/abs/pii/S0098135414003330)) | The established name for exactly this problem: adjust observations that conflict with a known constraint by finding the **orthogonal projection onto the constraint space**, minimising least-squares error | **Adopted wholesale.** It names the operation and supplies §4.1's estimator |
| **Gross error detection** (same literature) | Reconciliation assumes small random error; measurements too far off are *gross errors* to be **flagged, not reconciled** | **Adopted** — this is §4.2's second branch, and it is why the design has two branches rather than one |
| Least-squares projection onto `a = b` | Minimising `(x−a)² + (x−b)²` gives `x = (a+b)/2` | **Adopted** — the mean is not a taste choice, it is the minimum-total-displacement point |
| `tree_contract.py` and its cited precedent (symbolic pre-execution contract checking in EDA agent loops, [arXiv:2604.18834](https://arxiv.org/abs/2604.18834): 30% → 84% multi-step pass rate) | Reject or repair malformed calls *before* the expensive backend sees them | **Adopted** as the placement argument — this is a pre-execution property |
| CADCodeVerify (ICLR'25), already cited at `anatomy_oracle.py:14-16` | Derive checks at draft time, answer them against the produced artifact | **Adopted** for §4.4's verification |
| `server.py:566` `_PERTURB_DELTA = 0.10` | The ladder already moves any edge length ±10% in its jitter rung | **Adopted as the anchor** for §4.2's cutoff |
| Relaxing the pairing condition instead (withdrawn spec, `0c444cd`) | Measured: pairing *genuine* pairs helps packing (+12.5 points); only mismatched pairs are catastrophic (0/40) | **Rejected** — treat the cause, not the symptom |

**Nobody does this in origami tooling.** TreeMaker takes symmetry pairs as a
manual assertion by a human who supplies consistent lengths by hand. The
problem only exists because we *infer* pairs from a noisy measurement, so the
reconciliation step is ours to add.

---

## 4. Design

### 4.1 The operation

For each declared pair `(a, b)` with lengths `La`, `Lb`:

```python
def reconcile_pair(La, Lb) -> float:
    return (La + Lb) / 2.0
```

The mean, because it is the least-squares projection onto the constraint
`La = Lb` — the point satisfying the constraint that moves the two measurements
least in total. "Longer" would preserve reach and "shorter" would ease packing,
but both are unjustified displacements away from what was measured.

### 4.2 The cutoff, and what it is anchored to

**Reconcile when `gap ≤ MAX_PAIR_GAP = 0.20`; flag as a suspect pair above it.**

The anchor, not the data: equalizing to the mean moves **each** member by
`gap / 2`. A 20% gap therefore moves each flap by at most **10%** — exactly the
budget `server.py:566 _PERTURB_DELTA` already spends in the jitter rung. So
reconciliation never displaces a length further than the ladder is already
permitted to, and unlike jitter it moves lengths *toward* the tree's own
declared invariant instead of away from it.

On the measured corpus that admits **88/115 pairs** and flags 27.

Above the cutoff the two flaps are too different to be mirror images, and the
right response is **not** to average them — it is to doubt the pairing. §4.3.

### 4.3 What "flagged" means

A gross error is a claim about the *detector*, not the tree. Two options, and
the spec picks the conservative one:

- **Proposed: drop the pairing, keep both lengths, and say so.** The tree
  serves as two independent flaps at their measured lengths. Nothing is
  invented, nothing is averaged, and the base is honestly asymmetric because
  the anatomy it was measured from is.
- Rejected: reconcile anyway. A 42% average is not a measurement of anything.
- Rejected: refuse to compile. A suspect pair is a reason to doubt one
  relationship, not to fail the whole model.

### 4.4 Where it lives

**Proposed: inside `detect_symmetry`, at the point the pair is created.**

A pair is *born* consistent, so no downstream consumer can ever see the
contradiction — and every existing consumer (the engine, the contract check,
the scorecard, the gate) is fixed by one change. The alternative, a repair pass
in `tree_contract.py`, leaves the inconsistent tree existing and reachable, and
`tree_contract` today reports rather than mutates, which is a boundary worth
keeping.

Emit alongside each pair the evidence for what happened: the original two
lengths and the gap. Without that, an equalized tree is
byte-indistinguishable from one that was measured consistent — the same
argument `MeshTreeResult.stub_flaps` carries in its own comment.

### 4.5 Disclosure

Reconciliation changes measured lengths, so it is on the proportion axis and
must be visible. But it is **not** a jitter-class change and must not reuse
that vocabulary: jitter moves lengths *away* from the request to buy a pack;
this moves them *toward* the tree's own assertion to remove a contradiction.

- A new `MeshTreeResult` field carrying `[(pair, La, Lb, gap, reconciled_to)]`.
- `mesh_report` states it in the anatomy block, with the number.
- **`NUDGE_MARKER` / `ASYM_MARKER` are not reused.** `ASYM_MARKER` is already
  the length-domain jitter fallback (`benchmark_subjects.py:41`).

### 4.6 Scorecard

One column: `pair_gap_max` — the worst declared-pair gap **before**
reconciliation, or `null` when a subject has no pairs. It measures the
extractor's consistency, which nothing currently reports, and it stays
meaningful after this slice ships because it is a pre-reconciliation number.

---

## 5. Phasing

**Phase A — reconcile, and measure the blast radius.** `reconcile_pair` in
`detect_symmetry`, the evidence field, the disclosure. Re-run the scorecard.
> **STOP IF** any subject's `served_fidelity`, `rescue_stage` or `lint_class`
> regresses. The dog's measured cost was 0.5% of scale and no coverage change;
> a larger effect anywhere means the change is doing something unmodelled.

**Phase B — the gross-error branch.** ⛔ **REVISED BY IMPLEMENTATION, 2026-08-03.**

The cutoff was implemented, tested, and then **not wired in**. Enabling it
dropped one of the humanoid's two pairs and failed
`test_auto_selection_confirms_each_body_plan` — and that test is right: a
humanoid **has** two arms. The extractor measured them 26.86% apart, so the
*pairing* was correct and the *measurement* was noisy, which is precisely the
case reconciliation exists to fix.

**The lesson: a length gap alone cannot separate "noisy measurement of a real
pair" from "two limbs wrongly paired."** Deciding that needs the detector's own
geometric confidence — mirror distance and the hub bonus at
`mesh_to_tree.py:301-304` — which is independent of length. §4.3's design was
therefore wrong to key the decision on gap.

`reconcile_pairs` defaults to `max_gap=None` (reconcile everything).
`MAX_PAIR_GAP` and its tests remain so the option stays measured rather than
forgotten, but gross-error detection is deferred to a slice that can use
geometric confidence.
> **Original stopping rule, retained for that future slice:** STOP IF dropping
> a suspect pairing makes a currently-serving subject fail to pack, or loses a
> pair a body plan genuinely has. Better a slightly asymmetric model than a
> wrong one.

**Phase C — verification.** Fold each served base and assert paired flap tips
are congruent, using the instrument built for the withdrawn spec (9/9 template
pairs at exactly `0.000000`). This is the check that proves the fix worked on
the artifact rather than on the tree.

---

## 6. Testing

| Test | Asserts |
|---|---|
| `test_reconcile_is_the_mean` | `reconcile_pair(a, b) == (a+b)/2`; symmetric in its arguments; idempotent |
| `test_pairs_are_born_equal` | after `detect_symmetry`, **every** declared pair has exactly equal lengths, on all five committed meshes across the voxel/prune grid |
| `test_gross_error_drops_the_pairing` | a synthetic 42% pair is not averaged; the pairing is dropped and both original lengths survive |
| `test_cutoff_is_anchored_not_fitted` | `MAX_PAIR_GAP == 2 * server._PERTURB_DELTA`, pinned with the reason in a comment so the anchor cannot silently drift from the thing it is anchored to |
| `test_hand_authored_trees_unchanged` | all four templates and the stars are **byte-identical** through the new path — they are already equal, so reconciliation must be a no-op |
| `test_dog_folds_congruent` | the dog's paired flap tips fold to gap < 1e-6 (was 3.8% of span) |
| `test_disclosure_carries_numbers` | the report states both original lengths and the gap, not a boolean |
| `test_scorecard_pair_gap_max` | column present; `null` for a subject with no pairs; reports the **pre**-reconciliation value |
| Regression | full suite from the **MAIN** checkout, `--timeout=420` |

---

## 7. Risks

| # | Risk | Mitigation |
|---|---|---|
| R1 | **Reconciliation breaks a currently-serving subject.** Changing lengths changes packing | Phase A stopping rule. Measured on the dog: scale −0.5%, coverage unchanged, still packs |
| R2 | **The 20% cutoff is wrong.** It is anchored, not measured, because §2.2 showed the data has no threshold to find | Stated plainly as an anchor. `test_cutoff_is_anchored_not_fitted` pins it to `_PERTURB_DELTA` so the two move together |
| R3 | **It hides a real extractor bug.** Reconciling every pair could mask worsening measurement noise | `pair_gap_max` records the **pre**-reconciliation gap on every row, so the noise stays visible after the symptom is fixed |
| R4 | **Legitimate asymmetry gets averaged away.** Some animals really are lopsided (a fiddler crab) | The detector already asserted these two are mirror images; reconciliation only enforces its own claim. A genuinely asymmetric limb pair should not be *declared* a pair, which is the gross-error branch's job |
| R5 | **Interaction with the feasibility gate.** `n_sym_pairs` is a live gate feature (`train_model.FEATURE_ORDER`) trained on a corpus where 4+ pairs never pack — an artifact of that corpus's fabricated pairs | Out of scope here (§8) but **must be tracked**: this slice makes real pairs more consistent while the gate may still penalise having them |
| R6 | **Golden churn.** The dog's geometry changes | One coordinated re-bless in Phase A, in the session that moved it |

---

## 8. Out of scope

- **The feasibility gate's `n_sym_pairs` feature** and the corpus that trained
  it. Measured this session: `corpus_wide.jsonl` has **0 of 7502** equal-length
  pairs and 0/813 packs at 4+ pairs, so the gate learned "more symmetry ⇒
  infeasible" — the opposite of the controlled result (equal-paired 42.5% vs
  unpaired 30.0%). A real defect, a separate slice, and R5 tracks it.
- Improving the extractor so it measures paired limbs consistently in the first
  place. This reconciles the output; fixing the measurement is deeper.
- Corner occupancy / paper coverage (probe run 2026-08-02: pinning all four
  corners breaks every model, pinning one moves coverage ±0.3%; the built-but-
  unwired `free_paper` + `flap_fill` path is the candidate there).
- Relaxing the pairing condition (withdrawn, `0c444cd`).

---

## 9. Open questions

1. **Should reconciliation be silent or announced to the user?** Proposed:
   announced with the number, because it changes measured proportions. But it
   fires on essentially every mesh-derived model, so a per-pair disclosure may
   be noise. A single summary line naming the worst gap may serve better.
2. **Does `detect_symmetry`'s pair *choice* change once lengths are equal?**
   Its hub bonus already decays with the length ratio (`mesh_to_tree.py:301-304`),
   so reconciling after matching is stable — but reconciling could in principle
   make a different pairing look better on a re-run. Phase A should check the
   emitted pair sets are unchanged.
3. **Is 20% the right anchor, or should it be `1 × _PERTURB_DELTA` (10% gap,
   5% per flap)?** The stricter reading admits 74/115 instead of 88/115. This
   is a product judgement about how much silent proportion change is
   acceptable, and the measurement cannot settle it.

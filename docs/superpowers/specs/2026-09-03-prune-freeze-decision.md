# Spec: the prune-freeze decision

**2026-09-03. This is a MEASUREMENT spec, not an implementation spec.** It
exists because the prune freeze looks like a win, the reason it looks like a
win is not the reason anyone gave, and the measurement that would settle it has
never been run.

Nothing here authorises shipping. It authorises one experiment whose bar is
written down before it runs.

## 1. What is settled, and must not be re-litigated

* **The ratchet is real.** `_prune_rounds` (`mesh_to_tree.py:1146`) cuts
  branches below `prune_fraction * longest`, recomputed every round, and
  `longest` is monotone non-decreasing because `_contract_degree2` sums the
  chains pruned twigs leave behind. On the framed octopus at res 96 all nine
  branches survive round 0 at cutoff 12.28, then `longest` jumps 49.12 → 115.46
  and round 1 kills exactly those nine. A branch entering at **12.36 survived**
  while one at **26.78 was deleted**. This reproduces exactly.
* **The search for a better RULE is closed.** Measured on 10 real meshes under
  production conditions, scored against `min(T, 8)`: shipped **4**, freeze
  **1**, leaf-branch normaliser **14** (over-segments `bird-framed` to 11
  against a target of 6, and **non-serves** `octopus-framed` at 0 leaves), and
  elder-rule persistence **1** — a tie with the freeze that beats nothing.
  `stub_flaps` was 0 on all 40 rows. **Do not re-propose the normaliser.**
* **Forest handling is NOT required to decouple the freeze.** Both branches of
  `_keep_or_stitch` return a connected graph, so the frozen cutoff never sees a
  forest. Verified analytically and by building the decoupled flag across
  **144 real cells: 0 disconnected trees, 0 `ExtractionForestError`, 0
  exceptions.** The entanglement is exactly one token — `keep_components()` at
  `:1184`. An earlier handoff said otherwise; that claim was about a third,
  never-shipped arm ("keep components, don't stitch").

## 2. The finding that makes this a decision rather than a task

**The freeze's entire measured benefit is search re-routing, not ratchet
repair.** Holding the winning cell fixed at the shipped arm's own choice:

| | Σ \|leaves − cap\| |
|---|---|
| shipped | **4** |
| **freeze, held at the shipped arm's own winning cell** | **16** — 4× worse |
| freeze + free search | **1** |

The winning `(voxel_res, prune_fraction)` cell **moves on 5 of 10 rows**.
Across all 240 cells the freeze lifts the whole leaf-count surface — mean
leaves **6.34 → 8.43**, cells above `MAX_LEAVES` **19.6% → 32.5%**, cells below
`MIN_LEAVES` 27.1% → 7.1% — and the search re-ranks into it.

> **The freeze does not restore limbs where the pipeline was looking. It
> over-segments everywhere and the search lands somewhere else.**

Every arm measured so far scored **the served cell**, which is *the search's own
ranking key*. Scoring a change on the metric the search optimises cannot
distinguish "the tree got better" from "the search moved". The in-place
comparison separates them and inverts the result.

n = **3** informative subjects; sign test **p = 0.125**.

## 3. Prior art (CLAUDE.md §0)

| Adaptation | Source | Bears on |
|---|---|---|
| Significance computed **once**, on the unpruned skeleton, in a unit independent of which branches survive | Shaked & Bruckstein, *Pruning Medial Axes*, CVIU 69(2) 1998 — the "rate pruning" framing; Shen et al., Pattern Recognition 44 (2011) for the local/global split | Names the shipped rule's defect: `prune_fraction × longest` is global **and** recomputed |
| Elder-rule persistence of the geodesic-distance function | Standard TDA simplification; nearest formal match to this tree | **Measured and REJECTED as an improvement** — ties the freeze, beats nothing |
| Monotone significance giving a *nested* hierarchy under one threshold | Ogniewicz & Kübler, *Hierarchic Voronoi Skeletons*, PR 28(3) 1995; Reniers et al., IEEE TVCG 14(2) 2008 | Why a frozen threshold is the right shape, if any threshold is |
| **Rejected:** stop on reconstruction error | Bai & Latecki, TPAMI 2007 | Needs a reconstruction the curve skeleton does not carry |
| ⚠ **Correction owed:** `mesh_to_tree.py:1166-1168` attributes three claims to Bai & Latecki and Svensson & Sanniti di Baja. The paper's full text contains **none of them.** The substance is defensible from Frucci et al. (ICPRAM 2013); the attribution is not. | | Fix while in the file |

## 4. Precondition — decouple before measuring

`keep_components()` (`:962`) gates the frozen cutoff **and** `_keep_or_stitch`.
The measurement must isolate the freeze, so the flag must be split first. This
is a one-token change plus a new flag; it ships **no default change**.

Two of the five test failures observed under the coupled flag are the **stitch**
half (`test_probe_extraction_fate.py`, whose `largest_component` hard-codes the
discard) and disappear under decoupling. Do not attribute them to the freeze.

## 5. The held-out set

The five committed scorecard subjects — **bird, fish, insect, quadruped,
humanoid**. They qualify, and the qualification was verified rather than
assumed:

* different provider's meshes from the M4 ten used to formulate the fix;
* graded against `anatomy_expectation.json`, hand-authored **2026-08-21**,
  single commit, untouched since — it predates the ratchet's discovery
  (2026-09-02) and is provably unfitted;
* `_keep_or_stitch` is a **no-op** on all five at every shipped voxel (1
  component in all 15 cells), so every delta is the frozen cutoff alone and the
  coupling is not a confound.

### 5a. ⚠ What the held-out set can and cannot grade — measured 2026-09-03, before the run

Only **`bird`** of the five carries an authored anatomy row.
`anatomy_expectation.reference_count_for` returns **6** for `bird` and **None**
for `fish`, `insect`, `quadruped` and `humanoid`. The claim that all five are
"graded against a human-authored oracle" is true of one of them.

Two consequences, both binding on how the result may be reported:

1. **K3 (leaf count vs target) is evaluable on `bird` ALONE — n = 1.** It is
   therefore not a population claim and must never be reported as one. This is
   survivable because `bird` is also the named prediction, so the bar's
   leaf-count key and its decisive prediction are the same subject by
   construction.
2. **K1 and K2 are evaluable on all five**, because `stub_flaps` and pair count
   need no target. They are the primary keys, which is now doubly justified.

3. **The five split into two regimes, and the split matters.** For `bird`,
   production supplies an authored R and the plateau vote never runs. For the
   other four it supplies `None`, so the vote DOES run — over the very curve
   the prune shapes. Those four therefore measure freeze-and-vote together,
   not the freeze alone. Report the two regimes separately; do not pool them.

## 6. THE BAR — pre-registered, to be pasted into the probe before any number is looked at

```
K1  SAFETY, terminal.  stub_flaps must not rise on ANY held-out subject.
    A rule that invents flaps is disqualified regardless of every other key.
    Hit -> DO NOT SHIP.

K2  PRIMARY, pair count -- DIRECTION-FREE.  At least ONE held-out subject must
    GAIN a symmetric pair, and NO subject may LOSE one.
    A leaf gained as part of a bilateral pair cannot be a lone stray twig; a
    leaf gained alone can. Leaf count cannot make this distinction and is
    therefore not the primary key.
    ⚠ AMENDED 2026-09-03, BEFORE THE RUN. The original wording said "toward its
    AUTHORED pair count" and is UNEVALUABLE: there is no authored pair count.
    `expected_pairs` occurs in exactly two fixtures -- anatomy_reference.json,
    which is frozen and whose own _meta reads "extraction-derived, NOT ground
    truth", and fish_bilateral_evidence.json. anatomy_expectation.json, the
    human-authored oracle, carries THREE fields and none of them is a pair
    count. Grading against anatomy_reference.json would re-enter the closed
    loop this design exists to escape, and hand-authoring pair targets now,
    after seeing the data, would not be ground truth either. So the key is
    direction-free: a gain anywhere, a loss nowhere. It is weaker than the
    original and it is evaluable, which the original was not.

K3  SECONDARY, leaf count, ONE-WAY.  Σ|served_leaves − min(T,8)| must not get
    WORSE. An improvement here is not sufficient for a ship.

NAMED PREDICTION.  bird serves 4 leaves against an authored 6, and that deficit
    is independently confirmed by the VLM judge ("Four appendages where a bird
    needs six", fixtures/vlm_judge/replay.json). It is the largest anatomy gap
    on the held-out set and exactly the shape the freeze claims to repair.
    ⚠ AMENDED with K2: an earlier draft wrote this as "4 leaves / 1 pair
    against an authored 6 / 2". The 6 is sourced (anatomy_expectation.json) and
    the 2 was NOT -- it was inferred, and no authored pair count exists. The
    judge's quote is about APPENDAGES, not pairs. Only the leaf half of this
    prediction is sourced; it is stated that way now.
    If NO subject gains a pair -> DO NOT SHIP, even if K3 improves: the only
    thing that moved is leaf count, which this project has already ruled the
    wrong yardstick.

MECHANISM REPORT.  Required, ungated -- report, do not score. For every subject
    whose served leaves or pairs move, record (a) whether the winning
    (voxel_res, prune_fraction) cell changed, and (b) the freeze's leaf count
    AT THE SHIPPED ARM'S OWN winning cell.
    On the M4 ten the entire benefit was cell re-routing: in place the freeze
    is 4x worse (16 vs 4) and 5 of 10 winners move cell. If the held-out gains
    are also purely re-routing, the change MUST be described as "shifts where
    the search lands", NEVER as "fixes the ratchet", in the PR body and in
    every docstring.

SNAPSHOT RULE.  tests/fixtures/mesh_validation_trees.json WILL fail -- insect
    at 96/0.55 moves 8 nodes/6 leaves/3 pairs -> 13/8/4. Regenerating it is NOT
    evidence and is not part of passing this bar. Before re-blessing, inspect
    the new insect tree leaf-by-leaf against the mesh (positions plus
    label_leaves) and attribute the diff in the style of
    scorecard_baseline.jsonl's `attribution` block.
    test_pair_reconcile.py's _ADMISSION_ACCEPTED census also moves, and that
    test's THIRD assertion ("every other subject is unaffected") is FALSIFIED
    by the freeze -- fish splits 6 vs 4. It must be REWRITTEN, not renumbered.
    test_a_refused_pairs_gap_still_reaches_the_scorecard loses its only live
    witness (fish v64/p0.5 stops being degenerate) and needs a replacement
    input, not a re-bless.

VOID CONDITIONS.  The run is void if the shipped arm does not reproduce
    scorecard_baseline.jsonl exactly, or if benchmark_subjects reports any
    moved axis on the shipped arm. Ignore path_drift_max deltas of order 1e-16
    on humanoid/insect (known platform issue, documented in the baseline).
```

### What each outcome means

| outcome | decision |
|---|---|
| K1 hit | **DO NOT SHIP.** Terminal. |
| K2 fails, K3 improves | **DO NOT SHIP as an anatomy fix.** At most a *packing-window* change with the anatomy claim withdrawn from every docstring and PR body — and only if K1 is clean and the mechanism report is published. |
| K2 passes, K3 flat or better, K1 clean, ≥1 pair gained | **SHIP**, decoupled, with the mechanism report in the PR body. |
| K2 passes only via `insect` | **Suspicious.** `insect` already over-pairs (4 against 3) and is the subject the freeze moves most. `insect` 4 → 3 while others hold is a real pass; `insect` 4 → 5 is a K2 *worsening* and fails. |

## 7. If it passes, one more run before shipping

Run **elder-rule persistence** on the same held-out five. It ties the freeze on
the M4 ten (Σ=1, 9/10) while differing on two rows that cancel. If both pass the
held-out bar identically, the tie is confirmed on two independent sets and the
mechanism is genuinely unidentified — **prefer the rule with the smaller blast
radius.** If they diverge, that divergence is the first real evidence anyone has
about *which* property of the prune rule matters.

## 8. Out of scope

The `MAX_LEAVES = 8` clamp. Octopus and spider carry authored targets of 9 and
cannot serve more than 8, so a residual of 1 is their floor. Raising the clamp
is a packer question with its own spec; nothing here touches it.

---

## 9. Closing record — the quadruped "collapse", diagnosed 2026-09-03

The bar's mechanism report showed `quadruped` serving **0 leaves** under the
freeze at arm A's own cell (voxel 128, prune 0.3). That was reported as a
"total collapse" and read like a bug. **It is neither a collapse nor a bug, and
the precise mechanism strengthens the re-routing finding rather than
complicating it.**

Measured directly on the prune output at that cell:

| voxel 128, prune 0.3 | nodes | leaves |
|---|---|---|
| shipped | 12 | **7** |
| freeze | 19 | **11** |

**The freeze produces MORE tree there, not less.** 11 leaves exceeds
`MAX_LEAVES = 8`, so the candidate is inadmissible; `reference_feature_count`
then finds no plateau inside the packable window and returns **R = 0**, which
fires the terminal exit unconditionally (`mesh_to_tree.py:3245`,
`or ref_count <= 0`) and serves nothing. With the grid pinned to a single cell
there is no other cell to fall back to.

**Two things this rules out**, each checked:
* *Not a pinning artifact.* Arm A pinned to the identical cell serves **7
  leaves, `confirmed=True`, R=7**. Pinning is fine; the freeze is what changes.
* *Not the normaliser.* The predicted mechanism was that `longest` (max over
  ALL edges, including unprunable spine) sets a cutoff above every limb. It
  does not here: the round-0 cutoff is **10.87** and **10 of 19** leaf branches
  clear it. The normaliser ratio at this cell is only 1.43x (36.25 vs 25.39).

**What it IS:** the same over-segmentation the M4 measurement recorded —
the freeze lifts the whole leaf-count surface (mean 6.34 → 8.43 across 240
cells; cells above `MAX_LEAVES` 19.6% → 32.5%). With a free grid the search
escapes to a cell whose count lands back inside the window, which is why the
freeze looks good on the served metric. Pinned, there is nowhere to escape to.

**So the correct sentence is "the freeze over-segments past the packable window
and the search re-ranks around it", not "the freeze destroys the tree".** The
0 is a property of the serve, not of the tree.

## 10. The tie-break — RUN 2026-09-03. The freeze wins.

§7's follow-up was deferred on the grounds that no default was being flipped.
**The Class-3 refutation put the flip back on the table**, so it was run.

**The decisive row — the lizard, committed fixture mesh, authored T = 6:**

| rule | leaves | pairs | stubs | fidelity | cell |
|---|---|---|---|---|---|
| A shipped | 5 | 1 | 0 | 0.8333 | 96/0.20 |
| **B freeze** | **6** | 1 | 0 | **1.0** | 64/0.20 |
| **D persistence** | **6** | 1 | 0 | **1.0** | 64/0.45 |

**Both rules reach the anatomy §1.1 called unreachable.** On the evidence that
actually matters they are tied.

**The held-out five separate them, and the freeze wins:**

| subject | B freeze lv/pr/st | D persistence lv/pr/st | |
|---|---|---|---|
| **bird** (authored T = 6) | **6**/1/0 — hits target | **5**/1/0 — misses | **B** |
| fish | 8/3/0 | 8/3/0 | tie |
| insect | 8/**4**/0 | 8/**3**/0 | **B**, more pairs |
| quadruped | 6/2/0 | 7/2/0 | differs, no target |
| humanoid | 5/2/0 | 5/2/0 | tie |

**B beats D on the only held-out subject carrying an authored target, and B's
pair count is >= D's everywhere.** Add the asymmetries already known: the
freeze's blast radius is measured (3 test files, itemised in §6's snapshot
rule) while persistence's is unmeasured, and the freeze is an existing code
path behind a flag while persistence is new code. **Prefer the freeze. Do not
build persistence.**

### ⚠ What the tie-break does NOT establish

**Neither rule delivers correct anatomy — only the correct COUNT.** The
lizard's six leaves carry **1 pair** under both rules, where four legs should
give **2**. Two legs are read as unpaired singletons. So the strongest
available case for the freeze is *"it reaches the authored feature count on a
subject the spec called unreachable"*, and explicitly **not** *"it extracts the
lizard's anatomy correctly."*

That residual is the surviving argument for P3's U5' — shape, not count.

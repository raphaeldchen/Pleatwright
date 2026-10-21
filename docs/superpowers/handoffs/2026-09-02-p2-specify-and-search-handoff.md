# Handoff: P2 (specify and search)

**2026-09-02. 6 tasks, 51 steps, 19 commits, PR #179 (`claude/p2-implementation` -> `main`). CI green — the first clean run this repo has ever had.**

P2 is the second stage of the LLM-guided extraction design
(`docs/superpowers/specs/2026-09-01-llm-guided-extraction-design.md`). Its
premise: **the LLM supplies the objective, deterministic search supplies every
knob value.** No LLM output is ever a voxel resolution or a prune fraction.

This document exists because three things P3 depends on live nowhere else, and
because the largest finding of the day is not in any commit message.

## What shipped

| unit | change |
|---|---|
| U2 | `mesh_report._provenance_lines` dispatches on its dict, not a hardcoded tuple; `"llm"` provenance added |
| U2 | `auto_mesh_to_metric_tree` gains `reference_provenance=` (keyword-only, default `"external"`) |
| U2 | `anatomy_spec.py` — table first, model second, rows missing a derivation or citation **discarded** |
| U4 | `WIDE_VOXEL_GRID` (24..256) + `wide_grid_budget` |
| U4 | `spec_distance` — cell ranking, pair axis honestly inactive |
| U3 | `probe_framing_lever.py` — the instrument, and the live run that declined the unit |

Per spec §16, P2 ships its components **unwired**; Integration is §15, assigned
to P3. `vlm_judge.py` and `order_rank.py` are byte-unchanged, `hull_coverage`
still has zero occurrences in `order_rank.py`, and `MIN_LEAVES, MAX_LEAVES =
4, 8` is untouched.

---

## M4 — the framing lever, measured live. Verdict: **DO NOT SHIP U3.**

**The bar, pre-registered in `probe_framing_lever.BAR` before any numbers
existed:** *improve at least one subject's leaf count toward its authored
anatomy target, and regress none.* That is the same bar the **global** camera
change failed on 2026-08-25 (`85967c1`; `probe_mesh_bakeoff.py:236` — *"GATE
CLOSED … THE ANSWER IS NO — NOT GLOBALLY"*).

**The operational check passes: 0 of 10 rows carried an error.** Every draw
succeeded, so this is a real refutation and not ten swallowed exceptions.
`verdict()` cannot distinguish those two cases — always run this check before
believing a `DO NOT SHIP`.

| subject | target | control | framed | |
|---|---|---|---|---|
| lizard | 6 | 6 (dist 0) | 6 (dist 0) | unchanged |
| horse | 6 | 8 (dist 2) | 5 (dist 1) | improved |
| bird | 6 | 8 (dist 2) | 5 (dist 1) | improved |
| spider | 9 | 7 (dist 2) | 8 (dist 1) | improved |
| **octopus** | 9 | 7 (dist 2) | 5 (dist 4) | **regressed** |

Generator pinned on every row: `FLUX.1-schnell` `/infer` -> `Hunyuan3D-2`
`/shape_generation`. The prior camera fixture recorded no generator at all,
which made "same generator" an inference; that is not repeated here.

**Two findings worth more than the verdict.**

1. **The regression is the octopus — the same subject that killed the global
   change.** Per-subject framing is strictly *better* than global (three
   subjects rescued instead of one) and fails on the identical subject. A
   replication, not a coincidence.
2. **The lizard — §10's flagship example — shows ZERO effect.** 6 leaves in
   both arms. §10 called framing *"the highest-value measured lever in the
   whole design"* on the strength of the lizard going 1 -> 5. That headline was
   entirely an artifact of a superseded default: the fixture was committed at
   `43bcc1a`, the margin clause that fixed it landed at `c27f81e` the next day.

The bar was **not** re-scored to match the outcome, exactly as M3's was not in
P1.

---

## What U4 does NOT claim

P3 must not inherit a credit U4 did not earn.

* **"Fidelity against the spec" was already shipped.** The `reference_count=`
  seam (`mesh_to_tree.py:2710-2713`) is default-on and reaches **both**
  terminal exits; `tests/test_anatomy_expectation.py:332` already asserts it.
  **A test of that shape passes with U4 entirely reverted.** U4's new content
  is exactly three things: the widened grid, the cell budget, the ranking.
* **Class 2 is out of U4's success criteria.** `fidelity_score` clamps
  `r_eff = min(max(R, 4), 8)`, so `fidelity_score(8, 9) == fidelity_score(8,
  8) == 1.0`. For octopus and water bear — both 9-feature targets, and the two
  subjects §3's Class 2 names — feeding a spec target of 9 is *arithmetically
  identical* to today. A test pins this so no future reader claims the win.
* **U4's pair axis is INACTIVE on table hits.** None of the 14 authored rows
  carries a pair count; `expected_pairs` exists only in the frozen,
  extraction-derived `anatomy_reference.json`. Sourcing it from there would
  re-enter the closed loop this design exists to escape.

---

## ★ The prune ratchet — the largest finding, and it is not in any commit

Investigated 2026-09-02 while answering a question about VLM image gating. It
is unfixed. **It is where the octopus's arms actually are.**

**The anatomy is never lost at the front of the pipeline.** Traced stage by
stage on both real octopus meshes from the M4 run:

| stage | control | framed | >=9? |
|---|---|---|---|
| concept image | 8 arms + head | 8 arms + head | yes |
| mesh bodies, every res 16-192 | 1 | 1 | yes |
| skeleton components | 1 | 1 | yes |
| skeleton tips @96 | 33 | 35 | yes |
| round-0 tree leaves | 33 | 35 | yes |
| **after prune** | **7** | **5** | **NO** |

**The mechanism.** `_prune_rounds` (`mesh_to_tree.py:1146`) cuts branches below
`prune_fraction * longest`, recomputed every round — and `longest` is monotone
non-decreasing, because `_contract_degree2` sums the chains that pruned twigs
leave behind. The cutoff **ratchets upward** past limbs that already survived.

On the framed octopus at res 96: round 0's cutoff is 12.28 and **all nine
branches survive** (the 8 arms plus the mantle, in a tight band 18.90-26.78).
Pruning 24 noise twigs then makes `longest` jump **49.12 -> 115.46**, the cutoff
more than doubles to 28.87, and **round 1 kills exactly those nine.** The
inversion is explicit: a branch entering at length **12.36 survived**, while one
at **26.78 was deleted** — a shorter branch outliving longer ones because the
deleted arms were summed into its chain.

The control fails differently and also in the prune: one snaking chain of
length 78.32 sets a round-0 cutoff of 15.66 that exceeds every arm (5-11), so
31 of 33 leaves die in round 0.

**Frozen-cutoff A/B, 48 cells (2 meshes x 3 resolutions x 8 prunes): frozen
>= shipped in 48/48.** At the framed served cell, **5 -> 14**.

### ⚠ The trap: fixing the prune ALONE makes the serve WORSE

End-to-end with the cutoff frozen: control 7 -> 7, framed 5 -> **4**.

`reference_feature_count` votes R as the **widest plateau** on the very curve
the prune corrupts. The frozen framed curve is `{0.2:15, 0.25:14, 0.3:13,
0.4:12, 0.45:8, 0.5:5, 0.55:4, 0.6:4}` — the true anatomy has width 1 per
count, the degenerate collapsed tail has width 2, so **R = 4**, and the search
exits at fidelity 1.0 on a 4-leaf tree. **The ratchet and the plateau vote must
be fixed together.** And note the ceiling above them both: `MAX_LEAVES = 8`
means a 9-feature octopus can never serve more than 8 leaves regardless.

**Not verified:** that a 9-leaf tree is 9 *anatomical* features. In the frozen
9-leaf cells some tips are near-duplicates — split tips of one arm. "Recovers 9
leaves" is measured; "recovers 9 features" is not.

> ## ⚠ CORRECTED 2026-09-03, by a prior-art and design pass over this section
>
> Three of this section's claims do not survive contact with the literature and
> with the rest of the repo. The mechanism above is unchanged and reproduces
> exactly; what changes is **how much it matters and what the evidence proves**.
>
> **1. "The ratchet and the plateau vote must be fixed together" is TRUE OF
> PROBES AND FALSE OF PRODUCTION.** `server.py:4152` passes
> `reference_count=anatomy_expectation.reference_count_for(prompt)`,
> `external_r_enabled()` defaults **ON**, and `reference_count_for("an
> octopus")` is 9. `mesh_to_tree.py:3065` then takes the injected value and
> **never runs the vote**. The R=4 trap recorded above came from
> `probe_framing_lever.py:166` calling `auto_mesh_to_metric_tree(glb)` with no
> `reference_count` — a property of the probe I wrote, reported here as a
> production defect.
>
> **2. "Frozen beats shipped in 48/48" IS VACUOUS.** The frozen cutoff is by
> construction ≤ every ratcheted cutoff (`longest` is monotone non-decreasing),
> so the frozen arm deletes a subset at each round. **All eight candidate
> pruning rules tested satisfy 48/48.** A statistic every option satisfies has
> zero discriminating power; it restates the direction of the change, not
> evidence for it. **Do not cite it again.**
>
> **3. An EARLIER, committed 48/48 already said what those leaves are, and it
> disagrees.** `mesh_to_tree.keep_components()`'s docstring (`:928-962`,
> measured 2026-08-21) records: *"the prune fix WITHOUT the stitch recovers a
> leaf from a discarded component in ZERO of the 48 — it cannot; **every leaf
> it adds is a torso twig**"*. That is a different 48 (octopus + lizard) that
> coincidentally has the same shape as this one (octopus control + framed). The
> two must be reconciled before any leaf-count gain is called anatomy.
>
> **What the evidence actually supports, measured end to end on all ten M4
> meshes against authored targets:**
>
> | | Σ \|served − target\| | exact hits |
> |---|---|---|
> | self-derived R (the vote) | 14 | 2/10 |
> | **authored R (production default)** | **1** | **9/10** |
> | best plateau-vote repair | 10 | 3–4/10 |
>
> Framed octopus, served cell: **neither fix 5, prune-only 4 (worse),
> vote-only 7, both 8.** Every vote repair works by removing a false *stop*;
> only the authored table supplies a true *target*. In 9 of 30 frozen cells the
> clamped authored target is not present anywhere on that voxel's prune curve,
> so no rule reading off that curve can produce it.
>
> **Two further defects this section missed:**
> * **The normaliser is a second, independent defect.** `longest` is `max` over
>   **all** edges including unprunable spine chains — control v128 reads
>   **74.10** against a longest *prunable* branch of **28.74** (2.6×). Freezing
>   alone freezes the wrong number on that mesh, which is why the control reads
>   7 → 7. The control fails at round 0 by normaliser error, not by ratcheting.
> * **The freeze cannot be shipped as a flag flip.** `keep_components()` gates
>   the frozen cutoff **and** `_keep_or_stitch` together, and they cannot be
>   split without forest handling — `_bfs_remap` raises on a forest (`:1476`).
>
> ### The measurement that scopes it, run 2026-09-03 under PRODUCTION conditions
>
> 20 runs: 10 real meshes (5 subjects x control/framed), each with
> `reference_count=anatomy_expectation.reference_count_for(prompt)` supplied
> exactly as `server.py:4152` does, under arm **A** (shipped prune) and arm
> **B** (`IDE_KEEP_COMPONENTS=1`, frozen cutoff). Zero errors.
>
> | | Σ \|served − T\| | exact hits |
> |---|---|---|
> | **A — shipped** | **8** | 4/10 |
> | **B — frozen** | **5** | 6/10 |
>
> Per subject (B − A): lizard **0**, horse **−1**, bird **−1**, spider **0**,
> octopus **−1**. **Helps 3 of 5, hurts none, unmoved on 2** (lizard already
> exact; spider sits at the `MAX_LEAVES=8` clamp floor on both arms with a
> target of 9). `stub_flaps` was **0 on all 20 rows** — neither arm invents
> anatomy anywhere in this sample.
>
> **So the freeze IS a real win under production conditions — modest,
> subject-dependent, and smaller than the probe-condition numbers implied.**
>
> **On the "torso twig" verdict, the evidence is now mixed and the earlier
> claim does not hold as stated.** Three cells gained a leaf under B:
> * `bird-framed` and `octopus-framed` each gained **+1 leaf AND +1 pair** —
>   the addition arrived as a **bilateral pair**, which a single stray twig
>   cannot produce. Consistent with a restored limb pair; also consistent with
>   two symmetric noise bumps. **Cannot tell** without per-leaf inspection.
> * `horse-control` gained **+1 leaf, pairs unchanged at 0** — unpaired, and
>   the added leaf sits at height **y = 75.0**, *above the head* (56.81) and
>   far above the other three appendages (0.5-3.5). On a quadruped whose legs
>   sit near the ground, that geometry **leans noise**, though it was not
>   visually confirmed against the mesh.
>
> **What this does NOT license.** Five subjects. The freeze **cannot ship as a
> default flip** (see the `keep_components` coupling above). And it leaves the
> normaliser defect untouched, which is why the two worst rows in the sample —
> `octopus-control` (7 of 9) and `spider` both variants — are unmoved on both
> arms. Raw rows: `.superpowers/sdd/prune-production-ab.json` (gitignored;
> regenerate with the method above).

> ### ⛔ The normaliser fix was measured and REFUTED, 2026-09-03
>
> The obvious next move — fix the normaliser, since `longest` is `max` over all
> edges including unprunable spine — **was measured and is actively harmful.**
> Same 10 meshes, same production call shape, scored against `min(T, 8)`:
>
> | rule | Σ \|served − min(T,8)\| | exact | verdict |
> |---|---|---|---|
> | A shipped | 4 | 6/10 | baseline |
> | **B freeze** | **1** | **9/10** | what we already have |
> | C leaf-branch normaliser | **14** | 7/10 | **worse than doing nothing** |
> | D persistence | **1** | **9/10** | **ties B; beats nothing** |
>
> **C fails in both directions on one subject**: `bird-framed` serves **11
> leaves against a target of 6**, and `octopus-framed` serves **0 leaves,
> `confirmed=False`** — a total non-serve, worse than the unfixed baseline
> which served 7 there. Do not ship it, and do not re-propose it without new
> evidence.
>
> **D — elder-rule persistence, the literature's own answer** (stable by
> construction, root-invariant, nested for every k) — **ties the freeze and
> beats nothing.** They differ on two rows that cancel: D closes
> `octopus-control` (7→8) and opens `octopus-framed` (8→7). Theoretical
> soundness and measured benefit came apart cleanly here.
>
> `stub_flaps` was **0 on all 40 rows** — no rule invents anatomy.
>
> ⚠ **Validation caveat:** all 20 A/B rows carry wall-clock times byte-identical
> to the earlier file, so they were **reused, not re-run**. The search is
> deterministic so the values are right, but the C/D harness was never
> validated against a known-good baseline. Re-run that check before building on
> D specifically.
>
> **Conclusion: the freeze is as good as anything tested.** The remaining work
> is to decouple it from the stitch so it can ship, not to find a better rule.

> **Unrelated finding from the same pass, worth fixing:** the citation at
> `mesh_to_tree.py:1166-1168` attributing three claims to Bai & Latecki (TPAMI
> 2007) **does not check out** — the paper's full text contains none of them.
> The substance is defensible from Frucci et al. (ICPRAM 2013); the attribution
> is not. Separately, skeletor's `radius` column is populated and **discarded**
> at `:822-834`, though it is a canonical local significance measure.

**Two project-memory claims were REFUTED against these meshes:** that
resolutions attaching octopus arms sit outside `VOXEL_GRID` (nothing needs
attaching — body count is 1 at every resolution), and that coarser voxels weld
better (does not reproduce; that was a different octopus asset from an earlier
provider run).

---

## The VLM concept-image gate — asked, investigated, refuted

Proposal: judge the concept image with a VLM against the wanted anatomy, and
regenerate with targeted feedback when it fails. **It cannot catch the failure
that motivates it.** The anatomy is present in the image, the mesh, the voxel
solid, the skeleton and the round-0 tree; a VLM at the front is separated from
the defect by five stages.

The obvious refinement — judge *limb separation* rather than anatomy — is
refuted by the same numbers **and points the wrong way**: the more
self-contacting image (framed) produced the *richer* skeleton (35 tips vs 33,
frozen ceiling 14 vs 8). A separation gate would have rejected the better
input. Touching arms do fuse (framed genus 11-20 vs control 1-5) but fusion
makes *handles*, not lost limbs.

**What survives, and it is a different question in a different place:** a
one-call, advisory, **subject-identity** check — *"is the primary subject of
this image a {subject}?"* The recorded stage-1 failure is not too few features,
it is *"a water bear"* returning a literal bear — a categorical error that is
100% visible in the concept image and invisible downstream, because the bear
mesh extracts cleanly and serves a perfectly good bear tree. `mesh_identity.py`
already does exactly this for meshes, with a pre-registered band.

**Prerequisite before any regeneration experiment:** production does **not**
pin the stage-1 image seed (`get_provider("hf2")` passes no `image_kwargs`), so
"regenerate with feedback" changes the prompt *and* the seed simultaneously and
no success is attributable. Pinning it costs nothing.

---

## Methodological findings

1. **Five of six tasks needed a fix wave, and every defect was in the plan's
   own reference code, not the implementer's work.** A dict fixture where the
   code read an attribute (test could not fail); a cache guard missing
   valid-JSON-non-dict; validation on fresh rows but not cached ones; `pairs`
   assumed an int when every producer emits a list; and a probe whose `draw()`
   would have spent live GPU quota and returned a **fake refutation**. The plan
   file was corrected for each.
2. **The final whole-branch review ran 19 independent mutations and 2
   escaped** — both in code no fix wave had touched. One was the `pairs` defect
   one field over (`spec_distance` read `leaves`; all six `trace.append` sites
   emit `leaf_count`, making the ranking **constant** on real rows). The other:
   **the probe's two arms were confounded** — the framed arm dropped seven
   clauses the control carries, including `nothing cropped`.
3. **Check an instrument against real objects before firing it.** Task 6's
   `draw()` read `res.tree`, which does not exist; the `except` swallowed the
   `AttributeError` and `leaves` was `None` on every row. `verdict()` skips
   `None` rows, so the probe would have returned `DO NOT SHIP U3` every time
   regardless of the lever — indistinguishable from a real result.
4. **CI completed for the first time ever**, by marking the whole of
   `test_provider_variation.py` slow. Every CI failure this repo has recorded
   died inside that one file, at wall times from 10.1 to 52.5 minutes and
   across at least two distinct signatures. The successful run took **46
   minutes** — inside the window where three earlier runs died — which
   retrospectively kills elapsed time as the driver.
5. **A 275-commit stale checkout was invisible for a whole session.** The
   working checkout sat on a branch from 2026-08-06 while all work happened in
   a worktree, so committed and merged files read as "file not found".

---

## What P3 must do with these answers

* **U3 is declined, not deferred.** If framing returns, it is a *per-subject
  opt-in* with its own bar, and the octopus is the pre-registered failure case.
* **U5's producer choice inherits M4's table**: framing moves four of five
  subjects, three of them the wrong way.
* **Do not wire `spec_distance` to `res.trace` rows without checking the key.**
  Trace rows carry `leaf_count`; candidate rows carry `leaves`. The function now
  accepts both, but the next row shape will not be covered.
* **`MeshTreeResult.orientations` and `_last_orientations` stay RECORDED,
  NEVER RANKED.** P3 may read them; nothing may rank on them without its own bar.
* **The prune ratchet is the highest-value open work in the pipeline** and it
  costs no model calls.

## Open items

* PR #179 open and green.
* The prune ratchet and the plateau vote — unfixed, must be fixed together.
* Stage-1 image seed — unpinned.
* `orient_error` and `MeshTreeResult.orientations` remain write-only channels.

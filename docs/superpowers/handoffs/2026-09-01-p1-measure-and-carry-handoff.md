# Handoff: P1 (measure and carry)

**2026-09-01. 6 tasks, 45 steps, 18 commits, PR #174 (`claude/mesh-metric-tree-pipeline-7e56e9` -> `main`), branch head `0e08f94` on top of `13731b6`.**

P1 is the first stage of the LLM-guided extraction design
(`docs/superpowers/specs/2026-09-01-llm-guided-extraction-design.md`). It ships
**no LLM call at all**. Its whole job was to answer three questions the later
stages depend on, and to build the one channel P2 and P3 need. The spec's
sequencing rule is that **P1 must land and be measured before P2 or P3 is
planned** — this document exists because the three answers were about to survive
only in a gitignored scratch file.

## What shipped

| unit | change |
|---|---|
| M1 | `probe_reachable_cells.py` — does any Class-1 cell compile cleanly? |
| M2 | `probe_wide_window.py` — what happens past the 8-leaf window? |
| M3 | `probe_orientation_placement.py` — do measured orientations beat the fabricated arrangement? |
| U1 | `orientations.py` — per-stick azimuth/elevation, pinned bit-for-bit to `vlm_judge._angles` |
| U1b | `mesh_to_tree._last_orientations` side channel + `frame_from_mesh`, `MeshTreeResult.orientations` |
| U6 | `rescue_ladder.orientation_layout` + an appended `orientation` placement rung |

`vlm_judge.py` and `order_rank.py` are **byte-unchanged**. `MAX_LEAVES` is still
`4, 8` with zero +/- lines on the branch. `hull_coverage` still has **zero**
occurrences in `order_rank.py` — the §1.1 rule that coverage is never a ranking
key is intact.

---

## M1 — reachability. Verdict: **MET**. U4 ships.

**The question.** The spec's Class 1 says some extraction cells outside the
shipped `(voxel_res, prune)` grid produce the anatomically right leaf count. If
none of those cells actually *compiles* cleanly, U4 (search the wider grid) is
pointless.

**The answer.** 36 of 69 rows are Class-1 cells (`in_shipped_grid` false) that
compiled with `stub_flaps == 0`, across **three** subjects (bird, humanoid,
quadruped) — including the flagship cell Class 1 rests on:

| bird, `voxel_res` 192, `prune` 0.40 | |
|---|---|
| leaves | 6 |
| pairs | 2 |
| `stub_flaps` | 0 |
| ladder stage | `order` |
| `hull_coverage` | 0.7698 |
| `structural_prefilter` | True |

**What this does NOT say.** A hit is a **count** match, not an anatomy match —
recorded in the fixture's own `_meta.caveat`. Six leaves in the right number
says nothing about whether they are the right six. This is necessary, not
sufficient, and P2 must not quote it as an anatomy result.

**A defect here reversed a conclusion I had already stated.** The first draft
called `structural_prefilter(nodes)` without `root_children`; production passes
the **pre-reconciliation** count. Reading `prefilter: False`, I concluded U4
could never reach the bird cell at all. After the fix **all 60 compiled rows
read `prefilter: True`.** The probe was wrong, not the pipeline. Anyone
re-reading this fixture should know the earlier reading existed and was an
instrument defect.

---

## M2 — the wide window. **Two arms, and they are not comparable.**

**The question.** `MAX_LEAVES` is 8. What is on the other side of that clamp —
is the window a real packing limit or an arbitrary one?

The first version of this probe measured **the rescue ladder** and labelled the
result **the packer**. It was split into two arms because they answer different
questions and disagree loudly.

**Arm A — raw** (`probe_broad.run`, GUI-style scale-only). This is the **only**
arm comparable to the committed `k<=8` rows in
`s5_engine_repair_evidence.json -> packability_control`.

| k | jitter 0.0 | jitter 0.01 | jitter 0.3 |
|---|---|---|---|
| 9 | 1/1 | **0/20** | 7/20 |
| 10 | 1/1 | 17/20 | 8/20 |
| 11 | 0/1 | 4/20 | 8/20 |
| 12 | 0/1 | 0/20 | 5/20 |

**Arm B — laddered** (`mesh_to_tree._default_compile_fn`, the full serve path).
Every k, every jitter: **1/1, 20/20, 20/20.**

**Proof the arms genuinely differ**, measured on the same tree, jitter and
seeds at k=4 / jitter 0.01: committed raw **2/20** vs laddered **10/10**. One
table holding both without saying which is which would read as a packer result
when it is a rescue result.

**Read the raw arm carefully — it is not monotone in k.** k=9 at jitter 0.01
reads 0/20 while k=10 reads 17/20. Do not summarise this as "gets worse past
8".

Dominant failure class is `POLYS_MULTIPLE_IBPS` throughout. `polygon network is
not valid` peaks at **11/20 at k=9 / jitter 0.01** — and its documented remedy
is placement seeding, which is exactly U6's lever.

**The limitation that matters most.** Every row in `real_wide_trees` is
**`status: skipped`** — the octopus and water-bear meshes are gitignored
provider-cache artifacts absent from a fresh checkout. So the whole measurement
is **synthetic stars only**. *"Can a real 9-flap animal pack?"* is
**UNMEASURED**. P2 and P3 must not treat the laddered 20/20 as evidence that
widening the window is safe on real subjects.

---

## M3 — orientation seeds. Verdict: **DO NOT SHIP U6**, retained anyway.

**The pre-registered bar.** *U6 ships only if orientation-derived seeds are
non-inferior to `structural_layout` on `stub_flaps` and `design_scale` across
the whole fixture set, AND strictly better on at least one subject.*

**The result: 6 regressions against 7 improvements.**

| regressions | improvements |
|---|---|
| `fish/v64/p0.3` **stubs 0 -> 1** | `humanoid` x6 (`v64/p0.3-0.5`, `v96/p0.3`, `v128/p0.3-0.4`) |
| `bird/v128/p0.4` scale 0.962592 -> 0.882937 | `fish/v64/p0.4` |
| `fish/v64/p0.3` scale 0.636655 -> 0.597936 | |
| `insect/v64/p0.3-0.5` scale 0.56614 -> 0.536147 | |

Non-inferiority fails. `verdict()` was mutation-verified both directions:
forced SHIP -> 6/6 red; forced DO NOT SHIP -> 3/3 red.

**Retained regardless, by explicit owner decision, on separately measured
reachability**: **5 of 45 cells pack ONLY via orientation** (`fish/v96/p0.3`,
`fish/v128/p0.3`, `fish/v128/p0.4`, `insect/v96/p0.5`, `quadruped/v128/p0.3`)
and **0 cells pack only via structural**. This is a call on reachability, **not
a re-scoring of the bar**. `_meta.verdict` still reads `DO NOT SHIP U6` and
should stay that way.

**Why both can be true — the bar tests the wrong shape.** The bar tests
**substitution** (orientation compiled *alone* vs structural compiled *alone*).
The shipped design is **addition**: `placement_variants`
(`rescue_ladder.py:652`) *appends* the orientation rung after `structural` and
`structural+canonical`, and `server._search_first_clean` (`server.py:1906`)
serves the first clean pack in ladder order. **For a fixed tree the orientation
rung is only ever reached when structural already failed or packed dirty** — it
cannot displace a clean structural pack, so the substitution regressions above
largely cannot occur in production.

A replacement bar for the append design is registered at `_meta.next_bar` and
is explicitly **NOT evaluated** against this run's data — applying it here
would be circular, because this fixture is what motivated writing it.

**Two claims from the coordinating session were wrong and are corrected in the
fixture:** the append-not-replace design was committed at **`e7ba72e`**, not
`5960ec5`; and the mechanism protecting a clean rung for a fixed tree is
**`_search_first_clean`'s rung ordering**, not `_serve_rank` (which ranks
candidate *trees* across extraction cells — a weaker, order-dependent thing).

---

## What P2 and P3 must do with these three answers

- **U4 (`search_extraction`) ships** — M1 met its bar. Carry the count-vs-anatomy
  caveat into U4's own success criterion, or U4 will inherit a leaf-count
  yardstick that the extraction wave already recorded as the wrong one.
- **Do not widen `MAX_LEAVES` on M2's strength.** The laddered arm's 20/20 is a
  rescue result on synthetic stars. The real-subject question is unmeasured and
  needs the provider meshes present.
- **`MeshTreeResult.orientations` and `_last_orientations` are RECORDED, NEVER
  RANKED** — same contract as `runner_up`. P3's producer may read them; nothing
  may rank on them without its own bar.
- **The `orientation` rung stays appended.** If anyone proposes promoting it
  ahead of `structural`, that is a substitution change and M3's verdict applies
  directly to it.

---

## Methodological findings — the part most likely to be re-learned the hard way

1. **Chunked local suite runs have a structural blind spot.** Splitting the
   suite across processes put `test_component_stitch` and `test_forest_tolerance`
   in *different* processes, so the run could not see the global leak between
   them. I reported "4618 passed, 19 failed, all pre-existing" as stronger
   evidence than it was. The leak was real and needed PR #175.
2. **The stale symlinked `.so` fired again.** It produces ~19 phantom local
   failures CI does not have. The remedy is unchanged and is *not* a rebuild:
   reproduce at the merge base in a throwaway worktree with identical symlinked
   artifacts and prove non-causation.
3. **Three tests on this branch were vacuous until mutation-tested.** The worst:
   the emitted-id test passed 6/6 with `remap[]` deleted, because the fixture's
   `_bfs_remap` was the identity map. On real meshes that bug leaves the
   orientation channel silently empty. Mutation testing found it; no assertion
   did.
4. **A byte-identity gate can be built out of the wrong files.** Mine covered 7
   files that **call** `to_metric_tree` when the hazard was files that
   **replace** it with a test double. I told the user the gate proved the change
   invisible; two more doubles then went red (`test_normalizer.py:561`,
   `test_runner_up.py:542`).
5. **A probe defect reversed a stated conclusion** (M1's missing
   `root_children`, above). Check a probe against the production call signature
   before believing a negative result.
6. **CI has never completed this suite, on any branch.** Runs die with `exit
   143` (SIGTERM) inside `test_provider_variation.py`, always at the displayed
   `[ 60%]`, always at a *different* test within that file.

   > ⚠ **CORRECTED 2026-09-02, same day.** This entry originally read *"the
   > kill tracks elapsed time, not a poison test"*, on the strength of two
   > runs that died at 52.3 and 48.9 minutes. **That is falsified.** Two more
   > runs landed: `main` at **52.5 min** (uncancellable, nobody pushes there)
   > and a *tiered* run with the 22 heaviest tests excluded at **10.1 min**.
   > A run 5x faster reaching the *same file at the same displayed position*
   > is not a clock. **The constant is the FILE, not the wall time** — and the
   > original reading dismissed that because the individual test differed each
   > time, which was the wrong invariant to track. Four runs, four different
   > tests, one file.

   Mechanism still **UNCONFIRMED**. Ruled out with evidence: memory (143 is
   SIGTERM; this project's recorded local OOM is 137/SIGKILL, and sampled RSS
   stayed flat at 270-480 MB), concurrency cancellation (`conclusion:
   "failure"`, not `"cancelled"`), a network hang (the slow tests have no
   network path — they do unmocked mesh processing), and now elapsed time.
   Open candidates: something cumulative in `test_provider_variation.py`
   (disk from its per-draw mesh cache dirs is the named suspect, measured at
   only ~300 MB locally and so inconclusive), or the account's CI budget.
   There **is** a separately confirmed billing signal — a 44-hour CI blackout
   immediately preceding these failures, with runs in that window carrying
   GitHub's own *"recent account payments have failed or your spending limit
   needs to be increased"* annotation — but it is **not** established as this
   mechanism.

7. **The suite has now completed exactly once, locally, and the tail is
   clean.** `4563 passed, 19 failed, 13 skipped in 47m59s`. **The ~40% that CI
   has never reached passed cleanly** — which materially de-risks the
   unmeasured-baseline worry above, without confirming it on Linux. The 19
   failures are confined to `test_book_axis_projection.py`,
   `test_edge_optimization.py` and `test_projection_guards.py`, which pass on
   Linux CI; that pattern matches this project's documented macOS/Linux
   numeric divergence rather than finding #2's stale-`.so` trap. Caveat on
   that run: it executed in a worktree whose `.so` is a **symlink into the main
   checkout**, so `make`'s build step wrote *through* the symlink. It was
   therefore less isolated than "from scratch" implies, and a worktree build
   mutates an artifact every other worktree shares.

## Open items

- PR #174 is **open**, not merged.
- CI termination is being fixed separately; that work owns finding #6.
- `orient_error` and `MeshTreeResult.orientations` are **write-only channels**
  today. Both are deliberate and precedented (`label_error`'s history;
  `runner_up`'s contract). If P3 does not read `orientations`, they should be
  revisited rather than left indefinitely.

# A — rank the attempt-0 pack. Design spec.

**Cross-goal slice.** Fixes Goal 2's **G2a** (geometry does not mirror) on two
subjects and moves Goal 1's `hull_coverage` / `design_scale` on eight.
Status: **specced, one BLOCKER open (§7.1).** Python only; no claim on
`TreemakerWrapper.cpp`.

> ## ⚠ THE FRAMING THIS REPLACES WAS WRONG
>
> This slice was first described — by me — as *"rank the order stage instead of
> stopping at the first clean result."* **Measured over 30 subjects × every
> variant = 154 served arms, a ranker placed inside the ladder is DEAD CODE.**
>
> **The sharpest test refutes it.** `mesh-insect` already serves from the
> `order` rung after a **one-rung** ladder, so the ladder *is* running order
> variants for it. Of the four rungs first-clean skipped, only `seeded_3` would
> have packed, and it is strictly worse on every axis — scale −9.2%, coverage
> 0.8595 → 0.5999, `mv_swapped` 18 vs 6. `mesh-fish` runs all five order rungs
> and **zero pack**; its serve is a placement rung, so nothing was skipped.
>
> **Across all six subjects whose control reaches the ladder, ZERO have a
> skipped order rung that beats the serve on scale.**
>
> ⇒ The value is entirely in **opening `server.py:1516`'s attempt-0
> short-circuit**. 23 of 30 subjects pack attempt-0 and never see a variant —
> and both motivating examples, `mesh-bird` and `mesh-humanoid`, are among
> them. This is speculative exploration, not re-ranking.
>
> Secondary correction: `_search_first_clean` **already ranks** on one axis
> (cp-audit cleanliness). This slice extends an existing selector.

---

## 1. What it buys

154 arms, all through `server.draft_and_compile_full_base`, coverage from 0b's
true-polygon `paper_coverage`.

| definition of "better" | subjects improved / 30 |
|---|---|
| scale-max | **13** |
| bijection-then-scale | 12 |
| coverage-max | 11 |
| fewer stub flaps | 1 |
| **gains `cp_symmetric`** | **0** |
| **loses `cp_symmetric`** | 2 |

⚠ **`cp_symmetric` is never gained in any of the 154 arms.** This lever fixes
**G2a only**. It cannot touch G2b — consistent with S2a's proof that the M/V
defect is not reachable from the packing at all.

**Of the 13 scale wins, only 9 are reachable at depth 1.** Four require running
a variant's *own* ladder (~70 s per failing arm, 49 rungs) and are **excluded**
by §3. `mesh-quadruped`'s +19.7% is one of these: all five of its depth-1 order
rungs **fail**, and its win is a *second-generation* permutation
`[0,1,3,2,7,5,4,8,10,9,6,11]`. **No ranking of depth-1 variants reaches it.**

---

## 2. The recommended shape

```
control serves → is it a bijection?  ──yes──►  serve control, unchanged
                        │no
                        ▼
        ONE batched child: control + 5 depth-1 variants
                        │
                        ▼
                 rank by §4 → serve
```

**2.1 The predicate gate (`control is not a bijection`) is load-bearing, not an
optimisation.** Measured on the full corpus it fires on **12 of the 13** scale
wins. The single win it skips is `two-level-tree` — *the one whose +5.4% scale
costs the control's bijection and a third of its coverage.* So the predicate:

* captures every win worth having;
* **structurally protects `hshape` and `star-4-sym`** — bijective controls are
  never searched, so the mirror invariant cannot be sold for a 1e-9 scale gain;
* **removes the scale-primary-vs-ε-constraint dilemma of §4 entirely**;
* costs nothing: 6 of 32 serves searched, **392.6 s vs a 404.8 s baseline**
  (always-search is 476.0 s, +17.6%).

**2.2 Batch into ONE child spawn. Do not spec the naive shape.** Per-variant
`_run_isolated` costs **+8.89 s** (bird) — and **97% of that is `import server`
in the child** (1.460 s, of which `feasibility.gate → sklearn.ensemble` is
0.889 s). The packer itself is **~1 ms**. Batched: **0.042–0.050 s for six
candidates**, ~200×, byte-identical scales. Precedent already in the tree:
`_worker_compile_and_regions` runs the whole ladder in one child.

**2.3 No timeout is at risk.** `_COMPILE_TIMEOUT = 60` bounds each
`_run_isolated` join independently; batched is 0.05 s. The in-child 36 s
deadline (`0.6·_COMPILE_TIMEOUT`, `server.py:379`) is set *after* the attempt-0
return at ~line 357, and in-child rungs are ~1 ms — four orders of margin.

---

## 3. Depth 1 only — forbidden: running a variant's own ladder

A variant whose attempt-0 fails must be **discarded**, not rescued. The four
nested wins cost ~70 s per failing arm and can still return `ERROR` after 49
rungs. Candidate pool = CONTROL plus every variant with
`rescue_stage == "none"`.

---

## 4. The ranking rule

```
K1  −stub_flaps                          anatomy honesty; never sold for scale
K2   design_scale, PARSED AT 6 DECIMALS  CLAUDE.md §1.1(4) primary objective
K3   is_bijection                        mirror_verdict(f, axis_degrees=45.0)
K4  −mv_swapped                          ⚠ SUPERSEDED — see the amendment below
K5  −candidate_index, CONTROL at index 0 ties go to control, always

REFUSE: if any survivor's design_scale is None (no `scale=` in frame_title),
        abandon ranking and fall back BYTE-IDENTICALLY to today's behaviour.
        Never coerce None → 0.0.
```

> **⚠ AMENDED 2026-08-15 (U2′). K4 is now `−(mv_swapped + mv_mismatched)`, and
> an unmeasurable count sorts WORST rather than as 0.** `mv_swapped == 0` is a
> known-vacuous criterion (`COORDINATION.md:200`, *"Never gate on it alone"*) —
> a pattern reaches it by relocating the defect into `mv_mismatched`, and
> `cp_mirror.py:326-329` has owned the correct predicate
> (`symmetric = mv_swapped == 0 and mv_mismatched == 0`) the whole time. PR
> #104's root sweep measured six such packs of the scorecard's own trees
> (`humanoid` roots 6, 7; `insect` roots 5, 9, 12, 13): every one reads
> `mv_swapped == 0`, none is symmetric, and under this section's original key
> each **ties** a genuinely symmetric arm at the same scale so K5 hands the win
> to index 0. The same key shape shipped in `root_rank` (U1′, PR #107) already
> counted both kinds; `order_rank` and `root_rank` now share one `mv_defects`.
> K1, K2, K3, K5 and the REFUSE rule above are UNCHANGED, and the new K4 is
> pointwise ≤ the old one, so the rule can only refuse arms it used to accept.
> §4.1's required-fail inputs stand and gain those six measured rows.

**★ K2 must read the PARSED 6-decimal value, not the raw engine float.** This
is the whole disagreement between two recon agents and it dissolves on this one
detail. `hshape`'s five arms span **2.3e-9** of raw scale; ranking the raw float
picks `seeded_2` and **loses a bijection for 2.3e-9**, while ranking the parsed
value gives a five-way tie that the discrete keys resolve to CONTROL.
`TreemakerWrapper.cpp:1411` pins `std::fixed << setprecision(6)`, so the parsed
value *is* a 1e-6 band — no invented constant. Two agents' `star-4` rows
disagree on the **sign** of their 1e-9 margin, which is direct evidence that
sub-1e-6 differences are noise.

**`hull_coverage` is deliberately NOT a key.** No measured arm reaches it, and
per `COORDINATION.md` §4.1 a key no input exercises is vacuous. Ship it later
with a real exercising input, or not at all.

**K3 and K4 are exercised by real data** — `hshape` eliminates `seeded_1`/`2` at
K3 after a K2 tie and `seeded_0`/`3` at K4; `star-4-sym` eliminates `seeded_3`
(sw 2) against control (sw 0) at K4.

### 4.1 Required-fail inputs (`COORDINATION.md` §4.1)

| id | input | must |
|---|---|---|
| **R1** | `mesh-humanoid / canonical` — bijective, residual 0.000000, **largest cardinality of any arm (50/50)**, scale 0.598116 | **LOSE.** "First bijection wins", "most matched vertices wins" and "lowest residual wins" all pick it |
| **R2** | `hshape / seeded_2` — beats control by 2.3e-9 raw and is **not** a bijection (10/12) | **LOSE.** Pins "rank the parsed 6-dp value" |
| **R3** | `star-4-sym / seeded_3` — ties at 6 dp, breaks `cp_symmetric` (sw 0 → 2) | **LOSE** at K4 |
| **R4** | scale-maximal arm carrying `stub_flaps > 0` (constructed) | **LOSE.** Pins K1 above K2 |
| **R5** | `{A: scale 0.70, cov 0.95}` vs `{B: scale 0.75, cov 0.40}` (constructed) | pick **B**. Coverage never buys a scale loss |
| **R6** | fold whose `frame_title` carries no `scale=` (constructed) | **REFUSE**, fall back byte-identically |

⚠ **Latent hazard behind R6:** `fold_meta._SCALE_RE` silently mis-parses
scientific notation (`scale=1e-05` → `1.0`). Safe only because the emitter pins
`%.6f`. Once scale is a *selector* key, an emitter format change becomes a wrong
**serve**, not a wrong report. **Pin the emitter format in a test next to the
parser.**

---

## 5. What actually changes

Running the rule over all 154 arms: 12 serves change, 3 cosmetically. **With the
§2.1 predicate gate, 8 genuine changes, all strict improvements bar one trade:**

| subject | serves | scale | coverage | bijection |
|---|---|---|---|---|
| **mesh-bird** | seeded_3 | 1.095885 → 1.515998 | 0.5000 → **0.9848** | False → **True** |
| cat-short-legs | seeded_1 | 0.691274 → 0.855158 | 0.6661 → 0.7696 | — |
| **mesh-humanoid** | seeded_1 | 0.701537 → 0.775554 | 0.6319 → 0.6638 | False → **True** |
| cat-spine3 | seeded_1 | 0.580389 → 0.674783 | 0.7473 → 0.8435 | — |
| dog-repaired | seeded_0 | 0.658547 → 0.748723 | 0.6571 → 0.7252 | — |
| cat-spine4 | seeded_0 | 0.405389 → 0.441149 | 0.7067 → 0.8389 | — |
| uneven-star | seeded_2 | 0.582852 → 0.632102 | 0.6379 → 0.7751 | — |
| cat-long-legs | seeded_0 | 0.489429 → 0.493232 | 0.8620 → **0.8041** ⚠ | — |

`two-level-tree` (+5.4% scale for the control's bijection and a third of its
coverage) is **excluded by the predicate gate** and must stay excluded.
`cat-long-legs` is the one real trade: **+0.8% scale for −0.058 coverage.**
§1.1(4)-sanctioned in direction, but it is a trade and the PR must argue it.

`cp_symmetric` is neither gained nor lost on any of the eight. The three
subjects that are `cp_symmetric` today — `hshape`, `star-3`, `star-4-sym` — are
untouched.

---

## 6. The "deterministic" rationale does not reach this change

`server.py:1516`'s early return is deliberate, so it was traced. `git log -S` →
commit **2e39884** (2026-06-14), when the only rescue was ±10% edge-weight
jitter: *"the user's EXACT tree is always attempt 0, so a base that already
compiles is returned untouched and geometry stays deterministic; jitter fires
only when there is no exact base to lose."*

**It protects the user's PROPORTIONS from a random nudge. An order variant moves
no length.** `rescue_ladder.PRESERVING_STAGES` already places `STAGE_ORDER`
alongside `STAGE_EXACT`.

**The HITL clause is measurably vacuous.** *"A dirty exact tree surfaces HITL
through the classified lint verdict, never a server-side retry"* — all 9 corpus
trees that pack at attempt-0 are cp-audit **clean**. The condition it defers on
never occurs, while the mirror defect it never contemplated is present on four
of those nine.

---

## 7. Risks

### 7.1 🛑 BLOCKER — the mark-or-don't-mark fork, and the bird headline

Does a re-ranked serve get marked as rescued? **Both answers cost.**

* **Unmarked:** `agent_loop.py:316-325` tells the model that an unmarked
  `frame_title` means the tree packed exactly — that becomes a lie.
  `capture.record` mislabels the 2.4 retrain corpus as `STAGE_EXACT`.
* **Marked:** `mesh_to_tree.py:1586,1608`'s terminal early-exit
  `fid >= 1.0 and stage == "none"` stops firing, which **re-times the extraction
  drain and changes bird's extracted tree** — measured, 6 nodes / pairs
  `[[4,2]]` → 8 nodes / pairs `[[7,5]]`, reproducible on stock and patched.

⇒ **`mesh-bird`'s +38.3% / +97% was measured on the tree the STOCK drain
extracts. It is not yet a shipping number.** Re-measure end-to-end after the
marking decision, before quoting it again. **This is the one thing that must be
settled before dispatch.**

### 7.2 The suite has no serve-path byte pin for attempt-0 packers

The patched serve silently changes `dog-repaired`'s fold (sha1 `7a3aed84…` →
`e4d75f4a…`, scale 0.658547 → 0.748723) with **zero test failures**, and
`read_base()` cannot see it — stage stays `"none"` and `shadow_diff` is
id-set + leaf-path-length based, so a pure reorder is invisible **by
construction**. **Ship the pin before the behaviour change**, or the next
regression is invisible.

### 7.3 Blast radius is small — measured, 31 files / 568 tests, both arms

**Exactly 2 failures**, both `test_cp_mirror_serve.py::
test_mesh_validation_tree_verdicts_are_pinned` — `[bird]` (residual 0.053492 →
0.0) and `[humanoid]` (0.378336 → 0.0). Both are **improvements requiring a
re-bless of a red pin.** Everything feared survives: `test_templates_attempt0`,
`test_read_base::test_attempt0_unchanged`, `test_raw_dog_still_fails_clean`,
`test_dog_ladder_rescue`, all 39 of `test_ladder_audit`, and
`test_verdicts`/`test_geometry`/`test_determinism` (they use the ladder-free
`tests/runner.py`).

### 7.4 Cross-goal

`hull_coverage` and `design_scale` are **Goal 1's columns** and this slice moves
both on eight subjects. Goal 1 has been offered ownership in `COORDINATION.md`
§5. Whoever ships it, the frozen-scorecard delta must attribute every moved row
here — and `mesh-quadruped`'s coverage is **not** among them (its win is depth-2
and out of scope).

---

## 8. Prior art (CLAUDE.md §0)

| verdict | item | why |
|---|---|---|
| **ADOPT** | Multi-start / restart selection in global optimization — best-of-N over first-feasible | Exactly this problem at N=6. The cost model (pay N to rank N) is what §2.2's batching answers |
| **ADAPT** | `_search_first_clean`'s existing cp-audit-cleanliness rank | The codebase already ranks on one axis; this extends a selector rather than introducing one |
| **REJECT** | Algorithm portfolios / SATzilla-style learned selection | At N=5 exhaustive-then-rank dominates, and this project already measured a learned gate's retrain as **NO SHIP** (2026-07-31) when its apparent signal proved an `n_leaves` confound |
| **REJECT** | Lang's star-5 0.3536 as this lever's ceiling | **Measured null:** all five `star-5` arms are **bit-identical** at 0.323556, as are all five `star-4` arms at 0.5000000009. `order_variants` permutes the node *list* and the wrapper seeds node *i* at `r = 0.10+0.03·i, θ = 2.39996·i`, so permuting interchangeable leaves gives a **congruent** start. Node-order restarts explore permutations of one fixed spiral; **Lang's lever is leaf POSITIONS.** Different levers — CLAUDE.md §1.1(4) stands unamended |
| **HONEST NEGATIVE** | No literature found on selecting among *node orderings* for a tree-method origami packer | The restart-selection framing is generic; the domain instance is ours alone. No external oracle for what "better" means here — which is why §4.1's required-fail inputs are drawn from real corpus arms rather than theory |

---

## 9. Open

1. **§7.1's marking fork** — blocks dispatch.
2. Ownership: Goal 1 or Goal 2 (§7.4).
3. `mesh-quadruped`'s depth-2 win (+19.7%, bijection, 3 stub flaps eliminated)
   is real and reproducible but **out of scope**. Record it; do not chase it
   with nested serves.

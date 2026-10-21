# S2′b — σ-symmetric M/V search. Implementation findings.

**This fixes humanoid and `template-bird`. It does NOT fix the dog, quadruped
or insect — no relabel-only fix exists for those, and that is now a proof.
⚠ And it does NOT fix `mesh-bird` either, which corrects the slice's own
headline — see finding 2.**

> **REBASED ONTO `01134cd` (post-S6).** §§1–9 were measured at `1e4182c` and
> all of their counts still hold — S6 serves exactly the folds these fixtures
> pin, verified by fingerprint. **§11 is superseded by §13**: S2′b is now LIVE
> on the scorecard. Read §13 first.

Built on `1e4182c` (main, post-S2′a #93). Reported here for transcription; this
session does not edit `COORDINATION.md` or the specs.

Module: [`mcp_harness/mv_symmetrize.py`](../../../../mcp_harness/mv_symmetrize.py) ·
tests: [`tests/test_mv_symmetrize.py`](../../../../mcp_harness/tests/test_mv_symmetrize.py) ·
fixtures: `tests/fixtures/mv_symmetrize/*.fold` (pinned by CONTENT, per §9's
subject-identity rule).

---

## 1. Every number in spec §9.2 reproduced, and the intermediates it lacks

Three-conjunct gate (`symmetric` ∧ `cp_audit.clean` ∧ `layer_order`), the gate
§9.2's counts were taken under. Full enumeration by pruned σ-orbit DFS.

| fold | orbits (sw/pr/fx) | space | Maekawa-clean | audit-clean | **layer-consistent** | §9.2 says |
|---|---|---|---|---|---|---|
| `mesh-humanoid__seeded_1` | 13 (1/6/6) | 2^13 | 72 | 8 | **8** ✅ | 8 |
| `mesh-bird__seeded_3` | 12 (2/5/5) | 2^12 | 60 | 6 | **6** ✅ | 6 |
| `template-bird__CONTROL` | 19 (1/10/8) | 2^19 | 576 | 8 | **8** ✅ | 8 |
| `template-quadruped__CONTROL` | 19 (1/10/8) | 2^19 | 576 | **8** | **0** ✅ | 0 |
| `mesh-insect__CONTROL` | 28 (3/17/8) | **2^28** | 8,640 | **72** | **0** ✅ | (unmeasured) |

All five orbit censuses match §9.2 to the integer. Zero fast-vs-slow
mismatches on every subject, checked in **both** directions (below).

**`mesh-insect` is EXHAUSTED, not sampled.** 2^28 = 268,435,456 points reduced
to **167,100 DFS nodes in 3.12 s**. Its 0 is now the same kind of object as the
dog's.

**Record quadruped's and insect's intermediate, not just the 0.** Both have a
non-empty audit-clean set (8 and 72) and lose all of it at `layer_order`. "0
targets" reads as "no symmetric foldable relabel exists"; the true claim is
narrower and located — *symmetric, flat-foldable-at-every-vertex relabels
exist, and every one of them is refuted by the non-crossing oracle.*

## 2. ⚠ CORRECTION TO THE HEADLINE — conjunct 4 removes ALL SIX `mesh-bird` targets

The fourth conjunct is "the shipped Oriedita lint class is not worsened".
Measured:

| fold | base lint | layer-consistent | **lint-ok (4-conjunct)** |
|---|---|---|---|
| `mesh-humanoid__seeded_1` | Pass | 8 | **8** — all eight also lint Pass |
| `template-bird__CONTROL` | Pass | 8 | **4** |
| `mesh-bird__seeded_3` | Pass | 6 | **0** |

All six bird targets flip Oriedita **Pass → FAIL-LINT[BENIGN]**, and all six
carry the identical detail: `1 vertex violation (0 M/V-fixable, 1 geometry;
0 hull-boundary, 1 numeric-noise, 0 real-interior)` — `real = 0` — and the
classifier's own closing line on every one is *"The pattern is flat-foldable
as-is. ACCEPT."*

**The offender is the one vertex where symmetrization is most consequential.**
It is `v2` at paper `(0.504707669, 0.504707669)` — exactly on the 45° axis, so
σ **fixes** it. Symmetrizing inverts its ring from **M3/V1 to M1/V3**. Oriedita
calls that `ANGLES (Kawasaki)` at ~1e-6°; our own re-audit measures that
vertex's Kawasaki residual at **exactly 0.0**, with parity and arrangement both
OK, on both the base and every candidate.

Two candidate readings, and this session does not pick between them:

* **Oriedita noise.** 1e-6° is eleven orders inside `KAWASAKI_TOL_DEG`, the
  classifier scores it `real=0` and says ACCEPT, and Oriedita's rule labels are
  already on record as unreliable in exactly this direction (an M/V-parity
  defect reported as `ANGLES (Kawasaki) [real]`).
* **Conjunct 4 is specified on the wrong axis.** It gates on lint CLASS;
  `mv_repair.jvm_improving` gates the same linter on the **`real` count** with
  rank only as a guard. On the `real` axis all six bird targets are
  non-worsening and bird would read 6.

⇒ **Planning decision needed: should conjunct 4 rank on `real` or on class?**
It is worth exactly one scorecard subject. The gate is implemented **as
specified** (class), because loosening a gate to make a headline come true is
the failure mode this project keeps recording. Pinned by
`test_conjunct_4_removes_every_mesh_bird_target_and_why`.

## 3. The required-fail input is REJECTED — and it now fails TWO conjuncts

`template-quadruped` flips `{17, 27}`, verbatim:

```
conjunct 1  mirror_verdict.symmetric = True   (mv_swapped 0, mv_mismatched 0)
conjunct 2  cp_audit.clean           = False  <-- maekawa 1, kawasaki 0, arrangement 0
conjunct 3  layer_order              = contradiction: taco-taco (1, 3)x(0, 3)
GATE VERDICT                         = REJECTED
  maekawa offender: vertex 3 degree 4 M=2 V=2 |M-V|=0 (Maekawa wants 2)
```

**⚠ §3 records conjunct 3 as `layer_order` OK. That reading is now stale, and
the mechanism is a trap worth recording.** Stripping exactly the 38 flat-edge
constraints S2′a added to this subject (`layer_order.needs_flat_edge`)
restores `consistent` — so the old reading reproduces exactly, and the count 38
matches §2's measured gap for quadruped. But the refutation is reported as
**`taco-taco`, a family S2′a never touched**: `_propagate` only decides a
taco-taco check once all four of its literals are known, and the added
equalities force enough extra literals to make a **pre-existing** check fire.

⇒ **S2′a's constraints can change verdicts through OLD provenance. Anyone
attributing refutations by provenance string will mis-attribute this one.**
Pinned by `test_S2a_constraints_can_refute_through_PRE_EXISTING_provenance`.

**Conjunct 2 is still load-bearing, measured on the live space** — the
retracted target failing two conjuncts does not make `cp_audit` redundant:

| fold | symmetric | layer-consistent | of which cp_audit **DIRTY** |
|---|---|---|---|
| `mesh-humanoid__seeded_1` | 8192 | 24 | **16** |
| `mesh-bird__seeded_3` | 4096 | 12 | **6** |

A symmetry + `layer_order` gate would serve unfoldable paper on **two thirds**
of what it accepts for humanoid.

## 4. The space-size assertion

With s swapped / p preserved / f σ-fixed orbits, every one of the `2^(s+p+f)`
points must score `mv_swapped == 0`.

| fold | space | walked | symmetric | mode |
|---|---|---|---|---|
| `mesh-humanoid__seeded_1` | 2^13 | 8192 | 8192 | EXHAUSTIVE |
| `mesh-bird__seeded_3` | 2^12 | 4096 | 4096 | EXHAUSTIVE |
| `template-bird__CONTROL` | 2^19 | 2048 | 2048 | seeded sample |
| `template-quadruped__CONTROL` | 2^19 | 2048 | 2048 | seeded sample |
| `mesh-insect__CONTROL` | 2^28 | 2048 | 2048 | seeded sample |

Plus `_assert_two_resolutions`, which makes it exhaustive in O(n) rather than
O(2^n): symmetry is a **conjunction over orbits**, so checking that both
options of every orbit leave that orbit σ-consistent proves all 2^n points
symmetric. That is the halving bug as an assertion — a swapped orbit encoded
as "flip A, or don't" has an option (`{}`) that leaves the pair swapped, and it
raises on it.

**Why the bug was invisible to a count check:** "flip A, or don't" still has
arity 2, so the enumeration is still 2^n points. What halves is the number of
those points that are *symmetric*.

## 5. The base is invariant — bit-identical, on every candidate

| fold | candidates | faces | closure | result |
|---|---|---|---|---|
| `mesh-humanoid__seeded_1` | 8 | 18 | 1.934e-09 | ALL BIT-IDENTICAL |
| `mesh-bird__seeded_3` | 6 | 16 | 7.251e-09 | ALL BIT-IDENTICAL |
| `template-bird__CONTROL` | 8 | 24 | 5.146e-10 | ALL BIT-IDENTICAL |

Face lists, face transforms (`tobytes`), folded vertices (`tobytes`), face
count and closure max-error/bad-edges. **Not** scoped to
`leaf_node_locations` — no call site reads `edges_assignment`, so that check
can confirm invariance and can never detect a violation. Also asserted on the
serve path end-to-end.

## 6. Verification of the fast paths — in BOTH directions

The DFS prunes on an incremental Maekawa/arrangement oracle and re-runs only
`layer_order._propagate` over re-seeded `direct` constraints. Both are
re-derivations, so both are checked:

* **wrongly ACCEPTS** — every audit-clean point re-run through
  `cp_audit.audit_fold` and `mv_repair._layer_status`. **0 mismatches**, all
  five subjects.
* **wrongly REFUTES** — the dangerous half, and the one a natural
  implementation omits: a too-tight prune drops a target and leaves nothing to
  re-check; the count just comes out lower and reads as "no target exists". On
  the two 2^12/2^13 subjects the whole space is enumerated against `cp_audit`
  and the sets compared. **The pruned DFS finds exactly what brute force
  finds.** Whatever the DFS reports on insect's 2^28 rests on that equivalence.
* `_LayerGate` asserts its re-derived `direct` seeds equal the shipped
  `_build_constraints` output on the unflipped fold — a drift guard, not a
  comment.

## 7. Ranking rule, and what it picks

`Candidate.rank_key`, ascending: **(1)** Oriedita lint class
(Pass 0 < BENIGN 1 < MIXED 2 < REAL 3 < UNCLASSIFIED 4); **(2)** real
violations, then unlocated; **(3)** weight — fewer relabelled creases, §5's
human-folder concern; **(4)** the flip tuple, for determinism.

| fold | winner | weight | lint | dropped by conjunct 4 |
|---|---|---|---|---|
| `mesh-humanoid__seeded_1` | `[8,9,17,18,21]` | 5 of 20 M/V (25.0%) | Pass | — |
| `template-bird__CONTROL` | `[8,9,10,13,17,24,25,26,27,40,45]` | 11 of 30 M/V (36.7%) | Pass | 4, incl. `[0,1,2,5,19,20,22,28,29,34,37]` |
| `mesh-bird__seeded_3` | **none** | — | — | all 6 |
| `template-quadruped`, `mesh-insect` | **none** | — | — | — |

**`template-bird` reproduces §9.2's reconciliation exactly**: 8 under three
conjuncts, 4 under four, and the discriminator between the kept
`[8,9,10,13,…]` and the dropped `[3,4,6,7,8,9,10,13,…]` is precisely the orbit
**`{3,4,6,7}`**. M/V census `M11/V19 → M16/V14`, matching §5.

### ⚠ The ranker has a required-fail input of its own, and it is my own code

With `lint=False` the key falls through to weight — and on `template-bird` the
PASS and BENIGN survivors **both weigh 11**, so lexicographic order picks
`[0,1,2,5,…]`, **the BENIGN one**. No better tie-break can fix it: the two are
identical on symmetry, `cp_audit`, `layer_order` **and** folded geometry, so
there is no lint-free discriminator to find. **For ranking, conjunct 4 is the
only signal.** Consequences, both shipped: the serve defaults conjunct 4 **ON**,
and `test_ranking_without_conjunct_4_picks_the_BENIGN_survivor` pins the
hazard so nobody later optimises the JVM call away.

## 8. ⚠ The serve insertion point is NOT where §8 says it is

§8 names `server.py:1569` / `:422`'s `meta["clean"] is False` short-circuit.
Both are real and both are patched — **but neither is the one S2′b's subjects
go through.** `_compile_with_perturb`'s attempt-0 branch returns the pack
UNTOUCHED (*"exact tree packed → return untouched (deterministic); no ladder
ran"*), and `template-bird`, `template-quadruped`, bird and humanoid all pack
at attempt 0. **That early return has no repair hook of any kind.** Changing
only the `meta["clean"]` condition would have shipped a hook that never
executed on any subject it was written for.

Three insertion points, all through one helper `_symmetrize_and_annotate`:

| # | site | reached by |
|---|---|---|
| **1** | `_compile_with_perturb`, attempt-0 early return | **every S2′b subject** |
| 2 | `_compile_with_perturb`, after the ladder's `mv_repair` block, **outside** the clean check | ladder-rescued serves |
| 3 | `_worker_compile_and_regions`, before the `ok` payload | the regions path |

Point 1 fires **after** `capture.record` and `_record_serve` on purpose: the
2.4 capture row must keep meaning "what did the raw compile do", so only the
returned bytes change. Points 2/3 add `perturb["mv_symmetrize"]` only when
non-None, so the perturb dict's exact-equality pins are untouched while the
flag is off.

**Default OFF (`IDE_MV_SYMMETRIZE=1` to enable), and the default is the
decision.** §5 leaves open whether relabelling 25–37% of a crease pattern is
what a human folder wants, and nobody has compared the new layer stacking to
the stock one. Byte-identical serve while off, pinned by test.

> 🛑 **THE DEFAULT IS NOW ON — see §14.** The paragraph above records why it
> shipped OFF and that reasoning is unchanged; what changed is the other side
> of the trade. `IDE_MV_SYMMETRIZE=0` is still byte-identical and still
> pinned.

## 9. Reproduce

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_mv_symmetrize.py -q
```

`measure_nolint.txt` / `measure_lint.txt` in this directory are the raw
harness output for §§1–7.

## 10. Suite, before and after — measured on THIS base commit

Neither number was taken from a quoted figure; both were run here, serially, on
a quiet host, with the baseline in its own `git worktree` at `1e4182c`.

| | collected | passed | skipped | **failed** | wall |
|---|---|---|---|---|---|
| **BEFORE** — `1e4182c`, pristine worktree | 2468 | 2457 | 11 | **0** | 19:49 |
| **AFTER** — this branch | 2503 | 2492 | 11 | **0** | 20:53 |

Delta **+35**, exactly `test_mv_symmetrize.py`; skips identical at 11; no test
removed or renamed (`--collect-only` differs by the same 35).

⚠ `main` at `1e4182c` is **GREEN**. The "main is RED" note in COORDINATION §5
was recorded at `a04cb0a`; `test_checkpoint_fallback_pins_the_served_tree_not_
the_request` passes here in a full-suite run on both arms.

### ⚠ A harness trap that cost 11.5 hours, and it is the project's own

Two earlier attempts at these runs were killed by a broad `pkill -f pytest`
issued by a **concurrent agent session** working in
`.claude/worktrees/origami-resume-review-4677d4`. The fix — a runner script
whose argv contains no `pytest` substring — then walked straight into
[the recorded trap](../../../../mcp_harness/server.py): the runner called
`pytest.main()` at MODULE level with no `if __name__ == "__main__":` guard.

`server._run_isolated` uses `mp.get_context("spawn")`, and **a spawn child
re-imports the `__main__` module** — so every spawned compile worker re-entered
`pytest.main()` and started a nested full-suite run. Symptom: the suite reached
**7% in 11.5 hours** and emitted blocks of timeout failures
(`test_auto_mesh_to_tree.py` and neighbours). Adding the guard took the same
suite to 8% in **5 minutes** and 0 failures.

**Those failure blocks were an artifact of the harness, not regressions** — the
green run above is the same code. Two lessons worth keeping:

* the `if __name__ == "__main__":` rule applies to **anything that ends up as
  `__main__` above a serve**, including a test runner — not only to probe
  scripts, which is how it is currently written down;
* **a shared host with other agent sessions is now a real condition of this
  repo.** Check `ps` for foreign `pytest` before trusting a slow gate, and do
  not assume a `pkill` is yours.

## 11. Frozen scorecard — `--baseline`, and what happens with the flag ON

> ## 🛑 SUPERSEDED BY §13 — MEASURED AT `1e4182c`, BEFORE S6 LANDED.
> The "byte-identical with the flag ON" result below was true of its base and
> is **false on `main`**. S6 (PR #94) gave `mesh-bird` and `mesh-humanoid`
> vertex bijections, so S2′b is **no longer dormant**. Kept unedited because
> the reasoning is still correct — *no scorecard subject had both a bijection
> and a target* — and what changed is the premise, not the logic. §13 is the
> live reading.

```
=== deltas vs fixtures/scorecard_baseline.jsonl ===
quadruped: design_scale: None -> 0.599702
bird:      design_scale: None -> 1.095885
humanoid:  design_scale: None -> 0.701537
fish:      design_scale: None -> 0.653249
insect:    design_scale: None -> 0.582125
```

Every move is a **column-addition** (`None -> value`), attributable to the
`design_scale` slice; **no value moved and no goal-owned axis moved.**
`hull_coverage` reproduces the frozen values exactly (0.7161 / 0.5 / 0.6319 /
0.9077 / 0.8595). `--out` was never passed.

**Re-run with `IDE_MV_SYMMETRIZE=1`: the delta table is BYTE-IDENTICAL**, and
zero `mv-symmetrize` markers appear in any served fold. That is §9.1's "today
ZERO scorecard subjects have both a bijection and a relabel-only target",
measured rather than predicted: `insect` is the only bijective row and it has 0
targets; the other four have no bijection, so `orbit_space` refuses at once.

⇒ **Turning this feature on today moves nothing on the frozen scorecard.** The
subjects it does fix (`mesh-humanoid__seeded_1`, `mesh-bird__seeded_3`) are
post-slice-A folds that the serve does not produce yet.

## 12. Production callers — declared, not orphaned

`mv_symmetrize` has real call sites: `server._symmetrize_and_annotate` at the
three points in §8, behind `IDE_MV_SYMMETRIZE` (default off) with the
four-conjunct gate's JVM sub-flag default ON. Stated explicitly because this
repo has already shipped one module with tests and **zero** production callers
(`tree_render`, an "undeclared tool"); a default-off but wired-and-tested
caller is a different object from that, and the difference should be argued
rather than assumed.

---

# 13. ⚠ RE-MEASURED POST-S6 — S2′b IS NO LONGER DORMANT

Rebased `1e4182c` → `01134cd`. S6 (PR #94) hooks the same attempt-0 branch and
**created the bijections S2′b needs**, so three things in §§1–12 had to be
re-checked. Two survived unchanged; one is overturned.

## 13.1 S6 serves EXACTLY the folds these fixtures pin — verified, not assumed

The fixtures were captured from a sweep when the post-slice-A folds were
hypothetical. They are now what production serves:

| subject | served | fixture | geometry fingerprint | assignments | rank marker |
|---|---|---|---|---|---|
| `bird` | 18v / 33e | `mesh-bird__seeded_3` | `7772b6daa00b3754` **==** | **identical** | present |
| `humanoid` | 21v / 38e | `mesh-humanoid__seeded_1` | `9efc6a0cbc5e9c7b` **==** | **identical** | present |

Both now read `is_bijection True`, `residual 0.0` (from 0.053492 / 0.378336),
carrying `mv_swapped` 4 and 2. **⇒ every target count in §1 was computed on the
fold that is actually served**, and the σ-orbit censuses on the served folds
reproduce exactly: bird 12 (2/5/5) → 60 / 6 / **6**, humanoid 13 (1/6/6) →
72 / 8 / **8**. Pinned by `test_S6_now_serves_exactly_the_folds_these_fixtures_pin`
— by fingerprint and assignment array, never by name.

## 13.2 The scorecard MOVES. §11's byte-identity result is retracted.

`--baseline` on the rebased base, both arms, `--out` never passed:

**Flag OFF** — everything here is **S6's** (#94), plus the `design_scale`
column-addition:

```
quadruped: design_scale: None -> 0.599702
bird:      lint_class: 'BENIGN' -> 'PASS'; hull_coverage: 0.5 -> 0.9848;
           design_scale: None -> 1.515998; cp_mirror_residual: 0.053492 -> 0.0;
           cp_mv_broken: None -> 4
humanoid:  lint_class: 'BENIGN' -> 'PASS'; hull_coverage: 0.6319 -> 0.6638;
           design_scale: None -> 0.775554; cp_mirror_residual: 0.378336 -> 0.0;
           cp_mv_broken: None -> 2
fish:      design_scale: None -> 0.653249
insect:    design_scale: None -> 0.582125
```

**Flag ON** — diffed against the above, **exactly one row differs, and only in
the two axes S2′b owns**:

```
humanoid:  ... cp_symmetric: False -> True ...; cp_mv_broken: None -> 0
                                                              (was -> 2)
```

**Attribution, line by line.** `design_scale` on all five rows → the
`design_scale` column-addition slice. Everything on the `bird` row, and
everything on the `humanoid` row except the two axes named above → **S6 / PR
#94** (that PR's own body records the residual figures and flags that it moves
Goal-2-owned columns). **`cp_symmetric False → True` and `cp_mv_broken 2 → 0`
on `humanoid`, and nothing else anywhere → S2′b.** No row is unattributable.

`serve_attempt0_pin.json` is **not re-blessed** by this branch — S6 already
moved it and that attribution is S6's.

## 13.3 What ships, and what does not

| subject | layer-consistent | conjunct-4 ok | outcome |
|---|---|---|---|
| `mesh-humanoid__seeded_1` | 8 | **8** | **ships** `[8,9,17,18,21]`, weight 5, M7/V13 → M10/V10; post-state symmetric ✓ cp_audit clean ✓ layer consistent ✓ |
| `mesh-bird__seeded_3` | 6 | **0** | **nothing ships** — all six dropped at BENIGN, `real=0` |

## 13.4 ⚠ The conjunct-4 cost is now LOAD-BEARING — reported, not resolved

The planner ruled conjunct 4 stays STRICT partly *because* the decision was not
yet load-bearing: `mesh-bird` had no bijection, so no orbit set. **S6 gave it
one.** The six discarded targets are now six foldable, symmetric, cp-audit-clean
assignments that a **real scorecard subject does not get** — and the scorecard
shows it directly: humanoid moves `cp_symmetric False → True`, bird does not
move at all.

The evidence is unchanged from §2 and still points the same way: all six are
`real = 0`, one *numeric-noise* violation, the classifier's own line is *"The
pattern is flat-foldable as-is. ACCEPT."*, and the offending vertex is the
σ-**fixed** one on the mirror axis whose Kawasaki residual our own oracle
measures at exactly 0.0. What changed is only the price of the ruling. **The
gate is left exactly as specified.**

## 13.5 The two hooks compose in one direction, pinned

S6 fires only when the control is **not** a bijection and can **create** one;
S2′b needs a bijection to have any orbits. So the resolution is
**rank first, then symmetrize, on the fold S6 chose** —
`_symmetrize_and_annotate(served_result)`, never `result`.

Symmetrizing the control instead would compute flip indices against a fold
about to be discarded, and `apply_flips`' sha256 fingerprint guard would then
**refuse** them: the slice would read as *inert*, not as broken. That is why
the ordering is a test and not a comment
(`test_symmetrize_runs_on_S6s_chosen_fold_not_the_control`, which spies on the
hook's actual input and asserts it carries S6's rank marker).

**Both invariants still hold together**: S6 is byte-identical to its pre-S6 self
when `rank_variants` is None, S2′b when `IDE_MV_SYMMETRIZE` is off, and with
both defaults off the composed serve is byte-identical — asserted on a subject
S6 re-ranks (`dog-repaired`) and one it does not (`hshape`), by
`test_both_defaults_off_compose_to_a_byte_identical_serve`.

## 13.6 Suite, re-established on the REBASED base

Both arms run here, serially, with the baseline in its own `git worktree` at
`01134cd`. No count was carried over from the pre-rebase run.

| | passed | skipped | **failed** | wall |
|---|---|---|---|---|
| **BEFORE** — `01134cd` (main, post-S6) | 2473 | 11 | **0** | 19:28 |
| **AFTER** — this branch | 2511 | 11 | **0** | 20:07 |

Delta **+38**, exactly `test_mv_symmetrize.py` (35 at `1e4182c`, plus the three
S6-composition tests added on rebase). Skips identical. `main` at `01134cd` is
green.

## 13.7 What did NOT need re-measuring, and why

| §  | claim | status post-S6 |
|---|---|---|
| 1 | target counts / orbit censuses | **unchanged** — S6 serves exactly these folds (13.1) |
| 3 | `{17,27}` rejected, two conjuncts | **unchanged** — `template-quadruped` does not pack at attempt 0, so S6's gate never sees it |
| 4 | space-size assertion | **unchanged** — a property of the orbit construction, not of the serve |
| 5 | base invariance | **unchanged** — `flat_fold` is M/V-blind; re-asserted on the serve path |
| 6 | fast-path verification, both directions | **unchanged** — re-run green |
| 7 | ranking rule and picks | **unchanged**; humanoid's winner is what now ships |
| 11 | flag-ON scorecard byte-identical | **🛑 RETRACTED — see 13.2** |

---

# 14. ⚠ THE DEFAULT IS NOW ON (U4′), AND §13 IS SUPERSEDED IN THREE PLACES

Measured on the U1′ (root-rank, PR #107) packs. §§1–12's counts are all still
reproducible on the folds they name; what moved is which folds the serve
produces, and therefore what the flag is worth.

## 14.1 The full served-fold census — all five subjects, not just the winner

| subject | root | bijection | mv_swapped | σ-orbits | 3-conj | 4-conj | outcome |
|---|---|---|---|---|---|---|---|
| `quadruped` | 5 | yes | 10 | **64 (2⁶⁴)** | — | — | **REFUSED** `orbit_space_too_large` |
| `bird` | control | yes | 4 | 12 | 6 | **0** | unmoved — §13.4's ruling holds |
| `humanoid` | 2 | yes | **0** | 13 | 8 | 8 | winner is the **EMPTY flip set** |
| `fish` | — | **no** | — | — | — | — | `no_bijection` |
| `insect` | 6 | yes | **2** | 28 | **12** | **12** | **ships**, 17 creases |

§13.3's table is superseded: humanoid no longer needs a relabel at all (U1′
re-rooted it symmetric, so the search's lightest winner is `()` and the fold is
returned untouched), and **`insect` — which §1 recorded as an exhausted 0 —
now carries twelve targets under both gates.** Its 0 was a true statement about
a fold the serve no longer produces. That is §9's subject-identity rule biting
a fourth time, and the new fixtures are committed by content beside the old
ones rather than replacing them.

## 14.2 The scorecard delta, and it is one subject

Both arms run back-to-back on one machine, `--out` never passed. Diffed against
each other, **the `insect` row is the only difference**:

```
insect: cp_symmetric: False -> True; cp_mv_broken: 6 -> 2  =>  6 -> 0;
        lint_class: 'BENIGN' -> 'PASS'
```

Everything else on all five rows is byte-identical between the arms and belongs
to U1′/U2′/U3′, S6 and the `design_scale` column-addition.

## 14.3 ⚠ QUADRUPED WAS A SILENT NO-OP FOR THE WHOLE LIFE OF THE FLAG

At the shipped `NODE_BUDGET`/`DEADLINE_S`, `search` on the served quadruped
raises `AssertionError: the arrangement prune emitted a point the Maekawa
census did not` **after 292.4 s** — the subset check between the census and the
pruned walk is a theorem about two COMPLETE walks, and both truncate on a 2⁶⁴
space. `server._symmetrize_and_annotate` catches `Exception`, so this cost five
minutes per serve and left no trace anywhere.

Three fixes, none of which unbounds the search:

* `MAX_ORBITS = 40` — refuse **by name** before any DFS (largest measured
  exhaustive search is `mesh-dog`'s 2³⁵/692,867 nodes);
* the subset assertion is conditional on exhaustion, and a truncated search
  **refuses** rather than ranking — a determinism fix, since which candidates a
  DFS reaches before a wall-clock cap is a property of the HOST;
* `MV_SYMMETRIZE_SKIP_MARKER` on the fold + an `mv_symmetrize` key on
  `read_base()`, written ONLY for "we could not look". **A refusal is not a
  zero** — `no_bijection`, `blocked_orbits` and `base_not_relabel_fixable` are
  answers and get no note.

## 14.4 ⚠ §13.5's COMPOSITION ORDER IS SUPERSEDED — IT IS A CHAIN, NOT A NEST

§13.5 pins "rank first, then symmetrize, on the fold S6 chose" and that is
still true of S6. U1′ then put a THIRD stage in front of both, and because
S2′b's hooks live inside `_compile_with_perturb` — which the root stage calls
once per candidate — default-ON handed `root_rank` folds it had already
relabelled. Measured:

* **`template-bird` stopped calling `root_rank.rank` at all.** The stage skips
  when "the control is ALREADY mirror-symmetric"; with the relabeller running
  first, that gate fired on symmetry S2′b had just installed and the whole
  rooting search switched itself off.
* **`humanoid` (root 2 → control)** and **`template-quadruped` (control → root
  1)** changed which rooting they serve — K4 measures the PACKER's M/V defect
  and pre-symmetrizing zeroes it.

`server.mv_symmetrize_suppressed()` closes it. The order is

    root (U1′) → order (S6) → relabel (S2′b, ONCE, on what they settled on)

pinned by `test_THREE_hooks_compose_in_the_documented_order`, which asserts
`rank` still runs and that no relabel lands before it. `root_rank.py` and
`_rank_roots` are untouched.

## 14.5 §8's "default OFF is the decision" — the decision, taken

The open question §8 records (is relabelling 25–37% of a crease pattern what a
human folder wants?) is **not** answered here; what changed is that the flag
now buys a real scorecard subject instead of none. `IDE_MV_SYMMETRIZE=0`
remains byte-identical to the pre-S2′b serve and remains pinned by test —
rewritten from `test_both_defaults_off_compose_to_a_byte_identical_serve`,
whose old form asserted `delenv == setenv("0")` and so could only have been
kept green by asserting the very default this slice changes.

## 14.6 ⚠ §8's THREE INSERTION POINTS WERE ALWAYS FOUR

§8 lists three, and the third (`_worker_compile_and_regions`, "the regions
path") is only in that worker's LADDER branch. That worker has an attempt-0
early return of its own — the child's copy of the very short-circuit §8 is
about — and it had no relabel hook at all.

Consequence, measured: with the flag on, the parent symmetrized `STAR4`'s
attempt-0 fold and the child did not, so the two compile paths served
different bytes for the same tree. That is what `_run_ladder_child`'s docstring
forbids ("the two compile paths must not disagree about which rung serves a
tree") and what `test_read_base.py::test_child_and_parent_paths_agree_attempt0`
exists to catch — and it caught it.

**The gap is older than U4′; the default-OFF flag is the only reason it had
never fired.** It is the same shape as §8's own finding, one level down: an
attempt-0 branch that predates every repair stage and that nobody re-read when
one was added. Both attempt-0 branches now carry the hook.

# 15. ⚠ EARLY-EXIT (U6′) — `MAX_ORBITS` WAS RATIONING VALIDATION, NOT SEARCH

`MAX_ORBITS` is named, documented and derived as a bound on **search size**:
its "WHY 40" paragraph lists DFS node counts, largest first. PR #124 measured
the served `quadruped`'s 2⁴⁵ space directly and the premise does not hold.

| phase | cost |
|---|---|
| DFS, both passes, 1,382,884 nodes | **≤ 2.00 s** |
| `_LayerGate` build | 0.48 s |
| gate sweep over **288** audit-clean points | **16.58 s** |
| JVM lint (conjunct 4) | 2.94 s |
| **four-conjunct total, median of 5** | **22.15 s** |

The search is 9% of the cost. The other 91% is validating every audit-clean
point — and it is exhaustive **only so `Candidate.rank_key` can be applied**.
`search(..., first_valid=True)` stops at the first point of the (fixed)
enumeration passing all four conjuncts.

## 15.1 The measurement, against PR #124's own bar

`probe_first_valid.py`, `fixtures/first_valid_budget.json`, same served fold
(fingerprint `bf7dd0900c1a5587`, root 8), same 10 s bar:

| | exhaustive (PR #124) | **first_valid** |
|---|---|---|
| end-to-end, four-conjunct | 22.145 s (median of 5) | **1.336 s** (median of **7**; min 1.324, max 1.343) |
| DFS nodes | 1,382,884 | **1,037** |
| audit-clean points validated | 288 | **7** |
| winner | `[50,54,80,88,104,118]`, w6 | **identical** |

**16.5× faster, and the same candidate.** Not near the bar — 7.5× inside it,
with a 19 ms spread across seven runs at loadavg ≈ 2.3.

## 15.2 ⚠ THE WINNERS AGREE ON `quadruped` AND **DISAGREE ELSEWHERE** — measured

The quadruped agreement is a fact about that fold, **not** a general property,
and reporting it alone would have been the more comfortable half. Measured on
the committed fixtures through the four-conjunct gate:

| fold | ranked winner | first-valid winner | same? |
|---|---|---|---|
| served `quadruped` (45 orbits) | w**6** | w**6**, same flips | ✅ |
| `template-bird__CONTROL` (19) | w11, PASS | w11, same flips | ✅ |
| `mesh-bird__seeded_3` (12) | none (conjunct 4 drops all 6) | none | ✅ |
| `template-quadruped__CONTROL` (19) | none | none | ✅ |
| `mesh-insect__CONTROL` (28) | none | none | ✅ |
| **`mesh-humanoid__seeded_1` (13)** | **w5** `[8,9,17,18,21]` | **w7** `[0,5,9,12,14,26,27]` | ❌ |

On `mesh-humanoid__seeded_1` all 8 four-conjunct targets lint **PASS**, so
`rank_key`'s conjuncts 1–2 tie and **weight is the only discriminator**.
First-valid ships **two extra relabelled creases** on a fold whose exhaustive
gate costs a fraction of a second. Section 5's own concern — a wider relabel is
a visibly different crease pattern to a human folder, not a touch-up.

**Why `quadruped` agrees anyway.** All 24 of its four-conjunct targets lint
BENIGN (`ranked_lint_ranks: [1]`) and its weights run 6…73; the DFS's first
leaf is the all-`options[0]` point, and `options[0]` is the *no-flip*
resolution of every preserved and σ-fixed orbit, so low-weight points are
concentrated at the start of the walk. That is a **bias, not a guarantee** —
lexicographic order over the choice vector is not weight order globally, which
is exactly what `mesh-humanoid__seeded_1` demonstrates.

## 15.3 The consequence: a two-tier ceiling, not a switch

⇒ The serve **ranks at or below `MAX_RANKED_ORBITS = 40` and early-exits only
above it**. Every fold that serves a ranked winner today keeps serving
byte-identical bytes; above 40 the alternative was never a ranked winner but a
**refusal**, so early-exit there costs nothing that was being served.

40 is the *old* `MAX_ORBITS`, and that is the derivation, not a coincidence: it
is precisely where shipped behaviour changed from "ranked winner" to
"refusal", so it is the unique boundary with zero regression surface.
`MAX_ORBITS` becomes **45** — `quadruped`'s own orbit count, **no margin**,
because a margin is an advance admission of folds nobody has measured. PR #124
proposed 48; the band (40, 48] was re-verified empty of everything but
`quadruped`, and 45 is preferred so a future 46-orbit fold must re-run the
probe rather than inherit three spare orbits.

## 15.4 What the mode may NOT do, and how each is pinned

* **No conjunct is weakened.** Conjunct 4 stays a *filter*
  (`lint_rank <= base_lint_rank`), not merely a rank key — pinned by
  `mesh-bird__seeded_3`, which returns a winner at `lint=False` and **none** at
  `lint=True`. Conjunct 3 still bites — `template-quadruped__CONTROL` has 8
  audit-clean points and 0 layer-consistent ones and must return **none**.
* **A deliberate stop is not a truncation.** `FIRST_VALID_STOP` is a distinct
  stop word; a node-budget or deadline overrun **still** returns
  `search_truncated`, because *that* stop lands wherever the host got to
  (PR #119). Pinned from both sides on one fold.
* **The counts are a PREFIX, and say so.** `counts_are_census` is `False` on a
  hit, `n_maekawa_clean` is `None` (the census pass is skipped, and `0` would
  read as "counted, and empty") — and `True` when the walk *finishes* without a
  hit, where the zero is a proof of the same kind as mesh-dog's.
* **The provenance note does not claim a ranking it did not do.** The served
  `frame_title` reads *"FIRST valid candidate in enumeration order… (EARLY EXIT
  — that is not a target count)"*. The exhaustive branch is byte-identical to
  the pre-U6′ sentence, pinned as an exact string, because re-wording it would
  move the bytes of every subject that symmetrizes today.
* **`verify_slow_path` is refused** in combination — it is an inherently
  exhaustive both-directions claim (§6) and over a prefix it would report a
  vacuous 0.
* **`rank_key` is provably not consulted**: monkeypatching it to raise leaves
  `first_valid` working and takes the exhaustive path down.

## 15.5 Determinism — the precondition, not a bonus

"First" is only a stable answer because the enumeration order is fixed:
`orbit_space` iterates `sorted(emap)`, `_order_orbits` breaks every tie on the
orbit index, `_dfs` walks `ordered` in order taking `orbit.options` in order,
and no set of **strings** is iterated on that path (int hashing is not
randomised). Measured, not argued: **9 samples — 7 in-process + 2 fresh
interpreters at `PYTHONHASHSEED` 0 and 12345 — one flip set, one DFS node
count, one points-examined count**, with the children returning `hash(str)` to
prove the seeds actually differed.

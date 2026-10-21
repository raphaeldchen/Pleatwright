# COrigami F.1.1 steps 3-4: a selection filter on dense pleat candidates (gap 1, Phase A)

**Status: Tasks 1-3 IMPLEMENTED (committed and inert); Phase A HALTED 2026-09-27
by the measurement that should have come first.** Task 4, the activation, was
**not** committed, and its work is **not preserved in this repository**: it
exists only as `.superpowers/sdd/task-4-wip.diff` in the author's local scratch
directory, which is git-ignored and tracked nowhere, so no other clone has it.
Treat the activation as unavailable rather than recoverable.
The filter is a **no-op** at COrigami's own unit of selection (a segment: 100% of
`lizard`'s 4,488 dense candidates retained) and **destructive** below it (408 of
454 fully-bound interior vertices go odd, and `assign(dense=True,
filter_pleats=True)` fails as `AssignFail(kind='maekawa_fixed', site=(1, 21))`).
**Section 1's premise is refuted and this design must not be implemented on the
strength of it.** Full result: `../evidence/2026-09-27-pleat-filter/README.md`.

**Original status:** design approved 2026-09-27. Additive to
`2026-09-24-dense-pleats-design.md`. Supersedes that spec's section 3 decision
to reject "F.1.1 steps 1-4" as a bundle, for steps 3-4 only; steps 1-2 stay
rejected for the reason given there.

**Goal.** Dense mode currently creases **every** `axial`/`elev` piece. COrigami
filters. Build the filter, gated so nothing existing changes, and measure
whether a filtered dense pattern can reach a layer order -- which no unfiltered
dense pattern ever has.

---

## 1. The measurement this starts from

⚠ **WITHDRAWN 2026-09-27. The table's percentages are correct at UNIT-PIECE
granularity; the conclusion drawn from them is refuted.** COrigami's step 2 splits
the grid into candidate **segments** at every intersection with hinges and ridges,
so step 3 selects segments, not unit pieces. At that unit the filter retains
**100%** of `lizard`'s 4,488 dense candidates (365 collinear runs, 365 retained) —
a no-op — and below it the per-piece predicate truncates pleats mid-sheet,
dropping crease degree to 1 and making Maekawa's `|M − V| = 2` unsatisfiable at
408 of 454 fully-bound interior vertices. See
`../evidence/2026-09-27-pleat-filter/README.md`. **Nothing in this section
supports building the filter.** Original text unchanged below.

`evidence/2026-09-26-gap1-phase0/` applied F.1.1 step 3 as a **classifier** to
real dense candidates:

| subject | N | dense candidates | step 3 retains | % |
|---|---|---|---|---|
| `starfish` | 4 | 54 | 28 | 51.9% |
| `lizard` | 34 | 4,488 | 432 | **9.6%** |
| `frog` | 38 | 5,638 | 545 | **9.7%** |
| `horse` | 46 | 8,330 | 864 | **10.4%** |
| `bird` | 54 | 11,534 | 841 | **7.3%** |
| `guinea_pig` | 64 | 16,174 | 901 | **5.6%** |

**The filter would reject ~90% of what dense mode creases today**, and the
retained count is nearly FLAT in absolute terms (432, 545, 864, 841, 901) while
candidates grow 4,488 to 16,174. Candidates scale with the **grid area**
(O(N²)); a hinge-keyed filter scales with the tree's **structure**. So dense
mode is not uniformly ~10x too dense -- it gets monotonically worse with size.

⚠ **Both claims in that paragraph are WITHDRAWN 2026-09-27** (see the block at the
head of this section): the "~90%" and the size-dependent worsening are artefacts of
measuring at unit-piece rather than segment granularity. At the paper's own unit
the filter rejects **nothing** on `lizard` — 365 of 365 collinear runs retained —
so there is no 90% cut to scale with size.
`../evidence/2026-09-27-pleat-filter/README.md`.

**Variable census** (`phase0.json`, read from production's own `var_of`):
`elev` variables are **43-53%** of the CSP on every substantial subject, and
they are exactly what this filter cuts.

**Why nobody noticed.** `2026-09-24-dense-pleats-design.md` section 3 rejected
"F.1.1 steps 1-4" as a bundle, on the true grounds that `contours.py` already
supplies the elevation field steps 1-2 would build. **Steps 3-4 are not about
elevations -- they are a selection filter**, and nothing replaced them. That
spec booked the cost of the rejection as too LITTLE coverage ("54.7% of the
half-grid", a statement about steps 1-2) and never as too MANY creases.
`pleat_paths`' own docstring states the consequence: `dense=True` *"removes that
label filter -- every `axial`/`elev` piece is a candidate."*

⚠ **Two later corrections to that paragraph, 2026-09-28.** (1) The 54.7% figure
it quotes is **withdrawn** — unreproducible, no committed script computes it;
measured coverage is ≈49%, and `starfish` reads 48.2% rather than the 94.4% that
made it look like a high-coverage control
(`2026-09-24-dense-pleats-design.md` §2). (2) The reasoning above is otherwise
sound and its conclusion is now *reinforced from the other side*: step 5, the
fill this file identifies as the unbuilt other half, was measured and would
inject **zero** segments on all seven subjects — every unoccupied segment is a
*slope*, so there is no level line to find. Filter-then-fill is not merely
unbuilt here; the fill half is unreachable from an elevation field. See
`2026-09-28-pleat-grid-headroom-design.md` and its evidence directory.

**F.1.1 is filter-then-fill, and we built neither half.** Step 3 rejects
aggressively; step 5 then adds back "to guarantee comprehensive axial coverage
and a fully contiguous fundamental grid". "Keep everything" is not the filter
and not the fill.

## 2. Prior art (CLAUDE.md section 0)

**External.** COrigami (arXiv:2606.26299) appendix F.1.1, steps 3 and 4, read
directly and quoted in section 3 below. **Adopted**: both steps, as the
predicate. **Not adopted here**: step 5 (the fill), which is this spec's
declared follow-on (section 8), and steps 1-2, still rejected per the
dense-pleats spec.

**In-repo.** `interleave.py` is the closest precedent -- a pure function over
`pieces` and groups implementing an appendix-F rule -- and this module follows
its shape deliberately: pure, no I/O, no geometry construction, unit-testable
against hand-built inputs. Its history is also the cautionary one: three
definitions of `interleave.adjacency`, the second of which passed every
hand-built unit test while producing an **empty** graph on all real data. That
is why section 6 mandates a non-emptiness assertion against a real compiled
subject, not only hand-built fixtures.

## 3. The predicate

COrigami F.1.1, verbatim from the dense-pleats spec's own reading:

> (3) retain only segments strictly perpendicular to an intersecting hinge, or
> passing through an X-shape vertex (four intersecting ridges); (4) selectively
> re-introduce segments meeting the outer border where they share a vertex with
> both a ridge and an established pleat

### 3.1 Module

```python
# mcp_harness/box_pleat/pleat_filter.py

def retain(pieces, N) -> frozenset[int]:
    """Indices of the `axial`/`elev` pieces COrigami F.1.1 steps 3-4 keep.

    Pure: no I/O, no geometry construction, no mutation of `pieces`.
    Non-candidates (`B`, `ridge`, `hinge`) are never in the result and are
    never affected by it -- callers keep them exactly as before.
    """
```

Two steps, in order, because step 4 reads step 3's output ("an **established**
pleat"):

* **Step 3.** Retain candidate `i` if either
  (a) some `hinge` piece shares a vertex with `i` and runs perpendicular to it,
  or (b) an endpoint of `i` is an X-shape vertex -- a vertex with **four or
  more** incident `ridge` pieces.
* **Step 4**, one pass over the survivors: additionally retain a candidate that
  touches the paper border (any endpoint coordinate in `{0, 2N}`), shares a
  vertex with some `ridge` piece, and shares a vertex with a step-3 survivor.

**"Intersecting" means sharing a vertex, and on this lattice that is EXACTLY
geometric intersection -- proved, not chosen.** Measured piece directions on
`lizard`:

| role | direction | count |
|---|---|---|
| `elev` (candidate) | axis-aligned (0,1) / (1,0) | 2,820 / 1,668 |
| `hinge` | axis-aligned (0,1) / (1,0) | 88 / 136 |
| `ridge` | **diagonal (1,1)** | 136 |
| `ridge` | axis-aligned | 20 |
| `B` | axis-aligned | 136 / 136 |

Every piece is a unit segment whose direction is (1,0), (0,1) or (1,1) on the
half-grid. Two such segments meet only at half-grid points, and a half-grid
point on a unit segment is one of its endpoints. So endpoint-sharing and
geometric intersection coincide, and no separate crossing test is needed --
including for a diagonal ridge against an axis-aligned candidate, which can only
meet at a shared endpoint. (`lizard` carries **no** `axial` pieces at all; its
candidates are entirely `elev`.)

Since candidates and hinges are both axis-aligned, "strictly perpendicular" is
well defined as horizontal-versus-vertical, with no tolerance and no angle
arithmetic.

One pass, not a fixpoint: "established" reads as step 3's output, and iterating
would let step 4 bootstrap off its own additions -- a different and larger
filter than the paper describes. Recorded because the code is one line from
either reading.

### 3.2 Two clauses are inert in OUR geometry, and that is a property, not a bug

**Measured 2026-09-26/27, ridge-incidence degree at every vertex:**

| ridges meeting at a vertex | `lizard` | `bird` |
|---|---|---|
| 2 (a ridge passes through) | 150 | 459 |
| 3 (**Y-shape**) | 2 | 8 |
| **4 (X-shape)** | **0** | **1** |

**Our ridges do not cross, by construction.** They come from Lang's straight
skeleton (`skeleton.py`), and a straight skeleton's edges meet at nodes rather
than crossing. COrigami's box-pleated ridges evidently do cross; ours cannot.

**Also measured:** the perpendicularity test in clause (a) never discriminates
-- Phase 0's `v1` (perpendicular hinge) and `v2` (any hinge, no perpendicularity
test) are **equal on all six subjects**. Every candidate touching a hinge is
already perpendicular to it.

So the effective predicate on this geometry reduces to *"touches a hinge"*,
plus step 4's border cases.

**Both clauses are nevertheless implemented as the paper states them**, for
three reasons: fidelity if our ridge construction ever changes; the X-shape
count is 1 on `bird`, so it is not identically zero; and a filter that silently
omitted a clause would be indistinguishable from one that had a bug in it.
**Their vacuity is documented in the module docstring and asserted in the
evidence, so no reader mistakes them for load-bearing.**

### 3.3 The filter gates dense-mode ADDITIONS ONLY

**Owner ruling, standing: "augment, don't replace."** A piece whose elevation
profile already reads `M` or `V` -- the ~6% sparse mode keeps -- is a variable
in both modes and **the filter must not touch it.** In `initial_readings` that
falls out of the existing branch order: `elif lab in ("M", "V")` fires before
the dense branch.

Filtering away a crease sparse keeps would be a regression on the sparse
baseline, not a filter.

**Consequence for the numbers:** section 1's 432 counts retained pieces among
**all** 4,488 `lizard` candidates, so it slightly overstates what the filter
actually gates. The spec therefore pins **measured** counts in its tests
(section 6), never section 1's figures. Predicting a number and then
"confirming" it is how this project's last three retractions happened.

## 4. Architecture and data flow

One new module. Two touch points in `assign.py`. Two new parameters.

```
build_pieces                      (unchanged)
   |
   +-- [dense & filter] pleat_filter.retain(pieces, N) -> retained
   |
initial_readings(..., retained)   (MODIFIED, one branch condition)
   |
pleat_paths(..., dense=True)      (MODIFIED, one candidate test)
   |
interleave.colour                 (unchanged -- sees fewer groups)
   |
assign's CSP                      (unchanged mechanism, smaller variable set)
```

### 4.1 `initial_readings`

The dense branch gains the filter test. Nothing else changes:

```python
elif lab in ("M", "V"):
    pleat_lab[i] = lab
elif dense and (retained is None or i in retained):
    pleat_lab[i] = "M"
else:
    labels[i] = lab
```

A filtered-out candidate falls to `else: labels[i] = lab`, which is reachable
only when `lab == "F"` (the `elif` above catches `M`/`V`), so it is pinned `F`
exactly as sparse pins it, and `emit.py:31` drops it. **No new label state is
introduced.**

**Forbidden edits, unchanged from the dense-pleats spec section 9:** the
centre-column domain order (`["F"] + [lab, opposite]`) and
`label_from_profile`'s mirroring (`if lo is None: lo = e + (e - hi)`). Both
look collapsible. Neither is.

### 4.2 `pleat_paths` -- an intentional contract change

In dense mode the candidate test becomes **`labels[i] == "F"` -> skip**,
replacing today's "no label test at all".

⚠ **CORRECTED 2026-09-27 during implementation. An earlier revision of this
section said the test should be `labels[i] is None`. That is WRONG and would
have broken dense grouping outright** (`lizard` 365 paths -> 3). The reason is a
name collision this section reasoned past: **`pleat_paths`' second parameter is
named `labels`, but `assign` passes `probe`** (`assign.py:611`:
`groups = pleat_paths(pieces, probe, dense=dense)`), and `probe` is
`[pleat_lab[i] if i in pleat_lab else labels[i] ...]`. So in `probe`:

| piece | `probe[i]` | is it a candidate? |
|---|---|---|
| live dense candidate | `"M"` or `"V"` (from `pleat_lab`) | **yes** |
| centre-column piece | `None` (gets `domain`, no `pleat_lab`) | **yes** |
| candidate the filter rejected | `"F"` | no |

`is None` would therefore have skipped every live candidate and kept only the
centre-column ones. `== "F"` is the correct test, and it keeps centre-column
pieces for a different reason than this section originally gave.

**Why this is exactly equivalent when unfiltered.** In unfiltered dense no
candidate is ever `"F"` in `probe`: `initial_readings`' `else: labels[i] = lab`
branch is unreachable when `retained is None`, so every candidate gets
`pleat_lab[i]` and reads `"M"`/`"V"`, and centre-column pieces read `None`.
Nothing is skipped, exactly as today. When filtered, a rejected candidate falls
to that `else` branch, `lab` is `"F"` there, and it drops out.

**Why not `probe[i] in ("M", "V")`.** That would **silently exclude
centre-column pieces**, whose probe is `None` because they get a `domain` and no
`pleat_lab`. A behaviour change in unfiltered dense that no *sparse*
byte-identity test would catch. Testing for `"F"` explicitly -- rather than for
membership of the live values -- is what keeps `None` on the candidate side.

**This contradicts `pleat_paths`' current docstring**, which says `labels` *"is
read on no code path when `dense=True`"* and *"Do not 'fix' a dense-mode caller
to pass a meaningful `labels` argument."* That warning exists to prevent
precisely this edit. **The change is deliberate and the docstring must be
rewritten in the same commit**, stating that dense mode now reads `labels` to
learn what the filter pinned, and that the argument is meaningful again.

Its other contract is unchanged: the ridge/hinge split is geometric and stays in
both modes.

### 4.3 Signatures

```python
retain(pieces, N) -> frozenset[int]                       # new module
initial_readings(N, pieces, contours, prof, face_of, *, dense=False, retained=None)
pleat_paths(pieces, labels, *, dense=False)               # unchanged signature
assign(..., dense=False, filter_pleats=False)
compile_tree(..., dense=False, filter_pleats=False)
```

`assign` computes `retained = pleat_filter.retain(pieces, layout.N) if (dense
and filter_pleats) else None` and passes it to `initial_readings`. `pleat_paths`
needs no new parameter -- the filter reaches it through `labels`, per 4.2.

**`filter_pleats` is ignored unless `dense`**, documented on both functions. A
conditional parameter is a cost; it is accepted so that both dense modes run in
one process on the same geometry (section 5).

## 5. Gating: the two modes coexist

**Owner ruling, 2026-09-26.** `filter_pleats=False` keeps today's dense
behaviour available.

The reason is measurement quality, not caution: the deliverable is the
comparison *"unfiltered dense never certifies; filtered dense does or does
not"*, and an in-process A/B on the same `layout`, `ridges` and `contours` is
the only form of that comparison with no confound. This work has already been
bitten by the cross-process kind -- the `dog`/`guinea_pig` byte-identity dumps
that predated the verified base archive, where "IDENTICAL" could have been
vacuous for the two most expensive subjects.

**Two byte-identity guarantees, both load-bearing:**

* `dense=False` -- unchanged, and covered by the existing all-8 test.
* `dense=True, filter_pleats=False` -- must reproduce the committed dense
  measurements exactly (`evidence/2026-09-24-dense-pleats/dense_labelling.json`:
  `lizard` 4,868 dense M/V, 365 paths, 429 variables).

## 6. Testing

* **`retain` unit tests, hand-built geometry.** A candidate touching a
  perpendicular hinge (retained); one touching nothing (rejected); one touching
  a parallel hinge only -- **REJECTED**, and this is the only test that makes
  clause (a)'s perpendicularity requirement visible at all. (An earlier revision
  of this bullet said "retained ... since `v1 == v2`", which conflated two
  different claims: `v1 == v2` says REAL geometry contains no parallel-only
  candidate, NOT that the predicate keeps one. The predicate rejects it by
  construction.); a border candidate qualifying
  under step 4; **a hand-built X-shape vertex** (four ridge pieces at one
  vertex) so the production-vacuous clause is still exercised; and a step-4
  candidate that must NOT be retained because iterating would be needed to reach
  it, pinning the one-pass reading of 3.1.
* **Every count assertion is paired with a non-vacuity assertion.** PR #193
  shipped two tests reading `0 == 0` against fixtures generating zero of the
  thing under test.
* **Non-emptiness on a REAL compiled subject, mandatory.** `retain` on
  `lizard`'s real pieces must return a set that is neither empty nor all
  candidates. `interleave.adjacency`'s second definition passed every hand-built
  test while producing an empty graph on every real subject; a fix dispatch in
  that wave made this assertion mandatory, and it applies here.
* **Integration, pinning MEASURED values.** On `lizard` with
  `dense=True, filter_pleats=True`: record the retained count, the pinned-`F`
  count (0 without the filter, positive with it), the dense M/V count, the
  variable count and the path count. The test asserts the values the
  implementation measures, not section 1's estimates, and the evidence records
  both so the difference is visible.
* **Byte-identity, both guarantees of section 5**, on all 8 subjects via the
  established method: `git archive` the base into a temp tree (never move HEAD,
  never `git stash` -- the stack is shared with other worktrees), compile both
  sides, compare sha256 over the emitted dict.
* **Existing suites stay green:** `test_box_pleat_assign.py`,
  `test_box_pleat_interleave.py`, `test_box_pleat_layers.py`. Use
  `../.venv/bin/python3` from `mcp_harness` (bare `python3` lacks `skeletor` and
  dies at collection); that venv has no `pytest-timeout`, so never pass
  `--timeout`. **Never run `pytest tests/`** -- 5,167 tests, over 3 hours.
* **The measurement, which is the point.** `compile_tree(dense=True,
  filter_pleats=True)` on `lizard`, then the corpus as cost allows. Report
  candidates refused and the verdict. A negative is reported with the same
  prominence as a positive.

## 7. Risks

1. **The filtered pattern may be too sparse to read as box-pleated.** Expected:
   step 3 is aggressive precisely because step 5 exists to restore contiguity.
   **This must not be "fixed" by loosening the predicate** -- loosening a gate
   to reach a headline is this project's named recurring failure mode
   (CLAUDE.md section 1.1). The remedy is step 5 (section 8), or a recorded
   negative.
2. **The retained count is flat in N**, so large subjects get proportionally
   sparser (5.6% on `guinea_pig` against 9.6% on `lizard`). If filtered dense
   under-creases the big subjects, that is a finding about the predicate's
   scale-dependence, to be reported rather than tuned away.
3. **Filtering changes the initial `F` set, hence FOLD topology.** Expected and
   harmless: `compile._check`'s topology-drift assert guards drift *between
   candidates within one compile*, which this does not affect.
4. **Filtering may not help at all.** The crease set being 10-18x denser than
   COrigami's is a strong suspicion, not a proof that the set is what blocks
   folding. If filtered dense still never certifies, that **refutes root cause
   1** and redirects to the search levers -- a useful result, and the reason this
   spec is scoped to one measurable change.

   ⚠ **MATERIALISED 2026-09-27, and worse than stated.** Not only did filtering
   fail to help: the "10-18x denser" premise is itself **withdrawn**. That ratio is
   a unit-piece ratio; at COrigami's own unit of selection (a segment) the ratio is
   **1x** and the filter retains 100%, so the crease set is not denser than
   COrigami's by that criterion at all. Root cause 1 is refuted in the form this
   spec tested it. `../evidence/2026-09-27-pleat-filter/README.md`.
5. ⚠ **RESOLVED 2026-09-27: this risk is REFUTED.** It said F.3 was in doubt
   because `lizard` has 2 Y-shape and 0 X-shape ridge vertices against 88 ridge
   variables. That was the wrong statistic -- anchor COUNT rather than anchor
   REACHABILITY. Measured (`evidence/2026-09-27-f3-anchors/`): the ridge graph
   has only 1-2 components per subject, so a single anchor propagates through a
   whole component, and reach is **100% on five of eight subjects, >=71.7% on
   the rest**. F.3 remains a viable lever. What IS still open is whether its
   rules determine a consistent value at variable level, which that evidence
   file states as the next measurement.

## 8. Out of scope

* **F.1.1 step 5, the fill** (the dense-pleats spec's Component 1). The declared
  follow-on: build it if and only if the filter measurement says the result is
  too sparse.
* **F.3 ridge assignment** -- own spec, and see risk 5.
* **Minimal unsat cores** -- own spec.
* **No-good indexing** -- specced and WITHDRAWN 2026-09-26 (the scan is 1.28% of
  runtime). Do not re-propose.
* **`layer_order.py`** -- untouched across this whole line of work, and stays so.
* **The serve path.** `grep -c box_pleat mcp_harness/server.py` is 0 and stays 0.

## 9. Evidence

`docs/superpowers/evidence/2026-09-27-pleat-filter/`: the retained/pinned/M-V/
variable/path counts per subject for both dense modes side by side, the two
byte-identity tables with digests, and the verdict for filtered dense per
subject. Where a verdict is unaffordable it is recorded as UNDECIDED with its
budget -- silence is not a result.

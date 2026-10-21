# S1 — Crease-pattern mirror symmetry, measured correctly

**Date:** 2026-08-04
**Status:** design, awaiting review
**Author:** brainstorming session (Claude + raphaeldchen)
**Slice:** 1 of 5. See §9 for the decomposition and what this slice deliberately
does not touch.

> **This slice ships no fix.** It ships an instrument, and the instrument turns
> three committed `0.000000` readings into honest `ASYMMETRIC` verdicts —
> including one on a hand-authored template that no extractor and no lever has
> ever touched. That reversal *is* the deliverable: every later slice's
> before/after is unreadable until it lands.

---

## 1. Why this slice exists

The trigger for the two ALIGNMENT goals was *"the dog I generated looks a little
asymmetric"* — about a model that **compiled successfully**. Goal 2 is therefore
"a tree the user asked to be bilaterally symmetric compiles to a crease pattern
that is mirror-symmetric."

Nothing in production measures that. Three implementations exist and **all three
are wrong in the same two ways.**

| implementation | where | reads |
|---|---|---|
| `cp_mirror_residual` | `docs/superpowers/evidence/2026-08-03-reparented-bases/fold_and_look.py:146` | `vertices_coords` only |
| `cp_symmetry` → `vertex_residual_max` | `mcp_harness/probe_cp_symmetry.py:95` | `vertices_coords` only for the residual |
| `mirror_map` | `mcp_harness/mv_repair.py:408` | vertices + edges, **assignments deliberately ignored** |

### 1.1 The two defects

**(a) One-sided.** Both residuals are a *directed* Hausdorff distance from
`reflect(V)` to `V`: for each reflected vertex, the distance to the nearest
actual one. `fold_and_look.py:146`'s own docstring states the consequence and
then stops short of the conclusion:

> "coincidence can only ADD vertices that complete the inclusion, so it can only
> push the value toward 0. A ~0 reading on a small pattern may be degeneracy; a
> POSITIVE reading is a witness degeneracy cannot fabricate."

A directed distance reads 0 whenever `reflect(V)` is a strict **subset** of `V`
— including the many-to-one case where two distinct vertices both claim the same
actual vertex as their nearest neighbour, leaving a third homeless and invisible.

The textbook fix is the bidirectional form (§2), and revision 1 of this spec
adopted it. **That was wrong for this map, and §1.2 records the correction:** a
reflection is an isometry *and* an involution, so both directions are provably
equal and a bidirectional scan is arithmetic theatre. The defect is real; the
check that catches it is the CARDINALITY assertion (§3, condition 2), not a
second distance.

**(b) Vertices only.** Neither residual reads `edges_vertices` or
`edges_assignment`. **A crease pattern whose vertices are mirror-symmetric but
whose M/V assignment is not scores a perfect `0.000000`** — and that is a very
plausible mechanism for "compiled fine but looks a little asymmetric."

### 1.2 Defect (b) is not hypothetical — it is the live state of the repo

Measured 2026-08-04, all seven cases compiled on the current engine. `1-sided`
is what ships today; the remaining columns are the corrected metric.

| case | kind | 1-sided | 2-sided | bijection | \|RV∩V\| | edges | pres | swap | mism | verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| star-4 + pairs | POSITIVE | 0.000000 | 0.000000 | ✓ | 9/9 | ✓ | 16 | 0 | 0 | **SYMMETRIC** |
| HSHAPE | POSITIVE | 0.000000 | 0.000000 | ✓ | 12/12 | ✓ | 21 | 0 | 0 | **SYMMETRIC** |
| TEMPLATE_QUADRUPED | POSITIVE | 0.000000 | 0.000000 | ✓ | 27/27 | ✓ | 48 | **2** | 0 | ASYMMETRIC |
| lopsided-5 | NEGATIVE | 0.182685 | 0.182685 | ✗ | **4/19** | — | — | — | — | ASYMMETRIC |
| QUAD | NEGATIVE | 0.000000 | 0.000000 | ✓ | 13/13 | ✓ | 16 | 0 | **6** | ASYMMETRIC |
| bird (as served) | subject | 0.318880 | 0.318880 | ✗ | **4/18** | — | — | — | — | ASYMMETRIC |
| bird (axis-pinned) | probe | 0.000000 | 0.000000 | ✓ | 19/19 | ✓ | 30 | **4** | 0 | ASYMMETRIC |

**How these were compiled, because it decides what they can be used for.** The
table is a bare `HeadlessTreemaker` compile — attempt-0 for one exact node list,
**not** the serve path. That is the right instrument here (the question is
whether the defect exists, and attribution is cleaner without the ladder), but
it is the wrong instrument for a pin, and mistaking one for the other has bitten
this project four times.

Two of the three reversals are nevertheless **corroborated on the serve path**,
by the committed `fixtures/cp_symmetry_evidence.json`, which compiles through
`server.draft_and_compile_full_base`: `TEMPLATE_QUADRUPED` records
`mv_preserved 48 / mv_swapped 2` and `QUAD` records 22 creases with only 16
matched — the same 2 swapped and same 6 unmatched this table reports. `bird`
agrees across both methods because it packs at attempt 0, so for `bird` the bare
compile *is* the serve path. Every number used as an acceptance pin (§11) is
re-measured through the serve path during implementation regardless.

Three verdicts reverse. Read the columns honestly about **which** correction did
the work:

- **Two-sidedness changed no number on these seven cases — and CANNOT, ever.**
  ⚠ CORRECTED 2026-08-04, during implementation. A reflection is both an
  isometry and an involution, and those two facts alone force
  `d(ρ(p), v) = d(p, ρ(v))` for every p and v. So the directed distance from
  ρ(V) to V is *provably identical* to the one from V to ρ(V), for every point
  set. Pinned reproducibly by
  `test_cp_mirror.test_a_reverse_direction_scan_is_provably_vacuous_for_a_reflection`,
  a randomized sweep of 200 point sets at each of five axes (1000 total),
  rather than cited to a throwaway shell run. The revision-1 reading of this row — "the failure mode
  is real but did not fire here" — was wrong about the reason; it cannot fire.
  The degeneracy a directed distance is blind to is real, and is caught by the
  CARDINALITY assertion below, never by two-sidedness. `residual` is therefore
  a plain directed Hausdorff, honestly labelled.
- **Assignment-awareness reversed all three verdicts.**
- **Cardinality is what makes the negatives truthful.** `bird`'s baseline is not
  "a distance of 0.32" — it is *4 of 18 vertices have a mirror image at all*.

### 1.3 The two cases that matter most

**`QUAD` is the negative control the shipped metric got wrong.**
`probe_cp_symmetry.py:32-45` flags QUAD's perfect 0.0 as an unexplained
small-tree degeneracy and concludes "a ~0.0 reading on a small tree is
UNINFORMATIVE". It is not degeneracy: QUAD has **six creases mapping M/V ↔ F** —
folded on one side of the axis, flat on its mirror image. The old metric could
not see it because it never looked at an assignment.

**`TEMPLATE_QUADRUPED` is hand-authored and exactly symmetric,** needs no mesh
extractor, no pair reconciliation and no axis lever — and it carries the defect.
Whatever this is, it was not caused by anything the path-reconciliation slice
touched, and no leaf-placement fix will remove it.

### 1.4 Why this blocks the other slices

A prior session measured `bird` at CP residual `0.318880 → 0.000000` under an
axis-pinning probe and read it as "exactly symmetric." Under the corrected
metric that same pattern is an **exact vertex-and-edge bijection with four
swapped creases** — the geometry claim survives in full, the symmetry claim does
not. The repo has already produced one tautological zero on `bird`
(`pair_path_gap_max = 0.0`, with `bird`'s CP byte-identical before and after).
A second zero from an instrument that cannot distinguish symmetry from
degeneracy is not acceptable as a slice's success criterion.

---

## 2. Prior art (CLAUDE.md §0)

| Source | Finding | Adopted / rejected |
|---|---|---|
| [Hausdorff distance, directed vs bidirectional](https://metricgate.com/docs/hausdorff-distance-shape/) | The directed form "is only commutative when A and B contain the same number of points, which is why the expression is generally written in bidirectional form that penalizes the situation where some points are present in one structure but not in the other" | **Adopted, then SUPERSEDED by our own case.** The literature's reason for preferring bidirectional is precisely defect (a) plus the cardinality hole — but that reasoning assumes an arbitrary map between two sets. Ours is a REFLECTION, an isometry and an involution, for which the two directions are provably equal (§1.2). We keep the *concern* and answer it with the cardinality assertion instead |
| [Wolter, Woo & Volz, *Optimal algorithms for symmetry detection in two and three dimensions*](https://link.springer.com/article/10.1007/BF01901268) | All rotational and involutional symmetries of a 2-D point set in Θ(n log n); optimal | **Adopted as framing.** Symmetry of a finite planar figure is **decidable**, not approximable. Hence a *verdict* with the residual demoted to a witness |
| [Atallah, optimal algorithms for planar point-set symmetries](https://www.sciencedirect.com/science/article/abs/pii/0020019086900979) | O(n log n) for all axes of a planar figure of segments/points/circles, by reduction to a combinatorial question on words | **Framing adopted, algorithm REJECTED.** It answers *"what are all the axes of symmetry?"*. We must answer *"is it symmetric about **this** axis?"* An axis-finder reintroduces the coincidence failure mode this slice exists to remove — see §4.2 |
| [Mitra, Guibas & Pauly, *Partial and Approximate Symmetry Detection*](https://www.researchgate.net/publication/44250264_Partial_and_Approximate_Symmetry_Detection_for_3D_Geometry) | Graded partial-symmetry scores over a transformation space | **Rejected.** A graded partial score is the exact conflation being removed. We want a decision at a stated tolerance |
| Both optimal-algorithm papers, on complexity | Θ(n log n) is achievable and optimal | **Rejected for our n.** Our patterns are 9–83 vertices. The existing bucketed O(n) lookup in `mv_repair.mirror_map:429-441` already beats brute force at this scale; the optimal machinery buys nothing and costs risk |
| `mv_repair.mirror_map` (`mv_repair.py:408-487`), in-repo | Already does bijection + edge-set preservation + tolerance + spatial bucketing + `_geometry_frame` routing | **Adopted wholesale as the shared core** (§4.1). It is the one existing implementation that is right about everything it chose to look at |
| The visual-feedback-loop spec (`2026-08-02-visual-feedback-loop-design.md` §2) | A VLM cannot judge a flat crease pattern (κ=0.497; **zero** detection on a density-controlled single-crease flip). Silhouette IoU is meaningless. Headless WebGL never advances the solver | **Adopted as a hard scope limit.** §6's tripwire asks for an alignment and colour-clash judgement, never a crease count around a vertex, and never runs in CI as an acceptor |
| COrigami ([arXiv:2606.26299](https://arxiv.org/abs/2606.26299)) §3.1, Tier 2 | Their collapsed-base tier renders **nothing** and is symbolic only | **Adopted.** Independent confirmation that the base is judged arithmetically, not visually |

---

## 3. What is being measured, exactly

Let `V` be the pattern's vertex set, `E` its edge set, `A` its assignments, and
`ρ` the reflection about a **specified** axis. The pattern is mirror-symmetric
about that axis iff there is a bijection `σ : V → V` with

1. `‖ρ(v) − σ(v)‖ ≤ tol` for every `v` — every vertex has a mirror image,
2. `σ` is injective and `|σ(V)| = |V|` — distinct vertices do not collapse,
3. `{σ(a), σ(b)} ∈ E` for every `(a, b) ∈ E` — the edge set maps onto itself,
4. `A[{σ(a), σ(b)}] = A[{a, b}]` for every edge — the assignment is preserved.

`residual = sup_{r ∈ ρ(V)} d(r, V)` — the DIRECTED Hausdorff distance — is
reported as a **witness**, never as the verdict. Directed, not two-sided,
because for a reflection the two directions are identically equal (§1.2); a
"two-sided" variant would be arithmetic theatre. Its known blind spot, a
many-to-one collapse, is covered by condition 2 above rather than by a second
distance scan.

`residual = 0` does not imply symmetry. Two independent counterexamples, both
measured: `bird` axis-pinned (an exact 19/19 bijection carrying four swapped
creases) and any collapse (where the residual reads 0 while `cardinality_ok`
is false).

### 3.1 The M/V convention is settled, not assumed

`probe_cp_symmetry.py:17-20` declines to pick one — *"the M/V assignment
reported both as 'preserved' and 'swapped' because an in-plane reflection
reverses orientation and the convention is not worth assuming"* — and reports
both counts. Condition 4 above asserts **preserved**, on two independent
grounds:

- **Physically.** The mirror is `R : (x, y, z) → (y, x, z)`. It leaves `z`
  alone, so a crease folding toward `+z` still folds toward `+z`: a mountain
  maps to a mountain.
- **Measured.** The two unambiguously symmetric patterns in the repo come out
  with **zero** swapped creases — `star-4 + pairs` 16/16 preserved, `HSHAPE`
  21/21.

A swapped crease is therefore a **defect**, not an alternative convention: two
creases that are exact mirror images fold in opposite directions. `swapped` and
`mismatched` are reported separately so this decision stays auditable rather
than buried in a boolean.

### 3.2 And a mirror-symmetric assignment is achievable — no theorem is in the way

Checked before making it a gate. Every on-axis vertex in every pattern measured
carries an **even** number of mirror-paired creases plus one or two self-mapped
ones, so a preserved assignment can still reach Maekawa's `|M − V| = 2`.
Concretely at `bird`'s on-axis `v2 = (0.5427, 0.5427)`, degree 4, M=3 V=1:

| assignment | mirror pair | self-mapped | M | V | Maekawa | mirror |
|---|---|---|---|---|---|---|
| what the engine emitted | {M, V} | {M, M} | 3 | 1 | ✓ | ✗ |
| the symmetric alternative | {M, M} | {M, V} | 3 | 1 | ✓ | ✓ |

Both are legal and produce identical counts. **The engine picked the asymmetric
one arbitrarily, because nothing asks it not to.** That is S2's opening.

---

## 4. Architecture

### 4.1 Module boundary

New `mcp_harness/cp_mirror.py`:

```
candidate_axes(fold, tol)        -> [reflector]     bbox axes, then every
                                                    perpendicular bisector at
                                                    <= MIRROR_PAIR_AXES_MAX verts
mirror_bijection(fold, reflect)  -> {v: v} | None   THE shared core: reflect,
                                                    find within tol, require a
                                                    bijection, require the edge
                                                    set preserved
mirror_verdict(fold, axis_deg)   -> dict            the metric: bijection +
                                                    assignment + directed
                                                    residual as witness
overlay_svg(fold, axis_deg)      -> str             the tripwire (§6)
```

`mv_repair.mirror_map` becomes a thin caller — `candidate_axes` →
`mirror_bijection` → first non-identity hit — preserving its assignment-blind,
axis-**searching** contract exactly.

**The byte-identity risk is precise and testable:** `mirror_map` returns the
*first* matching axis, so `candidate_axes` must generate axes in verbatim the
current order (`mv_repair.py:443-466`: the two bbox axes, then perpendicular
bisectors in `(i, j)` ascending order, deduped by the same rounded key). Its two
existing tests pin both directions — a positive involution
(`tests/test_mv_repair.py:746`) and the served dog's `None`
(`tests/test_mv_repair.py:760`) — and both must stay green untouched.

**What happens to the two wrong ones.** `probe_cp_symmetry.cp_symmetry` and
`fold_and_look.cp_mirror_residual` are **deleted**, and their callers re-pointed
at `cp_mirror.mirror_verdict`. The two *driver* scripts survive — they own
subject construction, the node-order basin control and the SVG sheet, none of
which is in question — only their metric functions go. Writing a correct fourth
implementation beside three wrong ones would leave the repo one grep away from
citing a stale one, which is how this area reached three disagreeing metrics in
the first place.

So: three existing implementations plus the one written here collapse to a
single shared core. `cp_mirror.py` inherits
`cp_audit._geometry_frame` routing, which fixes a live defect in **both**
current CP-symmetry implementations: neither handles a nested `file_frames`
FOLD, and both `KeyError` on one.

### 4.2 Why the axis is an argument, not a search

`mirror_map` *searches* for any axis; `mirror_verdict` *tests* the one it is
given. Sharing the core without sharing the axis policy is the whole point of
the boundary.

If the verdict searched, a lopsided pattern that happens to be symmetric about
some accidental perpendicular bisector would score green — the same
coincidence-satisfiable failure mode as every other instrument this audit
found. The axis is the *model's* mirror, and only the caller knows it.

### 4.3 The axis is not recorded in the artifact — stated, not hidden

A `.fold` does not record which symmetry axis produced it. `frame_title` carries
the scale (`TreemakerWrapper.cpp:1331-1332`) but not the angle. So
`mirror_verdict` takes `axis_deg` as a **required** argument and every caller in
this slice passes `45.0`.

That is defensible **today** because all four `apply_symmetry` call sites
hard-code it (`server.py:185, 217, 264, 309`). The moment S4b makes the axis
selectable it becomes a lie. Threading the real angle through — or recording it
in `frame_title` beside the scale — is a **named prerequisite of S4b**, not a
loose end here.

**The same is true of the reflection CENTRE, not only the angle.** Noted
2026-08-04 (fix-wave review): `mirror_verdict` never takes a `centre`
parameter — it reaches `axis_reflector` with only `axis_degrees`, so every
call gets `axis_reflector`'s hard-coded default, `(0.5, 0.5)`. That is safe
today for the same reason 45° is safe today: the shipped 45° line happens to
pass through `(0.5, 0.5)`, so the two never disagree. But a selectable axis
that keeps an implicit, unparameterized centre is only half-selectable — an
angle away from 45° whose true mirror line does *not* pass through
`(0.5, 0.5)` would silently test the wrong line. Threading `centre` alongside
`axis_degrees` is therefore **also a named prerequisite of S4b**, not a
detail S4b can pick up unstated.

---

## 5. The verdict, and the scorecard

### 5.1 Return shape

```
symmetric        bool   THE verdict. residual == 0 does NOT imply it.
residual         float  DIRECTED Hausdorff. geometry witness, not a verdict.
is_bijection     bool
cardinality_ok   bool   |reflect(V) ∩ V| == |V|
edges_ok         bool
mv_preserved / mv_swapped / mv_mismatched   int
offenders        list   the specific creases, for diagnosis and for §6.
                        Capped at `OFFENDERS_MAX` (12) entries.
offenders_truncated bool  True when mv_swapped + mv_mismatched exceeds the
                        cap, so `len(offenders) == 12` reads as "exactly 12
                        offenders" or "at least 13, only 12 shown" honestly
                        instead of by silent inference. Added retroactively
                        (fix-wave, 2026-08-04): the committed
                        `fixtures/cp_symmetry_evidence.json` has an `insect`
                        row with `mv_swapped: 16` beside a bare 12-element
                        `offenders` list, which is exactly the ambiguity this
                        key removes.
```

### 5.2 Three columns, not one

The single biggest lesson of this audit is that one scalar hides independent
failure modes. `bird` as served fails on **geometry**; `bird` axis-pinned fails
on **assignment**; a single number cannot say which, and the next reader repeats
the error.

| column | bird (as served) | bird (axis-pinned) | QUAD |
|---|---|---|---|
| `cp_symmetric` | False | False | False |
| `cp_mirror_residual` | 0.053492 | 0.000000 | 0.000000 |
| `cp_mv_broken` | **None** | **4** | **6** |

`bird (as served)`'s residual here is the scorecard-tier value (⚠ CORRECTED
2026-08-04: an earlier revision quoted `0.318880`, which is
`probe_cp_symmetry`'s bare-compile voxel-64/prune-0.30 reading from §1.2's
table, not the served value — see §11 criterion 3 for the full correction and
what actually coincides across tiers).

`residual > 0, mv_broken = None` reads *"geometry failed, assignment never
evaluated"*. `residual = 0, mv_broken = 4` reads *"geometry exact, assignment
broken"*. A reader distinguishes G2a's problem from G2b's without opening
anything.

`cp_mv_broken` is `swapped + mismatched`, with the split kept in the verdict
dict. The two are physically different — folds the opposite way, versus folded
on one side and flat on the other — but at row level both mean "the assignment
does not mirror".

**`None`, never a fabricated number,** for an unserved or unparseable row, and
for `cp_mv_broken` whenever the bijection failed. This follows
`paper_coverage.py:82-95`'s explicit rule: *"a fabricated 0.0 or 1.0 in a
scorecard column is worse than an empty cell."*

### 5.3 Two pins, because one is not enough

The repo's own lesson: *a count-based test is not a pin of the wiring — measure
that by deleting the line.*

1. **Wiring.** `cp_symmetric` in `_COLS` and `_DIFF_COLS`, in the shape of
   `tests/test_stub_stage.py:339-340`. **The same two lines for
   `hull_coverage`,** which has never had them: its siblings `stub_flaps`
   (`test_stub_stage.py:339`), `pair_gap_max` (`test_pair_reconcile.py:264`) and
   `pair_path_gap_max` (`:280`) all do, and deleting `hull_coverage` from
   `_COLS` today leaves the suite green.
2. **Value.** A test that actually opens `fixtures/scorecard_baseline.jsonl`.
   **Nothing reads that file today** — and its own `_meta` claims
   `tests/test_anatomy_oracle.py` does, which is false: that test was
   deliberately re-pointed away on 2026-08-03
   (`tests/test_anatomy_oracle.py:92-105`). Until this exists every number in
   the fixture can go stale silently.

---

## 6. The tripwire

A committed SVG per re-bless: the crease pattern solid and wide in assignment
colour, its reflection dashed and narrow on top in **its own** colour, teal
rings on `reflect(V)`, the axis drawn. Symmetric ⇒ the dashes vanish inside
their own colour. Asymmetric geometry ⇒ rings scattered off the pattern.
Asymmetric assignment ⇒ **a blue dash running down the middle of a red line**.

**Its job is stated in the module: it is a TRIPWIRE ON THE METRIC, not an
acceptor.** It exists to catch *"the residual says `0.000000` but the two point
sets plainly do not sit on top of each other."*

### 6.1 It needs a pin, because the first version was blind exactly like the metric

The first draft of this tripwire reflected **only vertices** and drew the
reflected line **wider** than the original — so it covered the very line it was
meant to be compared against. On `bird` axis-pinned, whose vertices overlap
perfectly, it would have rendered a clean picture and caught nothing, faithfully
reproducing the blindness it was built to guard.

The pin that catches this: **for every offender the verdict reports, the SVG
draws two different stroke colours on one segment** (same endpoints, different
`stroke`). Mechanically checkable, and it fails on the first version.

### 6.2 Why this does not reopen the falsified visual work

`2026-08-02-visual-feedback-loop-design.md` §2.1 killed VLM judgement of flat
crease patterns twice, including a density-controlled test where the two arms
differed only in the colour of one line segment. This tripwire does not ask
anyone — human or model — to count creases around a vertex or find a Maekawa
violation. It asks whether two point sets overlap and whether two strokes are
the same colour. It is also deliberately **not** a render of the folded base:
every flap of a uniaxial base collapses onto one line, so that view shows layer
stacking rather than limb placement, as `docs/superpowers/evidence/
2026-08-03-reparented-bases/README.md:45-50` already records.

---

## 7. Test surface, in two tiers

### 7.1 CI tier — reproducible, runs on every PR

Compiled through `server.draft_and_compile_full_base`, no mesh extraction.

| case | assertion |
|---|---|
| `star-4 + pairs`, `HSHAPE` | **`cp_symmetric is True`** — the real invariant: a symmetric tree must yield a symmetric crease pattern |
| the five subjects in `tests/fixtures/mesh_validation_trees.json` | verdicts pinned |
| `TEMPLATE_QUADRUPED` | pinned **red** at `mv_broken = 2`, with the offending crease pair recorded — S2's regression target |
| tripwire | every reported offender renders as two colours on one segment (§6.1) |
| `mv_repair.mirror_map` | its two existing tests unchanged and green |

**The controls run through the serve path, not a bare `HeadlessTreemaker`
compile.** S2 will modify `mv_repair`, which only runs on the serve path, so a
control compiled bare would be structurally blind to the change it exists to
protect. A bare compile being mistaken for the serve path has bitten this
project four times (memory: `path-reconciliation-phase-a-outcome`); paying the
worker spawn is cheaper than a fifth.

`mesh_validation_trees.json` is chosen because it is **committed, CI-runnable
without trimesh, and already a drift tripwire** for two other tests
(`test_gate_mesh_region.py:22`, `test_pair_detection.py:370`), so it inherits
the pinned-mesh-lib discipline in `.github/workflows/ci.yml`.

### 7.2 Scorecard tier — manual regeneration, as today

`cp_symmetric` / `cp_mirror_residual` / `cp_mv_broken` join `_COLS`, wiring-
pinned; `hull_coverage` gets the pin it never had; and a test finally opens
`fixtures/scorecard_baseline.jsonl`.

**Stated limitation, now partly measured.** These verdicts are pinned against
a file whose input configuration was **unrecorded** at write time: the
`_meta` says "serve default (voxel 64 / prune 0.30)", the module constants
are 96 / 0.60 (`mesh_to_tree.py:39,42`), and the serve *searches*
`VOXEL_GRID = [96, 64, 128]`. Nothing committed records which configuration
produced the five rows.

⚠ QUALIFIED 2026-08-04 (fix-wave review). "The scorecard tier can go stale in
a way the CI tier cannot" is supported for only **two** of the five subjects.
Re-running the serve-default search directly (§10, §11 criterion 3) shows
`bird`, `humanoid` and `insect` land on the *same* measurement the CI tier
already pins — `bird`/`humanoid` byte-identical trees, `insect` verdict-
identical. For those three, the scorecard and CI tiers are not a cross-check
today, just one number pinned under two names; a drift in the scorecard's
live search would, today, show up as a CI failure too. Only `fish` and
`quadruped` land on genuinely different configurations from their CI-tier
counterparts, so the staleness risk this subsection warns about is real and
un-mitigated for those two specifically. This is still why the *asserted*
invariant lives in the CI tier regardless of the three that currently
coincide: the CI tier's input is committed and stable even where the two
happen to agree today, while the scorecard's live search could resolve to a
different (voxel, prune) tomorrow for any of the five, including the three
that agree now. Recording the serve config is addressed in §10.

---

## 8. Re-blessed evidence

Three committed artifacts contain numbers this slice reverses. All are
regenerated in the same commit, following the repo's rule that a re-bless
happens in the session that moves the rows:

- `mcp_harness/fixtures/cp_symmetry_evidence.json` — regenerated under
  `mirror_verdict`. **It also needs a banner**: at HEAD its `(raw)` arm is
  *already reconciled* (`probe_cp_symmetry.py` predates the wiring commit
  `8894d95`), and because the re-parent is idempotent a naive re-run silently
  produces identical rows instead of erroring.
- `docs/superpowers/evidence/2026-08-03-reparented-bases/README.md` — its
  residual table and its "Two limits" section.
- `mcp_harness/fixtures/scorecard_baseline.jsonl` — new columns, and the false
  `_meta` claim about `test_anatomy_oracle.py` corrected.

Two false docstrings are corrected in passing, because both would mislead the
next reader of this exact area:

- `benchmark_subjects.py:226-229` (and the path-reconciliation spec at `:1167`):
  *"a nonzero `pair_path_gap_max` means a pair was refused."* Refused pairs never
  reach `kept`, so the column returns `None` — never a nonzero. The committed
  `bird` row proves it: `pairs_expected 2 / pairs_kept 1 / pair_path_gap_max 0.0`.
- `probe_cp_symmetry.py:59-61`: *"a ~0.0 reading on a small tree is
  UNINFORMATIVE."* It means the leaf set was mirror-symmetric — the property
  Goal 2 wants. QUAD is the case that made this look mysterious and it is
  explained in §1.3.

---

## 9. Scope — the five-slice decomposition

| slice | what | depends on |
|---|---|---|
| **S1 (this)** | the metric, its pins, the tripwire | nothing |
| S2 | M/V mirror symmetry, in our own `mv_repair` T-join solver | S1 to verify |
| S3 | bind `SetToSymmetryLine`; `axis_nodes` on the tree contract | S1 to verify |
| S4a | make `ProjectActivePaths` refuse a non-45° axis loudly | nothing |
| S4b | `ProjectActivePaths` reads `mSymAngle`; parameterize `rescue_ladder._U/_V` | S4a, S1 |
| S5 | Goal 1 proper: axis selection, coverage vs scale as an argued trade | **S4b** |

### 9.1 Explicitly NOT in this slice

- **No fix.** No geometry changes, no assignment changes, no C++.
- **`design_scale`.** It serves S5's coverage-versus-scale argument. S1 ships no
  geometry change, so no trade arises for it to adjudicate. YAGNI.
- **Anything touching the symmetry axis.** See §4.3.
- **Any acceptance decision about the folded 3-D base.** §6.2.

### 9.2 One measured fact that reorders the remaining slices

A 49-cell sweep (7 subjects × 7 angles, 2026-08-04) classifying *where* each
non-45° axis dies:

| outcome | cells |
|---|---|
| built | 8 |
| **died inside `ProjectActivePaths`** | **21** |
| died in the molecule build downstream of it | 7 |
| died at gate 1, genuinely before it | 13 |

`star-4` optimizes to scale **1.000000** at 0° and 90° versus **0.707107** at
the shipped 45° — the advertised +41.4% (= √2) is real *at the optimizer* and
**dies inside the projection**. Same shape on `bird` (1.367116 vs 1.309349) and
`humanoid`. Worse: of the 8 cells that built, the non-45° ones are **silently
wrong** — `TEMPLATE_QUADRUPED` at 15°/30°/60° returns PACK with residuals of
0.29/0.28/0.15 *about the axis that was requested*, because the projection
re-symmetrized about `y=x` regardless.

Two consequences recorded here so no later slice re-derives them:

1. `ProjectActivePaths` is **load-bearing, not a precision polish**. The 1.8e-9
   drift figure that suggested otherwise was measured at 45° — the one axis the
   routine hard-codes, i.e. exactly where it cannot fail.
2. **Every non-45° measurement in the repo is contaminated**, including the
   "book symmetry FALSIFIED / 45° defensible" result. The axis question is not
   merely unresolved, it is *unmeasurable* until S4b.

---

## 10. Risks and owed items

| risk | mitigation |
|---|---|
| Refactoring `mv_repair.mirror_map` regresses the serve path | Its two existing tests pin both directions and stay untouched; `candidate_axes` must reproduce the current axis order verbatim (§4.1). A behaviour diff on the nine committed goldens is part of acceptance |
| The asserted controls turn out platform-fragile | These are **boolean verdicts at `tol = 1e-6`**, not frozen hashes over roundoff-bearing floats — a materially more robust object than the artifact that caused the PR #67 Linux/macOS split. Verify on Linux in a container before merge, per memory `ubuntu-platform-truth` |
| The CI tier's serve-path compiles are slow | Seven cases. Measure before merge; if it exceeds budget, the fallback is the two controls in CI and the rest fixture-pinned — **stated as a fallback, never taken silently** |
| `cp_mv_broken` conflates swapped and mismatched | Deliberate at row level; the split is in the verdict dict and in `offenders`. Revisit only if a case appears where the distinction changes a decision |

**Owed, not closed by this slice:**

- The serve configuration of the five scorecard subjects was unrecorded;
  **now partly known** (fix-wave review, 2026-08-04, measured by calling
  `mesh_to_tree.auto_mesh_to_metric_tree` directly at the serve default on
  each committed mesh): `bird` lands at voxel 96 / prune 0.25 and `humanoid`
  at voxel 96 / prune 0.3, both byte-identical to their `mesh_validation_
  trees.json` CI-tier fixture; `insect` lands at voxel 96 / prune 0.5 this
  session (the committed CI-tier fixture records prune 0.55), so its
  matching residual/`mv_broken` is a verdict match, not a confirmed tree
  match; `fish` (voxel 64 / prune 0.2) and `quadruped` (voxel 128 / prune
  0.3) land on visibly different configurations from their CI-tier
  counterparts (voxel 64 / prune 0.4 and voxel 96 / prune 0.55). Resolved to
  the extent measured (§7.2, §11 criterion 3); not closed further because the
  search is itself sensitive to the mesh-extraction library's pinned version
  (memory `ci-mesh-dep-pins`), so a configuration recorded today is not
  guaranteed to reproduce across a dependency bump — a *recorded* config, not
  a *permanently stable* one.
- `probe_cp_symmetry.py`'s `(raw)` arm is already reconciled at HEAD (§8).
- The axis is not recorded in the artifact; this is a **prerequisite of S4b**
  (§4.3), and so is its **centre** (§4.3).
- `QUAD`'s Linux/OpenBLAS packing basin has never had its own `cardinality` /
  `n_vertices` measured (fix-wave review, 2026-08-04). CI runs
  `ubuntu-latest`, which lands `QUAD` in the basin where `is_bijection` is
  False, so `test_quad_the_negative_control_the_shipped_metric_scored_
  perfect`'s `else` branch (§11 criterion 4) can only assert the
  basin-invariant `symmetric is False` plus the `None` sentinels — it has no
  Linux-measured count to pin the way the macOS branch pins `mv_mismatched =
  6`. Closing this needs a Linux measurement run, not a code change.

---

## 11. Acceptance criteria

1. `star-4 + pairs` and `HSHAPE` assert `cp_symmetric is True` through the serve
   path, in CI, on Linux.
2. `TEMPLATE_QUADRUPED` is pinned red at `mv_broken = 2` with its offending
   crease pair recorded.
3. **`bird` is pinned in both tiers.** ⚠ CORRECTED 2026-08-04 (fix-wave
   review): this criterion originally predicted the scorecard-tier and
   CI-tier `bird` were different trees, quoting `0.318880` as the
   scorecard-tier residual. Both halves are wrong. `0.318880` is
   `probe_cp_symmetry`'s bare-compile voxel-64/prune-0.30 reading (§1.2's
   table), never the scorecard's — the scorecard's actual committed
   `cp_mirror_residual` for `bird` is `0.053492`. And re-running
   `auto_mesh_to_metric_tree` at the serve default directly on `bird.glb`
   shows it lands on **voxel 96 / prune 0.25**, the exact configuration
   `mesh_validation_trees.json`'s CI-tier `bird` already uses, producing
   byte-identical nodes and `pairs == [[4, 2]]`. The two tiers are therefore
   **the same tree**, pinned twice: both read `cp_symmetric False`, residual
   `0.053492`, `cp_mv_broken None` — geometry failure, assignment
   unevaluated. The same holds for `humanoid` (residual `0.378336` in both,
   confirmed byte-identical nodes at voxel 96 / prune 0.3) and `insect`
   (residual `0.0`, `cp_mv_broken 6` in both, though tree identity there is
   verdict-confirmed rather than node-confirmed — see §10). Only `fish`
   (`0.121893` scorecard vs `0.207713` CI-tier) and `quadruped` (`0.374146`
   vs `0.090551`) are genuinely different trees, because their voxel/prune
   search lands on different configurations. Three of the five committed
   subjects are one measurement pinned under two names, not an independent
   cross-check — see §7.2's matching qualification.
4. `QUAD` is pinned red at `mv_broken = 6` **on the macOS/Accelerate packing
   basin**, reversing the shipped metric's perfect score on the negative
   control it was known to get wrong. ⚠ Verified on macOS only (fix-wave
   review, 2026-08-04). CI runs `ubuntu-latest`, which TreeMaker's ALM
   optimizer resolves to the other packing basin (memory
   `packer-two-basins-scale-lever`); there `is_bijection` reads False, so
   `test_quad_the_negative_control_the_shipped_metric_scored_perfect`'s
   `else` branch pins only the basin-invariant `symmetric is False` and the
   `mv_swapped`/`mv_mismatched` `None` sentinels, not the `mv_broken = 6`
   count. The accommodation is correct and intentionally left as-is (do not
   collapse the two branches) — the count is a macOS-basin measurement until
   the Linux basin's own geometry is characterized (§10).
5. Deleting `cp_symmetric` — or `hull_coverage` — from `_COLS` turns the suite
   red. Verified by actually deleting the line.
6. A test reads `fixtures/scorecard_baseline.jsonl`.
7. `mv_repair`'s two mirror tests pass unmodified, and the nine committed
   goldens produce byte-identical `mirror_map` results before and after the
   refactor.
8. The tripwire renders every reported offender as two stroke colours on one
   segment, and the committed SVG is regenerated.
9. `probe_cp_symmetry.cp_symmetry` and `fold_and_look.cp_mirror_residual` no
   longer exist.

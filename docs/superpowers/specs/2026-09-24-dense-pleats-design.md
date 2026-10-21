# Dense pleat construction and interleaved assignment (gap 1)

**Status:** design approved 2026-09-24. Supersedes nothing; additive to the
box-pleat compiler merged in PR #193.

**Goal.** Make the box-pleat compiler emit crease patterns that read as
box-pleated patterns rather than as COrigami's "step 1", by adopting
COrigami's pleat construction (F.1.1) and interleaved M/V assignment (F.2),
and measure what that costs the layer pipeline.

---

## 1. The observation this starts from

The owner's report: the crease patterns in the box-pleat gallery still look
like COrigami's Figure 5 step 1 (a packing crease pattern -- hinges and ridges,
no pleats). That report is accurate, and the cause was measured rather than
assumed.

## 2. What was measured (2026-09-24, on this HEAD)

**The density already exists; it is discarded at labelling.** `contours.py`
is not sparse. `bird` (N=54):

| quantity | count |
|---|---|
| pieces built by `build_pieces` | 12,868 |
| of which `role='elev'` | 11,144 |
| elev pieces kept as M/V | **688 (6.2%)** |
| elev pieces labelled `F` | **10,456 (93.8%)** |
| ridge / hinge / axial pieces | 476 / 426 / 390 |
| total M/V unit pieces | 1,980 |
| emitted edges after `_merge_runs` | 212 |
| interior vertices in the emitted fold | 81 |

Every ridge, hinge and axial piece is kept: 476 + 426 + 390 = 1,292, and
1,980 - 688 = 1,292. **`role_F` is exclusively `elev`.** So what survives is
the packing crease pattern plus 6% of the pleats -- which is precisely why the
output reads as step 1.

**The discard site is one branch**, `assign.initial_readings` (`assign.py:244`):

```python
elif lab in ("M", "V"):
    pleat_lab[i] = lab      # a VARIABLE, seeded from the elevation profile
else:
    labels[i] = lab         # hard-PINNED to "F"; never enters the search
```

`label_from_profile` (`assign.py:226`) returns `F` for a monotone elevation
slope, and on a large smooth field most cells sit on a monotone slope.

| subject | pieces | hard-pinned `F` | free variables |
|---|---|---|---|
| lizard (N=34) | 5,140 | 4,392 | 96 (48 pleat + 48 centre-column) |
| bird (N=54) | 12,868 | 10,456 | 1,078 (1,000 pleat + 78 centre-column) |

**Candidate coverage of the half-grid** (unit segments occupied / total):
~~`starfish` 94.4%, `lizard` 54.8%, `bird` 54.7%.~~

⚠ **WITHDRAWN 2026-09-28. These three figures are UNREPRODUCIBLE and no
committed script computes them.** Struck rather than deleted because three later
documents quote them. Measured 2026-09-28 over unit segments on the integer
half-grid `[0, 2N]`, excluding those lying along the paper boundary
(`contours.is_boundary_seg`), keyed with `contours._key`:

| subject | N | non-boundary segments | occupied | coverage | claimed above |
|---|---|---|---|---|---|
| `starfish` | 4 | 112 | 54 | **48.2%** | 94.4% |
| `lizard` | 34 | 9,112 | 4,488 | **49.3%** | 54.8% |
| `bird` | 54 | 23,112 | 11,534 | **49.9%** | 54.7% |

`starfish` is out by **46 points**, and the claim that it was a high-coverage
subject is false: coverage is **48.2%–49.9% across N = 4 to 74**, a band under two
points wide. The `occupied` column is corroborated on six subjects by
`../evidence/2026-09-26-gap1-phase0/phase0.json`'s `dense_candidate_pieces`, all
exact. Script, artifact and full record:
`../evidence/2026-09-28-pleat-grid-headroom/` and
`2026-09-28-pleat-grid-headroom-design.md` §9. The direction does **not** favour
this spec's hypothesis — real coverage is *lower*, so the gap is larger.

**Emitted patterns are locally valid, just thin.** On starfish, bird, lizard,
horse, octopus and frog, `cp_audit.audit_fold` reports zero Maekawa, zero
Kawasaki and zero arrangement violations at every interior vertex.

**`emit.py:31` drops every `F` piece** (`keep = [... if l != "F"]`), so an
emitted FOLD contains only M, V and B. Any "F fraction of the crease pattern"
is therefore a statement about the candidate piece set, never about the file.

## 3. Prior art (CLAUDE.md section 0)

Read 2026-09-24: COrigami, *An AI Pipeline for Co-Designing Flat-Foldable
Visually Recognisable Origami* (arXiv:2606.26299), sections 3.2, 3.3 and
appendix F.

**Adopted.**

* **F.1.1 pleat construction**, five steps: (1) a dense continuous orthogonal
  grid mapped across the sheet; (2) split into candidate segments at every
  intersection with hinges and ridges; (3) retain only segments strictly
  perpendicular to an intersecting hinge, or passing through an X-shape vertex
  (four intersecting ridges); (4) selectively re-introduce segments meeting the
  outer border where they share a vertex with both a ridge and an established
  pleat; (5) an iterative pass over remaining unoccupied grid coordinates,
  injecting structurally valid non-intersecting segments "to guarantee
  comprehensive axial coverage and a fully contiguous fundamental grid".
  **Only step 5 is adopted** -- see "Consciously rejected".
* **F.2 interleaving assignment**: pleats grouped into paths of connected
  segments; paths sorted by distance from the origin; BFS assigning fold
  orientations, with adjacent paths separated by a single grid unit taking
  alternating Mountain and Valley.
* **The deterministic/combinatorial split** (appendix F preamble): "step 1 and
  step 2a are essentially deterministic and do not involve decision making.
  Step 2b on the other hand involves multiple assignment options for each hinge
  crease and is therefore combinatorial in the number of hinges."

**Already present in this codebase, confirmed by reading:**

* **F.2's first bullet is implemented.** `assign.pleat_paths` groups connected
  contour pieces into single variables and cites COrigami F.2 by name in its
  docstring. What is missing is the *ordering* and the *alternation*.
* **Section 3.2's "Tiling (via Flap Expansion)" is closed.** COrigami
  eliminates residual gaps by computing feasible expansions of adjacent flaps
  and backtracking to a non-conflicting set. `pack.py` already does this
  ("gap fill grows from the polygon frontier", "finger-seeded gap fill", "gap
  fill by band units"), and polygon packing's rule 4 -- every cell belongs to
  some polygon -- is measured at `hull_coverage` = 1.000 on every emitted fold.
  An earlier gap list called this open. It is not.

**Consciously rejected.**

* **F.1.1 steps 1-4 as a replacement for `contours.py`.** Rejected because
  `contours.py` produces a global *elevation field*, and both the Maekawa CSP
  (`assign.profiles`, `label_from_profile`) and the layer stage consume it. The
  paper's filter produces segments, not elevations, and specifies no
  replacement for the field. Measured cost of the rejection: our candidate
  coverage is ~~54.7%~~ **≈49%** of the half-grid rather than contiguous (the
  54.7% figure is withdrawn — see §2), which step 5 is adopted to close.
  ⚠ **And step 5 was then measured to have NOTHING TO CLOSE**: `pleat_grid.fill`
  under its own no-invention contract would inject **zero** segments on all seven
  subjects measured, because every unoccupied segment is a *slope* — endpoints at
  different elevations, so not a level line at any elevation. See
  `2026-09-28-pleat-grid-headroom-design.md` and its evidence directory. The
  coverage deficit is real; the component adopted to close it cannot.
* **F.3 deterministic ridge assignment** (Y-shape anchors; X-shape same,
  parallel opposite, perpendicular same). Deferred to its own spec, not
  rejected. It is likely the largest cost lever available, because it would
  remove ridges from the CSP and leave only hinges combinatorial, as the paper
  intends. Out of scope here to keep this spec to one subsystem.
  ⚠ **"likely the largest cost lever" is SUPERSEDED, 2026-09-27.** F.3 was
  measured in `evidence/2026-09-27-f3-rules/` and found *"viable but thin"*,
  with the recommendation that **minimal unsat cores are the better-supported
  lever**; cores were then measured as a positive result in
  `evidence/2026-09-27-nogood-core/` (median cause **5** solver variables
  against a pre-core median of 109, `core_variables <= 10` on **31 of 31**
  rows). The deferral stands; the ranking does not.
* **COrigami's own pleat reassignment** ("when a symmetric hinge is assigned,
  it effectively traps a pleat, moving it from the fixed pattern back into the
  unassigned_pleats pool"). Deferred; see section 6, approach C.

**Distinct from our shipped work, recorded to prevent conflation:** this
project already has a feature called pleat reassignment (spec
`2026-09-22-pleat-reassignment-design.md`), which relabels a FIXED crease set
globally under layer-order feedback via CEGAR. COrigami's mechanism of the same
name is a LOCAL trap-and-release during hinge assignment. They are not the same
algorithm and must not be described as such.

## 4. Architecture

Three additive components in `mcp_harness/box_pleat/`, gated by a new
`dense: bool = False` parameter on `compile_tree`.

**With `dense=False`, output is byte-identical to PR #193.** This is a testable
invariant, not an aspiration (section 9).

```
layout + ridges                  (unchanged)
   |
contours.propagate               (unchanged -- the elevation field)
   |
   +-- [dense] pleat_grid.fill   (NEW, component 1: F.1.1 step 5)
   |
assign.build_pieces              (unchanged)
   |
assign.initial_readings          (MODIFIED, component 3: stop pinning F)
   |
   +-- [dense] interleave.assign_paths  (NEW, component 2: F.2)
   |
assign.assign  (CSP)             (unchanged mechanism; smaller free set)
   |
layers / certify                 (unchanged mechanism; see section 7)
   |
emit.to_fold                     (unchanged)
```

### Component 1 -- `pleat_grid.py` (new): F.1.1 step 5

Takes the same inputs `contours.propagate` takes, plus its output. Fills
half-grid unit segments that carry no candidate, so the fundamental grid
is contiguous.

```python
def fill(layout, tree, contours: dict, ridge_pts: dict,
         boundary_ridges: list) -> dict:
    """Return ADDITIONAL {SegKey: elevation} entries for unoccupied segments.

    Never mutates `contours`. Never returns a key already present. An injected
    segment carries an elevation derived from the existing field, never an
    invented one: a segment is injected only where its endpoints' elevations
    determine it uniquely and consistently.
    """
```

**The binding constraint:** an injected segment needs an elevation, because
the field is what `profiles` and the layer stage consume. A segment whose
elevation cannot be derived consistently is **not injected** -- coverage is
sacrificed before the field is corrupted. `contours.py` already treats "a
segment reached at two elevations" as a collision, which supplies the
correctness test directly.

### Component 2 -- `interleave.py` (new): F.2

```python
def assign_paths(paths: list, adjacency: dict, origin: tuple) -> dict:
    """Map path index -> "M" or "V" by COrigami F.2.

    Paths sorted by distance from `origin`; BFS from the nearest; adjacent
    paths separated by a single grid unit take alternating orientations.
    Pure function: no CSP, no geometry construction, no I/O.
    """
```

Consumes `assign.pleat_paths`' existing grouping. A separate helper computes
the adjacency relation between paths.

**Adjacency is the NEAREST parallel neighbour, at no fixed distance**
(amended twice on 2026-09-24; both earlier definitions were measured wrong).
Two paths are adjacent iff they hold pieces that are (a) the same orientation,
(b) aligned on the parallel axis, and (c) mutually nearest -- no third path's
aligned piece lies strictly between them on the perpendicular axis.

**Why no fixed distance, measured rather than argued.** Perpendicular offsets
between aligned parallel pieces of different paths, on the sparse grouping:

| subject | offset 1 | 2 | 3 | 4 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|
| bird | 0 | **288** | 162 | 118 | 100 | - | 54 |
| horse | 6 | 0 | 130 | 224 | **464** | 84 | 116 |

No single distance fits: bird's mode is 2 (one grid unit) and it has no offset-1
pairs at all; horse's mode is 6 and it has no offset-2 pairs at all. Nearest
neighbour is scale-free and needs no constant.

**The two rejected definitions, recorded so they are not re-proposed.**

1. *Proximity*: "within 1 unit orthogonally", no parallelism test. Measured
   `starfish`, `horse`, `octopus` non-bipartite with an odd cycle of length
   **exactly 3** every time -- a perpendicular path crowding two parallel
   pleats closed a triangle. Baseline:
   `evidence/2026-09-24-dense-pleats/bipartite-proximity-PARTIAL.json`.
2. *Facing at exactly 1 unit*: parallel and aligned, distance fixed at 1.
   Produced an **empty** adjacency graph -- `bird` read `edges=0,
   isolated=76`. That is a VACUOUS bipartite pass: an edgeless graph is
   trivially 2-colourable and F.2 over it would colour every path M, which is
   no interleaving at all. The reasoning behind it (contours sit on half-grid
   lines, so 1 is the finest spacing) was true and irrelevant -- offset 1 is
   not a spacing pleats actually use.

**The gate moves to the dense grouping.** An earlier version of this spec
called the sparse grouping "a lower bound on difficulty, since denser grouping
only adds edges". That is wrong. The sparse grouping is not a subgraph of the
dense one: it is a different graph whose spacing is an artifact of the 94%
discard this work exists to remove. A bipartiteness gate run on it cannot
answer whether F.2 is achievable, under any relation. The gate therefore runs
after the dense grouping exists, not before.

### Component 3 -- `initial_readings` change

In dense mode the `else` branch stops writing `labels[i] = "F"`. The piece
becomes a variable, and its path takes component 2's value. Sparse mode's
branch structure is untouched.

## 5. Approach C: interleave, then trap and release

**Approach A was measured impossible on 2026-09-24 and is superseded.** Its
premise -- that F.2's colour can be a single fixed value for every pleat path
-- requires the path-adjacency graph to be 2-colourable. It is not.

**The measurement.** With the dense grouping and the nearest-neighbour
relation:

| subject | paths | adjacency edges | isolated | bipartite | odd cycle |
|---|---|---|---|---|---|
| starfish | 39 | 33 | 0 | yes | - |
| bird | 963 | 1216 | 0 | **no** | **5** |
| lizard | 365 | 482 | 0 | **no** | **5** |
| horse | 809 | 977 | 0 | **no** | **5** |

(`octopus`, `frog`, `guinea_pig`, `dog` unmeasured; the run stopped after
`horse`.) These are dense, fully connected graphs -- roughly 1.25 edges per
path, zero isolated -- so this is not the empty-graph vacuous pass that an
earlier adjacency definition produced. The cycles are length **5**, not the
length-3 triangles the proximity definition produced. And the one remaining
known defect, a path re-entering the same lane, is measured at **0 of 216
lanes** on `bird`, with every member of the reported cycle having exactly one
entry per lane it spans. Five distinct 3-to-4 piece paths are genuinely in an
odd loop.

**This is not an implementation failure; it is the reason the paper has the
feature it has.** COrigami calls pleat reassignment "a critical innovation":
"when a symmetric hinge is assigned, it effectively 'traps' a pleat, moving it
from the fixed pattern back into the unassigned_pleats pool. This deferred
decision-making allows the solver to dynamically flip the pleat's orientation
downstream." If strict alternation always succeeded, that machinery would be
pointless.

### 5.1 The mechanism

`interleave.colour` currently returns `(colours | None, OddCycle | None)` and
gives up on an odd cycle. It becomes:

```python
def colour(pieces, groups) -> tuple[dict[int, str], frozenset[int]]:
    """F.2 with trap-and-release. Returns (colours, released).

    BFS 2-colours as before. When an edge closes an ODD cycle, the endpoint
    that closes it is RELEASED rather than coloured, and colouring continues.
    A released path carries no F.2 colour: it returns to the solver's
    variable pool with the ordinary domain ["M", "V"], which is this
    pipeline's form of COrigami's `unassigned_pleats`.
    """
```

**Release selection is GREEDY** (owner, 2026-09-24): the endpoint closing the
cycle is released, in O(1). The principled alternative -- a *minimum* odd-cycle
transversal, which would give up as little of F.2 as possible -- is NP-hard and
is deliberately not attempted. Greedy may release more paths than strictly
necessary; section 5.3 measures how many, which is the evidence for whether
that ever needs revisiting.

**There is no failure mode left.** Releasing an endpoint of every odd cycle
makes the remainder bipartite by construction, so `colour` always returns an
answer. `OddCycle` and the `AssignFail("f2_odd_cycle", ...)` kind are removed:
nothing can produce them.

### 5.2 Consequences for the two rulings

* **Section 6's precedence ruling gains a carve-out.** "F.2's pleats outrank
  CEGAR" continues to hold for **coloured** paths. A **released** path was
  never F.2's to own -- the whole point of releasing it is that the solver
  decides it -- so CEGAR may relabel released paths freely. Without this
  carve-out a released path would be pinned by a rule that no longer has an
  opinion about it.
* **The bipartiteness gate stops being a gate and becomes a metric.** Nothing
  halts on a non-bipartite graph any more. What it produces instead is the
  release count.

### 5.3 The release count is the headline measurement

Per subject, record: total paths, paths coloured, **paths released**, and the
release fraction. It states exactly how much of F.2 survived contact with our
geometry, and it is the number that decides whether greedy selection is good
enough or a better transversal is worth building. A release fraction near zero
means F.2 essentially holds and the odd cycles are a rounding error; a large
fraction means the interleaving is mostly advisory and the CSP is doing the
real work -- a materially different claim, and one this project must not make
without the number in front of it.

## 6. Precedence: F.2 SEEDS, CEGAR decides (reversed 2026-09-25)

**This reverses the 2026-09-24 ruling that F.2's pleats outrank CEGAR.** That
ruling was made when strict F.2 still looked achievable; measurement has since
disproved that twice, and then showed the ruling itself was what blocked
convergence.

**The measurement that forced the reversal.** On dense `lizard`:

```
assign (no layer check)     0.76s
to_fold                     0.00s   edges=759
flat_fold                   0.01s   faces=380     (sparse: 20)
constraints_for             3.65s   pairs=53,754
layers.propagate            1.00s   -> CONTRADICTION (taco-tortilla)
layers.certify              0.93s   -> REFUTED
```

⚠ **CORRECTED 2026-09-26: a complete dense candidate does NOT cost 6.4
seconds.** Summing the column above treats two ONE-TIME costs as per-candidate:
`constraint_graph` is cached in `compile._check`'s `graph_cell` and built once
(`compile.py:292`), and `certify` runs once after `assign` returns, outside the
CEGAR loop (`compile.py:347`). **Measured per-candidate layer cost: 1.577 s**
(`evidence/2026-09-26-nogood-indexing/wtg-lizard-500k.json`). The conclusion
this sentence drew -- that per-candidate cost was never the problem -- still
holds, and holds more strongly at 1.577 s. But the 6.4 s figure was reused as a
constant in a later cost apportionment and produced a false conclusion there,
so it is corrected here at the source.

⚠ **ALSO CORRECTED 2026-09-27: "756 seconds over six candidates" is supported
by no committed artifact, and the correction above had been spliced into the
middle of the sentence carrying it, leaving that sentence dangling.** The
committed diagnostic for dense `lizard` at the same 500,000-node budget reads
**113** candidates refused over **834.0 s**
(`evidence/2026-09-24-dense-pleats/nogood-lizard.json`, `partial: false`), and
the 10x run reads **584** over **8,865.1 s**
(`nogood-lizard-largebudget.json`) -- see §6.3.1. The 756 s / six-candidate
reading came from an ad-hoc run whose output was never committed; it is not
reproducible from anything in this repository and must not be cited. What
survives unchanged is the qualitative point: `compile_tree(dense=True)`
exhausted the 500,000-node budget without converging.

**The original sentence, left visible rather than erased:** "A complete dense
candidate costs about 6.4 seconds, so this was never a performance problem. But
`compile_tree` ran 756 seconds and exhausted a 500,000-node budget over six
candidates without converging."

**The cause is structural, not a defect.** The pleat-reassignment feature
(spec `2026-09-22`) repairs a layer-order contradiction **by flipping pleat
labels** -- that is its only lever. Pinning F.2's colours fixed 413 of 480
pleat variables, so the repair loop could flip only ridges, hinges and the
~14% of pleats that were released. We removed the degree of freedom the repair
mechanism depends on and then asked it to repair, so it burned the budget
discovering it could not.

### 6.1 The rule

**A coloured pleat variable's domain is `[f2_colour, flip(f2_colour)]`** -- the
F.2 colour first, so the solver tries it first and the first candidate offered
is exactly F.2's labelling, but the search may override it when the layer order
demands. Released and conflicted variables keep the two-element domains they
already had.

**No pleat variable has a one-element domain any more.** Two consequences:

* The CEGAR no-good filter that excluded coloured pleats is **removed**. It
  existed only because a no-good over a one-element domain can never be
  satisfied. With every domain at two values, every pleat variable is a
  legitimate target for a no-good clause, which is precisely the point.
* `pleat_vars`, `released_vars` and `conflict_vars` no longer differ in domain
  SIZE. They are now a record of **what F.2 had an opinion about**, and remain
  worth carrying for exactly that reason.

### 6.2 The new headline measurement

The release count alone no longer states how much of F.2 survived, because the
solver may now overrule a coloured path. Report, per subject:

* paths coloured by F.2, released by odd cycle, released by colour conflict
  (as before), and
* **pleats the CEGAR loop flipped away from F.2's colour** -- computed by
  comparing the emitted label of each coloured variable against the colour F.2
  assigned it.

The honest statement of F.2's influence is coloured-minus-flipped over total.
An earlier version of this spec reported only the odd-cycle release count and
read 0.52% on `bird`; the true figure once colour conflicts were counted was
13.96%. **A metric only counts the failure modes it has a name for**, and this
section exists so the third one does not go the same way.

## 6.3 OUTCOME: dense labelling works; dense layer-consistency does not

**Measured 2026-09-25. This section supersedes the success criteria in section
1 and is the result this spec ends on.**

**What works.** Dense pleat construction and F.2 interleaving produce a
complete, locally flat-foldable labelling of `lizard` in **0.76 seconds** --
4,868 M/V pieces against 476 sparse. Every interior vertex satisfies Maekawa,
Kawasaki and `cp_audit`'s arrangement oracle. The local CSP is not merely
adequate but easy, because F.2's seeding makes it nearly deterministic.

**What does not work.** No globally stackable labelling is reachable.
`compile_tree(dense=True)` on `lizard` exhausts a 500,000-node budget after
880 s having tried **113** candidate labellings, every one refused by the
layer-order checker. Sparse subjects converge in 5 to 22 candidates.

**The cause, measured: each no-good prunes too little.** Instrumenting
production's own `global_check` over those 113 rejections (artifact
`evidence/2026-09-24-dense-pleats/nogood-lizard.json`, `partial: false`):

| reading | value |
|---|---|
| rejections | **113** |
| distinct contradictions | **113 of 113** |
| most-repeated contradiction | 1x |
| clause size in **creases** (`len(keys)`) | min 39, median **2,069**, max 3,161 |
| clause size in **solver variables** (`len(clause)`) | min 6, median **202**, max 259 |

**Two units, reported separately on purpose.** `len(keys)` counts implicated
unit creases; production's clause is a dict over **solver variables**, strictly
smaller once run-merging, pleat-path grouping and mirror-merging have collapsed
several creases onto one variable -- median 2,069 creases become median 202
variables. Do not reason from an exponent over either figure.

**The loop is learning, not spinning.** All 113 rejections are distinct;
nothing recurs. So the operational picture is that the space of distinct
layer-order contradictions in a dense pattern is very large, and a clause over
~202 variables removes too small a slice of it to exhaust that space within the
budget tried.

**An earlier revision of this section was wrong twice, both times in the
instrument rather than the system.** (1) It read **"38 distinct of 113, one
repeating 15x"** from a throwaway probe that identified a witness by a
**40-character truncated slice** of its `repr`, so distinct contradictions
sharing a face triple collided into one bucket; the committed diagnostic hashes
the full frozen `Witness` and reads 113 of 113. (2) It argued from "a no-good
over 2,069 **variables**" -- the wrong unit, in the direction that flattered
the conclusion.

**The claim weakens with them.** The earlier text said *"no budget increase can
converge this"*. That followed from the repetition reading and is
**withdrawn**. What was measured is that dense layer-ordering does not converge
within 113 candidates and a 500,000-node budget -- not that it cannot.

### 6.3.1 The large-budget run (2026-09-26): 10x does not converge either

The run the withdrawal above called for has now been performed:
`assign_budget` 5,000,000, rejections effectively unbounded, wall-clock cap set
above the expected finish so the node budget is what binds. Artifact
`evidence/2026-09-24-dense-pleats/nogood-lizard-largebudget.json`
(`partial: false`); full analysis in that directory's README.

`lizard` refused **584** candidates over **8,865.1 s** and stopped on
`AssignFail(kind='budget', site=5000000)`. All 584 contradictions distinct.
Clause size unchanged at median **204.5 variables** (202 at the default
budget).

**Three readings that bind future plans:**

1. **Budget buys candidates sublinearly** -- 10x the nodes gave 5.17x the
   candidates (candidates ~ budget^0.71), because nodes per candidate rose
   1.93x and seconds per candidate 2.06x. Paying more gets progressively less.
2. **The learner never self-strengthens** -- 5.17x more experience left the
   clause the same size. This is the strongest support for the minimal-core
   follow-on below.
3. ⚠ **WITHDRAWN 2026-09-26. This read "the per-node slowdown is our own
   unindexed no-good store", from a per-node cost that appeared to grow 4.63x
   against a 5.17x clause growth. Both halves were artifacts of the 6.4 s
   constant corrected in section 6 above.** Directly measured instead
   (`evidence/2026-09-26-nogood-indexing/`): `hits_nogood` is **1.28% of total
   time** (upper bound), and **per-node cost is essentially FLAT** -- 1,668
   us/node at 500k versus 1,773 us/node at 5M, 1.06x. Nodes per candidate grew
   1.93x and seconds per candidate 2.06x, so **the whole slowdown is more nodes
   per candidate, not slower nodes** -- a learning search backtracking further
   as clauses accumulate, which is correct behaviour rather than a defect.

   **What the measurement found instead:** the **local CSP search is 79.57%** of
   dense `assign`'s time (`global_check` 19.15%). That makes **F.3 deterministic
   ridge assignment** -- which removes ridges from the CSP -- the best-supported
   remaining lever, on measurement rather than inference. The no-good indexing
   spec (`2026-09-26-nogood-indexing-design.md`) is WITHDRAWN unimplemented.

   ⚠ **The F.3 RANKING in the paragraph above is SUPERSEDED 2026-09-27; the
   79.57% apportionment it rests on is not.** F.3 was then measured at variable
   level (`evidence/2026-09-27-f3-rules/`) and found **thin**: of its three
   rules, one is already implemented here under another name (the mirror merge),
   one is inert on our geometry (0-1 X-shape vertices corpus-wide), and the
   residual governs roughly 5-10% of the CSP. Minimal unsat cores were measured
   next (`evidence/2026-09-27-nogood-core/`) and came back **positive**: the
   median actual cause of a rejection is **5 solver variables** where the clause
   states 109, and every one of 31 rejections had a cause of 10 or fewer. This
   is the third of three sites in this file stating the superseded ranking; the
   other two are annotated in section 3 and section 12.

**"Cannot converge" is still NOT restored.** 584 candidates is no more a proof
of impossibility than 113 was. What is established is that **convergence by
budget is economically implausible**: sublinear returns, per-candidate cost
doubling as the store grows, and a clause that never tightens. The gap must be
closed by pruning harder or searching less, not by paying more.

**This raises a DOUBT about the already-shipped pleat-reassignment feature --
not a finding.** That wave measured its own no-good clause at 125 of 249
variables, a fraction comparable to the 202 here, and it converges only because
sparse subjects need 5 to 22 candidates, so a weak learner is never stressed.
Whether it degrades the same way at a larger crease set is **untested**.

**What ships from this spec:** dense labelling behind `dense=False`, inert by
default and byte-identity-verified across all eight subjects; the measured
negative above; and the three superseded adjacency definitions with the
measurements that refuted each.

**The follow-on, not attempted here:** a minimal unsat core for the no-good
clause, in place of the whole dependency set. Shrinking a median **204-variable**
clause (2,117 creases) toward tens of variables is the root-cause fix, would
likely speed the shipped sparse feature as well, and needs its own spec --
minimal cores are themselves expensive to compute, so it is a real research
question rather than a refactor. Section 6.3.1's reading 2 is the direct
evidence for it, and the large-budget run's crease-frequency figures (a set of
creases in ~99.5% of all 584 clauses, while the union covers essentially every
crease) are the shape expected when `piece_keys`' dependency set drags
propagation hubs into every witness -- suggestive that the real core is far
smaller, but not itself a measurement of its size.

**A follow-on this spec briefly proposed and then RETRACTED:** indexing the
no-good store. Specced (`2026-09-26-nogood-indexing-design.md`) and withdrawn
unimplemented the same day, once the scan was measured at 1.28% of total time.
Recorded so it is not re-proposed: the mechanism is sound, the target is
negligible.

## 7. Certification is reported, not blocking (in dense mode only)

Owner ruling, 2026-09-24. `compile.py` keeps its `CERTIFIED` refusal exactly as
merged **for sparse mode**. In dense mode the verdict is computed, recorded per
subject, and the base is emitted regardless.

The bypass is a named parameter, not a relaxed check. Sparse mode's guarantee
-- "no base emits with a layer contradiction" -- holds everywhere it held
before this spec.

**Stated plainly, because the trade-off is real:** dense mode can emit crease
patterns this project cannot prove fold. That is an accepted cost of the chosen
success bar, and every dense result must carry its verdict beside it.

**Compute-and-report was chosen over skipping certification entirely** (owner,
2026-09-24), so do not later "optimise" the verdict away as dead work. The
verdict is the deliverable: section 1's goal is half measurement, and a dense
result whose foldability is simply unknown teaches nothing about the cost curve
in section 10. Where the verdict is unaffordable it must be recorded as
UNDECIDED with its budget, which is information; silence is not.

## 8. Sequencing

1. **Components 2 + 3** (F.2 interleaving, unpin `F`), then measure.
2. **Component 1** (F.1.1 step 5 coverage), then measure again.

Components 2 + 3 alone take `bird` from 1,078 free variables to roughly 11,500
and settle the largest unknown in the design -- whether interleaving survives
geometry derived from an elevation field rather than from the paper's grid
filter. Building the coverage pass first would mean debugging two unknowns at
once.

## 9. Testing

* **Byte-identity regression, load-bearing.** With `dense=False`, every
  currently-emitting subject reproduces its committed fold **byte-for-byte**,
  verified by sha256 over the emitted dict, as PR #193 did. This is what makes
  the change additive rather than a rewrite.

  **This constrains BEHAVIOUR, not structure, and it is a licence to refactor
  rather than a ban on it.** A pure refactor produces the same bytes by
  definition, and the sha256 proves it did -- which is a stronger guarantee
  than refactoring a CSP's seeding function normally affords. Encouraged while
  in `initial_readings`: hoisting `on_column` (line 267) into the branch that
  actually reads it; replacing `pleat_lab.get(i) or labels[i]` with an explicit
  `i in pleat_lab` test, since the `or` is correct only because every label is
  a non-empty string; and giving ridge/hinge pieces an explicit `else` instead
  of leaving "free variable, no seed" encoded as falling off the end of the
  branch chain.

  Forbidden, because each changes which solution the CSP reaches first and
  therefore the emitted labels: reordering the centre-column domain
  (`["F"] + [lab, opposite]`, line 278 -- F-first is the deliberate "plan view
  where feasible" preference), and altering `label_from_profile`'s mirroring
  (`if lo is None: lo = e + (e - hi)`). Both look collapsible. Neither is.
* **`interleave.assign_paths` unit tests.** Pure function: hand-built path sets
  with known adjacency and known expected alternation, including a path set
  with an odd cycle in the adjacency graph (where strict alternation is
  impossible) to pin the documented behaviour. **Every count assertion is
  paired with a non-vacuity assertion** -- PR #193 shipped two tests that read
  `0 == 0` against fixtures generating zero of the thing under test.
* **`pleat_grid.fill` tests.** Injected keys disjoint from existing ones;
  injected elevations consistent with the field; a fixture where an elevation
  is NOT uniquely determined, asserting the segment is skipped rather than
  invented.
* **`initial_readings` dense mode.** Hard-pinned `F` count is 0; free variable
  count rises to the measured figures (lizard 96 -> ~4,488; bird 1,078 ->
  ~11,534). Both directions asserted, with the sparse-mode counts pinned too.
* **Infeasibility record.** Populated on a fixture where pinning genuinely
  conflicts; empty on one where it does not. A record only ever tested in one
  direction proves nothing.
* **Precedence test.** In dense mode, a CEGAR search that would flip a pleat
  does not flip it; the same search in sparse mode does.
* **e2e.** Dense mode across the corpus, recording emit, verdict and cost per
  subject. Expected-failure entries carry the measured reason, never a guess.

## 10. Evidence

`docs/superpowers/evidence/2026-09-24-dense-pleats/`, carrying per subject:
pieces, free variables, emitted edges, **faces, face pairs**, verdict, certify
seconds, and infeasible-vertex count -- the cost curve. Plus a **regenerated CP
gallery showing dense beside sparse**, which is the artifact the original
observation asked for.

## 11. Risks

1. **Interleaving may be globally infeasible on our geometry.** Our paths come
   from an elevation field, not COrigami's grid filter; their adjacency
   structure may not admit consistent alternation. This is why section 5
   records rather than merely fails, and why section 8 sequences the
   measurement first.
2. **`flat_fold` and `layer_order` run BEFORE `certify`, and are not
   optional.** Certification was scoped non-blocking, but `to_fold` ->
   `flat_fold` is how the base is built at all, and face-count growth hits it
   first. The wall may arrive earlier than the certify stage. Implementation
   must measure face count and `flat_fold` time per subject and report them,
   not assume the pipeline reaches certification.
3. **`AREA_EPS` degrades exactly as density rises.** Denser pleating means
   smaller arrangement cells, more of which are dropped as slivers, and every
   dropped cell only ever REMOVES constraints. The certificate weakens
   precisely where the pattern becomes more ambitious. Dense verdicts must be
   read with this in mind.
4. **Dense mode ships patterns that cannot be proven to fold** (section 7).
   Accepted; recorded.
5. **Certification cost grows in face PAIRS.** `dog` at 298 faces carries
   30,697 pairs and certifies in 537 s. Dense subjects may be orders of
   magnitude worse. Performance work on the layer pipeline is explicitly a
   follow-on spec, not this one.

## 12. Out of scope

* F.3 deterministic ridge assignment (own spec; likely the largest cost lever).
  ⚠ **2026-09-27: "likely the largest cost lever" is superseded here too** --
  `evidence/2026-09-27-f3-rules/` measured F.3 as viable but thin and ranked
  **minimal unsat cores** above it, and `evidence/2026-09-27-nogood-core/` then
  measured cores positively (median cause 5 solver variables;
  `core_variables <= 10` on 31 of 31 rows). See §3's prior-art F.3 bullet for
  the same note. Still out of scope for this spec either way.
* COrigami's trap-and-release pleat reassignment (approach C) unless section
  5's record says it is needed.
* Layer-pipeline performance work (own spec).
* The serve path. `box_pleat` has zero references in `server.py`; that stays
  true.

# Incremental vertex index for dense `assign`'s variable selection

**Status:** design, pre-implementation. Written 2026-09-29.

**Predecessor:** `2026-09-29-local-csp-profile-design.md` and
`evidence/2026-09-29-local-csp-profile/`. That slice measured what this one
fixes. Read its §1.1 and §8 before this document: the goal is **dense
measurable on more subjects, explicitly NOT convergence.**

---

## 1. The question

The profile located dense `assign()`'s previously-unmeasured 79.57% residual
(740.16 s of `lizard`'s 930.19 s). It is **variable selection**, not constraint
checking:

| component | share of the remainder, 7 large subjects |
|---|---|
| `free_vars_at` | 64.8 – 65.3% (a **lower** bound) |
| `pick` self-time | 32.6 – 34.1% (an **upper** bound) |
| **the two together** | **~99%** — exact; the split is bounds-only, the sum is not |
| `violation` (constraint checking) | **0.3 – 1.5%** |

`pick()` ends in `for v in interior:` (`assign.py:914`) — a from-scratch rescan
of **every** interior vertex at **every node**, each vertex calling `eligible`
→ `free_vars_at`, which builds a set comprehension over the vertex's incident
pieces and then **sorts** it (`:861`). Measured `free_vars_at` calls per node:
28.6 on `starfish`, 4,237.5 on `lizard`, 20,858.0 on `octopus`. The sticky-
vertex fast path that exists to avoid the rescan (`:908`) carries **0.024%** of
`lizard`'s calls.

**And ≥90.4% of those calls return an empty list** — a `cProfile` call-count
ratio from the predecessor's `cprofile-lizard.txt`, explicitly not a share of
time. Most of the work is rediscovering, thousands of times per node, that a
vertex is already fully bound.

Between two consecutive `pick()` calls **exactly one variable changes state** —
bound at `:978`, unbound at `:982` or `:987`. Every per-vertex count not
incident to that variable is unchanged. The rescan recomputes all of them.

### 1.1 What this slice is, and is not

**Is:** replace the per-node rescan with an incrementally maintained index, so
the same vertex is selected with the same tie-break, faster.

**Is NOT a convergence fix, and cannot be.** The predecessor's own ceilings
bound it **per subject**. On `lizard`: removing `free_vars_at` entirely buys
**1.907×** whole-run, and removing `pick` and `free_vars_at` *both* entirely
buys **3.492×**. Those two figures are `lizard`'s and no other subject's, and
neither is a cap on this slice — the pair ceiling spans **1.362×** (`starfish`)
to **112.913×** (`octopus`) across the corpus. See the dated correction in
**§11**. Gap 1's non-convergence needs orders of magnitude on every subject.
A ceiling is also not a
speedup — it prices removing a component *entirely*, which no real optimisation
achieves.

**The goal is the one the predecessor set in its §1.1: more subjects measurable
inside a time budget**, so the corpus for future dense experiments grows.

---

## 2. Prior art (CLAUDE.md §0)

**Adopted.**

* **Watched literals** (Moskewicz, Madigan, Zhao, Zhang & Malik, *Chaff:
  Engineering an Efficient SAT Solver*, DAC 2001). The invariant is *visit a
  clause only when one of its watched literals becomes false*; everything else
  needs no visit and no update. Transposed here: **revisit a vertex only when an
  incident variable changes state.** This is the whole design in one sentence,
  and it is the reason the mechanism is sound rather than merely plausible.
* **Glasgow Constraint Solver issue #879**, "Seven of eleven value-order
  heuristics do work proportional to domain width, at every node"
  (github.com/ciaranm/glasgow-constraint-solver/issues/879). This is the *same
  defect class in a production CP solver*, on the value-order side rather than
  the variable-order side: four of the affected heuristics materialise the
  entire domain into a vector per node, and the report observes that at width
  10⁹ `median` "wants a `vector<Integer>` of a billion entries per node," with
  measured costs of 27 / 258 / 2588 ms at widths 10⁶ / 10⁷ / 10⁸. Its fix
  principle is exactly ours: **compute the shape you need without materialising
  the structure.** §3.1 below is that principle applied — `pick` needs two
  integers, never the sorted list.

**Named, not adopted.**

* **A bucket-queue / priority structure over vertices**, which would let `pick`
  find its minimum without any loop and would approach the 3.492× pair bound.
  Rejected for this slice: it needs correct **increase-key on backtrack** as
  well as decrease-key, and a wrong ordering changes the search silently rather
  than failing loudly. Revisit only if §5 shows the surviving loop dominant.
* **VSIDS** (same Chaff paper) and **conflict-directed ordering** — `wdeg` /
  `dom-wdeg` (Boussemart, Hemery, Lecoutre & Sais, ECAI 2004). These *change*
  the heuristic. This slice's entire correctness argument is that the heuristic
  does not change, so they are out of scope by construction. Chaff's transferable
  lesson is kept, though: a cheaper-to-maintain heuristic can beat a better one,
  because per-node cost is paid at every node.

**Background.** The heuristic `pick` implements is MRV / most-constrained-
variable (Bitner & Reingold 1975; Haralick & Elliott, *Increasing tree search
efficiency for constraint satisfaction problems*, AIJ 1980) with a
degree-flavoured tie-break in the spirit of Brélaz (1979).

---

## 3. The mechanism

### 3.1 The key reduction: two integers, not a sorted list

`pick`'s selection key is `key = (fv[0] not in domain, len(fv))` (`:918`), and
`fv` is `sorted(fv, key=lambda var: (var not in domain, var))` (`:861`). For a
variable in `domain` the sort key's first component is `False` (0); otherwise
`True` (1). **Domain variables therefore sort first**, so:

> `fv[0] in domain` ⟺ **some** free variable at `v` is in `domain`.

The selection key is thus computable from two counts alone:

* `n_free[v]` — the number of **distinct** free variables incident to `v`
* `n_free_domain[v]` — how many of those are in `domain`

giving `key == (n_free_domain[v] == 0, n_free[v])`. No set is built and nothing
is sorted.

**The pleat phase.** `eligible` (`:865`) restricts to `pleat_pref` keys while
any pleat path is unbound, so a third count is needed:

* `n_free_pleat[v]` — free distinct variables incident to `v` that are
  `pleat_pref` keys

`eligible`'s docstring asserts that *"a `domain` variable is never a
`pleat_pref` key"*. That makes the first key component constantly `True` during
the pleat phase. **This slice does not take that on trust:** §4.1 asserts
`not (domain.keys() & pleat_pref.keys())` at index construction. A docstring
claim that the code depends on becomes a checked one.

### 3.2 The index

A new module, `box_pleat/vertex_index.py`, owning:

* `vars_at[v]` — `{var_of[i] for i in inc[v] if i in var_of}`, built once
* `vertices_of[x]` — the inverse, a **set** of vertices per variable
* the three counts above, per vertex
* **two** sets, both maintained at the same time and neither ever rebuilt:
  `nonempty_all` = `{v : n_free[v] > 0}` and `nonempty_pleat` =
  `{v : n_free_pleat[v] > 0}`. `pick` reads whichever the current phase selects.

**Two sets rather than one phase-dependent set, and this is not a style
choice.** `pleat_open` is recomputed at every node (`:901`) and flips in **both**
directions — including on backtracking across the boundary, which a thrashing
search can do repeatedly. A single set whose *definition* changes with the phase
would have to be rebuilt over all of `interior` on each flip, which is the very
O(|interior|)-per-node cost this slice exists to remove, reintroduced on an
unbounded number of nodes. Maintaining both costs one extra set operation per
state change and makes a flip O(1).

Maintenance is O(degree) per state change, hooked at the three sites that mutate
`value`: bind at `:978`, unbind at `:982`, and the backtrack pop at `:987`.
`pick` reads the index; it never writes it.

A variable incident to no interior vertex has an empty `vertices_of[x]`, so its
bind and unbind are a no-op on every count. That is correct rather than merely
harmless: such a variable can never be selected, because `free_vars_at` is only
ever called on members of `interior`.

### 3.3 The three traps

These were found by reading the code, and each would have produced a wrong or
silently-divergent result.

**Trap 1 — variable aliasing. Counts must be over distinct variables, not
incident pieces.** `var_of[i] = min(base, mirror)` (`:688`), so a piece and its
mirror share one variable, and on the axis `x = N` both can be incident to the
same vertex. A counter incremented once per incident piece would overcount that
vertex, changing `len(fv)` and therefore the selection. Hence `vars_at[v]` is a
**set**, and `vertices_of[x]` is a **set** of vertices so that a variable
touching one vertex twice decrements it once.

**Trap 2 — the caller reads only `fv[0]`.** `assign.py:1061` is
`var = pk[1][0]`; the sorted list is never consumed past its first element. So
no list need be built except for the single chosen vertex — once per node rather
than ~4,237 times. The chosen vertex's full `eligible(v)` list **is** still
materialised and returned, so `pick`'s return value is unchanged in type and
content and the change stays behaviourally inert.

**Trap 3 — the tie-break is positional, and iterating a set would silently
break it.** The loop keeps `best` only on strict `<` (`:919`), so among vertices
with equal keys the **earliest in `interior` order** wins (`:772` builds
`interior` as a list). Python set iteration order is hash-based, so looping
`nonempty` directly would pick a different vertex — a *different search*, not a
faster one, and the symptom would be a mysterious identity-gate failure rather
than an obvious bug.

**The fix is to make the implicit tie-break explicit**: minimise
`(n_free_domain[v] == 0, n_free[v], interior_index[v])` over `nonempty`, where
`interior_index` is each vertex's position in `interior`. Minimising that
triple lexicographically is equivalent to "scan `interior` in order, keep on
strict `<`", and it makes the result **independent of iteration order** — so the
index may use any container it likes.

### 3.4 What `pick` becomes

Unchanged: the `now_open` phase check (`:901`), the sticky-vertex fast path
(`:908-912`), the `current[0]` bookkeeping (`:923`), and the return shape.

Changed: `for v in interior` (`:914`) becomes a loop over `nonempty`, with the
key read from the counts and the explicit `interior_index` tie-break, and
`eligible(v)` called **once** for the winner. The sticky fast path also reads
the index first, so an exhausted sticky vertex costs a count lookup rather than
a set build and a sort.

`free_vars_at` and `eligible` remain in the module unchanged. They are the
reference implementation §4.1 checks the index against, and they still serve the
chosen vertex.

---

## 4. Correctness

A correct index selects the same vertex, so the search is **identical, not
merely equivalent**. That is an unusually strong property and the gates exploit
it. Three gates, in increasing strength.

### 4.1 The invariant check — the gate that makes the counters trustworthy

A `verify=True` mode which, **at every node**, recomputes `eligible(v)` the
existing way for every interior vertex and asserts:

1. `n_free[v] == len(free_vars_at(v))` for every `v`
2. `n_free_domain[v] == len([x for x in free_vars_at(v) if x in domain])`
3. `n_free_pleat[v] == len([x for x in free_vars_at(v) if x in pleat_pref])`
4. `nonempty == {v for v in interior if eligible(v)}`
5. the vertex the index selects is **equal** to the vertex the old `interior`
   loop selects, **including the tie-break** — checked by running the old loop
   alongside and comparing, which is affordable only because this mode is
   already recomputing every vertex
6. at construction only: `not (domain.keys() & pleat_pref.keys())` — §3.1's
   docstring claim, now checked

Run on `starfish` (6,806 nodes, 112 vertices) and on `lizard` capped at **200
nodes** (~4,237 vertices each, so ~850,000 checked vertex-states), this
independently checks hundreds of thousands of vertex-states. The `lizard` cap is
named here so it is a stated parameter rather than whatever the implementer's
patience allowed; a full dense `lizard` under this mode is not affordable, and
that is the reason the cap exists.

**This is strictly stronger than byte-identity.** Byte-identity says *the answer*
matched; the invariant says *the counts were right at every step*. A counter
wrong in a compensating way passes the former and fails the latter. It is far
too slow to ship enabled, and is a test-only mode.

### 4.2 Sparse byte-identity

`compile_tree(..., dense=False)` over the 8-subject corpus, index off vs on,
asserting the emitted FOLD is **byte-identical**. Sparse box-pleating backs 10
validated folds; its output must not move at all.

### 4.3 Dense identity, and the chosen-variable-sequence hash

Dense does not converge, so identity is asserted at a fixed 20,000-node budget
on two quantities per subject:

1. the **node count** consumed, and the `AssignFail` payload
2. a **hash of the chosen-variable sequence** — the `var` pushed at `:1061` at
   every node, digested to one hex string per arm

Figure 2 is the point. Node counts alone would pass two searches that diverged
and then reconverged to the same total; the sequence hash fails at the **first**
differing node. It costs one number per arm and does not require running both
`pick` implementations side by side.

### 4.4 Why identity is the right gate rather than a benchmark

If the index changes which vertex is chosen, any timing comparison is
meaningless — the two arms solved different problems. Identity must therefore be
established **before** any speedup figure is quoted, and a speedup measured on
an arm that failed identity is not a result. §5 is gated on §4.

---

## 5. The measurement

### 5.1 The A/B

The 8-subject corpus, dense, at the fixed 20,000-node budget the predecessor
used, index off vs on. The off arm's numbers must reproduce
`evidence/2026-09-29-local-csp-profile/profile.json` within timing noise; a
material disagreement is a finding about the harness, not a speedup.

### 5.2 Figures required, per subject

* wall clock, both arms, and the realised **speedup**
* per-node ms, both arms — comparable because the node counts are identical by
  §4.3
* the **analytic ceiling** beside the realised figure — **that subject's own
  ceiling, recomputed for it** from the predecessor's `profile.json` by its own
  two formulas, `1 / (1 − free_vars_at / total_secs)` and
  `1 / (1 − (pick + free_vars_at) / total_secs)`. **`lizard`'s 1.907× and
  3.492× are `lizard`'s alone and must never be printed beside another
  subject's realised figure.** The pair ceiling spans 1.362× (`starfish`) to
  112.913× (`octopus`), so `lizard`'s bound printed beside `octopus`'s realised
  22.746× reads as a 6.5× overshoot of a ceiling the run is in fact well
  inside. Where the pair's share of total is ≈0.99 the ceiling is numerically
  unstable and must be marked as such rather than quoted as headroom (**§11**)
* sparse compile time, both arms. Expected small — sparse `lizard` is ~6.5 s
  total against ~65 s for a 20,000-node dense search — but sparse cost is what
  gates corpus size, so it is measured rather than assumed
* the count of vertices actually visited per node. This is the mechanism's own
  claim (~10% versus 100%) and it must be **measured**, not inferred from the
  ≥90.4% empty rate. Note the off arm's figure is `|interior|` by construction —
  the loop visits everything — so the comparison's content is entirely in the on
  arm, and `|interior|` itself is worth recording since the predecessor's spec
  had to withdraw a figure for it (that spec's dated §11)

### 5.3 The ceiling discipline, applied to ourselves

The README must state the realised speedup **beside** the ceiling and name the
gap. The predecessor withdrew four of its own figures and had a fifth refuted by
its own run; a speedup quoted without its ceiling is the same failure one level
on. No figure may be carried from this spec into the evidence README without
recomputation from that run's own artifact.

---

## 6. Files

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/vertex_index.py` (create) | the counts, `nonempty`, the maintenance hooks, and the §4.1 invariant check |
| `mcp_harness/box_pleat/assign.py` (modify) | build the index; hook `:978` / `:982` / `:987`; `pick` reads it; all behind the flag |
| `mcp_harness/tests/test_box_pleat_vertex_index.py` (create) | unit tests for the index, with no compile |
| `docs/superpowers/evidence/2026-09-29-vertex-index/` | the A/B instrument, its artifact, and the README |

The module boundary is the point: the counting arithmetic — where Trap 1 lives —
is unit-testable without running a compile, and `assign.py`'s diff stays small
enough to read in one sitting.

---

## 7. Testing

**Unit, no compile** (`test_box_pleat_vertex_index.py`): the counts under bind
and unbind; **Trap 1 explicitly** — a variable incident to one vertex via two
pieces must decrement that vertex once, built as a fixture rather than hoped for
from a real subject; `nonempty` across the 0↔1 transition in both directions;
the phase switch between `n_free` and `n_free_pleat`; and the §3.3 tie-break
equivalence — that minimising the triple equals scanning a list in order on
strict `<`, tested over a **fixed, hand-built** fixture containing at
least two vertices that share a key and at least one three-way tie. Not
randomised: a randomly-generated tie set makes a failure unreproducible, and the
predecessor's experience is that an under-specified fixture is how an assertion
becomes vacuous — a single-vertex fixture would make this one pass for any
implementation.

**Integration** (named files, never `pytest tests/` — 5,167 tests, >3 h): the
§4.2 sparse byte-identity and the §4.3 dense identity, with the cheap subjects
in the suite and the expensive ones in the evidence run.

**Anti-vacuity is required, not optional.** Every identity assertion must be
shown able to fail — the predecessor found five tests on this branch that could
not, including one where the node counter could be deleted outright while the
suite stayed green. Each gate in §4 is to be demonstrated red under a
deliberately broken index, and the demonstration recorded.

---

## 8. What this cannot say

* **Nothing about convergence.** Even a perfect fix caps at 3.492× on `lizard`
  — that subject's ceiling, not the slice's, and every subject has its own
  (1.362×–112.913×; **§11**). Dense still will not converge on any of them, and
  no figure here may suggest otherwise.
* **A ceiling is not a speedup.**
* Nothing about the **CEGAR regime**. The predecessor's ladder had 3 of 8
  subjects at *zero* rejections and the rest at 1 to 10, so the no-good scan at
  500,000 nodes remains unmeasured and untouched here.
* Nothing about the **>8-flap wall**, `layer_order` confluence, or the serve
  path. `grep -c box_pleat mcp_harness/server.py` stays **0**.
* The ≥90.4% empty rate is a `cProfile` **call-count ratio** carried from the
  predecessor, not a share of time and not re-measured here. §5.2 measures
  visited-vertices-per-node directly instead, which is the quantity this fix
  actually acts on.

---

## 9. The default-flip decision

The flag defaults **off** while the slice runs. The slice **ends with an explicit
recommendation on flipping it**, backed by whether §4's gates passed clean on
the full corpus.

This is stated as a deliverable because the alternative is the real risk:
shipping an optimisation permanently behind an off-by-default flag means paying
for the work and never collecting it. A flip is a change to what every dense
compile does, so it is evidenced rather than assumed — but it is not deferred
by default either.

---

## 10. Out of scope

* A bucket queue or any priority structure over vertices (§2, named and
  rejected).
* Any change to the heuristic. The same vertex is chosen, always; that is the
  correctness argument.
* `layer_order.py` — `mv_symmetrize` shares it on the serve path (CLAUDE.md).
* `now_open` (`:901`), measured at 0.19–0.36% of the remainder. A full
  `pleat_pref` scan per node is the same defect class and would yield to the
  same treatment, but it is not worth a slice at that share.
* `violation`, at 0.33–1.46%.

---

## 11. Dated correction, 2026-09-30 (POST-data): 1.907× / 3.492× are `lizard`'s ceilings, not the slice's

**Struck: every phrasing in this spec that let 1.907× and 3.492× read as a
bound on the slice.** Three sites carried it — §1.1 ("The predecessor's own
ceilings bound it"), §5.2 (which *prescribed* printing those two figures beside
every subject's realised speedup), and §8 ("Even a perfect fix caps at 3.492×").
All three named `lizard`, so each was literally true; the implicature was not.
The plan's line-11 reader instruction carried the same claim as an instruction
and is struck with them.

**§5.2 was the damaging one, because it was a prescription.** Obeyed literally,
it prints `lizard`'s 3.492× beside `octopus`'s realised **22.746×** and a reader
concludes the run overshot its own analytic bound by 6.5× — when `octopus`'s own
pair ceiling is **112.913×** and the run is comfortably inside it. §5.2 now
requires the subject's **own** ceiling, recomputed per subject.

**What the run measured.** Realised from
`evidence/2026-09-29-vertex-index/timing.json` (`dense.wall_speedup_min`);
ceilings recomputed here from `evidence/2026-09-29-local-csp-profile/profile.json`
by the two formulas §5.2 now names:

| subject | realised | `free_vars_at` ceiling | **pair ceiling** | `global_check` % of total |
|---|---|---|---|---|
| starfish | 1.095× | 1.216× | 1.362× | 30.23% |
| lizard | 2.449× | 1.907× | **3.492×** | 26.81% |
| frog | 4.843× | 2.310× | 6.950× | 12.82% |
| horse | 3.232× | 2.134× | 5.172× | 18.13% |
| bird | **28.154×** | 2.837× | (79.837×) | **0.00%** |
| guinea_pig | 4.585× | 2.325× | 7.402× | 12.68% |
| octopus | **22.746×** | 2.871× | (112.913×) | **0.00%** |
| dog | 5.728× | 2.854× | (101.384×) | **0.00%** |

Realised **exceeds 3.492× on five of the eight subjects**, and the pair ceiling
spans **1.362× to 112.913×** — a factor of 83 between the loosest and tightest
subject. There is no single number here to quote.

**The mechanism, and it is the predecessor's own finding.** `bird`, `octopus`
and `dog` read `global_check_secs: 0.0`: inside 20,000 nodes they never
completed a candidate, so no layer-check time exists to floor the ratio and
~99% of their total time *is* the `pick` + `free_vars_at` pair (shares 0.9875,
0.9911, 0.9901). The five subjects that did reject carry 12.68%–30.23% of total
in `global_check`, and that floor is what holds their ceilings down to
1.362×–7.402×. The ceiling is therefore a statement about how much of a
subject's time is *outside* the component, not about the component itself.

**The three bracketed ceilings are numerically unstable and must never be
quoted as precise headroom.** `1/(1 − x)` with `x ≈ 0.99` divides by ≈0.01, so
the figure is arithmetic about a near-zero denominator. Measured sensitivity: a
**0.1% relative** error in `x` moves the ceiling by **8.6% (`bird`), 11.1%
(`dog`), 12.5% (`octopus`)** — roughly a hundredfold amplification. That is
precisely why the predecessor declined to present them in its own headroom
table, and why this spec brackets them: the *shape* (two orders of magnitude,
unfloored) is the content; the digits are not. Treat them as "unfloored", never
as that much available headroom.

**This spec's own §5.3 already forbade the error it made.** §5.3 says: "No
figure may be carried from this spec into the evidence README without
recomputation from that run's own artifact." §5.2 then handed the README two
pre-computed figures to carry. The evidence README obeyed §5.3 rather than
§5.2 — it recomputed all sixteen ceilings per subject — and its run is what
refuted the prescription. This correction is the spec enforcing its own rule on
itself, which is the fifth figure this branch has withdrawn and the second to be
refuted by its own slice's measurement (the first is the predecessor's §11).

**What is NOT struck.** "A ceiling is not a speedup" stands unchanged and is
load-bearing: a ceiling prices removing a component *entirely*, which no real
optimisation achieves, so realised sitting at 0.62–0.80 of the pair ceiling on
the five floored subjects is the expected shape rather than a shortfall. §1.1's
conclusion also stands, and is the reason this correction changes no decision:
**this is not a convergence fix.** Zero subjects moved from budget-capped to
solved, every one of the seven still reads `stage_reached: assign` on both arms,
and a 28× cheaper search is a measurement affordance, not a solution.

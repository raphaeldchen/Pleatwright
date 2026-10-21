# Layer-order certification (`layer_certify`) — design

**Status:** design, 2026-09-23. Supersedes nothing; implements the follow-up
that `2026-09-22-pleat-reassignment-design.md` §10 defers and §12 sizes.

## 1. Why

Every layer-order verdict this project reports means "no contradiction was
found by this propagation." It has never meant "a consistent layer order
exists." `layer_order`'s own docstring says so: it "derives FORCED relations
only; it does NOT decide whether a total order exists, so 'no contradiction'
is weaker than ADK's satisfiability result."

The box-pleat bar now depends on that hedge. Spec §12 measured how large it
is, and the answer splits sharply: on 5 of the 8 emitting subjects propagation
already forces **every** overlapping face pair, so the missing work there is a
polynomial check, not a search. This spec builds that check, plus the small
search the other three need.

## 2. What changes, and what must not

**Changes.** Box-pleat's `layers` stage reports a three-valued verdict —
`CERTIFIED`, `REFUTED`, `UNDECIDED` — instead of `consistent` /
`contradiction`. `consistent` stops being reported, because it names the thing
we could not establish.

**Must not change.** `mcp_harness/layer_order.py` is **not edited by this
work**. Four shipped callers read it — `mv_symmetrize._LayerGate`
(`mv_symmetrize.py:594`), `mv_repair` (`:857`), `root_rank` (`:534`) and
`server.py`'s serve gate (`:2736`) — and every serve-path reading on record,
including `quadruped`'s `contradiction → consistent` from the root wave, was
taken with the propagation-only rule. Changing that module's verdict would
silently re-decide five served subjects and the root-wave scorecard. The
blast radius is held to box-pleat **structurally**, by putting the new code in
a new module, not by convention. Whether the serve path should adopt this is a
separate spec with its own scorecard measurement.

## 3. Prior art (CLAUDE.md §0)

| Source | What it gave | Adapted / rejected |
|---|---|---|
| Akitaya, Demaine & Ku, *Computing Flat-Folded States*, OSME 2024 (Origami8) — [erikdemaine.org](https://erikdemaine.org/papers/FlatFolder_OSME2024/) | The facewise formulation `layer_order` already cites, and the result this spec needs: a facewise layer order is **verified** in `O(min{n²p, n²+mp²}) = O(n³)`, so verifying is in **P** while finding one is in **NP**. Five constraint families stated as clauses. Computing *all* folded states costs `O(n³ + Σ tᵢ³2^tᵢ)` over components of `tᵢ` unassigned variables. | **Adapted:** the five clause forms verbatim as the verifier's specification; the component decomposition as the search's preprocessing. **Rejected:** their per-component brute force over all `2^tᵢ` assignments, because we need **one** satisfying order, not an enumeration of all folded states — see §4.4. |
| Flat-Folder (Ku 22), the paper's open-source implementation, with three public CP datasets | An independent implementation to differential-test against. | **Deferred, not rejected:** recorded as follow-up. Wiring a second toolchain is its own piece of work and the tests in §7 do not depend on it. |
| COrigami (arXiv 2606.26299) appendix D | Their reimplementation of the same ADK formulation: face-pair assignments seeded from M/V labels, propagated through implication tables, remaining variables partitioned into connected components and "solved independently via depth-first backtracking with constraint propagation." | **Adapted:** confirms propagate-then-branch is the standard shape, and that seeding from M/V (our `direct`) is theirs too. **Note:** their §3.3 *search* is scored on LOCAL per-vertex flat-foldability, not on this global CSP, so our CEGAR loop already asks a stronger question than their hinge solver does. |
| This project's own `assign_budget` / `layer_budget` pattern | The house convention for an unbounded search: count nodes, refuse on exhaustion, report the budget as a measured fact. | **Adapted** directly as `decide`'s budget and the `UNDECIDED` verdict. |

Prior art also corrected two claims made while designing this, both recorded
because the corrections are the useful part:

* "Only `starfish` has a real search instance, so skip the enumerator" was
  **wrong**. `bird` and `lizard` have 8 unforced pairs each, which collapse to
  **2** independent variables — 4 assignments. Skipping the search would have
  left two subjects uncertified for want of four checks.
* "`starfish`'s 236 might decompose into many small components" was **wrong in
  the other direction**: its 252 unforced pairs form **one** component. What
  makes it reachable anyway is that `2^tᵢ` is ADK's *enumeration* cost, and we
  need satisfiability.

## 4. Architecture

New module `mcp_harness/layer_certify.py`. It imports `layer_order` and
operates on the `_Constraints` that module's public `constraints_for(result)`
returns. Reading `layer_order`'s private helpers (`_lit`, `_covers_of`,
`_Constraints`) from a sibling module is existing practice — `mv_symmetrize`
and the `probe_*` files do it throughout.

```python
@dataclass(frozen=True)
class Violation:
    family: str        # antisymmetry | transitivity | tortilla_tortilla
                       # | taco_tortilla | taco_taco
    variables: tuple   # the canonical pairs the clause is over
    values: tuple      # what `rel` held for them
    prov: str          # layer_order's provenance text, unchanged

@dataclass(frozen=True)
class VerifyResult:
    violation: Violation | None
    checked: int       # clauses fully evaluated
    skipped: int       # clauses an undecided variable made unevaluable

@dataclass(frozen=True)
class Verdict:
    kind: str          # CERTIFIED | REFUTED | UNDECIDED
    violation: Violation | None   # set only for REFUTED found by `verify`
    nodes: int                    # search nodes spent
    free: int                     # independent variables after `collapse`
```

### 4.1 `clauses(cons) -> tuple`

Materialises ADK's five families from `cons` as explicit clauses. Each clause
is `(family, variables, predicate)` where `variables` are canonical pairs and
`predicate` takes their values and returns True when satisfied.

The mapping from `cons` to ADK, which is also the family diff this spec owes:

⚠ **Corrected post-implementation.** This table originally named five
`Violation.family` values (one per row group below); the shipped
`layer_certify.py` collapses them to three — `equality`, `transitivity`,
`taco` — plus `propagate` (a fourth kind, but not one `clauses` emits: it
names a contradiction `layer_order.propagate` itself raised on a branch,
before any clause was checked, so it has no row here). Tortilla-tortilla
and taco-tortilla (both rows) collapse into `equality`; taco-taco collapses
into `taco`; antisymmetry stays structural, exactly as this table always
said. The `Violation.family` column below names what the code actually
ships, added rather than substituted so the ADK correspondence stays
readable. The finer distinction is not lost: it survives in each clause's
provenance text (`Clause.prov` / `Violation.prov`, e.g. `"transitivity
{a},{b},{c}"`, or the `str(prov)` of the source equality/taco), and
`box_pleat/layers.py`'s `_KIND` table draws exactly this five-way
distinction (`taco-tortilla` / `tortilla-tortilla` / `taco-taco` /
`transitivity` / `crease`) for the OTHER tier, `layers.propagate`'s
`Witness.kind` — so the finer granularity exists in this codebase, just not
as `layer_certify.Violation.family`. This is a documentation correction
only; the code is unchanged (CLAUDE.md binding constraint: do not change
the code to match the spec).

| ADK family | ADK statement | Our source | `Violation.family` |
|---|---|---|---|
| Antisymmetry `(i,j)` | `Λij = -Λji` | Structural: `_lit` gives one canonical variable per unordered pair, so this is unrepresentable-as-violated. No clause emitted; asserted in a test instead. | *(no clause)* |
| Transitivity `(i,j,k)` | `Λij, Λjk, Λki` **not all equal** | Every triple inside one `cons.covers` entry. `_covers_of`'s gating — a triple is admissible only where all three faces stack over one cell — is kept. | `transitivity` |
| Tortilla-tortilla `(i,j,k,k)` | `Λik = Λjk` for `Fk` overlapping unfolded `eij` | `cons.equalities` from `_spanning` over `tortillas`. | `equality` |
| Tortilla-tortilla `(i,j,k,l)` | `Λik = Λjl` for unfolded `ekl` overlapping `eij` | `cons.equalities` from the `combinations(tortillas, 2)` block. | `equality` |
| Taco-tortilla `(i,j,k,k)` | `Λik = Λjk` for `Fk` overlapping folded `eij` | `cons.equalities` from `_spanning` over `creases`. | `equality` |
| Taco-tortilla `(i,j,k,l)` | `Λik = Λjk` for unfolded `ekl` overlapping folded `eij` | `cons.equalities` from the `creases × tortillas` `_collinear_overlap` block. Collinearity is the right restriction here rather than a narrowing of ADK: the transversal case is already covered by `_spanning`, and this block exists precisely because a flat pair's two faces straddle their own edge and are invisible to it. | `equality` |
| Taco-taco `(i,j,k,l)` | `Λik + Λjk + Λil + Λjl ≡ 0 (mod 4)` | `cons.tacos`, consumed as `(vals[0] != vals[1]) == (vals[2] != vals[3])` over `(_lit(r,p), _lit(r,q), _lit(s,p), _lit(s,q))`. **The one family whose FORM differs from the paper's**, so §7.1 tests the two predicates against each other over all 16 assignments rather than assuming they agree. | `taco` |

`clauses` emits no clause any family in `cons` does not already generate. It
changes direction, not coverage: the same constraints, as checks instead of
writes. Any coverage gap this diff exposes is reported as a finding and fixed
in `layer_order`'s builder — which would be an edit to `layer_order.py` and
therefore needs §2 revisited before it is made.

### 4.2 `verify(cons, rel) -> VerifyResult`

Checks every clause from `clauses(cons)` against `rel`. A clause naming an
undecided variable cannot be evaluated; it is **skipped and counted**, and
`skipped` is returned beside the violation so no caller can mistake a partial
check for a complete one. A `CERTIFIED` verdict requires `skipped == 0`.
Polynomial, no search.

This alone certifies the 5 subjects whose `free` count is 0 — `horse`,
`octopus`, `frog`, `guinea_pig`, `dog`, including dog's 180-face stack over a
single cell.

### 4.3 `collapse(cons, free) -> (classes, odd_cycle)`

Parity union-find over the equalities whose **both** variables are unforced.
`cons.equalities` asserts `value(la) == value(lb)` where
`value((pair, flip)) = rel[pair] != flip`, so each equality is a parity edge
and the quotient is the real search space. `classes` maps each free variable
to its representative; `odd_cycle` is a `Violation` when the parity graph
contains one, else `None` — an odd cycle is a contradiction propagation did
not find, and `decide` turns it straight into `REFUTED` without searching.

`collapse` is used to **choose** branching variables, to detect odd cycles,
and to report `Verdict.free`. It does **not** rewrite the CSP: `decide` seeds
only the representative and lets `_propagate`'s existing equality rule fill
the rest of the class, so there is one implementation of the equality
semantics, not two.

Measured 2026-09-23: `starfish` 252 → **114** classes, `bird` 8 → **2**,
`lizard` 8 → **2**, odd cycles **0** on all three.

### 4.4 `decide(cons, *, budget) -> Verdict`

Branch and propagate:

1. `rel = layer_order.propagate(cons)`; a `LayerContradiction` here is
   `REFUTED` with no search.
2. `free = cons.pairs - set(rel)`. If empty, return `verify`'s answer.
3. `collapse` the free variables; pick an undecided class representative.
4. Assign **only that representative** by appending one `direct` entry, then
   re-`propagate`; the equality rule fills its whole class. On
   `LayerContradiction`, try the other value; on both failing, backtrack.
5. On a complete `rel`, run `verify` before returning `CERTIFIED` — the search
   must never certify on propagation's word alone, since propagation is the
   thing being audited.
6. Each node decrements `budget`; exhaustion returns `UNDECIDED` with the node
   count, never a guess.

**The budget, and its measured basis.** `CERTIFY_BUDGET = 50_000` nodes, a
module constant. `starfish` is the only subject on which it can bind — the
other seven have 0 or 2 free variables — and one `propagate` there costs
**2.31 ms** (20-call mean, 2026-09-23; `bird` 50.61 ms but at most ~4 nodes,
`lizard` 0.79 ms). So 50,000 nodes bounds the worst case at roughly **115 s**,
comparable to and below the costs this corpus already carries (`guinea_pig`
295 s, `dog` 578 s). A search that needs more than 50,000 nodes on 114
variables is not going to finish at 500,000 either, so the budget is a
give-up threshold, not a tuning knob — the same role `layer_budget` plays in
the CEGAR loop.

**Why the exponential worst case is acceptable here, and it is not luck we
should rely on silently.** ADK's `2^tᵢ` is the cost of enumerating *all*
folded states; satisfiability needs one. And the corpus aligns favourably: the
subjects with a search (`starfish` 38 faces, `bird` 104, `lizard` 20) are the
ones where a single propagation is cheapest, while the subjects where
propagation is expensive (`dog` 298 faces, `horse` 166) have **zero** free
variables and need no search at all. `starfish` is 114 variables against ~938
non-equality constraints (148 equalities, 90 taco, 848 transitivity over free
variables) — small for a branching search. That alignment is a measured
property of this corpus, not a theorem, which is why the budget exists.

### 4.5 Two tiers: `mcp_harness/box_pleat/layers.py` and `compile.py`

`propagate` **stays exactly as it is** as the per-candidate filter inside the
CEGAR loop: fast (~300 ms on horse, 97% of a check), and sound in the only
direction the loop needs — a contradiction is a valid no-good clause.

`decide` runs **once, on the candidate the loop accepts.** Per-candidate
`decide` was considered and rejected: each rejection already costs a fresh CSP
re-descent, `rabbit` is already unresolved at 500k nodes / ~29 min, and `dog`
takes 578 s; multiplying the per-rejection cost would make the two worst
subjects worse to strengthen a filter that is already sound for refutation.

`layers.py` gains:

```python
def certify(graph: LayerGraph, labels: dict, *, budget: int) -> Verdict
```

built from `graph.cons` with `direct` seeded from `labels` exactly as
`propagate` does — reusing `_seed`, so there is still one copy of that formula.

`compile.py` calls `certify` after `assign` returns, records the `Verdict` on
`Result`, and refuses at stage `layers` on `REFUTED` or `UNDECIDED`.

## 5. Verdict semantics, and what CERTIFIED still does not mean

`CERTIFIED` means: a complete facewise layer order exists for this folded
state and satisfies every clause `clauses(cons)` generates.

It does **not** mean flat-foldable. `AREA_EPS` drops sliver arrangement cells
before `cons.pairs` is built, and a dropped cell removes constraints and can
never add one. So `CERTIFIED` is "certified against the constraint set that
survived `AREA_EPS`". That caveat is load-bearing and goes in the module
docstring, not only here. Closing it is a separate piece of work, and §12's
census cannot see it by construction.

`REFUTED` from `verify` on a relation propagation accepted is a **finding**:
it means propagation was wrong on that input. The `layers` stage refuses,
per the standing ruling that a subject which cannot be labelled consistently
refuses rather than emits. If that drops the reported headline below 8 of 10,
the lower number is the honest one — the previous one was measured with an
oracle that could not refute.

## 6. Pre-registered bar

Measured before any code is written, so the result cannot be read after the
fact:

1. `horse`, `octopus`, `frog`, `guinea_pig`, `dog` → `CERTIFIED`, `free = 0`,
   no search nodes spent.
2. `bird`, `lizard` → decided (`CERTIFIED` or `REFUTED`), `free = 2`, within 4
   assignments, budget untouched.
3. `starfish` → one of the three verdicts, recorded with its node count. **No
   expectation is pinned**; `UNDECIDED` is an acceptable, reportable outcome.
4. Every emitted `.fold` byte-identical to `46e2750`'s output on all 8
   subjects. This work changes what is *claimed*, never what is *emitted*.
5. `git diff` for `mcp_harness/layer_order.py` is empty.
6. No serve-path test changes and no scorecard re-measurement.

## 7. Testing

### 7.1 Taco-taco against ADK's own statement (first test written)

Exhaustively compare our predicate `(v0 != v1) == (v2 != v3)` to ADK's
`Λik + Λjk + Λil + Λjl ≡ 0 (mod 4)` over all 16 assignments, with the paper's
index correspondence made explicit in the test. The paper's Figure 3 gives the
expected split under `Λij = Λkl = 1`: 4 valid rows, 8 excluded by taco-taco, 4
by transitivity. The test asserts our predicate reproduces the taco-taco
column exactly — not the whole table, since transitivity is a separate family.

### 7.2 `verify` accepts a known-good order and rejects a corrupted one

A hand-built 3-face instance with a unique valid order: `verify` returns None;
flip one relation and it returns the `Violation` naming `transitivity`.

### 7.3 `collapse` finds an odd cycle

A constructed equality cycle of odd parity returns `REFUTED` without search.

### 7.4 `verify` refuses to pass a partial relation

Hand a relation missing one variable a clause needs; assert the skipped-clause
count is non-zero and that no caller can read the result as complete.

### 7.5 The search decides `bird` and `lizard`

Both reach a verdict with `free == 2` and fewer than 5 assignments.

### 7.6 Regression: the goldens do not move

The three byte-identity goldens (`starfish`, `lizard`, `bird` v1) still pass,
and all 8 subjects emit byte-identical folds.

### 7.7 End to end

`compile_tree` on all 8 subjects reports a `Verdict`, and the e2e strict table
carries the verdict kind per subject. Slow tier, marked, as the existing e2e
rows are.

## 8. Risks

1. **The headline may drop.** `decide` could refute a currently-emitting
   subject. Accepted per §5; the honest number replaces a number measured with
   a weaker oracle.
2. **`starfish` may burn the budget.** Accepted; `UNDECIDED` with a node count
   is a reportable outcome, as `spider`'s bounded negative already is.
3. **The family diff may find a coverage gap.** Fixing it means editing
   `layer_order.py`, which §2 forbids in this work. Such a finding is
   **reported and deferred**, not fixed inline.
4. **`decide` re-propagates from scratch per node** — `layer_order.propagate`
   is not incremental. Mitigated by the corpus alignment in §4.4 and bounded
   by the budget. Making propagation incremental is a follow-up, not scope.
5. **`Verdict` becomes a third thing the bar reports.** The evidence README's
   table and `LAYERS_EXPECTED` both need the new column, or they will keep
   reporting a field this work deletes.

## 9. Follow-ups, deliberately out of scope

* Adopting the verifier on the serve path, with the root-wave scorecard
  re-measured — needs its own spec (§2).
* Differential testing against Flat-Folder's public datasets (§3).
* Making `layer_order.propagate` incremental so `decide` does not re-run it
  per node (§8.4).
* The `AREA_EPS` under-refutation, which this work does not touch (§5).

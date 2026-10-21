# The SAT layer stage

**Status:** design approved 2026-10-02.

**Goal.** Make the complete layer-ordering query a first-class `compile_tree` stage, so the
dense path decides whether a labelling exists instead of searching for one and running out of
budget.

**Why now.** `docs/superpowers/evidence/2026-10-02-witness-identity-113/` §14–§16 established
all three things this needs: the query is **satisfiable** on dense `lizard` (SAT in 0.2 s), its
witness **emits** a fold four validators accept, and the one caveat that could have undone that
— `AREA_EPS` — is **measured inert** there (0 drops at any threshold down to 0, smallest cell
clearing 1e-9 by 108,131×). What remains is engineering.

**The number that motivates the stage.** On dense `lizard` the shipped path spends **1052.0 s**
(`../evidence/2026-09-27-core-in-loop/ab.json` `arms[0].secs`) and returns
`AssignFail(kind='budget', site=500000)` — no answer. The SAT path answers in **~17 s**.

---

## 0. Prior art (CLAUDE.md §0)

### Adopted

**Akitaya, Demaine & Ku, *Computing Flat-Folded States* (OSME 2024).** The clause families —
equality, transitivity, taco — are theirs, and `layer_certify` already enumerates them from a
`_Constraints`. This spec **translates `layer_certify._iter_clauses` and re-derives nothing**,
so the CNF cannot disagree with the shipped verifier about what the constraints are. Their
result that verifying a facewise order is in P while finding one is NP is exactly why a CDCL
solver is the right tool and `decide`'s hand-rolled branch-and-propagate is not.

**Lang & Demaine, *Facet Ordering and Crease Assignment in Uniaxial Bases* (Origami⁴ 2006),**
already load-bearing in CLAUDE.md §1.1 — the facet-ordering conditions these clauses encode.

**CDCL, via `python-sat` 1.9.dev15 (Ignatiev, Morgado & Marques-Silva) and Cadical (Biere).**
Conflict-driven clause learning with watched literals and activity-based branching, in C,
against `decide`'s pure-Python search and its `CERTIFY_BUDGET = 50_000` give-up threshold.

**`"MILP M/V"`,** on this project's adapt-list since the landscape survey
(`origami-landscape-survey` in memory). **Adapted to SAT rather than MILP**: the constraint
system is already Boolean clauses over pair variables, not linear inequalities, so an MILP
formulation would add a relaxation nobody needs. The adapt-list entry is answered, in a
different solver family, and that substitution is recorded here rather than left implicit.

### Found and consciously rejected

**Encoding a single labelling.** `layer_certify.decide` already decides one labelling
completely — it cites ADK, branches where propagation leaves variables free, and returns
CERTIFIED / REFUTED / UNDECIDED. Encoding that would rebuild shipped work. The
non-duplicative query is the **joint** one, with the labels as variables.

**Tseitin encoding for the taco family.** A taco clause is a 4-literal even-parity constraint;
the textbook encoding introduces one auxiliary variable per XOR. **Rejected** in favour of the
direct 8-clause form: 74,602 tacos × 8 = 596,816 clauses against 74,602 extra variables, and
at this scale a CDCL solver handles the clauses more cheaply than the variables. Recorded
because the choice is not obvious and a future reader should not have to re-derive it.

**MARCO (Liffiton & Sakallah, CPAIOR 2013 / JAR 2016)** for explaining an UNSAT result.
Rejected as **out of scope**: it answers "why unsatisfiable", and that path has never fired —
the one real instance is SAT. Named as the follow-on in §9 if it ever does.

**Chaff's two-watched-literal scheme (Moskewicz et al., DAC 2001).** Already adopted, in
transposed form, by `box_pleat/vertex_index.py`. Not re-adopted here: the solver implements it
internally and this spec writes no propagation of its own.

### Within-project, adapted

`layer_certify.verify` becomes the verdict's source (§4). `box_pleat/layers.py`'s
`constraint_graph` supplies the label-independence contract §3 rests on. The encoder, the
two-sided validation and the guard discipline come from `sat_encode.py` in the evidence
directory, promoted from probe to module.

**Untouched by design:** `layer_order.py`, `layer_certify.py`, `cores.py`, `layers.py`. Four
shipped callers read `layer_order` (`mv_symmetrize._LayerGate`, `mv_repair`, `root_rank`,
`server.py`'s serve gate) and this stage must not perturb any of them.

---

## 1. What exists today

`compile_tree`'s stages are `tree → pack → skeleton → contours → assign → layers → emit`.
After `assign` returns a candidate (`compile.py:552-574`):

```python
res.assignment = asg
fold = to_fold(lay, asg)
ff = flat_fold.flat_fold(fold)
graph = graph_cell[0] if graph_cell else _layers.constraint_graph(ff)
labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
res.verdict = _layers.certify(graph, labels, budget=certify_budget)
...
res.stage_reached = "emit"
res.fold = fold
```

On the dense path `assign` runs a CEGAR loop: `global_check=_check` filters each complete
candidate with `layers.propagate`, and a rejection becomes a learned no-good clause. On dense
`lizard` that loop refutes 113 candidates and exhausts a 500,000-node budget.

**Blast radius.** `box_pleat.compile.compile_tree` has exactly **one** non-test caller,
`probe_box_pleat.py`. `grep -c box_pleat mcp_harness/server.py` is **0**, and `dense=True`
appears nowhere outside `box_pleat/` and `tests/`. The binding constraint is the 21
`test_box_pleat_*` suites, not the serve path.

## 2. Why the CEGAR loop cannot be fixed by tuning it

Measured, in the evidence directory:

* the loop's 113 candidates agree with one another on a median **650 of 745** labels (§7) —
  it never leaves one basin;
* each rejection has **at least 80** minimal causes (§13), so one learned clause excludes
  roughly one-eightieth of why that basin is infeasible;
* the satisfying region sits **308+ of 745** labels from every candidate it tried (§14.2);
* and the witness satisfies every local law `assign` enforces on a complete assignment
  (§15.4), so it was always *inside* the search space.

Five prior slices attacked the search — local-CSP cost, clause width, clause timing, budget
scaling, no-good indexing — and each returned negative. The loop is not slow; it is **learning
the wrong thing**, one clause at a time, and no amount of faster searching changes that.

## 3. Architecture

With `dense=True, sat_layers=True`:

```
tree → pack → skeleton → contours
  → assign(global_check=None)        # FIRST complete candidate, geometry only
  → fold = to_fold(lay, cand); ff = flat_fold.flat_fold(fold)
  → cons, slots = via layers.constraint_graph(ff)
  → SIZE GUARD (§5)
  → sat_order.solve(cons, slots)
      ├─ OVERSIZE → LayerFail("oversize", ...)
      ├─ UNSAT    → LayerFail("unsatisfiable", ...)        a PROOF
      └─ SAT      → witness labelling + complete relation
                    rewrite fold's edges_assignment to the witness
                    res.verdict = verify(cons, relation)
                    → emit
```

### 3.1 `assign` needs no new mechanism

Its main loop reads
`verdict = global_check(cand) if global_check is not None else None`, then
`if verdict is None: return cand` (`assign.py:1230-1232`). So **`global_check=None` returns the
first complete candidate immediately.** The CEGAR loop is not disabled; it is never entered.

### 3.2 The stage needs a geometry, not a labelling

`layer_order.constraints_for`'s docstring states the contract this rests on:

> *"Everything except `_Constraints.direct` depends on the folded geometry alone, which
> `flat_fold` derives from the crease SET -- so a caller may re-propagate this same system
> under any other labelling of the same creases (spec §3)."*

And §15.1 measured it rather than trusting it: flat-folding two labellings of the same crease
set gave **380 faces both ways and a max folded-position difference of exactly 0.0**. M and V
both reflect across a crease, so they give identical folded positions and differ only in which
side lands above — which is why only `direct` moves.

So `assign`'s first candidate is a **scaffold**: the stage uses its geometry and discards its
labels.

### 3.3 The joint encoding

| | dense `lizard`, measured |
|---|---|
| order variables (one per canonical face pair, `layer_order._lit`'s convention) | **53,754** |
| **label variables** (one per crease edge, from `slots`) | **745** |
| equality clauses | 2 × 28,192 |
| transitivity clauses | 2 × **4,511,932** distinct triples |
| taco clauses | 8 × 74,602 |
| label biconditionals | 2 × 745 |
| **total** | **9,678,554** |

Translations, each from `layer_certify._satisfied`'s own predicate:

* **equality** — `vals[0] == vals[1]` → `L0 ↔ L1`, two clauses.
* **transitivity** — `not (rab == rbc and rac != rab)`; the two cyclic states `(T,T,F)` and
  `(F,F,T)` are the only forbidden ones → `(¬a ∨ ¬b ∨ c) ∧ (a ∨ b ∨ ¬c)`.
* **taco** — `(vals[0] != vals[1]) == (vals[2] != vals[3])`, i.e. the 4-way XOR is even →
  forbid all eight odd-parity assignments.
* **label link** — `layers._seed`: `val = (label == "V") == (sign == 1)`. With `Lv` meaning
  "this crease is V", the `DirectSlot`'s constraint is
  `(rel[pair] != flip) == (sign == 1 ? Lv : ¬Lv)`, two clauses.

A literal in `layer_certify`'s clauses is `(pair, flip)` whose value is `rel[pair] != flip`, so
the DIMACS literal is the pair's variable negated exactly when `flip` is set.

## 4. The verdict comes from `verify`, not from `decide`

The SAT model assigns **every** order variable, so a complete relation is already in hand.
Re-running `decide`'s search to find one would cost 15–50 s (measured, §16.1) for an answer we
have.

So the stage computes `layer_certify.verify(cons, relation)` — O(clauses), sub-second — and
reports CERTIFIED when it finds no violation. This is honest on `verify`'s own terms: it checks
every clause `clauses(cons)` generates against a complete relation, which is exactly what
CERTIFIED claims.

**`res.verdict` becomes a new `sat_order.SatVerdict`, not a `layer_certify.Verdict`.** Reusing
`Verdict` would require inventing values for its `nodes` and `free` fields on a path that runs
no search, and a defaulted zero read as a measurement is this project's named recurring
failure. `SatVerdict` carries solver facts instead:

```python
@dataclass(frozen=True)
class SatVerdict:
    kind: str            # CERTIFIED | REFUTED | OVERSIZE
    violation: object    # layer_certify.Violation | None
    order_vars: int
    label_vars: int
    clauses: int
    build_secs: float
    solve_secs: float
```

`kind` keeps the same vocabulary, so a caller reading `.kind` still works.

## 5. The size guard

Clause count scales as `Σ C(|cover|, 3)` over the arrangement cells — **cubic in cover
size**. Dense `lizard` has 26 cells with covers of 168–224 (in steps of 4, each size appearing
twice), giving `C(224,3) = 1,848,224` for the largest and **31,314,680** summed. A subject with
twice the cover would be roughly eight times that.

**The guard must fire before `layer_certify._iter_clauses` runs**, and that rules out an exact
estimate: deduping 4,511,932 triples costs a large Python set, and that set lives *inside*
`_iter_clauses`, which this spec does not modify. By the time an exact count is available the
memory is already spent.

Two stages, neither satisfiable by the other:

1. **`raw_triple_bound(cons) = Σ C(|cover|, 3)`** — microseconds, no allocation. Dense
   `lizard`: **31,314,680**, against the 4,511,932 it dedupes to, so the bound is **6.94×
   loose**. Loose is acceptable; it only has to separate "fine" from "will exhaust memory".
   Over `max_raw_triples` → `OVERSIZE`.
2. **A streaming exact counter** during emission, raising the moment it crosses `max_clauses`,
   so an instance that slips the loose bound still never materialises.

**Defaults, and what they are not.** `max_raw_triples = 100_000_000` and
`max_clauses = 20_000_000` — roughly 3.2× and 2.1× dense `lizard`'s 31.31 M and 9.68 M. They
exist to
admit the one measured instance with headroom and refuse what would exhaust memory. They are
**not tuned**, and no peak-RSS figure appears in this spec because none has been measured. The
plan must measure peak RSS for the dense `lizard` build and, **if it exceeds ~4 GB, lower
`max_clauses` to match** — a number derived from a measurement rather than from this document's
guess.

`OVERSIZE` is a verdict kind and not an exception: "too big to decide" is a fact about the
instance a caller should be able to read and report.

## 6. Failure taxonomy

`LayerFail.kind` currently takes `"no_labelling"`, `"budget"`, `"unfixable"` and
`"uncertified"` (`compile.py:43-44` and the `LayerFail` docstring). Two kinds are added.

| outcome | result | what it asserts |
|---|---|---|
| SAT, `verify` accepts | **emit**, `res.verdict = SatVerdict(CERTIFIED)` | a labelling exists; its order is verified clause by clause |
| **UNSAT** | `LayerFail("unsatisfiable", SatVerdict, 0)` | **a proof**: no M/V labelling of this F set has a valid layer order |
| guard fires | `LayerFail("oversize", (bound, budget), 0)` | nothing about the crease set — too big to decide |
| SAT but `verify` **rejects** | **`SatOrderError` raised, uncaught** | the encoder is under-constrained; never a fact about the tree |

**`"unsatisfiable"` sits beside `"no_labelling"` rather than replacing it, and the two are
INCOMPARABLE, not nested.** `"no_labelling"` comes from a search whose variable domain includes
`"F"` (`assign.py:357` `domain[i] = ["F"] + ...`; `:1085` appends `"F"` to the value order), so it
ranges over F sets but reaches only a subset of labels (its docstring: *"among those reachable"*,
and §15.4 proved the hedge was doing real work — the witness **was** reachable).
`"unsatisfiable"` is complete over M/V labels but restricted to **one arbitrary** F set, the one
`assign`'s first candidate fixed. Each trades one restriction for the other, so neither implies
the other, and **neither localises a defect in the packing by proof**: a different F set on the
same packing may well be satisfiable. A consumer must not re-pack on `"unsatisfiable"` alone.

**`checks` is 0, and falls out correctly.** `counter[0]` counts `_check` calls; with
`global_check=None` it is never called. No defaulted number to defend.

**Why `verify`-rejects raises rather than refuses.** Every `LayerFail` kind reads as a fact
about the tree — its docstring frames all four that way. `verify` rejecting the SAT model means
the CNF admitted something the project's verifier calls invalid, i.e. the encoder is wrong.
Typing that as a per-tree refusal would publish an encoder bug as a geometric finding.
`SatOrderError` therefore subclasses `Exception` and **none** of
`ValueError`/`RuntimeError`/`KeyError` — the three `compile_tree` catches around `assign(...)`
— exactly as `cores.CoreExtractionError` does, and for the same reason.

## 7. Interfaces

### `box_pleat/sat_order.py` (new)

```python
class SatOrderError(Exception): ...

@dataclass(frozen=True)
class SatVerdict: ...                      # §4

@dataclass(frozen=True)
class SatResult:
    sat: bool
    labels: dict | None                    # {(v_lo, v_hi): "M" | "V"}
    relation: dict | None                  # {(lo, hi): bool}, complete
    verdict: SatVerdict

def raw_triple_bound(cons) -> int
def encode(cons, slots, *, sink=None) -> tuple   # (pool, order_var, label_var, stats)
def solve(cons, slots, *, max_raw_triples=100_000_000,
          max_clauses=20_000_000, solver="cadical153") -> SatResult
```

`solve` never touches a fold. It returns a labelling and a relation; `compile.py` owns the
rewrite. That keeps the encoder testable against synthetic `_Constraints` with no geometry.

### `compile_tree` (modified signature)

```python
def compile_tree(..., clause_prop_verify: bool = False,
                 sat_layers: bool = False) -> Result:
```

One keyword-only parameter defaulting to `False`. With it off, every existing path is
byte-identical.

It applies on the sparse path too — not because sparse needs it (sparse already reaches
`emit`) but because sparse is the cheap positive control the tests use (§8).

## 8. Testing

### 8.1 The load-bearing test: exhaustive equivalence on a small instance

Build a synthetic `_Constraints` with about 8 pair variables, then **enumerate all 2⁸
assignments**, ask `layer_certify.verify` which it accepts, ask the solver which the CNF admits,
and require **the two sets to be equal** — not one-directional containment.

That pins the translation against the project's clause semantics in both directions, with no
geometry and no heuristic. Every per-family spot check is a weaker corollary of it, and the
per-family tests (one `cons` each for equality, transitivity, taco, and a label biconditional
at `sign = +1` and `sign ≠ 1`, each checked by enumeration) exist to **localise** a failure,
not to establish correctness.

### 8.2 Both guard stages, each firing for its own reason

A `cons` whose raw bound exceeds `max_raw_triples` → `OVERSIZE` **with no allocation**; and one
that slips the loose bound but crosses `max_clauses` mid-emission → `OVERSIZE` from the
streaming counter. Neither test can pass by the other's mechanism.

### 8.3 Wiring, `slow`-marked

`make test` is the PR gate and runs `-m "not slow"` (`Makefile:53`); `@pytest.mark.slow` is
registered at `mcp_harness/conftest.py:33`.

| test | assertion |
|---|---|
| sparse `lizard`, `sat_layers=True` | reaches `emit`, CERTIFIED, `cp_audit` 0 Maekawa / 0 Kawasaki over tolerance / arrangement clean — **the positive control** |
| sparse `lizard`, `sat_layers=False` | fold **byte-identical** to the shipped path |
| dense `lizard`, `sat_layers=True` | reaches `emit`, CERTIFIED, `cp_audit` clean |
| synthetic UNSAT `cons` | `LayerFail("unsatisfiable")`, and **not** `"no_labelling"` or `"budget"` |
| monkeypatched `verify` that rejects | **`SatOrderError`** raised, no `LayerFail` |

### 8.4 Properties gate; identity is reported

Everywhere else in this codebase the gate is **identity** — byte-identical folds, equal node
counts, matching digests. That cannot be the gate here: **any satisfying model is a valid
answer**, so the stage has no single correct output.

The CNF is deterministic (`sorted(cons.pairs)`, `cons.covers` is a tuple,
`combinations(sorted(cover), 3)`), so Cadical will very likely return the same witness run to
run — but requiring that would assert a solver implementation detail as a correctness property,
and a solver upgrade would read as a regression.

So the tests assert **properties** (CERTIFIED, `cp_audit` clean) and additionally **record a
hash of the witness labelling** so drift is visible without being a failure.

### 8.5 Pre-registered mutations, each required to fail §8.1

This session found four vacuous assertions, and the pattern every time was a check that could
not distinguish right from wrong behaviour.

* drop either of the two equality clauses
* flip either of transitivity's two forbidden states
* invert the taco parity (forbid even instead of odd)
* drop either direction of the label biconditional
* ignore `sign` on a `DirectSlot`

## 9. Limits

**The F set is fixed** by `assign`'s first candidate, so the stage decides *"is there an M/V
labelling for this F set"*, not *"for any F set"*. Iterating F sets is a different and much
larger project. §15.4 — the witness was always inside `assign`'s search space — is what makes
the fixed-F question the right one to ask first.

**Oversize instances are undecidable by this stage**, by construction (§5).

**`AREA_EPS` was measured inert on dense `lizard` only** (§16): 0 drops at every threshold from
1e-9 down to 0, smallest cell clearing the threshold by 108,131×. The prior six-subject study
at `layer_order.py:35-62` found subjects whose minimum cell areas genuinely straddle
(1.02e-09–1.75e-09), so that closure does **not** generalise. On a straddling subject this
stage inherits `layer_certify`'s "certified against the constraint set that survived AREA_EPS"
caveat in full.

**`python-sat==1.9.dev15` becomes a hard dependency of the dense path** whenever the flag is
on. Already pinned in `requirements.txt`, with the reason inline.

**One subject.** Every figure in §3.3, §5 and §2 is dense `lizard`'s.

## 10. Out of scope

* **Flipping the default.** `sat_layers` ships `False`, like `core_extraction`,
  `vertex_index` and `clause_prop` before it. Flipping it needs its own evidence run across
  subjects and its own decision.
* **Iterating over F sets** (§9).
* **Extracting an UNSAT core** to explain a refusal. MARCO is the prior art (§0) and this is a
  follow-on only if the `"unsatisfiable"` path ever fires; it never has.
* **Removing `assign`.** It is still the only source of the geometry (§3.2).
* **Any serve-path change.** `grep -c box_pleat mcp_harness/server.py` stays **0**.
* **Touching `layer_order.py`, `layer_certify.py`, `cores.py` or `layers.py`** (§0).

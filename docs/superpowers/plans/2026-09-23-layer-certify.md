# Layer-order certification (`layer_certify`) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace box-pleat's `consistent` / `contradiction` layer-order reading with a three-valued verdict — CERTIFIED / REFUTED / UNDECIDED — by checking Akitaya-Demaine-Ku's constraint families as clauses against a complete layer order, and searching for one where propagation leaves variables undecided.

**Architecture:** A new module `mcp_harness/layer_certify.py` consumes the `_Constraints` that `layer_order.constraints_for` already builds and never edits `layer_order.py`. Four stages: `clauses` materialises ADK's families as checks rather than writes; `verify` evaluates them against a complete relation in polynomial time; `collapse` quotients the undecided variables by the equality constraints' parity; `decide` branches on the quotient, reusing `layer_order.propagate` as its propagation step. `box_pleat/compile.py` calls it **once** on the candidate the CEGAR loop accepts, never per candidate.

**Tech Stack:** Python 3, stdlib only (`dataclasses`, `itertools`). No new dependencies — the search deliberately reuses `layer_order.propagate` instead of adding a SAT solver. `pytest` for tests.

## Global Constraints

Copied verbatim from `docs/superpowers/specs/2026-09-23-layer-certify-design.md`:

- **`mcp_harness/layer_order.py` is NOT edited by this work.** `git diff` for that path must be empty at every commit. Four shipped callers read it (`mv_symmetrize.py:594`, `mv_repair.py:857`, `root_rank.py:534`, `server.py:2736`) and every serve-path reading on record was taken with the propagation-only rule.
- **No serve-path test changes and no scorecard re-measurement.**
- `CERTIFY_BUDGET = 50_000` nodes, a module constant, basis measured 2026-09-23: `starfish` propagate 2.31 ms/call, so ~115 s worst case.
- `CERTIFIED` requires `skipped == 0` — a partial check may never certify.
- `CERTIFIED` does **not** mean flat-foldable. `AREA_EPS` drops sliver cells before `cons.pairs` is built, removing constraints and never adding one, so it means "certified against the constraint set that survived `AREA_EPS`". This caveat goes in the module docstring, not only in the spec.
- `clauses` emits no clause any family in `cons` does not already generate. It changes direction, not coverage. A coverage gap found against ADK is **reported and deferred**, never fixed inline, because fixing it means editing `layer_order.py`.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- Run every command from the worktree root `<repo>`. Do NOT `cd` to the original repository root.
- Never use bare `git stash` / `git stash pop` in this worktree.

## Background an implementer needs

**The one data structure everything reads.** `layer_order.constraints_for(ff)` returns `(cons, cons.slots)` where `cons` is a frozen `_Constraints` with:

| field | contents |
|---|---|
| `pairs` | `frozenset` of canonical overlapping face pairs `(lo, hi)`, `lo < hi` |
| `direct` | `tuple` of `(lit, value, Prov)` — the M/V crease seeds |
| `equalities` | `tuple` of `(litA, litB, Prov)` — `value(litA) == value(litB)` |
| `tacos` | `tuple` of `((p, q), (r, s), Prov)` |
| `covers` | `tuple` of `frozenset` per arrangement cell — the faces stacked over it |
| `slots` | `tuple` of `DirectSlot(edge, lit, sign, faces)` |

**Literals and their sign convention.** `layer_order._lit(x, f)` returns `((x, f), False)` when `x < f`, else `((f, x), True)`. A literal's value is `rel[pair] != flip`. And `rel[(lo, hi)] is True` means **`lo` is above `hi`** (read off `LayerOrder.above`, `layer_order.py:815`).

**Propagation.** `layer_order.propagate(cons, *, deps=False) -> dict` returns `{(lo, hi): bool}` for FORCED pairs only, or raises `layer_order.LayerContradiction` (a `ValueError`). It is not incremental: each call re-derives from scratch. To add a decision, build a new `cons` with `dataclasses.replace(cons, direct=cons.direct + (entry,))`.

**Why this work exists.** Propagation writes a pair only when currently unknown, so it derives forced relations and never decides satisfiability. Measured 2026-09-23 over the 8 emitting subjects (`docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/`):

| subject | unforced pairs | classes after `collapse` |
|---|---|---|
| horse, octopus, frog, guinea_pig, dog | 0 | — |
| bird, lizard | 8 | 2 |
| starfish | 252 (one component) | 114 |

So `verify` alone settles five subjects, and the search only ever runs on the three smallest.

---

### Task 1: `clauses` — ADK's families as checks, and the taco-taco equivalence proof

**Files:**
- Create: `mcp_harness/layer_certify.py`
- Test: `mcp_harness/tests/test_layer_certify.py`

**Interfaces:**
- Consumes: `layer_order.constraints_for`, `layer_order._lit`; and the three hand-derived fixtures already in `mcp_harness/tests/test_layer_order.py` — `strip_fold(a1, a2)` (1x3 strip), `strip_split_fold(a1, a2, flat="F")` (1x3 strip with an unfolded edge inside the middle face), `strip4_fold(a1, a2, a3)` (1x4 strip).
- Produces:
  - `Clause` frozen dataclass: `family: str`, `variables: tuple`, `flips: tuple`, `prov: str`.
  - `clauses(cons) -> tuple[Clause, ...]`.
  - `_value(rel, pair, flip) -> bool` — `rel[pair] != flip`.
  - Family names, exactly these strings: `"equality"`, `"transitivity"`, `"taco"`.

**Which fixture exercises which family — measured 2026-09-23, do not guess.** A test that reads `len(clauses) == len(cons.family)` passes vacuously when the fixture generates none of that family, and this project has been burned by exactly that ("a one-sub-family gap metric read 0 while two families were dropped — never accept 'no gap' from a partial metric"). So every count assertion below is paired with a non-vacuity assertion, and the fixtures are chosen from this table:

| fixture | pairs | covers | equalities | tacos | forced | free |
|---|---|---|---|---|---|---|
| `strip_fold("V", "V")` | 3 | 1 | 0 | 0 | 2 | 1 |
| `strip_fold("V", "M")` | 3 | 1 | 0 | 0 | 3 | **0** |
| `strip_split_fold("V", "V")` | 5 | 2 | **2** | 0 | 4 | 1 |
| `strip4_fold("V", "V", "V")` | 6 | 1 | 0 | **2** | 3 | 3 |
| `strip4_fold("V", "M", "V")` | 6 | 1 | 0 | **2** | 6 | **0** |

`strip4_fold("V", "M", "V")` is the important one: propagation alone gives a **complete** relation over all 6 pairs *and* the fixture carries real taco constraints, so it is the hand-sized analogue of the five corpus subjects that leave zero free variables.

**Derivation an implementer must not re-derive by guessing.** Our taco predicate and ADK's are provably the same constraint, and the test below pins the index mapping where a real bug could hide:

- ADK taco-taco `(i,j,k,l)` is `Λik + Λjk + Λil + Λjl ≡ 0 (mod 4)`. With each `Λ ∈ {+1,-1}`, a sum of four is `≡ 0 (mod 4)` exactly when it is `-4`, `0` or `+4`, i.e. when an **even number are `+1`** — a parity (XOR) constraint on the four.
- Ours, from `layer_order._propagate` (`layer_order.py:774`), is `(v0 != v1) == (v2 != v3)` over `(_lit(r,p), _lit(r,q), _lit(s,p), _lit(s,q))`, which is `(a XOR b) == (c XOR d)`, i.e. `a XOR b XOR c XOR d == 0`. **The same parity constraint.**
- The index mapping is `i=p, j=q, k=r, l=s`. Our four literals are the negations of ADK's four `Λ` (we take `_lit(r,p)` where ADK takes `Λik = Λ(p,r)`), and negating all four leaves the parity unchanged — which is why the two forms agree despite looking different.

**Transitivity as a check.** ADK: `Λij, Λjk, Λki` not all equal, i.e. no directed 3-cycle. `rel[(lo, hi)] is True` means **`lo` above `hi`** (`layer_order.LayerOrder.above`, `layer_order.py:815`). Over a sorted triple `(a, b, c)` with `rab = rel[(a,b)]`, `rbc = rel[(b,c)]`, `rac = rel[(a,c)]`, the two cyclic states are `(T, T, F)` (a>b, b>c, c>a) and `(F, F, T)`. So the clause is **violated iff `rab == rbc and rac != rab`**. Triples come from each `cons.covers` entry, because transitivity only holds where all three faces stack over one cell (`layer_order._covers_of`, `layer_order.py:652`).

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_layer_certify.py`:

```python
"""Tests for layer_certify.py.

Spec: docs/superpowers/specs/2026-09-23-layer-certify-design.md

Fixtures are the hand-derived strips already in test_layer_order.py rather
than new ones, and each test asserts NON-VACUITY before asserting a count:
`strip_fold` generates no equalities and no tacos, so a bare
`len(clauses) == len(cons.tacos)` would read 0 == 0 and prove nothing.
"""
import dataclasses
from itertools import combinations, product

import pytest

import layer_certify
import layer_order
from flat_fold import flat_fold
from layer_order import Prov, _lit, constraints_for
from test_layer_order import strip4_fold, strip_fold, strip_split_fold


def cons_for(fold):
    cons, _ = constraints_for(flat_fold(fold))
    return cons


def test_our_taco_predicate_equals_adks_mod_4_form_on_all_16_assignments():
    """ADK state taco-taco as `Lik + Ljk + Lil + Ljl = 0 mod 4`; we check
    `(v0 != v1) == (v2 != v3)` over (_lit(r,p), _lit(r,q), _lit(s,p),
    _lit(s,q)). Both are the parity of the four, but the INDEX MAPPING is
    where a real bug hides, so pin it: i=p, j=q, k=r, l=s, and our four
    literals are the negations of ADK's four Lambdas.
    """
    for bits in product((True, False), repeat=4):
        L_ik, L_jk, L_il, L_jl = bits     # ADK's, True = +1
        adk_ok = (sum(1 for b in bits if b) % 2) == 0
        v0, v1, v2, v3 = (not L_ik), (not L_jk), (not L_il), (not L_jl)
        ours_ok = (v0 != v1) == (v2 != v3)
        assert ours_ok == adk_ok, (bits, ours_ok, adk_ok)


def test_taco_clauses_match_the_propagators_four_literals():
    """One clause per `cons.tacos` entry, over exactly the four literals
    `layer_order._propagate` uses."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    assert len(cons.tacos) == 2, "fixture must carry real tacos"
    tacos = [c for c in layer_certify.clauses(cons) if c.family == "taco"]
    assert len(tacos) == len(cons.tacos)
    for clause, ((p, q), (r, s), _) in zip(tacos, cons.tacos):
        want = (_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))
        assert clause.variables == tuple(li[0] for li in want)
        assert clause.flips == tuple(li[1] for li in want)


def test_equality_clauses_are_one_per_constraint_with_their_flips():
    cons = cons_for(strip_split_fold("V", "V"))
    assert len(cons.equalities) == 2, "fixture must carry real equalities"
    eqs = [c for c in layer_certify.clauses(cons) if c.family == "equality"]
    assert len(eqs) == len(cons.equalities)
    for clause, (la, lb, _) in zip(eqs, cons.equalities):
        assert clause.variables == (la[0], lb[0])
        assert clause.flips == (la[1], lb[1])


def test_transitivity_clauses_come_only_from_within_one_cover():
    """Transitivity holds only where all three faces stack over one cell."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    allowed = {tri for cover in cons.covers
               for tri in combinations(sorted(cover), 3)}
    assert allowed, "fixture must have a cover of at least 3 faces"
    tris = [c for c in layer_certify.clauses(cons)
            if c.family == "transitivity"]
    assert len(tris) == len(allowed)
    for c in tris:
        faces = tuple(sorted({f for pr in c.variables for f in pr}))
        assert faces in allowed, faces


def test_transitivity_variables_are_the_three_pairs_of_the_triple():
    cons = cons_for(strip4_fold("V", "V", "V"))
    tris = [c for c in layer_certify.clauses(cons)
            if c.family == "transitivity"]
    assert tris, "no transitivity clauses -- the loop below would prove nothing"
    for c in tris:
        (a, b), (b2, cc), (a2, c2) = c.variables
        assert (a, b, cc) == (a2, b2, c2)
        assert c.flips == (False, False, False)


def test_clauses_emits_no_family_beyond_the_three():
    cons = cons_for(strip4_fold("V", "V", "V"))
    assert {c.family for c in layer_certify.clauses(cons)} <= {
        "equality", "transitivity", "taco"}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v
```

Expected: FAIL — a single **collection error** for the whole file: `ERROR tests/test_layer_certify.py - ModuleNotFoundError: No module named 'layer_certify'`. Not six individual failures: `import layer_certify` is at module scope, so pytest cannot collect or execute any test in the file until the module exists.

Record that as the RED evidence, exactly as observed. Do **not** claim that `test_our_taco_predicate_equals_adks_mod_4_form_on_all_16_assignments` passed at RED — it cannot, and an earlier draft of this plan said it would, which was wrong about Python semantics. What is true, and worth stating instead, is that this test references no `layer_certify` symbol at all: the taco/ADK equivalence is a claim about the spec, provable from the two formulas alone. That independence is verifiable by inspection of the test body, not by a RED-stage pass.

- [ ] **Step 3: Write `clauses`**

Create `mcp_harness/layer_certify.py`:

```python
"""Is there a COMPLETE layer order for this folded state, and does it
satisfy every constraint?

`layer_order` derives FORCED relations only. Its own docstring says it
"does NOT decide whether a total order exists, so 'no contradiction' is
weaker than ADK's satisfiability result." This module closes that gap for
the box-pleat compiler, by checking Akitaya-Demaine-Ku's families as
CLAUSES against a complete relation (`verify`) and searching for one where
propagation leaves variables undecided (`decide`).

Akitaya, Demaine & Ku, "Computing Flat-Folded States" (OSME 2024) prove a
facewise layer order is verified in O(min{n^2 p, n^2 + m p^2}) = O(n^3) --
verifying is in P, finding one is in NP. Their O(n^3 + sum t_i^3 2^t_i)
algorithm enumerates ALL folded states; we need ONE, which is why `decide`
branches instead of enumerating.

⚠ CERTIFIED IS NOT FLAT-FOLDABLE. `layer_order.AREA_EPS` drops sliver
arrangement cells before `cons.pairs` is built, and a dropped cell REMOVES
constraints and can never add one. So CERTIFIED means "certified against
the constraint set that survived AREA_EPS", which is strictly weaker than
a proof. Closing that is separate work.

⚠ THIS MODULE DOES NOT EDIT `layer_order.py`, BY DESIGN. Four shipped
callers read that module -- `mv_symmetrize._LayerGate`, `mv_repair`,
`root_rank` and `server.py`'s serve gate -- and every serve-path reading on
record, including quadruped's contradiction -> consistent from the root
wave, was taken with the propagation-only rule. Adopting this verdict there
needs its own spec and scorecard run (design doc section 2).
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from itertools import combinations

import layer_order
from layer_order import Prov, _lit

#: Search nodes `decide` may spend before returning UNDECIDED. Basis,
#: measured 2026-09-23: `starfish` is the only corpus subject on which this
#: can bind (the other seven leave 0 or 2 free variables) and one
#: `layer_order.propagate` there costs 2.31 ms, so this bounds the worst
#: case at roughly 115 s -- below costs this corpus already carries
#: (guinea_pig 295 s, dog 578 s). A search needing more than this on 114
#: variables will not finish at 500,000 either, so it is a give-up
#: threshold, not a tuning knob -- the role `layer_budget` plays in the
#: CEGAR loop.
CERTIFY_BUDGET = 50_000


@dataclass(frozen=True)
class Clause:
    """One ADK constraint, as a CHECK over canonical pair-variables.

    `variables[i]` is a canonical `(lo, hi)` face pair and `flips[i]` the
    matching flip bit from `layer_order._lit`, so the literal's value is
    `rel[variables[i]] != flips[i]`. `family` selects the predicate in
    `_satisfied`."""
    family: str          # equality | transitivity | taco
    variables: tuple
    flips: tuple
    prov: str


def _value(rel: dict, pair, flip: bool) -> bool:
    """A literal's value: `layer_order`'s own rule, one copy."""
    return rel[pair] != flip


def clauses(cons) -> tuple:
    """ADK's families from `cons`, as checks rather than writes.

    Emits NOTHING `cons` does not already carry -- this changes direction,
    not coverage (design doc section 4.1). Antisymmetry is absent on
    purpose: `_lit` gives one canonical variable per unordered pair, so
    "Lij = -Lji" is unrepresentable-as-violated rather than checked.

    A triple can be witnessed by more than one cover; its constraint is the
    same constraint either way, so triples are de-duplicated."""
    out = []
    for la, lb, prov in cons.equalities:
        out.append(Clause("equality", (la[0], lb[0]), (la[1], lb[1]),
                          str(prov)))
    seen = set()
    for cover in cons.covers:
        for a, b, c in combinations(sorted(cover), 3):
            if (a, b, c) in seen:
                continue
            seen.add((a, b, c))
            out.append(Clause("transitivity", ((a, b), (b, c), (a, c)),
                              (False, False, False),
                              f"transitivity {a},{b},{c}"))
    for (p, q), (r, s), prov in cons.tacos:
        lits = (_lit(r, p), _lit(r, q), _lit(s, p), _lit(s, q))
        out.append(Clause("taco", tuple(li[0] for li in lits),
                          tuple(li[1] for li in lits), str(prov)))
    return tuple(out)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/layer_certify.py mcp_harness/tests/test_layer_certify.py
git commit -m "$(cat <<'MSG'
layer_certify: ADK constraint families as clauses

`clauses(cons)` re-expresses equality, transitivity and taco constraints
as CHECKS over canonical pair-variables, emitting nothing cons does not
already carry -- direction, not coverage.

The taco family is the one whose FORM differs from ADK's paper, so its
equivalence is proved by test over all 16 assignments rather than
assumed: their `Lik + Ljk + Lil + Ljl = 0 mod 4` is the parity of the
four, and our `(v0 != v1) == (v2 != v3)` is the same parity. The test
pins the index mapping (i=p, j=q, k=r, l=s, all four negated), which is
where a real bug could hide.

Fixtures are test_layer_order.py's hand-derived strips, chosen per family
from a measured table, and every count assertion is paired with a
non-vacuity assertion: strip_fold carries no equalities and no tacos, so
a bare count test would read 0 == 0 and prove nothing.

Antisymmetry emits no clause on purpose: `_lit` makes it
unrepresentable-as-violated.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 2: `verify` — the polynomial certificate

**Files:**
- Modify: `mcp_harness/layer_certify.py`
- Test: `mcp_harness/tests/test_layer_certify.py`

**Interfaces:**
- Consumes: `Clause`, `clauses`, `_value` from Task 1.
- Produces:
  - `Violation` frozen dataclass: `family: str`, `variables: tuple`, `values: tuple`, `prov: str`.
  - `VerifyResult` frozen dataclass: `violation: Violation | None`, `checked: int`, `skipped: int`.
  - `verify(cons, rel) -> VerifyResult`.
  - `_satisfied(family, vals) -> bool`.

**The fixture to use, and why.** `strip4_fold("V", "M", "V")` leaves **zero** free variables — `layer_order.propagate` alone returns a complete relation over all 6 pairs — *and* carries 2 real taco constraints. So it needs no synthetic completion helper and it exercises every family `verify` can check. It is the hand-sized analogue of `horse`, `octopus`, `frog`, `guinea_pig` and `dog`.

`clauses` emits equalities first, then transitivity, then tacos, and `verify` returns the **first** violation it finds. `strip4_fold` generates no equalities, so a corrupted transitivity clause is the first thing checked and the family assertion below is deterministic rather than incidental.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_layer_certify.py`:

```python
def test_verify_accepts_the_complete_relation_propagation_already_forces():
    """strip4 V,M,V forces all 6 pairs, so this is the hand-sized analogue
    of the five corpus subjects that leave zero free variables."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = layer_order.propagate(cons)
    assert set(rel) == set(cons.pairs), "fixture must be fully forced"
    out = layer_certify.verify(cons, rel)
    assert out.violation is None
    assert out.skipped == 0
    assert out.checked > 0


def test_verify_rejects_a_relation_with_a_directed_3_cycle():
    """rel[(lo,hi)] True means lo above hi, so a>b, b>c, c>a is
    rab=True, rbc=True, rac=False. Transitivity must fire."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    tri = next(c for c in layer_certify.clauses(cons)
               if c.family == "transitivity")
    ab, bc, ac = tri.variables
    rel[ab], rel[bc], rel[ac] = True, True, False
    out = layer_certify.verify(cons, rel)
    assert out.violation is not None
    assert out.violation.family == "transitivity"
    assert out.violation.variables == tri.variables


def test_verify_rejects_a_broken_taco():
    """Corrupt only the taco parity, leaving transitivity satisfied, so the
    taco predicate is what fires."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    taco = next(c for c in layer_certify.clauses(cons) if c.family == "taco")
    vals = [layer_certify._value(rel, pr, fl)
            for pr, fl in zip(taco.variables, taco.flips)]
    assert (vals[0] != vals[1]) == (vals[2] != vals[3]), "start satisfied"
    pr, fl = taco.variables[0], taco.flips[0]
    rel[pr] = not rel[pr]        # flip one literal -> parity breaks
    out = layer_certify.verify(cons, rel)
    assert out.violation is not None
    assert out.violation.family in ("transitivity", "taco")


def test_verify_counts_skipped_clauses_and_never_hides_a_partial_check():
    """A CERTIFIED verdict requires skipped == 0, so a partial relation
    must read as partial rather than passing quietly."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    rel = dict(layer_order.propagate(cons))
    del rel[next(iter(rel))]
    out = layer_certify.verify(cons, rel)
    assert out.skipped > 0


def test_satisfied_raises_on_an_unknown_family():
    with pytest.raises(ValueError, match="unknown family"):
        layer_certify._satisfied("tortilla_surprise", (True, True))
```

`test_verify_rejects_a_broken_taco` accepts either family in its final assertion on purpose: flipping one literal of a taco also perturbs the transitivity clauses over the same faces, and which clause `verify` reaches first is an ordering detail, not a behaviour worth pinning. What matters is that the corruption is caught.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -k "verify or satisfied"
```

Expected: FAIL with `AttributeError: module 'layer_certify' has no attribute 'verify'`.

- [ ] **Step 3: Implement `verify`**

Append to `mcp_harness/layer_certify.py`:

```python
@dataclass(frozen=True)
class Violation:
    """A clause a complete relation does not satisfy.

    On a relation `layer_order.propagate` accepted, this is a FINDING:
    propagation was wrong on that input. Per the standing ruling, the
    caller refuses rather than emitting."""
    family: str
    variables: tuple
    values: tuple
    prov: str


@dataclass(frozen=True)
class VerifyResult:
    violation: Violation | None
    checked: int         # clauses fully evaluated
    skipped: int         # clauses an undecided variable made unevaluable


def _satisfied(family: str, vals: tuple) -> bool:
    """`rel[(lo, hi)] is True` means `lo` above `hi`, so the two cyclic
    states of a sorted triple are (T, T, F) and (F, F, T)."""
    if family == "equality":
        return vals[0] == vals[1]
    if family == "transitivity":
        rab, rbc, rac = vals
        return not (rab == rbc and rac != rab)
    if family == "taco":
        return (vals[0] != vals[1]) == (vals[2] != vals[3])
    raise ValueError(
        f"layer_certify._satisfied: unknown family {family!r} -- add its "
        f"predicate rather than let it fall through to a default, which "
        f"would silently certify a family nobody checks")


def verify(cons, rel: dict) -> VerifyResult:
    """Every clause from `clauses(cons)`, checked against `rel`.

    A clause naming a pair `rel` does not decide cannot be evaluated; it is
    SKIPPED and counted, and `skipped` is returned beside the violation so
    no caller can mistake a partial check for a complete one. A CERTIFIED
    verdict requires `skipped == 0`. Polynomial, no search -- ADK prove this
    direction is O(n^3) and in P."""
    checked = skipped = 0
    for c in clauses(cons):
        if any(pr not in rel for pr in c.variables):
            skipped += 1
            continue
        vals = tuple(_value(rel, pr, fl)
                     for pr, fl in zip(c.variables, c.flips))
        checked += 1
        if not _satisfied(c.family, vals):
            return VerifyResult(
                Violation(c.family, c.variables, vals, c.prov),
                checked, skipped)
    return VerifyResult(None, checked, skipped)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/layer_certify.py mcp_harness/tests/test_layer_certify.py
git commit -m "$(cat <<'MSG'
layer_certify: verify() -- the polynomial certificate

Evaluates every clause against a complete relation. ADK prove this
direction is O(n^3) and in P, which is why the cheap half of their result
is worth having separately from the search.

`skipped` is returned beside the violation and a CERTIFIED verdict
requires it to be zero: a partial relation must read as partial, never
pass quietly. `_satisfied` raises on an unknown family rather than
defaulting, so a family added later cannot be silently unchecked.

Tested on strip4 V,M,V, which propagation already forces completely --
the hand-sized analogue of the five corpus subjects with zero free
variables -- and which carries real tacos, so no family goes unexercised.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 3: `collapse` — parity quotient and odd-cycle refutation

**Files:**
- Modify: `mcp_harness/layer_certify.py`
- Test: `mcp_harness/tests/test_layer_certify.py`

**Interfaces:**
- Consumes: `Violation` from Task 2.
- Produces: `collapse(cons, free) -> (dict, Violation | None)` — a map from each free pair to its class representative, and an odd-cycle `Violation` or `None`.

**Why parity.** `cons.equalities` asserts `value(la) == value(lb)` where `value((pair, flip)) = rel[pair] != flip`. Substituting, `rel[pa] == rel[pb]` XOR `(flip_a != flip_b)`. So each equality is an edge carrying parity `flip_a XOR flip_b`, and union-find with parity quotients the search space. Measured 2026-09-23: `starfish` 252 free pairs → **114** classes, `bird` and `lizard` 8 → **2**, odd cycles **0** on all three.

**Why these tests are synthetic.** No hand-sized fixture has two *free* pairs joined by an equality: `strip_split_fold` has 2 equalities but only 1 free pair, so a test looping `if {la[0], lb[0]} <= free` would never enter its body — vacuous again. `collapse` is therefore unit-tested on a doctored `_Constraints` built with `dataclasses.replace`, which is existing practice in `tests/test_layer_order.py` (its synthetic-taco test does the same). Real-geometry collapse is covered by Task 4's `bird`/`lizard` test asserting `free == 2` against 8 unforced pairs.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_layer_certify.py`:

```python
def _doctored(cons, pairs, equalities, covers=()):
    """`cons` with a synthetic variable set, for unit-testing `collapse`
    and `decide` on shapes no hand-sized fold produces. Matches
    test_layer_order.py's own synthetic-taco practice."""
    return dataclasses.replace(cons, pairs=frozenset(pairs),
                               equalities=tuple(equalities),
                               direct=(), tacos=(), covers=tuple(covers))


def test_collapse_quotients_free_pairs_joined_by_an_equality():
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is None
    assert set(classes) == {a, b, c}
    assert classes[a] == classes[b]
    assert classes[c] != classes[a]
    assert len(set(classes.values())) == 2


def test_collapse_respects_the_flip_parity():
    """An equality between literals with DIFFERENT flips means the two
    pairs take OPPOSITE rel values -- still one class, and the parity is
    what makes a later odd cycle detectable."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, True), Prov("a!=b", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is None
    assert classes[a] == classes[b]


def test_collapse_reports_an_odd_parity_cycle():
    """a == b, b == c, a != c is unsatisfiable, and propagation does not
    find it. collapse must, without any search."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=())),
                      ((b, False), (c, False), Prov("b==c", faces=())),
                      ((a, False), (c, True), Prov("a!=c", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b, c})
    assert odd is not None
    assert odd.family == "equality"


def test_collapse_ignores_equalities_touching_a_forced_pair():
    """Only equalities whose BOTH variables are free can merge classes; one
    forced side means the value is already known and there is nothing to
    quotient."""
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (c, False), Prov("a==c", faces=()))])
    classes, odd = layer_certify.collapse(cons, {a, b})   # c is forced
    assert odd is None
    assert classes[a] != classes[b]
    assert set(classes) == {a, b}
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -k collapse
```

Expected: FAIL with `AttributeError: module 'layer_certify' has no attribute 'collapse'`.

- [ ] **Step 3: Implement `collapse`**

Append to `mcp_harness/layer_certify.py`:

```python
class _ParityDSU:
    """Union-find carrying a parity bit per element.

    `find` returns `(root, parity_to_root)`; `union(a, b, parity)` returns
    False when the edge contradicts the existing parity, i.e. an odd
    cycle."""

    def __init__(self):
        self._parent: dict = {}
        self._par: dict = {}

    def find(self, x):
        if x not in self._parent:
            self._parent[x], self._par[x] = x, False
            return x, False
        if self._parent[x] == x:
            return x, False
        root, up = self.find(self._parent[x])
        self._parent[x], self._par[x] = root, self._par[x] != up
        return root, self._par[x]

    def union(self, a, b, parity: bool) -> bool:
        ra, pa = self.find(a)
        rb, pb = self.find(b)
        if ra == rb:
            return (pa != pb) == parity
        self._parent[ra] = rb
        self._par[ra] = (pa != pb) != parity
        return True


def collapse(cons, free):
    """Quotient the free variables by the equality constraints' parity.

    Returns `(classes, odd_cycle)`. `classes` maps every element of `free`
    to its class representative; `decide` branches on representatives, so
    the search space is the quotient rather than `free` itself (measured
    2026-09-23: starfish 252 -> 114, bird and lizard 8 -> 2).

    `odd_cycle` is a `Violation` when the parity graph contains one, else
    None: an odd cycle is unsatisfiable, and propagation does not find it,
    so `decide` turns it straight into REFUTED with no search.

    Only equalities whose BOTH variables are in `free` can merge: one
    forced side means the value is already known, and there is nothing to
    quotient.

    This does NOT rewrite the CSP. `decide` seeds only a representative and
    lets `layer_order._propagate`'s existing equality rule fill the rest of
    the class, so there is one implementation of the equality semantics,
    not two."""
    dsu = _ParityDSU()
    for pr in free:
        dsu.find(pr)
    for la, lb, prov in cons.equalities:
        if la[0] in free and lb[0] in free:
            if not dsu.union(la[0], lb[0], la[1] != lb[1]):
                return ({pr: dsu.find(pr)[0] for pr in free},
                        Violation("equality", (la[0], lb[0]), (), str(prov)))
    return {pr: dsu.find(pr)[0] for pr in free}, None
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v
```

Expected: 15 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/layer_certify.py mcp_harness/tests/test_layer_certify.py
git commit -m "$(cat <<'MSG'
layer_certify: collapse() -- parity quotient and odd-cycle refutation

`cons.equalities` assert value(la) == value(lb) where value is
`rel[pair] != flip`, so each is a parity edge and union-find with parity
quotients the search space: starfish 252 free pairs -> 114 classes, bird
and lizard 8 -> 2 (measured 2026-09-23).

An odd cycle is unsatisfiable and propagation does not find it, so it
becomes REFUTED with no search. Measured 0 on the corpus, so this is a
guard rather than a repair.

Unit-tested on a doctored _Constraints, because no hand-sized fold has
two FREE pairs joined by an equality -- strip_split_fold has 2 equalities
but only 1 free pair, so a real-fixture test would loop zero times. Real
geometry is covered by bird/lizard asserting free == 2 over 8 unforced
pairs.

collapse does not rewrite the CSP: decide seeds one representative and
lets the existing equality rule fill the class.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 4: `decide` — branch and propagate, with the budget

**Files:**
- Modify: `mcp_harness/layer_certify.py`
- Test: `mcp_harness/tests/test_layer_certify.py`

**Interfaces:**
- Consumes: `verify`, `collapse`, `CERTIFY_BUDGET`, `Violation`.
- Produces:
  - `Verdict` frozen dataclass: `kind: str` (`"CERTIFIED"` / `"REFUTED"` / `"UNDECIDED"`), `violation: Violation | None`, `nodes: int`, `free: int`.
  - `decide(cons, *, budget=CERTIFY_BUDGET) -> Verdict`.

**Pre-validated by brute force, 2026-09-23, so a surprise is a bug and not a discovery.** Enumerating every completion of each fixture's free variables against the clause set gives:

| fixture | free | clauses | satisfying completions |
|---|---|---|---|
| `strip4_fold("V", "V", "V")` | 3 | 6 | **3 of 8** |
| `strip4_fold("V", "M", "V")` | 0 | 6 | 1 of 1 |
| `strip_fold("V", "V")` | 1 | 1 | 2 of 2 |
| `strip_split_fold("V", "V")` | 1 | 4 | 2 of 2 |

`strip4_fold("V", "V", "V")` certifies while 5 of its 8 completions are refuted, so the clauses are doing real work rather than accepting everything. And `strip_fold("V", "V")` accepting **both** completions reproduces, from the clause set alone, what `test_layer_order.py`'s own module docstring derived by hand: V+V "leaves the outer pair genuinely free (spiral vs tuck are both physically valid)". If `decide` disagrees with any row here, the defect is in `clauses` or `_satisfied`.

**`Verdict.free` counts CLASSES, not pairs.** It is the number of independent variables at the **root**, after `collapse` — so `bird` reads 2, not 8. Recording the pair count instead would make the field disagree with the design doc and with the `bird`/`lizard` assertion below.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_layer_certify.py`:

```python
def test_decide_certifies_a_physically_foldable_strip_with_free_variables():
    """The all-V 1x4 accordion folds in the real world, and propagation
    leaves 3 of its 6 pairs free. So `decide` must CERTIFY it.

    If this REFUTES, STOP and report it rather than adjusting the test:
    a refutation of a pattern that physically folds means `clauses` or
    `_satisfied` is wrong, which is exactly what this task is for."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    rel = layer_order.propagate(cons)
    assert len(set(cons.pairs) - set(rel)) == 3, "fixture must leave 3 free"
    v = layer_certify.decide(cons)
    assert v.kind == "CERTIFIED"
    assert v.violation is None
    assert v.free == 3          # no equalities here, so classes == pairs
    assert v.nodes >= 1


def test_decide_certifies_a_fully_forced_relation_without_searching():
    """strip4 V,M,V leaves nothing free: one node, no branching."""
    cons = cons_for(strip4_fold("V", "M", "V"))
    v = layer_certify.decide(cons)
    assert v.kind == "CERTIFIED"
    assert v.free == 0
    assert v.nodes == 1


def test_decide_refutes_an_odd_cycle_without_searching():
    a, b, c = (0, 1), (1, 2), (0, 2)
    cons = _doctored(cons_for(strip_fold("V", "V")), {a, b, c},
                     [((a, False), (b, False), Prov("a==b", faces=())),
                      ((b, False), (c, False), Prov("b==c", faces=())),
                      ((a, False), (c, True), Prov("a!=c", faces=()))],
                     covers=(frozenset({0, 1, 2}),))
    v = layer_certify.decide(cons)
    assert v.kind == "REFUTED"
    assert v.nodes == 1
    # A REFUTED verdict must NAME what refuted it, or a caller cannot tell a
    # finding about the folded state from a finding about the oracle.
    assert v.violation is not None
    assert v.violation.family == "equality"


def test_decide_returns_undecided_when_the_budget_is_exhausted():
    """A budget of 1 node cannot get past the root of a search that has to
    branch, and the verdict must say UNDECIDED rather than guess."""
    cons = cons_for(strip4_fold("V", "V", "V"))
    v = layer_certify.decide(cons, budget=1)
    assert v.kind == "UNDECIDED"
    assert v.nodes >= 1


@pytest.mark.slow
@pytest.mark.parametrize("subject", ["bird", "lizard"])
def test_decide_settles_bird_and_lizard_within_four_assignments(subject):
    """Both leave 8 unforced pairs that the equality parity collapses to 2
    independent variables, so 4 assignments bound the search. This is also
    the only test that exercises `collapse` on real geometry."""
    cons = _subject_constraints(subject)
    rel = layer_order.propagate(cons)
    assert len(set(cons.pairs) - set(rel)) == 8, "census said 8 unforced"
    v = layer_certify.decide(cons)
    assert v.kind in ("CERTIFIED", "REFUTED")
    assert v.free == 2, "equality parity must collapse 8 pairs to 2 classes"
    assert v.nodes <= 8


def _subject_constraints(subject):
    import json
    from box_pleat.compile import compile_tree
    path = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
            "/data/rule6_serve.json")
    entry = {e["subject"]: e for e in json.load(open(path))}[subject]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit", res.stage_reached
    cons, _ = constraints_for(flat_fold(res.fold))
    return cons
```

- [ ] **Step 2: Run the fast tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -k decide -m "not slow"
```

Expected: FAIL with `AttributeError: module 'layer_certify' has no attribute 'decide'`.

- [ ] **Step 3: Implement `decide`**

Append to `mcp_harness/layer_certify.py`:

```python
@dataclass(frozen=True)
class Verdict:
    """CERTIFIED: a complete layer order exists and satisfies every clause
    `clauses` generates -- which is NOT the same as flat-foldable, see this
    module's docstring on AREA_EPS.

    REFUTED: no complete order exists. From `verify` on a relation
    propagation accepted, this is a finding about propagation, and
    `violation` names the clause.

    UNDECIDED: the budget ran out. This says nothing about the folded
    state, only about this search's cost -- the same distinction
    `box_pleat.compile.LayerFail` already draws between "no_labelling" and
    "budget".

    `free` is the number of independent variables at the ROOT, after the
    equality quotient -- CLASSES, not unforced pairs. `bird` reads 2, not
    the 8 pairs the census counts."""
    kind: str
    violation: Violation | None
    nodes: int
    free: int


class _Exhausted(Exception):
    """Internal: the node budget ran out mid-search."""


def decide(cons, *, budget: int = CERTIFY_BUDGET) -> Verdict:
    """Does a complete, valid facewise layer order exist for `cons`?

    Branch and propagate. `layer_order.propagate` is reused as the
    propagation step rather than reimplemented, so the two can never
    disagree about what a constraint means. Every completed relation is
    run through `verify` before it may certify: propagation is the thing
    being audited, so the search must never certify on its word alone.

    ADK's O(n^3 + sum t_i^3 2^t_i) algorithm enumerates ALL folded states.
    This wants ONE, so it branches and stops at the first success -- which
    is why starfish's single 114-variable component is reachable at all.
    The corpus aligns favourably: the subjects needing a search are the
    ones where a single propagate is cheapest (starfish 38 faces at
    2.31 ms, lizard 20), while the expensive ones (dog 298 faces, horse
    166) leave zero free variables and need none. That is a measured
    property of this corpus, not a theorem, which is why `budget` exists."""
    counter = [0]
    root_free = [0]

    def search(extra: tuple):
        counter[0] += 1
        if counter[0] > budget:
            raise _Exhausted
        root = not extra
        c = (cons if root
             else dataclasses.replace(cons, direct=cons.direct + extra))
        try:
            rel = layer_order.propagate(c)
        except layer_order.LayerContradiction:
            return None, None
        free = set(c.pairs) - set(rel)
        if not free:
            if root:
                root_free[0] = 0
            out = verify(c, rel)
            if out.violation is None and out.skipped == 0:
                return rel, None
            return None, out.violation
        classes, odd = collapse(c, free)
        if root:
            root_free[0] = len({classes[pr] for pr in free})
        if odd is not None:
            return None, odd
        pick = sorted({classes[pr] for pr in free})[0]
        last = None
        for val in (True, False):
            seed = ((pick, False), val,
                    Prov(f"certify decision {pick}={val}", faces=pick))
            got, vio = search(extra + (seed,))
            if got is not None:
                return got, None
            last = vio if vio is not None else last
        return None, last

    try:
        rel, vio = search(())
    except _Exhausted:
        return Verdict("UNDECIDED", None, counter[0], root_free[0])
    if rel is not None:
        return Verdict("CERTIFIED", None, counter[0], root_free[0])
    return Verdict("REFUTED", vio, counter[0], root_free[0])
```

- [ ] **Step 4: Run the fast tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -m "not slow"
```

Expected: 19 passed, 2 deselected.

If `test_decide_certifies_a_physically_foldable_strip_with_free_variables` REFUTES, do not adjust the test. The all-V 1x4 accordion folds physically, so a refutation means `clauses` over-generates or `_satisfied` has a predicate backwards. Report it.

- [ ] **Step 5: Run the slow tests (bird and lizard compile, ~15 s)**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -m slow
```

Expected: 2 passed, both reporting `free == 2` over 8 unforced pairs. If either reports a different count, STOP and report it — the census measured 8 pairs and 2 classes on 2026-09-23, so a change means either the compiler moved or `collapse` is wrong, and neither should be papered over by relaxing the assertion.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/layer_certify.py mcp_harness/tests/test_layer_certify.py
git commit -m "$(cat <<'MSG'
layer_certify: decide() -- branch and propagate, with a node budget

Reuses `layer_order.propagate` as the propagation step so the search and
the propagator can never disagree about what a constraint means, and runs
`verify` on every completed relation before certifying: propagation is
the thing being audited, so the search must not certify on its word.

ADK's algorithm enumerates ALL folded states at 2^t_i per component; this
wants one and stops at the first success, which is why starfish's single
114-variable component is reachable at all.

`Verdict.free` counts CLASSES after the equality quotient, not unforced
pairs -- bird reads 2, not 8.

Budget 50,000 nodes, basis measured: starfish is the only subject it can
bind and its propagate costs 2.31 ms, so ~115 s worst case. Exhaustion
returns UNDECIDED, which says nothing about the folded state -- the same
distinction LayerFail already draws between "no_labelling" and "budget".

The all-V 1x4 accordion folds in the real world and leaves 3 pairs free,
so it is the test that would catch an over-generated clause or a backwards
predicate.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 5: Wire it into the box-pleat compiler, once per compile

**Files:**
- Modify: `mcp_harness/box_pleat/layers.py`
- Modify: `mcp_harness/box_pleat/compile.py:39-96` (`_LAYER_KIND`, `LayerFail`, `Result`), `:99` (`compile_tree`'s signature), `:300-310` (after the assign stage)
- Test: `mcp_harness/tests/test_layer_certify.py`

**Interfaces:**
- Consumes: `layer_certify.decide`, `layer_certify.Verdict`, `layer_certify.CERTIFY_BUDGET`; existing `layers.LayerGraph`, `layers._seed`, `layers.propagate`.
- Produces:
  - `layers._seeded(graph, labels) -> _Constraints` — the `direct`-seeded constraints, factored out of `propagate` so `certify` shares it.
  - `layers.certify(graph, labels, *, budget=layer_certify.CERTIFY_BUDGET) -> layer_certify.Verdict`.
  - `compile.Result.verdict: layer_certify.Verdict | None`.
  - `compile.compile_tree(..., certify_budget=layer_certify.CERTIFY_BUDGET)`.
  - A fourth `LayerFail.kind`: `"uncertified"`.

**The two-tier rule, which this task must not break.** `layers.propagate` stays the per-candidate filter inside the CEGAR loop, unchanged. `certify` runs **once**, on the candidate `assign` accepted. Per-candidate `decide` was considered and rejected: each rejection already costs a fresh CSP re-descent, `rabbit` is unresolved at 500k nodes / ~29 min, and `dog` takes 578 s.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_layer_certify.py`:

```python
@pytest.mark.slow
def test_compile_tree_reports_a_verdict_and_leaves_the_fold_unchanged():
    """`lizard` emits today. After this feature it must still emit, with
    the SAME fold bytes, plus a Verdict on the Result."""
    import json
    from box_pleat.compile import compile_tree
    path = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
            "/data/rule6_serve.json")
    entry = {e["subject"]: e for e in json.load(open(path))}["lizard"]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit"
    assert res.verdict is not None
    assert res.verdict.kind == "CERTIFIED"
    # GEOMETRY only, deliberately: `lizard-v1.fold` is the PRE-reassignment
    # labelling (lizard took 13 flips), so `edges_assignment` differs by
    # design. The crease SET is what must not move -- that is the enabling
    # theorem this whole subproject rests on.
    golden = json.load(open("tests/data/lizard-v1.fold"))
    assert res.fold["vertices_coords"] == golden["vertices_coords"]
    assert res.fold["edges_vertices"] == golden["edges_vertices"]


def test_layers_certify_and_propagate_seed_the_same_constraints():
    """The two tiers must judge the SAME constraint set. Asserted through
    behaviour rather than through `inspect.getsource`: build a graph, seed
    it via `_seeded`, and check the `direct` tuple both tiers consume is
    identical to the one `propagate` builds for the same labels."""
    from box_pleat import layers
    cons = cons_for(strip4_fold("V", "M", "V"))
    graph = layers.LayerGraph(cons=cons, slots=cons.slots)
    labels = {s.edge: "V" for s in cons.slots}
    seeded = layers._seeded(graph, labels)
    assert len(seeded.direct) == len(cons.slots)
    assert seeded.pairs == cons.pairs
    # same labels, same seeds, every time -- no hidden state in either tier
    assert layers._seeded(graph, labels).direct == seeded.direct
```

- [ ] **Step 2: Run the test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -k "seed_the_same_constraints"
```

Expected: FAIL with `AttributeError: module 'box_pleat.layers' has no attribute 'certify'`.

- [ ] **Step 3: Factor the seeded builder and add `certify` in `box_pleat/layers.py`**

Replace the body of `propagate` (`mcp_harness/box_pleat/layers.py:123-141`) and add `certify` after it:

```python
def _seeded(graph: LayerGraph, labels: dict):
    """`graph.cons` with `direct` seeded from `labels`.

    The ONLY place the seeding happens: both `propagate` (the per-candidate
    filter) and `certify` (once, on the accepted candidate) go through it,
    so the two tiers cannot end up judging different constraint sets."""
    direct = tuple(
        (s.lit, _seed(s, labels[s.edge]),
         layer_order.Prov(f"crease {s.edge} {labels[s.edge]}",
                          creases=(s.edge,), faces=s.faces))
        for s in graph.slots)
    return dataclasses.replace(graph.cons, direct=direct)


def propagate(graph: LayerGraph, labels: dict) -> Witness | None:
    """None when no contradiction was FOUND for `labels` (not a proof that a
    consistent layer order exists -- see the under-refutation caveat in this
    module's docstring), else the witness.

    This is the CEGAR loop's per-candidate filter and stays deliberately
    cheap: ~300 ms on horse, and sound in the only direction the loop needs
    (a contradiction is a valid no-good clause). `certify` below is the
    expensive tier and runs once, on the candidate the loop accepts.

    `labels` maps every slot's edge key to "M" or "V"."""
    try:
        layer_order.propagate(_seeded(graph, labels), deps=True)
    except layer_order.LayerContradiction as exc:
        return Witness(kind=_kind_of(exc.prov.text),
                       creases=frozenset(exc.deps or ()),
                       faces=tuple(exc.prov.faces), prov=str(exc))
    return None


def certify(graph: LayerGraph, labels: dict, *,
            budget: int = layer_certify.CERTIFY_BUDGET):
    """Does a complete, valid layer order exist for `labels`?

    The answer `propagate` above cannot give. Runs ONCE per compile, on the
    candidate the CEGAR loop accepted -- never per candidate, which would
    multiply the per-rejection cost that already dominates `dog` (578 s)
    and leaves `rabbit` unresolved.

    Returns a `layer_certify.Verdict`. CERTIFIED is still not a proof of
    flat-foldability: see `layer_certify`'s module docstring on
    AREA_EPS-dropped cells."""
    return layer_certify.decide(_seeded(graph, labels), budget=budget)
```

Add `import layer_certify` to the imports at the top of `mcp_harness/box_pleat/layers.py`, beside the existing `import layer_order`.

- [ ] **Step 4: Wire it into `compile.py`**

Four edits to `mcp_harness/box_pleat/compile.py`.

(a) Add `import layer_certify` beside the existing imports at the top of the file.

(b) Extend `LayerFail`'s docstring kind list (`compile.py:46-77`) with the fourth kind, inserting after the `"unfixable"` bullet:

```python
    * "uncertified" -- a labelling was accepted by the per-candidate filter
      but `layer_certify.decide` did not CERTIFY it. Two sub-cases, told
      apart by `witness.kind`: REFUTED means no complete layer order exists
      (and if `witness.violation` is set, propagation was WRONG on this
      input -- a finding about the oracle, not about the packing);
      UNDECIDED means the node budget ran out and says nothing about the
      crease set, exactly as "budget" above.
```

(c) Add the field to `Result` (after `layers_tried`, `compile.py:96`):

```python
    # `layer_certify.Verdict` for the accepted candidate, or None when the
    # compile never reached the `layers` stage. Replaces the old
    # `consistent` / `contradiction` reading, which named something this
    # pipeline could not establish.
    verdict: object = None
```

(d) Change `compile_tree`'s signature (`compile.py:99`) to add the budget:

```python
def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                 assign_budget=500_000, layer_budget=200,
                 certify_budget=layer_certify.CERTIFY_BUDGET) -> Result:
```

(e) Replace `compile.py:300-310` (from the `# No res.stage_reached = "layers"` comment to the end of the function) with:

```python
    # The candidate `assign` accepted passed the per-candidate FILTER, which
    # only ever established "no contradiction found". Certify it once here:
    # a complete layer order must exist and satisfy every ADK clause before
    # this compiler claims the base stacks. Once, not per candidate -- see
    # `layers.certify`'s docstring for why.
    fold = to_fold(lay, asg)
    ff = flat_fold.flat_fold(fold)
    graph = graph_cell[0] if graph_cell else _layers.constraint_graph(ff)
    labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
    res.verdict = _layers.certify(graph, labels, budget=certify_budget)
    if res.verdict.kind != "CERTIFIED":
        res.stage_reached = "layers"
        res.failure = LayerFail("uncertified", res.verdict, counter[0])
        tick("layers")
        return res
    tick("layers")

    res.stage_reached = "emit"
    res.fold = fold
    tick("emit")
    return res
```

Note `res.fold = fold` reuses the `to_fold` result rather than calling it twice — the old line was `res.fold = to_fold(lay, asg)`.

- [ ] **Step 5: Run the fast suite**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py tests/test_layer_order.py tests/test_mv_symmetrize.py -v -m "not slow"
```

Expected: all pass. `test_layer_order.py` and `test_mv_symmetrize.py` must be untouched and green — they are the tripwire for the global constraint that `layer_order.py` is not edited.

- [ ] **Step 6: Verify `layer_order.py` really is untouched**

```bash
git diff --stat HEAD -- mcp_harness/layer_order.py
```

Expected: no output. If there is any, STOP: the blast-radius constraint has been violated and the change belongs in a different spec.

- [ ] **Step 7: Run the slow integration test (lizard compiles, ~10 s)**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_certify.py -v -m slow
```

Expected: 3 passed.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/layer_certify.py mcp_harness/box_pleat/layers.py mcp_harness/box_pleat/compile.py mcp_harness/tests/test_layer_certify.py
git commit -m "$(cat <<'MSG'
box_pleat: certify the accepted candidate, once per compile

`layers.propagate` stays the CEGAR loop's per-candidate filter, unchanged
and cheap. `layers.certify` runs ONCE on the candidate the loop accepts
and asks the question the filter cannot: does a complete layer order
exist? Per-candidate certification was rejected -- each rejection already
costs a fresh CSP re-descent, dog takes 578 s and rabbit is unresolved.

Both tiers seed `direct` through one `_seeded` builder, so they cannot
end up judging different constraint sets.

`Result.verdict` replaces the old consistent/contradiction reading, and a
non-CERTIFIED verdict refuses at stage `layers` with a fourth LayerFail
kind, "uncertified", whose docstring keeps REFUTED (a fact about the
folded state, or about the oracle) apart from UNDECIDED (a fact about the
budget).

layer_order.py is unmodified, which is the point: four serve-path callers
read it and their readings must not move.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

### Task 6: Measure the corpus against the pre-registered bar, and report it

**Files:**
- Create: `docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify_corpus.py`
- Modify: `docs/superpowers/evidence/2026-09-20-box-pleat/README.md`
- Modify: `mcp_harness/tests/test_box_pleat_e2e.py` (the `LAYERS_EXPECTED` table)

**Interfaces:**
- Consumes: `compile.compile_tree` (now returning `Result.verdict`), `layer_certify.Verdict`.
- Produces: `certify_corpus.py` writing `certify.json` with one row per subject: `subject`, `kind`, `nodes`, `free`, `stage_reached`, `secs`.

**The bar, pre-registered in the spec and not to be renegotiated after seeing the numbers:**

1. `horse`, `octopus`, `frog`, `guinea_pig`, `dog` → `CERTIFIED`, `free == 0`, `nodes == 1`.
2. `bird`, `lizard` → decided, `free == 2`, `nodes <= 8`.
3. `starfish` → any of the three verdicts, recorded with its node count. **No expectation pinned.**
4. Every emitted `.fold` byte-identical to `46e2750`'s output.
5. `git diff` for `mcp_harness/layer_order.py` empty.

- [ ] **Step 1: Write the corpus measurement script**

Create `docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify_corpus.py`:

```python
"""The pre-registered bar for layer certification, measured.

Run from `mcp_harness/`:
  PYTHONPATH=. ../.venv/bin/python \
    ../docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify_corpus.py OUT.json

~17 min: dog 524 s and guinea_pig 354 s dominate, as they do for every
probe on this corpus. Rows are written after each subject so the fast ones
land while the big ones run.
"""
from __future__ import annotations
import json, sys, time

from box_pleat.compile import compile_tree

RULE6 = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
         "/data/rule6_serve.json")
OUT = sys.argv[1]
ORDER = ["starfish", "bird", "lizard", "horse", "octopus", "frog",
         "guinea_pig", "dog"]


def main():
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    rows = []
    for s in ORDER:
        t0 = time.time()
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        v = res.verdict
        rows.append({"subject": s, "stage_reached": res.stage_reached,
                     "kind": None if v is None else v.kind,
                     "nodes": None if v is None else v.nodes,
                     "free": None if v is None else v.free,
                     "tried": res.layers_tried,
                     "secs": round(time.time() - t0, 1)})
        json.dump(rows, open(OUT, "w"), indent=1)
        print(f"{s:11s} {res.stage_reached:8s} "
              f"{rows[-1]['kind']} free={rows[-1]['free']} "
              f"nodes={rows[-1]['nodes']} {rows[-1]['secs']}s", flush=True)


main()
```

- [ ] **Step 2: Run it**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python ../docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify_corpus.py ../docs/superpowers/evidence/2026-09-20-box-pleat/oracle-census/certify.json
```

Expected: 8 rows. Check each against the bar above.

- [ ] **Step 3: Handle `starfish`'s outcome — both branches, pick by what step 2 printed**

`starfish` is the only subject whose outcome the bar does not pin, and it is also one of the three byte-identity goldens (`mcp_harness/tests/data/starfish-v1.fold`). The two cases need different work, and which one applies is decided by the measurement, not by preference.

**If `starfish` is CERTIFIED:** nothing to do here. Its golden still passes because the fold is unchanged.

**If `starfish` is REFUTED or UNDECIDED:** it stops emitting, and the golden test that asserts it emits byte-identically now asserts something false. Do NOT relax the refusal to keep the golden green — loosening a gate to protect a headline is this project's named recurring failure mode. Instead, re-fixture the test to assert the new truth, in `mcp_harness/tests/test_box_pleat_e2e.py`:

```python
def test_starfish_no_longer_certifies_and_therefore_no_longer_emits():
    """starfish read `consistent` in 1 try with 0 flips before layer
    certification existed, and that reading was close to vacuous: 252 of
    the 561 pairs in its deepest cell were undetermined, in ONE component
    of 114 independent variables after the equality quotient (census
    2026-09-23). It refuses now. That is a finding about what the old
    reading was worth, not a regression."""
    import json
    from box_pleat.compile import compile_tree
    path = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring"
            "/data/rule6_serve.json")
    entry = {e["subject"]: e for e in json.load(open(path))}["starfish"]
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "layers"
    assert res.failure.kind == "uncertified"
    assert res.verdict.kind in ("REFUTED", "UNDECIDED")
```

and change `test_already_consistent_subjects_emit_byte_identical_folds`'s parametrisation at `mcp_harness/tests/test_box_pleat_e2e.py:175` from `("starfish", "bird")` to `("bird",)`, with a comment naming the test above as the reason starfish left. Also update the `LAYERS_EXPECTED` header comment at `:215-217`, which currently says `bird` and `starfish` are both pinned by that test.

- [ ] **Step 3b: Add the new refusal kind to the contradiction invariant's tolerance list**

`test_no_subject_emits_with_a_layer_contradiction` (`mcp_harness/tests/test_box_pleat_e2e.py:160-172`) asserts that a subject which does not emit refused at stage `layers` with one of three kinds:

```python
        assert res.failure.kind in ("no_labelling", "budget", "unfixable")
```

Task 5 added a fourth, `"uncertified"`. Add it to that tuple. Also replace the test's final line — `layer_order.layer_order(flat_fold.flat_fold(res.fold))   # must not raise` — which re-runs the OLD oracle, with an assertion on the new verdict:

```python
        assert res.verdict is not None and res.verdict.kind == "CERTIFIED", (
            subject, res.verdict)
```

and drop the now-unused `import flat_fold` / `import layer_order` from that function. The invariant the test names is unchanged; what establishes it has moved.

- [ ] **Step 4: Update `LAYERS_EXPECTED` and its assertion in the e2e table**

`mcp_harness/tests/test_box_pleat_e2e.py:238-246` currently reads:

```python
LAYERS_EXPECTED = {
    "dog": "consistent",
    "horse": "consistent",
    "guinea_pig": "consistent",
    "lizard": "consistent",
    "frog": "consistent",
    "octopus": "consistent",
    "rabbit": "assign_budget",
}
```

Replace each `"consistent"` with that subject's measured kind from step 2's `certify.json` — `"CERTIFIED"` for every one of the six if the bar held. `rabbit` keeps `"assign_budget"`: it never reaches the `layers` stage, so certification cannot apply to it.

Then change the assertion branch in `test_layer_outcome_matches_the_record` (`:250-262`), which currently re-runs the OLD oracle:

```python
    if want == "consistent":
        assert res.stage_reached == "emit", (subject, res.stage_reached, res.failure)
        layer_order.layer_order(flat_fold.flat_fold(res.fold))
```

to assert the new verdict instead:

```python
    if want == "CERTIFIED":
        assert res.stage_reached == "emit", (subject, res.stage_reached, res.failure)
        assert res.verdict is not None
        assert res.verdict.kind == "CERTIFIED", (subject, res.verdict)
```

and drop the now-unused `import flat_fold` / `import layer_order` from that function if nothing else in it uses them. `consistent` is no longer a value this pipeline produces, so any row or branch still carrying it is stale.

- [ ] **Step 5: Run the e2e suite**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_e2e.py -v
```

Expected: all pass. This is the slow tier — budget ~45 min, as the existing strict-table rows already cost.

- [ ] **Step 6: Report it in the evidence README**

In `docs/superpowers/evidence/2026-09-20-box-pleat/README.md`, in the "Oracle completeness census (`oracle-census/`)" section, append a subsection with: the 8-row table from `certify.json`; the statement that `consistent` is no longer reported and why; and the surviving caveat that CERTIFIED means "certified against the constraint set that survived `AREA_EPS`", with the note that the census cannot see that deficit by construction. Update the "Layer order" section's headline sentence, which currently says 8 of 10 read `consistent`, to the certified count.

- [ ] **Step 7: Commit**

```bash
git add docs/superpowers/evidence/2026-09-20-box-pleat/ mcp_harness/tests/test_box_pleat_e2e.py
git commit -m "$(cat <<'MSG'
evidence: the certification bar, measured

Per-subject CERTIFIED / REFUTED / UNDECIDED across the 8 emitting
subjects, against the bar pre-registered in the spec before any code was
written. `consistent` is no longer reported: it named something this
pipeline could not establish.

The surviving caveat is stated rather than buried -- CERTIFIED means
certified against the constraint set that survived AREA_EPS, and the
census cannot see that deficit by construction, because a dropped cell
removes pairs before they are counted.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
MSG
)"
```

---

## Self-review

**Spec coverage.** §2 blast radius → Task 5 steps 6 and the Global Constraints. §3 prior art → Task 1's derivation block and the module docstring. §4.1 `clauses` → Task 1. §4.2 `verify` → Task 2. §4.3 `collapse` → Task 3. §4.4 `decide` + budget → Task 4. §4.5 two tiers → Task 5. §5 verdict semantics and the AREA_EPS caveat → Task 4's `Verdict` docstring, the module docstring, Task 6 step 6. §6 bar → Task 6. §7.1–7.7 tests → Tasks 1–6 respectively (7.6 goldens in Task 5 step 1 and Task 6 step 3; 7.7 e2e in Task 6 step 5). §8 risks → Task 6 step 3 carries risk 1 and 2 concretely; risk 3 is in the Global Constraints; risk 5 is Task 6 step 4.

**Three defects found in self-review and fixed inline.**

1. **Two tests would have passed vacuously.** The first draft hand-rolled a 1x3 strip fixture and asserted `len(taco_clauses) == len(cons.tacos)` and the same for equalities. Measured: that fixture generates **0 equalities and 0 tacos**, so both assertions read `0 == 0` and proved nothing — the precise failure mode this project already has a rule about ("never accept 'no gap' from a partial metric"). Fixed by choosing fixtures per family from a measured table and pairing every count assertion with a non-vacuity assertion. The fixtures are `test_layer_order.py`'s existing hand-derived strips rather than new ones.
2. **`Verdict.free` counted the wrong thing.** The first draft recorded the number of unforced *pairs*; the design doc says independent variables *after* the equality quotient. On `bird` those are 8 and 2. Fixed in `decide` (`root_free` is set from the class count) and pinned by the `bird`/`lizard` test asserting both numbers.
3. **Task 6 named the wrong parametrisation.** `test_already_consistent_subjects_emit_byte_identical_folds` is parametrised over `("starfish", "bird")`, not starfish and lizard, and its `LAYERS_EXPECTED` header comment says so too. Both are now named with line numbers.

**One spec gap found and closed here.** §6 bar item 4 ("every emitted `.fold` byte-identical") and §5's refusal rule contradict each other if `starfish` fails to certify: it would stop emitting, so there would be no fold to compare, and the byte-identity golden would assert something false. The spec did not say which wins. **Task 6 step 3 resolves it in the spec's own spirit** — the refusal stands, the golden is re-fixtured to assert the new truth, and the reasoning is recorded in the test rather than the gate being relaxed. Both branches are fully written out so the outcome is decided by measurement.

**Placeholder scan.** No TBD/TODO. Every code step carries the code. Task 6 step 4's edit is data-dependent by nature (it copies measured values into a table), and step 2 produces those values before it.

**Type consistency.** `Clause(family, variables, flips, prov)`, `Violation(family, variables, values, prov)`, `VerifyResult(violation, checked, skipped)`, `Verdict(kind, violation, nodes, free)` are defined once and used consistently. `collapse` returns `(dict, Violation | None)` in Task 3 and is consumed that way in Task 4. `layers.certify(graph, labels, *, budget)` is produced in Task 5 and consumed in `compile.py` in the same task. Family strings are exactly `"equality"`, `"transitivity"`, `"taco"` throughout.

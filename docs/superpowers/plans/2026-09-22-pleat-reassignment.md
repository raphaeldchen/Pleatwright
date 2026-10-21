# Pleat Reassignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the box-pleat compiler produce crease patterns that are *globally* flat-foldable — no subject reaches `emit` with a layer-order contradiction — by searching M/V labellings of a fixed crease set.

**Architecture:** The assign CSP gains pleat-path variables and a no-good store. A new `box_pleat/layers.py` re-propagates `layer_order`'s constraint system under a candidate labelling and returns a structured witness; `compile.py` injects that as a `global_check` hook and caches the label-independent part of the system. Nothing else in the pipeline changes: the packing, the elevation field and the folded base are byte-identical by construction.

**Tech Stack:** Python 3.14, numpy, pytest. No new dependencies.

## Global Constraints

Copied from `docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md`:

- The crease **set** never changes. Only M↔V labels move. F stays F.
- The packing, the elevation field and the folded base stay byte-identical.
- A subject whose crease set admits no consistent labelling **refuses** at a new `layers` stage with a typed `LayerFail`. Owner ruling 2026-09-22: "refuse — it's a finding, not a regression."
- `compile_tree` never raises for a well-formed tree.
- `bird` and `starfish` are already consistent; their emitted FOLD must stay byte-identical.
- No new dependency. No SAT/MILP solver.
- Run tests as: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest <args>`
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
- In this worktree never use bare `git stash`; never `cd` to the main repo root.

## Measured baseline (2026-09-22, this branch at `21e316c`)

These numbers are the reason the plan is shaped this way. Reproduce with the
scripts named in each task.

| fact | value |
|---|---|
| layer-order contradictions | 8 of the 10 emitting subjects, **all taco-tortilla** |
| consistent today | `bird`, `starfish` |
| `layer_order()` per call | horse 1.72 s, octopus 10.17 s |
| of which `_cells` + `_build_constraints` (label-independent) | horse 1.72 s, octopus 2.02 s |
| of which `_propagate` (per candidate) | horse 0.7 ms, octopus **7.98 s** |
| `_propagate` with transitivity disabled | octopus 64 ms, but reads **consistent** — transitivity is load-bearing for detection, not just cost |

So: the label-independent part must be cached (Task 7), and the transitivity
closure must be made incremental (Task 2) or a 200-candidate loop on octopus
costs 26 minutes.

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/tests/test_layers_theorem.py` | **new.** Locks the two facts the design rests on: relabelling preserves the folded base; the merge topology is label-independent. |
| `mcp_harness/layer_order.py` | **modified.** Incremental transitivity; structured provenance (`Prov`); dependency tracking; `LayerContradiction`; public `constraints_for` and `propagate`. |
| `mcp_harness/box_pleat/layers.py` | **new.** `LayerGraph`, `Witness`, `constraint_graph`, `propagate(graph, labels)`, `piece_keys`. The only module that knows how a labelling becomes a layer-order verdict. |
| `mcp_harness/box_pleat/assign.py` | **modified.** Pleat-path variables; no-good store; `global_check` hook. |
| `mcp_harness/box_pleat/compile.py` | **modified.** `layers` stage, `LayerFail`, `layer_budget`, the graph cache and the hook closure. |
| `mcp_harness/probe_box_pleat.py` | **modified.** `layer_order` / `layers_tried` columns. |
| `mcp_harness/tests/test_layer_order.py` | **modified.** Equivalence and provenance tests. |
| `mcp_harness/tests/test_box_pleat_assign.py` | **modified.** Pleat-path and no-good tests. |
| `mcp_harness/tests/test_box_pleat_e2e.py` | **modified.** The strict expectation table. |

---

### Task 1: Lock the enabling theorem

The whole design rests on two claims about existing code. Prove them before
building anything on top. Both tests pass against today's code — they are
characterization tests, and if either fails the design is wrong and the rest
of the plan must stop.

**Files:**
- Create: `mcp_harness/tests/test_layers_theorem.py`

**Interfaces:**
- Consumes: `box_pleat.compile.compile_tree`, `box_pleat.emit.to_fold`, `flat_fold.flat_fold`
- Produces: nothing importable; a gate for Tasks 2-8.

- [ ] **Step 1: Write both tests**

```python
"""The two facts the pleat-reassignment design rests on (spec §3).

1. Relabelling M<->V on a FIXED crease set leaves the folded base
   byte-identical: flat_fold composes reflections, and a reflection does
   not care which way the paper turns.
2. The emitted FOLD's TOPOLOGY does not depend on the labels either, so a
   layer-order constraint system built for one labelling is valid for every
   other labelling of the same crease set (which is what makes the cache in
   compile.py sound). emit._merge_runs tests label equality, but at a vertex
   of degree 2 over the kept pieces Maekawa already forces the two incident
   creases to agree -- |M - V| = 2 over exactly two creases has no mixed
   solution -- so the label test never splits a run that geometry would join.
"""
import json
import os
import random

import pytest

import flat_fold
from box_pleat.compile import compile_tree
from box_pleat.emit import to_fold

RULE6 = os.path.join(os.path.dirname(__file__), "..", "..", "docs",
                     "superpowers", "evidence", "2026-09-08-vlm-tree-authoring",
                     "data", "rule6_serve.json")


def _compiled(subject):
    for e in json.load(open(RULE6)):
        if e["subject"] == subject:
            res = compile_tree(e["requested"], e["pairs"])
            assert res.stage_reached == "emit", res.failure
            return res
    raise AssertionError(f"no subject {subject}")


def test_relabelling_preserves_the_folded_base():
    res = _compiled("lizard")
    fold = to_fold(res.layout, res.assignment)
    base = flat_fold.flat_fold(fold)
    rng = random.Random(20260922)
    for _ in range(50):
        other = dict(fold)
        other["edges_assignment"] = [
            (rng.choice(("M", "V")) if a in ("M", "V") else a)
            for a in fold["edges_assignment"]]
        got = flat_fold.flat_fold(other)
        assert len(got.folded_vertices) == len(base.folded_vertices)
        for A, B in zip(got.folded_vertices, base.folded_vertices):
            assert A.tolist() == B.tolist()
        assert got.closure.max_error == base.closure.max_error


def test_merge_topology_does_not_depend_on_labels():
    res = _compiled("horse")
    fold = to_fold(res.layout, res.assignment)
    flipped = {"M": "V", "V": "M"}
    asg = res.assignment
    mirrored = type(asg)(asg.pieces, [flipped.get(l, l) for l in asg.labels])
    other = to_fold(res.layout, mirrored)
    assert other["vertices_coords"] == fold["vertices_coords"]
    assert other["edges_vertices"] == fold["edges_vertices"]
    assert other["edges_assignment"] != fold["edges_assignment"]
```

- [ ] **Step 2: Run them**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layers_theorem.py -v`
Expected: 2 passed. `lizard` compiles in ~0.6 s and `horse` in ~4 s.

**If either fails, STOP and report.** A failure of the first means the folded
base is label-dependent and the spec's §3 is false; a failure of the second
means the graph cache in Task 7 is unsound and the plan needs re-cutting.

- [ ] **Step 3: Commit**

```bash
git add mcp_harness/tests/test_layers_theorem.py
git commit -m "$(printf 'box_pleat: lock the two facts pleat reassignment rests on\n\nRelabelling a fixed crease set leaves flat_fold byte-identical, and the\nemitted FOLD topology is label-independent because Maekawa forces the two\ncreases at a degree-2 vertex to agree. Both are characterization tests\nagainst existing code; the cache in the layers stage is unsound without\nthe second.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 2: Make the global check affordable

`_propagate` re-enumerates every ordered triple of every cell's cover on
every fixpoint round. Octopus spends 7.98 s of an 8.00 s call there. A triple
can only fire when one of its two premises has just become true, so close over
a worklist instead.

**Files:**
- Modify: `mcp_harness/layer_order.py:645-660` (the `for cover in cons.covers` block inside `_propagate`)
- Test: `mcp_harness/tests/test_layer_order.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `_propagate(cons)` unchanged in signature and in *verdict*; faster. Which witness a contradiction reports may change (derivation order changed); whether a contradiction exists may not.

- [ ] **Step 1: Write the failing performance test**

Add to `mcp_harness/tests/test_layer_order.py`:

```python
@pytest.mark.slow
def test_propagate_transitivity_is_incremental():
    """Octopus measured 7.98 s in the triple loop on 2026-09-22; the
    worklist closure must bring the whole propagate under a second while
    returning the same verdict. Transitivity cannot simply be skipped:
    without it octopus and frog read CONSISTENT (measured same day), so
    this is a speed-up of a load-bearing inference, not a shortcut."""
    import json
    import time
    import numpy as np
    import flat_fold
    import layer_order as L
    from box_pleat.compile import compile_tree
    from box_pleat.emit import to_fold
    entry = next(e for e in json.load(open(RULE6_PATH))
                 if e["subject"] == "octopus")
    res = compile_tree(entry["requested"], entry["pairs"])
    ff = flat_fold.flat_fold(to_fold(res.layout, res.assignment))
    polys = []
    for P in ff.folded_vertices:
        P = np.asarray(P, float)
        polys.append(P[::-1] if L._area(P) < 0 else P)
    cons = L._build_constraints(ff, polys, L._cells(polys))
    t0 = time.perf_counter()
    with pytest.raises(ValueError, match="layer-order contradiction"):
        L._propagate(cons)
    assert time.perf_counter() - t0 < 1.0
```

`RULE6_PATH` does not exist in that file yet. Add it beside the other module
constants at the top of `tests/test_layer_order.py`:

```python
RULE6_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs",
                          "superpowers", "evidence",
                          "2026-09-08-vlm-tree-authoring", "data",
                          "rule6_serve.json")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_order.py::test_propagate_transitivity_is_incremental -v`
Expected: FAIL on the `assert time.perf_counter() - t0 < 1.0` line, at roughly 8 s. (Total test time ~45 s: octopus compiles in ~20 s.)

- [ ] **Step 3: Replace the triple loop**

In `mcp_harness/layer_order.py`, inside `_propagate`, delete the block:

```python
        for cover in cons.covers:
            for a, b, c in combinations(sorted(cover), 3):
                for x, y, z in ((a, b, c), (a, c, b), (b, a, c),
                                (b, c, a), (c, a, b), (c, b, a)):
                    if (get(_lit(x, y)) is True
                            and get(_lit(y, z)) is True
                            and get(_lit(x, z)) is None):
                        changed |= put(_lit(x, z), True,
                                       f"transitivity {x}>{y}>{z}")
```

and put this in its place (keeping it inside the `while changed:` body, after
the `tacos` loop):

```python
        changed |= _close_transitively(cons, rel, get, put, covers_of, up, down)
```

Add these two helpers at module level, above `_propagate`:

```python
def _covers_of(cons: _Constraints) -> dict:
    """face -> the set of cell indices whose cover contains it. Transitivity
    only holds where all three faces are stacked over ONE cell, so a
    derivation is admissible exactly when the three faces share a cover."""
    out: dict = {}
    for ci, cover in enumerate(cons.covers):
        for x in cover:
            out.setdefault(x, set()).add(ci)
    return out


def _close_transitively(cons, rel, get, put, covers_of, up, down) -> bool:
    """Worklist transitive closure, replacing a per-round enumeration of
    every ordered triple of every cover (measured 2026-09-22: 7.98 s of an
    8.00 s propagate on octopus). `up[x]` holds every y with "x above y"
    already seen and `down` its inverse; a pair only needs closing once, so
    each round processes the pairs that became true since the last one.

    Same fixpoint, different order. Propagation is confluent -- derived
    facts are implied, never retracted -- so a consistent input still
    reaches a fixpoint and an inconsistent one still raises. Which of
    several contradictions is reported can differ from the old order."""
    pending = []

    def note(x, y):
        if y in up.setdefault(x, set()):
            return
        up[x].add(y)
        down.setdefault(y, set()).add(x)
        pending.append((x, y))

    for (lo, hi), v in list(rel.items()):
        note(lo, hi) if v else note(hi, lo)
    changed = False
    while pending:
        x, y = pending.pop()
        cx, cy = covers_of.get(x, ()), covers_of.get(y, ())
        for z in list(up.get(y, ())):                      # x > y > z
            if covers_of.get(z, set()) & set(cx) & set(cy) and get(_lit(x, z)) is None:
                changed |= put(_lit(x, z), True, f"transitivity {x}>{y}>{z}")
                note(x, z)
        for w in list(down.get(x, ())):                    # w > x > y
            if covers_of.get(w, set()) & set(cx) & set(cy) and get(_lit(w, y)) is None:
                changed |= put(_lit(w, y), True, f"transitivity {w}>{x}>{y}")
                note(w, y)
    return changed
```

and initialise the three caches once, immediately before the `changed = True`
line in `_propagate`:

```python
    covers_of = _covers_of(cons)
    up: dict = {}
    down: dict = {}
```

- [ ] **Step 4: Run the performance test and the whole layer-order suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_order.py tests/test_mv_symmetrize.py -v`
Expected: all pass, including the new one. If any pre-existing test asserts a
specific *contradiction message*, and it now names a different witness, that
is the accepted behaviour change — update the assertion and say so in the
commit body. If a test flips between consistent and contradiction, that is a
**bug in this task**: stop, the closure is not equivalent.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/layer_order.py mcp_harness/tests/test_layer_order.py
git commit -m "$(printf 'layer_order: incremental transitive closure\n\nThe triple loop re-enumerated every ordered triple of every cover on every\nfixpoint round: 7.98 s of an 8.00 s propagate on octopus. A triple can only\nfire when a premise has just become true, so close over a worklist.\n\nSame fixpoint (propagation is confluent), so the verdict is unchanged;\nwhich of several contradictions is reported can differ. Transitivity is\nNOT optional -- without it octopus and frog read consistent.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 3: Structured provenance and dependency tracking

A no-good clause must name the *label decisions* a contradiction depends on.
Today that information is formatted into a string and lost. Make provenance a
dataclass whose `__str__` is the old string, and track, per derived literal,
the set of creases whose labels it depends on.

**Files:**
- Modify: `mcp_harness/layer_order.py` (provenance construction sites at lines 460, 526, 534, 537, 565, 583, 593; `_Constraints`; `_propagate`; new public `constraints_for` and `propagate`)
- Test: `mcp_harness/tests/test_layer_order.py`

**Interfaces:**
- Produces, all new and public:
  - `Prov(text: str, creases: tuple = (), faces: tuple = ())` with `__str__` returning `text`
  - `DirectSlot(edge: tuple, lit: tuple, sign: int, faces: tuple)`
  - `LayerContradiction(ValueError)` with `.prov: Prov` and `.deps: frozenset | None`
  - `constraints_for(result) -> tuple[_Constraints, tuple[DirectSlot, ...]]`
  - `propagate(cons, *, deps=False) -> dict`
- `layer_order(result)` keeps its signature, behaviour and message.

- [ ] **Step 1: Write the failing tests**

Add to `mcp_harness/tests/test_layer_order.py`:

```python
def test_prov_str_is_the_old_message():
    from layer_order import Prov
    p = Prov("taco-tortilla crease (3, 7)", creases=((3, 7),), faces=(1, 2))
    assert str(p) == "taco-tortilla crease (3, 7)"
    assert f"{p} through face 9" == "taco-tortilla crease (3, 7) through face 9"


@pytest.mark.slow
def test_contradiction_carries_the_creases_it_depends_on():
    """A no-good clause is exactly the set of label decisions the
    contradiction followed from, so every dependency must be a crease that
    appears in the direct slots -- never a face index, never empty."""
    import json
    import numpy as np
    import flat_fold
    import layer_order as L
    from box_pleat.compile import compile_tree
    from box_pleat.emit import to_fold
    entry = next(e for e in json.load(open(RULE6_PATH))
                 if e["subject"] == "horse")
    res = compile_tree(entry["requested"], entry["pairs"])
    ff = flat_fold.flat_fold(to_fold(res.layout, res.assignment))
    cons, slots = L.constraints_for(ff)
    with pytest.raises(L.LayerContradiction) as exc:
        L.propagate(cons, deps=True)
    assert str(exc.value).startswith("layer-order contradiction via ")
    assert exc.value.deps
    assert exc.value.deps <= {s.edge for s in slots}
    # deterministic: the same system must report the same witness, or a
    # no-good store cannot make progress
    with pytest.raises(L.LayerContradiction) as again:
        L.propagate(cons, deps=True)
    assert again.value.deps == exc.value.deps
    assert str(again.value) == str(exc.value)


@pytest.mark.slow
def test_layer_order_entry_point_is_unchanged():
    """constraints_for must return the same system layer_order() builds."""
    import json
    import flat_fold
    import layer_order as L
    from box_pleat.compile import compile_tree
    from box_pleat.emit import to_fold
    entry = next(e for e in json.load(open(RULE6_PATH))
                 if e["subject"] == "starfish")
    res = compile_tree(entry["requested"], entry["pairs"])
    ff = flat_fold.flat_fold(to_fold(res.layout, res.assignment))
    cons, slots = L.constraints_for(ff)
    assert L.propagate(cons) == L.layer_order(ff)._rel
    assert {s.edge for s in slots} <= {k for _, _, k, a in ff.shared_edges
                                       if a in ("M", "V")}
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_order.py -k "prov_str or depends_on or entry_point_is_unchanged" -v`
Expected: FAIL with `ImportError: cannot import name 'Prov'` and `AttributeError: module 'layer_order' has no attribute 'constraints_for'`.

- [ ] **Step 3: Add the types and the public entry points**

In `mcp_harness/layer_order.py`, above `_Constraints`:

```python
@dataclass(frozen=True)
class Prov:
    """Why a relation is forced. `text` is the message this module has
    always produced -- every site interpolates provenance into an f-string,
    so __str__ keeps those byte-identical -- and `creases`/`faces` carry the
    same facts structurally, so a caller can build a no-good clause without
    parsing English."""
    text: str
    creases: tuple = ()
    faces: tuple = ()

    def __str__(self) -> str:
        return self.text


@dataclass(frozen=True)
class DirectSlot:
    """Where an M/V label enters the system: one per creased shared edge
    whose faces overlap. `val = (label == "V") == (sign == 1)`."""
    edge: tuple
    lit: tuple
    sign: int
    faces: tuple


class LayerContradiction(ValueError):
    """A contradiction, with the provenance that raised it and -- when
    `propagate(deps=True)` tracked them -- the creases whose labels it
    depends on. Subclasses ValueError and formats identically, so every
    existing `except ValueError` and every message assertion still holds."""

    def __init__(self, prov, deps=None):
        super().__init__(f"layer-order contradiction via {prov}")
        self.prov = prov
        self.deps = deps
```

Change `needs_flat_edge` (line 460) to accept either form:

```python
def needs_flat_edge(provenance) -> bool:
    ...
    return "flat edge" in str(provenance)
```

Add the field to `_Constraints`:

```python
    slots: tuple = ()     # DirectSlot per creased shared edge in `pairs`
```

In `_build_constraints`, build slots beside the direct facts. Replace:

```python
            val = (a == "V") == (orient[fa] == 1)   # "fb above fa"
            direct.append((_lit(fb, fa), val, f"crease {k} {a}"))
```

with:

```python
            val = (a == "V") == (orient[fa] == 1)   # "fb above fa"
            direct.append((_lit(fb, fa), val,
                           Prov(f"crease {k} {a}", creases=(k,), faces=(fa, fb))))
            slots.append(DirectSlot(edge=k, lit=_lit(fb, fa),
                                    sign=orient[fa], faces=(fa, fb)))
```

initialising `slots = []` beside `direct, eqs, tacos = [], [], []`, and
returning `slots=tuple(slots)` from the `_Constraints(...)` constructor.

Wrap the remaining provenance construction sites (all in `_build_constraints`)
so each carries its facts. The texts are unchanged:

```python
        _spanning(seg, fa, fb, Prov(f"taco-tortilla crease {k}",
                                    creases=(k,), faces=(fa, fb)))
...
    for fa, fb, seg, k in tortillas:
        _spanning(seg, fa, fb, Prov(f"tortilla-tortilla flat edge {k}",
                                    faces=(fa, fb)))
```

and inside `_spanning`, which *composes* a provenance rather than consuming
one:

```python
            eqs.append((_lit(x, fa), _lit(x, fb),
                        Prov(f"{prov} through face {x}",
                             creases=prov.creases, faces=prov.faces + (x,))))
```

the taco-tortilla-along-a-flat-edge site:

```python
                eqs.append((_lit(x, fa), _lit(x, fb),
                            Prov(f"taco-tortilla crease {k} along flat edge {tk}",
                                 creases=(k,), faces=(x, fa, fb))))
```

the tortilla-tortilla site:

```python
        eqs.append((_lit(A[1], B[1]), _lit(A[-1], B[-1]),
                    Prov(f"tortilla-tortilla flat edges {k1}x{k2}",
                         faces=(A[1], B[1], A[-1], B[-1]))))
```

and both taco-taco sites:

```python
        tacos.append(((fa1, fb1), (fa2, fb2),
                      Prov(f"taco-taco {k1}x{k2}", creases=(k1, k2),
                           faces=(fa1, fb1, fa2, fb2))))
        tacos.append(((fa2, fb2), (fa1, fb1),
                      Prov(f"taco-taco {k2}x{k1}", creases=(k2, k1),
                           faces=(fa2, fb2, fa1, fb1))))
```

In `_close_transitively` (Task 2) wrap its two provenances the same way:
`Prov(f"transitivity {x}>{y}>{z}", faces=(x, y, z))`.

- [ ] **Step 4: Track dependencies in `_propagate`**

Change `_propagate`'s signature and its `put` so a literal remembers which
label decisions it followed from. Every constraint site passes the literals it
read as `srcs`.

```python
def _propagate(cons: _Constraints, *, deps: bool = False) -> dict:
    """Fixpoint propagation. Returns rel: {(lo,hi): bool} for FORCED
    pairs only. Raises LayerContradiction (a ValueError) on contradiction.

    With deps=True every derived literal also carries the set of creases
    whose LABELS it depends on, and a contradiction reports the union over
    the two conflicting derivations: that set is a sound no-good clause,
    because the conflict follows from exactly those label decisions."""
    rel: dict = {}
    dep: dict = {}

    def get(lit):
        pair, flip = lit
        v = rel.get(pair)
        return None if v is None else (v != flip)

    def _dep_of(prov, srcs):
        if not deps:
            return None
        out = set(prov.creases)
        for pair, _ in srcs:
            out |= dep.get(pair, frozenset())
        return frozenset(out)

    def put(lit, value, prov, srcs=()) -> bool:
        pair, flip = lit
        v = (value != flip)
        d = _dep_of(prov, srcs)
        if pair in rel:
            if rel[pair] != v:
                raise LayerContradiction(
                    prov, None if not deps else d | dep.get(pair, frozenset()))
            return False
        rel[pair] = v
        if deps:
            dep[pair] = d
        return True
```

Then pass `srcs` at the three derived sites. In the equalities loop:

```python
            if va is None and vb is not None:
                changed |= put(la, vb, prov, srcs=(lb,))
            elif vb is None and va is not None:
                changed |= put(lb, va, prov, srcs=(la,))
            elif va is not None and vb is not None and va != vb:
                raise LayerContradiction(
                    prov, None if not deps
                    else (dep.get(la[0], frozenset()) | dep.get(lb[0], frozenset())
                          | frozenset(prov.creases)))
```

In the tacos loop, the all-known contradiction and the one-unknown derivation:

```python
            if all(known):
                if (vals[0] != vals[1]) != (vals[2] != vals[3]):
                    raise LayerContradiction(
                        prov, None if not deps
                        else frozenset(prov.creases).union(
                            *(dep.get(li[0], frozenset()) for li in lits)))
```

```python
                changed |= put(lits[m], (not other) if straddles else other,
                               prov, srcs=tuple(li for i, li in enumerate(lits)
                                                if i != m))
```

and in `_close_transitively`, both `put` calls gain
`srcs=(_lit(x, y), _lit(y, z))` and `srcs=(_lit(w, x), _lit(x, y))`
respectively (matching each derivation's two premises).

Finally add the two public entry points at the end of the module:

```python
def constraints_for(result: FlatFoldResult):
    """The layer-order system for `result`, with the slots where M/V enters
    it. Everything except `_Constraints.direct` depends on the folded
    geometry alone, which `flat_fold` derives from the crease SET -- so a
    caller may re-propagate this same system under any other labelling of
    the same creases (spec §3). Returns (cons, slots)."""
    polys = _polys_of(result)
    cons = _build_constraints(result, polys, _cells(polys))
    return cons, cons.slots


def propagate(cons: _Constraints, *, deps: bool = False) -> dict:
    """Public `_propagate`: the forced relations, or LayerContradiction."""
    return _propagate(cons, deps=deps)
```

`_polys_of` does not exist yet — extract it from `layer_order()`, which
currently inlines the loop at `layer_order.py:711-719`. Replace those lines
in `layer_order()` with

```python
    polys = _polys_of(result)
```

and add the function at module level, so the convexity check and the CCW
normalization cannot drift apart between the two callers:

```python
def _polys_of(result: FlatFoldResult) -> list:
    """Folded faces as CCW convex polygons (reflected faces wind CW)."""
    polys = []
    for i, P in enumerate(result.folded_vertices):
        P = np.asarray(P, dtype=float)
        if _area(P) < 0:
            P = P[::-1]
        if not _is_convex(P):
            raise ValueError(f"face {i} is non-convex; layer ordering "
                             f"supports convex faces only")
        polys.append(P)
    return polys
```

- [ ] **Step 5: Run the full layer-order and mv_symmetrize suites**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_layer_order.py tests/test_mv_symmetrize.py -v`
Expected: all pass, including the three new tests.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/layer_order.py mcp_harness/tests/test_layer_order.py
git commit -m "$(printf 'layer_order: structured provenance and dependency tracking\n\nProvenance becomes Prov, whose __str__ is the message this module has\nalways produced, so every existing assertion and except ValueError still\nholds. propagate(deps=True) now also reports, per contradiction, the set of\ncreases whose LABELS it followed from -- a sound no-good clause.\n\nconstraints_for() exposes the label-independent system plus the slots where\nM/V enters it, so a caller can re-propagate under another labelling.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 4: `box_pleat/layers.py`

The only module that turns a candidate labelling into a verdict.

**Files:**
- Create: `mcp_harness/box_pleat/layers.py`
- Test: `mcp_harness/tests/test_box_pleat_layers.py`

**Interfaces:**
- Consumes: `layer_order.constraints_for`, `layer_order.propagate`, `layer_order.LayerContradiction`, `box_pleat.assign._unit_pieces`
- Produces:
  - `Witness(kind: str, creases: frozenset, faces: tuple, prov: str)`
  - `LayerGraph(cons, slots)`
  - `constraint_graph(ff) -> LayerGraph`
  - `propagate(graph, labels: dict) -> Witness | None`
  - `piece_keys(witness, fold) -> frozenset`  <!-- N dropped; read from the fold, see the Task 4 signature amendment -->

- [ ] **Step 1: Write the failing tests**

```python
"""box_pleat/layers.py: a candidate labelling -> a layer-order verdict."""
import json
import os

import pytest

import flat_fold
from box_pleat import layers
from box_pleat.compile import compile_tree
from box_pleat.emit import to_fold

RULE6 = os.path.join(os.path.dirname(__file__), "..", "..", "docs",
                     "superpowers", "evidence", "2026-09-08-vlm-tree-authoring",
                     "data", "rule6_serve.json")


def _folded(subject):
    entry = next(e for e in json.load(open(RULE6)) if e["subject"] == subject)
    res = compile_tree(entry["requested"], entry["pairs"])
    assert res.stage_reached == "emit", res.failure
    fold = to_fold(res.layout, res.assignment)
    return res, fold, flat_fold.flat_fold(fold)


def _labels(ff):
    return {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}


def test_consistent_subject_returns_none():
    _, _, ff = _folded("starfish")
    assert layers.propagate(layers.constraint_graph(ff), _labels(ff)) is None


def test_contradiction_returns_a_witness_naming_creases():
    _, _, ff = _folded("horse")
    w = layers.propagate(layers.constraint_graph(ff), _labels(ff))
    assert w is not None
    assert w.kind == "taco_tortilla"
    assert w.creases <= set(_labels(ff))
    assert w.prov.startswith("layer-order contradiction via ")


def test_graph_is_label_independent():
    """Same crease set, other labels: same system (spec §3). This is what
    makes caching the graph across candidates sound."""
    _, fold, ff = _folded("frog")
    flipped = dict(fold)
    flipped["edges_assignment"] = [
        {"M": "V", "V": "M"}.get(a, a) for a in fold["edges_assignment"]]
    other = flat_fold.flat_fold(flipped)
    g1, g2 = layers.constraint_graph(ff), layers.constraint_graph(other)
    assert g1.cons.pairs == g2.cons.pairs
    assert g1.cons.equalities == g2.cons.equalities
    assert g1.cons.tacos == g2.cons.tacos
    assert [s.edge for s in g1.slots] == [s.edge for s in g2.slots]


def test_piece_keys_lands_on_unit_pieces():
    res, fold, ff = _folded("starfish")
    w = layers.Witness(kind="taco_tortilla",
                       creases=frozenset([tuple(fold["edges_vertices"][0])]),
                       faces=(), prov="test")
    keys = layers.piece_keys(w, fold)
    piece_keys = {(p.a, p.b) for p in res.assignment.pieces}
    assert keys
    assert keys <= piece_keys
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_layers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'box_pleat.layers'`.

- [ ] **Step 3: Write the module**

```python
"""A candidate M/V labelling -> a global flat-foldability verdict
(spec 2026-09-22-pleat-reassignment §4.1).

`layer_order` decides whether a folded state has a consistent layer order.
Everything it derives except the `direct` facts comes from folded geometry,
which `flat_fold` builds from the crease SET alone -- so the expensive part
is built once per crease set (`constraint_graph`) and every candidate
labelling only re-propagates (`propagate`). Measured 2026-09-22: building
costs 1.7-2.2 s, propagating costs milliseconds.

A contradiction comes back as a `Witness` whose `creases` are the label
decisions it followed from -- a sound no-good clause, not a guess.
"""
from __future__ import annotations

import dataclasses
from dataclasses import dataclass

import layer_order

from .assign import _unit_pieces

_KIND = (("taco-tortilla", "taco_tortilla"),
         ("tortilla-tortilla", "tortilla_tortilla"),
         ("taco-taco", "taco_taco"),
         ("transitivity", "transitivity"),
         ("crease", "direct"))


@dataclass(frozen=True)
class Witness:
    kind: str            # taco_tortilla | tortilla_tortilla | taco_taco | transitivity | direct
    creases: frozenset   # FOLD edge keys (v_lo, v_hi) whose LABELS caused it
    faces: tuple         # face indices the provenance names; diagnostic only
    prov: str            # layer_order's message, unchanged


@dataclass(frozen=True)
class LayerGraph:
    cons: object         # layer_order._Constraints, label-independent part
    slots: tuple         # layer_order.DirectSlot per creased shared edge


def _kind_of(text: str) -> str:
    for needle, kind in _KIND:
        if text.startswith(needle):
            return kind
    return "direct"


def constraint_graph(ff) -> LayerGraph:
    """The label-independent layer-order system of a folded state."""
    cons, slots = layer_order.constraints_for(ff)
    return LayerGraph(cons=cons, slots=slots)


def propagate(graph: LayerGraph, labels: dict) -> Witness | None:
    """None when `labels` admits a consistent layer order, else the witness.

    `labels` maps every slot's edge key to "M" or "V"."""
    direct = tuple(
        (s.lit, (labels[s.edge] == "V") == (s.sign == 1),
         layer_order.Prov(f"crease {s.edge} {labels[s.edge]}",
                          creases=(s.edge,), faces=s.faces))
        for s in graph.slots)
    cons = dataclasses.replace(graph.cons, direct=direct)
    try:
        layer_order.propagate(cons, deps=True)
    except layer_order.LayerContradiction as exc:
        return Witness(kind=_kind_of(exc.prov.text),
                       creases=frozenset(exc.deps or ()),
                       faces=tuple(exc.prov.faces), prov=str(exc))
    return None


def piece_keys(witness: Witness, fold: dict) -> frozenset:
    """The unit-piece keys under the FOLD edges a witness names.

    A FOLD edge is a merged run of collinear unit pieces, so one crease maps
    to every piece along it; flipping any of them is a way to break the
    conflict. Coordinates are exact halves of 1/2N, so the half-grid point
    is `round(x * 2N)` with no epsilon."""
    V = fold["vertices_coords"]
    edges = {tuple(sorted(e)): i for i, e in enumerate(fold["edges_vertices"])}
    out: set = set()
    for k in witness.creases:
        if tuple(sorted(k)) not in edges:
            continue
        a, b = (V[k[0]], V[k[1]])
        pa = (round(a[0] * 2 * N), round(a[1] * 2 * N))
        pb = (round(b[0] * 2 * N), round(b[1] * 2 * N))
        out |= set(_unit_pieces(pa, pb))
    return frozenset(out)
```

- [ ] **Step 4: Run the tests**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_layers.py -v`
Expected: 4 passed. If `test_piece_keys_lands_on_unit_pieces` fails because
`_unit_pieces` returns pieces in a different key order than
`(p.a, p.b)`, normalise with `assign._key(...)` rather than changing
`_unit_pieces`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/layers.py mcp_harness/tests/test_box_pleat_layers.py
git commit -m "$(printf 'box_pleat: layers.py -- a labelling to a layer-order verdict\n\nThe expensive part of layer_order is label-independent, so build it once\nper crease set and re-propagate per candidate. A contradiction returns a\nWitness whose creases are the label decisions it followed from.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 5: Pleat-path variables in `assign`

Today every off-column contour piece takes its label from the elevation
profile and is not a variable. Make each *pleat path* a variable whose first
value is that profile label — so the first candidate is v1's answer, byte for
byte — and whose second value is the flip.

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py:300-325` (the label/domain loop and `var_of`), `:439-465` (`prefer`)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `assign()` unchanged in signature; its output for every subject unchanged.

- [ ] **Step 1: Write the failing tests**

`tests/test_box_pleat_assign.py` imports neither `json`, `os` nor `pytest`
today, and has no path to the corpus. Add at the top of the file, beside the
existing `from fractions import Fraction`:

```python
import json
import os

import pytest

RULE6_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "docs",
                          "superpowers", "evidence",
                          "2026-09-08-vlm-tree-authoring", "data",
                          "rule6_serve.json")
```

Then the two tests:

```python
@pytest.mark.slow
def test_pleat_paths_do_not_change_the_answer():
    """Widening the variable set must not move the first candidate: the
    profile rule stays each path's first value, so v1's assignment is what
    the search reaches first."""
    import json
    from box_pleat.compile import compile_tree
    from box_pleat.emit import to_fold
    for subject in ("starfish", "lizard", "bird"):
        entry = next(e for e in json.load(open(RULE6_PATH))
                     if e["subject"] == subject)
        res = compile_tree(entry["requested"], entry["pairs"])
        assert res.stage_reached == "emit", (subject, res.failure)
        golden = json.load(open(os.path.join(
            os.path.dirname(__file__), "data", f"{subject}-v1.fold")))
        assert to_fold(res.layout, res.assignment) == golden, subject


def test_pleat_path_members_share_one_variable():
    """Two contour pieces meeting where nothing else but the paper edge
    lands are forced equal by Maekawa (|M - V| = 2 over exactly two
    creases), so they must be ONE variable, not two."""
    from box_pleat import assign as A
    tree, lay = _toy_hand_layout()                 # existing helper, :148
    ridges, on_b = _ridges(lay)                    # existing helper, :115
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    got = A.assign(lay, ridges, on_b, cont)
    assert isinstance(got, Assignment), got
    groups = A.pleat_paths(got.pieces, got.labels)
    assert any(len(g) > 1 for g in groups)
    for g in groups:
        assert len({got.labels[i] for i in g}) == 1
```

Before writing them, record the three goldens the first test needs (they are
v1's output, captured *before* this task changes anything):

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python - <<'PY'
import json, os
from box_pleat.compile import compile_tree
from box_pleat.emit import to_fold
E = json.load(open("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))
os.makedirs("tests/data", exist_ok=True)
for e in E:
    if e["subject"] not in ("starfish", "lizard", "bird"): continue
    r = compile_tree(e["requested"], e["pairs"])
    json.dump(to_fold(r.layout, r.assignment),
              open(f"tests/data/{e['subject']}-v1.fold", "w"), indent=1)
    print(e["subject"], "captured")
PY
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_assign.py -k "pleat_path" -v`
Expected: the grouping test FAILS with `AttributeError: module 'box_pleat.assign' has no attribute 'pleat_paths'`; the golden test PASSES (nothing has changed yet). Both must pass at the end.

- [ ] **Step 3: Add `pleat_paths` and widen the variables**

Add at module level in `assign.py`, above `assign`:

```python
def pleat_paths(pieces, labels) -> list:
    """Groups of contour pieces that MUST carry the same label.

    Two folded creases meeting at a vertex where nothing else but the paper
    edge lands are forced equal: Maekawa needs |M - V| = 2 and two creases
    have no mixed solution. Grouping them into one variable is also what
    COrigami §F.2 does ("pleats are grouped into paths of connected
    segments"), and it is why the variable count stays in the hundreds.

    Conservative on purpose: a vertex where a ridge or hinge also lands
    leaves its pieces in separate groups. That costs variables, never
    correctness."""
    inc: dict = {}
    for i, p in enumerate(pieces):
        if p.role not in ("axial", "elev") or labels[i] not in ("M", "V"):
            continue
        inc.setdefault(p.a, []).append(i)
        inc.setdefault(p.b, []).append(i)
    parent = list(range(len(pieces)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        a, b = find(i), find(j)
        if a != b:
            parent[max(a, b)] = min(a, b)

    other: dict = {}
    for i, p in enumerate(pieces):
        if p.role == "B":
            continue
        for v in (p.a, p.b):
            other[v] = other.get(v, 0) + 1
    for v, ids in inc.items():
        if len(ids) == 2 and other.get(v, 0) == 2:
            i, j = ids
            if labels[i] == labels[j]:
                union(i, j)
    groups: dict = {}
    for i in inc:
        groups.setdefault(find(i), []).append(i)
    return [sorted(g) for g in groups.values()]
```

In `assign`, replace the off-column branch:

```python
            else:
                labels[i] = lab
```

with a two-pass structure. First record the profile reading without fixing
the label:

```python
            else:
                pleat_lab[i] = lab
```

declaring `pleat_lab: dict = {}` beside `domain`. Then, after the
`for i, p in enumerate(pieces)` loop that fills `domain`/`labels`, convert
the paths into variables — before the existing `var_of` loop:

```python
    # Pleat paths become variables: the profile reading first (so the first
    # candidate is exactly what v1 emitted), the flip second. They are NOT
    # in `domain`: F is not among their values, because the crease set is
    # fixed (spec §2).
    pleat_pref: dict = {}
    probe = [pleat_lab.get(i) or labels[i] for i in range(len(pieces))]
    for group in pleat_paths(pieces, probe):
        members = [i for i in group if i in pleat_lab]
        if not members:
            continue
        rep = min(members)
        lab = pleat_lab[rep]
        pleat_pref[rep] = [lab, "V" if lab == "M" else "M"]
        for i in members:
            pleat_of[i] = rep
```

declaring `pleat_of: dict = {}` beside `pleat_pref`. Then extend the existing
`var_of` loop so a pleat piece resolves to its path's representative, and a
mirrored path shares one variable with its image:

```python
    var_of: dict = {}
    for i, p in enumerate(pieces):
        if labels[i] is not None:
            continue
        base = pleat_of.get(i, i)
        m = _key((2 * N - p.a[0], p.a[1]), (2 * N - p.b[0], p.b[1]))
        if m in idx and labels[idx[m]] is None:
            mirror = pleat_of.get(idx[m], idx[m])
            var_of[i] = min(base, mirror)
        else:
            var_of[i] = base
```

For a mirrored pair the representative may be the mirror's index, so move the
preference with it:

```python
    for i in list(pleat_pref):
        v = var_of.get(i, i)
        if v != i:
            pleat_pref.setdefault(v, pleat_pref[i])
```

Finally teach `prefer` about them, as its first branch:

```python
        if var in pleat_pref:
            return pleat_pref[var]
```

`can_be_flat` needs no change: a pleat variable is not in `domain` and is not
on the centre column, so it is correctly reported as unable to stay flat.

- [ ] **Step 4: Run the assign suite and the goldens**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_assign.py -v`
Expected: all pass, including both new tests.

Then check the search did not get slower than the plan can afford:

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python - <<'PY'
import json, time
from box_pleat.compile import compile_tree
E = json.load(open("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_serve.json"))
for e in E:
    if e["subject"] not in ("horse", "bird", "octopus"): continue
    t = time.perf_counter(); r = compile_tree(e["requested"], e["pairs"])
    print(f"{e['subject']:9s} {r.stage_reached:7s} assign {r.timings.get('assign', 0):7.2f}s "
          f"total {time.perf_counter()-t:7.2f}s")
PY
```

Expected: every subject still reaches `emit`, and `assign` is within 3x of the
v1 timings recorded in `docs/superpowers/evidence/2026-09-20-box-pleat/results.json`.
If a subject regresses past that, the path grouping is too fine — report the
measurement rather than raising `assign_budget`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py mcp_harness/tests/data
git commit -m "$(printf 'box_pleat: pleat paths become CSP variables\n\nOff-column contour pieces were fixed by the elevation profile. They are now\nvariables, grouped into paths that Maekawa forces to agree, with the\nprofile reading as the first value -- so the first candidate is still\nexactly what v1 emitted (goldens for starfish, lizard, bird).\n\nNothing searches them yet; the global check arrives in the next task.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 6: The `global_check` hook and the no-good store

**Files:**
- Modify: `mcp_harness/box_pleat/assign.py` (`assign` signature and the search loop at `:466-500`)
- Test: `mcp_harness/tests/test_box_pleat_assign.py`

**Interfaces:**
- Produces:
  ```python
  def assign(layout, ridges, boundary_ridges, contours, *, budget=500_000,
             global_check=None, layer_checks=200)
  ```
  `global_check: Callable[[Assignment], tuple[frozenset, object] | None]` —
  `None` accepts the candidate; otherwise `(piece_keys, witness)`, where
  `piece_keys` are the unit-piece keys whose labels the conflict depends on.
  New `AssignFail` kinds: `"layer_unsat"`, `"layer_budget"`, `"layer_unfixable"`.

- [ ] **Step 1: Write the failing tests**

```python
def test_global_check_forces_a_flip():
    """A check that rejects the first candidate and names one pleat piece
    must send the solver to a DIFFERENT labelling, not to failure."""
    from box_pleat import assign as A
    tree, lay = _toy_hand_layout()
    ridges, on_b = _ridges(lay)
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    first = A.assign(lay, ridges, on_b, cont)
    assert isinstance(first, Assignment), first
    seen = []

    def check(cand):
        seen.append(list(cand.labels))
        if len(seen) == 1:
            i = next(i for i, p in enumerate(cand.pieces)
                     if p.role in ("axial", "elev") and cand.labels[i] in ("M", "V"))
            return frozenset([(cand.pieces[i].a, cand.pieces[i].b)]), "forced"
        return None

    got = A.assign(lay, ridges, on_b, cont, global_check=check)
    assert isinstance(got, Assignment), got
    assert len(seen) == 2
    assert got.labels != first.labels


def test_global_check_that_never_accepts_terminates():
    """Rejecting everything must end in a typed failure inside the budget,
    never a hang and never a wrong 'consistent'."""
    from box_pleat import assign as A
    tree, lay = _toy_hand_layout()
    ridges, on_b = _ridges(lay)
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    tried = []

    def check(cand):
        tried.append(1)
        i = next(i for i, p in enumerate(cand.pieces)
                 if p.role in ("axial", "elev") and cand.labels[i] in ("M", "V"))
        return frozenset([(cand.pieces[i].a, cand.pieces[i].b)]), "never"

    got = A.assign(lay, ridges, on_b, cont, global_check=check,
                   layer_checks=8)
    assert isinstance(got, AssignFail)
    assert got.kind in ("layer_unsat", "layer_budget")
    assert len(tried) <= 8


def test_the_loop_never_offers_the_same_candidate_twice():
    """What a sound no-good buys: progress. If the clause did not exclude
    the labelling that produced it, the search would re-offer it forever --
    which is the failure mode COrigami's greedy reassignment has and this
    one must not (spec §7.3, as amended)."""
    from box_pleat import assign as A
    tree, lay = _toy_hand_layout()
    ridges, on_b = _ridges(lay)
    cont = propagate(lay, tree, ridge_points(ridges), on_b)
    seen = []

    def check(cand):
        seen.append(tuple(cand.labels))
        i = next(i for i, p in enumerate(cand.pieces)
                 if p.role in ("axial", "elev") and cand.labels[i] in ("M", "V"))
        return frozenset([(cand.pieces[i].a, cand.pieces[i].b)]), "never"

    A.assign(lay, ridges, on_b, cont, global_check=check, layer_checks=12)
    assert len(seen) == len(set(seen))
```

- [ ] **Step 2: Run to verify they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_assign.py -k global_check -v`
Expected: FAIL with `TypeError: assign() got an unexpected keyword argument 'global_check'`.

- [ ] **Step 3: Restructure the search loop**

Change the signature:

```python
def assign(layout, ridges: list, boundary_ridges: list, contours: dict, *,
           budget: int = 500_000, global_check=None, layer_checks: int = 200):
```

Replace the search loop (from `nodes = budget` to the end of the function)
with this. The inner value loop becomes `retry()` so both the ordinary
backtrack and a rejected leaf can use it:

```python
    # Depth-first search, most-constrained vertex first, on an explicit
    # stack (one frame per assigned variable; a recursive search would
    # exceed the interpreter's frame limit on the larger subjects, spider
    # carries 830 variables). A node is one pick; backtracking within a
    # frame is free, as in the recursive form.
    nodes = budget
    frames: list = []          # [variable, value order, next value index]
    root = None
    nogoods: list = []         # each a {variable: value} that must not all hold
    checks = 0

    def hits_nogood() -> bool:
        return any(all(value.get(var) == val for var, val in g.items())
                   for g in nogoods)

    def retry() -> bool:
        """Advance the deepest frame to its next value, backtracking as far
        as needed. False when the space below the root is exhausted."""
        while True:
            var, vals, i = frames[-1]
            if i < len(vals):
                frames[-1][2] = i + 1
                value[var] = vals[i]
                if (all(feasible(w) for w in touching.get(var, ()))
                        and not hits_nogood()):
                    return True
                del value[var]
            else:
                frames.pop()
                if not frames:
                    return False
                value.pop(frames[-1][0], None)

    def materialise():
        out = list(labels)
        for i in var_of:
            out[i] = value[var_of[i]]
        return Assignment(pieces, out)

    while True:
        nodes -= 1
        if nodes < 0:
            return AssignFail("budget", budget)
        pk = pick()
        if pk is None:
            cand = materialise()
            verdict = global_check(cand) if global_check is not None else None
            if verdict is None:
                return cand
            checks += 1
            keys, witness = verdict
            clause = {var_of[idx[k]]: value[var_of[idx[k]]]
                      for k in keys if k in idx and idx[k] in var_of}
            if not clause:
                # nothing the solver controls can change this verdict
                return AssignFail("layer_unfixable", witness)
            if checks >= layer_checks:
                return AssignFail("layer_budget", witness)
            nogoods.append(clause)
            if not frames or not retry():
                return AssignFail("layer_unsat", witness)
            continue
        if root is None:
            root = pk[0]
        var = pk[1][0]
        frames.append([var, prefer(var), 0])
        if not retry():
            return AssignFail("unsat", root)
    return None                # unreachable; every exit is a return above
```

Delete the old trailing lines that wrote `labels` in place and returned
`Assignment(pieces, labels)` — `materialise()` replaces them, and it must not
mutate `labels`, because a rejected candidate has to leave the fixed labels
untouched for the next one.

- [ ] **Step 4: Run the assign suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_assign.py -v`
Expected: all pass, including both new tests. The Task 5 golden test must
still pass — with `global_check=None` the loop returns the first candidate.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/assign.py mcp_harness/tests/test_box_pleat_assign.py
git commit -m "$(printf 'box_pleat: global_check hook and no-good store in assign\n\nA candidate that satisfies every local condition is offered to an injected\ncheck; a rejection names the piece keys its conflict depends on, which\nbecome a no-good clause over the variables behind them, and the search\ncontinues. COrigami defers a trapped pleat to a greedy retry; the clause\nis the exact form of the same idea.\n\nassign still knows nothing about flat_fold or layer_order.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 7: The `layers` stage in `compile.py`

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py`
- Test: `mcp_harness/tests/test_box_pleat_e2e.py`

**Interfaces:**
- Produces:
  ```python
  STAGES = ("tree", "pack", "skeleton", "contours", "assign", "layers", "emit")

  @dataclass
  class LayerFail:
      kind: str                  # "no_labelling" | "budget" | "unfixable"
      witness: object
      tried: int

  def compile_tree(nodes, pairs, *, max_N=None, pack_budget=200_000,
                   assign_budget=500_000, layer_budget=200) -> Result
  ```
  `Result` gains `layers_tried: int = 0`.

- [ ] **Step 1: Write the failing test**

Add to `mcp_harness/tests/test_box_pleat_e2e.py`:

```python
@pytest.mark.slow
def test_no_subject_emits_with_a_layer_contradiction():
    """The invariant this feature establishes (spec §6). A subject either
    emits with a consistent layer order or refuses at stage `layers`."""
    import flat_fold
    import layer_order
    for subject in ("starfish", "lizard", "frog"):
        res = _compile(subject)
        if res.stage_reached != "emit":
            assert res.stage_reached == "layers", (subject, res.stage_reached)
            assert res.failure.kind in ("no_labelling", "budget", "unfixable")
            continue
        layer_order.layer_order(flat_fold.flat_fold(res.fold))   # must not raise
```

And the regression the spec's §6 requires — the two already-consistent
subjects must come through the new stage untouched. `tests/test_box_pleat_e2e.py`
imports `json` but not `os`, so add `import os` beside it first:

```python
@pytest.mark.slow
@pytest.mark.parametrize("subject", ("starfish", "bird"))
def test_already_consistent_subjects_emit_byte_identical_folds(subject):
    """bird and starfish read `consistent` before this feature existed, so
    the first candidate is accepted and nothing may move (spec §6)."""
    golden = json.load(open(os.path.join(
        os.path.dirname(__file__), "data", f"{subject}-v1.fold")))
    res = _compile(subject)
    assert res.stage_reached == "emit", res.failure
    assert res.fold == golden
    assert res.layers_tried == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_e2e.py::test_no_subject_emits_with_a_layer_contradiction -v`
Expected: FAIL — `lizard` and `frog` reach `emit` and `layer_order` raises
`layer-order contradiction via taco-tortilla ...`.

- [ ] **Step 3: Wire the stage**

In `compile.py`, add the imports and the failure type:

```python
import flat_fold

from . import layers as _layers
from .layers import Witness            # noqa: F401  (re-exported for callers)
```

```python
STAGES = ("tree", "pack", "skeleton", "contours", "assign", "layers", "emit")


@dataclass
class LayerFail:
    """No M/V labelling of this crease set has a consistent layer order.

    `kind` is "no_labelling" when the search exhausted the space, "budget"
    when it ran out of global checks, and "unfixable" when the conflict
    depends on no crease the solver controls. Per the owner's 2026-09-22
    ruling this REFUSES rather than emitting a contradictory base: the
    defect is then in the packing, which is subproject B's input."""
    kind: str
    witness: object
    tried: int
```

Add `layers_tried: int = 0` to `Result`. Then replace the assign call and the
emit stage with:

```python
    res.stage_reached = "assign"
    graphs: dict = {}
    counter = [0]

    def _check(cand):
        """Global flat-foldability of one candidate labelling.

        The graph is cached by CREASE SET: everything layer_order derives
        except the direct facts comes from folded geometry, and the emitted
        topology does not depend on labels either (tests/test_layers_theorem.py),
        so only a different set of folded pieces needs a rebuild. Building
        costs 1.7-2.2 s; re-propagating costs milliseconds."""
        counter[0] += 1
        fold = to_fold(lay, cand)
        ff = flat_fold.flat_fold(fold)
        key = frozenset((p.a, p.b) for p, l in zip(cand.pieces, cand.labels)
                        if l in ("M", "V"))
        graph = graphs.get(key)
        if graph is None:
            graph = graphs[key] = _layers.constraint_graph(ff)
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = _layers.propagate(graph, labels)
        if w is None:
            return None
        return _layers.piece_keys(w, fold), w

    try:
        asg = assign(lay, ridges, boundary, cont, budget=assign_budget,
                     global_check=_check, layer_checks=layer_budget)
    except (ValueError, RuntimeError, KeyError) as exc:
        res.failure = AssignFail("error", repr(exc))
        tick("assign")
        return res
    tick("assign")
    res.layers_tried = counter[0]
    if isinstance(asg, AssignFail):
        # a refusal the global check caused belongs to the layers stage
        if asg.kind in ("layer_unsat", "layer_budget", "layer_unfixable"):
            res.stage_reached = "layers"
            res.failure = LayerFail(
                {"layer_unsat": "no_labelling", "layer_budget": "budget",
                 "layer_unfixable": "unfixable"}[asg.kind],
                asg.site, counter[0])
            return res
        res.failure = asg
        return res
    res.assignment = asg

    res.stage_reached = "emit"
    res.fold = to_fold(lay, asg)
    tick("emit")
    return res
```

Also update the module docstring's list of typed failures to include
`LayerFail`.

- [ ] **Step 4: Run the test and the fast e2e tier**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_e2e.py -v -m "not slow"`
then: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_e2e.py::test_no_subject_emits_with_a_layer_contradiction -v`

Expected: both pass. `starfish` emits (already consistent), and `lizard` and
`frog` either emit with a consistent layer order or stop at `layers`. Either
outcome passes — which one happens is the measurement Task 8 records.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/box_pleat/compile.py mcp_harness/tests/test_box_pleat_e2e.py
git commit -m "$(printf 'box_pleat: the layers stage -- no base emits with a contradiction\n\ncompile_tree injects a global flat-foldability check into assign and caches\nthe layer-order graph by crease set. A crease set with no consistent\nlabelling now REFUSES at stage layers with a typed LayerFail instead of\nemitting a base that cannot be folded.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 8: Measure all 17, and record what moved

**Files:**
- Modify: `mcp_harness/probe_box_pleat.py`, `mcp_harness/tests/test_probe_box_pleat.py`, `mcp_harness/tests/test_box_pleat_e2e.py`
- Modify: `docs/superpowers/evidence/2026-09-20-box-pleat/{README.md,table.md,results.json}`
- Modify: `docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md` (amendments)

**Interfaces:**
- Consumes: everything above.
- Produces: the measured table; the strict expectation table in the e2e suite.

- [ ] **Step 1: Add the probe columns**

In `probe_box_pleat.py`, add `"layers_tried"` to `COLUMNS` after
`"stage_reached"`, and in `row_for`, beside the existing `layer_order`
handling:

```python
    row["layers_tried"] = getattr(res, "layers_tried", 0)
```

The existing `layer_order` column now reads `consistent` for every emitting
subject by construction; leave the code that computes it in place — it is the
independent check that the invariant holds, not a duplicate of it.

- [ ] **Step 2: Update the probe test**

In `tests/test_probe_box_pleat.py`, extend the column assertion to include
`layers_tried`:

```python
    assert "layers_tried" in probe_box_pleat.COLUMNS
```

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_probe_box_pleat.py -v`
Expected: all pass.

- [ ] **Step 3: Measure all 17**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python probe_box_pleat.py \
    --out ../docs/superpowers/evidence/2026-09-20-box-pleat
```

Expected wall clock: longer than the 13m30s of 2026-09-22, because each
subject now pays at least one graph build (1.7-2.2 s) plus its candidates.
If it exceeds 45 minutes, stop it, re-run with `--subjects` in batches, and
report the per-subject `layers_tried` — a subject burning the whole budget is
a finding worth reporting before the rest of the table is filled in.

- [ ] **Step 4: Write the strict expectation table**

In `tests/test_box_pleat_e2e.py`, add the table, filled in from Step 3's
`results.json` — one row per subject, no exceptions:

```python
#: Per-subject layer-order outcome, measured 2026-09-22 after pleat
#: reassignment. Strict: a subject that starts passing XPASSes and fails,
#: which forces this record to be updated rather than silently drifting.
LAYERS_EXPECTED = {
    # "dog": "consistent" | "no_labelling" | "budget" | "unfixable"
}
```

and the test that reads it:

```python
@pytest.mark.slow
@pytest.mark.parametrize("subject", sorted(LAYERS_EXPECTED))
def test_layer_outcome_matches_the_record(subject):
    import flat_fold
    import layer_order
    res = _compile(subject)
    want = LAYERS_EXPECTED[subject]
    if want == "consistent":
        assert res.stage_reached == "emit", res.failure
        layer_order.layer_order(flat_fold.flat_fold(res.fold))
    else:
        assert res.stage_reached == "layers", res.stage_reached
        assert res.failure.kind == want
```

- [ ] **Step 5: Rewrite the evidence README sections**

Update `docs/superpowers/evidence/2026-09-20-box-pleat/README.md`:
- the **Bar** section's counts (emitting subjects may now be fewer than 10);
- the **Coverage** section's closing paragraph, which currently says 8 of 10
  read `contradiction` — replace it with the measured outcome and drop the
  "not part of the bar" caveat, since it now is;
- a new **Layer order** section giving, per subject, `consistent` or the
  `LayerFail` kind with its witness, and `layers_tried`;
- for any subject that stopped emitting, say plainly that the base it used to
  emit could not be folded, and that the refusal localises the defect in the
  packing.

Keep every retraction and citation already in that file intact.

- [ ] **Step 6: Record the four amendments in the spec**

Append to `docs/superpowers/specs/2026-09-22-pleat-reassignment-design.md` a
section `## 10. Execution amendments`, with these four, each in the project's
usual form (what changed, and why the measurement forced it):

1. **The graph is cached by crease set, and `to_fold` does not gain
   `with_index`.** §4.4 proposed an edge-index map to get from a witness back
   to CSP variables. Unnecessary: the merge topology is label-independent
   (Task 1), so a witness maps back through coordinates alone
   (`layers.piece_keys`). Fewer moving parts, and `emit.to_fold` is untouched.
2. **`layer_order._propagate` gained an incremental transitive closure.**
   Not in the design. Measured 2026-09-22: octopus spent 7.98 s of an 8.00 s
   propagate re-enumerating triples, which at 200 candidates is 26 minutes for
   one subject. Transitivity cannot be skipped instead — without it octopus
   and frog read `consistent`, i.e. it is load-bearing for detection.
   Accepted consequence: which of several contradictions is reported may
   change; whether one exists may not.
3. **The hook returns `(piece_keys, witness)`, not a raw `Witness`.** Keeps
   `assign.py` free of any knowledge of FOLD vertex numbering, so the CSP
   stays a geometry-only module.
4. **Spec §7.3's hand-built five-face fixture was replaced.** Authoring a
   strip with a genuine taco-tortilla and a hand-derived dependency set
   would mean inventing coordinates the plan could not verify. What the
   fixture was for — that a no-good is sound and non-vacuous — is covered
   instead by three checks that can be stated exactly: the dependencies are
   a subset of the direct slots and non-empty (Task 3), propagation is
   deterministic (Task 3), and the search never offers the same candidate
   twice, which is what a vacuous clause would break (Task 6).
5. **`assign` gained `layer_checks` and three new `AssignFail` kinds**
   (`layer_unsat`, `layer_budget`, `layer_unfixable`), which `compile.py`
   translates into `LayerFail`. The CSP reports what it saw; naming the stage
   is the compiler's job.

- [ ] **Step 7: Run the whole box-pleat suite**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_box_pleat_*.py tests/test_layers_theorem.py tests/test_layer_order.py tests/test_probe_box_pleat.py -v`
Expected: green, with the strict table's rows either passing or XPASSing. An
XPASS means a subject moved: update `LAYERS_EXPECTED` and say so in the commit.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/probe_box_pleat.py mcp_harness/tests docs/superpowers
git commit -m "$(printf 'box_pleat: measure pleat reassignment across the 17\n\nProbe gains layers_tried; the e2e suite gains the strict per-subject\nlayer-order table; the evidence README reports what moved, including any\nsubject that stopped emitting -- a refusal is a finding, not a regression:\nit localises the defect in the packing rather than the labelling.\n\nSpec §10 records the four execution amendments.\n\nCo-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Amendment 2026-09-22 (controller, during Task 2): adapt `mv_symmetrize._LayerGate`

CLAUDE.md §0 requires prior art to be surveyed before planning. The survey
behind this plan looked outward (COrigami, Justin/Hull, MILP) and **missed
that this repository already contains the mechanism Tasks 4 and 7 specify**,
shipped on the TreeMaker path. Tasks 4 and 7 are re-scoped to adapt it.

`mcp_harness/mv_symmetrize.py:531-601`, `_LayerGate` — "`layer_order` re-run
over a relabel, without rebuilding the geometry":

1. Its docstring states this design's enabling theorem, and states it more
   completely than the spec's §3 did: `pairs`, `covers`, `equalities` **and**
   `tacos` are all functions of the folded geometry, "so the only
   assignment-dependent field in `_Constraints` is the boolean seed of each
   `direct` constraint, and one flipped crease flips exactly one seed."
   Both "M" and "V" land in `creases`, so the creases/tortillas split cannot
   move either. `mv_symmetrize.py:78-83` repeats it as a theorem about the
   folded base.
2. `__init__` builds the geometry-derived constraints once; `consistent(flips)`
   rebuilds **only** the `direct` tuple and re-propagates. That is exactly the
   cache Task 7 describes, already written.
3. It carries a **drift guard** the plan lacked and which is better than
   anything in it: it re-derives the seed↔edge correspondence independently and
   `assert`s it equals the shipped `_build_constraints` output on the unflipped
   fold — "if layer_order's direct-seed rule ever changes, this raises instead
   of quietly ordering the wrong stack." **`box_pleat/layers.py` must carry an
   equivalent assertion.**

**What is genuinely new, and is all that Task 4 should build:** `_LayerGate`
flips by FOLD *edge index* and answers `bool`. Box-pleating needs (a) the
mapping from unit pleat pieces to FOLD edges, because merged runs mean the two
are not one-to-one (Task 4's `piece_keys`); (b) a structured `Witness` carrying
creases and faces, so Task 6 can learn a no-good instead of only backtracking;
(c) Task 3's dependency tracking. Build those *around* `_LayerGate`'s shape —
same one-time build, same re-seed-only-`direct` step, same drift assertion —
rather than as a second implementation of it. Reuse the class directly if it
factors cleanly; otherwise state in the task report why it did not.

**Simplification this licenses in Task 7.** The plan caches the graph keyed by
`frozenset((p.a, p.b) for p, l in ... if l in ("M", "V"))`. Under this plan's
own Global Constraints the crease set never changes and F stays F, and Task 1
proved the emitted topology is label-independent — so that key is constant
across every candidate for a subject. Build the graph **once per subject** and
drop the key, unless the implementer finds a path that does change the crease
set, in which case keep the key and say what that path is.

**Verified by the controller, 2026-09-22, before Task 4 was dispatched.**
`mv_symmetrize._LayerGate` accepts a box-pleat `to_fold(...)` dict with **no
adaptation at all**:

| subject | build | `consistent(())` | expected | propagate |
|---|---|---|---|---|
| starfish | 0.06 s | `True` | consistent | 0.002 s |
| lizard | 0.03 s | `False` | contradiction | 0.001 s |

Both match the known baseline, the drift-guard `assert` passes on both, and
`_seeds` has 27 entries on lizard — the same count as the M/V edges the Task 1
gate measured. So the geometry build, the seed derivation and the drift guard
are reusable as they stand.

**The one place reuse stops.** `consistent()` catches `ValueError` and returns
`bool`, discarding the provenance Task 6 needs to learn a no-good. So Task 4
should use `_LayerGate.__init__` for the build, seed derivation and drift
assertion, then call Task 3's `propagate(cons, deps=True)` itself over a
re-seeded `direct` tuple, instead of calling `consistent()`. Note that
`_seeds` entries are `(lit, val, edge_index)`, so the FOLD edge index that
`piece_keys` must map unit pieces onto is already exposed.

### Amendment note for Task 3: dedupe with `_LayerGate` is optional, and has a trap

Task 3's `_polys_of` is the same loop `mv_symmetrize._LayerGate.__init__`
open-codes (`mv_symmetrize.py:556-566`), and Task 3's `constraints_for` is the
same `_cells` + `_build_constraints` pair that follows it. Deduplicating is
allowed but **not required**, and if you do it, preserve this difference:

| | non-convex face |
|---|---|
| `_polys_of` (Task 3) | **raises** `ValueError("face i is non-convex; ...")` |
| `_LayerGate.__init__` | **soft-fails**: sets `self.unavailable = f"face {i} is non-convex"` and returns; `consistent()` then answers `False` |

`_LayerGate` is on the **shipped serve path**. Converting its soft skip into a
raise would turn a gate answering "no" into a crash, so a dedupe must wrap the
call in `try/except ValueError` and set `unavailable` from the message. If that
looks at all delicate, leave `_LayerGate` alone — the duplication is nine lines
and the risk is a serve-path regression. Either way, do not change
`_LayerGate`'s observable behaviour, and say in the task report which you chose.

### Amendment correction for Task 4: what the drift guard should actually assert

The `_LayerGate` amendment above said `box_pleat/layers.py` "must carry an
equivalent assertion" to `_LayerGate`'s drift guard. That instruction, taken
literally, would produce an assertion that **cannot fail**. Corrected here
before Task 4 is dispatched.

`_LayerGate` needs its guard because it **re-derives** the seed↔edge
correspondence itself and then asserts the re-derivation equals
`_build_constraints`' output — two derivations, so drift is possible. Task 3
removed that situation: `slots` is built **inside `_build_constraints`**
(`layer_order.py:578`), in the same loop over shared edges that builds `direct`
(`:545`), and `constraints_for` returns `cons.slots` (`:881`). One source, so
`slots[i]` and `direct[i]` correspond by construction and an assertion that
they do is vacuous.

**The duplication that does exist, and is what Task 4 must guard.** Task 4's
`propagate` recomputes each seed's boolean from the slot:

```python
(labels[s.edge] == "V") == (s.sign == 1)
```

and `_build_constraints` computes the same boolean independently as
`(a == "V") == (orient[fa] == 1)`. Those are two copies of one rule. So the
assertion worth writing is a **round-trip**: rebuilding `direct` from `slots`
under the folded state's *own* labels must reproduce `cons.direct` exactly,
element for element. That fires if either formula changes, if `sign` stops
meaning `orient[fa]`, or if the slot ordering stops matching `direct`'s — the
real failure modes. Put it in the Task 1-style characterization test or as a
one-time check in `constraint_graph`, not inside the per-candidate hot path.

Task 4's own `constraint_graph` needs no other change: it already delegates to
`layer_order.constraints_for` rather than reimplementing `_LayerGate`'s build,
so the re-scoping amendment's remaining substance is (a) this round-trip guard
and (b) leaving `_LayerGate` itself untouched, which Task 3 did.

### Task 3 review findings that bear on Task 6 (recorded, deliberately NOT acted on)

Task 3's review verified `deps` is **sound** — ~19,000 relabellings that agree
with a reported `deps` all still contradicted, zero counterexamples, across all
8 contradicting subjects and all three raise sites. It also found `deps`
**over-approximates**, and the reason is a loose statement in this plan.

The soundness argument is that M/V labels enter the system at exactly one place,
the `direct` seeds, because every other family is a function of the folded
geometry and `flat_fold` is label-blind. That argument is correct — and it
implies the *converse* too: a geometry-derived constraint carries **no label
dependency of its own**. But the brief has taco-tortilla carry `creases=(k,)`
and taco-taco carry `creases=(k1, k2)`, and every raise site unions
`prov.creases`. Those entries are in the no-good without being label
dependencies. Measured: horse's witness is `taco-tortilla crease (64, 65)
through face 49` and `(64, 65)` is one of its 5 `deps` entries.

**Left as-is on purpose.** Over-approximation only makes the clause weaker — it
can never make it unsound — and the failure direction here is asymmetric: an
unsound no-good silently prunes valid labellings, which no test in this plan
would catch, while a weak one merely costs search steps. Tightening it is a
change whose *downside* is the dangerous one, so it does not belong in a task
that cannot measure the benefit.

**Task 6 should treat it as the first lever if the search is too slow.**
Dropping `prov.creases` from the `equalities` and `tacos` families (keeping it
on `direct`) tightens every clause, and Task 6 is the first task that can
measure whether that buys anything, because it is the first with a search to
count steps in. If Task 6 does tighten it, the required evidence is the same
relabelling check the reviewer ran — agree-on-`deps` relabellings must still
contradict — not just a step count.

**A latent test fragility this also explains.** Task 3's
`assert exc.value.deps <= {s.edge for s in slots}` holds on all 8 subjects
(measured: zero creases lack a slot) but is not structurally guaranteed: a
creased shared edge whose two faces do not overlap gets no `DirectSlot`
(`layer_order.py:544` gates on `pairs`) yet still contributes `creases=(k,)`
through `_spanning` and taco-taco. Tightening as above would make that
assertion true by construction rather than by luck of the corpus.

### Measured 2026-09-23 (Task 7): the no-good clause covers half the CSP

The Task 3 review found the witness dependency set sound but loose, and this
plan deferred tightening to "Task 6's first lever if the search is too slow",
noting that the benefit could not be measured until a search existed. Task 7
produced the number, on `lizard`'s v1 labelling:

| quantity | value |
|---|---|
| FOLD edges in the witness | 12 |
| unit pieces those resolve to | 238 |
| **solver variables in the clause** | **125 of 249 (50.2%)** |

**Read the direction correctly: a bigger clause is a WEAKER one.** A no-good
says "not (v₁=a₁ ∧ … ∧ v_k=a_k)", so a larger k excludes *fewer* labellings —
only those agreeing on all 125 variables. At half the CSP the clause is nearly
as specific as the candidate that produced it, so it forbids little beyond
that one leaf.

**So convergence is currently coming mostly from ordinary DFS backtracking, not
from learning.** Measured tries to reach a consistent labelling: `lizard` 9,
`horse` 5, `frog` 22. That the loop works at all with clauses this weak is the
good news; it also means the learning has not been tested at the scale where it
matters. The subjects to watch are `spider` (~400 s to assign) and `dog`
(~150 s), where a weak clause multiplies an already expensive search.

**This raises the value of the deferred tightening and does not change its
risk.** Dropping `prov.creases` from the `equalities` and `tacos` families
(keeping it on `direct`) should cut k substantially, because those families
contribute creases that are not label dependencies at all. The evidence any
such change owes is unchanged and non-negotiable: every relabelling that agrees
with a reported `deps` must still contradict, the check the Task 3 review ran
over ~19,000 trials. Report k before and after alongside the try counts, so the
claim is about pruning power and not just about a smaller number.

### Measured 2026-09-23 (Task 7 review): `layer_budget=200` is not a safe default

Plan risk #1 was "search blow-up on dog and spider". It is real, it has been
measured, and the shape is worse than a per-check cost.

**The per-check cost is not the problem.** With the graph cached, one check
costs `starfish` 3.9 ms, `lizard` 2.1 ms, `horse` 304 ms — and of horse's 304 ms,
295 ms is `propagate`, so `to_fold` + `flat_fold` is 3% and hoisting them out of
the loop (sound under Task 1's theorem) would buy nothing. The one-time graph
build is `lizard` 27 ms, `horse` 1.85 s.

**The cost is the CSP re-descent per rejection, and it grows.** `hits_nogood()`
is evaluated on every value attempt inside `retry()`, against an accumulating
store of clauses that each cover 125 of 249 variables (measured above). So each
extra candidate costs roughly a whole fresh descent:

| subject | first descent (no hook) | with the hook | tries | per extra try |
|---|---|---|---|---|
| `lizard` | 0.62 s | 6.84 s (11.0×) | 9 | ≈0.78 s = **1.25× the first descent** |
| `horse` | 1.59 s | 11.17 s (7.0×) | 5 | ≈2.4 s = **1.5× the first descent** |

Forcing rejections on `lizard` shows the marginal cost rising: 1 rejection
0.63 s, 5 → 2.91 s, 10 → 8.75 s (≈1.17 s each over that span), then
`layer_unsat` at 11.

**Extrapolated, the default is unusable on the two largest subjects.** At a
~400 s first descent, `spider` costs ≈500-600 s per extra try, so
`layer_budget=200` is a **≈30-hour** worst case; `dog` at ~150 s is ≈8 hours.
Ten tries on `spider` is already ~1.5 h. **`assign_budget=500_000` does not bind
this**: `lizard` exhausts its whole reachable space in 11 candidates, a few
thousand nodes, so the node budget permits hours of wall time on a large
subject. `layer_budget × re-descent` is the only bound that exists.

**Observed directly:** a full `tests/test_box_pleat_e2e.py` run reached 14 of
its tests in 44 minutes and was still inside `spider` when it was stopped.

**Two levers, and they are the same lever.** Tightening the dependency set
(recorded above as the deferred option) both prunes more *and* makes
`hits_nogood()` cheaper, because clause length falls. That is now the primary
performance lever, with two independent reasons rather than one. The
alternative — watched-variable indexing so a clause is tested only when its last
variable binds — is a second, orthogonal option and is standard practice in SAT
solvers; it is new design work and belongs in its own spec.

**What must NOT happen:** lowering the default budget so the suite passes.
A `budget` refusal is an honest typed outcome and is already distinct from
`no_labelling` in the kind taxonomy, so a subject that cannot be resolved within
a practical budget should be *reported* as a budget refusal with its measured
cost — not hidden by a number chosen to make a table look better. The default
must be set from the per-subject measurement, and the measurement reported
beside it.

---

## Execution amendment index (for Task 8)

Task 8's brief says to record "these four" execution amendments. That list was
written before execution. The real set is larger, and the spec's `§10` is
already taken by the non-confluence ruling, so Task 8 must record **these**,
under a new heading, rather than the four the brief predicted.

**Rulings that changed what the code does or claims:**

1. **`layer_order._propagate` is NOT confluent** — spec `§10` (`da927ca`). The
   premise Task 2 was planned on is false; the task stands with a better
   justification and a weaker claim ("no contradiction found", not
   flat-foldable). Measured by permuting the old loop's own iteration order.
2. **Two witnesses moved, and a commit message overclaims** — spec `§10`
   correction (`74e0141`). All 10 verdicts held; `lizard` and `octopus`
   witnesses changed. A second corpus instance of the order-dependence.
   Consequence for Task 8: **pin verdicts, never witness strings.**
3. **Tasks 4 and 7 re-scoped onto `mv_symmetrize._LayerGate`** (`87e5c6e`,
   verified `a96282f`) — the mechanism was already in this repo; the §0
   prior-art pass had looked only outward. Includes the `_polys_of`
   soft-fail-vs-raise trap (`959f570`) and the corrected drift-guard
   instruction (`7128a1a`), which as first written would have been vacuous.
4. **`piece_keys` lost its `N` parameter** (`045ec35`) — a caller-supplied `N`
   silently returned wrong-but-plausible piece keys. Four stale 3-arg call
   sites in this plan were corrected.
5. **`constraints_for` gained the `closure.bad_edges` guard** (`c7befc1`) —
   `layer_order()` and `_LayerGate` both had it; the new public entry point,
   which Task 4 calls, did not.
6. **Task 5's two-phase `pick()`** — unrequested, and approved after a review
   proved it necessary (starfish diverges without it) and non-blocking.
7. **Three bugs in this plan's own verbatim code** (Task 5) and **one
   regression caused by it** (Task 6's `materialise()` dropped Task 5's
   `unbound_variable` guard). Notably the F-routing bug would have violated
   "F stays F" — the toy emitted 0 F pieces instead of 60.

**Measurements that should appear in the evidence, not just the spec:**

8. **The no-good clause covers 125 of 249 variables** (`1d30200`) — and a
   bigger clause is a *weaker* one, so convergence is DFS backtracking rather
   than learning.
9. **`layer_budget=200` is a ≈30-hour worst case on `spider`** (`bd45d1b`) —
   each rejection costs a whole fresh CSP re-descent (1.25-1.5×). This is plan
   risk #1, measured. **Task 8 must therefore bound its own run and report
   `budget` refusals with their measured cost, not raise the budget until the
   table looks better.**
10. **Tightening the dependency set is the primary performance lever**, with
    two independent reasons (prunes more, costs less to test). Deferred
    deliberately: the tightening's failure direction is the unsound one.

### Correction 2026-09-23: the "1.25-1.5× first descent" cost model is pessimistic at the large end

The cost note above extrapolated from `lizard` and `horse`, where an extra
candidate cost 1.25-1.5× the first descent, and predicted ≈8 h for `dog` at
`layer_budget=200`. Measured on `dog` itself: **10 candidates, 565 s total
(contended), ≈57 s per try against a ~150 s first descent — 0.38×, not 1.25×.**
So 200 tries on `dog` is ≈3 h rather than 8 h.

The model overestimates because the per-candidate re-descent is not a *full*
descent: `retry()` pops back only as far as a clause variable, so on a subject
whose pleat variables sit late in the search order the re-descent explores a
small suffix rather than the whole tree. `lizard` and `horse` are small enough
that the suffix is most of the tree; `dog` is not. **Do not extrapolate this
cost from small subjects** — the ratio falls as the subject grows, which is the
opposite of the direction the first two data points suggested.

The conclusion the note drew still stands, for a different reason: ≈3 h is
still unusable in a suite, and the bound is still `layer_budget × re-descent`
with nothing else binding it.

**And the try counts turn out not to need a large budget at all.** Every subject
that resolves does so in **1, 1, 2, 5, 9, 10, 20 or 22** candidates — the
maximum is 22, an order of magnitude below the default. So `layer_budget=200`
never binds a solvable subject; it only sets how long the search grinds before
giving up on an unsolvable one. That reframes the default: it is a give-up
threshold, not a search-capacity knob, and the argument for lowering it is that
a smaller one reaches the same answers sooner — not that it makes a table
prettier.

### Measured 2026-09-23: `rabbit` is unresolved, and `assign_budget` DOES bind

`rabbit` is the one subject that does not resolve. Two runs:

| `layer_budget` | stage | `layers_tried` | secs | failure |
|---:|---|---:|---:|---|
| 25 | `layers` | 25 | 447 | `LayerFail(budget)` |
| 100 | `assign` | **56** | 1765 | **`AssignFail(budget)`** |

At `layer_budget=100` the search never reaches 100 candidates: it exhausts
`assign_budget=500_000` **search nodes** after 56 of them. So the Task 7
review's statement that "`assign_budget=500_000` does **not** bind this" is
**subject-dependent and false for `rabbit`** — the node budget binds first. It
was measured on `lizard`, which exhausts its whole reachable space in 11
candidates; that does not generalise.

**This is a fourth outcome the plan never enumerated**, and it is the one that
makes `Result.layers_tried` load-bearing rather than merely informative. Without
it the row reads as an ordinary local-CSP node exhaustion; with `layers_tried =
56` a reader can see that the CEGAR re-descents consumed the nodes. Task 6's
review insisted the field be set on every exit path, including the exception
path, and this is the row that needed it.

**What `rabbit` does and does not establish.** It establishes that no consistent
labelling is reachable within 500,000 search nodes and 56 candidates, at ~29
minutes. It does **not** establish that none exists: only a `layer_unsat` — the
search space genuinely exhausted, which `lizard` reaches at 11 candidates —
would do that, and `rabbit` never gets there. So `rabbit` must be reported as a
**budget** refusal with its measured cost, and must NOT be described as a
subject whose crease set admits no consistent labelling. That distinction is the
whole reason the kind taxonomy separates `budget` from `no_labelling`, and it
decides where the follow-up work goes: a genuine emptiness would localise the
defect in the packing and hand subproject B a site, whereas a budget refusal
points at this search's own weakness — for which the measured cause is already
recorded above (a no-good clause covering half the CSP prunes almost nothing).

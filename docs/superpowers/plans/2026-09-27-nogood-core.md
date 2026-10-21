# No-good Core Measurement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure how small the *actual cause* of a CEGAR rejection is, against today's median clause of 109 solver variables, without changing the CEGAR loop.

**Architecture:** One inert production change — `layers.propagate(graph, labels, *, only=None)` — supplies the oracle "do these creases alone force the contradiction?". A diagnostic script then runs QuickXplain over each rejection's blamed crease set and reports core sizes in creases and in solver variables.

**Tech Stack:** Python 3.14, pytest 9. No new dependencies.

Spec: `docs/superpowers/specs/2026-09-27-nogood-core-design.md`.

## Global Constraints

- **Run every command from this worktree.** Do NOT `cd` to the original repository root.
- **Use `../.venv/bin/python3` from `mcp_harness`.** Bare `python3` lacks `skeletor`, which `tests/conftest.py` imports, and dies at collection.
- **That venv has no `pytest-timeout`. NEVER pass `--timeout`.**
- **NEVER run `pytest tests/`** — 5,167 tests, over 3 hours. Always name files.
- **Never use bare `git stash` / `git stash pop`.** The stash stack is shared with the main checkout and other worktrees. Use a temporary WIP commit instead.
- **End every commit message with:** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Do NOT modify `layer_order.py`.** Untouched across this whole line of work; `mv_symmetrize` on the serve path shares it.
- **Do NOT wire core extraction into `assign`'s CEGAR loop.** That is the gated follow-on, explicitly out of scope (spec §11).
- **`grep -c box_pleat mcp_harness/server.py` must stay 0.**
- **`only=None` must be behaviourally identical to today.** No emitted fold may change.
- **Every count assertion is paired with a non-vacuity assertion or a fixture guard.**
- **A core is TESTED, never assumed.** A too-small clause is unsound: it forbids assignments that are not contradictory, prunes valid labellings, and can make the search report unsat when a solution exists.
- **Report the verdict in whichever direction the data falls.** Spec §8: a core of 50+ variables closes the lever as a negative and must NOT be answered by searching for a better heuristic.

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/layers.py` (modify) | `_seeded` and `propagate` gain `only=`; the oracle primitive. |
| `mcp_harness/tests/test_box_pleat_layers.py` (modify) | `only=` inertness in both directions. |
| `docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py` (new) | QuickXplain, its self-check, the `var_of` patch, the breadth+depth sampling, the JSON. |
| `docs/superpowers/evidence/2026-09-27-nogood-core/README.md` (new) | The tables and the verdict against spec §8's bar. |

---

### Task 1: `layers.propagate(..., only=)` — the oracle primitive

**Files:**
- Modify: `mcp_harness/box_pleat/layers.py` (`_seeded` at line 124, `propagate` at line 138)
- Test: `mcp_harness/tests/test_box_pleat_layers.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `layers.propagate(graph: LayerGraph, labels: dict, *, only=None) -> Witness | None` and `layers._seeded(graph, labels, only=None)`. `only=None` seeds every slot (today's behaviour); a `frozenset` of edge keys seeds only those, leaving every other slot unconstrained.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_box_pleat_layers.py`. The file already has
`_folded(subject)` returning `(res, fold, ff)` and `_labels(ff)`; reuse both.

```python
def test_only_everything_equals_the_default():
    """`only` naming every slot must be indistinguishable from omitting it.
    This is the inertness half: no existing caller passes `only`, so if this
    ever differed, the layers stage would have changed silently."""
    _, _, ff = _folded("lizard")
    graph, labels = layers.constraint_graph(ff), _labels(ff)
    every = frozenset(s.edge for s in graph.slots)
    assert len(every) > 100            # non-vacuity: lizard carries 745 slots
    assert layers.propagate(graph, labels) == layers.propagate(
        graph, labels, only=every)


def test_only_a_strict_subset_can_change_the_verdict():
    """The other half: a parameter tested only in its no-op direction is
    untested. `lizard`'s sparse labelling contradicts; seeding NOTHING cannot
    contradict, because an unseeded system has no crease-derived constraint to
    violate. If this ever passed with `only=frozenset()` still contradicting,
    the contradiction would not be coming from the labelling at all and the
    whole core measurement would be meaningless."""
    _, _, ff = _folded("lizard")
    graph, labels = layers.constraint_graph(ff), _labels(ff)
    assert layers.propagate(graph, labels) is not None    # non-vacuity
    assert layers.propagate(graph, labels, only=frozenset()) is None


def test_only_ignores_keys_that_are_not_slots():
    """A caller may hand a superset (e.g. every crease it blamed, some of which
    are not slots). Extra keys must be harmless, not a KeyError, so the oracle
    never fails for a reason unrelated to the core it is testing."""
    _, _, ff = _folded("lizard")
    graph, labels = layers.constraint_graph(ff), _labels(ff)
    every = frozenset(s.edge for s in graph.slots)
    bogus = every | {((-99, -99), (-98, -98))}
    assert layers.propagate(graph, labels, only=bogus) == layers.propagate(
        graph, labels)
```

Note: `test_the_layers_stage_repairs_v1s_lizard_without_moving_a_crease`
(line 78) already establishes that `lizard`'s **sparse v1** labelling
contradicts while its repaired one does not. If `_folded("lizard")` returns a
labelling that does NOT contradict, the second and third tests above have no
contradiction to work with — in that case use the same `v1` fixture that test
uses, and say so in a comment. Do not weaken the assertions.

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_layers.py -q \
  -k "only_everything or only_a_strict_subset or only_ignores_keys"
```

Expected: all three FAIL with `TypeError: propagate() got an unexpected keyword argument 'only'`.

- [ ] **Step 3: Add the parameter**

In `mcp_harness/box_pleat/layers.py`, replace:

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
```

with:

```python
def _seeded(graph: LayerGraph, labels: dict, only=None):
    """`graph.cons` with `direct` seeded from `labels`.

    The ONLY place the seeding happens: both `propagate` (the per-candidate
    filter) and `certify` (once, on the accepted candidate) go through it,
    so the two tiers cannot end up judging different constraint sets.

    `only`, when not `None`, is a set of edge keys: ONLY those slots are
    seeded and every other slot is left unconstrained. `None` seeds every
    slot, which is the behaviour every existing caller gets. Extra keys in
    `only` that are not slot edges are ignored, so a caller may pass a
    superset (spec `2026-09-27-nogood-core-design.md` §4.1: the core
    oracle's candidate set comes from a witness, whose creases are not
    guaranteed to all be slots).
    """
    slots = (graph.slots if only is None
             else tuple(s for s in graph.slots if s.edge in only))
    direct = tuple(
        (s.lit, _seed(s, labels[s.edge]),
         layer_order.Prov(f"crease {s.edge} {labels[s.edge]}",
                          creases=(s.edge,), faces=s.faces))
        for s in slots)
    return dataclasses.replace(graph.cons, direct=direct)
```

and replace `propagate`'s signature and its `_seeded` call:

```python
def propagate(graph: LayerGraph, labels: dict) -> Witness | None:
```
```python
        layer_order.propagate(_seeded(graph, labels), deps=True)
```

with:

```python
def propagate(graph: LayerGraph, labels: dict, *, only=None) -> Witness | None:
```
```python
        layer_order.propagate(_seeded(graph, labels, only), deps=True)
```

Add to `propagate`'s docstring, after the existing `labels` line:

```python
    `only`, when not `None`, seeds ONLY those edge keys, so a contradiction
    it reports is forced by THOSE creases alone. This is the minimal-core
    oracle of spec `2026-09-27-nogood-core-design.md` §4. `None` -- the
    default, and what every production call site passes -- seeds every slot
    and is the pre-existing behaviour exactly.
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_layers.py -q \
  -k "only_everything or only_a_strict_subset or only_ignores_keys"
```

Expected: 3 passed.

- [ ] **Step 5: Confirm nothing else moved**

`test_box_pleat_layers.py` in full takes ~17 minutes (two tests compile dense
subjects). Run it, plus the other box-pleat suites:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -m pytest \
  tests/test_box_pleat_layers.py tests/test_box_pleat_assign.py \
  tests/test_box_pleat_interleave.py tests/test_box_pleat_pleat_filter.py -q
```

Expected: all pass. **If any fails, do NOT commit** — report it verbatim, and do
not call it unrelated without showing why from the code.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/box_pleat/layers.py mcp_harness/tests/test_box_pleat_layers.py
git commit -m "$(printf '%s\n' 'box_pleat: layers.propagate(only=) -- the minimal-core oracle' '' 'propagate could not take a partial labelling: _seeded iterates EVERY slot and' 'reads labels[s.edge], so a missing key was a KeyError and its docstring stated' 'that contract. `only` filters the SLOTS instead, leaving unnamed ones' 'unconstrained, so a contradiction reported under `only=S` is forced by S alone.' '' 'only=None is the default and every production call site keeps it, so behaviour' 'is unchanged. Tested in BOTH directions -- naming every slot equals the default,' 'and naming none removes the contradiction -- because a parameter tested only in' 'its no-op direction is untested. Extra non-slot keys are ignored on purpose:' 'the oracles candidate set comes from a witness, whose creases are not' 'guaranteed to all be slots.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 2: the measurement script

**Files:**
- Create: `docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py`

**Interfaces:**
- Consumes: `layers.propagate(graph, labels, *, only=None)` (Task 1).
- Produces: `core-sizes.json` — a list of per-rejection rows.

**Why the QuickXplain implementation lives in the evidence script and not in
production, with no pytest file of its own:** this slice is a measurement and
must not touch the CEGAR loop (spec §11), and the project's other diagnostics
(`../2026-09-26-gap1-phase0/phase0.py`,
`../2026-09-26-nogood-indexing/where_the_time_goes.py`) are unit-test-free by the
same convention. The mitigation is that the script **self-tests the algorithm on
a synthetic monotone oracle and refuses to run if it fails** — Step 1's
`_self_test`. Do not skip it or reduce it to a smoke check.

- [ ] **Step 1: Write the script**

Create `docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py`:

```python
"""How small is the ACTUAL cause of a CEGAR rejection?

Spec: `../../specs/2026-09-27-nogood-core-design.md`.

The clause `assign` learns is a median of 109 solver variables and prunes almost
nothing. But every measured contradiction is a `taco_tortilla` among exactly
THREE faces, while the recorded cause is a median of 172 FOLD edges, because
`witness.creases` comes from `layer_order`'s `exc.deps` -- the whole derivation
chain, a dependency CONE rather than a CUT. This script measures the gap.

THE ORACLE. `layers.propagate(graph, labels, only=S)` contradicts iff the creases
in S, at this candidate's own labels, are ALONE sufficient. Monotone in S:
seeding more slots only adds constraints, and a contradictory system stays
contradictory under added constraints. Monotonicity is QuickXplain's
precondition, so it is VERIFIED on every rejection (`_checks`), not trusted.

SOUNDNESS. Every candidate core is tested, so a too-small core cannot be
produced. That matters more than size: a clause that is too small forbids
assignments that are not contradictory, prunes valid labellings, and can make the
search report unsat when a solution exists.

SAMPLING is breadth AND depth, because `lizard` misleads in both directions: its
`propagate` costs 1.07s against 0.004-0.014s on the other five subjects, so a
lizard-only cost figure overstates extraction ~100x -- yet lizard is the only
subject whose CEGAR loop yields many rejections cheaply.
  * breadth: one rejection on each labelling-capable subject, from
    `assign(global_check=None)` (no CEGAR loop needed).
  * depth: `DEPTH` rejections on lizard.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py \\
      ../docs/superpowers/evidence/2026-09-27-nogood-core/core-sizes.json [depth]
"""
import collections
import difflib
import importlib.util
import json
import os
import pathlib
import statistics
import sys
import time

import flat_fold

from box_pleat import emit
from box_pleat import layers as L
from box_pleat.compile import compile_tree

OUT = sys.argv[1]
DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 25
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
BREADTH = ["starfish", "lizard", "frog", "horse", "bird", "guinea_pig"]
ASSIGN_SRC = pathlib.Path("box_pleat/assign.py")

_ORIG = """    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_PATCHED = """    _PROBE["var_of"] = dict(var_of)
    _PROBE["idx"] = dict(idx)
    nodes = budget
    frames: list = []          # [variable, value order, next value index]
"""
_FOOTER = "\n\n_PROBE = {}\n"


def build_instrumented():
    """Patch `assign.py` in memory to expose `var_of` and `idx`; verify; import.

    `var_of` and `idx` are locals inside `assign`, and the clause's VARIABLE
    count -- the headline of this measurement -- cannot be computed without them.
    Patched in memory rather than forked: a committed copy would drift silently.
    Loaded under a dotted name so `assign.py`'s relative imports resolve, and
    appended rather than prepended because `assign.py` opens with
    `from __future__ import annotations`.
    """
    src = ASSIGN_SRC.read_text()
    if src.count(_ORIG) != 1:
        raise SystemExit("REFUSING TO MEASURE: assign.py's DFS setup no longer "
                         "matches this script's anchor text exactly once. "
                         "Re-derive the patch against today's source.")
    patched = src.replace(_ORIG, _PATCHED) + _FOOTER
    removed = [l[1:] for l in difflib.unified_diff(
        src.splitlines(), patched.splitlines(), lineterm="", n=0)
        if l.startswith("-") and not l.startswith("---")]
    if removed:
        raise SystemExit(f"REFUSING TO MEASURE: patch removed lines: {removed}")
    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_assign_core.py"
    out.write_text(patched)
    import box_pleat  # noqa: F401 - must be in sys.modules for relative imports
    name = "box_pleat._assign_core"
    spec = importlib.util.spec_from_file_location(name, out)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# QuickXplain (Junker, AAAI 2004; formal treatment arXiv:2001.01835)
# --------------------------------------------------------------------------
def quickxplain(candidates, holds, counter):
    """An IRREDUCIBLE subset of `candidates` for which `holds` is still true.

    `holds(frozenset)` must be MONOTONE: true for a set implies true for every
    superset. `counter` is a one-element list incremented per oracle call.

    Irreducible, not globally minimum: a smallest core is NP-hard and is not
    attempted, matching the greedy-vs-minimum ruling already taken for
    `interleave`'s odd-cycle release.

    Candidates are consumed in the DETERMINISTIC order given. QuickXplain's
    result depends on how it splits, so an unordered input would return a
    different irreducible core run to run and make every reported figure
    unreproducible. Which core is found is not canonical; finding the same one
    again must be.
    """
    def oracle(s):
        counter[0] += 1
        return holds(s)

    def qx(background, cand):
        if oracle(background):
            return frozenset()
        if len(cand) == 1:
            return frozenset(cand)
        k = len(cand) // 2
        c1, c2 = cand[:k], cand[k:]
        d1 = qx(background | set(c1), c2)
        d2 = qx(background | d1, c1)
        return d1 | d2

    return qx(frozenset(), list(candidates))


def _self_test():
    """Refuse to measure unless QuickXplain is demonstrably correct here.

    The algorithm is the measurement, so a wrong implementation would not fail
    loudly -- it would return plausible small cores. Two properties: it finds
    the exact cause on a synthetic monotone oracle, and it reports the oracle
    calls it actually made.
    """
    cause = {2, 4}
    calls = [0]
    got = quickxplain(sorted([1, 2, 3, 4, 5, 6, 7, 8]),
                      lambda s: cause <= set(s), calls)
    if got != frozenset(cause):
        raise SystemExit(f"REFUSING TO MEASURE: quickxplain self-test returned "
                         f"{sorted(got)}, expected {sorted(cause)}")
    if calls[0] < 3:
        raise SystemExit(f"REFUSING TO MEASURE: quickxplain self-test made only "
                         f"{calls[0]} oracle calls -- it cannot have searched")
    print(f"quickxplain self-test OK ({calls[0]} oracle calls for a "
          f"2-of-8 cause)", flush=True)


def _checks(graph, labels, blamed, core):
    """Spec §4.2's monotonicity checks, on this rejection. All three must hold.

    Returned as a dict so a FAILURE is recorded in the artifact rather than
    crashing the run -- a violated check invalidates that row, not the corpus.
    """
    full = L.propagate(graph, labels, only=blamed) is not None
    empty = L.propagate(graph, labels, only=frozenset()) is not None
    if core:
        extra = next((c for c in sorted(blamed) if c not in core), None)
        superset = (L.propagate(graph, labels,
                                only=core | {extra}) is not None
                    if extra is not None else True)
    else:
        superset = None
    return {"full_blamed_contradicts": full,
            "empty_contradicts": empty,
            "core_plus_one_contradicts": superset,
            "all_ok": bool(full) and not empty and superset is not False}


def measure_rejection(row, graph, labels, blamed, fold, var_of, idx):
    """Extract a core for one rejection and fill `row`."""
    slot_edges = frozenset(s.edge for s in graph.slots)
    # Spec §4.1: every blamed crease must be a slot edge. A crease silently
    # dropped here would make the core look smaller than it is.
    row["blamed_not_slots"] = len(blamed - slot_edges)
    t0 = time.time()
    calls = [0]
    core = quickxplain(
        sorted(blamed),
        lambda s: L.propagate(graph, labels, only=frozenset(s)) is not None,
        calls)
    row["extract_secs"] = round(time.time() - t0, 2)
    row["oracle_calls"] = calls[0]
    row["blamed_creases"] = len(blamed)
    row["core_creases"] = len(core)

    # variable-level sizes, using assign's OWN clause expression so the two
    # cannot disagree about what a clause's variable set is
    def variables(creases):
        keys = L.piece_keys(
            L.Witness(kind="probe", creases=frozenset(creases),
                      faces=(), prov="probe"), fold)
        return {var_of[idx[k]] for k in keys if k in idx and idx[k] in var_of}

    row["blamed_variables"] = len(variables(blamed))
    row["core_variables"] = len(variables(core))
    row["checks"] = _checks(graph, labels, blamed, core)
    return core


def main():
    _self_test()
    entries = {e["subject"]: e for e in json.load(open(RULE6))}
    A = build_instrumented()
    rows = []

    def flush():
        json.dump(rows, open(OUT, "w"), indent=1)

    # ---- BREADTH: one rejection per subject --------------------------------
    for s in BREADTH:
        row = {"subject": s, "sample": "breadth"}
        res = compile_tree(entries[s]["requested"], entries[s]["pairs"])
        if res.stage_reached != "emit":
            row["error"] = f"sparse compile stopped@{res.stage_reached}"
            rows.append(row); flush(); print(f"{s}: SPARSE STOP", flush=True)
            continue
        A._PROBE.clear()
        asg = A.assign(res.layout, res.ridges, res.boundary_ridges,
                       res.contours, dense=True, global_check=None)
        if isinstance(asg, A.AssignFail):
            row["error"] = f"dense assign failed: {asg!r}"
            rows.append(row); flush(); print(f"{s}: DENSE FAIL", flush=True)
            continue
        var_of, idx = A._PROBE["var_of"], A._PROBE["idx"]
        fold = emit.to_fold(res.layout, asg)
        ff = flat_fold.flat_fold(fold)
        graph = L.constraint_graph(ff)
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = L.propagate(graph, labels)
        if w is None:
            row["note"] = "first dense candidate did not contradict"
            rows.append(row); flush(); print(f"{s}: NO CONTRADICTION", flush=True)
            continue
        row["witness_kind"] = w.kind
        row["witness_faces"] = len(w.faces)
        measure_rejection(row, graph, labels, w.creases, fold, var_of, idx)
        rows.append(row); flush()
        print(f"{s:11} blamed {row['blamed_creases']:4}cr/"
              f"{row['blamed_variables']:4}var -> CORE "
              f"{row['core_creases']:3}cr/{row['core_variables']:3}var "
              f"({row['oracle_calls']} calls, {row['extract_secs']}s) "
              f"checks_ok={row['checks']['all_ok']}", flush=True)

    # ---- DEPTH: many rejections on lizard ---------------------------------
    res = compile_tree(entries["lizard"]["requested"], entries["lizard"]["pairs"])
    cell = {}
    seen = [0]

    class Stop(Exception):
        pass

    def spy(cand):
        if seen[0] >= DEPTH:
            raise Stop()
        fold = emit.to_fold(res.layout, cand)
        ff = flat_fold.flat_fold(fold)
        if "graph" not in cell:
            cell["graph"] = L.constraint_graph(ff)
        labels = {k: a for _, _, k, a in ff.shared_edges if a in ("M", "V")}
        w = L.propagate(cell["graph"], labels)
        if w is None:
            return None
        seen[0] += 1
        row = {"subject": "lizard", "sample": "depth",
               "witness_kind": w.kind, "witness_faces": len(w.faces)}
        measure_rejection(row, cell["graph"], labels, w.creases, fold,
                          A._PROBE["var_of"], A._PROBE["idx"])
        rows.append(row); flush()
        print(f"  lizard#{seen[0]:<3} blamed {row['blamed_creases']:4}cr/"
              f"{row['blamed_variables']:4}var -> CORE "
              f"{row['core_creases']:3}cr/{row['core_variables']:3}var "
              f"({row['oracle_calls']} calls, {row['extract_secs']}s) "
              f"checks_ok={row['checks']['all_ok']}", flush=True)
        return L.piece_keys(w, fold), w

    A._PROBE.clear()
    try:
        A.assign(res.layout, res.ridges, res.boundary_ridges, res.contours,
                 dense=True, global_check=spy, layer_checks=100000,
                 budget=5_000_000)
    except Stop:
        pass

    # ---- refuse to report a vacuous run ----------------------------------
    good = [r for r in rows if "core_variables" in r]
    if not good:
        flush()
        raise SystemExit("VACUOUS RUN: no rejection produced a core. Reporting "
                         "cores of size 0 here would look like success.")
    bad = [r for r in good if not r["checks"]["all_ok"]]
    cv = [r["core_variables"] for r in good]
    bv = [r["blamed_variables"] for r in good]
    print()
    print(f"rejections measured: {len(good)}  monotonicity FAILURES: {len(bad)}")
    print(f"blamed variables : median {statistics.median(bv)}  max {max(bv)}")
    print(f"CORE   variables : median {statistics.median(cv)}  max {max(cv)}")
    print(f"tightening ratio : {statistics.median(bv) / max(statistics.median(cv), 1):.1f}x")
    flush()


main()
```

- [ ] **Step 2: Verify the self-test and the oracle fire, on the cheapest subject only**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py \
    /tmp/core-smoke.json 2 2>&1 | head -30
```

Expected: `quickxplain self-test OK (N oracle calls for a 2-of-8 cause)`, then a
`starfish` row with `checks_ok=True` and a `core_variables` smaller than
`blamed_variables`.

**If `checks_ok=False` on any row, STOP and report it.** A failed monotonicity
check means the oracle does not reproduce the rejection it came from, and every
core size in the run is meaningless.

**If `core_variables == blamed_variables` on every row**, that is a real result,
not a bug — report it and continue; spec §8 covers that outcome.

- [ ] **Step 3: Commit the script**

```bash
git add docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py
git commit -m "$(printf '%s\n' 'evidence: QuickXplain core extraction over the no-good clause' '' 'Measures how small the ACTUAL cause of a rejection is. Every contradiction is' 'a taco_tortilla among exactly 3 faces while the recorded cause is a median 172' 'FOLD edges, because witness.creases is layer_orders exc.deps -- a dependency' 'CONE, not a cut. This measures the gap.' '' 'Oracle is layers.propagate(only=S): the creases in S alone force the' 'contradiction. Monotone, so QuickXplains precondition holds -- and it is' 'VERIFIED per rejection, not trusted. Every candidate core is tested, so a' 'too-small (unsound) core cannot be produced.' '' 'The script SELF-TESTS QuickXplain on a synthetic monotone oracle and refuses to' 'run if it fails: the algorithm IS the measurement, so a wrong implementation' 'would return plausible small cores rather than failing loudly. It also refuses' 'to report a run where no rejection produced a core, which would show cores of' 'size 0 and look like success.' '' 'Sampling is breadth AND depth: lizards propagate is 1.07s vs 0.004-0.014s' 'elsewhere, so a lizard-only cost figure overstates extraction ~100x, yet lizard' 'is the only subject whose loop yields many rejections cheaply.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

### Task 3: run it, and write the verdict

**Files:**
- Create: `docs/superpowers/evidence/2026-09-27-nogood-core/core-sizes.json`
- Create: `docs/superpowers/evidence/2026-09-27-nogood-core/README.md`

**Interfaces:**
- Consumes: `core_measure.py` (Task 2).
- Produces: the evidence directory.

- [ ] **Step 1: Run the full measurement**

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-nogood-core/core_measure.py \
    ../docs/superpowers/evidence/2026-09-27-nogood-core/core-sizes.json 25
```

Expect roughly 30–60 minutes: `guinea_pig`'s sparse compile alone is ~347 s and
its dense assign ~116 s, and `lizard`'s 25 rejections each carry ~20 oracle
calls at ~1.07 s.

- [ ] **Step 2: Write the README**

Create `docs/superpowers/evidence/2026-09-27-nogood-core/README.md` containing:

- **The headline first**, and in whichever direction the data falls: the median
  core size in **solver variables** against the pre-core median, and the verdict
  against spec §8's bar — `<=10` justifies a follow-on, `10-50` is ambiguous and
  needs the convergence effect rather than the size, `50+` closes the lever.
- **The per-subject breadth table**: blamed creases/variables, core
  creases/variables, oracle calls, extraction seconds.
- **The `lizard` depth distribution**: median and max of each of those.
- **The monotonicity checks**, with the count of failures (which must be 0 for
  any figure to be quoted).
- **The cost reading, separated from the size reading**: oracle calls is the
  portable number; seconds is `lizard`-inflated, and the breadth rows are what
  show the real cost on a normal subject.
- **What it does NOT establish**, stated plainly: a small core implies stronger
  pruning per rejection, NOT convergence. The large-budget run showed the
  contradiction space is vast, and this file must not be cited as evidence about
  convergence.
- **If the verdict is `50+`:** say the lever is closed, and say explicitly that
  the outcome must not be answered by hunting a better heuristic. Four levers in
  this line of work have been examined and two died; recording a fifth is the
  deliverable.

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/evidence/2026-09-27-nogood-core/
git commit -m "$(printf '%s\n' 'evidence: how small the no-good clause actual cause is' '' 'QuickXplain cores over real rejections, breadth (one per subject) and depth (25' 'on lizard), with the monotonicity checks and the verdict against the bar the' 'spec set BEFORE the data arrived.' '' 'Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>')"
```

---

## Plan Self-Review

**Spec coverage.** §1 motivation → Task 2's docstring. §2 prior art → Task 2's
QuickXplain citation. §3 the `only=` change → Task 1. §4.1 oracle + the
slot-edge assertion → Task 2 (`blamed_not_slots`). §4.2 monotonicity → Task 2
(`_checks`). §4.3 soundness → structural, by testing every core. §5 extraction +
determinism → Task 2 (`sorted(blamed)`, documented). §6 sampling → Task 2's
breadth/depth blocks. §7 reporting incl. how `var_of` is obtained → Task 2
(`build_instrumented`, `variables()`). §8 the bar → Task 3 Step 2. §9 testing →
Task 1 Steps 1–5, plus Task 2's self-test and vacuity refusal. §10 risks → Task 3
Step 2's "does NOT establish" and cost-separation bullets. §11 out of scope →
Global Constraints. §12 evidence → Task 3.

**Placeholder scan.** None. Task 3 Step 2 describes README *content* rather than
supplying prose, which is correct: the text depends on numbers that do not exist
until Step 1 runs, and the bullets fix what must be said in either direction.

**Type consistency.** `only=` is the keyword in Task 1 and used as `only=` in
Task 2. `quickxplain(candidates, holds, counter) -> frozenset` is defined and
called consistently. `L.Witness(kind=, creases=, faces=, prov=)` matches
`layers.Witness`'s four fields. `_checks` returns the dict whose `all_ok` key
Tasks 2 and 3 both read.

**One risk the plan carries deliberately:** Task 2 constructs a synthetic
`L.Witness` purely to reuse `piece_keys` for the crease→variable mapping. That is
a slightly unusual use of a production dataclass, and it is preferable to
re-implementing the expansion — but a reviewer should check that `piece_keys`
reads only `witness.creases` (it does, at `layers.py:198`) so the empty `faces`
and placeholder `prov` cannot matter.

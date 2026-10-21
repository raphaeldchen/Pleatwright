# Witness / Core Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record the identity of every dense CEGAR rejection — complete candidate, contradiction, core, signed core, piece keys — and replay core-in-loop arm B to decide whether its three rejections were three different facts or one fact three times.

**Architecture:** One new keyword-only diagnostic parameter on `compile_tree` (`debug_witness_cores`), appended to inside the existing `core_extraction` branch of `_check` from locals already in scope. One evidence script that replays arm B, applies a pre-registered reproduction guard, and only then claims a verdict row. No production behaviour changes; with the parameter `None` the compile is byte-for-byte what it is today.

**Tech Stack:** Python 3.14, pytest 9.1.1, the existing `mcp_harness/box_pleat/` package. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-09-28-witness-identity-design.md`. Every section reference below (`§4`, `§6.2`, …) is to that file.

## Global Constraints

* **Python is `../.venv/bin/python3`, run from `mcp_harness`.** `mcp_harness/conftest.py`'s autouse fixture imports `mesh_to_tree`, which gates ALL collection on skeletor/trimesh/networkx/numpy. Bare `python3` fails at collection.
* **Never pass `--timeout`.** That venv has no `pytest-timeout`.
* **Never run `pytest tests/`** — 5,167 tests, >3 hours. Always name files.
* **Run the FULL named test files, never a `-k` filtered subset.**
* **Do NOT modify `layer_order.py`** — `mv_symmetrize` on the serve path shares it.
* **Do NOT modify `assign.py`, `layers.py`, `cores.py`, or the serve path.** `grep -c box_pleat mcp_harness/server.py` must stay 0.
* **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with the main checkout and other worktrees. Use a temporary WIP commit.
* **Commit messages end with** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
* **The five level names are exactly** `candidate`, `witness`, `core`, `signed`, `keys` — in that order, spelled that way, in the record dict, the script, and the tests.
* **Arm B's guard values are exactly** 3 rejections; `debug_cores` rows `(44, 8, 31)`, `(361, 5, 47)`, `(65, 8, 43)` in that order (4th field free); failure repr `AssignFail(kind='budget', site=500000)`; clause min/median/max `(5, 8, 8)`. Source: `docs/superpowers/evidence/2026-09-27-core-in-loop/ab.json`.
* **Never use tardigrade / water bear as a test subject** — OWNER INSTRUCTION.

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/box_pleat/compile.py` (modify) | the `debug_witness_cores` parameter, its docstring paragraph, and the five-field append in `_check` |
| `mcp_harness/tests/test_box_pleat_witness_identity.py` (create) | §7's four tests, all on the sparse `lizard` fixture — no dense run |
| `docs/superpowers/evidence/2026-09-28-witness-identity/identity.py` (create) | the replay, the §6.2 guard, the §6.3 verdict, JSON serialisation, and a `--selftest` mode |
| `docs/superpowers/evidence/2026-09-28-witness-identity/identity.json` (generated) | the full per-rejection records |
| `docs/superpowers/evidence/2026-09-28-witness-identity/README.md` (create) | §9's required statements |

Three tasks. Task 1 is the instrumentation and is reviewable on its own; Task 2 is the script and its self-test, which must pass before any 16-minute run is spent; Task 3 spends it and writes the verdict.

---

### Task 1: The `debug_witness_cores` parameter

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py` (signature ~`:119-125`, docstring ~`:153-158`, `_check` ~`:344-373`)
- Test: `mcp_harness/tests/test_box_pleat_witness_identity.py` (create)

**Interfaces:**
- Consumes: `compile_tree`'s existing `core_extraction`, `debug_cores`, `debug_clause_sizes` parameters; `layers.Witness` (a frozen, hashable dataclass); `layers.piece_keys`.
- Produces: `compile_tree(..., debug_witness_cores=<list>)`, which appends one dict per extraction rejection with exactly the keys `"candidate"`, `"witness"`, `"core"`, `"signed"`, `"keys"`. `"witness"` is the `layers.Witness` object; the other four are `frozenset`s. Task 2 consumes this list.

**Context you need:** `_check` is a closure inside `compile_tree`, handed to `assign` as its `global_check`. It returns `None` to accept a candidate, or `(piece_keys, witness)` to reject it. The `core_extraction=True` branch already computes `core` and appends to `debug_cores`; everything the new record needs (`labels`, `w`, `core`, `fold`) is already a local there. This task adds no computation to the un-instrumented path.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_witness_identity.py`:

```python
"""compile_tree(debug_witness_cores=...): the identity of each rejection.

Spec: `docs/superpowers/specs/2026-09-28-witness-identity-design.md` section 7.

Sparse `lizard` only -- it rejects 8 times in ~6.5 s. The dense 500,000-node
replay this instrumentation exists for takes ~16 minutes and is the job of
`docs/superpowers/evidence/2026-09-28-witness-identity/identity.py`, never of
this suite.
"""
import json

from box_pleat.compile import compile_tree
from test_box_pleat_tree import RULE6

LEVELS = ("candidate", "witness", "core", "signed", "keys")


def _entry(subject):
    with open(RULE6) as fh:
        return next(e for e in json.load(fh) if e["subject"] == subject)


def _run(**kw):
    e = _entry("lizard")
    return compile_tree(e["requested"], e["pairs"], **kw)


def test_one_record_per_rejection_carrying_the_five_levels():
    rows: list = []
    seen: list = []
    res = _run(core_extraction=True, debug_cores=seen,
               debug_witness_cores=rows)
    assert res.stage_reached == "emit", res.failure
    assert rows, "extraction never ran -- lizard stopped rejecting?"
    assert len(rows) == len(seen), (len(rows), len(seen))
    for r in rows:
        assert set(r) == set(LEVELS), sorted(r)


def test_the_levels_agree_with_each_other_and_with_debug_cores():
    """The chain candidate -> witness -> core -> signed -> keys must be
    internally consistent, and must describe the SAME rejection `debug_cores`
    describes. This is also what pins section 4's claim that `labels[c]`
    cannot KeyError: it exercises the lookup on every core crease rather
    than asserting it in a comment.
    """
    rows: list = []
    seen: list = []
    res = _run(core_extraction=True, debug_cores=seen,
               debug_witness_cores=rows)
    assert res.stage_reached == "emit", res.failure
    assert rows, "extraction never ran"
    for r, (blamed, core_n, _calls, _secs) in zip(rows, seen):
        assert {c for c, _ in r["signed"]} == r["core"]
        assert all(a in ("M", "V") for _, a in r["signed"])
        assert r["core"] <= r["witness"].creases
        assert len(r["core"]) == core_n, (len(r["core"]), core_n)
        assert len(r["witness"].creases) == blamed
        assert r["keys"], "piece keys came back empty"
        assert r["candidate"], "the candidate labelling came back empty"
        assert all(a in ("M", "V") for _, a in r["candidate"])


def test_none_does_not_perturb_the_run():
    """Section 6.2's reproduction guard in miniature. `debug_cores`' 4th field
    is wall clock and is excluded: comparing it would make this test flaky for
    a reason that has nothing to do with the instrumentation.
    """
    off_seen: list = []
    off_clauses: list = []
    off = _run(core_extraction=True, debug_cores=off_seen,
               debug_clause_sizes=off_clauses, debug_witness_cores=None)
    on_seen: list = []
    on_clauses: list = []
    rows: list = []
    on = _run(core_extraction=True, debug_cores=on_seen,
              debug_clause_sizes=on_clauses, debug_witness_cores=rows)
    assert off.stage_reached == on.stage_reached
    assert repr(off.failure) == repr(on.failure)
    assert off.layers_tried == on.layers_tried
    assert off.fold == on.fold
    assert [t[:3] for t in off_seen] == [t[:3] for t in on_seen]
    assert off_clauses == on_clauses
    assert len(rows) == len(on_seen)


def test_stays_empty_when_extraction_is_off():
    """The flag gates the work, not just the reporting: with
    `core_extraction=False` there is no core to identify, so the list must
    stay empty even though rejections happened.
    """
    rows: list = []
    clauses: list = []
    res = _run(debug_clause_sizes=clauses, debug_witness_cores=rows)
    assert res.stage_reached == "emit", res.failure
    assert clauses, "nothing was rejected -- test is vacuous"
    assert rows == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_identity.py -q`

Expected: FAIL — `TypeError: compile_tree() got an unexpected keyword argument 'debug_witness_cores'` on all four.

- [ ] **Step 3: Add the parameter to the signature**

In `mcp_harness/box_pleat/compile.py`, change:

```python
                 debug_cores: list | None = None,
                 debug_clause_sizes: list | None = None) -> Result:
```

to:

```python
                 debug_cores: list | None = None,
                 debug_clause_sizes: list | None = None,
                 debug_witness_cores: list | None = None) -> Result:
```

- [ ] **Step 4: Add the docstring paragraph**

In the same function's docstring, immediately after the existing paragraph that ends `Both are diagnostics; production callers leave them \`None\`.`, insert:

```
    `debug_witness_cores`, when not `None`, gets one dict appended per
    extraction rejection -- the same population `debug_cores` records --
    carrying the IDENTITY of that rejection rather than its sizes:
    `{"candidate": frozenset(labels.items()), "witness": the Witness object,
    "core": the crease frozenset, "signed": frozenset((crease, label)),
    "keys": the piece keys handed to assign}`. Spec
    `2026-09-28-witness-identity-design.md` section 4. The five levels are a
    chain, each strictly downstream of the last, and a repeat is only
    meaningful relative to the level above it -- which is why all five are
    recorded rather than just the core. It stays empty when
    `core_extraction` is `False`, because the core is the thing being
    identified and there is none.
```

- [ ] **Step 5: Record the identity in `_check`**

In `_check`'s `core_extraction` branch, the function currently ends with the
~20-line comment block on the narrowed-keys/original-witness asymmetry,
followed by:

```python
        return _layers.piece_keys(replace(w, creases=core), fold), w
```

**Keep that comment block exactly as it is** — it documents the
`layer_unfixable`/`layer_bad_witness` reasoning that no other file records.
Replace only the `return` line above with:

```python
        keys = _layers.piece_keys(replace(w, creases=core), fold)
        if debug_witness_cores is not None:
            debug_witness_cores.append({
                "candidate": frozenset(labels.items()),
                "witness": w,
                "core": core,
                # `labels[c]` cannot KeyError: `core` is a subset of
                # `w.creases`, which `layers.propagate` fills from
                # `exc.deps` -- the SEEDED slot edges -- and `_seeded`
                # seeds only keys present in `labels`.
                "signed": frozenset((c, labels[c]) for c in core),
                "keys": keys,
            })
        return keys, w
```

`keys` is lifted into a local so the recorded frozenset is **the object the
loop actually uses**, not a recomputation that could diverge from it. No new
imports: `replace` and `time` are already imported in this module.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_identity.py -q`

Expected: `4 passed`. Runtime ~30 s (four sparse `lizard` compiles at ~6.5 s each).

- [ ] **Step 7: Run the neighbouring suites for regressions**

Run:

```bash
PYTHONPATH=. ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_identity.py tests/test_box_pleat_cores.py tests/test_box_pleat_core_in_loop.py tests/test_box_pleat_assign.py -q
```

Expected: all pass. The pre-existing baseline for the last three files is 62 passed together with `tests/test_box_pleat_pleat_filter.py`; here the three named files plus the four new tests must all pass with no failures.

- [ ] **Step 8: Verify the serve path is untouched**

Run: `grep -c box_pleat server.py`

Expected: `0`.

- [ ] **Step 9: Commit**

```bash
git add box_pleat/compile.py tests/test_box_pleat_witness_identity.py
git commit -m "box_pleat: record the IDENTITY of each dense rejection, not just its size

Spec 2026-09-28-witness-identity-design.md section 4. One keyword-only
diagnostic parameter, appended to from locals already in scope inside the
existing core_extraction branch. With it None the compile is byte-for-byte
what it was.

Five levels, not one: the core-in-loop A/B measured clause SIZE (202 -> 8)
and never measured what the clause stops the search redoing. A repeat is
only meaningful relative to the level above it, so the record carries the
whole chain -- complete candidate, witness, core, signed core, piece keys.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: The replay script, its guard, and its self-test

**Files:**
- Create: `docs/superpowers/evidence/2026-09-28-witness-identity/identity.py`

**Interfaces:**
- Consumes: `compile_tree(..., debug_witness_cores=<list>)` from Task 1; `box_pleat.cores.CoreExtractionError`.
- Produces: `identity.py` with pure functions `repeats(rows, level)`, `distinct(rows)`, `verdict(rows)`, `guard(rejections, core_rows, failure, clauses)`, and `serialise(value)`; a `--selftest` mode; and a default mode that writes `identity.json`. Task 3 runs both modes.

**Context you need:** this mirrors `docs/superpowers/evidence/2026-09-27-core-in-loop/ab.py`, which is the house pattern for an evidence script: module docstring carrying the reasoning and the run command, the pre-registered bar encoded as code rather than prose, JSON flushed so a partial run still leaves a record. Two differences: there is only **one** arm (extraction-off rejections have no core to identify), and the verdict logic is factored into pure functions with a `--selftest` mode, because project memory records two throwaway probes that drove wrong conclusions — one of which *printed its verdict unconditionally*.

- [ ] **Step 1: Write the script**

Create `docs/superpowers/evidence/2026-09-28-witness-identity/identity.py`:

```python
"""Were arm B's three rejections three different facts, or one fact three times?

Spec: `../../specs/2026-09-28-witness-identity-design.md`.

A replay of core-in-loop arm B -- dense `lizard`, 500,000-node budget,
`core_extraction=True` -- with ONE thing added: `debug_witness_cores`, which
records the identity of each rejection rather than its size. There is no second
arm: an extraction-off rejection has no core to identify, and arm A's 113
rejections are not the population in question.

WHY IDENTITY AND NOT COUNTS. The A/B settled that the clause narrows (median 202
-> 8 solver variables, 25.2x) and that extraction is not the cost (21.7 s of
954.9 s, 2.27%). It left the terminal outcome unmoved and the rejection count
113 -> 3, which is consistent with two OPPOSITE stories: stronger clauses
excluding more of the space a priori, or a search spending its budget
re-deriving ground it has already forbidden. Every instrument the A/B carried is
aggregate. The distinction is about identity.

WHAT A REPEAT MEANS, PER LEVEL (spec section 5). `candidate` repeating is a
decisive enforcement defect -- nothing may propose a labelling it has already
refuted. `signed` repeating means the loop re-derived a no-good it already
holds: sound but wasted, and the expected signature of `assign.hits_nogood`
pruning only on FULL binding. `keys` repeating means two crease-level no-goods
collapsed to one solver-variable set, so part of the narrowing cannot reach the
clause. `witness` or `core` repeating alone is NEITHER -- one taco_tortilla
among three faces arises under many labellings, and the same crease set under
different labels is a different no-good -- so those two are reported and carry
no verdict.

WHAT THIS CANNOT SAY. Not the clause itself. The clause is `{var: value}` and
`_check` sees neither `var_of` nor `value`; `keys` is the clause's INPUT. So a
`keys` repeat is suggestive and a `signed` repeat is strong, but neither PROVES
a duplicate clause. That needs a `debug_clauses` list in `assign.py`, out of
scope and gated on this run showing a repeat worth chasing.

n = 3, AND THE TEST IS ASYMMETRIC. One repeat is decisive -- a single
recurrence cannot be a statistical artifact. Three distinct is WEAK: consistent
with new territory each time and equally consistent with a loop that would
start repeating at rejection 20. The NEW TERRITORY row must be read as "no
recurrence in the only three rejections this budget produced", never as "the
loop does not re-derive".

THE GUARD COMES FIRST. Arm A reproduced the committed baseline on every
STRUCTURAL figure while differing 1.26x on wall clock, so this loop is
deterministic in structure and not in timing. The replay must therefore
reproduce arm B's structure exactly; if it does not, the instrumentation changed
the run and NO verdict row may be claimed in either direction. Wall clock is
deliberately not guarded.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py \\
      --selftest
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py \\
      ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.json
"""
import dataclasses
import json
import os
import statistics
import sys
import time

from box_pleat import cores
from box_pleat.compile import compile_tree

RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
BUDGET = 500_000

LEVELS = ("candidate", "witness", "core", "signed", "keys")
# Only these three carry a verdict, in this order (spec section 6.3). A repeat
# at `witness` or `core` alone is reported and changes nothing.
VERDICT_LEVELS = ("candidate", "signed", "keys")
_VERDICT = {
    "candidate": "ENFORCEMENT DEFECT",
    "signed": "LATE ENFORCEMENT",
    "keys": "GRANULARITY CEILING",
}

# Spec section 6.2, from ../2026-09-27-core-in-loop/ab.json. The `debug_cores`
# 4th field (seconds) is deliberately absent: it is wall clock.
ARM_B = {
    "rejections": 3,
    "core_rows": ((44, 8, 31), (361, 5, 47), (65, 8, 43)),
    "failure": "AssignFail(kind='budget', site=500000)",
    "clause_min_median_max": (5, 8, 8),
    "source": "../2026-09-27-core-in-loop/ab.json",
}


def repeats(rows, level):
    """{value: [row index, ...]} for every value of `level` seen more than once."""
    where: dict = {}
    for i, r in enumerate(rows):
        where.setdefault(r[level], []).append(i)
    return {v: idx for v, idx in where.items() if len(idx) > 1}


def distinct(rows):
    """{level: how many distinct values} across all five levels."""
    return {lv: len({r[lv] for r in rows}) for lv in LEVELS}


def verdict(rows):
    """Spec section 6.3, evaluated in order; the first matching row wins.

    Returns `(verdict, level)` -- `level` is the one that repeated, or `None`
    for NEW TERRITORY.
    """
    for lv in VERDICT_LEVELS:
        if repeats(rows, lv):
            return _VERDICT[lv], lv
    return "NEW TERRITORY", None


def guard(rejections, core_rows, failure, clauses):
    """Spec section 6.2. Returns `(passed, [mismatch, ...])`.

    `core_rows` is compared IN ORDER and on its first three fields only: the
    loop is deterministic in structure, so a reordering is a divergence, and
    the 4th field is wall clock, which arm A showed drifts 1.26x on an
    unchanged code path.
    """
    bad = []
    if rejections != ARM_B["rejections"]:
        bad.append(f"rejections {rejections} != {ARM_B['rejections']}")
    got = tuple(tuple(r[:3]) for r in core_rows)
    if got != ARM_B["core_rows"]:
        bad.append(f"core rows {got} != {ARM_B['core_rows']}")
    if failure != ARM_B["failure"]:
        bad.append(f"failure {failure!r} != {ARM_B['failure']!r}")
    trip = ((min(clauses), statistics.median(clauses), max(clauses))
            if clauses else None)
    if trip != ARM_B["clause_min_median_max"]:
        bad.append(f"clause min/median/max {trip} != "
                   f"{ARM_B['clause_min_median_max']}")
    return not bad, bad


def serialise(value):
    """frozensets -> sorted lists, tuples -> lists, dataclasses -> dicts.

    Sorting is what makes the artifact diffable: a frozenset's iteration order
    is not stable across runs, so an unsorted dump would differ run to run for
    reasons that are not findings.
    """
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {k: serialise(v)
                for k, v in dataclasses.asdict(value).items()}
    if isinstance(value, frozenset):
        return sorted(serialise(v) for v in value)
    if isinstance(value, tuple):
        return [serialise(v) for v in value]
    if isinstance(value, dict):
        return {str(k): serialise(v) for k, v in value.items()}
    return value


def _selftest():
    """The guard and the bar, exercised on synthetic rows.

    Project memory: "two throwaway probes drove wrong conclusions in one
    session; one printed its verdict unconditionally". This runs in
    milliseconds and must pass before the 16-minute replay is spent.
    """
    def row(cand, wit, core, signed, keys):
        return {"candidate": cand, "witness": wit, "core": core,
                "signed": signed, "keys": keys}

    a = row("c1", "w1", "k1", "s1", "p1")
    b = row("c2", "w2", "k2", "s2", "p2")
    c = row("c3", "w3", "k3", "s3", "p3")

    # --- the bar, all four rows -------------------------------------------
    assert verdict([a, b, c]) == ("NEW TERRITORY", None)
    assert verdict([a, b, dict(c, candidate="c1")]) == (
        "ENFORCEMENT DEFECT", "candidate")
    assert verdict([a, b, dict(c, signed="s1")]) == (
        "LATE ENFORCEMENT", "signed")
    assert verdict([a, b, dict(c, keys="p1")]) == (
        "GRANULARITY CEILING", "keys")

    # --- precedence: candidate wins over signed, signed over keys ---------
    both = dict(c, candidate="c1", signed="s1", keys="p1")
    assert verdict([a, b, both]) == ("ENFORCEMENT DEFECT", "candidate")
    assert verdict([a, b, dict(c, signed="s1", keys="p1")]) == (
        "LATE ENFORCEMENT", "signed")

    # --- witness or core repeating alone selects NO row -------------------
    assert verdict([a, b, dict(c, witness="w1")]) == ("NEW TERRITORY", None)
    assert verdict([a, b, dict(c, core="k1")]) == ("NEW TERRITORY", None)

    # --- repeats() reports WHERE, not just whether ------------------------
    assert repeats([a, b, dict(c, candidate="c1")], "candidate") == {"c1": [0, 2]}
    assert repeats([a, b, c], "candidate") == {}

    # --- distinct() covers all five levels -------------------------------
    assert distinct([a, b, c]) == {lv: 3 for lv in LEVELS}
    assert distinct([a, b, dict(c, core="k1")])["core"] == 2

    # --- the guard passes ONLY on arm B's exact structure -----------------
    ok_rows = [(44, 8, 31, 5.069), (361, 5, 47, 9.789), (65, 8, 43, 6.847)]
    passed, bad = guard(3, ok_rows, ARM_B["failure"], [8, 5, 8])
    assert passed, bad
    # seconds are free
    passed, _ = guard(3, [(44, 8, 31, 0.0), (361, 5, 47, 0.0), (65, 8, 43, 0.0)],
                      ARM_B["failure"], [5, 8, 8])
    assert passed
    # clause order is free, values are not
    assert guard(3, ok_rows, ARM_B["failure"], [5, 8, 8])[0]
    assert not guard(3, ok_rows, ARM_B["failure"], [5, 8, 9])[0]
    # core-row ORDER is not free
    assert not guard(3, [ok_rows[1], ok_rows[0], ok_rows[2]],
                     ARM_B["failure"], [8, 5, 8])[0]
    # each field is actually checked
    assert not guard(4, ok_rows, ARM_B["failure"], [8, 5, 8])[0]
    assert not guard(3, ok_rows[:2], ARM_B["failure"], [8, 5])[0]
    assert not guard(3, ok_rows, "AssignFail(kind='layer_unsat', site=None)",
                     [8, 5, 8])[0]
    assert not guard(3, ok_rows, ARM_B["failure"], [])[0]

    # --- serialise() is sorted, JSON-clean, and stable -------------------
    fs = frozenset({(12, 13), (2, 6), (5, 6)})
    assert serialise(fs) == [[2, 6], [5, 6], [12, 13]]
    signed = frozenset({((5, 6), "V"), ((2, 6), "M")})
    assert serialise(signed) == [[[2, 6], "M"], [[5, 6], "V"]]
    json.dumps(serialise({"core": fs, "signed": signed}))

    print("selftest OK: bar (4 rows + precedence + the two silent levels), "
          "guard (8 cases), repeats, distinct, serialise")


def main(out):
    with open(RULE6) as fh:
        entry = next(e for e in json.load(fh) if e["subject"] == "lizard")

    rows: list = []
    core_rows: list = []
    clauses: list = []
    res = None
    err = None
    t0 = time.time()
    try:
        res = compile_tree(entry["requested"], entry["pairs"], dense=True,
                           assign_budget=BUDGET, core_extraction=True,
                           debug_cores=core_rows, debug_clause_sizes=clauses,
                           debug_witness_cores=rows)
    except cores.CoreExtractionError as exc:
        # A DISTINCT outcome, not a crash: extraction refused its own pre- or
        # postcondition, so every clause this run learned is invalid and no
        # verdict row may be claimed. Nothing else is caught.
        err = f"{type(exc).__name__}: {exc}"
    secs = round(time.time() - t0, 1)

    rec = {
        "subject": "lizard",
        "assign_budget": BUDGET,
        "arm_b": {k: serialise(v) for k, v in ARM_B.items()},
        "core_extraction_error": err,
        "secs": secs,
        "rejections": len(clauses),
        "core_rows": core_rows,
        "clause_sizes": clauses,
        "stage_reached": res.stage_reached if res else None,
        "failure": repr(res.failure) if res else None,
        "layer_verdict": repr(res.verdict) if res else None,
        "layers_tried": res.layers_tried if res else None,
        "rejection_records": [{lv: serialise(r[lv]) for lv in LEVELS}
                              for r in rows],
    }

    def flush():
        with open(out, "w") as fh:
            json.dump(rec, fh, indent=1)

    flush()

    if err is not None:
        rec["guard_passed"] = False
        rec["verdict"] = "CORE EXTRACTION ERROR"
        flush()
        print(f"CORE EXTRACTION ERROR: {err}")
        print("cores.shrink refused its own pre/postcondition, so the clauses "
              "this run learned are invalid. NO row of section 6.3 may be "
              "claimed, in either direction.")
        return

    print(f"stage={rec['stage_reached']} failure={rec['failure']} "
          f"rejections={rec['rejections']} secs={secs}")

    passed, bad = guard(len(clauses), core_rows, rec["failure"], clauses)
    rec["guard_passed"] = passed
    rec["guard_mismatches"] = bad
    flush()

    if not passed:
        rec["verdict"] = "GUARD FAILED"
        flush()
        print("GUARD FAILED (spec section 6.2) -- the replay did not reproduce "
              "arm B's structure, so the instrumentation changed the run and "
              "this measures something other than arm B. NO row of section 6.3 "
              "may be claimed, in either direction.")
        for m in bad:
            print(f"  {m}")
        return

    print("guard PASSED: arm B's structure reproduced exactly")

    counts = distinct(rows)
    rec["distinct"] = counts
    n = len(rows)
    print(f"  distinct over {n} rejections: "
          + "  ".join(f"{lv}={counts[lv]}" for lv in LEVELS))

    rec["repeats"] = {lv: {str(serialise(v)): idx
                           for v, idx in repeats(rows, lv).items()}
                      for lv in LEVELS}
    v, level = verdict(rows)
    rec["verdict"] = v
    rec["verdict_level"] = level
    flush()

    for lv in LEVELS:
        for value, idx in repeats(rows, lv).items():
            print(f"  REPEAT at {lv}, rejections {idx}: {serialise(value)}")

    print()
    print(f"VERDICT: {v}" + (f" (at {level})" if level else ""))
    if v == "ENFORCEMENT DEFECT":
        print("A labelling was refuted twice. Stop this experiment line and fix "
              "assign's hits_nogood/retry. The A/B's numbers stand; every "
              "interpretation treating a rejection as new information does not.")
    elif v == "LATE ENFORCEMENT":
        print("The loop re-derived a no-good it already holds. Sound but "
              "wasted, and what hits_nogood pruning only on FULL binding "
              "predicts. Next lever is clause PROPAGATION during descent, not "
              "the local CSP.")
    elif v == "GRANULARITY CEILING":
        print("Two crease-level no-goods collapsed to one solver-variable set, "
              "so part of the 25.2x narrowing cannot reach the clause.")
    else:
        print(f"No recurrence in the only {n} rejections this budget produced. "
              f"The clause lever is finished AT THIS BUDGET: the 166,667 nodes "
              f"between rejections are the local CSP working through a "
              f"legitimately narrowed space, corroborating the independent "
              f"79.57% profile. This is WEAK evidence (section 6.4): it is "
              f"equally consistent with a loop that would start repeating at "
              f"rejection 20.")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main(sys.argv[1])
```

- [ ] **Step 2: Run the self-test to verify it passes**

Run:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py --selftest
```

Expected: `selftest OK: bar (4 rows + precedence + the two silent levels), guard (8 cases), repeats, distinct, serialise`, exit 0, in under 2 seconds.

If any assertion fails, the bar or the guard is wrong — fix it here, **before** Task 3 spends 16 minutes.

- [ ] **Step 3: Verify the self-test is not vacuous**

Temporarily break the bar to confirm the self-test catches it. Change
`VERDICT_LEVELS` to `("signed", "keys")` (dropping the decisive level), re-run
Step 2, and confirm it now FAILS on the `ENFORCEMENT DEFECT` assertion. Then
restore `VERDICT_LEVELS` to `("candidate", "signed", "keys")` and re-run
Step 2 to confirm it passes again.

Expected: fails when broken, passes when restored. A self-test that passes
against a broken bar is worse than none — it is exactly the "printed its
verdict unconditionally" failure project memory records.

- [ ] **Step 4: Commit**

```bash
git add ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py
git commit -m "evidence: the witness/core identity replay, with its bar self-tested

Spec 2026-09-28-witness-identity-design.md sections 6.2 and 6.3. One arm --
an extraction-off rejection has no core to identify.

The guard and the bar are pure functions with a --selftest mode covering all
four verdict rows, the precedence between them, the two levels that carry NO
verdict, eight guard cases, and serialise()'s sorting. Project memory records
two throwaway probes that drove wrong conclusions in one session, one of which
printed its verdict unconditionally; this runs in milliseconds and gates the
16-minute run.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Run the replay and write the verdict

**Files:**
- Create: `docs/superpowers/evidence/2026-09-28-witness-identity/identity.json` (generated)
- Create: `docs/superpowers/evidence/2026-09-28-witness-identity/README.md`

**Interfaces:**
- Consumes: `identity.py` from Task 2.
- Produces: the artifact and the README. Nothing consumes these; they are the deliverable.

**Context you need:** the run takes ~16 minutes. Start it in the background and do not poll it in a tight loop. The README is the only place the verdict is argued, and §9 fixes what it must contain. **The verdict is whatever the script prints — do not write the README before the run finishes, and do not adjust the bar to fit the data.**

- [ ] **Step 1: Re-run the self-test**

Run:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py --selftest
```

Expected: `selftest OK: ...`, exit 0. Do not start Step 2 unless this passes.

- [ ] **Step 2: Run the replay**

Run in the background (~16 minutes):

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.py ../docs/superpowers/evidence/2026-09-28-witness-identity/identity.json
```

Expected: a `guard PASSED` or `GUARD FAILED` line, then either a verdict or an
explicit refusal to claim one, and `identity.json` written.

- [ ] **Step 3: Read the artifact and confirm the run agrees with itself**

Run:

```bash
../.venv/bin/python3 -c "
import json
d = json.load(open('../docs/superpowers/evidence/2026-09-28-witness-identity/identity.json'))
print('guard', d.get('guard_passed'), d.get('guard_mismatches'))
print('verdict', d.get('verdict'), d.get('verdict_level'))
print('distinct', d.get('distinct'))
print('rejections', d['rejections'], 'records', len(d['rejection_records']))
print('core_rows', d['core_rows'])
print('clauses', d['clause_sizes'])
"
```

Expected: `rejections` equals `len(rejection_records)` equals 3. If the guard
failed, `verdict` is `GUARD FAILED` and there is no `distinct` block — that is
a correct refusal, not a bug, and Step 4 reports it as the outcome.

- [ ] **Step 4: Write the README**

Create `docs/superpowers/evidence/2026-09-28-witness-identity/README.md` with
these sections, all figures taken from `identity.json` rather than from this
plan:

1. **The question** — one paragraph: the A/B's 113 -> 3 admits two opposite
   readings, and the distinction is identity, not counts.
2. **The reproduction guard (§6.2)** — a table with all four guarded values,
   expected beside measured, and PASS/FAIL. If FAIL, the README stops here and
   says so; no verdict row may be claimed.
3. **The distinct-count table** — all five levels, distinct count out of the
   rejection count, and every repeat printed in full.
4. **The verdict (§6.3)** — which row, why that row and not its neighbours, and
   what it makes the next slice.
5. **The n=3 asymmetry (§6.4)** — stated explicitly whichever row was reached.
   If the row is NEW TERRITORY, the sentence must be *"no recurrence in the
   only three rejections this budget produced"*, and must say the result is
   equally consistent with a loop that would begin repeating at rejection 20.
6. **What this cannot say (§5)** — the clause is `{var: value}` and `keys` is
   only its input, so no `keys` or `signed` reading proves a duplicate clause;
   that needs `debug_clauses` in `assign.py`, out of scope.
7. **Limits** — §8.3: 26 of the 31 rows behind the core measurement were
   `lizard`, its `propagate` is ~100x slower than the other five subjects', and
   the subjects that would test generality cannot produce a dense labelling at
   all. Every figure here is evidence about `lizard`.
8. **Cost** — the measured wall clock, and the note that wall clock is not
   guarded because arm A drifted 1.26x on an unchanged code path.

- [ ] **Step 5: Check every figure in the README against the artifact**

Re-read the README beside `identity.json` and confirm each number appears in
the artifact. Any figure that does not must be removed or recomputed — this
step exists because the core-in-loop README shipped three arguments that its
own instruments dissolved on review.

- [ ] **Step 6: Commit**

```bash
git add ../docs/superpowers/evidence/2026-09-28-witness-identity/
git commit -m "evidence: <the verdict, in a clause> -- dense rejection identity

<one paragraph: the guard's outcome, the distinct-count table's headline, the
row reached, and the n=3 asymmetry stated explicitly>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage.** Every section of the spec maps to a task:

| Spec section | Task |
|---|---|
| §3.1/§3.2 (the two corrections) | Task 1 Step 5 records five levels, not two; Task 2's `VERDICT_LEVELS` excludes `core` |
| §4 (interfaces) | Task 1 Steps 3-5 |
| §5 (what the levels can say) | Task 2's docstring and `_VERDICT`; §5's "cannot identify the clause" in Task 3 Step 4 item 6 |
| §6.1 (protocol) | Task 2's `main` |
| §6.2 (reproduction guard) | Task 2's `guard`, self-tested in 8 cases; Task 3 Step 4 item 2 |
| §6.3 (the bar) | Task 2's `verdict`, self-tested on all four rows plus precedence |
| §6.4 (n=3 asymmetry) | Task 2's `main` prints it; Task 3 Step 4 item 5 requires it in the README |
| §7 (testing) | Task 1 Steps 1-7. §7 lists three tests; a fourth was added for §4's explicit claim that the list stays empty when `core_extraction` is `False`, which otherwise had no test. |
| §8 (risks) | §8.1 is Task 1's `test_none_does_not_perturb_the_run` plus Task 2's guard; §8.3 is Task 3 Step 4 item 7; §8.4 memory is out of scope at n=3 and noted in the spec |
| §9 (evidence) | Task 3 |
| §10 (out of scope) | the Global Constraints forbid every file it names |

**Placeholder scan.** The only intentional placeholders are in Task 3 Step 6's
commit message, which cannot be written before the data exists; Step 4's
numbered list fixes exactly what it must contain.

**Type consistency.** `debug_witness_cores` is a `list | None` receiving
`dict`s in Task 1 and read as `rows` (a list of dicts) by Task 2's `repeats`,
`distinct` and `verdict`. The five level names are spelled identically in
`compile.py`'s append, the test's `LEVELS`, and the script's `LEVELS`. `guard`
takes `(rejections, core_rows, failure, clauses)` and is called that way once.
`serialise` is the only name used for JSON conversion.

**2026-09-28 note, added after review of the shipped code.** Review fixes changed
`guard`'s signature to five arguments, adding `records` (the
`debug_witness_cores` population, distinct from `len(clause_sizes)` and
`len(core_rows)`), and raised the self-test's guard case count from 8 to 11.
This paragraph and the plan's tasks above describe what was planned, not the
shipped signature or case count; see `identity.py`'s `guard()` and `_selftest()`
for what actually shipped.

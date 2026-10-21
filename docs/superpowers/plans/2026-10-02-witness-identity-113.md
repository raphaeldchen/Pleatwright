# Witness Identity on the 113-Rejection Arm — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record which obstruction each of dense `lizard`'s 113 rejections names, and read the result against two bars pre-registered in the spec.

**Architecture:** One new keyword-only diagnostic parameter on `compile_tree` (`core_record`) runs `cores.shrink` for the **record only** while the search keeps receiving the unshrunk cone keys, so the committed arm-A baseline is preserved. One evidence script replays arm A with the record, applies a reproduction guard, and only then claims a verdict from either bar. No production behaviour changes; with `core_record=False` the compile is byte-for-byte what it is today.

**Tech Stack:** Python 3, pytest, `mcp_harness/box_pleat/` (`compile.py`, `cores.py`, `layers.py`).

**Spec:** `docs/superpowers/specs/2026-10-02-witness-identity-113-design.md`. Read it before Task 3 — the bars and their thresholds are pre-registered there and **must not be changed by any task in this plan**.

## Global Constraints

- **Run every command from the worktree root** `<repo>`, or from `mcp_harness` where a step says so. Do **NOT** `cd` to the original repository root.
- **Python is `../.venv/bin/python3` from inside `mcp_harness`** (`.venv/bin/python3` from the worktree root). The venv is a symlink shared across worktrees.
- **Never pass `--timeout` to pytest.** `pytest-timeout` is not installed and the flag makes pytest exit 4.
- **Never run `pytest tests/`** — 5,167 tests, over 3 hours. Always name the file.
- **Run the FULL named test file, never a `-k` filtered subset.**
- **Do NOT widen** `compile.py`'s `except (ValueError, RuntimeError, KeyError)` at `:236` and `:414`.
- **Do NOT modify `mcp_harness/box_pleat/cores.py`.** No code is added to a soundness-critical path.
- **Do NOT modify `docs/superpowers/evidence/2026-09-28-witness-identity/identity.py`.** That run's README claims it was never modified; editing it falsifies a published claim.
- **Do NOT change the bars or their thresholds** (spec §5.2, §5.4). They are pre-registered. `FACES_LOCALISED = 10`, `CORE_LOCALISED = 20`, `CORE_BOUNDED = 40`, `MIN_CORE_POPULATION = 90`, `EXPECTED_REJECTIONS = 113`.
- **No logic block may exist twice.** `_identity_record` and `_extract_core` are each the single implementation, shared by both of `_check`'s extraction paths; `_extract_core`'s `catch` flag is the only behavioural difference between them. (The spec's §3.2 proposed a separate duplicated call site instead; that was overruled in pre-flight review because Step 8 already shares the record block, so "the control path's code is untouched" was not a property the task could deliver anyway.)
- **`box_pleat` contains zero `print` and zero `warnings` calls across all 15 modules.** Do not add one. (Spec §4 says the caught extraction error is "printed loudly"; that printing lives in the evidence script, not the library. This is a deliberate deviation recorded here so a reviewer sees it rather than discovering it.)
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`. Write the message to a file **outside the repo** (the session scratchpad) and use `git commit -F <file>` — zsh mangles heredocs containing backticks.
- **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and other sessions. Use a temporary WIP commit.
- **Never `git add -f` anything under `.superpowers/`** (gitignored process scratch, `.gitignore:45`).
- `grep -c` **exits 1 on zero matches**, which short-circuits `&&` chains. Check exit codes before treating empty output as evidence.
- **Quote every glob passed to grep.** zsh's `nomatch` aborts the whole command when any glob fails to match, so an unquoted `--include=*.py` silently produces no output and no error.

---

## Measured Facts This Plan Relies On

Verified during planning, not assumed. Any step whose expected output disagrees with these should stop and report rather than adapt.

| fact | value | how obtained |
|---|---|---|
| `compile.py` early return | line **359** | `grep -n "if not core_extraction:"` |
| `debug_witness_cores` append | line **391** | `grep -n` |
| `replace` already imported | `compile.py:27` | `grep -n` |
| sparse `lizard` rejections | **8**, reaches stage `emit` | direct run, both paths |
| sparse `lizard` compile time | 6.6 s (`core_extraction=False`), 4.6 s (`True`) | same run |
| sparse `lizard`, extraction off | `debug_cores` **0**, `debug_witness_cores` **0** | same run (this is the gap) |
| sparse `lizard`, extraction on | `debug_cores` **8**, `debug_witness_cores` **8** | same run |
| arm A baseline | 113 rejections, 1052.0 s, clause vars 6/202/259 | `evidence/2026-09-27-core-in-loop/ab.json` |
| 31-row core facts | all `taco_tortilla`, all 3 faces, `core_variables` max 8, all ≤ 10 | `evidence/2026-09-27-nogood-core/core-sizes.json` |
| `box_pleat` print/warn count | **0** | `grep -rn "print(\|warnings\.\|sys.stderr" mcp_harness/box_pleat/*.py` |
| Python | **3.14.3** | `.venv/bin/python3 --version` |
| pytest invocation convention | `PYTHONPATH=.:tests` | `Makefile:8` |
| `@pytest.mark.slow` is registered, and `make test` excludes it | yes | `mcp_harness/conftest.py:33`, `Makefile:53` |
| `tests/test_box_pleat_witness_identity.py` | **4 passed, 25.6 s** | run during planning |
| `tests/test_box_pleat_cores.py` + `test_box_pleat_core_in_loop.py` | **11 passed, 12.8 s** | run during planning |
| `identity113.py`'s selftest and all 11 mutations | baseline green, **11/11 red** | extracted from this plan and executed during planning |

---

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/box_pleat/compile.py` (modify) | the `core_record` parameter, its misuse guard, the `_identity_record` helper, and the diagnostic branch on the extraction-off path |
| `mcp_harness/tests/test_box_pleat_witness_record.py` (create) | the parameter's behaviour, the control path's record shape, and the cheap sparse A/A |
| `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py` (create) | guard, both bars, multiplicity/overlap/Chao1 tables, serialiser, `--selftest`, `main()` |
| `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.json` (generated) | the artifact |
| `docs/superpowers/evidence/2026-10-02-witness-identity-113/README.md` (create) | the report, written from the artifact after the run |

`cores.py` and `identity.py` appear in no task. That is deliberate (Global Constraints).

---

### Task 1: The `core_record` parameter

**Files:**
- Modify: `mcp_harness/box_pleat/compile.py` — signature `:118-131`, docstring after `:177`, new helper above `compile_tree`, `_check` body `:359-400`
- Test: `mcp_harness/tests/test_box_pleat_witness_record.py` (create)

**Interfaces:**
- Consumes: `cores.shrink(graph, labels, creases, counter=list)`, `cores.CoreExtractionError`, `layers.piece_keys(witness, fold)`, `dataclasses.replace` (already imported at `compile.py:27`).
- Produces: `compile_tree(..., core_extraction=False, core_record=True, debug_witness_cores=<list>)`, appending one dict per rejection with exactly the keys `"candidate"`, `"witness"`, `"core"`, `"signed"`, `"keys"`, `"core_keys"`, `"core_error"`. On the `core_extraction=True` path the record keeps **exactly its existing five** keys. Also produces two module-level helpers, both shared by `_check`'s two extraction paths: `_identity_record(labels, w, core, keys) -> dict` and `_extract_core(graph, labels, w, debug_cores, *, catch) -> (core, error)`. Task 2 and Task 4 consume the parameter; Task 3 consumes the record's key names.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_box_pleat_witness_record.py`:

```python
"""`compile_tree(core_record=...)`: rejection identity WITHOUT narrowing.

Spec: `docs/superpowers/specs/2026-10-02-witness-identity-113-design.md` §3.

Sparse `lizard` is the subject throughout: measured 2026-10-02, it produces
exactly 8 rejections and reaches stage `emit` in ~7 s on both extraction
paths, so it exercises `_check`'s rejection branch cheaply. The dense corpus
run is `docs/superpowers/evidence/2026-10-02-witness-identity-113/
identity113.py`, not this suite.

NON-VACUITY: every test here asserts `len(records) == 8` rather than
`len(records) > 0`. If sparse `lizard` ever stops rejecting, these tests must
FAIL loudly rather than silently pass over an empty population -- an empty
record list satisfies every `all(...)` assertion about its contents.
"""
import json

import pytest

from box_pleat.compile import compile_tree
from test_box_pleat_tree import RULE6

SPARSE_LIZARD_REJECTIONS = 8
CONTROL_RECORD_KEYS = {"candidate", "witness", "core", "signed", "keys"}
DIAGNOSTIC_RECORD_KEYS = CONTROL_RECORD_KEYS | {"core_keys", "core_error"}


def _lizard():
    with open(RULE6) as fh:
        return next(e for e in json.load(fh) if e["subject"] == "lizard")


def _run(**kw):
    e = _lizard()
    return compile_tree(e["requested"], e["pairs"], **kw)


def test_core_record_without_the_list_is_refused():
    """Paying extraction's cost into nothing is a misuse, not a quiet no-op.

    Mirrors `assign.py`'s `vertex_index_verify` guard and `clause_prop_verify`
    guard: an instrument switched on with nowhere to write is the shape of
    vacuous pass this project keeps rediscovering."""
    with pytest.raises(ValueError, match="core_record"):
        _run(core_record=True)


def test_core_record_populates_records_with_extraction_off():
    """The gap this slice exists to close: today this list stays EMPTY."""
    rows = []
    res = _run(core_extraction=False, core_record=True,
               debug_witness_cores=rows)
    assert res.stage_reached == "emit"
    assert len(rows) == SPARSE_LIZARD_REJECTIONS
    for r in rows:
        assert set(r) == DIAGNOSTIC_RECORD_KEYS
        assert r["core_error"] is None
        assert r["core"] is not None and 0 < len(r["core"])
        assert r["signed"] is not None
        assert len(r["signed"]) == len(r["core"])


def test_keys_are_the_CONE_keys_not_the_narrowed_ones():
    """The non-interference claim, asserted rather than argued.

    `keys` is what `_check` RETURNS and therefore what `assign` builds its
    clause from. On this path it must be the unshrunk cone's keys -- the same
    value arm A has always returned. `core_keys` is the counterfactual
    narrowed set (spec 5.3) and must be a strict subset whenever the core is a
    strict subset of the cone.
    """
    rows = []
    _run(core_extraction=False, core_record=True, debug_witness_cores=rows)
    assert len(rows) == SPARSE_LIZARD_REJECTIONS
    narrowed_somewhere = False
    for r in rows:
        assert r["core"] <= r["witness"].creases
        assert r["core_keys"] <= r["keys"]
        if r["core"] < r["witness"].creases:
            narrowed_somewhere = True
    assert narrowed_somewhere, (
        "extraction narrowed NOTHING on any of the 8 rejections, so this test "
        "compared each set to itself and proves nothing about the cone/core "
        "distinction")


def test_core_record_off_leaves_the_list_empty():
    """The default must reproduce today's behaviour exactly."""
    rows = []
    res = _run(core_extraction=False, debug_witness_cores=rows)
    assert res.stage_reached == "emit"
    assert rows == []


def test_control_path_record_keeps_exactly_its_five_keys():
    """Arm B's record shape is published evidence and must not drift.

    `evidence/2026-09-28-witness-identity/identity.py` reads records by
    `r[level]` over its own `LEVELS`, so extra keys would not crash it -- which
    is precisely why nothing else would catch a silent widening here."""
    rows = []
    _run(core_extraction=True, debug_witness_cores=rows)
    assert len(rows) == SPARSE_LIZARD_REJECTIONS
    for r in rows:
        assert set(r) == CONTROL_RECORD_KEYS


def test_control_path_still_raises_CoreExtractionError_uncaught(monkeypatch):
    """The catch added for the diagnostic path must NOT reach the control path.

    On the control path an extraction failure means the clauses this run is
    learning are invalid -- a defect signal. `cores.CoreExtractionError`
    deliberately subclasses `Exception` and none of
    `ValueError`/`RuntimeError`/`KeyError` so `compile_tree`'s handler cannot
    fold it into an indistinguishable `AssignFail("error")`."""
    import box_pleat.compile as compile_mod
    from box_pleat.cores import CoreExtractionError

    def boom(*a, **kw):
        raise CoreExtractionError("synthetic control-path refusal")

    monkeypatch.setattr(compile_mod.cores, "shrink", boom)
    with pytest.raises(CoreExtractionError, match="synthetic control-path"):
        _run(core_extraction=True, debug_witness_cores=[])


def test_diagnostic_path_records_a_refusal_and_CONTINUES(monkeypatch):
    """A diagnostic failure must not kill a 47-minute run (spec 4).

    The core reaches no clause here, so nothing about soundness is at risk;
    the only thing at risk is the record's own population, which the evidence
    script gates on explicitly."""
    import box_pleat.compile as compile_mod
    from box_pleat.cores import CoreExtractionError

    def boom(*a, **kw):
        raise CoreExtractionError("synthetic diagnostic refusal")

    monkeypatch.setattr(compile_mod.cores, "shrink", boom)
    rows = []
    res = _run(core_extraction=False, core_record=True,
               debug_witness_cores=rows)
    assert res.stage_reached == "emit"
    assert len(rows) == SPARSE_LIZARD_REJECTIONS
    for r in rows:
        assert r["core"] is None
        assert r["signed"] is None
        assert r["core_keys"] is None
        assert "synthetic diagnostic refusal" in r["core_error"]
        assert r["keys"] is not None and len(r["keys"]) > 0


def test_debug_cores_records_only_SUCCESSFUL_extractions(monkeypatch):
    """`len(debug_cores)` is the core population the bars gate on.

    A refused extraction must append NO row rather than a row with a
    fabricated 0 core size. A default-valued zero is exactly how a missing
    measurement becomes a published number."""
    import box_pleat.compile as compile_mod
    from box_pleat.cores import CoreExtractionError

    def boom(*a, **kw):
        raise CoreExtractionError("synthetic refusal")

    rows, cores_rows = [], []
    _run(core_extraction=False, core_record=True, debug_witness_cores=rows,
         debug_cores=cores_rows)
    assert len(cores_rows) == SPARSE_LIZARD_REJECTIONS

    monkeypatch.setattr(compile_mod.cores, "shrink", boom)
    rows2, cores_rows2 = [], []
    _run(core_extraction=False, core_record=True, debug_witness_cores=rows2,
         debug_cores=cores_rows2)
    assert len(rows2) == SPARSE_LIZARD_REJECTIONS
    assert cores_rows2 == []


def test_sparse_AA_core_record_does_not_perturb_the_search():
    """The cheap half of the decisive gate (spec 6.1).

    The whole design rests on "diagnostic extraction does not change the
    search", which is a claim about shallow-copy aliasing:
    `layers._seeded` returns `dataclasses.replace(graph.cons, direct=direct)`
    and `replace` is SHALLOW, so a nested mutation inside
    `layer_order.propagate` is not excluded by inspection.

    The full clause-size POPULATION is compared, not its length: two runs can
    reject the same number of times with different clauses. Task 2 runs the
    same comparison on dense `lizard`, the arm that actually ships."""
    off, on = [], []
    r_off = _run(core_extraction=False, debug_clause_sizes=off)
    r_on = _run(core_extraction=False, core_record=True,
                debug_witness_cores=[], debug_clause_sizes=on)
    assert len(off) == SPARSE_LIZARD_REJECTIONS
    assert off == on
    assert r_off.stage_reached == r_on.stage_reached
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_record.py -v
```

Expected: every test FAILS. The eight that pass `core_record=` fail with `TypeError: compile_tree() got an unexpected keyword argument 'core_record'`; `test_control_path_record_keeps_exactly_its_five_keys` and `test_control_path_still_raises_CoreExtractionError_uncaught` are the only two that may already pass, since they exercise today's control path.

- [ ] **Step 3: Add the parameter to the signature**

In `mcp_harness/box_pleat/compile.py`, insert one line after `debug_witness_cores: list | None = None,` (`:126`):

```python
                 core_record: bool = False,
```

- [ ] **Step 4: Add the docstring paragraph**

In `compile.py`, immediately after the existing `debug_witness_cores` paragraph (the one ending `because the core is the thing being identified and there is none.`), replace that paragraph's final sentence and append a new paragraph. The final sentence becomes:

```
    It stays empty when `core_extraction` is `False` unless `core_record` is
    set -- see the next paragraph.
```

Then append:

```
    `core_record`, when `True` and `core_extraction` is `False`, runs
    `cores.shrink` for the RECORD ONLY. The keys handed to `assign` are the
    unshrunk cone's, exactly as on the un-recorded path, so the search is
    identical and the committed arm-A baseline (113 rejections, clause vars
    6/202/259, `evidence/2026-09-27-core-in-loop/ab.json`) is preserved while
    the record gains the true minimal cause. Its records carry two fields the
    `core_extraction` path's do not: `core_keys`, the clause input the
    narrowing path WOULD have built (spec section 5.3), and `core_error`, the
    message of a caught `cores.CoreExtractionError` or `None`. On this path
    that exception is CAUGHT -- the diagnostic core reaches no clause, so the
    only thing at risk is the record's population, which the evidence script
    gates on. On the `core_extraction` path it stays uncaught. Requires
    `debug_witness_cores`; see the guard below. Spec
    `2026-10-02-witness-identity-113-design.md` sections 3 and 4.
```

- [ ] **Step 5: Add the misuse guard**

In `compile.py`, immediately after the `compile_tree` docstring's closing `"""` and **before** `res = Result()`:

```python
    if core_record and debug_witness_cores is None:
        raise ValueError(
            "compile_tree: core_record=True with debug_witness_cores=None "
            "pays the full cost of `cores.shrink` on every rejection and "
            "writes the result NOWHERE. An instrument switched on with no "
            "sink is the vacuous-pass shape this project keeps "
            "rediscovering, so it is refused rather than silently ignored. "
            "Pass a list, or leave core_record False.")
```

This sits outside the `try` that wraps `assign(...)`, so the `ValueError` propagates rather than being typed into `AssignFail("error")`.

- [ ] **Step 6: Add the two shared helpers**

Both of `_check`'s extraction paths call both of these, so neither block is duplicated. In `compile.py`, immediately **above** `def compile_tree(`:

```python
def _identity_record(labels, w, core, keys) -> dict:
    """The five-level identity record for one rejection.

    The ONLY constructor of this dict, so the `core_extraction` path and the
    `core_record` path cannot drift apart in field names or ordering. The
    `core_extraction` path appends exactly what this returns; the
    `core_record` path adds `core_keys` and `core_error` on top (spec
    `2026-10-02-witness-identity-113-design.md` section 5.1).

    `core` is `None` only on the `core_record` path, when extraction refused.
    `signed` is then `None` too rather than an empty frozenset: an empty set
    is a real identity that would join the distinct-value population and
    fabricate a shared cause across every refused rejection.

    `labels[c]` cannot KeyError: `core` is a subset of `w.creases`, which
    `layers.propagate` fills from `exc.deps` -- the SEEDED slot edges -- and
    `_seeded` seeds only keys present in `labels`.
    """
    return {
        "candidate": frozenset(labels.items()),
        "witness": w,
        "core": core,
        "signed": (None if core is None
                   else frozenset((c, labels[c]) for c in core)),
        "keys": keys,
    }


def _extract_core(graph, labels, w, debug_cores, *, catch):
    """`cores.shrink` plus its cost row. Returns `(core, error_message)`.

    The ONLY caller of `cores.shrink` in this module, so the timer, the oracle
    counter and the `debug_cores` row cannot drift between `_check`'s two
    extraction paths.

    `catch` is the only difference between the two callers, and it is not a
    style choice. With `catch=False` -- the `core_extraction` control path --
    a `cores.CoreExtractionError` means the clauses this run is learning are
    invalid, a defect signal, and it propagates out of `compile_tree`
    UNCAUGHT: that exception deliberately subclasses `Exception` and none of
    `ValueError`/`RuntimeError`/`KeyError` precisely so the handler around
    `assign(...)` cannot fold it into an indistinguishable
    `AssignFail("error")`. With `catch=True` -- the `core_record` diagnostic
    path -- the core reaches no clause, so the only casualty is the record's
    own population, which the evidence script gates its verdict on; killing a
    ~47-minute run for a diagnostic failure would destroy the measurement it
    is paying for.

    A refused extraction appends NO cost row, so `len(debug_cores)` is the
    SUCCESSFUL-extraction population. A row carrying a fabricated core size of
    0 is how a missing measurement becomes a published number.

    `t0` here is a fresh local of a module-level function with no enclosing
    `t0` to shadow, so the naming caution the control path used to carry
    (`compile_tree`'s own `t0`, which `tick()` mutates via `nonlocal`) no
    longer applies and is deliberately not reproduced.
    """
    calls = [0]
    t0 = time.perf_counter()
    try:
        core = cores.shrink(graph, labels, w.creases, counter=calls)
    except cores.CoreExtractionError as exc:
        if not catch:
            raise
        return None, str(exc)
    if debug_cores is not None:
        debug_cores.append((len(w.creases), len(core), calls[0],
                            round(time.perf_counter() - t0, 3)))
    return core, None
```

- [ ] **Step 7: Rewrite the extraction-off branch in `_check`**

In `compile.py`, replace these two lines (`:359-360`):

```python
        if not core_extraction:
            return _layers.piece_keys(w, fold), w
```

with:

```python
        if not core_extraction:
            cone_keys = _layers.piece_keys(w, fold)
            if core_record:
                # DIAGNOSTIC ONLY. `cone_keys` above is what this function
                # returns, and therefore the only thing `assign` builds its
                # clause from; nothing below this line reaches the control
                # path. That is the whole non-interference claim, and it is
                # one line to check rather than an argument to trust (spec
                # `2026-10-02-witness-identity-113-design.md` section 3).
                #
                # `catch=True` is the ONLY way this call differs from the
                # control path's below -- see `_extract_core`'s docstring for
                # why that one flag is a soundness distinction and not a
                # style choice.
                rec_core, rec_err = _extract_core(graph_cell[0], labels, w,
                                                  debug_cores, catch=True)
                rec = _identity_record(labels, w, rec_core, cone_keys)
                rec["core_keys"] = (
                    None if rec_core is None
                    else _layers.piece_keys(replace(w, creases=rec_core),
                                            fold))
                rec["core_error"] = rec_err
                debug_witness_cores.append(rec)
            return cone_keys, w
```

- [ ] **Step 8: Route the control path through both helpers**

Two replacements in `compile.py`'s `_check`, so that neither helper's logic exists twice.

**8a.** Replace the control path's extraction block — from `calls = [0]` (`:361`) through the `debug_cores.append(...)` call and its closing paren (`:370`), **including** the four-line comment about naming `t_extract0` apart from `compile_tree`'s `t0`, which no longer applies because the timer now lives in a module-level helper — with:

```python
        core, _ = _extract_core(graph_cell[0], labels, w, debug_cores,
                                catch=False)
```

`catch=False` preserves today's behaviour exactly: `cores.CoreExtractionError` propagates out of `compile_tree` uncaught. The discarded second return value is always `None` on this path, because `_extract_core` only returns a message when it caught.

**8b.** Replace the control-path record append (the block starting `if debug_witness_cores is not None:` at `:391` and its dict literal, through the `"keys": keys,` entry and its closing `})`) with:

```python
        if debug_witness_cores is not None:
            # Exactly the five fields and values this path has always
            # appended. `_identity_record` is shared with the `core_record`
            # path so the two cannot drift; the two extra fields that path
            # adds are added THERE, because arm B's published record shape
            # (`evidence/2026-09-28-witness-identity/`) must not change.
            debug_witness_cores.append(
                _identity_record(labels, w, core, keys))
```

**The control path's behaviour must be unchanged by 8a and 8b, and that is what Step 11's three suites check.** Its *code* does change — both helpers are shared — so the claim this task makes is "behaviour-identical, pinned by tests", not "untouched".

- [ ] **Step 9: Run the tests to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_record.py -v
```

Expected: **9 passed**. Runtime roughly 1–2 minutes (eleven sparse `lizard` compiles at ~5–7 s each).

- [ ] **Step 10: Verify the standing invariants did not move**

```bash
cd mcp_harness && grep -c box_pleat server.py; echo "grep exit=$?"
```

Expected: `0` and `grep exit=1` (zero matches, and `grep -c` exits 1 on zero matches — the exit code is the check that the command ran).

```bash
cd mcp_harness && grep -n "except (ValueError, RuntimeError, KeyError)" box_pleat/compile.py
```

Expected: exactly two lines, unchanged — the handler was not widened.

```bash
cd mcp_harness && grep -rn "print(\|warnings\.\|sys.stderr" box_pleat/; echo "exit=$?"
```

Expected: no output, `exit=1`. The package's zero-print invariant holds.

- [ ] **Step 11: Verify the predecessor's suites still pass**

The control path was refactored in Step 8, so every suite covering it must be re-run in full. All three baselines below were measured during planning on the unmodified tree.

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_identity.py -v
```

Expected: **4 passed**, ~26 s. This is the predecessor's own suite and the one that covers the record Step 8 refactored.

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_cores.py tests/test_box_pleat_core_in_loop.py -v
```

Expected: **11 passed**, ~13 s.

A different count on either command means Step 8 changed behaviour, not just structure. Stop and report rather than adjusting the tests.

- [ ] **Step 12: Commit**

```bash
cd mcp_harness && git add box_pleat/compile.py tests/test_box_pleat_witness_record.py && cd .. && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t1-msg.txt
```

Write `t1-msg.txt` first, with this content:

```
witness-identity: core_record records the cause without narrowing the clause

compile_tree's identity record sat below the core_extraction early return at
compile.py:359, so it only ever populated on the 3-rejection arm. core_record
runs cores.shrink for the RECORD ONLY: the search still receives the unshrunk
cone keys, so arm A's 113-rejection structure is preserved while the record
gains the true minimal cause.

Two fields are added on this path only -- core_keys (the clause input the
narrowing path would have built) and core_error -- so arm B's published
record shape does not change. _identity_record is the single constructor both
paths share.

CoreExtractionError is caught HERE and nowhere else: the diagnostic core
reaches no clause, so the population is the only casualty, and the evidence
script gates its verdict on that count.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 2: The dense A/A non-interference gate

**Files:**
- Create: `mcp_harness/tests/test_box_pleat_witness_record_dense_aa.py`

**Interfaces:**
- Consumes: `compile_tree(..., dense=True, core_extraction=False, core_record=<bool>, debug_clause_sizes=<list>, debug_witness_cores=<list>, assign_budget=20_000)` from Task 1.
- Produces: nothing for later tasks. This is a gate, and Task 4 must not run until it passes.

**Why this is its own task.** The entire design rests on "diagnostic extraction does not change the search," and that is a claim about shallow-copy aliasing (`layers._seeded` returns `dataclasses.replace(graph.cons, direct=direct)`; `replace` is shallow) that cannot be settled by reading code. Task 1's sparse A/A is cheap and catches gross leaks; this one runs the **actual configuration that ships** — dense `lizard` — and a reviewer must be able to reject it independently of Task 1's code.

- [ ] **Step 1: Write the gate**

Create `mcp_harness/tests/test_box_pleat_witness_record_dense_aa.py`:

```python
"""The decisive A/A: does `core_record` perturb the DENSE search?

Spec: `docs/superpowers/specs/2026-10-02-witness-identity-113-design.md` §6.1.

SLOW BY DESIGN -- two dense `lizard` compiles at 20,000 nodes, expect roughly
5-12 minutes total. It is a gate, not a unit test, and it runs once before the
500,000-node measurement rather than on every suite run.

`assign_budget=20_000` and not 500,000: the point is to exercise the dense
configuration, and a budget 25x smaller samples the same code path. If
aliasing leaks, it leaks here.

MARKED `slow`: `make test` is the PR gate and runs `-m "not slow"`
(`Makefile:53`). Without the marker this file adds 5-12 minutes to every PR.
`make test-slow` and `make test-all` still run it.
"""
import json

import pytest

from box_pleat.compile import compile_tree
from test_box_pleat_tree import RULE6

BUDGET = 20_000


def _run(**kw):
    with open(RULE6) as fh:
        e = next(x for x in json.load(fh) if x["subject"] == "lizard")
    return compile_tree(e["requested"], e["pairs"], dense=True,
                        assign_budget=BUDGET, core_extraction=False, **kw)


@pytest.mark.slow
def test_dense_core_record_leaves_the_search_identical():
    """Identical rejection count AND identical clause-size POPULATION.

    The population, not its length: two runs can reject the same number of
    times having learned different clauses, and a length-only assertion would
    pass on that. The failure mode being excluded is a nested mutation inside
    `layer_order.propagate` leaking through `dataclasses.replace`'s shallow
    copy into the shared `graph_cell[0]`, which would make the recorded run a
    different search from the one whose baseline is committed.
    """
    off = []
    r_off = _run(debug_clause_sizes=off)

    on, recs = [], []
    r_on = _run(debug_clause_sizes=on, core_record=True,
                debug_witness_cores=recs)

    # Non-vacuity first: an empty population would satisfy `off == on`.
    assert len(off) > 0, (
        f"dense lizard rejected 0 times at budget {BUDGET}, so this A/A "
        f"compared two empty lists and tested nothing. Raise BUDGET until "
        f"rejections appear, and record the value used.")

    assert off == on, (
        f"CORE_RECORD PERTURBED THE SEARCH. clause sizes off={off} on={on}. "
        f"The diagnostic extraction is not diagnostic; do not run the "
        f"500,000-node measurement.")
    assert len(recs) == len(on), (
        f"records={len(recs)} but rejections={len(on)} -- the record "
        f"population must equal the rejection population")
    assert r_off.stage_reached == r_on.stage_reached
    assert repr(r_off.failure) == repr(r_on.failure)
```

- [ ] **Step 2: Run the gate**

```bash
cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python3 -m pytest tests/test_box_pleat_witness_record_dense_aa.py -v
```

Expected: **1 passed**, in roughly 5–12 minutes.

**If it FAILS on `off == on`:** stop. Do not proceed to Task 3 or 4. Report the two clause-size populations. The design's central assumption is false and the spec needs revision, not the code.

- [ ] **Step 3: Record the measured figures**

Report, for the task report file: the wall-clock of each arm, `len(off)` (the dense rejection count at 20,000 nodes), and `r_off.failure`. These are the first measurements of this configuration and Task 4's cost estimate is checked against them.

- [ ] **Step 4: Commit**

```bash
cd mcp_harness && git add tests/test_box_pleat_witness_record_dense_aa.py && cd .. && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t2-msg.txt
```

`t2-msg.txt`:

```
witness-identity: the dense A/A gate for core_record non-interference

The design rests on diagnostic extraction not changing the search, which is a
claim about shallow-copy aliasing -- layers._seeded returns
dataclasses.replace(graph.cons, direct=direct) and replace is SHALLOW, so a
nested mutation inside layer_order.propagate is not excluded by inspection.

So it is tested rather than argued: dense lizard at 20,000 nodes, twice, with
core_record off and on, asserting identical rejection count and identical
clause-size POPULATION (not merely its length -- two runs can reject the same
number of times having learned different clauses).

Slow by design, ~5-12 min. It runs once before the 500,000-node measurement.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 3: `identity113.py` — guard, both bars, tables

**Files:**
- Create: `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py` (pure functions and `--selftest` only; `main()` is Task 4)

**Interfaces:**
- Consumes: the record key names Task 1 produces — `"candidate"`, `"witness"`, `"core"`, `"signed"`, `"keys"`, `"core_keys"`, `"core_error"` — and `layers.Witness`'s attributes `kind`, `creases`, `faces`, `prov`.
- Produces, for Task 4: `ARM_A` (dict), `LEVELS`, `FACES_LOCALISED=10`, `CORE_LOCALISED=20`, `CORE_BOUNDED=40`, `MIN_CORE_POPULATION=90`, `EXPECTED_REJECTIONS=113`, `value_at(row, level)`, `population(rows, level)`, `distinct(rows, level) -> int`, `repeats(rows, level) -> dict`, `multiplicity(rows, level) -> dict`, `chao1(mult) -> float | None`, `overlaps(rows, level) -> list`, `guard(rejections, layers_tried, failure, clause_sizes, n_records) -> (bool, list)`, `solver_bar(rows) -> dict`, `geometry_bar(rows) -> dict`, `serialise(v)`, `selftest()`.

**Read the spec's §5.2, §5.4 and §5.5 before writing this file.** The thresholds and rows are pre-registered and this task implements them; it does not choose them.

- [ ] **Step 1: Write the module with its `--selftest`**

Create `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py`:

```python
"""Did dense `lizard`'s 113 rejections name 113 obstructions, or a few?

Spec: `../../specs/2026-10-02-witness-identity-113-design.md`.

Arm A's configuration plus `core_record=True`: the search receives the same
unshrunk cone keys it always has, so the committed 113-rejection baseline is
preserved, while the record gains the true minimal cause.

TWO BARS, both pre-registered in the spec before this file existed. The solver
bar is the predecessor's (`../2026-09-28-witness-identity/`) VERBATIM -- only
the population changes, 3 -> 113 -- because that run's outcome is now known
and a bar re-chosen with that knowledge is not a bar. The geometry bar is new.

`--selftest` runs every bar row, both bars' precedence, all five invalidity
conditions, and the mutations the spec pre-registers. Run it before the real
run; a bar nobody has exercised is not a bar either.
"""
from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------- constants

# The committed arm-A baseline this run must reproduce, from
# `../2026-09-27-core-in-loop/ab.json` `arms[0]`. Structure only: wall clock
# has drifted 0.82x-1.26x across replays of UNCHANGED code, so guarding it
# would fail the experiment for reasons unrelated to the instrument.
ARM_A = {
    "source": "../2026-09-27-core-in-loop/ab.json arms[0]",
    "rejections": 113,
    "layers_tried": 113,
    "failure": "AssignFail(kind='budget', site=500000)",
    "clause_vars_min": 6,
    "clause_vars_median": 202,
    "clause_vars_max": 259,
}

EXPECTED_REJECTIONS = 113

# Pre-registered thresholds (spec 5.4). DO NOT change these to fit the data.
FACES_LOCALISED = 10
CORE_LOCALISED = 20
CORE_BOUNDED = 40
MIN_CORE_POPULATION = 90

# Levels reported. `core_keys` carries NO bar row (spec 5.3) and `kind` and
# `faces` carry none alone (spec 5.4); all four are still reported.
LEVELS = ("candidate", "witness", "core", "signed", "keys", "core_keys",
          "faces", "kind")

# The solver bar's rows, in evaluation order, with the level each reads.
SOLVER_ROWS = (("1 ENFORCEMENT DEFECT", "candidate"),
               ("2 LATE ENFORCEMENT", "signed"),
               ("3 GRANULARITY CEILING", "keys"))


# ------------------------------------------------------------- accessors

def value_at(row, level):
    """The value of `level` in one record.

    `faces` and `kind` live on the witness rather than at the top level, and
    are reached here rather than by every caller, so a future level added to
    `LEVELS` has exactly one place to be taught about.
    """
    if level == "faces":
        return row["witness"].faces
    if level == "kind":
        return row["witness"].kind
    return row[level]


def population(rows, level):
    """The rows at which `level` actually has a value.

    A record whose extraction refused carries `core`, `signed` and
    `core_keys` as `None`. Those rows are NOT members of those levels'
    populations: counting `None` as a distinct value would fabricate one
    shared identity across every refused rejection, which understates
    distinctness exactly where the geometry bar reads it.
    """
    return [r for r in rows if value_at(r, level) is not None]


# ---------------------------------------------------------------- counting

def multiplicity(rows, level) -> dict:
    """value -> how many rows carry it, over `population(rows, level)`."""
    out = {}
    for r in population(rows, level):
        v = value_at(r, level)
        out[v] = out.get(v, 0) + 1
    return out


def distinct(rows, level) -> int:
    return len(multiplicity(rows, level))


def repeats(rows, level) -> dict:
    """value -> the row indices carrying it, for values carried more than once.

    Indices are into `rows` as given, not into the filtered population, so a
    reported index can be looked up in the artifact directly.
    """
    seen = {}
    for i, r in enumerate(rows):
        v = value_at(r, level)
        if v is None:
            continue
        seen.setdefault(v, []).append(i)
    return {v: idx for v, idx in seen.items() if len(idx) > 1}


def chao1(mult: dict):
    """Chao (1984) lower-bound estimate of the number of classes not seen.

    `S_obs + f1^2/(2*f2)`. REFERENCE FIGURE ONLY, never a bar level: Chao1
    assumes independent sampling and these rejections are outputs of one
    search. Returns `None` when `f2` is 0, where the estimator is undefined --
    not 0.0, and not `S_obs`, either of which would read as a measurement.
    """
    counts = list(mult.values())
    f1 = sum(1 for c in counts if c == 1)
    f2 = sum(1 for c in counts if c == 2)
    if f2 == 0:
        return None
    return len(counts) + (f1 * f1) / (2.0 * f2)


def overlaps(rows, level) -> list:
    """Pairwise |intersection| for every pair, for set-valued levels.

    Distinct is not disjoint. The predecessor's section 3 found that its three
    candidates agreed on 677 of 745 labels while reading as fully distinct,
    and a reader will find the same thing unaided.
    """
    pop = population(rows, level)
    out = []
    for i in range(len(pop)):
        for j in range(i + 1, len(pop)):
            a, b = value_at(pop[i], level), value_at(pop[j], level)
            if isinstance(a, frozenset) and isinstance(b, frozenset):
                out.append((i, j, len(a & b), len(a), len(b)))
    return out


# ------------------------------------------------------------------- guard

def guard(rejections, layers_tried, failure, clause_sizes, n_records):
    """Did this run reproduce arm A's STRUCTURE? Returns `(passed, mismatches)`.

    Arm B's guard compared three exact per-rejection triples in order. Arm A
    published no `core_rows`, so this guard compares a count and a
    min/median/max -- weaker, and the strongest the committed baseline
    affords. The run publishes its full 113-value clause-size population so a
    future replay can guard it exactly.
    """
    bad = []
    if rejections != ARM_A["rejections"]:
        bad.append(f"rejections {rejections} != {ARM_A['rejections']}")
    if layers_tried != ARM_A["layers_tried"]:
        bad.append(f"layers_tried {layers_tried} != {ARM_A['layers_tried']}")
    if failure != ARM_A["failure"]:
        bad.append(f"failure {failure!r} != {ARM_A['failure']!r}")
    if n_records != ARM_A["rejections"]:
        bad.append(f"records {n_records} != {ARM_A['rejections']}")
    if not clause_sizes:
        bad.append("clause_sizes is EMPTY -- nothing to compare")
    else:
        s = sorted(clause_sizes)
        med = s[len(s) // 2]
        for got, key in ((s[0], "clause_vars_min"), (med, "clause_vars_median"),
                         (s[-1], "clause_vars_max")):
            if got != ARM_A[key]:
                bad.append(f"{key} {got} != {ARM_A[key]}")
    return (not bad), bad


# -------------------------------------------------------------------- bars

def solver_bar(rows) -> dict:
    """The predecessor's bar (its spec 6.3), verbatim, on this population.

    Rows are evaluated in order and the first match wins. Rows 1 and 3 read
    levels present on every record; row 2 reads `signed`, which exists only
    where a core does, so its population can be smaller and is reported.

    Row 2 fires at ANY population size -- a repeat is decisive at n=1, which
    is the predecessor's own asymmetry argument, so a DETECTED repeat is never
    suppressed for being rare. What a small population forbids is the
    ABSENCE of a row-2 repeat supporting row 4 (spec 5.5 condition 4).
    """
    n_signed = len(population(rows, "signed"))
    out = {"signed_population": n_signed, "partial": False, "note": None}
    for name, level in SOLVER_ROWS:
        rep = repeats(rows, level)
        if rep:
            out["verdict"] = name
            out["verdict_level"] = level
            if level == "signed" and n_signed < EXPECTED_REJECTIONS:
                out["note"] = (f"row 2 fired on a signed population of "
                               f"{n_signed}, not {EXPECTED_REJECTIONS}")
            return out
    out["verdict_level"] = None
    if n_signed < MIN_CORE_POPULATION:
        out["verdict"] = "ROWS 1 AND 3 ONLY -- ROW 4 DECLINED"
        out["partial"] = True
        out["note"] = (
            f"no repeat at candidate or keys over {len(rows)} rejections, but "
            f"the signed population is {n_signed} < {MIN_CORE_POPULATION}, so "
            f"row 2's absence is untested and cannot support NEW TERRITORY")
        return out
    out["verdict"] = "4 NEW TERRITORY"
    if n_signed < EXPECTED_REJECTIONS:
        out["partial"] = True
        out["note"] = (f"row 4 reached with a signed population of {n_signed} "
                       f"of {EXPECTED_REJECTIONS}: PARTIAL")
    return out


def geometry_bar(rows) -> dict:
    """The new bar (spec 5.4). Rows in order, first match wins.

    G1 requires BOTH `faces` and `core` to be small: `layers.py:52` annotates
    `faces` "diagnostic only", so it may strengthen a row `core` supports and
    may never fire one alone. `core` <= CORE_LOCALISED with `faces` above its
    threshold therefore selects G2, and `faces` small with `core` above
    CORE_BOUNDED selects G3.
    """
    cored = population(rows, "core")
    n = len(cored)
    # ALL THREE counts are over `cored`, never over `rows`. `faces` and `kind`
    # live on the witness and are never `None`, so a refused extraction would
    # otherwise contribute a face triple to the site count while contributing
    # no cause to the core count -- making G1's two conditions measurements of
    # two different populations. A refused rejection has no IDENTIFIED
    # obstruction, so it is a member of neither. The two coincide when n == 113,
    # which is exactly why a mismatch here would surface only in the degraded
    # case, where it does the most damage.
    out = {"core_population": n,
           "partial": n < EXPECTED_REJECTIONS,
           "distinct_core": distinct(cored, "core"),
           "distinct_faces": distinct(cored, "faces"),
           "distinct_kind": distinct(cored, "kind"),
           "note": None}
    if n < MIN_CORE_POPULATION:
        out["verdict"] = "NO VERDICT"
        out["note"] = (f"core population {n} < {MIN_CORE_POPULATION}: "
                       f"extraction refused on {len(rows) - n} of "
                       f"{len(rows)} rejections")
        return out
    d_core, d_faces = out["distinct_core"], out["distinct_faces"]
    if d_faces <= FACES_LOCALISED and d_core <= CORE_LOCALISED:
        out["verdict"] = "G1 LOCALISED"
    elif d_core <= CORE_BOUNDED:
        out["verdict"] = "G2 BOUNDED"
    else:
        out["verdict"] = "G3 DIFFUSE"
        out["note"] = (
            "G3 IS THE SOFT VERDICT. `layer_order._propagate` is not "
            "confluent, so a cone is A derivation of the contradiction rather "
            "than THE cause, and distinctness may be derivational rather than "
            "geometric: 113 distinct cores are consistent with ONE "
            "obstruction reached 113 different ways. G3 licenses 'repeats are "
            "not exploitable through this instrument', NOT 'the geometry is "
            "fine'.")
    if out["partial"]:
        out["note"] = ((out["note"] or "") +
                       f" POPULATION IS {n}, NOT {EXPECTED_REJECTIONS}.")
    return out


# -------------------------------------------------------------- serialiser

def serialise(v):
    """JSON-safe, order-stable, and lossless about which TYPE it saw.

    `sorted` on a frozenset of tuples is what makes two runs' artifacts
    diffable; a bare `list(frozenset)` is insertion-ordered and would differ
    run to run for identical content.
    """
    if isinstance(v, frozenset):
        return sorted(serialise(x) for x in v)
    if isinstance(v, tuple):
        return [serialise(x) for x in v]
    if isinstance(v, (str, int, float)) or v is None:
        return v
    if hasattr(v, "kind") and hasattr(v, "creases"):
        return {"kind": v.kind, "creases": serialise(v.creases),
                "faces": serialise(v.faces), "prov": str(v.prov)}
    return str(v)
```

- [ ] **Step 2: Append the `--selftest` to the same file**

Append to `identity113.py`:

```python
# ---------------------------------------------------------------- selftest

class _W:
    """A Witness stand-in: the bars read only `kind`, `creases`, `faces`."""

    def __init__(self, kind="taco_tortilla", faces=(1, 2, 3), creases=()):
        self.kind = kind
        self.faces = faces
        self.creases = frozenset(creases)
        self.prov = f"{kind} among {faces}"


def _row(cand, core, keys, faces=(1, 2, 3), signed=None, core_keys=None,
         err=None):
    return {"candidate": frozenset(cand), "witness": _W(faces=faces),
            "core": None if core is None else frozenset(core),
            "signed": (None if core is None
                       else frozenset(signed if signed is not None else core)),
            "keys": frozenset(keys),
            "core_keys": (None if core is None
                          else frozenset(core_keys if core_keys is not None
                                         else core)),
            "core_error": err}


def _spread(n, start=0):
    """`n` rows, all distinct at every level, with distinct face triples."""
    return [_row([("c", i)], [i], [i], faces=(i, i + 1, i + 2))
            for i in range(start, start + n)]


def selftest():
    # --- population excludes refusals rather than counting None -----------
    rows = _spread(3) + [_row([("c", 99)], None, [99], err="refused")]
    assert len(population(rows, "core")) == 3
    assert len(population(rows, "keys")) == 4
    assert distinct(rows, "core") == 3, (
        "a refused row must not join the core population")

    # --- multiplicity, repeats, chao1 -------------------------------------
    dup = _spread(3) + [_row([("c", 0)], [0], [0], faces=(0, 1, 2))]
    m = multiplicity(dup, "core")
    assert sorted(m.values()) == [1, 1, 2]
    assert repeats(dup, "core") == {frozenset([0]): [0, 3]}
    assert chao1({"a": 1, "b": 1, "c": 2}) == 3 + (2 * 2) / 2.0
    assert chao1({"a": 1, "b": 1}) is None, "f2=0 must be None, not 0.0"

    # --- overlaps ---------------------------------------------------------
    ov = overlaps([_row([("c", 0)], [1, 2, 3], [1]),
                   _row([("c", 1)], [3, 4, 5], [2])], "core")
    assert ov == [(0, 1, 1, 3, 3)], ov

    # --- guard ------------------------------------------------------------
    good = [6] + [202] * 111 + [259]
    ok, bad = guard(113, 113, ARM_A["failure"], good, 113)
    assert ok and bad == [], bad
    for args, needle in (
            ((112, 113, ARM_A["failure"], good, 113), "rejections"),
            ((113, 112, ARM_A["failure"], good, 113), "layers_tried"),
            ((113, 113, "AssignFail(kind='unsat', site=None)", good, 113),
             "failure"),
            ((113, 113, ARM_A["failure"], good, 112), "records"),
            ((113, 113, ARM_A["failure"], [], 113), "EMPTY"),
            ((113, 113, ARM_A["failure"], [7] + [202] * 111 + [259], 113),
             "clause_vars_min"),
    ):
        ok, bad = guard(*args)
        assert not ok and any(needle in b for b in bad), (args, bad)

    # --- solver bar, every row and its precedence -------------------------
    base = _spread(113)
    assert solver_bar(base)["verdict"] == "4 NEW TERRITORY"
    assert solver_bar(base)["partial"] is False

    cand_dup = _spread(112) + [_row([("c", 0)], [900], [900], faces=(9, 9, 9))]
    v = solver_bar(cand_dup)
    assert v["verdict"] == "1 ENFORCEMENT DEFECT" and v["verdict_level"] == "candidate"

    sig_dup = _spread(112) + [_row([("c", 900)], [0], [900], faces=(9, 9, 9))]
    v = solver_bar(sig_dup)
    assert v["verdict"] == "2 LATE ENFORCEMENT" and v["verdict_level"] == "signed"

    key_dup = _spread(112) + [_row([("c", 900)], [900], [0], faces=(9, 9, 9))]
    v = solver_bar(key_dup)
    assert v["verdict"] == "3 GRANULARITY CEILING" and v["verdict_level"] == "keys"

    # precedence: candidate beats signed beats keys when all three repeat
    allthree = _spread(112) + [_row([("c", 0)], [0], [0], faces=(9, 9, 9))]
    assert solver_bar(allthree)["verdict"] == "1 ENFORCEMENT DEFECT"

    # row 2 fires at ANY population -- a repeat is decisive at n=1
    tiny = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(111)]
            + [_row([("c", 900)], [0], [900], faces=(8, 8, 8)),
               _row([("c", 901)], [0], [901], faces=(9, 9, 9))])
    v = solver_bar(tiny)
    assert v["verdict"] == "2 LATE ENFORCEMENT", v
    assert v["signed_population"] == 2 and "not 113" in v["note"]

    # row 4 is DECLINED when the signed population is too small
    thin = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(60)]
            + _spread(53, start=1000))
    v = solver_bar(thin)
    assert v["verdict"] == "ROWS 1 AND 3 ONLY -- ROW 4 DECLINED", v
    assert v["partial"] is True

    # row 4 is PARTIAL when the population is short of 113 but above the floor
    short = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(10)]
             + _spread(103, start=1000))
    v = solver_bar(short)
    assert v["verdict"] == "4 NEW TERRITORY" and v["partial"] is True
    assert "PARTIAL" in v["note"]

    # --- geometry bar, every row and the G1/G2 boundary -------------------
    # G1: few sites AND few causes
    g1 = [_row([("c", i)], [i % 7], [i], faces=((i % 5), 1, 2))
          for i in range(113)]
    v = geometry_bar(g1)
    assert v["verdict"] == "G1 LOCALISED", v
    assert v["distinct_core"] == 7 and v["distinct_faces"] == 5

    # G2 by the faces threshold alone: cores few, sites many
    g2 = [_row([("c", i)], [i % 7], [i], faces=(i, 1, 2)) for i in range(113)]
    v = geometry_bar(g2)
    assert v["verdict"] == "G2 BOUNDED", v
    assert v["distinct_core"] == 7 and v["distinct_faces"] == 113

    # G2 by the core threshold: 30 causes, in (CORE_LOCALISED, CORE_BOUNDED]
    g2b = [_row([("c", i)], [i % 30], [i], faces=(1, 2, 3))
           for i in range(113)]
    assert geometry_bar(g2b)["verdict"] == "G2 BOUNDED"

    # G3: many distinct causes even though every site is the same
    g3 = [_row([("c", i)], [i], [i], faces=(1, 2, 3)) for i in range(113)]
    v = geometry_bar(g3)
    assert v["verdict"] == "G3 DIFFUSE", v
    assert v["distinct_faces"] == 1 and "not exploitable" in v["note"]
    assert "confluent" in v["note"], "G3 must carry its own softness inline"

    # NO VERDICT below the floor
    nv = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(30)]
          + _spread(83, start=1000))
    v = geometry_bar(nv)
    assert v["verdict"] == "NO VERDICT" and v["core_population"] == 83
    assert "refused on 30 of 113" in v["note"]

    # PARTIAL above the floor but below 113
    pv = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(10)]
          + [_row([("c", 1000 + i)], [i % 7], [1000 + i], faces=(i % 5, 1, 2))
             for i in range(103)])
    v = geometry_bar(pv)
    assert v["verdict"] == "G1 LOCALISED" and v["partial"] is True
    assert "POPULATION IS 103, NOT 113" in v["note"]

    # --- the two floors are STRICT: exactly MIN_CORE_POPULATION verdicts --
    # `n < MIN_CORE_POPULATION` and `n <= MIN_CORE_POPULATION` differ at
    # exactly one value, so only a fixture sitting ON it can tell them apart.
    # Verified during planning: without these two cases the `<` -> `<=`
    # mutation survives the entire selftest.
    gfloor = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(23)]
              + [_row([("c", 1000 + i)], [i % 7], [1000 + i],
                      faces=(i % 5, 1, 2)) for i in range(90)])
    v = geometry_bar(gfloor)
    assert v["core_population"] == MIN_CORE_POPULATION, v["core_population"]
    assert v["verdict"] == "G1 LOCALISED", (
        "a core population of exactly MIN_CORE_POPULATION must still produce a "
        "verdict: the floor is `n < MIN_CORE_POPULATION`, not `<=`")

    sfloor = ([_row([("c", i)], None, [i], faces=(i, i, i)) for i in range(23)]
              + _spread(90, start=1000))
    v = solver_bar(sfloor)
    assert v["signed_population"] == MIN_CORE_POPULATION, v["signed_population"]
    assert v["verdict"] == "4 NEW TERRITORY", (
        "a signed population of exactly MIN_CORE_POPULATION must still reach "
        "row 4: the floor is `<`, not `<=`")
    assert v["partial"] is True

    # --- serialiser -------------------------------------------------------
    assert serialise(frozenset([(2, 1), (1, 2)])) == [[1, 2], [2, 1]]
    assert serialise(_W(faces=(3, 1, 2)))["faces"] == [3, 1, 2]
    assert serialise(None) is None

    # --- the constants are the spec's ------------------------------------
    assert (FACES_LOCALISED, CORE_LOCALISED, CORE_BOUNDED,
            MIN_CORE_POPULATION, EXPECTED_REJECTIONS) == (10, 20, 40, 90, 113)
    assert ARM_A["rejections"] == EXPECTED_REJECTIONS, (
        "the guard's rejection count and the bars' expected population are "
        "the same number and must not drift apart -- the predecessor's two "
        "clause-size constants drifted exactly this way")

    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    raise SystemExit("main() lands in Task 4; only --selftest exists yet")
```

- [ ] **Step 3: Run the selftest to verify it passes**

```bash
cd mcp_harness && ../.venv/bin/python3 ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py --selftest
```

Expected: `selftest OK`, exit 0.

- [ ] **Step 4: Verify the pre-registered mutations go RED**

Each of the eleven mutations below must make `--selftest` **fail**. A surviving mutation means the fixture is vacuous — the clause slice shipped a headline whose own mutant survived 52 tests, and that is how.

Apply each one, run the selftest, confirm it fails, then **revert it** before the next:

| # | mutation | file:symbol |
|---|---|---|
| 1 | `FACES_LOCALISED = 10` → `1000` | `identity113.py` |
| 2 | `CORE_LOCALISED = 20` → `2` | `identity113.py` |
| 3 | `CORE_BOUNDED = 40` → `400` | `identity113.py` |
| 4 | `MIN_CORE_POPULATION = 90` → `1` | `identity113.py` |
| 5 | `and` → `or` in `geometry_bar`'s G1 condition | `geometry_bar` |
| 6 | `population()` returns `rows` unfiltered | `population` |
| 7 | `ARM_A["rejections"] = 113` → `112` | `identity113.py` |
| 8 | `n < MIN_CORE_POPULATION` → `n <= MIN_CORE_POPULATION` in `geometry_bar` | `geometry_bar` |
| 8b | `n_signed < MIN_CORE_POPULATION` → `<=` in `solver_bar` | `solver_bar` |
| 9 | `chao1` returns `0.0` instead of `None` when `f2 == 0` | `chao1` |
| 10 | `SOLVER_ROWS` reordered to put `signed` first | `identity113.py` |

Run, for each:

```bash
cd mcp_harness && ../.venv/bin/python3 ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py --selftest; echo "exit=$?"
```

Expected per mutation: an `AssertionError` and `exit=1`.

**All eleven were verified RED during planning**, by extracting this file's code from this plan and executing each mutation against the selftest. Mutation 8 **survived the first time**: `n < 90` → `n <= 90` differs at exactly `n == 90` and no fixture sat there. The two floor fixtures (`gfloor`, `sfloor`) were added for that reason and kill both 8 and 8b. If any mutation comes back green for you, the fixture is vacuous — report it rather than adjusting the mutation.

- [ ] **Step 5: Record the mutation results**

Report all eleven as a table: mutation, selftest outcome, and which assertion caught it. Any mutation that survived must be named with the fixture added to kill it.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t3-msg.txt
```

`t3-msg.txt`:

```
witness-identity: the guard and both pre-registered bars, with their selftest

The solver bar is the predecessor's verbatim -- only the population changes,
3 -> 113 -- because its outcome is now known and a bar re-chosen with that
knowledge is not a bar. The geometry bar is new and its thresholds come from
figures that existed before the run: 31/31 rejections are taco_tortilla among
exactly 3 faces, cores are 4-8 with max 8 observed, and the dense candidate
has 745 creases.

population() excludes refused extractions rather than counting None as a
value -- a None would fabricate one shared cause across every refusal and
understate distinctness exactly where the geometry bar reads it.

G3 carries its own softness inline: _propagate is not confluent, so
distinctness may be derivational rather than geometric, and G3 licenses
"repeats are not exploitable through this instrument" and not "the geometry
is fine".

Eleven pre-registered mutations verified RED, including the two
floor-boundary cases that the first mutation pass showed were missing.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

### Task 4: `main()`, the run, and the README

**Files:**
- Modify: `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py` (add `main()`, replace the `__main__` stub)
- Create: `docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.json` (generated)
- Create: `docs/superpowers/evidence/2026-10-02-witness-identity-113/README.md`

**Interfaces:**
- Consumes: everything Task 3 produced, and `compile_tree(..., dense=True, core_extraction=False, core_record=True, assign_budget=500_000, debug_clause_sizes=<list>, debug_cores=<list>, debug_witness_cores=<list>)` from Task 1.
- Produces: the artifact and the report. Nothing consumes them.

**Do not start this task until Task 2's gate has passed.**

- [ ] **Step 1: Add `main()`**

In `identity113.py`, replace the `if __name__ == "__main__":` block with:

```python
# -------------------------------------------------------------------- main

# The same fixture the tests use, reached the way the predecessor evidence
# script reaches it (`../2026-09-28-witness-identity/identity.py:68`): a
# self-contained path relative to `mcp_harness`, NOT an import from the test
# package. An evidence script that imports from `tests/` silently acquires that
# package's conftest and sys.path assumptions, and is then only runnable under
# pytest's path setup rather than by the command printed in its own README.
RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data",
                     "rule6_serve.json")


def _subject_entry():
    import json as _json
    with open(RULE6) as fh:
        return next(e for e in _json.load(fh) if e["subject"] == "lizard")


def main(out_path):
    import json as _json
    import time as _time
    from box_pleat.compile import compile_tree

    e = _subject_entry()
    clauses, core_rows, rows = [], [], []
    t0 = _time.perf_counter()
    res = compile_tree(e["requested"], e["pairs"], dense=True,
                       assign_budget=500_000, core_extraction=False,
                       core_record=True, debug_clause_sizes=clauses,
                       debug_cores=core_rows, debug_witness_cores=rows)
    secs = round(_time.perf_counter() - t0, 1)

    rec = {
        "subject": "lizard",
        "arm": "A + core_record (diagnostic-only extraction)",
        "arm_a_expected": ARM_A,
        "assign_budget": 500_000,
        "stage_reached": res.stage_reached,
        "failure": repr(res.failure),
        "layer_verdict": repr(res.verdict),
        "layers_tried": res.layers_tried,
        "rejections": len(clauses),
        "records": len(rows),
        "secs": secs,
        # The full population, so a successor can guard it EXACTLY -- the
        # weakness this guard inherits is that arm A published only a
        # min/median/max (spec 5.6).
        "clause_sizes": sorted(clauses),
        "core_rows": [list(r) for r in core_rows],
    }

    refusals = [r["core_error"] for r in rows if r["core_error"] is not None]
    rec["core_refusals"] = len(refusals)
    rec["core_refusal_messages"] = sorted(set(refusals))
    if refusals:
        print(f"!!! CORE EXTRACTION REFUSED on {len(refusals)} of "
              f"{len(rows)} rejections. The geometry bar's population is "
              f"{len(rows) - len(refusals)}, not {len(rows)}.")
        for m in sorted(set(refusals)):
            print(f"!!!   {m}")

    passed, bad = guard(rec["rejections"], rec["layers_tried"],
                        rec["failure"], clauses, rec["records"])
    rec["guard_passed"] = passed
    rec["guard_mismatches"] = bad
    print(f"stage={rec['stage_reached']} failure={rec['failure']} "
          f"rejections={rec['rejections']} records={rec['records']} "
          f"secs={secs}")
    if not passed:
        rec["solver_bar"] = {"verdict": "GUARD FAILED"}
        rec["geometry_bar"] = {"verdict": "GUARD FAILED"}
        print("GUARD FAILED -- NO VERDICT from either bar:")
        for b in bad:
            print(f"  {b}")
    else:
        rec["solver_bar"] = solver_bar(rows)
        rec["geometry_bar"] = geometry_bar(rows)
        print(f"SOLVER BAR: {rec['solver_bar']['verdict']}")
        print(f"GEOMETRY BAR: {rec['geometry_bar']['verdict']}")
        for b in (rec["solver_bar"], rec["geometry_bar"]):
            if b.get("note"):
                print(f"  note: {b['note']}")

    rec["distinct"] = {lv: distinct(rows, lv) for lv in LEVELS}
    rec["populations"] = {lv: len(population(rows, lv)) for lv in LEVELS}
    rec["repeats"] = {lv: {str(serialise(v)): idx
                           for v, idx in repeats(rows, lv).items()}
                      for lv in LEVELS}
    rec["multiplicity_histogram"] = {
        lv: _histogram(multiplicity(rows, lv)) for lv in LEVELS}
    rec["chao1_reference"] = {lv: chao1(multiplicity(rows, lv))
                              for lv in LEVELS}
    rec["top5"] = {lv: _top5(multiplicity(rows, lv), len(rows))
                   for lv in LEVELS}
    rec["overlaps"] = {lv: overlaps(rows, lv)
                       for lv in ("candidate", "core", "signed", "keys",
                                  "core_keys")}
    rec["rejection_records"] = [
        {lv: serialise(value_at(r, lv)) for lv in LEVELS}
        | {"core_error": r["core_error"]} for r in rows]

    print("distinct: " + "  ".join(
        f"{lv}={rec['distinct'][lv]}/{rec['populations'][lv]}"
        for lv in LEVELS))
    for lv in LEVELS:
        for v, idx in rec["repeats"][lv].items():
            print(f"REPEAT at {lv}: rows {idx} share {v[:120]}")

    with open(out_path, "w") as fh:
        _json.dump(rec, fh, indent=1, sort_keys=True)
    print(f"wrote {out_path}")


def _histogram(mult: dict) -> dict:
    """multiplicity -> how many values occur that many times. f1 is key "1"."""
    out = {}
    for c in mult.values():
        out[str(c)] = out.get(str(c), 0) + 1
    return out


def _top5(mult: dict, total: int) -> dict:
    """The five most frequent values and the share of `total` they cover."""
    top = sorted(mult.items(), key=lambda kv: -kv[1])[:5]
    covered = sum(c for _, c in top)
    return {"counts": [c for _, c in top],
            "values": [serialise(v)[:40] if isinstance(serialise(v), list)
                       else serialise(v) for v, _ in top],
            "covered": covered,
            "share_of_total": (None if not total
                               else round(covered / total, 4))}


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit(0)
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: identity113.py <out.json> | identity113.py --selftest")
    main(sys.argv[1])
```

- [ ] **Step 2: Re-run the selftest**

```bash
cd mcp_harness && ../.venv/bin/python3 ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py --selftest
```

Expected: `selftest OK`, exit 0. (`main()` and its two helpers are additions; the selftest must still pass unchanged.)

- [ ] **Step 3: Smoke the whole script at a small budget**

Before spending ~47 minutes, confirm `main()` runs end to end. Temporarily change `assign_budget=500_000` to `assign_budget=20_000` in `main()`, run it to a scratch path, then **change it back**:

```bash
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/smoke.json
```

Expected: it prints `GUARD FAILED` (20,000 nodes cannot produce 113 rejections — that is correct behaviour, and it confirms the guard refuses rather than defaults), writes the JSON, and exits 0. Confirm the JSON contains non-empty `rejection_records`, `distinct`, `populations` and `multiplicity_histogram`.

**Then restore `assign_budget=500_000` and confirm with `grep -n "assign_budget" identity113.py`.** Shipping the smoke budget would silently produce a guard-failed run.

- [ ] **Step 4: Run the measurement**

```bash
cd mcp_harness && PYTHONPATH=. nohup ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.py ../docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.json > <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/run.log 2>&1 &
```

Expected: ~35–70 minutes (spec §7's estimate band). Poll the log; do not re-run it concurrently. Record the exit status and the commit SHA the run was launched on — `identity113.py` writes neither into the JSON, which is a defect the predecessor recorded against itself and the README must carry instead.

**Do not modify `identity113.py` at any point during or after the run.** Byte-identical reproducibility is what makes the result checkable.

- [ ] **Step 5: Read the verdict from the artifact, not the log**

```bash
cd <repo> && .venv/bin/python3 -c "
import json
d = json.load(open('docs/superpowers/evidence/2026-10-02-witness-identity-113/identity113.json'))
for k in ('guard_passed','guard_mismatches','rejections','records','secs',
          'core_refusals','solver_bar','geometry_bar','distinct','populations'):
    print(k, '=', json.dumps(d[k])[:300])
"
```

Every figure in the README comes from this re-read of the written file, never from the log watched while it ran.

- [ ] **Step 6: Write the README**

Create `docs/superpowers/evidence/2026-10-02-witness-identity-113/README.md` containing, in this order:

1. **The question**, and the one-line reason this run exists: the predecessor measured identity on 3 rejections and called the result weak; this measures it on 113.
2. **The reproduction command**, verbatim, plus the run date, the commit SHA, the exit status, and the statement that `--selftest` passed immediately before and that the script was not modified during or after. Say explicitly that date/commit/exit are the README's own record because the script writes none of them into the JSON.
3. **The guard table** — expected (from `arm_a_expected`) beside measured, every row, PASS/FAIL. State §5.6's weakness: arm A published only a min/median/max, so this guard is weaker than arm B's, and this run publishes its full 113-value `clause_sizes` so a successor can guard exactly.
4. **Both verdicts**, each with its population named, and each `note` quoted in full.
5. **The multiplicity tables** — histogram, top-5 coverage with its share, `f1`/`f2`, and the Chao1 reference with its independence caveat attached **on every appearance**.
6. **Every repeat, printed in full** — or the explicit sentence that there are none, as the predecessor did.
7. **The pairwise overlap table**, with the "distinct is not disjoint" reading stated before a reader finds it unaided.
8. **The `core_keys` counterfactual** (spec §5.3) and its limit: this is arm A's trajectory under counterfactual narrowing, not arm B's actual trajectory.
9. **Limits** (spec §8), in full: one subject, one arm, one budget, and the G1-robust / G3-soft asymmetry.
10. **Cost**, measured, against spec §7's ~47-minute estimate — and whether the estimate held.

**Rules for the prose, each of which this project has violated before:**
- Attribute every figure taken from another evidence directory inline, **on every appearance**.
- Mark every figure obtained by arithmetic as *derived* and show the derivation.
- Never state a count as "N subjects" when N is the row count; lizard can contribute more than one row.
- A share whose denominator is 0 is **undefined**, not 100%.
- If the geometry bar returned **G3**, the README's headline must carry the softness inline, not in a footnote.

- [ ] **Step 7: Verify every README figure against the artifact**

For each number in the README, name its source: a JSON key, another evidence directory with its path, or a marked derivation. Report any figure that cannot be sourced — and remove it rather than leaving it uncited.

- [ ] **Step 8: Commit**

```bash
git add docs/superpowers/evidence/2026-10-02-witness-identity-113/ && git commit -F <scratch>/9681b5fb-8510-4f03-86c1-4e4b6d0a887a/scratchpad/t4-msg.txt
```

`t4-msg.txt` — fill `<SOLVER>` and `<GEOMETRY>` with the measured verdicts:

```
evidence: witness identity on 113 rejections -- <SOLVER> / <GEOMETRY>

The predecessor measured rejection identity on the 3-rejection arm and said so
plainly: three distinct is equally consistent with a loop that would begin
repeating at rejection 20. This runs the same question on 113.

Diagnostic-only extraction: the search received the unshrunk cone keys, so the
committed arm-A structure is preserved and the guard checks it, while the
record carries the true minimal cause.

Both bars were pre-registered before the run. The artifact carries the guard,
both verdicts with their populations, the multiplicity tables, every repeat in
full, and all 113 records.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## Self-Review

**1. Spec coverage.**

| spec section | task |
|---|---|
| §0 prior art | recorded in the spec; `cores.py` and `identity.py` untouched (Global Constraints) |
| §3 `core_record` three-way table | Task 1 Steps 3, 7 |
| §3.1 non-interference | Task 1 Step 1 (sparse A/A), Task 2 (dense A/A) |
| §3.2 control path unchanged | Task 1 Steps 6, 8a, 8b, the five-key test in Step 1, and Step 11's three suites. **Deviation:** the spec proposed a duplicated call site; pre-flight review replaced it with the shared `_extract_core(catch=...)`, so the delivered claim is behaviour-identical-and-tested rather than code-untouched. |
| §4 catch / record / count / continue | Task 1 Step 7; printing relocated to Task 4 Step 1 (deviation recorded in Global Constraints) |
| §5.1 record fields | Task 1 Steps 6, 7 |
| §5.2 solver bar verbatim | Task 3 `solver_bar` |
| §5.3 `core_keys` counterfactual | Task 1 Step 7; Task 4 Step 6 item 8 |
| §5.4 geometry bar + tables | Task 3 `geometry_bar`, `multiplicity`, `chao1`, `overlaps`; Task 4 Step 6 item 5 |
| §5.5 invalidity 1–5 | Task 3 `guard` + both bars' population gates; condition 5 is Task 2 being a blocking gate |
| §5.6 guard weakness + full population published | Task 3 `guard` docstring; Task 4 `main()` writes `clause_sizes`; README item 3 |
| §6.1 A/A | Task 2 |
| §6.2 behavioural tests | Task 1 Step 1 |
| §6.3 mutations | Task 3 Step 4 |
| §6.4 inherited instrument defects | Task 4 `main()` interpolates every printed figure; `selftest` asserts `ARM_A["rejections"] == EXPECTED_REJECTIONS` |
| §7 cost | Task 4 Step 6 item 10 |
| §8 limits | Task 4 Step 6 item 9; G3's softness inline in `geometry_bar` |
| §9 files | the File Structure table |
| §10 out of scope | no task touches `assign.py`, a second subject, or a second budget |

**No gaps.**

**2. Placeholder scan.** Every code step carries complete code. The two `<SOLVER>`/`<GEOMETRY>` placeholders in Task 4's commit message are values that cannot exist before the run, and the step says where they come from. Task 1 Step 11's conditional (`if that file does not exist`) is a lookup instruction with the exact commands, not a deferred decision.

**3. Type consistency.** `_identity_record(labels, w, core, keys)` is defined in Task 1 Step 6 and called in Steps 7 and 8 with that arity. The record keys in Task 1 (`core_keys`, `core_error`) match `LEVELS` and `value_at` in Task 3 and `rejection_records` in Task 4. `guard(...)` is defined with five parameters in Task 3 and called with five in Task 4. `solver_bar`/`geometry_bar` return dicts whose `"verdict"`, `"note"`, `"partial"`, `"core_population"`, `"signed_population"` keys are read in Task 4's `main()`. `population`/`distinct`/`multiplicity`/`repeats` all take `(rows, level)`. `chao1(mult)` takes the multiplicity dict, and `main()` passes `multiplicity(rows, lv)`.

One inconsistency found and fixed while reviewing: `main()` originally called `distinct(rows)` returning a dict over all levels, the predecessor's shape, while Task 3 defines `distinct(rows, level) -> int`. `main()` now builds the dict with a comprehension.

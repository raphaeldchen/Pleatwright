# P2 (specify and search) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an LLM supply the *objective* (an auditable anatomy specification) while deterministic search supplies every *knob value*, and widen extraction's grid to hunt for cells that satisfy that objective.

**Architecture:** Three components from the spec's §9–§11, in dependency order. U2 writes an anatomy spec and must first repair two report/provenance defects that would otherwise launder a model guess as human-authored ground truth. U4 consumes that spec to widen and rank the extraction sweep. U3 is **measurement-gated**: a global framing change was already refuted on this repo, so U3 re-measures per-subject framing against what currently ships and only wires anything if it clears the bar that killed the global version.

**Tech Stack:** Python 3.14, pytest, the vendored TreeMaker C++ extension via `headless_treemaker`, Anthropic via `llm_client.py`. No new dependencies.

## Global Constraints

Copied verbatim from the spec and CLAUDE.md. Every task's requirements implicitly include this section.

- **No LLM output is ever a voxel resolution, a prune fraction, or any other numeric search parameter.** (spec §1.4)
- **Every model row must carry a derivation AND a citation. A row missing either is DISCARDED, not downgraded.** (spec §9)
- **`hull_coverage` is deliberately NOT a ranking key** and must not become one. `stub_flaps` outranks `design_scale`. (CLAUDE.md §1.1)
- **A bar written after seeing numbers is not a bar.** Every pre-registered bar in this plan is stated before its probe runs and must not be edited afterwards.
- **Offline degradation is mandatory.** With no API key, every unit returns exactly what it returns today, byte-identically.
- **The named recurring failure mode is "an instrument that reads green for the wrong reason."** Every test in this plan must be mutation-verified: break the code it guards and confirm the test goes red.
- Do not modify `vlm_judge.py` or `order_rank.py`.
- `MIN_LEAVES, MAX_LEAVES = 4, 8` (`mesh_to_tree.py:510`) is **not** to be changed by this plan.

---

## Setup

Work in a git worktree off `main`. Four gitignored build artifacts do not exist in a fresh worktree and must be symlinked from the parent checkout, or ~35 tests fail for reasons unrelated to your change:

```bash
cd <repo>
git worktree add .claude/worktrees/p2-specify-and-search -b claude/p2-specify-and-search main
cd .claude/worktrees/p2-specify-and-search/mcp_harness
ln -sf ../../../mcp_harness/headless_treemaker.cpython-314-darwin.so .
ln -sf ../../../mcp_harness/oriedita/*.jar oriedita/
ln -sf ../../../mcp_harness/OrieditaValidator.class .
ln -sf ../../../.env ../.env
```

⚠ The `.so` is a **symlink into the parent checkout**. `make`'s build step writes *through* it, mutating an artifact every other worktree shares. Prefer targeted `pytest` runs (below) over `make test` unless you specifically intend to rebuild.

### Verification protocol (CI cannot be relied on)

CI has never completed this suite. It dies with `exit 143` inside
`mcp_harness/tests/test_provider_variation.py`; billing was checked on
2026-09-02 and **ruled out** (minutes not exhausted, $20 limit not reached,
payment good), so the mechanism is open. **Do not wait for a green CI run.**

Each task claims exactly one of two things, and must say which:

1. **Inertness** — with the feature off / no API key, output is byte-identical on a pinned artifact set. Fully checkable locally.
2. **Confinement** — with the feature on, movement is confined to a named blast radius, measured against a frozen baseline, and attributed to this task.

Run targeted subsets in **one process** (never split across processes — that hides cross-test state leaks, which is how the `_last_stitch_evidence` bug survived):

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_anatomy_expectation.py tests/test_mesh_report.py tests/test_r_prepass.py -v
```

---

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/mesh_report.py` (modify) | Fix `_provenance_lines`' hardcoded dispatch; strengthen the import assert to cover it. |
| `mcp_harness/mesh_to_tree.py` (modify) | Accept and stamp a provenance alongside `reference_count=`; widen the voxel grid; rank cells against the spec. |
| `mcp_harness/anatomy_spec.py` (create) | U2. `anatomy_spec(prompt)` — table-first, model-second, disk-cached, discards uncited rows. |
| `mcp_harness/probe_framing_lever.py` (create) | U3's gate. Re-measures per-subject framing against HEAD's shipped suffix. |
| `mcp_harness/tests/test_provenance_dispatch.py` (create) | Guards Task 1: every provenance key gets its own caveat, proved by mutation. |
| `mcp_harness/tests/test_anatomy_spec.py` (create) | Guards Tasks 2–3: seam provenance, discard-without-citation, offline inertness. |
| `mcp_harness/tests/test_search_extraction.py` (create) | Guards Tasks 4–5: grid floor, budget, spec ranking, and the clamp's consequence. |

---

## Task 1: Repair the provenance dispatch that fails green

The spec's original mitigation for adding an `"llm"` provenance — put the key in both dicts — passes the import assert and still prints the wrong caveat, because `_provenance_lines` dispatches on a hardcoded tuple. Fix that before anything can stamp `"llm"`.

**Files:**
- Modify: `mcp_harness/mesh_report.py:224-226` (the assert), `mesh_report.py:242-251` (`_provenance_lines`)
- Test: `mcp_harness/tests/test_provenance_dispatch.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `mesh_report._PROVENANCE_CAVEAT` and `_R_SOURCE` gain the key `"llm"`; `_provenance_lines(result) -> list` returns that key's own caveat rather than the self-derived one.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_provenance_dispatch.py`:

```python
"""Every r_provenance must print ITS OWN caveat.

The pair (_PROVENANCE_CAVEAT, _R_SOURCE) exists so a report never labels R's
source one way and caveats it another. The import assert at mesh_report.py:224
only proves the two dicts have the same KEYS -- it does not prove the renderer
reads them. Before this test, _provenance_lines dispatched on a hardcoded
tuple, so a fourth key passed the assert and printed the self-derived caveat:
the exact contradiction the pair was added to remove, with every guard green.
"""
import mesh_report
from mesh_to_tree import MeshTreeResult

_NODES = [{"id": 0, "parent_id": None, "length": 0},
          {"id": 1, "parent_id": 0, "length": 0.3}]


def _result(prov, *, key="r_provenance"):
    """A served result whose CHOSEN trace row carries `prov`.

    ⚠ Must be a real MeshTreeResult, not a dict. `_chosen_row`
    (mesh_report.py:96-107) reads `result.trace` by ATTRIBUTE and then matches
    the row on BOTH voxel_res and prune, so a plain dict -- or a row missing
    those keys -- silently yields None and EVERY provenance resolves to
    "self-derived", making these tests unable to fail. An earlier draft of
    this plan used a plain dict; mutation proved the assertion output was
    byte-identical with the dispatch bug present and absent.
    """
    row = {"voxel_res": 96, "prune": 0.55}
    if prov is not None:
        row[key] = prov
    return MeshTreeResult(
        confirmed=True, nodes=_NODES, pairs=[],
        voxel_res=96, prune_fraction=0.55, gate={}, trace=[row])


def test_every_declared_provenance_prints_its_own_caveat():
    for prov in mesh_report._PROVENANCE_CAVEAT:
        lines = mesh_report._provenance_lines(_result(prov))
        assert lines == [mesh_report._PROVENANCE_CAVEAT[prov]], (
            f"{prov!r} printed another key's caveat: {lines!r}")


def test_the_fixture_can_actually_carry_a_provenance():
    # Guards the defect that motivated this fixture: if _chosen_row stops
    # seeing the row, every test above passes vacuously by falling through to
    # self-derived. Pin a NON-default value end to end.
    assert mesh_report._r_provenance(_result("external")) == "external"


def test_an_unrecorded_provenance_still_gets_the_self_derived_caveat():
    # Silence must never buy the flattering label -- an absent field and a
    # plateau vote carry the identical risk.
    for absent in (_result(None), _result("not-a-real-key")):
        assert mesh_report._provenance_lines(absent) == [
            mesh_report._PROVENANCE_CAVEAT["self-derived"]]


def test_llm_is_a_declared_provenance_with_both_a_caveat_and_a_source():
    assert "llm" in mesh_report._PROVENANCE_CAVEAT
    assert "llm" in mesh_report._R_SOURCE
    assert mesh_report._R_SOURCE["llm"] != mesh_report._R_SOURCE["external"], (
        "an LLM row must not be labelled as the human-authored table")
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_provenance_dispatch.py -v
```

Expected: `test_every_declared_provenance_prints_its_own_caveat` FAILS (`max-over-voxels` passes, but the loop proves nothing yet), and `test_llm_is_a_declared_provenance...` FAILS with `KeyError`/`assert 'llm' in ...`.

- [ ] **Step 3: Add the `llm` key to both dicts**

In `mesh_report.py`, add to `_PROVENANCE_CAVEAT` (beside the existing three):

```python
    "llm": ("⚠ R CAME FROM A LANGUAGE MODEL, NOT FROM A MEASUREMENT. The row "
            "carries a derivation and a citation and was accepted only "
            "because it carried both -- but no human checked it, and it is "
            "NOT the hand-authored anatomy table."),
```

and to `_R_SOURCE`:

```python
    "llm": "language-model anatomy row",
```

- [ ] **Step 4: Make the renderer dispatch on the dict**

Replace `_provenance_lines`' body (`mesh_report.py:249-251`):

```python
    prov = _r_provenance(result)
    return [_PROVENANCE_CAVEAT[prov]]
```

`_r_provenance` already falls back to `"self-derived"` for any key not in `_PROVENANCE_CAVEAT`, so the lookup cannot raise and the unrecorded-provenance behaviour is unchanged.

- [ ] **Step 5: Strengthen the import assert so this cannot regress**

Replace the assert at `mesh_report.py:224-226`:

```python
assert set(_R_SOURCE) == set(_PROVENANCE_CAVEAT), (
    "every r_provenance needs BOTH a caveat and a source label: "
    f"{set(_R_SOURCE) ^ set(_PROVENANCE_CAVEAT)}")
#: ⚠ AND the renderer must READ the dict, not a hardcoded list. The assert
#: above passed for a fourth key while `_provenance_lines` routed it to the
#: self-derived caveat via `if prov in ("external", "max-over-voxels")`, which
#: is the contradiction this pair exists to remove, reintroduced under a new
#: key with every guard green. Measured 2026-09-02. Keep the dispatch
#: dict-driven; `tests/test_provenance_dispatch.py` proves it by mutation.
```

- [ ] **Step 6: Run the tests and the surrounding suite**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_provenance_dispatch.py tests/test_mesh_report.py tests/test_anatomy_expectation.py -v
```

Expected: all PASS. `tests/test_anatomy_expectation.py:730-741` (the assert's test twin) must still pass — it asserts key-set equality, which the new key preserves on both sides.

- [ ] **Step 7: Mutation-verify the new test can fail**

Temporarily restore the hardcoded tuple in `_provenance_lines`:

```python
    if prov in ("external", "max-over-voxels"): return [_PROVENANCE_CAVEAT[prov]]
    return [_PROVENANCE_CAVEAT["self-derived"]]
```

Run: `PYTHONPATH=.:tests python -m pytest tests/test_provenance_dispatch.py -v`
Expected: `test_every_declared_provenance_prints_its_own_caveat` FAILS naming `'llm'`. **Restore the fix and re-run to green before committing.** Record both readings in the commit message.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/mesh_report.py mcp_harness/tests/test_provenance_dispatch.py
git commit -m "fix(mesh_report): every provenance prints its OWN caveat, not a hardcoded arm"
```

---

## Task 2: Carry provenance through the extraction seam

Today `reference_count is not None` unconditionally stamps `"external"`, which renders as *"human-authored anatomy table."* An LLM row handed to that seam is laundered as human-authored. Widen the seam.

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py:2710-2713` (signature), `mesh_to_tree.py:3048-3051` (the stamp)
- Test: `mcp_harness/tests/test_anatomy_spec.py`

**Interfaces:**
- Consumes: `mesh_report._PROVENANCE_CAVEAT` keys from Task 1.
- Produces: `auto_mesh_to_metric_tree(path, *, gate=None, compile_fn=None, voxel_grid=VOXEL_GRID, prune_grid=PRUNE_GRID, k=SEARCH_K, reference_count=None, reference_provenance="external")`. Keyword-only, defaulting to `"external"` so every existing caller is byte-identical.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_anatomy_spec.py`:

```python
"""U2's seam: an LLM-supplied R must never be stamped as human-authored."""
import inspect
import mesh_to_tree
import mesh_report


def test_reference_provenance_is_keyword_only_and_defaults_to_external():
    sig = inspect.signature(mesh_to_tree.auto_mesh_to_metric_tree)
    p = sig.parameters["reference_provenance"]
    assert p.kind is inspect.Parameter.KEYWORD_ONLY
    assert p.default == "external", (
        "the default must reproduce today's behaviour byte-identically")


def test_only_declared_provenances_are_accepted():
    sig = inspect.signature(mesh_to_tree.auto_mesh_to_metric_tree)
    assert "reference_provenance" in sig.parameters
    # The validator must reject anything mesh_report cannot caption.
    assert mesh_to_tree._validated_provenance("llm") == "llm"
    assert mesh_to_tree._validated_provenance("external") == "external"
    for bad in ("HUMAN", "", None, "made-up"):
        try:
            mesh_to_tree._validated_provenance(bad)
        except ValueError:
            continue
        raise AssertionError(f"{bad!r} was accepted but has no caveat")


def test_every_accepted_provenance_has_a_caveat_and_a_source():
    for key in mesh_to_tree._ACCEPTED_PROVENANCE:
        assert key in mesh_report._PROVENANCE_CAVEAT
        assert key in mesh_report._R_SOURCE
```

- [ ] **Step 2: Run it and watch it fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_anatomy_spec.py -v
```

Expected: FAIL — `KeyError: 'reference_provenance'` and `AttributeError: module 'mesh_to_tree' has no attribute '_validated_provenance'`.

- [ ] **Step 3: Add the validator**

Near `mesh_to_tree.py`'s other module constants (beside `MIN_LEAVES, MAX_LEAVES` at `:510`):

```python
#: R's provenance values this module is allowed to stamp. Kept in step with
#: mesh_report._PROVENANCE_CAVEAT deliberately: a value with no caveat prints
#: the self-derived warning above a contradicting source label, which is the
#: defect Task 1 repaired. "max-over-voxels" is excluded because nothing
#: writes it (tests/test_r_prepass.py:904-920 asserts that on purpose).
_ACCEPTED_PROVENANCE = ("external", "llm")


def _validated_provenance(value) -> str:
    """Reject anything the report cannot caption, loudly and at the call."""
    if value not in _ACCEPTED_PROVENANCE:
        raise ValueError(
            f"reference_provenance must be one of {_ACCEPTED_PROVENANCE}, "
            f"got {value!r} -- an uncaptioned provenance would print the "
            f"self-derived caveat under another source label")
    return value
```

- [ ] **Step 4: Widen the signature and the stamp**

At `mesh_to_tree.py:2710-2713`, add the parameter at the end of the keyword-only block:

```python
def auto_mesh_to_metric_tree(path, *, gate=None, compile_fn=None,
                             voxel_grid=VOXEL_GRID, prune_grid=PRUNE_GRID,
                             k=SEARCH_K, reference_count=None,
                             reference_provenance="external"):
```

At `mesh_to_tree.py:3048-3051`, stamp the validated value instead of the literal. **Keep this as its own pass after the annotation loop — the comment at `:3036-3047` says ORDER IS LOAD-BEARING and folding it back in would let F4's literal clobber it:**

```python
        if reference_count is not None:
            prov = _validated_provenance(reference_provenance)
            for row in trace:
                if row["voxel_res"] == voxel_res and row["verdict"] != "empty":
                    row["r_provenance"] = prov
```

- [ ] **Step 5: Run the tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_anatomy_spec.py tests/test_anatomy_expectation.py tests/test_r_prepass.py -v
```

Expected: all PASS. `tests/test_anatomy_expectation.py:277-305` (which asserts every row reads `r_provenance == "external"` on the authored path) must still pass unchanged — the default preserves it.

- [ ] **Step 6: Mutation-verify**

Change the default to `"llm"` and run `tests/test_anatomy_expectation.py -v`.
Expected: the `"external"` assertions at `:277-305` go RED, proving they see the stamp. **Restore `"external"` and re-run to green.**

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_anatomy_spec.py
git commit -m "feat(U2): the extraction seam carries R's provenance, not just its value"
```

---

## Task 3: `anatomy_spec(prompt)` — the model row itself

**Files:**
- Create: `mcp_harness/anatomy_spec.py`
- Modify: `mcp_harness/tests/test_anatomy_spec.py` (append)

**Interfaces:**
- Consumes: `mesh_to_tree._ACCEPTED_PROVENANCE` (Task 2); `anatomy_expectation.expectation_for(prompt)` and `normalize_prompt(prompt)` (existing, `anatomy_expectation.py:128`, `:97`).
- Produces: `anatomy_spec(prompt, *, client=None, cache_path=None) -> dict | None`, returning `{"expected_feature_count": int, "derivation": str, "citation": str, "provenance": "external" | "llm"}` or `None`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_anatomy_spec.py`:

```python
import anatomy_spec


class _FakeClient:
    """Records calls so a test can prove the model was NOT consulted."""
    def __init__(self, reply): self.reply, self.calls = reply, 0
    def complete(self, prompt):
        self.calls += 1
        return self.reply


def test_a_table_hit_never_consults_the_model(tmp_path):
    client = _FakeClient('{"expected_feature_count": 99, '
                         '"derivation": "x", "citation": "y"}')
    got = anatomy_spec.anatomy_spec(
        "a bird", client=client, cache_path=tmp_path / "c.json")
    assert client.calls == 0, "the authored row must win outright"
    assert got["provenance"] == "external"


def test_no_model_and_no_table_row_returns_None(tmp_path):
    got = anatomy_spec.anatomy_spec(
        "a wholly unknown creature", client=None,
        cache_path=tmp_path / "c.json")
    assert got is None, "offline must degrade to exactly today's behaviour"


def test_a_row_without_a_citation_is_DISCARDED_not_downgraded(tmp_path):
    client = _FakeClient('{"expected_feature_count": 7, '
                         '"derivation": "four legs, tail, head, snout"}')
    got = anatomy_spec.anatomy_spec(
        "a wholly unknown creature", client=client,
        cache_path=tmp_path / "c.json")
    assert got is None, "an uncited row must not be kept at lower confidence"


def test_a_row_without_a_derivation_is_DISCARDED(tmp_path):
    client = _FakeClient('{"expected_feature_count": 7, "citation": "Lang"}')
    got = anatomy_spec.anatomy_spec(
        "a wholly unknown creature", client=client,
        cache_path=tmp_path / "c.json")
    assert got is None


def test_a_complete_model_row_is_stamped_llm_and_cached(tmp_path):
    cache = tmp_path / "c.json"
    reply = ('{"expected_feature_count": 7, "derivation": "4 legs + tail + '
             'head + snout", "citation": "Lang, Origami Design Secrets 2e"}')
    client = _FakeClient(reply)
    got = anatomy_spec.anatomy_spec(
        "a wholly unknown creature", client=client, cache_path=cache)
    assert got == {"expected_feature_count": 7,
                   "derivation": "4 legs + tail + head + snout",
                   "citation": "Lang, Origami Design Secrets 2e",
                   "provenance": "llm"}
    assert cache.exists(), "the row must be auditable without a rerun"
    again = anatomy_spec.anatomy_spec(
        "a wholly unknown creature", client=client, cache_path=cache)
    assert client.calls == 1, "a cached row must not re-spend a call"
    assert again == got


def test_the_count_must_be_a_positive_int(tmp_path):
    for bad in ('{"expected_feature_count": 0, "derivation": "d", "citation": "c"}',
                '{"expected_feature_count": -3, "derivation": "d", "citation": "c"}',
                '{"expected_feature_count": "seven", "derivation": "d", "citation": "c"}',
                'not json at all'):
        got = anatomy_spec.anatomy_spec(
            "a wholly unknown creature", client=_FakeClient(bad),
            cache_path=tmp_path / f"{abs(hash(bad))}.json")
        assert got is None, f"{bad!r} must be discarded"
```

- [ ] **Step 2: Run and watch them fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_anatomy_spec.py -v -k "table_hit or DISCARDED or stamped or positive or no_model"
```

Expected: FAIL with `ModuleNotFoundError: No module named 'anatomy_spec'`.

- [ ] **Step 3: Implement**

Create `mcp_harness/anatomy_spec.py`:

```python
"""U2 -- an auditable anatomy specification for any prompt.

Extends the 14-row authored table (fixtures/anatomy_expectation.json) to
prompts it does not cover, WITHOUT ever letting a model guess masquerade as a
measurement. Three rules, in priority order:

  1. Table hit  -> the authored row wins and the model is never consulted.
     Hand-authored rows are stronger evidence and cheaper.
  2. Table miss + a model -> a model row, but ONLY if it carries both a
     derivation and a citation. A row missing either is DISCARDED, not kept at
     lower confidence: the whole value of this file is that every number can be
     audited without rerunning anything.
  3. Table miss + no model -> None, byte-identical to today.

The returned row carries `provenance`, which callers pass to
`mesh_to_tree.auto_mesh_to_metric_tree(reference_provenance=...)`. That is not
decoration: without it the seam stamps "external", which mesh_report renders as
"human-authored anatomy table", and a model guess is laundered as ground truth.

⚠ The row shape is THREE fields plus provenance. `named_parts` and
`expected_pairs` do NOT exist in the authored fixture -- an earlier draft of
the spec claimed they did. Do not add them here without migrating the fixture
and its shape assertions (tests/test_anatomy_expectation.py:129-143) together.
"""
import json
import anatomy_expectation

_PROMPT = (
    "You are cataloguing origami anatomy. For the subject below, give the "
    "number of DISTINCT EXTREMITIES a uniaxial base must supply (limbs, head, "
    "tail, antennae -- anything needing its own flap).\n\n"
    "Reply with ONLY a JSON object with exactly these keys:\n"
    '  "expected_feature_count": a positive integer\n'
    '  "derivation": how you counted, naming each feature\n'
    '  "citation": a real source for the anatomy\n\n'
    "If you cannot give a real citation, omit the key. A row without both a "
    "derivation and a citation is discarded, so a guess is worth nothing.\n\n"
    "Subject: {subject}")


def _load_blob(cache_path):
    """The cache file as a dict, or {} for anything unusable.

    ⚠ The isinstance check is NOT belt-and-braces. An earlier draft of this
    plan caught only (ValueError, OSError), which misses the corruption shape
    that actually escapes: a file holding SYNTACTICALLY VALID JSON that is not
    a dict ([], "x", 42). `.get()` on a list raises AttributeError, which that
    tuple does not catch, so the exception propagated out of the public
    function -- violating "a corrupt cache must never take the serve down"
    while the guard looked present. Reproduced in review, not theorised.
    """
    try:
        if cache_path is None or not cache_path.exists():
            return {}
        blob = json.loads(cache_path.read_text())
    except (ValueError, OSError):
        return {}
    return blob if isinstance(blob, dict) else {}


def _read_cache(cache_path, key):
    # Through _valid_row: an invalid cached entry is a MISS, never a bypass.
    return _valid_row(_load_blob(cache_path).get(key))


def _write_cache(cache_path, key, row):
    if cache_path is None:
        return
    # An unreadable existing blob is treated as EMPTY and overwritten, not as
    # a reason to abort. Aborting means a once-corrupted file can never
    # self-heal: every later call re-invokes the client and every write
    # silently no-ops forever, with no signal.
    blob = _load_blob(cache_path)
    blob[key] = row
    try:
        cache_path.write_text(json.dumps(blob, indent=1, sort_keys=True))
    except OSError:
        pass              # caching is an optimisation, never a precondition


def _valid_row(raw):
    """The SOLE authority on row shape, or None. Every rejection is deliberate.

    ⚠ Both paths must go through this. An earlier draft validated only FRESH
    model replies, so a cached entry was trusted blindly -- writing
    {"a wholly unknown creature": 42} into the cache made the public function
    return the bare int 42, defeating the audit guarantee this module exists
    to provide. Keep the shape rules in one place or the two paths drift.
    """
    if not isinstance(raw, dict):
        return None
    count = raw.get("expected_feature_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        return None
    derivation, citation = raw.get("derivation"), raw.get("citation")
    if not (isinstance(derivation, str) and derivation.strip()):
        return None
    if not (isinstance(citation, str) and citation.strip()):
        return None
    return {"expected_feature_count": count,
            "derivation": derivation,
            "citation": citation,
            "provenance": "llm"}


def _parse(reply):
    """Decode a model reply. JSON decoding here, shape rules in _valid_row."""
    try:
        return _valid_row(json.loads(reply))
    except (ValueError, TypeError):
        return None


def anatomy_spec(prompt, *, client=None, cache_path=None):
    """The anatomy specification for `prompt`, or None if there isn't one."""
    authored = anatomy_expectation.expectation_for(prompt)
    if authored is not None:
        row = dict(authored)
        row["provenance"] = "external"
        return row

    key = anatomy_expectation.normalize_prompt(prompt)
    cached = _read_cache(cache_path, key)
    if cached is not None:
        return cached

    if client is None:
        return None
    try:
        reply = client.complete(_PROMPT.format(subject=prompt))
    except Exception:
        return None       # offline degradation is mandatory (spec section 15)

    row = _parse(reply)
    if row is not None:
        _write_cache(cache_path, key, row)
    return row
```

- [ ] **Step 4: Run the tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_anatomy_spec.py -v
```

Expected: all PASS.

- [ ] **Step 5: Mutation-verify the discard rule**

In `_parse`, delete the citation check (`if not (isinstance(citation, str)...): return None`).
Run: `PYTHONPATH=.:tests python -m pytest tests/test_anatomy_spec.py -v -k DISCARDED`
Expected: `test_a_row_without_a_citation_is_DISCARDED_not_downgraded` FAILS. **Restore and re-run to green.** Do the same for the derivation check.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/anatomy_spec.py mcp_harness/tests/test_anatomy_spec.py
git commit -m "feat(U2): anatomy_spec -- table first, model second, uncited rows discarded"
```

---

## Task 4: Widen the voxel grid, honouring the safety floor

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (a new module constant beside `VOXEL_GRID`)
- Test: `mcp_harness/tests/test_search_extraction.py`

**Interfaces:**
- Consumes: `mesh_to_tree.VOXEL_GRID_MIN_SAFE` (`:274`), `VOXEL_GRID`, `DRAIN_BUDGET` (`:577`).
- Produces: `mesh_to_tree.WIDE_VOXEL_GRID` — a tuple, and `mesh_to_tree.wide_grid_budget(grid) -> int`.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_search_extraction.py`:

```python
"""U4's widened sweep. Two things this file exists to prevent:

  * a grid that dips below VOXEL_GRID_MIN_SAFE, which is a MEASUREMENT (at
    res 16 the committed insect fragments into 3 post-fill() bodies -- two
    legs amputated before skeletonization), not a style rule; and
  * a budget that silently under-serves a longer grid. DRAIN_BUDGET = 6 is
    documented as FIDELITY_K1 x len(VOXEL_GRID), which holds for a 3-voxel
    grid and not for a 7-voxel one.
"""
import mesh_to_tree


def test_the_wide_grid_never_dips_below_the_measured_safety_floor():
    assert min(mesh_to_tree.WIDE_VOXEL_GRID) >= mesh_to_tree.VOXEL_GRID_MIN_SAFE


def test_the_wide_grid_is_a_superset_of_the_shipped_default():
    # _VOXEL_GRID_DEFAULT, NOT VOXEL_GRID. `VOXEL_GRID` is a _LiveVoxelGrid
    # view (mesh_to_tree.py:440-500) that re-reads IDE_VOXEL_GRID on EVERY
    # access, so a test asserting against it passes or fails depending on the
    # developer's environment. Pin the constant the view falls back to.
    assert set(mesh_to_tree._VOXEL_GRID_DEFAULT) <= set(
        mesh_to_tree.WIDE_VOXEL_GRID)


def test_the_wide_grid_is_sorted_and_deduplicated():
    g = list(mesh_to_tree.WIDE_VOXEL_GRID)
    assert g == sorted(set(g))
    # Note the shipped default is deliberately NOT sorted -- [96, 64, 128]
    # escalates on failure. WIDE_VOXEL_GRID is a search space, not an
    # escalation order, so sorting it is correct here and is not a claim
    # about the default.


def test_the_budget_reproduces_the_shipped_constant_for_the_shipped_grid():
    # Again the default, not the live view: with IDE_VOXEL_GRID set, len()
    # changes and this identity would read red for an unrelated reason.
    assert (mesh_to_tree.wide_grid_budget(mesh_to_tree._VOXEL_GRID_DEFAULT)
            == mesh_to_tree.DRAIN_BUDGET), (
        "DRAIN_BUDGET is documented as FIDELITY_K1 x len(VOXEL_GRID); if this "
        "fails, the documented identity is ALREADY broken -- stop and report "
        "that rather than adjusting the helper to match")


def test_a_longer_grid_gets_a_larger_budget():
    wide = mesh_to_tree.wide_grid_budget(mesh_to_tree.WIDE_VOXEL_GRID)
    assert wide > mesh_to_tree.DRAIN_BUDGET, (
        "a longer grid needs a larger drain budget; reusing 6 spends the "
        "whole budget inside the first three voxels")
    assert wide == mesh_to_tree.FIDELITY_K1 * 7
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_search_extraction.py -v
```

Expected: FAIL with `AttributeError: module 'mesh_to_tree' has no attribute 'WIDE_VOXEL_GRID'`.

- [ ] **Step 3: Implement**

In `mesh_to_tree.py`, immediately after `DRAIN_BUDGET`'s definition (`:577`):

```python
#: U4's widened sweep. STARTS AT 24, NOT 16: VOXEL_GRID_MIN_SAFE = 24 (:274)
#: is a measurement, not a preference -- at res 16 the committed `insect`
#: fixture fragments into 3 post-fill() bodies with 0.9738 of occupied volume
#: in the largest, i.e. two legs amputated before skeletonization
#: (tests/test_voxel_grid_env.py:131-132). Sub-floor values are
#: warn-and-proceed, which is not the same as safe. An earlier spec draft
#: listed 16 while claiming to honour the floor; it did not.
WIDE_VOXEL_GRID = (24, 32, 64, 96, 128, 192, 256)


def wide_grid_budget(grid) -> int:
    """The drain budget for `grid`, derived rather than transcribed.

    DRAIN_BUDGET = 6 is documented as FIDELITY_K1 x len(VOXEL_GRID) so that
    "every phase-1 pick of every remaining voxel fits inside the bound"
    (:577, :583). That identity holds for the 3-voxel shipped grid and breaks
    silently for a longer one -- `configured_voxel_grid`'s own docstring
    already reports the breakage. Deriving it keeps the documented invariant
    true for whatever grid it is handed.
    """
    return FIDELITY_K1 * len(tuple(grid))
```

- [ ] **Step 4: Run the tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_search_extraction.py -v
```

Expected: all PASS. If `test_the_budget_reproduces_the_shipped_constant_for_the_shipped_grid` fails, `DRAIN_BUDGET` is not in fact `FIDELITY_K1 * len(_VOXEL_GRID_DEFAULT)` — **stop and report that**, because it means the documented identity is already broken and the constant, not this helper, is wrong.

- [ ] **Step 5: Mutation-verify the floor**

Temporarily set `WIDE_VOXEL_GRID = (16, 24, 32, 64, 96, 128, 192, 256)`.
Run: `PYTHONPATH=.:tests python -m pytest tests/test_search_extraction.py -v -k floor`
Expected: `test_the_wide_grid_never_dips_below_the_measured_safety_floor` FAILS. **Restore and re-run.**

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_search_extraction.py
git commit -m "feat(U4): a widened voxel grid that honours the measured safety floor"
```

---

## Task 5: Rank cells against the spec, and say what the clamp forbids

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` (new ranking helper)
- Modify: `mcp_harness/tests/test_search_extraction.py` (append)

**Interfaces:**
- Consumes: `anatomy_spec.anatomy_spec` (Task 3), `mesh_to_tree.fidelity_score` (`:3398-3409`).
- Produces: `mesh_to_tree.spec_distance(row, spec) -> tuple` — a sort key, lower is better.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_search_extraction.py`:

```python
def test_spec_distance_ranks_by_absolute_count_error():
    spec = {"expected_feature_count": 6}
    near = mesh_to_tree.spec_distance({"leaves": 6, "pairs": 2}, spec)
    far = mesh_to_tree.spec_distance({"leaves": 3, "pairs": 2}, spec)
    assert near < far


def test_the_pair_axis_is_INACTIVE_when_the_spec_carries_no_pair_target():
    # The 14 authored rows carry NO pair count -- `expected_pairs` exists only
    # in the frozen, extraction-derived anatomy_reference.json, and sourcing it
    # from there would re-enter the closed loop this design exists to escape.
    # So on a table hit the pair axis must contribute NOTHING, not zero-vs-N.
    spec = {"expected_feature_count": 6}
    a = mesh_to_tree.spec_distance({"leaves": 6, "pairs": 0}, spec)
    b = mesh_to_tree.spec_distance({"leaves": 6, "pairs": 3}, spec)
    assert a == b, "pairs must not rank when the spec does not ask for them"


def test_the_pair_axis_ACTIVATES_when_the_spec_supplies_a_target():
    spec = {"expected_feature_count": 6, "expected_pairs": 2}
    good = mesh_to_tree.spec_distance({"leaves": 6, "pairs": 2}, spec)
    bad = mesh_to_tree.spec_distance({"leaves": 6, "pairs": 0}, spec)
    assert good < bad


def test_count_dominates_pairs():
    spec = {"expected_feature_count": 6, "expected_pairs": 2}
    right_count = mesh_to_tree.spec_distance({"leaves": 6, "pairs": 0}, spec)
    right_pairs = mesh_to_tree.spec_distance({"leaves": 2, "pairs": 2}, spec)
    assert right_count < right_pairs


def test_the_clamp_makes_a_nine_target_identical_to_eight():
    # NOT a wish -- a recorded arithmetic fact, pinned so U4 cannot claim a
    # Class-2 win it does not have. fidelity_score clamps r_eff to
    # MAX_LEAVES = 8, so octopus and water bear (both 9-feature targets)
    # score exactly as if the spec had said 8.
    assert mesh_to_tree.fidelity_score(8, 9) == mesh_to_tree.fidelity_score(8, 8)
    assert mesh_to_tree.fidelity_score(8, 9) == 1.0
```

- [ ] **Step 2: Run and watch it fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_search_extraction.py -v -k "spec_distance or pair_axis or dominates or clamp"
```

Expected: FAIL with `AttributeError: ... has no attribute 'spec_distance'`. The clamp test should PASS immediately — it pins existing behaviour.

- [ ] **Step 3: Implement**

In `mesh_to_tree.py`, beside `fidelity_score`:

```python
def spec_distance(row, spec) -> tuple:
    """Sort key for U4: how far a cell is from the anatomy spec. Lower wins.

    Count dominates pairs because a cell with the right number of flaps and
    the wrong symmetry is repairable downstream, while a cell with the wrong
    number of flaps is a different animal.

    ⚠ THE PAIR AXIS IS INACTIVE UNLESS THE SPEC ASKS FOR IT. None of the 14
    authored rows carries a pair count -- `expected_pairs` exists only in
    fixtures/anatomy_reference.json, which is frozen and whose own _meta reads
    "extraction-derived, NOT ground truth". Ranking pairs against a missing
    key would either rank everything equal (harmless but dishonest) or rank
    against that file (a closed loop). So the axis is omitted entirely, and
    its absence is visible in the key's LENGTH, not hidden as a zero.
    """
    # ⚠ A None spec returns (), it does not raise. This function's own named
    # producer, anatomy_spec.anatomy_spec(), returns None for the COMMON cases
    # -- unlisted prompt, no client, offline -- so raising here would turn
    # mandatory offline degradation into a crash.
    if spec is None:
        return ()
    target = spec.get("expected_feature_count")
    if target is None:
        return ()
    key = (abs(int(row.get("leaves", 0)) - int(target)),)
    pair_target = spec.get("expected_pairs")
    if pair_target is not None:
        key += (abs(_pair_count(row.get("pairs", 0)) - int(pair_target)),)
    return key


def _pair_count(pairs):
    """How many symmetric pairs a row carries, for either shape it arrives in.

    ⚠ NOT decoration. Every candidate/held/admitted row this module actually
    produces stores `pairs` as a LIST of pair tuples (:1564 documents the shape
    as pairs=[[4, 6]]; see :2309, :2335-2336, :2743, :3002-3003, :3194-3198),
    so a bare int() crashes with TypeError on any real row. An earlier draft of
    this plan invented a {"leaves": N, "pairs": N} fixture shape that no
    producer emits, so its tests passed and gave no signal at all. `leaves` was
    checked at the same time and IS always a plain int.
    """
    return len(pairs) if isinstance(pairs, (list, tuple)) else int(pairs)
```

- [ ] **Step 4: Run the tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_search_extraction.py -v
```

Expected: all PASS.

- [ ] **Step 5: Mutation-verify the inactive pair axis**

Change `spec_distance` to always append the pair term:

```python
    key += (abs(int(row.get("pairs", 0)) - int(spec.get("expected_pairs") or 0)),)
```

Run: `PYTHONPATH=.:tests python -m pytest tests/test_search_extraction.py -v -k INACTIVE`
Expected: `test_the_pair_axis_is_INACTIVE_when_the_spec_carries_no_pair_target` FAILS. **Restore and re-run.**

- [ ] **Step 6: Record what U4 does NOT claim**

Append to `docs/superpowers/plans/2026-09-02-p2-specify-and-search.md` under a new "U4 measured outcome" heading, filled in at execution time, and state explicitly:
- U4's new content is the grid, the budget and the ranking — **not** "fidelity against the spec", which `reference_count=` already ships and which `tests/test_anatomy_expectation.py:332` already asserts.
- **Class 2 (octopus, water bear) is out of U4's success criteria**, because `fidelity_score` clamps a 9-target to 8.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_search_extraction.py docs/superpowers/plans/2026-09-02-p2-specify-and-search.md
git commit -m "feat(U4): rank cells by distance to the spec, with the pair axis honestly inactive"
```

### U4 measured outcome (filled in at execution time, 2026-09-02)

`spec_distance` shipped as a pure sort key, mutation-verified (forcing the
pair term to always append breaks
`test_the_pair_axis_is_INACTIVE_when_the_spec_carries_no_pair_target`, exactly
as designed) and wired nowhere — no production caller, per spec §16.

Two things this task does **not** claim:

- **U4's new content is the grid, the budget and the ranking — not "fidelity
  against the spec."** `reference_count=` already ships and
  `tests/test_anatomy_expectation.py:332` already asserts it; `spec_distance`
  adds a second, independent ranking axis over `{leaves, pairs}` cells, it
  does not introduce fidelity scoring.
- **Class 2 (octopus, water bear) is out of U4's success criteria.**
  `fidelity_score(8, 9) == fidelity_score(8, 8) == 1.0` is pinned by
  `test_the_clamp_makes_a_nine_target_identical_to_eight`: both subjects are
  9-feature targets, and `fidelity_score`'s `r_eff = min(max(reference_count,
  MIN_LEAVES), MAX_LEAVES)` clamp scores an 8-leaf candidate against either of
  them exactly as it would against an 8-feature target. No amount of ranking
  on top of that clamped score can distinguish "true anatomy is 8" from "true
  anatomy is 9, clamped to 8" — the information is gone before `spec_distance`
  or anything else sees it.

---

## Task 6: M4 — re-measure the framing lever before building U3

⚠ **This task is a MEASUREMENT, and it gates U3. Do not write `frame_concept` before it returns.** A global framing change was measured and refuted on this repo (`85967c1`, *"GATE CLOSED 2026-08-25, AND THE ANSWER IS NO — NOT GLOBALLY"*); U3 is the per-subject version and owes the same bar.

⚠ **This task spends live generation quota (FLUX + Hunyuan).** The side-profile lizard mesh referenced by `lizard_camera.json` no longer exists, so the control cannot be replayed — it must be redrawn. **Get explicit authorization before running it.**

**Files:**
- Create: `mcp_harness/probe_framing_lever.py`
- Create: `mcp_harness/fixtures/framing_lever_ab.json` (probe output)

**Interfaces:**
- Consumes: `mesh_acquire.acquire_mesh`, `probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX` (`:313-317`) as the control arm.
- Produces: `fixtures/framing_lever_ab.json` with a `_meta.verdict` of `SHIP U3` or `DO NOT SHIP U3`.

- [ ] **Step 1: Write the probe, bar first, before any run**

Create `mcp_harness/probe_framing_lever.py`:

```python
"""M4 -- does PER-SUBJECT framing beat the fixed suffix that already ships?

A GLOBAL framing change was measured and REFUTED on 2026-08-25 (commit
85967c1; probe_mesh_bakeoff.py:236 -- "GATE CLOSED ... THE ANSWER IS NO --
NOT GLOBALLY"): CAMERA_SUFFIX_CANDIDATE rescued the horse and regressed the
octopus. U3 is the per-subject version of the same idea and owes the same bar.

The control is NOT "no suffix". It is HEAD's shipped
probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX, including the compositional margin
clause added at c27f81e. Measuring against no-suffix would reproduce the
spec's original headline number, which was taken at 43bcc1a -- BEFORE that
clause landed -- and would therefore overstate the lever by whatever the
clause already buys.

ONLY THE CAMERA DIFFERS BETWEEN THE TWO ARMS -- nothing else is allowed to.
An earlier draft set the framed arm's suffix to "", which silently dropped
every one of IMAGE_PROMPT_SUFFIX's seven non-camera clauses ("nothing
cropped", "empty margin", "no clutter", "neutral lighting", "simple clean
shape", "fully inside the frame", "entire animal") from that arm alone. That
is the identical failure shape to the CAMERA_SUFFIX_CANDIDATE global-suffix
experiment this docstring already warns against: a cropped or cluttered draw
moves a subject's leaf count away from target for a reason that has nothing
to do with framing, and project memory records a cropped horse extracting
zero nodes. A refutation measured that way would be blamed on the lever under
test when the actual cause was the missing clauses. `_prompt_for` below is
the single place both arms' text is built, precisely so the two can never
diverge except in the one field the experiment is about: see
SHARED_INVARIANT_SUFFIX.
"""
import json
import os
import pathlib

import anatomy_expectation
import mesh_acquire
import mesh_to_tree
import probe_mesh_bakeoff

#: PRE-REGISTERED 2026-09-02, BEFORE THE PROBE RAN. Do not edit after seeing
#: numbers -- a bar written after the fact is not a bar.
BAR = ("U3 ships only if per-subject framing, against HEAD's fixed suffix as "
       "control, moves >=1 subject's leaf count TOWARD its authored anatomy "
       "target and moves NO other subject AWAY from its target.")

#: Subjects with an authored anatomy row, so "toward the target" is measured
#: against hand-authored ground truth and never against this run's own
#: extraction. Keep every subject in fixtures/anatomy_expectation.json that
#: the bakeoff can draw.
SUBJECTS = ("a lizard with a long tail", "a horse", "an octopus",
            "a bird", "a spider")


def _framed(subject):
    """The per-subject concept prompt. THIS is what U3 would generate; here it
    is written by hand so the probe measures the LEVER, not the model."""
    return probe_mesh_bakeoff.frame_for(subject)


#: Recorded in place of a generator-identifying field the provider object
#: cannot supply. Never `None` -- `draw()` used to read
#: `getattr(provider, "name"/"space"/"api_name", None)`, which silently
#: recorded `None` on every row because `TwoStageProvider` has none of those
#: three attributes (mesh_acquire.py:490-515), reproducing the exact defect
#: this probe exists to avoid: `lizard_camera.json` recorded no generator
#: field at all, so "same generator" was an inference, never a fact. This is
#: a plain, JSON-serialisable string (`run()` writes rows straight to JSON)
#: chosen so it can never collide with a real class name or HF Space id --
#: a row that cannot name its generator must stay visibly distinguishable
#: from one that can.
UNAVAILABLE = "<UNAVAILABLE: provider has no such attribute>"


def _provider_identity(provider) -> dict:
    """What actually identifies `provider` as a specific generator.

    `TwoStageProvider` (mesh_acquire.py:463-515) has no `.name`, `.space` or
    `.api_name`. What it DOES have -- and what actually pins which generator
    produced a mesh -- is the pair of HF Spaces it calls: `image_space` /
    `image_api` for the concept-image stage and `mesh_space` / `mesh_api` for
    the image-to-3D stage (mesh_acquire.py:498-501, set once in `__init__`
    and never mutated by `generate()`). `generator` is the provider's own
    class name, the same idiom `mesh_acquire.acquire_mesh` already uses for
    provenance (mesh_acquire.py:1284), so a row can be traced back to which
    provider class ran even if that class's attributes change later.

    Any of the four Space/api fields `provider` genuinely lacks reads as
    `UNAVAILABLE`, never `None` -- see that sentinel's docstring.
    """
    identity = {"generator": type(provider).__name__}
    for field_name in ("image_space", "image_api", "mesh_space", "mesh_api"):
        identity[field_name] = getattr(provider, field_name, UNAVAILABLE)
    return identity


#: F1: the ONE camera-describing fragment inside IMAGE_PROMPT_SUFFIX --
#: everything else in that suffix is anti-crop/composition/lighting, not
#: camera. Stripped out PROGRAMMATICALLY (rather than retyping the rest of
#: the suffix by hand) so SHARED_INVARIANT_SUFFIX below can never drift from
#: IMAGE_PROMPT_SUFFIX if that constant is ever edited elsewhere -- a
#: hand-copied duplicate is exactly the kind of silent fork that let the
#: framed arm lose its clauses in the first place.
_CAMERA_FRAGMENT_IN_SUFFIX = ", side view"
if _CAMERA_FRAGMENT_IN_SUFFIX not in probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX:
    raise AssertionError(
        f"{_CAMERA_FRAGMENT_IN_SUFFIX!r} no longer found in "
        f"probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX -- SHARED_INVARIANT_SUFFIX "
        f"below would silently stop being derived from it")

#: Every clause in IMAGE_PROMPT_SUFFIX that is NOT about the camera: the
#: anti-crop, composition and lighting clauses. Used by the FRAMED arm so it
#: carries the same non-camera clauses the control arm gets from
#: IMAGE_PROMPT_SUFFIX verbatim -- see the module docstring and `_prompt_for`.
SHARED_INVARIANT_SUFFIX = probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX.replace(
    _CAMERA_FRAGMENT_IN_SUFFIX, "", 1)


def _prompt_for(subject, framed):
    """The exact text drawn for one arm. ONLY THE CAMERA/POSE DESCRIPTION MAY
    DIFFER between the two arms -- see the module docstring for why.

    control (`framed is None`): `subject + IMAGE_PROMPT_SUFFIX` verbatim --
    HEAD's shipped suffix, its own camera clause ("side view") included.

    framed: `framed` (subject + the per-subject camera clause from
    `probe_mesh_bakeoff._SUBJECT_FRAMINGS`, via `_framed`/`frame_for`) +
    SHARED_INVARIANT_SUFFIX -- IMAGE_PROMPT_SUFFIX with its own camera clause
    removed, so every non-camera clause is present, in both arms, as the
    identical text.
    """
    if framed is None:
        return subject + probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX
    return framed + SHARED_INVARIANT_SUFFIX


def draw(subject, framed, out_dir):
    """One arm. Returns the row, never raises -- a generation failure is data."""
    row = {"subject": subject,
           "arm": "framed" if framed is not None else "control",
           "prompt": _prompt_for(subject, framed),
           "target": anatomy_expectation.expected_feature_count(subject)}
    try:
        provider = mesh_acquire.get_provider("hf2")
        # reuse_concept MUST be False. mesh_acquire.py:618-632 sends the
        # pipeline STRAIGHT TO STAGE 2 when an existing concept.* is found in
        # out_dir, so a reframed prompt would never be evaluated and this
        # probe would report a null result as a refutation.
        #
        # `if ... : raise` rather than `assert`: this script spends live GPU
        # quota, and a bare `assert` is silently stripped under `python -O`,
        # which would delete this refusal along with the guarantee it makes.
        if getattr(provider, "reuse_concept", False):
            raise AssertionError(
                "reuse_concept must be off or the framing is never drawn")
        # Pin the generator BEFORE spending the draw: lizard_camera.json
        # recorded no generator field, so "same generator" was always an
        # inference. Refusing here, before provider.generate() runs, means a
        # row that cannot name its generator never spends GPU quota either.
        identity = _provider_identity(provider)
        row.update(identity)
        # Same `-O`-proofing as the reuse_concept guard above.
        if UNAVAILABLE in identity.values():
            raise AssertionError(
                f"cannot pin this row's generator, refusing to draw: "
                f"{identity}")
        glb = provider.generate(row["prompt"], out_dir)
        res = mesh_to_tree.auto_mesh_to_metric_tree(glb)
        # `MeshTreeResult` has no `.tree` attribute -- `res.nodes` is the
        # real field (mesh_to_tree.py:653-661), and it is every node in the
        # tree, interior joints included, not the leaf count `target` above
        # is measured against. `_leaf_count` is the production leaf-counting
        # function every other consumer of a MeshTreeResult uses for exactly
        # this reason (mesh_to_tree.py:3339-3341; e.g.
        # benchmark_subjects.py:120,125: "leaves = _leaf_count(res.nodes) if
        # res.nodes else 0" -- the same guard is reused here).
        row.update(
            leaves=mesh_to_tree._leaf_count(res.nodes) if res.nodes else 0,
            error=None)
    except Exception as exc:                       # generation failure is data
        row.update(leaves=None, error=f"{type(exc).__name__}: {exc}")
    return row


def verdict(rows) -> str:
    """SHIP U3 / DO NOT SHIP U3, decided by BAR. A FUNCTION, not a hand-edit,
    so the fixture and the bar cannot silently disagree."""
    by = {}
    for r in rows:
        if r.get("leaves") is not None and r.get("target"):
            by.setdefault(r["subject"], {})[r["arm"]] = abs(
                r["leaves"] - r["target"])
    improved = regressed = 0
    for dists in by.values():
        if "framed" not in dists or "control" not in dists:
            continue
        if dists["framed"] < dists["control"]:
            improved += 1
        elif dists["framed"] > dists["control"]:
            regressed += 1
    if regressed:
        return "DO NOT SHIP U3"
    return "SHIP U3" if improved else "DO NOT SHIP U3"


def run(out="fixtures/framing_lever_ab.json"):
    rows = []
    for subject in SUBJECTS:
        base = pathlib.Path(os.environ.get("IDE_PROBE_DIR", "/tmp/m4"))
        rows.append(draw(subject, None, base / f"{subject}-control"))
        rows.append(draw(subject, _framed(subject), base / f"{subject}-framed"))
    doc = {"_meta": {"bar": BAR, "verdict": verdict(rows),
                     "control": "probe_mesh_bakeoff.IMAGE_PROMPT_SUFFIX at HEAD",
                     "generated_by": "probe_framing_lever.py"},
           "rows": rows}
    pathlib.Path(out).write_text(json.dumps(doc, indent=1, sort_keys=True))
    print(doc["_meta"]["verdict"])


if __name__ == "__main__":
    run()
```

⚠ `probe_mesh_bakeoff.frame_for` does **not** exist yet — add it to
`probe_mesh_bakeoff.py` as a plain dict lookup from subject to a hand-written
camera clause (e.g. `"a lizard with a long tail": "side profile, full body"`),
with a `KeyError` for anything unlisted. Writing the framings by hand is
deliberate: M4 measures whether *framing* is a lever, not whether a model can
write one. If the lever is real, U3 replaces this dict with a model call.

- [ ] **Step 2: Unit-test `verdict` before spending any quota**

Create `mcp_harness/tests/test_framing_lever.py`:

```python
import probe_framing_lever as m4


def _row(subject, arm, leaves, target):
    return {"subject": subject, "arm": arm, "leaves": leaves, "target": target}


def test_an_improvement_with_no_regression_ships():
    assert m4.verdict([_row("a", "control", 1, 5), _row("a", "framed", 5, 5)]) \
        == "SHIP U3"


def test_any_regression_blocks_the_ship_even_beside_an_improvement():
    # This is exactly the 2026-08-25 shape: horse rescued, octopus regressed.
    rows = [_row("horse", "control", 18, 9), _row("horse", "framed", 9, 9),
            _row("octo", "control", 8, 9), _row("octo", "framed", 1, 9)]
    assert m4.verdict(rows) == "DO NOT SHIP U3"


def test_no_movement_does_not_ship():
    assert m4.verdict([_row("a", "control", 5, 5), _row("a", "framed", 5, 5)]) \
        == "DO NOT SHIP U3"


def test_a_failed_generation_is_skipped_not_counted_as_an_improvement():
    rows = [_row("a", "control", None, 5), _row("a", "framed", 5, 5)]
    assert m4.verdict(rows) == "DO NOT SHIP U3", (
        "a missing control is not evidence the framed arm is better")
```

Run: `cd mcp_harness && PYTHONPATH=.:tests python -m pytest tests/test_framing_lever.py -v`
Expected: all PASS.

- [ ] **Step 3: Mutation-verify `verdict` in both directions**

Force `return "SHIP U3"` unconditionally → `test_any_regression_blocks...` and
`test_no_movement...` FAIL. Force `return "DO NOT SHIP U3"` →
`test_an_improvement_with_no_regression_ships` FAILS. **Restore and re-run to
green.** Record both readings in the commit message.

- [ ] **Step 4: Get explicit authorization, then run**

This spends live FLUX + Hunyuan quota — the side-profile mesh referenced by
`lizard_camera.json` is gone, so the control cannot be replayed. **Ask before
running.**

```bash
cd mcp_harness && MESH_PROVIDER=hf python probe_framing_lever.py
```

- [ ] **Step 5: Commit the probe and the fixture**

```bash
git add mcp_harness/probe_framing_lever.py mcp_harness/tests/test_framing_lever.py mcp_harness/fixtures/framing_lever_ab.json
git commit -m "probe(M4): per-subject framing measured against the shipped suffix"
```

- [ ] **Step 6: STOP and report**

If the verdict is `DO NOT SHIP U3`, **do not build `frame_concept`.** Report
the numbers and let the project owner decide, exactly as M3 was handled in P1:
the verdict stood unchanged, the wiring was retained on separately measured
grounds, and the bar was **not** re-scored to match the decision.

---

## Done criteria

- [x] `mesh_report._provenance_lines` dispatches on `_PROVENANCE_CAVEAT`, mutation-verified.
- [x] No path stamps `"external"` for a model-supplied R.
- [x] `anatomy_spec` returns `None` with no client, and discards rows missing a derivation or a citation — both mutation-verified.
- [x] `WIDE_VOXEL_GRID` starts at or above `VOXEL_GRID_MIN_SAFE`.
- [x] `spec_distance`'s pair axis is inactive without a pair target, mutation-verified.
- [x] A test pins that `fidelity_score(8, 9) == fidelity_score(8, 8)`, so no future reader claims a Class-2 win through that route.
- [x] `vlm_judge.py` and `order_rank.py` are byte-unchanged: `git diff main --stat -- mcp_harness/vlm_judge.py mcp_harness/order_rank.py` is empty.
- [x] `hull_coverage` still has zero occurrences in `order_rank.py`.
- [x] `MIN_LEAVES, MAX_LEAVES = 4, 8` is unchanged.
- [x] Each task states whether it claims **inertness** or **confinement**, and does not claim "no regressions" — the full gate is unavailable.
- [x] A handoff note records M4's verdict and what U4 did NOT claim, because P3's producer choice depends on both.

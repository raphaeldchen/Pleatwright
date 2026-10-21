# VLM Pack Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When the deterministic rescue ladder has exhausted every rung on an authored tree, let the VLM name ONE unpaired flap to merge into the trunk; code performs that single deletion, re-packs, and the human gate says exactly what happened.

**Architecture:** A new `mcp_harness/pack_repair.py` holds everything about the repair turn — the last-resort precondition (`ladder_exhausted`), the candidate list (`candidates`), the deterministic edit (`apply_merge`), the explained-error message (`explain`), the one-tool model turn (`attempt`), and the gate text (`describe`). `gated_pipeline._draft` gains one hook after `pack()`; `pack()` keeps the failure envelope's `DETAIL` payload; `summarise()` appends the repair block; `tree_authoring.SYSTEM` rule 4 gets the fused-head carve-out. The model never emits a tree in a repair turn — its only action is `merge_flap(name, reason)`.

**Tech Stack:** Python 3.14 (main-repo venv), pytest, the existing `llm_client.LLMClient` (OpenAI-compatible tool calls), `error_recipes.parse_detail`, `tree_authoring` helpers, `tree_contract.check`, `mesh_to_tree.MIN_LEAVES/MAX_LEAVES/ADMIT_MAX_LEAVES`.

**Spec:** `docs/superpowers/specs/2026-09-12-vlm-pack-repair-design.md` — read it first.

## Global Constraints

- The VLM turn fires ONLY when `packing["detail"]` shows `rungs_tried >= 1` and a non-empty `stages_tried` (spec §4.1). Timeout, crash, bare `ERROR:` → no model call.
- The model NEVER edits the tree. Its only tool is `merge_flap(name, reason)`; `apply_merge` deletes exactly one flap plus its private stalk (spec §5.3, owner ruling 2026-09-12).
- Only UNPAIRED leaves are candidates. A flap that appears in any `pairs` entry is never offered (spec §5.2).
- One repair turn per `_draft`. It is never counted in `revisions_authored` or `round` (spec §4.2).
- Nothing after the authoring turn may raise out of `_draft` (existing contract). Every failure inside the repair path becomes `outcome == "refused"` with the exception text.
- `_author`, `llm_client`, `rescue_ladder`, `server.py`, and the React `ReviewPanel` are NOT modified.
- The packable-window numbers in any message are read from `mesh_to_tree.MIN_LEAVES`, `MAX_LEAVES`, `ADMIT_MAX_LEAVES` — never literals in `pack_repair.py`.
- `tree_authoring.SYSTEM` must keep every pinned token: `FLIP THE SIGN`, `DOWNWARD`, `EACH SIDE IS ITS OWN CHAIN`, `READ BEFORE YOU DERIVE`, `LEAF CONVENTION`.
- Subjects that pack (at attempt 0 or any ladder rung) must produce a `summary` byte-identical to today's, and `state["repair"] is None`.
- Never use tardigrade / water bear as a test subject (owner instruction).
- Every test runs with a fake client and fake `pack_fn`: no network, no spawned compile.
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

## How to run tests

All commands from the worktree root `<repo>`. The worktree has no `.venv`; use the main repo's:

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_pack_repair.py -q
```

Abbreviated below as `PYTEST tests/<file>::<test>`.

## File structure

| file | responsibility |
|---|---|
| `mcp_harness/pack_repair.py` (create) | Everything about the repair turn. Pure functions plus one async `attempt`. Imports `tree_authoring`, `tree_contract`, `error_recipes`, `mesh_to_tree` (lazily), `llm_client` (lazily). Does NOT import `gated_pipeline`. |
| `mcp_harness/gated_pipeline.py` (modify) | `pack()` stores `detail`; `_build(tree)` helper factors the metric-tree derivation; `_draft` calls `pack_repair.attempt` after a failed pack; `summarise(..., repair=None)`; `_blank_state` gets `"repair": None`. |
| `mcp_harness/tree_authoring.py` (modify) | Rule 4 text only. |
| `mcp_harness/tests/test_pack_repair.py` (create) | Unit tests for every `pack_repair` function with a 10-flap spider fixture and a real envelope string. |
| `mcp_harness/tests/test_gated_pipeline.py` (modify) | `_draft`-level tests: call counts, outcomes, byte-identical summary on the packing path. |
| `mcp_harness/tests/test_tree_authoring.py` (modify) | Pins the new rule-4 tokens. |
| `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/repair_rolls.py` (create) | Live measurement driver: spider/scorpion/crab × 3. |
| `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/repair_rolls.json` (create, by running the driver) | The 9-row evidence table. |

## Shared test fixtures (used verbatim in Tasks 2–7)

Put these at the top of `mcp_harness/tests/test_pack_repair.py` in Task 2. Later tasks import from it: `from test_pack_repair import SPIDER, ENVELOPE, envelope_packing`.

```python
"""pack_repair: the VLM as LAST resort, naming ONE unpaired flap; code edits.

Every test is offline. The envelope string is the shape server._failure_envelope
emits (spec §4.1), with the DETAIL payload parse_detail reads.
"""
from __future__ import annotations

import json

import pytest

import pack_repair as PR

# A 10-flap spider: 2 unpaired midline flaps + 4 paired leg pairs. Lengths are
# grid-unit integers, the way the authoring tool schema requires.
SPIDER = {
    "subject_guess": "a spider", "readings": [],
    "leaves": ["abdomen", "head",
               "foot_1L", "foot_1R", "foot_2L", "foot_2R",
               "foot_3L", "foot_3R", "foot_4L", "foot_4R"],
    "nodes": [
        {"name": "cephalothorax", "parent": None, "length": 0, "direction": [0, 0, 0]},
        {"name": "abdomen", "parent": "cephalothorax", "length": 4, "direction": [-1, 0, 0]},
        {"name": "head", "parent": "cephalothorax", "length": 2, "direction": [1, 0, 0]},
        {"name": "foot_1L", "parent": "cephalothorax", "length": 6, "direction": [1, 1, 0]},
        {"name": "foot_1R", "parent": "cephalothorax", "length": 6, "direction": [1, -1, 0]},
        {"name": "foot_2L", "parent": "cephalothorax", "length": 6, "direction": [0.3, 1, 0]},
        {"name": "foot_2R", "parent": "cephalothorax", "length": 6, "direction": [0.3, -1, 0]},
        {"name": "foot_3L", "parent": "cephalothorax", "length": 6, "direction": [-0.3, 1, 0]},
        {"name": "foot_3R", "parent": "cephalothorax", "length": 6, "direction": [-0.3, -1, 0]},
        {"name": "foot_4L", "parent": "cephalothorax", "length": 5, "direction": [-1, 1, 0]},
        {"name": "foot_4R", "parent": "cephalothorax", "length": 5, "direction": [-1, -1, 0]},
    ],
    "pairs": [["foot_1L", "foot_1R"], ["foot_2L", "foot_2R"],
              ["foot_3L", "foot_3R"], ["foot_4L", "foot_4R"]],
}

DETAIL = {"code": "POLYS_NOT_VALID", "scale_at_failure": 0.281249,
          "stage_reached": "optimize", "rungs_tried": 55,
          "stages_tried": {"placement": 2, "order": 5, "flatten": 6,
                           "jitter": 24, "composed": 10, "stub": 8},
          "distinct_errors": ["POLYS_NOT_VALID", "POLYS_MULTIPLE_IBPS"],
          "suggested_lever": "try node-order restarts first"}

# The shape server._failure_envelope returns: human head + ladder note +
# lever, then ONE machine line.
ENVELOPE = ("ERROR: polygon network is not valid after optimization "
            "(scale=0.281249): the active-path network does not form a valid "
            "polygon partition, so the Universal Molecule cannot be built. "
            "[ladder: also tried 55 staged rescue rung(s) (placement 2, order 5, "
            "flatten 6, jitter 24, composed 10, stub 8); none packed; 1 other "
            "error class(es) seen -- see DETAIL.] [suggested lever (S1-measured; "
            "any stage already named in DETAIL.stages_tried has been tried): try "
            "node-order restarts first]\n"
            "DETAIL: " + json.dumps(DETAIL, separators=(",", ":")))


def envelope_packing(error=ENVELOPE, detail=DETAIL):
    """A `pack()` result for a tree the whole ladder failed on."""
    return {"served": False, "stage": None, "served_nodes": None,
            "invents_anatomy": False, "stub_flaps": 0, "fold": None,
            "error": error[:400], "detail": detail,
            "what_changed": "this tree does not pack yet"}
```

---

### Task 1: `pack()` keeps the envelope's DETAIL payload

The packer's failure string carries the ladder's `DETAIL` line; `pack()` truncates `error` to 400 characters for display and that cuts the line off. Store the parsed payload before truncating.

**Files:**
- Modify: `mcp_harness/gated_pipeline.py:81-100` (the `pack()` not-served branch)
- Test: `mcp_harness/tests/test_gated_pipeline.py`

**Interfaces:**
- Produces: `pack(...)` result dict gains key `"detail": dict | None` on BOTH branches (served → `None`; not served → `error_recipes.parse_detail(str(fold))`).

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_gated_pipeline.py`:

```python
# --------------------------------------------------------------------------
# pack() keeps the ladder's DETAIL payload (spec 2026-09-12 §4.1)
# --------------------------------------------------------------------------

def test_pack_keeps_the_detail_payload_off_the_full_error_string():
    """`error` is truncated to 400 chars for display, which cuts the DETAIL
    line off. The parsed payload must be taken from the FULL string first."""
    from test_pack_repair import ENVELOPE, DETAIL
    assert len(ENVELOPE) > 400            # the truncation would lose it

    def whole_ladder_failed(nodes, pairs):
        return (ENVELOPE, {})

    out = GP.pack([{"id": 0, "parent_id": None, "length": 0.0}], [],
                  pack_fn=whole_ladder_failed)
    assert out["served"] is False
    assert out["detail"] == DETAIL
    assert len(out["error"]) <= 400


def test_pack_detail_is_none_when_the_error_has_no_payload():
    def timed_out(nodes, pairs):
        return ("ERROR: compilation timed out after 60s", {})
    out = GP.pack([{"id": 0, "parent_id": None, "length": 0.0}], [],
                  pack_fn=timed_out)
    assert out["served"] is False
    assert out["detail"] is None


def test_pack_detail_is_none_on_a_served_tree():
    out = GP.pack([{"id": 0, "parent_id": None, "length": 0.0}], [],
                  pack_fn=fake_pack_ok)
    assert out["served"] is True
    assert out["detail"] is None
```

Also create `mcp_harness/tests/test_pack_repair.py` containing ONLY the shared-fixtures block above (the module docstring through `envelope_packing`), so the import in the first test resolves. `import pack_repair as PR` will fail until Task 2 — so for THIS task, leave that one import line out and add it in Task 2.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `PYTEST tests/test_gated_pipeline.py -k "detail" -q`
Expected: 3 failures, `KeyError: 'detail'`.

- [ ] **Step 3: Implement**

In `mcp_harness/gated_pipeline.py`, add `import error_recipes` after `import rescue_ladder`. Then in `pack()` replace the not-served return and add `detail` to the served return:

```python
    served = isinstance(fold, str) and not fold.startswith("ERROR:")
    if not served:
        # ⚠ `error` is TRUNCATED for display, and the ladder's machine-readable
        # DETAIL line is the LAST line of the envelope -- so it is exactly what
        # the truncation loses. Parse it off the full string first: it is how
        # pack_repair.ladder_exhausted tells "every rung failed" from "the
        # compile timed out / crashed before the ladder ran" (spec §4.1).
        return {"served": False, "stage": None, "served_nodes": None,
                "invents_anatomy": False, "stub_flaps": 0, "fold": None,
                "error": str(fold)[:400],
                "detail": error_recipes.parse_detail(str(fold)),
                "what_changed": "this tree does not pack yet"}
```

and in the served return dict add `"detail": None,` after `"error": None,`.

Also in `_draft`'s `except Exception` fallback packing dict (the "packability step CRASHED" one, around line 540) add `"detail": None,` after `"fold": None,` — a crash is not ladder exhaustion.

- [ ] **Step 4: Run the tests**

Run: `PYTEST tests/test_gated_pipeline.py -q`
Expected: all pass (the three new ones and every existing one).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tests/test_gated_pipeline.py mcp_harness/tests/test_pack_repair.py
git commit -m "pack(): keep the ladder's DETAIL payload before truncating the error

The envelope's machine line is its LAST line, so the 400-char display
truncation lost exactly the field that says whether every rescue rung ran.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `pack_repair.ladder_exhausted` — the last-resort gate

**Files:**
- Create: `mcp_harness/pack_repair.py`
- Test: `mcp_harness/tests/test_pack_repair.py`

**Interfaces:**
- Produces: `ladder_exhausted(packing: dict) -> tuple[bool, str]`.

- [ ] **Step 1: Write the failing tests**

Add `import pack_repair as PR` to the imports of `tests/test_pack_repair.py`, then append:

```python
# --------------------------------------------------------------------------
# ladder_exhausted -- the VLM is the LAST resort (spec §4.1)
# --------------------------------------------------------------------------

def test_a_full_envelope_means_the_ladder_is_exhausted():
    ok, why = PR.ladder_exhausted(envelope_packing())
    assert ok is True
    assert "55" in why


def test_a_timeout_is_not_exhaustion():
    ok, why = PR.ladder_exhausted(envelope_packing(
        error="ERROR: compilation timed out after 60s", detail=None))
    assert ok is False
    assert "did not run to completion" in why
    assert "timed out" in why


def test_a_bare_error_with_no_detail_is_not_exhaustion():
    ok, why = PR.ladder_exhausted(envelope_packing(error="ERROR: nope", detail=None))
    assert ok is False


def test_zero_rungs_is_not_exhaustion():
    d = dict(DETAIL, rungs_tried=0, stages_tried={})
    ok, why = PR.ladder_exhausted(envelope_packing(detail=d))
    assert ok is False
    assert "0" in why


def test_a_missing_detail_key_is_not_exhaustion():
    p = envelope_packing(); del p["detail"]
    ok, _ = PR.ladder_exhausted(p)
    assert ok is False


def test_a_served_packing_is_never_exhausted():
    ok, why = PR.ladder_exhausted({"served": True, "detail": None, "error": None})
    assert ok is False
    assert "served" in why
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_pack_repair.py -q`
Expected: `ModuleNotFoundError: No module named 'pack_repair'`.

- [ ] **Step 3: Create the module with `ladder_exhausted`**

Create `mcp_harness/pack_repair.py`:

```python
"""The VLM as LAST resort: name ONE unpaired flap to merge; code does the edit.

Spec: docs/superpowers/specs/2026-09-12-vlm-pack-repair-design.md.

Three owner rulings shape this module and are not up for local re-decision:

1. It runs only after the WHOLE deterministic rescue ladder has failed
   (`ladder_exhausted`, read off the packer's own envelope -- never inferred
   from flap count).
2. The model never emits a tree here. Its only tool is `merge_flap(name,
   reason)`; `apply_merge` deletes exactly that leaf and nothing else. The
   class of failure "the model edited proportions" is not detected by this
   design -- it is inexpressible.
3. Only UNPAIRED leaves are candidates. A paired flap is bilateral anatomy
   (limb, wing, ray) and is never offered, whatever the model says.

The window numbers quoted to the model are read from `mesh_to_tree` at call
time so the message moves when the packer wall moves.
"""
from __future__ import annotations

import json

import tree_authoring as TA
import tree_contract


def ladder_exhausted(packing: dict) -> tuple[bool, str]:
    """Did every deterministic rescue rung run and fail?

    Reads the failure envelope's DETAIL payload that `gated_pipeline.pack`
    stores under `packing["detail"]` (parsed off the FULL error string, before
    the display truncation). `server._failure_envelope` emits that payload
    only after "every rung failed -- nothing was served", so its presence with
    `rungs_tried >= 1` IS the ladder's own word that it is exhausted. A compile
    timeout, an engine crash, or a pack-step crash carries no payload and
    therefore never reaches the model.
    """
    if packing.get("served"):
        return False, "the tree was served; nothing to repair"
    d = packing.get("detail")
    if not isinstance(d, dict):
        head = (packing.get("error") or "no error text").splitlines()[0][:160]
        return False, f"the rescue ladder did not run to completion: {head}"
    rungs = d.get("rungs_tried")
    stages = d.get("stages_tried")
    if not isinstance(rungs, int) or rungs < 1 or not isinstance(stages, dict) or not stages:
        return False, (f"the rescue ladder reports {rungs!r} rung(s) tried "
                       f"({stages!r}); not exhausted")
    counts = ", ".join(f"{s} {n}" for s, n in stages.items())
    return True, f"all {rungs} deterministic rescue rungs failed ({counts})"
```

- [ ] **Step 4: Run the tests**

Run: `PYTEST tests/test_pack_repair.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pack_repair.py mcp_harness/tests/test_pack_repair.py
git commit -m "pack_repair.ladder_exhausted: the VLM fires only on the ladder's own exhaustion envelope

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `candidates` and `apply_merge` — the only edit, done by code

**Files:**
- Modify: `mcp_harness/pack_repair.py`
- Test: `mcp_harness/tests/test_pack_repair.py`

**Interfaces:**
- Produces: `candidates(tree: dict) -> list[str]`; `apply_merge(tree: dict, name: str) -> tuple[dict | None, str | None]` returning `(new_tree, None)` or `(None, refusal_text)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pack_repair.py`:

```python
# --------------------------------------------------------------------------
# candidates / apply_merge -- the model names, code edits (spec §5.2, §5.3)
# --------------------------------------------------------------------------

def _tuples(tree):
    return {(n["name"], n["parent"], tuple(n["direction"]), n["length"])
            for n in tree["nodes"]}


def test_candidates_are_exactly_the_unpaired_flaps_in_authored_order():
    assert PR.candidates(SPIDER) == ["abdomen", "head"]


def test_candidates_is_empty_when_every_flap_is_paired():
    t = json.loads(json.dumps(SPIDER))
    t["nodes"] = [n for n in t["nodes"] if n["name"] not in ("abdomen", "head")]
    assert PR.candidates(t) == []


def test_an_internal_joint_is_never_a_candidate():
    t = json.loads(json.dumps(SPIDER))
    # give the abdomen a child so it stops being a leaf
    t["nodes"].append({"name": "spinneret", "parent": "abdomen", "length": 1,
                       "direction": [-1, 0, 0]})
    assert PR.candidates(t) == ["head", "spinneret"]


def test_apply_merge_removes_exactly_that_node_and_nothing_else():
    out, why = PR.apply_merge(SPIDER, "head")
    assert why is None
    assert len(PR.candidates(out)) == 1                       # abdomen remains
    assert _tuples(out) == _tuples(SPIDER) - {("head", "cephalothorax", (1, 0, 0), 2)}
    assert out["pairs"] == SPIDER["pairs"]
    assert out["leaves"] == [l for l in SPIDER["leaves"] if l != "head"]
    assert out is not SPIDER and SPIDER["nodes"][2]["name"] == "head"   # input untouched


def test_apply_merge_refuses_a_paired_flap():
    out, why = PR.apply_merge(SPIDER, "foot_1L")
    assert out is None
    assert "foot_1L" in why and "paired" in why


def test_apply_merge_refuses_a_non_leaf_and_an_unknown_name():
    out, why = PR.apply_merge(SPIDER, "cephalothorax")
    assert out is None and "not a flap" in why
    out, why = PR.apply_merge(SPIDER, "antenna")
    assert out is None and "does not exist" in why


def test_apply_merge_refuses_to_go_below_the_packable_minimum(monkeypatch):
    import mesh_to_tree
    monkeypatch.setattr(mesh_to_tree, "MIN_LEAVES", 10)     # spider has 10
    out, why = PR.apply_merge(SPIDER, "head")
    assert out is None
    assert "below" in why and "10" in why
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_pack_repair.py -k "candidates or apply_merge" -q`
Expected: `AttributeError: module 'pack_repair' has no attribute 'candidates'`.

- [ ] **Step 3: Implement**

Append to `mcp_harness/pack_repair.py`:

```python
def _paired_names(tree: dict) -> set:
    out = set()
    for p in (tree.get("pairs") or []):
        if isinstance(p, (list, tuple)):
            out.update(str(x) for x in p)
    return out


def candidates(tree: dict) -> list[str]:
    """The flaps the model may name: leaves that are in NO symmetric pair.

    Paired flaps are bilateral anatomy -- limbs, wings, rays -- and are never
    offered. That single rule is what makes "drop a leg" (or a whole leg pair)
    inexpressible in a repair turn, regardless of what the model says.
    Authored order is kept so the list reads the way the tree was written.
    """
    leaves = TA.leaves_of(TA.to_tuples(tree))
    paired = _paired_names(tree)
    return [l for l in leaves if l not in paired]


def apply_merge(tree: dict, name: str) -> tuple[dict | None, str | None]:
    """Delete leaf `name` from `tree`. Returns (new_tree, None) or (None, why).

    The result differs from `tree` by exactly one node. Every other node keeps
    name, parent, length and direction byte-for-byte, because code -- not the
    model -- produced it. The merged flap's length is NOT added to its parent:
    that would be a proportion change, the class of edit this module forbids.
    """
    from mesh_to_tree import MIN_LEAVES                    # read at call time
    names = [n["name"] for n in tree["nodes"]]
    if name not in names:
        return None, f"`{name}` does not exist in the tree"
    leaves = TA.leaves_of(TA.to_tuples(tree))
    if name not in leaves:
        return None, f"`{name}` is not a flap (it has children)"
    if name in _paired_names(tree):
        return None, f"`{name}` is paired -- a limb, wing or ray is never merged"
    if len(leaves) - 1 < MIN_LEAVES:
        return None, (f"removing `{name}` would leave {len(leaves) - 1} flaps, "
                      f"below the packable minimum of {MIN_LEAVES}")
    out = json.loads(json.dumps(tree))                     # deep copy
    out["nodes"] = [n for n in out["nodes"] if n["name"] != name]
    if isinstance(out.get("leaves"), list):
        out["leaves"] = [l for l in out["leaves"] if l != name]
    # Defensive: candidates() guarantees no pair names it, but never emit a
    # pair whose member is gone.
    out["pairs"] = [p for p in (out.get("pairs") or []) if name not in p]
    try:
        nodes = TA.to_tuples(out)
        keep, _ = TA.leaf_pairs(out, TA.leaves_of(nodes))
        tn, sp, _ = TA.metric_tree(nodes, keep)
        errs = tree_contract.check(tn, sp).get("errors", [])
    except Exception as e:                                  # noqa: BLE001
        errs = [f"unbuildable: {e}"]
    if errs:
        return None, f"removing `{name}` leaves an invalid tree: " + "; ".join(errs)
    return out, None
```

- [ ] **Step 4: Run the tests**

Run: `PYTEST tests/test_pack_repair.py -q`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pack_repair.py mcp_harness/tests/test_pack_repair.py
git commit -m "pack_repair: candidates are the UNPAIRED leaves; apply_merge deletes exactly one

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `explain`, `REPAIR_SYSTEM`, `MERGE_TOOL` — what the model is told

**Files:**
- Modify: `mcp_harness/pack_repair.py`
- Test: `mcp_harness/tests/test_pack_repair.py`

**Interfaces:**
- Produces: `explain(packing: dict, tree: dict, cands: list[str]) -> str`; module constants `REPAIR_SYSTEM: str` and `MERGE_TOOL: list` (one OpenAI-style function tool named `merge_flap`).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pack_repair.py`:

```python
# --------------------------------------------------------------------------
# explain -- the RTLFixer-shaped message (spec §5.1)
# --------------------------------------------------------------------------

def test_explain_lists_paired_flaps_as_unmergeable_and_unpaired_as_candidates():
    s = PR.explain(envelope_packing(), SPIDER, PR.candidates(SPIDER))
    assert "10 flap tips" in s
    assert "foot_1L / foot_1R (6)" in s
    assert "cannot be merged" in s
    assert "abdomen (4)" in s and "head (2)" in s


def test_explain_quotes_the_engine_head_and_lever_but_not_the_detail_line():
    s = PR.explain(envelope_packing(), SPIDER, PR.candidates(SPIDER))
    assert "polygon network is not valid" in s
    assert "55 staged rescue rung" in s
    assert "suggested lever" in s
    assert "DETAIL:" not in s


def test_explain_reads_the_window_from_mesh_to_tree(monkeypatch):
    import mesh_to_tree
    monkeypatch.setattr(mesh_to_tree, "MAX_LEAVES", 7)
    monkeypatch.setattr(mesh_to_tree, "ADMIT_MAX_LEAVES", 11)
    s = PR.explain(envelope_packing(), SPIDER, PR.candidates(SPIDER))
    assert "more than 7 flap tips" in s
    assert "8-11" in s and "above 11" in s


def test_explain_omits_the_window_sentence_when_the_tree_is_inside_it(monkeypatch):
    import mesh_to_tree
    monkeypatch.setattr(mesh_to_tree, "MAX_LEAVES", 12)      # spider's 10 is inside
    s = PR.explain(envelope_packing(), SPIDER, PR.candidates(SPIDER))
    assert "packable window" not in s


def test_the_tool_is_one_function_taking_name_and_reason():
    assert len(PR.MERGE_TOOL) == 1
    f = PR.MERGE_TOOL[0]["function"]
    assert f["name"] == "merge_flap"
    assert set(f["parameters"]["required"]) == {"name", "reason"}


def test_the_system_prompt_states_the_rule_as_anatomy():
    s = PR.REPAIR_SYSTEM
    assert "ONE" in s and "unpaired" in s
    assert "cephalothorax" in s
    assert "not a distinct protruding appendage" in s
    assert '"none"' in s
    assert "cannot change lengths" in s
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_pack_repair.py -k "explain or tool or system_prompt" -q`
Expected: `AttributeError` on `explain`.

- [ ] **Step 3: Implement**

Append to `mcp_harness/pack_repair.py`:

```python
REPAIR_SYSTEM = """\
You are helping design an origami base. The packing engine cannot fit this \
metric tree on one square, and every deterministic rescue it has was tried \
and failed. You may merge ONE of the unpaired flaps listed into the trunk, if \
-- and only if -- it is not a distinct protruding appendage of this animal: a \
head fused into a cephalothorax or carapace, or a stub that is really part of \
the body. A tail, an abdomen, a stinger or a proboscis that protrudes is a \
real appendage; do not merge it to make the tree fit. If every unpaired flap \
is a real appendage, call the tool with name "none" and say why. You cannot \
change lengths, add or remove anything else, or edit the tree; you only name \
the flap. Look at the mesh render to judge what protrudes."""

MERGE_TOOL = [{"type": "function", "function": {
    "name": "merge_flap",
    "description": "Name ONE unpaired flap to merge into the trunk, or "
                   "\"none\" to decline. The pipeline performs the edit.",
    "parameters": {"type": "object", "properties": {
        "name": {"type": "string",
                 "description": "An unpaired flap from the list, or \"none\"."},
        "reason": {"type": "string",
                   "description": "One sentence: why this flap is not a "
                                  "distinct appendage, or why none is."}},
        "required": ["name", "reason"]}}}]


def _window_sentence(n_flaps: int) -> str:
    """The packable window, read from mesh_to_tree at CALL time (never a
    literal here), and omitted when the tree is already inside it -- then the
    failure is not a flap-count failure and saying so would misdirect."""
    import mesh_to_tree as M
    if n_flaps <= M.MAX_LEAVES:
        return ""
    return (f"On this engine, trees with more than {M.MAX_LEAVES} flap tips are "
            f"outside the measured packable window; {M.MAX_LEAVES + 1}-"
            f"{M.ADMIT_MAX_LEAVES} is a try-anyway window where packing usually "
            f"needs rescue and above {M.ADMIT_MAX_LEAVES} is not attempted. ")


def explain(packing: dict, tree: dict, cands: list[str]) -> str:
    """The explained error (RTLFixer: explained, never raw) plus the census.

    Three parts, all from things the pipeline already has: the flap census
    with pairing (so the model sees WHY legs are off the table), the window
    sentence, and the engine's own envelope head + ladder note + curated
    `[suggested lever ...]` clause with the machine DETAIL line stripped.
    """
    import error_recipes
    nodes = TA.to_tuples(tree)
    length = {n[0]: n[3] for n in nodes}
    leaves = TA.leaves_of(nodes)
    pairs = [p for p in (tree.get("pairs") or []) if len(p) == 2]
    paired_txt = ", ".join(f"{a} / {b} ({length.get(a)})" for a, b in pairs)
    cand_txt = ", ".join(f"{c} ({length.get(c)})" for c in cands) or "none"
    head = error_recipes.strip_detail(packing.get("error") or "").strip()
    return (f"This tree has {len(leaves)} flap tips. "
            f"Paired (limbs -- cannot be merged): {paired_txt or 'none'}. "
            f"Unpaired: {cand_txt}.\n\n"
            + _window_sentence(len(leaves))
            + f"The engine said: {head}\n\n"
            "Name ONE unpaired flap to merge, or \"none\".")
```

⚠ `packing["error"]` is the 400-char display string, which may already lack the DETAIL line; `strip_detail` is still applied so a caller passing the full string gets the same result.

- [ ] **Step 4: Run the tests**

Run: `PYTEST tests/test_pack_repair.py -q`
Expected: 19 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pack_repair.py mcp_harness/tests/test_pack_repair.py
git commit -m "pack_repair: explain() (census + window from mesh_to_tree + engine envelope), REPAIR_SYSTEM, MERGE_TOOL

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `attempt` — the one model turn, and the repair record

**Files:**
- Modify: `mcp_harness/pack_repair.py`
- Test: `mcp_harness/tests/test_pack_repair.py`

**Interfaces:**
- Consumes: `ladder_exhausted`, `candidates`, `explain`, `apply_merge`, `REPAIR_SYSTEM`, `MERGE_TOOL` (Tasks 2–4); `llm_client.user_message_with_images(text, [png_path]) -> dict`; `client.run_turn(system, messages, tools) -> TurnResult` with `.tool_calls[i].function.arguments` (JSON string).
- Produces: `async attempt(client, mesh_png: str, tree: dict, packing: dict, *, pack) -> tuple[dict, dict | None, dict | None]` where `pack(tree) -> packing` is a callable the caller supplies. Returns `(repair_record, new_tree_or_None, new_packing_or_None)`. `repair_record` is the spec §6 dict; `new_tree`/`new_packing` are non-None only when `outcome == "merged"`. Also `record_crash(exc, tree, packing) -> dict` for the caller's no-raise guard.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pack_repair.py`:

```python
# --------------------------------------------------------------------------
# attempt -- the one turn, and its record (spec §4, §5.3, §6)
# --------------------------------------------------------------------------
import asyncio


class _Call:
    def __init__(self, payload, name="merge_flap"):
        self.id = "call_r"
        self.function = type("F", (), {"name": name, "arguments": json.dumps(payload)})()


class _Result:
    def __init__(self, payload=None, text=""):
        self.text = text
        self.tool_calls = [] if payload is None else [_Call(payload)]
        self.finish_reason = "tool_calls" if payload is not None else "stop"
        self.usage = {"total_tokens": 50}


class RepairClient:
    def __init__(self, payload=None, text=""):
        self.payload, self.text, self.calls = payload, text, []

    async def run_turn(self, system, messages, tools):
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        return _Result(self.payload, self.text)


def _png(tmp_path):
    p = tmp_path / "mesh.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 64)
    return str(p)


def _pack_that_serves_at(n_max):
    """A fake packer: serves iff the tree has <= n_max flaps."""
    def pack(tree):
        n = len(TA_leaves(tree))
        if n <= n_max:
            return {"served": True, "stage": "flatten", "served_nodes": [],
                    "invents_anatomy": False, "stub_flaps": 0, "fold": "{}",
                    "error": None, "detail": None,
                    "what_changed": "joints merged"}
        return envelope_packing()
    return pack


def TA_leaves(tree):
    import tree_authoring as TA
    return TA.leaves_of(TA.to_tuples(tree))


def test_attempt_merges_the_named_unpaired_flap_and_repacks(tmp_path):
    c = RepairClient({"name": "head", "reason": "a spider's head is part of the cephalothorax"})
    rec, tree2, pk2 = asyncio.run(PR.attempt(c, _png(tmp_path), SPIDER, envelope_packing(),
                                             pack=_pack_that_serves_at(9)))
    assert rec["outcome"] == "merged" and rec["fired"] is True
    assert rec["merged_flap"] == "head" and rec["merged_length"] == 2
    assert rec["before_flaps"] == 10 and rec["after_flaps"] == 9
    assert rec["packed"] is True and rec["stage"] == "flatten"
    assert rec["rungs_tried"] == 55 and rec["stages_tried"]["stub"] == 8
    assert rec["candidates"] == ["abdomen", "head"]
    assert "cephalothorax" in rec["model_reason"]
    assert rec["original_tree"] == SPIDER
    assert tree2 is not None and len(TA_leaves(tree2)) == 9
    assert pk2["served"] is True
    # exactly one model call, with the image and the tree JSON in it
    assert len(c.calls) == 1
    assert c.calls[0]["system"] == PR.REPAIR_SYSTEM
    assert c.calls[0]["tools"] == PR.MERGE_TOOL
    blob = json.dumps(c.calls[0]["messages"])
    assert "foot_1L" in blob and "image" in blob


def test_attempt_records_merged_but_not_packed(tmp_path):
    c = RepairClient({"name": "head", "reason": "fused"})
    rec, tree2, pk2 = asyncio.run(PR.attempt(c, _png(tmp_path), SPIDER, envelope_packing(),
                                             pack=_pack_that_serves_at(0)))
    assert rec["outcome"] == "merged" and rec["packed"] is False and rec["stage"] is None
    assert tree2 is not None and pk2["served"] is False


def test_attempt_refuses_a_paired_flap_and_spends_no_pack(tmp_path):
    packs = []
    def pack(tree):
        packs.append(tree); return envelope_packing()
    c = RepairClient({"name": "foot_1L", "reason": "shortest"})
    rec, tree2, pk2 = asyncio.run(PR.attempt(c, _png(tmp_path), SPIDER, envelope_packing(), pack=pack))
    assert rec["outcome"] == "refused" and "paired" in rec["refusal"]
    assert tree2 is None and pk2 is None and packs == []


def test_attempt_records_a_decline(tmp_path):
    c = RepairClient({"name": "none", "reason": "the abdomen and head both protrude"})
    rec, tree2, _ = asyncio.run(PR.attempt(c, _png(tmp_path), SPIDER, envelope_packing(),
                                           pack=_pack_that_serves_at(9)))
    assert rec["outcome"] == "declined" and rec["fired"] is True
    assert "protrude" in rec["model_reason"] and tree2 is None


def test_attempt_refuses_prose_with_no_tool_call(tmp_path):
    c = RepairClient(None, text="I would merge the head.")
    rec, tree2, _ = asyncio.run(PR.attempt(c, _png(tmp_path), SPIDER, envelope_packing(),
                                           pack=_pack_that_serves_at(9)))
    assert rec["outcome"] == "refused" and "no merge_flap call" in rec["refusal"]


def test_attempt_skips_without_a_model_call_when_the_ladder_did_not_run(tmp_path):
    c = RepairClient({"name": "head", "reason": "x"})
    pk = envelope_packing(error="ERROR: compilation timed out after 60s", detail=None)
    rec, tree2, _ = asyncio.run(PR.attempt(c, _png(tmp_path), SPIDER, pk,
                                           pack=_pack_that_serves_at(9)))
    assert rec["outcome"] == "skipped" and rec["fired"] is False
    assert "did not run to completion" in rec["skipped_because"]
    assert c.calls == [] and rec["rungs_tried"] == 0


def test_attempt_skips_without_a_model_call_when_nothing_is_unpaired(tmp_path):
    t = json.loads(json.dumps(SPIDER))
    t["nodes"] = [n for n in t["nodes"] if n["name"] not in ("abdomen", "head")]
    c = RepairClient({"name": "foot_1L", "reason": "x"})
    rec, _, _ = asyncio.run(PR.attempt(c, _png(tmp_path), t, envelope_packing(),
                                       pack=_pack_that_serves_at(9)))
    assert rec["outcome"] == "skipped" and "no unpaired flap" in rec["skipped_because"]
    assert c.calls == []


def test_record_crash_is_a_refusal_with_the_exception_text():
    rec = PR.record_crash(RuntimeError("boom"), SPIDER, envelope_packing())
    assert rec["outcome"] == "refused" and "RuntimeError: boom" in rec["refusal"]
    assert rec["original_tree"] == SPIDER and rec["rungs_tried"] == 55
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_pack_repair.py -k "attempt or record_crash" -q`
Expected: `AttributeError` on `attempt`.

- [ ] **Step 3: Implement**

Append to `mcp_harness/pack_repair.py`:

```python
def _base_record(tree: dict, packing: dict) -> dict:
    """The spec §6 record with every field present, before any outcome."""
    d = packing.get("detail") if isinstance(packing.get("detail"), dict) else {}
    n = len(TA.leaves_of(TA.to_tuples(tree)))
    return {"fired": False, "skipped_because": None,
            "rungs_tried": int(d.get("rungs_tried") or 0),
            "stages_tried": dict(d.get("stages_tried") or {}),
            "candidates": [], "outcome": "skipped",
            "merged_flap": None, "merged_length": None,
            "model_reason": None, "refusal": None,
            "before_flaps": n, "after_flaps": n,
            "packed": False, "stage": None,
            "reason": (packing.get("error") or "")[:400],
            "original_tree": json.loads(json.dumps(tree))}


def record_crash(exc: BaseException, tree: dict, packing: dict) -> dict:
    """For the caller's no-raise guard: a crash anywhere in the repair path is
    a REFUSED repair carrying the exception, never a lost tree."""
    rec = _base_record(tree, packing)
    rec.update({"fired": True, "outcome": "refused",
                "refusal": f"{type(exc).__name__}: {exc}"[:400]})
    return rec


async def attempt(client, mesh_png: str, tree: dict, packing: dict, *, pack):
    """One repair turn. Returns (record, new_tree | None, new_packing | None).

    `pack(tree) -> packing` is supplied by the caller (gated_pipeline builds
    the metric tree and runs its own `pack()`), so this module never imports
    the pipeline. `new_tree`/`new_packing` are non-None only for "merged".

    Order of gates, each cheaper than the next and each recorded:
      ladder exhausted?  -> else "skipped" (no model call)
      any unpaired flap? -> else "skipped" (no model call)
      model turn         -> no call: "refused";  name "none": "declined"
      apply_merge        -> refusal text: "refused"
      pack(new_tree)     -> "merged", packed True/False
    """
    import llm_client
    rec = _base_record(tree, packing)
    ok, why = ladder_exhausted(packing)
    if not ok:
        rec["skipped_because"] = why
        return rec, None, None
    cands = candidates(tree)
    rec["candidates"] = list(cands)
    if not cands:
        rec["skipped_because"] = "no unpaired flap: every flap is one of a bilateral pair"
        return rec, None, None

    rec["fired"] = True
    ask = (explain(packing, tree, cands)
           + "\n\nThe tree as authored:\n"
           + json.dumps({"nodes": tree["nodes"], "pairs": tree.get("pairs") or []},
                        indent=1))
    msgs = [llm_client.user_message_with_images(ask, [mesh_png])]
    r = await client.run_turn(REPAIR_SYSTEM, msgs, MERGE_TOOL)
    if not r.tool_calls:
        rec.update({"outcome": "refused",
                    "refusal": f"the model returned no merge_flap call "
                               f"(finish_reason: {r.finish_reason})"})
        return rec, None, None
    try:
        args = json.loads(r.tool_calls[0].function.arguments)
        name = str(args["name"]).strip()
        rec["model_reason"] = str(args.get("reason") or "")[:400]
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        rec.update({"outcome": "refused",
                    "refusal": f"the merge_flap arguments did not parse: {e}"})
        return rec, None, None
    if name.lower() == "none":
        rec["outcome"] = "declined"
        return rec, None, None
    new_tree, refusal = apply_merge(tree, name)
    if new_tree is None:
        rec.update({"outcome": "refused", "refusal": refusal})
        return rec, None, None

    length = {n[0]: n[3] for n in TA.to_tuples(tree)}
    new_packing = pack(new_tree)
    rec.update({"outcome": "merged", "merged_flap": name,
                "merged_length": length.get(name),
                "after_flaps": len(TA.leaves_of(TA.to_tuples(new_tree))),
                "packed": bool(new_packing.get("served")),
                "stage": new_packing.get("stage") if new_packing.get("served") else None})
    return rec, new_tree, new_packing
```

- [ ] **Step 4: Run the tests**

Run: `PYTEST tests/test_pack_repair.py -q`
Expected: 27 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pack_repair.py mcp_harness/tests/test_pack_repair.py
git commit -m "pack_repair.attempt: one merge_flap turn, gated by ladder exhaustion and unpaired candidates

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `describe` and the `summarise` repair block

**Files:**
- Modify: `mcp_harness/pack_repair.py`
- Modify: `mcp_harness/gated_pipeline.py:229-295` (`summarise`)
- Test: `mcp_harness/tests/test_pack_repair.py`, `mcp_harness/tests/test_gated_pipeline.py`

**Interfaces:**
- Produces: `describe(repair: dict) -> str`; `summarise(..., repair=None)` appends `describe(repair)` before the closing question when `repair is not None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_pack_repair.py`:

```python
# --------------------------------------------------------------------------
# describe -- the five gate blocks (spec §6)
# --------------------------------------------------------------------------

def _rec(**over):
    rec = PR._base_record(SPIDER, envelope_packing())
    rec.update(over)
    return rec


def test_describe_skipped():
    s = PR.describe(_rec(outcome="skipped", skipped_because="the rescue ladder did not run to completion: timed out"))
    assert s.startswith("Self-repair was not attempted: the rescue ladder")
    assert "original tree, which does not pack yet" in s


def test_describe_merged_and_packed_names_everything_the_human_needs():
    s = PR.describe(_rec(fired=True, outcome="merged", merged_flap="head", merged_length=2,
                         after_flaps=9, packed=True, stage="flatten",
                         model_reason="fused into the cephalothorax"))
    assert "polygon network is not valid" in s            # error head
    assert "all 55 deterministic rescue rungs failed" in s
    assert "stub 8" in s                                  # stage counts
    assert "`head` (2 units)" in s
    assert "fused into the cephalothorax" in s
    assert "nothing else changed (10 -> 9 flaps)" in s
    assert "packed at rescue stage `flatten`" in s


def test_describe_merged_not_packed_says_which_tree_is_shown():
    s = PR.describe(_rec(fired=True, outcome="merged", merged_flap="head", merged_length=2,
                         after_flaps=9, packed=False, model_reason="fused"))
    assert "still does not pack; you are seeing it, not the original" in s


def test_describe_declined_quotes_the_reason():
    s = PR.describe(_rec(fired=True, outcome="declined", model_reason="both protrude"))
    assert 'declined: "both protrude"' in s and "original tree" in s


def test_describe_refused_names_why():
    s = PR.describe(_rec(fired=True, outcome="refused", refusal="`foot_1L` is paired"))
    assert "refused: `foot_1L` is paired" in s and "original tree" in s
```

Append to `tests/test_gated_pipeline.py`:

```python
def test_the_summary_appends_the_repair_block_only_when_a_repair_record_exists():
    base = GP.summarise(_tree(), {"served": False, "stub_flaps": 0,
                                  "invents_anatomy": False,
                                  "what_changed": "this tree does not pack yet"},
                        ["head"])
    with_none = GP.summarise(_tree(), {"served": False, "stub_flaps": 0,
                                       "invents_anatomy": False,
                                       "what_changed": "this tree does not pack yet"},
                             ["head"], repair=None)
    assert with_none == base                               # byte-identical
    import pack_repair as PR
    from test_pack_repair import SPIDER, envelope_packing
    rec = PR._base_record(SPIDER, envelope_packing())
    rec.update({"outcome": "skipped", "skipped_because": "no unpaired flap"})
    s = GP.summarise(_tree(), {"served": False, "stub_flaps": 0,
                               "invents_anatomy": False,
                               "what_changed": "this tree does not pack yet"},
                     ["head"], repair=rec)
    assert "Self-repair was not attempted: no unpaired flap" in s
    assert s.rstrip().endswith("say what is wrong with it.")   # question stays last
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_pack_repair.py -k describe -q; PYTEST tests/test_gated_pipeline.py -k repair_block -q`
Expected: `AttributeError: describe`; `TypeError: unexpected keyword 'repair'`.

- [ ] **Step 3: Implement `describe`**

Append to `mcp_harness/pack_repair.py`:

```python
def describe(rec: dict) -> str:
    """The plain-English block `summarise` appends. Lives beside the verdict
    so the words and the outcome cannot drift (spec §6)."""
    tail_orig = "You are seeing the original tree, which does not pack yet."
    o = rec.get("outcome")
    if o == "skipped":
        return f"Self-repair was not attempted: {rec.get('skipped_because')}. {tail_orig}"
    if o == "declined":
        return (f"Self-repair was offered and the model declined: "
                f"\"{rec.get('model_reason')}\". {tail_orig}")
    if o == "refused":
        return f"Self-repair was attempted and refused: {rec.get('refusal')}. {tail_orig}"
    # merged
    head = (rec.get("reason") or "").split("[ladder:")[0].strip()
    head = head[len("ERROR: "):] if head.startswith("ERROR: ") else head
    counts = ", ".join(f"{s} {n}" for s, n in (rec.get("stages_tried") or {}).items())
    s = (f"Self-repair: the packer rejected the authored tree ({head}), and all "
         f"{rec.get('rungs_tried')} deterministic rescue rungs failed ({counts}). "
         f"The model chose to merge the unpaired flap `{rec.get('merged_flap')}` "
         f"({rec.get('merged_length')} units) into the trunk -- its reason: "
         f"\"{rec.get('model_reason')}\" -- and the pipeline removed that one node; "
         f"nothing else changed ({rec.get('before_flaps')} -> {rec.get('after_flaps')} flaps).")
    if rec.get("packed"):
        return s + f" The repaired tree packed at rescue stage `{rec.get('stage')}`."
    return s + " The repaired tree still does not pack; you are seeing it, not the original."
```

- [ ] **Step 4: Implement the `summarise` hook**

In `mcp_harness/gated_pipeline.py`, add `import pack_repair` after `import error_recipes`. Change the signature:

```python
def summarise(tree, packing, leaf_names, *, splits=None, unscored_pairs=None,
              dropped_pairs=None, figure_note=None, repair=None) -> str:
```

Add to the docstring's last paragraph: `` `repair` is the spec-§6 record from `pack_repair.attempt`, or None when the tree packed without one; it is disclosed in full because the tree the compiler received may differ from the authored one by exactly one node.``

Insert before `lines.append("Does this read as the animal? ...")`:

```python
    if repair is not None:
        lines.append(pack_repair.describe(repair))
```

- [ ] **Step 5: Run the tests**

Run: `PYTEST tests/test_pack_repair.py tests/test_gated_pipeline.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pack_repair.py mcp_harness/gated_pipeline.py mcp_harness/tests/test_pack_repair.py mcp_harness/tests/test_gated_pipeline.py
git commit -m "pack_repair.describe + summarise(repair=): the five gate blocks

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: The `_draft` hook

**Files:**
- Modify: `mcp_harness/gated_pipeline.py` (`_blank_state`, `_draft`)
- Test: `mcp_harness/tests/test_gated_pipeline.py`

**Interfaces:**
- Consumes: `pack_repair.attempt`, `pack_repair.record_crash`, `pack()`.
- Produces: `state["repair"]` (None or the §6 record); `_build(tree) -> tuple` helper.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gated_pipeline.py`:

```python
# --------------------------------------------------------------------------
# The repair hook in _draft (spec §4, §8 tests 6-12)
# --------------------------------------------------------------------------
from test_pack_repair import SPIDER, ENVELOPE, envelope_packing


class TwoToolClient(FakeClient):
    """FakeClient whose payload for the REPAIR turn is passed through as
    merge_flap arguments. Records which system prompt each call used."""

    async def run_turn(self, system, messages, tools):
        self.calls.append({"system": system, "messages": messages, "tools": tools})
        p = self._payloads.pop(0)
        if p is None:
            return FakeResult(None, "stop")
        return FakeResult(p)


def _repair_calls(c):
    import pack_repair as PR
    return [k for k in c.calls if k["system"] == PR.REPAIR_SYSTEM]


def _author_calls(c):
    return [k for k in c.calls if k["system"] == GP.TA.SYSTEM]


def _leaf_count(tree_nodes):
    kids = {}
    for n in tree_nodes:
        if n["parent_id"] is not None:
            kids[n["parent_id"]] = kids.get(n["parent_id"], 0) + 1
    return sum(1 for n in tree_nodes if kids.get(n["id"], 0) == 0)


def serves_at_most(n_max):
    def pack_fn(tree_nodes, pairs):
        if _leaf_count(tree_nodes) <= n_max:
            return fake_pack_ok(tree_nodes, pairs)
        return (ENVELOPE, {})
    return pack_fn


def test_a_bare_error_never_reaches_the_model(tmp_path, monkeypatch):
    """THE LAST-RESORT PROPERTY. Without the ladder's own exhaustion envelope,
    no repair turn is spent -- one authoring call, zero repair calls."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([SPIDER, {"name": "head", "reason": "x"}])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=lambda n, p: ("ERROR: POLYS_NOT_VALID", {})))
    assert len(_author_calls(c)) == 1 and _repair_calls(c) == []
    assert st["status"] == "awaiting_review"
    assert st["repair"]["outcome"] == "skipped" and st["repair"]["fired"] is False
    assert "Self-repair was not attempted" in st["summary"]
    assert st["tree"] == SPIDER                             # original shown


def test_a_full_envelope_spends_exactly_one_repair_turn_and_the_merge_packs(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([SPIDER, {"name": "head", "reason": "fused into the cephalothorax"}])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=serves_at_most(9)))
    assert len(_author_calls(c)) == 1 and len(_repair_calls(c)) == 1
    r = st["repair"]
    assert r["outcome"] == "merged" and r["merged_flap"] == "head" and r["packed"] is True
    assert st["packing"]["served"] is True
    assert st["revisions_authored"] == 0 and st["round"] == 0
    assert "head" not in [n["name"] for n in st["tree"]["nodes"]]   # repaired tree shown
    assert r["original_tree"] == SPIDER
    assert st["metric_tree"]["names"]                                # rebuilt for 9 flaps
    assert len(st["metric_tree"]["tree_nodes"]) == len(SPIDER["nodes"]) - 1
    assert "The repaired tree packed" in st["summary"]
    assert "10 -> 9 flaps" in st["summary"]


def test_a_paired_name_is_refused_and_the_original_is_shown(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([SPIDER, {"name": "foot_1L", "reason": "shortest"}])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=serves_at_most(9)))
    assert len(_repair_calls(c)) == 1
    assert st["repair"]["outcome"] == "refused" and "paired" in st["repair"]["refusal"]
    assert st["tree"] == SPIDER and st["packing"]["served"] is False
    assert "refused: `foot_1L` is paired" in st["summary"]


def test_a_decline_keeps_the_original_and_quotes_the_reason(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([SPIDER, {"name": "none", "reason": "the abdomen and head are both real"}])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=serves_at_most(9)))
    assert st["repair"]["outcome"] == "declined"
    assert st["tree"] == SPIDER
    assert 'declined: "the abdomen and head are both real"' in st["summary"]


def test_prose_with_no_tool_call_is_refused(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([SPIDER, None])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=serves_at_most(9)))
    assert st["repair"]["outcome"] == "refused" and st["tree"] == SPIDER


def test_a_merge_that_still_fails_shows_the_repaired_tree(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([SPIDER, {"name": "head", "reason": "fused"}])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=lambda n, p: (ENVELOPE, {})))
    assert st["status"] == "awaiting_review"
    assert st["repair"]["outcome"] == "merged" and st["repair"]["packed"] is False
    assert "head" not in [n["name"] for n in st["tree"]["nodes"]]
    assert "still does not pack; you are seeing it, not the original" in st["summary"]


def test_a_tree_that_packs_has_no_repair_and_an_unchanged_summary(tmp_path, monkeypatch):
    """The 14 packing subjects must not change at all."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    c = TwoToolClient([DOG])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=fake_pack_ok))
    assert len(c.calls) == 1 and st["repair"] is None
    assert "Self-repair" not in st["summary"]
    expected = GP.summarise(DOG, st["packing"], ["head", "tail"],
                            splits=[], unscored_pairs=[], dropped_pairs=[])
    assert st["summary"] == expected


def test_a_crash_inside_the_repair_path_is_a_refusal_not_an_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    import pack_repair as PR

    async def boom(*a, **k):
        raise RuntimeError("boom")
    monkeypatch.setattr(PR, "attempt", boom)
    c = TwoToolClient([SPIDER])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=lambda n, p: (ENVELOPE, {})))
    assert st["status"] == "awaiting_review"
    assert st["repair"]["outcome"] == "refused" and "RuntimeError: boom" in st["repair"]["refusal"]
    assert st["tree"] == SPIDER
```

⚠ `test_a_tree_that_packs_has_no_repair_and_an_unchanged_summary` compares against `summarise` called the way `_draft` calls it for DOG today (two unpaired leaves → `splits == []`, no unscored, no dropped). If the existing `_draft` passes different kwargs for this fixture, read `_draft` and match them exactly — the property under test is byte-identity with the pre-change output, so before editing `_draft`, print `st["summary"]` from the existing `test_start_pauses_at_awaiting_review_with_a_figure` (add a temporary `print`, run it with `-s`, remove the print) and pin that exact string in this test if the `summarise` call shape differs. Never use bare `git stash` in this worktree.

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_gated_pipeline.py -k "repair or bare_error or envelope or decline or prose or crash or unchanged_summary" -q`
Expected: failures with `KeyError: 'repair'`.

- [ ] **Step 3: Implement**

In `mcp_harness/gated_pipeline.py`:

(a) `_blank_state`: add `"repair": None,` after `"revisions_authored": 0`.

(b) Factor the derivation into a helper placed just above `_draft`:

```python
def _build(tree):
    """Authored tree -> (nodes, leaf_names, keep, dropped, tn, sp, names,
    grid_per_unit). One place, because the repair hook has to rebuild all of
    it for a tree that differs from the authored one by one node."""
    nodes = TA.to_tuples(tree)
    leaf_names = TA.leaves_of(nodes)
    keep, dropped = TA.leaf_pairs(tree, leaf_names)
    tn, sp, names = TA.metric_tree(nodes, keep)
    grid_per_unit = (max(n[3] for n in nodes) or 1) / TA.LONGEST_LIMB_TARGET
    return nodes, leaf_names, keep, dropped, tn, sp, names, grid_per_unit
```

(c) In `_draft`, replace the five-line derivation inside the first `try:` with:

```python
    try:
        nodes, leaf_names, keep, dropped, tn, sp, names, grid_per_unit = _build(tree)
    except Exception as e:                                  # noqa: BLE001
        return _fail(state, f"the metric tree could not be built from the "
                            f"authored tree: {type(e).__name__}: {e}")
```

(d) Immediately after the `packing = pack(...)` try/except block, insert:

```python
    # ⚠ THE VLM IS THE LAST RESORT (owner ruling 2026-09-12). `pack()` has
    # already walked the whole deterministic ladder; `pack_repair.attempt`
    # re-checks that off the envelope and spends a model turn only then. The
    # model names ONE unpaired flap; code performs the edit; the human is told
    # exactly what changed. Nothing here may raise (see the block above).
    repair = None
    if not packing["served"]:
        def _repack(t):
            _nodes, _leaves, _keep, _dropped, tn2, sp2, _names, _g = _build(t)
            return pack(tn2, sp2, pack_fn=pack_fn)
        try:
            repair, new_tree, new_packing = await pack_repair.attempt(
                client, mesh_png, tree, packing, pack=_repack)
        except Exception as e:                              # noqa: BLE001
            repair, new_tree, new_packing = pack_repair.record_crash(e, tree, packing), None, None
        if repair.get("outcome") == "merged" and new_tree is not None:
            tree, packing = new_tree, new_packing
            nodes, leaf_names, keep, dropped, tn, sp, names, grid_per_unit = _build(tree)
```

(e) In `state.update({...})` at the end of `_draft`, add `"repair": repair,` and pass `repair=repair` to the `summarise(...)` call.

- [ ] **Step 4: Run the whole harness suite for these two files**

Run: `PYTEST tests/test_gated_pipeline.py tests/test_pack_repair.py -q`
Expected: all pass. If `test_a_tree_that_packs_has_no_repair_and_an_unchanged_summary` fails on the `expected` comparison only, follow the ⚠ note in Step 1.

- [ ] **Step 5: Run the wider fast suite to catch import-order or signature drift**

Run: `PYTEST tests/test_gated_pipeline.py tests/test_pack_repair.py tests/test_tree_authoring.py tests/test_eval_vlm_pipeline.py -q` (skip the last file if it does not exist: `ls mcp_harness/tests | grep eval_vlm`).
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tests/test_gated_pipeline.py
git commit -m "gated_pipeline: one last-resort pack_repair turn after a failed pack; state.repair; _build() helper

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: Rule 4 — the fused-head carve-out

**Files:**
- Modify: `mcp_harness/tree_authoring.py:65-69`
- Test: `mcp_harness/tests/test_tree_authoring.py`

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_tree_authoring.py`:

```python
def test_rule_4_says_a_fused_head_is_trunk_not_a_flap():
    """2026-09-12: spider, crab and scorpion each authored a `head` flap the
    animal does not have as a protruding appendage, and that one flap was the
    whole difference between packing and the packer wall. Stated as anatomy,
    with no mention of packing."""
    s = TA.SYSTEM
    assert "LEAF CONVENTION" in s                          # the pinned token survives
    assert "ONLY when it protrudes" in s
    assert "cephalothorax or carapace" in s
    assert "TRUNK, not a flap" in s
    assert "the head counts one;" not in s                 # the old unconditional clause is gone
    assert "pack" not in s.split("4. LEAF CONVENTION")[1].split("5. STRUCTURE")[0].lower()
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTEST tests/test_tree_authoring.py -q`
Expected: 1 failure on `"ONLY when it protrudes" in s`.

- [ ] **Step 3: Edit the prompt**

In `mcp_harness/tree_authoring.py`, replace the rule-4 text (it is a `\`-continued string; keep the same line-continuation style as its neighbours):

```python
4. LEAF CONVENTION. One leaf per terminal appendage: each limb, wing, tentacle \
or ray counts one; the tail counts one when the animal has an external tail. \
The head counts one ONLY when it protrudes from the body on a neck or as a \
distinct lobe (mammals, birds, reptiles, most fish). A head fused into the \
trunk -- a cephalothorax or carapace (spiders, scorpions, crabs), or a body \
that simply tapers to a mouth -- is TRUNK, not a flap, and gets no leaf. \
Digits, toes, ears, antennae and eyes are sub-flap detail and DO NOT count as \
leaves.
```

Do NOT edit `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/loop_lib.py` — it is the frozen prompt that produced the committed figures.

- [ ] **Step 4: Run the tests**

Run: `PYTEST tests/test_tree_authoring.py tests/test_gated_pipeline.py -q`
Expected: all pass (the five pinned tokens are untouched).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tree_authoring.py mcp_harness/tests/test_tree_authoring.py
git commit -m "tree_authoring rule 4: a head fused into a cephalothorax/carapace is trunk, not a flap

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: The live measurement — `repair_rolls.py`

Runs the real pipeline. Needs the funded Anthropic key in the repo-root `.env` (never print it), `LLM_MAX_TOKENS=64000`, and ~30–60 minutes. Sequential — the compile path is spawn-based and `server._LAST_SERVE` is global.

**Files:**
- Create: `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/repair_rolls.py`
- Create (by running): `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/repair_rolls.json`

- [ ] **Step 1: Write the driver**

```python
"""Spider, scorpion, crab x 3 rolls through the PRODUCTION gated pipeline, to
measure the last-resort repair turn (spec 2026-09-12-vlm-pack-repair-design §9).

Each roll is a fresh authoring (no temperature lever exists on this model), so
the headline is the 9-row table, not a single number. Expectation stated before
running: spider (10 -> 9 after a head merge) improves; crab (11 -> 10) and
scorpion (12 -> 11) mostly still fail. A DECLINE on a real appendage is a
success for this slice.

Inputs are the committed arm-C mesh renders; `vlm_render.render_mesh_views` is
stubbed to pass them through (the .glb binaries are not in-repo). Everything
downstream -- authoring, the whole rescue ladder, the repair turn, the compile
-- is the real serve path. Resumable: rows already in the output are skipped.
"""
from __future__ import annotations
import argparse, asyncio, json, os, sys, time

S = os.path.dirname(os.path.abspath(__file__))
H = "<repo>/mcp_harness"
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, "tests"))
os.chdir(H)
import env_config; env_config.load_env()
os.environ["LLM_MAX_TOKENS"] = "64000"

import llm_client, vlm_render, gated_pipeline, tree_authoring as TA

vlm_render.render_mesh_views = lambda mesh_path, out_path, **kw: {"png": mesh_path, "grid": None, "views": []}

SUBJECTS = ["spider", "scorpion", "crab"]
OUT = os.path.join(S, "..", "data", "repair_rolls.json")
WORK = os.path.join(S, "repair_rolls_out")


def _flaps(tree):
    return len(TA.leaves_of(TA.to_tuples(tree))) if tree else None


def _row(subject, roll, state, seconds):
    r = state.get("repair") or {}
    pk = state.get("packing") or {}
    authored = r.get("original_tree") or state.get("tree")
    return {"subject": subject, "roll": roll, "status": state.get("status"),
            "authored_flaps": _flaps(authored),
            "rungs_tried": r.get("rungs_tried"), "stages_tried": r.get("stages_tried"),
            "candidates": r.get("candidates"), "outcome": r.get("outcome") if r else "packed",
            "merged_flap": r.get("merged_flap"), "model_reason": r.get("model_reason"),
            "refusal": r.get("refusal"), "skipped_because": r.get("skipped_because"),
            "repaired_flaps": r.get("after_flaps") if r.get("outcome") == "merged" else None,
            "packed": bool(pk.get("served")), "stage": pk.get("stage"),
            "seconds": round(seconds, 1), "note": state.get("note")}


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rolls", type=int, default=3)
    ap.add_argument("--only", default=None)
    a = ap.parse_args()
    subs = a.only.split(",") if a.only else SUBJECTS
    os.makedirs(WORK, exist_ok=True)
    rows = json.load(open(OUT)) if os.path.exists(OUT) else []
    done = {(r["subject"], r["roll"]) for r in rows}
    cfg = llm_client.LLMConfig.from_env()
    print(f"provider={cfg.provider} model={cfg.model} max_tokens={cfg.max_tokens}", flush=True)
    client = llm_client.LLMClient(cfg)
    for s in subs:
        for k in range(a.rolls):
            if (s, k) in done:
                continue
            png = f"{S}/gridtest/C/{s}.png"
            t0 = time.time()
            try:
                st = await gated_pipeline.start(png, client=client,
                                                out_dir=os.path.join(WORK, f"{s}_{k}"))
            except Exception as e:                          # noqa: BLE001
                st = {"status": "driver_error", "note": f"{type(e).__name__}: {str(e)[:300]}"}
            row = _row(s, k, st, time.time() - t0)
            rows.append(row)
            json.dump(rows, open(OUT, "w"), indent=1)
            print(f"{s:9} roll {k}: authored={row['authored_flaps']} outcome={row['outcome']} "
                  f"merged={row['merged_flap']} packed={row['packed']} stage={row['stage']} "
                  f"rungs={row['rungs_tried']} {row['seconds']}s", flush=True)
    print(f"\n{len(rows)} rows in {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Smoke it offline first (no key spent)**

Run: `cd mcp_harness && <repo>/.venv/bin/python -c "import ast,sys; ast.parse(open('../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/repair_rolls.py').read()); print('syntax ok')"`
Expected: `syntax ok`.

- [ ] **Step 3: Run it (background; ~30–60 min)**

```bash
cd <repo>/docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts && <repo>/.venv/bin/python repair_rolls.py 2>&1 | tee repair_rolls.log
```

Expected: nine `spider/scorpion/crab roll k:` lines and `9 rows in .../data/repair_rolls.json`. If a roll ends `status=failed` (authoring truncation or contract failure), that row is kept as data — do not re-roll it by hand.

- [ ] **Step 4: Read the table and write the evidence note**

Run:
```bash
<repo>/.venv/bin/python - <<'EOF'
import json
rows=json.load(open("docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/repair_rolls.json"))
print(f"{'subject':9} {'roll':4} {'auth':4} {'rungs':5} {'outcome':8} {'merged':10} {'packed':6} stage    reason")
for r in rows:
    print(f"{r['subject']:9} {r['roll']:4} {str(r['authored_flaps']):4} {str(r['rungs_tried']):5} "
          f"{str(r['outcome']):8} {str(r['merged_flap']):10} {str(r['packed']):6} {str(r['stage']):8} "
          f"{(r['model_reason'] or r['refusal'] or r['skipped_because'] or '')[:60]}")
EOF
```

Append a section `## 2026-09-12 — repair_rolls (last-resort VLM merge turn)` to `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/README.md` (create the file if absent) containing: the printed table, the pre-stated expectation from the spec §9, and one paragraph of what actually happened — including any `declined` rows and their reasons verbatim, and whether `rungs_tried` was ≥ 1 on every fired row.

- [ ] **Step 5: Commit the driver, data, log and note**

```bash
git add docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/repair_rolls.py docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/repair_rolls.json docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/README.md
git commit -m "evidence: repair_rolls -- spider/scorpion/crab x3 through the last-resort merge turn

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

Do not commit `repair_rolls_out/` (per-roll PNG sheets and folds) or `repair_rolls.log` unless the evidence directory already tracks equivalents for `run17`; check with `git ls-files docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts | head`.

---

## Self-review against the spec

- §4.1 last resort → Task 1 (`detail` kept), Task 2 (`ladder_exhausted`), Task 7 test `test_a_bare_error_never_reaches_the_model`. ✓
- §5.0 model never edits → Task 3 (`apply_merge` is the only edit; identity test), Task 5 (`attempt` only parses a name). ✓
- §5.2 unpaired only → Task 3 `candidates`, refusal on paired in Tasks 3/5/7. ✓
- §5.1 explain / window from `mesh_to_tree` / DETAIL stripped → Task 4. ✓
- §5.3 tool + acceptance table (no call / none / not candidate / contract) → Tasks 3, 5. ✓
- §4.2 no-raise, separate budget → Task 7 (`record_crash`, `revisions_authored == 0`). ✓
- §6 state record fields and five blocks → Task 5 `_base_record`, Task 6 `describe`. ✓
- §7 rule 4 → Task 8. ✓
- §8 tests 1–13 → Tasks 2–8 (test 12 byte-identity is Task 7's `unchanged_summary`). ✓
- §9 measurement + columns → Task 9. ✓
- Type consistency: `attempt` returns `(rec, tree|None, packing|None)` in Task 5 and is consumed that way in Task 7; `pack=` callable takes a TREE dict in both; `describe(rec)` in Task 6 matches `summarise(repair=rec)`; `_base_record(tree, packing)` used by Tasks 5, 6 and the Task 6 pipeline test. ✓
- Placeholders: none. Every step has code or an exact command.

# S5 — Human Gate & Eval Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pausable mesh→tree pipeline that stops after making a tree
packable, shows a human a four-view figure, takes free-text feedback, and
either continues or revises — plus one offline command that regenerates every
number this branch quotes.

**Architecture:** Three new modules in `mcp_harness/`. `tree_authoring.py`
holds the authoring contract (system prompt, `submit_tree` schema, tuple
helpers) that currently lives in an evidence script and cannot be imported.
`gated_pipeline.py` is the pausable object: `start()` and `resume()` exchange a
plain JSON-serialisable `State`, so the pause is a return value rather than a
blocking prompt. `eval_vlm_pipeline.py` recomputes the scorecard from committed
data with no network.

**Tech Stack:** Python 3.14, pytest, PIL, trimesh, the repo's vendored
TreeMaker `.so` via `server.draft_and_compile_full_base`.

**Spec:** `docs/superpowers/specs/2026-09-10-s5-human-gate-design.md`

## Global Constraints

- Run every command from `mcp_harness/`. The interpreter is
  `<repo>/.venv/bin/python`.
- **Never `python - <<EOF`.** Heredoc-to-stdin cannot drive the spawn workers
  `compile_tree` uses; it fails with `FileNotFoundError: '<stdin>'`. Use a real
  `.py` file with an `if __name__ == "__main__":` guard, or `python -c`.
- **Every runnable `.py` needs an `if __name__ == "__main__":` guard.** An
  unguarded module re-runs its whole body inside every spawned worker.
- `MAX_REVISIONS = 3`. The first draft is `round = 0`; revisions author rounds
  1–3; a request for round 4 is refused **before** the model is called.
- `render_tree_sheet` must never be added to `agent_loop.IMAGE_RESULT_TOOLS`
  and no revision message may carry an image. Measured: showing a model its own
  figure scored MAE 0.53 against 0.29 for no review.
- Never rescale measured proportions to force a pack.
- Docstrings explain **why**, and record what was measured. This repo's
  convention is that a surprising line carries its evidence.

---

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/tree_authoring.py` | **new.** The authoring contract: `SYSTEM`, `TOOL`, `to_tuples`, `leaves_of`, `metric_tree`. Pure data and pure functions, no I/O, no network. |
| `mcp_harness/gated_pipeline.py` | **new.** `start`, `resume`, `State`, and the internals `_author`, `_pack`, `summarise`. |
| `mcp_harness/eval_vlm_pipeline.py` | **new.** One offline command; imports the metric modules, reads committed JSON, writes one scorecard. |
| `mcp_harness/tests/test_tree_authoring.py` | **new.** |
| `mcp_harness/tests/test_gated_pipeline.py` | **new.** |
| `mcp_harness/tests/test_eval_vlm_pipeline.py` | **new.** |

Nothing existing is modified. That is deliberate: S5's scope excludes MCP and
frontend wiring, so no shipped tool's contract changes.

---

### Task 1: `tree_authoring.py` — the authoring contract, in production

The system prompt and `submit_tree` schema live in
`docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/loop_lib.py`,
whose README says **"Do not import."** Production cannot author a tree until
they move.

**Files:**
- Create: `mcp_harness/tree_authoring.py`
- Test: `mcp_harness/tests/test_tree_authoring.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `SYSTEM: str`, `TOOL: list[dict]`,
  `to_tuples(tree: dict) -> list[tuple[str, str|None, list[float]|None, float]]`,
  `leaves_of(nodes) -> list[str]`,
  `metric_tree(nodes, pairs) -> tuple[list[dict], list[list[int]], dict[int, str]]`,
  `LONGEST_LIMB_TARGET = 0.40`.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_tree_authoring.py`:

```python
"""The authoring contract, moved into production.

The prompt and schema were an evidence script whose README says "Do not
import". These tests pin the clauses that were PAID FOR -- each one is in the
prompt because a measured run went wrong without it.
"""
from __future__ import annotations

import tree_authoring as TA


def test_the_prompt_carries_every_clause_a_run_paid_for():
    s = TA.SYSTEM
    # the two-frames warning: 3 of 17 trees came back upside down without it
    assert "FLIP THE SIGN" in s
    assert "DOWNWARD" in s
    # rule 6: 3 of 17 authored one leg with a forked foot without it
    assert "EACH SIDE IS ITS OWN CHAIN" in s
    # the readings rule -- what makes fabrication visible in the artifact
    assert "READ BEFORE YOU DERIVE" in s
    # the counting convention rides here; the expected COUNT never does
    assert "LEAF CONVENTION" in s
    assert "expected_feature_count" not in s


def test_the_tool_schema_requires_direction_on_every_node():
    """Without `direction` there is no pose, the stick figure cannot be drawn,
    and the human gate has nothing to show. The 2026-09-07 run omitted it and
    its trees could only be drawn as dendrograms."""
    props = TA.TOOL[0]["function"]["parameters"]["properties"]
    node = props["nodes"]["items"]
    assert "direction" in node["properties"]
    assert set(node["required"]) == {"name", "parent", "length", "direction"}


def test_to_tuples_gives_the_root_a_null_direction():
    t = {"nodes": [{"name": "root", "parent": None, "length": 0, "direction": [0, 0, 0]},
                   {"name": "head", "parent": "root", "length": 9, "direction": [1, 0, 0]}]}
    assert TA.to_tuples(t) == [("root", None, None, 0), ("head", "root", [1, 0, 0], 9)]


def test_leaves_of_names_the_childless_nodes():
    nodes = [("root", None, None, 0), ("a", "root", [1, 0, 0], 3),
             ("b", "a", [1, 0, 0], 3), ("c", "root", [0, 1, 0], 4)]
    assert sorted(TA.leaves_of(nodes)) == ["b", "c"]


def test_metric_tree_scales_the_longest_edge_to_the_packing_regime():
    """0.40 is mesh_to_tree.LONGEST_LIMB_TARGET -- the regime every other tree
    in this project is compiled in. A tree built at a different scale is not
    comparable to any committed number."""
    nodes = [("root", None, None, 0), ("a", "root", [1, 0, 0], 10),
             ("b", "root", [0, 1, 0], 5)]
    tn, pairs, names = TA.metric_tree(nodes, [])
    assert max(n["length"] for n in tn) == TA.LONGEST_LIMB_TARGET
    assert [n["length"] for n in tn] == [0.0, 0.40, 0.20]
    assert names == {0: "root", 1: "a", 2: "b"}


def test_metric_tree_maps_pair_names_to_ids():
    nodes = [("root", None, None, 0), ("L", "root", [0, 0, 1], 4),
             ("R", "root", [0, 0, -1], 4)]
    _, pairs, _ = TA.metric_tree(nodes, [("L", "R")])
    assert pairs == [[1, 2]]
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_tree_authoring.py -q
```

Expected: `ModuleNotFoundError: No module named 'tree_authoring'`.

- [ ] **Step 3: Create the module, copying the prompt verbatim**

Copy the prompt and schema across rather than retyping them — a hand-retyped
60-line prompt drifts silently, and this one's clauses were each bought with a
measured run. Create `mcp_harness/_copy_prompt.py`:

```python
"""One-shot: lift SYSTEM and TOOL out of the evidence script into production."""
import re

SRC = ("../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/"
       "scripts/loop_lib.py")


def main():
    src = open(SRC).read()
    sys_block = src[src.index('SYSTEM = """'):src.index('\nTOOL = [')]
    tool_block = src[src.index("TOOL = ["):src.index("\n\n\ndef to_tuples")]
    header = '''"""The authoring contract: what the model is told, and what it may return.

MOVED INTO PRODUCTION 2026-09-10 (S5). These lived in
`docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/loop_lib.py`,
whose README says "Do not import" -- so nothing shippable could author a tree.
The text is copied VERBATIM rather than retyped: every clause in it was bought
with a measured run, and a silent transcription drift would be invisible.

WHAT EACH LOAD-BEARING CLAUSE COST
  "FLIP THE SIGN"            3 of 17 trees came back with their limbs in the
                             air, scoring EXACT on every numeric metric.
  "EACH SIDE IS ITS OWN CHAIN"  3 of 17 authored one leg ending in a forked
                             foot -- the horse's hind pair 2 units of 22 apart.
  "READ BEFORE YOU DERIVE"   the rule that makes fabrication visible in the
                             artifact instead of detectable only by re-measuring.
  "LEAF CONVENTION"          the counting RULE rides here; the expected COUNT
                             never does. Feeding the count closes the loop that
                             §7 scores against.
"""
from __future__ import annotations

#: mesh_to_tree.LONGEST_LIMB_TARGET -- the packing regime every other tree in
#: this project is compiled in. A tree built at another scale is not comparable
#: to any committed number.
LONGEST_LIMB_TARGET = 0.40


'''
    helpers = '''

def to_tuples(tree: dict) -> list:
    """Model output -> (name, parent, direction, length) tuples.

    A root with an all-zero direction becomes `None`, which is what
    `vlm_render.positions` reads as "this node is the origin".
    """
    out = []
    for n in tree["nodes"]:
        d = n.get("direction") or [1, 0, 0]
        if not any(d):
            d = None if n.get("parent") is None else [1, 0, 0]
        out.append((n["name"], n.get("parent"), d, n["length"]))
    return out


def leaves_of(nodes) -> list:
    """Names of the nodes with no children -- the flaps TreeMaker will pack."""
    kids: dict = {}
    for name, parent, _, _ in nodes:
        if parent:
            kids[parent] = kids.get(parent, 0) + 1
    return [n[0] for n in nodes if kids.get(n[0], 0) == 0]


def metric_tree(nodes, pairs):
    """(name, parent, direction, length) tuples -> the repo Metric Tree format.

    Returns (tree_nodes, symmetric_pairs, names). Lengths are scaled so the
    longest EDGE is LONGEST_LIMB_TARGET; `names` maps the emitted integer ids
    back to the model's own labels, which is what lets a report say "front
    hoof" instead of "node 14".
    """
    idx = {n[0]: i for i, n in enumerate(nodes)}
    mx = max(n[3] for n in nodes) or 1
    k = LONGEST_LIMB_TARGET / mx
    tn = [{"id": i,
           "parent_id": (idx[n[1]] if n[1] is not None else None),
           "length": round(n[3] * k, 6)}
          for i, n in enumerate(nodes)]
    return (tn,
            [[idx[a], idx[b]] for a, b in pairs],
            {i: n[0] for i, n in enumerate(nodes)})
'''
    open("tree_authoring.py", "w").write(header + sys_block + tool_block + helpers)
    print("wrote tree_authoring.py")


if __name__ == "__main__":
    main()
```

Run it, then delete it:

```bash
cd mcp_harness && <repo>/.venv/bin/python _copy_prompt.py && rm _copy_prompt.py
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_tree_authoring.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tree_authoring.py mcp_harness/tests/test_tree_authoring.py
git commit -m "S5: move the authoring contract into production

The system prompt and submit_tree schema lived in an evidence script whose
README says 'Do not import', so nothing shippable could author a tree. Copied
verbatim rather than retyped: every clause was bought with a measured run and a
transcription drift would be invisible. Tests pin the four load-bearing clauses
and that the expected leaf COUNT never appears in the prompt.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: the packability step

**Files:**
- Create: `mcp_harness/gated_pipeline.py`
- Test: `mcp_harness/tests/test_gated_pipeline.py`

**Interfaces:**
- Consumes: `tree_authoring.metric_tree` (Task 1).
- Produces: `pack(tree_nodes, symmetric_pairs, *, pack_fn=None) -> dict` with keys
  `served: bool`, `stage: str|None`, `served_nodes: list[dict]|None`,
  `invents_anatomy: bool`, `stub_flaps: int`, `what_changed: str`,
  `fold: str|None`, `error: str|None`.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_gated_pipeline.py`:

```python
"""The pausable pipeline. Every test runs with a FAKE client and a FAKE packer,
so the whole loop is exercised with no network, no spawned compile and no human.
"""
from __future__ import annotations

import json

import pytest

import gated_pipeline as GP


def fake_pack_ok(tree_nodes, symmetric_pairs):
    """A serve that packed at attempt 0, unchanged."""
    return ("{\\"vertices_coords\\": [], \\"frame_title\\": \\"\\"}",
            {"requested": [dict(n) for n in tree_nodes],
             "served": [dict(n) for n in tree_nodes]})


def test_pack_reports_an_unchanged_serve_as_such():
    tn = [{"id": 0, "parent_id": None, "length": 0.0},
          {"id": 1, "parent_id": 0, "length": 0.4},
          {"id": 2, "parent_id": 0, "length": 0.3}]
    out = GP.pack(tn, [], pack_fn=fake_pack_ok)
    assert out["served"] is True
    assert out["invents_anatomy"] is False
    assert out["what_changed"] == "it packed exactly as drafted"


def test_pack_names_a_reorder_as_invisible():
    tn = [{"id": 0, "parent_id": None, "length": 0.0},
          {"id": 1, "parent_id": 0, "length": 0.4},
          {"id": 2, "parent_id": 0, "length": 0.3}]

    def reordered(nodes, pairs):
        return ("{\\"vertices_coords\\": []}",
                {"requested": [dict(n) for n in nodes],
                 "served": [dict(n) for n in reversed(nodes)]})

    out = GP.pack(tn, [], pack_fn=reordered)
    assert "reordered" in out["what_changed"]
    assert "figure is unchanged" in out["what_changed"]


def test_pack_reports_a_failure_without_pretending():
    def fails(nodes, pairs):
        return ("ERROR: POLYS_MULTIPLE_IBPS", {})

    out = GP.pack([{"id": 0, "parent_id": None, "length": 0.0}], [], pack_fn=fails)
    assert out["served"] is False
    assert out["fold"] is None
    assert "POLYS_MULTIPLE_IBPS" in out["error"]
    assert out["what_changed"] == "this tree does not pack yet"
```

- [ ] **Step 2: Run it to verify it fails**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `ModuleNotFoundError: No module named 'gated_pipeline'`.

- [ ] **Step 3: Write the module**

Create `mcp_harness/gated_pipeline.py`:

```python
"""The mesh -> tree pipeline, paused at a human.

WHY THE PAUSE IS A RETURN VALUE. Every other human-in-the-loop point in this
repository is prompt discipline: the agent is told to propose and wait, and
nothing checks that it did. Two defect classes have reached a finished-looking
tree here -- inverted limbs and fused limbs -- and BOTH were caught by a person
looking at a picture after every numeric metric passed. A gate that matters
cannot be a sentence in a prompt, so `start()` stops and returns, and `resume()`
carries the human's answer back in.

That also makes the whole loop testable with a fake client and no human, which
prompt discipline never is.
"""
from __future__ import annotations

import json
import os

import rescue_ladder
import tree_authoring as TA
import vlm_render

#: Cited, not chosen: iterative critique saturates after roughly three rounds
#: (arXiv:2507.05598 and related), beyond which further passes are flat or
#: negative. The first draft is round 0; revisions author rounds 1-3.
MAX_REVISIONS = 3

#: Rounds of `validate_tree` repair inside ONE authoring attempt.
MAX_VALIDATE = 2


def _default_pack_fn(tree_nodes, symmetric_pairs):
    """Compile through the real serve path and hand back its own record.

    Imported lazily because `server` pulls in sklearn and mcp -- a ~1.1s import
    that every spawned compile worker pays, and that a test with a fake packer
    should not pay at all.
    """
    import server
    server._LAST_SERVE.clear()
    fold = server.draft_and_compile_full_base(tree_nodes, symmetric_pairs)
    return fold, dict(server._LAST_SERVE)


def pack(tree_nodes, symmetric_pairs, *, pack_fn=None):
    """Run the packability rescue and describe what it did, in plain words.

    ⚠ THIS RUNS BEFORE THE HUMAN SEES ANYTHING, which is the opposite of the
    parent spec's original diagram and was ruled by the owner 2026-09-10.
    Measured on 17 subjects: the rescue is invisible in the figure for 15 of
    them, so for most subjects the ordering makes no difference -- but for the
    two where joints are merged, gating afterwards means the human approves the
    tree the compiler will actually receive.
    """
    import mesh_to_tree
    fn = pack_fn or _default_pack_fn
    fold, last = fn(tree_nodes, symmetric_pairs)
    served = isinstance(fold, str) and not fold.startswith("ERROR:")
    if not served:
        return {"served": False, "stage": None, "served_nodes": None,
                "invents_anatomy": False, "stub_flaps": 0, "fold": None,
                "error": str(fold)[:400],
                "what_changed": "this tree does not pack yet"}

    stage = mesh_to_tree.served_stage(fold)
    stubs = mesh_to_tree.served_stub_flaps(fold)
    srv = last.get("served") or [dict(n) for n in tree_nodes]
    req = last.get("requested") or [dict(n) for n in tree_nodes]
    return {"served": True, "stage": stage, "served_nodes": srv,
            "invents_anatomy": stage in rescue_ladder.INVENTS_ANATOMY,
            "stub_flaps": int(stubs or 0), "fold": fold, "error": None,
            "what_changed": _what_changed(stage, req, srv, stubs)}


def _what_changed(stage, req, srv, stubs) -> str:
    """One sentence a person can act on, not a log line."""
    if stage == rescue_ladder.STAGE_STUB:
        return (f"no rescue that preserved your anatomy could pack it, so the "
                f"engine ADDED {stubs} flap(s) that are not anatomy")
    if stage == rescue_ladder.STAGE_FLATTEN:
        return (f"{len(req) - len(srv)} pass-through joints were merged away "
                "(lossless: every flap and every distance between flaps is "
                "exactly as you specified)")
    if stage == rescue_ladder.STAGE_PLACEMENT:
        return "initial positions were seeded; the figure is unchanged"
    if stage == rescue_ladder.STAGE_ORDER:
        return "the node list was reordered; the figure is unchanged"
    root_req = next((n["id"] for n in req if n["parent_id"] is None), None)
    root_srv = next((n["id"] for n in srv if n["parent_id"] is None), None)
    if root_req != root_srv:
        return "the tree was re-rooted; the figure is unchanged"
    if [n["id"] for n in req] != [n["id"] for n in srv]:
        return "the node list was reordered; the figure is unchanged"
    return "it packed exactly as drafted"
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tests/test_gated_pipeline.py
git commit -m "S5: the packability step, described in words a person can act on

Runs BEFORE the human sees anything, per the owner's 2026-09-10 ruling and
against the parent spec's original diagram: measured on 17 subjects the rescue
is invisible in the figure for 15 of them, and for the 2 where joints are
merged, gating afterwards means the human approves the tree the compiler will
actually receive.

pack_fn is injectable so tests never spawn a compile.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: the human-facing summary

**Files:**
- Modify: `mcp_harness/gated_pipeline.py` (append `summarise`)
- Modify: `mcp_harness/tests/test_gated_pipeline.py` (append tests)

**Interfaces:**
- Consumes: `pack()`'s dict (Task 2).
- Produces: `summarise(tree: dict, packing: dict, leaf_names: list[str]) -> str`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_gated_pipeline.py`:

```python
def _tree(guess="a dog"):
    return {"subject_guess": guess,
            "nodes": [{"name": "root", "parent": None, "length": 0,
                       "direction": [0, 0, 0]}],
            "pairs": []}


def test_the_summary_leads_with_what_the_human_is_judging():
    s = GP.summarise(_tree(), {"served": True, "stub_flaps": 0,
                               "invents_anatomy": False,
                               "what_changed": "it packed exactly as drafted"},
                     ["head", "tail", "paw_L", "paw_R"])
    assert "a dog" in s
    assert "4 flaps" in s
    assert "packed exactly as drafted" in s


def test_the_summary_SHOUTS_when_the_engine_invented_flaps():
    """The crab's node list is byte-identical to its request, so its invented
    flaps exist only in the compiled base and NO picture can show them. This
    string is the only thing at the gate that can."""
    s = GP.summarise(_tree("a crab"),
                     {"served": True, "stub_flaps": 2, "invents_anatomy": True,
                      "what_changed": "the engine ADDED 2 flap(s)"},
                     ["claw_L", "claw_R"])
    assert "WARNING" in s
    assert "2 extra flap" in s
    assert "not anatomy" in s


def test_the_summary_says_so_when_nothing_packed_and_still_shows_the_tree():
    """Anatomy is the bar and pack rate is reported, never gated -- so an
    unpackable tree is still put in front of the human."""
    s = GP.summarise(_tree(), {"served": False, "stub_flaps": 0,
                               "invents_anatomy": False,
                               "what_changed": "this tree does not pack yet"},
                     ["head"])
    assert "does not pack yet" in s
    assert "WARNING" not in s
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `AttributeError: module 'gated_pipeline' has no attribute 'summarise'`.

- [ ] **Step 3: Append the implementation to `gated_pipeline.py`**

```python
def summarise(tree, packing, leaf_names) -> str:
    """What the human reads beside the figure.

    Written for a person, not a log. The last clause is the one that matters:
    a stub serve's node list is byte-identical to the request, so its invented
    flaps exist only in the compiled base and no picture can show them. The
    words are the only disclosure there is.
    """
    guess = tree.get("subject_guess") or "this mesh"
    lines = [f"Read as: {guess}",
             f"{len(leaf_names)} flaps: " + ", ".join(leaf_names),
             f"Packing: {packing['what_changed']}."]
    if packing.get("invents_anatomy"):
        lines.append(
            f"WARNING: the base carries {packing['stub_flaps']} extra flap(s) "
            "that are not anatomy. Every length you asked for is untouched and "
            "every flap you asked for is present, but the engine added "
            "structural filler to make the pattern resolvable. The figure "
            "above CANNOT show them.")
    lines.append("Does this read as the animal? Reply 'yes' to continue, or "
                 "say what is wrong with it.")
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tests/test_gated_pipeline.py
git commit -m "S5: the summary the human reads beside the figure

Its last clause is the load-bearing one: a stub serve's node list is
byte-identical to the request, so its invented flaps exist only in the compiled
base and no picture can show them. The words are the only disclosure there is.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `start()` — draft, pack, draw, pause

**Files:**
- Modify: `mcp_harness/gated_pipeline.py`
- Modify: `mcp_harness/tests/test_gated_pipeline.py`

**Interfaces:**
- Consumes: `pack` and `summarise` (Tasks 2–3); `tree_authoring.SYSTEM`, `TOOL`,
  `to_tuples`, `leaves_of`, `metric_tree` (Task 1); `vlm_render.render_mesh_views`,
  `vlm_render.render_tree_sheet`.
- Produces: `async start(mesh_path, *, client, out_dir, pack_fn=None) -> dict`
  returning a `State` whose `status` is `awaiting_review` or `failed`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_gated_pipeline.py`:

```python
import asyncio


class FakeCall:
    def __init__(self, payload):
        self.id = "call_1"
        self.function = type("F", (), {"name": "submit_tree",
                                       "arguments": json.dumps(payload)})()


class FakeResult:
    def __init__(self, payload=None, finish_reason="tool_calls"):
        self.text = ""
        self.tool_calls = [FakeCall(payload)] if payload else []
        self.finish_reason = finish_reason
        self.usage = {"total_tokens": 100}


class FakeClient:
    """Records every prompt it is given, so a test can assert what the model saw."""

    def __init__(self, payloads):
        self._payloads = list(payloads)
        self.calls = []

    async def run_turn(self, system, messages, tools):
        self.calls.append({"system": system, "messages": messages})
        p = self._payloads.pop(0)
        return FakeResult(p) if p is not None else FakeResult(None, "length")


DOG = {"subject_guess": "a dog", "readings": ["withers (7,6)"],
       "leaves": ["head", "tail"],
       "nodes": [{"name": "spine", "parent": None, "length": 0, "direction": [0, 0, 0]},
                 {"name": "head", "parent": "spine", "length": 9, "direction": [1, 0, 0]},
                 {"name": "tail", "parent": "spine", "length": 6, "direction": [-1, 0, 0]}],
       "pairs": []}


def test_start_pauses_at_awaiting_review_with_a_figure(tmp_path, monkeypatch):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": str(tmp_path / "mesh.png")})
    c = FakeClient([DOG])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=fake_pack_ok))
    assert st["status"] == "awaiting_review"
    assert st["round"] == 0
    assert st["subject_guess"] == "a dog"
    assert os.path.exists(st["sheet_png"])
    assert len(c.calls) == 1


def test_start_reports_a_truncated_turn_as_failed_not_as_a_tree(tmp_path, monkeypatch):
    """LLM_MAX_TOKENS truncation returns finish_reason 'length' and no tool
    call. Measured: at 32000 the bat truncated at exactly the cap. A half-built
    tree presented as real is the worst possible outcome here."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": str(tmp_path / "mesh.png")})
    c = FakeClient([None])
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=fake_pack_ok))
    assert st["status"] == "failed"
    assert st["tree"] is None
    assert "length" in st["note"]


def test_state_survives_a_json_round_trip(tmp_path, monkeypatch):
    """The pause is a return value precisely so a tool, a CLI or a frontend can
    hold it between turns. A State that will not serialise cannot do that."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": str(tmp_path / "mesh.png")})
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([DOG]),
                              out_dir=str(tmp_path), pack_fn=fake_pack_ok))
    assert json.loads(json.dumps(st)) == st
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `AttributeError: module 'gated_pipeline' has no attribute 'start'`.

- [ ] **Step 3: Append the implementation**

```python
import tree_contract


def _blank_state(mesh_path) -> dict:
    return {"status": "failed", "round": 0, "mesh_path": mesh_path,
            "subject_guess": None, "tree": None, "metric_tree": None,
            "packing": None, "sheet_png": None, "summary": "",
            "history": [], "note": None, "fold": None}


async def _author(client, mesh_png, prior_tree, feedback):
    """One authoring turn, with up to MAX_VALIDATE contract repairs.

    ⚠ On a revision the model is given the previous tree AS JSON and the
    human's words -- never the rendered figure. Showing a model its own picture
    was measured WORSE than no review at all (MAE 0.53 against 0.29), and
    `agent_loop.IMAGE_RESULT_TOOLS` excludes `render_tree_sheet` for that
    reason. This function must not become the loophole.
    """
    import llm_client
    ask = "Author the metric tree for the mesh in this image."
    if prior_tree is not None:
        ask = ("You previously authored this tree for the mesh in this image:\n"
               + json.dumps({"nodes": prior_tree["nodes"],
                             "pairs": prior_tree.get("pairs") or []}, indent=1)
               + "\n\nA human reviewed the stick figure and said:\n"
               + f"\"{feedback}\"\n\n"
               + "Re-author the COMPLETE tree, fixing what they described. "
                 "Keep everything they did not complain about.")
    msgs = [llm_client.user_message_with_images(ask, [mesh_png])]
    tree = note = None
    for _ in range(MAX_VALIDATE + 1):
        r = await client.run_turn(TA.SYSTEM, msgs, TA.TOOL)
        if not r.tool_calls:
            return None, f"the model returned no tree (finish_reason: {r.finish_reason})"
        tree = json.loads(r.tool_calls[0].function.arguments)
        nodes = TA.to_tuples(tree)
        leaves = set(TA.leaves_of(nodes))
        keep = [(a, b) for p in (tree.get("pairs") or []) if len(p) == 2
                for a, b in [p] if a in leaves and b in leaves]
        try:
            tn, sp, _ = TA.metric_tree(nodes, keep)
            errs = tree_contract.check(tn, sp).get("errors", [])
        except Exception as e:                              # noqa: BLE001
            errs = [f"unbuildable: {e}"]
        if not errs:
            return tree, None
        note = "; ".join(errs)
        msgs = msgs + [{"role": "user", "content":
                        "validate_tree REJECTED that tree:\n- "
                        + "\n- ".join(errs)
                        + "\n\nFix every error and re-submit the complete tree."}]
    return None, f"the tree still failed validation: {note}"


def _served_tuples(nodes, names, served_nodes):
    """The SERVED tree, drawable: (name, parent, direction, length) tuples.

    ⚠ THE SHEET MUST SHOW THE SERVED TREE, NOT THE AUTHORED ONE. For the spider
    that is 10 nodes rather than 26. Showing the authored tree would ask a
    person to approve something the compiler will not receive.

    A metric tree carries no geometry, only lengths, so the only honest source
    of a direction is the one the author supplied. Each served edge's direction
    is therefore DERIVED from the authored positions of its two endpoints:
    exact where the edge survived untouched, and a straight line between the
    two survivors where a chain was collapsed -- which is precisely what a
    lossless collapse asserts. Nothing is invented.
    """
    if not served_nodes:
        return nodes
    pos = vlm_render.positions(nodes)
    out = []
    for n in served_nodes:
        name = names[n["id"]]
        if n["parent_id"] is None:
            out.append((name, None, None, n["length"]))
            continue
        pname = names[n["parent_id"]]
        a, b = pos[pname], pos[name]
        d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]]
        out.append((name, pname, (d if any(d) else [1, 0, 0]), n["length"]))
    return out


async def _draft(state, *, client, out_dir, pack_fn, feedback=""):
    os.makedirs(out_dir, exist_ok=True)
    mesh_png = vlm_render.render_mesh_views(
        state["mesh_path"], os.path.join(out_dir, "mesh_views.png"))["png"]

    tree, note = await _author(client, mesh_png, state.get("tree"), feedback)
    if tree is None:
        state["status"] = "failed"
        state["note"] = note
        return state

    nodes = TA.to_tuples(tree)
    leaf_names = TA.leaves_of(nodes)
    leaves = set(leaf_names)
    keep = [(a, b) for p in (tree.get("pairs") or []) if len(p) == 2
            for a, b in [p] if a in leaves and b in leaves]
    tn, sp, names = TA.metric_tree(nodes, keep)

    packing = pack(tn, sp, pack_fn=pack_fn)

    draw = _served_tuples(nodes, names, packing["served_nodes"])
    sheet = os.path.join(out_dir, f"tree_round{state['round']}.png")
    vlm_render.render_tree_sheet(
        draw, sheet,
        title=f"{tree.get('subject_guess', '')}  —  round {state['round']}")

    state.update({"status": "awaiting_review", "tree": tree,
                  "subject_guess": tree.get("subject_guess"),
                  "metric_tree": {"tree_nodes": tn, "symmetric_pairs": sp,
                                  "names": {str(k): v for k, v in names.items()}},
                  "packing": {k: v for k, v in packing.items() if k != "fold"},
                  "fold": packing["fold"], "sheet_png": sheet,
                  "summary": summarise(tree, packing, leaf_names), "note": None})
    return state


async def start(mesh_path, *, client, out_dir, pack_fn=None) -> dict:
    """Draft a tree, make it packable, draw it, and STOP for a human."""
    return await _draft(_blank_state(mesh_path), client=client,
                        out_dir=out_dir, pack_fn=pack_fn)
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tests/test_gated_pipeline.py
git commit -m "S5: start() -- draft, pack, draw, and stop for a human

The sheet is drawn from the SERVED tree, not the authored one: for the spider
that is 10 nodes rather than 26, and showing the authored tree would ask a
person to approve something the compiler will not receive.

A truncated authoring turn returns failed with the reason rather than a
half-built tree. State survives a json round-trip, which is the whole point of
making the pause a return value.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `resume()` — approve, revise, exhaust

**Files:**
- Modify: `mcp_harness/gated_pipeline.py`
- Modify: `mcp_harness/tests/test_gated_pipeline.py`

**Interfaces:**
- Consumes: `_draft`, `MAX_REVISIONS` (Task 4).
- Produces: `async resume(state, verdict, feedback="", *, client, out_dir, pack_fn=None) -> dict`.
  `verdict` is `"approve"` or `"revise"`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_gated_pipeline.py`:

```python
def _started(tmp_path, monkeypatch, payloads):
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": str(tmp_path / "mesh.png")})
    c = FakeClient(payloads)
    st = asyncio.run(GP.start("fake.glb", client=c, out_dir=str(tmp_path),
                              pack_fn=fake_pack_ok))
    return st, c


def test_approve_keeps_the_fold_and_does_not_recompile(tmp_path, monkeypatch):
    """The packability step already compiled -- that is how it knows the tree
    packs. A second compile would be a billed no-op."""
    st, c = _started(tmp_path, monkeypatch, [DOG])
    out = asyncio.run(GP.resume(st, "approve", client=c,
                                out_dir=str(tmp_path), pack_fn=fake_pack_ok))
    assert out["status"] == "approved"
    assert out["fold"] == st["fold"]
    assert len(c.calls) == 1          # no further authoring


def test_three_revisions_stay_open_and_quote_the_human_verbatim(tmp_path, monkeypatch):
    st, c = _started(tmp_path, monkeypatch, [DOG, DOG, DOG, DOG])
    for i, msg in enumerate(("legs are fused", "tail too short", "head too big")):
        st = asyncio.run(GP.resume(st, "revise", msg, client=c,
                                   out_dir=str(tmp_path), pack_fn=fake_pack_ok))
        assert st["status"] == "awaiting_review"
        assert st["round"] == i + 1
        sent = json.dumps(c.calls[-1]["messages"])
        assert msg in sent
    assert len(c.calls) == 4          # one draft + three revisions
    assert [h["feedback"] for h in st["history"]] == \
        ["legs are fused", "tail too short", "head too big"]


def test_a_fourth_revision_is_refused_before_the_model_is_called(tmp_path, monkeypatch):
    """An exhausted budget must cost nothing. The refusal happens before the
    authoring turn, so `exhausted` is free."""
    st, c = _started(tmp_path, monkeypatch, [DOG, DOG, DOG, DOG])
    for msg in ("a", "b", "c"):
        st = asyncio.run(GP.resume(st, "revise", msg, client=c,
                                   out_dir=str(tmp_path), pack_fn=fake_pack_ok))
    assert len(c.calls) == 4
    st = asyncio.run(GP.resume(st, "revise", "d", client=c,
                               out_dir=str(tmp_path), pack_fn=fake_pack_ok))
    assert st["status"] == "exhausted"
    assert len(c.calls) == 4          # STILL four -- no call was spent
    assert st["tree"] is not None     # the best tree is kept, not discarded
    assert "not satisfied" in st["note"]


def test_no_revision_message_ever_carries_an_image(tmp_path, monkeypatch):
    """agent_loop.IMAGE_RESULT_TOOLS excludes render_tree_sheet for a measured
    reason (MAE 0.53 with the figure against 0.29 without). This loop must not
    become the loophole -- the ONE image is the mesh ruler, in the first turn."""
    st, c = _started(tmp_path, monkeypatch, [DOG, DOG])
    asyncio.run(GP.resume(st, "revise", "fix the legs", client=c,
                          out_dir=str(tmp_path), pack_fn=fake_pack_ok))
    for call in c.calls:
        images = [part for m in call["messages"]
                  if isinstance(m.get("content"), list)
                  for part in m["content"] if part.get("type") == "image_url"]
        assert len(images) <= 1, "only the mesh ruler may be an image"


def test_the_sheet_is_drawn_from_the_SERVED_tree(tmp_path, monkeypatch):
    """Pinned on a case where the two differ, so a regression to the authored
    tree reddens. The spider serves 10 nodes against 26 authored."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": str(tmp_path / "mesh.png")})
    seen = {}
    real = GP.vlm_render.render_tree_sheet

    def spy(nodes, out_path, **kw):
        seen["n"] = len(nodes)
        return real(nodes, out_path, **kw)

    monkeypatch.setattr(GP.vlm_render, "render_tree_sheet", spy)

    def collapses(nodes, pairs):
        """A serve that merged the middle node away: 3 in, 2 out."""
        return ("{\"vertices_coords\": []}",
                {"requested": [dict(n) for n in nodes],
                 "served": [{"id": 0, "parent_id": None, "length": 0.0},
                            {"id": 1, "parent_id": 0, "length": 0.4}]})

    asyncio.run(GP.start("fake.glb", client=FakeClient([DOG]),
                         out_dir=str(tmp_path), pack_fn=collapses))
    assert seen["n"] == 2, "the sheet drew the authored tree, not the served one"


def test_the_tree_sheet_is_never_a_tool_the_model_sees():
    """agent_loop.IMAGE_RESULT_TOOLS is the registry of tools whose rendered
    output goes back to the MODEL. render_tree_sheet is excluded because
    showing a model its own figure measured WORSE than no review at all, and
    S5 must not quietly re-enable the rung the evidence removed."""
    import agent_loop
    assert "render_tree_sheet" not in agent_loop.IMAGE_RESULT_TOOLS
    assert agent_loop.IMAGE_RESULT_TOOLS == {"render_mesh_views"}


def test_an_unpackable_tree_still_reaches_the_human(tmp_path, monkeypatch):
    """Anatomy is the bar, pack rate is reported and never gated -- so the
    person gets to look at the animal and decide."""
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: {"png": str(tmp_path / "mesh.png")})

    def never_packs(nodes, pairs):
        return ("ERROR: POLYS_NOT_VALID", {})

    st = asyncio.run(GP.start("fake.glb", client=FakeClient([DOG]),
                              out_dir=str(tmp_path), pack_fn=never_packs))
    assert st["status"] == "awaiting_review"
    assert st["packing"]["served"] is False
    assert "does not pack yet" in st["summary"]
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `AttributeError: module 'gated_pipeline' has no attribute 'resume'`.

- [ ] **Step 3: Append the implementation**

```python
async def resume(state, verdict, feedback="", *, client, out_dir,
                 pack_fn=None) -> dict:
    """Carry the human's answer back into the pipeline.

    `verdict` is "approve" or "revise". Approving does NOT recompile: the
    packability step already produced the fold, and a second compile would be a
    billed no-op that could, at the tangency cliff this repo has already met,
    return something different.
    """
    state = json.loads(json.dumps(state))          # never mutate the caller's
    if verdict == "approve":
        state["status"] = "approved"
        state["history"].append({"round": state["round"], "verdict": "approve",
                                 "feedback": feedback})
        return state
    if verdict != "revise":
        raise ValueError(f"verdict must be 'approve' or 'revise', got {verdict!r}")

    # REFUSE BEFORE AUTHORING, so an exhausted budget costs nothing.
    if state["round"] >= MAX_REVISIONS:
        state["status"] = "exhausted"
        state["note"] = (f"{MAX_REVISIONS} revisions were used and your last "
                         "critique was not satisfied. The best tree so far is "
                         "kept; nothing has been compiled beyond it.")
        state["history"].append({"round": state["round"], "verdict": "revise",
                                 "feedback": feedback})
        return state

    state["history"].append({"round": state["round"], "verdict": "revise",
                             "feedback": feedback})
    state["round"] += 1
    return await _draft(state, client=client, out_dir=out_dir,
                        pack_fn=pack_fn, feedback=feedback)
```

- [ ] **Step 4: Run to verify it passes**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_gated_pipeline.py -q
```

Expected: `16 passed`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/gated_pipeline.py mcp_harness/tests/test_gated_pipeline.py
git commit -m "S5: resume() -- approve, revise, and a budget that refuses for free

Three revisions stay open and quote the human verbatim; the fourth is refused
BEFORE the model is called, so an exhausted budget costs no authoring turn. The
best tree is kept rather than discarded, and nothing is silently compiled.

Approve does not recompile: the packability step already produced the fold.

Pinned: no revision message ever carries an image. IMAGE_RESULT_TOOLS excludes
render_tree_sheet for a measured reason and this loop must not be the loophole.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `eval_vlm_pipeline.py` — one offline command

**Files:**
- Create: `mcp_harness/eval_vlm_pipeline.py`
- Test: `mcp_harness/tests/test_eval_vlm_pipeline.py`

**Interfaces:**
- Consumes: `tree_authoring` (Task 1), plus the shipped metric modules
  `reading_fidelity`, `leaf_label_accuracy`, `pair_fusion`, `tree_contract`.
- Produces: `score_corpus(raw_path, *, subjects=None, compile_fn=None) -> dict`
  and a `main(argv=None) -> int` CLI entry point.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_eval_vlm_pipeline.py`:

```python
"""One command, no network, committed data in and one scorecard out."""
from __future__ import annotations

import json

import eval_vlm_pipeline as EV

RAW = [{"subject": "dog", "mode": "none", "tree": {
    "subject_guess": "a dog", "readings": ["withers (7,6)"],
    "leaves": ["head", "tail"],
    "nodes": [{"name": "spine", "parent": None, "length": 0, "direction": [0, 0, 0]},
              {"name": "head", "parent": "spine", "length": 9, "direction": [1, 0, 0]},
              {"name": "tail", "parent": "spine", "length": 6, "direction": [-1, 0, 0]}],
    "pairs": []}}]


def test_scoring_never_reaches_the_network_or_the_packer(tmp_path):
    """The default path must be pure computation over committed JSON. A run
    that silently re-authors would cost money AND change the numbers it was
    asked to check."""
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(RAW))
    out = EV.score_corpus(str(p), compile_fn=lambda *a, **k: ("err", None))
    assert out["n"] == 1
    row = out["rows"][0]
    assert row["subject"] == "dog"
    assert row["leaves"] == 2
    assert row["packs"] is False


def test_subject_filter_narrows_without_reordering(tmp_path):
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(RAW))
    out = EV.score_corpus(str(p), subjects=["cat"],
                          compile_fn=lambda *a, **k: ("err", None))
    assert out["n"] == 0


def test_the_scorecard_is_json_serialisable(tmp_path):
    p = tmp_path / "raw.json"
    p.write_text(json.dumps(RAW))
    out = EV.score_corpus(str(p), compile_fn=lambda *a, **k: ("err", None))
    assert json.loads(json.dumps(out)) == out
```

- [ ] **Step 2: Run to verify it fails**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_eval_vlm_pipeline.py -q
```

Expected: `ModuleNotFoundError: No module named 'eval_vlm_pipeline'`.

- [ ] **Step 3: Write the module**

Create `mcp_harness/eval_vlm_pipeline.py`:

```python
"""One command that regenerates this branch's scorecard from committed data.

WHY. Every number the VLM spec quotes was produced by one of ~30 as-run scripts
in `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/`, each
carrying hard-coded absolute paths from the session that ran it. Those stay --
they are the record of what was actually run -- but they were the ONLY way to
regenerate a figure, which meant no one but their author could check one.

NO NETWORK BY DEFAULT. Re-authoring costs money and re-rolls the model, and
§2f measured that the packing set churns almost completely between two runs of
the SAME configuration. Anyone using a re-author to "check" a number would get
a different one and could reasonably read it as a regression.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

KEY = {"guinea_pig": "guinea pig"}


def _compile(tree_nodes, symmetric_pairs, timeout=60):
    from runner import compile_tree
    return compile_tree(tree_nodes, symmetric_pairs, timeout=timeout)


def score_corpus(raw_path, *, subjects=None, compile_fn=None,
                 mesh_dir=None) -> dict:
    """Recompute every metric for one committed corpus. Pure, offline."""
    import numpy as np
    import tree_authoring as TA
    import tree_contract
    import leaf_label_accuracy as LA
    import pair_fusion as PF
    import reading_fidelity as RF

    cf = compile_fn or _compile
    exp = json.load(open(os.path.join(os.path.dirname(__file__),
                                      "fixtures", "anatomy_expectation.json")))
    want = set(subjects) if subjects else None
    rows = []
    for rec in json.load(open(raw_path)):
        s = rec.get("subject")
        if not rec.get("tree") or (want is not None and s not in want):
            continue
        t = rec["tree"]
        key = KEY.get(s, s)
        e = exp.get(key, {}).get("expected_feature_count")
        nodes = TA.to_tuples(t)
        leaf_names = TA.leaves_of(nodes)
        leaves = set(leaf_names)
        keep = [(a, b) for p in (t.get("pairs") or []) if len(p) == 2
                for a, b in [p] if a in leaves and b in leaves]
        tn, sp, _ = TA.metric_tree(nodes, keep)
        rep = tree_contract.check(tn, sp)
        status, _ = cf(tn, sp)
        lab = LA.score_labels(key, leaf_names) if e is not None else {}
        fus = PF.score_fusion(tn, sp)
        rf = None
        if mesh_dir:
            import trimesh
            m = trimesh.load(os.path.join(mesh_dir, f"{s}.glb"), force="mesh")
            m.vertices -= m.vertices.mean(axis=0)
            pts = RF.parse_readings(t.get("readings"))
            if pts:
                rf = float(RF.distance_outside(
                    pts, [RF.silhouette(m, v) for v in RF.VIEWS]).mean())
        rows.append({"subject": s, "leaves": len(leaf_names), "expected": e,
                     "delta": (len(leaf_names) - e) if e is not None else None,
                     "nodes": len(nodes), "pairs": len(sp),
                     "contract_ok": not rep.get("errors"),
                     "packs": status == "ok",
                     "label_exact": lab.get("exact"),
                     "coverage": lab.get("coverage"),
                     "min_limb_split": fus["min_branch_fraction"],
                     "reading_fidelity": rf})

    d = [abs(r["delta"]) for r in rows if r["delta"] is not None]
    cov = [r["coverage"] for r in rows if r["coverage"] is not None]
    return {"corpus": os.path.basename(raw_path), "n": len(rows), "rows": rows,
            "mae": (round(sum(d) / len(d), 4) if d else None),
            "count_exact": sum(1 for x in d if x == 0),
            "label_exact": sum(1 for r in rows if r["label_exact"]),
            "contract_ok": sum(1 for r in rows if r["contract_ok"]),
            "packs": sum(1 for r in rows if r["packs"]),
            "mean_coverage": (round(float(np.mean(cov)), 4) if cov else None),
            "worst_limb_splits": sorted(
                [r["min_limb_split"] for r in rows
                 if r["min_limb_split"] is not None])[:3]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raw", required=True, help="committed *_raw.json corpus")
    ap.add_argument("--subjects", help="comma-separated subset")
    ap.add_argument("--mesh-dir", help="enables reading fidelity; needs the .glb files")
    ap.add_argument("--out", default="scorecard.json")
    a = ap.parse_args(argv)
    out = score_corpus(a.raw,
                       subjects=(a.subjects.split(",") if a.subjects else None),
                       mesh_dir=a.mesh_dir)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"{out['corpus']}  n={out['n']}  MAE={out['mae']}  "
          f"count-exact={out['count_exact']}/{out['n']}  "
          f"label-exact={out['label_exact']}/{out['n']}  "
          f"contract={out['contract_ok']}/{out['n']}  "
          f"packs={out['packs']}/{out['n']}  cov={out['mean_coverage']}")
    print(f"worst limb splits: {out['worst_limb_splits']}")
    print(f"\n  {'subject':12}{'leaves':>7}{'exp':>5}{'split':>8}{'packs':>7}")
    for r in out["rows"]:
        sp = f"{r['min_limb_split']:.3f}" if r["min_limb_split"] is not None else "n/a"
        print(f"  {r['subject']:12}{r['leaves']:>7}{str(r['expected']):>5}"
              f"{sp:>8}{('Y' if r['packs'] else 'n'):>7}")
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest tests/test_eval_vlm_pipeline.py -q
```

Expected: `3 passed`.

- [ ] **Step 5: Verify it reproduces the committed figures**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m eval_vlm_pipeline \
  --raw ../docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/data/rule6_raw.json \
  --out /tmp/s5_scorecard.json
```

Expected, matching the spec's §2i/§2k figures:
`n=17  MAE=0.2353  count-exact=14/17  label-exact=14/17  contract=17/17  packs=5/17`

If any figure differs, STOP and report it rather than adjusting the code to
match — a divergence means either the metric moved or a committed number was
wrong, and both need saying out loud.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/eval_vlm_pipeline.py mcp_harness/tests/test_eval_vlm_pipeline.py
git commit -m "S5: one command that regenerates the scorecard from committed data

Every number this branch quotes came from one of ~30 as-run scripts carrying
hard-coded absolute paths from the session that ran it. Those stay -- they are
the record of what was run -- but they were the only way to regenerate a
figure, so nobody but their author could check one.

No network by default. Re-authoring costs money and re-rolls the model, and §2f
measured that the packing set churns almost completely between two runs of the
SAME configuration -- so a re-author used to 'check' a number returns a
different one and reads as a regression.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Run the full S5 test set**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest \
  tests/test_tree_authoring.py tests/test_gated_pipeline.py \
  tests/test_eval_vlm_pipeline.py -q
```

Expected: `25 passed`.

- [ ] **Run the regression set for the modules S5 reads**

```bash
cd mcp_harness && <repo>/.venv/bin/python -m pytest \
  tests/test_pair_fusion.py tests/test_reading_fidelity.py \
  tests/test_leaf_label_accuracy.py tests/test_flatten_stage.py \
  tests/test_rescue_ladder.py -q
```

Expected: all pass. S5 creates only new files, so any failure here is a
pre-existing break and must be reported rather than fixed silently.

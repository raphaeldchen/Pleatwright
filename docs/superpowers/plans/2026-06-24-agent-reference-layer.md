# Agent-Reference Layer (Slice #1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the agent use a generated 3-D model of the requested subject as a reference — query → acquire mesh → extract candidate tree + textual report → agent applies semantic corrections → existing compile/lint path.

**Architecture:** Merge PR #11 (mesh acquisition) into this branch, then add one MCP tool (`reference_tree_from_query`) that wraps `acquire_mesh` + `auto_mesh_to_metric_tree` + a pure report formatter (`mesh_report.format_reference_report`), and rewrite the agent system prompt so the mesh-derived candidate is the primary starting point with templates demoted to fallback. The compile/gate/lint half is unchanged.

**Tech Stack:** Python, pytest, FastMCP (`server.py`), the existing `mesh_to_tree`/`mesh_acquire` modules, Groq llama via `llm_client` (text-only).

## Global Constraints

- Tests live in `mcp_harness/tests/` and run from inside `mcp_harness/` via `.venv/bin/python -m pytest`.
- No new heavy dependencies (PR #11's `mesh_acquire` uses stdlib `urllib` only).
- Fail loud with specific messages; defensive on the serve path (tools return `"ERROR: ..."` strings, never raise across the MCP boundary).
- Money is spent only when `MESH_PROVIDER=meshy` with a real key; the agent tool defaults to the offline `fake` provider.
- Do NOT modify the compile/gate/lint tools or `mesh_to_tree.py` extraction logic.
- The candidate tree is PRIMARY; templates are demoted to fallback (not removed this slice).
- Reference is text-only (no multimodal/vision).

---

### Task 1: Merge PR #11 (mesh-acquisition) prerequisite

Bring `mesh_acquire.py` (the `MeshProvider` protocol, `FakeMeshProvider`, `MeshyProvider`, `acquire_mesh`, `query_to_metric_tree`) onto this branch. Verified clean: the two branches share zero changed files and `git merge-tree` shows no conflicts.

**Files:**
- Merge brings in: `mcp_harness/mesh_acquire.py`, `mcp_harness/tests/test_mesh_acquire.py`, `.gitignore`, two docs under `docs/superpowers/`.

**Interfaces:**
- Produces (for later tasks): `mesh_acquire.acquire_mesh(prompt, *, provider=None, provider_name=None, cache_dir=None) -> str` (returns a `.glb` path); `mesh_acquire.FakeMeshProvider(fixture_path=DEFAULT_FIXTURE)` with `.generate(prompt, out_dir) -> str`; `mesh_acquire.DEFAULT_FIXTURE`; `mesh_acquire._HERE` (the `mcp_harness/` dir).

- [ ] **Step 1: Confirm clean merge preconditions**

Run (from repo root `<repo>`):

```bash
git branch --show-current
git merge-tree $(git merge-base HEAD feat/mesh-acquisition) HEAD feat/mesh-acquisition | grep -i "CONFLICT\|changed in both\|<<<<<<<" || echo "NO CONFLICTS"
```

Expected: branch is `feat/mesh-to-tree-hardening`; prints `NO CONFLICTS`.
If conflicts appear, STOP and report BLOCKED (do not attempt resolution without the controller).

- [ ] **Step 2: Merge**

```bash
git merge --no-edit feat/mesh-acquisition
```

Expected: a merge commit is created with no conflicts.

- [ ] **Step 3: Run the full suite to confirm the merge is green**

Run (from `mcp_harness/`):

```bash
.venv/bin/python -m pytest -q
```

Expected: all pass (this branch's 155 + PR #11's `test_mesh_acquire.py` tests; ~169 passed, 1 skipped). Report the exact numbers. If anything fails, report BLOCKED with the failure.

- [ ] **Step 4: (No separate commit)**

The merge commit from Step 2 is the deliverable; do not amend it. Report the merge commit hash.

---

### Task 2: FakeMeshProvider prompt→fixture mapping

Make the offline `FakeMeshProvider` return a query-specific committed fixture so the offline smoke isn't always a quadruped, at no cost. Keep it backwards-compatible (an explicitly constructed `FakeMeshProvider(fixture_path=X)` still uses `X`; unmatched prompts still yield the quadruped).

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (the `FakeMeshProvider` class + a new module-level helper)
- Test: `mcp_harness/tests/test_mesh_acquire.py` (add tests)

**Interfaces:**
- Consumes: `mesh_acquire._HERE`, `mesh_acquire.DEFAULT_FIXTURE` (from Task 1).
- Produces: `mesh_acquire._fixture_for_prompt(prompt: str) -> str` (absolute path to a committed `.glb`); `FakeMeshProvider(fixture_path: str | None = None)` now maps by prompt when `fixture_path` is None.

- [ ] **Step 1: Write the failing tests**

Add to `mcp_harness/tests/test_mesh_acquire.py` (the file already imports `mesh_acquire as ma`, `os`, `pytest`; it defines fixtures with `tmp_path`):

```python
@pytest.mark.parametrize("prompt,expected", [
    ("a giant beetle", "insect.glb"),
    ("a soaring eagle", "bird.glb"),
    ("a rainbow trout", "fish.glb"),
    ("a standing person", "humanoid.glb"),
    ("a red fox", "quadruped.glb"),
])
def test_fixture_for_prompt_maps_keywords(prompt, expected):
    assert ma._fixture_for_prompt(prompt).endswith(expected)


def test_fake_provider_uses_prompt_mapping(tmp_path):
    import filecmp
    out = ma.FakeMeshProvider().generate("a giant beetle", str(tmp_path))
    insect = os.path.join(ma._HERE, "fixtures", "insect.glb")
    assert filecmp.cmp(out, insect, shallow=False)


def test_fake_provider_explicit_fixture_overrides_mapping(tmp_path):
    import filecmp
    bird = os.path.join(ma._HERE, "fixtures", "bird.glb")
    out = ma.FakeMeshProvider(fixture_path=bird).generate("a giant beetle", str(tmp_path))
    assert filecmp.cmp(out, bird, shallow=False)   # explicit path wins over 'beetle'->insect
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_mesh_acquire.py -k "fixture_for_prompt or prompt_mapping or explicit_fixture" -v`
Expected: FAIL (`_fixture_for_prompt` undefined / mapping not applied).

- [ ] **Step 3: Implement the mapping**

In `mcp_harness/mesh_acquire.py`, immediately after the `DEFAULT_FIXTURE = ...` line, add:

```python
# Keyword -> committed fixture (first match wins). Lets the offline FakeMeshProvider
# return a query-specific mesh so the agent smoke isn't always a quadruped, at no
# cost. Heuristic substrings (a test fake, not a classifier); unmatched -> quadruped.
_FIXTURE_KEYWORDS = [
    (("insect", "bug", "beetle", "spider", "wasp"), "insect.glb"),
    (("bird", "eagle", "owl", "sparrow", "hawk"), "bird.glb"),
    (("fish", "shark", "trout", "salmon"), "fish.glb"),
    (("human", "person", "humanoid"), "humanoid.glb"),
]


def _fixture_for_prompt(prompt: str) -> str:
    """Map a prompt to a committed fixture .glb by keyword; default quadruped."""
    p = prompt.lower()
    for keywords, fname in _FIXTURE_KEYWORDS:
        if any(k in p for k in keywords):
            return os.path.join(_HERE, "fixtures", fname)
    return DEFAULT_FIXTURE
```

Then change the `FakeMeshProvider` class so an unset fixture maps by prompt. Replace its `__init__` and `generate` with:

```python
    def __init__(self, fixture_path: str | None = None):
        # None -> choose a fixture per prompt (offline, query-specific). An explicit
        # path pins one fixture regardless of prompt (used by existing tests).
        self.fixture_path = fixture_path

    def generate(self, prompt: str, out_dir: str) -> str:
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        dest = os.path.join(out_dir, "mesh.glb")
        src = self.fixture_path or _fixture_for_prompt(prompt)
        shutil.copyfile(src, dest)
        return dest
```

- [ ] **Step 4: Run the new tests AND the existing FakeMeshProvider tests**

Run: `.venv/bin/python -m pytest tests/test_mesh_acquire.py -v`
Expected: PASS, including the pre-existing `test_fake_provider_writes_glb_into_out_dir` and `test_fake_provider_returns_absolute_path_for_relative_out_dir` (both use prompt "a quadruped" → maps to quadruped fixture, and assert only `.glb`/absolute-path, so they still pass).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "feat(mesh): FakeMeshProvider maps prompt keywords to committed fixtures

Offline provider returns a query-specific fixture (beetle->insect, etc.) so the
agent smoke isn't always a quadruped, at no cost. Explicit fixture_path still wins.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: mesh_report.format_reference_report (pure function)

Render a `MeshTreeResult` as the agent-facing text report. Pure function — no engine, no I/O — so it is fully unit-testable.

**Files:**
- Create: `mcp_harness/mesh_report.py`
- Test: `mcp_harness/tests/test_mesh_report.py`

**Interfaces:**
- Consumes: `mesh_to_tree.MeshTreeResult` (fields: `confirmed: bool`, `nodes: list[dict]`, `pairs: list`, `voxel_res: int`, `prune_fraction: float`, `gate: dict`, `trace: list`); each node is `{"id": int, "parent_id": int|None, "length": float}`.
- Produces: `mesh_report.format_reference_report(result, *, prompt: str, mesh_path: str) -> str`.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_mesh_report.py`:

```python
"""mesh_report.format_reference_report renders a MeshTreeResult as the agent's
text reference report. Pure function, no engine/IO."""
import mesh_report
from mesh_to_tree import MeshTreeResult

_NODES = [
    {"id": 0, "parent_id": None, "length": 0},
    {"id": 1, "parent_id": 0, "length": 0.3},
    {"id": 2, "parent_id": 0, "length": 0.3},
    {"id": 3, "parent_id": 1, "length": 0.4},
    {"id": 4, "parent_id": 1, "length": 0.4},
    {"id": 5, "parent_id": 2, "length": 0.3},
]
_PAIRS = [[3, 4]]


def _result(confirmed=True):
    return MeshTreeResult(
        confirmed=confirmed, nodes=_NODES, pairs=_PAIRS,
        voxel_res=96, prune_fraction=0.55,
        gate={"verdict": "feasible", "p_pack": 0.66, "ood": False},
        trace=[])


def test_report_contains_candidate_and_metrics():
    r = mesh_report.format_reference_report(_result(), prompt="a fox", mesh_path="/m/x.glb")
    assert "a fox" in r
    assert "/m/x.glb" in r
    assert '"parent_id"' in r                 # candidate tree JSON present
    assert "[[3, 4]]" in r                     # symmetric_pairs present
    assert "leaf (flap) count: 3" in r         # nodes 3,4,5 are leaves
    assert "hubs (root's children): [1, 2]" in r
    assert "verdict=feasible" in r
    assert "confirmed" in r.lower()
    assert "semantic" in r.lower()             # correction guidance present


def test_report_flags_unconfirmed():
    r = mesh_report.format_reference_report(_result(confirmed=False),
                                            prompt="a fox", mesh_path="/m/x.glb")
    assert "confirmed=False" in r or "best-effort" in r.lower()
    assert "fall back" in r.lower()            # template fallback hint


def test_report_handles_empty_extraction():
    empty = MeshTreeResult(confirmed=False, nodes=[], pairs=[], voxel_res=96,
                           prune_fraction=0.6, gate={}, trace=[])
    r = mesh_report.format_reference_report(empty, prompt="a fox", mesh_path="/m/x.glb")
    assert "no usable tree" in r.lower()
    assert "template" in r.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_mesh_report.py -v`
Expected: FAIL (`No module named 'mesh_report'`).

- [ ] **Step 3: Implement the formatter**

Create `mcp_harness/mesh_report.py`:

```python
"""Render a MeshTreeResult as the agent-facing reference report (text).

Pure function: no engine, no I/O. The agent reads this to start its draft from
the measured candidate and apply only semantic corrections. See
docs/superpowers/specs/2026-06-24-agent-reference-layer-design.md.
"""
from __future__ import annotations

import json


def _leaves(nodes):
    return [n for n in nodes if n["parent_id"] is not None
            and all(o["parent_id"] != n["id"] for o in nodes)]


def format_reference_report(result, *, prompt: str, mesh_path: str) -> str:
    nodes = result.nodes
    pairs = result.pairs
    if not nodes:
        return (f"REFERENCE for {prompt!r}: extraction produced no usable tree "
                f"(mesh {mesh_path}). Fall back to the nearest known-good template.")

    root = next(n["id"] for n in nodes if n["parent_id"] is None)
    hubs = [n["id"] for n in nodes if n["parent_id"] == root]
    children = {h: [n["id"] for n in nodes if n["parent_id"] == h] for h in hubs}
    leaves = _leaves(nodes)
    g = result.gate or {}

    lines = [
        f"REFERENCE MESH CANDIDATE for {prompt!r}",
        f"(generated mesh: {mesh_path})",
        "",
        "These proportions, topology, and bilateral symmetry are MEASURED from a "
        "3-D model of the requested subject. TRUST them. Start your draft from this "
        "candidate; change only SEMANTICS (see below).",
        "",
        "Candidate tree (pass to draft_and_compile_full_base verbatim or after "
        "semantic edits):",
        f"  tree_nodes = {json.dumps(nodes)}",
        f"  symmetric_pairs = {json.dumps(pairs)}",
        "",
        "Measured metrics:",
        f"  leaf (flap) count: {len(leaves)}",
        f"  root (body) id: {root}; hubs (root's children): {hubs}",
        "  flaps per hub: " + ", ".join(f"{h}->{children[h]}" for h in hubs),
        f"  bilateral pairs: {pairs}",
        "  (edges normalized so the longest limb == 0.40)",
        "",
        "Search provenance:",
        f"  voxel_res={result.voxel_res}, prune_fraction={result.prune_fraction}",
        f"  gate: verdict={g.get('verdict')}, p_pack={g.get('p_pack')}, "
        f"ood={g.get('ood')}",
        f"  confirmed (already compiled to FOLD during search): {result.confirmed}",
        "",
        "Semantic corrections you MAY make: name the anatomy; fix the flap count "
        "(drop a spurious twig the skeletonizer kept, or flag a clearly-missing "
        "limb); confirm the bilateral pairs read correctly.",
        "Do NOT rescale the proportions or re-invent the symmetry to force a pack -- "
        "those are the trustworthy measured part.",
    ]
    if not result.confirmed:
        lines += [
            "",
            "NOTE: confirmed=False -- this extraction is best-effort and did not "
            "compile during the search. Apply a semantic/topology fix, or fall back "
            "to the nearest known-good template if it will not pack.",
        ]
    return "\n".join(lines)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_mesh_report.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_report.py mcp_harness/tests/test_mesh_report.py
git commit -m "feat(mesh): mesh_report.format_reference_report (agent reference report)

Pure formatter turning a MeshTreeResult into the agent-facing text report:
candidate tree + measured metrics + search provenance + semantic-correction
guidance; flags confirmed=False / empty extraction with a template-fallback hint.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: reference_tree_from_query MCP tool (server.py)

Expose the query→mesh→candidate→report chain to the agent as one defensive MCP tool.

**Files:**
- Modify: `mcp_harness/server.py` (add one `@mcp.tool()` function)
- Test: `mcp_harness/tests/test_reference_tool.py`

**Interfaces:**
- Consumes: `mesh_acquire.acquire_mesh(prompt, *, provider_name=...) -> str` (Task 1); `mesh_to_tree.auto_mesh_to_metric_tree(glb) -> MeshTreeResult`; `mesh_report.format_reference_report(result, *, prompt, mesh_path) -> str` (Task 3).
- Produces: `server.reference_tree_from_query(prompt: str) -> str` (the report string, or `"ERROR: ..."`).

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_reference_tool.py`:

```python
"""The reference_tree_from_query MCP tool returns a reference report, defaults to
the offline 'fake' provider, and degrades to 'ERROR: ...' on failure. Network/
engine-free: acquire_mesh + auto_mesh_to_metric_tree are stubbed."""
import mesh_acquire
import mesh_to_tree
import server
from mesh_to_tree import MeshTreeResult


def _result():
    return MeshTreeResult(
        confirmed=True,
        nodes=[{"id": 0, "parent_id": None, "length": 0},
               {"id": 1, "parent_id": 0, "length": 0.4},
               {"id": 2, "parent_id": 0, "length": 0.4}],
        pairs=[[1, 2]], voxel_res=96, prune_fraction=0.55,
        gate={"verdict": "feasible", "p_pack": 0.5, "ood": False}, trace=[])


def test_reference_tool_returns_report(monkeypatch, tmp_path):
    captured = {}

    def fake_acquire(prompt, **kwargs):
        captured["provider_name"] = kwargs.get("provider_name")
        return str(tmp_path / "m.glb")

    monkeypatch.setattr(mesh_acquire, "acquire_mesh", fake_acquire)
    monkeypatch.setattr(mesh_to_tree, "auto_mesh_to_metric_tree", lambda glb, **k: _result())
    monkeypatch.delenv("MESH_PROVIDER", raising=False)

    out = server.reference_tree_from_query(prompt="a beetle")
    assert "REFERENCE MESH CANDIDATE" in out
    assert "[[1, 2]]" in out
    assert captured["provider_name"] == "fake"   # offline default, no money


def test_reference_tool_error_is_graceful(monkeypatch):
    def boom(prompt, **kwargs):
        raise RuntimeError("provider down")
    monkeypatch.setattr(mesh_acquire, "acquire_mesh", boom)
    out = server.reference_tree_from_query(prompt="a beetle")
    assert out.startswith("ERROR:")
    assert "provider down" in out
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_reference_tool.py -v`
Expected: FAIL (`server` has no attribute `reference_tree_from_query`).

- [ ] **Step 3: Implement the tool**

In `mcp_harness/server.py`, add this tool (place it next to `predict_tree_feasibility`; imports are lazy inside the function so the heavy `mesh_to_tree`/`skeletor` import cost is not paid at server startup):

```python
@mcp.tool()
def reference_tree_from_query(prompt: str) -> str:
    """Generate a rough 3-D model of the requested subject and extract a CANDIDATE
    metric tree from it, returned as a text REFERENCE REPORT to start the draft
    from. The candidate's proportions/topology/symmetry are measured from the mesh;
    apply only semantic corrections, then draft_and_compile_full_base as usual.

    Provider is the offline 'fake' (committed fixtures) unless MESH_PROVIDER=meshy,
    which spends money and needs MESHY_API_KEY. Returns the report, or 'ERROR: ...'
    on any acquisition/extraction failure.
    """
    import mesh_acquire
    import mesh_report
    import mesh_to_tree
    try:
        provider_name = os.environ.get("MESH_PROVIDER", "fake")
        glb = mesh_acquire.acquire_mesh(prompt, provider_name=provider_name)
        result = mesh_to_tree.auto_mesh_to_metric_tree(glb)
        return mesh_report.format_reference_report(result, prompt=prompt, mesh_path=glb)
    except Exception as exc:                # serve-path: never raise across MCP
        return f"ERROR: reference extraction failed: {exc}"
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_reference_tool.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_reference_tool.py
git commit -m "feat(server): reference_tree_from_query MCP tool

Wraps acquire_mesh + auto_mesh_to_metric_tree + format_reference_report into one
defensive tool; offline 'fake' provider by default (no cost), MESH_PROVIDER=meshy
for real generation. Returns ERROR: ... on failure.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: System prompt redesign + opt-in live smoke

Rewrite `SYSTEM_PROMPT` so the mesh-derived candidate is the primary starting point (templates demoted to fallback), pin the wiring with a fast unit test, and add an opt-in live smoke.

**Files:**
- Modify: `mcp_harness/agent_loop.py` (`SYSTEM_PROMPT` only)
- Test: `mcp_harness/tests/test_agent_reference_prompt.py` (fast) and `mcp_harness/tests/test_reference_smoke.py` (opt-in, skipped by default)

**Interfaces:**
- Consumes: `agent_loop.SYSTEM_PROMPT` (str); `agent_loop.connect_servers`, `agent_loop.agent_turn`, `llm_client.LLMClient.from_env` (for the smoke).
- Produces: nothing downstream.

- [ ] **Step 1: Write the failing fast prompt-wiring test**

Create `mcp_harness/tests/test_agent_reference_prompt.py`:

```python
"""The system prompt wires the mesh-reference-first flow: call
reference_tree_from_query first, start from the candidate, templates are fallback."""
import agent_loop


def test_system_prompt_wires_reference_flow():
    sp = agent_loop.SYSTEM_PROMPT
    assert "reference_tree_from_query" in sp           # the tool is named
    assert "START FROM THE REFERENCE MESH" in sp       # candidate-primary section
    assert "fallback" in sp.lower()                    # templates demoted
    # guardrail: don't rescale measured proportions
    assert "do not rescale" in sp.lower() or "do not rescale the" in sp.lower()
```

- [ ] **Step 2: Run it to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_agent_reference_prompt.py -v`
Expected: FAIL (strings not yet in the prompt).

- [ ] **Step 3: Rewrite the prompt — add the reference-first section**

In `mcp_harness/agent_loop.py`, insert a new section into `SYSTEM_PROMPT` immediately BEFORE the line that begins `KNOWN-GOOD BODY-PLAN TEMPLATES` (it currently reads `KNOWN-GOOD BODY-PLAN TEMPLATES -- start from the closest one, then adapt.`). Insert this block (note the trailing `\` line-continuations matching the existing prompt style):

```python
START FROM THE REFERENCE MESH \
For any creature or subject request, your FIRST action is \
reference_tree_from_query(<the user's request>). It generates a rough 3-D model of \
the subject and returns a REFERENCE REPORT: a candidate metric tree whose \
proportions, topology, and bilateral symmetry are MEASURED from that model. START \
your draft from this candidate -- it is the source of the tree, not a guess. Your \
job is SEMANTIC correction only: name the anatomy, fix the flap count (drop a \
spurious twig the skeletonizer kept, or add a clearly-missing limb), and confirm \
the bilateral pairs read correctly. Then run the gate -> draft_and_compile_full_base \
-> validate_flat_foldability path on the (possibly edited) candidate. \
GUARDRAIL: TRUST the measured metrics. Do NOT rescale the candidate's proportions \
or re-invent its symmetry to force a pack -- those are the reliable part. (Pre- \
compile length tweaks belong ONLY at the gate's 'infeasible' stage, as below; a \
post-compile ERROR is still a TOPOLOGY signal, as below.) \
If reference_tree_from_query returns an ERROR, or returns confirmed=False with an \
unusable candidate, FALL BACK to the nearest known-good template below. \

"""
```

(Keep the existing blank line / formatting so the new section is visually separated from the templates section that follows.)

- [ ] **Step 4: Demote the templates section to fallback**

In the same `SYSTEM_PROMPT`, change the templates section's opening sentence. Replace:

```
KNOWN-GOOD BODY-PLAN TEMPLATES -- start from the closest one, then adapt. These \
topologies are MEASURED to pack; most ad-hoc trees do NOT. Five shared rules make \
the difference:
```

with:

```
KNOWN-GOOD BODY-PLAN TEMPLATES (FALLBACK ONLY -- prefer the reference-mesh \
candidate above; use a template only when reference_tree_from_query errored or its \
candidate will not pack). These topologies are MEASURED to pack, and their five \
shared rules are also SANITY CHECKS to apply to the reference candidate: \
```

- [ ] **Step 5: Run the fast prompt test + the existing agent-loop tests**

Run: `.venv/bin/python -m pytest tests/test_agent_reference_prompt.py tests/test_agent_turn.py -v`
Expected: PASS for the new test AND all of `test_agent_turn.py` (those use a FakeClient that ignores `system`, so the prompt rewrite cannot break them).

- [ ] **Step 6: Add the opt-in live smoke (skipped by default)**

Create `mcp_harness/tests/test_reference_smoke.py`:

```python
"""Opt-in end-to-end smoke: query -> (fake-mapped) mesh -> candidate -> agent
applies a correction -> compile -> lint. Skipped unless RUN_AGENT_SMOKE=1 and LLM
creds are configured, because it drives the real LLM + backend subprocesses.

Run it with, e.g.:
    RUN_AGENT_SMOKE=1 MESH_PROVIDER=fake LLM_PROVIDER=groq GROQ_API_KEY=... \
        .venv/bin/python -m pytest tests/test_reference_smoke.py -v -s
"""
import asyncio
import os
from contextlib import AsyncExitStack

import pytest

import agent_loop
import llm_client

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_AGENT_SMOKE"),
    reason="set RUN_AGENT_SMOKE=1 (and LLM creds) to run the live agent smoke")


def test_reference_smoke_beetle():
    os.environ.setdefault("MESH_PROVIDER", "fake")     # offline mesh, no cost

    async def run():
        client = llm_client.LLMClient.from_env()
        agent_loop.ensure_gate_trained()
        async with AsyncExitStack() as stack:
            backend = await agent_loop.connect_servers(stack)
            assert "reference_tree_from_query" in backend.route
            messages = [{"role": "user",
                         "content": "design a beetle origami base"}]
            await agent_loop.agent_turn(client, backend, messages)
            transcript = "\n".join(str(m.get("content", "")) for m in messages)
            # the agent must have consulted the reference tool at least once
            assert any(
                m.get("role") == "assistant"
                and any(tc["function"]["name"] == "reference_tree_from_query"
                        for tc in m.get("tool_calls", []))
                for m in messages), "agent never called reference_tree_from_query"
            return transcript

    transcript = asyncio.run(run())
    # best-effort behavioral signal; do not hard-fail on llama variance beyond the
    # tool-call assertion above.
    print("\n=== smoke transcript tail ===\n", transcript[-2000:])
```

- [ ] **Step 7: Verify the smoke is collected but skipped by default**

Run: `.venv/bin/python -m pytest tests/test_reference_smoke.py -v`
Expected: 1 skipped (reason mentions `RUN_AGENT_SMOKE`).

- [ ] **Step 8: Run the full suite**

Run: `.venv/bin/python -m pytest -q`
Expected: all pass, 2 skipped (the pre-existing skip + this new smoke). Report exact numbers.

- [ ] **Step 9: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_reference_prompt.py \
        mcp_harness/tests/test_reference_smoke.py
git commit -m "feat(agent): mesh-reference-first system prompt + opt-in live smoke

Agent now calls reference_tree_from_query first and starts from the measured
candidate (semantic corrections only); templates demoted to fallback. Fast test
pins the wiring; opt-in RUN_AGENT_SMOKE smoke drives the full query->mesh->tree->
compile->lint path.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Controller follow-up (not a subagent task)

After the branch is merge-ready, update memory: add a `project` memory recording that Slice #1 wired mesh→tree into the agent (reference_tree_from_query tool + candidate-primary prompt + FakeMeshProvider mapping), the text-only constraint, and that templates are now fallback (slated for eventual removal). Update the MEMORY.md index hook.

## Self-Review

**Spec coverage:** §3 prerequisite merge → Task 1. §4 tool + report → Tasks 4 (tool) and 3 (formatter). §5 prompt redesign → Task 5 Steps 3-4. §6 FakeMeshProvider mapping → Task 2. §7 testing → offline tests in Tasks 2/3/4 + fast prompt test + opt-in smoke in Task 5. §8 error handling → Task 4 (tool `ERROR:`) + Task 3 (empty/confirmed=False report branches). §9 success criteria → offline suite (Tasks 2-4) + live smoke (Task 5). §10 out-of-scope respected (templates kept as fallback; no vision; no UI). §11 constraints in Global Constraints + the offline-default provider in Task 4.

**Placeholder scan:** none — every code/step is concrete; the only deferred item (controller memory update) is explicitly outside the task list.

**Type consistency:** `MeshTreeResult(confirmed, nodes, pairs, voxel_res, prune_fraction, gate, trace)` is constructed identically in Tasks 3 and 4 tests and matches `mesh_to_tree`. `format_reference_report(result, *, prompt, mesh_path)` signature matches its caller in Task 4. `acquire_mesh(prompt, provider_name=...)` and `auto_mesh_to_metric_tree(glb)` match the verified PR #11 / mesh_to_tree signatures. `_fixture_for_prompt` / `FakeMeshProvider(fixture_path=None)` are consistent across Task 2's impl and tests.

# Gate Wiring & Seam Replacement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the VLM pipeline with the S5 human gate the production mesh→tree step: `reference_tree_from_query` runs `gated_pipeline.start`, the web bridge drives the review loop and calls a bridge-only `resume_reference_tree`, the agent compiles the approved tree unchanged, and the skeletonizer leaves the serve path.

**Architecture:** The pause is a return value (S5). `reference_tree_from_query` returns a `__gate__`-marked state; `agent_loop.agent_turn` recognises it in code, holds the tool result with a placeholder, emits a `gate` event, and ends the turn — the model never sees the state or the figure. The bridge (`web/server.py`) shows a React `ReviewPanel`, calls `resume_reference_tree` through the backend session on each answer, and on approval replaces the placeholder with a REFERENCE REPORT and restarts the turn. This is the LangGraph `interrupt()` / Claude-Code permission-prompt pattern: the interrupted call's result is the only thing the model ever receives.

**Tech Stack:** Python 3.14, FastMCP (async tools), pytest, Starlette `TestClient` for the bridge, React 18 + Vite + vitest for the frontend, the S5 `gated_pipeline` module.

**Spec:** `docs/superpowers/specs/2026-09-11-gate-wiring-and-seam-replacement-design.md`

## Global Constraints

- Run every command from `mcp_harness/` (Python) or `web/frontend/` (frontend). Python interpreter: `<repo>/.venv/bin/python`.
- **Never `python - <<EOF`.** Heredoc-to-stdin cannot drive the spawn workers `compile_tree` uses. Use a real `.py` file with an `if __name__ == "__main__":` guard, or `python -c`.
- **Every runnable `.py` needs an `if __name__ == "__main__":` guard.**
- `MAX_REVISIONS = 3` is S5's, in `gated_pipeline`. This work never re-implements it and never constructs a gate state — it only forwards one.
- **`render_tree_sheet` must never be added to `agent_loop.IMAGE_RESULT_TOOLS`, and the model must never receive its own rendered tree figure** (measured MAE 0.53 vs 0.29). `sheet_png` bytes appear only in `review` frames, never in `messages`.
- **Anatomy outranks packability.** Nothing compiles that a human did not approve; the human approves the tree that is actually compiled (agent edits nothing post-approval).
- **Never rescale measured proportions to force a pack.**
- The gate state stays plain JSON-serialisable — no objects, no callables.
- Docstrings explain **why** and record what was measured. A surprising line carries its evidence.
- Tests run offline: inject the VLM client, use `MESH_PROVIDER=fake`, stub `pack_fn` where the C++ is not under test.
- A test whose fixture could make two branches agree must be shown to fail against an injected defect (S5 shipped six blind tests of exactly that shape).

---

## File Structure

| file | responsibility | change |
|---|---|---|
| `mcp_harness/server.py` | `reference_tree_from_query` runs the gate; new `resume_reference_tree` tool + label stash | modify |
| `mcp_harness/agent_loop.py` | `agent_turn` gate interrupt; hide `resume_reference_tree` from the model; system-prompt "compile unchanged" | modify |
| `mcp_harness/anatomy_oracle.py` | stand down `human-approved` on a marked report | modify |
| `web/server.py` | the review loop: `gate` event → review frame → `review_answer` → resume/restart | modify |
| `web/frontend/src/chat.ts` | `review` frame type + reducer state | modify |
| `web/frontend/src/App.tsx` | render `ReviewPanel`, disable composer during a review, send `review_answer` | modify |
| `web/frontend/src/ReviewPanel.tsx` | the figure + summary + Approve/Revise/exhausted controls | create |
| `mcp_harness/mesh_acquire.py` | delete the dead `query_to_metric_tree` seam | modify |
| probes/tests that referenced the dead seam | migrate off it | modify |

Nothing in `gated_pipeline.py` changes — this plan consumes S5, it does not alter it.

---

### Task 1: `reference_tree_from_query` runs the gate

`server.py:4211` is the only production call to `auto_mesh_to_metric_tree`. Replace the extract half with `gated_pipeline.start`; the tool now returns a `__gate__`-marked state on success, or `ERROR:` on a failed draft.

**Files:**
- Modify: `mcp_harness/server.py` (`reference_tree_from_query`, currently `4162`–`4227`)
- Modify: `mcp_harness/reference_demo.py` (the one non-MCP synchronous caller)
- Test: `mcp_harness/tests/test_reference_gate.py` (new)

**Caller check:** through MCP, FastMCP awaits an async tool natively, so the serve path is unaffected by making this `async`. The only synchronous caller is the standalone demo `reference_demo.py:28` (`print(server.reference_tree_from_query(prompt=prompt))`), which would otherwise print a coroutine. The other two hits (`judge_loop.py:14`, `agent_loop.py:205`) are docstring/prompt text, not calls. As part of Step 3, change the demo line to `print(asyncio.run(server.reference_tree_from_query(prompt=prompt)))` and add `import asyncio` at the top of `reference_demo.py`.

**Interfaces:**
- Consumes: `gated_pipeline.start(mesh_path, *, client, out_dir, pack_fn=None) -> dict` (S5); `mesh_acquire.acquire_mesh(prompt, *, provider_name) -> str`; `llm_client.LLMClient.from_env()`.
- Produces: `reference_tree_from_query(prompt: str) -> str` — an `async` MCP tool returning `json.dumps({**state, "__gate__": True})` when `state["status"] == "awaiting_review"`, else `"ERROR: <note>"`. The `__gate__` key is what Task 3 keys the interrupt on.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_reference_gate.py`:

```python
"""reference_tree_from_query wraps the S5 gate.

Boundary: this unit owns the WIRING (mesh acquire -> start -> __gate__/ERROR),
not the VLM. `gated_pipeline.start` is stubbed so the tests are offline and
assert only what this function decides."""
import asyncio
import json

import server


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_awaiting_review_is_returned_as_a_gate_state(monkeypatch, tmp_path):
    monkeypatch.setattr(server.mesh_acquire, "acquire_mesh",
                        lambda prompt, provider_name="fake": str(tmp_path / "m.glb"))

    async def fake_start(mesh_path, *, client, out_dir, pack_fn=None):
        return {"status": "awaiting_review", "round": 0, "sheet_png": "x.png",
                "summary": "Read as: a dog", "tree": {}, "metric_tree": {}}

    monkeypatch.setattr(server.gated_pipeline, "start", fake_start)
    monkeypatch.setattr(server.llm_client.LLMClient, "from_env",
                        classmethod(lambda cls: object()))

    out = _run(server.reference_tree_from_query("a dog"))
    parsed = json.loads(out)
    assert parsed["__gate__"] is True
    assert parsed["status"] == "awaiting_review"
    assert parsed["summary"] == "Read as: a dog"


def test_a_failed_draft_is_returned_as_ERROR(monkeypatch, tmp_path):
    monkeypatch.setattr(server.mesh_acquire, "acquire_mesh",
                        lambda prompt, provider_name="fake": str(tmp_path / "m.glb"))

    async def fake_start(mesh_path, *, client, out_dir, pack_fn=None):
        return {"status": "failed", "note": "the model returned no tree "
                "(finish_reason: length); LLM_MAX_TOKENS is 4096, need >= 64000"}

    monkeypatch.setattr(server.gated_pipeline, "start", fake_start)
    monkeypatch.setattr(server.llm_client.LLMClient, "from_env",
                        classmethod(lambda cls: object()))

    out = _run(server.reference_tree_from_query("a dog"))
    assert out.startswith("ERROR:")
    assert "LLM_MAX_TOKENS" in out


def test_an_acquisition_exception_is_returned_as_ERROR(monkeypatch):
    def boom(prompt, provider_name="fake"):
        raise RuntimeError("provider down")

    monkeypatch.setattr(server.mesh_acquire, "acquire_mesh", boom)
    out = _run(server.reference_tree_from_query("a dog"))
    assert out.startswith("ERROR:")
    assert "provider down" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_reference_gate.py -q`
Expected: FAIL — `reference_tree_from_query` is not a coroutine (the `_run` await raises `TypeError`), and it still returns a report, not a `__gate__` state.

- [ ] **Step 3: Rewrite the function body**

In `mcp_harness/server.py`, add near the other module imports at the top (with the existing `import`s):

```python
import gated_pipeline
import llm_client
```

Replace the whole `reference_tree_from_query` function (from `@mcp.tool()` / `def reference_tree_from_query` through its `except` return) with:

```python
@mcp.tool()
async def reference_tree_from_query(prompt: str) -> str:
    """Acquire a rough 3-D mesh for the subject, author a metric tree from it
    with the VLM, make it packable, draw a four-view figure, and STOP for a
    human to approve the anatomy.

    Returns one of two things, NEVER a finished tree the agent then edits:
      * a JSON gate state with "__gate__": true and status "awaiting_review".
        agent_loop.agent_turn recognises the marker IN CODE, holds this call's
        result, and ends the turn so the web bridge can run the review loop.
        The model never receives this state or the figure -- measured: showing
        a model its own figure scored MAE 0.53 vs 0.29 for no self-review.
      * "ERROR: ..." when the draft failed (no tree, token cap, provider
        down). The agent's existing template fallback applies unchanged.

    The mesh->tree step is now the VLM path; auto_mesh_to_metric_tree is no
    longer called here (2026-09-11 seam replacement). Labels for read_base are
    stashed by resume_reference_tree on approval, not here.
    """
    import tempfile
    # Clear any prior subject's anatomy stash BEFORE the provider runs, for the
    # same reason the old extractor did: a failed draft must not leave the
    # previous subject's labels for a hand-drafted same-shaped tree to inherit.
    _LAST_EXTRACTION.clear()
    try:
        provider_name = os.environ.get("MESH_PROVIDER", "fake")
        glb = mesh_acquire.acquire_mesh(prompt, provider_name=provider_name)
        client = llm_client.LLMClient.from_env()
        out_dir = tempfile.mkdtemp(prefix="gate_")
        state = await gated_pipeline.start(glb, client=client, out_dir=out_dir)
    except Exception as exc:                # serve-path: never raise across MCP
        return f"ERROR: reference extraction failed: {exc}"

    if state.get("status") == "awaiting_review":
        return json.dumps({**state, "__gate__": True})
    return f"ERROR: {state.get('note') or 'reference draft failed'}"
```

Note: `mesh_acquire` is already imported inside the old body; move `import mesh_acquire` to the top of the module beside the new imports if it is not already module-level (grep first: `grep -n '^import mesh_acquire' server.py`). Leave `_note_extraction`, `_judge_the_extraction`, `_judge_failed` in place — they are used by other paths and by Task 2's stash.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_reference_gate.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/server.py mcp_harness/reference_demo.py mcp_harness/tests/test_reference_gate.py
git commit -m "wire: reference_tree_from_query runs the S5 gate, returns __gate__/ERROR

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `resume_reference_tree` tool + the approval label stash

The bridge needs a tool to carry the human's answer into `gated_pipeline.resume`. It is registered so the bridge can call it through the backend session, but Task 3 hides it from the model. It adds one verdict of its own — `compile_anyway` — because S5's `resume()` refuses `approve` on an `exhausted` state (its I3 guard), and that guard stays.

**Files:**
- Modify: `mcp_harness/server.py` (new tool + a stash helper)
- Test: `mcp_harness/tests/test_resume_reference_tree.py` (new)

**Interfaces:**
- Consumes: `gated_pipeline.resume(state, verdict, feedback="", *, client, out_dir, pack_fn=None) -> dict` (S5); `state["metric_tree"] = {"tree_nodes", "symmetric_pairs", "names": {str_id: label}}`; `_LAST_EXTRACTION` (module global, dict).
- Produces: `resume_reference_tree(state: dict, verdict: str, feedback: str = "") -> str` — an `async` MCP tool returning the new state as JSON. On approval (`approve` or `compile_anyway`) it stashes the approved tree's leaf labels into `_LAST_EXTRACTION`. On `compile_anyway` from an `exhausted` state it approves the last tree and sets `state["compiled_after_exhaustion"] = True`. Any other terminal-state verdict returns `ERROR:` carrying S5's `ValueError` text.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_resume_reference_tree.py`:

```python
"""resume_reference_tree: the bridge-only wrapper over gated_pipeline.resume.

`resume` itself is stubbed except where the compile_anyway verdict is this
tool's OWN behaviour (S5's resume refuses approve on exhausted), which is
tested against the real gated_pipeline.resume to prove the guard still bites."""
import asyncio
import json

import gated_pipeline
import server


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def _approved_state():
    return {"status": "awaiting_review", "round": 0,
            "metric_tree": {"tree_nodes": [{"id": 0, "parent_id": None, "length": 0.0}],
                            "symmetric_pairs": [],
                            "names": {"0": "spine"}},
            "tree": {}, "fold": "{}", "sheet_png": "x.png", "summary": "s",
            "history": [], "note": None, "revisions_authored": 0}


def test_approve_returns_the_new_state_and_stashes_labels(monkeypatch):
    async def fake_resume(state, verdict, feedback="", *, client, out_dir, pack_fn=None):
        return {**state, "status": "approved"}

    monkeypatch.setattr(gated_pipeline, "resume", fake_resume)
    monkeypatch.setattr(server.llm_client.LLMClient, "from_env",
                        classmethod(lambda cls: object()))
    server._LAST_EXTRACTION.clear()

    out = json.loads(_run(server.resume_reference_tree(_approved_state(), "approve", "")))
    assert out["status"] == "approved"
    assert server._LAST_EXTRACTION["labels"]["0"]["label"] == "spine"


def test_start_over_is_not_a_verdict_here(monkeypatch):
    # start_over is handled entirely in the bridge (no tool call). If the tool
    # is ever asked for it, it must refuse, not silently approve.
    monkeypatch.setattr(server.llm_client.LLMClient, "from_env",
                        classmethod(lambda cls: object()))
    out = _run(server.resume_reference_tree(_approved_state(), "start_over", ""))
    assert out.startswith("ERROR:")


def test_compile_anyway_approves_an_exhausted_state_with_the_marker(monkeypatch):
    # Uses the REAL resume to prove S5's guard refuses a plain 'approve' here,
    # so compile_anyway must be handled by this tool, not passed through.
    monkeypatch.setattr(server.llm_client.LLMClient, "from_env",
                        classmethod(lambda cls: object()))
    exhausted = {**_approved_state(), "status": "exhausted", "round": 3,
                 "note": "3 revisions were used and your last critique was not satisfied."}

    out = json.loads(_run(server.resume_reference_tree(exhausted, "compile_anyway", "")))
    assert out["status"] == "approved"
    assert out["compiled_after_exhaustion"] is True


def test_plain_approve_on_exhausted_still_refuses(monkeypatch):
    monkeypatch.setattr(server.llm_client.LLMClient, "from_env",
                        classmethod(lambda cls: object()))
    exhausted = {**_approved_state(), "status": "exhausted", "round": 3}
    out = _run(server.resume_reference_tree(exhausted, "approve", ""))
    assert out.startswith("ERROR:")
    assert "exhausted" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_resume_reference_tree.py -q`
Expected: FAIL — `server.resume_reference_tree` does not exist (`AttributeError`).

- [ ] **Step 3: Add the tool and stash helper**

In `mcp_harness/server.py`, add after `reference_tree_from_query`:

```python
def _stash_approved_labels(state) -> None:
    """Put the approved tree's leaf labels where read_base() will find them.

    Same contract as _note_extraction's stash (keys normalised to STRINGS,
    read back through json.dumps), but sourced from the VLM tree's own
    `names` map rather than a MeshTreeResult. `basis`/`position` are absent --
    the VLM names a flap without measuring a coordinate for it -- and every
    shipped label consumer already reads those through `.get()`, so their
    absence degrades to "no position", never a KeyError. Never raises: a
    bookkeeping failure must not turn an approval into an ERROR.
    """
    try:
        mt = state.get("metric_tree") or {}
        names = mt.get("names") or {}
        nodes = mt.get("tree_nodes") or []
        child_ids = {n.get("parent_id") for n in nodes}
        leaves = {str(n["id"]) for n in nodes
                  if n.get("parent_id") is not None and n["id"] not in child_ids}
        _LAST_EXTRACTION.clear()
        _LAST_EXTRACTION.update({
            "prompt": state.get("subject_guess") or "",
            "labels": {sid: {"label": names[sid]} for sid in names if sid in leaves},
            "nodes": [dict(n) for n in nodes],
        })
    except Exception:                                   # noqa: BLE001
        _LAST_EXTRACTION.clear()


@mcp.tool()
async def resume_reference_tree(state: dict, verdict: str,
                                feedback: str = "") -> str:
    """Carry the human's review answer into gated_pipeline.resume. BRIDGE ONLY.

    Registered so web/server.py can call it through the backend session;
    agent_loop hides it from the model (a gate the agent could drive is a gate
    the agent could skip -- the pattern S5 declined). Returns the new state as
    JSON, or "ERROR: ..." on a refused verdict.

    `compile_anyway` is this tool's OWN verdict, not S5's: resume() refuses
    `approve` on an `exhausted` state (its measured I3 guard, which stays).
    compile_anyway takes the last authored tree as approved and marks it so
    the report can say the approval followed an unmet critique.
    """
    import tempfile
    client = llm_client.LLMClient.from_env()
    out_dir = tempfile.mkdtemp(prefix="gate_")

    if verdict == "compile_anyway":
        if state.get("status") != "exhausted":
            return f"ERROR: compile_anyway is only valid on an exhausted review"
        approved = {**state, "status": "approved", "compiled_after_exhaustion": True}
        _stash_approved_labels(approved)
        return json.dumps(approved)

    try:
        new_state = await gated_pipeline.resume(
            state, verdict, feedback, client=client, out_dir=out_dir)
    except ValueError as exc:
        return f"ERROR: {exc}"

    if new_state.get("status") == "approved":
        _stash_approved_labels(new_state)
    return json.dumps(new_state)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_resume_reference_tree.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_resume_reference_tree.py
git commit -m "wire: resume_reference_tree (bridge-only) + approval label stash

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `agent_loop` — the gate interrupt, the hidden tool, the new instruction

`agent_turn` recognises a `__gate__` result in code, holds it behind a placeholder, emits a `gate` event, and ends the turn. `resume_reference_tree` is filtered out of the tools offered to the model. The system prompt tells the agent to compile the returned tree unchanged.

**Files:**
- Modify: `mcp_harness/agent_loop.py` (`connect_servers` tool filter; `agent_turn` per-call loop; the reference-tree paragraph of `SYSTEM_PROMPT`; a `_gate_state` helper and `_AGENT_HIDDEN_TOOLS`/`_offered_tools`)
- Test: `mcp_harness/tests/test_agent_loop_gate.py` (new)

**Interfaces:**
- Consumes: the `__gate__` string from Task 1; `run_tool`, `budget`, the existing `agent_turn` loop.
- Produces: `_gate_state(name, output) -> dict | None`; `_offered_tools(discovered) -> list`; a new emitted event `{"type": "gate", "state": dict, "tool_call_id": str}`. On the gate, `messages` gains a placeholder tool result `"[awaiting human review]"` for the pending call and `agent_turn` returns.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_agent_loop_gate.py`:

```python
"""agent_turn interrupts on a __gate__ result, and the resume tool is hidden.

The gate state must never reach `messages` as a tool result the model reads:
it is held behind a placeholder and re-emitted as a `gate` event. Mutation-
checked in test_removing_the_gate_check_lets_the_model_see_the_state."""
import asyncio
import json

import agent_loop


class _Call:
    def __init__(self, name, args):
        self.id = "call_1"
        self.function = type("F", (), {"name": name, "arguments": json.dumps(args)})()


class _Result:
    def __init__(self, tool_calls, text=""):
        self.text = text
        self.tool_calls = tool_calls
        self.finish_reason = "tool_calls" if tool_calls else "stop"
        self.usage = {"total_tokens": 1}


class _Client:
    def __init__(self, results):
        self._results = list(results)

    async def run_turn(self, system, messages, tools):
        return self._results.pop(0)


def _backend(route):
    from types import SimpleNamespace
    return SimpleNamespace(sessions={}, tools=[], route=route)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_gate_result_ends_the_turn_with_a_placeholder_not_the_state(monkeypatch):
    gate = json.dumps({"status": "awaiting_review", "sheet_png": "x.png",
                       "round": 0, "__gate__": True})

    async def fake_run_tool(backend, name, args):
        return gate

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)
    events = []
    messages = []
    client = _Client([_Result([_Call("reference_tree_from_query", {"prompt": "a dog"})])])
    _run(agent_loop.agent_turn(client, _backend({}), messages, emit=events.append))

    gate_events = [e for e in events if e["type"] == "gate"]
    assert len(gate_events) == 1
    assert gate_events[0]["state"]["status"] == "awaiting_review"
    assert gate_events[0]["tool_call_id"] == "call_1"
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert tool_msgs[-1]["content"] == "[awaiting human review]"
    # the raw state never entered the model-facing history
    assert all("awaiting_review" not in (m.get("content") or "") for m in tool_msgs)


def test_a_normal_tool_result_is_appended_and_the_turn_continues(monkeypatch):
    async def fake_run_tool(backend, name, args):
        return "ok result"

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)
    messages = []
    client = _Client([_Result([_Call("get_template", {"body_plan": "bird"})]),
                      _Result([])])
    _run(agent_loop.agent_turn(client, _backend({}), messages, emit=lambda e: None))
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert tool_msgs[-1]["content"].startswith("ok result")


def test_removing_the_gate_check_lets_the_model_see_the_state():
    # Discrimination guard: _gate_state must recognise the marker only for the
    # reference tool. If it returned None here the interrupt would never fire
    # and the state would be appended as a normal tool result.
    gate = json.dumps({"status": "awaiting_review", "__gate__": True})
    assert agent_loop._gate_state("reference_tree_from_query", gate) is not None
    assert agent_loop._gate_state("get_template", gate) is None
    assert agent_loop._gate_state("reference_tree_from_query", "ERROR: x") is None


def test_resume_tool_is_hidden_from_the_model():
    class _T:
        def __init__(self, name):
            self.name = name
    offered = agent_loop._offered_tools(
        [_T("reference_tree_from_query"), _T("resume_reference_tree"),
         _T("draft_and_compile_full_base")])
    names = {t.name for t in offered}
    assert "reference_tree_from_query" in names
    assert "draft_and_compile_full_base" in names
    assert "resume_reference_tree" not in names


def test_system_prompt_says_compile_the_approved_tree_unchanged():
    p = agent_loop.SYSTEM_PROMPT
    assert "UNCHANGED" in p
    assert "APPROVED" in p or "approved" in p
    # the exact phrase removed from the old contract (real casing in the source)
    assert "SEMANTIC correction only" not in p
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_agent_loop_gate.py -q`
Expected: FAIL — `_gate_state`, `_offered_tools`, `_AGENT_HIDDEN_TOOLS` do not exist; the prompt still says "semantic correction only".

- [ ] **Step 3a: Add the helpers and the tool filter**

In `mcp_harness/agent_loop.py`, near `IMAGE_RESULT_TOOLS`:

```python
#: Registered so the web bridge can call it through the backend session, but
#: NEVER offered to the model: a gate the agent could drive is a gate the
#: agent could skip (the pattern S5 §2 declined). Hidden here, not unregistered.
_AGENT_HIDDEN_TOOLS = frozenset({"resume_reference_tree"})


def _offered_tools(discovered):
    """The discovered tools minus the ones the model must never call."""
    return [t for t in discovered if t.name not in _AGENT_HIDDEN_TOOLS]


def _gate_state(name, output):
    """The parsed gate state when `output` is a __gate__ result from the
    reference tool, else None. Scoped to the reference tool by name so no
    other tool's JSON output is ever parsed as a gate."""
    if name != "reference_tree_from_query":
        return None
    try:
        parsed = json.loads(output)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) and parsed.get("__gate__") else None
```

In `connect_servers`, change the tools line from:

```python
    return Backend(sessions=sessions,
                   tools=llm_client.tools_to_openai(discovered),
                   route=route)
```

to:

```python
    return Backend(sessions=sessions,
                   tools=llm_client.tools_to_openai(_offered_tools(discovered)),
                   route=route)
```

(`route` still holds every tool, so the bridge can reach `resume_reference_tree`.)

- [ ] **Step 3b: Add the interrupt to the per-call loop**

This is a two-line initialiser plus an INSERT — do not move the existing shared
`messages.append`. The current `else` branch ends with
`emit({"type": "tool_result", ...})`, and a shared
`messages.append({"role": "tool", ...})` runs (dedented) for both the
bad-args and normal paths. The gate `continue` deliberately skips that shared
append, so the placeholder we add is the only tool message for the gate call.

First, initialise a holder immediately before the `for tc in result.tool_calls:` loop:

```python
        pending_gate = None
```

Then, in the `else` branch, INSERT the gate check between the `budget.record`
block and the existing `emit({"type": "tool_result", ...})` line — so the
existing block reads:

```python
                output = budget.refuse(name)
                if output is None:
                    output = await run_tool(backend, name, args)
                    budget.record(name, output)
                gate = _gate_state(name, output)
                if gate is not None and pending_gate is None:
                    # Interrupt: hold this call's result behind a placeholder so
                    # history stays valid, and let the bridge fill it in when the
                    # human answers. `continue` skips the shared tool append and
                    # the tool_result emit below, so the model never sees the
                    # state or the figure.
                    pending_gate = {"state": gate, "tool_call_id": tc.id}
                    messages.append({"role": "tool", "tool_call_id": tc.id,
                                     "content": "[awaiting human review]"})
                    continue
                emit({"type": "tool_result", "name": name,
                      "output": output, "is_error": output.startswith("ERROR:")})
```

(The shared `messages.append({"role": "tool", ...})` that follows the `else`
block is left exactly as it is — the `continue` above bypasses it for the gate
call and the normal path still reaches it.)

Then, immediately after the `for tc in result.tool_calls:` loop ends (before the `if step == MAX_AGENT_STEPS:` check), add:

```python
        if pending_gate is not None:
            emit({"type": "gate", **pending_gate})
            return
```

(The `bad tool arguments` branch keeps its existing `emit` + append; it never produces a gate.)

- [ ] **Step 3c: Rewrite the reference-tree paragraph of the system prompt**

In `SYSTEM_PROMPT`, replace the paragraph beginning `START FROM THE REFERENCE MESH` (at `agent_loop.py:203`) through the end of the GUARDRAIL sentence — the exact end marker is `post-compile ERROR is still a TOPOLOGY signal, as below.) \` (the last line before `If reference_tree_from_query returns an ERROR,`). Keep everything from `If reference_tree_from_query returns an ERROR,` onward. Replace the removed span with:

```python
"""START FROM THE REFERENCE MESH \
For any creature or subject request, your FIRST action is \
reference_tree_from_query(<the user's request>). It drafts a metric tree from a \
3-D model of the subject, makes it packable, and a HUMAN reviews its anatomy \
before you ever see it. What this tool returns to you is the APPROVED tree: \
its anatomy has already been checked and accepted by the person. Pass its \
tree_nodes and symmetric_pairs to draft_and_compile_full_base UNCHANGED -- do \
NOT rename anatomy, add or drop a flap, re-parent, or rescale a length. If you \
believe the anatomy is still wrong, SAY SO to the user in words; do not edit \
the approved tree. (Node-order / hub-grouping / sliver rework to clear a pack \
failure happens inside the compile path already and changes no proportions.) """
```

Keep the paragraphs that follow (`If reference_tree_from_query returns an ERROR...` and the KNOWN-GOOD TEMPLATES block) — the ERROR fallback still applies.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_agent_loop_gate.py tests/test_agent_loop_images.py -q`
Expected: PASS (5 new + the existing image tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_loop_gate.py
git commit -m "wire: agent_turn interrupts on __gate__, hides resume tool, compiles unchanged

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: the web bridge review loop

The bridge turns a `gate` event into a `review` frame, takes `review_answer` back, calls `resume_reference_tree` through the backend, loops until approved/exhausted/failed, and on approval replaces the placeholder tool result with a REFERENCE REPORT and restarts the turn.

**Files:**
- Modify: `web/server.py` (`_send_frames` gate branch; `ws_chat` receive loop; new `_send_review_frame`, `_approved_report`, `_resume` helpers)
- Test: `web/tests/test_server_gate.py` (new)

**Interfaces:**
- Consumes: the `gate` event from Task 3; `agent_loop.run_tool(backend, "resume_reference_tree", args) -> str` (JSON state or `ERROR:`); `state["metric_tree"]`, `state["summary"]`, `state["sheet_png"]`, `state["round"]`.
- Produces: frames `{"type":"review", "sheet_png": <base64>, "summary": str, "round": int, "remaining": int, "exhausted": bool, "failed": bool, "note": str|None}`; consumes client frames `{"type":"review_answer", "verdict": "approve"|"revise"|"compile_anyway"|"start_over", "feedback": str}`. `conn["gate"]` holds `{"state": dict, "tool_call_id": str}` while a review is open.

- [ ] **Step 1: Write the failing test**

Create `web/tests/test_server_gate.py`:

```python
"""The gate half of the bridge: gate event -> review frame -> review_answer.

agent_turn and run_tool are faked so the loop runs offline. The fakes make no
two branches agree by accident: the approve path returns a genuinely different
state from the revise path, and the assertions read the frames the bridge
actually sent."""
import base64
import json
import os
from types import SimpleNamespace

from starlette.testclient import TestClient

_REF = "reference_tree_from_query"


def _state(status="awaiting_review", rnd=0):
    return {"status": status, "round": rnd, "sheet_png": None, "summary": "Read as: a dog",
            "metric_tree": {"tree_nodes": [{"id": 0, "parent_id": None, "length": 0.0},
                                           {"id": 1, "parent_id": 0, "length": 0.3}],
                            "symmetric_pairs": [], "names": {"0": "spine", "1": "head"}},
            "tree": {}, "note": None}


def _client(monkeypatch, gate_state, resume_script, tmp_path):
    import agent_loop
    import llm_client

    png = tmp_path / "sheet.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 16)
    gate_state = {**gate_state, "sheet_png": str(png)}

    async def fake_connect(stack):
        return SimpleNamespace(sessions={}, tools=[], route={"x": 1})

    monkeypatch.setattr(agent_loop, "connect_servers", fake_connect)
    monkeypatch.setattr(
        llm_client.LLMClient, "from_env",
        classmethod(lambda cls: SimpleNamespace(cfg=SimpleNamespace(provider="fake", model="fake"))))

    turn = {"n": 0}

    async def fake_turn(client_, backend, messages, emit=None):
        # Turn 0 hits the gate; later turns (after approval) do nothing.
        if turn["n"] == 0:
            emit({"type": "gate", "state": gate_state, "tool_call_id": "call_1"})
        turn["n"] += 1

    monkeypatch.setattr(agent_loop, "agent_turn", fake_turn)

    resume = {"n": 0}

    async def fake_run_tool(backend, name, args):
        assert name == "resume_reference_tree"
        out = resume_script[resume["n"]]
        resume["n"] += 1
        return json.dumps(out)

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)
    monkeypatch.setenv("MESH_PROVIDER", "fake")

    import importlib
    import web.server as server
    importlib.reload(server)
    return TestClient(server.app)


def _drain_to_review(ws):
    while True:
        f = ws.receive_json()
        if f["type"] == "review":
            return f


def test_gate_event_becomes_a_review_frame(monkeypatch, tmp_path):
    client = _client(monkeypatch, _state(), [{**_state(), "status": "approved"}], tmp_path)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "a dog"})
        f = _drain_to_review(ws)
        assert f["summary"] == "Read as: a dog"
        assert f["remaining"] == 3
        assert base64.b64decode(f["sheet_png"]).startswith(b"\x89PNG")


def test_approve_clears_the_review_and_restarts(monkeypatch, tmp_path):
    client = _client(monkeypatch, _state(), [{**_state(), "status": "approved"}], tmp_path)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "a dog"})
        _drain_to_review(ws)
        ws.send_json({"type": "review_answer", "verdict": "approve", "feedback": ""})
        # After approval the turn restarts and ends cleanly.
        saw_turn_end = False
        for _ in range(10):
            f = ws.receive_json()
            if f["type"] == "turn_end":
                saw_turn_end = True
                break
        assert saw_turn_end


def test_revise_reopens_the_review_with_one_fewer_remaining(monkeypatch, tmp_path):
    client = _client(monkeypatch, _state(),
                     [{**_state(rnd=1), "status": "awaiting_review"}], tmp_path)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "a dog"})
        _drain_to_review(ws)
        ws.send_json({"type": "review_answer", "verdict": "revise",
                      "feedback": "legs too short"})
        f = _drain_to_review(ws)
        assert f["remaining"] == 2


def test_exhausted_offers_compile_anyway(monkeypatch, tmp_path):
    client = _client(monkeypatch, _state(rnd=3),
                     [{**_state(rnd=3), "status": "exhausted",
                       "note": "3 revisions were used..."}], tmp_path)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "a dog"})
        _drain_to_review(ws)
        ws.send_json({"type": "review_answer", "verdict": "revise", "feedback": "no"})
        f = _drain_to_review(ws)
        assert f["exhausted"] is True


def test_a_prompt_during_an_open_review_is_refused(monkeypatch, tmp_path):
    client = _client(monkeypatch, _state(), [{**_state(), "status": "approved"}], tmp_path)
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "a dog"})
        _drain_to_review(ws)
        ws.send_json({"type": "prompt", "text": "a second thing"})
        f = ws.receive_json()
        assert f["type"] == "error"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd .. && PYTHONPATH=mcp_harness:mcp_harness/tests <repo>/.venv/bin/python -m pytest web/tests/test_server_gate.py -q`
Expected: FAIL — the bridge has no `gate` branch, no `review` frame, no `review_answer` handling.

- [ ] **Step 3a: Add the bridge helpers**

In `web/server.py`, add near the top imports:

```python
import base64  # noqa: E402
```

Add these module-level helpers (above `ws_chat`):

```python
def _review_frame(state: dict, *, exhausted: bool = False,
                  failed: bool = False) -> dict:
    """The frame the human reviews: the figure, the summary, the budget."""
    remaining = max(0, gated_pipeline.MAX_REVISIONS - int(state.get("round", 0)))
    sheet_b64 = None
    path = state.get("sheet_png")
    if path and os.path.isfile(path):
        with open(path, "rb") as fh:
            sheet_b64 = base64.b64encode(fh.read()).decode("ascii")
    return {"type": "review", "sheet_png": sheet_b64,
            "summary": state.get("summary", ""), "round": int(state.get("round", 0)),
            "remaining": remaining, "exhausted": exhausted, "failed": failed,
            "note": state.get("note")}


def _approved_report(state: dict) -> str:
    """The tool result the model finally sees: the APPROVED tree, verbatim.

    Same shape as the old mesh_report candidate block (tree_nodes /
    symmetric_pairs the agent passes to draft_and_compile_full_base), plus a
    marker line the anatomy oracle stands down on. Carries no figure."""
    mt = state.get("metric_tree") or {}
    round_n = int(state.get("round", 0))
    marker = (f"[human-approved round {round_n} after an unmet critique]"
              if state.get("compiled_after_exhaustion")
              else f"[human-approved round {round_n}]")
    names = mt.get("names") or {}
    named = ", ".join(f"{i}={names[i]}" for i in sorted(names))
    return "\n".join([
        "REFERENCE (human-approved). Pass tree_nodes and symmetric_pairs to "
        "draft_and_compile_full_base UNCHANGED.",
        marker,
        f"  tree_nodes = {json.dumps(mt.get('tree_nodes', []))}",
        f"  symmetric_pairs = {json.dumps(mt.get('symmetric_pairs', []))}",
        f"  flap labels: {named}",
        "",
        state.get("summary", ""),
    ])


async def _resume_gate(state: dict, verdict: str, feedback: str) -> dict:
    """Call the bridge-only resume tool and parse the new state (or raise)."""
    out = await agent_loop.run_tool(
        state_backend(), "resume_reference_tree",
        {"state": state, "verdict": verdict, "feedback": feedback})
    if out.startswith("ERROR:"):
        raise RuntimeError(out)
    return json.loads(out)


def state_backend():
    return state.backend
```

(`gated_pipeline` and `json` are importable in this process — `agent_loop` already puts `mcp_harness/` on `sys.path`. Add `import gated_pipeline  # noqa: E402` beside the other `mcp_harness` imports at the top of `web/server.py`.)

- [ ] **Step 3b: Add the gate branch to `_send_frames`**

In `web/server.py._send_frames`, add a branch for the `gate` event (alongside the `notice`/`tool_result` branches):

```python
    elif kind == "gate":
        conn["gate"] = {"state": event["state"], "tool_call_id": event["tool_call_id"]}
        await ws.send_json(_review_frame(event["state"]))
```

- [ ] **Step 3c: Handle `review_answer` and lock prompts during a review**

In `web/server.py.ws_chat`, initialise the gate slot where `conn` is built (add to the dict): `"gate": None,`.

In the receive loop, add a `review_answer` handler before the `if raw.get("type") != "prompt":` guard, and refuse prompts while a review is open. Insert:

```python
        if raw.get("type") == "review_answer":
            gate = conn.get("gate")
            if gate is None:
                continue
            verdict = raw.get("verdict")
            feedback = raw.get("feedback", "")
            if verdict == "start_over":
                messages.append({"role": "tool",
                                 "tool_call_id": gate["tool_call_id"],
                                 "content": "ERROR: the user abandoned the review"})
                conn["gate"] = None
                try:
                    await run_agent_turn()
                except WebSocketDisconnect:
                    return
                continue
            try:
                new_state = await _resume_gate(gate["state"], verdict, feedback)
            except RuntimeError as exc:
                await ws.send_json({"type": "error", "message": str(exc)})
                continue
            status = new_state.get("status")
            if status == "awaiting_review":
                conn["gate"]["state"] = new_state
                await ws.send_json(_review_frame(new_state))
            elif status == "approved":
                messages.append({"role": "tool",
                                 "tool_call_id": gate["tool_call_id"],
                                 "content": _approved_report(new_state)})
                # The report carries [human-approved]; the anatomy oracle stands
                # down on it (Task 5). Set it as this turn's report so the
                # per-fold check sees the marker.
                conn["latest_report"] = _approved_report(new_state)
                conn["gate"] = None
                try:
                    ok = await run_agent_turn()
                except WebSocketDisconnect:
                    return
                if conn.get("gate"):
                    continue
                if ok:
                    cp_fired = await maybe_cp_repair()
                    if not cp_fired:
                        anatomy_fired = await maybe_anatomy_check()
                        if not anatomy_fired:
                            await maybe_fidelity_check()
            elif status == "exhausted":
                conn["gate"]["state"] = new_state
                await ws.send_json(_review_frame(new_state, exhausted=True))
            elif status == "failed":
                conn["gate"]["state"] = new_state
                await ws.send_json(_review_frame(new_state, failed=True))
            continue

        if conn.get("gate") is not None and raw.get("type") == "prompt":
            await ws.send_json({"type": "error",
                                "message": "Finish the anatomy review before sending another prompt."})
            continue
```

Then, where the existing `prompt` path runs `ok = await run_agent_turn()` followed by the oracle cascade, guard the cascade so a paused turn skips it:

```python
            ok = await run_agent_turn()
            if conn.get("gate"):
                continue
            if ok:
                cp_fired = await maybe_cp_repair()
                ...
```

(Add only the `if conn.get("gate"): continue` line; the rest of the cascade is unchanged.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd .. && PYTHONPATH=mcp_harness:mcp_harness/tests <repo>/.venv/bin/python -m pytest web/tests/test_server_gate.py -q`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add web/server.py web/tests/test_server_gate.py
git commit -m "wire: web bridge drives the review loop (gate event -> review frame -> resume)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: anatomy oracle stands down on an approved tree

Under "compile unchanged" there is no agent edit for the `[ANATOMY]` oracle to catch, so it must stand down explicitly on a human-approved report — not fire a false shortfall, and not be silently bypassed.

**Files:**
- Modify: `mcp_harness/anatomy_oracle.py` (`decide`)
- Test: `mcp_harness/tests/test_anatomy_oracle.py` (add cases)

**Interfaces:**
- Consumes: `report_text` (may carry `[human-approved`).
- Produces: `decide(...)` returns `{"fire": False, "reason": "human-approved", ...}` when the report is marked; unmarked reports behave exactly as before.

- [ ] **Step 1: Write the failing test**

Add to `mcp_harness/tests/test_anatomy_oracle.py`:

```python
def test_a_human_approved_report_stands_the_oracle_down():
    # Under "compile unchanged" the tree the human approved IS what compiles,
    # so there is no agent edit to grade. A shortfall would otherwise fire:
    # served 1 leaf, but no reference count is claimed, so this must stand down
    # on the marker, not on the absent count.
    import anatomy_oracle
    report = ("REFERENCE (human-approved).\n[human-approved round 0]\n"
              "reference feature count (authored): 6")
    tree = [{"id": 0, "parent_id": None, "length": 0.0},
            {"id": 1, "parent_id": 0, "length": 0.3}]
    v = anatomy_oracle.decide(report_text=report, tree_nodes=tree,
                              symmetric_pairs=[], mesh_provider="fake")
    assert v["fire"] is False
    assert v["reason"] == "human-approved"


def test_an_unmarked_report_is_unaffected():
    # Guard: the stand-down keys on the marker, not on the word "approved"
    # appearing anywhere. A normal report with a real shortfall still fires.
    import anatomy_oracle
    report = "reference feature count (authored): 6"
    tree = [{"id": 0, "parent_id": None, "length": 0.0},
            {"id": 1, "parent_id": 0, "length": 0.3}]
    v = anatomy_oracle.decide(report_text=report, tree_nodes=tree,
                              symmetric_pairs=[], mesh_provider="meshy")
    assert v["reason"] != "human-approved"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_anatomy_oracle.py -q`
Expected: FAIL — `decide` has no `human-approved` stand-down.

- [ ] **Step 3: Add the stand-down**

In `mcp_harness/anatomy_oracle.py`, in `decide`, immediately after the `report_text` presence guard (the block that returns `reason="no-mesh-report"`), add:

```python
    # HUMAN-APPROVED. Since the 2026-09-11 gate wiring, a report marked
    # [human-approved ...] describes a tree a person accepted and the agent
    # compiles UNCHANGED -- there is no agent edit to grade, and R would just
    # be the approved tree's own leaf count. Stand down explicitly rather than
    # firing a false shortfall or being silently bypassed.
    if "[human-approved" in report_text:
        out["reason"] = "human-approved"
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_anatomy_oracle.py -q`
Expected: PASS (all, including the two new).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/anatomy_oracle.py mcp_harness/tests/test_anatomy_oracle.py
git commit -m "wire: anatomy oracle stands down on a human-approved report

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: the React ReviewPanel

The frontend renders the four-view figure and the summary, takes Approve / Revise (with feedback) / the exhausted choices, and disables the composer while a review is open.

**Files:**
- Modify: `web/frontend/src/chat.ts` (frame type + reducer state)
- Create: `web/frontend/src/ReviewPanel.tsx`
- Modify: `web/frontend/src/App.tsx` (render the panel, disable composer, send `review_answer`)
- Test: `web/frontend/src/review.test.ts` (new)

**Interfaces:**
- Consumes: `{type:"review", sheet_png, summary, round, remaining, exhausted, failed, note}`.
- Produces: reducer state `review: ReviewState | null`; sends `{type:"review_answer", verdict, feedback}`.

- [ ] **Step 1: Write the failing test**

Create `web/frontend/src/review.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { applyFrame, initialState } from "./chat";

describe("review frames", () => {
  it("stores an open review and blocks the composer", () => {
    const s = applyFrame(initialState, {
      type: "review", sheet_png: "AAAA", summary: "Read as: a dog",
      round: 0, remaining: 3, exhausted: false, failed: false, note: null,
    } as any);
    expect(s.review).not.toBeNull();
    expect(s.review!.remaining).toBe(3);
    expect(s.review!.exhausted).toBe(false);
  });

  it("clears the open review on turn_end after an approval", () => {
    let s = applyFrame(initialState, {
      type: "review", sheet_png: "AAAA", summary: "s",
      round: 0, remaining: 3, exhausted: false, failed: false, note: null,
    } as any);
    s = applyFrame(s, { type: "turn_end", ok: true });
    expect(s.review).toBeNull();
  });

  it("a second review frame replaces the first (a revision)", () => {
    let s = applyFrame(initialState, {
      type: "review", sheet_png: "A", summary: "s", round: 0, remaining: 3,
      exhausted: false, failed: false, note: null,
    } as any);
    s = applyFrame(s, {
      type: "review", sheet_png: "B", summary: "s2", round: 1, remaining: 2,
      exhausted: false, failed: false, note: null,
    } as any);
    expect(s.review!.remaining).toBe(2);
    expect(s.review!.summary).toBe("s2");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/frontend && npm test -- review.test.ts`
Expected: FAIL — `chat.ts` has no `review` frame or `review` state.

- [ ] **Step 3a: Extend `chat.ts`**

In `web/frontend/src/chat.ts`, add to the `Frame` union:

```ts
  | { type: "review"; sheet_png: string | null; summary: string;
      round: number; remaining: number; exhausted: boolean;
      failed: boolean; note: string | null }
```

Add the review-state type and field:

```ts
export interface ReviewState {
  sheetPng: string | null;
  summary: string;
  round: number;
  remaining: number;
  exhausted: boolean;
  failed: boolean;
  note: string | null;
}
```

Add `review: ReviewState | null;` to `ChatState`, and `review: null,` to `initialState`.

In `applyFrame`, add a `review` case, and clear the review on `turn_end`:

```ts
    case "review":
      return { ...state, review: {
        sheetPng: frame.sheet_png, summary: frame.summary, round: frame.round,
        remaining: frame.remaining, exhausted: frame.exhausted,
        failed: frame.failed, note: frame.note } };
```

Change the existing `turn_end` case to also clear the review:

```ts
    case "turn_end":
      return { ...state, busy: false, review: null };
```

- [ ] **Step 3b: Create `ReviewPanel.tsx`**

Create `web/frontend/src/ReviewPanel.tsx`:

```tsx
import type { ReviewState } from "./chat";

export type ReviewVerdict = "approve" | "revise" | "compile_anyway" | "start_over";

export default function ReviewPanel(props: {
  review: ReviewState;
  feedback: string;
  onFeedback: (s: string) => void;
  onAnswer: (v: ReviewVerdict) => void;
}) {
  const { review, feedback, onFeedback, onAnswer } = props;
  return (
    <div className="review">
      <h3>Does the anatomy look right?</h3>
      {review.sheetPng &&
        <img alt="proposed tree, four views"
             src={`data:image/png;base64,${review.sheetPng}`} />}
      <pre className="review-summary">{review.summary}</pre>
      {review.note && <p className="review-note">{review.note}</p>}
      {review.failed ? (
        <div className="review-actions">
          <button onClick={() => onAnswer("revise")}>Revise again</button>
          <button onClick={() => onAnswer("start_over")}>Start over</button>
        </div>
      ) : review.exhausted ? (
        <div className="review-actions">
          <button onClick={() => onAnswer("compile_anyway")}>Compile anyway</button>
          <button onClick={() => onAnswer("start_over")}>Start over</button>
        </div>
      ) : (
        <div className="review-actions">
          <button onClick={() => onAnswer("approve")}>Approve</button>
          <textarea value={feedback} placeholder="What needs fixing?"
            onChange={(e) => onFeedback(e.target.value)} />
          <button disabled={review.remaining === 0}
            onClick={() => onAnswer("revise")}>
            Revise ({review.remaining} left)
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3c: Wire `App.tsx`**

In `web/frontend/src/App.tsx`: import the panel and its verdict type:

```tsx
import ReviewPanel from "./ReviewPanel";
import type { ReviewVerdict } from "./ReviewPanel";
```

Add feedback state beside the others: `const [feedback, setFeedback] = useState("");`

Add a sender:

```tsx
  function answerReview(v: ReviewVerdict) {
    if (wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({
      type: "review_answer", verdict: v, feedback }));
    setFeedback("");
  }
```

Render the panel in the chat section, above the composer, when a review is open:

```tsx
        {state.review &&
          <ReviewPanel review={state.review} feedback={feedback}
            onFeedback={setFeedback} onAnswer={answerReview} />}
```

Disable the composer while a review is open — change the `textarea` and `button` `disabled` conditions from `state.busy` to `state.busy || state.review !== null`.

- [ ] **Step 4: Run tests**

Run: `cd web/frontend && npm test -- review.test.ts chat.test.ts`
Expected: PASS (the new review suite + the existing chat suite).

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/chat.ts web/frontend/src/ReviewPanel.tsx web/frontend/src/App.tsx web/frontend/src/review.test.ts
git commit -m "wire: React ReviewPanel renders the gate figure and takes the verdict

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: replace the seam — delete the dead path, migrate its users, add the invariant test

`auto_mesh_to_metric_tree` is no longer called on the serve path (Task 1). `mesh_acquire.query_to_metric_tree` has no production callers and is deleted; its three probes and three tests migrate to calling `acquire_mesh` + `auto_mesh_to_metric_tree` directly, which is exactly what it did. An invariant test pins that nothing outside `mesh_to_tree` calls the skeletonizer on the serve path.

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (delete `query_to_metric_tree`)
- Modify: `mcp_harness/probe_spike_kawasaki.py`, `probe_dangling.py`, `probe_square_lint.py`
- Modify: `mcp_harness/tests/test_mesh_acquire.py`, `tests/test_square_complete.py`, `tests/test_anatomy_expectation.py`
- Test: `mcp_harness/tests/test_seam_replaced.py` (new)

**Interfaces:**
- Consumes: `mesh_acquire.acquire_mesh`, `mesh_to_tree.auto_mesh_to_metric_tree` (both stay).
- Produces: invariant — `reference_tree_from_query`'s source contains no `auto_mesh_to_metric_tree(` call.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_seam_replaced.py`:

```python
"""The serve path no longer calls the skeletonizer.

reference_tree_from_query is the only production caller of
auto_mesh_to_metric_tree that ever existed (project memory
vlm-mesh-tree-branch-goal). After the 2026-09-11 wiring it calls the VLM gate
instead. This pins that, and pins that the dead query_to_metric_tree seam is
gone."""
import inspect

import mesh_acquire
import server


def test_reference_tree_from_query_does_not_call_the_skeletonizer():
    src = inspect.getsource(server.reference_tree_from_query)
    assert "auto_mesh_to_metric_tree(" not in src
    assert "gated_pipeline.start(" in src


def test_the_dead_query_seam_is_gone():
    assert not hasattr(mesh_acquire, "query_to_metric_tree")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_seam_replaced.py -q`
Expected: the first test passes (Task 1 already did this); the second FAILS — `query_to_metric_tree` still exists.

- [ ] **Step 3a: Delete the dead seam**

In `mcp_harness/mesh_acquire.py`, delete the whole `query_to_metric_tree` function (lines around `1321`–`1330`). Leave `acquire_mesh` and everything else.

- [ ] **Step 3b: Migrate the three probes**

In each of `probe_spike_kawasaki.py`, `probe_dangling.py`, `probe_square_lint.py`, replace the line `res = mesh_acquire.query_to_metric_tree("bear")` with:

```python
    res = mesh_to_tree.auto_mesh_to_metric_tree(mesh_acquire.acquire_mesh("bear"))
```

and ensure each file imports `mesh_to_tree` (add `import mesh_to_tree` next to `import mesh_acquire` if absent — grep each).

- [ ] **Step 3c: Migrate the three tests**

`tests/test_mesh_acquire.py::test_query_to_metric_tree_returns_result` — rewrite to call the two functions directly (the injected gate/compile go to `auto_mesh_to_metric_tree`):

```python
def test_acquire_then_extract_returns_result(tmp_path):
    class _StubGate:
        def predict(self, nodes, pairs):
            return {"verdict": "feasible", "p_pack": 0.9}

    def _stub_compile(nodes, pairs):
        return '{"vertices_coords": []}'

    glb = ma.acquire_mesh("a quadruped", provider=ma.FakeMeshProvider(),
                          provider_name="fake", cache_dir=str(tmp_path))
    res = m2t.auto_mesh_to_metric_tree(glb, gate=_StubGate(), compile_fn=_stub_compile)
    assert isinstance(res, m2t.MeshTreeResult)
    assert res.confirmed is True
    assert len(res.nodes) > 0
```

`tests/test_square_complete.py` (around line 170) — replace:

```python
    res = mesh_acquire.query_to_metric_tree("bear")
```

with:

```python
    import mesh_to_tree
    res = mesh_to_tree.auto_mesh_to_metric_tree(mesh_acquire.acquire_mesh("bear"))
```

`tests/test_anatomy_expectation.py` (the `for fn in (mesh_acquire.query_to_metric_tree, probe_base_eval.build_blob):` loop, around line 524) — drop the deleted function from the tuple so only `build_blob` remains, and update the docstring line naming it:

```python
    import probe_base_eval
    for fn in (probe_base_eval.build_blob,):
        src = inspect.getsource(fn)
        assert "auto_mesh_to_metric_tree(" in src
        assert "reference_count=" not in src, (
            f"{fn.__qualname__} grew an external R -- update this test and "
            "the PR's scope statement together")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_seam_replaced.py tests/test_mesh_acquire.py tests/test_square_complete.py tests/test_anatomy_expectation.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/probe_spike_kawasaki.py mcp_harness/probe_dangling.py mcp_harness/probe_square_lint.py mcp_harness/tests/test_mesh_acquire.py mcp_harness/tests/test_square_complete.py mcp_harness/tests/test_anatomy_expectation.py mcp_harness/tests/test_seam_replaced.py
git commit -m "seam: delete the dead query_to_metric_tree, migrate its users, pin the invariant

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

After all seven tasks:

- [ ] Run the new suites together:
  `cd mcp_harness && PYTHONPATH=.:tests <repo>/.venv/bin/python -m pytest tests/test_reference_gate.py tests/test_resume_reference_tree.py tests/test_agent_loop_gate.py tests/test_anatomy_oracle.py tests/test_seam_replaced.py -q`
- [ ] Run the bridge suite:
  `cd .. && PYTHONPATH=mcp_harness:mcp_harness/tests <repo>/.venv/bin/python -m pytest web/tests/ -q`
- [ ] Run the frontend suite:
  `cd web/frontend && npm test`
- [ ] Confirm no production module outside `mesh_to_tree` calls the skeletonizer on the serve path (Task 7's invariant test covers `reference_tree_from_query`; `test_anatomy_expectation.py`'s tripwire covers the probe).

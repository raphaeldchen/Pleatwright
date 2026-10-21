# Feasibility Gate — Agent Loop Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Tier 2 agent consult the Tier 2.5 feasibility gate before every compile, with the gate auto-trained at startup and degrading gracefully when unavailable.

**Architecture:** Two edits to `mcp_harness/agent_loop.py`: (1) a testable `ensure_gate_trained()` startup helper that trains `feasibility/gate.joblib` from the committed corpus if missing and never crashes the loop; (2) system-prompt additions defining a pre-compile gate stage with a model-driven predict→adjust micro-loop. The `predict_tree_feasibility` MCP tool already exists and is already auto-discovered — no server change.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv`), the existing `feasibility` package (scikit-learn/joblib), pytest. The agent loop uses the Anthropic SDK + `mcp` stdio clients (unchanged).

**Design spec:** `docs/superpowers/specs/2026-06-20-feasibility-gate-agent-wiring-design.md`.

## Global Constraints

- Run everything from `mcp_harness/` with `PYTHONPATH=.:tests` using `./.venv/bin/python`.
- The gate is a **pure accelerator**: the C++ engine stays authoritative; an absent or failed gate must never block the loop or veto a real compile.
- No new dependencies. No change to `server.py`, the gate model, the corpus, or the existing 3-compile cap / auto-nudge / lint logic.
- Gate micro-loop budget = **3** predict→adjust rounds per design, separate from and upstream of the existing 3-compile cap.
- Resolve the gate artifact and corpus paths relative to the module dir (`_HERE`), matching how `agent_loop.py` already pins server paths.

## File Structure

- Modify: `mcp_harness/agent_loop.py` — add `ensure_gate_trained()` (module level), call it in `main()`, and extend `SYSTEM_PROMPT`.
- Create: `mcp_harness/tests/test_gate_startup.py` — unit tests for `ensure_gate_trained()`.

---

### Task 1: `ensure_gate_trained()` startup helper

**Files:**
- Modify: `mcp_harness/agent_loop.py` (add the function near the other module-level helpers, just before `async def main()`)
- Test: `mcp_harness/tests/test_gate_startup.py`

**Interfaces:**
- Consumes: `feasibility.train_model.fit(corpus_path, out_path, ...)` (existing), and the test fixture builder `tests.test_train_model._write_corpus(path)` (existing).
- Produces: `ensure_gate_trained(path: str = <_HERE>/feasibility/gate.joblib, corpus: str = <_HERE>/feasibility/corpus_wide.jsonl) -> bool` — returns True if the artifact exists or was trained; False if training failed. Never raises.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_gate_startup.py`:

```python
"""Unit tests for the agent-loop startup gate helper (no LLM, no MCP)."""
import sys
sys.path.insert(0, "tests")

import os
import agent_loop
from tests.test_train_model import _write_corpus   # reuse the corpus fixture


def test_trains_when_artifact_missing(tmp_path):
    corpus = str(tmp_path / "c.jsonl")
    out = str(tmp_path / "gate.joblib")
    _write_corpus(corpus)
    assert not os.path.exists(out)
    ok = agent_loop.ensure_gate_trained(path=out, corpus=corpus)
    assert ok is True
    assert os.path.exists(out)


def test_noop_when_artifact_exists(tmp_path):
    out = str(tmp_path / "gate.joblib")
    with open(out, "wb") as f:
        f.write(b"sentinel")              # not a real artifact; must not be touched
    ok = agent_loop.ensure_gate_trained(path=out, corpus=str(tmp_path / "missing.jsonl"))
    assert ok is True
    with open(out, "rb") as f:
        assert f.read() == b"sentinel"    # existing artifact left untouched


def test_returns_false_when_training_fails(tmp_path):
    out = str(tmp_path / "gate.joblib")
    # Corpus path does not exist -> fit() raises -> helper must swallow and report.
    ok = agent_loop.ensure_gate_trained(path=out, corpus=str(tmp_path / "nope.jsonl"))
    assert ok is False
    assert not os.path.exists(out)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_gate_startup.py -v`
Expected: FAIL — `AttributeError: module 'agent_loop' has no attribute 'ensure_gate_trained'`.

- [ ] **Step 3: Implement the helper**

In `mcp_harness/agent_loop.py`, add this function immediately before `async def main() -> None:` (it relies on `_HERE`, `os`, and `sys`, all already imported/defined at the top of the file):

```python
def ensure_gate_trained(
    path: str = os.path.join(_HERE, "feasibility", "gate.joblib"),
    corpus: str = os.path.join(_HERE, "feasibility", "corpus_wide.jsonl"),
) -> bool:
    """Make the Tier 2.5 feasibility gate artifact available before the loop runs.

    The artifact is gitignored, so a fresh checkout has none. If it is missing we
    train it from the committed corpus (a RandomForest on ~2000 rows, a couple of
    seconds). The gate is a pure accelerator: if training fails for ANY reason we
    warn and return False so the loop runs gateless rather than crashing. An
    existing artifact is never retrained.
    """
    if os.path.exists(path):
        return True
    try:
        from feasibility import train_model
        train_model.fit(corpus, path)
        return True
    except Exception as exc:  # never let a training problem kill the loop
        print(
            f"[warning] could not train feasibility gate ({exc}); "
            "running without it.",
            file=sys.stderr,
        )
        return False
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_gate_startup.py -v`
Expected: all 3 tests PASS (allow a couple of seconds for the real-train test).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py mcp_harness/tests/test_gate_startup.py
git commit -m "feat(agent): ensure_gate_trained startup helper (auto-train, graceful)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Call the helper at loop startup

**Files:**
- Modify: `mcp_harness/agent_loop.py` (inside `main()`)

**Interfaces:**
- Consumes: `ensure_gate_trained()` from Task 1.
- Produces: no new symbol; `main()` prints a one-line gate status at startup.

- [ ] **Step 1: Wire it into `main()`**

In `mcp_harness/agent_loop.py`, find this line in `main()`:

```python
    client = AsyncAnthropic()
```

Replace it with:

```python
    if ensure_gate_trained():
        print("Feasibility gate ready (Tier 2.5 pre-compile checker).")
    else:
        print("Feasibility gate unavailable; running without it.")

    client = AsyncAnthropic()
```

- [ ] **Step 2: Verify the module still imports and the symbol is wired**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -c "import agent_loop; assert callable(agent_loop.ensure_gate_trained); print('ok')"`
Expected: prints `ok` (no import error).

- [ ] **Step 3: Verify startup trains/loads the real artifact without launching the REPL**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -c "import agent_loop; print(agent_loop.ensure_gate_trained())"`
Expected: prints `True` and `feasibility/gate.joblib` exists afterward (it already exists on this machine, so this is a no-op returning True; on a fresh checkout it would train once).

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py
git commit -m "feat(agent): train/load the feasibility gate at loop startup

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: System-prompt gate stage + cross-reference

**Files:**
- Modify: `mcp_harness/agent_loop.py` (the `SYSTEM_PROMPT` string)

**Interfaces:**
- Consumes: nothing new; documents the already-discovered `predict_tree_feasibility` tool for the model.
- Produces: no code symbol; behavioral change to the agent's drafting loop.

- [ ] **Step 1: Insert the gate section before "TWO WAYS TO COMPILE"**

In `mcp_harness/agent_loop.py`, find this exact line in `SYSTEM_PROMPT`:

```
TWO WAYS TO COMPILE -- PICK ONE, NEVER MIX THEM
```

Replace it with (the new section, a blank line, then the original header):

```
FAST FEASIBILITY GATE -- CHECK BEFORE EVERY COMPILE
Before EACH compile, first call predict_tree_feasibility(tree_nodes, \
symmetric_pairs). This is a fast Tier 2.5 predictor (CLAUDE.md section 6) that \
estimates whether the tree will pack in milliseconds, without running the \
expensive C++ packer. It returns JSON: verdict ('feasible' | 'infeasible' | \
'compile_anyway'), p_pack, ood, reason. Act on the verdict:
  - feasible / compile_anyway -> compile now. 'compile_anyway' means the tree is \
novel / out-of-distribution: the gate cannot judge it, so let the engine decide. \
NEVER skip a compile_anyway.
  - infeasible -> do NOT compile yet. Adjust the tree and re-check the gate. This \
is the ONE stage where tweaking edge LENGTHS is the correct cheap first move: the \
backend has NOT auto-nudged yet, so shrinking/rebalancing genuinely helps here \
(the opposite of a post-compile ERROR). You may instead restructure topology \
toward a known-good template when the reason string or the tree's shape points \
that way -- the lever choice is YOUR judgment per case.
  - a result beginning "ERROR: ... not trained" means the gate is unavailable: \
compile directly and do not retry the gate.
GATE BUDGET: at most 3 predict->adjust rounds per design. If still 'infeasible' \
after 3 rounds, compile your best candidate ANYWAY -- the C++ engine is \
authoritative and a fast predictor must NEVER veto a real attempt. This budget is \
separate from and upstream of the 3-compile cap described under ERROR HANDLING.

TWO WAYS TO COMPILE -- PICK ONE, NEVER MIX THEM
```

- [ ] **Step 2: Add the cross-reference in ERROR HANDLING**

In `mcp_harness/agent_loop.py`, find this exact sentence in `SYSTEM_PROMPT`:

```
packing error by only tweaking numbers.
```

Replace it with:

```
packing error by only tweaking numbers. (Pre-compile, the feasibility gate is \
the stage where length tweaks DO belong -- see FAST FEASIBILITY GATE above; this \
post-compile rule is strictly about ERRORs returned by a compile.)
```

- [ ] **Step 3: Verify the prompt still parses and contains the new section**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -c "import agent_loop; p=agent_loop.SYSTEM_PROMPT; assert 'FAST FEASIBILITY GATE' in p; assert 'GATE BUDGET' in p; assert p.count('TWO WAYS TO COMPILE') == 1; print('ok')"`
Expected: prints `ok` (the module imports, the gate section is present, and the original header was not duplicated).

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py
git commit -m "feat(agent): teach the prompt to gate-check before every compile

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full regression + manual smoke documentation

**Files:**
- Modify: `docs/superpowers/plans/2026-06-20-feasibility-gate-agent-wiring.md` (record the manual smoke result below)

**Interfaces:**
- Consumes: all prior tasks.
- Produces: a verified, green tree and a documented manual smoke check.

- [ ] **Step 1: Run the new unit tests**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_gate_startup.py -v`
Expected: all 3 PASS.

- [ ] **Step 2: Run the full suite to confirm no regressions**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest -q`
Expected: all tests PASS (the prior baseline was 79 passed; this adds 3 → expect 82 passed). The run takes ~3 minutes because engine-backed tests invoke the real C++/Java backends.

- [ ] **Step 3: Manual smoke check (requires `ANTHROPIC_API_KEY`)**

This verifies the model-driven behavior that unit tests can't cover. Run:

```bash
cd mcp_harness && PYTHONUTF8=1 ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY ./.venv/bin/python agent_loop.py
```

At the `you>` prompt, type: `design a quadruped (four legs, head, tail)`.
Confirm in the transcript:
  1. Startup printed `Feasibility gate ready ...`.
  2. A `[tool] predict_tree_feasibility(...)` call appears BEFORE the first compile tool call.
  3. The design proceeds to compile and lint as before.
Then type a deliberately over-heavy request, e.g. `design a creature with ten long legs all on the body`, and confirm at least one `predict_tree_feasibility` -> adjust -> `predict_tree_feasibility` round happens before any compile (or, if the gate is OOD/feasible, that it compiles and the existing handling takes over). Type `exit` to quit.

If `ANTHROPIC_API_KEY` is not available, record this step as "skipped (no API key)".

- [ ] **Step 4: Record the smoke result**

Edit this plan file, replacing the line below with the observed outcome:

`Manual smoke result (Step 3): skipped (no API key / non-interactive) — ANTHROPIC_API_KEY is present in environment but agent_loop.py requires an interactive REPL (you> prompt) which is not available in this automated execution context. Full suite: 82 passed (3 new gate-startup tests + 79 prior baseline), 0 failures, 0 errors (184.54s).`

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add docs/superpowers/plans/2026-06-20-feasibility-gate-agent-wiring.md
git commit -m "docs(agent): record feasibility-gate wiring smoke check

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** startup auto-train + graceful failure (Task 1, helper; Task 2, wiring) — spec §3.1; prompt gate stage with verdict semantics, pre-compile-length carve-out, 3-round budget, compile-anyway fallback, not-trained skip (Task 3) — spec §3.2 + §4; ERROR-HANDLING cross-reference (Task 3 Step 2) — spec §3.2; `ensure_gate_trained` unit tests for the three branches (Task 1) — spec §6; full-suite regression + manual smoke (Task 4) — spec §6. `server.py` unchanged — spec §3.3. No model/corpus/budget-plumbing changes — spec §7.
- **Placeholder scan:** the only fill-in is the runtime smoke result pasted in Task 4 Step 4 (a genuine runtime observation), consistent with the No-Placeholders rule for runtime values.
- **Type consistency:** `ensure_gate_trained(path, corpus) -> bool` is defined in Task 1 and called with no args in Task 2 and with keyword args in the Task 1 tests; signature matches across all references. `train_model.fit(corpus, path)` matches the existing `fit(corpus_path, out_path, ...)` positional order. `predict_tree_feasibility(tree_nodes, symmetric_pairs)` matches the tool signature in `server.py`.
- **Budget consistency:** gate budget = 3 rounds (Task 3) is stated as separate from the existing 3-compile cap everywhere it appears.

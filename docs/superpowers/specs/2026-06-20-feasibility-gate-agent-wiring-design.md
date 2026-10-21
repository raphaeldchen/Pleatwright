# Feasibility Gate — Agent Loop Wiring (Design Spec)

**Date:** 2026-06-20
**Status:** Approved (brainstorming) — ready for implementation plan
**Component:** Tier 2 orchestrator (`mcp_harness/agent_loop.py`)
**Depends on:** the trained Tier 2.5 gate (`feasibility/gate.py`, `train_model.py`, `predict_tree_feasibility` MCP tool) — already merged to `main`.

## 1. Goal

Wire the existing Tier 2.5 feasibility gate (CLAUDE.md §6) into the agent's
drafting loop so the agent consults `predict_tree_feasibility` **before every
compile** and adjusts cheap, near-certain-failure trees in milliseconds instead
of paying for a C++ packer run that will fail. The gate is a **pure
accelerator**: it may skip near-certain-failure compiles, but the C++ engine
stays authoritative for every real attempt, and an absent or broken gate never
blocks the existing flow.

## 2. Background / current state

- `predict_tree_feasibility(tree_nodes, symmetric_pairs)` already exists in
  `server.py`, returns JSON `{verdict, p_pack, ood, ood_score, reason}` where
  `verdict ∈ {feasible, infeasible, compile_anyway}`, and returns
  `ERROR: feasibility gate not trained (...)` when the artifact is missing.
- `agent_loop.py` discovers MCP tools **dynamically** (`connect_servers` lists
  every `@mcp.tool()`), so the gate tool is *already* in the agent's toolset.
  It is unused only because the system prompt never mentions it.
- The gate artifact `feasibility/gate.joblib` is **gitignored**, so it is absent
  on a fresh checkout; the committed `feasibility/corpus_wide.jsonl` (2000 labeled
  trees) is the training source.

Therefore "wiring" is two things: **(a)** system-prompt instructions that define
the gate stage and the predict→adjust micro-loop, and **(b)** a small startup
hook that makes the artifact available and degrades gracefully when it is not.
No change to `server.py`, the gate model, or the corpus.

## 3. Components

Two files change; no new modules.

### 3.1 `mcp_harness/agent_loop.py` — startup hook

Add a testable helper and call it from `main()` before `connect_servers`:

```
ensure_gate_trained(path="feasibility/gate.joblib",
                    corpus="feasibility/corpus_wide.jsonl") -> bool
```

Behavior:
- If `path` already exists → no-op, return True (do **not** retrain).
- If `path` is missing → call `feasibility.train_model.fit(corpus, path)` to
  produce it (RandomForest on 2000 rows ≈ a couple of seconds), return True.
- If training raises for any reason → catch, print a warning, return False.
  The loop continues; the agent runs gateless (the tool will return
  `not trained`, which the prompt handles).

`main()` calls it once at startup and prints a one-line status
(`gate ready` / `gate unavailable, running without it`).

### 3.2 `mcp_harness/agent_loop.py` — system prompt

Insert a new **"FAST FEASIBILITY GATE — CHECK BEFORE EVERY COMPILE"** section
immediately **before** the existing "TWO WAYS TO COMPILE" section (the gate fires
before any compile). Content:

- Call `predict_tree_feasibility(tree_nodes, symmetric_pairs)` before each
  compile. It returns JSON with `verdict`, `p_pack`, `ood`, `reason`.
- **feasible** / **compile_anyway** → compile now. `compile_anyway` means the
  tree is novel / out-of-distribution; the gate can't judge it, so the engine
  decides — never skip it.
- **infeasible** → do NOT compile yet. Adjust and re-check the gate. This is the
  ONE stage where tweaking edge LENGTHS is the correct cheap first move, because
  the backend has not auto-nudged yet (the opposite of the post-compile ERROR
  rule). The agent may instead restructure topology toward a known-good template
  when the `reason` or tree shape points that way — the lever choice is the
  agent's judgment per case.
- **ERROR: ... not trained** → the gate is unavailable; compile directly and do
  not retry the gate.
- **GATE BUDGET:** at most **3** predict→adjust rounds per design. If still
  `infeasible` after 3, compile the best candidate ANYWAY — the engine is
  authoritative and a fast predictor must never veto a real attempt. This budget
  is separate from and upstream of the existing 3-compile cap.

Also add a one-clause cross-reference inside the existing **ERROR HANDLING**
section so the pre/post-compile length rules don't read as contradictory:
*"(Pre-compile, the feasibility gate is where length tweaks belong — see FAST
FEASIBILITY GATE. This rule is about post-compile ERRORs.)"*

### 3.3 `mcp_harness/server.py` — no change

The tool already exists, is already discovered, and already degrades to
`ERROR: ... not trained`.

## 4. Data flow

```
draft tree (from template)
   │
   ▼
predict_tree_feasibility(tree_nodes, symmetric_pairs)   ◄─┐ gate micro-loop
   │                                                      │ (max 3 iterations)
   ├─ "feasible"        → compile                         │
   ├─ "compile_anyway"  → compile  (OOD: novel tree)      │
   ├─ "infeasible"      → adjust (agent picks lever) ──────┘
   │        └─ after 3 infeasible verdicts → compile best candidate anyway
   └─ ERROR "not trained" → skip gate, compile directly
   │
   ▼
compile  ── existing 3-compile cap + auto-nudge + error handling UNCHANGED ──
   │
   ▼
validate_flat_foldability  ── existing lint / free-paper logic UNCHANGED ──
```

**Two independent budgets:**
- **Gate budget** — ≤3 predict→adjust rounds per design attempt, all pre-compile
  (milliseconds, no engine).
- **Compile budget** — the existing ≤3 real compiles, unchanged. The gate sits
  upstream and is purely additive.

## 5. Error handling

All paths degrade toward "run gateless," never crash the loop:

| Condition | Behavior |
|---|---|
| Training fails at startup | Caught; warning printed; loop runs without the gate |
| Tool returns `not trained` mid-run | Prompt: agent compiles directly, no gate retry |
| Gate predicts a false `infeasible` | Bounded by the 3-iteration cap → compiles anyway; engine corrects |
| Malformed tree passed to gate | Tool already validates and returns an `ERROR:` string; agent skips to compile |

## 6. Testing

The full agent loop is a live LLM + subprocess REPL and is not unit-tested; we
test the deterministic parts and verify the model-driven parts manually.

- **Unit (automated):** tests for `ensure_gate_trained` in `tmp_path`:
  (a) missing artifact → trains, file appears, returns True;
  (b) existing artifact → no-op (not retrained; mtime unchanged), returns True;
  (c) training raises (e.g. bad corpus path) → returns False, does not propagate.
- **Existing suite:** all current tests (incl. `test_predict_tool.py`) stay
  green — the tool contract is unchanged.
- **Manual smoke (documented, not CI; gated behind `ANTHROPIC_API_KEY`):** run
  `agent_loop.py`, request a quadruped, confirm the transcript shows
  `predict_tree_feasibility` firing before the compile, and an `infeasible→adjust`
  round on a deliberately over-heavy tree.

## 7. Out of scope (YAGNI)

- No production retrain / telemetry loop; no logging of gate verdicts to disk for
  corpus growth.
- No changes to the gate model, features, or the corpus.
- No hard-coded Python micro-loop — the predict→adjust loop is model-driven via
  the system prompt, consistent with the existing loop architecture.

## 8. Success criteria

- A fresh checkout: launching `agent_loop.py` auto-trains the gate (or warns and
  runs gateless if training fails).
- The agent calls `predict_tree_feasibility` before compiling, and on a
  predicted-infeasible tree it adjusts and re-checks (≤3 rounds) before any
  compile, then compiles anyway if still infeasible.
- All existing tests pass; new `ensure_gate_trained` tests pass.

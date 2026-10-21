# Gate wiring and seam replacement — design

**Date:** 2026-09-11
**Branch:** `claude/vlm-mesh-to-tree-pipeline`
**Builds on:** `2026-09-10-s5-human-gate-design.md` (S5: `gated_pipeline.start/resume`)

## 1. Goal

Make the VLM pipeline with the human gate the production mesh→tree step.
After this work, every creature request flows

    prompt → mesh → VLM tree → HUMAN GATE → compile → lint → simulate

and `mesh_to_tree.auto_mesh_to_metric_tree` (the skeletonizer) is no longer on
the serve path.

## 2. What the main pipeline is today (traced, not recalled)

    React chat → web/server.py (websocket) → agent_loop (LLM + MCP tools)
      → agent's FIRST action on a creature request:
        reference_tree_from_query(prompt)                       server.py:4162
          → mesh_acquire.acquire_mesh(prompt)   text → .glb    :4199   (stays)
          → mesh_to_tree.auto_mesh_to_metric_tree(glb)          :4211   (REPLACED)
          → returns a text REFERENCE REPORT (candidate tree + prose)
      → agent applies "semantic corrections"
      → draft_and_compile_full_base → validate_flat_foldability → fold → viewport

Two corrections to project memory: `mesh_acquire.query_to_metric_tree` has
**no production callers** (`server.py:4199` calls `acquire_mesh` directly), so
there is one seam, not two. And `web/server.py:246` keys the `[ANATOMY]`
oracle on `reference_tree_from_query`'s output, so that tool's name and report
shape are load-bearing downstream.

## 3. Constraints the runtime imposes

* MCP tools run in a **spawned subprocess** (`agent_loop.py:178`;
  `session.call_tool` at `:646`). A tool cannot block on a websocket answer.
  The pause must be a return value — which is what S5 built.
* The model must never see its own rendered tree figure (measured: MAE 0.53
  vs 0.29 for no self-review). `render_tree_sheet` stays out of
  `agent_loop.IMAGE_RESULT_TOOLS`.
* Anatomy outranks packability. Nothing compiles that a human did not
  approve, and the human approves the tree that is actually compiled.
* `MAX_REVISIONS = 3` is S5's and is not re-implemented here.

## 4. Decisions (owner-settled 2026-09-11)

| question | decision |
|---|---|
| who receives the verdict and calls `resume()` | **the web bridge**; the agent is never in the loop |
| what the agent may change after approval | **nothing** — compile the approved tree unchanged; packing rescues run inside the compile path and change no proportions |
| the skeletonizer on failure | **removed from the serve path entirely**; no automatic fallback, no flag; templates remain the agent's last resort as today |
| how the turn is stopped and restarted | **interrupt in the loop** (§5) — the stop is in `agent_loop` code, not the prompt |

Rejected: prompt-level "end your turn now" (a promise the model can break —
the pattern S5 §2 declined); gating before the agent (airtight, but the
bridge would have to classify creature-vs-follow-up prompts itself, which is
the agent's judgement today).

## 5. Architecture

    user prompt ──► web bridge ──► agent turn
                                      │
                                      ▼
                       reference_tree_from_query(prompt)         [MCP tool, server.py subprocess]
                         ├─ acquire_mesh(prompt)      → .glb      (unchanged)
                         ├─ gated_pipeline.start(glb) → state     (VLM authors, packs, draws)
                         └─ returns state JSON, status=awaiting_review, "__gate__": true
                                      │
            agent_loop.agent_turn sees "__gate__" IN CODE → returns GATE_PENDING.
            The tool_use block stays in `messages`; NO tool_result is appended.
            The model never receives this result.
                                      │
                                      ▼
                    web bridge: conn["gate"] = state
                      ├─ sends {type:"review", sheet_png:<base64>, summary, round, remaining}
                      │                                    ▼
                      │                       React ReviewPanel: figure + summary
                      │                       [Approve]   [feedback ▭ Revise]
                      │                                    │
                      ◄── {type:"review_answer", verdict, feedback} ──┘
                      ├─ calls resume_reference_tree(state, verdict, feedback)
                      │       via state.backend — a tool the AGENT IS NEVER OFFERED
                      ├─ awaiting_review → another review frame (≤ 3 rounds)
                      └─ approved → append the REFERENCE REPORT as the pending
                                    tool call's tool_result; restart the agent turn.
                                      │
                                      ▼
            agent sees reference_tree_from_query "returned" an approved tree.
            System prompt: compile it UNCHANGED → draft_and_compile_full_base → lint → fold.

Guaranteed by construction, not by prompt: the model never sees the figure or
the summary; nothing compiles that a human did not approve; the agent keeps
deciding *whether* a prompt is a creature request (the gate fires only when it
calls the tool).

**State.** The plain JSON dict S5 produces. Lives in `conn["gate"]` on the
bridge for the duration of one review and is handed back to
`resume_reference_tree` on every answer. No server-side session. The sheet is
a PNG path on the server subprocess's disk (same machine); the bridge reads
the bytes and ships base64.

## 6. Components

**6.1 `server.reference_tree_from_query` (modify, `server.py:4162`).** Keeps
its name and its acquire-a-mesh half. The extract half becomes
`gated_pipeline.start(glb, client=<from env>, out_dir=<per-call temp dir>)`.
Returns the state JSON with `"__gate__": true` when `awaiting_review`. On
`failed` returns `ERROR: <state note>` (the note names the cause — S5 I2/I5)
so the agent's existing template fallback applies unchanged.

**6.2 `server.resume_reference_tree(state, verdict, feedback)` (new MCP
tool).** Wrapper over `gated_pipeline.resume`, with one extra verdict of its
own: `verdict == "compile_anyway"` on an `exhausted` state. S5's `resume()`
**refuses** `approve` from `exhausted` (its I3 guard) and that guard stays;
`compile_anyway` is handled here, not there — it takes `state["tree"]` as
approved and marks the report `[human-approved round N after an unmet
critique]`. Any other verdict on a terminal state propagates S5's
`ValueError` as an `ERROR:` string. Registered so the bridge can call it
through the backend session; **filtered out of the tool list the agent is
offered** (§6.3). On approval (either kind) it stashes the approved tree's
leaf labels the way the old report did (`server.py:4172`, "SIDE EFFECT
WORTH KNOWING") so `read_base` attaches them to the served base.

**6.3 `agent_loop.agent_turn` (modify).** After each tool result: if the
output parses as JSON with `"__gate__": true`, return a new outcome
`GATE_PENDING` carrying the state, ending the turn **without** appending a
`tool_result`. `resume_reference_tree` is excluded from the tools offered to
the model. The system-prompt paragraph at `agent_loop.py:205-223` changes from
"semantic correction only" to: the returned tree's anatomy was approved by the
user; pass it to `draft_and_compile_full_base` **unchanged**; if you believe
the anatomy is wrong, say so to the user instead of editing it.

**6.4 `web/server.py` review loop (modify).**
* On `GATE_PENDING`: `conn["gate"] = state`; read `state["sheet_png"]`; send
  `{type:"review", sheet_png, summary, round, remaining, exhausted:false}`.
  Disable turn starts: a `user` frame while `conn["gate"]` is set is answered
  with an `error` frame and dropped.
* On `{type:"review_answer", verdict, feedback}`: call
  `resume_reference_tree` via `state.backend`.
  * `awaiting_review` → another `review` frame.
  * `approved` → build the REFERENCE REPORT text: the leaf names, the pairs,
    S5's summary verbatim, and one marker line `[human-approved round N]`;
    append it as the pending tool call's `tool_result`; clear `conn["gate"]`;
    restart the agent turn (`run_agent_turn`).
  * `exhausted` → `{type:"review", …, exhausted:true}`; the panel offers
    **Compile anyway** (send `review_answer` with `verdict:"compile_anyway"`;
    §6.2 handles it and the report's marker line becomes
    `[human-approved round N after an unmet critique]`) or **Start over**
    (bridge appends `tool_result` `ERROR: the user abandoned the review`,
    clears the gate, restarts the turn so the agent's existing fallback
    applies).
  * `failed` (a revision that produced no tree) → `review` frame with the
    note; panel offers **Revise again** or **Start over**. S5 already
    refuses `approve` from `failed`.
* `anatomy_oracle.decide` gains one stand-down: when `report_text` carries
  the `[human-approved` marker, return `fire:false,
  reason:"human-approved"`. Under "compile unchanged" there is no agent edit
  for the oracle to catch; it stands down explicitly, never silently.

**6.5 `web/frontend` ReviewPanel (new, React).** Renders on a `review` frame:
the four-view figure, the summary text verbatim (S5 §6 decided what it
contains), **Approve**, a feedback textarea with **Revise** (disabled when
`remaining == 0`). On `exhausted:true`: **Compile anyway** / **Start over**.
On a `failed` note: **Revise again** / **Start over**. Chat input is disabled
while a review is open. Sends `review_answer`.

**Unchanged:** `draft_and_compile_full_base`, the rescue ladder, the linter,
the viewport, `get_template`, the shaping and pose contracts.

## 7. Failure paths

| outcome | what happens |
|---|---|
| `approved` | tree → tool result → agent compiles it unchanged |
| `awaiting_review` ×≤3 | another review frame; `remaining` 3 → 0 |
| `exhausted` | Compile anyway (defects disclosed in the report) or Start over |
| `failed` from `start()` | tool returns `ERROR: <note>`; existing fallback |
| `failed` from a revision | prior tree kept (S5); Revise again or Start over |
| disconnect mid-review | `conn` dies with the socket, like all per-connection state; nothing was compiled |
| second user message during a review | frontend disables input; bridge refuses with an `error` frame |

## 8. Invariants, each with a test

1. No `tool_result` for `reference_tree_from_query` reaches `messages` unless
   the state is `approved` or the output is an `ERROR:` string.
2. `resume_reference_tree` is absent from the tool list the agent is offered.
3. `sheet_png` bytes appear only in `review` frames; never in `messages`.
4. The bridge never constructs a gate state, only forwards one.
5. No production module outside `mesh_to_tree` calls
   `auto_mesh_to_metric_tree`.

## 9. The seam replacement

After §6 lands, `server.py:4211` no longer calls `auto_mesh_to_metric_tree`.
That was the only production call. `mesh_acquire.query_to_metric_tree` has no
production callers and is **deleted**. `mesh_to_tree.auto_mesh_to_metric_tree`
stays importable — ~70 probes and tests use it and its own suite keeps
running — but nothing on the serve path imports it.

`MESH_PROVIDER=fake` still works (fixture mesh → VLM → gate); offline tests
inject the VLM client exactly as S5's tests do.

Deliberately **not** done: no feature flag between old and new (a flag keeps
the old path alive and untested in production); no concept-image approval
step from CLAUDE.md §5 Step 1 (never built; out of scope).

## 10. Testing

All offline: injected VLM client, `fake` mesh provider, stub `pack_fn` where
the C++ is not the thing under test.

| unit | pins |
|---|---|
| `reference_tree_from_query` | `awaiting_review` → `__gate__` state; `failed` → `ERROR:` with the cause |
| `resume_reference_tree` | approved → labels stashed; `compile_anyway` on `exhausted` → approved report with the unmet-critique marker; `approve` on `exhausted` → `ERROR:` (S5's guard intact) |
| `agent_turn` | `__gate__` → `GATE_PENDING`, `tool_use` present, **no** `tool_result`; ordinary results still append. **Mutation-checked:** remove the sentinel check → the model receives the state |
| tool filtering | offered list has `reference_tree_from_query`, not `resume_reference_tree` |
| bridge loop | frame sequences: approve-first; revise-then-approve; exhaust→compile-anyway; exhaust→start-over; revision-failed→revise-again; disconnect; user frame during review refused. Sheet bytes only in `review` frames |
| ReviewPanel | `review` frame renders figure + both actions; Revise disabled at `remaining==0`; `review_answer` shape |
| anatomy oracle | stands down `human-approved` on a marked report; unmarked unchanged |
| seam | invariant 5 as a test |
| end to end | fake provider + injected client: prompt → review → approve → `fold` frame, no network |

Every test whose fixture could make two branches agree must be shown to fail
against an injected defect (S5 shipped six blind tests of exactly that
shape).

## 11. Prior art (CLAUDE.md §0)

**Adapted.** The chosen pattern — end the turn in code on a sentinel, let an
out-of-band controller resolve it, resume with the resolution as the tool's
result — is LangGraph's `interrupt()` / `Command(resume=…)`, and is how
Claude Code's own permission prompts work: the model's `tool_use` stays in
the transcript, the human answers outside the model loop, the `tool_result`
is filled in afterwards. Adopted directly, including the rule that the
interrupted call's result is the *only* thing the model ever sees.

**Rejected.** OpenAI Agents SDK approval-by-tool-flag: the approval is a
prompt-visible tool result the model reasons about, so the model would read
its own summary. This repo's own suggest-then-confirm contracts (shaping,
region fills, pose; `agent_loop.py:417-526`): prompt-level, which S5 §2
already declined for the gate. "Compile unchanged" follows CADSmith's
separation of an approved intermediate representation from the compile step.

## 12. Out of scope

Provider bake-off (owner deferred it). Concept-image approval. Persisting a
review across reconnects. Any change to `gated_pipeline` itself beyond what
a test reveals.

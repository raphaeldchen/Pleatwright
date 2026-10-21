# Web UI — Thin Vertical Slice (prompt → streamed agent → `.fold`)

**Date:** 2026-06-26
**Status:** Design approved, ready for implementation plan
**Branch (suggested):** `feat/web-ui-thin-slice`

## 1. Goal & Scope

Ship the **first browser-facing slice** of the AI-Driven Origami IDE: a web page
where a user types a prompt, watches the agent work in real time, and receives
the final `.fold` file (viewable as pretty-printed JSON + downloadable).

This replaces the terminal REPL as the primary way to drive the agent, and
becomes the foundation every later pane (WebGL viewport, concept-art board,
metric-tree view) plugs into.

### Deployment direction
**Local-first now, desktop later.** The slice is a localhost FastAPI server +
browser UI — the exact artifact that can later be wrapped in Tauri/Electron
(desktop) without re-architecture. The bring-your-own-key `.env` model
(`mcp_harness/env_config.py`) is the spine: the user supplies their own LLM key,
so there is zero server-side inference cost or secret storage. Hosted-SaaS is
explicitly *not* designed for here (it would add inference cost, secret
management, and prompt sandboxing — deferred).

### Non-goals (YAGNI — each is a later slice)
- WebGL Origami Simulator viewport / 3D fold animation
- Concept-art board (image generation isn't wired into the agent yet)
- Metric-tree "stick figure" visualization
- Multi-session, persistence, auth, multi-tenant isolation
- Tauri/Electron packaging

## 2. Architecture

```
┌─────────────── Browser (React + Vite + TypeScript) ───────────────┐
│  Chat pane:   prompt box + streaming transcript                    │
│  Result pane: pretty-printed .fold JSON + Download button          │
└───────────────┬───────────────────────────────────────────────────┘
                │  WebSocket (JSON frames)
┌───────────────▼─── FastAPI bridge (new: web/server.py) ────────────┐
│  • on startup: connect_servers() + LLMClient.from_env()            │
│  • per WS connection: holds a `messages` list (one session)        │
│  • per prompt: runs ONE agent turn, forwards each event as a frame │
└───────────────┬───────────────────────────────────────────────────┘
                │  in-process async calls
┌───────────────▼─── existing agent core (mcp_harness/agent_loop.py)─┐
│  agent_turn() → LLM tool-loop → MCP servers (TreeMaker, Oriedita)  │
│  over stdio → returns assistant text + tool results                │
└────────────────────────────────────────────────────────────────────┘
```

### 2.1 The core refactor: print → event-sink (dependency inversion)
`agent_turn()` in `mcp_harness/agent_loop.py` currently emits all progress via
`print()` directly to stdout (assistant text, `[tool] name(args)`, `[<-]`
results). A web server cannot intercept `print`.

**Change:** `agent_turn` emits **structured events to an injected sink** instead
of printing. The sink is a callable `emit(event: dict) -> None` (or `agent_turn`
becomes an async generator yielding events — to be settled in the plan; the
callback form is preferred for minimal churn).

- The existing **CLI** (`agent_loop.main`) supplies a sink that formats events
  back to `print()` — the terminal REPL behaves identically.
- The **WebSocket handler** supplies a sink that serializes each event to a JSON
  frame and sends it over the socket.

This keeps a single agent-core code path; the terminal app and browser app are
two sinks over the same engine. No agent logic is duplicated.

### 2.2 File layout
- `web/server.py` — FastAPI app: startup wiring, `GET /` (serve built
  frontend), `WS /ws/chat`, `GET /download/fold` (or fold delivered inline —
  see §4).
- `web/frontend/` — Vite + React + TS. Dev server proxies to FastAPI;
  `npm run build` emits static files FastAPI serves in production/desktop.
- `mcp_harness/agent_loop.py` — refactor `agent_turn` to emit to a sink; CLI
  keeps a print-sink adapter.
- New Python deps: `fastapi`, `uvicorn`, `websockets` (added to the project's
  install step; not required by the existing offline suite).

## 3. WebSocket Protocol

**Client → server:**
```json
{ "type": "prompt", "text": "Design a five-pointed star base" }
```

**Server → client** (event-sink types, streamed in order):

| `type`        | payload                          | UI effect                                   |
|---------------|----------------------------------|---------------------------------------------|
| `assistant`   | `{text}`                         | append assistant text to transcript         |
| `tool_call`   | `{name, args_preview}`           | show `⚙ compile_treemaker_math(...)`        |
| `tool_result` | `{name, preview, is_error}`      | show result; red line if `is_error`         |
| `fold`        | `{filename, json}`               | populate result pane + enable Download      |
| `turn_end`    | `{ok}`                           | re-enable the prompt box                    |
| `error`       | `{message}`                      | banner; re-enable prompt box                |

## 4. `.fold` Artifact Capture

The bridge inspects each `tool_result` as it streams. A FOLD document is JSON
with a top-level `"file_spec"` key — a reliable, **content-based** signal. When a
tool result parses as such, the bridge keeps it as the turn's **fold artifact**
and emits a `fold` frame.

- **Content-sniff, not tool-name match:** `generate_fold_file`, `compile_base`,
  and `draft_and_compile_full_base` can all emit FOLD; keying on the
  `"file_spec"` key stays correct as tools are renamed/added (same robustness as
  dynamic MCP tool discovery).
- **Last valid `.fold` wins:** perturb-and-retry can produce several compiles per
  turn; the most recent valid FOLD is the artifact.
- **Delivery:** the `fold` frame carries the JSON inline (so the result pane can
  pretty-print it without a second request). Download is a client-side blob saved
  as `model.fold` (`application/json`). A server `GET /download/fold` route is
  optional and only added if inline delivery proves awkward.

## 5. Error Handling

- **No/invalid API key or `LLM_PROVIDER`:** `LLMClient.from_env()` raises at
  startup. FastAPI logs a clear message; `GET /` serves a "backend not configured
  — set your key in `.env`" page rather than crashing.
- **Tool errors are normal signals, not crashes:** `ERROR: circles overlap`,
  lint failures, etc. stream as `tool_result{is_error:true}`; the agent continues
  its perturb/retry loop. They render inline and do **not** end the turn.
- **Engine crash / exception mid-turn:** caught at the turn boundary (mirrors the
  REPL's `[loop error]`), emitted as one `error` frame; the socket stays open for
  the next prompt.
- **Single-user/local assumption:** one shared `Backend` (MCP servers +
  subprocess-per-compile). Turns are serialized — one compile at a time. No
  multi-tenant isolation (a deferred hosting concern).

## 6. Testing

- **Agent core (unit):** `agent_turn` emits the correct event sequence into a
  **fake list-sink** (no stdout, no network). Locks the refactor and proves CLI
  parity.
- **Bridge (unit/integration):** FastAPI `TestClient` WebSocket test with a
  **stubbed agent core** (fake event stream including a `.fold`). Asserts frames
  arrive in order, the fold artifact is captured, and it is downloadable. No LLM,
  no C++ — deterministic, fits the existing offline suite.
- **Frontend (Vitest/component):** feed mock frames; assert transcript, result
  pane, and Download render correctly. Kept light.
- **Manual smoke (opt-in, not CI):** real Groq key + real prompt → real `.fold`,
  documented like the project's other live smokes.

## 7. Success Criteria

1. `npm run build` + start FastAPI → open `localhost`, type a prompt, watch the
   agent's text/tool/error events stream live, and receive a final `.fold` that
   pretty-prints and downloads as a valid FOLD file.
2. The terminal REPL (`agent_loop.main`) still works unchanged (print-sink).
3. Offline test suite stays green; new bridge/core tests pass without network or
   the C++ engine.

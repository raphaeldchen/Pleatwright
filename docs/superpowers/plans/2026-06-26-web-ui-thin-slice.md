# Web UI Thin Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A localhost web app where a user types a prompt, watches the agent stream its progress, and receives the final `.fold` file (pretty-printed + downloadable).

**Architecture:** Refactor the agent core's `agent_turn` from `print()` to an injected event sink (dependency inversion), so the existing terminal REPL and a new FastAPI WebSocket bridge are two sinks over one engine. A React/Vite/TS frontend sends prompts over a WebSocket and renders streamed event frames; the bridge content-sniffs tool results for FOLD documents and forwards them as a downloadable artifact.

**Tech Stack:** Python · FastAPI · uvicorn · WebSocket · React · Vite · TypeScript · Vitest

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-26-web-ui-thin-slice-design.md`
- Local-first; bring-your-own-key via `mcp_harness/env_config.py` + `.env`. No server-side secrets, no hosting concerns.
- The terminal REPL (`agent_loop.main`) MUST keep working unchanged after the refactor (print-sink adapter).
- The existing offline test suite MUST stay green; new tests run with NO network and NO C++ engine (stub/fake the agent core and tools).
- FOLD documents are detected by content: a JSON object with a top-level `"file_spec"` key. Never key on tool name.
- Single-user/local: one shared `Backend`, turns serialized. No auth, no persistence, no multi-tenant isolation.
- Non-goals (do NOT build): WebGL viewport, concept-art board, metric-tree view, Tauri packaging.
- Python web deps live in `web/requirements.txt`; install with `mcp_harness/.venv/bin/pip install -r web/requirements.txt`.
- Run tests with `mcp_harness/.venv/bin/python -m pytest`. Frontend tests with `npm test` inside `web/frontend`.

---

### Task 1: Refactor `agent_turn` to an injected event sink

Invert `agent_turn`'s output dependency: instead of calling `print()`, it calls an `emit(event: dict)` callback. A module-level `_print_sink` reproduces the current terminal output, and `agent_turn` defaults to it so the CLI is unchanged. The web bridge (Task 3) supplies its own sink.

**Files:**
- Modify: `mcp_harness/agent_loop.py` (the `agent_turn` function at lines 340-406; add `_print_sink` near `_preview` at ~469)
- Test: `mcp_harness/tests/test_agent_turn_events.py` (create)

**Interfaces:**
- Produces:
  - `agent_turn(client, backend, messages: list[dict], emit: Callable[[dict], None] | None = None) -> None` — `emit` defaults to `_print_sink`.
  - Event dicts emitted, in order:
    - `{"type": "assistant", "text": str}` (only when assistant text is non-empty)
    - `{"type": "tool_call", "name": str, "args_preview": str}`
    - `{"type": "tool_result", "name": str, "output": str, "is_error": bool}` (`output` is the FULL tool text, not truncated)
    - `{"type": "notice", "text": str}` (the MAX_AGENT_STEPS stop message)
  - `_print_sink(event: dict) -> None` — formats events to stdout exactly as the old prints did.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_agent_turn_events.py`:

```python
"""agent_turn must emit structured events to an injected sink (CLI parity).

No pytest-asyncio in this project, so we drive the coroutine with asyncio.run().
"""
import asyncio
import json
from types import SimpleNamespace

import agent_loop


def _tool_call(call_id, name, arguments):
    return SimpleNamespace(
        id=call_id,
        function=SimpleNamespace(name=name, arguments=arguments),
    )


class FakeClient:
    """Returns canned run_turn results: first a tool call, then a final answer."""

    def __init__(self, results):
        self._results = list(results)
        self.cfg = SimpleNamespace(provider="fake", model="fake")

    async def run_turn(self, system, messages, tools):
        return self._results.pop(0)


def test_agent_turn_emits_event_sequence(monkeypatch):
    fold_json = '{"file_spec": 1.1, "vertices_coords": [[0, 0]]}'

    # run_tool is the only thing that would touch the MCP backend; stub it.
    async def fake_run_tool(backend, name, args):
        return fold_json

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)

    results = [
        SimpleNamespace(
            text="planning the base",
            tool_calls=[_tool_call("c1", "generate_fold_file", "{}")],
        ),
        SimpleNamespace(text="all done", tool_calls=[]),
    ]
    client = FakeClient(results)
    events = []

    asyncio.run(agent_loop.agent_turn(
        client, backend=object(), messages=[], emit=events.append
    ))

    types = [e["type"] for e in events]
    assert types == ["assistant", "tool_call", "tool_result", "assistant"]
    assert events[0] == {"type": "assistant", "text": "planning the base"}
    assert events[1]["name"] == "generate_fold_file"
    assert events[2]["output"] == fold_json
    assert events[2]["is_error"] is False
    assert events[3] == {"type": "assistant", "text": "all done"}


def test_agent_turn_defaults_to_print_sink(capsys):
    """No emit passed -> falls back to _print_sink (CLI behavior preserved)."""
    client = FakeClient([SimpleNamespace(text="hello world", tool_calls=[])])
    asyncio.run(agent_loop.agent_turn(client, backend=object(), messages=[]))
    assert "hello world" in capsys.readouterr().out
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `mcp_harness/.venv/bin/python -m pytest mcp_harness/tests/test_agent_turn_events.py -v`
Expected: FAIL — `agent_turn()` got an unexpected keyword argument `emit` (and `_print_sink` not defined).

- [ ] **Step 3: Add `_print_sink` to `agent_loop.py`**

Insert this just above `def _preview(` (~line 469):

```python
def _print_sink(event: dict) -> None:
    """Default agent_turn sink: format events to stdout (the terminal REPL view)."""
    kind = event["type"]
    if kind == "assistant":
        if event["text"]:
            print(event["text"], flush=True)
    elif kind == "tool_call":
        print(f"\n  [tool] {event['name']}({event['args_preview']})", flush=True)
    elif kind == "tool_result":
        print(f"  [<-]  {_preview(event['output'], 160)}", flush=True)
    elif kind == "notice":
        print(event["text"], flush=True)
```

- [ ] **Step 4: Rewrite `agent_turn` to emit events**

Replace the `agent_turn` body (lines 340-406). Update the signature line and replace each `print(...)` with an `emit(...)` call:

```python
async def agent_turn(
    client: "llm_client.LLMClient",
    backend: Backend,
    messages: list[dict],
    emit: "Callable[[dict], None] | None" = None,
) -> None:
    """Run one user turn to completion, emitting progress events to `emit`.

    `emit` receives structured event dicts (assistant / tool_call / tool_result /
    notice) instead of printing, so the terminal REPL and the web bridge are two
    sinks over one engine. Defaults to `_print_sink` (unchanged CLI behavior).
    See the original docstring for the loop semantics (MAX_AGENT_STEPS, history
    mutation, perturb/retry).
    """
    if emit is None:
        emit = _print_sink

    for step in range(1, MAX_AGENT_STEPS + 1):
        _trim_consumed_blobs(messages)
        result = await client.run_turn(SYSTEM_PROMPT, messages, backend.tools)

        if result.text:
            emit({"type": "assistant", "text": result.text})

        assistant_msg: dict = {"role": "assistant", "content": result.text or None}
        if result.tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in result.tool_calls
            ]
        messages.append(assistant_msg)

        if not result.tool_calls:
            return

        for tc in result.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                output = f"ERROR: bad tool arguments for {name}: {exc}"
                emit({"type": "tool_result", "name": name,
                      "output": output, "is_error": True})
            else:
                emit({"type": "tool_call", "name": name,
                      "args_preview": _preview(args)})
                output = await run_tool(backend, name, args)
                emit({"type": "tool_result", "name": name,
                      "output": output, "is_error": output.startswith("ERROR:")})
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": output})

        if step == MAX_AGENT_STEPS:
            emit({"type": "notice", "text": (
                f"\n[stopped after {MAX_AGENT_STEPS} tool steps without "
                "finishing; ask me to continue if it needs more]")})
            return
```

Add `Callable` to the typing imports at the top of the file. Find the import block (~lines 29-37) and add:

```python
from typing import Callable
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `mcp_harness/.venv/bin/python -m pytest mcp_harness/tests/test_agent_turn_events.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Run the full suite to confirm no regressions**

Run: `mcp_harness/.venv/bin/python -m pytest mcp_harness/tests -q`
Expected: all prior tests still pass (the CLI `main` uses the default print-sink).

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_turn_events.py
git commit -m "refactor(agent): agent_turn emits to injected event sink

Invert agent_turn's output dependency: emit structured events to an
injected callback instead of print(). _print_sink preserves the terminal
REPL view and is the default, so the CLI is unchanged. This is the seam
the web bridge plugs its WebSocket sink into.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `extract_fold` content-sniffer

A pure function that recognizes a FOLD document by its `"file_spec"` key. Lives in the web package; the bridge (Task 3) calls it on every tool result.

**Files:**
- Create: `web/__init__.py` (empty)
- Create: `web/fold.py`
- Test: `web/tests/__init__.py` (empty), `web/tests/test_fold.py`

**Interfaces:**
- Produces: `extract_fold(output: str) -> dict | None` — returns the parsed FOLD dict if `output` is a JSON object containing a top-level `"file_spec"` key, else `None`.

- [ ] **Step 1: Write the failing test**

Create `web/tests/test_fold.py`:

```python
import json

from web.fold import extract_fold


def test_extract_fold_returns_dict_for_fold_document():
    doc = {"file_spec": 1.1, "vertices_coords": [[0, 0], [1, 0]]}
    out = extract_fold(json.dumps(doc))
    assert out == doc


def test_extract_fold_none_for_plain_text():
    assert extract_fold("ERROR: circles overlap") is None


def test_extract_fold_none_for_non_fold_json():
    assert extract_fold('{"status": "ok"}') is None


def test_extract_fold_none_for_malformed_json():
    assert extract_fold('{"file_spec": 1.1, ') is None


def test_extract_fold_tolerates_surrounding_whitespace():
    doc = {"file_spec": 1.0}
    assert extract_fold("  \n" + json.dumps(doc) + "\n ") == doc
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_fold.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'web.fold'`.

- [ ] **Step 3: Create the package files and implementation**

Create empty `web/__init__.py` and `web/tests/__init__.py`. Create `web/fold.py`:

```python
"""Recognize a FOLD document inside a tool's text output.

A FOLD file is JSON with a top-level "file_spec" key (the FOLD spec's version
marker). We content-sniff that key rather than keying on which tool produced the
output, so detection stays correct as backend tools are renamed or added.
"""
from __future__ import annotations

import json


def extract_fold(output: str) -> dict | None:
    """Return the parsed FOLD dict if `output` is a FOLD document, else None."""
    text = output.strip()
    if not text.startswith("{"):
        return None
    try:
        doc = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if isinstance(doc, dict) and "file_spec" in doc:
        return doc
    return None
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_fold.py -v`
Expected: PASS (all five).

- [ ] **Step 5: Commit**

```bash
git add web/__init__.py web/fold.py web/tests/__init__.py web/tests/test_fold.py
git commit -m "feat(web): extract_fold content-sniffer for FOLD documents

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: FastAPI WebSocket bridge

The server: on startup wires `LLMClient.from_env()` + `connect_servers()`; exposes `WS /ws/chat` that runs one agent turn per prompt, forwards core events as wire frames, emits `fold` frames via `extract_fold`, and serves the built frontend. Tests stub the agent core (no network, no C++).

**Files:**
- Create: `web/server.py`
- Create: `web/requirements.txt`
- Test: `web/tests/test_server.py`

**Interfaces:**
- Consumes: `agent_loop.agent_turn` (Task 1), `agent_loop.connect_servers`, `agent_loop._preview`, `llm_client.LLMClient.from_env`, `web.fold.extract_fold` (Task 2).
- Produces: `app` (FastAPI instance); `WS /ws/chat`; module-level `state` (`AppState`) with `client`, `backend`, `error`. Wire frames sent to the client: `assistant`, `tool_call`, `tool_result`, `fold`, `turn_end`, `error` (per spec §3).

- [ ] **Step 1: Write `web/requirements.txt`**

```
fastapi>=0.110
uvicorn[standard]>=0.29
```

- [ ] **Step 2: Install the web deps**

Run: `mcp_harness/.venv/bin/pip install -r web/requirements.txt`
Expected: fastapi, uvicorn, starlette, websockets installed.

- [ ] **Step 3: Write the failing test**

Create `web/tests/test_server.py`:

```python
"""WebSocket bridge: stub the agent core, assert frame ordering + fold capture."""
import json

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    import agent_loop
    import llm_client
    from types import SimpleNamespace

    # Avoid spawning real MCP servers / needing a key during lifespan startup.
    async def fake_connect(stack):
        return SimpleNamespace(sessions={}, tools=[], route={})

    monkeypatch.setattr(agent_loop, "connect_servers", fake_connect)
    monkeypatch.setattr(
        llm_client.LLMClient, "from_env",
        classmethod(lambda cls: SimpleNamespace(cfg=SimpleNamespace(
            provider="fake", model="fake"))),
    )

    fold_doc = {"file_spec": 1.1, "vertices_coords": [[0, 0]]}

    async def fake_turn(client_, backend, messages, emit=None):
        emit({"type": "assistant", "text": "working"})
        emit({"type": "tool_call", "name": "generate_fold_file",
              "args_preview": "{}"})
        emit({"type": "tool_result", "name": "generate_fold_file",
              "output": json.dumps(fold_doc), "is_error": False})

    monkeypatch.setattr(agent_loop, "agent_turn", fake_turn)

    import web.server as server
    return TestClient(server.app)


def test_ws_streams_frames_and_captures_fold(client):
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make a star"})
        frames = [ws.receive_json() for _ in range(5)]

    types = [f["type"] for f in frames]
    assert types == ["assistant", "tool_call", "tool_result", "fold", "turn_end"]
    fold = next(f for f in frames if f["type"] == "fold")
    assert fold["filename"] == "model.fold"
    assert fold["json"]["file_spec"] == 1.1
    assert frames[-1] == {"type": "turn_end", "ok": True}


def test_ws_reports_startup_error(monkeypatch):
    import agent_loop
    import llm_client

    def boom(cls):
        raise ValueError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")

    monkeypatch.setattr(llm_client.LLMClient, "from_env", classmethod(boom))

    async def fake_connect(stack):
        from types import SimpleNamespace
        return SimpleNamespace(sessions={}, tools=[], route={})

    monkeypatch.setattr(agent_loop, "connect_servers", fake_connect)

    import importlib
    import web.server as server
    importlib.reload(server)
    c = TestClient(server.app)
    with c.websocket_connect("/ws/chat") as ws:
        msg = ws.receive_json()
    assert msg["type"] == "error"
    assert "API key" in msg["message"]
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'web.server'`.

- [ ] **Step 5: Implement `web/server.py`**

```python
"""FastAPI WebSocket bridge: browser <-> the existing agent core.

On startup it builds the LLM client (from_env / .env) and connects the MCP
backends once. Each WebSocket connection is one session; each prompt runs ONE
agent turn whose event sink is forwarded to the browser as JSON frames. Tool
results are content-sniffed for FOLD documents (web.fold.extract_fold) and sent
as `fold` frames. Single-user/local: turns are serialized.

Run (after `pip install -r web/requirements.txt`):
    mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000
"""
from __future__ import annotations

import asyncio
import os
import sys
from contextlib import AsyncExitStack, asynccontextmanager

# Make the agent core importable (flat modules under mcp_harness/).
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "mcp_harness"))

import env_config            # noqa: E402
env_config.load_env()        # load .env before any os.environ reads

import agent_loop            # noqa: E402
import llm_client            # noqa: E402
from fastapi import FastAPI, WebSocket, WebSocketDisconnect  # noqa: E402
from fastapi.staticfiles import StaticFiles                  # noqa: E402

from web.fold import extract_fold  # noqa: E402

_DIST = os.path.join(_HERE, "frontend", "dist")


class AppState:
    client = None
    backend = None
    error: str | None = None


state = AppState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stack = AsyncExitStack()
    try:
        state.client = llm_client.LLMClient.from_env()
        state.backend = await agent_loop.connect_servers(stack)
    except Exception as exc:  # surfaced to the browser, not fatal
        state.error = str(exc)
    try:
        yield
    finally:
        await stack.aclose()


app = FastAPI(lifespan=lifespan)


async def _send_frames(ws: WebSocket, event: dict) -> None:
    """Translate one core event into client wire frame(s)."""
    kind = event["type"]
    if kind == "assistant":
        await ws.send_json({"type": "assistant", "text": event["text"]})
    elif kind == "tool_call":
        await ws.send_json({"type": "tool_call", "name": event["name"],
                            "args_preview": event["args_preview"]})
    elif kind == "notice":
        await ws.send_json({"type": "assistant", "text": event["text"]})
    elif kind == "tool_result":
        output = event["output"]
        await ws.send_json({
            "type": "tool_result",
            "name": event["name"],
            "preview": agent_loop._preview(output, 160),
            "is_error": event["is_error"],
        })
        fold = extract_fold(output)
        if fold is not None:
            await ws.send_json({"type": "fold", "filename": "model.fold",
                                "json": fold})


@app.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    await ws.accept()
    if state.error:
        await ws.send_json({"type": "error", "message": state.error})
        await ws.close()
        return

    messages: list[dict] = []
    while True:
        try:
            raw = await ws.receive_json()
        except WebSocketDisconnect:
            return
        if raw.get("type") != "prompt":
            continue
        messages.append({"role": "user", "content": raw["text"]})

        # agent_turn's sink is synchronous; bridge it to the async socket via a
        # queue, run the turn as a task, drain frames until a sentinel arrives.
        queue: asyncio.Queue = asyncio.Queue()

        async def run() -> None:
            try:
                await agent_loop.agent_turn(
                    state.client, state.backend, messages,
                    emit=queue.put_nowait)
                queue.put_nowait({"type": "__end__"})
            except Exception as exc:  # engine/loop failure -> one error frame
                queue.put_nowait({"type": "__error__", "message": str(exc)})

        task = asyncio.create_task(run())
        while True:
            event = await queue.get()
            if event["type"] == "__end__":
                await ws.send_json({"type": "turn_end", "ok": True})
                break
            if event["type"] == "__error__":
                await ws.send_json({"type": "error",
                                    "message": event["message"]})
                break
            await _send_frames(ws, event)
        await task


# Serve the built frontend in production / desktop (no-op if not built yet).
if os.path.isdir(_DIST):
    app.mount("/", StaticFiles(directory=_DIST, html=True), name="static")
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py -v`
Expected: PASS (both tests).

- [ ] **Step 7: Run the full Python suite**

Run: `mcp_harness/.venv/bin/python -m pytest mcp_harness/tests web/tests -q`
Expected: all green.

- [ ] **Step 8: Commit**

```bash
git add web/server.py web/requirements.txt web/tests/test_server.py
git commit -m "feat(web): FastAPI WebSocket bridge over the agent core

WS /ws/chat runs one agent turn per prompt, forwards the event sink as JSON
frames, and emits fold frames via content-sniffing. Startup errors (missing
API key) surface as an error frame instead of crashing. Stubbed-core tests
run with no network and no C++ engine.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: React + Vite + TypeScript frontend

The browser app: a prompt box, a streaming transcript, and a result pane showing the pretty-printed `.fold` with a Download button. Frame handling is a pure reducer (`applyFrame`) so it's unit-testable without a live socket.

**Files:**
- Create: `web/frontend/package.json`, `web/frontend/tsconfig.json`, `web/frontend/vite.config.ts`, `web/frontend/index.html`
- Create: `web/frontend/src/main.tsx`, `web/frontend/src/chat.ts`, `web/frontend/src/App.tsx`, `web/frontend/src/styles.css`
- Test: `web/frontend/src/chat.test.ts`

**Interfaces:**
- Consumes: the wire frames from Task 3.
- Produces: `applyFrame(state: ChatState, frame: Frame): ChatState`; `initialState: ChatState`; `<App>` React component connecting to `ws://${location.host}/ws/chat`.

- [ ] **Step 1: Scaffold the project files**

Create `web/frontend/package.json`:

```json
{
  "name": "origami-ide-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "typescript": "^5.5.3",
    "vite": "^5.3.4",
    "vitest": "^2.0.4"
  }
}
```

Create `web/frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"]
}
```

Create `web/frontend/vite.config.ts` (dev server proxies the WebSocket to FastAPI on :8000):

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

Create `web/frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Origami IDE</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Write the failing reducer test**

Create `web/frontend/src/chat.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { applyFrame, initialState } from "./chat";

describe("applyFrame", () => {
  it("appends assistant text to the transcript", () => {
    const s = applyFrame(initialState, { type: "assistant", text: "hi" });
    expect(s.transcript).toEqual([{ kind: "assistant", text: "hi" }]);
  });

  it("captures a fold artifact", () => {
    const fold = { file_spec: 1.1, vertices_coords: [[0, 0]] };
    const s = applyFrame(initialState, {
      type: "fold",
      filename: "model.fold",
      json: fold,
    });
    expect(s.fold).toEqual({ filename: "model.fold", json: fold });
  });

  it("marks tool errors", () => {
    const s = applyFrame(initialState, {
      type: "tool_result",
      name: "compile",
      preview: "ERROR: circles overlap",
      is_error: true,
    });
    expect(s.transcript[0]).toMatchObject({ kind: "tool_result", isError: true });
  });

  it("clears busy on turn_end", () => {
    const s = applyFrame({ ...initialState, busy: true }, {
      type: "turn_end",
      ok: true,
    });
    expect(s.busy).toBe(false);
  });

  it("records an error frame and clears busy", () => {
    const s = applyFrame({ ...initialState, busy: true }, {
      type: "error",
      message: "no API key",
    });
    expect(s.busy).toBe(false);
    expect(s.transcript.at(-1)).toEqual({ kind: "error", text: "no API key" });
  });
});
```

- [ ] **Step 3: Run the test to verify it fails**

Run (from `web/frontend`): `npm install` then `npm test`
Expected: FAIL — cannot find module `./chat`.

- [ ] **Step 4: Implement `web/frontend/src/chat.ts`**

```ts
export type Frame =
  | { type: "assistant"; text: string }
  | { type: "tool_call"; name: string; args_preview: string }
  | { type: "tool_result"; name: string; preview: string; is_error: boolean }
  | { type: "fold"; filename: string; json: unknown }
  | { type: "turn_end"; ok: boolean }
  | { type: "error"; message: string };

export type Entry =
  | { kind: "user"; text: string }
  | { kind: "assistant"; text: string }
  | { kind: "tool_call"; name: string; argsPreview: string }
  | { kind: "tool_result"; name: string; preview: string; isError: boolean }
  | { kind: "error"; text: string };

export interface FoldArtifact {
  filename: string;
  json: unknown;
}

export interface ChatState {
  transcript: Entry[];
  fold: FoldArtifact | null;
  busy: boolean;
}

export const initialState: ChatState = {
  transcript: [],
  fold: null,
  busy: false,
};

export function applyFrame(state: ChatState, frame: Frame): ChatState {
  switch (frame.type) {
    case "assistant":
      return { ...state, transcript: [...state.transcript,
        { kind: "assistant", text: frame.text }] };
    case "tool_call":
      return { ...state, transcript: [...state.transcript,
        { kind: "tool_call", name: frame.name, argsPreview: frame.args_preview }] };
    case "tool_result":
      return { ...state, transcript: [...state.transcript,
        { kind: "tool_result", name: frame.name, preview: frame.preview,
          isError: frame.is_error }] };
    case "fold":
      return { ...state,
        fold: { filename: frame.filename, json: frame.json } };
    case "turn_end":
      return { ...state, busy: false };
    case "error":
      return { ...state, busy: false, transcript: [...state.transcript,
        { kind: "error", text: frame.message }] };
    default:
      return state;
  }
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run (from `web/frontend`): `npm test`
Expected: PASS (all five).

- [ ] **Step 6: Implement the React UI**

Create `web/frontend/src/App.tsx`:

```tsx
import { useEffect, useReducer, useRef, useState } from "react";
import { applyFrame, initialState, type Frame, type ChatState } from "./chat";

function reducer(state: ChatState, action:
  | { kind: "frame"; frame: Frame }
  | { kind: "user"; text: string }): ChatState {
  if (action.kind === "user") {
    return { ...state, busy: true,
      transcript: [...state.transcript, { kind: "user", text: action.text }] };
  }
  return applyFrame(state, action.frame);
}

export default function App() {
  const [state, dispatch] = useReducer(reducer, initialState);
  const [draft, setDraft] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`ws://${location.host}/ws/chat`);
    ws.onmessage = (e) =>
      dispatch({ kind: "frame", frame: JSON.parse(e.data) as Frame });
    wsRef.current = ws;
    return () => ws.close();
  }, []);

  function send() {
    const text = draft.trim();
    if (!text || state.busy || wsRef.current?.readyState !== WebSocket.OPEN) return;
    wsRef.current.send(JSON.stringify({ type: "prompt", text }));
    dispatch({ kind: "user", text });
    setDraft("");
  }

  function download() {
    if (!state.fold) return;
    const blob = new Blob([JSON.stringify(state.fold.json, null, 2)],
      { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = state.fold.filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="app">
      <section className="chat">
        <h1>Origami IDE</h1>
        <div className="transcript">
          {state.transcript.map((e, i) => (
            <div key={i} className={`entry ${e.kind}`}>
              {e.kind === "user" && <p><b>you:</b> {e.text}</p>}
              {e.kind === "assistant" && <p>{e.text}</p>}
              {e.kind === "tool_call" &&
                <p className="tool">⚙ {e.name}({e.argsPreview})</p>}
              {e.kind === "tool_result" &&
                <p className={e.isError ? "err" : "tool"}>↳ {e.preview}</p>}
              {e.kind === "error" && <p className="err">⚠ {e.text}</p>}
            </div>
          ))}
        </div>
        <div className="composer">
          <textarea value={draft} disabled={state.busy}
            placeholder="Describe an origami subject…"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
            }} />
          <button onClick={send} disabled={state.busy}>
            {state.busy ? "Working…" : "Send"}
          </button>
        </div>
      </section>
      <section className="result">
        <div className="result-head">
          <h2>.fold output</h2>
          <button onClick={download} disabled={!state.fold}>Download .fold</button>
        </div>
        <pre className="fold">
          {state.fold ? JSON.stringify(state.fold.json, null, 2)
                      : "No .fold yet — send a prompt."}
        </pre>
      </section>
    </div>
  );
}
```

Create `web/frontend/src/main.tsx`:

```tsx
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

Create `web/frontend/src/styles.css`:

```css
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.5 ui-monospace, "SF Mono", Menlo, monospace; }
.app { display: grid; grid-template-columns: 1fr 1fr; height: 100vh; }
.chat, .result { display: flex; flex-direction: column; padding: 1rem;
  overflow: hidden; }
.result { border-left: 1px solid #ddd; background: #fafafa; }
.transcript { flex: 1; overflow-y: auto; }
.entry { margin: .25rem 0; }
.tool { color: #555; }
.err { color: #b00020; }
.composer { display: flex; gap: .5rem; }
.composer textarea { flex: 1; height: 3rem; resize: vertical; }
.result-head { display: flex; justify-content: space-between; align-items: center; }
.fold { flex: 1; overflow: auto; background: #fff; padding: .75rem;
  border: 1px solid #eee; white-space: pre-wrap; }
```

- [ ] **Step 7: Type-check and build**

Run (from `web/frontend`): `npm run build`
Expected: `tsc` passes and Vite writes `web/frontend/dist/`.

- [ ] **Step 8: Commit**

```bash
git add web/frontend
git commit -m "feat(web): React/Vite/TS frontend (chat + .fold result pane)

Streaming transcript over WebSocket, pure applyFrame reducer (unit-tested
with Vitest), result pane pretty-prints the .fold with a Download button.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Run docs, gitignore, and manual smoke

Wire the pieces together for a human: a README with run instructions, gitignore the frontend build artifacts, and a documented end-to-end manual smoke (real key, real prompt).

**Files:**
- Create: `web/README.md`
- Modify: `.gitignore`

- [ ] **Step 1: Ignore frontend build + node_modules**

Add to `.gitignore` (under the existing "Build artifacts" section):

```
# Web frontend build + deps
web/frontend/node_modules/
web/frontend/dist/
```

- [ ] **Step 2: Write `web/README.md`**

```markdown
# Web UI (thin slice)

Local-first browser front end for the origami agent: type a prompt, watch the
agent stream its work, download the final `.fold`.

## One-time setup
```bash
# Python web deps (into the project venv)
mcp_harness/.venv/bin/pip install -r web/requirements.txt
# Frontend deps
cd web/frontend && npm install && cd ../..
```

Set your LLM key in `.env` at the repo root (see `.env.example`), e.g.
`LLM_PROVIDER=groq` + `GROQ_API_KEY=...`.

## Run (two terminals)
```bash
# 1. Backend (FastAPI + agent core + MCP servers)
mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000

# 2. Frontend dev server (proxies the WebSocket to :8000)
cd web/frontend && npm run dev
```
Open the Vite URL (default http://localhost:5173).

## Production / single-port
```bash
cd web/frontend && npm run build && cd ../..
mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000
```
FastAPI then serves the built UI at http://localhost:8000.

## Tests
```bash
mcp_harness/.venv/bin/python -m pytest web/tests -q      # bridge + fold sniffer
cd web/frontend && npm test                              # reducer
```
```

- [ ] **Step 3: Manual smoke (opt-in, real key — document the result)**

With a real key in `.env`, run both servers (above), open the UI, and submit:
`Design a symmetric five-pointed star base.`

Expected: assistant text + `⚙` tool calls stream into the transcript; any
`ERROR:` lines appear inline; within the agent's step budget a `.fold` populates
the result pane and `Download .fold` saves a valid FOLD JSON file.

- [ ] **Step 4: Commit**

```bash
git add web/README.md .gitignore
git commit -m "docs(web): run instructions + gitignore frontend build artifacts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Plan Self-Review

- **Spec coverage:** §2 architecture → Tasks 1+3. §2.1 print→sink refactor → Task 1. §3 protocol frames → Task 3 `_send_frames` + Task 4 reducer. §4 fold capture (content-sniff `file_spec`, last-wins via per-result emit) → Task 2 + Task 3. §5 error handling (startup key error, tool errors as signals, turn-boundary crash) → Task 3 (`state.error` frame, `__error__` sentinel) + Task 4 (error entry). §6 testing (fake-sink core, stubbed-core bridge, Vitest reducer, manual smoke) → Tasks 1/3/4/5. §7 success criteria → Task 5 smoke + serve-built-frontend in Task 3. Non-goals respected (no viewport/board/tree/Tauri).
- **Placeholder scan:** none — all steps carry concrete code/commands.
- **Type consistency:** `agent_turn(..., emit=None)` and the event dict shapes (`assistant`/`tool_call`/`tool_result`/`notice`) are produced in Task 1 and consumed identically in Task 3 `_send_frames`. Wire frames in Task 3 (`assistant`/`tool_call`/`tool_result`/`fold`/`turn_end`/`error`) match the `Frame` union and `applyFrame` in Task 4. `extract_fold` signature consistent between Task 2 and Task 3.
- **Note:** Task 3 reads `agent_loop._preview` (a module private) for truncation parity with the CLI; acceptable in-repo reuse rather than duplicating the helper.
```

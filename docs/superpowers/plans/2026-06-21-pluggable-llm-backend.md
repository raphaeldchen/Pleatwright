# Pluggable LLM Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the agent orchestrator run against any OpenAI-compatible LLM endpoint (Groq, Gemini, Ollama, or Claude via its compat endpoint), selected by environment variable, defaulting to Claude.

**Architecture:** Add `mcp_harness/llm_client.py` — a provider-agnostic, non-streaming client over the `openai` SDK with a preset registry and env-based config. Rewrite `agent_loop.py` to use it: OpenAI-shaped tool schemas and message history, an OpenAI-style turn loop. Claude becomes just another `base_url`.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv`), the `openai` SDK (new dependency), the existing `mcp` stdio clients and FastMCP servers (unchanged), pytest.

**Design spec:** `docs/superpowers/specs/2026-06-21-pluggable-llm-backend-design.md`.

## Global Constraints

- Run everything from `mcp_harness/` with `PYTHONPATH=.:tests` using `./.venv/bin/python`.
- Single OpenAI-compatible client; **no native Anthropic SDK calls** in the new code path. The `anthropic` package stays installed but unused (do not remove it).
- **Non-streaming** only.
- Default `LLM_PROVIDER` = `claude` (backward-compatible). Verification/smoke runs on Groq (`LLM_PROVIDER=groq`).
- Env vars: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_MAX_TOKENS` (default `4096`), `LLM_TEMPERATURE` (default `0.0`).
- `llm_client.py` knows nothing about origami/MCP routing; `agent_loop.py` knows nothing about HTTP/provider specifics.
- Do not change the gate (`ensure_gate_trained`), the MCP servers, or tool routing logic.
- Unit tests must be network-free (use injected fakes, never a real provider call).

## File Structure

- Create: `mcp_harness/llm_client.py` — `PROVIDERS`, `LLMConfig`(+`from_env`), `tools_to_openai`, `TurnResult`, `LLMClient`(+`run_turn`).
- Create: `mcp_harness/tests/test_llm_client.py` — network-free unit tests for config, conversion, and `run_turn` parsing.
- Modify: `mcp_harness/agent_loop.py` — imports, `Backend.tools`, `connect_servers`, `agent_turn`, `main()`.
- Modify: `mcp_harness/tests/` — add `test_agent_turn.py` for the rewritten loop (network-free, fake client).

---

### Task 1: `llm_client.py` config + tool conversion (pure, network-free)

**Files:**
- Create: `mcp_harness/llm_client.py`
- Test: `mcp_harness/tests/test_llm_client.py`

**Interfaces:**
- Consumes: `openai` SDK (new dependency, installed in Step 0).
- Produces:
  - `PROVIDERS: dict[str, dict]` with keys `groq`, `gemini`, `ollama`, `claude`; each value has `base_url`, `default_model`, `api_key_env` (str or None).
  - `LLMConfig` dataclass: fields `provider, model, base_url, api_key, max_tokens, temperature`; classmethod `from_env() -> LLMConfig` (raises `ValueError` on unknown provider or missing required key).
  - `tools_to_openai(mcp_tools) -> list[dict]` — each input item has attributes `.name`, `.description`, `.inputSchema`.

- [ ] **Step 0: Install the `openai` SDK**

Run: `cd mcp_harness && ./.venv/bin/pip install openai`
Expected: installs `openai` and its deps; ends with "Successfully installed openai-...". Then confirm: `./.venv/bin/python -c "import openai; print(openai.__version__)"` prints a version.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_llm_client.py`:

```python
"""Network-free unit tests for the pluggable LLM client (config + conversion)."""
import sys
sys.path.insert(0, "tests")

from types import SimpleNamespace
import pytest
from llm_client import PROVIDERS, LLMConfig, tools_to_openai


def test_from_env_defaults_to_claude(monkeypatch):
    for v in ("LLM_PROVIDER", "LLM_MODEL", "LLM_BASE_URL",
              "LLM_MAX_TOKENS", "LLM_TEMPERATURE"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    cfg = LLMConfig.from_env()
    assert cfg.provider == "claude"
    assert cfg.base_url == PROVIDERS["claude"]["base_url"]
    assert cfg.model == PROVIDERS["claude"]["default_model"]
    assert cfg.api_key == "sk-test"
    assert cfg.max_tokens == 4096
    assert cfg.temperature == 0.0


def test_from_env_groq_resolves_preset(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    cfg = LLMConfig.from_env()
    assert cfg.base_url == "https://api.groq.com/openai/v1"
    assert cfg.model == "llama-3.3-70b-versatile"
    assert cfg.api_key == "gsk-test"


def test_from_env_model_and_base_url_overrides(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")
    monkeypatch.setenv("LLM_MODEL", "some-other-model")
    monkeypatch.setenv("LLM_BASE_URL", "http://localhost:9999/v1")
    cfg = LLMConfig.from_env()
    assert cfg.model == "some-other-model"
    assert cfg.base_url == "http://localhost:9999/v1"


def test_from_env_ollama_needs_no_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    cfg = LLMConfig.from_env()
    assert cfg.base_url == "http://localhost:11434/v1"
    assert cfg.api_key == "ollama"          # dummy non-empty key for the SDK


def test_from_env_unknown_provider_raises(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    with pytest.raises(ValueError, match="unknown LLM_PROVIDER"):
        LLMConfig.from_env()


def test_from_env_missing_key_raises_naming_var(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        LLMConfig.from_env()


def test_tools_to_openai_shape():
    mcp_tool = SimpleNamespace(
        name="add_node", description="Add a node",
        inputSchema={"type": "object", "properties": {"id": {"type": "integer"}}})
    out = tools_to_openai([mcp_tool])
    assert out == [{
        "type": "function",
        "function": {
            "name": "add_node",
            "description": "Add a node",
            "parameters": {"type": "object",
                           "properties": {"id": {"type": "integer"}}},
        },
    }]


def test_tools_to_openai_handles_missing_description():
    mcp_tool = SimpleNamespace(name="t", description=None, inputSchema={"type": "object"})
    out = tools_to_openai([mcp_tool])
    assert out[0]["function"]["description"] == ""
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_llm_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'llm_client'`.

- [ ] **Step 3: Implement the config + conversion (no client yet)**

Create `mcp_harness/llm_client.py`:

```python
"""Provider-agnostic LLM client for the Tier 2 orchestrator.

One responsibility: turn a (system, messages, tools) request into a completed,
non-streaming turn against ANY OpenAI-compatible endpoint -- Groq, Gemini,
Ollama, or Anthropic's compat endpoint. Selected by environment variable so the
project can run on a free/cheap backend. Knows nothing about origami or MCP.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

# Preset registry. Every provider here speaks the OpenAI chat-completions API;
# only base_url / model / key env var differ. api_key_env=None means the
# provider needs no key (local Ollama).
PROVIDERS: dict[str, dict] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
    },
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-2.0-flash",
        "api_key_env": "GEMINI_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "default_model": "qwen2.5:7b",
        "api_key_env": None,
    },
    "claude": {
        "base_url": "https://api.anthropic.com/v1/",
        "default_model": "claude-sonnet-4-6",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
}


@dataclass
class LLMConfig:
    """Resolved backend selection. Build with from_env()."""

    provider: str
    model: str
    base_url: str
    api_key: str
    max_tokens: int = 4096
    temperature: float = 0.0

    @classmethod
    def from_env(cls) -> "LLMConfig":
        provider = os.environ.get("LLM_PROVIDER", "claude")
        if provider not in PROVIDERS:
            raise ValueError(
                f"unknown LLM_PROVIDER {provider!r}; "
                f"valid: {', '.join(sorted(PROVIDERS))}")
        preset = PROVIDERS[provider]
        model = os.environ.get("LLM_MODEL", preset["default_model"])
        base_url = os.environ.get("LLM_BASE_URL", preset["base_url"])

        key_env = preset["api_key_env"]
        if key_env is None:
            api_key = "ollama"          # local; the SDK still wants a non-empty key
        else:
            api_key = os.environ.get(key_env, "")
            if not api_key:
                raise ValueError(
                    f"provider {provider!r} requires an API key; set {key_env}")

        max_tokens = int(os.environ.get("LLM_MAX_TOKENS", "4096"))
        temperature = float(os.environ.get("LLM_TEMPERATURE", "0.0"))
        return cls(provider, model, base_url, api_key, max_tokens, temperature)


def tools_to_openai(mcp_tools) -> list[dict]:
    """Convert discovered MCP tools to OpenAI's function-tool schema.

    Each input item has .name, .description, and .inputSchema (already JSON
    Schema, which is exactly what OpenAI's `function.parameters` expects).
    """
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description or "",
                "parameters": t.inputSchema,
            },
        }
        for t in mcp_tools
    ]
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_llm_client.py -v`
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/llm_client.py mcp_harness/tests/test_llm_client.py
git commit -m "feat(llm): provider presets + env config + MCP->OpenAI tool conversion

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `LLMClient.run_turn` (non-streaming, fake-client tested)

**Files:**
- Modify: `mcp_harness/llm_client.py`
- Test: `mcp_harness/tests/test_llm_client.py` (append)

**Interfaces:**
- Consumes: `LLMConfig` (Task 1), `openai.AsyncOpenAI`.
- Produces:
  - `TurnResult` dataclass: `text: str`, `tool_calls: list`, `finish_reason: str`. Each tool-call item exposes `.id`, `.function.name`, `.function.arguments` (a JSON string) — the OpenAI SDK's tool-call shape.
  - `LLMClient`: `__init__(self, cfg: LLMConfig)` sets `self.cfg`, `self.model`, `self.max_tokens`, `self.temperature`, and `self._client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key)`; classmethod `from_env() -> LLMClient`; `async run_turn(self, system, messages, tools) -> TurnResult`.

- [ ] **Step 1: Append the failing tests**

Append to `mcp_harness/tests/test_llm_client.py`:

```python
import asyncio
from llm_client import LLMClient, TurnResult


def _make_client():
    # Construct without env (AsyncOpenAI construction makes no network call).
    cfg = LLMConfig(provider="groq", model="m",
                    base_url="http://x/v1", api_key="k")
    return LLMClient(cfg)


def _fake_response(content, tool_calls, finish_reason):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=msg,
                                                    finish_reason=finish_reason)])


class _FakeCompletions:
    def __init__(self, resp):
        self._resp = resp
        self.last_kwargs = None

    async def create(self, **kwargs):
        self.last_kwargs = kwargs
        return self._resp


def _install_fake(client, resp):
    client._client = SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletions(resp)))
    return client._client.chat.completions


def test_run_turn_plain_text():
    client = _make_client()
    fake = _install_fake(client, _fake_response("hello", None, "stop"))
    result = asyncio.run(client.run_turn("SYS", [{"role": "user", "content": "hi"}], []))
    assert isinstance(result, TurnResult)
    assert result.text == "hello"
    assert result.tool_calls == []
    assert result.finish_reason == "stop"
    # system prepended, model + sampling params forwarded.
    assert fake.last_kwargs["messages"][0] == {"role": "system", "content": "SYS"}
    assert fake.last_kwargs["model"] == "m"
    assert fake.last_kwargs["max_tokens"] == 4096
    assert fake.last_kwargs["temperature"] == 0.0
    assert fake.last_kwargs["tool_choice"] == "auto"


def test_run_turn_extracts_tool_calls():
    client = _make_client()
    tc = SimpleNamespace(id="call_1",
                         function=SimpleNamespace(name="add_node",
                                                  arguments='{"id": 1}'))
    _install_fake(client, _fake_response(None, [tc], "tool_calls"))
    result = asyncio.run(client.run_turn("SYS", [], []))
    assert result.text == ""               # None content normalized to ""
    assert result.finish_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[0].function.name == "add_node"
    assert result.tool_calls[0].function.arguments == '{"id": 1}'
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_llm_client.py::test_run_turn_plain_text -v`
Expected: FAIL — `ImportError: cannot import name 'LLMClient'`.

- [ ] **Step 3: Implement `TurnResult` and `LLMClient`**

Append to `mcp_harness/llm_client.py` (add `from openai import AsyncOpenAI` near the top imports):

```python
from openai import AsyncOpenAI


@dataclass
class TurnResult:
    """One model turn. tool_calls items are OpenAI SDK tool-call objects, each
    with .id and .function.{name, arguments}; arguments is a JSON string."""

    text: str
    tool_calls: list
    finish_reason: str


class LLMClient:
    """Non-streaming chat-completions client over any OpenAI-compatible endpoint."""

    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg
        self.model = cfg.model
        self.max_tokens = cfg.max_tokens
        self.temperature = cfg.temperature
        self._client = AsyncOpenAI(base_url=cfg.base_url, api_key=cfg.api_key)

    @classmethod
    def from_env(cls) -> "LLMClient":
        return cls(LLMConfig.from_env())

    async def run_turn(self, system, messages, tools) -> TurnResult:
        """Run one turn. `messages` is OpenAI-format history (no system message --
        we prepend it here). Returns the assistant text, any tool calls, and the
        finish reason."""
        resp = await self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}] + messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        choice = resp.choices[0]
        msg = choice.message
        return TurnResult(
            text=msg.content or "",
            tool_calls=list(msg.tool_calls or []),
            finish_reason=choice.finish_reason,
        )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_llm_client.py -v`
Expected: all tests PASS (10 total).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/llm_client.py mcp_harness/tests/test_llm_client.py
git commit -m "feat(llm): non-streaming LLMClient.run_turn over OpenAI-compatible API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Rewrite `agent_loop.py` to use the pluggable client

**Files:**
- Modify: `mcp_harness/agent_loop.py`
- Test: `mcp_harness/tests/test_agent_turn.py`

**Interfaces:**
- Consumes: `llm_client.LLMClient` (`run_turn`, `from_env`, `.cfg.provider`, `.cfg.model`), `llm_client.tools_to_openai`, `llm_client.TurnResult` (Tasks 1-2).
- Produces:
  - `Backend.tools: list[dict]` (renamed from `anthropic_tools`).
  - `agent_turn(client, backend, messages)` operating in OpenAI message format: appends assistant messages `{"role":"assistant","content":..., "tool_calls":[{"id","type":"function","function":{"name","arguments"}}]}` and tool results `{"role":"tool","tool_call_id":..., "content":...}`.

- [ ] **Step 1: Write the failing integration test**

Create `mcp_harness/tests/test_agent_turn.py`:

```python
"""Network-free test of the rewritten agent_turn loop using a fake LLM client."""
import sys
sys.path.insert(0, "tests")

import asyncio
from types import SimpleNamespace

import agent_loop
from llm_client import TurnResult


class _FakeLLM:
    """Returns queued TurnResults in order; records run_turn calls."""

    def __init__(self, results):
        self._results = list(results)
        self.calls = 0

    async def run_turn(self, system, messages, tools):
        r = self._results[self.calls]
        self.calls += 1
        return r


def test_agent_turn_executes_tool_then_finishes(monkeypatch):
    # First turn asks for one tool call; second turn returns plain text.
    tc = SimpleNamespace(
        id="call_1",
        function=SimpleNamespace(name="predict_tree_feasibility",
                                 arguments='{"tree_nodes": []}'))
    results = [
        TurnResult(text="let me check", tool_calls=[tc], finish_reason="tool_calls"),
        TurnResult(text="all done", tool_calls=[], finish_reason="stop"),
    ]
    client = _FakeLLM(results)
    backend = SimpleNamespace(tools=[])

    recorded = []

    async def fake_run_tool(backend_, name, args):
        recorded.append((name, args))
        return "tool-output"

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)

    messages = [{"role": "user", "content": "design a quadruped"}]
    asyncio.run(agent_loop.agent_turn(client, backend, messages))

    # The tool was called once with parsed args.
    assert recorded == [("predict_tree_feasibility", {"tree_nodes": []})]
    # History is valid OpenAI shape: user, assistant(tool_calls), tool, assistant(text).
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["tool_calls"][0]["id"] == "call_1"
    assert messages[1]["tool_calls"][0]["function"]["name"] == "predict_tree_feasibility"
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_msgs) == 1
    assert tool_msgs[0]["tool_call_id"] == "call_1"
    assert tool_msgs[0]["content"] == "tool-output"
    assert messages[-1] == {"role": "assistant", "content": "all done"}
    assert client.calls == 2          # looped exactly twice


def test_agent_turn_bad_tool_args_recovers(monkeypatch):
    # Malformed JSON args must become an ERROR tool result, not a crash.
    tc = SimpleNamespace(
        id="call_x",
        function=SimpleNamespace(name="add_node", arguments="{not json"))
    results = [
        TurnResult(text="", tool_calls=[tc], finish_reason="tool_calls"),
        TurnResult(text="ok", tool_calls=[], finish_reason="stop"),
    ]
    client = _FakeLLM(results)
    backend = SimpleNamespace(tools=[])

    called = False

    async def fake_run_tool(backend_, name, args):
        nonlocal called
        called = True
        return "should-not-run"

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)

    messages = [{"role": "user", "content": "x"}]
    asyncio.run(agent_loop.agent_turn(client, backend, messages))

    assert called is False             # bad args never reach run_tool
    tool_msgs = [m for m in messages if m.get("role") == "tool"]
    assert tool_msgs[0]["tool_call_id"] == "call_x"
    assert tool_msgs[0]["content"].startswith("ERROR: bad tool arguments")
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_agent_turn.py -v`
Expected: FAIL — current `agent_turn` uses the Anthropic streaming API and `client.messages.stream`, so it errors on the fake client (`AttributeError`/wrong message shape).

- [ ] **Step 3: Update imports and the `Backend` dataclass**

In `mcp_harness/agent_loop.py`, replace:

```python
from anthropic import AsyncAnthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
```

with:

```python
import llm_client
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
```

Then remove the module-level `MODEL` and `MAX_TOKENS` constants (lines `MODEL = "claude-sonnet-4-6"` and `MAX_TOKENS = 4096`) — the client now owns these via `LLMConfig`.

Then in the `Backend` dataclass, replace:

```python
    anthropic_tools: list[dict]             # tool schemas in Anthropic's format
```

with:

```python
    tools: list[dict]                       # tool schemas in OpenAI function format
```

- [ ] **Step 4: Update `connect_servers` to build OpenAI tools**

In `connect_servers`, replace this block:

```python
    sessions: dict[str, ClientSession] = {}
    anthropic_tools: list[dict] = []
    route: dict[str, ClientSession] = {}
```

with:

```python
    sessions: dict[str, ClientSession] = {}
    discovered: list = []                   # raw MCP tool objects, converted below
    route: dict[str, ClientSession] = {}
```

Then replace the inner append block:

```python
            route[tool.name] = session
            anthropic_tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    # MCP's inputSchema is already JSON-Schema, which is exactly
                    # what Anthropic's tool `input_schema` expects.
                    "input_schema": tool.inputSchema,
                }
            )

    return Backend(sessions=sessions, anthropic_tools=anthropic_tools, route=route)
```

with:

```python
            route[tool.name] = session
            discovered.append(tool)

    return Backend(sessions=sessions,
                   tools=llm_client.tools_to_openai(discovered),
                   route=route)
```

- [ ] **Step 5: Rewrite `agent_turn`**

In `mcp_harness/agent_loop.py`, replace the entire body of `agent_turn` (from the `for step in range(1, MAX_AGENT_STEPS + 1):` loop through the end of the function) with this implementation, and update the signature's type hint from `client: AsyncAnthropic` to `client: "llm_client.LLMClient"`:

```python
    for step in range(1, MAX_AGENT_STEPS + 1):
        result = await client.run_turn(SYSTEM_PROMPT, messages, backend.tools)

        if result.text:
            print(result.text)

        # Record the assistant message in OpenAI format (provider-agnostic dicts
        # so it round-trips back into the next request).
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

        # Execute each requested tool; a bad-JSON arg string is a recoverable
        # signal (ERROR tool result), not a crash.
        for tc in result.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments)
            except json.JSONDecodeError as exc:
                output = f"ERROR: bad tool arguments for {name}: {exc}"
            else:
                print(f"\n  [tool] {name}({_preview(args)})", flush=True)
                output = await run_tool(backend, name, args)
                print(f"  [<-]  {_preview(output, 160)}", flush=True)
            messages.append(
                {"role": "tool", "tool_call_id": tc.id, "content": output})

        # Safety stop: pending tool batch is recorded, so history stays valid.
        if step == MAX_AGENT_STEPS:
            print(
                f"\n[stopped after {MAX_AGENT_STEPS} tool steps without "
                "finishing; ask me to continue if it needs more]",
                flush=True,
            )
            return
```

- [ ] **Step 6: Run the agent_turn test to verify it passes**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_agent_turn.py -v`
Expected: both tests PASS.

- [ ] **Step 7: Update `main()` to build the client from env**

In `mcp_harness/agent_loop.py`, in `main()`, replace this block:

```python
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            "ERROR: ANTHROPIC_API_KEY is not set.\n"
            "    export ANTHROPIC_API_KEY=sk-ant-...   then rerun."
        )

    client = AsyncAnthropic()
```

with:

```python
    try:
        client = llm_client.LLMClient.from_env()
    except ValueError as exc:
        sys.exit(f"ERROR: {exc}")
    print(f"LLM backend: {client.cfg.provider} ({client.cfg.model})")
```

(The gate-status block and `AsyncExitStack` that follow are unchanged. `os` and `sys` remain imported and used.)

- [ ] **Step 8: Confirm the module imports and the full file is consistent**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -c "import agent_loop; assert hasattr(agent_loop, 'agent_turn'); import inspect; assert 'anthropic' not in inspect.getsource(agent_loop).lower().replace('anthropic_api_key',''); print('ok')"`
Expected: prints `ok` (module imports cleanly; no stray `anthropic` SDK references remain besides the env-var name, which this check tolerates).

If the assertion about `anthropic` trips on the module docstring (line `|- anthropic.AsyncAnthropic`), edit that one docstring line to read `|- llm_client.LLMClient (OpenAI-compatible)` and re-run.

- [ ] **Step 9: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_turn.py
git commit -m "feat(agent): drive the loop through the pluggable LLM client

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Full regression + Groq end-to-end smoke

**Files:**
- Modify: `docs/superpowers/plans/2026-06-21-pluggable-llm-backend.md` (record the smoke result below)

**Interfaces:**
- Consumes: all prior tasks.

- [ ] **Step 1: Run the new unit tests**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest tests/test_llm_client.py tests/test_agent_turn.py -v`
Expected: all PASS (10 + 2 = 12).

- [ ] **Step 2: Run the full suite for regressions**

Run: `cd mcp_harness && PYTHONPATH=.:tests ./.venv/bin/python -m pytest -q`
Expected: all PASS. Prior baseline was 82; this adds 12 → expect 94 passed. The run takes ~3 minutes (engine-backed tests invoke the real C++/Java backends). If anything fails, do NOT mark done — report the failing test names and output.

- [ ] **Step 3: Groq end-to-end smoke (requires a free `GROQ_API_KEY`)**

This verifies the real backend swap and doubles as the gate end-to-end smoke that Claude billing blocked. Run:

```bash
cd mcp_harness && PYTHONUTF8=1 LLM_PROVIDER=groq GROQ_API_KEY="$GROQ_API_KEY" \
  ./.venv/bin/python agent_loop.py
```

At the `you>` prompt, type: `design a quadruped (four legs, head, tail)`.
Confirm in the transcript:
  1. Startup printed `LLM backend: groq (llama-3.3-70b-versatile)`.
  2. A `[tool] predict_tree_feasibility(...)` call appears before the first compile.
  3. The design proceeds to compile and lint.
Type `exit` to quit.

If `GROQ_API_KEY` is not available, record this step as "skipped (no Groq key)".

- [ ] **Step 4: Record the smoke result**

Edit this plan file, replacing the line below with the observed outcome:

`Groq smoke result (Step 3): skipped (no Groq key / non-interactive) — GROQ_API_KEY not set in environment; interactive REPL not available in CI context. Full regression: 94/94 passed (prior baseline 82 + 12 new).`

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add docs/superpowers/plans/2026-06-21-pluggable-llm-backend.md
git commit -m "docs(llm): record Groq end-to-end smoke result

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review Notes

- **Spec coverage:** single OpenAI-compatible client (Tasks 1-2); non-streaming `run_turn` (Task 2); provider-preset registry + env resolution incl. overrides, ollama-no-key, unknown-provider, missing-key (Task 1) — spec §4.1/§5; default `claude` (Task 1 test + §3); tool conversion (Task 1) — spec §6; OpenAI message-format turn loop with assistant `tool_calls` and `role:"tool"` results, bad-JSON recovery, `MAX_AGENT_STEPS` cap (Task 3) — spec §6/§7; `main()` provider-aware construction + startup print, removal of the hardcoded `ANTHROPIC_API_KEY` check (Task 3) — spec §4.2/§7; network-free unit tests with fakes (Tasks 1-3) — spec §8; regression + Groq smoke (Task 4) — spec §8/§10; `anthropic` left installed (Global Constraints) — spec §9.
- **Placeholder scan:** the only fill-ins are runtime values (the Groq smoke result in Task 4 Step 4, the `openai` version in Task 1 Step 0) — genuine runtime observations, not unfinished spec.
- **Type consistency:** `LLMConfig(provider, model, base_url, api_key, max_tokens, temperature)` is defined in Task 1 and constructed identically in Task 2's test; `LLMClient(cfg)` / `from_env()` / `run_turn(system, messages, tools) -> TurnResult` consistent across Tasks 2-3; `TurnResult(text, tool_calls, finish_reason)` fields consistent; tool-call attribute access `tc.id` / `tc.function.name` / `tc.function.arguments` consistent between `run_turn` output (Task 2) and `agent_turn` consumption (Task 3); `Backend.tools` consistent between `connect_servers` (produces) and `agent_turn` (consumes).
- **Deferred (out of scope per spec):** streaming, the template benchmark, removing the `anthropic` SDK, prompt tuning for weaker models.

# Pluggable LLM Backend for the Agent Orchestrator (Design Spec)

**Date:** 2026-06-21
**Status:** Approved (brainstorming) — ready for implementation plan
**Component:** Tier 2 orchestrator (`mcp_harness/agent_loop.py`)

## 1. Goal

Let the agent orchestrator run against any OpenAI-compatible LLM endpoint —
Groq, Google Gemini, local Ollama, or Anthropic's compatibility endpoint —
selected by environment variable, so the project can run on a free or cheap
backend instead of the paid native Anthropic API. The default backend stays
Claude (no behavior change unless opted in); verification runs on Groq.

**Motivation:** the native Anthropic API requires paid credits (it blocked the
gate end-to-end smoke). All viable free/cheap providers (Groq's free tier,
Gemini's free tier, local Ollama) expose an OpenAI-compatible chat-completions
API, so a single OpenAI-format client reaches all of them, and Claude too via
its compat endpoint.

## 2. Background / current state

- `agent_loop.py` hardcodes the native Anthropic SDK: `from anthropic import
  AsyncAnthropic`, `client.messages.stream(...)`, Anthropic content-block
  message format (`tool_use` / `tool_result` blocks), `stop_reason`, and the
  `system=` parameter.
- MCP tools are discovered dynamically and currently mapped to Anthropic's
  `{"name", "description", "input_schema"}` tool shape in `connect_servers`.
- The whole message history is Anthropic-shaped. Making the history
  OpenAI-shaped is the core of the change; once it is, every OpenAI-compatible
  provider is the same code path.
- Installed SDKs: `anthropic` only. `openai` is NOT yet installed.

## 3. Decisions (from brainstorming)

- **Single OpenAI-compatible client.** One code path via the `openai` SDK with a
  configurable `base_url`; Claude is reached through Anthropic's OpenAI-compatible
  endpoint. (Not an adapter pattern; not a Claude-removal.)
- **Non-streaming.** Each turn is one complete response; tool calls arrive whole,
  uniform across providers. The REPL prints the full assistant message at once.
- **Provider-preset registry via env vars** (not a config file).
- **Default provider = `claude`** (backward-compatible). Verification runs on Groq.
- **First provider wired + verified = Groq (Llama 3.3 70B).**
- **Quality benchmarking deferred** to a follow-up.

## 4. Components

One new file; focused edits to `agent_loop.py`. New dependency: `openai` (added
to `mcp_harness/.venv`).

### 4.1 New: `mcp_harness/llm_client.py`

One responsibility: turn a `(system, messages, tools)` request into a completed
turn against any OpenAI-compatible endpoint. Knows nothing about origami or MCP
routing.

- `PROVIDERS: dict[str, dict]` — preset registry:

  ```python
  PROVIDERS = {
      "groq":   {"base_url": "https://api.groq.com/openai/v1",
                 "default_model": "llama-3.3-70b-versatile", "api_key_env": "GROQ_API_KEY"},
      "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
                 "default_model": "gemini-2.0-flash", "api_key_env": "GEMINI_API_KEY"},
      "ollama": {"base_url": "http://localhost:11434/v1",
                 "default_model": "qwen2.5:7b", "api_key_env": None},
      "claude": {"base_url": "https://api.anthropic.com/v1/",
                 "default_model": "claude-sonnet-4-6", "api_key_env": "ANTHROPIC_API_KEY"},
  }
  ```

- `LLMConfig` (dataclass) + `LLMConfig.from_env()` — resolves provider, model,
  base_url, api_key, max_tokens, temperature from env (see §5). Raises on unknown
  provider or missing required key.
- `tools_to_openai(mcp_tools) -> list[dict]` — pure conversion of MCP tools
  (`name`, `description`, `inputSchema`) to OpenAI
  `{"type": "function", "function": {"name", "description", "parameters"}}`.
- `TurnResult` (dataclass) — `text: str`, `tool_calls: list`, `finish_reason: str`.
- `LLMClient` — wraps `openai.AsyncOpenAI(base_url=..., api_key=...)`; method
  `async run_turn(system, messages, tools) -> TurnResult` (non-streaming).
  Classmethod/factory `LLMClient.from_config(cfg)` or `from_env()`.

### 4.2 Modified: `mcp_harness/agent_loop.py`

- Remove `from anthropic import AsyncAnthropic`; import `llm_client`.
- `connect_servers`: build OpenAI-format tools via `tools_to_openai`; rename the
  `Backend.anthropic_tools` field to `tools`.
- `agent_turn`: rewrite to call `client.run_turn(...)` and operate in OpenAI
  message format (see §6).
- `main()`: build the client via `LLMConfig.from_env()` / `LLMClient`; replace the
  hardcoded `ANTHROPIC_API_KEY` check with provider-aware key validation (done by
  `from_env`); print the active provider + model.

The `anthropic` SDK becomes unused; it stays installed (removal is out of scope).
The gate (`ensure_gate_trained`), MCP servers, and tool routing are untouched.

## 5. Configuration

`LLMConfig.from_env()` reads:

| Env var | Meaning | Default |
|---|---|---|
| `LLM_PROVIDER` | preset name (groq/gemini/ollama/claude) | `claude` |
| `LLM_MODEL` | override the preset's default model | preset default |
| `LLM_BASE_URL` | override the endpoint (custom/self-hosted) | preset base_url |
| `LLM_MAX_TOKENS` | max output tokens | `4096` |
| `LLM_TEMPERATURE` | sampling temperature | `0.0` |

API key: read from the selected preset's `api_key_env`. For `ollama`
(`api_key_env is None`) the client sends a dummy non-empty `"ollama"` string,
since the OpenAI SDK rejects an empty key.

Errors (fail fast at startup):
- Unknown `LLM_PROVIDER` → error listing valid names.
- Missing key for a provider that requires one → error naming the exact env var
  (e.g. "set GROQ_API_KEY").

Groq run: `LLM_PROVIDER=groq GROQ_API_KEY=… ./.venv/bin/python agent_loop.py`.

## 6. Data flow (the rewritten turn loop)

Message history (OpenAI-shaped):
- user: `{"role": "user", "content": "..."}`
- assistant: `{"role": "assistant", "content": text_or_None, "tool_calls": [...]}`
  (recorded verbatim from the response message)
- tool result: `{"role": "tool", "tool_call_id": tc.id, "content": output_string}`

`agent_turn` (≤ `MAX_AGENT_STEPS`):

```
result = await client.run_turn(SYSTEM_PROMPT, messages, backend.tools)
print(result.text)
append assistant message (content + tool_calls) to history
if not result.tool_calls:        # finish_reason != "tool_calls"
    return
for tc in result.tool_calls:
    try:
        args = json.loads(tc.function.arguments)
    except json.JSONDecodeError as exc:
        output = f"ERROR: bad tool arguments for {tc.function.name}: {exc}"
    else:
        output = await run_tool(backend, tc.function.name, args)
    append {"role": "tool", "tool_call_id": tc.id, "content": output}
loop
```

`run_turn` internals:

```python
resp = await self._client.chat.completions.create(
    model=self.model,
    messages=[{"role": "system", "content": system}] + messages,
    tools=tools, tool_choice="auto",
    max_tokens=self.max_tokens, temperature=self.temperature)
msg = resp.choices[0].message
return TurnResult(text=msg.content or "",
                  tool_calls=msg.tool_calls or [],
                  finish_reason=resp.choices[0].finish_reason)
```

The `MAX_AGENT_STEPS` safety cap and "leave history valid on cap" behavior are
preserved.

## 7. Error handling

| Condition | Behavior |
|---|---|
| Unknown `LLM_PROVIDER` | startup error listing valid names |
| Missing required API key | startup error naming the exact env var |
| Malformed tool-call JSON from model | `run_tool` path returns `ERROR: bad tool arguments…` as the tool result; model can recover |
| API error (rate limit, billing, network) | caught in `agent_turn`, printed, REPL stays alive |
| Ollama empty key | client sends dummy `"ollama"` |

## 8. Testing

Network-free unit tests in `mcp_harness/tests/test_llm_client.py`:
- `LLMConfig.from_env`: groq/gemini/ollama/claude resolve to correct
  base_url+model+key; `LLM_MODEL` and `LLM_BASE_URL` overrides apply; unknown
  provider raises; missing key raises naming the env var; ollama needs no key.
- `tools_to_openai`: an MCP-style tool converts to the exact OpenAI function shape.
- `run_turn` with a fake injected client: canned response objects (one with
  tool_calls, one without) → `TurnResult` fields extracted correctly.
- `agent_turn` with a fake `LLMClient` + fake backend: first turn returns a tool
  call, second returns plain text → assert the tool executed and a `role:"tool"`
  message with the correct `tool_call_id` was appended, then the loop ended.

Manual smoke (documented, key-gated) — run on Groq:
`LLM_PROVIDER=groq GROQ_API_KEY=… ./.venv/bin/python agent_loop.py`, request a
quadruped, confirm tool calls fire (including `predict_tree_feasibility` before
the compile) and a design completes. Doubles as the gate end-to-end smoke that
Claude billing previously blocked.

Regression: the existing 82 tests stay green (gate/MCP code untouched).

## 9. Out of scope (YAGNI)

- Streaming output.
- The template quality benchmark (`benchmark_templates.py` across backends) —
  a separate follow-up.
- Removing the now-unused `anthropic` SDK.
- System-prompt tuning for weaker/local models.

## 10. Success criteria

- With no env changes, the loop runs against Claude as before (via the new client).
- `LLM_PROVIDER=groq` + `GROQ_API_KEY` runs the full draft→gate→compile→lint loop
  on Groq, with correct tool calls.
- All network-free unit tests pass; the existing 82 tests still pass.

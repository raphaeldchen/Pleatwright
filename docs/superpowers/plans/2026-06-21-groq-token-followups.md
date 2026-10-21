# Groq Token-Limit Follow-ups Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the orchestrator's per-request token footprint by trimming consumed FOLD blobs from history (#3), then make the loop survive Groq's transient 12K-TPM 413 by backing off and retrying (#2).

**Architecture:** #3 adds a pure, idempotent `_trim_consumed_blobs` helper to `agent_loop.py`, called at the top of each step in `agent_turn`; it placeholders every oversized tool-result/tool-call-argument except the single newest one. #2 wraps the `chat.completions.create` call in `LLMClient.run_turn` with a retry loop driven by a pure `_transient_tpm_delay` helper that keys on the response *body* (not the status code). The two changes are independent and live in different files.

**Tech Stack:** Python 3.14, `asyncio`, `openai` SDK (`AsyncOpenAI`, `APIStatusError`), `pytest` + `monkeypatch`, `httpx` (test-only, for constructing real `APIStatusError`s).

## Global Constraints

- Do NOT change agent behavior or output quality — trimming only removes data the agent never reasons over (raw geometry); the lint verdict drives decisions.
- Keep the file separation: `llm_client.py` knows HTTP; `agent_loop.py` does not. The backoff lives in `run_turn`, the trimming in `agent_turn`.
- Trim threshold default: `2000` chars. Keep-newest default: `1`.
- Backoff: key on body `code == "rate_limit_exceeded"` AND `type == "tokens"`; honor `retry-after` header else default `60.0`s; cap at `3` attempts total; re-raise everything else immediately.
- All new tests must be network-free (fakes/monkeypatch only).
- Run tests from `mcp_harness/`: `cd mcp_harness && ./.venv/bin/python -m pytest <path> -v`.

---

## File Structure

- Modify: `mcp_harness/agent_loop.py` — add `_trim_consumed_blobs` + `_trim_arg_json`; call the trim at the top of the `agent_turn` step loop.
- Modify: `mcp_harness/llm_client.py` — add `import asyncio`, import `APIStatusError`, add `_transient_tpm_delay`, wrap the create call in `run_turn`.
- Test: `mcp_harness/tests/test_agent_turn.py` — unit tests for trimming + an integration test through `agent_turn`.
- Test: `mcp_harness/tests/test_llm_client.py` — unit tests for `_transient_tpm_delay` + the retry loop.

---

## Task 1: History-trim helpers (`_trim_consumed_blobs`, `_trim_arg_json`)

**Files:**
- Modify: `mcp_harness/agent_loop.py` (add two module-level functions near `_preview`, ~line 382)
- Test: `mcp_harness/tests/test_agent_turn.py`

**Interfaces:**
- Consumes: nothing (pure functions over OpenAI-format message dicts).
- Produces:
  - `_trim_consumed_blobs(messages: list[dict], threshold: int = 2000, keep_newest: int = 1) -> None` — mutates `messages` in place.
  - `_trim_arg_json(arguments: str, threshold: int = 2000) -> str` — returns a trimmed arguments string.

- [ ] **Step 1: Write the failing tests**

Add to the bottom of `mcp_harness/tests/test_agent_turn.py`:

```python
from agent_loop import _trim_consumed_blobs, _trim_arg_json

_BIG = "x" * 3000          # over the 2000-char threshold


def test_trim_keeps_newest_oversized_blob_and_trims_older():
    # Two oversized payloads: the FOLD tool-result (older) and the lint arg (newer).
    msgs = [
        {"role": "tool", "tool_call_id": "c1", "content": _BIG},          # older, trim
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c2", "type": "function",
             "function": {"name": "validate_flat_foldability",
                          "arguments": '{"fold_json_string": "' + _BIG + '"}'}}]},  # newest, keep
    ]
    _trim_consumed_blobs(msgs)
    assert msgs[0]["content"].startswith("[large result omitted")
    assert str(len(_BIG)) in msgs[0]["content"]
    assert msgs[1]["tool_calls"][0]["function"]["arguments"] == '{"fold_json_string": "' + _BIG + '"}'


def test_trim_trims_old_arg_once_newer_blob_exists():
    msgs = [
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "c1", "type": "function",
             "function": {"name": "validate_flat_foldability",
                          "arguments": '{"fold_json_string": "' + _BIG + '"}'}}]},  # older, trim
        {"role": "tool", "tool_call_id": "c2", "content": _BIG},          # newest, keep
    ]
    _trim_consumed_blobs(msgs)
    assert "omitted" in msgs[0]["tool_calls"][0]["function"]["arguments"]
    assert msgs[1]["content"] == _BIG


def test_trim_leaves_small_results_untouched():
    msgs = [
        {"role": "tool", "tool_call_id": "c1", "content": "Pass"},
        {"role": "tool", "tool_call_id": "c2", "content": "ERROR: circles overlap"},
    ]
    before = [dict(m) for m in msgs]
    _trim_consumed_blobs(msgs)
    assert msgs == before


def test_trim_is_idempotent():
    msgs = [
        {"role": "tool", "tool_call_id": "c1", "content": _BIG},
        {"role": "tool", "tool_call_id": "c2", "content": _BIG},
    ]
    _trim_consumed_blobs(msgs)
    once = [dict(m) for m in msgs]
    _trim_consumed_blobs(msgs)
    assert msgs == once


def test_trim_arg_json_replaces_only_oversized_field():
    arguments = '{"fold_json_string": "' + _BIG + '", "keep": "small"}'
    out = _trim_arg_json(arguments)
    data = json.loads(out)
    assert data["keep"] == "small"
    assert "omitted" in data["fold_json_string"]
    assert str(len(_BIG)) in data["fold_json_string"]


def test_trim_arg_json_handles_non_json():
    out = _trim_arg_json("{not valid json " + _BIG)
    assert "omitted" in out
```

(Note: `json` is already imported at the top of `agent_loop.py` and re-exported into the test module's namespace via `import agent_loop`; the test file imports `json` transitively through its own use. If `json` is not in scope in the test module, add `import json` at the top of the test file.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_agent_turn.py -v`
Expected: FAIL with `ImportError: cannot import name '_trim_consumed_blobs' from 'agent_loop'`.

- [ ] **Step 3: Implement the helpers**

Add to `mcp_harness/agent_loop.py` just above `def _preview(` (~line 382):

```python
def _trim_arg_json(arguments: str, threshold: int = 2000) -> str:
    """Replace oversized string fields inside a tool-call arguments JSON string
    with a short marker, keeping all other fields and valid JSON. Falls back to a
    bare placeholder when the arguments are not parseable JSON."""
    try:
        data = json.loads(arguments)
    except (json.JSONDecodeError, TypeError):
        return f"[omitted — {len(arguments)} chars, lint already run]"
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, str) and len(value) > threshold:
                data[key] = f"[omitted — {len(value)} chars, lint already run]"
        return json.dumps(data)
    return json.dumps(f"[omitted — {len(arguments)} chars, lint already run]")


def _trim_consumed_blobs(
    messages: list[dict], threshold: int = 2000, keep_newest: int = 1
) -> None:
    """Drop dead-weight geometry from history in place.

    The FOLD JSON (~40 KB) rides in history twice -- as a tool result and as the
    echoed `fold_json_string` argument to validate_flat_foldability -- and is pure
    dead weight once linted (the agent reasons over the lint verdict, not raw
    coordinates). We replace every oversized tool-result content and tool-call
    argument with a compact placeholder, EXCEPT the single most-recent one
    (`keep_newest`), which the agent may still need to lint or report. Placeholders
    fall under `threshold`, so this is idempotent; only `content`/`arguments` text
    is edited, so tool_call_id<->tool pairing stays valid.
    """
    # Locate oversized payloads in chronological order.
    # kind "tool" -> (i, None); kind "arg" -> (i, tool_call_index)
    locations: list[tuple[str, int, int | None]] = []
    for i, msg in enumerate(messages):
        role = msg.get("role")
        if role == "tool":
            content = msg.get("content")
            if isinstance(content, str) and len(content) > threshold:
                locations.append(("tool", i, None))
        elif role == "assistant":
            for j, tc in enumerate(msg.get("tool_calls") or []):
                args = tc.get("function", {}).get("arguments")
                if isinstance(args, str) and len(args) > threshold:
                    locations.append(("arg", i, j))

    to_trim = locations[:-keep_newest] if keep_newest else locations
    for kind, i, j in to_trim:
        if kind == "tool":
            n = len(messages[i]["content"])
            messages[i]["content"] = (
                f"[large result omitted to save context — {n} chars; "
                "already consumed by a later step. Recompile if you need "
                "the geometry again.]"
            )
        else:
            tc = messages[i]["tool_calls"][j]
            tc["function"]["arguments"] = _trim_arg_json(
                tc["function"]["arguments"], threshold)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_agent_turn.py -v`
Expected: PASS (all tests, including the two pre-existing ones).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_turn.py
git commit -m "feat(agent): trim consumed FOLD blobs from history

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Wire trimming into the `agent_turn` step loop

**Files:**
- Modify: `mcp_harness/agent_loop.py:331` (top of the `for step in range(...)` loop in `agent_turn`)
- Test: `mcp_harness/tests/test_agent_turn.py`

**Interfaces:**
- Consumes: `_trim_consumed_blobs` (Task 1), the existing `_FakeLLM` test fake, `TurnResult`.
- Produces: nothing new (behavioral change to `agent_turn`).

- [ ] **Step 1: Write the failing test**

Add to `mcp_harness/tests/test_agent_turn.py`:

```python
def test_agent_turn_trims_old_fold_after_consumption(monkeypatch):
    # Step 1: model calls a compile tool. Step 2: model calls the linter. Step 3: done.
    # The FOLD tool result from step 1 must be trimmed by the time step 3 runs,
    # while the most-recent oversized blob is preserved.
    tc_compile = SimpleNamespace(
        id="c1",
        function=SimpleNamespace(name="draft_and_compile_full_base", arguments="{}"))
    tc_lint = SimpleNamespace(
        id="c2",
        function=SimpleNamespace(name="validate_flat_foldability",
                                 arguments='{"fold_json_string": "' + _BIG + '"}'))
    results = [
        TurnResult(text="", tool_calls=[tc_compile], finish_reason="tool_calls"),
        TurnResult(text="", tool_calls=[tc_lint], finish_reason="tool_calls"),
        TurnResult(text="done", tool_calls=[], finish_reason="stop"),
    ]
    client = _FakeLLM(results)
    backend = SimpleNamespace(tools=[])

    async def fake_run_tool(backend_, name, args):
        if name == "draft_and_compile_full_base":
            return _BIG            # the FOLD blob
        return "Pass"

    monkeypatch.setattr(agent_loop, "run_tool", fake_run_tool)

    messages = [{"role": "user", "content": "design a quadruped"}]
    asyncio.run(agent_loop.agent_turn(client, backend, messages))

    # The FOLD tool result (consumed by the lint call) is now a placeholder.
    fold_tool_msg = next(m for m in messages
                         if m.get("role") == "tool" and m.get("tool_call_id") == "c1")
    assert fold_tool_msg["content"].startswith("[large result omitted")
    # tool_call_id<->tool pairing is still intact for every tool message.
    tool_ids = {m["tool_call_id"] for m in messages if m.get("role") == "tool"}
    assert tool_ids == {"c1", "c2"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_agent_turn.py::test_agent_turn_trims_old_fold_after_consumption -v`
Expected: FAIL — `fold_tool_msg["content"]` still equals `_BIG` (trimming not wired in yet).

- [ ] **Step 3: Wire the trim into `agent_turn`**

In `mcp_harness/agent_loop.py`, change the top of the step loop (currently line 331-332):

```python
    for step in range(1, MAX_AGENT_STEPS + 1):
        result = await client.run_turn(SYSTEM_PROMPT, messages, backend.tools)
```

to:

```python
    for step in range(1, MAX_AGENT_STEPS + 1):
        # Drop dead-weight geometry from earlier steps before re-sending history
        # ("full now, trimmed later"): the newest oversized blob is kept so the
        # current step can still lint/report it.
        _trim_consumed_blobs(messages)
        result = await client.run_turn(SYSTEM_PROMPT, messages, backend.tools)
```

- [ ] **Step 4: Run the full agent-turn suite to verify it passes**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_agent_turn.py -v`
Expected: PASS (all tests, including the two original ones — trimming is a no-op on their small histories).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_turn.py
git commit -m "feat(agent): trim history at the top of each agent_turn step

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: TPM-detection helper (`_transient_tpm_delay`)

**Files:**
- Modify: `mcp_harness/llm_client.py` (add `import asyncio` near line 10; import `APIStatusError`; add the helper near the other module functions, ~line 98)
- Test: `mcp_harness/tests/test_llm_client.py`

**Interfaces:**
- Consumes: `openai.APIStatusError` instances.
- Produces: `_transient_tpm_delay(exc, default: float = 60.0) -> float | None` — returns seconds to wait for a transient TPM 413, or `None` if the error is not a transient TPM rate-limit (caller re-raises).

- [ ] **Step 1: Write the failing tests**

Add to `mcp_harness/tests/test_llm_client.py`:

```python
import httpx
import openai
from llm_client import _transient_tpm_delay


def _status_error(body, headers=None, status=413):
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp = httpx.Response(status, headers=headers or {}, request=req)
    return openai.APIStatusError("err", response=resp, body=body)


def test_tpm_delay_detects_transient_and_uses_retry_after():
    exc = _status_error(
        {"error": {"code": "rate_limit_exceeded", "type": "tokens"}},
        headers={"retry-after": "5"})
    assert _transient_tpm_delay(exc) == 5.0


def test_tpm_delay_defaults_when_no_header():
    exc = _status_error({"error": {"code": "rate_limit_exceeded", "type": "tokens"}})
    assert _transient_tpm_delay(exc, default=60.0) == 60.0


def test_tpm_delay_accepts_flat_body():
    exc = _status_error({"code": "rate_limit_exceeded", "type": "tokens"})
    assert _transient_tpm_delay(exc, default=42.0) == 42.0


def test_tpm_delay_none_for_context_overflow():
    exc = _status_error({"error": {"code": "context_length_exceeded", "type": "tokens"}})
    assert _transient_tpm_delay(exc) is None


def test_tpm_delay_none_for_request_rate_limit():
    # rate_limit_exceeded but type "requests" (RPM, not TPM) -> not our case.
    exc = _status_error({"error": {"code": "rate_limit_exceeded", "type": "requests"}})
    assert _transient_tpm_delay(exc) is None


def test_tpm_delay_none_for_missing_body():
    req = httpx.Request("POST", "http://x")
    exc = openai.APIStatusError("err", response=httpx.Response(413, request=req), body=None)
    assert _transient_tpm_delay(exc) is None


def test_tpm_delay_default_on_unparseable_header():
    exc = _status_error(
        {"error": {"code": "rate_limit_exceeded", "type": "tokens"}},
        headers={"retry-after": "Wed, 21 Oct 2099 07:28:00 GMT"})
    assert _transient_tpm_delay(exc, default=60.0) == 60.0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_llm_client.py -k tpm_delay -v`
Expected: FAIL with `ImportError: cannot import name '_transient_tpm_delay' from 'llm_client'`.

- [ ] **Step 3: Implement the helper**

In `mcp_harness/llm_client.py`, add `import asyncio` under `import os` (line 10), and change the openai import (line 12) to also bring in the error type:

```python
import asyncio
import os
from dataclasses import dataclass
from openai import AsyncOpenAI, APIStatusError
```

Then add this function just above `@dataclass class TurnResult` (~line 100):

```python
def _transient_tpm_delay(exc: APIStatusError, default: float = 60.0) -> float | None:
    """Seconds to wait before retrying a transient tokens-per-minute rate-limit,
    or None if `exc` is not that case (caller should re-raise).

    Groq signals a TPM limit as HTTP 413 (not 429), so we key on the response
    BODY -- code 'rate_limit_exceeded' AND type 'tokens' -- which stays correct
    across providers and distinguishes the transient TPM window from a permanent
    context-length overflow. Honors the `retry-after` header when present (and
    numeric), else falls back to `default`.
    """
    body = getattr(exc, "body", None)
    if not isinstance(body, dict):
        return None
    err = body.get("error", body)
    if not isinstance(err, dict):
        return None
    if err.get("code") != "rate_limit_exceeded" or err.get("type") != "tokens":
        return None

    retry_after = None
    resp = getattr(exc, "response", None)
    if resp is not None:
        retry_after = resp.headers.get("retry-after")
    try:
        return float(retry_after) if retry_after is not None else default
    except (TypeError, ValueError):
        return default
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_llm_client.py -k tpm_delay -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/llm_client.py mcp_harness/tests/test_llm_client.py
git commit -m "feat(llm): _transient_tpm_delay detects Groq's 413 TPM limit

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Retry loop in `run_turn`

**Files:**
- Modify: `mcp_harness/llm_client.py:124-144` (`LLMClient.run_turn`)
- Test: `mcp_harness/tests/test_llm_client.py`

**Interfaces:**
- Consumes: `_transient_tpm_delay` (Task 3), `asyncio.sleep`, `APIStatusError`.
- Produces: no signature change to `run_turn`; adds bounded retry behavior (max 3 attempts).

- [ ] **Step 1: Write the failing tests**

Add to `mcp_harness/tests/test_llm_client.py` (reuses `_make_client`, `_fake_response`, `_status_error`):

```python
class _FlakyCompletions:
    """Raises queued exceptions in order, then returns `resp` for every later call."""

    def __init__(self, raises, resp):
        self._raises = list(raises)
        self._resp = resp
        self.calls = 0

    async def create(self, **kwargs):
        self.calls += 1
        if self._raises:
            exc = self._raises.pop(0)
            if exc is not None:
                raise exc
        return self._resp


def _install_flaky(client, raises, resp):
    comp = _FlakyCompletions(raises, resp)
    client._client = SimpleNamespace(chat=SimpleNamespace(completions=comp))
    return comp


def test_run_turn_retries_transient_tpm_then_succeeds(monkeypatch):
    slept = []

    async def fake_sleep(seconds):
        slept.append(seconds)

    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)

    client = _make_client()
    tpm = _status_error(
        {"error": {"code": "rate_limit_exceeded", "type": "tokens"}},
        headers={"retry-after": "1"})
    comp = _install_flaky(client, [tpm], _fake_response("ok", None, "stop"))

    result = asyncio.run(client.run_turn("SYS", [], []))
    assert result.text == "ok"
    assert comp.calls == 2          # one failure + one success
    assert slept == [1.0]           # honored retry-after


def test_run_turn_reraises_context_overflow_without_sleeping(monkeypatch):
    slept = []
    monkeypatch.setattr(llm_client.asyncio, "sleep",
                        lambda s: slept.append(s))  # never awaited
    client = _make_client()
    overflow = _status_error({"error": {"code": "context_length_exceeded",
                                        "type": "tokens"}})
    _install_flaky(client, [overflow], _fake_response("never", None, "stop"))

    with pytest.raises(openai.APIStatusError):
        asyncio.run(client.run_turn("SYS", [], []))
    assert slept == []


def test_run_turn_gives_up_after_three_attempts(monkeypatch):
    async def fake_sleep(seconds):
        pass

    monkeypatch.setattr(llm_client.asyncio, "sleep", fake_sleep)
    client = _make_client()
    tpm = _status_error({"error": {"code": "rate_limit_exceeded", "type": "tokens"}})
    comp = _install_flaky(client, [tpm, tpm, tpm], _fake_response("x", None, "stop"))

    with pytest.raises(openai.APIStatusError):
        asyncio.run(client.run_turn("SYS", [], []))
    assert comp.calls == 3          # capped at 3 attempts
```

Add `import llm_client` at the top of the test file if not already present (the existing file imports symbols from `llm_client` but the monkeypatch targets the module object — add `import llm_client` near the other imports).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_llm_client.py -k run_turn_retries -v`
Expected: FAIL — without the retry loop, the first `tpm` exception propagates out of `run_turn` (no retry, `comp.calls == 1`).

- [ ] **Step 3: Add the retry loop to `run_turn`**

In `mcp_harness/llm_client.py`, replace the body of `run_turn` from the `kwargs` block through the `resp = await ...` line (currently lines 128-137) with:

```python
        kwargs: dict = dict(
            model=self.model,
            messages=[{"role": "system", "content": system}] + messages,
            tools=tools,
            tool_choice="auto",
            max_tokens=self.max_tokens,
        )
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        # Groq's free tier enforces a 12K tokens/MINUTE cap and signals it as a
        # transient HTTP 413. Retry only that case (waiting for the window to
        # reset), capped so a permanent oversize request still fails cleanly. The
        # SDK's max_retries does not cover 413 and backs off far less than 60s.
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                resp = await self._client.chat.completions.create(**kwargs)
                break
            except APIStatusError as exc:
                delay = _transient_tpm_delay(exc)
                if delay is None or attempt == max_attempts:
                    raise
                await asyncio.sleep(delay)
```

The existing lines below (`choice = resp.choices[0]` onward) are unchanged.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/test_llm_client.py -v`
Expected: PASS (all tests, old and new).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/llm_client.py mcp_harness/tests/test_llm_client.py
git commit -m "feat(llm): retry transient Groq TPM 413 with backoff in run_turn

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Full-suite regression check

**Files:** none (verification only).

- [ ] **Step 1: Run the whole harness test suite**

Run: `cd mcp_harness && ./.venv/bin/python -m pytest tests/ -q`
Expected: PASS (no regressions in the existing suite). If any pre-existing test is environment-gated (e.g. needs the Oriedita jar or the `.so`) and was already skipping/failing before this work, note it but do not treat it as introduced by these changes.

- [ ] **Step 2: Update the project memory**

Update `groq-token-limit-followups.md` to mark #3 and #2 as BUILT (with the branch/commit), and adjust `MEMORY.md`'s pointer line accordingly. (This is a memory edit, not a code commit.)

---

## Self-Review

**Spec coverage:**
- #3 trim helper + keep-newest + placeholder text + idempotency + arg/tool both → Task 1. ✓
- #3 "per step, before run_turn" timing → Task 2. ✓
- #2 body-keyed detection (413, code+type), retry-after, default 60s, transient-vs-permanent → Task 3. ✓
- #2 cap at 3 attempts, re-raise non-transient, lives in run_turn → Task 4. ✓
- Testing plan (both files, network-free) → Tasks 1-4. ✓
- Deferred templates-to-tool redesign → intentionally not planned (out of scope per spec). ✓

**Placeholder scan:** no TBD/TODO; all code blocks complete. ✓

**Type consistency:** `_trim_consumed_blobs`/`_trim_arg_json`/`_transient_tpm_delay` signatures match between definition, tests, and call sites. The retry loop uses `_transient_tpm_delay` exactly as defined in Task 3. ✓

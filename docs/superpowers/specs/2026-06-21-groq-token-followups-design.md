# Groq token-limit follow-ups: history trimming + 413 backoff

**Date:** 2026-06-21
**Status:** Approved (brainstorm)
**Scope:** Two follow-ups to survive/avoid Groq free tier's 12K tokens-per-minute
(TPM) cap in the Tier 2 orchestrator. Build #3 (history trimming) first, then #2
(413 backoff).

## Background

The pluggable LLM backend (commit `d5d8f5e`) runs `agent_loop.py` on any
OpenAI-compatible provider, selected by `LLM_PROVIDER`. The Anthropic key is out
of credits, so live runs use Groq's free tier. A multi-turn smoke crashed when a
later turn exceeded Groq's **12K tokens/MINUTE** cap: the API returned `HTTP 413`
with body `code: rate_limit_exceeded`, `type: tokens`.

Two root issues, addressed independently:

- **#3 (efficiency — do first):** conversation history grows unbounded. The worst
  offender is the FOLD JSON (~40 KB): `draft_and_compile_full_base` returns it as
  a `tool` message, and the agent then echoes the SAME blob as the
  `fold_json_string` argument to `validate_flat_foldability`. So it sits in
  history TWICE and persists on every subsequent turn, though the FOLD is dead
  weight once linted.
- **#2 (robustness — do second):** even with a smaller footprint, a request can
  still trip the per-minute window. The loop should back off and retry the
  transient case instead of crashing.

## Design goal

Reduce token usage as much as possible **without changing agent behavior or
output quality.** The raw FOLD geometry is only ever used to (a) feed the linter
and (b) report to the user. The agent reasons over the lint *verdict*
("Pass" / "vertex 45 violates Kawasaki"), never over the raw vertex coordinates.
So a linted FOLD blob is pure dead weight and can be dropped safely.

---

## Follow-up 3: History trimming

### Component

A pure helper in `agent_loop.py`:

```python
_trim_consumed_blobs(messages, threshold=2000, keep_newest=1) -> None
```

Called once at the **top of each iteration** in `agent_turn`, immediately before
`client.run_turn(...)`. Mutates `messages` in place ("full now, trimmed later":
the turn that produces a blob sees it in full; trimming happens on a later step).

### What counts as an oversized payload

1. A `role:"tool"` message whose `content` string length exceeds `threshold`.
2. Any single `tool_calls[i].function.arguments` string in an assistant message
   whose length exceeds `threshold` (the echoed FOLD lint argument).

### Algorithm

1. Walk `messages` in order, recording every oversized payload location (tool
   result content, or a specific tool-call argument).
2. Leave the **single most-recent** oversized payload untouched (`keep_newest=1`).
3. Replace every older oversized payload with a compact placeholder:
   - Tool result content →
     `"[large result omitted to save context — {n} chars; already consumed by a later step. Recompile if you need the geometry again.]"`
   - Tool-call argument → re-serialize the arguments JSON with only the oversized
     string field(s) replaced by `"[omitted — {n} chars, lint already run]"`,
     keeping all other argument fields intact and the JSON valid. If the argument
     string is not parseable JSON, fall back to truncating it to a short
     placeholder string.

### Why this preserves quality

- **Keep-newest** guarantees the just-produced FOLD is always still in context to
  be linted and re-emitted as the lint argument, so the produce -> lint -> report
  handshake never breaks. The FOLD-producing step, the lint, and any M/V-repair
  flow all happen within the same autonomous `agent_turn`, where the blob is still
  the newest oversized payload (kept full).
- **Threshold ~2 KB** only ever catches FOLD-sized blobs. Format docs, lint
  verdicts, and error strings are all well under it, so normal results are never
  touched.
- The agent reasons over the lint verdict, not raw geometry, so removing a linted
  FOLD removes nothing the model uses to decide.

### Accepted trade-off

If a *later user turn* asks to re-lint or re-edit a FOLD from an earlier turn,
that blob is now a placeholder and the agent must recompile. Recompiling is
deterministic (same tree -> same FOLD), so the result is identical — just one
extra compile. The placeholder text tells the agent exactly this.

### Safety properties

- Placeholders fall under `threshold`, so the helper is **idempotent** — re-running
  on already-trimmed history is a no-op.
- The helper only edits `content` / `arguments` text; it never adds or removes
  messages, so OpenAI's `tool_call_id` <-> `tool` pairing stays valid.

---

## Follow-up 2: 413 TPM backoff

### Component

A retry loop wrapping the `chat.completions.create(**kwargs)` call inside
`LLMClient.run_turn` (`llm_client.py`). Nothing above the HTTP boundary changes;
`agent_turn` stays oblivious, preserving the spec's file separation (llm_client
knows HTTP; agent_loop does not).

### Detection — key on the body, not the status code

Groq signals a TPM rate-limit as HTTP **413**, not the usual 429. So we inspect
the exception body, not the status code:

- **Transient TPM (retry):** body `code == "rate_limit_exceeded"` and
  `type == "tokens"`. Waiting for the per-minute window to reset makes the retry
  succeed.
- **Permanent (re-raise immediately):** anything else — notably
  `context_length_exceeded`, where retrying is useless.

### Behavior

- Catch `openai.APIStatusError`. Read `.body` defensively (it may be a dict, may
  be nested under an `"error"` key, or may be absent).
- Transient TPM case → honor the `retry-after` response header if present, else
  default to `~60s`; `await asyncio.sleep(...)`; retry.
- Cap at **3 attempts** total, then re-raise so an oversize request still fails
  cleanly.
- Any non-transient body, or attempts exhausted → re-raise unchanged.

The SDK's built-in `max_retries` is insufficient: it does not auto-retry 413, and
its backoff is far shorter than a 60s TPM window.

---

## Testing

### #3 (pure helper — unit tests in `tests/test_agent_turn.py`)

- An older FOLD tool-result is trimmed while the newest oversized blob is kept.
- A lint argument is trimmed once it is no longer the newest oversized blob.
- Sub-threshold tool results are untouched.
- Idempotent: a second pass over trimmed history makes no further change.
- `tool_call_id` <-> `tool` pairing is intact after trimming.

### #2 (retry — unit tests in `tests/test_llm_client.py`)

- Stub `self._client.chat.completions.create` to raise a constructed
  `APIStatusError` with a TPM body, then succeed → assert one sleep + retry +
  success.
- A `context_length_exceeded` body re-raises with no sleep.
- The attempt cap (3) re-raises after exhausting retries.
- Patch `asyncio.sleep` so tests do not actually wait.

---

## Out of scope (future work)

Moving the 4 body-plan templates out of the system prompt into an on-demand tool
(the memory's "secondary, bigger redesign") is deferred. It adds a round-trip per
design and is a separate concern from killing the FOLD dead-weight; the trimming
win is far larger and lower-risk.

Prompt caching does not help here: Groq does not share Anthropic's caching, so the
per-turn fixed cost must be reduced structurally, not cached away.

The quickest non-code unblock for a full multi-turn run remains upgrading Groq to
Dev tier (removes the TPM cap), still far cheaper than Claude.

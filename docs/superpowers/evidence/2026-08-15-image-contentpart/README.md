# Does the OpenAI-compat endpoint accept `image_url` content-parts?

**YES.** Measured 2026-08-15 with one live call. HTTP 200, and the model read the picture.

The question that had been open and explicitly **UNVERIFIED since 2026-08-04**
is closed. The compat endpoint accepts OpenAI-style `image_url` content-parts,
and the shipped `LLMClient.run_turn` carries them with **no change to the
request builder**.

| | |
|---|---|
| **Endpoint** | `https://api.anthropic.com/v1/` (Anthropic's OpenAI-compatibility layer, via `AsyncOpenAI`) |
| **Model** | `claude-sonnet-5` — resolved from the repo `.env` (`LLM_MODEL`), **not** the `PROVIDERS["claude"]` preset default `claude-sonnet-4-6` |
| **SDK** | `openai==2.43.0` (CI-pinned), `chat.completions.create` |
| **Call path** | `llm_client.LLMClient.run_turn(system, messages, tools)` — the same entry point `agent_loop.py:762` uses |
| **Stimulus** | 128×128 PNG, 570 bytes, **exactly 3** filled circles ([`three_circles.png`](three_circles.png)) |
| **Result** | HTTP 200 · `finish_reason='tool_calls'` · `report_circle_count({"count": 3})` |
| **Ground truth** | 3 — **matched** |
| **Live calls spent** | **1** |

Anthropic's published compatibility table says the same thing independently:
for `messages[n].role == "user"`, `content` as an `array` with
`type == "image_url"`, the **`url` sub-field is "Fully supported"**; only
`detail` is ignored.

---

## 1. The request shape that works

A user message whose `content` is a **list of parts** rather than a string.
Everything else — `model`, `tools`, `tool_choice`, `max_tokens` — is unchanged
from an ordinary text turn.

```json
{
  "role": "user",
  "content": [
    {"type": "text",  "text": "How many circles are in this image? ..."},
    {"type": "image_url",
     "image_url": {"url": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAI..."}}
  ]
}
```

Built by the helpers this slice adds to `mcp_harness/llm_client.py`:

```python
msg = llm_client.user_message_with_images("How many circles?", [png_bytes])
result = await client.run_turn(system, [msg], tools)
```

`image_data_uri` / `image_part` / `text_part` / `user_message_with_images` are
the whole feature. **`run_turn` was not touched** — it already forwards
`messages` verbatim, so an image rides in on the message list.

## 2. Verbatim transcript

Reproduce with:

```
cd mcp_harness
RUN_AGENT_SMOKE=1 ./.venv/bin/python probe_image_contentpart.py \
    --save-png ../docs/superpowers/evidence/2026-08-15-image-contentpart/three_circles.png
```

The unedited output of the one call that was made is in
[`probe_transcript.txt`](probe_transcript.txt) — which also records the two
**cosmetic** presentation changes code review landed on the probe afterwards,
and why the transcript was deliberately not regenerated to match them (doing so
costs another paid call, and the captured payload is field-for-field identical
because no `LLM_TEMPERATURE` is set). Its operative lines:

```
  provider   : claude
  base_url   : https://api.anthropic.com/v1/
  model      : claude-sonnet-5
  max_tokens : 4096
  api key    : present
  image      : 128x128 PNG, 570 bytes, 3 circles (ground truth)

--- ONE live call via LLMClient.run_turn ---
  finish_reason : tool_calls
  text          : ''
  tool_call     : report_circle_count({"count": 3})

========================================================================
VERDICT: YES -- the compat endpoint ACCEPTED the image_url content-part (HTTP 200).
         And the model READ the image: reported 3, ground truth 3.
========================================================================
```

## 3. What this proves, and what it does not

**Proven.**

1. The compat endpoint **accepts** `image_url` content-parts with a `data:`
   URI. No 400, no silent strip — a stripped image could not have produced a
   correct count.
2. The image is **actually read**, not merely tolerated. The reply is the right
   number, and the number is not guessable from the prompt: nothing in the text
   says three.
3. Content-parts **coexist with tool use**. The request carried a real function
   tool and `tool_choice="auto"`, exactly the shape the agent loop sends, and
   the model answered *through the tool*.
4. The shipped `run_turn` needs no image awareness.

**Not proven — do not read these into the YES.**

1. **One model, one call.** `claude-sonnet-5` on 2026-08-15. The preset default
   `claude-sonnet-4-6` was **not** exercised, nor was any other provider in
   `PROVIDERS` (Groq/Gemini/Ollama each have their own compat surface).
2. **Nothing about judgment quality.** Counting three high-contrast discs is a
   floor, not evidence that a vision model can assess whether a crease pattern
   folds into the intended animal. That is the actual downstream question and
   this probe says nothing about it.
3. **No multi-image, no large-image, no resolution behaviour.** One 570-byte
   PNG. Token cost and any downscaling threshold are unmeasured.

## 4. Caveats the compat layer imposes (published, not measured here)

- **`detail` is ignored.** `image_part` deliberately does not emit it.
- **`input_audio` and `file` content-parts are ignored** — there is no PDF or
  file-attachment path through this endpoint.
- **Prompt caching is not supported on the compat layer.** An image left in the
  history is re-uploaded and re-billed on **every** turn. Anything that shows a
  model a picture repeatedly should budget for that, or move to the native
  Anthropic Messages API.
- **System/developer messages are hoisted** and concatenated into one leading
  system message. `run_turn` already sends exactly one, so this changes nothing
  here.

## 5. The fallback, if this ever regresses

The compat layer is documented as a testing/comparison surface, not a
production commitment. If `image_url` is ever dropped, the fallback is the
**native Anthropic Messages API**, whose vision input is a different shape —
a content block, not an `image_url` part:

```python
{"type": "image",
 "source": {"type": "base64", "media_type": "image/png", "data": "<b64>"}}
```

That path needs the `anthropic` SDK rather than `openai`, so it is a new client
in `PROVIDERS` terms, not a tweak. **It was not needed.** Recorded so the next
reader does not have to re-derive it.

## 6. Cost discipline

The probe refuses to run without `RUN_AGENT_SMOKE=1` (same gate as
`probe_prompt_ab.py:1012` and `tests/test_reference_smoke.py:30`), makes no
retry, and sweeps no models. `tests/test_llm_client.py` covers its stimulus
generator, redaction, reply parser, and the refusal gate **offline** — the
whole suite remains network-free.

## Files

| Path | What |
|---|---|
| `mcp_harness/llm_client.py` | `sniff_media_type`, `image_data_uri`, `text_part`, `image_part`, `user_message_with_images` (additive) |
| `mcp_harness/probe_image_contentpart.py` | the env-gated one-call probe |
| `mcp_harness/tests/test_llm_client.py` | offline tests, incl. the byte-identical text-path pin |
| `three_circles.png` | the exact stimulus that was sent |
| `probe_transcript.txt` | unedited probe output |

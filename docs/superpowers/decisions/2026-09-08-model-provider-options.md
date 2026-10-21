# Model provider options — measured cost, and what a swap would actually take

**Status: research, deferred by decision.** Not to be acted on until the VLM
tree-authoring spec is finished. Written now because the measurements are in
hand and would be expensive to re-derive.

## What we currently pay, measured not estimated

`run_turn` discarded `resp.usage` until 2026-09-08, so no run in this project's
history could report its own cost. It now can, and the 17-subject ablation is
the first run with a real bill attached.

| arm | calls | prompt | completion | Sonnet 5 |
|---|---|---|---|---|
| none | 17 | 48,535 | 253,851 | $2.64 |
| text | 34 | 131,491 | 401,641 | $4.28 |
| visual | 34 | 157,310 | 378,763 | $4.10 |
| **total** | **85** | **337,336** | **1,034,255** | **$11.02** |

At Claude Sonnet 5's **$2 / $10** per 1M (platform.claude.com/docs, Sept 2026).

**Output is 75% of tokens and 94% of the bill.** That is prompt-contract rule 1
— quote a grid reading behind every length — and it is not waste: it is the
only reason fabrication is visible and `reading_fidelity` is scorable at all.
Any provider comparison is therefore dominated by the OUTPUT rate, and a
provider that is cheap on input and dear on output buys us nothing.

## The screen, in this order

A cheaper model that cannot do the job is not cheaper.

1. **Vision.** The pipeline's entire premise is reading a grid render. A
   text-only model scores zero regardless of price.
2. **Tool calling.** The authoring contract is one `submit_tree` call with a
   structured schema. Prose-wrapped JSON is a different (worse) design.
3. **OpenAI-compatible endpoint.** `llm_client` speaks chat-completions to a
   configurable `base_url`; a compatible provider is a `PROVIDERS` entry and an
   env var, not a rewrite.
4. **Then, and only then, price.**

## Candidates

| provider / model | vision | tools | OAI-compatible | input / output per 1M | this run |
|---|---|---|---|---|---|
| Claude Sonnet 5 *(current)* | ✅ | ✅ | ✅ (compat endpoint) | $2 / $10 | **$11.02** |
| **DeepSeek V4-Flash-Vision-Exp** | ✅ | ✅ | ✅ | **$0.22 / $0.66** off-peak; $0.44 / $1.32 peak | **$0.76** |
| **GLM-4.6V** (Novita) | ✅ | ✅ | ✅ | $0.30 / $0.90 | ~$1.03 |
| Qwen3-VL (`qwen3-vl-plus`) | ✅ | ✅ | ✅ | not pinned here | — |

Sources: [DeepSeek V4-Flash-Vision-Exp](https://openrouter.ai/deepseek/deepseek-v4-flash-vision-exp)
· [DeepSeek multimodal announcement](https://x.com/deepseek_ai/status/2090730039973392531)
· [GLM-4.6V on Novita](https://blogs.novita.ai/glm-4-6v-api-on-novita-ai/)
· [Qwen pricing 2026](https://www.eesel.ai/blog/qwen-pricing)
· [Claude pricing](https://platform.claude.com/docs/en/about-claude/pricing).
Prices are as published at 2026-09-08 and are the least durable thing in this
file — re-check before acting.

**DeepSeek shipped vision on 2026-08-21**: images by base64, external URL or
Files API, billed at **≤384 input tokens each**, through the same Chat
Completions endpoint. That is the same `image_url` content-part shape
`llm_client.image_part` already emits.

## Three savings, and they multiply

1. **Drop the second turn.** ADOPTED 2026-09-08 (spec §5). $11.02 → **$2.64**
   with equal-or-better anatomy. No provider change, no accuracy cost.
2. **Change provider.** The same experiment at DeepSeek off-peak: **$0.18**.
   Combined with (1), roughly **60x** cheaper than what was actually paid.
3. **Prompt caching — the one nobody has counted.** DeepSeek and GLM both
   price cache-hit input separately ($0.007 and $0.055 per 1M). Anthropic's
   **OpenAI-compat layer does not expose caching at all**, which is why an
   image is re-uploaded and re-billed on every turn it stays in history
   (`llm_client.py` docstring, "CAVEATS THE COMPAT LAYER IMPOSES"). Anthropic's
   **native Messages API does** support it. So "stop paying twice for the same
   image" and "switch model" are INDEPENDENT fixes, and the first one keeps
   Sonnet.

## How to evaluate, when the time comes

Do not swap. **Bake off**, using the rig that already exists.

Add a `PROVIDERS` entry, point `LLM_PROVIDER`/`LLM_MODEL` at it, and re-run
`evidence/2026-09-08-vlm-tree-authoring/scripts/run17.py` in `none` mode over
the same 17 subjects — about **$0.20** at DeepSeek rates. Score it on the same
four metrics (anatomy MAE, exact, contract-clean, `reading_fidelity`) against
the committed Sonnet numbers in §2c of the spec.

Two things to watch that price cannot tell you:

* **Long structured output.** The 37-node scorpion needed ~22k output tokens in
  ONE tool call. A model with a smaller max-output, or one that degrades on
  long structured emission, will truncate exactly as Sonnet did at the default
  4096 ceiling — and that failure LOOKS like a null result across every arm.
  Check `finish_reason` before believing any comparison.
* **Convention adherence, not just anatomy.** The scorpion row exists to catch
  a model that counts pedipalps. Sonnet fails it (11 against 9). Whether a
  cheaper model fails it the same way is a more interesting question than its
  MAE.

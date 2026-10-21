# Nano Banana 2.1 as the `hf2` image stage (concept-image phase 2)

**Status:** approved by the owner, 2026-10-19 (the question at the end
answered "yes, approved is approved").
**Follows:** `docs/superpowers/specs/2026-10-16-concept-image-quality-design.md`
§4 and the results in `docs/superpowers/evidence/2026-10-16-concept-image/README.md`.

## Why

The experiment held the Hunyuan3D-2 lift fixed and changed only the concept
image. Nano Banana 2.1 with the shipped `CONCEPT_PROMPT_TEMPLATE` (arm B) gave
anatomically correct meshes on **33/34** owner-scored cells over two rounds.
FLUX.1-schnell, the image model `hf2` uses today, gave **21/34**. Arm B also beat
the owner's hand-picked photo meshes (13/17). Anatomy text (arm C) and a
photographic prompt (arm D) did not improve on B. Best-of-4 (arm E) was not run
because one image was already good enough.

So the change is narrow: `hf2` draws its concept image with Nano Banana 2.1
instead of FLUX, using the same prompt, and lifts it exactly as before.

## Goals

1. With a `GEMINI_API_KEY`, `MESH_PROVIDER=hf2` draws the concept image with
   `gemini-nano-banana-2.1` through the existing
   `gemini_image.generate_image`, using `concept_prompt(subject,
   CONCEPT_PROMPT_TEMPLATE)` unchanged.
2. Stage 2 is untouched: the same Space, API and `HUNYUAN_SHAPE_KWARGS`
   (seed 1234), which is the configuration the 33/34 was measured with.
3. Without a `GEMINI_API_KEY`, `hf2` behaves exactly as it does today (FLUX),
   including its cache keys. `make test` stays offline.
4. A FLUX draw is never served as a Gemini draw, and the reverse.
5. The app's mesh review (approve, feedback redraw, retry) keeps working.
   Every Gemini draw is a fresh draw.
6. A key with no image quota fails with a message that says so and what to do.

## Non-goals

* Anatomy text, a photographic prompt, best-of-N or a VLM picker. The
  experiment showed none of them helps.
* Any change to the Hunyuan lift, its settings or its Space.
* Removing FLUX or its constants.
* A spend ledger or budget cap in the app. The cost is documented, not metered.
* The google-genai SDK. `gemini_image` already talks REST over httpx.
* Re-rating or migrating existing cached meshes.

## Anti-goals (a failure even if it works)

* An old FLUX cache entry served when the user expects a new Gemini draw.
* A silent runtime fallback to FLUX when Gemini fails. It would hide a billing
  problem and mix two image models under one setting.
* `make test`, or any default offline path, sending a request to Google.

## Prior art (CLAUDE.md §0)

Gathered by a research agent on 2026-10-19. Rows marked _unverified_ were not
confirmed against a primary source.

| source | finding | adopted / rejected |
|---|---|---|
| DSPy `dspy/clients/lm.py` (`rollout_id`) | A caller-chosen `rollout_id` separates cache entries for otherwise identical LLM requests. A new id bypasses the cache, and later calls with the same id hit it. The id is stripped before the provider sees the request. | **Adopted** as §4's draw label. The closest prior art to our case. |
| LiteLLM and GPTCache caching docs | Exact-match memoization of a stochastic call, keyed on the whole request. Freshness is the caller's opt-in (`no-cache`, `cache_skip`). | **Adopted:** a stored draw is a memo. The caller asks for a fresh draw by changing the label. |
| Bazel `no-cache` tag; DVC `always_changed`; ComfyUI `IS_CHANGED` | Forcing every run to be uncached is the escape hatch, and ComfyUI calls it "not recommended". Its normal way to get a fresh output is to change the seed widget. | **Rejected:** a unique nonce for every draw. That is `no-cache`, and it would make a retry after a failed lift buy a second picture. |
| ai.google.dev troubleshooting + billing pages | Retry only transient errors (408, 429, 5xx) with backoff. Never retry 400, 402 or 403. A request that fails with 400 or 500 is not billed. | **Adopted** in §5. |
| python-genai `_api_client.py` | The documented SDK default is to retry, but with `retry_options=None` the code does `stop_after_attempt(1)`, so it never retries. | **Reason** we retry ourselves (and one more reason not to take the SDK). |
| gemini-cli issue 8437; Google forum thread on image 429s; `google/rpc/error_details.proto` | A free-tier image 429 is `RESOURCE_EXHAUSTED` with `QuotaFailure` violations (`quotaId` ending `-FreeTier`) and a message containing "limit: 0". It **also** carries a `RetryInfo` delay, which is misleading because waiting never helps. The proto defines `quota_value`, but the bodies people have pasted do not include it. | **Adopted:** treat a 429 as permanent when a violation has `quotaValue == "0"`, or the message matches `limit:\s*0\b`, or it says prepayment credits are depleted. A 402 is permanent too. Never trust `RetryInfo` alone. _Unverified: a 429 body captured from `gemini-nano-banana-2.1` itself._ |
| ai.google.dev pricing page (read 2026-10-19) | `gemini-nano-banana-2.1` free tier: "Not available". | **Confirms** that every free-tier key fails. The message in §5 says so. |
| ai.google.dev `generate-content` reference | `seed`: "If not set, the request uses a randomly generated seed". Nothing about determinism. Blocked output comes back as HTTP **200** with `finishReason` `IMAGE_SAFETY` / `IMAGE_PROHIBITED_CONTENT` / `NO_IMAGE`, or with `promptFeedback.blockReason`. Image output is listed as `IMAGE_JPEG`. | **Adopted:** the seed is a label, not a recipe. Blocks stay "no image" errors, as `gemini_image` already does. JPEG is the expected type. |
| OpenAI cookbook, `seed` | "Best effort" determinism. `system_fingerprint` marks backend changes. | **Noted:** the same lesson. Recording the response's `modelVersion` would be the analogue. _Unverified that Gemini returns it, so it is left out._ |
| Hunyuan3D-2 `gradio_app.py`, `hy3dgen/rembg.py` | Uploads become RGBA. rembg runs only if `check_box_rembg` is true or the image is RGB. The function's default is False. | **Adopted as a pinned test:** a JPEG has no alpha, so `HUNYUAN_SHAPE_KWARGS["check_box_rembg"] is True` is load-bearing for Gemini concepts. The constant does not change. |
| Meshy image-to-3D docs | Accepts .jpg, .jpeg and .png, and recommends a clean background. | Consistent with lifting the JPEG as is, without re-encoding it to PNG. |
| Concept-image experiment (2026-10-16..19) | The 33/34 was measured with the Gemini JPEG lifted directly and Hunyuan seed 1234. | **Adopted:** no re-encode, and the lift seed stays 1234 (§4). |

## Design

### 1. Choosing the image backend

`get_provider("hf2")` picks stage 1 from a new variable, `MESH_IMAGE_BACKEND`:

| `MESH_IMAGE_BACKEND` | `GEMINI_API_KEY` | stage 1 |
|---|---|---|
| unset or `auto` | set (non-empty) | Nano Banana 2.1 |
| unset or `auto` | unset or empty | FLUX on HuggingFace, as today |
| `gemini` | set | Nano Banana 2.1 |
| `gemini` | unset | `ValueError` at `get_provider`, like `meshy` without its key |
| `flux` | either | FLUX, as today |
| anything else | either | `ValueError` naming the valid values |

* `GEMINI_IMAGE_MODEL` overrides the model id (default
  `gemini_image.DEFAULT_MODEL`). The model is in the cache key, so an override
  can never be served a different model's draw. _(Builder's call: cheap, and
  model ids change; the spec's "Later" list already names Nano Banana Pro.)_
* `GEMINI_API_KEY` is also the key `LLM_PROVIDER=gemini` reads. A user whose
  key is on the free tier, set only for the LLM, will now get Gemini images
  and the no-quota error of §5. That error tells them to set
  `MESH_IMAGE_BACKEND=flux`. This is the reason the variable exists.
* `HF_IMAGE_SPACE_ID` / `HF_IMAGE_API` keep their meaning, and apply only to
  the FLUX backend.

### 2. Stage 1 inside `TwoStageProvider`

`TwoStageProvider` gains three constructor arguments:

* `image_model=None`. `None` keeps today's HF Space stage. A model id selects
  the Gemini stage.
* `image_seed=None`. Sent to Gemini as `seed` and recorded, never relied on.
* `image_fn=gemini_image.generate_image`. Injectable, so tests never touch
  the network.

When `image_model` is set, `generate()` does stage 1 like this:

1. The prompt is built exactly as today: `subject_description` or the prompt,
   then `concept_prompt(subject, self.prompt_template)`.
2. `image_fn(prompt, <out_dir>/concept.part.<n>, model=…, seed=…)`, with the
   bounded retries of §5.
3. The file is renamed to `concept<ext>` by its **bytes**, not by the
   returned `mimeType`: `.jpg` for JPEG (`FF D8 FF`), `.png`, `.webp`. The
   probe saw JPEG, but the bytes are the truth. Stale `concept.*` of another
   extension in the folder are removed first, so the folder never holds two
   concept images.
4. `progress("image", concept)`, then stage 2 exactly as today:
   `self._call(self.mesh_space, self.mesh_api, concept, self.mesh_kwargs,
   "mesh", primary_is_file=True)`.

The FLUX branch of `generate()` is not changed.

### 3. The cache key

`cache_settings` keeps the FLUX dict **byte-identical** (the pinned
`moose-0ea544523bcf6966` key stays green). The Gemini dict has a different
shape:

```python
{"image_backend": "gemini", "image_model": "gemini-nano-banana-2.1",
 "image_seed": <int or None>, "prompt_template": CONCEPT_PROMPT_TEMPLATE,
 "mesh_space": ..., "mesh_api": ..., "mesh_kwargs": {...}}
# + "subject_description" when set, as today
```

FLUX settings have no `image_backend` key and Gemini settings have no
`image_space` key, so the two digests cannot collide. A test checks the
default key of each backend differs for the same prompt, and that changing
only `image_model` moves the key.

### 4. What the key means when the seed does not reproduce

Gemini accepts `seed` but two calls with the same seed return different
images (live probe, 2026-10-16). So a Gemini cache entry is **a stored copy of
one paid draw**, not a recipe that would reproduce it. The seed in the key is
a **draw label** chosen by the caller:

* **Same label, same draw.** Asking again for the same label returns the stored
  mesh, and a retry after a failed lift lifts the concept already drawn. For
  this, `get_provider` sets `reuse_concept=True` on the Gemini backend. That
  flag is opt-in today because a stale concept could pass as a fresh draw.
  Under a draw label the concept in the folder *is* that draw's, already paid
  for and already shown to the user. FLUX keeps `reuse_concept=False`.
* **A new draw needs a new label.** The app gives every round its own label:
  * `revise_mesh` already draws with `random.randrange(1, 10**7)`.
  * `first_mesh`'s default draw (no library mesh and no proven mesh) now also
    uses a random label when draws do not reproduce. Today it uses no seed, so
    a second app run of a subject would hit the first run's folder and re-serve
    a mesh the reviewer may already have rejected. With FLUX that was harmless,
    because a fresh FLUX draw would be the same mesh. With Gemini it would
    waste a review round on a known-bad mesh.
  * `retry_mesh` reuses the pending round's label, so it lifts the same
    concept again.
* **The CLI** (`author`, `run`) passes no seed, so its label is `None`. A
  re-run of `author "a dog"` returns that subject's stored first draw, as it
  does today with FLUX.
* **The lift seed stays 1234 on Gemini draws.** Today a redraw seed is written
  into both stages, because a fresh FLUX picture needed a new seed. A Gemini
  picture is fresh without one. Keeping Hunyuan at `HUNYUAN_SHAPE_KWARGS` as
  is reproduces the measured setup on every round. FLUX keeps today's
  behaviour (the seed goes to both stages).

`mesh_acquire.draws_reproduce(name=None) -> bool` tells the app which case it
is in: `False` only when `hf2` resolves to the Gemini backend.

### 5. Errors, retries and spend

* **Cost.** About $0.042 an image on the paid tier ($0.0336 for the image
  tokens, the rest text and thinking tokens). One draw is one image. A round
  that only retries the lift costs nothing on Gemini.
* **No quota on this key**: not retried, and `RetryInfo` is ignored. This
  covers HTTP 402, a 400 `FAILED_PRECONDITION` (billing), and a 429 with a
  `QuotaFailure` violation whose `quotaValue` is `"0"`, or whose message
  matches `limit:\s*0\b` or mentions depleted prepayment credits. The message, prefixed `image stage:` like
  every stage error:
  > image stage: Gemini gemini-nano-banana-2.1 has no image quota on this API
  > key. The free tier's image quota is 0. Enable billing for the key's Google
  > Cloud project (about $0.042 an image), or set MESH_IMAGE_BACKEND=flux to
  > draw with FLUX on HuggingFace.
* **Transient** (any other 429, and 408, 500, 502, 503, 504, timeouts,
  connection errors): retried with `TwoStageProvider`'s existing `attempts`
  and `backoff`, then reported as `image stage: Gemini <model> failed after N
  attempts: …`.
* **Everything else** (400 bad request or bad key, 403, a blocked prompt, no
  image in the answer): not retried, reported with Gemini's own message.
* `gemini_image` gains what the classifier needs: the HTTP status and the
  parsed error body on `GeminiImageError`, so callers do not parse message
  text. Its existing behaviour and tests are unchanged.
* The app already catches `RuntimeError`/`ValueError` from a draw and shows a
  failed stage with a retry button, and the CLI maps them to exit 2.
  `GeminiImageError` is a `RuntimeError`, so nothing else changes there.

### 6. Concept images are JPEG now

Every reader already accepts `.jpg`: `_cached_concept`, `cached_files`, the
app's `concept_r{N}` copy (it keeps the source extension), the CLI's
`author/concept.*` copy, the web viewer (`Viewer.tsx` `IMG`) and
`llm_client.sniff_media_type` (used when the concept goes to the VLM in
`subject_rewrite.rewrite`). Tests pin `concept.jpg` in the cache folder and
`concept_r0.jpg` in an app run.

### 7. Small visible changes

* The app's image stage summary gains `image_model`, and the stage line shows
  it beside the provider: `hf2 · gemini-nano-banana-2.1`. It names the model
  that **drew the mesh being shown**: it is read from that cache folder's
  `meta.json` `settings` (`image_model` for Gemini, `image_space` for FLUX), so
  a served best-rated or library mesh is labelled by what made it, not by
  today's backend. It is omitted when the folder records neither.
  _(Builder's call: without it the live run cannot show which model drew the
  picture.)_
* `meta.json` already records `settings`, so the image model is in each
  cached mesh's provenance with no schema change.
* `.env.example` documents `GEMINI_API_KEY` (missing today, though
  `llm_client` reads it), `MESH_IMAGE_BACKEND`, `GEMINI_IMAGE_MODEL`, the
  cost, and the free-tier limit. `CLAUDE.md` §3/§4 say `hf2` is Nano Banana
  2.1 → Hunyuan3D-2 with FLUX as the fallback.

### 8. Tests

All offline. The Gemini backend is tested through `image_fn` fakes and
`httpx.MockTransport`.

* The app's `load_env` copies the repo `.env` into `os.environ` for the rest
  of a test session, and the owner's `.env` has a `GEMINI_API_KEY`. So the
  `hf2` tests that assert FLUX behaviour would flip to Gemini depending on test
  order. Every test that resolves `hf2` clears `GEMINI_API_KEY`,
  `MESH_IMAGE_BACKEND` and `GEMINI_IMAGE_MODEL` first (an autouse fixture in
  the two mesh test modules), and the Gemini tests set them explicitly.
* Pinned behaviours: backend selection table (§1); FLUX settings and the moose
  key unchanged; Gemini settings shape and non-collision; prompt is the shipped
  template; Hunyuan kwargs passed unchanged, seed 1234 even with a draw label;
  `concept.jpg` by bytes; reuse of a drawn concept on retry; quota-zero error
  text and no retry; transient retry count; app `first_mesh` passes a fresh
  label only when draws do not reproduce; `image_model` in the summary.

### 9. Done

* This design approved by the owner.
* Implementation on a branch with `make test` green.
* One live app run of "a scorpion" (`MESH_PROVIDER=hf2`, the `.env`'s Gemini
  key, `MESH_LIBRARY_DIR` unset so round 0 is a draw and not the photo mesh),
  showing the Nano Banana concept image and its Hunyuan mesh, with
  `meta.json` naming the model.

## Calls made without the owner (check these)

1. **Backend chosen by key presence, with `MESH_IMAGE_BACKEND=flux` as the
   override** (§1), not by a new `MESH_PROVIDER` name. The brief asked for
   FLUX as the fallback without a key. The override exists because the
   same key also serves `LLM_PROVIDER=gemini`.
2. **No silent runtime fallback to FLUX** when Gemini fails (anti-goals).
3. **The seed is a draw label** (§4). Same label, same stored draw. The app
   gives each round a new label, including round 0. The CLI's default draw is
   stored and reused.
4. **The Hunyuan seed stays 1234 on Gemini draws**, including redraws (§4).
   Today a redraw seed also changes the lift seed. FLUX keeps that.
5. **`reuse_concept=True` on the Gemini backend**: a lift retry lifts the
   picture already paid for and shown (§4).
6. **The concept is named by its bytes** (`concept.jpg`), and it is not
   re-encoded to PNG (§2, §6).
7. **`GEMINI_IMAGE_MODEL` override** and the **`image_model` label** in the app
   (§1, §7).
8. Retries reuse `TwoStageProvider`'s `attempts`/`backoff` (3 attempts, 10 s
   then 30 s), not Gemini's `RetryInfo` delay (§5).

## Question for the owner

**When Gemini is on, may round 0 still serve a best-rated mesh that FLUX drew?**

Ratings are filed under the provider name, and that is `hf2` for both
backends. So `best_proven` will keep serving an approved FLUX mesh first. The
cache has one today, a `moose` with 1 approval. In that case no Gemini draw
happens for the subject until a reviewer rejects that mesh.

* **Yes, approved is approved (recommended).** A reviewer has already passed
  that mesh, so serving it again costs nothing and is safe. New Gemini ratings
  go into the same `hf2` pool, and the Wilson ranking compares meshes from
  both models. The stage line still names the model that drew it (§7). No
  ratings code changes.
* **No, only meshes from the current image model.** `best_proven` also
  filters on the folder's `meta.json` `settings` (`image_backend`). Old FLUX
  approvals stay on disk, but a Gemini run ignores them. This adds a filter
  and its tests, and needs no migration.

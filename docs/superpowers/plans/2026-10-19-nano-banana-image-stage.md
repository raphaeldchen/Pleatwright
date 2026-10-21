# Nano Banana 2.1 as the `hf2` Image Stage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With a `GEMINI_API_KEY`, `MESH_PROVIDER=hf2` draws its concept image with `gemini-nano-banana-2.1` and lifts it with the unchanged Hunyuan3D-2 stage. Without a key it falls back to FLUX, exactly as today.

**Architecture:** `gemini_image` learns to classify its own errors. `TwoStageProvider` gains a Gemini stage-1 branch, selected by `image_model`, with its own differently shaped `cache_settings`. `get_provider("hf2")` picks the backend from `MESH_IMAGE_BACKEND` and `GEMINI_API_KEY`. The app gives every Gemini round a fresh draw label and shows which model drew the picture.

**Tech Stack:** Python 3.14, httpx (already a dependency), pytest, FastAPI app server, React/TypeScript with vitest.

**Spec:** `docs/superpowers/specs/2026-10-19-nano-banana-image-stage-design.md` (approved 2026-10-19; best-rated FLUX meshes keep being served).

## Global Constraints

- `CONCEPT_PROMPT_TEMPLATE`, `concept_prompt`, `HUNYUAN_SHAPE_KWARGS` and `FLUX_IMAGE_KWARGS` are not edited.
- With the FLUX backend, `cache_settings` and every cache key are byte-identical to today: `cache_key("hf2", "moose", get_provider("hf2").cache_settings) == "moose-0ea544523bcf6966"`.
- `make test` makes no network call. Gemini is exercised only through an injected `image_fn` or `httpx.MockTransport`.
- No new dependencies (no google-genai SDK).
- Tests use only the 51 artifact trees. Never use tardigrade or water bear as a subject.
- Every stage error message starts with `image stage:` or `mesh stage:`.
- The no-quota message is the spec §5 text, verbatim with the model id filled in.
- Draw labels are `random.randrange(1, 10**7)`, the same range `revise_mesh` uses.

## Review Focus

1. **The developer's `.env` leaking into tests.** The app's `load_env` copies `GEMINI_API_KEY` into `os.environ`. Every `hf2` FLUX assertion must still hold when that key is set in the shell. This is pinned by Task 2's conftest and by `test_flux_is_unchanged_even_with_a_key_when_forced`.
2. **A retry after a failed lift.** It must not buy a second picture, and it must lift the concept the user already saw. Pinned by `test_a_lift_retry_reuses_the_drawn_concept` (Task 2).
3. **Leftover `concept.png` from an older FLUX draw** in the same folder must not sit beside a new `concept.jpg`. Pinned by `test_a_new_concept_replaces_any_other_concept_file` (Task 2).
4. **`MESH_IMAGE_BACKEND` set to a typo or in another case** (`Gemini`, `FLUX `) must give a clear `ValueError`, or be normalised, never a silent FLUX. Pinned by `test_backend_value_is_case_and_space_insensitive` and `test_an_unknown_backend_names_the_valid_values` (Task 3).
5. **An empty `GEMINI_API_KEY=` line in `.env`** means "absent" (FLUX), not "present". Pinned in Task 3's selection table test.

---

### Task 1: `gemini_image` reports status and body, and classifies them

**Files:**
- Modify: `mcp_harness/gemini_image.py`
- Test: `mcp_harness/tests/test_gemini_image.py`

**Interfaces:**
- Produces:
  - `GeminiImageError(message: str, *, status: int | None = None, body: dict | None = None)`, with `.status` and `.body` attributes. `status` is `None` for a transport failure, the HTTP status for a non-200, and `200` for an answer with no image.
  - `no_image_quota(e: GeminiImageError) -> bool`
  - `is_transient(e: GeminiImageError) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
def _err(status, message="", details=None, err_status=""):
    return {"error": {"code": status, "message": message, "status": err_status,
                      "details": details or []}}

FREE_429 = _err(429, "Quota exceeded for metric: generativelanguage.googleapis.com/"
                "generate_content_free_tier_requests, limit: 0, model: gemini-nano-banana-2.1. "
                "Please retry in 11.89s.", err_status="RESOURCE_EXHAUSTED",
                details=[{"@type": "type.googleapis.com/google.rpc.QuotaFailure", "violations": [
                    {"quotaMetric": "generativelanguage.googleapis.com/generate_content_free_tier_requests",
                     "quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},
                         {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "11s"}])
RATE_429 = _err(429, "Resource has been exhausted (e.g. check quota).", err_status="RESOURCE_EXHAUSTED")

def _fail(status, body, tmp_path):
    t = httpx.MockTransport(lambda req: httpx.Response(status, json=body))
    with pytest.raises(GI.GeminiImageError) as ei:
        GI.generate_image("x", str(tmp_path / "c.jpg"), api_key="k", transport=t)
    return ei.value

def test_an_http_error_carries_its_status_and_body(tmp_path):
    e = _fail(429, FREE_429, tmp_path)
    assert e.status == 429 and e.body == FREE_429

@pytest.mark.parametrize("status, body", [
    (429, FREE_429),
    (429, _err(429, "x", details=[{"@type": "type.googleapis.com/google.rpc.QuotaFailure",
                                   "violations": [{"quotaValue": "0"}]}])),
    (429, _err(429, "Your prepayment credits are depleted.")),
    (402, _err(402, "payment required")),
    (400, _err(400, "billing not enabled", err_status="FAILED_PRECONDITION")),
])
def test_no_image_quota_is_recognised_and_not_transient(tmp_path, status, body):
    e = _fail(status, body, tmp_path)
    assert GI.no_image_quota(e) and not GI.is_transient(e)

@pytest.mark.parametrize("status", [408, 500, 502, 503, 504])
def test_server_errors_are_transient(tmp_path, status):
    e = _fail(status, _err(status, "boom"), tmp_path)
    assert GI.is_transient(e) and not GI.no_image_quota(e)

def test_a_plain_rate_limit_is_transient(tmp_path):
    e = _fail(429, RATE_429, tmp_path)
    assert GI.is_transient(e) and not GI.no_image_quota(e)

@pytest.mark.parametrize("status, body", [
    (400, _err(400, "API key not valid.", err_status="INVALID_ARGUMENT")),
    (403, _err(403, "denied", err_status="PERMISSION_DENIED")),
])
def test_client_errors_are_neither(tmp_path, status, body):
    e = _fail(status, body, tmp_path)
    assert not GI.is_transient(e) and not GI.no_image_quota(e)

def test_a_transport_failure_is_transient_with_no_status(tmp_path):
    def boom(req):
        raise httpx.ConnectError("down")
    with pytest.raises(GI.GeminiImageError) as ei:
        GI.generate_image("x", str(tmp_path / "c.jpg"), api_key="k",
                          transport=httpx.MockTransport(boom))
    assert ei.value.status is None and GI.is_transient(ei.value)

def test_an_answer_without_an_image_is_status_200_and_not_transient(tmp_path):
    body = {"candidates": [{"finishReason": "IMAGE_SAFETY", "content": {"parts": []}}]}
    e = _fail(200, body, tmp_path)
    assert e.status == 200 and not GI.is_transient(e) and not GI.no_image_quota(e)
```

`test_an_answer_without_an_image…` reuses `_fail`, because a 200 with no `inlineData` also raises.

- [ ] **Step 2: Run them and see them fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_gemini_image.py -q`
Expected: FAIL (`GeminiImageError` takes no `status`; `no_image_quota` is undefined).

- [ ] **Step 3: Implement**

- `GeminiImageError.__init__(self, message, *, status=None, body=None)`.
- `generate_image` passes `status=resp.status_code, body=<parsed JSON or None>` on a non-200, `status=None` on `httpx.HTTPError`, and `status=200, body=data` when no image comes back.
- `no_image_quota`, in this order:
  - `status == 402` → true;
  - `status == 400` and `body.error.status == "FAILED_PRECONDITION"` → true;
  - `status == 429` and any of: a `QuotaFailure` violation with `quotaValue` in `("0", 0)`, the message matching `re.compile(r"limit:\s*0\b")`, or the message containing both "prepayment credits" and "depleted" (case-folded) → true;
  - otherwise false.
- `is_transient`: `status is None`, or `status in {408, 429, 500, 502, 503, 504}` and not `no_image_quota(e)`.
- Add a docstring paragraph citing the sources from the spec's prior-art rows.

- [ ] **Step 4: Run them and see them pass**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_gemini_image.py -q`
Expected: all pass, including the existing tests.

- [ ] **Step 5: Commit** `gemini_image: errors carry status and body; classify no-quota vs transient`

---

### Task 2: Gemini stage 1 inside `TwoStageProvider`

**Files:**
- Create: `mcp_harness/tests/conftest.py`
- Create: `mcp_harness/tests/test_hf2_gemini.py`
- Modify: `mcp_harness/mesh_acquire.py` (`TwoStageProvider.__init__`, `cache_settings`, `generate`; new `_draw_gemini`, `_concept_ext`)

**Interfaces:**
- Consumes: Task 1's `GeminiImageError`, `no_image_quota` and `is_transient`; `gemini_image.generate_image(prompt, out_path, *, model, seed) -> GeminiImage`.
- Produces:
  - `TwoStageProvider(..., image_model: str | None = None, image_seed: int | None = None, image_fn=None)`. `image_fn` defaults to `gemini_image.generate_image`, resolved at call time so tests can monkeypatch it.
  - `GEMINI_NO_QUOTA = "image stage: Gemini {model} has no image quota on this API key. The free tier's image quota is 0. Enable billing for the key's Google Cloud project (about $0.042 an image), or set MESH_IMAGE_BACKEND=flux to draw with FLUX on HuggingFace."` (module constant, `.format(model=…)`).
  - The Gemini `cache_settings` shape: `{"image_backend": "gemini", "image_model", "image_seed", "prompt_template", "mesh_space", "mesh_api", "mesh_kwargs"}`, plus `"subject_description"` when it is set.

- [ ] **Step 1: Write `tests/conftest.py`**

An autouse fixture that runs `monkeypatch.delenv(v, raising=False)` for `GEMINI_API_KEY`, `MESH_IMAGE_BACKEND` and `GEMINI_IMAGE_MODEL`. Its docstring explains the `load_env` leak (spec §8). Then run `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_gemini_image.py tests/test_llm_client.py tests/test_two_stage_provider.py tests/test_mesh_acquire.py -q`. Expected: all pass. Any test that relied on an ambient key now fails visibly; fix it with an explicit `setenv`.

- [ ] **Step 2: Write the failing tests** in `test_hf2_gemini.py`

Shared fakes:
- `JPEG = b"\xff\xd8\xff\xe0" + b"j" * 32`.
- `_image_fn(log, data=JPEG, errors=())` returns a callable `(prompt, out_path, *, model, seed)`. It pops and raises the queued errors first, then writes `data` to `out_path`, appends `(prompt, out_path, model, seed)` to `log`, and returns a `gemini_image.GeminiImage`.
- The mesh Space fake comes from `test_two_stage_provider._factory` / `_FakeClient` (import them), with the `glb` fixture defined the same way.
- `_gem(tmp_path, log, mlog, glb, **kw)` builds `TwoStageProvider(mesh_space="mesh/space", mesh_api="/shape_generation", mesh_kwargs=dict(mesh_acquire.HUNYUAN_SHAPE_KWARGS), prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE, image_model="gemini-nano-banana-2.1", client_factory=_factory({"mesh/space": glb}, mlog), sleep=lambda s: None, image_fn=_image_fn(log), **kw)`.

Tests:

```python
def test_gemini_draws_the_shipped_template_and_hunyuan_lifts_it_unchanged(tmp_path, glb):
    log, mlog = [], []
    p = _gem(tmp_path, log, mlog, glb, image_seed=4242)
    out = p.generate("a scorpion", str(tmp_path / "k"))
    assert log[0][0] == mesh_acquire.concept_prompt("a scorpion")
    assert log[0][2:] == ("gemini-nano-banana-2.1", 4242)
    assert out == str(tmp_path / "k" / "mesh.glb")
    sent = mlog[0]["args"]
    assert sent[1] == _file_arg(str(tmp_path / "k" / "concept.jpg"))   # image slot 2
    assert sent[2:] == tuple(v for k, v in mesh_acquire.HUNYUAN_SHAPE_KWARGS.items()
                             if k not in ("caption", "image"))       # seed 1234 survives

def test_the_concept_is_named_by_its_bytes(tmp_path, glb):  # parametrize JPEG/.jpg, PNG/.png, RIFF....WEBP/.webp
    ...  # the only concept.* in the folder has the expected extension

def test_bytes_that_are_no_known_image_fail_the_image_stage(tmp_path, glb):
    # data=b"<html>" -> RuntimeError starting "image stage:", and the mesh Space is never called

def test_a_new_concept_replaces_any_other_concept_file(tmp_path, glb):
    # pre-write k/concept.png; after a JPEG draw only concept.jpg exists

def test_a_lift_retry_reuses_the_drawn_concept(tmp_path, glb):
    # reuse_concept=True; mesh Space raises the first time (results["mesh/space"] = RuntimeError("Connection refused")),
    # generate() raises "mesh stage:"; swap the results to glb; generate() again -> len(log) == 1

def test_no_quota_fails_at_once_with_the_spec_message(tmp_path, glb):
    # errors=[GeminiImageError("…limit: 0", status=429, body=FREE_429-like)]
    # str(exc) == mesh_acquire.GEMINI_NO_QUOTA.format(model="gemini-nano-banana-2.1"); 0 sleeps; no mesh call

def test_transient_errors_are_retried_then_named(tmp_path, glb):
    # attempts=3, three 503 errors -> RuntimeError matching r"^image stage: Gemini gemini-nano-banana-2\.1 failed after 3 attempts"
    # sleeps recorded == [10.0, 30.0]

def test_a_transient_error_then_success_draws_once(tmp_path, glb):
    # one 503 then success -> mesh returned, len(log) == 1

def test_a_client_error_is_not_retried(tmp_path, glb):
    # a 400 INVALID_ARGUMENT -> RuntimeError starting "image stage:" carrying Gemini's message; 0 sleeps

def test_gemini_cache_settings_shape():
    s = _gem(...).cache_settings
    assert s["image_backend"] == "gemini" and s["image_model"] == "gemini-nano-banana-2.1"
    assert "image_space" not in s and "image_kwargs" not in s
    assert s["mesh_kwargs"]["seed"] == 1234 and s["mesh_kwargs"]["image"] == "<stage input>"
    json.dumps(s)                                           # JSON-safe

def test_the_image_model_and_seed_move_the_key():
    # keys for (model A, seed None), (model B, seed None), (model A, seed 7) all differ

def test_hunyuan_needs_rembg_for_a_jpeg_concept():
    """JPEG has no alpha; Hunyuan3D-2 runs rembg only when check_box_rembg is set
    (hy3dgen/rembg.py), so this flag is load-bearing for Gemini concepts."""
    assert mesh_acquire.HUNYUAN_SHAPE_KWARGS["check_box_rembg"] is True
```

- [ ] **Step 3: Run them and see them fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_hf2_gemini.py -q`
Expected: FAIL (`unexpected keyword argument 'image_model'`).

- [ ] **Step 4: Implement**

- `__init__` stores `image_model`, `image_seed` and `image_fn`.
- `cache_settings` returns the Gemini shape when `image_model` is set. Otherwise it returns today's dict, unchanged.
- In `generate`, stage 0 (reuse) is unchanged. In stage 1, when `image_model` is set, call `concept = self._draw_gemini(image_prompt, out_dir)` and then `progress("image", concept)`. Stage 2 then lifts `concept`. The FLUX branch is untouched.
- `_draw_gemini(self, prompt, out_dir) -> str`:
  - Retry loop over `self.attempts` with `self.sleep(self.backoff[...])`, like `_call`.
  - Write to `os.path.join(out_dir, ".concept.part")`.
  - On `GeminiImageError`: if `no_image_quota`, raise `RuntimeError(GEMINI_NO_QUOTA…)`. If it is not transient, raise `RuntimeError(f"image stage: {e}")`. Otherwise remember the error and loop.
  - After the loop: `RuntimeError(f"image stage: Gemini {model} failed after {n} attempts: {last}")`.
  - On success: `ext = _concept_ext(first 12 bytes)`. Raise `RuntimeError("image stage: Gemini {model} returned bytes that are not JPEG, PNG or WEBP")` if `ext` is `None`, removing the part file first. Unlink any `concept.{png,jpg,jpeg,webp}`, `os.replace` the part file to `concept + ext`, and return that path.
  - Every raise uses `from e`.
- `_concept_ext(head: bytes) -> str | None`: `b"\xff\xd8\xff"` → `.jpg`, `b"\x89PNG\r\n\x1a\n"` → `.png`, `RIFF????WEBP` → `.webp`.

- [ ] **Step 5: Run them and see them pass**, plus the existing provider tests

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_hf2_gemini.py tests/test_two_stage_provider.py tests/test_concept_ab.py -q`
Expected: all pass.

- [ ] **Step 6: Commit** `mesh_acquire: Gemini concept stage in TwoStageProvider`

---

### Task 3: `get_provider("hf2")` chooses the backend

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (`get_provider`, new `hf2_image_backend`, `draws_reproduce`, `image_model_label`)
- Test: `mcp_harness/tests/test_hf2_gemini.py`

**Interfaces:**
- Consumes: Task 2's `TwoStageProvider` arguments.
- Produces:
  - `hf2_image_backend() -> str`: returns `"gemini"` or `"flux"`. Raises `ValueError` for `gemini` without a key, or for an unknown value. The value is read stripped and case-folded, and empty means `auto`.
  - `draws_reproduce(name: str | None = None) -> bool`: `False` only when the provider name resolves to `hf2` and the backend resolves to `gemini`. Never raises; a misconfiguration surfaces later from `get_provider`.
  - `image_model_label(name: str | None = None, key_dir: str | None = None) -> str | None`. With `key_dir`, it reads `read_mesh_meta(key_dir)["settings"]` and returns `image_model`, else `image_space`, else `None`. Without `key_dir`, for `hf2` it returns the current Gemini model id or `HF_IMAGE_SPACE_ID`/`DEFAULT_HF_IMAGE_SPACE`, and `None` for any other provider. It never raises.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("backend, key, expect", [
    (None, "k", "gemini"), ("auto", "k", "gemini"), ("", "k", "gemini"),
    (None, None, "flux"), (None, "", "flux"), ("flux", "k", "flux"), ("gemini", "k", "gemini"),
])
def test_the_selection_table(monkeypatch, backend, key, expect): ...
    # set/delete the env, then assert hf2_image_backend() == expect and
    # (get_provider("hf2").image_model is not None) == (expect == "gemini")

def test_gemini_without_a_key_is_a_value_error(monkeypatch):
    # MESH_IMAGE_BACKEND=gemini, no key -> ValueError mentioning GEMINI_API_KEY

def test_an_unknown_backend_names_the_valid_values(monkeypatch):
    # "dalle" -> ValueError whose text has "auto", "gemini", "flux"

def test_backend_value_is_case_and_space_insensitive(monkeypatch):
    # " Gemini " with a key -> "gemini"; "FLUX" -> "flux"

def test_flux_is_unchanged_even_with_a_key_when_forced(monkeypatch):
    # key set + MESH_IMAGE_BACKEND=flux: cache_key("hf2","moose",settings) == "moose-0ea544523bcf6966"

def test_the_gemini_provider_is_wired_as_designed(monkeypatch):
    # key set: p.image_model == "gemini-nano-banana-2.1"; p.reuse_concept is True;
    # p.prompt_template == CONCEPT_PROMPT_TEMPLATE; p.mesh_kwargs == HUNYUAN_SHAPE_KWARGS
    # get_provider("hf2", seed=48213, description="bull scorpion"): image_seed == 48213,
    # mesh_kwargs["seed"] == 1234, subject_description == "bull scorpion"

def test_gemini_image_model_env_overrides_the_model(monkeypatch): ...

def test_flux_and_gemini_default_keys_differ_for_every_subject(monkeypatch):
    # for the 17 subjects of the 51 artifact trees (artifact_trees subject list): key(flux) != key(gemini)

def test_draws_reproduce(monkeypatch):
    # fake -> True; hf2+flux -> True; hf2+gemini -> False; hf2 + bad backend -> True (no raise)

def test_image_model_label(monkeypatch, tmp_path):
    # no key_dir: hf2+gemini -> model id; hf2+flux -> DEFAULT_HF_IMAGE_SPACE; fake -> None
    # key_dir with meta settings {"image_model": "m"} -> "m"; {"image_space": "s"} -> "s";
    # {"glb_sha256": ...} -> None; no meta.json -> None
```

For the subject list, use whatever the artifact-tree helper (`tests/artifact_trees.py`) exposes. If it exposes no list, take the subject names from the file names in `fixtures/full17_v3_sticks/`.

- [ ] **Step 2: Run them and see them fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_hf2_gemini.py -q`

- [ ] **Step 3: Implement**

- `get_provider("hf2")` calls `hf2_image_backend()`. On `flux`, it runs today's code, unchanged. On `gemini`, it builds `TwoStageProvider` with:
  - the same `mesh_space`, `mesh_api` and `token`, and the same rule for `mesh_kwargs` (Hunyuan's kwargs only on the default Space);
  - the seed **not** written into `mesh_kwargs`;
  - `image_model=os.environ.get("GEMINI_IMAGE_MODEL") or gemini_image.DEFAULT_MODEL`, `image_seed=seed`, `reuse_concept=True`;
  - `prompt_template=CONCEPT_PROMPT_TEMPLATE` and `subject_description=description`.
- Update the docstring of `get_provider` and the module's hf2 comment to describe the two backends.

- [ ] **Step 4: Run them and see them pass**, plus the full mesh suites

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_hf2_gemini.py tests/test_two_stage_provider.py tests/test_mesh_acquire.py tests/test_mesh_progress.py tests/test_mesh_ratings.py -q`
Expected: all pass.

- [ ] **Step 5: Commit** `mesh_acquire: hf2 draws with Nano Banana 2.1 when GEMINI_API_KEY is set`

---

### Task 4: The app gives Gemini rounds fresh labels and shows the image model

**Files:**
- Modify: `app/server/pleatwright_app/tools.py` (`first_mesh`, `_draw_round`'s image summary, `make_mesh`'s image summary)
- Modify: `app/server/tests/conftest.py` (`offline` also deletes the three env vars)
- Modify: `app/web/src/runStore.ts` (`summaryLine`, `summaryPairs` for `image`)
- Test: `app/server/tests/test_guided.py`, `app/server/tests/test_tools.py`, `app/web/src/runStore.test.ts`

**Interfaces:**
- Consumes: Task 3's `mesh_acquire.draws_reproduce(name)` and `mesh_acquire.image_model_label(name, key_dir)`.
- Produces: the image-stage summary key `image_model: str` (absent when `None`).

- [ ] **Step 1: Write the failing tests**

```python
# test_guided.py
def test_a_first_draw_gets_a_fresh_label_when_draws_do_not_reproduce(offline, monkeypatch):
    monkeypatch.setattr(mesh_acquire, "draws_reproduce", lambda name=None: False)
    # create "a bird" twice (no approval between) -> both round-0 seeds are ints and differ

def test_a_first_draw_has_no_label_when_draws_reproduce(offline):
    # create "a bird" -> mesh_state rounds[0]["seed"] is None (today's behaviour)

def test_the_image_stage_names_the_model_that_drew_it(offline, monkeypatch):
    monkeypatch.setattr(mesh_acquire, "image_model_label", lambda name=None, key_dir=None: "m-1")
    # stage_output image round 0 summary["image_model"] == "m-1"
    # (the fake provider emits no concept file, so assert on the skipped summary too: the label
    #  is added only when a concept file exists. Use a provider fake that writes concept.jpg,
    #  via monkeypatching mesh_acquire.acquire_mesh to call progress("image", <tmp jpg>) then
    #  progress("mesh", <fixture glb>))

def test_a_jpeg_concept_lands_as_concept_r0_jpg(offline, monkeypatch):
    # same acquire_mesh fake -> mesh_state rounds[0]["concept"] ends with "concept_r0.jpg"
```

```ts
// runStore.test.ts, in "mesh review"
expect(summaryLine(o({ provider: "hf2", image_model: "gemini-nano-banana-2.1" }, "image")))
  .toBe("hf2 · gemini-nano-banana-2.1");
expect(summaryLine(o({ provider: "hf2" }, "image"))).toBe("hf2");
expect(summaryPairs(mk("image", { provider: "hf2", image_model: "m" })))
  .toEqual([["provider", "hf2"], ["image model", "m"]]);
```

Adapt `o(...)` to however the file builds an image-stage `Output`. The existing helper `mk(stage, summary)` already does.

- [ ] **Step 2: Run them and see them fail**

Run: `make PYTHON=$PWD/mcp_harness/.venv/bin/python test-app` if that target exists. Otherwise: `cd mcp_harness && PYTHONPATH=.:tests:../app/server .venv/bin/python -m pytest ../app/server/tests/test_guided.py -q -p no:cacheprovider`. For the web side: `cd app/web && npx vitest run src/runStore.test.ts`.

- [ ] **Step 3: Implement**

- `first_mesh`: with no library mesh and no best mesh, use `seed = None if mesh_acquire.draws_reproduce(_provider_name()) else random.randrange(1, 10**7)`, then `_draw_round(ctx, prompt, ms, seed=seed)`. The library and best-rated paths stay as they are.
- `_draw_round` computes `label = mesh_acquire.image_model_label(_provider_name(), best_dir)` once. A drawn round has `best_dir=None`, so it gets the current backend. A best-rated round reads its folder's meta. A library folder's meta has neither key, so it yields `None`. When a concept file exists, the image summary is `{"provider": provider, "image_model": label}`, with the key omitted if `label` is `None`. `make_mesh` does the same with `key_dir=None`.
- `runStore.ts`: `image` → `[s.provider, s.image_model].filter(Boolean).join(" · ")` unless skipped. `summaryPairs` adds `add("image model", s.image_model)` after the provider.

- [ ] **Step 4: Run them and see them pass**

Same commands. Expected: pass.

- [ ] **Step 5: Commit** `app: fresh draw label for Gemini rounds; the image stage names its model`

---

### Task 5: Docs, full suite, live run

**Files:**
- Modify: `.env.example` (Mesh provider section), `CLAUDE.md` (§3 table row and §4 Mesh bullet), `mcp_harness/gemini_image.py` module docstring (one line: now the `hf2` image stage)
- Create: `docs/superpowers/evidence/2026-10-19-nano-banana-image-stage/README.md` (the live run's record)

- [ ] **Step 1: Docs.**
  - `.env.example`: `hf2` now reads "Nano Banana 2.1 (Gemini, paid, about $0.042 an image) when GEMINI_API_KEY is set, else FLUX.1-schnell → Hunyuan3D-2". Add a commented `GEMINI_API_KEY=` with a note that the free tier's image quota is 0, plus `# MESH_IMAGE_BACKEND=auto   # auto | gemini | flux` and `# GEMINI_IMAGE_MODEL=gemini-nano-banana-2.1`.
  - `CLAUDE.md`: in the §3 mesh row, `hf2: Nano Banana 2.1 image (FLUX.1-schnell without GEMINI_API_KEY) → Hunyuan3D-2 mesh`. Update the §4 Mesh bullet the same way, and add `gemini_image.py` to the §3 row's module list.
- [ ] **Step 2: Full suite.** `make test`, and `cd app/web && npx vitest run && npm run build`. Expected: green. Paste the summary lines into the commit message body.
- [ ] **Step 3: Commit** `docs: hf2 image stage is Nano Banana 2.1`
- [ ] **Step 4: Live run.** Start the app with `MESH_PROVIDER=hf2 MESH_LIBRARY_DIR= make app`, using the `.env` key; the empty `MESH_LIBRARY_DIR` disables the library. Create a run "a scorpion". Check that:
  - round 0's concept is `concept_r0.jpg` and the stage line reads `hf2 · gemini-nano-banana-2.1`;
  - the mesh lifts;
  - the cache folder's `meta.json` `settings.image_backend == "gemini"`.

  Screenshot the concept and mesh into the evidence folder and write its README: the date, the run id, the cost (one image, about $0.042), and what was seen. Commit it.

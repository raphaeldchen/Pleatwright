# Concept-Image Quality Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether a stronger image model, anatomy text, and a photographic prompt make Hunyuan3D-2 lift anatomically correct meshes for the 17 library animals, scored by the owner against a visible-anatomy checklist, with a confirmation round before anything ships.

**Architecture:**

* **Gemini client.** A small production-grade client, `mcp_harness/gemini_image.py`, sits beside `mesh_acquire.py`. Phase 2 reuses it as the shipped image stage.
* **Anatomy text.** A new `anatomy()` in `subject_rewrite.py`, with the same validation rules as the mesh-review rewrite. Phase 2 reuses it.
* **Experiment package.** `mcp_harness/concept_ab/` holds the arms, a resumable runner, a Claude judge (draft scores and the best-of-4 picker), a local HTML review page, and scoring.
* **The lift is untouched.** Every arm writes `concept.png` into its cell and calls the existing `TwoStageProvider` with `reuse_concept=True` and `HUNYUAN_SHAPE_KWARGS`.

**Tech Stack:** Python 3.14; `httpx` for the Gemini REST API (already a dependency, so no new package); `gradio_client` through `mesh_acquire`; Claude through `llm_client` (OpenAI-compatible endpoint); `trimesh` and Pillow through `vlm_render`; pytest.

**Spec:** `docs/superpowers/specs/2026-10-16-concept-image-quality-design.md`

## Global Constraints

* **Hunyuan settings are fixed for every arm:** `mesh_acquire.HUNYUAN_SHAPE_KWARGS` unchanged (seed 1234, 30 steps, guidance 5.0, octree 256, `check_box_rembg` True).
* **Subjects:** the 17 library animals in `~/Downloads/photo_meshes/manifest.json` and nothing else. Never tardigrade or water bear.
* **Image model:** `gemini-nano-banana-2.1`, with key `GEMINI_API_KEY` read from the repo-root `.env` through `env_config.load_env()`.
* **Spending cap:** $15 for the experiment.
  * Planning price: $0.034 per Nano Banana image.
  * Stop if the measured per-image cost is more than double that ($0.068).
* **Anatomy text** is written from the subject word only. It never sees the manifest or the checklist. It is phrased positively (`subject_rewrite.problems` rules).
* **Pass rule:** a cell passes when every checklist part is present, attached and correctly numbered, with no extra or floating parts. **Good enough** means an arm's pass count is at least the photo meshes' pass count minus 1.
* **Rounds:**
  * Round 1 runs arms A–D.
  * After the owner reviews round 1, round 2 redraws the round-1 winner and arm A with new seeds.
  * Arm E runs only if no single-image arm is good enough after round 2, or if the owner asks.
* **Location of live runs:** they go under `$CONCEPT_AB_DIR` (default `~/Pleatwright/experiments/2026-10-16-concept-image/`) and never into the repo. `make test` stays offline: every test uses fakes.
* **Claude models:**
  * Anatomy text: `claude-haiku-5-5` (the `claude` preset default).
  * Judge, draft scores and picker: `claude-sonnet-5`, the model this repo has already verified with image input on the compat endpoint.

## Review Focus

1. **Gemini returns no image part.** This can be a safety block, a text-only answer, or `finishReason` other than `STOP`. Expected: `GeminiImageError` naming the finish reason and any text, and no zero-byte `concept.png`. Test: `test_no_image_part_raises_with_reason` (Task 1).
2. **A quota error on cell 30 of 68.** Expected: the runner stops with exit code 4, keeps every finished cell, and a rerun skips them. Test: `test_quota_stops_run_and_rerun_resumes` (Task 4).
3. **Cost overrun mid-run.** Expected: the ledger refuses the next Gemini call once the spend plus one more image would exceed $15. Test: `test_ledger_refuses_past_cap` (Task 3).
4. **The judge model invents a pass.** For example, it reports every part as seen but with a wrong count. Expected: pass or fail is computed in code from the reported counts and never taken from the model. Test: `test_verdict_is_computed_not_trusted` (Task 5).
5. **The owner's `scores.json` is missing cells or has typos.** Expected: scoring lists the unscored cells by id and does not count them as fails. Test: `test_unscored_cells_reported_not_failed` (Task 7).

## File Structure

| file | responsibility |
|---|---|
| `mcp_harness/gemini_image.py` (create) | One function: a prompt goes in, an image file comes out, with usage metadata. No experiment knowledge. |
| `mcp_harness/subject_rewrite.py` (modify) | Adds `anatomy()` and a `max_words` parameter on `problems()`. |
| `mcp_harness/concept_ab/__init__.py`, `__main__.py` (create) | The CLI: `run`, `draft`, `review`, `calibrate`, `score`, `trees`. |
| `mcp_harness/concept_ab/arms.py` (create) | Subjects, arm definitions, prompt templates, seeds, cell paths and the spend ledger. |
| `mcp_harness/concept_ab/anatomy_checklist.json` (create) | Per-subject visible-anatomy checklist (data). |
| `mcp_harness/concept_ab/run.py` (create) | Generating and lifting cells, resumably. |
| `mcp_harness/concept_ab/judge.py` (create) | `assess()` and `pick()` with Claude vision. |
| `mcp_harness/concept_ab/review.py` (create) | The review page builder, including the photo reference row. |
| `mcp_harness/concept_ab/score.py` (create) | Tallies, the good-enough check, calibration and the unscored report. |
| `mcp_harness/concept_ab/trees.py` (create) | The secondary signal: tree authoring plus fold per mesh. |
| `mcp_harness/tests/test_gemini_image.py`, `test_concept_ab.py`, `test_subject_rewrite.py` (create / modify) | Offline tests. |

**Worktree note:** `env_config` reads `.env` at the worktree root, and the owner's `.env` lives in the main checkout. Before any live step, run `ln -s <repo>/.env .env` in the worktree root. The file is gitignored, so check it with `git check-ignore .env` before linking.

---

### Task 1: Gemini image client

**Files:**
- Create: `mcp_harness/gemini_image.py`
- Test: `mcp_harness/tests/test_gemini_image.py`

**Interfaces:**
- Produces:
  - `generate_image(prompt: str, out_path: str, *, model: str = DEFAULT_MODEL, seed: int | None = None, api_key: str | None = None, transport: httpx.BaseTransport | None = None, timeout: float = 120.0) -> GeminiImage`
  - `@dataclass GeminiImage(path: str, model: str, seed: int | None, mime_type: str, usage: dict, finish_reason: str)`
  - `class GeminiImageError(RuntimeError)`
  - `DEFAULT_MODEL = "gemini-nano-banana-2.1"`

**The request:**
* `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`, with header `x-goog-api-key`.
* Body: `{"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "1:1"}, "seed": seed}}`. Omit `seed` when it is None.
* The image is the first `candidates[0].content.parts[*].inlineData` (`mimeType`, base64 `data`).
* `usage` is `usageMetadata` verbatim.

- [ ] **Step 1: Write the failing tests** (use `httpx.MockTransport`):

```python
def test_writes_decoded_image_and_returns_usage(tmp_path):
    png = b"\x89PNG\r\n\x1a\n" + b"x" * 20
    body = {"candidates": [{"finishReason": "STOP", "content": {"parts": [
        {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(png).decode()}}]}}],
        "usageMetadata": {"candidatesTokenCount": 1290}}
    seen = {}
    def handler(req):
        seen["url"], seen["key"], seen["body"] = str(req.url), req.headers["x-goog-api-key"], json.loads(req.content)
        return httpx.Response(200, json=body)
    r = GI.generate_image("a scorpion", str(tmp_path / "c.png"), seed=11, api_key="k",
                          transport=httpx.MockTransport(handler))
    assert open(r.path, "rb").read() == png
    assert r.usage == {"candidatesTokenCount": 1290} and r.finish_reason == "STOP"
    assert seen["url"].endswith("/models/gemini-nano-banana-2.1:generateContent")
    assert seen["key"] == "k"
    assert seen["body"]["generationConfig"]["seed"] == 11
    assert seen["body"]["generationConfig"]["responseModalities"] == ["IMAGE"]

def test_seed_none_is_omitted(tmp_path): ...   # "seed" not in generationConfig

def test_no_image_part_raises_with_reason(tmp_path):
    body = {"candidates": [{"finishReason": "IMAGE_SAFETY", "content": {"parts": [{"text": "cannot"}]}}]}
    with pytest.raises(GI.GeminiImageError, match="IMAGE_SAFETY.*cannot"):
        GI.generate_image("x", str(tmp_path / "c.png"), api_key="k",
                          transport=httpx.MockTransport(lambda r: httpx.Response(200, json=body)))
    assert not (tmp_path / "c.png").exists()

def test_http_error_names_status_and_message(tmp_path): ...  # 400 {"error":{"message":"bad field"}} -> GeminiImageError matching "400.*bad field"

def test_missing_key_raises_before_request(tmp_path, monkeypatch): ...  # GEMINI_API_KEY unset, api_key None -> GeminiImageError matching "GEMINI_API_KEY"; transport never called
```

- [ ] **Step 2: Run them to make sure they fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests ../.venv/bin/python -m pytest tests/test_gemini_image.py -q` (in the worktree, use the main checkout's interpreter `<repo>/mcp_harness/.venv/bin/python`).
Expected: FAIL, `ModuleNotFoundError: gemini_image`.

- [ ] **Step 3: Implement `generate_image`** as specified above. The key comes from `api_key or os.environ.get("GEMINI_API_KEY")`. Write the image to a temp file, then `os.replace` it to `out_path`, so a failure never leaves a partial file.

- [ ] **Step 4: Run the tests to make sure they pass.** Expected: 5 passed.

- [ ] **Step 5: Live probe (owner-approved, about $0.03).** Do this once only, after `.env` is linked. Generate `"A full-body 3D render of a single scorpion …"` (`CONCEPT_PROMPT_TEMPLATE`) with seed 11 into `$CONCEPT_AB_DIR/probe/`. Check four things:
  * It returns an image.
  * Whether `seed` was accepted. If Gemini returns 400 on `seed` or `imageConfig`, remove that field from the request, update the test, and record the fact in the module docstring.
  * `usageMetadata`.
  * The per-image cost: the output image tokens times the per-token price on Google's pricing page for this model, read now. Record the price and its source URL in the docstring. **If the cost is above $0.068, stop and report to the owner.**

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/gemini_image.py mcp_harness/tests/test_gemini_image.py
git commit -m "gemini_image: Nano Banana image client (REST via httpx)"
```

---

### Task 2: Anatomy text

**Files:**
- Modify: `mcp_harness/subject_rewrite.py` (`problems` gains `max_words`; add `ANATOMY_SYSTEM`, `ANATOMY_MAX_WORDS = 40` and `anatomy`)
- Test: `mcp_harness/tests/test_subject_rewrite.py`

**Interfaces:**
- Produces:
  - `problems(description: str, subject: str, *, max_words: int = MAX_WORDS) -> list[str]`. The default is unchanged, so existing callers are untouched.
  - `async anatomy(client, subject: str) -> str`. It raises `RewriteFailed` after `MAX_REPAIRS`.

`ANATOMY_SYSTEM` tells the model three things. It must describe the animal's full visible anatomy for a text-to-image prompt: each limb type with its count and per-side count, pincers or claws, tail, fins, wings, tentacles or rays, and the head where distinct. It must use the same positivity, subject-word and no-scene rules as `SYSTEM`, in at most 40 words, and call `submit_subject`. It gives **no** leaf or flap convention and names no animal. Reuse `TOOL` and the repair loop. Factor the loop out of `rewrite` into a private `_submit(client, system, ask, image_path, subject, max_words)` so both functions share it.

- [ ] **Step 1: Write the failing tests**

```python
def test_anatomy_returns_valid_description():
    c = FakeClient([{"description": "scorpion with eight walking legs, four on each side, two large pincers, and a segmented tail curving up to a stinger"}])
    out = asyncio.run(SR.anatomy(c, "scorpion"))
    assert out.startswith("scorpion with eight walking legs")
    prompt = json.dumps(c.calls[0])
    assert "scorpion" in prompt and "convention" not in prompt.lower() and "leaf" not in prompt.lower()

def test_anatomy_allows_40_words_rewrite_still_25():
    assert SR.problems("crab " + "big " * 30, "crab", max_words=40) == []
    assert any("at most 25 words" in e for e in SR.problems("crab " + "big " * 30, "crab"))

def test_anatomy_repairs_a_negation():
    c = FakeClient([{"description": "dolphin with no legs"},
                    {"description": "dolphin with two pectoral flippers, a dorsal fin and a tail fluke"}])
    assert "flippers" in asyncio.run(SR.anatomy(c, "dolphin"))
    assert len(c.calls) == 2
```

- [ ] **Step 2: Run them.** Expected: FAIL, `AttributeError: anatomy`.
- [ ] **Step 3: Implement** as described. Every existing test in `test_subject_rewrite.py` must still pass unchanged.
- [ ] **Step 4: Run `tests/test_subject_rewrite.py`.** Expected: everything passes.
- [ ] **Step 5: Commit:** `git commit -m "subject_rewrite: anatomy() writes full visible anatomy from the subject word"`

---

### Task 3: Arms, cells, checklist and spend ledger

**Files:**
- Create: `mcp_harness/concept_ab/__init__.py` (empty), `mcp_harness/concept_ab/arms.py`, `mcp_harness/concept_ab/anatomy_checklist.json`
- Test: `mcp_harness/tests/test_concept_ab.py`

**Interfaces:**
- Produces:
  - `SUBJECTS: tuple[str, ...]`: the 17 manifest subjects in manifest order ("guinea pig" keeps its space).
  - `slug(subject) -> str`: lowercase, with spaces turned into `_`.
  - `@dataclass(frozen=True) Arm(name: str, image_model: str, template: str, uses_anatomy: bool, candidates: int = 1)`, `ARMS: dict[str, Arm]` for "A" to "D", and `arm_e(winner: str) -> Arm` for E.
  - `PHOTO_TEMPLATE: str`
  - `seed_for(arm: str, round_: int, candidate: int = 0) -> int`
  - `cell_dir(root: str, arm: str, subject: str, round_: int) -> str`: `<root>/<arm>/<slug>/r<round>`.
  - `concept_prompt_for(arm: Arm, subject: str, anatomy_text: str | None) -> str`
  - `load_checklist() -> dict[str, list[dict]]`; `checklist_text(subject) -> str`
  - `class Ledger(path: str, cap_usd: float = 15.0, price_usd: float = 0.034)` with `.spent() -> float`, `.charge(n_images: int, note: str) -> None` (raises `BudgetExceeded` when the spend plus `n_images * price` would exceed the cap), and `.record_usage(cell: str, usage: dict)`.

**Pinned values:**
* Arm A: `image_model="flux-schnell"`, `CONCEPT_PROMPT_TEMPLATE`.
* Arm B: Nano Banana 2.1, `CONCEPT_PROMPT_TEMPLATE`, `uses_anatomy=False`.
* Arm C: as B, but `uses_anatomy=True`.
* Arm D: `PHOTO_TEMPLATE`, `uses_anatomy=True`.
* Arm E: `candidates=4`, a copy of the round-1 winner among C and D. `ARMS["E"]` is built by `arm_e(winner: str) -> Arm`.
* Seeds: round 1 = 11. Round 2 = 22. Arm E candidates: 101–104.
* When `uses_anatomy` is set, the anatomy text fills `{subject}`, the way `subject_description` does today.

`PHOTO_TEMPLATE` (exact copy):
`"A full-body wildlife photograph of a single {subject}, three-quarter side view, the entire animal in frame with every leg, the tail and all appendages clearly visible and separated from the body, centered, against a plain uncluttered background, natural daylight, sharp focus, no props, no text"`

**Checklist data.** The schema per subject is `[{"part": "walking legs", "count": 8, "note": "4 per side"}, ...]`. Draft all 17 from each manifest `derivation` text, but count **visible** parts, not the leaf convention:
* scorpion: 8 walking legs, 2 pincers, 1 segmented tail with stinger
* dolphin: 2 pectoral flippers, 1 dorsal fin, 1 tail fluke, 1 head with beak
* elephant: 4 legs, 1 trunk, 2 ears, 1 tail, 2 tusks only if the photo shows them
* Leave out digits and toes.

The owner corrects the checklist on the review page. The draft is committed now and edited later.

- [ ] **Step 1: Write the failing tests**

```python
def test_seventeen_subjects_no_tardigrade():
    assert len(A.SUBJECTS) == 17 and not {"tardigrade", "water bear"} & set(A.SUBJECTS)

def test_cell_dir_layout(tmp_path):
    assert A.cell_dir(str(tmp_path), "C", "guinea pig", 2).endswith("C/guinea_pig/r2")

def test_prompts_per_arm():
    assert "3D render of a single scorpion," in A.concept_prompt_for(A.ARMS["B"], "scorpion", None)
    p = A.concept_prompt_for(A.ARMS["D"], "scorpion", "scorpion with eight walking legs")
    assert p.startswith("A full-body wildlife photograph of a single scorpion with eight walking legs,")

def test_checklist_covers_every_subject_with_counts():
    cl = A.load_checklist()
    assert set(cl) == set(A.SUBJECTS)
    assert all(isinstance(p["count"], int) and p["count"] > 0 for parts in cl.values() for p in parts)
    assert {p["part"] for p in cl["scorpion"]} >= {"walking legs", "pincers"}

def test_ledger_refuses_past_cap(tmp_path):
    L = A.Ledger(str(tmp_path / "ledger.json"), cap_usd=0.10, price_usd=0.034)
    L.charge(2, "b"); assert round(L.spent(), 3) == 0.068
    with pytest.raises(A.BudgetExceeded): L.charge(1, "c")
    assert round(A.Ledger(str(tmp_path / "ledger.json"), cap_usd=0.10).spent(), 3) == 0.068  # persisted
```

- [ ] **Step 2: Run them.** Expected: FAIL (no module).
- [ ] **Step 3: Implement `arms.py` and write `anatomy_checklist.json`.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `git commit -m "concept_ab: arms, cells, anatomy checklist draft, spend ledger"`

---

### Task 4: Resumable runner (generate + lift)

**Files:**
- Create: `mcp_harness/concept_ab/run.py`, `mcp_harness/concept_ab/__main__.py`
- Test: `mcp_harness/tests/test_concept_ab.py`

**Interfaces:**
- Consumes: Task 1 `generate_image`, Task 2 `anatomy`, Task 3 `ARMS`, `cell_dir`, `seed_for`, `concept_prompt_for`, `Ledger`, plus `mesh_acquire.TwoStageProvider`, `HUNYUAN_SHAPE_KWARGS`, `FLUX_IMAGE_KWARGS`, `CONCEPT_PROMPT_TEMPLATE` and `_is_hf_quota_exhaustion_error`.
- Produces:
  - `run_cells(root: str, arms: list[str], round_: int, subjects: list[str], *, llm=None, image_fn=generate_image, provider_factory=None, ledger=None) -> RunReport`
  - `@dataclass RunReport(done: list[str], skipped: list[str], failed: dict[str, str], stopped_for_quota: bool)`
  - `class QuotaStop(Exception)`
  - Each cell's `meta.json`: `{arm, subject, round, seed, prompt, anatomy_text, image_model, usage, utc}`.
  - Anatomy texts are cached in `<root>/anatomy/<slug>.txt`, written once per subject and reused by C, D and E.
  - CLI: `python -m concept_ab run --arms A,B,C,D --round 1 [--subjects scorpion,dog] [--root DIR]`.

**Behaviour:**
* **Skip finished cells.** A cell with `mesh.glb` is skipped.
* **Reuse an existing image.** A cell with `concept.png` but no mesh only re-lifts it. No new image is generated and nothing is charged.
* **Arm A** builds `TwoStageProvider(image_kwargs={**FLUX_IMAGE_KWARGS, "seed": seed}, mesh_kwargs=dict(HUNYUAN_SHAPE_KWARGS), prompt_template=CONCEPT_PROMPT_TEMPLATE, token=HF_TOKEN)` and calls `.generate(subject, cell)`.
* **Gemini arms:**
  1. `ledger.charge(1)`
  2. `image_fn(prompt, cell/concept.png, seed=...)`
  3. `ledger.record_usage`
  4. `TwoStageProvider(reuse_concept=True, mesh_kwargs=..., token=...)` `.generate(subject, cell)`
* **Quota.** A `RuntimeError` whose `__cause__` satisfies `_is_hf_quota_exhaustion_error` raises `QuotaStop`. The CLI prints the stopped cell and exits 4. Any other exception is recorded in `failed[cell]` and the run moves to the next cell.
* **Budget.** `BudgetExceeded` stops the run with exit code 5.

- [ ] **Step 1: Write the failing tests** with a fake provider, image function and LLM:

```python
def test_runs_each_cell_once_and_skips_done(tmp_path): ...       # arms B,C x [scorpion]; second call -> all skipped, image_fn called 2 times total
def test_anatomy_written_once_and_used_by_c_and_d(tmp_path): ... # FakeClient payload used once; C and D prompts contain it; B prompt does not
def test_concept_without_mesh_relifts_without_charging(tmp_path): ...
def test_quota_stops_run_and_rerun_resumes(tmp_path):
    # provider raises RuntimeError("mesh stage ... quota") from a cause the classifier accepts on the 2nd cell
    # -> RunReport.stopped_for_quota, 1 done; rerun with a healthy provider -> 1 skipped, 1 done
def test_other_failures_recorded_and_run_continues(tmp_path): ...
def test_meta_json_records_seed_prompt_model(tmp_path): ...
```

For the quota test's cause, take an exception message from `tests/test_hf_error_classification.py` that `_is_hf_quota_exhaustion_error` accepts. Reuse it; don't invent one.

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement `run.py` and the `run` subcommand in `__main__.py`.** `__main__` calls `env_config.load_env()` and sets `LLM_MAX_TOKENS` the way `pleatwright.__main__._client` does.
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `git commit -m "concept_ab: resumable generate+lift runner with quota and budget stops"`

---

### Task 5: Judge: assess and pick

**Files:**
- Create: `mcp_harness/concept_ab/judge.py`
- Test: `mcp_harness/tests/test_concept_ab.py`

**Interfaces:**
- Produces:
  - `async assess(client, image_path: str, anatomy: str) -> dict`, returning `{"parts": [{"part", "expected", "seen", "attached"}], "extras": [str], "passed": bool, "mismatches": int}`
  - `async pick(client, image_paths: list[str], anatomy: str) -> dict`, returning `{"index": int, "none_acceptable": bool, "assessments": [dict]}`
  - `JUDGE_MODEL = "claude-sonnet-5"`

**How it works:**
* `assess` makes one `submit_assessment` tool turn through `llm_client.run_turn`, as `subject_rewrite` does. The tool schema takes `parts[]` and `extras[]`.
* The system prompt asks the model to:
  1. List the parts the anatomy text names, with their expected counts.
  2. Count each part visible in the image, and say whether it is attached to the body.
  3. List anything visible that the text does not name: an extra limb, a floating or detached piece, a second animal.
  4. Answer per part and never give an overall verdict.
* It allows "none acceptable" through `pick`.
* **Computed in code:** `passed = all(seen == expected and attached) and not extras`. `mismatches` is the number of failing parts plus `len(extras)`.
* `pick` assesses each image and returns the first passing index. With no pass, it returns the index with the fewest mismatches and sets `none_acceptable=True`.
* Use the repair loop pattern from `subject_rewrite` for a missing or garbled tool call, with at most 2 repairs. If it still fails, return `{"passed": False, "error": "..."}` and do not raise.

- [ ] **Step 1: Write the failing tests**

```python
def test_verdict_is_computed_not_trusted():
    c = FakeClient([{"parts": [{"part": "walking legs", "expected": 8, "seen": 7, "attached": True}],
                     "extras": [], "verdict": "pass"}], call_name="submit_assessment")
    r = asyncio.run(J.assess(c, img, "scorpion with eight walking legs"))
    assert r["passed"] is False and r["mismatches"] == 1

def test_extras_fail_even_when_parts_match(): ...   # floating blob in extras -> passed False
def test_pick_first_pass_else_fewest_mismatches(): ...  # [fail(2), pass, pass] -> 1; [fail(3), fail(1)] -> 1, none_acceptable True
def test_assess_sends_the_image_and_never_the_checklist_word(): ...  # the message has an image_url part; no "checklist" in the prompt
```

`FakeClient` in `test_gated_pipeline.py` takes `call_name` through `FakeResult`. Extend `FakeClient` with a `call_name` keyword, defaulting to `"submit_tree"`, if it lacks one.

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `git commit -m "concept_ab: Claude judge; pass/fail computed from per-part counts"`

---

### Task 6: Draft scores and the review page

**Files:**
- Create: `mcp_harness/concept_ab/review.py`
- Test: `mcp_harness/tests/test_concept_ab.py`

**Interfaces:**
- Consumes: Task 5 `assess`, Task 3 `checklist_text`, `cell_dir`, `SUBJECTS`, and `vlm_render.render_mesh_views`.
- Produces:
  - `ensure_photo_cells(root, library_dir) -> None`: copies `meshes/<slug>.glb` and `photos/<slug>.png` into `<root>/photo/<slug>/r1/` as `mesh.glb` and `concept.png`.
  - `async draft_scores(root, client, *, cells=None) -> int`: for each cell with `mesh.glb`, it renders `mesh_views.png` if missing, then writes `draft.json = {"mesh": assess(mesh_views.png, checklist_text), "image": assess(concept.png, checklist_text)}`. It skips cells that already have `draft.json` and returns how many it wrote.
  - `build_review(root, round_) -> str`: writes `<root>/review_r<round>.html` and returns its path.
  - CLI: `python -m concept_ab draft` and `python -m concept_ab review --round 1`.

**The page:**
* **Layout.** One self-contained HTML file with images referenced by relative path. One section per subject, in this order:
  1. The checklist, editable inline as count inputs.
  2. One row per arm, the `photo` row first, then A–E as present. Each row shows the concept image, the mesh views, and the draft per-part table.
* **Inputs.** Each row has a mesh pass/fail toggle and an image pass/fail toggle, both pre-filled from the draft, plus a note box.
* **Saving.** A "Download scores.json" button saves `{"round": n, "checklist": {...edited...}, "cells": {"<arm>/<slug>/r<n>": {"mesh": "pass"|"fail", "image": "pass"|"fail", "note": str}}}`. The owner saves it as `<root>/scores_r<n>.json`.
* **Blinding.** Cells are labelled by arm letter only, and the page has no legend saying which model an arm is. The legend stays in the spec, so the owner judges anatomy without knowing the model.

- [ ] **Step 1: Write the failing tests**

```python
def test_photo_cells_copied(tmp_path): ...            # fake library dir with meshes/dog.glb + photos/dog.png
def test_draft_scores_skip_existing(tmp_path): ...    # fake assess via FakeClient; second call writes 0
def test_review_page_has_every_cell_and_prefills(tmp_path):
    # two cells with draft.json (one pass, one fail); build_review -> html contains both cell ids,
    # the 'checked' state matches the drafts, and the page contains no model names ("gemini", "flux", "banana")
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.** Use the stdlib only (`html.escape`, f-strings). The download is a short inline `<script>` that serializes the form to a Blob.
- [ ] **Step 4: Run them.** Expected: PASS. Then open a page generated from fake cells in the in-app browser and check the download produces valid JSON.
- [ ] **Step 5: Commit:** `git commit -m "concept_ab: draft scores + blinded review page with scores.json export"`

---

### Task 7: Scoring and picker calibration

**Files:**
- Create: `mcp_harness/concept_ab/score.py`
- Test: `mcp_harness/tests/test_concept_ab.py`

**Interfaces:**
- Produces:
  - `tally(scores: dict, root: str) -> dict`, returning `{"by_arm": {arm: {"round": n, "passed": int, "scored": int}}, "photo_bar": int, "good_enough": {arm: bool}, "unscored": [cell_id]}`
  - `async calibrate(root, client, scores) -> dict`: runs `assess` on every scored A–D `concept.png` using the subject's **anatomy text**, not the checklist. Returns `{"agree": int, "total": int, "false_reject": int, "false_accept": int}` against the owner's image labels.
  - `winner(tally) -> str`: the Gemini arm (B, C or D) with the most passes. On a tie, fewer arms using anatomy text wins (simpler ships), then B < C < D.
  - CLI: `python -m concept_ab score --round 1` prints the tally as a table and writes `tally_r<n>.json`. `python -m concept_ab calibrate`.
- `good_enough[arm] = passed >= photo_bar - 1`.

- [ ] **Step 1: Write the failing tests**

```python
def test_unscored_cells_reported_not_failed(tmp_path):
    # cells A/dog/r1 and A/cat/r1 exist on disk; scores only has A/dog/r1 = pass
    t = S.tally({"round": 1, "cells": {"A/dog/r1": {"mesh": "pass", "image": "pass"}}}, str(tmp_path))
    assert t["by_arm"]["A"] == {"round": 1, "passed": 1, "scored": 1} and "A/cat/r1" in t["unscored"]

def test_good_enough_is_photo_bar_minus_one(): ...   # photo 15, arm 14 -> True, arm 13 -> False
def test_winner_tie_prefers_simpler_arm(): ...       # B=12, C=12, D=11 -> "B"
def test_calibrate_counts_false_rejects_and_accepts(): ...
```

- [ ] **Step 2: Run them.** Expected: FAIL.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `git commit -m "concept_ab: tally, good-enough bar, winner, picker calibration"`

---

### Task 8: Secondary signal (tree and fold)

**Files:**
- Create: `mcp_harness/concept_ab/trees.py`
- Test: `mcp_harness/tests/test_concept_ab.py`

**Interfaces:**
- Consumes: `gated_pipeline.start`, `pleatwright.__main__.tree_file`, `pleatwright.pipeline.run`, and `fixtures/full17_v3_sticks/<slug>_*.json`.
- Produces:
  - `artifact_leaf_count(subject) -> int`: the most common leaf count across that subject's artifact trees. Scorpion → 11, dolphin → 5.
  - `async tree_signal(root, client, *, cells=None) -> dict`: per cell, `{"leaves": int | None, "expected": int, "match": bool, "folded": bool, "failure": str | None}`, written to `<cell>/tree_signal.json`. Cells that already have it are skipped.
  - CLI: `python -m concept_ab trees`.

It uses Haiku 5.5, the default `claude` preset, with no human gate. A state that is not `awaiting_review` is recorded as a failure. The fold is `pipeline.run(tree.json, <cell>/fold, verbose=False)`. A `StageError` or a `"failure"` key means `folded=False`, with the stage name.

- [ ] **Step 1: Write the failing tests**

```python
def test_artifact_leaf_count_uses_tree_convention():
    assert T.artifact_leaf_count("scorpion") == 11 and T.artifact_leaf_count("dolphin") == 5

def test_tree_signal_records_failure_without_raising(tmp_path, monkeypatch): ...  # monkeypatch gated_pipeline.start -> failed state
```

- [ ] **Step 2: Run them.** Expected: FAIL. **Step 3: Implement.** **Step 4: Run them.** Expected: PASS.
- [ ] **Step 5: Commit:** `git commit -m "concept_ab: secondary signal -- authored-tree leaf count and fold per mesh"`

Then run the whole suite: `make test` from the worktree root with `PYTHON` set to the main checkout's venv. Expected: all tests pass.

---

### Task 9: Round 1 (A–D), then owner review. Owner gate.

No code. This is an operational task, and the results go in `$CONCEPT_AB_DIR`.

- [ ] **Step 1:** Link `.env` (see File Structure). Check that `GEMINI_API_KEY`, `HF_TOKEN` and `ANTHROPIC_API_KEY` are set, printing names only and never values.
- [ ] **Step 2:** Run `python -m concept_ab run --arms A,B,C,D --round 1`. Run it in the background; it is long-running because of the ZeroGPU queue. On exit code 4 (quota), report it and rerun later; finished cells are kept. Expect 68 lifts, 51 Gemini images and about $1.75 on the ledger.
- [ ] **Step 3:** Run `python -m concept_ab draft`, then `python -m concept_ab review --round 1`. Open the page for the owner. Ask them to:
  * Correct the checklist first.
  * Then score each cell.
  * Save the result as `scores_r1.json`.
- [ ] **Step 4:** After the owner saves the scores:
  * `python -m concept_ab score --round 1`, `python -m concept_ab calibrate` and `python -m concept_ab trees`.
  * Report to the owner: the tally, the photo bar, the good-enough flags, the winner, the calibration figures, and the anatomy texts that disagree with the checklist.
  * Commit the edited checklist back into `mcp_harness/concept_ab/anatomy_checklist.json`.

**Stop. The owner decides round 2.**

### Task 10: Round 2, optional arm E, and the write-up

- [ ] **Step 1:** Run `python -m concept_ab run --arms A,<winner> --round 2`, then `draft`, `review --round 2`, the owner's scoring, and `score --round 2`.
- [ ] **Step 2: Arm E.** Run it only if no arm is good enough on both rounds, or if the owner asks: `run --arms E --round 1`. Each cell generates candidates seeded 101–104, saved as `candidate_<i>.png`. `judge.pick` chooses one using the anatomy text, the choice is copied to `concept.png` and lifted, and `pick.json` is recorded. This branch lives in `run.py` and is unit-tested with a fake `pick` in Task 4's test file **before** it is used: write `test_arm_e_lifts_only_the_picked_candidate`. Expected cost: 68 images, about $2.30.
- [ ] **Step 3: Write-up.** Write `docs/superpowers/evidence/2026-10-16-concept-image/README.md` with:
  * the arms and each arm's tally per round
  * the photo bar
  * calibration
  * spend from the ledger
  * a per-subject table with mechanism notes for each failure, e.g. "scorpion C r1: 7 legs per side"
  * a contact sheet of the photo row and the winning arm
  
  Update project memory with the outcome.
- [ ] **Step 4:** Commit the evidence. Then ask the owner whether to start the Phase 2 design (shipping the winner as the `hf2` image stage). That is spec §4 and gets a separate short design.

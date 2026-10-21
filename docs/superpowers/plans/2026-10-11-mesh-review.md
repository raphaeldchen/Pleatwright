# Mesh review with feedback, and approval-ranked meshes: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** In the app, a new run first shows its concept image and mesh for
review. The user approves, or gives feedback that the VLM turns into a better
subject description before a fresh-seed redraw. Each subject's meshes are rated,
and the best proven one is served first.

**Architecture:**
* **Mesh draws:** `mesh_acquire` can draw with a subject description and a seed.
  Both enter the cache key only when set, so default keys stay byte-identical.
* **Ratings:** `mesh_ratings.py` holds the subject key, the Wilson ranking and a
  per-cache-folder `ratings.json`.
* **Rewrite:** `subject_rewrite.py` is one forced-tool VLM turn with validation
  and repairs.
* **App:** the app's tools gain mesh rounds (`first_mesh`, `revise_mesh`,
  `approve_mesh`, `retry_mesh`) recorded in `author/mesh_state.json`.
  `guided.Manager` dispatches `message`/`approve` on the review's `stage`.
* **UI:** the web UI keys image and mesh rounds like tree rounds, and labels the
  review by stage.

**Tech Stack:** Python 3.14, pytest, FastAPI app, React with vitest. No new
dependencies.

**Spec:** `docs/superpowers/specs/2026-10-11-mesh-review-design.md` (commit
811a64a1). Read it first.

**Refinements to the spec**, each with its reason, recorded as rulings and
written back into the spec in Task 7:
1. **Ratings live in a sibling `ratings.json`, not inside `meta.json`.**
   `write_mesh_meta` rewrites `meta.json` whole, and app tests disable
   provenance writes (`IDE_MESH_PROVENANCE=0`). Counts kept in `meta.json` would
   be lost or never written. The per-cache-folder convention is kept.
2. **A rewrite that still fails validation after its repairs goes back to mesh
   review** (`retry="review_mesh"`) and records nothing. The user rephrases,
   instead of the round being retried with the same words. A failed *draw*
   still uses `retry="make_mesh"`, as in the spec.
3. **`approve` carries the model pill.** Approving a mesh starts tree
   authoring, so it needs the model choice. The websocket `approve` command
   gains an optional `model`.

## Global Constraints

* **Default draws keep today's cache keys byte for byte.** The live entry
  `moose-0ea544523bcf6966` must still be the key for prompt "moose".
* **The CLI (`python -m pleatwright author/run`) is unchanged** (owner: "app
  only for now").
* **Tests use only artifact trees or named edits of them** (CLAUDE.md §5). App
  tests run offline: the `fake` mesh provider plus `FakeClient`.
* **Never use tardigrade or water bear** as a test subject.
* **The template `CONCEPT_PROMPT_TEMPLATE` is not edited.** Only its `{subject}`
  slot changes.
* **Rewrite rules:** at most 25 words; subject words kept; no negations
  (`no`, `not`, `without`, `never`, `none`, `*less`); no scene words
  (`background`, `render`, `lighting`, `studio`, `shadow`, `camera`, `view`);
  at most 2 repair turns; `tool_choice="required"`.
* **Ranking:** "proven" means at least 1 approval. Rank by Wilson lower bound
  with z = 1.96, then approvals, then newest.
* **Interpreter:** `PY=<repo>/mcp_harness/.venv/bin/python`.
  * Pipeline tests, from `mcp_harness/`: `PYTHONPATH=.:tests $PY -m pytest tests/<file> -q`.
  * App tests, from the repo root: `make PYTHON=$PY test-app`.
  * Web tests, from `app/web`: `npx vitest run` and `npm run build`.
* **Commits** end with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

1. **Feedback given as a negation** ("no tail", "legs shouldn't be fused"). The
   rewrite must come back phrased positively. A negated first answer gets a
   repair turn that names the word. (Task 3,
   `test_a_negated_rewrite_gets_a_repair_that_names_the_word`)
2. **A rewrite that never validates.** The run returns to mesh review on the
   same round. No rejection is recorded and no round is added. (Task 4,
   `test_a_rewrite_that_never_validates_goes_back_to_mesh_review`)
3. **A redraw that fails at the mesh Space** (HF down or out of quota). The
   failure shows with Retry, and Retry redraws that round with the same
   description and seed. (Task 4,
   `test_a_failed_redraw_retries_the_same_description_and_seed`)
4. **A proven cache entry whose `mesh.glb` is gone or empty.** It is never
   served. (Task 2, `test_best_proven_skips_a_missing_or_empty_mesh`)
5. **Approving a mesh with no usable LLM key.** It is refused before anything is
   logged, because tree authoring would need the VLM. (Task 4,
   `test_approving_a_mesh_needs_the_llm`)

---

## File structure

| file | change | responsibility |
|---|---|---|
| `mcp_harness/mesh_acquire.py` | modify | `TwoStageProvider(subject_description=)`; `get_provider(..., description=, seed=)`; `acquire_mesh(..., description=, seed=)`; `cached_files(key_dir)` |
| `mcp_harness/mesh_ratings.py` | **create** | `subject_key`, `wilson_lower_bound`, `read_ratings`, `record_verdict`, `best_proven` |
| `mcp_harness/subject_rewrite.py` | **create** | `TOOL`, `SYSTEM`, `problems`, `RewriteFailed`, `rewrite` |
| `mcp_harness/tests/test_mesh_ratings.py`, `test_subject_rewrite.py` | **create** | unit tests |
| `mcp_harness/tests/test_two_stage_provider.py`, `test_mesh_acquire.py` | modify | description, seed and key tests |
| `app/server/pleatwright_app/tools.py` | modify | mesh rounds, `mesh_state.json`, `present` emits `stage="tree"` |
| `app/server/pleatwright_app/guided.py` | modify | `phase()` stage; `create`/`message`/`approve`/`retry` dispatch |
| `app/server/pleatwright_app/api.py` | modify | `approve` passes `model` |
| `app/server/record_fixture.py` | modify | the recorded run approves its mesh |
| `app/server/tests/test_guided.py`, `test_api.py` | modify | new mesh tests; existing flows approve round 0's mesh |
| `app/web/src/types.ts`, `runStore.ts`, `api.ts`, `components/Chat.tsx`, `components/Viewer.tsx` | modify | round keys, review stage, labels |
| `app/web/src/runStore.test.ts`, `__fixtures__/bird_run.events.jsonl` | modify / re-record | |
| `CLAUDE.md`, the spec | modify | Task 7 |

---

### Task 1: Mesh draws by description and seed

**Files:**
- Modify: `mcp_harness/mesh_acquire.py` (`TwoStageProvider.__init__`, `cache_settings`, `generate`; `get_provider`; `acquire_mesh`; a new `cached_files` beside `_cached_concept`)
- Test: `mcp_harness/tests/test_two_stage_provider.py`, `mcp_harness/tests/test_mesh_acquire.py`

**Interfaces:**
- Produces:
  * `get_provider(name=None, *, description=None, seed=None)`;
  * `acquire_mesh(prompt, *, provider=None, provider_name=None, cache_dir=None, progress=None, description=None, seed=None) -> str`, the path of `mesh.glb` inside its cache folder;
  * `cached_files(key_dir) -> tuple[str | None, str]`, giving (concept image or None, `mesh.glb`).

- [ ] **Step 1: Write the failing tests.** Append to `mcp_harness/tests/test_two_stage_provider.py`:

```python
def test_a_subject_description_fills_the_template_subject_slot(tmp_path, png, glb):
    """Mesh review (2026-10-11): the VLM's rewrite replaces only {subject}; the
    measured template around it is unchanged."""
    log = []
    p = _provider({"img/space": png, "mesh/space": glb}, log,
                  prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE,
                  subject_description="bull moose, four long well-separated legs")
    p.generate("a moose", str(tmp_path / "out"))
    sent = log[0]["args"][0]
    assert sent == mesh_acquire.concept_prompt("bull moose, four long well-separated legs")
    assert sent.startswith("A full-body 3D render of a single bull moose, four long")


def test_the_description_enters_the_cache_settings_only_when_set(png, glb):
    plain = _provider({}, [], prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE)
    assert "subject_description" not in plain.cache_settings
    d = _provider({}, [], prompt_template=mesh_acquire.CONCEPT_PROMPT_TEMPLATE,
                  subject_description="bull moose")
    assert d.cache_settings["subject_description"] == "bull moose"
```

Append to `mcp_harness/tests/test_mesh_acquire.py`:

```python
def test_default_hf2_draws_keep_todays_cache_key(monkeypatch):
    """The live cache entry for "moose" (drawn 2026-10-11) must stay reachable:
    adding description/seed must not move any default key."""
    for v in ("HF_IMAGE_SPACE_ID", "HF_MESH_SPACE_ID", "HF_IMAGE_API", "HF_MESH_API"):
        monkeypatch.delenv(v, raising=False)
    p = mesh_acquire.get_provider("hf2")
    assert mesh_acquire.cache_key("hf2", "moose", p.cache_settings) == "moose-0ea544523bcf6966"


def test_a_seed_or_a_description_gets_its_own_cache_key(monkeypatch):
    for v in ("HF_IMAGE_SPACE_ID", "HF_MESH_SPACE_ID", "HF_IMAGE_API", "HF_MESH_API"):
        monkeypatch.delenv(v, raising=False)
    plain = mesh_acquire.get_provider("hf2")
    seeded = mesh_acquire.get_provider("hf2", seed=48213)
    assert seeded.image_kwargs["seed"] == seeded.mesh_kwargs["seed"] == 48213
    assert seeded.image_kwargs["randomize_seed"] is False
    assert seeded.mesh_kwargs["randomize_seed"] is False
    described = mesh_acquire.get_provider("hf2", description="bull moose")
    keys = {mesh_acquire.cache_key("hf2", "moose", p.cache_settings)
            for p in (plain, seeded, described)}
    assert len(keys) == 3


def test_the_fake_provider_ignores_description_and_seed(tmp_path):
    a = mesh_acquire.acquire_mesh("a bird", provider_name="fake", cache_dir=str(tmp_path))
    b = mesh_acquire.acquire_mesh("a bird", provider_name="fake", cache_dir=str(tmp_path),
                                  description="a sparrow", seed=7)
    assert a == b


def test_cached_files_names_the_concept_and_the_mesh(tmp_path):
    (tmp_path / "mesh.glb").write_bytes(b"glTF")
    assert mesh_acquire.cached_files(str(tmp_path)) == (None, str(tmp_path / "mesh.glb"))
    (tmp_path / "concept.webp").write_bytes(b"RIFF")
    assert mesh_acquire.cached_files(str(tmp_path))[0] == str(tmp_path / "concept.webp")
```

- [ ] **Step 2: Run them; they fail.**

Run (from `mcp_harness/`): `PYTHONPATH=.:tests $PY -m pytest tests/test_two_stage_provider.py tests/test_mesh_acquire.py -q -k "description or seed or cache_key or cached_files" -p no:cacheprovider`

Expected: FAIL. `subject_description` is an unexpected keyword, and `get_provider`/`acquire_mesh` have no `seed`/`description`. `test_default_hf2_draws_keep_todays_cache_key` should already PASS; it pins the current behaviour.

- [ ] **Step 3: Implement.** In `TwoStageProvider.__init__`, add the keyword `subject_description=None` after `prompt_template=None`, and store it:

```python
        self.prompt_template = prompt_template
        # Mesh review (2026-10-11): the VLM's rewrite of the subject, from the
        # user's feedback. It fills the template's {subject} slot in place of the
        # prompt's subject; None draws the plain subject as before.
        self.subject_description = subject_description
```

In `cache_settings`, build the dict, then add the description only when set:

```python
        s = {"image_space": self.image_space, "image_api": self.image_api,
             "image_kwargs": plain(self.image_kwargs),
             "prompt_template": self.prompt_template,
             "mesh_space": self.mesh_space, "mesh_api": self.mesh_api,
             "mesh_kwargs": plain(self.mesh_kwargs)}
        if self.subject_description is not None:     # absent by default: keys unchanged
            s["subject_description"] = self.subject_description
        return s
```

In `generate`, stage 1:

```python
        subject = self.subject_description or prompt
        image_prompt = (concept_prompt(subject, self.prompt_template)
                        if self.prompt_template else subject)
```

Change `get_provider`'s signature to `def get_provider(name: str | None = None, *, description: str | None = None, seed: int | None = None) -> MeshProvider:`. In its `hf2` branch, build the kwargs first, apply the seed, then construct:

```python
    if name == "hf2":
        image_kwargs = (dict(FLUX_IMAGE_KWARGS)
                        if os.environ.get("HF_IMAGE_SPACE_ID", DEFAULT_HF_IMAGE_SPACE)
                        == DEFAULT_HF_IMAGE_SPACE else None)
        mesh_kwargs = (dict(HUNYUAN_SHAPE_KWARGS)
                       if os.environ.get("HF_MESH_SPACE_ID", DEFAULT_HF_MESH_SPACE)
                       == DEFAULT_HF_MESH_SPACE else None)
        if seed is not None:          # a fresh draw: both stages take this seed, still pinned
            for kw in (image_kwargs, mesh_kwargs):
                if kw is not None:
                    kw["seed"] = seed
        return TwoStageProvider(
            image_space=os.environ.get("HF_IMAGE_SPACE_ID", DEFAULT_HF_IMAGE_SPACE),
            image_api=os.environ.get("HF_IMAGE_API", DEFAULT_HF_IMAGE_API),
            mesh_space=os.environ.get("HF_MESH_SPACE_ID", DEFAULT_HF_MESH_SPACE),
            mesh_api=os.environ.get("HF_MESH_API", DEFAULT_HF_MESH_API),
            token=os.environ.get("HF_TOKEN") or None,
            prompt_template=CONCEPT_PROMPT_TEMPLATE,
            image_kwargs=image_kwargs, mesh_kwargs=mesh_kwargs,
            subject_description=description,
        )
```

Keep the two existing comments about "FLUX's slots, FLUX's Space only" and "only when the mesh stage IS the default Space" above the `image_kwargs` and `mesh_kwargs` lines.

Give `acquire_mesh` the keywords `description: str | None = None, seed: int | None = None` (after `progress=None`). Change `provider = provider or get_provider(name)` to:

```python
    provider = provider or get_provider(name, description=description, seed=seed)
```

Add, just below `_cached_concept`:

```python
def cached_files(key_dir: str) -> tuple[str | None, str]:
    """A cache folder's concept image (None if it has none) and its mesh.glb."""
    return _cached_concept(key_dir), os.path.join(key_dir, "mesh.glb")
```

- [ ] **Step 4: Run them; they pass.** Same command. Expected: all pass.

- [ ] **Step 5: Run the mesh suites whole.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_two_stage_provider.py tests/test_mesh_acquire.py -q -p no:cacheprovider`
Expected: all pass.

- [ ] **Step 6: Commit.**

```bash
git add mcp_harness/mesh_acquire.py mcp_harness/tests/test_two_stage_provider.py mcp_harness/tests/test_mesh_acquire.py
git commit -m "mesh_acquire: draw by subject description and seed; both key the cache only when set

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Mesh ratings

**Files:**
- Create: `mcp_harness/mesh_ratings.py`
- Test: `mcp_harness/tests/test_mesh_ratings.py`

**Interfaces:**
- Produces:
  * `subject_key(prompt: str) -> str`;
  * `wilson_lower_bound(approvals: int, rejections: int, z: float = 1.96) -> float`;
  * `read_ratings(key_dir) -> dict | None`;
  * `record_verdict(key_dir, *, approved: bool, run_id: str, subject: str, provider: str, prompt: str, description=None, seed=None, feedback: str = "") -> dict`;
  * `best_proven(cache_dir, provider, subject) -> str | None`;
  * the file `ratings.json`, with keys `subject`, `provider`, `prompt`,
    `description`, `seed`, `approvals` (int) and `rejections` (a list of
    `{feedback, run, utc}`).

- [ ] **Step 1: Write the failing tests.** Create `mcp_harness/tests/test_mesh_ratings.py`:

```python
"""Mesh ratings (spec 2026-10-11 §1): a subject key, Wilson ranking, and a
ratings.json beside each cached mesh."""
import json
import os

import pytest

import mesh_ratings as R


@pytest.mark.parametrize("prompt,key", [
    ("a moose", "moose"), ("Moose.", "moose"), ("the moose", "moose"),
    ("  A Moose!! ", "moose"), ("bull moose", "bull moose"), ("an antelope", "antelope"),
    ("can you make a fox", "can you make a fox")])
def test_subject_key(prompt, key):
    assert R.subject_key(prompt) == key


def test_wilson_ranks_many_approvals_above_one():
    assert R.wilson_lower_bound(0, 0) == 0.0
    assert R.wilson_lower_bound(9, 1) > R.wilson_lower_bound(1, 0)
    assert abs(R.wilson_lower_bound(1, 0) - 0.2065) < 1e-3


def _entry(root, name, glb=b"glTF", **ratings):
    d = root / name
    d.mkdir()
    if glb is not None:
        (d / "mesh.glb").write_bytes(glb)
    if ratings:
        (d / "ratings.json").write_text(json.dumps(ratings))
    return str(d)


def _r(approvals, rejections=0, provider="hf2", subject="moose"):
    return dict(subject=subject, provider=provider, prompt=subject, description=None,
                seed=None, approvals=approvals,
                rejections=[{"feedback": "x", "run": "r", "utc": "t"}] * rejections)


def test_record_verdict_counts_and_keeps_the_identity(tmp_path):
    d = _entry(tmp_path, "moose-1")
    R.record_verdict(d, approved=False, run_id="run-a", subject="moose", provider="hf2",
                     prompt="a moose", description="bull moose", seed=7, feedback="legs fused")
    r = R.record_verdict(d, approved=True, run_id="run-b", subject="moose", provider="hf2",
                         prompt="a moose", description="bull moose", seed=7)
    assert r["approvals"] == 1 and [x["feedback"] for x in r["rejections"]] == ["legs fused"]
    assert r["subject"] == "moose" and r["seed"] == 7 and r["description"] == "bull moose"
    assert R.read_ratings(d) == r
    assert not [f for f in os.listdir(d) if f.endswith(".tmp")]        # written atomically


def test_best_proven_ranks_by_wilson_then_approvals(tmp_path):
    _entry(tmp_path, "one-of-one", **_r(1, 0))
    best = _entry(tmp_path, "nine-of-ten", **_r(9, 1))
    _entry(tmp_path, "unrated")
    _entry(tmp_path, "rejected-only", **_r(0, 3))
    assert R.best_proven(str(tmp_path), "hf2", "moose") == best


def test_best_proven_needs_an_approval_and_matches_provider_and_subject(tmp_path):
    _entry(tmp_path, "fake-one", **_r(5, 0, provider="fake"))
    _entry(tmp_path, "elk-one", **_r(5, 0, subject="elk"))
    _entry(tmp_path, "no-votes", **_r(0, 0))
    assert R.best_proven(str(tmp_path), "hf2", "moose") is None
    assert R.best_proven(str(tmp_path / "missing"), "hf2", "moose") is None


def test_best_proven_skips_a_missing_or_empty_mesh(tmp_path):
    """Review focus 4: a proven folder whose mesh.glb is gone or empty is never served."""
    _entry(tmp_path, "gone", glb=None, **_r(9, 0))
    _entry(tmp_path, "empty", glb=b"", **_r(9, 0))
    ok = _entry(tmp_path, "ok", **_r(1, 0))
    assert R.best_proven(str(tmp_path), "hf2", "moose") == ok


def test_an_unreadable_ratings_file_is_ignored(tmp_path):
    d = _entry(tmp_path, "torn")
    (tmp_path / "torn" / "ratings.json").write_text("{not json")
    assert R.read_ratings(d) is None
    assert R.best_proven(str(tmp_path), "hf2", "moose") is None
```

- [ ] **Step 2: Run them; they fail.** Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_mesh_ratings.py -q -p no:cacheprovider`. Expected: collection ERROR, `ModuleNotFoundError: mesh_ratings`.

- [ ] **Step 3: Implement.** Create `mcp_harness/mesh_ratings.py`:

```python
"""Mesh ratings for the app's mesh review (spec 2026-10-11 §1).

Each cached mesh folder may hold a `ratings.json` beside its `mesh.glb` and
`meta.json`: who the mesh is for (subject, provider, prompt, description, seed)
and how reviewers judged it (approvals, rejections with their feedback). A
separate file, not fields in meta.json: write_mesh_meta rewrites meta.json
whole, and provenance writing can be disabled, so counts kept there could be
lost. A new run of a subject is served its best PROVEN mesh first: at least one
approval, ranked by the Wilson score lower bound (Evan Miller, "How Not To Sort
By Average Rating"), so 9 of 10 outranks 1 of 1.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
import re

RATINGS = "ratings.json"
_ARTICLE = re.compile(r"^(?:a|an|the)\s+")


def subject_key(prompt: str) -> str:
    """The prompt as a ratings key: lower-case, punctuation gone, one leading
    article dropped. "a moose", "Moose." and "the moose" share `moose`."""
    words = re.sub(r"[^a-z0-9]+", " ", prompt.lower()).split()
    return _ARTICLE.sub("", " ".join(words))


def wilson_lower_bound(approvals: int, rejections: int, z: float = 1.96) -> float:
    n = approvals + rejections
    if n == 0:
        return 0.0
    p = approvals / n
    return ((p + z * z / (2 * n) - z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n))
            / (1 + z * z / n))


def read_ratings(key_dir: str) -> dict | None:
    try:
        with open(os.path.join(key_dir, RATINGS)) as f:
            r = json.load(f)
    except (OSError, ValueError):
        return None
    return r if isinstance(r, dict) else None


def record_verdict(key_dir: str, *, approved: bool, run_id: str, subject: str,
                   provider: str, prompt: str, description: str | None = None,
                   seed: int | None = None, feedback: str = "") -> dict:
    """Count one review of the mesh in `key_dir`; return the updated record.
    Written atomically (temp file + os.replace), like the cache's meta.json."""
    r = read_ratings(key_dir) or {}
    for k, v in (("subject", subject), ("provider", provider), ("prompt", prompt),
                 ("description", description), ("seed", seed)):
        r.setdefault(k, v)
    r.setdefault("approvals", 0)
    r.setdefault("rejections", [])
    if approved:
        r["approvals"] += 1
    else:
        r["rejections"].append({"feedback": feedback, "run": run_id,
                                "utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")})
    path = os.path.join(key_dir, RATINGS)
    with open(path + ".tmp", "w") as f:
        json.dump(r, f, indent=1)
    os.replace(path + ".tmp", path)
    return r


def best_proven(cache_dir: str, provider: str, subject: str) -> str | None:
    """The folder of `subject`'s best proven mesh from `provider`, or None."""
    try:
        names = os.listdir(cache_dir)
    except OSError:
        return None
    ranked = []
    for name in names:
        d = os.path.join(cache_dir, name)
        r = read_ratings(d)
        if not r or r.get("provider") != provider or r.get("subject") != subject:
            continue
        a, rej = int(r.get("approvals", 0)), len(r.get("rejections", []))
        glb = os.path.join(d, "mesh.glb")
        if a < 1 or not os.path.isfile(glb) or os.path.getsize(glb) == 0:
            continue
        ranked.append((wilson_lower_bound(a, rej), a, os.path.getmtime(os.path.join(d, RATINGS)), d))
    return max(ranked)[3] if ranked else None
```

- [ ] **Step 4: Run them; they pass.** Same command. Expected: all pass.

- [ ] **Step 5: Commit.**

```bash
git add mcp_harness/mesh_ratings.py mcp_harness/tests/test_mesh_ratings.py
git commit -m "mesh_ratings: subject key, Wilson-ranked best proven mesh, ratings.json per cache folder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: The feedback rewrite

**Files:**
- Create: `mcp_harness/subject_rewrite.py`
- Test: `mcp_harness/tests/test_subject_rewrite.py`

**Interfaces:**
- Consumes: `llm_client.user_message_with_images(text, images)`; a client with
  `async run_turn(system, messages, tools)` (the real `LLMClient` or the tests'
  `FakeClient`).
- Produces:
  * `problems(description, subject) -> list[str]`;
  * `class RewriteFailed(Exception)`;
  * `async rewrite(client, subject, feedback: list[str], image_path: str | None) -> str`.

- [ ] **Step 1: Write the failing tests.** Create `mcp_harness/tests/test_subject_rewrite.py`:

```python
"""The mesh review's feedback rewrite (spec 2026-10-11 §3)."""
import asyncio
import json

import pytest

import subject_rewrite as SR
from test_gated_pipeline import FakeClient, Prose


@pytest.mark.parametrize("text,needle", [
    ("bull elk, long legs", "moose"),                        # subject words kept
    ("moose with no tail", "remove: no"),                    # negation
    ("tailless moose", "tailless"),
    ("moose, " + "very " * 30 + "tall", "at most 25 words"),
    ("moose on a white background", "background"),           # scene words belong to the template
])
def test_problems_name_the_rule_broken(text, needle):
    errs = SR.problems(text, "moose")
    assert errs and needle in " ".join(errs)


def test_a_good_description_has_no_problems():
    assert SR.problems("bull moose, four long well-separated legs, short stubby tail", "moose") == []
    assert SR.problems("Bull Moose with broad palmate antlers", "bull moose") == []


def test_rewrite_returns_the_description_from_one_forced_tool_call():
    c = FakeClient([{"description": "bull moose, four long well-separated legs"}])
    got = asyncio.run(SR.rewrite(c, "moose", ["the legs are fused"], None))
    assert got == "bull moose, four long well-separated legs"
    sent = json.dumps(c.calls[0]["messages"])
    assert "the legs are fused" in sent and "moose" in sent


def test_every_round_sends_the_original_subject_and_all_feedback():
    c = FakeClient([{"description": "moose, short stubby tail"}])
    asyncio.run(SR.rewrite(c, "moose", ["legs fused", "no tail"], None))
    sent = json.dumps(c.calls[0]["messages"])
    assert "legs fused" in sent and "no tail" in sent


def test_a_negated_rewrite_gets_a_repair_that_names_the_word():
    """Review focus 1: "no tail" must come back phrased positively."""
    c = FakeClient([{"description": "moose with no tail"}, {"description": "moose, short stubby tail"}])
    assert asyncio.run(SR.rewrite(c, "moose", ["no tail"], None)) == "moose, short stubby tail"
    repair = json.dumps(c.calls[1]["messages"][-1])
    assert "remove: no" in repair


def test_a_prose_answer_is_repaired_too():
    c = FakeClient([Prose("Sure! A moose with long legs."), {"description": "moose, long legs"}])
    assert asyncio.run(SR.rewrite(c, "moose", ["legs too short"], None)) == "moose, long legs"


def test_three_bad_answers_raise_rewrite_failed():
    c = FakeClient([{"description": "no"}] * 3)
    with pytest.raises(SR.RewriteFailed, match="could not rewrite"):
        asyncio.run(SR.rewrite(c, "moose", ["x"], None))
    assert len(c.calls) == 3
```

- [ ] **Step 2: Run them; they fail.** Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_subject_rewrite.py -q -p no:cacheprovider`. Expected: collection ERROR, no module `subject_rewrite`.

- [ ] **Step 3: Implement.** Create `mcp_harness/subject_rewrite.py`:

```python
"""Mesh review: turn the reviewer's feedback into a better subject description
(spec 2026-10-11 §3).

The description fills ONLY the {subject} slot of mesh_acquire's measured
concept template; the template itself is never touched (memory: concept-prompt
A/B). Every round starts from the original subject plus ALL feedback so far,
never from the previous rewrite, so edits cannot compound (Maestro, arXiv
2509.10704). Fixes are phrased positively: text-to-image models, FLUX/T5
included, tend to draw what a prompt says to omit (arXiv 2411.17066,
2410.23054).
"""
from __future__ import annotations

import json
import re

import llm_client

MAX_WORDS = 25
MAX_REPAIRS = 2
_NEGATION = re.compile(r"\b(?:no|not|without|never|none)\b|\b\w+less\b", re.IGNORECASE)
_SCENE = ("background", "render", "lighting", "studio", "shadow", "camera", "view")

TOOL = [{"type": "function", "function": {
    "name": "submit_subject",
    "description": "Submit the rewritten subject description.",
    "parameters": {"type": "object", "properties": {
        "description": {"type": "string",
                        "description": "One phrase, at most 25 words: the animal and its anatomy."}},
        "required": ["description"]}}}]

SYSTEM = (
    "You improve the SUBJECT of a fixed text-to-image prompt. The prompt is a "
    "full-body 3D render template that already sets the camera view, the plain "
    "white background and the lighting; your text replaces only the subject in "
    "'A full-body 3D render of a single <subject>, ...'. The image is turned into "
    "a 3D mesh, so the anatomy must be clear.\n"
    "Write ONE phrase of at most 25 words describing the animal and its body: "
    "legs, tail, head, appendages, their shape and how they separate. Keep the "
    "subject words exactly. Phrase every fix POSITIVELY, as what should be "
    "visible ('a short stubby tail', 'four long, well-separated legs'); never use "
    "no, not, without, never, none or words ending in -less. Do not describe the "
    "background, render, lighting, studio, shadow, camera or view. Call "
    "submit_subject with the phrase.")


class RewriteFailed(Exception):
    """No valid description after the repairs; the message says why."""


def problems(description: str, subject: str) -> list[str]:
    """What breaks the rewrite rules, each as an instruction the model can act on."""
    words = re.findall(r"[a-z]+", description.lower())
    errs = []
    missing = [w for w in subject.split() if w not in words]
    if missing:
        errs.append(f"keep the subject words: {', '.join(missing)} must appear")
    neg = sorted({m.group(0).lower() for m in _NEGATION.finditer(description)})
    if neg:
        errs.append("phrase every fix positively, as what should be visible; "
                    f"remove: {', '.join(neg)}")
    n = len(description.split())
    if n > MAX_WORDS:
        errs.append(f"at most {MAX_WORDS} words (this has {n})")
    scene = [w for w in _SCENE if w in words]
    if scene:
        errs.append(f"describe only the animal; the template already sets {', '.join(scene)}")
    return errs


async def rewrite(client, subject: str, feedback: list[str], image_path: str | None) -> str:
    """One forced submit_subject turn, with up to MAX_REPAIRS repairs."""
    ask = (f"The subject is: {subject}\n"
           "A reviewer looked at the concept image"
           + (" (attached)" if image_path else "")
           + " and the 3D mesh drawn from it, and said, in order:\n"
           + "\n".join(f"- {f}" for f in feedback)
           + "\n\nRewrite the subject so the next draw fixes all of it.")
    msgs = [llm_client.user_message_with_images(ask, [image_path]) if image_path
            else {"role": "user", "content": ask}]
    errs = ["no description yet"]
    for _ in range(MAX_REPAIRS + 1):
        r = await client.run_turn(SYSTEM, msgs, TOOL)
        if not r.tool_calls:
            errs = ["answer by calling submit_subject with the description"]
            msgs = msgs + [{"role": "assistant", "content": r.text or ""},
                           {"role": "user", "content": errs[0]}]
            continue
        call = r.tool_calls[0]
        try:
            description = str(json.loads(call.function.arguments).get("description", "")).strip()
        except (ValueError, AttributeError):
            description = ""
        errs = problems(description, subject) if description else ["the description is empty"]
        if not errs:
            return description
        msgs = msgs + [
            {"role": "assistant", "content": None,
             "tool_calls": [{"id": call.id, "type": "function",
                             "function": {"name": call.function.name,
                                          "arguments": call.function.arguments}}]},
            {"role": "tool", "tool_call_id": call.id, "content": "received"},
            {"role": "user", "content": "That description breaks the rules:\n- "
             + "\n- ".join(errs) + "\nSubmit a corrected description."}]
    raise RewriteFailed("could not rewrite the subject from that feedback: " + "; ".join(errs))
```

- [ ] **Step 4: Run them; they pass.** Same command. Expected: all pass.

- [ ] **Step 5: Commit.**

```bash
git add mcp_harness/subject_rewrite.py mcp_harness/tests/test_subject_rewrite.py
git commit -m "subject_rewrite: feedback -> a positive, subject-only description (forced tool, 2 repairs)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Mesh rounds in the app server

**Files:**
- Modify: `app/server/pleatwright_app/tools.py` (new mesh-review section after `make_mesh`; `present` emits `stage="tree"`)
- Modify: `app/server/pleatwright_app/guided.py` (`phase`, `create`, `message`, `approve`, `retry`)
- Modify: `app/server/pleatwright_app/api.py` (`approve` passes `model`)
- Test: `app/server/tests/test_guided.py`

**Interfaces:**
- Consumes: Task 1's `acquire_mesh(..., description=, seed=)` and
  `cached_files`; Task 2's `subject_key`, `best_proven`, `read_ratings` and
  `record_verdict`; Task 3's `rewrite` and `RewriteFailed`.
- Produces:
  * the tools `first_mesh(ctx, prompt)`, `revise_mesh(ctx, prompt, feedback)`,
    `approve_mesh(ctx, prompt)`, `retry_mesh(ctx, prompt)`,
    `present_mesh(ctx, ms)` and `load_mesh_state(run_dir)`;
  * the events: image and mesh `stage_output`s carry `round`, and
    `awaiting_review` carries `stage` (`"mesh"` or `"tree"`);
  * `phase()` returns `{"phase": "review", "stage": ..., "can_approve": ...}`;
  * `Manager.approve(rid, model=None)`.

- [ ] **Step 1: Write the failing tests.** Append to `app/server/tests/test_guided.py`. Add `import json` and `import mesh_acquire` to its imports if they're missing.

```python
async def approve_first_mesh(m, rid):
    """Mesh review (2026-10-11): a new run first waits on its mesh. Approving
    round 0 takes it on to the tree, as every run went before."""
    await m.wait_idle()
    await m.approve(rid)
    await m.wait_idle()


def _events(m, rid, type_, **match):
    return [e for e in m.store.log(rid).events
            if e["type"] == type_ and all(e.get(k) == v for k, v in match.items())]


def _ratings(m, rid):
    import mesh_ratings
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    return mesh_ratings.read_ratings(ms["rounds"][-1]["cache_dir"])


def test_a_new_run_waits_on_its_mesh_first(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    assert phase(log) == {"phase": "review", "stage": "mesh", "can_approve": True}
    assert _events(m, rid, "stage_output", stage="mesh")[-1]["round"] == 0
    assert not _events(m, rid, "stage_started", stage="tree")


def test_mesh_feedback_records_a_rejection_rewrites_and_draws_round_1(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "sparrow-sized bird, long tail"}]))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "the tail is too short")
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "mesh", "can_approve": True}
    assert [e["round"] for e in _events(m, rid, "stage_output", stage="mesh")] == [0, 1]
    ms = json.load(open(os.path.join(m.store.dir(rid), "author", "mesh_state.json")))
    assert ms["feedback"] == ["the tail is too short"]
    assert ms["rounds"][1]["description"] == "sparrow-sized bird, long tail"
    assert isinstance(ms["rounds"][1]["seed"], int)
    # the fake provider ignores description/seed: both rounds share one cache folder
    assert [x["feedback"] for x in _ratings(m, rid)["rejections"]] == ["the tail is too short"]


def test_approving_the_mesh_counts_it_and_authors_the_tree(offline):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD]))
        rid = await m.create("a bird")
        await approve_first_mesh(m, rid)
        return m, rid
    m, rid = asyncio.run(main())
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "tree", "can_approve": True}
    assert _ratings(m, rid)["approvals"] == 1
    assert os.path.isfile(os.path.join(m.store.dir(rid), "author", "mesh.glb"))
    approved = _events(m, rid, "stage_output", stage="mesh")[-1]
    assert approved["summary"]["approved"] is True and approved["round"] == 0


def test_a_second_run_of_the_subject_is_served_the_proven_mesh(offline, monkeypatch):
    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([BIRD, BIRD]))
        first = await m.create("a bird")
        await approve_first_mesh(m, first)
        calls = []
        monkeypatch.setattr(mesh_acquire, "acquire_mesh",
                            lambda *a, **k: calls.append(1) or (_ for _ in ()).throw(AssertionError("drew")))
        second = await m.create("A bird.")              # same subject key
        await m.wait_idle()
        return m, second, calls
    m, rid, calls = asyncio.run(main())
    assert calls == []
    mesh = _events(m, rid, "stage_output", stage="mesh")[-1]
    assert mesh["summary"]["served"] == "best_rated" and mesh["summary"]["approvals"] == 1
    assert "best-rated" in _events(m, rid, "assistant_message")[-1]["text"]


def test_a_rewrite_that_never_validates_goes_back_to_mesh_review(offline):
    """Review focus 2: nothing is recorded and no round is added; the user rephrases."""
    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "no"}] * 3))
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "no tail")
        await m.wait_idle()
        failed = m.store.log(rid).last
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed
    m, rid, failed = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["retry"] == "review_mesh"
    assert phase(m.store.log(rid)) == {"phase": "review", "stage": "mesh", "can_approve": True}
    assert len(_events(m, rid, "stage_output", stage="mesh")) == 1
    assert _ratings(m, rid) is None


def test_a_failed_redraw_retries_the_same_description_and_seed(offline, monkeypatch):
    """Review focus 3: the mesh Space fails; Retry redraws that round unchanged."""
    real = mesh_acquire.acquire_mesh
    seen = []

    def flaky(prompt, **k):
        seen.append((k.get("description"), k.get("seed")))
        if len(seen) == 2:
            raise RuntimeError("mesh stage: Space 'x' looks unreachable or down")
        return real(prompt, **k)

    async def main():
        m = Manager(RunStore(str(offline / "runs")),
                    lambda model: FakeClient([{"description": "bird, long tail"}]))
        monkeypatch.setattr(mesh_acquire, "acquire_mesh", flaky)
        rid = await m.create("a bird")
        await m.wait_idle()
        await m.message(rid, "longer tail")
        await m.wait_idle()
        failed = m.store.log(rid).last
        await m.retry(rid)
        await m.wait_idle()
        return m, rid, failed
    m, rid, failed = asyncio.run(main())
    assert failed["type"] == "stage_failed" and failed["retry"] == "make_mesh"
    assert seen[1] == seen[2] and seen[1][0] == "bird, long tail" and isinstance(seen[1][1], int)
    assert [e["round"] for e in _events(m, rid, "stage_output", stage="mesh")] == [0, 1]
    assert phase(m.store.log(rid))["stage"] == "mesh"


def test_approving_a_mesh_needs_the_llm(offline):
    """Review focus 5: tree authoring follows, so approval is refused without a key."""
    calls = []

    def factory(model):
        calls.append(model)
        if len(calls) > 1:
            raise ConfigError("provider 'claude' requires an API key; set ANTHROPIC_API_KEY")
        return FakeClient([BIRD])

    async def main():
        m = Manager(RunStore(str(offline / "runs")), factory)
        rid = await m.create("a bird")
        await m.wait_idle()
        m.clients.clear()                               # the key went away
        n = len(m.store.log(rid).events)
        with pytest.raises(Refused, match="authoring is disabled"):
            await m.approve(rid)
        return m, rid, n
    m, rid, n = asyncio.run(main())
    assert len(m.store.log(rid).events) == n


def test_an_old_review_without_a_stage_is_a_tree_review():
    class Log:
        last = {"type": "awaiting_review", "round": 2, "can_approve": True}
    assert phase(Log) == {"phase": "review", "stage": "tree", "can_approve": True}
```

- [ ] **Step 2: Run them; they fail.** Run (repo root): `make PYTHON=$PY test-app 2>&1 | tail -15`. Expected: the new tests FAIL, because phase has no `stage` and there are no mesh rounds.

- [ ] **Step 3: Implement `tools.py`.** Add `import random` to its imports. Change `present` so its `awaiting_review` emits carry `stage="tree"`:

```python
        ctx.emit("awaiting_review", stage="tree", round=rnd, can_approve=True)
    elif state["status"] == "failed":
        ctx.emit("assistant_message", text=state.get("note") or "this round failed")
        ctx.emit("awaiting_review", stage="tree", round=rnd, can_approve=False)
```

Add after `make_mesh` (keep `make_mesh` as it is; the tool tests use it):

```python
# ---- mesh review (spec 2026-10-11) ---------------------------------------------
def load_mesh_state(run_dir: str) -> dict | None:
    try:
        with open(os.path.join(run_dir, "author", "mesh_state.json")) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _save_mesh_state(ctx: Ctx, ms: dict) -> None:
    os.makedirs(ctx.work, exist_ok=True)
    path = os.path.join(ctx.work, "mesh_state.json")
    _dump(ms, path + ".tmp")
    os.replace(path + ".tmp", path)


def _provider_name() -> str:
    return os.environ.get("MESH_PROVIDER", "fake")


async def _draw_round(ctx: Ctx, prompt: str, ms: dict, *, description=None, seed=None,
                      best_dir: str | None = None) -> dict:
    """One mesh round: a draw (or the subject's best proven cached mesh), copied into
    the run as concept_r{N}/mesh_r{N}, its record appended to `ms`. `ms["pending"]`
    holds the round's parameters until it lands, so a retry redraws it unchanged."""
    import mesh_acquire
    import mesh_ratings
    rnd, provider = len(ms["rounds"]), _provider_name()
    ms["pending"] = {"description": description, "seed": seed, "best_dir": best_dir}
    _save_mesh_state(ctx, ms)
    stage, got = ["image"], {}
    ctx.emit("stage_started", stage="image")

    def progress(kind, path):                          # runs on the worker thread
        if ctx.cancelled.is_set():
            return
        if kind == "image":
            files = []
            if path:
                dest = os.path.join(ctx.work, f"concept_r{rnd}" + os.path.splitext(path)[1])
                shutil.copyfile(path, dest)
                files = [ctx.rel(dest)]
                got["concept"] = files[0]
            summary = {"provider": provider} if files else \
                {"skipped": True, "note": f"no concept image ({provider})"}
            ctx.emit_threadsafe("stage_output", stage="image", round=rnd, files=files, summary=summary)
            ctx.emit_threadsafe("stage_started", stage="mesh")
            stage[0] = "mesh"
        elif kind == "mesh":
            dest = os.path.join(ctx.work, f"mesh_r{rnd}.glb")
            shutil.copyfile(path, dest)
            got["mesh"], got["cache_dir"] = ctx.rel(dest), os.path.dirname(path)
            summary = _mesh_summary(dest, provider)
            if best_dir:
                r = mesh_ratings.read_ratings(best_dir) or {}
                summary.update(served="best_rated", approvals=r.get("approvals", 0),
                               votes=r.get("approvals", 0) + len(r.get("rejections", [])))
            else:
                summary.update({k: v for k, v in (("description", description), ("seed", seed)) if v is not None})
            got["summary"] = summary
            ctx.emit_threadsafe("stage_output", stage="mesh", round=rnd, files=[got["mesh"]], summary=summary)

    def serve_cached():
        concept, glb = mesh_acquire.cached_files(best_dir)
        progress("image", concept)
        progress("mesh", glb)

    try:
        if best_dir:
            await asyncio.to_thread(serve_cached)
        else:
            await asyncio.to_thread(mesh_acquire.acquire_mesh, prompt, progress=progress,
                                    description=description, seed=seed)
    except (RuntimeError, TimeoutError, ValueError, OSError) as e:
        ctx.emit("stage_failed", stage=stage[0], error=str(e), reason="error", retry="make_mesh")
        raise ToolFailed(str(e)) from e
    rec = {"cache_dir": got["cache_dir"], "description": description, "seed": seed,
           "provenance": "best_rated" if best_dir else "drawn", "concept": got.get("concept"),
           "mesh": got["mesh"], "summary": got["summary"]}
    ms["rounds"].append(rec)
    ms["pending"] = None
    _save_mesh_state(ctx, ms)
    return rec


def present_mesh(ctx: Ctx, ms: dict) -> None:
    rec = ms["rounds"][-1]
    if rec["provenance"] == "best_rated":
        s = rec["summary"]
        text = (f"This is the best-rated {ms['subject']} mesh so far "
                f"({s.get('approvals', 0)} of {s.get('votes', 0)} reviews approved it).")
    elif rec["description"]:
        text = f"Redrawn as “{rec['description']}”."
    else:
        text = f"A {ms['subject']} mesh, drawn from the plain subject."
    ctx.emit("assistant_message",
             text=text + " Does it read as the animal? Approve it, or say what is wrong with it.")
    ctx.emit("awaiting_review", stage="mesh", round=len(ms["rounds"]) - 1, can_approve=True)


async def first_mesh(ctx: Ctx, prompt: str) -> dict:
    """Round 0: the subject's best proven mesh if it has one, else a default draw."""
    import mesh_acquire
    import mesh_ratings
    ms = {"subject": mesh_ratings.subject_key(prompt), "feedback": [], "rounds": [], "pending": None}
    best = mesh_ratings.best_proven(mesh_acquire.output_dir(), _provider_name(), ms["subject"])
    await _draw_round(ctx, prompt, ms, best_dir=best)
    present_mesh(ctx, ms)
    return ms


async def revise_mesh(ctx: Ctx, prompt: str, feedback: str) -> dict:
    """Rewrite the subject from all feedback so far; if that validates, count the
    rejection and draw the next round with a fresh seed."""
    import mesh_ratings
    import subject_rewrite
    ms = load_mesh_state(ctx.run_dir)
    rec = ms["rounds"][-1]
    ctx.emit("stage_started", stage="mesh")
    concept = os.path.join(ctx.run_dir, rec["concept"]) if rec.get("concept") else None
    try:
        description = await subject_rewrite.rewrite(ctx.client, ms["subject"],
                                                    ms["feedback"] + [feedback], concept)
    except subject_rewrite.RewriteFailed as e:
        ctx.emit("stage_failed", stage="mesh", error=str(e), reason="error", retry="review_mesh")
        raise ToolFailed(str(e)) from e
    mesh_ratings.record_verdict(rec["cache_dir"], approved=False, feedback=feedback,
                                run_id=os.path.basename(ctx.run_dir), subject=ms["subject"],
                                provider=_provider_name(), prompt=prompt,
                                description=rec["description"], seed=rec["seed"])
    ms["feedback"].append(feedback)
    await _draw_round(ctx, prompt, ms, description=description, seed=random.randrange(1, 2**31))
    present_mesh(ctx, ms)
    return ms


async def approve_mesh(ctx: Ctx, prompt: str) -> str:
    """Count the approval; the round's mesh becomes author/mesh.glb for the tree."""
    import mesh_ratings
    ms = load_mesh_state(ctx.run_dir)
    rnd, rec = len(ms["rounds"]) - 1, ms["rounds"][-1]
    mesh_ratings.record_verdict(rec["cache_dir"], approved=True,
                                run_id=os.path.basename(ctx.run_dir), subject=ms["subject"],
                                provider=_provider_name(), prompt=prompt,
                                description=rec["description"], seed=rec["seed"])
    path = os.path.join(ctx.work, "mesh.glb")
    shutil.copyfile(os.path.join(ctx.run_dir, rec["mesh"]), path)
    ctx.emit("stage_output", stage="mesh", round=rnd, files=[rec["mesh"]],
             summary=dict(rec["summary"], approved=True))
    return path


async def retry_mesh(ctx: Ctx, prompt: str) -> dict:
    """After a failed draw: redraw the pending round unchanged, then review again."""
    ms = load_mesh_state(ctx.run_dir)
    if ms is None:
        return await first_mesh(ctx, prompt)
    p = ms.get("pending")
    if p is not None or not ms["rounds"]:
        p = p or {}
        await _draw_round(ctx, prompt, ms, description=p.get("description"),
                          seed=p.get("seed"), best_dir=p.get("best_dir"))
    present_mesh(ctx, ms)
    return ms
```

Add `"review_mesh"` handling to `retry_for` only if a stage-based retry can produce it. It can't: `retry_for` derives retries for image/mesh as `make_mesh`, and `review_mesh` is only ever emitted explicitly by `revise_mesh`. So `retry_for` is unchanged.

- [ ] **Step 4: Implement `guided.py`.** In `phase()`:

```python
    if t == "awaiting_review":
        return {"phase": "review", "stage": last.get("stage") or "tree",
                "can_approve": bool(last["can_approve"])}
    if t == "stage_failed" and last.get("reason") == "exhausted":
        # a run stopped at the 3-revision cap, removed 2026-10-11: back in review
        return {"phase": "review", "stage": "tree", "can_approve": True}
```

In `create`, the flow becomes the mesh's first round only:

```python
        async def flow(ctx):
            await T.first_mesh(ctx, prompt)
```

Replace `message`:

```python
    async def message(self, rid: str, text: str, model: str | None = None) -> None:
        key = self._model_key(model)
        self._refuse_if_busy()
        self._require_llm(key)
        log = self.store.log(rid)
        ph = phase(log)
        if ph["phase"] != "review":
            raise Refused("nothing is waiting for review")
        log.append("user_message", text=text, model=key)
        if ph["stage"] == "mesh":
            prompt = log.events[0]["prompt"]
            self._start(rid, lambda ctx: T.revise_mesh(ctx, prompt, text), key)
        else:
            self._start(rid, lambda ctx: T.revise_tree(ctx, text), key)
```

Replace `approve` (the tree branch keeps today's body):

```python
    async def approve(self, rid: str, model: str | None = None) -> None:
        self._refuse_if_busy()
        log = self.store.log(rid)
        ph = phase(log)
        if ph["phase"] != "review" or not ph["can_approve"]:
            raise Refused("there is nothing to approve: this round produced no tree")
        prompt = log.events[0]["prompt"]
        if ph["stage"] == "mesh":
            key = self._model_key(model)
            self._require_llm(key)                     # the tree is authored next
            log.append("user_message", text="Approve")

            async def mesh_flow(ctx):
                await T.approve_mesh(ctx, prompt)
                await T.author_tree(ctx)
            self._start(rid, mesh_flow, key)
            return
        log.append("user_message", text="Approve")

        async def flow(ctx):
            await T.approve_tree(ctx, prompt)
            await T.fold(ctx, certify_global=self.certify_global)
        self._start(rid, flow)
```

In `retry`, the `make_mesh` branch no longer authors a tree (mesh review comes first), and `review_mesh` re-presents the review:

```python
        async def flow(ctx):
            if tool == "make_mesh":
                await T.retry_mesh(ctx, prompt)
            elif tool == "review_mesh":
                T.present_mesh(ctx, T.load_mesh_state(ctx.run_dir))
            elif tool == "author_tree":
                await T.author_tree(ctx)
            ...                                        # the remaining branches unchanged
```

In `api.py`, change the action to `"approve": lambda m: manager.approve(run_id, model_of(m)),`.

- [ ] **Step 5: Update the existing app tests that drive a run to the tree.**
  * **Rule:** in each test below, insert `await approve_first_mesh(m, rid)` in place of the first `await m.wait_idle()` after `rid = await m.create(...)` (the helper waits itself). Then change any `phase(...) == {"phase": "review", "can_approve": ...}` to include `"stage": "tree"`.
  * **`test_guided.py`:**
    * `test_a_whole_guided_run`
    * `test_messages_outside_review_are_refused`
    * `test_cancel_during_the_fold_logs_cancelled_with_retry`
    * `test_retry_runs_the_failed_stage_again`
    * `test_recover_marks_interrupted_runs_and_keeps_paused_reviews`
    * `test_a_failure_while_approving_is_blamed_on_the_tree_and_retries_without_the_vlm`
    * `test_authoring_actions_are_refused_without_an_llm_and_log_nothing`
    * `test_recover_blames_an_interrupted_approval_on_the_tree`
    * `test_haiku_is_the_default_and_each_authoring_action_can_pick_sonnet`
    * `test_an_antlered_tree_goes_straight_to_packing`
    * `test_a_run_stopped_at_the_old_revision_cap_can_be_revised`
  * **Model-pick test:** in `test_haiku_is_the_default_and_each_authoring_action_can_pick_sonnet`, the first tree is now authored at the mesh approval. Pass the model the test expected `create` to use as `approve(rid, model=...)` (read the test: if `create` used `"sonnet"`, approve with `"sonnet"`).
  * **`test_api.py`**, in `test_a_whole_run_over_the_websocket_and_replay`, `test_the_recorded_frontend_fixture_matches_what_the_server_emits` and `test_a_run_and_a_revision_can_choose_their_model`: after the first `_until(ws, lambda m: m.get("type") == "awaiting_review")`, insert the following. In the model test, approve with the model `create` used, `{"type": "approve", "model": "sonnet"}`.

    ```python
            ws.send_json({"type": "approve"})
            _until(ws, lambda m: m.get("type") == "awaiting_review" and m.get("stage") == "tree")
    ```
  * **Refusal message:** `message`'s refusal text changes from "the tree is not waiting for review" to "nothing is waiting for review". Update any test matching the old text (`grep -rn "not waiting for review" app/server/tests`).

- [ ] **Step 6: Re-record the frontend fixture.** In `app/server/record_fixture.py`:
  * construct the manager with `lambda model: FakeClient([bird, bird])` (the current `lambda:` takes no argument and would raise on the model key);
  * insert `await m.approve(rid)` and `await m.wait_idle()` after the first `await m.wait_idle()`.

  Then run (from `mcp_harness/`):

  `PYTHONPATH=.:tests:../app/server $PY ../app/server/record_fixture.py`

  Expected: `wrote ../app/web/src/__fixtures__/bird_run.events.jsonl`.

- [ ] **Step 7: Run the app suite.** Run (repo root): `make PYTHON=$PY test-app 2>&1 | tail -3`. Expected: all pass. If an updated existing test fails, read it: the rule in Step 5 covers flows that go from mesh to tree, so a failure there is a real behaviour difference, which you should debug, not re-pin.

- [ ] **Step 8: Commit.**

```bash
git add app/server/pleatwright_app/tools.py app/server/pleatwright_app/guided.py app/server/pleatwright_app/api.py \
  app/server/tests/test_guided.py app/server/tests/test_api.py app/server/record_fixture.py \
  app/web/src/__fixtures__/bird_run.events.jsonl
git commit -m "app: a new run reviews its mesh first — feedback rewrites and redraws, approve counts and authors the tree

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Mesh rounds and the review stage in the web UI

**Files:**
- Modify: `app/web/src/types.ts` (`RunView.review`), `app/web/src/runStore.ts` (`keyOf`, `awaiting_review`, the legacy `exhausted` branch, `outputTitle`, `outputLabel`, `summaryLine`, `summaryPairs`; new `reviewCopy`), `app/web/src/api.ts` (`Command` approve `model`), `app/web/src/components/Chat.tsx`, `app/web/src/components/Viewer.tsx`
- Test: `app/web/src/runStore.test.ts`

**Interfaces:**
- Consumes: Task 4's events: `awaiting_review.stage`, and `round` on image and
  mesh outputs; mesh summaries with `description`, `seed`, `served`,
  `approvals`, `votes` and `approved`.
- Produces:
  * `RunView.review: { round: number; canApprove: boolean; stage: StageId } | null`;
  * `reviewCopy(stage) -> { approve: string; hint: string; placeholder: string; aria: string }`.

- [ ] **Step 1: Write the failing tests.** In `app/web/src/runStore.test.ts`:
  * add `reviewCopy` to the import from `./runStore`;
  * the re-recorded fixture now starts with a mesh review, so in every `upTo((e) => e.type === "awaiting_review"...)` predicate that meant the tree, add `&& e.stage === "tree"`;
  * append:

```ts
describe("mesh review", () => {
  it("the recorded run reviews its mesh first, keyed by round", () => {
    const v = replay(upTo((e) => e.type === "awaiting_review"));
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "mesh" });
    expect(v.stages.mesh).toBe("waiting");
    expect(v.outputs.map((o) => o.key)).toEqual(["image:0", "mesh:0"]);
    expect(outputLabel(v.outputs[1])).toBe("02 MESH · R1");
  });
  it("an old run's image and mesh outputs keep their plain keys", () => {
    const v = reduce(emptyView("old"), { type: "event", event: {
      seq: 1, t: "", type: "stage_output", stage: "mesh", files: ["author/mesh.glb"], summary: {} } });
    expect(v.outputs[0].key).toBe("mesh");
  });
  it("an old awaiting_review without a stage is a tree review", () => {
    const v = reduce(emptyView("old"), { type: "event", event: {
      seq: 1, t: "", type: "awaiting_review", round: 0, can_approve: true } });
    expect(v.review).toEqual({ round: 0, canApprove: true, stage: "tree" });
  });
  it("labels the review by stage", () => {
    expect(reviewCopy("mesh")).toEqual({ approve: "Approve mesh", hint: "or type what is wrong with the mesh ↓",
      placeholder: "Describe what is wrong with the mesh…", aria: "Message about the mesh" });
    expect(reviewCopy("tree").approve).toBe("Approve");
  });
  it("a redrawn mesh shows its description; a served one its rating", () => {
    const o = (summary: Record<string, unknown>): Output =>
      ({ key: "mesh:1", stage: "mesh", round: 1, files: [], summary, seq: 0 });
    expect(summaryLine(o({ provider: "hf2", faces: 1000, description: "bull moose, long legs" })))
      .toBe("hf2 · 1,000 faces · “bull moose, long legs”");
    expect(summaryLine(o({ provider: "hf2", served: "best_rated", approvals: 3, votes: 4 })))
      .toBe("hf2 · best-rated · 3/4 approved");
    expect(summaryLine(o({ provider: "hf2", approved: true }))).toBe("hf2 · approved");
  });
});
```

- [ ] **Step 2: Run them; they fail.** Run (from `app/web`): `npx vitest run src/runStore.test.ts 2>&1 | grep -E "×|Tests "`. Expected: failures (no `stage` on review, plain image/mesh keys, no `reviewCopy`).

- [ ] **Step 3: Implement.** `types.ts`:

```ts
  review: { round: number; canApprove: boolean; stage: StageId } | null;
```

`runStore.ts`, `keyOf`:

```ts
const ROUNDED: StageId[] = ["image", "mesh", "tree"];
const keyOf = (e: PwEvent) =>
  ROUNDED.includes(e.stage!) && typeof e.round === "number" ? `${e.stage}:${e.round}` : String(e.stage);
```

The `awaiting_review` case:

```ts
    case "awaiting_review": {
      const stage = (e.stage as StageId | undefined) ?? "tree";
      n.stages[stage] = "waiting";
      n.review = { round: Number(e.round), canApprove: Boolean(e.can_approve), stage };
      n.running = false;
      break;
    }
```

In the legacy `exhausted` branch, set `n.review = { round: …, canApprove: true, stage: "tree" };`.

`outputTitle`: `return o.round != null ? `${names[o.stage]} · round ${o.round + 1}` : names[o.stage];`

`outputLabel`: `return stageLabel(o.stage) + (o.round != null ? ` · R${o.round + 1}` : "");`

The `summaryLine` mesh case:

```ts
    case "mesh": return [s.provider, s.faces != null ? `${Number(s.faces).toLocaleString()} faces` : "",
      s.served === "best_rated" ? `best-rated · ${s.approvals}/${s.votes} approved`
        : s.description ? `“${s.description}”` : "",
      s.approved ? "approved" : ""].filter(Boolean).join(" · ");
```

The `summaryPairs` mesh case:

```ts
    case "mesh":
      add("provider", s.provider);
      add("faces", s.faces != null ? Number(s.faces).toLocaleString() : null);
      if (s.served === "best_rated") add("rating", `${s.approvals}/${s.votes}`);
      add("description", s.description);
      add("seed", s.seed);
      if (s.approved) add("status", "approved");
      break;
```

Add the following, exported, after `outputLabel`:

```ts
/** The review controls' words for the stage under review. */
export function reviewCopy(stage: StageId): { approve: string; hint: string; placeholder: string; aria: string } {
  const noun = stage === "mesh" ? "mesh" : "tree";
  return { approve: stage === "mesh" ? "Approve mesh" : "Approve", hint: `or type what is wrong with the ${noun} ↓`,
           placeholder: `Describe what is wrong with the ${noun}…`, aria: `Message about the ${noun}` };
}
```

`api.ts` `Command`: change `{ type: "approve" }` to `{ type: "approve"; model?: string }`.

`Chat.tsx`: import `reviewCopy`, and after `const reviewing = …` add `const copy = reviewCopy(view.review?.stage ?? "tree");`. Use `copy.approve` for the Approve button, `copy.hint` for the hint span, and `copy.placeholder` and `copy.aria` on the textarea. Send `{ type: "approve", model }`. Change the pill's `title` to "Model for the next tree or mesh feedback".

`Viewer.tsx`: the round buttons follow the stage on show:

```tsx
  const rounds = output.round != null ? allOutputs.filter((o) => o.stage === output.stage && o.round != null) : [];
```

and render them with `{rounds.map(...)}` (drop the `output.stage === "tree" &&` guard).

- [ ] **Step 4: Run the web suite and build.** Run (from `app/web`): `npx vitest run 2>&1 | grep -E "×|Tests "` and `npm run build 2>&1 | grep -E "error|built"`. Expected: all pass and the build is clean. If another fixture-based test fails because outputs now have round keys (`image:0`, `mesh:0`), update its expected keys to the round keys; that is the intended change.

- [ ] **Step 5: Commit.**

```bash
git add app/web/src
git commit -m "app/web: mesh rounds keyed like tree rounds; the review labels itself by stage; approve carries the model

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Full suite, and the real UI on a scratch run

**Files:** none (verification).

- [ ] **Step 1: Run the full suite.** Run (repo root): `make PYTHON=$PY test 2>&1 | grep -E "passed|failed" | tail -2`. Expected: all pass (2 env-gated skips).

- [ ] **Step 2: Real UI, offline.** Serve this branch against a scratch runs folder and a scratch mesh cache, so the real `~/Pleatwright/runs` and `generated_meshes` are never touched:

```bash
cd mcp_harness
PLEATWRIGHT_RUNS_DIR=$TMPDIR/mr_runs MESH_OUTPUT_DIR=$TMPDIR/mr_meshes MESH_PROVIDER=fake \
  PYTHONPATH=.:../app/server $PY -m pleatwright_app --port 8765
```

This needs `ANTHROPIC_API_KEY`: link the main checkout's `.env` into the worktree as in earlier sessions, or check only what needs no key.

In the browser pane at `http://127.0.0.1:8765`:
1. Start "a bird". The chat should show `02 Mesh · round 1` and the mesh review controls ("Approve mesh").
2. Approve. Tree review should follow.
3. Start "a bird" again. It should say "best-rated … 1 of 1".

Record what you saw in the final message.

---

### Task 7: Docs, and the spec refinements

**Files:**
- Modify: `CLAUDE.md` (§3 app row, §4 App bullet)
- Modify: `docs/superpowers/specs/2026-10-11-mesh-review-design.md` (Sections 1–2)

- [ ] **Step 1: CLAUDE.md.**
  * In §4's **App** bullet, add after the first sentence: "A new run first shows its concept image and mesh for review (`Approve mesh`, or feedback that the VLM turns into a better subject description before a fresh-seed redraw; `mcp_harness/subject_rewrite.py`). Each subject's meshes are rated in a `ratings.json` beside the cached mesh (`mcp_harness/mesh_ratings.py`), and a new run of the subject is served its best proven mesh first."
  * In §3's mesh row, append `, mesh_ratings.py, subject_rewrite.py` to the module list.

- [ ] **Step 2: The spec.** In Section 1, replace the `meta.json` field block and its first bullet with the `ratings.json` record and the reason (Refinement 1 above). In Section 2's **Failures**, add: "A rewrite still invalid after its repairs returns to mesh review (`retry="review_mesh"`) and records nothing; a failed draw keeps `retry="make_mesh"`." Add one line to Section 2: "`approve` carries the model pill (tree authoring follows a mesh approval)."

- [ ] **Step 3: Commit.**

```bash
git add CLAUDE.md docs/superpowers/specs/2026-10-11-mesh-review-design.md
git commit -m "docs: mesh review in CLAUDE.md; spec records ratings.json, the rewrite-failure path and approve's model

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 4: Ask the owner for the live check.** One real `hf2` run with one feedback round in the app uses about 2–3 minutes of HF GPU time and one Haiku call. Do it only on a yes, and report the description the VLM wrote and the two meshes.

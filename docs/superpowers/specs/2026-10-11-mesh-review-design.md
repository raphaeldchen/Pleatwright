# Pleatwright app: mesh review with feedback, and approval-ranked meshes

**Owner request (2026-10-11).** Each subject currently gets the same concept
image and mesh every time, because the per-prompt cache and the pinned seeds
(FLUX 11, Hunyuan3D 1234) make every draw of a prompt identical. The owner wants
a review stage for the mesh, like the tree's: after a mesh is generated, the app
asks whether it is good, and the user gives feedback or approves. Meshes with the
highest approval rates are served first for their subject.

## Decisions (owner, in the design discussion)

| question | decision |
|---|---|
| shape | **Approach A.** One review per round, covering the image and the mesh together. Feedback leads to a redraw; approval leads on to tree authoring. |
| what feedback does | The VLM **rewrites the subject description** from the feedback, and a **fresh seed** redraws the image and mesh. |
| first mesh of a new run | The subject's **best proven** mesh (at least 1 approval, ranked by the Wilson lower bound), served from cache. With none, a default draw. |
| subject key | The **normalized prompt**: lower-case, punctuation and a leading article dropped. |
| scope | **App only.** The CLI is unchanged; it is recorded under *Later*. |

## Prior art (CLAUDE.md §0)

| source | finding | adopted / rejected |
|---|---|---|
| DALL-E 3, "Improving Image Generation with Better Captions" (OpenAI 2023); the Imagen on Vertex AI prompt rewriter | LLM-rewritten prompts help, but a rewriter can hallucinate detail | **Adopted:** an LLM rewrite, limited to the template's `{subject}` slot. The measured template is never touched (memory: concept-prompt A/B). |
| Promptist (Hao et al., NeurIPS 2023) | its RL reward includes a relevance term against drift from the user's intent | **Adopted** as a rule: the original subject words must appear in the rewrite. **Rejected:** RL training. |
| Maestro (arXiv 2509.10704) | edits compound over rounds | **Adopted:** every round rewrites from the **original subject plus all feedback so far**, never from the previous rewrite. |
| FaithRewriter (arXiv 2606.08492), Boogu-Image (arXiv 2607.13125) | rewrites over-infer detail and run long | **Adopted:** at most 25 words; a single phrase. |
| Negation studies (arXiv 2411.17066; arXiv 2410.23054 on FLUX/T5); Black Forest Labs guidance | T2I models tend to draw what they are told to omit, FLUX included | **Adopted:** fixes are phrased positively, and a rewrite containing a negation is rejected and repaired. |
| Idea2Img (ECCV 2024) | the model critiques the draft image | **Adopted:** the rewrite sees the current round's concept image (a FLUX picture, not the model's own output). |
| PRISM (TMLR 2025) | the best result can come from any round | **Partly adopted:** every round stays viewable; approval is of the current round. |
| 3DGen-Bench (arXiv 2503.21745), DreamReward (ECCV 2024) | human 3-D preferences are learnable from per-asset votes | **Adopted:** every rejection keeps its feedback text. **Rejected for now:** training on it (see *Later*). |
| Evan Miller, "How Not To Sort By Average Rating" | rank by the Wilson score lower bound, not the mean | **Adopted:** z = 1.96, so 9 of 10 ranks above 1 of 1. |
| Russo et al., "A Tutorial on Thompson Sampling" (2018) | Beta-Bernoulli explore/exploit | **Rejected for now:** the owner chose a predictable "best proven first". Recorded under *Later*. |

## Section 1: data and storage

Ratings live in a sibling `ratings.json` in each cached mesh folder, beside
`mesh.glb` and `meta.json`, not inside `meta.json`. `write_mesh_meta` rewrites
`meta.json` whole, and provenance writing can be disabled, so counts kept there
could be lost. `mesh_acquire.py` also rejects a single index at the cache root,
so ratings stay per folder:

```json
"subject": "moose",
"provider": "hf2",
"prompt": "a moose",
"description": "bull moose, four long well-separated legs, short stubby tail",
"seed": 48213,
"approvals": 2,
"rejections": [{"feedback": "legs fused", "run": "2026-10-11-1516-moose", "utc": "..."}]
```

* `description` is `null` for the plain subject, and `seed` is `null` for the
  pinned seeds.
* `read_ratings` ignores a torn or mistyped file (`approvals` must be an int,
  `rejections` a list), so a bad file cannot crash a new run.
* **`acquire_mesh(prompt, *, description=None, seed=None, ...)`** and
  **`get_provider(name, *, description=None, seed=None)`**.
  * For `hf2`, a seed replaces both pinned seeds and `randomize_seed` stays
    `False`, so a given seed reproduces exactly.
  * The description fills the template's `{subject}` slot.
  * **Both enter `cache_settings` only when set.** `cache_key` hashes
    `json.dumps(settings, sort_keys=True)`, so a default draw keeps today's key
    byte for byte and the 27 existing cache entries stay valid.
  * The other providers (`fake`, `hf`, `meshy`) ignore both.
* There is no `meta.json` fallback: a mesh is rated only once a run records a
  verdict, which writes its `ratings.json` with the subject.

**New module `mcp_harness/mesh_ratings.py`** (pure functions):

* `words(text) -> list[str]`: Unicode word tokens (letters and digits of any
  script), case-folded. The one tokeniser, shared with `subject_rewrite`.
* `subject_key(prompt) -> str`: those words joined by spaces, one leading
  a/an/the dropped. "a moose", "Moose." and "the moose" become `moose`;
  "bull moose" stays `bull moose`; "狗" and "猫" keep distinct keys.
  `best_proven` of an empty subject is `None`.
* `wilson_lower_bound(approvals, rejections, z=1.96) -> float`, which is 0 when
  there are no votes.
* `best_proven(cache_dir, provider, subject) -> str | None`. It keeps entries of
  this provider and subject with **at least 1 approval** and a non-empty
  `mesh.glb`, ranks them by Wilson lower bound, then approvals, then newest,
  and returns the cache directory.
* `record_verdict(key_dir, *, approved, feedback="", run_id) -> dict`: an
  atomic update of `ratings.json` (temporary file, then `os.replace`).

`best_proven` only considers the run's own provider, so `fake` and live meshes
never mix.

## Section 2: the run flow

**New run:** image and mesh, round 0 → **mesh review** → (approve) → tree
authoring → tree review → fold. Everything from tree authoring on is unchanged.

* **Round 0.**
  * If `best_proven(provider, subject_key(prompt))` finds a mesh, it is served
    from cache with no generation, provenance `best_rated`.
  * Otherwise a default draw (pinned seeds, plain subject), cached as today.
  * Either way, the run then emits `awaiting_review` with `stage="mesh"` and
    `round=0`.
* **Feedback during mesh review:**
  1. Rewrite the subject (Section 3), from the original subject and all
     feedback so far plus this feedback.
  2. Once the rewrite validates, `record_verdict(rejected)` on the current
     round's cache directory, with the feedback text and run id. A failed
     rewrite records nothing (see Failures).
  3. Draw with the new description and a fresh random seed.
  4. `awaiting_review(stage="mesh", round=N)`.
* **Approve during mesh review:**
  1. `record_verdict(approved)` on the current round's cache directory.
  2. That round's mesh is copied to `author/mesh.glb`, the file tree authoring
     already reads.
  3. `author_tree`, then everything continues as today.
  4. `approve` carries the model pill (tree authoring follows a mesh approval).
* **Run files.**
  * Each round keeps `author/concept_r{N}.<ext>` and `author/mesh_r{N}.glb`.
  * **`author/mesh_state.json`** records `subject`, `feedback` (the list so
    far), and per round `{cache_dir, description, seed, provenance}`.
* **Events.**
  * Image and mesh `stage_output`s carry `round`.
  * `awaiting_review` carries `stage` (`"mesh"` or `"tree"`); one without a
    `stage` (older logs) means `tree`.
* **Server.**
  * `guided.phase()` returns `{"phase": "review", "stage": ..., "can_approve": ...}`.
  * `Manager.message` and `Manager.approve` dispatch on `stage` (mesh actions
    vs. the existing tree actions).
  * The legacy-`exhausted` rule (#206) stays a tree rule.
* **Failures.**
  * A failed redraw (an HF error) emits `stage_failed` with
    `retry="make_mesh"`. Retrying re-runs that round from `mesh_state.json`
    (the same description and seed).
  * A rewrite still invalid after its repairs returns to mesh review
    (`retry="review_mesh"`) and records nothing. So does any other error from
    the rewrite step, for example the API being down: the user resends the
    feedback.
  * A server restart mid-draw goes through the existing `recover()`, which shows
    "interrupted" with the same retry.
  * Cancel works as today.
* **Not included:** reopening mesh review after approval (start a new run), and
  approving an older round.

## Section 3: the feedback rewrite (`mcp_harness/subject_rewrite.py`)

* **Input, every round:** the original subject (the subject key), all feedback
  so far in order, and the current round's concept image.
* **Output:** a forced tool call, `submit_subject {description: string}`, with
  `tool_choice="required"` (as in #207). It uses the model chosen on the
  composer pill, Haiku 5.5 by default.
* **Instructions:**
  * Rewrite only the subject phrase that goes into the fixed full-body template;
    the template covers view, background and lighting.
  * Describe the animal's anatomy and shape, phrasing every fix as what should
    be visible: "a short stubby tail", not "no tail".
  * Keep the subject words; 25 words at most.
* **Validation,** before any draw:
  1. Every word of the subject key appears (whole words, case-insensitive).
  2. No negation: `no`, `not`, `without`, `never`, `none`, `lacking`, a
     contraction ending in `n't` (straight or curly apostrophe), or a word
     ending in `less` (for example "tailless").
  3. At most 25 words besides the subject's own.
  4. None of the template's scene words (`background`, `render`, `lighting`,
     `studio`, `shadow`, `camera`, `view`).
  The subject's own words are exempt from rules 2 to 4, so a subject such as
  "hairless cat" or "cat with no tail" can still be revised.
* **Repair.** A failing rewrite gets up to 2 repair turns, each naming the rule
  broken. After that, the run returns to mesh review (`retry="review_mesh"`) and
  records nothing (see Section 2, Failures).
* **Use.** The description fills `{subject}` through `concept_prompt` (a leading
  article is dropped, as today). The template is unchanged.
* **Shown in the UI:** the mesh round's summary shows the description.

## Section 4: UI and testing

**UI** (`app/web`):

* `runStore.keyOf` gives image and mesh outputs round keys (`image:N`,
  `mesh:N`) when an event carries `round`; otherwise the key stays as today.
* `review` gains `stage`.
* `Chat`:
  * the Approve button and composer label themselves by stage ("Approve mesh",
    "Describe what is wrong with the mesh…");
  * the model pill's tooltip names both uses.
* `Viewer`: round buttons for the stage on show (mesh rounds as well as tree
  rounds); `viewFiles` handles the round files.
* **Mesh summary:** provider, faces, round, and the description, or
  `best-rated · a/n approved` when served from ratings.
* The stepper shows 02 MESH as "waiting" during mesh review.
* Older runs display as today.

**Tests, written first:**

* **`mesh_ratings`:**
  * `subject_key` cases;
  * Wilson values (9/10 > 1/1; 0/0 = 0);
  * `best_proven`: ranking, the provider filter, the approval floor, a missing or
    empty `mesh.glb` skipped;
  * `record_verdict` is atomic and counts correctly;
  * `read_ratings` ignores a torn or mistyped `ratings.json`, and a mesh with no
    `ratings.json` is never proven.
* **`mesh_acquire`:**
  * a description or seed changes the cache key;
  * **the default key is unchanged** (pinned for a known prompt);
  * `fake` ignores both.
* **`subject_rewrite`:** each validation rule; the repair path; `tool_choice`.
* **App flow** (fake provider, fake VLM):
  * a new run stops at mesh review (round 0);
  * feedback records a rejection, rewrites, and stops at round 1;
  * approve records an approval and reaches tree review;
  * a second run of the subject is served the proven mesh with no generation;
  * an old log without `stage` reviews the tree;
  * a failed redraw retries the same round.
* **Web:** round keys; the review stage in the reducer; labels by stage;
  `viewFiles` for mesh rounds.
* **Gates:**
  * `make test`, plus vitest and `npm run build`;
  * a real-UI check on a scratch runs folder;
  * **one live `hf2` run with one feedback round, only with the owner's OK** (HF
    GPU quota and one Haiku call).

**Docs:** CLAUDE.md §3 and §4 describe the mesh review.

## Later (owner: recorded, not built)

* Mesh review in the CLI (`author` / `run`).
* The CLI serving the subject's best proven mesh.
* Thompson sampling, Beta(1+a, 1+r), plus a "fresh draw" arm, in place of best
  proven first.
* An image-first gate (approach B): review the concept image before paying for
  the mesh. Fused limbs usually start in the image.
* A VLM pre-screen trained or prompted on recorded rejection reasons.
* An A/B test of the template's own "no shadow, no props, no text" clause,
  given the negation findings.

# Live mesh quality: a better concept image (experiment, then ship)

**Owner request (2026-10-16).** Meshes from the 17 hand-picked photos in
`MESH_LIBRARY_DIR` (`~/Downloads/photo_meshes/`) are clearly better than the
meshes a live run makes. The owner thinks a better image generator, one that
gets close to the quality of those photos, would close the gap.

## What we already know (measured 2026-10-16, before this design)

* **The lift is identical, so the gap is entirely in the image.** The library
  meshes were lifted by `tencent/Hunyuan3D-2` `/shape_generation` with the same
  settings live runs use (`manifest.json` `_meta.generator`, which equals
  `mesh_acquire.HUNYUAN_SHAPE_KWARGS`: seed 1234, 30 steps, guidance 5.0,
  octree 256, background removal on).
* **Live concept images on disk:** dog and penguin (app runs), moose ×6 and
  scorpion ×5 (`generated_meshes/` and `~/Pleatwright/runs/`), all from
  FLUX.1-schnell with `CONCEPT_PROMPT_TEMPLATE`. The other 17 subject folders
  in `generated_meshes/` are library copies, not live draws.
* **The live failures are anatomical.** One live scorpion mesh has a tail
  floating free of the body and no head. One has about 7 legs per side. One is
  a crab with no tail and loose blobs. The photo scorpion mesh is correct. The
  live moose meshes are acceptable, so the failures cluster on many-legged
  animals.
* **Other differences:** the live images look like smooth toy renders, while
  the library images are wildlife photos. The animal fills about 40% of a live
  frame.

## Decisions (owner, in the design discussion)

| question | decision |
|---|---|
| what "better" means | **Anatomy.** The right number of legs, a head, and a tail attached where the animal has one. Surface detail (fur, faces) does not matter. |
| cost | Paid image APIs are fine if they are meaningfully better, at a reasonable cost per image. |
| provider | **Google Gemini.** The owner added `GEMINI_API_KEY` to the repo-root `.env`. On 2026-10-16 the key listed `gemini-nano-banana-2.1` ("Nano Banana 2.1"), `gemini-3.1-flash-image` (Nano Banana 2), `gemini-3-pro-image` (Nano Banana Pro) and `gemini-3.1-flash-lite-image`. |
| best-of-N | **Test whether a single image is good enough first.** Generating several images and having a VLM pick one is a later arm of the experiment, not the default. |
| Claude's role | The Claude API cannot generate images. Claude writes the anatomy text and acts as the VLM picker. |
| replication | **Confirm before shipping.** After A–D, the winning arm and the baseline are drawn once more on all 17 subjects. |

## Prior art (CLAUDE.md §0)

These sources were gathered by a research agent on 2026-10-16. The Hunyuan3D
source files are cited by path, and the remaining items are as reported.

| source | finding | adopted / rejected |
|---|---|---|
| Hunyuan3D-2 `hy3dgen/text2image.py` (Tencent's own text-to-3D helper) | Uses HunyuanDiT with the suffix "white background, 3D style, best quality" and "extra limbs" in the negative prompt. **Tencent asks for render style on purpose.** | **Adopted:** render style stays the default arm. **Tested, not assumed:** a photographic arm, because the owner's photos suggest otherwise. |
| Hunyuan3D-2 `shapegen/preprocessors.py` | Crops to the alpha bounding box, scales the subject to 85% of the canvas, then resizes to 512². | **Rejected:** changing framing. A small subject in the frame is re-centred and loses little at 512². |
| Hunyuan3D Studio (arXiv 2509.12815) | Normalises concept images to a 3D style with Qwen-Image-Edit and standardises characters to an A-pose front view. | **Rejected for now:** pose standardisation (see *Later*). |
| Meshy image-to-3D docs; Tripo guide | Use a single object on a plain background with no heavy shadows; three-quarter view for organic shapes. | **Adopted:** keep the template's view and its "no shadow". |
| CORGI (arXiv 2607.00321), 4D-Animal (arXiv 2507.10437) | Image-to-3D models trained on synthetic data lose fidelity on real animal photos. | **Reason for the photographic arm being an experiment.** The literature predicts it loses. |
| Project memory: concept-prompt A/B, 2026-10-07 | The bare word gave close-up portraits and scenes, and "3D style" alone turned "mouse" into a computer mouse. The current template went 5/5. | **Adopted:** every arm keeps "full-body", "single", "entire animal in frame" and the word "animal". |
| Negation studies (arXiv 2411.17066, 2410.23054); mesh review spec | Image models tend to draw what they are told to omit. | **Adopted:** anatomy text is phrased positively ("eight walking legs, four on each side"). |
| "Tiny Inference-Time Scaling" (CVPR 2026 Findings) | Best-of-N with an MLLM verifier added about 8–9 points of GenEval counting. | **Adopted:** best-of-N arm E. |
| Substructure-counting study (NeurIPS 2026, Li et al.) | VLM verifiers are unreliable on part counts (frontier models about 60% on leaflets). Few-shot examples plus a reject option worked best. | **Adopted:** the picker answers per-part checks, may answer "none acceptable", and is calibrated before arm E is scored. |
| CADCodeVerify (ICLR'25), already used in this project | A VLM answers per-query yes/no checks against renders. | **Adopted:** the picker's checks are per-part yes/no questions generated from the anatomy text. |
| Will Keleher, "spider test" (2026) | Nano Banana 2 partly passes a deliberate seven-legged-spider count test. | **Note:** weak evidence that the model follows counts. |

## Section 1: the experiment

**Test set:** the 17 library subjects. The library photo mesh of each subject
is the reference.

**What a mesh is scored against: visible anatomy, not a leaf convention
(Claude's call, from the owner's "anatomy is what matters").** The repo has two
leaf-count conventions, and they disagree:

| subject | manifest `expected_feature_count` | `tree_authoring.py` convention (and the artifact trees) |
|---|---|---|
| scorpion | 9 (pincers excluded as pedipalps) | 11 (chelae count as limbs) |
| dolphin | 4 (dorsal fin excluded) | 5 |

Both are rules about flaps in the folding pattern, not about whether a mesh
looks like the animal. Under the manifest rule, a scorpion mesh that lost its
pincers would pass. Scoring therefore uses an **anatomy checklist**,
`anatomy_checklist.json`:

* It has one entry per subject listing the visible parts that must be present,
  attached and correctly numbered. Scorpion: 8 walking legs (4 per side), 2
  pincers, a segmented tail ending in a stinger. Dolphin: 2 pectoral flippers,
  a dorsal fin, a tail fluke, a head with a beak. Digit-level detail, such as
  toes or individual antenna segments, is out.
* Claude drafts it from the manifest's derivation text before any image is
  generated.
* The owner corrects it on the first review page.
* The manifest count is reported beside the checklist, only as a cross-check.

**Fixed across every arm:** Hunyuan3D-2 with `HUNYUAN_SHAPE_KWARGS` unchanged.
Only the concept image varies.

| arm | image model | prompt | images per subject |
|---|---|---|---|
| A, baseline | FLUX.1-schnell, as shipped (seed 11) | `CONCEPT_PROMPT_TEMPLATE` | 1 |
| B, stronger model | Nano Banana 2.1 | `CONCEPT_PROMPT_TEMPLATE` | 1 |
| C, + anatomy | Nano Banana 2.1 | template + anatomy text | 1 |
| D, + photo style | Nano Banana 2.1 | photographic-style template + anatomy text | 1 |
| E, best of 4 | Nano Banana 2.1, the better of C and D | that arm's prompt | 4, and the Claude picker chooses 1 to lift |

* **The anatomy text is written by Claude from the subject word alone.**
  * It describes the full visible anatomy: legs per side, pincers, tail, fins,
    and so on.
  * It is given no leaf convention and never sees the manifest or the
    checklist, so it generalises to subjects outside the test set.
  * Each text is saved and compared with the checklist. A wrong anatomy text is
    reported as its own error, not as an image-model failure.
* **The photographic template (arm D)** replaces "3D render … soft even studio
  lighting, no shadow" with a wildlife-photograph phrasing. It keeps
  everything the 2026-10-07 A/B found load-bearing (full body, single animal,
  entire animal in frame, plain background). The exact wording is left to the
  builder.
* **Order and gates:**
  1. A–D run first, one draw per cell (round 1).
  2. The owner reviews the results.
  3. **Confirmation round (owner decision):** before anything ships, the
     round-1 winner and baseline A are drawn once more on all 17 subjects with
     new seeds. That is about 34 more Hunyuan lifts. The decision rests on
     both rounds. The runner's cell layout therefore carries a replicate index
     (`<arm>/<subject>/r<n>/`).
  4. E runs only if no single-image arm is good enough after the confirmation
     round, or if the owner asks for it anyway.
* **Every image and mesh is kept**, with its prompt, model ID, seed (where the
  API takes one) and Gemini usage metadata, so any cell can be inspected.

## Section 2: scoring

1. **Anatomy, per mesh, against the checklist.** For each mesh, go through the
   subject's checklist on a `vlm_render.render_mesh_views` sheet. Record which
   parts are present, which are missing, any extras, any part that is detached
   or floating, and any part that is fused to the body.
   * **The owner's reading is final.** Claude pre-fills a draft score for each
     mesh, and the owner confirms or corrects it.
   * The review page shows, per subject, the photo mesh and arms A–D side by
     side, each with its concept image.
   * **The page also records a pass/fail for each concept image against the
     same checklist (Claude's call).** Arm E's picker judges images, not
     meshes, and an image can be right while its lift fails. Recording both
     in one review avoids a second pass over all 68 cells.
2. **A cell passes** when every checklist part is present, attached and
   correctly numbered, and there are no extra limbs or tails, bases, or large
   detached pieces. **Small floating specks and thin slivers do not fail a cell
   (owner, 2026-10-18)** unless they are large enough to be read as a body
   part. **An arm's
   score** is the number of subjects out of 17 that pass. The photo meshes are
   scored the same way, to give the bar.
3. **"Good enough" (Claude's call, owner to confirm):** a single-image arm is
   good enough when it passes at least as many subjects as the photo meshes,
   less one.
4. **Secondary signal, reported but not used to decide:** whether each mesh's
   VLM-authored tree (`gated_pipeline` with no human gate, Haiku 5.5) has the
   leaf count of that subject's artifact trees, and whether it folds. The
   comparison is with the artifact trees, not the manifest, because
   `gated_pipeline` authors with `tree_authoring`'s convention.
5. **Picker calibration (before arm E is scored):** run the picker on the A–D
   concept images the owner has already scored. Report how often it agrees
   with the owner on pass/fail, and how often it rejects a passing image.

## Section 3: cost and limits

* **Images:** about 17 × 3 (B–D) + 17 (confirmation) + 17 × 4 (E) ≈ 136 Nano
  Banana images. At the reported ~$0.034 each that is about $5. Claude calls (anatomy text, picker,
  optional tree authoring) cost cents. **Cap: $15 for the experiment.** The
  first real call reads the actual cost from Gemini's usage metadata, and the
  run stops if the per-image cost is more than double the estimate.
* **Hunyuan lifts:** about 119 runs on the free ZeroGPU Space (A–D = 68,
  confirmation = 34, E = 17). The quota is the real limit. The runner must be resumable: a cell that
  already has a mesh is skipped, so the run can be spread over several days.
  It must stop cleanly on a quota error, using `mesh_acquire`'s existing
  quota-error classifiers.
* **Owner rules:** subjects are the 17 library animals (the 51 artifact trees'
  subjects). There is no tardigrade or water bear. The experiment is not part
  of `make test`.

## Section 4: after the experiment (outline; decided on results)

If an arm wins, its image stage becomes the `hf2` default: a Gemini image
backend in `TwoStageProvider` in place of the FLUX Space, with the anatomy text
step if arm C or D won. The details are a separate short design approved after
the results, because they depend on which arm wins. These points are already
known:

* The cache key must change with the image model (`cache_settings` already
  covers the image settings).
* The mesh review redraw path (`description`, `seed`) must keep working.
* FLUX stays available as the fallback when `GEMINI_API_KEY` is absent, as it
  does today offline.

## Later (not in this design)

* A-pose / front-view standardisation (Hunyuan3D Studio).
* Reference-image conditioning from a curated photo. Nano Banana takes up to
  14 reference images.
* Nano Banana Pro or GPT Image 2.5 if 2.1 falls short.
* Hunyuan3D-2.1 / 2.5 or TRELLIS.2 as the lift.

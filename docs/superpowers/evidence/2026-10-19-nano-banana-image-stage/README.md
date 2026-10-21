# Live run: Nano Banana 2.1 as the `hf2` image stage (2026-10-19)

Spec: `docs/superpowers/specs/2026-10-19-nano-banana-image-stage-design.md` §9.
Plan: `docs/superpowers/plans/2026-10-19-nano-banana-image-stage.md`.

## Setup

* The app ran from this branch on port 8010, with
  `MESH_PROVIDER=hf2 MESH_LIBRARY_DIR=`. The library was off, so round 0 is a
  draw and not the photo mesh.
* The `.env` supplied `GEMINI_API_KEY` (paid tier), so `MESH_IMAGE_BACKEND`
  resolved to `auto` → `gemini`.
* The mesh cache was the worktree's own `mcp_harness/generated_meshes/`, so the
  owner's cache and ratings were not touched.
* Run `2026-10-19-1647-scorpion` (in `~/Pleatwright/runs/`), subject
  "a scorpion".

## What happened

| | |
|---|---|
| concept | `author/concept_r0.jpg`, JPEG 1024×1024 (`concept_r0-512.jpg` here, downscaled): one whole scorpion on white, tail, pincers and legs visible |
| stage line | `hf2 · gemini-nano-banana-2.1` (`app-concept.jpg`) |
| draw label | round 0 seed `1154703`, a fresh label, because Gemini draws do not reproduce |
| lift | Hunyuan3D-2 `/shape_generation`, settings = `HUNYUAN_SHAPE_KWARGS` (seed 1234, `check_box_rembg` true): **283,202 faces**, one scorpion body (`app-mesh-review.jpg`) |
| cache folder | `a-scorpion-55c3d0c71e6e5c65/` holding `concept.jpg`, `mesh.glb` and `meta.json` (`meta.json` here) |
| provenance | `meta.json` `settings`: `image_backend: gemini`, `image_model: gemini-nano-banana-2.1`, `image_seed: 1154703`; `glb_sha256 74af145d…cbcbf` |
| time | concept in about 12 s, mesh about 60 s later |
| cost | one Nano Banana image, about $0.042; one Hunyuan lift on the free ZeroGPU quota |

The run was left waiting at mesh review. Approving or rejecting the mesh is
the owner's call, so no verdict was recorded in `ratings.json`.

## Suite

`make test`: 715 passed, 2 skipped (pipeline) and 97 passed (app server).
`app/web`: vitest 85 passed, `tsc` clean, `npm run build` ok.

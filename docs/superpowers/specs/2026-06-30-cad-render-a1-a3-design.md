# Design: CAD-Quality Physical-Paper Render (A1–A3)

**Status:** Approved design — ready for implementation planning.
**Date:** 2026-06-30
**Parent roadmap:** `2026-06-30-finished-model-view-research.md` (Pillar A)
**Sub-project:** A1 (stable geometry extraction) + A2 (thickness) + A3 (materials/lighting)

---

## 1. Goal

Add a **finished-look** 3D view of the model: a clean, thick-paper, properly-lit, stable
object the user can orbit — the "CAD software" feel. This replaces neither the validated
`.fold` nor the existing folding-animation simulator; it sits beside them as a new tab.

This sub-project renders the **current base**. It will not make a base look like a
finished animal (that is Pillar B, honest shaping). It makes the paper look *real and
clean* instead of a jittering zero-thickness shell, and it builds the rendering substrate
that Pillar B's shaped outputs will later render through unchanged.

## 2. Decisions locked in brainstorming

1. **Render host: a fresh scene we own** (react-three-fiber / current three.js). The
   vendored MIT Origami Simulator stays only as the folding-animation tab; the CAD view is
   our own scene graph, materials, camera, and export.
2. **Geometry source: reuse the proven solver's output.** Drive the vendored mass-spring
   solver offscreen to convergence and read the folded vertex positions once. Honest (it
   is the validated fold), no new fold math.
3. **Pose + thickness: a 3D pose + simple per-face shell.** Render a 3D-separated pose
   (partial fold for the base; naturally-3D for future shaped models) so thickness is a
   trivial per-face offset with **no global layer ordering**. Sidesteps the NP-hard part
   and matches what Pillar B always produces.

## 3. Why these choices (rationale to preserve)

- A base is *flat-foldable*: at 100% it collapses to a flat stack of coincident layers,
  which would require NP-hard layer ordering to render as a solid. A **3D pose** keeps
  layers separated in space, so a per-face shell suffices. Pillar B's shaped models are
  inherently 3D (not flat-foldable), so this approach is also their long-term renderer —
  nothing here is base-only throwaway.
- The "jank" is the live relaxation *process*, not the converged *answer*. Freezing the
  converged geometry removes the jitter while staying honest to the validated fold.
- Owning the scene (vs. patching the aging vendored app) gives us modern materials,
  lighting, camera, and glTF export, and decouples the CAD look from the solver we are
  trying to visually escape.

## 4. Architecture & data flow

```
fold.displayJson
      │
      ▼
[Extractor]  hidden iframe running the vendored sim, driven one-shot:
             loadFold → setFold(POSE) → poll to convergence → getFoldedGeometry
      │  { vertices_coords (3D), faces_vertices }   ← frozen static mesh
      ▼
[Shell builder]  PURE: per-face offset both sides → thickened triangles,
                 recomputed normals, crease edges carried with M/V tags.
                 No layer ordering.
      │  ModelMesh { positions, normals, edgeLines(M/V) }
      ▼
[CADViewer]  react-three-fiber scene we own: PBR paper material, light rig,
             soft shadows / AO, OrbitControls, ground plane, lighting presets,
             glTF export. Rendered in a new "Model" tab.
```

## 5. Components

Each unit has one purpose, a defined interface, and is independently testable.

### 5.1 `getFoldedGeometry` bridge extension
- **What:** the single edit to the vendored sim (`ide-bridge.js`). A new postMessage
  `getFoldedGeometry` that reads the sim's converged `model` vertex positions + face
  indices and emits them back to the parent.
- **Interface:** in `{ type: "getFoldedGeometry" }` → out
  `{ type: "foldedGeometry", vertices_coords, faces_vertices }`.
- **Depends on:** the vendored sim's `model` object (lead: `model.js`, `saveFOLD.js`,
  `saveSTL.js` for how it reads positions).
- **Honesty note:** this is the only authored file inside the vendored app, consistent
  with the existing bridge comment ("The only file we author inside the vendored app").

### 5.2 `extractFoldedMesh(fold, pose) → Promise<StaticMesh>`
- **What:** owns a hidden sim iframe; loads the fold, sets the target pose, polls until
  converged (energy threshold + NaN check), requests geometry, resolves a static mesh.
  Encapsulates all "wait for convergence" logic so nothing downstream sees jitter.
- **Interface:** `(fold: FoldJson, pose: number) → Promise<{ vertices_coords, faces_vertices }>`;
  rejects on timeout or NaN/non-convergence.
- **Depends on:** 5.1, the hidden iframe, the existing `Outbound`/`Inbound` message types
  in `viewer.ts` (extended).

### 5.3 `buildShell(mesh, thickness) → ModelMesh`  *(pure)*
- **What:** per-face offset to a solid, recompute normals, carry crease edges with M/V
  tags. No DOM, no layer ordering.
- **Interface:** `({ vertices_coords, faces_vertices, edges? }, thickness: number) →
  { positions: Float32Array, normals: Float32Array, edgeLines: {a,b,assignment}[] }`.
- **Robustness:** validates well-formed faces (mirror `fold_is_wellformed` from A-9);
  degrades a degenerate face to zero-thickness rather than throwing.
- **Depends on:** nothing (pure) — the most heavily unit-tested unit.

### 5.4 `CADViewer` (react-three-fiber component)
- **What:** our scene — PBR paper material (roughness, faint back-translucency, fiber
  normal map), light rig with soft shadows / AO, `OrbitControls`, ground plane, lighting
  presets, and glTF export. Lives in a new **"Model" tab** beside JSON / Simulator /
  2D-panel.
- **Interface:** `props: { mesh: ModelMesh | null; error: string | null }`.
- **Depends on:** 5.3 output; react-three-fiber + three.js (new frontend deps).

## 6. Pose selection

A single module-level constant `DEFAULT_POSE` (a fold fraction, default ≈ 0.9) passed to
`extractFoldedMesh`. Defined once so it is trivial to expose in UI later or override for
Pillar B's shaped output (which arrives at its natural 3D pose, effectively 1.0). No
slider in this sub-project.

## 7. Error handling

- **Extractor:** convergence guarded by energy threshold + NaN check + timeout. On
  failure it rejects; `CADViewer` shows the message in the Model tab (no silent blank
  canvas), mirroring the existing viewer error path in `viewer.ts`.
- **Shell builder:** bad/degenerate faces fall back to zero-thickness for that face rather
  than throwing, so one malformed face never blanks the whole render.

## 8. Testing strategy

- **`buildShell` (pure unit):** known small fold → expected thickened vertex/normal
  counts; M/V edge preservation; degenerate-face zero-thickness fallback. Mirrors the
  `flap_fill.py` pure-geometry test style.
- **`extractFoldedMesh` (controller test, faked bridge):** like `viewer.test.ts` —
  convergence-then-resolve; timeout → reject; NaN → reject. No real iframe.
- **`CADViewer` (smoke):** mounts and consumes a `ModelMesh` without throwing; renders the
  error state when `error` is set.

## 9. UI integration

A new **"Model"** tab added next to the existing tabs (JSON / Simulator / 2D crease
panel). Selecting it triggers `extractFoldedMesh(fold.displayJson, DEFAULT_POSE)` →
`buildShell` → `CADViewer`. The existing Simulator tab (folding animation) is unchanged.

## 10. Out of scope (this sub-project)

- Global layer ordering and flat-folded stacked-solid rendering.
- All of Pillar B (honest shaping).
- Replacing or modifying the existing Simulator folding view.
- A pose slider / interactive scrub (deferred; pose is a constant for now).

## 11. Open implementation unknowns (resolve during planning/spikes)

1. Exactly how to read converged vertex positions out of the vendored sim's `model`
   (probe `model.js` / `saveFOLD.js` / `saveSTL.js`).
2. Which react-three-fiber + three.js versions to pin, and how they fit the existing Vite
   frontend build.
3. The energy/NaN convergence criterion the sim already exposes vs. one we add.

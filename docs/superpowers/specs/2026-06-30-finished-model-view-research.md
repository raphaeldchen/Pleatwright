# Research / Roadmap: Showing the Finished Origami Model in a CAD-Quality 3D View

**Status:** Research document — not yet an implementation spec. Captures the problem,
the design constraints, and a proposed two-pillar decomposition for review.
**Date:** 2026-06-30
**Author:** brainstorming session (Claude + raphaeldchen)

---

## 1. Goal

Let the user see what the **finished** origami model looks like in a polished, CAD-like
3D view — the way you'd inspect a part in Fusion 360 or Onshape: thick material, clean
lighting, a stable pose you can orbit around.

Today the viewport embeds the MIT Origami Simulator, which shows the *crease pattern
folding*. The user's two complaints:

1. **It's janky** — it jitters as the mass-spring solver relaxes, faces interpenetrate,
   shading is flat and unlit.
2. **It doesn't show the finished model** — it stops at the flat *base*, with no
   *shaping* (the artistic folds that turn a base into a recognizable animal) and no
   sense of *physical paper* (thickness, material).

**Decided constraint (this session):** the finished view must stay **honest** — every
piece of geometry shown must be derived from the real, validated foldable sheet. No
faked impression, no decoupled AI render, no swapping in the reference mesh. Shaping,
when we add it, must be *real additional folds on the same sheet*, traceable back to the
crease pattern. This is the same anti-hallucination thesis the whole project is built on
(see `CLAUDE.md` §2: "Source Code vs. Compiled Output").

---

## 2. Why this is hard (the core conceptual gap)

Origami design has three stages. The project has industrial-strength tooling for the
first two and **nothing** for the third:

| Stage | What it produces | Tooling in this project | Deterministic? |
|---|---|---|---|
| **Packing** | flap layout on the square | TreeMaker (circle/river packing) | yes |
| **Base** | flat uniaxial base — creases drawn, flaps are flat radial slivers | TreeMaker (universal molecule) → `.fold` | yes |
| **Shaping** | the finished 3D model — legs bent, head popped, body rounded | **none** | **no — this is where human artistry lives** |

The base is a *flat-foldable* object: every flap lies in the plane, the whole thing
collapses flat. A finished animal is a *3D* object: it does **not** lie flat. Getting
from base → finished is the unsolved problem of computational origami. There is no
"TreeMaker for shaping."

### The key reframe that makes it tractable

The FOLD file format already represents 3D folded states:

- `vertices_coords` may be 3D.
- `edges_foldAngle` is a dihedral angle in **degrees, anywhere in −180…180** — not just
  the ±180° (fully flat) the base uses.
- `frame_classes: ["foldedForm"]` and `file_frames` let one file carry multiple folded
  states of the same crease pattern.

So **honest shaping = adding real creases to the same sheet and assigning them non-flat
3D fold angles.** That converts a vague artistic problem ("make it look like a dog") into
a concrete geometric operation on a data structure we already emit. It also means the
flat-foldability laws (Maekawa/Kawasaki, enforced by Oriedita) **no longer apply** to the
shaped result — shaping deliberately leaves the flat-foldable regime, so we need a
different notion of "valid" (see Pillar B / B4).

### What the current viewer actually does (grounded in code)

- `web/frontend/public/simulator/js/ide-bridge.js` takes the bare crease pattern, derives
  `edges_foldAngle` as **M → −180, V → +180, else 0**, builds faces, and calls
  `pattern.setFoldData`. Note: fold angles are hard-wired to flat. There is no path today
  for non-flat (shaping) angles.
- `web/frontend/src/viewer.ts` drives `setFold(percent)` from 0→100%, i.e. it animates
  the flat fold; it renders `displayJson ?? json` (the squared display copy).
- The simulator (Ghassaei) is a GPU mass-spring solver over a triangulated mesh (axial +
  crease + face beams). It is **zero-thickness** and targets the supplied fold angles. It
  ships an STL export (`saveSTL.js`) but no thickness, materials, or shaping.

So the viewer is structurally locked to "fold the flat base." Both complaints follow
directly: no thickness (zero-thickness solver) and no shaping (fold angles pinned to
±180°).

---

## 3. Proposed decomposition: two pillars

The goal is really two sub-projects with very different risk profiles. Bundling them into
one spec would be a mistake.

### Pillar A — CAD-quality physical-paper rendering

Mostly a *rendering* problem, achievable on the geometry we already have. It fixes
"janky" and "physical paper," and it is **infrastructure that Pillar B renders through
later** — nothing here is throwaway.

| Piece | What it is | Depends on |
|---|---|---|
| **A1** Stable geometry extraction | Capture the *converged* folded vertex positions (the 3D mesh at the target fold), divorced from the jittery live solver. Produce one clean static triangle mesh. | — |
| **A2** Paper thickness / solidification | Shell the zero-thickness surface into real paper; resolve **layer ordering** so stacked flaps don't z-fight. Origami stacks many coincident layers; a correct stacking order is needed. **Oriedita already computes layer ordering** and is in our stack — candidate source of truth. | A1 + layer order |
| **A3** Material & lighting | PBR paper material (roughness, faint back-translucency, fiber normal map), a light rig, soft shadows / ambient occlusion, an orbit camera and ground plane. This is the "CAD look." | A1 |
| **A4** Crisp crease/edge shading | Render mountain vs valley edges cleanly; optional bevel so folds read as creased paper, not knife cuts. | A1 |
| **A5** Presentation UX | Orbit / zoom / pan, lighting presets, exploded-layer view, screenshot, and **glTF export** so the result is a real, portable 3D asset. | A1–A4 |

**Honest limitation:** A on the *current base* makes the base a clean, thick, beautifully
lit paper object — but still a spiky base, not a dog. A makes it *look* like real paper;
only B makes it *look like the animal*.

**Build vs. buy note (research item):** A can be done by either (a) extending the vendored
simulator's three.js scene, or (b) extracting the static mesh and rendering it in a fresh,
modern three.js / react-three-fiber scene we control. (b) is cleaner long-term (we own the
scene graph, materials, camera) and decouples us from the aging vendored app, at the cost
of re-implementing the load path. This is the main open architecture choice inside A.

### Pillar B — Honest shaping (the research core)

The unsolved part. Reframed via §2 as "add real creases with 3D fold angles."

| Piece | What it is | Depends on |
|---|---|---|
| **B1** Shaping representation | A small vocabulary of parametric primitives, each defined as a real geometry operation (creases + 3D fold angles) on a named flap: **narrow-flap** (mountain-fold a flap thinner), **reverse-fold** (inside/outside — bend a leg, pop a head), **crimp** (two folds — shorten/angle a segment), **squash / rabbit-ear / sink** (round or tuck). | — |
| **B3** Apply engine | `base.fold` + ordered shaping ops → `finished.fold`. The hard part: each op alters layer order and geometry, ops compose, and the result must stay physically valid (paper conservation, no self-intersection). Likely incremental: apply op → re-solve → repeat. | B1 |
| **B2** Intent → shaping mapping | Tree nodes are already labeled (`front_left_leg_tip`, `head`); map anatomy → which primitive, where, with what parameters. This is where the **agent** plugs in, HITL suggest-then-confirm, mirroring the A-9 generative-detail engine. | B1, B3 |
| **B4** Honesty re-validation | `finished.fold` isn't flat-foldable, so Oriedita's flat-fold lint is moot. New validity = *physically realizable*: no tearing, no interpenetration, layers consistent. **Use the simulator itself as ground truth** (does it relax without NaN / self-intersection?) — mirrors A-3, where the sim overruled Oriedita's false-negatives. | B3 |
| **B5** Target-mesh-guided shaping | Use the reference mesh (the existing text→3D pipeline) as the **goal silhouette**; search shaping parameters so the posed base matches it. Automates the *artistry*. Ambitious, optional, last. | B1–B4 + mesh pipeline |

`★ Insight ─────────────────────────────────────`
B4 is the linchpin and the most project-consistent idea here. The project already learned
(A-3) that Oriedita throws false-negatives on geometry that physically folds fine, and
that **the simulator is the more trustworthy oracle**. Shaping leaves the flat-foldable
regime entirely, so we lean on that same oracle: "valid" = "the sim folds it without
exploding," not "Oriedita says flat-foldable."
`─────────────────────────────────────────────────`

---

## 4. How the pillars connect

- **A is independent and ships first.** B is the research bet.
- **A is also B's infrastructure.** Once B produces `finished.fold` (3D fold angles), it
  renders through the *same* A pipeline. A1 (stable extraction) and A2 (thickness) are
  reused verbatim. So A is never wasted even though shaping is the ultimate goal.
- **B's output feeds A's renderer.** Clean handoff: build A on the base now; when B lands,
  point A at the shaped fold instead of the bare base.
- **B reuses existing project machinery.** The reference-mesh pipeline (B5), the
  HITL suggest-then-confirm pattern (B2, from A-9), and the sim-as-oracle stance (B4, from
  A-3) all already exist in some form.

---

## 5. Recommended build order

1. **A1–A3** — CAD render of the current base. Independent, fast visible win, builds the
   substrate B reuses. Retires "janky" and "physical paper" immediately.
2. **B1 + B3 on ONE primitive** (e.g. reverse-fold a single flap) — a tracer bullet
   through the hardest pipe, validated by B4 (sim as ground truth). Proves the
   "add 3D fold angles → still physically valid" loop end-to-end on the smallest case.
3. **B2** — wire the agent to choose shaping ops, HITL, mirroring A-9.
4. **B5** — target-mesh-guided automation of the artistry, last and optional.

**Recommendation:** start with **A1–A3**. Fastest path to "no longer janky," lowest risk,
and it is the foundation everything in B eventually renders through.

---

## 6. Open research questions (to investigate before committing to a sub-project)

These are the unknowns worth reading up on / prototyping before we turn either pillar into
an implementation spec.

**Pillar A:**

1. **Static mesh extraction** — does the vendored sim expose the converged vertex
   positions, or do we re-run the fold headless to capture them? (`saveSTL.js` /
   `saveFOLD.js` are leads.)
2. **Layer ordering for thickness** — can Oriedita emit a global stacking order we can
   consume for per-layer offset? Is its order total or partial? (Global flat-fold layer
   ordering is NP-hard in general; Oriedita solves practical cases.)
3. **Render host** — extend the vendored three.js scene, or extract the mesh into a fresh
   react-three-fiber scene we own? (Trade-off: control & modernity vs. re-implementation.)

**Pillar B:**

4. **Primitive geometry** — for each primitive (start with reverse-fold), what is the
   exact crease-and-angle construction on a flap, in terms of the FOLD data? Is there
   prior art (e.g. Tachi's Freeform Origami / Origamizer, ORIPA, reference-fold libraries)
   we can adapt rather than derive from scratch?
5. **Composition & layer bookkeeping** — how do sequential shaping ops update layer order
   and avoid self-intersection? Does the mass-spring sim tolerate intermediate non-flat
   targets, or do we need a rigid-origami solver (e.g. Tachi's rigid origami simulator)?
6. **The validity oracle** — what exactly does "the sim folds it without exploding" mean
   operationally (NaN check, energy threshold, self-intersection test)? Can we make it a
   programmatic pass/fail, like `validate_flat_foldability` but for 3D realizability?
7. **Target-mesh matching (B5)** — what's the right objective (silhouette IoU, joint-angle
   fit) and search method (gradient-free over a handful of joint angles) to pose the base
   toward the reference mesh?

**Prior art worth a literature pass:** Lang's *Origami Design Secrets* (shaping chapters),
Tachi's Freeform Origami / Origamizer / rigid-origami simulator, the Learn2Fold
neuro-symbolic paper (already cited in `CLAUDE.md` §6), and the Origami Simulator paper
(Ghassaei, Demaine, Gershenfeld) for the solver internals.

---

## 7. What this document does *not* decide

- Which sub-project we build first (user wants to research further).
- The render host choice (A: extend vendored sim vs. fresh scene).
- The exact shaping primitive set or their geometric constructions.
- Whether B5 (target-mesh guidance) is ever in scope.

Each chosen sub-project gets its own spec → plan → implementation cycle. This doc is the
shared map they hang off of.

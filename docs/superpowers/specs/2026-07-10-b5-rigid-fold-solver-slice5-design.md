# B5 slice 5 — Python rigid-fold solver (deterministic angle→3D core)

**Status:** diagnostic subset (fold_to_3d forward pass + folding_dof
first-order DOF count, math-anchored) implemented on `feat/b5-rigid-fold-slice5`
and PROMOTED into `feat/b5-front-dof` 2026-07-12. The closure solve
(Component 2), `tip_vectors`, and validation-ladder step 3 (sim anchor) were
NOT built — closure solve is escalation-only per the b5-front-dof design spec
(prefer consuming the Codex rigid/ kernel's).
**Predecessor:** `docs/superpowers/specs/2026-07-09-b5-pose-fit-slice4-design.md`
(slice 4 HALTED at gate 2 — both cheap hypotheses measured dead: second
descent pass regressed, crimp is direction-neutral).
**Lineage:** [[b5-pose-fit-slice4]], [[b5-pose-fit-slice3]],
[[flat-fold-engine-slice1]].

## Motivation

The B5 pose-fit loop searches fold parameters by driving the vendored MIT
Origami Simulator (mass-spring, GPU) as a **black-box oracle** via Playwright
captures. Two structural costs of that design:

1. **Noise.** Every evaluation fights a derived-quantity capture-drift band of
   ~0.09° (measured slice 4, Task 7: identical-params eval-vs-recapture 0.0934
   total-error units). This is why the crimp gate needed a 10° margin to be
   readable.
2. **Flat equilibrium.** The mass-spring solver minimizes energy, and a
   flat-foldable base has the flat state as a valid low-energy equilibrium, so
   compiled squared bases (dog/quad) never pop into 3D — only the star-4
   topology folds. The oracle produces *nothing to search* on the realistic
   bases.

Tomohiro Tachi's Rigid Origami Simulator solves folding **kinematically**: it
parameterizes the configuration by per-crease fold angles ρ and projects an
intended angle change into the null-space of a closure-constraint Jacobian.
There is no energy and no flat attractor — you prescribe angles and it maintains
rigidity. Tachi's software is proprietary, Windows-only, closed-source, and
imports/exports no `.fold` (dealbreaker for our headless agentic pipeline), but
the *algorithm* is published (Simulation of Rigid Origami, 4OSME; Folding
Simulation with Lagrange Multiplier Method, arXiv 2006.05025) and
reimplementable.

Our `flat_fold.py` is already ~60% of a rigid folder: it builds the
face-adjacency graph, spans a tree from the largest face, composes reflections
(M/V = reflect, F/B = identity) to place every face at a **100% flat** fold, and
reports cycle-closure residual at non-tree shared edges (`ClosureReport`). Tachi's
folder is the same graph algorithm with the fixed 180° reflection replaced by a
fold-angle-parameterized 3D rotation, plus a Newton solve driving those closure
residuals to zero.

## Goal & sequencing

Slice 5 builds the **validated deterministic angle→3D core** (the shared engine),
sequenced so the two bigger prizes become the obvious next slices:

- **This slice (core):** deterministic `fold_to_3d` + closure solve + pose
  extraction, validated against the sim on star-4 where the sim actually folds.
- **Next (reachability, Option 3):** use the constraint Jacobian to answer "is
  the fox pose in this base's configuration manifold?" — a real yes/no the
  black-box search structurally cannot give.
- **Later (flat equilibrium, Option 2):** point the *trusted* engine at squared
  dog/quad, where the sim gives nothing to cross-check against.

**Why the core first, not flat-equilibrium first (per memory's stated next
effort):** the binding constraint is *trust*, not ambition. The only anchor to
validate a pure-Python folder against is the MIT sim, and it only produces a
foldable 3D state on star-4. We bootstrap trust where the sim folds, *then* aim
the trusted tool at the flat-equilibrium mystery. An engine that adjudicates the
flat-equilibrium question must first be proven on a case with a cross-check.

## Architecture

New module `mcp_harness/rigid_fold.py`, sibling to `flat_fold.py`: numpy-only,
sim-free, so pytest covers the math without Playwright (same discipline as
`flat_fold.py` and `pose_target.py`).

**Targeted refactor (no behavior change):** lift `flat_fold.py`'s face-graph
construction — `_extract_faces` + face adjacency + shared-edge list +
deterministic root (largest interior face) + spanning tree (currently inline,
`flat_fold.py:47–179`) — into a shared internal `_build_face_graph(fold)`
returning `(faces, adj, shared, root, tree)`. `flat_fold()` is rewritten to call
it; `rigid_fold` calls it too. This is the only edit to `flat_fold.py`, and it
must leave every existing `flat_fold` test green (behavior-preserving).

### Component 1 — forward pass

```
fold_to_3d(fold: dict, rho: dict) -> RigidFoldState
```

- `rho`: `{crease_edge_key: angle_radians}` for M/V creases; F/B are 0
  (`crease_edge_key` is `tuple(sorted(edge))`, matching `flat_fold`'s `assign`
  dict keys).
- Root face pinned in the z=0 plane (identity 4×4). BFS the spanning tree; each
  tree edge crossing crease *k* right-multiplies the parent's 4×4 transform by a
  **3D rotation of ρ_k about that crease's line** (the 3D generalization of
  `flat_fold._reflect`, which becomes a 4×4 homogeneous rotation). M vs V sets
  the rotation sign, mirroring the M/V branch at `flat_fold.py:172`.
- `RigidFoldState` (frozen dataclass) carries: `faces` (CCW index lists, from the
  shared graph), `transforms` (per-face 4×4), `folded_vertices` (per-face N×3
  arrays — image of each face vertex), and `residual`: the 3D gap vector at every
  non-tree shared edge (the 3D generalization of `ClosureReport`). Reported,
  never assumed zero.

**Sign convention** is pinned by the ρ=±π anchor (below) and by the single-vertex
fixture (step 2), not chosen by hand — the same way `flat_fold`'s M/V sign was
pinned by strip fixtures in layer-order slice 2.

### Component 2 — closure solve

```
solve_closure(fold: dict, rho_seed: dict, drive: dict) -> (rho, residual)
```

- Constraint `g(ρ) = state.residual` (non-tree shared-edge 3D gaps); target
  `g(ρ) = 0`.
- **Gauss-Newton.** Jacobian `J = ∂g/∂ρ` by **finite differences** first
  (~n_creases forward passes per iteration; analytic Jacobian deferred to a
  later slice). Project the driven change `drive` into `null(J)` and iterate —
  Tachi's projection method.
- **Seed slightly folded** (`rho_seed`), never ρ=0: the Jacobian is
  rank-deficient at the flat state (documented ROS singularity).
- Returns solved `rho` and final `residual`. **Report** the residual, do not
  assert convergence — squared-base Kawasaki violations keep it non-zero, which
  is the informative signal (they are hull-frontier bases with *accepted*
  violations; `flat_fold` already flags exactly these at 180°).

### Component 3 — pose interface

```
tip_vectors(state: RigidFoldState, hub_id: int) -> {leaf_id: np.ndarray(3)}
```

Folded tip directions (leaf image minus hub image) from a `RigidFoldState`.
These feed the *existing* `pose_target.angles_from_bones(head_vec, front_vecs,
back_vecs)`, which already turns tip/hub vectors into the `{front, back, head}`
angle triple used on both sides of the fit. Net: rigid_fold yields the **same
pose representation the sim does, deterministically**. Thin (~20 lines) because
`pose_target` owns the angle math.

## Validation ladder (how the engine earns trust)

| Step | Check | Anchor | Where |
|---|---|---|---|
| 1 | `fold_to_3d(fold, all-±π)` equals `flat_fold(fold)` (z→0, reflection recovered) | pure math, exact | pytest |
| 2 | closure solve + finite-diff Jacobian on a single degree-4 flat-foldable vertex vs the closed-form 1-DOF fold-angle relation (Huffman/Tachi) | analytic, no sim | pytest |
| 3 | star-4 winner-base tip directions → `{front,back,head}` angles vs a MIT-sim capture at a matched configuration | reality | committed probe |

- Step 1 is the free correctness anchor: at ρ=±π a rotation-about-a-line
  degenerates to `flat_fold`'s 2D reflection, so the whole composition path is
  checked by one assertion (tolerance at flat_fold's `CLOSURE_EPS` scale).
- Step 2 pins the sign convention and validates the solve/Jacobian against math.
- Step 3 is a committed probe (headed `SimSession`, like `probe_pose_fit.py`),
  **not** a unit test. Per standing gotchas: never 0.0 tolerances; tolerance set
  to the measured derived-quantity drift band (~0.09°); assert displacement > 0.
  Matched configuration: drive rigid_fold with the same fold angles the sim
  capture used (the star-4 winner base b=0.95, h=0.40 from slice 3).

**Honest failure mode (halt condition):** if step 3 disagrees beyond the drift
band, that is a real finding (rigid model ≠ the sim's compliant model, or a
sign/convention bug). Slice 5 **halts** there with the discrepancy documented —
same disciplined halt as slice 2 and slice 4 — and we do **not** build Options
2/3 on an unvalidated engine.

## Scope

**IN:** `_build_face_graph` refactor; `fold_to_3d`; `solve_closure`
(Gauss-Newton, finite-diff Jacobian); `tip_vectors`; validation steps 1–3;
exercised on the star-4 winner base plus one clean rigid-foldable fixture (single
degree-4 vertex).

**OUT (named so later slices can grab them):**
- analytic Jacobian (finite-diff is enough to validate the method);
- reachability verdict tool (Option 3 — built *on* this engine);
- flat-equilibrium probe on squared dog/quad (Option 2);
- self-intersection / layer-order coupling during folding;
- arbitrary-pose inverse kinematics (driving to a target pose, not just closing);
- thick / rigid-panel offsets (Tachi's thick-origami extension).

## Testing

- Pure pytest (numpy only) for steps 1–2 and all input-validation / degenerate
  cases (mirror `flat_fold.py`'s and `pose_target.py`'s error-reporting style:
  raise a typed error on structurally-unusable input; *report* residual on
  no-consistent-state input).
- The `flat_fold` refactor must keep every existing `flat_fold`/`layer_order`
  test green (behavior-preserving change — this is a regression tripwire).
- Step 3 ships as a committed probe with an uncommitted `.out.json`, run under
  the headed SimSession (spawn workers need real script files; nohup for subagent
  probes; playwright venv-only).

## Gotchas carried forward

- Our bases are hull-frontier with **accepted** Kawasaki violations, so they are
  not perfectly rigid-foldable; the solver must **report** residual, not assume
  it reaches zero (same contract as `flat_fold`'s `ClosureReport`).
- Derived-quantity drift band is ~0.09°, wider than the ~1e-5–0.02° per-capture
  band; step 3's tolerance uses the derived band.
- StarHeadBase keys tips/hub off the **squared** frame, not the raw hull.
- Jacobian is rank-deficient at ρ=0 (flat) — always seed slightly folded.

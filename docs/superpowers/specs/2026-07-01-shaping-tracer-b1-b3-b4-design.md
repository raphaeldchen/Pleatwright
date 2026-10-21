# Design: Honest-Shaping Tracer Bullet (Pillar B — B1 + B3 + B4 on one primitive)

**Status:** Approved design, ready for implementation planning.
**Date:** 2026-07-01
**Parent doc:** `2026-06-30-finished-model-view-research.md` (Pillar B). A1–A3 (CAD
Model tab) shipped in PR #19 and is the render substrate this feature feeds.

---

## 1. Goal

Prove the entire Pillar-B pipe end-to-end on the smallest honest case: one shaping
primitive — a **tip-local inside reverse fold** — applied server-side to the compiled
base, rendered as a genuinely 3D posed model in the existing Model tab, and validated
by a programmatic physical-realizability check (the sim as oracle).

Success demo: with `IDE_SHAPE_OP` set, compile the dog; the Model tab shows the base
with the chosen flap bent ~90° out of the flat plane, thick lit paper, no validity
rejection. With the env var unset, behavior is byte-identical to today.

## 2. What the code dig established (grounding)

- **The sim already supports shaping.** `ide-bridge.js` only *derives*
  `edges_foldAngle` (M→−180, V→+180) when the FOLD file lacks it; Ghassaei's solver
  natively targets arbitrary per-edge angles scaled by crease-percent. Serving a FOLD
  that carries non-flat angles folds into a 3D pose through the unchanged A1–A3
  pipeline (load → fold visible → capture → thick-paper r3f render).
- **No face bookkeeping.** The bridge rebuilds `faces_vertices` from the edge graph on
  every load. The apply engine only edits `vertices_coords` / `edges_vertices` /
  `edges_assignment` / `edges_foldAngle`, keeping the edge graph planar-valid.
- **Flap tips are locally trivial.** Probing `docs/dog.fold`: every leaf/tip vertex is
  a boundary vertex with exactly two `B` edges plus **one** crease inward (the flap's
  axial crease) — the `BBV`/`BBM` signature. Near the tip the CP has no other
  structure, which is what makes a tip-local analytic construction safe.
- **Flap identity is geometric at this boundary.** `web/server.py` sees only the FOLD
  dict (the tree and `engine.leaf_node_locations()` live in the MCP engine process),
  so the tracer addresses flaps by paper coordinates; B2 later maps anatomy → location.

## 3. Decisions made in this cycle

| Question | Decision |
|---|---|
| Scope | Tracer bullet only: B1 + B3 + B4 on ONE primitive. B2 (agent wiring) next cycle. |
| Demo surface | In-app, server-side at the display boundary (the `square_complete` pattern), op selected by env var. |
| Validity oracle | Existing NaN/empty gate **plus** a paper-conservation (edge-strain) check. Self-intersection deferred. |
| Construction approach | **A: tip-local analytic CP op** (pure geometry, precondition-gated), over B (folded-state-first / fold-through-layers — requires a Python flat-folding engine first; it is the phase-2 generalization) and C (pose-only on existing creases — never exercises crease insertion, the pipe the tracer exists to prove). |

## 4. Architecture & data flow

One new pure-geometry module, `mcp_harness/shaping.py`, plus small touches at
existing seams. No simulator surgery, no new solver, no frontend geometry code beyond
the strain check.

```
compile → base.fold (unchanged; still the raw linted artifact)
                │
web/server.py display boundary:
   display_json = shape( square( fold ) )     ← op from IDE_SHAPE_OP (tracer)
                │
frontend Model tab (A1–A3, unchanged):
   load → sim folds to edges_foldAngle → capture (+flat positions)
        → strain oracle → buildShell → thick lit paper
```

- **Provenance mirror of `square_complete`:** shaping rides on `display_json` only;
  the downloaded/linted `json` stays the raw validated hull. Every shown crease is a
  real crease on the same sheet — the shaped copy is a derived view until B2 promotes
  shaping to a first-class artifact.
- **Ordering matters:** square first, then shape — the wedge creases must land on the
  real paper boundary, which for hull-compiled bases only exists after
  `complete_square`.
- **Failure contract:** like `_square_for_display`, every shaping step is defensive —
  any precondition or transform failure returns the previous step's output unchanged
  (never break the stream), with the refusal reason available for logging.

## 5. B1 — the primitive: tip-local inside reverse fold

`reverse_fold(fold, tip_xy, d, theta, gamma=45°) -> fold` — bend the flap whose tip
vertex is nearest `tip_xy`, at distance `d` from the tip along its axial crease, by
`theta` degrees out of the flat pose.

Construction:

1. **Locate.** Tip vertex `P` = boundary vertex nearest `tip_xy` with the `BB`+1-crease
   signature; the single crease is the axial crease, inward unit direction `u`. Fold
   point `F = P + d·u`; split the axial edge at `F`.
2. **Wedge creases.** Two straight segments from `F` to the raw edge, symmetric about
   the axial line at half-angle `gamma`, splitting the boundary edges where they land.
   These are the real new creases of the reverse fold.
3. **Assignments.** Both wedge arms take the mountain-family assignment; the axial
   segment beyond `F` (tip side) flips M↔V — the classic reverse-fold CP signature.
4. **Angles.** Wedge arms get ±theta-derived partial angles; the tip-side axial gets a
   flipped partial angle. The degree-4 vertex at `F` has a known 1-DOF rigid-origami
   angle relation; start from the analytic relation and **calibrate under the strain
   oracle** (wrong relation → strain → programmatic fail, not a faked pose). This is
   the same self-verifying pattern as A-9's `flap_fill.py`.
5. **Precondition gate.** The disc of radius `d` around `P` must intersect only the
   two boundary edges and the axial crease. Anything else (ridge creases, other flaps,
   molecule structure) → refuse, return input unchanged. This is the fence that keeps
   the tracer out of general CP-boolean territory.

## 6. B3 — serve plumbing

- **Op selection:** `IDE_SHAPE_OP="reverse:<x>,<y>:<d>:<theta>"`, e.g.
  `reverse:0.62,1.0:0.15:90`. Unset ⇒ no shaping, no `edges_foldAngle` emission,
  inactive path byte-identical to today.
- **Placement:** `_square_for_display` generalizes to `_transform_for_display`
  (square → shape, each step defensive).
- **Angle emission:** a helper in `shaping.py` fills `edges_foldAngle` for *every*
  edge (M→−180, V→+180, F/B→0, shaped creases→their 3D angles), emitted only when
  shaping actually applied. The bridge's derive-if-missing branch then never fires.

## 7. B4 — validity oracle (NaN + strain)

Shaping leaves the flat-foldable regime, so Maekawa/Kawasaki (Oriedita) no longer
apply. The replacement law is paper conservation, judged on the sim's converged state:

- **`ide-bridge.js`:** `getFoldedGeometry` additionally returns the *flat* positions
  of the same triangulation (the solver retains originals; exact buffer identified at
  implementation time), same index space as the folded capture.
- **`extraction.ts`:** after the existing finite/non-empty checks, compute per-edge
  strain `|folded_len − flat_len| / flat_len` over the captured triangles; reject the
  capture when max strain exceeds a threshold. Start ~5% and calibrate against the
  known-good unshaped bear/dog bases so A1–A3 stays green. The rejection message
  reports the measured strain — the programmatic "did the paper tear/stretch" verdict.

## 8. Testing

- **Python (pytest, joins the existing suite):**
  - `reverse_fold` unit tests on synthetic tip geometry: vertex/edge counts, wedge
    symmetry about the axial line, assignment flip beyond `F`, complete
    `edges_foldAngle` array, edge-graph planarity (new creases split what they cross).
  - Precondition-refusal cases: foreign crease inside the disc, no tip signature at
    `tip_xy`, `d` overruns the axial crease — all return input unchanged.
  - Fixture test: shape `docs/dog.fold` post-squaring; snapshot as a drift tripwire
    (project convention).
- **Frontend (vitest):** strain-check units on hand-built meshes (flat passes, mild
  passes, stretched rejects); extraction-controller rejection path.
- **Acceptance (manual):** the §1 demo, plus env-var-unset byte-identical check.

## 9. Out of scope (deferred, on purpose)

- **B2** agent wiring (anatomy → op, HITL suggest-then-confirm, MCP tool) — next cycle;
  the env var is its placeholder.
- Additional primitives (crimp, narrow-flap, squash/sink) and op composition.
- Folded-state-first generalization (folds at arbitrary depth through many layers) —
  requires a Python flat-folding engine; phase 2.
- Self-intersection testing (coincident ±180° layers make it false-positive-prone).
- Layer-order-aware thickness (A2) and A4/A5 render polish.
- Flat-foldability of the shaped file — moot by design; the strain oracle is the
  replacement validity law.

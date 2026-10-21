# Rigid origami Phase 2 implementation plan

**Goal:** Ship the deterministic degree-4 topology-to-FOLD artifact pipeline.
**Branch:** `codex/rigid-origami-phase-2-topology-fold`

## Gate P1 — architecture and convention audit

- [x] Confirm Phase-1 PR #38 is merged into current `origin/main`.
- [x] Cut the requested Phase-2 branch in the dedicated rigid worktree.
- [x] Read the required rigid docs, schema, Phase-1 mathematics, tests, fixtures,
  legacy FOLD/face extraction, and CLI/build surfaces.
- [x] Research FOLD 1.2, degree-4/rigid-fold sources, RFC 8259, and RFC 8785.
- [x] Complete independent repository, FOLD, `SE(3)`, and provenance audits.
- [x] Freeze finite geometry, scale, topology IDs/orientation, fixed face,
  spanning tree/cycle, transform direction/order, FOLD profile, branch bridge,
  canonical bytes, hash DAG, metamorphic behavior, and claim boundary.
- [x] Commit the audit, design specification, and this plan before production
  code.

## Gate P2 — independent fixtures and topology authority

Each checkbox is implemented through one or more red-green-refactor cycles.

- [x] Commit an independent Phase-2 fixture generator and pose/reference anchors.
- [x] Commit `ro-cjson-1` byte/hash vectors and standards-only FOLD fixture.
- [x] Implement strict canonical JSON/parser behavior and runtime profile guard.
- [x] Implement the equal-radius finite degree-4 generator.
- [x] Implement half-edges, twins, face loops, vertex stars, boundary loops,
  components, dual graph, Kruskal tree, and fundamental cycles.
- [x] Add positive fixtures and one structured diagnostic regression per negative
  topology class.
- [x] Prove reindex normalization, cyclic mappings, reflection mappings, axis
  reversal/side swap, and uniform-scale behavior.
- [x] Commit the topology authority as a coherent unit.

## Gate P3 — face-pose and trajectory authority

- [x] Implement the simple left/right hinge crossing anchor.
- [x] Propagate fixed-`f3` poses over the canonical tree.
- [x] Check `SE(3)`, all face distances, shared vertices, both hinge endpoints,
  axes, normalized translation, and omitted cycles.
- [x] Match omitted `e3` against the Phase-1 product/residual.
- [x] Compare all four ring spanning-tree choices.
- [x] Resolve exact schema-compatible branch keys and reject stale/ambiguous IDs.
- [x] Compile deterministic non-flat samples for both fixtures, both branches,
  both travel signs, and multiple target magnitudes.
- [x] Cover exact-flat inconclusive, near-flat rejection, binding, and just-inside
  binding.
- [x] Prove forward/reverse traversal and reverse-travel mirror behavior.
- [x] Commit face poses and trajectory compilation as coherent units.

## Gate P4 — FOLD and provenance authority

- [x] Export deterministic reference `creasePattern` frames with `U+0` hinges.
- [x] Export folded static frames with explicit XYZ, radians-to-degrees boundary,
  and anchored `M/V` signs.
- [x] Emit explicit `edges_faces`, `faces_edges`, stable IDs, and namespaced
  metadata with exact parallel-array alignment.
- [x] Reject every unsupported FOLD feature with stable diagnostics.
- [x] Normalize fully reindexed profiled FOLD artifacts to identical bytes.
- [x] Prove export does not mutate inputs and repeated export is byte-identical.
- [x] Recompute design, mechanism, reference, sample, and trajectory hashes.
- [x] Corrupt every serialized artifact class and dependency link.
- [x] Commit FOLD/canonicalization/provenance as a coherent unit.

## Gate P5 — certificate, bundle, and CLI vertical slice

- [x] Assemble schema-valid topology/local/global certificate evidence.
- [x] Keep collision and flat endpoint `not_run` with explicit warnings.
- [x] Prevent pass for exact flat, singular samples, excessive closure, incomplete
  rank evidence, or positional inconsistency.
- [x] Write the deterministic bundle through a verified sibling temp directory.
- [x] Implement independent disk verification without production generation,
  pose propagation, or FOLD writing shortcuts.
- [x] Implement `compile-degree4`, `verify`, and `inspect` CLI commands.
- [x] Prove failure atomicity, byte-identical reruns, safe manifest paths, and no
  network/UI dependency.
- [x] Commit certificate/CLI behavior as a coherent unit.

## Gate P6 — adversarial review and integration

- [x] Request an independent adversarial review of topology, signs, transforms,
  branch identity, FOLD, hashing, certificates, and corruption behavior.
- [x] Add a regression for every P1/P2 finding and resolve all such findings.
- [x] Run focused rigid tests and record exact counts/residual maxima.
- [x] Confirm public schema source/generated JSON did not change.
- [x] Run `make PYTHON=<shared-python> test`.
- [x] Run web backend and frontend isolation gates.
- [x] Run `compileall` and `git diff --check`.
- [x] Fetch/merge current `origin/main`, then rerun the complete gate.
- [x] Create `docs/rigid-origami-phase2-outcome.md` with versions, commands,
  counts, residuals, hashes, findings, changes, commits, limits, and next slice.
- [x] Commit outcome/integration evidence, push, and open a ready PR.

## Deferred after Phase 2

The recommended next vertical slice is multi-vertex global continuation with
explicit `SE(3)` cycle constraints, followed by the first bounded Miura family.
Collision/CCD remains a separate evidence stage.

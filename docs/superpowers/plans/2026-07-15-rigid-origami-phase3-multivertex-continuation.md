# Phase 3 rigid-origami multi-vertex continuation implementation plan

**Date:** 2026-07-15  
**Design:** `docs/superpowers/specs/2026-07-15-rigid-origami-phase3-multivertex-continuation-design.md`

This plan uses strict red-green-refactor TDD.  Every production item names its
first observable test.  Commits preserve the requested eight coherent slices.

## Gate M1 — authority frozen

- [x] Verify PR #43 merged, fetch current `origin/main`, and create the isolated
  Phase-3 worktree/branch without changing either earlier checkout.
- [x] Read Phase-1/2 audits, designs, outcomes, production modules, tests,
  fixtures, Miura scaffolding, and legacy experiments.
- [x] Research primary Miura, rigid-origami, Lie-group, continuation, and FOLD
  sources; maintain the evidence ledger.
- [x] Freeze audit, design, and this plan before production code.
- [ ] Commit `docs: freeze phase 3 global continuation authority`.

## Commit 2 — independent fixtures

1. Add a generator that imports no `rigid` production package.
2. Generate 2x3 and 3x4 reference vertices, face loops, edge incidence,
   assignments, local sector order, shared-fold relations, analytic trajectory
   states, and high-precision hashes.
3. Include a hand-derived nonconcurrent cycle transform and separate
   translation/rotation corruption anchors.
4. Include five-point Jacobian anchors at fixed non-flat states.
5. Include 100-digit circle turning-point anchors, far-root branch-jump data,
   binding point, rank-loss, and bifurcation-candidate fixtures.
6. Add generator self-tests for topology counts, exact relation residuals,
   canonical ordering, and deterministic reruns.
7. Commit `test: freeze independent phase 3 authorities`.

## Commit 3 — Miura geometry and topology (Gate M2)

1. **Red:** minimum 2x3 coordinates/loops equal the independent fixture.
2. **Green:** implement `patterns.miura` grid geometry and stable IDs.
3. **Red:** exact counts, positive areas, one boundary, shared edge IDs, and
   left/right sides for minimum and 3x4 patches.
4. **Green:** build unique edge incidence, hinges, fixed face, and sheet.
5. **Red:** local sectors/assignments/half-angle seed match fixture for both
   travel signs; shared crease angles are identical.
6. **Green:** implement branch key, driver inversion, analytic seed, and
   structured unsupported-angle/request diagnostics.
7. **Red:** two-cycle bijection and nonconcurrent second minimum cycle.
8. **Green:** derive lexicographic tree paths/cycles and strengthen topology
   omitted-hinge bijection validation.
9. **Red/green:** minimum/larger, reflection, reindex mapping, scale, malformed
   incidence, repeated/missing cycles, hole/cut/disconnect adversaries.
10. Run all Phase-1/2 rigid tests and confirm frozen hashes unchanged.
11. Commit `feat: compile bounded multi-vertex Miura topology`.

## Commit 4 — global residual and Jacobian (Gate M3)

1. **Red:** one serialized nonconcurrent cycle evaluates to fixture `SE(3)`
   transform and six signed residual coordinates.
2. **Green:** implement stable `SO(3)` left Jacobian/inverse and `SE(3)` log
   coordinates with near-zero series.
3. **Red:** translation-only and rotation-only corruption affect the expected
   residual blocks; scale normalization is invariant.
4. **Green:** precompute directed cycle factors and evaluate every cycle.
5. **Red:** first analytic column matches independent five-point anchor.
6. **Green:** implement prefix adjoints and differentiated inverse-left-Jacobian.
7. Extend red/green to all columns, both patches/signs, fixed-seed randomized
   parameters, near identity, alternate valid trees/bases, cycle reversal,
   reflection, scale, non-finite, and log-cut cases.
8. Add strict rank/nullity/conditioning evidence and inclusive tolerance tests.
9. Record max analytic-vs-five-point error.
10. Commit `feat: add global SE3 residual and analytic Jacobian`.

## Commit 5 — deterministic continuation (Gate M4)

1. **Red:** initialize a unique oriented tangent on one circle anchor.
2. **Green:** implement protocol, policy validation, SVD tangent/rank rules.
3. **Red:** one predictor/corrector reaches the next high-precision anchor.
4. **Green:** implement Keller hyperplane and thresholded-SVD Newton.
5. **Red:** far circle root is rejected by correction tube.
6. **Green:** deterministic Armijo halving, bounds, tube, and alignment guards.
7. **Red/green:** cross the circle's driver-coordinate turning point; forward
   trace and recorded-step reverse replay agree.
8. **Red/green:** retries halve exactly, adaptation is deterministic, exhausted
   corrector returns a structured event, exact boundaries use frozen inclusive
   semantics.
9. **Red/green:** binding, exact-flat, near-flat, rank-loss, bifurcation
   candidate, nonfinite, and no-automatic-switch behavior.
10. **Red/green:** checkpoint/restart bytes equal uninterrupted trace.
11. **Red:** minimum Miura analytic seed has nullity one away from flat.
12. **Green:** adapt global system to generic kernel; trace both signs and
   directions for minimum and larger patches.
13. Validate all local relations, global cycles, alternate trees, poses, and
   oracle states at every accepted Miura sample.
14. Commit `feat: continue deterministic Miura branches`.

## Commit 6 — artifacts, verifier, and CLI (Gate M5)

1. **Red:** generic reference/static sample FOLD arrays match independent
   fixture, preserve M/V degree signs, and normalize byte-identically.
2. **Green:** add `miura_fold` v1 writer without changing Phase-2 writer.
3. **Red:** continuation manifest exact shape/order/hash vector.
4. **Green:** serialize branch/system/policy/seed/sample/event evidence.
5. **Red:** certificate refuses flat, rank-deficient, translation-failing,
   Jacobian-mismatched, collision-required, or overclaimed requests.
6. **Green:** create honest schema-0.1 summary and bundle-v2 hash DAG.
7. **Red:** independent on-disk verifier accepts the authority fixture without
   importing any prohibited production generator/solver/writer.
8. **Green:** implement independent geometry, cycle transform, five-point
   derivative, rank, arclength, pose, FOLD, hash, and certificate checks.
9. **Red/green:** corrupt every artifact and dependency link; malformed files,
   unsafe paths, symlinks/special files, extra/missing bytes, numerical evidence,
   assignments/units, and overclaims fail with stable diagnostics.
10. **Red/green:** `compile-miura`, `verify`, and `inspect`; atomic no-clobber,
    failed-publication cleanup, and byte-identical reruns.
11. Run under multiple `PYTHONHASHSEED` values and freeze full hash vectors.
12. Commit `feat: publish independently verified Miura bundles`.

## Commit 7 — adversarial fixes

1. Spawn an independent read-only adversarial reviewer after implementation.
2. Review equations, signs, cycle/tree invariance, rank claims, continuation
   event semantics, verifier independence, FOLD interoperability, and security.
3. Classify findings P0-P3.  Resolve every P1/P2; add one regression per fix.
4. Run mutation probes for dropped translation, swapped left/right, axis/fold
   sign mismatch, reordered variables, missing cycle, finite-difference leakage,
   branch jump, rank-threshold weakening, restart tampering, and hash bypass.
5. Commit `fix: harden phase 3 continuation authority` if changes are needed.

## Commit 8 — outcome and integration (Gate M6)

1. Record dependency/runtime versions and fixture/artifact hashes.
2. Run focused rigid tests; record counts and maxima for geometry, pose,
   rotation, translation, Jacobian, corrector, oracle, and FOLD round trip.
3. Run `python -m compileall` for changed Python packages.
4. Run full `make test`, web tests, frontend tests/build/lint as defined by the
   repository; rebuild external engines if the gate requires it.
5. Run `git diff --check`, status audit, and Phase-2 frozen-hash regressions.
6. Fetch and merge latest `origin/main`; resolve only Phase-3 overlaps and
   rerun the full gate.
7. Write `docs/rigid-origami-phase3-outcome.md` with architecture, equations,
   exact counts/maxima/hashes, compatibility, findings, commits, limitations,
   and recommended next slice.
8. Commit `docs: record phase 3 continuation outcome`.
9. Push `codex/rigid-origami-phase-3-multivertex-continuation`.
10. Open a ready PR with scope, evidence, claim limits, and CI context.

## Required final evidence

- Minimum and larger fixture identities and counts.
- Both travel signs, forward/reverse, multiple pseudo-arclengths, and exact
  checkpoint/restart byte identity.
- Maximum reference geometry, local relation, rotational closure, normalized
  translation closure, analytic/five-point Jacobian, corrector, face isometry,
  shared-edge, axis, oracle, and FOLD round-trip errors.
- Rank/nullity and conditioning ranges; flat/binding/rank-loss classifications.
- Bundle/hash vectors under multiple hash seeds and all corruption diagnostics.
- Focused/full/web/frontend/compileall counts and exact runtime versions.
- Adversarial findings and regressions.
- Eight coherent commit hashes, current-main integration commit, pushed branch,
  and ready PR URL.


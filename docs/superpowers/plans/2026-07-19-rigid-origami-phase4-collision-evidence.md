# Phase 4 rigid-origami collision-evidence implementation plan

**Date:** 2026-07-19
**Design:** `docs/superpowers/specs/2026-07-19-rigid-origami-phase4-collision-evidence-design.md`

This plan uses strict vertical red-green-refactor TDD. Production work begins
only after the audit/design/plan authority is committed. Each numbered behavior
starts with one failing public-interface test and the smallest implementation
that makes it pass.

## Gate C1 — authority frozen

- [x] Confirm the Phase-3 worktree is clean at exact
  `354d238d1fb14e961c99baa0d7eba6fbbf5350bb`.
- [x] Confirm current `main` does not contain that commit and stack Phase 4 on
  `codex/rigid-origami-phase-3-multivertex-continuation`.
- [x] Create the isolated Phase-4 worktree and branch.
- [x] Read Phase-3 audit, design, plan, outcome, implementation, tests, and
  fixtures completely.
- [x] Reproduce the rigid baseline (`498 passed`).
- [x] Complete parallel geometry, artifact, architecture/reuse, and security
  audits and primary-source numerical review.
- [x] Freeze contact semantics, exactness boundary, profile/hash domains,
  limits, diagnostics, and the CCD gate.
- [ ] Commit `docs: freeze phase 4 collision authority`.

## Commit 2 — independent oracle and tracer bullet

1. Add the no-production-import exact rational oracle generator.
2. Freeze separated, noncoplanar crossing, coplanar overlap, edge contact,
   vertex contact, legal hinge, off-hinge adjacent collision, triangulation
   diagonal, seam-boundary, collision-free Miura, colliding integration, and
   interior-only CCD cases.
3. Add byte-regeneration, metadata, generator-import, and fixture-hash tests.
4. **Red:** one public `evaluate_collision_sample` test for the separated oracle
   case fails before `rigid.collision_geometry` exists.
5. Record the exact red command and diagnostic for the outcome report.
6. **Green:** implement only immutable validated faces, the stable broad phase,
   and separated result needed by the tracer bullet.
7. Commit `test: freeze independent phase 4 collision oracle` after green.

## Commit 3 — broad and discrete narrow phase (Gate C2)

1. **Red/green:** insertion-order-independent sweep candidates equal the
   independent exhaustive `O(F^2)` candidates.
2. **Red/green:** closed AABB touching and immediately separated boundaries.
3. **Red/green:** proper noncoplanar face crossing via exact plane slices.
4. **Red/green:** coplanar area overlap via exact 2D convex clipping.
5. **Red/green:** edge-only and vertex-only contacts classify collision.
6. **Red/green:** no intersection classifies separated.
7. **Red/green:** a would-be fixed-diagonal crossing remains detected because
   the direct convex predicate introduces no internal diagonal.
8. **Red/green:** legal shared hinge and shared vertex are neutral contacts.
9. **Red/green:** adjacent faces intersecting away from their hinge collide.
10. **Red/green:** seam tolerance exactly at, below, and above the inclusive
    boundary; nonfinite, duplicate, nonconvex, degenerate, nonplanar, and
    malformed topology never pass.
11. Refactor exact vector/clip helpers only while green.
12. Run the complete geometry/oracle tests under hash seeds 0, 1, and 8675309.
13. Commit `feat: add exact discrete face collision evaluation`.

## Commit 4 — verified Phase-3 integration and evidence (Gate C3)

1. **Red:** compile a three-sample 2x3 Phase-3 bundle, snapshot/verify it, and
   produce a pass evidence object without changing any source bytes.
2. **Green:** implement bounded immutable source snapshots and independent
   source verification on the snapshot.
3. **Red/green:** reconstruct each face from reference coordinates and its own
   serialized face matrix with exact dyadic affine arithmetic.
4. **Red/green:** stable `[seed,*samples]`, face, pair, and source-link order.
5. **Red/green:** compile every per-sample candidate/evaluation/count/status and
   deterministic first collision.
6. **Red/green:** deliberately colliding integrated snapshot yields fail while
   still producing valid evidence.
7. **Red/green:** an unsupported evaluation reduces to inconclusive unless a
   proven collision exists.
8. **Red/green:** CCD is exactly `not_run`; any continuous overclaim is rejected.
9. Freeze representative evidence bytes/hashes under multiple hash seeds.
10. Confirm all Phase-3 artifact hashes and `collision:not_run` bytes unchanged.
11. Commit `feat: generate discrete collision evidence from phase 3`.

## Commit 5 — sidecar hash DAG and independent verifier (Gate C4)

1. **Red:** exact three-file manifest/evidence/certificate vector.
2. **Green:** implement domain-separated evidence and certificate identities and
   fixed-order bundle manifest.
3. **Red:** independent verifier accepts the authority sidecar while an AST test
   proves it imports no production collision evaluator/writer/compiler or
   prohibited Phase-3 generator/solver/writer.
4. **Green:** independently reconstruct faces, compute exhaustive candidates,
   repeat narrow predicates, reduce summaries, and validate all source/hash
   links.
5. **Red/green mutation loop, one mutation at a time:** omitted/extra/reordered/
   duplicate/reversed pairs; sample drift; false relation; false legal feature;
   candidate omission; first-collision/status/count forgery; CCD overclaim;
   policy/profile drift; source substitution; evidence/certificate/manifest
   rehashing.
6. Require fully rehashed false evidence to fail independent replay.
7. Commit `feat: independently verify collision sidecars`.

## Commit 6 — filesystem, limits, CLI, and publication (Gate C5)

1. **Red/green:** exact three regular files; missing/extra members and
   directories fail.
2. **Red/green:** root/member/in-bundle-ancestor symlinks,
   FIFO/socket/device, malformed
   UTF-8 names, unsafe/NUL paths, and special files fail without blocking.
3. **Red/green:** canonical JSON, BOM, duplicate key, nonfinite/overflow number,
   unsafe integer, excess depth, trailing byte, hash format/mismatch failures.
4. **Red/green:** sample/face/pair/candidate/work limits exactly at and one over
   the boundary fail before unbounded allocation; use pure preflight
   predicates where no profile-valid integer case lands exactly on a bound.
5. **Red/green:** manifest/certificate/evidence/source/total byte boundaries.
6. **Red/green:** snapshot replay is immune to source mutation after capture.
7. **Red/green:** source/output equality and nesting are rejected.
8. **Red/green:** `generate-collision`, `verify-collision`, and
   `inspect-collision` canonical JSON/exit behavior.
9. **Red/green:** atomic no-replace publish, identical rerun, differing output,
   destination race, verifier failure cleanup, and unsupported platform.
10. Verify legacy `verify`/`inspect` and Phase-2/3 publication unchanged.
11. Commit `feat: publish collision evidence sidecars`.

## Gate C6 — conditional interval CCD review

1. Run the discrete oracle, mutation suite, rigid suite, and local gate.
2. Evaluate whether Phase-3 serialized records provide a certified continuous
   branch segment rather than only accepted endpoints.
3. Freeze the needed motion parameter, branch isolation, interval state/pose
   enclosures, swept bounds, inclusion predicates, subdivision, work limits,
   convergence result, and first-contact bracket.
4. Replay the endpoint-clear/interior-collision oracle case.
5. Decision: Phase-3 v1 lacks those enclosures. Do not implement an endpoint-
   interpolation CCD approximation. Keep Phase 4A CCD `not_run` and document the
   precise Phase-4B continuation-contract extension. Permit that extension as
   a separately verified sidecar so Phase-3 bytes remain unchanged.

## Commit 7 — independent adversarial reviews and fixes

1. Obtain one read-only geometry/numerical review focused on exact rational
   signs/constructions, plane slicing, coplanar clipping, contact envelopes,
   diagonal independence, and broad-phase conservativeness.
2. Obtain one independent artifact/security review focused on canonical bytes,
   immutable source binding, hash domains, complete replay, resource limits,
   path handling, and fully rehashed forgeries.
3. Classify findings P0-P3; fix every material P1/P2 with a regression.
4. Rerun targeted geometry, verifier, mutation, determinism, and compatibility
   tests after each fix.
5. Commit `fix: harden phase 4 collision evidence` if changes are required.

## Commit 8 — outcome and full verification (Gate C7)

1. Regenerate the independent oracle and compare bytes.
2. Record generator/fixture/evidence/certificate/bundle hashes.
3. Compute observed candidate counts, relation counts, exact predicate boundary
   results, and maximum Phase-3 shared-feature gap used by the contact policy.
4. Run all `test_rigid_*.py` tests under warnings-as-errors.
5. Run exact local CI:

   ```text
   make PYTHON=<repo>/mcp_harness/.venv/bin/python test
   ```

6. Run multiple `PYTHONHASHSEED` values and repeated clean generations.
7. Run Python compileall and `git diff --check`.
8. Run web/frontend gates only if shared interfaces or frontend code changed.
9. Write `docs/rigid-origami-phase4-outcome.md` with architecture, predicates,
   semantics, independent authority, hash DAG, limits, exact commands/counts,
   numerical evidence, adversarial fixes, CCD decision, compatibility,
   macOS/Ubuntu caveat, interruptions, and next slice.
10. Commit `docs: record phase 4 collision outcome`.

## Publication

1. Confirm PR #45 remains unmerged. If so, target
   `codex/rigid-origami-phase-3-multivertex-continuation`; target `main` only if
   it contains exact Phase-3 HEAD.
2. Confirm worktree clean and exact local gate pass.
3. Push `codex/rigid-origami-phase-4-collision-evidence`.
4. Open a ready stacked PR describing the discrete-only claim, independent
   replay, compatibility, explicit CCD deferral, and complete local evidence.
5. Explain that GitHub Actions has a known external billing/spending-limit
   zero-step failure and is not the code verdict authority.

## Required final evidence

- branch/worktree/HEAD/commit/PR identities and clean status;
- red and green tracer-bullet commands/output;
- oracle generator/fixture and representative sidecar hashes;
- broad-versus-exhaustive equality and deterministic first collision;
- all required intersection/contact/degeneracy/diagonal fixtures;
- exact rational predicate claim and the bounded `1e-9 mm` seam semantics;
- sample/face/pair/candidate/byte limits and boundary tests;
- independent replay and fully rehashed mutation rejection;
- Phase-3/schema-0.1.0 frozen-byte compatibility;
- CCD `not_run` reason and exact Phase-4B authority needed;
- targeted/rigid/full local test counts and runtimes;
- adversarial findings/fixes; and
- crash-lost, interrupted, or reconstructed work.

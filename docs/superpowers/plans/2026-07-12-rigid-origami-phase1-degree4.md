# Rigid origami Phase 1 implementation plan

**Goal:** Ship the notation-audited degree-4 oracle and SO(3) closure kernel.
**Branch:** `codex/rigid-origami-phase-1-degree4`

## Gate R1 — notation before formulas

- [x] Read Phase-0 architecture, outcome, conventions, fixtures, schemas,
  rotation primitives, and all rigid tests.
- [x] Audit Foschi–Hull–Ku source order, fold sign, Eq. (6) roots, and the
  reciprocal/cotangent reading of Theorem 3.
- [x] Reconcile the stored hinge transform with CCW vertex traversal.
- [x] Record cyclic/reflection/reversal/scale mappings and the uncertainty ledger.
- [x] Obtain independent source-review agreement.
- [x] Commit these three documents before production formulas.

## Gate R2 — independent goldens

- [x] Add a standalone high-precision evaluator under test fixtures.
- [x] Generate 80-digit goldens for both generic fixtures, both branches, both
  travel signs, and multiple driver magnitudes.
- [x] Record generator version/hash, precision, equations, copied-byte status,
  tolerances, and fixture hash.
- [x] Confirm the evaluator imports no production degree-4 or closure module.

## Gate R3 — closure and analytic solver, vertical TDD

Each item is one red-green-refactor slice; do not batch all tests first.

1. [x] Identity and exact-axis SO(3) log tests, then minimal log implementation.
2. [x] Small-angle and near-pi guarded tests, then guarded implementation.
3. [x] Pinned unfolded/non-flat rotation product tests, then closure product.
4. [x] Invalid/non-finite/non-SO(3) tests, then strict validation.
5. [x] Raw-sector classification tests, then classifier.
6. [x] First branch/travel golden test, then minimum analytic evaluator.
7. [x] Reverse travel and second root tests, then durable tangent selection.
8. [x] All fixture values and closure cross-checks, then general cyclic driver
   support.
9. [x] Wrong-root/wrong-sign regressions.
10. [x] Driver round-trip and deterministic output tests.

## Gate R4 — singularity, trace, and metamorphic behavior

1. [x] Non-flat Jacobian rank-3/nullity-1 test, then diagnostics.
2. [x] Exact-flat rank-2/nullity-2 test with no finite-2-DOF claim.
3. [x] Rank-threshold boundary tests.
4. [x] Bounded non-flat trace forward and reverse.
5. [x] Cyclic reindexing and reflection mappings.
6. [x] Axis reversal, reverse travel, and uniform ray-scale invariance.
7. [x] Approach-to-zero tests without false flat certification.

## Verification and review

- [x] Run focused rigid tests with the shared Python 3.14 environment.
- [x] Confirm schemas are byte-identical; do not regenerate because contracts do
  not change.
- [x] Run `make PYTHON=<shared-python> test`.
- [x] Run web backend and frontend isolation gates.
- [x] Run `compileall` and `git diff --check`.
- [x] Request independent adversarial review after implementation.
- [x] Fix every P1/P2 issue and add one regression per issue.
- [x] Add `docs/rigid-origami-phase1-outcome.md` with exact versions, commands,
  counts, tolerances, residual maxima, hashes, limitations, and deferred work.
- [x] Commit the outcome and push the branch.

## Explicitly deferred

Miura, flashers, arbitrary topology, collision/CCD, SE(3) cycles, MCP tools,
agent prompts, frontend, thickness, fabrication, mechanics, and learned
feasibility remain out of scope.

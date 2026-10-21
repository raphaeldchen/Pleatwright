# Rigid origami Phase 0 implementation plan

**Goal:** Ship the contract-and-convention kernel specified in
`docs/superpowers/specs/2026-07-12-rigid-origami-phase0-design.md` without
changing the legacy TreeMaker, linter, agent, simulator, or frontend paths.

**Branch:** `codex/rigid-origami-phase-0`

**Tech stack:** Python 3.14, Pydantic 2.13, NumPy 2.4, jsonschema 4.26, pytest 9.
New direct requirements are declared for the rigid package rather than assumed
from transitive MCP dependencies.

## Binding constraints

- `MetricTree` remains the sole AI-editable source for TreeMaker; the rigid path
  uses `RigidDesignSpec` and does not convert between the two in version 1.
- Internal length is millimeters; internal angle is radians; positive fold is
  valley; FOLD serialization is degrees with the same sign.
- Pydantic models are strict, frozen, extra-forbidden, non-finite-forbidden,
  versioned, and use immutable nested collections.
- Tests belong in `mcp_harness/tests/` so `make test` discovers them.
- No degree-4 equation is implemented until a separate notation audit maps the
  paper diagram and square-root branches.
- No user-owned untracked artifact is removed, overwritten, or staged.

## Task 0: Record the pre-change baseline

- [x] Create/switch to `codex/rigid-origami-phase-0`.
- [x] Run `make test`.
  - Result: `481 passed, 4 skipped` in `576.09s`.
- [x] Run `PYTHONPATH=. mcp_harness/.venv/bin/python -m pytest web/tests -q`.
  - Result: `40 passed`, one existing Starlette deprecation warning.
- [x] Run `npm test -- --run` in `web/frontend`.
  - Result: `59 passed` across six test files.
- [x] Persist environment/package versions and the commands in the Phase-0
  baseline note.

## Task 1: Freeze documentation before code

- [x] Write the Phase-0 design spec.
- [x] Write this ordered implementation plan.
- [x] Add `docs/adr/0001-multi-compiler-rigid-origami.md` covering source
  ownership, authority, FOLD-as-interchange, and legacy isolation.
- [x] Add `docs/rigid-origami-v1-scope.md` with supported/non-supported claims.
- [x] Add `docs/rigid-origami-conventions.md` with the exact hinge diagram/table,
  numerical policy, branch identity, and Rigid FOLD Profile 0.1.
- [x] Add `docs/rigid-origami-third-party.md` with license/use status and the
  permissive-only-until-decided policy.
- [x] Add `docs/rigid-origami-fixtures.md` with provenance fields and reserved
  degree-4 fixtures.

## Task 2: Add failing contract tests

Create `mcp_harness/tests/test_rigid_schema.py` covering:

- [x] valid diagnostic degree-4 and Miura specs;
- [x] discriminated-family/parameter mismatch;
- [x] extra field, string-number coercion, NaN/Infinity, invalid bounds, raw
  coordinate, duplicate objective, and duplicate stable-ID rejection;
- [x] mechanism graph reference and hinge-role validation;
- [x] kinematics-only certificate with collision `not_run`;
- [x] impossible certificate status combinations;
- [x] immutable project revisions/artifact references;
- [x] generated Draft 2020-12 schema validation with `jsonschema`.

Run:

```text
cd mcp_harness && .venv/bin/python -m pytest tests/test_rigid_schema.py -q
```

Expected before implementation: import/collection failure because the rigid
package does not exist.

## Task 3: Implement the four contracts

- [x] Add `mcp_harness/rigid/__init__.py`.
- [x] Add `mcp_harness/rigid/schema.py` with:
  - strict immutable base model and bounded scalar/ID/hash types;
  - family-discriminated `RigidDesignSpec`;
  - reference-validated `RigidMechanismGraph`;
  - staged-evidence `MotionCertificate` with status-consistency validators;
  - immutable `RigidProjectRecord` revisions/events/artifact references;
  - stable public exports and schema version constants.
- [x] Add `mcp_harness/rigid/requirements.txt` declaring the direct Phase-0
  dependencies and license comments/links.
- [x] Make the Task-2 tests pass without weakening strictness.

## Task 4: Export and independently validate JSON Schemas

- [x] Add `mcp_harness/rigid/export_schemas.py` with deterministic key ordering
  and stable Draft 2020-12 `$id` values.
- [x] Add generated schemas under `mcp_harness/rigid/schemas/` for all four
  top-level artifacts.
- [x] Test regeneration is byte-identical.
- [x] Run `Draft202012Validator.check_schema` on every generated schema.
- [x] Do not implement semantic hashes until an RFC 8785 dependency/implementation
  is explicitly selected.

## Task 5: Add failing convention and rotation tests

Create `mcp_harness/tests/test_rigid_conventions.py` covering:

- [x] radians/degrees conversion and M/V assignment at exact anchors;
- [x] CCW signed-area/face-normal convention;
- [x] right-handed `R_x(pi/2)` exact fixture;
- [x] arbitrary unit-axis rotation orthogonality and determinant;
- [x] positive-valley hinge maps the canonical right-face point to `+z`;
- [x] reversed edge plus swapped faces gives the same physical pose;
- [x] invalid/nonunit axes, invalid angles, and non-finite inputs fail cleanly.

Expected before implementation: import failure for the new modules.

## Task 6: Implement convention and rotation primitives

- [x] Add `mcp_harness/rigid/conventions.py` with versioned constants and
  centralized unit/sign conversion.
- [x] Add `mcp_harness/rigid/kinematics/__init__.py`.
- [x] Add `mcp_harness/rigid/kinematics/rotations.py` with active right-handed
  axis-angle rotation and the left-to-right hinge transform.
- [x] Keep the primitive independent of SciPy; use NumPy and explicit checks.
- [x] Make the Task-5 tests pass at the documented tolerances.

## Task 7: Run the proportional verification gate

- [x] Run focused rigid tests.
  - Result: `76 passed in 0.21s`.
- [x] Run `make test`; expected count is the baseline plus the new rigid tests,
  with the same four skips.
  - Result: `557 passed, 4 skipped` in `541.58s`, exactly baseline plus 76.
- [x] Run web backend tests and frontend Vitest to demonstrate isolation.
  - Result: web `40 passed`; frontend `59 passed` across six files.
- [x] Run `git diff --check`.
- [x] Verify no existing tracked source file changed outside documentation.
- [x] Verify all original user-owned untracked files remain present.

## Task 8: Record the outcome and next gate

- [x] Add `docs/rigid-origami-phase0-outcome.md` containing exact commands,
  versions, test counts, generated schema hashes, tolerances, known limitations,
  and next task IDs.
- [x] Next gate: a diagram-level Foschi/Hull/Ku notation audit followed by
  rotation-product closure, flat-singularity diagnostics, and one analytic
  degree-4 mode fixture. Do not jump to Miura, MCP, or frontend work.

## Slice acceptance checklist

- [x] Documentation precedes implementation in the branch history/work log.
- [x] Four contracts are reviewable, versioned, strict, and independently
  schema-validated.
- [x] Certificate semantics cannot turn missing collision work into a pass.
- [x] Fold sign, hinge orientation, face winding, units, and branch identity are
  unambiguous.
- [x] Exact rotation and positive-valley hinge fixtures pass.
- [x] Legacy TreeMaker, Oriedita normalization, agent loop, simulator, and UI are
  unchanged and retain their baselines.

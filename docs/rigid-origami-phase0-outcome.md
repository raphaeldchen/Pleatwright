# Rigid origami Phase-0 outcome

**Date:** 2026-07-12
**Branch:** `codex/rigid-origami-phase-0`
**Starting commit:** `450059b`
**Design specification:**
`docs/superpowers/specs/2026-07-12-rigid-origami-phase0-design.md`
**Implementation plan:**
`docs/superpowers/plans/2026-07-12-rigid-origami-phase0.md`

## Result

Phase 0 established the contract-and-convention kernel for a sibling rigid-
origami compiler without changing the legacy TreeMaker, Oriedita, agent, web,
simulator, or frontend source paths. The design specification and ordered plan
were completed before implementation began.

The slice added:

- strict, frozen, versioned Pydantic contracts for `RigidDesignSpec`,
  `RigidMechanismGraph`, `MotionCertificate`, and `RigidProjectRecord`;
- deterministic Draft 2020-12 JSON Schema exports for all four artifacts;
- explicit graph ownership, winding, incidence, hinge-side, hinge-axis,
  cycle, sector, evidence, rank, and immutable-project invariants;
- centralized millimeter/radian/FOLD-degree and M/V/U conventions;
- active right-handed axis-angle rotation and the oriented left-to-right hinge
  transform;
- adversarial and exact-fixture tests under the repository's existing test
  discovery path.

The review/fix loop closed seven contract defects before the final gate:
ordered-sector validation, hinge-edge bijection, geometric left/right and axis
checks, face winding/incidence/sheet ownership, recomputable rank evidence,
certificate pass consistency, typed project events, and geometrically
zero-length hinge rejection. A final independent narrow review found no
remaining P1/P2 contract-correctness issue.

## Verification

Environment:

- Python 3.14.3
- Pydantic 2.13.4
- NumPy 2.4.6
- jsonschema 4.26.0
- pytest 9.0.3

Focused contract and convention gate:

```text
cd mcp_harness
.venv/bin/python -m rigid.export_schemas
.venv/bin/python -m pytest \
  tests/test_rigid_schema.py tests/test_rigid_conventions.py -q
```

Result: `76 passed in 0.21s`. Regeneration was byte-identical and every schema
passed `Draft202012Validator.check_schema` plus independent example validation.

Full repository gate:

```text
make test
```

Result: `557 passed, 4 skipped, 1 existing warning in 541.58s`. This is
the `481 passed, 4 skipped` baseline plus all 76 new rigid tests. The warning is
the existing joblib physical-core detection fallback.

Isolation gates:

```text
PYTHONPATH=. mcp_harness/.venv/bin/python -m pytest web/tests -q
cd web/frontend && npm test -- --run
```

Results:

- web backend: `40 passed, 1 existing warning in 0.72s`;
- frontend: `59 passed` across six files in `374ms` total Vitest duration.

Mechanical checks:

```text
mcp_harness/.venv/bin/python -m compileall -q mcp_harness/rigid
git diff --check
git diff --name-only
```

Results: all commands passed. `git diff --name-only` was empty because this
slice adds isolated files and does not edit tracked legacy source. Python cache
files are covered by the repository's existing `.gitignore`. Every new file was
also checked individually with `git diff --no-index --check`.

## Generated schema SHA-256

```text
510a5a8e2027ee1e0420b93e9982b5a16f98a6ca203ea032829810f77d5b448c  MotionCertificate.schema.json
2fb0c6d034c58f83d154016861feeaa3799c64df76023ecb2436694b98076c71  RigidDesignSpec.schema.json
364978b19445b9b391233493be4a5f6b00fbc588c10ab949368469dcd59e3c38  RigidMechanismGraph.schema.json
ad32c0d366f7f5809d159b040093eea9c185dcbf59bab643bd6c88d18de311b1  RigidProjectRecord.schema.json
```

These hashes identify the generated schema files, not semantic artifact
hashes. Artifact hashing remains blocked on an explicit RFC 8785 canonical-JSON
implementation decision.

## Pinned numerical and geometry policy

- Reference geometry: XY plane at `z = 0`, outer face loops CCW from `+z`, hole
  loops CW.
- Internal units: millimeters and radians; FOLD serialization: degrees.
- Fold sign: positive valley, negative mountain, zero unassigned.
- Hinge orientation: start-to-end edge with geometric left face fixed; the right
  face rotates by `-rho` around the oriented axis.
- Primitive and rotation fixture tolerance: `1e-12` absolute.
- Developability/sector-sum tolerance: `1e-10 rad`.
- Certificate default closure tolerance fixture: `1e-9 rad`.
- Rank threshold: `max(1e-10, 1e-8 * largest_singular_value)` after the recorded
  characteristic-length normalization.

## Known limitations

- No degree-4 analytic equation, closure solver, Jacobian, continuation,
  collision backend, trajectory, FOLD exporter, Miura generator, MCP endpoint,
  or UI was implemented in this slice.
- Pydantic validates parsed values. A later API boundary must reject duplicate
  raw JSON object keys before parsing.
- Draft 2020-12 exports carry field-level structure and bounds; cross-reference,
  geometric, and certificate-status invariants still require the authoritative
  Pydantic validation layer.
- `sha256:<hex>` references are syntactically checked, but semantic artifact
  hashing awaits the RFC 8785 decision.
- Version 0.1 hinge side frames are deliberately aligned with reference XY;
  arbitrary face-local frames require a later schema version.
- Collision evidence is representable and truth-constrained, but no collision
  engine is selected. `not_run` remains distinct from pass.
- Numerical certificates support only the claim “verified under the recorded
  model and tolerances”; Phase 0 makes no rigid-foldability claim.

## Next gate

Execute these tasks in order:

1. **R1 — notation audit:** map the Foschi/Hull/Ku diagram's crease order,
   sector order, mode aliases, fold sign, driver direction, and square-root
   branches into repository conventions.
2. **R2 — independent oracle fixtures:** evaluate the reserved generic and
   published degree-4 cases with a separate high-precision implementation and
   record provenance.
3. **R3 — closure kernel:** implement pinned-order `SO(3)` rotation-product
   closure, log-map residuals with a near-pi guard, and analytic/numerical
   cross-checks.
4. **R4 — singularity diagnostics:** compute rank evidence, explicitly classify
   the flat singular state, and trace one branch away from a non-flat seed.

Do not begin Miura generation, MCP wiring, collision, or frontend work until
R1–R4 pass their fixture and regression gates.

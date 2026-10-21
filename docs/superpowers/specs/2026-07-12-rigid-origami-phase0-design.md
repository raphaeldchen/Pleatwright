# Rigid origami Phase 0: contract-and-convention kernel

**Status:** Implementable specification for the first rigid-origami slice
**Date:** 2026-07-12
**Branch:** `codex/rigid-origami-phase-0`
**Master plan:** `docs/rigid-origami-ide-plan.md`

## 1. Mission

Establish the smallest trustworthy boundary for a rigid-origami compiler without
changing the legacy TreeMaker product path. This slice freezes the source/IR/
evidence contracts, units, orientation, fold-angle, branch, FOLD, numerical, and
licensing conventions. It implements only the contract models and the exact
rotation/hinge primitives needed to test those conventions.

This slice deliberately does **not** implement a degree-4 analytic solver. The
published equations are the next mathematical step, but their crease numbering,
sector ordering, fold sign, mode labels, and square-root branches must first be
mapped diagram-by-diagram into the repository convention. Squared half-angle
equations combine modes and can admit the wrong root if transcribed without that
audit.

The acceptance claim for this slice is therefore:

> The repository has a versioned, strict, testable rigid-origami contract and an
> exact hinge convention on which the degree-4 oracle can safely be built.

It is not yet a rigid-foldability claim.

## 2. Research conclusions that change the master plan

### 2.1 Product wording

Numerical continuation and collision analysis provide evidence under a recorded
model, algorithm, tolerance, and path representation. The product must say
"numerically verified under the recorded model and tolerances" unless a later
formal or conservative method supports a stronger statement. The existing
phrases "mathematically perfect" and "proof" are product aspirations, not labels
for an ordinary floating-point result.

### 2.2 FOLD is an interchange profile

FOLD 1.2 is the external static-state interchange format. It does not become the
canonical project record because multiple-frame support is optional and the
format does not define continuous-time interpolation, branch identity, closure
residuals, solver provenance, or collision certificates.

### 2.3 Collision claims have strength

The collision stage must eventually distinguish:

- `sampled_discrete`: only the stored states were tested;
- `piecewise_linear_ccd`: straight interpolation between stored geometry states
  was tested;
- `conservative_nonlinear_ccd`: the actual bounded nonlinear trajectory model
  was conservatively tested.

Only the last can support an interval-wide collision-free claim, and only for the
verified intervals and contact policy. IPC Toolkit is the leading Phase-5 spike;
FCL/python-fcl is a useful discrete/distance cross-check. Neither is a dependency
of this Phase-0 slice.

### 2.4 Degree-4 equations require a notation gate

Foschi, Hull, and Ku provide the analytic oracle for the general degree-4 vertex,
but their mode names are not invariant under cyclic relabeling or reflection.
Before implementing the half-angle equations, a fixture note must draw or tabulate
the exact mapping among paper `e_i`/`alpha_i`, repository crease IDs, positive
valley, driver crease, and the selected square-root branch.

## 3. Compiler ownership and authority

The repository contains two sibling compiler domains. They share FOLD only at an
interchange boundary.

| Domain | AI-editable source | Deterministic compiler | Authoritative result |
|---|---|---|---|
| Artistic tree method | `MetricTree` | TreeMaker C++ | TreeMaker FOLD plus flat-endpoint lint evidence |
| Rigid mechanism families | `RigidDesignSpec` | New rigid package | `RigidMechanismGraph`, trajectory, and `MotionCertificate` |

There is no version-1 conversion between `MetricTree` and `RigidDesignSpec`, and
neither source may patch the other's compiler output. This resolves the apparent
conflict in the repository blueprint: "only the Metric Tree is AI editable"
continues to govern the TreeMaker domain; "only RigidDesignSpec is AI editable"
governs the rigid domain.

Authority is layered:

1. `RigidDesignSpec` records bounded semantic intent.
2. A family generator creates `RigidMechanismGraph` deterministically.
3. Local analysis identifies admissible vertex branches.
4. Global analysis traces a finite compatible path and reports rank/closure
   evidence.
5. Collision analysis adds a separate, explicitly scoped result.
6. Optional flat-endpoint lint/layer analysis adds another separate result.
7. `RigidProjectRecord` binds versions, hashes, events, artifacts, and evidence.

No later layer upgrades an earlier failure, and a skipped layer is `not_run`, not
an implied pass.

## 4. Repository map and isolation boundary

Current callers are:

```text
web/server.py
  -> mcp_harness/agent_loop.py
       -> mcp_harness/server.py          (MetricTree / TreeMaker)
       -> mcp_harness/linter_server.py   (Oriedita flat-endpoint lint)
  -> FOLD frames
       -> CreasePanel / CADViewer / Origami Simulator
```

Relevant reuse boundaries:

- `agent_loop.py` has reusable MCP discovery/routing, but its `_SERVERS` and
  `SYSTEM_PROMPT` are TreeMaker-specific. This slice does not edit it.
- `server.py` demonstrates spawned-process isolation but contains TreeMaker
  state and tools. This slice does not add rigid tools there.
- `linter_server.py` removes `edges_foldAngle`, `faces_vertices`, and ordering
  arrays when it reindexes a lint copy. It must never normalize the canonical
  rigid artifact.
- `flat_fold.py` has useful planar face walking, but computes a reflected flat
  endpoint rather than a continuous 3D rigid path.
- `layer_order.py` remains a flat-endpoint-only consumer.
- `pose_search.py` may later inform bounded family optimization, not kinematic
  authority.
- `CADViewer.tsx` uses a visual `THICKNESS = 0.01`; that is not a thick-origami
  mechanism.
- Origami Simulator remains an approximate comparison viewer. Its compliant
  dynamics are not certificate evidence.

The new package starts at `mcp_harness/rigid/`. Tests live under
`mcp_harness/tests/test_rigid_*.py`, because the current `make test` gate only
discovers `mcp_harness/tests/`.

## 5. Versioned contracts

Pydantic v2 is the contract source of truth. Every contract model uses:

```python
ConfigDict(
    strict=True,
    extra="forbid",
    allow_inf_nan=False,
    validate_default=True,
    frozen=True,
    revalidate_instances="always",
)
```

Nested collections are tuples so the artifact is not mutable through a frozen
outer model. Every top-level schema has a literal `schema_version = "0.1.0"`.
Generated JSON Schemas use Draft 2020-12, carry stable `$id` values, are committed,
and are checked with the independent `jsonschema` implementation.

The API boundary must later reject duplicate JSON object keys before Pydantic
validation. This slice reserves and validates `sha256:<64 lowercase hex>`
references but does not implement semantic hashes. The later Phase-2 audit
supersedes the provisional RFC 8785 direction with the explicitly non-JCS,
golden-tested project profile `ro-cjson-1`; see
`docs/rigid-origami-phase2-topology-fold-audit.md`.

### 5.1 `RigidDesignSpec`

This is the only rigid representation an AI or typed design UI may edit.

- It is a discriminated union keyed by `family`; parameters are never an open
  `dict[str, Any]`.
- Initial family variants are `degree4_vertex` for diagnostic fixtures and
  `miura` for the first product generator.
- Degree-4 input is sector angles and a semantic crease selector, never raw
  coordinates.
- Miura input is repetition counts, two edge lengths, and a sector angle with
  explicit units.
- A signed target fold angle replaces a redundant direction Boolean. Positive is
  valley and negative is mountain.
- Constraints and objectives use a closed vocabulary and bounded values.
- Fabrication is fixed to `null` in this zero-thickness slice.
- Prompt/provenance metadata is retained but excluded from a future geometry
  content hash.
- Unknown fields, stringified numbers, NaN/Infinity, invalid bounds, duplicate
  objectives, mismatched family parameters, and raw crease-coordinate fields
  fail validation.

### 5.2 `RigidMechanismGraph`

This deterministic compiler IR is not AI-editable. Version 0.1 represents:

- stable sheet, vertex, face, edge, and hinge IDs;
- millimeter reference coordinates;
- counterclockwise outer loops and clockwise hole loops viewed from `+z`;
- edge roles `hinge | boundary | cut_boundary | join | construction`;
- explicitly oriented hinge endpoints and left/right incident faces;
- per-face local hinge axes (the 0.1 face-local basis is aligned with the
  reference XY frame; arbitrary face frames require a later schema version);
- signed radian angle bounds;
- driver/fixed-face annotations;
- ordered vertex sectors and a deterministic independent-cycle list when known;
- generator name/version and design-spec content hash.

Graph validation checks unique IDs, existing references, non-repeated edge
endpoints, valid loops, role/incident-face cardinality, unit hinge axes, hinge-edge
role agreement, and a real fixed face. Full manifold/cut/hole validation remains
Phase 1, but the schema cannot silently accept dangling references.

### 5.3 `MotionCertificate`

The overall status is `pass | fail | inconclusive`. Evidence stages have
`pass | fail | not_run | inconclusive` and include topology, local kinematics,
global kinematics, collision, and optional flat endpoint.

The certificate records which stages were requested. Its invariants are:

- `pass` means every requested stage passed;
- `fail` means at least one requested stage failed;
- otherwise the result is `inconclusive`;
- an unrequested or unavailable collision stage remains `not_run` with
  `collision_free = null` and `minimum_clearance_mm = null`;
- a kinematics-only certificate may pass its requested scope without making a
  collision statement;
- a collision pass requires a collision scope, backend/version, checked
  intervals, contact policy, and nonnegative minimum clearance.

Rank evidence uses unambiguous names:

- `minimum_retained_singular_value`: smallest singular value classified nonzero;
- `maximum_null_singular_value`: largest singular value classified zero;
- `maximum_effective_condition_number`: condition number on the retained
  constrained subspace;
- `rank_absolute_tolerance` and `rank_relative_tolerance`: the exact policy used.

The certificate also stores the variable count, characteristic-length
normalization, and the nonincreasing singular-value sequence for every reported
trajectory sample. Nullity, singular sample indices, retained/null extrema, and
the effective condition number must be recomputable from those values.

At the unfolded degree-4 singular state, first-order nullity can be two even
though either finite branch is one-dimensional. The certificate must report the
state as singular/inconclusive for finite DOF rather than claiming two mechanism
DOFs.

### 5.4 `RigidProjectRecord`

The project record binds immutable spec revisions, typed domain events, artifact
references/hashes, mechanism and trajectory hashes, FOLD exports, certificates,
approvals, and later fabrication/experiment records. A new revision is created
instead of mutating an accepted spec in place.

Raw RFC 6902 patches are not the public editing protocol. Later editing tools use
typed events such as `set_family_parameter`, `set_driver`, and
`set_constraint`, then revalidate the complete candidate spec.

## 6. Geometry and fold conventions

### 6.1 Reference frame and units

- Reference sheet: XY plane, `z = 0`.
- Length: millimeters in the IR and project record.
- Internal angles: radians.
- FOLD `edges_foldAngle`: degrees at the serialization boundary.
- Vectors are column vectors; transforms act actively.
- Rotation matrices are right-handed and belong to `SO(3)` within tolerance.
- Faces wind counterclockwise when viewed from `+z`, so the reference normal is
  `+z`.

### 6.2 Hinge orientation and fold sign

Every hinge stores an oriented edge `start -> end`. In the unfolded XY reference
state, the incident face on the geometric left of that direction is `left_face`;
the other is `right_face`.

The canonical fold angle `rho` matches FOLD:

- `rho > 0`: valley;
- `rho < 0`: mountain;
- `rho = 0`: flat/unassigned;
- valid ideal range: `[-pi, pi]`.

When the left face is fixed, the relative pose of the right face uses a
right-handed rotation of `-rho` about the oriented hinge axis. Reversing the edge
and swapping left/right is physically invariant and will be a property test.

The first exact fixtures are:

1. `R_x(pi/2) @ [0, 1, 0] == [0, 0, 1]`.
2. For a hinge from `(0,0,0)` to `(1,0,0)`, left face at `y > 0`, and
   `rho = +pi/2`, the right-face point `(0,-1,0)` maps to `(0,0,1)`.
3. Radians/degrees and M/V conversion round-trip at `0`, `+/-pi/2`, and
   `+/-pi`.

### 6.3 Vertex ordering and branches

Creases `e0..e(n-1)` are counterclockwise in the XY reference plane.
`alpha_i` is the positive sector from `e_i` to `e_(i+1)`. A generic planar
degree-4 fixture requires `0 < alpha_i < pi` and `sum(alpha_i) = 2*pi`; collinear
and other special vertices use explicit fixture classes rather than the generic
formula path.

A branch identity contains:

- ordered crease IDs and sector angles;
- selected analytic mode signature;
- driver crease ID;
- driver sign/travel direction;
- a normalized tangent/sign signature at a small non-flat seed.

`mode-1`/`mode-2` may be retained only as source-specific aliases. They are not
the durable identifier.

### 6.4 Closure residuals (next slice contract)

For one concurrent vertex, `SO(3)` rotation-product closure is sufficient when
the multiplication order is pinned by face-pose fixtures. The solve residual is
the three-component rotation vector/logarithm of the closure error. Frobenius
`||R-I||`, orthogonality, and determinant are diagnostics. The log map needs a
documented near-`pi` guard.

General panel cycles, holes, cuts, offset hinges, and thick mechanisms use
`SE(3)` closure; orientation-only closure can hide a translational gap.

## 7. Numerical policy version 0.1

- Precision: IEEE-754 `float64`.
- Normalize lengths by a recorded characteristic length before solving; report
  physical residuals after rescaling.
- Exact/convention fixture absolute comparison: `1e-12`.
- Developability tolerance: `1e-10 rad` after ordered-sector summation.
- Rotation orthogonality and determinant tolerance: `1e-12` for primitive tests.
- Global closure target (future continuation default): `1e-9 rad` rotation-vector
  norm, always stored in the certificate.
- Rank policy (future default): classify `s_i` as nonzero when
  `s_i > max(1e-10, 1e-8 * s_max)` after nondimensionalization; store singular
  values and both thresholds so the verdict can be recomputed.
- NaN and Infinity are always contract failures.
- Every tolerance is centralized and versioned; fixture-specific overrides are
  explicit metadata, never scattered literals.

These are initial engineering tolerances, not physical accuracy claims. Phase 3
must calibrate them against scale/property tests before certification wording is
enabled.

## 8. Rigid FOLD Profile 0.1

- Emit FOLD 1.2 static states by default with `frame_unit: "mm"`.
- Preserve the FOLD sign/range for `edges_foldAngle`: degrees,
  `+V / -M`, `[-180, 180]`.
- Default cut export expands each internal cut into coincident `B` boundary
  edges, one per incident face. Collapsed `C` output is opt-in because support is
  optional among consumers.
- `J` edges are nonmechanical subdivisions/triangulation. They never become
  hinges or collision exclusions merely because they are edges.
- Panels with holes remain explicit in the IR. FOLD export may subdivide them and
  uses `faces_ro:panelId` to preserve the effective panel.
- Custom fields use the `ro:` namespace, including array forms such as
  `edges_ro:hingeId`.
- Optional `file_frames` animation is a sampled convenience export. Canonical
  trajectory/certificate data remains a sidecar referenced by a content hash.
- Import validates parallel-array lengths, index ranges, incidence, face winding,
  assignment/fold-angle consistency, units, and cut/join policy; JSON shape alone
  is insufficient.

## 9. Fixture and dependency provenance

No figure, mesh, source code, or TeX is copied from research software. Mathematics
is independently implemented from primary publications, and golden numeric values
must come from an independent high-precision evaluator rather than the code under
test.

Every fixture entry records source/DOI, equation or figure, paper notation,
repository notation, valid interval, expected singular/binding points, whether
self-intersection is allowed, derivation method, generator hash, content/code
license, copied-byte status, and attribution.

Initial corpus:

- exact `R_x(pi/2)` and positive-valley hinge fixtures;
- generic flat-foldable sectors `(pi/3, pi/4, 2*pi/3, 3*pi/4)` reserved for the
  audited two-mode oracle;
- published general developable sectors
  `(pi/3, pi/2, 3*pi/4, 5*pi/12)` reserved until independently evaluated;
- special/collinear cross `(pi/3, 2*pi/3, pi/3, 2*pi/3)` routed away from generic
  equations;
- non-developable planar negative `(pi/3, pi/3, pi/3, pi/3)`;
- cyclic reindexing, reflection, reverse travel, and scale invariance variants.

Until the repository's product license is chosen, the dependency allowlist is
permissive-only and clean-room-by-default. GPL, noncommercial, no-license, and
unclear-license code is reference-only. This does not settle the repository's
eventual license; it prevents an early choice from contaminating that decision.

## 10. First implementation slice

### In scope

- Phase-0 ADR, scope, conventions/FOLD profile, dependency/license manifest,
  fixture manifest, and baseline note.
- Strict Pydantic 0.1 contracts for all four top-level artifacts.
- Committed Draft 2020-12 schemas and independent schema validation tests.
- Central angle/unit/MV conversion helpers.
- Right-handed axis-angle rotation and the exact positive-valley hinge transform.
- Tests under the existing `make test` discovery gate.

### Out of scope

- Degree-4 half-angle equations or bird's-foot verdicts.
- Topology extraction/refactoring from `flat_fold.py`.
- Global closure, Jacobians, continuation, collision, Miura, flashers, MCP tools,
  agent prompts, web frames, frontend components, fabrication, thickness, or
  learned feasibility.
- Any edits to the legacy TreeMaker, linter normalization, active simulator, or
  current UI.

### Acceptance

- All pre-existing test surfaces retain their recorded baseline.
- Every contract rejects extra fields, coercive string numbers, and non-finite
  values.
- `RigidDesignSpec` rejects raw crease-coordinate fields and mismatched family
  parameters.
- Graph references and IDs receive basic cross-validation.
- A certificate can truthfully encode kinematics checked/collision not run, and
  cannot encode collision pass without collision evidence.
- Generated JSON Schemas validate with Draft 2020-12.
- Exact rotation, hinge-sign, conversion, edge-reversal, and face-winding tests
  pin the convention.
- No legacy source file changes.

## 11. Deferred decisions

The following do not block this slice:

- proprietary versus permissive-open-source versus GPL-compatible product;
- final collision backend after the IPC/FCL spike;
- automatic differentiation stack;
- general cuts outside named families;
- multiple sheets/joints;
- first thickening method and material workflow.

They become blocking before their associated dependency or product feature is
merged.

## 12. Primary references

- [FOLD specification 1.2](https://edemaine.github.io/fold/doc/spec.html)
- [He and Guest, On Rigid Origami I](https://arxiv.org/abs/1803.01430)
- [Belcastro and Hull, A Mathematical Model for Non-Flat Origami](https://doi.org/10.1016/S0024-3795(01)00608-5)
- [Foschi, Hull, and Ku, Explicit Kinematic Equations for Degree-4 Rigid Origami Vertices](https://doi.org/10.1103/PhysRevE.106.055001)
- [Abel et al., Rigid Origami Vertices: Conditions and Forcing Sets](https://doi.org/10.20382/jocg.v7i1a9)
- [Tachi, Simulation of Rigid Origami](https://origami.c.u-tokyo.ac.jp/~tachi/cg/SimulationOfRigidOrigami_tachi_4OSME.pdf)
- [Pydantic strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/),
  [configuration](https://docs.pydantic.dev/latest/api/config/), and
  [JSON Schema generation](https://docs.pydantic.dev/latest/concepts/json_schema/)
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12)
- [RFC 8785 JSON Canonicalization Scheme](https://www.rfc-editor.org/info/rfc8785/)
- [IPC Toolkit nonlinear CCD](https://ipctk.xyz/tutorials/nonlinear_ccd.html)
- [Flexible Collision Library](https://github.com/flexible-collision-library/fcl)

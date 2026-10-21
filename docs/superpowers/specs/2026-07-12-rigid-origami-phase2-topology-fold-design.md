# Rigid origami Phase 2: deterministic topology-to-artifact pipeline

**Status:** Implementable specification
**Date:** 2026-07-12
**Branch:** `codex/rigid-origami-phase-2-topology-fold`
**Hard gate:** `docs/rigid-origami-phase2-topology-fold-audit.md`

## Mission

Compile a validated `Degree4VertexDesignSpec` through one complete offline,
deterministic vertical slice:

```text
normalized RigidDesignSpec
  -> finite degree-4 RigidMechanismGraph
  -> validated TopologyView
  -> exact Phase-1 branch resolution and sampled fold vectors
  -> reference-to-folded face poses
  -> reference and folded static FOLD 1.2 frames
  -> trajectory manifest and MotionCertificate
  -> content-addressed bundle
  -> independent disk verification
```

The public schemas remain at 0.1.0. New topology, pose, FOLD, trajectory, and
bundle types are immutable implementation-layer contracts.

## Module boundaries

### `rigid.canonical`

Owns strict JSON parsing, `ro-cjson-1`, artifact byte rendering, SHA-256, and
profile runtime vectors. It knows no origami mathematics, artifact-specific
array semantics, or filesystem paths.

Public behavior:

```python
strict_json_loads(data: str | bytes) -> JSONValue
canonical_json_bytes(value: JSONValue) -> bytes
content_hash(value: JSONValue) -> str
content_hash_bytes(data: bytes) -> str
```

Artifact-specific producers and normalizers are named and versioned in their
own modules; the generic serializer never guesses which arrays are semantic
sets or reorders them.

### `rigid.patterns.degree4`

Owns only the finite equal-radius diagnostic construction, stable entity IDs,
fixed scale, fixed face, ordered sectors, and generator provenance.

```python
compile_degree4_pattern(
    spec: Degree4VertexDesignSpec,
    *,
    design_spec_hash: str,
) -> RigidMechanismGraph
```

The production radius is exactly `100.0 mm`. A private positive scale parameter
may be used only by metamorphic tests.

### `rigid.topology`

Owns raw structured preflight and typed topology materialization:

```python
preflight_topology(payload: Mapping[str, object]) -> TopologyValidation
build_topology(graph: RigidMechanismGraph) -> TopologyView
```

`TopologyView` contains stable-ID maps, oriented half-edges, twins, face loops,
vertex stars, boundary loops, face adjacency, components, hinge incidence,
ordered sectors, lexicographic Kruskal tree edges, and directed fundamental
cycles. Diagnostics are ordered by `(code, entity_kind, entity_id, related_ids)`.

### `rigid.kinematics.face_poses`

Owns deterministic `SE(3)` propagation from authoritative fold angles:

```python
propagate_face_poses(
    graph: RigidMechanismGraph,
    topology: TopologyView,
    fold_angles_by_hinge: Mapping[str, float],
    *,
    spanning_tree_hinge_ids: tuple[str, ...] | None = None,
) -> FacePoseSample
```

`FacePoseSample` stores row-major reference-to-folded matrices ordered by face
ID, omitted-cycle rotation/normalized-translation residuals, maximum isometry,
shared-vertex, shared-hinge endpoint, and world-axis errors. It validates every
pose as `SE(3)`.

### `rigid.fold_io`

Owns only the audited static FOLD 1.2 profile:

```python
export_reference_frame(graph, metadata) -> dict[str, JSONValue]
export_folded_frame(graph, pose_sample, fold_angles, metadata) -> dict[str, JSONValue]
import_static_frame(data: str | bytes | Mapping[str, object]) -> NormalizedFoldFrame
normalize_static_frame(frame) -> dict[str, JSONValue]
```

Import is all-or-nothing, returns structured stable FOLD diagnostic codes, and
never repairs topology. Export never mutates the graph or sample.

### `rigid.compiler`

Owns branch-key derivation/resolution, deterministic sampling, manifest and
certificate assembly, failure-safe publication, verification, and inspection.

```python
degree4_branch_key(branch: Degree4Branch) -> str
compile_degree4(spec, *, samples: int = 9, traversal: Literal["forward", "reverse"] = "forward") -> CompiledBundle
write_bundle(spec_path: Path, output: Path, *, samples: int = 9, traversal: Literal["forward", "reverse"] = "forward") -> BundleSummary
verify_bundle(path: Path) -> VerificationReport
inspect_bundle(path: Path) -> BundleInspection
```

The compiler depends on public Phase-1 interfaces. It never reimplements the
degree-4 analytic formulas.

### `rigid.validation.bundle`

Owns safe relative-manifest-path checks, special-file rejection, exact disk
reads, hash/link validation, and independent evidence replay. It deliberately
does not call the production topology builder, pose propagator, or FOLD writer.

### `rigid.cli`

A thin `argparse` adapter. From the repository root the honest offline commands
are:

```text
PYTHONPATH=mcp_harness python -m rigid.cli compile-degree4 spec.json --output out/
PYTHONPATH=mcp_harness python -m rigid.cli compile-degree4 spec.json --output out-reverse/ --reverse
PYTHONPATH=mcp_harness python -m rigid.cli verify out/
PYTHONPATH=mcp_harness python -m rigid.cli inspect out/
```

No shared packaging, MCP, network, browser, simulator, TreeMaker, Oriedita, or
frontend edit is required.

## Source normalization and compiler preconditions

The input JSON is parsed with duplicate-key/nonfinite rejection and validated as
`RigidDesignSpec`. The Phase-2 compiler requires:

- family `degree4_vertex` and purpose `diagnostic`;
- a generic developable/noncollinear sector tuple;
- exactly one `degree4_crease` driver;
- an explicit branch request;
- no required collision-free claim;
- no required flat endpoint for a passing compile; and
- no maximum-stowed-width or minimum-deployed-width constraint;
- no optimization objectives; and
- no unsupported fabrication payload.

The normalized design artifact is the full schema-valid model dump rendered as
`ro-cjson-1`; provenance is included in the design content hash.

Branch resolution enumerates Phase-1 branches for the exact sector tuple and
driver, computes `d4b:<sha256(phase1_branch_id)>` for each, and requires exactly
one match. Available keys may be returned in an error diagnostic, but the
compiler never substitutes one.

## Topology behavior

The generated mechanism follows the audit exactly. `build_topology` must prove:

- every face segment maps to exactly one edge record;
- every internal half-edge has one oppositely oriented twin;
- boundary half-edges form one CCW loop;
- every edge has role-consistent incidence;
- the sheet and dual graphs are connected;
- the central star orders `e0,e1,e2,e3` CCW and reproduces the supplied sectors;
- hinge left/right sides and local axes agree with geometry;
- fixed `f3` exists; and
- Kruskal tree/fundamental cycle records agree with graph rank.

Raw adversarial payloads receive structured diagnostics for missing/duplicate
entities, repeated/geometrically zero edges, loop self-intersection, winding,
incidence, nonmanifold edges, disconnected components, holes/cuts, hinge sides,
axes, boundary coverage, fixed face, sectors, and cycles.

The trajectory serializes that preflight as `topology_report`, with exact keys
`profile`, `valid`, `entities_checked`, and `diagnostics`. The profile is
`rigid-topology-report-v1`. A publishable bundle records `valid=true`, the exact
sheet/vertex/face/edge/hinge/sector/cycle/half-edge count, and no diagnostics;
the independent disk verifier recomputes those facts without calling the
production topology builder.

## Trajectory behavior

For a nonzero target, require `branch.driver_sign == sign(target)`. Forward
traversal samples `t_i=(i+1)/N`; reverse traversal samples `t_i=(N-i)/N`, so it
replays the same non-flat endpoints in reverse order without crossing the flat
singularity. `N` is an exact integer in `[1,10000]` and defaults to 9. The
sample closest to flat must remain at or above the Phase-1 minimum nonzero
guard. Evaluation uses `evaluate_degree4` for every sample and retains:

- `t`, signed driver radians, and all four fold radians;
- the exact branch key and Phase-1 branch signature/provenance;
- Phase-1 closure vector/norm and rank diagnostics;
- face pose matrices and all geometric/cycle error maxima; and
- the corresponding static FOLD path/hash.

Forward and reversed traversal over the same non-flat endpoints must produce the
same samples in reverse order within tolerance. Positive and negative travel on
one branch must obey the Phase-1 odd fold relation and the face-pose mirror
relation.

Exact zero is a singular diagnostic sample with rank 2/nullity 2 and an
inconclusive certificate. Tiny nonzero, a path that crosses zero, exact binding,
and outside-interval targets fail. The compiler never wraps an angle through
`+/-pi`, changes roots, or crosses the shared flat singularity.

## Face-pose and global-evidence behavior

Every sample starts from fixed `f3 = I`. Crossing a tree hinge applies the
audited right-multiplied relative transform. For the canonical tree, omitted
`e3` yields the exact Phase-1 product. Acceptance requires:

- every rotation is orthogonal with determinant `+1` and every homogeneous
  bottom row is exact within primitive tolerance;
- every pairwise reference face distance is preserved;
- every shared vertex image agrees across all incident faces;
- both hinge endpoints and world axis direction agree across incident faces;
- omitted-cycle rotational residual is within `CLOSURE_ATOL_RADIANS`;
- normalized translational and direct positional errors are within centralized
  geometric tolerances; and
- all four ring spanning-tree choices produce equivalent poses.

New positional tolerances, if required, live in `rigid.conventions`, are named by
quantity, are normalized by the `100.0 mm` characteristic length where
appropriate, and have boundary tests. Phase-1 rotational/rank tolerances remain
unchanged.

## FOLD profile behavior

Exports contain every standard/custom key frozen by the audit. Arrays are
stable-ID normalized and index-aligned. Reference vertices are 2D; folded sample
vertices are explicit 3D. Folds convert radians to degrees only in `fold_io`.

The writer maps `B`, `M`, `V`, and `U` exactly as audited. The exact Phase-2
degree-4 profile has no construction edges and rejects `J`; adding them requires
a future profile version. It emits no multi-frame, ordering, collision,
self-contact, cut, or unsupported metadata.

Strict import:

1. rejects duplicate/nonfinite JSON;
2. validates the exact allowed key set, FOLD 1.2, classes, attributes, and `mm`;
3. validates all parallel arrays, indices, dimensions, assignments, degrees,
   incidence, winding, manifold connectivity, IDs, roles, and hashes;
4. normalizes vertices/edges/faces by stable IDs and remaps every aligned array;
5. canonicalizes oriented edges and face-loop start positions without reversing
   material winding; and
6. reproduces identical normalized canonical bytes for compiler exports.

Unsupported FOLD features return a stable diagnostic. Third-party FOLD without
the required `ro` stable IDs is not a semantic mechanism import. A separate
standards-only fixture demonstrates that ordinary consumers can ignore custom
metadata; it is not accepted by the semantic importer.

## Canonicalization and provenance behavior

`ro-cjson-1` implements every rule in the audit and runs its byte/hash vectors
before compilation. The committed vectors include:

```text
general branch 0:
  d4b:a694254a3c05cbfa31627a46260aecfe8a6c86479acebf742ad2349dbf8d1ec2
general branch 1:
  d4b:44e1f008ac2f52722b3bda201007eb73c41d500a202787e38b113fbd3093fa12
basic object hash:
  sha256:e28bc0ae0e8a179538a945ec44933b788c114c78a575865cb60374104bb30c5f
Unicode code-point sort discriminator:
  sha256:daec79d8b6582badd3b46bd783a72379bc0b5ae29f5d59f6133025aad69bc8d4
float boundary vector:
  sha256:a59a0ab645a72004f75d8282bac1823bfed8283d881fcf38f35cedcc73ba683e
NFC/NFD preservation vector:
  sha256:a7962fb10dc1255be368ece9c22b2256605921dc6d0a8c9409d3ee406bcb86e5
```

Verification rejects altered bytes, whitespace/newline/BOM, duplicate escaped
keys, invalid UTF-8, truncation, missing/extra/renamed files, hash/link swaps,
unsafe/symlink paths, and refreshed hashes with false mathematical evidence.

## Bundle format

Canonical filenames are:

```text
design.json
mechanism.json
reference.fold
frames/sample-0000.fold ...
trajectory.json
certificate.json
bundle.json
```

`bundle.json` contains profile and canonical-profile identifiers plus ordered
artifact paths, kinds, media types, and hashes. Stable entity IDs live in the
linked mechanism/FOLD/trajectory artifacts and are intentionally not duplicated
in the index. The index does not contain its own hash. The externally computed
bundle hash addresses the canonical index bytes.

Compilation writes a private sibling temporary directory, validates and verifies
the complete candidate, then atomically publishes without replacement through
macOS `renamex_np(RENAME_EXCL)` or Linux
`renameat2(RENAME_NOREPLACE)`. It fails closed with an unsupported-operation
error on platforms without either primitive. On error it removes the candidate
and leaves no passing partial output. If the destination already contains
byte-identical artifacts, rerun succeeds read-only; a different existing bundle
is never overwritten.

Paths in the manifest are normalized relative POSIX paths. Absolute paths,
`..`, symlinks, duplicate paths, and paths outside the bundle root are rejected.

## Certificate assembly

For an accepted non-flat trajectory:

- topology is `pass`, with entity count and no errors;
- local kinematics is `pass`, with one branch key and maximum Phase-1 closure;
- global kinematics is `pass`, with all sample singular values, variable count
  4, expected DOF 1, nullity extrema, conditioning extrema, sample count,
  characteristic length, and the maximum of Phase-1/cycle rotation residuals;
- collision and flat endpoint remain `not_run`; and
- warnings state that the singular flat endpoint was excluded and collision,
  layer order, thickness, and physical realization were not evaluated; and
- when any accepted sample is within the inclusive `1e-5 rad` binding-proximity
  band, an additional warning names the tangent-half-angle binding endpoint.

The trajectory retains positional evidence absent from schema 0.1. The
certificate ID is `cert:<sha256(mechanism_hash + "\n" + trajectory_hash)>`; the
full certificate content hash remains a separate bundle entry.

Exact flat produces `inconclusive` local/global stages and overall status. A
schema constraint or request must never be worked around to fabricate pass.

## Independent disk verification

`verify_bundle` must not call the production pattern generator, face-pose
propagator, or FOLD writer to manufacture expected output. From serialized
artifacts it independently:

- checks exact canonical bytes and every hash/link;
- schema-validates design, mechanism, and certificate;
- reconstructs incidence and topology invariants;
- re-enumerates/resolves the Phase-1 branch and recomputes every fold vector,
  closure residual, Jacobian rank, and certificate extremum;
- directly applies serialized pose matrices to reference vertices and checks
  `SE(3)`, isometry, shared vertices, hinge endpoints/axes, FOLD coordinates, and
  omitted-cycle consistency; and
- compares the recomputed evidence with both trajectory and certificate.

The verification root provides corruption detection, not signature-based
authentication.

## Independent fixtures

Before production modules, commit a standalone fixture generator that imports no
production topology, face-pose, FOLD, canonicalization, or compiler module. It
uses the committed high-precision Phase-1 oracle fold vectors and a separately
implemented Rodrigues/homogeneous chain to emit hand-auditable geometry and pose
anchors for both generic sector fixtures, both branches, both travel signs, and
multiple magnitudes.

Also commit:

- exact finite reference-geometry anchors;
- the composition-order/simple-hinge anchor;
- shared-hinge/isometry/cycle values;
- the `ro-cjson-1` byte/hash vectors;
- a standards-only static FOLD fixture containing no `ro` keys; and
- provenance, generator hash, copied-byte status, versions, and tolerances.

## TDD order

Each numbered behavior is a red-green-refactor slice, never a batch of tests
followed by a batch of implementation:

1. canonical byte vector -> minimal serializer;
2. strict JSON rejection -> parser guards;
3. first finite pattern anchor -> degree-4 generator;
4. first topology view -> half-edge/twin/loop builder;
5. one adversarial topology diagnostic at a time -> validator;
6. simple hinge pose anchor -> relative crossing;
7. one oracle pose anchor -> canonical tree propagation;
8. omitted cycle/alternative trees -> global pose evidence;
9. reference FOLD anchor -> writer;
10. folded sign/unit anchor -> folded writer;
11. import/reindex round trip -> strict importer;
12. first branch trajectory -> compiler orchestration;
13. exact-flat/near-flat/binding failures -> honest classifications;
14. certificate summary -> evidence assembly;
15. disk corruption case by artifact class -> independent verifier;
16. CLI compile/verify/inspect and atomic/rerun behavior -> adapter/publication.

Tests use public interfaces and observable artifact behavior. Production tests do
not import private legacy `flat_fold`, `fold_mutate`, simulator, TreeMaker, or
Oriedita code.

## Acceptance gates

- P2: deterministic generated topology and structured adversarial validation.
- P3: face rigidity, shared hinges, alternative trees, exact Phase-1 cycle
  reconciliation, both branches/directions.
- P4: strict deterministic FOLD, units/signs, normalization, hashes, and
  corruption detection.
- P5: full bundle, recomputable certificate, offline CLI, atomic failure.
- P6: focused/full/backend/frontend/compileall/diff gates, independent
  adversarial review, current-main integration, outcome documentation, push, and
  ready pull request.

## Explicit non-goals

Arbitrary topology, multi-vertex continuation, pseudo-arclength continuation,
Miura, flashers, collision/CCD, layer order, thickness, mechanics, fabrication,
MCP, prompts, frontend integration, simulator verdicts, and product proof claims
remain outside Phase 2.

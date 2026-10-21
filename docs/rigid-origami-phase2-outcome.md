# Rigid-origami Phase 2 outcome: deterministic topology-to-artifact pipeline

**Status:** Accepted — gates P1–P6 pass
**Date:** 2026-07-15
**Branch:** codex/rigid-origami-phase-2-topology-fold
**Pushed branch:** origin/codex/rigid-origami-phase-2-topology-fold
**Phase-2 starting baseline:** 353d249
**Current-main integration baseline:** 32afbd4
**Post-merge integration commit:** 19d3af1
**Pull request:** [#43](https://github.com/raphaeldchen/origami-design-ide/pull/43) — ready

Phase 2 compiles one validated, branch-selected degree-4 diagnostic design into
a deterministic finite mechanism, independently checked face poses, static FOLD
frames, a recomputable motion certificate, and a content-addressed offline
bundle. The branch was developed only in the dedicated
AI-Driven-Origami-IDE-rigid worktree. Current origin/main at 32afbd4 was merged
without conflict before the final gates; the original worktree remained
tracked-clean and was not used for Phase-2 mutations.

## Accepted claim

For one generated, initially planar, concurrent, developable, noncollinear
degree-4 diagnostic sheet, an accepted non-flat branch trajectory:

- has deterministic manifold panel/hinge topology;
- uses fold vectors accepted by the Phase-1 analytic authority;
- propagates active reference-to-folded face transforms in SE(3);
- preserves face metrics and makes shared hinges coincident within the recorded
  tolerances;
- reconciles the omitted dual-cycle residual with the Phase-1 SO(3) residual;
- exports the audited static FOLD 1.2 subset; and
- carries hashes and certificate evidence independently recomputable from disk.

The claim is ideal_zero_thickness_kinematics. Collision, layer order, thickness,
elasticity, forces, stiffness, fabrication, and formal or global physical
realizability are not evaluated. Collision and flat-endpoint certificate stages
remain not_run.

## End-to-end artifact flow

    Degree4VertexDesignSpec
      -> normalized design.json
      -> equal-radius finite RigidMechanismGraph in mechanism.json
      -> validated half-edge and dual topology view
      -> exact durable Phase-1 branch resolution
      -> deterministic forward or reverse non-flat samples
      -> SE(3) face poses and global evidence
      -> reference.fold plus frames/sample-NNNN.fold
      -> trajectory.json
      -> schema-valid certificate.json
      -> ordered content-addressed bundle.json
      -> independent offline disk verification

The production diagnostic radius is exactly 100.0 mm. Four rays at the input
sector angles are joined by outer chords; no square boundary is assumed. The
result has 5 vertices, 8 edges, 4 triangular CCW faces, 4 hinges, 12 face
half-edges, one material component, one boundary loop, and one independent dual
cycle. The certificate reports 36 checked topology entities. Face face:f3 is
fixed. Lexicographic Kruskal selects hinges e0, e1, and e2; e3 is the omitted
cycle edge.

The schema-compatible branch key is d4b: followed by the full SHA-256 of the
exact Phase-1 branch text. Verification re-enumerates the Phase-1 branches and
requires an exact composite design-hash and branch-key match. It never chooses a
nearby root, wraps an angle, or crosses the shared flat singularity. Forward
sampling uses t=(i+1)/N; reverse traversal contains the same non-flat states in
reverse order. The public sample count is restricted to the exact integer range
1 through 10000.

## Convention mapping and invariants

- Rays e0 through e3 point outward and are counterclockwise in the reference
  plane; positive fold angle means valley.
- A stored face transform maps reference coordinates to folded coordinates and
  acts actively on column vectors. The fixed face transform is identity.
- With left face held, left-to-right crossing uses the audited negative semantic
  fold angle and is right-multiplied in reference coordinates.
- Hinge edges run from vertex:center to vertex:eN. edges_faces is ordered left,
  then right, relative to that orientation.
- Every pose is checked for SE(3), face isometry, shared-vertex and hinge-endpoint
  coincidence, world-axis agreement, omitted-cycle closure, and consistency
  under every ring spanning tree.
- Cyclic semantic relabeling, planar reflection, oriented hinge reversal with
  side swap, sign-reversed travel, traversal reversal, and uniform positive
  scale have explicit tested mappings rather than informal equivalence claims.

## Module and API boundaries

- rigid.canonical owns strict JSON parsing, ro-cjson-1 byte rendering, SHA-256,
  and runtime profile vectors. It knows no topology or filesystem paths.
- rigid.patterns.degree4 owns the finite 100 mm diagnostic construction, stable
  entity IDs, fixed face, ordered sectors, and generator provenance.
- rigid.topology owns raw structured preflight and immutable half-edge, boundary,
  incidence, dual-tree, and fundamental-cycle materialization.
- rigid.kinematics.face_poses owns deterministic SE(3) propagation from
  authoritative Phase-1 fold angles and complete positional evidence.
- rigid.fold_io owns only the audited static FOLD import/export profile.
- rigid.compiler owns branch resolution, trajectory sampling, manifests,
  certificate assembly, and failure-safe publication.
- rigid.validation.bundle owns safe disk reads, path and file-type rejection,
  hash/link checking, and separately structured evidence replay. It does not
  call the production topology builder, pose propagator, pattern compiler, or
  FOLD writer.
- rigid.cli is a thin offline argparse adapter exposing compile-degree4, verify,
  and inspect, including the reverse-traversal option.

The public callable boundaries are:

    rigid.canonical.strict_json_loads(data)
    rigid.canonical.canonical_json_bytes(value)
    rigid.canonical.content_hash(value)
    rigid.canonical.content_hash_bytes(data)
    rigid.canonical.assert_canonical_runtime_compatible()
    rigid.patterns.degree4.compile_degree4_pattern(spec, design_spec_hash=...)
    rigid.topology.preflight_topology(payload)
    rigid.topology.build_topology(graph)
    rigid.kinematics.face_poses.propagate_face_poses(graph, topology, folds, spanning_tree_hinge_ids=...)
    rigid.fold_io.export_reference_frame(graph, metadata)
    rigid.fold_io.export_folded_frame(graph, pose_sample, folds, metadata)
    rigid.fold_io.import_static_frame(data)
    rigid.fold_io.normalize_static_frame(frame)
    rigid.compiler.degree4_branch_key(branch)
    rigid.compiler.compile_degree4(spec, samples=9, traversal="forward")
    rigid.compiler.write_bundle(spec_path, output, samples=9, traversal="forward")
    rigid.compiler.verify_bundle(path)
    rigid.compiler.inspect_bundle(path)
    rigid.validation.bundle.verify_bundle(path)
    rigid.cli.main(argv)

Keyword-only markers are omitted above for readability; the compiler and writer
make samples and traversal keyword-only, and the pose propagator makes an
alternate spanning tree keyword-only. The corresponding CLI commands are
compile-degree4, compile-degree4 --reverse, verify, and inspect.

The CLI summary artifact_count counts content members and intentionally excludes
bundle.json, whose externally reported hash addresses the ordered bundle index.
Mechanism entity-array order is authoritative for mechanism bytes and hashes,
even though the typed topology view is invariant to in-memory reordering.

## Exact supported FOLD subset

Each FOLD artifact is a self-contained top-level static frame with the exact
5-vertex, 8-edge, 4-face compiler profile. Reference output is a 2D
creasePattern; sample output is an explicit XYZ foldedForm and is marked 3D only
when geometrically nonplanar.

Strict common metadata is file_spec=1.2,
file_creator="Origami IDE rigid compiler phase2-v1",
file_classes=["singleModel"], frame_unit="mm", and
ro:profileVersion="0.1.0". Reference frames require
frame_classes=["creasePattern"] and
frame_attributes=["2D","manifold","orientable","noCuts","noJoins",
"convexFaces"]. Folded frames require frame_classes=["foldedForm"] and the same
attribute array except that its first token is exactly "2D" or "3D" according
to measured planarity.

The exact common standard key set is file_spec, file_creator, file_classes,
file_title, frame_title, frame_classes, frame_attributes, frame_unit,
vertices_coords, edges_vertices, edges_assignment, edges_foldAngle,
edges_faces, faces_vertices, and faces_edges. The exact rigid key set is
ro:profileVersion, ro:designSpecHash, ro:mechanismHash, vertices_ro:id,
edges_ro:id, edges_ro:role, edges_ro:hingeId, and faces_ro:id. Samples add
exactly ro:branchId, ro:trajectoryParameter, ro:sampleIndex, and
ro:referenceFoldHash.

Boundary edges map to B and 0 degrees. Positive nonzero hinges map to V and
positive degrees; negative hinges map to M and negative degrees; zero hinges map
to U and exactly 0 degrees. Internal radians convert to degrees only at this
boundary. Arrays are exactly aligned, export is nonmutating and byte-stable, and
strict import normalizes index permutations through stable IDs.

The profile emits no multi-frame trajectory, joins, cuts, holes, construction
edges, collision, self-contact, layer-order, or simulator-specific claim.
Unsupported keys and topology fail explicitly. Geometry-only third-party FOLD
without the required semantic IDs is outside strict semantic round trip. The
standards-only neutral fixture is consumer-neutral syntax evidence, not accepted
strict semantic input.

## Canonicalization, provenance, and publication

ro-cjson-1 is a project-local deterministic profile, not RFC 8785/JCS. It uses
strict built-in JSON types, valid unnormalized Unicode, Unicode-code-point key
sorting, safe-range integers, finite binary64 floats, CPython 3.14 shortest
round-trip float spelling, compact separators, positive zero normalization, and
no terminal newline. Runtime vectors cover Unicode ordering, NFC/NFD
preservation, exponent and subnormal boundaries, negative zero, duplicate keys,
cycles, invalid types, unsafe integers, and non-finite values.

The hash DAG is acyclic: design -> mechanism -> reference/sample FOLD ->
trajectory -> certificate -> bundle index. Artifacts contain dependency hashes
but never their own hash. This provides deterministic integrity and content
addressing, not authentication against an attacker able to rewrite every file
and link.

Bundle publication writes and verifies a sibling temporary directory, then uses
renamex_np with RENAME_EXCL on macOS or renameat2 with RENAME_NOREPLACE on Linux.
Existing identical output is an idempotent no-op; differing output is never
overwritten. Symlinks, FIFOs, special files, unsafe absolute/parent/drive paths,
duplicate paths, noncanonical JSON, extra members, and publication races fail
safely. Platforms without the required no-replace primitive fail closed.

## Certificate boundary

For accepted non-flat trajectories, topology, local kinematics, and global
kinematics may pass only when their serialized evidence recomputes. Rank,
nullity, singular values, fold vectors, poses, face and hinge errors, cycle
residuals, sample counts, characteristic length, warnings, and all hash links
are cross-checked. Exact flat is singular and inconclusive; too-near-flat,
binding, out-of-interval, wrong-sign, stale-branch, unevaluated objective/width,
and malformed requests fail before publication. Accepted states within the
inclusive 1e-5 rad binding-warning band carry the warning.

Exact flat produces a zero-sample bundle with overall inconclusive status and
singular diagnostic evidence; it does not evaluate the flat-endpoint stage.
Collision and flat endpoint stay not_run, layer order is not_requested, and no
certificate upgrades the scope beyond ideal zero-thickness kinematics.

## Independent numerical evidence

The committed oracle generator imports no production rigid module and uses
mpmath high-precision geometry and matrix arithmetic. The complete production
path re-evaluated each target through Phase 1, then propagated its binary64
result. It was compared over both fixtures, both branches, both travel signs,
two magnitudes, and all four ring spanning trees: 16 committed non-flat states
and 64 propagation-tree realizations.

| Measurement | Observed maximum |
|---|---:|
| reference vertex vs independent anchor | 4.973799150320701e-14 mm component; 5.1728291973635394e-14 mm Euclidean |
| production fold angle vs independent oracle | 8.881784197001252e-16 rad |
| canonical face-pose entry vs independent oracle | 5.828670879282072e-16 |
| all-tree face-pose entry vs independent oracle | 8.881784197001252e-16 |
| folded vertex vs independent oracle | 7.460698725481052e-14 mm component; 9.592326932761353e-14 mm Euclidean |
| face-isometry error | 5.684341886080802e-14 mm |
| shared hinge endpoint / shared vertex gap | 9.800597115467527e-14 mm |
| world hinge-axis unit-vector gap | 9.371360918460988e-16 |
| simple positive-valley anchor | 6.123233995736766e-17 mm |
| omitted-cycle rotation residual | 9.275564966116015e-16 rad |
| independent Phase-1 closure residual | 9.57707061453503e-16 rad |
| cycle residual vs Phase-1 component delta | 3.691175416608165e-17 rad |
| cycle-vs-Phase-1 norm delta | 3.4088321279390625e-17 rad |
| normalized omitted-cycle translation | 0.0 |
| alternate-tree vs canonical pose entry delta | 8.326672684688674e-16 |
| alternate-tree translation delta | 0.0 mm |
| radians -> degrees -> radians round-trip | 1.1102230246251565e-16 rad |
| strict FOLD normalized round-trip over 18 frames | numeric delta 0.0; zero byte or length differences |

Metamorphic probes additionally observed at most 7.105427357601002e-14 mm
reference-vertex and 7.771561172376096e-16 pose-entry delta under cyclic
relabeling, 4.618527782440651e-14 mm and 3.3306690738754696e-16 under
reflection, and 6.679101716144942e-13 mm vertex delta under complete hinge-axis
reversal plus side swap and cycle reversal. The last is a scale-sensitive
binary64 re-expression, far below the 1e-9 mm acceptance threshold.

The compiler was also exercised through 200 fixed-seed randomized
compile-to-disk bundles with zero verification failures. The final independent
artifact reviewer added 56 accepted random-sector cases and all 16
driver/branch/sign combinations with mixed forward/reverse traversal, again
with zero failures.

## Fixture and artifact hashes

Committed independent fixtures:

| Artifact | SHA-256 |
|---|---|
| generate_rigid_degree4_oracle.py | 7ece25b829215fd2bc2cc12a7b39d835e02b57fb65be39881ed431c57480d977 |
| rigid_degree4_oracle_v1.json | 99fbaa87defc16c0661427d76c92051b64db758ed775e0711cc7b16d2e54c4d3 |
| generate_rigid_phase2_oracle.py | 0ca90e5744711f56c1e842bae0a72f9b39e58083936001c5d670928342e76663 |
| rigid_phase2_oracle_v1.json | 01d4e1aa54f491126b247d4e125b67d682171af0aa2852a2b8d050368d0e3ea6 |
| rigid_static_neutral_v1.fold | 7247896afe2e02e44ce6c05e7ba5ca38b2f849fb238ca6fb1ddb293561d5af67 |

ro-cjson-1 vector hashes are e28bc0ae0e8a179538a945ec44933b788c114c78a575865cb60374104bb30c5f
for the basic object, daec79d8b6582badd3b46bd783a72379bc0b5ae29f5d59f6133025aad69bc8d4
for Unicode code-point sorting, a59a0ab645a72004f75d8282bac1823bfed8283d881fcf38f35cedcc73ba683e
for float boundaries, and a7962fb10dc1255be368ece9c22b2256605921dc6d0a8c9409d3ee406bcb86e5
for NFC/NFD preservation. The two representative branch-key vectors are
d4b:a694254a3c05cbfa31627a46260aecfe8a6c86479acebf742ad2349dbf8d1ec2
and d4b:44e1f008ac2f52722b3bda201007eb73c41d500a202787e38b113fbd3093fa12.

The frozen representative target-0.3-rad, two-sample full bundle vector is:

| Bundle member | Content hash |
|---|---|
| design.json | sha256:a53b0b6cb7836bac02944225c023ede643ba5f881a74b48d4f28687fa21eb2cd |
| mechanism.json | sha256:6e180752093d0a6d8ca1a053da469a0e3ab319e5e1dcb0233294a54670df7439 |
| reference.fold | sha256:1778c3508ca21850a8f1272d5b90d43f8885e0986e0656d0e73f3bc62c00978b |
| frames/sample-0000.fold | sha256:747ec7c4efa319ddadec7e95b3e48378bc287f13973553d5c92fc54370e6a81f |
| frames/sample-0001.fold | sha256:514c12dfd1aa7003fc26688b515eab25285db29c3eaac9d0f78ac3a9aa1a57e3 |
| trajectory.json | sha256:c5af21272a3082e594b627dd1a6fab5d15f063f06ae22661875b5c87c441d8e3 |
| certificate.json | sha256:3c5fba94ca2786a12b72ebbcec29b27d55a925a4458314c51493f79f9676b9c1 |
| bundle.json | sha256:29605b7ff817b01aa8f2e21c4358247a5dbbff92fe97bab43db3ef70812e4cc9 |

The full vector stayed identical under PYTHONHASHSEED values 0, 1, 123, and a
random seed.

## Adversarial review closure

Independent reviewers found and the implementation closed, with regressions:

- trust in serialized branch intervals and driver samples for binding warnings;
- unsafe or blocking manifest members, symlinks, FIFOs, drive paths, and
  time-of-check/time-of-use reads;
- incomplete atomic no-clobber behavior and a post-publication cleanup race;
- false characteristic-length and negative-magnitude evidence;
- tolerance-based M/V sign changes and nonzero values masquerading as exact
  flat;
- bool/int JSON type confusion, impossible sample counts, underflowed nonzero
  targets, and unevaluated objective or width claims;
- axis, side, traversal, branch, and raw-mechanism ordering ambiguities;
- overreliance on production topology, pose, or FOLD generation during disk
  verification; and
- documentation drift around module ownership, FOLD normalization, traversal,
  bundle shape, publication primitives, and the binding-warning boundary.

Every P1/P2 finding has a dedicated regression. Two final independent reviews
reported no unresolved P0/P1/P2 or P1/P2 findings. The certificate still makes
no collision or flat-endpoint claim.

## Verification record

Environment:

- macOS 15.6 arm64; Python 3.14.3
- NumPy 2.4.6; Pydantic 2.13.4; pytest 9.0.3
- independent oracle generation: mpmath 1.3.0 at 100 decimal digits; not a
  runtime dependency
- TreeMaker native extension rebuilt from 50 model sources
- Oriedita validator 1.1.3 rebuilt
- Node 25.6.1; npm 11.9.0; Vitest 2.1.9

Commands and final post-merge results:

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=mcp_harness <shared-python> -m pytest mcp_harness/tests/test_rigid_*.py -q -p no:cacheprovider -W error
    327 passed in 2.55s

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=mcp_harness <shared-python> -m pytest mcp_harness/tests/test_rigid_canonical.py -q -p no:cacheprovider -W error
    16 passed in 0.07s

    make PYTHON=<shared-python> test
    native and Oriedita builds passed; 947 passed, 9 skipped in 548.48s

    PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. <shared-python> -m pytest web/tests -q -p no:cacheprovider
    40 passed, 1 pre-existing Starlette deprecation warning in 0.50s

    <shared-node_modules>/.bin/vitest run
    6 files passed; 59 tests passed in 337 ms

    PYTHONPYCACHEPREFIX=/tmp/rigid-phase2-pycache PYTHONPATH=mcp_harness <shared-python> -m compileall -q mcp_harness/rigid mcp_harness/tests/test_rigid_bundle_verifier.py mcp_harness/tests/test_rigid_cli.py mcp_harness/tests/test_rigid_compiler.py
    exit 0

    git diff --check
    exit 0

    git diff --exit-code origin/main -- mcp_harness/schemas mcp_harness/rigid/schema.py
    exit 0

Public schema source and generated JSON remain unchanged at version 0.1.0.
Half-edges, poses, detailed trajectory evidence, FOLD normalized frames, and
bundle manifests deliberately remain versioned implementation artifacts.

The nine full-suite skips are existing opt-in external smoke tests and
experimental handoff cases; none is a Phase-2 skip.

## Changed files

Documentation:

- docs/rigid-origami-phase2-topology-fold-audit.md
- docs/rigid-origami-phase2-outcome.md
- docs/superpowers/plans/2026-07-12-rigid-origami-phase2-topology-fold.md
- docs/superpowers/specs/2026-07-12-rigid-origami-phase0-design.md
- docs/superpowers/specs/2026-07-12-rigid-origami-phase2-topology-fold-design.md

Production:

- mcp_harness/rigid/canonical.py
- mcp_harness/rigid/cli.py
- mcp_harness/rigid/compiler.py
- mcp_harness/rigid/conventions.py
- mcp_harness/rigid/fold_io.py
- mcp_harness/rigid/kinematics/__init__.py
- mcp_harness/rigid/kinematics/face_poses.py
- mcp_harness/rigid/patterns/__init__.py
- mcp_harness/rigid/patterns/degree4.py
- mcp_harness/rigid/topology.py
- mcp_harness/rigid/validation/__init__.py
- mcp_harness/rigid/validation/bundle.py

Independent fixtures and tests:

- mcp_harness/tests/fixtures/generate_rigid_phase2_oracle.py
- mcp_harness/tests/fixtures/rigid_phase2_oracle_v1.json
- mcp_harness/tests/fixtures/rigid_static_neutral_v1.fold
- mcp_harness/tests/test_rigid_bundle_verifier.py
- mcp_harness/tests/test_rigid_canonical.py
- mcp_harness/tests/test_rigid_cli.py
- mcp_harness/tests/test_rigid_compiler.py
- mcp_harness/tests/test_rigid_conventions.py
- mcp_harness/tests/test_rigid_face_poses.py
- mcp_harness/tests/test_rigid_fold_io.py
- mcp_harness/tests/test_rigid_topology.py

No TreeMaker source, Oriedita source, MCP surface, prompt, web/frontend source,
simulator, Phase-1 solver, or public schema was changed.

## Commit record

- 46c652a — freeze the Phase-2 audit, design, and plan
- 556c92c — add independent fixtures and canonical vectors
- f431ebb — compile deterministic rigid topology
- 7a6394f — propagate deterministic rigid face poses
- 1f904a6 — enforce deterministic FOLD provenance
- a812a0b — certify the compiler, disk verifier, bundle, CLI, and adversarial
  hardening
- 19d3af1 — merge current origin/main at 32afbd4 before final gates
- 4bf2188 — record the Phase-2 outcome and post-merge integration evidence

The branch is pushed to origin and ready PR #43 contains the complete Phase-2
history. The publication URL and final plan state are recorded by the follow-up
documentation commit containing this paragraph.

## Known limitations

- Only the generated generic single concurrent degree-4 diagnostic topology is
  compiled; collinear-special, arbitrary user-authored, and multi-vertex
  topology are unsupported.
- The Phase-1 connected branch interval remains a deterministic numeric
  scan/bisection boundary, not a symbolic proof of every singular boundary.
- Exact flat is intentionally inconclusive and excluded from passing non-flat
  trajectories.
- The current concurrent diagnostic geometry makes omitted-cycle translation
  identically zero; offset-hinge translational closure remains future evidence.
- Static FOLD frames are interoperable geometry snapshots, not a claim that
  consumers implement FOLD multi-frame trajectories or preserve custom IDs.
- Strict semantic FOLD import requires the namespaced stable IDs.
- Content hashes provide integrity, not signatures or authentication.
- Atomic publication is available only where the audited native macOS or Linux
  no-replace primitive exists; other platforms fail closed.
- There is no collision/CCD, layer ordering, thickness, material, force,
  stiffness, fabrication, simulator-verdict, MCP, prompt, or frontend feature.

## Recommended next vertical slice

Add deterministic multi-vertex global continuation around explicit SE(3) cycle
constraints and the existing immutable topology/pose evidence. Preserve exact
branch identity, introduce a versioned continuation manifest, and keep collision
as a separate evidence stage. After that authority is established, add the first
bounded Miura family against the same FOLD, provenance, and offline-verification
pipeline.

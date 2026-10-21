# Rigid-origami Phase 2 topology, pose, FOLD, and provenance audit

**Status:** Gate P1 accepted — no unresolved transform, FOLD-sign, topology,
or content-hash ambiguity remains
**Date:** 2026-07-12
**Baseline:** `origin/main` at `353d249651fc9bf933c0c8e1878e10c36589591a`
**Branch:** `codex/rigid-origami-phase-2-topology-fold`

This audit freezes the conventions for the first deterministic rigid-origami
artifact pipeline. Production code and fixtures must implement these decisions
exactly. A change to any frozen mapping is an artifact-profile version change,
not an implementation detail.

## Accepted claim and exclusions

For one generated, initially planar, concurrent, developable, noncollinear
degree-4 diagnostic sheet, Phase 2 may claim that a recorded non-flat branch
trajectory:

- has a deterministic manifold panel/hinge topology;
- uses fold vectors accepted by the Phase-1 analytic oracle;
- propagates reference-to-folded face poses in `SE(3)`;
- preserves each face's metric and makes shared hinges coincident within the
  recorded tolerance;
- has an omitted dual-cycle residual agreeing with the Phase-1 `SO(3)` closure
  residual;
- is serialized into the documented static FOLD 1.2 subset; and
- has content hashes and certificate evidence recomputable from the bundle.

The pipeline does not evaluate collision, layer order, thickness, elasticity,
forces, stiffness, fabrication, or formal/global physical realizability.
Collision and flat-endpoint evidence remain `not_run`. The certificate scope is
`ideal_zero_thickness_kinematics`.

## Decision ledger

| Type | Frozen decision | Authority |
|---|---|---|
| Sourced | FOLD angles are degrees, positive valley and negative mountain | FOLD 1.2 `edges_foldAngle` |
| Sourced | `edges_faces` orders left then right relative to the oriented edge | FOLD 1.2 edge information |
| Sourced | Face loops describe material faces CCW; the exterior is omitted | FOLD 1.2 face information |
| Sourced | Multiple-frame support is optional and custom keys require a namespace colon | FOLD 1.2 multiple frames/custom properties |
| Sourced | Concurrent vertex closure is an ordered product of crease rotations | Belcastro–Hull; Tachi; He–Guest |
| Repository | Outward crease rays, CCW sectors, positive valley, active right-handed column transforms | `docs/rigid-origami-conventions.md` |
| Repository | Phase-1 branch folds and rank evidence are the local authority | `rigid.degree4` and `rigid.kinematics.closure` |
| Derived | Right-to-left crossing uses `A(start,axis,+rho)`; left-to-right uses `A(start,axis,-rho)` | Existing hinge primitive plus the stored left/right convention |
| Derived | Fixed `f3` and lexicographic Kruskal tree `e0,e1,e2` make omitted `e3` equal the Phase-1 product exactly | Independent `SE(3)` derivation |
| Engineering | Four equal-radius rays joined by boundary chords form the finite diagnostic sheet | Sector range `(0,pi)` and planar geometry |
| Engineering | Characteristic radius is exactly `100.0 mm` in the public generator | Schema 0.1 has no scale field |
| Serialization | `ro-cjson-1` plus SHA-256 is the content policy; it is not RFC 8785/JCS | RFC 8259/8785 audit and independent review |
| Deferred | Geometry-only import of third-party FOLD without stable IDs | Semantic identity is ambiguous without namespaced IDs |

## Finite reference geometry

For sectors `alpha_0..alpha_3`, define cumulative angles

```text
theta_0 = 0
theta_i = sum(alpha_0 .. alpha_(i-1))
```

and characteristic length `L = 100.0 mm`. The canonical vertices are

```text
v:center = (0, 0)
v:e_i    = L (cos(theta_i), sin(theta_i))
```

Coordinates whose absolute value is at most the primitive cleanup tolerance are
stored as positive zero. The outer boundary consists of chords
`v:e_i -> v:e_(i+1 mod 4)`. Face `f_i` is the triangle

```text
(v:center, v:e_i, v:e_(i+1 mod 4)).
```

Every supported sector lies in `(0,pi)`, so every triangle has positive area,
the outer chord loop is a simple convex quadrilateral containing the center,
and all four input sectors are preserved. No square boundary is assumed or
manufactured.

The public design schema has no scale parameter. The generator therefore fixes
`L=100.0 mm` and records `L` and the generator version in trajectory provenance.
A private/test-only positive scale override may exercise covariance; it is not a
new schema 0.1 source field.

## Stable topology and orientation

Canonical semantic IDs are:

```text
sheet:0
vertex:center, vertex:e0 .. vertex:e3
face:f0 .. face:f3
edge:e0 .. edge:e3              # hinges
edge:b0 .. edge:b3              # outer boundary chords
hinge:e0 .. hinge:e3
cycle:degree4
```

The generator emits mechanism entity arrays in the stable-ID order below, and
that order is authoritative in mechanism artifact bytes and hashes. The
topology view uses stable-ID maps/sorts, so it is invariant to in-memory entity
array order, but arbitrary reordered mechanism JSON is not normalized back to
the compiler profile. Strict FOLD import has its own stable-ID/index
normalization. Face loops are cyclically rotated to their smallest stable
vertex ID but never reversed. Edge orientation is semantic:

- hinge `e_i` is `vertex:center -> vertex:e_i`;
- boundary `b_i` is `vertex:e_i -> vertex:e_(i+1)`;
- face `f_i` is geometrically left of hinge `e_i`;
- face `f_(i-1 mod 4)` is geometrically right of hinge `e_i`;
- the local axis point is the oriented edge start exactly;
- both incident face-local axis directions equal the outward reference unit
  edge direction.

All outer face loops are CCW from `+z`; holes would be CW, but holes and cuts are
unsupported in Phase 2. The deterministic fixed face is `face:f3`.

The topology authority materializes oriented half-edges, loop ownership, twins,
vertex stars, face adjacency, connected components, boundary loops,
hinge incidence, the ordered central sectors, a deterministic dual spanning
tree, and fundamental cycles. Kruskal processes hinges by stable ID:

```text
tree hinges: e0, e1, e2
omitted hinge: e3
fundamental cycle: e0, e1, e2, e3
```

The generated graph has 5 vertices, 8 edges, 4 faces, 4 hinges, 12 face
half-edges, 1 sheet component, 1 boundary loop, and 1 independent dual cycle.

## Validation layers and diagnostics

Raw-payload preflight, Pydantic schema validation, and geometric/topological
validation are distinct stages:

1. strict JSON parsing rejects duplicate keys and invalid JSON values;
2. schema 0.1 validates types, versions, references, and contract invariants;
3. topology validation returns stable structured diagnostics with entity IDs.

The topology layer does not silently repair, reorient, merge, or delete input.
Diagnostic codes use uppercase stable vocabulary, including:

```text
TOPOLOGY_ENTITY_MISSING
TOPOLOGY_ENTITY_DUPLICATE
TOPOLOGY_EDGE_REPEATED
TOPOLOGY_EDGE_ZERO_LENGTH
TOPOLOGY_LOOP_REPEATED_VERTEX
TOPOLOGY_LOOP_SELF_INTERSECTION
TOPOLOGY_LOOP_WINDING
TOPOLOGY_EDGE_INCIDENCE
TOPOLOGY_EDGE_NONMANIFOLD
TOPOLOGY_SHEET_DISCONNECTED
TOPOLOGY_HOLE_UNSUPPORTED
TOPOLOGY_CUT_UNSUPPORTED
TOPOLOGY_HINGE_SIDE
TOPOLOGY_HINGE_AXIS
TOPOLOGY_BOUNDARY_COVERAGE
TOPOLOGY_FIXED_FACE
TOPOLOGY_SECTOR_ORDER
TOPOLOGY_CYCLE_INVALID
```

The certificate's tuple of stable error IDs is only a summary. Detailed codes,
entity kinds, entity IDs, related IDs, and messages live in the topology report
inside the trajectory artifact. Its exact object has profile
`rigid-topology-report-v1`, an exact boolean `valid`, an exact integer
`entities_checked`, and a `diagnostics` array. A published passing bundle has
`valid=true`, the independently recomputable entity count, and an empty array;
the shape still freezes every structured diagnostic field for failed compiler
preflight before publication.

## Reference-to-folded `SE(3)` convention

For a reference point `x` on face `f`, the stored row-major homogeneous matrix
`T_f` means

```text
[x_folded; 1] = T_f [x_reference; 1].
```

It is an active, right-handed reference-to-folded transform acting on column
vectors. The fixed face has `T_face:f3 = I_4`.

For axis point `p`, unit direction `a`, and right-handed angle `phi`, define

```text
A(p,a,phi) = [[R(a,phi), (I-R(a,phi))p], [0,0,0,1]].
```

For stored left face `L`, right face `R`, and positive-valley semantic angle
`rho`:

```text
H_L_to_R = A(start, axis, -rho)
T_R = T_L @ H_L_to_R
T_L = T_R @ inverse(H_L_to_R)
```

The crossing transform is right-multiplied because it is expressed in reference
coordinates. `H @ T_parent` is incorrect.

Let `G_i = A(vertex:center, axis_i, +rho_i)`, the right-to-left crossing.
With fixed `f3` and the frozen tree:

```text
T_f3 = I
T_f0 = G0
T_f1 = G0 G1
T_f2 = G0 G1 G2
D_e3 = inverse(T_f3) T_f2 G3 = G0 G1 G2 G3.
```

The rotation block of `D_e3` is exactly the Phase-1 product
`R(e0,rho0) R(e1,rho1) R(e2,rho2) R(e3,rho3)`. Because the common vertex is the
origin, the cycle translation is identically zero for this diagnostic family.
The implementation still records

```text
rotation residual = Log(D_e3[0:3,0:3]) in radians
normalized translation residual = D_e3[0:3,3] / L
```

and direct shared-endpoint/axis errors so later offset and multi-vertex work does
not inherit an `SO(3)`-only interface.

Per sample, validation checks `SE(3)`, all pairwise distances on every face,
both endpoints of every shared hinge, world-axis coincidence, every shared
vertex image, every omitted cycle, and poses obtained from alternative spanning
trees.

## Branch identity and trajectory policy

Phase-1 `Degree4Branch.branch_id` is not a schema-0.1 `StableId`: it contains
characters such as `=`, `+`, and `,`. Schema 0.1 is not changed. The bridge is

```text
d4b:<sha256(exact UTF-8 bytes of Phase-1 branch_id)>
```

using the full 64 lowercase hexadecimal digits. This 68-character key is stored
in `BranchRequest.mode_signature`, certificate `branch_id`, and FOLD
`ro:branchId`. Branch identity is the composite `(design_spec_hash, d4b key)`;
the Phase-1 text alone rounds tangent ratios to 12 significant digits and does
not contain exact sectors.

The trajectory manifest retains the exact Phase-1 text, formula version,
sectors, driver, tangent ratios/signs, positive-driver root sign, and connected
validity interval. Verification re-enumerates Phase-1 branches and requires one
exact key match. Unknown, stale, or ambiguous keys fail; there is no alias,
nearest-root, or automatic branch switch.

For a nonzero target and `N` samples, the canonical forward parameter is

```text
t_i = (i+1)/N, i=0..N-1
driver_i = t_i * target_driver_angle.
```

The public reverse traversal uses `t_i=(N-i)/N`, `i=0..N-1`, and therefore
contains exactly the forward non-flat states in reverse order. Thus the
singular unfolded endpoint `t=0` is excluded and separately exported as the
reference frame. `N`, traversal, and the parameterization version are recorded.
The first sample must satisfy the Phase-1 minimum nonzero driver guard; the
target must remain strictly inside the branch's connected validity interval.
The schema branch `driver_sign` must equal the sign of a nonzero target.

An exact-zero target produces only singular/inconclusive evidence and never a
passing finite-trajectory certificate. A tiny nonzero, exact binding,
out-of-interval, cross-zero, or inconsistent-sign request fails before bundle
publication. An accepted sample whose distance to either branch binding
endpoint is within the inclusive `1e-5 rad` policy remains valid but adds an
explicit tangent-half-angle binding-proximity certificate warning.

## FOLD 1.2 static-frame profile

Every `.fold` artifact is one self-contained top-level static frame. No
`file_frames`, inheritance, or trajectory claim is emitted.

Required standard keys are:

```text
file_spec, file_creator, file_classes, file_title,
frame_title, frame_classes, frame_attributes, frame_unit,
vertices_coords, edges_vertices, edges_assignment, edges_foldAngle,
edges_faces, faces_vertices, faces_edges
```

Required rigid-profile keys are:

```text
ro:profileVersion, ro:designSpecHash, ro:mechanismHash,
vertices_ro:id, edges_ro:id, edges_ro:role,
edges_ro:hingeId, faces_ro:id
```

Folded samples additionally carry `ro:branchId`,
`ro:trajectoryParameter`, `ro:sampleIndex`, and `ro:referenceFoldHash`.
They do not carry a trajectory hash because the trajectory manifest contains
the sample hashes; adding that back-reference would create a hash cycle.

Reference frames use `frame_classes=["creasePattern"]`, 2D coordinates, and
`frame_attributes=["2D","manifold","orientable","noCuts","noJoins",
"convexFaces"]`. Folded samples use `frame_classes=["foldedForm"]` and explicit
3D coordinates. The attribute is `3D` only if the geometry is actually
nonplanar; an explicit XYZ planar state remains `2D`. No self-touching,
self-intersection, collision, or ordering attribute is emitted.

The exact edge mapping is:

| Internal meaning | FOLD assignment | FOLD degrees |
|---|---|---:|
| boundary | `B` | `0.0` |
| positive nonzero hinge | `V` | positive |
| negative nonzero hinge | `M` | negative |
| zero-angle hinge | `U` | `0.0` |

The exact Phase-2 degree-4 profile contains only four boundary edges and four
hinges; it has no construction/triangulation edges. Although FOLD defines `J`
for joins, this profile does not emit or accept `J`. Supporting construction
edges requires a future profile version with independently audited incidence
and simulator behavior. `F` means an actual flat crease and is not used for
construction. `C`, cuts, holes, joins in imported topology, and arbitrary user
topology are unsupported.
`edges_faces[e]` is always `[left,right]`, using `null` on the absent boundary
side. `faces_edges` is aligned with `faces_vertices`. All standard and custom
indexed arrays have exact parallel lengths.

The strict importer rejects unsupported keys/features rather than discarding
them. Semantic round trip requires `vertices_ro:id`, `edges_ro:id`, and
`faces_ro:id`; FOLD itself defines indices but no stable semantic IDs. Import
normalization sorts by stable IDs, remaps every indexed array/reference,
canonicalizes edge orientation by endpoint IDs while swapping `edges_faces`,
and rotates face loops and `faces_edges` together without reversing them.

## `ro-cjson-1` canonical bytes and hashes

`ro-cjson-1` is a project-local deterministic JSON serialization profile. It is
not RFC 8785/JCS: Python key sorting uses Unicode code points instead of UTF-16
code units, and CPython number spelling differs from ECMAScript/JCS.

The normative rules are:

- strict built-in JSON types only: `dict`, `list`, `str`, `None`, exact `bool`,
  exact `int`, and exact `float`; tuples, NumPy scalars, subclasses, custom
  objects, and cycles are rejected at the serialization boundary;
- object keys are exact strings and unique after JSON escape decoding;
- strings are preserved without NFC/NFD normalization, must be valid Unicode,
  and are emitted as UTF-8 without BOM;
- object keys sort recursively by Python Unicode code-point order; arrays retain
  artifact-normalized semantic order;
- integers are limited to `[-9007199254740991,9007199254740991]`; larger exact
  values must be strings;
- schema model dumps and the strict FOLD normalizer establish profile-specific
  float versus integer kinds before serialization; `ro-cjson-1` itself never
  coerces or semantically reorders values;
- floats are finite IEEE-754 binary64 values, `-0.0` becomes `0.0`, and CPython
  3.14 `json` shortest-round-trip spelling is normative for profile version 1;
- separators are exactly `,` and `:` with no insignificant whitespace;
- hashed and written canonical artifact bytes have no terminal newline; and
- timestamps, absolute paths, hash seeds, object identities, and event records
  are absent from deterministic artifacts.

Runtime compatibility is guarded by committed byte/hash vectors, including
negative zero, exponent boundaries, subnormal values, Unicode code-point sort
order, NFC/NFD preservation, and rejection cases. A runtime that fails these
vectors must refuse to compile rather than emit a different hash under the same
profile name.

## Hash dependency graph

The hash graph is acyclic:

```text
normalized design bytes -> design hash D
D -> mechanism bytes -> mechanism hash M
D,M -> reference FOLD -> reference hash F0
D,M,F0,branch,parameter -> sample FOLDs -> ordered hashes Fi
D,M,F0,Fi,fold vectors,poses,evidence -> trajectory -> hash T
M,T-derived certificate ID,evidence -> certificate -> hash C
D,M,F0,Fi,T,C -> bundle index -> externally reported bundle hash B
```

`B` is not stored inside the bytes it hashes. No FOLD frame embeds `T`; no
artifact embeds its own hash. The full normalized design, including provenance,
is hashed as D. A future geometry-only projection must have a different named
hash field and version.

Verification hashes exact bytes, requires canonical-byte equality after strict
parse and normalization, checks all dependency links, and recomputes evidence.
This is integrity/content addressing, not authentication: an attacker able to
rewrite every artifact and hash is outside the claim.

## Transformations and hash/evidence behavior

| Transformation | Geometry/pose behavior | Content behavior |
|---|---|---|
| Incoming mechanism entity-array reordering | topology view is unchanged after stable-ID lookup/sort | raw mechanism order is authoritative; bytes/hash change and the reordered graph is outside the compiler bundle profile |
| Incoming FOLD index permutation with all IDs/references carried | no physical change | identical normalized bytes/hash |
| Cyclic semantic relabel | compare through explicit entity map; regenerated gauges also need planar conjugation/re-gauging | may change source/artifact hash unless IDs are normalized back to the same semantics |
| Oriented hinge reversal plus side swap | same physical relative pose after reversing cycle traversal | raw bytes/hash differ; regenerating the compiler profile restores canonical orientation |
| Axis reversal alone | valid only with angle reversal at primitive boundary | malformed graph if sides are not swapped |
| Sign-reversed travel | `T_f(-rho)=J T_f(rho) J`, `J=diag(1,1,-1,1)` | different sample/trajectory hashes; same branch key |
| Traversal-order reversal | identical non-flat states and endpoints in reverse list order | distinct trajectory/frame indices and hashes; same branch key |
| Reflection fixing `e0` | explicit edge/face map, side swap, coordinate conjugation and possible fixed-face re-gauge | distinct reflected design/artifact hashes |
| Uniform positive scale | lengths/errors scale; rotations/folds and normalized residuals do not | distinct geometry/artifact hashes |

## Failure and unsupported behavior

- Non-finite, malformed, duplicate-key, unsupported-version, or noncanonical
  artifact input is rejected.
- Collinear-special and nondevelopable designs never enter generic formulas.
- Unknown/stale branch keys, wrong target sign, root changes, angle wrapping, and
  branch crossings are rejected.
- Exact flat is singular/inconclusive; near-flat below the guard is rejected.
- Exact binding and out-of-interval requests are rejected without partial
  output; accepted samples within `1e-5 rad` of binding carry a warning.
- Holes, cuts, disconnected sheets, nonmanifolds, arbitrary joins, malformed
  axes/sides, missing boundary coverage, and inconsistent sectors fail with
  structured diagnostics.
- Third-party geometry-only FOLD lacking stable IDs is outside semantic import.
- Current Origami Simulator import/save is not a round-trip authority. The
  Phase-2 profile excludes `J`; no profile rule is weakened for simulator
  compatibility.

## Schema decision

Public schema version 0.1.0 is unchanged. It already represents the source,
mechanism graph, and summary certificate. Half-edges, directed cycles, face
poses, trajectory samples, detailed diagnostics, FOLD normalized frames, and
bundle manifests are immutable implementation-layer artifacts in Phase 2.

The trajectory and bundle carry details absent from `MotionCertificate`, such
as positional closure, face-isometry, hinge coincidence, trajectory/FOLD hashes,
and structured entity diagnostics. The certificate remains a schema-valid
summary and never overclaims those absent fields.

## Independent review closure

Four independent read-only audits were reconciled:

1. repository reuse/isolation found no reusable strict topology/FOLD/hash module
   and identified the branch-ID/schema mismatch;
2. FOLD 1.2 review fixed keys, incidence, units, assignments, static-frame
   semantics, and unsupported import behavior;
3. `SE(3)` review fixed transform direction/order and proved omitted `e3`
   matches Phase 1 exactly; and
4. provenance review rejected an RFC 8785 claim, fixed numeric/Unicode behavior,
   branch-key scope, semantic reindexing, and the acyclic hash graph.

No P1 ambiguity remains. Production implementation is gated on this document,
the design specification, and the implementation plan being committed together.

## Primary references

- [FOLD specification 1.2](https://edemaine.github.io/fold/doc/spec.html)
- [RFC 8259, JSON](https://www.rfc-editor.org/rfc/rfc8259)
- [RFC 8785, JSON Canonicalization Scheme](https://www.rfc-editor.org/rfc/rfc8785)
- [Foschi, Hull, and Ku](https://arxiv.org/abs/2206.12691)
- [He and Guest, On Rigid Origami I](https://arxiv.org/abs/1803.01430)
- [Tachi, Simulation of Rigid Origami](https://origami.c.u-tokyo.ac.jp/~tachi/cg/SimulationOfRigidOrigami_tachi_4OSME.pdf)
- Belcastro and Hull, “A Mathematical Model for Non-Flat Origami,” LAA 348
  (2002), 273–297.

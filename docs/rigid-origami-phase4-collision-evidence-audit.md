# Rigid Origami Phase 4: zero-thickness collision-evidence audit

**Date:** 2026-07-19
**Branch:** `codex/rigid-origami-phase-4-collision-evidence`
**Base:** exact Phase-3 authority `354d238d1fb14e961c99baa0d7eba6fbbf5350bb`

## 1. Decision and claim boundary

Phase 4A adds a separate deterministic post-processing stage for the accepted
samples of a verified `rigid-artifact-bundle-v2`. It answers one bounded
question: do any two zero-thickness face interiors or non-topological
boundaries intersect at an accepted serialized Phase-3 sample?

It does not alter Phase 3. In particular:

- the Phase-3 bundle and certificate bytes remain unchanged;
- the Phase-3 public `MotionCertificate.collision.status` remains `not_run`;
- public source schema `0.1.0` remains unchanged;
- collision evidence is not an alternate kinematics authority; and
- a Phase-4 pass means only `collision_free_at_certified_discrete_samples`.

No positive clearance is claimed. Collision response, layer order, thickness,
friction, material behavior, fabrication, arbitrary topology, branch switching,
and physical realizability remain outside this phase.

Interval CCD is not implemented in Phase 4A. Accepted Phase-3 endpoints and
corrector records do not serialize a continuous enclosure of the one-DOF root
curve between samples. Interpolating exported FOLD vertices, pose matrices, or
fold angles would choose a new motion not certified by Phase 3. The Phase-4
claim therefore records CCD as `not_run`.

## 2. Audited inputs and geometry authority

The input must first pass the existing independent bundle-v2 verifier. Phase 4
then operates on an immutable, bounded, no-follow byte snapshot of that exact
bundle. The filesystem path is an invocation argument and is never serialized.

For each sample, face geometry is reconstructed from:

1. the lexicographically ordered mechanism face loops and reference 2D vertex
   coordinates; and
2. that sample's independently verified face-local 4x4
   `reference_to_folded_face_poses` matrices in `continuation.json`.

Shared `vertices_coords` in static FOLD frames are not the face-planarity
authority. The Phase-3 writer deliberately chooses one incident face image for
each shared vertex, so another face can inherit sub-tolerance nonplanarity.

Every finite JSON float is interpreted as its exact IEEE-754 binary64 rational
using `as_integer_ratio`. Applying a serialized affine face pose to a reference
point is then an exact rational construction. All vertices of one face are
therefore exactly coplanar in the serialized pose-induced plane, rather than
being rounded independently after transformation.

This is an exact-predicate authority for the serialized binary64 data, not a
symbolic proof of the ideal analytic Miura surface. Phase 3 already bounds the
serialized pose/isometry/shared-feature error; Phase 4 preserves that caveat.

## 3. Evidence ledger

| Kind | Accepted statement | Authority |
|---|---|---|
| Repository | Phase-3 samples, poses, topology, hashes, rank, and closure are independently replayed before collision work. | Phase-3 bundle-v2 verifier |
| Repository | Internal lengths are millimetres, faces are stable-ID loops, and arrays carrying order are semantic. | `rigid.conventions`, `rigid.schema`, Phase-3 audit |
| Sourced | Robust geometric branching must be based on exact/adaptive predicates rather than unguarded floating signs. | J. R. Shewchuk, *Adaptive Precision Floating-Point Arithmetic and Fast Robust Geometric Predicates*, DCG 18 (1997), https://people.eecs.berkeley.edu/~jrs/papers/robustr.pdf |
| Sourced | A robust triangle-overlap test can be expressed with orientation predicates and without unstable intermediate floating constructions. | P. Guigue and O. Devillers, *Fast and Robust Triangle-Triangle Overlap Test Using Orientation Predicates* (2003), https://doi.org/10.1080/10867651.2003.10487580 |
| Sourced | Exact predicates and exact constructions are distinct requirements; constructed objects can otherwise reintroduce error. | CGAL kernel manual, https://doc.cgal.org/latest/Kernel_23/index.html |
| Derived | Exact rational affine evaluation of one serialized face pose preserves that face's reference coplanarity exactly. | This audit |
| Derived | Closed AABB overlap is conservative for intersection of the exact pose-induced polygons. | This audit |
| Numerical | The `1e-9 mm` seam envelope is a bounded topology-contact policy inherited from the maximum verified Phase-3 shared-feature gap. | Phase-3 verifier policy and this audit |
| Serialization | Stable sample, face, pair, artifact, and hash order are deterministic repository choices. | `ro-cjson-1` and this audit |
| Deferred | A continuous collision claim needs a certified continuous motion/enclosure, swept bounds, deterministic subdivision, and convergence policy. | Phase-4B gate |

## 4. Supported face and topology profile

Phase 4A accepts only the already-supported bounded Miura bundle-v2 profile:

- one connected sheet;
- one outer loop and no inner loops per face;
- exactly four unique vertices per face;
- finite reference coordinates and face matrices;
- convex, consistently ordered, nondegenerate quadrilaterals after exact
  pose-induced reconstruction;
- stable unique face and vertex IDs; and
- shared topology consisting only of one intended hinge edge or one intended
  vertex between distinct faces.

A malformed source bundle is invalid. A verified bundle that exceeds the
collision profile's resource bounds is refused before pair allocation. A
well-formed pair that reaches an explicitly unsupported geometric state is
recorded as `unsupported`; it can never contribute to a pass.

## 5. Deterministic broad phase

For face `f`, let `B_f` be the closed exact-rational axis-aligned box of its
pose-induced vertices, expanded in each coordinate by the topological seam
envelope `delta = 1e-9 mm`:

```text
B_f[k] = [min_i p_i[k] - delta, max_i p_i[k] + delta].
```

The production broad phase is a stable sweep on x:

1. sort faces by `(min_x, face_id)`;
2. retain active faces whose `max_x >= current.min_x`;
3. test closed y/z interval overlap; and
4. emit `(min_face_id, max_face_id)` in final lexicographic order.

Expansion can add false positives but cannot remove a real intersection.
Intended adjacent/shared-vertex pairs are not pruned. The independent verifier
recomputes the same required candidate set by exhaustive unordered `O(F^2)`
closed-box comparison, not by the production sweep. Exact candidate-list
equality is required; a conservative-but-different claimed list is invalid.

## 6. Discrete narrow phase

### 6.1 Direct convex-face predicates and constructions

Each accepted quadrilateral is intersected directly as one closed convex planar
polygon. No evaluation diagonal is introduced. This removes duplicate or missed
results on triangulation boundaries while preserving the same face surface. The
oracle nevertheless contains an intersection lying exactly on the diagonal a
conventional stable fan would choose, proving independence from that
non-material boundary.

All signs and constructed intersection points use exact `Fraction` arithmetic
over the serialized dyadic rationals.

For non-coplanar faces, exact signed plane evaluations reject strict same-side
pairs. Each convex polygon is sliced by the other face's plane using
exact edge parameters

```text
t = d_i / (d_i - d_j),
p = p_i + t (p_j - p_i).
```

The two resulting point/segment intervals are compared along the largest exact
component of the plane-intersection direction `n_a x n_b`. Empty, point, and
positive-length overlap classify separation, vertex contact, and segment
contact respectively.

For coplanar faces, the dominant normal component is dropped and exact
Sutherland-Hodgman clipping computes the closed convex intersection polygon.
Its exact signed area distinguishes area overlap from segment or point contact.
No tolerance-based predicate is called exact.

The face-pair contact dimension is ordered as
`none < point < segment < area`. A non-topological point or edge contact is a
collision for zero-thickness evidence; penetration volume is not required.

### 6.3 Legal topology

The legal locus is derived only from mechanism topology:

- faces sharing one hinge may meet on that intended shared edge;
- faces sharing exactly one material vertex may meet at that intended point;
- faces with no shared material feature have no legal contact locus.

Because independently serialized face poses may differ at a shared feature by
the already-certified Phase-3 gap, the legal locus is a closed `delta=1e-9 mm`
envelope around both face-local images of the shared edge or vertex. Exact
rational squared point-to-segment/point comparisons apply the inclusive
boundary. An intersection component is legal only if all of its vertices lie
inside both corresponding feature envelopes. Any component away from that
locus is a collision, even for adjacent faces.

An intended shared feature is reported as `legal_topological_contact` even when
the two serialized face-local images have a sub-tolerance gap and therefore do
not exactly intersect. That relation describes material topology; it is not a
positive-clearance or exact-coincidence claim.

## 7. Verdict reduction and deterministic first collision

Each broad-phase candidate receives exactly one ordered result:

- `separated`;
- `legal_topological_contact`;
- `collision`; or
- `unsupported`.

The overall claim is reduced as follows:

1. any proven collision yields `fail`;
2. otherwise any unsupported result yields `inconclusive`;
3. otherwise the complete discrete trace yields `pass`.

The first collision is the first collision in serialized trajectory order
`[seed, *samples]`, then lexicographic stable face-pair order. Pseudo-arclength
is evidence, not a sorting key. Legal contact is neutral. Empty maxima or first
event fields are JSON `null`, never NaN, infinity, or a numeric sentinel.

## 8. Artifact and hash DAG

Phase 4A introduces three implementation profiles:

- `rigid-miura-discrete-collision-evidence-v1`;
- `rigid-miura-collision-certificate-v1`; and
- `rigid-collision-artifact-bundle-v1`.

The sidecar directory contains exactly:

```text
collision-evidence.json
collision-certificate.json
bundle.json
```

It references, but does not copy or modify, the Phase-3 bundle. The evidence
binds the exact Phase-3 bundle, design, mechanism, reference, continuation, and
certificate hashes; branch/continuation IDs; and every ordered sample index,
sample ID, path, and FOLD hash.

Identity hashes use canonical JSON objects with explicit domain fields:

```text
evidence_id = "cole:" + SHA256(CJSON(evidence_without_id plus
                 domain="rigid-miura-discrete-collision-evidence-id-v1"))

certificate_id = "colcert:" + SHA256(CJSON({
  domain: "rigid-miura-collision-certificate-id-v1",
  source_bundle_hash: ...,
  collision_evidence_hash: ...
}))
```

`bundle.json` hashes the exact evidence and certificate bytes in fixed order.
SHA-256 supplies deterministic integrity, not signer authentication.

## 9. Resource and filesystem authority

Phase-3 public bounds would permit more than 551 billion pair/sample checks,
so Phase 4A freezes tighter limits checked before allocation:

| Limit | Value |
|---|---:|
| samples | `257` |
| faces per sample | `256` |
| total unordered pair universe | `1,000,000` |
| emitted candidates/results | `65,536` |
| source snapshot bytes | `64 MiB` |
| collision manifest bytes | `64 KiB` |
| collision certificate bytes | `64 KiB` |
| collision evidence bytes | `32 MiB` |
| collision artifact total bytes | `33 MiB` |

The candidate cap was reduced from the pre-implementation audit value of
`1,000,000` after adversarial allocation analysis. One million records require
at least 197.41 MiB of canonical candidate/evaluation JSON and therefore can
never satisfy the 32 MiB evidence profile; their Python container footprint
could exceed 620 MiB before canonicalization. The `65,536` cap is checked
cumulatively after broad phase and before any narrow-result allocation.

The 33 MiB aggregate sidecar cap is defense in depth: the three individual
maxima sum to only 32.125 MiB. Likewise, no allowed integer sample/face pair
lands exactly on the 1,000,000 pair-work limit. Inclusive/first-over behavior
for those arithmetic bounds is frozen through pure preflight tests, with the
nearest profile-valid cases exercised end to end.

The 3x4, 257-sample committed geometry needs only 16,962 exhaustive pair
checks. Inclusive limit and first-over-limit tests freeze every boundary.

Both source and sidecar roots are opened as directories without following
symlinks. Members are enumerated with an early count stop, opened relative to
directory descriptors with no-follow flags, required to be regular files, and
read only after size checks. Source bytes are snapshotted once and the snapshot
is both independently Phase-3-verified and collision-replayed, preventing a
verify-then-reread race. Output equal to or nested inside the source is rejected.

Malformed JSON, noncanonical bytes, duplicate keys, unsafe or NUL paths,
symlinks, special files, missing/extra/reordered members, hash mismatch,
unsupported profiles, source substitution, and every work/byte overrun fail
closed with stable diagnostics.

## 10. Independent oracle

The committed generator imports no production `rigid` module. It uses exact
rational constructions and its own exhaustive broad phase and intersection
classification. The v1 fixture includes:

- separated faces;
- a proper non-coplanar crossing;
- coplanar area overlap;
- edge-only and vertex-only non-topological contact;
- a legal shared hinge;
- adjacent faces intersecting away from their hinge;
- a would-be triangulation-diagonal adversary;
- inclusive seam-tolerance cases and values immediately on both sides;
- a collision-free bounded non-flat Miura sample;
- a deliberately colliding integrated face set; and
- collision-free endpoints with an interior collision, reserved for CCD.

Regeneration freezes the generator hash, fixture hash, Python/runtime metadata,
and exact command. Production and verifier results must both match the fixture.

## 11. Interval CCD gate

The Phase-3 continuation artifact certifies accepted roots and corrector
replays. It does not provide, for each interval:

- a unique continuous parameterization of every intermediate root;
- an interval enclosure of fold angles or face poses;
- a branch-isolation/Lipschitz certificate excluding another root component;
- swept AABB bounds;
- conservative vertex-face and edge-edge inclusion functions; or
- deterministic subdivision/convergence and first-contact brackets.

Modern inclusion-based CCD similarly requires an inclusion function whose
range contains the motion over the entire time interval, not only endpoint
samples; see Wang et al., *A Large Scale Benchmark and an Inclusion-Based
Algorithm for Continuous Collision Detection*, ACM TOG 40(5), 2021,
https://continuous-collision-detection.github.io/tight_inclusion/CCD-benchmark-paper-350ppi.pdf.

Phase 4B must first widen the continuation evidence with certified segment
enclosures or another independently replayable continuous-motion contract.
Until then, endpoint interpolation cannot receive a continuation-path CCD pass.
That future contract can be a distinct, independently verified sidecar bound to
the existing Phase-3 hashes; the byte-frozen Phase-3 artifact need not change.

## 12. Compatibility and rejected alternatives

- Extending bundle-v2 in place is rejected because its exact file set and hash
  DAG are frozen.
- Reusing public `CollisionEvidence` as the sidecar claim is rejected because a
  public pass requires `minimum_clearance_mm`, which Phase 4A does not compute.
- Static FOLD shared coordinates are rejected as face-planarity authority.
- Floating epsilon orientation tests are rejected.
- Pruning adjacent faces before narrow phase is rejected because off-hinge
  intersections must remain detectable.
- An unordered or implementation-dependent candidate set is rejected.
- Linear endpoint interpolation labeled as CCD is rejected.

Schema `0.1.0`, generated schemas, Phase-1/2 profiles, Phase-3 bundle-v2, and
all frozen Phase-3 bytes remain backward compatible.

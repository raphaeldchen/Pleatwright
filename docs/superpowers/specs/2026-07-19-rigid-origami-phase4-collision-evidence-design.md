# Phase 4 rigid-origami collision-evidence design

**Status:** accepted for implementation
**Date:** 2026-07-19
**Audit:** `docs/rigid-origami-phase4-collision-evidence-audit.md`

## Goal

Generate, publish, and independently replay a deterministic sidecar claim about
zero-thickness face intersections at every accepted sample in one verified
Phase-3 Miura bundle.

```text
verified Phase-3 bundle-v2
          |
          +-> immutable bounded snapshot
          +-> exact face-local sample polygons
          +-> sweep broad phase -> exact rational narrow phase
          +-> collision-evidence.json
          +-> collision-certificate.json
          +-> collision sidecar bundle
                         |
                         +-> independent exhaustive replay verifier
```

## Compatibility decisions

- Public schema stays `0.1.0`; generated schemas are unchanged.
- Phase-3 bundles and certificates remain byte-identical, including
  `collision.status="not_run"`.
- Collision is post-processing over a verified bundle-v2, not a compiler mode.
- The sidecar is a separate three-file directory and receives its own profiles.
- The claim is intersection-only. It has no `minimum_clearance_mm` field.
- CCD is serialized as `not_run` with the frozen insufficient-authority reason.

## Module ownership

### `rigid.collision_geometry`

Owns generic immutable face snapshots, the production sweep broad phase, exact
rational direct convex-face intersection, and topology-contact reduction. It has no
JSON, filesystem, Phase-3 solver, or publication dependency.

```python
@dataclass(frozen=True)
class CollisionFace:
    id: str
    vertex_ids: tuple[str, str, str, str]
    vertices: tuple[tuple[Fraction, Fraction, Fraction], ...]

    @classmethod
    def from_serialized(cls, *, id, vertex_ids, vertices): ...

@dataclass(frozen=True)
class LegalFeature:
    kind: Literal["none", "shared_vertex", "shared_hinge"]
    vertex_ids: tuple[str, ...]
    hinge_id: str | None

@dataclass(frozen=True)
class PairCollisionResult:
    face_pair: tuple[str, str]
    relation: Literal[
        "separated", "legal_topological_contact", "collision", "unsupported"
    ]
    contact_dimension: Literal["none", "point", "segment", "area", "unknown"]
    legal_feature: LegalFeature
    predicate_evaluations: int
    intersection_component_count: int

def broad_phase_candidates(faces, *, padding_mm=...): ...
def evaluate_face_pair(left, right, *, legal_feature, seam_tolerance_mm=...): ...
def evaluate_collision_sample(faces, *, legal_features): ...
```

The serialized-input factory accepts exact built-in finite ints/floats and
converts them immediately to `Fraction`; the stored public geometry is rational.
Artifact reconstruction performs `T*x+T*y+t` in `Fraction` before constructing
the face and never rounds a world vertex back to float. Inputs also require
unique stable IDs, exactly four unique vertices, convex winding, exact
pose-induced planarity, strict convexity, and nonzero edges.

The narrow phase intersects each closed convex quadrilateral directly, without
introducing a non-material triangulation diagonal. Results reduce to one
face-pair relation with collision priority over legal contact and separation.

### `rigid.collision_evidence`

Owns source snapshot interpretation, sample reconstruction, evidence/claim
construction, source-aware inspection, and atomic no-replace publication.

```python
@dataclass(frozen=True)
class CollisionInspection:
    source_bundle_hash: str
    collision_bundle_hash: str
    claim_status: Literal["pass", "fail", "inconclusive"]
    sample_count: int
    first_collision: Mapping[str, JSONValue] | None
    artifact_paths: tuple[str, ...]

@dataclass(frozen=True)
class CompiledCollisionEvidence:
    artifacts_by_path: Mapping[str, bytes]
    bundle_hash: str
    inspection: CollisionInspection

def compile_collision_evidence(source_bundle: Path) -> CompiledCollisionEvidence: ...
def write_collision_evidence(source_bundle: Path, output: Path) -> ...: ...
def inspect_collision_evidence(source_bundle: Path, evidence: Path) -> ...: ...
```

Source records are `[continuation.seed, *continuation.samples]`. Reference
points are transformed independently per face with that record's face matrix.
Stable faces and pairs are lexicographically ordered. Resource work is checked
before face-pair list construction.

Publication factors the existing atomic no-replace primitive behind a verifier
callback, preserving existing Phase-2/3 behavior. Existing output is verified
first under collision caps, then compared byte-for-byte. Source and output may
not be equal or nested in either direction.

### `rigid.validation.safe_snapshot`

Owns a small filesystem boundary shared by the generator and verifier:

- directory-descriptor root open with no-follow;
- bounded streaming member enumeration;
- component-relative no-follow regular-file reads;
- byte caps before allocation;
- exact immutable `Mapping[str, bytes]`; and
- optional materialization into a private temporary directory for the existing
  Phase-3 verifier.

It performs no collision or source semantic validation.

### `rigid.validation.collision_evidence`

Owns independent two-input verification. It may reuse canonical JSON, immutable
profile constants, public schema parsing, safe snapshot I/O, and the existing
independent Phase-3 verifier. It must not import production collision geometry,
evidence/compiler/publication modules, Phase-3 pattern/solver/pose modules, or
FOLD writers.

The verifier reconstructs source faces itself, computes candidates by
exhaustive `O(F^2)` closed-AABB comparison, independently repeats exact
  direct convex-face predicates, and rebuilds every sample summary, first collision,
certificate, and hash link. Fully rehashed false evidence must fail.

Artifact validity and collision verdict are separate:

- `valid=false` means malformed, untrusted, mismatched, or unreplayable bytes;
- `valid=true, claim_status=fail` means collision evidence is sound;
- `valid=true, claim_status=inconclusive` means sound evidence contains an
  explicitly unsupported evaluation; and
- `valid=true, claim_status=pass` means every candidate was resolved without a
  non-topological intersection.

## Geometry algorithms

### Pose-induced exact polygons

For serialized reference point `(x,y)` and row-major face matrix `T`, exact
dyadic coordinates are

```text
p = (
  T00*x + T01*y + T03,
  T10*x + T11*y + T13,
  T20*x + T21*y + T23
).
```

All arithmetic uses rational values created from the serialized binary64
numbers. This affine construction makes all vertices of a face exactly
coplanar in `span(T[:,0], T[:,1])`.

### Broad phase

Closed AABBs are expanded by `COLLISION_LEGAL_CONTACT_ATOL_MM`. Production uses
a deterministic x sweep and exact rational comparisons. Verification uses
exhaustive unordered pairs. Both produce the exact same sorted candidate list.

### Narrow phase

For each convex face pair:

1. exact plane-side determinants reject strict separation;
2. noncoplanar plane slices yield exact point/segment intervals;
3. coplanar dominant-axis projection and exact convex clipping yield the
   intersection polygon; and
4. exact area/extent classify `none`, `point`, `segment`, or `area`.

No floating intersection coordinate or internal diagonal is constructed.

### Contact policy

Mechanism topology derives the only legal feature. The inclusive seam envelope
is `1e-9 mm`. Exact squared point-to-point and point-to-segment comparisons
classify an intersection component. Every component must remain inside both
face-local images of the legal feature; otherwise the pair collides.

Non-topological vertex-only or edge-only contact is a collision. Intended
hinge/vertex topology is reported as legal contact even if the independently
serialized face images have a sub-tolerance gap.

## Frozen constants and resource limits

All constants live in `rigid.conventions` with inclusive boundary tests:

| Constant | Value |
|---|---:|
| evidence profile | `rigid-miura-discrete-collision-evidence-v1` |
| certificate profile | `rigid-miura-collision-certificate-v1` |
| bundle profile | `rigid-collision-artifact-bundle-v1` |
| scope | `discrete_samples_only` |
| broad phase | `exact-rational-sweep-aabb-v1` |
| narrow phase | `exact-rational-direct-convex-face-v1` |
| contact policy | `phase3-topological-seam-envelope-v1` |
| seam envelope | `1e-9 mm` |
| max samples | `257` |
| max faces | `256` |
| max pair-universe work | `1,000,000` |
| max candidate records | `65,536` |
| max source snapshot | `64 MiB` |
| max evidence | `32 MiB` |
| max certificate | `64 KiB` |
| max manifest | `64 KiB` |
| max sidecar total | `33 MiB` |

The verifier rejects policy drift rather than trusting serialized limits. The
candidate cap binds cumulatively before narrow-result allocation. It replaces
the pre-implementation `1,000,000` value, which could not fit the 32 MiB
evidence contract and exposed excessive transient allocation. The 33 MiB total
sidecar cap is intentionally redundant with the tighter per-file caps; exact
arithmetic boundaries unreachable under valid sample/face counts are tested
through their preflight predicates.

## Evidence contract

`collision-evidence.json` exact top-level fields:

```text
profile
evidence_id
canonical_json_profile
scope
source
policy
samples
summary
ccd
```

`source` binds bundle/design/mechanism/reference/continuation/certificate hashes,
branch ID, continuation ID, and ordered sample links. `samples` stores the
source link, face/pair counts, exact broad candidate array, aligned narrow
evaluation array, relation counts, sample status, and first collision.

`summary` stores sample/candidate/relation counts, overall status, and the first
collision. It stores no clearance. `ccd` is exactly:

```json
{
  "status": "not_run",
  "reason": "phase3-v1-lacks-certified-continuous-segment-enclosures"
}
```

`collision-certificate.json` binds the evidence hash and source bundle hash,
repeats only the honest scope/status/first collision/CCD summary, and carries a
domain-separated ID. `bundle.json` has exact ordered entries for evidence then
certificate, with JSON media types and exact content hashes.

## Independent fixture

The generator and fixture are:

```text
mcp_harness/tests/fixtures/generate_rigid_phase4_collision_oracle.py
mcp_harness/tests/fixtures/rigid_phase4_collision_oracle_v1.json
```

The generator imports no production `rigid` module. Exact integer/rational
coordinates supply base cases and tolerance boundaries. An independent
high-precision Miura constructor supplies the non-flat 2x3 collision-free
sample. The fixture freezes generator/runtime metadata, case inputs, exhaustive
candidates, expected relations/dimensions, integrated summaries, and a
continuous-motion counterexample reserved for CCD.

## CLI

The smallest separate surface is:

```text
python -m rigid.cli generate-collision SOURCE_BUNDLE --output SIDECAR
python -m rigid.cli verify-collision SOURCE_BUNDLE SIDECAR
python -m rigid.cli inspect-collision SOURCE_BUNDLE SIDECAR
```

Output is canonical one-line JSON. `verify-collision` exits zero for valid
pass/fail/inconclusive evidence and nonzero only for invalid evidence; the
payload always reports `claim_status`, `scope=discrete_samples_only`, and
`ccd_status=not_run` together. Generation publishes fail evidence as a valid
result rather than treating a detected collision as an execution error.

## CCD gate decision

Phase 4B is deferred. A future design must add to the continuation contract:

- a certified interval parameter and unique branch segment;
- interval enclosures for intermediate fold states or face poses;
- swept broad-phase bounds;
- conservative vertex-face and edge-edge inclusion predicates;
- deterministic subdivision, work limits, and convergence failure;
- first-contact brackets; and
- independent replay of the interior-collision fixture.

Endpoint-only or linearly interpolated FOLD data cannot satisfy this contract.
The added continuous authority may be published as a new independently
verified Phase-4B sidecar; it need not mutate the byte-frozen Phase-3 bundle.

## TDD slices

1. independent oracle plus one separated end-to-end red test;
2. stable broad phase versus exhaustive fixture;
3. noncoplanar exact narrow phase;
4. coplanar/contact/diagonal cases;
5. legal topology and away-from-hinge collision;
6. verified Phase-3 sample reconstruction and integrated evidence;
7. sidecar hash DAG, independent verifier, and fully rehashed mutations;
8. filesystem/resource hardening, CLI, and atomic publication;
9. CCD authority review and explicit deferral;
10. adversarial geometry and artifact reviews.

Every slice is one observable red/green cycle before the next behavior. Tests
exercise public interfaces and do not mock production collaborators.

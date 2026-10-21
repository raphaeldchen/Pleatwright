# Rigid-origami Phase 4 outcome: independently verified collision evidence

**Status:** Accepted — Phase 4A discrete collision gates pass

**Date:** 2026-07-21

**Branch:** `codex/rigid-origami-phase-4-collision-evidence`

**Worktree:** `<repo>-rigid-phase4`

**Exact Phase-3 base:** `354d238d1fb14e961c99baa0d7eba6fbbf5350bb`

**Pull-request base:** `main`, which now contains the exact Phase-3 base

Phase 4A adds a deterministic, independently replayed collision stage over an
already verified bounded Miura trajectory. It evaluates the exact serialized
binary64 face poses at accepted Phase-3 samples, publishes a separate
content-addressed sidecar, and leaves every Phase-3 byte and claim unchanged.

The accepted claim is deliberately narrow:

```text
scope = discrete_samples_only
ccd.status = not_run
ccd.reason = phase3-v1-lacks-certified-continuous-segment-enclosures
```

A Phase-4A `pass` means that every supported face-pair evaluation at every
serialized accepted sample was either separated or confined to its intended
topological seam. It is not a positive-clearance, continuous-motion,
finite-thickness, layer-order, contact-response, fabrication, or general
physical-foldability claim.

## Recovery of the interrupted turn

The resumed worktree and branch were the requested ones. Commits `d2109a3`,
`f0bc38c`, and `289e425` were preserved. The three interrupted untracked files
also survived:

- `mcp_harness/rigid/collision_evidence.py`;
- `mcp_harness/rigid/validation/safe_snapshot.py`; and
- `mcp_harness/tests/test_rigid_collision_evidence.py`.

They were inspected before editing. No source bytes were crash-lost and no
partial implementation had to be recreated. The only interrupted state was a
newly written GREEN that had not yet been executed; its focused tracer test was
rerun and passed before development continued.

The coherent implementation history before this outcome record is:

| Commit | Slice |
|---|---|
| `d2109a3` | freeze Phase-4 collision authority |
| `f0bc38c` | freeze the independent oracle |
| `289e425` | exact discrete face collision evaluation |
| `6dca0b4` | sidecar publication and independent verification |
| `5319a3a` | parser, resource, filesystem, and mutation hardening |
| `ad4d148` | final geometry, claim-boundary, and snapshot review fixes |

## Architecture and evidence flow

```text
verified rigid-artifact-bundle-v2 snapshot
  -> independent Phase-3 bundle verification
  -> exact rational face reconstruction from reference geometry + face poses
  -> stable padded-AABB sweep broad phase
  -> direct convex quadrilateral narrow phase
  -> per-sample ordered collision ledger
  -> canonical collision-evidence.json
  -> source-bound collision-certificate.json
  -> rigid-collision-artifact-bundle-v1 bundle.json
  -> independent exhaustive replay from the same immutable source snapshot
  -> atomic no-replace publication
```

The source and sidecar are snapshotted through bounded directory descriptors.
The same immutable source bytes are independently Phase-3-verified, compiled,
and collision-replayed. Publication verifies staged sidecar bytes against that
snapshot before the no-replace rename. Identical existing output is an
idempotent success; different output and overlapping or nested source/output
roots are refused.

The CLI surface is:

```text
python -m rigid.cli generate-collision SOURCE --output SIDECAR
python -m rigid.cli verify-collision SOURCE SIDECAR
python -m rigid.cli inspect-collision SOURCE SIDECAR
```

All three summaries report `claim_status`, `scope`, and `ccd_status` together,
so a discrete `pass` cannot be presented without its CCD boundary. Verification
uses exit zero for valid pass/fail/inconclusive evidence and nonzero for invalid
evidence; a valid detected collision is evidence, not a command failure.

## Geometry authority and predicates

Each serialized finite JSON float is reconstructed as its exact IEEE-754
binary64 rational. A face-local 4x4 pose is applied to its four reference
vertices with rational arithmetic. Thus every supported face is exactly planar
in the authority induced by the serialized pose, while remaining subject to
Phase 3's already measured serialization error relative to the ideal analytic
surface.

Faces must have four unique stable vertex IDs and four unique, finite,
coplanar, strictly convex, consistently ordered points. Duplicate,
nonfinite, degenerate, nonconvex, nonplanar, and malformed-topology cases fail
before intersection work.

For face `f`, the production broad phase uses the closed box

```text
B_f[k] = [min_i p_i[k] - delta, max_i p_i[k] + delta]
delta = 1e-9 mm.
```

Faces are swept by `(min_x, face_id)` and candidate IDs are emitted in final
lexicographic order. Closed padding can add false positives but cannot remove a
true closed-set intersection. The independent verifier does not reuse the
sweep: it evaluates all unordered `O(F^2)` box pairs and requires exact
candidate-list equality.

The narrow phase treats each convex quadrilateral directly, without an
internal triangulation diagonal. All signs and constructed points use exact
`Fraction` arithmetic over the serialized dyadic inputs.

For noncoplanar planes, strict same-side signs reject separation and polygon
edges are sliced with

```text
t = d_i / (d_i - d_j)
p = p_i + t (p_j - p_i).
```

The resulting point or segment intervals are compared along the largest exact
component of the plane-intersection direction. For coplanar faces, dominant-
axis projection and exact Sutherland-Hodgman clipping distinguish empty,
point, segment, and positive-area intersections. Point and edge tangencies are
closed-set collisions unless they are an intended material feature.

Legal contact is derived only from mechanism topology. A shared hinge permits
contact on its intended edge; a shared material vertex permits contact at that
point. Both face-local feature images receive an inclusive `1e-9 mm` envelope
to accommodate Phase-3-certified pose serialization gaps. Every intersection
vertex must lie in both feature envelopes. Contact away from the intended
feature remains a collision even for adjacent faces.

Relations are `separated`, `legal_topological_contact`, `collision`, and
`unsupported`. Any collision produces `fail`; otherwise any unsupported result
produces `inconclusive`; otherwise the complete discrete trace produces
`pass`. First collision is selected by serialized trajectory order and then
stable face-pair order.

## Artifact profiles and hash DAG

The exact three-file sidecar is:

```text
collision-evidence.json
collision-certificate.json
bundle.json
```

Its versioned profiles are:

- `rigid-miura-discrete-collision-evidence-v1`;
- `rigid-miura-collision-certificate-v1`; and
- `rigid-collision-artifact-bundle-v1`.

The evidence binds the exact Phase-3 bundle, design, mechanism, reference,
continuation, and certificate hashes, plus every ordered sample ID, FOLD path,
and FOLD hash. Identity construction is:

```text
evidence_id = "cole:" + SHA256(CJSON({
  domain: "rigid-miura-discrete-collision-evidence-id-v1",
  ...evidence_without_id
}))

certificate_id = "colcert:" + SHA256(CJSON({
  domain: "rigid-miura-collision-certificate-id-v1",
  source_bundle_hash: ...,
  collision_evidence_hash: ...
}))
```

The manifest hashes the exact evidence and certificate bytes in fixed order.
Canonical JSON rejects NaN, infinity, duplicate keys, unsafe integers,
noncanonical whitespace/order, BOMs, invalid UTF-8, and excess nesting. SHA-256
provides deterministic integrity and source binding, not signer authentication.

## Independent authority

The committed oracle generator imports no production `rigid` module. It uses
exact rational constructions, its own exhaustive broad phase, and independent
intersection classification. Its fixture covers separation, proper
noncoplanar crossing, coplanar overlap, edge/vertex contact, legal hinge and
vertex contact, off-hinge collision, a triangulation-diagonal adversary,
inclusive seam boundaries and first-outside values, a nonflat collision-free
Miura sample, deterministic first collision, and an endpoint-clear/interior-
collision case reserved for the CCD gate.

The production/verifier independence guard checks both `import` and
`from ... import ...` AST forms, including dotted imports, and forbids production
collision predicates, compiler/solver paths, kinematics, and patterns. The
verifier reconstructs faces locally and uses exhaustive pairs rather than the
production sweep.

Oracle hashes:

| File | SHA-256 |
|---|---|
| generator | `6b2b49cc7b474f5b147f4b6c7c6f0a43654b2305a767ef007a17e520508df83a` |
| fixture | `fd9fce4da7cd0fefd200ddf61f48c54c43769ccfd27e4fdb5f04350359a90d9b` |

Regeneration produced byte-identical output with the same fixture hash.

## Representative evidence and observed bound

For the standard 2x3, three-sample Phase-4 fixture:

| Item | Value |
|---|---|
| source bundle | `sha256:1aad04690dcbb14441877f3f9607d59d55e78ba672d393408e73e7d6897eb01b` |
| collision bundle | `sha256:525d104ad93ffabdda0ba5dcde72c4ec19208968e5d94f96336230393dcbfaea` |
| evidence ID | `cole:f56b6259e1ab0d79dba856465b0ccdad40c23c5ea234cb3d8614872054683287` |
| certificate ID | `colcert:b02ea9d9d05927c70227e6d945e9f611f8b64b26133a1640dd64b875243d070a` |
| evidence bytes/hash | `14,713` / `sha256:2c18509c5f97ce36b6628f319dc3e07f3220a39a8ad7c5a0c6f261a93eba3f39` |
| certificate bytes/hash | `519` / `sha256:1e943455ae2e67e9cce3eb1dadd17f81d0de831b21a0615377102d6dcf4cbafc` |
| manifest bytes/hash | `569` / `sha256:525d104ad93ffabdda0ba5dcde72c4ec19208968e5d94f96336230393dcbfaea` |
| samples / faces | `3` / `6` |
| pair universe / candidates | `45` / `33` |
| relations | `33 legal_topological_contact`; all others `0` |
| status / first collision | `pass` / `null` |

The maximum observed separation between corresponding legal feature images was
`5.2963299901390066e-14 mm`, at sample 0 for
`face:r000:c002` / `face:r001:c002`, hinge
`hinge:1-longitudinal:r001:c002`, vertex `vertex:r001:c003`. This is about
18,900 times smaller than the inclusive `1e-9 mm` policy envelope. Predicate
decisions themselves add no floating sign error because they are exact over the
serialized rational inputs.

## Resource and filesystem hardening

| Limit | Value |
|---|---:|
| samples | `257` |
| faces per sample | `256` |
| cumulative unordered pair work | `1,000,000` |
| cumulative candidate/evaluation records | `65,536` |
| source snapshot | `64 MiB` |
| evidence | `32 MiB` |
| certificate | `64 KiB` |
| sidecar manifest | `64 KiB` |
| total sidecar | `33 MiB` |

Candidate count is checked cumulatively before narrow-result allocation. The
pre-implementation one-million candidate value was reduced to `65,536` after
review showed that its minimum canonical record size could not fit the 32 MiB
artifact cap and its live Python footprint could exceed 620 MiB.

Source and sidecar roots are opened by canonical parent descriptors, then the
final root with `O_DIRECTORY|O_NOFOLLOW`; in-bundle directories and members are
also no-follow. Exact file sets, regular-file types, member counts, individual
sizes, and aggregate sizes are checked before reads/materialization. Relative
paths and standard macOS temporary-directory aliases work; final-root,
ancestor, and member symlinks remain rejected.

Snapshot capabilities defensively copy their byte maps, recompute hashes,
enforce exact field/key/value types, member/count/manifest/aggregate caps, and
are revalidated at the independent-verifier boundary. This closes forged
cached hashes, hidden members, mutable aliases, deceptive equality objects,
and exceptional mapping wrappers. FIFO, directory, socket, character-device,
missing, extra, and symlink substitutions fail closed without blocking.

## TDD record

The first collision-evidence integration test was written before its production
module. Its initial focused run failed with
`ModuleNotFoundError: No module named 'rigid.collision_evidence'`; after the
tracer implementation and recovery of the interrupted files, that exact test
passed (`1 passed`).

Subsequent preserved RED states included:

- missing independent verifier module, then `1 passed`;
- missing `write_collision_evidence`, then publication GREEN;
- invalid `generate-collision` argparse choice, then CLI GREEN;
- relative root traversal attempting `private` below the current directory;
- a replaced cached sidecar hash returning `valid=True`;
- deceptive equality accepting a non-string hash; and
- an exceptional mapping escaping the verifier instead of returning invalid.

Each failure was reproduced by a focused regression before its implementation
change. The final focused collision/CLI/oracle selection passed
`101 passed, 1 skipped in 15.19s`; the skip was the unprivileged macOS sandbox's
Unix-domain-socket creation restriction. The authoritative full gate ran that
case successfully.

## Independent adversarial reviews

The computational-geometry review found no P0/P1 geometry defect. It added a
stronger import-independence guard and explicit regressions for nonfinite,
duplicate, degenerate, nonconvex, nonplanar, malformed, and noncoplanar
point/edge-tangency cases. Its read-only probes passed:

- 20,000 randomized intersection-commutativity cases;
- 99,805 randomized noncoplanar cases against an independent edge/plane
  reference;
- 520 randomized coplanar cases against an independent 2D reference; and
- 500 randomized sweep-versus-exhaustive broad phases.

The artifact/security review found two P1 issues: forgeable cached snapshot
fields at the public snapshot verifier, and broken relative-root traversal with
a final-root symlink race. Sealing/revalidation, cap parity, canonical-parent
descriptor traversal, final-component no-follow, and focused hostile-capability
tests fixed both. A follow-up review found the deceptive equality edge case;
exact types and fail-closed reconstruction fixed it. The final recheck reported
no remaining P0/P1 finding.

The CCD review confirmed that Phase-3 evidence does not authorize continuous
collision freedom. CLI/report summaries were amended to expose scope and CCD
status next to every claim status.

## Compatibility

The Phase-3 read-only worktree remained clean at exact
`354d238d1fb14e961c99baa0d7eba6fbbf5350bb`. Compiling the same representative
specification with Phase-3 and Phase-4 code produced the same nine-path set and
byte-identical content for every Phase-3 artifact. The existing frozen Phase-3
hash-vector tests also pass. Phase-3 `certificate.json` continues to serialize
`collision.status=not_run`; the new claim exists only in its separate sidecar.

No public Pydantic schema source or generated schema changed. User-authored
schema remains `0.1.0`; Phase-1/2 profiles, Phase-3 bundle-v2 verification, and
legacy `verify`/`inspect` behavior remain compatible.

## Final verification

Runtime:

- macOS `15.6`, arm64;
- CPython `3.14.3`;
- NumPy `2.4.3`;
- SciPy `1.17.1`; and
- Pydantic `2.13.4`.

Final commands and results:

| Gate | Result |
|---|---|
| complete rigid suite with `-W error` | `590 passed, 1 skipped in 29.59s` |
| `make PYTHON=<repo>/mcp_harness/.venv/bin/python test` | `1211 passed, 9 skipped in 542.34s` |
| oracle regenerate + `cmp` | byte-identical |
| hash seeds `0`, `1`, `8675309` | `30 passed` for each seed |
| `python -m compileall -q mcp_harness/rigid mcp_harness/tests` | passed |
| `git diff --check` for worktree and Phase-3-to-Phase-4 range | passed |
| public schema diff from exact Phase-3 base | empty |
| Phase-3 representative generated-byte comparison | all 9 paths byte-identical |

The exact committed-suite and artifact commands were:

```text
PYTHONPATH=. <repo>/mcp_harness/.venv/bin/python \
  -m pytest \
  mcp_harness/tests/test_rigid_collision_evidence.py::test_compile_collision_evidence_postprocesses_verified_phase3_without_mutation \
  -q -p no:cacheprovider

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=mcp_harness \
  <repo>/mcp_harness/.venv/bin/python \
  -m pytest mcp_harness/tests/test_rigid_*.py \
  -q -p no:cacheprovider -W error

make PYTHON=<repo>/mcp_harness/.venv/bin/python test

<repo>/mcp_harness/.venv/bin/python \
  mcp_harness/tests/fixtures/generate_rigid_phase4_collision_oracle.py \
  --output /private/tmp/rigid-phase4-oracle.zXFjdb/rigid_phase4_collision_oracle_v1.json

cmp mcp_harness/tests/fixtures/rigid_phase4_collision_oracle_v1.json \
  /private/tmp/rigid-phase4-oracle.zXFjdb/rigid_phase4_collision_oracle_v1.json

for phase4_seed in 0 1 8675309; do
  PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED="$phase4_seed" \
    PYTHONPATH=mcp_harness \
    <repo>/mcp_harness/.venv/bin/python \
    -m pytest \
    mcp_harness/tests/test_rigid_collision_geometry.py \
    mcp_harness/tests/test_rigid_phase4_collision_oracle_fixture.py \
    -q -p no:cacheprovider -W error
done

PYTHONPYCACHEPREFIX=/private/tmp/rigid-phase4-pycache \
  PYTHONPATH=mcp_harness \
  <repo>/mcp_harness/.venv/bin/python \
  -m compileall -q mcp_harness/rigid mcp_harness/tests

git diff --check
git diff --check 354d238d1fb14e961c99baa0d7eba6fbbf5350bb..HEAD
git diff --exit-code \
  354d238d1fb14e961c99baa0d7eba6fbbf5350bb..HEAD \
  -- mcp_harness/schemas mcp_harness/rigid/schema.py
```

The cross-worktree byte check constructed the same Phase-4 test specification
in isolated subprocesses with `PYTHONPATH` set respectively to the Phase-3 and
Phase-4 `mcp_harness` roots, decoded both `compile_miura(..., samples=3)`
artifact maps, asserted equal path sets, and compared every byte. It first
confirmed the Phase-3 worktree HEAD with:

```text
git -C <repo>-rigid-phase3 \
  rev-parse HEAD
```

Web and frontend code/shared interfaces were untouched, so their conditional
gates were not rerun. GitHub Actions remains externally unavailable because of
the repository owner's billing/spending limit; its zero-step result must not be
treated as a code failure.

The local authority is macOS arm64. Exact rational and canonical byte logic is
platform-independent by design, but Ubuntu descriptor semantics, native-build
integration, and cross-platform byte identity remain residual verification for
CI when the external billing block is lifted.

## CCD decision, limitations, and next slice

Interval CCD remains honestly `not_run`. Phase 3 serializes accepted roots,
tangents, corrector evidence, and endpoint face poses, but not a certified
continuous parameter or interval enclosure between those states. Its
pseudo-arclength is accumulated solver step, not a proof that every interior
root and pose lies in a known tube. Linear interpolation of exported vertices,
poses, or fold angles would invent a different motion.

Phase 4B should add a separately versioned, independently verified continuous-
motion sidecar containing:

- a certified interval parameter and ordered branch coverage;
- unique-root/branch isolation per segment;
- outward-rounded state, rotation, and face-pose enclosures;
- swept AABBs and conservative vertex-face/edge-edge inclusion predicates;
- legal-topology, grazing, and coplanar semantics;
- deterministic subdivision, work caps, and inconclusive termination; and
- independently replayed first-contact brackets.

That sidecar can bind the frozen Phase-3 hashes without mutating Phase-3 bytes.
Until such authority exists, the committed endpoint-clear/interior-collision
fixture remains a gate against accidental endpoint-only CCD overclaim.

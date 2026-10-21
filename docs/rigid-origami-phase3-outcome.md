# Rigid-origami Phase 3 outcome: deterministic multi-vertex global continuation

**Status:** Accepted — gates M1–M6 pass  
**Date:** 2026-07-18  
**Branch:** `codex/rigid-origami-phase-3-multivertex-continuation`  
**Pushed branch:** `origin/codex/rigid-origami-phase-3-multivertex-continuation`  
**Current-main baseline:** `2886e8116f961a286697a907e3fe87500e4bb5a3`  
**Current-main integration:** `git merge --no-edit origin/main` returned `Already up to date`  
**Pull request:** [#45](https://github.com/raphaeldchen/origami-design-ide/pull/45) — ready

Phase 3 establishes the first deterministic global rigid-origami continuation
authority in the repository. It compiles bounded multi-vertex Miura sheets,
keeps every independent dual cycle including normalized translation, follows a
selected one-degree-of-freedom branch with Keller pseudo-arclength continuation,
exports static FOLD samples, and publishes a content-addressed bundle whose
mathematics is independently replayed from disk.

The work stayed in the dedicated
`AI-Driven-Origami-IDE-rigid-phase3` worktree. The original checkout and the
Phase-2 worktree were not used for Phase-3 mutations. Public schema `0.1.0` and
all Phase-2 artifact bytes remain unchanged.

## Accepted claim

For the generated bounded Miura family, accepted non-flat trajectories:

- form one connected, consistently wound, no-cut, no-hole sheet;
- share one canonical hinge and fold variable across adjacent vertices;
- close every deterministic independent dual cycle in full normalized `SE(3)`;
- have analytic residual Jacobians that agree with an independent five-point
  derivative and exhibit finite nullity one away from singular states;
- follow one oriented branch through deterministic predictor/corrector steps,
  retries, reverse replay, and checkpoint restart without root switching;
- propagate globally consistent reference-to-folded face poses;
- export strict static FOLD 1.2 crease-pattern and folded-form frames; and
- carry canonical hashes, rank evidence, corrector evidence, and certificate
  summaries independently recomputable from serialized artifacts.

The scope is `ideal_zero_thickness_kinematics`. Collision, continuous collision
detection, self-contact, layer order, thickness, elasticity, forces, stiffness,
fabrication, inverse design, and global physical-realizability proofs are not
evaluated. Collision and flat endpoint remain `not_run`; layer order remains
`not_requested`.

## End-to-end flow

```text
MiuraDesignSpec (schema 0.1.0)
  -> normalized design.json
  -> bounded deterministic RigidMechanismGraph
  -> half-edge topology + lexicographic dual tree/cycles
  -> analytic non-flat Miura seed and durable branch ID
  -> full normalized SE(3) cycle residual and analytic Jacobian
  -> SVD rank/nullity and independent five-point audit
  -> Keller predictor + augmented-SVD Newton/Armijo corrector
  -> local closure + global closure + face-pose evidence per sample
  -> reference.fold + frames/sample-NNNN.fold
  -> continuation.json
  -> honest schema-0.1.0 certificate.json
  -> rigid-artifact-bundle-v2 bundle.json
  -> independent bounded offline verification and CLI inspect/verify
```

The CLI surface is:

```text
python -m rigid.cli compile-miura spec.json --output out/
python -m rigid.cli verify out/
python -m rigid.cli inspect out/
```

Publication retains the Phase-2 atomic no-replace behavior. Identical output is
an idempotent no-op; differing existing output, symlinks, special files, unsafe
paths, extra/missing members, malformed JSON, resource-limit violations, and
verification failures fail closed.

## Bounded Miura authority

Rows and columns count faces, not vertices or unit cells. The supported minimum
is 2 face rows by 3 face columns; the next committed authority is 3 by 4.
Reference vertices are a staggered parallelogram grid in millimetres with
deterministic row/column IDs. Faces are CCW quadrilaterals. Boundary segments
are `B`; shared transverse and longitudinal creases carry canonical hinge IDs,
left/right face ownership, assignments, and one fold variable.

| Patch | Vertices | Faces | Edges | Hinges | Interior degree-4 vertices | Independent cycles |
|---|---:|---:|---:|---:|---:|---:|
| minimum 2x3 | 12 | 6 | 17 | 7 | 2 | 2 |
| larger 3x4 | 20 | 12 | 31 | 17 | 6 | 6 |

The minimum cycle lengths are 4 and 6 hinges; the longer cycle has no common
grid vertex and therefore exercises nonconcurrent-axis translation. The larger
cycle lengths are 4, 6, 8, 4, 6, and 8. Face, edge, hinge, vertex, spanning-tree,
cycle, and variable orders are lexicographic and stable. Face `face:r000:c000`
is fixed.

The analytic Miura branch uses one transverse base angle `tau` and the frozen
parity relations

```text
T(r,c) = (-1)^(c-1) tau
tan(L(r,c)/2) = (-1)^(r+c) cos(gamma) tan(tau/2)
```

Both travel signs share a direction-neutral `miurab:<sha256>` branch identity.
Traversal direction is part of the direction-specific
`miurac:<sha256>` continuation identity. Reflection, cyclic/reindexed semantic
mappings, sign reversal, traversal reversal, alternate spanning trees/cycle
bases, and uniform scale are covered explicitly rather than treated as
unrecorded equivalences.

## Full SE(3) residual and Jacobian

For each directed fundamental cycle `c`, serialized reference hinge lines define
twists and the ordered product

```text
G_c(rho) = product_i Exp(epsilon_i rho_i xi_i^)
```

with `epsilon_i` fixed by cycle direction. If `G_c=(R_c,t_c)`, the six retained
residual coordinates are

```text
phi_c = Log_SO3(R_c)
F_c(rho) = [phi_c, J_l(phi_c)^(-1) t_c / L]
```

where `L=max(edge_a_mm, edge_b_mm)` is the characteristic length. No
translational row is dropped. The logarithm uses audited near-identity series
and rejects the principal rotation cut.

The analytic Jacobian differentiates ordered transform products with prefix
adjoints and the inverse left-Jacobian derivative. Columns are ordered by
canonical hinge ID. Verification separately reconstructs cycles and uses a
fixed five-point stencil with `h=1e-4 rad`; it does not import the production
Miura generator, global residual/Jacobian builder, continuation solver, pose
propagator, or FOLD writer.

Rank evidence uses SVD with
`max(1e-10, 1e-8*sigma_max)` and records all singular values, threshold, rank,
nullity, and effective condition number. Regular accepted states have rank 6,
nullity 1 for 2x3 and rank 16, nullity 1 for 3x4. Exact flat is intentionally
classified singular; the minimum flat Jacobian has rank 4 and nullity 3.

## Deterministic continuation policy

Given a regular point `x_k`, oriented unit null tangent `z_k`, and step `h`, the
predictor and Keller normal plane are

```text
x_p = x_k + h z_k
g(x) = z_k dot (x - x_p) = 0.
```

The corrector applies thresholded-SVD augmented Newton to `[J; z_k^T]` with
deterministic Armijo halving. It never forms normal equations. The frozen
defaults are equation `1e-10`, arclength `1e-12`, update `1e-12`, initial step
`0.04`, minimum `1e-6`, maximum `0.10`, 20 Newton iterations, 8 retries, 12
line-search halvings, correction tube `0.5h`, minimum tangent alignment
`cos(45 deg)`, growth `1.25`, shrink `0.5`, and inclusive binding margin
`1e-8 rad`.

Restart recomputes residual, Jacobian, rank, and the null tangent; a stored
tangent can orient but cannot replace the recomputed null vector. Exact reverse
replay is a separate trusted path that uses negated recorded parent tangents and
recorded step sizes to recreate the original Keller planes.

Events are `binding`, `flat_singular`, `rank_loss`,
`bifurcation_candidate`, `log_cut`, `branch_jump`, `corrector_failure`, and
`nonfinite`. There is no automatic branch switching. A committed unit-circle
fixture crosses a driver-coordinate turning point. Checkpoint/restart is exact,
and forward/reverse Miura state replay differs by at most the recorded float64
roundoff below.

Published accepted correctors are independently rerun with a five-point
Jacobian. Near-binding predictor retries serialize unevaluated equation/update
norms as JSON `null`, not infinity or a false zero. The bounded published retry
scope independently recognizes predictor-binding failures and verifies every
recorded field before accepting the later corrected step. The 179.8-degree
regression freezes steps `0.04 -> 0.02 -> 0.01`, two binding failures, and one
accepted attempt.

## Artifact, FOLD, and certificate boundaries

The implementation profiles are:

- `rigid-miura-continuation-v1`;
- `rigid-miura-static-fold-v1`; and
- `rigid-artifact-bundle-v2`.

Bundle v2 contains `design.json`, `mechanism.json`, `reference.fold`, one
`frames/sample-NNNN.fold` per sample including seed `sample-0000`,
`continuation.json`, `certificate.json`, and `bundle.json`. The sample count is
restricted to 1 through 257 including the seed.

`continuation.json` binds design/mechanism/reference hashes, formula and branch,
ordered variables/cycles, characteristic length and bounds, full policy,
state/tangent/arclength, predictors, attempts, corrector evidence,
local/global/pose evidence, Jacobian hashes and rank, ordered FOLD hashes, and
events. Sample IDs hash all accepted evidence. Certificate IDs retain the exact
Phase-2-compatible formula

```text
cert: + SHA256_UTF8(mechanism_hash + "\n" + continuation_hash)
```

with no terminal newline.

Static FOLD output is FOLD 1.2 in millimetres. Reference output is 2D
`creasePattern`; samples are explicit 3D `foldedForm`. Boundary angles are zero;
positive radians become `V` and positive degrees, negative radians become `M`
and negative degrees. Standard and `ro:*` arrays are aligned to stable IDs and
strictly normalized. No multi-frame animation, collision, contact, layer-order,
cut, join, or simulator verdict is implied.

Public Pydantic schema source and generated JSON remain unchanged at `0.1.0`.
Detailed half-edge, cycle, continuation, pose, FOLD, and bundle evidence remains
in versioned implementation artifacts. This avoids a schema change for evidence
that is not a new user-authored source construct or public certificate claim.

## Independent numerical evidence

The oracle generator imports no production `rigid` module. It uses mpmath at
100 decimal digits, independently constructs both patches, evaluates Miura fold
relations and ordered transforms, differentiates the residual with a five-point
stencil, supplies a translation-only cycle anchor, freezes a circle turning
point, and emits independent static FOLD arrays.

The following maxima were recomputed after adversarial hardening across the two
committed patches, both signs, three oracle magnitudes (`0.2`, `0.4`, `0.65`
rad), and six five-sample forward/reverse bundle cases:

| Measurement | Observed maximum |
|---|---:|
| reference vertex component / Euclidean error | `1.4210854715202004e-14 / 1.5888218580782548e-14 mm` |
| hinge-axis point / unit-direction component error | `1.4210854715202004e-14 mm / 1.1102230246251565e-16` |
| production fold angle vs 100-digit oracle | `5.551115123125783e-17 rad` |
| cycle-transform entry vs 100-digit oracle | `1.1934897514720433e-15` |
| full oracle-state SE(3) residual component | `1.1934897514720433e-15` |
| analytic Jacobian vs oracle matrix | `6.661338147750939e-16` |
| local closure rotation | `2.2673290089981854e-16 rad` |
| global cycle rotation | `2.371089188857353e-16 rad` |
| normalized cycle translation | `1.4994434357713061e-15` |
| analytic vs fixed five-point Jacobian | `4.450925739085676e-12` |
| face-isometry error | `9.947598300641403e-14 mm` |
| pose determinant / orthogonality error | `6.661338147750939e-16 / 6.661338147750939e-16` |
| shared hinge endpoint / shared vertex gap | `2.0097183471152322e-13 / 2.0097183471152322e-13 mm` |
| world hinge-axis unit-vector gap | `3.969863087459981e-15` |
| corrector equation infinity norm | `1.4849232954361469e-15` |
| corrector normal-plane error | `1.4371608016063714e-17` |
| corrector final update infinity norm | `1.687623255130347e-15` |
| corrector predictor-to-root correction | `5.4461878187254456e-05` |
| reverse replay state difference | `9.575673587391975e-16 rad` |
| checkpoint/restart | exact dataclass and byte identity |
| reference FOLD vertex vs oracle | `1.4210854715202004e-14 mm` |
| folded FOLD vertex component / Euclidean error | `5.684341886080802e-14 / 5.826883674891095e-14 mm` |
| FOLD degree angle vs oracle | `3.552713678800501e-15 deg` |
| radians-degrees-radians round trip | `2.7755575615628914e-17 rad` |
| strict FOLD normalized byte delta | `0` |

Across the six five-sample cases, rank spans 6 through 16 only because the two
patches have different variable counts; nullity is exactly 1 throughout.
Effective retained condition numbers range from `16.190930255234086` to
`95.18690638386715`. The minimum retained singular value is
`0.0781392975858139`; the maximum null singular value is
`5.873219052067894e-16`.

The independent translation-only anchor closes rotation exactly while retaining
normalized translation `sqrt(2)` from `(0,-1,1)`, proving that translation is a
real verdict quantity rather than a serialized zero.

## Fixture and artifact hashes

| Artifact | SHA-256 |
|---|---|
| independent generator | `659f0c6431f048187b95cdd5e56bf7b94df333212924c992900be094d24f15c8` |
| independent fixture | `d73af0d463727f9f25d75365c36d8e8c5019bfa988ab2e7addbe99c6e53b679c` |
| independent reference FOLD projection | `sha256:0efc8f770dd1e30cf5fd9f7b7bcd42f58cb2958c619b0c8582370eb890c221e0` |
| independent folded sample projection | `sha256:26052a2c8b2e52590c4f35e4291665464fdbd225afa9cc7e97aaf6b807edfc88` |

The representative three-sample bundle vector after hardening is:

| Member | Content hash |
|---|---|
| `design.json` | `sha256:1e001b1b544bd82cbdcbda745d96aecc83b87e2c493f134dc77dc89f9c22020f` |
| `mechanism.json` | `sha256:b432e0e99a3162af60ac327f37cbe2ca1f0d07e6dc6cd0cab92fd7b9daf15a46` |
| `reference.fold` | `sha256:ef8ef785390f7dc698b4cd3c6a5f1067dfa41c6efa07d08fd23e240dcfd34276` |
| `frames/sample-0000.fold` | `sha256:ad0aa8d8b7f99d26a86ab3594453bccd7a87e2ec6ef954cd4dfcc81ab3a10813` |
| `frames/sample-0001.fold` | `sha256:ab913bc985842a6b9e2159fc2c157eb01d957d057ddab99c8ede3cbce921631e` |
| `frames/sample-0002.fold` | `sha256:6316febf1261d4343497aed2e772e4306d6ccd2ad159bbb2b16d6f8c32ebd92d` |
| `continuation.json` | `sha256:d9d8687e2bc622e45fe9899340ba7c4cb705cbc70345dbb0e7e4f139d64d8883` |
| `certificate.json` | `sha256:02e5a8044d06e799ca4ec8998efa921ee318d4c2731df2730286c4f595e013c6` |
| `bundle.json` | `sha256:05282f819d7961a7899a8f1ed6d733a9490d61b7baafc826eb29e96933ba4683` |

The vector is identical under `PYTHONHASHSEED=0`, `1`, and `8675309`.
Representative five-sample bundle hashes are:

| Case | Bundle hash |
|---|---|
| minimum positive forward | `sha256:22ff65c595af7c28d947a7cbc6029473093922ec9999dad96f8825c858e4c1a3` |
| minimum negative forward | `sha256:e024027e0efc8c1687d9ab6cf44991e38592dbcaaccea991d1eb2c928d908d88` |
| minimum positive reverse | `sha256:31f51416c2549b2bedf1f908d5b4390c2d422e53ed5b6de20317f19c8a109589` |
| larger positive forward | `sha256:95711aa08999aa1f836fec3b2f82c3a0b2e1645f0953c4c4aa9c67df9fb0c069` |
| larger negative forward | `sha256:ddda3effc61d466c2a734d0d0fb8490197b8ff48418c0be5a611e8a62398a5ee` |
| larger positive reverse | `sha256:e1fe39d6fded33064357ba2f92ba28ea5c705d2a79da421ef78f70f98fb50e79` |

## Adversarial review closure

Independent review found and the implementation closed, with regressions:

- CI installed NumPy 2.4.6 and omitted mpmath even though oracle bytes bind
  NumPy 2.4.3 and mpmath 1.3.0; CI now installs the rigid requirements file and
  the regression binds workflow and fixture metadata to those exact pins.
- Fully rehashed accepted-corrector iteration and norm forgeries passed; the
  verifier now independently reruns the five-point Newton/Armijo corrector and
  recomputes endpoint residual, correction, arclength, update, iteration, and
  halving evidence.
- Restart allowed a merely aligned but non-null checkpoint tangent to alter the
  predictor and Keller plane; restart now uses the recomputed null tangent,
  with 1-degree and 30-degree perturbation regressions.
- A valid 179.8-degree near-binding trajectory retried successfully in memory
  but could not serialize infinity-valued unevaluated evidence; failures now use
  explicit nulls and the verifier independently replays both binding retries.
- Unsafe paths, NULs, symlinks, FIFOs, file-set drift, oversized manifests and
  sample counts, static-FOLD forgery, pose/fold/residual/Jacobian forgery,
  certificate overclaim, and trailing-newline certificate IDs were also probed.

The final targeted independent rerun compiled and verified the 179.8-degree
case, rejected a fully rehashed failed-attempt mutation with
`CONTINUATION_CORRECTOR`, and reported zero remaining P1/P2 findings. The
reviewer's earlier damping observation was closed because this phase selected
the explicitly permitted augmented Newton path; Levenberg damping was not a
separate requirement after that choice.

## Runtime and verification record

Observed environment:

- macOS 15.6 arm64; CPython 3.14.3;
- NumPy 2.4.3; mpmath 1.3.0 at 100 decimal digits;
- Pydantic 2.13.4; jsonschema 4.26.0; pybind11 3.0.4; pytest 9.0.3;
- TreeMaker native extension rebuilt from 50 model sources;
- Oriedita validator 1.1.3 rebuilt;
- Node 25.6.1; npm 11.9.0; Vitest 2.1.9.

Final commands and results:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=mcp_harness <python> \
  -m pytest mcp_harness/tests/test_rigid_*.py -q -p no:cacheprovider -W error
498 passed in 14.46s

make PYTHON=<python> test
1,118 passed, 9 skipped in 542.40s (0:09:02)

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. <python> \
  -m pytest web/tests -q -p no:cacheprovider
40 passed, 1 pre-existing Starlette deprecation warning in 0.49s

npm test
6 files passed; 59 tests passed in 299 ms

npm run build
630 modules transformed; production build passed in 1.72s
(pre-existing >500 kB chunk-size warning)

PYTHONPYCACHEPREFIX=/tmp/rigid-phase3-pycache PYTHONPATH=mcp_harness \
  <python> -m compileall -q mcp_harness/rigid mcp_harness/tests/test_rigid_*.py
exit 0

git diff --check
exit 0

git diff --exit-code origin/main -- mcp_harness/schemas mcp_harness/rigid/schema.py
exit 0
```

The nine full-suite skips are pre-existing opt-in external smoke tests and
experimental handoff cases; none skips Phase-3 authority.

## Changed files

Documentation:

- `docs/rigid-origami-phase3-multivertex-continuation-audit.md`
- `docs/rigid-origami-phase3-outcome.md`
- `docs/superpowers/plans/2026-07-15-rigid-origami-phase3-multivertex-continuation.md`
- `docs/superpowers/specs/2026-07-15-rigid-origami-phase3-multivertex-continuation-design.md`

Production and CI:

- `.github/workflows/ci.yml`
- `mcp_harness/rigid/cli.py`
- `mcp_harness/rigid/compiler.py`
- `mcp_harness/rigid/conventions.py`
- `mcp_harness/rigid/kinematics/__init__.py`
- `mcp_harness/rigid/kinematics/continuation.py`
- `mcp_harness/rigid/kinematics/global_closure.py`
- `mcp_harness/rigid/kinematics/miura_trajectory.py`
- `mcp_harness/rigid/miura_compiler.py`
- `mcp_harness/rigid/miura_fold.py`
- `mcp_harness/rigid/patterns/__init__.py`
- `mcp_harness/rigid/patterns/miura.py`
- `mcp_harness/rigid/requirements.txt`
- `mcp_harness/rigid/topology.py`
- `mcp_harness/rigid/validation/__init__.py`
- `mcp_harness/rigid/validation/dispatch.py`
- `mcp_harness/rigid/validation/miura_bundle.py`

Independent fixtures and tests:

- `mcp_harness/tests/fixtures/generate_rigid_phase3_oracle.py`
- `mcp_harness/tests/fixtures/rigid_phase3_oracle_v1.json`
- `mcp_harness/tests/test_rigid_cli.py`
- `mcp_harness/tests/test_rigid_continuation.py`
- `mcp_harness/tests/test_rigid_conventions.py`
- `mcp_harness/tests/test_rigid_global_closure.py`
- `mcp_harness/tests/test_rigid_miura.py`
- `mcp_harness/tests/test_rigid_miura_bundle.py`
- `mcp_harness/tests/test_rigid_miura_compiler.py`
- `mcp_harness/tests/test_rigid_miura_fold.py`
- `mcp_harness/tests/test_rigid_miura_trajectory.py`
- `mcp_harness/tests/test_rigid_phase3_oracle_fixture.py`

No TreeMaker source, Oriedita source, MCP tool, prompt, frontend source,
simulator, Phase-1/2 mathematical authority, or public schema was changed.

## Commit record

- `583145b` — freeze the Phase-3 audit, design, and plan;
- `a779545` — freeze independent high-precision authorities;
- `d85f55f` — compile bounded multi-vertex Miura topology;
- `5968115` — add global `SE(3)` residual and analytic Jacobian;
- `e9bf2da` — continue deterministic Miura branches;
- `09ba23b` — publish and independently verify Miura bundles;
- `7b94589` — close adversarial CI, restart, corrector, and retry findings;
- this outcome commit — record the Phase-3 outcome and publication evidence.

`origin/main` remained at `2886e81`; after a fresh fetch, the required merge
reported `Already up to date`, so no synthetic integration commit was created.

## Interrupted-agent recovery

The resumed implementation found the worktree clean at `583145b`; no
uncommitted production edit had survived or needed guessing. Two inherited
research workers (Carver and Huygens) and one fixture worker had been interrupted
by the earlier task crash before returning usable output. Their read-only
analysis was reconstructed from the committed audit/spec/plan and the oracle
fixture was rebuilt test-first; no repository edits were lost. The first final
adversarial reviewer (Ptolemy) was stopped by an automated classifier before it
could inspect code and made no edits. A replacement reviewer completed the full
audit and two targeted closure reruns. These interruptions caused review work to
be repeated, not source changes to be recovered.

## Known limitations

- Only deterministic bounded Miura sheets with at least 2x3 faces are compiled;
  arbitrary user-authored topology and broader origami families are unsupported.
- Automatic bifurcation branch switching is deliberately absent. Rank loss and
  bifurcation candidates stop or classify; they do not select a new root.
- Exact flat is singular and cannot receive a passing non-flat trajectory claim.
- The continuation bounds and principal-log cut are numerical authority within
  the frozen policy, not a symbolic proof of every branch boundary.
- Published failed retry replay is intentionally bounded to independently
  recognizable predictor-binding failures before a later accepted corrector;
  other terminal failure kinds remain kernel events rather than successful
  bundle history.
- Static FOLD frames are interoperable snapshots, not a multi-frame animation
  or a promise that third-party consumers preserve custom semantic IDs.
- Content hashes provide deterministic integrity, not signatures or
  authentication against an attacker able to rewrite every artifact and link.
- Atomic publication requires the audited macOS or Linux no-replace primitive;
  unsupported platforms fail closed.
- There is no collision/CCD, self-contact, layer ordering, thickness, material,
  force, stiffness, fabrication, simulator-verdict, MCP, prompt, or frontend
  integration in this phase.

## Recommended next vertical slice

Add a separate collision-evidence stage for the already certified bounded Miura
trajectory: broad-phase face-pair pruning, exact discrete sample intersection,
then interval CCD only after independent fixtures exist. Keep collision outside
the kinematic authority and certificate it as its own `not_run/pass/fail` stage.
That produces the next honest vertical slice without widening topology,
switching bifurcation branches, or conflating zero-thickness compatibility with
physical non-self-intersection.

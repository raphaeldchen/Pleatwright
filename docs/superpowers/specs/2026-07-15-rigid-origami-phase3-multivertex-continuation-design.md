# Phase 3 rigid-origami multi-vertex continuation design

**Status:** accepted for implementation  
**Date:** 2026-07-15  
**Audit:** `docs/rigid-origami-phase3-multivertex-continuation-audit.md`

## Goal

Compile the existing `MiuraDesignSpec` into a deterministic finite connected
sheet, continue its selected regular one-degree-of-freedom branch using global
`SE(3)` cycle equations, and publish independently verifiable static FOLD
samples and numerical evidence.

The architecture is a vertical slice with four deep boundaries:

```
Miura source -> mechanism/topology -> SE(3) system -> continuation
      |                |                    |              |
      +----------------+--------------------+--------------+
                               |
                        artifacts/certificate
                               |
                       independent disk verifier
```

## Compatibility decisions

- Public schema stays `0.1.0`.  `MiuraDesignSpec` is the intended source
  family; `RigidMechanismGraph` is already multi-vertex; the certificate stays
  a summary.  Rich step evidence lives in `rigid-miura-continuation-v1`.
- Phase-2 `compile_degree4`, bundle v1, FOLD output, verifier semantics, and
  frozen hashes remain unchanged.
- Phase 3 adds sibling compiler/writer/verifier modules and dispatches by
  bundle profile.  It does not widen a Phase-2 profile in place.
- NumPy remains the only numerical array dependency.  No SciPy optimizer,
  autodiff package, simulator, or legacy folding module becomes authority.

## Module ownership

### `rigid.patterns.miura`

Owns only finite reference geometry and the analytic branch seed.

Public immutable results:

```python
@dataclass(frozen=True)
class MiuraBranch:
    branch_id: str
    formula_version: str
    variable_ids: tuple[str, ...]
    driver_hinge_id: str
    base_transverse_angle_rad: float
    fold_angles_by_hinge: Mapping[str, float]

def miura_branch_key(spec: MiuraDesignSpec) -> str: ...
def compile_miura_pattern(spec, *, design_spec_hash: str) -> RigidMechanismGraph: ...
def analytic_miura_seed(spec, graph) -> MiuraBranch: ...
```

Rows/columns count faces.  Supported dimensions are `R>=2,C>=3`.  Coordinates,
IDs, winding, orientation, fixed face, formula parity, and angle exclusions are
exactly those frozen in the audit.  The implementation builds all faces first,
derives unique grid edges and incidence, computes left/right from cross
products, then derives the lexicographic tree and one fundamental cycle per
omitted hinge.  It validates the full graph and never repairs input.

The topology invariant is strengthened: omitted tree hinge IDs and serialized
cycle omitted IDs must be a bijection.  This closes the Phase-2 multi-cycle gap
without changing valid Phase-2 behavior.

### `rigid.kinematics.global_closure`

Owns a precomputed immutable global closure system.  System creation validates
the graph/topology once; evaluations allocate only transform/Jacobian arrays.

```python
@dataclass(frozen=True)
class DirectedCycle:
    id: str
    hinge_ids: tuple[str, ...]
    directions: tuple[TravelDirection, ...]
    omitted_hinge_id: str

@dataclass(frozen=True)
class GlobalClosureEvaluation:
    residual: NDArray[float64]
    jacobian: NDArray[float64]
    cycle_transforms: tuple[tuple[float, ...], ...]
    rank: RankDiagnostics

@dataclass(frozen=True)
class GlobalClosureSystem:
    variable_ids: tuple[str, ...]
    residual_ids: tuple[str, ...]
    cycles: tuple[DirectedCycle, ...]
    characteristic_length_mm: float
    lower_bounds: tuple[float, ...]
    upper_bounds: tuple[float, ...]

    def residual(self, fold_angles) -> NDArray[float64]: ...
    def jacobian(self, fold_angles) -> NDArray[float64]: ...
    def evaluate(self, fold_angles) -> GlobalClosureEvaluation: ...

def build_global_closure_system(graph, topology, *, spanning_tree_hinge_ids=None): ...
```

Alternative trees are validated as connected acyclic face trees and generate
their own ordered fundamental cycles; they do not mutate graph serialization.
Variable order is always sorted hinge ID.  Residual ID order is cycle, then
`rx,ry,rz,tx,ty,tz`.

For each cycle the residual is the normalized principal `SE(3)` logarithm
`[phi, J_l(phi)^-1 t / ell]`.  The analytic Jacobian uses product prefixes,
line-twist adjoints, inverse `SO(3)` left Jacobians, and the directional
derivative of that inverse.  All branches use near-zero series and reject
non-finite/log-cut evaluations.

`five_point_jacobian` lives in a separate checking module or test fixture and
must not call the analytic Jacobian.

### `rigid.kinematics.continuation`

Owns a generic, JSON/filesystem-free Keller pseudo-arclength kernel.

```python
class ContinuationSystem(Protocol):
    variable_count: int
    lower_bounds: tuple[float, ...]
    upper_bounds: tuple[float, ...]
    def residual(self, state): ...
    def jacobian(self, state): ...

@dataclass(frozen=True)
class ContinuationPolicy: ...
@dataclass(frozen=True)
class ContinuationAttempt: ...
@dataclass(frozen=True)
class ContinuationSample: ...
@dataclass(frozen=True)
class ContinuationCheckpoint: ...
@dataclass(frozen=True)
class ContinuationEvent: ...
@dataclass(frozen=True)
class ContinuationTrace: ...

def initialize_continuation(system, state, *, orientation_index, orientation_sign, policy): ...
def advance_continuation(system, checkpoint, *, policy, forced_step=None): ...
def trace_continuation(system, checkpoint, *, sample_count, policy): ...
```

The tangent is the unique SVD right-null vector and is oriented by an explicit
driver component or the previous tangent.  Predictor and normal-plane equation
are

```
x_p = x_k + h z_k
g(x) = z_k dot (x-x_p).
```

The corrector uses thresholded-SVD least squares on `[J;z_k^T]`, bounded
Levenberg damping only for intermediate iterates, and deterministic Armijo
halving.  It never forms normal equations.  An accepted endpoint must satisfy
the true residual and arclength equation, regular rank/nullity, branch tube,
tangent alignment, finite/bound guards, and correction-radius policy.

Frozen v1 defaults:

| Item | Value |
|---|---:|
| equation infinity tolerance | `1e-10` |
| arclength absolute tolerance | `1e-12` |
| update infinity tolerance | `1e-12` |
| initial/min/max step | `0.04 / 1e-6 / 0.10` |
| corrector iterations | `20` |
| retries | `8` |
| line-search halvings | `12` |
| Armijo coefficient / reduction | `1e-4 / 0.5` |
| correction tube | `0.5 h` |
| minimum tangent alignment | `cos(45 deg)` |
| growth / shrink | `1.25 / 0.5` |
| binding margin | `1e-8 rad` |

All numeric constants reside in `rigid.conventions`, include a derivation
comment, and have inclusive `<=`/strict `>` boundary tests.  Fast convergence
(`<=4` iterations, no retry/backtrack/damping) grows; slow convergence (`>8`)
shrinks; otherwise the next step is unchanged.  Any retry suppresses growth.

Checkpoint state contains the accepted vector/tangent, next step, cumulative
pseudo-arclength, accepted index, and immutable prior attempt records.  Forced
recorded steps support exact reverse replay.  Restart recomputes residual,
Jacobian, rank, and tangent before proceeding.

Events are `binding`, `flat_singular`, `rank_loss`, `bifurcation_candidate`,
`log_cut`, `branch_jump`, `corrector_failure`, and `nonfinite`.  The
overdetermined Miura adapter may call a nullity increase only a bifurcation
candidate; it cannot claim a verified bifurcation or switch branches.

### `rigid.miura_compiler` and `rigid.miura_fold`

The compiler validates one nonzero driver, branch key/sign, unsupported
constraints/objectives, and canonical runtime.  It builds the graph/system,
checks the analytic seed, runs continuation, validates every accepted pose,
writes static frames, summarizes a `MotionCertificate`, and constructs bundle
v2 bytes in dependency order.

`miura_fold` is a new strict static writer.  It emits generic FOLD 1.2 arrays
from the graph and accepted poses while preserving all Phase-2 field meanings:

- reference: `frame_classes=["creasePattern"]`, 2D coordinates;
- sample: `frame_classes=["foldedForm"]`, explicit 3D coordinates;
- `edges_assignment` is `M/V/B`; `edges_foldAngle` is degrees and sign-matched;
- `edges_faces`, `faces_vertices`, and `faces_edges` preserve canonical graph
  ordering and left/right semantics;
- `ro:*` fields bind design, mechanism, reference, branch, continuation,
  sample index, and pseudo-arclength;
- no animation, inherited frames, cuts, joins, collision, or layer order.

### `rigid.validation.miura_bundle`

The v2 verifier shares only canonical JSON, public schema parsing, immutable
constants, and low-level mathematical definitions.  It must not import:

- `patterns.miura`;
- `kinematics.global_closure`;
- `kinematics.continuation`;
- `kinematics.face_poses`;
- `miura_fold` or `miura_compiler`.

It reconstructs grid expectations directly from serialized design fields,
walks serialized graph arrays, recomputes directed transform products and a
five-point Jacobian, replays SVD/arclength/predictor/corrector evidence, applies
serialized face poses directly, validates FOLD parallel arrays, and checks all
hash links and certificate claims.  Malformed bytes return stable diagnostics,
never an exception.

Bundle verification dispatch reads only canonical `bundle.json.profile`, then
selects frozen v1 or v2 semantics.  Atomic no-replace publication is factored
without changing behavior.

## Artifact contract

Bundle v2 exact files:

```
design.json
mechanism.json
reference.fold
frames/sample-0000.fold ...
continuation.json
certificate.json
bundle.json
```

`continuation.json` exact top-level fields are:

```
profile
design_spec_hash
mechanism_hash
reference_fold_hash
branch
continuation
system
policy
seed
samples
events
```

The `system` freezes variable IDs, residual IDs, tree hinges, directed cycles,
characteristic length, bounds, and normalization.  `seed` freezes analytic
relation identity, state, residual/Jacobian/rank, and tangent orientation.
Each sample freezes parent index, accepted/proposed step, cumulative
pseudo-arclength, state/tangent, predictor, correction and retry evidence,
cycle transforms/residuals, analytic Jacobian hash and rank evidence, pose
maxima, FOLD path/hash.  Arrays are never maps when order carries meaning.

Branch identity is direction-neutral.  Continuation identity hashes design,
mechanism, branch, seed, system, policy, traversal direction, and requested
sample count.  Checkpoint/sample identity additionally hashes its parent and
all accepted evidence.

## Certificate semantics

A passing certificate requires:

- topology preflight and explicit multi-cycle bijection pass;
- every non-flat sample has full global residual within certificate tolerance;
- every Jacobian has expected rank `n-1` and nullity one;
- analytic versus independent five-point maximum error is within policy;
- every pose is a rigid transform and all face/shared-edge/cycle checks pass;
- every FOLD frame round-trips under v2 normalization;
- no unresolved stop event lies inside the requested trace.

`local_kinematics` reports all interior Miura vertices checked, branch ID, and
maximum local rotation closure.  `global_kinematics.max_closure_residual_rad`
remains a rotational scalar by public schema definition; normalized
translation maxima are detailed in the continuation artifact and warnings,
not mislabeled as radians.  Collision and flat endpoint remain `not_run`.

## TDD and independent evidence

Vertical tracer bullets are implemented in this order:

1. minimum reference geometry and exact independent fixture;
2. multi-cycle topology and nonconcurrent cycle;
3. one cycle residual plus separate rotation/translation corruption;
4. one analytic Jacobian column versus five-point anchor, then all columns;
5. manufactured circle predictor/corrector through a coordinate fold;
6. minimum Miura continuation, then larger/reverse/restart paths;
7. one static FOLD frame, then full manifest/bundle/verifier/CLI;
8. adversarial corruption and compatibility matrix.

Each behavior starts with one failing test, receives the smallest production
change, and is refactored only while green.  Fixture generation imports no
production rigid implementation and runs at high precision.

## Rejected alternatives

- Local vertex `SO(3)` equations alone: cannot exercise nonconcurrent
  translational closure.
- Norm residuals: lose sign/direction and are nonsmooth at closure.
- Natural driver continuation: fails at a driver-coordinate fold.
- Finite-difference production Jacobian or autodiff: fails the independently
  derived analytic authority requirement.
- Generic optimizer: obscures branch/rank/corrector evidence.
- Automatic branch switching: explicitly out of scope.
- Extending Phase-2 bundle/FOLD profile in place: would break frozen bytes and
  blur compatibility claims.


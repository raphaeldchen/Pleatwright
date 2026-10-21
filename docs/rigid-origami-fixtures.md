# Rigid origami golden-fixture manifest

**Manifest version:** 0.1.0
**Date:** 2026-07-12

Every numeric golden must be produced by an independent high-precision evaluator,
not by the implementation being tested. Reserved entries have no expected numeric
trajectory until their notation audit is complete.

## Required provenance fields

- fixture ID and schema version;
- source citation/DOI and equation/figure/page;
- source license and code/data license, separately;
- copied bytes (`none` unless explicitly reviewed);
- repository crease/sector/fold mapping;
- derivation/evaluator and its version/hash;
- input parameters and precision;
- expected branch/sign/range/singularities/binding points;
- whether self-contact/intersection is permitted;
- absolute/relative comparison tolerance.

## Phase-0 exact fixtures

### `rot-x-quarter-turn-v1`

- Source: standard active right-handed rotation convention.
- Input: axis `(1,0,0)`, angle `pi/2`, vector `(0,1,0)`.
- Expected: `(0,0,1)` within `1e-12`.
- Copied bytes: none.

### `hinge-positive-valley-v1`

- Source: repository convention mapped to FOLD 1.2 positive-valley sign.
- Axis: `(0,0,0) -> (1,0,0)`.
- Left face: `y > 0`, fixed.
- Fold: `rho = +pi/2`.
- Right point: `(0,-1,0)`.
- Expected: `(0,0,1)` within `1e-12`.
- Invariance: reverse axis and swap left/right without changing physical pose.
- Copied bytes: none.

## Reserved degree-4 fixtures

### `d4-flat-foldable-generic-v1`

- Sectors: `(pi/3, pi/4, 2*pi/3, 3*pi/4)`.
- Expected: two analytic finite modes, both driver signs.
- Source mapping: paper `e1..e4`, `alpha1..alpha4`, and positive-valley
  `rho1..rho4` map directly to repository `e0..e3`, `alpha0..alpha3`, and
  `rho0..rho3` by a one-based-to-zero-based shift.
- Accepted evaluator: `degree4-quaternion-polynomial-v1`, CPython 3.14.3,
  mpmath 1.3.0, 100 decimal digits. It solves the vector part of an unnormalized
  tangent-half-angle quaternion product and independently verifies a Rodrigues
  matrix product. It imports no production rigid module.
- Coverage: driver `e0` at `+/-0.2` and `+/-0.8` rad, both Theorem-1 modes;
  normalized tangent ratios and high-precision closure evidence are committed.
- Validity: non-flat states strictly inside `(-pi,pi)`; zero is the shared
  singular state and `+/-pi` are half-angle binding poles.
- Comparison tolerance: `5e-12` absolute and relative radians.
- Self-intersection: not evaluated in Phase 1.
- Copied bytes: none; mathematics independently implemented from the paper.
- Status: accepted in `mcp_harness/tests/fixtures/rigid_degree4_oracle_v1.json`.

### `d4-general-developable-published-v1`

- Sectors: `(pi/3, pi/2, 3*pi/4, 5*pi/12)`.
- Source: Foschi, Hull, Ku, published example/figure; DOI
  [10.1103/PhysRevE.106.055001](https://doi.org/10.1103/PhysRevE.106.055001).
- Expected: two analytic modes and both travel directions.
- Accepted evaluator and mapping: identical clean-room quaternion/Rodrigues
  process documented for `d4-flat-foldable-generic-v1`.
- Coverage: driver `e0` at `+/-0.2` and `+/-0.8` rad, both durable tangent
  branches; publication mode numbers remain aliases only.
- Validity, tolerance, self-intersection, and copied-byte policy: identical to
  the flat-foldable fixture.
- Status: accepted in `mcp_harness/tests/fixtures/rigid_degree4_oracle_v1.json`.

### `d4-collinear-special-v1`

- Sectors: `(pi/3, 2*pi/3, pi/3, 2*pi/3)`.
- Expected: classify special/collinear and route away from generic formulas;
  document trivial/additional straight-line motions.
- Status: reserved.

### `d4-nondevelopable-planar-negative-v1`

- Sectors: `(pi/3, pi/3, pi/3, pi/3)`.
- Expected: reject planar developability because the sum is `4*pi/3`, not
  `2*pi`.
- Status: parameter-level negative, ready for the degree-4 slice.

### `d4-flat-singularity-v1`

- State: all fold angles zero on the generic fixture.
- Expected first-order observation: generic closure Jacobian rank 2/nullity 2 at
  the singular flat state.
- Required verdict: finite DOF inconclusive at the singular state; do not report a
  two-DOF mechanism.
- Status: reserved for closure/Jacobian implementation.

## Required derived variants

For each accepted positive degree-4 golden, generate cyclic reindexing,
reflection, reverse-travel, and uniform-scale variants. Branch identity and
physical results must remain invariant under the documented mapping.

## Phase-1 independent oracle provenance

```text
generator:
  mcp_harness/tests/fixtures/generate_rigid_degree4_oracle.py
  sha256:7ece25b829215fd2bc2cc12a7b39d835e02b57fb65be39881ed431c57480d977
goldens:
  mcp_harness/tests/fixtures/rigid_degree4_oracle_v1.json
  sha256:99fbaa87defc16c0661427d76c92051b64db758ed775e0711cc7b16d2e54c4d3
```

The JSON records its generator hash, exact versions, decimal precision,
formula shape, primary-source provenance, copied-byte status, and comparison
tolerance. Runtime tests load the committed JSON and do not require mpmath.

## Primary mathematical sources

- [Belcastro and Hull, A Mathematical Model for Non-Flat Origami](https://doi.org/10.1016/S0024-3795(01)00608-5)
- [Foschi, Hull, and Ku, Explicit Kinematic Equations for Degree-4 Rigid Origami Vertices](https://doi.org/10.1103/PhysRevE.106.055001)
- [Abel et al., Rigid Origami Vertices: Conditions and Forcing Sets](https://doi.org/10.20382/jocg.v7i1a9)
- [Tachi, Simulation of Rigid Origami](https://origami.c.u-tokyo.ac.jp/~tachi/cg/SimulationOfRigidOrigami_tachi_4OSME.pdf)

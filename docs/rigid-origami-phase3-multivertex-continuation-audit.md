# Rigid Origami Phase 3: Multi-vertex continuation audit

**Date:** 2026-07-15  
**Branch:** `codex/rigid-origami-phase-3-multivertex-continuation`  
**Base:** merged Phase 2 (`2886e8116f961a286697a907e3fe87500e4bb5a3`)

## 1. Decision and claim boundary

Phase 3 adds one deliberately bounded vertical slice: a finite rectangular
Miura sheet whose parallelogram facets share crease variables, a global
`SE(3)` loop-closure authority, an analytic residual Jacobian, and
deterministic pseudo-arclength continuation.  The result certifies only
ideal, zero-thickness kinematic compatibility for the serialized samples.

It does **not** certify collision freedom, a flat endpoint, layer order,
thickness, elasticity, loads, fabrication, or physical realizability.  Those
checks remain `not_run`; layer order remains `not_requested`.  No simulator,
legacy folding experiment, optimizer, or FOLD consumer is a verdict authority.

Public schema `0.1.0` is sufficient:

- `MiuraDesignSpec` already expresses face-row/column counts, facet edges and
  sector angle, a typed hinge driver, a durable mode signature, and travel sign.
- `RigidMechanismGraph` already expresses a connected sheet, shared vertices,
  faces, oriented hinges, ordered sectors, and independent cycles.
- `MotionCertificate` already contains the honest summary fields needed for
  topology, local/global evidence, rank, nullity, and non-evaluated checks.

Detailed continuation evidence is therefore a versioned implementation
artifact, not a public-schema expansion.  Phase-2 serializers and hashes remain
byte-identical.

## 2. Evidence ledger

| Kind | Accepted statement | Authority |
|---|---|---|
| Sourced | A Miura sheet is a tessellation of congruent parallelogram facets with scale-independent one-parameter rigid kinematics. | Schenk & Guest, *Geometry of Miura-folded metamaterials*, PNAS 110 (2013), doi:10.1073/pnas.1217998110 |
| Sourced | Rigid-origami compatibility can be written as ordered products of hinge rotations around closed loops and differentiated by transformed hinge axes. | Tachi, *Simulation of Rigid Origami*, 4OSME (2009) |
| Sourced | For non-concurrent loops and holes, compatibility has rotational and translational content; local vertex compatibility alone is not generally sufficient. | He & Guest, *On Rigid Origami I*, arXiv:1803.01430 |
| Sourced | Pseudo-arclength augments the governing equations with a local tangent hyperplane and can continue through a fold of a chosen coordinate. | Keller, *Numerical Solution of Bifurcation and Nonlinear Eigenvalue Problems* (1977) |
| Sourced | `SE(3)` composition derivatives use adjoints and left/right Lie Jacobians. | Solà, Deray & Atchuthan, *A micro Lie theory for state estimation in robotics*, arXiv:1812.01537 |
| Sourced | FOLD 1.2 fold angles are degrees, positive valley and negative mountain; each emitted sample may be a self-contained static `foldedForm`. | FOLD specification 1.2 |
| Repository | Internal lengths are mm, angles are radians, fold-positive means valley, transforms are active reference-to-folded transforms on columns, and faces wind CCW in reference `+z`. | `rigid.conventions`, Phase-1 notation audit, Phase-2 topology/FOLD audit |
| Repository | With an oriented hinge and left face fixed, left-to-right crossing is `A(q,u,-rho)` and right-to-left is its inverse. | `rigid.kinematics.rotations` |
| Derived | The bounded coordinates and half-angle relation in section 4 produce one shared fold value per physical crease and close every local Miura vertex. | Phase-3 derivation, independently checked fixtures |
| Numerical | SVD thresholds, continuation stopping rules, damping, retry counts, and event margins are versioned policy rather than mathematical facts. | `rigid.conventions` plus inclusive boundary tests |
| Serialization | Stable IDs, ordered variables/cycles, profile names, and hash-DAG order are deterministic repository choices. | This audit and canonical JSON profile `ro-cjson-1` |
| Deferred | Collision, contact, branch switching, layer order, thickness, forces, stiffness, and arbitrary crease topology. | Explicit Phase-3 scope |

## 3. Miura terminology and supported finite patches

`rows = R` and `columns = C` count **parallelogram faces**, not vertices and
not two-face crystallographic unit cells.  The reference grid therefore has
`(R+1)(C+1)` vertices and `RC` faces.  A local "Miura vertex" means one
interior grid vertex; there are `(R-1)(C-1)` of them.

Phase 3 accepts `R >= 2` and `C >= 3`.  The two committed authorities are:

- minimum acceptance patch: `R=2, C=3`, six faces, two interior degree-4
  vertices, seven hinges, and two independent dual cycles;
- next-larger patch: `R=3, C=4`, twelve faces, six interior vertices,
  seventeen hinges, and six independent dual cycles.

This is a finite, connected, simply bounded sheet.  It has one material
boundary and no cuts, holes, joins, construction edges, or manufactured seams.

Let `a=edge_a_mm`, `b=edge_b_mm`, and `gamma=sector_angle_deg` in radians.
For grid row `r in [0,R]` and column `c in [0,C]`,

```
p(r,c) = (c a + (r mod 2) b cos(gamma), r b sin(gamma)).
```

Face `(r,c)` is the CCW loop

```
(r,c), (r,c+1), (r+1,c+1), (r+1,c).
```

The compiler rejects angles too close to `0`, `pi/2`, or `pi` under the
centralized Miura geometry margin.  The right-angle case is not silently
treated as Miura because its longitudinal folds vanish in the selected mode
and the expected rank changes.

Stable IDs use fixed-width zero-based grid coordinates:

```
vertex:rRRR:cCCC
face:rRRR:cCCC
edge:crease:0-transverse:rRRR:cCCC
edge:crease:1-longitudinal:rRRR:cCCC
hinge:0-transverse:rRRR:cCCC
hinge:1-longitudinal:rRRR:cCCC
edge:boundary:<side>:iIII
cycle:iIII
```

The numeric role prefix is intentional: all transverse dual edges sort before
longitudinal edges.  Kruskal's lexicographic dual tree consequently includes
each face-row chain and the first longitudinal connection between adjacent
rows.  Later omitted longitudinal hinges create progressively wider
fundamental cycles.  On the 2x3 patch the second cycle is nonlocal and its axes
are not concurrent.  `face:r000:c000` is fixed.

Edges are stored eastward for longitudinal segments and from row `r` to
`r+1` for transverse segments.  Left/right incident faces are computed from
the oriented reference geometry, never guessed from indices.  Adjacent faces
share one edge ID, one hinge ID, and one scalar state variable.

## 4. Analytic Miura seed and assignment

Transverse crease `c` means the grid-column crease at `c in [1,C-1]` and is
shared by every face row.  Choose a nonzero base transverse angle `tau` and
travel sign `sigma in {-1,+1}`.  The selected Miura mode is

```
rho_T(r,c) = sigma (-1)^(c-1) tau

tan(rho_L(r,k)/2)
  = sigma (-1)^(r+k) cos(gamma) tan(tau/2),
```

for transverse hinges `(r,c)`, `r in [0,R-1]`, and longitudinal hinges
`(r,k)`, `r in [1,R-1]`, `k in [0,C-1]`.

At an even interior row, the ordered rays are at
`0, gamma, pi, 2pi-gamma`; at an odd interior row they are at
`0, pi-gamma, pi, pi+gamma`.  Substitution into the ordered quaternion product
leaves the vector factor

```
cos(gamma) tan(rho_T/2) + tan(rho_L/2),
```

up to the parity reversals above.  This derives the half-angle relation and is
independently evaluated without production code in the fixture generator.

Assignments are the exact signs of the requested non-flat analytic seed:
positive is `V`, negative is `M`.  Mirrored travel sign negates every fold and
swaps every `M/V` assignment.  The exact flat state has assignment ambiguity
and rank gain; it is a diagnostic singular state, never a certified sample.

The one required `MiuraHingeSelector` selects a role plus its zero-based index
in role-then-grid order.  Its nonzero target fold angle defines the analytic
seed.  The branch request's `driver_sign` must match.  Inverting the relation
for a longitudinal driver is explicit and rejects a zero/ill-conditioned
coefficient.  A branch key hashes the formula profile, patch dimensions,
sector angle, ordered variable roles, and mode parity; the mirrored sign is a
travel orientation on that branch, not a new mode.

## 5. Topology and cycle policy

The Phase-2 half-edge preflight remains authoritative for manifold incidence,
winding, one boundary, hinge sides/axes, sectors, and dual connectivity.  Phase
3 generalizes only diagnostics whose message named Phase 2; it does not weaken
the accepted topology.

The default spanning tree is the lexicographic Kruskal tree over hinge IDs.
For every omitted hinge, the fundamental cycle begins with that hinge,
traversed from its stored right face to its left face, then follows the unique
tree path back to the initial right face.  Cycles are ordered by omitted hinge
ID.  No cycle is reoriented or repaired after serialization.

Residual construction also accepts a caller-supplied valid spanning tree.
Alternative fundamental bases must span the same dual cycle space and produce
the same zero set and Jacobian rank.  Residual vectors themselves may differ by
orientation/basis; evidence compares closure transforms/norms and rank, not
componentwise equality across bases.  Reversing a cycle inverts its closure
transform and preserves zero, rank, and first-order norm at closure.

## 6. Global `SE(3)` residual

For directed cycle `k`, each crossing contributes

```
G_j(rho_j) = A(q_j, u_j, s_j rho_j),
s_j = +1 for right_to_left, -1 for left_to_right.
```

The ordered closure transform is

```
C_k(rho) = G_1 G_2 ... G_m = [R_k, t_k; 0, 1].
```

Let `phi_k = Log_SO3(R_k)`, let `J_l(phi)` be the `SO(3)` left Jacobian, and
let `v_k = J_l(phi_k)^(-1) t_k`.  With characteristic length
`ell=max(a,b)`, the six residual coordinates are

```
f_k = [phi_k, v_k / ell].
```

Stack every cycle in frozen order.  This is the principal `SE(3)` logarithm in
twist order `[rotation, translation]`, with only the translational coordinates
nondimensionalized.  Near identity, series are used.  Near `pi`, the existing
stable deterministic `SO(3)` axis policy applies; continuation stops before
the branch enters the log cut margin.

No translation row is discarded, including for a locally concurrent cycle.
Six rows per cycle are equations, not an assertion of six independent scalar
constraints.  Rank, nullity, conditioning, and retained/null singular values
come from the full stacked analytic Jacobian under centralized absolute and
relative SVD thresholds.  A regular Miura sample must have rank `n-1` for `n`
hinges and measured nullity one.

Uniform positive scale multiplies all `q,t,ell` and leaves the residual and
rank invariant.  A rigid planar reflection plus global fold-sign reversal maps
the same physical branch.  Reindexing changes serialization hashes but a
semantic mapping preserves closure and rank.

## 7. Analytic Jacobian

Variables are ordered by hinge ID.  For a cycle product, an additive change in
factor `j` gives the left-trivialized closure perturbation

```
zeta_j = Ad_(G_1 ... G_(j-1)) [s_j u_j, s_j (-u_j x q_j)].
```

Write `zeta_j=[omega_j, upsilon_j]`.  Then

```
d phi = J_l(phi)^(-1) omega_j
d t   = omega_j x t + upsilon_j.
```

With

```
J_l(phi)^(-1) = I - 1/2 Phi + A(theta) Phi^2,
A(theta) = (1 - theta/2 cot(theta/2)) / theta^2,
```

the directional derivative of `v=J_l(phi)^(-1)t` is evaluated analytically by
differentiating `Phi`, `A(theta)`, and `t`.  Series for `A` and its derivative
cover the near-zero interval.  The final three rows divide by `ell`.

The independent checker is a five-point central difference

```
(-F(x+2h)+8F(x+h)-8F(x-h)+F(x-2h))/(12h),
```

implemented outside the production Jacobian.  It uses a fixed centralized
step, checks finite inputs/outputs, and compares max absolute and scaled error.
Committed anchors and fixed-seed randomized states exercise both patches,
both travel signs, alternate trees, near-identity series, and tolerance
boundaries.

## 8. Pseudo-arclength continuation

The generic kernel solves `F(x)=0` with expected nullity one.  At accepted
state `x_i`, SVD supplies a normalized null vector `z_i`.  The first tangent is
oriented by the selected driver component and requested travel sign; later
tangents are negated when necessary to make `z_i dot z_(i-1) > 0`.

For step `ds`,

```
x_predict = x_i + ds z_i

G(x) = [F(x);
        z_i^T (x - x_predict)] = 0.
```

The corrector uses an explicit thresholded-SVD least-squares Newton step on
`[J(x); z_i^T]`.  A deterministic halving line search must reduce the scaled
augmented norm and remain inside the correction radius.  It is not a generic
optimizer.  Convergence requires residual, arclength, and update tolerances.

Step policy is frozen:

- initial, minimum, and maximum step are versioned options with audited
  defaults;
- at most a versioned Newton count and line-search halving count per attempt;
- a failed attempt halves `ds`; retries are bounded and serialized;
- fast convergence grows the next step by the fixed growth factor, slow
  convergence shrinks it, and all changes clamp to `[ds_min,ds_max]`;
- tangent misalignment, excess correction radius, non-finite evaluation,
  binding, log-cut approach, rank loss, or nullity greater than one are
  structured events, never silent branch switches.

Nullity greater than one is classified `bifurcation`; nullity zero or a lost
augmented rank is `rank_loss`; neither automatically switches branch.  The
flat Miura state is `flat_singular`.  A hinge within the inclusive binding
margin of `+-pi` is `binding`.  Exhausted retries are `corrector_failure`.

Each checkpoint contains the accepted state, oriented tangent, next step,
accepted step index, cumulative arclength, and complete retry history.  Restart
uses those bytes directly.  Concatenated restarted records must be byte-equal
to a single uninterrupted run.

A separate manufactured unit-circle fixture proves passage through a genuine
turning point of the first coordinate; no coordinate is used as a global
parameter.

## 9. Artifacts and hash DAG

Phase 3 introduces, without changing Phase 2:

- `rigid-miura-continuation-v1` continuation manifest;
- `rigid-miura-static-fold-v1` self-contained FOLD sample profile;
- `rigid-artifact-bundle-v2` bundle profile.

Dependency order is

```
design -> mechanism -> reference.fold
                         |
                         +-> ordered static sample FOLD files
design + mechanism + samples + numerical evidence -> continuation.json
mechanism + continuation -> certificate.json
all artifact bytes -> bundle.json
```

The continuation manifest contains design/mechanism/reference hashes, profile,
branch and continuation IDs, seed identity, ordered variables and directed
cycles, options, each accepted tangent/arclength/predictor/corrector record,
residual/Jacobian/rank evidence, event/retry history, face-pose maxima, and
ordered sample paths/hashes.

Every `.fold` remains one static top-level frame.  Reference output is a
`creasePattern`; samples are `foldedForm`; fold angles are degrees with FOLD
positive-valley signs.  No `file_frames`, inheritance, animation, collision,
or layer-order claim is added.  Generic mesh counts replace the Phase-2
degree-4 exact-count profile only in the new writer/verifier.

The offline verifier reads canonical bytes from disk, recomputes the hash DAG,
validates schema/topology independently, recomputes cycle transforms,
five-point Jacobians, SVD evidence, arclength equations, poses, and FOLD arrays,
and validates certificate limits.  It imports no production Miura generator,
global residual/Jacobian builder, continuation solver, pose propagator, or FOLD
writer.  Publication retains Phase-2 atomic no-replace and identical-rerun
behavior.

## 10. Invariance and failure matrix

| Transformation or boundary | Required behavior |
|---|---|
| Cyclic/reindexed IDs with explicit semantic map | geometry, closure zero set, rank, and mapped folds agree; hashes may differ |
| Alternate valid spanning tree/cycle basis | all closure transforms are identity at accepted states; stacked rank/nullity agree |
| Cycle reversal | inverse transform; same closure, rank, and first-order norm |
| Planar reflection plus fold-sign mirror | mapped face poses/closure agree; assignments swap M/V |
| Global fold-sign reversal | opposite travel on same branch key |
| Uniform positive scale | normalized residual/Jacobian and fold path invariant; geometry hashes differ |
| Exact flat | excluded and classified `flat_singular` |
| Near flat outside margin | evaluated with series; rank must still be one-DOF regular |
| Any `|rho| >= pi-margin` | stop with `binding` |
| `SO(3)` log-cut margin | stop; do not cross principal-log ambiguity |
| Corrector non-finite or no descent | reject, shrink, retry, then structured failure |
| Tangent alignment below boundary | reject as branch-jump risk |
| Nullity > 1 | classify bifurcation; no branch switch |
| Nullity != 1 otherwise | rank-loss event; no certificate pass |
| Topology corruption | ordered stable diagnostic; no repair |
| Artifact/link/hash corruption | independent verifier failure tied to path |

## 11. Reuse and isolation

Reused unchanged: canonical JSON/hashes, public schemas, hinge primitive,
half-edge preflight, rank diagnostics policy, safe publication semantics, and
the certificate's summary boundary.

Generalized behind new profiles: finite Miura generation, fundamental cycles
for arbitrary valid trees, static FOLD writing for general quadrilateral
meshes, and bundle verification dispatch.

Isolated: `mcp_harness/rigid_fold.py` and `flex_extension.py`.  Their raw
matrix residuals, finite-difference-only Jacobians, flat-state diagnostics, and
driver-style continuation may inspire tests but are not imported by Phase 3
and cannot supply verdict evidence.

## 12. Primary references

- Mark Schenk and Simon D. Guest, “Geometry of Miura-folded metamaterials,”
  *PNAS* 110(9), 2013, doi:10.1073/pnas.1217998110.
- Tomohiro Tachi, “Simulation of Rigid Origami,” 4OSME, 2009.
- Zeyuan He and Simon D. Guest, “On Rigid Origami I: Piecewise-planar Paper
  with Straight-line Creases,” arXiv:1803.01430.
- Herbert B. Keller, “Numerical Solution of Bifurcation and Nonlinear
  Eigenvalue Problems,” in *Applications of Bifurcation Theory*, 1977.
- Joan Solà, Jérémie Deray, and Dinesh Atchuthan, “A micro Lie theory for
  state estimation in robotics,” arXiv:1812.01537.
- FOLD Specification 1.2, https://edemaine.github.io/fold/doc/spec.html.


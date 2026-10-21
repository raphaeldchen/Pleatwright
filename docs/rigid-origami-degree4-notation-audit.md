# Rigid-origami degree-4 notation audit

**Status:** Gate R1 accepted
**Date:** 2026-07-12
**Source baseline:** Foschi, Hull, and Ku, arXiv:2206.12691v2 / Phys. Rev. E 106, 055001 (2022)

This audit freezes the translation from the primary-source degree-4 equations to
the repository convention. Production analytic formulas are forbidden from using
any mapping other than the one below.

## Audit result

No unresolved source-notation ambiguity remains for the developable, noncollinear
degree-4 scope of Phase 1. The main extraction hazard was resolved explicitly:
Foschi–Hull–Ku Theorem 3, Equations (7) and (8), contain reciprocals of tangent
half-angles. In particular Equation (8) is a **cotangent-half-angle** relation;
plain-text PDF extraction can erase the fraction bars and make it look like a
linear tangent relation. That misreading contradicts Theorem 1 and fails SO(3)
closure. Reading the displayed fractions correctly agrees with both.

## Geometry and indexing map

Viewed from repository `+z`, all crease rays point outward from the vertex.

```text
                         e2
                        /
                alpha1/  alpha2
                      v
      e3 <-------------o-------------> e1 (schematic only)
                      ^
                alpha0\  alpha3
                        \
                         e0 (theta0 = 0)

Counterclockwise data order is e0, e1, e2, e3.
alpha_i is the positive sector from e_i to e_(i+1 mod 4).
The drawing is topological; the ray directions are cumulative sector sums.
```

| Meaning | Foschi–Hull–Ku | Repository | Conversion |
|---|---|---|---|
| Crease | `e_1..e_4` | `e0..e3` | paper `e_(i+1)` = repo `e_i` |
| Sector | `alpha_i` between `e_i,e_(i+1)` | `alpha_i` from `e_i` CCW to `e_(i+1)` | paper `alpha_(i+1)` = repo `alpha_i` |
| Fold angle | `rho_i` | `rho_i` | paper `rho_(i+1)` = repo `rho_i` |
| Positive sign | valley | valley | identical |
| Negative sign | mountain | mountain | identical |
| Range | `[-pi,pi]` | `[-pi,pi]` | identical |
| Half angle | `tan(rho_i/2)` | same | identical |

Foschi–Hull–Ku Figure 1 and Section II define `alpha_i` between `e_i` and
`e_(i+1)` and use positive valley. Theorem 2 equivalently says crease `e_i` lies
between sectors `alpha_(i-1)` and `alpha_i`. These statements are consistent.

## Rotation and sign reconciliation

Repository hinge storage says: for outward oriented crease `e_i`, the geometric
left face is fixed and the right face transforms by `R(e_i,-rho_i)`. A
counterclockwise walk around the vertex crosses every crease from its right face
to its left face, so the traversal uses the inverse transform `R(e_i,+rho_i)`.
With active right-handed column-vector rotations, the pinned closure is

```text
C(rho) = R(e0,rho0) R(e1,rho1) R(e2,rho2) R(e3,rho3) = I,
theta0 = 0,
theta_i = sum(alpha_0 .. alpha_(i-1)),
e_i = (cos(theta_i), sin(theta_i), 0).
```

This is the fixed-axis form of Belcastro–Hull's rotation-product model and agrees
with Tachi Equation (1). He–Guest Definition 11, Equation (8), gives the
equivalent post-multiplied local-frame product `prod Rz(alpha_j) Rx(rho_j)=I` and
states that only three of the nine rotation-matrix equations are independent.
The repository residual is `Log(C)` as a three-vector, not nine matrix entries.

An axis reversal alone changes `R(a,rho)` to `R(a,-rho)`. Therefore the invariant
primitive mapping is `(a,rho) -> (-a,-rho)`. Reversing an oriented stored hinge
also swaps left/right; the repository positive-valley `rho` remains semantic,
while the traversal direction changes. Tests exercise both descriptions.

## Adopted analytic equations

For evaluation, cyclically relabel so the selected repository driver is local
paper crease `e_4`. The local crease order is then

```text
(paper e1,e2,e3,e4) = (repo e_(d+1), e_(d+2), e_(d+3), e_d),
(paper alpha1..alpha4) = the same cyclic rotation of repo sectors.
```

Let `u = tan(rho_4/2)` and `y = tan(rho_1/2)`. Foschi–Hull–Ku Theorem 2,
Equation (6), is the quadratic root of Appendix A, Equation (A6):

```text
A y^2 - 4 sin(alpha1) sin(alpha3) u y + B = 0

A = cos(alpha2) - cos(alpha1-alpha3-alpha4)
    + [cos(alpha2)-cos(alpha1+alpha3-alpha4)] u^2

B = cos(alpha2) - cos(alpha1+alpha3+alpha4)
    + [cos(alpha2)-cos(alpha1-alpha3+alpha4)] u^2

y = [2 sin(alpha1) sin(alpha3) u +/- sqrt(D)] / A
D = 4 sin(alpha1)^2 sin(alpha3)^2 u^2 - A B.
```

The remaining two half angles use the correctly read cotangent form of Theorem
3, Equation (8):

```text
sin(alpha_(i+1)+alpha_(i+2)) / tan(rho_i/2)
  = sin(alpha_i) / tan(rho_(i-1)/2)
  + sin(alpha_(i-1)) / tan(rho_(i+1)/2).
```

For local `e1,e2,e3,e4`, this determines `tan(rho_2/2)` and
`tan(rho_3/2)` from the already selected `(rho_1,rho_4)` root. The equations are
used only away from the shared unfolded point; at zero the finite limit belongs
to a selected tangent ray, while the displayed cotangents are undefined.

## Root, branch, and travel choices

The raw `+/-sqrt(D)` symbol is not a durable mode name. For a fixed positive
driver seed, the two raw roots give two tangent rays. Reverse travel negates the
entire fold vector, but because `sqrt(D)` is nonnegative while `u` changes sign,
the raw root symbol swaps. Consequently:

| Concept | Durable representation |
|---|---|
| Finite mode | normalized tangent vector with driver component `+1` |
| Compact signature | ordered signs of that normalized tangent plus its numeric ratios |
| Driver | repository crease ID/index, stored explicitly |
| Travel | sign of the requested driver angle, stored separately |
| Paper alias | metadata only; never the identity key |
| Raw root | positive-seed sign stored explicitly; sign flips under reverse travel |

For a positive driver seed, compute both roots, map all folds back to repository
order, divide by the positive driver, and sort deterministically by the resulting
tangent vector, recording its raw root sign. For a negative driver request,
evaluation uses the opposite raw sign. This explicitly couples opposite raw
square-root signs across reverse travel and prevents branch switching at the
origin without a nearest-candidate heuristic.

Foschi–Hull–Ku Theorem 1 aliases for the reserved flat-foldable fixture are:

| Paper alias | Invariant fold relation |
|---|---|
| mode 1 | `rho1=rho3`, `rho2=-rho4` |
| mode 2 | `rho1=-rho3`, `rho2=rho4` |

For the paper's general developable example, Section III Example 1/Figure 3 is
used only for comparison. Its `mode 1/2` labels are not exported as durable IDs.

## Validity, singularity, and binding

| Case | Phase-1 behavior |
|---|---|
| Any non-finite angle | reject |
| Any sector outside `(0,pi)` | reject as unsupported/degenerate |
| Sector sum differs from `2pi` by more than `1e-10` | classify nondevelopable; do not evaluate developable formulas |
| Consecutive sector pair sums to `pi` within tolerance | classify collinear special; do not use generic formulas |
| Generic driver `rho_d=0` | return the unfolded singular state honestly; branch formulas are not certified there |
| Driver magnitude below `1e-8 rad`, except exact zero | reject as too close to the shared singularity |
| `abs(rho_d)=pi` | binding endpoint; tangent half angle is unbounded and is not evaluated as a finite formula input |
| First dependent half-angle pole | open connected branch endpoint found by deterministic scan/bisection |
| Negative discriminant beyond roundoff | no real state for that root/request |
| Vanishing quadratic/cotangent denominator | pole or special case; no silent fallback/root change |
| Any output outside `[-pi,pi]` or closure over tolerance | reject the analytic candidate |

At a generic non-flat solution the three-component closure Jacobian has rank 3
and nullity 1 for four fold variables. At the unfolded state the four crease
axes lie in the reference plane, so the first derivative spans only two rotation
directions: rank 2, nullity 2. This is a singular intersection of two finite
one-dimensional branches, not a certified two-DOF finite mechanism.

## Transformation audit

| Transformation | Data mapping | Expected invariant |
|---|---|---|
| Cyclic relabel by `k` | rotate sectors, folds, IDs, and driver by `k` | physical branch and residual norm |
| Reflection fixing `e0` | sectors `(a3,a2,a1,a0)`; folds `(r0,r3,r2,r1)` | closure and mapped tangent; global fold negation is reverse travel |
| Axis reversal | `(axis,rho)->(-axis,-rho)` | rotation matrix exactly |
| Reverse travel | `rho->-rho` on the same tangent signature | same finite mode, opposite direction |
| Uniform scale | ray lengths multiply; sectors and unit axes do not change | all fold relations, rank, and rotational residuals |

Uniform scale is tested before the sector-only oracle boundary: scaled rays are
renormalized to the same unit axes/sectors. No meaningless scale parameter is
added to the degree-4 analytic API.

## Source and decision ledger

| Type | Decision/evidence | Authority |
|---|---|---|
| Sourced fact | positive `rho` is valley; sectors are cyclic; two generic curves | Foschi–Hull–Ku pp. 1–3, Theorems 1–2 |
| Sourced fact | Eq. (6) has two square-root choices; root tracking is required | Foschi–Hull–Ku p. 3, Eq. (6), Remarks 1–2 |
| Sourced fact | reciprocal half-angle equations for developable vertices | Foschi–Hull–Ku pp. 3–4, Theorem 3, Eqs. (7)–(8), Appendix B |
| Sourced fact | vertex rotation closure has three independent equations | He–Guest Definition 11 Eq. (8); Tachi Eqs. (1)–(6) |
| Repository convention | outward oriented creases, CCW sectors, positive valley, left face fixed | `docs/rigid-origami-conventions.md` |
| Derived mapping | CCW right-to-left traversal uses `R(e_i,+rho_i)` | inverse of the pinned hinge transform |
| Numerical choice | log residual, float64, rank threshold, transported-axis Jacobian | Phase-0 numerical policy plus Phase-1 design spec |
| Rejected hypothesis | Theorem 3 Eq. (8) is linear in tangent half-angles | contradicts Theorem 1 and fails closure |
| Remaining limitation | collision/self-intersection and general nondevelopable cones are not judged | explicit Phase-1 scope |

## Primary references

- Foschi, Hull, and Ku, “Explicit Kinematic Equations for Degree-4 Rigid
  Origami Vertices,” Phys. Rev. E 106, 055001 (2022), arXiv:2206.12691v2.
- He and Guest, “On Rigid Origami I,” arXiv:1803.01430, especially Definition
  11 and Equations (8)–(9).
- Belcastro and Hull, “A Mathematical Model for Non-Flat Origami,” Linear
  Algebra and its Applications 348 (2002), 273–297.
- Tachi, “Simulation of Rigid Origami,” 4OSME (2009), Equations (1)–(6).
- FOLD specification 1.2, `edges_vertices`, `edges_faces`, and
  `edges_foldAngle`.

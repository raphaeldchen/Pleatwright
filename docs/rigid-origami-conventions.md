# Rigid origami conventions and FOLD profile 0.1

**Version:** 0.1.0
**Date:** 2026-07-12

This document is the operational convention reference for the new rigid package.
The design rationale is in
`docs/superpowers/specs/2026-07-12-rigid-origami-phase0-design.md`.

## Coordinates and units

| Quantity | Internal representation | External FOLD |
|---|---|---|
| Reference sheet | XY plane, `z = 0` | 2D or 3D `vertices_coords` |
| Face winding | CCW viewed from `+z` | CCW `faces_vertices` |
| Length | millimeters | `frame_unit: "mm"` |
| Fold angle | radians in `[-pi, pi]` | degrees in `[-180, 180]` |
| Positive fold | valley | valley (`V`) |
| Negative fold | mountain | mountain (`M`) |
| Vector convention | column vector | n/a |
| Transform convention | active, right-handed | n/a |

Non-finite numbers are invalid at every boundary.

Outer material loops wind counterclockwise and hole loops wind clockwise. In
schema 0.1, each face-local reference basis is aligned with the unfolded global
XY basis, so stored local hinge axes can be checked directly against the oriented
reference edge. Supporting independently oriented face frames requires an
explicit later schema version.

## Oriented hinge

For an oriented hinge edge `start -> end`, define the axis unit vector

```text
a = (end - start) / ||end - start||.
```

In the unfolded XY reference state, `left_face` is on the geometric left of the
axis and `right_face` is on the right. When `left_face` is fixed, the relative
right-face rotation is

```text
R_right_from_left(rho) = R_axis(a, -rho).
```

The minus sign makes `rho > 0` a valley while retaining a conventional
right-handed axis-angle primitive. Reversing the axis and swapping left/right
must yield the same physical configuration.

Exact anchors:

```text
R_x(+pi/2) [0, 1, 0]^T = [0, 0, 1]^T

hinge start=(0,0,0), end=(1,0,0), rho=+pi/2
right-face point (0,-1,0) -> (0,0,1)
```

## Vertex ordering

- Creases `e0..e(n-1)` are counterclockwise in the reference plane.
- `alpha_i` is the positive sector from `e_i` to `e_(i+1)`.
- Generic planar degree-4: every `alpha_i` lies in `(0, pi)` and the sum is
  `2*pi` within the documented developability tolerance.
- Collinear, symmetric, binding, or otherwise degenerate fixtures are classified
  before entering a generic analytic formula.

## Branch identity

A durable branch stores ordered crease IDs/sectors, analytic mode signature,
driver crease, driver sign, and a normalized tangent/sign signature at a small
non-flat seed. Publication labels such as `mode 1` are aliases only; cyclic
relabeling/reflection can change those names.

The unfolded degree-4 state is singular: a first-order nullity of two there does
not mean a two-DOF finite mechanism. Seed and classify finite branches away from
zero before reporting finite DOF.

## Rotation and closure

- Axis-angle rotations are active/right-handed and checked for `R^T R = I` and
  `det(R) = +1`.
- A concurrent single vertex may use a documented `SO(3)` product closure.
- The solve residual is the three-component rotation vector/logarithm; Frobenius
  error, determinant, and orthogonality are diagnostics.
- General face cycles, holes, cuts, offset joints, and thick mechanisms require
  `SE(3)` closure so translation gaps cannot hide behind correct orientation.

## Numerical policy 0.1

| Policy | Initial value |
|---|---:|
| dtype | IEEE-754 float64 |
| exact primitive comparison | `1e-12` |
| developability sum | `1e-10 rad` |
| primitive orthogonality/determinant | `1e-12` |
| future global rotation-vector closure target | `1e-9 rad` |
| future rank absolute threshold | `1e-10` |
| future rank relative threshold | `1e-8 * s_max` |

Solvers nondimensionalize lengths by a recorded characteristic scale. Every
certificate stores the actual values used. These defaults are engineering
starting points, not claims of physical accuracy.

## Rigid FOLD Profile 0.1

- Pin `file_spec: 1.2` and `frame_unit: "mm"` on export.
- `edges_foldAngle` is degrees, `+V/-M`, and assignment/sign consistency is
  validated.
- Static state is the default compatibility export.
- Multiple `file_frames` may provide sampled animation but are never the
  canonical trajectory.
- Internal cuts are duplicated boundary halfedges/vertices with a shared cut
  group. Export separate `B` edges by default; collapsed `C` is opt-in.
- `J` edges are nonmechanical subdivisions/triangulation and do not become
  hinges.
- Panels with holes remain explicit in the IR; subdivided export preserves a
  `faces_ro:panelId`.
- Custom keys contain a namespace colon: `ro:branchId`,
  `edges_ro:hingeId`, and similar.
- Import validates array lengths, indices, incidence, winding, units,
  assignment/angle consistency, and cut/join semantics.

Primary format authority:
[FOLD specification 1.2](https://edemaine.github.io/fold/doc/spec.html).

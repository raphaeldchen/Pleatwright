# Rigid origami Phase 1: notation-audited degree-4 oracle

**Status:** Implementable specification
**Date:** 2026-07-12
**Branch:** `codex/rigid-origami-phase-1-degree4`
**Hard gate:** `docs/rigid-origami-degree4-notation-audit.md`

## Mission and claim boundary

Implement a deterministic analytic oracle for generic developable degree-4
vertices and the concurrent-vertex SO(3) closure kernel that independently checks
it. The accepted claim is:

> For the recorded ideal concurrent zero-thickness vertex, branch, inputs,
> implementation version, and tolerances, the analytic fold vector satisfies the
> pinned rotation-product closure and has the reported first-order rank.

This phase does not claim collision freedom, global multi-vertex compatibility,
physical foldability with thickness, or formal proof.

## Public mathematical boundary

`mcp_harness/rigid/kinematics/closure.py` provides:

- guarded `SO(3)` logarithm returning a rotation vector;
- ordered rotation-product closure for CCW sectors/folds;
- closure residual and norm diagnostics;
- exact transported-axis closure Jacobian, independently finite-difference checked;
- SVD rank/nullity diagnostics under the centralized threshold policy.

`mcp_harness/rigid/degree4.py` provides frozen result objects and functions for:

- raw-sector developability/special classification;
- enumeration of two durable generic branch tangents;
- branch-selected driver evaluation in either travel direction;
- explicit unfolded/binding/special reporting;
- analytic-vs-closure cross-check evidence;
- bounded sampling of one finite branch away from zero.

The existing Pydantic artifact schemas do not change. The local oracle is a
mathematical layer beneath serialized certificates; exact-flat diagnostics cannot
be encoded as a passing `GlobalKinematicsEvidence` sample under schema 0.1.

## Numerical policy additions

All constants live in `rigid.conventions`:

| Quantity | Value |
|---|---:|
| closure pass norm | `1e-9 rad` |
| rank absolute threshold | `1e-10` |
| rank relative threshold | `1e-8 * s_max` |
| SO(3) near-zero log guard | `1e-8 rad` |
| SO(3) near-pi log guard | `1e-7 rad` |
| Jacobian cross-check central step | `1e-7 rad` |
| branch tangent seed | `1e-6 rad` |
| algebraic cancellation guard | `1e-14` |
| minimum certified nonzero driver | `1e-8 rad` |

`Log(R)` uses `atan2(||vee((R-R^T)/2)||,(trace(R)-1)/2)` away from the
guards. Near zero it uses the skew vector with the analytic small-angle factor.
Near pi it extracts the axis from `(R+R^T+2I)/4`, aligns it with the skew vector when
possible, and otherwise uses a deterministic first-nonzero-positive sign. Inputs
must already be in SO(3) under the primitive tolerance.

For `C=prod R(e_i,rho_i)`, let `P_i` be the product before crease `i`. The
left-trivialized derivative column is `P_i e_i` under the pinned positive
traversal. At closure this is exactly the derivative of `Log(C)`; away from
closure it remains the natural closure tangent. A deterministic central
difference of the public residual is a test oracle, not the production rank
path. Every diagnostic stores its matrix, singular values, threshold, rank, and
nullity so the verdict is recomputable.

## Degree-4 classifications

Closed classification vocabulary:

- `generic_flat_foldable`: developable, Kawasaki, noncollinear;
- `generic_developable`: developable, non-Kawasaki, noncollinear;
- `collinear_special`: developable with an opposite crease line;
- `nondevelopable`: sector sum is not `2pi`;
- invalid input raises rather than becoming a classification.

The collinear fixture is deliberately routed away from Equation (6). Phase 1
reports that special motions exist but does not pretend the generic two-root
parameterization covers them.

## Branch contract

A branch is not a raw quadratic-root sign or a publication mode number. It stores:

- ordered repository crease indices;
- ordered sector angles;
- driver crease index;
- normalized tangent ratios at a positive non-flat seed;
- tangent sign signature;
- the raw root sign at a positive driver seed;
- the open connected driver interval before a dependent half-angle pole;
- optional source-specific alias;
- formula/provenance version.

Enumeration evaluates both roots at the positive seed and sorts by the full
tangent tuple, making output deterministic. It records the seed's raw root sign;
evaluation flips that sign under reverse travel, preserving the same odd finite
mode without a nearest-candidate heuristic. A deterministic scan plus bisection
finds the first dependent half-angle pole in each direction and records the open
connected validity interval. Inputs closer than `1e-8 rad` to flat are rejected
except for exact zero, whose singular state is reported explicitly.

## Independent oracle

Committed goldens are generated offline by a standalone mpmath 1.3.0 evaluator
at 100 decimal digits. It imports neither `rigid.degree4` nor
`rigid.kinematics.closure`.

Its structure is intentionally different:

1. Build high-precision tangent-half-angle hinge quaternions directly.
2. Multiply the four quaternions and set the three vector components to zero.
3. Fix the requested driver and solve those three multilinear closure equations
   with two documented deterministic basin hints: the published flat-foldable
   mode relations or rounded null rays from a separate high-precision flat
   closure-Jacobian calculation. Newton's solved values, not the hints, are the
   oracle output.
4. Verify that both solves remain separated and reverse-travel states are odd.
5. Independently verify all nine Rodrigues-product entries, determinant, and
   orthogonality.
6. Emit decimal strings plus evaluator version, precision, source equations,
   script hash, and fixture hash.

Production uses Theorem 2 Equation (6) plus Theorem 3 Equation (8); the oracle
uses the rotation-product polynomial directly and therefore does not share the
production evaluation path.

## Required behavior

- Both generic fixtures: two finite branch tangents and both driver signs.
- Multiple non-flat driver values agree with committed high-precision goldens.
- Re-evaluating with another crease as driver returns the same fold vector.
- Every analytic result independently closes under the SO(3) kernel.
- Wrong-root mixing and fold-sign corruption fail closure.
- Non-flat states report rank 3/nullity 1.
- Exact flat reports rank 2/nullity 2, `singular=True`, and no finite-DOF claim.
- A bounded trace excludes zero and is deterministic in forward/reverse order.
- Cyclic relabeling and reflection map each stored tangent identity directly;
  axis reversal, reverse travel, and ray scaling preserve the documented result.

## Error and limitation behavior

Type errors, malformed shapes, non-finite values, out-of-range folds, invalid
sectors, unsupported generic formulas, negative discriminants, vanishing
denominators, branch mismatches, and closure failures are distinct exceptions or
structured statuses. No fallback changes root, mode, driver, or sign silently.

Self-intersection is not tested. A kinematically closed analytic state can still
be physically inadmissible once finite panels, collision, thickness, or a larger
mechanism are considered.

## Isolation

No changes to schema JSON, TreeMaker, Oriedita, MCP servers, prompts, web,
frontend, simulator, Miura, collision, topology, fabrication, or learned
feasibility. Runtime remains NumPy-only; mpmath is an offline fixture generator
dependency and committed goldens are the test input.

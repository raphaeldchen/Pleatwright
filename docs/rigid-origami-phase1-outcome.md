# Rigid-origami Phase 1 outcome: degree-4 authority

**Status:** Accepted — gates R1–R4 and repository isolation gates pass
**Date:** 2026-07-12
**Branch:** `codex/rigid-origami-phase-1-degree4`
**Phase-1 starting baseline:** `cbe139849a937df7c92a064e0ef80796cd79d14a`
**Post-merge integration baseline:** `1ddd653ce6de8f07c8db5ace22dfeaf469e247a7`

The branch was cut from `origin/main` after Phase-0 PR #36 merged and commit
`80ca3b0` was present. Before opening the Phase-1 PR, current `origin/main` was
merged without conflict at `1ddd653`; the complete repository and isolation
gates were rerun against that combined history.

## Accepted claim

For an ideal, concurrent, developable, zero-thickness, noncollinear degree-4
vertex under the recorded repository convention, the implementation enumerates
two durable finite tangent branches, evaluates either travel direction inside
the branch's connected interval, independently checks ordered `SO(3)` closure,
and reports recomputable first-order rank evidence.

It does not certify collision freedom, finite thickness, material behavior,
global compatibility, or physical realizability of a larger crease pattern.

## Accepted notation mapping

- Repository creases `e0..e3` are outward rays ordered counterclockwise from
  `+z`; `alpha_i` is the positive sector from `e_i` to `e_(i+1 mod 4)`.
- Foschi–Hull–Ku paper indices are one-based: paper `e_(i+1)`, `alpha_(i+1)`,
  and `rho_(i+1)` map directly to repository index `i`.
- Positive `rho` is valley in both systems. Repository hinge storage moves the
  right face by `R(e_i,-rho_i)` with the left fixed; the counterclockwise
  right-to-left vertex traversal therefore uses the inverse,
  `R(e_i,+rho_i)`.
- Closure is `R(e0,rho0) R(e1,rho1) R(e2,rho2) R(e3,rho3)=I` with active,
  right-handed, column-vector rotations.
- For driver `d`, local paper creases `(e1,e2,e3,e4)` are repository
  `(e_(d+1),e_(d+2),e_(d+3),e_d)`. Production uses Theorem 2 Equation (6) for
  the quadratic root and the correctly read cotangent-half-angle form of
  Theorem 3 Equation (8) for the remaining folds.
- A branch stores its normalized positive-driver tangent ray, sign signature,
  full numeric ratios, positive-driver raw root sign, and open connected driver
  interval. Reverse travel flips the raw sign. Publication `mode 1/2` labels are
  aliases only for the reserved flat-foldable fixture.

The full equation, indexing, transformation, and source ledger is in
`docs/rigid-origami-degree4-notation-audit.md`.

## Implemented capability

`mcp_harness/rigid/kinematics/closure.py` now provides:

- strict axis/sector/fold validation;
- pinned ordered vertex rotation products;
- a guarded `SO(3)` logarithm near zero and pi;
- closure residual and norm;
- exact transported-axis closure Jacobian;
- explicit SVD threshold, singular values, rank, nullity, and singular status.

`mcp_harness/rigid/degree4.py` now provides:

- generic flat-foldable, generic developable, collinear-special, and
  nondevelopable classification;
- cancellation-resistant evaluation of the two Equation (6) roots;
- durable branch enumeration for any selected driver crease;
- both travel directions without nearest-root switching;
- deterministic dependent-half-angle pole detection by scan and bisection;
- exact-flat singular reporting and a minimum certified nonzero driver guard;
- analytic-result closure and rank cross-checks;
- bounded, reversible branch traces that exclude the shared flat singularity.

For the published general fixture, the two driver-0 open intervals are
`(-1.9106332362489997, +1.9106332362489997)` and
`(-2.3331131661693467, +2.3331131661693467)` radians. The reserved generic
flat-foldable branches remain valid up to the excluded `+/-pi` driver binding.

At exact flat, rank is 2 and nullity is 2, `singular=True`, and `finite_dof` is
unset. At accepted non-flat samples, rank is 3 and nullity is 1, yielding the
limited finite-branch claim `finite_dof=1`.

## Independent oracle evidence

The committed evaluator
`mcp_harness/tests/fixtures/generate_rigid_degree4_oracle.py` imports no
production rigid module. Under CPython 3.14.3 and mpmath 1.3.0 at 100 decimal
digits, it solves the three vector components of an unnormalized
tangent-half-angle quaternion closure product. It then independently verifies a
Rodrigues matrix product, orthogonality, and determinant.

It uses two documented deterministic basin hints—published flat-foldable mode
relations or rounded high-precision flat-Jacobian null rays—but only Newton's
solved values are emitted. The generator rejects branch collapse and verifies
odd reverse travel.

Evidence over 16 committed non-flat states (2 fixtures x 2 branches x 2 signs x
2 magnitudes):

| Measurement | Observed maximum |
|---|---:|
| independent high-precision verification error | `2.8574684782056875e-101` |
| production vs. oracle fold-angle error | `8.881784197001252e-16 rad` |
| production closure residual norm | `9.57707061453503e-16 rad` |
| extra deterministic random sweep, 160 states | `3.224910822914672e-14 rad` |

Hashes:

- generator: `sha256:7ece25b829215fd2bc2cc12a7b39d835e02b57fb65be39881ed431c57480d977`
- fixture: `sha256:99fbaa87defc16c0661427d76c92051b64db758ed775e0711cc7b16d2e54c4d3`

No source code, figures, meshes, tables, or unexplained numeric output were
copied from research repositories.

## Numerical policy

| Quantity | Value |
|---|---:|
| closure acceptance | `1e-9 rad` |
| developability | `1e-10 rad` |
| rank absolute threshold | `1e-10` |
| rank relative threshold | `1e-8 * s_max` |
| `SO(3)` near-zero guard | `1e-8 rad` |
| `SO(3)` near-pi guard | `1e-7 rad` |
| branch tangent seed | `1e-6 rad` |
| algebraic cancellation guard | `1e-14` |
| minimum nonzero driver | `1e-8 rad` |

## Adversarial review closure

An independent post-implementation review identified the following issues; the
branch fixes each with a dedicated regression:

- cancellation in the seed-scale quadratic root and consequent unstable branch
  signatures/aliases;
- an unreported dependent-fold `+/-pi` pole that could wrap to the other angle
  representation;
- use of a nonsymmetric near-pi axis projector;
- trace rounding that could turn tiny nonzero inputs into exact zero;
- stale documentation describing nearest-candidate root selection;
- metamorphic tests that selected a nearest state rather than mapping branch
  identity directly;
- an incorrect independent-oracle branch-collapse guard and undocumented basin
  hints.

All P1/P2 findings are closed by commit `8ea9099` and pass in the full gate.

## Verification record

Environment:

- macOS/Darwin; Python 3.14.3
- NumPy 2.4.6; pytest 9.0.3; Pydantic 2.13.4
- TreeMaker native extension rebuilt from 50 model sources
- Oriedita validator 1.1.3 rebuilt
- Node 25.6.1; npm 11.9.0; Vitest 2.1.9

Commands and results:

```text
PYTHONPATH=mcp_harness <shared-python> -m pytest mcp_harness/tests/test_rigid*.py -q
111 passed in 0.45s

make PYTHON=<shared-python> test
592 passed, 4 skipped in 512.10s (post-merge integration gate)

PYTHONPATH=. <shared-python> -m pytest web/tests -q
40 passed in 0.46s

npm test  # dedicated worktree sources, temporary link to existing node_modules
6 files passed; 59 tests passed

PYTHONPYCACHEPREFIX=/private/tmp/rigid-phase1-pyc PYTHONPATH=mcp_harness \
  <shared-python> -m compileall -q mcp_harness/rigid \
  mcp_harness/tests/test_rigid_closure.py mcp_harness/tests/test_rigid_degree4.py
exit 0

git diff --check
exit 0

git diff --exit-code cbe1398 -- mcp_harness/schemas
exit 0
```

The four skips are opt-in external Meshy, Hugging Face, reference, and simulator
smoke tests. The web backend emits one pre-existing Starlette/httpx deprecation
warning. No public schema changed and committed schema JSON is byte-identical to
the Phase-0 baseline.

## Changed files

- `docs/rigid-origami-degree4-notation-audit.md`
- `docs/rigid-origami-fixtures.md`
- `docs/rigid-origami-phase1-outcome.md`
- `docs/superpowers/specs/2026-07-12-rigid-origami-phase1-degree4-design.md`
- `docs/superpowers/plans/2026-07-12-rigid-origami-phase1-degree4.md`
- `mcp_harness/rigid/conventions.py`
- `mcp_harness/rigid/degree4.py`
- `mcp_harness/rigid/kinematics/__init__.py`
- `mcp_harness/rigid/kinematics/closure.py`
- `mcp_harness/tests/fixtures/generate_rigid_degree4_oracle.py`
- `mcp_harness/tests/fixtures/rigid_degree4_oracle_v1.json`
- `mcp_harness/tests/test_rigid_closure.py`
- `mcp_harness/tests/test_rigid_degree4.py`

No TreeMaker, Oriedita, MCP, prompt, web, frontend, simulator, or schema source
was changed.

## Known limitations and deferred work

- Collinear/symmetric special motions are classified and routed away from the
  generic formula; Phase 1 does not parameterize them.
- The connected interval detector is a deterministic numeric scan/bisection,
  not a symbolic proof of every possible singular boundary.
- The kernel is for one ideal concurrent vertex. General face cycles need
  `SE(3)`, deterministic topology, face poses, and global continuation.
- No collision, thickness, elasticity, fabrication, layer order, arbitrary
  crease synthesis, Miura, flasher, learned feasibility, MCP, or UI claim is
  made.

## Recommended next vertical slice

Compile one branch-selected degree-4 vertex all the way from a deterministic
panel/half-edge mechanism graph through face-pose propagation to reference and
sampled folded FOLD frames. Use the current analytic oracle as the acceptance
reference and preserve schema/legacy isolation. This supplies the smallest
topology/FOLD/pose foundation needed before multi-vertex global continuation and
Miura, while exercising a complete deterministic artifact path without adding
collision or AI claims.

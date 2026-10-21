# ADR 0001: Add rigid origami as a sibling compiler domain

**Status:** Accepted for Phase 0
**Date:** 2026-07-12

## Context

The existing product compiles an AI-editable `MetricTree` through TreeMaker into
FOLD geometry, optionally runs Oriedita flat-endpoint linting, and previews the
result in Origami Simulator. A rigid-origami mechanism needs different source
semantics, panel/hinge topology, branch-aware finite kinematics, and collision
evidence. TreeMaker, Oriedita, and the compliant browser simulator do not provide
that authority.

Using `MetricTree` and `RigidDesignSpec` as two editable descriptions of the same
design would introduce an unspecifiable synchronization problem. Replacing the
working TreeMaker path would also risk the artistic origami product without
helping the rigid mathematical kernel.

## Decision

Create two sibling compiler domains:

- Tree method: `MetricTree -> TreeMaker -> FOLD`.
- Rigid families: `RigidDesignSpec -> RigidMechanismGraph -> trajectory ->
  MotionCertificate`.

The AI-editable source is domain-specific. `MetricTree` remains the only editable
source for TreeMaker; `RigidDesignSpec` is the only editable source for the rigid
compiler. Version 1 has no automatic conversion between them.

FOLD 1.2 is a shared interchange format, not the canonical rigid project record.
`RigidProjectRecord` owns spec revisions, mechanism/trajectory hashes, branch and
solver provenance, certificates, approvals, and later experiment data.

The rigid implementation lives under `mcp_harness/rigid/` and will eventually be
exposed by a separate MCP server/prompt profile. Phase 0 does not change
`agent_loop.py`, `server.py`, `linter_server.py`, the web bridge, or the frontend.

Authority remains layered:

1. family generator: construction invariants only;
2. local analyzer: local branch claims only;
3. global solver: ideal zero-thickness finite-path claims only;
4. collision engine: explicitly scoped contact/clearance claims only;
5. flat endpoint tools: endpoint/layer claims only;
6. physical tests: experimental observations only.

Skipped evidence is recorded as `not_run`. A numerical result is described as
verified under its recorded model and tolerances, not as a universal proof.

## Consequences

- The legacy TreeMaker path can evolve independently and must retain its tests.
- Rigid mechanisms get a richer IR without forcing nonstandard semantics into
  FOLD.
- Agent routing must later select a domain profile rather than exposing
  incompatible tools together.
- Oriedita normalization may operate on a lint copy only; it cannot touch a
  canonical rigid artifact because it drops angle/face/order arrays while
  reindexing.
- Origami Simulator remains a labeled approximate comparison view.
- Cross-domain product features require an explicit future ADR.

## Rejected alternatives

- **Extend `MetricTree` with panel/hinge fields.** A flap-allocation source does
  not encode mechanism topology, branch choice, or face cycles.
- **Treat FOLD as the only database.** FOLD has no required continuous-trajectory,
  branch, solver-residual, or collision-certificate semantics.
- **Replace TreeMaker in place.** This risks a functioning compiler and combines
  unrelated mathematical models.
- **Use the browser simulator as authority.** Its compliant dynamics can mask
  rigid closure errors and do not report authoritative rank or branch evidence.

## References

- `docs/rigid-origami-ide-plan.md`
- `docs/superpowers/specs/2026-07-12-rigid-origami-phase0-design.md`
- [FOLD specification 1.2](https://edemaine.github.io/fold/doc/spec.html)

# Rigid origami version-1 scope

**Status:** Frozen for Phase 0
**Date:** 2026-07-12

## Supported model

- One connected, initially planar sheet.
- Straight creases and polygonal ideal rigid faces.
- Zero material thickness.
- Quasi-static kinematics; no force, stiffness, dynamics, or fatigue claims.
- Exactly one finite mechanism DOF away from documented singular states.
- Known parameterized families, beginning with Miura.
- A diagnostic single degree-4 vertex family for kernel fixtures.
- One published rigid cut-flasher family only after cut/hole and global closure
  support exists.
- FOLD 1.2 static-state interchange plus a richer project-record sidecar.
- Collision as a separate stage with an explicit evidence strength.

## Supported first requests

- Construct/analyze one notation-audited degree-4 diagnostic vertex.
- Generate a bounded Miura array from typed repetitions, edge lengths, sector
  angle, branch, driver, and target fold angle.
- Compare valid Miura candidates using a closed objective vocabulary.
- Later, generate the named Lang-Magleby-Howell rigid cut-flasher family.

## Required evidence distinctions

The UI/API must keep these separate: topology, developability, local
flat-foldability, local rigid branch, global compatibility, first-order
flexibility, finite rigid motion, collision, flat endpoint/layer order, and thick
mechanism realizability.

No Boolean named only `foldable` is accepted in a public rigid contract.

## Non-goals

- Arbitrary natural-language crease topology synthesis.
- TreeMaker animals or recognizable-object bases on the rigid path.
- Curved creases, elastic faces, or general multi-DOF motion planning.
- Universal thickening, naive shell extrusion as mechanics, or fabrication
  certification.
- Force/stiffness/buckling/fatigue/deployment dynamics.
- Safety-critical flight, medical, structural, or building-code certification.
- Treating any radial flasher or locally Kawasaki/Maekawa-valid pattern as a
  globally rigid mechanism.
- Treating a first-order nullspace, endpoint solve, compliant preview, or sampled
  collision check as stronger evidence than it is.

## Claim language

Allowed after the relevant stages pass:

> Numerically verified for the recorded ideal zero-thickness model, branch,
> trajectory representation, solver version, and tolerances.

Not allowed without a stronger formal/conservative method:

- mathematically perfect;
- physically proven;
- guaranteed collision-free for unsampled motion;
- fabrication-ready merely because zero-thickness closure passed.

## Exit from version 1

Additional families, sheets/joints, thickening, mechanics, fabrication, and
learned feasibility each require an explicit versioned contract and renewed
validation; none silently extends a version-1 certificate.

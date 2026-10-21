# The (variant × scale) grid that falsified §4.9 a third time

Design [2026-08-03-path-reconciliation-design.md](../../specs/2026-08-03-path-reconciliation-design.md)
§4.9. The section asked for exactly this measurement before a fourth attempt:

> A third attempt should begin by measuring which *(variant, scale)*
> combinations actually pack, not by choosing where to slot a rung.

Reproduce: `PYTHONPATH=.:tests .venv/bin/python probe_scale_grid.py out.json`
from `mcp_harness/`. Each cell is a **direct engine compile** of one node list —
which is attempt-0 for that list — rather than a ladder call, so the grid
attributes the pack to a specific *(variant, scale)* instead of to the search.

Subjects: the four `insect` v64 configurations §4.9 claims as its rescues.
Variants: `exact` + every `order_variants` + every `placement_variants`
candidate (8 cells per scale). `longest = 0.4217`, so the clamp factor
`LONGEST_LIMB_TARGET / longest` = **0.9486**.

## Result — identical on all four configurations

| scale | packs | which |
|---|---|---|
| 1.0000 | 0 / 8 | — |
| 0.9800 | 0 / 8 | — |
| **0.9600** | **1 / 8** | `order:seeded_0` |
| **0.9486 ← THE CLAMP** | **0 / 8** | **—** |
| 0.9400 | 0 / 8 | — |
| 0.9200 | 0 / 8 | — |
| 0.9000 | 1 / 8 | `order:seeded_0` |
| 0.8500 | 1 / 8 | `order:seeded_2` |
| 0.8000 | 2 / 8 | **`exact:caller`**, `order:seeded_2` |

**The clamp factor lands in a dead band.** Nothing packs at 0.9486 while 0.96 —
a 4% shrink — does. The factor is derived from a packing-regime convention, not
from this tree, so where it falls on a pitted pack/fail structure is a
coincidence; here a bad one.

**And the rescue it claimed was bought with jitter.** Through the real serve
path (`server.draft_and_compile_full_base`):

| scale | serve | via |
|---|---|---|
| 1.0000 | FAILED | — |
| **0.9486 (clamp)** | packed | node-order restart **+ jitter** |
| **0.9600** | packed | node-order restart — **no jitter** |
| **0.8000** | packed | **attempt-0 exact** |

`did not pack exactly` is the jitter note: `agent_loop.py:318` defines it as
*"the backend nudged your EDGE LENGTHS"*. So §4.9's central justification —
*"proportion-preserving, which is why it may sit ahead of jitter"* — is
backwards for the factor it specifies.

## The constructive half

A **searched** uniform-scale rung (0.96 / 0.90 / 0.85 / 0.80, each composed with
the order variants, first-to-pack wins) reaches all four rescues, and at 0.96
does it proportion-preserving. That is strictly better than the clamp on every
axis. It is not shipped — see §4.9.2 for the three reasons, all design
decisions rather than work: it needs a new `STAGE_HONESTY` rank inside a
test-pinned ordering the ladder's proportion barrier is monotone in; PR #70
names margin-to-cliff as a pre-ship gate for anything that moves achievable
scale, and this moves it the risky way (0.6128 at scale 0.80 against the clamp's
0.5409); and the factor ladder is fitted to four configurations of one subject.

# Design: Shaping Primitives — Crimp + Outside Reverse (Pillar B)

**Status:** Approved design, ready for implementation planning.
**Date:** 2026-07-02
**Parent docs:** `2026-07-01-shaping-tracer-b1-b3-b4-design.md` (the wedge
geometry and angle model) and `2026-07-01-shaping-agent-wiring-b2-design.md`
(the `apply_shaping_ops` tool, ops-with-fold transport, HITL contract). B2
merged as PR #21; its review-minor follow-up is PR #22 (wrapper carries
`paper: [w, h]`; env fallback keyed on `ops is None`). This spec assumes both.

---

## 1. Goal

Grow the shaping vocabulary from one primitive (inside reverse fold) to
three agent-callable kinds — `reverse`, `outside`, `crimp` — on the SAME
`apply_shaping_ops` tool and `targets` schema, with no behavioral change to
the display replay machinery beyond one new op-string kind.

Success demo (live, Groq scout): compile the dog; "crimp its neck" and
"bend the head back" each produce a posed render in the Model tab. With only
`kind: "reverse"` targets (or no `kind` at all), behavior is byte-identical
to today.

## 2. Decisions made in this cycle

| Question | Decision |
|---|---|
| Primitive set | **Crimp + outside reverse.** Squash/sink rejected for now: layer-aware, dishonest in our display model — waits for folded-state-first. |
| Success bar | Suite + live Groq demo (same as B2). |
| Schema | `kind` field on targets of the ONE existing tool, default `"reverse"`. Separate tools rejected: schema tokens already push Groq request 1 near the TPM cap. |
| Architecture | **Approach A:** outside reverse is the only new geometry (a `sense` flip in `reverse_fold`); crimp is a tool-level atomic composition (inside + outside) emitting two ordinary op strings. Rejected B (first-class `crimp_fold` — duplicates/refactors ~90 lines of the trickiest wedge geometry and teaches the display a new compound op for the same rendered result) and C (prompt-only composition — cannot express the sense alternation, so a true crimp is impossible without `outside`). |

## 3. Geometry: `sense` in `reverse_fold` (`mcp_harness/shaping.py`)

```
reverse_fold(fold, tip_xy, d, theta, gamma=45.0, sense=+1) -> dict
```

- `sense=+1` is today's inside reverse fold, bit-for-bit (default keeps every
  existing caller and test unchanged).
- `sense=-1` (outside) multiplies the angle-model sign for the **wedge arms
  and tip-side axial only**:
  - wedge arms: `sense * s * theta`
  - tip-side axial: `sense * s * (180 - 2*theta)`
  - body-side axial: `s * 180` — UNCHANGED. That crease belongs to the
    compiled base; flipping it would misrepresent the base fold.
  Physically: inside bends the tip toward the flap's existing fold
  direction; outside bends it away. Like the tracer's model, this is a
  calibration start — the browser strain oracle (p90 < 0.15,
  converge-or-reject) is the judge, and the fixture acceptance calibrates.
- **Guard:** `theta == 180` with `sense=-1` raises `ShapingError` (the flat
  outside case breaks Maekawa parity at the new degree-4 vertex; shaping
  targets partial angles anyway). Inside keeps its `(0, 180]` range.
- All existing preconditions (tip signature, arm marching, region guard,
  all-or-nothing construction) apply identically to both senses.

### Op grammar

`outside:X,Y:D:THETA` joins `reverse:X,Y:D:THETA`.

- `parse_op(op)` returns `(kind, (x, y), d, theta)` where `kind` is
  `"reverse"` or `"outside"` — **a signature change**; its callers
  (`apply_display_op`, tests) are updated in the same task. Range checks:
  `d > 0`; theta `(0, 180]` for `reverse`, `(0, 180)` for `outside`.
- `apply_display_op` maps kind to `sense` and calls `reverse_fold`. It stays
  defensive (any failure -> input unchanged, one stderr line).
- `apply_display_ops` (the sequential replay loop), `web/fold.py`, and
  `web/server.py` are **untouched** — a crimp arrives at the display as two
  ordinary single-fold op strings.

## 4. Tool: `kind` on targets (`mcp_harness/server.py`)

Target schema:

```
{"node_id": <leaf id>,
 "kind": "reverse" (default) | "outside" | "crimp",
 "fraction": (0,1), default 0.5,      # fold point from the tip
 "fraction2": (0,1), default 0.5,     # crimp only: second fold point, as a
                                      # fraction of the REMAINING tip segment
 "theta": degrees}
```

- `reverse` / `outside`: exactly today's path with the op kind prefixed and
  the theta range per §3. `d = fraction * axial_length(current, tip_xy)`,
  baked into the op string (the B2 cross-path-equivalence contract).
- `crimp`: the tool expands one target into TWO ops, applied and validated
  sequentially like any two ops:
  1. inside reverse at `d1 = fraction * axial_length(current, tip_xy)`,
  2. outside reverse at `d2 = fraction2 * d1` (the tip's axial segment after
     op 1 has length `d1`; the CP's 2D positions don't move, so the same
     `tip_xy` addresses the tip).
  Equal theta on both halves returns the tip section parallel to the flap —
  the classic zigzag (knees, ankles, neck angles, beaks).
- **Crimp theta guard:** `theta == 90` is refused up front for `crimp`
  (verdict reason names the constraint). At exactly 90 the inside half's
  tip-side axial angle is `s*(180 - 2*90) = 0` -> assignment `F`, so the tip
  loses its one-crease signature — and probing shows the second half does
  NOT refuse: `_find_tip` silently retargets a different vertex (nearest
  remaining tip signature) and the fold lands on the wrong structure. The
  guard prevents silent mis-targeting. The HITL prompt (§5) tells the agent
  to pick e.g. 75 or 105 for crimps.
- **Atomicity:** before a crimp, snapshot `current` and the ops-list length.
  If EITHER half raises, restore both and emit ONE verdict
  `{node_id, kind: "crimp", status: "refused", reason: <the failing half's
  geometric reason>}`. No half-crimp ever ships. An applied crimp emits one
  `applied` verdict but appends two entries to `ide_shape_ops`.
- Verdicts gain a `kind` field for all target kinds (additive; B2 consumers
  only read node_id/status/reason).
- Malformed `kind` (unknown string, non-string) -> per-target `refused`
  verdict, batch continues (B2's never-abort rule).
- Wrapper JSON shape is otherwise unchanged (`status`, `fold`,
  `ide_shape_ops`, `paper`, `verdicts`).

## 5. HITL prompt (`agent_loop.py` SYSTEM_PROMPT)

The existing SHAPING section grows a short kinds vocabulary (a few lines,
schema-mirroring):

- `reverse` — bend the flap at a point (default).
- `outside` — bend the other way (away from the flap's fold direction).
- `crimp` — zigzag at a point: offsets the flap sideways while keeping its
  direction; use for knees, ankles, neck angles, beaks. `fraction2` places
  the second fold within the tip segment. theta must not be exactly 90
  (use e.g. 75 or 105).

The propose-first / user-confirms / report-refused-verdicts-verbatim
contract is unchanged and its pinned wording untouched.

## 6. Out of scope (deferred, on purpose)

- Squash/sink and any layer-aware primitive (needs folded-state-first).
- Closing the strain-oracle loop (browser -> agent verdict channel).
- Per-op `gamma` (wedge arm angle) control.
- Persisting shaped folds as first-class artifacts.
- Folded-state-first generalization (phase 2).

## 7. Testing

- **pytest, unit (TWO_TIP_SQUARE fixture, fast):**
  - `outside` sense: same topology delta as inside (+3 vertices/+5 edges);
    wedge-arm and tip-axial fold angles are the sign-flip of the inside op
    on the same fixture; body-axial angle identical between senses.
  - `theta=180` outside -> `ShapingError`; inside `theta=180` still applies.
  - `parse_op` round-trips `outside:`; unknown kind still refused.
  - `apply_display_op` dispatches `outside:` and stays defensive.
- **pytest, engine (real spawn compile, star-4):**
  - one `kind: "crimp"` target -> `status: "shaped"`, one `applied` verdict
    with `kind: "crimp"`, TWO ops in `ide_shape_ops` (first `reverse:`,
    second `outside:`), and the B2 re-square-and-replay equivalence
    assertion extended over the mixed grammar (+10 edges).
  - a crimp forced to fail on its second half -> ONE `refused` verdict,
    `ide_shape_ops` unchanged by that target, a following good target still
    applies. Probing found NO in-range `fraction2` that naturally refuses
    on star-4, so the failure is forced by monkeypatching
    `shaping.reverse_fold` to raise `ShapingError` on its `sense=-1` call —
    this pins the tool's atomic bookkeeping, which is the contract under
    test (the geometry's own refusals are covered by the unit tests).
  - `kind: "outside"` single target through the tool -> applied, op string
    starts `outside:`.
  - `kind: "crimp"` with `theta: 90` -> `refused` up front (the §4 guard),
    no compile-side geometry attempted for that target.
  - plan-time probe run (like B2) picks the exact fixture parameters before
    they are pinned in tests.
- **prompt pins:** kinds vocabulary substrings; the existing
  "ONLY AFTER THE USER APPROVES" pin must still pass unmodified.
- **vitest:** none — the frontend contract is unchanged.
- **Acceptance (manual, live Groq scout):** the §1 demo; plus the identity
  path (kind omitted -> byte-identical to B2 behavior).

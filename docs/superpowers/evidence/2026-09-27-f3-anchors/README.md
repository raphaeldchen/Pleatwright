# F.3's anchor structure is ADEQUATE — the doubt about it is refuted

Script: `f3_anchors.py` · Artifact: `f3-anchors.json` · Measured 2026-09-27

## What was in doubt

After Phase 0, F.3 (COrigami's deterministic ridge assignment: *"Y-shape
anchors; X-shape same, parallel opposite, perpendicular same"*) was put in doubt
on the grounds that `lizard` has only **2 Y-shape and 0 X-shape** ridge vertices
against **88 ridge variables** — seemingly far too few anchors to determine them.
That reasoning was recorded in `../2026-09-26-gap1-phase0/README.md` §2.1 and as
risk 5 of `../../specs/2026-09-27-pleat-filter-design.md`.

**It was the wrong statistic, and the doubt does not survive measurement.**

## The measurement

Posed RULE-AGNOSTICALLY, so the answer cannot depend on how F.3's propagation
rules are read: *a ridge in a connected component of the ridge graph containing
no anchor vertex can never be determined by any propagation rule, because no
information reaches it.* `reach_pct` is therefore an **upper bound on F.3's
reach under every possible reading of its rules.**

| subject | N | ridge pieces | Y (3 ridges) | X (4+) | components | anchored | **reach** |
|---|---|---|---|---|---|---|---|
| `starfish` | 4 | 32 | 2 | 1 | 1 | 1 | **100%** |
| `lizard` | 34 | 156 | 2 | 0 | 2 | 2 | **100%** |
| `frog` | 38 | 212 | 5 | 0 | 2 | 1 | **71.7%** |
| `horse` | 46 | 346 | 11 | 0 | 2 | 2 | **100%** |
| `bird` | 54 | 476 | 8 | 1 | 2 | 1 | **87.4%** |
| `guinea_pig` | 64 | 370 | 5 | 0 | 2 | 1 | **78.4%** |
| `octopus` | 74 | 708 | 13 | 1 | 1 | 1 | **100%** |
| `dog` | 74 | 798 | 19 | 0 | 2 | 2 | **100%** |

Needs only a sparse compile, so unlike every dense measurement in this line of
work it reaches `octopus` and `dog`.

**Why the anchor count was the wrong statistic.** The ridge graph is **barely
fragmented**: one or two components per subject, never more. A single anchor
propagates through an entire component, so two anchors are ample when the graph
is connected. Component sizes confirm it — `lizard` is `{78: 2}`, `octopus` a
single component of 708.

Anchors also **grow with subject size** (2 on `lizard` to 19 on `dog`), so the
scarcity does not worsen with scale. The three subjects below 100% each have
exactly one unanchored component, and it is always the smaller one (`frog` 60 of
212, `bird` 60 of 476, `guinea_pig` 80 of 370) — a suspiciously regular ~60-80
pieces, unexplained and worth a look if Phase B proceeds.

Ridge-vertex degrees are overwhelmingly **2** (a ridge passing through): 150 of
158 on `lizard`, 680 of 707 on `octopus`. Degree-1 endpoints and degree-3
Y-shapes are a handful each, and degree 4+ is 0 or 1 everywhere (`starfish` has
a single degree-5 vertex).

## What this does and does not establish

**Establishes:** the structural objection to F.3 is refuted. Information can
reach 100% of ridges on five of eight subjects and at least 71.7% on the rest.
F.3 is a viable lever again.

**Does NOT establish that F.3 works.** `reach_pct` is an upper bound on where
information can arrive, not a claim that the rules determine a consistent value
once it does. Two open questions remain, and the second is the real one:

1. **A real minority of ridges sit in unanchored components** on `frog`,
   `bird` and `guinea_pig`. Those need a second anchor source or stay in the CSP.
2. **One of F.3's three rules essentially never fires.** X-shapes are 0 or 1
   across the whole corpus, so "X-shape same" is inert here for the same
   straight-skeleton reason that killed the F.1.1 filter (see
   `../2026-09-27-pleat-filter/`). That leaves "parallel opposite, perpendicular
   same".

   **And those two cannot be applied at PIECE level.** At a degree-2 vertex the
   two ridge pieces are collinear — i.e. parallel — so "parallel opposite" would
   alternate M/V along a single straight ridge, which is not a sane reading. The
   rules must operate on distinct ridges at variable level, where merging has
   collapsed a geometric ridge to one variable and the degree-2 pass-throughs
   have disappeared.

**So the next measurement, if Phase B proceeds, is the VARIABLE-level ridge
graph**: classify each shared vertex by the orientation relationship of the
distinct ridge *variables* meeting there, and test whether "parallel opposite,
perpendicular same" determines a consistent assignment. That is a different
question from this one, and it is where F.3 would actually succeed or fail.

**Method note.** This is reported at piece level deliberately. Variable-level
merging can only *increase* connectivity — it may carry information across a
component boundary — so the piece-level reach figure cannot be argued down as
pessimistic.

## Reproduce

```bash
# from mcp_harness
PYTHONPATH=. ../.venv/bin/python3 -u \
    ../docs/superpowers/evidence/2026-09-27-f3-anchors/f3_anchors.py \
    ../docs/superpowers/evidence/2026-09-27-f3-anchors/f3-anchors.json
```

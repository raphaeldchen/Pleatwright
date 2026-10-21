# The packing diagram, drawn correctly for the first time

Follow-up 3 from [PR #75](https://github.com/raphaeldchen/origami-design-ide/pull/75)
— *"decide the packing diagram explicitly: fair trial on real data, or delete."*
Run 2026-08-06. **Outcome: kept, as a human debug render. Not an agent tool.**

## Why the earlier trial was not fair

`tree_render.packing_diagram` shipped with `scale=1.0` as a silent keyword
default, and **nothing in the repository ever passed a real one** — its only
caller was its own test module. So every diagram it could produce was drawn at
the wrong scale. Measured here, from one serve each:

| subject | packing scale | discs | oversize factor without it |
|---|---|---|---|
| star-4 | 0.5000000009 | 4 | **2.00×** |
| template-insect | 0.7633998419 | 9 | **1.31×** |

Those bracket the 1.25×–2.1× range recorded for the earlier radius defect, and
they are not a cosmetic error. At 2× the four discs cross each other
(`star-4-unscaled.png`), which reads as *the packer overlapped its circles* —
something a circle packing never does. Discs may touch; they never overlap.

PR #78 is what made the fair trial possible: it emitted `scale` from the parent
serve path, where it had read `null` on every serve until then.

## The correctness proof is visual, and star-4 is the one that gives it

`star-4-scaled.png`: four flaps of length 1.0 at scale 0.5 land as four
**quarter-discs, one per corner, tangent at the edge midpoints** — Lang's
canonical four-corner packing, exactly. A wrong scale would show gaps or
crossings. Nothing in the test suite asserts this; it is checkable only by
looking, which is also how the earlier radius defect was found.

star-4 is also the sharpest possible statement of what this view is for. The
**folded** star-4 is a featureless triangle face-on and a single line edge-on
([2026-08-05 §5 evidence](../2026-08-05-base-3d-calibration/)). The **packing**
of the same model is four cleanly separated quarter-discs. Same base, one step
earlier in the pipeline, and the anatomy is legible.

### One thing in the insect image that looks wrong and is not

`template-insect-scaled.png` has a zero-radius dot labelled `0` at the centre.
That is correct. `leaf_node_locations()` works on the **free** (unrooted) tree,
which is what circle packing is defined over, and in `template-insect` node 0
has degree 1 — so it is a genuine leaf, with length `0.0`, hence a disc of
radius zero. Verified against the fixture: free-tree leaves are
`[0, 4, 5, 6, 7, 8, 9, 10, 11]`, exactly the nine locs the serve returned. In
`star-4` node 0 has degree 4 and is correctly absent (4 locs, 4 discs).

## The verdict, and why it is not "ship it to the agent"

The corrected diagram carries real information the shadow-diff table cannot:
spatial adjacency (which flaps are neighbours), and how much of the square
nothing was allocated to — the large empty middle in `template-insect-scaled.png`,
which is [CLAUDE.md §1.1](../../../../CLAUDE.md)'s coverage concern made visible
at a glance.

It still does not look like an insect, and Gate-2 already measured that the
agent decides better from `read_base()`'s text. Both remain true. The
resolution is that this render's demonstrated value is **to a human debugging
the packer** — twice now, for defects no assertion caught — and its value to
the agent in-loop has never been demonstrated at all.

So it keeps its scope and gains an entry point:

- `mcp_harness/probe_packing_diagram.py` — serve a committed subject through
  the real ladder, draw its packing at the real scale.
- `server.last_serve_locs()` — the seam it reads. Deliberately **not** on
  `read_base()` and **not** an `@mcp.tool`, so per-leaf coordinates stay out of
  the agent's context.
- `scale` now defaults to a `None` sentinel and stamps `UNSCALED_STAMP` on the
  image when omitted, so the wrong picture can never again be produced silently.

## Files

- `probe_scaled_vs_unscaled.py` — regenerates everything here from one serve
  per subject, so the pair differs in exactly one argument.
- `star-4-scaled.png` / `star-4-unscaled.png` — the eye-checkable control.
- `template-insect-scaled.png` / `template-insect-unscaled.png` — the
  anatomy-bearing subject.

## What this does NOT establish

- **Not that the agent should see it.** Gate-2 stands; nothing here re-ran it.
  The fair trial was about whether the *render* works, not whether the *agent*
  benefits.
- **Not that rivers are drawn.** They are not, and `RIVER_NOTE` says so on
  every image. The empty middle is therefore "no leaf disc here", not
  "no paper structure here".
- **Not a coverage measurement.** Corner and edge flaps have most of their disc
  outside the square, so summing disc area would fabricate a number. The
  diagram shows the unallocated region; it does not quantify it.

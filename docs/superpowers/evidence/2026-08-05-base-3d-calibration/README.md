# Is a folded base legible in 3-D? — the section 5 calibration capture

Spec: [2026-08-04-base-inspection-loop-design.md](../../specs/2026-08-04-base-inspection-loop-design.md) §5.
Run once, 2026-08-05. **This closes the last open empirical question in that spec.**

## The question

The falsification record establishes that a uniaxial base cannot show anatomy in
its **flat-folded** form: every flap tip lands on one central line, the measured
stack ratios are 3–8×, and
[`bases.svg`](../2026-08-03-reparented-bases/bases.svg) draws exactly that.
What had never been measured is the **3-D simulator view**. The spec routed
around a claim nobody had tested. This tests it.

Reproduce: `PYTHONPATH=.:tests .venv/bin/python ../docs/superpowers/evidence/2026-08-05-base-3d-calibration/probe_base_3d.py` from `mcp_harness/`.

## Method, and two traps met while writing it

1. **`setFold` animates.** The first attempt screenshotted a few seconds after
   posting the message and caught star-4 at **60 % folded** — a torn state
   (THEOREM Z), worthless as evidence. `capture()`'s 20 s settle is
   load-bearing. This probe asserts `globals.creasePercent == 1` from the page
   rather than trusting elapsed time. ⚠ **The on-screen "Fold Percent: 60 %"
   label is stale in every image below** — it is driven by the slider widget,
   which the postMessage path does not update. The global is authoritative.
2. **One camera angle is not a measurement.** A flat-folded base is a *planar*
   object, so a single viewpoint invites "you just picked a bad angle." The
   camera is orbited and each angle shot.

## Measured

All three subjects, all `crease_percent: 1`, three angles each — 9 images.

| subject | verts | creases | fully folded | face-on (az 0) | edge-on (az 90) |
|---|---|---|---|---|---|
| **star-4** (4 equal flaps — the best case) | 9 | 16 | ✅ | featureless dark triangle | **a single vertical line** |
| **dog** (6 flaps — the canonical subject) | 35 | 62 | ✅ | crumpled angular grey mass, pink strain patches | thin irregular sliver |
| **quad** | 13 | 22 | ✅ | low grey wedge, ~4 crease lines, one strain patch | thin sliver |

## What the eye found

Answering the three questions in the order that matters:

| | star-4 | dog | quad |
|---|---|---|---|
| 1. Can you count the flaps? | **no** — one triangle | **no** | **no** |
| 2. Which flap is which limb? | **no** | **no** | **no** |
| 3. Could you tell if two flaps that should match don't? | **no** | **no** | **no** |

**Question 3 is the one that decides it** — that is the defect the whole
inspection loop exists to catch, and no view answers it. Note that a *yes* on
question 1 would not have been enough on its own: `served_leaves` already counts
flaps exactly, for free.

## Verdict: NO. The door is closed.

**star-4 settles it by itself.** Four equal flaps, the simplest base in the
repo, and face-on it is a featureless triangle while edge-on it is **a single
line** — zero thickness, because a perfectly flat-folded base is a *planar*
object. There is no camera angle at which four coplanar stacked flaps become
four visible flaps. If the best case fails this way, the harder cases cannot
pass, and they don't.

This is not a rendering-quality problem, a camera problem, or a
model-capability problem. It is what a uniaxial base **is**.

## One genuine nuance, worth recording

The three subjects are **not** identical. star-4 goes truly flat (a line
edge-on); dog and quad retain visible 3-D relief and carry pink strain patches.
So the 3-D view does carry *some* real information — **whether the base actually
collapsed, and where strain concentrates.**

That is a **foldability** signal, not an **anatomy** signal. And foldability
already has deterministic instruments that beat it: `DISP_GATE`
(`sim_capture.check_capture`) and `cp_audit`. So the nuance changes nothing
about the verdict — it just names precisely what the picture *does* show, so
nobody mistakes strain relief for anatomy later.

## What this closes

- Spec §2's open item — the only entry marked "unmeasured" — is now measured.
- Phase 3's cancellation stands on a second independent leg. Gate-2 already
  found the text table beats the render for recognisability; this shows the
  richest available render carries no anatomy at all.
- "Just look at the folded model in 3-D" should never be re-proposed. It has
  now been tested at the best case, at three angles, at a verified 100 % fold.

## Honest limits

- Three subjects, one simulator, one machine. The conclusion leans on the
  *geometric* argument (a flat-folded base is planar) which the images confirm,
  not on the sample size.
- Only the default **Material** view mode was captured. Strain mode would show
  more strain detail — which is a foldability read, already instrumented.
- This says nothing about **shaped** models. COrigami's 7-view judge looks at a
  posed model, and that remains the legitimate home for a visual judge. It is
  blocked on shaping, not on rendering.

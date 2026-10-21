# Automatic orientation checking: TWO SIGNALS TRIED, BOTH FAILED

**Do not re-derive this. Neither approach works, and the numbers are here.**

## The defect

The grid render's vertical axis increases DOWNWARD (tick 0 top, 24 bottom)
while the authoring prompt declares the output frame as `+y up`. A model must
flip the sign between reading and writing, and the prompt did not say so.
Measured on the finalized loop's 17 trees: **the dog and the rabbit did not
flip** — their limbs point at the ceiling (`dog elbow_L direction = [0, +7, 0]`).

**It is invisible to every metric in the spec.** Both inverted trees score
EXACT on leaf count, and `reading_fidelity` scores them fine, because the
readings are correct and only the derived directions are wrong. It survived two
full sweeps, an ablation, a replicate, and an author's review of the sheets. A
person looked at a picture and said "that looks weird."

## Attempt 1 — silhouette fit, both ways up

Compare `fit(tree)` against `fit(tree with the vertical axis negated)` by mean
distance to the mesh silhouette, centred and scaled so only orientation varies.
Anatomy-free by construction, and correct for radial subjects, which flip to
roughly themselves.

**Result: 0 true positives, 1 false positive, 2 false negatives.**

The flip-gain ranks `dolphin +0.852` **above** both genuinely inverted trees
(`rabbit +0.624`, `dog +0.250`). No threshold separates them. The mechanism is
clear in hindsight: silhouette fit conflates SHAPE mismatch with ORIENTATION,
and a leaping dolphin's arch fits its own flipped tree well for reasons that
have nothing to do with which way is up.

## Attempt 2 — vertical skew agreement

Narrower question: is the vertical mass distribution top- or bottom-heavy, and
do tree and mesh agree in sign?

**Result: 1 true positive, 3 false positives, 1 false negative.**

Skew is dominated by limb-node density, not by body orientation, so the frog,
elephant and ant all read inverted while upright.

## Why it stops here

A third signal tuned until it fits these 17 points would be overfitting a gate
to the only data available — this project's named recurring failure mode. Both
attempts are preserved in `scripts/FAILED_tree_orientation.py` so the next
person spends their effort on a *different* idea rather than these two.

## What is shipped instead

1. **The prompt now names both frames** and the required sign flip
   (`loop_lib.SYSTEM`). It addresses the cause; it cannot guarantee compliance,
   and 15 of 17 already complied without it, so a small sweep cannot show that
   it worked.
2. **The human gate (spec §5) is the only thing measured to catch this.** That
   is no longer a formality in the design — it is the sole defence against a
   whole defect class, and `render_tree_sheet` earns its place there for
   exactly the reason it was cut from the model-facing loop: showing the figure
   to a *person* finds what showing it to the model did not.

## An idea worth trying, that was not

Compare the tree's directions against the model's OWN quoted readings rather
than against the mesh. The readings are in image coordinates and the directions
in the declared frame, so a correct conversion makes them anti-correlate. It
needs a node-to-reading correspondence, which the current schema does not
capture — adding a `reading` field per node would supply it and would make the
check nearly free.

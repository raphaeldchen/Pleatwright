# Crease patterns for a box-pleating review

Thank you for looking at these. Nothing here has been folded by hand: the owner has not folded these models yet. They are crease patterns that a program computed and checked for local flat-foldability, and your intuition about whether they are sensible is exactly what we are missing. Please mark up whatever bothers you; there are no wrong answers.

## What the program is

Pleatwright turns a stick-figure tree (a body with limbs of given lengths, read off a 3-D model of an animal) into a box-pleated crease pattern for one uncut square. It packs the flaps on an N x N grid, runs rivers between them, adds the pleats, and then shapes the base towards the animal. Every pattern below uses the whole square, with no cuts.

## What changed

Until now the program laid out a body's flaps in full-width strips: a river crossed the whole sheet from edge to edge, and every strip cost its full width in grid units. The new layout lets a river wrap a hub's flaps in a corner or edge pocket instead. A river can bend in an L around a corner, or in a U around an edge pocket, like the bent rivers in COrigami's published packings (arXiv:2606.26299). It is only used when the whole sheet then fits on a strictly smaller grid. Of 51 test trees, 10 got a smaller grid; the other 41 are unchanged. Here are four of the ten, shown before and after, plus two for a different question.

## Files

Every tree has a `packing_cp.svg` and a `solving_cp.svg`, each with a `.png` rendering beside it (the SVG is the original).

* **packing**: the flap layout. Green lines are hinges (the borders of flaps and rivers), red are ridges, black is the sheet border. Rivers are the strips between double green lines. This is where the bent rivers show.
* **solving**: the full box-pleated crease pattern, with mountain and valley assigned. Red = mountain, blue = valley, black = border.

File names are `<tree>_<grid>_<before|after|current>_<packing|solving>_cp`. "Before" is today's main branch, "after" is with the new layout. "Current" is a pattern the program produces today, which this change did not alter.

## The trees

"Mean layers" is one number for the whole model: the total paper area given to all the flaps, divided by the total length of all the flaps, which is the average number of paper layers across a limb's width. It is a rough proxy for how thick the limbs are. A larger grid means more pleats per limb, since the limb lengths are fixed.

| tree | grid before | grid after | mean layers before | mean layers after | new river shape |
|---|---|---|---|---|---|
| scorpion_2 | 86 | 64 | 62.7 | 33.2 | nested L around a left-edge pocket (not mirror-symmetric) |
| crab_3 | 104 | 86 | 82.5 | 53.1 | nested U, open to the bottom edge, mirror-symmetric |
| elephant_3 | 80 | 68 | 49.7 | 35.1 | L around the bottom-left corner pocket (not mirror-symmetric) |
| elephant_1 | 72 | 64 | 45.0 | 33.0 | U around a top-edge pocket, mirror-symmetric |

Two patterns that are thickest at present (highest mean layers), unchanged by this work:

| tree | grid | mean layers | note |
|---|---|---|---|
| spider_2 | 136 | 100.2 | highest of all 51; the layout search used up its time budget, so no bent river was found |
| dog_1 | 72 | 52.9 | the next-highest unchanged tree; the highest changed one, crab_3 after, is in the table above |

(crab_3 after, at 53.1, is also the second-highest of all 51, so it covers the second slot. dog_1 is included as a certified pattern to compare against.)

Status of the checks: every pattern is locally flat-foldable at every vertex. elephant_1, elephant_3 and dog_1 also have a global layer-order certificate. scorpion_2, crab_3 and spider_2 do not: the global check (a SAT solver) is too large to run on them (reported as OVERSIZE), before and after the change alike, so for those only the local result stands. That is not a failure, but it is weaker evidence. The river shapes above are our reading of the packing patterns, not a program label.

## Questions

1. Could you collapse this by hand?
2. Do the river bends look like good box pleating?
3. For these models, does the grid size or the flap thickness worry you more?

Please answer these per pattern if you can, and say which of the before/after patterns you would rather start from. Anything else you notice, such as a river that looks wasteful, a bend that looks unfoldable, or an area that looks too thick, is welcome.

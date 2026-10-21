# Branching-packer evidence (2026-10-10)

The probe and gate for spec
`docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md` §4 and plan
`docs/superpowers/plans/2026-10-10-branching-hub-packer.md` Task 7.

## How it was produced

From `mcp_harness/`, at commit a989761 (Tasks 1–6; the later `ORDER_CAP` fix
does not change any pocket of at most five strips, and every tree here has at
most four):

```
PYTHONPATH=.:tests $PY ../docs/superpowers/evidence/2026-10-10-branching-packer/probe_branching.py OUT
```

`probe_branching.py` applies three named edits from `tests/test_pack_chain.py`
to every one of the 51 artifact trees and keeps the trees whose hub graph
branches:

* `antlered` puts forked antlers on the head;
* `toed` puts two toes on each foot of the longest leaf pair;
* `lopsided` is `antlered` with unequal antler rivers, so the antlers form no
  hub pair.

Each kept tree runs through the full pipeline (`pipeline.run`,
`certify_global=True`), one row per tree in `records.jsonl`. Total time was 155
minutes, sharing the machine with the byte gate and the test suite. The
slowest tree took 249 s.

## Results

| edit | trees | packed | rungs | locally flat-foldable | CERTIFIED | median grid / unedited |
|---|---|---|---|---|---|---|
| antlered | 35 | 35 | symmetric 18, asymmetric 17 | 35/35 | 27/35 | 1.30 |
| toed | 39 | 36 | symmetric 29, asymmetric 7 | 36/36 | 28/36 | 1.18 |
| lopsided | 35 | 35 | symmetric 22, asymmetric 13 | 35/35 | 4/35 | 1.68 |

* **106 of 109 branching trees pack, and every packed one folds.**
  * Every solving vertex of every packed model is locally flat-foldable.
  * Global verdicts:
    * 59 are CERTIFIED;
    * 46 are `OVERSIZE+LOCAL_SAT`;
    * 1 is `OVERSIZE` (`toed elephant_0`, whose heuristic labels were already
      646/646 locally flat-foldable).
  * OVERSIZE means the model is too large for the global SAT certifier
    (`solve.certify`: `raw_triple_bound` over its cap). It is not a fold
    failure. 12 of the 51 artifact trees are in the same class
    (`2026-10-06-corigami-pipeline/records.jsonl`).
* **The symmetric rung.** 69 of the 106 land on the mirror-symmetric rung. The
  other 37 land on the unmirrored-rows rung. `pipeline.py` exists for exactly
  that: "unequal declared pairs, or hinge parities a symmetric row cannot
  meet". `antlered dog_0` is one of them; its head river is 9, an odd length,
  and an odd river is a known cause. This was not isolated here. Hub pairs
  are still mirrored on that rung, because `nest` splits them at the axis on
  every rung.
* **`lopsided` costs the most paper.** Its unpaired antlers become two
  full-width strips stacked one above the other (median grid 1.68 × the
  unedited roll's). Its larger grids push 31 of 35 into OVERSIZE.

### The three misses: the grid cap, from stacked strips

| tree | failure | pipeline cap `max(2G, G+60)` | certifies uncapped at N | unedited roll N |
|---|---|---|---|---|
| toed crab_3 | packing, 0 candidates | 106 | 108 | 104 |
| toed elephant_3 | packing, 0 candidates | 106 | 110 | 80 |
| toed spider_2 | packing, 0 candidates | 132 | 142 | 136 |

The uncapped N values were measured on 2026-10-10 by the plan's prototype,
which is the same code. In each of these trees a pocket stacks its children
as full-width strips. A long, thin branch then costs a whole strip with bands
above and below, so the parent's height exceeds the cap. In crab_3, the toed
`leg1` pair under `carapace_row1` sits above the four-hub carapace chain.
elephant_3's ears are declared as a pair with unequal lengths (6 and 5), so
they form no hub pair. The path packer would place such a limb as a column.
This is the input the spec's "Fallbacks" section waits for: placing the limb
as a column (collapse-and-carve) or changing the cap policy.

## Byte-identity gate

At a989761 plus the doc edits (the 8e284ab8 tree), `python -m pleatwright
fold` ran on all 51 artifact trees. Every output file was compared with
`~/Desktop/origami_samples_artifact_trees`:

```
51 folders, 204 identical, 0 different []
```

## Looked at, not only scored

* **antlered dog_0** (N=62, asymmetric, CERTIFIED). Reads as a dog with two
  mirrored forked antlers at the head. The packing CP shows the two L-shaped
  antler bands meeting on the axis at the top.
* **antlered horse_1** (N=70, symmetric, CERTIFIED). Reads as a horse with
  forked antlers on the head. The packing CP is mirror-symmetric, with the
  antler pockets at the top corners.
* **toed crab_0** (N=78, symmetric, OVERSIZE+LOCAL_SAT). The packing CP is
  mirror-symmetric and the claws and legs fold. The length-2 toes are too
  small to tell apart from the leg tips at the overview's render size, so
  this view cannot confirm them.

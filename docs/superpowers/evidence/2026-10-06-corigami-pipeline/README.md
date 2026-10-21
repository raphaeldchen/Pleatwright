# COrigami pipeline on the 51 "Bases in Triplicate III" trees (2026-10-06)

> **2026-10-07:** this pipeline is now **Pleatwright**, package `mcp_harness/pleatwright/`
> (see `docs/superpowers/specs/2026-10-07-pleatwright-retire-treemaker-design.md`).
> The body below is the record as written on 2026-10-06.

Deliverable: `~/Desktop/origami_samples_artifact_trees/` — 51 folders
`<Subject> roll <n>_<grid>/` with `packing_cp.svg`, `solving_cp.svg`,
`shaping_cp.svg`, `overview.png`, the exact layout of COrigami's released
`~/Desktop/origami_samples/` (34 MB; not committed).

Reproduce one model (repo-root `.venv`, matplotlib installed):

```
cd mcp_harness && python -m pleatwright fold fixtures/full17_v3_sticks/dog_0.json --out /tmp/out
```

All 51 in parallel: `python batch.py <out_dir> <records.jsonl> 1 2400 6`
(this directory), then `python summarise.py <records.jsonl>`.

## Results (`results.md`, `records.jsonl`)

| | |
|---|---|
| trees completed | **51 / 51** |
| solving CP: every vertex locally flat-foldable (App. D crimp test) | **51 / 51** |
| solving CP: globally certified (facewise layer order, SAT) | **39 / 51**; the 12 largest (grid 66-136) exceed the SAT size guard and are solved locally (`OVERSIZE+LOCAL_SAT`) |
| shaping CP: every vertex locally flat-foldable | **51 / 51** |
| folded model: max closure error / max mean axial strain | 6.3e-6 grid units / ~1e-6 |
| tree similarity (App. C.2, Procrustes) | median 0.996, min 0.938 (octopus_0: arms 1 unit long) |
| packing rung | 45 symmetric, 6 unmirrored (crab_3, dog_2, elephant_3, frog_0, spider_2, starfish_0); all at authored lengths |
| grid sizes | 10 - 136 |
| wall-clock, 6 workers | 35 CPU-minutes total |
| orchestrator | tree shaping (§3.6 algorithmic); the LLM/VLM path is built but the `.env` Anthropic key returns 401 |

Independent checks:
* every delivered `shaping_cp.svg` re-parsed with COrigami's SVG rules and
  re-folded: closure <= 1.2e-6 on the unit square;
* the files load and fold in COrigami's own Visualiser (its `app.js`,
  served locally) at 0.0000% strain;
* the crimp-test port agrees with `cp_audit.arrangement_ok_at_vertex` on
  256/256 labellings; the folder port closes COrigami's own Ram shaping CP.

## Baseline: the repo's `box_pleat` compiler on the same trees

`box_pleat_baseline.jsonl` (`box_pleat_baseline_probe.py`, sparse labelling,
300 s cap): 7 emit, 31 time out, 7 stop at contours, 4 refused at tree, 2 fail
to pack — the measurement that sent the packer/solver to a new construction
(spec §Prior art).

## Failure history worth keeping

* **guinea_pig_1 read similarity 0.49** until chains through a degree-2
  authored root were folded to the REVERSED stick direction; the direction
  check had compared against the same reversed reference and passed.
* **dog_2 could not pack symmetrically at any grid**: its 11-unit river puts
  opposite hinge parities on its two sides while both slabs' column
  boundaries (hw - 6, hw - 8) share one parity.
* **Folded views were rotated** until the folder's start-face frame was
  mapped back to the world frame; Procrustes similarity cannot see a rigid
  rotation, so only looking at the renders caught it.

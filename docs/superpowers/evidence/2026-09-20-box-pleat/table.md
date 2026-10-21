| subject | leaves | rivers | unit | N_lb | N | scale_bp | scale_tm | ratio | hull_coverage | tip_hull_coverage | tm_tip_hull_coverage | flap_width_units | stage_reached | layers_tried | maekawa_defects | lint_class | flat_fold_ok | layer_order | pack_ms | failure | tm_error |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dog | 6 | 1 | 0.044444 | 46 | 74 | 0.013514 | 0.016131 | 0.838 | 1.0 | 1.0 |  | 1 | emit | 10 | 0 | PASS | True | consistent | 21083.8 |  |  |
| cat | 6 | 1 | 0.08 | 34 | 46 | 0.021739 | 0.019971 | 1.089 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 2272.8 | ContourFail: ContourFail(kind='collision', site=((2, 92), Fraction(0, 1), Fraction(1, 1))) |  |
| horse | 7 | 1 | 0.05 | 32 | 46 | 0.021739 | 0.022057 | 0.986 | 1.0 | 1.0 |  | 1 | emit | 5 | 0 | PASS | True | consistent | 2676.2 |  |  |
| rabbit | 6 | 1 | 0.05 | 34 | 54 | 0.018519 | 0.022751 | 0.814 |  | 1.0 |  | 1 | assign | 56 |  |  |  |  | 5284.7 | AssignFail: AssignFail(kind='budget', site=500000) (measured 2026-09-23 at layer_budget=100, 1be01b0; not independently re-measured at the shipped default layer_budget=200 -- 56 << 100 << 200 means the node budget, not the layer budget, binds either way -- see spec 2026-09-22-pleat-reassignment-design.md sec 11) |  |
| guinea_pig | 5 | 1 | 0.033333 | 54 | 64 | 0.015625 | 0.014799 | 1.056 | 1.0 | 1.0 |  | 1 | emit | 20 | 0 | PASS | True | consistent | 4005.9 |  |  |
| elephant | 6 | 1 | 0.033333 | 44 | 56 | 0.017857 | 0.017213 | 1.037 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 3681.3 | ContourFail: ContourFail(kind='collision', site=((4, 0), Fraction(0, 1), Fraction(1, 1))) |  |
| lizard | 6 | 1 | 0.066667 | 34 | 34 | 0.029412 | 0.022673 | 1.297 | 1.0 | 1.0 |  | 1 | emit | 9 | 0 | PASS | True | consistent | 23.1 |  |  |
| frog | 5 | 1 | 0.057143 | 36 | 38 | 0.026316 | 0.022306 | 1.18 | 1.0 | 1.0 |  | 1 | emit | 22 | 0 | PASS | True | consistent | 154.4 |  |  |
| bird | 6 | 0 | 0.044444 | 36 | 54 | 0.018519 | 0.021727 | 0.852 | 1.0 | 0.7407407407407407 |  | 1 | emit | 1 | 0 | PASS | True | consistent | 156.4 |  |  |
| bat | 6 | 1 | 0.036364 | 28 | 40 | 0.025 | 0.029426 | 0.85 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 1677.2 | ContourFail: ContourFail(kind='collision', site=((34, 0), Fraction(0, 1), Fraction(1, 1))) |  |
| dolphin | 5 | 1 | 0.036364 | 36 | 48 | 0.020833 | 0.027998 | 0.744 |  | 0.5 |  | 1 | contours | 0 |  |  |  |  | 2339.4 | ContourFail: ContourFail(kind='collision', site=((10, 0), Fraction(0, 1), Fraction(1, 1))) |  |
| starfish | 5 | 0 | 0.4 | 4 | 4 | 0.25 | 0.292893 | 0.854 | 1.0 | 0.75 |  | 1 | emit | 1 | 0 | PASS | True | consistent | 3.4 |  |  |
| octopus | 9 | 0 | 0.026667 | 52 | 74 | 0.013514 | 0.014854 | 0.91 | 1.0 | 1.0 |  | 1 | emit | 2 | 0 | PASS | True | consistent | 1456.0 |  |  |
| crab |  |  |  |  |  |  |  |  |  |  |  |  | tree | 0 |  |  |  |  | 0.0 | AsymmetricPair: pair (4, 6): r 13 vs 9, hub 1 vs 1 | no contracted tree (stage=tree failure) |
| spider | 9 | 0 | 0.05 | 54 | 90 | 0.011111 | 0.015186 | 0.732 | 1.0 | 1.0 |  | 1 | emit |  | 0 | PASS | True | contradiction (2026-09-22, pre-pleat-reassignment; 2026-09-23 re-measurement at layer_budget=25 did not resolve in 60 min and was stopped -- no post-feature verdict) | 402.4 |  |  |
| scorpion | 11 | 1 | 0.066667 | 48 | 70 | 0.014286 | 0.01663 | 0.859 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 109873.3 | ContourFail: ContourFail(kind='collision', site=((0, 96), Fraction(0, 1), Fraction(1, 1))) |  |
| ant | 8 | 0 | 0.04 | 46 | 56 | 0.017857 | 0.015675 | 1.139 |  | 1.0 |  | 1 | contours | 0 |  |  |  |  | 3196.2 | ContourFail: ContourFail(kind='collision', site=((0, 58), Fraction(0, 1), Fraction(1, 1))) |  |

# Handoff: the corigami-2 stick-figure judge rebuild

**2026-08-29/30. 14 units, PRs #149–#166, 164 billed calls. All on `main` at `4094fc3`.**

## Why this happened

`vlm_judge.py` scores a Metric Tree against the prompt that asked for it. Its
entire design was credited to COrigami (arXiv:2606.26299). **The credit pointed
at the wrong stage of that pipeline**, and every measured limitation followed.

Our five criteria — `appendage_count`, `topology`, `proportionality`,
`differentiation` ("quaternary"), `aesthetic_refinement` ("quinary") — are
COrigami's **Single Model Evaluation Mode Prompt**, Appendix I p.30, which
judges *"a 3D-simulated fold"* from *"snapshots of the final 3D folded state"*.
The ordinals were lifted verbatim. Their **stick-figure** judge is §3.1 and uses
four different criteria (topological accuracy, proportional feasibility,
semantic recognisability, structural complexity) plus four renders.

So the module docstring said *"never re-propose showing this judge a folded
base"* and then applied the rubric written exclusively for one.

## What shipped

| area | change |
|---|---|
| rubric | `corigami-2`: §3.1's four criteria, weights 4/3/2/1 |
| payload | named hubs + per-stick azimuth/elevation; angles kept in separate frames and never fabricated |
| flap count | `build_payload` and `_serve_block` both moved to `shadow_tree.flap_ids` (undirected degree 1) |
| labels | `leaf_labels` now reaches `read_base()` — it had **zero occurrences** in `server.py` |
| images | relative-`--out` double-join fixed; the four-view sheet can reach a judge |
| report card | `reasons` and the per-criterion table render, in rubric priority order |
| offline | `base_report --replay` exercises `--judge` for free |
| pairwise | `judge_compare.py` — COrigami's Comparison Judge Mode, cross-subject comparison **refused** |
| instrument | `test_rubric_answerability.py` — every criterion must be movable by some payload mutation |
| extraction | `IDE_EXTERNAL_R` **default ON**, kill switch retained |
| corpora | both live-recorded; corigami-1 frozen beside them |

## The measurement, honestly

| gate | corigami-2 | corigami-1 | delta |
|---|---|---|---|
| A labelled | +0.617857 PASS | +0.676389 PASS | −0.058 |
| A stripped | +0.489286 PASS | +0.527778 PASS | −0.039 |
| B labelled | 0.813750 PASS | 0.899305 PASS | −0.085 |
| B stripped | 0.766964 FAIL | 0.816666 PASS | −0.050 |
| C | gap +0.227971, row max 3/5 FAIL | +0.239653, 3/5 FAIL | −0.012 |

**Not one delta clears the 0.169 LSD.** By this project's own rule the rewrite
**did not move the gates**, in either direction. Gate B stripped *crosses its
bar* on a −0.050 move — a bar crossing inside the noise floor, not a regression.
The verdict is unchanged: **usable for ranking, within one subject.**

What changed is categorical, not numeric: the replies now cite per-stick angles,
named hubs, path lengths and stub counts, and **none of 140 mentions fold
sharpness**.

### The live lead

    semantic_recognisability   gap +0.223125   row max 4/5   <- Gate C's bar
    anatomy (what is gated)    gap +0.227971   row max 3/5

`semantic_recognisability` is **excluded from `anatomy` by construction**, so
corigami-1's bars could transfer. The subject signal exists and sits in the one
criterion the gate cannot see. Gating it needs a **fresh pre-registration** —
4/5 is a discrete count the continuous LSD does not cover.

## The extraction loop

`IDE_EXTERNAL_R` is now ON. Measured, three subjects, both arms:

| subject | arm | leaves | pairs | stubs | R | voxels built |
|---|---|---|---|---|---|---|
| octopus | OFF | 4 | 1 | 0 | 4 self | **1** |
| octopus | **ON** | **6** | **3** | 0 | 9 external | **3** |
| lizard | OFF→ON | 5 → 5 | 1 → 1 | 0 | 5 → 6 | 3 |
| dog | OFF→ON | 6 → 6 | 2 → 2 | 0 | 6 → 6 | 3 |

`stub_flaps` 0 on both octopus arms — the extra anatomy is **found, not
invented**. **The dog is a verified no-op**, which is what licenses believing
the octopus moved for the right reason.

**Ceiling, unchanged:** the octopus has 9 appendages and serves 6. The clamp
`r_eff = min(max(R,4),8)` reads 1.0000 for an 8-leaf serve even against a
correct R of 9. `MAX_LEAVES` untouched.

## Known open

1. **The unsourced `43/100` still ships inside `SYSTEM_PROMPT`.** It is in no
   paper we cite; "43" appears once in COrigami, inside "743". Digest-bound —
   fixing it costs 164 billed calls. The last deferral was missed by a re-bless.
2. **6 of 140 replies do not parse** — 5 empty, 1 answered the **American**
   `semantic_recognizability`. **All six fall in E2**, so Gate C rests partly on
   cells sampled 3 and 2 times; two are diagonals. `--report` prints no `parsed`
   column, so none of it is visible. Gates A and B are clean 4/4.
3. **The anatomy table is 14 rows.** Everything outside it falls back to
   self-derived R. Scaling path documented in
   `plans/2026-08-29-anatomy-oracle-beyond-the-table.md`; the invariant is that
   **the oracle may never read the extracted skeleton**.
4. **The judge still has no production caller.** Opt-in CLI flag only.

## Traps this session re-confirmed

- **Full suite OOMs at ~57%** (Error 137). Split into separate pytest processes:
  **4316 passed / 19 failed / 12 skipped**, no OOM.
- **All 19 failures are the borrowed `.so`** — built 2026-08-05, the C++ needing
  those symbols landed 2026-08-15. `run_edge_optimization_and_export`,
  `edge_strain_report`, `build_and_export_with_axis` all absent from the binary.
  Fifth recorded firing.
- **A worktree has no `.env`.** `load_env()` resolves relative to its own module,
  returns `False` **silently**, surfaces as "requires an API key".
- **An identity-linked API key needs `anthropic-workspace-id` on every
  endpoint** — measured on `/v1/messages` and `/v1/models`. The id cannot be read
  off the key. Diagnose in order: 401 → 400 workspace → 400 credits → 200.
- **Merging a parent PR before its children reach it strands the whole stack.**
  #155 hit `main` 30s before its first child merged into it; #157–#162 all
  reported MERGED while none was an ancestor of `main`.
- **GitHub Actions is out of minutes**: 2s jobs, zero steps, no logs. CI has not
  run on any of this.

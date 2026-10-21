# Packing layout choice and efficiency metrics (efficiency slice 1)

Status: design, approved in conversation 2026-10-16; builder-checked.
Research behind it: `reports/Box pleating efficiency techniques.md` and
`research_notes/Box pleating efficiency techniques/` (both in this branch).

## 1. Why

Pleatwright's packing ladder (`mcp_harness/pleatwright/pipeline.py`, `_run`)
takes the FIRST rung that builds a base: mirror-symmetric rows, then unmirrored
rows, then every length doubled. It never asks whether a later rung packs on a
smaller grid. On the 51 artifact trees the unmirrored rung packs on a strictly
smaller grid for 16 trees (dolphin_0 50→32, lizard_1 64→38, ant_0 102→70,
octopus_3 84→56, ...), and the folded model's size goes as 1/N, so those models
come out up to 1.68× larger from the same sheet. The cost is a crease pattern
that is no longer mirror-symmetric.

That is a real trade-off, and the owner's call (2026-10-16) is to **show it to
the person folding, with a recommendation**, rather than settle it in code.
Alongside it, every run starts recording **paper-efficiency metrics**, because
later efficiency work (river routing, level shifters, Pythagorean stretches;
see the research report's ordering) needs a baseline to beat, and today there is
no efficiency number anywhere in the code.

Probe evidence (2026-10-16, full pipeline with the symmetric rungs disabled;
script and results in `docs/superpowers/evidence/2026-10-16-layout-choice/`):
every smaller unmirrored layout solves, certifies and shapes, with all solving
and shaping vertices flat-foldable. The 11 trees that were `CERTIFIED` at their
symmetric grid stay `CERTIFIED` (dolphin_0/1/2, lizard_1/2, bird_1, frog_1/2,
dog_0/1, horse_0). Of the five that were `OVERSIZE+LOCAL_SAT` at their
symmetric grid, four become fully `CERTIFIED` at the smaller grid (ant_0
102→70, octopus_3 84→56, ant_2 78→64, elephant_0 80→72) and octopus_2 (66→60)
stays `OVERSIZE+LOCAL_SAT`. A smaller grid is also a smaller certification
problem (`asym_cert.jsonl` in the evidence folder).

## 2. Goals, non-goals, anti-goals

Goals
1. Every fold computes the mirror-symmetric layout and searches for an
   unmirrored layout small enough to matter (§5.2), and records what it found.
2. When the smaller layout makes the model materially larger (§4), the person
   chooses: a question card in the app, a terminal prompt in `run`.
3. The recommendation comes from the numbers; the VLM writes the explanation for
   this subject.
4. `fold` (no VLM, no human) applies the same rule on its own, with a flag to
   override it.
5. Every run record carries the efficiency metrics in §6.

Non-goals (later slices)
* Changing what the packer can produce: no river routing, level shifters,
  Pythagorean stretches, 22.5° gadgets.
* Making the unmirrored search faster (the `_pocket_solutions` 4^n row
  assignment). This slice bounds its time instead (§5.2).
* Choosing between more than two layouts, or among the doubled-length rung.

Anti-goals (would make this a failure even if it works)
* Silently dropping mirror symmetry when the gain is small.
* The VLM deciding the layout. Two earlier VLM judges in this project (the
  stick-figure judge and the extraction judge) never changed an outcome, and the
  folded previews of the two layouts look nearly identical (dolphin_0, checked
  by eye), so a picture-based judgement has little to go on.
* Making a fold fail, or stall indefinitely, because the second layout search
  is slow or the VLM call fails.

## 3. Prior art (CLAUDE.md §0)

| source | what we take | what we leave |
|---|---|---|
| BP Studio optimizer (Tsai; MIT, `src/client/plugins/optimizer`) | rank layouts by grid size first; its integer stage starts one size *below* the continuous optimum | its continuous circle relaxation (out of scope) |
| COrigami App. E.1 / §3.2 | `G_init` as a reported floor | its selection by VLM score at the cost of efficiency (its own words) — rejected for the recommendation, kept only for the prose |
| B. Wong, Origami Design Class 4.2 | the perimeter lower bound N ≥ ⌈total tree length / 2⌉, tighter than `G_init` on 37/51 trees | — |
| Lang & Demaine, Origami⁴ §2.1 | scale m (folded flap length / tree length) as the efficiency measure; on an integer grid m = 1/N | — |
| Claude Code's question tool | the card shape: a question, labelled options with a short description, the recommended option first and marked | — |

## 4. The rule

Let `N_sym` be the grid of the first mirror-symmetric layout that builds, and
`N_small` the grid of the first unmirrored layout that builds (`pack.candidates`
already yields in increasing N, so "first" is "smallest").

    gain = N_sym / N_small          # how much larger the folded model is

* `gain ≥ 1.10` → **ask**, recommending the smaller layout.
* `gain < 1.10`, or no unmirrored layout found within the budget → use the
  symmetric layout, no question.
* No symmetric layout → use the unmirrored one, no question (today's behaviour
  for crab_3, dog_2, elephant_3, frog_0, spider_2, starfish_0).
* Neither → the doubled-length rung, as today.

`GAIN_THRESHOLD = 1.10` is a named constant. It was chosen because the 16 trees
split there with a clean gap: gains of 3–5% below it (bird_1, dog_0, dog_1,
frog_1, frog_2, horse_0) and 10% or more at or above it (elephant_0 1.11,
lizard_2 1.10, octopus_2 1.10, then 1.22–1.68). The owner first proposed an
absolute 8–10 grid units and accepted the relative rule on the reasoning that
the same unit gap means 25% at grid 32 but 6% at grid 136.

Ties and order: when `gain < 1.10` the symmetric layout wins even though the
unmirrored one is smaller. The recommendation is always "smaller" whenever the
question is asked.

## 5. Pipeline changes (`mcp_harness/pleatwright/`)

### 5.1 Two entry points instead of one

* `pipeline.pack_options(tree) -> dict`: loads and contracts the tree, packs
  the symmetric and unmirrored layouts, builds each base, and returns both
  options with their grid sizes, efficiency metrics (§6), `gain`, and the
  rule's verdict (`ask` | `symmetric` | `smaller` | `only_unmirrored` |
  `doubled`). Packing only: no solving, nothing written to disk except what the
  caller asks for.
* `pipeline.run(tree, out_dir, *, layout="auto", ...)`, where `layout` is
  `"auto"` (apply §4 and never ask; this is `fold`'s default), `"symmetric"` or
  `"smaller"`. A requested layout that does not exist (e.g. `"smaller"` when the
  unmirrored search found nothing) falls back to the one that does, and the
  record says so. *(Builder-check call)* `run` never re-searches a layout
  that `pack_options` already found: `pack_options` persists both layouts (in
  the run's work directory, in the app; in memory, for `fold`) and `run` takes
  the chosen one. A user's choice can therefore never be undone by a second
  search running out of budget, and the packing time is not paid twice
  (octopus_2's unmirrored search took 109 s).

### 5.2 Bounding the unmirrored search

The unmirrored rung is usually fast (median well under 5 s), but octopus_3
took 45 s, octopus_2 109 s, and scorpion_0 ran more than 11 CPU-minutes without
a candidate. Two bounds apply once the symmetric layout is found
*(builder-check calls)*:

* **Grid cap.** Only grids `N ≤ ⌊N_sym / 1.10⌋` are searched, because a larger
  unmirrored layout can never change the outcome (§4). Trees whose unmirrored
  N equals `N_sym` (most of the 51) then finish quickly.
* **Deterministic work budget.** The search stops after a fixed amount of
  packer work (`SMALLER_WORK_BUDGET`, counted in row assignments / nodes
  tried, not seconds), so `fold --layout auto` gives the same answer on every
  machine and the byte-identity gate stays meaningful. It is calibrated at 3,500,000
  ticks: octopus_2's deterministic 3,395,895 plus 3%, which costs about 165 s
  worst case (scorpion_0) on a loaded host. The
  budget must be counted inside the packer's inner loops (`pack.candidates`,
  `_pocket_solutions`'s row assignment, and `nest.py`'s search), not only
  between yielded candidates, because the scorpion case never yields.

Past either bound the record says why (`"n_smaller": "none_below_cap"` or
`"budget"`) and §4 treats it as "not found". When the symmetric layout is NOT
found, the unmirrored search runs as today, with neither bound (it is then the
only way to get a model).

### 5.2a When the chosen smaller layout fails downstream

*(Builder-check call.)* The probe found no such case, but if a smaller layout
fails at solving or shaping: under `layout="auto"` the run folds the symmetric
layout instead and records `"reason": "fallback"` with the error; under an
explicit `"smaller"` (the user's or the flag's) the failure is reported as
today, and in the app Retry returns to the layout card with a note that the
smaller layout failed, so the other option can be picked.

### 5.3 Records

`rec["layout"]` = `{"chosen": "symmetric"|"smaller", "reason":
"rule"|"user"|"flag"|"only_option"|"fallback", "n_symmetric": int|None,
"n_smaller": int|None|"none_below_cap"|"budget", "gain": float|None,
"threshold": 1.10}`. `packing_rung`
stays as it is. The output folder name stays `<Subject>_<grid>` with the chosen
grid.

## 6. Efficiency metrics (every run, both options)

Computed on the layout and base, recorded under `rec["efficiency"]` for the
chosen layout and inside each option of `pack_options`:

| key | definition |
|---|---|
| `grid` | N |
| `grid_init` | COrigami `G_init` (`pack.grid_init`, already recorded today) |
| `perimeter_bound` | ⌈T / 2⌉, T = sum of every edge length in the contracted tree (flaps and rivers) |
| `n_over_bound` | N / `perimeter_bound` (median 1.33 on the 51 trees today) |
| `scale` | 1 / N (Lang's scale for integer tree lengths; doubled-length runs report it in original units) |
| `slack_fraction` | 1 − (Σ minimum flap polygons + Σ river cells) / N². A flap's minimum polygon is the L∞ ball of radius L (its length) centred on its tip, clipped to the paper — Lang's box-pleated minimum, r² / 2r² / 4r² for corner / edge / interior tips (median 0.39 today) |
| `flap_expansion` | per flap: flap cells / its minimum polygon cells; recorded as the max and median |
| `mean_layers` | Σ flap cells / Σ flap lengths (the strip is one unit wide, so this is the average layer count of a flap; median ≈ 34 today) |

The baseline probe that measured these on the 51 trees
(`docs/superpowers/evidence/2026-10-16-layout-choice/bp_efficiency_probe.py`,
results in `bp_eff.jsonl` beside it) is the reference implementation for `slack_fraction` and `flap_expansion`; the
builder should reproduce its numbers on dolphin_0 and ant_0 before trusting the
code. These metrics are recorded only; nothing in this slice optimises them.

## 7. The VLM explanation

When §4 says `ask`, one text-only LLM call writes a short explanation (2–4
sentences) for this subject. It receives the subject, the tree's bilateral
pairs (or that there are none), both grid sizes, `gain`, and both options'
`slack_fraction` and `mean_layers`. It is told the recommendation and asked to
explain the trade-off for this subject, not to choose. It uses the run's LLM
client (the app's model pill choice; Haiku 5.5 by default). If the call fails
or no client is configured, a fixed template explanation built from the
numbers is used and the question is still asked. The explanation is saved with
the run so a reload shows the same text.

## 8. Surfaces

### 8.1 App (`app/server/pleatwright_app`, `app/web`)

Flow after "Approve" on the tree: `approve_tree` → **pack options** → either
fold directly (no question) or pause for review at the existing stage `packing`
(no new `layout` stage).

* Packing options runs in the spawned child process like the fold
  (`foldproc.py`), so Cancel still kills it.
* `awaiting_review` with `stage="packing"` carries both options (grid, gain,
  metrics), the recommendation and the explanation; both packing crease
  patterns are written as files so the viewer can show them side by side.
* The chat panel shows the question card from the 2026-10-16 mockup
  (`docs/superpowers/evidence/2026-10-16-layout-choice/layout-choice-mockup.html`): the
  question, two options (recommended first and marked "(Recommended)"), each
  with grid size and 2–3 pros and cons, and the VLM explanation. Every number
  on the card comes from packing time *(builder-check call)*: grid, gain,
  `slack_fraction`, `mean_layers`, and the base's crease count (the base already
  carries every crease; solving only assigns mountain/valley, so the base count
  stands in for the mockup's "129 vertices against 257"). Nothing is solved
  before the question is asked. Choosing an
  option starts the fold with that layout. The free-text box is not used at this
  stage.
* The viewer shows the two packing CPs side by side with their grid sizes, and
  a size comparison of the folded model from the same sheet.
* A run reloaded while waiting at the packing review shows the same card (state from the
  event log and saved files, like the mesh and tree reviews). Retry after a
  failed fold at this point returns to the card (the retry tool is still named `layout`).
* The packing stage's summary shows the chosen layout and the §6 metrics.

### 8.2 CLI (`python -m pleatwright`)

* `run`: after tree approval, if §4 says `ask`, print both grid sizes, the gain,
  the recommendation and the explanation, then prompt
  `[a] accept recommendation   [s] symmetric   [m] smaller   [q] quit`.
  Quit exits 1 like the tree review. EOF is quit.
* `fold TREE --out DIR [--layout auto|symmetric|smaller]`: default `auto`
  (§4, never asks, no LLM call). The chosen layout and reason are printed with
  the existing JSON record.
* `pipeline.main` (the batch runner) takes the same `--layout` flag.

## 9. Acceptance

1. `fold` (auto) over all 51 artifact trees completes; every tree folds.
2. The trees whose `gain ≥ 1.10` switch to the smaller grid; all other trees'
   four output files are byte-identical to today's (the 2026-10-10 byte-identity
   gate method).
3. Every switched tree is globally `CERTIFIED`, or `OVERSIZE+LOCAL_SAT` only if
   its symmetric layout already was, with all solving and shaping vertices
   flat-foldable (the probe already shows this for the 16 trees; §1).
4. No tree's packing takes more than about 165 s longer than today (scorpion,
   spider and starfish included), and two `fold` runs give identical layouts.
5. App: a dolphin_0-like run stops at the layout card; choosing either option
   finishes the fold at that grid; reload at the card shows the same card.
   A bird_1-like run (gain 1.05) never shows the card.
6. CLI `run` with scripted input `a` / `s` / `m` / `q` behaves as §8.2.
7. Tests use only the 51 artifact trees (owner rule). Never tardigrade / water
   bear.

## 10. Left to the builder

* How the work budget is threaded through `pack.py` / `nest.py`, and its
  calibrated value (§5.2).
* How `pack_options` persists the two layouts (§5.1).
* The exact prose of the template explanation, the card's pros/cons wording,
  and the VLM prompt.
* Event and file names for the layout review (stage id `packing`), following the mesh-review spec's
  conventions (`docs/superpowers/specs/2026-10-11-mesh-review-design.md`).

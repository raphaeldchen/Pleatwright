# Handoff: P3, and where the LLM-guided extraction design actually stands

**2026-09-04. Closes P3. The answer to "are we done?" is NO, and the remaining
work is not what the spec thought.**

## 1. Every unit now has a verdict

| unit | verdict | shipped? |
|---|---|---|
| M1 reachability | MET | — |
| M2 wide window | two arms, real subjects unmeasured | — |
| M3 orientations | DO NOT SHIP, retained on reachability | wiring kept |
| **U1** orientations channel | shipped | ✅ |
| **U2** `anatomy_spec` | shipped | ✅ **but UNWIRED** |
| **U3** `frame_concept` | **measured, DO NOT SHIP** | never built |
| **U4** `search_extraction` | shipped | ✅ **but UNWIRED** |
| **U5** `propose_tree` | **justification REFUTED** — Class 3 is empty | never built |
| **U5′** shape not count | **measured, DO NOT SHIP** | built, not wired |
| U6 `seed_placement` | DO NOT SHIP, retained | wiring kept |
| **U7** `critique` | **structurally impossible as specified** | never built |
| **§15** Integration | **NOT DONE** | — |

**The measurement programme is complete. The integration was never started.**

## 2. ⛔ The unfinished work, verified not asserted

`server.py` contains **zero** references to `anatomy_spec`, `WIDE_VOXEL_GRID`,
`wide_grid_budget`, `spec_distance`, `reference_provenance`, `pair_producers`
or `propose_pairs`. Each appears exactly once in `mesh_to_tree.py` — at its own
definition.

> **P2's components are defined, tested, mutation-verified and called by
> nothing.** That was deliberate: §16 assigns Integration to P3, and the
> project owner confirmed the unwired ship before P2 executed. But P3 was then
> rescoped away from §15, so nobody picked it up.

This is the single largest open item in the design, and it is not a research
question — it is plumbing whose blast radius has never been costed.

⚠ And §15's own acceptance gate is **provably vacuous**: a committed test shows
the five-fixture scorecard cannot observe the seam §15 would wire. Anyone doing
this work needs a new gate first.

## 3. U5′ — the last unit measured, and the most instructive

**Verdict: DO NOT SHIP.** K=5 consensus, aggregation fixed in code and
mutation-verified before the run:

| subject | want | A | C (null) | B (K=5) | vs A |
|---|---|---|---|---|---|
| lizard | 2 | 1 | 0 | **0** | worse |
| bird | 2 | 1 | 0 | **2** | better |
| spider | 4 | 3 | 2 | 3 | tie |
| horse | 2 | **0** | 1 | **2** | better |
| octopus | 4 | 2 | 0 | **0** | worse |

**★ The finding is not that the model is wrong.** The empty results are `[]`
and not `None`: five draws all expressed opinions and **no single pair appeared
in three of them.** The model does not disagree with the extractor — it
disagrees with **itself**.

**Three runs gave net +1, +2 and 0.** Only the third used an instrument
variance could not fool. N=1's `+2` was a coin landing well.

`G4_NET_MIN` stayed at **3** throughout. Having seen +2, lowering it to 2 would
have been the exact failure the bar exists to prevent; it is pinned by test.

**Two things survive the verdict:**
* **The horse.** The shipped extractor declares **zero** pairs in a quadruped;
  the model finds both, stably enough to clear a majority of five. A real,
  reproducible win where arm A is weakest.
* **Arm C**, twelve lines and no calls, which is why we know the model's wins
  are not mechanical — it reaches the right count on none of the five.

## 4. Four claims this wave refuted, all in the spec's own text

Each was a correct number measured under conditions that had since moved.

1. **Class 3 — "the lizard's six flaps are provably absent from all 64 mesh
   cells."** False. `IDE_FREEZE_PRUNE_CUTOFF` serves them at fidelity 1.0 with
   correct anatomical labels and no LLM. The fixture was generated before 25
   commits and a generator swap. **Its guard was tautological** — the test read
   the same frozen fixture the claim came from, so it could never fail.
2. **Class 1 — "we have never looked there"** (bird). Also false; its target is
   reachable inside the shipped grid.
3. **U3's framing lever** — "the highest-value measured lever in the whole
   design", on a lizard 1→5 that was an artifact of a superseded default. Live,
   the lizard reads 6→6.
4. **U7's veto is impossible at the ordering §14 cites to prove it safe** —
   `server.py:4153` completes the search, the judge runs at `:4165`. And
   `_FORBIDDEN_KEYS` is bypassable: `'veto'` refused, `'blocking'` passes.

Plus four citation defects (§14's COrigami row is the weaker judge; §12's
T=1/N=4 is a category transfer from an evaluator ablation; COrigami's schema
has no pairs field; `tree_contract` is not a hard gate).

## 5. What a successor should do, in order

1. **§15 Integration**, with a gate that can see the seam. U2 and U4 are built
   and idle; that is the only place shipped code is waiting on work rather than
   on evidence.
2. **Nothing on U5, U5′, U3 or U7** without new evidence. All four are measured
   negatives, not backlog.
3. If U5′ is revisited, the lead is **output stability, not prompt quality** —
   constrain the model so it cannot propose a different partition each draw.
   "Try a better prompt" is contradicted by the K=5 data.

## 6. Methodological findings

1. **A measurement is only valid for the configuration it ran under.** Four
   stale claims this wave, three in the spec and one of mine — step zero ran on
   a branch predating the freeze default and reported the pre-flip world as
   "the current default". Record the flag state, the commit and the generator
   beside every number.
2. **A test that reads the artifact its claim came from cannot fail.** Class
   3's guard was the claim restated.
3. **A broad `except` turns "this code is broken" into "the model had nothing
   to say."** A missing `import json` inside one produced ten failures that all
   looked like reply-parsing problems.
4. **Distinguish "no opinion" from "no result".** `None` vs `[]` caught a token
   cap truncating the model *and* separated "declined" from "answered five
   times, never twice the same". Collapsing them to `0` would have produced a
   confident wrong negative, then a confident wrong positive.
5. **Score the change on something other than the search's own ranking key.**
   Holding the winning cell fixed inverted the freeze's apparent benefit
   entirely — 4 vs 16.
6. **A null arm is the cheapest thing in any producer comparison.** Arm C cost
   nothing and is why U5′'s two wins are attributable at all.

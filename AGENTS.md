# Agent Instructions

Project architecture, stages and owner rules live in [`CLAUDE.md`](CLAUDE.md).

## Required: research prior art before developing plans

Before writing any plan (new feature, subsystem, algorithm, rescue/repair
strategy), you MUST research existing and adjacent work first — academic
literature, open-source tools, and analogous systems in neighboring domains
(computational origami, fabrication pipelines, text-to-CAD/EDA agent loops).
Take every opportunity to draw from existing work instead of inventing from
scratch.

Concretely, a plan is not complete unless it:

1. States what prior art was surveyed (with sources).
2. Lists what was **adapted** — mapped to the specific module it lands in.
3. Lists what was **consciously rejected**, with the reason (a verified
   "nothing exists in this sub-area" is a valid and valuable finding).

Model example: `docs/superpowers/plans/2026-07-25-perfect-base-slices.md`
(see its "Prior-art adaptations" table). Rationale: this project's own
vendored TreeMaker source turned out to already contain the author's fixes
for failures we had been attacking with home-grown heuristics, and adjacent
agent-loop domains had published measured answers (error→recipe tables,
breadth-vs-depth repair budgets) to questions we were about to re-derive
blind. Search first; build second.

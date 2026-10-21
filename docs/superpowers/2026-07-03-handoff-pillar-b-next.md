# Handoff: Pillar B next sequence — fast-follow → folded-state-first → B5

**Date:** 2026-07-03. Written at the end of the session that shipped PRs #22–#24.
**For:** the next working session. Read this plus the memory index; everything
else is discoverable from the repo.

---

## 1. Where the project stands (all merged to main, tip d9a543f)

Pillar B ("honest shaping" — pose a compiled origami base in 3D with real
creases, never faked geometry) is complete through its feedback loop:

| PR | What |
|---|---|
| #19 | Model tab: folded base rendered as thick lit paper (r3f scene we own). |
| #20 | Tracer: `shaping.reverse_fold` as a pure FOLD transform at the display boundary; browser p90 strain oracle (converge-or-reject, p90 < 0.15). |
| #21 | `apply_shaping_ops` MCP tool: agent poses by node_id/fraction/theta; ops ride the wrapper (`ide_shape_ops`), display replays them; HITL prompt. |
| #22 | Minors: `ops is None` three-state fix; wrapper carries `paper: [w,h]`. |
| #23 | Primitives: `outside` reverse (sense=-1) + `crimp` (atomic tool composition → two op strings). ⚠️ crimp θ=90 silently mis-targets — guarded. |
| #24 | **Oracle loop closed**: fold frames carry `id`/`shaped`/`strain_max`; browser sends `oracle_verdict` ws frames; server injects `[STRAIN ORACLE]` user-role messages and runs ONE capped autonomous retry turn on shaped-fold rejects; UI auto-switches to the Model tab for shaped folds. |

Suites at head: backend `287 passed / 3 skipped` (~10 min, real spawn
compiles), web pytest `40`, frontend vitest `55` + clean `tsc` build.

Key files: `mcp_harness/shaping.py` (pure geometry), `mcp_harness/server.py`
(`apply_shaping_ops`), `mcp_harness/agent_loop.py` (SYSTEM_PROMPT SHAPING
section, pin-tested), `web/server.py` (ws bridge, verdict branch, retry
budget), `web/fold.py` (wrapper extraction), `web/frontend/src/extraction.ts`
(capture + oracle), `CADViewer.tsx`, `App.tsx`, `chat.ts`.

Specs/plans live in `docs/superpowers/specs|plans/` (read
`2026-07-01-shaping-tracer-b1-b3-b4-design.md` first for the geometry model,
then the B2/primitives/oracle-loop specs). SDD ledger:
`.superpowers/sdd/progress.md`. Roadmap source:
`docs/superpowers/specs/2026-06-30-finished-model-view-research.md` (Pillar B
table defines B1–B5).

## 2. The agreed sequence

### Step 1 — Fast-follow: fold-id captured at start() (small PR, ~2 files)

Deferred finding from PR #24's final review (design already decided there):
`App.tsx`'s `sendVerdict` reads `state.fold?.id` at VERDICT time, so under
overlapping folds a stale capture's verdict can be tagged with the newest
fold's id — which the server's stale-id guard then wrongly ACCEPTS. Fix:

- `extraction.ts`: `start(fold, maxStrain?, foldId?)` records the id per run;
  `OracleVerdict` gains `foldId?: number`; every terminal `onVerdict` carries
  the run's own id.
- `CADViewer.tsx`: pass `fold.id` into `start()`.
- `App.tsx`: `sendVerdict` uses `v.foldId` (skip send when undefined) instead
  of reading ambient state.
- Tests: extend the existing `onVerdict` vitest block (id carried on pass and
  reject; verdict for run A after `start(B)` — the existing stale-window tests
  show the pattern); web pytest unchanged (server already validates fold_id).

Small enough that brainstorming should be minutes, not a design cycle — the
final-review triage in the ledger IS the approved design.

### Step 2 — Folded-state-first generalization (the big one, MULTIPLE cycles)

Phase 2 of the tracer spec (§7 of the B2/primitives specs, "the hard part" of
B3 in the roadmap): today's primitives are tip-local because we operate on the
FLAT crease pattern and only flap tips are geometrically unambiguous there.
Folding at arbitrary depth (mid-flap through many layers, squash/sink) needs a
Python model of the FOLDED state: where every face sits after folding, and in
what layer order.

Do NOT plan this as one cycle. Brainstorm the decomposition first. A suggested
tracer-style slicing (validate/adjust in brainstorming):

1. **Flat-fold engine tracer**: compute folded 2D positions of every face of a
   compiled base (reflection composition along the face adjacency tree —
   Lang's standard construction). Oracle: folded positions of flap tips match
   what the simulator converges to (capture comparison), or at minimum
   symmetry/involution invariants. Pure Python, `mcp_harness/`, no UI.
2. **Layer ordering**: a consistent stacking order for overlapping faces
   (Justin's non-crossing conditions / Tachi's bipartite constraints — this is
   the genuinely hard research-grade part; consider accepting partial orders
   or simulator-assisted disambiguation the way A-3 used the sim to overrule
   Oriedita).
3. **One at-depth op**: reverse fold THROUGH layers at a point that is not a
   tip, expressed — critically — still as flat-CP creases + fold angles (the
   display/provenance contract is unchanged: ops at the display boundary,
   raw fold untouched, sim solves the target angles).
4. **Squash/sink primitive** on top (this is what unlocks the roadmap's
   remaining vocabulary).

Also useful: the engine doubles as a FAST headless pose evaluator (seconds,
no browser) — which Step 3 needs.

### Step 3 — B5: target-mesh-guided shaping (after Step 2)

Roadmap definition: use the reference mesh (existing text→3D pipeline) as the
goal silhouette; search shaping parameters so the posed base matches.
Deliberately last because (a) its value scales with the op vocabulary Step 2
provides, and (b) a parameter search needs the headless evaluator from Step 2
— the only current honest evaluator is the browser capture at 30–90s per
candidate, visible-tab-only. Objective function (silhouette IoU vs joint
angles) is an open question — brainstorm fresh.

## 3. Operational gotchas (will bite if forgotten)

- **Groq**: `LLM_PROVIDER=groq LLM_MODEL=meta-llama/llama-4-scout-17b-16e-instruct`
  (llama-3.3-70b exceeds the 12k TPM cap on request 1). Anthropic key is out
  of credits. Expect sporadic `tool_use_failed` 400s mid-turn; scout also has
  a documented adherence gap (skips propose-first on imperative commands;
  explained instead of re-calling in its free oracle-retry turn) — judge live
  demos on the mechanical pipe, pin contracts in prompt tests.
- **Test commands**: backend `cd mcp_harness && .venv/bin/python -m pytest tests -q`
  (10 min); web `mcp_harness/.venv/bin/python -m pytest web/tests -q` (repo
  root); frontend `cd web/frontend && npm test && npm run build` (the build IS
  the type gate for .tsx). The served UI is `web/frontend/dist` — rebuild
  before live demos.
- **Sim visibility**: the vendored simulator's GPU solver does NOT run while
  its iframe is offscreen — anything needing a fold must be visible (this is
  why shaped folds auto-switch to the Model tab).
- **Stacked PRs**: GitHub only auto-retargets when the base branch is deleted.
  PR #23's squash silently landed on its undeleted base branch instead of
  main. After ANY merge, verify main's actual tip, not just `mergedAt`.
- **Demo knobs**: `IDE_STRAIN_MAX` (default 0.15) forces oracle rejects;
  `IDE_ORACLE_RETRIES` (default 1) caps autonomous retries.
- **Provenance contract** (never break): the fold frame's `json` is the raw
  linted artifact; squaring/shaping happen only on `display_json`; ops never
  enter the FOLD dict; the AI never edits coordinates.
- Sporadic unrelated flake seen once: Oriedita lint `Index 64 out of bounds`
  on a perturbed compile — retry the compile, not a code bug on any current
  path.

## 4. Process used (works well, recommend continuing)

superpowers brainstorming → spec (committed) → writing-plans (complete code in
tasks, probe engine behavior BEFORE pinning test params) → subagent-driven
development (haiku for transcription tasks, sonnet for integration, sonnet
reviewers, opus final whole-branch review) → finishing-a-development-branch
(user picks "Push and create a PR", user merges). Ledger every task in
`.superpowers/sdd/progress.md` — it is the recovery map after compaction.

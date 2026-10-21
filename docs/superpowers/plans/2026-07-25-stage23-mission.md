# Mission: Stage 2 completion — M/V repair solver, arrangement-aware audit, gate retrain, live oracle smoke

ultracode

Charter: finish roadmap §Stage 2 (`docs/superpowers/2026-07-18-cp-root-cause-and-specificity-roadmap.md`)
— roadmap items 2.3 (M/V repair solver) and 2.4 (gate retrain), plus the two
loose ends the Stage-2 handoff names (`docs/superpowers/2026-07-24-stage2-lint-split-handoff.md`):
cp_audit's missing arrangement check and the unproven live [CP AUDIT] loop.
Base: main at 9f7432a (PR #49 merged; main also carries PR #48's rigid phase 4,
untouched by this mission). Work in a fresh worktree branched from main.

EXECUTION ORDER IS LOAD-BEARING: D → B → A → C. D (live smoke) MUST run before
A (solver) lands, because a working solver may clean the dog's served base and
remove the exact cp-audit marker D needs as its trigger. B (arrangement-aware
audit) lands before A so the solver certifies against the true cleanliness
definition, not the necessary-conditions-only one.

## Phase 0 — bootstrap + fresh baseline (do first, cheap)

- Fresh worktree from main. `make build` IN-PLACE (a borrowed
  headless_treemaker.so from another checkout inflates baseline failures 27 vs
  ~3 — memory: worktree-borrowed-so-inflates-failures). build_linter.sh
  downloads oriedita-1.1.3.jar if missing (needs network once).
- The venv: Makefile assumes mcp_harness/.venv exists (PYTHON ?=
  .venv/bin/python, no creation target). Copy the main checkout's venv — but
  the copied .venv/bin/* entry-script shebangs point at the MAIN checkout's
  venv; always invoke `.venv/bin/python -m pytest`, never `.venv/bin/pytest`.
- Copy `mcp_harness/generated_meshes/` from the main checkout — the dog mesh
  (36f4aec6… = sha256("hf:a dog"), 874,640 bytes) is git-ignored and exists
  ONLY on this machine. Losing it loses the Stage-2 test subject.
- Run `make test` once for a FRESH baseline count: the recorded 1427-passed
  number predates PR #48's ~5 new test files; post-merge main's absolute count
  has never been measured. Expect the 3 pre-existing rigid hash failures
  (test_rigid_compiler / test_rigid_miura_compiler /
  test_rigid_phase3_oracle_fixture — env float-repr drift, proven at 78b2be0;
  NOT yours, do not chase). CI is expected back ~end of July; if the repo has
  a green CI run by session time, CI is the gate again — otherwise local
  `make test` remains the gate.
- Regenerate the solver's target: `cd mcp_harness && PYTHONPATH=.:tests
  .venv/bin/python probe_stage2_audit.py` (defaults: dog cache glb, voxel 64,
  prune 0.6) with CLEAN env — a stale IDE_LADDER_AUDIT/IDE_LADDER_EXTRA_TRIES
  silently changes which base is served. Confirm the served pack still reads
  maekawa=5, tries=11, packs_seen=3 after the fresh .so build. Then COMMIT it
  as a new golden (e.g. tests/goldens/hf-dog-ladder-best.fold) with a
  provenance docstring — the 5-defect base is currently NOT in git anywhere;
  the committed hf-dog-nudged.fold is the OLD 7-defect pre-2.2 fold, frozen as
  the classifier benchmark, and its pinned defect set {3,4,5,9,26,31,35} does
  NOT transfer (vertex numbering is per-fold). Also consider committing the
  dog mesh.glb itself as a test fixture (~875 KB) to end the single-machine
  risk — ask the user before adding a binary to git.

## D — live smoke of the [CP AUDIT] repair loop (run FIRST)

The 2.2 bridge is fully stub-tested (web/tests/test_server_cp_oracle.py); the
ONLY untested layer is the live LLM's behavior on a real [CP AUDIT] message.

PROVIDER CHANGED 2026-07-25 — Groq is dead for this agent, permanently, not
by misconfiguration. Groq retired meta-llama/llama-4-scout-17b-16e-instruct
(404 model_not_found); it had been the only free-tier model whose window fit
this agent. Measured that day from the live rate-limit headers, every model
the key can still reach caps BELOW the agent's ~17k-token first request:
llama-3.3-70b 12k TPM (and it fumbled a tool call in the probe), gpt-oss-120b
/ gpt-oss-20b / qwen3.6-27b 8k, llama-3.1-8b-instant 6k, compound-mini no
tool calling at all. A single request exceeds the whole per-minute budget, so
the 413 backoff in llm_client can never rescue it — do not re-attempt Groq or
re-set the scout literal that still appears in older handoffs. The request is
that large structurally: SYSTEM_PROMPT alone is ~22.4k chars (~5.6k tokens)
and the ~14 MCP tool schemas make up most of the rest.

- Env (the main checkout's .env is ALREADY set this way as of 2026-07-25 —
  verify, don't re-derive): LLM_PROVIDER=claude, LLM_MODEL=claude-sonnet-5,
  ANTHROPIC_API_KEY (funded ~$16 as of 2026-07-25 — if the smoke 401s, that
  is credits, not config), MESH_PROVIDER=hf, IDE_CP_REPAIR_RETRIES=1.
  Verified live: tool calling survives the OpenAI-compatible shim at
  https://api.anthropic.com/v1/ through the project's own llm_client (proper
  tool_calls finish reason on sonnet-5, haiku-4-5, sonnet-4-6). NOTE the
  preset default in llm_client.PROVIDERS is the older claude-sonnet-4-6 — set
  LLM_MODEL explicitly rather than relying on it.
- COST DISCIPLINE (~$16 budget, no prompt caching through this shim): each
  model step sends ~17k input tokens and MAX_AGENT_STEPS=12 allows a heavy
  turn to run a few hundred thousand input tokens. Run plumbing/driver
  iterations on claude-haiku-4-5-20251001 and switch to claude-sonnet-5 only
  for the runs whose RESULT is the contract-compliance verdict — the whole
  point of D is instruction-following, so the verdict run must use the strong
  model. Report tokens/cost actually spent in the handoff.
- The worktree has NO .env and env_config resolves .env relative to its own
  checkout, so a run launched from a worktree silently loses every key: run
  from the main checkout or export explicitly. Shell exports beat .env
  (override=False) — check `env | grep LLM_` before blaming config.
- ALL env must be set before uvicorn starts: web/server.py builds the LLM
  client at import time and agent_loop snapshots the MCP child env at import.
- Launch: `mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8000`
  from repo root; /ws/chat works headless (no frontend build needed).
- Driver: a scripted raw-websocket client written to a REAL file (stdin-piped
  python cannot parent the spawn workers), replaying the frame discipline of
  web/tests/test_server_cp_oracle.py's _drain_turn. Handle the error-frame
  case: an errored turn sends NO turn_end, does not spend the repair budget,
  and defers the firing to the next healthy user turn — the driver must
  re-prompt, and must not count the deferred firing as a second injection.
- Subject: the prompt must reach mesh_acquire as EXACTLY "a dog" for the cache
  hit (any paraphrase goes to the live HF Space = nondeterministic mesh), and
  must NOT invite shaping/posing (a shaped fold suppresses the CP oracle by
  design). Fallback if the natural path fails: reference_tree_from_query uses
  AUTO constants (may differ from the proven v64/p0.6 tree) — run a 5-minute
  offline probe of that path first; if it serves clean, paste the precomputed
  v64/p0.6 tree_nodes+symmetric_pairs into the chat prompt instead.
- Wire success criteria (all observable as frames): (1) fold frame whose
  json.frame_title contains "[ide: cp-audit:"; (2) after turn_end, an
  assistant frame starting "[CP AUDIT] " containing "Repair now"; (3) ONE
  autonomous repair turn whose draft_and_compile_full_base args CHANGED at
  least one edge length (an identical-tree recompile is the deterministic
  no-op the prompt forbids) followed by validate_flat_foldability and a second
  turn_end; (4) a later foldless prompt fires INFORM-ONLY, never a second
  repair turn; (5) final assistant text reports repaired-or-still-violating
  honestly ("still violating, served the better base" is an acceptable honest
  outcome — the dog's defects may be robust to few-percent length changes).
- KNOWN LIMIT to report correctly: the ONE-recompile cap is PROMPT-enforced
  only (no code-level compile counter exists; code caps only autonomous
  TURNS). A compliant-bridge-but-2-recompiles run is an LLM-compliance
  finding, not a bridge bug — do NOT "fix" it by adding a code cap mid-smoke.
- Evidence to keep: full frame transcript + the served fold JSON + the capture
  rows the smoke itself appends (serve defaults IDE_CAPTURE_PATH to
  mcp_harness/feasibility/captured.jsonl — expected side effect; C's dedup
  must tolerate this pollution).

## B — fold the arrangement check into cp_audit (before A)

cp_audit.AuditReport.clean is necessary-conditions-only (closure + Maekawa
parity + Kawasaki residual); the big-little-big M/V-ARRANGEMENT oracle exists
only in lint_verdict._mv_arrangement_ok (greedy crimp reduction; stuck ⇒ NOT
ok — the conservative tie rule is the pinned false-FAILED-only fail direction,
never relax it). The ladder can therefore serve a BLB-broken pack as "clean"
today.

- The port is not copy-paste: cp_audit builds incidence-ordered rays and never
  retains angle-sorted (sector, assignment) rings — add the sort-and-pair step
  lint_verdict does. Extract the shared oracle to ONE home (cp_audit owns it,
  lint_verdict imports) rather than duplicating.
- CHURN PROBE BEFORE LANDING (the review flagged this): arrangement-aware
  clean changes ladder pack SELECTION (_audit_score / first-clean-wins), not
  just reporting. On the three cached HF trees (dog 36f4aec6, deer 62501429,
  crane ca8680d8), measure whether the served rung changes. Expected blast
  radius is FOUR pin files: test_ladder_audit.py:341-345 (EXACT dict equality
  on perturb['audit'] — any new key breaks it), test_ladder_audit annotation
  substrings, web/tests/test_server_cp_oracle.py marker source-text pins,
  test_cp_audit + CLI exit codes (arrangement-only-defective folds flip exit
  0→1). Budget deliberate test updates + a bless dry-run; any FAIL-LINT
  baseline flip is a deliberate re-bless committed separately (bless.py
  policy).
- Re-verify after landing: test_lint_classification's pin that lint's [real]
  set == cp_audit's independent set on the 7-defect golden must still hold
  (the golden has no arrangement-only defects, so it should — verify, don't
  assume). Capture's perturb['audit'] gains arrangement counts only with the
  matching test updates and a note in the handoff (2.4 consumes this schema).

## A — roadmap 2.3: the coupled M/V repair solver (the centerpiece)

Problem, per the live evidence: the dog's residual 5 interior Maekawa defects
are |M−V| ∈ {0,4}. One flip moves a vertex's M−V by exactly ±2, so each is
one flip from parity IN ISOLATION — but each crease couples two endpoint
vertices, and single flips are live-proven insufficient. The solver reassigns
JOINTLY.

Hard constraints (all pinned in code/tests — violating any is a regression):
- NEVER repair attempt-0 packs: "a dirty exact tree surfaces HITL through the
  classified lint verdict, never a server-side retry" (server.py policy
  comment; test_ladder_audit byte-pins out == DIRTY_FOLD). Sanctioned
  insertion points are ONLY the ladder's best-dirty branch after
  _search_first_clean exhaustion, or a separate explicitly-invoked tool.
- Closure and Kawasaki are M/V-BLIND (flat_fold reflects M and V identically;
  Kawasaki sees only ray angles) — they can NEVER score a reassignment.
  Candidate scoring = Maekawa parity + arrangement (_mv_arrangement_ok) +
  layer_order forced-relation propagation (necessary, not sufficient — no
  branching, free pairs remain) as pure-Python filters; the Oriedita JVM lint
  is the FINAL oracle only (subprocess, 90s cap — keep it out of any inner
  loop; probe_reassign.py is the prior art: brute-force 2^k with
  oracle-in-the-loop, exponential, spawn-context).
- Route repairs from LOCAL RE-AUDIT facts (DETAIL violations[].local.mv_delta
  parity + arrangement), NEVER from Oriedita rule labels or the mv_fixable
  flag — rule labels are proven liars; MV_FIXABLE_RULES={"MAEKAWA"} is a
  counting/rendering convention, not solver routing.
- Odd |M−V| (1/3) is NEVER relabel-fixable — the solver must refuse those
  honestly (geometry defects), and Kawasaki/boundary defects are out of its
  jurisdiction by construction.
- Solve on the RAW `json` frame only (display_json is squared = no consistent
  flat state); raw compiled folds have NO edges_foldAngle (nothing to sync on
  the raw frame); vertex indices are per-fold and do not survive recompiles.
- Deadline/process discipline if solver runs in the ladder worker: spawn-safe,
  pure-Python in-child (no MCP, no capture in-child), respect the checkpoint
  protocol landed in the review hardening.

Design decisions the session MUST settle BEFORE implementation (judge-panel
material — these were identified as unowned by any code or doc):
1. ACCEPTANCE BAR: what counts as "repaired"? Recommended: cp_audit interior
   defect count strictly reduced AND arrangement-aware clean not worsened AND
   closure unchanged (flips can't move closure — verify as tripwire), with the
   JVM classified verdict improving (real count down; [BENIGN]/Pass = full
   win). Partial reduction = partial win, honestly annotated. Dog 5→0 is the
   target; a bounded honest negative WITH search-space trace is an acceptable
   outcome (mirrors the crane precedent).
2. MARKER LIFECYCLE: a solver-repaired fold must NOT keep the stale cp-audit
   marker (web keys the repair oracle on marker presence — a repaired-but-
   marked fold re-triggers [CP AUDIT]; a silently-stripped marker hides the
   repair). Recommended: rewrite to a distinct repaired-provenance note the
   web bridge does NOT key on, and extend web/fold extraction knowingly. The
   marker literal is source-text cross-pinned in web/tests — plan the pin
   updates.
3. PLACEMENT: in-ladder (repair the best-dirty pack before serving) vs a
   separate MCP tool (agent-invoked on [CP AUDIT]/[real] evidence) vs both.
   Latency, the zero-churn unauditable rule, and D's contract (the shipped
   [CP AUDIT] message commands a tree-LENGTH micro-adjust — an M/V solver is
   a DIFFERENT lever; decide replace/precede/complement and update the
   message + prompt pins together).
4. SYMMETRY: must a repaired assignment preserve bilateral symmetry on
   symmetric_pairs trees (the dog is symmetric; an asymmetric label pattern
   on a symmetric base is geometrically legal but aesthetically wrong)?
   Recommended: prefer symmetric solutions, accept asymmetric with annotation.
5. CAPTURE SEMANTICS: if the solver repairs in-ladder, capture must record the
   PRE-repair audit (preserves 2.4 label continuity = "what did the raw
   compile do") plus explicit repair-outcome keys — never silently overwrite
   the audit dict the 2.4 labeler reads. Schema change ⇒ test_ladder_audit
   exact-dict pins churn deliberately.
Also scope: measure the search-space size FIRST (per-defect incident crease
count k, defect adjacency/coupling on the regenerated 5-defect dog) — if the
coupled neighborhood is ≤ ~2^12, exact enumeration with pure-Python filters +
one final JVM confirm beats anything clever. Build the clever thing only if
enumeration provably can't work. A small Java spike against the jar's
FoldedFigure.folding_estimated (layer-level global validation) is OPTIONAL,
time-boxed, and only if the pure-Python certification proves insufficient —
Oriedita as wired is check-only; the CLAUDE.md claim that it "deduces M/V" is
fiction relative to this pipeline.

Acceptance for A: the dog's served base measurably improves (defect count
strictly down, verified by cp_audit AND the classified JVM verdict on the
served fold) OR a bounded honest negative with the enumerated/searched space
recorded in the handoff. Byte-"Pass", FAIL-LINT baselines, and the frozen
7-defect classifier golden all unchanged (bless dry-run empty unless B's
deliberate re-bless already moved them — keep those commits separate).

## C — roadmap 2.4: merge-with-id + retrain (LAST; conditional)

- FIRST probe the actual data: captured.jsonl lives in the MAIN checkout (this
  worktree has none) — row count, schema-era mix (legacy vs audit-bearing vs
  audit-free rows; the 'audit' key is OMITTED when unauditable, never null),
  plus D's smoke pollution. If volume is thin, the honest outcome is: land the
  merge machinery + report, and defer the actual retrain — say so rather than
  training on noise. A synthetic ladder-outcome corpus pass (mesh_like family
  precedent, PR #9) is the documented alternative; scope it only if time
  allows.
- The merge script must: assign integer ids continuing above the corpus max
  (corpus_wide.jsonl holds ids 0–2599; existing_ids() KeyErrors on ANY id-less
  row and build_corpus calls it unconditionally — one bad row bricks resume);
  dedup by canonical nodes+pairs JSON (compiles are deterministic ⇒ repeated
  serves are duplicates; keep first-by-ts); PRESERVE perturb_pack None vs
  False (None = attempt-0 packed, False = ladder exhausted — coercion corrupts
  exactly the 2.4 label); treat failure_mode as attempt-0-only semantics (the
  "needs nudge" truth lives in perturb_pack/perturb); STRIP the 'gate' field
  (it encodes the OLD model's verdict — leakage risk); keep extra keys
  otherwise (corpus key-set pin is a superset check).
- Merge TARGET decision (settle early): committed corpus_wide.jsonl (puts
  served user trees in git history; test_gate_mesh_region retrains from that
  exact path and its fish/insect fixtures sit at p_pack ≈ 0.17, JUST above the
  block threshold — the designed help/hurt tripwire; measure fixture margins
  on the merged corpus BEFORE committing, and never delete the pin to make a
  retrain pass) vs a new gitignored merged file (requires plumbing the corpus
  path through train_model --corpus, ensure_gate_trained, mesh_to_tree
  _default_gate, and test_gate_mesh_region CORPUS). Recommended: new file +
  plumbing — keeps user trees out of git and the synthetic corpus pristine.
- Retrain mechanics: every loader early-returns when gate.joblib exists AND
  server/capture cache the Gate in process globals — a retrain takes effect
  only by explicit train_model.fit / deleting the artifact AND restarting
  long-lived processes. Decide where the retrained gate LIVES (gate.joblib is
  never committed; train-on-demand reproduces only from the committed corpus)
  — this is structural, surface it in the handoff.
- Label design decision: "packs exactly" = attempt0_pack; "needs nudge" =
  perturb_pack True; decide where perturb_pack False and unsampled None rows
  go (three-class vs drop) — judge-panel material, small.
- Acceptance: merge script + tests (id continuity, None/False preservation,
  dedup, gate-strip, mixed-era tolerance); eval evidence (test_gate_mesh_region
  margins + benchmark_templates before/after) for whatever retrain ships, or
  the explicit deferral report.

## Out of scope (fence hard)

Stage 0.5 (default pose — gated on platform chips h-f1/h-f2 + B4), Stage 2.5
(mobility composer), Stage 3 (semantic ops / target-guided search), the .so
optimizer convergence knobs (roadmap's "heavier unexplored lever" — the
crane's honest negative stays parked), squared-display flat-foldability,
gate.joblib CI/CD, the 3 rigid-origami hash failures, and CLAUDE.md §4's
fictional tool names (note the drift in the handoff; a one-line doc fix is
allowed, a rewrite is not).

## Standing operational constraints

Compile probes = real script files with `if __name__ == "__main__":` guards
(heredocs break spawn and masquerade as engine crashes). Seeds are CODE
CONSTANTS (SKELETOR_SEED, _PERTURB_SEED) — exporting them does nothing. Lint
only RAW `json` frames, never display_json. /tmp is wiped between sessions —
artifacts go to the session scratchpad or committed goldens. The verdict
grammar has FIVE mirrored pin sites (lint_verdict renderer, SYSTEM_PROMPT,
test_lint_classification, test_agent_reference_prompt, web _MIXED_VERDICT
fixture) — grammar edits move all five together. SYSTEM_PROMPT negative pins:
"ide_perturbation", "may be repairable by flipping", "ZERO M/V-fixable" must
stay ABSENT. web/server fabricates "[ide: cp-audit: (note lost)]" when the
stored note is missing — greps must not count it as a served marker.

## Finish with

Roadmap §Stage 2 status updated (2.3/2.4 lines), a dated handoff in
docs/superpowers/, memory updated, and a PR to main (do not merge it
yourself). Deliberate re-blesses (from B) committed separately from feature
work. If CI is back, include the CI run link; otherwise record the fresh
local gate numbers against the Phase-0 baseline.

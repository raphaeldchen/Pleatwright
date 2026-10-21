# Task D — live [CP AUDIT] repair-loop smoke (2026-07-25)

Stage-2.2 wired the `[CP AUDIT]` repair oracle into `/ws/chat`. The bridge is
stub-tested by `web/tests/test_server_cp_oracle.py`; the **only** untested layer
was the live LLM's behavior on a real `[CP AUDIT]` message. This is that test.

Driver: `web/probe_cp_audit_smoke.py` (raw websocket, replays the `_drain_turn`
frame discipline of `test_server_cp_oracle.py`, including the errored-turn
no-`turn_end` deferral case).

## Runs

| Run | Model | Purpose | Frames | Injections | Repair turns | Transcript |
|---|---|---|---|---|---|---|
| haiku45 | `claude-haiku-4-5-20251001` | plumbing / driver shakeout | 27 | 2 | 1 | `haiku45-frames.jsonl` |
| sonnet5 | `claude-sonnet-5` | **compliance verdict** | 25 | 2 | 1 | `sonnet5-frames.jsonl` |

Serve: `mcp_harness/.venv/bin/python -m uvicorn web.server:app --port 8010` from
the worktree root, `LLM_MODEL` exported before start (the LLM client is built at
import time, so a model switch requires a server restart).
`IDE_CP_REPAIR_RETRIES=1` (code default). `MESH_PROVIDER=hf`.

`haiku45-summary.json` is absent: that run's driver process was killed after the
final frame but before `_finish()` wrote the summary. The frame transcript is
complete and is the evidence of record. `sonnet5-summary.json` is present.

### Subject and determinism

The prompt drives the agent to call `reference_tree_from_query` with the query
string exactly `a dog`, which cache-hits the stored HF mesh
(`36f4aec6…/mesh.glb`) rather than the live HF Space. An offline probe confirmed
the natural path's AUTO constants select **voxel_res=64 / prune_fraction=0.6** and
produce a tree byte-identical to the precomputed v64/p0.6 tree — so no
tree-pasting fallback was needed in the prompt.

Determinism held across models: both runs compiled the same tree to the same
`fold_handle: fold:0934563efeea`, and `haiku45-fold-1.json` is byte-identical to
`sonnet5-fold-1.json`. Both differ from
`mcp_harness/tests/goldens/hf-dog-ladder-best.fold` **only** by the extra
`file_description` key the golden carries; all geometry (`vertices_coords`,
`edges_vertices`, `edges_assignment`) and the `frame_title` are identical.

## The five wire criteria — verdicts against the sonnet-5 transcript

All citations are `seq` numbers in `sonnet5-frames.jsonl`.

### Post-review correction: capture-row citations (§3, §"Capture pollution")

An earlier version of this document cited capture row 8 as the original
compile. That is wrong. `mcp_harness/feasibility/captured.jsonl` timestamps
place `reference_tree_from_query` (`seq 2`/`seq 3`, `15:58:57`–`16:00:19.848`)
BEFORE the agent's own explicit `draft_and_compile_full_base` (`seq 7`,
tool_result `seq 8` at `16:00:43.347`):

| row | ts (local) | source |
|---|---|---|
| 6, 7, 8 | 10:59:30, 11:00:03, 11:00:19 | `reference_tree_from_query`'s OWN internal candidate compiles (it tries several trees before returning one) — the agent never issued these calls directly, and rows 6/7 are 10-node and 9-node candidates the agent never touched |
| **9** | **11:00:43** | **the agent's explicit compile, `seq 7`/`seq 8` in `sonnet5-frames.jsonl`** — this is the ORIGINAL compile referred to below |
| **10** | **11:01:20** | **the repair compile, `seq 15`/`seq 17`** |

Row 8 (11:00:19, the last of the three internal candidates) happens to hold
the *identical* tree to row 9 — reference_tree_from_query converged on the
same v64/p0.6 tree the agent then compiled verbatim — which is why an earlier
reading of this evidence mistook row 8 for the original compile and described
rows 8/9 as "the same tree captured twice (attempt + perturb of the original
compile)". That description of the *mechanism* was wrong: rows 8 and 9 are
TWO DISTINCT compile invocations 24 seconds apart (reference-tool internal
selection vs. the agent's explicit, separately-issued compile), not two
capture writes produced by one compile call. The diff table below (§3) is
unaffected either way, since rows 8 and 9 are byte-identical trees — the
correct citation is row 9 → row 10.

### (1) Fold frame whose `json.frame_title` contains `[ide: cp-audit:` — PASS

`seq 9` (`fold`, `shaped=false`):

```
TreeMaker crease pattern (scale=0.649835) [ide: compiled after nudging edge
lengths up to +/-10% (11 attempt(s)) ...] [ide: cp-audit: 5 interior Maekawa +
0 interior Kawasaki violation(s), closure max error 1.5e-08 remain in the best
of 3 packed nudge rung(s); real interior defects, NOT hull frontier -- served
best-effort]
```

Both the nudge marker and the cp-audit marker are present, as required.

### (2) After `turn_end`, an assistant frame starting `[CP AUDIT] ` containing "Repair now" — PASS

`seq 13` is `turn_end`; `seq 14` is an `assistant` frame beginning `[CP AUDIT] `
and closing with:

```
Repair now: micro-adjust the tree's edge LENGTHS by a few percent, biasing the
flaps nearest the listed paper-frame vertices; keep the topology and
symmetric_pairs IDENTICAL. Recompiling an identical tree is a deterministic
no-op -- change at least one length. Then recompile ONCE and re-lint; this
recompile is exempt from the 3-compile HARD LIMIT. Report
repaired-or-still-violating honestly and serve the better base.
```

The echo enumerated the 5 confirmed `[real]` vertices with per-vertex re-audit
data.

### (3) ONE autonomous repair turn, compile args CHANGED, then lint + `turn_end` — PASS

- `draft_and_compile_full_base` calls: `seq 7` (user turn) and `seq 15` (repair
  turn) — **exactly one** compile after the repair echo at `seq 14`.
- `validate_flat_foldability` at `seq 18`, then `turn_end` at `seq 21`.

**Args changed.** The `args_preview` field is truncated at ~100 chars and node 1
happens to be unchanged, so the previews look identical; the authoritative diff
comes from the capture rows the smoke itself appended
(`mcp_harness/feasibility/captured.jsonl`, **row 9** = original compile, row 10 =
repair compile — see the row-citation correction above):

| node | parent | original | repair | |
|---|---|---|---|---|
| 0 | — | 0 | 0 | same |
| 1 | 0 | 0.337572 | 0.337572 | same |
| 2 | 0 | 0.4 | 0.385 | **CHANGED** |
| 3 | 0 | 0.342712 | 0.342712 | same |
| 4 | 0 | 0.381814 | 0.365 | **CHANGED** |
| 5 | 2 | 0.296637 | 0.285 | **CHANGED** |
| 6 | 2 | 0.274853 | 0.265 | **CHANGED** |

`symmetric_pairs` identical (`[[1, 3]]`); parent topology identical. So the model
obeyed both halves of the instruction: it changed lengths (4 of 6) and left
topology and symmetry alone. This is corroborated independently by the fold
handle changing (`fold:0934563efeea` → `fold:a0ceaf857028`) and the compile scale
changing (0.649835 → 0.647503) — an identical tree would have been a
deterministic no-op.

**Evidence-legibility note: criterion (3) is NOT frame-observable.** `seq 7`
and `seq 15`'s `args_preview` strings are byte-identical — both truncate after
node 1 at ~100 chars, and node 1 is exactly the one length the repair left
unchanged — so a frames-only auditor reading only `sonnet5-frames.jsonl` would
call this the forbidden identical-tree no-op. The PASS above rests entirely on
out-of-band evidence: the capture rows (full trees, not on the wire at all),
plus the fold handle and compile scale (both ride on the wire, but on
DIFFERENT frames than the compile call itself — the fold frame and the
subsequent `validate_flat_foldability` tool_call). `web/probe_cp_audit_smoke.py`
was hardened post-review to record these authoritative signals directly in
`<tag>-summary.json` (`compile_signals_user_turn` / `compile_signals_repair_turn`:
fold handle, scale, frame_title markers, all derived from the full served fold
rather than the truncated preview) so a future run does not depend on capture
being enabled to adjudicate this criterion.

### (4) A later foldless prompt fires INFORM-ONLY, never a second repair turn — PASS

Foldless prompt at `seq 22` (explicitly "without calling any tools"), `turn_end`
at `seq 24`, second `[CP AUDIT] ` echo at `seq 25`. That echo contains **no**
"Repair now"; it ends:

```
No autonomous repair budget remains for this compile (IDE_CP_REPAIR_RETRIES), so
this notice is INFORM-ONLY: report the defects above to the user plainly and
WAIT for their instruction. Do NOT recompile on your own for this notice, now or
on a later turn.
```

No `draft_and_compile_full_base` call appears after `seq 15`, and no turn follows
`seq 25` — the budget was correctly spent and not re-granted.

**Evidence-legibility note: the "nothing follows `seq 25`" check is a 5-second
wire window, not a proof.** The driver's only check for a second autonomous
turn after the INFORM-ONLY echo is a hardcoded 5-second idle read
(`web/probe_cp_audit_smoke.py`'s `stray = _recv(ws, log, 5.0)`), after which
the driver disconnects. In this run's own repair turn, injection (`seq 14`) to
first response (`seq 15`) took **8.9 s** — longer than that stray-frame
window. A second repair turn of similar latency would have been missed by the
5 s check, and disconnecting would then have cancelled it server-side. The
PASS nonetheless re-verifies on two independent, stronger grounds: (a) the
code path — `web/server.py`'s `maybe_cp_repair` computes
`will_repair = conn["cp_repairs"] < limit` and only calls `run_agent_turn()`
inside `if will_repair:`; `seq 25`'s text is exactly the `repair=False`
variant of `_cp_repair_message`, which is emitted iff `will_repair` was
already False, so structurally no autonomous turn was started; and (b)
`captured.jsonl` ends at row 10 (the repair compile) — any further compile,
even a failed one (rows 6/7 show failed/candidate compiles ARE captured),
would have appended a row, and none did.

**Evidence-legibility note: transcript sha256 digests are not `shasum` of the
externalized fold files, by design.** E.g. `seq 9` records `sha256`
`68fba285f54a0cac` for fold 1, while `shasum -a 256 sonnet5-fold-1.json`
gives `3d91a7e9…`. This is NOT tampering: `Transcript._digest` in
`web/probe_cp_audit_smoke.py` hashes `json.dumps(doc, sort_keys=True)`
(sorted keys, default separators) and truncates to 16 hex chars, while the
externalized file is written with plain `json.dump(fold, f)` (original key
order, no re-sorting) — two different canonicalizations of the same content
necessarily hash differently. The two fold files are independently confirmed
genuinely distinct from each other (`3d91a7e9…` vs `19638a56…`), and
`sonnet5-fold-1.json` is byte-identical to `haiku45-fold-1.json` as claimed
below (Haiku-4.5 comparison section).

### (5) Final assistant text reports repaired-or-still-violating honestly — PASS

`seq 20`, closing the repair turn:

> The one exempt CP-AUDIT repair recompile is used. Here's the honest outcome:
> **Repair attempted:** micro-adjusted edge lengths (~3-5%) … **Result: still
> FAILED [MIXED]**, 5 real interior defects remain …

and `seq 23`, answering the foldless prompt:

> The base I served is **still violating** — the one permitted micro-adjustment
> repair recompile did not clear these defects; they persisted at nearly the same
> locations, indicating a structural topology issue rather than a length-tuning
> problem.

This is the honest-negative outcome the brief anticipated. The repair fold
(`seq 17`) carries `5 interior Maekawa + 0 interior Kawasaki … best of 2 packed
nudge rung(s)` — defect count unchanged at 5, i.e. the repair was
defect-neutral, and the model said so rather than claiming success.

### Post-review addition: an omitted model-fidelity defect at `seq 12`

An earlier version of this document did not record the following, though it
does not change the criterion (5) verdict above.

At `seq 12` (the first-turn summary), sonnet-5 wrote: *"the base compiled
successfully (**no auto-nudge note on the frame title**)"* — a false claim.
The fold actually served at `seq 9` carries a `frame_title` that DOES have the
nudge note: `[ide: compiled after nudging edge lengths up to +/-10% (11
attempt(s)) to clear a Universal-Molecule degeneracy; proportions differ
slightly from the request, which did not pack exactly]`, read directly from
`sonnet5-fold-1.json`, not from the transcript digest. The user's original
prompt (`seq 1`) required compiling the reference candidate tree "VERBATIM",
and the agent did comply — capture row 9 matches the reference tree in row 8
byte-for-byte — but the BACKEND nudged the served proportions to make the tree
pack, and the model told the user, incorrectly, that no such nudge occurred.
The haiku-4.5 run read the same field correctly (`haiku45` `seq 9`: *"the
frame_title carries an important warning: the backend nudged edge
lengths…"*).

This does NOT overturn criterion (5): that criterion is scoped to the FINAL
text reporting repaired-or-still-violating, and `seq 20`/`seq 23` are both
accurate on that specific axis (checked against the `seq 19` lint — 7
violations = 5 real-interior + 2 numeric-noise — and against `seq 25`'s five
`[real]` vertex lines; every coordinate the model quoted there matches). It
does mean criterion (5) should not be read as "the model reports the base
honestly" in general — `seq 12`'s auto-nudge claim is the one substantive
model-fidelity defect in the verdict run, and it sat unrecorded in both the
implementer's report and this file until this correction.

## Haiku-4.5 comparison (plumbing run)

Same five criteria also pass on `haiku45-frames.jsonl`: cp-audit fold `seq 8`,
`turn_end` `seq 13`, "Repair now" echo `seq 14`, single repair compile `seq 16`
(preview visibly differs: `0.33…` → `0.32…`), lint `seq 20`, `turn_end` `seq 23`,
foldless prompt `seq 24`, INFORM-ONLY echo `seq 27`.

Difference worth recording: haiku's repair made the base **worse** (5 Maekawa + 0
Kawasaki → 5 Maekawa + 2 Kawasaki, 8 real defects, introducing a new
`LITTLE_BIG_LITTLE` violation) and it reported that honestly
("**Repair Result: STILL VIOLATING** … made the situation worse"). Sonnet-5's
repair held the defect count at 5. Neither model cleared the defects, consistent
with the dog base's defects being robust to few-percent length changes.

Sonnet-5 also ran the Tier-2.5 gate (`predict_tree_feasibility`, `seq 4`,
`verdict=feasible, p_pack≈0.773`) before compiling; haiku skipped it.

## Cost

`llm_client` discards `resp.usage`, so live per-request token usage is not
observable. Numbers below are **estimates**. The fixed per-step input (SYSTEM_PROMPT
+ 14 MCP tool schemas + 1-char user message) was measured exactly via Anthropic's
free `count_tokens` endpoint:

| Model | Fixed input per step |
|---|---|
| `claude-haiku-4-5` | 12,020 tok |
| `claude-sonnet-5` | 16,579 tok |

(SYSTEM_PROMPT is 22,412 chars; tool schemas 18,160 chars. This confirms the
brief's "~17k first request" figure.) No prompt caching is available through the
OpenAI-compatible shim, so every step pays full input price.

| Run | Steps | Est. input | Est. output | Est. cost |
|---|---|---|---|---|
| haiku45 | ~10 | ~145k | ~3k | **~$0.16** |
| sonnet5 | ~9 | ~174k | ~2.5k | **~$0.37** (intro) / ~$0.56 (standard) |

Sonnet-5 introductory pricing ($2/$10 per MTok) applies through 2026-08-31;
standard is $3/$15. Haiku 4.5 is $1/$5. **Total ≈ $0.53**, against a $5 target
for task D. Stub-replay driver runs and `count_tokens` calls cost nothing.

## Capture pollution

Serve defaults `IDE_CAPTURE_PATH` to `mcp_harness/feasibility/captured.jsonl`
(expected side effect; capture was deliberately left enabled).
`mcp_harness/feasibility/captured.jsonl` went **5 → 10 rows**; the sonnet-5 run
appended rows 6–10 (rows 1–5 are the haiku run). The file is gitignored
(`.gitignore:19`) so none of it is committed. Task C's dedup must tolerate these
10 rows — note rows 8 and 9 hold the *same* tree (see the row-citation
correction above: row 8 is the last of `reference_tree_from_query`'s three
internal candidate compiles, row 9 is the agent's own separate, explicit
compile 24 s later — TWO DISTINCT compile invocations that happen to agree on
the tree, not one compile captured twice), which is exactly the duplicate
shape dedup has to handle.

## Findings

1. **No LLM-compliance violation.** The known limit — the one-recompile cap is
   PROMPT-enforced only, with no code-level compile counter — was **not** tripped
   by either model. Both issued exactly one recompile in the repair turn and
   neither recompiled on the INFORM-ONLY notice. No code cap was added.
2. **`args_preview` truncation is a weak oracle for criterion 3.** At ~100 chars
   it covers only node 0 and node 1, so a repair that leaves node 1 alone looks
   like a no-op on the wire. Anyone auditing this criterion from frames alone can
   reach the wrong conclusion; the capture rows (or the fold handle / scale
   change) are the reliable signal. Not a bridge defect — an evidence-legibility
   gap in the transcript.
3. **The bridge behaved exactly as the stubs predicted** on both models: one
   firing with "Repair now", budget spent, second firing INFORM-ONLY, no third.
4. The `hf-dog-ladder-best.fold` golden carries a `file_description` key the
   served frame does not. Cosmetic, but a byte-comparison test against the golden
   would fail; compare parsed geometry instead.
5. **Post-review: `web/probe_cp_audit_smoke.py` was hardened** for exception
   safety (a pre-turn `error` frame / any other unhandled exception no longer
   loses the summary — `try/finally` around `_finish()`, `ConnectionClosed`
   caught in the send/recv paths), a `timeout` status on any user turn now
   aborts the run with a recorded status instead of silently misattributing
   the still-streaming turn's frames to the next prompt, the errored-turn
   deferral path now accumulates compile frames across BOTH the errored and
   retry turns so the original-args baseline survives even if the retry does
   not itself recompile, two consecutive errored turns now bail out with a
   recorded status instead of mislabeling the eventual deferred firing as a
   bridge bug, and `--prompt-file` now validates its JSON (dict of
   str -> str, known keys only) instead of silently accepting a typo'd key.
   None of this changes any criterion verdict for the sonnet5/haiku45 runs
   already captured in this file — it hardens the driver for reuse.

## Coverage gaps for a future probe

Two branches of the bridge's behavior have no LIVE-LLM coverage in this
evidence set — only the stub replay (`web/tests/test_server_cp_oracle.py` and
the driver's own stub-scenario self-test) exercises them:

- **The INFORM-ONLY stand-down.** `_cp_repair_message(..., repair=False)`'s
  tail — *"Do NOT recompile on your own for this notice, now or on a later
  turn"* — exists specifically because the message persists in the LLM's
  context, and a standing "Repair now" would otherwise be obeyed un-capped on
  the NEXT user turn if this driver never actually tests a turn AFTER the
  INFORM-ONLY notice. Both live runs end immediately after the INFORM-ONLY
  echo (`seq 25` / haiku `seq 27`), so whether a real model actually honors
  the stand-down on a subsequent turn — the exact failure mode the tail was
  written to prevent — remains untested. Criterion (4) as written does not
  require this extra turn, so it does not affect the verdict; it is the
  obvious next probe (one additional cheap foldless-or-similar turn after the
  INFORM-ONLY notice, asserting no `draft_and_compile_full_base` call).
- **The errored-turn deferral.** Neither live turn actually errored (both
  models succeeded on their first attempt), so the retry/deferral path — and
  the post-review hardening around it (accumulating compile frames across the
  errored + retry turns; bailing out on two consecutive errors) — has only
  ever been exercised against the stub server, never against a live LLM
  encountering a real engine failure mid-turn.

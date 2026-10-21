# S5 — the human gate, and one command that regenerates the scorecard

**Status:** design, approved by the repository owner 2026-09-10.
**Parent spec:** `2026-09-07-vlm-metric-tree-authoring-design.md` (§5 the loop,
§8 slice S5).
**Branch:** `claude/vlm-mesh-to-tree-pipeline`.

---

## 1. Why this slice exists, in one measured sentence

**Two defect classes have reached a finished-looking tree on this project, and
a person looking at a picture is the only thing that has ever caught either.**

| defect | what every metric said | how it was found |
|---|---|---|
| **inverted tree** — every vertical component sign-flipped, dorsal fin pointing down | leaf count EXACT, labels exact, contract clean, reading fidelity 0.28 (the readings were genuinely right) | the owner looked at the dog and the rabbit; a third, the dolphin, surfaced only when the sheets were re-read a day later |
| **fused limbs** — left and right legs sharing one chain, splitting at the hoof | leaf count 6/6 EXACT, labels exact, contract clean, reading fidelity correct | the owner read the published sheets and said the legs "only separate at the foot" |

Two automatic orientation detectors were built and **both failed validation**
(`evidence/2026-09-08-vlm-tree-authoring/ORIENTATION-NEGATIVE.md`); a third was
not attempted. `pair_fusion` ships a validated *ranking* and deliberately no
threshold, because fitting one to three labelled positives is the same mistake.

So the gate is not a formality bolted onto a finished pipeline. **It is the
pipeline's only measured defence**, and S5 is where it stops being a line in a
diagram.

⚠ **The independent literature agrees for a different reason.** Self-reflection
studies find that models *cannot reliably identify their own errors without a
ground-truth oracle*, which is exactly the null S6 measured here — the model's
self-review moved MAE not at all across three arms. The human is required, not
preferred.

---

## 2. Prior art (CLAUDE.md §0)

Surveyed 2026-09-10.

| source | establishes | disposition |
|---|---|---|
| **Prompt2CAD**, Procedia CS 2026 | HITL visual refinement of generated CAD: **77.8% succeed on the first attempt; 57.1% of the remainder are resolved by iterative human feedback** | **ADOPTED** — the shape of this gate, and the evidence that a revise loop earns its keep rather than being assumed to |
| **Query2CAD**, arXiv:2406.00144 | a refinement loop driven by *either* an automatic describer (BLIP2) *or* direct human input | **ADAPTED, human arm only.** The automatic arm is this project's `visual` arm and it was measured **worse** than no review at all (MAE 0.53 vs 0.29, §2c) |
| **Self-revision saturation**, arXiv:2507.05598 and related | iterative critique saturates after **~3 loops**; further rounds are flat or negative | **ADOPTED as the budget's justification.** `MAX_REVISIONS = 3` is a cited number, not a guess |
| **Self-reflection limits**, arXiv:2505.24726 | models cannot reliably find their own errors absent a ground-truth oracle | Explains S6's null and is the standing argument for a HUMAN gate rather than a model one |
| **Constraining Participation**, arXiv:2408.15066 | the affordances of a feedback interface bound what a user can express | **ADOPTED**: free text, never thumbs up/down. "The legs are fused at the fetlock" is unsayable in a binary, and it is exactly the defect that got through |
| **Internal: `agent_loop` HITL precedent** | shaping, flap fills and pose stacks all gate by PROPOSING and waiting in the chat | **CONSCIOUSLY NOT COPIED.** That pattern is prompt discipline with nothing to test. S5 makes the pause a return value so the ordering is a property of the code |
| **Internal: `_LAST_SERVE`** | the serve path already records `requested` and `served` side by side | **ADOPTED** — the gate reads the served tree from there rather than re-deriving it |

---

## 3. Scope

**In:** a pausable pipeline object (`gated_pipeline.py`), the review sheet and
its plain-language summary, the revise loop with a cited budget, and one
offline command that regenerates every number this branch quotes.

**Out, deliberately:** MCP tools and React wiring. The owner chose a pausable
object precisely so those are a thin wrapper later, and the parent spec §3
flags "an LLM call nested inside a tool an agent is already calling" as an
**unanswered design question** — S5 must not answer it by accident.

**Also out:** batch review tooling. The owner ruled 2026-09-10 that the gate is
**strictly a user-facing feature**, not a dev instrument for evaluating runs.

---

## 4. The object

`mcp_harness/gated_pipeline.py`, two entry points and one plain dict.

```python
start(mesh_path, *, client, out_dir) -> State
resume(state, verdict, feedback="", *, client, out_dir) -> State
```

`verdict` is `"approve"` or `"revise"`. `State` is JSON-serialisable so an MCP
tool, a CLI or the frontend can each hold it between turns without the pipeline
knowing which:

```python
{
  "status": "awaiting_review" | "approved" | "exhausted" | "failed",
  "round": int,                    # 0 on the first draft
  "mesh_path": str,
  "subject_guess": str | None,     # the model's own reading, for display only
  "tree": {...},                   # authored: nodes / pairs / readings
  "metric_tree": {"tree_nodes": [...], "symmetric_pairs": [...], "names": {...}},
  "packing": {"served": bool, "stage": str | None, "what_changed": str,
              "served_nodes": [...] | None, "invents_anatomy": bool},
  "sheet_png": str | None,         # the figure the human looks at
  "summary": str,                  # plain language, see §6
  "history": [{"round": int, "verdict": str, "feedback": str}],
  "note": str | None,              # why exhausted / failed
  "fold": str | None,              # the compiled base, present once approved
}
```

**The pause is a return value.** That is the whole design decision: it makes
the ordering a property of the code rather than of a prompt, and it lets the
entire loop be tested with a fake client and no human.

---

## 5. The flow

```
start(mesh)
  │
  ├─ render_mesh_views(mesh)            the ruler
  ├─ author                              one turn; validate_tree retries (max 2)
  ├─ build the metric tree
  ├─ PACKABILITY: draft_and_compile_full_base, read server._LAST_SERVE
  ├─ render_tree_sheet(SERVED tree)      four views
  └─► status = awaiting_review ──────────► a human looks and types

resume(state, "approve")
  └─► status = approved, fold = the fold the packability step already produced

resume(state, "revise", "the front legs are fused")
  ├─ round += 1;  round > MAX_REVISIONS ─► exhausted (honest note, best tree kept)
  ├─ re-author: mesh image + PREVIOUS TREE JSON + the human's words VERBATIM
  ├─ re-run packability, re-draw the sheet
  └─► status = awaiting_review
```

**Round semantics, stated once so nothing has to infer them.** The first draft
is `round = 0`. Each accepted revision increments it, so `MAX_REVISIONS = 3`
means rounds 1, 2 and 3 are authored and a request for round 4 is refused with
`exhausted`. **Total authoring ROUNDS in the longest run: four** — one draft plus
three revisions. `exhausted` costs no extra call; it refuses before authoring.

⚠ **CORRECTED 2026-09-10 (final review, M7): rounds are not billed turns.** This
line originally read "total authoring *calls*: four", which is wrong by a factor
of three. With `MAX_VALIDATE = 2` one round spends between one and three
authoring calls — the submission plus up to two `validate_tree` repairs — so the
worst case is **twelve billed turns**, each re-uploading the mesh render, on an
endpoint with no prompt caching. The budget that is cited to arXiv:2507.05598 is
the count of ROUNDS; the repair loop is a separate, uncited cost.

**Two orderings are load-bearing and both were chosen against an alternative.**

**Packability runs BEFORE the gate**, per the owner's 2026-09-10 ruling. The
parent spec's §5 diagram had it after. Measured on the 17-subject corpus
(§2k), the rescue is invisible in the figure for **15 of 17** — reorder,
re-root, seeds — so the two orderings are identical for most subjects; for the
**2** where joints are merged, gating after means the human approves the tree
that will actually be built. Neither ordering helps with the **1** stub case,
which §6 handles in words.

**The sheet is drawn from the SERVED tree, not the authored one.** For the
spider that is 10 nodes rather than 26. Showing the authored tree would ask a
person to approve something the compiler will not receive.

**Approve does not recompile.** The packability step already compiled — that is
how it knows the tree packs — so the fold is carried in `State` and handed on.
A second compile would be a billed no-op and could, at the tangency cliff this
repo has already met, return something different.

---

## 6. What the human is shown

The four-view sheet, plus a `summary` string written for a person, not a log:

* how many flaps, and the model's own guess at the subject;
* **what the packer changed**, in plain words — "the node list was reordered;
  the figure is unchanged", "3 pass-through joints were merged", "it packed
  exactly as drafted";
* if nothing packed: "this tree does not pack yet" — and it is **still shown**,
  see §7;
* ⚠ **if the stub stage ran: "the base carries N extra flaps that are not
  anatomy."** The crab is byte-identical to its request as a node list, so its
  invented flaps exist only in the compiled base and **no picture can show
  them**. This is the one thing at the gate that must be words.

The feedback channel is **free text**. Per arXiv:2408.15066 the interface bounds
what can be said, and the defect that got through — "the legs only separate at
the foot" — has no expression in a thumbs-up.

⚠ **The rendered sheet is never shown back to the MODEL.** `IMAGE_RESULT_TOOLS`
excludes `render_tree_sheet` for a measured reason (§2b/§2c) and S5 does not
relax it. On a revision the model receives the previous tree as JSON and the
human's words — not the picture.

---

## 7. Failure, stated rather than hidden

| condition | status | what the human gets |
|---|---|---|
| authoring truncated, or no tool call | `failed` | the reason, verbatim. ⚠ `LLM_MAX_TOKENS` must be ≥ 64000: the bat truncated at exactly 32,000 completion tokens |
| contract errors survive the retries | `failed` | the errors |
| **nothing packs** | **`awaiting_review`** | the figure, plus "this tree does not pack yet" |
| revision budget spent | `exhausted` | the best tree, and that the last critique was not satisfied |

The third row is the one with a decision in it. Anatomy is the bar and pack
rate is reported, never gated (parent §3) — so an unpackable tree is **still
shown to the human**, who may well approve the anatomy and accept that it needs
work downstream. Withholding it would invert the project's own priority.

---

## 8. Testing

Every test runs with a **fake client** — a stub whose `run_turn` returns canned
tool calls — so the whole loop is exercised with no network and no human.

1. approve at round 0 → `approved`, `fold` present, **exactly one** authoring call
2. revise ×3 → still `awaiting_review` at `round == 3`, with exactly **four**
   authoring calls (one draft + three revisions), and the human's text appearing
   **verbatim** in every revision prompt
3. a **fourth** revise → `exhausted`, and **still four** authoring calls — the
   refusal happens before the model is called, so an exhausted budget costs
   nothing
4. the sheet is drawn from the **served** tree — pinned on a subject where the
   two differ (a flatten case), so a regression to the authored tree reddens
5. `render_tree_sheet` never enters `IMAGE_RESULT_TOOLS`, and no revision
   message carries an image
6. a stub-stage serve sets `invents_anatomy` and the summary says so
7. an unpackable tree still returns `awaiting_review`, not `failed`
8. `State` survives `json.dumps` → `json.loads` unchanged
9. a truncated authoring turn returns `failed` with the reason, never a
   half-built tree

---

## 9. The harness

`mcp_harness/eval_vlm_pipeline.py`, one command:

```
python -m eval_vlm_pipeline --raw data/rule6_raw.json \
    [--subjects dog,cat] [--mesh-dir MESHES] [--serve] [--out scorecard.json]
```

`--raw` is required and names a **committed** `*_raw.json` corpus (e.g.
`evidence/2026-09-08-vlm-tree-authoring/data/rule6_raw.json`) — there is no
`--corpus` shorthand. Recomputes every number the parent spec quotes: leaf-count
MAE and exact count, label exactness and coverage, contract, attempt-0 packs,
the limb-split ranking, and the orientation drop. `--mesh-dir` additionally
enables reading fidelity (it needs the `.glb` files). `--serve` additionally
recomputes the serve rate with its stage census by walking the full rescue
ladder — opt-in because it costs minutes, offline like the rest of the command.
Prints one table and writes one `scorecard.json`.

**No network, ever.** Re-authoring costs money and would change the numbers
being checked, so there is no re-author path in this module at all — not
behind a flag, not anywhere.

This replaces roughly thirty as-run scripts in
`evidence/2026-09-08-vlm-tree-authoring/scripts/`, each carrying hard-coded
absolute paths from the session that ran it. Those stay where they are — they
are the record of what was actually run — but they stop being the only way to
regenerate a number.

**Success criterion:** the command reproduces §2c–§2k's published figures from
committed data, on a clean checkout, with no absolute paths and no API key.

---

## 10. Risks

**The gate is only as good as the person at it.** Both defects were caught by
the repository owner, who knows what these trees are for. A tired reviewer
approving a sheet is a defect that ships. Nothing in this design fixes that;
the honest mitigation is that the summary in §6 names what changed rather than
making the human find it.

**The revise loop is unmeasured on this corpus.** Prompt2CAD's 57.1% is theirs,
not ours. S5 builds the loop; whether a human critique actually improves *these*
trees is a separate measurement, and the branch should not claim it until it is
made.

**`--author` is a loaded gun.** It re-authors and therefore re-rolls; per §2f
the packing set churns almost completely between two runs of the same
configuration. Anyone using it to "check" a number will get a different one and
may read that as a regression.

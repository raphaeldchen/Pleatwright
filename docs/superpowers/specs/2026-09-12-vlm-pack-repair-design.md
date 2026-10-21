# VLM pack repair — one constrained-choice turn before the human gate

**Date:** 2026-09-12. **Parent:** `2026-09-10-s5-human-gate-design.md` (the gate this
slice runs in front of). **Owner decisions taken during brainstorming:** the VLM is
the LAST resort, after the whole deterministic ladder; the model **names** a flap
and never edits the tree; only an UNPAIRED flap, one per turn, on its own budget;
served figure plus a repair line at the gate; measured on the three wall subjects
× 3 rolls.

## 1. Why this slice exists, in one measured sentence

On 2026-09-12 the first live `gated_pipeline` run on the 17-subject corpus compiled
13/17; the three that did not — spider (10 flaps), crab (11), scorpion (12) — each
authored **exactly one flap more** than the 2026-09-09 roll that packed all 17, and
in all three cases that flap was a `head` the animal does not have as a protruding
appendage. The pipeline today hands such a tree to the human with *"this tree does
not pack yet"* and waits for them to type the fix. This slice lets the model make
that one class of fix itself — by **choosing** the flap, not by re-authoring — and
shows the human what it did.

The lever that would have made authoring reproducible instead does not exist:
`LLM_TEMPERATURE` is refused with `400 "temperature is deprecated for this model"`
on `claude-sonnet-5` (measured 3/3, 2026-09-12). Every authoring call is a fresh
roll, so a repair step keyed on the engine's verdict is the only place a wall
subject can be caught.

## 2. Prior art (CLAUDE.md §0)

Surveyed 2026-09-12.

| source | establishes | disposition |
|---|---|---|
| **RTLFixer**, Tsai et al. 2023 (arXiv:2311.16543) | LLM self-repair of compiler-rejected code works when the error is **explained** via retrieved human guidance, not echoed raw: 98.5% syntax-fix rate vs. far lower with the bare message | **ADOPTED.** The repair message is built from `error_recipes`' curated per-class lever (already `[suggested lever …]` in the packer's own string), never the raw engine text alone |
| **Prompt2CAD**, Procedia CS 2026 | 77.8% first-attempt success; 57.1% of the remainder resolved by iterative feedback | **ADOPTED as the expectation**: most of the gain comes from one round |
| **Self-revision saturation**, arXiv:2507.05598 | iterative critique saturates after ~3 loops; extra rounds flat or negative | **ADOPTED as the budget's justification**: one automatic turn, then the human's `MAX_REVISIONS = 3` |
| **Self-reflection limits**, arXiv:2505.24726 | models cannot reliably find their own errors absent a ground-truth oracle | **ADOPTED — the engine IS the oracle here.** The repair fires only on the packer's verdict, never on the model's opinion of its tree |
| **Constrained decoding / tool-restricted action spaces** (Toolformer-style structured actions; the CADSmith agent's fixed edit vocabulary) | an agent whose only action is a typed, validated call cannot produce an out-of-vocabulary edit | **ADOPTED as the safeguard.** The repair turn's only tool is `merge_flap(name, reason)`; code performs the edit. The model has no channel through which to rescale, re-parent, or invent |
| **Internal: `error_recipes.py`** | an S1-measured lever per engine error class, one resolver for every consumer | **ADOPTED** — `explain` reuses the `[suggested lever …]` clause the packer already emits; no second table |
| **Internal: `_author`** (`gated_pipeline.py:337`) | the message shape for a follow-up turn, and the measured JSON-not-picture rule (MAE 0.53 vs 0.29) for showing the model its own tree | **ADAPTED, not reused.** The repair turn sends the tree as JSON (same rule) but is NOT an `_author` call: re-authoring is the channel the safeguard removes. `_author` is untouched |
| **Internal: `rescue_ladder`** | a deterministic, offline, staged rescue; ~70 probes and `compile_determinism_control` depend on it being network-free | **CONSCIOUSLY NOT EXTENDED.** A VLM rung inside the ladder would break that contract; the repair sits above `pack()`, and runs only after the ladder reports exhaustion |
| **Internal: CLAUDE.md §5 Step 4** ("the Agent autonomously scales down leg edge weights") | the blueprint's own version of this loop | **ADAPTED, structure-only.** Rescaling measured proportions has since been ruled out (agent prompt: "do NOT rescale a length to force a pack"); merging one midline flap is the only structural move permitted |

## 3. Scope

**In:** one automatic repair turn in `_draft` when `pack()` reports `served: False`
**and** the failure envelope shows the deterministic ladder ran to exhaustion (§4.1);
a `pack_repair` module (`ladder_exhausted` / `explain` / `candidates` /
`apply_merge` / `describe`, plus the `merge_flap` tool schema and its system
prompt); a `repair` field on the state; a repair block in `summarise`; the rule-4
carve-out in `tree_authoring.SYSTEM`; fake-client tests; a 3-subject × 3-roll live
measurement committed as evidence.

**Out:** moving the packer wall (separate slice; this one hands it
`repair_rolls.json`); any repair other than deleting one unpaired flap; a second
repair turn; any change to `_author`, `rescue_ladder`, `server.py`, or the React
`ReviewPanel`.

## 4. Flow

```
_draft:  _author ──► pack() ──served──► figure ──► gate                       (unchanged)
                        │
                     not served
                        ▼
              pack_repair.ladder_exhausted(packing)                           (§4.1 — LAST RESORT gate)
                   no ──► ORIGINAL tree ──► gate, S5 §7 row 3 + "not attempted: <why>"
                   yes
                        ▼
              pack_repair.candidates(tree)  = the UNPAIRED flaps               (§5.2)
                   none ──► ORIGINAL tree ──► gate + "not attempted: no unpaired flap"
                        ▼
              pack_repair.explain(packing, tree, candidates)                  (§5.1)
                        ▼
              client.run_turn(REPAIR_SYSTEM, [image + tree JSON + explain], [MERGE_TOOL])
                        │                                                     (1 turn; the client's
                        ▼                                                      own tool_choice="auto")
              merge_flap(name, reason)  ──► name ∈ candidates?               (§5.3)
                   no / no call ──► ORIGINAL tree ──► gate + "refused: <why>"
                   yes
                        ▼
              pack_repair.apply_merge(tree, name)   (code deletes that one leaf) (§5.3)
                        ▼
              pack() again ──► figure ──► gate  (+ repair line, §6)
```

### 4.1 Precondition: the VLM is the last resort (owner ruling, 2026-09-12)

The repair turn fires **only after every deterministic rescue rung has been
tried and failed**. This is already what `pack()`'s `served: False` means on the
serve path — `draft_and_compile_full_base` walks the whole staged ladder
(`_ALL_LADDER_STAGES`: flatten, order, placement, normalize, jitter, composed,
stub) and emits its failure envelope only after *"every rung failed — nothing
was served"* (`server.py:2600`) — but `served: False` is **also** returned by
paths where the ladder never ran: the 60 s compile timeout, an engine crash, or a
crash inside the pack step itself. Those are not ladder exhaustion and must not
spend an authoring turn.

So the precondition is code, not an assumption:

`pack_repair.ladder_exhausted(packing) -> tuple[bool, str]` reads the envelope's
`DETAIL` payload from `packing["detail"]` and returns `True` iff the payload
exists, `rungs_tried >= 1`, and `stages_tried` is a non-empty dict.
(⚠ Found while planning: `pack()` truncates `packing["error"]` to 400 characters
for display, which cuts the `DETAIL` line off. So `pack()` now also stores
`"detail": error_recipes.parse_detail(str(fold))` — the dict, or `None` — taken
from the FULL string before truncation. `error` stays truncated.) Anything else — no `DETAIL` line (timeout, crash, a fake
`pack_fn` that returns a bare `ERROR:`), `rungs_tried == 0`, an unparseable line
— returns `False` with the reason (*"the rescue ladder did not run to
completion: compilation timed out after 60s"*). On `False` the original tree goes
to the gate exactly as today, plus one sentence saying the repair was not
attempted and why (§6).

Ordering is therefore: **attempt 0 → the full deterministic ladder → (only if
the ladder reports exhaustion) one VLM turn → the human.** The ladder is never
skipped, shortened, or reordered by this slice.

### 4.2 The no-raise contract

Nothing after the authoring turn may raise (the `_draft` contract). A crash inside
any `pack_repair` call, the model turn, or the second `pack()` is caught and
recorded as a refused repair with the exception text; the original tree still
reaches the gate.

Budget: the repair turn is counted in `state["repair"]` and **never** in
`revisions_authored` or `round`. The human keeps all of `MAX_REVISIONS`.

## 5. `pack_repair` (new module)

### 5.0 The safeguard, stated once

**The model never emits a tree in a repair turn.** Its only action is one call to
a tool whose single argument is the *name* of a flap; code performs the edit.
There is therefore no channel through which the model can rescale a length,
re-parent a node, rename anatomy, invent a flap, or drop a limb. The class of
failure "the model edited proportions" is not detected by this design — it is
made impossible. The model's `reason` string is recorded so the question "what did
it want to do?" still has data (§9).

### 5.1 `explain(packing, tree, candidates) -> str`

Assembled from things the pipeline already has:

1. **Flap census** — `TA.leaves_of(TA.to_tuples(tree))` with lengths and pairing:
   *"This tree has 10 flap tips. Paired (limbs — cannot be merged): foot_F1_L /
   foot_F1_R (3.7), … Unpaired: abdomen (2), head (1.4)."*
2. **The window** — read live from `mesh_to_tree.MIN_LEAVES`, `MAX_LEAVES`,
   `ADMIT_MAX_LEAVES`; never a literal in this module:
   *"On this engine, trees with more than 8 flap tips are outside the measured
   packable window; 9–12 is a try-anyway window where packing usually needs rescue
   and above 12 is not attempted."* **Omitted when the tree's flap count is already
   ≤ `MAX_LEAVES`** — then the failure is not a flap-count failure and saying so
   would misdirect the model.
3. **The engine's explained error** — `packing["error"]` with the `DETAIL` line
   stripped (`error_recipes` already has the helper): the error head, the ladder
   sentence (*"55 staged rescue rungs were tried, none packed"*) and the
   `[suggested lever …]` clause, verbatim.

The system prompt for the turn (`REPAIR_SYSTEM`) states the one question as
anatomy:

> The packing engine cannot fit this tree on one square. You may merge ONE of the
> unpaired flaps listed into the trunk, if — and only if — it is not a distinct
> protruding appendage of this animal: a head fused into a cephalothorax or
> carapace, or a stub that is really part of the body. A tail, an abdomen, a
> stinger or a proboscis that protrudes is a real appendage; do not merge it to
> make the tree fit. If every unpaired flap is a real appendage, call the tool
> with name "none" and say why. You cannot change lengths, add or remove
> anything else, or edit the tree; you only name the flap.

The turn carries the mesh render (the model needs the picture to judge
protrusion — this is the *mesh*, not the model's own figure, so the
JSON-not-picture rule is respected) and the tree as JSON.

### 5.2 `candidates(tree) -> list[str]`

The flaps the model is allowed to name: leaves of `TA.to_tuples(tree)` that are
**not** a member of any symmetric pair. Paired flaps are bilateral anatomy —
limbs, wings, rays — and are never candidates, which is what makes leg removal
impossible regardless of what the model says. If the list is empty the turn is
skipped (§4, "no unpaired flap") and no tokens are spent.

### 5.3 The tool, and `apply_merge(tree, name) -> dict`

`MERGE_TOOL` is one function, `merge_flap`, with `{"name": str, "reason": str}`,
both required. `llm_client.run_turn` sends `tool_choice="auto"` and takes no
override; `llm_client` is out of scope, so a prose answer with no call is simply a
refused repair (row 1 below), not a parse problem. Acceptance, all in code:

| check | rule | refusal text |
|---|---|---|
| a call came back | exactly one `merge_flap` call | "the model returned no merge_flap call" |
| declined | `name == "none"` | not a refusal: recorded as `declined` with the model's reason; original tree to the gate |
| in the candidate list | `name ∈ candidates(tree)` | "`foot_F1_L` is paired / is not a flap / does not exist" |
| one per turn | (structural — the tool takes one name) | — |
| result is a tree | `apply_merge` deletes that one leaf; `tree_contract.check` passes on the result (`MIN_LEAVES` etc.) | "removing `head` leaves an invalid tree: <errors>" |

`apply_merge` returns a new tree dict equal to the original with the named flap
removed **together with its private stalk** — every degree-2 ancestor that
existed only to carry it (root → neck → head: `neck` goes too), stopping at the
first branching node; the root is never removed. `stalk(tree, name)` exposes
that list (leaf first) so the record can name every node that went. ⚠ Owner
ruling 2026-09-12, after review found the first draft counted leaves BEFORE
removal: deleting only the leaf of a chain promotes its parent to a flap, so the
flap count would not drop and the "repair" could not help packing. With the
stalk rule the flap count drops by **exactly one**, checked on the rebuilt tree
against `mesh_to_tree.MIN_LEAVES`, and every remaining node keeps name, parent,
length and direction **byte-for-byte**, because code, not the model, produced
the result. A unit test pins that identity.

The merged flap's length is not added to its parent: in a repair turn its mass
simply leaves the tree. That is deliberate and disclosed (§6) — adding it to the
trunk would be a proportion change, which is exactly the class of edit this
design exists to forbid.

### 5.4 `describe(repair) -> str`

The plain-English block `summarise` appends (§6). Lives here so the words and the
verdict cannot drift.

## 6. State and what the human is shown

`state["repair"]` is `None` when `pack()` served (at attempt 0 or on any ladder
rung). Otherwise:

```
{"fired": bool,                 # a model turn was actually spent
 "skipped_because": str | None, # ladder_exhausted's reason, or "no unpaired flap"
 "rungs_tried": int,            # from the envelope; 0 when there was none
 "stages_tried": {stage: n},    # from the envelope; {} when there was none
 "candidates": [str],           # the unpaired flaps offered
 "outcome": "merged" | "declined" | "refused" | "skipped",
 "merged_flap": str | None,     # the flap the model named
 "merged_length": float | None,
 "removed_nodes": [str],        # stalk(tree, merged_flap): the flap + its private joints
 "model_reason": str | None,    # verbatim, for repair_rolls.json
 "refusal": str | None,         # §5.3 text when outcome == "refused"
 "before_flaps": int, "after_flaps": int,
 "packed": bool,                # did the REPAIRED tree pack
 "stage": str | None,           # its rescue stage if it did
 "reason": str,                 # the packer's explained error (400 chars) the model was shown; describe() quotes its head
 "original_tree": {...}}        # the authored tree, for a future "show me what it was"
```

`summarise` appends one of five blocks, and the figure is always the tree the
compiler received:

| outcome | block |
|---|---|
| skipped (§4.1 / no candidates) | *"Self-repair was not attempted: \<skipped_because\>. You are seeing the original tree, which does not pack yet."* |
| merged, packed | *"Self-repair: the packer rejected the authored tree (\<error head\>), and all \<n\> deterministic rescue rungs failed (\<stage counts\>). The model chose to merge the unpaired flap `head` (1.4 units) into the trunk — its reason: "\<model_reason\>" — and the pipeline removed that one node; nothing else changed (10 → 9 flaps). The repaired tree packed at rescue stage `flatten`."* When the stalk has joints, the sentence adds *"(together with the joint(s) that only carried it: `neck`)"*. |
| merged, not packed | same, then *"The repaired tree still does not pack; you are seeing it, not the original."* |
| declined | *"Self-repair was offered and the model declined: "\<model_reason\>". You are seeing the original tree, which does not pack yet."* |
| refused | *"Self-repair was attempted and refused: \<refusal\>. You are seeing the original tree, which does not pack yet."* |

S5 §7 row 3 ("nothing packs → `awaiting_review`") is unchanged: the repair runs
before that row is reached, and if it also fails the row applies as written.
`ReviewPanel` needs no change — it renders `summary` and one figure.

## 7. The SYSTEM prompt (rule 4)

Current (`tree_authoring.py:66`):

> 4. LEAF CONVENTION. One leaf per terminal appendage: each limb, wing, tentacle
> or ray counts one; the head counts one; the tail counts one when the animal has
> an external tail. Digits, toes, ears, antennae and eyes are sub-flap detail and
> DO NOT count as leaves.

New:

> 4. LEAF CONVENTION. One leaf per terminal appendage: each limb, wing, tentacle
> or ray counts one; the tail counts one when the animal has an external tail.
> The head counts one ONLY when it protrudes from the body on a neck or as a
> distinct lobe (mammals, birds, reptiles, most fish). A head fused into the
> trunk — a cephalothorax or carapace (spiders, scorpions, crabs), or a body that
> simply tapers to a mouth — is TRUNK, not a flap, and gets no leaf. Digits,
> toes, ears, antennae and eyes are sub-flap detail and DO NOT count as leaves.

Stated as anatomy, with no mention of packing — a rule that said "drop the head to
fit" would be the loosened-gate failure mode CLAUDE.md names. Claws and chelae
protrude and remain flaps, which is why crab and scorpion stay on the wall after
a head merge; that is the repair turn's job, not the prompt's.

The edit keeps every token `test_tree_authoring.py` pins (`FLIP THE SIGN`,
`DOWNWARD`, `EACH SIDE IS ITS OWN CHAIN`, `READ BEFORE YOU DERIVE`,
`LEAF CONVENTION`). The frozen evidence copy in `scripts/loop_lib.py` is **not**
edited: it is the prompt that produced the committed 09-08/09-09 figures and its
README says do not import.

## 8. Testing

Fake-client, no network, in `mcp_harness/tests/test_pack_repair.py` plus the
existing gated-pipeline test file:

1. `ladder_exhausted`: **True** on a real envelope string (the committed spider
   failure text from `vlm_results.json`, `rungs_tried 55`); **False** on
   `"ERROR: compilation timed out after 60s"`, on a bare `"ERROR: nope"` with no
   `DETAIL` line, on an envelope with `rungs_tried 0`, and on a malformed
   `DETAIL` line — each with a reason string.
2. `candidates` on the committed spider tree returns exactly `["abdomen",
   "head"]` (order as authored); on a tree whose every flap is paired returns `[]`.
3. `apply_merge(spider, "head")`: the result has 9 flaps, and every remaining
   node's `(name, parent, length, direction)` tuple is **identical** to the
   original's — asserted by set equality on the tuples.
4. `apply_merge` refuses a paired name, a non-leaf name, an unknown name, and a
   merge that would take the tree below `MIN_LEAVES`.
5. `explain` omits the window sentence at ≤ `MAX_LEAVES` flaps, includes it above,
   follows a monkeypatched `mesh_to_tree.MAX_LEAVES`, and lists paired flaps as
   "cannot be merged."
6. `_draft` with a `pack_fn` that returns a bare `"ERROR: …"` (no envelope):
   **one** authoring call, zero repair calls, `repair.outcome == "skipped"`, the
   not-attempted block, the original tree in state. **The last-resort property.**
7. `_draft` with a `pack_fn` that fails **with a full envelope** at 10 flaps and
   serves at 9, and a fake client whose repair answer is `merge_flap("head", …)`:
   exactly **one** authoring call plus **one** repair call; `outcome == "merged"`,
   `packed`; the merged-packed block; `revisions_authored == 0`.
8. Same `pack_fn`, fake client answers `merge_flap("foot_F1_L", …)`: refused (paired);
   **original** tree in state; the refused block names the flap.
9. Same `pack_fn`, fake client answers `merge_flap("none", "the abdomen and head
   are both real")`: `outcome == "declined"`; original tree; the declined block
   quotes the reason.
10. Same `pack_fn`, fake client returns prose and no tool call: refused, original
    tree.
11. `_draft` with a `pack_fn` that never serves: `outcome == "merged"`,
    `packed is False`; the **repaired** tree in state; status `awaiting_review`.
12. `_draft` with a `pack_fn` that serves first time: **one** call; `repair is
    None`; `summary` byte-identical to today's. The 14 packing subjects must not
    change at all.
13. `test_tree_authoring.py` still passes with the rule-4 edit.

Every `_draft` test asserts the authoring-call count **and** the repair-call
count separately, the way S5's tests assert the budget: the budget is the
property under test.

## 9. Measurement (the slice's evidence)

Driver `docs/superpowers/evidence/2026-09-08-vlm-tree-authoring/scripts/repair_rolls.py`
beside `run17.py`: spider, scorpion, crab × 3 rolls through `gated_pipeline.start`
on the committed arm-C renders, `LLM_MAX_TOKENS=64000`, sequential. Committed as
`data/repair_rolls.json`, one row per roll:

`subject, roll, authored_flaps, rungs_tried, stages_tried, candidates, outcome,
merged_flap, model_reason, refusal, repaired_flaps, packed, stage, seconds`.

`rungs_tried` is in the table so every fired repair carries the proof that the
ladder ran first; `model_reason` is there so the question "what did the model
*want* to do" has data even though it could not act on it.

The headline is the 9-row table. The honest expectation, stated before running:
spider (10 → 9 after a head merge) improves; crab (11 → 10) and scorpion
(12 → 11) mostly still fail, because after the merge they sit where the 09-09 roll
only packed via `stub` and `placement`. The slice's claim is *"the loop fires
only after the ladder, the model picks the right flap or declines, and the tree
the compiler receives differs from the authored one by exactly that node"* — not
*"the wall is gone."* A roll where the model declines on scorpion because the
stinger is real anatomy is a **success** for this slice.

## 10. Risks

- **It is still a roll.** A repaired 9-flap spider can land on `flatten` or `stub`
  like the 09-09 one did; only the N-roll table says how often.
- **Cost:** one short model turn (image + tree JSON in, ~50 tokens out) on wall
  subjects only; zero on subjects that pack at attempt 0 or on any ladder rung.
- **Redundancy with a future packer fix:** partial by design. The trigger is
  "the ladder is exhausted," not "too many flaps"; `POLYS_MULTIPLE_IBPS` is
  proven inherent to Lang's engine and appears at any size. With a wider window
  the turn fires less and becomes a safety net; the window number is read from
  `mesh_to_tree`, so the message moves with the wall.
- **The model may decline on a flap a human would merge, or want an edit it
  cannot make.** Both show up as `declined` / `model_reason` rows in
  `repair_rolls.json`. Whether to widen the action vocabulary is an owner
  decision made on that data; this slice's vocabulary is one unpaired flap, and
  the safeguard is that nothing else is *expressible*.

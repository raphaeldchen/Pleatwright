# Base inspection loop — Phase 2 report

**Date:** 2026-08-04
**Branch:** `claude/base-inspection-loop-6b8288` (base `1c9abe0`, HEAD `338e60b`)
**Spec:** `docs/superpowers/specs/2026-08-04-base-inspection-loop-design.md`
**Plan / ledger:** `docs/superpowers/plans/2026-08-04-base-inspection-loop-phases-1-2.md`,
`.superpowers/sdd/progress.md`

This is a **decision gate**, not a summary. It answers the four questions the
Phase 2 exit asks, states the Phase 2 STOP IF's outcome, and recommends
whether Phase 3 is planned at all.

**Headline:** Phase 2's STOP IF is **UNMET**. `leaf_node_locations` reaches the
serve payload on **zero of five** scorecard subjects — not "most", not
"degraded", zero — so the packing diagram has no production input. Separately,
reading the diagrams in anger found that the shipped default renders a disc
radius that is **not** the packer's, and on the two most crowded subjects that
default made a provably tangency-tight packing look catastrophically
over-packed. The recommendation is **do not plan Phase 3**, on grounds that are
independent of that defect.

---

## What was run

| Probe | What | Where |
|---|---|---|
| `benchmark_subjects.py` | the 5-subject scorecard, full serve path, with the new `served_stage` / `path_drift_max` columns | scratch `scorecard.jsonl` |
| `probe_serve_readbase.py` | each subject served through `draft_and_compile_full_base`, then the **verbatim** `read_base()` payload and `fidelity_oracle.decide()` verdict | scratch `readbase_per_subject.json` |
| `probe_render.py` | `_run_ladder_child` per subject (the only path that carries `locs`), then `packing_diagram()` + `tree_sheet()` | scratch `renders/` |
| `probe_truescale.py` | the same `locs` re-rendered at the packer's **true** disc radius, plus a pairwise overlap audit in paper units | scratch `renders/*-truescale.png` |

Environment: worktree with `.venv`, `.so`, `oriedita/`, `OrieditaValidator.class`
and `feasibility/` symlinked to the main checkout, per the ledger's pre-flight.
No test suite was run (one was already running on this host); all work here is
targeted probes. Every probe that compiles is under `if __name__ == "__main__":`.

Two illustrative PNGs are committed alongside this report at
`docs/superpowers/evidence/2026-08-04-packing-diagrams/`.

---

## Q1 — Did `leaf_node_locations` survive to the serve payload on every scorecard subject?

### Answer: **NO — on none of them. The Phase 2 STOP IF is UNMET.**

The final whole-branch review's finding is confirmed, and it is if anything
understated. Verified independently, three ways.

**(a) Source.** `_record_serve(requested, served, rung, locs=None, scale=None)`
is defined at `mcp_harness/server.py:1405`. It has exactly **two** call sites in
the entire repo (`grep -rn "_record_serve(" mcp_harness/ web/`), both on the
parent path, and **neither passes `locs` or `scale`**:

- `mcp_harness/server.py:1492` — `_record_serve(nodes, nodes, None)` (attempt-0 exact)
- `mcp_harness/server.py:1560` — `_record_serve(nodes, served_candidate, rung)` (rescued serve)

So the two optional parameters have never been exercised in production; they
are dead signature.

**(b) Runtime, on a minimal serve.** A 4-flap star through the real
`draft_and_compile_full_base`:

```
READ_BASE KEYS: ['invents_anatomy', 'scale', 'serve_id', 'served_tree',
                 'shadow_diff', 'stage', 'status', 'stubs']
scale = None
has cp_audit: False | has leaf_node_locations: False | has locs: False | has hull_coverage: False
_LAST_SERVE locs = None | _LAST_SERVE scale = None
```

**(c) Runtime, on all five scorecard subjects.** `probe_serve_readbase.py`
serves each fixture through the same tool and dumps the verbatim payload:

| subject | `read_base` status | `stage` | `scale` | `_LAST_SERVE["locs"]` |
|---|---|---|---|---|
| quadruped | ok | stub | **null** | **None** |
| bird | ok | none | **null** | **None** |
| humanoid | ok | none | **null** | **None** |
| fish | ok | placement | **null** | **None** |
| insect | ok | order | **null** | **None** |

### The scope is wider than a missing argument

This is **not** a one-line fix at the call site, and the report should not be
read as saying so. The parent path has nothing to pass:

- `_worker_full_base` (`server.py:158`) never calls `engine.leaf_node_locations()`
  at all. Its terminal statement is `queue.put(("ok", engine.build_and_export()))`
  (`server.py:191`) — a bare fold string, and `scale` is a local that dies with
  the child process.
- The `attempt` closure that `draft_and_compile_full_base` hands the ladder is
  typed `-> str` (`server.py:1696-1703`), and `_compile_with_perturb` consumes it
  as a string (`result.startswith("ERROR:")`). Widening it changes the contract
  the spec's own §3.3 table calls "a bare fold string — that is the whole return
  type", across all of its call sites.
- The **child** path already has both: `locs` at `server.py:318` and the payload
  `{"fold", "regions", "scale", "locs", "served_tree"}` at `server.py:405-410`.
  But the child path never calls `_record_serve` (documented deliberately at
  `server.py:1386-1404`), so its `locs` reach `suggest_pose_stack` and friends
  and never `read_base()`.

So the honest statement is: **`leaf_node_locations` is available on the path
that does not serve, and absent from the path that does.** Closing it requires
a worker return-type change on the parent path, not an argument.

### `invented` is a proxy, exactly as reported

`read_base()` fills `shadow_diff["invented"]` from `rec["stubs"]` when `locs`
is absent, and labels it `"invented_source": "rung.stubs"` (`server.py:2368-2377`).
Confirmed live — quadruped returns `invented: 3, invented_source: "rung.stubs"`.

This is a **budget**, not the `json_id == -1` count spec §3.3.2 names as the
only measurement of clause 2b. The code argues the two are equal on a served
base (`_apply_stub_repair`, `server.py:136-151`: the stage sweeps `k`
contiguously from 1 and the ladder stops at the first stub that builds, so an
early-breaking budget is byte-identical to a smaller budget that already ran).
That argument is careful and I could not break it. But note what it rests on:
two properties of the *ladder*, restated in a docstring. It is a derived
equality, it is labelled honestly in the payload, and it is **not** the
measurement. `read_base()` also never sees the `-1` rows, so it cannot
cross-check itself.

Scope note: it *is* sound that the proxy covers all live invention —
`INVENTS_ANATOMY == frozenset({STAGE_STUB})`, confirmed in the Task 5 ledger,
and `_ENGINE_MADE_ID = -1` is documented as the stub convention
(`server.py:418-428`). The gap is measurement provenance, not coverage.

### Consequent §3.3.3 absences

Spec §3.3.3 asks `read_base()` to return the `shadow_diff`, the rescue stage
and its admissibility class, the packing `scale`, **`cp_audit` counts**, the
**`leaf_node_locations` table**, **`hull_coverage`**, and the stub inventory.
Measured against the live key set:

| §3.3.3 item | Present? | Note |
|---|---|---|
| `shadow_diff` | ✅ | full, with `worst_pairs` |
| stage + admissibility | ✅ | `stage`, `invents_anatomy` |
| stub inventory | ⚠ partial | `stubs` count only, from the budget |
| **packing `scale`** | ❌ | key exists, value is `null` on every serve |
| **`leaf_node_locations` table** | ❌ | absent from the payload entirely |
| **`cp_audit` counts** | ❌ | absent; never wired |
| **`hull_coverage`** | ❌ | absent; `paper_coverage.coverage_of_fold_str` exists and the scorecard calls it (`benchmark_subjects.py:226`), but `read_base` does not |

Four of seven items are missing or degraded. Three of the four —
`leaf_node_locations`, `scale`, `hull_coverage` — are precisely the inputs a
packing diagram or a paper-allocation judgement needs. **The agent-facing tool
is blind on exactly the axis Phases 2 and 3 exist to open.**

---

## Q2 — `path_drift_max` per subject, and did `[FIDELITY]` fire?

### Scorecard, this run (full serve path, `benchmark_subjects.py`)

| subject | R | served leaves | stub flaps | `rescue_stage` (markers) | `served_stage` (rung) | **`path_drift_max`** | hull cov | lint |
|---|---|---|---|---|---|---|---|---|
| quadruped | 6 | 7 | 3 | stub | stub | **0.0** | 0.7161 | MIXED |
| bird | 4 | 4 | 0 | none | none | **0.0** | 0.5000 | BENIGN |
| humanoid | 5 | 5 | 0 | none | none | **0.0** | 0.6319 | BENIGN |
| fish | 10 | 8 | 0 | placement | placement | **0.0** | 0.9077 | BENIGN |
| insect | 9 | 8 | 0 | order | order | **0.0** | 0.8595 | BENIGN |

`path_drift_max` is **0.0 on all five**. The two independently-sourced stage
columns agree on all five, which is the cross-check Task 10 built them for.

### `[FIDELITY]` verdicts

`fidelity_oracle.decide()` run on each subject's real `read_base()` payload:

| subject | fires? | reason |
|---|---|---|
| quadruped | **no** | `stage-stub` |
| bird | **no** | `no-drift` |
| humanoid | **no** | `no-drift` |
| fish | **no** | `no-drift` |
| insect | **no** | `no-drift` |

**`[FIDELITY]` fired on nothing.** Every stand-down is a *designed*
suppression, not an accident: quadruped is the stub serve the spec named in
advance ("Known in advance not to fire: quadruped serves `stage=stub`"), and
the other four are genuinely drift-free.

### How much this measurement can carry — the honest bound

**Three of five subjects exercised the rescue ladder** (quadruped → stub, fish
→ placement, insect → order); **two packed at attempt 0** (bird, humanoid) and
by construction can show no drift at all — `_record_serve(nodes, nodes, None)`
records the request as the serve, so `shadow_diff` compares a tree with itself.
Their `0.0` is a tautology, not evidence.

That leaves **three informative rows**, and all three land at 0.0 for a
structural reason worth stating: `order` and `placement` are in
`_STAGE_INTEGRITY` as proportion-preserving, and `stub` adds flaps *inside the
engine* where no Python node list sees them. So the three ladder stages that
actually fire on this corpus are exactly the three that **cannot** move a
leaf-to-leaf path length. The stages that *would* move it — `normalize` /
`contract_slivers` (bounded drift) and path reconciliation (unbounded by design)
— **did not fire on any scorecard subject in this run**.

Conclusion: this run is consistent with a correct metric and equally consistent
with a metric that returns 0.0 for everything. What rules the second out is not
this run but `test_shadow_diff_contraction_bounded` and
`test_shadow_diff_reconciled_pair`, which pin non-zero drift on fixtures that
production did not reach here. Read the scorecard column as a **tripwire that
has not yet been tripped**, which is the [ANATOMY] precedent the spec cites, and
not as a measurement of the ladder's fidelity.

---

## Q3 — Reading the packing diagrams IN ANGER

I rendered all five subjects from real `locs` and opened the PNGs. Impressions
below are from looking, not from the code; the arithmetic came afterwards, and
it is the arithmetic that changed my mind.

### First impression: four of five are unreadable, and the fifth is borderline

At the shipped call convention (`packing_diagram(locs, nodes, path)` — `scale`
defaults to `1.0`) the diagrams for **insect**, **humanoid**, **fish** and
**quadruped** are spirographs. Eight circles the size of the sheet, every one
overlapping every other, arcs crossing at a dozen points, labels landing on top
of arcs or off-canvas. I could not tell which disc was which limb. I could not
tell whether the design was crowded. The only thing I could read was "this is a
disaster" — and that reading is **false**.

`bird` (4 flaps) is the only one legible at the default, and only because four
circles cannot produce enough crossings to lose the eye.

### What was actually wrong: the radius is not the packer's

`tree_render.py:129`:

```python
r = (length / longest) * (box * 0.5) * float(scale)
```

Lang's invariant, which the docstring quotes two lines above, is that a flap of
tree-length ℓ owns a disc of paper radius **s·ℓ**, where s is the packing
scale. The shipped formula instead normalises the longest flap to **half the
square** and then multiplies by `scale`. In paper units it draws
`0.5·s·(ℓ/ℓ_max)`, which equals `s·ℓ` **only when `ℓ_max == 0.5`**. On this
corpus `ℓ_max` is 0.4 (quadruped, bird, fish), 0.3817 (humanoid), 0.3937
(insect) — so every disc is drawn 1.25×–1.31× too large *even if the caller
passes the correct `scale`*, and 1.67×–2.1× too large at the `scale=1.0`
default, which is the only value a caller can supply today because **`read_base()`
returns `scale: null`** (Q1).

I checked this against the packing constraint rather than trusting my eye.
Pairwise, in paper units, with the **true** radius `r = s·ℓ`:

| subject | packing scale s | tightest pair | slack (dist − r₁ − r₂) |
|---|---|---|---|
| quadruped | 0.5997 | 7 ↔ 10 | **+3.3e-10** (tangent) |
| bird | 1.0959 | 2 ↔ 4 | **−3.5e-12** (tangent) |
| humanoid | 0.7015 | 6 ↔ 7 | **−6.7e-10** (tangent) |
| insect | 0.5821 | 8 ↔ 11 | **−4.7e-14** (tangent) |
| fish | 0.6532 | 9 ↔ 3 | **+0.0680** (slack) |

**No pair of real discs overlaps anywhere.** Four of five packings are
tangency-tight to 1e-10 — textbook-clean circle packings. The overlap I read
off the image is entirely an artifact of the radius convention.

This is the single most important thing in this report about renders, and it is
a direct in-domain replication of the spec's own strongest cited finding
(§3.4: "render choice dominates prompt design"; splat renders made broken
meshes look clean). Here the render made a **clean** packing look broken. Same
mechanism, opposite sign, on our own artifact. Had this image been shown to an
agent under Phase 3, the correct behaviour would have been to report a serious
packing failure that does not exist.

### With the radius corrected, the diagram is genuinely good

Passing `scale = 2·ℓ_max·s` makes the shipped formula reduce to `s·ℓ` exactly,
so I re-rendered the same `locs` through the same unmodified function. The
difference is night and day, and it says something for the design that the
parameter *can* express the truth:

- **insect** (committed as evidence): eight tangent discs, all pushed to edges
  and corners, and a large clean **void in the centre of the square**. That
  reads instantly: every one of the eight legs is an edge flap, and the middle
  of the sheet holds no flap. Directly legible against CLAUDE.md §1.1 —
  and `hull_coverage` 0.8595 does not tell you *where* the uncovered paper is.
- **fish**: two interior discs (3, 12) and six on the boundary, with visible
  slack around 12 — the +0.068 pair. "This flap has room it isn't using" is a
  one-glance read.
- **quadruped**: 9 in the top-left corner, 11 large on the top edge, 8 and 7 on
  the side edges, 10 on the bottom, and 3 and 4 as the two interior discs. A
  quadruped with two middle flaps and five edge flaps, readable as such.
- **humanoid**: five discs, four boundary-centred, a lot of unclaimed centre.

So: **limb allocation IS legible — but only at the corrected radius, and only
if you already know which id is which limb.**

### The labels are node ids, and that is a real limit

Every disc is labelled with a bare integer (`tree_render.py:133`). "9", "11",
"5" carry no anatomy. `leaf_labels[nid]["label"]` already holds
`"left hind limb (pair 2)"`, `"likely head"`, `"mid-body appendage
(unclassified)"` — and `packing_diagram` does not take `leaf_labels` at all.
So the answer to "can you tell which disc is which limb" is, from the image
alone, **no**. You must cross-reference every id against the text table. The
picture is not self-sufficient; it is an index into the table.

### The engine-made discs are drawn at a fabricated radius, and nothing says so

`tree_render.py:128`: `length = lengths.get(nid, longest * 0.25)`. Engine-made
leaves arrive as `json_id == -1` and are, by `_leaf_lengths`' own docstring,
"not in `nodes`" — so **every stub disc is drawn at a made-up 25% of the
longest flap**. On quadruped this puts three identical red circles on the
sheet, and in the corrected render two of them sit **inside** black discs 3 and
4. Looking at it, I read "the engine's invented flaps are colliding with the
hind legs". That is not a fact about the design; it is the fallback constant.

The two honesty stamps do not cover this. `LAYOUT_STAMP` says "layout, not
survey"; `RIVER_NOTE` says rivers are not drawn. Neither says "the size of the
red circles is invented by the renderer". A stub's size is exactly the quantity
a reader would want (how much paper did the engine take for anatomy nobody
asked for?), and it is the one number on the image that is fiction.

### Does the missing-rivers limitation mislead in practice? — Mostly no, and `RIVER_NOTE` is doing real work

This one comes out **better** than the risk register (R9) feared, and I want to
be precise about where the line is.

The place rivers would have mattered most is exactly the insect's empty centre.
Without the note, "big void in the middle" reads as *wasted paper* — a design
flaw, and the kind of thing an agent would try to "fix" by lengthening flaps.
With the note ("this shows limb allocation, not the body segments between
limbs"), the correct reading is available: that void is where the thorax/abdomen
rivers live, and it is claimed paper, not waste. So the disclaimer converts a
wrong conclusion into a correct one on the single most tempting misreading in
the corpus. That is a disclaimer earning its place, not boilerplate.

Two residual complaints, both real but smaller:

1. **The note only says the rivers aren't drawn; it doesn't say the void is
   probably theirs.** A reader who has not internalised circle-river packing
   gets "some information is missing" rather than "that specific empty region is
   the missing information". One extra clause would close it.
2. **On fish the note is not sufficient**, because there the slack (+0.068
   between discs 3 and 9) is genuine slack in a packing that is *not*
   tangency-tight, and the diagram gives no way to distinguish "river lives
   here" from "the packer left it on the table". That distinction is the one an
   allocation judgement turns on, and v1 cannot make it. R9's mitigation holds
   for the *global* misreading and fails for the *local* one.

### Other things that made the images hard to read

- Labels sit at `(cx+3, cy+3)` — the disc **centre**. Boundary-centred discs
  (the majority: the packer parks leaves on edges and corners) therefore label
  half-off-canvas, and corner discs label into the frame line. On insect, "11"
  and "13" collide with the wrapped `RIVER_NOTE` text at the bottom margin.
- The three quadruped stubs are all labelled `"engine"`, identically. They are
  distinguishable by position and by nothing else — you cannot tell stub 1 from
  stub 3, or match one to the flap it repaired.
- Nothing on the image reports the packing scale, so two diagrams of the same
  subject at different scales are not comparable by eye and carry no number
  that would make them comparable.

### The tree sheet is a separate matter, and it is not good

`tree_sheet()` on quadruped (`measured=True`, all seven leaf positions real) is
four panels of unlabelled dots joined by dashed lines. No node ids, no
anatomical labels, and in the "top" view the whole skeleton collapses into a
horizontal smear. I could not identify head, tail, or any limb.

One structural finding worth recording, because it defeats the Task 9 fix on
its own terms: **every edge on every `measured=True` sheet is dashed, always.**
`edges` is built as `(parent_id, id)` (`tree_render.py:333`), a parent is by
definition an internal node, internal nodes are never in `measured_pos`, so
`a in guess_cue_ids` is `True` for every edge (`tree_render.py:361`). Verified
on a minimal 3-node tree: `unmeasured_node_ids == [0]`, both edges dashed. The
cue is therefore constant and carries zero bits — it cannot distinguish a
well-measured sheet from a fully-guessed one. `unmeasured_node_ids` in the
returned dict is still informative; the pixel cue is not.

---

## Q4 — Does the leaf-`position` text table already answer the recognisability question?

### Answer: **Yes for recognisability. The tree sheet is redundant. The packing diagram answers a different question — and mostly loses to arithmetic on that one too.**

The two artifacts do not measure the same thing, and conflating them is how
this question gets answered wrongly in either direction:

| | leaf-`position` table (Task 7) | packing diagram |
|---|---|---|
| Frame | **mesh space**, source mesh's arbitrary scale (labelled as such since `338e60b`) | **paper space**, unit square |
| Answers | *does the tree read as the subject* | *where did the paper go* |
| Carries | label, basis, 3-D position | id, x, y, radius |

### Recognisability — the table wins outright

Here is the quadruped table as an agent receives it from
`mesh_report._anatomy_lines`, with the long `basis` string elided from each
line:

```
node 3  -> right hind limb (pair 2)   at mesh-space [5.0026, -0.4909, 94.0038]
node 4  -> left hind limb (pair 2)    at mesh-space [14.939, -0.4381, 91.3751]
node 7  -> left fore limb (pair 1)    at mesh-space [16.4291, -0.5006, 47.4294]
node 8  -> likely tail                at mesh-space [7.324, 44.2655, 125.7358]
node 9  -> mid-body appendage (uncl.) at mesh-space [19.2511, 64.7534, 115.0051]
node 10 -> right fore limb (pair 1)   at mesh-space [2.9975, -0.5058, 46.4996]
node 11 -> likely head                at mesh-space [9.4, 14.4008, 0.2999]
```

Reading that cold I get: four limbs in two mirrored pairs; fore pair at z≈47,
hind pair at z≈91-94, head at z≈0.3, tail at z≈126 — a clean, monotone
anterior-posterior ordering along z, with the pairs straddling the axis in x
(≈3 vs ≈16, ≈5 vs ≈15). Plus one unclassified appendage at (19.3, 64.8, 115.0):
high in y, near the tail end — something sticking **up** at the back. That is a
recognisable quadruped, plus one extra flap, and I got it from seven lines of
text with no image.

The `tree_sheet` renders **exactly these coordinates** and tells me less: no
labels, no ids, everything dashed, panels that smear. On this corpus the picture
is a strictly lossy rendering of the table.

**Verdict for §3.5 precondition 2: the text table answers the recognisability
question. Per the spec's own rule, the picture is redundant for it — stop.**

### Paper allocation — the picture's only real claim, and it is weaker than it looks

The honest case *for* the diagram is that clause 4 (paper allocation) is
paper-space, so the mesh-space table says nothing about it, and no shipped
scalar is per-limb (`hull_coverage` is global: dog 0.664, quad 0.496). The
insect void is genuinely something I saw in a picture and could not have read
off `hull_coverage = 0.8595`.

But four things cut against it, and together they are decisive:

1. **The diagram's own data is already a table.** Its whole input is
   `(id, x, y)` plus a radius derivable as `s·ℓ`. A ten-line text table of
   `id, label, x, y, r` carries every bit the image carries, *plus* the
   anatomical labels the image omits. There is no information in the render
   that is not in that table; there is information in that table that is not in
   the render.
2. **The derived relations are cheap arithmetic and the eye is worse at them.**
   "Which discs are tight" is `n(n−1)/2` subtractions — 28 for insect. I ran it,
   and it was the arithmetic that told me the packings were tangent while the
   picture told me they were catastrophically overlapping. On the one question
   the diagram is supposed to own — crowding — **the image and the numbers
   disagreed and the numbers were right.** That is not a hypothetical about
   VLM reliability; it happened to me in this session, on this corpus.
3. **The one genuinely perceptual read — "where is the void" — is a
   two-dimensional coverage question that has a deterministic answer.** A
   largest-empty-circle or per-cell occupancy computation over the same `locs`
   returns "unclaimed region centred at (0.5, 0.5), radius 0.21" as a number,
   for far less than the cost of an image channel. And it would be an
   *acceptor*, which §3.1 says is the only thing allowed to decide anything —
   whereas a VLM impression is not.
4. **There is no input.** Per Q1, `locs` and `scale` do not reach `read_base()`.
   Phase 3 would have to build the same plumbing Phase 2's STOP IF names,
   *and* fix the radius convention, before there is a picture to look at.

### What the picture would carry that no table can — stated fairly

To be even-handed, one thing survives: **gestalt over ~8 discs.** "All eight
flaps are on the boundary and the middle is empty" is a single perceptual act
that, from a table, requires knowing to ask. A model reading a table will answer
questions it thinks to ask; a model reading a picture may notice something it
was not looking for. That is a real asymmetry and it is the only honest argument
for the render.

It is not enough here, because (a) the spec's own cited evidence says
unsupervised self-inspection scores **negative** without a deterministic
acceptor, and the acceptor for this axis does not exist yet, and (b) the noticing
this diagram actually produced in this session was **wrong** (false overlap) and
the arithmetic corrected it.

---

## Phase 3's two preconditions (spec §3.5)

> **1.** "Verify the Anthropic OpenAI-compat endpoint accepts `image_url`
> content-parts (`llm_client.py:33-37`). Untested. Blocks everything here."

**Does not pass — still untested, and the code to test it does not exist.**
`grep -rn "image_url"` over `llm_client.py`, `agent_loop.py` and `web/server.py`
returns nothing: no content-part message is constructed anywhere. The synthetic
channel Phase 3 would use appends a **plain string** content
(`web/server.py:645`, `messages.append({"role": "user", "content": text})`), and
the tool channel is a plain string by construction (`agent_loop.py:815-817`), which
the spec already identifies as the blocked route. I deliberately did **not**
make a live paid API call to probe the endpoint: it is an external
side-effecting request nobody asked for, and its outcome cannot change this
report's recommendation, which turns on precondition 2 and on Q1. Recorded as
**unverified**, exactly as the spec left it.

> **2.** "Run the Gate-2 experiment: does the labelled leaf-`position` text
> table answer the recognisability question? If yes, the picture is redundant —
> stop."

**Does not pass — because the experiment came back YES.** Q4 above is the
Gate-2 run: the table answers it, and on the same coordinates the rendered sheet
answers it worse. By the spec's own wording this is the STOP branch.

Both preconditions therefore fail, one on the merits and one for want of a
built channel. Spec §4's Phase 3 STOP IF is satisfied twice over (image
content-parts unproven; text table already sufficient), before the
arithmetic-invisible control is even attempted — and note that R12 already
pre-registered "no qualifying clear-gap pair exists" as evidence *against*
Phase 3, and the `path_drift_max == 0.0` column plus per-subject differing
`hull_coverage` gives no obvious candidate pair.

---

## Recommendation

**Do not plan Phase 3.** Three independent grounds, any one of which suffices:

1. **Phase 2's STOP IF is UNMET.** The diagram's input does not exist on the
   serve path. Phase 3 is specified to be planned "only after Phase 2 reports and
   both preconditions pass" (§4, Scope control).
2. **Gate-2 returned YES.** The text table answers recognisability; the spec
   says stop.
3. **The image channel is unbuilt and unproven.**

**What to do instead, in priority order.** These are Phase-2 repairs, not Phase 3:

1. **Fix the disc radius convention** in `packing_diagram` — draw `s·ℓ`, not
   `0.5·s·ℓ/ℓ_max`. It is a one-line change and it converts a misleading image
   into a truthful one. Until then the renderer should not be shown to anyone,
   agent or human, at its default parameters. (No committed golden is affected:
   nothing calls it in production.)
2. **Stop fabricating the engine-made disc radius**, or stamp it. Drawing a
   guessed size for invented anatomy, in the same image whose two stamps are
   about honesty, is the sharpest inconsistency found here.
3. **Carry `locs` and `scale` on the parent path** — the STOP IF's actual
   content. This needs `_worker_full_base` to return a payload rather than a
   bare fold string, then the two `_record_serve` call sites. It also unblocks
   `hull_coverage` and the `leaf_node_locations` table in `read_base()`, which
   is where §3.3.3's remaining gaps live.
4. **Label discs with `leaf_labels[nid]["label"]`**, not bare ids. Without this
   the image cannot answer "which disc is which limb" at all.
5. **If paper allocation is worth acting on, build the deterministic
   instrument, not the picture** — largest-empty-region and per-disc tangency
   slack over `locs`. That is an acceptor under §3.1; a render is not. If it
   later turns out that instrument misses something a human sees in the
   diagram, *that* is the evidence that would reopen Phase 3, and it would be
   evidence rather than an expectation.

**What Phases 1-2 did deliver, and it is not nothing:** `shadow_diff` on the
key that survives re-rooting, a read-only `read_base()` that cannot report a
stale record from any of three routes, a `[FIDELITY]` oracle that is correctly
silent on all five subjects for five *named* reasons, two new scorecard columns
that cross-check each other, and leaf positions in the reference report — which
is the artifact that just made Phase 3 unnecessary. The tripwires are in place
and none of them has been tripped. That is the honest state.

---

## Artifacts

- `docs/superpowers/evidence/2026-08-04-packing-diagrams/insect-packing-default-scale1.png`
  — the shipped default. Eight overlapping circles; unreadable.
- `docs/superpowers/evidence/2026-08-04-packing-diagrams/insect-packing-true-disc-radius.png`
  — identical `locs`, identical function, `scale = 2·ℓ_max·s`. Eight tangent
  discs on the boundary and a clean central void. Same data, opposite conclusion.

Probes are scratch-only and not committed (`probe_render.py`,
`probe_truescale.py`, `probe_serve_readbase.py`, `probe_readbase.py`); each is
reproducible from the descriptions above, and each keeps every compile under
`if __name__ == "__main__":`.

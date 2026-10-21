# Design: LLM-guided extraction (A′) — the LLM specifies, the search optimises

**Status:** design, pre-implementation. Nothing here has been built.
**Supersedes nothing.** Every component is additive and every one of them is
inert when its flag is off or its credential is missing.

**Origin.** A read of *COrigami: An AI Pipeline for Co-Designing Flat-Foldable
Visually Recognisable Origami* (arXiv:2606.26299v1, Google DeepMind, Jan 2026)
against our own `mesh → tree` pipeline, followed by a reachability measurement
over `fixtures/extraction_fate.json`. The conversation that produced it also
corrected two claims the first draft of this design made; both corrections are
recorded in §1.3 rather than quietly fixed, because both were wrong in the
direction that would have made the design smaller.

---

## 1. Why this, and why now

### 1.1 The measured problem

`fixtures/extraction_fate.json` sweeps **8 voxel resolutions × 8 prune
fractions × 8 subjects** (512 extraction cells, `probe_extraction_fate.py`,
git 6a2d32a). Cross-referencing its `leaf_by_prune` curves against the
human-authored ground truth in `fixtures/anatomy_expectation.json` answers the
only question that matters before building anything: **is the correct anatomy
reachable by steering the knobs the extractor already has?**

| subject | true count | cells hitting it (of 64) | inside shipped grid `[96,64,128]` | class |
|---|---|---|---|---|
| humanoid | 5 | 42 | 20 | already found |
| quadruped | 6 | 17 | 4 | already found |
| bird | 6 | **1** — only (192, 0.40) | **0** | **1 — grid coverage** |
| octopus | 9 | 5, incl. (64, 0.40) and (64, 0.45) | 2 | **2 — window clamp** |
| water bear | 9 | 4, all at voxel 64 | 4 | **2 — window clamp** |
| lizard | 6 | **0** | **0** | **3 — unreachable** |

Three failure classes, three different answers:

* **Class 1 — grid coverage.** A bird's six flaps exist in the reachable set at
  voxel 192 / prune 0.40. `_VOXEL_GRID_DEFAULT` is `[96, 64, 128]`. We have
  never looked there. **Steering fixes this.**
* **Class 2 — window clamp.** Nine leaves are already produced at voxel 64,
  inside the shipped grid, at four separate prune values for the water bear.
  `structural_prefilter` rejects them because `MAX_LEAVES = 8`. **Steering
  cannot fix this**; it is a constant and a packer-capacity question.
* **Class 3 — unreachable.** Six leaves never appear for the lizard in any of
  its 64 cells. **Only a different producer helps.**

> ## ⛔ CLASS 3 IS EMPTY. CORRECTED 2026-09-03.
>
> **"Six leaves never appear for the lizard in any of its 64 cells" is FALSE**,
> and it was refuted on the very mesh the fixture records (sha256
> `6d1edc99…`, byte-identical to its own record). The instrument was validated
> first — **0 diffs across all 64 lizard and all 64 bird cells at default
> flags** — so every difference below is the arm, not the method.
>
> | arm | 6-leaf cells of 64 | production serve, shipped grid, authored R=6 |
> |---|---|---|
> | default flags | **0** — the fixture reproduces exactly | 5 leaves, 1 pair |
> | **`IDE_FREEZE_PRUNE_CUTOFF=1`** | 2 | **6 leaves, 0 stubs, confirmed, fid 1.0** |
> | `IDE_KEEP_COMPONENTS=1` | 3 | **6 leaves, 0 stubs, confirmed, fid 1.0** |
>
> Production `label_leaves` on that serve reads *right/left hind limb (pair 1),
> right/left hind limb (pair 2), likely tail, likely head* — four legs, head,
> tail. The lizard's authored anatomy, **from the mesh, with no LLM involved.**
>
> **Why the fixture went stale.** `extraction_fate.json` was generated at git
> `6a2d32a` (2026-08-21). **25 commits have touched `mesh_to_tree.py` since**,
> including the B2 component stitch, and the mesh provider was swapped on
> 2026-08-24. It describes a pipeline that no longer exists.
>
> **The guard could never have caught it.**
> `tests/test_reachable_cells.py`'s `test_lizard_is_unreachable_anywhere_in_the_grid`
> read the frozen fixture. Its docstring said *"if this ever passes with a
> non-empty list, the spec's Class 3 claim is void"* — **it could not.** The
> claim and its guard were the same artifact. Renamed to
> `test_the_FIXTURE_records_zero_lizard_hits`, with the caveat pinned by a
> second test.
>
> **This section also contradicted itself.** §1.2 names `IDE_KEEP_COMPONENTS`
> as available steering headroom, while this table declares the lizard
> unreachable *by steering* — from a measurement taken with that exact knob
> **off**.
>
> **Class 1 moves too:** the bird reads 1 hit at default (as recorded, outside
> the grid) and **5 hits under the freeze, 2 of them inside the shipped grid**.
> "We have never looked there" is answered without widening the grid.
>
> **So the sentence below is wrong as written.** The table's negatives are
> conclusive **only conditional on the flag state, the code revision and the
> mesh provider that produced the fixture** — all three of which have moved.
> Every impossibility claim in this table needs that qualifier.

⚠ **THE TABLE'S NEGATIVES ARE CONCLUSIVE AND ITS POSITIVES ARE OPTIMISTIC, AND
THE ASYMMETRY IS LOAD-BEARING.** Leaf count is necessary, not sufficient — the
repo's own record has a lizard whose anatomy was correct at *four* leaves and a
horse that served 8 leaves with 0 pairs and 6 unclassified limbs. A count
*miss* proves the anatomy wrong; a count *hit* proves nothing. So "lizard: 0 of
64" is an impossibility proof, while "bird: 1 of 64" is an upper bound. The
fixture's own `_meta` adds the second caveat: *"Extraction only — NO compile
was run. A cell recorded here is not thereby packable or servable."* M1 (§5)
exists to close exactly that gap before anything is built on it.

### 1.2 The steering headroom

The shipped grid covers **24 of 64 cells (37.5%)**. The search terminates early
on `fid >= 1.0 and stage == "none"`, and `configured_voxel_grid`'s docstring
records that the flag-off octopus trace "contains voxel 96 and nothing else" —
so on the subject that most needs exploration the extractor examines **8 of 64
cells (12.5%) and stops.**

The knobs exist (`IDE_VOXEL_GRID`, `IDE_KEEP_COMPONENTS`, `IDE_R_PREPASS`,
`IDE_EXTERNAL_R`, `IDE_ADMIT_WIDE`) but are **process-global environment
variables**, not per-subject decisions. That is the gap this design closes.

### 1.3 Two corrections this design is built on

Both were errors in the first draft of the approach, both found by the user,
and both recorded because each was wrong in the direction that shrinks the work.

**(a) "COrigami's angles drive a shaping stage we don't have" — FALSE.** We
have ≈2,100 lines of shaping: `shaping.py`, `shaping_deep.py`, `pose_target.py`,
`pose_search.py`, `pose_base.py`, `pose_coupling.py`, `pose_pregate.py`, plus
the shipped `apply_shaping_ops` and `suggest_pose_stack` MCP tools.

**(b) "Angles are a shaping concern" — TOO NARROW.** Angles are already
load-bearing in three places, only one of which is shaping. See §2.

### 1.4 The rule the prior art imposes

A budget-matched study of LLM-driven hyperparameter optimisation
([arXiv:2606.21641](https://arxiv.org/html/2606.21641v1)) found the apparent
advantage of an LLM advisor came from **the default it was warm-started with,
not the model**: +0.40pp CV accuracy, **−0.01pp held-out test (p=0.92)**;
classical random search on the same default caught up within 5 evaluations and
led by 0.37pp at 12. Its one exception (`vehicle`, where classical search found
configurations 66–99pp better while the LLM sat at the default) is an
**exploration failure** — precisely what we would invite by letting a model
pick voxel numbers.

Our setting differs in one respect that decides the design: the LLM knows *an
octopus has eight arms*, which the extractor cannot derive from anything it
has. That is semantic information, not a knob value. Hence the binding rule of
this whole spec:

> **The LLM supplies the objective and the constraints. Deterministic search
> supplies the knob values. No LLM output is ever a voxel resolution, a prune
> fraction, or any other numeric search parameter.**

---

## 2. The angle finding, stated once

Three independent sites are already reaching for per-node orientation and not
finding it. This is the evidence for the `orientations` side channel (U1).

**(a) We compute it and discard it.** `extract_skeleton` puts a 3-D `pos` on
every skeleton node (`mesh_to_tree.py:744`); `detect_symmetry` and
`label_leaves` both read it; `to_metric_tree` emits `{id, parent_id, length}`
and **never reads `pos` at all**. The only survivor is
`leaf_labels[id]["position"]` — leaf tips only, so bone *vectors* are not
reconstructable from a served result even though all of them were computed.

**(b) The packer already consumes an angle per node, and it is meaningless.**
`TreemakerWrapper.cpp:254`:

```cpp
double a = 2.39996 * double(order);            // golden-angle spread
```

Every unseeded node is placed on a golden-angle spiral at **137.5° × its index
in the node list**. That is the mechanism behind the largest measured win in
this project — node ORDER moves `bird` hull coverage **0.5000 → 0.9848** —
which means the ladder's `order` stage and its four random topological restarts
are **a blind search over arbitrary angular assignments**. And
`rescue_ladder.structural_layout` is a hand-written *guess* at the anatomical
arrangement (root-children alternate ± along the 45° diagonal, paired leaves at
± the perpendicular, unpaired siblings staggered by index parity) — measured to
pack the raw 6-leaf dog at voxel 96, which is the measurement that bought the
placement stage. **We wrote a fake angle field because we did not carry a real
one.**

**(c) The judge has the field and cannot fill it.** `vlm_judge.py:708-726`
states it directly: our tree "carries no angle at any stage" and
`tree_contract.py` "does not contain the word 'angle'". `build_payload` emits
`azimuth_angle`/`elevation_angle` opportunistically and carries an
`angle_coverage` block whose job is to confess how many sticks got one. Because
internal joints have no measured position, the reported values **are not stick
directions** — they are each flap tip's direction from the figure's centre.
This lands on `semantic_recognisability`, the criterion the corigami-2 work
flagged as the live lead, and it is the criterion that most needs arrangement.

**(d) Shaping needs it and only the mesh arm can supply it.**
`pose_target.bone_vectors(tree)` requires nodes carrying `pos`. Under a
no-angles schema an LLM-authored tree is structurally excluded from posing.
⚠ Angles do **not** unblock shaping — B5 was capped as a research negative and
the recorded blocker was cross-coupling / anti-additivity between ops, not a
missing target. They remove a blocker for the *LLM arm* only.

---

## 3. Scope

**In scope.** Three measurement units; an optional `orientations` side channel
with a mesh derivation and a packer consumer; two LLM *specification* tools; one
deterministic targeted search; one LLM *producer*; one VLM *critic*; and the
integration that unions producers into the existing candidate pool.

**Out of scope, with reasons.**

| Excluded | Reason |
|---|---|
| Replacing TreeMaker with a discrete box-pleating packer | COrigami Table 3 measures fully-automated TreeMaker at **1.1% on 66,036 stick figures** and names the four bypassed manual steps — symmetry pairing, stub fracturing, forcing leaves to paper edges, node repositioning — **all four of which this repo has built**. Their number is un-rescued TreeMaker. A packer comparison is its own spec with its own measurement. |
| COrigami's shaping stage and RL loop | Downstream of the tree. |
| Learned riggers (RigAnything, UniRig, MagicArticulate, Anymate) | Genuinely promising — RigAnything emits joints in **BFS order as positions + parent indices**, field-for-field our Metric Tree — but release, licence and local runnability are all **unverified**. Building on it now is exactly what CLAUDE.md §0 forbids. Queued as the next prior-art experiment behind a flag, with a bake-off against `skeletor`. |
| Raising `MAX_LEAVES` | Class 2's fix, and it is a **policy decision that M2 must inform first**. `fidelity_score`'s clamp drives the terminal early-exit, not just ranking, so moving it re-times the search on fish and insect as a side effect. |
| Adding `hull_coverage` to the ranking key | CLAUDE.md is explicit: it is deliberately not a key (`order_rank.py:143`), coverage is a reported consequence and never buys a scale loss. Untouched. |

---

## 4. Prior art (CLAUDE.md §0)

| Adaptation | Source | Lands in |
|---|---|---|
| LLM-authored semantic stick figure: named joints, declared symmetry, per-stick azimuth/elevation, acyclic by construction | COrigami §3.1 + Appendix C.1 (arXiv:2606.26299v1) | U1 schema, U5 producer |
| Hierarchical prompting with explicit negative constraints for subject admissibility | COrigami Appendix C.1 category/object prompts | U2 |
| VLM refinement over multi-view renders with named repair instructions (adjust lengths, correct joint angles, enforce mirrored angles, add/remove nodes) | COrigami §3.1 | U7 |
| **Rejected:** tree-similarity as a fidelity oracle | COrigami Appendix C.2 — it Procrustes-matches the fold against *the stick figure that generated it*. A wrong figure faithfully folded scores 1.0. Identical closed loop to our retired `reference_feature_count`; `anatomy_expectation.py` already exists to break it. |
| **Rejected:** LLM proposing search hyperparameters | Budget-matched HPO study (arXiv:2606.21641): +0.40pp CV, −0.01pp test (p=0.92); classical search seeded with a good default wins by 12 evaluations. Directly motivates §1.4's binding rule. |
| Oracle must be independent of the generator | RTLFixer (arXiv:2311.16543), CADSmith (arXiv:2603.26512), ICLR'24 self-repair — already the stated basis of `anatomy_expectation.py` | U2 extends that table rather than replacing it |
| LLM decomposes a prompt into a hierarchy of parts/links/joints before geometry exists | LAM, CVPR 2026; ArtLLM (arXiv:2603.01142) | U5 — confirms COrigami's move is an established pattern, not a one-off |
| Breadth-over-depth: many diverse candidates, shallow repair | ICLR'24 "Is Self-Repair a Silver Bullet?" — already the ladder's policy | U5 samples K trees rather than iterating one |
| Side-channel discipline for engine-visible seeds | This repo, `rescue_ladder` Rule 2 | U1's central constraint |
| **Rejected:** a single global camera/framing suffix | ⚠ **This repo's own measurement**, commit `85967c1` (2026-08-25), *"the camera fix is refuted"*; `probe_mesh_bakeoff.py:236` — *"GATE CLOSED 2026-08-25, AND THE ANSWER IS NO — NOT GLOBALLY."* `CAMERA_SUFFIX_CANDIDATE` rescued the horse and regressed the octopus. | U3 is rescoped to **per-subject** framing and must clear the same bar the global change failed |
| Fixed compositional suffix applied outside the provider | This repo, `IMAGE_PROMPT_SUFFIX` (`probe_mesh_bakeoff.py:313-317`, margin clause added `c27f81e`) — what shipped *instead of* the camera fix | U3's control arm: the thing per-subject framing must beat |

---

## 5. Component M1 — does the bird's cell actually compile?

**Question.** `extraction_fate` records extraction only. Class 1's entire value
rests on one cell, (voxel 192, prune 0.40), producing a bird tree that *packs*.

**Method.** A probe (`probe_reachable_cells.py`) that, for each (subject, cell)
in the reachability table's hit list, runs the production emitter and then
`server.draft_and_compile_full_base` under `root_rank_suppressed()` and
`mv_symmetrize_suppressed()` — i.e. exactly `mesh_to_tree._default_compile_fn`,
so the answer is about the serve path and not about a bare compile. Records
per cell: `leaves`, `pairs`, `compiled`, `stage`, `stub_flaps`, `design_scale`,
`hull_coverage`, `lint_class`.

**Output.** `fixtures/reachable_cell_compiles.json`.

**Decision it gates.** If the bird's single cell does not compile, Class 1 is
cosmetic for the bird and U4's widened sweep must be justified on other
subjects or dropped. **Pre-registered:** U4 ships only if ≥1 Class-1 cell
compiles on ≥1 subject with `stub_flaps == 0`.

## 6. Component M2 — do 9-flap trees pack at all?

**Question.** Class 2 (octopus, water bear) is worth nothing if the engine
cannot pack 9 flaps, and everything if it can.

**Method.** Two arms, both offline. (a) Re-read
`fixtures/s5_engine_repair_evidence.json → packability_control`, which already
holds k-leaf star pack rates (k=8: 3/3 at 0% jitter, 7/20 at 30%) — extend the
same control to k=9..12. (b) Compile the actual 9-leaf octopus and water-bear
trees from M1's cell list through the full ladder, recording which rung, if
any, rescues them.

**Output.** `fixtures/wide_window_packability.json`.

**Decision it gates.** Whether `MAX_LEAVES`, `ADMIT_MAX_LEAVES` and
`_phase4_admitted_serve`'s displacement ban are revisited **in a separate
spec**. ⚠ This unit MEASURES; it changes no constant. Loosening a gate to reach
a headline is this project's named recurring failure mode.

## 7. Component M3 — do real orientations beat golden-angle-by-index?

**Question.** §2(b)'s claim is a mechanism, not a result. Nobody has compared a
placement seed derived from real anatomy against the ladder's index-parity
guess.

**Method.** On the five committed fixtures plus the octopus and lizard, at each
cell that emits a servable tree: derive orientations from the skeleton (U1's
derivation), build placement seeds from them (U6), and compare against three
controls on the same trees — (i) attempt-0 unseeded, (ii) the `order` stage's
four restarts, (iii) `structural_layout` as it ships. Report pack rate,
`design_scale`, `hull_coverage`, `stub_flaps`, `lint_class`, rung reached.

**Output.** `fixtures/orientation_placement_ab.json`.

**Decision it gates.** U6 ships only if orientation-derived seeds are
**non-inferior** to `structural_layout` on `stub_flaps` and `design_scale`
across the whole fixture set, and strictly better on ≥1 subject.
⚠ The trade must be argued per CLAUDE.md §1.1 item 4: a coverage gain bought
with a scale loss is a trade to state, never a free win.

---

## 8. Component U1 — the `orientations` side channel

```python
tree_nodes      = [{"id": 3, "parent_id": 1, "length": 0.31}, ...]   # UNCHANGED
symmetric_pairs = [[3, 4], ...]                                      # UNCHANGED
orientations    = {3: {"azimuth": 90.0, "elevation": -90.0}, ...}    # NEW, optional
```

**⚠ NOT A NODE FIELD, AND THE REASON IS MEASURED.** The C++ wrapper reads nodes
via `.contains()` for exactly `id`, `parent_id`, `length` and optional `x`/`y`,
so an extra key could not break a compile. The Python side is where the blast
radius is:

* `json.dumps(entry[1], sort_keys=True)` is the candidate dedup key
  (`mesh_to_tree.py:2970`) — extra keys silently defeat deduplication;
* `json.dumps(nodes)` is the capture-corpus and serve record
  (`server.py:2683`, `:4281`) — the training corpus would change shape;
* `rescue_ladder` **Rule 2** already legislates this exact hazard for placement
  seeds: *"placement seeds NEVER ride in the node dicts that reach attempt-0"*,
  with `has_placement_seed` as the tripwire.

So the repo has solved this once and this follows it verbatim.

**Two producers, one shape.**

* **Derived** (mesh path). `to_metric_tree` gains an optional **keyword-only**
  `frame=` argument and publishes the result on a module global,
  `_last_orientations`, computed from the skeleton `pos` it already holds — for
  every node, not just leaves, which is what fixes `vlm_judge`'s "these are not
  stick directions" caveat. Frame: the same PCA construction `label_leaves`
  uses (`_mesh_pca` + the winning mirror normal), so mesh angles and mesh
  labels agree by construction.

  ⚠ **NOT A THIRD RETURN VALUE, AND THE COUNT IS THE REASON.** An earlier
  revision of this section said "gains an optional third return value". There
  are **35 call sites** that unpack exactly two (`nodes, pairs =
  to_metric_tree(...)`), across production, probes and six test files, so a
  third value breaks every one of them. `mesh_to_tree.py` already carries this
  exact pattern twice — `_last_pair_evidence` and `_last_pre_root_children` —
  and the module-global side channel is what those exist to demonstrate. A
  keyword-only argument with a `None` default is likewise invisible to all 35.

* **Angle convention: PINNED, NOT REINVENTED.** `vlm_judge._angles` already
  defines it — azimuth `degrees(atan2(v·lateral, v·axial))`, elevation
  `degrees(asin(v·dorsal / |v|))`, both to 1 d.p. — and U1 must agree with it
  bit for bit or the judge payload and the side channel will report two
  different numbers for one stick. P1 does **not** edit `vlm_judge`; it pins
  the two with an equality test over a fixed vector set, the same discipline
  `_PROVENANCE_CAVEAT`/`_R_SOURCE` and `test_hub_degree_notice_matches_the_extractor`
  already use.

  The one deliberate difference is the **vector**, not the maths: `vlm_judge`
  measures each flap tip from the tip centroid because internal joints have no
  measured position on the serve path. U1 runs at extraction time where every
  node has one, so it measures the **stick itself** (`pos[child] −
  pos[parent]`). That difference is the point of the channel.
* **Declared** (LLM path). U5 emits them directly, COrigami-style.

**Invariants.**

1. `orientations=None` → every consumer behaves byte-identically to today.
   Pinned by test on all five committed fixtures.
2. Frames are never mixed. A record carries `"space": "mesh"` or `"paper"`,
   never both — `vlm_judge:1139` already enforces this rule for its own payload
   and the same reasoning applies here.
3. Angles are **advisory input to seeds and reports only**. Nothing in
   `_serve_rank`, `order_rank.rank_key`, any budget, or any exit condition may
   read them. A fifth ranking key is pinned shut by existing tests and this
   does not open one.

## 9. Component U2 — `anatomy_spec(prompt)`

An LLM tool that returns the same shape `fixtures/anatomy_expectation.json`
holds. It **extends** the authored table from a fixed list to any prompt, and
feeds the **already-plumbed** `reference_count=` keyword argument on
`auto_mesh_to_metric_tree` (`mesh_to_tree.py:2710-2713`, keyword-only, default
`None`) — the seam C1 built and Z1 turned on by default.

⚠ **AMENDED 2026-09-02 after reading the code. Three of this section's original
claims were false, and one of them ships a defect that reads green.**

**The row shape is THREE fields, not five.** Every one of the 14 authored rows
is exactly `{expected_feature_count, derivation, citation}`, pinned by
`tests/test_anatomy_expectation.py:129-143`. `named_parts` has **zero
occurrences anywhere in `mcp_harness`**. `expected_pairs` exists only in
`fixtures/anatomy_reference.json`, whose own `_meta.status` reads
*"extraction-derived, NOT ground truth"* and which is frozen.

> **Consequence, and it is load-bearing for U4.** §11 ranks cells "on both
> count and pair count", but the authored path — the path this section's
> contract *prefers* — supplies **no pair target at all**. Sourcing pairs from
> `anatomy_reference.json` would re-enter, through the back door, the closed
> loop this whole design exists to escape. **U4's pair axis is therefore
> INACTIVE on table hits**, and must be documented as such rather than
> silently ranked on a missing key. Extending the authored rows with a pair
> count is a fixture migration that U2 does **not** scope here.

**Contract.**
* Table hit → authored row wins, **model never consulted.** The hand-authored
  rows are stronger evidence and cheaper.
* Table miss + model available → model row, cached to disk, stamped
  `r_provenance: "llm"`.
* Table miss + no model → `None`, byte-identical to today.
* The model is asked for a derivation and a citation, and a row without both is
  **discarded**, not downgraded. The value of that file is that every number is
  auditable without rerunning anything.

### 9a. Two defects U2 must fix before it can stamp anything

Neither was visible from the spec; both were found by executing the change.

**(1) The stated mitigation is insufficient and FAILS GREEN.** This section
originally said `mesh_report._PROVENANCE_CAVEAT` and `_R_SOURCE` "must both
gain the key". They must — the import assert at `mesh_report.py:224` enforces
it — but that is **not sufficient**. `_provenance_lines` (`mesh_report.py:249`)
does not dispatch through the dict; it is a **hardcoded tuple**:

```python
if prov in ("external", "max-over-voxels"): return [_PROVENANCE_CAVEAT[prov]]
return [_PROVENANCE_CAVEAT["self-derived"]]
```

So `"llm"` falls to the else-arm. Measured by making exactly the change this
section originally prescribed — **the import assert passes** — and
`format_reference_report` then emits, adjacently:

```
reference feature count (language-model anatomy row): 9
⚠ R IS NOT GROUND TRUTH -- IT WAS VOTED OVER THIS RUN'S OWN EXTRACTION.
```

That is verbatim the self-contradiction the caveat/source pair exists to
remove, reintroduced under the new key with every guard green. **U2 must fix
the dispatch** (make it dict-driven, or `set(_PROVENANCE_CAVEAT) -
{"self-derived"}`) **and strengthen the assert to cover it**, or stamping
`"llm"` is worse than not stamping at all.

Note also that this section's original description of the failure mode — "a
caveat added to one alone prints a plateau label above a contradicting caveat"
— describes the **pre-assert** hazard. With the assert in place that case
raises at import; it does not print.

**(2) There is no provenance parameter in extraction.** `mesh_to_tree.py:3048-3051`
stamps `"external"` **unconditionally** on `reference_count is not None` — the
sole signal is `None`-vs-not-`None`. And `_R_SOURCE["external"]`
(`mesh_report.py:211`) renders that as **"human-authored anatomy table."**

> So an LLM-written R handed to today's seam **is laundered as human-authored
> ground truth.** U2 must widen the seam to carry provenance alongside the
> count before any model row reaches it. This is a prerequisite, not a
> nice-to-have.

`"llm"` is the **fourth** key in the report dicts (`self-derived`, `external`,
`max-over-voxels`) though only the third ever *produced* — `max-over-voxels` is
deliberately never written, asserted by `tests/test_r_prepass.py:904-920`.

## 10. Component U3 — `frame_concept(prompt, spec)`

An LLM tool that writes the **concept-image prompt**, including an explicit
camera.

⚠ **RESCOPED 2026-09-02. This section originally called framing "the
highest-value measured lever in the whole design". A global framing change was
MEASURED AND REFUTED on 2026-08-25, and this section cited neither the
refutation nor the replacement that shipped instead.**

**The refutation.** Commit `85967c1` is titled *"measure: a horse replaces the
water bear, and the camera fix is refuted"*, and `probe_mesh_bakeoff.py:236`
carries the ruling: **"⚠ GATE CLOSED 2026-08-25, AND THE ANSWER IS NO — NOT
GLOBALLY."** `CAMERA_SUFFIX_CANDIDATE` rescued the horse (18L/6P → 9L/2P
servable) and **regressed the octopus**. What shipped instead was
`IMAGE_PROMPT_SUFFIX` (`probe_mesh_bakeoff.py:313-317`) — a fixed suffix
applied **outside** the provider, and living in a **probe**, not on the serve
path. The live path (`server.py:4140`) still calls `acquire_mesh` with the
**raw** prompt.

**The headline A/B was measured against a superseded default.**
`compare_extraction.json` was committed at `43bcc1a` (2026-08-24); the
compositional margin clause landed later, at `c27f81e` (2026-08-25). So the
lizard's 1-leaf floor is an **upper bound taken against framing that no longer
ships**. Whether it still collapses to 1 leaf today is **UNMEASURED**.

**And the A/B is not re-measurable from this checkout.**
`lizard_camera.json["glb"]` points at an empty scratchpad directory; no
side-profile `.glb` is committed. Re-establishing the control costs a **live
FLUX + Hunyuan draw**, not a replay.

**U3's scope is therefore:**
1. **Re-measure the lever under HEAD's framing**, generator pinned and
   recorded — `lizard_camera.json` records no `generator` field, so "same
   generator" was always an inference. The lever's size is whatever that run
   says. **Pre-registered: if per-subject framing does not beat HEAD's fixed
   suffix on ≥1 subject without regressing another, U3 does not ship** — the
   same bar `85967c1` applied to the global change.
2. Only if that bar is met: wire per-subject framing into the serve path.

**Two staleness hazards, both verified.** (a) The mesh cache key must
incorporate the framed prompt, or a reframed concept silently serves the old
mesh. (b) **Second, unmentioned hazard:** `mesh_acquire.py:618-632` — when
`reuse_concept` is set, an existing `concept.*` in `out_dir` sends the pipeline
**straight to stage 2**, so a framed prompt injected at `:635` is never
evaluated at all. Production is safe today (`reuse_concept=False` by default,
and `get_provider("hf2")` does not set it) but `probe_mesh_bakeoff` sets it
**True** — so a probe measuring U3 would silently measure nothing.

Falls back to the raw prompt when no model is available.

## 11. Component U4 — `search_extraction(spec)`

**Deterministic.** Given a spec (target count, expected pairs), sweep a widened
grid and rank cells by distance to the target. No model is consulted. The LLM
never sees a voxel number — §1.4.

⚠ **AMENDED 2026-09-02. Most of what this section claimed as U4's content is
ALREADY SHIPPED, and its proposed grid violates a measured safety floor.**

**What is already shipped — U4 must not claim it.** The injected-reference seam
exists and is default-on: `reference_count=` (`mesh_to_tree.py:2710-2713`)
substitutes at `:2989-2990` and reaches **both** terminal exits, the reported
fidelity, `rank_by_fidelity` and `_serve_rank`. C1/Z1 did this, and
`tests/test_anatomy_expectation.py:332` already asserts it.

> **A U4 test of the shape "fidelity is scored against the spec" WILL PASS WITH
> U4 ENTIRELY REVERTED.** That is an instrument that cannot fail. This
> section's original sentence — "applied to the exit rather than only to
> ranking" — inverts what C1/C2 actually did: `r_prepass_enabled`'s docstring
> says the *stop-searching decision* moved and the reported fidelity was
> untouched.

**U4's genuinely new content is exactly three things:** the widened grid, an
explicit cell budget, and ranking cells by distance to the spec. The plan must
scope it to those and measure only those.

**There are TWO terminal exits, not one.** `mesh_to_tree.py:3169-3170` (`held
is None`) and `:3198-3203` (drain path, `held` bound). The comment at
`:3193-3197` is an explicit warning left by the last unit that touched it. A
change to one is not a change to both.

**The grid must start at 24, not 16.** `VOXEL_GRID_MIN_SAFE = 24`
(`mesh_to_tree.py:274`); 16 sits **below** the floor, and the floor is a
measurement, not a style rule — at res 16 the committed `insect` fixture
fragments into **3 post-`fill()` bodies** (two legs amputated before
skeletonization), asserted by `tests/test_voxel_grid_env.py:131-132`. Sub-floor
values are warn-and-proceed, not accept-as-safe. **Use `[24, 32, 64, 96, 128,
192, 256]`.**

**The cell budget interacts with a recorded, unrepaired defect.**
`DRAIN_BUDGET = 6` is documented as `FIDELITY_K1 × len(VOXEL_GRID)`
(`mesh_to_tree.py:577`), which holds for a 3-voxel grid and **not** for a
longer one — `configured_voxel_grid`'s own docstring already reports the
breakage. A 7- or 8-voxel grid walks straight into it. U4 must either raise the
budget with a measured justification or document that it is knowingly running
past it.

**`fidelity_score` CLAMPS, and that makes the Class-2 subjects a no-op.**
`r_eff = min(max(reference_count, MIN_LEAVES), MAX_LEAVES)` with `MIN_LEAVES,
MAX_LEAVES = 4, 8` (`mesh_to_tree.py:3398-3409`). So `fidelity_score(8, R) ==
1.0` for every `R ≥ 8`.

> For **octopus and water bear — the two subjects §3's Class 2 names, both with
> a 9-feature target** — feeding "fidelity against the spec" is *arithmetically
> identical* to today. U4 cannot claim a Class-2 win through this route. Either
> the clamp is addressed (out of U4's scope as written) or Class 2 is dropped
> from U4's success criteria.

* Cost: the 7-voxel grid is ~2.3× today's skeleton builds. Bounded by the cell
  budget above and by early exit on an exact spec match. ⚠ Note the recorded
  finding that ~76% of pipeline runtime is per-compile **process startup**, not
  geometry — the cheaper win may be there, and a plan that widens the grid
  without checking that first is optimising the wrong axis.
* Emits ordinary candidates. `structural_prefilter`, the gate, the drain,
  phases 3/4 and every receipt are untouched. ⚠ `structural_prefilter` takes
  the **pre-reconciliation** `root_children` count; calling it without that
  silently inverts the result (P1, M1).

## 12. Component U5 — `propose_tree(prompt, spec)`

The **second producer**: an LLM writes K candidate stick figures (K from
diversity, per ICLR'24 breadth-over-depth; COrigami measured T=1/N=4 beating
T=0/N=1 on their own judge benchmark and then deployed the weaker setting for
determinism — we should take the diversity, because our ranker is a real
compile).

* **Named joints**, COrigami-style: `{"start": "shoulders", "end":
  "front_left_paw", "length": 3, "azimuth": 90, "elevation": -90}`. A
  deterministic adapter compiles joint names to integer `parent_id`s, which
  makes the malformation class `tree_contract.py` guards against
  *unrepresentable* rather than merely detected.
* Output passes `tree_contract` as a hard gate before it can become a
  candidate. A tree that fails is refused with its errors, never repaired
  silently.
* Lengths are **continuous and normalised** to `LONGEST_LIMB_TARGET`, not
  COrigami's small integers — those exist for a box-pleating grid we do not use.
* ⛔ **THIS BULLET IS VOID. CORRECTED 2026-09-03 — see §1.1's correction
  block.** Class 3 is empty: the lizard's six flaps ARE reachable, and
  `IDE_FREEZE_PRUNE_CUTOFF=1` serves them (6 leaves, 0 stubs, confirmed,
  fidelity 1.0) with correct anatomical labels and no LLM. **U5's sole stated
  justification is gone.**

  **Octopus and water bear are NOT a replacement justification.** Their nine
  leaves *are* extracted — 9 of 64 cells for the octopus under the freeze — and
  are rejected by `MAX_LEAVES = 8`. §15 says U5's trees "enter the same queue"
  with "`structural_prefilter`, the gate, the drain, phases 3/4 and every
  receipt untouched", so an LLM-authored 9-leaf tardigrade dies at the
  identical constant. U5 cannot answer Class 2 either.

  **What survives is a different and weaker argument, and it must be made on
  its own terms: SHAPE, NOT COUNT.** The lizard's servable six carries **1
  pair where its anatomy wants 2**; cells with the correct 6-leaf/2-pair
  signature exist and the search does not land on them. That is the pair axis
  P2 was forced to leave inactive (§9's correction: no authored pair count
  exists). Any case for U5 must name its subject, rest on pairing and
  attachment topology, and **may not be made on "unreachable".**

## 13. Component U6 — `seed_placement(nodes, pairs, orientations)`

Projects real orientations onto the paper to produce `x`/`y` seeds, replacing
`structural_layout`'s index-parity guess. Rides the **same side channel** and
the same `with_seeds` / `_dedupe_seeds` path, inheriting the SIGSEGV guard on
coincident seeds and the rounding rule (uniqueness enforced on the *rounded*
coordinates, because a raw-float dedup let 59 of 2600 corpus trees land
coincident and wedge the engine).

Ships only on M3's pre-registered bar (§7).

## 14. Component U7 — `critique(tree, orientations, labels, prompt)`

A VLM **critic**, not a scorer.

⚠ **THE SCORE IS DELIBERATELY NOT USED, AND THAT IS THIS REPO'S OWN
MEASUREMENT.** The judge-loop wave (PRs #168–#173, 16 billed calls) found
extracted trees scoring *identically* to hand-authored ones (+0.000536 against
a 0.169 LSD), the one available pairwise comparison was an **order flip** (the
judge preferred whichever tree was shown second), and the **prose found the
bird's missing leg unprompted while the score moved nothing.** COrigami's own
Table 2 points the same way: their deployed judge reaches 0.715 accuracy on a
set whose majority-class baseline is 0.636 — **+7.9 points.**

So the output is a list of named defects (`missing_appendage`,
`wrong_attachment`, `broken_symmetry`, `implausible_proportion`), each naming
node ids. It reaches the agent as advisory text and the search as **at most a
veto flag**, never a ranking term. It runs **after** the serve is recorded, the
ordering `_judge_the_extraction` already uses so the stash can never contain
something the judge influenced.

## 15. Integration

`auto_mesh_to_metric_tree` gains one keyword-only argument, `extra_candidates`,
defaulting to `()`. U5's trees enter the same queue as mesh candidates, are
deduped by the same key, ranked by the same `_serve_rank`, and repaired by the
same phases. `MeshTreeResult` gains `producer` (`"mesh"` | `"llm"`) and
`orientations`.

**Why the search itself does not change:** this is the property that made node
order (S6) and re-rooting (PRs #107–#118) shippable — *change the input to the
search, not the search*. Every ranking key, budget, trace row and receipt keeps
its exact meaning.

**Degradation, the binding contract.** No key / no network / flags off →
U2 falls back to the 14-row table, U3 to the raw prompt, U5 contributes zero
candidates, U7 returns `None`, U4 reduces to the shipped grid, U1 and U6 emit
nothing. **The result is byte-identical to today's pipeline**, pinned by test
on all five committed fixtures — the same rollback shape `IDE_JUDGE_LOOP` and
`IDE_EXTERNAL_R` already use.

---

## 16. Decomposition — three implementation plans, not one

| Plan | Units | Character | LLM required |
|---|---|---|---|
| **P1 — measure and carry** | M1, M2, M3, U1, U6 | Pure measurement plus one optional data channel. Ships value alone: better placement seeds and a judge payload that can finally fill `angle_coverage`. | **No** |
| **P2 — specify and search** | U2, U3, U4 | The LLM supplies objectives; deterministic search consumes them. | Yes, degrades |
| **P3 — propose and critique** | U5, U7, §15 | The second producer and the critic. | Yes, degrades |

P1 is a prerequisite for P3 (U5 emits orientations U1 must already define) and
independent of P2. **P1 must land and be measured before P2 or P3 is planned**
— M1 and M3 carry pre-registered ship bars that can cancel U4 and U6.

## 17. Error handling

Every LLM seam follows `_judge_the_extraction`'s shipped posture: flag off →
`None` and byte-identical output; no client → `None`, because a missing
credential is not an error; any exception → a **structured failure record**,
never a raise, because a bookkeeping failure must not un-measure the work. The
three states (*never asked* / *asked with nothing to read* / *asked and
failed*) stay distinguishable — collapsing them is the defect `_judge_failed`
was added to fix.

`ExtractionForestError` and `tree_contract` errors propagate as today. U5 tree
adapter failures are refusals with the contract errors attached.

## 18. Testing

* **Byte-identity suite.** All five committed fixtures through
  `auto_mesh_to_metric_tree` with every flag off, asserting the served tree,
  pairs, trace and receipts are unchanged. This is the gate on the whole design.
* **Anti-vacuity.** Each new instrument must be shown to *vary*: an
  `orientations` channel that is always empty, a critic that always returns no
  defects, or a spec that is always `None` fails its own test. (`base_eval.py`
  already carries this discipline.)
* **Side-channel tripwire.** A test asserting no node dict reaching attempt-0
  carries an orientation key, mirroring `has_placement_seed`.
* **Provenance pairing.** `_PROVENANCE_CAVEAT` and `_R_SOURCE` asserted to
  agree at import, extended for the `llm` key.
* **Offline.** Every LLM tool tested against a recorded transcript; `recorded_with`
  checked, because a `replay.json` that was never actually recorded has bitten
  this repo before.

## 19. Risks

| Risk | Mitigation |
|---|---|
| The LLM's proportions are worse than measured ones | The mesh remains the proportion source whenever both producers agree on count; disagreements are recorded as receipts, not silently resolved. |
| U4's widened grid costs too much wall-clock | Cell budget + spec-match early exit; M1 sizes it. Note the recorded finding that 76% of pipeline runtime is per-compile process startup, not geometry — the cheaper win may be there. ⚠ The budget also collides with `DRAIN_BUDGET = 6`, documented as `FIDELITY_K1 × len(VOXEL_GRID)` and already broken for grids longer than 3 — see §11. |
| Real orientations turn out no better than golden-angle-by-index | M3 is pre-registered to cancel U6. The channel still pays for itself through `vlm_judge` and `pose_target`. |
| A third `r_provenance` value silently misattributes R | ⚠ **The mitigation originally written here was MEASURED INSUFFICIENT 2026-09-02.** The import assertion passes while `_provenance_lines` (`mesh_report.py:249`) routes the new key to the self-derived caveat via a hardcoded tuple, printing a contradiction with every guard green. And extraction has no provenance parameter at all — `"external"` is stamped unconditionally, laundering an LLM row as *human-authored*. Real mitigation: fix the dispatch, widen the seam, strengthen the assert. See §9a. |
| Adding a producer changes rankings invisibly | `runner_up` already records the displaced arm; extend it to record `producer` so a serve that switched producers is visible in the receipt. |
| Scope creep into the packer question | Explicitly out of scope (§3), with its own future spec. |

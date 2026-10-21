# Handoff: the two ALIGNMENT goals — whole-square design, and models that look symmetric

**Date:** 2026-08-03
**Lands from:** PR #71 (`claude/crease-pattern-vlm-validation-dfc97b`, 37 commits)
**Owner:** picks up both goals from a corrected framing. Neither is done.

> **For whoever executes this — read §0 before anything else.** Both goals have
> been specced once already and BOTH specs were built against the wrong frame.
> The single highest-value thing you can do is not skip brainstorming.

---

## 0. The framing correction (this is the important part)

Two specs were written for these goals and both were built as **rescue rungs** —
mechanisms to help a tree that FAILS TO PACK get packed, slotted into the
existing ladder (`order → placement → normalize → jitter → composed → stub`).

That was wrong. The goals are **alignment tools for models that already compile
fine**:

| goal | what it actually means |
|---|---|
| boundary placement | the agent should design models that fold from a whole **uncut square**, not models that only crease the convex hull of the leaf positions |
| symmetry | fix models that come out **lopsided** when they are supposed to be symmetric |

The framing error was not cosmetic — **it inverted one spec's direction.** As a
rescue rung, the natural move is to REMOVE a constraint blocking the packer, so
the symmetry spec proposed *relaxing* bilateral pairing. As an alignment tool the
move is to *strengthen* it. The correct fix (path reconciliation, now shipped)
strengthens it. Exactly backwards.

**Concretely, for your brainstorm:** the trigger for all of this was
*"the dog I generated looks a little asymmetric"* — about a model that
**compiled successfully**. Pack rate is not the target. Do not accept a design
whose success metric is "more trees pack."

---

## 1. What shipped, and what it does NOT prove

**Path reconciliation** (`mcp_harness/pair_reconcile.py`), unconditional at
`mesh_to_tree.to_metric_tree:669-671`. A flap's tip lands at its **root-to-tip
path length**, not its last edge length, so a declared pair whose two limbs hang
off different junctions came out asymmetric even when the tree looked symmetric.
Two reach-preserving operations: LCA re-parent (both members onto the lowest
common ancestor, each edge grown by the distance travelled) and orphan removal
to a fixpoint (a childless non-root node is a leaf, i.e. an invented flap —
omitting this measured **12 invented flaps across 10 of 50 configs**).

### ⚠ Three things about it that are easy to over-read

1. **`pair_path_gap_max = 0.0` on all five subjects is TAUTOLOGICAL, not
   evidence.** After reparent+equalize every surviving pair is two siblings
   carrying byte-equal lengths, so 0.0 holds *by construction* (0 violations
   over 60 extractor configs). It is a **wiring tripwire for the operation**,
   not a measurement that any model came out symmetric. Do not cite it as
   "the models are symmetric now."

2. **It did not move crease-pattern symmetry.** Measured, committed:

   | subject | CP mirror residual before | after |
   |---|---|---|
   | humanoid | 0.1044 | **0.0000** (exact mirror, 33 → 21 verts) |
   | bird | 0.318880 | **0.318880 — byte-identical** |
   | fish | 0.104129 | 0.114566 (slightly worse) |

   `bird` is the existential proof that a symmetric tree does not give a
   symmetric CP: its metric tree is exactly symmetric and its CP is 31.9% of the
   paper's edge length off under reflection, with only 48.5% of creases matching.

3. **It only covers mesh-extracted trees.** `server.py` does not import
   `pair_reconcile`, so any tree the LLM authors through the MCP tree-drafting
   tools bypasses reconciliation entirely. If the agent hand-builds a tree, none
   of this runs.

**Known regression, recorded not fixed:** quadruped moved `jitter → stub`,
`stub_flaps 0 → 3` — the serve trades nudged proportions for three
engine-invented flaps, a downgrade in admissibility class. Found only by
counterfactual attribution; pack rate, the admission table and `served_leaves`
are all blind to it.

---

## 2. GOAL 1 — whole-square design. **Open. The falsification is weaker than recorded.**

Current coverage (fraction of the square the CP reaches), committed baseline:

| bird | humanoid | quadruped | insect | fish |
|---|---|---|---|---|
| **0.500** | 0.632 | 0.716 | 0.860 | 0.908 |

### What the record says killed it, and why that is now in doubt

CLAUDE.md §1.1(2) states the premise-falsifying number:

> "The unconstrained solver already parks ~83% of leaves exactly on the boundary
> unaided (k=4 puts 4/4 at the corners and scores coverage 1.000) … So 'force
> leaves to the boundary' is not a lever — the leaves are already there."

**That number was measured in the friendliest regime.** Re-measured on the live
engine during this audit:

| regime | leaves on boundary | k=4 corners | k=3 |
|---|---|---|---|
| **equal-length** flaps | 87.9% (29/33) | 4/4 | 3/3 on boundary |
| **unequal-length** flaps | **69.7%** (23/33) | **1** | **0 of 3 on boundary** |

Real subjects have unequal flaps. The falsification holds in the regime that
does not describe the product.

### Four more facts that change the picture

- **Slice 0 was never executed.** The plan has **0 of 55 checkboxes** done; the
  spec still reads *"design, revision 2, awaiting review."* It was killed by
  analysis plus one side measurement, not by running its own plan.
- **The measurement that retired the C++ mechanism was never committed.**
  *"pinning all four corners breaks every model, pinning one moves coverage
  ±0.3%"* exists as **one line of prose** in a different spec, with no script, no
  fixture, no log anywhere in git. It is unreproducible from the repo alone.
- **The only coverage-relevant knob on the automatic path pushes the WRONG WAY.**
  `rescue_ladder.py:188` clamps every placement seed into `[0.05, 0.95]` under
  the comment *"keep seeds off the paper boundary."* Lifting it was Slice 0's
  **Phase 0** — pure Python, no C++, described in its own plan as an
  afternoon — and it was **never run**. This is the cheapest untried experiment
  in the whole retired slice.
- **Coverage is observed and never acted upon.** No code anywhere reads a
  coverage value and branches on it. There is no `design_scale` column either.

### Two traps in the metric itself

- `hull_coverage` reads **exactly 1.0000 on all nine committed goldens** after
  `square_complete` — which is the fold the 3-D viewer actually receives. The
  deficiency it exists to expose is invisible on the user-facing artifact.
- Its **wiring is unpinned**: no test asserts `hull_coverage` is in
  `benchmark_subjects._COLS`, and no test reads `scorecard_baseline.jsonl` at
  all. Gutting the call site leaves the suite green. Its sibling columns
  (`pair_gap_max`, `stub_flaps`) both have exactly that pin. **Fix this first —
  it is cheap and the project has been bitten by this precise gap before.**

### The one working lever that already exists

`find_free_paper` + `suggest_flap_for_region` turn an uncreased region into a new
detail flap, recompile, and **verify the free area shrank**. It is real and
gated — but it is agent-callable/HITL only, never automatic, and it has never
been run against `hull_coverage` (the two measure *different* hulls: leaf-node
locations vs the exported fold's `B` vertices).

---

## 3. GOAL 2 — models that look symmetric. **Half done; the remaining half has a named lever.**

Tree-level symmetry ships (§1). **CP-level symmetry does not**, and nothing in
production measures it — `cp_mirror_residual` is a one-off script under `docs/`,
not a column. The three scorecard columns that *look* like symmetry
(`asymmetric`, `pair_gap_max`, `pair_path_gap_max`) are all **tree-space** and
none would move when a CP goes lopsided.

### The mechanism, established

Symmetry reaches the geometry at only **two sites** — the optimizer's
`tmConditionNodesPaired`, and `ProjectActivePaths`'s two linear rows per pair.
Both touch **only paired leaves**. Nothing constrains anything else.

### ★ The biggest single finding in this audit

`set_symmetry_angle` is a far bigger lever than the codebase acknowledges, and
**it is dead-ended by our own code, not by Lang's.** On a 4-leaf paired star:

| axis | design scale | where the leaves land |
|---|---|---|
| 45° (hard-coded default) | 1.010153 | edge midpoints |
| **0° (book)** | **1.428571 (+41.4%)** | **all four on the CORNERS** |

It then dies with *"polygon network became invalid after active-path
projection … this should not happen."* Cause: **`ProjectActivePaths` hard-codes
the mirror axis to `(x,y)→(y,x)`** (`TreemakerWrapper.cpp:1139-1143, 1181-1200`)
and never reads `mSymAngle`. So `set_symmetry_angle` changes the optimizer's axis
while the post-optimization polish still forces `y=x`, and the two fight.

**This is one lever that hits BOTH goals** — corner occupancy *and* the symmetry
axis. Pulling it requires fixing `ProjectActivePaths` first: a C++ change.

Two corollaries:

- **The prior conclusion "book symmetry falsified, the hard-coded 45° is
  defensible" is CONFOUNDED.** 4 of book0's 10 rows fail *inside the projection
  step itself*; diag45 has zero such failures. book0's 0/10 was partly a
  measurement of our projection, not of book symmetry.
- **`ProjectActivePaths` would partially defeat the previously-proposed slice-2
  lever.** It re-solves and overwrites *every* leaf coordinate after the
  optimizer converges, carries symmetry rows only for `apply_symmetry`'s pairs,
  and consults no `tmCondition` at all. Pinning an unpaired leaf to the axis in
  the **optimizer** is not sufficient — the projection is free to move it back.

### A correction to the spec's own prescription

The spec says the lever is `tmConditionNodeSymmetric` (unbound) and that the
already-bound `tmConditionNodeCombo` *"cannot express lies on y=x."* **Wrong
about the class.** Combo has `SetToSymmetryLine`, which emits the byte-identical
`StickToLineFn`, and Lang ships `tmTree::SetNodesFixedToSymmetryLine` as the
one-line v5 wrapper. What is true is that the three *exposed* wrapper methods
never touch that flag. **The cheap version is a flag on an existing condition,
not a new condition class.**

---

## 4. The R5 gate defect — real, but NOT in the shape it was recorded

Alleged: the Tier 2.5 gate learned *"more declared pairs ⇒ infeasible"* from a
corpus whose pairs are geometric contradictions.

**The corpus defect is confirmed exactly:** `feasibility/corpus_wide.jsonl`,
2600 rows, 7502 declared pairs, and **0 of 7502 have equal edge lengths** (not
even to 1e-6). The cause is the **independent length draw**, not only the
shuffle — two of six generator families never call `_pair_leaves` and still
produce 0-equal pairs. `n_sym_pairs` is the **3rd most important of 7 features**.

**But the rule as stated is refuted.** It is non-monotone: declaring 2 genuine
equal-length pairs on a 4-leaf tree **RAISES** p_pack by +0.177; the penalty only
begins at 3+. And `n_sym_pairs` is heavily confounded with `n_leaves` — the same
within-stratum confound S8 already found. **A plan written against the monotone
premise will target the wrong region.**

**The real defect, in the region that matters:** on all four production body-plan
templates — whose pairs are exactly equal-length — declaring the pairs **lowers**
p_pack, directionally opposite to the repo's own controlled ground truth
(equal-paired 42.5% vs unpaired 30.0%).

**Severity: LATENT, not inert.** The gate is consulted on three live paths with
this model; the verdict is a **hard code-level block on two**, and `p_pack`
**orders the mesh candidate compile queue**, so genuinely-paired candidates are
silently demoted even when nothing is blocked. This reaches the user-facing
`reference_tree_from_query`. The model is gitignored and auto-trains from the
committed corpus, so **the defect self-reproduces on every clean checkout and in
CI.**

**Mitigating, and one genuine near-miss:** `block_threshold` is very low
(0.0167), so nothing among the production templates is actually blocked. But at
**5–6 genuine pairs p_pack falls to 0.0100 — below the threshold**, and those
trees escape only because `gate.predict` evaluates OOD *before* the threshold.
That safety is **accidental**. As the corpus gains coverage and trees stop
reading OOD, it converts into real blocks.

> Directly relevant: this PR added `tests/gate_drift_exceptions.py` because
> path reconciliation pushed `insect` **out of distribution** (OOD 0.6250 →
> 1.0243, threshold 0.8626; the LCA re-parent owns it, `edge_mean` is the
> mover). Insect is currently shielded by the OOD branch. **A gate retrain that
> brings insect back in-distribution could expose it to the very near-miss
> above** — check p_pack against the block threshold as part of that slice, not
> after.

---

## 5. Lever inventory (verified, not remembered)

**Built, functional, ZERO callers anywhere** — not production, not tests, not
probes:

- `set_node_at`, `set_node_on_x`, `set_node_on_y` — verified live during this
  audit: they pin leaves exactly to the requested corners with no scale loss.
  Landed *deliberately dead*, after the falsification, for a corner-occupancy
  probe **that was never committed**.
- `set_symmetry_angle` — one probe caller; see §3.
- `debug_active_path_report` — the only read-out on the projection step that
  breaks non-45 builds.

**Unbound but compiled into the shipped `.so`:** 10 of 13 `tmCondition*` classes
(including `tmConditionNodeSymmetric`), `tmEdgeOptimizer` entirely, and
`tmStubFinder::TriangulateTree` / `FindAllStubs`.

**A free win, no new binding required:** the ladder **computes the design scale
of every rung**, carries it in the payload, embeds it in every exported fold's
`frame_title` — and **never compares it.** None of the four selection keys has a
scale term. Adding one is a new term in one tuple.

**Production-dead modules that look like levers:** `crease_augment`,
`mobility_search`, `fold_mutate`, `kick_field`, `pose_search`, `pose_coupling`,
`pose_pregate`, and `structural_search` (reachable only from `mobility_search`,
which has no importers — and it bypasses the ladder, the audit, mv-repair and
every annotation).

---

## 6. Traps that will cost you a session if you miss them

- **A bare `HeadlessTreemaker` compile is NOT the serve path.** It is attempt-0
  for one exact node list; the serve runs the rescue ladder. This has bitten the
  project **four times**, most recently twice in one session. Use
  `server.draft_and_compile_full_base`. (Conversely, the bare compile is the
  *right* instrument for a variant × scale grid, where you want attribution.)
- **The ladder does not live in `mesh_to_tree.py`.** Stage generators are in
  `rescue_ladder.py`; the sequence is `server.py::_perturb_ladder`.
- **A count-based test is not a pin of the wiring.** If a test cannot see the
  line it protects, it is not a pin — measure that by deleting the line.
- **A scorecard re-bless without attribution absorbs regressions.** Re-run with
  the change monkeypatched to identity and diff.
- **A citation can go stale by being FIXED.** Prefer citing structure over
  citing a measurement that might improve.
- Environment: use
  `<repo>/mcp_harness/.venv/bin/python`
  (3.14.3); `cd mcp_harness && PYTHONPATH=.:tests <python> -m pytest tests/
  --timeout=420`; bare `make test` never terminates. A worktree needs **three**
  gitignored build artifacts (engine `.so`, `oriedita/oriedita-1.1.3.jar`,
  `OrieditaValidator.class` via `./build_linter.sh`) or every verdict fakes
  `FAIL-LINT`. Any script calling `draft_and_compile_full_base` must sit under
  `if __name__ == "__main__":`.

---

## 7. Suggested entry points (brainstorm first — do not treat this as a plan)

**Goal 1, cheapest first:**
1. Pin `hull_coverage`'s scorecard wiring (minutes, closes a known gap).
2. Run Slice 0's Phase 0: lift the `[0.05, 0.95]` seed clamp and measure
   coverage. Pure Python, never run, explicitly scoped as an afternoon.
3. Re-measure the ~83% claim across the **unequal-length** regime the product
   actually lives in, and commit the probe this time.

**Goal 2:**
1. Decide whether CP symmetry gets a production measurement at all — today it
   has none, and `pair_path_gap_max` will not serve.
2. The `ProjectActivePaths` axis fix is the load-bearing C++ slice, and it
   unlocks the corner-occupancy result in §3 as a side effect.

**Cross-cutting:** the gate retrain is a genuine prerequisite for trusting any
before/after on either goal, because `p_pack` orders the compile queue.

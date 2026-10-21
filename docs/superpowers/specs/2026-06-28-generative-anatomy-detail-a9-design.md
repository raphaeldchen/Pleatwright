# A-9: Generative Anatomy-Detail Engine — Design

**Date:** 2026-06-28
**Status:** Approved (brainstorm complete) — ready for implementation plan
**Roadmap item:** `docs/followups-web-ui-and-foldability.md` item 9
**Depends on / sits behind:** A-3 = ACCEPT uncreased paper (`origami-viewport-and-a3`);
`find_free_paper` / `free_paper.py` (`molecule-topology-next-session`,
`hull-frontier-agent-fixes-a1-a2`); the 2D crease panel
(`2026-06-28-2d-crease-pattern-panel-design.md`).

## 1. Purpose

Make `find_free_paper` **generative**. Today it is diagnostic: it reports the paper a
tree leaves uncreased (the region outside the leaf-node convex hull) so the agent and
UI can treat it as a design signal. A-9 closes the loop — turn a free-paper region into
**new metric-tree nodes + edges (a detail flap)**, recompile through TreeMaker, and
re-verify, so the IDE genuinely *designs* added anatomy (ears, tail, snout) rather than
only validating what it was given.

**Framing: "generative anatomy detail," not "fill corners."** The bear base proved free
paper is not always in the corners — it can be a `frame` region (sheet minus a fully
interior hull). A-9 fills *regions*, wherever they are.

**What A-9 is NOT (explicit non-goals):**
- It is **not** "option 3" (molecule-level corner-creasing to make the *squared* FOLD
  flat-foldable). That is separately deferred and `complete_square` §8 recommends
  *against* it. A-9 never touches the molecule or the squaring path.
- It does **not** retire the validated-fold-on-download split. A-9 adds flaps but still
  compiles to a leaf-node convex hull that gets squared **for display only**; the
  downloaded `.fold` remains the validated raw artifact, exactly as today.
- It is **not** a correctness fix. Per A-3 the hull-frontier base already folds; A-9 is
  optional aesthetic/anatomical polish.

## 2. Architecture & placement

One new pure module, one new self-verifying MCP tool, no new compile path.

- **`mcp_harness/flap_fill.py`** (new, pure). Same discipline as `free_paper.py`: plain
  coordinates + tree topology in, plain data out; **no** engine / JVM / MCP imports;
  unit-testable in isolation. Owns the *geometry* of turning a region into an ordered
  list of candidate flaps `(attach_node_id, length)` (+ a mirror flap when asked).

- **`suggest_flap_for_region(...)`** (new MCP tool in `server.py`). The *self-verifying*
  wrapper. Calls `flap_fill` for candidates, then drives recompile + re-check through the
  **existing** `_run_isolated` / `_worker_full_base` / `_compile_with_perturb` machinery
  and `free_paper.free_paper_regions`. The compile pipeline itself is unchanged.

- **Reused unchanged:** `draft_and_compile_full_base` (recompile), `find_free_paper`
  (detect + re-verify), `predict_tree_feasibility` (optional fast pre-reject), the
  perturb budget, the 2D `CreasePanel` / `creasePattern.ts` (view result), the
  `json` / `display_json` WebSocket split, and the metric-tree format.

**Invariant preserved (CLAUDE.md §2):** the tool only ever emits a new **metric tree**
(nodes + symmetric_pairs). The `.fold` stays pure compiler output the AI never edits.

### Data flow (one confirmed fill)

```
agent: find_free_paper(tree) -> regions[]
user approves "ears" on region R (+ its mirror R')
agent: suggest_flap_for_region(tree, region=R, mirror_region=R',
                               desired_length?, name="ears")
   |- flap_fill: R (+R') -> ordered candidates (attach_node, length) [+ mirror]
   |- for each candidate:
   |     tree' = tree + flap(s) + symmetric_pair
   |     (optional) predict_tree_feasibility(tree') == infeasible -> skip
   |     fold = recompile(tree')            # existing worker + perturb
   |     if ERROR: next candidate
   |     regions' = free_paper(tree')
   |     if _verified(R[,R'], regions', fold): return status="filled"
   |- exhausted -> status="accept" (A-3), tree unchanged
agent: shows recompiled fold in 2D panel; reports status honestly
```

## 3. The region -> flap geometry (`flap_fill.py`)

A detail flap is a new **leaf node** `{id, parent_id, length}`; nothing else structural
changes. TreeMaker's packing constraint is, for every leaf pair *i,j*:
`distance(tip_i, tip_j) >= scale * treepath(i,j)`. The new leaf draws a circle that must
find room; A-9 aims that room at the chosen region.

**Attach model — "sibling flap" (v1 core).** A region is bounded by a hull chord between
two adjacent leaf tips A and B (`region.adjacent_node_ids`). Grow the new leaf off the
**nearest common ancestor** of A and B in the tree, so its circle packs into the angular
wedge of free paper between them. Anatomically: a new limb between two existing ones
(tail between hind legs, ears between head and shoulders). Covers the bear and
essentially every quadruped/bird case.

**Length.** New circle radius (paper units) ≈ the region's **inradius** (largest inscribed
circle of the region polygon). Tree-edge length relates by the pack scale:
`L ≈ region_inradius / scale` (scale is known post-optimization). Then **clamp to the
optional `desired_length` hint** (a "long tail" biases longer, capped at what the inradius
allows; a short hint is honored). This is the first guess; §4 corrects it.

**Ordered candidate list** (the wrapper tries them until one verifies):
1. sibling off nearest-common-ancestor(A,B) at `L = inradius/scale` (primary)
2. same, shorter (≈0.6×) — for tight repacks
3. sibling off parent-of-A / parent-of-B — when the common ancestor is the root and the
   wedge is lopsided

**Deferred — "branch flap" (NOT v1 corner/edge-strip).** Attaching the new leaf to an
adjacent *leaf* itself (turning that tip into an interior node), subdividing an existing
flap — toes, claws. Restructures an existing flap (riskier repack); not needed for the
headline animal cases. v1 corner/edge-strip path grows siblings only.

### Frame-region attach model (Task 8 / branch-flap variant)

When the leaf hull is **fully interior** to the paper (no flap tip on any sheet edge),
`free_paper` returns a single `kind="frame"` region — the frame around the hull. The
sibling-off-NCA geometry is meaningless here (the chord is the whole hull); instead A-9
uses the **branch-flap** attach:

- For each free corner `C` in `region["corners_contained"]`, find the hull leaf whose
  tip is nearest `C` (index-aligned with `region["hole"]` and `region["adjacent_node_ids"]`).
- Add a **child** of that hull leaf (`parent_id = nearest_hull_leaf_id`) with length
  `L = dist(hull_tip, corner) / scale`, clamped by `desired_length` when given.
- The child circle is anchored at the nearest hull tip and extends toward the open corner,
  pulling the pack to fill that quadrant.

Candidates are ordered by descending `L` (most-open corner first) with a 0.6× shorter
fallback of the top candidate, exactly as the corner path.

**Hole/id alignment guard:** if `len(hole) != len(adjacent_node_ids)` or no free corners
exist, `suggest()` returns `[]` (graceful empty, triggers `status="accept"`).

**Frame mirror (bilateral frame fill) is deferred** to a later increment. Frame candidates
are always solo (`new_pairs: []`); `mirror_region` is ignored on the frame path.

**Why this is tractable:** `free_paper.py` already computes the hull, regions, polygons,
and the bounding chord's endpoint node ids. `flap_fill` is a *consumer* of that output
plus tree topology; it never re-derives geometry from the engine. "inradius/scale" is the
one origami-math step: a region's largest inscribed circle is the largest flap-circle that
fits there, and packing is scale-linear in tree lengths, so dividing by the known scale
converts paper room directly into tree edge length.

## 4. The self-verify loop & ACCEPT fallback (`suggest_flap_for_region`)

The wrapper owns convergence reasoning so the agent never does.

```
candidates = flap_fill.suggest(tree, region, mirror_region, desired_length)
for cand in candidates:
    tree' = tree + cand.flap(s) + cand.pair
    (optional) if predict_tree_feasibility(tree') == "infeasible": continue
    fold = recompile(tree')                  # existing worker + perturb budget
    if fold is ERROR: continue               # didn't pack -> next candidate
    regions' = free_paper(tree')
    if _verified(region[, mirror_region], regions', fold):
        return { status:"filled", tree:tree', fold, regions_after:regions',
                 flap_ids:[...], message:"added <name>" }
return { status:"accept", tree:<unchanged>, regions:<original>,
         message:"no flap converges into this region; accept as free paper (A-3)" }
```

**`_verified(...)` — three required conjuncts:**
1. **Frontier shrank where intended.** The *target* region's area in `regions'` dropped
   below a fraction of its original (the flap consumed *that* region; did not merely
   shuffle the frontier elsewhere). The check the feature lives or dies on.
2. **Still packs.** `recompile` returned a real `.fold`, not `ERROR:`.
3. **Still folds.** Reuse the existing foldability path the viewport trusts (bounded, no
   NaN). We do **not** gate on a clean Oriedita pass — per A-3 the hull-frontier lint
   failures are false-negatives; gating on a clean lint would reject every flap and the
   feature could never fire.

**ACCEPT is a first-class success state, not an error.** If no candidate verifies, return
`status:"accept"`, tree **unchanged**, with the A-3 verdict as the message. The tool
refusing to fabricate a non-converging flap is correct behavior; the agent surfaces it as
"that corner is best left as free paper," not a failure.

**Budget:** the candidate list (≤3–4) × the existing per-compile perturb budget; typically
one recompile. The optional `predict_tree_feasibility` pre-reject (ms, no C++) skips
candidates doomed to a packing failure before paying for the build.

## 5. Symmetry handling

- **Agent owns pairing (semantic).** The LLM decides region R (left flank) and R′ (right
  flank) are the same feature and passes both:
  `suggest_flap_for_region(tree, region=R, mirror_region=R', name="ears")`.
- **Tool adds + verifies the pair atomically.** `flap_fill` emits *both* leaves (mirror's
  `length` equals primary's; `parent_id` is the common ancestor on the mirror side) **and**
  registers the new `symmetric_pair`. The §4 recompile runs on this balanced tree — never
  a lopsided intermediate — so the knife-edge packing only sees symmetric bases and the
  engine's per-pair Gauss-Newton projection (`molecule-topology-next-session`) is fed
  correctly.
- **`_verified` requires BOTH regions to shrink** (conjunct #1 on R and R′), so the
  guarantee covers the whole paired base.
- **On-axis / deliberately-asymmetric features omit `mirror_region`** → single flap,
  single recompile, no pair.
- **Frame + mirror (bilateral frame fill) is deferred.** The frame branch always produces
  solo candidates (`new_pairs: []`); if `mirror_region` is passed alongside a `kind="frame"`
  target region it is silently ignored. Bilateral frame fill (two symmetric branch flaps
  from the hull toward opposing corners) is a later increment.

## 6. Agent & UX integration

**SYSTEM_PROMPT (`agent_loop.py`).** Extend the existing free-paper / A-2 ACCEPT block
with a proactive-but-gated step (Suggest-then-confirm, HITL):
- After a base compiles, if `find_free_paper` returns regions above a meaningful area,
  the agent **names them as opportunities and asks**, then stops. ("Free paper near the
  haunches (~18%) and along the back — room for ears and a tail. Add them?")
- Calls `suggest_flap_for_region` **only on user-approved regions**, passing the user's
  words as `name` and any size cue as `desired_length`.
- Reports `status` honestly: `"filled"` → "added ears, here's the updated pattern";
  `"accept"` → "that corner won't take a clean flap, so I've left it as free paper."
- The ACCEPT-as-default teaching stays intact: A-9 is *offered*, never forced; a base
  with free paper is still a finished base.

**2D panel.** No code change — `CreasePanel` / `creasePattern.ts` already render any
`.fold` by `vertices_coords` + `edges_assignment`. After a confirmed fill the recompiled
fold flows through the existing `json` / `display_json` split; the agent shows the new
flap's creases in the 2D tab (the 3D sim cannot show a clean CP — the reason the 2D panel
exists). The downloaded `.fold` stays the validated raw artifact.

**No server-transport changes.** The tool returns tree + fold as a tool result; the
existing WebSocket `fold` frame carries it to both tabs.

## 7. Testing strategy

**Unit — `flap_fill.py` (pure, fast, no engine):**
- Attach selection: nearest-common-ancestor chosen for known `adjacent_node_ids`;
  root-as-ancestor routes to parent-of-A / parent-of-B candidates.
- Length math: `L ≈ inradius/scale` for known polygons; `desired_length` clamps (long
  capped at inradius-allowed, short honored).
- Inradius: largest inscribed circle on hand-checked polygons (corner, edge-strip, frame).
- Mirror emission: off-axis + `mirror_region` → two equal-length leaves, mirrored parents,
  well-formed `symmetric_pair`; on-axis / no mirror → single leaf, no pair.
- Candidate ordering matches §3.

**Integration — `suggest_flap_for_region` (engine, few, pinned like existing compile tests):**
- **`star-5` corner fill:** `find_free_paper` returns corner regions → `suggest_flap_for_region`
  returns `status:"filled"`, target locale lost free paper, result packs and folds.
- **`cat-spine5` frame fill (Task 8):** `find_free_paper` returns a single `kind="frame"`
  region (hull fully interior) → `suggest_flap_for_region` applies the branch-flap geometry,
  returns `status:"filled"` with a child-of-nearest-hull-leaf new node, total free area
  drops by ≥10% (verified: before=0.1590, after=0.1361 in practice, clearing the 0.9 gate).
- **ACCEPT fallback:** region constructed so no candidate converges → `status:"accept"`,
  tree **unchanged**, A-3 message present.
- **Symmetry atomicity:** paired fill compiles a *balanced* base, both regions shrink, no
  lopsided tree is ever the final result.
- **Determinism / no-regression:** fixed seed → same suggestion; pinned as a drift
  tripwire (matches the existing suite).

**Probe (debug, not CI):** `probe_flap_fill.py` — run a fill, print before/after regions
+ chosen candidate (matches the `probe_*.py` family).

**Verification before done:** full harness suite green (currently 212) + a Playwright
check that a filled bear renders its new flap in the 2D panel.

## 8. Scope / YAGNI (v1 exclusions)

- **No branch flaps** (sibling-only; subdividing an existing flap is future).
- **No recursive auto-fill to fixpoint** — each confirmed fill is ONE
  detect→fill→verify cycle; new free paper means the agent asks again (HITL), the tool
  never recurses. Structural blob-avoidance.
- **No automatic / unprompted filling** — suggest-then-confirm only.
- **No new compile path, no squaring change, no molecule work** — strictly tree-layer +
  existing pipeline. Does not touch option 3; does not retire the download split.
- **No Oriedita-clean gate** — verify = packs + folds + target region shrank (A-3).
- **No anatomy library / flap catalog** — tool is anatomy-agnostic geometry; all meaning
  is the LLM's descriptive `name` string (rides in `frame_title`, never affects geometry).

## 9. Build summary

`mcp_harness/flap_fill.py` (pure geometry) · `suggest_flap_for_region` (self-verifying
MCP tool reusing existing compile/perturb/free-paper machinery) · a SYSTEM_PROMPT block
(HITL suggest-then-confirm) · unit + integration tests + a probe. Rides entirely on
existing transport, the 2D panel, and the metric-tree invariant.

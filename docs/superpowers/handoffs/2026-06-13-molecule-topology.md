# Handoff: TreeMaker Molecule-Construction Layer

## UPDATE 2026-06-13 (session 5) — FAIL-LINT ROOT CAUSE FOUND: MISSING PAPER CORNERS, *not* a degree-5 subpoly crease.

**The "degree-5 interior subpoly missing-crease" hypothesis at the bottom of
section 4 of this doc is DISPROVEN for the current frontier.** Evidence gathered
purely from the exported FOLD (no rebuild) via the NEW `probe_degree.py` +
direct Oriedita verdict.

**The real defect (fully characterized, quantitative law):** every FAIL-LINT
case has a **malformed paper boundary** — it is missing one or more of the four
paper corners `(0,0),(1,0),(1,1),(0,1)`, and each missing corner is replaced by
exactly ONE spurious **degree-3 (ODD) interior vertex** that "bevels" the corner.
That bevel vertex has 1 real crease (M or V) to a molecule vertex + **2 creases
mislabeled `BORDER`("B")** running between the two adjacent paper-edge points.
An odd-degree interior vertex can never be flat-foldable → Oriedita flags it
(ANGLES/Kawasaki). Count law confirmed:

| case        | corners present        | defective interior verts |
|-------------|------------------------|--------------------------|
| star-4 PASS | all 4                  | 0                        |
| star-5      | 1  {(0,0)}             | 3  (v7,v13,v14)          |
| star-6      | 2  {(0,0),(1,1)}       | 2  (v13,v19)             |
| star-8      | 2  {(0,0),(1,0)}       | 2                        |
| cat-spine4  | (similar)              | matches missing corners  |

i.e. **#defective interior verts == #missing paper corners**, every time.
NOT precision (coords are exact, e.g. 0.7712), NOT the old self-loop #7, NOT an
interior subpoly crease. The bug is in **paper-corner / outer-boundary path
generation** in the molecule builder.

**Why earlier sessions missed it:** the first `probe_degree.py` (and intuition)
classified any vertex with a "B" edge as a *border* vertex and skipped it →
false "0 interior violations". The fix: a vertex is INTERIOR iff its coords are
NOT on x∈{0,1} or y∈{0,1}; a B edge on such a vertex is the DEFECT SIGNATURE.
`probe_degree.py` now reports corner-presence + interior-B vertices correctly.

**>>> DEFINITIVE (2026-06-13, later): NOT AN ENGINE BUG / NOT A REGRESSION. <<<**
Followed the trail all the way down. `tmTree.cpp:2723-2734` is explicit:
TreeMaker builds the crease pattern on the **convex hull of the leaf nodes**, and
`mIsPolygonValid` only certifies *the hull is filled* — NOT the paper square. For
star-4 the hull IS the square (flap tips at the 4 corners) → whole paper creased
→ PASS. For star-5 the 5 flap tips give a **pentagonal hull inscribed in the
square**; the 3 square corners lie OUTSIDE the hull and TreeMaker (by design)
does not crease them. The hull boundary is also slightly **non-convex** at the
hinge-boundary points: e.g. star-5 `v7 (0.27, 0.8236)` sits ~0.0014 *inside* the
straight hull edge `v6(0,0.65)->v5(0.54,1)` (that line is at y≈0.825 at x=0.27).
That faint concavity makes Oriedita classify `v7` as INTERIOR (not on the convex
paper boundary) → Kawasaki applied → deg-3 odd → FAIL-LINT. So the FAIL-LINT set
= trees whose leaf-node convex hull does not fill the square. There is NO missing
crease to add in the molecule builder; the engine is doing what TreeMaker does.

**Implications for "the fix" (a PRODUCT decision, not a code bug):**
- (A) Treat FAIL-LINT on hull<paper trees as CORRECT/expected; keep them pinned
  in the baseline as the documented behavior (no engine change). Lowest risk.
- (B) Make them PASS by trimming the EXPORTED paper boundary to the actual hull
  (the outer crease cycle) so Oriedita validates the hull as the sheet — but the
  ~1e-3 concavity at hinge points must be resolved (snap hinge-boundary vertices
  onto the straight hull edge, or emit the true convex outline). Export/linter
  work, NOT engine.
- (C) Constrain tree drafting (Tier 2) to corner-fillable trees / add paper-corner
  node conditions (`tmConditionNodeCombo` ToPaperCorner exists) so the hull fills
  the square. Design-side.
- (D) Genuinely crease the corner triangles outside the hull — NOT what TreeMaker
  does; would be inventing new molecule behavior. Highest risk, not recommended.

Diagnostics added this session: `probe_degree.py` (corner/interior-B detector),
`probe_facets.py` (C++ crease-KIND + poly-network dumps, `--poly` mode).

---

**KEY LOCALIZATION (narrows the C++ target a lot):** `"B"` is NOT semantically
"paper edge". `tmCrease::CalcFold()` (`tmCrease.cpp:394-410`) sets `mFold = BORDER`
**iff a crease is missing one of its two adjacent facets** (`mFwdFacet == 0 ||
mBkdFacet == 0`); the export then maps `BORDER -> "B"` (`TreemakerWrapper.cpp:89`).
So the interior "B" creases at the bevel vertices are interior creases with a
**MISSING FACET on one side**. ⇒ the real defect is **incomplete FACET
construction in the paper-corner regions of non-axis-aligned flaps** — the facets
that should tile each missing corner are never built, leaving the bounding creases
one-sided (→ BORDER) and the corner vertex absent. NOT a `tmPoly` interior
subpoly crease, NOT boundary-path drawing.

**NEXT TASK (Phase 3/4, needs C++ + rebuild):** instrument facet construction.
Add a diag that, after build, dumps each `tmCrease` with `mFwdFacet`/`mBkdFacet`
addresses + the facets touching each corner region; compare star-4 (all 4 corners
covered by facets) vs star-5 (3 corners with a one-sided gap). Find where the
corner-region facet is dropped in the molecule facet builder
(`tmPoly::BuildPolyContents` facet/corridor pass + the `CalcLocalFacetOrder` /
`BuildCorridorLinks` helpers). Success = a previously FAIL-LINT star/cat returns
Oriedita "Pass"; then re-bless the verdict baseline (`make bless`).

---

## UPDATE 2026-06-11 (session 4) — CATERPILLAR SIGSEGV FIXED (regression #8). Broad sweep: 0 crashes / 0 hangs.

**Headline (objective A) DONE — and it Passes, not just compiles.** The 5-leaf
caterpillar SIGSEGV (`exit -11`) is fixed. It now compiles to a 23-vertex / 38-edge
FOLD and **Passes Oriedita end-to-end** (`probe_lint.py`, `probe_sweep.py`).

**Root cause = regression #8, a classic off-by-one in the `tmArray.h` rewrite.**
`tmArray<T>::MoveItem(from, to)` is **1-based** (its `RemoveItemAt`/`InsertItemAt`
do `begin()+n-1`), but the rewrite grabbed the moved element with the 0-based
`operator[]` *without* the `- 1`: `T t = (*this)[inFromIndex];` instead of
pristine's `(*this)[inFromIndex - 1]`. `tmPath::MakeVertex`'s insertion-sort calls
`mOwnedVertices.MoveItem(mOwnedVertices.size(), i+1)`, so the grab read
`(*this)[size()]` — one past the end — getting garbage/NULL, which `InsertItemAt`
then planted into `mOwnedVertices` while `RemoveItemAt(size())` dropped the real
new vertex. The planted **NULL** later SIGSEGV'd in `tmPath::GetOrMakeVertex`
(`tmPath.cpp:320`, deref `testVertex->mLoc` at addr `0x38` = NULL+offsetof(mLoc)),
called from `tmPoly::BuildPolyContents:1037`. Only topologies whose molecule
builder reorders path-owned vertices (a path with ≥2 interior branch-nodes, e.g.
the caterpillar's length-3 spine) hit the `MoveItem` branch — which is why
star/H/quad never tripped it. `TMASSERT(n < size())` in `operator[]` compiles out
under NDEBUG, so the OOB read was silent in all builds; the `-O0 -g` lldb backtrace
was essential to localize it.

**Fix (`Source/tmModel/tmPtrClasses/tmArray.h`, restores pristine `ad83e7c`):**
`MoveItem` now grabs `(*this)[inFromIndex - 1]`. Also restored the **same dropped
`- 1` in both `NthItem` overloads** (`return (*this)[n - 1]`) — a latent OOB read
of the identical class, used by `tmDpptrArray::ReplaceItemAt` (currently no live
caller, but it contradicted its own "1-based index" doc). No other engine change.

**Objective B (CalcLocalFacetOrder infinite-loop) did NOT reproduce.** The larger
stars the prior handoff said *hung* (star-5/6/8) now compile cleanly in the sweep
(they only FAIL-LINT on the known v5-class precision frontier). No bounded-iteration
guard was added — there is no current reproducer, and adding one speculatively
would violate the reproduce-first discipline. Re-open only if a real hang resurfaces.

**Objective C — broad robustness sweep (`probe_sweep.py`, NEW).** 16 trees varying
node count / depth / edge weights / symmetry. Result: **0 CRASH, 0 HANG**; every
failure is a clean Python `RuntimeError` or a lint verdict. Tally: 9 PASS,
5 FAIL-LINT (precision/topology = the existing v5/molecule frontier: star-5/6/8,
cat-spine4, star-6-sym), 2 CLEAN-ERR (`cat-spine5` "could not build a full crease
pattern"; `deep-chain` "polygon network is not valid" — legitimate un-packable
trees, surfaced cleanly). This PASS/FAIL-LINT/CLEAN-ERR catalog is also the seed
dataset for the CLAUDE.md §6 Tier-2.5 heuristic checker.

**Regression:** `probe_verify.py` still shows star/H/quad all **Pass** (re-run after
the optimized rebuild). New artifacts: `probe_sweep.py`, `repro_cat.py` (minimal
single-process caterpillar repro for lldb). Build the optimized `.so` with
`PYTHON=.venv/bin/python ./build.sh` from inside `mcp_harness`.

Still open (unchanged, the deep frontier — NOT robustness): the FAIL-LINT bases are
the v5-class precision / facet-two-coloring topology issue; the strain path still
perturbs the optimum (non-default); caterpillar/quad strain non-converge (reason 1).

---

## UPDATE 2026-06-11 (session 3) — v5 SOLVED: active-path projection lands. ALL THREE canonical bases now PASS.

**Milestone: the quad (and non-grid bases generally) is now fully flat-foldable.**
`probe_verify.py`: **star Pass, H-shape Pass, spine-2branch quad Pass** — the first
non-grid base to pass end-to-end. The v5 precision blocker is fixed *outside* the
global ALM penalty, exactly as the session-2 handoff predicted (option (b)).

**What shipped** (`TreemakerWrapper.cpp`): a post-optimization **Gauss-Newton
projection of the leaf-node positions onto the active-path constraint manifold**,
holding scale fixed (`ProjectActivePaths`, called inside `BuildAndExport` after the
polygon-validity gate). Each active axis-parallel leaf path contributes the
equality `|loc_a − loc_b| − scale·treeLen = 0` (Jacobian row = unit chord vector
+u at a, −u at b); the tiny normal system `(JᵀJ + λI)dX = −Jᵀr` (n = 2·leafCount,
λ=1e-9 damps the translation/rotation gauge) is solved by a dense Gauss-elim helper
`SolveDense`. Refined coords are written back via `SetLoc`, then polys are rebuilt
for the molecule. Measured effect (`probe_project.py`, `debug_active_path_report`):
active-path |residual| **quad 9.5e-9 → 0**, **H 2.9e-9 → 1.1e-16** in ~1 iter.
Exact leaf coords ⟹ exact Universal-Molecule interior angles ⟹ Kawasaki ≈ 0 — the
irrational-coordinate analogue of the session-1 "snap the star to grid → Pass".

**Critical subtlety — symmetry must be carried in the projection.** Free projection
fixed the quad but **regressed the H-shape** (Pass→2 violations): the active-path
set alone is under-determined, so damped GN drifted the base asymmetric. Fix:
`apply_symmetry` now records the mirror pairs (`mSymPairs`); the projection adds two
linear rows per pair — `b.x−a.y=0`, `b.y−a.x=0` (reflection about the 45° axis
y=x through center (0.5,0.5), which simplifies to `mirror(p)=(p.y,p.x)` since the
center lies on the line). With those rows the H-shape stays symmetric and Passes.

Verified: `probe_verify.py` (all 3 Pass via the plain `build_and_export` path),
`probe_project.py` (residual before/after + lint), `probe_determinism.py` (6/6
identical Pass — projection is deterministic). Build: `PYTHON=.venv/bin/python
./build.sh`.

KNOWN / OUT OF SCOPE (unchanged, pre-existing — NOT caused by the projection):
- The **star stalls at ~1.7e-9** (hits the 50-iter cap, λ-damping floor on its
  rank-deficient/redundant constraint set) but **passes with margin**. Harmless;
  if a future non-grid base needs a tighter floor, add an explicit gauge-fix (pin
  one leaf + one coord) so λ can go to ~0 instead of damping.
- **5-leaf caterpillar still SIGSEGVs** on the scale path (handoff §5, downstream in
  the facet builder — projection doesn't touch it).
- The **strain path** still perturbs the optimum (non-default by design; §5).

---

## UPDATE 2026-06-11 (session 2) — v9 RESOLVED in the linter; v5 is the lone quad blocker; all 3 global ALM levers now CLOSED.

**v9 (the "facet two-coloring frontier") is fixed** — not in the engine, but as a
foldability-preserving **linter normalisation** now LIVE in `linter_server.py`
(`_normalize_for_foldability`, applied inside `validate_flat_foldability` before
the JVM). Two provably-neutral transforms: (1) drop flat `F` creases (Oriedita
already treats them as aux); (2) merge any degree-2 vertex whose two creases are
collinear + same M/V (a spurious midpoint of one straight fold). v9 was exactly a
spurious midpoint (two collinear valleys c13/c14, surrounded only by flat hinges).
Verified (`probe_verify.py`): **star Pass, H-shape Pass (unchanged); quad 2→1
violation** — v9 gone, only v5 left. The H-shape exercises the merge (V12→V10) and
stays Pass, proving the transform is safe. Proof probe: `probe_normalize.py`.
Rationale for linter-side (not export-side): v9 only becomes a deg-2 vertex AFTER
flat hinges are dropped, and dropping real creases is valid only for foldability
checking, never for the canonical FOLD the simulator needs.

**v5 (precision) is now the SOLE quad blocker, and all three global ALM knobs are
definitively exhausted** (don't retry any of them):
- `TOL_* 1e-8 → 1e-10` (keeping WEIGHT_MAX=1e8): **breaks quad convergence**
  (`scale optimization did not converge, reason 1`). The penalty-feasibility floor
  is set by the weight cap (~1e-8); the tolerance can't go below it.
- `WEIGHT_MAX 1e8 → 1e9`: **fixes v5** (Kawasaki −1.16e-6° → +2.6e-8°) **but BREAKS
  the star** (a structural hinge flips FLAT → 1 violation) — same failure as the
  handoff's `1e10`. So 1e8 < safe-for-star < 1e9, and 1e9 ≤ needed-for-quad-v5.
  No single global weight serves both grid (star) and non-grid (quad) bases.
- Conclusion (architectural): the v5-class precision fix MUST live **outside** the
  global penalty — a post-optimization **projection onto the active-path constraint
  manifold** (option (b) below), or a **warm-started high-weight polish** (re-run
  scale-opt from the good 1e8 solution with high weight so it tightens within the
  good basin instead of jumping to the star's degenerate one — needs a
  configurable WEIGHT_START/WEIGHT_MAX in `tmNLCO_alm`). Access points already
  exist: `mTree->GetLeafPaths()` + `IsActivePath()` + `GetMinPaperLength()`
  (= scale·treeLen target) + node `GetLoc()`; a wrapper would add node get/set
  accessors and Gauss-Newton on the active-path equalities holding scale fixed.
  Star proves the target residual (~1e-7°) is reachable and Oriedita-passing.

New probes this session: `probe_normalize.py` (proves the v9 fix), `probe_crease_quad.py`
(facet-colour dump). Engine source is back at known-good (WEIGHT_MAX=1e8, all
TOL=1e-8); the only `tmNLCO_alm.cpp` diff vs commit is the prior session's
1e-5→1e-8 landing.

---

## UPDATE 2026-06-11 — PRECISION SOLVED; FIRST E2E PASSES; quad v9 parked.

**Milestone:** tightened the ALM convergence tolerances `TOL_FEAS`, `TOL_F`
(`tmNLCO_alm.cpp::Minimize`) and `TOL_G` (`MinimizeAugLag` inner BFGS), all
`1.0e-5 → 1.0e-8`. **The 4-flap star AND 4-flap H-shape now PASS Oriedita
end-to-end** (compile→FOLD→lint Pass) — the first clean happy-path successes.
Verify with `.venv/bin/python mcp_harness/probe_verify.py`. KEEP this change.
Rebuild from inside mcp_harness (`PYTHON=.venv/bin/python ./build.sh`).

- Measured Oriedita's Kawasaki tolerance ≈ **1e-6°** (`probe_tol.py`): 2e-7°
  passes, 2e-6° fails — NOT machine-zero, so ~100× tightening was the right lever.
  Exported residual went 9.6e-5° → ~1e-7° on the star.
- DEAD END (reverted): also raising `WEIGHT_MAX 1e8→1e10` fixed quad-v5 precision
  but BROKE the star (flipped a hinge to FLAT) and broke quad-strain convergence.
  Left at 1e8. WEIGHT_MAX is too blunt a knob.
- PARKED (deep frontier, NOT precision, NOT a simple mislabel — that hypothesis
  was falsified): the **spine-2branch quad still fails at vertex v9**. v9's two
  hinge creases are *legitimate* UNFOLDED_HINGEs (the passing H-shape has unfolded
  hinges too, at v7). Differentiator: after dropping unfolded hinges, H-shape v7 =
  1M3V (deg-4, flat-foldable) but quad **v9 = only 2 collinear valleys** (deg-2) —
  both of v9's hinges came out unfolded, so Oriedita rejects it. A valid flat-fold
  M/V *exists* (reassigning the hinges → Pass, `probe_reassign.py`), so the
  geometry is fine; the facet two-coloring just left both v9 hinges unfolded.
  Dropping F edges does NOT help (`probe_fdrop.py`). Real fix is in the
  facet-order/CalcColor layer (why both v9 hinges unfold on asymmetric bases) or
  an export-side collinear-crease merge. Probes: `probe_creasekind.py`,
  `probe_hshape_creases.py`, `probe_v5v9.py`, `probe_verify.py`.

---

**Status as of 2026-06-10.** The headless TreeMaker engine now compiles a metric
tree all the way to a `.fold` crease pattern, and the full **compile → lint**
pipeline runs end-to-end (Oriedita returns per-vertex Kawasaki/Maekawa errors).
This was unblocked by fixing a chain of **7 regressions** introduced by git
commit `d737e92` ("fix: compiler vs build issues") and siblings, all in
`treemaker/Source/tmModel/tmTreeClasses/`.

## UPDATE (this session): the "odd-degree vertex" was a MISDIAGNOSIS — fixed.

The prior handoff blamed **odd-degree interior vertices**. That was wrong. Direct
measurement (new wrapper diagnostic `debug_vertex_report`) showed the genuine
INTERIOR vertices were already **even-degree and satisfied Kawasaki exactly**
(alt-sum = 0 over all incident creases). The degree-5 vertices the prior handoff
called "interior" are actually **border** vertices (engine `IsBorderVertex()==1`,
carrying `BORDER`-fold creases), where Kawasaki does not apply.

**The actual root cause (regression #7, now fixed):** `tmPath::MakeVertex` was
**double-listing every path-owned vertex** in `mOwnedVertices`. The `tmVertex`
constructor already self-registers with its owner (`tmVertex.cpp:96
mVertexOwner->mOwnedVertices.push_back(this)`), but a refactor added an *explicit*
`mOwnedVertices.push_back(theVertex.release())` on top of it. The duplicate then
flowed into `tmPoly::GetRidgelineVertices` (line 639 asserts, debug-only, that
ridgeline vertices are never double-listed) and `tmPath::ConnectSelfVertices`,
which creased **consecutive identical vertices** together → **zero-length
self-loop creases** (`GetOrMakeCrease(v, v)`; `tmCrease.cpp:92` asserts, debug-
only, `aVertex1 != aVertex2`). The causal chain to the lint failures:

```
double push_back  ->  vertex listed 2x in mOwnedVertices
                  ->  self-loop creases (9 of them on spine-2branch quad)
                  ->  GetAxialOrGussetCreases() returns a self-loop as a "flank"
                  ->  CalcBend sees depth2==depth3, mislabels hinge bend
                  ->  CalcColor parity inverts (facet two-coloring inconsistent)
                  ->  CalcFold emits FLAT for structural creases (even ridges: RF)
                  ->  Oriedita drops F edges -> bogus Kawasaki/Maekawa failures
```

**The fix** (one statement, `tmPath.cpp::MakeVertex`): drop the redundant
`mOwnedVertices.push_back`; let the constructor register the vertex (matches the
pristine `ad83e7c` code). Results on `spine-2branch quad`: **31→22 creases**, all
9 self-loops gone, lint **10→2 violations**, interior vertex `v4` now perfectly
flat-foldable, all interior vertices satisfy Kawasaki+Maekawa by direct math.
Side effects: the **classic 4-flap star now BUILDS** (it previously HUNG in
`CalcLocalFacetOrder`, §5 below — the self-loops were corrupting the corridor
graph), and **4-flap H-shape (strain) now compiles** (was a 60 s timeout).

## Remaining (NEW, separate issue): scale-only base is not fully converged.

The residual lint violations are **numerical precision, not topology**. The
4-flap star's center is a textbook flat-foldable vertex (8 creases at 45°), yet
its measured Kawasaki alt-sum is **−0.0001°**, not 0 — the scale-only ALM
optimizer converges to ~1e-4°, which exceeds Oriedita's angular tolerance.
**Proof:** snapping the star's coords to their true grid (`round(x,4)`) makes
Oriedita return **Pass** (`probe_snap.py`); a hand-built perfect 3M1V vertex also
Passes (so the face-less FOLD interface is fine and Oriedita is not the problem).
Non-grid bases (scale 0.717…) can't be snapped to true positions, so they still
show ~1e-4° residuals. **Next task = drive the base to a true uniaxial optimum**
(tighter ALM convergence, active-path/angle conditions, or a snap-to-uniaxial
post-process) so interior-vertex angles are exact. This is the §5 "not at a
complete uniaxial optimum" item, now isolated as THE remaining blocker.

New wrapper diagnostics (kept; match the `debug_poly_report` pattern):
`debug_vertex_report()` (per-vertex border/interior, degree, incident crease
Kind+Fold), `debug_crease_report()` (per-crease facet colors/orders — finds
FLAT-but-should-fold creases). Probes: `probe_vertex.py`, `probe_kawasaki.py`
(direct Kawasaki/Maekawa from the FOLD), `probe_crease.py`, `probe_snap.py`
(demonstrates the convergence-precision residual).

---

## 1. Quick start / reproduce

```bash
cd mcp_harness
PYTHON=.venv/bin/python ./build.sh        # builds headless_treemaker*.so (clang++, ~30s)
# debug build with line numbers (same NDEBUG behavior, for lldb):
TM_OPT="-O0 -g" PYTHON=.venv/bin/python ./build.sh

.venv/bin/python probe_broad.py           # structured trees, GUI-style scale-only build
.venv/bin/python probe_lint.py            # compile (both paths) + Oriedita lint
```

**The proven case** (`spine-2branch quad`): root with two spine nodes 1,2; legs
3,4,5 hanging off nodes 0,1,2 (lengths 0.4/0.4/0.5/0.5/0.5). Compiles to a FOLD
of 13 vertices / 31 edges, scale ≈ 0.717. It is NOT yet flat-foldable (see §4).

Key wrapper entry points (`TreemakerWrapper.cpp`):
- `run_scale_optimization()` → scale (circle packing).
- `build_and_export()` — **GUI-style scale-only build** (mirrors Action→Build
  Crease Pattern; NO strain opt). Use this as the default build path.
- `run_strain_optimization_and_export()` — scale+strain path (shares
  `BuildAndExport`).
- `debug_poly_report()` — **diagnostic**: after scale-opt, dumps per-leaf-path
  `A`(ctive)/`B`(order)/`F`(easible)/`Poly`gon flags, lengths, leaf positions,
  nPolys, IsPolygonValid. This is how the feasibility-tolerance bug was found.
  (Temp; safe to remove once the layer is solid.)

---

## 2. Regressions fixed (all `treemaker/Source/tmModel/tmTreeClasses/`)

Method that found them all: `git show ad83e7c:<file>` (initial commit) vs HEAD;
the refactor wave rewrote functions and broke them.

1. **`tmPath.cpp::TreePathCalcLengths`** — computed actual paper length as
   `treeLen*scale` (ignoring node positions); restored
   `mActPaperLength = Mag(front->mLoc - back->mLoc)` and paper-space
   active/feasible tests. *Was: every path trivially "active", polygon partition
   never validated.*
2. **`tmPath.cpp::MakeVertex`** (crease split) — built split creases with the
   bare `tmCrease(mTree)` ctor, wiring crease→vertex but not vertex→crease;
   restored the full ctor `tmCrease(tree,owner,v1,v2,kind)`.
3. **`tmPath.cpp::ConnectSelfVertices`** — wrapped `GetOrMakeCrease()`'s
   **tree-owned** return in `std::unique_ptr`, deleting every axial/gusset/hinge
   crease right after creation. *This was the "crease network does not close into
   facets" bug.* Fix: discard the return, do not wrap.
4. **`tmPath.cpp::TestIsFeasible`** — used `TMFLOAT_TOL` (1e-10) where activity
   uses `IsTiny`/`DistTol()` (1e-4); a binding path landing ~1e-7 short came out
   **active-but-infeasible**, and an infeasible path strips polygon-node status
   from both endpoints (`tmTree::CalcPolygonNetwork:2161`) → cascade → 0 polys.
   Fix: `return actLen >= minLen - DistTol();`. *This was THE dominant
   polygon-validity blocker.*

7. **`tmPath.cpp::MakeVertex`** (THIS session) — removed a redundant explicit
   `mOwnedVertices.push_back(theVertex.release())` that double-listed every
   path-owned vertex on top of the `tmVertex` constructor's self-registration.
   The duplicate produced zero-length self-loop creases that corrupted the
   bend/facet-color/fold pipeline. *This was THE flat-foldability blocker — see
   the UPDATE block at the top.* `unique_ptr` ownership was the wrong model here:
   the tree owns all parts via its part hierarchy, not the local scope.

Crash/hang hardening (the original `TMASSERT`/`TMFAIL` guards are compiled out
under `NDEBUG`; **routines reached via `tmTreeCleaner`'s destructor must
`return`, never `throw`** — throwing from a destructor calls `std::terminate`):

5. **`tmCrease.cpp::CalcBend`** — null-guard the `GetAxialOrGussetCreases()`
   result (`return` on null; destructor context).
6. **`tmFacetOwner.cpp::BuildFacetsFromCreases`** — throw on a dead-ended facet
   walk and on `tooMany>=100` (infinite walk), both fwd and bkd loops. (Not in a
   destructor; throw is fine and surfaces as a clean RuntimeError.)
7. **`tmTree_FacetOrder.cpp::CalcFacetOrder`** — when no source facet exists
   (unbroken cycle), set `mIsFacetDataValid = mIsLocalRootConnectable = false`
   and `return`; `CleanupAfterEdit` then early-outs before CalcFacetColor/CalcFold
   (which would deref the unset facet order). Destructor context → no throw.

Also in the working tree (beneficial, keep): **`tmPoint.h`** — removed a leftover
`~tmPoint()` that did `std::cout` on every destruction (would flood stdout, break
the MCP stdio protocol, and cripple performance).

Modified files: `tmPath.cpp`, `tmCrease.cpp`, `tmFacetOwner.cpp`,
`tmTree_FacetOrder.cpp`, `tmPoint.h` (+ wrapper `TreemakerWrapper.cpp`,
`mcp_harness/build.sh` now honors `TM_OPT`). Not committed — the treemaker dir is
a git repo; `git -C treemaker diff` shows them.

---

## 3. Engine pipeline map (where each stage lives)

```
HeadlessTreemaker::BuildAndExport (TreemakerWrapper.cpp)
  tmTree::BuildPolysAndCreasePattern        tmTree.cpp:1760
    BuildTreePolys                          tmTree.cpp:1725  (polygon outlines)
      -> CleanupAfterEdit                   tmTree.cpp:2612  (runs via tmTreeCleaner dtor)
           TreePathCalcLengths (per path)   tmPath.cpp:754   [fix 1] sets A/F
           CalcBorderNodesAndPaths          tmTree.cpp ~2095 sets B
           CalcPolygonNetwork               tmTree.cpp:2134  sets Poly; snips on infeasible [fix 4 critical here]
           CalcPolygonValidity              tmTree.cpp:2225  -> IsPolygonValid()
    for each poly: BuildPolyContents        tmPoly.cpp       <-- MOLECULE: subpolys/ridges/creases
       tmPath::MakeVertex / GetOrMakeVertex tmPath.cpp       [fix 2]
       tmPath::ConnectSelfVertices          tmPath.cpp:471   [fix 3]
       tmFacetOwner::BuildFacetsFromCreases tmFacetOwner.cpp:206 [fix 6]
    -> CleanupAfterEdit again
         CalcDepthAndBend / tmCrease::CalcBend tmCrease.cpp:341 [fix 5]
         CalcFacetOrder                      tmTree_FacetOrder.cpp:515 [fix 7]
            tmPoly::CalcLocalFacetOrder / BuildCorridorLinks  tmPoly.cpp  <-- HANGS on degenerate cases
  ExportFold (vertices_coords + creases->edges)  TreemakerWrapper.cpp
```

`tmPoly.cpp` is git-**untouched** (only the initial commit), so any remaining
defect there is most likely driven by bad data from the `tmPath`/`tmVertex`
helpers it calls — i.e. the same class of regression already seen — rather than
by `tmPoly` itself.

---

## 4. [SUPERSEDED — see the UPDATE block at the top] odd-degree interior vertices

> **This section's diagnosis was WRONG and is kept only for history.** The
> degree-5 vertices below are *border* vertices (Kawasaki-exempt), not interior;
> the genuine interior vertices were already even-degree and Kawasaki-satisfying.
> The real defect was the `tmPath::MakeVertex` double-`push_back` (regression #7),
> now fixed. The actual remaining blocker is **scale-only convergence precision**
> (UPDATE block). Do not chase "odd-degree interior vertices."

**Symptom.** `spine-2branch quad` compiles, but Oriedita reports ~10 vertex
violations (7 Kawasaki / 3 Maekawa). Direct angle measurement of the FOLD:

```
interior vertex   degree   Kawasaki alt-sum (want 0°)
  v4,v5,v9          6        0.00   <- correct, flat-foldable
  v10,v11,v12       (even)   0.00   <- correct
  v2,v3,v7,v8       5        180.0  <- WRONG: odd degree => not flat-foldable
```

So the molecule geometry is **mostly correct** (half the interior vertices
satisfy Kawasaki exactly — rules out a numeric/convergence cause), with a
discrete **topology** defect: some interior vertices come out degree-5. A
flat-foldable interior vertex must have **even** degree. Each bad vertex is
missing (or has one spurious) incident crease.

**Hypothesis.** A missing-crease defect in subpoly / ridge / gusset / hinge
generation inside `tmPoly::BuildPolyContents` and the `tmPath` helpers it calls
(`MakeVertex`, `GetOrMakeVertex`, `ConnectSelfVertices`, and the ridge/hinge
crease creation). Same shape as fix 3 (a crease that should exist isn't being
created or is being dropped). NOT necessarily in `tmPoly.cpp` itself (untouched);
diff the helpers it calls.

**Concrete investigation plan (next session):**
1. Use `debug_poly_report()` plus a NEW diagnostic that, after a successful
   build, dumps every interior `tmVertex`: its location, `mCreases.size()`, and
   each incident crease's `Kind` (axial/gusset/ridge/hinge/pseudohinge) and
   fold. Identify exactly which crease type is missing at the degree-5 vertices.
2. `git diff ad83e7c HEAD` the molecule-construction helpers and compare against
   the crash/fix pattern: `tmPath.cpp` ridge/hinge functions,
   `tmVertex.cpp`/`.h`, and any `GetOrMakeCrease`/`MakeCrease` callers in
   `tmPoly.cpp`'s build path. Look for: (a) more `unique_ptr`-wrapped tree-owned
   returns (premature delete — `grep -rn unique_ptr` in tmTreeClasses; only
   MakeVertex's, which correctly `.release()`s, should remain), (b) loops that
   were re-indexed/range-for'd and now skip an element, (c) dropped
   `vertex->mCreases` back-links.
3. Cross-check against TreeMaker's `change_log.txt` for the expected crease set
   of a known molecule (e.g. a bird-base quadrant) to know the correct degree.
4. Re-run `probe_lint.py`; success = a tree whose FOLD returns "Flat-foldable"
   (or only M/V-fixable, which Oriedita can auto-resolve).

---

## 5. Secondary issues (robustness, lower priority)

- **Infinite loop / hang** in `tmPoly::CalcLocalFacetOrder()` /
  `BuildCorridorLinks()` on degenerate highly-symmetric topologies (e.g. the
  classic 4-flap star = single square poly). Found via `sample <pid>`. Needs a
  bounded-iteration guard, but these run in the `tmTreeCleaner` **destructor**
  path → must set an invalidity flag and `return`, NOT throw. (Server-side spawn
  isolation already turns the hang into a 60s timeout, so it's contained, just
  slow.)
- A few trees still SIGSEGV (`-11`), e.g. `5-leaf caterpillar` scale path — not
  yet localized (`lldb -O0 -g`, drive past the dyld exec stops with `continue`).
- `run_strain_optimization_and_export` is the wrong default (perturbs the
  uniaxial optimum); keep `build_and_export` (scale-only) as primary.

## 6. Diagnostics left in the tree
- `mcp_harness/probe_broad.py` — structured trees, scale-only.
- `mcp_harness/probe_lint.py` — compile (both paths) + Oriedita lint.
- `mcp_harness/probe_scale_only.py`, `probe_trees.py` — earlier sweeps.
- `HeadlessTreemaker::debug_poly_report()` — per-path flag dump (temp).
- lldb recipe: `TM_OPT="-O0 -g" ./build.sh`, then
  `lldb -b -s cmds.txt -- .venv/bin/python repro.py` with cmds = `process
  launch` + several `continue` + `bt`. (Optimized builds mis-symbolicate; always
  reconfirm a crash site with the `-O0 -g` build.)

Related memory: `treemaker-molecule-build-fragility`, `agent-orchestrator-tier2`,
`headless-treemaker-build-recipe`, `oriedita-linter-slice`.

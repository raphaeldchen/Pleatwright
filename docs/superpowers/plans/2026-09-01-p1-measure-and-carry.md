# P1 "Measure and Carry" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure whether the three steering levers this project is about to
build on are real, and land the one data channel they all depend on — per-node
stick orientations — without changing a single served byte.

**Architecture:** Three probes that measure and commit fixtures (M1, M2, M3),
one pure-python module that turns skeleton positions into stick angles (U1a),
one side-channel wiring into `to_metric_tree` (U1b), and one consumer that
turns those angles into packer placement seeds (U6). Everything is additive
and inert by default: with no frame supplied, every code path is byte-identical
to today.

**Tech Stack:** Python 3.14.3, pytest, networkx, numpy, trimesh, skeletor, the
vendored TreeMaker C++ extension via `headless_treemaker`.

**Spec:** [`docs/superpowers/specs/2026-09-01-llm-guided-extraction-design.md`](../specs/2026-09-01-llm-guided-extraction-design.md) — this plan implements **P1 only** (§16: units M1, M2, M3, U1, U6). P2 and P3 are separate plans and must not be started until P1's measurements are in.

## Global Constraints

- **Byte-identity is the gate.** With no `frame=` argument and no
  `orientations`, every served tree, pair list, trace row and receipt must be
  unchanged. Any task that cannot demonstrate this fails.
- **Orientations are never a ranking input.** Nothing in `_serve_rank`,
  `order_rank.rank_key`, any budget, or any exit condition may read them.
  (Spec §8 invariant 3.)
- **Angles are pinned to `vlm_judge._angles`, not reinvented** — azimuth
  `degrees(atan2(v·lateral, v·axial))`, elevation `degrees(asin(v·dorsal/|v|))`,
  both rounded to 1 decimal place. P1 does not edit `vlm_judge.py`.
- **Side channel, never a node field.** No orientation key may appear in any
  node dict that reaches attempt-0 (`rescue_ladder` Rule 2). `to_metric_tree`
  keeps its exact 2-tuple return — there are **35 call sites** that unpack two
  values.
- **Probes measure; they never change a constant.** M2 in particular informs a
  future `MAX_LEAVES` decision and must not make one.
- **Frames are never mixed.** Every orientation record carries
  `"space": "mesh"`; a paper-frame record would be a different thing and P1
  does not produce one.
- **Skip-and-report, never fail-on-missing.** `lizard`, `octopus` and
  `water_bear` meshes are gitignored provider-cache artifacts and are **not in
  a fresh checkout**. Committed `.glb` fixtures are exactly: `bird`, `fish`,
  `humanoid`, `insect`, `quadruped`.

## Setup (once, before Task 1)

This worktree has **no build artifacts and no venv** — they are gitignored, and
this is the documented worktree trap (five artifacts, not one). Run this from
the worktree root. Verified working 2026-09-01.

```bash
MAIN=<repo>
ln -sfn "$MAIN/mcp_harness/.venv" mcp_harness/.venv
ln -sfn "$MAIN/mcp_harness/headless_treemaker.cpython-314-darwin.so" mcp_harness/headless_treemaker.cpython-314-darwin.so
ln -sfn "$MAIN/mcp_harness/OrieditaValidator.class" mcp_harness/OrieditaValidator.class
mkdir -p mcp_harness/oriedita && ln -sfn "$MAIN/mcp_harness/oriedita/oriedita-1.1.3.jar" mcp_harness/oriedita/oriedita-1.1.3.jar
[ -f "$MAIN/.env" ] && ln -sfn "$MAIN/.env" .env
mcp_harness/.venv/bin/python -c "import trimesh, skeletor, networkx, numpy; print('deps ok')"
```

Expected final line: `deps ok`

**The test command used throughout this plan** (verified: 41 passed in 104s):

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/<file> -v --timeout=300
```

⚠ Engine-touching tests are slow (~2s each) and the full suite has been
observed to OOM at ~59% on 7–8 GB. Run per-file, never `tests/` as a whole,
and always pass `--timeout=300`.

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `mcp_harness/probe_reachable_cells.py` | M1: which reachability-table cells actually compile | 1 |
| `mcp_harness/tests/test_reachable_cells.py` | Pins the hit-list logic and the subject→target table | 1 |
| `mcp_harness/fixtures/reachable_cell_compiles.json` | M1 output | 1 |
| `mcp_harness/probe_wide_window.py` | M2: do 9–12-flap trees pack | 2 |
| `mcp_harness/tests/test_wide_window.py` | Pins the star-tree builder | 2 |
| `mcp_harness/fixtures/wide_window_packability.json` | M2 output | 2 |
| `mcp_harness/orientations.py` | U1a: pure stick-angle maths. **math only, no numpy** | 3 |
| `mcp_harness/tests/test_orientations.py` | Pins angles to `vlm_judge._angles` | 3 |
| `mcp_harness/mesh_to_tree.py` | U1b: `frame_from_mesh`, `_last_orientations`, `frame=` kwarg, search capture, `MeshTreeResult.orientations` | 4 |
| `mcp_harness/tests/test_orientation_channel.py` | Byte-identity + channel population | 4 |
| `mcp_harness/rescue_ladder.py` | U6: `orientation_layout` + `placement_variants` hook | 5 |
| `mcp_harness/tests/test_orientation_placement.py` | Pins seed geometry and the empty-input fallback | 5 |
| `mcp_harness/probe_orientation_placement.py` | M3: A/B vs golden-angle and `structural_layout` | 6 |
| `mcp_harness/fixtures/orientation_placement_ab.json` | M3 output + ship verdict | 6 |

---

### Task 1: M1 — do the reachable cells actually compile?

`fixtures/extraction_fate.json` records extraction only. Its own `_meta` says:
*"A cell recorded here is not thereby packable or servable."* Class 1 of the
spec rests entirely on one bird cell, (voxel 192, prune 0.40). This task finds
out whether it packs.

**Files:**
- Create: `mcp_harness/probe_reachable_cells.py`
- Create: `mcp_harness/tests/test_reachable_cells.py`
- Output: `mcp_harness/fixtures/reachable_cell_compiles.json`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `probe_reachable_cells.SUBJECT_TARGETS` (dict: fate-subject key →
  `(anatomy_expectation row key, int expected count)`) and
  `probe_reachable_cells.hit_cells(fate_doc, targets=SUBJECT_TARGETS) -> list[dict]`
  where each dict has keys `subject`, `voxel_res`, `prune`, `target`,
  `in_shipped_grid`. Task 6 imports `hit_cells`.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_reachable_cells.py`:

```python
"""M1: the reachability hit list, and the targets it is measured against.

`extraction_fate.json` is extraction-only. This pins the pure part -- WHICH
cells claim the correct anatomy -- so the probe's compile results can be read
against a hit list nobody can quietly redefine.
"""
import json
import os

import probe_reachable_cells as prc

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FATE_PATH = os.path.join(HERE, "fixtures", "extraction_fate.json")
EXPECT_PATH = os.path.join(HERE, "fixtures", "anatomy_expectation.json")


def _fate():
    with open(FATE_PATH) as fh:
        return json.load(fh)


def test_every_target_matches_the_authored_anatomy_row_it_cites():
    """The two files must not drift. Same discipline as
    test_hub_degree_notice_matches_the_extractor."""
    with open(EXPECT_PATH) as fh:
        table = json.load(fh)
    for subject, (row, count) in prc.SUBJECT_TARGETS.items():
        assert row in table, f"{subject} cites missing row {row!r}"
        assert table[row]["expected_feature_count"] == count, subject


def test_bird_has_exactly_one_hit_and_it_is_outside_the_shipped_grid():
    hits = [h for h in prc.hit_cells(_fate()) if h["subject"] == "bird"]
    assert len(hits) == 1, hits
    assert (hits[0]["voxel_res"], hits[0]["prune"]) == (192, 0.4)
    assert hits[0]["in_shipped_grid"] is False


def test_lizard_is_unreachable_anywhere_in_the_grid():
    """The impossibility proof Class 3 rests on. If this ever passes with a
    non-empty list, the spec's Class 3 claim is void and must be re-argued."""
    assert [h for h in prc.hit_cells(_fate()) if h["subject"] == "lizard"] == []


def test_octopus_and_water_bear_hits_exist_inside_the_shipped_grid():
    """Class 2: reachable, then rejected by MAX_LEAVES=8 -- so the hits must
    really be there, or Class 2 is a different problem than the spec says."""
    hits = prc.hit_cells(_fate())
    for subject in ("octopus", "water_bear"):
        inside = [h for h in hits
                  if h["subject"] == subject and h["in_shipped_grid"]]
        assert inside, subject
        assert all(h["target"] > prc.MAX_LEAVES_AT_WRITING for h in inside)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_reachable_cells.py -v --timeout=300
```

Expected: FAIL, `ModuleNotFoundError: No module named 'probe_reachable_cells'`

- [ ] **Step 3: Write the module**

Create `mcp_harness/probe_reachable_cells.py`:

```python
"""M1: which reachability cells actually COMPILE.

`fixtures/extraction_fate.json` sweeps 8 voxels x 8 prunes x 8 subjects and
records leaf counts. Its own _meta is explicit that this is extraction only:
"A cell recorded here is not thereby packable or servable." The spec's Class 1
(grid coverage) rests on ONE bird cell, so this probe recompiles every cell
whose leaf count equals the subject's authored anatomy and records what the
serve path does with it.

⚠ THE HIT LIST IS NECESSARY, NOT SUFFICIENT. Leaf count is a count: the repo's
own record has a lizard whose anatomy was correct at FOUR leaves and a horse
that served 8 leaves with 0 pairs and 6 unclassified limbs. A miss proves the
anatomy wrong; a hit proves nothing. This probe measures packability of the
hits, not their correctness.

Run:
    cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_reachable_cells.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
FATE_PATH = os.path.join(HERE, "fixtures", "extraction_fate.json")
OUT_PATH = os.path.join(HERE, "fixtures", "reachable_cell_compiles.json")

#: The packable window's upper bound AT THE TIME THIS PROBE WAS WRITTEN.
#: A literal, deliberately NOT an import of mesh_to_tree.MAX_LEAVES: this
#: probe's Class-2 claim is a statement about the window as it stood when the
#: measurement was taken, and it must not silently re-interpret itself if the
#: constant later moves. tests/test_wide_window.py pins the two equal for as
#: long as they ARE equal.
MAX_LEAVES_AT_WRITING = 8

#: fate-fixture subject key -> (anatomy_expectation.json row key, count).
#: `fish` and `insect` are deliberately absent: neither has an authored row,
#: and inventing one here would be the closed loop this whole design exists to
#: break. `quadruped` cites `dog` because the authored dog/cat/horse rows all
#: read 6 (4 legs + head + tail) and quadruped.glb is that body plan.
SUBJECT_TARGETS = {
    "bird": ("bird", 6),
    "humanoid": ("human", 5),
    "lizard": ("lizard", 6),
    "octopus": ("octopus", 9),
    "quadruped": ("dog", 6),
    "water_bear": ("water bear", 9),
}

#: Committed .glb fixtures. Everything else is a gitignored provider-cache
#: artifact that a fresh checkout does not have -- the probe SKIPS those and
#: says so rather than failing, because "we could not look" and "we looked and
#: found nothing" must not share a message.
COMMITTED_MESHES = ("bird", "fish", "humanoid", "insect", "quadruped")


def hit_cells(fate_doc, targets=SUBJECT_TARGETS):
    """[{subject, voxel_res, prune, target, in_shipped_grid}] -- every cell
    whose extracted leaf count equals the subject's authored anatomy count.

    Sorted by (subject, voxel_res, prune) so the output is stable.
    """
    meta = fate_doc["_meta"]
    prunes = meta["prunes"]
    shipped = set(meta["shipped_voxel_grid"])
    out = []
    for subject in sorted(targets):
        target = targets[subject][1]
        cells = (fate_doc["meshes"].get(subject) or {}).get("cells") or {}
        for voxel in sorted(cells, key=int):
            curve = cells[voxel].get("leaf_by_prune") or {}
            for prune in prunes:
                if curve.get(str(prune)) == target:
                    out.append({
                        "subject": subject,
                        "voxel_res": int(voxel),
                        "prune": prune,
                        "target": target,
                        "in_shipped_grid": int(voxel) in shipped,
                    })
    return out


def _mesh_path(subject):
    """The .glb for a fate subject, or None when it is not committed."""
    if subject not in COMMITTED_MESHES:
        return None
    path = os.path.join(HERE, "fixtures", f"{subject}.glb")
    return path if os.path.isfile(path) else None


def compile_cell(subject, voxel_res, prune):
    """Run the SERVE PATH on one cell and report what happened.

    `mesh_to_tree._default_compile_fn` is used deliberately rather than a bare
    compile: it suppresses the root-rank and MV-symmetrize stages exactly as
    the extraction search does, so the answer is about the path that would
    actually serve this tree.
    """
    import mesh_to_tree as m2t
    import paper_coverage

    path = _mesh_path(subject)
    if path is None:
        return {"status": "skipped",
                "reason": "mesh is a gitignored provider-cache artifact, "
                          "not present in a fresh checkout"}
    mesh = m2t.load_mesh(path, voxel_res)
    tree = m2t.simplify_to_tree(m2t.extract_skeleton(mesh), prune)
    if tree.number_of_edges() == 0:
        return {"status": "empty", "reason": "over-pruned: no edges"}
    sym = m2t.detect_symmetry(tree, mesh)
    nodes, pairs = m2t.to_metric_tree(tree, sym)

    # ONE compile, and everything read off its result. `compiles_to_fold`
    # discards the FOLD string, so calling it and THEN recompiling for coverage
    # would pay for the packer twice per cell -- and would compare two separate
    # engine runs, which is a worse measurement even where they agree.
    fold = m2t._default_compile_fn(nodes, pairs)
    ok = not fold.startswith("ERROR:") and '"vertices_coords"' in fold
    return {"status": "compiled" if ok else "failed",
            "leaves": m2t._leaf_count(nodes),
            "pairs": len(pairs),
            "stage": m2t.served_stage(fold) if ok else None,
            "stub_flaps": m2t.served_stub_flaps(fold) if ok else 0,
            "compile_error": None if ok else fold,
            "prefilter": m2t.structural_prefilter(nodes),
            "hull_coverage": (paper_coverage.coverage_of_fold_str(fold)
                              if ok else None)}


def main():
    with open(FATE_PATH) as fh:
        fate = json.load(fh)
    hits = hit_cells(fate)
    rows = []
    for hit in hits:
        result = compile_cell(hit["subject"], hit["voxel_res"], hit["prune"])
        rows.append(dict(hit, **result))
        print(f"{hit['subject']:11} v{hit['voxel_res']:<4} p{hit['prune']:<5} "
              f"-> {result.get('status')} "
              f"leaves={result.get('leaves')} stage={result.get('stage')} "
              f"stubs={result.get('stub_flaps')}")
    doc = {"_meta": {
        "generated_by": "probe_reachable_cells.py",
        "what": "Serve-path compile result for every extraction_fate cell "
                "whose leaf count equals the subject's AUTHORED anatomy count.",
        "caveat": "A hit is a COUNT match, not an anatomy match. Necessary, "
                  "not sufficient -- see the module docstring.",
        "max_leaves_at_writing": MAX_LEAVES_AT_WRITING,
    }, "rows": rows}
    with open(OUT_PATH, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    print(f"\nwrote {OUT_PATH} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_reachable_cells.py -v --timeout=300
```

Expected: PASS, 4 passed

- [ ] **Step 5: Run the probe and read the result**

```bash
cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_reachable_cells.py
```

Expected: a line per hit cell. `octopus`, `water_bear` and `lizard` rows print
`skipped`. The bird's `v192 p0.4` row is **the decision**.

- [ ] **Step 6: Record the ship verdict for U4 in the fixture's `_meta`**

Add a `"u4_verdict"` key to the written `_meta` stating, in one sentence,
whether the pre-registered bar was met: **U4 ships only if ≥1 Class-1 cell
compiled on ≥1 subject with `stub_flaps == 0`.** Write what the run said,
including "not met" if it was not met.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/probe_reachable_cells.py mcp_harness/tests/test_reachable_cells.py mcp_harness/fixtures/reachable_cell_compiles.json
git commit -m "probe(M1): do the reachability-table cells actually compile"
```

---

### Task 2: M2 — do 9–12-flap trees pack at all?

Class 2 (octopus, water bear) is worth nothing if the engine cannot pack nine
flaps and everything if it can. `fixtures/s5_engine_repair_evidence.json →
packability_control` already holds k-leaf star rates through k=8 (3/3 at 0%
jitter, 7/20 at 30%). This extends the same control upward.

**Files:**
- Create: `mcp_harness/probe_wide_window.py`
- Create: `mcp_harness/tests/test_wide_window.py`
- Output: `mcp_harness/fixtures/wide_window_packability.json`

**Interfaces:**
- Consumes: **Task 1** — `probe_reachable_cells.hit_cells`, `.compile_cell`,
  `.FATE_PATH`, `.MAX_LEAVES_AT_WRITING`. Task 1 must be complete first.
- Produces: `probe_wide_window.star_tree(k) -> list[dict]` returning
  `[{"id": 0, "parent_id": None, "length": 0}, {"id": i, "parent_id": 0,
  "length": 0.4}, ...]` for `i` in `1..k`.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_wide_window.py`:

```python
"""M2: the k-leaf star control, extended above the packable window."""
import probe_wide_window as pww
import mesh_to_tree as m2t
import rescue_ladder


def test_star_tree_has_one_root_and_k_leaves():
    nodes = pww.star_tree(9)
    assert len(nodes) == 10
    roots = [n for n in nodes if n["parent_id"] is None]
    assert len(roots) == 1 and roots[0]["id"] == 0
    assert m2t._leaf_count(nodes) == 9


def test_star_tree_leaf_lengths_are_all_equal():
    """Equal lengths is the CONTROL condition -- s5_engine_repair_evidence's
    packability_control measures jitter AGAINST this baseline, so a star with
    unequal lengths would not be comparable to the committed k<=8 rows."""
    nodes = pww.star_tree(11)
    lengths = {n["length"] for n in nodes if n["parent_id"] is not None}
    assert lengths == {0.4}


def test_star_tree_is_well_formed_for_the_ladder():
    assert rescue_ladder.root_id(pww.star_tree(12)) == 0


def test_the_window_literal_still_matches_the_extractor():
    """probe_reachable_cells pins MAX_LEAVES as a literal on purpose. While the
    two ARE equal, assert it -- so the day the constant moves, the probe's
    Class-2 wording gets re-read rather than silently re-interpreted."""
    import probe_reachable_cells as prc
    assert prc.MAX_LEAVES_AT_WRITING == m2t.MAX_LEAVES
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_wide_window.py -v --timeout=300
```

Expected: FAIL, `ModuleNotFoundError: No module named 'probe_wide_window'`

- [ ] **Step 3: Write the module**

Create `mcp_harness/probe_wide_window.py`:

```python
"""M2: does the engine pack 9-12 flaps?

The spec's Class 2 (octopus, water bear) is that the correct anatomy IS
extracted -- 9 leaves at voxel 64, inside the shipped grid -- and is then
rejected by structural_prefilter because MAX_LEAVES = 8. That rejection is
only worth revisiting if the engine can actually pack nine flaps.

⚠ THIS PROBE CHANGES NO CONSTANT. It measures. Loosening a gate to reach a
headline is this project's named recurring failure mode, and the MAX_LEAVES
decision belongs to its own spec with its own argument. fidelity_score's clamp
drives the terminal early-exit and not merely ranking, so moving the window
re-times the search on fish and insect as a side effect.

Run:
    cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_wide_window.py
"""
import json
import os

import error_recipes
import probe_broad

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "fixtures", "wide_window_packability.json")

#: Matches the committed packability_control's flap length so the new rows are
#: comparable to the k<=8 rows already on disk.
LEAF_LENGTH = 0.4

#: Trials per (k, jitter) cell. 20 matches the committed control's own depth.
TRIALS = 20

JITTERS = (0.0, 0.01, 0.30)
KS = (9, 10, 11, 12)


def star_tree(k):
    """A k-leaf star: one root, k equal-length children. This IS a k-child
    root, which is the shape the retired 'root>4 reliably fails' rule claimed
    could not pack -- tree_contract.py records that refutation."""
    nodes = [{"id": 0, "parent_id": None, "length": 0}]
    for i in range(1, k + 1):
        nodes.append({"id": i, "parent_id": 0, "length": LEAF_LENGTH})
    return nodes


def _jittered(nodes, frac, rng):
    out = []
    for n in nodes:
        n = dict(n)
        if n["parent_id"] is not None and frac:
            n["length"] = round(n["length"] * (1.0 + rng.uniform(-frac, frac)), 6)
        out.append(n)
    return out


def star_control_raw():
    """{k: {jitter: {"ok", "n", "fail_classes"}}} -- THE COMPARABLE ARM.

    ⚠ THIS IS THE ONLY ARM THAT EXTENDS THE COMMITTED CONTROL. The k<=8 rows in
    `fixtures/s5_engine_repair_evidence.json -> packability_control` were
    measured with a GUI-style scale-only build -- init_paper,
    build_tree_from_json, apply_symmetry, run_scale_optimization,
    build_and_export -- which is why every failing cell there carries a
    `fail_classes` histogram of raw compiler errors (FACETS_NOT_VALID,
    POLYS_MULTIPLE_IBPS). `probe_broad.run` is that path, in a spawned child so
    a crash costs one trial.

    MEASURED 2026-09-01, and this is why the arms are separated: at k=4 /
    jitter 0.01 the committed raw control reads 2/20 while the LADDERED path
    below reads 10/10 on the same tree, jitter and seeds. The two are different
    quantities and putting them in one table would have made the k=9..12 rows
    read as a packer result when they are a rescue result.
    """
    import random
    out = {}
    for k in KS:
        base = star_tree(k)
        row = {}
        for jitter in JITTERS:
            rng = random.Random(f"{k}:{jitter}")
            trials = 1 if jitter == 0.0 else TRIALS
            ok, fails = 0, {}
            for _ in range(trials):
                status, detail, _fold = probe_broad.run(
                    _jittered(base, jitter, rng), [])
                if status == "ok":
                    ok += 1
                else:
                    cls = _fail_class(status, detail)
                    fails[cls] = fails.get(cls, 0) + 1
            row[str(jitter)] = {"ok": ok, "n": trials, "fail_classes": fails}
        out[str(k)] = row
        print(f"raw   k={k}: "
              + " ".join(f"{j}:{c['ok']}/{c['n']}" for j, c in row.items()))
    return out


def _fail_class(status, detail):
    """The failure's canonical code, via THIS REPO'S OWN vocabulary.

    ⚠ DO NOT REPLACE THIS WITH A PRIVATE TOKEN LIST. An earlier revision did
    exactly that -- a five-name `if name in detail` scan with an "OTHER"
    fallback -- and "OTHER" became the LARGEST bucket at k=9 (11 of 20),
    silently swallowing `polygon network is not valid after optimization ...
    the active-path network does not ...`. `error_recipes._MATCHERS` already
    carries that string, plus PROJECTION_UNSUPPORTED and PROJECTION_INVALID
    which the same list would also have swallowed.

    A non-"err" status is returned unchanged so a timeout or a crash is never
    counted as a compile failure of the same kind, and an unmatched error is
    "UNCLASSIFIED" rather than "OTHER" -- the classifier had no code for it,
    which is a different statement from "some residual category".
    """
    if status != "err":
        return status                       # "timeout" / "crash"
    code = error_recipes.classify(detail)
    return code if code is not None else "UNCLASSIFIED"


def star_control_laddered():
    """{k: {jitter: "packed/trials"}} -- THE SERVE-PATH ARM.

    `_default_compile_fn` runs the full rescue ladder (order, placement,
    normalize, jitter, composed, stub), so this answers "would our serve path
    DELIVER a k-flap base", not "can the packer pack one". Both questions bear
    on a future MAX_LEAVES decision and they have different answers; neither is
    a substitute for the other, and NEITHER IS COMPARABLE TO THE COMMITTED
    k<=8 ROWS except through `star_control_raw` above.
    """
    import random
    import mesh_to_tree as m2t
    out = {}
    for k in KS:
        base = star_tree(k)
        row = {}
        for jitter in JITTERS:
            rng = random.Random(f"{k}:{jitter}")
            trials = 1 if jitter == 0.0 else TRIALS
            packed = 0
            for _ in range(trials):
                nodes = _jittered(base, jitter, rng)
                ok, _err, _stage, _stub = m2t.compiles_to_fold(
                    nodes, [], m2t._default_compile_fn)
                packed += 1 if ok else 0
            row[str(jitter)] = f"{packed}/{trials}"
        out[str(k)] = row
        print(f"ladder k={k}: {row}")
    return out


def real_wide_trees():
    """Compile the ACTUAL >8-leaf cells M1 listed, through the full ladder.

    A star is a control, not an animal: it has no pairs and no interior
    structure, so it cannot answer whether a real 9-leaf octopus packs. Cells
    whose mesh is not committed are skipped and say so.
    """
    import probe_reachable_cells as prc
    with open(prc.FATE_PATH) as fh:
        fate = json.load(fh)
    rows = []
    for hit in prc.hit_cells(fate):
        if hit["target"] <= prc.MAX_LEAVES_AT_WRITING:
            continue
        result = prc.compile_cell(hit["subject"], hit["voxel_res"],
                                  hit["prune"])
        rows.append(dict(hit, **result))
        print(f"{hit['subject']:11} v{hit['voxel_res']:<4} "
              f"p{hit['prune']:<5} -> {result.get('status')}")
    return rows


def main():
    doc = {"_meta": {
        "generated_by": "probe_wide_window.py",
        "what": "k-leaf star pack rates for k=9..12 on TWO arms, plus "
                "serve-path compiles of the real >8-leaf cells the "
                "reachability table lists.",
        "arms": {
            "star_control_raw": "GUI-style scale-only build via "
                "probe_broad.run. THE ONLY ARM COMPARABLE to the committed "
                "k<=8 rows in s5_engine_repair_evidence.json -> "
                "packability_control, measured the same way and carrying the "
                "same fail_classes histogram.",
            "star_control_laddered": "the full serve path via "
                "mesh_to_tree._default_compile_fn, i.e. WITH the rescue "
                "ladder. Answers what production would deliver. NOT "
                "comparable to the committed rows.",
        },
        "why_two_arms": "Measured 2026-09-01 at k=4 / jitter 0.01: the "
                        "committed raw value is 2/20 and the laddered arm "
                        "reads 10/10 on the same tree, jitter and seeds. One "
                        "table holding both without saying so would read as a "
                        "packer result when it is a rescue result.",
        "changes_no_constant": True,
        "leaf_length": LEAF_LENGTH,
        "trials": TRIALS,
    },
        "star_control_raw": star_control_raw(),
        "star_control_laddered": star_control_laddered(),
        "real_wide_trees": real_wide_trees()}
    with open(OUT_PATH, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    print(f"\nwrote {OUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_wide_window.py -v --timeout=300
```

Expected: PASS, 4 passed

- [ ] **Step 5: Run the probe**

```bash
cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_wide_window.py
```

Expected: a `k=9..12` line each, then the real-tree rows (all `skipped` in a
fresh checkout — the >8-leaf subjects are octopus and water bear, neither
committed). The star rows are the durable result.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/probe_wide_window.py mcp_harness/tests/test_wide_window.py mcp_harness/fixtures/wide_window_packability.json
git commit -m "probe(M2): k-leaf star pack rates above the packable window"
```

---

### Task 3: U1a — the orientations module

Pure stick-angle maths. No numpy, no trimesh — `math` and tuples only, the
same discipline `pose_target.py` states ("Deliberately import-light") and the
same primitives `vlm_judge` uses, so the pinning test in Step 1 is a direct
comparison rather than a translation.

**Files:**
- Create: `mcp_harness/orientations.py`
- Create: `mcp_harness/tests/test_orientations.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `orientations.Frame` — `namedtuple("Frame", "origin axial lateral dorsal")`,
    each field a 3-tuple of floats.
  - `orientations.angles(vec, frame) -> tuple[float, float] | None` —
    `(azimuth, elevation)` in degrees, 1 d.p.; `None` for a zero vector.
  - `orientations.stick_orientations(positions, parent_of, frame) -> dict` —
    `{node_id: {"azimuth": float, "elevation": float, "space": "mesh"}}`, one
    entry per node that has a parent and a measurable stick.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_orientations.py`:

```python
"""U1a: stick orientations, pinned to the judge's existing angle convention."""
import math

import pytest

import orientations as orient
import vlm_judge

FRAME = orient.Frame(origin=(0.0, 0.0, 0.0),
                     axial=(1.0, 0.0, 0.0),
                     lateral=(0.0, 1.0, 0.0),
                     dorsal=(0.0, 0.0, 1.0))

_VECTORS = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
            (1.0, 1.0, 0.0), (-1.0, 0.0, 0.0), (0.0, -1.0, 0.0),
            (2.0, -3.0, 1.5), (-0.4, 0.25, -0.9), (1e-3, 1e-3, 1e-3)]


@pytest.mark.parametrize("vec", _VECTORS)
def test_angles_agree_bit_for_bit_with_the_judge(vec):
    """THE PINNING TEST. One stick must never get two different numbers from
    two parts of this repo. If vlm_judge._angles changes, this fails loudly
    rather than the two silently disagreeing in a payload."""
    assert orient.angles(vec, FRAME) == vlm_judge._angles(
        vec, FRAME.axial, FRAME.lateral, FRAME.dorsal)


def test_axial_direction_is_azimuth_zero_elevation_zero():
    assert orient.angles((3.0, 0.0, 0.0), FRAME) == (0.0, 0.0)


def test_lateral_direction_is_azimuth_ninety():
    az, el = orient.angles((0.0, 2.0, 0.0), FRAME)
    assert az == 90.0 and el == 0.0


def test_dorsal_direction_is_elevation_ninety():
    _az, el = orient.angles((0.0, 0.0, 2.0), FRAME)
    assert el == 90.0


def test_zero_vector_has_no_angle():
    assert orient.angles((0.0, 0.0, 0.0), FRAME) is None


def test_stick_orientations_measures_the_stick_not_the_tip():
    """The whole point of the channel: vlm_judge measures a tip from the tip
    centroid because internal joints have no measured position on the serve
    path. Here every node has one, so a child offset LATERALLY from its parent
    reads azimuth 90 even though its absolute position is mostly axial."""
    positions = {0: (0.0, 0.0, 0.0), 1: (5.0, 0.0, 0.0), 2: (5.0, 1.0, 0.0)}
    got = orient.stick_orientations(positions, {1: 0, 2: 1}, FRAME)
    assert got[1]["azimuth"] == 0.0
    assert got[2]["azimuth"] == 90.0


def test_root_gets_no_orientation_and_every_record_names_its_space():
    positions = {0: (0.0, 0.0, 0.0), 1: (1.0, 0.0, 0.0)}
    got = orient.stick_orientations(positions, {1: 0}, FRAME)
    assert 0 not in got
    assert got[1]["space"] == "mesh"


def test_a_zero_length_stick_is_omitted_not_guessed():
    positions = {0: (0.0, 0.0, 0.0), 1: (0.0, 0.0, 0.0)}
    assert orient.stick_orientations(positions, {1: 0}, FRAME) == {}


def test_a_node_with_a_missing_position_is_omitted():
    positions = {0: (0.0, 0.0, 0.0)}
    assert orient.stick_orientations(positions, {1: 0}, FRAME) == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientations.py -v --timeout=300
```

Expected: FAIL, `ModuleNotFoundError: No module named 'orientations'`

- [ ] **Step 3: Write the module**

Create `mcp_harness/orientations.py`:

```python
"""U1a: per-stick orientation, in the figure's own frame.

WHY THIS EXISTS. Three sites in this repo already reach for a per-node
orientation and do not find one:

  * `mesh_to_tree.extract_skeleton` puts a 3-D `pos` on every skeleton node,
    `detect_symmetry` and `label_leaves` both read it, and `to_metric_tree`
    emits {id, parent_id, length} and never reads it at all. The only survivor
    is `leaf_labels[id]["position"]` -- leaf TIPS only.
  * `TreemakerWrapper.cpp:254` places every unseeded node on a golden-angle
    spiral at `2.39996 * list index`. That is the mechanism behind the node-
    ORDER lever (bird hull coverage 0.5000 -> 0.9848), which means the ladder's
    order restarts are a blind search over ARBITRARY angular assignments.
  * `vlm_judge.build_payload` emits azimuth/elevation opportunistically and
    carries an `angle_coverage` block whose job is to confess how few sticks
    got one.

⚠ THE MATHS IS NOT OURS AND MUST NOT DRIFT. `vlm_judge._angles` already
defines the convention. `angles()` below is pinned to it bit-for-bit by
tests/test_orientations.py rather than reimplemented on faith, because one
stick reported with two different numbers by two parts of this repo is worse
than no number at all.

⚠ THE VECTOR *IS* OURS, AND IT IS THE POINT. `vlm_judge` measures each flap tip
from the centroid of the tips, because on the serve path an internal joint has
no measured position. This module runs at EXTRACTION time, where every node
does, so it measures the STICK -- `pos[child] - pos[parent]`. A tip-from-centre
bearing and a stick direction are different quantities and are never mixed.

Import-light on purpose (`math` only, no numpy): the whole contract is unit-
testable with plain tuples, the same discipline `pose_target.py` states.
"""
from __future__ import annotations

import math
from collections import namedtuple

#: The frame angles are measured in. `axial` is the body axis (azimuth 0),
#: `lateral` is left/right (azimuth +/-90), `dorsal` completes them
#: (elevation +/-90). Signs are arbitrary and carry no anatomical up or front
#: -- exactly the caveat `vlm_judge._figure_frame` prints for its own frame.
Frame = namedtuple("Frame", "origin axial lateral dorsal")

#: Below this the stick has no direction to report.
_EPS = 1e-9

#: The one space this module produces. A paper-frame bearing is a different
#: quantity (a direction on the SHEET, not on the animal) and mixing the two
#: under one key is the failure `vlm_judge.py:1139` already guards against.
SPACE = "mesh"


def _dot(a, b) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub(a, b) -> tuple:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def angles(vec, frame: Frame):
    """(azimuth, elevation) in degrees to 1 d.p., or None for a null vector.

    PINNED to `vlm_judge._angles`; see the module docstring.
    """
    n = math.sqrt(_dot(vec, vec))
    if n < _EPS:
        return None
    return (round(math.degrees(math.atan2(_dot(vec, frame.lateral),
                                          _dot(vec, frame.axial))), 1),
            round(math.degrees(math.asin(
                max(-1.0, min(1.0, _dot(vec, frame.dorsal) / n)))), 1))


def stick_orientations(positions, parent_of, frame: Frame) -> dict:
    """{node_id: {"azimuth", "elevation", "space"}} -- one per measurable stick.

    A node is OMITTED, never guessed, when it has no parent (the root), when
    either endpoint has no position, or when the stick has no length. An
    omission is readable downstream as "not measured"; a fabricated angle is
    not, and `_root_path_length` already sets that precedent for a dangling
    parent.
    """
    out = {}
    for child, parent in parent_of.items():
        if child not in positions or parent not in positions:
            continue
        got = angles(_sub(positions[child], positions[parent]), frame)
        if got is None:
            continue
        out[child] = {"azimuth": got[0], "elevation": got[1], "space": SPACE}
    return out
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientations.py -v --timeout=300
```

Expected: PASS, 17 passed (9 parametrised pin cases + 8 behaviour cases)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/orientations.py mcp_harness/tests/test_orientations.py
git commit -m "feat(U1a): per-stick orientations, pinned to the judge's angle convention"
```

---

### Task 4: U1b — wire the side channel

`to_metric_tree` keeps its exact 2-tuple return (35 call sites unpack two
values) and publishes on a module global, the pattern `_last_pair_evidence`
and `_last_pre_root_children` already establish in this file.

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py` — add `_last_orientations` beside
  `_last_pre_root_children` (~line 110); add `frame_from_mesh`; add
  `frame=None` keyword-only param to `to_metric_tree` (line 1434); capture in
  the search loop beside `pair_ev` (~line 2819); add
  `MeshTreeResult.orientations` (~line 600) and populate it in `_confirmed`.
- Modify: `mcp_harness/tests/test_mesh_report.py:391-411` — `_patch_forest_pipeline`
  stubs `to_metric_tree`; see Step 3e.
- Create: `mcp_harness/tests/test_orientation_channel.py`

⚠ **A KEYWORD-ONLY PARAMETER IS INVISIBLE TO CALLERS AND VISIBLE TO DOUBLES.**
The 35 call sites that *call* `to_metric_tree` are unaffected. A test that
*replaces* it is not: `tests/test_mesh_report.py` monkeypatches it with
`lambda t, sym: (emitted, [])`, and the search loop's `frame=frame` call raises
`TypeError` against that stub on 5 tests. Measured — this exact failure blocked
the first attempt at this task, and the gate caught it. Step 3e is the fix, and
it follows a convention the file already documents rather than inventing one.

**Interfaces:**
- Consumes: `orientations.Frame`, `orientations.stick_orientations` (Task 3).
- Produces:
  - `mesh_to_tree._last_orientations: dict` — same shape
    `stick_orientations` returns, keyed by **EMITTED** node id, reset on every
    `to_metric_tree` call.
  - `mesh_to_tree.frame_from_mesh(tree, mesh) -> orientations.Frame`
    (**note the argument order: `tree` first**, matching `label_leaves`'s own
    `(tree, mesh, ...)` order in this module)
  - `mesh_to_tree.to_metric_tree(tree, sym, *, frame=None)`
  - `MeshTreeResult.orientations: dict` (default `{}`)

⚠ **NAME COLLISION, AND IT IS WHY EVERY IMPORT BELOW IS LOCAL.**
`MeshTreeResult` gains a field called `orientations` and the new module is also
called `orientations`. A module-level `import orientations` in
`mesh_to_tree.py` would be shadowed by nothing today — but the two names
reading identically in one file is exactly how a later edit introduces a real
bug. Import it **inside** `frame_from_mesh` and inside `to_metric_tree`, as
written in Steps 3b and 3c, and never at module scope.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_orientation_channel.py`:

```python
"""U1b: the orientations side channel, and the byte-identity it must preserve."""
import networkx as nx

import mesh_to_tree as m2t
import orientations as orient

FRAME = orient.Frame(origin=(0.0, 0.0, 0.0), axial=(1.0, 0.0, 0.0),
                     lateral=(0.0, 1.0, 0.0), dorsal=(0.0, 0.0, 1.0))


def _tree():
    """A 4-leaf figure: hub 0 at the origin, two lateral limbs, two axial."""
    g = nx.Graph()
    for nid, pos in {0: (0.0, 0.0, 0.0), 1: (0.0, 4.0, 0.0),
                     2: (0.0, -4.0, 0.0), 3: (6.0, 0.0, 0.0),
                     4: (-6.0, 0.0, 0.0)}.items():
        g.add_node(nid, pos=list(pos))
    for a, b, w in ((0, 1, 4.0), (0, 2, 4.0), (0, 3, 6.0), (0, 4, 6.0)):
        g.add_edge(a, b, length=w)
    return g


def test_no_frame_means_no_orientations_and_an_unchanged_return():
    nodes, pairs = m2t.to_metric_tree(_tree(), [])
    assert isinstance(nodes, list) and isinstance(pairs, list)
    assert m2t._last_orientations == {}


def test_a_frame_populates_the_channel_keyed_by_EMITTED_id():
    tree = _tree()
    nodes, _pairs = m2t.to_metric_tree(tree, [], frame=FRAME)
    emitted = {n["id"] for n in nodes}
    assert m2t._last_orientations
    assert set(m2t._last_orientations) <= emitted
    root = next(n["id"] for n in nodes if n["parent_id"] is None)
    assert root not in m2t._last_orientations


def test_the_channel_is_reset_between_calls():
    """`_last_*` promises what the LAST call did. A stale channel would
    attribute one cell's angles to a different cell -- the exact failure
    to_metric_tree already guards against for _last_pair_evidence."""
    m2t.to_metric_tree(_tree(), [], frame=FRAME)
    assert m2t._last_orientations
    m2t.to_metric_tree(_tree(), [])
    assert m2t._last_orientations == {}


def test_orientations_never_ride_in_the_node_dicts():
    """rescue_ladder Rule 2, applied to this channel. A node dict carrying an
    angle would change the candidate dedup key (mesh_to_tree.py:2970) and the
    capture corpus (server.py:2683)."""
    nodes, _pairs = m2t.to_metric_tree(_tree(), [], frame=FRAME)
    for n in nodes:
        assert set(n) == {"id", "parent_id", "length"}, n


def test_lateral_and_axial_limbs_read_different_azimuths():
    """ANTI-VACUITY: a channel that reports the same angle for every stick is
    a field that cannot vary, which base_eval's rule exists to reject."""
    tree = _tree()
    m2t.to_metric_tree(tree, [], frame=FRAME)
    azimuths = {round(v["azimuth"]) for v in m2t._last_orientations.values()}
    assert len(azimuths) >= 3, azimuths


def test_mesh_tree_result_defaults_to_an_empty_channel():
    r = m2t.MeshTreeResult(confirmed=False, nodes=[], pairs=[], voxel_res=96,
                           prune_fraction=0.4, gate={})
    assert r.orientations == {}
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientation_channel.py -v --timeout=300
```

Expected: FAIL, `AttributeError: module 'mesh_to_tree' has no attribute '_last_orientations'`

- [ ] **Step 3a: Add the module global**

In `mcp_harness/mesh_to_tree.py`, immediately after the
`_last_pre_root_children` declaration (~line 112), add:

```python
#: Per-call stick orientations from the last `to_metric_tree`, keyed by
#: EMITTED node id: {id: {"azimuth", "elevation", "space"}}. Empty whenever no
#: `frame=` was supplied, which is every caller that has ever existed -- so the
#: quiet path is byte-identical.
#:
#: A MODULE GLOBAL and not a third return value: 35 call sites unpack exactly
#: two values from this function, across production, probes and six test
#: files. `_last_pair_evidence` above is the same pattern for the same reason.
_last_orientations: dict = {}
```

- [ ] **Step 3b: Add the frame builder**

In `mcp_harness/mesh_to_tree.py`, immediately after `_canonical_sign`
(~line 1631), add:

```python
def frame_from_mesh(tree: nx.Graph, mesh) -> "orientations.Frame":
    """The figure frame stick angles are measured in, from the mesh PCA.

    THE SAME CONSTRUCTION `label_leaves` USES, deliberately: mirror normal from
    `_symmetry_pairs_and_axis`, body axis = the larger-variance remaining axis,
    height = the other one, each sign-canonicalised. Sharing it is what makes
    an emitted angle and an emitted label two statements about one frame rather
    than two frames that happen to be near each other.
    """
    import orientations
    centroid, eigvecs, _scale = _mesh_pca(mesh)
    _pairs, mirror_idx = _symmetry_pairs_and_axis(tree, mesh)
    rest = [i for i in range(3) if i != mirror_idx]
    body_idx, height_idx = max(rest), min(rest)
    return orientations.Frame(
        origin=tuple(float(c) for c in centroid),
        axial=tuple(float(c) for c in _canonical_sign(eigvecs[:, body_idx])),
        lateral=tuple(float(c) for c in _canonical_sign(eigvecs[:, mirror_idx])),
        dorsal=tuple(float(c) for c in _canonical_sign(eigvecs[:, height_idx])))
```

- [ ] **Step 3c: Accept the frame and publish the channel**

In `mcp_harness/mesh_to_tree.py`, change the signature at line 1434 from
`def to_metric_tree(tree, sym):` to:

```python
def to_metric_tree(tree: nx.Graph, sym: list, *, frame=None):
```

Then, immediately after the existing
`globals()["_last_pair_evidence"] = []` reset near the top of the body, add:

```python
    # Same reset-first argument as _last_pair_evidence directly above: this
    # promises what the LAST call did, and a stale channel would attribute one
    # candidate's geometry to a different one.
    globals()["_last_orientations"] = {}
```

And immediately before the closing `return nodes, pairs`, add:

```python
    if frame is not None:
        import orientations
        positions = {remap[o]: tuple(float(c) for c in tree.nodes[o]["pos"])
                     for o in order}
        parent_of_emitted = {n["id"]: n["parent_id"] for n in nodes
                             if n["parent_id"] is not None}
        globals()["_last_orientations"] = orientations.stick_orientations(
            positions, parent_of_emitted, frame)
```

⚠ Placement matters: this must run **after** `pair_reconcile.reparent_pairs_to_shared_hub`,
so `parent_of_emitted` reflects the tree that is actually returned.

- [ ] **Step 3d: Carry it on the result**

In `mcp_harness/mesh_to_tree.py`, add to `MeshTreeResult` (after
`pair_evidence`, ~line 660):

```python
    orientations: dict = field(default_factory=dict)
                                       # U1: {emitted id: {"azimuth",
                                       # "elevation", "space"}} for the served
                                       # tree, or {} when no frame was built.
                                       # RECORDED, NEVER RANKED -- no key in
                                       # _serve_rank, no budget and no exit
                                       # condition reads it, the same contract
                                       # `runner_up` carries.
```

In `auto_mesh_to_metric_tree`, beside `pair_ev = {}` add
`orient_ev = {}`; in the prune loop, replace

```python
            nodes, pairs = to_metric_tree(tree, sym)
```

with

```python
            try:
                frame = frame_from_mesh(tree, mesh)
            except Exception:       # a degenerate frame is not an extraction
                frame = None        # failure -- the channel is garnish
            nodes, pairs = to_metric_tree(tree, sym, frame=frame)
            orient_ev[(voxel_res, prune)] = dict(_last_orientations)
```

and in `_confirmed`, add:

```python
            orientations=orient_ev.get((c["voxel_res"], c["prune"])) or {},
```

- [ ] **Step 3e: Update the test double whose subject changed**

In `mcp_harness/tests/test_mesh_report.py`, `_patch_forest_pipeline` (~line 407),
change the stub to carry the real signature and reset the new global:

```python
    monkeypatch.setattr(m2t, "to_metric_tree",
                        lambda t, sym, frame=None: (emitted, []))
    # to_metric_tree is what publishes these module globals; with it stubbed
    # they would otherwise leak in from whatever test ran last.
    monkeypatch.setattr(m2t, "_last_pre_root_children", None)
    monkeypatch.setattr(m2t, "_last_pair_evidence", [])
    monkeypatch.setattr(m2t, "_last_orientations", {})
```

⚠ **THIS IS NOT PATCHING A TEST TO MAKE IT PASS.** The two `setattr` lines above
`_last_orientations` are already in the file, under a comment that states the
exact hazard: a stubbed `to_metric_tree` never runs the reset, so a global
would "leak in from whatever test ran last". `_last_orientations` is a third
global published by the same function and it needs the same line for the same
reason. Adding it, and giving the double the signature it is standing in for,
is maintaining a double whose subject changed. Patching would be editing an
assertion; nothing here touches one.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientation_channel.py -v --timeout=300
```

Expected: PASS, 6 passed

- [ ] **Step 5: Run the byte-identity gate**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_mesh_to_tree.py tests/test_auto_mesh_to_tree.py tests/test_pair_detection.py tests/test_component_stitch.py tests/test_mesh_report.py tests/test_forest_tolerance.py tests/test_probe_extraction_fate.py -v --timeout=600
```

Expected: PASS, no failures. **This is the gate on the whole task** — these are
the files that unpack `to_metric_tree`'s return. Any failure here means the
signature change was not invisible and must be reverted, not patched.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/mesh_to_tree.py mcp_harness/tests/test_orientation_channel.py
git commit -m "feat(U1b): publish per-stick orientations on a side channel"
```

---

### Task 5: U6 — orientation-derived placement seeds

Replace `structural_layout`'s index-parity guess with the real arrangement,
riding the same `_dedupe_seeds` / `with_seeds` path so it inherits the SIGSEGV
guard on coincident seeds and the rounding rule.

**Files:**
- Modify: `mcp_harness/rescue_ladder.py` — add `orientation_layout` after
  `structural_layout` (~line 495); extend `placement_variants` (~line 567).
- Create: `mcp_harness/tests/test_orientation_placement.py`

**Interfaces:**
- Consumes: `mesh_to_tree._last_orientations`'s record shape
  (`{"azimuth", "elevation", "space"}`).
- Produces:
  `rescue_ladder.orientation_layout(nodes, orientations, scale=_LAYOUT_SCALE) -> dict`
  returning `{node_id: (x, y)}`, the identical shape `structural_layout`
  returns, already deduped; `{}` when `orientations` is empty or the walk
  cannot cover the tree.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_orientation_placement.py`:

```python
"""U6: placement seeds built from measured orientations."""
import rescue_ladder as rl

NODES = [{"id": 0, "parent_id": None, "length": 0},
         {"id": 1, "parent_id": 0, "length": 0.4},
         {"id": 2, "parent_id": 0, "length": 0.4},
         {"id": 3, "parent_id": 0, "length": 0.4},
         {"id": 4, "parent_id": 0, "length": 0.4}]

ORIENT = {1: {"azimuth": 0.0, "elevation": 0.0, "space": "mesh"},
          2: {"azimuth": 180.0, "elevation": 0.0, "space": "mesh"},
          3: {"azimuth": 90.0, "elevation": 0.0, "space": "mesh"},
          4: {"azimuth": -90.0, "elevation": 0.0, "space": "mesh"}}


def test_empty_orientations_yield_no_layout():
    """The fallback contract: with no measured angles the stage must behave
    exactly as it does today, which means emitting nothing here."""
    assert rl.orientation_layout(NODES, {}) == {}
    assert rl.orientation_layout(NODES, None) == {}


def test_every_node_is_seeded_and_the_root_is_centred():
    pos = rl.orientation_layout(NODES, ORIENT)
    assert set(pos) == {0, 1, 2, 3, 4}
    assert pos[0] == (0.5, 0.5)


def test_opposite_azimuths_land_on_opposite_sides_of_the_root():
    """ANTI-VACUITY: a layout that ignores the angle would put these together."""
    pos = rl.orientation_layout(NODES, ORIENT)
    rx, ry = pos[0]
    for a, b in ((1, 2), (3, 4)):
        ax, ay = pos[a][0] - rx, pos[a][1] - ry
        bx, by = pos[b][0] - rx, pos[b][1] - ry
        assert ax * bx + ay * by < 0, (a, b, pos[a], pos[b])


def test_no_two_seeds_share_a_position():
    """_dedupe_seeds' invariant: coincident seeds SIGSEGV the engine, and in a
    spawned ladder child that takes every remaining rung with them."""
    pos = rl.orientation_layout(NODES, ORIENT)
    assert len(set(pos.values())) == len(pos)


def test_seeds_stay_off_the_paper_boundary():
    pos = rl.orientation_layout(NODES, ORIENT)
    for x, y in pos.values():
        assert rl._SEED_MIN <= x <= rl._SEED_MAX
        assert rl._SEED_MIN <= y <= rl._SEED_MAX


def test_placement_variants_gains_a_variant_only_when_orientations_exist():
    without = rl.placement_variants(NODES, [])
    with_or = rl.placement_variants(NODES, [], orientations=ORIENT)
    assert len(with_or) == len(without) + 1
    assert any(name == "orientation" for name, _o, _n in with_or)


def test_placement_variants_is_byte_identical_without_orientations():
    """The rollback contract for this stage."""
    assert (rl.placement_variants(NODES, [])
            == rl.placement_variants(NODES, [], orientations=None))
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientation_placement.py -v --timeout=300
```

Expected: FAIL, `AttributeError: module 'rescue_ladder' has no attribute 'orientation_layout'`

- [ ] **Step 3a: Add the layout**

In `mcp_harness/rescue_ladder.py`, immediately after `structural_layout`
(before `_dedupe_seeds`), add:

```python
def orientation_layout(nodes, orientations, scale: float = _LAYOUT_SCALE) -> dict:
    """{node_id: (x, y)} -- a placement seed built from MEASURED stick angles.

    `structural_layout` above fabricates an arrangement: root-children alternate
    +/- along the diagonal and unpaired siblings stagger by index parity. That
    is a guess, made because the Metric Tree carried no angles. It is a good
    guess -- it packed the raw 6-leaf dog at voxel 96, which is the measurement
    that bought the placement stage -- but it is still a guess, and so is the
    engine's own fallback (`TreemakerWrapper.cpp:254` places every unseeded node
    at golden-angle x LIST INDEX).

    Each stick is walked from the root, its azimuth mapped onto the paper with
    the body axis along the engine's 45-degree symmetry diagonal `_U` and the
    lateral axis along the perpendicular `_V` -- the same two directions
    `structural_layout` uses, so the two layouts live in one coordinate system
    and can be compared arm to arm.

    ⚠ ELEVATION IS DROPPED, AND THAT IS NOT AN OVERSIGHT. The sheet is flat, so
    a paper layout has no elevation to carry; `vlm_judge` omits the key for its
    own paper frame for the same reason rather than emitting a constant 0.0.
    Two limbs that differ ONLY in elevation therefore seed to the same point,
    and `_dedupe_seeds` separates them exactly as it separates equal-length
    unpaired root children today.

    Returns {} for empty orientations, so a caller with no measured angles
    falls back byte-identically.
    """
    if not orientations or not _well_formed(nodes):
        return {}
    r = root_id(nodes)
    if r is None:
        return {}
    ch = _children(nodes)
    lengths = {n["id"]: (n.get("length") or 0) for n in nodes}
    pos = {r: (0.5, 0.5)}

    def place(nid, depth):
        if depth > len(nodes):          # defensive: a cycle can't spin forever
            return
        for c in ch.get(nid, []):
            rec = orientations.get(c) or orientations.get(str(c))
            length = max(lengths.get(c, 0), _SEED_MIN) * scale
            px, py = pos[nid]
            if rec is None:
                # No measured angle for this stick: leave it unseeded rather
                # than invent a direction. with_seeds simply omits it and the
                # engine falls back to its golden-angle placement for that one
                # node, which is the honest degradation.
                continue
            a = math.radians(float(rec["azimuth"]))
            ca, sa = math.cos(a), math.sin(a)
            pos[c] = _clamp((px + length * (ca * _U[0] + sa * _V[0]),
                             py + length * (ca * _U[1] + sa * _V[1])))
            place(c, depth + 1)

    place(r, 0)
    return _dedupe_seeds(pos)
```

- [ ] **Step 3b: Extend `placement_variants`**

In `mcp_harness/rescue_ladder.py`, change the signature of
`placement_variants` to
`def placement_variants(nodes, pairs, orientations=None):` and, immediately
before its `return out`, add:

```python
    # U6: the measured arm, offered ALONGSIDE the fabricated one rather than
    # replacing it. M3 (probe_orientation_placement.py) is what decides whether
    # it earns its place; until then both are on the ladder and the ranking
    # rules already in force pick between their outcomes.
    opos = orientation_layout(nodes, orientations)
    if opos and len(opos) == len(nodes or []):
        out.append(("orientation", None, with_seeds(nodes, opos)))
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientation_placement.py -v --timeout=300
```

Expected: PASS, 7 passed

- [ ] **Step 5: Run the ladder regression**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_dog_ladder_rescue.py tests/test_rescue_ladder.py tests/test_drain_before_downgrade.py -v --timeout=600
```

Expected: PASS. Every existing placement rescue must be preserved — the new
variant is appended, never substituted.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/rescue_ladder.py mcp_harness/tests/test_orientation_placement.py
git commit -m "feat(U6): placement seeds from measured stick orientations"
```

---

### Task 6: M3 — does the measured arrangement beat the fabricated one?

The spec's §2(b) claim is a *mechanism*, not a result. This is the A/B that
decides whether U6 ships.

**Files:**
- Create: `mcp_harness/probe_orientation_placement.py`
- Create: `mcp_harness/tests/test_orientation_verdict.py`
- Output: `mcp_harness/fixtures/orientation_placement_ab.json`

**Interfaces:**
- Consumes: `orientation_layout` and `placement_variants` (Task 5),
  `frame_from_mesh` and `_last_orientations` (Task 4),
  `probe_reachable_cells.COMMITTED_MESHES` (Task 1).
- Produces: the fixture, plus a printed verdict against the pre-registered bar.

- [ ] **Step 1: Write the probe**

Create `mcp_harness/probe_orientation_placement.py`:

```python
"""M3: measured stick orientations vs the fabricated arrangement.

THE PRE-REGISTERED BAR (spec section 7, written before this was run):
U6 ships only if orientation-derived seeds are NON-INFERIOR to
`structural_layout` on `stub_flaps` and `design_scale` across the whole
fixture set, AND strictly better on at least one subject.

⚠ A COVERAGE GAIN BOUGHT WITH A SCALE LOSS IS A TRADE TO ARGUE, NEVER A FREE
WIN (CLAUDE.md section 1.1 item 4). This probe reports all four axes and makes
no ranking claim of its own; `hull_coverage` is deliberately NOT a ranking key
in this repo and nothing here makes it one.

Four arms per cell, on the SAME tree:
  attempt0      no seeds at all -- the engine's golden-angle-by-list-index
  order         the ladder's canonical pairs-first order variant
  structural    `structural_layout`, the fabricated arrangement (shipped)
  orientation   `orientation_layout`, the measured one (U6)

Run:
    cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_orientation_placement.py
"""
import json
import os

import fold_meta
import mesh_to_tree as m2t
import paper_coverage
import probe_reachable_cells as prc
import rescue_ladder as rl

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_PATH = os.path.join(HERE, "fixtures", "orientation_placement_ab.json")

VOXELS = (64, 96, 128)
PRUNES = (0.3, 0.4, 0.5)


def _compile(nodes, pairs):
    fold = m2t._default_compile_fn(nodes, pairs)
    if fold.startswith("ERROR:"):
        return {"packed": False, "error": m2t.served_stage(fold)}
    return {"packed": True,
            "stage": m2t.served_stage(fold),
            "stub_flaps": m2t.served_stub_flaps(fold),
            "hull_coverage": paper_coverage.coverage_of_fold_str(fold),
            "design_scale": fold_meta.scale_from_fold_str(fold)}


def arms_for(subject, voxel, prune):
    path = os.path.join(HERE, "fixtures", f"{subject}.glb")
    mesh = m2t.load_mesh(path, voxel)
    tree = m2t.simplify_to_tree(m2t.extract_skeleton(mesh), prune)
    if tree.number_of_edges() == 0:
        return None
    sym = m2t.detect_symmetry(tree, mesh)
    try:
        frame = m2t.frame_from_mesh(tree, mesh)
    except Exception as exc:                    # noqa: BLE001
        frame = None
        frame_error = f"{type(exc).__name__}: {exc}"
    else:
        frame_error = None
    nodes, pairs = m2t.to_metric_tree(tree, sym, frame=frame)
    orient = dict(m2t._last_orientations)

    out = {"leaves": m2t._leaf_count(nodes), "pairs": len(pairs),
           "orientation_coverage": f"{len(orient)}/{max(len(nodes) - 1, 0)}",
           "frame_error": frame_error, "arms": {}}
    out["arms"]["attempt0"] = _compile(nodes, pairs)

    canon = rl.canonical_order(nodes, pairs)
    if canon is not None:
        out["arms"]["order"] = _compile(canon, pairs)

    spos = rl.structural_layout(nodes, pairs)
    if spos and len(spos) == len(nodes):
        out["arms"]["structural"] = _compile(rl.with_seeds(nodes, spos), pairs)

    opos = rl.orientation_layout(nodes, orient)
    if opos and len(opos) == len(nodes):
        out["arms"]["orientation"] = _compile(rl.with_seeds(nodes, opos), pairs)
    return out


def verdict(cells):
    """The pre-registered bar, evaluated. Returns (verdict_string, detail)."""
    worse, better = [], []
    for key, cell in sorted(cells.items()):
        arms = (cell or {}).get("arms") or {}
        s, o = arms.get("structural"), arms.get("orientation")
        if not s or not o or not s.get("packed") or not o.get("packed"):
            continue
        if (o.get("stub_flaps") or 0) > (s.get("stub_flaps") or 0):
            worse.append(f"{key}: stubs {s['stub_flaps']}->{o['stub_flaps']}")
        if (o.get("design_scale") or 0) < (s.get("design_scale") or 0):
            worse.append(f"{key}: scale {s['design_scale']}->{o['design_scale']}")
        if ((o.get("stub_flaps") or 0) < (s.get("stub_flaps") or 0)
                or (o.get("design_scale") or 0) > (s.get("design_scale") or 0)):
            better.append(key)
    if worse:
        return "DO NOT SHIP U6", {"regressions": worse, "improvements": better}
    if not better:
        return "DO NOT SHIP U6", {"reason": "non-inferior but never better -- "
                                            "the bar requires a strict win on "
                                            "at least one subject",
                                  "regressions": [], "improvements": []}
    return "SHIP U6", {"regressions": [], "improvements": better}


def main():
    cells = {}
    for subject in prc.COMMITTED_MESHES:
        for voxel in VOXELS:
            for prune in PRUNES:
                key = f"{subject}/v{voxel}/p{prune}"
                try:
                    cells[key] = arms_for(subject, voxel, prune)
                except Exception as exc:            # noqa: BLE001
                    cells[key] = {"error": f"{type(exc).__name__}: {exc}"}
                print(f"{key}: {cells[key]}")
    said, detail = verdict(cells)
    doc = {"_meta": {
        "generated_by": "probe_orientation_placement.py",
        "pre_registered_bar": (
            "U6 ships only if orientation-derived seeds are NON-INFERIOR to "
            "structural_layout on stub_flaps and design_scale across the whole "
            "fixture set, AND strictly better on at least one subject."),
        "verdict": said,
        "verdict_detail": detail,
    }, "cells": cells}
    with open(OUT_PATH, "w") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    print(f"\nVERDICT: {said}\n{json.dumps(detail, indent=1)}")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 1b: Test the verdict function**

`verdict()` is what decides SHIP / DO NOT SHIP for U6. An untested decision
function is the one thing in this plan that must not be taken on faith.

Create `mcp_harness/tests/test_orientation_verdict.py`:

```python
"""M3: the pre-registered bar, as executable code rather than prose."""
import probe_orientation_placement as pop


def _cell(structural, orientation):
    return {"arms": {"structural": dict(structural, packed=True),
                     "orientation": dict(orientation, packed=True)}}


def test_a_stub_regression_blocks_the_ship():
    cells = {"a": _cell({"stub_flaps": 0, "design_scale": 0.5},
                        {"stub_flaps": 1, "design_scale": 0.9})}
    said, detail = pop.verdict(cells)
    assert said == "DO NOT SHIP U6"
    assert detail["regressions"]


def test_a_scale_regression_blocks_the_ship():
    cells = {"a": _cell({"stub_flaps": 0, "design_scale": 0.6},
                        {"stub_flaps": 0, "design_scale": 0.5})}
    assert pop.verdict(cells)[0] == "DO NOT SHIP U6"


def test_non_inferior_but_never_better_does_not_ship():
    """The half of the bar that is easy to lose: 'no worse' is not the bar."""
    cells = {"a": _cell({"stub_flaps": 0, "design_scale": 0.5},
                        {"stub_flaps": 0, "design_scale": 0.5})}
    said, detail = pop.verdict(cells)
    assert said == "DO NOT SHIP U6"
    assert "never better" in detail["reason"]


def test_a_strict_win_with_no_regression_ships():
    cells = {"a": _cell({"stub_flaps": 0, "design_scale": 0.5},
                        {"stub_flaps": 0, "design_scale": 0.5}),
             "b": _cell({"stub_flaps": 1, "design_scale": 0.5},
                        {"stub_flaps": 0, "design_scale": 0.5})}
    said, detail = pop.verdict(cells)
    assert said == "SHIP U6"
    assert detail["improvements"] == ["b"]


def test_cells_where_either_arm_failed_to_pack_are_ignored():
    """An arm that did not pack has no stub count and no scale to compare."""
    cells = {"a": {"arms": {"structural": {"packed": False},
                            "orientation": {"packed": True, "stub_flaps": 0,
                                            "design_scale": 0.9}}}}
    assert pop.verdict(cells)[0] == "DO NOT SHIP U6"


def test_an_empty_run_does_not_ship():
    assert pop.verdict({})[0] == "DO NOT SHIP U6"
```

Run:

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_orientation_verdict.py -v --timeout=300
```

Expected: PASS, 6 passed

- [ ] **Step 2: Run the probe**

```bash
cd mcp_harness && PYTHONPATH=. .venv/bin/python probe_orientation_placement.py
```

Expected: 45 cell lines (5 subjects × 3 voxels × 3 prunes), then a `VERDICT:`
line. Runtime is minutes, not seconds — each cell runs up to four compiles.

⚠ **If `design_scale` reads `None` on every packed arm, STOP.**
`fold_meta.scale_from_fold_str` parses it out of the FOLD's `frame_title`, so a
uniform `None` means the arms are being compared on a field that cannot vary —
and the non-inferiority half of the bar would pass vacuously. That is the exact
failure this repo's anti-vacuity rule exists to catch. Fix the reader before
reading the verdict.

- [ ] **Step 3: Act on the verdict**

If `DO NOT SHIP U6`: revert Task 5's `placement_variants` hunk only (leave
`orientation_layout` and its tests in place — the function is still the
measured arm and the fixture is its record), and note the outcome in the
fixture's `_meta`.

If `SHIP U6`: leave it wired, and record in `_meta` which subjects improved.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/probe_orientation_placement.py mcp_harness/tests/test_orientation_verdict.py mcp_harness/fixtures/orientation_placement_ab.json mcp_harness/rescue_ladder.py
git commit -m "probe(M3): measured orientations vs the fabricated arrangement"
```

---

## Done criteria

- [ ] All six tasks committed.
- [ ] `fixtures/reachable_cell_compiles.json` carries a `u4_verdict`.
- [ ] `fixtures/wide_window_packability.json` carries k=9..12 star rows.
- [ ] `fixtures/orientation_placement_ab.json` carries a `verdict`.
- [ ] The byte-identity gate (Task 4 Step 5) passes.
- [ ] `MAX_LEAVES` is unchanged. `order_rank.rank_key` is unchanged.
      `vlm_judge.py` is unchanged.
- [ ] A handoff note records what M1/M2/M3 said, because P2's U4 and P3's
      producer choice both depend on those three answers.

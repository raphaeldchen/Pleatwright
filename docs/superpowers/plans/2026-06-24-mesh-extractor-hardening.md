# Mesh Extractor Hardening (Slice #2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the (now-verified) mesh→tree extractor provably trustworthy by correcting false debt-justification comments, pinning PR #9's recalibration on the live path, and re-tying the drifted gate-validation snapshots to live extraction — no runtime logic changes.

**Architecture:** Three tasks, all on `feat/mesh-to-tree-hardening`. Task 1 adds a committed generator that regenerates `mesh_validation_trees.json` from live extraction plus a drift-tripwire test. Task 2 adds a fast (compile-free) live-path in-distribution regression pin. Task 3 corrects documentation (code comments + POC design + handoff) and removes scratch. The existing slow E2E test already pins `confirmed=True` for all five fixtures, so nothing new compiles.

**Tech Stack:** Python, pytest, the existing `mcp_harness/mesh_to_tree.py` extractor and `feasibility/gate.py` two-stage gate.

## Global Constraints

- Tests live in `mcp_harness/tests/` and run from inside `mcp_harness/` via `.venv/bin/python -m pytest`.
- No new heavy dependencies.
- Fail loud with specific messages.
- TreeMaker/Oriedita engine behavior is fixed/partly inherent — fixes are extraction/doc-side, never engine-side.
- Do NOT change `SEARCH_K`, the `PRUNE_GRID` cap (0.60), or `VOXEL_GRID` values — evidence (2026-06-24 live run) shows they are load-bearing.
- Extraction is deterministic (`SKELETOR_SEED = 0`); equality assertions rely on this.
- The documented auto-selected constants per fixture (verified 2026-06-24), used by the generator and the in-distribution pin:
  quadruped `(96, 0.55)`, humanoid `(96, 0.30)`, fish `(64, 0.40)`, bird `(96, 0.25)`, insect `(96, 0.55)`.

---

### Task 1: Committed snapshot generator + drift-tripwire test

Regenerate `mesh_validation_trees.json` from the live extraction path (the current
file has drifted — humanoid differs ~3% with a different edge normalized to 0.40)
and add a generator that records provenance, plus a test that trips if extraction
ever drifts from the committed snapshot again.

**Files:**
- Create: `mcp_harness/tests/fixtures/gen_mesh_validation_trees.py`
- Modify (regenerate): `mcp_harness/tests/fixtures/mesh_validation_trees.json`
- Test: `mcp_harness/tests/test_gate_mesh_region.py` (add one test)

**Interfaces:**
- Consumes: `mesh_to_tree.mesh_to_metric_tree(path, voxel_res=int, prune_fraction=float) -> (nodes, pairs)` where `nodes` is a list of `{"id": int, "parent_id": int|None, "length": float}` and `pairs` is a list of `[int, int]`.
- Produces: `mesh_validation_trees.json` shape `{name: {"nodes": [...], "pairs": [...], "meta": {"voxel_res": int, "prune_fraction": float}}}`. The `meta` block is the per-fixture provenance the tripwire test reads.

- [ ] **Step 1: Write the generator**

Create `mcp_harness/tests/fixtures/gen_mesh_validation_trees.py`:

```python
"""Regenerate mesh_validation_trees.json from the LIVE extraction path, so the
gate-region validation trees stay tied to what mesh_to_tree actually produces.
They had drifted (humanoid differed ~3% with a different edge normalized to 0.40).

Run from mcp_harness/:
    .venv/bin/python tests/fixtures/gen_mesh_validation_trees.py

The (voxel_res, prune_fraction) per fixture are the constants
auto_mesh_to_metric_tree selects on the live path (verified 2026-06-24); see
docs/superpowers/specs/2026-06-24-mesh-extractor-hardening-design.md.
"""
import json
import os

import mesh_to_tree as m2t

# name -> (voxel_res, prune_fraction): the auto-selected constants per fixture.
CONSTANTS = {
    "quadruped": (96, 0.55),
    "humanoid":  (96, 0.30),
    "fish":      (64, 0.40),
    "bird":      (96, 0.25),
    "insect":    (96, 0.55),
}

HERE = os.path.dirname(os.path.abspath(__file__))       # tests/fixtures/
ROOT = os.path.dirname(os.path.dirname(HERE))           # mcp_harness/
OUT = os.path.join(HERE, "mesh_validation_trees.json")


def build():
    trees = {}
    for name, (vr, pr) in CONSTANTS.items():
        path = os.path.join(ROOT, "fixtures", f"{name}.glb")
        nodes, pairs = m2t.mesh_to_metric_tree(path, voxel_res=vr, prune_fraction=pr)
        trees[name] = {
            "nodes": nodes,
            "pairs": pairs,
            "meta": {"voxel_res": vr, "prune_fraction": pr},
        }
    return trees


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(build(), f, indent=2)
    print(f"wrote {OUT}")
```

- [ ] **Step 2: Regenerate the snapshot from live extraction**

Run (from `mcp_harness/`):

```bash
.venv/bin/python tests/fixtures/gen_mesh_validation_trees.py
```

Expected: prints `wrote .../mesh_validation_trees.json`. The file now carries a
`meta` block per fixture and the humanoid tree matches current live extraction.

- [ ] **Step 3: Add the drift-tripwire test**

In `mcp_harness/tests/test_gate_mesh_region.py`, add this test (the file already
defines `HERE` = `mcp_harness/` and `TREES` = the JSON path, and imports `json`,
`os`):

```python
def test_snapshots_match_live_extraction():
    """The committed validation trees must equal what mesh_to_tree produces today
    at each fixture's recorded (voxel_res, prune_fraction). Trips if extraction
    drifts from the snapshot (regenerate via
    tests/fixtures/gen_mesh_validation_trees.py when intended)."""
    import mesh_to_tree as m2t
    with open(TREES, encoding="utf-8") as f:
        trees = json.load(f)
    for name, t in trees.items():
        vr = t["meta"]["voxel_res"]
        pr = t["meta"]["prune_fraction"]
        path = os.path.join(HERE, "fixtures", f"{name}.glb")
        nodes, pairs = m2t.mesh_to_metric_tree(path, voxel_res=vr, prune_fraction=pr)
        assert nodes == t["nodes"], f"{name} nodes drifted from snapshot; regenerate"
        assert pairs == t["pairs"], f"{name} pairs drifted from snapshot; regenerate"
```

Note: this is a tripwire/characterization test — it passes immediately because
Step 2 regenerated the snapshot from the same path. Its value is catching future
drift, so there is no red-first step here.

- [ ] **Step 4: Run the new test and the existing region tests**

Run (from `mcp_harness/`):

```bash
.venv/bin/python -m pytest tests/test_gate_mesh_region.py -v
```

Expected: PASS for `test_snapshots_match_live_extraction`,
`test_mesh_fixtures_are_in_distribution` (now validating live trees), and
`test_no_recall_regression`.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tests/fixtures/gen_mesh_validation_trees.py \
        mcp_harness/tests/fixtures/mesh_validation_trees.json \
        mcp_harness/tests/test_gate_mesh_region.py
git commit -m "test(mesh): regenerate gate-validation snapshots from live path + drift tripwire

Committed generator records per-fixture (voxel_res, prune_fraction) provenance;
fixes humanoid drift. New test asserts the snapshot equals live extraction.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Fast live-path in-distribution regression pin

Pin PR #9's recalibration on the LIVE extraction path: every fixture, freshly
extracted and run through the gate, must read in-distribution (`ood is False`) and
not be rejected (`verdict != "infeasible"`). This is the gap the existing slow E2E
test left (it asserts `confirmed=True` but not in-distribution, so a silent
regression to OOD would pass). Compile-free, so it adds only seconds.

**Files:**
- Create: `mcp_harness/tests/test_mesh_recalibration_live.py`

**Interfaces:**
- Consumes: `mesh_to_tree.mesh_to_metric_tree(path, voxel_res, prune_fraction) -> (nodes, pairs)`; `feasibility.train_model.fit(corpus_path, artifact_path) -> dict`; `feasibility.gate.load(artifact_path) -> Gate`; `Gate.predict(nodes, pairs) -> {"verdict": str, "p_pack": float, "ood": bool, "ood_score": float, "reason": str}`.
- Produces: nothing consumed downstream (leaf test module).

- [ ] **Step 1: Write the in-distribution pin test**

Create `mcp_harness/tests/test_mesh_recalibration_live.py`:

```python
"""Live-path regression pin for PR #9's gate recalibration: each real mesh
fixture, freshly extracted and scored by the gate, must read in-distribution
(ood is False) and not be rejected (verdict != 'infeasible'). The existing slow
E2E (test_auto_selection_confirms_each_body_plan) pins that they COMPILE; this
fast, compile-free test pins that they stay in the gate's known region. See
docs/superpowers/specs/2026-06-24-mesh-extractor-hardening-design.md."""
import os

import pytest

import mesh_to_tree as m2t
from feasibility import gate as gatemod
from feasibility import train_model

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # mcp_harness/
CORPUS = os.path.join(HERE, "feasibility", "corpus_wide.jsonl")

# Auto-selected constants per fixture (verified 2026-06-24); see the hardening spec.
CONSTANTS = {
    "quadruped": (96, 0.55),
    "humanoid":  (96, 0.30),
    "fish":      (64, 0.40),
    "bird":      (96, 0.25),
    "insect":    (96, 0.55),
}


@pytest.fixture(scope="module")
def gate(tmp_path_factory):
    """Train a gate from the committed corpus into a temp artifact (a few seconds),
    so this runs on a fresh checkout where gate.joblib is gitignored."""
    art = str(tmp_path_factory.mktemp("gate") / "gate.joblib")
    train_model.fit(CORPUS, art)
    return gatemod.load(art)


@pytest.mark.parametrize("name", list(CONSTANTS))
def test_fixtures_in_distribution_on_live_path(name, gate):
    vr, pr = CONSTANTS[name]
    path = os.path.join(HERE, "fixtures", f"{name}.glb")
    nodes, pairs = m2t.mesh_to_metric_tree(path, voxel_res=vr, prune_fraction=pr)
    r = gate.predict(nodes, pairs)
    assert r["ood"] is False, f"{name} regressed to OOD on the live path: {r}"
    assert r["verdict"] != "infeasible", f"{name} rejected as infeasible: {r}"
```

- [ ] **Step 2: Run the test**

Run (from `mcp_harness/`):

```bash
.venv/bin/python -m pytest tests/test_mesh_recalibration_live.py -v
```

Expected: 5 PASS (one per fixture). This passes immediately because PR #9 already
made it true; it is a regression pin (it would fail if a future gate/corpus change
pushed a fixture back OOD), so there is no red-first step.

- [ ] **Step 3: Commit**

```bash
git add mcp_harness/tests/test_mesh_recalibration_live.py
git commit -m "test(mesh): pin fixtures in-distribution on the live extraction path

Compile-free regression guard for PR #9's recalibration: catches a silent
regression to OOD that the existing confirmed=True E2E would not.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Correct documentation (comments, POC design, handoff) + remove scratch

Replace the false OOD-based justification comments on the debt constants with the
real, measured reason; reclassify `insect` as expected-pass in the POC design;
correct the handoff's refuted Slice #2 assumptions; delete the investigation
scratch files. Pure documentation/cleanup — no logic change.

**Files:**
- Modify: `mcp_harness/mesh_to_tree.py:31-39`
- Modify: `docs/superpowers/specs/2026-06-16-mesh-to-tree-poc-design.md` (the "Expected outcomes" paragraph)
- Modify: `docs/superpowers/handoffs/2026-06-24-mesh-to-tree-hardening-and-agent-reference.md` (Slice #2 section)
- Delete: `mcp_harness/verify_recalibration.py`, `mcp_harness/verify_recalibration_out.json`

**Interfaces:** none (documentation only).

- [ ] **Step 1: Rewrite the debt-constant comments**

In `mcp_harness/mesh_to_tree.py`, replace the current `PRUNE_GRID` / `VOXEL_GRID` /
`SEARCH_K` block (lines 31–39) with:

```python
PRUNE_GRID = [0.20, 0.25, 0.30, 0.40, 0.45, 0.50, 0.55, 0.60]  # capped at 0.60 (0.70 omitted): 0.70 yields
                                                                 # over-compact trees (fewer leaves) that win on
                                                                 # the gate's p_pack and displace the faithful
                                                                 # flap count. Fixtures are in-distribution now
                                                                 # (PR #9), but p_pack still over-rewards
                                                                 # compactness, so the cap stays. See the
                                                                 # 2026-06-24 mesh-extractor-hardening spec.
VOXEL_GRID = [96, 64, 128]                                      # expensive outer axis; escalate on failure
SEARCH_K = 4                                                    # 4 (not 2) is load-bearing: the in-distribution
                                                                 # gate's p_pack mis-ranks by leaf count -- it
                                                                 # ranks unpackable 6-leaf trees ABOVE the
                                                                 # packable 5-leaf tree, so the packable candidate
                                                                 # is rank-4 for quadruped & humanoid (measured
                                                                 # 2026-06-24). K=4 reaches it; K=2 would drop
                                                                 # both. NOT OOD debt (fixtures in-distribution
                                                                 # since PR #9) -- the deeper fix is recalibrating
                                                                 # the gate's ranking. See the hardening spec.
```

- [ ] **Step 2: Reclassify insect in the POC design**

In `docs/superpowers/specs/2026-06-16-mesh-to-tree-poc-design.md`, replace the
"Expected outcomes" paragraph (currently saying insect packs 0% / hits the wall):

Old:

```
**Expected outcomes:** quadruped / bird / humanoid → *both* dimensions pass.
**Insect** → *faithful extraction* expected (a sensible 6-leg tree), but
packability is expected to hit the known TreeMaker fragile-edge wall (the insect
template itself packs 0% under jitter); that is **not** a POC failure — it is the
inherent packing limit already proven, and the POC should report it as such.
```

New:

```
**Expected outcomes:** all five body plans → *both* dimensions pass.
**Insect** was originally expected to hit the TreeMaker fragile-edge wall (the
hand-made insect *template* packs 0% under jitter), but `auto_mesh_to_metric_tree`
rediscovers a packable extraction: as of the 2026-06-24 live verification it
confirms a foldable insect at (voxel_res 96, prune 0.55), 6 leaves / 3 bilateral
pairs. The closed-loop search finds packable proportions the single hand template
did not — so insect is now expected-pass, pinned by
test_auto_selection_confirms_each_body_plan. See the 2026-06-24 hardening spec.
```

- [ ] **Step 3: Correct the handoff's Slice #2 assumptions**

In `docs/superpowers/handoffs/2026-06-24-mesh-to-tree-hardening-and-agent-reference.md`,
append this note at the end of the `## SLICE #2` section (after the "Success
criteria" line):

```
> **Correction (2026-06-24 live verification):** two assumptions above were
> refuted by evidence. (1) The debt is NOT retire-able: fixtures are now
> in-distribution AND compile, but the in-distribution gate still mis-ranks by
> leaf count, so SEARCH_K=4 stays load-bearing (quadruped/humanoid reach the
> packable tree only at rank-4); the PRUNE 0.60 cap stays too. The slice instead
> corrects the now-false justification comments and pins the behavior. (2) The
> live-path confirm test was not missing — test_auto_selection_confirms_each_body_plan
> already pins confirmed=True for all five fixtures incl. insect; insect is
> expected-PASS, not expected-fail. Implemented per
> docs/superpowers/specs/2026-06-24-mesh-extractor-hardening-design.md.
```

- [ ] **Step 4: Delete the scratch investigation files**

```bash
git rm -f --ignore-unmatch mcp_harness/verify_recalibration.py mcp_harness/verify_recalibration_out.json
rm -f mcp_harness/verify_recalibration.py mcp_harness/verify_recalibration_out.json
```

(The files are untracked scratch; `git rm --ignore-unmatch` is a no-op if they were
never staged, and the `rm` removes them from the working tree either way.)

- [ ] **Step 5: Run the full suite**

Run (from `mcp_harness/`):

```bash
.venv/bin/python -m pytest -q
```

Expected: all pass (was 163 passed, 1 skipped; now +2 new tests → 165 passed, 1
skipped). The doc/comment edits don't affect runtime, so the slow E2E and gate
tests stay green.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/mesh_to_tree.py \
        docs/superpowers/specs/2026-06-16-mesh-to-tree-poc-design.md \
        docs/superpowers/handoffs/2026-06-24-mesh-to-tree-hardening-and-agent-reference.md
git commit -m "docs(mesh): correct debt-constant rationale; insect is expected-pass

SEARCH_K=4 / PRUNE cap 0.60 stay because the in-distribution gate mis-ranks by
leaf count (not OOD). Reclassify insect as expected-pass; correct the handoff's
refuted Slice #2 assumptions. Remove investigation scratch.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Controller follow-up (not a subagent task)

After the branch is merge-ready, update the persistent memory files (outside the
repo, controller-owned) to match the evidence:
- `memory/mesh-auto-constant-selection.md` — correct "all 5 real meshes OOD → gate
  decorative"; record that the 2026-06-24 live path reads all 5 in-distribution and
  confirms all 5 incl. insect; SEARCH_K=4 / PRUNE cap 0.60 remain, not as OOD debt
  but because the in-distribution gate mis-ranks by leaf count.
- `memory/MEMORY.md` hook line for the same — drop "all 5 meshes OOD"; note the
  recalibration holds on the live path and the debt's real reason.

## Self-Review

**Spec coverage:** §3 item 1 (correct comments) → Task 3 Step 1. Item 2 (live
in-distribution pin) → Task 2. Item 3 (regenerate snapshots + provenance test) →
Task 1. Item 4 (reclassify insect) → Task 3 Steps 2–3 + Controller follow-up
(memory). §5 scratch cleanup → Task 3 Step 4. §6 testing/cost → all new tests are
compile-free; full suite in Task 3 Step 5. §7 deferred limitation → documented in
the new comments (Task 3 Step 1) and spec; no task (intentionally out of scope).

**Placeholder scan:** none — all code blocks are complete, all commands concrete.

**Type consistency:** `mesh_to_metric_tree(path, voxel_res, prune_fraction) ->
(nodes, pairs)`, `gate.predict(...) -> dict` with keys `ood`/`verdict`, and the JSON
`meta.{voxel_res,prune_fraction}` shape are used identically across Tasks 1 and 2
and match the generator's output.

# B5-front-dof Phase D Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a confirmed verdict — SEARCH GAP vs STRUCTURAL LOCK — on whether
any first-order folding freedom of the served/squared compiled dog moves the
front pose group independently of back/head (spec:
`docs/superpowers/specs/2026-07-12-b5-front-dof-diagnosis-design.md`).

**Architecture:** Promote the `feat/b5-rigid-fold-slice5` instrument into this
branch, extend `rigid_fold.py` with null-space → tip-coupling analysis (Gate D1),
cross-validate against the 162-row measured coupling table (Gate D2), and — only
on a SEARCH-GAP/GRAY reading — run a ≤40-read sim pilot (Gate D3). Everything up
to D3 is sim-free numpy. Phase S is NOT planned here; it is scoped at the user
checkpoint after the verdict.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv`), numpy, pytest; headed
Playwright SimSession ONLY in the conditional Task 10.

## Global Constraints

- Branch: `feat/b5-front-dof` (already exists; spec committed at `d855f32`). Worktree: `.claude/worktrees/b5-front-residual-rigidity-e47903`.
- SHARED CHECKOUT: a Codex session is active on `<repo>` (the main checkout). NEVER write there. Copy inputs FROM it only.
- `.gitignore` does NOT ignore `*.out.json` / `*.out.jsonl`. Probe outputs and suite logs stay UNCOMMITTED: always `git add` explicit file paths, never `git add -A` / `git add .`.
- Test command pattern: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/<file> -q`. Full suite (`tests/` , ~10 min, includes real spawn compiles): expected baseline 557 passed / 4 skipped + tests added by this branch.
- Probes run as scripts: `cd mcp_harness && .venv/bin/python <probe>.py`.
- Never 0.0 tolerances. All thresholds in this plan come verbatim from the spec — do not tune them.
- Controller-only for ANY headed-sim run (Task 10). Subagent-launched background sim processes get orphan-killed. Subagents may run sim-free probes.
- The bridge (`web/frontend/public/simulator/js/ide-bridge.js`) must NOT be touched. If a task seems to need it: HALT and ask.
- After each task: append a ledger entry to `.superpowers/sdd/progress.md` (task, gate status, measured numbers if any, deviations).
- Human merges the PR; ask before any push.
- Commit messages end with: `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

**Verdict-branch map (from Task 8's measured output — decided then, not now):**
- STRUCTURAL-LOCK (incl. degenerate) → skip Tasks 9–10 → Task 11 checkpoint.
- SEARCH-GAP or GRAY, D2 not FAIL → Tasks 9–10 → Task 11.
- D2 non-vacuous FAIL (probe exit 2) → skip Tasks 9–10 → Task 11 checkpoint with "instrument uncalibrated" finding (no pilot without user approval).

---

### Task 1: Environment + promote the rigid instrument (Gate D0, part 1)

**Files:**
- Merge in (via `git merge`): `mcp_harness/rigid_fold.py`, `mcp_harness/probe_folding_dof.py`, `mcp_harness/tests/test_rigid_fold.py`, `docs/superpowers/specs/2026-07-10-b5-rigid-fold-solver-slice5-design.md`
- Modify: `mcp_harness/rigid_fold.py` (module docstring), `docs/superpowers/specs/2026-07-10-b5-rigid-fold-solver-slice5-design.md` (status banner)
- Create: `mcp_harness/tests/test_flex_diagnosis.py`
- Uncommitted local setup: `mcp_harness/.venv` (symlink), `mcp_harness/headless_treemaker.cpython-314-darwin.so`, `mcp_harness/oriedita/*.jar` (copies)

**Interfaces:**
- Produces: importable `rigid_fold` (existing API: `fold_to_3d(fold, rho) -> RigidFoldState`, `folding_dof(fold, eps=1e-6, rtol=1e-6) -> DofResult` with fields `dof/rank/n_creases/singular_values/rank_tol`), `probe_folding_dof` (module-level `DEG4_VERTEX`, `_anchors_ok()`), and the test file every later task extends.

- [ ] **Step 1: Set up the worktree environment** (this worktree has no venv/build artifacts)

```bash
cd <repo>
ln -s <repo>/mcp_harness/.venv mcp_harness/.venv
cp <repo>/mcp_harness/headless_treemaker.cpython-314-darwin.so mcp_harness/
cp <repo>/mcp_harness/oriedita/*.jar mcp_harness/oriedita/
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q --collect-only | tail -2
```

Expected: collection succeeds (hundreds of tests listed, no errors). These are
all gitignored paths (`.venv/`, `*.so`, `oriedita/*.jar`) — nothing to commit.

- [ ] **Step 2: Merge the instrument branch**

```bash
git merge feat/b5-rigid-fold-slice5 --no-edit
git diff --stat HEAD~1..HEAD -- mcp_harness docs
```

Expected: clean merge (all four files are new; no conflicts). If conflicts
appear, STOP and report — do not resolve ad hoc.

- [ ] **Step 3: Run the instrument's own tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_rigid_fold.py -q
```

Expected: all pass (the branch was green when written; this verifies it is
still green against current-main `flat_fold.py`/`square_complete.py`).

- [ ] **Step 4: Add the ownership note to `rigid_fold.py`'s docstring**

Edit `mcp_harness/rigid_fold.py` — replace the final docstring paragraph:

```
Deliberately numpy-only and sim-free, like flat_fold.py and pose_target.py.
Does NOT modify flat_fold.py -- it reuses `_extract_faces`/`_signed_area` and
rebuilds the small face graph locally, so the shared file is untouched.
"""
```

with:

```
Deliberately numpy-only and sim-free, like flat_fold.py and pose_target.py.
Does NOT modify flat_fold.py -- it reuses `_extract_faces`/`_signed_area` and
rebuilds the small face graph locally, so the shared file is untouched.

OWNERSHIP NOTE (2026-07-12, b5-front-dof): the Codex rigid-origami kernel
(mcp_harness/rigid/, PR #36) is the likely eventual home for this math; its
pinned conventions differ (mm/radian units, oriented left/right hinge
transforms, per-artifact tolerances). This module stays a lightweight B5
diagnosis instrument. Do NOT build a closure solver here -- that is
escalation-only, and consuming the kernel's closure solver (its gate R3) is
preferred (see docs/superpowers/specs/2026-07-12-b5-front-dof-diagnosis-design.md).
"""
```

- [ ] **Step 5: Update the slice-5 spec status banner**

Edit `docs/superpowers/specs/2026-07-10-b5-rigid-fold-solver-slice5-design.md` — replace:

```
**Status:** design approved 2026-07-10, not yet implemented.
```

with:

```
**Status:** diagnostic subset (fold_to_3d forward pass + folding_dof
first-order DOF count, math-anchored) implemented on `feat/b5-rigid-fold-slice5`
and PROMOTED into `feat/b5-front-dof` 2026-07-12. The closure solve
(Component 2), `tip_vectors`, and validation-ladder step 3 (sim anchor) were
NOT built — closure solve is escalation-only per the b5-front-dof design spec
(prefer consuming the Codex rigid/ kernel's).
```

- [ ] **Step 6: Write the failing D0 regression test**

Create `mcp_harness/tests/test_flex_diagnosis.py`:

```python
"""Phase-D diagnosis math (b5-front-dof design spec, gates D0-D2).

Pure data-layer/numpy -- no sim imports. Verdict VALUES are deliberately NOT
pinned here: the committed artifacts are the instrument mechanics and the
decision RULES; the measurement itself happens when probe_front_flex runs
(gates pinned before data -- SDD honesty rule).
"""
import json
import os

import numpy as np
import pytest

import square_complete
from rigid_fold import folding_dof

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")


def _golden(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def _dog_squared():
    return square_complete.complete_square(_golden("dog.fold"), 1.0, 1.0)


class TestD0Regressions:
    def test_dog_squared_dof_is_3(self):
        # Pinned D0 regression: the whole slice is premised on the recorded
        # instrument reading (probe_folding_dof run, rigid-fold worktree,
        # 2026-07-12: dog-squared dof=3 rank=35 creases=38).
        res = folding_dof(_dog_squared())
        assert res.dof == 3
        assert res.rank == 35
        assert res.n_creases == 38
```

- [ ] **Step 7: Run the new test**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: 1 passed (this is a regression pin of an already-recorded value, so
it passes immediately — the "fail first" evidence here is Step 8's probe run,
which recomputes the same number independently).

- [ ] **Step 8: Re-run the DOF probe (D0 anchor re-check)**

```bash
cd mcp_harness && .venv/bin/python probe_folding_dof.py
```

Expected: `=== instrument anchors ===` all `[PASS]`; the table row
`dog-squared (served)` shows `dof 3, rank 35, creases 38`. Output file
`probe_folding_dof.out.json` is written — do NOT commit it.

- [ ] **Step 9: Full suite (D0 requirement: suite green post-merge)**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q
```

Expected: baseline 557 passed / 4 skipped PLUS the merged instrument tests and
the new regression test, 0 failures. (~10 min.)

- [ ] **Step 10: Commit**

```bash
git add mcp_harness/rigid_fold.py docs/superpowers/specs/2026-07-10-b5-rigid-fold-solver-slice5-design.md mcp_harness/tests/test_flex_diagnosis.py
git commit -m "chore(b5-front-dof): promote rigid instrument -- ownership note, spec banner, dog-squared dof=3 regression pin

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Gate D0 data package (coupling-table reconcile + naming parity)

**Files:**
- Create: `mcp_harness/probe_front_flex.py` (constants + D0 pure functions; `main()` comes in Task 7)
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)
- Uncommitted local copy: `mcp_harness/probe_dog_coupling.out.jsonl`

**Interfaces:**
- Consumes: `pose_coupling.CouplingTable(path)` / `CouplingRow` (fields `gate`, `key`, `verdict`, `site`, `delta_groups`, …), `pose_base.NamedBase(raw, sq, DOG_CONFIG)` (`.grouping`, `.ambiguity_count`, `.ambiguities`), `square_complete.complete_square(raw, 1.0, 1.0)`.
- Produces: `probe_front_flex.served_dog() -> (raw, sq)`, `reconcile_coupling(table) -> dict` (raises ValueError), `naming_parity(nb) -> None` (raises ValueError), `sq_vertex_index(sq, xy) -> int` (raises `rigid_fold.FlexInstrumentError` — defined in Task 4; until then use `ValueError`, switched in Task 4), plus module constants `EXPECTED_DOF`, `GATE1_TALLY`, `RECORDED_GROUPING`, `R_SEARCH_GAP`, `R_STRUCTURAL`, `DEGENERATE_FRONT`, `ALIGN_THRESHOLD`, `VACUITY_COND`, `COUPLING_JSONL`, `OUT_JSON`.

- [ ] **Step 1: Copy the coupling table from the main checkout (read-only source)**

```bash
cp <repo>/mcp_harness/probe_dog_coupling.out.jsonl \
   <repo>/mcp_harness/
wc -l <repo>/mcp_harness/probe_dog_coupling.out.jsonl
```

Expected: file copied; line count > 162 (it also holds gate0/anchor/gate2/gate3
rows). NEVER commit this file.

- [ ] **Step 2: Write the failing tests**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
import dataclasses

import pose_base
import pose_coupling as pc
import probe_front_flex as pff


def _mini_table(tmp_path, tallies):
    """Synthetic gate-1 JSONL with the given verdict tallies."""
    path = tmp_path / "mini.jsonl"
    with open(path, "w") as fh:
        for verdict, n in tallies.items():
            for i in range(n):
                row = pc.CouplingRow(
                    gate="gate1", key=f"{verdict}{i}", ops=[],
                    verdict=verdict,
                    site="front_v18" if verdict == "scored" else None,
                    delta_groups=({"front": 1.0, "back": 2.0, "head": 3.0}
                                  if verdict == "scored" else None))
                fh.write(json.dumps(dataclasses.asdict(row)) + "\n")
    return pc.CouplingTable(str(path))


class TestD0DataPreflight:
    def test_reconcile_passes_on_handoff_tallies(self, tmp_path):
        table = _mini_table(tmp_path, pff.GATE1_TALLY)
        counts = pff.reconcile_coupling(table)
        assert counts == pff.GATE1_TALLY

    def test_reconcile_rejects_wrong_tallies(self, tmp_path):
        bad = dict(pff.GATE1_TALLY, scored=113, parked=37)
        table = _mini_table(tmp_path, bad)
        with pytest.raises(ValueError, match="reconcile"):
            pff.reconcile_coupling(table)

    def test_reconcile_rejects_scored_without_delta_groups(self, tmp_path):
        table = _mini_table(tmp_path, pff.GATE1_TALLY)
        table.rows[0].delta_groups = None
        with pytest.raises(ValueError, match="delta_groups"):
            pff.reconcile_coupling(table)

    def test_dog_naming_parity_holds(self):
        # The recorded B5-prime grouping, verbatim (handoff Gate 0:
        # ambiguity 0, grouping == recorded Gate-3 exactly).
        raw, sq = pff.served_dog()
        nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
        pff.naming_parity(nb)  # must not raise
        assert nb.grouping == pff.RECORDED_GROUPING

    def test_sq_vertex_index_roundtrip(self):
        raw, sq = pff.served_dog()
        nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
        for s in nb.sites.values():
            i = pff.sq_vertex_index(sq, s.xy)
            assert (round(float(sq["vertices_coords"][i][0]), 8),
                    round(float(sq["vertices_coords"][i][1]), 8)) == s.xy

    def test_sq_vertex_index_rejects_unknown_point(self):
        _raw, sq = pff.served_dog()
        with pytest.raises(Exception, match="vert"):
            pff.sq_vertex_index(sq, (0.123456789, 0.987654321))
```

- [ ] **Step 3: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'probe_front_flex'`.

- [ ] **Step 4: Create `mcp_harness/probe_front_flex.py`**

```python
"""Phase-D sim-free diagnosis driver (b5-front-dof design spec, gates D0-D2).

Answers: does the served/squared dog's first-order flex space contain a
direction that moves the FRONT pose group independently of back/head?

D0 preflight -> D1 flex-space front-selectivity -> D2 cross-validation
against the measured 162-row coupling table. NO SIM: pure numpy on the
data layer. Refuses all verdicts if any D0 anchor fails (probe_folding_dof
pattern). The conditional D3 pilot lives in probe_front_pilot.py.

Exit codes: 0 = verdict produced; 1 = D0/instrument failure (no verdict);
2 = D2 non-vacuous FAIL (verdict produced but instrument uncalibrated --
HALT to checkpoint, no pilot without user approval).

Run:  cd mcp_harness && .venv/bin/python probe_front_flex.py
Output: probe_front_flex.out.json (uncommitted).
"""
import json
import os
import sys

import numpy as np

import pose_base
import pose_coupling as pc
import square_complete

_HERE = os.path.dirname(os.path.abspath(__file__))
GOLDENS = os.path.join(_HERE, "tests", "goldens")
COUPLING_JSONL = os.path.join(_HERE, "probe_dog_coupling.out.jsonl")
OUT_JSON = os.path.join(_HERE, "probe_front_flex.out.json")

# ---- pinned constants (design spec section 4; do not tune) -------------
EXPECTED_DOF = 3                    # recorded dog-squared reading
GATE1_TALLY = {"scored": 114, "refused": 12, "parked": 36, "error": 0}
RECORDED_GROUPING = {               # B5-prime handoff Gate 0, verbatim
    "head": "v25", "front": ["v13", "v18"], "back": ["v12", "v16"],
    "tail": "v14", "rear_trio": ["v12", "v14", "v16"]}
R_SEARCH_GAP = 1.0                  # r* >= : SEARCH-GAP candidate
R_STRUCTURAL = 0.2                  # r* <= : STRUCTURAL LOCK
DEGENERATE_FRONT = 1e-9             # front/total below this in ALL dirs
ALIGN_THRESHOLD = 0.8               # D2 captured-fraction pass bar
VACUITY_COND = 0.2                  # signature-matrix cond above -> VACUOUS


def served_dog():
    """The B5-prime substrate: goldens/dog.fold squared for display
    (probe_dog_coupling.served semantics, minus the display replay)."""
    with open(os.path.join(GOLDENS, "dog.fold")) as fh:
        raw = json.load(fh)
    return raw, square_complete.complete_square(raw, 1.0, 1.0)


def reconcile_coupling(table):
    """D0: the copied coupling JSONL must reconcile to the handoff tallies
    (162 gate1 rows = 114 scored + 12 refused + 36 parked + 0 error) and
    every scored row must carry the delta_groups D2 consumes."""
    gate1 = [r for r in table.rows if r.gate == "gate1"]
    counts = {v: sum(1 for r in gate1 if r.verdict == v)
              for v in ("scored", "refused", "parked", "error")}
    if len(gate1) != 162 or counts != GATE1_TALLY:
        raise ValueError(
            f"coupling table does not reconcile: {len(gate1)} gate1 rows,"
            f" tallies {counts} != {GATE1_TALLY}")
    bad = [r.key for r in gate1 if r.verdict == "scored"
           and (r.delta_groups is None
                or set(r.delta_groups) != set(pc.GROUPS))]
    if bad:
        raise ValueError(f"scored rows missing delta_groups: {bad[:5]}")
    return counts


def naming_parity(nb):
    """D0: grouping must equal B5-prime's recorded grouping, ambiguity 0."""
    if nb.ambiguity_count != 0:
        raise ValueError(f"naming ambiguities: {nb.ambiguities}")
    if nb.grouping != RECORDED_GROUPING:
        raise ValueError(f"grouping drifted from recorded: {nb.grouping}")


def sq_vertex_index(sq, xy):
    """Squared-fold vertex index for an 8dp-snapped coordinate key (the
    NamedBase Site.xy / targets convention). Exactly-one-match required
    (unique_targets already guarantees this for kept targets)."""
    key = (round(float(xy[0]), 8), round(float(xy[1]), 8))
    hits = [i for i, p in enumerate(sq["vertices_coords"])
            if (round(float(p[0]), 8), round(float(p[1]), 8)) == key]
    if len(hits) != 1:
        raise ValueError(f"{len(hits)} squared-fold vertices at {key}")
    return hits[0]
```

- [ ] **Step 5: Run tests to verify pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: all pass (7 tests total now).

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/probe_front_flex.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): D0 data package -- coupling-table reconcile (162=114/12/36/0), recorded-grouping parity, squared-vertex index

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `null_space_basis` (Gate D1, part 1)

**Files:**
- Modify: `mcp_harness/rigid_fold.py` (refactor `folding_dof`, add `_rigidity_matrix` + `null_space_basis`)
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)

**Interfaces:**
- Produces: `rigid_fold._rigidity_matrix(fold, eps=1e-6) -> (creases, J)` where `creases` is a list of edge-key tuples and `J` is the (m, n) rigidity matrix; `rigid_fold.null_space_basis(fold, eps=1e-6, rtol=1e-6) -> (creases, basis, DofResult)` where `basis` is an (n_creases, dof) ndarray with orthonormal columns spanning the first-order flex space.
- Constraint: `folding_dof`'s behavior is unchanged (all existing `test_rigid_fold.py` tests plus the dof=3 regression stay green).

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
import rigid_fold
from probe_folding_dof import DEG4_VERTEX
from rigid_fold import null_space_basis


class TestNullSpaceBasis:
    def test_deg4_vertex_basis(self):
        creases, B, res = null_space_basis(DEG4_VERTEX)
        assert res.dof == 2 and B.shape == (4, 2)
        assert len(creases) == 4
        # orthonormal columns
        assert np.allclose(B.T @ B, np.eye(2), atol=1e-9)
        # genuine first-order flexes: J @ b ~ 0
        _c, J = rigid_fold._rigidity_matrix(DEG4_VERTEX)
        assert float(np.max(np.abs(J @ B))) < 1e-6 * max(1.0, float(np.abs(J).max()))

    def test_star4_basis_matches_dof(self):
        star = _golden("star-4.fold")
        creases, B, res = null_space_basis(star)
        assert res.dof == 6 and B.shape == (8, 6)

    def test_folding_dof_unchanged_by_refactor(self):
        # behavior-preservation tripwire: same numbers as the direct call
        res_direct = folding_dof(DEG4_VERTEX)
        _c, _B, res_via_basis = null_space_basis(DEG4_VERTEX)
        assert res_direct.dof == res_via_basis.dof
        assert res_direct.rank == res_via_basis.rank
        assert np.allclose(res_direct.singular_values,
                           res_via_basis.singular_values)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestNullSpaceBasis -q
```

Expected: FAIL — `ImportError: cannot import name 'null_space_basis'`.

- [ ] **Step 3: Implement in `mcp_harness/rigid_fold.py`**

Replace the body of `folding_dof` (keep its docstring) and add the two new
functions directly above it:

```python
def _rigidity_matrix(fold: dict, eps: float = 1e-6):
    """(creases, J): the rigidity matrix J = d(closure)/d(rho) by central
    differences at the unfolded flat state rho = 0 (where the closure gap is
    identically 0 and its Jacobian is the first-order flex space)."""
    creases = fold_to_3d(fold, {}).creases
    n = len(creases)

    def g(rho_vec):
        return fold_to_3d(fold, dict(zip(creases, rho_vec))).residual

    m = len(g(np.zeros(n))) if n else 0
    J = np.zeros((m, n))
    for i in range(n):
        e = np.zeros(n)
        e[i] = eps
        J[:, i] = (g(e) - g(-e)) / (2.0 * eps)
    return creases, J


def _dof_from_svd(sv: np.ndarray, n: int, shape, rtol: float) -> DofResult:
    smax = float(sv[0]) if sv.size else 0.0
    tol = rtol * smax * max(shape)
    rank = int((sv > tol).sum())
    return DofResult(dof=n - rank, rank=rank, n_creases=n,
                     singular_values=sv, rank_tol=tol)


def null_space_basis(fold: dict, eps: float = 1e-6, rtol: float = 1e-6):
    """(creases, basis, DofResult): `basis` is (n_creases, dof) with
    orthonormal columns spanning the first-order flex space -- the
    right-singular vectors of the rigidity matrix at/below the rank
    tolerance. Same rank decision as folding_dof (shared SVD)."""
    creases, J = _rigidity_matrix(fold, eps)
    n = len(creases)
    if n == 0:
        return creases, np.zeros((0, 0)), DofResult(
            dof=0, rank=0, n_creases=0,
            singular_values=np.zeros(0), rank_tol=0.0)
    if J.shape[0] == 0:
        # no closure constraints at all: every crease is a free DOF
        res = _dof_from_svd(np.zeros(0), n, J.shape, rtol)
        return creases, np.eye(n), res
    _u, sv, vt = np.linalg.svd(J)
    res = _dof_from_svd(sv, n, J.shape, rtol)
    return creases, vt[res.rank:].T, res
```

Then rewrite `folding_dof`'s body to delegate (docstring unchanged):

```python
def folding_dof(fold: dict, eps: float = 1e-6, rtol: float = 1e-6) -> DofResult:
    creases, J = _rigidity_matrix(fold, eps)
    n = len(creases)
    if n == 0:
        return DofResult(dof=0, rank=0, n_creases=0,
                         singular_values=np.zeros(0), rank_tol=0.0)
    sv = np.linalg.svd(J, compute_uv=False) if J.shape[0] else np.zeros(0)
    return _dof_from_svd(sv, n, J.shape, rtol)
```

(Note: `vt[res.rank:]` on a (m, n) SVD with `full_matrices=True` — numpy's
default — always yields all n right-singular vectors, so the slice is valid
even when m < n.)

- [ ] **Step 4: Run tests — new AND behavior-preservation**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py tests/test_rigid_fold.py -q
```

Expected: all pass (incl. `test_dog_squared_dof_is_3` — the refactor must not
move the recorded reading).

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/rigid_fold.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): null_space_basis -- expose the flex basis from the shared rigidity-matrix SVD (folding_dof refactor, behavior pinned)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Tip flex velocities + signatures with dual-step guard (Gate D1, part 2)

**Files:**
- Modify: `mcp_harness/rigid_fold.py` (add `FlexInstrumentError`, `_vertex_face_slot`, `tip_flex_velocity`, `tip_flex_signatures`)
- Modify: `mcp_harness/probe_front_flex.py` (switch `sq_vertex_index` to raise `FlexInstrumentError`)
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)

**Interfaces:**
- Consumes: `fold_to_3d`, `null_space_basis` (Task 3).
- Produces: `rigid_fold.FlexInstrumentError(RuntimeError)`; `tip_flex_velocity(fold, creases, direction, vertex_ids, h=1e-5) -> {vid: float}` (first-order z-velocity per vertex along a unit flex direction); `tip_flex_signatures(fold, creases, basis, tip_vids, hub_of_tip, h1=1e-5, h2=1e-6, agree_rtol=1e-4) -> list[dict]` (one `{tip_vid: hub-relative z-velocity}` per basis column; raises `FlexInstrumentError` on step-size disagreement).

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
from rigid_fold import (FlexInstrumentError, tip_flex_signatures,
                        tip_flex_velocity)

# Single-crease strip: two unit squares sharing crease (1,4). One crease,
# no closure constraints -> dof 1. Hand derivation (test oracle): the
# non-root face rotates about the line x=1; its far corners have
# |dz/drho| = distance to the axis = 1 exactly; crease vertices (1, 4)
# never move. Which geometric face is root depends on _extract_faces
# order (both have area 1 -> lowest index wins), so assertions use the
# order-free facts: one far corner moves |1|, the other 0, crease = 0.
STRIP = {
    "vertices_coords": [[0, 0], [1, 0], [2, 0], [2, 1], [1, 1], [0, 1]],
    "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0],
                       [1, 4]],
    "edges_assignment": ["B", "B", "B", "B", "B", "B", "M"],
}


class TestFlexSignatures:
    def _strip_basis(self):
        creases, B, res = null_space_basis(STRIP)
        assert res.dof == 1 and B.shape == (1, 1)
        return creases, B

    def test_strip_velocity_magnitudes(self):
        creases, B = self._strip_basis()
        v = tip_flex_velocity(STRIP, creases, B[:, 0], [0, 1, 2, 4])
        far = sorted([abs(v[0]), abs(v[2])])
        assert far[0] == pytest.approx(0.0, abs=1e-9)
        assert far[1] == pytest.approx(1.0, rel=1e-6)
        assert abs(v[1]) < 1e-9 and abs(v[4]) < 1e-9  # crease line

    def test_strip_velocity_antisymmetry(self):
        creases, B = self._strip_basis()
        vp = tip_flex_velocity(STRIP, creases, B[:, 0], [0, 2])
        vm = tip_flex_velocity(STRIP, creases, -B[:, 0], [0, 2])
        for vid in (0, 2):
            assert vp[vid] == pytest.approx(-vm[vid], abs=1e-9)

    def test_signatures_relative_to_hub(self):
        creases, B = self._strip_basis()
        # treat the moving far corner as tip, a crease vertex as its hub
        v = tip_flex_velocity(STRIP, creases, B[:, 0], [0, 2])
        tip = 2 if abs(v[2]) > abs(v[0]) else 0
        sigs = tip_flex_signatures(STRIP, creases, B, [tip], {tip: 1})
        assert len(sigs) == 1
        assert abs(sigs[0][tip]) == pytest.approx(1.0, rel=1e-6)

    def test_dual_step_guard_fires(self):
        creases, B = self._strip_basis()
        v = tip_flex_velocity(STRIP, creases, B[:, 0], [0, 2])
        tip = 2 if abs(v[2]) > abs(v[0]) else 0
        # h1=0.5 gives sin(0.5)/0.5 ~ 0.9589 vs ~1.0 at h2 -> relative
        # disagreement ~4e-2 >> 1e-6 -> the instrument must refuse.
        with pytest.raises(FlexInstrumentError, match="disagreement"):
            tip_flex_signatures(STRIP, creases, B, [tip], {tip: 1},
                                h1=0.5, h2=1e-6, agree_rtol=1e-6)

    def test_unknown_vertex_raises(self):
        creases, B = self._strip_basis()
        with pytest.raises(FlexInstrumentError, match="no face"):
            tip_flex_velocity(STRIP, creases, B[:, 0], [99])
```

- [ ] **Step 2: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestFlexSignatures -q
```

Expected: FAIL — `ImportError: cannot import name 'FlexInstrumentError'`.

- [ ] **Step 3: Implement in `mcp_harness/rigid_fold.py`** (append after `null_space_basis`)

```python
class FlexInstrumentError(RuntimeError):
    """The diagnosis instrument itself failed (step-size disagreement,
    unknown vertex) -- an instrument fault, never a verdict."""


def _vertex_face_slot(state: RigidFoldState, vid: int):
    """Deterministic image choice for a vertex: (face_index, slot) of the
    LOWEST-index face containing it. Along a flex direction the per-face
    images of a shared vertex differ only at O(h^2), so the choice cannot
    affect a first-order velocity."""
    for fi, f in enumerate(state.faces):
        if vid in f:
            return fi, list(f).index(vid)
    raise FlexInstrumentError(f"vertex {vid} is in no face")


def tip_flex_velocity(fold: dict, creases: list, direction, vertex_ids,
                      h: float = 1e-5):
    """First-order out-of-plane velocity {vid: dz/dt} along the unit flex
    `direction` (coefficients over `creases`), by central finite difference
    of fold_to_3d at rho = +/- h * direction. At the flat state a flex
    produces pure z-motion (in-plane motion is second order)."""
    d = np.asarray(direction, dtype=float)

    def z_at(t):
        st = fold_to_3d(fold, dict(zip(creases, t * d)))
        out = {}
        for vid in vertex_ids:
            fi, sl = _vertex_face_slot(st, vid)
            out[vid] = float(st.folded_vertices[fi][sl][2])
        return out

    zp, zm = z_at(h), z_at(-h)
    return {v: (zp[v] - zm[v]) / (2.0 * h) for v in vertex_ids}


def tip_flex_signatures(fold: dict, creases: list, basis: np.ndarray,
                        tip_vids, hub_of_tip: dict,
                        h1: float = 1e-5, h2: float = 1e-6,
                        agree_rtol: float = 1e-4):
    """One dict per flex-basis column: {tip_vid: z-velocity of the tip
    RELATIVE to its hub} (mirrors pose_target's leaf-minus-hub bone
    convention). Every velocity is computed at both step sizes; a
    disagreement |v1 - v2| > agree_rtol * max(|v1|, |v2|, 1e-9) raises
    FlexInstrumentError (never 0.0 tolerances; the 1e-9 floor keeps
    exact zeros comparable)."""
    vids = sorted(set(tip_vids) | set(hub_of_tip.values()))
    sigs = []
    for j in range(basis.shape[1]):
        d = basis[:, j]
        v1 = tip_flex_velocity(fold, creases, d, vids, h=h1)
        v2 = tip_flex_velocity(fold, creases, d, vids, h=h2)
        for v in vids:
            if abs(v1[v] - v2[v]) > agree_rtol * max(abs(v1[v]),
                                                     abs(v2[v]), 1e-9):
                raise FlexInstrumentError(
                    f"step-size disagreement at v{v}, direction {j}:"
                    f" {v1[v]!r} (h={h1}) vs {v2[v]!r} (h={h2})")
        sigs.append({t: v1[t] - v1[hub_of_tip[t]] for t in tip_vids})
    return sigs
```

Also update `probe_front_flex.sq_vertex_index` to raise the shared error type
— change its import block to `from rigid_fold import FlexInstrumentError` and
its raise to `raise FlexInstrumentError(f"{len(hits)} squared-fold vertices at {key}")`.
(The Task-2 test matched `Exception, match="vert"` so it stays green.)

- [ ] **Step 4: Run tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/rigid_fold.py mcp_harness/probe_front_flex.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): tip flex velocities + hub-relative signatures with dual-step-size instrument guard (strip fixture pins |dz/drho|=1)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: `front_selectivity` — the D1 verdict quantity (Gate D1, part 3)

**Files:**
- Modify: `mcp_harness/rigid_fold.py` (add `SelectivityResult`, `front_selectivity`)
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)

**Interfaces:**
- Consumes: signatures from `tip_flex_signatures` (Task 4).
- Produces: `rigid_fold.SelectivityResult` (frozen dataclass: `r_star: float` — may be `inf`, `w_coeffs: np.ndarray` unit vector in basis coefficients, `w_creases: np.ndarray` same direction in crease space, `unbounded: bool`, `front_rms: float`, `backhead_rms: float`); `front_selectivity(signatures, front, back, head, basis) -> SelectivityResult` where `front`/`back` are lists of tip vids and `head` a single vid.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
from rigid_fold import front_selectivity


class TestFrontSelectivity:
    # Synthetic 2-dim flex space over three tips f=10, b=20, h=30.
    # Hand derivation (comment = test oracle):
    #   direction 1 velocities: f=1, b=2, h=0
    #   direction 2 velocities: f=2, b=0, h=1
    #   s_f=(1,2), s_b=(2,0), s_h=(0,1)
    #   A = s_f s_f^T = [[1,2],[2,4]];  B = s_b s_b^T + s_h s_h^T = [[4,0],[0,1]]
    #   B^-1 A eigenvalues {0, 4.25} -> r* = sqrt(4.25), w* prop (1, 8).
    BOUNDED = [{10: 1.0, 20: 2.0, 30: 0.0}, {10: 2.0, 20: 0.0, 30: 1.0}]

    def test_bounded_case_exact(self):
        res = front_selectivity(self.BOUNDED, [10], [20], 30, np.eye(2))
        assert not res.unbounded
        assert res.r_star == pytest.approx(np.sqrt(4.25), rel=1e-9)
        w = res.w_coeffs / np.linalg.norm(res.w_coeffs)
        expect = np.array([1.0, 8.0]) / np.sqrt(65.0)
        assert abs(float(w @ expect)) == pytest.approx(1.0, rel=1e-9)
        # basis = identity -> crease-space direction equals coefficients
        assert np.allclose(res.w_creases, res.w_coeffs)

    def test_unbounded_when_backhead_vanishes(self):
        # direction 2 moves ONLY the front tip -> r* unbounded
        sigs = [{10: 1.0, 20: 2.0, 30: 1.0}, {10: 1.0, 20: 0.0, 30: 0.0}]
        res = front_selectivity(sigs, [10], [20], 30, np.eye(2))
        assert res.unbounded and res.r_star == float("inf")
        assert res.backhead_rms == pytest.approx(0.0, abs=1e-12)

    def test_front_dead_subspace_is_not_unbounded(self):
        # back+head vanish along direction 2 but so does front: the
        # ratio must restrict to B's range, not report inf.
        sigs = [{10: 1.0, 20: 2.0, 30: 1.0}, {10: 0.0, 20: 0.0, 30: 0.0}]
        res = front_selectivity(sigs, [10], [20], 30, np.eye(2))
        assert not res.unbounded
        # on B's range: r = 1 / sqrt(4 + 1) = sqrt(1/5)
        assert res.r_star == pytest.approx(np.sqrt(0.2), rel=1e-9)

    def test_single_direction_ratio(self):
        sigs = [{10: 1.0, 20: 2.0, 30: 0.0}]
        res = front_selectivity(sigs, [10], [20], 30, np.eye(1))
        assert res.r_star == pytest.approx(0.5, rel=1e-9)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestFrontSelectivity -q
```

Expected: FAIL — `ImportError: cannot import name 'front_selectivity'`.

- [ ] **Step 3: Implement in `mcp_harness/rigid_fold.py`** (append)

```python
@dataclass(frozen=True)
class SelectivityResult:
    r_star: float           # max front_rms / sqrt(back_rms^2 + head^2); inf ok
    w_coeffs: np.ndarray    # optimal direction, basis coefficients (unit)
    w_creases: np.ndarray   # the same direction in crease space (basis @ w)
    unbounded: bool         # back+head motion vanishes along w_coeffs
    front_rms: float
    backhead_rms: float


def front_selectivity(signatures, front, back, head, basis: np.ndarray):
    """Maximize r(w) = front_rms(w) / sqrt(back_rms(w)^2 + head(w)^2) over
    unit w in the flex space (design spec Gate D1). signatures: one
    {tip_vid: hub-relative z-velocity} per basis column. Closed form via
    the generalized symmetric eigenproblem on the (dof x dof) restricted
    quadratic forms A (front mean-square) and B (back mean-square + head
    square); pure numpy (Cholesky reduction + eigh). B-singular subspaces
    are handled explicitly: nonzero front motion there means r is
    unbounded; otherwise the ratio restricts to B's range."""
    d = len(signatures)
    if d == 0:
        raise FlexInstrumentError("no flex directions (dof 0)")

    def form(vids):
        M = np.zeros((d, d))
        for v in vids:
            s = np.asarray([sig[v] for sig in signatures])
            M += np.outer(s, s)
        return M / len(vids)

    A = form(front)                       # front_rms(w)^2 = w' A w
    B = form(back) + form([head])         # back_rms^2 + head^2 = w' B w
    scale = max(float(np.abs(A).max()), float(np.abs(B).max()), 1e-30)
    tol = 1e-12 * scale

    def result(w, unbounded):
        w = w / np.linalg.norm(w)
        fr = float(np.sqrt(max(float(w @ A @ w), 0.0)))
        bh = float(np.sqrt(max(float(w @ B @ w), 0.0)))
        r = float("inf") if unbounded else fr / bh
        return SelectivityResult(r_star=r, w_coeffs=w, w_creases=basis @ w,
                                 unbounded=unbounded, front_rms=fr,
                                 backhead_rms=bh)

    evB, VB = np.linalg.eigh(B)
    null = VB[:, evB <= tol]
    if null.shape[1]:
        An = null.T @ A @ null
        ev, U = np.linalg.eigh(An)
        if ev[-1] > tol:
            return result(null @ U[:, -1], unbounded=True)
        keep = VB[:, evB > tol]
        if keep.shape[1] == 0:
            raise FlexInstrumentError("all tip motion vanishes on the flex"
                                      " space -- signatures degenerate")
        A2, B2 = keep.T @ A @ keep, keep.T @ B @ keep
    else:
        keep = np.eye(d)
        A2, B2 = A, B
    L = np.linalg.cholesky(B2)
    Li = np.linalg.inv(L)
    ev, U = np.linalg.eigh(Li @ A2 @ Li.T)
    return result(keep @ (Li.T @ U[:, -1]), unbounded=False)
```

- [ ] **Step 4: Run tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/rigid_fold.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): front_selectivity -- closed-form max front/backhead ratio over the flex space, singular-B branches pinned by synthetic oracles

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: Gate D2 package — measured mode, span alignment, vacuity guard

**Files:**
- Modify: `mcp_harness/pose_coupling.py` (add `_response_matrix`, `dominant_mode`; refactor `rank1_share` to share the matrix builder)
- Modify: `mcp_harness/probe_front_flex.py` (add `group_signature_r3`, `degenerate_front`, `span_alignment`, `rank_measured_against`)
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)

**Interfaces:**
- Consumes: `CouplingTable.scored_cells() -> {key: CouplingRow}` with `delta_groups`; signatures from Task 4; `pc.GROUPS == ("front", "back", "head")`.
- Produces: `pose_coupling.dominant_mode(cells) -> (mode ndarray(3) unit sign-normalized, share float) | None`; `probe_front_flex.group_signature_r3(sig, fronts, backs, head) -> ndarray(3)` (unsigned RMS per group); `degenerate_front(signatures, fronts) -> bool`; `span_alignment(mode, sig_vecs, align_threshold=ALIGN_THRESHOLD, vacuity_cond=VACUITY_COND) -> {"captured", "cond", "rank", "status"}` with status in `{"PASS", "FAIL", "VACUOUS"}`; `rank_measured_against(cells, front_dir_r3) -> [( |cos|, key )]` descending.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
def _cell(key, front, back, head):
    return pc.CouplingRow(gate="gate1", key=key, ops=[], verdict="scored",
                          site=key.split("|")[0],
                          delta_groups={"front": front, "back": back,
                                        "head": head})


class TestD2:
    def test_dominant_mode_recovers_rank1(self):
        cells = {"a": _cell("a", 1.0, 2.0, 3.0), "b": _cell("b", 2.0, 4.0, 6.0)}
        mode, share = pc.dominant_mode(cells)
        assert share == pytest.approx(1.0, rel=1e-12)
        expect = np.array([1.0, 2.0, 3.0]) / np.sqrt(14.0)
        assert np.allclose(mode, expect, atol=1e-12)  # sign-normalized +

    def test_dominant_mode_none_under_two_rows(self):
        assert pc.dominant_mode({"a": _cell("a", 1, 2, 3)}) is None

    def test_rank1_share_unchanged_by_refactor(self):
        cells = {"a": _cell("a", 1.0, 0.0, 0.0), "b": _cell("b", 0.0, 1.0, 0.0)}
        assert pc.rank1_share(cells) == pytest.approx(0.5, rel=1e-12)

    def test_span_alignment_pass(self):
        sigs = [np.array([1.0, 0, 0]), np.array([0, 1.0, 0])]
        out = pff.span_alignment(np.array([0.6, 0.8, 0.0]), sigs)
        assert out["status"] == "PASS"
        assert out["captured"] == pytest.approx(1.0, rel=1e-9)

    def test_span_alignment_fail(self):
        sigs = [np.array([1.0, 0, 0]), np.array([0, 1.0, 0])]
        out = pff.span_alignment(np.array([0.0, 0.0, 1.0]), sigs)
        assert out["status"] == "FAIL"
        assert out["captured"] == pytest.approx(0.0, abs=1e-9)

    def test_span_alignment_vacuous(self):
        sigs = [np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                np.array([0, 0, 1.0])]
        out = pff.span_alignment(np.array([0.5, 0.5, 0.5]), sigs)
        assert out["status"] == "VACUOUS" and out["rank"] == 3

    def test_degenerate_front(self):
        dead = [{1: 1e-15, 2: 5.0, 3: 4.0}]
        live = [{1: 0.5, 2: 5.0, 3: 4.0}]
        assert pff.degenerate_front(dead, [1]) is True
        assert pff.degenerate_front(live, [1]) is False

    def test_rank_measured_against_orders_by_cos(self):
        cells = {"hit": _cell("hit", 1.0, 0.0, 0.0),
                 "miss": _cell("miss", 0.0, 1.0, 0.0)}
        ranked = pff.rank_measured_against(cells, np.array([1.0, 0.0, 0.0]))
        assert [k for _c, k in ranked] == ["hit", "miss"]
        assert ranked[0][0] == pytest.approx(1.0, rel=1e-9)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestD2 -q
```

Expected: FAIL — `AttributeError: module 'pose_coupling' has no attribute 'dominant_mode'`.

- [ ] **Step 3: Implement**

In `mcp_harness/pose_coupling.py`, replace `rank1_share` with:

```python
def _response_matrix(cells):
    """(n_cells, 3) matrix of measured delta_groups in GROUPS order."""
    return np.asarray([[float(r.delta_groups[g]) for g in GROUPS]
                       for r in cells.values()], dtype=float)


def rank1_share(cells):
    """Rank-1 energy share of the op x group response matrix
    (informational; None when under 2 scored rows)."""
    M = _response_matrix(cells)
    if M.shape[0] < 2:
        return None
    s = np.linalg.svd(M, compute_uv=False)
    denom = float((s ** 2).sum())
    return float(s[0] ** 2 / denom) if denom > 0 else None


def dominant_mode(cells):
    """(unit mode over GROUPS, rank-1 energy share): the dominant
    right-singular vector of the response matrix, sign-normalized so its
    largest-|component| is positive. None when under 2 scored rows."""
    M = _response_matrix(cells)
    if M.shape[0] < 2:
        return None
    _u, s, vt = np.linalg.svd(M)
    denom = float((s ** 2).sum())
    if denom <= 0:
        return None
    mode = vt[0]
    i = int(np.argmax(np.abs(mode)))
    if mode[i] < 0:
        mode = -mode
    return mode, float(s[0] ** 2 / denom)
```

In `mcp_harness/probe_front_flex.py`, append:

```python
def group_signature_r3(sig, fronts, backs, head):
    """Unsigned (front, back, head) RMS aggregation of one per-tip
    signature -- the D1/D2 group observable."""
    def rms(vids):
        return float(np.sqrt(np.mean([sig[v] ** 2 for v in vids])))
    return np.asarray([rms(fronts), rms(backs), rms([head])])


def degenerate_front(signatures, fronts):
    """Hard-lock guard (spec D1): front motion below DEGENERATE_FRONT of
    the total tip-motion norm in EVERY flex direction."""
    for sig in signatures:
        tot = float(np.sqrt(np.mean([v ** 2 for v in sig.values()])))
        fr = float(np.sqrt(np.mean([sig[v] ** 2 for v in fronts])))
        if fr >= DEGENERATE_FRONT * max(tot, 1e-30):
            return False
    return True


def span_alignment(mode, sig_vecs, align_threshold=ALIGN_THRESHOLD,
                   vacuity_cond=VACUITY_COND):
    """D2 calibration: fraction of the |measured mode|'s norm captured by
    the span of the predicted group signatures (sign-free comparison:
    elementwise absolute values). Pinned honesty trap: if the signature
    matrix is well-conditioned full-rank in R^3 the test cannot fail by
    construction -> status VACUOUS (counts as not-failing, flagged at the
    checkpoint)."""
    S = np.asarray(sig_vecs, dtype=float).T          # 3 x d
    m = np.abs(np.asarray(mode, dtype=float))
    m = m / np.linalg.norm(m)
    U, sv, _vt = np.linalg.svd(S)
    smax = float(sv[0]) if sv.size else 0.0
    cond = float(sv[-1] / smax) if smax > 0 else 0.0
    rank = int((sv > 1e-12 * max(smax, 1e-30)).sum())
    if rank:
        Q = U[:, :rank]        # orthonormal, rank-safe span basis (SVD,
        captured = float(np.linalg.norm(Q.T @ m))   # not QR: dependent
    else:                      # columns would defeat a QR-based basis)
        captured = 0.0
    if rank == 3 and cond > vacuity_cond:
        status = "VACUOUS"
    elif captured >= align_threshold:
        status = "PASS"
    else:
        status = "FAIL"
    return {"captured": captured, "cond": cond, "rank": rank,
            "status": status}


def rank_measured_against(cells, front_dir_r3):
    """Search-gap readout: |cos| of each measured scored row's unsigned
    delta_groups against the predicted front-direction signature --
    which existing op families already couple to it. Descending."""
    f = np.abs(np.asarray(front_dir_r3, dtype=float))
    f = f / np.linalg.norm(f)
    out = []
    for k, r in cells.items():
        v = np.abs(np.asarray([float(r.delta_groups[g])
                               for g in pc.GROUPS]))
        n = float(np.linalg.norm(v))
        if n > 0:
            out.append((float(f @ v / n), k))
    return sorted(out, reverse=True)
```

- [ ] **Step 4: Run tests (full file — the pose_coupling refactor must not break other suites)**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py tests/test_pose_coupling.py -q
```

Expected: all pass. (If `tests/test_pose_coupling.py` does not exist under that
name, run `ls tests/ | grep -i coupling` and run whichever test file covers
`pose_coupling` — the refactor is behavior-preserving and must stay green.)

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pose_coupling.py mcp_harness/probe_front_flex.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): D2 package -- measured dominant mode, sign-free span alignment with pinned vacuity guard, degenerate-front check, coupling ranking

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: Probe assembly — `probe_front_flex.main()` + verdict rule

**Files:**
- Modify: `mcp_harness/probe_front_flex.py` (add `d1_verdict`, `main`)
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 2–6 plus `probe_folding_dof._anchors_ok()`, `rigid_fold.null_space_basis/tip_flex_signatures/front_selectivity/tip_flex_velocity/folding_dof`.
- Produces: `d1_verdict(r_star, degenerate) -> str` (one of `"STRUCTURAL-LOCK (degenerate)"`, `"STRUCTURAL-LOCK"`, `"SEARCH-GAP"`, `"GRAY"`); runnable probe writing `probe_front_flex.out.json`; exit codes 0/1/2 per the module docstring.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
class TestVerdictRule:
    # Boundary semantics pinned from the spec: >= 1.0 search-gap,
    # <= 0.2 structural, strictly between = gray; degenerate overrides.
    def test_boundaries(self):
        assert pff.d1_verdict(1.0, False) == "SEARCH-GAP"
        assert pff.d1_verdict(float("inf"), False) == "SEARCH-GAP"
        assert pff.d1_verdict(0.2, False) == "STRUCTURAL-LOCK"
        assert pff.d1_verdict(0.5, False) == "GRAY"
        assert pff.d1_verdict(5.0, True) == "STRUCTURAL-LOCK (degenerate)"


class TestDogPipelineIntegrity:
    """Structural integrity of the real D1 pipeline on the served dog.
    Deliberately does NOT assert the verdict, r*, or any threshold
    comparison -- the measurement happens when the probe RUNS (Task 8),
    after the rules were pinned. These assertions only prove the
    instrument operates on the real substrate."""

    def test_d1_pipeline_runs_on_dog_squared(self):
        raw, sq = pff.served_dog()
        nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
        pff.naming_parity(nb)
        creases, basis, res = null_space_basis(sq)
        assert res.dof == 3 and basis.shape == (38, 3)
        site_by_vid = {s.vid: s for s in nb.sites.values()}
        pose_vids = list(nb.fronts) + list(nb.backs) + [nb.head]
        tip_sq = {v: pff.sq_vertex_index(sq, site_by_vid[v].xy)
                  for v in pose_vids}
        hub_sq = {h: pff.sq_vertex_index(sq, nb.targets[h])
                  for h in ("hub_front", "hub_rear")}
        hub_of_tip = {tip_sq[v]: hub_sq[nb.leaf_hub_name[v]]
                      for v in pose_vids}
        sigs = tip_flex_signatures(sq, creases, basis,
                                   list(hub_of_tip), hub_of_tip)
        assert len(sigs) == 3 and all(len(s) == 5 for s in sigs)
        sel = front_selectivity(
            sigs, [tip_sq[v] for v in nb.fronts],
            [tip_sq[v] for v in nb.backs], tip_sq[nb.head], basis)
        assert sel.r_star >= 0.0
        assert sel.w_creases.shape == (38,)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestVerdictRule -q
```

Expected: FAIL — `AttributeError: ... 'd1_verdict'`. (`TestDogPipelineIntegrity`
should already pass — it uses only Task 3–5 APIs; if it fails, that is a real
finding about the real substrate: STOP and report, do not adjust tolerances.)

- [ ] **Step 3: Implement `d1_verdict` + `main` in `mcp_harness/probe_front_flex.py`**

Add imports at the top (after the existing ones):

```python
import probe_folding_dof
from rigid_fold import (FlexInstrumentError, folding_dof, front_selectivity,
                        null_space_basis, tip_flex_signatures,
                        tip_flex_velocity)
```

Append:

```python
def d1_verdict(r_star, degenerate):
    """Pinned decision rule (spec Gate D1). Inclusive bounds."""
    if degenerate:
        return "STRUCTURAL-LOCK (degenerate)"
    if r_star >= R_SEARCH_GAP:
        return "SEARCH-GAP"
    if r_star <= R_STRUCTURAL:
        return "STRUCTURAL-LOCK"
    return "GRAY"


def _ck(name, ok):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    return ok


def main():
    # ---------------- D0: refuse verdicts unless every anchor holds
    print("=== Gate D0: instrument + data preflight ===")
    if not probe_folding_dof._anchors_ok():
        print("ANCHORS FAILED -- instrument untrustworthy, no verdicts.")
        return 1
    raw, sq = served_dog()
    res = folding_dof(sq)
    if not _ck(f"dog-squared dof == {EXPECTED_DOF} (got {res.dof},"
               f" rank {res.rank}, creases {res.n_creases})",
               res.dof == EXPECTED_DOF):
        return 1
    if not os.path.exists(COUPLING_JSONL):
        print(f"MISSING {COUPLING_JSONL}\ncopy it (read-only source):\n"
              "  cp <repo>/"
              "mcp_harness/probe_dog_coupling.out.jsonl mcp_harness/")
        return 1
    table = pc.CouplingTable(COUPLING_JSONL)
    try:
        counts = reconcile_coupling(table)
        nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
        naming_parity(nb)
    except ValueError as exc:
        print(f"D0 FAIL: {exc}")
        return 1
    _ck(f"coupling tallies {counts}", True)
    _ck("naming parity (recorded grouping, ambiguity 0)", True)

    # ---------------- D1: flex-space front selectivity
    print("\n=== Gate D1: flex-space tip coupling ===")
    creases, basis, _res = null_space_basis(sq)
    site_by_vid = {s.vid: s for s in nb.sites.values()}
    pose_vids = list(nb.fronts) + list(nb.backs) + [nb.head]
    tip_sq = {v: sq_vertex_index(sq, site_by_vid[v].xy) for v in pose_vids}
    hub_sq = {h: sq_vertex_index(sq, nb.targets[h])
              for h in ("hub_front", "hub_rear")}
    hub_of_tip = {tip_sq[v]: hub_sq[nb.leaf_hub_name[v]]
                  for v in pose_vids}
    fronts_sq = [tip_sq[v] for v in nb.fronts]
    backs_sq = [tip_sq[v] for v in nb.backs]
    head_sq = tip_sq[nb.head]
    try:
        sigs = tip_flex_signatures(sq, creases, basis,
                                   list(hub_of_tip), hub_of_tip)
    except FlexInstrumentError as exc:
        print(f"D1 INSTRUMENT FAIL: {exc}")
        return 1
    degen = degenerate_front(sigs, fronts_sq)
    sel = front_selectivity(sigs, fronts_sq, backs_sq, head_sq, basis)
    verdict = d1_verdict(sel.r_star, degen)
    print(f"r* = {sel.r_star:.6g}  (front_rms {sel.front_rms:.6g},"
          f" backhead_rms {sel.backhead_rms:.6g},"
          f" unbounded {sel.unbounded}, degenerate {degen})")
    print(f"D1 VERDICT: {verdict}"
          f"   [rule: >= {R_SEARCH_GAP} search-gap,"
          f" <= {R_STRUCTURAL} structural, else gray]")

    # ---------------- D2: cross-validation against the measured table
    print("\n=== Gate D2: empirical cross-validation (162-row table) ===")
    cells = table.scored_cells()
    mode, share = pc.dominant_mode(cells)
    sig_r3 = [group_signature_r3(s, fronts_sq, backs_sq, head_sq)
              for s in sigs]
    align = span_alignment(mode, sig_r3)
    print(f"measured mode {np.round(mode, 4).tolist()} (share {share:.3f});"
          f" captured {align['captured']:.3f}, cond {align['cond']:.3f},"
          f" rank {align['rank']} -> {align['status']}")
    ranking = None
    if verdict in ("SEARCH-GAP", "GRAY"):
        w = sel.w_creases / np.linalg.norm(sel.w_creases)
        vids = sorted(set(hub_of_tip) | set(hub_of_tip.values()))
        vel = tip_flex_velocity(sq, creases, w, vids)
        wsig = {t: vel[t] - vel[hub_of_tip[t]] for t in hub_of_tip}
        front_dir_r3 = group_signature_r3(wsig, fronts_sq, backs_sq,
                                          head_sq)
        ranking = rank_measured_against(cells, front_dir_r3)[:10]
        print("top measured couplings to the predicted front direction:")
        for c, k in ranking[:5]:
            print(f"  |cos| {c:.3f}  {k}")

    out = {
        "thresholds": {"R_SEARCH_GAP": R_SEARCH_GAP,
                       "R_STRUCTURAL": R_STRUCTURAL,
                       "DEGENERATE_FRONT": DEGENERATE_FRONT,
                       "ALIGN_THRESHOLD": ALIGN_THRESHOLD,
                       "VACUITY_COND": VACUITY_COND},
        "d0": {"dof": res.dof, "rank": res.rank,
               "n_creases": res.n_creases, "tallies": counts,
               "grouping": nb.grouping},
        "d1": {"r_star": sel.r_star, "unbounded": sel.unbounded,
               "front_rms": sel.front_rms,
               "backhead_rms": sel.backhead_rms,
               "degenerate": degen, "verdict": verdict,
               "w_creases": {f"{u}-{v}": float(c) for (u, v), c
                             in zip(creases, sel.w_creases)},
               "signatures_r3": [s.tolist() for s in sig_r3],
               "tip_sq": {f"v{v}": i for v, i in tip_sq.items()},
               "hub_sq": hub_sq},
        "d2": {"mode": mode.tolist(), "share": share, **align},
        "d3_ranking": ranking,
    }
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=2, default=float)
    print(f"\nwrote {OUT_JSON}")
    if align["status"] == "FAIL":
        print("D2 NON-VACUOUS FAIL -- instrument uncalibrated. HALT to"
              " checkpoint: NO pilot capture without user approval.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

(`json.dump(..., default=float)` handles `r_star = inf` by serializing to
`Infinity`, which `json.load` round-trips; that is acceptable for an
uncommitted probe artifact.)

- [ ] **Step 4: Run tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: all pass (~20 tests). Do NOT run the probe itself in this task —
running it is Task 8, so the measurement stays separated from the build.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/probe_front_flex.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): probe_front_flex assembly -- D0 refuse-verdict ladder, D1 verdict rule (pinned bounds), D2 calibration + ranking, exit codes 0/1/2

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 8: RUN the sim-free diagnosis (Gates D0–D2 measured) — decision point

This task produces the slice's headline measurement. It may be run by a
subagent (NO sim involved), but its output interpretation follows the pinned
branch map in Global Constraints — no judgment calls.

**Files:**
- Modify: `.superpowers/sdd/progress.md` (ledger entry)
- Output (uncommitted): `mcp_harness/probe_front_flex.out.json`

- [ ] **Step 1: Run the probe**

```bash
cd mcp_harness && .venv/bin/python probe_front_flex.py; echo "exit=$?"
```

Expected: D0 all PASS, a D1 verdict line, a D2 status line, `wrote ...out.json`,
exit 0 (or exit 2 on D2 non-vacuous FAIL — see branch map; exit 1 means an
instrument/preflight bug: fix that before believing anything).

- [ ] **Step 2: Record the measurement in the ledger**

Append to `.superpowers/sdd/progress.md`: date, task, the full D1 line
(r*, front_rms, backhead_rms, unbounded, degenerate, verdict), the D2 line
(mode, share, captured, cond, status), and which plan branch fires
(Tasks 9–10 or straight to Task 11).

- [ ] **Step 3: Full suite (pre-checkpoint gate)**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q
```

Expected: everything green (baseline + all new tests).

- [ ] **Step 4: Commit the ledger**

```bash
git add .superpowers/sdd/progress.md
git commit -m "docs(b5-front-dof): Task-8 measurement ledger -- D0-D2 verdict recorded [numbers in ledger; probe output uncommitted]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

**DECISION POINT (pinned, no judgment):** verdict `STRUCTURAL-LOCK*` or exit 2
→ skip Tasks 9–10, go to Task 11. Verdict `SEARCH-GAP`/`GRAY` with D2
PASS/VACUOUS → Tasks 9–10, then 11.

---

### Task 9 (CONDITIONAL — fires only on SEARCH-GAP/GRAY): pilot builder `probe_front_pilot.py`

**Files:**
- Create: `mcp_harness/probe_front_pilot.py`
- Modify: `mcp_harness/tests/test_flex_diagnosis.py` (append)

**Interfaces:**
- Consumes: `probe_front_flex.out.json` (`d1.w_creases`, `d1.verdict`), `probe_front_flex` module functions, `probe_dog_coupling.open_session_with_anchor(sim, table, session)`, `probe_dog_coupling._measure(sim, base, targets, shaped, tgt)`, `probe_dog_coupling.fox_targets_with_fallback()`, `probe_dog_coupling._session_id()`, `pose_base.NamedBase.apply_strict(ops)`, `pose_base.unique_targets`, `sim_capture.SimSession()` (context manager), `pc.CouplingTable`/`CouplingRow`.
- Produces: runnable pilot driver writing `probe_front_pilot.out.jsonl` + `probe_front_pilot.out.json`; pure functions `support_creases(w, energy=0.9, cap=10)`, `crease_contexts(sq, nb, support)`, `build_recipes(nb, contexts, gate1_terminal_keys)`.

**Pinned constants (spec Gate D3 — do not tune):** `PILOT_BUDGET = 40` sim
reads total (every `sim.capture` call counts, INCLUDING the session anchor and
park retries), `CANDIDATE_CAP = 8`, `READS_PER_RECIPE = 3`, `PARK_RETRIES = 3`
(total attempts per read slot), `CONFIRM_FRONT_DELTA = 20.0` degrees toward
the fox front target (mean of 3), baseline re-read ×3 first.

- [ ] **Step 1: Write the failing tests for the pure translation functions**

Append to `mcp_harness/tests/test_flex_diagnosis.py`:

```python
import probe_front_pilot as pfp


class TestPilotTranslation:
    def test_support_creases_energy_rule(self):
        w = {(1, 2): 3.0, (3, 4): 1.0, (5, 6): 0.1}
        # energies 9 / 1 / 0.01 -> 9/10.01 = 0.899 < 0.9 -> need two
        sup = pfp.support_creases(w, energy=0.9, cap=10)
        assert sup == [(1, 2), (3, 4)]

    def test_support_creases_cap(self):
        w = {(i, i + 1): 1.0 for i in range(20)}
        assert len(pfp.support_creases(w, energy=0.999, cap=10)) == 10

    def test_build_recipes_excludes_measured_cells_and_caps(self):
        raw, sq = pff.served_dog()
        nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
        # context weights: both fronts + rear hub
        contexts = {"front_v13": 2.0, "front_v18": 1.5, "hub_rear": 1.0}
        gate1 = {"front_v13|outside|142.5|0.5"}  # pretend-measured
        recipes = pfp.build_recipes(nb, contexts, gate1)
        assert 0 < len(recipes) <= pfp.CANDIDATE_CAP
        ids = [rid for rid, _ops in recipes]
        assert len(ids) == len(set(ids))          # deduped
        assert all(rid not in gate1 for rid in ids)  # novelty rule
        # the atomic front-pair unit exists when both fronts have weight
        assert any(rid.startswith("frontpair|") for rid in ids)
        # every recipe's ops parse through the shaping layer's grammar
        for _rid, ops in recipes:
            assert all(isinstance(o, str) and ":" in o for o in ops)
```

- [ ] **Step 2: Run to verify failure**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestPilotTranslation -q
```

Expected: FAIL — `ModuleNotFoundError: No module named 'probe_front_pilot'`.

- [ ] **Step 3: Create `mcp_harness/probe_front_pilot.py`**

```python
"""Gate D3 pilot (CONDITIONAL: SEARCH-GAP/GRAY only) -- b5-front-dof spec.

Translates the D1 optimal flex direction w* into <= 8 NEW candidate
excitations (never re-measuring a terminal gate-1 cell) and measures them
STANDALONE from the unshaped base, x3 reads each, under a hard 40-read
budget. CONFIRM = front group moves >= 20 deg toward the fox front target
(mean of 3). Selectivity is reported, not verdict-bearing.

CONTROLLER-ONLY RUN (headed SimSession). Requires in this worktree:
web/frontend/dist, headless_treemaker*.so, mcp_harness/.venv (Task 10
copies them).

Run:  cd mcp_harness && .venv/bin/python probe_front_pilot.py
"""
import json
import os

import numpy as np

import pose_base
import pose_coupling as pc
import probe_dog_coupling as pdc
import probe_front_flex as pff
import sim_capture

_HERE = os.path.dirname(os.path.abspath(__file__))
FLEX_JSON = pff.OUT_JSON
OUT_JSONL = os.path.join(_HERE, "probe_front_pilot.out.jsonl")
OUT_JSON = os.path.join(_HERE, "probe_front_pilot.out.json")

# ---- pinned constants (spec Gate D3; do not tune) ----------------------
PILOT_BUDGET = 40          # hard cap on sim.capture calls, anchor included
CANDIDATE_CAP = 8
READS_PER_RECIPE = 3
PARK_RETRIES = 3           # total attempts per read slot (persistent-park)
CONFIRM_FRONT_DELTA = 20.0  # deg toward target, mean of 3 (~3x the +/-7
                            # shaped-re-read noise band)
SUPPORT_ENERGY = 0.9
SUPPORT_CAP = 10


class BudgetExhausted(RuntimeError):
    pass


class ReadBudget:
    def __init__(self, cap):
        self.cap, self.used = cap, 0

    def spend(self, n=1):
        if self.used + n > self.cap:
            raise BudgetExhausted(f"{self.used}+{n} > {self.cap}")
        self.used += n


def load_flex(path=FLEX_JSON):
    """(full json, {edge-key tuple: w component}) -- refuses to run on a
    structural verdict (the pilot only fires on SEARCH-GAP/GRAY)."""
    with open(path) as fh:
        d = json.load(fh)
    if d["d1"]["verdict"].startswith("STRUCTURAL"):
        raise SystemExit("D1 verdict is structural -- pilot must not run")
    w = {tuple(int(x) for x in k.split("-")): float(v)
         for k, v in d["d1"]["w_creases"].items()}
    return d, w


def support_creases(w, energy=SUPPORT_ENERGY, cap=SUPPORT_CAP):
    """Creases carrying the direction: ranked by |component|^2 until the
    cumulative energy share reaches `energy`, capped at `cap`."""
    items = sorted(w.items(), key=lambda kv: -(kv[1] ** 2))
    tot = sum(v ** 2 for _k, v in items) or 1.0
    out, acc = [], 0.0
    for k, v in items:
        out.append(k)
        acc += (v ** 2) / tot
        if acc >= energy or len(out) == cap:
            break
    return out


def crease_contexts(sq, nb, support):
    """{context_name: summed |w|^2-rank weight}: each support crease maps
    to the nearest named anchor (a site tip or a hub) by midpoint distance
    in the squared frame. Weight = 1/(1+rank) so earlier (stronger)
    creases dominate the ordering."""
    V = np.asarray([p[:2] for p in sq["vertices_coords"]], dtype=float)
    anchors = {k: s.xy for k, s in nb.sites.items()}
    anchors["hub_front"] = nb.targets["hub_front"]
    anchors["hub_rear"] = nb.targets["hub_rear"]
    out = {}
    for rank, (u, v) in enumerate(support):
        mid = (V[u] + V[v]) / 2.0
        best = min(anchors, key=lambda a: float(
            np.hypot(mid[0] - anchors[a][0], mid[1] - anchors[a][1])))
        out[best] = out.get(best, 0.0) + 1.0 / (1.0 + rank)
    return out


def _sink_op(nb, site_key, frac):
    s = nb.sites[site_key]
    return f"sink:{s.xy[0]},{s.xy[1]}:{frac * s.axial}"


def build_recipes(nb, contexts, gate1_terminal_keys):
    """Ordered [(recipe_id, [op strings])], deduped, novelty-enforced
    (no recipe id may be a terminal gate-1 cell key -- the pilot buys NEW
    information only), capped at CANDIDATE_CAP. Pinned menu (spec D3:
    existing vocabulary only -- deep/hub/pair units, moderated angles):
      tip context   -> sink frac 1.25 (kind absent from the gate-1 grid);
                       outside theta=30 frac 0.5 (moderated, off-grid);
      hub context   -> reverse_deep theta=105 frac 2.0 at the hub's two
                       sites nearest the hub (beyond-grid depth);
      both fronts weighted -> atomic front-pair units (one recipe, two
                       ops): outside 142.5 and outside 105 at frac 0.5.
    """
    ranked = sorted(contexts, key=contexts.get, reverse=True)
    recipes = []

    def add(rid, ops):
        if rid in gate1_terminal_keys:
            return
        if any(rid == r for r, _o in recipes):
            return
        recipes.append((rid, ops))

    fronts = [k for k in nb.sites if k.startswith("front_")]
    if all(f in contexts for f in fronts) and len(fronts) == 2:
        for theta in (142.5, 105.0):
            ops = []
            for f in sorted(fronts):
                ops += nb.site_op(f, "outside", theta, 0.5)
            add(f"frontpair|outside|{theta:g}|0.5", ops)
    for ctx in ranked:
        if ctx in ("hub_front", "hub_rear"):
            hx, hy = nb.targets[ctx]
            sites = sorted(
                (k for k, s in nb.sites.items() if s.hub == ctx),
                key=lambda k: float(np.hypot(nb.sites[k].xy[0] - hx,
                                             nb.sites[k].xy[1] - hy)))[:2]
            for sk in sites:
                add(f"{sk}|reverse_deep|105|2",
                    nb.site_op(sk, "reverse_deep", 105.0, 2.0))
        else:
            add(f"{ctx}|sink|1.25", [_sink_op(nb, ctx, 1.25)])
            add(f"{ctx}|outside|30|0.5",
                nb.site_op(ctx, "outside", 30.0, 0.5))
    return recipes[:CANDIDATE_CAP]
```

(The measured driver — `main()` — is Step 5; the pure functions land and are
tested first.)

- [ ] **Step 4: Run the translation tests**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py::TestPilotTranslation -q
```

Expected: all pass.

- [ ] **Step 5: Append the measured driver to `probe_front_pilot.py`**

```python
def _read(sim, nb, targets, shaped, budget, table, key, ops, session,
          baseline_angles=None):
    """One read slot: up to PARK_RETRIES attempts, each a budget spend.
    Returns the appended CouplingRow (scored | parked | error)."""
    tgt, dropped = pose_base.unique_targets(shaped, nb.targets)
    last = None
    for _a in range(PARK_RETRIES):
        budget.spend()
        try:
            triple, per_leaf, total, disp, attempts = pdc._measure(
                sim, nb, targets, shaped, tgt)
        except sim_capture.CaptureError as exc:
            last = exc
            if "did not fold" in str(exc):
                continue            # park: retry costs another read
            row = pc.CouplingRow(gate="pilot", key=key, ops=ops,
                                 verdict="error", note=str(exc),
                                 session=session)
            table.append(row)
            return row
        dg = (None if baseline_angles is None else
              {g: triple[g] - baseline_angles[g] for g in pc.GROUPS})
        row = pc.CouplingRow(gate="pilot", key=key, ops=ops,
                             verdict="scored", angles=triple,
                             per_leaf=per_leaf, total=total,
                             delta_groups=dg, disp=disp,
                             attempts=attempts, session=session,
                             note=f"targets_dropped: {dropped}"
                                  if dropped else None)
        table.append(row)
        return row
    row = pc.CouplingRow(gate="pilot", key=key, ops=ops, verdict="parked",
                         note=f"persistent park: {last}", session=session)
    table.append(row)
    return row


def main():
    d, w = load_flex()
    raw, sq = pff.served_dog()
    nb = pose_base.NamedBase(raw, sq, pose_base.DOG_CONFIG)
    pff.naming_parity(nb)
    gate1_keys = pc.CouplingTable(pff.COUPLING_JSONL).resume_keys()
    contexts = crease_contexts(sq, nb, support_creases(w))
    recipes = build_recipes(nb, contexts, gate1_keys)
    targets, prov = pdc.fox_targets_with_fallback()
    print(f"contexts: {contexts}\nrecipes ({len(recipes)}):")
    for rid, ops in recipes:
        print(f"  {rid}: {ops}")
    table = pc.CouplingTable(OUT_JSONL)
    budget = ReadBudget(PILOT_BUDGET)
    summary = {"provenance": prov, "contexts": contexts,
               "recipes": {r: o for r, o in recipes}, "results": {}}
    with sim_capture.SimSession() as sim:
        session = pdc._session_id()
        budget.spend()                      # the anchor is a read
        pdc.open_session_with_anchor(sim, table, session)
        # unshaped baseline x3 (defines 'toward target' from its own data)
        base_rows = [_read(sim, nb, targets, sq, budget, table,
                           f"baseline{i}", [], session) for i in range(3)]
        scored = [r for r in base_rows if r.verdict == "scored"]
        if len(scored) < 3:
            raise sim_capture.CaptureError("pilot baseline not x3-scored")
        angles0 = {g: float(np.mean([r.angles[g] for r in scored]))
                   for g in pc.GROUPS}
        toward = 1.0 if targets["front"] >= angles0["front"] else -1.0
        summary["baseline"] = angles0
        try:
            for rid, ops in recipes:
                shaped = None
                try:
                    shaped = nb.apply_strict(ops)
                except pose_base.OpRefused as exc:
                    table.append(pc.CouplingRow(
                        gate="pilot", key=rid, ops=ops, verdict="refused",
                        note=str(exc), session=session))
                    summary["results"][rid] = {"verdict": "refused"}
                    continue
                rows = [_read(sim, nb, targets, shaped, budget, table,
                              f"{rid}#{i}", ops, session, angles0)
                        for i in range(READS_PER_RECIPE)]
                sc = [r for r in rows if r.verdict == "scored"]
                if len(sc) == READS_PER_RECIPE:
                    dfront = float(np.mean(
                        [r.delta_groups["front"] for r in sc])) * toward
                    summary["results"][rid] = {
                        "verdict": "scored",
                        "front_delta_toward": dfront,
                        "mean_angles": {g: float(np.mean(
                            [r.angles[g] for r in sc]))
                            for g in pc.GROUPS},
                        "confirm": dfront >= CONFIRM_FRONT_DELTA}
                else:
                    summary["results"][rid] = {
                        "verdict": "incomplete",
                        "row_verdicts": [r.verdict for r in rows]}
        except BudgetExhausted as exc:
            summary["budget_exhausted"] = str(exc)
    confirmed = [r for r, v in summary["results"].items()
                 if v.get("confirm")]
    summary["reads_used"] = budget.used
    summary["confirmed"] = confirmed
    summary["pilot_verdict"] = (
        "SEARCH-GAP CONFIRMED" if confirmed else
        "STRUCTURAL FOR PRACTICAL PURPOSES (no candidate moved front"
        f" >= {CONFIRM_FRONT_DELTA} deg; closure-solve escalation goes"
        " on the checkpoint table)")
    with open(OUT_JSON, "w") as fh:
        json.dump(summary, fh, indent=2, default=float)
    print(f"\nreads used: {budget.used}/{PILOT_BUDGET}")
    print(f"PILOT VERDICT: {summary['pilot_verdict']}")
    print(f"wrote {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Re-run the whole test file** (driver import must not break collection)

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_flex_diagnosis.py -q
```

Expected: all pass. (`sim_capture` imports playwright lazily through the
established probe pattern; if collection fails on import, gate the
`import sim_capture` behind `main()`/function scope exactly as
`probe_dog_coupling` does — check its import section and mirror it.)

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/probe_front_pilot.py mcp_harness/tests/test_flex_diagnosis.py
git commit -m "feat(b5-front-dof): D3 pilot -- w*-support -> context -> novelty-enforced recipe menu (cap 8), 40-read budget guard, x3 confirm rule at 20 deg

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 10 (CONDITIONAL, CONTROLLER-ONLY): run the D3 pilot

**HARD RULE:** the controller (main session) runs this task itself. No
subagent may launch the sim (orphan-kill record, two incidents).

- [ ] **Step 1: Copy sim dependencies into the worktree** (read-only source)

```bash
cd <repo>
cp -R <repo>/web/frontend/dist web/frontend/dist
ls web/frontend/dist/simulator/js/ide-bridge.js
```

Expected: dist copied; the bridge file exists (`cp public→dist` is
load-bearing; the bridge itself is NOT modified by this slice).

- [ ] **Step 2: Run the pilot (headed, controller terminal)**

```bash
cd mcp_harness && .venv/bin/python probe_front_pilot.py; echo "exit=$?"
```

Expected: recipe list printed, reads ≤ 40, `PILOT VERDICT:` line, exit 0.
If the session anchor refuses (`SESSION REFUSED`), retry once in a fresh
session; a second refusal is a HALT (report, don't push through).

- [ ] **Step 3: Ledger + commit**

Append the pilot verdict + per-recipe table + reads-used to
`.superpowers/sdd/progress.md`.

```bash
git add .superpowers/sdd/progress.md
git commit -m "docs(b5-front-dof): Task-10 pilot measurement ledger [verdict + reads in ledger; outputs uncommitted]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 11: Checkpoint package (mid-slice user gate)

**Files:**
- Create: `docs/superpowers/2026-07-XX-checkpoint-b5-front-dof-phase-d.md` (use the actual date)
- Modify: `docs/superpowers/specs/2026-07-12-b5-front-dof-diagnosis-design.md` (status banner), `.superpowers/sdd/progress.md`

- [ ] **Step 1: Write the checkpoint document** with exactly these sections
(numbers from the probe outputs and ledger; no rounding beyond 2 decimals):
  1. **Confirmed verdict** — one line: SEARCH GAP / STRUCTURAL LOCK /
     STRUCTURAL-FOR-PRACTICAL-PURPOSES / INSTRUMENT-UNCALIBRATED, with the
     defining numbers (r*, D2 status, pilot confirm list if run).
  2. **Gate-by-gate record** — D0 (anchors, dof, tallies, parity), D1
     (r*, front/backhead RMS, degenerate flag, per-direction signatures_r3),
     D2 (mode, share, captured, cond, status incl. VACUOUS flag), D3 (recipe
     table with per-recipe front_delta_toward and verdicts, reads used) or
     "not fired" with the reason.
  3. **Proposed Phase S scope** — the spec §5 charter matching the verdict
     branch, made concrete: named first gate, capture budget ask, and any
     dependency triggers that fired (back_v12 involvement, kick-hardening,
     closure-solve escalation ask if the pilot dead-heated).
  4. **What is NOT decided** — Phase S detail awaits user approval here.

- [ ] **Step 2: Update the design-spec status banner** — replace
`**Status:** design approved 2026-07-12 (brainstorm with raphaeldchen), not yet
implemented.` with a line recording: Phase D executed, the verdict, and
"Phase S scoping at checkpoint" (one sentence, numbers included).

- [ ] **Step 3: Full suite final check**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -q
```

Expected: green.

- [ ] **Step 4: Commit and present**

```bash
git add docs/superpowers/2026-07-XX-checkpoint-b5-front-dof-phase-d.md docs/superpowers/specs/2026-07-12-b5-front-dof-diagnosis-design.md .superpowers/sdd/progress.md
git commit -m "docs(b5-front-dof): Phase-D checkpoint package [verdict + proposed Phase S scope for user approval]

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Then STOP: present the checkpoint document to the user in-conversation
(verdict, evidence, proposed Phase S scope). Phase S work — including any
plan addendum — begins only on their approval. Do NOT push without asking.

# S4a′ — The projection refuses what it cannot represent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `ProjectActivePaths` refuse a symmetry axis or a paper shape its
hard-coded mirror rows cannot represent, verify (not refuse) boundary pins, expose
the projection's own iteration/residual counters as a margin-to-cliff proxy, and
give the projection's failure string a name in the error vocabulary.

**Architecture:** All engine changes are inside one routine
(`HeadlessTreemaker::ProjectActivePaths`) plus three setters and one new binding.
The routine currently builds active-path rows and mirror rows hard-coded to
`(x,y) → (y,x)`; it reads `mSymAngle` nowhere and reads `w`/`h` only for its
on-paper clamp. Two guards make that hard-coding explicit and loud; a pin ledger
mirroring the existing `mSymPairs` pattern makes pin survival measurable; the
production call site starts passing the out-params it has always discarded.

**Tech Stack:** C++17 via pybind11 (`headless_treemaker`), Python 3.14, pytest.
No new dependencies.

**Spec:** [docs/superpowers/specs/2026-08-04-whole-square-axis-projection-design.md](../specs/2026-08-04-whole-square-axis-projection-design.md) §4.1, §6
**Evidence:** [docs/superpowers/evidence/2026-08-04-axis-corner-capacity/](../evidence/2026-08-04-axis-corner-capacity/)
**Coordination:** [docs/superpowers/goals/COORDINATION.md](../goals/COORDINATION.md)

---

## Global Constraints

- **Base commit `1c9abe0`.** Worktree `.claude/worktrees/goal-1-square-coverage-f25303`, branch `claude/goal-1-square-coverage-f25303`.
- **Build the `.so` IN PLACE, and NOT with bare `./build.sh`.** It defaults to `PYTHON=python3`, which on this machine resolves to a Homebrew interpreter without `pybind11` and **exits producing no `.so` and no obvious failure**. The worktree has no `.venv` of its own. Use exactly:
  ```bash
  cd mcp_harness && PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh
  ```
- **A worktree also needs `oriedita/oriedita-1.1.3.jar` and `OrieditaValidator.class`** (`./build_linter.sh`) or every lint verdict fakes `FAIL-LINT`.
- **Tests:** `cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420`. Bare `make test` never terminates here. Full suite ~14 min and **looks stalled early at near-zero CPU — do not kill it.** Baseline at `1c9abe0`: **2241 passed, 11 skipped, 0 failed**.
- **The shell cwd is `mcp_harness`, not the repo root**, and `tests/` means `mcp_harness/tests`.
- **`mcp_harness/fixtures/scorecard_baseline.jsonl` is FROZEN at `1c9abe0`. Do not regenerate it.** Report the `--baseline` delta and attribute every moved row. A row you cannot attribute is a FINDING — say so in the PR.
- **Never pin a number you did not observe.** Where a step says "record what it prints", paste that value.
- **A bare `HeadlessTreemaker` compile is NOT the serve path.** It is attempt-0 for one exact node list. It is the right instrument for the guard tests here (they are about one routine, not about rescue); it is the wrong one for anything claiming a serve outcome.
- Commit messages end with: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

---

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/TreemakerWrapper.cpp` | **Modify.** `ProjectActivePaths` (guards + pin verification), the three `set_node_*` setters (pin ledger), `build_tree_from_json` (ledger reset), `BuildAndExport`'s call site (pass the out-params), new members, new `projection_report` binding. |
| `mcp_harness/error_recipes.py` | **Modify.** Two appended vocabulary codes. |
| `mcp_harness/tests/test_projection_guards.py` | **Create.** All S4a′ behaviour, engine-driven, isolated subprocess per arm. |
| `mcp_harness/tests/test_error_recipes.py` | **Modify** if it exists, else assertions live in the new file. Vocabulary pins. |
| `docs/superpowers/goals/COORDINATION.md` | **Modify** on merge: release the file claim, post the S4a′ signal for Goal 2. |
| `docs/superpowers/goals/goal-1-whole-square/PROGRESS.md` | **Modify** on merge: S4a′ → done. |

---

## Task 1: The two refusals

**Files:**
- Modify: `mcp_harness/TreemakerWrapper.cpp` — `ProjectActivePaths`
- Test: `mcp_harness/tests/test_projection_guards.py` (create)

**Interfaces:**
- Consumes: `tmTree::GetSymAngle()`, `tmTree::GetPaperWidth/Height()` (existing accessors, present in **both** vendored `tmTree.h` twins).
- Produces: two `std::runtime_error` messages, both containing the exact substring `the active-path projection does not represent`. Task 3 matches on it.

> **Why gate on `syms` and not on `HasSymmetry()`:** `set_symmetry_angle` can set
> an angle with **zero pairs**. The routine then emits no mirror rows at all, so a
> non-45° angle is genuinely harmless there, and refusing would be a false
> positive that breaks unpaired trees. This is a tested property, not a comment.

> **This task is also the ODR pre-flight.** `GetSymAngle()` is declared in both
> `treemaker/Source/tmTree.h` and
> `treemaker/Source/tmModel/tmTreeClasses/tmTree.h` at different offsets (memory
> `treemaker-odr-tmtree-header`). If it reads the wrong member through the wrong
> header, the guard fires on every 45° compile and Task 4's golden run goes red
> immediately. That is the intended signal.

- [ ] **Step 1: Write the failing tests**

Create `mcp_harness/tests/test_projection_guards.py`:

```python
"""S4a' -- ProjectActivePaths refuses what its mirror rows cannot represent.

The routine's mirror rows are hard-coded to (x,y)->(y,x): the reflection about
y=x, which is the paper's centre diagonal ONLY on square paper, and which is
the correct mirror ONLY at a 45-degree symmetry axis. The optimizer's own
condition (tmConditionNodesPaired -> PairFn1A/PairFn1B) is fully general in
mSymLoc/mSymAngle, so at any other axis the two enforce DIFFERENT mirrors and
fight -- measured 2026-08-04, 21 of 49 non-45 sweep cells die inside this
routine and the ones that build come back silently re-symmetrized and still
return PACK.

Every arm runs in a spawned child: the engine can SIGSEGV on a
not-fully-converged base, and a crash must be a verdict, not a harness death.
"""
from __future__ import annotations
import json
import multiprocessing as mp
import queue as _queue

import pytest

import cases

REFUSAL_TOKEN = "the active-path projection does not represent"


def _worker(q, payload_json):
    try:
        import headless_treemaker as ht
        d = json.loads(payload_json)
        e = ht.HeadlessTreemaker()
        e.init_paper(float(d["w"]), float(d["h"]))
        e.build_tree_from_json(json.dumps(d["nodes"]))
        if d["angle"] is not None:
            e.set_symmetry_angle(float(d["angle"]))
        for a, b in d["pairs"]:
            e.apply_symmetry(int(a), int(b))
        for nid, axis, val in d["pins"]:
            if axis == "x":
                e.set_node_on_x(int(nid), float(val))
            elif axis == "y":
                e.set_node_on_y(int(nid), float(val))
            else:
                e.set_node_at(int(nid), float(val[0]), float(val[1]))
        e.run_scale_optimization()
        fold = e.build_and_export()
        q.put(("ok", json.dumps({"fold_len": len(fold),
                                 "report": dict(e.projection_report())})))
    except BaseException as exc:  # noqa: BLE001
        q.put(("err", f"{type(exc).__name__}: {exc}"))


def run(nodes, pairs=(), angle=None, pins=(), w=1.0, h=1.0, timeout=90):
    """("ok", {...}) | ("err", msg) | ("CRASH", info) | ("HANG", "")."""
    payload = json.dumps({"nodes": nodes, "pairs": [list(p) for p in pairs],
                          "angle": angle, "pins": [list(p) for p in pins],
                          "w": w, "h": h})
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(q, payload))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate(); p.join(); return ("HANG", "")
    try:
        status, body = q.get(timeout=5)
    except _queue.Empty:
        return ("CRASH", f"exit {p.exitcode}")
    return (status, json.loads(body)) if status == "ok" else (status, body)


STAR4_SYM_NODES, STAR4_SYM_PAIRS = cases.symmetric_pairs_star(4)
STAR4_NODES, _ = cases.star(4)


def test_non_45_axis_with_pairs_is_refused():
    status, body = run(STAR4_SYM_NODES, STAR4_SYM_PAIRS, angle=0.0)
    assert status == "err", f"expected a refusal, got {status}: {body}"
    assert REFUSAL_TOKEN in body, body
    assert "0" in body, "the message must name the angle it refused"


def test_non_45_axis_WITHOUT_pairs_is_NOT_refused():
    """The guard is gated on emitted mirror rows, not on HasSymmetry().

    set_symmetry_angle with zero pairs emits no mirror row, so the angle is
    genuinely harmless. Gating on HasSymmetry() would refuse this and break
    every unpaired tree that ever sets an axis.
    """
    status, body = run(STAR4_NODES, pairs=(), angle=0.0)
    assert status == "ok", f"guard fired with no pairs: {body}"


def test_45_degrees_with_pairs_still_builds():
    status, body = run(STAR4_SYM_NODES, STAR4_SYM_PAIRS, angle=45.0)
    assert status == "ok", f"the shipped axis must be unaffected: {body}"


def test_the_default_axis_is_unaffected_when_no_angle_is_set():
    """apply_symmetry's own default establishes 45; nothing else changes."""
    status, body = run(STAR4_SYM_NODES, STAR4_SYM_PAIRS, angle=None)
    assert status == "ok", body


def test_non_square_paper_with_pairs_is_refused():
    status, body = run(STAR4_SYM_NODES, STAR4_SYM_PAIRS, angle=None,
                       w=1.0, h=2.0)
    assert status == "err", f"expected a refusal, got {status}: {body}"
    assert REFUSAL_TOKEN in body, body


def test_non_square_paper_WITHOUT_pairs_is_NOT_refused():
    status, body = run(STAR4_NODES, pairs=(), w=1.0, h=2.0)
    assert status == "ok", f"guard fired with no pairs: {body}"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_projection_guards.py -v --timeout=420
```

Expected: the two refusal tests FAIL (`status == "ok"`, no refusal raised); the
four "not refused" tests may ERROR on `e.projection_report()` not existing —
that binding arrives in Task 2. **If they error rather than fail, that is
acceptable at this step**; they must all pass by the end of Task 2.

- [ ] **Step 3: Restructure `ProjectActivePaths` so the guards can see `syms`**

In `mcp_harness/TreemakerWrapper.cpp`, inside `ProjectActivePaths`: the mirror-row
block currently sits **after** `if (cons.empty()) return;`, so a tree with pairs
but no active axis-parallel paths would return before any guard could run. Move
the early return down.

**Delete** this line where it currently stands (immediately after the
active-path `cons` loop):

```cpp
    if (cons.empty()) return;
```

**And delete** these two lines from where they currently stand (just below
`const std::size_t n = 2 * L;`):

```cpp
    const double w = double(mTree->GetPaperWidth());
    const double h = double(mTree->GetPaperHeight());
```

- [ ] **Step 4: Insert the guards**

Immediately **after** the `syms` build loop and the
`if (outCons) *outCons = cons.size() + 2 * syms.size();` line, insert:

```cpp
    // ---- Refuse any constraint class these rows cannot represent ----------
    // The mirror rows above are hard-coded to (x,y)->(y,x): the reflection
    // about y=x. That is the paper's centre diagonal ONLY when w == h, and the
    // correct mirror ONLY at a 45-degree symmetry axis. The OPTIMIZER's own
    // condition (tmConditionNodesPaired -> PairFn1A/PairFn1B,
    // tmConstraintFns.cpp) is fully general in mSymLoc/mSymAngle, so at any
    // other axis or sheet shape the two steps enforce DIFFERENT mirrors and
    // fight.
    //
    // MEASURED 2026-08-04 (49-cell axis sweep, 7 subjects x 7 angles): 21 of 49
    // non-45 cells die INSIDE this routine, and of the 8 that build, the non-45
    // ones come back silently re-symmetrized about y=x and STILL RETURN PACK.
    // Refusing loudly converts that silent wrongness into a named error.
    //
    // Gated on `syms`, NOT on HasSymmetry(): set_symmetry_angle can set an
    // angle with zero pairs, in which case no mirror row is emitted here and
    // the angle is genuinely harmless. Gating on HasSymmetry() would be a false
    // positive on every unpaired tree that sets an axis.
    const double w = double(mTree->GetPaperWidth());
    const double h = double(mTree->GetPaperHeight());
    if (!syms.empty()) {
      const double ang = double(mTree->GetSymAngle());
      if (std::fabs(ang - 45.0) > 1e-9) {
        std::ostringstream ss;
        ss << "the active-path projection does not represent a symmetry axis of "
           << ang << " degrees (only 45 is implemented). The scale optimizer "
           << "mirrors about " << ang << " while this step re-mirrors about "
           << "y=x, so the base would come back symmetric about the WRONG axis "
           << "and still report success.";
        throw std::runtime_error(ss.str());
      }
      if (std::fabs(w - h) > 1e-12) {
        std::ostringstream ss;
        ss << "the active-path projection does not represent a non-square sheet "
           << "(" << w << " x " << h << ") carrying symmetry pairs: its mirror "
           << "rows are (x,y)->(y,x), the reflection about y=x, which equals "
           << "the paper's centre diagonal only when width == height. The "
           << "correct rows carry an offset of (w-h)/2 -- see the S4a' design "
           << "doc before lifting this.";
        throw std::runtime_error(ss.str());
      }
    }
    if (cons.empty()) return;
```

- [ ] **Step 5: Rebuild and run the tests**

```bash
cd mcp_harness && PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_projection_guards.py -v --timeout=420
```

Expected: `test_non_45_axis_with_pairs_is_refused` and
`test_non_square_paper_with_pairs_is_refused` PASS. The four others still error
on the missing `projection_report` binding (Task 2).

**⚠ If a 45° test now fails, STOP.** That is the ODR signal: `GetSymAngle()` is
reading the wrong member through the wrong `tmTree.h`. Report it; do not paper
over it by widening the tolerance.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/TreemakerWrapper.cpp mcp_harness/tests/test_projection_guards.py
git commit -m "$(cat <<'EOF'
feat(projection): refuse a symmetry axis or sheet shape the mirror rows cannot represent

ProjectActivePaths hard-codes its mirror to (x,y)->(y,x) and reads mSymAngle
nowhere, while tmConditionNodesPaired is fully general in mSymLoc/mSymAngle.
A 49-cell sweep measured 21 of 49 non-45 cells dying inside this routine and
the survivors returning PACK on bases silently re-symmetrized about y=x.
Non-square paper desynchronizes the same rows AT 45 too, since (x,y)->(y,x) is
the centre diagonal only when w == h.

Both refusals are gated on emitted mirror rows, not on HasSymmetry(), so
set_symmetry_angle with zero pairs stays legal.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: The pin ledger, pin verification, and the margin proxy

**Files:**
- Modify: `mcp_harness/TreemakerWrapper.cpp` — members, `build_tree_from_json`, the three `set_node_*` setters, `ProjectActivePaths`, `BuildAndExport`'s call site, the pybind `.def` block
- Test: `mcp_harness/tests/test_projection_guards.py`

**Interfaces:**
- Produces: `HeadlessTreemaker.projection_report() -> dict` with keys
  `iters` (int), `cons` (int), `n_pins` (int), `pin_max_displacement` (float).
  Values reflect the **most recent** `ProjectActivePaths` run; all zero before
  the first `build_and_export`.

> **Why verify and not refuse.** MEASURED 2026-08-04
> (`evidence/…/probe_4_pin_survival.py`): pins **survive** the projection —
> worst displacement 5.83e-07 over seven arms, five of them ≤ 4.4e-09. The old
> spec's R8 ("the projection moves the node off the boundary") was inferred from
> reading the routine and is false. Refusing here would reject configurations
> measured to work.
>
> **Record the reason narrowly.** Pins survive because the projection is a
> *damped* step from the ALM solution whose per-iteration clamp holds
> `x ∈ [0,w]`, `y ∈ [0,h]` — so a pin at exactly 0 or `w` sits **on the clamp**.
> This does **not** generalize to interior pins, and emphatically not to "the
> projection preserves constraints": the mirror rows preserve the *wrong* mirror
> perfectly.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_projection_guards.py`:

```python
# ---------------------------------------------------------------- pin ledger

def test_a_pinned_leaf_survives_the_projection():
    """R8 falsified. Pins are VERIFIED here, never refused.

    Measured 2026-08-04 (evidence 2026-08-04-axis-corner-capacity/probe_4):
    worst displacement 5.83e-07 over seven arms. 1e-6 is an order-of-magnitude
    envelope around that measurement, not an invented tolerance.
    """
    corners = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
    nodes, _ = cases.star(5)
    status, body = run(nodes, pins=[(i + 1, "at", corners[i]) for i in range(4)])
    assert status == "ok", body
    rep = body["report"]
    assert rep["n_pins"] == 4, rep
    assert rep["pin_max_displacement"] <= 1e-6, rep


def test_a_one_equality_edge_pin_is_counted_and_verified():
    nodes, _ = cases.star(6)
    status, body = run(nodes, pins=[(1, "x", 0.0), (2, "x", 1.0),
                                    (3, "y", 0.0), (4, "y", 1.0)])
    assert status == "ok", body
    rep = body["report"]
    assert rep["n_pins"] == 4, rep
    assert rep["pin_max_displacement"] <= 1e-6, rep


def test_the_margin_proxy_is_wired_at_the_production_call_site():
    """iters/cons are out-params ProjectActivePaths has always accepted and
    BuildAndExport has always discarded. Book symmetry raises scale on 4 of 5
    subjects, i.e. toward the tangency cliff, so a failure must be separable
    from 'the geometry is rejected'. cons must exceed zero on a tree that has
    active paths at all."""
    status, body = run(*cases.symmetric_pairs_star(4))
    assert status == "ok", body
    rep = body["report"]
    assert rep["cons"] > 0, rep
    assert rep["iters"] >= 0, rep


def test_no_pins_reports_zero_pins():
    status, body = run(*cases.symmetric_pairs_star(4))
    assert status == "ok", body
    assert body["report"]["n_pins"] == 0, body["report"]
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_projection_guards.py -v --timeout=420
```

Expected: every new test errors with `'headless_treemaker.HeadlessTreemaker' object has no attribute 'projection_report'`.

- [ ] **Step 3: Add the members**

In `mcp_harness/TreemakerWrapper.cpp`, in the member block at the end of the
class (immediately after the `mSymPairs` declaration), insert:

```cpp
  //: S4a'. Boundary/position pins, mirroring the mSymPairs ledger above.
  //: tmConditionNodeCombo is reachable only through GetOrMakeOnePartCondition,
  //: and the same node can receive an X pin and a Y pin in separate calls
  //: (both land on ONE Combo), so this is keyed by node and updated in place
  //: rather than appended.
  struct Pin { bool xFixed = false, yFixed = false; double x = 0.0, y = 0.0; };
  std::map<tmNode*, Pin> mPinned;

  //: S4a'. Last ProjectActivePaths run: its own convergence counters plus the
  //: worst |projected - requested| over pinned coordinates. iters/cons are
  //: out-params the routine has always accepted and BuildAndExport always
  //: discarded; they are the cheapest available margin-to-cliff proxy (star-7,
  //: the one tree that only builds when pinned, displaces 5.83e-07 against a
  //: <= 4.4e-09 baseline).
  std::size_t mProjIters = 0;
  std::size_t mProjCons = 0;
  std::size_t mProjPins = 0;
  double mProjPinMax = 0.0;
```

- [ ] **Step 4: Reset the ledger with the others**

In `build_tree_from_json`, beside the existing resets, add `mPinned.clear();`:

```cpp
    mNodeMap.clear();
    mEdgeMap.clear();
    mStubApplied = false;
    mSymPairs.clear();
    mPinned.clear();
```

- [ ] **Step 5: Record pins in the three setters**

Replace the bodies of the three setters so each also writes the ledger.
`set_node_at`:

```cpp
  void set_node_at(int node_id, double x, double y) {
    tmNode* n = PinTarget(node_id, "set_node_at");
    tmTreeCleaner tc(mTree);
    tmConditionNodeCombo* c =
        mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
    c->SetXFixed(true);  c->SetXFixValue(x);
    c->SetYFixed(true);  c->SetYFixValue(y);
    Pin& p = mPinned[n];
    p.xFixed = true;  p.x = x;
    p.yFixed = true;  p.y = y;
  }
```

`set_node_on_x`:

```cpp
  void set_node_on_x(int node_id, double x) {
    tmNode* n = PinTarget(node_id, "set_node_on_x");
    tmTreeCleaner tc(mTree);
    tmConditionNodeCombo* c =
        mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
    c->SetXFixed(true);  c->SetXFixValue(x);
    Pin& p = mPinned[n];
    p.xFixed = true;  p.x = x;
  }
```

`set_node_on_y`:

```cpp
  void set_node_on_y(int node_id, double y) {
    tmNode* n = PinTarget(node_id, "set_node_on_y");
    tmTreeCleaner tc(mTree);
    tmConditionNodeCombo* c =
        mTree->GetOrMakeOnePartCondition<tmConditionNodeCombo, tmNode>(n);
    c->SetYFixed(true);  c->SetYFixValue(y);
    Pin& p = mPinned[n];
    p.yFixed = true;  p.y = y;
  }
```

- [ ] **Step 6: Verify pins inside the projection**

In `ProjectActivePaths`, immediately **before** the write-back block
(`tmTreeCleaner tc(mTree); for (...) leaves[i]->SetLoc(...)`), insert:

```cpp
    // ---- Verify (never refuse) boundary/position pins --------------------
    // MEASURED 2026-08-04 (evidence 2026-08-04-axis-corner-capacity/probe_4):
    // pins SURVIVE this step -- worst displacement 5.83e-07 over seven arms,
    // five of them <= 4.4e-09. The old R8 inference that the projection walks a
    // pinned node off the boundary is FALSE.
    //
    // Record the reason NARROWLY: it holds because this is a DAMPED step from
    // the ALM solution whose per-iteration clamp above pins x into [0,w] and y
    // into [0,h], so a pin at exactly 0 or w sits ON the clamp -- which the
    // step cannot push outward and has no incentive to pull inward. It does NOT
    // generalize to interior pins, and emphatically not to "the projection
    // preserves constraints": the mirror rows above preserve the WRONG mirror
    // perfectly. Hence: report, do not assume.
    mProjPins = 0;
    mProjPinMax = 0.0;
    for (std::size_t i = 0; i < L; ++i) {
      auto pit = mPinned.find(leaves[i]);
      if (pit == mPinned.end()) continue;
      ++mProjPins;
      if (pit->second.xFixed)
        mProjPinMax = std::max(mProjPinMax, std::fabs(x[i] - pit->second.x));
      if (pit->second.yFixed)
        mProjPinMax = std::max(mProjPinMax, std::fabs(y[i] - pit->second.y));
    }
```

- [ ] **Step 7: Stop discarding the out-params at the production call site**

In `BuildAndExport`, the projection is called with no arguments. Replace:

```cpp
    ProjectActivePaths();
```

with:

```cpp
    ProjectActivePaths(&mProjIters, &mProjCons);
```

> `debug_active_path_report` already passes its own local `iters`/`cons`; leave
> it alone. This is the **production** site, and it is the one that has always
> discarded them.

- [ ] **Step 8: Add the binding**

Add the accessor as a public method on the class (next to
`debug_active_path_report`):

```cpp
  py::dict projection_report() {
    py::dict d;
    d["iters"] = mProjIters;
    d["cons"] = mProjCons;
    d["n_pins"] = mProjPins;
    d["pin_max_displacement"] = mProjPinMax;
    return d;
  }
```

And register it in the `.def` chain, immediately after the
`debug_active_path_report` entry:

```cpp
      .def("projection_report", &HeadlessTreemaker::projection_report,
           "Last ProjectActivePaths run: {iters, cons, n_pins, "
           "pin_max_displacement}. All zero before the first build_and_export.")
```

- [ ] **Step 9: Rebuild and run the file**

```bash
cd mcp_harness && PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_projection_guards.py -v --timeout=420
```

Expected: **all ten tests PASS.**

Record the observed `pin_max_displacement` for the star-5 four-corner arm and
paste it into this plan here → `____________`. It should reproduce probe_4's
`0.00e+00`; if it does not, say so rather than widening the assertion.

> **Observed 2026-08-04** (this session, `mcp_harness/tests/test_projection_guards.py`
> run against the built `.so`): star-5 four-corner `pin_max_displacement = 0.0`
> — reproduces probe_4's `0.00e+00` exactly. Star-6 four-edge (1-eq) arm
> (`test_a_one_equality_edge_pin_is_counted_and_verified`) read
> `6.629976567751328e-10`, matching probe_4's `6.63e-10` to displayed precision.

- [ ] **Step 10: Commit**

```bash
git add mcp_harness/TreemakerWrapper.cpp mcp_harness/tests/test_projection_guards.py
git commit -m "$(cat <<'EOF'
feat(projection): verify boundary pins and expose the convergence counters

Pins are VERIFIED, not refused: measured 2026-08-04, they survive the
projection at worst 5.83e-07 over seven arms, which falsifies the old R8
inference. The reason is clamp-specific -- a pin at 0 or w sits on the
per-iteration on-paper clamp -- so it does not generalize to interior pins and
the ledger reports rather than assumes.

iters/cons have been out-params of ProjectActivePaths all along and
BuildAndExport discarded both; only debug_active_path_report ever passed them.
They are the cheapest margin-to-cliff proxy available, and S4b0 needs one
because book symmetry raises scale toward the tangency cliff.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Name the projection failure in the error vocabulary

**Files:**
- Modify: `mcp_harness/error_recipes.py`
- Test: `mcp_harness/tests/test_projection_guards.py`

**Interfaces:**
- Consumes: Task 1's refusal substring `the active-path projection does not represent`.
- Produces: two codes appended to `ERROR_CODES` — `PROJECTION_UNSUPPORTED`, `PROJECTION_INVALID`.

> `_MATCHERS` is order-sensitive (`classify()` returns the **first** match) and
> its own comment says *"append new codes, never reorder or re-mean the prefix
> (baseline rows pin it)."* **Append.** Note the two strings do not shadow each
> other or the existing `"polygon network is not valid"` entry: the projection
> failure reads `"became invalid after active-path projection"`, which shares no
> substring with `"is not valid"`. That is why `classify()` returns `None` for it
> today, and why every projection failure on record has landed unclassified.
>
> **No `_RECIPES` entries.** That table's own rule is *"Codes with no measured
> lever have NO entry: the honest answer is silence, not invented advice."*
> `PROJECTION_UNSUPPORTED` carries its remedy in the message; `PROJECTION_INVALID`
> has no measured remedy yet.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_projection_guards.py`:

```python
# ------------------------------------------------------------- vocabulary

import error_recipes  # noqa: E402


def test_the_refusal_string_classifies():
    msg = ("the active-path projection does not represent a symmetry axis of "
           "0 degrees (only 45 is implemented).")
    assert error_recipes.classify(msg) == "PROJECTION_UNSUPPORTED"


def test_the_pre_existing_projection_failure_classifies():
    """This string has been emitted since the projection landed and classify()
    has returned None for it the whole time -- it shares no substring with the
    'polygon network is not valid' entry, which reads 'is not valid' where this
    reads 'became invalid'."""
    msg = ("polygon network became invalid after active-path projection "
           "(scale=0.5); this should not happen for a converged base")
    assert error_recipes.classify(msg) == "PROJECTION_INVALID"


def test_the_existing_vocabulary_prefix_is_unmoved():
    """_MATCHERS is order-sensitive and the committed scorecard rows pin its
    prefix. New codes append; they never reorder."""
    assert error_recipes.ERROR_CODES[:5] == [
        "POLYS_MULTIPLE_IBPS",
        "NOT_LOCAL_ROOT_CONNECTABLE",
        "FACETS_NOT_VALID",
        "EDGES_TOO_SHORT",
        "polygon network is not valid",
    ]


def test_a_polygon_invalid_error_still_classifies_as_before():
    """The new entries must not shadow the pre-existing class."""
    msg = ("polygon network is not valid after optimization (scale=0.84): the "
           "active-path network does not form a valid polygon partition")
    assert error_recipes.classify(msg) == "polygon network is not valid"


def test_no_recipe_is_invented_for_the_new_codes():
    assert error_recipes.recipe("PROJECTION_UNSUPPORTED") is None
    assert error_recipes.recipe("PROJECTION_INVALID") is None
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_projection_guards.py -k vocabulary -v --timeout=420
```

Expected: `test_the_refusal_string_classifies` and
`test_the_pre_existing_projection_failure_classifies` FAIL with
`assert None == 'PROJECTION_UNSUPPORTED'` / `'PROJECTION_INVALID'`. The other
three PASS already.

- [ ] **Step 3: Append the two codes**

In `mcp_harness/error_recipes.py`, append to `_MATCHERS` (after
`("COMPILE_TIMEOUT", ("compilation timed out",))`):

```python
    # S4a'. The post-optimization active-path projection. BOTH of these
    # returned None from classify() before this slice, so every projection
    # failure the repo has ever recorded landed unclassified -- neither string
    # shares a substring with the "polygon network is not valid" entry above
    # ("is not valid" vs "became invalid" / "does not represent").
    ("PROJECTION_UNSUPPORTED",
     ("the active-path projection does not represent",)),
    ("PROJECTION_INVALID",
     ("became invalid after active-path projection",)),
```

- [ ] **Step 4: Run to verify they pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/test_projection_guards.py -v --timeout=420
```

Expected: all fifteen tests PASS.

- [ ] **Step 5: Prove the vocabulary entry is load-bearing by DELETING it**

A count-based test is not a pin of the wiring. Temporarily delete the
`PROJECTION_UNSUPPORTED` tuple from `_MATCHERS`, re-run, and confirm
`test_the_refusal_string_classifies` goes **RED**. Restore it and confirm green.
Do the same for `PROJECTION_INVALID`.

Record here that you did it and what went red → `____________`

> **Observed 2026-08-04.** Deleting the `PROJECTION_UNSUPPORTED` tuple:
> `test_the_refusal_string_classifies` went RED (`assert None ==
> 'PROJECTION_UNSUPPORTED'`), 14 others stayed green. Restored, re-ran: 15/15
> green. Deleting the `PROJECTION_INVALID` tuple: only
> `test_the_pre_existing_projection_failure_classifies` went RED (`assert None
> == 'PROJECTION_INVALID'`), 14 others stayed green. Restored, re-ran: 15/15
> green. Both deletions were clean and isolated -- no collateral failures.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/error_recipes.py mcp_harness/tests/test_projection_guards.py
git commit -m "$(cat <<'EOF'
feat(error-recipes): name the two active-path projection failures

classify() returned None for both -- the pre-existing "became invalid after
active-path projection" shares no substring with the "polygon network is not
valid" entry, so every projection failure on record landed unclassified.
Appended, never reordered: _MATCHERS is order-sensitive and the committed
scorecard rows pin its prefix. No _RECIPES entries -- that table's rule is
silence where no lever is measured.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Regression, goldens, Linux, and the baseline delta

**Files:**
- Modify: `docs/superpowers/goals/COORDINATION.md`, `docs/superpowers/goals/goal-1-whole-square/PROGRESS.md`

- [ ] **Step 1: Prove the out-param pass-through is load-bearing by DELETING it**

Temporarily revert Task 2 Step 7 (`ProjectActivePaths(&mProjIters, &mProjCons);`
→ `ProjectActivePaths();`), rebuild, and confirm
`test_the_margin_proxy_is_wired_at_the_production_call_site` goes **RED**
(`cons` reads 0). Restore, rebuild, confirm green.

Record what went red → `____________`

> **Observed 2026-08-04.** Reverting `ProjectActivePaths(&mProjIters,
> &mProjCons);` -> `ProjectActivePaths();` in `BuildAndExport` and rebuilding:
> `test_the_margin_proxy_is_wired_at_the_production_call_site` went RED
> (`{'cons': 0, 'iters': 0, ...}`, `assert 0 > 0` failed); all 14 others stayed
> green. Restored, rebuilt, re-ran: 15/15 green.

- [ ] **Step 2: Full suite**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420
```

Expected: **2241 passed + 15 new = 2256 passed, 11 skipped, 0 failed.**
Takes ~14 min and looks stalled early at near-zero CPU — **do not kill it.**

If the geometry goldens moved, **STOP.** This slice adds refusals on paths
nothing in production takes; goldens moving means a guard is firing on the
shipped 45°/square configuration, which is the ODR signal from Task 1 Step 5.

Record the observed line → `____________`

> **Observed 2026-08-04:** `================= 2256 passed, 11 skipped in
> 944.01s (0:15:44) =================`. Zero failures, zero errors (grep
> confirmed). No golden moved.

- [ ] **Step 3: The frozen-baseline delta**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl
```

**Do NOT regenerate the baseline.** Paste the delta table into the PR body.

Expected: `no axis moved` on all five subjects. **The one axis that plausibly
moves is `error_codes`**, because Task 3 gives previously-unclassified strings a
name. If a row moves, **attribute it explicitly** — a row you cannot attribute
is a FINDING, and the PR must say so.

Record the delta → `____________`

> **Observed 2026-08-04:** `no axis moved: quadruped, bird, humanoid, fish,
> insect`. Not even `error_codes` moved -- none of the five subjects' current
> failures happen to be one of the two new projection classes (quadruped:
> `polygon network is not valid`, fish: `NOT_LOCAL_ROOT_CONNECTABLE`, insect:
> `POLYS_MULTIPLE_IBPS`, bird/humanoid: pack clean, `-`). The `error_codes`
> column move the spec flags as plausible did not occur on this corpus.

- [ ] **Step 4: Linux, in the container, BEFORE merge**

Check host CPU for orphans first — a stray background process once made a gate
run 6× slow and would have manufactured timeout failures.

```bash
uptime && ps aux | sort -rn -k3 | head -5
```

Then run the suite in the `ci-amd64-run` container. This is a C++ change on the
serve path; memory `rigid-frozen-hash-platform-divergence` and
`linux-ci-3-failures-diagnosis-outcome` both record Linux-only failures that
push-and-wait would have found late.

Record the container result → `____________`

> **Observed 2026-08-04.** Host CPU checked first (`uptime`: load 3.15/3.23/3.47
> on this machine, no orphan). Docker Desktop was not running; started it, ran
> `docker run --rm -v "<worktree>:/repo-src:ro" ci-amd64-run:latest bash -c
> "cp -r /repo-src/. /repo && cd /repo && make PYTHON=python test"` (copied
> rather than bind-mounted, so the container's root-owned build artifacts never
> touch the host worktree). Result:
> `================ 2257 passed, 10 skipped in 1354.22s (0:22:34) ================`.
> Zero failures (grep-confirmed; the one `FAILED`/`ERROR` regex hit was the test
> named `test_only_FAILED_compiles_count`, not an actual failure).
>
> **The 2257/10 vs macOS's 2256/11 is a skip-count difference, not a
> failure, not attributable to this slice.** Diagnosed to
> `test_rigid_collision_evidence.py::test_collision_verifier_rejects_symlinks_at_every_bundle_boundary[member_socket]`
> (line ~503): it binds an AF_UNIX socket to `Path.cwd() /
> ".p4-<pid>-<id>.sock"`. Under this session's deeply nested worktree cwd
> (`.../worktrees/goal-1-s4a-projection-guards/mcp_harness`) the path exceeds
> macOS's `sun_path` limit and the test's own `except OSError` ->
> `pytest.skip(...)` fires; under the container's short `/repo/mcp_harness` cwd
> it fits and the test runs and passes. This is the exact mechanism memory
> `worktree-borrowed-so-inflates-failures` already recorded ("skip count:
> worktree 11 vs main-checkout 10 is AF_UNIX path length ... not a
> regression"). Confirmed pre-existing and environmental, not introduced by
> this slice.

- [ ] **Step 5: Update the tracking docs and commit**

In `docs/superpowers/goals/COORDINATION.md`: release the
`TreemakerWrapper.cpp` claim in §2, and add a §5 signal —
**"S4a′ merged; Goal 2's S3 is unblocked."** Add the `error_recipes` row to §4
with its merge commit.

In `docs/superpowers/goals/goal-1-whole-square/PROGRESS.md`: S4a′ → ✅ done,
with the measured pin displacement and the baseline delta.

```bash
git add docs/superpowers/goals/
git commit -m "$(cat <<'EOF'
docs(goal-1): S4a' merged -- release the C++ claim, unblock Goal 2's S3

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Self-review against the spec

| spec requirement | task |
|---|---|
| §4.1(1) refuse non-45°, gated on `syms` | Task 1 (both directions tested) |
| §4.1(2) refuse non-square; fix the stale comment | Task 1 |
| §4.1(3) verify, not refuse, boundary pins | Task 2 |
| §4.1 expose `outIters`/`outCons` at the production site | Task 2 Step 7, pinned by deletion in Task 4 Step 1 |
| §4.1 add the projection string to `error_recipes` | Task 3, pinned by deletion in Task 3 Step 5 |
| §6 criterion 1 (both directions) | Task 1 tests 1–2 |
| §6 criterion 2 (non-square) | Task 1 test 5 |
| §6 criterion 3 (displacement reproduces §3.5) | Task 2 tests 1–2 |
| §6 criterion 4 (classify, verified by deletion) | Task 3 Step 5 |
| §6 criterion 5 (goldens byte-identical) | Task 4 Step 2 |
| §6 criterion 6 (out-params, verified by deletion) | Task 4 Step 1 |
| §6 criterion 7 (full suite) | Task 4 Step 2 |
| §6 criterion 8 (Linux container before merge) | Task 4 Step 4 |
| §5.2 (`error_codes` may move; attribute it) | Task 4 Step 3 |

**Not in this plan, by design:** S4b₀'s book/90° rows (own plan, after this
merges and after Goal 2's S3 takes its turn in the serial file), 0α, the
`design_scale` and true-polygon-coverage instruments, and the CLAUDE.md edit.

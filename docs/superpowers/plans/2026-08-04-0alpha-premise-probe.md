# 0α — The premise probe and its fixture — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn five ad-hoc evidence probes into **one reproducible instrument
under `mcp_harness/` writing a committed fixture**, and close the three
measurement gaps the planning session left open — the edge-pin arms, a
**non-vacuous** order-restart control, and a margin-to-cliff reading.

**Architecture:** One new `mcp_harness/probe_axis_corner_capacity.py`, forked
from the working `probe_symmetry_axis.py` (which already imports
`paper_coverage`, already runs each arm in an isolated child, and already writes
a `fixtures/` JSON). It emits `fixtures/axis_corner_capacity.json`. **It adds no
scorecard column and moves no scorecard row** — it is an instrument, not a
change to the product.

**Tech Stack:** Python 3.14, the `headless_treemaker` pybind11 extension, pytest.

**Spec:** [docs/superpowers/specs/2026-08-04-whole-square-axis-projection-design.md](../specs/2026-08-04-whole-square-axis-projection-design.md) §3, §4.3
**Evidence being hardened:** [docs/superpowers/evidence/2026-08-04-axis-corner-capacity/](../evidence/2026-08-04-axis-corner-capacity/)

---

## Global Constraints

- **Branch from `5f6ab2a`** (main, S4a′ merged). Branch `claude/goal-1-0alpha-premise-probe`, its own worktree.
- **Build the `.so` IN PLACE, and NOT with bare `./build.sh`** — it defaults to `PYTHON=python3`, a Homebrew interpreter without `pybind11`, and **exits producing no `.so` and no obvious failure.** The worktree has no `.venv` of its own:
  ```bash
  cd mcp_harness && PYTHON=<repo>/mcp_harness/.venv/bin/python ./build.sh
  ```
  Also needs `oriedita/` and `OrieditaValidator.class` for the full suite.
- **Tests:** `cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420`. Bare `make test` never terminates. Full suite ~15 min, **looks stalled early at near-zero CPU — do not kill it.** Expect **2256 / 11 / 0** (deep path) or **2257 / 10 / 0** (short path).
- **`mcp_harness/fixtures/scorecard_baseline.jsonl` is FROZEN at `1c9abe0`.** This slice must not touch it; report the `--baseline` delta and expect `no axis moved`.
- **The bare `HeadlessTreemaker` compile is the CORRECT instrument here.** This is a variant × angle grid wanting attribution, not a serve. Every arm runs in a spawned child because the engine can SIGSEGV.
- **Never pin a number you did not observe.** Every `____________` blank in this plan is a value you paste after running.
- **Do not "fix" a surprising number.** If an arm disagrees with the committed evidence, report the disagreement — that is a finding, not a bug to smooth away.
- Commit messages end with: `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`

> **⚠ Report, do not chase, rescue-shaped results.** `star-7` does not build
> unpinned and does build corner-pinned. A constraint that makes an unpackable
> tree pack is a **rescue rung**, and this project has already built two specs as
> rescue rungs when the ask was alignment tools for models that pack fine
> (memory `rescue-ladder-vs-alignment-tool`). Record it in the fixture. Do not
> extend the probe to hunt for more of it.

---

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/probe_axis_corner_capacity.py` | **Create.** The one instrument: arms, isolated-child runner, fixture writer. |
| `mcp_harness/fixtures/axis_corner_capacity.json` | **Create.** Its output, committed. |
| `mcp_harness/tests/test_axis_corner_capacity_fixture.py` | **Create.** Pins the fixture's shape and its load-bearing rows. |
| `docs/superpowers/goals/goal-1-whole-square/PROGRESS.md` | **Modify** on merge. |

---

## Task 1: The instrument

**Files:**
- Create: `mcp_harness/probe_axis_corner_capacity.py`

**Interfaces:**
- Produces: `run_arm(nodes, pairs, pins, angle, export) -> dict` with keys
  `status` (`"PACK"` | `"OPT"` | `"FAIL"` | `"TIMEO"` | `"CRASH"`), `scale`,
  `coverage`, `bbox`, `leaf_hull`, `corners`, `on_boundary`, `proj_iters`,
  `proj_cons`, `pin_max_displacement`, `err`.
- `export=False` stops after `run_scale_optimization()` — **required for
  non-45° arms**, because `ProjectActivePaths` now *refuses* them (S4a′) and
  before S4a′ it silently re-symmetrized. Optimizer-only readings are the only
  honest non-45° measurement available until S4b₀.

- [ ] **Step 1: Read the working instrument you are forking**

Read `mcp_harness/probe_symmetry_axis.py` in full. Reuse its `_CHILD` /
`run_arm` shape — isolated child, `@@`-prefixed JSON line, `subprocess.run` with
a timeout. Do **not** invent a new harness pattern.

Also read all five probes in
`docs/superpowers/evidence/2026-08-04-axis-corner-capacity/`. Your arms must
reproduce their committed numbers; the outputs are in `out_*.txt` beside them.

- [ ] **Step 2: Write the probe**

Create `mcp_harness/probe_axis_corner_capacity.py`. Requirements, each of which
is checked in Task 2:

1. **Arms, at minimum:**
   - *corner capacity by axis* — the five paired subjects (`star-4-sym`,
     `TEMPLATE_QUADRUPED`, `TEMPLATE_BIRD`, `TEMPLATE_HUMANOID`,
     `TEMPLATE_INSECT`) × {diag45, book0} × {free, 1 pair→2 corners,
     2 pairs→4 corners}, `export=False`.
   - *unpaired k-sweep* — `star(k)` for k = 5..8 × {free, 1, 2, 4 corners},
     `export=True`.
   - *one-equality edge pins* — the same five paired subjects and the k-sweep
     stars, using `set_node_on_x` / `set_node_on_y`, `export=True`. **This is
     where the boundary policy lives now** — as measurement, not as a slice.
   - *pin survival* — the arms from `probe_4`, reporting
     `pin_max_displacement` from `projection_report()` (new in S4a′) rather
     than by diffing coordinates by hand.
2. **`paired` and `n_pinned_corners` recorded on every row.** The paired /
   unpaired split is the reported discriminator, so it must be a field, not
   something a reader infers from the label.
3. **`proj_iters` / `proj_cons` from `projection_report()` on every exporting
   arm** — the margin-to-cliff reading.
4. Writes `fixtures/axis_corner_capacity.json` with a `_meta` block: what, when,
   how to re-run, the engine commit, and **the platform**, because
   `QUAD`'s two packing basins make some readings platform-dependent
   (macOS/Accelerate 0.717008 vs Linux/OpenBLAS 0.714406).
5. Under `if __name__ == "__main__":`.

- [ ] **Step 3: Run it and record**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python probe_axis_corner_capacity.py
```

Paste the corner-capacity table here → `____________`

**Cross-check against the committed evidence.** These must reproduce:

| arm | expected |
|---|---|
| `star-4-sym` diag45 free | scale 0.353553, leaf hull 0.500000, **0** corners |
| `star-4-sym` book0, 2 pairs → 4 corners | scale 0.500000, leaf hull **1.000000**, 4 corners |
| all five subjects, diag45, 2 pairs → 4 corners | **FAIL**, `scale optimization did not converge (reason code 1)` |
| all five subjects, book0, 2 pairs → 4 corners | **OPT**, leaf hull **1.000000**, 4 corners |
| `star-5` free vs 4 corners (export) | 0.323556 / 0.703897 → 0.353553 / **1.000000** |
| `star-6` four-edge 1-equality pins | `pin_max_displacement` ≈ 6.63e-10 |

**Any disagreement is a finding.** Report it; do not adjust the arm to match.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/probe_axis_corner_capacity.py mcp_harness/fixtures/axis_corner_capacity.json
git commit -m "$(cat <<'EOF'
feat(probe): one reproducible instrument for axis corner capacity

Forks probe_symmetry_axis.py, which already isolates each arm in a child and
already writes a fixtures/ JSON. Replaces five ad-hoc evidence scripts with one
committed instrument, because the two prior measurements that decided this goal
survive only as prose in specs and were unreproducible from the repo alone.

Non-45 arms are optimizer-only by construction: ProjectActivePaths now REFUSES
them (S4a'), and before S4a' it silently re-symmetrized about y=x and returned
PACK anyway. Optimizer-only is the honest reading until S4b0.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: The non-vacuous order-restart control

**Files:**
- Modify: `mcp_harness/probe_axis_corner_capacity.py`

> **This task exists because the planning session got it wrong, and the error is
> instructive.** It tested "is the corner win just a basin re-roll the ladder
> already reaches?" by permuting the leaves of `star(5)`. All twelve
> permutations returned scale 0.323556 identically — **because `star(5)`'s five
> leaves are all length 1.0, so permuting them is a relabeling.** The control was
> run in the regime where it *cannot succeed*. Committed as
> `probe_3_edge_pins_and_order.py` with a warning in the evidence README.

**The question is real and still open:** node-order restarts are a shipped
rescue lever (`rescue_ladder.order_variants`; memory: order alone rescued 45.8%
of cohort attempt-0 pack failures). If a plain order permutation reaches the
corner-pinned basin on a tree where permutation actually *does* something, then
corner pinning buys nothing new and 0α should say so.

- [ ] **Step 1: Add the control on UNEQUAL-length trees**

Add an arm set that, for at least **three** trees whose leaves have distinct
lengths — `cases.TEMPLATE_HUMANOID`, `cases.TEMPLATE_BIRD`, and
`cases.uneven_star` if it exists (otherwise a hand-built star with lengths
`0.2, 0.3, 0.4, 0.5, 0.6`) — compiles **≥ 12 distinct node orderings** with no
pins, records `(status, scale, coverage)` for each, and reports:

- the **best** scale over the order restarts,
- the scale of the **corner-pinned** arm on the same tree,
- and explicitly whether order restarts **reach, exceed, or fall short of** it.

Record the outcome in the fixture under a `order_restart_control` key with a
`verdict` string, so a reader cannot mistake it for a raw table.

- [ ] **Step 2: Run and record**

Paste the control's result → `____________`

**Report whichever way it falls.** If order restarts reach the corner basin,
that materially weakens the corner lever and **must** be said plainly in the PR
body and in `PROGRESS.md` — it is more valuable than a confirmation.

- [ ] **Step 3: Commit**

```bash
git add mcp_harness/probe_axis_corner_capacity.py mcp_harness/fixtures/axis_corner_capacity.json
git commit -m "$(cat <<'EOF'
test(probe): a NON-VACUOUS order-restart control, on unequal-length trees

The planning session's own control permuted the leaves of star(5) -- five
identical 1.0 leaves, so permutation is a relabeling and 12/12 identical results
were near-guaranteed. That is the "measured in the regime where it cannot fail"
error, committed with a warning rather than quietly dropped.

Re-run on trees whose leaves actually differ, which is where rescue_ladder's
order lever does its work.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Margin-to-cliff, calibrated against QUAD's two basins

**Files:**
- Modify: `mcp_harness/probe_axis_corner_capacity.py`

> **Why this matters and why it is not simply "record iters".** Book symmetry
> raises scale on 4 of 5 subjects, i.e. **toward** the tangency cliff, and
> memory `packer-two-basins-scale-lever` records that max-scale packs sit near
> tangency where 1-ULP platform differences flip outcomes. S4b₀ will need to tell
> "hit the cliff" from "book geometry rejected."
>
> **⚠ `proj_iters` alone will not serve.** S4a′'s review measured it saturating
> at `maxIters = 50` on `star-4-sym` and `star-5`, with the residual barely
> moving (2.031e-09 → 1.717e-09). A censored counter cannot be a margin. The
> residual itself is the quantity, and exposing it is **S4b₀'s Task 1**, not
> this slice's. **Record what is available now and say plainly what it cannot
> measure** — do not present `iters` as a working margin proxy.

- [ ] **Step 1: Record the reference point**

`QUAD` is the calibration: its two packing basins differ by 2.6e-3 in objective
(macOS 0.717008 / Linux 0.714406) and **flip the CP symmetry verdict**, not
merely coordinates. Compile `cases.QUAD` and record `scale`, `proj_iters`,
`proj_cons`, and the platform, into the fixture's `_meta` under
`margin_reference`.

- [ ] **Step 2: Record the per-arm reading and its limits**

For every exporting arm record `proj_iters` / `proj_cons`, and add a fixture
field `margin_proxy_censored: true` on any arm where `proj_iters == 50`, with a
`_meta` note naming the cap and pointing at S4b₀ Task 1 for the fix.

- [ ] **Step 3: Run, record, commit**

Paste the margin table → `____________`

```bash
git add mcp_harness/probe_axis_corner_capacity.py mcp_harness/fixtures/axis_corner_capacity.json
git commit -m "$(cat <<'EOF'
feat(probe): margin-to-cliff reading, with its censoring marked

Records proj_iters/proj_cons per arm and QUAD's two-basin split as the
calibration reference. Marks margin_proxy_censored where iters hits the
maxIters=50 cap -- which is star-4-sym and star-5, i.e. exactly the trees S4b0
cares about. The residual is the real quantity and exposing it is S4b0's Task 1;
this slice records what exists and names what it cannot measure.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Pin the fixture, and prove the pin

**Files:**
- Create: `mcp_harness/tests/test_axis_corner_capacity_fixture.py`

- [ ] **Step 1: Write the tests**

```python
"""The premise fixture is READ by something, and its load-bearing rows are pinned.

The two prior measurements that decided this goal survived only as prose in
specs -- unreproducible from the repo alone. A committed fixture nothing reads
is the same failure with extra steps.
"""
from __future__ import annotations
import json
import os

import pytest

FIXTURE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "fixtures", "axis_corner_capacity.json")


@pytest.fixture(scope="module")
def data():
    with open(FIXTURE) as fh:
        return json.load(fh)


def test_the_fixture_is_read_by_something(data):
    assert "_meta" in data
    assert data["_meta"].get("platform"), "platform must be recorded -- QUAD's " \
        "two packing basins make some readings platform-dependent"


def test_the_diagonal_cannot_seat_four_paired_corners(data):
    """The finding the whole goal is built on. A paired leaf can only take a
    corner whose mirror image is also a corner: the diagonal supplies TWO."""
    rows = [r for r in data["rows"]
            if r.get("axis") == 45.0 and r.get("n_pinned_corners") == 4
            and r.get("paired")]
    assert rows, "no diag45 four-corner arms in the fixture"
    assert all(r["status"] == "FAIL" for r in rows), \
        [(r["subject"], r["status"]) for r in rows]


def test_book_seats_four_paired_corners_on_every_subject(data):
    rows = [r for r in data["rows"]
            if r.get("axis") == 0.0 and r.get("n_pinned_corners") == 4
            and r.get("paired")]
    assert len(rows) >= 5, len(rows)
    for r in rows:
        assert r["status"] == "OPT", (r["subject"], r["status"])
        assert r["leaf_hull"] == pytest.approx(1.0, abs=1e-6), r
        assert r["corners"] == 4, r


def test_the_order_restart_control_is_not_vacuous(data):
    """It must run on trees whose leaves actually differ -- permuting identical
    leaves is a relabeling, which is how the planning session's own control
    came to prove nothing."""
    ctrl = data["order_restart_control"]
    assert ctrl["verdict"], "the control must state a verdict, not just a table"
    for t in ctrl["trees"]:
        assert len(set(t["leaf_lengths"])) > 1, \
            f"{t['subject']}: equal-length leaves make this control vacuous"
        assert t["n_orders"] >= 12, t
```

- [ ] **Step 2: Run, then prove the pin by BREAKING the fixture**

A count-based test is not a pin. Temporarily flip one `diag45` four-corner row's
`status` from `"FAIL"` to `"OPT"` in the fixture, re-run, and confirm
`test_the_diagonal_cannot_seat_four_paired_corners` goes **RED**. Restore.

Record what went red → `____________`

- [ ] **Step 3: Full suite, baseline delta, commit**

```bash
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python -m pytest tests/ --timeout=420
cd mcp_harness && PYTHONPATH=.:tests <repo>/mcp_harness/.venv/bin/python benchmark_subjects.py --baseline fixtures/scorecard_baseline.jsonl
```

Expected: suite green plus the new tests; **`no axis moved`** — this slice adds
an instrument and changes no product behaviour. If a row moves, that is a
FINDING and the PR must say so.

Record both → `____________`

---

## Self-review against the spec

| spec §4.3 requirement | task |
|---|---|
| One reproducible probe under `mcp_harness/` writing a `fixtures/` JSON | Task 1 |
| Fork `probe_symmetry_axis.py` rather than write a new harness | Task 1 Step 1 |
| Paired/unpaired split as the reported discriminator | Task 1 req. 2; Task 4 |
| One-equality edge-pin arms | Task 1 req. 1 |
| Non-vacuous order-restart control on an unequal tree | Task 2 |
| Margin-to-cliff calibrated against QUAD's basins | Task 3 |
| Adds no scorecard column, moves no row | Task 4 Step 3 |

**Not in this plan:** the CLAUDE.md §1.1(2)+(4) edit — the planning session
drafts that itself, behind this fixture, because it reverses two numbered claims
in the document governing every future session's premises and turns on history
that does not transfer through a spec.

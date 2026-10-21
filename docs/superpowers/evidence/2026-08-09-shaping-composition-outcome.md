# Shaping composition fix — Task 6 outcome

Plan: `docs/superpowers/plans/2026-08-09-shaping-composition-*` (6 tasks).
Spec: `docs/superpowers/specs/2026-08-09-shaping-composition-design.md`.

## 1. The pre-fix defect (measured in Task 4, on unmodified code)

Task 4 Step 2's headline test, run against `shaping.py` before any production
change in this arc, found:

- `op1` set partial angles on edges 11 and 12 (both `90.0` degrees).
- `op2` reset 2 of 2 of them to `180.0` degrees.
- Total drift: `180.0` degrees, both moves toward **more** fold (never less).

Verbatim failure message:

```
op2 reset edge 11: op1 set 90.0, after op2 it reads 180.0
```

This is the concrete instance of the design's claim (§1): every op rebuilt
`edges_foldAngle` from `edges_assignment` plus its own overrides, discarding
whatever partial angle an earlier op had already set.

## 2. The byte-identity gate (Task 6, this task)

`mcp_harness/tests/test_shaping_composition_gate.py` runs
`shaping.apply_display_ops(square_complete.complete_square(raw, 1.0, 1.0),
[op])` for every one of the 24 keys in
`mcp_harness/fixtures/shaping_single_op_baseline.json` (frozen by Task 1,
**before** any of Tasks 2-5's production changes) and asserts
`json.dumps(out, sort_keys=True)` is byte-identical to the frozen baseline.

Result: **24 of 24 keys byte-identical.** No STOP condition fired. The
`test_composition_is_not_a_flatten_of_everything_prior` headline test and the
fixture-presence check also pass. Full run:

```
26 passed in 0.05s
```

(`tests/test_shaping_composition_gate.py -v --timeout=420`; independently
re-run, `26 passed in 0.04s`, same result)

The baseline fixture covers **6 of the 8 goldens** the probe names:
`dog-repaired`, `dog`, `hf-crane-ladder-blb`, `hshape`, `quad`, `star-4`
(24 keys, 4 per golden: `outside`/`reverse` × 2 probe points each).
`hf-dog-nudged` and `hf-dog-ladder-best` contributed **0** entries — their
candidate ops were refused by shaping's own crease guards, not by anything
this task changed. The gate therefore exercises 6 goldens, not 8, and that
limit is recorded here rather than papered over.

## 3. Full-suite counts

**Before** (from the plan's stated expectation, `docs/superpowers/plans/
2026-08-09-shaping-composition-*`): `2422 passed, 11 skipped`. This is
**taken from the plan document, not a measurement on this branch** — no
pre-fix full-suite run was captured in this task.

**After** (measured on this branch,
`cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest --timeout=420`):

```
13 failed, 2499 passed, 11 skipped in 1497.89s (0:24:57)
```

The higher passed-count relative to the plan's `2422` figure reflects two
things, not one: the `origin/main` merge (`c5da4c1`) that landed between the
plan being written and this task running, and this arc's own new tests
(Task 1's baseline-freeze work plus this task's 26-test gate).

**The 13 failures are pre-existing and unrelated to this arc.** All 13 are in
`tests/test_book_axis_projection.py` (11) and `tests/test_projection_guards.py`
(2). The engine's own error is:

```
RuntimeError: the active-path projection does not represent a symmetry axis
of 0 degrees (only 45 is implemented)
```

Book-axis support shipped as C++ constraint rows in S4b0 (PR #90) and arrived
in this worktree via the `origin/main` merge, but
`mcp_harness/headless_treemaker.cpython-314-darwin.so` in this worktree is a
symlink into the main checkout's build, which predates that C++ change — the
known "borrowed `.so`" trap (see memory:
`worktree-missing-build-artifacts`, `linux-ci-3-failures-diagnosis-outcome`).
The `.so` was deliberately **not** rebuilt here: it is a symlink into the
user's main checkout, and rebuilding it in place would overwrite their main
artifact from a task with no mandate to touch it.

**Non-causation was verified directly, not inferred**: with
`mcp_harness/shaping.py` and `mcp_harness/shaping_deep.py` reverted to
`c5da4c1` (the state immediately before any production change in this arc),
the same 13 tests still fail — `13 failed, 18 passed in 2.19s` on that
narrower run. The working tree was restored to the fixed state afterward.

So the accurate statement is: **no shaping test regressed, and no
previously-green test in this worktree turned red — but the suite is not
all-green here, for a reason (a stale symlinked `.so`) that predates and is
independent of this arc's changes.** This is recorded plainly rather than
claimed as a clean suite.

## 4. The `_find_tip` bind-distance table (spec §6)

Measured 2026-08-09 over `mcp_harness/tests/goldens/`, counting vertices
`_find_tip`'s own predicate accepts, before and after `complete_square`:

| golden | raw → served tips | min served spacing | half |
|---|---|---|---|
| hf-dog-nudged | 11 → 7 | 0.020479 | 0.0102 |
| dog-repaired | 18 → 8 | 0.145802 | 0.0729 |
| dog | 16 → 8 | 0.174600 | 0.0873 |
| star-4 | 8 → 8 | 0.500000 | 0.2500 |
| hshape | 8 → 4 | 0.589256 | 0.2946 |
| hf-crane-ladder-blb | 7 → 2 | 0.635996 | 0.3180 |
| quad | 6 → 3 | 1.003812 | 0.5019 |
| hf-dog-ladder-best | 7 → 1 | — | — |
| bear-base | 1 → 1 | — | — |

`TIP_BIND_MAX = 0.05` sits below half the minimum served spacing on 6 of the
7 goldens with >=2 served tips, so on those a bind within the bound is
provably unambiguous. It does **not** solve wrong-flap ambiguity on dense
models (`hf-dog-nudged`'s served tips are 0.020479 apart — no absolute bound
both admits legitimate requests and separates those).

`mcp_harness/server.py:2392` hardcodes `_ref_xy = (0.0, 0.46801304)` — dog's
`front_v18` site. Against `dog` (its intended subject) that point is an exact
served tip, so it binds at distance **0.000000**. Against `quad` the nearest
served tip is `(0.0, 0.0)`, so the same fixed point binds **0.468013** away —
the distance happens to equal the y-coordinate only because `quad`'s nearest
tip sits at the origin, not because of any general relationship between the
two. The mechanism is: `_ref_xy` is a hardcoded reference point built for one
golden, and nothing stops a caller from reusing it against a different
golden whose tip layout is unrelated. That reuse is exactly the failure mode
`TIP_BIND_MAX` is meant to catch — at `0.05`, `quad`'s bind is refused;
`dog`'s is not.

## 5. What this establishes, and what it does not

**Establishes:** that `shaping.apply_display_ops` now composes — an edge one
op partially folds is not silently reset to full mountain/valley by a later
op touching a different site — verified arithmetically, and that this fix is
a **no-op for every single-op case in the frozen baseline** (24/24 byte
identical), so every past single-op measurement in the arc (including P1's
capture fixture) remains valid and comparable.

Caveat on that no-op claim: none of the 9 goldens behind the 24 frozen keys
carries an incoming `edges_foldAngle`, so the baseline cannot exercise the
case where a length-matching incoming array is *honored* rather than
discarded (`_seed_fold_angles` only discards on a length mismatch). A
follow-up test,
`test_incoming_fold_angle_survives_on_an_edge_the_op_does_not_touch` in
`mcp_harness/tests/test_shaping_composition_gate.py`, now pins that
boundary directly — a synthetic fold with a length-matching, non-default
`edges_foldAngle` shows the value surviving on an edge the op never
touches.

**Does not establish:**

- Whether composed ops produce *better* models. This work is purely about
  whether the fold-angle array is preserved correctly across ops; it says
  nothing about aesthetic or anatomical quality of the result.
- Whether the B5-prime anti-additivity finding (median `|pred - meas|` =
  127.11 degrees over 7 pairs, against a threshold of 15) was an artifact of
  this defect. That hypothesis is now **testable** — it was not testable
  before this fix landed, because the operator itself was broken — but
  testing it requires the Gate-2 re-run under its own pre-registration
  (spec §8 non-goal 1, §10 risk 3). A green Gate-2 re-run would license the
  claim "the previously measured anti-additivity was substantially an
  artifact," not "composition works" — the additive predictor still needs
  its own validation on the corrected operator. Neither of those claims is
  made here.

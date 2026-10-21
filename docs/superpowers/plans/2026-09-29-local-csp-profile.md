# Local-CSP Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Break dense `assign()`'s 740.16 s residual (79.57% of runtime) into named, non-overlapping components across all 8 subjects, so any local-CSP optimisation rests on a measurement rather than a guess.

**Architecture:** One read-only evidence script. It patches a **temp copy** of the real `box_pleat/assign.py` by renaming each target function and inserting a timing wrapper, asserts the diff contains only lines it added, then runs dense `assign()` at a fixed node budget per subject. Self-time accounting subtracts measured children from each enclosing block. A `cProfile` sweep on `lizard` gates the whole thing on completeness. **No production code changes.**

**Tech Stack:** Python 3.14, the existing `mcp_harness/box_pleat/` package, `cProfile` from the stdlib. No new dependencies. No pytest file (nothing in production changes).

**Spec:** `docs/superpowers/specs/2026-09-29-local-csp-profile-design.md`. Every `§` below refers to it. **Read §1.1 first** — the goal is measurability on more subjects, explicitly NOT convergence.

## Global Constraints

* **Python is `../.venv/bin/python3`, run from `mcp_harness`.** `mcp_harness/conftest.py`'s autouse fixture imports `mesh_to_tree`, gating all test collection on skeletor/trimesh/networkx/numpy.
* **Never pass `--timeout`** to pytest (no `pytest-timeout` in that venv) and **never run `pytest tests/`** (5,167 tests, >3 h). This slice needs no pytest run.
* **Nothing under `mcp_harness/` may change.** The instrument patches a **temp copy**; production is read, never written. `grep -c box_pleat mcp_harness/server.py` stays 0.
* **Every patch anchor must appear exactly once in production, or the script REFUSES to run.** Verified 2026-09-29: all eleven anchors below occur exactly once.
* **Self-time is mandatory (§3.2):** `pick`'s total includes `free_vars_at` and the `now_open` scan; `retry`'s total includes `violation` (via `feasible`) and `hits_nogood`. Enclosing blocks are reported as total minus measured children. Never report a raw total as a component.
* **`global_check` must stay (§3.3).** With `global_check=None` there are no rejections, so `assign` returns on the first complete candidate and dense `lizard` reaches one in 0.76 s.
* **Node count must be counted, not inferred (§1.2).** `AssignFail("budget", budget)` reports the budget, not the consumption.
* **Fixed node budget across subjects**, recorded in the artifact, so per-node costs compare.
* **Per-subject cap set from committed readings, never borrowed.** `dog`'s sparse compile alone is **537.3 s** (`evidence/2026-09-20-box-pleat/oracle-census/certify.json`). Use **1800 s**.
* **`cProfile` is a completeness check, NEVER a share (§6).** Its numbers must not appear in the README as percentages of anything.
* **Never use bare `git stash` / `git stash pop`** — the stash stack is shared with other worktrees and concurrent sessions.
* **Commit messages end with** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
* **Component names are exactly** `setup`, `pick`, `now_open`, `free_vars_at`, `violation`, `prefer`, `materialise`, `retry`, `hits_nogood` — spelled that way in the code, the JSON and the README.
* **Never use tardigrade / water bear as a test subject** — OWNER INSTRUCTION.

## File Structure

| File | Responsibility |
|---|---|
| `docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py` (create) | the patch table, `build_instrumented()`, the pure arithmetic (self-times, shares, ceilings, the §4.3 bar), the `cProfile` sweep, and `--selftest` |
| `docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.json` (generated) | per-subject components + run metadata |
| `docs/superpowers/evidence/2026-09-29-local-csp-profile/cprofile-lizard.txt` (generated) | the completeness sweep's raw output |
| `docs/superpowers/evidence/2026-09-29-local-csp-profile/README.md` (create) | §5.5's required contents |

Three tasks. Task 1 is the harness and its self-test, which gates the runs. Task 2 spends the runs. Task 3 writes the verdict.

---

### Task 1: The patch harness and the arithmetic

**Files:**
- Create: `docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py`

**Interfaces:**
- Consumes: `box_pleat/assign.py` (read only, as text); `box_pleat.compile.compile_tree`; `flat_fold`; `box_pleat.emit`.
- Produces: `PATCHES` (a list of `(anchor, replacement)` pairs), `patch_source(src) -> str`, `self_times(probe) -> dict`, `ceiling(self_secs, total_secs) -> float`, `remainder_of(total_secs, global_check_secs, hits_nogood_secs) -> float`, `top_component(components) -> str`, `gate(components, remainder_secs, cprofile_uncovered) -> tuple`, `verdict(top_name, top_share, setup_share, scaling) -> tuple`, `select_uncovered(text, mod_file, owner_of, where) -> list`. Task 2 runs this file; nothing imports it. **`remainder_of`, `top_component` and `select_uncovered` are named functions rather than inline expressions for one reason: each encodes a choice that a mutation could silently reverse, and inline they were testable only by reading.**

**Context you need:** the model for this file is `docs/superpowers/evidence/2026-09-26-nogood-indexing/where_the_time_goes.py`. **Read it before writing yours** — you are extending its mechanism, not inventing one. Its two load-bearing properties are reused verbatim: it refuses when an anchor is not found exactly once, and it diffs the patched source against production and refuses if any removed line is not one it expected to remove. Its `_HEADER` is **appended, not prepended**, because `assign.py` opens with `from __future__ import annotations`, which must be the file's first statement. It loads the temp module under the **dotted** name `box_pleat._assign_instrumented`, because `assign.py` uses relative imports (`from . import interleave`) that resolve only when `__package__` is `box_pleat`.

- [ ] **Step 1: Create the directory**

```bash
mkdir -p docs/superpowers/evidence/2026-09-29-local-csp-profile
```

- [ ] **Step 2: Write the script**

Create `docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py`:

```python
"""What IS the 79.57%? Dense `assign()`'s residual, broken into named parts.

Spec: `../../specs/2026-09-29-local-csp-profile-design.md`. **Read its §1.1
first** -- the goal is measurability on more than one subject, NOT convergence.

WHY THIS EXISTS. `../2026-09-26-nogood-indexing/wtg-lizard-500k.json` apportions
dense `lizard`'s 930.19 s as layer check 19.15%, no-good scan 1.28%, remainder
**79.57%** (740.16 s). The 1.28% withdrew the indexing spec. The 79.57% is the
largest share and nothing has touched it -- but it is a RESIDUAL, defined as
`total - global_check - hits_nogood` and glossed "the local CSP search itself".
Nothing has measured what is inside it. That script exists because an earlier
apportionment used a constant conflating per-candidate with one-time costs, and
correcting it flipped the conclusion; a residual glossed rather than measured is
the same hazard one level down.

NOT A CONVERGENCE FIX, AND THE SPEC SAYS SO FIRST. `assign_budget` is a NODE
budget, so a cheaper node explores the same nodes faster, not more of them. The
only way to explore more is to raise the budget, and that is a recorded negative:
`../2026-09-24-dense-pleats/nogood-lizard-largebudget.json` has 10x the budget
buying 5.17x the candidates, the clause median unmoved (204.5 vs 202 solver
variables), 584 of 584 witnesses distinct, 2.46 hours, no convergence. What a
speedup can buy is a dense labelling on a subject other than `lizard` --
`octopus` and `dog` finish inside no cap this project has used, and every
finding across seven slices carries "this is lizard" as its limit.

AMDAHL IS IN THE BAR, NOT JUST THE PREAMBLE. Removing a component entirely buys
only its share of the TOTAL. A component at 50% of the remainder is 39.8% of
total -- a **1.66x** whole-run ceiling -- and the whole remainder running free
caps everything at 4.89x. So every component reports a `whole_run_ceiling` beside
its `share_of_remainder`, and the bar reads the ceiling. Otherwise a bar could say
"68% of the remainder!" and license work whose real ceiling is 2.2x: a share of a
share presented as a share of the whole.

SELF-TIME, BECAUSE THE CALL GRAPH NESTS. `retry` calls `feasible` (-> `violation`)
and `hits_nogood`; `pick` calls `eligible` -> `free_vars_at`, and contains the
`now_open` scan. Accumulating naively either pushes the shares past 100% or sums
to something plausible while charging a child's cost to its parent twice. Leaf
components are measured exclusively; every enclosing block is reported as its own
total MINUS its measured children.

WHY `global_check` STAYS. Passing `global_check=None` looks like it isolates the
local CSP. It does not: without rejections `assign` returns on the FIRST complete
candidate, and dense `lizard` reaches one in 0.76 s. The CEGAR rejections are what
drive the search deep.

NODES ARE COUNTED, NOT INFERRED. The 1.48 ms/node figure everyone quotes is
`remainder / hits_nogood_calls`, using the scan count as a PROXY because
`AssignFail("budget", budget)` reports the budget, not the consumption. That proxy
is the denominator of every per-node figure, so this script patches a real counter.

HOW IT INSTRUMENTS WITHOUT FORKING PRODUCTION. It READS the real
`box_pleat/assign.py`, applies the `PATCHES` table below by RENAMING each target
function and inserting a timing wrapper, writes the result to a temp module, and
ASSERTS the diff against production removes only the anchor lines it meant to
remove. Every anchor must occur exactly once or the script refuses. Production is
never written.

Run from mcp_harness:
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py --selftest
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py \\
      ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.json
  PYTHONPATH=. ../.venv/bin/python3 -u \\
      ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py \\
      --cprofile ../docs/superpowers/evidence/2026-09-29-local-csp-profile/cprofile-lizard.txt
"""
import contextlib
import datetime
import difflib
import importlib.util
import io
import json
import os
import pathlib
import signal
import subprocess
import sys
import textwrap
import time

# `cProfile` and `pstats` are imported INSIDE `cprofile_sweep`, not here, and
# that is load-bearing -- do not "tidy" them back to the top. This file is
# required to be named `profile.py` (spec §5.1), and stdlib `cProfile` does
# `import profile as _pyprofile` internally to borrow docstrings. Python puts a
# directly-run script's own directory first on `sys.path`, so that import
# resolves to THIS file, which has no `run` attribute, and `import cProfile`
# raises `AttributeError: module 'profile' has no attribute 'run'`. At module
# top that breaks all three commands in the docstring above -- including
# `--selftest` and the plain JSON run, neither of which profiles anything.
# Deferring the import into the one function that needs it makes every
# documented command run as printed, with no `-P` / PYTHONSAFEPATH flag.

RULE6 = os.path.join("..", "docs", "superpowers", "evidence",
                     "2026-09-08-vlm-tree-authoring", "data", "rule6_serve.json")
ASSIGN_SRC = pathlib.Path("box_pleat/assign.py")

SUBJECTS = ("starfish", "lizard", "frog", "horse",
            "bird", "guinea_pig", "octopus", "dog")

#: Spec §3.1. Order matters only for reporting.
COMPONENTS = ("setup", "pick", "now_open", "free_vars_at", "violation",
              "prefer", "materialise", "retry", "hits_nogood")

#: The components that are PARTS OF THE REMAINDER, i.e. the ones §4.1(2)'s
#: sum-check may add up. `hits_nogood` is MEASURED (its self-time is subtracted
#: from `retry`'s as a child, and reporting it lets a reader check this run
#: against the published 1.28% of total) but it is NOT a part of the remainder:
#: the remainder is DEFINED as `total - global_check - hits_nogood`, so
#: `hits_nogood`'s seconds are subtracted out of the very whole the sum is
#: compared against. Including it would compare the parts against a whole that
#: omits one of them -- measured on the committed `starfish` smoke row, that
#: error alone puts the sum-check 1.54% off where excluding it reads 0.71%, a
#: third of the 5% tolerance spent before any real error. The remainder's own
#: definition is NOT negotiable here: it is the quantity the predecessor script
#: published as 79.57%, and redefining it would make this a measurement of
#: something else.
REMAINDER_COMPONENTS = tuple(c for c in COMPONENTS if c != "hits_nogood")

#: Enclosing block -> the measured children whose time it contains (spec §3.2).
#: `pick` calls `eligible` -> `free_vars_at` and holds the `now_open` scan;
#: `retry` calls `feasible` -> `violation`, and `hits_nogood`.
CHILDREN = {"pick": ("free_vars_at", "now_open"),
            "retry": ("violation", "hits_nogood")}

#: A fixed NODE budget for every subject, so per-node costs are comparable.
#: Small enough that the largest subject completes it inside CAP_SECS.
BUDGET = 20_000

#: Spec §5.2: set ABOVE dog's committed 537.3 s sparse cost
#: (../2026-09-20-box-pleat/oracle-census/certify.json), never borrowed from a
#: sibling slice's dense arm -- which is how the 2026-09-28 headroom census lost
#: dog to a 300 s cap, predictably.
CAP_SECS = 1800

#: Spec §4.3 thresholds.
TOP_DOMINATES = 0.50        # share of remainder
NO_LEVER_BELOW = 0.25
SCALES = 2.0                # octopus per-node / lizard per-node
FLAT_AT_OR_BELOW = 1.2

#: Spec §4.1: components must sum to the remainder within this fraction.
GATE_SUM_TOL = 0.05


def _wrap(name, args, call):
    """A timing wrapper plus the renamed original's `def` line.

    Renaming beats reproducing the body: the patch is then a ONE-LINE anchor,
    so it cannot go stale against an edit inside a function it does not read.
    The wrapper resolves `_p_<name>` at CALL time from `assign`'s own local
    scope, where the renamed original is defined a few lines below it.
    """
    return (f"    def {name}({args}):\n"
            f"        _t0 = _perf()\n"
            f"        try:\n"
            f"            return _p_{name}({call})\n"
            f"        finally:\n"
            f'            _PROBE["{name}_secs"] += _perf() - _t0\n'
            f'            _PROBE["{name}_calls"] += 1\n'
            f"\n"
            f"    def _p_{name}({args}):\n")


#: (anchor, replacement). Every anchor MUST occur exactly once in production --
#: verified 2026-09-29 for all eleven. `feasible` is deliberately NOT wrapped:
#: it is `return violation(v) is None`, so wrapping both would double-count.
PATCHES = [
    # --- rename-and-wrap the six functions in the search loop --------------
    ("    def violation(v):\n",     _wrap("violation", "v", "v")),
    ("    def free_vars_at(v):\n",  _wrap("free_vars_at", "v", "v")),
    ("    def prefer(var):\n",      _wrap("prefer", "var", "var")),
    ("    def materialise():\n",    _wrap("materialise", "", "")),
    ("    def pick():\n",           _wrap("pick", "", "")),
    ("    def retry() -> bool:\n",  _wrap("retry", "", "")),
    ("    def hits_nogood() -> bool:\n", _wrap("hits_nogood", "", "")),

    # --- the `now_open` scan is a single statement inside `pick` -----------
    ("        now_open = any(var not in value for var in pleat_pref if var in touching)\n",
     "        _t0n = _perf()\n"
     "        now_open = any(var not in value for var in pleat_pref if var in touching)\n"
     '        _PROBE["now_open_secs"] += _perf() - _t0n\n'
     '        _PROBE["now_open_calls"] += 1\n'),

    # --- count nodes for real (spec §1.2) ---------------------------------
    ("        nodes -= 1\n",
     "        nodes -= 1\n"
     '        _PROBE["nodes"] += 1\n'),

    # --- setup starts at the first real work in `assign` -------------------
    ("    pieces = build_pieces(layout, ridges, contours)\n",
     '    _PROBE["_t_start"] = _perf()\n'
     "    pieces = build_pieces(layout, ridges, contours)\n"),

    # --- the setup/search boundary: snapshot every counter -----------------
    # Everything before `nodes = budget` is one-time. Snapshotting here lets
    # per-search figures be reported as DELTAS, so `violation`'s setup calls
    # (the `for v in interior: law = violation(v)` loop) are not charged to
    # the search.
    ("    nodes = budget\n",
     '    _PROBE["setup_secs"] = _perf() - _PROBE["_t_start"]\n'
     '    _PROBE["_snap"] = {k: v for k, v in _PROBE.items()\n'
     "                       if isinstance(v, (int, float))}\n"
     "    nodes = budget\n"),
]

#: APPENDED, not prepended: `assign.py` opens with `from __future__ import
#: annotations`, which must be the first statement in the file. The wrappers
#: resolve `_perf` and `_PROBE` as module globals at CALL time, so defining
#: them at the end of the module is correct.
_HEADER = '''

from time import perf_counter as _perf
import collections as _collections
_PROBE = _collections.defaultdict(float)
'''


def patch_source(src):
    """Apply PATCHES to `src`. Raises SystemExit if any anchor is not unique.

    Pure on its argument so `--selftest` can feed it altered source and prove
    the refusal fires (spec §5.4 test 4).
    """
    out = src
    for anchor, replacement in PATCHES:
        n = out.count(anchor)
        if n != 1:
            raise SystemExit(
                f"REFUSING TO MEASURE: anchor {anchor!r} occurs {n} times in "
                f"box_pleat/assign.py, expected exactly 1. Production has "
                f"changed; re-derive this patch against today's source before "
                f"trusting any number from it.")
        out = out.replace(anchor, replacement, 1)
    return out + _HEADER


def verify_diff(src, patched):
    """Refuse unless every removed line is an anchor we meant to remove."""
    allowed = set()
    for anchor, _ in PATCHES:
        allowed |= set(anchor.splitlines())
    removed = []
    for line in difflib.unified_diff(src.splitlines(), patched.splitlines(),
                                     lineterm="", n=0):
        if line[:3] in ("+++", "---", "@@ "):
            continue
        if line.startswith("-"):
            removed.append(line[1:])
    unexpected = [r for r in removed if r not in allowed]
    if unexpected:
        raise SystemExit(f"REFUSING TO MEASURE: patch removed unexpected "
                         f"lines: {unexpected}")


def build_instrumented():
    """Patch production `assign.py` in memory, verify the diff, import it."""
    src = ASSIGN_SRC.read_text()
    patched = patch_source(src)
    verify_diff(src, patched)
    out = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_assign_profiled.py"
    out.write_text(patched)
    # Dotted name: `assign.py` uses relative imports (`from . import
    # interleave`), which resolve only when `__package__` is `box_pleat`.
    import box_pleat  # noqa: F401 -- must be in sys.modules for those imports
    name = "box_pleat._assign_profiled"
    spec = importlib.util.spec_from_file_location(name, out)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# pure arithmetic
# --------------------------------------------------------------------------
def self_times(probe):
    """Component -> SELF seconds (spec §3.2): total minus measured children.

    `probe` is the post-run counter dict, already reduced to search-only
    deltas by `search_deltas`. A negative self-time means a child was charged
    time its parent did not contain, i.e. the CHILDREN map is wrong -- so it
    is surfaced as a hard error rather than clamped to zero.
    """
    out = {}
    for c in COMPONENTS:
        total = float(probe.get(f"{c}_secs", 0.0))
        for child in CHILDREN.get(c, ()):
            total -= float(probe.get(f"{child}_secs", 0.0))
        if total < 0:
            raise SystemExit(
                f"REFUSING TO REPORT: self-time for {c!r} is negative "
                f"({total:.4f}s). Its measured children exceed its own total, "
                f"so CHILDREN misdescribes the call graph and every share "
                f"below it is wrong.")
        out[c] = total
    return out


def search_deltas(probe):
    """Counters for the SEARCH only: post-run minus the setup-boundary snapshot.

    `setup_secs` is excluded from the subtraction -- it IS the setup figure and
    is not a delta.
    """
    snap = probe.get("_snap") or {}
    out = {}
    for k, v in probe.items():
        if k.startswith("_"):
            continue
        if k == "setup_secs":
            out[k] = float(v)
        elif isinstance(v, (int, float)):
            out[k] = float(v) - float(snap.get(k, 0.0))
    return out


def ceiling(self_secs, total_secs):
    """Whole-run speedup if this component cost nothing (spec §4.2).

    DERIVED, and the actionable figure: a component at 50% of a 79.57%
    remainder is 39.8% of total and yields 1.66x, not 2x.
    """
    if total_secs <= 0 or self_secs >= total_secs:
        return None
    return 1.0 / (1.0 - self_secs / total_secs)


def remainder_of(total_secs, global_check_secs, hits_nogood_secs):
    """The remainder, by the ONE definition this whole slice measures against.

    `total - global_check - hits_nogood`, i.e. the quantity the predecessor
    script published as 79.57% of dense `lizard`. This is a three-line function
    only because it is the DEFINITIONAL ANCHOR of the entire measurement: every
    `share_of_remainder`, the §4.1(2) sum-check's whole, `per_node_ms`'s
    numerator and hence the `scaling` reading that drives two of the four §4.3
    rows all hang off it. Inline in `run_subject` it was protected by nothing
    but reading -- dropping the `- hits_nogood` term left `--selftest` green
    while silently redefining what is being measured. As a named function it is
    exact-testable on integers.
    """
    return total_secs - global_check_secs - hits_nogood_secs


def top_component(components):
    """The top component OF THE REMAINDER: `max` over REMAINDER_COMPONENTS.

    Selected over `REMAINDER_COMPONENTS`, never `COMPONENTS`: a component the
    remainder's own definition subtracts out can never be the top component of
    it, and `hits_nogood` is routinely large enough to win a `max` over the full
    set. Named rather than inline in `main` so the choice of set is testable --
    inline, reverting it to `COMPONENTS` left `--selftest` green.
    """
    return max(REMAINDER_COMPONENTS, key=lambda c: components[c])


def gate(components, remainder_secs, cprofile_uncovered):
    """Spec §4.1, evaluated BEFORE any row. Returns (passed, [failure, ...]).

    Takes the full component dict (signature unchanged) and selects
    `REMAINDER_COMPONENTS` inside: `hits_nogood` is measured but is not a part
    of the remainder, so it must not be added into a sum compared against it.
    """
    bad = []
    if cprofile_uncovered:
        bad.append(f"§4.1(1) cProfile names {len(cprofile_uncovered)} hot "
                   f"function(s) no accumulator covers: {cprofile_uncovered}")
    got = sum(components[c] for c in REMAINDER_COMPONENTS if c in components)
    if remainder_secs <= 0:
        bad.append("§4.1(2) remainder_secs is not positive")
    else:
        rel = abs(got - remainder_secs) / remainder_secs
        if rel > GATE_SUM_TOL:
            bad.append(f"§4.1(2) components sum to {got:.1f}s against a "
                       f"remainder of {remainder_secs:.1f}s "
                       f"({100 * rel:.1f}% off, tolerance "
                       f"{100 * GATE_SUM_TOL:.0f}%)")
    return not bad, bad


def verdict(top_name, top_share, setup_share, scaling):
    """Spec §4.3, evaluated in the spec's order. Returns (verdict, why).

    ROW 3 IS CHECKED FIRST: `setup` is one-time, so a setup-dominated residual
    must not license per-node optimisation via row 1 or 2.
    """
    if setup_share >= TOP_DOMINATES:
        return "DIFFERENT FIX", "setup dominates; a one-time cost cannot grow with node count"
    if top_name == "setup":
        return "DIFFERENT FIX", "the top component is one-time setup"
    if top_share >= TOP_DOMINATES:
        if scaling is None:
            return "REPORT AND DECIDE", "no scaling reading (octopus produced no row)"
        if scaling >= SCALES:
            return "OPTIMISE IT", f"{top_name} dominates and per-node cost scales {scaling:.2f}x"
        if scaling <= FLAT_AT_OR_BELOW:
            return ("GENERALITY NOT REACHABLE THIS WAY",
                    f"{top_name} dominates but per-node cost is flat ({scaling:.2f}x)")
        return "REPORT AND DECIDE", f"scaling {scaling:.2f}x falls in the no-commitment band"
    if top_share < NO_LEVER_BELOW:
        return "NO SINGLE LEVER", f"top component is only {100 * top_share:.1f}% of the remainder"
    return "REPORT AND DECIDE", f"top component {100 * top_share:.1f}% is between the thresholds"
```

The rest of the script -- `_selftest`, `run_subject`, `cprofile_sweep` and `main` -- is Step 3. Keep this step's commit to the code above plus the imports, so a reviewer can judge the patch table on its own.

- [ ] **Step 3: Append the runner, the cProfile sweep and the self-test**

Append to the same file:

```python
#: Accumulator-covered names, for the §4.1(1) completeness check. A cProfile
#: entry that is RESIDENT IN THE INSTRUMENTED MODULE'S FILE, whose function
#: name is not here, and whose cumulative time exceeds COVER_MIN_SHARE of
#: `assign`'s OWN cumulative time, is an UNCOVERED hot function.
#:
#: WHAT THIS SET NOW MEANS FOR THE CHECK'S LIVE SENSITIVITY -- READ THIS BEFORE
#: REPORTING §4.1(1) AS "MEASURED", BECAUSE IT IS NOT. The names below cover
#: EVERY function defined in the file the sweep reads. Counted with `ast`
#: 2026-09-29: production `assign.py` defines 27 (14 module-level + 13 nested),
#: the PATCHED module defines 34 (the same 14, and 20 nested -- the 7 `_p_*`
#: renames added), and `set(defined) - COVERED` is EMPTY on both. (`COVERED`
#: additionally lists `arrangement_ok_at_vertex`, which `assign.py` imports from
#: `cp_audit` rather than defining, so the file filter would drop it anyway --
#: belt and braces, not a 35th function.) Meanwhile
#: `cprofile_sweep`'s file filter structurally excludes every other module and
#: every C builtin. So no NAMED, file-resident function can be flagged: each one
#: is either an accumulator (category A) or sits inside an interval some
#: accumulator already times (category B, each justification verified by
#: call-site analysis). The named-function limb of §4.1(1) is therefore
#: satisfied STRUCTURALLY, not measured -- see `SWEEP_SCOPE`. The only thing the
#: sweep can still flag is an ANONYMOUS frame (`<genexpr>`, `<lambda>`) owned by
#: `assign` itself or by module level, which is exactly the case
#: `enclosing_defs`' `own != "assign"` carve-out preserves.
#:
#: AND THE SPEC'S OWN THREE EXAMPLES ARE ALL OUT OF REACH. §4.1(1) names "a cost
#: in `_deg`, in a tuple `__hash__`, or in a comprehension nobody wrapped".
#: `_deg` is pre-declared covered below; a `__hash__` is a builtin or lives in
#: another file and the file filter drops it; and on Python 3.14 PEP 709 INLINES
#: list/dict/set comprehensions, so they emit no `cProfile` frame at all
#: (verified on 3.14.3: a genexpr appears as `<genexpr>`, the three
#: comprehensions appear nowhere). A comprehension nobody wrapped is invisible
#: to the check written to catch it. That is a named blind spot, not a defect to
#: patch here: making it visible needs a different instrument (`sys.monitoring`
#: or a line profiler), which is out of scope for this slice.
#:
#: EVERY NAME BELOW WAS ADDED BEFORE ANY RUN, WITH A STRUCTURAL REASON, AND
#: THAT IS THE DISTINCTION THAT MATTERS. Task 2's brief forbids adding names to
#: `COVERED` *to make a failing gate pass* -- a post-hoc addition made after
#: seeing a failure, which is this project's named recurring failure mode
#: (loosening a gate to reach a headline). These are pre-run, and each one
#: falls into exactly one of two categories, named inline:
#:   (A) it is an accumulator, or the renamed original behind one;
#:   (B) it is reached from `assign` but sits INSIDE an interval some
#:       accumulator already measures -- so its time is already counted, and
#:       flagging it would be double-reporting, not a gap.
#: A name with no such reason does NOT belong here, whatever the sweep says.
COVERED = {
    # (A) the accumulators themselves, and the renamed originals they wrap.
    "violation", "free_vars_at", "prefer", "materialise", "pick",
    "retry", "hits_nogood", "_p_violation", "_p_free_vars_at",
    "_p_prefer", "_p_materialise", "_p_pick", "_p_retry",
    "_p_hits_nogood", "assign",
    # (B) inside `pick`'s measured interval: `pick` calls `eligible`, which
    # calls `free_vars_at` (itself an accumulator).
    "eligible",
    # (B) inside `violation`'s measured interval: `feasible` is
    # `return violation(v) is None` and is deliberately unwrapped to avoid
    # double-counting; the rest are called from `violation`'s body.
    "feasible", "can_be_flat", "other_end", "_deg",
    "_maekawa_feasible", "_blb_prune", "arrangement_ok_at_vertex",
    # (B) inside the `setup` interval -- everything `assign` runs before
    # `nodes = budget`, which `setup_secs` times as one duration.
    # `build_pieces` -> `_key` / `_unit_pieces`; `faces`; `profiles` ->
    # `_inside`; `initial_readings` -> `label_from_profile` -> `_side`;
    # `pleat_paths` -> its local `find` / `union`.
    # (`_unit_pieces` is additionally imported by `box_pleat.layers`, so some
    # of its cumulative time is spent inside the `global_check` spy -- which
    # is outside the remainder entirely, and so also not a gap.)
    "build_pieces", "_key", "_unit_pieces", "faces", "profiles", "_inside",
    "initial_readings", "label_from_profile", "_side", "pleat_paths",
    "find", "union",
}
COVER_MIN_SHARE = 0.05

#: What the §4.1(1) sweep's outcome MEANS, carried wherever that outcome is
#: printed or recorded -- the same discipline `gate_scope` applies to §4.1(2).
#: "all hot functions covered" on its own overstates the result: it reads as a
#: measurement when the named-function limb is satisfied by construction.
SWEEP_SCOPE = (
    "§4.1(1) SCOPE: `COVERED` names every function defined in the patched "
    "module (34/34, `ast`-counted) and the file filter excludes every other "
    "module and all C builtins, so the named-function limb is satisfied "
    "STRUCTURALLY, not measured -- an empty list here is not evidence that a "
    "sweep looked for a named gap and found none. What this sweep can still "
    "flag, and all it can flag, is an ANONYMOUS frame (`<genexpr>`, `<lambda>`) "
    "owned by `assign`'s own loop or by module level. KNOWN BLIND SPOT: on "
    "Python 3.14 PEP 709 inlines list/dict/set comprehensions, so §4.1(1)'s own "
    "example -- 'a comprehension nobody wrapped' -- emits no cProfile frame and "
    "cannot be flagged at all. §4.1(2)'s sum-check is the live NUMERICAL "
    "completeness check; this limb is the structural one.")


def enclosing_defs(src):
    """Return `lineno -> innermost enclosing def name` for `src`.

    WHY THIS EXISTS, and it is a MEASURED reason, not a tidiness one. Restricting
    candidates to the instrumented module's own file (see `cprofile_sweep`) cuts
    the false positives from 23 to 1, and the one that survives is an ANONYMOUS
    code object: `_assign_profiled.py:1034(<genexpr>)`, the
    `all(feasible(w) for w in touching.get(var, ()))` generator inside `retry`.
    Its time is entirely inside `retry`'s measured interval, so it is not a gap
    -- but `COVERED` is keyed by name, and `<genexpr>` cannot be listed there
    without blanket-excluding every generator in the file, including GENERATOR
    EXPRESSIONS in `assign`'s own main loop, which NO accumulator measures.

    "GENERATOR expressions" is the precise claim, and an earlier revision of this
    docstring said "generators ... including ones in `assign`'s own main loop"
    as if it covered comprehensions too. It does not, and the difference is
    load-bearing: on Python 3.14 (measured on 3.14.3) PEP 709 INLINES
    list/dict/set comprehensions into their enclosing code object, so they emit
    no `cProfile` frame and reach neither this resolver nor the sweep. A
    genexpr still emits `<genexpr>` and is resolved here. So this function's
    live reach is genexprs and lambdas only; see `SWEEP_SCOPE`.

    So an anonymous frame is resolved to the `def` that lexically contains it
    and judged by that owner. `ast`, not a regex over indentation, because the
    answer has to be right: a wrong owner either hides a real finding or
    manufactures a false one.
    """
    import ast

    spans = []
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            spans.append((node.lineno, node.end_lineno, node.name))

    def owner(lineno):
        best = None
        for s, e, n in spans:
            if s <= lineno <= e and (best is None or (e - s) < best[1] - best[0]):
                best = (s, e, n)
        return best[2] if best else None

    return owner


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _commit():
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception as exc:                    # noqa: BLE001 -- metadata only
        return f"unavailable: {exc}"


def _entry(subject):
    with open(RULE6) as fh:
        return next((e for e in json.load(fh) if e["subject"] == subject), None)


def run_subject(subject, mod):
    """Sparse-compile `subject`, then dense-assign it under the patched module.

    Returns a row dict. Never raises `Exception` on a subject (spec §5.3): a cap
    breach, a compile stop or an engine exception is recorded as that subject's
    outcome so the ladder continues. The ONE thing that still escapes is a
    `BaseException` -- in practice `self_times`' `SystemExit` soundness refusal,
    which is not one subject's bad luck but a statement that the CHILDREN map is
    wrong; see the `except Exception` clause below.
    """
    from box_pleat import emit                  # noqa: F401 -- parity of imports
    from box_pleat.compile import compile_tree
    import flat_fold
    from box_pleat import layers as _layers

    entry = _entry(subject)
    if entry is None:
        return {"subject": subject, "outcome": "not in rule6_serve"}
    row = {"subject": subject}

    old = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(CAP_SECS)
    t0 = time.time()
    try:
        res = compile_tree(entry["requested"], entry["pairs"])
        if not res.contours or res.layout is None:
            row["outcome"] = f"no contours; stopped at {res.stage_reached}"
            return row
        row["sparse_secs"] = round(time.time() - t0, 1)
        row["N"] = res.layout.N
        row["stage_reached"] = res.stage_reached

        # The layer check, timed from the caller exactly as
        # ../2026-09-26-nogood-indexing/where_the_time_goes.py does: a spy
        # around the real `_check` work, so `global_check_secs` is measured and
        # not estimated. `global_check` must stay (spec §3.3).
        gc_secs = [0.0]
        graph_cell, topo_cell = [], []

        def spy(cand):
            g0 = time.perf_counter()
            try:
                fold = emit.to_fold(res.layout, cand)
                ff = flat_fold.flat_fold(fold)
                if not graph_cell:
                    graph_cell.append(_layers.constraint_graph(ff))
                labels = {k: a for _, _, k, a in ff.shared_edges
                          if a in ("M", "V")}
                w = _layers.propagate(graph_cell[0], labels)
                if w is None:
                    return None
                return _layers.piece_keys(w, fold), w
            finally:
                gc_secs[0] += time.perf_counter() - g0

        mod._PROBE.clear()
        a0 = time.perf_counter()
        out = mod.assign(res.layout, res.ridges, res.boundary_ridges,
                         res.contours, budget=BUDGET, global_check=spy,
                         dense=True)
        total = time.perf_counter() - a0

        raw = dict(mod._PROBE)
        # An `assign` that returns BEFORE `nodes = budget` -- a `build_pieces`
        # or `profiles` AssignFail, a `"<law>_fixed"` verdict,
        # `"unbound_variable"` -- never reaches the setup/search boundary, so
        # `_snap` is unset. Without it `search_deltas` subtracts nothing, every
        # counter is reported as search time, `setup_secs` reads 0.0 and the
        # setup loop's `violation` cost is misattributed to a search that never
        # ran. That must not be stamped "ok".
        if "_snap" not in raw:
            row["outcome"] = ("assign returned before the setup/search boundary "
                              "(`nodes = budget`), so no setup/search split "
                              f"exists: {repr(out)[:100]}")
            row["assign_outcome"] = repr(out)[:120]
            row["total_secs"] = round(total, 2)
            row["global_check_secs"] = round(gc_secs[0], 2)
            return row

        probe = search_deltas(raw)
        comps = self_times(probe)
        nodes = int(probe.get("nodes", 0))
        remainder = remainder_of(total, gc_secs[0], comps["hits_nogood"])
        ceilings = {c: ceiling(v, total) for c, v in comps.items()}
        row.update({
            "outcome": "ok",
            "assign_outcome": repr(out)[:120],
            "budget": BUDGET,
            "nodes": nodes,
            "total_secs": round(total, 2),
            "global_check_secs": round(gc_secs[0], 2),
            "remainder_secs": round(remainder, 2),
            # The SAME quantity unrounded, and it is not redundant: the §4.1(2)
            # gate is evaluated against THIS one, by `main` and by `--selftest`
            # alike. `remainder_secs` is rounded to 2 dp for the artifact, and
            # on a sub-second subject that rounding is a +-1.67% quantum against
            # a 5% tolerance -- enough, on top of the genuine ~0.3-1% unmeasured
            # -loop gap, to make a deterministic gate read as a coin flip.
            # Rounding belongs in the display, never in the assertion.
            "remainder_secs_exact": remainder,
            "components": {c: round(v, 4) for c, v in comps.items()},
            "calls": {c: int(probe.get(f"{c}_calls", 0)) for c in COMPONENTS},
            # `hits_nogood` is deliberately `None`, not a number: the remainder
            # is defined as `total - global_check - hits_nogood`, so a "share of
            # the remainder" for it would be a share of a quantity that excludes
            # it.
            "share_of_remainder": {
                c: (round(v / remainder, 4)
                    if (remainder > 0 and c in REMAINDER_COMPONENTS) else None)
                for c, v in comps.items()},
            # A share of TOTAL, which DOES include `hits_nogood` -- so every
            # component gets one, this one included.
            "whole_run_ceiling": {c: (round(k, 3) if k is not None else None)
                                  for c, k in ceilings.items()},
            "per_node_ms": (round(1000 * remainder / nodes, 4) if nodes else None),
        })
        return row
    except _Timeout:
        row["outcome"] = f"exceeded {CAP_SECS}s"
        return row
    except Exception as exc:                    # noqa: BLE001 -- see below
        # ONE SUBJECT'S ENGINE CRASH MUST NOT COST THE LADDER. Project memory
        # records `spider_2` SIGSEGV-ing this engine; a Python-level engine
        # exception used to propagate out of here and abort every remaining
        # subject, after up to 30 minutes of work. Spec §5.3: "the profile never
        # raises on a subject".
        #
        # `Exception`, NOT `BaseException`, AND THAT IS LOAD-BEARING. Everything
        # this clause now spans includes `self_times`, whose negative-self-time
        # refusal is a SOUNDNESS refusal raised as `SystemExit` -- it means the
        # CHILDREN map misdescribes the call graph, so every share below it is
        # wrong, and it must abort the run rather than be filed as one subject's
        # bad luck. `SystemExit` inherits from `BaseException`, not `Exception`,
        # so it escapes this clause untouched. `--selftest` asserts that escape;
        # widening this to `BaseException` turns the self-test red. A
        # `KeyboardInterrupt` escapes for the same reason.
        row["outcome"] = f"raised {type(exc).__name__}: {exc}"[:300]
        row["error_type"] = type(exc).__name__
        return row
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old)


def cprofile_sweep(mod, out_path):
    """§4.1(1): name every hot function, so the accumulators can be checked.

    NOT a share measurement (spec §6) -- a deterministic profiler distorts
    many-small-call workloads, and at 23.7 us per hits_nogood call this is
    exactly that. Its only job is to surface a hot function no accumulator
    covers.

    WHAT THIS CHECK CAN AND CANNOT STILL FIND -- READ `SWEEP_SCOPE` AND
    `COVERED`'S COMMENT BEFORE REPORTING ITS OUTCOME. `COVERED` now names all 34
    functions defined in the patched module and the file filter below excludes
    every other module and all C builtins, so NO named, file-resident function
    can be flagged: §4.1(1)'s named-function limb is satisfied STRUCTURALLY, by
    construction, not measured. The live sensitivity that remains is an
    ANONYMOUS frame (`<genexpr>`, `<lambda>`) owned by `assign`'s own loop or by
    module level. §4.1(1)'s own example -- a comprehension nobody wrapped --
    cannot be flagged at all on Python 3.14, where PEP 709 inlines
    list/dict/set comprehensions so they emit no frame. An empty uncovered list
    is therefore NOT a measurement of completeness; §4.1(2)'s sum-check is.

    TWO THINGS THE CANDIDATE SELECTION MUST GET RIGHT, both learned the hard
    way, because a check that cannot fail for the reason it exists is this
    project's named recurring failure mode:

    1. THE DENOMINATOR IS `assign`'S OWN CUMULATIVE TIME, not the first line of
       the listing. The profiled callable is all of `run_subject` -- the sparse
       `compile_tree`, the `global_check` spy, and `once`/`run_subject`
       themselves -- so the first line's cumulative is the WHOLE run.

       WHAT THAT BUYS, STATED AS THE RATIO IT ACTUALLY IS. Write
       `r = assign_cum / whole_cum`. This check flags an `assign`-internal
       function at fraction `f` of `assign` when `f >= COVER_MIN_SHARE`; the old
       whole-run denominator flagged it only when `f * r >= COVER_MIN_SHARE`,
       i.e. `f >= COVER_MIN_SHARE / r`. So the window the new denominator buys is
       `COVER_MIN_SHARE <= f < COVER_MIN_SHARE / r`, and it is non-empty exactly
       when `r < 1`. It is NOT a fixed percentage, because `r` is a property of
       each run, and an earlier revision of this docstring asserted a flat "6% of
       `assign`" that does not hold on the subject that matters: a 6% function
       needs `r < 5/6 = 0.833` to have been missed before.
       Measured windows, both first-hand on this instrument, 2026-09-29:
         * `starfish`: r = 1.737 / 2.235 = 0.7772, window 5.00% <= f < 6.43%
           (three consecutive trials read r = 0.7772 / 0.7792 / 0.7758, i.e. the
           window's upper edge moves in the third significant figure).
           A 6% function WAS missed by the old check here.
         * `lizard`:   r = 122.674 / 135.872 = 0.9029, window
           5.00% <= f < 5.54%. A 6% function was NOT missed by the old check
           here: 6% of `assign` is 5.42% of the whole run, already over the
           threshold. (An earlier revision of this docstring cited exactly that
           6% case as the finding the fix buys. On `lizard` it is not one.)
       The window is narrow and subject-dependent; it is still the correct
       denominator, because §4.1(1) asks a question about `assign`, and a
       denominator that grows with unrelated work outside `assign` makes the
       threshold mean something different on every subject.

       A missing `assign` entry RAISES: a denominator that silently defaults is
       a gate that silently passes.
    2. CANDIDATES ARE RESTRICTED TO FUNCTIONS RESIDENT IN THE INSTRUMENTED
       MODULE'S FILE. §4.1(1) asks "is there a hot function inside `assign`
       that no accumulator covers?", and `compile_tree`, `spy`, `to_fold`,
       `flat_fold`, `propagate`, `piece_keys`, `constraint_graph`,
       `run_subject` and `once` are none of them -- they live in other files,
       and the filter excludes them STRUCTURALLY, without this table having to
       name them. `once` in particular has `cum == total`, so an unfiltered
       check reports its own top frame as uncovered, every time.
    """
    # Deferred on purpose -- see the comment beside the imports at the top of
    # this file. Importing `cProfile` at module scope breaks every command this
    # script documents, because this file is named `profile.py`.
    #
    # Deferring alone is NOT enough, and that was measured: `--cprofile` still
    # died here, because `sys.path[0]` is still this file's own directory when
    # the script is run by path, so `cProfile`'s internal `import profile`
    # still finds THIS file. So drop this directory from `sys.path` for the
    # duration of the two imports and put it straight back. Scoped to two
    # statements, restored in `finally`, and it touches nothing else the run
    # imports (the package comes from `PYTHONPATH=.`, i.e. `mcp_harness`, which
    # is a different directory).
    _here = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
    _saved_path = list(sys.path)
    sys.path[:] = [p for p in sys.path
                   if p and os.path.realpath(p) != _here]
    try:
        import cProfile
        import pstats
    finally:
        sys.path[:] = _saved_path

    row_holder = {}

    def once():
        row_holder["row"] = run_subject("lizard", mod)

    pr = cProfile.Profile()
    pr.enable()
    once()
    pr.disable()
    buf = io.StringIO()
    # UNBOUNDED, and that is deliberate: `print_stats(60)` bounded the candidate
    # set, so a file-resident function truncated below rank 60 was silently not
    # flagged -- whereas a MISSING `assign` row raises. The truncation is a
    # measured non-issue today and is removed anyway, because it costs one
    # argument and it also makes the written artifact re-derivable past 60 rows.
    # Measured on both subjects, 2026-09-29, and the truncation provably hid
    # nothing flaggable on either -- it was a bound, not an active fault:
    #   `starfish`: 47 file-resident entries in the full listing vs 17 inside
    #     `print_stats(60)`; lowest retained cumulative 0.022 s = 1.3% of
    #     `assign`'s 1.727 s, and the above-threshold set is identical between
    #     the two listings (12 entries).
    #   `lizard`:   47 vs 15; the 60th row of the whole listing is already down
    #     at 0.241 s = 0.20% of `assign`'s 122.674 s, against a 5% threshold of
    #     6.134 s.
    # Removed anyway, because it costs one argument and a silent truncation is
    # the wrong failure mode for a completeness check.
    pstats.Stats(pr, stream=buf).sort_stats("cumulative").print_stats()
    text = buf.getvalue()
    pathlib.Path(out_path).write_text(text)

    # Only functions defined in the patched temp copy of `assign.py` count.
    mod_file = os.path.basename(getattr(mod, "__file__", "") or "")
    owner_of = enclosing_defs(pathlib.Path(mod.__file__).read_text())
    return (select_uncovered(text, mod_file, owner_of, out_path), text,
            row_holder.get("row"))


def select_uncovered(text, mod_file, owner_of, where):
    """The §4.1(1) classifier, as a PURE function on a `pstats` listing.

    `text` is a `pstats` listing, `mod_file` the instrumented module's basename,
    `owner_of` an `enclosing_defs` resolver, `where` a path named in the refusal
    message. Returns the sorted uncovered labels.

    SEPARATE FROM `cprofile_sweep` SO IT CAN BE TESTED WITHOUT A 130-SECOND RUN.
    The whole classifier used to be inline, which meant the `own != "assign"`
    carve-out -- the one place this check can still fire, and the one deviation
    the previous fix wave made from its brief -- was protected by reading only.
    Removing that carve-out is precisely the direction in which a real uncovered
    hot function gets masked: `assign` is in `COVERED` because it is the
    DENOMINATOR, not because any accumulator measures its DFS loop. `--selftest`
    now feeds synthetic listing lines through here and asserts an
    `assign`-owned `<genexpr>` IS reported while a `_p_retry`-owned one is NOT.
    """
    entries = []                      # [(name, lineno, cum), ...], file-resident
    assign_cum = None
    for line in text.splitlines():
        # `ncalls tottime percall cumtime percall filename:lineno(function)`;
        # split at most 5 times so the location field keeps its own spaces
        # (built-ins render as `~:0(<built-in method builtins.len>)`).
        parts = line.split(None, 5)
        if len(parts) < 6:
            continue
        try:
            cum = float(parts[3])
        except ValueError:
            continue
        loc = parts[5].strip()
        if not loc.endswith(")") or ":" not in loc or "(" not in loc:
            continue
        head, _, name = loc[:-1].partition("(")
        fname, _, lineno = head.rpartition(":")
        if not lineno.isdigit():
            continue
        if os.path.basename(fname) != mod_file:
            continue                  # not inside the instrumented module
        entries.append((name, lineno, cum))
        if name == "assign" and assign_cum is None:
            assign_cum = cum

    if assign_cum is None or assign_cum <= 0:
        raise SystemExit(
            f"REFUSING TO GATE: no `assign` entry with positive cumulative "
            f"time was found in the cProfile listing for "
            f"{mod_file or '<unknown module file>'}. §4.1(1)'s denominator is "
            f"`assign`'s own cumulative time; without it this check would "
            f"compare against the whole run and pass by construction. Read "
            f"{where} and re-derive the parser before trusting any verdict.")

    uncovered = []
    for name, lineno, cum in entries:
        if cum / assign_cum < COVER_MIN_SHARE:
            continue
        label = f"{mod_file}:{lineno}({name})"
        if name.startswith("<") and name.endswith(">"):
            # An anonymous code object -- a generator expression, a lambda, a
            # comprehension. It has no name to match, so judge it by the `def`
            # that lexically contains it: its time IS that function's time.
            # `assign` itself is the deliberate exception. It is in `COVERED`
            # because it is the denominator, NOT because an accumulator
            # measures it, and its main DFS loop body is measured by nothing --
            # so a hot generator sitting directly in that loop is a genuine
            # §4.1(1) finding and must be reported.
            own = owner_of(int(lineno))
            label = f"{label} inside {own or '<module>'}"
            if own is not None and own != "assign" and own in COVERED:
                continue
        elif name in COVERED:
            continue
        # Seconds only, never a percentage: `cProfile` is a completeness check
        # and NEVER a share (spec §6). The line number is here so a `<genexpr>`
        # or `<lambda>` can be found without guessing.
        uncovered.append(f"{label} ({cum:.1f}s cum)")
    return sorted(set(uncovered))


def _selftest():
    """The arithmetic, the gate, the bar, and the patcher's refusal.

    Project memory records two throwaway probes that drove wrong conclusions in
    one session, one of which printed its verdict unconditionally. This runs in
    milliseconds and must pass before any subject is compiled.
    """
    # --- self-time: parent total MINUS measured children ------------------
    probe = {"pick_secs": 10.0, "free_vars_at_secs": 4.0, "now_open_secs": 1.0,
             "retry_secs": 20.0, "violation_secs": 12.0, "hits_nogood_secs": 3.0,
             "prefer_secs": 2.0, "materialise_secs": 0.5, "setup_secs": 7.0}
    st = self_times(probe)
    assert st["pick"] == 5.0, st["pick"]          # 10 - 4 - 1
    assert st["retry"] == 5.0, st["retry"]        # 20 - 12 - 3
    assert st["free_vars_at"] == 4.0 and st["violation"] == 12.0
    assert st["setup"] == 7.0 and st["prefer"] == 2.0
    # the parts sum to the whole: no time is counted twice and none is lost
    assert abs(sum(st.values()) - (5.0 + 5.0 + 4.0 + 1.0 + 12.0 + 3.0
                                   + 2.0 + 0.5 + 7.0)) < 1e-9

    # a negative self-time is a CHILDREN bug and must refuse, not clamp
    try:
        self_times({"pick_secs": 1.0, "free_vars_at_secs": 5.0})
    except SystemExit as exc:
        assert "negative" in str(exc)
    else:
        raise AssertionError("negative self-time did not refuse")

    # --- search_deltas subtracts the setup snapshot -----------------------
    d = search_deltas({"violation_secs": 30.0, "violation_calls": 900,
                       "setup_secs": 7.0, "nodes": 500,
                       # a FLOAT underscore key, so the `k.startswith("_")`
                       # guard is what excludes it. `_snap` alone proved
                       # nothing: it is a dict, so the isinstance filter
                       # already dropped it and the guard could be deleted
                       # with this test still green.
                       "_t_start": 123.5,
                       "_snap": {"violation_secs": 4.0, "violation_calls": 400,
                                 "nodes": 0}})
    assert d["violation_secs"] == 26.0, d
    assert d["violation_calls"] == 500.0, d
    assert d["setup_secs"] == 7.0, "setup_secs must NOT be a delta"
    assert "_snap" not in d
    assert "_t_start" not in d, "the underscore guard must drop float _ keys"

    # --- Amdahl: the figure §4.2 exists to surface ------------------------
    tot, rem = 930.19, 740.16
    assert abs(ceiling(0.5 * rem, tot) - 1.661) < 0.002, ceiling(0.5 * rem, tot)
    assert abs(ceiling(rem, tot) - 4.89) < 0.01
    assert ceiling(tot, tot) is None               # cannot remove everything
    assert ceiling(1.0, 0.0) is None

    # --- the gate ---------------------------------------------------------
    good = {c: 0.0 for c in COMPONENTS}
    good["violation"] = 100.0
    ok, bad = gate(good, 100.0, [])
    assert ok, bad
    ok, bad = gate(good, 100.0, ["_deg (80.0s cum)"])
    assert not ok and "§4.1(1)" in bad[0], bad
    ok, bad = gate(good, 200.0, [])                # sums to 50% of remainder
    assert not ok and "§4.1(2)" in bad[0], bad
    ok, bad = gate(good, 104.0, [])                # 3.8% off -> inside tolerance
    assert ok, bad
    ok, bad = gate(good, 107.0, [])                # 6.5% off -> outside
    assert not ok, bad
    # EXACTLY on the tolerance, and exact in floats: 5.0 / 100.0 IS the double
    # that `0.05` denotes, so this is the boundary point itself. The gate is
    # inclusive there (`rel > GATE_SUM_TOL`, not `>=`), which this pins: flip
    # the comparison and this assertion fails.
    edge = {c: 0.0 for c in COMPONENTS}
    edge["violation"] = 95.0
    assert abs(100.0 - 95.0) / 100.0 == GATE_SUM_TOL   # the boundary, exactly
    ok, bad = gate(edge, 100.0, [])
    assert ok, bad
    # `hits_nogood` is MEASURED but is NOT a part of the remainder, so the sum
    # must ignore it however large it is. Put it back into the sum and this
    # fails: the parts would be compared against a whole that excludes one.
    excl = {c: 0.0 for c in COMPONENTS}
    excl["violation"] = 100.0
    excl["hits_nogood"] = 500.0
    ok, bad = gate(excl, 100.0, [])
    assert ok, bad
    assert "hits_nogood" not in REMAINDER_COMPONENTS
    assert set(REMAINDER_COMPONENTS) | {"hits_nogood"} == set(COMPONENTS)

    # --- the bar: every row, and row 3 FIRST ------------------------------
    assert verdict("violation", 0.60, 0.10, 3.0)[0] == "OPTIMISE IT"
    assert verdict("violation", 0.60, 0.10, 1.0)[0] == "GENERALITY NOT REACHABLE THIS WAY"
    assert verdict("violation", 0.60, 0.10, 1.5)[0] == "REPORT AND DECIDE"
    assert verdict("violation", 0.10, 0.10, 3.0)[0] == "NO SINGLE LEVER"
    assert verdict("violation", 0.30, 0.10, 3.0)[0] == "REPORT AND DECIDE"
    # row 3 precedence: a setup-dominated residual must NOT reach row 1
    assert verdict("violation", 0.60, 0.55, 3.0)[0] == "DIFFERENT FIX"
    assert verdict("setup", 0.60, 0.60, 3.0)[0] == "DIFFERENT FIX"
    # The `top_name == "setup"` limb ON ITS OWN, with setup_share BELOW
    # TOP_DOMINATES so the first limb cannot be what answers. Both assertions
    # above return via `setup_share >= TOP_DOMINATES`, so deleting this limb
    # left them green -- i.e. "the top component is one-time setup" was
    # untested. `setup` topping a residual it is only 40% of is exactly the
    # case that must not license per-node optimisation.
    v, why = verdict("setup", 0.40, 0.40, 3.0)
    assert v == "DIFFERENT FIX" and "top component is one-time" in why, (v, why)
    # setup_share EXACTLY at TOP_DOMINATES: the threshold is `>=`, so 0.50
    # already dominates. No other case sat on this boundary.
    assert verdict("violation", 0.60, TOP_DOMINATES, 3.0)[0] == "DIFFERENT FIX"
    # boundaries, exact
    assert verdict("violation", 0.50, 0.0, 2.0)[0] == "OPTIMISE IT"
    assert verdict("violation", 0.50, 0.0, 1.2)[0] == "GENERALITY NOT REACHABLE THIS WAY"
    assert verdict("violation", 0.25, 0.0, 3.0)[0] == "REPORT AND DECIDE"
    assert verdict("violation", 0.24, 0.0, 3.0)[0] == "NO SINGLE LEVER"
    # a missing octopus row cannot be read as either scaling verdict
    assert verdict("violation", 0.60, 0.10, None)[0] == "REPORT AND DECIDE"

    # --- the patcher refuses on altered source ---------------------------
    real = ASSIGN_SRC.read_text()
    patch_source(real)                             # must not raise today
    for anchor, _ in PATCHES:
        broken = real.replace(anchor, "", 1)
        try:
            patch_source(broken)
        except SystemExit as exc:
            assert "REFUSING TO MEASURE" in str(exc)
        else:
            raise AssertionError(f"patcher accepted source missing {anchor!r}")
    # And the diff check refuses when a line vanishes for a reason the patch
    # table does not explain. NOTE the input: it must be a line that is NOT one
    # of the anchors. Every anchor removal is LEGITIMATE -- that is what
    # patching them means -- so asserting a refusal on, say, `nodes = budget`
    # would be asserting the opposite of correct behaviour, and would pressure a
    # future reader into making `verify_diff` stricter and breaking the patch.
    assert real.count("    checks = 0\n") == 1
    assert not any("    checks = 0\n" == a for a, _ in PATCHES)
    try:
        verify_diff(real, real.replace("    checks = 0\n", "", 1))
    except SystemExit as exc:
        assert "unexpected" in str(exc)
    else:
        raise AssertionError("verify_diff accepted an unexpected removal")

    # --- the patched source is valid Python ------------------------------
    compile(patch_source(real), "<patched>", "exec")

    # --- anonymous frames resolve to the def that contains them -----------
    own = enclosing_defs("def a():\n"
                         "    def b():\n"
                         "        return any(x for x in ())\n"
                         "    return b\n"
                         "z = [y for y in ()]\n")
    assert own(3) == "b", own(3)      # innermost wins, not the outer `a`
    assert own(2) == "b", own(2)
    assert own(4) == "a", own(4)
    assert own(5) is None, own(5)     # module level has no owner
    # and on the real patched source: `retry`'s genexpr belongs to `_p_retry`,
    # which IS covered -- the one false positive the file filter alone leaves.
    _p = patch_source(ASSIGN_SRC.read_text())
    _own = enclosing_defs(_p)
    _ln = 1 + _p[:_p.index("all(feasible(w) for w in")].count("\n")
    assert _own(_ln) == "_p_retry", (_ln, _own(_ln))
    assert "_p_retry" in COVERED

    # --- `_wrap`'s CALL counter, executed, not just compiled --------------
    # The `calls` dict is what produces every per-node call-rate claim, and
    # `_PROBE["<name>_calls"] += 1` -> `+= 2` survived a compile-only test.
    # Run the wrapper on a stand-in and count. Deterministic: no timing.
    import collections as _c
    _ns = {"_perf": time.perf_counter, "_PROBE": _c.defaultdict(float)}
    exec("def outer():\n" + _wrap("probe_fn", "", "")
         + "        return 7\n"
         + "    return probe_fn(), probe_fn()\n", _ns)
    assert _ns["outer"]() == (7, 7), "the wrapper must return the original's value"
    assert _ns["_PROBE"]["probe_fn_calls"] == 2, _ns["_PROBE"]["probe_fn_calls"]
    assert _ns["_PROBE"]["probe_fn_secs"] >= 0.0

    # --- the remainder's DEFINITION, on exact floats ----------------------
    # `total - global_check - hits_nogood` is the definitional anchor of the
    # whole measurement, and dropping the `- hits_nogood` term used to leave this
    # self-test green. 100 - 20 - 5 is exact in binary floats, so `==` is safe.
    assert remainder_of(100.0, 20.0, 5.0) == 75.0, remainder_of(100.0, 20.0, 5.0)
    assert remainder_of(8.0, 2.0, 0.0) == 6.0      # and the term is not ignored
    assert remainder_of(8.0, 2.0, 1.0) == 5.0

    # --- the top component is the top OF THE REMAINDER --------------------
    # `hits_nogood` is deliberately the largest entry: it is not part of the
    # remainder, so it can never be the top component of it. `max` over
    # COMPONENTS instead of REMAINDER_COMPONENTS would return it.
    _tc = {c: 0.0 for c in COMPONENTS}
    _tc["hits_nogood"], _tc["violation"], _tc["pick"] = 500.0, 3.0, 2.0
    assert top_component(_tc) == "violation", top_component(_tc)

    # --- §4.1(1)'s classifier, on SYNTHETIC pstats lines -------------------
    # The `own != "assign"` carve-out is the ONE place this check can still fire
    # (see SWEEP_SCOPE) and was the previous wave's one deviation from its brief.
    # Removing it masks a hot generator sitting in `assign`'s own DFS loop, which
    # no accumulator measures -- so it is asserted in both directions here, with
    # no 130-second run. Line 10 is owned by `assign`, line 20 by `_p_retry`.
    _hdr = "   ncalls  tottime  percall  cumtime  percall filename:lineno(function)"

    def _prow(cum, lineno, name):
        return (f"        1    0.000    0.000  {cum:8.3f}    0.000 "
                f"/tmp/_assign_profiled.py:{lineno}({name})")

    _owner = {10: "assign", 20: "_p_retry"}.get
    _lines = [_hdr, _prow(100.0, 529, "assign"),
              _prow(50.0, 10, "<genexpr>"),     # in assign's loop -> REPORTED
              _prow(50.0, 20, "<genexpr>"),     # inside _p_retry  -> not a gap
              _prow(4.0, 10, "<genexpr>")]      # 4% of assign     -> below the bar
    _unc = select_uncovered("\n".join(_lines), "_assign_profiled.py",
                            _owner, "<synthetic>")
    assert _unc == ["_assign_profiled.py:10(<genexpr>) inside assign (50.0s cum)"], _unc
    # and the missing-`assign` refusal, previously reachable only via a real run
    try:
        select_uncovered("\n".join([_hdr, _prow(50.0, 10, "<genexpr>")]),
                         "_assign_profiled.py", _owner, "<synthetic>")
    except SystemExit as exc:
        assert "REFUSING TO GATE" in str(exc)
    else:
        raise AssertionError("select_uncovered accepted a listing with no assign row")

    # --- main()'s WIRING, with run_subject MONKEYPATCHED ------------------
    # `gate()`, the top selection and `verdict()` are each self-tested above as
    # functions; what was untested is that `main` CALLS them. Replacing its
    # `gate()` call with `g_ok, g_bad = True, []`, reverting `top_component` to a
    # `max` over COMPONENTS, or deleting the `verdict()` call all left this
    # self-test green. Synthetic rows, so this costs no compile: `run_subject`
    # and `build_instrumented` are both swapped out, and stdout is captured.
    def _synth_row(subject, comps, rem, per_node):
        return {"subject": subject, "outcome": "ok", "N": 7, "nodes": 1000,
                "budget": BUDGET, "total_secs": 100.0, "global_check_secs": 0.0,
                "remainder_secs": round(rem, 2), "remainder_secs_exact": rem,
                "components": dict(comps),
                "calls": {c: 1 for c in COMPONENTS},
                "share_of_remainder": {
                    c: (round(comps[c] / rem, 4)
                        if (rem > 0 and c in REMAINDER_COMPONENTS) else None)
                    for c in COMPONENTS},
                "whole_run_ceiling": {c: ceiling(comps[c], 100.0)
                                      for c in COMPONENTS},
                "per_node_ms": per_node}

    def _synth_factory(off):
        def _rs(subject, mod):
            comps = {c: 0.0 for c in COMPONENTS}
            comps["violation"], comps["pick"], comps["setup"] = 60.0, 20.0, 10.0
            # the largest entry in the dict, deliberately, and NOT part of the
            # remainder: a `max` over COMPONENTS would make it the top component
            comps["hits_nogood"] = 500.0
            # REMAINDER_COMPONENTS sum to exactly 90.0; `off` moves the stated
            # remainder away from that so the sum-check can be driven either way
            return _synth_row(subject, comps, 90.0 * (1.0 + off),
                              3.0 if subject == "octopus" else 1.0)
        return _rs

    _mainjson = pathlib.Path(os.environ.get("TMPDIR", "/tmp")) / "_profile_st_main.json"
    _real_rs, _real_bi = run_subject, build_instrumented
    _g = globals()
    for _off, _want_row, _want_gate in ((0.0, "OPTIMISE IT", True),
                                        (1.0, "SUPPRESSED", False)):
        try:
            _g["run_subject"] = _synth_factory(_off)
            _g["build_instrumented"] = lambda: None
            with contextlib.redirect_stdout(io.StringIO()) as _cap:
                main(str(_mainjson))
        finally:
            _g["run_subject"], _g["build_instrumented"] = _real_rs, _real_bi
        _rec = json.loads(_mainjson.read_text())
        _r0 = _rec["rows"][0]
        assert _r0["sum_check_passed"] is _want_gate, (_off, _r0)
        assert bool(_r0["gate_failures"]) is (not _want_gate), (_off, _r0)
        # the key is `sum_check_passed`, never `gate_passed`: one limb of §4.1
        assert "gate_passed" not in _r0, _r0
        assert _r0["top_component"] == "violation", _r0["top_component"]
        # §5.3: a verdict on EVERY path, and GATE FAILED when the gate fails
        assert "verdict" in _rec and _rec["verdict"], _rec.get("verdict")
        assert _rec["verdict"].startswith(
            "GATE FAILED" if not _want_gate else "NO ROW CLAIMED"), _rec["verdict"]
        _prov = _rec["provisional_row_pending_4_1_1"]
        assert _prov["row"] == _want_row, (_off, _prov)
        if _want_gate:
            # and it is `verdict()`'s own answer, not a hand-rolled duplicate
            assert _prov["row"] == verdict("violation", _r0["share_of_remainder"]
                                          ["violation"],
                                          _r0["share_of_remainder"]["setup"],
                                          _rec["scaling"])[0], _prov
            assert _rec["scaling"] == 3.0, _rec["scaling"]
            assert "PROVISIONAL" in _prov["scope"]
        assert "top=violation" in _cap.getvalue(), _cap.getvalue()[:400]
    _mainjson.unlink(missing_ok=True)

    # --- AND THE INSTRUMENT ACTUALLY RUNS --------------------------------
    # Everything above is arithmetic on synthetic dicts plus `compile()`. That
    # left real mutants alive: deleting the `_PROBE["nodes"] += 1` patch
    # entirely, and flipping the sign of the inline `now_open` accumulator,
    # both kept this self-test green -- while `nodes` is the denominator of
    # `per_node_ms` and hence of the `scaling` reading that drives two of the
    # four verdict rows. So: build the instrumented module and run the smallest
    # subject. `starfish` is N=4 with 54 candidates (~0.1 s sparse, a fraction
    # of a second dense) and is NOT representative of anything -- this is
    # evidence the harness runs, not a result.
    #
    # NO EXACT SECONDS ARE ASSERTED: they are timing-dependent and would make
    # this flaky. `nodes > 0` rather than `nodes == 6806` for the same reason --
    # the count is deterministic in principle, but it is not pinned here.
    #
    # The three `_FakeMod` probes further down exercise `run_subject`'s two
    # refusal branches, and they need the same subject compiled. `compile_tree`
    # is memoised for the rest of this function so they cost ~0 s instead of
    # 0.22 s each: the REAL measurement below is the cache-filling call, so its
    # `sparse_secs` is untouched. Restored in the `finally`.
    import box_pleat.compile as _bpc
    _real_compile, _ccache = _bpc.compile_tree, {}

    def _cached_compile(requested, pairs):
        key = repr((requested, pairs))
        if key not in _ccache:
            _ccache[key] = _real_compile(requested, pairs)
        return _ccache[key]

    _bpc.compile_tree = _cached_compile
    try:
        _live_checks(build_instrumented())
    finally:
        _bpc.compile_tree = _real_compile


def _live_checks(mod):
    """The part of `--selftest` that actually runs the instrument.

    Split out only so `_selftest`'s `compile_tree` memoisation has a `finally`
    that cannot be skipped. Returns nothing; every check is an assertion.
    """
    row = run_subject("starfish", mod)
    assert row.get("outcome") == "ok", row
    assert row["nodes"] > 0, ("nodes is 0: the node-counter patch did not take "
                              "effect, and it is the denominator of every "
                              "per-node figure")
    for c, v in row["components"].items():
        assert v >= 0.0, (c, v)
    assert row["components"]["now_open"] >= 0.0
    assert row["per_node_ms"] is not None and row["per_node_ms"] > 0
    # `now_open` is a single statement executed exactly once per `pick()` call,
    # so the two counters must agree exactly -- this catches a doubled or
    # dropped increment on either of those two patches.
    assert row["calls"]["now_open"] == row["calls"]["pick"], row["calls"]
    # One node is counted per main-loop iteration, before `pick()` is called;
    # the loop can exit after counting a node and before picking (budget), so
    # `nodes` is `pick` calls or one more. Kills a doubled node counter.
    assert row["calls"]["pick"] <= row["nodes"] <= row["calls"]["pick"] + 1, row
    # `setup` is a DURATION between two patch points, not a wrapped function,
    # so nothing increments a call counter for it. 0 is correct, not a bug.
    assert row["calls"]["setup"] == 0, row["calls"]
    assert row["calls"]["violation"] > 0, row["calls"]
    # `hits_nogood` gets NO share of the remainder, because the remainder's own
    # definition subtracts it out; every other component gets one. Dropping
    # `share_of_remainder`'s `c in REMAINDER_COMPONENTS` filter would hand it a
    # share of a quantity that excludes it, and left this self-test green.
    assert row["share_of_remainder"]["hits_nogood"] is None, row["share_of_remainder"]
    assert all(row["share_of_remainder"][c] is not None
               for c in REMAINDER_COMPONENTS), row["share_of_remainder"]
    # ... while `whole_run_ceiling` IS a share of `total`, which includes it, so
    # that dict must have an entry for every component.
    assert set(row["whole_run_ceiling"]) == set(COMPONENTS)
    # GATED ON THE UNROUNDED REMAINDER, and that is the point of the key. Against
    # `remainder_secs` (2 dp) a ~0.30 s `starfish` remainder carries a +-1.67%
    # rounding quantum into a 5% tolerance, on top of a genuine ~0.3-1%
    # unmeasured-loop gap -- so this assertion used to be timing-dependent inside
    # a gate that has to be deterministic. The TOLERANCE is untouched: loosening
    # a gate to let a test through is a distinct failure mode.
    assert row["remainder_secs_exact"] > 0, row
    assert abs(row["remainder_secs_exact"] - row["remainder_secs"]) <= 0.005 + 1e-9
    g_ok, g_bad = gate(row["components"], row["remainder_secs_exact"], [])
    _off = 100 * abs(sum(row["components"][c] for c in REMAINDER_COMPONENTS)
                     - row["remainder_secs_exact"]) / row["remainder_secs_exact"]
    assert g_ok, g_bad

    # --- run_subject's two refusal branches, on a stand-in module ----------
    # `compile_tree` is memoised by the caller, so each of these is a real sparse
    # compile off the cache plus a fake `assign`.
    import collections as _cc

    class _FakeMod:
        """A stand-in for the patched module: real layout, scripted `assign`."""

        def __init__(self, mode):
            self._PROBE, self._mode = _cc.defaultdict(float), mode

        def assign(self, *a, **k):
            if self._mode == "raise":
                raise RuntimeError("synthetic engine failure")
            if self._mode == "hitsnogood":
                # A CONTROLLED `hits_nogood`, large enough that the remainder's
                # definition is visible in the sign of the answer: the fake
                # `assign` returns in microseconds, so `total - 0 - 0.25` is
                # NEGATIVE and `total - 0` is positive. Testing the call site,
                # not just `remainder_of`: inlining it back as
                # `total - gc_secs[0]` left every other assertion green, because
                # a real `starfish`'s `hits_nogood` is small enough to keep the
                # §4.1(2) sum-check inside tolerance either way.
                self._PROBE["_snap"] = {}
                self._PROBE["retry_secs"] = 0.50
                self._PROBE["hits_nogood_secs"] = 0.25
                self._PROBE["nodes"] = 10.0
                return ("ok", None)
            if self._mode == "negative":
                # past the setup/search boundary, but with a child charged more
                # than its parent -- `self_times` must REFUSE, not be filed as
                # one subject's bad luck
                self._PROBE["_snap"] = {}
                self._PROBE["pick_secs"] = 1.0
                self._PROBE["free_vars_at_secs"] = 5.0
                return ("ok", None)
            # returned before `nodes = budget`, so no `_snap` and no split
            self._PROBE["violation_secs"] = 0.5
            return ("stopped", "unbound_variable")

    # (1) no setup/search boundary -> NOT "ok". Neutering the `"_snap" not in
    # raw` guard stamps this row "ok" with `setup_secs` 0.0 and the setup loop's
    # `violation` cost misattributed to a search that never ran.
    _r = run_subject("starfish", _FakeMod("nosnap"))
    assert _r["outcome"].startswith("assign returned before the setup/search "
                                    "boundary"), _r
    assert "components" not in _r and "per_node_ms" not in _r, _r

    # (1b) the remainder's DEFINITION at the call site, and the exact key's
    # unroundedness -- both deterministic, both driven by a controlled probe
    # rather than by `starfish`'s real (small, timing-dependent) `hits_nogood`.
    _r = run_subject("starfish", _FakeMod("hitsnogood"))
    assert _r["outcome"] == "ok", _r
    assert _r["components"]["hits_nogood"] == 0.25, _r["components"]
    assert _r["components"]["retry"] == 0.25, _r["components"]     # 0.50 - 0.25
    # `total` is microseconds, so dropping `- hits_nogood` flips the sign
    assert _r["remainder_secs_exact"] < -0.2499, _r["remainder_secs_exact"]
    assert _r["share_of_remainder"]["violation"] is None, _r       # remainder <= 0
    # and `remainder_secs_exact` is the UNROUNDED value: the 2-dp display reads
    # exactly -0.25 while the exact one is strictly greater (total > 0).
    assert _r["remainder_secs"] == -0.25, _r["remainder_secs"]
    assert _r["remainder_secs_exact"] > -0.25, _r["remainder_secs_exact"]

    # (2) an engine exception is one subject's outcome, not the end of the ladder
    _r = run_subject("starfish", _FakeMod("raise"))
    assert _r["outcome"].startswith("raised RuntimeError"), _r
    assert "synthetic engine failure" in _r["outcome"], _r
    assert _r.get("error_type") == "RuntimeError", _r

    # (3) ... but `self_times`' SystemExit is a SOUNDNESS refusal and must still
    # escape. It does because `SystemExit` derives from `BaseException`, not
    # `Exception`; widening that clause to `BaseException` turns this red.
    try:
        run_subject("starfish", _FakeMod("negative"))
    except SystemExit as exc:
        assert "REFUSING TO REPORT" in str(exc) and "negative" in str(exc), exc
    else:
        raise AssertionError("self_times' SystemExit refusal did not escape "
                             "run_subject -- an `except Exception` widened to "
                             "BaseException would swallow a soundness refusal")

    print(f"selftest OK: self-time (6 + refusal), search_deltas (incl. the "
          f"underscore guard), Amdahl (4), remainder_of (3), top_component (1), "
          f"gate (8 incl. the exact 5% boundary "
          f"and hits_nogood's exclusion), bar (15 incl. row-3 precedence, the "
          f"setup-top limb alone, and 5 exact boundaries), enclosing_defs (5), "
          f"select_uncovered (2: assign-owned genexpr reported, _p_retry-owned "
          f"not, + the missing-assign refusal), main()'s wiring on synthetic "
          f"rows (2 arms: OPTIMISE IT / GATE FAILED-SUPPRESSED), "
          f"wrapper call count "
          f"executed, patcher refusal ({len(PATCHES)} anchors + diff), "
          f"run_subject's 3 branches (no-boundary, engine exception, "
          f"SystemExit escapes), patched "
          f"source compiles AND RUNS: starfish nodes={row['nodes']} "
          f"components sum {_off:.2f}% off its remainder "
          f"(tolerance {100 * GATE_SUM_TOL:.0f}%, on the UNROUNDED remainder)")


def main(out):
    mod = build_instrumented()
    rec = {
        "measured_utc": datetime.datetime.now(datetime.UTC).isoformat(
            timespec="seconds"),
        "commit": _commit(),
        "budget": BUDGET,
        "cap_secs": CAP_SECS,
        "components": list(COMPONENTS),
        "children": {k: list(v) for k, v in CHILDREN.items()},
        "thresholds": {"top_dominates": TOP_DOMINATES,
                       "no_lever_below": NO_LEVER_BELOW,
                       "scales": SCALES, "flat_at_or_below": FLAT_AT_OR_BELOW,
                       "gate_sum_tol": GATE_SUM_TOL},
        "rows": [],
    }

    def flush():
        with open(out, "w") as fh:
            json.dump(rec, fh, indent=1)

    flush()
    for s in SUBJECTS:
        row = run_subject(s, mod)
        rec["rows"].append(row)
        flush()
        if row.get("outcome") != "ok":
            print(f"{s}: {row.get('outcome')}", flush=True)
            continue

        # §4.1's completeness gate, evaluated PER ROW and RECORDED. It used to
        # exist, be self-tested, and be called by nothing -- while Task 2's
        # verification snippet re-did the sum by hand. Only the sum-check limb
        # can be evaluated here; §4.1(1) needs the separate --cprofile sweep, so
        # `cprofile_uncovered` is `[]` and the scope is stated in the row, in
        # the print, and in the artifact. A run must never look like it passed a
        # gate it only half-evaluated.
        # Gated on the UNROUNDED remainder (spec §4.1(2) is an arithmetic
        # identity, and 2-dp display rounding is a +-1.67% quantum on a
        # sub-second subject against a 5% tolerance). `remainder_secs` stays
        # rounded in the artifact; the assertion reads the exact value. The
        # tolerance itself is untouched -- loosening a gate to let a reading
        # through is this project's named recurring failure mode.
        g_ok, g_bad = gate(row["components"], row["remainder_secs_exact"], [])
        row["sum_check_passed"] = g_ok
        row["gate_failures"] = g_bad
        row["gate_scope"] = (
            "§4.1(2) sum-check ONLY (components summed over "
            "REMAINDER_COMPONENTS, i.e. excluding hits_nogood, which the "
            "remainder's own definition subtracts out; evaluated against "
            "remainder_secs_exact, not the 2-dp remainder_secs). §4.1(1) "
            "completeness is NOT evaluated by this run: it needs the "
            "--cprofile sweep, and even there its named-function limb is "
            "structural rather than measured -- see SWEEP_SCOPE. The key is "
            "named sum_check_passed and NOT gate_passed for exactly that "
            "reason: it is one limb of §4.1, never §4.1 itself.")

        # The top component OF THE REMAINDER. Selected by `top_component`, which
        # maximises over REMAINDER_COMPONENTS, never COMPONENTS: a component the
        # remainder's own definition subtracts out can never be the top
        # component of it. Recorded, not only printed, so Task 3's README reads
        # it rather than re-deriving it.
        top = top_component(row["components"])
        row["top_component"] = top
        share = row["share_of_remainder"][top]
        share_txt = ("n/a (remainder <= 0)" if share is None
                     else f"{100 * share:.1f}% of rem")
        print(f"{s}: N={row['N']} nodes={row['nodes']} "
              f"total={row['total_secs']}s rem={row['remainder_secs']}s "
              f"per_node={row['per_node_ms']}ms top={top} "
              f"({share_txt}, ceiling {row['whole_run_ceiling'][top]}x)",
              flush=True)
        if not g_ok:
            print(f"  ** GATE FAILED (§4.1(2) sum-check limb only; §4.1(1) "
                  f"needs the --cprofile sweep) **", flush=True)
            for b in g_bad:
                print(f"     {b}", flush=True)
        flush()

    liz = next((r for r in rec["rows"]
                if r["subject"] == "lizard" and r.get("outcome") == "ok"), None)
    oct_ = next((r for r in rec["rows"]
                 if r["subject"] == "octopus" and r.get("outcome") == "ok"), None)
    print()
    if liz is None:
        rec["verdict"] = "NO VERDICT: lizard produced no row"
        flush()
        print("NO VERDICT: lizard produced no row, so §4.3 cannot be evaluated.")
        return

    # The §4.1 gate needs the cProfile sweep, which is a separate invocation
    # (--cprofile). Record what this run can and refuse the row without it.
    # Both per-node readings must be present AND positive. An `ok` row whose
    # `per_node_ms` is None (nodes == 0) would otherwise TypeError here, after
    # every subject has already run -- losing the whole summary at the end of a
    # 40-minute ladder.
    liz_pn, oct_pn = liz.get("per_node_ms"), oct_.get("per_node_ms") if oct_ else None
    rec["scaling"] = (round(oct_pn / liz_pn, 3)
                      if (liz_pn and oct_pn is not None) else None)
    flush()
    print(f"lizard per-node {liz_pn} ms; "
          f"octopus {oct_pn if oct_ else 'no row'} ms; "
          f"scaling {rec['scaling']}")
    failed = [r["subject"] for r in rec["rows"]
              if r.get("outcome") == "ok" and not r.get("sum_check_passed")]
    print(f"§4.1(2) sum-check: {'FAILED on ' + ', '.join(failed) if failed else 'passed on every ok row'}"
          f" -- this is the sum limb ONLY; §4.1(1) needs the --cprofile sweep.")

    # §5.3: "A failed completeness gate (§4.1) sets the verdict to `GATE FAILED`
    # and suppresses every row, in either direction." That sentence had no
    # implementation: `rec["verdict"]` was set ONLY in the `liz is None` branch,
    # so `profile.json` carried no `verdict` key on either normal path. It is now
    # set on every path this function can take.
    if failed:
        rec["verdict"] = ("GATE FAILED: §4.1(2) sum-check failed on "
                          + ", ".join(failed))
        rec["provisional_row_pending_4_1_1"] = {
            "row": "SUPPRESSED",
            "why": "§5.3 suppresses every row, in either direction, when the "
                   "completeness gate fails; the sum-check failed on "
                   + ", ".join(failed),
            "scope": "no row may be claimed from this run"}
        flush()
        print("GATE FAILED: no row may be claimed in either direction (§5.3).")
        return

    # §4.3's row, APPLIED BY THE SELF-TESTED FUNCTION rather than by hand in the
    # README. `verdict()` used to be self-tested with fifteen assertions and
    # called by nothing, while the README was briefed to apply the same table by
    # hand off `scaling` / TOP_DOMINATES / NO_LEVER_BELOW / SCALES /
    # FLAT_AT_OR_BELOW -- a hand-rolled duplicate of self-tested logic, which is
    # how a wrong row gets published. This is the same defect FIX 2 closed for
    # `gate()`, one function along.
    #
    # THE KEY'S NAME SAYS IT IS NOT FINAL, because it is not: §4.1(1) is not
    # evaluated by this invocation at all, and §4.1 forbids claiming a row until
    # both its limbs hold. A reader who takes this as the verdict has skipped the
    # sweep; a reader who re-derives the row by hand has duplicated it. Neither
    # is what the README should do: it must report THIS key, having first
    # recorded the sweep's outcome.
    liz_top = top_component(liz["components"])
    liz_top_share = liz["share_of_remainder"][liz_top]
    liz_setup_share = liz["share_of_remainder"]["setup"]
    if liz_top_share is None or liz_setup_share is None:
        rec["provisional_row_pending_4_1_1"] = {
            "row": "NO ROW", "subject": "lizard", "top_component": liz_top,
            "why": "lizard's remainder is not positive, so no share is defined",
            "scope": "§4.1(1) has NOT been evaluated by this invocation"}
    else:
        v, why = verdict(liz_top, liz_top_share, liz_setup_share,
                         rec["scaling"])
        rec["provisional_row_pending_4_1_1"] = {
            "row": v, "why": why, "subject": "lizard",
            "top_component": liz_top,
            "top_share_of_remainder": liz_top_share,
            "setup_share_of_remainder": liz_setup_share,
            "scaling": rec["scaling"],
            "scope": ("PROVISIONAL. This is verdict() applied to lizard's row "
                      "under §4.3, computed by the self-tested function and NOT "
                      "to be re-derived by hand. It is NOT the final row: "
                      "§4.1(1)'s completeness limb is not evaluated by this "
                      "invocation (it needs --cprofile, where its named-function "
                      "part is structural rather than measured -- see "
                      "SWEEP_SCOPE). §4.1 forbids claiming a row until both "
                      "limbs hold.")}
    rec["verdict"] = ("NO ROW CLAIMED: §4.1(2) passed on every ok row; "
                      "§4.1(1) needs the --cprofile sweep. See "
                      "provisional_row_pending_4_1_1.")
    flush()
    print(f"provisional §4.3 row (pending §4.1(1)): "
          f"{rec['provisional_row_pending_4_1_1']['row']} -- "
          f"{rec['provisional_row_pending_4_1_1']['why']}")
    print("NO ROW CLAIMED YET: §4.1's completeness gate needs the --cprofile "
          "sweep. Run it, then report the row from "
          "`provisional_row_pending_4_1_1` -- do not re-derive it by hand.")


_USAGE = """usage (run from mcp_harness, with PYTHONPATH=.):
  profile.py --selftest
  profile.py <out.json>
  profile.py --cprofile <out.txt>
See this module's docstring for the full commands."""


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    elif "--cprofile" in sys.argv:
        i = sys.argv.index("--cprofile") + 1
        if i >= len(sys.argv):
            raise SystemExit("--cprofile needs an output path.\n" + _USAGE)
        mod = build_instrumented()
        unc, text, row = cprofile_sweep(mod, sys.argv[i])
        # THE WORDING CARRIES THE SCOPE, the way each row's `gate_scope` does for
        # §4.1(2). "all hot functions covered" read as a measurement; it is not
        # one, and saying so here is the difference between reporting §4.1(1) as
        # satisfied structurally and reporting it as swept.
        print("UNCOVERED ANONYMOUS FRAMES (§4.1(1)):" if unc
              else "NO uncovered frame found -- but read the scope below "
                   "before reporting this as measured completeness")
        for u in unc:
            print(f"  {u}")
        print()
        print(textwrap.fill(SWEEP_SCOPE, 78))
        # Also written INTO the artifact, so the listing cannot be read later
        # without the scope that qualifies it.
        pathlib.Path(sys.argv[i]).write_text(
            textwrap.fill(SWEEP_SCOPE, 78, initial_indent="# ",
                          subsequent_indent="# ") + "\n"
            + textwrap.fill(
                "§4.1(1) OUTCOME: "
                + ("; ".join(unc) if unc else "no uncovered frame found"),
                78, initial_indent="# ", subsequent_indent="# ") + "\n#\n"
            + text)
        # The sweep computes a full dense `lizard` row on the way. Print its
        # headline rather than discard it -- the same run, read twice, costs
        # nothing extra. It is NOT a substitute for the plain JSON run's row:
        # these seconds are profiler-distorted (spec §6), so they are labelled.
        if row and row.get("outcome") == "ok":
            print(f"  [PROFILER-DISTORTED, not a timing result] lizard "
                  f"N={row['N']} nodes={row['nodes']} "
                  f"total={row['total_secs']}s rem={row['remainder_secs']}s")
        elif row:
            print(f"  [sweep's lizard row] outcome: {row.get('outcome')}")
    elif len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        raise SystemExit("no output path given.\n" + _USAGE)
```

- [ ] **Step 4: Run the self-test to verify it passes**

Run, from `mcp_harness`:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py --selftest
```

Expected: a `selftest OK: ...` line naming the self-time, `search_deltas`, Amdahl, `remainder_of`, `top_component`, gate, bar, `enclosing_defs`, `select_uncovered`, `main()`-wiring, wrapper-call-count, patcher and `run_subject`-branch groups **and a live `starfish` reading** (`nodes=...`, components sum `...% off its remainder`, on the UNROUNDED remainder), exit 0, in under 5 seconds (**measured 0.66-0.68 s over three runs, against 0.64-0.70 s for the version before the second fix wave: the three `_FakeMod` probes and both `main()` arms are paid for by memoising `compile_tree` for the duration of the live checks**).

**No `-P` flag.** All three commands in the module docstring run exactly as printed. `cProfile` and `pstats` are imported inside `cprofile_sweep`, with this file's own directory dropped from `sys.path` for the duration — both halves are needed, because the file is required to be named `profile.py` and stdlib `cProfile` does `import profile` internally.

If it fails on the patcher block, an anchor no longer matches production — **do not edit the assertion**; re-derive the anchor against today's `box_pleat/assign.py` and record the change in your report.

- [ ] **Step 5: Verify the patched module actually imports and runs**

**Step 4 now covers this**: `--selftest` builds the instrumented module, runs `starfish`, and asserts `nodes > 0`, every component `>= 0`, `calls["now_open"] == calls["pick"]`, `calls["pick"] <= nodes <= calls["pick"] + 1`, and the §4.1(2) sum-check — because a compile-only self-test left real mutants alive (deleting the `_PROBE["nodes"] += 1` patch, and flipping the sign of the inline `now_open` accumulator, both kept it green). Run the snippet below only if you want the numbers printed rather than asserted (it uses `starfish`, the smallest subject, ~0.1 s sparse):

```bash
PYTHONPATH=. ../.venv/bin/python3 -c "
import sys; sys.argv = ['profile.py']
import importlib.util
s = importlib.util.spec_from_file_location('prof', '../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
mod = m.build_instrumented()
row = m.run_subject('starfish', mod)
print('outcome:', row.get('outcome'))
print('nodes:', row.get('nodes'), '| components:', row.get('components'))
print('remainder sum:', round(sum(row['components'][c] for c in m.REMAINDER_COMPONENTS), 4),
      'vs remainder', row.get('remainder_secs'))
"
```

Expected: `outcome: ok`, a non-zero `nodes` count, and a components dict with non-zero entries. **If `nodes` is 0 the node counter patch did not take effect** — that is a hard failure, since it is the denominator of every per-node figure.

**Sum over `REMAINDER_COMPONENTS`, not over `components`.** `hits_nogood` is measured, but the remainder is *defined* as `total − global_check − hits_nogood`, so adding it back in compares the parts against a whole that omits one of them. On the committed smoke row that error alone reads **1.54% off** where the correct sum reads **0.71%** — a third of the 5% tolerance spent before any real error.

Measured on this plan's own code, 2026-09-29, as a smoke check only:
`nodes 6806`, components (excluding `hits_nogood`) summing to 0.2780 s against a
0.28 s remainder (**0.71% off**, inside §4.1(2)'s 5%), `violation` the largest at
0.1428 s, `free_vars_at` called 28.6x per node and `violation` 4.5x per node.
**`starfish` is N=4 with 54 candidates and is not representative of anything** —
this is evidence the harness runs, not a result. Task 2 owns the real ladder.
Note that on a remainder this small the 2-decimal rounding is a **±1.8%**
quantum, so repeated runs read anywhere in 0.1–2.9% off in either direction; on
the real subjects (tens to hundreds of seconds) that rounding is negligible.

Note `calls["setup"]` is `0` and that is correct, not a bug: `setup` is a
**duration** taken between two patch points, not a wrapped function, so nothing
increments a call counter for it.

- [ ] **Step 6: Verify the self-test is not vacuous — break the self-time arithmetic**

Temporarily change `self_times`'s `total -= float(probe.get(f"{child}_secs", 0.0))` to `total += float(...)`. Re-run Step 4 and confirm it FAILS on the `st["pick"] == 5.0` assertion. Then restore and re-run Step 4 to confirm it passes.

Keep a pristine copy outside the repo and confirm restoration by `shasum` or `diff`, not by eye — self-time is the spec's §3.2 contract and a silently broken version would inflate every parent's share.

- [ ] **Step 7: Confirm nothing under `mcp_harness/` changed**

```bash
git status --porcelain mcp_harness/
grep -c box_pleat mcp_harness/server.py
```

Expected: the first prints nothing; the second prints `0`.

- [ ] **Step 8: Commit**

```bash
git add ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py
git commit -m "evidence: the local-CSP profile harness, with its bar self-tested

Spec 2026-09-29-local-csp-profile-design.md. Read-only: production assign.py is
read as TEXT and patched into a temp module, never written.

Eleven anchors, each verified to occur exactly once, patched by RENAME-AND-WRAP
so every patch is a one-line anchor and cannot go stale against an edit inside a
function it does not read. A setup-boundary snapshot makes every per-search
figure a DELTA, so violation's setup calls are not charged to the search, and a
real node counter replaces the hits_nogood_calls proxy the 1.48 ms/node figure
was built on.

Self-time is enforced, not hoped for: a negative self-time REFUSES rather than
clamping, because it means CHILDREN misdescribes the call graph and every share
below it is wrong. --selftest covers the arithmetic, search_deltas, Amdahl's
1.66x, the completeness gate in both directions, all four bar rows plus row-3
precedence and four exact boundaries, and the patcher's refusal on source with
each anchor removed in turn.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Run the ladder and the completeness sweep

**Files:**
- Create: `docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.json` (generated)
- Create: `docs/superpowers/evidence/2026-09-29-local-csp-profile/cprofile-lizard.txt` (generated)

**Interfaces:**
- Consumes: `profile.py` from Task 1.
- Produces: both artifacts. Task 3 reads them.

**Context you need:** eight sparse compiles plus eight dense `assign()` runs at a 20,000-node budget, each capped at 1800 s. `lizard` sparse is ~6.5 s, `guinea_pig` ~274 s, `dog` ~537 s. Budget up to ~40 minutes overall. Run it in the background and check back at intervals rather than polling tightly. **Do not edit `profile.py`** — if you believe it has a defect, STOP and report BLOCKED. An instrument edited during or after its run is one whose results cannot be trusted, and a reviewer will check its blob hash.

- [ ] **Step 1: Re-run the self-test**

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py --selftest
```

Expected: `selftest OK: ...`, exit 0. Do not proceed unless this passes.

- [ ] **Step 2: Record the instrument's blob hash before the run**

```bash
git hash-object ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py
```

Paste the hash in your report. Task 3 and the reviewer will compare against it.

- [ ] **Step 3: Run the ladder**

In the background, from `mcp_harness`:

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.json
```

Expected: one line per subject with `N`, nodes, total, remainder, per-node ms, and the top component with its share and ceiling; then the lizard/octopus scaling line and an explicit statement that no row is claimed until the sweep runs.

- [ ] **Step 4: Run the completeness sweep**

```bash
PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py --cprofile ../docs/superpowers/evidence/2026-09-29-local-csp-profile/cprofile-lizard.txt
```

Expected: either `all hot functions covered`, or a list of uncovered hot functions, each as `_assign_profiled.py:<lineno>(<name>)` with its cumulative seconds — plus a headline for the dense `lizard` row the sweep computes on the way, labelled **profiler-distorted** so it is never read as a timing result. **Either outcome is a result.** If functions are uncovered, §4.1(1) fails and Task 3 reports `GATE FAILED` rather than a row — do NOT add names to `COVERED` to make the gate pass.

What the sweep asks, precisely: *is there a hot function inside `assign` that no accumulator covers?* So the denominator is **`assign`'s own cumulative time** (not the first line of the listing, which is the whole run including the sparse compile and the `global_check` spy — against that, a function at 6% of `assign` reads under the 5% threshold and is missed), and candidates are restricted to functions **resident in the instrumented module's file** (which excludes `compile_tree`, `spy`, `to_fold`, `flat_fold`, `propagate`, `piece_keys`, `constraint_graph`, `run_subject` and `once` structurally, without naming them — `once` in particular has `cum == total`, so an unfiltered check reports its own top frame every time). A missing `assign` entry **raises**; a denominator that silently defaults is a gate that silently passes. An anonymous frame (`<genexpr>`, `<lambda>`) is judged by the `def` that lexically contains it, with `assign` itself deliberately excepted — it is in `COVERED` as the denominator, not because any accumulator measures its main loop.

- [ ] **Step 5: Check the run agrees with itself**

**The run itself now evaluates the §4.1(2) sum-check per row** and records `sum_check_passed`, `gate_failures`, `gate_scope` and `top_component` in each `ok` row, plus a top-level `verdict` and `provisional_row_pending_4_1_1` (§4.3's row as `verdict()` itself computes it), so this step READS those rather than re-deriving anything by hand. A hand-rolled duplicate is how the double-counting bug below got into two places at once.

**The key is `sum_check_passed`, not `gate_passed`.** It was renamed because `gate_passed` reads as "§4.1 passed" and only the `gate_scope` string prevented that; the name now says which limb it is. The sum-check is evaluated against `remainder_secs_exact` (unrounded), not the 2-dp `remainder_secs`, so the gate is deterministic rather than sensitive to display rounding — the tolerance itself is unchanged at 5%.

```bash
../.venv/bin/python3 -c "
import json
P = '../docs/superpowers/evidence/2026-09-29-local-csp-profile/'
d = json.load(open(P + 'profile.json'))
# hits_nogood is MEASURED but is NOT a part of the remainder: the remainder is
# DEFINED as total - global_check - hits_nogood, so summing it back in compares
# the parts against a whole that omits one of them. Same set the instrument's
# REMAINDER_COMPONENTS names.
REM = [c for c in d['components'] if c != 'hits_nogood']
print('commit', d['commit'][:7], '| budget', d['budget'], '| scaling', d.get('scaling'))
for r in d['rows']:
    if r.get('outcome') != 'ok':
        print(f\"{r['subject']:<11} -> {r.get('outcome')}\"); continue
    c = r['components']; s = sum(c[k] for k in REM)
    rem = r['remainder_secs_exact']   # the UNROUNDED one the gate itself reads
    off = abs(s - rem) / rem * 100 if rem else float('inf')
    top = r['top_component']          # recorded by the run, not re-derived
    print(f\"{r['subject']:<11} N={r['N']:<3} nodes={r['nodes']:<6} \"
          f\"rem={rem:<8} sum={s:<9.2f} off={off:<5.1f}% \"
          f\"per_node={r['per_node_ms']}ms top={top} \"
          f\"sum_check={'PASS' if r['sum_check_passed'] else 'FAIL ' + str(r['gate_failures'])}\")
print('verdict:', d.get('verdict'))
print('provisional row:', (d.get('provisional_row_pending_4_1_1') or {}).get('row'))
"
```

Expected: every `ok` row has non-zero `nodes`, `sum_check=PASS`, and `off` within 5% (§4.1(2)) — and `off` must agree with `sum_check_passed`, since both read the same rule and the same unrounded remainder. A row with `off` above 5% means components are missing; the run then writes `verdict: GATE FAILED ...` and `provisional row: SUPPRESSED` itself (§5.3), and Task 3 reports that.

**`sum_check_passed` here is the §4.1(2) SUM LIMB ONLY** — that is what each row's `gate_scope` string says, and it is why the run prints "this is the sum limb ONLY". §4.1(1) completeness is decided by Step 4's sweep and by nothing in `profile.json`. A row reading `sum_check_passed: true` has **not** passed §4.1 — which is why the key is no longer called `gate_passed`. The same caution applies to `provisional_row_pending_4_1_1`: its name says it, and its `scope` field repeats it.

- [ ] **Step 6: Confirm the instrument was not edited**

```bash
git status --porcelain ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py
git hash-object ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.py
git status --porcelain mcp_harness/
```

Expected: the first and third print nothing; the second prints the same hash as Step 2.

- [ ] **Step 7: Commit both artifacts**

```bash
git add ../docs/superpowers/evidence/2026-09-29-local-csp-profile/profile.json \
        ../docs/superpowers/evidence/2026-09-29-local-csp-profile/cprofile-lizard.txt
git commit -m "evidence: the local-CSP profile run across the size ladder

<one line: the gate's outcome, the top component with its share and ceiling, and
the lizard->octopus per-node scaling>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Write the verdict

**Files:**
- Create: `docs/superpowers/evidence/2026-09-29-local-csp-profile/README.md`

**Interfaces:**
- Consumes: both artifacts from Task 2.
- Produces: the README. Nothing consumes it; it is the deliverable.

**Context you need:** **the verdict is whatever the data selects under §4.3's rules — do not adjust the bar to fit it.** If the §4.1 gate failed, that is a correct refusal and the README reports it as the outcome; do NOT edit `profile.py` to make a gate pass. Every figure must come from `profile.json` or `cprofile-lizard.txt`, except figures explicitly labelled as cited from other evidence directories.

- [ ] **Step 1: Write the README**

Create `docs/superpowers/evidence/2026-09-29-local-csp-profile/README.md` with these sections, every figure taken from the artifacts:

1. **The question** — the 79.57% is a residual, not a measurement; this names what is inside it. State in this section that the goal is **measurability on more than one subject, not convergence** (§1.1), and why: `assign_budget` is a node budget and 10× it is a recorded negative (cite `../2026-09-24-dense-pleats/nogood-lizard-largebudget.json`'s 584 rejections / 204.5 median / 8,865.1 s / no convergence as **that directory's figures**).
2. **The §4.1 completeness gate** — both readings, expected beside measured: the uncovered-frame list from the sweep, and the components-sum-versus-remainder percentage per subject (read `sum_check_passed`, `gate_failures` and `gate_scope` from each row; the percentage is against `remainder_secs_exact`, which is what the gate itself reads). If either failed, the README **stops here** and says no row may be claimed in either direction — and when the sum-check failed the run has already written `verdict: GATE FAILED ...`, so the README reports that key rather than deciding it.

   **REQUIRED WORDING FOR §4.1(1), AND IT IS NOT OPTIONAL.** The README must report §4.1(1) as **satisfied structurally, not measured**, and must **not** describe the sweep as having measured completeness. `COVERED` names every function defined in the patched module (34/34, `ast`-counted) and `cprofile_sweep`'s file filter excludes every other module and all C builtins, so no named, file-resident function can be flagged: an empty uncovered list is a property of the construction, not a finding. The sweep's live sensitivity is **anonymous frames (`<genexpr>`, `<lambda>`) owned by `assign`'s own loop or by module level**, and that must be stated. **The blind spot must be named:** on Python 3.14, PEP 709 inlines list/dict/set comprehensions, so §4.1(1)'s own worked example — "a comprehension nobody wrapped" — emits no `cProfile` frame and cannot be flagged at all; the spec's other two examples are out of reach too (`_deg` is pre-declared covered, and a builtin or foreign-module `__hash__` is excluded by the file filter). **§4.1(2)'s sum limb is the live numerical completeness check**, and the README must say which limb carries the weight. The instrument prints and writes this scope itself as `SWEEP_SCOPE`, at the head of `cprofile-lizard.txt` — quote it rather than paraphrasing it.

   Every category-(B) justification in `COVERED` was independently verified by call-site analysis, so this narrowing costs no known detection today. Say that too: the point is honest reporting, not a suspected gap.
3. **The component table**, per subject: `self_secs`, `share_of_remainder`, `whole_run_ceiling`, and call counts. Label `share_of_remainder` and `whole_run_ceiling` **derived**, and state that they are the same measurement rescaled so neither corroborates the other.
4. **The Amdahl reading** — the top component's `whole_run_ceiling`, and explicitly that a ceiling is what removing the component *entirely* would buy, which no real optimisation achieves (§6).
5. **The per-node ladder** — per-node ms against `N` and against candidate count for every subject with a row, and whether §4.4's prediction held: `pick`-dominated predicts per-node cost tracking candidate count (`octopus` ≈4.8× `lizard`), `violation`-dominated predicts a nearly flat curve. Say which shape the data has.
6. **The verdict (§4.3)** — which row, why that row and not its neighbours, and note that row 3 is checked first because `setup` is one-time. **The row must be the one `profile.json`'s `provisional_row_pending_4_1_1` reports, not one re-derived by hand** from `scaling` / `TOP_DOMINATES` / `NO_LEVER_BELOW` / `SCALES` / `FLAT_AT_OR_BELOW`: `main()` calls the self-tested `verdict()` and records its answer with its `why` string, and a hand-applied table beside a self-tested function is how a wrong row gets published. Quote the key's name and its `scope` field so the reader sees that it was provisional pending §4.1(1), then state whether the sweep's outcome (item 2) lets it stand.
7. **What this cannot say (§6)** — nothing here addresses convergence; a ceiling is not a speedup; `lizard` remains the only subject with a dense convergence history; `cProfile` is a completeness check and its numbers are not shares.
8. **Subjects that produced no row** — which, why, and the corpus size stated plainly. Do not generalise to eight if fewer produced rows.
9. **Run metadata** — the commit and timestamp from `profile.json`, the fixed budget, the cap, and the instrument's blob hash with the statement that it is unchanged from before the run.

- [ ] **Step 2: Check every README figure against the artifacts**

Re-read the README beside `profile.json` and `cprofile-lizard.txt` and confirm each number appears in one of them. Any figure that does not must be removed or recomputed, with its derivation shown. This step exists because a sibling slice's README shipped three arguments its own instruments dissolved, and because this branch has now withdrawn four of its own figures for being quoted forward without recomputation.

- [ ] **Step 3: Confirm the instrument and artifacts were not edited**

```bash
git status --porcelain ../docs/superpowers/evidence/2026-09-29-local-csp-profile/
git diff --stat HEAD -- mcp_harness/
```

Expected: the only untracked/modified path is `README.md`; the second prints nothing.

- [ ] **Step 4: Commit**

```bash
git add ../docs/superpowers/evidence/2026-09-29-local-csp-profile/README.md
git commit -m "evidence: <the verdict, in a clause> -- dense assign's residual

<one paragraph: the gate's outcome, the component table's headline with the top
component's share and whole-run ceiling, whether the per-node curve matched the
pick-dominated or violation-dominated prediction, and the §4.3 row reached>

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage.** Every section maps to a task:

| spec section | task |
|---|---|
| §1.1 goal is not convergence | Task 1 Step 2's docstring; Task 3 Step 1 item 1 |
| §1.2 count nodes, do not infer | Task 1's `nodes -= 1` patch; Step 5 fails hard if `nodes` is 0 |
| §2 Amdahl adopted | `ceiling()`; self-tested against 1.661× and 4.89× |
| §3.1 the components | `COMPONENTS`, `PATCHES` |
| §3.2 self-time | `self_times` + `CHILDREN`, with a refusal on negative self-time; Step 6 proves the test can fail |
| §3.3 `global_check` stays | `run_subject`'s `spy` |
| §4.1 the gate | `gate()`, self-tested both directions **and at the exact 5% boundary**, and CALLED by `main()` for every `ok` row (recorded as `sum_check_passed` / `gate_failures` / `gate_scope`, sum limb only, against the UNROUNDED `remainder_secs_exact`); the call itself is covered by a monkeypatched-`run_subject` self-test that fails if it is replaced by `True, []`; Task 2 Steps 4-5; Task 3 Step 1 item 2. **§4.1(1)'s named-function limb is satisfied STRUCTURALLY, not measured** — see `SWEEP_SCOPE`, and Task 3 Step 1 item 2's required wording, including the PEP 709 comprehension blind spot |
| §4.2 three figures per component | `run_subject`'s `components` / `share_of_remainder` / `whole_run_ceiling` |
| §4.3 the rows, row 3 first | `verdict()`, self-tested incl. precedence and four boundaries, and **CALLED by `main()`**, which records its answer as `provisional_row_pending_4_1_1` (name and `scope` both state that §4.1(1) is unevaluated). Task 3 Step 1 item 6 requires the README to report that key rather than re-derive the row |
| §4.4 the prediction | Task 3 Step 1 item 5 |
| §4.5 the 1-hour target | Task 3 Step 1 item 6 states what the row licenses |
| §5.1 files | File Structure |
| §5.2 instrument requirements | `BUDGET`, `CAP_SECS` (1800, set from `dog`'s 537.3 s), node counter, patch-and-assert, run metadata |
| §5.3 error handling | `run_subject` returns a row on cap breach; flush per subject; gate suppresses rows |
| §5.4 testing | Task 1 Steps 4-6; `_selftest` covers the spec's five groups **and executes the instrument** on `starfish` (compile-only assertions left the node counter and the `now_open` sign mutable while staying green) |
| §5.5 evidence | Task 3 Step 1's nine items |
| §6 what it cannot say | Task 3 Step 1 item 7 |
| §7 out of scope | Global Constraints forbid every file it names |

**Placeholder scan.** The only intentional placeholders are Task 2 Step 7's and Task 3 Step 4's commit messages, which cannot be written before the data exists; both have their required content enumerated.

**Type consistency.** `COMPONENTS` is the single source of the nine names, used by `self_times` and `run_subject`'s three dicts. `REMAINDER_COMPONENTS` is derived from it by dropping `hits_nogood`, and is the set `gate`'s sum, `main`'s `top` selection, `share_of_remainder`'s non-`None` entries and Task 2 Step 5's check all use — because the remainder is defined as `total - global_check - hits_nogood`, so `hits_nogood` is measured but is not a part of it. `whole_run_ceiling` uses the full `COMPONENTS`, since it is a share of `total`, which does include it. `CHILDREN` keys are a subset of `COMPONENTS` and its values name only `COMPONENTS` members. `self_times(probe) -> dict` and `search_deltas(probe) -> dict` both take the flat counter dict and are composed in that order in `run_subject`. `ceiling(self_secs, total_secs)` returns `float | None` and every caller handles `None`. `gate(components, remainder_secs, cprofile_uncovered)` is called by `main()` once per `ok` row and once by `--selftest`'s live check, always with `remainder_secs_exact`; `verdict(top_name, top_share, setup_share, scaling)` is called once by `main()`, on `lizard`'s row, and its answer is recorded as `provisional_row_pending_4_1_1` — **an earlier revision of this line said each was "called once" while `verdict` was in fact called by nothing.** `remainder_of(total_secs, global_check_secs, hits_nogood_secs)` is the one definition of the remainder and `run_subject` is its only caller; `top_component(components)` maximises over `REMAINDER_COMPONENTS` and is called by `main()` and by `--selftest`; `select_uncovered(text, mod_file, owner_of, where)` is called by `cprofile_sweep` and by `--selftest` on synthetic `pstats` lines. `patch_source` and `verify_diff` both take raw source text, so `--selftest` can feed them altered strings.

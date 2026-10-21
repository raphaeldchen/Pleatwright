# Cross-Section Oracle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide whether `layer_certify`'s `taco` clause family means what it says, by slicing the SAT-certified dense `lizard` perpendicular to each of its 29 collinear crease lines and comparing the constraints that one-dimensional picture imposes against `cons.tacos`.

**Architecture:** Two import-free predicate modules (`lines.py`, `strip.py`) carry the oracle; a driver (`cross_section_oracle.py`) supplies the shared input geometry, runs ten gates, performs one order-free set comparison, and emits a JSON artifact. Nothing under `mcp_harness/` is modified.

**Tech Stack:** Python 3.14, `fractions.Fraction` exact arithmetic, `pytest`. Interpreter is `../../../../.venv/bin/python3` relative to the evidence directory.

**Spec:** `docs/superpowers/specs/2026-10-05-cross-section-oracle-design.md`

## Global Constraints

These bind every task. A task's requirements implicitly include all of them.

- **Working directory.** All commands run from the worktree
  `<repo>`
  or a subdirectory of it. **Never `cd` to the original repository root.**
- **Never use bare `git stash` / `git stash pop`.** The stash stack is shared
  with the main checkout and every other worktree, and other sessions may push
  or pop concurrently. Use a temporary WIP commit instead.
- **Never run `pytest tests/`.** That is 5,167 tests and over three hours.
  Always name the test file.
- **Run FULL named test files, never a `-k` filtered subset.**
- **Never pass `--timeout`.** `pytest-timeout` is not installed; pytest exits 4.
- **`timeout` is not available on macOS.** Do not use it.
- **Do NOT modify** `mcp_harness/layer_order.py`, `mcp_harness/layer_certify.py`,
  `mcp_harness/box_pleat/layers.py`, `mcp_harness/box_pleat/cores.py`.
- **`git diff origin/main --stat -- mcp_harness/` must print nothing** at the
  end of every task.
- **`grep -c box_pleat mcp_harness/server.py` must stay 0.**
- **Do NOT widen** `box_pleat/compile.py`'s `except (ValueError, RuntimeError, KeyError)`.
- **Write commit messages to a file outside the repository** (the session
  scratchpad) and use `git commit -F <file>`. zsh mangles heredocs containing
  backticks.
- **Never nest a heredoc inside another heredoc.**
- **Never `git add -f` anything under `.superpowers/`** — it is gitignored at
  `.gitignore:45`.
- **Quote every glob passed to `grep`** (zsh `nomatch`). `grep -c` exits 1 on
  zero matches, so guard it with `|| true` when the count may be zero.
- **Never use tardigrade / water bear as a test subject.** OWNER INSTRUCTION.
- **End every commit message with** `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`
- **Exact arithmetic only in the oracle.** `lines.py` and `strip.py` use
  `fractions.Fraction`; no float appears in either file.
- **`lines.py` and `strip.py` must not import production code, and must not
  import `geom`.** `geom.py` is a transcription of the production
  layer-ordering module; importing it would make side determination and crease
  bundling common-mode with production, and a shared defect there would make
  both arms miss the same bundles and **agree silently**. Spec §2.3.
- **Docstrings in `lines.py` and `strip.py` must not contain the strings**
  `layer_order`, `layer_certify`, `box_pleat`, `flat_fold`, `build`,
  `mcp_harness`. Cite the transcription by path and line instead — e.g.
  "`geom.py:311`" — and refer to production in prose as "production". A
  docstring that names a banned module and a test that bans it is a
  contradiction, and the predecessor slice resolved it the wrong way round once
  by relaxing the test; **conform the docstring, never the test.**

---

## File Structure

New directory `docs/superpowers/evidence/2026-10-05-cross-section-oracle/`.

| file | responsibility |
|---|---|
| `lines.py` | exact canonical line keys, projection along a line, closed-interval overlap, bundling edges into lines. Imports: `fractions`, `math` only. |
| `strip.py` | the cross-section: unclamped line/convex-polygon clip, strand side classification, U-turn extraction, conditions 1 and 2, the order-free constraint emissions, breakpoint sampling. Imports: `fractions`, `lines` only. |
| `cross_section_oracle.py` | driver: input geometry, the ten gates, the set comparison, `selftest`, `main`, artifact emission. May import production. |
| `conftest.py` | the shared import-allowlist checker. Test machinery only; the oracle never imports it. |
| `test_allowlist.py` | the checker's positive control — each of its three checks must fire, and a clean file must pass. |
| `test_lines.py` | unit tests for `lines.py`, including its import allowlist. |
| `test_strip.py` | unit tests for `strip.py`, including its import allowlist. |
| `cross-section-oracle.json` | the artifact (written by `main`). |
| `README.md` | the write-up. |

**The common-mode boundary, restated because it decides where code goes.** The
*input geometry* is necessarily shared: folded coordinates and clipping
polygons both come from production through `exact_arrangement.load()`. That
sharing lives in the **driver**. Everything the oracle *computes* from that
geometry lives in `lines.py` and `strip.py` and is written for this slice.

**One trap that will bite an implementer who does not read this.** The folded
vertices and the clipping polygons are **different arrays**.
`exact_arrangement.load()` returns `(ff, polys)`:

- crease segments must be read from `ff.folded_vertices` **per face**
  (via `restrict.crease_segments`, which does exactly this), because those are
  **unreversed**;
- clipping and the perpendicular clip must use `polys`, which the production
  helper may have **reversed** to counter-clockwise.

Mixing them silently inverts windings. `is_convex` (gate 2) tests `polys`.

---

## Task 1: `lines.py` — exact line identity and bundling

**Files:**
- Create: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/lines.py`
- Test: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/test_lines.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces, for Task 2: `conftest.assert_import_allowlist(path, allowed, banned=PRODUCTION_NAMES)`
  — raises `AssertionError` naming the offending module; `allowed` is an iterable of module names. Task 2's test file calls it rather than repeating the check. Its positive control lives in `test_allowlist.py`.
- Produces, for Tasks 2–4:
  - `line_key(seg) -> tuple | None` — `(dx, dy, c)` with `dx, dy` `int`, `c` `Fraction`; `None` on a zero-length segment
  - `direction_of(key) -> tuple[int, int]`
  - `project(direction, point) -> Fraction`
  - `span(direction, seg) -> tuple[Fraction, Fraction]` — `(lo, hi)`, `lo <= hi`
  - `intervals_overlap(i1, i2) -> bool` — strictly more than a point
  - `contains(interval, t) -> bool` — closed containment
  - `bundles(edges) -> dict[tuple, tuple]` — `line_key -> edges on that line`; raises `ValueError` on a degenerate segment
  - `overlapping_lines(bundles_map, kinds=("M", "V")) -> tuple` — the line keys carrying two edges of those kinds whose spans overlap in more than a point
  - An `edge` is the 4-tuple `(fa: int, fb: int, assignment: str, seg)`.
  - A `seg` is `((Fraction, Fraction), (Fraction, Fraction))`.

- [ ] **Step 1: Create the directory and the shared allowlist checker**

Create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/conftest.py`:

```python
"""Shared test machinery for the cross-section oracle's unit tests.

Holds ONE copy of the import-allowlist check. Both `lines.py` and `strip.py`
must be free of production code and of `geom` (design spec section 2.3), and
the check for that is identical in structure for each -- so it lives here
rather than being repeated, and it carries a POSITIVE CONTROL proving it can
actually fail. A checker that never fails is the same trap as a gate that
never fires.

This file is test machinery. Neither `lines.py` nor `strip.py` imports it,
and their own allowlists do not list it.
"""
import ast
import os

HERE = os.path.dirname(os.path.abspath(__file__))

#: Module names whose mere MENTION in the oracle's source -- docstrings
#: included -- would indicate a production dependency. The constraint is
#: literal, so the scan is too.
PRODUCTION_NAMES = ("layer_order", "layer_certify", "box_pleat", "flat_fold",
                    "build", "mcp_harness")


def imported_modules(src):
    """Every module named by an import statement in `src`.

    Structural, via the AST, rather than by substring: a substring scan would
    match a module name inside a comment and miss `from x import y`.
    """
    out = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            out.add(node.module)
    return out


def assert_import_allowlist(path, allowed, banned=PRODUCTION_NAMES):
    """The oracle module at `path` imports only `allowed` and names no
    module in `banned`.

    Three checks, all required:
      1. every imported module is in `allowed`;
      2. no dynamic-import escape hatch, which would evade check 1;
      3. no `banned` name anywhere in the RAW source, docstrings included.

    Check 3 is on raw source deliberately. The predecessor slice hit the
    contradiction of a docstring naming a module its own test banned, and
    resolved it the wrong way round once by relaxing the test. The rule is:
    conform the docstring -- cite the file and line instead -- never the test.
    """
    with open(path) as fh:
        src = fh.read()
    name = os.path.basename(path)
    extra = sorted(imported_modules(src) - set(allowed))
    assert not extra, (
        f"{name} imports {extra} beyond the allowlist {sorted(allowed)}")
    for dynamic in ("__import__", "importlib"):
        assert dynamic not in src, (
            f"{name} mentions {dynamic!r}; a dynamic import would evade the "
            f"AST allowlist")
    for bad in banned:
        assert bad not in src, (
            f"{name} mentions {bad!r}; the oracle must not import or name "
            f"production code, or the comparison is circular")
```

Then create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/test_allowlist.py` — the checker's own positive control:

```python
"""POSITIVE CONTROL for `conftest.assert_import_allowlist`.

A checker that cannot fail is the same trap as a gate that never fires, and
this arc has already shipped one of those -- an `is_convex` that admitted the
clockwise face it existed to reject. So each of the checker's three checks is
exercised here against a purpose-built file, plus a fourth assertion that it
PASSES a clean one, since a checker that always fails is the mirror-image
trap.

ITS OWN FILE, for two reasons learned by running the first draft of it:

  * pointing the control at `conftest.py` does not work. That file contains
    the literal `__import__` inside its own dynamic-import check, so check 2
    fires first and MASKS checks 1 and 3.
  * pytest does not collect test functions out of `conftest.py` unless the
    file is named on the command line, so a control living there would
    silently not run under the ordinary invocation.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pytest                          # noqa: E402
from conftest import assert_import_allowlist   # noqa: E402


def test_each_check_fires_and_a_clean_file_passes(tmp_path):
    def _f(name, body):
        p = tmp_path / name
        p.write_text(body)
        return str(p)

    # check 1: an import outside the allowlist.
    with pytest.raises(AssertionError, match="beyond the allowlist"):
        assert_import_allowlist(_f("a.py", "import os\n"),
                                allowed=("fractions",))

    # check 2: a dynamic-import escape hatch, which is NOT an import node and
    # so passes check 1 -- which is exactly why check 2 exists.
    with pytest.raises(AssertionError, match="dynamic import"):
        assert_import_allowlist(_f("b.py", "x = __import__('os')\n"),
                                allowed=())

    # check 3: a banned name in a DOCSTRING rather than an import, which is
    # the case the raw-source scan exists for.
    with pytest.raises(AssertionError, match="layer_order"):
        assert_import_allowlist(_f("c.py", '"""cites layer_order."""\n'),
                                allowed=())

    # and it must PASS a clean file.
    assert_import_allowlist(_f("d.py", "from fractions import Fraction\n"),
                            allowed=("fractions",))
```

Then create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/test_lines.py`:

```python
"""Unit tests for `lines.py`. Run directly, never via `pytest tests/`.

    cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
    ../../../../.venv/bin/python3 -m pytest test_lines.py -v
"""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lines                           # noqa: E402
import pytest                          # noqa: E402
from conftest import assert_import_allowlist   # noqa: E402

F = Fraction


def _seg(x0, y0, x1, y1):
    return ((F(x0), F(y0)), (F(x1), F(y1)))


def test_imports_are_allowlisted():
    """`lines.py` must depend on neither production nor `geom`.

    `geom` is deliberately absent from the allowlist: its `collinear_overlap`
    and `segs_interact` are transcriptions of production, and bundling with
    those would make the bundling common-mode, so a shared defect would make
    both arms miss the same bundles and AGREE SILENTLY.

    The checker lives in `conftest.py` with its own positive control, so this
    test states the allowlist and nothing else.
    """
    assert_import_allowlist(os.path.join(HERE, "lines.py"),
                            allowed=("fractions", "math"))


def test_line_key_equal_for_collinear_segments():
    a = lines.line_key(_seg(0, 0, 2, 0))
    b = lines.line_key(_seg(5, 0, 7, 0))
    c = lines.line_key(_seg(-3, 0, -1, 0))
    assert a == b == c


def test_line_key_differs_for_parallel_offset_lines():
    assert lines.line_key(_seg(0, 0, 2, 0)) != lines.line_key(_seg(0, 1, 2, 1))


def test_line_key_is_direction_sign_invariant():
    """A segment and its reverse are the same line."""
    assert lines.line_key(_seg(0, 0, 3, 1)) == lines.line_key(_seg(3, 1, 0, 0))


def test_line_key_is_scale_invariant():
    """Collinear segments of different lengths share one key, which requires
    the direction to be reduced to lowest terms before the offset is formed."""
    assert lines.line_key(_seg(0, 0, 2, 4)) == lines.line_key(_seg(0, 0, 1, 2))


def test_line_key_handles_fractional_coordinates():
    """Folded box-pleat coordinates are rationals with large denominators, so
    the integer reduction must go through the denominators' lcm."""
    s1 = ((F(1, 3), F(1, 7)), (F(4, 3), F(1, 7)))
    s2 = ((F(10, 3), F(1, 7)), (F(13, 3), F(1, 7)))
    assert lines.line_key(s1) == lines.line_key(s2)


def test_line_key_none_on_degenerate_segment():
    assert lines.line_key(_seg(2, 2, 2, 2)) is None


def test_direction_of_round_trips():
    k = lines.line_key(_seg(0, 0, 2, 4))
    assert lines.direction_of(k) == (1, 2)


def test_project_is_order_preserving_along_the_line():
    d = lines.direction_of(lines.line_key(_seg(0, 0, 1, 1)))
    ts = [lines.project(d, (F(t), F(t))) for t in (-2, 0, 1, 5)]
    assert ts == sorted(ts)


def test_span_is_sorted():
    d = (1, 0)
    assert lines.span(d, _seg(5, 0, 1, 0)) == (F(1), F(5))


def test_intervals_overlap_needs_more_than_a_point():
    assert lines.intervals_overlap((F(0), F(2)), (F(1), F(3))) is True
    assert lines.intervals_overlap((F(0), F(1)), (F(1), F(2))) is False
    assert lines.intervals_overlap((F(0), F(1)), (F(2), F(3))) is False


def test_contains_is_closed():
    assert lines.contains((F(0), F(2)), F(0)) is True
    assert lines.contains((F(0), F(2)), F(2)) is True
    assert lines.contains((F(0), F(2)), F(3)) is False


def test_bundles_groups_by_line():
    edges = (
        (0, 1, "M", _seg(0, 0, 2, 0)),
        (2, 3, "V", _seg(1, 0, 3, 0)),
        (4, 5, "M", _seg(0, 1, 2, 1)),
    )
    b = lines.bundles(edges)
    assert len(b) == 2
    sizes = sorted(len(v) for v in b.values())
    assert sizes == [1, 2]


def test_bundles_refuses_a_degenerate_segment():
    """A zero-length folded crease image means the folded state is degenerate.
    The caller must learn that, so it is a refusal and not a silent drop."""
    edges = ((0, 1, "M", _seg(1, 1, 1, 1)),)
    with pytest.raises(ValueError, match="degenerate"):
        lines.bundles(edges)


def test_overlapping_lines_requires_two_creases_that_overlap():
    edges = (
        (0, 1, "M", _seg(0, 0, 2, 0)),      # line A, overlaps the next
        (2, 3, "V", _seg(1, 0, 3, 0)),      # line A
        (4, 5, "M", _seg(0, 1, 1, 1)),      # line B, touches only
        (6, 7, "M", _seg(1, 1, 2, 1)),      # line B
        (8, 9, "M", _seg(0, 2, 1, 2)),      # line C, alone
    )
    b = lines.bundles(edges)
    got = lines.overlapping_lines(b)
    assert got == (lines.line_key(_seg(0, 0, 2, 0)),)


def test_overlapping_lines_ignores_flat_edges_by_default():
    """`kinds` defaults to the creases. A pair of flat edges is a
    tortilla-tortilla configuration, not a taco, so it must not by itself make
    a line count as crease-overlapping."""
    edges = (
        (0, 1, "F", _seg(0, 0, 2, 0)),
        (2, 3, "F", _seg(1, 0, 3, 0)),
    )
    assert lines.overlapping_lines(lines.bundles(edges)) == ()


def test_overlapping_lines_honours_an_explicit_kinds_argument():
    edges = (
        (0, 1, "F", _seg(0, 0, 2, 0)),
        (2, 3, "F", _seg(1, 0, 3, 0)),
    )
    b = lines.bundles(edges)
    assert len(lines.overlapping_lines(b, kinds=("F",))) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -m pytest test_lines.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'lines'`.

- [ ] **Step 3: Write `lines.py`**

Create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/lines.py`:

```python
"""Grouping folded edge images into collinear bundles, in exact rationals.

INDEPENDENT BY CONSTRUCTION: this module imports only `fractions` and `math`.

It deliberately does NOT use the transcriptions in `geom.py` --
`collinear_overlap` (`geom.py:359`) and `segs_interact` (`geom.py:379`) are
copies of production's predicates. Bundling with those would make the bundling
common-mode with production: a defect shared by both arms would make them miss
the same bundles and AGREE SILENTLY, which is the worst failure available to a
comparison. The design spec section 2.3 states the whole boundary.

The bundling test here is an EQUALITY on exact rationals, not a tolerance
comparison: two segments lie on one line exactly when their canonical line
keys are equal. There is no epsilon anywhere in this file.
"""
from fractions import Fraction
from math import gcd, lcm


def _integer_direction(dx, dy):
    """`(dx, dy)` as a sign-canonical integer direction in lowest terms.

    Returns None for the zero vector. The reduction has to happen before the
    line offset is formed: scaling a direction scales the offset identically,
    so only the reduced pair is unique per line.
    """
    fx, fy = Fraction(dx), Fraction(dy)
    if fx == 0 and fy == 0:
        return None
    m = lcm(fx.denominator, fy.denominator)
    ix, iy = int(fx * m), int(fy * m)
    g = gcd(abs(ix), abs(iy))
    ix, iy = ix // g, iy // g
    if ix < 0 or (ix == 0 and iy < 0):
        ix, iy = -ix, -iy
    return (ix, iy)


def line_key(seg):
    """A canonical exact identifier for the infinite line through `seg`.

    `(dx, dy, c)` where `(dx, dy)` is the reduced sign-canonical integer
    direction and `c = dx * y0 - dy * x0` is the line's offset in those same
    units. Two segments lie on one line iff their keys are equal.

    Returns None on a zero-length segment -- a caller that needs a refusal
    should raise it; this predicate reports, it does not decide.
    """
    (x0, y0), (x1, y1) = seg
    d = _integer_direction(x1 - x0, y1 - y0)
    if d is None:
        return None
    dx, dy = d
    return (dx, dy, dx * Fraction(y0) - dy * Fraction(x0))


def direction_of(key):
    """The reduced integer direction a `line_key` carries."""
    return (key[0], key[1])


def project(direction, point):
    """`point`'s coordinate along `direction`, as an exact rational.

    This is the dot product with the (unnormalised) direction, so the absolute
    scale is arbitrary. That is harmless and deliberate: every comparison made
    with it is between two projections taken on the SAME line with the SAME
    direction, and the map is strictly order-preserving along that line.
    Avoiding normalisation keeps the value rational.
    """
    dx, dy = direction
    return dx * Fraction(point[0]) + dy * Fraction(point[1])


def span(direction, seg):
    """`seg`'s closed interval `(lo, hi)` along `direction`, with `lo <= hi`."""
    a, b = project(direction, seg[0]), project(direction, seg[1])
    return (a, b) if a <= b else (b, a)


def intervals_overlap(i1, i2):
    """True iff two closed intervals share MORE THAN a single point.

    Strict, matching production's own reading: two segments meeting at one
    endpoint are not an overlap. That degenerate neighbour is recorded as a
    limitation in the design spec section 8.7 rather than handled here.
    """
    return min(i1[1], i2[1]) - max(i1[0], i2[0]) > 0


def contains(interval, t):
    """Closed containment. The endpoints belong to the interval."""
    return interval[0] <= t <= interval[1]


def bundles(edges):
    """`line_key -> tuple of edges on that line`, over every line.

    `edges` holds 4-tuples `(fa, fb, assignment, seg)`. Every line with at
    least one edge appears; filtering to the interesting ones is
    `overlapping_lines`' job, kept separate so each is testable alone.

    A degenerate segment is a REFUSAL, not a drop: a zero-length folded edge
    image means the folded state itself is degenerate, and a caller that
    silently loses the edge would under-report the comparison and call it
    agreement.
    """
    out = {}
    for edge in edges:
        key = line_key(edge[3])
        if key is None:
            raise ValueError(
                f"lines.bundles: edge {edge[0]}-{edge[1]} has a degenerate "
                f"(zero-length) folded segment {edge[3]}. Refusing: a "
                f"zero-length folded edge image means the folded state is "
                f"degenerate, and dropping it would under-report the "
                f"comparison.")
        out.setdefault(key, []).append(edge)
    return {k: tuple(v) for k, v in out.items()}


def overlapping_lines(bundles_map, kinds=("M", "V")):
    """The line keys carrying two edges of `kinds` whose spans overlap.

    Sorted for determinism. `kinds` defaults to the creases, because a pair of
    flat edges is a tortilla-tortilla configuration rather than a taco and
    must not by itself mark a line as crease-overlapping.
    """
    out = []
    for key, edges in bundles_map.items():
        d = direction_of(key)
        spans = [span(d, e[3]) for e in edges if e[2] in kinds]
        found = False
        for i in range(len(spans)):
            for j in range(i + 1, len(spans)):
                if intervals_overlap(spans[i], spans[j]):
                    found = True
                    break
            if found:
                break
        if found:
            out.append(key)
    return tuple(sorted(out))
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -m pytest test_allowlist.py test_lines.py -v
```

Expected: 18 passed — 1 in `test_allowlist.py` plus 17 in `test_lines.py`.

- [ ] **Step 5: Confirm production is untouched**

```bash
git diff origin/main --stat -- mcp_harness/
```

Expected: no output.

- [ ] **Step 6: Commit**

Write the message to `<scratchpad>/msg-task1.txt`, then:

```bash
git add docs/superpowers/evidence/2026-10-05-cross-section-oracle/ && git commit -F <scratchpad>/msg-task1.txt
```

---

## Task 2: `strip.py` — the cross-section and its validity rule

**Files:**
- Create: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/strip.py`
- Test: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/test_strip.py`

**Interfaces:**
- Consumes from Task 1: `lines.direction_of`, `lines.project`, `lines.span`,
  `lines.contains` — exact signatures in Task 1's Produces block.
- Produces, for Tasks 3–4:
  - Constants `SIDE_POS = 1`, `SIDE_NEG = -1`, `THROUGH = 0`
  - `perpendicular(direction) -> tuple[int, int]`
  - `line_clip(poly, p, w) -> tuple[Fraction, Fraction] | None`
  - `side_at(poly, p, w) -> int | None` — raises `ValueError` on a single-point touch
  - `sides_at(polys, faces, p, w) -> dict[int, int]`
  - `edges_at(bundle_edges, direction, t, kinds) -> tuple`
  - `uturns_at(crease_edges, sides) -> tuple[tuple, tuple]` — `(uturns, anomalies)`; a uturn is `(fa, fb, side)`
  - `taco_pairs(uturns) -> set[frozenset]` — elements are `frozenset({frozenset({fa1, fb1}), frozenset({fa2, fb2})})`
  - `pierce_pairs(uturns, sides) -> set[tuple]` — elements are `(through_face, frozenset({fa, fb}))`
  - `pierced(uturn, sides, order) -> tuple[int, ...]`
  - `interleaved(u1, u2, order) -> bool`
  - `accepts(sides, uturns, order) -> tuple` — the violations; empty means accept
  - `breakpoints(intervals) -> tuple[Fraction, ...]`
  - `sub_segment_samples(bps) -> tuple[Fraction, ...]`
  - `point_at(direction, anchor, t) -> tuple[Fraction, Fraction]`

- [ ] **Step 1: Write the failing tests**

Create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/test_strip.py`:

```python
"""Unit tests for `strip.py`. Run directly, never via `pytest tests/`.

    cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
    ../../../../.venv/bin/python3 -m pytest test_strip.py -v
"""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lines                           # noqa: E402
import pytest                          # noqa: E402
import strip                           # noqa: E402
from conftest import assert_import_allowlist   # noqa: E402

F = Fraction

#: The x axis, as a bundle direction and its perpendicular.
XDIR = (1, 0)
XPERP = strip.perpendicular(XDIR)       # (0, 1)


def _ccw_rect(x0, y0, x1, y1):
    """A strictly counter-clockwise axis-aligned rectangle, exact."""
    return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]


def test_imports_are_allowlisted():
    """`strip.py` must depend on neither production nor `geom`.

    `side_of` (`geom.py:311`) derives the side from the polygon CENTROID,
    which is exactly the derivation `side_at` has to reach independently, and
    `clip_seg` (`geom.py:250`) clamps to [0, 1] where this module needs the
    unclamped interval of an infinite line. Importing either would make the
    oracle's side determination common-mode with production.

    The checker lives in `conftest.py` with its own positive control.
    """
    assert_import_allowlist(os.path.join(HERE, "strip.py"),
                            allowed=("fractions", "lines"))


def test_perpendicular_is_the_left_normal():
    assert strip.perpendicular((1, 0)) == (0, 1)
    assert strip.perpendicular((0, 1)) == (-1, 0)
    assert strip.perpendicular((2, 3)) == (-3, 2)


def test_line_clip_through_a_rectangle():
    """The vertical line x = 1 crosses the rectangle y in [-2, 3]."""
    poly = _ccw_rect(0, -2, 4, 3)
    got = strip.line_clip(poly, (F(1), F(0)), XPERP)
    assert got == (F(-2), F(3))


def test_line_clip_misses_a_rectangle():
    poly = _ccw_rect(0, -2, 4, 3)
    assert strip.line_clip(poly, (F(9), F(0)), XPERP) is None


def test_line_clip_is_one_sided_for_a_face_above_the_line():
    """A face sitting entirely above y = 0 clips to a span with lo == 0."""
    poly = _ccw_rect(0, 0, 4, 5)
    assert strip.line_clip(poly, (F(1), F(0)), XPERP) == (F(0), F(5))


def test_line_clip_refuses_an_unbounded_reading():
    """A degenerate ring can leave an end unbounded; a bounded convex polygon
    cannot, so that is a refusal rather than a half-open interval a caller
    would misread as a side.

    A ONE-VERTEX ring is the real case. Its single zero-length edge gives
    `den == 0` and `num == 0`, which the parallel-and-inside branch skips, so
    neither end is ever bounded. (A two-point "ring" does NOT work: both its
    edges bound t and the clip returns (0, 0) -- a single-point touch, not an
    unbounded reading.)
    """
    degenerate = [(F(0), F(0))]                    # one vertex: not a ring
    with pytest.raises(ValueError, match="unbounded"):
        strip.line_clip(degenerate, (F(0), F(0)), XPERP)


def test_side_at_reads_through_pos_neg():
    p = (F(1), F(0))
    assert strip.side_at(_ccw_rect(0, -2, 4, 3), p, XPERP) == strip.THROUGH
    assert strip.side_at(_ccw_rect(0, 0, 4, 5), p, XPERP) == strip.SIDE_POS
    assert strip.side_at(_ccw_rect(0, -5, 4, 0), p, XPERP) == strip.SIDE_NEG


def test_side_at_none_when_the_point_is_outside():
    assert strip.side_at(_ccw_rect(5, 0, 9, 5), (F(1), F(0)), XPERP) is None


def test_side_at_refuses_a_single_point_touch():
    """A face meeting the line only at p itself has no determinable side.

    The triangle must be TANGENT to the perpendicular at p -- entirely in
    x >= 1, touching x = 1 only at the vertex (1, 0). A triangle the
    perpendicular crosses would read SIDE_POS instead, and the test would pass
    for the wrong reason.
    """
    triangle = [(F(1), F(0)), (F(3), F(-1)), (F(3), F(1))]   # CCW, tangent
    with pytest.raises(ValueError, match="single point"):
        strip.side_at(triangle, (F(1), F(0)), XPERP)


def test_sides_at_collects_only_the_faces_that_meet_the_point():
    polys = {
        7: _ccw_rect(0, -2, 4, 3),      # through
        8: _ccw_rect(0, 0, 4, 5),       # pos
        9: _ccw_rect(5, 0, 9, 5),       # off the point entirely
    }
    got = strip.sides_at(polys, (7, 8, 9), (F(1), F(0)), XPERP)
    assert got == {7: strip.THROUGH, 8: strip.SIDE_POS}


def test_edges_at_selects_by_closed_span_containment():
    edges = (
        (0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),
        (2, 3, "M", ((F(5), F(0)), (F(7), F(0)))),
        (4, 5, "F", ((F(0), F(0)), (F(2), F(0)))),
    )
    got = strip.edges_at(edges, XDIR, F(1), ("M", "V"))
    assert tuple(e[:2] for e in got) == ((0, 1),)


def test_uturns_at_pairs_same_side_faces():
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS}
    edges = ((0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),)
    uturns, anomalies = strip.uturns_at(edges, sides)
    assert uturns == ((0, 1, strip.SIDE_POS),)
    assert anomalies == ()


def test_uturns_at_reports_an_opposite_side_crease_as_an_anomaly():
    """A crease's two faces lie on the SAME side -- that is what folding over
    is. An opposite-side reading is reported, never silently dropped: a silent
    drop would hide a disagreement about which pairs are interpretable."""
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_NEG}
    edges = ((0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),)
    uturns, anomalies = strip.uturns_at(edges, sides)
    assert uturns == ()
    assert anomalies == ((0, 1, strip.SIDE_POS, strip.SIDE_NEG),)


def test_uturns_at_reports_a_through_face_as_an_anomaly():
    sides = {0: strip.THROUGH, 1: strip.SIDE_POS}
    edges = ((0, 1, "M", ((F(0), F(0)), (F(2), F(0)))),)
    uturns, anomalies = strip.uturns_at(edges, sides)
    assert uturns == () and len(anomalies) == 1


def test_taco_pairs_emits_one_object_per_same_side_pair():
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    got = strip.taco_pairs(uturns)
    assert got == {frozenset((frozenset((0, 1)), frozenset((2, 3))))}


def test_taco_pairs_skips_opposite_side_pairs():
    """Arcs on opposite sides bulge opposite ways in x and cannot meet. This
    is the geometric content of production's side bookkeeping, and the
    pre-registered prediction of design spec section 6 rests on it."""
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_NEG))
    assert strip.taco_pairs(uturns) == set()


def test_taco_pairs_is_order_free():
    """The emission depends on geometry alone, which is why the comparison in
    design spec section 3 needs no candidate layer order."""
    a = strip.taco_pairs(((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS)))
    b = strip.taco_pairs(((2, 3, strip.SIDE_POS), (0, 1, strip.SIDE_POS)))
    assert a == b


def test_pierce_pairs_emits_through_face_against_crease():
    uturns = ((0, 1, strip.SIDE_POS),)
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    assert strip.pierce_pairs(uturns, sides) == {(5, frozenset((0, 1)))}


def test_pierce_pairs_ignores_non_through_strands():
    uturns = ((0, 1, strip.SIDE_POS),)
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.SIDE_NEG}
    assert strip.pierce_pairs(uturns, sides) == set()


def test_pierced_finds_a_through_strand_between_the_layers():
    order = {0: 0, 5: 1, 1: 2}
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    assert strip.pierced((0, 1, strip.SIDE_POS), sides, order) == (5,)


def test_pierced_ignores_a_through_strand_outside_the_layers():
    order = {0: 0, 1: 1, 5: 2}
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    assert strip.pierced((0, 1, strip.SIDE_POS), sides, order) == ()


def test_interleaved_detects_crossing_arcs():
    order = {0: 0, 2: 1, 1: 2, 3: 3}          # a < c < b < d
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_POS), order) is True


def test_interleaved_accepts_nested_arcs():
    """A nested pleat is valid -- this is the configuration that has no thick
    realization at all, which is why the thickened route was refuted."""
    order = {0: 0, 2: 1, 3: 2, 1: 3}          # a < c < d < b
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_POS), order) is False


def test_interleaved_accepts_disjoint_arcs():
    order = {0: 0, 1: 1, 2: 2, 3: 3}
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_POS), order) is False


def test_interleaved_is_false_across_sides():
    order = {0: 0, 2: 1, 1: 2, 3: 3}
    assert strip.interleaved((0, 1, strip.SIDE_POS),
                             (2, 3, strip.SIDE_NEG), order) is False


def test_accepts_is_empty_on_a_valid_nested_strip():
    order = {0: 0, 2: 1, 3: 2, 1: 3}
    sides = {f: strip.SIDE_POS for f in (0, 1, 2, 3)}
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    assert strip.accepts(sides, uturns, order) == ()


def test_accepts_reports_an_interleaving():
    order = {0: 0, 2: 1, 1: 2, 3: 3}
    sides = {f: strip.SIDE_POS for f in (0, 1, 2, 3)}
    uturns = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    v = strip.accepts(sides, uturns, order)
    assert len(v) == 1 and v[0][0] == "interleaved"


def test_accepts_reports_a_pierce():
    order = {0: 0, 5: 1, 1: 2}
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    v = strip.accepts(sides, ((0, 1, strip.SIDE_POS),), order)
    assert len(v) == 1 and v[0][0] == "pierced"


def test_breakpoints_are_sorted_and_deduplicated():
    got = strip.breakpoints([(F(2), F(5)), (F(0), F(2)), (F(0), F(5))])
    assert got == (F(0), F(2), F(5))


def test_sub_segment_samples_land_strictly_inside():
    bps = (F(0), F(2), F(5))
    got = strip.sub_segment_samples(bps)
    assert got == (F(1), F(7, 2))
    for i, t in enumerate(got):
        assert bps[i] < t < bps[i + 1]


def test_sub_segment_samples_empty_for_fewer_than_two_breakpoints():
    assert strip.sub_segment_samples((F(3),)) == ()
    assert strip.sub_segment_samples(()) == ()


def test_point_at_round_trips_through_project():
    d = (1, 2)
    anchor = (F(1), F(1))
    for t in (F(-3), F(0), F(5, 7)):
        p = strip.point_at(d, anchor, t)
        assert lines.project(d, p) == t


def test_point_at_stays_on_the_line():
    d = lines.direction_of(lines.line_key(((F(0), F(0)), (F(2), F(4)))))
    anchor = (F(0), F(0))
    p = strip.point_at(d, anchor, F(5))
    assert lines.line_key((anchor, p)) == lines.line_key(
        ((F(0), F(0)), (F(2), F(4))))
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -m pytest test_strip.py -v
```

Expected: collection error, `ModuleNotFoundError: No module named 'strip'`.

- [ ] **Step 3: Write `strip.py`**

Create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/strip.py`:

```python
"""The perpendicular cross-section of a flat-folded state, and its validity
rule.

INDEPENDENT BY CONSTRUCTION: this module imports only `fractions` and
`lines.py`, which is itself import-free. In particular it does NOT use the
transcriptions in `geom.py`:

  * `side_of` (`geom.py:311`) derives the side from the polygon CENTROID --
    precisely the derivation `side_at` below has to reach independently. Using
    it would make side determination common-mode with production.
  * `clip_seg` (`geom.py:250`) clamps the parameter to [0, 1]. This module
    needs the UNCLAMPED interval of an infinite line, which production has no
    routine for at all -- so `line_clip` is a NEW computation rather than a
    re-transcription, and carries none of the bitwise-fidelity risk that
    justified reusing those transcriptions in the predecessor slice.

The design spec section 2.3 states the full boundary. What remains common-mode
is the input geometry both arms necessarily read.

THE RULE, derived in the cross-section plane with `x` the perpendicular
coordinate and `z` the layer index.

A crease whose folded image passes through the sample point is a U-TURN: an
arc at x = 0 joining its two faces' layers and sweeping every layer between
them. Its two faces lie on the SAME side, because folding over is what a
crease is. Two conditions follow, and nothing else does:

  1. no THROUGH strand may sit strictly between a U-turn's two layers -- the
     arc passes through (0, z) and the through strand already occupies it;
  2. no two U-turns on the SAME side may interleave -- arcs spanning layers
     a < c < b < d cross.

U-turns on OPPOSITE sides bulge opposite ways in x and cannot meet; that is
the geometric content of production's side bookkeeping. A flat (uncreased)
edge on the line is a through strand realized as two faces, one each side, so
it needs no third condition.

A face terminating exactly at the line is a FREE END: its endpoint lies ON the
arc but does not pierce it -- a measure-zero touch rather than a penetration,
which is why production's spanning rule requires strict interiority. That
modelling choice is SHARED with production, so this module does not test it;
design spec section 8.2 records it as a limitation.

SIDE LABELS ARE SIGNS, NOT COMPASS DIRECTIONS. `SIDE_POS` means the face
extends toward +t along the perpendicular `w`, and `SIDE_NEG` toward -t. No
claim is made about which is geometrically left: the rule is symmetric in the
two sides, so the labelling only has to be CONSISTENT, and tying it to the
sign of t makes that automatic.
"""
from fractions import Fraction

import lines

#: Strand classes. The two sides are signs along the perpendicular; THROUGH
#: means the face's interior crosses the line at the sample point.
SIDE_POS = 1
SIDE_NEG = -1
THROUGH = 0


def perpendicular(direction):
    """The exact left-normal of an integer direction. Stays integral."""
    dx, dy = direction
    return (-dy, dx)


def line_clip(poly, p, w):
    """The parametric interval of the infinite line `p + t*w` inside a
    strictly counter-clockwise convex `poly`, as `(t_lo, t_hi)`.

    `None` when the line misses the polygon. `t_lo == t_hi` is a single-point
    touch and is returned as such -- classifying it is `side_at`'s job.

    A half-plane intersection over t in (-inf, inf). For each directed edge
    a -> b of a counter-clockwise ring the interior is
    `cross(b - a, x - a) >= 0`; substituting `x = p + t*w` gives
    `num + t*den >= 0` with

        num = cross(e, p - a),  den = cross(e, w),  e = b - a

    so `den > 0` gives a lower bound on t, `den < 0` an upper bound, and
    `den == 0` (the line parallel to that edge) is satisfiable iff
    `num >= 0`.

    Refuses if either end is still unbounded after the loop. A bounded convex
    ring cannot leave one unbounded, so that reading means the ring is
    degenerate or not convex -- and returning a half-open interval would let a
    caller read it as a side.
    """
    lo = None
    hi = None
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        ex, ey = b[0] - a[0], b[1] - a[1]
        den = ex * w[1] - ey * w[0]
        num = ex * (p[1] - a[1]) - ey * (p[0] - a[0])
        if den == 0:
            if num < 0:
                return None                 # parallel and strictly outside
            continue                        # parallel and inside: no bound
        t = Fraction(-num) / den
        if den > 0:
            lo = t if lo is None else max(lo, t)
        else:
            hi = t if hi is None else min(hi, t)
    if lo is None or hi is None:
        raise ValueError(
            f"strip.line_clip: the line through {p} is unbounded inside this "
            f"polygon ({n} vertices), which a bounded convex ring cannot "
            f"produce -- the ring is degenerate or not convex. Refusing "
            f"rather than returning a half-open interval a caller would read "
            f"as a side.")
    if hi < lo:
        return None
    return (lo, hi)


def side_at(poly, p, w):
    """How `poly` meets the line at `p`: THROUGH, SIDE_POS, SIDE_NEG, or None.

    Read off the sign of the clipped interval, with t = 0 at `p`:

        t_lo < 0 < t_hi  ->  THROUGH    (the interior crosses the line at p)
        t_lo = 0 < t_hi  ->  SIDE_POS
        t_lo < 0 = t_hi  ->  SIDE_NEG
        t_lo = t_hi = 0  ->  a single-point touch: REFUSE
        the interval misses t = 0  ->  None (p is not in this face)

    The single-point case is a refusal and not a guess: a face meeting the
    line in exactly the sample point has no determinable side, and choosing
    one would silently decide a constraint.
    """
    span = line_clip(poly, p, w)
    if span is None:
        return None
    lo, hi = span
    if lo > 0 or hi < 0:
        return None
    if lo == 0 and hi == 0:
        raise ValueError(
            f"strip.side_at: the line meets this polygon in the single point "
            f"{p} itself (t_lo == t_hi == 0), so its side is undetermined. "
            f"Refusing rather than guessing.")
    if lo < 0 and hi > 0:
        return THROUGH
    return SIDE_POS if lo == 0 else SIDE_NEG


def sides_at(polys, faces, p, w):
    """`face -> strand class`, for the faces in `faces` that meet `p`.

    `polys` is a mapping face -> counter-clockwise exact ring. Faces whose
    `side_at` is None are absent from the result rather than present with a
    sentinel, so a caller cannot accidentally treat "not here" as a side.
    """
    out = {}
    for f in faces:
        s = side_at(polys[f], p, w)
        if s is not None:
            out[f] = s
    return out


def edges_at(bundle_edges, direction, t, kinds):
    """The edges of `bundle_edges` with an assignment in `kinds` whose span
    along `direction` contains `t`, closed.

    Closed containment is deliberate: `t` is a sub-segment midpoint, so it
    never coincides with a span endpoint in the driver's use, and keeping the
    test closed means a hand-built test fixture can place `t` on an endpoint
    without the function quietly disagreeing with `lines.contains`.
    """
    return tuple(e for e in bundle_edges if e[2] in kinds
                 and lines.contains(lines.span(direction, e[3]), t))


def uturns_at(crease_edges, sides):
    """`(uturns, anomalies)` for the creases at a sample point.

    A uturn is `(fa, fb, side)`. An anomaly is `(fa, fb, side_a, side_b)`.

    A crease's two faces must lie on the same side and neither may be THROUGH.
    A pair that fails this is REPORTED, never silently dropped: production
    skips such a pair, and a silent skip here would hide a disagreement about
    which pairs are interpretable at all. The driver gates on the anomaly
    count so the quantity is measured rather than assumed.
    """
    uturns = []
    anomalies = []
    for edge in crease_edges:
        fa, fb = edge[0], edge[1]
        sa, sb = sides.get(fa), sides.get(fb)
        if sa is None or sb is None or sa == THROUGH or sb == THROUGH \
                or sa != sb:
            anomalies.append((fa, fb, sa, sb))
            continue
        uturns.append((fa, fb, sa))
    return tuple(uturns), tuple(anomalies)


def taco_pairs(uturns):
    """Condition 2's constraint OBJECTS -- the constraints the geometry
    IMPOSES, not the ones a given order violates.

    One canonical element per unordered pair of distinct same-side U-turns:

        frozenset({frozenset({fa1, fb1}), frozenset({fa2, fb2})})

    Order-free, which is why the comparison in design spec section 3 needs no
    candidate layer order at all -- and why it cannot go vacuous the way the
    predecessor's subset design did.
    """
    out = set()
    n = len(uturns)
    for i in range(n):
        for j in range(i + 1, n):
            if uturns[i][2] != uturns[j][2]:
                continue                   # opposite sides: arcs cannot meet
            k1 = frozenset((uturns[i][0], uturns[i][1]))
            k2 = frozenset((uturns[j][0], uturns[j][1]))
            if k1 == k2:
                continue
            out.add(frozenset((k1, k2)))
    return out


def pierce_pairs(uturns, sides):
    """Condition 1's constraint objects, in the predecessor's own triple shape
    `(through_face, frozenset({fa, fb}))`.

    Also order-free. The driver uses this for the cross-validation gate: these
    must reproduce the predecessor oracle's `equality` triples on the same
    creases, which makes the new instrument prove itself against an
    already-established result before its condition-2 verdict is believed.
    """
    out = set()
    through = [f for f, s in sides.items() if s == THROUGH]
    for fa, fb, _side in uturns:
        pair = frozenset((fa, fb))
        for f in through:
            if f in pair:
                continue
            out.add((f, pair))
    return out


def pierced(uturn, sides, order):
    """Condition 1 against an order: the THROUGH faces strictly between a
    U-turn's two layers, sorted.

    `order` maps face -> layer index. Only BETWEENNESS is read, so which
    direction the index counts in is irrelevant.
    """
    fa, fb, _side = uturn
    lo, hi = sorted((order[fa], order[fb]))
    return tuple(sorted(f for f, s in sides.items()
                        if s == THROUGH and f not in (fa, fb)
                        and lo < order[f] < hi))


def interleaved(u1, u2, order):
    """Condition 2 against an order: do two U-turns' arcs cross?

    Arcs spanning layers a < c < b < d interleave. Opposite sides are False by
    the rule above. A shared layer reads False, which is the conservative
    direction: a shared layer is a contact, not a crossing.
    """
    if u1[2] != u2[2]:
        return False
    a, b = sorted((order[u1[0]], order[u1[1]]))
    c, d = sorted((order[u2[0]], order[u2[1]]))
    return (a < c < b < d) or (c < a < d < b)


def accepts(sides, uturns, order):
    """Both conditions at one sample point. The violations, empty iff valid.

    Each violation is `("pierced", frozenset({fa, fb}), through_face)` or
    `("interleaved", frozenset({fa, fb}), frozenset({fc, fd}))`.
    """
    out = []
    for u in uturns:
        for f in pierced(u, sides, order):
            out.append(("pierced", frozenset((u[0], u[1])), f))
    n = len(uturns)
    for i in range(n):
        for j in range(i + 1, n):
            if interleaved(uturns[i], uturns[j], order):
                out.append(("interleaved",
                            frozenset((uturns[i][0], uturns[i][1])),
                            frozenset((uturns[j][0], uturns[j][1]))))
    return tuple(out)


def breakpoints(intervals):
    """The sorted, de-duplicated boundaries of a collection of intervals.

    These are the only projections along a line at which the configuration can
    change: between two consecutive boundaries no span starts or ends, so both
    the set of edges containing the point and the set of faces meeting it are
    constant.
    """
    vals = set()
    for lo, hi in intervals:
        vals.add(lo)
        vals.add(hi)
    return tuple(sorted(vals))


def sub_segment_samples(bps):
    """One exact rational midpoint per open sub-segment between consecutive
    breakpoints.

    EXHAUSTIVE BY CONSTRUCTION, which is the whole reason there is no
    sampling-density parameter anywhere in this slice: no configuration change
    can occur strictly inside a sub-segment, so one sample decides all of it.
    """
    return tuple((bps[i] + bps[i + 1]) / 2 for i in range(len(bps) - 1))


def point_at(direction, anchor, t):
    """The point on `anchor`'s line whose projection along `direction` is `t`.

    `lines.project` is the dot product with `direction`, so moving by
    `s * direction` changes the projection by `s * (dx^2 + dy^2)`. Hence from
    `anchor`, whose projection is `t0`, the point at `t` is
    `anchor + ((t - t0) / (dx^2 + dy^2)) * direction`.
    """
    dx, dy = direction
    t0 = lines.project(direction, anchor)
    s = Fraction(t - t0) / (dx * dx + dy * dy)
    return (Fraction(anchor[0]) + s * dx, Fraction(anchor[1]) + s * dy)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -m pytest test_strip.py -v
```

Expected: 33 passed.

- [ ] **Step 5: Re-run Task 1's tests to confirm nothing regressed**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -m pytest test_allowlist.py test_lines.py test_strip.py -v
```

Expected: 57 passed (1 + 19 + 37). ⚠ Updated from the originally planned
51 (1 + 17 + 33): the Task 1 and Task 2 review waves each added tests to close
mutations that survived the planned fixtures — two in `test_lines.py` and four
in `test_strip.py`. The figure to expect is whatever those files now hold; run
them and reconcile rather than assuming.

- [ ] **Step 6: Confirm production is untouched**

```bash
git diff origin/main --stat -- mcp_harness/
```

Expected: no output.

- [ ] **Step 7: Commit**

Write the message to `<scratchpad>/msg-task2.txt`, then:

```bash
git add docs/superpowers/evidence/2026-10-05-cross-section-oracle/strip.py docs/superpowers/evidence/2026-10-05-cross-section-oracle/test_strip.py && git commit -F <scratchpad>/msg-task2.txt
```

---

## Task 3: `cross_section_oracle.py` — input geometry and the ten gates

**Files:**
- Create: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/cross_section_oracle.py`

**Interfaces:**
- Consumes from Tasks 1–2: every name in their Produces blocks.
- Consumes from the predecessor slices, by `sys.path` insertion:
  - `kernel.EXACT` — the exact kernel object, with `.conv(float) -> Fraction`
  - `exact_arrangement.load() -> (ff, polys)`
  - `exact_arrangement.as_tuples(polys, K) -> list[list[tuple]]`
  - `exact_arrangement.fidelity_gate() -> dict` — **returns a dict and raises
    `SystemExit` on failure. Never write `if not fidelity_gate():` — a dict is
    truthy and that line is dead code wearing a gate's name.** Assert on the
    returned figures.
  - `restrict.crease_segments(result, K) -> tuple[(fa, fb, seg), ...]` — M/V only
  - `stacks.is_convex(poly, K) -> bool` — the corrected half-plane form
  - `layer_order.constraints_for(ff) -> (cons, slots)` — a 2-tuple, not a `cons`
  - `layer_certify.clauses(cons) -> tuple[Clause, ...]`
  - `box_pleat.sat_order.solve(cons, slots) -> SatResult` with `.sat`,
    `.relation`, `.verdict.kind`
  - `geom.collinear_overlap(s1, s2, K) -> bool` — **driver-only, as a
    cross-check in gate 8. Never used by the oracle.**
- Produces, for Task 4:
  - `K`, `HERE`, `ART` module constants
  - `load_all() -> dict` with keys `ff`, `polys`, `polymap`, `edges`,
    `creases`, `bundles`, `lines`, `cons`, `relation`, `order`, `census`,
    `tacos`, `sat_kind`
  - `walk_line(d, key, bundle) -> dict` with keys `samples`, `taco_pairs`,
    `pierce_pairs`, `anomalies`, `sub_segments`
  - `gate_fidelity(d) -> dict`, `gate_faces_usable(d) -> dict`,
    `gate_transversal(d) -> dict`, `gate_sides(d) -> dict`,
    `gate_accounting(d) -> dict`, `gate_constancy(d) -> dict`,
    `gate_refuses(d) -> dict`, `gate_untouched() -> dict`

- [ ] **Step 1: Write the driver's load and gate layer**

Create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/cross_section_oracle.py`:

```python
"""Does `layer_certify`'s `taco` clause family mean what it says?

Spec: `../../specs/2026-10-05-cross-section-oracle-design.md`

Run:
    cd docs/superpowers/evidence/2026-10-05-cross-section-oracle
    ../../../../.venv/bin/python3 cross_section_oracle.py

THIS FILE IS THE ONLY ONE ALLOWED TO TOUCH PRODUCTION. `lines.py` and
`strip.py` are import-free by design and by test (spec section 2.3): the
oracle's predicates must not be transcriptions, or the comparison is a
comparison of a copy with its original. What IS shared, necessarily, is the
input geometry -- the folded coordinates and the clipping polygons both come
from production through `exact_arrangement.load()` -- and that sharing lives
here.

TWO ARRAYS, NOT ONE. `load()` returns `(ff, polys)`. Crease segments are read
PER FACE out of `ff.folded_vertices`, which are UNREVERSED; clipping and the
perpendicular clip use `polys`, which the production helper may have REVERSED
to counter-clockwise. Mixing them silently inverts windings, and a clockwise
ring makes every interior test read empty. `restrict.crease_segments` already
reads the right one.
"""
import json
import os
import sys
import time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
_EVID = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(_EVID, "2026-10-04-exact-arrangement"))
sys.path.insert(0, os.path.join(_EVID, "2026-10-04-pointwise-oracle"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "..", "mcp_harness"))
sys.path.insert(0, HERE)

import exact_arrangement               # noqa: E402
import geom                            # noqa: E402
import kernel                          # noqa: E402
import layer_certify                   # noqa: E402
import layer_order                     # noqa: E402
import lines as L                      # noqa: E402
import restrict                        # noqa: E402
import stacks                          # noqa: E402
import strip                           # noqa: E402
from box_pleat import sat_order         # noqa: E402

K = kernel.EXACT
ART = os.path.join(HERE, "cross-section-oracle.json")

#: Edge assignments that fold (a U-turn) and that stay flat (a through pair).
CREASE_KINDS = ("M", "V")
FLAT_KINDS = ("F",)

#: Bounded witness lists keep the artifact readable without hiding a
#: disagreement: the COUNT is always exact, only the examples are capped.
MAX_WITNESSES = 12


def _canon_taco(pq, rs):
    """A production taco entry as the oracle's canonical object.

    `cons.tacos` holds `((p, q), (r, s), prov)` and emits BOTH orders of each
    unordered pair (`layer_order.py:641` and `:644`), so this collapses them to
    one element -- which is why the comparison counts unordered pairs on both
    sides and the two counts are directly comparable.
    """
    return frozenset((frozenset(pq), frozenset(rs)))


def load_all():
    """The folded state, the polygons, every shared edge with its exact folded
    segment, the bundles, the clause set and the certified order.

    `load()` re-folds the witness and `sat_order.solve` costs roughly 30 s, so
    each runs exactly once here and the result is threaded through the gates.
    """
    ff, polys = exact_arrangement.load()
    polys_k = exact_arrangement.as_tuples(polys, K)
    polymap = {i: p for i, p in enumerate(polys_k)}

    # Creases (M/V) come from the helper that reads folded_vertices per face.
    creases = restrict.crease_segments(ff, K)
    crease_by_pair = {frozenset((fa, fb)): seg for fa, fb, seg in creases}

    # Flat edges need the same per-face read. `shared_edges` carries the
    # assignment, so one pass over it covers both kinds and keeps the segment
    # source identical for each.
    folded = [[(K.conv(float(x)), K.conv(float(y))) for x, y in P]
              for P in ff.folded_vertices]
    edges = []
    for fa, fb, k, a in ff.shared_edges:
        face = ff.faces[fa]
        i0, i1 = face.index(k[0]), face.index(k[1])
        edges.append((fa, fb, a, (folded[fa][i0], folded[fa][i1])))
    edges = tuple(edges)

    bundles_map = L.bundles(edges)
    over = L.overlapping_lines(bundles_map, kinds=CREASE_KINDS)

    cons, slots = layer_order.constraints_for(ff)
    all_clauses = layer_certify.clauses(cons)
    census = {}
    for c in all_clauses:
        census[c.family] = census.get(c.family, 0) + 1
    census["TOTAL"] = len(all_clauses)
    del all_clauses

    res = sat_order.solve(cons, slots)
    if not res.sat or res.relation is None:
        raise SystemExit(
            f"REFUSED: the SAT arm returned {res.verdict.kind!r} with no "
            f"relation, so there is no certified order to test. This probe "
            f"tests a CERTIFIED witness; without one it has no subject.")
    # ⚠ THIS BLOCK WAS WRONG AND IS DELETED. It called
    #     order = enumerate_orders.rel_to_order(res.relation,
    #                                           range(len(polys_k)))
    # and refused when that returned None -- which it always does on this
    # subject, for a reason that has nothing to do with the witness.
    # `rel_to_order` needs a COMPLETE tournament, and `sat_order`'s relation
    # spans exactly `cons.pairs`: 53,754 of the 72,010 pairs among 380 faces,
    # because faces whose folded footprints never overlap carry no order
    # variable at all. MEASURED: `set(relation) == set(cons.pairs)`.
    #
    # Nothing needs a total order. The headline comparison is ORDER-FREE --
    # neither `strip.taco_pairs` nor `strip.pierce_pairs` takes one -- and
    # gate 4 builds its own small synthetic orders. So the replacement is a
    # GATE, not an order: `gate_relation_scope` reports the three counts and
    # refuses if the relation and `cons.pairs` ever disagree about which pairs
    # have an order variable.
    #
    # Whether the certified order PASSES this oracle pointwise is a separate
    # question, and this slice does not ask it. Do not add it here.

    return {
        "ff": ff,
        "polys": polys_k,
        "polymap": polymap,
        "edges": edges,
        "creases": creases,
        "crease_by_pair": crease_by_pair,
        "bundles": bundles_map,
        "lines": over,
        "cons": cons,
        "relation": res.relation,
        "census": census,
        "tacos": tuple(_canon_taco(pq, rs) for pq, rs, _p in cons.tacos),
        "sat_kind": res.verdict.kind,
    }


def walk_line(d, key, bundle):
    """One collinear line, walked exhaustively.

    The breakpoints are every edge-span boundary AND every face-span boundary
    on this line: a face can start or stop meeting the line without any crease
    endpoint being there, and omitting those would let a sub-segment contain a
    configuration change -- which is exactly the property the single-sample
    argument rests on.
    """
    direction = L.direction_of(key)
    w = strip.perpendicular(direction)
    anchor = bundle[0][3][0]

    intervals = [L.span(direction, e[3]) for e in bundle]
    faces_here = set()
    for e in bundle:
        faces_here.add(e[0])
        faces_here.add(e[1])

    # A face contributes breakpoints exactly where its intersection WITH THIS
    # LINE starts and ends, so the quantity to clip is the bundle line itself,
    # not the perpendicular. `line_clip` returns the parameter u along
    # `direction` measured from `anchor`, and `project` advances by
    # `|direction|^2` per unit of u, so u converts to projection units by
    #     t = project(direction, anchor) + u * (dx^2 + dy^2).
    #
    # Getting this wrong in the other direction is the dangerous one: a test
    # that EXCLUDES a face which does meet the line shrinks the oracle arm,
    # and a shrunken oracle arm reads as agreement.
    dx, dy = direction
    scale = dx * dx + dy * dy
    t_anchor = L.project(direction, anchor)
    for f, poly in d["polymap"].items():
        hit = strip.line_clip(poly, anchor, direction)
        if hit is None:
            continue
        u_lo, u_hi = hit
        intervals.append((t_anchor + u_lo * scale, t_anchor + u_hi * scale))
        faces_here.add(f)

    bps = strip.breakpoints(intervals)
    samples = strip.sub_segment_samples(bps)

    tacos, pierces, anomalies = set(), set(), []
    for t in samples:
        p = strip.point_at(direction, anchor, t)
        sides = strip.sides_at(d["polymap"], sorted(faces_here), p, w)
        creases_at = strip.edges_at(bundle, direction, t, CREASE_KINDS)
        uturns, anom = strip.uturns_at(creases_at, sides)
        anomalies.extend((str(key), str(t)) + tuple(map(str, a))
                         for a in anom)
        tacos |= strip.taco_pairs(uturns)
        pierces |= strip.pierce_pairs(uturns, sides)

    return {
        "samples": len(samples),
        "sub_segments": len(bps) - 1 if bps else 0,
        "taco_pairs": tacos,
        "pierce_pairs": pierces,
        "anomalies": tuple(anomalies),
    }


def gate_fidelity(d):
    """GATE 1. The transcription's arrangement cells are bitwise identical to
    production's.

    `fidelity_gate()` RETURNS A DICT and raises `SystemExit` on failure, so a
    truthiness test on it is dead code. Assert on the figures it returns.
    """
    r = exact_arrangement.fidelity_gate()
    if not r.get("bitwise_identical"):
        raise SystemExit(f"GATE 1 FAILED: cells not bitwise identical: {r}")
    if r.get("production_cells", 0) <= 0:
        raise SystemExit(
            f"GATE 1 FAILED: zero production cells, so 'identical' is "
            f"vacuous: {r}")
    return r


def gate_faces_usable(d):
    """GATE 2. Every face is a strictly counter-clockwise convex exact ring.

    `stacks.is_convex` is the CORRECTED half-plane form: at least three
    vertices, strictly positive shoelace area, and every vertex weakly left of
    every directed edge. An earlier turn-sign version admitted a clockwise
    square, a pentagram, an all-collinear ring and an empty list -- and a
    clockwise ring makes every interior test read empty, so the oracle would
    miss intruders and accept bad orders. Silent failure in the dangerous
    direction.
    """
    bad, non_rational = [], []
    for i, poly in enumerate(d["polys"]):
        if not all(isinstance(c, Fraction) for v in poly for c in v):
            non_rational.append(i)
        if not stacks.is_convex(poly, K):
            bad.append(i)
    if bad or non_rational:
        raise SystemExit(
            f"GATE 2 FAILED: non-convex faces {bad[:MAX_WITNESSES]}, "
            f"non-rational faces {non_rational[:MAX_WITNESSES]}")
    return {"faces_checked": len(d["polys"]), "non_convex": 0,
            "non_rational": 0}


def gate_transversal(d):
    """GATE 7. Every taco clause is over a COLLINEAR crease pair.

    The oracle sees lines; a transversal taco is invisible to it. The scoping
    measurement found zero on this subject, and if that ever changes the probe
    must STOP rather than silently under-report its coverage.
    """
    coll, trans, missing = 0, [], []
    for pq, rs, _prov in d["cons"].tacos:
        s1 = d["crease_by_pair"].get(frozenset(pq))
        s2 = d["crease_by_pair"].get(frozenset(rs))
        if s1 is None or s2 is None:
            missing.append((tuple(pq), tuple(rs)))
            continue
        k1, k2 = L.line_key(s1), L.line_key(s2)
        if k1 == k2 and L.intervals_overlap(L.span(L.direction_of(k1), s1),
                                            L.span(L.direction_of(k1), s2)):
            coll += 1
        else:
            trans.append((tuple(pq), tuple(rs)))
    if trans or missing:
        raise SystemExit(
            f"GATE 7 FAILED: {len(trans)} transversal and {len(missing)} "
            f"unresolved taco crease pairs. The oracle cannot see transversal "
            f"pairs, so continuing would under-report coverage and call it "
            f"agreement. Witnesses: {trans[:MAX_WITNESSES]} / "
            f"{missing[:MAX_WITNESSES]}")
    if coll == 0:
        raise SystemExit(
            "GATE 7 FAILED: zero collinear taco clauses, so the comparison "
            "has no population and 'identical' would be vacuous.")
    return {"taco_clauses": len(d["cons"].tacos), "collinear": coll,
            "transversal": 0, "unresolved": 0}


def gate_sides(d):
    """GATE 8. Two measurements, neither of which the oracle relies on.

    (a) CROSS-CHECK the oracle's own bundling against the transcription
        `geom.collinear_overlap` (`geom.py:359`). This is control C2 of spec
        section 1.2 promoted to a gate. It is a CROSS-CHECK and not the
        oracle's machinery -- using that predicate to bundle would make the
        bundling common-mode, so it is called here and nowhere else.

    (b) The SAME-SIDE census behind the pre-registered prediction of spec
        section 6: `layer_order.py:633-646` applies no side test while its
        sibling `:590-611` does, so opposite-side collinear crease pairs
        should surface in `only_production`. Reported either way, so the run
        can falsify the prediction instead of explaining it afterwards.
    """
    agree = disagree = 0
    for pq, rs, _prov in d["cons"].tacos:
        s1 = d["crease_by_pair"][frozenset(pq)]
        s2 = d["crease_by_pair"][frozenset(rs)]
        k1, k2 = L.line_key(s1), L.line_key(s2)
        mine = (k1 == k2
                and L.intervals_overlap(L.span(L.direction_of(k1), s1),
                                        L.span(L.direction_of(k1), s2)))
        theirs = geom.collinear_overlap(s1, s2, K)
        if bool(mine) == bool(theirs):
            agree += 1
        else:
            disagree += 1
    if disagree:
        raise SystemExit(
            f"GATE 8 FAILED: the oracle's bundling and the transcription "
            f"`geom.collinear_overlap` disagree on {disagree} taco crease "
            f"pairs. One of the two is wrong and the comparison cannot be "
            f"read until that is resolved.")

    same = opposite = indeterminate = 0
    for pq, rs, _prov in d["cons"].tacos:
        s1 = d["crease_by_pair"][frozenset(pq)]
        s2 = d["crease_by_pair"][frozenset(rs)]
        key = L.line_key(s1)
        if key != L.line_key(s2):
            continue
        direction = L.direction_of(key)
        w = strip.perpendicular(direction)
        i1 = L.span(direction, s1)
        i2 = L.span(direction, s2)
        t = (max(i1[0], i2[0]) + min(i1[1], i2[1])) / 2
        p = strip.point_at(direction, s1[0], t)
        try:
            sides = strip.sides_at(
                d["polymap"], sorted(set(pq) | set(rs)), p, w)
        except ValueError:
            indeterminate += 1
            continue
        s_pq = {sides.get(f) for f in pq}
        s_rs = {sides.get(f) for f in rs}
        if len(s_pq) != 1 or len(s_rs) != 1 or None in s_pq | s_rs:
            indeterminate += 1
        elif s_pq == s_rs:
            same += 1
        else:
            opposite += 1
    return {"bundling_cross_check_agree": agree,
            "bundling_cross_check_disagree": 0,
            "same_side": same, "opposite_side": opposite,
            "indeterminate": indeterminate}


def gate_accounting(d):
    """GATE 5. Exhaustive accounting: every line visited, every edge placed.

    Reconciles the bundle contents against the total edge count, so an edge
    lost in bundling cannot shrink the oracle's arm unnoticed. A smaller
    oracle arm reads as agreement, which is why this is a gate and not a log
    line.
    """
    placed = sum(len(v) for v in d["bundles"].values())
    if placed != len(d["edges"]):
        raise SystemExit(
            f"GATE 5 FAILED: {placed} edges placed in bundles but "
            f"{len(d['edges'])} exist. A lost edge shrinks the oracle arm and "
            f"reads as agreement.")
    creases = sum(1 for e in d["edges"] if e[2] in CREASE_KINDS)
    flats = sum(1 for e in d["edges"] if e[2] in FLAT_KINDS)
    if len(d["lines"]) == 0:
        raise SystemExit(
            "GATE 5 FAILED: zero crease-overlapping lines, so the oracle has "
            "nothing to walk and any verdict would be vacuous.")
    return {"edges": len(d["edges"]), "edges_placed": placed,
            "bundle_lines": len(d["bundles"]),
            "crease_overlapping_lines": len(d["lines"]),
            "creases": creases, "flat_edges": flats}


def gate_constancy(d):
    """GATE 3. The configuration really is constant inside a sub-segment, AND
    it really can change across a breakpoint.

    THE POSITIVE CONTROL IS THE POINT. The predecessor's version of this gate
    read "constant" because all three of its probes landed off the face, so it
    certified a fixture that proved nothing. Here the same walk must find at
    least one sub-segment boundary across which the strand set DIFFERS, or the
    constancy half is unfalsifiable and the gate refuses.
    """
    constant = varied = 0
    for key in d["lines"]:
        bundle = d["bundles"][key]
        direction = L.direction_of(key)
        w = strip.perpendicular(direction)
        anchor = bundle[0][3][0]
        intervals = [L.span(direction, e[3]) for e in bundle]
        bps = strip.breakpoints(intervals)
        samples = strip.sub_segment_samples(bps)
        faces = sorted({f for e in bundle for f in (e[0], e[1])})

        def _read(t):
            p = strip.point_at(direction, anchor, t)
            return tuple(sorted(strip.sides_at(d["polymap"], faces, p,
                                               w).items()))

        prev = None
        for i, t in enumerate(samples):
            lo, hi = bps[i], bps[i + 1]
            three = (lo + (t - lo) / 2, t, t + (hi - t) / 2)
            readings = {_read(x) for x in three}
            if len(readings) == 1:
                constant += 1
            else:
                raise SystemExit(
                    f"GATE 3 FAILED: the strand set is NOT constant inside "
                    f"sub-segment {i} of line {key}: {len(readings)} distinct "
                    f"readings. The single-sample argument does not hold and "
                    f"the oracle's exhaustiveness claim is void.")
            cur = _read(t)
            if prev is not None and cur != prev:
                varied += 1
            prev = cur
    if varied == 0:
        raise SystemExit(
            "GATE 3 FAILED (positive control): no sub-segment boundary "
            "changed the strand set anywhere. A constancy check that cannot "
            "observe a change is unfalsifiable -- which is exactly how this "
            "gate passed vacuously in the predecessor slice.")
    return {"sub_segments_constant": constant, "boundaries_that_varied": varied}


def gate_refuses(d):
    """GATE 4. The oracle rejects what it must. Both controls required.

    (a) SEEDED INTERLEAVING: take a real line with two same-side U-turns and
        reorder the four faces so their arcs cross. `accepts` must report it.
    (b) INTRUDER: place a THROUGH strand between a real U-turn's layers.
        `accepts` must report it.

    A probe that accepts everything passes every other gate in this file, so
    without these two the run proves nothing.
    """
    seeded = intruder = 0
    witness = None
    for key in d["lines"]:
        bundle = d["bundles"][key]
        direction = L.direction_of(key)
        w = strip.perpendicular(direction)
        anchor = bundle[0][3][0]
        intervals = [L.span(direction, e[3]) for e in bundle]
        for t in strip.sub_segment_samples(strip.breakpoints(intervals)):
            p = strip.point_at(direction, anchor, t)
            faces = sorted({f for e in bundle for f in (e[0], e[1])})
            sides = strip.sides_at(d["polymap"], faces, p, w)
            uturns, _a = strip.uturns_at(
                strip.edges_at(bundle, direction, t, CREASE_KINDS), sides)
            if len(uturns) < 2:
                continue
            (a1, b1, s1), (a2, b2, s2) = uturns[0], uturns[1]
            if s1 != s2:
                continue
            crossed = {a1: 0, a2: 1, b1: 2, b2: 3}
            if strip.accepts(sides, uturns[:2], crossed):
                seeded += 1
                witness = {"line": str(key), "t": str(t),
                           "uturns": [[a1, b1], [a2, b2]],
                           "crossed_order": {str(k): v
                                             for k, v in crossed.items()}}
            fake_sides = dict(sides)
            fake_sides[-1] = strip.THROUGH
            fake_order = {a1: 0, -1: 1, b1: 2}
            if strip.accepts(fake_sides, ((a1, b1, s1),), fake_order):
                intruder += 1
            if seeded and intruder:
                break
        if seeded and intruder:
            break
    if not seeded:
        raise SystemExit(
            "GATE 4 FAILED: no seeded interleaving was rejected. An oracle "
            "that accepts a crossing cannot distinguish a valid order from an "
            "invalid one, so every other figure in this run is meaningless.")
    if not intruder:
        raise SystemExit(
            "GATE 4 FAILED: the intruder control was not rejected.")
    return {"seeded_interleaving_rejected": seeded,
            "intruder_rejected": intruder, "seeded_witness": witness}


def gate_untouched():
    """GATE 10. Production is untouched.

    Asserted in code rather than left to a reviewer's eye, because every slice
    in this arc carries the same standing constraint and a diff that appears
    between a review and a push would otherwise go unnoticed.
    """
    import subprocess
    root = os.path.join(HERE, "..", "..", "..", "..")
    diff = subprocess.run(
        ["git", "-C", root, "diff", "origin/main", "--stat", "--",
         "mcp_harness/"],
        capture_output=True, text=True, check=True).stdout.strip()
    if diff:
        raise SystemExit(
            f"GATE 10 FAILED: mcp_harness/ differs from origin/main:\n{diff}")
    with open(os.path.join(root, "mcp_harness", "server.py")) as fh:
        hits = fh.read().count("box_pleat")
    if hits != 0:
        raise SystemExit(
            f"GATE 10 FAILED: server.py mentions box_pleat {hits} times; the "
            f"standing constraint is 0.")
    return {"mcp_harness_diff_empty": True, "server_box_pleat_mentions": 0}
```

- [ ] **Step 2: Verify the driver imports and the gates run**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -c "
import cross_section_oracle as P
d = P.load_all()
print('sat', d['sat_kind'])
print('edges', len(d['edges']), 'creases', len(d['creases']))
print('bundle lines', len(d['bundles']), 'overlapping', len(d['lines']))
print('census', d['census'])
print('tacos canonical', len(d['tacos']))
print('G1', P.gate_fidelity(d))
print('G2', P.gate_faces_usable(d))
print('G5', P.gate_accounting(d))
print('G7', P.gate_transversal(d))
print('G10', P.gate_untouched())
"
```

Expected: `sat CERTIFIED`; `creases 745`; `overlapping 29`;
`census` reporting `taco` 74,602 and `equality` 28,192; `G7` reporting
`collinear 74602, transversal 0`; every gate returning a dict with no
`SystemExit`.

**If `overlapping` is not 29 or `G7`'s `collinear` is not 74,602, STOP and
report.** Those two numbers were measured independently before this plan was
written (spec §1.1, with three controls in §1.2); a different reading means
either the bundling or the segment source is wrong, and the comparison in
Task 4 cannot be read until it is resolved. Do not adjust the expected figure
to match the code.

- [ ] **Step 3: Verify the slow gates run**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -c "
import cross_section_oracle as P
d = P.load_all()
print('G3', P.gate_constancy(d))
print('G4', P.gate_refuses(d))
print('G8', P.gate_sides(d))
"
```

Expected: `G3` reporting a non-zero `sub_segments_constant` **and** a non-zero
`boundaries_that_varied`; `G4` reporting both controls rejected; `G8`
reporting `bundling_cross_check_disagree 0` and the same/opposite census.

- [ ] **Step 4: Confirm production is untouched**

```bash
git diff origin/main --stat -- mcp_harness/
```

Expected: no output.

- [ ] **Step 5: Commit**

Write the message to `<scratchpad>/msg-task3.txt`, then:

```bash
git add docs/superpowers/evidence/2026-10-05-cross-section-oracle/cross_section_oracle.py && git commit -F <scratchpad>/msg-task3.txt
```

---

## Task 4: The comparison, the cross-validation gate, the artifact and the write-up

**Files:**
- Modify: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/cross_section_oracle.py` (append)
- Create: `docs/superpowers/evidence/2026-10-05-cross-section-oracle/README.md`
- Create (by running): `docs/superpowers/evidence/2026-10-05-cross-section-oracle/cross-section-oracle.json`

**Interfaces:**
- Consumes from Task 3: every name in its Produces block, **plus two added
  during Task 3's review that `run()` MUST call and the plan text above does
  not mention**: `gate_relation_scope(d) -> dict` (register it in `gates`
  under `"relation_scope"`) and `taco_counts(d) -> dict` (its
  `taco_entries_ordered` and `taco_pairs_unordered` keys belong in the
  artifact — gate 7 counts ORDERED entries, the comparison counts UNORDERED
  pairs, and a reader comparing the two without both numbers will think one
  went missing).
- Produces: `compare(oracle_pairs, production_pairs) -> dict`,
  `gate_crossvalidate(d, pierces) -> dict`, `run() -> dict`,
  `selftest() -> dict`, `main(out_path) -> None`

- [ ] **Step 1: Append the comparison, the cross-validation gate, the runner and the selftest**

Append to `cross_section_oracle.py`:

```python
def compare(oracle_pairs, production_pairs):
    """The set comparison of spec section 3, in both directions.

    Order-free on both sides: the oracle's elements come from geometry alone
    and production's from `cons.tacos`, so no candidate layer order enters.
    That is what makes this comparison incapable of going vacuous the way the
    predecessor's subset design did -- there is no sampled population to be
    empty.

    `only_oracle` non-empty  -> production's taco branch is INCOMPLETE.
    `only_production` non-empty -> production OVER-CONSTRAINS.
    """
    o, p = set(oracle_pairs), set(production_pairs)
    only_o, only_p = o - p, p - o

    def _w(s):
        return [sorted(sorted(x) for x in pair)
                for pair in sorted(s, key=lambda q: sorted(sorted(x)
                                                           for x in q))
                ][:MAX_WITNESSES]

    return {
        "oracle_pairs": len(o),
        "production_pairs": len(p),
        "identical": only_o == set() and only_p == set(),
        "only_oracle": len(only_o),
        "only_production": len(only_p),
        "only_oracle_witnesses": _w(only_o),
        "only_production_witnesses": _w(only_p),
    }


def gate_crossvalidate(d, pierces):
    """GATE 9. The strip's CONDITION 1 must reproduce the predecessor oracle's
    `equality` triples, on the creases it shares with them.

    This is what earns the condition-2 verdict its credibility: a brand-new
    instrument reproducing an already-established exhaustive result
    (28,192 = 28,192, zero either way) before anyone reads its new answer.

    Production's `equality` clauses carry the same information in the same
    shape, so the comparison is direct: `(through_face, {fa, fb})`.

    GATED NON-VACUOUS. The reproduced count must be > 0, or the control
    establishes nothing -- which is the failure mode this arc has hit twice.
    """
    prod = set()
    for la, lb, _prov in d["cons"].equalities:
        pa, pb = la[0], lb[0]
        shared = set(pa) & set(pb)
        if len(shared) != 1:
            continue
        x = shared.pop()
        fa = (set(pa) - {x}).pop()
        fb = (set(pb) - {x}).pop()
        prod.add((x, frozenset((fa, fb))))

    creases_on_lines = {frozenset((e[0], e[1]))
                        for key in d["lines"] for e in d["bundles"][key]
                        if e[2] in CREASE_KINDS}
    prod_here = {t for t in prod if t[1] in creases_on_lines}

    if not prod_here:
        raise SystemExit(
            "GATE 9 FAILED: production has no `equality` clause on any of the "
            "crease-overlapping lines, so the cross-validation control has an "
            "empty population and would pass vacuously.")
    if not pierces:
        raise SystemExit(
            "GATE 9 FAILED: the strip produced no condition-1 constraints on "
            "those lines while production has "
            f"{len(prod_here)}. The instrument is not reading the geometry.")

    only_o, only_p = pierces - prod_here, prod_here - pierces
    out = {
        "oracle_condition1": len(pierces),
        "production_equality_on_these_lines": len(prod_here),
        "only_oracle": len(only_o),
        "only_production": len(only_p),
        "reproduced": len(pierces & prod_here),
        "identical": not only_o and not only_p,
    }
    if not out["identical"]:
        out["only_oracle_witnesses"] = [
            [w[0], sorted(w[1])] for w in sorted(only_o)][:MAX_WITNESSES]
        out["only_production_witnesses"] = [
            [w[0], sorted(w[1])] for w in sorted(only_p)][:MAX_WITNESSES]
    return out


def run():
    """Every gate, then the comparison. The artifact's whole body."""
    t0 = time.time()
    d = load_all()
    gates = {
        "fidelity": gate_fidelity(d),
        "faces_usable": gate_faces_usable(d),
        "accounting": gate_accounting(d),
        "transversal": gate_transversal(d),
        "sides": gate_sides(d),
        "constancy": gate_constancy(d),
        "refuses": gate_refuses(d),
        "untouched": gate_untouched(),
    }

    oracle_tacos, oracle_pierces, anomalies = set(), set(), []
    per_line = []
    for key in d["lines"]:
        r = walk_line(d, key, d["bundles"][key])
        oracle_tacos |= r["taco_pairs"]
        oracle_pierces |= r["pierce_pairs"]
        anomalies.extend(r["anomalies"])
        per_line.append({"line": str(key), "samples": r["samples"],
                         "sub_segments": r["sub_segments"],
                         "taco_pairs": len(r["taco_pairs"])})

    if anomalies:
        raise SystemExit(
            f"REFUSED: {len(anomalies)} crease(s) read with faces on opposite "
            f"sides or a THROUGH face at a sample point. A crease's two faces "
            f"lie on one side by definition, so this is a disagreement about "
            f"which pairs are interpretable and must be resolved before the "
            f"comparison is read. Witnesses: {anomalies[:MAX_WITNESSES]}")

    headline = compare(oracle_tacos, d["tacos"])
    gates["crossvalidate"] = gate_crossvalidate(d, oracle_pierces)

    geometric = d["census"].get("equality", 0) + d["census"].get("taco", 0)
    return {
        "subject": "dense lizard (SAT-certified witness)",
        "kernel": "exact",
        "sat_verdict": d["sat_kind"],
        "faces": len(d["polys"]),
        "creases": len(d["creases"]),
        "edges": len(d["edges"]),
        "collinear_lines": len(d["lines"]),
        "clause_census": d["census"],
        "geometric_clauses": geometric,
        "taco_share_of_geometric": (round(d["census"].get("taco", 0)
                                          / geometric, 4)
                                    if geometric else None),
        "headline_comparison": headline,
        "verdict": "identical" if headline["identical"] else "DISAGREEMENT",
        "families_independently_checked": ["taco"],
        "families_cross_validated": ["equality"],
        "families_not_under_test": ["transitivity"],
        "gates": gates,
        "per_line": per_line,
        "python": ".".join(str(x) for x in sys.version_info[:3]),
        "sys_platform": sys.platform,
        "elapsed_secs": round(time.time() - t0, 1),
    }


def selftest():
    """Checks on the probe itself, run before the subject is touched.

    Every one of these is a property a bug could break while leaving the
    headline looking plausible.
    """
    F = Fraction
    checks = {}

    def rect(x0, y0, x1, y1):
        return [(F(x0), F(y0)), (F(x1), F(y0)), (F(x1), F(y1)), (F(x0), F(y1))]

    # 1-3: line identity.
    checks["line_key_collinear_equal"] = (
        L.line_key(((F(0), F(0)), (F(2), F(0))))
        == L.line_key(((F(9), F(0)), (F(4), F(0)))))
    checks["line_key_offset_differs"] = (
        L.line_key(((F(0), F(0)), (F(2), F(0))))
        != L.line_key(((F(0), F(1)), (F(2), F(1)))))
    checks["line_key_none_degenerate"] = (
        L.line_key(((F(1), F(1)), (F(1), F(1)))) is None)

    # 4-6: the cross-section.
    w = strip.perpendicular((1, 0))
    checks["side_through"] = (
        strip.side_at(rect(0, -1, 2, 1), (F(1), F(0)), w) == strip.THROUGH)
    checks["side_pos"] = (
        strip.side_at(rect(0, 0, 2, 1), (F(1), F(0)), w) == strip.SIDE_POS)
    checks["side_neg"] = (
        strip.side_at(rect(0, -1, 2, 0), (F(1), F(0)), w) == strip.SIDE_NEG)

    # 7: a clockwise ring must NOT read as a usable face. This is the defect
    # that the predecessor's first is_convex missed.
    cw = list(reversed(rect(0, 0, 2, 1)))
    checks["clockwise_ring_rejected"] = not stacks.is_convex(cw, K)

    # 8-10: the two conditions.
    nested = {0: 0, 2: 1, 3: 2, 1: 3}
    crossed = {0: 0, 2: 1, 1: 2, 3: 3}
    u = ((0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_POS))
    checks["nested_accepted"] = not strip.interleaved(u[0], u[1], nested)
    checks["crossed_rejected"] = strip.interleaved(u[0], u[1], crossed)
    checks["cross_side_accepted"] = not strip.interleaved(
        (0, 1, strip.SIDE_POS), (2, 3, strip.SIDE_NEG), crossed)

    # 11: the emission is order-free.
    checks["taco_pairs_order_free"] = (
        strip.taco_pairs(u) == strip.taco_pairs((u[1], u[0])))

    # 12: a pierce is found and a non-pierce is not.
    sides = {0: strip.SIDE_POS, 1: strip.SIDE_POS, 5: strip.THROUGH}
    checks["pierce_found"] = strip.pierced(
        (0, 1, strip.SIDE_POS), sides, {0: 0, 5: 1, 1: 2}) == (5,)
    checks["pierce_outside_ignored"] = strip.pierced(
        (0, 1, strip.SIDE_POS), sides, {0: 0, 1: 1, 5: 2}) == ()

    # 13-14: exhaustive sampling.
    bps = strip.breakpoints([(F(0), F(2)), (F(1), F(3))])
    checks["breakpoints_sorted_unique"] = bps == (F(0), F(1), F(2), F(3))
    checks["samples_strictly_inside"] = all(
        bps[i] < t < bps[i + 1]
        for i, t in enumerate(strip.sub_segment_samples(bps)))

    # 15: point_at inverts project.
    checks["point_at_inverts_project"] = all(
        L.project((1, 2), strip.point_at((1, 2), (F(1), F(1)), F(t))) == F(t)
        for t in (-3, 0, 4))

    # 16: `compare` is not a constant. A comparator that always reports
    # identical would reproduce this run's best outcome exactly.
    a = {frozenset((frozenset((0, 1)), frozenset((2, 3))))}
    b = {frozenset((frozenset((0, 1)), frozenset((4, 5))))}
    checks["compare_detects_difference"] = (
        not compare(a, b)["identical"]
        and compare(a, b)["only_oracle"] == 1
        and compare(a, b)["only_production"] == 1)
    checks["compare_detects_identity"] = compare(a, a)["identical"]

    failed = sorted(k for k, v in checks.items() if not v)
    if failed:
        raise SystemExit(f"SELFTEST FAILED: {failed}")
    return {"checks": len(checks), "passed": len(checks)}


def main(out_path=ART):
    st = selftest()
    print(f"selftest: {st['passed']}/{st['checks']}")
    result = run()
    result["selftest"] = st
    with open(out_path, "w") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print(json.dumps({k: result[k] for k in
                      ("verdict", "headline_comparison", "collinear_lines",
                       "taco_share_of_geometric")},
                     indent=2, sort_keys=True))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the selftest alone first**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -c "
import cross_section_oracle as P
print(P.selftest())
"
```

Expected: `{'checks': 18, 'passed': 18}`.

- [ ] **Step 3: Run the full probe**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 cross_section_oracle.py
```

Expected: `selftest: 18/18`, then a JSON summary and
`wrote .../cross-section-oracle.json`.

**Record the verdict exactly as it comes out.** `identical`, `only_oracle`
non-zero (production incomplete) and `only_production` non-zero (production
over-constrains) are all publishable results. **Do not tune any gate or
predicate to reach a particular verdict** — loosening a gate to reach a
headline is this project's named recurring failure mode.

- [ ] **Step 4: Verify the artifact reproduces bit-identically**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 cross_section_oracle.py && cp cross-section-oracle.json /tmp/cso-1.json && ../../../../.venv/bin/python3 cross_section_oracle.py && ../../../../.venv/bin/python3 -c "
import json
a = json.load(open('/tmp/cso-1.json'))
b = json.load(open('cross-section-oracle.json'))
a.pop('elapsed_secs'); b.pop('elapsed_secs')
assert a == b, 'ARTIFACT NOT REPRODUCIBLE'
print('artifact reproduces bit-identically except elapsed_secs')
"
```

Expected: `artifact reproduces bit-identically except elapsed_secs`.

- [ ] **Step 5: Run both unit test files**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -m pytest test_allowlist.py test_lines.py test_strip.py -v
```

Expected: 57 passed (1 + 19 + 37). ⚠ Updated from the originally planned
51 (1 + 17 + 33): the Task 1 and Task 2 review waves each added tests to close
mutations that survived the planned fixtures — two in `test_lines.py` and four
in `test_strip.py`. The figure to expect is whatever those files now hold; run
them and reconcile rather than assuming.

- [ ] **Step 6: Write `README.md`**

Create `docs/superpowers/evidence/2026-10-05-cross-section-oracle/README.md`
with these sections, **every figure read from `cross-section-oracle.json` and
none from this plan**:

1. **The question** — `layer_certify._satisfied`'s `taco` predicate quoted, its
   producer at `layer_order.py:633-646` named, and what the predecessor slice
   left open.
2. **The verdict** — the headline table: oracle pairs, production pairs,
   `only_oracle`, `only_production`, and the verdict string.
3. **Why the named successor was not built** — the three refutations of
   arXiv:1601.05747 with the two verbatim quotes (the `strictly` definition and
   the `non-wrapping` precondition). ⚠ The third — that thickness is strictly
   stronger than flat-foldability — must be **qualified, not asserted**: it
   restates the second as a universal on an unsupported premise, so the first
   two carry the conclusion. **Credit the correction: the paper was cited in the
   predecessor spec as "Tachi & Hull" without being read.**
4. **The oracle** — the cross-section construction, the strand table, and the
   two conditions.
5. **Independence, bounded** — spec §2.3's boundary, naming the input geometry
   as the irreducible common-mode residue and stating that no oracle predicate
   is a transcription.
6. **The scoping measurement** — 74,602 of 74,602 collinear, zero transversal,
   29 lines, with the three controls; and the explicit note that the
   predecessor's "subsumption holds for the transversal arm" is **true and
   vacuous here**.
7. **The pre-registered prediction and its outcome** — gate 8's same-side /
   opposite-side census against spec §6, said plainly whichever way it fell.
8. **Gates** — all ten, with their reported figures, and one line each on the
   defect that made the gate necessary.
9. **Limitations** — spec §8's eight items, carried over without softening.
10. **Reproducing** — the exact commands.

- [ ] **Step 7: Reconcile every README figure against the artifact**

```bash
cd docs/superpowers/evidence/2026-10-05-cross-section-oracle && ../../../../.venv/bin/python3 -c "
import json, re
art = json.load(open('cross-section-oracle.json'))
flat = {}
def walk(o, p=''):
    if isinstance(o, dict):
        for k, v in o.items(): walk(v, p + '.' + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): walk(v, p + '[%d]' % i)
    else:
        flat[p] = o
walk(art)
nums = {str(v) for v in flat.values() if isinstance(v, (int, float))}
nums |= {format(v, ',') for v in flat.values() if isinstance(v, int)}
text = open('README.md').read()
found = set(re.findall(r'\b[0-9][0-9,]*(?:\.[0-9]+)?\b', text))
unmatched = sorted(f for f in found if f not in nums and f.replace(',', '') not in nums)
print('figures in README:', len(found))
print('NOT FOUND IN ARTIFACT:', unmatched)
"
```

Review every entry in `NOT FOUND IN ARTIFACT`. Line numbers (`633`, `646`,
`590`, `613`, `311`, `250`), years (`2016`, `2004`, `2024`), the arXiv id and
page ranges are expected there. **Any count or measurement in that list is a
figure the artifact does not support — fix the README, never the artifact.**

- [ ] **Step 8: Confirm production is untouched**

```bash
git diff origin/main --stat -- mcp_harness/ && grep -c box_pleat mcp_harness/server.py || true
```

Expected: no diff output, then `0`.

- [ ] **Step 9: Commit**

Write the message to `<scratchpad>/msg-task4.txt`, then:

```bash
git add docs/superpowers/evidence/2026-10-05-cross-section-oracle/ && git commit -F <scratchpad>/msg-task4.txt
```

---

## Self-Review

Run against the spec after Task 4.

**1. Spec coverage.**

| spec section | task |
|---|---|
| §0 prior art, §0.4 corrections | already committed in `98904786` |
| §1 the question, §1.3 census | Task 3 `load_all` census; Task 4 README §1 |
| §1.1 scoping, §1.2 controls | Task 3 gate 7 + gate 8(a); Task 4 README §6 |
| §2.1 construction | Task 2 `line_clip`, `side_at`, `sides_at`; Task 3 `walk_line` |
| §2.2 validity rule | Task 2 `pierced`, `interleaved`, `accepts` |
| §2.3 independence | Task 1 `conftest.assert_import_allowlist` + `test_allowlist.py`'s control; Tasks 1–2 allowlist tests; Task 4 README §5 |
| §3 comparison | Task 4 `compare` |
| §4.1 files | all four tasks |
| §4.2 reuse | Task 3 imports |
| §4.3 data flow | Task 3 `load_all` + Task 4 `run` |
| §5 gates 1–10 | gates 1,2,5,7,10 Task 3 step 2; 3,4,8 Task 3 step 3; 6 Task 4 step 4; 9 Task 4 `gate_crossvalidate` |
| §6 prediction | Task 3 `gate_sides`; Task 4 README §7 |
| §7 scope | Global Constraints + Task 3 gate 7 and gate 10 |
| §8 limitations | Task 4 README §9 |
| §9 successor | Task 4 README, from the measured verdict |

No gap.

**2. Placeholder scan.** No `TBD`, no "add error handling", no "similar to
Task N". Every code step carries the code; every command carries its expected
output. Each refusal path has its message written out.

**3. Type consistency.** `seg` is `((Fraction, Fraction), (Fraction, Fraction))`
everywhere. An `edge` is `(fa, fb, assignment, seg)` in `lines.bundles`,
`strip.edges_at`, `strip.uturns_at` and the driver. A `uturn` is
`(fa, fb, side)` in `uturns_at`, `taco_pairs`, `pierce_pairs`, `pierced`,
`interleaved` and `accepts`. A taco object is
`frozenset({frozenset, frozenset})` in `strip.taco_pairs` and
`cross_section_oracle._canon_taco`. A pierce object is
`(int, frozenset)` in `strip.pierce_pairs` and `gate_crossvalidate`.
`order` maps `face -> int` in every consumer. `lines.direction_of` feeds
`strip.perpendicular`, `lines.project`, `lines.span` and `strip.point_at`,
all taking `direction` first.

**4. Known risks to watch during execution.**

- `walk_line`'s face-breakpoint loop calls `line_clip` once per face per line.
  That is 380 × 29 = 11,020 calls, which is cheap, but the predecessor peaked
  at 2,454 MB and this driver holds the same clause census. If memory is the
  binding constraint, the `transitivity` clauses are the cause and
  `layer_certify.clauses` can be replaced by a census-only pass over
  `_iter_clauses` — **report before changing it**, since the census is an
  artifact figure.
- Gate 4 mutates a copy of `sides` with the synthetic key `-1`. No real face
  index is negative, so it cannot collide; if `polymap` ever gains negative
  keys this control silently stops testing what it claims. Asserted implicitly
  by `faces_usable` enumerating `0..len(polys)-1`.
- Four defects were found in this plan by hand-executing its own fixtures
  before dispatch, and are already fixed above: a two-point ring that does not
  actually go unbounded, a triangle the perpendicular crosses rather than
  touches, three wrong expected test counts, and `walk_line` asking the wrong
  clip question about which faces meet the line. The last is the one that
  mattered — it could have excluded a face that does meet the line, shrinking
  the oracle arm into a false agreement.

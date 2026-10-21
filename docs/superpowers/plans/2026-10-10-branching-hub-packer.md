# Branching hub graphs in Pleatwright's packer: implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pack trees whose hubs (branch points) branch, such as a head carrying
two forked antlers, so they fold like the 51 artifact trees. The 51 artifact
outputs must stay byte-identical.

**Architecture:** A new `pleatwright/nest.py` lays out only branching hub
graphs. Every hub owns a rectangular pocket. A child hub's river is the
L-infinity offset band along the non-paper sides of its strip, and a mirrored
pair of hub subtrees shares one strip split at x = N/2. `pack.candidates`
dispatches to it. Path-shaped graphs keep today's code untouched. `base.build`
learns that one region may be several rectangles. PR #204's `chain_problem`
guard is retired.

**Tech Stack:** Python 3.14 (CI) with pytest; FastAPI app tests; React/vitest
for one web test. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md`
(commit 632d1139). Read it before Task 1.

**Prototype provenance:** every code block for `pack.py`, `base.py` and
`nest.py` below was run on 2026-10-10 in a scratch worktree, along with the
expected values the tests assert. Results:

* `antlered("dog_0")`: asymmetric rung, N=62, first candidate; end to end
  368/368 flat-foldable, global CERTIFIED, similarity 0.994, 28 s;
* the two CI-pinned `packing_cp.svg` hashes still pass;
* across 109 branching named edits, 106 pack within the pipeline's grid cap.
  The 3 misses (`toed` crab_3, elephant_3, spider_2) certify above the cap,
  at N = 108, 110 and 142.

If a test's measured value (a rung or an N) differs from what is written
here, **stop and report it**. Do not re-pin it: a different value means the
code differs from the prototype.

## Global Constraints

* All 51 artifact outputs stay byte-identical. Run `python -m pleatwright fold`
  on every roll and compare each file against
  `~/Desktop/origami_samples_artifact_trees`: **204/204 identical**.
* CI's two pinned hashes stay green:
  `test_pleatwright.py::test_packing_cp_bytes_match_the_delivered_models`.
* Tests and probes use **only** the 51 artifact trees in
  `mcp_harness/fixtures/full17_v3_sticks/`, or **named edits** of them defined
  in `mcp_harness/tests/test_pack_chain.py`. No new fixture corpus
  (CLAUDE.md §5).
* **Never** use tardigrade / water bear as a test subject.
* Path-shaped hub graphs must never reach `nest.py`.
* The tree schema (`tree.json`, `submit_tree`, `tree_contract`) does not
  change. Hub pairs are derived from leaf pairs.
* Interpreter: `PY=<repo>/mcp_harness/.venv/bin/python`.
  This worktree has no `.venv`. Single test files run from `mcp_harness/` as
  `PYTHONPATH=.:tests $PY -m pytest tests/<file> -q`. App tests run as
  `make PYTHON=$PY test-app` from the repo root.
* End every commit message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Review Focus

These inputs are implied by the spec, but no task's main tests reach them.
Each one is pinned by a test in the task named.

1. **A mirrored subtree authored with its pairs reversed (R, L) or its
   children in a different order.** `hub_pairs` must still pair the hubs.
   (Task 3, `test_hub_pairs_ignore_pair_orientation_and_node_order`)
2. **A hub pair whose river has odd width** (antlers of length 3). The band's
   outer corners still need x+y even, and the tree must still pack.
   (Task 4, `test_review_focus_shapes_pack[odd_antlers]`)
3. **Unpaired sibling hubs** (`lopsided`: antler rivers 2 and 3). Each becomes
   a full-width axial strip, and the tree packs. (Task 4, `[lopsided]`)
4. **Two branching hubs in one tree** (antlers plus toed forelimbs). This
   needs the ×2 rung. (Task 4, `[antlered_and_toed]`)
5. **A branching tree whose stacked strips exceed the pipeline's grid cap**
   (`toed("crab_3")`). The pipeline must report `failure == "packing"`
   cleanly, with no crash and no hang. (Task 5,
   `test_a_branching_tree_past_the_grid_cap_fails_at_packing`)

---

## File structure

| file | change | responsibility |
|---|---|---|
| `mcp_harness/pleatwright/pack.py` | modify | `Region.more`/`rects`, `Layout.pockets`, `hub_pairs`, `_row_concrete_span`, `_pocket_solutions(rowfn=)`, dispatch in `candidates`; Task 6 deletes `chain_problem` |
| `mcp_harness/pleatwright/base.py` | modify | ownership loop over `r.rects` |
| `mcp_harness/pleatwright/nest.py` | **create** | nested-pocket search for branching hub graphs |
| `mcp_harness/tests/test_nest.py` | **create** | regions, span rows, nest geometry, end to end |
| `mcp_harness/tests/test_pack_chain.py` | modify | named edits `toed`, `lopsided`, `odd_antlers`; `hub_pairs` tests; Task 6 rewrite |
| `mcp_harness/gated_pipeline.py` | modify (Task 6) | drop `pack_problem` |
| `mcp_harness/tests/test_gated_pipeline.py` | modify (Task 6) | replace the guard test |
| `app/server/pleatwright_app/tools.py` | modify (Task 6) | drop `_pack_problem`, the refusal and the `packable` flag |
| `app/server/tests/test_guided.py` | modify (Task 6) | replace the guard test |
| `app/web/src/runStore.ts`, `app/web/src/runStore.test.ts` | modify (Task 6) | drop `packable` |
| `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md` | modify (Task 7) | deviation 1 |
| `CLAUDE.md` | modify (Task 7) | §2 pairs, §3 module list |
| `docs/superpowers/evidence/2026-10-10-branching-packer/` | **create** (Task 7) | probe script, records, README |

---

### Task 1: A region may be several rectangles

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py` (`Region`, `Layout` dataclasses near the top)
- Modify: `mcp_harness/pleatwright/base.py` (`build`, the ownership loop)
- Create: `mcp_harness/tests/test_nest.py`

**Interfaces:**
- Produces:
  * `Region.more: list` (default `[]`) and `Region.rects -> list[tuple]`
    (`[rect, *more]`);
  * `Layout.pockets: list` (default `[]`);
  * `base.build` owns the cells of every rectangle in `r.rects`;
  * the test helper `_first_certified(tree) -> (rung, Layout, Contracted, Base) | None`
    in `test_nest.py`, used by Tasks 4 and 5.

- [ ] **Step 1: Write the failing tests.** Create `mcp_harness/tests/test_nest.py`:

```python
"""Pleatwright's nested packer for branching hub graphs (spec
docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md).

Every tree is an artifact tree or a named edit of one
(tests/test_pack_chain.py), per the owner rule (CLAUDE.md §5)."""
import dataclasses

from artifact_trees import artifact_tree
from pleatwright import base as B
from pleatwright import pack as PK
from pleatwright import shape as SH
from pleatwright import stick as ST

#: pipeline._run's packing ladder: (rung, scale, symmetric)
LADDER = (("symmetric", 1.0, True), ("asymmetric", 1.0, False), ("symmetric x2", 2.0, True))


def _first_certified(tree, max_candidates=400):
    """The pipeline's packing ladder on an in-memory tree: the first layout
    base.build certifies, as (rung, layout, contracted tree, base), or None."""
    tried = 0
    for rung, scale, symmetric in LADDER:
        sf = ST.load_tree(tree, scale)
        con = ST.contract(sf)
        sigma = SH.choose_sigma(sf, con)
        n_max = max(2 * PK.grid_init(con), PK.grid_init(con) + 60)
        for lay in PK.candidates(con, symmetric=symmetric, N_max=n_max):
            tried += 1
            b = B.build(lay, con, sigma)
            if not b.errors:
                return rung, lay, con, b
            if tried >= max_candidates:
                return None
    return None


def test_region_rects_default_to_its_one_rectangle():
    assert PK.Region(0, (0, 0, 2, 2), [], [], "flap", 1).rects == [(0, 0, 2, 2)]
    assert PK.Layout(4, [], [], [], []).pockets == []


def test_a_region_of_several_rectangles_builds_like_one_rectangle():
    """A nested river band is ONE Region of several rectangles (spec §1):
    base.build must own every rectangle's cells and draw no hinge where two
    rectangles of one region meet. Splitting a certified river in two must
    change nothing."""
    _, lay, con, base = _first_certified(artifact_tree("dog_0"))
    i, r = next((i, r) for i, r in enumerate(lay.regions) if r.kind == "river")
    x0, y0, x1, y1 = r.rect
    xm = (x0 + x1) // 2
    split = dataclasses.replace(r, rect=(x0, y0, xm, y1), more=[(xm, y0, x1, y1)])
    lay2 = dataclasses.replace(lay, regions=lay.regions[:i] + [split] + lay.regions[i + 1:])
    b2 = B.build(lay2, con, base.sigma)
    assert b2.errors == []
    assert b2.boundary_edges == base.boundary_edges
    assert {k: v["kind"] for k, v in b2.creases.items()} == \
        {k: v["kind"] for k, v in base.creases.items()}
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run (from `mcp_harness/`): `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q`

Expected: FAIL. The first test fails with `AttributeError: 'Region' object has no attribute 'rects'`; the second fails with `TypeError` (`more` is not a field).

- [ ] **Step 3: Implement.** In `pack.py`, add to `Region` after the `virtual` field:

```python
    virtual: list = field(default_factory=list)
    more: list = field(default_factory=list)   # further rectangles of the SAME region

    @property
    def rects(self) -> list:
        """Every rectangle of the region: a nested river band is several."""
        return [self.rect, *self.more]
```

Add to `Layout` after `score`:

```python
    score: float = 0.0
    pockets: list = field(default_factory=list)   # nested layouts: [(hub, rect, sides)]
```

In `base.py` `build`, replace the ownership loop:

```python
    for ri, r in enumerate(lay.regions):
        x0, y0, x1, y1 = r.rect
        for i in range(max(0, x0), min(N, x1)):
            for j in range(max(0, y0), min(N, y1)):
                if (i, j) in owner:
                    raise BaseError(f"cell {(i, j)} owned twice")
                owner[(i, j)] = ri
```

with:

```python
    for ri, r in enumerate(lay.regions):
        for x0, y0, x1, y1 in r.rects:
            for i in range(max(0, x0), min(N, x1)):
                for j in range(max(0, y0), min(N, y1)):
                    if (i, j) in owner:
                        raise BaseError(f"cell {(i, j)} owned twice")
                    owner[(i, j)] = ri
```

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q`
Expected: `2 passed`.

- [ ] **Step 5: Run the byte-identity guard.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pleatwright.py -q -k bytes_match`
Expected: `2 passed`.

- [ ] **Step 6: Commit.**

```bash
git add mcp_harness/pleatwright/pack.py mcp_harness/pleatwright/base.py mcp_harness/tests/test_nest.py
git commit -m "pleatwright: a region may be several rectangles (Region.more/rects); base.build owns each

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Rows across an off-axis span

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py` (add `_row_concrete_span` just
  before `_pocket_solutions`, and a `rowfn` keyword on `_pocket_solutions`)
- Test: `mcp_harness/tests/test_nest.py`

**Interfaces:**
- Consumes: `antlered(roll="dog_0")` from `tests/test_pack_chain.py` (#204).
- Produces:
  * `pack._row_concrete_span(items, x0, x1, left, right, h, top, bot, y_paper, p, limit=6) -> list[row]`,
    where a row has the same shape as `_row_concrete_asym`'s: a list of
    `(item, x0, x1, my, (vtag, ("explicit", vlines)))`;
  * `pack._pocket_solutions(..., rowfn=None)`: when `rowfn` is given it
    replaces the row builder, using the signature
    `rowfn(items, hw, h, top, bot, y_paper, p, limit=6)`.

- [ ] **Step 1: Write the failing tests.** Append to `test_nest.py`, and add `from test_pack_chain import antlered` to its imports:

```python
def _antler_items():
    """antler_L's two flaps (beam, palm: length 3), unmirrored, as nest packs them."""
    con = ST.contract(ST.load_tree(antlered("dog_0"), 1.0))
    return PK._items(con, "antler_L", False)


def test_span_rows_tile_an_off_axis_pocket_with_its_hinge_side_on_a_hinge_line():
    """The antler_L pocket of the certified antlered dog: [0, 29] x [0, 3], paper
    on top and left, hinge (its river band) on the bottom and right."""
    items = _antler_items()
    sols = PK._row_concrete_span(items, 0, 29, "paper", "hinge", 3, "paper", "hinge", 0, 1,
                                 limit=50)
    assert sols
    for sol in sols:
        spans = [(s[1], s[2]) for s in sol]
        assert spans[0][0] == 0 and spans[-1][1] == 29
        assert all(a[1] == b[0] for a, b in zip(spans, spans[1:]))
        regs = PK._row_regions(62, 0, 3, sol, "paper", "hinge")
        assert all(abs(PK._max_d(r) - r.L) < 1e-9 and PK._parity_ok(r) for r in regs)
        assert 29 in max(regs, key=lambda r: r.rect[2]).vlines
        assert max(v for r in regs for v in r.vlines) <= 29      # nothing past the hinge side


def test_span_rows_put_a_left_hinge_on_its_line_and_respect_parity():
    items = _antler_items()
    sols = PK._row_concrete_span(items, 33, 62, "hinge", "paper", 3, "paper", "hinge", 0, 1,
                                 limit=50)
    assert sols
    for sol in sols:
        regs = PK._row_regions(62, 0, 3, sol, "paper", "hinge")
        assert 33 in min(regs, key=lambda r: r.rect[0]).vlines
        assert min(v for r in regs for v in r.vlines) >= 33
    # a hinge side off the row's parity class can carry no ridge corner
    assert PK._row_concrete_span(items, 0, 29, "paper", "hinge", 3, "paper", "hinge", 0, 0) == []


def test_pocket_solutions_take_an_injected_row_builder():
    items = _antler_items()

    def rowfn(its, hw, h, t, b, yp, p, limit=6):
        return PK._row_concrete_span(its, 0, 29, "paper", "hinge", h, t, b, yp, p, limit)
    rows = next(PK._pocket_solutions(items, 62, 0, 3, "paper", "hinge", rowfn=rowfn))
    assert all(0 <= s[1] < s[2] <= 29 for _, _, sol, _, _ in rows for s in sol)
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q -k "span or injected"`
Expected: FAIL with `AttributeError: module 'pleatwright.pack' has no attribute '_row_concrete_span'`.

- [ ] **Step 3: Implement.** In `pack.py`, insert immediately before `def _pocket_solutions(`:

```python
def _row_concrete_span(items, x0, x1, left, right, h, top, bot, y_paper, p, limit=6):
    """`_row_concrete_asym` on the span [x0, x1] (an off-axis pocket, nest.py).
    A `hinge` side is the inner edge of a river band: the column touching it
    has its hinge line ON that side, never a virtual line past it, and is
    sized as an inner column.  A `paper` side behaves as the paper edge does
    in `_row_concrete_asym`."""
    vc = {}
    for it in items:
        ex, fl = _vopts(it.L, h, top, bot)
        if fl is not None and not _vline_parity_ok(fl, p, y_paper):
            fl = None
        if ex is not None and not _vline_parity_ok(ex, p, y_paper):
            ex = None
        if ex is None and fl is None:
            return []
        vc[id(it)] = (ex, fl)

    def on_p(x):
        return p is None or (x - p) % 2 == 0
    if (left == "hinge" and not on_p(x0)) or (right == "hinge" and not on_p(x1)):
        return []
    W = x1 - x0
    out = []
    if len(items) == 1 and left == right == "paper":
        it = items[0]
        ex, fl = vc[id(it)]
        if fl is not None:
            out.append([(it, x0, x1, it.L, (fl, ("explicit", [])))])
        elif ex is not None and 2 * it.L >= W:
            d1 = (2 * it.L - W) // 2
            d2 = 2 * it.L - W - d1
            if on_p(x0 - d1) and on_p(x1 + d2):
                out.append([(it, x0, x1, INF, (ex, ("explicit", [x0 - d1, x1 + d2])))])
        return out

    def edge(it, w, is_left, a, b):
        ex, fl = vc[id(it)]
        use_fl = w > 2 * it.L or ex is None
        vt = fl if use_fl else ex
        if is_left:
            vl = [b] if (use_fl or w == it.L) else [a - (2 * it.L - w), b]
        else:
            vl = [a] if (use_fl or w == it.L) else [a, b + (2 * it.L - w)]
        return (it, a, b, it.L if use_fl else INF, (vt, ("explicit", vl)))

    lefts = items if left == "paper" else [None]
    rights = items if right == "paper" else [None]
    for eL in lefts:
        for eR in rights:
            if eL is not None and eR is eL:
                continue
            inner = [it for it in items if it is not eL and it is not eR]
            fixed = sum(2 * it.L for it in inner)
            flex_inner = [it for it in inner if vc[id(it)][1] is not None]
            loL = eL.L if eL else 0
            hiL = (INF if vc[id(eL)][1] is not None else 2 * eL.L) if eL else 0
            loR = eR.L if eR else 0
            hiR = (INF if vc[id(eR)][1] is not None else 2 * eR.L) if eR else 0
            for wL in range(loL, min(hiL, W) + 1):
                if eL is not None and not on_p(x0 + wL):
                    continue
                rem = W - wL - fixed
                if rem < loR:
                    break
                wR = rem if eR is not None else 0
                extra = rem - wR
                if eR is not None and wR > hiR:
                    extra, wR = wR - hiR, hiR
                if extra and (not flex_inner or extra % 2):
                    continue
                if eR is not None and not on_p(x1 - wR):
                    continue
                sol, x = [], x0
                if eL is not None:
                    sol.append(edge(eL, wL, True, x0, x0 + wL))
                    x = x0 + wL
                for it in inner:
                    ex_i, fl_i = vc[id(it)]
                    wi = 2 * it.L
                    vt_i = ex_i if ex_i is not None else fl_i
                    if extra and it is flex_inner[0]:
                        wi += extra
                        vt_i = fl_i
                    sol.append((it, x, x + wi, it.L, (vt_i, ("explicit", [x, x + wi]))))
                    x += wi
                if eR is not None:
                    sol.append(edge(eR, wR, False, x, x1))
                    x = x1
                if x != x1:
                    continue
                out.append(sol)
                if len(out) >= limit:
                    return out
    return out
```

Then change the head of `_pocket_solutions` from:

```python
def _pocket_solutions(items, N, y0, y1, top, bot, max_rows=4, limit=24):
    """Tile pocket [0,N] x [y0,y1] with rows of symmetric columns.  Yields
    lists of rows (ry0, ry1, row_solution, top, bot)."""
    hw = N // 2
    H = y1 - y0
    n = len(items)
    asym = any(it.single for it in items)
    rowfn = (lambda its, hw_, h_, t_, b_, yp_, p_, limit=6:
             _row_concrete_asym(its, N, h_, t_, b_, yp_, p_, limit)) if asym else _row_concrete
```

to:

```python
def _pocket_solutions(items, N, y0, y1, top, bot, max_rows=4, limit=24, rowfn=None):
    """Tile pocket [0,N] x [y0,y1] with rows of symmetric columns.  Yields
    lists of rows (ry0, ry1, row_solution, top, bot).  `rowfn` replaces the
    row builder (nest.py: an off-axis span); its signature is _row_concrete's."""
    hw = N // 2
    H = y1 - y0
    n = len(items)
    asym = any(it.single for it in items)
    if rowfn is None:
        rowfn = (lambda its, hw_, h_, t_, b_, yp_, p_, limit=6:
                 _row_concrete_asym(its, N, h_, t_, b_, yp_, p_, limit)) if asym else _row_concrete
```

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Run the byte-identity guard.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pleatwright.py -q -k bytes_match`
Expected: `2 passed`.

- [ ] **Step 6: Commit.**

```bash
git add mcp_harness/pleatwright/pack.py mcp_harness/tests/test_nest.py
git commit -m "pleatwright: rows across an off-axis span (_row_concrete_span); _pocket_solutions takes a row builder

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Hub pairs, derived from leaf pairs

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py` (add `_mirror` and `hub_pairs`
  just before `class PackError`)
- Modify: `mcp_harness/tests/test_pack_chain.py` (named edits and tests)

**Interfaces:**
- Consumes: `Contracted.chains`, `Contracted.pairs` (`stick.py`).
- Produces:
  * `pack.hub_pairs(con) -> list[tuple[int, int, dict]]`: tuples
    `(river_a, river_b, chain_map)`, where `chain_map` maps every chain id of
    either subtree to its mirror image, in both directions;
  * named edits in `test_pack_chain.py`: `_toe(tree)`, `toed(roll="dog_0")`,
    `lopsided(roll="dog_0")`, `odd_antlers(roll="dog_0")`.

- [ ] **Step 1: Write the failing tests.** In `mcp_harness/tests/test_pack_chain.py`:
  * change the pack import to `from pleatwright.pack import PackError, chain_problem, hub_pairs, hub_path`;
  * add `import copy` at the top;
  * append the following.

```python
def _toe(t):
    """DEFECT (named): each leaf of the tree's longest declared leaf pair gets an
    inner and an outer toe (length 2), paired across, so the pair's hub gains a
    mirrored pair of hub children. Pairs naming nodes the tree lacks (octopus)
    are skipped; a tree with no usable pair raises ValueError."""
    t = copy.deepcopy(t)
    length = {n["name"]: n["length"] for n in t["nodes"]}
    leaves = set(t["leaves"])
    usable = [p for p in t["pairs"] if p[0] in leaves and p[1] in leaves
              and p[0] in length and p[1] in length]
    a, b = max(usable, key=lambda p: length[p[0]])
    for leaf in (a, b):
        for toe in ("inner", "outer"):
            t["nodes"].append({"name": f"{leaf}_{toe}", "parent": leaf, "length": 2,
                               "direction": [0, -1, 0]})
    t["leaves"] = [x for x in t["leaves"] if x not in (a, b)] + \
        [f"{x}_{toe}" for x in (a, b) for toe in ("inner", "outer")]
    t["pairs"] = t["pairs"] + [[f"{a}_inner", f"{b}_inner"], [f"{a}_outer", f"{b}_outer"]]
    return t


def toed(roll="dog_0"):
    """`_toe` applied to an artifact tree."""
    return _toe(artifact_tree(roll))


def lopsided(roll="dog_0"):
    """DEFECT (named): `antlered` with the right antler's river 3 instead of 2, so
    the two antlers are NOT a hub pair (unpaired sibling hubs)."""
    t = antlered(roll)
    next(n for n in t["nodes"] if n["name"] == "antler_R")["length"] = 3
    return t


def odd_antlers(roll="dog_0"):
    """DEFECT (named): `antlered` with both antler rivers 3 (odd), still paired."""
    t = antlered(roll)
    for n in t["nodes"]:
        if n["name"] in ("antler_L", "antler_R"):
            n["length"] = 3
    return t


def _hub_pair_names(t):
    con = ST.contract(ST.load_tree(t, 1.0))
    return {(con.chains[a].v, con.chains[b].v) for a, b, _ in hub_pairs(con)}


def test_hub_pairs_are_derived_from_leaf_pairs():
    assert _hub_pair_names(antlered()) == {("antler_L", "antler_R")}
    assert _hub_pair_names(toed("dog_0")) == {("paw_front_L", "paw_front_R")}
    assert _hub_pair_names(lopsided()) == set()


def test_a_hub_pair_maps_every_chain_of_both_subtrees():
    con = ST.contract(ST.load_tree(antlered(), 1.0))
    (_, _, m), = hub_pairs(con)
    names = {con.chains[k].v: con.chains[v].v for k, v in m.items()}
    assert names == {"antler_L": "antler_R", "antler_R": "antler_L",
                     "antler_L_beam": "antler_R_beam", "antler_R_beam": "antler_L_beam",
                     "antler_L_palm": "antler_R_palm", "antler_R_palm": "antler_L_palm"}


def test_hub_pairs_ignore_pair_orientation_and_node_order():
    """Review focus 1: a VLM may list a pair right-first, or a mirrored subtree's
    children in a different order."""
    t = antlered()
    t["pairs"] = [p[::-1] for p in t["pairs"]]
    right = [n for n in t["nodes"] if n["name"].startswith("antler_R_")]
    t["nodes"] = [n for n in t["nodes"] if not n["name"].startswith("antler_R_")] + right[::-1]
    assert _hub_pair_names(t) == {("antler_L", "antler_R")}
```

`test_pack_chain.py` must also import `artifact_tree`. Change its first import line to `from artifact_trees import ROLLS, artifact_tree`, which is what #204 has; check it.

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pack_chain.py -q`
Expected: collection ERROR, `ImportError: cannot import name 'hub_pairs'`.

- [ ] **Step 3: Implement.** In `pack.py`, insert immediately before `class PackError(Exception):`:

```python
def _mirror(con: Contracted, a: int, b: int, pair: dict, kids: dict) -> dict | None:
    """Chain-id map {a: b, b: a, ...} over two subtrees that mirror each other
    (equal lengths, leaves matched through `pair`), or None."""
    ca, cb = con.chains[a], con.chains[b]
    if ca.length != cb.length or ca.leaf != cb.leaf:
        return None
    if ca.leaf:
        return {a: b, b: a} if pair.get(a) == b else None
    A, B = kids.get(ca.v, []), kids.get(cb.v, [])
    if len(A) != len(B):
        return None
    out, used = {a: b, b: a}, set()
    for x in A:
        for y in B:
            if y in used:
                continue
            m = _mirror(con, x, y, pair, kids)
            if m is not None:
                out.update(m)
                used.add(y)
                break
        else:
            return None
    return out


def hub_pairs(con: Contracted) -> list:
    """Mirrored pairs of hub subtrees, as (river_a, river_b, chain map): two
    child hubs of one parent whose rivers have equal length and whose subtrees
    match leaf for leaf through the declared leaf pairs (spec 2026-10-10 §1)."""
    pair = {}
    for a, b in con.pairs:
        pair[a], pair[b] = b, a
    kids = {}
    for c in con.chains:
        kids.setdefault(c.u, []).append(c.id)
    out = []
    for cs in kids.values():
        rivers = [i for i in cs if not con.chains[i].leaf]
        used = set()
        for i, a in enumerate(rivers):
            for b in rivers[i + 1:]:
                if a in used or b in used:
                    continue
                m = _mirror(con, a, b, pair, kids)
                if m is not None:
                    out.append((a, b, m))
                    used |= {a, b}
    return out
```

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pack_chain.py -q`
Expected: `5 passed`: #204's two tests plus the three new ones.

- [ ] **Step 5: Commit.**

```bash
git add mcp_harness/pleatwright/pack.py mcp_harness/tests/test_pack_chain.py
git commit -m "pleatwright: hub pairs derived from leaf pairs; named edits toed, lopsided, odd_antlers

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: The nested-pocket search, and the dispatch to it

**Files:**
- Create: `mcp_harness/pleatwright/nest.py`
- Modify: `mcp_harness/pleatwright/pack.py` (`candidates`: dispatch at the top)
- Test: `mcp_harness/tests/test_nest.py`

**Interfaces:**
- Consumes:
  * `pack.Region(..., more=)` and `Layout(..., pockets=)` (Task 1);
  * `pack._row_concrete_span` and `_pocket_solutions(rowfn=)` (Task 2);
  * `pack.hub_pairs` (Task 3);
  * `pack._items`, `_row_regions`, `_max_d`, `_parity_ok`, `_score`,
    `grid_init` (existing).
- Produces:
  * `nest.Box(x0, y0, x1, y1, top, bot, left, right)`, a frozen dataclass
    whose sides are `'paper' | 'hinge'`;
  * `nest.band(chain, W, box) -> (Region, Box) | None`;
  * `nest.mirror(reg, N, chain_map) -> Region`;
  * `nest.candidates(con, *, N_min=None, N_max=160, per_N=60, symmetric=True)`,
    which yields `Layout`s (same contract as `pack.candidates`);
  * `pack.candidates` calls `nest.candidates` exactly when some hub joins
    more than two hubs.

- [ ] **Step 1: Write the failing tests.** Append to `test_nest.py`. Add
  `import pytest`, `from pleatwright import nest as NE`, and
  `from test_pack_chain import _toe, lopsided, odd_antlers` to its imports.

```python
def test_band_wraps_the_hinge_sides_of_a_box():
    """antler_L's region of the certified antlered dog: paper above and left,
    head hinges below (the head river) and right (the axis)."""
    reg, pocket = NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge"))
    assert (reg.chain, reg.kind, reg.L) == (7, "river", 2)
    assert reg.rects == [(0, 3, 31, 5), (29, 0, 31, 3)]
    assert reg.vlines == [31] and reg.hlines == [5]
    assert pocket == NE.Box(0, 0, 29, 3, "paper", "hinge", "paper", "hinge")


def test_band_needs_a_hinge_side_and_room_for_a_pocket():
    assert NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "paper", "paper", "paper")) is None
    assert NE.band(7, 20, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge")) is None


def test_mirror_reflects_in_the_axis_and_swaps_the_chain():
    reg, _ = NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge"))
    m = NE.mirror(reg, 62, {7: 8})
    assert m.chain == 8 and m.rects == [(31, 3, 62, 5), (31, 0, 33, 3)]
    assert m.vlines == [31] and m.hlines == [5]


def test_a_path_shaped_tree_never_enters_nest(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("nest.candidates called for a path-shaped hub graph")
    monkeypatch.setattr(NE, "candidates", boom)
    con = ST.contract(ST.load_tree(artifact_tree("dog_0"), 1.0))
    assert next(PK.candidates(con)) is not None


def test_antlered_dog_packs_with_mirrored_antlers():
    rung, lay, con, _ = _first_certified(antlered("dog_0"))
    assert (rung, lay.N) == ("asymmetric", 62)
    by = {con.chains[r.chain].v: r for r in lay.regions}
    for left, right in (("antler_L", "antler_R"), ("antler_L_beam", "antler_R_beam"),
                        ("antler_L_palm", "antler_R_palm")):
        a, b = by[left], by[right]
        assert NE.mirror(a, lay.N, {a.chain: b.chain}) == b
    assert by["antler_L"].more, "the antler band is one region of several rectangles"
    assert [p[0] for p in lay.pockets][:1] == [con.root]


def test_a_symmetric_rung_layout_is_its_own_mirror_image():
    rung, lay, con, _ = _first_certified(antlered("bird_1"))
    assert (rung, lay.N) == ("symmetric", 54)
    pm = {}
    for a, b in con.pairs:
        pm[a], pm[b] = b, a
    for _, _, m in PK.hub_pairs(con):
        pm.update(m)

    def sig(r):
        return (r.chain, tuple(sorted(r.rects)), tuple(r.vlines), tuple(r.hlines))
    assert {sig(NE.mirror(r, lay.N, {r.chain: pm.get(r.chain, r.chain)})) for r in lay.regions} \
        == {sig(r) for r in lay.regions}


def test_no_hinge_is_drawn_between_two_rectangles_of_one_chain():
    """The spurious-hinge regression (spec §1): a band split into separate
    Regions would put a region boundary between two cells of the SAME chain."""
    _, lay, _, base = _first_certified(antlered("dog_0"))
    owner = {}
    for r in lay.regions:
        for x0, y0, x1, y1 in r.rects:
            for i in range(max(0, x0), min(lay.N, x1)):
                for j in range(max(0, y0), min(lay.N, y1)):
                    owner[(i, j)] = r.chain
    for (x, y), (x2, y2) in base.boundary_edges:
        if y == y2:
            c0, c1 = (min(x, x2), y - 1), (min(x, x2), y)
        else:
            c0, c1 = (x - 1, min(y, y2)), (x, min(y, y2))
        assert owner[c0] != owner[c1]


@pytest.mark.parametrize("edit,rung,N", [
    ("lopsided", "symmetric", 86),               # review focus 3: unpaired sibling hubs
    ("odd_antlers", "asymmetric", 64),           # review focus 2: odd hub-pair river
    ("antlered_and_toed", "symmetric x2", 128),  # review focus 4: two branching hubs
])
def test_review_focus_shapes_pack(edit, rung, N):
    tree = {"lopsided": lambda: lopsided("dog_0"),
            "odd_antlers": lambda: odd_antlers("dog_0"),
            "antlered_and_toed": lambda: _toe(antlered("dog_0"))}[edit]()
    got = _first_certified(tree)
    assert got is not None and (got[0], got[1].N) == (rung, N)
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q`
Expected: collection ERROR, `ImportError: cannot import name 'nest' from 'pleatwright'`.

- [ ] **Step 3: Create `mcp_harness/pleatwright/nest.py`:**

```python
"""Nested pockets: packing for branching hub graphs (spec 2026-10-10).

`pack.py` lays rivers as full-width bands, which needs the hubs in one chain.
Here every hub owns a rectangular *pocket*: the root's is the whole paper; a
child hub's region is a strip of its parent's pocket, its river is the band of
width W along every side of that strip that is not paper edge (an L-infinity
offset band, Box Pleating Studio's river contour), and its pocket is the strip
shrunk by W on those sides.  A pocket is a vertical stack of strips: the hub's
flap block (pack's row model) and one strip per child.  On the mirror axis a
mirrored pair of hub subtrees shares one strip, split at x = N/2: the left
child is packed, the right is its mirror image.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from .pack import (Layout, Region, _items, _max_d, _parity_ok, _pocket_solutions,
                   _row_concrete_span, _row_regions, _score, grid_init, hub_pairs)


@dataclass(frozen=True)
class Box:
    """A rectangle of the grid and what lies past each side."""
    x0: int
    y0: int
    x1: int
    y1: int
    top: str        # 'paper' | 'hinge'
    bot: str
    left: str
    right: str

    def rows(self, y0: int, y1: int) -> "Box":
        """The full-width strip [y0, y1] of this box; inner edges are hinges."""
        return Box(self.x0, y0, self.x1, y1,
                   self.top if y0 == self.y0 else "hinge",
                   self.bot if y1 == self.y1 else "hinge", self.left, self.right)

    def key(self) -> tuple:
        """What feasibility depends on (translation in y keeps parity)."""
        return (self.x0, self.x1, self.y0 % 2, self.y1 - self.y0,
                self.top, self.bot, self.left, self.right)


def band(chain: int, W: int, box: Box) -> tuple[Region, Box] | None:
    """The river band of width W around `box`'s hinge sides, and the pocket it
    encloses; None if the box has no hinge side or no room for a pocket."""
    hinge = {s: getattr(box, s) == "hinge" for s in ("top", "bot", "left", "right")}
    if not any(hinge.values()):
        return None
    px0 = box.x0 + (W if hinge["left"] else 0)
    px1 = box.x1 - (W if hinge["right"] else 0)
    py0 = box.y0 + (W if hinge["top"] else 0)
    py1 = box.y1 - (W if hinge["bot"] else 0)
    if px1 <= px0 or py1 <= py0:
        return None
    rects = [r for r in ((box.x0, box.y0, box.x1, py0), (box.x0, py1, box.x1, box.y1),
                         (box.x0, py0, px0, py1), (px1, py0, box.x1, py1))
             if r[0] < r[2] and r[1] < r[3]]
    vl = sorted([box.x0] * hinge["left"] + [box.x1] * hinge["right"])
    hl = sorted([box.y0] * hinge["top"] + [box.y1] * hinge["bot"])
    reg = Region(chain, rects[0], vl, hl, "river", W, more=rects[1:])
    pocket = Box(px0, py0, px1, py1, box.top, box.bot, box.left, box.right)
    return reg, pocket


def mirror(reg: Region, N: int, m: dict) -> Region:
    """`reg` reflected in x = N/2, its chain swapped through the pair map."""
    def flip(r):
        return (N - r[2], r[1], N - r[0], r[3])
    return Region(m[reg.chain], flip(reg.rect), sorted(N - v for v in reg.vlines),
                  list(reg.hlines), reg.kind, reg.L, more=[flip(r) for r in reg.more])


class _Search:
    """Candidate layouts of one grid size N."""

    def __init__(self, con, N: int, symmetric: bool):
        self.con, self.N, self.symmetric = con, N, symmetric
        self.pairs = hub_pairs(con)
        self.kids = {}
        for c in con.chains:
            self.kids.setdefault(c.u, []).append(c)
        self.fcache = {}

    def parts(self, hub: str, axial: bool) -> list:
        """The strips of `hub`'s pocket: ('flaps',), ('child', river),
        ('pair', index into self.pairs).  Pairs split only on the axis; off it,
        each member is its own strip."""
        kids = self.kids.get(hub, [])
        out = [("flaps",)] if any(c.leaf for c in kids) else []
        mine = [i for i, p in enumerate(self.pairs) if self.con.chains[p[0]].u == hub] \
            if axial else []
        paired = {x for i in mine for x in self.pairs[i][:2]}
        out += [("child", c.id) for c in kids if not c.leaf and c.id not in paired]
        out += [("pair", i) for i in mine]
        return out

    def orders(self, parts: list) -> list:
        """Strip orders, those putting children against the paper first (a band
        side against paper is a band side not drawn)."""
        k = len(parts)
        return sorted(itertools.permutations(parts),
                      key=lambda o: sum(1 for i, p in enumerate(o)
                                        if p[0] != "flaps" and 0 < i < k - 1))

    def feasible(self, hub: str, part: tuple, box: Box, axial: bool) -> bool:
        key = (hub, part, box.key(), axial)
        if key not in self.fcache:
            self.fcache[key] = next(self.part(hub, part, box, axial), None) is not None
        return self.fcache[key]

    def heights(self, hub: str, box: Box, axial: bool, order: tuple):
        """Strip heights summing to the box height, each strip feasible."""
        k = len(order)
        reach = [dict() for _ in range(k + 1)]
        reach[0][box.y0] = []
        for i, part in enumerate(order):
            for y in reach[i]:
                hs = [box.y1 - y] if i == k - 1 else range(1, box.y1 - y - (k - 1 - i) + 1)
                for hh in hs:
                    if hh >= 1 and self.feasible(hub, part, box.rows(y, y + hh), axial):
                        reach[i + 1].setdefault(y + hh, []).append((y, hh))

        def back(i, y, acc):
            if i == 0:
                yield acc[::-1]
                return
            for py, hh in reach[i].get(y, [])[:4]:
                yield from back(i - 1, py, acc + [hh])
        yield from back(k, box.y1, [])

    def fill(self, hub: str, box: Box, axial: bool, limit: int = 24):
        """Yield (regions, pockets) tilings of `hub`'s pocket `box`."""
        found = 0
        for order in self.orders(self.parts(hub, axial)):
            for hs in itertools.islice(self.heights(hub, box, axial, order), 6):
                ys = list(itertools.accumulate(hs, initial=box.y0))
                sols = []
                for part, a, b in zip(order, ys, ys[1:]):
                    sols.append(list(itertools.islice(
                        self.part(hub, part, box.rows(a, b), axial), 8)))
                    if not sols[-1]:
                        break
                else:
                    for combo in itertools.product(*sols):
                        regs = [r for rs, _ in combo for r in rs]
                        pockets = [(hub, (box.x0, box.y0, box.x1, box.y1),
                                    (box.top, box.bot, box.left, box.right))]
                        pockets += [p for _, ps in combo for p in ps]
                        yield regs, pockets
                        found += 1
                        if found >= limit:
                            return

    def part(self, hub: str, part: tuple, box: Box, axial: bool):
        """Yield (regions, pockets) for one strip of `hub`'s pocket."""
        N = self.N
        if part[0] == "flaps":
            yield from self.flaps(hub, box, axial)
        elif part[0] == "child":
            yield from self.child(part[1], box, axial)
        else:
            a, b, m = self.pairs[part[1]]
            half = Box(box.x0, box.y0, N // 2, box.y1, box.top, box.bot, box.left, "hinge")
            for regs, pockets in self.child(a, half, False):
                yield regs + [mirror(r, N, m) for r in regs], pockets

    def child(self, river: int, box: Box, axial: bool):
        c = self.con.chains[river]
        made = band(river, c.length, box)
        if made is None or not _parity_ok(made[0]):
            return
        reg, pocket = made
        for regs, pockets in self.fill(c.v, pocket, axial):
            yield [reg] + regs, pockets

    def flaps(self, hub: str, box: Box, axial: bool):
        N = self.N
        if axial:
            items = _items(self.con, hub, self.symmetric)
            gen = _pocket_solutions(items, N, box.y0, box.y1, box.top, box.bot)
        else:
            items = _items(self.con, hub, False)

            def rowfn(its, hw, h, t, b, yp, p, limit=6):
                return _row_concrete_span(its, box.x0, box.x1, box.left, box.right,
                                          h, t, b, yp, p, limit)
            gen = _pocket_solutions(items, N, box.y0, box.y1, box.top, box.bot, rowfn=rowfn)
        for rows in gen:
            regs = []
            for ry0, ry1, sol, t, b in rows:
                regs += _row_regions(N, ry0, ry1, sol, t, b)
            if all(abs(_max_d(r) - r.L) < 1e-9 and _parity_ok(r) for r in regs):
                yield regs, []


def candidates(con, *, N_min=None, N_max=160, per_N=60, symmetric=True):
    """Yield nested Layouts in increasing grid size (pack.candidates' contract)."""
    G = grid_init(con) if N_min is None else N_min
    G = max(G, 2)
    G += G % 2
    hub_order = [con.root] + [c.v for c in con.chains if not c.leaf]
    for N in range(G, N_max + 1, 2):
        search = _Search(con, N, symmetric)
        paper = Box(0, 0, N, N, "paper", "paper", "paper", "paper")
        for regs, pockets in itertools.islice(search.fill(con.root, paper, True, limit=per_N),
                                              per_N):
            lay = Layout(N, regs, hub_order, [], [], pockets=pockets)
            lay.score = _score(lay)
            yield lay
```

- [ ] **Step 4: Add the dispatch.** In `pack.py` `candidates`, replace the start of the body:

```python
    packs unmirrored rows (for figures whose declared pairs differ)."""
    hubs = hub_path(con)
```

with:

```python
    packs unmirrored rows (for figures whose declared pairs differ).  A
    branching hub graph is laid out by nest.py (spec 2026-10-10)."""
    _, nb = _hub_graph(con)
    if any(len(v) > 2 for v in nb.values()):
        from . import nest
        yield from nest.candidates(con, N_min=N_min, N_max=N_max, per_N=per_N,
                                   symmetric=symmetric)
        return
    hubs = hub_path(con)
```

The import is local because `nest` imports `pack` at module level.

- [ ] **Step 5: Run the tests to verify they pass.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q`
Expected: `15 passed`, in under about a minute; `antlered_and_toed` takes about 8 s.

- [ ] **Step 6: Run the byte-identity guard and the pack tests.**

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_pleatwright.py tests/test_pack_chain.py -q`
Expected: all pass, including `bytes_match` (2).

- [ ] **Step 7: Commit.**

```bash
git add mcp_harness/pleatwright/nest.py mcp_harness/pleatwright/pack.py mcp_harness/tests/test_nest.py
git commit -m "pleatwright: nested pockets pack branching hub graphs (nest.py); pack.candidates dispatches to it

Rivers are L-infinity offset bands around each child hub's strip; a mirrored pair of
hub subtrees shares a strip split at the axis. Path-shaped graphs keep pack.py's bands.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: End to end, and the grid-cap failure

**Files:**
- Test: `mcp_harness/tests/test_nest.py`

**Interfaces:**
- Consumes: `pipeline.run(tree_path, out_dir, *, certify_global, verbose) -> dict`
  (existing; a packing failure returns `rec["failure"] == "packing"` and
  raises nothing).

- [ ] **Step 1: Write the tests.** Append to `test_nest.py`. Add `import json`,
  `import os`, `from pleatwright import pipeline as PL` and
  `from test_pack_chain import toed` to its imports.

```python
def test_antlered_dog_folds_end_to_end(tmp_path):
    """The spec's hard gate: the moose's shape folds like the 51 artifact trees."""
    tree = tmp_path / "tree.json"
    tree.write_text(json.dumps(antlered("dog_0")))
    rec = PL.run(str(tree), str(tmp_path), certify_global=True, verbose=False)
    assert rec.get("failure") is None
    assert (rec["packing_rung"], rec["grid_size"]) == ("asymmetric", 62)
    ff = rec["solving_flat_foldable"]
    assert ff[0] == ff[1]
    assert rec["global_verdict"] == "CERTIFIED"
    assert sorted(os.listdir(rec["folder"])) == \
        ["overview.png", "packing_cp.svg", "shaping_cp.svg", "solving_cp.svg"]


def test_a_branching_tree_past_the_grid_cap_fails_at_packing(tmp_path):
    """Review focus 5: toed crab_3 stacks strips past the pipeline's cap
    max(2G, G + 60) = 106; it certifies only at N = 108 (measured 2026-10-10).
    It must fail AT PACKING, cleanly; this pins the known limit, so a later
    improvement updates this test on purpose."""
    tree = tmp_path / "tree.json"
    tree.write_text(json.dumps(toed("crab_3")))
    rec = PL.run(str(tree), str(tmp_path), certify_global=False, verbose=False)
    assert rec["failure"] == "packing" and rec["pack_tried"] == 0
```

- [ ] **Step 2: Run them.** Both exercise code from Tasks 1–4, so they should pass on first run. If either fails, it is a real defect: use superpowers:systematic-debugging, and do not edit the expected values.

Run: `PYTHONPATH=.:tests $PY -m pytest tests/test_nest.py -q -k "end_to_end or grid_cap"`
Expected: `2 passed`. That takes about 30 s and about 20 s.

- [ ] **Step 3: Commit.**

```bash
git add mcp_harness/tests/test_nest.py
git commit -m "test: antlered dog folds end to end (CERTIFIED); a branching tree past the grid cap fails at packing

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Retire #204's chain guard

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py` (delete `chain_problem`; keep `_hub_graph`)
- Modify: `mcp_harness/tests/test_pack_chain.py` (rewrite its two #204 tests)
- Modify: `mcp_harness/gated_pipeline.py` (`summarise`, `_draft`)
- Modify: `mcp_harness/tests/test_gated_pipeline.py` (replace `test_review_warns_when_the_tree_cannot_be_packed_yet`)
- Modify: `app/server/pleatwright_app/tools.py` (`present`, `_pack_problem`, `fold`)
- Modify: `app/server/tests/test_guided.py` (replace `test_an_unpackable_tree_is_flagged_and_its_failure_returns_to_review`)
- Modify: `app/web/src/runStore.ts`, `app/web/src/runStore.test.ts`

**Keep** (spec Section 3):
* `stick.load_tree`;
* `tools.review_again` reopening an approved tree;
* `present` labelling a round with `state["model"]`;
* `Chat.tsx`'s "Back to the tree" label;
* `guided.retry` not requiring a key for `review`.

- [ ] **Step 1: Rewrite the tests first.**

In `mcp_harness/tests/test_pack_chain.py`:
* replace the module docstring;
* replace the import with `from pleatwright.pack import PackError, hub_pairs, hub_path`;
* replace `test_every_artifact_tree_is_chain_shaped` and
  `test_a_forked_antler_head_is_named_and_packing_refuses_it` with the two
  tests below. Keep `antlered` and every Task 3 addition.

```python
"""Named edits of artifact trees for the branching packer (spec
docs/superpowers/specs/2026-10-10-branching-hub-packer-design.md), and the
path-shaped precondition that keeps the 51 artifact outputs byte-identical."""
```

```python
def test_every_artifact_tree_is_path_shaped():
    """The 51 keep pack.py's band code, so their outputs stay byte-identical."""
    for r in ROLLS:
        hub_path(ST.contract(ST.load_tree(artifact_tree(r), 1.0)))


def test_hub_path_still_refuses_a_branching_hub_graph():
    """pack.candidates sends these to nest.py; hub_path itself is unchanged."""
    with pytest.raises(PackError, match="not a path"):
        hub_path(ST.contract(ST.load_tree(antlered(), 1.0)))
```

In `mcp_harness/tests/test_gated_pipeline.py`, replace `test_review_warns_when_the_tree_cannot_be_packed_yet` with:

```python
def test_review_does_not_warn_about_branching(tmp_path, monkeypatch):
    """Branching hub graphs pack (nest.py), so a forked-antler tree reaches
    review with no packing warning (spec 2026-10-10 §3)."""
    from test_pack_chain import antlered
    monkeypatch.setattr(GP.vlm_render, "render_mesh_views",
                        lambda *a, **k: _fake_mesh_views(tmp_path))
    t = antlered()
    payload = {k: t[k] for k in ("subject_guess", "nodes", "pairs", "readings", "leaves")}
    st = asyncio.run(GP.start("fake.glb", client=FakeClient([payload]), out_dir=str(tmp_path)))
    assert st["status"] == "awaiting_review"
    assert "pack_problem" not in st
    assert "cannot pack" not in st["summary"]
```

In `app/server/tests/test_guided.py`, replace `test_an_unpackable_tree_is_flagged_and_its_failure_returns_to_review` with:

```python
def test_an_antlered_tree_goes_straight_to_packing(offline):
    """A tree whose branch points branch (forked antlers on the head) is no
    longer flagged or refused: approving it folds it (spec 2026-10-10 §3)."""
    from test_pack_chain import antlered
    t = antlered()
    payload = {k: t[k] for k in ("subject_guess", "nodes", "pairs", "readings", "leaves")}

    async def main():
        m = Manager(RunStore(str(offline / "runs")), lambda model: FakeClient([payload]),
                    certify_global=False)
        rid = await m.create("a dog with antlers")
        await m.wait_idle()
        await m.approve(rid)
        await m.wait_idle()
        return m, rid
    m, rid = asyncio.run(main())
    log = m.store.log(rid)
    tree_out = next(e for e in log.events if e["type"] == "stage_output" and e["stage"] == "tree")
    assert "packable" not in tree_out["summary"]
    assert any(e["type"] == "stage_output" and e["stage"] == "packing" for e in log.events)
    assert log.last["type"] == "run_finished"
```

In `app/web/src/runStore.test.ts`, delete the whole `it("flags a tree round the packer cannot lay out yet", ...)` block, lines 137–142 at the time of writing.

- [ ] **Step 2: Run the new tests to verify they fail.**

Run (repo root): `make PYTHON=$PY test-app 2>&1 | tail -5`
Expected: `test_an_antlered_tree_goes_straight_to_packing` FAILS, because the run ends in `stage_failed` (the refusal).

Run (from `mcp_harness/`): `PYTHONPATH=.:tests $PY -m pytest tests/test_gated_pipeline.py -q -k branching`
Expected: FAIL on `assert "pack_problem" not in st`.

- [ ] **Step 3: Remove the guard.**

`pack.py`: delete the whole `def chain_problem(tree: dict) -> str | None:` function. `_hub_graph` and `hub_path` stay.

`gated_pipeline.py`:
* in `summarise`, change the signature's tail `figure_note=None, pack_problem=None) -> str:` to `figure_note=None) -> str:`;
* delete the whole `if pack_problem:` block (the `lines.append("WARNING: Pleatwright cannot pack this tree yet. ...")`);
* in `_draft`, delete the comment and `try/except` that compute `pack_problem` (from `# Whether the packer can lay this tree out at all` to `pack_problem = None`);
* in the `state.update({...})` call, delete the `"pack_problem": pack_problem,` entry and the `pack_problem=pack_problem,` argument to `summarise`.

`app/server/pleatwright_app/tools.py`:
* in `present`, delete
  ```python
          if state.get("pack_problem"):      # the summary text carries the why
              summary["packable"] = False
  ```
* delete the whole `def _pack_problem(tree_path: str) -> str | None:` function;
* in `fold`, delete the comment block and the refusal, from `# Refuse a tree the packer cannot lay out` to `raise ToolFailed(error)` inclusive, so `fold` reads:
  ```python
  async def fold(ctx: Ctx, *, certify_global: bool = True) -> dict:
      from .foldproc import FoldJob
      ctx.emit("stage_started", stage="packing")
      current = "packing"                  # the UI stage last started
  ```
* `import json` stays, because `load_state` uses it.

`app/web/src/runStore.ts`:
* in `summaryLine`, change the `tree` case back to
  ```ts
      case "tree": return s.approved ? "approved"
        : `${s.flaps} flaps, ${s.pairs} pairs${s.model ? ` · ${s.model}` : ""}`;
  ```
* in `summaryPairs`, change the `tree` case's `else` back to
  ```ts
        else { add("flaps", s.flaps); add("pairs", s.pairs); add("model", s.model); }
  ```

- [ ] **Step 4: Verify nothing still names the guard.**

Run (repo root): `grep -rn "chain_problem\|pack_problem\|packable\|cannot be packed yet\|cannot pack this tree" mcp_harness app --include=*.py --include=*.ts --include=*.tsx`
Expected: no output.

- [ ] **Step 5: Run the affected suites.**

Run (from `mcp_harness/`): `PYTHONPATH=.:tests $PY -m pytest tests/test_pack_chain.py tests/test_gated_pipeline.py tests/test_nest.py -q`
Expected: all pass.

Run (repo root): `make PYTHON=$PY test-app`
Expected: all pass.

Run: `cd app/web && npm ci && npm test && npm run build`
Expected: vitest all pass; the build succeeds (`tsc --noEmit` clean).

- [ ] **Step 6: Commit.**

```bash
git add -A mcp_harness/pleatwright/pack.py mcp_harness/gated_pipeline.py mcp_harness/tests/test_pack_chain.py \
  mcp_harness/tests/test_gated_pipeline.py app/server/pleatwright_app/tools.py app/server/tests/test_guided.py \
  app/web/src/runStore.ts app/web/src/runStore.test.ts
git commit -m "Retire #204's chain guard: branching hub graphs now pack (nest.py)

chain_problem, the review WARNING, the app's pre-fold refusal and the packable flag go;
review reopening, model labels and the 'Back to the tree' label stay (spec 2026-10-10 §3).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Evidence, the byte-identity gate, and the docs

**Files:**
- Create: `docs/superpowers/evidence/2026-10-10-branching-packer/probe_branching.py`
- Create: `docs/superpowers/evidence/2026-10-10-branching-packer/records.jsonl` (written by the probe)
- Create: `docs/superpowers/evidence/2026-10-10-branching-packer/README.md`
- Modify: `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md` (deviation 1)
- Modify: `CLAUDE.md` (§2 pairs bullet, §3 module list)

- [ ] **Step 1: Write the probe.** Create `docs/superpowers/evidence/2026-10-10-branching-packer/probe_branching.py`:

```python
"""Branching-packer probe (spec 2026-10-10 §4): every branching named edit
through the full pipeline. Run from mcp_harness/:

    PYTHONPATH=.:tests $PY ../docs/superpowers/evidence/2026-10-10-branching-packer/probe_branching.py OUT

Writes the model folders under OUT/<edit>_<roll>/ and one JSON line per tree
to records.jsonl beside this script. Trees: named edits of the 51 artifact
trees only (CLAUDE.md §5)."""
import glob
import json
import os
import sys
import time

from artifact_trees import ROLLS, artifact_tree
from pleatwright import pack as PK
from pleatwright import pipeline as PL
from pleatwright import stick as ST
from test_pack_chain import antlered, lopsided, toed

HERE = os.path.dirname(os.path.abspath(__file__))
DELIVERED = os.path.expanduser("~/Desktop/origami_samples_artifact_trees")
EDITS = (("antlered", antlered), ("toed", toed), ("lopsided", lopsided))


def branching(tree):
    _, nb = PK._hub_graph(ST.contract(ST.load_tree(tree, 1.0)))
    return any(len(v) > 2 for v in nb.values())


def unedited_grid(roll):
    """The grid of the delivered model of the unedited roll."""
    title = PL.title_of(ST.load_tree(artifact_tree(roll), 1.0))
    hits = [p for p in glob.glob(os.path.join(DELIVERED, glob.escape(title) + "_*"))
            if os.path.isdir(p)]
    return int(hits[0].rsplit("_", 1)[1]) if len(hits) == 1 else None


def main(out):
    with open(os.path.join(HERE, "records.jsonl"), "w") as rec_f:
        for edit, fn in EDITS:
            for roll in ROLLS:
                try:
                    tree = fn(roll)
                except (KeyError, ValueError, StopIteration):
                    continue                     # the edit does not apply to this roll
                if not branching(tree):
                    continue
                d = os.path.join(out, f"{edit}_{roll}")
                os.makedirs(d, exist_ok=True)
                path = os.path.join(d, "tree.json")
                with open(path, "w") as f:
                    json.dump(tree, f)
                t0 = time.perf_counter()
                row = {"edit": edit, "roll": roll, "unedited_grid": unedited_grid(roll)}
                try:
                    rec = PL.run(path, d, certify_global=True, verbose=False)
                    row.update({k: rec.get(k) for k in (
                        "failure", "packing_rung", "grid_size", "pack_tried", "pack_secs",
                        "solving_flat_foldable", "global_verdict", "tree_similarity", "folder")})
                except PL.StageError as e:
                    row.update({"failure": e.stage, "error": str(e)})
                row["secs"] = round(time.perf_counter() - t0, 1)
                rec_f.write(json.dumps(row) + "\n")
                rec_f.flush()
                print(edit, roll, row.get("failure") or row.get("grid_size"), flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
```

- [ ] **Step 2: Run the probe in the background.** It folds about 109 trees at about 30 s each, so roughly an hour.

Run (from `mcp_harness/`):
`PYTHONPATH=.:tests $PY ../docs/superpowers/evidence/2026-10-10-branching-packer/probe_branching.py "$TMPDIR/branching_probe" > "$TMPDIR/branching_probe.log" 2>&1`

Expected, from the prototype, for packing:
* `antlered` 35/35;
* `toed` 36/39, with `failure == "packing"` for crab_3, elephant_3 and spider_2;
* `lopsided` 35/35.

Packed trees should be locally flat-foldable throughout. Record whatever the probe actually measures.

- [ ] **Step 3: Run the byte-identity gate while the probe runs.**

Run (from `mcp_harness/`):

```bash
OUT="$TMPDIR/byte_gate"; mkdir -p "$OUT"
PYTHONPATH=.:tests $PY -c "from artifact_trees import ROLLS; print('\n'.join(ROLLS))" \
  | xargs -P 4 -I{} sh -c "PYTHONPATH=. $PY -m pleatwright fold {} --out $OUT/{} > /dev/null 2>&1 || echo FAIL {}"
```

```bash
$PY - "$OUT" <<'EOF'
import filecmp, glob, os, sys
out, ref = sys.argv[1], os.path.expanduser("~/Desktop/origami_samples_artifact_trees")
folders = [p for p in glob.glob(os.path.join(out, "*", "*_*")) if os.path.isdir(p)]
same, diff = 0, []
for folder in sorted(folders):
    name = os.path.basename(folder)
    for f in ("packing_cp.svg", "solving_cp.svg", "shaping_cp.svg", "overview.png"):
        a, b = os.path.join(folder, f), os.path.join(ref, name, f)
        if os.path.exists(b) and filecmp.cmp(a, b, shallow=False):
            same += 1
        else:
            diff.append((name, f))
print(f"{len(folders)} folders, {same} identical, {len(diff)} different", diff[:10])
EOF
```

Expected: `51 folders, 204 identical, 0 different []`. Any other result blocks the PR: use superpowers:systematic-debugging.

- [ ] **Step 4: Look at three models, not only their scores.** Open the overview PNGs for:
* `antlered_dog_0`;
* `antlered_horse_1`;
* `toed_crab_0`.

Each is the `folder` field of its `records.jsonl` row. Check that the antlers or toes are visible as mirrored forks at the right end of the body. Note what you see in the README (Step 5). If one looks wrong, stop and report: memory *looking-at-models-beats-scoring-them*.

- [ ] **Step 5: Write `README.md` from the measured records.** Generate the table:

```bash
$PY - <<'EOF'
import json, collections
rows = [json.loads(l) for l in open("../docs/superpowers/evidence/2026-10-10-branching-packer/records.jsonl")]
by = collections.defaultdict(list)
for r in rows:
    by[r["edit"]].append(r)
print("| edit | trees | packed | rungs | flat-foldable | CERTIFIED | median grid / unedited |")
print("|---|---|---|---|---|---|---|")
for e, v in by.items():
    ok = [r for r in v if not r.get("failure")]
    rungs = dict(collections.Counter(r["packing_rung"] for r in ok))
    ff = sum(1 for r in ok if r["solving_flat_foldable"][0] == r["solving_flat_foldable"][1])
    cert = sum(1 for r in ok if r["global_verdict"] == "CERTIFIED")
    ratios = sorted(r["grid_size"] / r["unedited_grid"] for r in ok if r.get("unedited_grid"))
    med = ratios[len(ratios) // 2] if ratios else None
    print(f"| {e} | {len(v)} | {len(ok)} | {rungs} | {ff}/{len(ok)} | {cert}/{len(ok)} | {med:.2f} |")
for r in rows:
    if r.get("failure"):
        print("MISS", r["edit"], r["roll"], r["failure"], r.get("error", ""))
EOF
```

The README holds:
* the command that produced `records.jsonl`;
* that table;
* each miss with its cause. The prototype's diagnosis for the three `toed` misses: children stack as full-width strips, so their height exceeds the pipeline's cap `max(2G, G + 60)`. Uncapped they certify at N = 108, 110 and 142 (unedited 104, 80, 136).
* the byte-gate line from Step 3;
* the Step 4 observations.

- [ ] **Step 6: Update the docs.**

In `docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md`, replace deviation 1, from `1. **Pocket tiling family.**` through `Branching hub graphs need the paper's wall-following packer (planned).`, with the text below. Use the probe's measured miss count if it differs from three of 109.

```markdown
1. **Pocket tiling family.** The paper's packer snakes rivers by wall-following
   around arbitrary obstacles. Ours nests them. A path-shaped hub graph (all 51
   artifact trees, measured) gets parallel full-width bands, which is exactly
   the wall-following result for a chain. A branching one (first seen
   2026-10-10: a moose whose head carried forked antlers) is packed by
   `pleatwright/nest.py`: each child hub's river is the L-infinity offset band
   around its own rectangle, and a mirrored pair of hub subtrees shares a strip
   split at x = N/2 (spec `2026-10-10-branching-hub-packer-design.md`). Rivers
   still never bend around flaps, so a long thin branch costs a full-width
   strip; three of the 109 named branching edits exceed the pipeline's grid cap
   for that reason (evidence `2026-10-10-branching-packer/`).
```

In `CLAUDE.md` §2, after the sentence ending `... (\`pleatwright/pack.py\`).` in the `pairs` bullet, insert:

```markdown
  A tree whose hubs branch is packed by `pleatwright/nest.py`, where two child
  hubs whose subtrees mirror each other through these leaf pairs
  (`pack.hub_pairs`) share a strip split at x = N/2; hub pairs are derived,
  never authored.
```

In `CLAUDE.md` §3's table, change `pleatwright/` (stick, pack, base, ...)
to `pleatwright/` (stick, pack, nest, base, ...).

- [ ] **Step 7: Run the full suite.**

Run (repo root): `make PYTHON=$PY test`
Expected: all pass.

- [ ] **Step 8: Commit.**

```bash
git add docs/superpowers/evidence/2026-10-10-branching-packer docs/superpowers/specs/2026-10-06-corigami-tree-to-model-pipeline.md CLAUDE.md
git commit -m "docs: branching-packer evidence (probe over named edits, 204/204 byte gate); deviation 1 and CLAUDE.md updated

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

After this task, use superpowers:finishing-a-development-branch. The PR to
`main` also carries PR #204, which this branch fast-forwarded onto; say so in
the PR body.

# River Routing (Efficiency Slice 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the packer put a child hub's pocket in a box beside its parent's flaps, wrapped by an L-, U- or ring-shaped river, and use such a layout only when it packs a tree on a strictly smaller grid than the tree uses today.

**Architecture:** A new strip kind, the *beside strip*, in `nest._Search` (the child box and the parent's flank blocks share one strip), plus a new mirrored span row builder in `pack.py` so a centred child pocket can be packed symmetrically. `pipeline.pack_options` first runs today's search unchanged, then two budgeted *beside searches* capped at today's chosen grid minus 2, and reapplies the slice-1 rule. Everything is behind a switch until the Phase 0 measurement (Task 6) passes its kill threshold.

**Tech Stack:** Python 3.14, pytest, numpy (existing `mcp_harness/.venv`).

**Spec:** `docs/superpowers/specs/2026-10-19-river-routing-design.md` (read it first; section numbers below are the spec's).

## Global Constraints

- `base.py`, `solve`, `shape`, `fold`, `certify/` and `app/` are not modified (spec §2, §10).
- `pack.candidates`, `_row_concrete`, `_row_concrete_asym`, `_row_concrete_span`, `_row_regions` and `_pocket_solutions` keep their current behaviour exactly; new behaviour lives in new functions or behind `beside=True` (spec §4.2, §4.3).
- Today's search in `pack_options` runs first and unchanged: the same candidates, `MAX_CANDIDATES = 400`, `SMALLER_WORK_BUDGET = 3_500_000` and caps (spec §5.1).
- Beside results must have a grid of at most `C − 2`, where C is today's chosen grid under `--layout auto`. When today found nothing, they use today's `n_max`. Beside searches never run on the doubled rung (spec §5.2).
- Every beside layout contains at least one beside strip (spec §4.3).
- Each beside search has its own tick budget **and** a cap on candidates passed to `base.build` (spec §5.3). No tree's `pack_secs` may exceed about 165 s.
- The kill threshold: stop if fewer than **5 of the 39** multi-hub artifact trees get a smaller chosen grid (spec §6).
- Tests use only the 51 artifact trees (`fixtures/full17_v3_sticks/`) and the named edits in `tests/test_pack_chain.py`. Never tardigrade / water bear (CLAUDE.md §5).
- Run everything from `mcp_harness/` with `<repo>/mcp_harness/.venv/bin/python` (written `PY` below). Worktrees have no `.venv` of their own.

## Review Focus

1. **A pocket whose hub has only axial flaps, in symmetric mode.** No pair can flank a centred child box. The beside part must yield nothing and must not crash (Task 4 test `test_axial_only_hub_has_no_symmetric_beside`).
2. **A river too wide for its box.** When `band()` returns None, the beside part skips that width; there is no exception and no zero-width flank (Task 3 test `test_beside_skips_boxes_too_small_for_the_band`).
3. **An `options.json` saved before this slice** (no `family` key), loaded by the app's history. `load_options` must accept it and treat it as `"today"` (Task 5 test `test_pre_slice_options_json_loads`).
4. **`BudgetExhausted` inside a beside search.** It must end that beside search only. Today's options must still be returned, and the record must say `"budget"` (Task 5 test `test_beside_budget_exhaustion_keeps_today`).
5. **Determinism of the flank-subset enumeration.** It must never iterate over a `set` or `dict` of chains whose order can vary. Two runs must yield identical layouts (Task 3 test `test_beside_candidates_are_deterministic`).

---

## File structure

| file | responsibility in this slice |
|---|---|
| `mcp_harness/pleatwright/pack.py` | new `_row_concrete_sym_span` (mirrored span rows); `Layout.family` field; `layout_from_dict` tolerant of its absence |
| `mcp_harness/pleatwright/nest.py` | beside strips in `_Search`; new generator `beside_candidates` |
| `mcp_harness/pleatwright/pipeline.py` | `pack_options(..., beside=...)`, the two beside searches, `Option.family`, records, save/load |
| `mcp_harness/pleatwright/efficiency.py` | `river_corners` |
| `mcp_harness/tests/test_river_routing.py` | all new tests in this slice (new file, so `test_nest.py` stays the 2026-10-10 slice's) |
| `docs/superpowers/evidence/2026-10-19-river-routing/` | baseline, Phase 0 probe, calibration, acceptance, artist packet |

---

### Task 1: Baseline corpus at `main` (before any code change)

**Files:**
- Create: `docs/superpowers/evidence/2026-10-19-river-routing/README.md` (first section only)

**Interfaces:**
- Produces: `BASE=~/Desktop/pleatwright_baseline_4a64d1ad/`, holding one folder per tree plus `records.jsonl`. Tasks 6 and 9 compare against it.

- [ ] **Step 1: Check the worktree is at the spec's baseline commit plus docs only**

Run: `git diff --stat 4a64d1ad -- mcp_harness` (from the repo root)
Expected: empty output (no code changes yet).

- [ ] **Step 2: Fold the corpus in the background (about 45 min)**

Run from `mcp_harness/`: `PY -m pleatwright.pipeline --out ~/Desktop/pleatwright_baseline_4a64d1ad --record ~/Desktop/pleatwright_baseline_4a64d1ad/records.jsonl`
Expected: 51 records, none with `failure`. Verdicts match slice 1: 44 `CERTIFIED` and 7 `OVERSIZE+LOCAL_SAT`.

- [ ] **Step 3: Record the baseline in the evidence README**

Write the command, the host and its load average, the commit, and the verdict counts. Also add a table of the 39 multi-hub trees giving each one's chosen grid C, `layout.chosen` and `pack_secs`, taken from `records.jsonl`. Multi-hub means the contracted tree has more than one hub (`len(ST.contract(sf).hubs) > 1`).

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/evidence/2026-10-19-river-routing/README.md
git commit -m "evidence: river routing baseline corpus at 4a64d1ad"
```

---

### Task 2: Mirrored span row builder

**Files:**
- Modify: `mcp_harness/pleatwright/pack.py` (new function after `_row_concrete_span`)
- Create: `mcp_harness/tests/test_river_routing.py`

**Interfaces:**
- Consumes: `_row_concrete_span(items, x0, x1, left, right, h, top, bot, y_paper, p, limit)` and `Item`.
- Produces: `_row_concrete_sym_span(items, x0, x1, side, h, top, bot, y_paper, p, limit=6) -> list[list[tuple]]`. It needs `x0 + x1 == N` and `side in ("paper", "hinge")`, the kind of both span ends. Each solution is a list of `(item, a, b, my, (vtag, ("explicit", vlines)))` entries that tile `[x0, x1]` exactly. A mirrored pair appears twice: once as `Item((left,), L, False, True)` at `[a, b]` and once as `Item((right,), L, False, True)` at `[x0 + x1 − b, x0 + x1 − a]`, with mirrored vlines. At most one axial item, centred. Because every entry uses the `("explicit", …)` htag, the unchanged `_row_regions` turns each entry into one `Region`.

- [ ] **Step 1: Write the failing tests**

```python
def _hub_items(roll, symmetric=True):
    """(con, hub, items) of the artifact tree's hub with the most pairs."""
    con = ST.contract(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0))
    hub = max(con.hubs, key=lambda h: sum(1 for it in PK._items(con, h, True) if not it.axial))
    return con, hub, PK._items(con, hub, symmetric)

@pytest.mark.parametrize("roll", ["dog_0", "bird_1", "cat_1"])
def test_sym_span_rows_tile_the_span_mirror_symmetrically(roll):
    con, hub, items = _hub_items(roll)
    pairs = [it for it in items if not it.axial][:2]
    found = 0
    N = 2 * max(30, 3 * sum(it.L for it in pairs))
    for x0 in range(0, N // 2 - 1):
        for side in ("paper", "hinge"):
            for h in range(1, 2 * max(it.L for it in pairs) + 2):
                for p in (0, 1):
                    for sol in PK._row_concrete_sym_span(pairs, x0, N - x0, side, h,
                                                         "hinge", "hinge", 0, p):
                        found += 1
                        spans = sorted((a, b) for _, a, b, _, _ in sol)
                        assert spans[0][0] == x0 and spans[-1][1] == N - x0
                        assert all(b1 == a2 for (_, b1), (a2, _) in zip(spans, spans[1:]))
                        mirrored = {(N - b, N - a) for a, b in spans}
                        assert mirrored == set(spans)
                        if side == "hinge":
                            lines = {v for e in sol for v in e[4][1][1]}
                            assert x0 in lines and N - x0 in lines
                        regs = PK._row_regions(N, 0, h, sol, "hinge", "hinge")
                        assert all(abs(PK._max_d(r) - r.L) < 1e-9 for r in regs)
    assert found > 0

def test_sym_span_rejects_two_axial_items():
    a = PK.Item((0,), 3, True); b = PK.Item((1,), 3, True)
    assert PK._row_concrete_sym_span([a, b], 4, 36, "hinge", 6, "hinge", "hinge", 0, 0) == []
```

(Imports at the top of the new test file: `os`, `pytest`, `from pleatwright import base as B, nest as NE, pack as PK, pipeline as PL, efficiency as EF, shape as SH, stick as ST`, `from artifact_trees import artifact_tree`, `from test_pack_chain import antlered, toed`, `FIX = os.path.join(os.path.dirname(__file__), "..", "fixtures", "full17_v3_sticks")`, and a module docstring citing the spec and the owner rule, in the style of `test_nest.py`.)

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `PY -m pytest tests/test_river_routing.py -q`
Expected: FAIL with `AttributeError: module 'pleatwright.pack' has no attribute '_row_concrete_sym_span'`.

- [ ] **Step 3: Implement `_row_concrete_sym_span` in `pack.py`**

Approach (the tests do not pin this down):
- **More than one axial item:** return `[]`.
- **No axial item:** call `_row_concrete_span` on the left members (as single `Item`s) over `[x0, c]` with `left=side` and `right="hinge"`, where `c = (x0 + x1) // 2`. This is how `nest` packs a pair half today: the mirrored pair columns meet on a hinge line at the axis.
- **One axial item of length L:** enumerate its centred width `wa`. It is `2L` exactly; if `_vopts` gives it a flex option, it may also be `2L + 2k` while `c − wa/2` keeps the parity `p`. Pack the left members over `[x0, c − wa // 2]` the same way, then add the axial entry `(axial, c − wa/2, c + wa/2, …, ("explicit", [c − wa/2, c + wa/2]))`. If there are no pairs, `x0` must equal `c − wa/2`.
- **Mirroring:** append each mirrored entry with its vlines reflected through `x0 + x1`.
- **Limit:** stop after `limit` solutions.

- [ ] **Step 4: Run the tests and confirm they pass**

Run: `PY -m pytest tests/test_river_routing.py -q`
Expected: PASS.

- [ ] **Step 5: Run the existing packer tests to confirm nothing moved**

Run: `PY -m pytest tests/test_nest.py tests/test_pack_chain.py tests/test_layout_choice.py -q -k "not octopus_2_fits and not scorpion_0_stops"`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pleatwright/pack.py mcp_harness/tests/test_river_routing.py
git commit -m "pack: mirrored span row builder for centred pockets"
```

---

### Task 3: Unmirrored beside strips and `beside_candidates`

**Files:**
- Modify: `mcp_harness/pleatwright/nest.py`, `mcp_harness/pleatwright/pack.py` (`Layout.family` only)
- Test: `mcp_harness/tests/test_river_routing.py`

**Interfaces:**
- Consumes: `band`, `Box`, `_row_concrete_span`, `_pocket_solutions`, `tick`.
- Produces:
  - `pack.Layout.family: str = "today"`, a new last field. `layout_from_dict` reads `d.get("family", "today")`.
  - `nest._Search(con, N, symmetric, beside=False)`. `fill`, `part` and `child` now yield `(regs, pockets, nbeside)`, where `nbeside` is the number of beside strips used. With `beside=False` it is always 0 and the layouts are unchanged.
  - `nest.beside_candidates(con, *, N_min=None, N_max=160, per_N=60, symmetric=True)` yields `Layout`s with `family="beside"`, in increasing N. It yields only layouts with `nbeside >= 1`, and yields nothing when `con` has a single hub.
  - Constants: `BESIDE_PER_POCKET = 2` (beside strips per pocket) and `FLANK_MAX = 2` (items per flank set; a mirrored pair counts as one). Task 6 may tune them and records the final values.
  - Part tuple: `("beside", river_id, flank)`, where `flank` is a tuple of the hub's item chain-tuples in a fixed order. The hub's `("flaps",)` part then packs only the items not in any flank, and is omitted if none are left.

- [ ] **Step 1: Write the failing tests**

```python
MULTI = ["dog_0", "bird_1", "ant_0", "lizard_1", "crab_1"]

def _con(roll, scale=1.0):
    return ST.contract(ST.load_roll(os.path.join(FIX, roll + ".json"), scale))

def _today_n(roll):
    return {"dog_0": 46, "bird_1": 40, "ant_0": 102, "lizard_1": 64, "crab_1": 50}[roll]

@pytest.mark.parametrize("roll", MULTI)
def test_unmirrored_beside_layouts_tile_and_build(roll):
    con = _con(roll)
    sigma = SH.choose_sigma(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0), con)
    got = list(itertools.islice(NE.beside_candidates(con, symmetric=False,
                                                     N_max=_today_n(roll) + 20), 5))
    assert got, "some unmirrored beside layout exists within today's N + 20"
    for lay in got:
        assert lay.family == "beside"
        assert not B.build(lay, con, sigma).errors

def test_beside_rivers_bend():
    """Some beside layout of dog_0 has a river band that is an L, U or ring, not a straight band."""
    con = _con("dog_0")
    lay = next(NE.beside_candidates(con, symmetric=False, N_max=66))
    bent = [r for r in lay.regions if r.kind == "river" and r.more]
    assert bent

def test_beside_off_changes_nothing():
    """nest.candidates (beside off) on the antlered dog: the 2026-10-10 pin."""
    con = ST.contract(ST.load_tree(antlered("dog_0"), 1.0))
    lay = next(NE.candidates(con, symmetric=False, N_max=62))
    assert lay.family == "today" and lay.N == 62

def test_single_hub_tree_has_no_beside_layouts():
    assert next(NE.beside_candidates(_con("octopus_0"), symmetric=False, N_max=40), None) is None

def test_beside_skips_boxes_too_small_for_the_band():
    con = _con("dog_0")
    s = NE._Search(con, 20, False, beside=True)
    river = next(c for c in con.chains if not c.leaf and c.u == con.root)
    flank = (PK._items(con, con.root, False)[0].chains,)
    tiny = NE.Box(0, 0, 2 * river.length, 4, "paper", "hinge", "paper", "paper")
    assert list(s.part(con.root, ("beside", river.id, flank), tiny, False)) == []

def test_beside_candidates_are_deterministic():
    con = _con("crab_1")
    run = lambda: [PK.layout_to_dict(l) for l in itertools.islice(
        NE.beside_candidates(con, symmetric=False, N_max=60), 3)]
    assert run() == run()

def test_family_survives_json_and_defaults_to_today():
    lay = next(NE.beside_candidates(_con("dog_0"), symmetric=False, N_max=66))
    d = PK.layout_to_dict(lay)
    assert PK.layout_from_dict(json.loads(json.dumps(d))).family == "beside"
    d.pop("family")
    assert PK.layout_from_dict(d).family == "today"
```

(Add `import itertools, json` to the file.) The N's in `_today_n` are the 2026-10-06 symmetric grids from `bp_eff.jsonl`. Their only purpose is to set a generous `N_max`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `PY -m pytest tests/test_river_routing.py -q -k "beside or family or single_hub"`
Expected: FAIL (`beside_candidates` does not exist; `Layout` has no `family`).

- [ ] **Step 3: Add `Layout.family` and make `layout_from_dict` tolerate its absence**

- [ ] **Step 4: Thread `nbeside` through `_Search.fill`, `part`, `child` and `candidates`, with no new behaviour yet**

Run: `PY -m pytest tests/test_nest.py -q`
Expected: PASS. Every existing nest test still pins the same N's.

- [ ] **Step 5: Implement unmirrored beside strips in `_Search`**

- **`parts(hub, axial)`.** When `self.beside` is set, also return part lists in which up to `BESIDE_PER_POCKET` of the `("child", id)` parts are replaced by `("beside", id, flank)`. Flank sets are enumerated as subsets of the hub's items, of size 1..`FLANK_MAX`, in a fixed order: items sorted by `(−L, chains)`. Remove the flanked items from the hub's `("flaps",)` part, for example by carrying the remaining items in `("flaps", remaining)`; `flaps()` packs exactly those. Enumerate only part lists with at least one beside part (the plain lists are today's family). `fill` loops over these part lists outside its existing `orders(...)` loop.
- **`part(...)` for `("beside", river, flank)` on strip box B (full width of the pocket, height h).** Try three arrangements. Pocket-side kinds are B.left and B.right; inner sides are `"hinge"`:
  - `[C | F]`: C = `Box(B.x0, B.y0, B.x0 + wc, B.y1, B.top, B.bot, B.left, "hinge")`, with the flank span `[B.x0 + wc, B.x1]` given `left="hinge"` and `right=B.right`.
  - `[F | C]`: the mirror image of the above.
  - `[F1 | C | F2]`: the flank items split into two non-empty prefix/suffix groups in their fixed order.
- **C and the flanks.** For each arrangement and each C width `wc` (every width whose `band()` is not None and whose `_parity_ok` holds), call `band(river, W, C)`. Fill the child pocket with `fill(child, pocket, axial=False)`. Pack each flank block with `_pocket_solutions(flank_items, N, B.y0, B.y1, B.top, B.bot, rowfn=<_row_concrete_span on the flank span>)`, keeping regions that pass `_max_d == L` and `_parity_ok`. Yield `nbeside = 1 + child's nbeside`. Call `tick()` once per (arrangement, wc) and once per yielded combination. Use `self.fcache` for flank and child feasibility, as `feasible()` does.
- **`beside_candidates`.** It is `candidates` with `_Search(..., beside=True)`. It yields only results with `nbeside >= 1`, sets `family="beside"`, and yields nothing if `len(con.hubs) == 1`.

- [ ] **Step 6: Run the tests and confirm they pass**

Run: `PY -m pytest tests/test_river_routing.py tests/test_nest.py -q`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/pleatwright/nest.py mcp_harness/pleatwright/pack.py mcp_harness/tests/test_river_routing.py
git commit -m "nest: unmirrored beside strips (L/U/ring rivers) and beside_candidates"
```

---

### Task 4: Symmetric (centred) beside strips

**Files:**
- Modify: `mcp_harness/pleatwright/nest.py`
- Test: `mcp_harness/tests/test_river_routing.py`

**Interfaces:**
- Consumes: `_row_concrete_sym_span` (Task 2); the `_Search` beside machinery (Task 3); `mirror`.
- Produces: `beside_candidates(con, symmetric=True)` yields mirror-symmetric beside layouts. `_Search.flaps(hub, box, axial=True)` uses `_row_concrete_sym_span` whenever `box` is not the full paper width (`(box.x0, box.x1) != (0, N)`). Full-width boxes take today's path unchanged.

- [ ] **Step 1: Write the failing tests**

```python
def _pair_map(con):
    pm = {}
    for a, b in con.pairs:
        pm[a], pm[b] = b, a
    for _, _, m in PK.hub_pairs(con):
        pm.update(m)
    return pm

def _sig(r):
    return (r.chain, tuple(sorted(r.rects)), tuple(r.vlines), tuple(r.hlines))

@pytest.mark.parametrize("roll", MULTI)
def test_symmetric_beside_layouts_are_their_own_mirror_image(roll):
    con = _con(roll)
    sigma = SH.choose_sigma(ST.load_roll(os.path.join(FIX, roll + ".json"), 1.0), con)
    pm = _pair_map(con)
    got = list(itertools.islice(NE.beside_candidates(con, symmetric=True,
                                                     N_max=_today_n(roll) + 20), 3))
    assert got
    for lay in got:
        assert {_sig(NE.mirror(r, lay.N, {r.chain: pm.get(r.chain, r.chain)}))
                for r in lay.regions} == {_sig(r) for r in lay.regions}
        assert not B.build(lay, con, sigma).errors

def test_a_symmetric_beside_river_is_a_u_or_ring():
    con = _con("dog_0")
    lay = next(NE.beside_candidates(con, symmetric=True, N_max=66))
    bent = [r for r in lay.regions if r.kind == "river" and r.more]
    assert bent and all(len(r.vlines) == 2 for r in bent)   # both side arms

def test_axial_only_hub_has_no_symmetric_beside():
    con = _con("dog_0")
    s = NE._Search(con, 60, True, beside=True)
    river = next(c for c in con.chains if not c.leaf and c.u == con.root)
    axial = next((it for it in PK._items(con, con.root, True) if it.axial), None)
    if axial is None:
        pytest.skip("dog_0's root has no axial flap")
    box = NE.Box(0, 0, 60, 20, "paper", "hinge", "paper", "paper")
    assert list(s.part(con.root, ("beside", river.id, (axial.chains,)), box, True)) == []
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `PY -m pytest tests/test_river_routing.py -q -k "symmetric_beside or u_or_ring or axial_only"`
Expected: FAIL (`symmetric=True` yields nothing yet).

- [ ] **Step 3: Implement the centred arrangement `[F | C | mirror(F)]` for `axial=True` pockets**

- **Flank sets.** On the axis they contain only mirrored pairs; a set holding an axial item yields nothing.
- **C.** Enumerate `wc` with `(box.x1 − box.x0 − wc)` even, giving `C = Box(c − wc/2, B.y0, c + wc/2, B.y1, B.top, B.bot, "hinge", "hinge")` with `c = (box.x0 + box.x1) // 2`. Build the band, then fill the child pocket with `axial=True`.
- **The left flank.** Pack it on `[box.x0, c − wc/2]` with `left=box.left` and `right="hinge"`, using the left members as single items, as `part()` packs a `("pair", i)` half today. Add `mirror(r, N, pm)` of each of its regions, with `pm` built as in the test helper `_pair_map`.
- **`flaps()`.** For `axial=True` on a box that is not full width, pass `rowfn=lambda its, hw, h, t, b, yp, p, limit=6: _row_concrete_sym_span(its, box.x0, box.x1, box.left, h, t, b, yp, p, limit)`. `box.left == box.right` always holds for a centred box.

- [ ] **Step 4: Run the tests and confirm they pass, along with every nest test**

Run: `PY -m pytest tests/test_river_routing.py tests/test_nest.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/pleatwright/nest.py mcp_harness/tests/test_river_routing.py
git commit -m "nest: symmetric beside strips (centred child pocket, U/ring river)"
```

---

### Task 5: `pack_options` beside searches, records and persistence (behind the switch)

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py`
- Test: `mcp_harness/tests/test_river_routing.py`

**Interfaces:**
- Consumes: `nest.beside_candidates` (Tasks 3–4), `pack.work_budget`, `pack.BudgetExhausted`, `B.build`, `EF.metrics`, `_verdict`, `_context`.
- Produces:
  - `BESIDE = False`, the module switch (spec §6). It becomes True in Task 8.
  - `BESIDE_WORK_BUDGET = 1_000_000` ticks and `BESIDE_MAX_BUILDS = 50`, both per beside search. These are initial values; Task 7 calibrates them.
  - `pack_options(tree, *, scale=1.0, work_budget=None, beside: bool | None = None)`. `None` means use `BESIDE`.
  - `Option.family: str = "today"`, a new last field.
  - `PackOptions.beside: dict`, of the form `{"symmetric": int | str, "smaller": int | str}`. An int is the beside search's grid; a str is one of `"none_below_cap"`, `"budget"`, `"builds"`, `"no_child_hub"`, `"doubled"` or `"off"`. It defaults to `{}`.
  - `summary()` adds `"beside": self.beside` and puts `"family"` inside each option's dict.
  - `_layout_record` adds `"family": chosen.family` and `"beside": opts.beside`.
  - `save_options` writes `"family"` for each option. `load_options` reads `d.get("family", "today")` and `doc["summary"].get("beside", {})`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("roll", ["dolphin_0", "bird_1", "starfish_0"])
def test_beside_off_is_todays_pack_options(roll):
    off = PL.pack_options(roll, beside=False).summary()
    assert off["beside"] == {"symmetric": "off", "smaller": "off"}
    off.pop("beside")
    for k in ("symmetric", "smaller"):
        if off[k]:
            assert off[k].pop("family") == "today"
    # today's slice-1 expectations still hold
    assert {"dolphin_0": ("ask", 50), "bird_1": ("symmetric", 40),
            "starfish_0": ("only_unmirrored", None)}[roll] == \
        (off["verdict"], off["symmetric"] and off["symmetric"]["grid"])

def _chosen_grid(o):
    opt, _ = PL._choose(o, "auto", "flag")
    return opt.layout.N

@pytest.mark.parametrize("roll", ["dog_0", "bird_1", "lizard_1", "crab_1"])
def test_beside_never_grows_the_chosen_grid(roll):
    today, new = PL.pack_options(roll, beside=False), PL.pack_options(roll, beside=True)
    assert _chosen_grid(new) <= _chosen_grid(today)
    for k in ("symmetric", "smaller"):
        v = new.beside[k]
        assert isinstance(v, str) or v <= _chosen_grid(today) - 2

def test_single_hub_tree_skips_beside():
    o = PL.pack_options("octopus_0", beside=True)
    assert o.beside == {"symmetric": "no_child_hub", "smaller": "no_child_hub"}

def test_beside_budget_exhaustion_keeps_today(monkeypatch):
    monkeypatch.setattr(PL, "BESIDE_WORK_BUDGET", 1)
    today = PL.pack_options("dog_0", beside=False)
    o = PL.pack_options("dog_0", beside=True)
    assert o.beside == {"symmetric": "budget", "smaller": "budget"}
    assert _chosen_grid(o) == _chosen_grid(today)

def test_pre_slice_options_json_loads(tmp_path):
    o = PL.pack_options("dolphin_0", beside=False)
    PL.save_options(o, str(tmp_path))
    p = tmp_path / "options.json"
    doc = json.loads(p.read_text())
    for d in doc["options"].values():
        d.pop("family")
        d["layout"].pop("family")
    doc["summary"].pop("beside")
    p.write_text(json.dumps(doc))
    r = PL.load_options("dolphin_0", str(tmp_path))
    assert r.symmetric.family == "today" and r.beside == {}
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `PY -m pytest tests/test_river_routing.py -q -k "pack_options or beside_never or skips_beside or budget_exhaustion_keeps or pre_slice"`
Expected: FAIL (`pack_options` has no `beside` argument).

- [ ] **Step 3: Implement the beside searches after today's search in `pack_options`**

- **Today's search.** Keep the existing body unchanged as `_pack_options_today(...)`.
- **Skip cases.** If the switch is off: `beside = {"symmetric": "off", "smaller": "off"}`. Else if `len(con.hubs) == 1`: `"no_child_hub"`. Else if the verdict is `"doubled"`: `"doubled"`.
- **The searches.** Otherwise compute `C = _choose(today, "auto", "flag")[0].layout.N`. If the verdict is `"none"`, use `n_max` instead and do not subtract 2. Then run `_search_beside(con, sigma, symmetric=s, n_max=C − 2)` for `s = True` and `s = False`, each inside `PK.work_budget(BESIDE_WORK_BUDGET)`:
  - It iterates `NE.beside_candidates(con, symmetric=s, N_max=n_max)` and returns the first layout whose `B.build` has no errors.
  - It raises an internal `_BuildCap` after `BESIDE_MAX_BUILDS` builds. Catch it, and catch `PK.BudgetExhausted`, recording `"builds"` / `"budget"` respectively.
  - Returning None gives `"none_below_cap"`.
- **The new options.** `S' = beside sym Option` (name `"symmetric"`, rung `"symmetric"`, `family="beside"`) if found, else today's. For `U'`, take the smaller-grid of today's smaller option and the beside unmirrored Option (name `"smaller"`, rung `"asymmetric"`, `family="beside"`); on a tie keep today's. Then:
  - Recompute `verdict, gain = _verdict(S', U', today.doubled)`.
  - Set `n_smaller` to `U'.layout.N` if U' exists, else keep today's value.
  - Return a new `PackOptions` carrying `beside` and today's `tried`. Beside builds do not add to `tried`.

- [ ] **Step 4: Add `family` and `beside` to `summary`, `_layout_record`, `save_options` and `load_options`**

- [ ] **Step 5: Run the new tests, then the slice-1 tests**

Run: `PY -m pytest tests/test_river_routing.py tests/test_layout_choice.py -q -k "not octopus_2_fits and not scorpion_0_stops"`
Expected: PASS. The switch is off by default, so `test_layout_choice.py` is unaffected.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pleatwright/pipeline.py mcp_harness/tests/test_river_routing.py
git commit -m "pipeline: beside searches after today's packing, behind a switch"
```

---

### Task 5b: `river_corners` metric

**Files:**
- Modify: `mcp_harness/pleatwright/efficiency.py`
- Test: `mcp_harness/tests/test_river_routing.py`

**Interfaces:**
- Produces: `efficiency.river_corners(lay) -> int`, and `metrics(...)["river_corners"]`. It counts the lattice points strictly inside the paper (`0 < x < N`, `0 < y < N`) that are vertices of some river region's boundary. A point is a vertex when 1 or 3 of the region's cells touch it, or 2 diagonal cells do (the latter counts twice), the same rule as `corigami_samples/regions.py` `corners()`.

- [ ] **Step 1: Write the failing tests**

```python
def test_river_corners_counts_only_interior_bends():
    straight = PK.Region(0, (0, 10, 62, 12), [], [10], "river", 2)
    reg, _ = NE.band(7, 2, NE.Box(0, 0, 31, 5, "paper", "hinge", "paper", "hinge"))
    ring, _ = NE.band(8, 2, NE.Box(10, 10, 30, 30, "hinge", "hinge", "hinge", "hinge"))
    mk = lambda rs: PK.Layout(62, rs, [], [], [])
    assert EF.river_corners(mk([straight])) == 0
    assert EF.river_corners(mk([reg])) == 2          # L: outer (31,5) and inner (29,3)
    assert EF.river_corners(mk([ring])) == 8

def test_metrics_carry_river_corners():
    con, lay, base = _first_symmetric_layout("dolphin_0")
    assert EF.metrics(lay, con, base, 1.0)["river_corners"] == 0
```

(`_first_symmetric_layout(roll)` is a test helper: `next(PK.candidates(con, symmetric=True, N_max=...))` built with `B.build`, the same as `test_layout_choice._first_symmetric`.)

- [ ] **Step 2: Run, confirm the tests fail; implement; run, confirm they pass**

Run: `PY -m pytest tests/test_river_routing.py -q -k river_corners`
Expected: FAIL, then PASS after implementing.

- [ ] **Step 3: Confirm the slice-1 metric pins still hold**

Run: `PY -m pytest tests/test_layout_choice.py -q -k metrics_match`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add mcp_harness/pleatwright/efficiency.py mcp_harness/tests/test_river_routing.py
git commit -m "efficiency: river_corners metric"
```

---

### Task 6: Phase 0 probe and the kill decision (STOP GATE)

**Files:**
- Create: `docs/superpowers/evidence/2026-10-19-river-routing/phase0_probe.py`, `phase0.jsonl`, and a README section

**Interfaces:**
- Consumes: `PL.pack_options(roll, beside=False|True)`, `PL._choose`, `PK.work_used`.

- [ ] **Step 1: Write `phase0_probe.py ROLL... > phase0.jsonl`**

For each multi-hub roll, run `pack_options` with `beside=False` and with `beside=True`. Emit one JSON line per roll with these fields:
- today: S, U, verdict and C;
- beside: `beside` (S_b / U_b or the reason), the new verdict and the new chosen grid;
- the `family` of the chosen option;
- seconds for each call, measured with `time.perf_counter`.

It calls only the real `pack_options`; it never copies search code (spec §6).

- [ ] **Step 2: Run it on the 39 multi-hub trees in the background**

Run from `mcp_harness/`: `PYTHONPATH=. PY ../docs/superpowers/evidence/2026-10-19-river-routing/phase0_probe.py $(PY -c "…list multi-hub rolls…") > ../docs/superpowers/evidence/2026-10-19-river-routing/phase0.jsonl`
Expected: 39 lines.

- [ ] **Step 3: Write the README section**

Include a table per tree (C before, C after, family, S_b, U_b, seconds) and the count of trees whose chosen grid shrank. Also include two kill counts: unmirrored-only, the chosen grid if only U_b had been used, and both arrangements.

- [ ] **Step 4: Apply the kill threshold**

- **Fewer than 5 of 39 shrink:** commit the evidence, leave `BESIDE = False`, and STOP. Report to the owner with the table; do not do Tasks 7–10.
- **Otherwise:** note which trees shrank and by how much, then continue.

- [ ] **Step 5: Commit**

```bash
git add docs/superpowers/evidence/2026-10-19-river-routing/
git commit -m "evidence: river routing phase 0 measurement"
```

---

### Task 7: Calibrate the beside budget and build cap

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (the constants and their comment), `mcp_harness/pleatwright/nest.py` (`BESIDE_PER_POCKET`, `FLANK_MAX` if tuned)
- Create: `docs/superpowers/evidence/2026-10-19-river-routing/budget_probe.py` and a README section
- Test: `mcp_harness/tests/test_river_routing.py`

- [ ] **Step 1: Measure ticks and builds to the first beside success for each shrinking tree**

Use `phase0.jsonl`'s winners. Find the largest measured count of ticks and the largest count of builds; the largest-ticks tree is the "budget anchor".

- [ ] **Step 2: Set the constants as slice 1 did**

`BESIDE_WORK_BUDGET` is the anchor's ticks plus 3%; `BESIDE_MAX_BUILDS` is the largest builds count plus 10. If the anchor's seconds plus today's `pack_secs` for any multi-hub tree goes past about 165 s, lower the budget to fit, and record which trees are lost.

- [ ] **Step 3: Add pinning tests**

These are the slice-1 style calibration tests: `test_<anchor>_fits_the_beside_budget` asserts the anchor still shrinks to its Phase 0 grid with `beside=True`. `test_beside_ticks_are_deterministic` runs `pack_options(<anchor>, beside=True)` twice and asserts the summaries are identical.

- [ ] **Step 4: Run, confirm they pass; commit**

Run: `PY -m pytest tests/test_river_routing.py -q`

```bash
git add mcp_harness/pleatwright/ mcp_harness/tests/test_river_routing.py docs/superpowers/evidence/2026-10-19-river-routing/
git commit -m "pipeline: calibrated beside budget and build cap"
```

---

### Task 8: Switch on, end-to-end pins, docs

**Files:**
- Modify: `mcp_harness/pleatwright/pipeline.py` (`BESIDE = True`), `mcp_harness/tests/test_river_routing.py`, `mcp_harness/tests/test_nest.py` (only if toed crab_3 now packs), `CLAUDE.md` §2

- [ ] **Step 1: Write the end-to-end test from Phase 0's largest drop**

`test_<roll>_folds_on_a_smaller_beside_grid(tmp_path)` calls `PL.run(<roll>, tmp_path, certify_global=True, verbose=False)` and asserts:
- `rec["layout"]["family"] == "beside"`;
- `rec["grid_size"] == <phase-0 grid>`;
- `rec["global_verdict"] == "CERTIFIED"` (or the baseline's verdict, if that was `OVERSIZE+LOCAL_SAT`);
- `ff[0] == ff[1]` for `solving_flat_foldable`.

Pick a roll whose fold takes under 60 s in the baseline records.

- [ ] **Step 2: Set `BESIDE = True` and run the whole suite**

Run: `make PYTHON=<repo>/mcp_harness/.venv/bin/python test` (from the repo root)
Expected: PASS. Any slice-1 test that pinned a grid now beaten by a beside layout is a deliberate update:
- Change its expectation to the Phase 0 numbers and say so in the commit message.
- `test_dolphin_asks`, `test_bird_keeps_symmetry_without_asking` and `test_lizard_2_sits_exactly_on_the_threshold` are candidates to move.
- `test_a_branching_tree_past_the_grid_cap_fails_at_packing`: if toed crab_3 now packs, switch it to toed spider_2, the edit furthest over the cap, or assert the new outcome (spec §8.5).

- [ ] **Step 3: Update CLAUDE.md §2**

Add one sentence after the packing-ladder sentence: after the ladder, `pack_options` tries beside layouts, in which a child hub's pocket sits beside its parent's flaps wrapped by an L, U or ring river. It keeps one only when its grid is below today's chosen grid (spec 2026-10-19).

- [ ] **Step 4: Commit**

```bash
git add -A mcp_harness CLAUDE.md
git commit -m "pipeline: beside layouts on by default"
```

---

### Task 9: Corpus acceptance (spec §8)

**Files:**
- Create: README sections, `records.jsonl` summary and an `edits.jsonl` probe in `docs/superpowers/evidence/2026-10-19-river-routing/`

- [ ] **Step 1: Fold the corpus in the background**

Run from `mcp_harness/`: `PY -m pleatwright.pipeline --out ~/Desktop/pleatwright_river_routing --record ~/Desktop/pleatwright_river_routing/records.jsonl`
Expected: 51 records, no `failure` (§8.1).

- [ ] **Step 2: Byte identity (§8.2)**

For every tree whose folder name (`<Subject>_<grid>`) also exists in `BASE`, run `filecmp.cmp(..., shallow=False)` on the four files.
Expected: every compared file identical. Every tree with no counterpart has `layout.family == "beside"`.

- [ ] **Step 3: Changed trees (§8.3)**

For each changed tree, check that the verdict is `CERTIFIED`, or `OVERSIZE+LOCAL_SAT` where `BASE`'s was, and that every solving and shaping vertex is flat-foldable. **Open each `overview.png`** and write one line on what it reads as. Look at the model; don't score it.

- [ ] **Step 4: Grid report (§8.4)**

Make a table for the 39 multi-hub trees: C before/after, `n_over_bound`, `slack_fraction`, `mean_layers` and `river_corners`, with medians.

- [ ] **Step 5: Branching edits (§8.5)**

Write a probe script that, for the 74 edits plus `lopsided`, records `pack_options(beside=False)` against `pack_options(beside=True)` chosen grids, and states whether toed crab_3, elephant_3 and spider_2 now fit under the cap.

- [ ] **Step 6: Time and determinism (§8.6)**

Find the largest `pack_secs` (expected ≤ about 165 s). Then compute `pack_options(r).summary()` for all 51 rolls in two separate processes and compare the dumps.
Expected: identical.

- [ ] **Step 7: Suites (§8.7)**

Run `make test`, then `cd app/web && npm test && npm run build`.
Expected: all pass.

- [ ] **Step 8: Commit the evidence**

```bash
git add docs/superpowers/evidence/2026-10-19-river-routing/
git commit -m "evidence: river routing corpus acceptance"
```

---

### Task 10: Artist packet (spec §9)

**Files:**
- Create: `docs/superpowers/evidence/2026-10-19-river-routing/artist/` (SVGs, PNG renders, `README.md`)

- [ ] **Step 1: Copy before/after packing and solving CPs for 3–4 changed trees**

Pick the largest grid drops, with at least one symmetric U and one L if both occur. Name the files `<roll>_<grid>_<before|after>_{packing,solving}_cp.svg` and render a PNG beside each. Rendering method is the builder's choice; for example, rasterise the SVG.

- [ ] **Step 2: Add the two current CPs with the highest `mean_layers` from the acceptance records**

- [ ] **Step 3: Write the one-page README**

It is for someone who knows box pleating but not this project. Cover:
- what each file is;
- the colours (red = mountain, blue = valley, green = hinge, black = border);
- each tree's grid and mean layers per flap;
- the three questions, verbatim from spec §9: could you collapse this by hand; do the river bends look like good box pleating; for these models, does the grid size or the flap thickness worry you more.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/evidence/2026-10-19-river-routing/artist/
git commit -m "evidence: artist review packet for river routing"
```

---

## Prior-art adaptations (CLAUDE.md §0)

| source | adapted into | rejected |
|---|---|---|
| COrigami §3.2 and its 18 released packings (L, Π/U, nested Π) | the beside-strip shapes: L (corner, Task 3) and U/ring (edge/centred, Tasks 3–4) | Π-with-feet and incremental wall-following (non-rectangular remainders) |
| BP Studio `roughContour.ts` / `expand.ts` | `nest.band()` already is the one-rectangle case, reused unchanged | the `riverCorner.ts` pairing check (band is constant-width by construction) |
| BP Studio optimiser (sheet size first, bends a cost) | today's search runs first, and beside layouts must beat its grid (Task 5) | bend minimisation at a fixed N (recorded as `river_corners` only, Task 5b) |
| Wong 5.4 (nested U rivers compact rows) | centred U arrangement (Task 4) | meanders that move thickness into the river (spec non-goal) |
| Slice 1 calibration method | tick budget and build cap set from measured winners (Task 7) | wall-clock budgets |

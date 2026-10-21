# Base Inspection Loop — Phases 1 & 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the agent a deterministic, read-only account of what the compiler
actually built — how the served tree differs from the requested one — and two
human-facing renders of the packing, without changing a single byte of what the
pipeline serves.

**Architecture:** Three layers, strictly bottom-up. (1) A pure-Python metric
module comparing two trees by their **leaf-to-leaf path matrix** on the free
(unrooted) tree — the quantity the packer consumes and the shadow realises.
(2) Plumbing so the *served* candidate survives the rescue ladder on **both**
ladder paths, plus a read-only `read_base()` MCP tool and a quiet `[FIDELITY]`
oracle that fires only on drift no existing marker explains. (3) Two Pillow
renderers written to disk for humans; **no model sees them in this plan.**

**Tech Stack:** Python 3, pytest, Pillow 12.2.0, numpy 2.4.3, pybind11 C++
extension (`headless_treemaker`), FastMCP, FastAPI/websockets bridge.

**Source spec:** `docs/superpowers/specs/2026-08-04-base-inspection-loop-design.md`
(commits `01c00f0`, `0e32541`). **Phase 3 is out of scope for this plan** and
gets its own plan only after Phase 2 reports.

**Deliberately not in this plan, and why:**

| Spec § | Item | Why not here |
|---|---|---|
| §3.5 | Everything about the agent looking | Phase 3. Its own plan, after the Phase 2 report and only if both preconditions pass. |
| §5 | The one `SimSession.screenshot()` calibration capture | The spec itself says "not a CI step, not a gate, and not on any critical path", and it needs a **headed** browser on a dev machine — it cannot run in this plan's test discipline. Schedule it as a standalone probe; it closes §2's open item whenever it runs. |
| §3.4 | River rendering | Needs an internal-node position binding that does not exist. Named future work in the spec's §8. |
| §9 Q2 | Frontend panel for the packing diagram | Spec puts it out of scope; the renders land as files. |

## Global Constraints

- **Build and run tests from the MAIN checkout**, never a worktree. A worktree
  borrowing main's `.so` reports 27 baseline failures instead of ~3.
- Python is `mcp_harness/.venv/bin/python`. Full suite: `make test`. Single
  file: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/<f> -v --timeout=420`.
- **Never** run bare `make test` without a timeout on macOS — it does not
  terminate. Always `--timeout=420`.
- Any script calling `server.draft_and_compile_full_base` **must** be under
  `if __name__ == "__main__":`. Without it every compile dies and reports a
  FALSE pack failure.
- Check host CPU for orphaned processes before timing anything.
- **Never freeze a byte hash over rendered PNGs.** Assert structure only.
- **No fold bytes change in this plan.** `test_attempt0_unchanged` must stay
  byte-identical for all four templates.
- Tests must read the **real production call site**. A count-based test is not
  a pin — a prior gate stayed green while the production call was gutted.
- `role:"tool"` messages carry a plain string; images cannot ride that path.
  (Relevant to Phase 3 only; noted so nobody builds toward it here.)
- New Python modules under `mcp_harness/` import flat (`import shadow_tree`),
  matching `anatomy_oracle`, `pair_reconcile`, `cp_audit`. Root `conftest.py`
  puts `mcp_harness/` on `sys.path`.
- Commit after every task. Conventional-commit subjects, `Co-Authored-By:
  Claude Opus 5 <noreply@anthropic.com>` trailer.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `mcp_harness/shadow_tree.py` | **Create.** Pure metric: leaf sets, leaf-to-leaf path matrix, `shadow_diff`. No engine import, no I/O. | 1, 2 |
| `mcp_harness/tests/test_shadow_tree.py` | **Create.** Metric unit tests + the three invariance pins. | 1, 2 |
| `mcp_harness/server.py` | **Modify.** Parent-path serve record (`:1350-1445`), child-path payload (`:372`, `:392-407`), `read_base()` tool. | 3, 4 |
| `mcp_harness/tests/test_read_base.py` | **Create.** Plumbing through the real tool + no-recompile guarantee. | 3, 4 |
| `mcp_harness/fidelity_oracle.py` | **Create.** `decide()` / `message()`, five suppressions, unexplained-drift rule. Pure, no I/O — mirrors `anatomy_oracle.py`. | 5 |
| `mcp_harness/tests/test_fidelity_oracle.py` | **Create.** Suppression coverage + the marker-explains-it rule. | 5 |
| `web/server.py` | **Modify.** `[FIDELITY]` bridge wiring beside `[ANATOMY]`. | 6 |
| `web/tests/test_server_fidelity_oracle.py` | **Create.** Bridge contract, mirroring `test_server_cp_oracle.py`. | 6 |
| `mcp_harness/mesh_report.py` | **Modify.** `_anatomy_lines` prints `position`. | 7 |
| `mcp_harness/tree_render.py` | **Create.** Both renderers: packing diagram, tree sheet. | 8, 9 |
| `mcp_harness/tests/test_tree_render.py` | **Create.** Structural assertions only. | 8, 9 |
| `.github/workflows/ci.yml` | **Modify.** Pin Pillow explicitly. | 8 |
| `mcp_harness/benchmark_subjects.py` | **Modify.** New scorecard columns. | 10 |

---

## Task 1: The shadow-tree metric

**Files:**
- Create: `mcp_harness/shadow_tree.py`
- Test: `mcp_harness/tests/test_shadow_tree.py`

**Interfaces:**
- Consumes: nothing (leaf module).
- Produces:
  - `leaf_ids(nodes) -> list[int]`
  - `root_distance(nodes, nid) -> float | None`
  - `leaf_path_matrix(nodes) -> dict[tuple[int,int], float]` — keys are
    `(a, b)` with `a < b`, values the undirected tree distance.
  - `shadow_diff(requested_nodes, served_nodes, locs=None) -> dict` with keys
    `invented: int | None`, `dropped: list[int]`, `contracted: list[int]`,
    `path_drift_max: float`, `path_drift_mean: float`,
    `worst_pairs: list[tuple[int,int]]`, `span: float`, `comparable: bool`.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_shadow_tree.py`:

```python
"""The shadow-tree metric: does the served tree realise the requested one?

The metric is the LEAF-TO-LEAF PATH MATRIX on the free (unrooted) tree, never
parent pointers. See the spec's 3.3.1 -- three shipped, anatomy-PRESERVING
paths (rehome, contract_slivers, path reconciliation) change parent pointers,
so an id-keyed diff reports a flood of defects on transformations that change
no anatomy. Task 2's invariance pins are the tests that hold that line.
"""
import shadow_tree as st


# root 0; two leaves 1,2 hanging off it at 0.4 and 0.6
SIMPLE = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 1, "parent_id": 0, "length": 0.4},
    {"id": 2, "parent_id": 0, "length": 0.6},
]

# root 0 -> junction 3 (0.2) -> leaves 1 (0.4) and 2 (0.6); leaf 4 off root
DEEPER = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 3, "parent_id": 0, "length": 0.2},
    {"id": 1, "parent_id": 3, "length": 0.4},
    {"id": 2, "parent_id": 3, "length": 0.6},
    {"id": 4, "parent_id": 0, "length": 0.5},
]


def test_leaf_ids_excludes_root_and_junctions():
    assert st.leaf_ids(SIMPLE) == [1, 2]
    assert st.leaf_ids(DEEPER) == [1, 2, 4]


def test_root_distance_sums_the_chain():
    assert st.root_distance(DEEPER, 1) == 0.6      # 0.2 + 0.4
    assert st.root_distance(DEEPER, 4) == 0.5


def test_leaf_path_matrix_uses_the_lca():
    m = st.leaf_path_matrix(DEEPER)
    assert m[(1, 2)] == 1.0                        # 0.4 + 0.6, LCA is node 3
    assert m[(1, 4)] == 1.1                        # 0.6 + 0.5, LCA is root
    assert set(m) == {(1, 2), (1, 4), (2, 4)}


def test_identical_trees_diff_to_all_zero():
    d = st.shadow_diff(DEEPER, DEEPER, locs=[])
    assert d["dropped"] == []
    assert d["contracted"] == []
    assert d["path_drift_max"] == 0.0
    assert d["path_drift_mean"] == 0.0
    assert d["invented"] == 0
    assert d["comparable"] is True


def test_invented_is_unmeasured_without_locs_never_zero():
    # A stub flap is created INSIDE the engine and is structurally absent from
    # every Python node list (anatomy_oracle.py:78-82), so it cannot be read
    # off served_nodes. Silently reporting 0 would be a false all-clear.
    d = st.shadow_diff(DEEPER, DEEPER)
    assert d["invented"] is None


def test_invented_counts_engine_made_leaves_in_locs():
    locs = [(1, 0.1, 0.1), (2, 0.9, 0.1), (4, 0.5, 0.9), (-1, 0.5, 0.5)]
    d = st.shadow_diff(DEEPER, DEEPER, locs=locs)
    assert d["invented"] == 1


def test_dropped_leaf_is_reported():
    served = [n for n in DEEPER if n["id"] != 4]
    d = st.shadow_diff(DEEPER, served, locs=[])
    assert d["dropped"] == [4]


def test_lengthened_limb_shows_as_path_drift_and_localises():
    served = [dict(n) for n in DEEPER]
    for n in served:
        if n["id"] == 4:
            n["length"] = 1.0                      # was 0.5, +0.5
    d = st.shadow_diff(DEEPER, served, locs=[])
    # span is the largest REQUESTED root-to-tip = 0.6; drift 0.5 / 0.6
    assert abs(d["path_drift_max"] - 0.5 / 0.6) < 1e-12
    assert (1, 4) in d["worst_pairs"] or (2, 4) in d["worst_pairs"]


def test_reattached_limb_at_equal_root_distance_is_still_caught():
    # Leaf 4 moves from the root to junction 3, its edge shortened so its
    # ROOT-TO-TIP reach is unchanged (0.5 = 0.2 + 0.3). A root-distance metric
    # sees nothing. The leaf-to-leaf matrix sees it, because 4 is now closer
    # to 1 and 2.
    served = [dict(n) for n in DEEPER]
    for n in served:
        if n["id"] == 4:
            n["parent_id"], n["length"] = 3, 0.3
    assert st.root_distance(served, 4) == st.root_distance(DEEPER, 4)
    d = st.shadow_diff(DEEPER, served, locs=[])
    assert d["path_drift_max"] > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shadow_tree.py -v --timeout=420
```

Expected: collection error, `ModuleNotFoundError: No module named 'shadow_tree'`.

- [ ] **Step 3: Write minimal implementation**

Create `mcp_harness/shadow_tree.py`:

```python
"""Did the base the compiler served realise the tree the caller requested?

THE METRIC IS THE LEAF-TO-LEAF PATH MATRIX, NEVER PARENT POINTERS.

This is the single most important fact in this module, and it is easy to get
wrong because `reparented` ("nodes whose parent differs") is the more natural
thing to reach for. It is wrong here, and the reason is measured, not stylistic
-- three SHIPPED, deliberately anatomy-preserving paths rewrite parent pointers:

  * rescue_ladder.rehome        -- "a no-op topologically ... only re-attributed
                                   across node ids (which is exactly why a
                                   rehomed rung is not in PRESERVING_STAGES --
                                   that set is keyed on (id, length))"
  * rescue_ladder.contract_slivers -- deletes a sub-threshold INTERIOR node and
                                   re-points its children; the leaf set is
                                   invariant by hard guard
  * pair_reconcile (path reconciliation, PR #72) -- "grows its edge by
                                   precisely the distance travelled, so the tip
                                   does not move at all"

An id-keyed diff reports a defect on every one of them. It would have read
PR #72's feature as a bug on every reconciled pair.

The right key is not an invention of this module. pair_reconcile.max_pair_path_gap
already names it: "it is the full leaf-to-leaf metric that circle packing
consumes ... if one scalar ever has to carry the claim, prefer
max |d(sx, sy) - d(x, y)| over leaf pairs." It is also literally the compiler's
constraint variable -- tmPath is "a path from one node to another along the
tree, but a subset of the LEAF PATHS also serves as the basis of the crease
pattern", with mMinTreeLength "as specified by the tree" (tmPath.h:36-47).

And it is what the design's central theorem means operationally: if a uniaxial
base's shadow IS its tree, the shadow realises leaf-to-leaf tree distances as
distances in the plane. The theorem does not merely justify skipping a
renderer; it names the metric.

Pure: no engine import, no I/O, no numpy. Safe to import anywhere.

ON THE DUPLICATED WALK. pair_reconcile carries its own private _chain / _lca /
_dist_to_ancestor (pair_reconcile.py:248-271). They are deliberately NOT reused
here: they are private to a module that pulls in the extraction stack, and this
module's whole value is that an oracle, a test, or the scorecard can import it
with nothing behind it. The walk is a dozen lines; the coupling would cost more
than it saves. If the two ever disagree, THIS one is the one that agrees with
the packer's constraint variable -- pair_reconcile's own docstring already
calls its root-to-tip scalar the cheap approximation and points at the
leaf-to-leaf metric as the sufficient statement.
"""
from __future__ import annotations


def _by_id(nodes) -> dict:
    return {n["id"]: n for n in (nodes or []) if isinstance(n, dict) and "id" in n}


def leaf_ids(nodes) -> list:
    """Node ids that have a parent and are nobody's parent, sorted.

    The root is deliberately excluded even when it has one child: it is not a
    flap. Same definition mesh_report._leaves and anatomy_oracle.served_anatomy
    use, kept identical so the three cannot disagree about what a flap is.
    """
    ns = [n for n in (nodes or []) if isinstance(n, dict) and "id" in n]
    return sorted(n["id"] for n in ns
                  if n.get("parent_id") is not None
                  and all(o.get("parent_id") != n["id"] for o in ns))


def _chain(by: dict, nid):
    """[(ancestor_id, distance from nid up to it), ...], nid first, root last.

    A node's `length` is the length of the edge to ITS parent, so the distance
    accumulates AFTER appending. Returns None on a cycle or a broken parent
    link -- callers degrade to "not comparable" rather than hanging, the same
    defensive posture max_pair_path_gap takes.
    """
    out, d, seen, cur = [], 0.0, set(), nid
    while cur is not None:
        if cur not in by:
            return None
        if cur in seen:
            return None
        seen.add(cur)
        out.append((cur, d))
        d += by[cur].get("length") or 0.0
        cur = by[cur].get("parent_id")
    return out
```

⚠ **Corrected during implementation:** the `_chain` above was originally
written as `while cur is not None and cur in by:`, which cannot distinguish
"walked off the end of a dangling parent link" from "reached the root" (both
exit the loop the same way), so a broken link was silently treated as its own
root instead of returning `None` as the docstring promises; the version above
is the fix, with membership checked inside the loop so the two exits are
distinguishable.

```python
def root_distance(nodes, nid):
    """Root-to-tip path length, or None when the chain is broken."""
    ch = _chain(_by_id(nodes), nid)
    return None if ch is None else ch[-1][1] + 0.0 if False else (
        None if ch is None else _root_dist_from_chain(ch))


def _root_dist_from_chain(chain) -> float:
    """Total distance from the chain's start node up to the root.

    The last entry's stored distance is the walk to the root node itself, which
    is exactly the root-to-tip length: the root contributes no edge.
    """
    return chain[-1][1]


def _pair_distance(by: dict, a, b):
    """Undirected tree distance between two nodes, or None if not comparable.

    d(a,b) = dist(a, lca) + dist(b, lca). Found by walking b's chain until it
    meets a node already on a's chain -- that meeting point IS the LCA.
    """
    ca, cb = _chain(by, a), _chain(by, b)
    if ca is None or cb is None:
        return None
    da = {nid: d for nid, d in ca}
    for nid, d in cb:
        if nid in da:
            return da[nid] + d
    return None                      # disjoint components


def leaf_path_matrix(nodes) -> dict:
    """{(a, b): tree distance} over every leaf pair, a < b. Skips broken pairs."""
    by = _by_id(nodes)
    leaves = leaf_ids(nodes)
    out = {}
    for i, a in enumerate(leaves):
        for b in leaves[i + 1:]:
            d = _pair_distance(by, a, b)
            if d is not None:
                out[(a, b)] = d
    return out


def _span(nodes) -> float:
    """Largest root-to-tip length in the REQUESTED tree.

    Deliberately the requested span, never the served one: a rescue that
    shortens the model would otherwise shrink the denominator and make drift
    look smaller than it is. Matches max_pair_path_gap's normaliser so the two
    columns are read on one scale.
    """
    by = _by_id(nodes)
    best = 0.0
    for n in (nodes or []):
        ch = _chain(by, n.get("id"))
        if ch is not None:
            best = max(best, _root_dist_from_chain(ch))
    return best


def shadow_diff(requested_nodes, served_nodes, locs=None) -> dict:
    """How the served tree differs from the requested one.

    `locs` is leaf_node_locations() output -- [(json_id, x, y), ...]. It is
    REQUIRED to measure invented flaps and there is no substitute: a stub flap
    "is created inside the engine and is structurally absent from any Python
    node list" (anatomy_oracle.py:78-82), surfacing only here under the
    json_id = -1 convention (server.py:415). Passing None yields
    invented=None -- never 0, which would read as "measured, and clean".
    """
    req_leaves = leaf_ids(requested_nodes)
    srv_leaves = set(leaf_ids(served_nodes))
    req_ids = {n["id"] for n in (requested_nodes or []) if "id" in n}
    srv_ids = {n["id"] for n in (served_nodes or []) if "id" in n}

    dropped = sorted(set(req_leaves) - srv_leaves)
    # Interior ids that vanished: bookkeeping (a sliver contraction), reported
    # apart from `dropped` so a merge never reads as a lost flap.
    contracted = sorted((req_ids - srv_ids) - set(req_leaves))

    invented = None
    if locs is not None:
        invented = sum(1 for row in locs if int(row[0]) == -1)

    span = _span(requested_nodes) or 1.0
    req_m = leaf_path_matrix(requested_nodes)
    srv_m = leaf_path_matrix(served_nodes)
    shared = [k for k in req_m if k in srv_m]

    drifts = {k: abs(srv_m[k] - req_m[k]) / span for k in shared}
    worst = max(drifts.values()) if drifts else 0.0
    mean = (sum(drifts.values()) / len(drifts)) if drifts else 0.0
    worst_pairs = sorted(k for k, v in drifts.items() if v >= worst > 0.0)

    return {
        "invented": invented,
        "dropped": dropped,
        "contracted": contracted,
        "path_drift_max": worst,
        "path_drift_mean": mean,
        "worst_pairs": worst_pairs,
        "span": span,
        "comparable": bool(shared) or not req_leaves,
    }
```

⚠ **Implementer note:** `root_distance` above is written awkwardly on purpose
to be replaced — write it plainly:

```python
def root_distance(nodes, nid):
    """Root-to-tip path length, or None when the chain is broken."""
    ch = _chain(_by_id(nodes), nid)
    return None if ch is None else _root_dist_from_chain(ch)
```

Use this version. Delete the placeholder-shaped one.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shadow_tree.py -v --timeout=420
```

Expected: 9 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/shadow_tree.py mcp_harness/tests/test_shadow_tree.py
git commit -m "feat(shadow-tree): leaf-to-leaf path metric for served-vs-requested"
```

---

## Task 2: The invariance pins

The three tests that hold §3.3.1's line. Without them the id key comes back.

Each one is **two-sided or two-fact** on purpose. `rehome` asserts the new
metric reads zero AND the old id-keyed one reads non-empty; `contraction`
asserts no flap was lost AND the drift stays inside its own bound;
`reconciled` asserts the tip did not move AND the matrix did. A one-sided
assertion would pass against a metric that returns zero for everything.

**Files:**
- Modify: `mcp_harness/tests/test_shadow_tree.py` (append)

**Interfaces:**
- Consumes: `shadow_tree.shadow_diff`, `shadow_tree.leaf_ids` (Task 1);
  `rescue_ladder.rehome`, `rescue_ladder.contract_slivers`,
  `rescue_ladder.SLIVER_RATIO`; `pair_reconcile`.
- Produces: nothing consumed downstream.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_shadow_tree.py`:

```python
import rescue_ladder
import shadow_tree as st


def _parent_pointer_diff(requested, served):
    """The WRONG metric, kept only so the pins can assert it is wrong.

    Never use this in production. It exists to make the invariance tests
    two-sided: asserting only "new metric == 0" would also pass against a
    metric that returns 0 for everything.
    """
    rp = {n["id"]: n.get("parent_id") for n in requested}
    sp = {n["id"]: n.get("parent_id") for n in served}
    return sorted(i for i in rp if i in sp and rp[i] != sp[i])


# A chain deep enough that re-rooting reverses more than one edge, and with a
# second leaf so the old root does not become a leaf (rehome's own guard).
REHOMABLE = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 1, "parent_id": 0, "length": 0.3},
    {"id": 2, "parent_id": 1, "length": 0.4},
    {"id": 3, "parent_id": 2, "length": 0.5},
    {"id": 4, "parent_id": 0, "length": 0.6},
]


def test_rehome_is_invisible_to_the_metric_and_visible_to_the_id_key():
    """THE PIN. rehome is a topological no-op that rewrites parent pointers.

    Two-sided on purpose: the path metric must read exactly 0.0 AND the
    parent-pointer diff must read non-empty. If someone re-keys shadow_diff on
    rooting, the first assertion fails; if someone makes it vacuous, the second
    documents what it was protecting.
    """
    served = rescue_ladder.rehome(REHOMABLE, 2)
    assert served is not None, "fixture must be rehomable"

    assert _parent_pointer_diff(REHOMABLE, served), \
        "fixture is not exercising the hazard -- parents must move"

    d = st.shadow_diff(REHOMABLE, served, locs=[])
    assert d["path_drift_max"] == 0.0
    assert d["dropped"] == []
    assert d["contracted"] == []
    assert sorted(st.leaf_ids(served)) == sorted(st.leaf_ids(REHOMABLE))


# One interior node under the sliver threshold (0.08 * longest = 0.08 * 0.6).
CONTRACTABLE = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 1, "parent_id": 0, "length": 0.6},
    {"id": 2, "parent_id": 0, "length": 0.01},     # sliver interior
    {"id": 3, "parent_id": 2, "length": 0.5},
    {"id": 4, "parent_id": 2, "length": 0.4},
]


def test_contraction_drops_no_flap_and_drifts_within_its_own_bound():
    served = rescue_ladder.contract_slivers(CONTRACTABLE, [])
    assert served is not None, "fixture must contain a contractable sliver"

    d = st.shadow_diff(CONTRACTABLE, served, locs=[])
    assert d["dropped"] == [], "contraction never deletes a flap"
    assert d["contracted"] == [2]
    # The sliver's own length is DISCARDED, not folded into its children, so
    # some leaf-to-leaf paths genuinely shorten. Bounded PER CONTRACTION --
    # several victims can lie on one path, so the bound scales with the count.
    bound = len(d["contracted"]) * rescue_ladder.SLIVER_RATIO
    assert d["path_drift_max"] <= bound + 1e-12


# A declared pair whose members hang off junctions at DIFFERENT depths -- the
# exact case path reconciliation exists for.
RECONCILABLE = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 1, "parent_id": 0, "length": 0.2},      # junction A
    {"id": 2, "parent_id": 1, "length": 0.2},      # junction B, deeper
    {"id": 3, "parent_id": 1, "length": 0.5},      # pair member, off A
    {"id": 4, "parent_id": 2, "length": 0.5},      # pair member, off B
    {"id": 5, "parent_id": 0, "length": 0.7},      # a third leaf to measure against
]


def test_reconciled_pair_keeps_its_reach_while_the_matrix_moves():
    """Path reconciliation is NOT a false positive -- it is a real change, and
    the metric should say so.

    It buys pair congruence with re-attachment: the moved flap's ROOT-TO-TIP
    reach is unchanged by construction ("grows its edge by precisely the
    distance travelled, so the tip does not move at all"), but moving it to
    the pair's LCA genuinely changes its distance to third leaves. Both facts
    are asserted so neither is ever mistaken for the other.
    """
    import pair_reconcile
    out = pair_reconcile.reparent_pairs_to_shared_hub(RECONCILABLE, [[3, 4]])
    served = out[0] if isinstance(out, tuple) else out
    assert served is not None, "fixture must be reconcilable"

    for nid in (3, 4):
        assert abs((st.root_distance(served, nid) or 0.0)
                   - (st.root_distance(RECONCILABLE, nid) or 0.0)) < 1e-9, \
            "reconciliation must not move a tip"

    d = st.shadow_diff(RECONCILABLE, served, locs=[])
    assert d["dropped"] == [], "the leaf set is invariant, by contract"
    assert d["path_drift_max"] > 0.0, \
        "re-attachment does move leaf-to-leaf distances -- report it"
```

⚠ **Verified API:** the function is
`pair_reconcile.reparent_pairs_to_shared_hub(nodes, pairs)`
(`pair_reconcile.py:282`). Confirm its return shape before unpacking — the test
above tolerates either a bare list or a `(nodes, evidence)` tuple. If the
fixture is refused (returns `None`), widen it until the function accepts it; a
skipped test here would leave the spec's `test_shadow_diff_reconciled_pair` row
unimplemented, which is the row that proves the metric reports a real change
rather than suppressing everything.

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shadow_tree.py -k "rehome or contraction or reconciled" -v --timeout=420
```

Expected: FAIL. Both are genuine behaviour checks against Task 1's module —
if they pass immediately, verify the fixtures actually trigger the
transformations (the `assert ... is not None` guards catch a fixture that
`rehome`/`contract_slivers` refuses).

- [ ] **Step 3: Fix `shadow_tree.py` if the pins fail**

If `test_rehome_...` fails with non-zero drift, the bug is in `_chain`'s
accumulation order — the distance must be appended **before** adding the
node's own edge length. No other change should be needed; Task 1's
implementation is written to satisfy these.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_shadow_tree.py -v --timeout=420
```

Expected: 12 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tests/test_shadow_tree.py
git commit -m "test(shadow-tree): pin the metric against rehome and contraction"
```

---

## Task 3: Plumb the served tree on the PARENT path + `read_base()`

This is the highest-leverage change in the plan. **Read the warning first.**

⚠ There are two ladder paths. `draft_and_compile_full_base` — the actual serve
— goes through `_compile_with_perturb` (`server.py:1350`), whose return type is
a **bare fold string**. No payload field can reach it. The tree is recorded in
a module-level slot in the MCP server process instead; `read_base()` is an MCP
tool in that same process and reads it. **No fold bytes change.**

**Files:**
- Modify: `mcp_harness/server.py` — `_compile_with_perturb` (`:1350-1445`), new
  `read_base` tool near the other read-only tools.
- Test: `mcp_harness/tests/test_read_base.py` (create)

**Interfaces:**
- Consumes: `shadow_tree.shadow_diff` (Task 1).
- Produces:
  - `server._LAST_SERVE: dict` — `{"serve_id": int, "requested": list,
    "served": list, "stage": str, "stubs": int, "invents_anatomy": bool,
    "locs": list, "scale": float | None}`, or empty dict before any serve.
  - `server._record_serve(requested, served, rung, locs=None, scale=None) -> None`
  - MCP tool `read_base() -> str` (JSON string).

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_read_base.py`:

```python
"""read_base(): what did the compiler actually build?

THE POINT OF THIS FILE is that the assertions go through the REAL production
call site. A prior gate in this repo stayed green while the production call was
gutted, because it counted invocations instead of watching the real one. So:
draft_and_compile_full_base is called, and read_base is then asked what it saw.
"""
import json

import pytest

import server


@pytest.fixture(autouse=True)
def _clear_serve_record():
    server._LAST_SERVE.clear()
    yield
    server._LAST_SERVE.clear()


# A template that packs at attempt 0 -- no rescue, so served IS requested.
STAR4 = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 1, "parent_id": 0, "length": 0.25},
    {"id": 2, "parent_id": 0, "length": 0.25},
    {"id": 3, "parent_id": 0, "length": 0.25},
    {"id": 4, "parent_id": 0, "length": 0.25},
]


def test_read_base_before_any_serve_reports_no_base():
    out = json.loads(server.read_base())
    assert out["status"] == "no-base"


def test_serve_records_the_tree_through_the_real_tool():
    fold = server.draft_and_compile_full_base(STAR4, symmetric_pairs=[])
    assert not fold.startswith("ERROR:"), fold

    out = json.loads(server.read_base())
    assert out["status"] == "ok"
    assert out["stage"] == "none"                 # attempt-0 packed
    assert out["shadow_diff"]["dropped"] == []
    assert out["shadow_diff"]["path_drift_max"] == 0.0
    # The served tree is recorded, not merely the requested one.
    assert sorted(n["id"] for n in out["served_tree"]) == [0, 1, 2, 3, 4]


def test_read_base_spawns_no_worker(monkeypatch):
    """read_base must never trigger a compile. suggest_pose_stack documents
    that cost at server.py:2053; this tool is explicitly read-only."""
    server.draft_and_compile_full_base(STAR4, symmetric_pairs=[])

    calls = []
    monkeypatch.setattr(server, "_run_isolated",
                        lambda *a, **k: calls.append(a) or "{}")
    server.read_base()
    assert calls == []


def test_read_base_does_not_mutate_the_record():
    server.draft_and_compile_full_base(STAR4, symmetric_pairs=[])
    before = json.dumps(server._LAST_SERVE, sort_keys=True, default=str)
    server.read_base()
    server.read_base()
    after = json.dumps(server._LAST_SERVE, sort_keys=True, default=str)
    assert before == after
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py -v --timeout=420
```

Expected: FAIL, `AttributeError: module 'server' has no attribute '_LAST_SERVE'`.

- [ ] **Step 3: Write minimal implementation**

In `mcp_harness/server.py`, immediately **above** `def _compile_with_perturb`
(currently line 1350), add:

```python
#: The last base this process served, for read_base(). NOT the fold -- the
#: TREES, so "what did the compiler actually build" is answerable after a
#: rescue has substituted a candidate.
#:
#: WHY A MODULE SLOT AND NOT A PAYLOAD FIELD. There are two ladder paths.
#: _worker_compile_and_regions returns a JSON queue payload, so one more field
#: works there (and Task 4 adds it). This path -- the one draft_and_compile_
#: full_base and compile_base actually serve through -- returns a BARE FOLD
#: STRING. Its `served` tuple even unpacks as `rung, asym, result, _payload`;
#: the underscore is this file already saying the tree is thrown away.
#:
#: WHY NOT ANNOTATE THE FOLD. frame_title is "the only annotation channel
#: Oriedita's strict parser accepts" (_append_frame_note) and is a display
#: string the web bridge parses for markers. Putting a tree in it would be
#: both a parse hazard and a fold-bytes change, and this whole slice is
#: required to leave attempt-0 output byte-identical.
_LAST_SERVE: dict = {}
_SERVE_SEQ = {"n": 0}


def _record_serve(requested, served, rung, locs=None, scale=None) -> None:
    """Record (requested, served) for read_base(). Never raises.

    Defensive by construction: this runs on the serve path, and a bookkeeping
    error here must never turn a successful compile into a failure. Same
    posture _append_frame_note takes about annotation.
    """
    try:
        _SERVE_SEQ["n"] += 1
        _LAST_SERVE.clear()
        _LAST_SERVE.update({
            "serve_id": _SERVE_SEQ["n"],
            "requested": [dict(n) for n in (requested or [])],
            "served": [dict(n) for n in (served or [])],
            "stage": getattr(rung, "stage", rescue_ladder.STAGE_EXACT),
            "stubs": int(getattr(rung, "stubs", 0) or 0),
            "invents_anatomy": getattr(rung, "stage", None)
                in rescue_ladder.INVENTS_ANATOMY,
            "locs": list(locs) if locs is not None else None,
            "scale": scale,
        })
    except Exception:                                   # noqa: BLE001
        pass
```

In `_compile_with_perturb`, the attempt-0 success branch currently reads:

```python
    result = attempt(nodes, 0)
    if not result.startswith("ERROR:"):
```

Immediately before its `return result`, and **after** the existing
`capture.record(...)` call, add:

```python
        _record_serve(nodes, nodes, None)
```

Then widen the ladder's `_run_rung` so the winning candidate survives. Change:

```python
    def _run_rung(candidate, rung):
        stages_tried[rung.stage] = stages_tried.get(rung.stage, 0) + 1
        r = attempt(candidate, rung.stubs)
        if r.startswith("ERROR:"):
            rung_codes.append(error_recipes.classify(r))
            return None, None
        return r, None
```

to:

```python
    def _run_rung(candidate, rung):
        stages_tried[rung.stage] = stages_tried.get(rung.stage, 0) + 1
        r = attempt(candidate, rung.stubs)
        if r.startswith("ERROR:"):
            rung_codes.append(error_recipes.classify(r))
            return None, None
        # The candidate rides the payload slot _search_first_clean already
        # carries, so the winning TREE reaches the caller. Before this it died
        # in the closure and `served` unpacked it into `_payload`.
        return r, candidate
```

and in the `if served is not None:` branch change:

```python
        rung, asym, result, _payload = served
```

to:

```python
        rung, asym, result, served_candidate = served
```

then, immediately before that branch's `return out`, add:

```python
        _record_serve(nodes, served_candidate, rung)
```

Finally, add the tool. Place it beside the other read-only tools (after
`suggest_pose_stack`'s definition):

```python
@mcp.tool()
def read_base() -> str:
    """Report what the compiler ACTUALLY built for the last served base.

    Read-only. Spawns no worker, triggers no recompile, mutates nothing. It
    reads values already recorded at serve time -- suggest_pose_stack documents
    what a fresh compile costs, and this tool deliberately does not pay it.

    Returns a JSON object:
      status        "ok" | "no-base"
      serve_id      monotonic counter for this process
      stage         the rescue stage that served ("none" == the exact tree packed)
      stubs         structural flaps the engine was permitted to invent
      invents_anatomy  True iff the stage can add anatomy nobody requested
      scale         packing scale, when known
      shadow_diff   see shadow_tree.shadow_diff -- invented / dropped /
                    contracted / path_drift_max / path_drift_mean / worst_pairs
      served_tree   the node list actually compiled (differs from the request
                    after a rescue)
    """
    import shadow_tree
    if not _LAST_SERVE:
        return json.dumps({"status": "no-base"})
    rec = _LAST_SERVE
    diff = shadow_tree.shadow_diff(rec.get("requested"), rec.get("served"),
                                   locs=rec.get("locs"))
    # ⚠ THE PARENT PATH HAS NO `locs`. _worker_full_base returns a fold string
    # and nothing else, so shadow_diff correctly reports invented=None there --
    # "not measured", never a false 0. But the count IS known by another route:
    # the rung's stub budget is exactly how many flaps the engine was permitted
    # to invent, and STAGE_STUB is the only stage in INVENTS_ANATOMY. Fill it
    # in rather than shipping a permanent None on the serve path.
    if diff.get("invented") is None and rec.get("stubs") is not None:
        diff["invented"] = int(rec["stubs"])
        diff["invented_source"] = "rung.stubs"
    return json.dumps({
        "status": "ok",
        "serve_id": rec.get("serve_id"),
        "stage": rec.get("stage"),
        "stubs": rec.get("stubs"),
        "invents_anatomy": rec.get("invents_anatomy"),
        "scale": rec.get("scale"),
        "shadow_diff": diff,
        "served_tree": rec.get("served"),
    })
```

⚠ `_record_serve(nodes, nodes, None)` on the attempt-0 path passes `rung=None`;
`getattr(None, "stage", rescue_ladder.STAGE_EXACT)` yields `STAGE_EXACT`, whose
value is the string `"none"` the test asserts. Confirm with
`python -c "import rescue_ladder; print(rescue_ladder.STAGE_EXACT)"` before
relying on it, and adjust the test's expected `stage` to the real constant if
it differs.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py -v --timeout=420
```

Expected: 5 passed (4 plus the 4 parametrised byte-identity cases once Step 5
lands — re-run after adding them).

Then confirm nothing moved in the ladder's own suite:

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_perturb_ladder.py -v --timeout=420
```

Expected: same pass count as before this task.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_read_base.py
git commit -m "feat(read-base): keep the served tree on the parent ladder path"
```

---

## Task 4: Plumb the served tree on the CHILD path

**Files:**
- Modify: `mcp_harness/server.py` — `_worker_compile_and_regions` (`:372`,
  `:380-386`, `:392-407`)
- Test: `mcp_harness/tests/test_read_base.py` (append)

**Interfaces:**
- Consumes: nothing new.
- Produces: queue payload gains `"served_tree": list` on all three `queue.put`
  sites (attempt-0, checkpoint, final).

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_read_base.py`:

```python
def test_child_payload_carries_the_served_tree():
    """The OTHER ladder path -- the one suggest_pose_stack and
    apply_shaping_ops consume. Distinct from the parent path in Task 3, and
    the spec's first draft named only this one.
    """
    raw = server._run_ladder_child(STAR4, [], 1.0, 1.0)
    assert not raw.startswith("ERROR:"), raw
    payload = json.loads(raw)
    assert "served_tree" in payload
    assert sorted(n["id"] for n in payload["served_tree"]) == [0, 1, 2, 3, 4]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py::test_child_payload_carries_the_served_tree -v --timeout=420
```

Expected: FAIL, `KeyError`/`assert 'served_tree' in payload`.

- [ ] **Step 3: Write minimal implementation**

In `_worker_compile_and_regions`:

Change the attempt-0 `queue.put` from:

```python
            queue.put(("ok", json.dumps({"fold": fold, "regions": regions,
                                         "scale": scale, "locs": locs})))
```

to:

```python
            queue.put(("ok", json.dumps({"fold": fold, "regions": regions,
                                         "scale": scale, "locs": locs,
                                         "served_tree": nodes})))
```

Change `_run_rung` from:

```python
                fold, regions, scale, locs = _try_once(candidate, rung.stubs)
                return fold, (regions, scale, locs)
```

to:

```python
                fold, regions, scale, locs = _try_once(candidate, rung.stubs)
                return fold, (regions, scale, locs, candidate)
```

Change `_checkpoint` from:

```python
        def _checkpoint(served_t, audit, packs_seen):
            ck_rung, _ck_asym, ck_fold, (ck_regions, ck_scale, ck_locs) = served_t
```

to:

```python
        def _checkpoint(served_t, audit, packs_seen):
            (ck_rung, _ck_asym, ck_fold,
             (ck_regions, ck_scale, ck_locs, ck_tree)) = served_t
```

and its `queue.put` payload from:

```python
                {"fold": ck_fold, "regions": ck_regions,
                 "scale": ck_scale, "locs": ck_locs})))
```

to:

```python
                {"fold": ck_fold, "regions": ck_regions,
                 "scale": ck_scale, "locs": ck_locs,
                 "served_tree": ck_tree})))
```

Change the final unpack from:

```python
            rung, _asym, fold, (regions, scale, locs) = served
```

to:

```python
            rung, _asym, fold, (regions, scale, locs, served_tree) = served
```

and its `queue.put` from:

```python
            queue.put(("ok", json.dumps({"fold": fold, "regions": regions,
                                         "scale": scale, "locs": locs})))
```

to:

```python
            queue.put(("ok", json.dumps({"fold": fold, "regions": regions,
                                         "scale": scale, "locs": locs,
                                         "served_tree": served_tree})))
```

⚠ All four unpack sites must change together — the tuple shape is shared. A
missed site raises `ValueError: not enough values to unpack` on the first
rescue, which is loud, but only on the rescue path. Grep to confirm:

```bash
grep -n "regions, scale, locs" mcp_harness/server.py
```

Every hit inside `_worker_compile_and_regions` must carry the fourth element.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py -v --timeout=420
```

Expected: 5 passed.

- [ ] **Step 5: Add the byte-identity guard as its own test**

This is the guard the whole slice rests on, and it must be an assertion, not a
manual eyeball. Append to `mcp_harness/tests/test_read_base.py`:

```python
TEMPLATES = {
    "star4": STAR4,
    "tee": [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.30},
        {"id": 2, "parent_id": 0, "length": 0.30},
        {"id": 3, "parent_id": 0, "length": 0.35},
    ],
    "chain": [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.25},
        {"id": 2, "parent_id": 1, "length": 0.25},
        {"id": 3, "parent_id": 0, "length": 0.40},
    ],
    "wide": [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.2},
        {"id": 2, "parent_id": 0, "length": 0.2},
        {"id": 3, "parent_id": 0, "length": 0.2},
        {"id": 4, "parent_id": 0, "length": 0.2},
        {"id": 5, "parent_id": 0, "length": 0.2},
    ],
}


@pytest.mark.parametrize("name", sorted(TEMPLATES))
def test_attempt0_output_is_byte_identical_after_this_slice(name):
    """THE GUARD. This whole slice is required to change no served bytes.

    Recorded here as a value rather than a description: run this test on the
    commit BEFORE the slice, paste each fold into tests/goldens/, and the test
    then fails loudly if any later task moves a byte. `frame_title` carries
    every rescue marker, so a stray annotation shows up immediately.
    """
    import hashlib
    import os
    fold = server.draft_and_compile_full_base(TEMPLATES[name],
                                              symmetric_pairs=[])
    assert not fold.startswith("ERROR:"), fold
    digest = hashlib.sha256(fold.encode()).hexdigest()
    path = os.path.join(os.path.dirname(__file__), "goldens",
                        f"attempt0_{name}.sha256")
    if not os.path.exists(path):                 # first run records it
        with open(path, "w") as fh:
            fh.write(digest)
    with open(path) as fh:
        assert fh.read().strip() == digest, (
            f"attempt-0 output for {name} moved -- this slice must change no "
            "served bytes. Fix the cause; do NOT re-bless.")
```

⚠ **This is the one place a hash is correct**, and it is not a hash over a
render — it is over a deterministic compiled fold on one platform, which is
exactly what "changed nothing" means. Record the goldens on the commit
**before** Task 3 lands (`git stash` the slice, run once, `git stash pop`), so
the baseline is genuinely pre-slice.

- [ ] **Step 6: Verify no fold bytes moved**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/ -k "golden or attempt0 or verdict" -v --timeout=420
```

Expected: same results as before Task 3. Any change here means a fold byte
moved and must be fixed, not blessed.

- [ ] **Step 7: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_read_base.py
git commit -m "feat(read-base): carry the served tree on the child ladder payload"
```

---

## Task 5: The `[FIDELITY]` oracle

**Files:**
- Create: `mcp_harness/fidelity_oracle.py`
- Test: `mcp_harness/tests/test_fidelity_oracle.py`

**Interfaces:**
- Consumes: `shadow_tree.shadow_diff` output shape (Task 1);
  `rescue_ladder.SLIVER_RATIO`, `rescue_ladder.STAGE_STUB`,
  `rescue_ladder.STAGE_NORMALIZE`.
- Produces:
  - `decide(*, base_report, reparent_reported=False) -> dict` with keys
    `fire: bool`, `reason: str`, `drift: float`, `invented: int | None`,
    `dropped: list`.
  - `message(verdict: dict, *, repair: bool = False) -> str`

`base_report` is `read_base()`'s parsed dict.

- [ ] **Step 1: Write the failing test**

Create `mcp_harness/tests/test_fidelity_oracle.py`:

```python
"""The [FIDELITY] oracle: did the compiler build what was asked for?

IT IS AN UNEXPLAINED-DRIFT DETECTOR, and the suppressions are the important
half -- exactly as in test_anatomy_oracle.py. Every deliberate transformation
in this pipeline already announces itself (NORMALIZE_MARKER, STUB_MARKER, the
reparent report lines), so drift the agent has ALREADY been told about must not
fire. Drift nothing explains is the only thing this oracle is for.

Note what is NOT here: no fake-provider suppression. [ANATOMY] needs one
because the fake provider corrupts the REFERENCE it grades against. This oracle
grades requested-against-served -- both ours, on any provider -- so it is
measurable offline, which is why this file needs no mesh stack and no network.
"""
import fidelity_oracle as fo
import rescue_ladder


def _report(stage="none", drift=0.0, invented=0, dropped=(), contracted=(),
            stubs=0, status="ok"):
    return {
        "status": status,
        "stage": stage,
        "stubs": stubs,
        "shadow_diff": {
            "invented": invented,
            "dropped": list(dropped),
            "contracted": list(contracted),
            "path_drift_max": drift,
            "path_drift_mean": drift,
            "worst_pairs": [],
            "span": 1.0,
            "comparable": True,
        },
    }


def test_no_base_stands_down_with_a_reason():
    v = fo.decide(base_report={"status": "no-base"})
    assert v["fire"] is False
    assert v["reason"] == "unknown-tree"


def test_clean_serve_stands_down():
    v = fo.decide(base_report=_report())
    assert v["fire"] is False
    assert v["reason"] == "no-drift"


def test_unexplained_drift_fires():
    v = fo.decide(base_report=_report(stage="order", drift=0.31))
    assert v["fire"] is True
    assert "0.31" in v["reason"] or "drift" in v["reason"]


def test_stub_stage_does_not_fire_on_invented_flaps():
    """The stub stage runs only after every anatomy-preserving rung failed,
    and the fold already carries STUB_MARKER with the count. Firing here
    instructs a chase the ladder has already exhausted."""
    v = fo.decide(base_report=_report(stage=rescue_ladder.STAGE_STUB,
                                      invented=3, stubs=3))
    assert v["fire"] is False
    assert v["reason"] == "stage-stub"


def test_sliver_contraction_within_its_bound_does_not_fire():
    v = fo.decide(base_report=_report(stage=rescue_ladder.STAGE_NORMALIZE,
                                      drift=rescue_ladder.SLIVER_RATIO / 2,
                                      contracted=[7]))
    assert v["fire"] is False
    assert v["reason"] == "sliver-contraction"


def test_contraction_beyond_its_bound_still_fires():
    v = fo.decide(base_report=_report(stage=rescue_ladder.STAGE_NORMALIZE,
                                      drift=rescue_ladder.SLIVER_RATIO * 5,
                                      contracted=[7]))
    assert v["fire"] is True


def test_reported_reparenting_does_not_fire():
    v = fo.decide(base_report=_report(stage="none", drift=0.2),
                  reparent_reported=True)
    assert v["fire"] is False
    assert v["reason"] == "reconciled-pairs"


def test_dropped_flap_always_fires():
    v = fo.decide(base_report=_report(stage="order", dropped=[4]))
    assert v["fire"] is True


def test_message_never_composes_an_imperative_without_budget():
    v = fo.decide(base_report=_report(stage="order", drift=0.31))
    text = fo.message(v, repair=False)
    assert text.startswith("[FIDELITY]")
    lowered = text.lower()
    assert "repair now" not in lowered
    assert "recompile" not in lowered


def test_every_stand_down_names_itself():
    for report, kwargs in [
        ({"status": "no-base"}, {}),
        (_report(), {}),
        (_report(stage=rescue_ladder.STAGE_STUB, invented=1, stubs=1), {}),
        (_report(stage=rescue_ladder.STAGE_NORMALIZE,
                 drift=rescue_ladder.SLIVER_RATIO / 2, contracted=[7]), {}),
        (_report(stage="none", drift=0.2), {"reparent_reported": True}),
    ]:
        v = fo.decide(base_report=report, **kwargs)
        assert v["fire"] is False
        assert v["reason"], "a stand-down must always name its suppression"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_fidelity_oracle.py -v --timeout=420
```

Expected: collection error, `ModuleNotFoundError: No module named 'fidelity_oracle'`.

- [ ] **Step 3: Write minimal implementation**

Create `mcp_harness/fidelity_oracle.py`:

```python
"""The [FIDELITY] oracle: did the compiler build the tree that was requested?

IT IS AN UNEXPLAINED-DRIFT DETECTOR, NOT A DRIFT DETECTOR.

Every deliberate transformation in this pipeline already announces itself --
PLACEMENT_MARKER, NORMALIZE_MARKER and STUB_MARKER on the served fold, and
_pair_reparent_lines in the reference report. Drift those explain, the agent
has already been told about, with evidence, by a channel that predates this
module. Drift nothing explains is the defect class nothing catches today, and
it is the only thing this oracle is for.

WHY THE SUPPRESSIONS MATTER MORE THAN THE FIRING, quoting anatomy_oracle:
"An oracle that fires on a subject the pipeline provably cannot serve does not
inform the agent -- it trains it to chase impossible repairs, spending its one
capped turn and its compile budget on a target that does not exist."

WHAT IS DELIBERATELY ABSENT. [ANATOMY] suppresses on the fake provider, and on
three reference-derived conditions (no-mesh-report, no-reference-count,
R-unservable). This oracle needs NONE of them, because it never consults R. It
compares requested against served -- both ours, on any provider -- so it is
measurable offline on the committed fixtures, which [ANATOMY] is not. Copying
that suppression list over would silence it everywhere for no reason.

IT SHIPS WITH ZERO REPAIR BUDGET. message(repair=False) is the only shape the
current wiring composes. The imperative branch exists so the no-budget text is
composed FOR that outcome rather than by withholding a sentence, which is the
CP AUDIT review fix anatomy_oracle also carries.

Pure decision logic + message text: no I/O, no websocket, no engine.
"""
from __future__ import annotations

#: Below this, drift is not worth a synthetic turn. It is a fraction of the
#: model's own span, so it is scale-free. Deliberately generous: this oracle's
#: likelier failure is firing too often, not too rarely (spec R1b).
DRIFT_EPS = 0.01


def _sliver_ratio() -> float:
    """rescue_ladder's own threshold, read lazily so this module imports
    without the ladder. Same lazy-import discipline anatomy_oracle uses for
    mesh_to_tree.MAX_LEAVES."""
    try:
        import rescue_ladder
        return rescue_ladder.SLIVER_RATIO
    except Exception:                                   # noqa: BLE001
        return 0.08


def _stage_stub() -> str:
    try:
        import rescue_ladder
        return rescue_ladder.STAGE_STUB
    except Exception:                                   # noqa: BLE001
        return "stub"


def _stage_normalize() -> str:
    try:
        import rescue_ladder
        return rescue_ladder.STAGE_NORMALIZE
    except Exception:                                   # noqa: BLE001
        return "normalize"


def decide(*, base_report, reparent_reported: bool = False) -> dict:
    """Should the oracle fire, and if not, why not?

    `base_report` is read_base()'s parsed dict. `reparent_reported` is True
    when the reference report already itemised a path-reconciliation re-parent
    for this base -- the caller knows that, this module cannot.

    `reason` is ALWAYS set: on a firing it names the drift, on a stand-down it
    names the suppression. Callers log it either way.
    """
    out = {"fire": False, "reason": "", "drift": 0.0,
           "invented": None, "dropped": []}

    # (1) UNKNOWN TREE. The incremental compile_base path takes no tree at all,
    # and a base can be served before any record exists. "I do not know what
    # was served" is not "nothing was served" -- only a suppression can express
    # the difference. [ANATOMY]'s (1b), rated BLOCKER on adversarial review.
    if not base_report or base_report.get("status") != "ok":
        out["reason"] = "unknown-tree"
        return out

    diff = base_report.get("shadow_diff") or {}
    drift = float(diff.get("path_drift_max") or 0.0)
    dropped = list(diff.get("dropped") or [])
    invented = diff.get("invented")
    contracted = list(diff.get("contracted") or [])
    stage = base_report.get("stage")
    out.update({"drift": drift, "invented": invented, "dropped": dropped})

    if not diff.get("comparable", True):
        out["reason"] = "not-comparable"
        return out

    # A DROPPED FLAP IS NEVER SUPPRESSED. Every ladder stage guards the leaf
    # set explicitly (contract_slivers bans leaves as victims, rehome carries
    # the mirror guard, path reconciliation contracts to "the leaf set is
    # invariant"). So a dropped leaf means a guard did not hold, which no
    # marker explains and no stage is entitled to.
    if dropped:
        out["fire"] = True
        out["reason"] = f"dropped flap(s) {dropped}"
        return out

    # (2) STAGE-STUB, on the invented clause only. The stub stage runs only
    # after every anatomy-preserving rung has failed, and STUB_MARKER already
    # carries the count on the served fold.
    if stage == _stage_stub():
        if drift <= DRIFT_EPS:
            out["reason"] = "stage-stub"
            return out

    # (3) SLIVER CONTRACTION. A contraction discards the sliver's own length
    # rather than folding it into its children, so some leaf-to-leaf paths
    # genuinely shorten -- bounded PER CONTRACTION, and NORMALIZE_MARKER
    # already states that the graph was restructured.
    if stage == _stage_normalize() and contracted:
        if drift <= len(contracted) * _sliver_ratio() + 1e-12:
            out["reason"] = "sliver-contraction"
            return out

    # (4) RECONCILED PAIRS. Path reconciliation genuinely moves leaf-to-leaf
    # distances -- it buys pair congruence with re-attachment -- but
    # _pair_reparent_lines has already itemised it with evidence.
    if reparent_reported:
        out["reason"] = "reconciled-pairs"
        return out

    # (5) NO DRIFT.
    if drift <= DRIFT_EPS and not (invented or 0):
        out["reason"] = "no-drift"
        return out

    out["fire"] = True
    out["reason"] = f"unexplained path drift {drift:.4f} of span"
    return out


def message(verdict: dict, *, repair: bool = False) -> str:
    """The synthetic '[FIDELITY]' user message.

    Composed FOR the budget outcome, exactly as anatomy_oracle.message is: an
    imperative left standing in the LLM context would be obeyed on the next
    user turn, un-capped.
    """
    drift = verdict.get("drift", 0.0)
    dropped = verdict.get("dropped") or []
    parts = []
    if dropped:
        parts.append(
            f"[FIDELITY] The base that was served is missing flap(s) "
            f"{dropped} from the tree you asked for. This is measured by "
            "comparing leaf-to-leaf path lengths -- the same quantity the "
            "packer solves against -- not estimated.")
    else:
        parts.append(
            f"[FIDELITY] The base that was served differs from the tree you "
            f"asked for by {drift:.1%} of the model's own span, and no rescue "
            "marker on the fold explains it. Measured on leaf-to-leaf path "
            "lengths, the quantity the packer solves against.")
    if repair:
        parts.append(
            "Repair now: compare read_base()'s worst_pairs against your "
            "requested tree and correct the attachment point or edge length "
            "for those flaps, then recompile ONCE and re-read. Do NOT rescale "
            "the model to hide the difference.")
    else:
        parts.append(
            "No autonomous repair budget is allocated for this check. This is "
            "a report only -- call read_base() if you want the per-pair "
            "detail, and raise it with the user rather than acting on it now.")
    return " ".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_fidelity_oracle.py -v --timeout=420
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/fidelity_oracle.py mcp_harness/tests/test_fidelity_oracle.py
git commit -m "feat(fidelity): the [FIDELITY] unexplained-drift oracle"
```

---

## Task 6: Bridge the oracle into the serve

**Files:**
- Modify: `web/server.py` — conn dict (`:342-352`), the fold branch of
  `_send_frames`, and the end-of-turn oracle block beside `[ANATOMY]` (`:436-466`)
- Test: `web/tests/test_server_fidelity_oracle.py` (create)

**Interfaces:**
- Consumes: `fidelity_oracle.decide` / `.message` (Task 5).
- Produces: conn keys `latest_fidelity_report`, `fidelity_checks`,
  `in_fidelity`.

⚠ **Read this before writing anything.** `[CP AUDIT]` is deliberately
**marker-keyed**: it triggers off a string on the served fold, so it fires
"independent of whether the agent remembered to lint"
(`test_server_cp_oracle.py:9-13`). `[FIDELITY]` **cannot** be marker-keyed,
because this plan changes no fold bytes and the tree is too large to ride
`frame_title` anyway.

So it is keyed on the agent having called `read_base()`, whose result the
bridge observes as an ordinary `tool_result`. That is a genuinely weaker
trigger than `[CP AUDIT]`'s, and the honest handling is to make the
not-called case an explicit, recorded stand-down rather than silence. This is
consistent with the oracle shipping with zero repair budget and the
`[ANATOMY]` precedent of "fires on NOTHING today, and that is the honest
state". Do not paper over it by inventing a fold marker.

- [ ] **Step 1: Read the existing pattern first**

```bash
sed -n '420,480p' web/server.py
sed -n '100,145p' web/tests/test_server_cp_oracle.py
```

- [ ] **Step 2: Write the failing test**

Create `web/tests/test_server_fidelity_oracle.py`:

```python
"""The [FIDELITY] bridge half.

UNLIKE [CP AUDIT], THIS ORACLE IS NOT MARKER-KEYED. [CP AUDIT] triggers off a
string on the served fold precisely so it fires whether or not the agent
remembered to lint. [FIDELITY] has no such marker -- the base inspection slice
changes no fold bytes -- so it keys on the agent having called read_base(),
and the not-called case is an explicit recorded stand-down. These tests pin
that asymmetry so nobody "fixes" it later by adding a fold marker.

Guard discipline is otherwise copied from the CP oracle: the dirty flag is
consumed per firing, budget is shared, and an errored turn defers.
"""
from __future__ import annotations

import json
import os
from types import SimpleNamespace

from starlette.testclient import TestClient

_COMPILE = "draft_and_compile_full_base"
_READ_BASE = "read_base"

_FOLD = {"file_spec": 1.1,
         "frame_title": "TreeMaker crease pattern (scale=0.615)",
         "vertices_coords": [[0, 0], [1, 0]],
         "edges_vertices": [[0, 1]], "edges_assignment": ["B"]}


def _read_base_out(drift=0.0, stage="none", dropped=()):
    return json.dumps({
        "status": "ok", "serve_id": 1, "stage": stage, "stubs": 0,
        "invents_anatomy": False, "scale": 0.6,
        "shadow_diff": {"invented": 0, "dropped": list(dropped),
                        "contracted": [], "path_drift_max": drift,
                        "path_drift_mean": drift, "worst_pairs": [],
                        "span": 1.0, "comparable": True},
        "served_tree": [],
    })


def _client(monkeypatch, turns, env=None):
    """Same shape as test_server_cp_oracle._cp_client."""
    import agent_loop
    import llm_client

    async def fake_connect(stack):
        return SimpleNamespace(sessions={}, tools=[], route={})

    monkeypatch.setattr(agent_loop, "connect_servers", fake_connect)
    monkeypatch.setattr(
        llm_client.LLMClient, "from_env",
        classmethod(lambda cls: SimpleNamespace(cfg=SimpleNamespace(
            provider="fake", model="fake"))),
    )
    calls = {"n": 0, "messages": None}

    async def fake_turn(client_, backend, messages, emit=None):
        calls["messages"] = messages
        events = turns[min(calls["n"], len(turns) - 1)]
        calls["n"] += 1
        for name, out in events:
            emit({"type": "tool_result", "name": name, "output": out,
                  "is_error": False})

    monkeypatch.setattr(agent_loop, "agent_turn", fake_turn)
    monkeypatch.delenv("IDE_SHAPE_OP", raising=False)
    monkeypatch.delenv("IDE_CP_REPAIR_RETRIES", raising=False)
    for k, v in (env or {}).items():
        monkeypatch.setenv(k, v)

    import importlib
    import web.server as server
    importlib.reload(server)
    monkeypatch.setattr(server, "_square_for_display", lambda f, w=1.0, h=1.0: f)
    return TestClient(server.app), calls


def _drain_turn(ws):
    frames = []
    while True:
        f = ws.receive_json()
        if f["type"] == "turn_end":
            return frames
        frames.append(f)


def test_unexplained_drift_injects_one_fidelity_message(monkeypatch):
    client, calls = _client(monkeypatch, [[
        (_COMPILE, json.dumps(_FOLD)),
        (_READ_BASE, _read_base_out(drift=0.31, stage="order")),
    ]])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make a dog"})
        _drain_turn(ws)
        echo = ws.receive_json()
        assert echo["type"] == "assistant"
        assert echo["text"].startswith("[FIDELITY] ")
    msgs = [m for m in calls["messages"] if m["role"] == "user"
            and str(m["content"]).startswith("[FIDELITY]")]
    assert len(msgs) == 1


def test_clean_base_never_fires(monkeypatch):
    client, calls = _client(monkeypatch, [[
        (_COMPILE, json.dumps(_FOLD)),
        (_READ_BASE, _read_base_out(drift=0.0)),
    ]])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make a dog"})
        _drain_turn(ws)
    assert calls["n"] == 1
    assert not [m for m in calls["messages"] if m["role"] == "user"
                and str(m["content"]).startswith("[FIDELITY]")]


def test_without_a_read_base_call_it_stands_down_not_fires(monkeypatch):
    """THE ASYMMETRY. No read_base result means no verdict -- and 'I do not
    know what was served' is not 'nothing was served'."""
    client, calls = _client(monkeypatch, [[(_COMPILE, json.dumps(_FOLD))]])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make a dog"})
        _drain_turn(ws)
    assert calls["n"] == 1
    assert not [m for m in calls["messages"] if m["role"] == "user"
                and str(m["content"]).startswith("[FIDELITY]")]


def test_fires_once_per_base_never_twice(monkeypatch):
    """The dirty flag is consumed per firing: a second end-of-turn on the same
    base must not re-fire, exactly as the CP oracle guarantees."""
    client, calls = _client(monkeypatch, [[
        (_COMPILE, json.dumps(_FOLD)),
        (_READ_BASE, _read_base_out(drift=0.31, stage="order")),
    ]])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make a dog"})
        _drain_turn(ws)
        ws.receive_json()                       # the one [FIDELITY] echo
        _drain_turn(ws)                          # the follow-up turn
    fid = [m for m in calls["messages"] if m["role"] == "user"
           and str(m["content"]).startswith("[FIDELITY]")]
    assert len(fid) == 1


def test_message_carries_no_standing_imperative(monkeypatch):
    client, calls = _client(monkeypatch, [[
        (_COMPILE, json.dumps(_FOLD)),
        (_READ_BASE, _read_base_out(drift=0.31, stage="order")),
    ]])
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "prompt", "text": "make a dog"})
        _drain_turn(ws)
        echo = ws.receive_json()
    low = echo["text"].lower()
    assert "repair now" not in low
    assert "no autonomous repair budget" in low
```

- [ ] **Step 3: Run test to verify it fails**

```bash
cd <repo> && PYTHONPATH=.:mcp_harness mcp_harness/.venv/bin/python -m pytest web/tests/test_server_fidelity_oracle.py -v --timeout=420
```

Expected: FAIL — no `[FIDELITY]` frame is emitted.

- [ ] **Step 4: Wire the bridge**

Add to the conn dict initialiser (beside the Slice 7 `[ANATOMY]` keys):

```python
            # [FIDELITY] oracle (base inspection loop, phase 1). Keyed on a
            # read_base tool_result, NOT on a fold marker -- see this slice's
            # test module for why that asymmetry is deliberate.
            "latest_base_report": None, "fidelity_checks": 0,
            "in_fidelity": False, "latest_fidelity_id": None,
```

In `_send_frames`'s `tool_result` branch, beside the existing handlers, record
the report:

```python
        if event.get("name") == "read_base" and not event.get("is_error"):
            try:
                conn["latest_base_report"] = json.loads(event["output"])
            except (ValueError, TypeError):
                conn["latest_base_report"] = None
```

In the end-of-turn oracle block, **after** the `[ANATOMY]` branch and gated on
neither `[CP AUDIT]` nor `[ANATOMY]` having fired this turn (they share one
budget), add:

```python
        # [FIDELITY]: report-only. It never composes an imperative, it consumes
        # its own one-shot flag, and it stands down silently when the agent did
        # not call read_base -- there is nothing to grade, and guessing would
        # grade the agent against itself.
        import fidelity_oracle
        report = conn.get("latest_base_report")
        if (report and conn["latest_id"] is not None
                and conn.get("latest_fidelity_id") != conn["latest_id"]):
            conn["latest_fidelity_id"] = conn["latest_id"]      # consume
            verdict = fidelity_oracle.decide(base_report=report)
            if verdict["fire"]:
                text = fidelity_oracle.message(verdict, repair=False)
                await ws.send_json({"type": "assistant", "text": text})
                messages.append({"role": "user", "content": text})
```

⚠ Match the surrounding block's actual variable names (`ws`, `messages`,
`conn`) — read `web/server.py:436-466` and follow it exactly rather than
copying these identifiers blind.

- [ ] **Step 5: Run test to verify it passes**

```bash
cd <repo> && PYTHONPATH=.:mcp_harness mcp_harness/.venv/bin/python -m pytest web/tests/ -v --timeout=420
```

Expected: all pass, including the pre-existing CP and anatomy oracle tests.
Those two must be **unchanged** — a shared budget that starves them is a
regression, not a trade.

- [ ] **Step 6: Commit**

```bash
git add web/server.py web/tests/test_server_fidelity_oracle.py
git commit -m "feat(fidelity): wire [FIDELITY] into the serve bridge"
```

---

## Task 7: Print leaf positions in the reference report

Nearly free, and it is Phase 3's Gate-2 experiment: if the text table already
answers the recognisability question, the picture is redundant.

**Files:**
- Modify: `mcp_harness/mesh_report.py:17-33`
- Test: `mcp_harness/tests/test_mesh_report.py` (append; create if absent)

**Interfaces:**
- Consumes: `leaf_labels[nid]["position"]`, already written at
  `mesh_to_tree.py:776` as `[round(float(c), 4) for c in pos]`.
- Produces: one extra clause per anatomy line.

- [ ] **Step 1: Write the failing test**

```python
def test_anatomy_lines_print_the_measured_position():
    labels = {3: {"label": "front-left leg", "basis": "extremal",
                  "position": [0.1234, -0.5, 0.25]}}
    lines = mesh_report._anatomy_lines(labels)
    body = "\n".join(lines)
    assert "front-left leg" in body
    assert "0.1234" in body


def test_anatomy_lines_survive_a_label_with_no_position():
    labels = {3: {"label": "tail", "basis": "extremal"}}
    lines = mesh_report._anatomy_lines(labels)
    assert any("tail" in ln for ln in lines)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_mesh_report.py -k anatomy_lines -v --timeout=420
```

Expected: FAIL on the `0.1234` assertion.

- [ ] **Step 3: Write minimal implementation**

In `mesh_report._anatomy_lines`, change:

```python
            lines.append(f"  node {nid} -> {label}" + (f" ({basis})" if basis else ""))
```

to:

```python
            pos = info.get("position")
            # The measured anatomical position, which this block used to drop.
            # Display only: it lives on leaf_labels, NOT on the tree nodes, so
            # it is outside the packing path by construction -- never copy it
            # onto a node dict, where it would sit beside the x/y packing seeds.
            pos_txt = ""
            if isinstance(pos, (list, tuple)) and len(pos) == 3:
                pos_txt = "  at [{}, {}, {}]".format(*pos)
            lines.append(f"  node {nid} -> {label}"
                         + (f" ({basis})" if basis else "") + pos_txt)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_mesh_report.py -v --timeout=420
```

Expected: all pass. Some report-text goldens may need re-blessing — inspect
each diff and confirm it is only the added `at [...]` clause before blessing.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/mesh_report.py mcp_harness/tests/test_mesh_report.py
git commit -m "feat(report): print measured leaf positions in the anatomy block"
```

---

# PHASE 2 — the renderers

Everything below writes PNGs to disk for **humans**. No model sees them in this
plan. Phase 3 is a separate plan written only after Phase 2 reports.

## Task 8: The packing diagram

**Files:**
- Create: `mcp_harness/tree_render.py`
- Test: `mcp_harness/tests/test_tree_render.py`
- Modify: `.github/workflows/ci.yml` (pin Pillow)

**Interfaces:**
- Consumes: `locs` (`[(json_id, x, y), ...]`) and the requested node list.
- Produces:
  - `packing_diagram(locs, nodes, out_path, *, scale=1.0, size=800) -> dict`
    returning `{"path": str, "circles": [{"id": int, "x": float, "y": float,
    "r": float, "engine_made": bool}], "note": str}`.

- [ ] **Step 1: Write the failing test**

```python
"""The packing diagram -- the ONE view that carries anatomy.

A folded base cannot show limb placement to anyone (every flap tip collapses
onto one line), but the PACKING still gives each limb its own disc of paper.
This render is the last moment a limb has extent rather than only length.

NEVER assert a byte hash over the PNG. Renders differ across platforms by
antialiasing; a frozen hash over roundoff-bearing artifacts cannot be green on
both, and this repo has already retired one such gate. Assert STRUCTURE.
"""
import json
import os

import tree_render


NODES = [
    {"id": 0, "parent_id": None, "length": 0.0},
    {"id": 1, "parent_id": 0, "length": 0.25},
    {"id": 2, "parent_id": 0, "length": 0.50},
]
LOCS = [(1, 0.2, 0.2), (2, 0.8, 0.8)]


def test_one_circle_per_leaf(tmp_path):
    out = tree_render.packing_diagram(LOCS, NODES, str(tmp_path / "p.png"))
    assert len(out["circles"]) == 2
    assert {c["id"] for c in out["circles"]} == {1, 2}


def test_radius_is_proportional_to_flap_length(tmp_path):
    out = tree_render.packing_diagram(LOCS, NODES, str(tmp_path / "p.png"))
    by = {c["id"]: c for c in out["circles"]}
    assert by[2]["r"] == 2 * by[1]["r"]


def test_engine_made_leaves_are_marked_distinctly(tmp_path):
    locs = LOCS + [(-1, 0.5, 0.5)]
    out = tree_render.packing_diagram(locs, NODES, str(tmp_path / "p.png"))
    made = [c for c in out["circles"] if c["engine_made"]]
    assert len(made) == 1
    assert made[0]["id"] == -1


def test_the_river_limitation_is_stamped_on_the_render(tmp_path):
    out = tree_render.packing_diagram(LOCS, NODES, str(tmp_path / "p.png"))
    assert "river" in out["note"].lower()


def test_writes_a_readable_png(tmp_path):
    p = str(tmp_path / "p.png")
    tree_render.packing_diagram(LOCS, NODES, p)
    assert os.path.exists(p) and os.path.getsize(p) > 0
    from PIL import Image
    with Image.open(p) as im:
        assert im.size == (800, 800)


def test_deterministic_within_a_platform(tmp_path):
    a, b = str(tmp_path / "a.png"), str(tmp_path / "b.png")
    tree_render.packing_diagram(LOCS, NODES, a)
    tree_render.packing_diagram(LOCS, NODES, b)
    assert open(a, "rb").read() == open(b, "rb").read()
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_tree_render.py -v --timeout=420
```

Expected: `ModuleNotFoundError: No module named 'tree_render'`.

- [ ] **Step 3: Write minimal implementation**

Create `mcp_harness/tree_render.py`:

```python
"""Renders for human eyes. NOTHING here is shown to a model in this slice.

WHY THE PACKING AND NOT THE FOLDED BASE. A uniaxial base is DEFINED by every
flap lying on one axis, so when it is flattened every flap tip aligns along a
single line -- folding is the operation that destroys spatial separation
between limbs. That is not a camera problem and no render fixes it (see
docs/superpowers/evidence/2026-08-03-reparented-bases/bases.svg, whose panels
are featureless wedges). The PACKING is one step earlier, and there each limb
still owns its own disc of paper: the last moment a limb has EXTENT rather
than only LENGTH.

NEVER FREEZE A BYTE HASH OVER THESE PNGs. Antialiasing differs across
platforms; this repo has already retired one frozen-hash gate that could not be
green on both. Assert structure -- which is why every function here returns a
dict describing what it drew.
"""
from __future__ import annotations

from PIL import Image, ImageDraw

#: Stamped on every packing diagram. v1 draws leaf circles only: a river's
#: width is an INTERNAL tree edge, and leaf_node_locations returns leaf
#: positions only, so there is no binding to draw one from. Saying so on the
#: image is the mitigation for "the diagram without rivers misleads".
RIVER_NOTE = ("Circles only -- no rivers. A river's width is an internal tree "
              "edge and the engine binding returns LEAF locations only, so "
              "this shows limb allocation, not the body segments between limbs.")

_BG = (255, 255, 255)
_INK = (20, 20, 20)
_ENGINE = (200, 60, 60)


def _leaf_lengths(nodes) -> dict:
    """{leaf id: its own edge length}. Engine-made leaves are not in `nodes`."""
    return {n["id"]: float(n.get("length") or 0.0) for n in (nodes or [])}


def packing_diagram(locs, nodes, out_path, *, scale=1.0, size=800) -> dict:
    """Draw the unit square with one labelled circle per packed leaf.

    Radius is proportional to the flap's own length -- Lang's circle-packing
    invariant: every flap gets "a circular region whose radius equals the
    length of that flap". Engine-made leaves arrive as json_id == -1 (the
    convention leaf_node_locations already uses) and are drawn distinctly,
    because a flap nobody requested must never read as anatomy.
    """
    lengths = _leaf_lengths(nodes)
    longest = max([v for v in lengths.values() if v > 0] or [1.0])

    img = Image.new("RGB", (size, size), _BG)
    d = ImageDraw.Draw(img)
    pad = int(size * 0.06)
    box = size - 2 * pad
    d.rectangle([pad, pad, pad + box, pad + box], outline=_INK, width=2)

    circles = []
    for row in (locs or []):
        nid, x, y = int(row[0]), float(row[1]), float(row[2])
        engine_made = nid == -1
        length = lengths.get(nid, longest * 0.25)
        r = (length / longest) * (box * 0.5) * float(scale)
        cx, cy = pad + x * box, pad + (1.0 - y) * box
        colour = _ENGINE if engine_made else _INK
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=colour, width=2)
        d.text((cx + 3, cy + 3), "engine" if engine_made else str(nid),
               fill=colour)
        circles.append({"id": nid, "x": x, "y": y, "r": r,
                        "engine_made": engine_made})

    d.text((pad, pad + box + 8), RIVER_NOTE, fill=_INK)
    img.save(out_path)
    return {"path": out_path, "circles": circles, "note": RIVER_NOTE}
```

⚠ `d.text` uses Pillow's default bitmap font, which is deterministic within a
platform and needs no font file — that is what makes
`test_deterministic_within_a_platform` pass without shipping a `.ttf`.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_tree_render.py -v --timeout=420
```

Expected: 6 passed.

- [ ] **Step 5: Pin Pillow in CI**

In `.github/workflows/ci.yml`, alongside the existing scikit-learn pin (line
~138), add `"pillow==12.2.0"`. Pillow arrives transitively today — the exact
hazard the file already documents for scikit-learn.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/tree_render.py mcp_harness/tests/test_tree_render.py .github/workflows/ci.yml
git commit -m "feat(render): the packing diagram, the one anatomy-legible view"
```

---

## Task 9: The tree sheet

**Files:**
- Modify: `mcp_harness/tree_render.py`, `mcp_harness/tests/test_tree_render.py`

**Interfaces:**
- Produces: `tree_sheet(nodes, out_path, *, leaf_labels=None, size=800) -> dict`
  returning `{"path": str, "views": ["top", "side", "front", "iso"],
  "segments": int, "measured": bool, "stamp": str}`.

- [ ] **Step 1: Write the failing test**

```python
def test_four_views_at_fixed_dimensions(tmp_path):
    out = tree_render.tree_sheet(NODES, str(tmp_path / "t.png"))
    assert out["views"] == ["top", "side", "front", "iso"]
    from PIL import Image
    with Image.open(out["path"]) as im:
        assert im.size == (800, 800)


def test_n_bones_render_n_segments(tmp_path):
    out = tree_render.tree_sheet(NODES, str(tmp_path / "t.png"))
    assert out["segments"] == 2          # two edges: 0->1 and 0->2


def test_a_tree_without_measured_positions_is_stamped_as_a_layout(tmp_path):
    out = tree_render.tree_sheet(NODES, str(tmp_path / "t.png"))
    assert out["measured"] is False
    assert out["stamp"] == "LAYOUT, NOT MEASURED"


def test_measured_positions_are_used_and_not_stamped(tmp_path):
    labels = {1: {"label": "leg", "basis": "extremal", "position": [0.1, 0.2, 0.3]},
              2: {"label": "tail", "basis": "extremal", "position": [0.4, 0.5, 0.6]}}
    out = tree_render.tree_sheet(NODES, str(tmp_path / "t.png"),
                                 leaf_labels=labels)
    assert out["measured"] is True
    assert out["stamp"] == ""


def test_the_renderer_never_writes_coordinates_onto_a_node(tmp_path):
    """anat_pos does not exist and must not be created. Coordinates live on
    leaf_labels, off the node list -- which is what keeps them outside the
    packing path by construction rather than by rule."""
    labels = {1: {"label": "leg", "basis": "e", "position": [0.1, 0.2, 0.3]}}
    before = json.dumps(NODES, sort_keys=True)
    tree_render.tree_sheet(NODES, str(tmp_path / "t.png"), leaf_labels=labels)
    assert json.dumps(NODES, sort_keys=True) == before
    for n in NODES:
        assert "anat_pos" not in n and "position" not in n
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_tree_render.py -k sheet -v --timeout=420
```

Expected: `AttributeError: module 'tree_render' has no attribute 'tree_sheet'`.

- [ ] **Step 3: Write minimal implementation**

Add to `mcp_harness/tree_render.py`:

```python
import math

#: Stamped on any sheet whose coordinates are a LAYOUT rather than a
#: measurement. A guessed pose presented as data is worse than no pose.
LAYOUT_STAMP = "LAYOUT, NOT MEASURED"

#: (label, projection) -- projection maps (x, y, z) to plane coordinates.
_VIEWS = [
    ("top",   lambda p: (p[0], p[1])),
    ("side",  lambda p: (p[0], p[2])),
    ("front", lambda p: (p[1], p[2])),
    # Standard isometric: 45 deg about the vertical, then 35.264 deg tilt.
    ("iso",   lambda p: ((p[0] - p[1]) * math.cos(math.radians(30.0)),
                         (p[0] + p[1]) * math.sin(math.radians(30.0)) - p[2])),
]


def _layout_positions(nodes) -> dict:
    """Deterministic fallback pose: depth on z, children fanned in x/y.

    Deliberately crude. Its only job is to make the graph readable; the stamp
    is what stops it being mistaken for the measured anatomy.
    """
    by_parent: dict = {}
    for n in nodes:
        by_parent.setdefault(n.get("parent_id"), []).append(n["id"])
    pos, depth = {}, {}
    order = [n["id"] for n in nodes if n.get("parent_id") is None]
    for nid in order:
        pos[nid], depth[nid] = (0.0, 0.0, 0.0), 0
    i = 0
    while i < len(order):
        pid = order[i]
        i += 1
        kids = sorted(by_parent.get(pid, []))
        for k, kid in enumerate(kids):
            ang = (2.0 * math.pi * k) / max(1, len(kids))
            d = depth[pid] + 1
            pos[kid] = (math.cos(ang) * d, math.sin(ang) * d, float(d))
            depth[kid] = d
            order.append(kid)
    return pos


def tree_sheet(nodes, out_path, *, leaf_labels=None, size=800) -> dict:
    """Four orthographic views of the Metric Tree on one sheet.

    Coordinates come from leaf_labels[nid]["position"] when EVERY leaf has one
    -- the measured anatomical position the extractor already records. They are
    read, never written back: `position` lives on leaf_labels, a separate
    object from the node list, which is what keeps it outside the packing path
    by construction rather than by rule. There is no `anat_pos` field on a node
    and none must be created.
    """
    nodes = list(nodes or [])
    labels = leaf_labels or {}
    leaves = [n["id"] for n in nodes
              if n.get("parent_id") is not None
              and all(o.get("parent_id") != n["id"] for o in nodes)]

    measured_pos = {}
    for nid in leaves:
        p = (labels.get(nid) or {}).get("position")
        if isinstance(p, (list, tuple)) and len(p) == 3:
            measured_pos[nid] = tuple(float(c) for c in p)
    measured = bool(leaves) and len(measured_pos) == len(leaves)

    pos = _layout_positions(nodes)
    if measured:
        pos = {**pos, **measured_pos}

    edges = [(n["parent_id"], n["id"]) for n in nodes
             if n.get("parent_id") is not None]

    img = Image.new("RGB", (size, size), _BG)
    d = ImageDraw.Draw(img)
    half = size // 2
    stamp = "" if measured else LAYOUT_STAMP

    for idx, (name, proj) in enumerate(_VIEWS):
        ox, oy = (idx % 2) * half, (idx // 2) * half
        d.rectangle([ox, oy, ox + half - 1, oy + half - 1], outline=_INK)
        d.text((ox + 6, oy + 6), name, fill=_INK)
        if stamp:
            d.text((ox + 6, oy + half - 16), stamp, fill=_ENGINE)
        pts = {nid: proj(p) for nid, p in pos.items()}
        xs = [p[0] for p in pts.values()] or [0.0]
        ys = [p[1] for p in pts.values()] or [0.0]
        spread = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
        k = (half - 60) / spread

        def place(nid):
            px, py = pts[nid]
            return (ox + half / 2 + (px - (min(xs) + max(xs)) / 2) * k,
                    oy + half / 2 + (py - (min(ys) + max(ys)) / 2) * k)

        for a, b in edges:
            if a in pts and b in pts:
                d.line([place(a), place(b)], fill=_INK, width=2)

    img.save(out_path)
    return {"path": out_path, "views": [v[0] for v in _VIEWS],
            "segments": len(edges), "measured": measured, "stamp": stamp}
```

⚠ Nothing above mutates `nodes` or any node dict — `_layout_positions` builds
its own `pos` map. `test_the_renderer_never_writes_coordinates_onto_a_node`
asserts exactly that.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_tree_render.py -v --timeout=420
```

Expected: 11 passed.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/tree_render.py mcp_harness/tests/test_tree_render.py
git commit -m "feat(render): the four-view tree sheet"
```

---

## Task 10: Scorecard columns and the full regression

**Files:**
- Modify: `mcp_harness/benchmark_subjects.py:320` (`_COLS`) and the row builder
- Test: `mcp_harness/tests/test_benchmark_subjects.py` (append)

**Interfaces:**
- Consumes: `shadow_tree.shadow_diff` (Task 1).
- Produces: two new columns, `path_drift_max` and `served_stage`.

⚠ Per spec open question 6, `contracted` is deliberately **not** a column: it
is bookkeeping, and a column invites someone to drive it to zero, which would
mean disabling a rescue that works.

- [ ] **Step 1: Write the failing test**

```python
def test_scorecard_carries_the_new_fidelity_columns():
    assert "path_drift_max" in benchmark_subjects._COLS
    assert "served_stage" in benchmark_subjects._COLS


def test_existing_scorecard_columns_are_unchanged():
    for col in ["subject", "R", "served_leaves", "stub_flaps",
                "served_fidelity", "pair_gap_max", "pair_path_gap_max"]:
        assert col in benchmark_subjects._COLS
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_benchmark_subjects.py -k scorecard -v --timeout=420
```

Expected: FAIL on the first assertion.

- [ ] **Step 3: Write minimal implementation**

Add both names to `_COLS` and populate them in the row builder from
`shadow_diff`, defaulting to `0.0` / `"none"` when no served tree was recorded.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_benchmark_subjects.py -v --timeout=420
```

Expected: all pass.

- [ ] **Step 5: Run the FULL regression from the MAIN checkout**

⚠ **Not from a worktree.** A worktree borrowing main's `.so` reports 27
baseline failures instead of ~3, which would bury a real regression.

First check the host is idle:

```bash
ps -Ao pcpu,etime,command -r | head -8
```

Then:

```bash
cd <repo> && make test 2>&1 | tail -40
```

⚠ The suite **looks hung early** (~0% CPU) and finishes in roughly 23 minutes.
Do not kill it. Expected shape: the documented baseline (~4 failed / ~2124
passed / ~11 skipped on macOS), ± rows this plan deliberately re-blessed in
Task 7. **Any other change is a regression to fix, not to bless.**

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/benchmark_subjects.py mcp_harness/tests/test_benchmark_subjects.py
git commit -m "feat(scorecard): add path_drift_max and served_stage columns"
```

---

## Phase 2 report (required before any Phase 3 plan)

Write `docs/superpowers/handoffs/2026-08-04-base-inspection-phase-2-report.md`
answering, with evidence:

1. Did `leaf_node_locations` survive to the serve payload on every scorecard
   subject? (Phase 2's STOP IF.)
2. What is `path_drift_max` on each scorecard subject, and did `[FIDELITY]`
   fire on any of them?
3. Read the packing diagrams **in anger**. Is limb allocation legible? Does the
   missing-rivers limitation mislead in practice? (Spec open question 4.)
4. Does the leaf-`position` text table from Task 7 already answer the
   recognisability question? **If yes, Phase 3's picture is redundant and the
   spec says stop.**

Phase 3 is planned only after this report, and only if both of its
preconditions (§3.5) pass.

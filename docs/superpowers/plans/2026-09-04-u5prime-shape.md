# U5′ (shape, not count) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether an LLM can supply the **pairing** a mesh extraction gets wrong, on trees whose leaf count is already correct — and refuse to ship it if a mechanical mirror rule does just as well.

**Architecture:** Three arms over the same four subjects. **A** is the tree as served today. **C** is a *null producer*: a deterministic mirror rule over per-stick azimuths. **B** is the LLM, given exactly the same information C gets — the tree's structure and P1's orientation channel, never coordinates. B ships only if it beats **both**.

**Tech Stack:** Python 3.14, pytest, `orientations.py` (P1), `llm_client.py`. No new dependencies.

## Global Constraints

- **No LLM output is ever a coordinate, a voxel resolution or a prune fraction.** The model sees node ids, parent ids, lengths and per-stick azimuth/elevation. Nothing else. (spec §1.4)
- **LEAF COUNT MUST NOT MOVE.** U5′ supplies pairing on a tree whose count it does not touch. Any leaf-count change means the unit exceeded its scope and **the run is VOID, not merely failed.**
- **`stub_flaps` must not rise on any subject.** Terminal — it outranks scale in `order_rank` (K1) and proportion integrity in `_serve_rank`.
- **Do not grade against `anatomy_reference.json`.** It is frozen and extraction-derived; its own `_meta` reads *"NOT ground truth"*. Grading against it re-enters the closed loop this design exists to escape.
- **Offline degradation is mandatory.** No key → `propose_pairs` returns `None` and every caller is byte-identical to today.
- **The named recurring failure mode is "an instrument that reads green for the wrong reason."** Mutation-verify every test: break the code it guards and confirm it goes red.
- Do not modify `vlm_judge.py`, `order_rank.py`, `_serve_rank`, or `MIN_LEAVES, MAX_LEAVES = 4, 8`.
- ⚠ **`_serve_rank` is inverted against a correct LLM tree** — its first key scores against an `anchor_r` voted over the mesh's own prune curve, which reads 5 for the lizard whose correct count is 6. U5′ must change **only `len(pairs)`**, holding keys 1–3 constant by construction. Nothing here may enter the ranker on key 1.

## The measured premise this plan rests on

Step zero (2026-09-04, live meshes, current default) found **four of four subjects reach their authored leaf count inside the shipped grid and not one has the right pair structure:**

| subject | cell | leaves | pairs | unpaired | pairs the anatomy wants |
|---|---|---|---|---|---|
| lizard | 64/0.20 | 6 ✓ | 1 | 4 | 2 (four legs) |
| bird | 128/0.30 | 6 ✓ | 1 | 4 | 2 (wings, legs) |
| spider | 64/0.45 | 9 ✓ | 3 | 3 | 4 (eight legs) |
| **horse** | 64/0.20 | 6 ✓ | **0** | **6** | 2 (four legs) |

**The count is solved everywhere; the shape is solved nowhere.** No cherry-picking is possible — every subject fails the same way.

## Prior art (CLAUDE.md §0)

| Adaptation | Source | Note |
|---|---|---|
| Named joints + per-stick azimuth/elevation as the LLM's view of a skeleton | COrigami §3.1, Appendix C.1 | ⚠ **Their schema has NO pairs field.** Symmetry is prompt-encouraged and implicit in mirrored azimuths. Ours cannot express angles in the tree, so the mirror must arrive as an explicit list. |
| **Rejected:** inherit COrigami's evidence that an LLM declares symmetry | — | It does not exist. They show mirrored *angles*, never a declared pairing. **U5′ must carry its own evidence.** This is the largest risk in the unit. |
| Breadth over depth: sample K candidates, rank by a real check | Olausson et al., ICLR'24 | Their producers were measured; COrigami's T/N table is the *judge's* config and does not transfer. |
| A null/trivial baseline the real system must beat | This repo, `probe_freeze_decision`'s null critic; standard ablation practice | Arm C exists because "the LLM found the pairing" and "any mirror rule finds the pairing" are indistinguishable without it. |

---

## Setup

```bash
cd <repo>
git worktree add .claude/worktrees/u5prime -b claude/u5prime main
cd .claude/worktrees/u5prime/mcp_harness
ln -sf ../../../mcp_harness/headless_treemaker.cpython-314-darwin.so .
ln -sf ../../../mcp_harness/oriedita/*.jar oriedita/
ln -sf ../../../mcp_harness/OrieditaValidator.class .
ln -sf ../../../.env ../.env
```

Run tests with `PYTHONPATH=.:tests .venv/bin/python3 -m pytest tests/<file> -v`.
⚠ Any standalone script needs an `if __name__ == "__main__":` guard — the pipeline spawns multiprocessing children that re-import `__main__`.

---

## File Structure

| File | Responsibility |
|---|---|
| `mcp_harness/pair_producers.py` (create) | Both producers. `mirror_pairs` (arm C, deterministic) and `propose_pairs` (arm B, LLM). One file because they must share an input contract exactly. |
| `mcp_harness/probe_u5prime.py` (create) | The G1–G4 bar, with `verdict()` as a tested pure function. |
| `mcp_harness/tests/test_pair_producers.py` (create) | Guards both producers, including that they consume identical inputs. |
| `mcp_harness/tests/test_u5prime_bar.py` (create) | Guards `verdict()`, mutation-verified both directions. |

---

## Task 1: The null producer — arm C

Build the control **first**. It costs nothing, and if it recovers the pairings on its own the LLM has a high bar to clear rather than an empty one.

**Files:** Create `mcp_harness/pair_producers.py`, `mcp_harness/tests/test_pair_producers.py`

**Interfaces:**
- Consumes: `orientations.stick_orientations(positions, parent_of, frame) -> {node_id: {"azimuth", "elevation", "space"}}` (P1).
- Produces: `mirror_pairs(nodes, orients, *, az_tol=15.0, el_tol=20.0, len_tol=0.25) -> list[list[int]]`

- [ ] **Step 1: Write the failing tests**

```python
"""Arm C, the null producer. Its whole job is to be the thing the LLM must beat.

A pairing is only evidence about a MODEL if a mechanical rule on the same
inputs cannot produce it. This rule sees exactly what the model sees -- node
ids, parent ids, lengths, and P1's per-stick azimuth/elevation -- and never
coordinates.
"""
import pair_producers as pp

_NODES = [{"id": 0, "parent_id": None, "length": 0},
          {"id": 1, "parent_id": 0, "length": 0.40},   # left  fore
          {"id": 2, "parent_id": 0, "length": 0.40},   # right fore
          {"id": 3, "parent_id": 0, "length": 0.42},   # left  hind
          {"id": 4, "parent_id": 0, "length": 0.42},   # right hind
          {"id": 5, "parent_id": 0, "length": 0.30},   # head, unpaired
          {"id": 6, "parent_id": 0, "length": 0.55}]   # tail, unpaired


_ORIENTS = {1: {"azimuth": 60.0, "elevation": -30.0, "space": "mesh"},
            2: {"azimuth": -60.0, "elevation": -30.0, "space": "mesh"},
            3: {"azimuth": 120.0, "elevation": -30.0, "space": "mesh"},
            4: {"azimuth": -120.0, "elevation": -30.0, "space": "mesh"},
            5: {"azimuth": 0.0, "elevation": 10.0, "space": "mesh"},
            6: {"azimuth": 180.0, "elevation": 5.0, "space": "mesh"}}


def test_mirrored_azimuths_of_equal_length_pair():
    assert pp.mirror_pairs(_NODES, _ORIENTS) == [[1, 2], [3, 4]]


def test_the_axial_leaves_stay_unpaired():
    # head at azimuth 0 and tail at 180 are their own mirror image; pairing a
    # leaf with itself, or with the other axial leaf, is not bilateral symmetry.
    pairs = pp.mirror_pairs(_NODES, _ORIENTS)
    assert not any(5 in p or 6 in p for p in pairs)


def test_a_length_mismatch_refuses_the_pair():
    nodes = [dict(n) for n in _NODES]
    nodes[2]["length"] = 0.90          # right fore no longer matches left
    assert [1, 2] not in pp.mirror_pairs(nodes, _ORIENTS)


def test_an_elevation_mismatch_refuses_the_pair():
    o = {k: dict(v) for k, v in _ORIENTS.items()}
    o[2]["elevation"] = 60.0
    assert [1, 2] not in pp.mirror_pairs(_NODES, o)


def test_no_leaf_appears_in_two_pairs():
    pairs = pp.mirror_pairs(_NODES, _ORIENTS)
    seen = [n for p in pairs for n in p]
    assert len(seen) == len(set(seen))


def test_missing_orientations_yield_no_pairs_not_a_crash():
    assert pp.mirror_pairs(_NODES, {}) == []


def test_pairs_are_sorted_and_deterministic():
    a = pp.mirror_pairs(_NODES, _ORIENTS)
    b = pp.mirror_pairs(list(reversed(_NODES)), _ORIENTS)
    assert a == b == sorted(a), "the null arm must not depend on input order"
```

- [ ] **Step 2: Run and watch them fail**

Run: `cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python3 -m pytest tests/test_pair_producers.py -v`
Expected: FAIL, `ModuleNotFoundError: No module named 'pair_producers'`.

- [ ] **Step 3: Implement**

Create `mcp_harness/pair_producers.py`:

```python
"""Two producers of `symmetric_pairs`, sharing one input contract.

Arm C (`mirror_pairs`) is deterministic and free. Arm B (`propose_pairs`) asks
a model. They take IDENTICAL inputs on purpose: the only thing that may differ
between the arms is the producer, or the comparison says nothing.

⚠ NEITHER PRODUCER SEES COORDINATES. Spec section 1.4 -- the model gets node
ids, parent ids, lengths and P1's per-stick azimuth/elevation, and nothing
else. `mirror_pairs` is held to the same diet so the control is fair.
"""
import json


def _leaf_ids(nodes):
    """Ids with no children. The root is never a leaf even at degree 1."""
    parents = {n.get("parent_id") for n in nodes}
    return [n["id"] for n in nodes
            if n["id"] not in parents and n.get("parent_id") is not None]


def _norm(deg):
    """Fold an angle to (-180, 180]."""
    d = float(deg) % 360.0
    return d - 360.0 if d > 180.0 else d


def mirror_pairs(nodes, orients, *, az_tol=15.0, el_tol=20.0, len_tol=0.25):
    """ARM C. Pair leaves whose azimuths are mirror images about the axis.

    The rule: two leaves pair when their azimuths are reflections (a and -a),
    their elevations agree, and their lengths agree relatively. Axial leaves
    (azimuth ~0 or ~180) are their OWN mirror image and are left unpaired --
    pairing them would manufacture a symmetry that is not bilateral.

    Deterministic and order-independent: candidates are scored, then taken
    greedily by ascending residual with each leaf used at most once.
    """
    by_id = {n["id"]: n for n in nodes}
    leaves = [i for i in _leaf_ids(nodes) if i in orients]
    cand = []
    for a in leaves:
        for b in leaves:
            if a >= b:
                continue
            oa, ob = orients[a], orients[b]
            az_a, az_b = _norm(oa.get("azimuth", 0.0)), _norm(ob.get("azimuth", 0.0))
            if min(abs(az_a), abs(180.0 - abs(az_a))) < az_tol:
                continue                      # a is axial -- its own mirror
            if min(abs(az_b), abs(180.0 - abs(az_b))) < az_tol:
                continue
            az_res = abs(az_a + az_b)         # mirrored means a == -b
            if az_res > az_tol:
                continue
            el_res = abs(float(oa.get("elevation", 0.0)) - float(ob.get("elevation", 0.0)))
            if el_res > el_tol:
                continue
            la = float(by_id[a].get("length") or 0.0)
            lb = float(by_id[b].get("length") or 0.0)
            scale = max(la, lb) or 1.0
            len_res = abs(la - lb) / scale
            if len_res > len_tol:
                continue
            cand.append((az_res + el_res + len_res * 100.0, a, b))
    used, out = set(), []
    for _res, a, b in sorted(cand):
        if a in used or b in used:
            continue
        used.add(a); used.add(b)
        out.append([a, b])
    return sorted(out)
```

- [ ] **Step 4: Run the tests**

Run: `PYTHONPATH=.:tests .venv/bin/python3 -m pytest tests/test_pair_producers.py -v`
Expected: PASS.

- [ ] **Step 5: Mutation-verify**

Delete the axial guard (`if min(abs(az_a), ...) < az_tol: continue`, both arms).
Run: `-k axial`
Expected: `test_the_axial_leaves_stay_unpaired` FAILS. **Restore and re-run green.** Do the same for the length check and confirm `test_a_length_mismatch_refuses_the_pair` reddens.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/pair_producers.py mcp_harness/tests/test_pair_producers.py
git commit -m "feat(U5'): the null producer -- a mirror rule the LLM must beat"
```

---

## Task 2: Measure arm C against the four subjects, before any LLM exists

⚠ **This task can cancel the unit.** If the mirror rule already recovers the correct pairings, there is no gap for a model to fill and U5′ should not be built. Run it before spending a single billed call.

**Files:** Create `mcp_harness/probe_u5prime.py` (arm A and C only for now)

- [ ] **Step 1: Write the probe's arm-A/C sweep**

For each of `lizard 64/0.20`, `bird 128/0.30`, `spider 64/0.45`, `horse 64/0.20`, using the live meshes under `/tmp/m4-live/<prompt>-control/mesh.glb`: build the tree at that cell, emit `(nodes, pairs)` via `to_metric_tree`, compute `orientations` via `mesh_to_tree.frame_from_mesh` + `orientations.stick_orientations`, then record:

`subject, cell, leaves, pairs_A (len), pairs_C (len), pairs_C_ids`

- [ ] **Step 2: Run it and report, before writing any interpretation**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python3 probe_u5prime.py --arms AC
```

- [ ] **Step 3: STOP and decide**

The expected counts are lizard 2, bird 2, spider 4, horse 2.

* **If arm C reaches those on 3 or more subjects → CANCEL U5′.** The gap is mechanical, not semantic; report it and stop. This is a real outcome, not a failure.
* **If arm C reaches them on 0–1 subjects →** the gap is real and Task 3 proceeds.
* **In between → report and ask.** Do not proceed on a judgement call.

- [ ] **Step 4: Commit the arm-A/C fixture whichever way it goes**

```bash
git add mcp_harness/probe_u5prime.py mcp_harness/fixtures/u5prime_ac.json
git commit -m "probe(U5'): arm C measured against four subjects before any LLM"
```

---

## Task 3: `propose_pairs` — arm B

**Only if Task 2 said proceed.**

**Files:** Modify `mcp_harness/pair_producers.py`, `mcp_harness/tests/test_pair_producers.py`

**Interfaces:**
- Produces: `propose_pairs(prompt, nodes, orients, *, client=None) -> list[list[int]] | None`

- [ ] **Step 1: Write the failing tests**

```python
class _FakeClient:
    def __init__(self, reply):
        self.reply, self.calls, self.last_prompt = reply, 0, None

    def complete(self, prompt):
        # last_prompt is what test_the_model_never_sees_a_coordinate reads --
        # the only way to assert on what actually left the process.
        self.calls, self.last_prompt = self.calls + 1, prompt
        return self.reply


def test_no_client_returns_None_not_an_empty_list():
    # None and [] mean different things: None is "no opinion", [] is "no pairs".
    assert pp.propose_pairs("a horse", _NODES, _ORIENTS, client=None) is None


def test_a_well_formed_reply_is_accepted():
    c = _FakeClient('{"symmetric_pairs": [[1, 2], [3, 4]]}')
    assert pp.propose_pairs("a horse", _NODES, _ORIENTS, client=c) == [[1, 2], [3, 4]]


def test_a_pair_naming_a_non_leaf_is_DISCARDED():
    c = _FakeClient('{"symmetric_pairs": [[0, 1]]}')   # 0 is the root
    assert pp.propose_pairs("a horse", _NODES, _ORIENTS, client=c) == []


def test_a_leaf_in_two_pairs_is_DISCARDED():
    c = _FakeClient('{"symmetric_pairs": [[1, 2], [2, 3]]}')
    got = pp.propose_pairs("a horse", _NODES, _ORIENTS, client=c)
    seen = [n for p in got for n in p]
    assert len(seen) == len(set(seen))


def test_a_malformed_reply_returns_None_not_a_crash():
    for bad in ("not json", '{"symmetric_pairs": "x"}', '{}', '[[1,2]]'):
        assert pp.propose_pairs("a horse", _NODES, _ORIENTS,
                                client=_FakeClient(bad)) is None


def test_the_model_never_sees_a_coordinate():
    c = _FakeClient('{"symmetric_pairs": []}')
    pp.propose_pairs("a horse", _NODES, _ORIENTS, client=c)
    sent = c.last_prompt
    for banned in ("pos", "xyz", "coordinate", "voxel", "prune"):
        assert banned not in sent.lower(), f"{banned!r} reached the model"


def test_both_producers_take_the_same_inputs():
    # If the arms ever diverge on inputs, the comparison stops meaning anything.
    import inspect
    b = inspect.signature(pp.propose_pairs).parameters
    c = inspect.signature(pp.mirror_pairs).parameters
    assert {"nodes", "orients"} <= set(b) and {"nodes", "orients"} <= set(c)
```

- [ ] **Step 2: Run and watch them fail.** Expected: `AttributeError: ... 'propose_pairs'`.

- [ ] **Step 3: Implement**, reusing `_leaf_ids` and validating every returned pair against the same rules `tree_contract` applies to `symmetric_pairs` — both ids are leaves, no self-pair, no leaf twice. A reply failing validation returns `[]` (an opinion of "no pairs"); a reply that will not parse returns `None` (no opinion). Record the sent prompt on the client as `last_prompt` for the coordinate test.

- [ ] **Step 4: Run the tests.** Expected: PASS.

- [ ] **Step 5: Mutation-verify** the non-leaf rejection and the duplicate-leaf rejection; each must redden its own test. Restore.

- [ ] **Step 6: Commit**

---

## Task 4: The bar — G1 through G4

**Files:** Modify `mcp_harness/probe_u5prime.py`; create `mcp_harness/tests/test_u5prime_bar.py`

- [ ] **Step 1: Write `verdict()` and its tests FIRST, before any arm-B numbers exist**

```python
BAR = ("G1 arm B must beat BOTH arm A and arm C. "
       "G2 stub_flaps must not rise on any subject (terminal). "
       "G3 leaf count must not move at all -- any change VOIDS the run. "
       "G4 net >= +3 of the subjects gain a correct pair, judged against the "
       "mesh's own leaf positions, never against anatomy_reference.json.")
```

`verdict(rows) -> str` returning `SHIP U5'` or a `DO NOT SHIP (Gn: ...)` / `VOID (G3: ...)` string.

Tests must cover, each mutation-verified: a clean ship; arm B tying arm C (→ do not ship); `stub_flaps` rising (→ terminal); leaf count moving (→ **VOID**, distinct from failed); net gain below 3 (→ do not ship); an errored arm not silently counting as a pass.

- [ ] **Step 2: Mutation-verify `verdict()` in both directions** — force `SHIP` and force `DO NOT SHIP`, confirm each reddens a different set of tests, restore.

- [ ] **Step 3: Get explicit authorization, then run all three arms**

This spends billed calls. **Ask before running.** Budget: ≤ 60 calls, hard abort.

- [ ] **Step 4: Commit the fixture and the verdict**

- [ ] **Step 5: STOP and report**

If the verdict is `DO NOT SHIP`, **do not wire `propose_pairs` into anything.** Report the numbers and let the project owner decide, exactly as M3 and M4 were handled: the verdict stands, and the bar is not re-scored to match it.

---

## Scope note — U7 is deliberately absent

The spec's bar states U5′ and U7 **fail independently** and that U5′ runs first
because it costs zero billed calls until Task 4. U7 needs its own plan, and it
should not be written until this one returns a verdict: if arm C wins Task 2,
the producer story is over and a critic for it is moot.

## Done criteria

- [ ] `mirror_pairs` is deterministic and order-independent, mutation-verified.
- [ ] Arm C was measured and reported **before** any billed call.
- [ ] `propose_pairs` returns `None` with no client and never emits a pair naming a non-leaf or reusing a leaf — both mutation-verified.
- [ ] No coordinate, voxel resolution or prune fraction appears in the model's prompt, pinned by test.
- [ ] Leaf count is identical across all three arms on every subject; otherwise the run is recorded **VOID**.
- [ ] `vlm_judge.py`, `order_rank.py` and `_serve_rank` are byte-unchanged; `MIN_LEAVES, MAX_LEAVES` unchanged.
- [ ] Nothing U5′ produces reaches `_serve_rank` key 1.
- [ ] A handoff records the verdict and arm C's numbers, because a future reader will otherwise assume the LLM was the only way to get pairs.

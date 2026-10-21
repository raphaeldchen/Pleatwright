# Base inspection follow-ups: real `locs`/`scale`, and a tripwire that trips

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the parent serve path emit the packed leaf locations and the real
packing scale, so `read_base()` measures invented flaps instead of proxying them
— then deliberately drive a serve that moves a leaf path, so `[FIDELITY]` is
observed firing rather than merely proven correct.

**Architecture:** `_worker_full_base` already computes `scale` into a local and
holds `engine` at the moment it returns; it just discards both and puts a bare
fold string. The ladder worker's `_try_once` two hundred lines away already does
the right thing. Task 1 makes the parent path emit the same shape, threading it
through the one closure and the two `_record_serve` call sites that currently
omit it. Task 2 retires the `rung.stubs` proxy to a fallback. Task 3 is an
evidence probe, not a feature.

**Tech Stack:** Python 3.14 (`mcp_harness/.venv/bin/python`), pytest, pybind11
extension `headless_treemaker`, multiprocessing `spawn` context.

## Global Constraints

- Python is `mcp_harness/.venv/bin/python`. Run pytest as
  `.venv/bin/python -m pytest tests/ --timeout=420 -q` from `mcp_harness/`.
  Bare `make test` never terminates on macOS.
- **Verify the `.so` is newer than the newest `.cpp` before trusting any run.**
  Worktrees symlink main's binary by default; main's was a week stale as of
  2026-08-05. Rebuild with `PYTHON=$PWD/.venv/bin/python ./build.sh`, and delete
  a symlinked `.so` first so the build does not overwrite the shared binary.
- **Do not cite a test or a measurement as existing without a grep hit taken at
  citation time.** `test_attempt0_unchanged` propagated through four planning
  documents as an existing byte-identity guard and was never implemented.
- **A count-based test is not a pin of wiring.** Assert against the real
  production call site; §6.18 stayed green when the production call was gutted.
- **A scorecard re-bless without attribution absorbs regressions.** Any moved row
  must name which change moved it and why.
- Baseline at plan time: `mcp_harness/tests/` = **2353 passed, 11 skipped, 0
  failed** at `58d2acd` with a freshly built extension.
- `_run_isolated` returns the worker's `ok` payload verbatim, or
  `f"ERROR: {payload}"`. Every decoder distinguishes on the `ERROR:` prefix.

---

### Task 1: Emit `locs` and `scale` from the parent serve path

**Files:**
- Modify: `mcp_harness/server.py:158-193` (`_worker_full_base`)
- Modify: `mcp_harness/server.py:1461` (`_compile_with_perturb` signature)
- Modify: `mcp_harness/server.py:1492`, `:1560` (the two `_record_serve` calls)
- Modify: `mcp_harness/server.py:1696-1705` (the `attempt` closure in
  `draft_and_compile_full_base`)
- Test: `mcp_harness/tests/test_read_base.py`

**Interfaces:**
- Consumes: `_record_serve(requested, served, rung, locs=None, scale=None)`
  (`server.py:1405`) — already accepts both; nothing to change there.
- Produces: `_worker_full_base` puts `("ok", json.dumps({"fold": str,
  "scale": float|None, "locs": list[[int, float, float]]}))`.
  `_compile_with_perturb(nodes, attempt, pairs=None, meta_sink=None)` — when
  `meta_sink` is a dict, it is populated with `{"locs", "scale"}` from the
  winning attempt before `_record_serve` is called.

- [ ] **Step 1: Write the failing test**

Add to `mcp_harness/tests/test_read_base.py`:

```python
def test_parent_path_records_real_locs_and_scale(tmp_path):
    """The PARENT path (draft_and_compile_full_base) must record packed leaf
    locations and the real packing scale -- not None.

    Watches the REAL production call site: it calls the shipped MCP tool and
    reads the module's own _LAST_SERVE, rather than asserting on a count or on
    a hand-built record.
    """
    import json
    import server

    nodes = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.5},
        {"id": 2, "parent_id": 0, "length": 0.5},
        {"id": 3, "parent_id": 0, "length": 0.5},
        {"id": 4, "parent_id": 0, "length": 0.5},
    ]
    out = server.draft_and_compile_full_base(nodes)
    assert not out.startswith("ERROR:"), out

    rec = server._LAST_SERVE
    assert rec.get("ok") is True
    assert rec.get("scale") is not None, "parent path recorded scale=None"
    assert isinstance(rec.get("scale"), float)
    assert rec.get("scale") > 0.0
    locs = rec.get("locs")
    assert locs is not None, "parent path recorded locs=None"
    assert len(locs) >= 4, f"expected >=4 leaf locations, got {locs}"
    for row in locs:
        assert len(row) == 3, f"loc row is (json_id, x, y), got {row}"
```

- [ ] **Step 2: Run it and confirm it fails**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py::test_parent_path_records_real_locs_and_scale -v --timeout=420
```

Expected: FAIL — `AssertionError: parent path recorded scale=None`.

- [ ] **Step 3: Make the worker emit the richer payload**

In `mcp_harness/server.py`, in `_worker_full_base`, replace:

```python
        stage = "molecule"
        queue.put(("ok", engine.build_and_export()))
```

with:

```python
        stage = "molecule"
        fold = engine.build_and_export()
        # Mirrors _run_ladder_child's _try_once, which has emitted exactly this
        # since S2. The parent path computed `scale` above and holds `engine`
        # here; it simply discarded both. `regions` is deliberately NOT included
        # -- nothing on this path consumes it, and the ladder computes its own.
        locs = [list(row) for row in engine.leaf_node_locations()]
        queue.put(("ok", json.dumps(
            {"fold": fold, "scale": scale, "locs": locs})))
```

- [ ] **Step 4: Decode it in the closure and thread it to the record**

In `draft_and_compile_full_base`, replace the `attempt` closure:

```python
    def attempt(nodes: list[dict], stubs: int = 0) -> str:
        return _run_isolated(
            _worker_full_base,
            json.dumps(nodes),
            pairs,
            paper_width,
            paper_height,
            stubs,
        )

    return _compile_with_perturb(tree_nodes, attempt, pairs)
```

with:

```python
    # Filled by the WINNING attempt and read by _compile_with_perturb just
    # before it records the serve. A dict rather than a return-shape change
    # because `attempt` returns a fold string by contract at 31 call sites.
    meta_sink: dict = {}

    def attempt(nodes: list[dict], stubs: int = 0) -> str:
        out = _run_isolated(
            _worker_full_base,
            json.dumps(nodes),
            pairs,
            paper_width,
            paper_height,
            stubs,
        )
        if out.startswith("ERROR:"):
            return out
        payload = json.loads(out)
        meta_sink["locs"] = payload.get("locs")
        meta_sink["scale"] = payload.get("scale")
        return payload["fold"]

    return _compile_with_perturb(tree_nodes, attempt, pairs,
                                 meta_sink=meta_sink)
```

- [ ] **Step 5: Widen `_compile_with_perturb` and pass the values through**

Change the signature at `server.py:1461`:

```python
def _compile_with_perturb(nodes: list[dict], attempt, pairs=None,
                          meta_sink=None) -> str:
```

Append to its docstring:

```
    `meta_sink` (optional dict) carries per-attempt measurements OUT of the
    closure -- packed leaf locations and the real packing scale. Only the
    parent path supplies one; the ladder path already returns them through its
    own queue payload, and the recipe path has no engine to read. Absent, every
    call site behaves exactly as before.
```

Then at both `_record_serve` call sites, pass them through. Replace
`server.py:1492`:

```python
        _record_serve(nodes, nodes, None)
```

with:

```python
        _record_serve(nodes, nodes, None,
                      locs=(meta_sink or {}).get("locs"),
                      scale=(meta_sink or {}).get("scale"))
```

and replace `server.py:1560`:

```python
        _record_serve(nodes, served_candidate, rung)
```

with:

```python
        _record_serve(nodes, served_candidate, rung,
                      locs=(meta_sink or {}).get("locs"),
                      scale=(meta_sink or {}).get("scale"))
```

- [ ] **Step 6: Run the new test and confirm it passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py -v --timeout=420
```

Expected: PASS, including the pre-existing tests in that file.

- [ ] **Step 7: Run the two suites that touch these workers**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_stub_stage.py tests/test_agent_contract_prompt.py -v --timeout=420
```

Expected: PASS. Both introspect `_worker_full_base` — `test_stub_stage.py:542`
and `:604` iterate over it and `test_agent_contract_prompt.py:343` reads its
source asserting `scale` is assigned only on the successful path. Neither
assertion is invalidated by this change; if either fails, the change went
further than intended — stop and report rather than editing the test.

- [ ] **Step 8: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_read_base.py
git commit -m "feat(read-base): emit locs and scale from the parent serve path

_worker_full_base computed the packing scale into a local and held the engine
at the moment it returned, then discarded both and put a bare fold string --
so read_base() reported scale=None on every parent-path serve and could not
measure invented flaps at all. The ladder worker's _try_once has emitted
exactly this payload since S2; this adopts the same shape.

Threaded through a meta_sink dict rather than by changing attempt()'s return
type, because 'attempt returns a fold string' is a contract at 31 call sites."
```

---

### Task 2: Retire the `rung.stubs` proxy to a fallback

**Files:**
- Modify: `mcp_harness/server.py:2367-2377` (the proxy block in `read_base`)
- Test: `mcp_harness/tests/test_read_base.py`

**Interfaces:**
- Consumes: `shadow_tree.shadow_diff(requested, served, locs=...)`
  (`shadow_tree.py:164`) — returns `invented` as a measured int when `locs` is
  given, `None` when it is not.
- Produces: `read_base()`'s payload gains `invented_source` values `"locs"`
  (measured) or `"rung.stubs"` (proxied). No other key changes.

- [ ] **Step 1: Write the failing test**

Add to `mcp_harness/tests/test_read_base.py`:

```python
def test_invented_is_measured_not_proxied_on_parent_path():
    """With real locs, `invented` comes from the json_id == -1 convention, and
    read_base says so. The rung.stubs proxy survives only as a fallback for
    records that genuinely have no locs."""
    import json
    import server

    nodes = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.5},
        {"id": 2, "parent_id": 0, "length": 0.5},
        {"id": 3, "parent_id": 0, "length": 0.5},
        {"id": 4, "parent_id": 0, "length": 0.5},
    ]
    out = server.draft_and_compile_full_base(nodes)
    assert not out.startswith("ERROR:"), out

    rb = json.loads(server.read_base())
    assert rb["status"] == "ok", rb
    assert rb["invented"] is not None
    assert rb.get("invented_source") == "locs", (
        f"expected a measured count, got {rb.get('invented_source')!r}")


def test_invented_falls_back_to_rung_stubs_without_locs():
    """A record with no locs still reports a count, tagged as a proxy."""
    import json
    import server

    server._LAST_SERVE.clear()
    server._LAST_SERVE.update({
        "ok": True, "serve_id": 1,
        "requested": [{"id": 0, "parent_id": None, "length": 0.0},
                      {"id": 1, "parent_id": 0, "length": 0.5}],
        "served": [{"id": 0, "parent_id": None, "length": 0.0},
                   {"id": 1, "parent_id": 0, "length": 0.5}],
        "stage": "stub", "stubs": 2, "invents_anatomy": True,
        "locs": None, "scale": None,
    })
    rb = json.loads(server.read_base())
    assert rb["invented"] == 2
    assert rb["invented_source"] == "rung.stubs"
```

- [ ] **Step 2: Run and confirm the first fails, the second passes**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py -k "invented" -v --timeout=420
```

Expected: `test_invented_is_measured_not_proxied_on_parent_path` FAILS with
`expected a measured count, got 'rung.stubs'` — because Task 1 supplies locs but
nothing yet tags the measured case. The fallback test PASSES already.

- [ ] **Step 3: Tag the measured case**

In `read_base` (`server.py`, the block beginning `# THE PARENT PATH HAS NO
locs.`), replace:

```python
    # THE PARENT PATH HAS NO `locs`. _worker_full_base returns a fold string
    # and nothing else, so shadow_diff correctly reports invented=None there --
    # "not measured", never a false 0. But the count IS known by another route:
    # the rung's stub budget is exactly how many flaps the engine was permitted
    # to invent, and STAGE_STUB is the only stage in INVENTS_ANATOMY. Fill it
    # in rather than shipping a permanent None on the serve path.
    if diff.get("invented") is None and rec.get("stubs") is not None:
        diff["invented"] = int(rec["stubs"])
        diff["invented_source"] = "rung.stubs"
```

with:

```python
    # `invented` is MEASURED when locs reached us -- a stub flap is structurally
    # absent from any Python node list and surfaces only under the json_id == -1
    # convention (server.py:415). Both serve paths now supply locs, so the
    # proxy below is a fallback, not the normal case.
    if diff.get("invented") is not None:
        diff["invented_source"] = "locs"
    elif rec.get("stubs") is not None:
        # No locs: the rung's stub budget is exactly how many flaps the engine
        # was PERMITTED to invent, and STAGE_STUB is the only stage in
        # INVENTS_ANATOMY. An upper bound, tagged as such -- never a false 0.
        diff["invented"] = int(rec["stubs"])
        diff["invented_source"] = "rung.stubs"
```

- [ ] **Step 4: Run and confirm both pass**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_read_base.py -k "invented" -v --timeout=420
```

Expected: PASS, PASS.

- [ ] **Step 5: Commit**

```bash
git add mcp_harness/server.py mcp_harness/tests/test_read_base.py
git commit -m "feat(read-base): measure invented flaps, keep rung.stubs as fallback

With locs on both serve paths, invented comes from the json_id == -1 convention
rather than the rung's stub BUDGET -- which was only ever an upper bound on what
the engine was permitted to invent, not a count of what it did. invented_source
now distinguishes the two so a proxied number is never read as a measured one."
```

---

### Task 3: Make the tripwire trip

**Files:**
- Create: `docs/superpowers/evidence/2026-08-05-fidelity-fires/probe_jitter_drift.py`
- Create: `docs/superpowers/evidence/2026-08-05-fidelity-fires/README.md`
- Test: `mcp_harness/tests/test_fidelity_oracle.py`

**Interfaces:**
- Consumes: `fidelity_oracle.decide(*, base_report, reparent_reported=False)`
  (`fidelity_oracle.py:66`), which reads
  `drift = float(diff.get("path_drift_max") or 0.0)` at `:88`.
- Consumes: `shadow_tree.shadow_diff` (`shadow_tree.py:164`), whose
  `path_drift_max` is `max |served_path - requested_path| / span` over leaf
  pairs present in both trees (`:190-193`).
- Produces: no code artifact other than the test and the probe. This task
  produces **evidence**.

**Why this task exists.** `path_drift_max` read 0.0 on all five scorecard
subjects and `[FIDELITY]` fired on none. That is not a bug: the stages those
subjects reached — `STAGE_STUB`, `STAGE_PLACEMENT`, `STAGE_ORDER`
(`rescue_ladder.py:56-61`) — mathematically cannot move a leaf-to-leaf path.
`STAGE_ORDER` and `STAGE_PLACEMENT` are proportion-preserving; `STAGE_STUB`
adds a flap the engine invents without moving a requested length. Only
`STAGE_JITTER`, `STAGE_COMPOSED` (lengths moved) and `STAGE_NORMALIZE` (graph
restructured) can. **No subject in the corpus reaches one.** So the instrument
is correct by construction and unobserved in production — and this repo has a
recorded case of a gate staying green while its production call site was gutted.

- [ ] **Step 1: Write the failing test**

Add to `mcp_harness/tests/test_fidelity_oracle.py`:

```python
def test_fidelity_fires_on_a_jittered_serve():
    """A serve whose lengths were nudged MUST move path_drift_max off 0.0 and
    MUST make the oracle fire. Guards against the instrument being permanently
    silent: every scorecard subject reaches a stage that cannot move a path,
    so without this test nothing anywhere exercises the firing branch.
    """
    import fidelity_oracle
    import shadow_tree

    requested = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.50},
        {"id": 2, "parent_id": 0, "length": 0.50},
        {"id": 3, "parent_id": 0, "length": 0.50},
    ]
    # What a jitter rung produces: same graph, lengths nudged off the request.
    served = [
        {"id": 0, "parent_id": None, "length": 0.0},
        {"id": 1, "parent_id": 0, "length": 0.44},
        {"id": 2, "parent_id": 0, "length": 0.50},
        {"id": 3, "parent_id": 0, "length": 0.50},
    ]
    diff = shadow_tree.shadow_diff(requested, served, locs=[])
    assert diff["path_drift_max"] > 0.0, (
        f"a jittered serve read 0.0 drift: {diff}")
    assert diff["comparable"] is True

    report = {"status": "ok", "stage": "jitter", "stubs": 0,
              "invents_anatomy": False, **diff}
    verdict = fidelity_oracle.decide(base_report=report)
    assert verdict["fire"] is True, (
        f"oracle stood down on real drift: {verdict}")
```

- [ ] **Step 2: Run it**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m pytest tests/test_fidelity_oracle.py::test_fidelity_fires_on_a_jittered_serve -v --timeout=420
```

Expected: this **may already pass** — the unit is believed correct. If it
passes, that is the intended outcome and the test is a regression pin. If it
fails, read `fidelity_oracle.decide`'s stand-down reasons (`decide()` always
returns why) and report before changing any threshold. Do not tune a constant
to make it fire.

- [ ] **Step 3: Write the end-to-end probe**

Create `docs/superpowers/evidence/2026-08-05-fidelity-fires/probe_jitter_drift.py`:

```python
"""Drive a serve that ACTUALLY reaches a jitter rung, and record what
read_base() and [FIDELITY] say about it.

The unit test proves the arithmetic. This proves the WIRING: that a real
compile, through the real serve path, reaches a length-moving stage and that
the oracle sees it. Run from mcp_harness/:

    PYTHONPATH=.:tests .venv/bin/python \\
        ../docs/superpowers/evidence/2026-08-05-fidelity-fires/probe_jitter_drift.py
"""
import json
import os
import sys

HERE = os.environ.get("IDE_HARNESS") or os.getcwd()
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tests"))

import fidelity_oracle          # noqa: E402
import server                   # noqa: E402


#: Trees chosen to be tight enough that attempt-0 and the proportion-preserving
#: rungs fail, forcing the ladder down to a length-moving rung. Widen this list
#: until at least one lands on jitter/composed/normalize.
CANDIDATES = {
    "star6_tight": [{"id": 0, "parent_id": None, "length": 0.0}] +
                   [{"id": i, "parent_id": 0, "length": 0.62}
                    for i in range(1, 7)],
    "star7_tight": [{"id": 0, "parent_id": None, "length": 0.0}] +
                   [{"id": i, "parent_id": 0, "length": 0.58}
                    for i in range(1, 8)],
    "star8_tight": [{"id": 0, "parent_id": None, "length": 0.0}] +
                   [{"id": i, "parent_id": 0, "length": 0.55}
                    for i in range(1, 9)],
}

MOVES_A_PATH = {"jitter", "composed", "normalize"}


def main():
    rows = []
    for name, nodes in CANDIDATES.items():
        out = server.draft_and_compile_full_base(nodes)
        served = not out.startswith("ERROR:")
        rb = json.loads(server.read_base()) if served else {}
        stage = rb.get("stage")
        verdict = (fidelity_oracle.decide(base_report=rb)
                   if rb.get("status") == "ok" else {})
        rows.append({
            "subject": name,
            "served": served,
            "stage": stage,
            "can_move_a_path": stage in MOVES_A_PATH,
            "path_drift_max": rb.get("path_drift_max"),
            "invented": rb.get("invented"),
            "invented_source": rb.get("invented_source"),
            "scale": rb.get("scale"),
            "fidelity_fired": verdict.get("fire"),
            "fidelity_reason": verdict.get("reason"),
        })
        print(json.dumps(rows[-1], indent=2), flush=True)

    hit = [r for r in rows if r["can_move_a_path"]]
    print(f"\n=== {len(hit)}/{len(rows)} reached a path-moving stage ===")
    if not hit:
        print("NO SUBJECT REACHED jitter/composed/normalize. The tripwire "
              "remains unobserved -- widen CANDIDATES or report this as the "
              "finding. Do NOT weaken the oracle to manufacture a firing.")


if __name__ == "__main__":       # spawns workers -- the guard is mandatory
    main()
```

- [ ] **Step 4: Run the probe and capture its output**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -u \
  ../docs/superpowers/evidence/2026-08-05-fidelity-fires/probe_jitter_drift.py \
  > ../docs/superpowers/evidence/2026-08-05-fidelity-fires/out_jitter_drift.txt 2>&1
tail -20 ../docs/superpowers/evidence/2026-08-05-fidelity-fires/out_jitter_drift.txt
```

Two legitimate outcomes, and **both are results**:
- At least one subject reaches `jitter`/`composed`/`normalize` with
  `path_drift_max > 0` and `fidelity_fired: true`. The tripwire is observed.
- No subject reaches one. Then the honest finding is that the corpus cannot
  exercise the instrument, and that goes in the README verbatim. **Do not lower
  a threshold to force a firing.**

- [ ] **Step 5: Write the evidence README**

Create `docs/superpowers/evidence/2026-08-05-fidelity-fires/README.md` with: the
question (does `[FIDELITY]` ever fire in production?), the table of measured
rows from step 4, which stages each subject reached, and an explicit statement
of which of the two outcomes occurred. If no subject reached a path-moving
stage, say so as the headline finding.

- [ ] **Step 6: Commit**

```bash
git add mcp_harness/tests/test_fidelity_oracle.py \
        docs/superpowers/evidence/2026-08-05-fidelity-fires/
git commit -m "test(fidelity): exercise the tripwire, and record whether it trips

path_drift_max read 0.0 on all five scorecard subjects and the oracle fired on
none -- not a bug, because stub/placement/order provably cannot move a
leaf-to-leaf path. Only jitter/composed/normalize can, and no subject reaches
one. The unit test pins the firing branch; the probe asks whether any real
compile reaches a stage that would trip it."
```

---

### Task 4: Re-run the gate and attribute anything that moved

**Files:**
- Modify (only if rows move): `mcp_harness/fixtures/scorecard_baseline.jsonl`

- [ ] **Step 1: Confirm the extension is current**

```bash
cd mcp_harness && ls -la headless_treemaker*.so && \
  git log -1 --format='%ad %s' --date=iso -- '*.cpp' '*.h'
```

If the `.so` predates the newest `.cpp`, rebuild first: delete it if it is a
symlink, then `PYTHON=$PWD/.venv/bin/python ./build.sh`.

- [ ] **Step 2: Run the full suite**

```bash
cd mcp_harness && .venv/bin/python -u -m pytest tests/ --timeout=420 -q \
  > /tmp/followup_tests.log 2>&1; tail -3 /tmp/followup_tests.log
```

Expected: **2355 passed** (2353 baseline + the two new tests in Tasks 1–2, plus
Task 3's), 11 skipped, 0 failed. Any failure is a real finding — report it
rather than adjusting the test.

- [ ] **Step 3: Check whether any scorecard row moved**

```bash
cd mcp_harness && PYTHONPATH=.:tests .venv/bin/python -m benchmark_subjects \
  --baseline fixtures/scorecard_baseline.jsonl
```

`scale` becoming non-null and `invented_source` becoming `"locs"` are the
*intended* movements. Anything else — a changed `rescue_stage`,
`served_fidelity`, or `stub_flaps` — means this change altered a serve, which it
must not. Stop and report.

- [ ] **Step 4: Re-bless only with attribution**

If and only if rows moved for the intended reasons, re-bless and record in the
fixture's `_meta` **which change moved which axis and why** — a re-bless without
attribution absorbs regressions, which is how the quadruped `jitter -> stub`
(+3 invented flaps) regression reached a committed baseline unnoticed.

- [ ] **Step 5: Commit**

```bash
git add -A mcp_harness/fixtures/scorecard_baseline.jsonl
git commit -m "test(scorecard): re-bless for real scale and measured invented

Attributed: scale moves null -> float because the parent path now emits it;
invented_source moves rung.stubs -> locs because it is now measured rather than
proxied off the rung's stub budget. No serve changed: rescue_stage,
served_fidelity and stub_flaps are unmoved on every row."
```

---

## Self-review

**Spec coverage.** This plan implements follow-ups 1 and 2 from PR #75's report
and the base-inspection spec's §I. Follow-up 3 ("decide the packing diagram:
fair trial or delete") is **deliberately not planned here** — it depends on
Task 1's output existing first, and deciding it now would be guessing.

**Known gap, stated rather than hidden.** Task 1 does not give the *recipe* path
(`_worker_compile_recipe`, `server.py:197`) locs or scale. That path rebuilds an
engine from a serialized recipe and is used by the incremental session
(`new_base`/`compile_base`), not by `draft_and_compile_full_base`. Extending it
is a separate change with its own call sites; `read_base()` correctly reports
`invented=None` there, and the fallback in Task 2 covers it.

**Type consistency.** `locs` is `list[list[int, float, float]]` everywhere:
`leaf_node_locations()` returns tuples, `_worker_full_base` converts to lists for
JSON, `_record_serve` stores `list(locs)`, `shadow_diff` reads `int(row[0])`.
`scale` is `float | None` throughout.

**Risk not mitigated by any task.** `packing_diagram` computes
`r = box * float(scale) * length` (`tree_render.py:158`) with `scale=1.0` by
default. Once a real scale reaches it, rendered radii change. No caller is
updated here because no caller currently passes the served scale — that is
follow-up 3's business. Flagged so it is not discovered as a surprise.

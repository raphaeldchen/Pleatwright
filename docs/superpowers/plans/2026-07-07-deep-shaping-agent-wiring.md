# Deep-Shaping Agent Wiring (reverse_deep + sink) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the slice-3/4 deep primitives (`reverse_deep`, `sink`) to the agent by extending the `apply_shaping_ops` MCP tool and the SYSTEM_PROMPT shaping vocabulary.

**Architecture:** Two new target kinds in `server.py apply_shaping_ops` dispatch `shaping_deep.reverse_deep` (sink at pinned θ=180), enforcing the deep-first ordering rule that `shaping.apply_display_ops` already pins. Recorded op strings are byte-compatible with `parse_op`, so the display boundary (`web/server.py`, which already passes `raw`) replays them with **zero web-tier changes**. A compact SYSTEM_PROMPT addition teaches the vocabulary.

**Tech Stack:** Python (mcp_harness), pytest. Spec: `docs/superpowers/specs/2026-07-07-deep-shaping-agent-wiring-design.md`.

## Global Constraints

- **Measure-then-pin:** never pin a test value not first printed by a committed probe and checked against hand reasoning. Task 1's probe measures which star-4 deep params apply BEFORE Task 2 pins them.
- **Provenance contract:** `web/server.py` is NOT modified. The raw `json` frame is untouched; ops ride `display_json`.
- **Groq TPM ceiling:** the prompt addition stays compact (one short passage); no new MCP tools, no tool-schema growth beyond the docstring.
- **Suite:** `cd mcp_harness && .venv/bin/python -m pytest tests -q` must stay green (~396 passed / 3 skipped at slice 4). Tool tests spawn real compiles (~5–20 s each) — batch targets per test, as the existing tests do.
- All commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Working dir for all commands: `<repo>/mcp_harness` unless stated.

---

### Task 1: Branch + probe the deep params through the real tool path

**Files:**
- Create: `mcp_harness/probe_deep_tool.py`

**Interfaces:**
- Produces: the measured `(node_id, fraction, theta)` combos on star-4 for which `reverse_deep`/sink APPLY via the tool's exact compile→square→dispatch path, plus at least one naturally-refusing combo (if any exists) with its reason. Task 2 pins ONLY combos this probe printed as applied.

- [ ] **Step 1: Create the feature branch off main**

Local `main` is ahead of `origin/main` by doc-only commits (this cycle's specs + plan); they ride into this PR like prior slices' docs.

```bash
cd <repo>
git checkout -b feat/deep-shaping-agent-wiring main
```

Expected: `Switched to a new branch 'feat/deep-shaping-agent-wiring'`.

- [ ] **Step 2: Write the probe**

Create `mcp_harness/probe_deep_tool.py`. It mirrors `apply_shaping_ops`' internals exactly (same worker, same squaring, same `d = fraction * axial_length`) WITHOUT the tool, because the tool's deep dispatch does not exist yet:

```python
"""Probe (agent-wiring mini-PR): which deep params apply on star-4 via the
tool path?

apply_shaping_ops is about to grow "reverse_deep"/"sink" kinds. Before any
test pins params, this probe compiles star-4 through the SAME worker the
tool uses, squares it the same way, and tries reverse_deep on every leaf
at candidate (fraction, theta) combos, printing applied/refused per combo.

Run: cd mcp_harness && .venv/bin/python probe_deep_tool.py
"""
import json
import sys

sys.path.insert(0, "tests")
from cases import CASES_BY_NAME    # noqa: E402
import server                      # noqa: E402
import shaping                     # noqa: E402
import shaping_deep                # noqa: E402
import square_complete             # noqa: E402


def main():
    nodes, pairs = CASES_BY_NAME["star-4"]
    raw = server._run_isolated(
        server._worker_compile_and_regions, json.dumps(nodes),
        [list(p) for p in pairs], 1.0, 1.0)
    base = json.loads(raw)
    fold = base["fold"]
    if isinstance(fold, str):
        fold = json.loads(fold)
    locs = {int(n): (x, y) for n, x, y in base.get("locs", [])}
    squared = square_complete.complete_square(fold, 1.0, 1.0)
    print(f"star-4 leaves: {sorted(locs)}")

    for nid in sorted(locs):
        x, y = locs[nid]
        for fraction in (0.25, 0.5, 0.75):
            for theta in (120.0, 180.0):
                d = fraction * shaping.axial_length(squared, (x, y))
                try:
                    out = shaping_deep.reverse_deep(
                        squared, fold, (x, y), d, theta)
                    delta = (len(out["edges_vertices"])
                             - len(squared["edges_vertices"]))
                    print(f"node {nid} f={fraction} th={theta}: "
                          f"APPLIED (+{delta} edges)")
                except shaping.ShapingError as exc:
                    print(f"node {nid} f={fraction} th={theta}: "
                          f"refused: {exc}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Run the probe and record its output**

```bash
cd <repo>/mcp_harness
.venv/bin/python probe_deep_tool.py
```

Expected (from slice-3 evidence: star-4 f=0.5 θ=180 applies at a tip; the
squared star-4 == raw): at least one `APPLIED` line per leaf at f=0.5.
Record the full output — Task 2's test params come ONLY from `APPLIED`
lines here, and Task 2's refusal test (if written) uses a `refused` line's
reason verbatim. Sanity-check by hand: applied combos must be interior
fold points (0 < f < 1) and θ in (0, 180].

**If NO combo applies:** stop, report the printed output to the human —
the spec's assumption fails and the tests need rethinking. Do not force it.

- [ ] **Step 4: Commit**

```bash
cd <repo>
git add mcp_harness/probe_deep_tool.py
git commit -m "probe(deep-wiring): measure star-4 deep params via the tool path

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Tool — `reverse_deep` + `sink` kinds in `apply_shaping_ops`

**Files:**
- Modify: `mcp_harness/server.py:617-676` (the target loop in `apply_shaping_ops`) and its docstring (`:560-585`)
- Test: `mcp_harness/tests/test_shaping_tool.py`

**Interfaces:**
- Consumes: Task 1's measured applied combos. The code below assumes `node_id=1, fraction=0.5, theta=120` and `node_id=2, fraction=0.5` (sink) applied — **replace with probe-printed values if they differ.**
- Produces: `apply_shaping_ops` accepting `kind="reverse_deep"` (`fraction`, `theta`) and `kind="sink"` (`fraction` only), emitting op strings `reverse_deep:{x},{y}:{d}:{theta}` / `sink:{x},{y}:{d}`; a deep target anywhere but position 0 is refused with a reason containing `"FIRST"`.

- [ ] **Step 1: Write the failing tests**

Append to `mcp_harness/tests/test_shaping_tool.py`:

```python
def test_deep_kinds_apply_and_replay_at_display():
    # ONE compile: reverse_deep FIRST (deep-first rule), then a tip-local
    # reverse on another leaf. Params probe-verified 2026-07-07 by
    # probe_deep_tool.py (adjust to its APPLIED lines if they differ).
    out = _run([
        {"node_id": 1, "kind": "reverse_deep", "fraction": 0.5,
         "theta": 120},
        {"node_id": 2, "fraction": 0.25, "theta": 90},
    ])
    assert out["status"] == "shaped"
    assert [v["status"] for v in out["verdicts"]] == ["applied", "applied"]
    assert out["ide_shape_ops"][0].startswith("reverse_deep:")
    assert out["ide_shape_ops"][1].startswith("reverse:")
    for op in out["ide_shape_ops"]:
        shaping.parse_op(op)                      # grammar round-trips
    # display-replay: deep ops need raw -- exactly what web/server.py passes
    squared = square_complete.complete_square(out["fold"], 1.0, 1.0)
    shaped = shaping.apply_display_ops(squared, out["ide_shape_ops"],
                                       raw=out["fold"])
    assert len(shaped["edges_vertices"]) > len(squared["edges_vertices"])
    assert len(shaped["edges_foldAngle"]) == len(shaped["edges_vertices"])


def test_sink_needs_no_theta_and_deep_first_is_enforced():
    # ONE compile: sink without theta applies (position 0); a SECOND deep
    # target is refused (only one, FIRST); a tip-local target still applies
    # after the refusal (refusal never aborts the batch).
    out = _run([
        {"node_id": 2, "kind": "sink", "fraction": 0.5},
        {"node_id": 1, "kind": "reverse_deep", "fraction": 0.5,
         "theta": 120},
        {"node_id": 3, "fraction": 0.25, "theta": 90},
    ])
    assert [v["status"] for v in out["verdicts"]] == \
        ["applied", "refused", "applied"]
    assert "FIRST" in out["verdicts"][1]["reason"]
    assert out["ide_shape_ops"][0].startswith("sink:")
    assert len(out["ide_shape_ops"][0].split(":")) == 3   # no theta segment
    for op in out["ide_shape_ops"]:
        shaping.parse_op(op)


def test_deep_after_tip_local_is_refused():
    # ONE compile: deep target listed second -> refused even though no
    # other deep target exists (FIRST means literally first).
    out = _run([
        {"node_id": 1, "fraction": 0.25, "theta": 90},
        {"node_id": 2, "kind": "sink", "fraction": 0.5},
    ])
    assert [v["status"] for v in out["verdicts"]] == ["applied", "refused"]
    assert "FIRST" in out["verdicts"][1]["reason"]
    assert len(out["ide_shape_ops"]) == 1


def test_deep_trap_refusal_surfaces_verbatim_and_batch_continues(monkeypatch):
    # star-4 has no natural forced trap (probe-verified), so force one: the
    # contract under test is the tool's refusal plumbing (reason verbatim,
    # batch continues), not the trap geometry (unit-tested in slice 3).
    import shaping_deep

    def trapped(squared, raw, tip_xy, d, theta, gamma=45.0):
        raise shaping.ShapingError(
            "forced layer trap: face 7 is forced strictly between "
            "through-face 1 (above it) and through-face 6 (below it) "
            "-- cannot be creased consistently")

    monkeypatch.setattr(shaping_deep, "reverse_deep", trapped)
    out = _run([
        {"node_id": 1, "kind": "reverse_deep", "fraction": 0.5,
         "theta": 120},
        {"node_id": 2, "fraction": 0.25, "theta": 90},
    ])
    assert [v["status"] for v in out["verdicts"]] == ["refused", "applied"]
    assert "forced layer trap" in out["verdicts"][0]["reason"]
    assert len(out["ide_shape_ops"]) == 1     # only the tip-local reverse
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd <repo>/mcp_harness
.venv/bin/python -m pytest tests/test_shaping_tool.py -q -k "deep or sink"
```

Expected: 4 FAILED — refusal reason `"kind must be reverse, outside, or crimp"` (the whitelist rejects the new kinds; the monkeypatch test fails because the tool never reaches the patched function).

- [ ] **Step 3: Implement the tool changes**

In `mcp_harness/server.py`, inside `apply_shaping_ops`:

**(a)** add the import next to the existing ones (line ~586):

```python
    import shaping
    import shaping_deep
    import square_complete
```

**(b)** change the loop header (line ~617) to track position:

```python
    for idx, t in enumerate(targets or []):
```

**(c)** replace the kind whitelist check:

```python
        if kind not in ("reverse", "outside", "crimp",
                        "reverse_deep", "sink"):
            refuse("kind must be reverse, outside, crimp, reverse_deep, "
                   "or sink")
            continue
        if kind in ("reverse_deep", "sink") and idx > 0:
            refuse("a deep target (reverse_deep/sink) must be the FIRST "
                   "target -- at most one per call, before tip-local ops")
            continue
```

**(d)** in the numeric-parse block, sink pins theta (no key required):

```python
        try:
            fraction = float(t.get("fraction", 0.5))
            fraction2 = float(t.get("fraction2", 0.5))
            theta = 180.0 if kind == "sink" else float(t["theta"])
        except (KeyError, TypeError, ValueError):
            refuse("target needs numeric theta (fraction/fraction2 optional)")
            continue
```

(The existing range checks then hold unchanged: sink's pinned 180 passes
`0 < theta <= 180`; the `outside/crimp`-specific checks don't touch deep
kinds.)

**(e)** in the apply block, add the deep branch before the tip-local `else`:

```python
            elif kind in ("reverse_deep", "sink"):
                # deep runs at idx 0 only, so `current` is still the freshly
                # squared base -- exactly reverse_deep's contract (squared
                # display fold + raw fold, shared CP coordinates).
                d = fraction * shaping.axial_length(current, (x, y))
                current = shaping_deep.reverse_deep(current, fold, (x, y),
                                                    d, theta)
                if kind == "sink":
                    ops.append(f"sink:{x},{y}:{d}")
                else:
                    ops.append(f"reverse_deep:{x},{y}:{d}:{theta}")
```

(`shaping_deep` raises the shared `shaping.ShapingError`, so the existing
`except shaping.ShapingError` refusal path surfaces deep refusals — e.g.
the forced-layer-trap message — verbatim, and a refused deep target never
aborts the batch: nothing was consumed.)

**(f)** docstring: extend the `targets:` kind list with

```
"reverse_deep" (fold THROUGH the flap's stacked layers; tucks between
them) | "sink" (tuck the tip inside -- an open sink; no theta),
```

and append one sentence: `At most one reverse_deep/sink target per call,
and it must be the FIRST target.`

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_shaping_tool.py -q
```

Expected: ALL tests in the file pass (the 3 new + all pre-existing, incl. `test_kinds_batch_outside_crimp_guard_and_unknown`, whose `"kind" in reason` assertion tolerates the extended message).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/server.py mcp_harness/tests/test_shaping_tool.py
git commit -m "feat(deep-wiring): reverse_deep + sink kinds in apply_shaping_ops

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Prompt — deep vocabulary in the SHAPING section

**Files:**
- Modify: `mcp_harness/agent_loop.py:276-283` (the target-kinds passage of the SHAPING section)
- Test: `mcp_harness/tests/test_agent_shaping_prompt.py`

**Interfaces:**
- Consumes: the tool behavior from Task 2 (kinds, deep-first rule, trap refusals).
- Produces: SYSTEM_PROMPT containing the exact pins `'"reverse_deep"'`, `'"sink"'`, `"listed FIRST"`, `"forced layer trap"`, `"do NOT retry with a different theta"`.

- [ ] **Step 1: Write the failing test**

Append to `mcp_harness/tests/test_agent_shaping_prompt.py`:

```python
def test_prompt_teaches_deep_kinds_and_trap_handling():
    for needle in ('"reverse_deep"', '"sink"', "listed FIRST",
                   "forced layer trap",
                   "do NOT retry with a different theta"):
        assert needle in P, f"missing deep-vocabulary pin: {needle}"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
.venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -q
```

Expected: 1 FAILED (`missing deep-vocabulary pin: "reverse_deep"`), 5 passed.

- [ ] **Step 3: Add the prompt passage**

In `mcp_harness/agent_loop.py`, after the crimp sentence (`... (pick e.g. \` / `75 or 105).`) and before `Read the verdicts honestly:`, insert:

```
"reverse_deep" folds the flap THROUGH its stacked layers at the fold point \
(tucks it between layers; plain "reverse" folds around them); "sink" (no \
theta needed) tucks the tip inside the base -- an open sink. At most ONE \
deep target ("reverse_deep"/"sink") per call, and it must be listed FIRST, \
before any tip-local target. A "forced layer trap" refusal is geometric, \
not tunable: report its reason verbatim, then pick a different fraction or \
drop the deep target -- do NOT retry with a different theta. \
```

(Same line-continuation style as the surrounding string; keep it one
compact passage — Groq TPM.)

- [ ] **Step 4: Run tests to verify they pass**

```bash
.venv/bin/python -m pytest tests/test_agent_shaping_prompt.py -q
```

Expected: 6 passed (all existing pins unmodified).

- [ ] **Step 5: Commit**

```bash
cd <repo>
git add mcp_harness/agent_loop.py mcp_harness/tests/test_agent_shaping_prompt.py
git commit -m "feat(deep-wiring): teach the prompt reverse_deep + sink (deep-first, trap not tunable)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Full suite green + wrap-up

**Files:**
- None new (fix-forward only if the suite reddens).

- [ ] **Step 1: Run the full backend suite**

```bash
cd <repo>/mcp_harness
.venv/bin/python -m pytest tests -q
```

Expected: all pass (~396+3 skipped at slice 4, plus the 4 new tests), ~10 min. If anything fails, fix forward and re-run; report failures honestly.

- [ ] **Step 2: Reset local main to origin (the branch carries the doc commits)**

```bash
cd <repo>
git branch -f main origin/main
```

Expected: `main` back at `origin/main` (9a35239); the two spec commits live on `feat/deep-shaping-agent-wiring`.

- [ ] **Step 3: Report to the human**

Summarize: probe output, tests added, suite count. **Do NOT push or open a PR without explicit approval** — the human merges every PR.

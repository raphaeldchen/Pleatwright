# Runtime Capture — Close the Gate Data Loop (Capture Half)

**Date:** 2026-06-24
**Status:** Design approved, pending implementation plan
**Component:** `mcp_harness/server.py`, `mcp_harness/feasibility/capture.py` (new)
**Sub-project:** B of the gate-recalibration effort (A = mesh-region corpus coverage, PR #9). This spec is the CAPTURE half of B only.

## Problem

The Tier 2.5 feasibility gate never improves after first training. Novel (OOD)
trees met at runtime are flagged `compile_anyway` with the reason "compile and
log for retraining" — but **nothing logs them**. Every served compile produces a
real pack/no-pack outcome (exactly the label the corpus needs), and it is thrown
away. Without runtime capture, any later merge/retrain step has no new data to
fold in.

## Goal

Record every served compile — the submitted tree, its real attempt-0 outcome, and
the gate's verdict at that moment — to an append-only `captured.jsonl`, in a form
directly mergeable into the corpus later.

### Non-goals (explicitly out of scope)

- **Merge into the corpus / retrain.** A later effort consumes `captured.jsonl`.
- **Automation (cron / CI eval gate).** Later.
- **Filtering which rows are "useful".** Capture is dumb and faithful: it records
  ALL served compiles, tagged with the gate verdict; the future merge step decides
  what to keep.

## Capture point

Hook inside `server.py::_compile_with_perturb(nodes, attempt)`:

- **Serve-only.** Both serve compile tools route through it
  (`draft_and_compile_full_base` and the incremental `compile_base`), but the
  corpus builder (`tree_labeler`) compiles via `runner.compile_tree` directly and
  never touches `_compile_with_perturb`. So capture records real serve traffic and
  never re-captures the thousands of build compiles — no exclusion flag needed.
- **Attempt-0 label.** Its first line is `result = attempt(nodes)` — the original
  tree, before any perturb jitter. `attempt0_pack = not result.startswith("ERROR:")`
  on that first result is exactly the corpus's `attempt0_pack` semantics (a
  perturb-rescued success would mislabel "this tree packs").
- **One hook, both paths.** One-shot and incremental sessions both funnel through it.

Required change: `_compile_with_perturb` currently receives `nodes` but not `pairs`
(pairs are bound in the `attempt` closure). Thread `pairs` in as a parameter so
capture can record them. Both call sites have pairs available
(`draft_and_compile_full_base` → its `pairs`; `compile_base` → `_SESSION["pairs"]`).

The hook: after the first `attempt(nodes)`, call
`capture.record(nodes, pairs or [], attempt0_pack, result)`. It is a side-channel
that MUST never affect the compile.

## The `capture.py` module

New `mcp_harness/feasibility/capture.py`, one public function:
`record(nodes, pairs, attempt0_pack, result_str)`.

### Gating — env var presence is the switch

Capture is active iff `IDE_CAPTURE_PATH` is set; that variable is BOTH the
on-switch and the destination file path. Unset → `record` is a no-op. Consequences:

- Normal test/CI runs and the corpus builder never capture (nothing to exclude).
- The real MCP server deployment sets `IDE_CAPTURE_PATH=feasibility/captured.jsonl`.
- The capture test sets it to a tmp path.
- `mcp_harness/feasibility/captured.jsonl` is gitignored.

### Defensiveness — capture must never break a serve compile

The entire `record` body is wrapped so any exception (gate missing, disk error,
malformed tree) is swallowed (optional stderr warning), never propagated. A failed
capture silently drops one row; it never fails the user's compile.

### Row schema

Mirrors a corpus row plus serve metadata, so a future merge just dedups + assigns
an id:

```json
{
  "source": "captured",
  "nodes": [...], "pairs": [...],
  "features": { ...ds.extract_features(nodes, pairs)... },
  "attempt0_pack": true,
  "failure_mode": "pack" | "no_pack_ibps" | "not_connectable" | "build_failed" | "crash" | "hang",
  "perturb_pack": null,
  "gate": {"verdict": "...", "p_pack": 0.0, "ood": false, "ood_score": 0.0} | null,
  "ts": "2026-06-24T12:34:56"
}
```

- `failure_mode` reuses `tree_labeler.classify_status` (passing `"ok"`/`"err"` plus
  the result string) so captured rows share the corpus's exact vocabulary — no
  parallel classifier.
- `gate` is recomputed at capture via a cached `feasibility.gate.load` (loaded once,
  module-level). If no artifact exists, `gate = null`; capture does NOT train
  on-demand (too heavy for a side-channel) — it tags only when a gate already
  exists.
- `perturb_pack` is `null` at capture (not measured at serve; a merge step may fill
  it).

### Concurrency

A module-level `threading.Lock` guards the append (auto_mesh and threads can compile
concurrently), so rows never interleave or corrupt.

## Wiring

In `server.py`:
- `_compile_with_perturb(nodes, attempt, pairs=None)` — add the `pairs` parameter;
  pass it from both call sites.
- After the first `result = attempt(nodes)`, call
  `capture.record(nodes, pairs or [], not result.startswith("ERROR:"), result)`.
- Import `capture` at module top.

In `.gitignore`: add `mcp_harness/feasibility/captured.jsonl`.

## Testing

All fast — capture is pure I/O plus a cheap predict; no real compiles needed.

- **No-op when disabled:** `IDE_CAPTURE_PATH` unset → `record(...)` writes nothing,
  returns without error.
- **Writes a corpus-compatible row when enabled:** `IDE_CAPTURE_PATH` → tmp file;
  `record(nodes, pairs, True, fold_str)` appends exactly one JSON line with all
  schema keys; `features == ds.extract_features(nodes, pairs)`; `attempt0_pack`
  true; `source == "captured"`.
- **`failure_mode` matches the corpus vocabulary:**
  `record(..., False, "ERROR: ...POLYS_MULTIPLE_IBPS...")` → `failure_mode ==
  "no_pack_ibps"`; a packed result → `"pack"`.
- **Defensive — never raises:** monkeypatch the gate loader to throw → row still
  written with `gate == null`, no exception escapes; malformed input → swallowed.
- **Concurrency:** fire `record` from several threads at a tmp path → all rows
  present, each a valid standalone JSON line.
- **Serve hook fires, builder does not:** a `_compile_with_perturb` call (with
  `IDE_CAPTURE_PATH` set, `attempt` stubbed to return a FOLD, then an ERROR)
  records the attempt-0 outcome; a `tree_labeler.label` call (using a monkeypatched
  `runner.compile_tree`) records nothing — proving builds are never captured.

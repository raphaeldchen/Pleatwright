# The SAT layer stage, end to end on `lizard`

Spec: `../../specs/2026-10-02-sat-layer-stage-design.md`. Script: `stage.py`. Artifact: `stage.json`.

Every figure below is from `stage.json` unless it names another source or is marked *derived*
with its arithmetic shown.

## 1. Headline

Dense `lizard` through `compile_tree(..., dense=True, sat_layers=True)` **reaches `emit` with
`verdict.kind = CERTIFIED` in 28.6 s** (`stage.json` `dense.secs`, `dense.stage_reached`,
`dense.verdict.kind`).

The shipped dense path, on the same subject, spent **1052.0 s** and returned
`AssignFail(kind='budget', site=500000)` with no fold
(`../2026-09-27-core-in-loop/ab.json` `arms[0].secs`, `arms[0].failure`).

The defensible statement is that one path answers in tens of seconds and the other did not
answer in over 800 s. The shipped path's own `baseline.secs` for the same path is **834.0 s**
(`../2026-09-27-core-in-loop/ab.json` `baseline.secs`), so its wall clock varies by at least
1052.0 - 834.0 = 218.0 s (*derived*) between runs.

*Derived, and not a speed-up claim:* 1052.0 / 28.6 = 36.8x. **Do not quote this ratio without
the rest of this paragraph.** The two timings are of different outcomes (28.6 s is time to a
certified emit; 1052.0 s is time to giving up at a 500,000-node budget), and they were taken in
different runs on different days under unrecorded load.

## 2. Reproduction, and this README's own record

```
cd mcp_harness && PYTHONPATH=. ../.venv/bin/python3 -u ../docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.py ../docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.json
```

`stage.py` writes none of the following into the JSON, so this README is their only record:

| | |
|---|---|
| run date | 2026-10-02, launched 22:11:31 CDT host-local (= 2026-10-03 03:11 UTC, *derived*: CDT is UTC-5), finished 22:12:01 CDT |
| code commit (HEAD when run) | `2a3a75624287158790af63da80f172eeb63aeade`. **The tree was not clean:** `stage.py` carried the uncommitted edits made for this run (the `raw_triple_bound` recorder and the empty-audit guard), committed immediately afterwards; `stage.json` was the only other modified file. Nothing under `mcp_harness/` was modified. |
| exit status | 0 (`wrote ...stage.json` and a VERDICT line were printed; the shell recorded `exit=0`) |
| platform | macOS (darwin); `ru_maxrss` read as bytes, see section 4 |
| host load average (1/5/15 min) | **2.82 / 2.69 / 3.01** by `uptime` immediately before launch, 2.88 / 2.72 / 3.00 immediately after exit |
| other host activity | one unrelated process from a different project (`scripts/prediction_burden.py`) read about 33% CPU in a `ps` snapshot taken right after the run, alongside a Chrome renderer (about 38%) and Slack (about 27%). The host was **not idle**. The 28.6 s is therefore a figure under a load of about 3, not a quiet-host figure. |

This is the **second** run of the same compile. The first (committed in `2a3a7562`, readable with
`git show 2a3a7562:docs/superpowers/evidence/2026-10-02-sat-layer-stage/stage.json`) read
**28.2 s** and **1491.3 MB** peak RSS; this one reads 28.6 s and 1432.3 MB. The re-run was made to
record `raw_triple_bound`, and it moved every timing and the RSS (section 4). The two runs differ
by 28.6 - 28.2 = 0.4 s and 1491.3 - 1432.3 = 59.0 MB (*derived*); two readings are not a variance
estimate. The Task 3 brief also records an earlier 28.42 s reading of the same compile, not
recorded in this directory. Only the second run's numbers are used below.

## 3. The instance

Dense `lizard`, from `stage.json` `dense.verdict` and `dense.fold`:

| quantity | value |
|---|---|
| order variables | 53,754 |
| label variables | 745 |
| clauses streamed | 9,678,554 |
| `raw_triple_bound` (`sat_order.raw_triple_bound(cons)`) | 31,314,680 |
| build seconds | 12.443 |
| solve seconds | 0.185 |
| emitted fold | 380 vertices, 759 edges |

The 12.443 + 0.185 = 12.628 s of build plus solve (*derived*) is 44% of the 28.6 s total
(*derived*, 12.628 / 28.6). The remaining ~16.0 s (*derived*, 28.6 - 12.628 = 15.972) is the rest
of the wall clock outside `sat_order.solve`. **`stage.json` does not decompose it and this
README does not attribute it to any stage.** The solver itself is not the cost: 0.185 s.

**The 745 label variables are near-definitional, not independent corroboration.**
`sat_order.encode` builds one label variable per slot (`label_var = {s.edge: pool.id(("lab",
s.edge)) for s in slots}`, `mcp_harness/box_pleat/sat_order.py:160`), and
`mcp_harness/box_pleat/layers.py:59` documents `slots` as one `DirectSlot` "per creased shared
edge". So "745 label variables" restates "745 slots", i.e. the number of creased shared edges the
compile hands the encoder. The 745 creases that
`../2026-10-02-witness-identity-113/README.md` section 15.2 reports ("745 of 745") count the same
slot set for the same subject, so their agreement is expected from the construction and confirms
only that the two runs encoded the same crease set, not that either count is right about the fold.

**`raw_triple_bound`: 31,314,680 for dense `lizard`** (`stage.json` `dense.raw_triple_bound`),
recorded in this run by observing the `cons` that `compile_tree` passed to `sat_order.solve`
(`stage.py` `_recording_solve`, a pass-through wrapper; `compile_tree` does not return `cons`).
It **agrees exactly** with the 31,314,680 stated in the `MAX_RAW_TRIPLES` comment in
`mcp_harness/box_pleat/sat_order.py`, which was previously unmeasured here. It is the refusal
check's input, against the 100,000,000 ceiling (`stage.json` `max_raw_triples`); 31,314,680 /
100,000,000 = 31.3% of the ceiling (*derived*). It is a loose upper bound on transitivity triples,
not a count of them. Sparse `lizard`'s bound is 996 (`stage.json` `sparse.raw_triple_bound`).

Sparse `lizard` (`stage.json` `sparse`): CERTIFIED, 0.7 s, 158 order vars, 27 label vars, 2,402
clauses, fold 22 vertices / 41 edges. Sparse has no shipped-path baseline in this directory, so no
comparison is made.

## 4. Peak RSS, and the `MAX_CLAUSES` decision

**Measured peak RSS, dense `lizard`: 1432.3 MB** (`stage.json` `dense.peak_rss_mb`).

How it is derived: `resource.getrusage(RUSAGE_SELF).ru_maxrss`, which macOS reports in **bytes**
(Linux: kilobytes); `peak_rss_mb()` divides by 1024 x 1024 on darwin. Units: MB with 1 MB =
1,048,576 bytes.

Why the bytes reading is the coherent one, from this run's own number: the raw `ru_maxrss` is
1432.3 x 1,048,576 = about 1.502 x 10^9 (*derived*; the operand is `peak_rss_mb` rounded to 0.1
MB). Read as kilobytes, that is 1.502 x 10^9 x 1024 = about 1.54 x 10^12 bytes = **about 1.54 TB**
(*derived*), which no machine this was run on has. Under the bytes reading it is 1.43 GB. Only the
bytes reading is possible.

What the number covers and does not:

* It is a **process-wide high-water mark**, not a per-stage figure. The run was one process doing
  sparse then dense. The sparse row's high-water mark was 43.8 MB (`sparse.peak_rss_mb`), so the
  dense figure is entirely dense's own peak; nothing from sparse inflates it.
* It includes the interpreter and imports: **36.0 MB** before any compile (`rss_before_mb`).
* It includes the in-process CaDiCaL solver's memory.
* It is **one run in this artifact**. The earlier run read 1491.3 MB (section 2), 59.0 MB higher
  (*derived*); that is two readings, not a variance estimate.

**Decision: `MAX_CLAUSES` stands at 20,000,000 (`stage.json` `max_clauses`). Nothing changed.**
Spec section 5's rule is to lower it if peak RSS exceeds ~4 GB (4096 MB). 1432.3 MB does not:
1432.3 / 4096 = 35.0% of 4096 MB (*derived*), a margin of 4096 / 1432.3 = 2.86x (*derived*). The
decision was re-derived from this run's RSS and is the same as from the earlier run's 1491.3 MB.

What this does **not** license: the measurement is at 9,678,554 clauses, and the ceiling is at
20,000,000, which is 20,000,000 / 9,678,554 = 2.07x the measured instance (*derived*). **No run
here approaches the ceiling, so RSS at the ceiling is unmeasured.** A linear extrapolation gives
an indicative figure: (1432.3 - 36.0) = 1396.3 MB attributed to the build, scaled by 2.07, plus the
36.0 MB baseline, is about 2,921 MB (*derived*, 36.0 + 1396.3 x 20,000,000 / 9,678,554). That is
under 4096 MB, but it is an extrapolation under two assumptions that are both unverified: that
all 1396.3 MB scales with clause count (it does not entirely, since the compile's own structures
are fixed; this errs high) and that growth is linear with no allocator or solver step effects
(which errs in an unknown direction). Treat ~2.9 GB as an estimate, not a measurement.

## 5. `cp_audit` on the emitted fold

`cp_audit.audit_fold` on the dense emitted fold (`stage.json` `dense.audit`). The population is
**366 interior vertices** (`audit.interior` = `len(report.vertices)`, which
`mcp_harness/cp_audit.py` documents as "every interior vertex, audited") of the 380-vertex fold.
The other 14 vertices (*derived*, 380 - 366) are outside the audit population by definition:
`mcp_harness/cp_audit.py:20` pins an interior vertex as one with at least one incident crease and
**no** incident `"B"` (border) edge, so the 14 are border-incident or crease-free. `stage.json`
does not record which of those two each is; this README does not split them.

| counter | value | of |
|---|---|---|
| Maekawa violations (`abs(m - v) != 2`) | 0 | 366 interior vertices |
| Kawasaki violations (residual over `kawasaki_tol_deg`) | 0 | 366 interior vertices |
| `arrangement_ok` False | 0 | 366 interior vertices |
| closure bad edges | 0 | edges (count not recorded in JSON) |
| closure max error | 3.1401849173675502e-15 | n/a |

These agree with the same five-counter audit of the SAT witness fold in
`../2026-10-02-witness-identity-113/README.md` section 15.3 (0 / 0 / 366-of-366 ok / 0 bad edges /
max error 3.1e-15). That agreement is expected rather than independent: both are the same crease
set decided by the same encoding. This run's contribution is that the **shipped `compile_tree`
stage** produces it end to end, not that a second solver confirmed it.

Sparse audit (`stage.json` `sparse.audit`): all counters 0 over 8 interior vertices.

## 6. What this does not establish

* **The F set is fixed by `assign`'s first candidate.** The stage decides the layer order and the
  M/V labels of a crease set that `assign` already chose. A different F set might be better or
  worse, or might be unsatisfiable; this run does not explore that. A CERTIFIED verdict means the
  query is satisfiable *for that F set*.
* **`AREA_EPS` was measured inert on dense `lizard` only.** `../2026-10-02-witness-identity-113/README.md`
  section 16 measured that no arrangement cells are dropped at any threshold down to zero on
  dense `lizard`. The six-subject study recorded in the `AREA_EPS` header comment of `mcp_harness/layer_order.py` (lines 36-62, U20 2026-08-17, `probe_sigma_platform.py`) found subjects that straddle the threshold, so for
  those subjects "certified" would mean certified against the constraint set that survived
  `AREA_EPS`, not the full one. Nothing here measures any other subject.
* **One subject.** `lizard`, dense and sparse. The two rows of `stage.json` are two compiles of the
  same tree, not two subjects. No claim about other subjects' wall clock, RSS or satisfiability.
* **One run in the artifact, one host, under load.** Timing and RSS are single readings on a macOS host at load
  about 3 with an unrelated process running. No variance is estimated.
* **RSS at the `MAX_CLAUSES` ceiling is unmeasured** (section 4).
* **Wall-clock comparison with the shipped path is across different runs** and is a comparison of
  different outcomes (section 1).
* **`sat_layers` ships OFF.** `compile_tree`'s default is `sat_layers=False`; this evidence says
  the opt-in path works on this subject, not that it should be the default, and no default was
  changed.
* **`tests/test_box_pleat_e2e.py` was not run** in this task; it exceeds the environment's
  background time limit and is owned by the controller.

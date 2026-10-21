# Regression Testing + CI — Design

**Date:** 2026-06-12
**Status:** Approved (design); pending implementation plan
**Scope:** Add a regression test suite and a CI pipeline to `origami-design-ide`,
and restructure the repo into a single monorepo to host them.

## Motivation

The compile pipeline (Metric Tree → TreeMaker C++ → `.fold` → Oriedita lint) has
already regressed silently once: a single commit chain (`d737e92`) introduced 8
distinct engine regressions that broke a previously-working pipeline and cost
multiple sessions to recover. There is currently no automated gate that would
catch this class of breakage. The building blocks for one already exist
(`probe_sweep.py` classifies 16 topologies; the Oriedita linter is a trusted
correctness oracle), but they only *print* results — nothing *asserts*.

This design freezes the current known-good behavior as a baseline and fails fast
on regression, locally (`make test`) and in CI (GitHub Actions).

## Decisions (locked during brainstorming)

| Decision | Choice | Rationale |
|---|---|---|
| Repo topology | Single monorepo rooted at project root, absorbing the `origami-design-ide` repo (currently rooted at `mcp_harness/`) | User wants everything under one repo; root docs are currently untracked |
| treemaker fork | Dropped from tree; full history preserved as a git bundle in `docs/engine-history/` | Build only ever used the vendored subset (`mcp_harness/treemaker/`); fixes are already baked into it; fork's `origin` was someone else's repo so history was unbacked. **(Already executed.)** |
| Assertion level | Verdict baseline + epsilon geometry goldens for the 3 known-good cases | Catches d737e92-class breakage with low maintenance; geometry goldens catch numeric drift on the proven-good path |
| CI runner | `macos-latest` | `build.sh` is macOS-specific (clang `-undefined dynamic_lookup`, `cpython-314-darwin`, Python 3.14); matches dev env with zero portability work |

## Architecture

Four phases. Phase 0 (fork bundle + drop) is already done.

```
origami-design-ide/                 ← git init / .git promoted here = canonical repo
├── .gitignore                      ← NEW: *.so, *.dSYM/, oriedita-*.jar, __pycache__/, *.class, .venv/
├── Makefile                        ← NEW: single source of truth for build/test/bless
├── CLAUDE.md, *.md, docs/          ← now tracked
├── docs/engine-history/            ← treemaker-fork.bundle (DONE) + README
├── headless_spike/
├── mcp_harness/                    ← harness + vendored engine subset (build-complete)
│   ├── build.sh, build_linter.sh   ← existing build scripts (unchanged)
│   ├── server.py, linter_server.py, agent_loop.py, probe_*.py
│   ├── treemaker/                  ← vendored minimal engine subset (142 .cpp/.h) — what builds
│   └── tests/                      ← NEW: the regression suite
│       ├── conftest.py
│       ├── cases.py
│       ├── baseline_verdicts.json
│       ├── goldens/*.fold
│       ├── test_verdicts.py
│       ├── test_geometry.py
│       └── test_determinism.py
└── .github/workflows/ci.yml        ← NEW: thin wrapper over `make test`
```

### Phase 0 — Repo restructure (foundation)

- **DONE:** `treemaker/` fork bundled to `docs/engine-history/treemaker-fork.bundle`
  (verified, complete history, 5.6MB) with a restore `README.md`, then the 653MB
  fork directory removed. Vendored engine subset intact (142 files).
- Promote the existing `origami-design-ide` repo from `mcp_harness/` to the root:
  move `mcp_harness/.git` → root and record the path shift as one isolated
  "restructure" commit. Git rename detection keeps history reachable
  (`git log --follow`). Preserves the 246-file history and the GitHub remote.
- Add `.gitignore`; `git rm --cached` the committed artifacts (keeps local files,
  stops versioning generated output).
- Begin tracking the root docs and `headless_spike/`.

### Phase 1 — Regression suite (`mcp_harness/tests/`, pytest)

Co-located under `mcp_harness/` so `import headless_treemaker` and
`import linter_server` resolve without path hacks. Built on the proven
spawn+timeout isolation pattern from `probe_sweep.py`.

- **`cases.py`** — the canonical tree catalog (star, caterpillar, symmetric,
  uneven, deep-chain, two-level, plus the H-shape and quad known-good cases).
  Single source of truth; `probe_sweep.py` is refactored to import it.
- **`runner.py`** — importable helpers (an importable module rather than a
  `conftest.py`, so `bless.py` and `probe_sweep.py` can import the same logic):
  - `compile_tree(nodes, pairs, timeout)` → runs a compile in a spawned
    subprocess with a timeout, returning `("ok", fold) | ("err", msg) |
    ("CRASH", info) | ("HANG", "")`. Lifted from `probe_sweep.run`/`_worker`.
  - `lint(fold)` → first line of `linter_server.validate_flat_foldability`.
  - `verdict_for(...)` and `fold_geom(...)`; `GEOM_KEYS` is the single source of
    which keys are compared and stored in goldens.
- **`test_verdicts.py`** — parametrized over every case. Computes the current
  verdict (`PASS`/`FAIL-LINT`/`CLEAN-ERR`/`CRASH`/`HANG`) and asserts it equals
  the value in `baseline_verdicts.json`. `CRASH`/`HANG` always fail regardless of
  baseline. A verdict that *improves* (e.g. `FAIL-LINT`→`PASS`) also fails until
  re-blessed — intentional, forces conscious acknowledgement.
- **`test_geometry.py`** — for star/H/quad: compile, then compare against the
  golden `.fold`:
  - `vertices_coords`: per-coordinate within abs tolerance `1e-6` (CI runs on a
    different machine than dev, so exact float match is not assumed).
  - `edges_assignment` (mountain/valley): exact match.
  - `edges_vertices` (topology): exact match.
  - Note: the engine's FOLD export contains vertices + edges only (no
    `faces_vertices`), plus `file_*`/`frame_*` metadata which the comparison
    ignores. Confirmed keys: `vertices_coords`, `edges_vertices`,
    `edges_assignment`, `file_classes`, `file_creator`, `file_spec`,
    `frame_attributes`, `frame_classes`, `frame_title`.
- **`test_determinism.py`** — compile the same tree twice; assert identical
  geometry (the `runner.GEOM_KEYS` subset; volatile `file_*`/`frame_*` metadata
  is excluded so it can't masquerade as nondeterminism). (Generalizes
  `probe_determinism.py`.)

**Blessing workflow:** `make bless` regenerates `baseline_verdicts.json` and the
`goldens/*.fold` from current engine output. Run deliberately when the engine
legitimately changes; the diff to the baseline/goldens is the reviewable record
of what changed.

### Phase 2 — Makefile (single source of truth)

Root `Makefile` so local and CI invoke identical commands:

- `make build` → `mcp_harness/build.sh` (C++ ext) + `mcp_harness/build_linter.sh`
  (Oriedita jar + validator).
- `make test` → `make build`, then `pytest mcp_harness/tests/`. **The gate.**
- `make bless` → regenerate verdict baseline + goldens.
- `make sweep` → run `probe_sweep` catalog (exploratory, non-gating).
- `make clean` → remove build artifacts.

### Phase 3 — CI pipeline (`.github/workflows/ci.yml`)

Triggered on push + pull_request, `runs-on: macos-latest`:

1. `actions/checkout`
2. setup Python 3.14 + Java 17 (Temurin)
3. cache pip + the Oriedita jar (keyed on `ORIEDITA_VERSION`)
4. `pip install pybind11 pytest`
5. `make test`
6. concurrency group cancels superseded runs on the same ref

CI is a thin wrapper: all logic lives in the Makefile, so any CI failure
reproduces locally with one command.

## Error handling / failure semantics

- Engine SIGSEGV or infinite loop → caught by subprocess isolation + timeout →
  reported as a `CRASH`/`HANG` test failure, never a harness crash.
- Lint failure on a case baselined as `PASS` → test failure (regression).
- Geometry drift beyond `1e-6`, or any M/V or topology change → test failure.
- Non-determinism → test failure.
- Legitimate engine change → developer runs `make bless`, reviews the baseline/
  golden diff, commits it alongside the engine change.

## Out of scope (YAGNI)

- The ~30 `probe_*.py` scripts remain as investigation tools (only the `CASES`
  catalog graduates to `tests/cases.py`).
- No Linux/matrix build, no CD/deploy automation, no pre-commit hooks. Defer
  until a second contributor or a deploy target exists.
- No deduplication of the vendored vs. (now-removed) full engine source — the
  vendored subset is canonical going forward.

## First-run expectation

Per current engine state: star/H/quad PASS end-to-end; larger stars/caterpillars
are `FAIL-LINT` (the known precision/molecule-topology frontier); no crashes or
hangs across the 16-case sweep. The initial `make bless` will encode these as the
baseline, so the gate locks in the good path and guarantees nothing silently
starts crashing or regressing from PASS.

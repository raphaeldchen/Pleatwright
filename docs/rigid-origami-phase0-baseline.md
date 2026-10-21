# Rigid origami Phase-0 pre-change baseline

**Date:** 2026-07-12
**Branch:** `codex/rigid-origami-phase-0`
**Starting commit:** `450059b`
**Platform:** macOS, Python 3.14.3

The worktree already contained user-owned untracked research artifacts, including
`AGENTS.md` and `docs/rigid-origami-ide-plan.md`. They were preserved. Tracked
files were clean before the baseline build.

## Environment used

`mcp_harness/.venv`:

- Python 3.14.3
- NumPy 2.4.6
- SciPy 1.17.1
- NetworkX 3.6.1
- Pydantic 2.13.4
- jsonschema 4.26.0
- pytest 9.0.3
- Trimesh 4.12.2 (present but not selected as rigid collision authority)
- pybind11 3.0.4

## Regression commands and results

```text
make test
```

- Rebuilt the C++ TreeMaker extension and Java Oriedita adapter.
- Result: `481 passed, 4 skipped, 1 warning in 576.09s`.
- Warning: existing joblib physical-core detection fallback.

```text
PYTHONPATH=. mcp_harness/.venv/bin/python -m pytest web/tests -q
```

- Result: `40 passed, 1 warning in 0.78s`.
- Warning: existing Starlette `httpx`/`TestClient` deprecation.

```text
cd web/frontend && npm test -- --run
```

- Result: `59 passed` across six files in `359ms` test duration.

## Gate interpretation

This is the comparison point for the isolated rigid package. The Phase-0 slice
must not change legacy TreeMaker/Oriedita/web/frontend behavior, and the final
gate must rerun all three surfaces.

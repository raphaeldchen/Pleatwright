# full17_v3 trees — the "Bases in Triplicate III" corpus

51 packed rolls over 17 subjects, copied verbatim from the untracked
`repair_rolls_out_full17_v3/<roll>/state.json` run directory by
`export_full17_v3_fixtures.py` (spec
`docs/superpowers/specs/2026-09-16-corner-pin-tooling-design.md` §3).
The six rolls that did not serve are not here.

Each `<roll>.json`: `tree_nodes` (authored order), `served_nodes` (the order
that served), `symmetric_pairs`, `names`, `leaves`, `served_stage`,
`served_fold` (the served 45° FOLD string, verbatim — scale is in its
`frame_title`). `index.json` lists roll, subject, leaf count, pair count and
served stage. Integrity: `tests/test_full17_v3_fixtures.py`.

**Note, 2026-10-07 (Pleatwright retirement of TreeMaker).** The text above is
the corpus's original record and is kept as written. On `main`,
`export_full17_v3_fixtures.py` no longer exists, and nothing reads the served
fields (`served_nodes`, `served_stage`, `served_fold`): they are TreeMaker
serve-path output, still present in each `<roll>.json` but not checked by the
integrity test here. The exporter, the serve path that produced those fields,
and the tests that pinned them are on the branch `archive/treemaker-box-pleat`.
Pleatwright reads the trees through `fixtures/full17_v3_sticks/`.

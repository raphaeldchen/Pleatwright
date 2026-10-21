"""Root conftest for the mcp_harness test suite (invoked as
``cd mcp_harness && pytest tests``)."""
import os

# A TEST RUN MUST NOT MUTATE STATE OUTSIDE ITS OWN WORKTREE.
#
# mesh_acquire writes a provenance sidecar (meta.json) beside every cached
# mesh, on the fetch path AND on a cache hit. A call site that acquires without
# a `cache_dir` lands in mcp_harness/generated_meshes/, whose per-key entries
# are SYMLINKS INTO SIBLING CHECKOUTS under this repo's worktree bootstrap. The
# sidecars are correct and gitignored, so nothing breaks; the problem is that a
# plain `pytest tests` silently writes into another checkout's cache.
#
# This wave has already been burned three times by shared state: a shared
# scratchpad published one unit's PR body under another unit's name, a shared
# 10-core host manufactured timeout failures at load ~150, and an
# account-global GPU quota died mid-experiment. A test run writing into a
# neighbouring checkout is the same class of surprise and the same class of
# phantom debugging six weeks from now.
#
# setdefault, not a plain assignment: an explicit IDE_MESH_PROVENANCE=1 in the
# environment still wins, for anyone who wants a suite run to exercise the real
# write path. No coverage is lost either way -- tests/test_mesh_acquire.py
# re-enables it per test, which is the one module where the write IS the
# subject, and it asserts this line is in force (see
# test_conftest_disables_provenance_writing_for_the_whole_suite).
os.environ.setdefault("IDE_MESH_PROVENANCE", "0")

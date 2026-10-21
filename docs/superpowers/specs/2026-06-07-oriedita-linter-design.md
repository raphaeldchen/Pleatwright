# Oriedita Static Linter — Design

**Date:** 2026-06-07
**Status:** Approved
**Component:** Tier 3 "Static Linter" (per `CLAUDE.md` §3, §4B)

## Purpose

Wrap the open-source Java origami solver **Oriedita** as a Python MCP server that
receives a `.fold` JSON string, runs Oriedita's per-vertex flat-foldability checks
(Maekawa / Kawasaki / number-of-folds / big-little-big), and returns either `"Pass"`
or a list of vertex violations to the AI agent.

This is the validation half of the backend; the geometry compiler (headless
TreeMaker) already exists in `mcp_harness/`.

## Verified facts (investigated against oriedita/oriedita @ master, 2026-06-07)

The original task spec guessed at Oriedita internals. Actual API, confirmed by
reading source:

- Core class is `origami.crease_pattern.FoldLineSet` (NOT the spec's
  `oriedita.engine.core.FoldLineSet`, which does not exist).
- The flat-foldability checker is `origami.crease_pattern.worker.foldlineset.Check4`:
  `Check4.apply(FoldLineSet)` populates a queue read via `FoldLineSet.getViolations()`.
- Each result is `origami.crease_pattern.FlatFoldabilityViolation` with:
  - `getViolatedRule()` → enum `{NUMBER_OF_FOLDS, ANGLES, MAEKAWA, LITTLE_BIG_LITTLE, NONE}`
    (ANGLES = Kawasaki's theorem).
  - `getColor()` → enum `{NOT_ENOUGH_MOUNTAIN, NOT_ENOUGH_VALLEY, EQUAL, CORRECT, UNKNOWN}`.
  - `getPoint()` → vertex location (x, y).
- `.fold` ingestion: `oriedita.editor.export.FoldImporter.importFile(File)` returns a
  `Save`; `new FoldLineSet().setSave(save)` loads it. `FoldImporter` is annotated
  `@ApplicationScoped` but its methods work when called via plain `new FoldImporter()`
  (no CDI container required).
- **No headless CLI exists** — the only entry point is the Swing app `App.java`. A small
  Java wrapper is therefore required (the spec anticipated this).
- The degree-magnitude of a violation ("off by 15°") is **not** exposed by this API; we
  report rule + vertex + M/V color only.

## Build approach

- No Maven/Gradle installed; Temurin JDK 17 is present (`javac`/`java`).
- Use the prebuilt shaded release jar `oriedita-1.1.3.jar` (~15 MB) from GitHub releases.
  It bundles `origami.*`, `oriedita.editor.export.*`, the `fold.io` FOLD parser, tinylog,
  and jakarta annotations — everything the wrapper links against.
- The ~48 MB release assets are platform installers with a bundled JRE; not needed.

## Components (all under `mcp_harness/`)

### `OrieditaValidator.java`
```
main(args[0] = path to .fold):
  Save save = new FoldImporter().importFile(new File(path));
  FoldLineSet fls = new FoldLineSet();
  fls.setSave(save);
  Check4.apply(fls);
  Queue<FlatFoldabilityViolation> v = fls.getViolations();
  if v.isEmpty(): println "PASS"
  else: for each -> println "VIOLATION\t<rule>\t<color>\t<x>\t<y>"
  exit 0
  // on any exception: System.err "ERROR\t<message>"; exit 1
```
Tab-delimited, machine-readable; Python does the human formatting.

### `build_linter.sh`
Idempotent. Downloads `oriedita/oriedita-1.1.3.jar` if absent, then
`javac -cp oriedita-1.1.3.jar OrieditaValidator.java`.

### `linter_server.py` (FastMCP, mirrors `server.py`)
Tool `validate_flat_foldability(fold_json_string: str) -> str`:
1. Sanity-gate: parse JSON and confirm it looks like FOLD (`vertices_coords` +
   `edges_vertices`). Reject early with a clean error — never spawn the JVM on garbage.
2. Write to a `NamedTemporaryFile(suffix=".fold")`.
3. `subprocess.run(["java","-cp", jar+os.pathsep+classdir, "OrieditaValidator", path],
   capture_output=True, text=True, timeout=60)`, wrapped for `TimeoutExpired` and any
   spawn error. JVM crash cannot kill the server (separate process).
4. Parse stdout: `PASS` → `"Pass"`; `VIOLATION` lines → formatted multi-line string.
   Nonzero exit / stderr → `"ERROR: …"`.
5. Delete temp file in `finally`.

## Error-handling matrix

| Input | Result |
|---|---|
| Valid, flat-foldable | `"Pass"` |
| Valid FOLD, bad vertices | `"Flat-foldability FAILED:\n  Vertex (x,y): MAEKAWA — NOT_ENOUGH_MOUNTAIN\n …"` |
| Not JSON / not FOLD | `"ERROR: input is not a valid FOLD file (…)"` (no JVM spawned) |
| JVM crash / OOM / hang | `"ERROR: validator subprocess …"`, server survives |

## Verification (this session)

1. Oriedita's own `oriedita_minimal.fold` fixture → expect `Pass`.
2. Hand-built single interior vertex violating Maekawa (3 mountain, 1 valley) →
   expect a MAEKAWA violation line.
3. `"{not json"` and a valid-JSON-but-not-FOLD blob → expect clean `ERROR`, server alive.

## Out of scope

Auto-deduction of missing mountain/valley assignments (Oriedita's `Fix1`/`Fix2`
workers). Validation only, per the task spec.

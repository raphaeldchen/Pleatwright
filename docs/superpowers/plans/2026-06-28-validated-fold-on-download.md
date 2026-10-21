# Serve the Validated Hull on Download (fix #1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Download button and JSON tab serve the *validated* raw hull while the 3D viewer keeps showing the squared display copy, closing the provenance gap where the downloaded file is not the artifact that passed validation.

**Architecture:** Split the single `fold` WebSocket frame into two fields — `json` (the raw hull straight from `extract_fold`, what the agent linted) and `display_json` (the squared copy from `_square_for_display`). Download + JSON tab read `json`; the 3D viewer reads `display_json`. No change to the squaring algorithm or the compile/lint path.

**Tech Stack:** Python / FastAPI WebSocket bridge (`web/server.py`, pytest + `fastapi.testclient`); React + TypeScript frontend (`web/frontend/src`, vitest).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-28-validated-fold-on-download-design.md`.
- `_square_for_display` is unchanged (still fail-safe: returns input on any exception).
- The server ALWAYS sends `display_json`, even when it equals `json`. No "did squaring change" branch.
- The JSON text tab shows the validated hull (matches Download), NOT the square.
- `App.tsx` requires NO edits: `download()` and the JSON `<pre>` already read `state.fold.json` (now the validated hull); the viewer already receives the whole `state.fold`.
- Python tests run: `mcp_harness/.venv/bin/python -m pytest <path> -v`
- Frontend tests run from `web/frontend/`: `npx vitest run <path>`
- Treat this as likely permanent, not a stopgap: it is reverted (delete the `display_json`/`displayJson` field) only if option 3 (molecule corner-creasing, §8 — recommended against) ever makes the squared FOLD the validated artifact. A-9 (generative detail) does NOT retire it — it still compiles to a hull that gets squared for display.

---

### Task 1: Split the server fold frame into `json` (validated) + `display_json` (squared)

**Files:**
- Modify: `web/server.py:101-104` (`_send_frames`, the `fold is not None` branch)
- Test: `web/tests/test_server.py` (modify `test_ws_squares_fold_for_display`)

**Interfaces:**
- Consumes: `extract_fold(output) -> dict | None` (raw hull); `_square_for_display(fold: dict) -> dict` (squared, fail-safe) — both already in `web/server.py`.
- Produces: a `fold` frame shaped `{"type": "fold", "filename": "model.fold", "json": <raw hull dict>, "display_json": <squared dict>}`. Frontend Task 2 relies on the snake_case key `display_json`.

- [ ] **Step 1: Update the existing display test to expect the split**

In `web/tests/test_server.py`, the current `test_ws_squares_fold_for_display` asserts the squared corner `(1.0, 1.0)` appears in `fold_frame["json"]`. After the split, `json` is the RAW hull (no corner) and `display_json` is the squared copy (has the corner). Replace the assertion block at the end of that test (everything from `fold_frame = next(...)` to the end of the function) with:

```python
    fold_frame = next(f for f in frames if f["type"] == "fold")

    # json = the raw, validated hull: the (1,1) corner is NOT creased in.
    raw_coords = {(round(p[0], 6), round(p[1], 6))
                  for p in fold_frame["json"]["vertices_coords"]}
    assert (1.0, 1.0) not in raw_coords          # download/JSON-tab = validated hull

    # display_json = the squared copy for the 3D viewer: corner added.
    disp_coords = {(round(p[0], 6), round(p[1], 6))
                   for p in fold_frame["display_json"]["vertices_coords"]}
    assert (1.0, 1.0) in disp_coords             # viewer = full square
    assert disp_coords != raw_coords             # the two artifacts genuinely differ
```

Also rename the test for clarity — change the `def` line and docstring to:

```python
def test_ws_splits_validated_hull_and_squared_display(monkeypatch):
    """The fold frame carries TWO artifacts: json = the raw validated hull
    (what Download serves), display_json = the squared copy (what the 3D
    viewer renders). The provenance guard: json must equal the linted hull."""
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py::test_ws_splits_validated_hull_and_squared_display -v`
Expected: FAIL — the current server squares `json`, so `(1.0, 1.0)` IS in `json` and there is no `display_json` key (KeyError or assertion failure).

- [ ] **Step 3: Split the frame in `_send_frames`**

In `web/server.py`, replace the `fold is not None` branch (currently lines 101-104):

```python
        fold = extract_fold(output)
        if fold is not None:
            await ws.send_json({"type": "fold", "filename": "model.fold",
                                "json": _square_for_display(fold)})
```

with:

```python
        fold = extract_fold(output)
        if fold is not None:
            # json = the raw hull the agent actually linted (Download + JSON tab);
            # display_json = the squared copy for the 3D viewer only. See
            # docs/superpowers/specs/2026-06-28-validated-fold-on-download-design.md
            await ws.send_json({"type": "fold", "filename": "model.fold",
                                "json": fold,
                                "display_json": _square_for_display(fold)})
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py::test_ws_splits_validated_hull_and_squared_display -v`
Expected: PASS

- [ ] **Step 5: Run the full server test file to confirm no regressions**

Run: `mcp_harness/.venv/bin/python -m pytest web/tests/test_server.py -v`
Expected: PASS — `test_ws_streams_frames_and_captures_fold` still passes because its hull already fills the square, so `json["file_spec"]` is unchanged and it never inspects corners.

- [ ] **Step 6: Commit**

```bash
git add web/server.py web/tests/test_server.py
git commit -m "$(cat <<'EOF'
fix(download): serve the validated hull, square only for the viewer

Split the fold frame into json (raw linted hull -> Download + JSON tab)
and display_json (squared -> 3D viewer). Closes the provenance gap: the
downloaded file now equals the artifact the agent passed.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Carry `displayJson` through the frontend reducer

**Files:**
- Modify: `web/frontend/src/chat.ts` (the `fold` `Frame` variant, `FoldArtifact`, and the `applyFrame` `fold` case)
- Test: `web/frontend/src/chat.test.ts` (modify "captures a fold artifact")

**Interfaces:**
- Consumes: the `fold` frame from Task 1 with snake_case `display_json`.
- Produces: `FoldArtifact = { filename: string; json: unknown; displayJson?: unknown }`. Task 3's viewer reads `displayJson` off this object. The reducer maps frame `display_json` -> artifact `displayJson` (snake_case wire -> camelCase state).

- [ ] **Step 1: Update the reducer test to expect `displayJson`**

In `web/frontend/src/chat.test.ts`, replace the entire "captures a fold artifact" test with:

```typescript
  it("captures a fold artifact with validated json and display copy", () => {
    const fold = { file_spec: 1.1, vertices_coords: [[0, 0]] };
    const squared = { file_spec: 1.1, vertices_coords: [[0, 0], [1, 1]] };
    const s = applyFrame(initialState, {
      type: "fold",
      filename: "model.fold",
      json: fold,
      display_json: squared,
    });
    expect(s.fold).toEqual({
      filename: "model.fold",
      json: fold,
      displayJson: squared,
    });
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run (from `web/frontend/`): `npx vitest run src/chat.test.ts`
Expected: FAIL — the `fold` `Frame` type has no `display_json` (TS/compile error) and the reducer does not store `displayJson`.

- [ ] **Step 3: Add `display_json` to the frame type**

In `web/frontend/src/chat.ts`, change the `fold` variant of `Frame` from:

```typescript
  | { type: "fold"; filename: string; json: unknown }
```

to:

```typescript
  | { type: "fold"; filename: string; json: unknown; display_json: unknown }
```

- [ ] **Step 4: Add `displayJson` to `FoldArtifact`**

In `web/frontend/src/chat.ts`, change `FoldArtifact` from:

```typescript
export interface FoldArtifact {
  filename: string;
  json: unknown;
}
```

to:

```typescript
export interface FoldArtifact {
  filename: string;
  json: unknown;        // the raw, validated hull (Download + JSON tab)
  displayJson?: unknown; // the squared copy for the 3D viewer
}
```

- [ ] **Step 5: Store both in the reducer**

In `web/frontend/src/chat.ts`, change the `fold` case of `applyFrame` from:

```typescript
    case "fold":
      return { ...state,
        fold: { filename: frame.filename, json: frame.json } };
```

to:

```typescript
    case "fold":
      return { ...state,
        fold: { filename: frame.filename, json: frame.json,
                displayJson: frame.display_json } };
```

- [ ] **Step 6: Run the test to verify it passes**

Run (from `web/frontend/`): `npx vitest run src/chat.test.ts`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add web/frontend/src/chat.ts web/frontend/src/chat.test.ts
git commit -m "$(cat <<'EOF'
feat(web): carry displayJson through the chat reducer

The fold frame now has json (validated hull) + display_json (squared);
store both on FoldArtifact so Download reads the hull and the viewer
can read the display copy.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Render the squared display copy in the viewer

**Files:**
- Modify: `web/frontend/src/viewer.ts` (`foldChanged` in `createViewerController`)
- Test: `web/frontend/src/viewer.test.ts` (update the shared `fold` fixture + add a fallback test)

**Interfaces:**
- Consumes: `FoldArtifact` with optional `displayJson` (from Task 2). `OrigamiViewer.tsx` already passes the whole artifact to `controller.foldChanged`; no change needed there.
- Produces: when `displayJson` is present the controller posts `{ type: "loadFold", fold: <displayJson> }`; when absent it falls back to `json`. The `?? fold.json` is type null-safety, NOT a "did squaring change" branch — Task 1 always sends the field in production.

- [ ] **Step 1: Update the viewer tests to expect the display copy**

In `web/frontend/src/viewer.test.ts`, change the shared fixture at the top from:

```typescript
const fold = { filename: "m.fold", json: { vertices_coords: [[0, 0]] } };
```

to:

```typescript
const fold = {
  filename: "m.fold",
  json: { vertices_coords: [[0, 0]] },            // raw hull (Download)
  displayJson: { vertices_coords: [[0, 0], [1, 1]] }, // squared (viewer)
};
```

Then in the three existing assertions that reference `fold.json`, change them to `fold.displayJson`:
- in "queues fold until ready, then flushes on ready": `expect(post).toHaveBeenCalledWith({ type: "loadFold", fold: fold.displayJson });`
- in "posts loadFold immediately when already ready": `expect(post).toHaveBeenLastCalledWith({ type: "loadFold", fold: fold.displayJson });`
- in "keeps only the latest pending fold (last-write-wins)": `expect(post).toHaveBeenCalledWith({ type: "loadFold", fold: fold.displayJson });`

(The "last-write-wins" test's first `foldChanged({ filename: "a", json: { a: 1 } })` has no `displayJson`; it is overwritten before ready, so its fallback value is never posted — leave that line as is.)

Add one new test inside the `describe("createViewerController", ...)` block to pin the fallback:

```typescript
  it("falls back to json when displayJson is absent", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    const hullOnly = { filename: "h.fold", json: { vertices_coords: [[2, 2]] } };
    c.foldChanged(hullOnly);
    c.receive({ type: "ready" });
    expect(post).toHaveBeenCalledWith({ type: "loadFold", fold: hullOnly.json });
  });
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `web/frontend/`): `npx vitest run src/viewer.test.ts`
Expected: FAIL — `foldChanged` currently loads `fold.json`, so the updated assertions expecting `fold.displayJson` do not match.

- [ ] **Step 3: Prefer the display copy in `foldChanged`**

In `web/frontend/src/viewer.ts`, change the `foldChanged` method from:

```typescript
    foldChanged(fold) {
      if (!fold) return;
      if (ready) loadFold(fold.json);
      else pending = fold.json;
    },
```

to:

```typescript
    foldChanged(fold) {
      if (!fold) return;
      // The viewer renders the squared display copy; ?? is null-safety for the
      // optional field, not a "did squaring change" branch (server always sends it).
      const data = fold.displayJson ?? fold.json;
      if (ready) loadFold(data);
      else pending = data;
    },
```

- [ ] **Step 4: Run the tests to verify they pass**

Run (from `web/frontend/`): `npx vitest run src/viewer.test.ts`
Expected: PASS (all viewer tests, including the new fallback test)

- [ ] **Step 5: Run the full frontend suite + typecheck**

Run (from `web/frontend/`): `npx vitest run && npx tsc --noEmit`
Expected: PASS — all `.test.ts` green and no TypeScript errors (confirms `App.tsx`, which reads `state.fold.json` for Download/JSON and passes `state.fold` to the viewer, still typechecks against the widened `FoldArtifact`).

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/viewer.ts web/frontend/src/viewer.test.ts
git commit -m "$(cat <<'EOF'
feat(web): render the squared display copy in the 3D viewer

foldChanged now loads displayJson (the squared copy), falling back to
the validated json when absent. Download/JSON tab keep serving the
validated hull; only the viewer sees the square.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- Provenance split (`json` raw + `display_json` squared) → Task 1.
- JSON tab shows validated hull, `App.tsx` unchanged → Global Constraints + verified by `tsc` in Task 3 Step 5 (no App.tsx task because it already reads `state.fold.json`).
- Always send `display_json` (no branch) → Task 1 Step 3.
- Frontend type/reducer threading → Task 2.
- Viewer reads display copy with null-safety fallback → Task 3.
- Tests named in spec (server provenance guard, reducer stores displayJson, viewer loads display copy) → Task 1 Step 1, Task 2 Step 1, Task 3 Step 1.
- Out-of-scope items (#2/#3/#4/#5, squaring algorithm) → none touched; confirmed by leaving `square_complete.py` and the lint/compile path alone.

**Placeholder scan:** No TBD/TODO/"handle edge cases"/vague steps; every code step shows full code.

**Type consistency:** Wire key is `display_json` (snake_case) in Task 1 frame and Task 2 `Frame` type; state key is `displayJson` (camelCase) on `FoldArtifact` (Task 2) and read in `viewer.ts` (Task 3) — reducer maps one to the other in Task 2 Step 5. Consistent throughout.

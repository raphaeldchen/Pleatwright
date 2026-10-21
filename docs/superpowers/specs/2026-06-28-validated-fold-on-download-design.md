# Serve the validated hull on download (fix #1)

**Date:** 2026-06-28
**Status:** Approved — ready for implementation plan
**Scope:** Provenance fix only. Issues #2 (expected lint math), #3/#4 (deferred to A-9), and the squaring algorithm itself are explicitly out of scope.

## Problem

The IDE streams one `fold` frame per served compile (`web/server.py:104`). That frame carries `_square_for_display(fold)` — the hull crease pattern dressed up into a full square for the viewport. Both UI consumers read this single payload:

- the **Download .fold** button (`App.tsx:39`), and
- the **3D viewer** + JSON text tab.

But the agent's "Pass" verdict was computed on the **raw hull**, never on the square. Squaring is a display-only transform that even lints *worse* (10 → 19 violations — see `square_complete` design doc; this is expected boundary-edge math, not a bug, which is exactly why it must never re-enter the validation path). The consequence: **the file the user downloads is not the artifact that passed validation.** Re-linting the download in another tool surfaces violations the IDE never reported — a trust/provenance gap.

This is the only genuinely actionable problem of the five raised. It is also the cheapest: the squared and validated artifacts only need to be *routed* to different consumers.

## Relationship to A-9 and option 3 (why this fix is likely permanent, not a stopgap)

**Correction (2026-06-28):** an earlier draft of this section claimed "A-9 will move squaring into the compile path, so this fix is a stopgap reverted when A-9 lands." That conflated two distinct pieces of deferred work and is wrong.

This fix is retired only when the *validated* artifact and the *displayed/downloaded* artifact become the **same object** — i.e. when the **square itself** passes validation. Making the square validate is **option 3** (molecule-level corner-creasing: crease the corner regions with real M/V folds so the former hull-boundary vertices go even-degree and the full square lints clean). See design doc §8 of `2026-06-27-complete-square-export-design.md`. **Option 3 is recommended *against*** there: the spike (`probe_spike_kawasaki.py`) proved the base is already exactly flat-foldable (0.0000° at all 25 strictly-interior vertices); every violation is the hull-vs-square boundary artifact, so option 3 would be aesthetic-only and would partly contradict the (correct) A-3 ACCEPT decision.

**A-9 (the "generative anatomy-detail engine") does NOT retire this fix.** A-9 turns free-paper regions into *new tree nodes + edges* (detail flaps) and recompiles. But TreeMaker always creases the **convex hull of the leaf nodes**; A-9 changes *which* nodes exist, making the hull bigger and busier, but the output is still a leaf-node hull with uncreased corner paper outside it. So after A-9 the pipeline still validates a **hull** and still squares it for display → the downloaded-square ≠ validated-hull gap persists → this split is still needed. (If A-9's flaps happened to reach all four corners, squaring would be a no-op and `json == display_json`; the fix still works, just unexercised — a per-model accident, not structural retirement.)

We do this now because a live download misrepresenting validation ships today, and the split is cheap. Treat it as **likely permanent**; it is retired only if option 3 is ever built, which §8 advises against.

## Design

Split the single payload into two fields on the existing `fold` frame. Each consumer reads the artifact it actually needs.

```
extract_fold(output) -> raw hull   (validated; == what the agent linted)
                          |
   server builds ONE fold frame with TWO fields:
     json         = raw hull                       -> download + JSON tab
     display_json = _square_for_display(raw hull)  -> 3D viewer only
```

### Decisions (settled during brainstorming)

1. **JSON text tab shows the validated hull (matches download), not the square.**
   The JSON tab is conceptually a text preview of the exported artifact, so it must equal what Download produces. This also happens to be the least code: download and the JSON tab already read `state.fold.json`, so keeping `json` = the validated hull makes both correct with no rewiring. The only residual discrepancy is "the 3D *looks* square, but what you export is the validated hull" — which is the truth and is easy to label.

2. **The server always sends `display_json`, even when it equals `json`.**
   When the hull already fills the square (squaring is a no-op) or `_square_for_display` fails and returns its input unchanged, `display_json` will equal `json`. The server sends it anyway — one code path, no "did squaring change anything" branch to write now and unwind later. The few duplicate KB are irrelevant for a local single-user tool.

### Touch points

1. **`web/server.py` — `_send_frames`.**
   Send the raw fold as `json` and the squared copy as `display_json`:
   ```python
   fold = extract_fold(output)
   if fold is not None:
       await ws.send_json({"type": "fold", "filename": "model.fold",
                           "json": fold,
                           "display_json": _square_for_display(fold)})
   ```
   `_square_for_display` is unchanged (still fail-safe: returns input on any exception).

2. **`web/frontend/src/chat.ts` — types + reducer.**
   - Add `display_json: unknown` to the `fold` `Frame` variant.
   - Add `displayJson?: unknown` to `FoldArtifact`.
   - Reducer's `fold` case stores both: `{ filename, json, displayJson }`.

3. **`web/frontend/src/App.tsx` — consumers unchanged on the validated path.**
   `download()` and the JSON `<pre>` keep reading `state.fold.json` — now the validated hull, correct for free. No edits required beyond confirming this. The viewer continues to receive `state.fold`.

4. **`web/frontend/src/viewer.ts` — viewer renders the display copy.**
   `foldChanged` currently loads `fold.json`. Change it to prefer the display copy:
   `const data = fold.displayJson ?? fold.json;` then `loadFold(data)` / stash as `pending`.
   The `?? fold.json` is type null-safety for the optional field (and keeps existing test fixtures that omit `displayJson` valid), **not** a "did squaring change" branch — the server always sends the field in production.

   `OrigamiViewer.tsx` needs no change: it passes the whole `FoldArtifact` to the controller, which now reaches for `displayJson` internally.

## Testing

- **Server / `web/fold` test:** for a hull that does not fill the square, assert the emitted `fold` frame contains both `json` (equal to `extract_fold` output, the raw/validated artifact) and `display_json` (the squared copy), and that the two differ. This is the regression guard for the provenance gap.
- **`chat.test.ts`:** the reducer stores `displayJson` alongside `json` and `filename`.
- **`viewer.test.ts`:** when `displayJson` is present the controller loads it (the squared copy) rather than `json`; when absent it falls back to `json`.

## Out of scope

- Issue #2 — squaring lints 10 → 19. Expected boundary-edge math; documented; not a defect.
- Issues #3 / #4 — cosmetic-only corners and the hanging-crease render artifact. Both depend on real corner creases, deferred to A-9. The clean fix for #4 is a separate 2D crease-pattern panel, not a sim toggle (the `passiveEdgesVisible` toggle was already tried and rejected).
- Issue #5 — geometry edge cases already handled and tested in `square_complete` (`_snap_to_boundary`, radial cuts, fail-safe return).
- The squaring algorithm in `square_complete.py` is not modified.

## Reversal (only if option 3 is ever built)

This split is removed only if option 3 (molecule corner-creasing, §8 — currently recommended *against*) ever makes the squared FOLD the compiled+validated artifact. A-9 does **not** trigger this reversal (see "Relationship to A-9 and option 3" above). If that day comes: delete `display_json` from the server frame, `displayJson` from `chat.ts`, and the `?? fold.json` preference in `viewer.ts`; the viewer reads `fold.json` again, which by then is the real validated square. No migration, no entanglement.

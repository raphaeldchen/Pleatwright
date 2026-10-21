# Design: Embed Origami Simulator viewport (A-3 evidence)

**Date:** 2026-06-27
**Branch:** `feat/origami-viewport-embed`
**Status:** Approved design, pre-implementation
**Roadmap item:** Follow-up **1 / A-3** in `docs/followups-web-ui-and-foldability.md`.

## 1. Purpose

The web UI's result pane currently shows raw `.fold` JSON only; the Tier-1
"Powered by Origami Simulator" viewport in `CLAUDE.md` does not exist yet. We
need it to answer the open **A-3** product question:

> Do we **accept** uncreased paper (outside the leaf-node convex hull) as a valid
> flat-foldable result, or do we build an engine to **fill** it?

The decision hinges on physical evidence: does a hull-frontier base — which
Oriedita lints as **0 M/V-fixable, hull-boundary Kawasaki violations** — actually
fold cleanly? Embedding the real WebGL simulator both answers this *and* builds
the missing Tier-1 viewport, reusable for every future base.

Scope is **minimal evidence-grade**: embed the sim, load the current `.fold`,
scrub 0→100%. No M/V edge coloring, no camera-control chrome, no multi-user
concerns.

## 2. Background (verified facts)

From the upstream repo `amandaghassaei/OrigamiSimulator` (inspected 2026-06-27):

- **License:** MIT © 2018 Amanda Ghassaei — vendorable with attribution.
- **`?model=` URL param** (`js/main.js:70`) only loads files already present in
  the app's own `assets/` folder (it clicks a matching `.demo` anchor). It is
  **not** a generic loader for arbitrary blob URLs, so it cannot directly receive
  our streamed `.fold`.
- **Programmatic hooks exist:** `globals.pattern.setFoldData(foldObj, true)` loads
  a FOLD object; `globals.setCreasePercent(fraction)` drives the fold slider
  (fraction in [0,1]).
- `globals` is the app's central object, threaded through ~20 files; it is **not**
  exposed on `window`. Wiring our `.fold` in therefore requires a small patch.

This is why a pure zero-patch iframe (Approach A) and a deep native-React
extraction (Approach C) were both rejected in favor of **Approach B: vendored sim
+ a tiny `postMessage` bridge.**

## 3. Architecture & components

```
web/frontend/
  public/simulator/          ← vendored Origami Simulator (MIT), served same-origin
    index.html, js/, css/, dependencies/, assets/
    js/ide-bridge.js         ← OUR ~15-line patch (only file we author here)
    VENDOR.md                ← provenance, upstream commit, license, patch note
  src/
    OrigamiViewer.tsx        ← NEW: <iframe> wrapper + fold-% slider
    OrigamiViewer.test.tsx   ← NEW: unit tests for the message contract
    App.tsx                  ← MODIFIED: result pane gets a JSON / 3D toggle
```

Four well-bounded units, coupled only by a three-message contract:

- **Vendored simulator** — opaque GPU folding dependency. Untouched except for one
  appended script and `VENDOR.md`. Served same-origin so `postMessage`
  `targetOrigin` is the page origin and relative `assets/` load normally.
- **`ide-bridge.js`** (runs inside the iframe) — the only sim-side code we write.
  Appended after `main.js` so `globals` is in scope. Responsibilities:
  1. read `?embed=1` and hide the sim's own menu/import chrome via injected CSS;
  2. `postMessage({type:'ready'})` to the parent once the app is initialized;
  3. listen for `{type:'loadFold', fold}` → `globals.pattern.setFoldData(fold, true)`;
  4. listen for `{type:'setFold', percent}` → `globals.setCreasePercent(percent/100)`;
  5. wrap 3–4 in try/catch → `postMessage({type:'error', message})` on throw.
  Depends only on `globals`.
- **`OrigamiViewer.tsx`** (parent) — `<iframe src="/simulator/?embed=1">` + a
  0–100 range input. Interface: `<OrigamiViewer fold={state.fold} />`. Behavior:
  waits for `{ready}`, posts `{loadFold}` (queuing last-write-wins if `fold`
  arrives before `ready`), posts `{setFold}` on slider input, renders any
  `{error}` inline. All `postMessage` use `targetOrigin = window.location.origin`
  and ignore inbound messages whose `event.source` is not the iframe window.
  Depends only on the bridge contract.
- **`App.tsx`** — adds a JSON/3D toggle so the existing raw-`.fold` `<pre>`
  survives alongside the new viewer. Minimal change to the result `<section>`.

The parent↔iframe contract is the only coupling, keeping the heavy GPU app
swappable/upgradable behind a thin seam.

## 4. Data flow

```
agent run → WebSocket → state.fold (already in chat.ts)
   │
   ▼
<OrigamiViewer fold> mounts <iframe src="/simulator/?embed=1">
   │  iframe loads → ide-bridge.js runs → postMessage {ready}
   ▼
parent receives {ready} → postMessage {loadFold, fold.json}  (targetOrigin = own origin)
   │
   ▼  bridge: globals.pattern.setFoldData(fold, true) → app builds & relaxes the model
slider 0→100 → postMessage {setFold, percent} → globals.setCreasePercent(percent/100)
```

- **`?embed=1`** hides the sim's own chrome (CSS only; the app still runs fully).
  Fallback if hiding is fiddly: show the sim as-is — cosmetic, non-blocking.
- **Re-load on new prompt** — when `fold` changes, parent posts a fresh
  `loadFold`; no iframe reload. If `ready` hasn't arrived, parent queues the
  latest fold and sends on `ready` (last-write-wins).

## 5. Error handling (deliberately light — local single-user evidence tool)

| Case | Behavior |
|------|----------|
| No `.fold` yet | Viewer shows "No model — send a prompt." (mirrors JSON pane) |
| `fold.json` malformed / `setFoldData` throws | Bridge catches → posts `{error, message}`; viewer shows it inline; React app does not crash |
| Iframe never signals `ready` (~8s timeout) | Viewer shows "viewer failed to load — JSON still available." |
| WebGL/float-texture unsupported | Sim shows its own message; not special-cased |

No retry logic, no backpressure. YAGNI for a local tool.

## 6. The A-3 experiment (the deliverable for item 1)

1. **Generate a deterministic hull-frontier base** — run the pipeline with
   `MESH_PROVIDER=fake` on the bear/quadruped prompt to reproduce the documented
   signature (scale-optimized; 0 M/V-fixable; hull-boundary Kawasaki). Save as a
   committed fixture so the experiment repeats without API spend.
2. **Load it in the viewer, scrub 0→100%.**
3. **Decide with a crisp rule:**
   - *Folds to a stable base* (uncreased regions stay flat, creased hull collapses
     cleanly, no exploding/self-intersecting geometry) → Oriedita failures are
     **false-negatives** → **A-3 = "accept"**. Item 5 (generative fill) becomes
     optional aesthetic polish, not a correctness requirement.
   - *Fails to fold / tears / blows up* → uncreased paper genuinely breaks
     foldability → **A-3 = "fill"**. Item 5 becomes necessary.
4. **Record** verdict + screenshot in
   `docs/followups-web-ui-and-foldability.md` (resolving A-3 item 3), which gates
   item 5.

## 7. Testing strategy

The GPU folding cannot run in jsdom, so verification splits:

- **`OrigamiViewer.tsx`** — unit-tested (Vitest + jsdom) against a *mock* iframe
  `contentWindow`: posts `loadFold` only after `ready`; queues last-write-wins if
  fold arrives early; slider posts `setFold` with the right percent; `error`
  renders inline; ignores messages from foreign sources. Covers all *our* logic.
- **`App.tsx` toggle** — unit test: JSON and 3D panes switch correctly; existing
  chat tests stay green.
- **`ide-bridge.js`** — ~15 lines, runs only inside the real sim; verified
  manually during the A-3 run (we do not mock the whole GPU app — that tests the
  vendor, not us).
- **Folding behavior itself** — verified by the A-3 manual scrub. That observation
  *is* the item-1 deliverable.

Automated suite proves the plumbing; the manual scrub proves the physics and
answers the product question.

## 8. Out of scope (YAGNI)

- Mountain/valley edge coloring, camera-control UI, lighting options.
- Driving the sim's own export (STL/OBJ) — we already have `.fold` download.
- Multi-user / hosted concerns (queue backpressure is follow-up B-4).
- Making `find_free_paper` generative (item 5 / follow-up A-9) — gated on A-3.
- Bundling the sim through Vite's module graph; it ships as static `public/`
  assets loaded by its own `<script>` tags.

## 9. Open questions / risks

- **Sim boot time / float-texture support** in the dev browser — mitigated by the
  ~8s `ready` timeout fallback; the JSON pane always remains.
- **Chrome-hiding via `?embed=1`** may need iteration against the sim's actual DOM
  ids; fallback is to show it as-is.
- **Vendored asset size** (~a few MB incl. three.js/jQuery/shaders) — acceptable;
  recorded in `VENDOR.md`. Trim VR/video extras only if trivially safe.

# Origami Simulator Viewport Embed — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Embed the Origami Simulator WebGL viewport into the web UI so a streamed `.fold` can be folded 0→100%, and use it to answer the A-3 "accept vs fill uncreased paper" product question.

**Architecture:** Vendor the MIT Origami Simulator as same-origin static assets under `web/frontend/public/simulator/`. A ~20-line `ide-bridge.js` patch (running inside the iframe) exposes the app's `globals.pattern.setFoldData` / `globals.setCreasePercent` hooks via `postMessage`. A pure, framework-agnostic `viewer.ts` controller (node-tested, mirroring the repo's `chat.ts` pattern) owns the message protocol; a thin `OrigamiViewer.tsx` shell wires it to an `<iframe>` + fold-% slider; `App.tsx` gains a JSON/3D toggle.

**Tech Stack:** React 18 + TypeScript + Vite, Vitest (node environment), vanilla JS bridge, Origami Simulator (three.js + GPU GLSL solver, vendored).

## Global Constraints

- **Scope:** minimal evidence-grade. No M/V edge coloring, no camera-control chrome, no multi-user/hosted concerns, no Vite module-graph bundling of the sim (ships as static `public/` assets). (spec §1, §8)
- **License:** Origami Simulator is MIT © 2018 Amanda Ghassaei. Vendored copy MUST retain its `LICENSE` and record provenance in `public/simulator/VENDOR.md`. (spec §2)
- **Pinned upstream commit:** `7855983a613c879c171b2b1557f8cd102d2640cf` (amandaghassaei/OrigamiSimulator, 2025-11-20). (spec §2)
- **Same-origin only:** all `postMessage` calls use `targetOrigin = window.location.origin`; the parent ignores inbound messages whose `event.source` is not the iframe window or whose origin differs. (spec §3)
- **Message contract (the only coupling):** parent→iframe `{type:'loadFold', fold}` and `{type:'setFold', percent}` (percent 0–100); iframe→parent `{type:'ready'}` and `{type:'error', message}`. Bridge maps `setFold` percent→fraction via `percent/100` into `setCreasePercent`. (spec §3, §4)
- **Test pattern:** follow the existing repo convention — pure logic modules are unit-tested in the node Vitest environment (`chat.ts`/`chat.test.ts`); React shells (`App.tsx`) are thin and verified manually. Do NOT add jsdom/testing-library. (spec §7; existing `web/frontend`)
- **Fixture generation is offline:** use `MESH_PROVIDER=fake` — no network, no API spend. (spec §6)

---

### Task 1: Vendor the simulator + add the embed bridge

**Files:**
- Create (vendored tree): `web/frontend/public/simulator/**` (from pinned upstream)
- Create: `web/frontend/public/simulator/js/ide-bridge.js`
- Create: `web/frontend/public/simulator/VENDOR.md`
- Modify: `web/frontend/public/simulator/index.html` (append one `<script>` tag)

**Interfaces:**
- Consumes: nothing.
- Produces: a same-origin app at `/simulator/?embed=1` that, once booted, responds to `postMessage` per the Global Constraints message contract. `window.globals` (the app's global, declared `globals = {}` at `js/main.js:5`, reassigned in the jQuery-ready init) holds `.pattern.setFoldData(foldObj, true)` and `.setCreasePercent(fraction)`.

- [ ] **Step 1: Vendor the pinned static app**

```bash
cd web/frontend/public
git clone https://github.com/amandaghassaei/OrigamiSimulator.git simulator
cd simulator
git checkout 7855983a613c879c171b2b1557f8cd102d2640cf
rm -rf .git .github .gitignore CNAME   # static assets only; keep LICENSE
cd ../../../..
```

- [ ] **Step 2: Verify the app boots same-origin via Vite**

```bash
cd web/frontend && npm install && npm run dev    # serves public/ at /
```
Open `http://localhost:5173/simulator/` in a browser.
Expected: the Origami Simulator UI loads and the default waterbomb pattern appears (relative asset paths resolve under `/simulator/`). Stop the dev server (Ctrl-C) when confirmed.

- [ ] **Step 3: Write the embed bridge**

Create `web/frontend/public/simulator/js/ide-bridge.js`:

```javascript
// IDE embed bridge for Origami Simulator (added by AI-Driven-Origami-IDE).
// Exposes the app's load/fold hooks over postMessage and hides chrome when
// loaded with ?embed=1. The only file we author inside the vendored app.
(function () {
  "use strict";
  var ORIGIN = window.location.origin;
  var embed = /[?&]embed=1\b/.test(window.location.search);

  function emit(msg) { try { parent.postMessage(msg, ORIGIN); } catch (e) {} }

  if (embed) {
    var style = document.createElement("style");
    // Hide the sim's own navbar/menus/help so only the 3D canvas shows.
    style.textContent =
      "#navbar,#nav,.navbar,#header,#about,#helper,#controls,#flapsControls" +
      "{display:none!important} body{overflow:hidden!important}";
    (document.head || document.documentElement).appendChild(style);
  }

  window.addEventListener("message", function (e) {
    if (e.origin !== ORIGIN) return;
    var d = e.data || {};
    try {
      if (d.type === "loadFold") {
        window.globals.pattern.setFoldData(d.fold, true);
      } else if (d.type === "setFold") {
        window.globals.setCreasePercent((d.percent || 0) / 100);
      }
    } catch (err) {
      emit({ type: "error", message: String((err && err.message) || err) });
    }
  });

  // Signal readiness once the app's pattern machinery is initialized.
  (function waitReady() {
    var g = window.globals;
    if (g && g.pattern && typeof g.pattern.setFoldData === "function" &&
        typeof g.setCreasePercent === "function") {
      emit({ type: "ready" });
    } else {
      setTimeout(waitReady, 100);
    }
  })();
})();
```

- [ ] **Step 4: Load the bridge from index.html**

In `web/frontend/public/simulator/index.html`, find the `<script ... src="js/main.js">` tag (near the end of the body) and add immediately AFTER it:

```html
    <script type="text/javascript" src="js/ide-bridge.js"></script>
```

(It must come after `main.js` so `globals` is declared before the bridge polls it.)

- [ ] **Step 5: Record provenance**

Create `web/frontend/public/simulator/VENDOR.md`:

```markdown
# Vendored: Origami Simulator

- Upstream: https://github.com/amandaghassaei/OrigamiSimulator
- Pinned commit: 7855983a613c879c171b2b1557f8cd102d2640cf (2025-11-20)
- License: MIT © 2018 Amanda Ghassaei (see ./LICENSE)

## Local modifications
- Added `js/ide-bridge.js` — postMessage bridge for embedding (load FOLD,
  drive fold %, hide chrome with ?embed=1). The only authored file.
- `index.html`: one added `<script src="js/ide-bridge.js">` tag after main.js.
- Removed `.git`, `.github`, `CNAME` (static-asset deploy only).

To upgrade: re-clone at a newer commit, then re-apply the two changes above.
```

- [ ] **Step 6: Manually verify the bridge handshake**

Re-run `npm run dev`, open `http://localhost:5173/simulator/?embed=1`, open the browser console and run:

```js
window.addEventListener("message", e => console.log("from sim:", e.data));
// reload once with the listener installed, or re-open in an iframe; expect {type:"ready"}
globals.setCreasePercent(0.5);   // model should fold halfway
```
Expected: chrome is hidden, the canvas shows, and `setCreasePercent` visibly folds the demo model. Stop the server.

- [ ] **Step 7: Commit**

```bash
git add web/frontend/public/simulator
git commit -m "feat(web): vendor Origami Simulator (MIT) + embed postMessage bridge"
```

---

### Task 2: `viewer.ts` — pure message-protocol controller (TDD)

**Files:**
- Create: `web/frontend/src/viewer.ts`
- Test: `web/frontend/src/viewer.test.ts`

**Interfaces:**
- Consumes: the `FoldArtifact` shape from `chat.ts` (`{ filename: string; json: unknown }`).
- Produces:
  - `isTrustedMessage(event, expectedSource, expectedOrigin): boolean`
  - `createViewerController(opts: { post: (msg: Outbound) => void }): ViewerController`
  - Types: `Outbound = { type:'loadFold'; fold: unknown } | { type:'setFold'; percent: number }`;
    `Inbound = { type:'ready' } | { type:'error'; message: string }`;
    `ViewerState = { ready: boolean; error: string | null }`;
    `ViewerController = { foldChanged(fold: FoldArtifact | null): void; percentChanged(percent: number): void; receive(msg: Inbound): void; getState(): ViewerState }`.
  - Behavior contract: `foldChanged` posts `loadFold` immediately if `ready`, else stores it as pending (last-write-wins, not posted). `percentChanged` posts `setFold` only if `ready`. `receive({type:'ready'})` sets `ready=true`, clears `error`, and flushes any pending fold as a `loadFold`. `receive({type:'error',message})` sets `error=message`.

- [ ] **Step 1: Write the failing tests**

Create `web/frontend/src/viewer.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { createViewerController, isTrustedMessage } from "./viewer";

const fold = { filename: "m.fold", json: { vertices_coords: [[0, 0]] } };

describe("isTrustedMessage", () => {
  const src = {} as Window;
  it("accepts matching source and origin", () => {
    expect(isTrustedMessage({ source: src, origin: "http://x" }, src, "http://x")).toBe(true);
  });
  it("rejects foreign source", () => {
    expect(isTrustedMessage({ source: {} as Window, origin: "http://x" }, src, "http://x")).toBe(false);
  });
  it("rejects foreign origin", () => {
    expect(isTrustedMessage({ source: src, origin: "http://evil" }, src, "http://x")).toBe(false);
  });
});

describe("createViewerController", () => {
  it("queues fold until ready, then flushes on ready", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    c.foldChanged(fold);
    expect(post).not.toHaveBeenCalled();       // not ready yet
    c.receive({ type: "ready" });
    expect(post).toHaveBeenCalledWith({ type: "loadFold", fold: fold.json });
    expect(c.getState().ready).toBe(true);
  });

  it("posts loadFold immediately when already ready", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    c.receive({ type: "ready" });
    c.foldChanged(fold);
    expect(post).toHaveBeenLastCalledWith({ type: "loadFold", fold: fold.json });
  });

  it("keeps only the latest pending fold (last-write-wins)", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    c.foldChanged({ filename: "a", json: { a: 1 } });
    c.foldChanged(fold);
    c.receive({ type: "ready" });
    expect(post).toHaveBeenCalledTimes(1);
    expect(post).toHaveBeenCalledWith({ type: "loadFold", fold: fold.json });
  });

  it("posts setFold only when ready", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    c.percentChanged(50);
    expect(post).not.toHaveBeenCalled();
    c.receive({ type: "ready" });
    c.percentChanged(50);
    expect(post).toHaveBeenCalledWith({ type: "setFold", percent: 50 });
  });

  it("captures error messages and clears on ready", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    c.receive({ type: "error", message: "bad fold" });
    expect(c.getState().error).toBe("bad fold");
    c.receive({ type: "ready" });
    expect(c.getState().error).toBeNull();
  });

  it("does nothing on null fold", () => {
    const post = vi.fn();
    const c = createViewerController({ post });
    c.receive({ type: "ready" });
    c.foldChanged(null);
    expect(post).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd web/frontend && npx vitest run src/viewer.test.ts`
Expected: FAIL — `Cannot find module './viewer'`.

- [ ] **Step 3: Implement `viewer.ts`**

Create `web/frontend/src/viewer.ts`:

```typescript
import type { FoldArtifact } from "./chat";

export type Outbound =
  | { type: "loadFold"; fold: unknown }
  | { type: "setFold"; percent: number };

export type Inbound = { type: "ready" } | { type: "error"; message: string };

export interface ViewerState {
  ready: boolean;
  error: string | null;
}

export interface ViewerController {
  foldChanged(fold: FoldArtifact | null): void;
  percentChanged(percent: number): void;
  receive(msg: Inbound): void;
  getState(): ViewerState;
}

export function isTrustedMessage(
  event: { source: unknown; origin: string },
  expectedSource: unknown,
  expectedOrigin: string,
): boolean {
  return event.source === expectedSource && event.origin === expectedOrigin;
}

export function createViewerController(opts: {
  post: (msg: Outbound) => void;
}): ViewerController {
  let ready = false;
  let error: string | null = null;
  let pending: unknown | null = null; // latest fold.json awaiting readiness

  function loadFold(fold: unknown) {
    opts.post({ type: "loadFold", fold });
  }

  return {
    foldChanged(fold) {
      if (!fold) return;
      if (ready) loadFold(fold.json);
      else pending = fold.json;
    },
    percentChanged(percent) {
      if (ready) opts.post({ type: "setFold", percent });
    },
    receive(msg) {
      if (msg.type === "ready") {
        ready = true;
        error = null;
        if (pending !== null) {
          loadFold(pending);
          pending = null;
        }
      } else if (msg.type === "error") {
        error = msg.message;
      }
    },
    getState() {
      return { ready, error };
    },
  };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd web/frontend && npx vitest run src/viewer.test.ts`
Expected: PASS (9 tests).

- [ ] **Step 5: Confirm the whole frontend suite is still green**

Run: `cd web/frontend && npm test`
Expected: PASS (existing `chat.test.ts` + new `viewer.test.ts`).

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/viewer.ts web/frontend/src/viewer.test.ts
git commit -m "feat(web): viewer.ts message-protocol controller for the embedded sim"
```

---

### Task 3: Wire the viewport into the UI (`OrigamiViewer.tsx` + `App.tsx` toggle)

**Files:**
- Create: `web/frontend/src/OrigamiViewer.tsx`
- Modify: `web/frontend/src/App.tsx` (result `<section>`: add JSON/3D toggle, render viewer)
- Modify: `web/frontend/src/styles.css` (viewer + toggle styling)

**Interfaces:**
- Consumes: `createViewerController`, `isTrustedMessage` from `viewer.ts`; `FoldArtifact` from `chat.ts`; the booted `/simulator/?embed=1` app from Task 1.
- Produces: `<OrigamiViewer fold={state.fold} />` — a thin React shell (untested, per the repo pattern) that renders the iframe + a 0–100 fold slider and surfaces ready-timeout / error text.

- [ ] **Step 1: Implement `OrigamiViewer.tsx`**

Create `web/frontend/src/OrigamiViewer.tsx`:

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import type { FoldArtifact } from "./chat";
import { createViewerController, isTrustedMessage, type Inbound } from "./viewer";

const READY_TIMEOUT_MS = 8000;

export default function OrigamiViewer({ fold }: { fold: FoldArtifact | null }) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [percent, setPercent] = useState(0);
  const [, forceRender] = useState(0);
  const [timedOut, setTimedOut] = useState(false);

  const controller = useMemo(
    () =>
      createViewerController({
        post: (msg) =>
          iframeRef.current?.contentWindow?.postMessage(
            msg,
            window.location.origin,
          ),
      }),
    [],
  );

  // Inbound messages from the iframe bridge.
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      const win = iframeRef.current?.contentWindow;
      if (!isTrustedMessage(e, win, window.location.origin)) return;
      controller.receive(e.data as Inbound);
      if ((e.data as Inbound)?.type === "ready") setTimedOut(false);
      forceRender((n) => n + 1);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [controller]);

  // Push the current fold whenever it changes.
  useEffect(() => {
    controller.foldChanged(fold);
  }, [controller, fold]);

  // Ready timeout: if the sim never boots, fall back to the JSON pane.
  useEffect(() => {
    const t = setTimeout(() => {
      if (!controller.getState().ready) setTimedOut(true);
    }, READY_TIMEOUT_MS);
    return () => clearTimeout(t);
  }, [controller]);

  const { error } = controller.getState();

  return (
    <div className="viewer">
      {!fold && <p className="viewer-msg">No model — send a prompt.</p>}
      {fold && (
        <iframe
          ref={iframeRef}
          className="viewer-frame"
          title="Origami Simulator"
          src="/simulator/index.html?embed=1"
        />
      )}
      {fold && (
        <div className="viewer-controls">
          <label>
            fold {percent}%
            <input
              type="range"
              min={0}
              max={100}
              value={percent}
              onChange={(e) => {
                const p = Number(e.target.value);
                setPercent(p);
                controller.percentChanged(p);
              }}
            />
          </label>
        </div>
      )}
      {error && <p className="viewer-err">⚠ {error}</p>}
      {timedOut && (
        <p className="viewer-err">viewer failed to load — JSON still available.</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add the JSON/3D toggle to `App.tsx`**

In `web/frontend/src/App.tsx`, add the import near the top (after the existing imports):

```tsx
import { useState } from "react";   // already imported alongside others — ensure useState is present
import OrigamiViewer from "./OrigamiViewer";
```

Add a view-mode state inside `App()` next to the existing `draft` state:

```tsx
  const [view, setView] = useState<"json" | "3d">("json");
```

Replace the existing result `<section className="result"> … </section>` block with:

```tsx
      <section className="result">
        <div className="result-head">
          <h2>.fold output</h2>
          <div className="result-tabs">
            <button className={view === "json" ? "active" : ""}
              onClick={() => setView("json")}>JSON</button>
            <button className={view === "3d" ? "active" : ""}
              onClick={() => setView("3d")}>3D</button>
          </div>
          <button onClick={download} disabled={!state.fold}>Download .fold</button>
        </div>
        {view === "json" ? (
          <pre className="fold">
            {state.fold ? JSON.stringify(state.fold.json, null, 2)
                        : "No .fold yet — send a prompt."}
          </pre>
        ) : (
          <OrigamiViewer fold={state.fold} />
        )}
      </section>
```

- [ ] **Step 3: Add styles**

Append to `web/frontend/src/styles.css`:

```css
.result-tabs { display: inline-flex; gap: .25rem; margin: 0 .5rem; }
.result-tabs button { padding: .15rem .6rem; }
.result-tabs button.active { font-weight: 600; background: #e8e8e8; }
.viewer { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.viewer-frame { flex: 1; width: 100%; border: 0; background: #111; }
.viewer-controls { padding: .5rem .75rem; }
.viewer-controls input[type="range"] { width: 100%; }
.viewer-msg { padding: .75rem; color: #666; }
.viewer-err { padding: .5rem .75rem; color: #b00; }
```

- [ ] **Step 4: Typecheck and run the suite**

Run: `cd web/frontend && npx tsc --noEmit && npm test`
Expected: typecheck clean; all tests PASS (no new automated tests — `OrigamiViewer`/`App` are thin shells; protocol logic is covered by Task 2).

- [ ] **Step 5: Manual smoke**

Run `npm run dev`, open the app, switch to the **3D** tab. With no prompt yet it shows "No model — send a prompt." (Full fold verification happens in Task 4 with a real base.) Stop the server.

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/OrigamiViewer.tsx web/frontend/src/App.tsx web/frontend/src/styles.css
git commit -m "feat(web): embed Origami Simulator viewport with JSON/3D toggle + fold slider"
```

---

### Task 4: A-3 experiment — generate the hull-frontier base, fold it, record the verdict

**Files:**
- Create: `scripts/make_hull_frontier_fixture.py` (one-shot fixture generator)
- Create: `web/frontend/public/simulator/assets/ide/bear-base.fold` (committed artifact)
- Modify: `docs/followups-web-ui-and-foldability.md` (record A-3 verdict, resolving item 3)

**Interfaces:**
- Consumes: `mesh_acquire.query_to_metric_tree(prompt) -> MeshTreeResult(.nodes, .pairs)` (`mcp_harness/mesh_acquire.py:262`) and `server.draft_and_compile_full_base(nodes, pairs) -> str` (a `.fold` JSON string, or `"ERROR: …"`); both under `MESH_PROVIDER=fake` for an offline, deterministic base.
- Produces: a committed `.fold` exhibiting the hull-frontier signature, plus a written A-3 decision (accept vs fill) that gates roadmap item 5.

- [ ] **Step 1: Write the fixture generator**

Create `scripts/make_hull_frontier_fixture.py`:

```python
"""One-shot: produce a deterministic hull-frontier base .fold (offline, no API).

Reproduces the documented signature (scale-optimized; 0 M/V-fixable;
hull-boundary Kawasaki) for the A-3 viewport experiment. Run once; commit the
output. See docs/superpowers/specs/2026-06-27-origami-viewport-embed-design.md.
"""
import os
import sys

os.environ.setdefault("MESH_PROVIDER", "fake")  # offline fixture, no spend
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mcp_harness"))

import mesh_acquire  # noqa: E402
import server        # noqa: E402

OUT = os.path.join(
    HERE, "..", "web", "frontend", "public", "simulator", "assets", "ide",
    "bear-base.fold",
)


def main() -> int:
    res = mesh_acquire.query_to_metric_tree("bear")  # fake -> quadruped fixture
    fold = server.draft_and_compile_full_base(res.nodes, res.pairs)
    if fold.startswith("ERROR:") or '"vertices_coords"' not in fold:
        print("compile did not yield a FOLD:\n", fold[:500], file=sys.stderr)
        return 1
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(fold)
    print("wrote", os.path.relpath(OUT))
    print("confirmed packable:", res.confirmed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Generate the fixture**

Run: `python scripts/make_hull_frontier_fixture.py`
Expected: prints `wrote web/frontend/public/simulator/assets/ide/bear-base.fold` and a `confirmed packable:` line. The file contains `"vertices_coords"`.
(If `query_to_metric_tree`'s closed-loop search is slow, that's fine — it's a one-time generation. If it errors on import paths, confirm you ran from the repo root.)

- [ ] **Step 3: Fold it in the viewport and observe**

Run `cd web/frontend && npm run dev`. In a second terminal load the base into the running sim without needing the agent: open `http://localhost:5173/simulator/index.html?embed=1`, then in the browser console:

```js
fetch("/simulator/assets/ide/bear-base.fold").then(r => r.json())
  .then(fold => globals.pattern.setFoldData(fold, true));
// then scrub:
globals.setCreasePercent(0);   // flat
globals.setCreasePercent(0.5); // halfway
globals.setCreasePercent(1.0); // fully folded
```

Observe across 0→1: do the **uncreased regions outside the leaf hull stay flat** while the creased hull collapses, producing a coherent base **without exploding/self-intersecting geometry**? Take a screenshot at ~100%.

- [ ] **Step 4: Record the A-3 verdict**

Edit `docs/followups-web-ui-and-foldability.md`, item **A-3 (3)**. Append a dated resolution using this exact decision rule (fill in the observed outcome):

```markdown
**Resolved 2026-06-27 (viewport experiment, `bear-base.fold`):** <FOLDS CLEANLY |
FAILS>. Decision rule applied — folds to a stable base with uncreased regions
staying flat ⇒ Oriedita hull-boundary Kawasaki failures are **false-negatives**
⇒ **ACCEPT** uncreased paper as valid; item 5 (generative fill) is optional
aesthetic polish, not a correctness fix. (If it failed instead: uncreased paper
breaks foldability ⇒ **FILL** ⇒ item 5 is necessary.) See screenshot
<path/to/screenshot>.
```

Replace `<FOLDS CLEANLY | FAILS>` and the parenthetical with the branch that actually occurred, and link the screenshot.

- [ ] **Step 5: Commit**

```bash
git add scripts/make_hull_frontier_fixture.py \
        web/frontend/public/simulator/assets/ide/bear-base.fold \
        docs/followups-web-ui-and-foldability.md
git commit -m "feat(web): A-3 hull-frontier base fixture + recorded accept/fill verdict"
```

---

## Self-Review

**Spec coverage:**
- §1 purpose / minimal scope → Global Constraints + Task 3 (toggle keeps JSON), Task 4 (A-3). ✓
- §2 verified facts (MIT, `?model=` limits, `globals` hooks, pinned commit) → Task 1 + Constraints. ✓
- §3 components (vendored sim, `ide-bridge.js`, `OrigamiViewer.tsx`, `App.tsx`) → Tasks 1–3. ✓
- §4 data flow (ready/queue/last-write-wins, `?embed=1`, re-load on change) → Task 2 controller + Task 3 shell. ✓
- §5 error handling (no fold, malformed→error, ready timeout) → Task 3 (`viewer-msg`, `viewer-err`, `READY_TIMEOUT_MS`) + bridge try/catch in Task 1. ✓
- §6 A-3 experiment (fake provider, decision rule, record verdict) → Task 4. ✓
- §7 testing (pure controller node-tested; shells + folding manual) → Task 2 tests; Tasks 1/3/4 manual. ✓
- §8 out-of-scope respected (no coloring/camera/bundling/server.py change). ✓

**Deliberate deviation from spec §7:** the spec mentioned a unit test for the App toggle. The repo has no jsdom/testing-library and keeps React shells untested (`App.tsx`), testing only pure logic (`chat.ts`). Adding a DOM test harness for a one-boolean toggle violates YAGNI and the established pattern, so the toggle is verified manually (Task 3 Step 5). All non-trivial protocol logic is still unit-tested via `viewer.ts` (Task 2).

**Placeholder scan:** none — every code/file/command step is concrete. The only intentional fill-in is the A-3 *outcome* in Task 4 Step 4, which is an observed experimental result, not a plan placeholder.

**Type consistency:** `loadFold`/`setFold`/`ready`/`error` message types, `setFoldData(fold, true)`, `setCreasePercent(percent/100)`, `createViewerController({post})`, `foldChanged`/`percentChanged`/`receive`/`getState`, and `FoldArtifact.{filename,json}` are used identically across the bridge (Task 1), controller (Task 2), and shell (Task 3). ✓

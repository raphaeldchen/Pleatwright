# CAD-Quality Physical-Paper Render (A1–A3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new "Model" tab that shows the model as a clean, thick-paper, lit, orbit-able 3D object — the "CAD software" finished-look — rendered in a scene we own.

**Architecture:** Drive the vendored Origami Simulator offscreen to a 3D pose and read its converged folded vertex positions once (honest reuse of the proven solver). A pure function thickens that triangle mesh into a per-face solid (no layer ordering). A react-three-fiber scene we own renders it with PBR paper, lighting, soft shadows, and orbit controls.

**Tech Stack:** TypeScript, React 18, Vite, Vitest (pure-logic tests), three.js + @react-three/fiber + @react-three/drei. The vendored MIT Origami Simulator stays as-is except one bridge handler.

## Global Constraints

- React 18.3 / Vite 5 / Vitest 2 frontend in `web/frontend/`. Run tests with `npm test` (= `vitest run`) from `web/frontend/`.
- Follow the existing test pattern: **pure logic lives in its own module and is unit-tested in the node env (no DOM); React components are thin, untested shells** (e.g. `viewer.ts` is tested, `OrigamiViewer.tsx` is not).
- **Honest geometry only:** geometry shown must come from the validated fold via the proven solver. No invented coordinates, no reference-mesh swap.
- **No global layer ordering** in this sub-project. Thickness is a per-face shell on a 3D-separated pose.
- **Exactly one edit to the vendored sim** (`ide-bridge.js`), consistent with its existing "only file we author inside the vendored app" comment.
- Pose is a single module constant `DEFAULT_POSE_PERCENT = 90` (a fold %), not a UI slider.
- M/V crease-edge overlay (A4) is **out of scope** here — `buildShell` produces the solid only.

---

### Task 1: `buildShell` — pure per-face thickening

**Files:**
- Create: `web/frontend/src/shell.ts`
- Test: `web/frontend/src/shell.test.ts`

**Interfaces:**
- Consumes: nothing (pure).
- Produces:
  - `interface RawMesh { positions: number[][]; faces: number[][]; }` (positions are Nx3 folded coords; faces are triangles of vertex indices)
  - `interface ShellMesh { positions: Float32Array; normals: Float32Array; }`
  - `function buildShell(mesh: RawMesh, thickness: number): ShellMesh`
  - Each input triangle becomes a triangular prism: front face (+½·thickness along the face normal), reversed back face (−½·thickness), and 3 side quads — 8 output triangles. A degenerate (near-zero-area) triangle falls back to a zero-thickness front+back pair (2 triangles) and never throws.

- [ ] **Step 1: Write the failing test**

```typescript
// web/frontend/src/shell.test.ts
import { describe, it, expect } from "vitest";
import { buildShell, type RawMesh } from "./shell";

const tri: RawMesh = {
  positions: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
  faces: [[0, 1, 2]],
};

describe("buildShell", () => {
  it("turns one triangle into an 8-triangle prism", () => {
    const s = buildShell(tri, 0.1);
    // 8 triangles * 3 verts * 3 coords
    expect(s.positions.length).toBe(8 * 3 * 3);
    expect(s.normals.length).toBe(8 * 3 * 3);
  });

  it("offsets front and back by half the thickness along the normal", () => {
    const s = buildShell(tri, 0.1);
    // First triangle is the front face (z = +0.05); collect its 3 z coords.
    const frontZ = [s.positions[2], s.positions[5], s.positions[8]];
    expect(frontZ.every((z) => Math.abs(z - 0.05) < 1e-9)).toBe(true);
    // Front normal points +z.
    expect(Math.abs(s.normals[2] - 1)).toBeLessThan(1e-9);
  });

  it("falls back to a zero-thickness pair on a degenerate triangle", () => {
    const degenerate: RawMesh = {
      positions: [[0, 0, 0], [0, 0, 0], [1, 1, 1]],
      faces: [[0, 1, 2]],
    };
    const s = buildShell(degenerate, 0.1);
    expect(s.positions.length).toBe(2 * 3 * 3); // front + back only, no throw
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/frontend && npm test -- shell`
Expected: FAIL — `buildShell` not found / module `./shell` missing.

- [ ] **Step 3: Write minimal implementation**

```typescript
// web/frontend/src/shell.ts
export interface RawMesh {
  positions: number[][]; // Nx3 folded coordinates
  faces: number[][];     // triangles of vertex indices
}

export interface ShellMesh {
  positions: Float32Array;
  normals: Float32Array;
}

type V3 = [number, number, number];

const sub = (a: V3, b: V3): V3 => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const add = (a: V3, b: V3): V3 => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const scale = (a: V3, s: number): V3 => [a[0] * s, a[1] * s, a[2] * s];
const cross = (a: V3, b: V3): V3 => [
  a[1] * b[2] - a[2] * b[1],
  a[2] * b[0] - a[0] * b[2],
  a[0] * b[1] - a[1] * b[0],
];
const len = (a: V3): number => Math.hypot(a[0], a[1], a[2]);

function normal(a: V3, b: V3, c: V3): V3 | null {
  const n = cross(sub(b, a), sub(c, a));
  const l = len(n);
  if (l < 1e-12) return null; // degenerate
  return [n[0] / l, n[1] / l, n[2] / l];
}

export function buildShell(mesh: RawMesh, thickness: number): ShellMesh {
  const pos: number[] = [];
  const nrm: number[] = [];
  const h = thickness / 2;

  const pushTri = (p: V3, q: V3, r: V3) => {
    const n = normal(p, q, r) ?? [0, 0, 1];
    for (const v of [p, q, r]) {
      pos.push(v[0], v[1], v[2]);
      nrm.push(n[0], n[1], n[2]);
    }
  };

  for (const f of mesh.faces) {
    const a = mesh.positions[f[0]] as V3;
    const b = mesh.positions[f[1]] as V3;
    const c = mesh.positions[f[2]] as V3;
    const n = normal(a, b, c);

    if (!n) {
      // Degenerate: emit a flat front+back pair, never throw.
      pushTri(a, b, c);
      pushTri(c, b, a);
      continue;
    }

    const off = scale(n, h);
    const af = add(a, off), bf = add(b, off), cf = add(c, off); // front
    const ab = sub(a, off), bb = sub(b, off), cb = sub(c, off); // back

    pushTri(af, bf, cf);       // front (+n)
    pushTri(cb, bb, ab);       // back (reversed, -n)

    // 3 side quads (front edge -> back edge), each as 2 triangles.
    const edges: [V3, V3, V3, V3][] = [
      [af, bf, bb, ab],
      [bf, cf, cb, bb],
      [cf, af, ab, cb],
    ];
    for (const [p0, p1, p2, p3] of edges) {
      pushTri(p0, p1, p2);
      pushTri(p0, p2, p3);
    }
  }

  return { positions: new Float32Array(pos), normals: new Float32Array(nrm) };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/frontend && npm test -- shell`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/shell.ts web/frontend/src/shell.test.ts
git commit -m "feat(cad): pure per-face shell thickening (A2)"
```

---

### Task 2: `createExtractionController` — offscreen-extraction protocol

**Files:**
- Create: `web/frontend/src/extraction.ts`
- Test: `web/frontend/src/extraction.test.ts`

**Interfaces:**
- Consumes: `RawMesh` from `./shell`.
- Produces:
  - `type ExtractOutbound = { type: "loadFold"; fold: unknown } | { type: "setFold"; percent: number } | { type: "getFoldedGeometry" }`
  - `type ExtractInbound = { type: "ready" } | { type: "foldedGeometry"; vertices_coords: number[][]; faces_vertices: number[][] } | { type: "error"; message: string }`
  - `function createExtractionController(opts: { post: (m: ExtractOutbound) => void; settle: (fn: () => void) => void; posePercent: number }): { start(fold: unknown): Promise<RawMesh>; receive(msg: ExtractInbound): void; }`
  - Flow: `start` waits for `ready`, then posts `loadFold` + `setFold(posePercent)`, then on `settle` posts `getFoldedGeometry`. Resolves the promise with `{ positions, faces }` from a finite `foldedGeometry`; rejects on non-finite geometry or an `error` message.

- [ ] **Step 1: Write the failing test**

```typescript
// web/frontend/src/extraction.test.ts
import { describe, it, expect, vi } from "vitest";
import { createExtractionController } from "./extraction";

function make() {
  const post = vi.fn();
  let settleFn: (() => void) | null = null;
  const c = createExtractionController({
    post,
    settle: (fn) => { settleFn = fn; },
    posePercent: 90,
  });
  return { post, c, runSettle: () => settleFn?.() };
}

describe("createExtractionController", () => {
  it("loads, poses, and requests geometry after ready + settle", async () => {
    const { post, c, runSettle } = make();
    const p = c.start({ k: 1 });
    expect(post).not.toHaveBeenCalled();      // waits for ready
    c.receive({ type: "ready" });
    expect(post).toHaveBeenCalledWith({ type: "loadFold", fold: { k: 1 } });
    expect(post).toHaveBeenCalledWith({ type: "setFold", percent: 90 });
    runSettle();
    expect(post).toHaveBeenCalledWith({ type: "getFoldedGeometry" });
    c.receive({
      type: "foldedGeometry",
      vertices_coords: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
      faces_vertices: [[0, 1, 2]],
    });
    await expect(p).resolves.toEqual({
      positions: [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
      faces: [[0, 1, 2]],
    });
  });

  it("rejects on non-finite geometry", async () => {
    const { c, runSettle } = make();
    const p = c.start({});
    c.receive({ type: "ready" });
    runSettle();
    c.receive({
      type: "foldedGeometry",
      vertices_coords: [[0, NaN, 0]],
      faces_vertices: [[0, 0, 0]],
    });
    await expect(p).rejects.toThrow(/non-finite/);
  });

  it("rejects on an error message", async () => {
    const { c } = make();
    const p = c.start({});
    c.receive({ type: "error", message: "boom" });
    await expect(p).rejects.toThrow(/boom/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd web/frontend && npm test -- extraction`
Expected: FAIL — module `./extraction` / `createExtractionController` missing.

- [ ] **Step 3: Write minimal implementation**

```typescript
// web/frontend/src/extraction.ts
import type { RawMesh } from "./shell";

export type ExtractOutbound =
  | { type: "loadFold"; fold: unknown }
  | { type: "setFold"; percent: number }
  | { type: "getFoldedGeometry" };

export type ExtractInbound =
  | { type: "ready" }
  | { type: "foldedGeometry"; vertices_coords: number[][]; faces_vertices: number[][] }
  | { type: "error"; message: string };

export interface ExtractionController {
  start(fold: unknown): Promise<RawMesh>;
  receive(msg: ExtractInbound): void;
}

function allFinite(rows: number[][]): boolean {
  return rows.every((r) => r.every((n) => Number.isFinite(n)));
}

export function createExtractionController(opts: {
  post: (m: ExtractOutbound) => void;
  settle: (fn: () => void) => void;
  posePercent: number;
}): ExtractionController {
  let ready = false;
  let pendingFold: { fold: unknown } | null = null;
  let resolveMesh: ((m: RawMesh) => void) | null = null;
  let rejectMesh: ((e: Error) => void) | null = null;

  function begin(fold: unknown) {
    opts.post({ type: "loadFold", fold });
    opts.post({ type: "setFold", percent: opts.posePercent });
    opts.settle(() => opts.post({ type: "getFoldedGeometry" }));
  }

  return {
    start(fold) {
      return new Promise<RawMesh>((resolve, reject) => {
        resolveMesh = resolve;
        rejectMesh = reject;
        if (ready) begin(fold);
        else pendingFold = { fold };
      });
    },
    receive(msg) {
      if (msg.type === "ready") {
        ready = true;
        if (pendingFold) {
          const { fold } = pendingFold;
          pendingFold = null;
          begin(fold);
        }
      } else if (msg.type === "foldedGeometry") {
        if (!allFinite(msg.vertices_coords)) {
          rejectMesh?.(new Error("non-finite geometry from solver"));
          return;
        }
        resolveMesh?.({ positions: msg.vertices_coords, faces: msg.faces_vertices });
      } else if (msg.type === "error") {
        rejectMesh?.(new Error(msg.message));
      }
    },
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd web/frontend && npm test -- extraction`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add web/frontend/src/extraction.ts web/frontend/src/extraction.test.ts
git commit -m "feat(cad): offscreen folded-geometry extraction controller (A1)"
```

---

### Task 3: `getFoldedGeometry` bridge handler

**Files:**
- Modify: `web/frontend/public/simulator/js/ide-bridge.js`

**Interfaces:**
- Consumes: the `ExtractOutbound` `{ type: "getFoldedGeometry" }` message from Task 2.
- Produces: an `ExtractInbound` `{ type: "foldedGeometry", vertices_coords, faces_vertices }` message — positions and triangle indices read from one self-consistent `globals.model.getGeometry()` buffer geometry (the same converged folded mesh `saveFOLD.js` exports).

**Note on verification:** `ide-bridge.js` runs inside the vendored sim iframe and is not imported by Vitest (like the existing bridge code, it has no unit test). Verify it manually via the integration check in Step 3.

- [ ] **Step 1: Add the handler to the message switch**

In `web/frontend/public/simulator/js/ide-bridge.js`, locate the `window.addEventListener("message", ...)` switch (currently handling `"loadFold"` and `"setFold"`) and add a third branch before the closing `}` of the `try`:

```javascript
      } else if (d.type === "getFoldedGeometry") {
        // Read the converged folded mesh from the solver's geometry — the same
        // source saveFOLD.js uses. Positions and faces come from ONE buffer
        // geometry so their index spaces are self-consistent.
        var bufferGeo = window.globals.model.getGeometry();
        var posAttr = bufferGeo.attributes.position.array;
        var idx = bufferGeo.index ? bufferGeo.index.array : null;
        var verts = [];
        for (var i = 0; i < posAttr.length; i += 3) {
          verts.push([posAttr[i], posAttr[i + 1], posAttr[i + 2]]);
        }
        var faces = [];
        if (idx) {
          for (var j = 0; j < idx.length; j += 3) {
            faces.push([idx[j], idx[j + 1], idx[j + 2]]);
          }
        } else {
          for (var k = 0; k < verts.length; k += 3) {
            faces.push([k, k + 1, k + 2]);
          }
        }
        emit({ type: "foldedGeometry", vertices_coords: verts, faces_vertices: faces });
      }
```

- [ ] **Step 2: Type-check the build**

Run: `cd web/frontend && npm run build`
Expected: PASS (the bridge is plain JS; this just confirms nothing else broke).

- [ ] **Step 3: Manual integration check**

Run: `cd web/frontend && npm run dev`, open the app, send a prompt that yields a `.fold`, then in the simulator iframe's devtools console run:

```javascript
window.postMessage({ type: "getFoldedGeometry" }, window.location.origin);
```

Expected: a `message` event with `type: "foldedGeometry"` whose `vertices_coords` has > 0 rows of 3 finite numbers and `faces_vertices` has > 0 triangles. (This confirms the accessor before the real consumer in Task 4.)

- [ ] **Step 4: Commit**

```bash
git add web/frontend/public/simulator/js/ide-bridge.js
git commit -m "feat(cad): bridge handler returning converged folded geometry (A1)"
```

---

### Task 4: `CADViewer` component, deps, and "Model" tab

**Files:**
- Modify: `web/frontend/package.json` (add deps via npm install)
- Create: `web/frontend/src/CADViewer.tsx`
- Modify: `web/frontend/src/App.tsx` (add the "model" view + tab + render)
- Modify: `web/frontend/src/styles.css` (canvas sizing)

**Interfaces:**
- Consumes: `buildShell` + `RawMesh`/`ShellMesh` from `./shell`; `createExtractionController` + message types from `./extraction`; `FoldArtifact` from `./chat`.
- Produces: `export default function CADViewer({ fold }: { fold: FoldArtifact | null }): JSX.Element` — a thin shell (untested, like `OrigamiViewer.tsx`): hosts a hidden sim iframe, runs the extraction controller, thickens with `buildShell`, and renders the result in a react-three-fiber scene with PBR paper, lighting, soft shadows, a ground plane, and orbit controls.

**Note on verification:** Like `OrigamiViewer.tsx`, this React shell is verified by the TypeScript build + manual run, not a unit test. The testable logic already lives in Tasks 1–2.

- [ ] **Step 1: Install the 3D dependencies**

Run:

```bash
cd web/frontend && npm install three@^0.169.0 @react-three/fiber@^8.17.10 @react-three/drei@^9.114.0 && npm install -D @types/three@^0.169.0
```

Expected: `package.json` gains `three`, `@react-three/fiber`, `@react-three/drei` (deps) and `@types/three` (devDep).

- [ ] **Step 2: Create the component**

```tsx
// web/frontend/src/CADViewer.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows } from "@react-three/drei";
import * as THREE from "three";
import type { FoldArtifact } from "./chat";
import { buildShell, type ShellMesh } from "./shell";
import {
  createExtractionController,
  type ExtractInbound,
  type ExtractOutbound,
} from "./extraction";

const DEFAULT_POSE_PERCENT = 90;
const SETTLE_MS = 1500;   // let the mass-spring solver relax before reading
const THICKNESS = 0.01;   // paper thickness in fold units

function Paper({ shell }: { shell: ShellMesh }) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(shell.positions, 3));
    g.setAttribute("normal", new THREE.BufferAttribute(shell.normals, 3));
    g.computeBoundingSphere();
    return g;
  }, [shell]);

  // Recenter so OrbitControls frames the model.
  const center = useMemo(() => {
    const c = geometry.boundingSphere?.center ?? new THREE.Vector3();
    return [-c.x, -c.y, -c.z] as [number, number, number];
  }, [geometry]);

  return (
    <group position={center}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshStandardMaterial
          color="#e9e2d0"
          roughness={0.85}
          metalness={0}
          side={THREE.DoubleSide}
        />
      </mesh>
    </group>
  );
}

export default function CADViewer({ fold }: { fold: FoldArtifact | null }) {
  const iframeRef = useRef<HTMLIFrameElement | null>(null);
  const [shell, setShell] = useState<ShellMesh | null>(null);
  const [error, setError] = useState<string | null>(null);

  const controller = useMemo(
    () =>
      createExtractionController({
        post: (m: ExtractOutbound) =>
          iframeRef.current?.contentWindow?.postMessage(m, window.location.origin),
        settle: (fn) => window.setTimeout(fn, SETTLE_MS),
        posePercent: DEFAULT_POSE_PERCENT,
      }),
    [],
  );

  // Inbound messages from the hidden sim iframe.
  useEffect(() => {
    function onMessage(e: MessageEvent) {
      const win = iframeRef.current?.contentWindow;
      if (e.source !== win || e.origin !== window.location.origin) return;
      controller.receive(e.data as ExtractInbound);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, [controller]);

  // Extract + thicken whenever the fold changes.
  useEffect(() => {
    setShell(null);
    setError(null);
    if (!fold) return;
    const data = fold.displayJson ?? fold.json;
    let cancelled = false;
    controller
      .start(data)
      .then((raw) => { if (!cancelled) setShell(buildShell(raw, THICKNESS)); })
      .catch((err: Error) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [controller, fold]);

  return (
    <div className="cad">
      {!fold && <p className="viewer-msg">No model — send a prompt.</p>}
      {fold && (
        <iframe
          ref={iframeRef}
          className="cad-extractor"
          title="folded-geometry extractor"
          src="/simulator/index.html?embed=1"
          style={{ display: "none" }}
        />
      )}
      {fold && !shell && !error && <p className="viewer-msg">Building model…</p>}
      {error && <p className="viewer-err">⚠ {error}</p>}
      {shell && (
        <Canvas shadows camera={{ position: [2, 1.5, 2], fov: 45 }}>
          <color attach="background" args={["#2a2d34"]} />
          <ambientLight intensity={0.4} />
          <directionalLight position={[3, 5, 2]} intensity={1.1} castShadow />
          <Paper shell={shell} />
          <ContactShadows position={[0, -1, 0]} opacity={0.5} blur={2} />
          <Environment preset="studio" />
          <OrbitControls enableDamping />
        </Canvas>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Add canvas sizing CSS**

Append to `web/frontend/src/styles.css`:

```css
.cad { width: 100%; height: 100%; position: relative; }
.cad-extractor { width: 1px; height: 1px; border: 0; }
.cad canvas { width: 100% !important; height: 100% !important; display: block; }
```

- [ ] **Step 4: Wire the "Model" tab into App.tsx**

In `web/frontend/src/App.tsx`:

1. Add the import after the `CreasePanel` import:

```tsx
import CADViewer from "./CADViewer";
```

2. Widen the view state union:

```tsx
const [view, setView] = useState<"json" | "2d" | "3d" | "model">("json");
```

3. Add a tab button after the `3d` button:

```tsx
<button className={view === "model" ? "active" : ""}
  onClick={() => setView("model")}>Model</button>
```

4. Add a render branch — change the final `) : (` / `<OrigamiViewer .../>` block so the chain ends:

```tsx
        ) : view === "3d" ? (
          <OrigamiViewer fold={state.fold} />
        ) : (
          <CADViewer fold={state.fold} />
        )}
```

- [ ] **Step 5: Type-check and build**

Run: `cd web/frontend && npm run build`
Expected: PASS — `tsc` clean, Vite build succeeds.

- [ ] **Step 6: Manual run check**

Run: `cd web/frontend && npm run dev`, send a prompt that yields a `.fold`, click the **Model** tab.
Expected: after a short "Building model…", a thick, lit, orbit-able paper object appears; dragging rotates it; no console errors.

- [ ] **Step 7: Run the full frontend test suite**

Run: `cd web/frontend && npm test`
Expected: PASS — all existing tests plus `shell` (3) and `extraction` (3).

- [ ] **Step 8: Commit**

```bash
git add web/frontend/package.json web/frontend/package-lock.json web/frontend/src/CADViewer.tsx web/frontend/src/App.tsx web/frontend/src/styles.css
git commit -m "feat(cad): CAD-quality Model tab — lit thick-paper r3f render (A3)"
```

---

## Self-Review

**Spec coverage:**
- A1 (stable geometry extraction) → Task 2 (controller) + Task 3 (bridge accessor). ✓
- A2 (thickness, per-face shell, no layer ordering) → Task 1 (`buildShell`). ✓
- A3 (materials/lighting, fresh r3f scene we own, new tab) → Task 4. ✓
- Decision "reuse solver output" → Task 3 reads `globals.model.getGeometry()`. ✓
- Decision "3D pose + simple shell" → `DEFAULT_POSE_PERCENT = 90` + `buildShell`. ✓
- Decision "fresh scene we own" → Task 4 r3f scene, sim only as hidden extractor. ✓
- Error handling (§7): non-finite → reject (Task 2); degenerate face → fallback (Task 1); error surfaced in tab (Task 4). ✓
- Out of scope honored: no layer ordering, no shaping, Simulator tab untouched, pose is a constant, M/V overlay deferred to A4. ✓

**Placeholder scan:** No TBD/TODO; every code step is complete. The one manual step (Task 3 Step 3 / Task 4 Step 6) is an integration check with an exact command and expected result, not a placeholder.

**Type consistency:** `RawMesh` defined in Task 1, consumed in Tasks 2 & 4. `ShellMesh` (Task 1) consumed in Task 4. `ExtractOutbound`/`ExtractInbound` defined in Task 2, consumed by the bridge (Task 3) and component (Task 4). `createExtractionController` signature matches between Task 2 definition and Task 4 use. `buildShell(mesh, thickness)` signature consistent. ✓

**Known follow-ups (not blockers):** A4 M/V crease-edge overlay; energy-based convergence (currently a fixed `SETTLE_MS`); exposing pose in the UI; tuning `THICKNESS`/`SETTLE_MS` against real models during the Task 4 manual check.

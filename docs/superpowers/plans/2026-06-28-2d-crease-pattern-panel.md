# 2D Crease-Pattern Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a third "2D" result tab that renders the raw validated hull (`state.fold.json`) as an SVG crease pattern colored by mountain/valley/border/flat assignment.

**Architecture:** A pure, DOM-free builder (`creasePattern.ts`) turns a FOLD dict into normalized, Y-flipped SVG line segments with per-assignment styling; a thin presentational component (`CreasePattern.tsx`) renders those segments as `<line>`s plus a legend; `App.tsx` gains a `"2d"` tab. Mirrors the existing `viewer.ts` (pure) / `OrigamiViewer.tsx` (thin) split so the geometry math is unit-testable without a DOM.

**Tech Stack:** React + TypeScript, vitest. Inline SVG (no new dependencies).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-28-2d-crease-pattern-panel-design.md`.
- Renders `state.fold.json` (raw validated hull), NEVER `displayJson`.
- SVG constants: `SIZE = 100`, `PAD = 4`, viewBox always `"0 0 100 100"`.
- FOLD is y-up, SVG is y-down → segments MUST flip Y: `y_svg = SIZE - ny_up`.
- Assignment → style table (uppercase the assignment; unknown/missing → `"U"`):
  - `M` mountain → color `#d33`, solid
  - `V` valley → color `#36c`, dashed (`strokeDasharray` `"4 3"`); V is the ONLY dashed kind
  - `B` border → color `#444`, solid
  - `F` flat → color `#ccc`, solid
  - `U`/missing → color `#bbb`, solid
- `buildCreaseGeometry` NEVER throws: degenerate input (non-object, missing `vertices_coords`/`edges_vertices`, zero-span bbox) returns `{ viewBox: "0 0 100 100", segments: [] }`; an edge index out of range is skipped, not thrown.
- Empty state copy matches the JSON tab exactly: `No .fold yet — send a prompt.`
- Tests run from `web/frontend/`: `npx vitest run <path>`; full verify: `npx vitest run && npx tsc --noEmit`.
- v1 is static fit-to-view: no zoom/pan, no vertex dots, no source toggle, no 2D export (YAGNI per spec).

---

### Task 1: Pure crease-geometry builder (`creasePattern.ts`)

**Files:**
- Create: `web/frontend/src/creasePattern.ts`
- Test: `web/frontend/src/creasePattern.test.ts`

**Interfaces:**
- Consumes: a FOLD dict (untyped `unknown`) with `vertices_coords: [number,number][]`, `edges_vertices: [number,number][]`, optional `edges_assignment: string[]`.
- Produces:
  ```ts
  export interface Segment {
    x1: number; y1: number; x2: number; y2: number;
    kind: "M" | "V" | "B" | "F" | "U";
    color: string;
    dash?: string;          // set for V only
  }
  export interface CreaseGeometry { viewBox: string; segments: Segment[]; }
  export function buildCreaseGeometry(fold: unknown): CreaseGeometry;
  ```
  Task 2's `CreasePattern.tsx` imports `buildCreaseGeometry`, `Segment`, `CreaseGeometry`.

- [ ] **Step 1: Write the failing tests**

Create `web/frontend/src/creasePattern.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { buildCreaseGeometry } from "./creasePattern";

const EMPTY = { viewBox: "0 0 100 100", segments: [] };

describe("buildCreaseGeometry", () => {
  it("normalizes coords into the padded square and flips Y", () => {
    // Right triangle: bbox 0..1 in both axes, span = 1, scale = (100-8)/1 = 92.
    const fold = {
      vertices_coords: [[0, 0], [1, 0], [0, 1]],
      edges_vertices: [[0, 1], [0, 2]],
      edges_assignment: ["B", "B"],
    };
    const g = buildCreaseGeometry(fold);
    expect(g.viewBox).toBe("0 0 100 100");
    // vertex 0 (0,0): nx=4, ny_up=4 -> y_svg=96. vertex 1 (1,0): nx=96, y_svg=96.
    // vertex 2 (0,1): nx=4, ny_up=96 -> y_svg=4.
    expect(g.segments[0]).toMatchObject({ x1: 4, y1: 96, x2: 96, y2: 96 });
    expect(g.segments[1]).toMatchObject({ x1: 4, y1: 96, x2: 4, y2: 4 });
  });

  it("maps each assignment to the documented color, dashing only V", () => {
    const fold = {
      vertices_coords: [[0, 0], [1, 0], [1, 1], [0, 1], [0.5, 0.5]],
      edges_vertices: [[0, 4], [1, 4], [2, 4], [3, 4], [0, 1]],
      edges_assignment: ["M", "V", "F", "x", "B"],
    };
    const segs = buildCreaseGeometry(fold).segments;
    expect(segs[0]).toMatchObject({ kind: "M", color: "#d33" });
    expect(segs[0].dash).toBeUndefined();
    expect(segs[1]).toMatchObject({ kind: "V", color: "#36c", dash: "4 3" });
    expect(segs[2]).toMatchObject({ kind: "F", color: "#ccc" });
    expect(segs[3]).toMatchObject({ kind: "U", color: "#bbb" }); // unknown letter
    expect(segs[4]).toMatchObject({ kind: "B", color: "#444" });
  });

  it("falls back to U when edges_assignment is missing or short", () => {
    const fold = {
      vertices_coords: [[0, 0], [1, 0], [0, 1]],
      edges_vertices: [[0, 1], [0, 2]],
      edges_assignment: ["M"], // shorter than edges
    };
    const segs = buildCreaseGeometry(fold).segments;
    expect(segs[0].kind).toBe("M");
    expect(segs[1].kind).toBe("U"); // index past the assignment array
  });

  it("skips an edge that references an out-of-range vertex", () => {
    const fold = {
      vertices_coords: [[0, 0], [1, 0]],
      edges_vertices: [[0, 1], [0, 9]], // second edge out of range
      edges_assignment: ["B", "B"],
    };
    expect(buildCreaseGeometry(fold).segments).toHaveLength(1);
  });

  it("returns empty geometry (no throw) for degenerate inputs", () => {
    expect(buildCreaseGeometry(null)).toEqual(EMPTY);
    expect(buildCreaseGeometry({})).toEqual(EMPTY);
    expect(buildCreaseGeometry({ vertices_coords: [[1, 1], [1, 1]],
      edges_vertices: [[0, 1]] })).toEqual(EMPTY); // zero-span bbox
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run (from `web/frontend/`): `npx vitest run src/creasePattern.test.ts`
Expected: FAIL — `creasePattern.ts` does not exist (import error / "buildCreaseGeometry is not a function").

- [ ] **Step 3: Implement the builder**

Create `web/frontend/src/creasePattern.ts`:

```typescript
export interface Segment {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  kind: "M" | "V" | "B" | "F" | "U";
  color: string;
  dash?: string; // SVG stroke-dasharray, set for V only
}

export interface CreaseGeometry {
  viewBox: string;
  segments: Segment[];
}

const SIZE = 100;
const PAD = 4;
const EMPTY: CreaseGeometry = { viewBox: `0 0 ${SIZE} ${SIZE}`, segments: [] };

const STYLE: Record<Segment["kind"], { color: string; dash?: string }> = {
  M: { color: "#d33" },
  V: { color: "#36c", dash: "4 3" },
  B: { color: "#444" },
  F: { color: "#ccc" },
  U: { color: "#bbb" },
};

function kindOf(raw: unknown): Segment["kind"] {
  const c = typeof raw === "string" ? raw.toUpperCase() : "";
  return c === "M" || c === "V" || c === "B" || c === "F" ? c : "U";
}

export function buildCreaseGeometry(fold: unknown): CreaseGeometry {
  if (typeof fold !== "object" || fold === null) return EMPTY;
  const f = fold as Record<string, unknown>;
  const verts = f.vertices_coords;
  const edges = f.edges_vertices;
  if (!Array.isArray(verts) || !Array.isArray(edges) || verts.length === 0) {
    return EMPTY;
  }
  const assign = Array.isArray(f.edges_assignment) ? f.edges_assignment : [];

  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  for (const v of verts) {
    if (!Array.isArray(v)) return EMPTY;
    const [x, y] = v as [number, number];
    if (x < minX) minX = x;
    if (y < minY) minY = y;
    if (x > maxX) maxX = x;
    if (y > maxY) maxY = y;
  }
  const span = Math.max(maxX - minX, maxY - minY);
  if (!(span > 0)) return EMPTY; // zero-span / NaN guard

  const scale = (SIZE - 2 * PAD) / span;
  const project = (x: number, y: number): [number, number] => {
    const nx = PAD + (x - minX) * scale;
    const nyUp = PAD + (y - minY) * scale;
    return [nx, SIZE - nyUp]; // flip Y: FOLD y-up -> SVG y-down
  };

  const segments: Segment[] = [];
  edges.forEach((e, i) => {
    if (!Array.isArray(e)) return;
    const [a, b] = e as [number, number];
    if (a < 0 || b < 0 || a >= verts.length || b >= verts.length) return;
    const [x1, y1] = project((verts[a] as number[])[0], (verts[a] as number[])[1]);
    const [x2, y2] = project((verts[b] as number[])[0], (verts[b] as number[])[1]);
    const kind = kindOf(assign[i]);
    segments.push({ x1, y1, x2, y2, kind, ...STYLE[kind] });
  });

  return { viewBox: `0 0 ${SIZE} ${SIZE}`, segments };
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run (from `web/frontend/`): `npx vitest run src/creasePattern.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Typecheck**

Run (from `web/frontend/`): `npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/creasePattern.ts web/frontend/src/creasePattern.test.ts
git commit -m "$(cat <<'EOF'
feat(2d-panel): pure crease-geometry builder

buildCreaseGeometry turns a FOLD dict into normalized, Y-flipped SVG line
segments styled by M/V/B/F assignment. Pure/DOM-free and fail-safe (empty
geometry on degenerate input), mirroring the viewer.ts split.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: `CreasePattern` component + the "2D" tab

**Files:**
- Create: `web/frontend/src/CreasePattern.tsx`
- Modify: `web/frontend/src/App.tsx` (view union at line 18; the `.result-tabs` buttons ~line 81-86; the tab body conditional ~line 89-96)
- Modify: `web/frontend/src/styles.css` (append crease-panel styles)

**Interfaces:**
- Consumes: `buildCreaseGeometry`, `Segment` from `./creasePattern` (Task 1); `FoldArtifact` from `./chat` (existing — has `json: unknown`, `displayJson?: unknown`).
- Produces: `export default function CreasePattern({ fold }: { fold: FoldArtifact | null })`.

- [ ] **Step 1: Create the component**

Create `web/frontend/src/CreasePattern.tsx`:

```tsx
import type { FoldArtifact } from "./chat";
import { buildCreaseGeometry } from "./creasePattern";

const LEGEND: { label: string; color: string; dash?: string }[] = [
  { label: "mountain", color: "#d33" },
  { label: "valley", color: "#36c", dash: "4 3" },
  { label: "border", color: "#444" },
  { label: "flat", color: "#ccc" },
];

export default function CreasePattern({ fold }: { fold: FoldArtifact | null }) {
  if (!fold) {
    return <p className="viewer-msg">No .fold yet — send a prompt.</p>;
  }
  const { viewBox, segments } = buildCreaseGeometry(fold.json);
  return (
    <div className="crease">
      <svg className="crease-svg" viewBox={viewBox} preserveAspectRatio="xMidYMid meet">
        {segments.map((s, i) => (
          <line key={i} x1={s.x1} y1={s.y1} x2={s.x2} y2={s.y2}
            stroke={s.color} strokeWidth={0.6} strokeDasharray={s.dash} />
        ))}
      </svg>
      <ul className="crease-legend">
        {LEGEND.map((l) => (
          <li key={l.label}>
            <svg width="22" height="8" aria-hidden="true">
              <line x1="1" y1="4" x2="21" y2="4" stroke={l.color}
                strokeWidth={2} strokeDasharray={l.dash} />
            </svg>
            {l.label}
          </li>
        ))}
      </ul>
    </div>
  );
}
```

- [ ] **Step 2: Append panel styles**

Append to `web/frontend/src/styles.css`:

```css
.crease { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.crease-svg { flex: 1; width: 100%; min-height: 0; background: #fff;
  border: 1px solid #eee; }
.crease-legend { list-style: none; display: flex; gap: 1rem; flex-wrap: wrap;
  margin: .5rem 0 0; padding: 0; font-size: .8rem; color: #555; }
.crease-legend li { display: inline-flex; align-items: center; gap: .35rem; }
```

- [ ] **Step 3: Wire the "2D" tab into App.tsx**

In `web/frontend/src/App.tsx`:

Add the import after the `OrigamiViewer` import (line 3):

```tsx
import CreasePattern from "./CreasePattern";
```

Widen the view state (line 18):

```tsx
  const [view, setView] = useState<"json" | "2d" | "3d">("json");
```

Add the "2D" tab button between the JSON and 3D buttons in `.result-tabs` (currently lines 82-85). The block becomes:

```tsx
            <button className={view === "json" ? "active" : ""}
              onClick={() => setView("json")}>JSON</button>
            <button className={view === "2d" ? "active" : ""}
              onClick={() => setView("2d")}>2D</button>
            <button className={view === "3d" ? "active" : ""}
              onClick={() => setView("3d")}>3D</button>
```

Replace the tab-body conditional (currently the `{view === "json" ? (...) : (<OrigamiViewer .../>)}` block, lines ~89-96) with a three-way render:

```tsx
        {view === "json" ? (
          <pre className="fold">
            {state.fold ? JSON.stringify(state.fold.json, null, 2)
                        : "No .fold yet — send a prompt."}
          </pre>
        ) : view === "2d" ? (
          <CreasePattern fold={state.fold} />
        ) : (
          <OrigamiViewer fold={state.fold} />
        )}
```

- [ ] **Step 4: Verify the full suite + typecheck**

Run (from `web/frontend/`): `npx vitest run && npx tsc --noEmit`
Expected: all tests pass (the existing `chat`/`viewer`/`creasePattern` suites), `tsc` exits 0. This confirms the new component and the widened `view` union typecheck and that App.tsx still compiles. (The component is presentational — its segment-mapping logic is fully covered by Task 1's pure tests — so no separate component test is added, matching the `viewer.ts`/`OrigamiViewer.tsx` convention.)

- [ ] **Step 5: Build to confirm the production bundle compiles**

Run (from `web/frontend/`): `npx vite build`
Expected: build succeeds (no TS/bundler errors), `dist/` written.

- [ ] **Step 6: Commit**

```bash
git add web/frontend/src/CreasePattern.tsx web/frontend/src/App.tsx web/frontend/src/styles.css
git commit -m "$(cat <<'EOF'
feat(2d-panel): CreasePattern component + 2D result tab

A third "2D" tab renders state.fold.json as an SVG crease pattern (lines
colored M/V/B/F + legend) via the pure builder. Every edge incl. the
border is drawn, so no crease looks "hanging" (issue #4); also the
inspection surface A-9 will use.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
EOF
)"
```

---

## Self-Review

**Spec coverage:**
- Renders `state.fold.json` raw hull → Task 2 Step 1 (`buildCreaseGeometry(fold.json)`).
- SVG `<line>` per edge colored by assignment, M/V/B/F/U table + V-only dash → Task 1 (`STYLE`, `kindOf`) + tests.
- Normalize + Y-flip, `SIZE=100`/`PAD=4`/viewBox → Task 1 Step 3 (`project`) + Step 1 test.
- Legend → Task 2 Step 1 (`LEGEND`).
- Third "2D" tab in App.tsx → Task 2 Step 3.
- Empty state copy identical to JSON tab → Task 2 Step 1 (`viewer-msg` message string).
- Fail-safe degenerate handling (never throws; out-of-range edge skipped; missing/short assignment → U) → Task 1 Step 3 + the degenerate/short/out-of-range tests.
- Static fit-to-view, no zoom/dots/toggle/export (YAGNI) → nothing added; `preserveAspectRatio="xMidYMid meet"` gives static fit.

**Placeholder scan:** No TBD/TODO/vague steps; every code step shows complete code; every command has an expected result.

**Type consistency:** `buildCreaseGeometry`, `Segment`, `CreaseGeometry` defined in Task 1 and imported by name in Task 2. `Segment.kind` union `"M"|"V"|"B"|"F"|"U"` matches the `STYLE` keys and `kindOf` returns. `FoldArtifact.json` (`unknown`) is what `buildCreaseGeometry(fold: unknown)` accepts. `view` union `"json"|"2d"|"3d"` is consistent across the state declaration, the three tab buttons, and the body conditional.

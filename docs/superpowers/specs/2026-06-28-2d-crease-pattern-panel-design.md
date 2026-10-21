# 2D Crease-Pattern Panel

**Date:** 2026-06-28
**Status:** Approved — ready for implementation plan
**Depends on:** the fold-frame split ([validated-fold-on-download](2026-06-28-validated-fold-on-download-design.md)) which exposed `state.fold.json` (the raw validated hull) separately from the squared display copy.

## Problem

The 3D viewer (Origami Simulator) is a folding simulator, not a crease-pattern renderer. It hides flat (`"F"`) creases (`passiveEdgesVisible=false`) and clutters the view with internal triangulation diagonals, so the mountain/valley creases that terminate on the flat hull outline appear to "hang" mid-paper (issue #4). There is no honest 2D view of the crease pattern in the IDE today.

Two payoffs:
1. **Fixes #4** — a real 2D panel draws *every* edge (including the boundary), so no crease looks unattached.
2. **Tooling for A-9** — generative anatomy detail (the next feature) needs a way to *see* the crease pattern produced after adding flaps and recompiling; the 3D sim cannot serve that. This panel is that inspection surface.

## What it renders

The panel reads **`state.fold.json`** — the raw, validated hull crease pattern (the linted artifact), NOT the squared `displayJson`. The raw hull's outline is honest `"B"` border, so every M/V crease visibly terminates on a drawn boundary line — the direct fix for #4. (Decision settled in brainstorming; rendering the squared copy would re-introduce the faint-`"F"`-outline confusion #4 is about.)

It draws each edge from `edges_vertices` / `vertices_coords` as an SVG `<line>`, colored by `edges_assignment` using standard origami convention:

| Assignment | Color | Stroke |
|---|---|---|
| `M` (mountain) | red | solid |
| `V` (valley) | blue | dashed |
| `B` (border) | dark gray (`#444`) | solid |
| `F` (flat) | faint gray (`#ccc`) | solid |
| `U` / missing | light gray (`#bbb`) | solid |

A small legend maps colors → types. v1 is **static fit-to-view** — no zoom/pan (YAGNI; real patterns are tens–hundreds of edges and fit the panel). Confirmed real FOLDs carry `edges_assignment` (e.g. `star-4.fold`: 9 verts / 16 edges, values M/V/B).

## Architecture

Mirrors the existing viewer split (pure logic module + thin presentational component), so the geometry math is unit-testable without a DOM.

### `web/frontend/src/creasePattern.ts` (new, pure — no DOM, no React)

```ts
export interface Segment {
  x1: number; y1: number; x2: number; y2: number;
  kind: "M" | "V" | "B" | "F" | "U";
  color: string;
  dash?: string;            // SVG stroke-dasharray, set for V only
}

export interface CreaseGeometry {
  viewBox: string;          // e.g. "0 0 100 100"
  segments: Segment[];
}

// Returns zero-segment geometry (never throws) for any degenerate input.
export function buildCreaseGeometry(fold: unknown): CreaseGeometry;
```

Responsibilities:
- **Normalize** `vertices_coords` into a fixed padded square viewBox (`SIZE = 100`, `PAD = 4`): scale by the larger bbox dimension so aspect ratio is preserved.
- **Flip Y** (FOLD is y-up, SVG is y-down): `y_svg = SIZE - y_norm` after normalization.
- **Map** each `edges_assignment[i]` (uppercased; unknown/missing → `"U"`) to color + dash via a single lookup table; build one `Segment` per `edges_vertices[i]`.

### `web/frontend/src/CreasePattern.tsx` (new, thin/presentational)

- Props: `{ fold: FoldArtifact | null }`.
- If `fold` is null → render the empty-state message (same copy/style as the JSON tab: "No .fold yet — send a prompt.").
- Else call `buildCreaseGeometry(fold.json)`; render an `<svg>` with the computed `viewBox` and one `<line>` per segment (stroke = color, `strokeDasharray` = dash), plus a static legend. No logic beyond mapping segments → `<line>`s.

### `web/frontend/src/App.tsx` (modify)

- Extend the view union: `useState<"json" | "3d" | "2d">("json")`.
- Add a **"2D"** tab button in `.result-tabs`, between JSON and 3D, following the existing `className={view === "2d" ? "active" : ""}` pattern.
- Render `<CreasePattern fold={state.fold} />` when `view === "2d"`.

## Coordinate transform (precise)

Given `vertices_coords` (array of `[x, y]`):
1. `minX, minY, maxX, maxY` = bbox.
2. `span = max(maxX - minX, maxY - minY)`. **Guard:** if `span === 0` (all points identical/degenerate) → return `{ viewBox: "0 0 100 100", segments: [] }`.
3. `scale = (SIZE - 2*PAD) / span`.
4. For each vertex: `nx = PAD + (x - minX) * scale`; `ny_up = PAD + (y - minY) * scale`; `y_svg = SIZE - ny_up`.
5. viewBox is `"0 0 100 100"` (`SIZE`).

This fits any aspect ratio inside the square with padding and orients the pattern the conventional way (origami y-up).

## Error handling

`buildCreaseGeometry` returns `{ viewBox: "0 0 100 100", segments: [] }` (never throws) when:
- `fold` is not an object, or `vertices_coords` / `edges_vertices` is missing or not an array;
- bbox span is 0 (degenerate);
- an edge references a vertex index out of range → skip that single edge (don't throw).

`edges_assignment` missing or shorter than `edges_vertices` → those edges map to `"U"`.

The component renders the empty state for `fold === null`; a non-null fold that yields zero segments renders an empty `<svg>` (acceptable — means a degenerate/empty pattern, not an error).

## Testing

`web/frontend/src/creasePattern.test.ts` (vitest, pure — no DOM):
- **Normalization + Y-flip:** a known 3-vertex fold (e.g. `[[0,0],[1,0],[0,1]]`) produces segments whose coords match the hand-computed padded/flipped values and a `"0 0 100 100"` viewBox.
- **Assignment → style:** each of M/V/B/F maps to the documented color; V (and only V) gets a dash.
- **Missing/short `edges_assignment`:** affected edges fall back to `"U"` style.
- **Out-of-range edge index:** that edge is skipped; others still produced.
- **Degenerate inputs:** non-object, missing arrays, and zero-span bbox each return zero segments without throwing.

The component is presentational (mapping segments → `<line>`s); its logic is fully covered by the pure module, so no separate component test is added (matching the `viewer.ts` / `OrigamiViewer.tsx` convention).

## Out of scope (YAGNI)

- Zoom / pan / interactivity.
- Vertex dots / labels (edges convey the pattern; dots are debug clutter — revisit only if A-9 work needs them).
- Rendering the squared `displayJson` or a source toggle.
- Fold-angle shading, layer ordering, or any folded-state visualization (that is the 3D viewer's job).
- Export of the 2D view (PNG/SVG download) — the `.fold` download already exists.

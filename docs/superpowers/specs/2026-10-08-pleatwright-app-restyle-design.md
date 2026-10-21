# Pleatwright app restyle: design

Date: 2026-10-08. Status: approved in brainstorming (owner), pending spec review.
Builds on `2026-10-07-pleatwright-app-design.md` (the app itself, merged in PR #200).

## Goal

Give the app (`app/web`) a clean, deliberate look: the form of a folding diagram
(monospace, square corners, 1px rules, numbered steps) on the colours of a
viewport-first pro tool (neutral greys, one blue accent), in light and dark
modes with a toggle. This is a visual pass only; behaviour changes are a later pass.

## Prior art

| source | taken | rejected |
|---|---|---|
| Teenage Engineering, Observable, Are.na, Lang's folding diagrams | monospace type, square corners, black 1px rules, numbered steps (`01 IMAGE`) | cream-only palette (kept as the light theme) |
| Figma, Spline, Blender, Shapr3D | neutral grey chrome, dotted canvas, `#0d99ff` accent, stage numbers beside the canvas | floating inspector box (the viewer's corners are taken; see Viewer header) |
| claude.ai, Linear, Vercel, Raycast | shown to the owner as directions A and B; not chosen | — |
| VS Code, Linear | theme control in the sidebar footer; System / Light / Dark | — |
| `next-themes`, Josh Comeau "The Quest for the Perfect Dark Mode" | a blocking inline `<head>` script sets `data-theme` before first paint; `prefers-color-scheme` applies only when no choice is stored | applying the theme in a React effect (flashes the wrong theme on reload) |
| Tailwind; Radix Themes / shadcn | — | rewriting 10 components for a re-skin; a kit's rounded look fights the square ruled style |

The owner chose from mockups kept in `.superpowers/brainstorm/` (directions A–D,
then three C×D hybrids; chosen: dotted canvas, both themes).

## Constraints

* Front-end only: no change to `app/server`, the event log, or `mcp_harness/`.
  Pleatwright output bytes are unchanged (crease colours change on screen only).
* One new dependency, exact-pinned: `@fontsource/ibm-plex-mono` `5.3.0`, bundled
  by Vite (works offline; no CDN).
* All colours are CSS custom properties in `app/web/src/styles.css`; components
  carry no hard-coded colours except three.js materials (see Crease colours).
* The existing 34 vitest tests, `tsc --noEmit`, `vite build` and `make test` stay green.

## Theme

### Tokens

| token | dark | light |
|---|---|---|
| `--bg` | `#1e1e1e` | `#f4f1e8` |
| `--panel` | `#252525` | `#ece8dc` |
| `--raise` | `#2c2c2c` | `#fbf9f3` |
| `--line` | `#3d3d3d` | `#1d1d1b` |
| `--text` | `#e6e6e6` | `#1d1d1b` |
| `--muted` | `#8f8f8f` | `#6d6a62` |
| `--user` | `#333333` | `#e4dfd0` |
| `--accent` / `--accent-fg` | `#0d99ff` / `#ffffff` | same |
| `--ok` | `#3ecf7a` | `#1f8a4c` |
| `--bad` | `#e33b2e` | `#e33b2e` |
| `--canvas` / `--dot` | `#1a1a1a` / `#333333` | `#f4f1e8` / `#e1dccd` |
| `--mountain` / `--valley` | `#e33b2e` / `#2f55d4` | same |
| `--sheet` | `#ffffff` | `#ffffff` |

The old `--step-*` tokens are removed; step states use the tokens above.

### Selection rule

`<html data-theme="light|dark">` when the viewer has chosen; no attribute means
System. CSS defines each themed token once, as `light-dark(<light>, <dark>)` on `:root`,
and `color-scheme` selects the value: `color-scheme: light dark` on `:root` follows the
OS (System); `:root[data-theme="light"]` / `[data-theme="dark"]` set `color-scheme: light` /
`dark`. Native controls follow the same `color-scheme`. (Owner decision 2026-10-08, replacing
a duplicated light-token block; `light-dark()` needs Chrome 123+, Safari 17.5+, Firefox 120+.)

### `theme.ts`

* `type ThemePref = "system" | "light" | "dark"`; `STORAGE_KEY = "pleatwright.theme"`.
* `readPref(storage): ThemePref`: a stored `"light"`/`"dark"` is returned;
  anything else, a missing value, or a throwing storage gives `"system"`.
* `nextPref(p)`: system → light → dark → system.
* `applyPref(p, root, storage)`: sets or removes `data-theme`; stores the pref
  (removes the key for `"system"`); storage errors are swallowed.
* `HEAD_SCRIPT`: the inline script's source, exported as a string so a test can
  evaluate it against the same stored values as `readPref`.

`index.html` carries that script inline in `<head>` before the module script.

### Toggle

The sidebar footer holds one button, `◐ SYSTEM` / `☀ LIGHT` / `☾ DARK`, which
cycles `nextPref`. Its `aria-label` names the current setting.

## Type and shape

* `font-family: "IBM Plex Mono", "SF Mono", Menlo, ui-monospace, monospace`
  everywhere; base size 12px, line-height 1.5. Weights 400 and 600 imported.
* `border-radius: 0` throughout. Selected items get a 1px accent border plus a
  2px accent rule on the left (`box-shadow: inset 2px 0 0 var(--accent)`).
* Button labels uppercase. Primary = accent fill; ghost = 1px `--line` border.

## Components

### Stage labels

`stageLabel(s)` in `types.ts` returns `"01 IMAGE"` … `"07 MODEL"` (two-digit index
in `STAGES` order, upper-case name; `packing` shows as `PACK`); `stageNum(s)`
returns `"01"` … `"07"`. The stepper, chat blocks and filmstrip all use them.

### Stepper

A full-width row of seven equal cells divided by 1px rules, each showing
`stageLabel`. States: done = `✓` in `--ok` before the label; running = existing
spinner + elapsed seconds; waiting = accent fill, `--accent-fg` text; failed =
`✕` in `--bad`; skipped = struck through; todo = muted. Logic in `Stepper.tsx`
is unchanged.

### Chat

* Stage block: one ruled line: muted `stageNum`, `outputTitle`, then
  `summaryLine` right-aligned and muted; the thumbnail is a bordered square.
* Assistant text is prefixed by an accent `●`. User text is a square, bordered box
  aligned right.
* Composer: a `>` prompt glyph before the textarea. Review controls: APPROVE
  (primary), RETRY / CANCEL (ghost).

### Sidebar

* `[+] NEW RUN` with a muted `N` hint; pressing `N` starts a new run when focus
  is not in a text field or other editable element. (Not ⌘N: Chrome reserves
  ⌘N/Ctrl+N for a new window and never delivers it to the page. The single-key
  pattern is Linear's `C` / Gmail's `c`.)
* Day headings: `— TODAY`, `— YESTERDAY`, otherwise `— YYYY-MM-DD`.
* Status marks replace dots: done `✓` (`--ok`), running `…` (`--accent`),
  waiting `⏸` (`--accent`), failed `✕` (`--bad`), new `·` (`--muted`). Each mark
  has an `aria-label` with the status word.
* The open run: `--raise` background and a 2px accent left rule.
* Footer: the theme toggle.

### Viewer header

A thin bar above the canvas, replacing the floating `.vtools` and `.follow`
placements for image, CP and tree views:

* left: `stageLabel` of the shown output, `· R<n>` for a tree round, then
  `summaryPairs(output)` as `key value` separated by `·`;
* right: the round tabs, the file tabs, `follow latest` (when not following),
  and the view's own toggles (CP: hinges, M/V colours; model: overview).

`summaryPairs(o: Output): [string, string][]` in `runStore.ts`:

| stage | pairs |
|---|---|
| image | `provider`; or `note` when skipped |
| mesh | `provider`, `faces` (locale-formatted) |
| tree | `flaps`, `pairs`; or `approved` → `["status","approved"]` |
| packing | `grid`, `rung`, `tried` |
| solve | `flat-foldable` (`a/b`), `global` (verdict) |
| shape | `flat-foldable` (`a/b`) |
| model | `folder` (last path segment) when present, else empty |

Missing keys are skipped, never shown as `undefined`. The mesh orbit controls
and the model fold slider stay at the bottom of the canvas.

### Canvas

The viewer area uses `--canvas` with a `--dot` radial-gradient dot grid (12px).
`MeshView` and `ModelView` render with a transparent WebGL clear
(`gl={{ alpha: true }}`, no scene background) so the dotted CSS shows through.
CP SVGs sit on `--sheet`; in the light theme the sheet has a 1px `--line` border.

### Filmstrip

Square frames labelled with `stageLabel`; the selected frame has an accent outline.

### Crease colours (display only)

* CP view: `.cp line[stroke="red"] { stroke: var(--mountain) }`,
  `.cp line[stroke="blue"] { stroke: var(--valley) }`; the mono and no-hinges
  toggles keep working.
* `ModelView` fold lines use `#e33b2e` / `#2f55d4` (three.js cannot read CSS
  variables). Paper stays cream front (`#f4efe6`), orange back (`#d08a2a`).

## Testing

* `theme.test.ts`: `readPref` for `"light"`, `"dark"`, missing, junk, throwing
  storage; `nextPref` cycle; `applyPref` sets/removes the attribute and key and
  survives a throwing storage; `HEAD_SCRIPT` evaluated against a stub `document`
  and storage yields the same attribute as `readPref` + `applyPref` for each case.
* `runStore.test.ts`: `summaryPairs` for every stage present in the recorded
  `bird_run.events.jsonl` fixture plus a skipped image and an approved tree;
  no value is `"undefined"`.
* `types.test.ts` (or alongside): `stageLabel` / `stageNum` for all 7 stages.
* `RunsSidebar` day-heading function: today, yesterday, an older ISO date.
* The `N` shortcut: fires from the page body, not from inside the textarea.
* Browser check (Browser pane, visible tab): the app on the fake provider with
  seeded runs, screenshots of image, mesh, tree, CP and model views in both
  themes; a reload with a stored theme shows no flash; the font is served from
  localhost; the console is clean.

## Out of scope

Behavioural UI/UX changes, layout changes beyond the viewer header, server or
pipeline changes, new stages or events.

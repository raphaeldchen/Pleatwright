# Pleatwright App Restyle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle `app/web` as a folding diagram (monospace, square corners, 1px rules, numbered steps) on pro-tool colours (neutral greys, one `#0d99ff` accent), with light and dark themes and a System / Light / Dark toggle.

**Architecture:** All colours become CSS custom properties in `app/web/src/styles.css`. Dark values sit on `:root`; light values apply under `data-theme="light"`, or under System on a light OS. A pure `theme.ts` reads, cycles and applies the stored choice. A Vite plugin injects `theme.ts`'s `HEAD_SCRIPT` into `<head>`, so a stored theme is set before first paint. New label and summary helpers are pure functions with vitest tests. A header bar above the canvas takes over each view's floating buttons through a React portal (`<Tools>`).

**Tech Stack:** React 18.3.1, TypeScript 5.6.3, Vite 5.4.11, vitest 2.1.8 (node environment, no DOM), three 0.169.0 / @react-three/fiber 8.18.0, `@fontsource/ibm-plex-mono` 5.3.0.

**Spec:** `docs/superpowers/specs/2026-10-08-pleatwright-app-restyle-design.md`

## Global Constraints

* Front-end only: no change to `app/server`, the event log, or `mcp_harness/`. Pleatwright output bytes are unchanged; crease colours change on screen only.
* One new dependency, exact-pinned: `@fontsource/ibm-plex-mono` `5.3.0`, bundled by Vite (works offline; no CDN).
* All colours are CSS custom properties in `app/web/src/styles.css`. Components carry no hard-coded colours except three.js materials.
* Dark tokens: `--bg #1e1e1e`, `--panel #252525`, `--raise #2c2c2c`, `--line #3d3d3d`, `--text #e6e6e6`, `--muted #8f8f8f`, `--user #333333`, `--accent #0d99ff`, `--accent-fg #ffffff`, `--ok #3ecf7a`, `--bad #e33b2e`, `--canvas #1a1a1a`, `--dot #333333`, `--mountain #e33b2e`, `--valley #2f55d4`, `--sheet #ffffff`.
* Light tokens: `--bg #f4f1e8`, `--panel #ece8dc`, `--raise #fbf9f3`, `--line #1d1d1b`, `--text #1d1d1b`, `--muted #6d6a62`, `--user #e4dfd0`, `--ok #1f8a4c`, `--canvas #f4f1e8`, `--dot #e1dccd`. All other tokens are the same as dark.
* `font-family: "IBM Plex Mono", "SF Mono", Menlo, ui-monospace, monospace`; base 12px, line-height 1.5; weights 400 and 600.
* `border-radius: 0` throughout. A selected item gets a 1px accent border plus `box-shadow: inset 2px 0 0 var(--accent)`.
* Theme storage key `"pleatwright.theme"`. The stored value is `"light"` or `"dark"`; no key means System.
* The new-run shortcut is plain `N`, not ⌘N, which Chrome reserves. It never fires while typing in an editable element.
* The existing 34 vitest tests, `tsc --noEmit`, `vite build` and `make test` stay green.
* Effects that call DOM methods must use block bodies (`useEffect(() => { el.scrollIntoView(); })`). In Chrome 152, `scrollIntoView` returns a Promise, and an expression-bodied effect hands that Promise to React as a cleanup function.
* All npm commands run from `app/web/`.

## Spec readings (decided here; reviewers check against these)

1. **`HEAD_SCRIPT` reaches `index.html` through a Vite `transformIndexHtml` plugin.** It is not pasted into `index.html` by hand, so only one copy exists, in `theme.ts`. The built `dist/index.html` and the dev server both carry it in `<head>`.
2. **"Reset view" moves into the header like every other view button.** That applies to both the mesh and the folded-model views. Only the fold slider stays on the canvas.
3. **One token beyond the spec's table: `--sheet-edge`.** It is `transparent` in dark and `#1d1d1b` in light, and implements the spec's "in the light theme the sheet has a 1px `--line` border".
4. **The relative order of buttons in the header is not specified.** The `Viewer`'s own tabs and a view's toggles both portal into one slot.

## File structure

| file | role |
|---|---|
| `app/web/src/theme.ts` (new) | `ThemePref`, `STORAGE_KEY`, `readPref`, `nextPref`, `applyPref`, `safeStorage`, `HEAD_SCRIPT` |
| `app/web/src/shortcuts.ts` (new) | `isNewRunKey` |
| `app/web/src/types.ts` | adds `stageNum`, `stageLabel` |
| `app/web/src/runStore.ts` | adds `summaryPairs`, `outputLabel` |
| `app/web/src/components/ThemeToggle.tsx` (new) | the System / Light / Dark button |
| `app/web/src/components/ViewerHeader.tsx` (new) | `ViewerHeader`, `ToolSlot` context, `<Tools>` portal |
| `app/web/src/components/RunsSidebar.tsx` | `dayLabel`, status marks, footer toggle |
| `app/web/src/components/{Chat,StageBlock,Stepper,Filmstrip}.tsx` | numbered labels, new markup |
| `app/web/src/components/{Viewer,CPView,MeshView,ModelView}.tsx` | buttons into `<Tools>`, transparent WebGL, display crease colours |
| `app/web/src/App.tsx` | `N` shortcut; viewer = header + dotted canvas |
| `app/web/src/styles.css` | rewritten on tokens |
| `app/web/vite.config.ts` | theme head plugin |
| `app/web/src/main.tsx` | font imports |
| tests | `theme.test.ts`, `types.test.ts`, `shortcuts.test.ts`, `components/RunsSidebar.test.ts`; `runStore.test.ts` extended |

---

### Task 1: Theme module, head script and font

**Files:**
- Create: `app/web/src/theme.ts`
- Create: `app/web/src/theme.test.ts`
- Modify: `app/web/vite.config.ts`
- Modify: `app/web/src/main.tsx`
- Modify: `app/web/package.json`, `app/web/package-lock.json` (via npm)

**Interfaces:**
- Produces: `type ThemePref = "system" | "light" | "dark"`; `STORAGE_KEY: string`; `interface PrefStore { getItem; setItem; removeItem }`; `interface ThemeRoot { setAttribute; removeAttribute }`; `readPref(storage: PrefStore | null): ThemePref`; `nextPref(p: ThemePref): ThemePref`; `applyPref(p: ThemePref, root: ThemeRoot, storage: PrefStore | null): void`; `safeStorage(): PrefStore | null`; `HEAD_SCRIPT: string`. Task 3's `ThemeToggle` uses all of these except `HEAD_SCRIPT`.

- [ ] **Step 1: Write the failing test** — create `app/web/src/theme.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { applyPref, HEAD_SCRIPT, nextPref, readPref, STORAGE_KEY, type PrefStore } from "./theme";

function memStore(init: Record<string, string> = {}): PrefStore & { data: Record<string, string> } {
  const data = { ...init };
  return {
    data,
    getItem: (k) => (k in data ? data[k] : null),
    setItem: (k, v) => { data[k] = v; },
    removeItem: (k) => { delete data[k]; },
  };
}
const throwing: PrefStore = {
  getItem: () => { throw new Error("blocked"); },
  setItem: () => { throw new Error("blocked"); },
  removeItem: () => { throw new Error("blocked"); },
};
function fakeRoot() {
  const attrs: Record<string, string> = {};
  return { attrs,
           setAttribute: (n: string, v: string) => { attrs[n] = v; },
           removeAttribute: (n: string) => { delete attrs[n]; } };
}

describe("readPref", () => {
  it.each([["light", "light"], ["dark", "dark"], ["system", "system"], ["blue", "system"]])(
    "stored %s reads as %s", (stored, want) => {
      expect(readPref(memStore({ [STORAGE_KEY]: stored }))).toBe(want);
    });
  it("a missing key, no storage and a throwing storage all read as system", () => {
    expect(readPref(memStore())).toBe("system");
    expect(readPref(null)).toBe("system");
    expect(readPref(throwing)).toBe("system");
  });
});

describe("nextPref", () => {
  it("cycles system → light → dark → system", () => {
    expect(nextPref("system")).toBe("light");
    expect(nextPref("light")).toBe("dark");
    expect(nextPref("dark")).toBe("system");
  });
});

describe("applyPref", () => {
  it("light/dark set the attribute and store the choice", () => {
    const root = fakeRoot(), s = memStore();
    applyPref("dark", root, s);
    expect(root.attrs["data-theme"]).toBe("dark");
    expect(s.data[STORAGE_KEY]).toBe("dark");
  });
  it("system removes both the attribute and the key", () => {
    const root = fakeRoot(), s = memStore({ [STORAGE_KEY]: "light" });
    root.setAttribute("data-theme", "light");
    applyPref("system", root, s);
    expect(root.attrs).toEqual({});
    expect(s.data).toEqual({});
  });
  it("still sets the attribute when storage throws", () => {
    const root = fakeRoot();
    expect(() => applyPref("light", root, throwing)).not.toThrow();
    expect(root.attrs["data-theme"]).toBe("light");
  });
});

describe("HEAD_SCRIPT agrees with readPref + applyPref", () => {
  const viaHead = (storage: PrefStore) => {
    const root = fakeRoot();
    new Function("localStorage", "document", HEAD_SCRIPT)(storage, { documentElement: root });
    return root.attrs["data-theme"] ?? null;
  };
  const viaModule = (storage: PrefStore) => {
    const root = fakeRoot();
    applyPref(readPref(storage), root, memStore());
    return root.attrs["data-theme"] ?? null;
  };
  it.each([["light"], ["dark"], ["system"], ["junk"], [null]])("stored %s", (stored) => {
    const init = stored == null ? {} : { [STORAGE_KEY]: stored };
    expect(viaHead(memStore(init))).toBe(viaModule(memStore(init)));
  });
  it("a throwing storage leaves no attribute either way", () => {
    expect(viaHead(throwing)).toBe(null);
    expect(viaModule(throwing)).toBe(null);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails.**

Run: `npx vitest run src/theme.test.ts`
Expected: FAIL, because `./theme` cannot be resolved.

- [ ] **Step 3: Write the implementation** — create `app/web/src/theme.ts`:

```ts
/** Light/dark theme preference. "system" = no stored choice; the CSS follows prefers-color-scheme. */
export type ThemePref = "system" | "light" | "dark";
export const STORAGE_KEY = "pleatwright.theme";

export interface PrefStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}
export interface ThemeRoot {
  setAttribute(name: string, value: string): void;
  removeAttribute(name: string): void;
}

export function readPref(storage: PrefStore | null): ThemePref {
  try {
    const p = storage?.getItem(STORAGE_KEY);
    return p === "light" || p === "dark" ? p : "system";
  } catch {
    return "system";
  }
}

export const nextPref = (p: ThemePref): ThemePref =>
  p === "system" ? "light" : p === "light" ? "dark" : "system";

export function applyPref(p: ThemePref, root: ThemeRoot, storage: PrefStore | null): void {
  if (p === "system") root.removeAttribute("data-theme");
  else root.setAttribute("data-theme", p);
  try {
    if (p === "system") storage?.removeItem(STORAGE_KEY);
    else storage?.setItem(STORAGE_KEY, p);
  } catch { /* private window or blocked site data: the choice lasts until reload */ }
}

/** window.localStorage, or null where touching it throws (sandboxed frames, blocked site data). */
export function safeStorage(): PrefStore | null {
  try { return window.localStorage; } catch { return null; }
}

/** Runs in <head> before first paint (vite.config.ts injects it), so a stored theme never flashes.
 *  Must agree with readPref + applyPref; theme.test.ts checks that it does. */
export const HEAD_SCRIPT =
  `try{var p=localStorage.getItem(${JSON.stringify(STORAGE_KEY)});` +
  `if(p==="light"||p==="dark")document.documentElement.setAttribute("data-theme",p)}catch(e){}`;
```

- [ ] **Step 4: Run the test to verify it passes.**

Run: `npx vitest run src/theme.test.ts`
Expected: PASS, with all tests green.

- [ ] **Step 5: Inject the head script.** Replace `app/web/vite.config.ts` with:

```ts
import { defineConfig, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { HEAD_SCRIPT } from "./src/theme";

const api = "http://127.0.0.1:8000";

// Sets data-theme from the stored choice before first paint (see src/theme.ts).
const themeHead = (): Plugin => ({
  name: "pleatwright-theme-head",
  transformIndexHtml: () => [{ tag: "script", children: HEAD_SCRIPT, injectTo: "head-prepend" }],
});

export default defineConfig({
  plugins: [react(), themeHead()],
  server: {
    host: "127.0.0.1",
    proxy: {
      "/status": api,
      "/runs": api,
      "/ws": { target: "ws://127.0.0.1:8000", ws: true },
    },
  },
  test: { environment: "node" },
});
```

- [ ] **Step 6: Add the font.**

Run: `npm install --save-exact @fontsource/ibm-plex-mono@5.3.0`
Then check: `ls node_modules/@fontsource/ibm-plex-mono/400.css node_modules/@fontsource/ibm-plex-mono/600.css`. Both files must exist.
Then check that `package.json` `dependencies` has `"@fontsource/ibm-plex-mono": "5.3.0"`, with no `^`.

In `app/web/src/main.tsx`, add these two imports directly above `import "./styles.css";`:

```ts
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/600.css";
```

- [ ] **Step 7: Verify the whole web package.**

Run: `npm test && npm run build && grep -c 'pleatwright.theme' dist/index.html && ls dist/assets | grep -ci plex`
Expected:
- all vitest files pass (the 34 existing tests plus the new ones);
- `tsc` is clean and the build succeeds;
- `grep` prints `1`, so the head script is in the built `index.html`;
- the last command prints a count ≥ 1, so the font files are bundled.

- [ ] **Step 8: Commit.**

```bash
git add app/web/src/theme.ts app/web/src/theme.test.ts app/web/vite.config.ts app/web/src/main.tsx app/web/package.json app/web/package-lock.json
git commit -m "app/web: theme preference module, pre-paint head script, bundled IBM Plex Mono"
```

---

### Task 2: Label and summary helpers

**Files:**
- Modify: `app/web/src/types.ts` (append)
- Modify: `app/web/src/runStore.ts` (import + append)
- Create: `app/web/src/shortcuts.ts`
- Modify: `app/web/src/components/RunsSidebar.tsx` (replace the private `day` with exported `dayLabel`)
- Create: `app/web/src/types.test.ts`, `app/web/src/shortcuts.test.ts`, `app/web/src/components/RunsSidebar.test.ts`
- Modify: `app/web/src/runStore.test.ts` (append)

**Interfaces:**
- Produces:
  - `stageNum(s: StageId): string` returns `"01"`…`"07"`.
  - `stageLabel(s: StageId): string` returns `"01 IMAGE"`…`"07 MODEL"`; `packing` shows as `"04 PACK"`.
  - `summaryPairs(o: Output): [string, string][]`.
  - `outputLabel(o: Output): string` returns, for example, `"03 TREE · R2"`.
  - `interface KeyLike { key; metaKey; ctrlKey; altKey; target }` and `isNewRunKey(e: KeyLike): boolean`.
  - `dayLabel(iso: string, now?: Date): string` returns `"— TODAY"`, `"— YESTERDAY"` or `"— YYYY-MM-DD"`.
  - Tasks 3 and 4 use all of these.

- [ ] **Step 1: Write the failing tests.**

Create `app/web/src/types.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { STAGES, stageLabel, stageNum } from "./types";

describe("stage labels", () => {
  it("number and name every stage in pipeline order", () => {
    expect(STAGES.map((s) => stageLabel(s))).toEqual(
      ["01 IMAGE", "02 MESH", "03 TREE", "04 PACK", "05 SOLVE", "06 SHAPE", "07 MODEL"]);
    expect(STAGES.map((s) => stageNum(s))).toEqual(["01", "02", "03", "04", "05", "06", "07"]);
  });
});
```

Create `app/web/src/shortcuts.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { isNewRunKey, type KeyLike } from "./shortcuts";

const k = (over: Partial<KeyLike> = {}): KeyLike =>
  ({ key: "n", metaKey: false, ctrlKey: false, altKey: false, target: null, ...over });
const el = (tagName: string, isContentEditable = false) =>
  ({ tagName, isContentEditable }) as unknown as EventTarget;

describe("isNewRunKey", () => {
  it("fires on a plain n or N from the page", () => {
    expect(isNewRunKey(k())).toBe(true);
    expect(isNewRunKey(k({ key: "N" }))).toBe(true);
    expect(isNewRunKey(k({ target: el("BODY") }))).toBe(true);
    expect(isNewRunKey(k({ target: el("BUTTON") }))).toBe(true);
  });
  it("ignores modified presses and other keys", () => {
    expect(isNewRunKey(k({ metaKey: true }))).toBe(false);
    expect(isNewRunKey(k({ ctrlKey: true }))).toBe(false);
    expect(isNewRunKey(k({ altKey: true }))).toBe(false);
    expect(isNewRunKey(k({ key: "m" }))).toBe(false);
  });
  it("never fires while typing", () => {
    for (const t of ["TEXTAREA", "INPUT", "SELECT"]) expect(isNewRunKey(k({ target: el(t) }))).toBe(false);
    expect(isNewRunKey(k({ target: el("DIV", true) }))).toBe(false);
  });
});
```

Create `app/web/src/components/RunsSidebar.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { dayLabel } from "./RunsSidebar";

describe("dayLabel (local time)", () => {
  const now = new Date(2026, 9, 8, 15, 0);
  it("names today and yesterday", () => {
    expect(dayLabel(new Date(2026, 9, 8, 0, 5).toISOString(), now)).toBe("— TODAY");
    expect(dayLabel(new Date(2026, 9, 7, 23, 59).toISOString(), now)).toBe("— YESTERDAY");
  });
  it("gives older runs an ISO date", () => {
    expect(dayLabel(new Date(2026, 9, 6, 12, 0).toISOString(), now)).toBe("— 2026-10-06");
    expect(dayLabel(new Date(2025, 0, 2, 12, 0).toISOString(), now)).toBe("— 2025-01-02");
  });
});
```

Append to `app/web/src/runStore.test.ts`. First extend its existing first import line to:

```ts
import { emptyView, latestByStage, outputLabel, reduce, selectedOutput, summaryLine, summaryPairs } from "./runStore";
```

and its types import to:

```ts
import type { Output, PwEvent, RunView } from "./types";
```

Then append at the end of the file:

```ts
describe("summaryPairs / outputLabel over the recorded run", () => {
  const v = replay();
  const by = (key: string) => v.outputs.find((o) => o.key === key)!;
  const mk = (stage: Output["stage"], summary: Record<string, unknown>): Output =>
    ({ key: stage, stage, files: [], summary, seq: 0 });

  it("gives each recorded stage its pairs", () => {
    expect(summaryPairs(by("image"))).toEqual([["note", "no concept image (fake)"]]);
    expect(summaryPairs(by("mesh"))).toEqual([["provider", "fake"], ["faces", (608).toLocaleString()]]);
    expect(summaryPairs(by("tree:0"))).toEqual([["flaps", "6"], ["pairs", "2"]]);
    expect(summaryPairs(by("tree:1"))).toEqual([["status", "approved"]]);
    expect(summaryPairs(by("packing"))).toEqual([["grid", "40"], ["rung", "symmetric"], ["tried", "1"]]);
    expect(summaryPairs(by("solve"))).toEqual([["flat-foldable", "187/187"], ["global", "CERTIFIED"]]);
    expect(summaryPairs(by("shape"))).toEqual([["flat-foldable", "792/792"]]);
    expect(summaryPairs(by("model"))).toEqual([]);
  });

  it("never shows undefined or null", () => {
    for (const o of v.outputs) for (const [, val] of summaryPairs(o)) expect(val).not.toMatch(/undefined|null/);
  });

  it("covers a provider image, a model folder, and skips missing or malformed keys", () => {
    expect(summaryPairs(mk("image", { provider: "hf2" }))).toEqual([["provider", "hf2"]]);
    expect(summaryPairs(mk("model", { folder: "Dog_54" }))).toEqual([["folder", "Dog_54"]]);
    expect(summaryPairs(mk("model", { folder: "runs/x/Dog_54/" }))).toEqual([["folder", "Dog_54"]]);
    expect(summaryPairs(mk("packing", { grid: 54 }))).toEqual([["grid", "54"]]);
    expect(summaryPairs(mk("solve", { flat_foldable: "weird" }))).toEqual([]);
    expect(summaryPairs(mk("tree", {}))).toEqual([]);
  });

  it("labels outputs with stage number and tree round", () => {
    expect(outputLabel(by("tree:0"))).toBe("03 TREE · R1");
    expect(outputLabel(by("tree:1"))).toBe("03 TREE · R2");
    expect(outputLabel(by("packing"))).toBe("04 PACK");
    expect(outputLabel(by("model"))).toBe("07 MODEL");
  });
});
```

- [ ] **Step 2: Run the tests to verify they fail.**

Run: `npx vitest run src/types.test.ts src/shortcuts.test.ts src/components/RunsSidebar.test.ts src/runStore.test.ts`
Expected: FAIL. The new names are not exported, and `./shortcuts` does not exist. The pre-existing `runStore` tests still pass.

- [ ] **Step 3: Implement.**

Append to `app/web/src/types.ts`:

```ts
/** "01" … "07": a stage's position in STAGES. */
export const stageNum = (s: StageId): string => String(STAGES.indexOf(s) + 1).padStart(2, "0");

/** "01 IMAGE" … "07 MODEL" ("packing" shows as PACK); shared by the stepper, chat and filmstrip. */
export const stageLabel = (s: StageId): string =>
  `${stageNum(s)} ${(s === "packing" ? "pack" : s).toUpperCase()}`;
```

In `app/web/src/runStore.ts`, change the first import to:

```ts
import { STAGES, stageLabel, type Action, type Output, type PwEvent, type RunView, type StageId,
         type StageStatus } from "./types";
```

and append at the end of the file:

```ts
const frac = (x: unknown) => (Array.isArray(x) && x.length === 2 ? `${x[0]}/${x[1]}` : null);

/** A stage summary as label/value pairs for the viewer header. Missing keys are skipped: old runs'
 *  events are never rewritten, so a summary may predate a key. */
export function summaryPairs(o: Output): [string, string][] {
  const s = o.summary;
  const out: [string, string][] = [];
  const add = (k: string, v: unknown) => { if (v != null && v !== "") out.push([k, String(v)]); };
  switch (o.stage) {
    case "image":
      if (s.skipped) add("note", s.note); else add("provider", s.provider);
      break;
    case "mesh":
      add("provider", s.provider);
      add("faces", s.faces != null ? Number(s.faces).toLocaleString() : null);
      break;
    case "tree":
      if (s.approved) add("status", "approved");
      else { add("flaps", s.flaps); add("pairs", s.pairs); }
      break;
    case "packing": add("grid", s.grid); add("rung", s.rung); add("tried", s.tried); break;
    case "solve": add("flat-foldable", frac(s.flat_foldable)); add("global", s.global_verdict); break;
    case "shape": add("flat-foldable", frac(s.flat_foldable)); break;
    case "model":
      add("folder", typeof s.folder === "string" ? s.folder.split("/").filter(Boolean).pop() : null);
      break;
  }
  return out;
}

/** "03 TREE · R2" for a tree round, else the stage label. */
export function outputLabel(o: Output): string {
  return stageLabel(o.stage) + (o.stage === "tree" && o.round != null ? ` · R${o.round + 1}` : "");
}
```

Create `app/web/src/shortcuts.ts`:

```ts
export interface KeyLike {
  key: string; metaKey: boolean; ctrlKey: boolean; altKey: boolean; target: EventTarget | null;
}

/** Plain "N" starts a new run (Linear's single-key style; Chrome keeps ⌘N for a new window and never
 *  delivers it to the page). Never while typing in an editable element. */
export function isNewRunKey(e: KeyLike): boolean {
  if (e.key !== "n" && e.key !== "N") return false;
  if (e.metaKey || e.ctrlKey || e.altKey) return false;
  const t = e.target as { tagName?: string; isContentEditable?: boolean } | null;
  return !(t && (t.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(t.tagName ?? "")));
}
```

In `app/web/src/components/RunsSidebar.tsx`, replace the `const day = (iso: string) => { … };` block (lines 3–9) with:

```ts
/** "— TODAY", "— YESTERDAY", else "— YYYY-MM-DD" (local time). */
export function dayLabel(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (d.toDateString() === now.toDateString()) return "— TODAY";
  if (d.toDateString() === y.toDateString()) return "— YESTERDAY";
  const p = (n: number) => String(n).padStart(2, "0");
  return `— ${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}
```

In the same file, change `const d = day(r.created);` to `const d = dayLabel(r.created);`.

- [ ] **Step 4: Run the tests to verify they pass.**

Run: `npm test && npx tsc --noEmit`
Expected: every vitest file passes, and `tsc` prints nothing.

- [ ] **Step 5: Commit.**

```bash
git add app/web/src/types.ts app/web/src/runStore.ts app/web/src/shortcuts.ts app/web/src/components/RunsSidebar.tsx app/web/src/types.test.ts app/web/src/shortcuts.test.ts app/web/src/components/RunsSidebar.test.ts app/web/src/runStore.test.ts
git commit -m "app/web: stage labels, summary pairs, output labels, day headings, N-key predicate"
```

---

### Task 3: Shell restyle (tokens, sidebar, chat, stepper, filmstrip, toggle, N shortcut)

**Files:**
- Modify: `app/web/src/styles.css` (full rewrite)
- Create: `app/web/src/components/ThemeToggle.tsx`
- Modify: `app/web/src/components/RunsSidebar.tsx` (full rewrite)
- Modify: `app/web/src/components/StageBlock.tsx` (full rewrite)
- Modify: `app/web/src/components/Stepper.tsx`
- Modify: `app/web/src/components/Filmstrip.tsx`
- Modify: `app/web/src/components/Chat.tsx`
- Modify: `app/web/src/App.tsx`

**Interfaces:**
- Consumes:
  - from Task 1: `readPref`, `nextPref`, `applyPref`, `safeStorage` and `ThemePref` (in `theme.ts`);
  - from Task 2: `stageNum` and `stageLabel` (in `types.ts`), `dayLabel` (in `RunsSidebar.tsx`), and `isNewRunKey` (in `shortcuts.ts`).
- Produces: the CSS class names Task 4 relies on. `styles.css` holds a block delimited by `/* ── viewer (Task 4 replaces this block) ── */` and `/* ── end viewer ── */`, which keeps the current viewer markup (`.viewer`, `.vtools`, `.follow`) working on the new tokens until Task 4 replaces it.

- [ ] **Step 1: Rewrite `app/web/src/styles.css`** with exactly:

```css
/* Pleatwright app. Form: folding diagram (mono, square corners, 1px rules, numbered steps).
   Colours: pro-tool greys + one blue accent. Dark is the default; light applies for
   data-theme="light", or for System (no data-theme) on a light OS. See src/theme.ts. */
:root {
  --bg:#1e1e1e; --panel:#252525; --raise:#2c2c2c; --line:#3d3d3d; --text:#e6e6e6; --muted:#8f8f8f;
  --user:#333333; --accent:#0d99ff; --accent-fg:#ffffff; --ok:#3ecf7a; --bad:#e33b2e;
  --canvas:#1a1a1a; --dot:#333333; --mountain:#e33b2e; --valley:#2f55d4;
  --sheet:#ffffff; --sheet-edge:transparent;
  --mono:"IBM Plex Mono", "SF Mono", Menlo, ui-monospace, monospace;
  color-scheme:dark; font:12px/1.5 var(--mono); color:var(--text); background:var(--bg);
}
:root[data-theme="light"] {
  --bg:#f4f1e8; --panel:#ece8dc; --raise:#fbf9f3; --line:#1d1d1b; --text:#1d1d1b; --muted:#6d6a62;
  --user:#e4dfd0; --ok:#1f8a4c; --canvas:#f4f1e8; --dot:#e1dccd; --sheet-edge:#1d1d1b;
  color-scheme:light;
}
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    --bg:#f4f1e8; --panel:#ece8dc; --raise:#fbf9f3; --line:#1d1d1b; --text:#1d1d1b; --muted:#6d6a62;
    --user:#e4dfd0; --ok:#1f8a4c; --canvas:#f4f1e8; --dot:#e1dccd; --sheet-edge:#1d1d1b;
    color-scheme:light;
  }
}

* { box-sizing:border-box; border-radius:0 }
body { margin:0; overflow:hidden }
html, body, #root { height:100% }
button { font:inherit; color:inherit; cursor:pointer }
button:disabled { cursor:default }
textarea { font:inherit }
:focus-visible { outline:1px solid var(--accent); outline-offset:-1px }
.muted { color:var(--muted) }
.shell { display:flex; flex-direction:column; height:100% }
.app { display:grid; grid-template-columns:220px 400px 1fr; grid-template-rows:minmax(0, 1fr); flex:1; min-height:0 }

/* ── sidebar ── */
.sidebar { min-height:0; display:flex; flex-direction:column; background:var(--panel); border-right:1px solid var(--line) }
.sidebar .runs { flex:1; min-height:0; overflow:auto; padding:10px }
.sidebar .new { display:flex; justify-content:space-between; width:100%; margin-bottom:4px; padding:6px 8px;
                border:1px solid var(--line); background:var(--raise); text-align:left; text-transform:uppercase }
.sidebar .new .hint { color:var(--muted) }
.sidebar .day { margin:12px 0 3px; color:var(--muted); font-size:10px }
.sidebar .run { display:flex; justify-content:space-between; gap:6px; width:100%; padding:4px 8px; border:none;
                background:none; color:var(--muted); text-align:left; box-shadow:inset 2px 0 0 transparent }
.sidebar .run:hover { color:var(--text) }
.sidebar .run.on { background:var(--raise); color:var(--text); box-shadow:inset 2px 0 0 var(--accent) }
.mark { flex:none; width:1.2em; text-align:center }
.mark.done { color:var(--ok) } .mark.running, .mark.waiting { color:var(--accent) }
.mark.failed { color:var(--bad) } .mark.new { color:var(--muted) }
.sidebar-foot { flex:none; padding:8px 10px; border-top:1px solid var(--line) }
.theme-toggle { width:100%; padding:4px 8px; border:1px solid var(--line); background:none; color:var(--muted);
                text-align:left; text-transform:uppercase }
.theme-toggle:hover { color:var(--text) }

/* ── chat ── */
.chat { min-height:0; min-width:0; overflow:hidden; display:flex; flex-direction:column; border-right:1px solid var(--line) }
.msgs { flex:1; min-height:0; overflow:auto; padding:12px; display:flex; flex-direction:column; gap:8px }
.user { align-self:flex-end; max-width:85%; padding:5px 10px; background:var(--user); border:1px solid var(--line); white-space:pre-wrap }
.assistant { white-space:pre-wrap }
.assistant::before { content:"● "; color:var(--accent) }
.block { display:flex; align-items:center; gap:8px; width:100%; padding:5px 8px; border:1px solid var(--line);
         background:var(--raise); color:var(--text); text-align:left }
.block.sel { border-color:var(--accent); box-shadow:inset 2px 0 0 var(--accent) }
.block .thumb { flex:none; width:40px; height:30px; display:flex; align-items:center; justify-content:center;
                object-fit:contain; border:1px solid var(--line); background:var(--canvas); color:var(--muted); font-size:10px }
.block .num { flex:none; color:var(--muted) }
.block .title { flex:none }
.block .sum { margin-left:auto; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; color:var(--muted) }
.review { display:flex; align-items:center; gap:10px }
.failed { padding:8px; border:1px solid var(--bad); box-shadow:inset 2px 0 0 var(--bad) }
.failed .actions { margin-top:6px }
.empty-run { margin:auto; text-align:center; color:var(--muted) }
.empty-run h3 { margin:0 0 6px; color:var(--text); font-weight:600; text-transform:uppercase }
.composer { margin:10px; display:flex; align-items:flex-start; gap:8px; padding:6px 8px; border:1px solid var(--line); background:var(--raise) }
.composer:focus-within { border-color:var(--accent) }
.composer .prompt { flex:none; padding-top:2px; color:var(--accent) }
.composer textarea { flex:1; resize:none; border:none; outline:none; padding:2px 0; background:none; color:var(--text) }

/* ── buttons, banner, toast ── */
.btn { padding:4px 12px; border:1px solid var(--accent); background:var(--accent); color:var(--accent-fg);
       font-weight:600; text-transform:uppercase; letter-spacing:.04em }
.btn:disabled { opacity:.4 }
.btn.ghost { border-color:var(--line); background:none; color:var(--text); font-weight:400 }
.banner { padding:6px 12px; background:var(--bad); color:#fff }
.toast { position:fixed; bottom:16px; left:50%; transform:translateX(-50%); display:flex; gap:10px; align-items:center;
         padding:8px 14px; border:1px solid var(--bad); background:var(--raise) }

/* ── outputs: stepper ── */
.out { min-height:0; min-width:0; overflow:hidden; display:flex; flex-direction:column }
.stepper { flex:none; display:flex; border-bottom:1px solid var(--line); background:var(--panel) }
.step { flex:1; min-width:0; padding:7px 4px; border:none; border-right:1px solid var(--line); background:none;
        color:var(--muted); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis }
.step:last-child { border-right:none }
.step .ic { margin-right:4px }
.step.done, .step.running, .step.failed { color:var(--text) }
.step.done .ic { color:var(--ok) } .step.failed .ic { color:var(--bad) }
.step.waiting { background:var(--accent); color:var(--accent-fg); font-weight:600 }
.step.skipped { text-decoration:line-through }
.step.running::before { content:""; display:inline-block; width:9px; height:9px; margin-right:5px; vertical-align:-1px;
                        border:2px solid transparent; border-top-color:currentColor; border-radius:50%; animation:spin .8s linear infinite }
@keyframes spin { to { transform:rotate(360deg) } }
@media (prefers-reduced-motion: reduce) { .step.running::before { animation-duration:3s } }

/* ── viewer (Task 4 replaces this block) ── */
.viewer { flex:1; margin:10px; position:relative; overflow:hidden; min-height:0; border:1px solid var(--line); background:var(--canvas) }
.viewer-empty { display:flex; align-items:center; justify-content:center; height:100%; color:var(--muted) }
.vtools { position:absolute; top:8px; right:8px; z-index:2; display:flex; gap:4px }
.vtools button { padding:2px 8px; border:1px solid var(--line); background:var(--panel); color:var(--text); font-size:11px }
.vtools button.on { background:var(--accent); color:var(--accent-fg) }
.follow { position:absolute; top:8px; left:8px; z-index:2; border:none; background:none; color:var(--muted); font-size:11px }
.pz { width:100%; height:100%; overflow:hidden; cursor:grab }
.pz > * { transform-origin:0 0 }
.cp.no-hinges line[stroke="green"] { display:none }
.cp.mono line[stroke="red"], .cp.mono line[stroke="blue"] { stroke:#888 }
.cp svg { width:100%; height:100%; background:var(--sheet) }
/* ── end viewer ── */

/* ── filmstrip ── */
.film { flex:none; display:flex; gap:6px; padding:8px 10px; overflow-x:auto; border-top:1px solid var(--line); background:var(--panel) }
.frame { position:relative; flex:none; width:78px; height:52px; overflow:hidden; display:flex; align-items:flex-end; padding:0;
         border:1px solid var(--line); background:var(--canvas); color:var(--muted); font-size:9px; text-align:left }
.frame img { position:absolute; inset:0; width:100%; height:100%; object-fit:contain }
.frame span { position:relative; padding:0 4px; background:var(--panel); border-top:1px solid var(--line); border-right:1px solid var(--line) }
.frame.on { border-color:var(--accent); box-shadow:inset 0 0 0 1px var(--accent); color:var(--text) }
.frame.none { border-style:dashed; background:none }
```

- [ ] **Step 2: Create `app/web/src/components/ThemeToggle.tsx`:**

```tsx
import { useState } from "react";
import { applyPref, nextPref, readPref, safeStorage, type ThemePref } from "../theme";

const LABEL: Record<ThemePref, string> = { system: "◐ System", light: "☀ Light", dark: "☾ Dark" };

/** Cycles System → Light → Dark. index.html's head script applied the stored choice before paint. */
export function ThemeToggle() {
  const [pref, setPref] = useState<ThemePref>(() => readPref(safeStorage()));
  const cycle = () => {
    const n = nextPref(pref);
    applyPref(n, document.documentElement, safeStorage());
    setPref(n);
  };
  return (
    <button className="theme-toggle" onClick={cycle}
            aria-label={`Theme: ${pref}. Switch to ${nextPref(pref)}.`}>{LABEL[pref]}</button>
  );
}
```

- [ ] **Step 3: Rewrite `app/web/src/components/RunsSidebar.tsx`** with exactly this. `dayLabel` is unchanged from Task 2.

```tsx
import type { RunSummary } from "../types";
import { ThemeToggle } from "./ThemeToggle";

/** "— TODAY", "— YESTERDAY", else "— YYYY-MM-DD" (local time). */
export function dayLabel(iso: string, now: Date = new Date()): string {
  const d = new Date(iso);
  const y = new Date(now);
  y.setDate(now.getDate() - 1);
  if (d.toDateString() === now.toDateString()) return "— TODAY";
  if (d.toDateString() === y.toDateString()) return "— YESTERDAY";
  const p = (n: number) => String(n).padStart(2, "0");
  return `— ${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

const MARK: Record<RunSummary["status"], string> = { done: "✓", running: "…", waiting: "⏸", failed: "✕", new: "·" };

export function RunsSidebar({ runs, current, onOpen, onNew }: {
  runs: RunSummary[]; current: string | null; onOpen: (id: string) => void; onNew: () => void;
}) {
  let lastDay = "";
  return (
    <div className="sidebar">
      <div className="runs">
        <button className="new" onClick={onNew} title="New run (N)">
          <span>[+] New run</span><span className="hint" aria-hidden="true">N</span>
        </button>
        {runs.map((r) => {
          const d = dayLabel(r.created);
          const head = d !== lastDay ? <div className="day">{(lastDay = d)}</div> : null;
          return (
            <div key={r.id}>
              {head}
              <button className={`run${r.id === current ? " on" : ""}`} onClick={() => onOpen(r.id)}
                      title={r.prompt} aria-current={r.id === current ? "true" : undefined}>
                <span>{r.subject}</span>
                <span className={`mark ${r.status}`} role="img" aria-label={r.status}>{MARK[r.status]}</span>
              </button>
            </div>);
        })}
      </div>
      <div className="sidebar-foot"><ThemeToggle /></div>
    </div>
  );
}
```

- [ ] **Step 4: Rewrite `app/web/src/components/StageBlock.tsx`** with exactly:

```tsx
import { fileUrl } from "../api";
import { outputTitle, summaryLine } from "../runStore";
import { stageNum, type Output } from "../types";

export function StageBlock({ runId, o, selected, onClick }: {
  runId: string; o: Output; selected: boolean; onClick: () => void;
}) {
  const img = o.files.find((f) => /\.(png|jpe?g|webp|svg)$/i.test(f));
  return (
    <button className={`block${selected ? " sel" : ""}`} onClick={onClick}>
      {img ? <img className="thumb" src={fileUrl(runId, img)} alt={outputTitle(o)} />
           : <span className="thumb">{o.stage === "mesh" || o.stage === "model" ? "3D" : "—"}</span>}
      <span className="num">{stageNum(o.stage)}</span>
      <span className="title">{outputTitle(o)}</span>
      <span className="sum">{summaryLine(o)}</span>
    </button>
  );
}
```

- [ ] **Step 5: Stepper.** In `app/web/src/components/Stepper.tsx`:

Change the import `import { STAGES, type RunView } from "../types";` to:

```ts
import { STAGES, stageLabel, type RunView, type StageStatus } from "../types";
```

Replace `const ICON = { done: "✓ ", running: "", waiting: "⏸ ", failed: "✕ ", skipped: "", todo: "" };` with:

```ts
const ICON: Record<StageStatus, string> = { done: "✓", running: "", waiting: "⏸", failed: "✕", skipped: "", todo: "" };
```

Replace the `<button …>…</button>` returned in the `STAGES.map` with:

```tsx
          <button key={s} className={`step ${st}`} disabled={!latest[s]} title={st}
                  aria-label={`${stageLabel(s)}: ${st}`}
                  onClick={() => latest[s] && onSelect(latest[s]!.key)}>
            {ICON[st] && <span className="ic" aria-hidden="true">{ICON[st]}</span>}
            {stageLabel(s)}{secs != null ? ` ${secs}s` : ""}
          </button>);
```

- [ ] **Step 6: Filmstrip.** In `app/web/src/components/Filmstrip.tsx`, change `import { STAGES, type RunView } from "../types";` to `import { STAGES, stageLabel, type RunView } from "../types";`, and change `<span>{s}</span>` to `<span>{stageLabel(s)}</span>`.

- [ ] **Step 7: Chat.** In `app/web/src/components/Chat.tsx`, make these replacements.

(a) In the no-run branch, replace

```tsx
        <div className="composer">
          <textarea rows={2} value={text} disabled={!canStart} placeholder="a dog"
```

with

```tsx
        <div className="composer">
          <span className="prompt" aria-hidden="true">&gt;</span>
          <textarea rows={2} value={text} disabled={!canStart} placeholder="a dog"
```

(b) Replace the failed-item retry wrapper

```tsx
                <div style={{ marginTop: 6 }}><button className="btn" onClick={() => send({ type: "retry" })}>Retry</button></div>}
```

with

```tsx
                <div className="actions"><button className="btn ghost" onClick={() => send({ type: "retry" })}>Retry</button></div>}
```

(c) Replace the review block

```tsx
        {reviewing && (
          <div>
            <button className="btn" disabled={!view.review!.canApprove}
                    onClick={() => send({ type: "approve" })}>Approve</button>
            <span className="muted" style={{ marginLeft: 8, color: "var(--muted)" }}>
              or type what is wrong with the tree ↓</span>
          </div>)}
```

with

```tsx
        {reviewing && (
          <div className="review">
            <button className="btn" disabled={!view.review!.canApprove}
                    onClick={() => send({ type: "approve" })}>Approve</button>
            <span className="muted">or type what is wrong with the tree ↓</span>
          </div>)}
```

(d) Replace the ended composer

```tsx
        <div className="composer"><button className="btn" onClick={onNewRun}>＋ New run</button></div>
```

with

```tsx
        <div className="composer"><button className="btn" onClick={onNewRun}>[+] New run</button></div>
```

(e) In the run composer, replace

```tsx
        <div className="composer">
          <textarea rows={2} value={text} disabled={!reviewing} aria-label="Message about the tree"
```

with

```tsx
        <div className="composer">
          <span className="prompt" aria-hidden="true">&gt;</span>
          <textarea rows={2} value={text} disabled={!reviewing} aria-label="Message about the tree"
```

- [ ] **Step 8: The `N` shortcut.** In `app/web/src/App.tsx`:

Add the import `import { isNewRunKey } from "./shortcuts";` after the `./runStore` import.

Directly after the line `const select = (key: string) => dispatch({ type: "select", key });`, add:

```tsx
  // "N" starts a new run (see shortcuts.ts). A ref so the once-registered listener calls the current `open`.
  const openRef = useRef(open);
  openRef.current = open;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (isNewRunKey(e)) { e.preventDefault(); openRef.current(null); } };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, []);
```

`useRef` and `useEffect` are already imported.

- [ ] **Step 9: Verify.**

Run: `npm test && npm run build`
Expected: all vitest files pass, `tsc` is clean, and the build succeeds.
Then run `grep -n 'style={{' src/components/Chat.tsx`. It must print nothing: the inline styles moved to CSS.

- [ ] **Step 10: Commit.**

```bash
git add app/web/src/styles.css app/web/src/components/ThemeToggle.tsx app/web/src/components/RunsSidebar.tsx app/web/src/components/StageBlock.tsx app/web/src/components/Stepper.tsx app/web/src/components/Filmstrip.tsx app/web/src/components/Chat.tsx app/web/src/App.tsx
git commit -m "app/web: folding-diagram restyle on theme tokens; theme toggle, numbered stages, status marks, N for a new run"
```

---

### Task 4: Viewer header, dotted canvas, crease colours

**Files:**
- Create: `app/web/src/components/ViewerHeader.tsx`
- Modify: `app/web/src/App.tsx` (the `.viewer` block)
- Modify: `app/web/src/components/Viewer.tsx`, `CPView.tsx`, `MeshView.tsx`, `ModelView.tsx`
- Modify: `app/web/src/styles.css` (replace the viewer block)
- Modify: `app/README.md`

**Interfaces:**
- Consumes: from Task 2, `summaryPairs(o)` and `outputLabel(o)` (in `runStore.ts`); from Task 3, the viewer-block markers in `styles.css`.
- Produces: `ToolSlot: React.Context<HTMLElement | null>`; `Tools({ children })`, which portals into the slot and renders nothing without one; `ViewerHeader({ output, following, onFollow, slotRef })`.

- [ ] **Step 1: Create `app/web/src/components/ViewerHeader.tsx`:**

```tsx
import { createContext, useContext, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { outputLabel, summaryPairs } from "../runStore";
import type { Output } from "../types";

/** The header's tool area; views render their buttons into it through <Tools>. */
export const ToolSlot = createContext<HTMLElement | null>(null);

/** A view's own buttons, shown in the viewer header (nothing until the header has mounted). */
export function Tools({ children }: { children: ReactNode }) {
  const el = useContext(ToolSlot);
  return el ? createPortal(children, el) : null;
}

export function ViewerHeader({ output, following, onFollow, slotRef }: {
  output: Output | null; following: boolean; onFollow: () => void;
  slotRef: (el: HTMLDivElement | null) => void;
}) {
  return (
    <div className="vhead">
      <span className="vh-title">{output ? outputLabel(output) : "—"}</span>
      {output && summaryPairs(output).map(([k, v]) => (
        <span key={k} className="vh-pair"><span className="muted">{k}</span>{v}</span>))}
      <span className="vh-gap" />
      {!following && <button className="vh-follow" onClick={onFollow}>● follow latest</button>}
      <div className="vh-tools" ref={slotRef} />
    </div>
  );
}
```

- [ ] **Step 2: App viewer block.** In `app/web/src/App.tsx`:

Add the import `import { ToolSlot, ViewerHeader } from "./components/ViewerHeader";` after the `./components/Viewer` import.

Add `const [slot, setSlot] = useState<HTMLDivElement | null>(null);` after the `connectNonce` state line.

Replace the whole `<div className="viewer"> … </div>` block (the one holding the `follow` button and `<Viewer …/>`) with:

```tsx
          <div className="viewer">
            <ViewerHeader output={view ? selectedOutput(view) : null} following={!view || view.followLatest}
                          onFollow={() => dispatch({ type: "follow" })} slotRef={setSlot} />
            <div className="canvas">
              <ToolSlot.Provider value={slot}>
                {view
                  ? <Viewer key={selectedOutput(view)?.key ?? "none"} runId={view.id}
                            output={selectedOutput(view)} allOutputs={view.outputs} onSelect={select} />
                  : <div className="viewer-empty">Start a run to see its outputs.</div>}
              </ToolSlot.Provider>
            </div>
          </div>
```

- [ ] **Step 3: Viewer.** In `app/web/src/components/Viewer.tsx`:

Add the import `import { Tools } from "./ViewerHeader";`.

Replace

```tsx
      {/* a model output has only model.fold; ModelView draws its own tools in this corner */}
      {ext(f) !== ".fold" && <div className="vtools">
```

with

```tsx
      {/* a model output has only model.fold; ModelView puts its own tools in the header */}
      {ext(f) !== ".fold" && <Tools>
```

Then replace the matching close `</div>}` (the line after the file-tab `map`) with `</Tools>}`.

- [ ] **Step 4: CPView.** In `app/web/src/components/CPView.tsx`:

Add the import `import { Tools } from "./ViewerHeader";`.

Replace

```tsx
      <div className="vtools">
        <button className={hinges ? "on" : ""} onClick={() => setHinges(!hinges)}>hinges</button>
        <button className={mv ? "on" : ""} onClick={() => setMv(!mv)}>M/V colours</button>
      </div>
```

with

```tsx
      <Tools>
        <button className={hinges ? "on" : ""} onClick={() => setHinges(!hinges)}>hinges</button>
        <button className={mv ? "on" : ""} onClick={() => setMv(!mv)}>M/V colours</button>
      </Tools>
```

Update the doc comment line `(COrigami semantics: red mountain, blue valley, black border, green hinge). */` to:

```ts
 * (COrigami semantics: red mountain, blue valley, black border, green hinge). The file is never
 * changed; styles.css only recolours red/blue on screen to --mountain/--valley. */
```

- [ ] **Step 5: MeshView.** In `app/web/src/components/MeshView.tsx`:

Add the import `import { Tools } from "./ViewerHeader";`.

Change `<Canvas camera={{ position: HOME, fov: 40 }}>` to:

```tsx
        <Canvas camera={{ position: HOME, fov: 40 }} gl={{ alpha: true }}>
```

Replace

```tsx
      <div className="vtools" style={{ top: "auto", bottom: 8 }}>
        <button onClick={() => setNonce((n) => n + 1)}>reset view</button>
      </div>
```

with

```tsx
      <Tools>
        <button onClick={() => setNonce((n) => n + 1)}>reset view</button>
      </Tools>
```

- [ ] **Step 6: ModelView.** In `app/web/src/components/ModelView.tsx`:

Add the import `import { Tools } from "./ViewerHeader";`.

Change the two crease materials:

```tsx
      <lineSegments geometry={geos.m} frustumCulled={false}><lineBasicMaterial color="#e33b2e" /></lineSegments>
      <lineSegments geometry={geos.v} frustumCulled={false}><lineBasicMaterial color="#2f55d4" /></lineSegments>
```

Directly above them, add the comment `{/* --mountain / --valley from styles.css; three.js cannot read CSS variables */}`. The paper colours `#f4efe6` and `#d08a2a` stay.

Replace

```tsx
      <div className="vtools">
        {!overview && <button onClick={() => setResetNonce((n) => n + 1)}>reset view</button>}
```

with

```tsx
      <Tools>
        {!overview && <button onClick={() => setResetNonce((n) => n + 1)}>reset view</button>}
```

and its closing `</div>` (after the `overview.png` button) with `</Tools>`.

Change `<Canvas camera={{ position: pose.position, up: [...VIEW_UP], fov: 40, near: pose.near, far: pose.far }}>` to:

```tsx
            <Canvas camera={{ position: pose.position, up: [...VIEW_UP], fov: 40, near: pose.near, far: pose.far }}
                    gl={{ alpha: true }}>
```

Replace the slider row

```tsx
          <div style={{ position: "absolute", left: 12, right: 12, bottom: 10, display: "flex", gap: 8, alignItems: "center", zIndex: 2 }}>
            <button className="btn ghost" onClick={() => setPlaying(!playing)}>{playing ? "❚❚" : "▶"}</button>
            <input type="range" min={0} max={100} value={pct} style={{ flex: 1 }}
                   onChange={(e) => { setPlaying(false); setPct(Number(e.target.value)); }} />
            <span style={{ width: 44, textAlign: "right" }}>{pct}%</span>
          </div>
```

with

```tsx
          <div className="foldbar">
            <button className="btn ghost" onClick={() => setPlaying(!playing)}>{playing ? "❚❚" : "▶"}</button>
            <input type="range" min={0} max={100} value={pct} aria-label="Fold"
                   onChange={(e) => { setPlaying(false); setPct(Number(e.target.value)); }} />
            <span className="pct">{pct}%</span>
          </div>
```

- [ ] **Step 7: Replace the viewer CSS block.** In `app/web/src/styles.css`, replace everything from `/* ── viewer (Task 4 replaces this block) ── */` through `/* ── end viewer ── */` (inclusive) with:

```css
/* ── viewer: header bar + dotted canvas ── */
.viewer { flex:1; min-height:0; display:flex; flex-direction:column }
.vhead { flex:none; height:32px; display:flex; align-items:center; gap:14px; padding-left:10px; overflow:hidden;
         white-space:nowrap; border-bottom:1px solid var(--line); background:var(--panel) }
.vh-title { font-weight:600 }
.vh-pair .muted { margin-right:5px }
.vh-gap { flex:1 }
.vh-follow { padding:0; border:none; background:none; color:var(--accent) }
.vh-tools { display:flex; align-self:stretch }
.vh-tools button { padding:0 10px; border:none; border-left:1px solid var(--line); background:none; color:var(--muted);
                   font-size:11px; text-transform:uppercase }
.vh-tools button:hover { color:var(--text) }
.vh-tools button.on { background:var(--accent); color:var(--accent-fg) }
.canvas { flex:1; min-height:0; position:relative; overflow:hidden; background-color:var(--canvas);
          background-image:radial-gradient(var(--dot) 1px, transparent 1px); background-size:12px 12px }
.viewer-empty { display:flex; align-items:center; justify-content:center; height:100%; color:var(--muted) }
.pz { width:100%; height:100%; overflow:hidden; cursor:grab }
.pz > * { transform-origin:0 0 }
/* The CP sheet is a square of paper centred on the dots, whatever the canvas's aspect. */
.cp { display:flex; align-items:center; justify-content:center; container-type:size }
.cp svg { width:min(100cqw, 100cqh); height:min(100cqw, 100cqh); background:var(--sheet); outline:1px solid var(--sheet-edge) }
.cp line[stroke="red"] { stroke:var(--mountain) }
.cp line[stroke="blue"] { stroke:var(--valley) }
.cp.no-hinges line[stroke="green"] { display:none }
.cp.mono line[stroke="red"], .cp.mono line[stroke="blue"] { stroke:#888 }
.foldbar { position:absolute; left:12px; right:12px; bottom:10px; z-index:2; display:flex; gap:8px; align-items:center }
.foldbar input[type="range"] { flex:1; accent-color:var(--accent) }
.foldbar .pct { width:44px; text-align:right }
```

- [ ] **Step 8: README.** In `app/README.md`, after the bullet that begins `* The server listens on 127.0.0.1 only.`, add:

```markdown
* The look follows `docs/superpowers/specs/2026-10-08-pleatwright-app-restyle-design.md`. The theme follows macOS by default; the button at the foot of the runs sidebar cycles System → Light → Dark (remembered per browser). Press `N` to start a new run.
```

- [ ] **Step 9: Verify.**

Run: `npm test && npm run build`
Expected: all vitest files pass, `tsc` is clean, and the build succeeds.

Then run: `grep -rn 'vtools\|className="follow"' src/`
Expected: no output.

Then run: `grep -n 'style={{' src/components/ModelView.tsx src/components/MeshView.tsx`
Expected: only the `position: "absolute", inset: 0` canvas wrappers remain.

- [ ] **Step 10: Commit.**

```bash
git add app/web/src/components/ViewerHeader.tsx app/web/src/App.tsx app/web/src/components/Viewer.tsx app/web/src/components/CPView.tsx app/web/src/components/MeshView.tsx app/web/src/components/ModelView.tsx app/web/src/styles.css app/README.md
git commit -m "app/web: viewer header with stage numbers and tools, dotted canvas, transparent WebGL, display crease colours"
```

---

### Task 5: Browser verification and full suite (controller)

The controller runs this task, because it needs the Browser pane. No subagent is involved.

- [ ] **Step 1: Suite.** From the repo root, run `make test`. Expected: the pipeline and app server tests pass, with the same counts as on `main` (508 passed / 2 skipped; 63 passed). Then run `cd app/web && npm ci && npm test && npm run build`.
- [ ] **Step 2: Serve.** Run `preview_start` with `pleatwright-app`. That config is the fake provider with seeded runs from `.claude/launch.json`. The server serves `app/web/dist`, so the Step 1 build must come first. Then open a seeded completed run.
- [ ] **Step 3: Dark screenshots.** Use `resize_window colorScheme: dark` with no stored theme. Screenshot each view: image or skipped, mesh, tree round, packing CP, solved CP, shaped CP, and folded model (slider at 50% and 100%). Take each screenshot with the pane visible: a hidden pane stops rAF, so WebGL would be blank.
- [ ] **Step 4: Light screenshots.** Click the toggle until it reads `☀ LIGHT`, then repeat the Step 3 views.
- [ ] **Step 5: No flash.** With `dark` stored and the OS set to light, reload. Then run `javascript_tool` on `document.documentElement.dataset.theme` and confirm it is `"dark"`. Read `dist/index.html` and confirm the head script comes before the module script.
- [ ] **Step 6: Font is local.** Run `read_network_requests` with `urlPattern: "plex"`. Every request must go to `127.0.0.1:8000`.
- [ ] **Step 7: Console.** Run `read_console_messages` with `onlyErrors`. Expected: no errors.
- [ ] **Step 8: Shortcut.** With focus on the page body, press `N`. The new-run screen must appear. Then type `n` in the textarea; the run must not change.
- [ ] **Step 9: Record.** Append the outcome to the ledger and update the `pleatwright-app` memory with any new trap found.

/** Light/dark theme preference. "system" = no stored choice: no data-theme, so styles.css's color-scheme "light dark" follows the OS. */
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

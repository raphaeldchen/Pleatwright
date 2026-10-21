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

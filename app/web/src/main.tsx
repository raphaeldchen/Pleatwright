import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { ensureControlled } from "./browser/swControl";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/600.css";
import "./styles.css";

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);

// The site build has no server: a service worker answers the run-file URLs (browser/sw.ts).
// A page it does not control (Shift+Reload) reloads once (browser/swControl.ts).
if (import.meta.env.VITE_PW_TARGET === "site" && "serviceWorker" in navigator) {
  navigator.serviceWorker.register(`${import.meta.env.BASE_URL}sw.js`, { scope: import.meta.env.BASE_URL });
  let storage: Storage | null = null;
  try { storage = sessionStorage; } catch { /* blocked site data */ }
  void ensureControlled({ container: navigator.serviceWorker, storage, reload: () => location.reload() });
}

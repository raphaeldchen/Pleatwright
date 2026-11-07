import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { build, defineConfig, loadEnv, type Plugin } from "vite";
import react from "@vitejs/plugin-react";
import { configDefaults } from "vitest/config";
import { HEAD_SCRIPT } from "./src/theme";

const api = "http://127.0.0.1:8000";

// The static site (npm run build:site, `--mode site`): served from a GitHub Pages project
// site, so every URL is under SITE_BASE. Its own folder, and its own public directory:
// public-site/ holds the self-hosted Pyodide and py.zip, which the local server build must
// not ship.
const SITE_BASE = "/Pleatwright/";

const here = fileURLToPath(new URL(".", import.meta.url));

const isSite = (mode: string) => mode === "site" || loadEnv(mode, here, "VITE_").VITE_PW_TARGET === "site";

// The site's Content-Security-Policy. The one inline script is the theme head script
// (below), allowed by the hash of exactly that string; scripts/check-site.mjs recomputes
// the hash from the built index.html.
const cspFor = (inline: string) =>
  [
    "default-src 'self'",
    `script-src 'self' 'wasm-unsafe-eval' 'sha256-${createHash("sha256").update(inline, "utf8").digest("base64")}'`,
    "worker-src 'self'",
    "connect-src 'self'",
    "img-src 'self' blob: data:",
    "style-src 'self' 'unsafe-inline'",
    "object-src 'none'",
    "base-uri 'self'",
  ].join("; ");

// Sets data-theme from the stored choice before first paint (see src/theme.ts). The site
// build puts its CSP meta tag ahead of it: a policy applies only to what comes after it.
const themeHead = (site: boolean): Plugin => ({
  name: "pleatwright-theme-head",
  transformIndexHtml: () => [
    ...(site
      ? [{ tag: "meta", attrs: { "http-equiv": "Content-Security-Policy", content: cspFor(HEAD_SCRIPT) }, injectTo: "head-prepend" as const }]
      : []),
    { tag: "script", children: HEAD_SCRIPT, injectTo: "head-prepend" as const },
  ],
});

// The service worker is a second, classic (IIFE) bundle at <base>sw.js with its imports
// inlined: module service workers are not safe across Chrome, Firefox and Safari.
const serviceWorker = (): Plugin => ({
  name: "pleatwright-service-worker",
  apply: "build",
  async closeBundle() {
    await build({
      configFile: false,
      publicDir: false,
      logLevel: "warn",
      build: {
        outDir: "dist-site",
        emptyOutDir: false,
        copyPublicDir: false,
        lib: { entry: `${here}src/browser/sw.ts`, name: "pleatwrightSw", formats: ["iife"], fileName: () => "sw.js" },
      },
    });
  },
});

// The server build must not load apiBrowser at all: api.ts drops its code, but Vite emits
// the worker scripts it starts as soon as the module is loaded. So "./apiBrowser" is
// apiServer there (tests and dev keep the real module).
const serverOnly = (command: string, mode: string) =>
  command === "build" && !isSite(mode)
    ? [{ find: /^\.\/apiBrowser$/, replacement: `${here}src/apiServer.ts` }]
    : [];

export default defineConfig(({ command, mode }) => {
  const site = isSite(mode);
  return {
    base: site ? SITE_BASE : "/",
    publicDir: site ? "public-site" : "public",
    plugins: [react(), themeHead(site && command === "build"), ...(site && command === "build" ? [serviceWorker()] : [])],
    resolve: { alias: serverOnly(command, mode) },
    define: site ? { "import.meta.env.VITE_PW_TARGET": JSON.stringify("site") } : {},
    build: site ? { outDir: "dist-site", modulePreload: { polyfill: false } } : {},
    server: {
      host: "127.0.0.1",
      proxy: {
        "/status": api,
        "/runs": api,
        "/ws": { target: "ws://127.0.0.1:8000", ws: true },
      },
    },
    // e2e/ holds the Playwright tests (npm run e2e), which vitest must not collect.
    test: { environment: "node", exclude: [...configDefaults.exclude, "e2e/**"] },
  };
});

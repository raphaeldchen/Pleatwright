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

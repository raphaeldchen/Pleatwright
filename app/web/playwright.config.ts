// The site's end-to-end tests (e2e/): the built site in real browsers. Run
// `npm run e2e:prepare` first (the site build plus a dog_0 gallery in dist-site/), then
// `npm run e2e -- --project=chromium`. The site is served by `vite preview` under its
// GitHub Pages base path.
import { defineConfig, devices } from "@playwright/test";

const PORT = 4178;

export default defineConfig({
  testDir: "e2e",
  // Every fold test runs Pyodide (a few hundred MB of heap, a CPU core for its jobs):
  // one at a time keeps the timings near a quiet host's.
  workers: 1,
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}/Pleatwright/`,
    trace: "retain-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: {
    command: `npx vite preview --mode site --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: `http://127.0.0.1:${PORT}/Pleatwright/`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});

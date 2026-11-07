// The static site (npm run e2e:prepare: dist-site/ with a dog_0 gallery) in real browsers:
// the gallery, a real fold in Pyodide workers, cancel and retry, a reload mid-fold, and the
// Content-Security-Policy. Each test gets a fresh browser context, so a fresh IndexedDB
// and service worker.
import { expect, test, type Page, type Worker } from "@playwright/test";

const GALLERY_ID = "gallery-dog_0";
const GALLERY_LABEL = "dog roll 0";
const BROWSER_LABEL = "dog roll 0 (folded in your browser)";
const GALLERY_CP = "gallery/gallery-dog_0/Dog roll 0_46/solving_cp.svg";
// dog_0 folded in about 22 s in browser Python on a quiet M-series host; the brief's bound is
// 120 s, and these tests allow 180 s for a loaded host (or CI runner).
const FOLD_MS = 180_000;

// The page's console errors, attached to a failed test (a CSP refusal shows up here).
let consoleErrors: string[] = [];
test.beforeEach(({ page }) => {
  consoleErrors = [];
  page.on("console", (m) => { if (m.type() === "error") consoleErrors.push(m.text()); });
  page.on("pageerror", (e) => consoleErrors.push(`pageerror: ${e.message}`));
});
test.afterEach(async ({}, info) => {
  if (info.status !== info.expectedStatus && consoleErrors.length)
    await info.attach("console-errors", { body: consoleErrors.join("\n"), contentType: "text/plain" });
});

/** Open the site and wait until its service worker controls the page: it answers the
 *  run-file URLs (on a first visit it takes control a moment after load). */
async function openSite(page: Page, path = "./") {
  await page.goto(path);
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
}

/** The sidebar's button for the run whose label is exactly `label`. */
const sidebarRun = (page: Page, label: string) =>
  page.locator(".sidebar .run").filter({ has: page.getByText(label, { exact: true }) });

/** The step button for a stage in a given status, e.g. ("05 SOLVE", "running"). */
const step = (page: Page, label: string, status: string) =>
  page.getByRole("button", { name: `${label}: ${status}`, exact: true });

/** The chat's "[+] New run": shown only once the open run has its run_finished event. */
const finished = (page: Page) => page.locator(".chat .composer").getByRole("button", { name: "[+] New run" });

/** A file fetched by the page itself (so through its service worker), base64-encoded. */
async function pageFile(page: Page, url: string) {
  return page.evaluate(async (u) => {
    const r = await fetch(u);
    const bytes = new Uint8Array(await r.arrayBuffer());
    let bin = "";
    for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
    return { status: r.status, type: r.headers.get("content-type") ?? "", b64: btoa(bin) };
  }, url);
}

/** Open the dog_0 example and press "Fold it here"; returns the new browser run's id once
 *  it is open. */
async function foldHere(page: Page): Promise<string> {
  await openSite(page);
  await sidebarRun(page, GALLERY_LABEL).click();
  await page.getByRole("button", { name: "Fold it here" }).click();
  await page.waitForURL(/#run=(?!gallery-)[^&]+$/, { timeout: FOLD_MS });   // after the engine boots
  const id = new URLSearchParams(new URL(page.url()).hash.slice(1)).get("run")!;
  await expect(sidebarRun(page, BROWSER_LABEL)).toBeVisible();
  await expect(page.locator(".vh-label")).toHaveText("Folded in your browser");
  return id;
}

test("gallery_dog_0_opens_with_its_files", async ({ page }) => {
  await openSite(page);
  await expect(page.locator(".sidebar .group").first()).toHaveText("Examples");
  const row = sidebarRun(page, GALLERY_LABEL);
  await expect(row).toBeVisible();
  await row.click();
  await expect(step(page, "07 MODEL", "done")).toBeVisible();

  const cp = page.waitForResponse((r) => r.url().endsWith(`/${GALLERY_CP.split("/").map(encodeURIComponent).join("/")}`));
  await step(page, "05 SOLVE", "done").click();
  const res = await cp;
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("image/svg+xml");
  await expect(page.locator(".cp svg line").first()).toBeAttached();
});

test.describe("with service workers blocked", () => {
  test.use({ serviceWorkers: "block" });

  // An example's files are static: they load with no service worker at all (blocked, or a
  // Shift+Reload page it does not control), where a run-file URL would be the SPA fallback.
  test("gallery_files_load_without_a_service_worker", async ({ page }) => {
    await page.goto("./");
    const model = page.waitForResponse((r) => r.url().endsWith(`/gallery/${GALLERY_ID}/model.fold`));
    await sidebarRun(page, GALLERY_LABEL).click();
    await expect(step(page, "07 MODEL", "done")).toBeVisible();
    expect(await page.evaluate(() => navigator.serviceWorker?.controller ?? null)).toBeNull();
    await step(page, "07 MODEL", "done").click();
    const fold = await model;
    expect(fold.status()).toBe(200);
    expect(fold.headers()["content-type"] ?? "").not.toContain("text/html");
    await expect(page.locator("canvas")).toBeAttached();
    await expect(page.getByText("could not load the model")).toHaveCount(0);

    const cp = page.waitForResponse((r) => r.url().endsWith(`/${GALLERY_CP.split("/").map(encodeURIComponent).join("/")}`));
    await step(page, "05 SOLVE", "done").click();
    const res = await cp;
    expect(res.status()).toBe(200);
    expect(res.headers()["content-type"]).toContain("image/svg+xml");
    await expect(page.locator(".cp svg line").first()).toBeAttached();
  });
});

test("fold_here_finishes_and_matches_gallery", async ({ page }, info) => {
  test.setTimeout(FOLD_MS);
  const t0 = Date.now();
  const id = await foldHere(page);
  await expect(finished(page)).toBeVisible({ timeout: FOLD_MS });
  info.annotations.push({ type: "fold seconds", description: ((Date.now() - t0) / 1000).toFixed(1) });
  for (const s of ["04 PACK", "05 SOLVE", "06 SHAPE", "07 MODEL"]) await expect(step(page, s, "done")).toBeVisible();

  // The model view offers the solved CP for download: its href is the run's file URL.
  const href = await page.locator("a.dl", { hasText: "solving_cp.svg" }).getAttribute("href");
  expect(href).toBe(`/Pleatwright/runs/${id}/files/Dog%20roll%200_46/solving_cp.svg`);
  const mine = await pageFile(page, href!);
  const theirs = await pageFile(page, GALLERY_CP);
  expect(mine.status).toBe(200);
  expect(theirs.status).toBe(200);
  expect(mine.type).toContain("image/svg+xml");
  expect(mine.b64.length).toBeGreaterThan(1000);
  expect(Buffer.from(mine.b64, "base64").equals(Buffer.from(theirs.b64, "base64"))).toBe(true);

  // The packing CP is drawn from a set of hinges: byte-equal only if its line
  // order does not follow the set's (platform-dependent) iteration order.
  const packing = (base: string) => pageFile(page, `${base}/Dog%20roll%200_46/packing_cp.svg`);
  const minePack = await packing(`/Pleatwright/runs/${id}/files`);
  const theirPack = await packing(GALLERY_CP.split("/").slice(0, 2).join("/"));
  expect(minePack.status).toBe(200);
  expect(Buffer.from(minePack.b64, "base64").equals(Buffer.from(theirPack.b64, "base64"))).toBe(true);
});

test("cancel_mid_fold_then_retry_finishes", async ({ page }) => {
  test.setTimeout(FOLD_MS * 2);
  await foldHere(page);
  await expect(step(page, "05 SOLVE", "running")).toBeVisible({ timeout: FOLD_MS });
  await page.locator(".chat .composer").getByRole("button", { name: "Cancel" }).click();

  const failed = page.locator(".chat .failed").last();
  await expect(failed.locator("b")).toHaveText("solve cancelled");
  await expect(step(page, "05 SOLVE", "failed")).toBeVisible();
  await failed.getByRole("button", { name: "Retry" }).click();
  await expect(finished(page)).toBeVisible({ timeout: FOLD_MS });
  await expect(sidebarRun(page, BROWSER_LABEL).getByRole("img", { name: "done" })).toBeVisible({ timeout: 10_000 });
});

test("reload_mid_fold_offers_retry", async ({ page }) => {
  test.setTimeout(FOLD_MS * 2);
  const id = await foldHere(page);
  await expect(step(page, "05 SOLVE", "running")).toBeVisible({ timeout: FOLD_MS });
  await page.reload();
  await page.waitForFunction(() => !!navigator.serviceWorker.controller);
  expect(page.url()).toContain(`#run=${id}`);

  // The new page's engine finds the run mid-stage and marks it interrupted (recover()).
  const failed = page.locator(".chat .failed").last();
  await expect(failed.locator("b")).toHaveText("solve interrupted", { timeout: FOLD_MS });
  await expect(page.locator(".banner")).toHaveCount(0);                // not a read-only tab
  await expect(sidebarRun(page, BROWSER_LABEL).getByRole("img", { name: "failed" })).toBeVisible({ timeout: 10_000 });
  await failed.getByRole("button", { name: "Retry" }).click();
  await expect(finished(page)).toBeVisible({ timeout: FOLD_MS });
});

test("csp_blocks_external_fetch", async ({ page }) => {
  await openSite(page);
  await expect(page.evaluate(() => fetch("https://example.com"))).rejects.toThrow();
  // ...and it is the policy that refused it: without the CSP, CORS rejects this fetch too.
  const directive = await page.evaluate(() => new Promise<string>((resolve) => {
    addEventListener("securitypolicyviolation", (e) => resolve(e.effectiveDirective), { once: true });
    fetch("https://example.com").catch(() => {}).finally(() => setTimeout(() => resolve("no violation"), 2000));
  }));
  expect(directive).toBe("connect-src");
});

// The workers' policy comes from their own script responses, which the service worker
// gives one (sw.ts withWorkerPolicy). A no-cors fetch would resolve (opaque) without it.
test("worker_csp_blocks_external_fetch", async ({ page }) => {
  test.setTimeout(FOLD_MS);
  const outside = (w: Worker) => w.evaluate(() =>
    fetch("https://example.com/", { mode: "no-cors" }).then(() => "fetched", (e: Error) => `refused: ${e.message}`));
  const opts = (name: string) => ({ predicate: (w: Worker) => w.url().includes(`/assets/${name}`), timeout: FOLD_MS });
  const manager = page.waitForEvent("worker", opts("managerWorker"));
  const job = page.waitForEvent("worker", opts("jobWorker"));
  const script = page.waitForResponse((r) => r.url().includes("/assets/managerWorker"), { timeout: FOLD_MS });
  await openSite(page);
  await sidebarRun(page, GALLERY_LABEL).click();
  await page.getByRole("button", { name: "Fold it here" }).click();
  expect(await outside(await manager)).toMatch(/^refused/);
  expect(await outside(await job)).toMatch(/^refused/);
  expect((await script).headers()["content-security-policy"]).toContain("connect-src 'self'");
  // ...and Pyodide still runs under it: the job worker's pack finishes.
  await expect(step(page, "04 PACK", "done")).toBeVisible({ timeout: FOLD_MS });
});

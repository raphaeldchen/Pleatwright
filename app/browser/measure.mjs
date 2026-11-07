// Measure the gallery's rolls (gallery/index.json) folded in real browsers (spec §7.3, §7.5).
//
//   node app/browser/measure.mjs --browsers chromium,webkit --rolls all --results RESULTS.jsonl
//        [--gallery DIR] [--timeout-min 15] [--retry-failed] [--keep DIR]
//   node app/browser/measure.mjs --results RESULTS.jsonl --report            # the README's table
//   node app/browser/measure.mjs --results RESULTS.jsonl --heap-out app/browser/browser_heap.json
//
// It drives the built site (app/web/dist-site, served by `vite preview`) the way a visitor
// does: open the example, press "Fold it here", answer the layout card with its recommended
// layout, wait for run_finished (or a failed stage, a crash, or the timeout). Each roll x
// browser gets a fresh browser process, so one fold's heap does not carry into the next.
// Per pair it appends one JSON line to RESULTS: wall seconds, the wasm heap the job workers
// reported (`heap_mb` on a job's terminal message), the verdict, and whether the browser's
// solving_cp.svg / shaping_cp.svg equal the native gallery's (--gallery, default the site's
// own dist-site/gallery, folded natively by build_gallery.py). A restart skips pairs already
// in RESULTS.
//
// The heap is read without touching the site: an init script wraps `Worker` and records each
// job message's `heap_mb` on the page (the jobRelay's own `heaps()` is not exposed).
import { spawn } from "node:child_process";
import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const web = join(here, "..", "web");
const { chromium, firefox, webkit } = createRequire(join(web, "package.json"))("@playwright/test");
const ENGINES = { chromium, firefox, webkit };

const PORT = 4179;
const BASE = `http://127.0.0.1:${PORT}/Pleatwright/`;
/** A fold that peaked above this does not fit a browser tab (build_gallery.HEAP_LIMIT_MB). */
const HEAP_LIMIT_MB = 3500;
/** What browser_heap.json records for a roll some browser failed on. */
const FAILED_HEAP = 9999;

// ---------------------------------------------------------------- arguments
function parseArgs(argv) {
  const a = { browsers: ["chromium", "webkit"], rolls: "all", timeoutMin: 15, gallery: join(web, "dist-site", "gallery") };
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    const val = () => argv[++i];
    if (k === "--browsers") a.browsers = val().split(",").filter(Boolean);
    else if (k === "--rolls") a.rolls = val();
    else if (k === "--results") a.results = val();
    else if (k === "--gallery") a.gallery = val();
    else if (k === "--timeout-min") a.timeoutMin = Number(val());
    else if (k === "--keep") a.keep = val();
    else if (k === "--retry-failed") a.retryFailed = true;
    else if (k === "--report") a.report = true;
    else if (k === "--heap-out") a.heapOut = val();
    else throw new Error(`unknown argument ${k}`);
  }
  if (!a.results) throw new Error("--results FILE is required");
  return a;
}

/** roll -> its sidebar label (build_gallery.label()), from the gallery's index.json:
 *  dog_0 -> "dog roll 0", demo_scorpion -> "demo scorpion". */
const galleryLabels = (gallery) => Object.fromEntries(
  JSON.parse(readFileSync(join(gallery, "index.json"), "utf8")).map((row) => [row.id.replace(/^gallery-/, ""), row.prompt]));

function readResults(path) {
  if (!existsSync(path)) return [];
  return readFileSync(path, "utf8").split("\n").filter(Boolean).map((l) => JSON.parse(l));
}

// ---------------------------------------------------------------- comparing crease patterns
const LINE = /<line\b[^>]*\/>/g;
const attrs = (tag) => Object.fromEntries([...tag.matchAll(/([\w:-]+)="([^"]*)"/g)].map((m) => [m[1], m[2]]));

/** A line's endpoints in a canonical order, so a flipped segment equals itself. */
const geometryKey = (tag) => {
  const x = attrs(tag);
  const p = [`${x.x1},${x.y1}`, `${x.x2},${x.y2}`].sort();
  return p.join(" ");
};

/** How many elements of `a` have no partner in `b` (a multiset difference). */
function missing(a, b) {
  const left = new Map();
  for (const t of b) left.set(t, (left.get(t) ?? 0) + 1);
  let n = 0;
  for (const t of a) {
    const c = left.get(t) ?? 0;
    if (c > 0) left.set(t, c - 1); else n++;
  }
  return n;
}

/** Compare two crease-pattern SVGs: equal bytes, or how they differ. `diff` counts the <line>
 *  elements of `mine` that `theirs` lacks (as a set, so a reordering alone is 0); `geometry`
 *  counts those whose endpoints `theirs` also lacks, so `diff > 0, geometry == 0` means the
 *  same segments with another stroke or opacity (the spike's horse_0: mountain and valley
 *  swapped). `positional` counts the lines that differ at the same position. */
export function compareCp(mine, theirs) {
  if (mine === theirs) return { equal: true };
  const a = mine.match(LINE) ?? [];
  const b = theirs.match(LINE) ?? [];
  const out = { equal: false, lines: [a.length, b.length], diff: missing(a, b),
                geometry: missing(a.map(geometryKey), b.map(geometryKey)), positional: null };
  if (a.length === b.length) out.positional = a.filter((t, i) => t !== b[i]).length;
  if (out.diff === 0 && a.length === b.length) out.note = "same <line> elements, in another order or with other bytes outside them";
  return out;
}

// ---------------------------------------------------------------- the site server
async function reachable(url) {
  try { return (await fetch(url)).ok; } catch { return false; }
}

async function ensureServer() {
  if (await reachable(BASE)) return null;
  const p = spawn("npx", ["vite", "preview", "--mode", "site", "--host", "127.0.0.1", "--port", String(PORT), "--strictPort"],
                  { cwd: web, stdio: "ignore" });
  for (let i = 0; i < 120; i++) {
    if (await reachable(BASE)) return p;
    await new Promise((r) => setTimeout(r, 500));
  }
  p.kill();
  throw new Error(`the site did not come up at ${BASE} (run npm run e2e:prepare in app/web)`);
}

// ---------------------------------------------------------------- one fold
/** Wraps Worker so each worker's terminal job message leaves its `heap_mb` in window.__heaps,
 *  and a job worker's "dead" message its reason in window.__dead. */
const HEAP_SPY = () => {
  window.__heaps = [];
  window.__dead = [];
  const Real = window.Worker;
  window.Worker = class extends Real {
    constructor(...args) {
      super(...args);
      this.addEventListener("message", (e) => {
        const d = e.data;
        if (d && d.type === "msg" && typeof d.heap_mb === "number" && Array.isArray(d.msg))
          window.__heaps.push({ terminal: d.msg[0], heap_mb: d.heap_mb });
        if (d && d.type === "dead") window.__dead.push(String(d.reason));
      });
    }
  };
};

/** A file fetched by the page itself (so through its service worker), as base64. */
const fetchB64 = (page, url) => page.evaluate(async (u) => {
  const r = await fetch(u);
  const bytes = new Uint8Array(await r.arrayBuffer());
  let bin = "";
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
  return { status: r.status, b64: btoa(bin) };
}, url);

const text = (b64) => Buffer.from(b64, "base64").toString("utf8");

/** Whether the run's event log (as the page reads it) has its run_finished event. */
async function runFinished(page, runId) {
  const ev = await fetchB64(page, `${BASE}runs/${runId}/files/events.jsonl`).catch(() => null);
  return ev?.status === 200 && text(ev.b64).includes('"run_finished"');
}

async function foldOne(engine, roll, opts) {
  const t0 = Date.now();
  const rec = { roll, browser: engine, status: "failed", wall_s: null, fold_s: null, heap_mb: null,
                verdict: null, solving: null, shaping: null, error: null };
  const timeoutMs = opts.timeoutMin * 60_000;
  const browser = await ENGINES[engine].launch();
  try {
    const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    await page.addInitScript(HEAP_SPY);
    let crashed = false;
    page.on("crash", () => { crashed = true; });

    await page.goto(BASE);
    await page.waitForFunction(() => !!navigator.serviceWorker.controller, null, { timeout: 60_000 });
    const label = opts.labels[roll];
    if (!label) throw new Error(`${roll} is not in the gallery`);
    const row = page.locator(".sidebar .run").filter({ has: page.getByText(label, { exact: true }) });
    await row.click({ timeout: 30_000 });
    await page.getByRole("button", { name: "07 MODEL: done", exact: true }).waitFor({ timeout: 30_000 });
    const tClick = Date.now();
    await page.getByRole("button", { name: "Fold it here" }).click();
    await page.waitForURL(/#run=(?!gallery-)[^&]+$/, { timeout: timeoutMs });
    const tRun = Date.now();
    const runId = new URLSearchParams(new URL(page.url()).hash.slice(1)).get("run");

    // The old (finished) example's chat can still be on screen for a moment: wait for the new run's view.
    await page.locator(".vh-label").filter({ hasText: "Folded in your browser" }).waitFor({ timeout: 60_000 });
    const finished = page.locator(".chat .composer").getByRole("button", { name: "[+] New run" });
    const failed = page.locator(".chat .failed");
    const optBtn = page.locator(".layout-card button.lc-opt.rec");
    let chose = 0;
    for (;;) {
      if (crashed) { rec.error = "the page crashed"; break; }
      if (Date.now() - tClick > timeoutMs) { rec.error = `no result within ${opts.timeoutMin} min`; break; }
      try {
        if (await finished.isVisible() && await runFinished(page, runId)) { rec.status = "done"; break; }
        if (await failed.count()) {
          rec.error = ((await failed.last().innerText()) || "a stage failed").replace(/\s+/g, " ").slice(0, 300);
          break;
        }
        if (await optBtn.count() && await optBtn.first().isEnabled()) {
          chose++;
          await optBtn.first().click({ timeout: 5000 });
          await page.waitForTimeout(1000);
        }
      } catch (e) {
        if (crashed || page.isClosed()) { rec.error = "the page crashed"; break; }
        // a transient "element detached" while React re-renders: look again
      }
      await page.waitForTimeout(500);
    }
    const tEnd = Date.now();
    rec.wall_s = Math.round((tEnd - tClick) / 100) / 10;            // click to result, engine boot included
    rec.fold_s = Math.round((tEnd - tRun) / 100) / 10;              // run created to result
    rec.layout_choices = chose;

    if (!page.isClosed() && !crashed) {
      const heaps = await page.evaluate(() => window.__heaps ?? []).catch(() => []);
      if (heaps.length) rec.heap_mb = Math.round(Math.max(...heaps.map((h) => h.heap_mb)) * 10) / 10;
      rec.heaps = heaps.map((h) => `${h.terminal}:${Math.round(h.heap_mb)}`);
      const dead = await page.evaluate(() => window.__dead ?? []).catch(() => []);
      if (dead.length) rec.dead = dead;                              // the job worker's own reason
    }
    if (rec.status === "done" && !page.isClosed()) {
      const files = `runs/${runId}/files/`;
      const ev = await fetchB64(page, BASE + files + "events.jsonl").catch(() => null);
      if (ev?.status === 200) {
        const events = text(ev.b64).split("\n").filter(Boolean).map((l) => JSON.parse(l));
        const fin = events.findLast((e) => e.type === "run_finished");
        if (fin) { rec.verdict = fin.global_verdict ?? null; rec.grid = Number(fin.grid); rec.folder = fin.folder; rec.secs = fin.secs;
                    rec.solving_ff = fin.solving_ff; rec.shaping_ff = fin.shaping_ff; }
      }
      const href = await page.locator("a.dl", { hasText: "solving_cp.svg" }).first().getAttribute("href").catch(() => null);
      const folder = href ? decodeURIComponent(href.split("/files/")[1].split("/")[0]) : rec.folder;
      if (folder) {
        rec.folder = folder;
        for (const [key, name] of [["solving", "solving_cp.svg"], ["shaping", "shaping_cp.svg"]]) {
          const mine = await fetchB64(page, `${BASE}${files}${encodeURIComponent(folder)}/${name}`);
          const nativePath = join(opts.gallery, `gallery-${roll}`, folder, name);
          if (mine.status !== 200) { rec[key] = { equal: false, error: `browser file ${mine.status}` }; continue; }
          if (!existsSync(nativePath)) { rec[key] = { equal: false, error: "no native file at that folder (the grid differs?)" }; continue; }
          const cmp = compareCp(text(mine.b64), readFileSync(nativePath, "utf8"));
          rec[key] = cmp;
          if (!cmp.equal && opts.keep) {                     // the browser's file, for a closer look
            mkdirSync(opts.keep, { recursive: true });
            writeFileSync(join(opts.keep, `${roll}.${engine}.${name}`), text(mine.b64));
          }
        }
      }
    }
  } catch (e) {
    rec.error ??= String(e?.message ?? e).split("\n")[0].slice(0, 300);
    rec.wall_s ??= Math.round((Date.now() - t0) / 100) / 10;
  } finally {
    await browser.close().catch(() => {});
  }
  return rec;
}

// ---------------------------------------------------------------- reporting
/** The roll -> heap map for browser_heap.json: the most any browser that finished the roll
 *  reached, or FAILED_HEAP when some browser failed on it. */
export function heapMap(results) {
  const byRoll = new Map();
  for (const r of results) byRoll.set(r.roll, [...(byRoll.get(r.roll) ?? []), r]);
  const out = {};
  for (const [roll, rs] of [...byRoll].sort(([a], [b]) => a.localeCompare(b))) {
    const bad = rs.some((r) => r.status !== "done" || r.heap_mb == null);
    out[roll] = bad ? FAILED_HEAP : Math.max(...rs.map((r) => r.heap_mb));
  }
  return out;
}

const cell = (c) => {
  if (!c) return "-";
  if (c.equal) return "equal";
  if (c.error) return c.error;
  if (c.lines?.[0] === 0 && c.lines?.[1] > 0) return "NOT AN SVG (0 <line> elements)";
  const kind = c.geometry ? `geometry differs in ${c.geometry}` : c.diff ? "same segments, other stroke" : "same lines, other order";
  return `${c.diff}/${c.lines?.[1] ?? "?"} (${kind})`;
};

function report(results) {
  const browsers = [...new Set(results.map((r) => r.browser))];
  const rolls = [...new Set(results.map((r) => r.roll))].sort();
  const get = (roll, b) => results.findLast((r) => r.roll === roll && r.browser === b);
  const head = ["roll", ...browsers.flatMap((b) => [`${b} s`, `${b} heap MB`, `${b} verdict`, `${b} solving_cp`, `${b} shaping_cp`])];
  const lines = [`| ${head.join(" | ")} |`, `|${head.map(() => "---").join("|")}|`];
  for (const roll of rolls) {
    const cells = browsers.flatMap((b) => {
      const r = get(roll, b);
      if (!r) return Array(5).fill("-");
      if (r.status !== "done") return [String(r.wall_s ?? "-"), r.heap_mb != null ? String(r.heap_mb) : "-", `FAILED: ${r.error ?? "?"}`.replaceAll("|", "/"), "-", "-"];
      return [String(r.wall_s), r.heap_mb != null ? String(r.heap_mb) : "-", r.verdict ?? "-", cell(r.solving), cell(r.shaping)];
    });
    lines.push(`| ${roll} | ${cells.join(" | ")} |`);
  }
  return lines.join("\n");
}

// ---------------------------------------------------------------- main
async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.report) { console.log(report(readResults(a.results))); return; }
  if (a.heapOut) {
    const map = heapMap(readResults(a.results));
    writeFileSync(a.heapOut, JSON.stringify(map, null, 2) + "\n");
    console.log(`${Object.keys(map).length} rolls -> ${a.heapOut}; above ${HEAP_LIMIT_MB} MB: ${Object.entries(map).filter(([, v]) => v > HEAP_LIMIT_MB).map(([k]) => k).join(", ") || "none"}`);
    return;
  }
  a.labels = galleryLabels(a.gallery);
  const rolls = a.rolls === "all" ? Object.keys(a.labels) : a.rolls.split(",").filter(Boolean);
  const server = await ensureServer();
  try {
    for (const roll of rolls) {
      for (const engine of a.browsers) {
        const prior = readResults(a.results).findLast((r) => r.roll === roll && r.browser === engine);
        if (prior && !(a.retryFailed && prior.status !== "done")) continue;
        const rec = await foldOne(engine, roll, a);
        appendFileSync(a.results, JSON.stringify({ ...rec, at: new Date().toISOString() }) + "\n");
        console.log(`${roll} ${engine}: ${rec.status} ${rec.wall_s}s heap=${rec.heap_mb} ${rec.verdict ?? rec.error ?? ""} solving=${cell(rec.solving)} shaping=${cell(rec.shaping)}`);
      }
    }
  } finally {
    server?.kill();
  }
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  main().catch((e) => { console.error(e); process.exit(1); });
}

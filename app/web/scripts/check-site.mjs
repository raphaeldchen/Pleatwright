// Checks the site build (npm run build:site -> dist-site/) before it is published:
//   * index.html carries the site's Content-Security-Policy as the first thing in <head>,
//     and the hash in it is the sha256 of the one inline script the page has;
//   * sw.js exists and is a classic script (a module service worker is not safe across
//     Chrome, Firefox and Safari);
//   * the Pyodide files and py.zip are in the folder, where the site serves them from;
//   * no file names a host other than the site's own (Pyodide's own files excluded): http(s)
//     and ws(s) URLs, and protocol-relative ones (//host/...), which the workers could fetch.
// Exits 1 with one line per problem. Run `npm run build:site` first.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { Script } from "node:vm";

const HOST = "raphaeldchen.github.io";

// External URLs that may appear as text in the built files without the page ever fetching
// them. Each entry is a prefix and the reason it is harmless.
const ALLOWED = [
  ["http://www.w3.org/", "XML, SVG, MathML and XHTML namespace identifiers (React, three.js); never fetched"],
  ["https://reactjs.org/docs/error-decoder.html", "React's production error message, shown to the user; never fetched"],
  ["https://docs.pmnd.rs/react-three-fiber/", "react-three-fiber warning text; never fetched"],
  ["https://github.com/react-spring/react-use-measure/", "react-use-measure (via drei) warning text; never fetched"],
  ["https://www.gstatic.com/draco/versioned/decoders/", "drei's default Draco decoder path; MeshView passes useGLTF(src, false), so it is never used"],
];

// File types the URL scan skips: binary, nothing to read as text.
const BINARY = /\.(zip|wasm|png|jpe?g|gif|ico|woff2?|ttf|otf|glb)$/i;

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const dist = join(web, "dist-site");
const problems = [];
const bad = (msg) => problems.push(msg);
const sha256b64 = (s) => createHash("sha256").update(s, "utf8").digest("base64");

function files(dir) {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    return statSync(p).isDirectory() ? files(p) : [p];
  });
}

if (!existsSync(dist)) {
  console.error("site check failed:\n  dist-site/ does not exist (run npm run build:site)");
  process.exit(1);
}

// ---- index.html: CSP first, hash matches the inline script
const indexPath = join(dist, "index.html");
if (!existsSync(indexPath)) bad("index.html is missing");
else {
  const html = readFileSync(indexPath, "utf8");
  const head = html.slice(html.indexOf("<head>") + "<head>".length, html.indexOf("</head>"));
  const csp = /<meta\s+http-equiv="Content-Security-Policy"\s+content="([^"]*)"\s*\/?>/i.exec(head);
  if (!csp) bad("index.html has no Content-Security-Policy meta tag in <head>");
  else {
    const first = head.search(/<script\b/i);
    if (first >= 0 && first < csp.index) bad("a <script> comes before the Content-Security-Policy meta tag");
    const inline = [...html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/gi)].filter((m) => !/\bsrc\s*=/.test(m[1]));
    if (inline.length !== 1) bad(`expected exactly one inline script, found ${inline.length}`);
    else {
      const want = `'sha256-${sha256b64(inline[0][2])}'`;
      const m = /script-src\s([^;]*)/.exec(csp[1]);
      if (!m || !m[1].split(/\s+/).includes(want)) bad(`script-src does not carry the inline script's hash ${want}: ${csp[1]}`);
    }
    for (const dir of ["default-src 'self'", "worker-src 'self'", "connect-src 'self'", "object-src 'none'", "base-uri 'self'"]) {
      if (!csp[1].split(/;\s*/).includes(dir)) bad(`the policy lacks "${dir}"`);
    }
    if (/unsafe-eval|https?:/.test(csp[1].replace(/wasm-unsafe-eval/g, ""))) bad(`the policy allows eval or another origin: ${csp[1]}`);
  }
}

// ---- sw.js: present, a classic script
const swPath = join(dist, "sw.js");
if (!existsSync(swPath)) bad("sw.js is missing");
else {
  try { new Script(readFileSync(swPath, "utf8"), { filename: "sw.js" }); } // parsed as a classic script
  catch (e) { bad(`sw.js does not parse as a classic script (a module?): ${e.message}`); }
}

// ---- the files the site serves itself
for (const f of ["py.zip", "pyodide/pyodide.mjs", "pyodide/pyodide.asm.wasm", "pyodide/pyodide-lock.json"]) {
  if (!existsSync(join(dist, f))) bad(`${f} is missing (npm run fetch-pyodide / bundle-py)`);
}
const assets = existsSync(join(dist, "assets")) ? readdirSync(join(dist, "assets")) : [];
for (const w of ["managerWorker", "jobWorker"]) {
  if (!assets.some((a) => a.startsWith(w) && a.endsWith(".js"))) bad(`assets/${w}-*.js is missing: the browser build lost a worker`);
}

// ---- no other hosts
// A URL with a scheme, or a protocol-relative one: "//" (not after a scheme or a word) and a
// dotted host, so a "// comment" is not one.
const URL_RE = /\b(?:https?|wss?):\/\/[^\s"'`)<>\\,;]+|(?<![\w:/])\/\/[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+(?::\d+)?(?=[/"'`?#)\s]|$)[^\s"'`)<>\\,;]*/g;
for (const file of files(dist)) {
  const rel = relative(dist, file).split(sep).join("/");
  if (rel.startsWith("pyodide/") || BINARY.test(rel)) continue;
  const text = readFileSync(file, "latin1");
  for (const [url] of text.matchAll(URL_RE)) {
    let host;
    try { host = new URL(url, `https://${HOST}/`).host; } catch { bad(`${rel} names ${url}, which does not parse`); continue; }
    if (host === HOST) continue;
    if (ALLOWED.some(([prefix]) => url.startsWith(prefix))) continue;
    bad(`${rel} names ${url}`);
  }
}

if (problems.length) {
  console.error(`site check failed:\n${problems.map((p) => "  " + p).join("\n")}`);
  process.exit(1);
}
console.log("site check ok");

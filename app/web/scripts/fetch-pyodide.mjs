// Self-host Pyodide for the browser build: public-site/pyodide/ gets the core files from
// node_modules/pyodide and the wheels the pipeline imports, each checked against the
// sha256 in pyodide-lock.json. The wheels are downloaded here, at build time, from the
// jsDelivr copy of the release; the site itself never contacts a CDN.
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const VERSION = "314.0.7";
const CDN = `https://cdn.jsdelivr.net/pyodide/v${VERSION}/full/`;
const WANT = ["numpy", "matplotlib", "python-sat", "pillow"];
const CORE = [
  "pyodide.js",
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "python_stdlib.zip",
  "pyodide-lock.json",
];

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(web, "node_modules", "pyodide");
const dest = join(web, "public-site", "pyodide");

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

/** True when `path` exists and (if `hash` is given) holds exactly that content. */
function present(path, hash) {
  return existsSync(path) && (!hash || sha256(readFileSync(path)) === hash);
}

const installed = JSON.parse(readFileSync(join(src, "package.json"), "utf8")).version;
if (installed !== VERSION) throw new Error(`node_modules/pyodide is ${installed}, expected ${VERSION}`);

mkdirSync(dest, { recursive: true });
for (const name of CORE) {
  const from = join(src, name);
  const to = join(dest, name);
  if (!present(to, sha256(readFileSync(from)))) copyFileSync(from, to);
}

const lock = JSON.parse(readFileSync(join(dest, "pyodide-lock.json"), "utf8"));
if (lock.info.python == null) throw new Error("pyodide-lock.json has no info.python");

// the wheels, with their dependencies resolved through the lockfile
const need = new Set();
const stack = [...WANT];
while (stack.length) {
  const name = stack.pop();
  if (need.has(name)) continue;
  const pkg = lock.packages[name];
  if (!pkg) throw new Error(`pyodide-lock.json has no package ${name}`);
  need.add(name);
  stack.push(...pkg.depends);
}

let downloaded = 0;
for (const name of [...need].sort()) {
  const { file_name: file, sha256: expect } = lock.packages[name];
  const to = join(dest, file);
  if (present(to, expect)) continue;
  const res = await fetch(CDN + file);
  if (!res.ok) throw new Error(`${CDN + file}: HTTP ${res.status}`);
  const buf = Buffer.from(await res.arrayBuffer());
  const got = sha256(buf);
  if (got !== expect) throw new Error(`${file}: sha256 ${got} does not match the lockfile's ${expect}`);
  writeFileSync(to, buf);
  downloaded += 1;
}
console.log(`pyodide ${VERSION}: ${need.size} packages (${downloaded} downloaded) in ${dest}`);

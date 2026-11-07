// The end-to-end tests' site (npm run e2e:prepare): the site build in dist-site/ with a
// one-roll gallery (dog_0) in dist-site/gallery/. The gallery is folded natively by
// app/browser/build_gallery.py with the harness Python ($PYTHON, else python3).
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const run = (cmd, args) => execFileSync(cmd, args, { cwd: web, stdio: "inherit" });

for (const script of ["fetch-pyodide", "bundle-py", "build:site"]) run(npm, ["run", script]);

const out = mkdtempSync(join(tmpdir(), "pleatwright-gallery-"));
try {
  run(process.env.PYTHON || "python3", [join(web, "..", "browser", "build_gallery.py"), out, "--rolls", "dog_0"]);
  const dest = join(web, "dist-site", "gallery");
  rmSync(dest, { recursive: true, force: true });
  cpSync(out, dest, { recursive: true });
  console.log(`gallery (dog_0) copied to ${dest}`);
} finally {
  rmSync(out, { recursive: true, force: true });
}

// Node smoke test for the browser build's Python: load the self-hosted Pyodide from
// public-site/pyodide/, unzip public-site/py.zip into its in-memory filesystem (nothing is mounted
// from the repo), import pwbrowser, and fold dog_0 through jobchild.run_job.
// Run `npm run fetch-pyodide && npm run bundle-py` first. Fails if anything is requested
// over the network.
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadPyodide } from "pyodide";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const indexURL = join(web, "public-site", "pyodide") + "/";

// Pyodide reads local paths with fs and everything else with fetch, so a fetch of a
// URL that is not a local file is a network request.
const requested = [];
const realFetch = globalThis.fetch;
globalThis.fetch = (input, ...rest) => {
  const url = String(input?.url ?? input);
  requested.push(url);
  if (/^https?:/i.test(url)) throw new Error(`network request: ${url}`);
  return realFetch(input, ...rest);
};

const loaded = [];
const py = await loadPyodide({ indexURL, stdout: () => {}, stderr: () => {}, checkAPIVersion: true });
await py.loadPackage(["numpy", "matplotlib", "python-sat", "pillow"], {
  messageCallback: (m) => loaded.push(m),
  errorCallback: (m) => loaded.push(m),
});
if (loaded.some((m) => /https?:/i.test(m))) throw new Error(`a package came from the network: ${loaded.join("; ")}`);

py.unpackArchive(new Uint8Array(readFileSync(join(web, "public-site", "py.zip"))), "zip",{ extractDir: "/repo" });

py.globals.set("tree_json", readFileSync(join(web, "..", "..", "mcp_harness", "fixtures", "full17_v3_sticks", "dog_0.json"), "utf8"));
const result = JSON.parse(await py.runPythonAsync(`
import json, os, sys
sys.dont_write_bytecode = True
import matplotlib
matplotlib.use("Agg")
sys.path[:0] = ["/repo/mcp_harness", "/repo/app/server", "/repo/app/browser/py"]
import pwbrowser, jobchild  # the manager worker's import chain

out = "/runs/smoke"
os.makedirs(out)
with open(out + "/tree.json", "w") as f:
    f.write(tree_json)

posted = []
jobchild.run_job("pack", out, {}, posted.append)
jobchild.run_job("fold", out, {"certify_global": True, "options_dir": out + "/layout"}, posted.append)
done = posted[-1]
json.dumps({"kinds": [[m[0], m[1]] for m in posted], "done": done[2].get("grid"),
            "files": sorted(p for m in posted for p in m[3])})
`));

const folder = "Dog roll 0_46";
const fail = (msg) => { throw new Error(`${msg}: ${JSON.stringify(result)}`); };
if (result.done !== 46) fail("expected grid 46");
if (result.kinds.at(-1)[0] !== "done") fail("the last message is not done");
for (const f of ["packing_cp.svg", "solving_cp.svg", "shaping_cp.svg", "overview.png"]) {
  if (!result.files.includes(`${folder}/${f}`)) fail(`${folder}/${f} was not produced`);
}
const net = requested.filter((u) => /^https?:/i.test(u));
if (net.length) throw new Error(`network requests: ${net.join(", ")}`);
console.log("smoke ok");

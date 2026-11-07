import { describe, expect, it, vi } from "vitest";
import { StorageUnavailable } from "./runFiles";
import { resolveFileRequest, respond, withWorkerPolicy, WORKER_CSP } from "./sw";

const BASE = "/Pleatwright/";
const u = (path: string) => new URL(path, "https://example.github.io");

describe("resolveFileRequest", () => {
  it("matches_run_file_urls_under_base", () => {
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/tree.json"), BASE)).toEqual({ runId: "dog_0", rel: "tree.json" });
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/Dog_54/packing_cp.svg"), BASE)).toEqual({ runId: "dog_0", rel: "Dog_54/packing_cp.svg" });
    // segments are decoded
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/my%20dir/a%2Bb.json?x=1"), BASE)).toEqual({ runId: "dog_0", rel: "my dir/a+b.json" });
    expect(resolveFileRequest(u("/runs/dog_0/files/tree.json"), "/")).toEqual({ runId: "dog_0", rel: "tree.json" });
  });

  it("rejects_dotdot_and_bad_ids", () => {
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/../x.json"), BASE)).toBeNull();
    // the URL parser itself collapses dot segments, so this is the in-scope file it names
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/a/%2e%2e/x.json"), BASE)).toEqual({ runId: "dog_0", rel: "x.json" });
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/%2e%2e/%2e%2e/x.json"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/a%2F..%2Fx.json"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/.hidden/files/x.json"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/a%20b/files/x.json"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/a%2Fb/files/x.json"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/a//b.json"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/files/%E0%A4%A"), BASE)).toBeNull();
  });

  it("ignores_other_paths", () => {
    expect(resolveFileRequest(u("/Pleatwright/"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/assets/index.js"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/Pleatwright/runs/dog_0/events"), BASE)).toBeNull();
    expect(resolveFileRequest(u("/runs/dog_0/files/tree.json"), BASE)).toBeNull(); // outside base
    expect(resolveFileRequest(u("/Pleatwright/gallery/gallery-dog/tree.json"), BASE)).toBeNull();
  });
});

describe("respond", () => {
  const blob = (s: string) => new Blob([s]);
  const deps = (over: Partial<Parameters<typeof respond>[2]> = {}) => ({
    getFile: vi.fn(async () => null as Blob | null),
    fetch: vi.fn(async () => new Response("net")),
    ...over,
  });

  it("gallery_ids_route_to_static_files", async () => {
    const d = deps();
    const res = await respond(u("/Pleatwright/runs/gallery-dog/files/Dog 54/packing_cp.svg"), BASE, d);
    expect(await res!.text()).toBe("net");
    expect(d.getFile).not.toHaveBeenCalled();
    const target = d.fetch.mock.calls[0][0] as URL;
    expect(target.href).toBe("https://example.github.io/Pleatwright/gallery/gallery-dog/Dog%2054/packing_cp.svg");
  });

  it("serves_store_files_with_content_type", async () => {
    const cases: Array<[string, string]> = [
      ["a.svg", "image/svg+xml"], ["a.png", "image/png"], ["a.json", "application/json"],
      ["a.jsonl", "application/x-ndjson"], ["a.fold", "application/json"], ["a.zip", "application/zip"],
      ["a.glb", "model/gltf-binary"], ["a.bin", "application/octet-stream"], ["noext", "application/octet-stream"],
    ];
    for (const [name, type] of cases) {
      const d = deps({ getFile: vi.fn(async () => blob("body")) });
      const res = (await respond(u(`/Pleatwright/runs/dog_0/files/${name}`), BASE, d))!;
      expect(d.getFile).toHaveBeenCalledWith("dog_0", name);
      expect(res.status).toBe(200);
      expect(res.headers.get("Content-Type")).toBe(type);
      expect(res.headers.get("X-Content-Type-Options")).toBe("nosniff");
      expect(res.headers.get("Content-Security-Policy")).toBe(name.endsWith(".svg") ? "sandbox" : null);
      expect(await res.text()).toBe("body");
    }
  });

  it("answers_404_for_missing_and_503_for_unavailable_storage", async () => {
    const missing = (await respond(u("/Pleatwright/runs/dog_0/files/x.json"), BASE, deps()))!;
    expect(missing.status).toBe(404);
    const broken = deps({ getFile: vi.fn(async () => { throw new StorageUnavailable("nope"); }) });
    expect((await respond(u("/Pleatwright/runs/dog_0/files/x.json"), BASE, broken))!.status).toBe(503);
    const other = deps({ getFile: vi.fn(async () => { throw new Error("boom"); }) });
    await expect(respond(u("/Pleatwright/runs/dog_0/files/x.json"), BASE, other)).rejects.toThrow("boom");
  });

  it("passes_other_urls_through", async () => {
    const d = deps();
    expect(await respond(u("/Pleatwright/assets/a.js"), BASE, d)).toBeNull();
    expect(d.fetch).not.toHaveBeenCalled();
    expect(d.getFile).not.toHaveBeenCalled();
  });
});

describe("withWorkerPolicy", () => {
  it("adds_the_worker_policy_and_keeps_the_script", async () => {
    const script = new Response("self.onmessage = null;", {
      status: 200, headers: { "Content-Type": "text/javascript", "Cache-Control": "max-age=600" } });
    const res = withWorkerPolicy(script);
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("text/javascript");
    expect(res.headers.get("Cache-Control")).toBe("max-age=600");
    expect(res.headers.get("Content-Security-Policy")).toBe(WORKER_CSP);
    expect(await res.text()).toBe("self.onmessage = null;");
  });

  it("is_the_site_policy_for_what_a_worker_does", () => {
    const dirs = WORKER_CSP.split(/;\s*/);
    expect(dirs).toEqual(expect.arrayContaining(["default-src 'self'", "connect-src 'self'"]));
    expect(dirs.find((d) => d.startsWith("script-src"))).toBe("script-src 'self' 'wasm-unsafe-eval'");
    expect(WORKER_CSP.replace(/wasm-unsafe-eval/g, "")).not.toMatch(/unsafe-eval|https?:/);
  });
});

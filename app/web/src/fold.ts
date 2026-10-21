import * as THREE from "three";

export interface FoldFile {
  vertices_coords: number[][];
  faces_vertices: number[][];
  edges_vertices: number[][];
  edges_assignment: string[];
  edges_foldAngle: number[];
  file_frames: { vertices_coords: number[][]; frame_title?: string }[];
  "pleatwright:percents": number[];
}

export function triangulate(faces: number[][]): Uint32Array {
  const out: number[] = [];
  for (const f of faces) for (let i = 1; i + 1 < f.length; i++) out.push(f[0], f[i], f[i + 1]);
  return new Uint32Array(out);
}

export function framePositions(fold: FoldFile, i: number): Float32Array {
  const V = fold.file_frames[i].vertices_coords;
  const out = new Float32Array(V.length * 3);
  V.forEach((v, j) => { out[3 * j] = v[0]; out[3 * j + 1] = v[1]; out[3 * j + 2] = v[2] ?? 0; });
  return out;
}

/** Vertex positions at any fold percent: the two stored frames either side, blended linearly (clamped
 *  to the first and last frame). The frames are 5% apart, so playing them as-is steps visibly. */
export function posePositions(fold: FoldFile, percent: number): Float32Array {
  const ps = fold["pleatwright:percents"];
  const last = ps.length - 1;
  if (percent <= ps[0]) return framePositions(fold, 0);
  if (percent >= ps[last]) return framePositions(fold, last);
  let j = 1;
  while (ps[j] < percent) j++;
  const t = (percent - ps[j - 1]) / (ps[j] - ps[j - 1]);
  const A = framePositions(fold, j - 1), B = framePositions(fold, j);
  for (let k = 0; k < A.length; k++) A[k] += (B[k] - A[k]) * t;
  return A;
}

export function creaseSegments(fold: FoldFile, i: number, kind: "M" | "V"): Float32Array {
  return creaseSegmentsOf(fold, framePositions(fold, i), kind);
}

function creaseSegmentsOf(fold: FoldFile, P: Float32Array, kind: "M" | "V"): Float32Array {
  const out: number[] = [];
  fold.edges_vertices.forEach(([a, b], k) => {
    if (fold.edges_assignment[k] !== kind) return;
    out.push(P[3 * a], P[3 * a + 1], P[3 * a + 2], P[3 * b], P[3 * b + 1], P[3 * b + 2]);
  });
  return new Float32Array(out);
}

export function bounds(P: Float32Array): { center: [number, number, number]; radius: number } {
  const lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity];
  for (let i = 0; i < P.length; i += 3)
    for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], P[i + k]); hi[k] = Math.max(hi[k], P[i + k]); }
  const center = [0, 1, 2].map((k) => (lo[k] + hi[k]) / 2) as [number, number, number];
  const radius = Math.hypot(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2;
  return { center, radius };
}

/** The uniform scale and offset (applied as scale, then position) that put a pose's bounding sphere onto
 *  `end`, the folded model's. The flat sheet is several times larger than the folded model, so drawn
 *  as-is the start of the animation overflows a camera fitted to the end. */
export function fitOnto(
  end: { center: [number, number, number]; radius: number }, P: Float32Array,
): { scale: number; position: [number, number, number] } {
  const b = bounds(P);
  const scale = end.radius / Math.max(b.radius, 1e-9);
  const position = [0, 1, 2].map((k) => end.center[k] - scale * b.center[k]) as [number, number, number];
  return { scale, position };
}

/** Why a parsed JSON value cannot be played back as a Pleatwright model.fold, or null if it can. */
export function validateFold(j: unknown): string | null {
  const f = j as Partial<FoldFile> | null;
  if (!f || typeof f !== "object") return "not a FOLD object";
  for (const k of ["vertices_coords", "faces_vertices", "edges_vertices", "edges_assignment", "file_frames"] as const)
    if (!Array.isArray(f[k])) return `missing ${k}`;
  const frames = f.file_frames!;
  if (frames.length === 0) return "model.fold has no fold frames";
  const ps = f["pleatwright:percents"];
  if (!Array.isArray(ps)) return "missing pleatwright:percents";
  if (ps.length !== frames.length) return "pleatwright:percents does not match file_frames";
  const n = f.vertices_coords!.length;
  for (let i = 0; i < frames.length; i++)
    if (!Array.isArray(frames[i].vertices_coords) || frames[i].vertices_coords.length !== n)
      return `frame ${i} has the wrong vertex count`;
  return null;
}

/**
 * Default view direction (from the model's centre towards the camera) in the model's world frame.
 * Pleatwright's world is +Y up, profile in XY, Z lateral (mcp_harness/pleatwright/render.py:22-27;
 * `to_plot` maps (x, y, z) to plot (x, -z, y)). overview.png looks from plot elevation 28 deg,
 * azimuth -55 deg, which in world axes is (cos28 cos-55, sin28, sin55 cos28) ~ (0.506, 0.469, 0.723).
 */
export const VIEW_DIR: readonly [number, number, number] = (() => {
  const el = (28 * Math.PI) / 180, az = (-55 * Math.PI) / 180;
  const v: [number, number, number] = [Math.cos(el) * Math.cos(az), Math.sin(el), -Math.sin(az) * Math.cos(el)];
  const n = Math.hypot(...v);
  return [v[0] / n, v[1] / n, v[2] / n];
})();
export const VIEW_UP: readonly [number, number, number] = [0, 1, 0];
export const VFOV_DEG = 40;

/**
 * Camera placement that frames a bounding sphere along VIEW_DIR. `aspect` is width / height: in a
 * portrait viewer the horizontal fov is the narrower one, so the sphere is fitted to the smaller fov.
 */
export function viewPose(
  b: { center: [number, number, number]; radius: number },
  aspect = 1,
  vfovDeg = VFOV_DEG,
): { position: [number, number, number]; near: number; far: number } {
  const r = Math.max(b.radius, 1e-6);
  const vfov = (vfovDeg * Math.PI) / 180;
  const hfov = 2 * Math.atan(Math.tan(vfov / 2) * Math.max(aspect, 1e-3));
  const d = (r / Math.sin(Math.min(vfov, hfov) / 2)) * 1.1;
  return {
    position: [b.center[0] + VIEW_DIR[0] * d, b.center[1] + VIEW_DIR[1] * d, b.center[2] + VIEW_DIR[2] * d],
    near: r / 100,
    far: r * 100,
  };
}

export interface PaperGeometries {
  sheet: THREE.BufferGeometry;
  m: THREE.BufferGeometry;
  v: THREE.BufferGeometry;
}

function setPositions(g: THREE.BufferGeometry, data: Float32Array): void {
  const a = g.getAttribute("position") as THREE.BufferAttribute;
  a.array.set(data);
  a.needsUpdate = true;
  // A stale sphere makes three cull the model; drop it so it is rebuilt from the new positions.
  g.boundingSphere = null;
  g.computeBoundingSphere();
}

/** The sheet and the two crease geometries, already holding `frame`'s positions. */
export function makeGeometries(fold: FoldFile, frame: number): PaperGeometries {
  const sheet = new THREE.BufferGeometry();
  sheet.setAttribute("position", new THREE.BufferAttribute(framePositions(fold, frame), 3));
  sheet.setIndex(new THREE.BufferAttribute(triangulate(fold.faces_vertices), 1));
  const crease = (kind: "M" | "V") => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(creaseSegments(fold, frame, kind), 3));
    return g;
  };
  const geos = { sheet, m: crease("M"), v: crease("V") };
  setFrame(geos, fold, frame);
  return geos;
}

/** Rewrite the geometries' positions in place for `frame` (crease counts are fixed per fold). */
export function setFrame(geos: PaperGeometries, fold: FoldFile, frame: number): void {
  setPose(geos, fold, framePositions(fold, frame));
}

/** Rewrite the geometries' positions in place from vertex positions `P` (e.g. a blended pose). */
export function setPose(geos: PaperGeometries, fold: FoldFile, P: Float32Array): void {
  setPositions(geos.sheet, P);
  geos.sheet.computeVertexNormals();
  setPositions(geos.m, creaseSegmentsOf(fold, P, "M"));
  setPositions(geos.v, creaseSegmentsOf(fold, P, "V"));
}

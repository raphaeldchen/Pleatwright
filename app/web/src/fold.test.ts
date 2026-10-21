import * as THREE from "three";
import { describe, expect, it } from "vitest";
import { bounds, creaseSegments, fitOnto, framePositions, posePositions, setPose, triangulate, makeGeometries, setFrame, validateFold, viewPose, VIEW_UP, type FoldFile } from "./fold";

const sq: FoldFile = {
  vertices_coords: [[0, 0], [1, 0], [1, 1], [0, 1]],
  faces_vertices: [[0, 1, 2], [0, 2, 3]],
  edges_vertices: [[0, 1], [1, 2], [2, 3], [3, 0], [0, 2]],
  edges_assignment: ["B", "B", "B", "B", "V"],
  edges_foldAngle: [0, 0, 0, 0, 180],
  file_frames: [
    { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]] },
    { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [1, 0, 0]] },
  ],
  "pleatwright:percents": [0, 100],
};

describe("fold.ts", () => {
  it("fan-triangulates faces", () => {
    expect(Array.from(triangulate([[0, 1, 2, 3]]))).toEqual([0, 1, 2, 0, 2, 3]);
  });
  it("flattens a frame to xyz", () => {
    expect(Array.from(framePositions(sq, 1)).slice(9)).toEqual([1, 0, 0]);
  });
  it("blends the two frames either side of a percent", () => {
    const at = (pct: number) => Array.from(posePositions(sq, pct)).slice(9);   // vertex 3 moves (0,1,0) -> (1,0,0)
    expect(at(0)).toEqual([0, 1, 0]);
    expect(at(100)).toEqual([1, 0, 0]);
    expect(at(50)).toEqual([0.5, 0.5, 0]);
    expect(at(25)).toEqual([0.25, 0.75, 0]);
    expect(at(-10)).toEqual([0, 1, 0]);                    // clamped to the ends
    expect(at(150)).toEqual([1, 0, 0]);
  });
  it("lands exactly on a stored frame at its percent", () => {
    const three: FoldFile = { ...sq, "pleatwright:percents": [0, 40, 100], file_frames: [
      sq.file_frames[0], { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 1]] }, sq.file_frames[1],
    ] };
    expect(Array.from(posePositions(three, 40))).toEqual(Array.from(framePositions(three, 1)));
    expect(Array.from(posePositions(three, 70)).slice(9)).toEqual([0.5, 0, 0.5]);
  });
  it("emits segments for one crease kind", () => {
    expect(Array.from(creaseSegments(sq, 0, "V"))).toEqual([0, 0, 0, 1, 1, 0]);
    expect(creaseSegments(sq, 0, "M").length).toBe(0);
  });
  it("fits any pose onto the folded model's bounding sphere", () => {
    // A 4x4 flat sheet that folds down into a 1-unit region far from the origin.
    const big: FoldFile = { ...sq, file_frames: [
      { vertices_coords: [[0, 0, 0], [4, 0, 0], [4, 4, 0], [0, 4, 0]] },
      { vertices_coords: [[10, 0, 0], [11, 0, 0], [11, 1, 0], [10, 1, 1]] },
    ] };
    const last = bounds(framePositions(big, 1));
    const folded = fitOnto(last, framePositions(big, 1));
    expect(folded.scale).toBeCloseTo(1);
    expect(folded.position.map((x) => x + 0)).toEqual([0, 0, 0]);
    for (const pct of [0, 30, 50, 100]) {
      const P0 = posePositions(big, pct);
      const { scale, position } = fitOnto(last, P0);
      const b = bounds(P0.map((v, j) => v * scale + position[j % 3]));
      expect(b.radius).toBeCloseTo(last.radius);
      b.center.forEach((c, k) => expect(c).toBeCloseTo(last.center[k]));
    }
    expect(fitOnto(last, framePositions(big, 0)).scale).toBeLessThan(1);   // the flat sheet shrinks to the model's size
  });
  it("bounds", () => {
    const b = bounds(framePositions(sq, 0));
    expect(b.center).toEqual([0.5, 0.5, 0]);
    expect(b.radius).toBeCloseTo(Math.SQRT2 / 2);
  });
  it("triangulates a triangle unchanged and a pentagon as a fan", () => {
    expect(Array.from(triangulate([[4, 5, 6]]))).toEqual([4, 5, 6]);
    expect(Array.from(triangulate([[0, 1, 2, 3, 4]]))).toEqual([0, 1, 2, 0, 2, 3, 0, 3, 4]);
  });
  it("setPose writes blended positions into the sheet and the crease lines", () => {
    const g = makeGeometries(sq, 0);
    const P = posePositions(sq, 50);
    setPose(g, sq, P);
    expect(Array.from(g.sheet.getAttribute("position").array)).toEqual(Array.from(P));
    expect(Array.from(g.v.getAttribute("position").array)).toEqual([0, 0, 0, 1, 1, 0]);
  });
  it("reads crease segments from a later frame, for the M kind", () => {
    const strip: FoldFile = {
      vertices_coords: [[0, 0], [1, 0], [2, 0], [2, 1], [1, 1], [0, 1]],
      faces_vertices: [[0, 1, 4, 5], [1, 2, 3, 4]],
      edges_vertices: [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [1, 4]],
      edges_assignment: ["B", "B", "B", "B", "B", "B", "M"],
      edges_foldAngle: [0, 0, 0, 0, 0, 0, -90],
      file_frames: [
        { vertices_coords: [[0, 0, 0], [1, 0, 0], [2, 0, 0], [2, 1, 0], [1, 1, 0], [0, 1, 0]] },
        { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 0, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]] },
      ],
      "pleatwright:percents": [0, 100],
    };
    expect(Array.from(creaseSegments(strip, 1, "M"))).toEqual([1, 0, 0, 1, 1, 0]);
    expect(creaseSegments(strip, 1, "V").length).toBe(0);
    expect(validateFold(strip)).toBeNull();
  });
  it("rejects folds that cannot be played back", () => {
    expect(validateFold(sq)).toBeNull();
    expect(validateFold(null)).not.toBeNull();
    expect(validateFold({ ...sq, "pleatwright:percents": undefined })).toMatch(/percents/);
    expect(validateFold({ ...sq, "pleatwright:percents": [0] })).toMatch(/percents/);
    expect(validateFold({ ...sq, file_frames: [] })).toMatch(/no fold frames/);
    expect(validateFold({ ...sq, file_frames: [sq.file_frames[0], { vertices_coords: [[0, 0, 0]] }] }))
      .toMatch(/frame 1/);
  });
  it("places the camera along the Y-up overview direction, outside the sphere", () => {
    const c: [number, number, number] = [1, 2, 3];
    const p = viewPose({ center: c, radius: 2 }, 1);
    const off = [p.position[0] - c[0], p.position[1] - c[1], p.position[2] - c[2]];
    const dist = Math.hypot(...off);
    expect(dist).toBeCloseTo((2 / Math.sin((40 * Math.PI) / 360)) * 1.1);
    // render.py's overview: from +x, slightly above (+y), from +z
    expect(off[0] / dist).toBeCloseTo(0.506, 2);
    expect(off[1] / dist).toBeCloseTo(0.469, 2);
    expect(off[2] / dist).toBeCloseTo(0.723, 2);
    expect(VIEW_UP).toEqual([0, 1, 0]);
    expect(p.near).toBeCloseTo(0.02);
    expect(p.far).toBeCloseTo(200);
  });
  it("backs off further in a portrait viewer and keeps the sphere inside the narrower fov", () => {
    const b = { center: [0, 0, 0] as [number, number, number], radius: 5 };
    const dist = (a: number) => Math.hypot(...viewPose(b, a).position);
    expect(dist(0.6)).toBeGreaterThan(dist(1.6));
    for (const aspect of [0.6, 1.6]) {
      const vfov = (40 * Math.PI) / 180;
      const hfov = 2 * Math.atan(Math.tan(vfov / 2) * aspect);
      expect(dist(aspect)).toBeGreaterThanOrEqual(5 / Math.sin(Math.min(vfov, hfov) / 2));
    }
  });
  it("builds geometries holding the requested frame, with a bounding sphere around it", () => {
    for (const frame of [0, 1]) {
      const g = makeGeometries(sq, frame);
      const want = framePositions(sq, frame);
      expect(Array.from(g.sheet.getAttribute("position").array)).toEqual(Array.from(want));
      const sphere = g.sheet.boundingSphere!;
      for (let i = 0; i < want.length; i += 3)
        expect(sphere.center.distanceTo(new THREE.Vector3(want[i], want[i + 1], want[i + 2])))
          .toBeLessThanOrEqual(sphere.radius + 1e-6);
      expect(Array.from(g.v.getAttribute("position").array)).toEqual(Array.from(creaseSegments(sq, frame, "V")));
    }
  });
  it("never keeps a stale bounding sphere when frames are far apart", () => {
    const far: FoldFile = {
      ...sq,
      file_frames: [
        { vertices_coords: [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]] },
        { vertices_coords: [[100, 100, 100], [101, 100, 100], [101, 101, 100], [100, 101, 100]] },
      ],
    };
    const g = makeGeometries(far, 0);
    const before = g.sheet.boundingSphere!.center.clone();
    setFrame(g, far, 1);
    const sphere = g.sheet.boundingSphere!;
    expect(sphere.center.distanceTo(before)).toBeGreaterThan(100);
    const want = framePositions(far, 1);
    for (let i = 0; i < want.length; i += 3)
      expect(sphere.center.distanceTo(new THREE.Vector3(want[i], want[i + 1], want[i + 2])))
        .toBeLessThanOrEqual(sphere.radius + 1e-6);
    // built straight from the far frame, the sphere is right from the first upload too
    expect(makeGeometries(far, 1).sheet.boundingSphere!.center.x).toBeCloseTo(100.5);
  });
});

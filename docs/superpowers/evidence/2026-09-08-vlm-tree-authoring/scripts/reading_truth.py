"""Whose grid readings were actually right?

The renderer's world->grid map is invertible, so a landmark's TRUE grid
coordinate can be computed from the mesh instead of argued about:

    u = 24 * (x - cx + span/2) / span
    v = 24 * (cy - y + span/2) / span

with span = max(ptp(x), ptp(y)) over the projected view, exactly as panel()
computes it. Landmarks are chosen to be argument-free extremes -- the nose is
the minimum-x vertex, the ground is the maximum-y one -- so no judgement enters
the ground truth.
"""
import numpy as np, trimesh, os, sys

GRID = 24


def side_grid(mesh_path):
    m = trimesh.load(mesh_path, force="mesh")
    m.vertices -= m.vertices.mean(axis=0)
    V = m.vertices
    x, y = V[:, 0], V[:, 1]           # side view (XY), as rendered
    span = max(np.ptp(x), np.ptp(y))
    cx, cy = (x.min() + x.max()) / 2, (y.min() + y.max()) / 2
    u = GRID * (x - cx + span / 2) / span
    v = GRID * (cy - y + span / 2) / span
    return V, u, v


def landmarks(mesh_path):
    V, u, v = side_grid(mesh_path)
    out = {}
    i = int(np.argmin(u)); out["extreme -x (nose/snout end)"] = (u[i], v[i])
    i = int(np.argmax(u)); out["extreme +x (tail/rear end)"] = (u[i], v[i])
    i = int(np.argmax(v)); out["lowest point (ground)"] = (u[i], v[i])
    i = int(np.argmin(v)); out["highest point (topline)"] = (u[i], v[i])
    return out


if __name__ == "__main__":
    for subj in ("dog", "horse", "bird"):
        p = os.path.expanduser(f"~/Downloads/photo_meshes/meshes/{subj}.glb")
        print(f"=== {subj} (side view, 24-unit grid) ===")
        for k, (a, b) in landmarks(p).items():
            print(f"   {k:32} ({a:5.1f}, {b:5.1f})")

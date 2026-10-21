"""Step 2: render 7 fixed views per capture, offline. ZERO browser cost.

Dependency-free SVG (numpy only). matplotlib is absent from the venv and that
venv is symlinked to the MAIN repo, so installing into it would mutate the
user's main environment and its CI-pinned deps.

Render spec is pinned in the prereg (section 4) and must not be tuned after
seeing output:
  - 7 fixed camera directions, identical for every capture
  - identical face colour rule / edge weight / projection / panel size
  - one shared scale from the UNION bounding box over ALL captures, so a model
    cannot be identified by its size on the page
  - fixed Lambert light, identical across conditions
  - no labels, no axes, no legend, no filename in the image

Blinding (prereg section 5): a seeded shuffle assigns opaque ids and randomises
left/right within each pair. The mapping goes to a SEPARATE file, not shown to
the judge until answers are recorded.
"""
import json
import os
import random
import sys

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))
SEED = 20260807

# (elev, azim) degrees. Spread so a uniaxial-ish object cannot hide edge-on
# in all of them.
VIEWS = [(90, -90), (0, -90), (0, 0), (25, -55), (25, 35), (-25, -125), (55, 140)]

PANEL = 230          # px per view
LIGHT = np.array([0.35, -0.55, 0.75])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
EDGE = "#242832"
LW = 0.5


def basis(elev_deg, azim_deg):
    e, a = np.radians(elev_deg), np.radians(azim_deg)
    cam = np.array([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)])
    f = -cam / np.linalg.norm(cam)                  # forward, toward origin
    up = np.array([0.0, 0.0, 1.0])
    if abs(np.dot(f, up)) > 0.999:                  # top/bottom view
        up = np.array([0.0, 1.0, 0.0])
    r = np.cross(f, up); r /= np.linalg.norm(r)
    u = np.cross(r, f)
    return r, u, f


def face_arrays(cap):
    V = np.asarray(cap["vertices_coords"], dtype=float)
    if V.shape[1] == 2:
        V = np.hstack([V, np.zeros((len(V), 1))])
    V = V - V.mean(axis=0)
    return V, [np.asarray(fv, dtype=int) for fv in cap["faces_vertices"]]


def newell(pts):
    n = np.zeros(3)
    m = len(pts)
    for i in range(m):
        a, b = pts[i], pts[(i + 1) % m]
        n[0] += (a[1] - b[1]) * (a[2] + b[2])
        n[1] += (a[2] - b[2]) * (a[0] + b[0])
        n[2] += (a[0] - b[0]) * (a[1] + b[1])
    ln = np.linalg.norm(n)
    return n / ln if ln > 1e-12 else np.array([0.0, 0.0, 1.0])


def shade(nrm):
    """Fixed two-sided Lambert -> grey. Identical rule for every capture."""
    c = abs(float(np.dot(nrm, LIGHT)))
    v = 0.42 + 0.50 * c
    q = int(max(0, min(255, round(v * 255))))
    return f"#{q:02x}{q:02x}{max(0,min(255,q+6)):02x}"


def panel_svg(cap, elev, azim, scale, ox, oy):
    V, faces = face_arrays(cap)
    r, u, f = basis(elev, azim)
    P2 = np.stack([V @ r, V @ u], axis=1)
    depth = V @ f
    order = sorted(range(len(faces)),
                   key=lambda i: -float(depth[faces[i]].mean()))
    cx, cy = ox + PANEL / 2.0, oy + PANEL / 2.0
    out = []
    for i in order:
        idx = faces[i]
        pts = V[idx]
        xy = P2[idx]
        sx = cx + xy[:, 0] * scale
        sy = cy - xy[:, 1] * scale
        d = " ".join(f"{x:.2f},{y:.2f}" for x, y in zip(sx, sy))
        out.append(f'<polygon points="{d}" fill="{shade(newell(pts))}" '
                   f'stroke="{EDGE}" stroke-width="{LW}" '
                   f'stroke-linejoin="round"/>')
    return "".join(out)


def union_scale(caps):
    m = 0.0
    for c in caps:
        V, _ = face_arrays(c)
        for elev, azim in VIEWS:
            r, u, _ = basis(elev, azim)
            m = max(m, float(np.abs(V @ r).max()), float(np.abs(V @ u).max()))
    return (PANEL / 2.0 * 0.88) / m


def render_pair(pid, left, right, scale, path):
    n = len(VIEWS)
    gut = 34
    W = gut + n * PANEL
    H = 2 * PANEL + 26
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" '
             f'height="{H}" viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
             f'<text x="8" y="{26 + PANEL/2}" font-family="sans-serif" '
             f'font-size="27" font-weight="700" fill="#111">A</text>',
             f'<text x="8" y="{26 + PANEL + PANEL/2}" font-family="sans-serif" '
             f'font-size="27" font-weight="700" fill="#111">B</text>',
             f'<text x="{gut}" y="18" font-family="sans-serif" font-size="14" '
             f'fill="#444">Pair {pid}</text>']
    for j, (elev, azim) in enumerate(VIEWS):
        parts.append(panel_svg(left, elev, azim, scale, gut + j * PANEL, 26))
    for j, (elev, azim) in enumerate(VIEWS):
        parts.append(panel_svg(right, elev, azim, scale,
                               gut + j * PANEL, 26 + PANEL))
    parts.append(f'<line x1="{gut}" y1="{26+PANEL}" x2="{W}" y2="{26+PANEL}" '
                 f'stroke="#d0d0d0" stroke-width="1"/>')
    parts.append("</svg>")
    with open(path, "w") as fh:
        fh.write("\n".join(parts))


def main():
    with open(os.path.join(OUT, "captures.json")) as fh:
        payload = json.load(fh)
    caps = [c for c in payload["captures"] if c["ok"]]
    base = [c for c in caps if c["condition"] == "BASE"]
    shaped = [c for c in caps if c["condition"] == "SHAPED"]
    print(f"BASE ok={len(base)}  SHAPED ok={len(shaped)}")
    if len(base) < 2 or len(shaped) < 3:
        print("INSUFFICIENT CAPTURES for the pinned pair set")
        return 1

    scale = union_scale(caps)
    print(f"shared scale {scale:.3f} px/unit")

    pairs = [(base[0], shaped[0], "BASE", "SHAPED#1"),
             (base[0], shaped[1], "BASE", "SHAPED#2"),
             (base[0], shaped[2], "BASE", "SHAPED#3"),
             (base[0], base[1],   "BASE", "BASE(null)")]

    rng = random.Random(SEED)
    rng.shuffle(pairs)
    key = {}
    for n, (ca, cb, na, nb) in enumerate(pairs, start=1):
        pid = f"P{n}"
        if rng.random() < 0.5:
            left, right, ln, rn = ca, cb, na, nb
        else:
            left, right, ln, rn = cb, ca, nb, na
        path = os.path.join(OUT, f"pair_{pid}.svg")
        render_pair(pid, left, right, scale, path)
        key[pid] = {"A": ln, "B": rn,
                    "A_disp": round(left["maxDisplacement"], 4),
                    "B_disp": round(right["maxDisplacement"], 4),
                    "is_null": "null" in (ln + rn)}
        print(f"{pid}: A={ln:<11} B={rn:<11} -> {os.path.basename(path)}")

    with open(os.path.join(OUT, "BLIND_KEY.json"), "w") as fh:
        json.dump({"seed": SEED, "key": key}, fh, indent=2)
    print("\nwrote BLIND_KEY.json (withheld until answers are recorded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

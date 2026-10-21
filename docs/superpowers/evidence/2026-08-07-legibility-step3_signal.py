"""Post-hoc: is the SHAPED-vs-BASE geometric change even bigger than the
BASE-vs-BASE capture noise?

"No difference" from the judge has two very different causes:
  (a) the change is real and substantial, but not legible  -> legibility problem
  (b) the change is barely larger than solver drift        -> the op does little

These route differently, so measure it. Rigid-aligned (SO(3) ONLY -- memory
records that orthogonal_procrustes optimises over O(n) and a reflection would
flatter the fit) over the shared vertex prefix.
"""
import json
import os
import sys

import numpy as np

OUT = os.path.dirname(os.path.abspath(__file__))


def kabsch(P, Q):
    """Rotation+translation taking P onto Q, restricted to SO(3)."""
    pc, qc = P.mean(0), Q.mean(0)
    H = (P - pc).T @ (Q - qc)
    U, S, Vt = np.linalg.svd(H)
    d = np.sign(np.linalg.det(Vt.T @ U.T))
    D = np.diag([1.0, 1.0, d])                 # forbid reflection
    R = Vt.T @ D @ U.T
    return (R @ (P - pc).T).T + qc


def arr(c, key="vertices_coords"):
    V = np.asarray(c[key], dtype=float)
    return np.hstack([V, np.zeros((len(V), 1))]) if V.shape[1] == 2 else V


def compare(a, b, label):
    # NB: len() on the capture DICT is its key count, not its vertex count.
    n = min(len(a["vertices_coords"]), len(b["vertices_coords"]))
    P, Q = arr(a)[:n], arr(b)[:n]
    Pa = kabsch(P, Q)
    d = np.linalg.norm(Pa - Q, axis=1)
    # scale reference: the model's own extent
    ext = float(np.linalg.norm(Q.max(0) - Q.min(0)))
    print(f"{label:<26} n={n:3d}  rms={d.mean():.4f}  max={d.max():.4f}  "
          f"max/extent={d.max()/ext:.3%}")
    return d.mean(), d.max(), ext


def main():
    with open(os.path.join(OUT, "captures.json")) as fh:
        p = json.load(fh)
    caps = [c for c in p["captures"] if c["ok"]]
    base = [c for c in caps if c["condition"] == "BASE"]
    shaped = [c for c in caps if c["condition"] == "SHAPED"]

    print("shared-prefix vertex displacement after SO(3) best fit\n")
    print("--- NOISE FLOOR (same fold, two captures) ---")
    nb = compare(base[0], base[1], "BASE#1 vs BASE#2")

    print("\n--- SHAPED re-read spread (same fold, drift) ---")
    ss = []
    for i in range(len(shaped)):
        for j in range(i + 1, len(shaped)):
            ss.append(compare(shaped[i], shaped[j], f"SHAPED#{i+1} vs #{j+1}"))

    print("\n--- SIGNAL (the thing the judge was asked to see) ---")
    sig = []
    for i, s in enumerate(shaped):
        sig.append(compare(base[0], s, f"BASE vs SHAPED#{i+1}"))

    noise_max = max([nb[1]] + [x[1] for x in ss])
    sig_max = float(np.mean([x[1] for x in sig]))
    sig_rms = float(np.mean([x[0] for x in sig]))
    print(f"\nnoise ceiling (max over all same-condition pairs): {noise_max:.4f}")
    print(f"signal (mean over BASE-vs-SHAPED):  rms={sig_rms:.4f}  max={sig_max:.4f}")
    print(f"SIGNAL-TO-NOISE (max):  {sig_max/noise_max:.2f}x")

    # where does the change live? per-vertex, BASE vs SHAPED#1
    n = min(len(base[0]["vertices_coords"]), len(shaped[0]["vertices_coords"]))
    P, Q = arr(base[0])[:n], arr(shaped[0])[:n]
    d = np.linalg.norm(kabsch(P, Q) - Q, axis=1)
    top = np.argsort(-d)[:8]
    ext = float(np.linalg.norm(Q.max(0) - Q.min(0)))
    print(f"\nmost-moved vertices (BASE vs SHAPED#1), model extent {ext:.3f}:")
    for v in top:
        print(f"  v{v:<3d} moved {d[v]:.4f}  ({d[v]/ext:.2%} of extent)")
    print(f"  vertices moving >5% of extent: {int((d/ext > 0.05).sum())} of {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

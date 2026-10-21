"""Is an authored tree the right way up?

WHY THIS EXISTS
---------------
The grid render's vertical axis increases DOWNWARD (image convention: tick 0
at the top, 24 at the bottom), while the authoring prompt declares the output
frame as `+y up`. A model must therefore FLIP the sign between what it reads
and what it writes, and the prompt did not say so. Measured 2026-09-08 on the
finalized loop's 17 trees: 15 flipped correctly, and the dog and rabbit did
not -- their legs point at the ceiling.

That defect is invisible to every other metric in this project. Both inverted
trees score EXACT on leaf count, and `reading_fidelity` scores them fine too,
because the READINGS are right and only the derived directions are wrong. It
survived two full sweeps, an ablation and a replicate, and was caught by a
person looking at a picture.

HOW IT IS TESTED, WITHOUT ANY ANATOMY
-------------------------------------
No rule like "limbs descend" is used: it is false for a bat's wings, a
starfish's rays and an octopus's arms. Instead the tree is compared against
the mesh it claims to describe, BOTH WAYS UP:

    fit(tree)  vs  fit(tree with the vertical axis negated)

Node positions are derived from (parent, direction, length), projected into the
same grid coordinates as `reading_fidelity.silhouette`, centred and scaled to
the mesh's own extent so only ORIENTATION is being compared, then scored by
mean distance to the silhouette. If the flipped tree fits materially better,
the tree is upside down.

A radially symmetric subject flips to roughly itself, so the two fits come out
nearly equal and nothing is flagged -- which is the correct answer for a
starfish, and the reason a fit COMPARISON is used rather than a fit threshold.
"""
from __future__ import annotations

import math

import numpy as np

import reading_fidelity as RF

#: How much better the flipped fit must be, in grid units, before a tree is
#: called inverted. Set from the measured separation on the finalized loop's
#: 17 trees rather than chosen: the two known-bad trees clear it comfortably
#: and no good tree comes close.
FLIP_MARGIN = 0.75
#: Views whose vertical axis is the y axis. The top view (XZ) cannot see an
#: up/down flip at all and is deliberately excluded.
VERTICAL_VIEWS = ("side", "front")


def positions(nodes) -> dict:
    """Walk parent->child accumulating direction*length. `nodes` are
    (name, parent, direction, length) tuples with parents before children."""
    pos = {}
    for name, parent, d, ln in nodes:
        if parent is None or d is None:
            pos[name] = (0.0, 0.0, 0.0)
            continue
        px, py, pz = pos[parent]
        n = math.sqrt(d[0] ** 2 + d[1] ** 2 + d[2] ** 2) or 1.0
        pos[name] = (px + d[0] / n * ln, py + d[1] / n * ln, pz + d[2] / n * ln)
    return pos


def _mask_frame(mask):
    """Centroid and max extent of an occupancy mask, in grid units."""
    occ = RF._occupied_xy(mask)
    return occ.mean(axis=0), float(max(np.ptp(occ[:, 0]), np.ptp(occ[:, 1]))), occ


def _fit(pts, mask):
    """Mean distance from points to the silhouette, after centring and scaling
    the point cloud onto the mask so only orientation is compared."""
    centre, extent, occ = _mask_frame(mask)
    p = np.asarray(pts, dtype=float)
    span = float(max(np.ptp(p[:, 0]), np.ptp(p[:, 1]))) or 1.0
    p = (p - p.mean(axis=0)) * (extent / span) + centre
    d = np.sqrt(((p[:, None, :] - occ[None, :, :]) ** 2).sum(-1)).min(1)
    n = mask.shape[0]
    iu = np.clip((p[:, 0] * RF.CELLS_PER_UNIT).astype(int), 0, n - 1)
    iw = np.clip((p[:, 1] * RF.CELLS_PER_UNIT).astype(int), 0, n - 1)
    return float(np.where(mask[iw, iu], 0.0, d).mean())


def check_orientation(mesh, nodes, *, margin: float = FLIP_MARGIN) -> dict:
    """Compare the tree against the mesh both ways up.

    Returns {as_is, flipped, gain, inverted, views}. `gain` is how much better
    the flipped tree fits; positive and above `margin` means upside down.
    """
    pos = positions(nodes)
    names = [n[0] for n in nodes]
    out = {}
    a_tot, f_tot = [], []
    for view in VERTICAL_VIEWS:
        h, v, _ = RF.VIEWS[view]
        mask = RF.silhouette(mesh, view)
        P = np.array([[pos[n][h], pos[n][v]] for n in names], dtype=float)
        # image v grows downward, so a +y-up tree is negated to be drawn
        a = _fit(np.stack([P[:, 0], -P[:, 1]], axis=1), mask)
        f = _fit(np.stack([P[:, 0], P[:, 1]], axis=1), mask)
        out[view] = {"as_is": round(a, 4), "flipped": round(f, 4)}
        a_tot.append(a); f_tot.append(f)
    a, f = float(np.mean(a_tot)), float(np.mean(f_tot))
    return {"as_is": round(a, 4), "flipped": round(f, 4),
            "gain": round(a - f, 4), "inverted": (a - f) > margin,
            "views": out}

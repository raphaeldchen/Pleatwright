"""The folded model as a FOLD 1.1 file, with fold-slider frames.

`file_frames[i]` holds the 3-D vertex positions at fold percentage
`pleatwright:percents[i]`, computed by Pleatwright's own folder
(`fold.solve_fold`) and carried through the shaped world transform `W0`, so
the browser only plays frames back and there is one fold implementation.
Frame 0 is the flat sheet moved rigidly by `W0` (coplanar, congruent to the
CP, not necessarily at z = 0) so the camera does not jump while scrubbing.
"""
from __future__ import annotations

import json

import numpy as np

from . import fold as F

FRAMES = 21


def _world(X: np.ndarray, W0: np.ndarray) -> list:
    return (np.c_[X, np.ones(len(X))] @ W0.T)[:, :3].tolist()


def model_fold(cand: dict, frames: int = FRAMES) -> dict:
    m, W0 = cand["model"], cand["W0"]
    percents = [round(100 * i / (frames - 1), 6) for i in range(frames)]
    out = []
    for p in percents:
        X = F.vertex_positions(m, F.solve_fold(m, p / 100))
        out.append({"frame_title": f"{p:g}%", "frame_inherit": True, "frame_parent": 0,
                    "frame_classes": ["foldedForm"], "vertices_coords": _world(X, W0)})
    return {
        "file_spec": 1.1, "file_creator": "pleatwright",
        "file_classes": ["singleModel"], "frame_classes": ["creasePattern"],
        "frame_unit": "unit",
        "vertices_coords": np.asarray(m.vertices, float).tolist(),
        "faces_vertices": [list(map(int, f)) for f in m.faces],
        "edges_vertices": [[int(u), int(v)] for u, v in m.edges],
        "edges_assignment": list(m.assignment),
        "edges_foldAngle": [float(a) for a in m.fold_angle],
        "file_frames": out,
        "pleatwright:percents": percents,
    }


def write_model_fold(path: str, cand: dict, frames: int = FRAMES) -> dict:
    doc = model_fold(cand, frames)
    with open(path, "w") as f:
        json.dump(doc, f)
    return doc

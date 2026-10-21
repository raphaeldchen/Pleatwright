"""Hooks the app needs from the pipeline (spec 2026-10-07-pleatwright-app §4.3).
Artifact trees only (owner rule)."""
import json
import os

import numpy as np
import pytest

from pleatwright import export as EX
from pleatwright import fold as F
from pleatwright import pipeline as PL

FOUR = ["overview.png", "packing_cp.svg", "shaping_cp.svg", "solving_cp.svg"]
ORDER = ["packing_cp.svg", "solving_cp.svg", "shaping_cp.svg", "overview.png"]


@pytest.fixture(autouse=True, scope="module")
def _no_beside():
    """These tests pin the app's stage hooks, not packing: the beside searches (river
    routing, tests/test_river_routing.py) are switched off to save their
    seconds on every fold."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(PL, "BESIDE", False)
        yield


def test_on_stage_fires_per_stage_once_that_stages_file_is_on_disk(tmp_path):
    seen = []

    def on_stage(stage, info):
        names = [os.path.basename(f) for f in info["files"]]
        assert all(os.path.isfile(f) for f in info["files"])
        # the NEXT stage's file is not written yet: files appear stage by stage
        i = ORDER.index(names[0])
        folder = os.path.dirname(info["files"][0])
        assert not any(os.path.exists(os.path.join(folder, n)) for n in ORDER[i + 1:])
        if stage == "shaping":
            assert {"model", "W0", "polys"} <= set(info["candidate"])
        seen.append((stage, names))

    rec = PL.run("bird_1", str(tmp_path), certify_global=False, verbose=False,
                 on_stage=on_stage)
    assert seen == [("packing", ["packing_cp.svg"]), ("solving", ["solving_cp.svg"]),
                    ("shaping", ["shaping_cp.svg"]), ("output", ["overview.png"])]
    assert sorted(os.listdir(rec["folder"])) == FOUR


def test_on_stage_info_carries_the_numbers_the_chat_shows(tmp_path):
    got = {}
    PL.run("bird_1", str(tmp_path), certify_global=False, verbose=False,
           on_stage=lambda s, i: got.setdefault(s, i))
    assert got["packing"]["grid"] == 40 and got["packing"]["tried"] >= 1
    assert isinstance(got["packing"]["rung"], str)
    assert len(got["solving"]["flat_foldable"]) == 2
    assert len(got["shaping"]["flat_foldable"]) == 2
    assert got["output"]["folder"] == got["packing"]["folder"]


def test_an_on_stage_error_is_reported_as_that_stage(tmp_path):
    def boom(stage, info):
        if stage == "solving":
            raise RuntimeError("callback failed")
    with pytest.raises(PL.StageError) as e:
        PL.run("bird_1", str(tmp_path), certify_global=False, verbose=False, on_stage=boom)
    assert e.value.stage == "solving"


def _candidate(roll, tmp_path):
    got = {}
    PL.run(roll, str(tmp_path), certify_global=False, verbose=False,
           on_stage=lambda s, i: got.setdefault(s, i))
    return got["shaping"]["candidate"]


@pytest.fixture(scope="module")
def bird(tmp_path_factory):
    return _candidate("bird_1", tmp_path_factory.mktemp("bird"))


def test_full_frame_reproduces_the_polygons_overview_png_draws(bird):
    doc = EX.model_fold(bird)
    X = np.array(doc["file_frames"][-1]["vertices_coords"])
    m = bird["model"]
    worst = max(float(np.linalg.norm(X[f] - P, axis=1).max())
                for f, P in zip(m.faces, bird["polys"]))
    # frames average a vertex's images over its faces; the polygons do not.
    # closure_error is the max PER-AXIS spread of those images in the paper
    # frame, so after the rigid W0 the Euclidean gap is at most sqrt(3) * it.
    assert worst <= np.sqrt(3) * bird["closure"] + 1e-9


def test_zero_frame_is_the_sheet_moved_rigidly(bird):
    doc = EX.model_fold(bird)
    X0 = np.array(doc["file_frames"][0]["vertices_coords"])
    V = np.array(doc["vertices_coords"])
    Vz = np.c_[V, np.zeros(len(V))]
    # congruent: every pairwise distance on a sample of vertices is preserved
    idx = np.linspace(0, len(V) - 1, 40).astype(int)
    d_flat = np.linalg.norm(Vz[idx, None] - Vz[None, idx], axis=-1)
    d_frame = np.linalg.norm(X0[idx, None] - X0[None, idx], axis=-1)
    assert np.allclose(d_flat, d_frame, atol=1e-9)
    # coplanar: rank-2 after centring
    s = np.linalg.svd(X0 - X0.mean(axis=0), compute_uv=False)
    assert s[2] <= 1e-9 * s[0]


def test_fold_file_is_internally_consistent(bird, tmp_path):
    p = tmp_path / "model.fold"
    EX.write_model_fold(str(p), bird)
    doc = json.loads(p.read_text())
    nv = len(doc["vertices_coords"])
    assert doc["file_spec"] == 1.1 and len(doc["file_frames"]) == EX.FRAMES
    assert doc["pleatwright:percents"][0] == 0 and doc["pleatwright:percents"][-1] == 100
    assert len(doc["edges_vertices"]) == len(doc["edges_assignment"]) == len(doc["edges_foldAngle"])
    assert set(doc["edges_assignment"]) <= {"B", "M", "V"}
    assert all(0 <= i < nv for f in doc["faces_vertices"] for i in f)
    assert all(len(fr["vertices_coords"]) == nv for fr in doc["file_frames"])


def test_frames_follow_the_fold_solver_at_each_percent(bird):
    doc = EX.model_fold(bird, frames=3)
    m, W0 = bird["model"], bird["W0"]
    X = F.vertex_positions(m, F.solve_fold(m, 0.5))
    want = (np.c_[X, np.ones(len(X))] @ W0.T)[:, :3]
    assert np.allclose(np.array(doc["file_frames"][1]["vertices_coords"]), want, atol=1e-12)

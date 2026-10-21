"""Tests for flat_fold.py (folded-state-first slice 1).

Spec: docs/superpowers/specs/2026-07-03-flat-fold-engine-slice1-design.md
Fixture provenance: star-4/hshape/quad are compile goldens; dog.fold is
the 2026-06 six-leaf dog compile; bear-base.fold is the hull-frontier
display asset (accepted Kawasaki violations); star4-sim-100.json is the
2026-07-03 probe's converged 100% browser capture of star-4.
"""
import json
import os

import numpy as np
import pytest

from pleatwright.certify.flat_fold import CLOSURE_EPS, FlatFoldResult, _extract_faces, _signed_area, _validate, flat_fold

GOLDENS = os.path.join(os.path.dirname(__file__), "goldens")

# Drift tripwire, measured from THIS implementation in Task 2 Step 4
# (spanning-tree-dependent; see TestHullFrontierTier).
BEAR_BAD_EDGES = 15


def load_golden(name):
    with open(os.path.join(GOLDENS, name)) as fh:
        return json.load(fh)


def cp_vertices(fold):
    return np.asarray([v[:2] for v in fold["vertices_coords"]], dtype=float)


class TestExtractFaces:
    def test_star4_faces(self):
        fold = load_golden("star-4.fold")
        faces = _extract_faces(cp_vertices(fold),
                               [tuple(e) for e in fold["edges_vertices"]])
        assert len(faces) == 8
        assert all(len(f) == 3 for f in faces)

    def test_faces_are_ccw(self):
        fold = load_golden("star-4.fold")
        V = cp_vertices(fold)
        faces = _extract_faces(V, [tuple(e) for e in fold["edges_vertices"]])
        assert all(_signed_area(V[f]) > 0 for f in faces)

    def test_bear_faces_including_nonconvex_frame(self):
        # 45 interior faces; the hull-frontier frame region is a 12-gon.
        fold = load_golden("bear-base.fold")
        faces = _extract_faces(cp_vertices(fold),
                               [tuple(e) for e in fold["edges_vertices"]])
        assert len(faces) == 45
        assert max(len(f) for f in faces) == 12

    def test_every_edge_bounds_at_most_two_faces(self):
        fold = load_golden("dog.fold")
        V = cp_vertices(fold)
        faces = _extract_faces(V, [tuple(e) for e in fold["edges_vertices"]])
        assert len(faces) == 28
        count = {}
        for f in faces:
            for j in range(len(f)):
                k = tuple(sorted((f[j], f[(j + 1) % len(f)])))
                count[k] = count.get(k, 0) + 1
        assert max(count.values()) <= 2


class TestValidate:
    def test_missing_keys_raise(self):
        with pytest.raises(ValueError, match="vertices_coords"):
            _validate({"edges_vertices": [[0, 1]], "edges_assignment": ["B"]})
        with pytest.raises(ValueError, match="edges_vertices"):
            _validate({"vertices_coords": [[0, 0]], "edges_assignment": ["B"]})

    def test_empty_arrays_raise(self):
        with pytest.raises(ValueError):
            _validate({"vertices_coords": [], "edges_vertices": [],
                       "edges_assignment": []})

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError, match="length"):
            _validate({"vertices_coords": [[0, 0], [1, 0]],
                       "edges_vertices": [[0, 1]],
                       "edges_assignment": []})


CLEAN_RAW = ["star-4.fold", "hshape.fold", "quad.fold", "dog.fold"]


class TestCleanTier:
    @pytest.mark.parametrize("name", CLEAN_RAW)
    def test_raw_bases_close(self, name):
        res = flat_fold(load_golden(name))
        assert res.closure.max_error < 1e-6
        assert res.closure.bad_edges == ()

    @pytest.mark.parametrize("name", CLEAN_RAW)
    def test_folded_bbox_within_flat_bbox(self, name):
        fold = load_golden(name)
        V = cp_vertices(fold)
        res = flat_fold(fold)
        pts = np.vstack(res.folded_vertices)
        # eps widened from the brief's literal 1e-9: dog.fold's leg-flap
        # fold genuinely overhangs the flat bbox by ~0.0321 paper units
        # (folding near a sheet edge legitimately sends the flap past the
        # opposite boundary — real geometry, not float noise). Verified
        # independently against probe_folded_state.py, which reports the
        # identical bbox for dog raw with the same algorithm. star-4's
        # own float-noise overshoot is ~4e-9.
        eps = 0.04
        assert (pts.min(0) >= V.min(0) - eps).all()
        assert (pts.max(0) <= V.max(0) + eps).all()

    @pytest.mark.parametrize("name", CLEAN_RAW)
    def test_per_face_isometry(self, name):
        fold = load_golden(name)
        V = cp_vertices(fold)
        res = flat_fold(fold)
        for f, P in zip(res.faces, res.folded_vertices):
            for j in range(len(f)):
                flat_len = np.linalg.norm(V[f[j]] - V[f[(j + 1) % len(f)]])
                fold_len = np.linalg.norm(P[j] - P[(j + 1) % len(f)])
                assert abs(flat_len - fold_len) < 1e-9

    def test_deterministic(self):
        fold = load_golden("dog.fold")
        a, b = flat_fold(fold), flat_fold(fold)
        assert a.faces == b.faces
        for ta, tb in zip(a.transforms, b.transforms):
            assert np.array_equal(ta, tb)
        for pa, pb in zip(a.folded_vertices, b.folded_vertices):
            assert np.array_equal(pa, pb)

    def test_transforms_are_orthogonal(self):
        # every transform is a composition of reflections: orthogonal
        # linear part, det = +/-1
        res = flat_fold(load_golden("quad.fold"))
        for T in res.transforms:
            L = T[:2, :2]
            assert np.allclose(L @ L.T, np.eye(2), atol=1e-12)

    def test_results_compare_without_raising(self):
        # frozen dataclass with ndarray fields: eq=False so == is
        # identity, not an ambiguous-array ValueError (final review)
        fold = load_golden("star-4.fold")
        a, b = flat_fold(fold), flat_fold(fold)
        assert a == a
        assert (a == b) is False
        assert isinstance(hash(a), int)

    def test_shared_edges_field(self):
        # additive slice-2 field: every shared edge with its assignment
        res = flat_fold(load_golden("star-4.fold"))
        assert len(res.shared_edges) == 8
        for fa, fb, k, a in res.shared_edges:
            assert a in ("M", "V", "B", "F")
            assert k[0] < k[1]


class TestHullFrontierTier:
    def test_bear_reports_inconsistency_without_raising(self):
        # Drift-tripwire values: MEASURED from this implementation
        # (BFS spanning tree), sanity-bounded by the probe's findings
        # (probe measured 15 bad edges, max 1.199 with a different
        # tree; the error magnitude is tree-dependent, the EXISTENCE
        # of inconsistency is not).
        res = flat_fold(load_golden("bear-base.fold"))
        bad = res.closure.bad_edges
        assert len(bad) == BEAR_BAD_EDGES
        # measured 0.5393 with this implementation's BFS spanning tree;
        # widened ±0.2 per brief Step 4 (magnitude is tree-dependent).
        assert 0.3 <= res.closure.max_error <= 0.75
        # closure errors are reported, never raised
        assert isinstance(res, FlatFoldResult)


class TestErrorPaths:
    def test_flat_fold_validates(self):
        with pytest.raises(ValueError):
            flat_fold({"vertices_coords": [], "edges_vertices": [],
                       "edges_assignment": []})

    def test_degenerate_crease_raises(self):
        # two coincident vertices joined by an M edge inside a creased
        # square: zero-length crease is structurally unusable
        fold = {
            "vertices_coords": [[0, 0], [1, 0], [1, 1], [0, 1],
                                [0.5, 0.5], [0.5, 0.5]],
            "edges_vertices": [[0, 1], [1, 2], [2, 3], [3, 0],
                               [0, 4], [4, 5], [5, 2]],
            "edges_assignment": ["B", "B", "B", "B", "V", "M", "V"],
        }
        with pytest.raises(ValueError):
            flat_fold(fold)


def _kabsch(A, B):
    """Best rigid alignment A->B; reflection allowed (a flat fold has
    mirror ambiguity — the sim may settle on either enantiomer)."""
    ca, cb = A.mean(0), B.mean(0)
    U, _, Vt = np.linalg.svd((A - ca).T @ (B - cb))
    R = Vt.T @ U.T
    return lambda X: (X - ca) @ R.T + cb


class TestSimAgreement:
    def test_star4_analytic_matches_converged_sim_capture(self):
        fold = load_golden("star-4.fold")
        cap = load_golden("star4-sim-100.json")
        V = cp_vertices(fold)
        Vsim = np.asarray(cap["vertices_coords"], dtype=float)
        flat = np.asarray(cap["flat_coords"], dtype=float)
        assert len(Vsim) == len(V)  # sim nodes are 1:1 with CP vertices

        res = flat_fold(fold)
        # one analytic image per CP vertex (star-4 closes: per-face
        # images of the same vertex coincide)
        img = {}
        for f, P in zip(res.faces, res.folded_vertices):
            for v, p in zip(f, P):
                img.setdefault(v, []).append(p)
        for ps in img.values():
            assert np.ptp(np.asarray(ps), 0).max() < 1e-9
        pos = {v: np.mean(ps, axis=0) for v, ps in img.items()}

        # sim-node -> CP-vertex correspondence via the capture's flat
        # coords: the sim recenters and rescales the pattern into a
        # plane, so fit a similarity and match nearest
        plane = sorted(np.argsort(np.ptp(flat, 0))[-2:])
        f2 = flat[:, plane]
        scale = float((np.ptp(f2, 0) / np.ptp(V, 0)).mean())
        Vs = (V - V.mean(0)) * scale + f2.mean(0)
        idx = [int(np.linalg.norm(Vs - q, axis=1).argmin()) for q in f2]
        assert sorted(idx) == list(range(len(V)))  # bijective match

        # embed the analytic folded state in 3D (z=0), align, compare
        A = np.array([np.append((pos[idx[i]] - V.mean(0)) * scale, 0.0)
                      for i in range(len(Vsim))])
        fit = _kabsch(A, Vsim)
        residual = float(np.linalg.norm(fit(A) - Vsim, axis=1).max())
        assert residual / scale < 1e-3  # paper units

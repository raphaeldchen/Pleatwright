"""cp_audit: the Stage-2.0 acceptance instrument.

Pure-Python interior-soundness audit of a RAW hull FOLD: closure (flat_fold),
per-interior-vertex Maekawa |M-V|=2, Kawasaki residual, and (Stage 2.3) the
big-little-big M/V-ARRANGEMENT oracle. The interior-vertex definition is
PINNED here: a vertex is interior iff it has >=1 incident crease and NO
incident "B" (border) edge — hull-frontier vertices all touch B edges, so
anything this audit flags cannot be explained away as the benign frontier
(probe_spike_kawasaki's "strictly interior"; the paper-border-coordinate
variant in probe_degree.py would misclassify hull tips as interior).

The arrangement half is the SUFFICIENCY pin: parity + residual are necessary
conditions only, so before 2.3 the ladder could serve a big-little-big-broken
pack as "clean". Its oracle lives here (ONE home) and lint_verdict imports it.
"""
import json
import math

import pytest

from pleatwright.certify import cp_audit


# --------------------------------------------------------------------------- #
# Synthetic single-interior-vertex square: center -> 4 edge midpoints.        #
# Kawasaki: four 90 deg sectors (alternating sum 0). Maekawa: M=3,V=1.        #
# --------------------------------------------------------------------------- #
def _cross_fold(center=(0.5, 0.5), assigns=("M", "M", "M", "V")):
    V = [
        [0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0],      # corners 0-3
        [0.5, 0.0], [1.0, 0.5], [0.5, 1.0], [0.0, 0.5],      # midpoints 4-7
        [center[0], center[1]],                               # center 8
    ]
    edges = [
        # perimeter, split at midpoints (B)
        ([0, 4], "B"), ([4, 1], "B"), ([1, 5], "B"), ([5, 2], "B"),
        ([2, 6], "B"), ([6, 3], "B"), ([3, 7], "B"), ([7, 0], "B"),
        # creases center -> midpoints
        ([8, 4], assigns[0]), ([8, 5], assigns[1]),
        ([8, 6], assigns[2]), ([8, 7], assigns[3]),
    ]
    return {
        "vertices_coords": V,
        "edges_vertices": [e for e, _ in edges],
        "edges_assignment": [a for _, a in edges],
    }


def test_clean_cross_audits_clean():
    rep = cp_audit.audit_fold(_cross_fold())
    assert rep.interior_total == 1
    assert rep.maekawa_violations == ()
    assert rep.kawasaki_violations == ()
    assert rep.closure_max_error <= cp_audit.CLOSURE_EPS
    assert rep.closure_bad_edges == 0
    assert rep.clean


def test_maekawa_parity_violation_is_flagged():
    rep = cp_audit.audit_fold(_cross_fold(assigns=("M", "M", "V", "V")))
    assert len(rep.maekawa_violations) == 1
    va = rep.maekawa_violations[0]
    assert (va.m, va.v) == (2, 2)
    assert va.coords == (0.5, 0.5)
    assert not rep.clean


def test_kawasaki_and_closure_break_together_off_center():
    # moving the hub off BOTH axes skews the sectors: Kawasaki residual is
    # degrees-scale and the reflection cycle no longer closes. (Off one axis
    # only is NOT enough — opposite rays stay collinear and Kawasaki holds
    # by symmetry.)
    rep = cp_audit.audit_fold(_cross_fold(center=(0.6, 0.55)))
    assert len(rep.kawasaki_violations) == 1
    assert rep.kawasaki_violations[0].kawasaki_residual_deg > 1.0
    assert rep.closure_max_error > cp_audit.CLOSURE_EPS
    assert rep.closure_bad_edges >= 1
    assert not rep.clean


def test_interior_definition_is_no_incident_border_edge():
    # midpoints touch B edges -> boundary, whatever their coordinates; only
    # the hub is interior. This is the pin that keeps hull-frontier vertices
    # out of the audit.
    rep = cp_audit.audit_fold(_cross_fold())
    assert [va.vertex for va in rep.vertices] == [8]


def test_flat_creases_are_ignored():
    # an F (facet/flat) edge adds no fold constraint: same verdicts with one
    # spliced in (mirrors the linter's normalization contract).
    fold = _cross_fold()
    fold["edges_vertices"].append([8, 0])
    fold["edges_assignment"].append("F")
    rep = cp_audit.audit_fold(fold)
    assert rep.maekawa_violations == () and rep.kawasaki_violations == ()
    assert rep.vertices[0].degree == 4          # F edge not counted
    assert rep.closure_max_error <= cp_audit.CLOSURE_EPS


def test_kawasaki_threshold_is_deliberate():
    # The live hf_dog defect measured 0.049 deg; template-clean interiors
    # measure <= ~1e-6 deg. The default tolerance must separate them.
    assert 1e-5 < cp_audit.KAWASAKI_TOL_DEG < 0.049
    # residual just under the default tol is NOT flagged
    rep = cp_audit.audit_fold(_cross_fold(center=(0.5 + 1e-9, 0.5)))
    assert rep.kawasaki_violations == ()


def test_golden_star4_audits_clean():
    # star-4 is the baseline-PASS golden: hull == paper, closure ~1e-9.
    with open(cp_audit_golden("star-4.fold")) as f:
        rep = cp_audit.audit_fold(json.load(f))
    assert rep.clean
    assert rep.closure_max_error <= cp_audit.CLOSURE_EPS
    assert rep.maekawa_violations == () and rep.kawasaki_violations == ()


def cp_audit_golden(name):
    import os
    return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "goldens", name)


# --------------------------------------------------------------------------- #
# M/V ARRANGEMENT (big-little-big) — the sufficiency half (Stage 2.3).        #
# Fixture: one interior vertex, four creases at 0/30/130/280 deg, so the      #
# sectors are 30/100/150/80 (alternating sum 0 -> Kawasaki clean) and any     #
# 3-1 assignment is Maekawa clean. Only WHERE the lone V sits decides         #
# foldability: flanking the strict-minimum 30 deg sector with two M's is the  #
# live LITTLE_BIG_LITTLE shape the parity-only audit used to bless.          #
# --------------------------------------------------------------------------- #
_BLB_RAYS_DEG = (0.0, 30.0, 130.0, 280.0)


def _border_hit(deg, cx=0.5, cy=0.5):
    """Where a ray from the hub leaves the unit square (snapped to the axis)."""
    dx, dy = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    ts = [t for t in (((1.0 - cx) / dx if dx > 1e-12 else None),
                      (-cx / dx if dx < -1e-12 else None),
                      ((1.0 - cy) / dy if dy > 1e-12 else None),
                      (-cy / dy if dy < -1e-12 else None))
          if t is not None and t > 0]
    t = min(ts)
    x, y = cx + t * dx, cy + t * dy
    x = 1.0 if abs(x - 1.0) < 1e-9 else 0.0 if abs(x) < 1e-9 else x
    y = 1.0 if abs(y - 1.0) < 1e-9 else 0.0 if abs(y) < 1e-9 else y
    return [x, y]


def _blb_fold(assigns=("M", "M", "M", "V"), crease_order=(0, 1, 2, 3)):
    """Square, hub 0, creases to the four _BLB_RAYS_DEG border hits.

    `assigns` is indexed by ANGULAR position (0/30/130/280 deg);
    `crease_order` permutes the order the creases are LISTED in, which is the
    order cp_audit's incidence lists come out in — an angle-blind arrangement
    check reads a different ring for every permutation.
    """
    h = [_border_hit(d) for d in _BLB_RAYS_DEG]         # -> vertices 1..4
    V = [[0.5, 0.5]] + h + [[0, 0], [1, 0], [1, 1], [0, 1]]
    edges = [([5, 4], "B"), ([4, 6], "B"),              # bottom (280 deg hit)
             ([6, 1], "B"), ([1, 2], "B"), ([2, 7], "B"),   # right (0, 30)
             ([7, 3], "B"), ([3, 8], "B"),              # top (130)
             ([8, 5], "B")]                             # left
    edges += [([0, k + 1], assigns[k]) for k in crease_order]
    return {"vertices_coords": V,
            "edges_vertices": [e for e, _ in edges],
            "edges_assignment": [a for _, a in edges]}


def test_blb_fixture_is_maekawa_and_kawasaki_clean():
    # precondition: the necessary conditions CANNOT see this defect.
    rep = cp_audit.audit_fold(_blb_fold())
    assert rep.interior_total == 1
    assert rep.maekawa_violations == () and rep.kawasaki_violations == ()
    assert rep.closure_bad_edges == 0
    va = rep.vertices[0]
    assert va.maekawa_defect == 2
    assert va.kawasaki_residual_deg <= cp_audit.KAWASAKI_TOL_DEG


def test_arrangement_defect_at_a_maekawa_clean_vertex_is_not_clean():
    # THE 2.3 pin: parity + residual pass, the arrangement does not, so the
    # report must say so and `clean` must be False (pre-2.3 it was True).
    rep = cp_audit.audit_fold(_blb_fold())
    assert [va.vertex for va in rep.arrangement_violations] == [0]
    assert rep.vertices[0].arrangement_ok is False
    assert not rep.clean


def test_arrangement_clean_ring_with_the_same_angles_audits_clean():
    # move the lone V off the strict-minimum sector's flank: same geometry,
    # same parity, same residual — now it folds, so the audit is CLEAN.
    rep = cp_audit.audit_fold(_blb_fold(assigns=("M", "V", "M", "M")))
    assert rep.vertices[0].arrangement_ok is True
    assert rep.arrangement_violations == ()
    assert rep.clean


@pytest.mark.parametrize("order", [(0, 1, 2, 3), (2, 0, 3, 1), (3, 2, 1, 0)])
def test_arrangement_sorts_rays_by_angle_not_incidence(order):
    """The load-bearing port detail: cp_audit's rays come out in EDGE-LIST
    (incidence) order, while the oracle needs the angular ring. Every listing
    permutation of the same pattern must give the same verdict."""
    assert cp_audit.audit_fold(_blb_fold(crease_order=order)
                               ).arrangement_violations
    assert cp_audit.audit_fold(_blb_fold(assigns=("M", "V", "M", "M"),
                                         crease_order=order)).clean


def test_arrangement_violations_never_double_count_parity_defects():
    """A crimp removes one M and one V, so a reduction can only terminate at
    |M-V|=2: the oracle is stuck at EVERY parity defect. Re-reporting those
    would inflate the counts, so arrangement_violations lists only vertices
    the necessary conditions already blessed."""
    rep = cp_audit.audit_fold(_cross_fold(assigns=("M", "M", "V", "V")))
    assert len(rep.maekawa_violations) == 1
    assert rep.vertices[0].arrangement_ok is False   # raw per-vertex fact...
    assert rep.arrangement_violations == ()          # ...not a second count
    assert not rep.clean


def test_non_finite_kawasaki_residual_reads_as_a_violation(monkeypatch):
    """Fail-closed pin (mirrors lint_verdict's NaN guard): a non-finite
    residual must not slip out of BOTH violation lists — kawasaki_violations
    tests `not (<=)` and arrangement_violations only claims vertices the
    necessary conditions positively blessed."""
    monkeypatch.setattr(cp_audit, "_kawasaki_residual_deg",
                        lambda rays: float("nan"))
    rep = cp_audit.audit_fold(_cross_fold())
    assert len(rep.kawasaki_violations) == 1
    assert rep.arrangement_violations == ()
    assert not rep.clean


def test_mv_arrangement_oracle_reduction():
    """The shared oracle itself (moved here from lint_verdict, which now
    imports it). Ring semantics: sectors[i] follows crease i."""
    ok = cp_audit.mv_arrangement_ok
    # strict-min sector flanked by SAME assignment: stuck (big-little-big)
    assert not ok([30, 100, 150, 80], ["M", "M", "M", "V"])
    # same ring with the V moved so the min sector's flanks differ: reduces
    assert ok([30, 100, 150, 80], ["M", "V", "M", "M"])
    # the classic all-90 bird-base vertex (equal-angle ties)
    assert ok([90, 90, 90, 90], ["M", "M", "M", "V"])
    # degree-2 terminal: equal sectors + equal assignment only
    assert ok([180, 180], ["M", "M"])
    assert not ok([180, 180], ["M", "V"])
    # degenerate rings read NOT ok (conservative, false-FAILED-only)
    assert not ok([360], ["M"])
    assert not ok([180, 180], ["M"])


def test_arrangement_tie_rule_stays_conservative():
    """PINNED fail direction: a stuck greedy reduction reads NOT ok. Never
    relax this to 'unknown -> ok' — false-FAILED is the allowed error."""
    assert cp_audit.mv_arrangement_ok([30, 100, 150, 80],
                                      ["M", "M", "M", "V"]) is False
    assert cp_audit.arrangement_ok_at_vertex(
        [280.0, 0.0, 130.0, 30.0], ["V", "M", "M", "M"]) is False


def test_arrangement_ok_at_vertex_ignores_assignment_on_a_ray_tie():
    """Regression for a real crash: sorted(zip(rays, assignments)) falls
    through to comparing `assignments` whenever two rays tie exactly, and a
    non-string assignment (malformed FOLD: JSON null) then raises TypeError.
    The fix sorts on the ray alone; this must return a plain bool, never
    raise, whatever the tied assignment values are."""
    assert cp_audit.arrangement_ok_at_vertex(
        [0.0, 0.0, 120.0, 240.0], [None, "M", "M", "V"]) in (True, False)
    assert cp_audit.arrangement_ok_at_vertex(
        [0.0, 0.0], [None, "M"]) in (True, False)


def test_audit_fold_does_not_crash_on_coincident_ray_with_null_assignment():
    """Full-pipeline repro of the same defect (not just the unit call): a hub
    with a genuine ray tie (crease to vertex 5 at 0 deg, plus a second crease
    along the SAME ray to a nearer point) where the nearer crease's assignment
    is malformed (None). Pre-fix this raised TypeError out of audit_fold's
    vertex loop -- uncaught by the CLI, so the documented exit code contract
    (0/1/2) never applied. Post-fix it audits normally: no exception, and the
    malformed vertex and the coincident-ray hub both surface as violations."""
    fold = _cross_fold()
    fold["vertices_coords"].append([0.8, 0.5])     # same ray as hub->vertex 5
    fold["edges_vertices"].append([8, 9])
    fold["edges_assignment"].append(None)
    rep = cp_audit.audit_fold(fold)                # must not raise
    assert not rep.clean


def test_cli_does_not_crash_on_coincident_ray_with_null_assignment(tmp_path,
                                                                    capsys):
    fold = _cross_fold()
    fold["vertices_coords"].append([0.8, 0.5])
    fold["edges_vertices"].append([8, 9])
    fold["edges_assignment"].append(None)
    p = tmp_path / "coincident_null.fold"
    p.write_text(json.dumps(fold))
    assert cp_audit.main([str(p)]) == 1            # violations, not a crash


def test_golden_hf_crane_carries_a_live_arrangement_only_defect():
    """The LIVE case, not a synthetic one: the crane base the TreeMaker-era 2.2
    ladder served (rung 2 of its +/-10% ladder) has a degree-6 interior
    vertex that passes BOTH necessary conditions and still cannot fold. Before
    2.3 this fold's only reported defects were its two Kawasaki vertices, so
    the audit under-counted a served base. Oriedita reports the same vertex as
    LITTLE_BIG_LITTLE (cross-checked live; the JVM half was pinned in
    test_lint_classification, now on archive/treemaker-box-pleat)."""
    with open(cp_audit_golden("hf-crane-ladder-blb.fold")) as f:
        rep = cp_audit.audit_fold(json.load(f))
    assert [va.vertex for va in rep.arrangement_violations] == [37]
    va = next(v for v in rep.vertices if v.vertex == 37)
    assert (va.degree, va.m, va.v) == (6, 2, 4)
    assert va.maekawa_defect == 2                          # parity PASSES
    assert va.kawasaki_residual_deg <= cp_audit.KAWASAKI_TOL_DEG   # and so
    assert va.arrangement_ok is False                      # does the residual
    # the pre-2.3 counts are unchanged around it -- this is a NEW defect, not
    # a re-labelling of the two Kawasaki vertices the audit already knew.
    assert len(rep.kawasaki_violations) == 2
    assert 37 not in {v.vertex for v in rep.kawasaki_violations}
    assert rep.maekawa_violations == ()


def test_loosened_kawasaki_tolerance_does_not_erase_the_arrangement_defect():
    """Regression: audit_fold used to forward --kawasaki-tol-deg straight
    into the arrangement oracle's eps. At tol >= 0.1 deg that bleeds enough
    slack into the greedy reduction's tie test to bless the crane v37
    big-little-big defect (residual 5.7e-07 deg) -- a false CLEAN reachable
    with a CLI flag an operator would plausibly pass to quiet Kawasaki noise.
    The arrangement eps is now clamped to the DEFAULT tolerance, so a loosened
    CLI tolerance only widens the necessary-condition checks, never the
    sufficiency oracle: v37 must still show up as an arrangement violation
    even though loosening the tolerance also reclassifies v5/v29 out of
    kawasaki_violations and into arrangement_violations alongside it (the
    defect doesn't vanish, it moves category -- both lists stay non-empty)."""
    with open(cp_audit_golden("hf-crane-ladder-blb.fold")) as f:
        fold = json.load(f)
    rep = cp_audit.audit_fold(fold, kawasaki_tol_deg=1.0)
    assert 37 in {va.vertex for va in rep.arrangement_violations}
    assert not rep.clean


def test_cli_loosened_kawasaki_tolerance_still_exits_nonzero(capsys):
    rc = cp_audit.main([cp_audit_golden("hf-crane-ladder-blb.fold"),
                        "--kawasaki-tol-deg", "1.0"])
    assert rc == 1
    out = capsys.readouterr().out
    # Load-bearing, not just an exit code: the v37 big-little-big defect must
    # still be NAMED in the human output at this loosened tolerance, or the
    # nonzero exit could be coming from an unrelated defect while the
    # arrangement bug this test guards against silently erases v37 again.
    assert any("arrangement" in ln.lower() and "37" in ln
               for ln in out.splitlines())


def test_file_frames_nesting_is_accepted():
    inner = _cross_fold()
    rep = cp_audit.audit_fold({"file_spec": 1.1, "file_frames": [inner]})
    assert rep.interior_total == 1 and rep.clean


def test_structurally_unusable_fold_raises_value_error():
    with pytest.raises(ValueError):
        cp_audit.audit_fold({"vertices_coords": []})


# ------------------------------ CLI ---------------------------------------- #

def test_cli_human_output_and_exit_codes(tmp_path, capsys):
    clean = tmp_path / "clean.fold"
    clean.write_text(json.dumps(_cross_fold()))
    assert cp_audit.main([str(clean)]) == 0
    out = capsys.readouterr().out
    assert "interior vertices: 1" in out
    assert "CLEAN" in out

    dirty = tmp_path / "dirty.fold"
    dirty.write_text(json.dumps(_cross_fold(center=(0.6, 0.55))))
    assert cp_audit.main([str(dirty)]) == 1
    out = capsys.readouterr().out
    assert "Kawasaki" in out and "closure" in out


def test_cli_arrangement_only_defect_exits_nonzero(tmp_path, capsys):
    """Deliberate exit-code churn: a fold whose ONLY defect is the M/V
    arrangement used to exit 0 (clean). The human line must explain that the
    necessary conditions passed, or the verdict reads self-contradictory."""
    p = tmp_path / "blb.fold"
    p.write_text(json.dumps(_blb_fold()))
    assert cp_audit.main([str(p)]) == 1
    out = capsys.readouterr().out
    assert "Arrangement v0" in out
    assert "both PASS" in out and "big-little-big" in out
    assert "0 Maekawa + 0 Kawasaki + 1 M/V-arrangement" in out

    ok = tmp_path / "blb_ok.fold"
    ok.write_text(json.dumps(_blb_fold(assigns=("M", "V", "M", "M"))))
    assert cp_audit.main([str(ok)]) == 0
    assert "CLEAN" in capsys.readouterr().out


def test_cli_json_reports_arrangement(tmp_path, capsys):
    p = tmp_path / "blb.fold"
    p.write_text(json.dumps(_blb_fold()))
    assert cp_audit.main([str(p), "--json"]) == 1
    d = json.loads(capsys.readouterr().out)
    assert d["maekawa_violations"] == [] and d["kawasaki_violations"] == []
    assert [v["vertex"] for v in d["arrangement_violations"]] == [0]
    assert d["arrangement_violations"][0]["arrangement_ok"] is False
    assert d["clean"] is False


def test_cli_json_output_is_machine_readable(tmp_path, capsys):
    p = tmp_path / "x.fold"
    p.write_text(json.dumps(_cross_fold(center=(0.6, 0.55))))
    assert cp_audit.main([str(p), "--json"]) == 1
    d = json.loads(capsys.readouterr().out)
    assert d["interior_total"] == 1
    assert d["closure_bad_edges"] >= 1
    assert len(d["kawasaki_violations"]) == 1
    assert d["kawasaki_violations"][0]["vertex"] == 8
    assert d["clean"] is False


def test_cli_missing_file_is_a_clean_error(tmp_path, capsys):
    assert cp_audit.main([str(tmp_path / "nope.fold")]) == 2
    assert "ERROR" in capsys.readouterr().err

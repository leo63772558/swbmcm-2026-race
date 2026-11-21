from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from shutil import copyfile

import problem_b_geometry as g
import b_revision_geometry as rg
from b_revision_corner_routes import main as compare_nominal_corners

REVIEW_DIR = Path(__file__).resolve().parent.parent / "10_比赛工作区" / "submission" / "b_revision_20261121"


def test_direct_obstacle_free_route_is_exact_euclidean():
    """Unobstructed route equals exact Euclidean distance with 2 endpoints."""
    a, b = (5.0, 5.0), (15.0, 12.0)
    assert rg.road_clear(a, b)
    dist_val, pts = rg.route(a, b)
    assert len(pts) == 2
    assert math.isclose(dist_val, math.hypot(10.0, 7.0), rel_tol=1e-12)


def test_detour_route_maintains_continuous_rounded_clearance():
    """Detours around buildings maintain >= 1.5 m continuous segment clearance on every leg."""
    b = g.BUILDINGS[2]  # (x0, x1, y0, y1, h)
    x0, x1, y0, y1, _ = b
    start = (x0 - 4.0, 0.5 * (y0 + y1))
    goal = (x1 + 4.0, 0.5 * (y0 + y1))
    assert not rg.road_clear(start, goal)
    dist_val, pts = rg.route(start, goal)
    assert math.isfinite(dist_val) and dist_val > math.dist(start, goal)
    assert len(pts) >= 3
    for u, v in zip(pts, pts[1:]):
        assert g.in_field(u) and g.in_field(v)
        for bld in g.BUILDINGS:
            assert rg.segment_rect_distance(u, v, bld) >= g.RADIUS - 1e-7


def test_2925_route_audit_matches_rounded_vs_aabb():
    """Verified 2,925-route audit confirms 100 shortened and 5 restored routes with positive margin."""
    p2 = json.loads((REVIEW_DIR / "results" / "priority_2.json").read_text(encoding="utf-8"))
    ra = p2["routing"]
    assert ra["compared_routes"] == 2925
    assert ra["shorter_paths"] == 100
    assert ra["restored_endpoints"] == 5
    assert math.isclose(ra["maximum_saving_m"], 0.03193, abs_tol=1e-4)

    audit = json.loads((REVIEW_DIR / "results" / "HARDCORE_AUDIT_REPORT.json").read_text(encoding="utf-8"))
    assert audit["audit_1_field_inset"]["passed"] is True
    assert audit["audit_2_minkowski_clearance"]["passed"] is True
    assert audit["audit_2_minkowski_clearance"]["audited_routes_count"] == 2925
    assert audit["audit_2_minkowski_clearance"]["audited_min_route_margin_m"] > 0.0


def test_nominal_v3_detour_has_a_feasible_exact_corner_arc(tmp_path):
    results = REVIEW_DIR / "results"
    for name in ("P1_geometry.json", "P2_precision.csv", "P2_precision_routes.json", "P2_main_plans.json"):
        copyfile(results / name, tmp_path / name)
    row, = compare_nominal_corners(tmp_path)
    assert (row["vehicle"], row["alert"], row["building"], row["corner"]) == (3, "T2", "B3", "northwest")
    assert 90 < row["tangent_entry_deg"] < row["tangent_exit_deg"] < 180
    assert math.isclose(row["graph_length_m"], row["graph_in_m"] + row["graph_out_m"])
    assert math.isclose(
        row["tangent_arc_length_m"],
        row["tangent_in_m"] + row["arc_m"] + row["tangent_out_m"],
    )
    assert math.isclose(row["absolute_gap_m"], 0.1546841379, abs_tol=1e-9)
    assert math.isclose(row["relative_gap_pct"], 0.8047467656, abs_tol=1e-9)
    with (results / "P2_corner_arc_comparison.csv").open(encoding="utf-8", newline="") as stream:
        assert list(csv.DictReader(stream)) == [{key: str(value) for key, value in row.items()}]

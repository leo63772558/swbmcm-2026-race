from __future__ import annotations

import json
import math
from pathlib import Path

import problem_b_geometry as g
import b_revision_geometry as rg

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

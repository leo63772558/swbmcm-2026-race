# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Implementation scaffolding, numerical verification, and automated test engineering
# - Date: 2026-11-20 to 2026-11-21
# - Team Verification: Mathematical models and outputs verified by Team#SWBMCM2613050.
from __future__ import annotations

import math

import problem_b_geometry as g
import b_revision_geometry as rg


def test_field_inset_boundaries():
    """Vehicle disk radius 1.5 m enforces exact [1.5, 98.5]^2 center domain."""
    assert g.WIDTH == 100.0 and g.DEPTH == 100.0 and g.RADIUS == 1.5
    assert g.in_field((1.5, 1.5))
    assert g.in_field((98.5, 98.5))
    assert g.in_field((50.0, 50.0))
    assert not g.in_field((1.499, 50.0))
    assert not g.in_field((98.501, 50.0))
    assert not g.in_field((50.0, 1.499))
    assert not g.in_field((50.0, 98.501))


def test_minkowski_rounded_corner_vs_aabb():
    """Exact rounded Minkowski buffer allows points in the quarter-circle fillet corner excluded by AABB."""
    # BUILDINGS layout: (x0, x1, y0, y1, height)
    b = g.BUILDINGS[0]
    x0, x1, y0, y1, _ = b
    offset = 1.51 / math.sqrt(2.0)  # ~1.0677 m < 1.5 m -> blocked by AABB, clear by rounded disk!
    corner_pt = (x0 - offset, y0 - offset)
    d_exact = rg.rect_distance(corner_pt, b)
    assert math.isclose(d_exact, 1.51, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(rg.clearance(corner_pt, corner_pt), 0.01, abs_tol=1e-9)
    assert g.vehicle_fits(corner_pt)

    # Strictly inside the rounded fillet (distance 1.49 m) must be blocked
    offset_in = 1.49 / math.sqrt(2.0)
    inside_pt = (x0 - offset_in, y0 - offset_in)
    assert rg.rect_distance(inside_pt, b) < g.RADIUS
    assert not g.vehicle_fits(inside_pt)


def test_closed_disk_tangency_allowed():
    """Exact tangency at distance == 1.5 m from a building wall is permitted."""
    b = g.BUILDINGS[0]
    x0, x1, y0, y1, _ = b
    tangent_pt = (x0 - g.RADIUS, 0.5 * (y0 + y1))
    assert math.isclose(rg.rect_distance(tangent_pt, b), g.RADIUS, abs_tol=1e-12)
    assert g.vehicle_fits(tangent_pt)
    assert not g.vehicle_fits((x0 - g.RADIUS + 1e-4, 0.5 * (y0 + y1)))


def test_all_five_vehicles_and_buildings_valid():
    """All 5 initial vehicle centers lie inside [1.5, 98.5]^2 with clearance >= 1.5 m."""
    assert len(g.BUILDINGS) == 5
    assert len(g.VEHICLES) == 5
    for vid, pos in enumerate(g.VEHICLES, start=1):
        assert g.in_field(pos), f"V{vid} outside inset field"
        assert rg.clearance(pos, pos) >= -1e-9, f"V{vid} violates Minkowski clearance"


def test_continuous_segment_minkowski_clearance_and_grazing():
    """Continuous segment distance & road_clear enforce r >= 1.5 m along the entire segment."""
    b = g.BUILDINGS[0]
    x0, x1, y0, y1, _ = b
    # Segment cutting right across a corner inside the 1.5 m fillet must fail
    a_bad = (x0 - 1.5, y0 + 2.0)
    b_bad = (x0 + 2.0, y0 - 1.5)
    assert rg.segment_rect_distance(a_bad, b_bad, b) < g.RADIUS
    assert not rg.road_clear(a_bad, b_bad)

    # Segment running parallel at exact 1.5 m tangent clearance must pass
    a_ok = (x0 - g.RADIUS, y0)
    b_ok = (x0 - g.RADIUS, y1)
    assert math.isclose(rg.segment_rect_distance(a_ok, b_ok, b), g.RADIUS, abs_tol=1e-12)
    assert rg.road_clear(a_ok, b_ok)

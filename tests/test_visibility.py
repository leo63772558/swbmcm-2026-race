# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Implementation scaffolding, numerical verification, and automated test engineering
# - Date: 2026-11-20 to 2026-11-21
# - Team Verification: Mathematical models and outputs verified by Team#SWBMCM2613050.
from __future__ import annotations

import csv
import math
from pathlib import Path

import problem_b_geometry as g
import b_revision_geometry as rg

REVIEW_DIR = Path(__file__).resolve().parent.parent / "10_比赛工作区" / "submission" / "b_revision_20261121"


def test_elevation_bounds_and_min_radius():
    """Minimum horizontal range obeys r_min = (H - h_c) / tan(80 deg)."""
    t1 = g.TARGETS["T1"]
    t2 = g.TARGETS["T2"]
    assert math.isclose(g.minimum_radius(t1), (45.0 - 2.0) / math.tan(math.radians(80.0)), rel_tol=1e-12)
    assert math.isclose(g.minimum_radius(t1), 7.582060198229744, abs_tol=1e-6)
    assert math.isclose(g.minimum_radius(t2), (35.0 - 2.0) / math.tan(math.radians(80.0)), rel_tol=1e-12)
    assert math.isclose(g.minimum_radius(t2), 5.818790384687944, abs_tol=1e-6)


def test_closed_prism_tangency_blocks_visibility():
    """Ray grazing a closed building roof/wall edge is classified as occluded."""
    b = g.BUILDINGS[0]
    x0, x1, y0, y1, h = b
    box3d = ((x0, x1), (y0, y1), (0.0, h))
    # Ray strictly grazing the top edge at y = y0, z = h
    assert g.segment_hits_box((x0 - 5.0, y0, h), (x1 + 5.0, y0, h), box3d)
    # Ray passing strictly above the roof (z = h + 0.5) is clear
    assert not g.segment_hits_box((x0 - 5.0, y0, h + 0.5), (x1 + 5.0, y0, h + 0.5), box3d)


def test_p1_optimal_arc_and_endpoints_feasible():
    """Problem 1 optimal inner arc spans [236.896047, 520.747873] deg with feasible closed endpoints."""
    t1 = g.TARGETS["T1"]
    r_min = g.minimum_radius(t1)
    arcs = rg.feasible_arcs(t1, r_min)
    assert len(arcs) == 1
    a0, a1, inc0, inc1 = arcs[0]
    assert inc0 is True and inc1 is True
    deg0, deg1 = math.degrees(a0), math.degrees(a1)
    assert math.isclose(deg0, 236.896047, abs_tol=1e-4)
    assert math.isclose(deg1, 520.747873, abs_tol=1e-4)
    arc_len = (a1 - a0) * r_min
    assert math.isclose(arc_len, 37.562656, abs_tol=1e-4)

    # Both endpoints must satisfy closed-disk tangency and clear LOS
    for ang in (a0, a1):
        pt = rg.point_on_circle(t1, r_min, ang)
        assert g.in_field(pt)
        assert rg.clearance(pt, pt) >= -1e-7
        assert g.visible(pt, t1)


def test_p1_pitch_sensitivity_derivative():
    """Lowering beta_max from 80 deg to 79 deg drops peak quality Q_max by 9.2876%."""
    q80 = math.tan(math.radians(80.0)) / (45.0 - 2.0)
    q79 = math.tan(math.radians(79.0)) / (45.0 - 2.0)
    drop_pct = (1.0 - q79 / q80) * 100.0
    assert math.isclose(drop_pct, 9.2876, abs_tol=1e-3)
    with (REVIEW_DIR / "results" / "P1_station.csv").open("r", encoding="utf-8") as fh:
        rows = {r["tie"]: r for r in csv.DictReader(fh)}
    assert math.isclose(float(rows["ready"]["ready_s"]), 5.064533, abs_tol=1e-5)
    assert math.isclose(float(rows["arrival"]["arrival_s"]), 1.224247, abs_tol=1e-5)

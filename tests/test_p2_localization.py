# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Implementation scaffolding, numerical verification, and automated test engineering
# - Date: 2026-11-20 to 2026-11-21
# - Team Verification: Mathematical models and outputs verified by Team#SWBMCM2613050.
from __future__ import annotations

import math
import random

import problem_b_geometry as g
import b_revision_geometry as rg
import solve_problem_b as s


def test_analytical_lower_bound_proposition_1():
    """Proposition 1: RMS_local >= sqrt(2) * sigma_theta * r_min(T2) for all feasible pairs."""
    t2 = g.TARGETS["T2"]
    r_min = g.minimum_radius(t2)
    sigma_rad = math.radians(1.0)
    lb = math.sqrt(2.0) * sigma_rad * r_min
    assert math.isclose(lb, 0.143623358, abs_tol=1e-8)

    # Verify against 200 random non-collinear station pairs on or outside r_min(T2)
    rng = random.Random(20261121)
    for _ in range(200):
        r1 = r_min + rng.uniform(0.0, 25.0)
        r2 = r_min + rng.uniform(0.0, 25.0)
        a1 = rng.uniform(0.0, 2.0 * math.pi)
        gamma = rng.uniform(math.radians(5.0), math.radians(175.0))
        a2 = a1 + gamma
        p1 = (t2[0] + r1 * math.cos(a1), t2[1] + r1 * math.sin(a1))
        p2 = (t2[0] + r2 * math.cos(a2), t2[1] + r2 * math.sin(a2))
        rms, _ = s.accuracy(p1, p2, t2)
        assert rms >= lb - 1e-12


def test_optimal_v3_v5_attains_exact_lower_bound_within_30s():
    """V3 and V5 attain exact 0.143623 m RMS at gamma=90 deg with arrivals <= 30 s."""
    t2 = g.TARGETS["T2"]
    r_min = g.minimum_radius(t2)
    # Exact symmetric stations on T2's r_min circle (avoiding 6-decimal rounding below r_min)
    s1 = (t2[0] - r_min / math.sqrt(2.0), t2[1] - r_min / math.sqrt(2.0))
    s2 = (t2[0] - r_min / math.sqrt(2.0), t2[1] + r_min / math.sqrt(2.0))
    rms, crossing = s.accuracy(s1, s2, t2)
    baseline = math.dist(s1, s2)
    assert math.isclose(rms, 0.143623358, abs_tol=1e-6)
    assert math.isclose(crossing, 90.0, abs_tol=1e-6)
    assert math.isclose(baseline, 8.229012, abs_tol=1e-4)

    # Check both stations feasible and reachable within 30 s under rounded clearance
    for pt in (s1, s2):
        assert g.in_field(pt)
        assert rg.clearance(pt, pt) >= -1e-6
        assert g.visible(pt, t2)

    t_v3 = rg.route(g.VEHICLES[2], s1)[0] / g.SPEED
    t_v5 = rg.route(g.VEHICLES[4], s2)[0] / g.SPEED
    assert t_v3 <= 30.0 and t_v5 <= 30.0
    assert math.isclose(t_v3, 6.459, abs_tol=5e-3)
    assert math.isclose(t_v5, 15.365, abs_tol=5e-3)


def test_finite_difference_jacobian_and_collinear_degeneracy():
    """Independent central finite differences match analytical RMS <1e-9; near-collinear diverges."""
    t2 = g.TARGETS["T2"]
    r_min = g.minimum_radius(t2)
    s1 = (t2[0] - r_min / math.sqrt(2.0), t2[1] - r_min / math.sqrt(2.0))
    s2 = (t2[0] - r_min / math.sqrt(2.0), t2[1] + r_min / math.sqrt(2.0))
    rms_ana, _ = s.accuracy(s1, s2, t2)

    eps = 1e-5
    def bearings(tx, ty):
        return (math.atan2(ty - s1[1], tx - s1[0]), math.atan2(ty - s2[1], tx - s2[0]))

    bxp = bearings(t2[0] + eps, t2[1])
    bxm = bearings(t2[0] - eps, t2[1])
    byp = bearings(t2[0], t2[1] + eps)
    bym = bearings(t2[0], t2[1] - eps)
    j11 = (bxp[0] - bxm[0]) / (2 * eps)
    j12 = (byp[0] - bym[0]) / (2 * eps)
    j21 = (bxp[1] - bxm[1]) / (2 * eps)
    j22 = (byp[1] - bym[1]) / (2 * eps)
    det = j11 * j22 - j12 * j21
    frob2 = j11 * j11 + j12 * j12 + j21 * j21 + j22 * j22
    rms_fd = math.radians(1.0) * math.sqrt(frob2) / abs(det)
    assert abs(rms_fd - rms_ana) / rms_ana < 1e-9

    # Near-collinear crossing angle (gamma = 1 deg) blows up RMS by > 50x
    s_near = (t2[0] + r_min, t2[1])
    s_near2 = (t2[0] + r_min * math.cos(math.radians(1.0)), t2[1] + r_min * math.sin(math.radians(1.0)))
    rms_deg, _ = s.accuracy(s_near, s_near2, t2)
    assert rms_deg > 50.0 * rms_ana

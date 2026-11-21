# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Implementation scaffolding, numerical verification, and automated test engineering
# - Date: 2026-11-20 to 2026-11-21
# - Team Verification: Mathematical models and outputs verified by Team#SWBMCM2613050.
from __future__ import annotations

import csv
import math
from pathlib import Path

import b_revision_probability as rp

REVIEW_DIR = Path(__file__).resolve().parent.parent / "10_比赛工作区" / "submission" / "b_revision_20261121"


def test_coverage_strictly_decreasing_including_zero_boundary():
    """Theorem 1: P(sigma) is strictly decreasing on [0, inf), continuous at sigma=0."""
    p0 = rp.coverage(0.0)
    assert math.isclose(p0, math.erf(5.0 / (math.sqrt(2.0) * 1.0)), abs_tol=1e-6)
    assert p0 > 0.999999

    sigmas = [0.0, 0.05, 0.3, 0.8, 1.2, 1.63674517, 2.0, 3.5, 6.0, 12.0]
    probs = [rp.coverage(sig) for sig in sigmas]
    for a, b in zip(probs, probs[1:]):
        assert a > b, f"Monotonicity violated: {a} <= {b}"
    assert probs[-1] > 5.0 / 180.0


def test_unique_travel_threshold_and_80m_closed_form_simplex():
    """s_max = 66.837258 m, sigma* = 1.63674517 m; 80 m domain a>=0, b>=0, a+80b <= sigma*."""
    s_max = rp.find_crossing(96)
    sigma_star = rp.A + rp.B * s_max
    assert math.isclose(s_max, 66.8372584, abs_tol=1e-4)
    assert math.isclose(sigma_star, 1.63674517, abs_tol=1e-6)
    assert math.isclose(rp.coverage(sigma_star), 0.95, abs_tol=1e-7)

    # Boundary vertices of closed simplex {(a,b) >= 0 : a + 80 b <= sigma*}
    assert math.isclose(rp.coverage(sigma_star + 0.0 * 80.0), 0.95, abs_tol=1e-7)
    assert rp.coverage(sigma_star - 0.01) > 0.95
    assert rp.coverage(sigma_star + 0.01) < 0.95

    b_max = sigma_star / 80.0
    assert math.isclose(rp.coverage(0.0 + b_max * 80.0), 0.95, abs_tol=1e-7)
    assert rp.coverage(0.0 + (b_max - 1e-4) * 80.0) > 0.95
    assert rp.coverage(0.0 + (b_max + 1e-4) * 80.0) < 0.95


def test_bonferroni_wilson_mc_dual_closure():
    """3x2,000,000 MC probes strictly bracket 0.95 on opposite sides of s_max."""
    with (REVIEW_DIR / "results" / "P3_MC.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 3
    above = next(r for r in rows if r["assessment"] == "above")
    belows = [r for r in rows if r["assessment"] == "below"]
    assert len(belows) == 2
    assert float(above["simultaneous_95_lower"]) > 0.95
    for r in belows:
        assert float(r["simultaneous_95_upper"]) < 0.95

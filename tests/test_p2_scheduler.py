# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Implementation scaffolding, numerical verification, and automated test engineering
# - Date: 2026-11-20 to 2026-11-21
# - Team Verification: Mathematical models and outputs verified by Team#SWBMCM2613050.
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import problem_b_geometry as g
import solve_problem_b as s

REVIEW_DIR = Path(__file__).resolve().parent.parent / "10_比赛工作区" / "submission" / "b_revision_20261121"


def test_decoupled_pan_tilt_slew_formula():
    """Slew duration equals max(|pan|/w_pan, |tilt|/w_tilt) — independent axes, NOT sum."""
    assert g.PAN_SPEED == 30.0 and g.PITCH_SPEED == 30.0
    t1 = g.TARGETS["T1"]
    pt = (12.0, 92.0)
    yaw, pitch = g.angles(pt, t1)
    expected = max(abs(yaw) / g.PAN_SPEED, abs(pitch) / g.PITCH_SPEED)
    assert math.isclose(g.slew_time(pt, t1), expected, abs_tol=1e-12)


def test_shortlist_ranking_reversal_and_exact_1000_pair_bnb():
    """k=3 vs k=8 ranking reversal holds; full-space 1,000-pair / 4,200-order B&B certifies 0.000 s gap."""
    with (REVIEW_DIR / "results" / "P2_trials.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    lookup = {
        (r["routing"], int(r["k"]), int(r["beam_width"]), r["policy"]): float(r["latest_start_s"])
        for r in rows
    }
    k3_beam = lookup[("rounded", 3, 20, "beam")]
    k3_near = lookup[("rounded", 3, 20, "nearest")]
    k8_beam = lookup[("rounded", 8, 20, "beam")]
    k8_near = lookup[("rounded", 8, 20, "nearest")]

    assert math.isclose(k3_beam, 13.069183, abs_tol=1e-4)
    assert math.isclose(k3_near, 11.724422, abs_tol=1e-4)
    assert k3_beam > k3_near  # ranking reversal at k=3
    assert math.isclose(k8_beam, 11.034062, abs_tol=1e-5)
    assert math.isclose(k8_near, 11.724422, abs_tol=1e-4)
    assert k8_beam < k8_near  # resolved at k=8

    # Exact B&B audit covering all C(5,2)^3 = 1,000 legal vehicle pairings & 4,200 acyclic orders
    audit = json.loads((REVIEW_DIR / "results" / "HARDCORE_AUDIT_REPORT.json").read_text(encoding="utf-8"))
    bnb = audit["audit_4_p2_exact_bnb"]
    assert bnb["passed"] is True
    full = bnb["exact_full_discrete_pool_bnb"]
    assert full["legal_pairings_total"] == 1000
    assert full["acyclic_ordered_topologies_total"] == 4200
    assert sum(full["multiplicity_pattern_counts"].values()) == 1000
    assert "(3, 1, 1, 1, 0)" in full["multiplicity_pattern_counts"]
    assert "(2, 2, 1, 1, 0)" in full["multiplicity_pattern_counts"]
    assert "(3, 3, 0, 0, 0)" in full["multiplicity_pattern_counts"]
    assert abs(bnb["gap_vs_full_discrete_pool_s"]) < 1e-9
    assert math.isclose(full["exact_discrete_optimum_s"], 11.034062, abs_tol=1e-5)


def test_nominal_k8_schedule_satisfies_constraints():
    """Nominal k=8 schedule assigns 2 distinct vehicles & non-collinear stations to each alert."""
    plans = json.loads((REVIEW_DIR / "results" / "P2_main_plans.json").read_text(encoding="utf-8"))
    visits = plans["beam"]
    assert len(visits) == 6
    by_alert = {}
    by_vehicle = {}
    for v in visits:
        by_alert.setdefault(v["alert"], []).append(v)
        by_vehicle.setdefault(v["vehicle"], []).append(v)
    assert set(by_alert.keys()) == {"T1", "T2", "T3"}
    for alert, pair in by_alert.items():
        assert len(pair) == 2
        assert pair[0]["vehicle"] != pair[1]["vehicle"]
        assert math.isclose(pair[0]["start"], pair[1]["start"], abs_tol=1e-6)
        p1 = tuple(pair[0]["station"])
        p2 = tuple(pair[1]["station"])
        assert math.dist(p1, p2) > 1e-3
        _, gamma = s.accuracy(p1, p2, g.TARGETS[alert])
        assert 0.0 < gamma < 180.0
    for vid, vlist in by_vehicle.items():
        vlist.sort(key=lambda x: x["depart"])
        for a, b in zip(vlist, vlist[1:]):
            assert b["depart"] >= a["reset"] - 1e-6


def test_live_scheduler_and_exact_bnb_invocation():
    """Directly invoke live solver.solve_schedule(), validate_visits(), and exact B&B topological helpers."""
    import b_hardcore_audit as audit
    import b_revision_geometry as rg
    from unittest.mock import patch

    with patch.object(s, "road_clear", rg.road_clear), patch.object(s, "route", rg.route):
        init_state = [(pos, 0.0) for pos in g.VEHICLES]
        live_visits = s.solve_schedule(init_state, g.TARGETS, 60.0, beam_width=20, stations=8)
        assert len(live_visits) == 6
        s.validate_visits(live_visits, g.TARGETS)
        t_last = max(v.start for v in live_visits)
        assert math.isclose(t_last, 11.034062, abs_tol=1e-5)

        # Verify topological order enumeration helper for a sample single-reuse pairing
        sample_orders = audit._topological_orders_for_pairing(((2, 4), (0, 3), (1, 2)), ("T1", "T2", "T3"))
        assert len(sample_orders) == 2

        # Verify live unseeded B&B certification on k=8 shortlist matches 11.034062 s
        res_k8 = audit._exact_p2_bnb(shortlist_k=8, initial_ub=float("inf"))
        assert res_k8["legal_pairings_total"] == 1000
        assert res_k8["acyclic_ordered_topologies_total"] == 4200
        assert math.isclose(res_k8["exact_discrete_optimum_raw_s"], 11.034062, abs_tol=1e-5)

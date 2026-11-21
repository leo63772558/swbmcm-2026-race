from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from b_hardcore_audit import _p2_replay_witness
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


def test_unseeded_exact_audit_replays_feasible_station_witness():
    audit = json.loads((REVIEW_DIR / "results" / "HARDCORE_AUDIT_REPORT.json").read_text(encoding="utf-8"))
    bnb = audit["audit_4_p2_exact_bnb"]
    expected = bnb["beam_k8_incumbent_s"]
    for key, pool, inner_prunes in (
        ("unseeded_k8_bnb", 8, 56581),
        ("unseeded_full_discrete_pool_bnb", "FULL_DISCRETE_POOL", 4479089),
    ):
        run = bnb[key]
        assert run["initial_upper_bound_s"] is None
        assert run["shortlist_k"] == pool
        assert run["discrete_station_pool_size"] == 585
        assert run["legal_pairings_total"] == 1000
        assert run["acyclic_ordered_topologies_total"] == 4200
        assert run["pruned_layer0_topologies"] == 3693
        assert run["pruned_inner_branches"] == inner_prunes
        assert run["exact_discrete_optimum_s"] == expected
        assert run["witness_replay_passed"]
        assert _p2_replay_witness(run)


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


def test_faster_pan_benchmark_retains_exact_fixed_witness():
    with (REVIEW_DIR / "results" / "P2_pan_speed_benchmark.csv").open(encoding="utf-8", newline="") as file:
        rows = {row["method"]: row for row in csv.DictReader(file)}
    fixed = rows["fixed_nominal_plan"]
    greedy = rows["greedy_beam"]
    exact = rows["exact_full_pool"]
    assert all(float(row["pan_deg_s"]) == 36.0 and float(row["tilt_deg_s"]) == 30.0 for row in rows.values())
    assert {int(row["station_alert_candidates"]) for row in rows.values()} == {585}
    assert int(greedy["arrival_shortlist_k"]) == 8 and int(greedy["beam_width"]) == 20
    assert not exact["arrival_shortlist_k"]
    assert int(exact["vehicle_pairings_evaluated"]) == 1000
    assert int(exact["acyclic_orders_evaluated"]) == 4200
    assert float(exact["latest_start_s"]) == float(fixed["latest_start_s"]) == 10.707896
    assert float(greedy["latest_start_s"]) == 12.210374


def test_exact_crossing_floor_trades_latency_for_lower_worst_alert_rms():
    with (REVIEW_DIR / "results" / "P2_angle_constrained_tradeoff.csv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    by_method = {}
    for row in rows:
        by_method.setdefault(row["method"], []).append(row)
        first = tuple(float(row[f"{axis}_1_m"]) for axis in ("x", "y"))
        second = tuple(float(row[f"{axis}_2_m"]) for axis in ("x", "y"))
        rms, gamma = s.accuracy(first, second, g.TARGETS[row["alert"]])
        assert math.isclose(gamma, float(row["crossing_deg"]), abs_tol=1e-7)
        assert math.isclose(rms, float(row["horizontal_rms_m"]), abs_tol=1e-7)
    assert set(by_method) == {"archived_nominal_beam", "exact_unconstrained", "exact_angle_floor"}
    assert all({row["alert"] for row in group} == set(g.TARGETS) and len(group) == 3 for group in by_method.values())
    assert min(float(row["crossing_deg"]) for row in by_method["archived_nominal_beam"]) < 30.0
    unconstrained = by_method["exact_unconstrained"]
    constrained = by_method["exact_angle_floor"]
    for group in (unconstrained, constrained):
        assert {int(row["station_alert_candidates"]) for row in group} == {585}
        assert {int(row["vehicle_pairings_evaluated"]) for row in group} == {1000}
        assert {int(row["acyclic_orders_evaluated"]) for row in group} == {4200}
    assert {float(row["latest_start_s"]) for row in unconstrained} == {11.034062}
    assert {float(row["latest_start_s"]) for row in constrained} == {12.006612}
    assert all(float(row["crossing_deg"]) >= 30.0 for row in constrained)
    assert max(float(row["horizontal_rms_m"]) for row in constrained) < max(
        float(row["horizontal_rms_m"]) for row in unconstrained
    )

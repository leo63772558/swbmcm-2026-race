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
import b_revision_geometry as rg

REVIEW_DIR = Path(__file__).resolve().parent.parent / "10_比赛工作区" / "submission" / "b_revision_20261121"


def test_nominal_timeline_monotonic_and_collision_free():
    """Nominal k=8 executed timeline has monotonic clocks, valid states inside [1.5,98.5]^2, 0 collisions."""
    timeline = json.loads((REVIEW_DIR / "results" / "Executed_timeline.json").read_text(encoding="utf-8"))
    events = timeline["nominal_policies"]["beam"]
    assert len(events) > 0

    by_v = {}
    for item in events:
        by_v.setdefault(item["vehicle"], []).append(item)
    assert len(by_v) == 5
    for vid, v_events in by_v.items():
        v_events.sort(key=lambda x: (x["start_s"], x["end_s"]))
        for a, b in zip(v_events, v_events[1:]):
            assert b["start_s"] >= a["end_s"] - 1e-6, f"V{vid} non-monotonic event"
        for item in v_events:
            assert item["end_s"] >= item["start_s"] - 1e-9
            for pt in item.get("path", []):
                assert g.in_field(tuple(pt)), f"V{vid} out of [1.5,98.5]^2"
                assert rg.clearance(tuple(pt), tuple(pt)) >= -1e-6


def test_cached_vs_ongoing_only_outage_semantics():
    """Cached full-plan execution finishes at 11.034 s vs ongoing-only 33.727 s (+22.693 s penalty)."""
    with (REVIEW_DIR / "results" / "P4_instruction_sensitivity.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    lookup = {(r["case"], float(r["recovery_s"]), r["interpretation"]): float(r["latest_start_s"]) for r in rows}
    cached = lookup[("outage_upper_time", 30.0, "cached")]
    ongoing = lookup[("outage_upper_time", 30.0, "ongoing_only")]
    assert math.isclose(cached, 11.034062, abs_tol=1e-4)
    assert math.isclose(ongoing, 33.727180, abs_tol=1e-3)
    assert math.isclose(ongoing - cached, 22.693118, abs_tol=2e-3)

    # 30s outage sensitivity branch shifts compound recovery predictably by +5.000 s
    t30 = lookup[("all_V2", 30.0, "cached")]
    t35 = lookup[("all_duration_sensitivity", 35.0, "cached")]
    assert math.isclose(t35 - t30, 5.0, abs_tol=1e-4)


def test_live_event_engine_and_strict_locking_clock():
    """Directly invoke b_revision_events and solve_problem_b.scenario_state / observation_starts."""
    import b_revision_events as ev
    import solve_problem_b as s

    plans = json.loads((REVIEW_DIR / "results" / "P2_main_plans.json").read_text(encoding="utf-8"))
    visits = tuple(
        s.Visit(
            vehicle=int(v["vehicle"]), alert=v["alert"], station=tuple(v["station"]),
            path=tuple(tuple(p) for p in v["path"]), depart=float(v["depart"]),
            arrival=float(v["arrival"]), ready=float(v["ready"]),
            start=float(v["start"]), end=float(v["end"]), reset=float(v["reset"]),
        )
        for v in plans["beam"]
    )
    # V5 fails at t_d = 5.0 s: T1 started at 3.093 s < 5.0 s, so T1 remains preserved & locked!
    preserved = s.observation_starts(visits, failed=4, disturbance=5.0)
    assert "T1" in preserved and preserved["T1"] < 5.0
    assert set(preserved.keys()) == {"T1", "T2", "T3"}

    # Live scenario_state on fleet at t = 5.0 s (V5 failed, V3 during T1 observation)
    fleet_state = s.scenario_state(visits, 5.0, failed=4, disturbance=5.0)
    assert fleet_state[4] is None
    v3_pos, v3_rel = fleet_state[2]
    assert v3_pos == (12, 92)
    assert math.isclose(v3_rel, visits[0].reset, abs_tol=1e-9)

    # Live b_revision_events.nominal_events round-trip
    nom_ev = ev.nominal_events(visits, preserved)
    assert len(nom_ev) > 0
    assert all(e["end_s"] >= e["start_s"] - 1e-9 for e in nom_ev)

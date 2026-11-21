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

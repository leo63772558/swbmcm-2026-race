from __future__ import annotations

import csv
import json
import math
from pathlib import Path

REVIEW_DIR = Path(__file__).resolve().parent.parent / "10_比赛工作区" / "submission" / "b_revision_20261121"


def test_p4_deduplication_and_115_unique_expansion():
    """73 raw IDs deduplicate to 62 unique baseline + 53 expanded = 115 strictly unique cases."""
    summary = json.loads((REVIEW_DIR / "results" / "P4_extended_summary.json").read_text(encoding="utf-8"))
    assert summary["raw_archived_case_count"] == 73
    assert summary["duplicates_removed"] == 11
    assert summary["dedup_baseline_unique_cases"] == 62
    assert summary["expanded_new_cases"] == 53
    assert summary["total_unique_cases"] == 115

    # Verify strict uniqueness in CSV ledger
    with (REVIEW_DIR / "results" / "P4_dedup_expanded_cases.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 115
    case_ids = {r["case"] for r in rows}
    assert len(case_ids) == 115, "Duplicate scenario IDs found in deduplicated ledger!"
    assert sum(1 for r in rows if r["suite"] == "baseline_unique") == 62
    assert sum(1 for r in rows if r["suite"] in ("expanded_spatial", "expanded_hard")) == 53

    # Verify lexicographic scores and hysteresis 0-loss guarantee
    tot = summary["expanded_total_row"]
    assert tot["cases"] == 115
    assert tot["mean_replan_eta"] == 1.0
    assert tot["replan_wins"] == 110
    assert tot["keep_wins"] == 1
    assert tot["ties"] == 4
    assert tot["hyst_losses"] == 0


def test_v5_myopic_penalty_and_search_budget_stability():
    """V5 single-fault +1.893 s myopic penalty is invariant across k=2/3/5/8 search budgets."""
    with (REVIEW_DIR / "results" / "P4_budget_stability.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 4
    ks = [int(r["stations_k"]) for r in rows]
    assert ks == [2, 3, 5, 8]
    for r in rows:
        assert float(r["mean_replan_eta"]) == 1.0
        assert int(r["hyst_losses"]) == 0
        assert math.isclose(float(r["v5_replan_tlast_s"]), 12.927041, abs_tol=1e-4)
        assert math.isclose(float(r["v5_delta_vs_keep_s"]), 1.89298, abs_tol=1e-4)


def test_real_solver_sensitivity_weight_check_and_3d_pareto():
    """Real P1-P4 sensitivity (no proxy), 5 weight schemes, and 3D Pareto proving both k=5 & k=8 non-dominated."""
    sens = json.loads((REVIEW_DIR / "results" / "Global_sensitivity_summary.json").read_text(encoding="utf-8"))
    assert "Sobol" not in sens["method"]
    assert sens["weight_schemes_tested"] == 5
    assert sens["pareto_front_3d_count"] == 8

    # Check 5 weight schemes present with 6 ranked parameters each
    with (REVIEW_DIR / "results" / "Global_sensitivity_weight_check.csv").open("r", encoding="utf-8") as fh:
        wrows = list(csv.DictReader(fh))
    assert len(wrows) == 30
    assert len({r["scheme"] for r in wrows}) == 5

    # Check 3D Pareto proves BOTH beam k=5 and beam k=8 are strictly 3D non-dominated
    with (REVIEW_DIR / "results" / "Pareto_tradeoff_3d.csv").open("r", encoding="utf-8") as fh:
        prows = list(csv.DictReader(fh))
    assert len(prows) == 16
    front_3d = [r for r in prows if r["is_pareto_3d"] == "True"]
    assert len(front_3d) == 8
    k5 = next(r for r in prows if r["policy"] == "beam" and int(r["k"]) == 5 and int(r["beam_width"]) == 20)
    k8 = next(r for r in prows if r["policy"] == "beam" and int(r["k"]) == 8 and int(r["beam_width"]) == 20)
    assert k5["is_pareto_3d"] == "True"
    assert k8["is_pareto_3d"] == "True"
    assert float(k5["total_travel_m"]) < float(k8["total_travel_m"])
    assert float(k8["mean_quality_m_inv"]) > float(k5["mean_quality_m_inv"])

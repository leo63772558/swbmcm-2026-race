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


def test_live_hysteresis_sweep_and_case_deduplication():
    """Directly invoke b_revision_p4_extended helpers and verify positive-threshold hysteresis sweep."""
    import b_revision_p4_extended as p4ext

    # Verify live deduplication builder produces exact 62 baseline + 53 expanded = 115 unique cases
    dedup_base, expanded, dup_cnt = p4ext.build_dedup_and_expanded_specs()
    assert len(dedup_base) == 62
    assert len(expanded) == 53
    assert dup_cnt == 11
    all_sigs = {p4ext._case_signature(a, f, r) for _, _, a, f, r in (*dedup_base, *expanded)}
    assert len(all_sigs) == 115

    # Verify persisted positive-threshold hysteresis sweep across delta in {0, 0.25, 0.5, 1.0, 2.0} s
    sweep_path = REVIEW_DIR / "results" / "P4_hysteresis_sweep.csv"
    assert sweep_path.is_file(), "Missing P4_hysteresis_sweep.csv"
    with sweep_path.open("r", encoding="utf-8") as fh:
        srows = list(csv.DictReader(fh))
    assert [float(r["hyst_delta_s"]) for r in srows] == [0.0, 0.25, 0.5, 1.0, 2.0]
    for r in srows:
        assert float(r["mean_hyst_eta"]) == 1.0
        assert int(r["hyst_losses"]) == 0
        assert int(r["hyst_wins"]) == 110
        assert int(r["hyst_ties"]) == 5

    # Live single-case suite invocation testing both delta=0.0 and delta=1.0 on failure_V5
    nominal_visits = p4ext._load_nominal_visits(REVIEW_DIR / "results")
    v5_spec = [("baseline_unique", "failure_V5", None, 4, 5.0)]
    r0 = p4ext._run_suite(nominal_visits, v5_spec, stations=2, beam_width=3, hyst_delta=0.0)[0]
    r1 = p4ext._run_suite(nominal_visits, v5_spec, stations=2, beam_width=3, hyst_delta=1.0)[0]
    assert r0["winner"] == "keep" and r0["hyst_winner"] == "tie"
    assert r1["hyst_winner"] == "tie"
    assert math.isclose(r0["hyst_latest_s"], 11.034062, abs_tol=1e-5)
    assert math.isclose(r1["hyst_latest_s"], 11.034062, abs_tol=1e-5)

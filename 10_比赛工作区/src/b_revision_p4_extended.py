"""P4 scenario deduplication, multi-azimuth/range/shadow-edge expansion, and search-budget stability.

AI assistance: Antigravity (Gemini), 2026-11-21.
Does not alter frozen nominal schedules or archived P4_cases.csv; produces independent
deduplicated category statistics, expanded spatial stress results, and k=3/5/8 stability tables.
"""
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import ExitStack
from math import isclose
from pathlib import Path
from unittest.mock import patch

import b_revision_geometry as rounded
import problem_b_geometry as model
import solve_problem_b as solver
from b_revision_data import DEFAULT_OUTPUT, read_csv, read_json, window_score, write_csv, write_json
from check_b_p4_cross import crossed_cases


DISTURBANCE = model.number("p4", "disturbance", "occurrence_time")   # 5.0 s
HORIZON = model.number("p4", "evaluation", "window_end")            # 60.0 s
T4_ALT = model.number("p4", "new_alert", "altitude")                # 50.0 m


def _case_signature(new_alert, failed, recovery):
    t4_key = None if new_alert is None else tuple(round(float(c), 4) for c in new_alert)
    return (failed, round(float(recovery), 6), t4_key)


def _category_of(new_alert, failed, recovery):
    has_f = failed is not None
    has_n = new_alert is not None
    has_o = float(recovery) > DISTURBANCE + 1e-9
    if has_f and has_n and has_o:
        return "All Three Combined"
    if has_f and has_n:
        return "Failure + New Alert"
    if has_f and has_o:
        return "Failure + Comms Outage"
    if has_n and has_o:
        return "New Alert + Comms Outage"
    if has_f:
        return "Vehicle Failure Only"
    if has_n:
        return "New Alert Only"
    return "Comms Outage Only (cached)"


def _load_nominal_visits(results_dir):
    plans = read_json(results_dir / "P2_main_plans.json")
    return tuple(
        solver.Visit(
            vehicle=int(v["vehicle"]), alert=v["alert"], station=tuple(v["station"]),
            path=tuple(tuple(p) for p in v["path"]), depart=float(v["depart"]),
            arrival=float(v["arrival"]), ready=float(v["ready"]),
            start=float(v["start"]), end=float(v["end"]), reset=float(v["reset"]),
        )
        for v in plans["beam"]
    )


def build_dedup_and_expanded_specs():
    """Deduplicate the original 73 scenarios and build systematic spatial-coverage expansion."""
    # 1. Deduplicate original 73 scenarios (28 base + 45 crossed)
    raw_specs = [*solver.scenarios(), *crossed_cases()]
    seen = set()
    dedup_base = []
    duplicate_count = 0
    for name, alert, failed, rec in raw_specs:
        sig = _case_signature(alert, failed, rec)
        if sig in seen:
            duplicate_count += 1
            continue
        seen.add(sig)
        dedup_base.append(("baseline_unique", name, alert, failed, rec))

    # 2. Expanded multi-azimuth (0..315 deg step 45) x multi-range (30/40/50 m) + shadow-edge hard points
    expanded = []
    # Full 8-azimuth x 3-range sweep (24 new-alert-only spatial probes)
    for az in range(0, 360, 45):
        for rng in (30.0, 40.0, 50.0):
            pt = model.target(az, rng, T4_ALT)
            sig = _case_signature(pt, None, DISTURBANCE)
            if sig not in seen:
                seen.add(sig)
                expanded.append(("expanded_spatial", f"spatial_az{az:03d}_r{int(rng)}", pt, None, DISTURBANCE))

    # 4 building-shadow-edge / observable-boundary hard points (within [30,50] m from O=(50,50))
    hard_points = (
        ("shadow_B2_NE", model.target(38.0, 34.0, T4_ALT)),   # Adjacent to B2 (28 m roof)
        ("shadow_B5_SW", model.target(225.0, 30.0, T4_ALT)),  # Across tall B5 (32 m roof)
        ("shadow_B4_SE", model.target(315.0, 38.0, T4_ALT)),  # Adjacent to B4 (24 m roof)
        ("shadow_B3_NW", model.target(145.0, 42.0, T4_ALT)),  # Adjacent to B3 & field corner
    )
    # Cross hard points with worst-case vehicle faults (V3 reused, V2 bottleneck, V5 counterexample) & outage clocks
    for hp_name, pt in hard_points:
        # Pure new alert at hard point
        sig = _case_signature(pt, None, DISTURBANCE)
        if sig not in seen:
            seen.add(sig)
            expanded.append(("expanded_hard", f"hard_{hp_name}", pt, None, DISTURBANCE))
        # Hard point + comms outage (t_rec = 30 s)
        sig = _case_signature(pt, None, 30.0)
        if sig not in seen:
            seen.add(sig)
            expanded.append(("expanded_hard", f"hard_{hp_name}_out30", pt, None, 30.0))
        # Hard point + critical faults (V2=1, V3=2, V5=4) at active link (5 s) and upper outage (30 s)
        for failed_idx in (1, 2, 4):
            for rec in (DISTURBANCE, 30.0):
                sig = _case_signature(pt, failed_idx, rec)
                if sig not in seen:
                    seen.add(sig)
                    tag = "act" if rec == DISTURBANCE else "out30"
                    expanded.append((
                        "expanded_hard",
                        f"hard_{hp_name}_V{failed_idx+1}_{tag}",
                        pt, failed_idx, rec,
                    ))

    return dedup_base, expanded, duplicate_count


def _run_suite(nominal_visits, specs, stations=2, beam_width=3, hyst_delta=0.0):
    """Evaluate a list of (suite, name, alert, failed, rec) specs under Keep, Reschedule, and Hysteresis."""
    rows = []
    with ExitStack() as stack:
        stack.enter_context(patch.object(solver, "road_clear", rounded.road_clear))
        stack.enter_context(patch.object(solver, "route", rounded.route))
        stack.enter_context(patch.object(solver, "candidate_stations", rounded.stations))
        for suite, name, new_alert, failed, rec in specs:
            goals = dict(model.TARGETS)
            if new_alert is not None:
                goals["T4"] = new_alert
            preserved = solver.observation_starts(nominal_visits, failed, DISTURBANCE)
            locked = {a: t for a, t in preserved.items() if t < rec}
            pending = {a: g for a, g in goals.items() if a not in locked}
            state = solver.scenario_state(nominal_visits, rec, failed, DISTURBANCE)
            revised = solver.solve_schedule(state, pending, HORIZON, beam_width=beam_width, stations=stations)
            solver.validate_visits(revised, goals)
            revised_starts = locked | solver.observation_starts(revised, None, DISTURBANCE)

            k_cnt, k_eta, k_last = window_score(preserved, set(goals), 0.0, HORIZON, HORIZON)
            r_cnt, r_eta, r_last = window_score(revised_starts, set(goals), 0.0, HORIZON, HORIZON)

            # Hysteresis-gated Eq. (5) decision
            trigger = (r_eta > k_eta + 1e-12) or (
                abs(r_eta - k_eta) <= 1e-12 and (k_last - r_last) > hyst_delta + 1e-9
            )
            h_eta, h_last = (r_eta, r_last) if trigger else (k_eta, k_last)

            score_k = (k_cnt, -k_last)
            score_r = (r_cnt, -r_last)
            winner = "reschedule" if score_r > score_k else ("keep" if score_k > score_r else "tie")
            score_h = (round(h_eta * len(goals)), -h_last)
            hyst_winner = "hyst_replan" if score_h > score_k else ("keep" if score_k > score_h else "tie")

            rows.append({
                "suite": suite,
                "case": name,
                "category": _category_of(new_alert, failed, rec),
                "failed_vehicle": "" if failed is None else failed + 1,
                "recovery_s": rec,
                "outage_duration_s": round(rec - DISTURBANCE, 6),
                "alerts": len(goals),
                "keep_eta": round(k_eta, 6),
                "keep_latest_s": round(k_last, 6),
                "replan_eta": round(r_eta, 6),
                "replan_latest_s": round(r_last, 6),
                "hyst_eta": round(h_eta, 6),
                "hyst_latest_s": round(h_last, 6),
                "delta_replan_minus_keep_s": round(r_last - k_last, 6),
                "winner": winner,
                "hyst_winner": hyst_winner,
            })
    return rows


def _summarize_categories(rows):
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)
    order = (
        "Vehicle Failure Only",
        "New Alert Only",
        "Comms Outage Only (cached)",
        "Failure + New Alert",
        "Failure + Comms Outage",
        "New Alert + Comms Outage",
        "All Three Combined",
    )
    summary = []
    for cat in order:
        grp = by_cat.get(cat, [])
        if not grp:
            continue
        n = len(grp)
        summary.append({
            "category": cat,
            "cases": n,
            "mean_keep_eta": round(sum(r["keep_eta"] for r in grp) / n, 4),
            "mean_replan_eta": round(sum(r["replan_eta"] for r in grp) / n, 4),
            "mean_hyst_eta": round(sum(r["hyst_eta"] for r in grp) / n, 4),
            "mean_replan_tlast_s": round(sum(r["replan_latest_s"] for r in grp) / n, 3),
            "replan_wins": sum(1 for r in grp if r["winner"] == "reschedule"),
            "keep_wins": sum(1 for r in grp if r["winner"] == "keep"),
            "ties": sum(1 for r in grp if r["winner"] == "tie"),
            "hyst_losses": sum(1 for r in grp if r["hyst_winner"] == "keep"),
        })
    n_tot = len(rows)
    summary.append({
        "category": "Total Unique Suite",
        "cases": n_tot,
        "mean_keep_eta": round(sum(r["keep_eta"] for r in rows) / n_tot, 4),
        "mean_replan_eta": round(sum(r["replan_eta"] for r in rows) / n_tot, 4),
        "mean_hyst_eta": round(sum(r["hyst_eta"] for r in rows) / n_tot, 4),
        "mean_replan_tlast_s": round(sum(r["replan_latest_s"] for r in rows) / n_tot, 3),
        "replan_wins": sum(1 for r in rows if r["winner"] == "reschedule"),
        "keep_wins": sum(1 for r in rows if r["winner"] == "keep"),
        "ties": sum(1 for r in rows if r["winner"] == "tie"),
        "hyst_losses": sum(1 for r in rows if r["hyst_winner"] == "keep"),
    })
    return summary


def main(results_dir=None):
    results_dir = Path(results_dir) if results_dir else (DEFAULT_OUTPUT / "results")
    nominal_visits = _load_nominal_visits(results_dir)
    dedup_base, expanded, dup_count = build_dedup_and_expanded_specs()
    all_unique_specs = dedup_base + expanded

    # 1. Run full deduplicated + expanded unique suite at baseline P4 rescheduler settings (k=2, bw=3)
    full_rows = _run_suite(nominal_visits, all_unique_specs, stations=2, beam_width=3, hyst_delta=0.0)
    dedup_only_rows = [r for r in full_rows if r["suite"] == "baseline_unique"]
    cat_summary_all = _summarize_categories(full_rows)
    cat_summary_dedup = _summarize_categories(dedup_only_rows)

    # 2. Search-budget stability sweep on the deduplicated baseline suite (k=2/3/5/8)
    budget_rows = []
    for label, k_val, bw_val in (
        ("archived_k2_bw3", 2, 3),
        ("budget_k3_bw5", 3, 5),
        ("budget_k5_bw10", 5, 10),
        ("budget_k8_bw20", 8, 20),
    ):
        run_r = _run_suite(nominal_visits, dedup_base, stations=k_val, beam_width=bw_val, hyst_delta=0.0)
        v5_row = next(r for r in run_r if r["case"] == "failure_V5")
        n = len(run_r)
        budget_rows.append({
            "budget_label": label,
            "stations_k": k_val,
            "beam_width": bw_val,
            "unique_cases": n,
            "mean_replan_eta": round(sum(r["replan_eta"] for r in run_r) / n, 6),
            "mean_replan_tlast_s": round(sum(r["replan_latest_s"] for r in run_r) / n, 4),
            "mean_hyst_tlast_s": round(sum(r["hyst_latest_s"] for r in run_r) / n, 4),
            "replan_wins": sum(1 for r in run_r if r["winner"] == "reschedule"),
            "keep_wins": sum(1 for r in run_r if r["winner"] == "keep"),
            "ties": sum(1 for r in run_r if r["winner"] == "tie"),
            "hyst_losses": sum(1 for r in run_r if r["hyst_winner"] == "keep"),
            "v5_replan_tlast_s": v5_row["replan_latest_s"],
            "v5_delta_vs_keep_s": v5_row["delta_replan_minus_keep_s"],
        })

    write_csv(results_dir / "P4_dedup_expanded_cases.csv", full_rows)
    write_csv(results_dir / "P4_category_summary_expanded.csv", cat_summary_all)
    write_csv(results_dir / "P4_category_summary_dedup62.csv", cat_summary_dedup)
    write_csv(results_dir / "P4_budget_stability.csv", budget_rows)
    write_json(results_dir / "P4_extended_summary.json", {
        "raw_archived_case_count": len(dedup_base) + dup_count,
        "duplicates_removed": dup_count,
        "dedup_baseline_unique_cases": len(dedup_base),
        "expanded_new_cases": len(expanded),
        "total_unique_cases": len(full_rows),
        "dedup_total_row": cat_summary_dedup[-1],
        "expanded_total_row": cat_summary_all[-1],
        "budget_stability": budget_rows,
    })
    print(
        f"P4 extended audit: {len(dedup_base)+dup_count} raw -> {len(dedup_base)} unique baseline "
        f"({dup_count} duplicates removed) + {len(expanded)} spatial/hard-edge = {len(full_rows)} unique cases; "
        f"expanded W/T/L={cat_summary_all[-1]['replan_wins']}/{cat_summary_all[-1]['ties']}/{cat_summary_all[-1]['keep_wins']} "
        f"(hyst losses={cat_summary_all[-1]['hyst_losses']})"
    )


if __name__ == "__main__":
    p = ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path, default=DEFAULT_OUTPUT / "results")
    main(p.parse_args().results)

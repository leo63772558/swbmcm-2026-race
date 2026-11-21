"""Three-policy Problem 4 comparison: ignore (Keep), keep-append (FCFS), full reschedule.

Keep, as published, freezes the nominal schedule and never reassigns a vehicle, so a
new alert is structurally unservable and the completion ratio is capped below one by
definition. Keep-append closes that gap without granting any re-optimization: the frozen
timeline is executed verbatim, and any alert left unserved is appended after the vehicles
finish their cached work, dispatched on a first-come-first-served basis.

With this third policy the Keep-vs-Reschedule margin can be split into two parts:
the part that only requires *serving* the new alert (Keep-append) and the part that
requires *re-sequencing* existing work (Reschedule minus Keep-append).

AI assistance: WorkBuddy Agent (DeepSeek-V4.1-Flash), 2026-11-21, experiment plumbing
only; policy definition and interpretation remain team work.
"""
from argparse import ArgumentParser
from collections import defaultdict
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import b_revision_geometry as rounded
import b_revision_p4_extended as ext
import problem_b_geometry as model
import solve_problem_b as solver
from b_revision_data import DEFAULT_OUTPUT, window_score, write_csv, write_json


HORIZON = ext.HORIZON
DISTURBANCE = ext.DISTURBANCE


def frozen_release(nominal, failed, recovery):
    """Vehicle states after executing the frozen plan verbatim (link restored at recovery)."""
    states = []
    for vehicle in range(len(model.VEHICLES)):
        if vehicle == failed:
            states.append(None)
            continue
        own = [v for v in nominal if v.vehicle == vehicle]
        if own:
            last = max(own, key=lambda v: v.reset)
            states.append((last.station, max(last.reset, recovery)))
        else:
            states.append((model.VEHICLES[vehicle], recovery))
    return tuple(states)


def evaluate(nominal, specs, stations, beam_width):
    rows = []
    with ExitStack() as stack:
        stack.enter_context(patch.object(solver, "road_clear", rounded.road_clear))
        stack.enter_context(patch.object(solver, "route", rounded.route))
        stack.enter_context(patch.object(solver, "candidate_stations", rounded.stations))
        for suite, name, new_alert, failed, rec in specs:
            goals = dict(model.TARGETS)
            if new_alert is not None:
                goals["T4"] = new_alert
            preserved = solver.observation_starts(nominal, failed, DISTURBANCE)
            locked = {a: t for a, t in preserved.items() if t < rec}
            pending = {a: g for a, g in goals.items() if a not in preserved}

            state = solver.scenario_state(nominal, rec, failed, DISTURBANCE)
            revised = solver.solve_schedule(state, {a: g for a, g in goals.items() if a not in locked},
                                            HORIZON, beam_width=beam_width, stations=stations)
            solver.validate_visits(revised, goals)
            replan_starts = locked | solver.observation_starts(revised, None, DISTURBANCE)

            appended = ()
            if pending:
                release = frozen_release(nominal, failed, rec)
                appended = solver.solve_schedule(release, pending, HORIZON,
                                                 beam_width=beam_width, stations=stations)
                solver.validate_visits(appended, pending)
            append_starts = preserved | solver.observation_starts(appended, None, DISTURBANCE)

            keep = window_score(preserved, set(goals), 0.0, HORIZON, HORIZON)
            append = window_score(append_starts, set(goals), 0.0, HORIZON, HORIZON)
            replan = window_score(replan_starts, set(goals), 0.0, HORIZON, HORIZON)
            ranked = {"keep": keep, "append": append, "replan": replan}
            chosen = max(ranked, key=lambda p: (ranked[p][0], -ranked[p][2]))
            select = ranked[chosen]

            rows.append({
                "suite": suite, "case": name, "category": ext._category_of(new_alert, failed, rec),
                "failed_vehicle": "" if failed is None else failed + 1,
                "recovery_s": rec, "alerts": len(goals),
                "keep_eta": round(keep[1], 6), "keep_latest_s": round(keep[2], 6),
                "append_eta": round(append[1], 6), "append_latest_s": round(append[2], 6),
                "replan_eta": round(replan[1], 6), "replan_latest_s": round(replan[2], 6),
                "select_policy": chosen, "select_eta": round(select[1], 6),
                "select_latest_s": round(select[2], 6),
                "append_vs_keep": _winner(keep, append),
                "replan_vs_append": _winner(append, replan),
                "replan_vs_keep": _winner(keep, replan),
                "append_gain_s": round(keep[2] - append[2], 6) if append[0] == keep[0] else "",
                "replan_gain_over_append_s": round(append[2] - replan[2], 6) if append[0] == replan[0] else "",
            })
    return rows


def _winner(base, candidate):
    rank_base, rank_candidate = (base[0], -base[2]), (candidate[0], -candidate[2])
    return "candidate" if rank_candidate > rank_base else ("base" if rank_base > rank_candidate else "tie")


def summarize(rows, label):
    by_cat = defaultdict(list)
    for row in rows:
        by_cat[row["category"]].append(row)
    out = []
    for category, group in sorted(by_cat.items()):
        out.append(_block(category, group))
    out.append(_block("Total Unique Suite", rows))
    return out


def _block(category, rows):
    n = len(rows)
    served = [r for r in rows if r["append_eta"] >= 1.0 - 1e-12]
    return {
        "category": category, "cases": n,
        "mean_keep_eta": round(sum(r["keep_eta"] for r in rows) / n, 4),
        "mean_append_eta": round(sum(r["append_eta"] for r in rows) / n, 4),
        "mean_replan_eta": round(sum(r["replan_eta"] for r in rows) / n, 4),
        "mean_keep_latest_s": round(sum(r["keep_latest_s"] for r in rows) / n, 3),
        "mean_append_latest_s": round(sum(r["append_latest_s"] for r in rows) / n, 3),
        "mean_replan_latest_s": round(sum(r["replan_latest_s"] for r in rows) / n, 3),
        "mean_select_latest_s": round(sum(r["select_latest_s"] for r in rows) / n, 3),
        "select_append": sum(1 for r in rows if r["select_policy"] == "append"),
        "select_replan": sum(1 for r in rows if r["select_policy"] == "replan"),
        "select_keep": sum(1 for r in rows if r["select_policy"] == "keep"),
        "append_wins_vs_keep": sum(1 for r in rows if r["append_vs_keep"] == "candidate"),
        "append_ties_vs_keep": sum(1 for r in rows if r["append_vs_keep"] == "tie"),
        "append_losses_vs_keep": sum(1 for r in rows if r["append_vs_keep"] == "base"),
        "replan_wins_vs_append": sum(1 for r in rows if r["replan_vs_append"] == "candidate"),
        "replan_ties_vs_append": sum(1 for r in rows if r["replan_vs_append"] == "tie"),
        "replan_losses_vs_append": sum(1 for r in rows if r["replan_vs_append"] == "base"),
        "cases_where_append_serves_all": len(served),
        "mean_replan_gain_over_append_s": round(
            sum(r["replan_gain_over_append_s"] for r in served) / len(served), 3) if served else "",
    }


def main(results_dir=None):
    results_dir = Path(results_dir) if results_dir else (DEFAULT_OUTPUT / "results")
    nominal = ext._load_nominal_visits(results_dir)
    dedup_base, expanded, _ = ext.build_dedup_and_expanded_specs()
    specs = dedup_base + expanded
    rows = evaluate(nominal, specs, stations=2, beam_width=3)
    summary = summarize(rows, "all")
    write_csv(results_dir / "P4_keep_append_cases.csv", rows)
    write_csv(results_dir / "P4_keep_append_summary.csv", summary)

    budget = []
    for label, k_val, width in (("baseline_k2_bw3", 2, 3), ("budget_k8_bw20", 8, 20)):
        block = summarize(evaluate(nominal, specs, stations=k_val, beam_width=width), label)[-1]
        budget.append({"budget": label, "stations_k": k_val, "beam_width": width, **block})
    write_csv(results_dir / "P4_keep_append_budget.csv", budget)

    total = summary[-1]
    write_json(results_dir / "P4_keep_append_summary.json",
               {"stations_k": 2, "beam_width": 3, "unique_cases": total["cases"],
                "total": total, "budget_stability": budget})
    print(f"Keep mean eta={total['mean_keep_eta']}, Keep-append={total['mean_append_eta']}, "
          f"Reschedule={total['mean_replan_eta']} over {total['cases']} cases")
    print(f"Append vs Keep W/T/L = {total['append_wins_vs_keep']}/{total['append_ties_vs_keep']}/"
          f"{total['append_losses_vs_keep']}; Reschedule vs Append = "
          f"{total['replan_wins_vs_append']}/{total['replan_ties_vs_append']}/{total['replan_losses_vs_append']}")
    print(f"Append serves all alerts in {total['cases_where_append_serves_all']}/{total['cases']} cases; "
          f"mean Reschedule gain over Append = {total['mean_replan_gain_over_append_s']} s")
    print(f"Three-way gate chooses append {total['select_append']}x, replan {total['select_replan']}x, "
          f"keep {total['select_keep']}x; mean t_last={total['mean_select_latest_s']} s "
          f"(replan-only {total['mean_replan_latest_s']} s)")
    for row in budget:
        print(f"  [{row['budget']}] append W/T/L vs keep {row['append_wins_vs_keep']}/"
              f"{row['append_ties_vs_keep']}/{row['append_losses_vs_keep']}; "
              f"replan vs append {row['replan_wins_vs_append']}/{row['replan_ties_vs_append']}/"
              f"{row['replan_losses_vs_append']}; mean t_last replan {row['mean_replan_latest_s']}")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_OUTPUT / "results")
    main(parser.parse_args().results)

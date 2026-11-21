"""Recompute the P2 dispatch benchmarks with faster pan and a crossing floor.

AI assistance: ChatGPT (Codex, GPT-6 series), OpenAI, 2026-11-21.
Public model release date unverified. Implemented and verified the specified comparisons.
"""
from argparse import ArgumentParser
from functools import partial
from pathlib import Path

import problem_b_geometry as model
import solve_problem_b as solver
from b_hardcore_audit import _exact_p2_bnb, _p2_replay_witness
from b_revision_data import DEFAULT_OUTPUT, read_json, write_csv
from b_revision_sensitivity_pareto import (
    _decoupled_slew_time,
    _p2_fixed_plan_time,
    _p2_reoptimized_schedule,
)


def _full_pool_run(**options):
    run = _exact_p2_bnb(**options)
    if (
        run["discrete_station_pool_size"] != 585
        or run["legal_pairings_total"] != 1000
        or run["acyclic_ordered_topologies_total"] != 4200
        or run["initial_upper_bound_s"] is not None
        or not _p2_replay_witness(run, **options)
    ):
        raise RuntimeError(f"Exact full-pool P2 audit failed: {run}")
    return run


def _angle_rows(method, min_crossing_deg, stations, starts, run=None):
    latest = max(starts.values())
    rows = []
    for alert, goal in model.TARGETS.items():
        first, second = sorted(stations[alert].items())
        rms, gamma = solver.accuracy(first[1], second[1], goal)
        rows.append({
            "method": method,
            "min_crossing_deg": min_crossing_deg,
            "latest_start_s": round(latest, 6),
            "alert": alert,
            "paired_start_s": round(starts[alert], 6),
            "vehicle_1": first[0],
            "vehicle_2": second[0],
            "x_1_m": round(first[1][0], 9),
            "y_1_m": round(first[1][1], 9),
            "x_2_m": round(second[1][0], 9),
            "y_2_m": round(second[1][1], 9),
            "crossing_deg": round(gamma, 9),
            "horizontal_rms_m": round(rms, 9),
            "station_alert_candidates": run["discrete_station_pool_size"] if run else 585,
            "vehicle_pairings_evaluated": run["legal_pairings_total"] if run else "",
            "acyclic_orders_evaluated": run["acyclic_ordered_topologies_total"] if run else "",
        })
    return rows


def main(out_results):
    out_results = Path(out_results)
    nominal = read_json(out_results / "P2_main_plans.json")
    beam = nominal["beam"]
    pan_speed = 36.0
    tilt_speed = model.PITCH_SPEED
    faster_pan = partial(_decoupled_slew_time, pan_dps=pan_speed, pitch_dps=tilt_speed)
    faster_run = _full_pool_run(slew_time=faster_pan)
    fixed = _p2_fixed_plan_time(beam, model.SPEED, pan_speed, tilt_speed)
    _, greedy = _p2_reoptimized_schedule(
        model.SPEED, pan_speed, tilt_speed, model.PITCH_MAX,
        k=nominal["shared_k"], bw=nominal["beam_width"],
    )
    exact = faster_run["exact_discrete_optimum_s"]
    if exact > min(round(fixed, 6), round(greedy, 6)):
        raise RuntimeError("A feasible dispatch outperformed the exact faster-pan benchmark")
    pan_rows = []
    for method, latest, k, width, run in (
        ("fixed_nominal_plan", fixed, "", "", None),
        ("greedy_beam", greedy, nominal["shared_k"], nominal["beam_width"], None),
        ("exact_full_pool", exact, "", "", faster_run),
    ):
        pan_rows.append({
            "method": method,
            "pan_deg_s": pan_speed,
            "tilt_deg_s": tilt_speed,
            "latest_start_s": round(latest, 6),
            "station_alert_candidates": faster_run["discrete_station_pool_size"],
            "arrival_shortlist_k": k,
            "beam_width": width,
            "vehicle_pairings_evaluated": run["legal_pairings_total"] if run else "",
            "acyclic_orders_evaluated": run["acyclic_ordered_topologies_total"] if run else "",
        })

    beam_stations = {alert: {} for alert in model.TARGETS}
    beam_starts = {}
    for visit in beam:
        alert = visit["alert"]
        beam_stations[alert][f"V{visit['vehicle'] + 1}"] = visit["station"]
        beam_starts[alert] = visit["start"]
    angle_rows = _angle_rows("archived_nominal_beam", 0.0, beam_stations, beam_starts)
    unconstrained = _full_pool_run()
    constrained = _full_pool_run(min_crossing_deg=30.0)
    if constrained["exact_discrete_optimum_s"] < unconstrained["exact_discrete_optimum_s"]:
        raise RuntimeError("The restricted candidate pool outperformed the unconstrained exact optimum")
    for method, floor, run in (
        ("exact_unconstrained", 0.0, unconstrained),
        ("exact_angle_floor", 30.0, constrained),
    ):
        witness = run["witness"]
        angle_rows.extend(_angle_rows(method, floor, witness["stations_m"], witness["starts_s"], run))
    write_csv(out_results / "P2_pan_speed_benchmark.csv", pan_rows)
    write_csv(out_results / "P2_angle_constrained_tradeoff.csv", angle_rows)
    print(f"Pan {pan_speed:g} deg/s: fixed={fixed:.6f}s, beam={greedy:.6f}s, exact={exact:.6f}s")
    for method in ("archived_nominal_beam", "exact_unconstrained", "exact_angle_floor"):
        rows = [row for row in angle_rows if row["method"] == method]
        worst_rms = max(row["horizontal_rms_m"] for row in rows)
        print(f"{method}: latest={rows[0]['latest_start_s']:.6f}s, worst RMS={worst_rms:.6f}m")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_OUTPUT / "results")
    main(parser.parse_args().results)

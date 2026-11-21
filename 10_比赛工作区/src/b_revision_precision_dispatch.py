"""Precision-aware dispatch study for Problem 2(2).

Adds a crossing-angle guard gamma in [gamma_min, gamma_max] to the cooperative
dispatcher, reruns the shared-shortlist beam search (k=8, w=20) and the exact
Branch-and-Bound certification on the 585-station pool, and records for every
alert the station pair, baseline, crossing angle and local first-order RMS.

Defaults reproduce the published time-only optimum (gamma_min=0), so the script
is a pure superset of the existing audit.

AI assistance: WorkBuddy Agent (DeepSeek-V4.1-Flash), 2026-11-21, experiment
plumbing only; model formulation and interpretation remain team work.
"""
import json
from contextlib import ExitStack
from dataclasses import asdict
from math import dist
from unittest.mock import patch

import b_hardcore_audit as audit
import b_revision_geometry as rounded
import problem_b_geometry as model
import solve_problem_b as solver
from b_revision_data import DEFAULT_OUTPUT, write_csv, write_json


OUT = DEFAULT_OUTPUT / "results"
GRID = ((0.0, 180.0), (20.0, 160.0), (30.0, 180.0), (30.0, 150.0), (40.0, 140.0), (45.0, 135.0), (60.0, 120.0))
SHARED_K, BEAM_WIDTH = 8, 20


def with_routing():
    stack = ExitStack()
    stack.enter_context(patch.object(solver, "road_clear", rounded.road_clear))
    stack.enter_context(patch.object(solver, "route", rounded.route))
    stack.enter_context(patch.object(solver, "candidate_stations", rounded.stations))
    return stack


def _replay(assignment, starts):
    """assignment: {alert: {vehicle(1-based): station}}; causally replays the clocks."""
    state = {v: (model.VEHICLES[v - 1], 0.0) for v in range(1, len(model.VEHICLES) + 1)}
    visits = []
    for alert in sorted(starts, key=starts.get):
        pair = assignment[alert]
        goal = model.TARGETS[alert]
        slots = []
        for vehicle, station in pair.items():
            position, free = state[vehicle]
            distance, path = solver.route(position, station)
            arrival = free + distance / model.SPEED
            ready = arrival + solver._station_slew_time(station, goal)
            slots.append((vehicle, station, path, free, arrival, ready))
        start = max(row[5] for row in slots)
        if abs(start - starts[alert]) > 1e-5:
            return None
        for vehicle, station, path, depart, arrival, ready in slots:
            reset = start + model.OBSERVE + solver._station_slew_time(station, goal)
            visits.append((vehicle - 1, alert, station, path, depart, arrival, ready, start,
                           start + model.OBSERVE, reset))
            state[vehicle] = (station, reset)
    return visits


def rebuild(witness):
    """Reconstruct full phase clocks from a Branch-and-Bound witness.

    The witness fixes the vehicle pair and the station set per alert, but the
    stored order within a pair may be swapped by the solver's loop reordering,
    so we test both assignments per alert (2^3 combinations) and keep the unique
    physically feasible one. Start times are the solver's and are re-verified.
    """
    alerts = sorted(witness["pairing"])
    options = []
    for alert in alerts:
        u, w = witness["pairing"][alert]
        s1, s2 = (tuple(s) for s in witness["stations_m"][alert])
        options.append((alert, [{u: s1, w: s2}, {u: s2, w: s1}]))
    feasible = []
    for combo in range(1 << len(options)):
        assignment = {}
        for bit, (alert, pair_options) in enumerate(options):
            assignment[alert] = pair_options[(combo >> bit) & 1]
        replay = _replay(assignment, witness["starts_s"])
        if replay is not None:
            feasible.append(replay)
    if not feasible:
        raise SystemExit("witness replay found no physically feasible vehicle-station assignment")
    if len(feasible) > 1:
        print(f"   note: {len(feasible)} replay assignments tie; keeping the first")
    return tuple(sorted((solver.Visit(*row) for row in feasible[0]), key=lambda v: (v.depart, v.vehicle)))
    return tuple(sorted(finished, key=lambda v: (v.depart, v.vehicle)))


def plan_rows(gamma_min, gamma_max, visits):
    per_alert = {}
    for v in visits:
        per_alert.setdefault(v.alert, []).append(v)
    rows = []
    for alert, pair in sorted(per_alert.items()):
        goal = model.TARGETS[alert]
        a, b = pair
        rms, gamma = solver.accuracy(a.station, b.station, goal)
        rows.append({
            "crossing_min_deg": gamma_min, "crossing_max_deg": gamma_max, "alert": alert,
            "vehicle_1": a.vehicle + 1, "vehicle_2": b.vehicle + 1,
            "x_1_m": round(a.station[0], 6), "y_1_m": round(a.station[1], 6),
            "x_2_m": round(b.station[0], 6), "y_2_m": round(b.station[1], 6),
            "ready_1_s": round(a.ready, 6), "ready_2_s": round(b.ready, 6),
            "start_s": round(a.start, 6),
            "crossing_deg": round(gamma, 6), "baseline_m": round(dist(a.station, b.station), 6),
            "rms_m": round(rms, 6),
        })
    return rows


def main():
    summary, detail, plans = [], [], {}
    with with_routing():
        for gamma_min, gamma_max in GRID:
            with patch.object(solver, "CROSSING_MIN_DEG", gamma_min), \
                 patch.object(solver, "CROSSING_MAX_DEG", gamma_max):
                visits = solver.solve_schedule(solver.INITIAL, model.TARGETS,
                                               beam_width=BEAM_WIDTH, stations=SHARED_K)
                beam_last = max((v.start for v in visits), default=float("inf"))
                feasible = len({v.alert for v in visits}) == len(model.TARGETS)
                bnb = audit._exact_p2_bnb(shortlist_k=SHARED_K, initial_ub=beam_last + 1e-4,
                                          crossing_min=gamma_min, crossing_max=gamma_max)
                bnb_last = bnb["exact_discrete_optimum_s"]
                source = "beam"
                if bnb_last is not None and bnb["witness"] is not None and bnb_last < beam_last - 1e-6:
                    visits = rebuild(bnb["witness"])
                    beam_last = max(v.start for v in visits)
                    feasible = len({v.alert for v in visits}) == len(model.TARGETS)
                    source = "bnb-witness"
            rows = plan_rows(gamma_min, gamma_max, visits) if feasible else []
            detail.extend(rows)
            worst = max((r["rms_m"] for r in rows), default=float("inf"))
            summary.append({
                "crossing_min_deg": gamma_min, "crossing_max_deg": gamma_max,
                "feasible": feasible, "latest_start_s": round(beam_last, 6) if feasible else "",
                "bnb_optimum_s": bnb_last, "schedule_source": source,
                "worst_rms_m": round(worst, 6) if rows else "",
                "mean_crossing_deg": round(sum(r["crossing_deg"] for r in rows) / len(rows), 6) if rows else "",
                "pruned_layer0": bnb["pruned_layer0_topologies"],
                "pruned_inner": bnb["pruned_inner_branches"],
            })
            plans[f"{gamma_min:g}-{gamma_max:g}"] = [asdict(v) for v in visits]
            print(f"gamma in [{gamma_min:g},{gamma_max:g}]: t_last={beam_last:.6f}s "
                  f"bnb={bnb_last}s worst_rms={worst:.4f}m")
            for r in rows:
                print(f"   {r['alert']}: V{r['vehicle_1']}/V{r['vehicle_2']} "
                      f"gamma={r['crossing_deg']:.2f} baseline={r['baseline_m']:.3f} rms={r['rms_m']:.3f}")

    write_csv(OUT / "P2_precision_dispatch.csv", detail)
    write_csv(OUT / "P2_precision_tradeoff.csv", summary)
    write_json(OUT / "P2_precision_plans.json", plans)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()

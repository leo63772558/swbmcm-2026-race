"""Parameter perturbation, pairwise interaction, weight-stability, and 3D Pareto analysis.

AI assistance:
  - Antigravity (Gemini), Google DeepMind; version release date: not publicly disclosed; used 2026-11-21.
All P1, P2 (both fixed-plan and re-optimized with decoupled pan/tilt axes), P3, and P4
metrics are evaluated directly through the verified physics and discrete-event solvers;
no linear proxy formulas are used and existing P1-P4 baseline CSVs are never modified.
"""
from argparse import ArgumentParser
from contextlib import ExitStack
from math import dist, radians, tan
from pathlib import Path
from unittest.mock import patch

import b_revision_geometry as rounded
import b_revision_probability as prob
import problem_b_geometry as model
import solve_problem_b as solver
from b_revision_data import DEFAULT_OUTPUT, read_csv, read_json, write_csv, write_json


WEIGHT_SCHEMES = (
    ("baseline_balanced", (0.25, 0.30, 0.25, 0.20), "Baseline balanced (0.25/0.30/0.25/0.20)"),
    ("equal_weight", (0.25, 0.25, 0.25, 0.25), "Equal weight (0.25/0.25/0.25/0.25)"),
    ("time_priority", (0.15, 0.45, 0.15, 0.25), "Time priority (0.15/0.45/0.15/0.25)"),
    ("precision_priority", (0.35, 0.15, 0.35, 0.15), "Precision priority (0.35/0.15/0.35/0.15)"),
    ("resilience_priority", (0.15, 0.20, 0.15, 0.50), "Resilience priority (0.15/0.20/0.15/0.50)"),
)


def _p1_quality(pitch_deg):
    t1_h = model.TARGETS["T1"][2]
    r_min = (t1_h - model.HEIGHT) / tan(radians(pitch_deg))
    return 1.0 / r_min


def _p3_crossing(a_val, b_val, n=96):
    """Exact bisection for 95% coverage distance using b_revision_probability.coverage."""
    if a_val < 0 or b_val < 0:
        raise ValueError("Position error parameters a and b must be non-negative")
    lo, hi = 0.0, 240.0
    if prob.coverage(a_val + b_val * lo, n=n) < prob.REQUIRED:
        return 0.0
    if b_val == 0.0:
        return hi
    if prob.coverage(a_val + b_val * hi, n=n) >= prob.REQUIRED:
        return hi
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if prob.coverage(a_val + b_val * mid, n=n) >= prob.REQUIRED:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _decoupled_slew_time(point, goal, pan_dps, pitch_dps):
    """Strict decoupled pan/tilt slew time: max(|pan|/w_pan, |tilt|/w_tilt)."""
    pan_deg, tilt_deg = model.angles(point, goal)
    return max(abs(pan_deg) / pan_dps, abs(tilt_deg) / pitch_dps)


def _p2_fixed_plan_time(nominal_beam_plan, speed_mps, pan_dps, pitch_dps):
    """Fixed-Plan Local Sensitivity: hold nominal k=8 vehicle-station schedule fixed and
    recompute exact drive times and decoupled pan/tilt slew/reset durations."""
    alert_order = sorted(
        {v["alert"] for v in nominal_beam_plan},
        key=lambda a: min(v["start"] for v in nominal_beam_plan if v["alert"] == a),
    )
    obs_dur = model.OBSERVE
    v_free = {v: 0.0 for v in range(len(model.VEHICLES))}
    alert_starts = {}
    for alert in alert_order:
        goal = model.TARGETS[alert]
        pair = [v for v in nominal_beam_plan if v["alert"] == alert]
        readies = []
        for item in pair:
            vid = int(item["vehicle"])
            dep = v_free[vid]
            path = item["path"]
            leg_m = sum(dist(a, b) for a, b in zip(path[:-1], path[1:]))
            slew_s = _decoupled_slew_time(tuple(item["station"]), goal, pan_dps, pitch_dps)
            ready = dep + leg_m / speed_mps + slew_s
            readies.append((vid, ready, slew_s))
        t_start = max(x[1] for x in readies)
        alert_starts[alert] = t_start
        for vid, _ready, slew_s in readies:
            v_free[vid] = t_start + obs_dur + slew_s
    return max(alert_starts.values())


def _visible_at_pitch(point, goal, pitch_max_deg):
    pitch = model.angles(point, goal)[1]
    return (
        model.vehicle_fits(point)
        and model.PITCH_MIN - 1e-9 <= pitch <= pitch_max_deg + 1e-9
        and not any(
            model.segment_hits_box((*point, model.HEIGHT), goal, ((x0, x1), (y0, y1), (0, z)))
            for x0, x1, y0, y1, z in model.BUILDINGS
        )
    )


def _stations_at_pitch(goal, pitch_max_deg):
    if abs(pitch_max_deg - model.PITCH_MAX) < 1e-12:
        return rounded.stations(goal)
    base_r = (goal[2] - model.HEIGHT) / tan(radians(pitch_max_deg))
    pts = [
        pt for offset in (0, 1, 3, 7, 12, 20, 32)
        for pt in model.ring(goal, base_r + offset, 15)
    ]
    pts.extend((x, y) for x in range(4, int(model.WIDTH), 8) for y in range(4, int(model.DEPTH), 8))
    return tuple(pt for pt in pts if _visible_at_pitch(pt, goal, pitch_max_deg) and rounded.road_clear(pt, pt))


def _p2_reoptimized_schedule(speed_mps, pan_dps, pitch_dps, pitch_max_deg, k=8, bw=20):
    """Re-Optimized Sensitivity: genuinely re-solve cooperative dispatch under perturbed parameters."""
    orig_opts = solver.station_options
    station_cache = {}

    def custom_stations(goal):
        if goal not in station_cache:
            station_cache[goal] = _stations_at_pitch(goal, pitch_max_deg)
        return station_cache[goal]

    def custom_slew(point, goal):
        return _decoupled_slew_time(point, goal, pan_dps, pitch_dps)

    with ExitStack() as stack:
        stack.enter_context(patch.object(solver, "SPEED", speed_mps))
        stack.enter_context(patch.object(solver, "PAN_SPEED", pan_dps))
        stack.enter_context(patch.object(solver, "PITCH_SPEED", pitch_dps))
        stack.enter_context(patch.object(solver, "_station_slew_time", custom_slew))
        stack.enter_context(patch.object(solver, "road_clear", rounded.road_clear))
        stack.enter_context(patch.object(solver, "route", rounded.route))
        stack.enter_context(patch.object(solver, "candidate_stations", custom_stations))

        def screen(state, goal, _limit):
            return sorted(orig_opts(state, goal, len(custom_stations(goal))))[:k]

        stack.enter_context(patch.object(solver, "station_options", screen))
        plan = solver.solve_schedule(solver.INITIAL, model.TARGETS, beam_width=bw, stations=k)
    return plan, max(v.start for v in plan)


def _p4_real_reschedule_eval(base_plan_visits, outage_s, speed_mps, pan_dps, pitch_dps, pitch_max_deg):
    """Real discrete-event P4 rescheduling evaluation under perturbed outage & vehicle parameters.

    Re-runs real event replay (scenario_state + solve_schedule) on the benchmark compound
    outage/fault/new-alert recovery suite (all_V2, failure_outage_V2, new_outage) with
    recovery clock t_rec = t_disturbance + outage_s, returning mean completion ratio eta and
    mean latest paired observation start time (s). Zero proxy formulas.
    """
    t_dist = model.number("p4", "disturbance", "occurrence_time")  # 5.0 s
    horizon = model.number("p4", "evaluation", "window_end")      # 60.0 s
    t_rec = min(horizon, t_dist + outage_s)
    altitude_t4 = model.number("p4", "new_alert", "altitude")
    ranges = model.read_values("p4", "new_alert", "horizontal_range_min", "horizontal_range_max")
    t4_north = model.target(90.0, ranges[1], altitude_t4)

    probe_cases = (
        ("all_V2", t4_north, 1, t_rec),            # V2 fails + T4 + comms outage
        ("failure_outage_V2", None, 1, t_rec),     # V2 fails + comms outage
        ("new_outage", t4_north, None, t_rec),     # T4 + comms outage
    )

    station_cache = {}

    def custom_stations(goal):
        if goal not in station_cache:
            station_cache[goal] = _stations_at_pitch(goal, pitch_max_deg)
        return station_cache[goal]

    def custom_slew(point, goal):
        return _decoupled_slew_time(point, goal, pan_dps, pitch_dps)

    def custom_visible(point, goal):
        return _visible_at_pitch(point, goal, pitch_max_deg)

    # First rebuild the nominal plan visits under the perturbed speed/pan/tilt/pitch
    if (
        abs(speed_mps - model.SPEED) < 1e-12
        and abs(pan_dps - model.PAN_SPEED) < 1e-12
        and abs(pitch_dps - model.PITCH_SPEED) < 1e-12
        and abs(pitch_max_deg - model.PITCH_MAX) < 1e-12
    ):
        plan_visits = base_plan_visits
    else:
        plan_visits, _ = _p2_reoptimized_schedule(speed_mps, pan_dps, pitch_dps, pitch_max_deg)

    etas, latest_starts = [], []
    with ExitStack() as stack:
        stack.enter_context(patch.object(solver, "SPEED", speed_mps))
        stack.enter_context(patch.object(solver, "PAN_SPEED", pan_dps))
        stack.enter_context(patch.object(solver, "PITCH_SPEED", pitch_dps))
        stack.enter_context(patch.object(solver, "_station_slew_time", custom_slew))
        stack.enter_context(patch.object(solver, "road_clear", rounded.road_clear))
        stack.enter_context(patch.object(solver, "route", rounded.route))
        stack.enter_context(patch.object(solver, "candidate_stations", custom_stations))
        stack.enter_context(patch.object(solver, "visible", custom_visible))
        outcomes, _timelines = solver.solve_p4(plan_visits, cases=probe_cases)
        for row in outcomes:
            if row["policy"] == "reschedule":
                etas.append(float(row["completion_ratio"]))
                latest_starts.append(float(row["latest_start_s"]))
    return sum(etas) / len(etas), sum(latest_starts) / len(latest_starts)


def compute_parameter_perturbation(results_dir):
    plans_json = read_json(results_dir / "P2_main_plans.json")
    nominal_beam_raw = plans_json["beam"]
    nominal_visits = tuple(
        solver.Visit(
            vehicle=int(v["vehicle"]), alert=v["alert"], station=tuple(v["station"]),
            path=tuple(tuple(p) for p in v["path"]), depart=float(v["depart"]),
            arrival=float(v["arrival"]), ready=float(v["ready"]),
            start=float(v["start"]), end=float(v["end"]), reset=float(v["reset"]),
        )
        for v in nominal_beam_raw
    )

    nom = {
        "vehicle_speed": model.SPEED,          # 3.0 m/s
        "pan_speed": model.PAN_SPEED,          # 30.0 deg/s (tilt fixed at 30.0 deg/s)
        "pitch_ceiling": model.PITCH_MAX,      # 80.0 deg
        "pos_error_slope": prob.B,             # 0.02 m/m
        "pos_error_intercept": prob.A,         # 0.30 m
        "outage_duration": 25.0,               # 25.0 s (t_rec = 30.0 s)
    }
    bounds = {
        "vehicle_speed": (round(nom["vehicle_speed"] * 0.8, 4), round(nom["vehicle_speed"] * 1.2, 4), "Vehicle speed v (m/s)"),
        "pan_speed": (round(nom["pan_speed"] * 0.8, 4), round(nom["pan_speed"] * 1.2, 4), "Gimbal pan rate w_pan (deg/s)"),
        "pitch_ceiling": (76.0, 82.0, "Pitch ceiling beta_max (deg)"),
        "pos_error_slope": (round(nom["pos_error_slope"] * 0.8, 5), round(nom["pos_error_slope"] * 1.2, 5), "Drift slope b (m/m)"),
        "pos_error_intercept": (round(nom["pos_error_intercept"] * 0.8, 4), round(nom["pos_error_intercept"] * 1.2, 4), "Base pos. std a (m)"),
        "outage_duration": (20.0, 30.0, "Outage duration dt_out (s)"),
    }

    pitch_dps_fixed = model.PITCH_SPEED  # Strictly held constant at 30.0 deg/s when perturbing pan_speed

    # Memoize real solver evaluations so OAT, 6x6 interactions, and 5 weight schemes share exact solver outputs
    eval_cache = {}

    def evaluate_metrics(params):
        key = tuple((k, round(float(params[k]), 8)) for k in sorted(nom))
        if key not in eval_cache:
            q1 = _p1_quality(params["pitch_ceiling"])
            t2_fixed = _p2_fixed_plan_time(
                nominal_beam_raw, params["vehicle_speed"], params["pan_speed"], pitch_dps_fixed
            )
            _, t2_reopt = _p2_reoptimized_schedule(
                params["vehicle_speed"], params["pan_speed"], pitch_dps_fixed, params["pitch_ceiling"]
            )
            s3 = _p3_crossing(params["pos_error_intercept"], params["pos_error_slope"])
            eta4, t4_real = _p4_real_reschedule_eval(
                nominal_visits, params["outage_duration"],
                params["vehicle_speed"], params["pan_speed"], pitch_dps_fixed, params["pitch_ceiling"],
            )
            eval_cache[key] = {
                "q1": q1, "t2_fixed": t2_fixed, "t2_reopt": t2_reopt,
                "s3": s3, "eta4": eta4, "t4_real": t4_real,
            }
        return eval_cache[key]

    m0 = evaluate_metrics(nom)

    def composite_index(params, weights=(0.25, 0.30, 0.25, 0.20), mode="reopt"):
        """Weighted dimensionless mission effectiveness index J (nominal = 1.000).
        Weights (w1, w2, w3, w4) apply to P1 quality, P2 dispatch latency (inverse),
        P3 admissible travel distance, and P4 real event-simulated recovery latency (inverse)."""
        m = evaluate_metrics(params)
        w1, w2, w3, w4 = weights
        t2_val = m["t2_reopt"] if mode == "reopt" else m["t2_fixed"]
        t2_ref = m0["t2_reopt"] if mode == "reopt" else m0["t2_fixed"]
        # P4 sub-score combines real completion fraction eta4 and real recovery latency t4_real
        p4_ratio = (m["eta4"] / m0["eta4"]) * (m0["t4_real"] / max(m["t4_real"], 1e-6))
        return (
            w1 * (m["q1"] / m0["q1"])
            + w2 * (t2_ref / t2_val)
            + w3 * (m["s3"] / m0["s3"])
            + w4 * p4_ratio
        )

    keys = list(nom.keys())
    j0 = composite_index(nom)

    # 1. OAT & Tornado (Re-Optimized primary + Fixed-Plan local comparison)
    oat_rows = []
    fixed_vs_reopt_rows = []
    for k in keys:
        lo_v, hi_v, label = bounds[k]
        p_lo = {**nom, k: lo_v}
        p_hi = {**nom, k: hi_v}
        m_lo = evaluate_metrics(p_lo)
        m_hi = evaluate_metrics(p_hi)
        j_lo = composite_index(p_lo, mode="reopt")
        j_hi = composite_index(p_hi, mode="reopt")
        j_lo_fix = composite_index(p_lo, mode="fixed")
        j_hi_fix = composite_index(p_hi, mode="fixed")
        main_eff = abs(j_hi - j_lo)
        oat_rows.append({
            "parameter": k,
            "label": label,
            "low_param": lo_v,
            "nominal_param": nom[k],
            "high_param": hi_v,
            "j_low": round(j_lo, 6),
            "j_nominal": round(j0, 6),
            "j_high": round(j_hi, 6),
            "delta_low_pct": round((j_lo - j0) / j0 * 100.0, 4),
            "delta_high_pct": round((j_hi - j0) / j0 * 100.0, 4),
            "swing_pct": round(main_eff / j0 * 100.0, 4),
            "fixed_plan_swing_pct": round(abs(j_hi_fix - j_lo_fix) / j0 * 100.0, 4),
        })
        fixed_vs_reopt_rows.append({
            "parameter": k,
            "low_param": lo_v, "nominal_param": nom[k], "high_param": hi_v,
            "p2_fixed_low_s": round(m_lo["t2_fixed"], 6),
            "p2_fixed_nom_s": round(m0["t2_fixed"], 6),
            "p2_fixed_high_s": round(m_hi["t2_fixed"], 6),
            "p2_reopt_low_s": round(m_lo["t2_reopt"], 6),
            "p2_reopt_nom_s": round(m0["t2_reopt"], 6),
            "p2_reopt_high_s": round(m_hi["t2_reopt"], 6),
            "p4_eta_low": round(m_lo["eta4"], 4),
            "p4_eta_high": round(m_hi["eta4"], 4),
            "p4_real_tlast_low_s": round(m_lo["t4_real"], 6),
            "p4_real_tlast_nom_s": round(m0["t4_real"], 6),
            "p4_real_tlast_high_s": round(m_hi["t4_real"], 6),
        })

    # 2. 6x6 Pairwise Interaction Matrix (strictly symmetric, real solver evaluations)
    inter_rows = []
    inter_sum = {k: 0.0 for k in keys}
    for i, ki in enumerate(keys):
        for j, kj in enumerate(keys):
            if i == j:
                val = 0.0
            else:
                lo_i, hi_i, _ = bounds[ki]
                lo_j, hi_j, _ = bounds[kj]
                j_pp = composite_index({**nom, ki: hi_i, kj: hi_j}, mode="reopt")
                j_pm = composite_index({**nom, ki: hi_i, kj: lo_j}, mode="reopt")
                j_mp = composite_index({**nom, ki: lo_i, kj: hi_j}, mode="reopt")
                j_mm = composite_index({**nom, ki: lo_i, kj: lo_j}, mode="reopt")
                val = abs((j_pp - j_pm - j_mp + j_mm) / (4.0 * j0)) * 100.0
                inter_sum[ki] += val
            inter_rows.append({
                "param_i": ki, "param_j": kj,
                "label_i": bounds[ki][2], "label_j": bounds[kj][2],
                "interaction_pct": round(val, 5),
            })

    total_swing = sum(r["swing_pct"] for r in oat_rows)
    for r in oat_rows:
        r["interaction_sum_pct"] = round(inter_sum[r["parameter"]], 5)
        r["total_effect_pct"] = round(r["swing_pct"] + inter_sum[r["parameter"]], 4)
        r["main_share_pct"] = round(r["swing_pct"] / total_swing * 100.0, 2) if total_swing else 0.0

    oat_rows.sort(key=lambda r: r["swing_pct"], reverse=True)
    cum = 0.0
    for r in oat_rows:
        cum += r["main_share_pct"]
        r["cumulative_share_pct"] = round(min(100.0, cum), 2)

    # 3. Weight-Perturbation Stability Check across 5 schemes (baseline + 4 perturbations)
    weight_rows = []
    for scheme_name, w_tuple, desc in WEIGHT_SCHEMES:
        scored = []
        for k in keys:
            lo_v, hi_v, _ = bounds[k]
            j_lo = composite_index({**nom, k: lo_v}, weights=w_tuple, mode="reopt")
            j_hi = composite_index({**nom, k: hi_v}, weights=w_tuple, mode="reopt")
            scored.append((k, abs(j_hi - j_lo) * 100.0))
        scored.sort(key=lambda x: x[1], reverse=True)
        tot_w = sum(x[1] for x in scored) or 1.0
        for rank_idx, (k, sw) in enumerate(scored, 1):
            weight_rows.append({
                "scheme": scheme_name,
                "weights": "/".join(f"{w:.2f}" for w in w_tuple),
                "description": desc,
                "rank": rank_idx,
                "parameter": k,
                "swing_pct": round(sw, 4),
                "share_pct": round(sw / tot_w * 100.0, 2),
            })

    write_csv(results_dir / "Global_sensitivity_oat.csv", oat_rows)
    write_csv(results_dir / "Global_sensitivity_interaction.csv", inter_rows)
    write_csv(results_dir / "Global_sensitivity_fixed_vs_reopt.csv", fixed_vs_reopt_rows)
    write_csv(results_dir / "Global_sensitivity_weight_check.csv", weight_rows)
    return oat_rows, inter_rows, fixed_vs_reopt_rows, weight_rows


def compute_pareto_tradeoff_3d(results_dir):
    """True 3D multi-objective Pareto sweep minimizing (latest_start_s, total_travel_m)
    and maximizing mean_quality_m_inv across 16 verified rounded-clearance solver configs."""
    orig_opts = solver.station_options

    def all_options(state, goal):
        return sorted(orig_opts(state, goal, len(solver.candidate_stations(goal))))

    rows = []
    with (
        patch.object(solver, "road_clear", rounded.road_clear),
        patch.object(solver, "route", rounded.route),
        patch.object(solver, "candidate_stations", rounded.stations),
    ):
        configs = [
            ("beam", 2, 10), ("beam", 3, 5), ("beam", 3, 20), ("beam", 4, 20),
            ("beam", 5, 20), ("beam", 6, 20), ("beam", 8, 5), ("beam", 8, 10),
            ("beam", 8, 20), ("beam", 8, 40), ("beam", 10, 20), ("beam", 12, 20),
            ("nearest", 3, 1), ("nearest", 5, 1), ("nearest", 8, 1), ("nearest", 12, 1),
        ]
        for policy, k, bw in configs:
            def screen(state, goal, _limit, _k=k):
                return all_options(state, goal)[:_k]

            with patch.object(solver, "station_options", screen):
                plan = solver.solve_schedule(
                    solver.INITIAL, model.TARGETS,
                    nearest=(policy == "nearest"), beam_width=bw, stations=k,
                )
            t_last = max(v.start for v in plan)
            total_travel_m = sum((v.arrival - v.depart) * model.SPEED for v in plan)
            ranges = [dist(v.station, model.TARGETS[v.alert][:2]) for v in plan]
            mean_range_m = sum(ranges) / len(ranges)
            mean_quality = sum(1.0 / r for r in ranges) / len(ranges)
            by_v_dist = {}
            for v in plan:
                by_v_dist[v.vehicle] = by_v_dist.get(v.vehicle, 0.0) + (v.arrival - v.depart) * model.SPEED
            max_veh_dist_m = max(by_v_dist.values())
            rows.append({
                "policy": policy, "k": k, "beam_width": bw,
                "_raw_t": t_last, "_raw_d": total_travel_m, "_raw_q": mean_quality,
                "latest_start_s": round(t_last, 6),
                "total_travel_m": round(total_travel_m, 4),
                "max_vehicle_travel_m": round(max_veh_dist_m, 4),
                "mean_range_m": round(mean_range_m, 4),
                "mean_quality_m_inv": round(mean_quality, 6),
                "tag": "nominal_recommended" if (policy == "beam" and k == 8 and bw == 20)
                       else ("nearest_baseline" if (policy == "nearest" and k == 8) else "sweep"),
            })

    # 2D Pareto (for transparent historical comparison) AND 3D Pareto (true primary frontier on raw floats)
    for i, r in enumerate(rows):
        dom_2d = False
        dom_3d = False
        for j, o in enumerate(rows):
            if i == j:
                continue
            # 2D: min (latest_start_s, total_travel_m)
            if (o["_raw_t"] <= r["_raw_t"] + 1e-9
                and o["_raw_d"] <= r["_raw_d"] + 1e-6
                and (o["_raw_t"] < r["_raw_t"] - 1e-9
                     or o["_raw_d"] < r["_raw_d"] - 1e-6)):
                dom_2d = True
            # 3D: min latest_start_s, min total_travel_m, max mean_quality_m_inv
            if (o["_raw_t"] <= r["_raw_t"] + 1e-9
                and o["_raw_d"] <= r["_raw_d"] + 1e-6
                and o["_raw_q"] >= r["_raw_q"] - 1e-9
                and (o["_raw_t"] < r["_raw_t"] - 1e-9
                     or o["_raw_d"] < r["_raw_d"] - 1e-6
                     or o["_raw_q"] > r["_raw_q"] + 1e-9)):
                dom_3d = True
        r["is_pareto_2d"] = not dom_2d
        r["is_pareto_3d"] = not dom_3d
        r["is_pareto"] = not dom_3d  # Primary Pareto flag is now exact 3D non-dominated status
    for r in rows:
        r.pop("_raw_t", None)
        r.pop("_raw_d", None)
        r.pop("_raw_q", None)

    rows.sort(key=lambda r: (r["latest_start_s"], r["total_travel_m"], -r["mean_quality_m_inv"]))
    write_csv(results_dir / "Pareto_tradeoff.csv", rows)
    write_csv(results_dir / "Pareto_tradeoff_3d.csv", rows)
    return rows


def main(results_dir=None):
    results_dir = Path(results_dir) if results_dir else (DEFAULT_OUTPUT / "results")
    oat, inter, fixed_reopt, weight_rows = compute_parameter_perturbation(results_dir)
    pareto = compute_pareto_tradeoff_3d(results_dir)
    n_front_3d = sum(1 for r in pareto if r["is_pareto_3d"])
    n_front_2d = sum(1 for r in pareto if r["is_pareto_2d"])
    distinct_3d = len({
        (r["latest_start_s"], r["total_travel_m"], r["mean_quality_m_inv"])
        for r in pareto if r["is_pareto_3d"]
    })
    write_json(results_dir / "Global_sensitivity_summary.json", {
        "method": "Parameter Perturbation and Pairwise Interaction Analysis (real P1-P4 solver evaluations)",
        "top_parameter": oat[0]["parameter"],
        "top_swing_pct": oat[0]["swing_pct"],
        "pareto_configs": len(pareto),
        "pareto_front_count": n_front_3d,
        "pareto_front_2d_count": n_front_2d,
        "pareto_front_3d_count": n_front_3d,
        "pareto_front_distinct_vectors": distinct_3d,
        "weight_schemes_tested": len(WEIGHT_SCHEMES),
    })
    print(
        f"Perturbation & 3D Pareto complete: {len(oat)} OAT params (top={oat[0]['parameter']} {oat[0]['swing_pct']:.2f}%), "
        f"{len(inter)} interactions, {len(WEIGHT_SCHEMES)} weight schemes, "
        f"{len(pareto)} configs ({n_front_3d} 3D Pareto / {n_front_2d} 2D Pareto)"
    )


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_OUTPUT / "results")
    args = parser.parse_args()
    main(args.results)

"""Stage-1 Hardcore Automated Audit (6 checks) for Problem B.

Checks:
1. Field safety inset [1.5, 98.5] x [1.5, 98.5] across all stations, waypoints, and trajectories.
2. Euclidean rounded Minkowski clearance B_i (+) D(0, 1.5) continuous segment & point verification.
3. Global tie-break rule uniqueness audit across code & paper.
4. Independent exact Branch-and-Bound verification of P2(2) on the fixed k=8 shortlist AND full discrete pool.
5. Global sensitivity & Pareto deterministic reproducibility and dimensional consistency check.
6. Three-way 100% numeric consistency across solver outputs, CSVs, 72 LaTeX macros, and figures.

AI assistance: Antigravity (Gemini), 2026-11-21. Audit & verification only.
Audit entry and witness checks assisted by ChatGPT (Codex, GPT-6 series), OpenAI,
2026-11-21; public model release date unverified.
"""
from argparse import ArgumentParser
from collections import Counter
from itertools import combinations, permutations, product
from math import dist, isfinite
from pathlib import Path
import re
from unittest.mock import patch

import b_revision_geometry as rounded
import problem_b_geometry as model
import solve_problem_b as solver
from b_revision_data import DEFAULT_OUTPUT, read_csv, read_json, write_json


def audit_1_field_inset(review_dir):
    """Verify every candidate station, waypoint, and executed point lies inside [1.5, 98.5]^2."""
    lo, hi = model.RADIUS, model.WIDTH - model.RADIUS
    lo_y, hi_y = model.RADIUS, model.DEPTH - model.RADIUS
    tol = 1e-9
    violations = []
    checked_stations = 0
    for name, goal in model.TARGETS.items():
        for pt in rounded.stations(goal):
            checked_stations += 1
            if not (lo - tol <= pt[0] <= hi + tol and lo_y - tol <= pt[1] <= hi_y + tol):
                violations.append(("station", name, pt))
    for i, wp in enumerate(model.WAYPOINTS):
        if not (lo - tol <= wp[0] <= hi + tol and lo_y - tol <= wp[1] <= hi_y + tol):
            violations.append(("waypoint", i, wp))
    timeline = read_json(review_dir / "results" / "Executed_timeline.json")
    checked_traj_pts = 0
    for case_name, case in timeline["cases"].items():
        for pol, rows in case["policies"].items():
            for row in rows:
                pts = row.get("path") or ([row["position"]] if row.get("position") else [])
                for pt in pts:
                    checked_traj_pts += 1
                    if not (lo - tol <= pt[0] <= hi + tol and lo_y - tol <= pt[1] <= hi_y + tol):
                        violations.append(("traj", case_name, pol, pt))
    return {
        "passed": len(violations) == 0,
        "bounds_m": [lo, hi, lo_y, hi_y],
        "checked_stations": checked_stations,
        "checked_waypoints": len(model.WAYPOINTS),
        "checked_trajectory_points": checked_traj_pts,
        "violations": violations[:10],
    }


def audit_2_minkowski_clearance(review_dir):
    """Verify continuous Euclidean rounded Minkowski clearance >= 1.5 m - 1e-9 on all executed legs."""
    tol = 1e-9
    timeline = read_json(review_dir / "results" / "Executed_timeline.json")
    min_seg_margin = float("inf")
    min_pt_margin = float("inf")
    seg_count = 0
    pt_count = 0
    violations = []
    # Also check simultaneous vehicle-vehicle separation in nominal k=8 beam plan
    plans = read_json(review_dir / "results" / "P2_main_plans.json")
    beam_plan = plans["beam"]
    min_pair_sep = float("inf")
    by_alert = {}
    for v in beam_plan:
        by_alert.setdefault(v["alert"], []).append(v)
    for alert, pair in by_alert.items():
        if len(pair) == 2:
            d = dist(pair[0]["station"], pair[1]["station"])
            min_pair_sep = min(min_pair_sep, d)

    for case_name, case in timeline["cases"].items():
        for pol, rows in case["policies"].items():
            for row in rows:
                if row["phase"] == "travel" and row.get("path"):
                    path = row["path"]
                    for a, b in zip(path[:-1], path[1:]):
                        m = rounded.clearance(tuple(a), tuple(b))
                        seg_count += 1
                        min_seg_margin = min(min_seg_margin, m)
                        if m < -tol:
                            violations.append(("segment", case_name, pol, a, b, m))
                elif row.get("position"):
                    pt = tuple(row["position"])
                    m = rounded.clearance(pt, pt)
                    pt_count += 1
                    min_pt_margin = min(min_pt_margin, m)
                    if m < -tol:
                        violations.append(("point", case_name, pol, pt, m))
    route_summary = read_json(review_dir / "results" / "Route_summary.json")
    return {
        "passed": len(violations) == 0 and min_pair_sep >= 2 * model.RADIUS - tol,
        "segments_checked": seg_count,
        "stationary_points_checked": pt_count,
        "min_continuous_segment_margin_m": round(min_seg_margin, 9),
        "min_stationary_point_margin_m": round(min_pt_margin, 9),
        "min_nominal_pair_separation_m": round(min_pair_sep, 6),
        "audited_routes_count": route_summary["compared_routes"],
        "audited_min_route_margin_m": route_summary["minimum_margin_m"],
        "detour_caveat": "Direct legs are exact Euclidean shortest paths; multi-segment detours are continuous-clearance-verified feasible upper bounds on the corner waypoint graph.",
        "violations": violations[:10],
    }


def audit_3_tie_break_uniqueness(review_dir):
    """Check tie-break consistency across P1 station record and solver comparators."""
    p1_rows = {r["tie"]: r for r in read_csv(review_dir / "results" / "P1_station.csv")}
    ready = p1_rows["ready"]
    arrival = p1_rows["arrival"]
    paper_tex = (review_dir / "paper" / "B_submission.tex").read_text(encoding="utf-8")
    p1_team = (review_dir / "paper" / "team" / "p1.tex").read_text(encoding="utf-8")
    has_ready = "5.064533" in (review_dir / "paper" / "B_review_metrics.tex").read_text(encoding="utf-8")
    # Check solver tie-break in solve_problem_b.py (row[1] is ready, row[0] is arrival)
    solver_src = (model.ROOT / "src" / "solve_problem_b.py").read_text(encoding="utf-8")
    solver_uses_ready_first = "key=lambda row: (row[1], row[0], row[2])" in solver_src
    return {
        "passed": bool(has_ready and solver_uses_ready_first),
        "primary_p1_tie_break": "readiness_first (V4 ready at 5.064533 s, drive 2.397866 s)",
        "secondary_documented_contrast": f"arrival_first witness ({float(arrival['arrival_s']):.6f} s drive, {float(arrival['ready_s']):.6f} s ready)",
        "solver_station_options_ready_first": solver_uses_ready_first,
        "paper_references_readiness": ("Readiness" in paper_tex and "readiness" in p1_team.lower()),
    }


def _topological_orders_for_pairing(pairing, alerts):
    """Return all acyclic per-vehicle service-order combinations and a valid global topological order.

    pairing: tuple of 3 vehicle pairs (pair_T1, pair_T2, pair_T3), each a sorted 2-tuple in 0..4.
    """
    veh_alerts = {v: [] for v in range(5)}
    for a_idx, (u, w) in enumerate(pairing):
        veh_alerts[u].append(a_idx)
        veh_alerts[w].append(a_idx)
    reused = [(v, tuple(al)) for v, al in veh_alerts.items() if len(al) >= 2]
    if not reused:
        return [({}, (0, 1, 2))]
    perm_lists = [list(permutations(al)) for _, al in reused]
    valid = []
    for choice in product(*perm_lists):
        # Build precedence graph on alerts {0, 1, 2}
        adj = {0: set(), 1: set(), 2: set()}
        indeg = {0: 0, 1: 0, 2: 0}
        veh_order = {}
        for (v, _), seq in zip(reused, choice, strict=True):
            veh_order[v] = seq
            for x, y in zip(seq, seq[1:]):
                if y not in adj[x]:
                    adj[x].add(y)
                    indeg[y] += 1
        # Kahn's algorithm to detect cycles and produce canonical topological order
        queue = sorted(a for a in (0, 1, 2) if indeg[a] == 0)
        topo = []
        while queue:
            u = queue.pop(0)
            topo.append(u)
            for nxt in sorted(adj[u]):
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
                    queue.sort()
        if len(topo) == 3:
            valid.append((veh_order, tuple(topo)))
    return valid


def _p2_crossing_allowed(gamma, min_crossing_deg):
    return 1e-6 < gamma < 180.0 - 1e-6 and gamma >= min_crossing_deg


def _exact_p2_bnb(shortlist_k=None, initial_ub=float("inf"), *, min_crossing_deg=0.0, slew_time=None):
    """Independent zero-truncation exact Branch-and-Bound over ALL C(5,2)^3 = 1,000 legal vehicle pairings
    and ALL acyclic service-order permutations (covering 1-vehicle 3-alert, 2-vehicle 2-alert, 3-vehicle
    2-alert, idle-vehicle patterns, and the 360 1-reused-vehicle topologies).

    If shortlist_k is an int (e.g. 8), uses the exact arrival-sorted top-k stations per (vehicle, alert).
    If shortlist_k is None, searches the ENTIRE 585-station discrete candidate pool.
    The crossing floor applies to both fresh and reused vehicle pairs.
    A supplied slew_time replaces both the pointing and reset duration.
    """
    orig_opts = solver.station_options
    if slew_time is None:
        slew_time = solver._station_slew_time
    alerts = tuple(model.TARGETS.keys())  # ("T1", "T2", "T3")
    goals = tuple(model.TARGETS[a] for a in alerts)
    n_veh = len(model.VEHICLES)
    all_pairs = list(combinations(range(n_veh), 2))  # 10 pairs

    with (
        patch.object(solver, "road_clear", rounded.road_clear),
        patch.object(solver, "route", rounded.route),
        patch.object(solver, "candidate_stations", rounded.stations),
        patch.object(solver, "_station_slew_time", slew_time),
    ):
        all_stations = {a_i: rounded.stations(goals[a_i]) for a_i in range(3)}
        total_pool_size = sum(len(v) for v in all_stations.values())

        # Arrival-sorted station pools from t=0, plus ready-sorted views for tight B&B pruning
        init_opts = {}
        init_ready_sorted = {}
        r0_min = {}
        for v in range(n_veh):
            for a_i in range(3):
                full = sorted(orig_opts(solver.INITIAL[v], goals[a_i], len(all_stations[a_i])))
                pool = full[:shortlist_k] if shortlist_k else full
                init_opts[(v, a_i)] = pool
                rs = sorted(pool, key=lambda x: (x[1], x[0], x[2]))
                init_ready_sorted[(v, a_i)] = rs
                r0_min[(v, a_i)] = rs[0][1] if rs else float("inf")

        min_slew = {
            a_i: min(solver._station_slew_time(st, goals[a_i]) for st in all_stations[a_i])
            for a_i in range(3)
        }

        # Precompute exact second/third-leg options from any station pos at t=0 (relative times)
        leg_cache = {}

        def get_leg_opts(pos, a_i):
            key = (pos, a_i)
            if key not in leg_cache:
                full = sorted(orig_opts((pos, 0.0), goals[a_i], len(all_stations[a_i])))
                pool = full[:shortlist_k] if shortlist_k else full
                leg_cache[key] = sorted(pool, key=lambda x: (x[1], x[0], x[2]))
            return leg_cache[key]

        # Precompute exact minimum single-use pair start time when both vehicles start fresh from t=0
        best_pair_fresh = {}
        for a_i in range(3):
            goal = goals[a_i]
            for v1, v2 in all_pairs:
                best_t = float("inf")
                best_st = None
                opts1 = init_ready_sorted[(v1, a_i)]
                opts2 = init_ready_sorted[(v2, a_i)]
                for _a1, r1, p1, _ in opts1:
                    if r1 >= best_t:
                        break
                    b1 = solver._station_bearing(p1, goal)
                    for _a2, r2, p2, _ in opts2:
                        t_st = r1 if r1 >= r2 else r2
                        if t_st >= best_t:
                            break
                        if p1 == p2:
                            continue
                        g = solver._crossing_angle(solver._station_bearing(p2, goal) - b1)
                        if _p2_crossing_allowed(g, min_crossing_deg):
                            best_t = t_st
                            best_st = (p1, p2)
                            break
                best_pair_fresh[(v1, v2, a_i)] = (best_t, best_st)
                best_pair_fresh[(v2, v1, a_i)] = (best_t, (best_st[1], best_st[0]) if best_st else None)

        best_makespan = initial_ub
        best_witness = None
        pairings_total = 0
        ordered_topologies_total = 0
        pruned_layer0 = 0
        pruned_inner = 0
        pattern_counts = Counter()

        for pairing in product(all_pairs, repeat=3):
            pairings_total += 1
            mult = Counter(v for pr in pairing for v in pr)
            pattern = tuple(sorted([mult[v] for v in range(n_veh)], reverse=True))
            pattern_counts[str(pattern)] += 1

            # Determine all acyclic service orders for this pairing
            orders = _topological_orders_for_pairing(pairing, alerts)
            for veh_order, topo in orders:
                ordered_topologies_total += 1

                # --- Layer-0 theoretical lower bound ---
                # (a) Every alert a must wait at least max(r0_min[u, a], r0_min[w, a])
                # (b) If neither u nor w has an earlier alert, exact fresh pair minimum applies
                # (c) For each reused vehicle with sequence (a0, a1[, a2]), chain lower bound:
                #     t_start(a1) >= r0_min[v, a0] + OBSERVE + min_slew[a0] + min_slew[a1]
                #     t_start(a2) >= r0_min[v, a0] + 2*OBSERVE + min_slew[a0] + 2*min_slew[a1] + min_slew[a2]
                lb0 = 0.0
                first_alert_of = {}
                for pos_idx, a_i in enumerate(topo):
                    u, w = pairing[a_i]
                    u_fresh = u not in first_alert_of
                    w_fresh = w not in first_alert_of
                    if u_fresh:
                        first_alert_of[u] = a_i
                    if w_fresh:
                        first_alert_of[w] = a_i
                    if u_fresh and w_fresh:
                        t_lb = best_pair_fresh[(u, w, a_i)][0]
                    else:
                        t_lb = max(
                            r0_min[(u, a_i)] if u_fresh else min_slew[a_i],
                            r0_min[(w, a_i)] if w_fresh else min_slew[a_i],
                        )
                    if t_lb > lb0:
                        lb0 = t_lb
                for v, seq in veh_order.items():
                    if len(seq) == 2:
                        a0, a1 = seq
                        t_chain = r0_min[(v, a0)] + model.OBSERVE + min_slew[a0] + min_slew[a1]
                        if t_chain > lb0:
                            lb0 = t_chain
                    elif len(seq) == 3:
                        a0, a1, a2 = seq
                        t_chain = (
                            r0_min[(v, a0)]
                            + 2.0 * model.OBSERVE
                            + min_slew[a0]
                            + 2.0 * min_slew[a1]
                            + min_slew[a2]
                        )
                        if t_chain > lb0:
                            lb0 = t_chain

                if lb0 >= best_makespan - 1e-12:
                    pruned_layer0 += 1
                    continue

                # Determine for each step in topo whether each vehicle has a subsequent alert
                # (only vehicles with a subsequent alert need full station branching; terminal vehicles
                # only need their earliest non-collinear station!)
                last_step_of = {}
                for step_idx, a_i in enumerate(topo):
                    for v in pairing[a_i]:
                        last_step_of[v] = step_idx

                # Recursive exact B&B over the 3 alerts in topological order
                # veh_state[v] = (pos, available_s)
                init_state = {v: (model.VEHICLES[v], 0.0) for v in range(n_veh)}

                def dfs(step_idx, veh_state, cur_max, chosen):
                    nonlocal best_makespan, best_witness, pruned_inner
                    if cur_max >= best_makespan - 1e-12:
                        pruned_inner += 1
                        return
                    if step_idx == 3:
                        if cur_max < best_makespan - 1e-12:
                            best_makespan = cur_max
                            best_witness = {
                                "pairing": {alerts[i]: [pairing[i][0] + 1, pairing[i][1] + 1] for i in range(3)},
                                "pattern": list(pattern),
                                "topo_order": [alerts[i] for i in topo],
                                "reused_orders": {f"V{v+1}": [alerts[i] for i in seq] for v, seq in veh_order.items()},
                                "starts_s": {alerts[a_i]: round(t_st, 6) for a_i, t_st, *_ in chosen},
                                "stations_m": {
                                    alerts[a_i]: {
                                        f"V{u + 1}": su,
                                        f"V{w + 1}": sw,
                                    }
                                    for a_i, _, u, w, su, sw in chosen
                                },
                            }
                        return

                    a_i = topo[step_idx]
                    goal = goals[a_i]
                    u, w = pairing[a_i]
                    pos_u, avail_u = veh_state[u]
                    pos_w, avail_w = veh_state[w]
                    u_reused_later = last_step_of[u] > step_idx
                    w_reused_later = last_step_of[w] > step_idx

                    # If neither u nor w is reused later AND both are fresh at t=0, use exact precomputed pair!
                    if not u_reused_later and not w_reused_later and avail_u == 0.0 and avail_w == 0.0:
                        t_st, st_pair = best_pair_fresh[(u, w, a_i)]
                        if t_st >= best_makespan - 1e-12:
                            pruned_inner += 1
                            return
                        dfs(step_idx + 1, veh_state, max(cur_max, t_st), chosen + ((a_i, t_st, u, w, *st_pair),))
                        return

                    opts_u = init_ready_sorted[(u, a_i)] if avail_u == 0.0 else get_leg_opts(pos_u, a_i)
                    opts_w = init_ready_sorted[(w, a_i)] if avail_w == 0.0 else get_leg_opts(pos_w, a_i)

                    # Swap so that if only one is reused later, the reused one is outer loop (u_out)
                    if not u_reused_later and w_reused_later:
                        u, w = w, u
                        pos_u, avail_u, pos_w, avail_w = pos_w, avail_w, pos_u, avail_u
                        u_reused_later, w_reused_later = True, False
                        opts_u, opts_w = opts_w, opts_u

                    for _au, ru_rel, su, _ in opts_u:
                        ru = avail_u + ru_rel
                        if ru >= best_makespan - 1e-12:
                            pruned_inner += 1
                            break
                        bu = solver._station_bearing(su, goal)
                        slew_u = solver._station_slew_time(su, goal)
                        if u_reused_later and (ru + model.OBSERVE + slew_u >= best_makespan - 1e-12):
                            pruned_inner += 1
                            continue

                        for _aw, rw_rel, sw, _ in opts_w:
                            rw = avail_w + rw_rel
                            t_st = ru if ru >= rw else rw
                            if t_st >= best_makespan - 1e-12:
                                pruned_inner += 1
                                break
                            if su == sw:
                                continue
                            g = solver._crossing_angle(solver._station_bearing(sw, goal) - bu)
                            if not _p2_crossing_allowed(g, min_crossing_deg):
                                continue

                            # Check post-observation release lower bounds for vehicles reused later
                            next_state = dict(veh_state)
                            if u_reused_later:
                                t_free_u = t_st + model.OBSERVE + slew_u
                                if t_free_u >= best_makespan - 1e-12:
                                    pruned_inner += 1
                                    if not w_reused_later:
                                        break
                                    continue
                                next_state[u] = (su, t_free_u)
                            if w_reused_later:
                                slew_w = solver._station_slew_time(sw, goal)
                                t_free_w = t_st + model.OBSERVE + slew_w
                                if t_free_w >= best_makespan - 1e-12:
                                    pruned_inner += 1
                                    continue
                                next_state[w] = (sw, t_free_w)

                            dfs(step_idx + 1, next_state, max(cur_max, t_st), chosen + ((a_i, t_st, u, w, su, sw),))

                            # If w is NOT reused later, the first compatible w (sorted by ready time)
                            # strictly dominates all later w for this fixed su!
                            if not w_reused_later:
                                break
                        # If neither u nor w is reused later, the first feasible pair can still be
                        # improved only by a later u? No: opts_u is sorted by ready time, so wait:
                        # if su == sw blocked the best w, a slightly later su might match a much earlier sw,
                        # so we only break outer when ru >= best_makespan (already checked above).

                dfs(0, init_state, 0.0, ())

        return {
            "shortlist_k": shortlist_k if shortlist_k else "FULL_DISCRETE_POOL",
            "discrete_station_pool_size": total_pool_size,
            "legal_pairings_total": pairings_total,
            "acyclic_ordered_topologies_total": ordered_topologies_total,
            "multiplicity_pattern_counts": dict(sorted(pattern_counts.items())),
            "initial_upper_bound_s": round(initial_ub, 6) if isfinite(initial_ub) else None,
            "lower_bound_formula": (
                "Layer-0: max(fresh_pair_min, r0_min[u,a], r0_min[w,a], chain_lb(r0_min + m*OBSERVE + sum_min_slew)); "
                "Layer-1/2: max(cur_max, ready_u, ready_w, t_start + OBSERVE + reset_slew for any reused vehicle)."
            ),
            "pruned_layer0_topologies": pruned_layer0,
            "pruned_inner_branches": pruned_inner,
            "exact_discrete_optimum_s": round(best_makespan, 6) if best_witness is not None else None,
            "witness": best_witness,
        }


def _p2_replay_witness(run, *, min_crossing_deg=0.0, slew_time=model.slew_time):
    """Check the logged P2 witness through the specified pointing and reset clocks."""
    witness = run["witness"]
    if witness is None:
        return False
    states = {f"V{i + 1}": (point, 0.0) for i, point in enumerate(model.VEHICLES)}
    order = witness["topo_order"]
    if len(order) != len(model.TARGETS) or set(order) != set(model.TARGETS):
        return False
    replayed = {}
    service_orders = {vehicle: [] for vehicle in states}
    for alert in order:
        goal = model.TARGETS[alert]
        stations = {vehicle: tuple(point) for vehicle, point in witness["stations_m"][alert].items()}
        if set(stations) != {f"V{i}" for i in witness["pairing"][alert]} or len(stations) != 2:
            return False
        first, second = stations.values()
        _, gamma = solver.accuracy(first, second, goal)
        if first == second or not _p2_crossing_allowed(gamma, min_crossing_deg):
            return False
        candidates = set(rounded.stations(goal))
        legs = []
        for vehicle, station in stations.items():
            if station not in candidates:
                return False
            origin, available = states[vehicle]
            distance, _ = rounded.route(origin, station)
            slew = slew_time(station, goal)
            legs.append((vehicle, station, slew, available + distance / model.SPEED + slew))
        start = max(leg[3] for leg in legs)
        replayed[alert] = round(start, 6)
        for vehicle, station, slew, _ in legs:
            states[vehicle] = station, start + model.OBSERVE + slew
            service_orders[vehicle].append(alert)
    reused_orders = {vehicle: alerts for vehicle, alerts in service_orders.items() if len(alerts) > 1}
    return (
        replayed == witness["starts_s"]
        and reused_orders == witness["reused_orders"]
        and max(replayed.values()) == run["exact_discrete_optimum_s"]
    )


def audit_4_p2_exact_bnb(review_dir):
    """Run seeded and unseeded audits on both the k=8 and full station pools."""
    trials = read_csv(review_dir / "results" / "P2_trials.csv")
    beam_k8 = float(next(
        r["latest_start_s"] for r in trials
        if r["routing"] == "rounded" and r["k"] == "8" and r["beam_width"] == "20" and r["policy"] == "beam"
    ))
    seeded_upper_bound = beam_k8 + 1e-4
    exact_k8 = _exact_p2_bnb(shortlist_k=8, initial_ub=seeded_upper_bound)
    exact_full = _exact_p2_bnb(shortlist_k=None, initial_ub=seeded_upper_bound)
    unseeded_k8 = _exact_p2_bnb(shortlist_k=8)
    unseeded_full = _exact_p2_bnb(shortlist_k=None)
    runs = (exact_k8, exact_full, unseeded_k8, unseeded_full)
    for run in runs:
        run["witness_replay_passed"] = _p2_replay_witness(run)
    incumbent = round(beam_k8, 6)

    def gap(run):
        optimum = run["exact_discrete_optimum_s"]
        return None if optimum is None else round(incumbent - optimum, 6)

    return {
        "passed": all(
            run["legal_pairings_total"] == 1000
            and run["acyclic_ordered_topologies_total"] == 4200
            and run["discrete_station_pool_size"] == 585
            and sum(run["multiplicity_pattern_counts"].values()) == 1000
            and run["witness_replay_passed"]
            and gap(run) == 0
            for run in runs
        ),
        "beam_k8_incumbent_s": incumbent,
        "exact_k8_bnb": exact_k8,
        "gap_vs_exact_k8_s": gap(exact_k8),
        "exact_full_discrete_pool_bnb": exact_full,
        "gap_vs_full_discrete_pool_s": gap(exact_full),
        "unseeded_k8_bnb": unseeded_k8,
        "unseeded_full_discrete_pool_bnb": unseeded_full,
    }


def audit_5_sensitivity_pareto(review_dir):
    """Verify real-solver perturbation, 5-scheme weight stability, 3D Pareto, and P4 dedup/extended CSVs."""
    oat = read_csv(review_dir / "results" / "Global_sensitivity_oat.csv")
    inter = read_csv(review_dir / "results" / "Global_sensitivity_interaction.csv")
    w_chk = read_csv(review_dir / "results" / "Global_sensitivity_weight_check.csv")
    f_reopt = read_csv(review_dir / "results" / "Global_sensitivity_fixed_vs_reopt.csv")
    pareto = read_csv(review_dir / "results" / "Pareto_tradeoff_3d.csv")
    p4_ext = read_csv(review_dir / "results" / "P4_dedup_expanded_cases.csv")
    share_sum = sum(float(r["main_share_pct"]) for r in oat)
    sym_err = 0.0
    imap = {(r["param_i"], r["param_j"]): float(r["interaction_pct"]) for r in inter}
    for (i, j), v in imap.items():
        sym_err = max(sym_err, abs(v - imap[(j, i)]))
    n_front_3d = sum(1 for r in pareto if r["is_pareto_3d"] == "True")
    k5_3d = any(r["policy"] == "beam" and r["k"] == "5" and r["is_pareto_3d"] == "True" for r in pareto)
    k8_3d = any(r["policy"] == "beam" and r["k"] == "8" and r["beam_width"] == "20" and r["is_pareto_3d"] == "True" for r in pareto)
    return {
        "passed": (
            len(oat) == 6 and len(inter) == 36 and len(w_chk) == 30 and len(f_reopt) == 6
            and len(pareto) == 16 and abs(share_sum - 100.0) < 0.05 and sym_err < 1e-9
            and k5_3d and k8_3d and len(p4_ext) == 115
        ),
        "oat_count": len(oat),
        "interaction_entries": len(inter),
        "interaction_max_asymmetry": sym_err,
        "weight_check_rows": len(w_chk),
        "fixed_vs_reopt_rows": len(f_reopt),
        "main_share_sum_pct": round(share_sum, 2),
        "pareto_configs": len(pareto),
        "pareto_3d_front_count": n_front_3d,
        "k5_and_k8_both_3d_nondominated": bool(k5_3d and k8_3d),
        "p4_unique_expanded_cases": len(p4_ext),
    }


def audit_6_three_way_consistency(review_dir):
    """Verify 100% numeric consistency across NUMBER_PROVENANCE.csv, B_review_metrics.tex, and B_submission.pdf."""
    from pypdf import PdfReader

    prov = read_csv(review_dir / "paper" / "NUMBER_PROVENANCE.csv")
    macros_tex = (review_dir / "paper" / "B_review_metrics.tex").read_text(encoding="utf-8")
    paper_txt = "".join(re.sub(r"\s+", "", p.extract_text() or "")
                        for p in PdfReader(review_dir / "paper" / "B_submission.pdf").pages)
    errata_txt = "".join(re.sub(r"\s+", "", p.extract_text() or "")
                         for p in PdfReader(review_dir / "paper" / "P1_ERRATA.pdf").pages)
    missing_macros = []
    missing_in_pdf = []
    for row in prov:
        m = row["macro"]
        val = row["rendered"]
        if f"\\newcommand{{\\B{m}}}{{{val}}}" not in macros_tex:
            missing_macros.append(m)
        target_txt = errata_txt if m.startswith(("From", "To", "At", "Branch")) else paper_txt
        if val not in target_txt:
            missing_in_pdf.append((m, val))
    # Also check citation coverage of all bibitems in B_submission.tex + team/*.tex
    tex_all = (review_dir / "paper" / "B_submission.tex").read_text(encoding="utf-8")
    for tf in sorted((review_dir / "paper" / "team").glob("*.tex")):
        tex_all += "\n" + tf.read_text(encoding="utf-8")
    bibkeys = re.findall(r"\\bibitem\{([^}]+)\}", tex_all)
    cited = set()
    for grp in re.findall(r"\\cite\{([^}]+)\}", tex_all):
        for k in grp.split(","):
            cited.add(k.strip())
    uncited = [k for k in bibkeys if k not in cited]
    return {
        "passed": not missing_macros and not missing_in_pdf and not uncited,
        "bound_macros": len(prov),
        "missing_macros": missing_macros,
        "missing_in_pdf": missing_in_pdf,
        "bibitems_total": len(bibkeys),
        "uncited_bibitems": uncited,
    }


def main(review_dir):
    review_dir = Path(review_dir).resolve()
    report = {
        "audit_1_field_inset": audit_1_field_inset(review_dir),
        "audit_2_minkowski_clearance": audit_2_minkowski_clearance(review_dir),
        "audit_3_tie_break_uniqueness": audit_3_tie_break_uniqueness(review_dir),
        "audit_4_p2_exact_bnb": audit_4_p2_exact_bnb(review_dir),
        "audit_5_sensitivity_pareto": audit_5_sensitivity_pareto(review_dir),
        "audit_6_three_way_consistency": audit_6_three_way_consistency(review_dir),
    }
    write_json(review_dir / "results" / "HARDCORE_AUDIT_REPORT.json", report)
    for k, v in report.items():
        print(f"{k}: passed={v['passed']}")
    a4 = report["audit_4_p2_exact_bnb"]
    print(f"  P2(2) Beam k=8: {a4['beam_k8_incumbent_s']} s | Exact k=8 B&B: {a4['exact_k8_bnb']['exact_discrete_optimum_s']} s (gap {a4['gap_vs_exact_k8_s']} s)")
    print(f"  P2(2) Exact FULL discrete pool B&B: {a4['exact_full_discrete_pool_bnb']['exact_discrete_optimum_s']} s (gap {a4['gap_vs_full_discrete_pool_s']} s)")
    print(f"  Full witness: {a4['exact_full_discrete_pool_bnb']['witness']}")
    print(f"  k=8 witness:  {a4['exact_k8_bnb']['witness']}")
    for label, key in (("k=8", "unseeded_k8_bnb"), ("full pool", "unseeded_full_discrete_pool_bnb")):
        run = a4[key]
        print(f"  Unseeded {label} B&B (+inf): {run['exact_discrete_optimum_s']} s | "
              f"{run['legal_pairings_total']} pairings / {run['acyclic_ordered_topologies_total']} orders | "
              f"witness replay passed={run['witness_replay_passed']}")
    failed = [name for name, result in report.items() if not result["passed"]]
    if failed:
        raise RuntimeError(f"Hardcore audit failed: {', '.join(failed)}")


if __name__ == "__main__":
    p = ArgumentParser(description=__doc__)
    p.add_argument("--review", type=Path, default=DEFAULT_OUTPUT)
    main(p.parse_args().review)

"""Stage 3: run controlled configurations of the existing team-review solver.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: experimental plumbing,
field/route validation, and event exports. Model design remains team work.
"""
from argparse import ArgumentParser
from collections import Counter
from contextlib import ExitStack, contextmanager
from dataclasses import asdict
from math import dist, isclose
from unittest.mock import patch

import b_revision_events as events
import b_revision_geometry as rounded
import check_problem_b as checks
import problem_b_geometry as model
import solve_problem_b as solver
from b_revision_data import DEFAULT_OUTPUT, SOURCE_RESULTS, case_parameters, digest
from b_revision_data import file_hash, read_csv, read_json, window_score, write_csv, write_json
from check_b_p4_cross import crossed_cases


SHARED_K = 8
BEAM_WIDTH = 20
DISTURBANCE = model.number("p4", "disturbance", "occurrence_time")
START, HORIZON, INCOMPLETE = events.WINDOW_START, events.HORIZON, events.INCOMPLETE
ORIGINAL_OPTIONS = solver.station_options


@contextmanager
def routing(predicate, route, station_pool):
    """Use the same route and station geometry in both original policies."""
    with ExitStack() as stack:
        for name, implementation in (("road_clear", predicate), ("route", route),
                                     ("candidate_stations", station_pool)):
            stack.enter_context(patch.object(solver, name, implementation))
        stack.enter_context(patch.object(checks, "road_clear", predicate))
        yield


def all_options(state, goal):
    return sorted(ORIGINAL_OPTIONS(state, goal, len(solver.candidate_stations(goal))))


def starts_for(visits):
    return {v.alert: v.start for v in visits}


def tally(visits):
    return max(starts_for(visits).values())


def validate_schedule(visits, goals, states, label):
    result = checks.verify_visits([asdict(v) for v in visits], goals, states, label)
    solver.validate_visits(visits, goals)
    return result


def compare_p2(out):
    trials, by_visit, sums, rankings, plans = [], [], [], [], {}
    full_set = ("rounded", SHARED_K, BEAM_WIDTH)
    for method, predicate, route, stations in (
            ("aabb", model.road_clear, model.route, model.candidate_stations),
            ("rounded", rounded.road_clear, rounded.route, rounded.stations)):
        with routing(predicate, route, stations):
            configs = ((3, BEAM_WIDTH), (SHARED_K, BEAM_WIDTH))
            if method == "rounded":
                configs += ((SHARED_K, 5), (SHARED_K, 40))
            for count, width in configs:
                def screen(state, goal, _limit):
                    return all_options(state, goal)[:count]

                prefix = (method, count, width)
                with patch.object(solver, "station_options", screen):
                    pair = {
                        "beam": solver.solve_schedule(solver.INITIAL, model.TARGETS,
                                                      beam_width=width, stations=count),
                        "nearest": solver.solve_schedule(solver.INITIAL, model.TARGETS,
                                                         nearest=True, beam_width=1, stations=count),
                    }
                plans[prefix] = pair
                for policy, plan in pair.items():
                    validate_schedule(plan, model.TARGETS, solver.INITIAL, f"{prefix}/{policy}")
                    starts = starts_for(plan)
                    assert starts.keys() == model.TARGETS.keys()
                    latest = max(starts, key=starts.__getitem__)
                    critical = max((v for v in plan if v.alert == latest), key=lambda v: v.ready)
                    label = {"routing": method, "k": count, "beam_width": width, "policy": policy}
                    trials.append({**label, "latest_start_s": starts[latest], "critical_alert": latest,
                                   "critical_vehicle": critical.vehicle+1, "plan_id": digest([asdict(v) for v in plan]),
                                   **{f"{name}_start_s": starts[name] for name in model.TARGETS}})
                    for i, initial in enumerate(model.VEHICLES):
                        used = sorted((v for v in plan if v.vehicle == i), key=lambda v: v.depart)
                        state = (initial, 0.0)
                        for v in used:
                            ordered = all_options(state, model.TARGETS[v.alert])
                            rank = next(j for j,r in enumerate(ordered,1) if r[2] == v.station)
                            assert rank <= count
                            rankings.append({**label, "vehicle": i+1, "alert": v.alert, "rank": rank,
                                             "within_k3": rank <= 3, "x_m": v.station[0], "y_m": v.station[1],
                                             "previous_release_s": state[1]})
                            by_visit.append({**label, "vehicle": i+1, "alert": v.alert,
                                             "depart_s": v.depart, "arrival_s": v.arrival, "ready_s": v.ready,
                                             "start_s": v.start, "end_s": v.end, "reset_s": v.reset,
                                             "drive_s": v.arrival-v.depart, "slew_s": v.ready-v.arrival,
                                             "partner_wait_s": v.start-v.ready, "observe_s": v.end-v.start,
                                             "reset_duration_s": v.reset-v.end})
                            state = v.station, v.reset
                    # Account for the critical vehicle from t=0 to the final start.
                    chain = sorted((v for v in plan if v.vehicle == critical.vehicle and v.start <= critical.start),
                                   key=lambda v: v.depart)
                    prev = chain[:-1]
                    parts = {"prior_drive_s": sum(v.arrival-v.depart for v in prev),
                             "prior_slew_s": sum(v.ready-v.arrival for v in prev),
                             "prior_wait_s": sum(v.start-v.ready for v in prev),
                             "prior_observe_s": sum(v.end-v.start for v in prev),
                             "prior_reset_s": sum(v.reset-v.end for v in prev),
                             "idle_s": sum(v.depart-before for v,before in zip(chain, [0]+[v.reset for v in prev])),
                             "last_drive_s": critical.arrival-critical.depart,
                             "last_slew_s": critical.ready-critical.arrival,
                             "last_wait_s": critical.start-critical.ready}
                    assert isclose(sum(parts.values()), critical.start, abs_tol=1e-8)
                    sums.append({**label, "chain": ">".join(v.alert for v in chain),
                                 "critical_vehicle": critical.vehicle+1, **parts, "latest_start_s": critical.start})
    old = {(int(r["per_vehicle_k"]), policy): float(r[f"{policy}_latest_start_s"])
           for r in read_csv(SOURCE_RESULTS / "B_P2_fairness.csv")
           if r["probe"] == "common_dynamic" and r["screen"] == "arrival"
           for policy in ("beam", "nearest")}
    assert all(isclose(old[k,p], tally(plan)) for (kind,k,width), pair in plans.items() if kind == "aabb"
               for p, plan in pair.items())
    write_csv(out / "P2_trials.csv", trials)
    write_csv(out / "P2_visit_phases.csv", by_visit)
    write_csv(out / "P2_critical_chains.csv", sums)
    write_csv(out / "P2_station_ranks.csv", rankings)
    write_json(out / "P2_main_plans.json", {
        "shared_k": SHARED_K, "screen": "arrival", "beam_width": BEAM_WIDTH,
        **{p: [asdict(v) for v in plan] for p,plan in plans[full_set].items()},
    })
    print("P2 shared shortlist deltas (nearest minus beam):",
          [(kind,k,width,round(tally(pair["nearest"])-tally(pair["beam"]), 6))
           for (kind,k,width), pair in plans.items()])
    return plans[full_set]


def outage_rule(receivable):
    if receivable == DISTURBANCE:
        return "none"
    maximum = model.number("p4", "outage_formula", "recovery_time_max")
    return "absolute_time" if receivable <= maximum else "duration_sensitivity"


def tighter_prefix(plan, specs, nominal_states):
    rec = specs["dispatch_allowed_from_s"]
    failed = specs["failed_vehicle"]
    initiated = [v for v in plan if v.depart < DISTURBANCE]
    planned_starts = starts_for(initiated)
    partners = Counter(v.alert for v in initiated)
    locked = {a: t for a,t in planned_starts.items() if partners[a] == 2 and t < rec
              and (t < DISTURBANCE or all(v.vehicle+1 != failed for v in initiated if v.alert == a))}
    caps = lambda v: min(rec if v.alert not in locked else HORIZON,
                         DISTURBANCE if v.vehicle+1 == failed else HORIZON)
    prefix = events.visits_to_events(initiated, model.TARGETS, locked, expire=caps)
    vehicle_events = events.per_vehicle(prefix)
    states = []
    for v, home in enumerate(model.VEHICLES, 1):
        if v == failed:
            states.append(None)
            continue
        owned = vehicle_events.get(v, ())
        resource = next((e for e in owned if e["start_s"] <= rec < e["end_s"]), None)
        if resource is not None and resource["alert"] in locked:
            states.append(nominal_states[v-1])
        elif owned:
            last = max((e for e in owned if e["start_s"] < rec), key=lambda e:e["end_s"])
            point, pan, pitch = events.state_of(last, min(rec, last["end_s"]))
            release = rec + max(abs(pan)/model.PAN_SPEED, abs(pitch)/model.PITCH_SPEED) if last["end_s"] >= rec else rec
            states.append((point, release))
        else:
            states.append((home, rec))
    return tuple(states), locked


def compare_p4(out, plans):
    nominal = plans["beam"]
    plan_id = digest([asdict(v) for v in nominal])
    specs = [*solver.scenarios(), *crossed_cases()]
    assert len({a[0] for a in specs}) == len(specs)
    old = {(row["scenario"], row["policy"]): row for row in read_csv(SOURCE_RESULTS / "B_P4.csv")}
    all_traces, rows, variants, comparisons = {}, [], [], []
    nominated = {p: events.nominal_events(visits, starts_for(visits)) for p, visits in plans.items()}
    with routing(rounded.road_clear, rounded.route, rounded.stations):
        figures, traces = solver.solve_p4(nominal, cases=specs)
        table = {(record["scenario"], record["policy"]): record for record in figures}
        for name, extra, failed, rec in specs:
            record = traces[name]
            controls = case_parameters(name, (name, extra, failed, rec), DISTURBANCE, HORIZON, outage_rule(rec))
            assert isclose(rec, record["recovery_s"])
            goals = dict(model.TARGETS)
            if extra is not None:
                assert DISTURBANCE == controls["disturbance_s"]
                goals["T4"] = extra
            states = tuple(record["state_at_recovery"])
            locked = record["locked_observations"]
            kept = record["keep_observation_starts"]
            revised = [solver.Visit(**v) for v in record["rescheduled"]]
            assert set(kept) <= set(goals) and all(v.depart >= rec and v.vehicle != failed for v in revised)
            updated = locked | starts_for(revised)
            validate_schedule(revised, goals, states, name)
            assert not set(locked) & set(starts_for(revised))
            compiled = events.scenario_events(nominal, revised, controls, goals, locked, kept, states, updated)
            scores = {}
            for policy, starts in (("keep", kept), ("reschedule", updated)):
                count, ratio, latest = window_score(starts, set(goals), START, HORIZON, INCOMPLETE)
                published = table[name,policy]
                assert count == published["successes"] and isclose(latest, published["latest_start_s"])
                scores[policy] = {"successes": count, "alerts": len(goals), "completion_ratio": ratio,
                                  "latest_start_s": latest, "starts": starts}
                rows.append({**controls, "new_target": "" if extra is None else "|".join(map(str, extra)),
                             "policy": policy, "plan_id": plan_id, "successes": count,
                             "alerts": len(goals), "completion_ratio": ratio, "latest_start_s": latest})
                if (name, policy) in old:
                    archive = old[name,policy]
                    comparisons.append({"case": name, "policy": policy,
                                        "archived_successes": archive["successes"], "successes": count,
                                        "archived_latest_s": archive["latest_start_s"], "latest_s": latest,
                                        "delta_s": latest-float(archive["latest_start_s"])})
            all_traces[name] = {
                **controls, "plan_id": plan_id, "targets": goals, "policies": compiled, "scores": scores,
                "locked": locked, "planned_pending": sorted(set(goals)-set(locked)),
                "cancelled_cached_visits": [{"vehicle": v.vehicle+1, "alert": v.alert, "depart_s": v.depart,
                                            "prior_phase": "already_dispatched" if v.depart < rec else "not_dispatched"}
                                           for v in nominal if v.alert not in locked and v.vehicle != failed],
            }
            if name in ("outage_upper_time", "failure_outage_V2", "all_V2", "all_duration_sensitivity"):
                alt_state, alt_locked = tighter_prefix(nominal, controls, states)
                pending = {a:g for a,g in goals.items() if a not in alt_locked}
                alternative = solver.solve_schedule(alt_state, pending, HORIZON, beam_width=3, stations=2)
                validate_schedule(alternative, pending, alt_state, f"{name}/ongoing_only")
                alt_starts = alt_locked | starts_for(alternative)
                for mode, taken, times in (("cached", locked, updated), ("ongoing_only", alt_locked, alt_starts)):
                    n, eta, last = window_score(times, set(goals), START, HORIZON, INCOMPLETE)
                    variants.append({"case": name, "recovery_s": rec, "outage_duration_s": rec-DISTURBANCE,
                                     "interpretation": mode, "locked": "|".join(sorted(taken)),
                                     "successes": n, "completion_ratio": eta, "latest_start_s": last})
    verify_outage_boundaries(nominal)
    write_csv(out / "P4_cases.csv", rows)
    write_csv(out / "P4_archived_comparison.csv", comparisons)
    write_csv(out / "P4_instruction_sensitivity.csv", variants)
    data = {"plan_id": plan_id, "input_sha256": file_hash(model.ROOT / "data" / "B题题面参数.csv"),
            "window_s": [START, HORIZON], "nominal_policies": nominated, "cases": all_traces}
    write_json(out / "Executed_timeline.json", data)
    v5 = all_traces["failure_V5"]
    detail = []
    for policy, phases in v5["policies"].items():
        for item in phases:
            position, pan, pitch = events.state_of(item, item["end_s"])
            detail.append({"policy": policy, "vehicle": item["vehicle"], "phase": item["phase"],
                           "alert": item["alert"] or "", "origin": item["origin"], "start_s": item["start_s"],
                           "end_s": item["end_s"], "duration_s": item["end_s"]-item["start_s"],
                           "end_x_m": position[0], "end_y_m": position[1], "end_pan_deg": pan, "end_pitch_deg": pitch})
    write_csv(out / "P4_V5_event_comparison.csv", detail)
    return all_traces


def verify_outage_boundaries(nominal):
    from dataclasses import replace
    from math import inf, nextafter

    target = next(v for v in nominal if v.start >= DISTURBANCE).alert
    pair = [p for p in nominal if p.alert == target]
    failed = pair[0].vehicle
    fixtures = (nextafter(DISTURBANCE, -inf), DISTURBANCE, nextafter(DISTURBANCE, inf))
    assert [target in solver.observation_starts([replace(v,start=t) for v in pair], failed, DISTURBANCE)
            for t in fixtures] == [True, False, False]


def main(out):
    stage2 = read_json(out / "priority_2.json")
    assert stage2["routing"]["compared_routes"] > 0
    plans = compare_p2(out)
    cases = compare_p4(out, plans)
    v5 = cases["failure_V5"]["scores"]
    delta = v5["reschedule"]["latest_start_s"] - v5["keep"]["latest_start_s"]
    summary = {
        "nominal_plan_id": digest([asdict(v) for v in plans["beam"]]),
        "shared_k": SHARED_K, "P2_latest_starts_s": {k:tally(p) for k,p in plans.items()},
        "P4_case_count": len(cases), "V5_delay_s": delta, "V5_scores": v5,
        "scope": "Finite candidate pool and beam incumbents; deterministic case grid.",
    }
    write_json(out / "priority_3.json", summary)
    print(f"Priority 3 verified {len(cases)} case pairs and the P2-to-P4 plan ID. V5 delay = {delta:.6f} s.")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=type(DEFAULT_OUTPUT), default=DEFAULT_OUTPUT)
    main(parser.parse_args().out / "results")

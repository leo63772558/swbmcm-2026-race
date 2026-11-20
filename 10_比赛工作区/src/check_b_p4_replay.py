"""Replay published P4 events under explicit clock and instruction assumptions.

Review script assisted by OpenAI Codex (GPT-6 series). One conditional probe
reuses the existing scheduler with only the V3 release time varied.
"""

from argparse import ArgumentParser
import csv
from dataclasses import asdict, replace
import json
from math import dist, inf, nextafter
from pathlib import Path

from check_problem_b import near, read, verify_nominal_records, verify_visits
from problem_b_geometry import TARGETS, number
from solve_problem_b import RESULTS, Visit, observation_starts, solve_schedule


FIELDS = ("case", "interpretation", "metric", "boundary_s", "event_s", "value", "unit")


def point_string(point):
    return "|".join(map(str, point))


def replay_cached_commands(timelines, pairs, scores, disturbance, horizon, add):
    for name, failed in (("outage_upper_time", None), ("failure_outage_V2", 1)):
        record = timelines["scenarios"][name]
        recovery = record["recovery_s"]
        for cached in (True, False):
            locked = {
                alert: visits[0]["start"] for alert, visits in pairs.items()
                if visits[0]["start"] < recovery
                and (visits[0]["start"] < disturbance
                     or all(visit["vehicle"] != failed for visit in visits))
                and (cached or all(visit["depart"] < disturbance for visit in visits))
            }
            interpretation = "full_nominal_plan_cached" if cached else "per_vehicle_ongoing_visits_only"
            expected = record["locked_observations"]
            if not cached and failed is None:
                expected = {alert: start for alert, start in expected.items() if alert != "T3"}
            assert locked == expected, name
            add(name, interpretation, "locked_alerts", "|".join(sorted(locked)))
            add(name, interpretation, "locked_count", len(locked), "alerts")

    name = "failure_outage_V2"
    record = timelines["scenarios"][name]
    recovery = record["recovery_s"]
    first = next(v for v in pairs["T1"] if v["vehicle"] == 2)
    second = next(v for v in pairs["T3"] if v["vehicle"] == 2)
    position, available = record["state_at_recovery"][2]
    assert first["reset"] == second["depart"] and disturbance < second["depart"] < recovery
    assert first["station"] == second["path"][0] == second["station"] == position
    distance = sum(dist(a, b) for a, b in zip(second["path"], second["path"][1:]))
    assert distance == 0 and available == recovery and second["reset"] < recovery
    add(name, "full_nominal_plan_cached", "V3_T3_preparation_start", second["depart"], "s")
    add(name, "full_nominal_plan_cached", "V3_T3_travel", distance, "m")
    add(name, "full_nominal_plan_cached", "V3_nominal_reset_end", second["reset"], "s")
    for interpretation in ("published_nominal_phase_clock", "per_vehicle_ongoing_visits_only"):
        add(name, interpretation, "V3_recovery_position", point_string(position), "m")
        add(name, interpretation, "V3_available_time", available, "s")

    # If V3 remains aimed awaiting its missing partner, apply the existing reset
    # duration at recovery as a sensitivity of the resource state.
    held_until_recovery = "cached_aim_held_until_recovery_then_reset"
    release = recovery + (second["ready"] - second["arrival"])
    revised = next(v for v in record["rescheduled"] if v["vehicle"] == 2)
    assert revised["depart"] == recovery < release
    add(name, held_until_recovery, "V3_recovery_position", point_string(position), "m")
    add(name, held_until_recovery, "V3_available_time", release, "s")
    add(name, held_until_recovery, "V3_published_departure_respects_release", False)

    locked = record["locked_observations"]
    pending = {alert: goal for alert, goal in TARGETS.items() if alert not in locked}
    assert set(pending) == {"T3"}, name
    nominal_states = tuple(
        (tuple(state[0]), state[1]) if state is not None else None
        for state in record["state_at_recovery"]
    )
    delayed = nominal_states[:2] + ((tuple(position), release),) + nominal_states[3:]
    for interpretation, states in (("published_nominal_phase_clock", nominal_states),
                                   (held_until_recovery, delayed)):
        schedule = solve_schedule(states, pending, horizon, beam_width=3, stations=2)
        matched = verify_visits([asdict(v) for v in schedule], pending, states, interpretation)
        starts = locked | {alert: visits[0]["start"] for alert, visits in matched.items()}
        started = [time for time in starts.values() if time < horizon]
        latest = max(started) if len(started) == len(TARGETS) else horizon
        if states == nominal_states:
            published = scores[name, "reschedule"]
            assert len(started) == int(published["successes"])
            assert near(latest, float(published["latest_start_s"]))
            assert json.loads(json.dumps([asdict(v) for v in schedule])) == record["rescheduled"]
        add(name, interpretation, "rerun_started_count", len(started), "alerts")
        add(name, interpretation, "rerun_total_count", len(TARGETS), "alerts")
        add(name, interpretation, "rerun_latest_start_score", latest, "s")
        assigned = sorted(v.vehicle + 1 for v in schedule if v.alert == "T3")
        add(name, interpretation, "rerun_T3_vehicles", "|".join(f"V{i}" for i in assigned))
        v3 = next((v for v in schedule if v.vehicle == 2), None)
        add(name, interpretation, "rerun_V3_assigned", v3 is not None)
        if v3 is not None:
            add(name, interpretation, "rerun_V3_depart", v3.depart, "s")


def replay_recovery_pair(timelines, scores, disturbance, add):
    before, after = "all_V2", "all_duration_sensitivity"
    early, late = (timelines["scenarios"][scenario] for scenario in (before, after))
    for policy in ("keep", "reschedule"):
        first, second = (scores[scenario, policy] for scenario in (before, after))
        for field in ("failed_vehicle", "new_alert_x_m", "new_alert_y_m", "new_alert_altitude_m",
                      "successes", "alerts", "completion_ratio"):
            assert first[field] == second[field], (policy, field)
        for scenario, row in ((before, first), (after, second)):
            recovery = float(row["recovery_s"])
            add(scenario, policy, "absolute_recovery", recovery, "s")
            add(scenario, policy, "outage_duration", recovery - disturbance, "s")
            add(scenario, policy, "started_count", int(row["successes"]), "alerts")
            add(scenario, policy, "total_count", int(row["alerts"]), "alerts")
            add(scenario, policy, "latest_start_score", float(row["latest_start_s"]), "s")

    shift = late["recovery_s"] - early["recovery_s"]
    assert early["locked_observations"] == late["locked_observations"]
    assert early["keep_observation_starts"] == late["keep_observation_starts"]
    for first, second in zip(early["state_at_recovery"], late["state_at_recovery"], strict=True):
        if first is None:
            assert second is None
        else:
            assert first[0] == second[0] and near(second[1] - first[1], shift)
    for first, second in zip(early["rescheduled"], late["rescheduled"], strict=True):
        for key in ("vehicle", "alert", "station", "path"):
            assert first[key] == second[key], key
        for event in ("depart", "arrival", "ready", "start", "end", "reset"):
            assert near(second[event] - first[event], shift), event
    latest_shift = float(scores[after, "reschedule"]["latest_start_s"]) - float(
        scores[before, "reschedule"]["latest_start_s"])
    assert near(latest_shift, shift)
    add("all_V2_to_all_duration_sensitivity", "matched_failure_and_alert", "latest_start_shift", latest_shift, "s")


def check_clock_boundaries(timelines, pairs, disturbance, horizon, add):
    nominal_starts = [visit_pair[0]["start"] for visit_pair in pairs.values()]
    records = timelines["scenarios"].values()
    assert all(start != disturbance for start in nominal_starts)
    assert all(start != record["recovery_s"] for record in records for start in nominal_starts)
    assert all(visit["start"] != horizon for record in records for visit in record["rescheduled"])
    assert all(start != horizon for start in nominal_starts)
    add("published_cases", "exact_equality", "nominal_or_replanned_starts_at_applicable_boundary", 0, "events")

    # Equality cases are synthetic. The live exclusion of an affected pair at
    # the disturbance is also checked against observation_starts.
    affected_pair = tuple(Visit(**v) for v in pairs["T3"])
    recovery = timelines["scenarios"]["outage_upper_time"]["recovery_s"]
    for case, boundary in (("affected_start_at_failure", disturbance),
                           ("nominal_start_at_recovery", recovery),
                           ("counted_start_at_window_end", horizon)):
        for event in (nextafter(boundary, -inf), boundary, nextafter(boundary, inf)):
            before = event < boundary
            if case == "affected_start_at_failure":
                pair = [replace(v, start=event) for v in affected_pair]
                assert ("T3" in observation_starts(pair, affected_pair[0].vehicle, disturbance)) == before
            add(case, "published_strict_before", "accepted", before, boundary=boundary, event=event)
            add(case, "inclusive_equality_sensitivity", "accepted", event <= boundary, boundary=boundary, event=event)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RESULTS / "B_P4_replay.csv")
    args = parser.parse_args()
    timelines = json.loads((RESULTS / "B_timelines.json").read_text(encoding="utf-8"))
    pairs = verify_nominal_records(read("B_P2_schedules.csv"), timelines)
    scores = {(r["scenario"], r["policy"]): r for r in read("B_P4.csv")}
    disturbance = number("p4", "disturbance", "occurrence_time")
    horizon = number("p4", "evaluation", "window_end")
    rows = []

    def add(case, interpretation, metric, value, unit="", *, boundary="", event=""):
        rows.append((case, interpretation, metric, boundary, event, value, unit))

    replay_cached_commands(timelines, pairs, scores, disturbance, horizon, add)
    replay_recovery_pair(timelines, scores, disturbance, add)
    check_clock_boundaries(timelines, pairs, disturbance, horizon, add)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(FIELDS)
        writer.writerows(rows)
    print(f"P4 replay and boundary checks passed. Wrote {len(rows)} evidence rows to {args.output}.")


if __name__ == "__main__":
    main()

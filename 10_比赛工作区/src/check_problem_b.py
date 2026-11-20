"""Independent numerical and timeline cross-checks. AI-assisted (OpenAI Codex)."""

from ast import literal_eval
from collections import defaultdict
import csv
from functools import partial
import json
from math import atan2, cos, degrees, dist, isclose, isfinite, isinf, radians, sin, sqrt
from random import Random
from statistics import NormalDist

from problem_b_geometry import BUILDINGS, OBSERVE, ORIGIN, SPEED, TARGETS, VEHICLES
from problem_b_geometry import angles, in_field, number, read_values, road_clear, route_position
from problem_b_geometry import segment_hits_box, slew_time, visible
from solve_problem_b import RESULTS, INITIAL, accuracy, solve_schedule, validate_visits, write_csv


TOL = 1e-8
near = partial(isclose, rel_tol=0.0, abs_tol=TOL)


def verify_geometry():
    box = ((0, 1), (0, 1), (0, 1))
    assert segment_hits_box((-1, 0, 1), (2, 0, 1), box)
    assert not segment_hits_box((-1, 0, 1.1), (2, 0, 1.1), box)
    assert not segment_hits_box((-2, .5, .5), (-1, .5, .5), box)
    assert len(BUILDINGS) == 5 and len(VEHICLES) == 5
    assert not visible(TARGETS["T1"][:2], TARGETS["T1"])


def verify_localization_boundaries(row):
    synthetic_target = (0.0, 0.0, 10.0)
    reference = (10.0, 0.0)
    _, right_angle = accuracy(reference, (0.0, 10.0), synthetic_target)
    assert near(right_angle, 90.0)
    for second in ((20.0, 0.0), (-10.0, 0.0)):
        rms, angle = accuracy(reference, second, synthetic_target)
        assert isinf(rms) and angle in (0.0, 180.0)

    target = TARGETS["T2"]
    for index in (1, 2):
        station = float(row[f"x_{index}_m"]), float(row[f"y_{index}_m"])
        radius = dist(target[:2], station)
        unit = tuple((value - center) / radius for value, center in zip(station, target[:2]))
        inward = tuple(value - 0.001 * axis for value, axis in zip(station, unit))
        outward = tuple(value + 0.001 * axis for value, axis in zip(station, unit))
        assert visible(station, target), ("nominal T2 station", index)
        assert not visible(inward, target) and visible(outward, target), ("1 mm pitch probe", index)


def intersection_rms(row, rng, samples):
    first = float(row["x_1_m"]), float(row["y_1_m"])
    second = float(row["x_2_m"]), float(row["y_2_m"])
    true_x, true_y, _ = TARGETS["T2"]
    alpha1 = atan2(true_y - first[1], true_x - first[0])
    alpha2 = atan2(true_y - second[1], true_x - second[0])
    sigma = radians(number("p2_1", "bearing", "error_std"))
    dx, dy = second[0] - first[0], second[1] - first[1]
    error_sum = 0.0
    for _ in range(samples):
        a1, a2 = alpha1 + rng.gauss(0, sigma), alpha2 + rng.gauss(0, sigma)
        d1 = cos(a1), sin(a1)
        d2 = cos(a2), sin(a2)
        quotient = (dx * d2[1] - dy * d2[0]) / (d1[0] * d2[1] - d1[1] * d2[0])
        x, y = first[0] + quotient * d1[0], first[1] + quotient * d1[1]
        error_sum += (x - true_x) ** 2 + (y - true_y) ** 2
    return sqrt(error_sum / samples)


def wilson(successes, samples):
    z = NormalDist().inv_cdf(.975)
    p = successes / samples
    denominator = 1 + z*z / samples
    center = (p + z*z / (2 * samples)) / denominator
    delta = z * sqrt(p * (1 - p) / samples + (z / (2 * samples))**2) / denominator
    return p, center - delta, center + delta


def pointing_coverage(distance_traveled, rng, samples):
    r = number("p3", "target", "horizontal_range")
    a, b = read_values("p3", "position", "coordinate_std_intercept", "coordinate_std_slope")
    z, c = read_values("p3", "gimbal", "zero_offset_std", "control_error_std")
    limit = number("p3", "error", "absolute_error_max")
    deviation = a + b * distance_traveled
    successes = 0
    for _ in range(samples):
        x, y = rng.gauss(0, deviation), rng.gauss(0, deviation)
        angle = degrees(atan2(y, r - x)) + rng.gauss(0, z) + rng.gauss(0, c)
        successes += abs((angle + 180) % 360 - 180) <= limit
    return wilson(successes, samples)


def verify_visits(visits, goals, states, context):
    by_vehicle = defaultdict(list)
    by_alert = defaultdict(list)
    for visit in visits:
        vehicle, alert = visit["vehicle"], visit["alert"]
        where = f"{context} V{vehicle + 1} {alert}"
        assert 0 <= vehicle < len(VEHICLES) and states[vehicle] is not None, where
        assert alert in goals, where
        path, station = visit["path"], visit["station"]
        assert path and dist(path[-1], station) <= TOL, f"{where} path endpoint"
        assert all(in_field(point) for point in path), f"{where} path outside field"
        assert all(road_clear(a, b) for a, b in zip(path, path[1:])), f"{where} blocked route"
        assert visible(station, goals[alert]), f"{where} obstructed view"
        depart, arrive, ready, start, end, reset = (
            visit[event] for event in ("depart", "arrival", "ready", "start", "end", "reset")
        )
        assert all(isfinite(t) for t in (depart, arrive, ready, start, end, reset)), where
        assert 0 <= depart <= arrive <= ready <= start < end <= reset, f"{where} event order"
        travel = sum(dist(a, b) for a, b in zip(path, path[1:])) / SPEED
        turn = slew_time(station, goals[alert])
        assert near(arrive - depart, travel), f"{where} drive time"
        assert near(ready - arrive, turn), f"{where} aiming time"
        assert near(end - start, OBSERVE), f"{where} observation time"
        assert near(reset - end, turn), f"{where} reset time"
        by_vehicle[vehicle].append(visit)
        by_alert[alert].append(visit)

    for vehicle, own in by_vehicle.items():
        position, available = states[vehicle]
        for visit in sorted(own, key=lambda v: v["depart"]):
            where = f"{context} V{vehicle + 1} {visit['alert']}"
            assert visit["depart"] >= available - TOL, f"{where} overlaps previous visit or recovery"
            assert dist(visit["path"][0], position) <= TOL, f"{where} path origin"
            position, available = visit["station"], visit["reset"]

    for alert, pair in by_alert.items():
        where = f"{context} {alert}"
        assert len(pair) == 2 and pair[0]["vehicle"] != pair[1]["vehicle"], f"{where} pair"
        expected_start = max(visit["ready"] for visit in pair)
        assert all(near(visit["start"], expected_start) for visit in pair), f"{where} synchronized start"
        first, second = (angles(visit["station"], goals[alert])[0] for visit in pair)
        crossing = abs((first - second + 180) % 360 - 180)
        assert 1e-6 < crossing < 180 - 1e-6, f"{where} degenerate baseline"
    return by_alert


def verify_nominal_records(rows, timelines):
    csv_visits = {(row["policy"], int(row["vehicle"]), row["alert"]): row for row in rows}
    assert len(csv_visits) == len(rows), "P2 duplicate visit"
    nominal_pairs = None
    for policy, key in (("beam", "nominal"), ("nearest", "nearest")):
        visits = timelines[key]
        pairs = verify_visits(visits, TARGETS, INITIAL, policy)
        assert set(pairs) == set(TARGETS), f"{policy} missing nominal alert"
        if policy == "beam":
            nominal_pairs = pairs
        for visit in visits:
            identity = (policy, visit["vehicle"], visit["alert"])
            row = csv_visits.pop(identity)
            assert dist(literal_eval(row["station"]), visit["station"]) <= TOL, identity
            for event in ("depart", "arrival", "ready", "start", "end", "reset"):
                assert near(float(row[event]), visit[event]), (identity, event)
    assert not csv_visits, "P2 CSV contains visits missing from the JSON"
    return nominal_pairs


def verify_recovery_state(record, nominal, time, failed, locked, scenario):
    states = record["state_at_recovery"]
    assert len(states) == len(VEHICLES), scenario
    assert record["nominal_before_replan"] == [visit for visit in nominal if visit["depart"] < time], scenario
    for vehicle, actual in enumerate(states):
        where = f"{scenario} V{vehicle + 1}"
        if vehicle == failed:
            assert actual is None, f"{where} failed vehicle in recovery state"
            continue
        assert actual is not None, f"{where} missing recovery state"
        position, available = VEHICLES[vehicle], time
        active = max(
            (v for v in nominal if v["vehicle"] == vehicle and v["depart"] <= time),
            key=lambda v: v["depart"],
            default=None,
        )
        if active and time < active["arrival"]:
            position = route_position(active["path"], (time - active["depart"]) * SPEED)
        elif active:
            position = active["station"]
            if time < active["reset"]:
                if active["alert"] in locked:
                    available = active["reset"]
                else:
                    turn = min(time, active["ready"]) - active["arrival"]
                    available = time + turn
        assert dist(actual[0], position) <= TOL, f"{where} recovery position"
        assert near(actual[1], available), f"{where} recovery availability or head reset"
    return states


def verify_scenario_records(rows, timelines, nominal_pairs):
    grouped = defaultdict(dict)
    window_start, horizon, incomplete = read_values(
        "p4", "evaluation", "window_start", "window_end", "incomplete_latest_start"
    )
    disturbance = number("p4", "disturbance", "occurrence_time")
    alert_fields = ("new_alert_x_m", "new_alert_y_m", "new_alert_altitude_m")
    min_range, max_range, altitude = read_values(
        "p4", "new_alert", "horizontal_range_min", "horizontal_range_max", "altitude"
    )
    for row in rows:
        policies = grouped[row["scenario"]]
        assert row["policy"] not in policies, f"P4 duplicate row for {row['scenario']}"
        policies[row["policy"]] = row
    assert set(grouped) == set(timelines["scenarios"])
    assert grouped, "P4 results are empty"
    for scenario, pair in grouped.items():
        assert set(pair) == {"keep", "reschedule"}, f"{scenario} missing or unknown policy"
        original = pair["keep"]
        for field in ("alerts", "failed_vehicle", "recovery_s", *alert_fields):
            assert original[field] == pair["reschedule"][field], (scenario, field)
        record = timelines["scenarios"][scenario]
        recovery = float(original["recovery_s"])
        assert disturbance <= recovery <= horizon and near(record["recovery_s"], recovery), scenario
        failed = int(original["failed_vehicle"]) - 1 if original["failed_vehicle"] else None
        assert failed is None or 0 <= failed < len(VEHICLES), scenario
        goals = dict(TARGETS)
        coordinates = [original[field] for field in alert_fields]
        if any(coordinates):
            assert all(coordinates), f"{scenario} incomplete new alert"
            goal = tuple(map(float, coordinates))
            assert min_range - TOL <= dist(goal[:2], ORIGIN) <= max_range + TOL, scenario
            assert near(goal[2], altitude), scenario
            goals["T4"] = goal

        keep = {
            alert: visits[0]["start"] for alert, visits in nominal_pairs.items()
            if visits[0]["start"] < disturbance or all(v["vehicle"] != failed for v in visits)
        }
        locked = {alert: time for alert, time in keep.items() if time < recovery}
        assert record["keep_observation_starts"] == keep, f"{scenario} keep observations"
        assert record["locked_observations"] == locked, f"{scenario} locked observations"
        states = verify_recovery_state(record, timelines["nominal"], recovery, failed, locked, scenario)
        after = verify_visits(record["rescheduled"], goals, states, scenario)
        assert not locked.keys() & after.keys(), f"{scenario} locked alert rescheduled"
        rescheduled = locked | {alert: visits[0]["start"] for alert, visits in after.items()}
        for policy, starts in (("keep", keep), ("reschedule", rescheduled)):
            row = pair[policy]
            assert all(time >= window_start for time in starts.values()), (scenario, policy)
            times = [time for time in starts.values() if time < horizon]
            total, completed = len(goals), len(times)
            assert total == int(row["alerts"]) and completed == int(row["successes"]), (scenario, policy)
            assert near(completed / total, float(row["completion_ratio"])), (scenario, policy, "ratio")
            expected_score_time = max(times) if completed == total else incomplete
            assert near(expected_score_time, float(row["latest_start_s"])), (scenario, policy, "time")


def read(name):
    with (RESULTS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main():
    verify_geometry()
    timelines = json.loads((RESULTS / "B_timelines.json").read_text(encoding="utf-8"))
    nominal_pairs = verify_nominal_records(read("B_P2_schedules.csv"), timelines)
    verify_scenario_records(read("B_P4.csv"), timelines, nominal_pairs)
    samples = 100_000
    rng = Random(20261120)
    loc = read("B_P2_localization.csv")[0]
    verify_localization_boundaries(loc)
    p3 = read("B_P3.csv")[0]
    estimate = intersection_rms(loc, rng, samples)
    reference = float(loc["horizontal_rms_m"])
    assert abs(estimate / reference - 1) < .02
    audit = [{"test": "P2 RMS exact intersection", "setting": "selected pair",
              "estimate": estimate, "comparison": reference,
              "lower": "", "upper": "", "samples": samples}]
    check = number("p3", "vehicle", "parameter_check_distance")
    for label, path in (("threshold", float(p3["path_cap_m"])), ("parameter check", check)):
        result, lower, upper = pointing_coverage(path, rng, samples)
        required = number("p3", "error", "coverage_min")
        assert (lower <= required <= upper) if label == "threshold" else upper < required
        audit.append({"test": "P3 wrapped Monte Carlo", "setting": label, "estimate": result,
                      "comparison": required, "lower": lower, "upper": upper, "samples": samples})
    for width, k in ((5, 3), (12, 6), (20, 8), (40, 12)):
        schedule = solve_schedule(INITIAL, TARGETS, beam_width=width, stations=k)
        assert len(schedule) == 2 * len(TARGETS)
        validate_visits(schedule, TARGETS)
        audit.append({"test": "P2 schedule budget", "setting": f"beam={width}, stations={k}",
                      "estimate": max(v.start for v in schedule),
                      "comparison": "", "lower": "", "upper": "", "samples": ""})
    write_csv("B_validation.csv", audit)
    print(f"Geometry, two published schedules, {len(timelines['scenarios'])} disturbance pairs, "
          "repeated scheduling and Monte Carlo checks passed.")


if __name__ == "__main__":
    main()

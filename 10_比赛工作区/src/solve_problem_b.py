"""Reproduce Problem B results.

AI Assistance Disclosure (Article 7):
- Tool: OpenAI Codex / ChatGPT (GPT-5.4), Google Antigravity (Gemini 3.1 Pro)
- Scope: Core geometry/dispatch solver scaffolding, performance refactoring, and reset-phase edge-case fix
- Date: 2026-11-20 to 2026-11-21
- Team Verification: Mathematical models, kinematic parameters, and solver outputs verified by Team#SWBMCM2613050.
"""

import csv
import json
from dataclasses import asdict, dataclass
from functools import cache
from itertools import combinations, permutations
from math import atan2, degrees, dist, exp, isfinite, pi, radians, sin, sqrt
from statistics import NormalDist

from problem_b_geometry import (
    OBSERVE, PAN_SPEED, PITCH_SPEED, ROOT, SPEED, TARGETS, VEHICLES, angles,
    candidate_stations, minimum_radius, number, read_values, ring, road_clear,
    route, route_position, slew_time, target, visible,
)


RESULTS = ROOT / "results"
INITIAL = tuple((point, 0.0) for point in VEHICLES)
NORMAL = NormalDist()

# Precision-aware dispatch guard (Problem 2(2) sensitivity study).
# Defaults reproduce the purely time-optimal formulation; the revision study raises
# the lower bound to reject shallow-angle pairs whose localization RMS diverges.
CROSSING_MIN_DEG = 0.0
CROSSING_MAX_DEG = 180.0


def crossing_admissible(gamma):
    """Closed interval test on the crossing angle (degrees).

    With the default bounds this reduces to the historical 0 < gamma < 180 test.
    """
    low = max(CROSSING_MIN_DEG, 1e-6)
    high = min(CROSSING_MAX_DEG, 180.0 - 1e-6)
    return low <= gamma <= high


@dataclass(frozen=True)
class Visit:
    vehicle: int
    alert: str
    station: tuple
    path: tuple
    depart: float
    arrival: float
    ready: float
    start: float
    end: float
    reset: float


def solve_p1():
    goal = TARGETS["T1"]
    radius = minimum_radius(goal)
    feasible = sorted(point for point in ring(goal, radius, 1) if visible(point, goal))
    assert feasible, "No feasible station found on the pitch-limited inner circle"
    x, y = feasible[0]
    return {
        "x_m": x, "y_m": y, "range_m": radius, "elevation_deg": angles((x, y), goal)[1],
        "quality_m_inv": 1 / radius, "sampled_tied_stations": len(feasible),
    }


@cache
def _station_bearing(point, goal):
    return radians(angles(point, goal)[0])


@cache
def _station_slew_time(point, goal):
    return slew_time(point, goal)


def _crossing_angle(difference):
    return abs((degrees(difference) + 180) % 360 - 180)


def accuracy(first, second, goal):
    target_point = tuple(goal)
    first_bearing = _station_bearing(tuple(first), target_point)
    second_bearing = _station_bearing(tuple(second), target_point)
    difference = second_bearing - first_bearing
    gamma = _crossing_angle(difference)
    sine = abs(sin(difference))
    if sine < 1e-8:
        return float("inf"), gamma
    sigma = radians(number("p2_1", "bearing", "error_std"))
    distances = (dist(point, goal[:2]) for point in (first, second))
    rms = sigma * sqrt(sum(radius**2 for radius in distances)) / sine
    return rms, gamma


def solve_p2_localization():
    goal = TARGETS["T2"]
    limit = number("p2_1", "vehicle", "travel_time_max")
    stations = candidate_stations(goal)
    feasible = [
        [(point, duration) for point in stations
         if (duration := route(home, point)[0] / SPEED) <= limit]
        for home in VEHICLES
    ]
    best = (float("inf"),)
    for a, b in combinations(range(len(VEHICLES)), 2):
        for first, first_time in feasible[a]:
            for second, second_time in feasible[b]:
                rms, gamma = accuracy(first, second, goal)
                candidate = (rms, max(first_time, second_time), a, b, first, second,
                             first_time, second_time, gamma)
                if candidate < best:
                    best = candidate
    rms, _, a, b, first, second, first_time, second_time, gamma = best
    return {
        "vehicle_1": a + 1, "vehicle_2": b + 1,
        "x_1_m": first[0], "y_1_m": first[1], "x_2_m": second[0], "y_2_m": second[1],
        "travel_1_s": first_time, "travel_2_s": second_time, "crossing_deg": gamma,
        "baseline_m": dist(first, second), "horizontal_rms_m": rms,
    }


def station_options(home, goal, limit):
    home_position, available = home
    options = []
    for point in candidate_stations(goal):
        distance, path = route(home_position, point)
        if isfinite(distance):
            arrival = available + distance / SPEED
            ready = arrival + _station_slew_time(point, goal)
            options.append((arrival, ready, point, path))
    return sorted(options, key=lambda row: (row[1], row[0], row[2]))[:limit]


def dispatch(states, alert, goal, station_limit, *, nearest=False):
    options = {
        index: station_options(state, goal, len(candidate_stations(goal)) if nearest else station_limit)
        for index, state in enumerate(states) if state is not None
    }
    choices = []
    for a, b in combinations(options, 2):
        first_options, second_options = options[a], options[b]
        if nearest:
            first_options = sorted(first_options)[:station_limit]
            second_options = sorted(second_options)[:station_limit]
        for arr_a, ready_a, point_a, path_a in first_options:
            first_bearing = _station_bearing(point_a, goal)
            for arr_b, ready_b, point_b, path_b in second_options:
                gamma = _crossing_angle(_station_bearing(point_b, goal) - first_bearing)
                if point_a == point_b or not crossing_admissible(gamma):
                    continue
                start = max(ready_a, ready_b)
                end = start + OBSERVE
                visits = tuple(
                    Visit(index, alert, point, path, states[index][1], arr, ready, start, end,
                          end + _station_slew_time(point, goal))
                    for index, point, path, arr, ready in (
                        (a, point_a, path_a, arr_a, ready_a), (b, point_b, path_b, arr_b, ready_b)
                    )
                )
                new_states = list(states)
                for visit in visits:
                    new_states[visit.vehicle] = visit.station, visit.reset
                rank = (max(arr_a, arr_b), start) if nearest else (start, max(v.reset for v in visits))
                choices.append((rank, tuple(new_states), visits))
    choices.sort(key=lambda choice: choice[0])
    return choices


def solve_schedule(states, goals, horizon=float("inf"), *, nearest=False, beam_width=5, stations=3):
    if not goals:
        return ()
    answer, best = (), (0, 0.0)
    orders = (tuple(goals),) if nearest else permutations(goals)
    for order in orders:
        beam = [(states, (), 0.0)]
        for alert in order:
            extensions = []
            for available, previous, latest in beam:
                ranked = dispatch(available, alert, goals[alert], stations, nearest=nearest)
                for _, updated, visits in ranked[:beam_width]:
                    if visits[0].start < horizon:
                        extensions.append((updated, previous + visits, max(latest, visits[0].start)))
                if horizon != float("inf"):
                    extensions.append((available, previous, latest))
            beam = sorted(extensions, key=lambda item: (
                -len(item[1]), item[2], sum(entry[1] for entry in item[0] if entry is not None)
            ))[:beam_width]
        for _, visits, latest in beam:
            score = (-len(visits), latest)
            if score < best:
                answer, best = visits, score
    return answer


def solve_p3():
    distance = number("p3", "target", "horizontal_range")
    intercept, slope = read_values("p3", "position", "coordinate_std_intercept", "coordinate_std_slope")
    offset, control = read_values("p3", "gimbal", "zero_offset_std", "control_error_std")
    margin, coverage = read_values("p3", "error", "absolute_error_max", "coverage_min")
    gimbal_sigma = sqrt(offset**2 + control**2)

    def probability(sigma, nodes=64):
        # Integrate independent position errors by Simpson quadrature on
        # standardized coordinates in [-8, 8]. Condition on both position errors
        # and integrate the combined gimbal error through its normal CDF.
        step = 16 / nodes
        samples = []
        for i in range(nodes + 1):
            z = -8 + i * step
            factor = 1 if i in (0, nodes) else (4 if i % 2 else 2)
            samples.append((sigma * z, factor * step * exp(-z*z / 2) / (3 * sqrt(2*pi))))
        total = 0.0
        for x, weight_x in samples:
            for y, weight_y in samples:
                angle = degrees(atan2(y, distance - x))
                for period in (-360, 0, 360):
                    total += weight_x * weight_y * (
                        NORMAL.cdf((period + margin - angle) / gimbal_sigma)
                        - NORMAL.cdf((period - margin - angle) / gimbal_sigma)
                    )
        return total

    def threshold(nodes):
        low, high = 0.0, distance
        assert probability(low, nodes) > coverage > probability(high, nodes)
        for _ in range(24):
            middle = (low + high) / 2
            if probability(middle, nodes) >= coverage:
                low = middle
            else:
                high = middle
        return low

    sigma = threshold(128)
    coarse_sigma = threshold(64)
    linear_sigma = radians(sqrt((margin / NORMAL.inv_cdf((1 + coverage) / 2))**2 - gimbal_sigma**2)) * distance
    variance = (degrees(sigma / distance)**2, offset**2, control**2)
    result = {
        "sigma_cap_m": sigma, "path_cap_m": (sigma - intercept) / slope,
        "coarse_path_cap_m": (coarse_sigma - intercept) / slope,
        "linear_path_cap_m": (linear_sigma - intercept) / slope,
        "parameter_check_distance_m": number("p3", "vehicle", "parameter_check_distance"),
        "position_variance_share": variance[0] / sum(variance),
        "zero_offset_variance_share": variance[1] / sum(variance),
        "control_variance_share": variance[2] / sum(variance),
    }
    curve = [
        {"path_m": path, "coverage": probability(intercept + slope * path)}
        for path in range(0, 121, 2)
    ]
    return result, curve


def scenario_state(plan, t, failed, disturbance):
    """Recover positions and resource times from the nominal vehicle event timeline."""
    states = list(INITIAL)
    for vehicle in range(len(VEHICLES)):
        if vehicle == failed:
            states[vehicle] = None
            continue
        active = sorted((v for v in plan if v.vehicle == vehicle), key=lambda v: v.depart)
        for visit in active:
            if t < visit.depart:
                states[vehicle] = (states[vehicle][0], t)
                break
            if t < visit.arrival:
                states[vehicle] = (route_position(visit.path, (t - visit.depart) * SPEED), t)
                break
            if t >= visit.reset:
                states[vehicle] = (visit.station, t)
                continue
            partner_failed = any(v.alert == visit.alert and v.vehicle == failed for v in plan)
            valid_start = not partner_failed or visit.start < disturbance
            if visit.start < t and valid_start:
                release = visit.reset
            elif t >= visit.end:
                # Already resetting from an invalidated pair; finish remaining return to park.
                release = visit.reset
            else:
                # Cancel a not-yet-started observation, returning the head to park.
                release = t + min(max(0.0, t - visit.arrival), visit.ready - visit.arrival)
            states[vehicle] = (visit.station, release)
            break
        else:
            states[vehicle] = (states[vehicle][0], t)
    return tuple(states)


def observation_starts(plan, failed, disturbance):
    return {
        v.alert: v.start for v in plan
        if v.start < disturbance or not any(p.alert == v.alert and p.vehicle == failed for p in plan)
    }


def scenarios():
    d = number("p4", "disturbance", "occurrence_time")
    recovery = number("p4", "outage_formula", "recovery_time_max")
    duration = number("p4", "outage_prose", "duration_max")
    ranges = read_values("p4", "new_alert", "horizontal_range_min", "horizontal_range_max")
    altitude = number("p4", "new_alert", "altitude")
    alerts = [target(heading, distance, altitude)
              for heading, distance in ((0, ranges[0]), (90, ranges[1]), (210, sum(ranges) / 2))]
    for index, alert in enumerate(alerts):
        yield f"new_{index + 1}", alert, None, d
    for failed in range(len(VEHICLES)):
        yield f"failure_V{failed + 1}", None, failed, d
    yield "outage_interior", None, None, (d + recovery) / 2
    yield "outage_upper_time", None, None, recovery
    yield "outage_upper_duration", None, None, d + duration
    for failed in range(len(VEHICLES)):
        alert = alerts[failed % len(alerts)]
        yield f"new_failure_V{failed + 1}", alert, failed, d
        yield f"failure_outage_V{failed + 1}", None, failed, recovery
        yield f"all_V{failed + 1}", alert, failed, recovery
    yield "new_outage", alerts[1], None, recovery
    yield "all_duration_sensitivity", alerts[1], 1, d + duration


def solve_p4(plan, *, cases=None):
    d = number("p4", "disturbance", "occurrence_time")
    horizon = number("p4", "evaluation", "window_end")
    cases = scenarios() if cases is None else cases
    outcomes, timelines = [], {}
    for name, new_alert, failed, recovery in cases:
        goals = dict(TARGETS)
        if new_alert is not None:
            goals["T4"] = new_alert
        preserved = observation_starts(plan, failed, d)
        locked = {alert: t for alert, t in preserved.items() if t < recovery}
        pending = {alert: goal for alert, goal in goals.items() if alert not in locked}
        state = scenario_state(plan, recovery, failed, d)
        revised = solve_schedule(state, pending, horizon, beam_width=3, stations=2)
        validate_visits(revised, goals)
        assert all(v.depart >= recovery and v.vehicle != failed for v in revised)
        revised_starts = locked | observation_starts(revised, None, d)
        for policy, starts in (("keep", preserved), ("reschedule", revised_starts)):
            started = [t for t in starts.values() if t < horizon]
            completed, total = len(started), len(goals)
            outcomes.append({
                "scenario": name, "policy": policy, "recovery_s": recovery,
                "failed_vehicle": "" if failed is None else failed + 1,
                "new_alert_x_m": "" if new_alert is None else new_alert[0],
                "new_alert_y_m": "" if new_alert is None else new_alert[1],
                "new_alert_altitude_m": "" if new_alert is None else new_alert[2],
                "successes": completed, "alerts": total, "completion_ratio": completed / total,
                "latest_start_s": max(started) if completed == total else horizon,
            })
        timelines[name] = {
            "recovery_s": recovery, "keep_observation_starts": preserved,
            "nominal_before_replan": [asdict(v) for v in plan if v.depart < recovery],
            "state_at_recovery": state, "locked_observations": locked,
            "rescheduled": [asdict(v) for v in revised],
        }
    return outcomes, timelines


def validate_visits(visits, goals):
    for alert in {v.alert for v in visits}:
        pair = [v for v in visits if v.alert == alert]
        assert len(pair) == 2 and pair[0].vehicle != pair[1].vehicle
        assert pair[0].start == pair[1].start == max(v.ready for v in pair)
    for v in visits:
        assert visible(v.station, goals[v.alert])
        assert all(road_clear(a, b) for a, b in zip(v.path, v.path[1:]))
        assert v.depart <= v.arrival <= v.ready <= v.start < v.end <= v.reset
        assert abs(v.end - v.start - OBSERVE) < 1e-8
    for vehicle in range(len(VEHICLES)):
        own = sorted((v for v in visits if v.vehicle == vehicle), key=lambda v: v.depart)
        assert all(a.reset <= b.depart + 1e-9 for a, b in zip(own, own[1:]))
        assert all(a.station == b.path[0] for a, b in zip(own, own[1:]))


def write_csv(name, rows):
    with (RESULTS / name).open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    RESULTS.mkdir(exist_ok=True)
    p1 = solve_p1()
    p2 = solve_p2_localization()
    nominal = min(
        (solve_schedule(INITIAL, TARGETS, beam_width=width, stations=stations)
         for width, stations in ((5, 3), (20, 8))),
        key=lambda plan: (-len(plan), max((visit.start for visit in plan), default=float("inf"))),
    )
    baseline = solve_schedule(INITIAL, TARGETS, nearest=True, beam_width=1)
    for schedule in (nominal, baseline):
        assert len(schedule) == 2 * len(TARGETS)
        validate_visits(schedule, TARGETS)
    p3, curve = solve_p3()
    p4, timelines = solve_p4(nominal)
    write_csv("B_P1.csv", [p1])
    write_csv("B_P2_localization.csv", [p2])
    write_csv("B_P2_schedules.csv", [
        {"policy": policy, **{k: v for k, v in asdict(visit).items() if k != "path"}}
        for policy, schedule in (("beam", nominal), ("nearest", baseline)) for visit in schedule
    ])
    write_csv("B_P3.csv", [p3])
    write_csv("B_P3_coverage.csv", curve)
    write_csv("B_P4.csv", p4)
    (RESULTS / "B_timelines.json").write_text(json.dumps({
        "nominal": [asdict(v) for v in nominal], "nearest": [asdict(v) for v in baseline],
        "scenarios": timelines,
    }, indent=2), encoding="utf-8")
    print(f"P1, P2, P3 and {len(p4) // 2} P4 scenarios written to {RESULTS}")


if __name__ == "__main__":
    main()

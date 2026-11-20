"""Independent numerical and timeline cross-checks. AI-assisted (OpenAI Codex)."""

from collections import defaultdict
import json
from math import atan2, cos, degrees, dist, radians, sin, sqrt
from random import Random
from statistics import NormalDist

from problem_b_geometry import BUILDINGS, HEIGHT, OBSERVE, SPEED, TARGETS, VEHICLES
from problem_b_geometry import number, read_values, segment_hits_box, visible
from solve_problem_b import RESULTS, INITIAL, solve_schedule, validate_visits, write_csv


def verify_geometry():
    box = ((0, 1), (0, 1), (0, 1))
    assert segment_hits_box((-1, 0, 1), (2, 0, 1), box)
    assert not segment_hits_box((-1, 0, 1.1), (2, 0, 1.1), box)
    assert not segment_hits_box((-2, .5, .5), (-1, .5, .5), box)
    assert len(BUILDINGS) == 5 and len(VEHICLES) == 5
    assert not visible(TARGETS["T1"][:2], TARGETS["T1"])


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


def verify_scenario_records(rows, timelines):
    grouped = defaultdict(dict)
    horizon = number("p4", "evaluation", "window_end")
    disturbance = number("p4", "disturbance", "occurrence_time")
    for row in rows:
        grouped[row["scenario"]][row["policy"]] = row
    assert set(grouped) == set(timelines["scenarios"])
    for scenario, pair in grouped.items():
        original, revised = pair["keep"], pair["reschedule"]
        for field in ("alerts", "failed_vehicle", "recovery_s"):
            assert original[field] == revised[field]
        record = timelines["scenarios"][scenario]
        after = record["rescheduled"]
        for visit in after:
            assert visit["depart"] >= record["recovery_s"]
            if revised["failed_vehicle"]:
                assert visit["vehicle"] + 1 != int(revised["failed_vehicle"])
            traveled = sum(dist(a, b) for a, b in zip(visit["path"], visit["path"][1:]))
            assert abs(traveled / SPEED - (visit["arrival"] - visit["depart"])) < 1e-8
            assert abs(visit["end"] - visit["start"] - OBSERVE) < 1e-8
        for policy, row in pair.items():
            starts = record["keep_observation_starts"] if policy == "keep" else (
                record["locked_observations"] | {v["alert"]: v["start"] for v in after}
            )
            times = [time for time in starts.values() if time < horizon]
            assert len(times) == int(row["successes"])
            assert len(times) / int(row["alerts"]) == float(row["completion_ratio"])
            assert (max(times) if len(times) == int(row["alerts"]) else horizon) == float(row["latest_start_s"])
            assert all(t >= 0 for t in times)
        assert record["recovery_s"] >= disturbance


def read(name):
    import csv
    with (RESULTS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main():
    verify_geometry()
    samples = 100_000
    rng = Random(20261120)
    loc = read("B_P2_localization.csv")[0]
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
    verify_scenario_records(read("B_P4.csv"),
                            json.loads((RESULTS / "B_timelines.json").read_text(encoding="utf-8")))
    write_csv("B_validation.csv", audit)
    print("Geometry, repeated scheduling, Monte Carlo and paired scenario checks passed.")


if __name__ == "__main__":
    main()

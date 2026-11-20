"""Audit the stored P1 station and P3 travel threshold.

OpenAI Codex (GPT-6 series) assisted with this check on 2026-11-20.
"""

from math import dist
from random import Random

from check_problem_b import near, pointing_coverage, read
from problem_b_geometry import TARGETS, angles, minimum_radius, number, ring, visible
from solve_problem_b import write_csv


SAMPLES = 200_000
SEED = 26130503
OFFSETS_M = (-5, -2, 0, 2, 5)


def verify_p1_tie():
    row, = read("B_P1.csv")
    target = TARGETS["T1"]
    minimum = minimum_radius(target)
    candidates = [point for point in ring(target, minimum, 1) if visible(point, target)]
    chosen = float(row["x_m"]), float(row["y_m"])
    assert candidates and chosen == min(candidates), "Stored P1 station disagrees with the x/y tie rule"
    assert len(candidates) == int(row["sampled_tied_stations"]), "Stored P1 tie count differs"
    assert near(dist(chosen, target[:2]), float(row["range_m"]))
    assert near(angles(chosen, target)[1], float(row["elevation_deg"]))
    print(f"P1: {len(candidates)} feasible 1-degree samples; lexicographic x/y tie check passed.")


def margin_checks():
    result, = read("B_P3.csv")
    threshold = float(result["path_cap_m"])
    required = number("p3", "error", "coverage_min")
    rng = Random(SEED)
    rows = []
    for offset in OFFSETS_M:
        distance = threshold + offset
        assert distance >= 0, "Selected checkpoint falls outside the travel domain"
        estimate, lower, upper = pointing_coverage(distance, rng, SAMPLES)
        outcome = "interval_contains_requirement"
        if lower > required:
            outcome = "interval_above_requirement"
        elif upper < required:
            outcome = "interval_below_requirement"
        rows.append({
            "travel_m": distance,
            "offset_from_reported_limit_m": offset,
            "successes": round(estimate * SAMPLES),
            "samples": SAMPLES,
            "estimated_coverage": estimate,
            "pointwise_wilson_95_lower": lower,
            "pointwise_wilson_95_upper": upper,
            "required_coverage": required,
            "interval_assessment": outcome,
            "rng_seed": SEED,
        })
    return rows


def main():
    verify_p1_tie()
    write_csv("B_P3_margin.csv", margin_checks())
    print("P3: wrote the five checkpoint estimates and pointwise Wilson intervals.")


if __name__ == "__main__":
    main()

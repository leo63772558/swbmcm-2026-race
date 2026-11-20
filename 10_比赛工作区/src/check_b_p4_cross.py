"""Cross existing P4 inputs without changing the recorded dispatch policies.

OpenAI Codex (GPT-6 series) assisted with the verification script.
"""

from itertools import product
import json

from check_problem_b import read, verify_nominal_records, verify_scenario_records
from problem_b_geometry import VEHICLES, number
from solve_problem_b import RESULTS, Visit, scenarios, solve_p4, write_csv


def crossed_cases():
    disturbance = number("p4", "disturbance", "occurrence_time")
    published = list(scenarios())
    locations = [
        (name, alert) for name, alert, failed, recovery in published
        if alert is not None and failed is None and recovery == disturbance
    ]
    recovery_times = sorted({
        recovery for _, alert, failed, recovery in published
        if alert is not None and failed is not None
    })
    for recovery, (location, alert), failed in product(recovery_times, locations, range(len(VEHICLES))):
        yield f"{location}_V{failed + 1}_recovery_{recovery:g}", alert, failed, recovery


def scenario_key(row):
    return (row["policy"], int(row["failed_vehicle"]), float(row["recovery_s"]),
            *(float(row[name]) for name in ("new_alert_x_m", "new_alert_y_m", "new_alert_altitude_m")))


def check_published_overlap(rows):
    existing = {
        scenario_key(row): row for row in read("B_P4.csv")
        if row["failed_vehicle"] and row["new_alert_x_m"]
    }
    keys = {scenario_key(row) for row in rows}
    assert len(keys) == len(rows) and existing.keys() <= keys
    for row in rows:
        original = existing.get(scenario_key(row))
        if original is not None:
            assert all(float(original[name]) == row[name] for name in (
                "successes", "alerts", "completion_ratio", "latest_start_s",
            )), ("Published score mismatch", row["scenario"], row["policy"])
    return len(existing) // 2


def main():
    nominal = json.loads((RESULTS / "B_timelines.json").read_text(encoding="utf-8"))
    nominal_pairs = verify_nominal_records(read("B_P2_schedules.csv"), nominal)
    plan = [
        Visit(**(entry | {
            "path": tuple(tuple(point) for point in entry["path"]),
            "station": tuple(entry["station"]),
        }))
        for entry in nominal["nominal"]
    ]
    rows, timelines = solve_p4(plan, cases=crossed_cases())
    traces = json.dumps({"nominal": nominal["nominal"], "scenarios": timelines}, indent=2)
    verify_scenario_records(rows, json.loads(traces), nominal_pairs)
    overlap = check_published_overlap(rows)
    write_csv("B_P4_cross.csv", rows)
    (RESULTS / "B_P4_cross_timelines.json").write_text(traces + "\n", encoding="utf-8")
    print(f"P4 crossed replay passed for {len(rows) // 2} cases, including {overlap} published cases.")


if __name__ == "__main__":
    main()

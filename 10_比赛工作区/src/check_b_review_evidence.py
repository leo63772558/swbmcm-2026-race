"""Check completeness and arithmetic in published B review evidence."""

import argparse
import csv
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def audit(rows, horizon):
    groups = defaultdict(dict)
    for row in rows:
        policies = groups[row["scenario"]]
        if row["policy"] in policies:
            raise ValueError(f"Duplicate scenario and policy: {row}")
        policies[row["policy"]] = row

    results = []
    for scenario, pair in groups.items():
        if set(pair) != {"keep", "reschedule"}:
            raise ValueError(f"Missing paired policy for {scenario}")
        keep, replan = pair["keep"], pair["reschedule"]
        for key in ("failed_vehicle", "recovery_s", "alerts", "new_alert_x_m",
                    "new_alert_y_m", "new_alert_altitude_m"):
            if keep[key] != replan[key]:
                raise ValueError(f"Different {key} for {scenario}")
        for row in (keep, replan):
            done, total = int(row["successes"]), int(row["alerts"])
            latest = Decimal(row["latest_start_s"])
            if not 0 <= done <= total or float(row["completion_ratio"]) != done / total:
                raise ValueError(f"Inconsistent completion ratio for {scenario}")
            if not (0 <= latest < horizon if done == total else latest == horizon):
                raise ValueError(f"Inconsistent latest start for {scenario}")

        gain = int(replan["successes"]) - int(keep["successes"])
        delta = Decimal(replan["latest_start_s"]) - Decimal(keep["latest_start_s"])
        outcome = ("completion win" if gain > 0 else "completion loss") if gain else (
            "timing win" if delta < 0 else "timing loss" if delta > 0 else "tie"
        )
        paired = bool(keep["failed_vehicle"] and keep["new_alert_x_m"])
        location = "/".join(keep[key] for key in
                            ("new_alert_x_m", "new_alert_y_m", "new_alert_altitude_m"))
        results.append({
            "scenario": scenario, "failed_vehicle": keep["failed_vehicle"],
            "alert_xyz_m": location if keep["new_alert_x_m"] else "",
            "recovery_s": keep["recovery_s"], "success_gain": gain,
            "latest_start_change_s": delta, "comparison": outcome,
            "failure_and_new_alert": int(paired),
        })
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    params = read_csv(Path(__file__).resolve().parents[1] / "data" / "B题题面参数.csv")
    horizon = next(Decimal(row["value"]) for row in params
                   if (row["group"], row["entity"], row["parameter"])
                   == ("p4", "evaluation", "window_end"))
    rows = audit(read_csv(args.source), horizon)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(dict(Counter(row["comparison"] for row in rows)))
    combinations = defaultdict(set)
    for row in rows:
        if row["failure_and_new_alert"]:
            combinations[row["recovery_s"]].add((row["failed_vehicle"], row["alert_xyz_m"]))
    print("Distinct failure/location pairs by recovery time:",
          {time: len(pairs) for time, pairs in combinations.items()})


if __name__ == "__main__":
    main()

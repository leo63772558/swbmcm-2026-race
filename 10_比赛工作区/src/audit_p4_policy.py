"""Compare keeping, unconditional replanning, and model-based selection."""

import csv
from collections import Counter

from problem_b_geometry import ROOT


def score(row):
    return float(row["completion_ratio"]), -float(row["latest_start_s"])


def main():
    results = ROOT / "results"
    grouped = {}
    with (results / "B_candidate_P4.csv").open(newline="") as file:
        for row in csv.DictReader(file):
            grouped.setdefault(row["scenario"], {})[row["policy"]] = row
    rows = []
    for scenario, outcomes in grouped.items():
        keep, replan = outcomes["keep"], outcomes["reschedule"]
        metadata = ("recovery_s", "failed_vehicle", "new_alert_x_m", "new_alert_y_m", "alerts")
        assert all(keep[key] == replan[key] for key in metadata)
        kept, replanned = score(keep), score(replan)
        chosen = "reschedule" if replanned > kept else "keep"
        selected = score(outcomes[chosen])
        assert selected >= kept
        rows.append({
            "scenario": scenario, "selected": chosen,
            "keep_completion": kept[0], "replan_completion": replanned[0],
            "selected_completion": selected[0], "keep_latest_s": -kept[1],
            "replan_latest_s": -replanned[1], "selected_latest_s": -selected[1],
            "replan_vs_keep": "better" if replanned > kept else "worse" if replanned < kept else "tied",
            "selected_vs_keep": "better" if selected > kept else "tied",
        })
    with (results / "B_P4_policy_comparison.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    for field in ("replan_vs_keep", "selected_vs_keep"):
        print(field, dict(Counter(row[field] for row in rows)))


if __name__ == "__main__":
    main()

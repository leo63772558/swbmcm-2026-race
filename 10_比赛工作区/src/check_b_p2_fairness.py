"""Controlled replays of the existing P2(2) policies. AI-assisted (OpenAI Codex)."""

from argparse import ArgumentParser
import csv
from dataclasses import asdict
from functools import cache
from pathlib import Path
from unittest.mock import patch

from check_problem_b import read, verify_visits
import solve_problem_b as solver


BEAM_WIDTH = 20
GREEDY_WIDTH = 1
DEFAULT_OUTPUT = solver.RESULTS / "B_P2_fairness.csv"
ORIGINAL_STATION_OPTIONS = solver.station_options


@cache
def reachable_options(state, goal):
    total = len(solver.candidate_stations(goal))
    return tuple(ORIGINAL_STATION_OPTIONS(state, goal, total))


def prescreen(state, goal, count, screen):
    options = reachable_options(state, goal)
    if screen == "arrival":
        options = sorted(options)
    return options[:count]


def static_pools(count):
    """Build each target pool from both screens and the five initial states."""
    return {
        goal: frozenset(
            record[2]
            for state in solver.INITIAL
            for screen in ("arrival", "ready")
            for record in prescreen(state, goal, count, screen)
        )
        for goal in solver.TARGETS.values()
    }


def replay(select_options, limit, probe, beam_width=BEAM_WIDTH):
    schedules = {}
    # Only replace station prescreening for the duration of this audit.
    with patch.object(solver, "station_options", select_options):
        for policy, nearest, width in (("beam", False, beam_width), ("nearest", True, GREEDY_WIDTH)):
            visits = solver.solve_schedule(
                solver.INITIAL, solver.TARGETS, nearest=nearest, beam_width=width, stations=limit,
            )
            records = [asdict(visit) for visit in visits]
            pairs = verify_visits(records, solver.TARGETS, solver.INITIAL, f"{probe}/{policy}")
            assert set(pairs) == set(solver.TARGETS), f"{probe}/{policy}: incomplete schedule"
            schedules[policy] = records
    return schedules


def trial_row(probe, screen, count, pool_sizes, schedules, beam_width, nearest_width):
    row = {
        "probe": probe,
        "screen": screen,
        "per_vehicle_k": count,
        **{f"fixed_pool_{name}_size": pool_sizes.get(name, "") for name in solver.TARGETS},
        "beam_width": beam_width,
        "nearest_width": nearest_width,
    }
    for policy, visits in schedules.items():
        starts = {visit["alert"]: float(visit["start"]) for visit in visits}
        critical = max(starts, key=starts.__getitem__)
        bottleneck = max(
            (visit for visit in visits if visit["alert"] == critical),
            key=lambda visit: float(visit["ready"]),
        )
        row.update({
            **{f"{policy}_{name}_start_s": starts[name] for name in solver.TARGETS},
            f"{policy}_latest_start_s": starts[critical],
            f"{policy}_critical_alert": critical,
            f"{policy}_critical_vehicle": int(bottleneck["vehicle"]) + 1,
            f"{policy}_critical_depart_s": float(bottleneck["depart"]),
            f"{policy}_critical_drive_s": float(bottleneck["arrival"]) - float(bottleneck["depart"]),
            f"{policy}_critical_slew_s": float(bottleneck["ready"]) - float(bottleneck["arrival"]),
        })
    row["nearest_minus_beam_s"] = row["nearest_latest_start_s"] - row["beam_latest_start_s"]
    return row


def audit():
    source = read("B_P2_schedules.csv")
    published = {policy: [row for row in source if row["policy"] == policy] for policy in ("beam", "nearest")}
    rows = [trial_row("published", "different", "beam: 3 or 8; nearest: 3", {}, published, "5 or 20", 1)]

    for count, width in ((2, BEAM_WIDTH), (3, BEAM_WIDTH), (3, 5)):
        pools = static_pools(count)
        sizes = {name: len(pools[goal]) for name, goal in solver.TARGETS.items()}

        def fixed_options(state, goal, _):
            return [record for record in reachable_options(state, goal) if record[2] in pools[goal]]

        probe = f"fixed_initial_union_k{count}_w{width}"
        schedules = replay(fixed_options, max(sizes.values()), probe, beam_width=width)
        assert all(
            visit["station"] in pools[solver.TARGETS[visit["alert"]]]
            for visits in schedules.values() for visit in visits
        )
        rows.append(trial_row("fixed_initial_union", "both", count, sizes, schedules, width, GREEDY_WIDTH))

    for count in (3, 8):
        for screen in ("arrival", "ready"):
            def common_options(state, goal, _):
                return prescreen(state, goal, count, screen)

            schedules = replay(common_options, count, f"common_dynamic_{screen}_k{count}")
            rows.append(trial_row("common_dynamic", screen, count, {}, schedules, BEAM_WIDTH, GREEDY_WIDTH))
    return rows


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    rows = audit()
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} P2 comparison rows to {args.output}")


if __name__ == "__main__":
    main()

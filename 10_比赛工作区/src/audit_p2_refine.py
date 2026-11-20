"""Independent spatial sensitivity check around the existing P2 schedule."""

import ast
import csv
from dataclasses import asdict
import json
from math import cos, isfinite, pi, sin

from problem_b_geometry import OBSERVE, ROOT, SPEED, TARGETS, road_clear, route, slew_time, visible
from check_problem_b import verify_scenario_records
from solve_problem_b import INITIAL, Visit, accuracy, solve_p4, validate_visits


def rebuild(groups, stations):
    states = list(INITIAL)
    visits = []
    for alert, indices in groups:
        first, second = indices
        goal = TARGETS[alert]
        positions = [stations[i] for i in indices]
        if any(not visible(point, goal) or not road_clear(point, point) for point in positions):
            return None
        if not isfinite(accuracy(*positions, goal)[0]):
            return None
        legs = []
        for i in (first, second):
            vehicle, point = i[0], stations[i]
            origin, depart = states[vehicle]
            distance, path = route(origin, point)
            if not isfinite(distance):
                return None
            arrival = depart + distance / SPEED
            slew = slew_time(point, goal)
            legs.append((vehicle, point, path, depart, arrival, arrival + slew, slew))
        start = max(leg[5] for leg in legs)
        end = start + OBSERVE
        for vehicle, point, path, depart, arrival, ready, slew in legs:
            visit = Visit(vehicle, alert, point, path, depart, arrival, ready, start, end, end + slew)
            states[vehicle] = point, visit.reset
            visits.append(visit)
    return tuple(visits)


def score(plan):
    return max(v.start for v in plan), sum(v.start for v in plan), sum(v.reset for v in plan)


def refine(groups, positions):
    incumbent = rebuild(groups, positions)
    start = score(incumbent)[0]
    moves = [(key,) for key in positions]
    for vehicle in {key[0] for key in positions}:
        visits = tuple(key for key in positions if key[0] == vehicle)
        if len(visits) > 1:
            moves.append(visits)
    for step in (8, 4, 2, 1, .5, .25, .125, .0625, .03125):
        offsets = [(step * cos(heading * pi / 8), step * sin(heading * pi / 8))
                   for heading in range(16)]
        for _ in range(50):
            improved = False
            for move in moves:
                for dx, dy in offsets:
                    candidate = dict(positions)
                    for key in move:
                        x, y = positions[key]
                        candidate[key] = (x + dx, y + dy)
                    plan = rebuild(groups, candidate)
                    if plan and score(plan) < score(incumbent):
                        incumbent, positions = plan, candidate
                        improved = True
            if not improved:
                break
    validate_visits(incumbent, TARGETS)
    return start, incumbent


def main():
    results = ROOT / "results"
    with (results / "B_P2_schedules.csv").open(newline="") as source:
        rows = list(csv.DictReader(source))
    plans = {}
    for policy in ("beam", "nearest"):
        original = [row for row in rows if row["policy"] == policy]
        groups, stations = {}, {}
        for row in original:
            key = int(row["vehicle"]), row["alert"]
            groups.setdefault(row["alert"], []).append(key)
            stations[key] = ast.literal_eval(row["station"])
        start, refined = refine(tuple(groups.items()), stations)
        plans[policy] = {"before_s": start, "after_s": score(refined)[0],
                         "visits": [asdict(visit) for visit in refined]}
        print(policy, start, score(refined)[0], flush=True)
    best = min(plans, key=lambda key: plans[key]["after_s"])
    visits = [Visit(**row) for row in plans[best]["visits"]]
    outcomes, timelines = solve_p4(visits)
    scores = results / "B_candidate_P4.csv"
    with scores.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=outcomes[0])
        writer.writeheader()
        writer.writerows(outcomes)
    with scores.open(newline="") as file:
        verify_scenario_records(list(csv.DictReader(file)), {"scenarios": timelines})
    (results / "B_candidate_timelines.json").write_text(
        json.dumps(timelines, indent=2) + "\n", encoding="utf-8"
    )
    (results / "B_candidate_schedule.json").write_text(
        json.dumps({"best_seed": best, "candidates": plans}, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

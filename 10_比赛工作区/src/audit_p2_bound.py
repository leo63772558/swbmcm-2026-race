"""Independent continuous-domain lower bound for the nominal P2 schedule."""

import csv
import json
from itertools import permutations

import numpy as np

from problem_b_geometry import (
    DEPTH, HEIGHT, OBSERVE, PAN_SPEED, PITCH_SPEED, RADIUS, ROOT, SPEED,
    TARGETS, VEHICLES, WIDTH, minimum_radius,
)


def boxes(step):
    x, y = np.meshgrid(np.arange(RADIUS, WIDTH - RADIUS, step),
                       np.arange(RADIUS, DEPTH - RADIUS, step))
    lower = np.column_stack((x.ravel(), y.ravel()))
    upper = np.minimum(lower + step, (WIDTH - RADIUS, DEPTH - RADIUS))
    return lower, upper


def minimum_distance(a, b, c, d):
    separation = np.maximum(np.maximum(a - d, c - b), 0)
    return np.hypot(separation[..., 0], separation[..., 1])


def relax_alert(lower, upper, goal):
    xy = np.array(goal[:2])
    delta_lo, delta_hi = xy - upper, xy - lower
    delta_far = np.maximum(abs(delta_lo), abs(delta_hi))
    far = np.hypot(delta_far[:, 0], delta_far[:, 1])
    near_y = np.maximum(np.maximum(delta_lo[:, 1], -delta_hi[:, 1]), 0)
    max_x = delta_hi[:, 0]
    yaw = np.degrees(np.arctan2(np.where(max_x < 0, delta_far[:, 1], near_y), max_x))
    pitch = np.degrees(np.arctan2(goal[2] - HEIGHT, far))
    slew = np.maximum(yaw / PAN_SPEED, pitch / PITCH_SPEED)
    slew[far + 1e-10 < minimum_radius(goal)] = np.inf
    return slew


def lower_bound(step, incumbent):
    lo, hi = boxes(step)
    homes = np.array(VEHICLES)
    travel = minimum_distance(lo[None, :, :], hi[None, :, :],
                              homes[:, None, :], homes[:, None, :]) / SPEED
    slew = {name: relax_alert(lo, hi, goal) for name, goal in TARGETS.items()}
    ready = {name: travel + value[None, :] for name, value in slew.items()}
    earliest = {name: values.min(axis=1) for name, values in ready.items()}
    any_pair = max(np.sort(values)[1] for values in earliest.values())
    best_chain = np.inf
    for first, second in permutations(TARGETS, 2):
        for vehicle in range(len(homes)):
            others = np.arange(len(homes)) != vehicle
            partner_first = earliest[first][others].min()
            partner_second = earliest[second][others].min()
            first_depart = np.maximum(ready[first][vehicle], partner_first) + OBSERVE + slew[first]
            a = np.flatnonzero(first_depart <= incumbent + 1e-8)
            b = np.flatnonzero(ready[second][vehicle] <= incumbent + 1e-8)
            if not a.size or not b.size:
                continue
            for block in np.array_split(a, max(1, (a.size + 127) // 128)):
                transfer = minimum_distance(lo[block, None, :], hi[block, None, :],
                                            lo[None, b, :], hi[None, b, :]) / SPEED
                end = first_depart[block, None] + transfer + slew[second][b]
                best_chain = min(best_chain, max(end.min(), partner_second))
    return max(any_pair, best_chain) - 1e-8


def main():
    results = ROOT / "results"
    candidate = json.loads((results / "B_candidate_schedule.json").read_text(encoding="utf-8"))
    incumbent = candidate["candidates"][candidate["best_seed"]]["after_s"]
    rows = []
    for width in (2, 1, .5, .25):
        bound = lower_bound(width, incumbent)
        assert np.isfinite(bound) and 0 < bound <= incumbent + 1e-8
        rows.append((width, len(boxes(width)[0]), bound, incumbent, incumbent - bound,
                     100 * (incumbent - bound) / bound))
        print(rows[-1], flush=True)
    with (results / "B_P2_bound.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("cell_m", "cells", "lower_s", "incumbent_s", "gap_s", "gap_pct_of_lower"))
        writer.writerows(rows)


if __name__ == "__main__":
    main()

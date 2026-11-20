"""Stage 2: independent area, routing, and probability diagnostics.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Evidence for internal team review.
"""
from argparse import ArgumentParser
from collections import deque
from math import degrees, dist, hypot, isfinite, radians, sqrt, tan
from random import Random

import b_revision_geometry as rounded
import b_revision_probability as probability
import problem_b_geometry as model
from b_revision_data import DEFAULT_OUTPUT, read_json, write_csv, write_json


def polygon_span(y, polygon):
    values = []
    for p, q in zip(polygon, polygon[1:] + polygon[:1]):
        if min(p[1], q[1]) <= y <= max(p[1], q[1]):
            if q[1] == p[1]:
                values.extend((p[0], q[0]))
            else:
                values.append(p[0] + (y-p[1]) * (q[0]-p[0]) / (q[1]-p[1]))
    return (min(values), max(values)) if values else None


def body_span(y, box):
    x0, x1, y0, y1, _ = box
    height_gap = max(y0-y, 0.0, y-y1)
    if height_gap >= model.RADIUS:
        return None
    dx = sqrt(model.RADIUS**2 - height_gap**2)
    return x0-dx, x1+dx


def components(cells, diagonals):
    unvisited = set(cells)
    count = 0
    offsets = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if diagonals:
        offsets += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    while unvisited:
        pending = deque([unvisited.pop()])
        count += 1
        while pending:
            i, j = pending.popleft()
            for a, b in offsets:
                p = (i+a, j+b)
                if p in unvisited:
                    unvisited.remove(p)
                    pending.append(p)
    return count


def grid(step, offset, goal, polygons, *, map_details=False):
    counts = dict.fromkeys(("body", "elevation", "los", "intersection"), 0)
    nx, ny = round(model.WIDTH/step), round(model.DEPTH/step)
    radius = model.minimum_radius(goal)
    xs = [(i+offset)*step for i in range(nx)]
    good = set()
    spans = []
    for j in range(ny):
        y = (j+offset)*step
        blocked = [hit for poly in polygons if (hit := polygon_span(y, poly))]
        inflated = [hit for box in model.BUILDINGS if (hit := body_span(y, box))]
        start = None
        for i, x in enumerate(xs):
            body = model.in_field((x,y)) and not any(a < x < b for a,b in inflated)
            elevation = (x-goal[0])**2+(y-goal[1])**2 >= radius**2
            los = not any(a <= x <= b for a,b in blocked)
            feasible = body and elevation and los
            for name, indicator in (("body", body), ("elevation", elevation),
                                    ("los", los), ("intersection", feasible)):
                counts[name] += indicator
            if map_details:
                if feasible:
                    good.add((i,j))
                    if start is None:
                        start = i
                if start is not None and (not feasible or i == nx-1):
                    spans.append([j, start, i if feasible else i-1])
                    start = None
    result = {"method": "point_grid", "step_m": step, "phase": offset, "sample_count": nx*ny,
              **{f"{k}_area_m2": v*step**2 for k,v in counts.items()},
              "components_4": components(good, False) if map_details else "",
              "components_8": components(good, True) if map_details else "",
              "ci_lo_m2": "", "ci_hi_m2": "", "seed": ""}
    return result, {"step_m": step, "phase": offset, "runs": spans}


def p1_area(out):
    goal = model.TARGETS["T1"]
    polygons = rounded.shadows(goal)
    rows = []
    for spacing, offset in ((1,.5), (.5,.5), (.5,.25), (.25,.5), (.25,.25), (.125,.5), (.1,.5)):
        item, image = grid(spacing, offset, goal, polygons,
                           map_details=spacing in (.25, .5))
        if (spacing, offset) == (.5,.5):
            write_json(out / "P1_grid_map.json", image)
        rows.append(item)
    samples, seed = 250_000, 261305012
    rng = Random(seed)
    hits = sum(model.visible((rng.uniform(0, model.WIDTH), rng.uniform(0, model.DEPTH)), goal)
               for _ in range(samples))
    area = model.WIDTH*model.DEPTH
    interval = probability.wilson(hits, samples, 1.95996398454)
    assert interval[0]*area <= rows[-1]["intersection_area_m2"] <= interval[1]*area
    rows.append({**dict.fromkeys(rows[0], ""), "method": "fixed_seed_MC", "sample_count": samples,
                 "intersection_area_m2": hits/samples*area,
                 "ci_lo_m2": interval[0]*area, "ci_hi_m2": interval[1]*area, "seed": seed})
    write_csv(out / "P1_area.csv", rows)

    duration = 0.0
    sensitivity = []
    for variable, baseline in (("height_m", goal[2]), ("radius_m", model.RADIUS),
                               ("pitch_cap_deg", model.PITCH_MAX)):
        factors = (.8, .9, 1, 1.1, 1.2) if variable != "pitch_cap_deg" else (.8, .9, 1, 1.05, 1.1)
        for factor in factors:
            trial = baseline*factor
            g = (*goal[:2], trial) if variable == "height_m" else goal
            body = trial if variable == "radius_m" else model.RADIUS
            pitch = trial if variable == "pitch_cap_deg" else model.PITCH_MAX
            r = (g[2] - model.HEIGHT) / tan(radians(pitch))
            arcs = rounded.feasible_arcs(g, r, body_radius=body)
            sensitivity.append({"parameter": variable, "scale": factor, "value": trial,
                                "lower_range_m": r, "feasible_witness": bool(arcs),
                                "quality_at_bound_m_inv": 1/r if arcs else "",
                                "arc_length_m": sum((b-a)*r for a,b,_,_ in arcs),
                                "angular_components": len(arcs)})
    assert all(row["feasible_witness"] for row in sensitivity if row["scale"] == 1)
    write_csv(out / "P1_sensitivity.csv", sensitivity)
    print(f"P1 area: 0.1 m grid {rows[-2]['intersection_area_m2']:.3f} m^2; {samples:,} sample check passed")


def route_audit(out):
    rows = []
    for target, goal in model.TARGETS.items():
        for vehicle, home in enumerate(model.VEHICLES, 1):
            for point in rounded.stations(goal):
                metres, path = rounded.route(home, point)
                old_length, old_path = model.route(home, point)
                assert path and isfinite(metres)
                assert dist(path[0], home) < 1e-9 and dist(path[-1], point) < 1e-9
                legs = list(zip(path, path[1:]))
                margin = min(rounded.clearance(a,b) for a,b in legs)
                assert margin >= -1e-8 and abs(metres-sum(dist(a,b) for a,b in legs)) < 1e-8
                if old_path:
                    assert metres <= old_length+1e-8
                rows.append({"target": target, "vehicle": vehicle, "x_m": point[0], "y_m": point[1],
                             "aabb_distance_m": old_length if old_path else "",
                             "rounded_verified_distance_m": metres, "min_rounded_clearance_m": margin,
                             "saving_m": max(0, old_length-metres) if old_path else "",
                             "aabb_reachable": bool(old_path),
                             "route_type": "direct" if len(path) == 2 else "checked_graph_detour"})
    write_csv(out / "Route_clearance_comparison.csv", rows)
    improved = [r for r in rows if r["saving_m"] != "" and r["saving_m"] > 1e-8]
    summary = {"compared_routes": len(rows), "shorter_paths": len(improved),
               "restored_endpoints": sum(not row["aabb_reachable"] for row in rows),
               "maximum_saving_m": max((r["saving_m"] for r in improved), default=0),
               "minimum_margin_m": min(r["min_rounded_clearance_m"] for r in rows),
               "method": "Exact Euclidean segment feasibility; finite graph upper bounds for detours"}
    write_json(out / "Route_summary.json", summary)
    print("Rounded route audit", summary)
    return summary


def main(out):
    source = read_json(out / "priority_1.json")
    assert source["contact_checks"]["body_contact"] == "allowed"
    p1_area(out)
    routing = route_audit(out)
    p3 = probability.run(out)
    write_json(out / "priority_2.json", {"routing": routing, "p3": p3})
    print("Priority 2 checks passed.")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=type(DEFAULT_OUTPUT), default=DEFAULT_OUTPUT)
    main(parser.parse_args().out / "results")

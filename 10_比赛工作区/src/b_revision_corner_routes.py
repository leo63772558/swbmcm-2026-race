"""Check the radius-1.5 m corner approximation on the routed nominal detour.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: implementation and QA.
"""
from argparse import ArgumentParser
from math import acos, atan2, degrees, dist, hypot, pi, tau

import b_revision_geometry as rounded
import problem_b_geometry as model
from b_revision_data import DEFAULT_OUTPUT, read_csv, read_json, write_csv


def _compare_b3_northwest(path):
    """Compare the archived V3 route to the exact tangent-arc path at B3."""
    start, waypoint, finish = path
    x0, _, _, y1, _ = model.BUILDINGS[2]
    corner = (x0, y1)
    radius = model.RADIUS
    assert waypoint[0] < x0 and waypoint[1] > y1
    assert rounded.point_segment_distance(corner, start, finish) < radius

    start_angle = atan2(start[1] - y1, start[0] - x0)
    finish_angle = atan2(finish[1] - y1, finish[0] - x0)
    start_offset = acos(radius / dist(start, corner))
    finish_offset = acos(radius / dist(finish, corner))
    entry_angle = (start_angle + start_offset) % tau
    exit_angle = (finish_angle - finish_offset) % tau
    clockwise_span = (start_angle - finish_angle - start_offset - finish_offset) % tau
    assert pi / 2 <= entry_angle < exit_angle <= pi
    span = exit_angle - entry_angle

    # For a blocked chord, both shortest disk detours have the same two
    # straight tangent lengths. Only the boundary arc length differs.
    assert span <= clockwise_span
    entry = rounded.point_on_circle(corner, radius, entry_angle)
    exit_point = rounded.point_on_circle(corner, radius, exit_angle)
    assert rounded.road_clear(start, entry) and rounded.road_clear(exit_point, finish)

    # On the northwest quarter circle, distance to B3 is identically R.
    # Its enclosing box is inside the field inset and clears every other building.
    arc_x0, arc_x1 = x0 - radius, x0
    arc_y0, arc_y1 = y1, y1 + radius
    assert model.in_field((arc_x0, arc_y0)) and model.in_field((arc_x1, arc_y1))
    for index, (bx0, bx1, by0, by1, _) in enumerate(model.BUILDINGS, 1):
        if index != 3:
            dx = max(bx0 - arc_x1, arc_x0 - bx1, 0)
            dy = max(by0 - arc_y1, arc_y0 - by1, 0)
            assert hypot(dx, dy) >= radius

    graph_in, graph_out = dist(start, waypoint), dist(waypoint, finish)
    tangent_in, arc, tangent_out = dist(start, entry), radius * span, dist(exit_point, finish)
    graph_length = graph_in + graph_out
    tangent_arc_length = tangent_in + arc + tangent_out
    gap = graph_length - tangent_arc_length
    assert gap >= -1e-10
    return {
        "building": "B3",
        "corner": "northwest",
        "corner_x_m": x0,
        "corner_y_m": y1,
        "offset_radius_m": radius,
        "start_x_m": start[0],
        "start_y_m": start[1],
        "finish_x_m": finish[0],
        "finish_y_m": finish[1],
        "graph_waypoint_x_m": waypoint[0],
        "graph_waypoint_y_m": waypoint[1],
        "graph_in_m": graph_in,
        "graph_out_m": graph_out,
        "tangent_entry_deg": degrees(entry_angle),
        "tangent_exit_deg": degrees(exit_angle),
        "arc_span_deg": degrees(span),
        "tangent_in_m": tangent_in,
        "arc_m": arc,
        "tangent_out_m": tangent_out,
        "graph_length_m": graph_length,
        "tangent_arc_length_m": tangent_arc_length,
        "absolute_gap_m": gap,
        "relative_gap_pct": 100 * gap / tangent_arc_length,
    }


def main(out_results):
    p1 = read_json(out_results / "P1_geometry.json")["ties"]
    precision, = read_csv(out_results / "P2_precision.csv")
    precision_paths = read_json(out_results / "P2_precision_routes.json")
    dispatch = read_json(out_results / "P2_main_plans.json")
    nominal = [
        *((f"P1 {tie}", int(row["vehicle"]), "T1", row["path"]) for tie, row in p1.items()),
        *(("P2(1)", int(precision[f"vehicle_{i}"]), "T2", path)
          for i, path in enumerate(precision_paths, 1)),
        *((f"P2(2) {policy}", v["vehicle"] + 1, v["alert"], v["path"])
          for policy in ("beam", "nearest") for v in dispatch[policy]),
    ]
    rows = []
    for problem, vehicle, alert, path in nominal:
        points = [tuple(point) for point in path]
        assert len(points) >= 2
        assert all(rounded.road_clear(a, b) for a, b in zip(points, points[1:]))
        if len(points) > 2:
            assert (problem, vehicle, alert) == ("P2(1)", 3, "T2")
            rows.append({"problem": problem, "vehicle": vehicle, "alert": alert,
                         **_compare_b3_northwest(points)})
    assert len(rows) == 1, "Expected exactly one routed nominal detour"
    write_csv(out_results / "P2_corner_arc_comparison.csv", rows)
    print(f"Corner arc comparison: {len(rows)} detour in {len(nominal)} checked routes")
    return rows


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=type(DEFAULT_OUTPUT), default=DEFAULT_OUTPUT)
    main(parser.parse_args().out / "results")

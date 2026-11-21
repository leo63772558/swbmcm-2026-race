"""Stage 1: cross-check contact, the approved P1 tie, T2 covariance and clocks.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Evidence for internal team review.
"""
from argparse import ArgumentParser
from math import atan2, degrees, dist, hypot, isclose, nextafter, pi, radians, sqrt, tan
from random import Random

import b_revision_geometry as rounded
import problem_b_geometry as model
from b_revision_data import DEFAULT_OUTPUT, SOURCE_RESULTS, case_parameters, read_csv, window_score
from b_revision_data import write_csv, write_json
from check_problem_b import verify_localization_boundaries
from solve_problem_b import accuracy


def verify_contacts():
    b = model.BUILDINGS[1]
    x0, x1, y0, y1, _ = b
    r = model.RADIUS
    sample = (x1 + 0.8*r, y1 + 0.8*r)
    assert rounded.road_clear(sample, sample) and not model.road_clear(sample, sample)
    assert model.vehicle_fits(sample)
    contact = (x1 + r, (y0 + y1) / 2)
    assert rounded.road_clear(contact, contact)
    inside = (contact[0] - 1e-5, contact[1])
    assert not rounded.road_clear(inside, inside)
    assert not rounded.road_clear((r - 1e-5, r), (r, r))
    assert rounded.road_clear((r, r), (r, r))
    rect = ((0, 1), (0, 1), (0, 1))
    fixtures = (
        ("face", (-1, .5, 1), (2, .5, 1), True),
        ("edge", (-1, 0, 1), (2, 0, 1), True),
        ("vertex", (-1, -1, 2), (0, 0, 1), True),
        ("height_gap", (-1, .5, 1 + 1e-5), (2, .5, 1 + 1e-5), False),
        ("finite_segment", (-2, .5, .5), (-1, .5, .5), False),
    )
    for _, a, z, expected in fixtures:
        assert model.segment_hits_box(a, z, rect) is expected
    assert abs(rounded.segment_rect_distance((x1+r, y0), (x1+r, y1), b) - r) < 1e-10
    return {"body_contact": "allowed", "los_contact": "blocked",
            "three_dimensional_fixtures": len(fixtures), "aabb_false_rejection_xy": sample}


def p1_checks(out):
    goal = model.TARGETS["T1"]
    r = model.minimum_radius(goal)
    arcs = rounded.feasible_arcs(goal, r)
    assert arcs and all(b >= a for a, b, _, _ in arcs)
    shade = rounded.shadows(goal)
    rng = Random(2613050)
    for _ in range(5000):
        point = rng.uniform(0, model.WIDTH), rng.uniform(0, model.DEPTH)
        for box, polygon in zip(model.BUILDINGS, shade):
            x0, x1, y0, y1, h = box
            blocked = model.segment_hits_box((*point, model.HEIGHT), goal, ((x0, x1), (y0, y1), (0, h)))
            assert blocked == rounded.in_shadow(point, polygon)
    for a, b, lc, rc in arcs:
        for theta, allowed in ((a, lc), ((a+b)/2, True), (b, rc)):
            p = rounded.point_on_circle(goal[:2], r, theta)
            assert model.visible(p, goal) is allowed
    choices, branches = rounded.tie_checks(goal, r, arcs)
    for record in choices.values():
        assert 0 <= record["bound_width_s"] < 0.0001
    assert all(isclose(c["quality_m_inv"], 1/r, abs_tol=1e-12) for c in choices.values())
    source, = read_csv(SOURCE_RESULTS / "B_P1.csv")
    assert all(isclose(choices["ready"][k], float(source[k]), abs_tol=1e-8)
               for k in ("range_m", "quality_m_inv", "elevation_deg"))
    arcs_deg = [{"start_deg": degrees(a), "end_deg": degrees(b), "start_included": lc,
                 "end_included": rc, "length_m": r * (b-a)} for a, b, lc, rc in arcs]
    pitch = []
    for cap in (model.PITCH_MAX, model.PITCH_MAX - 1, model.PITCH_MAX - 20):
        cap_r = (goal[2] - model.HEIGHT) / tan(radians(cap))
        cap_arcs = rounded.feasible_arcs(goal, cap_r)
        assert cap_arcs, "Quality bound lacks a feasible witness at this pitch cap"
        pitch.append({"elevation_ceiling_deg": cap, "range_m": cap_r, "quality_m_inv": 1/cap_r,
                      "relative_quality_loss": 1-r/cap_r,
                      "feasible_arc_length_m": sum((b-a)*cap_r for a, b, _, _ in cap_arcs)})
    write_csv(out / "P1_station.csv", ({"tie": mode, **{k: v for k, v in row.items() if k != "path"}}
                                       for mode, row in choices.items()))
    write_csv(out / "P1_arc.csv", arcs_deg)
    write_csv(out / "P1_ready_branches.csv", branches)
    write_csv(out / "P1_pitch_checks.csv", pitch)
    write_json(out / "P1_geometry.json", {"ties": choices, "arcs": arcs_deg, "shadows": shade})
    print("P1", choices["ready"]["vehicle"], f'ready {choices["ready"]["ready_s"]:.9f} s',
          f'bound gap {choices["ready"]["bound_width_s"]:.6g} s',
          f'one-degree quality loss {100*pitch[1]["relative_quality_loss"]:.4f}%')


def p2_precision_checks(out):
    target = model.TARGETS["T2"]
    archived, = read_csv(SOURCE_RESULTS / "B_P2_localization.csv")
    verify_localization_boundaries(archived)
    stations = [(float(archived[f"x_{i}_m"]), float(archived[f"y_{i}_m"])) for i in (1, 2)]
    step = 0.0001
    # Independently differentiate the bearings of the recorded pair.
    gradients = []
    for x, y in stations:
        dx, dy = target[0] - x, target[1] - y
        dd = []
        for vx, vy in ((step, 0), (0, step)):
            plus, minus = atan2(dy+vy, dx+vx), atan2(dy-vy, dx-vx)
            dd.append(((plus-minus+pi) % (2*pi) - pi) / (2*step))
        gradients.append(dd)
    (a, b), (c, d) = gradients
    det = a*d-b*c
    sigma = radians(model.number("p2_1", "bearing", "error_std"))
    s = (sigma/det)**2
    cov_xx, cov_xy, cov_yy = s*(d*d+b*b), -s*(d*c+b*a), s*(c*c+a*a)
    rms = sqrt(cov_xx+cov_yy)
    r = model.minimum_radius(target)
    value, gamma = accuracy(*stations, target)
    assert isclose(rms, value, rel_tol=1e-8) and isclose(value, float(archived["horizontal_rms_m"]))
    assert isclose(value, sqrt(2)*r*sigma, abs_tol=1e-10)
    assert isclose(gamma, 90, abs_tol=1e-8)
    travel = []
    paths = []
    for i, p in enumerate(stations, start=1):
        origin = model.VEHICLES[int(archived[f"vehicle_{i}"]) - 1]
        length, path = rounded.route(origin, p)
        assert model.visible(p, target) and path
        assert isclose(dist(p, target[:2]), r, abs_tol=1e-9)
        assert model.angles(p, target)[1] <= model.PITCH_MAX + 1e-9
        assert length/model.SPEED <= model.number("p2_1", "vehicle", "travel_time_max")
        travel.append(length/model.SPEED)
        paths.append(path)
    row = {**archived, "metric": "local_first_order_horizontal_rms", "cov_xx_m2": cov_xx,
           "cov_xy_m2": cov_xy, "cov_yy_m2": cov_yy, "finite_difference_rms_m": rms,
           "existing_lower_bound_m": sqrt(2)*r*sigma,
           "rounded_travel_1_s": travel[0], "rounded_travel_2_s": travel[1]}
    write_csv(out / "P2_precision.csv", [row])
    write_json(out / "P2_precision_routes.json", paths)
    pitch_rows = []
    travel_limit = model.number("p2_1", "vehicle", "travel_time_max")
    for cap in (model.PITCH_MAX, model.PITCH_MAX - 1):
        cap_range = (target[2] - model.HEIGHT) / tan(radians(cap))
        cap_stations = [
            tuple(t + (p - t) * (cap_range / r) for p, t in zip(station, target[:2]))
            for station in stations
        ]
        cap_rms, cap_angle = accuracy(*cap_stations, target)
        assert isclose(cap_angle, 90.0, abs_tol=1e-8)
        assert isclose(cap_rms, sqrt(2) * cap_range * sigma, abs_tol=1e-10)
        pitch_row = {
            "elevation_ceiling_deg": cap,
            "minimum_radius_m": cap_range,
            "crossing_deg": cap_angle,
            "horizontal_rms_m": cap_rms,
            "rms_increase_pct": 100 * (cap_rms / value - 1),
        }
        for i, station in enumerate(cap_stations, 1):
            vehicle = int(archived[f"vehicle_{i}"])
            length, path = rounded.route(model.VEHICLES[vehicle - 1], station)
            assert model.visible(station, target) and path
            assert isclose(model.angles(station, target)[1], cap, abs_tol=1e-9)
            assert length / model.SPEED <= travel_limit
            pitch_row.update({f"vehicle_{i}": vehicle, f"x_{i}_m": station[0], f"y_{i}_m": station[1],
                              f"travel_{i}_s": length / model.SPEED})
        pitch_rows.append(pitch_row)
    write_csv(out / "P2_precision_pitch_checks.csv", pitch_rows)
    print(f"P2(1) finite difference RMS {rms:.9f} m; both pitch witnesses meet the 30 s limit")


def verify_clocks(out):
    d = model.number("p4", "disturbance", "occurrence_time")
    absolute = model.number("p4", "outage_formula", "recovery_time_max")
    duration = model.number("p4", "outage_prose", "duration_max")
    window_start, horizon, incomplete = model.read_values(
        "p4", "evaluation", "window_start", "window_end", "incomplete_latest_start")
    items = [
        case_parameters("fault_only", ("fault_only", None, 4, d), d, horizon, "no_outage"),
        case_parameters("absolute_cap", ("absolute_cap", None, None, absolute), d, horizon, "absolute"),
        case_parameters("duration_cap", ("duration_cap", None, None, d+duration), d, horizon, "duration"),
    ]
    assert items[1]["outage_duration_s"] == absolute-d
    assert items[2]["outage_duration_s"] == duration
    assert items[0]["failure_s"] == d and items[0]["absolute_recovery_s"] is None
    requested = {"T1", "T2"}
    near_end = nextafter(horizon, -float("inf"))
    scores = [
        window_score({"T1": d, "T2": at}, requested, window_start, horizon, incomplete)
        for at in (near_end, horizon, nextafter(horizon, float("inf")))
    ]
    assert scores == [(2, 1, near_end), (1, .5, incomplete), (1, .5, incomplete)]
    write_json(out / "P4_clock_checks.json", {"clock_examples": items, "window_scores": scores})
    return items


def main(out):
    out.mkdir(parents=True, exist_ok=True)
    contacts = verify_contacts()
    p1_checks(out)
    p2_precision_checks(out)
    clocks = verify_clocks(out)
    write_json(out / "priority_1.json", {"contact_checks": contacts, "clock_checks": len(clocks)})
    print("Priority 1 boundary/metric/clock checks passed.")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=type(DEFAULT_OUTPUT), default=DEFAULT_OUTPUT)
    main(parser.parse_args().out / "results")

"""Route clearance and geometric checks for the team's selected disk model.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: implementation and QA.
"""
from functools import cache
from itertools import product
from math import acos, atan2, cos, dist, hypot, pi, sin, sqrt

import problem_b_geometry as base


GEOMETRY_TOL = 1e-9  # metres for clearances; radians for deduplicating arc breaks


def dot(first, second):
    return sum(a * b for a, b in zip(first, second))


def sub(first, second):
    return tuple(a - b for a, b in zip(first, second))


def cross(first, second):
    return first[0] * second[1] - first[1] * second[0]


def rect_distance(point, box):
    x, y = point
    x0, x1, y0, y1, _ = box
    return hypot(max(x0 - x, 0.0, x - x1), max(y0 - y, 0.0, y - y1))


def point_segment_distance(point, start, end):
    delta = sub(end, start)
    square = dot(delta, delta)
    t = min(1.0, max(0.0, dot(sub(point, start), delta) / square)) if square else 0.0
    return hypot(*(a - b - t * d for a, b, d in zip(point, start, delta)))


def segment_rect_distance(start, end, box):
    """Euclidean segment to filled AABB distance; includes finite endpoints."""
    x0, x1, y0, y1, _ = box
    if base.segment_hits_box(start, end, ((x0, x1), (y0, y1))):
        return 0.0
    return min(rect_distance(start, box), rect_distance(end, box),
               *(point_segment_distance(corner, start, end)
                 for corner in product((x0, x1), (y0, y1))))


def clearance(start, end):
    """Minimum signed margin to all building footprints and field walls."""
    field = min(*(p[0] for p in (start, end)), *(p[1] for p in (start, end)),
                *(base.WIDTH - p[0] for p in (start, end)),
                *(base.DEPTH - p[1] for p in (start, end)))
    return min(field, *(segment_rect_distance(start, end, b) for b in base.BUILDINGS)) - base.RADIUS


@cache
def road_clear(start, end):
    """Contact of the body is allowed. LOS contact uses the closed 3D slabs."""
    if not base.in_field(start) or not base.in_field(end):
        return False
    for box in base.BUILDINGS:
        x0, x1, y0, y1, _ = box
        if (max(start[0], end[0]) <= x0 - base.RADIUS or
                min(start[0], end[0]) >= x1 + base.RADIUS or
                max(start[1], end[1]) <= y0 - base.RADIUS or
                min(start[1], end[1]) >= y1 + base.RADIUS):
            continue
        if segment_rect_distance(start, end, box) < base.RADIUS - GEOMETRY_TOL:
            return False
    return True


@cache
def route(start, end):
    """Use an exact-clearance direct leg, else shortcut the legacy graph route.

    Exact for direct legs. Detours are feasible upper bounds from the existing
    graph. The existing graph's terminal connections also use the rounded
    clearance, so an admissible corner endpoint can attach to that graph.
    """
    if road_clear(start, end):
        return dist(start, end), (start, end)
    if not road_clear(start, start) or not road_clear(end, end):
        return float("inf"), ()
    length, path = base.route(start, end)
    if not path:
        # The legacy AABB screen excluded this endpoint. Reuse its graph.
        length, path = min(
            ((a + base.ROAD_COST[i][j] + b, (start, *base.ROAD_PATH[i][j], end))
             for i, a in connections(start) for j, b in connections(end)
             if base.ROAD_PATH[i][j]), default=(float("inf"), ()))
    if not path:
        return length, path
    # Minimise length on the DAG of Euclidean-safe shortcuts of this path.
    best = [(0.0, (path[0],))]
    for j, point in enumerate(path[1:], 1):
        best.append(min(
            (cost + dist(previous, point), prefix + (point,))
            for previous, (cost, prefix) in zip(path[:j], best)
            if road_clear(previous, point)
        ))
    return best[-1]


@cache
def connections(point):
    return tuple((i, dist(point, via)) for i, via in enumerate(base.WAYPOINTS)
                 if road_clear(point, via))


@cache
def stations(goal):
    # Same sampling settings as the archived candidate generator.
    radius = base.minimum_radius(goal)
    ring = (p for offset in (0, 1, 3, 7, 12, 20, 32)
            for p in base.ring(goal, radius + offset, 15))
    grid = product(range(4, int(base.WIDTH), 8), range(4, int(base.DEPTH), 8))
    return tuple(p for p in (*ring, *grid) if base.visible(p, goal) and road_clear(p, p))


def hull(points):
    def chain(sequence):
        half = []
        for p in sequence:
            while len(half) >= 2 and cross(sub(half[-1], half[-2]), sub(p, half[-1])) <= 0:
                half.pop()
            half.append(p)
        return half[:-1]
    unique = sorted(set(points))
    return tuple(chain(unique) + chain(reversed(unique)))


def shadows(goal):
    """Independent closed shadow polygons on the camera plane for high targets."""
    gx, gy, gz = goal
    if gz <= max(b[-1] for b in base.BUILDINGS):
        raise ValueError("Closed finite projections require target above all roofs")
    projected = []
    for x0, x1, y0, y1, h in base.BUILDINGS:
        projected.append(hull(
            (gx + (x - gx) * (gz - base.HEIGHT) / (gz - z),
             gy + (y - gy) * (gz - base.HEIGHT) / (gz - z))
            for x, y, z in product((x0, x1), (y0, y1), (base.HEIGHT, h))))
    return tuple(projected)


def in_shadow(point, polygon):
    return all(cross(sub(b, a), sub(point, a)) >= -GEOMETRY_TOL
               for a, b in zip(polygon, polygon[1:] + polygon[:1]))


def circle_line_angles(center, radius, start, end):
    direction = sub(end, start)
    length = hypot(*direction)
    normal = (-direction[1] / length, direction[0] / length)
    signed = dot(sub(start, center), normal) / radius
    if abs(signed) > 1.0:
        return ()
    heading = atan2(normal[1], normal[0])
    turn = acos(signed)
    return heading - turn, heading + turn


def circle_circle_angles(center, radius, corner, offset):
    distance = dist(center, corner)
    if not distance:
        return ()  # Coincident or concentric, so there is no isolated breakpoint.
    c = (radius**2 + distance**2 - offset**2) / (2 * radius * distance)
    if abs(c) > 1.0:
        return ()
    angle = atan2(*reversed(sub(corner, center)))
    turn = acos(c)
    return angle - turn, angle + turn


def point_on_circle(center, radius, angle):
    return center[0] + radius * cos(angle), center[1] + radius * sin(angle)


def feasible_arcs(goal, radius, body_radius=base.RADIUS):
    """Boundary partition for verification. Extraneous breakpoints are merged."""
    center = goal[:2]
    shade = shadows(goal)
    boxes = [(x0 - body_radius, x1 + body_radius, y0 - body_radius, y1 + body_radius)
             for x0, x1, y0, y1, _ in base.BUILDINGS]
    boxes.append((body_radius, base.WIDTH - body_radius, body_radius, base.DEPTH - body_radius))
    lines = [((x, 0), (x, 1)) for x0, x1, _, _ in boxes for x in (x0, x1)]
    lines.extend(((0, y), (1, y)) for _, _, y0, y1 in boxes for y in (y0, y1))
    lines.extend((a, b) for p in shade for a, b in zip(p, p[1:] + p[:1]))
    roots = [0.0, 2*pi]
    roots.extend(angle % (2*pi) for a, b in lines for angle in circle_line_angles(center, radius, a, b))
    for x0, x1, y0, y1, _ in base.BUILDINGS:
        roots.extend(angle % (2*pi) for corner in product((x0, x1), (y0, y1))
                     for angle in circle_circle_angles(center, radius, corner, body_radius))
    breaks = []
    for value in sorted(roots):
        if not breaks or value - breaks[-1] > GEOMETRY_TOL:
            breaks.append(value)
    breaks[-1] = 2*pi

    def allowed(theta):
        p = point_on_circle(center, radius, theta)
        return (body_radius <= p[0] <= base.WIDTH - body_radius
                and body_radius <= p[1] <= base.DEPTH - body_radius
                and all((rect_distance(p, b) >= body_radius - GEOMETRY_TOL if body_radius
                         else not (b[0] < p[0] < b[1] and b[2] < p[1] < b[3]))
                        for b in base.BUILDINGS)
                and not any(in_shadow(p, poly) for poly in shade))

    arcs = []
    for left, right in zip(breaks, breaks[1:]):
        if allowed((left + right) / 2):
            if arcs and arcs[-1][1] == left and allowed(left):
                arcs[-1] = arcs[-1][0], right
            else:
                arcs.append((left, right))
    if len(arcs) > 1 and arcs[0][0] == 0.0 and arcs[-1][1] == 2*pi and allowed(0.0):
        arcs = arcs[1:-1] + [(arcs[-1][0], arcs[0][1] + 2*pi)]
    isolated = [(theta, theta) for theta in breaks[:-1] if allowed(theta)
                and not any(a - GEOMETRY_TOL <= theta + wrap <= b + GEOMETRY_TOL
                            for a, b in arcs for wrap in (0.0, 2*pi))]
    return [(a, b, allowed(a), allowed(b)) for a, b in sorted(arcs + isolated)]


def tie_checks(goal, radius, arcs, spacing=0.002):
    """Bound the existing ready/arrival criteria from below using straight distance."""
    from math import ceil, degrees, radians

    candidates = {"ready": [], "arrival": []}
    lower = dict.fromkeys(candidates, float("inf"))
    branches = []
    critical = sorted({0.0, 360.0, 720.0, *(v + wrap for v in
                      (180 - base.PITCH_MAX, 180 + base.PITCH_MAX)
                      for wrap in (0, 360))})
    for start, stop, include_start, include_stop in arcs:
        a, b = degrees(start), degrees(stop)
        splits = [a, *(c for c in critical if a < c < b), b]
        for left, right in zip(splits, splits[1:]):
            n = max(1, ceil((right - left) / spacing))
            best = {key: [None for _ in base.VEHICLES] for key in candidates}
            h = (right - left) / n
            for j in range(n + 1):
                theta = left + h * j
                point = point_on_circle(goal[:2], radius, radians(theta))
                slew = base.slew_time(point, goal)
                for v, home in enumerate(base.VEHICLES):
                    drive = dist(home, point) / base.SPEED
                    for mode, score in (("ready", drive + slew), ("arrival", drive)):
                        record = (score, drive, v, theta, point, slew)
                        if best[mode][v] is None or record < best[mode][v]:
                            best[mode][v] = record
            for mode, rows in best.items():
                rate = radius * pi / (180 * base.SPEED) + (1 / base.PAN_SPEED if mode == "ready" else 0)
                bounds = min(row[0] for row in rows) - rate * h / 2
                lower[mode] = min(lower[mode], bounds)
                for score, _, v, theta, point, slew in rows:
                    if (not include_start and theta == a) or (not include_stop and theta == b):
                        continue
                    if base.visible(point, goal):
                        metres, path = route(base.VEHICLES[v], point)
                        if path:
                            drive = metres / base.SPEED
                            result = drive + slew if mode == "ready" else drive
                            candidates[mode].append((result, drive, v, theta, point, slew, path))
            # Branch table uses the straight-line lower envelope for the specific V4 check.
            value, drive, v, theta, point, slew = best["ready"][3]
            metres, path = route(base.VEHICLES[v], point)
            branches.append({
                "vehicle": v + 1, "from_deg": left, "to_deg": right, "argmin_grid_deg": theta,
                "straight_lower_s": value - (radius * pi / (180 * base.SPEED) + 1/base.PAN_SPEED) * h/2,
                "feasible_ready_s": metres / base.SPEED + slew if path and base.visible(point, goal) else "",
                "argmin_is_direct": bool(path) and abs(metres / base.SPEED - drive) < 1e-8,
            })
    rows = {}
    for mode, entries in candidates.items():
        score, drive, v, theta, point, slew, path = min(entries)
        rows[mode] = {
            "vehicle": v + 1, "azimuth_deg": theta % 360, "x_m": point[0], "y_m": point[1],
            "range_m": radius, "elevation_deg": base.angles(point, goal)[1], "quality_m_inv": 1 / radius,
            "arrival_s": drive, "slew_s": slew, "ready_s": drive + slew,
            "criterion_lower_s": lower[mode], "criterion_upper_s": score,
            "bound_width_s": score - lower[mode], "path": path,
        }
    return rows, branches

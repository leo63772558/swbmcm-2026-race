"""Problem B geometry and routing. AI-assisted implementation (OpenAI Codex)."""

import csv
from functools import cache
from math import atan2, cos, degrees, dist, hypot, radians, sin, tan
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
with (ROOT / "data" / "B题题面参数.csv").open(encoding="utf-8-sig", newline="") as source:
    INPUT = {
        (row["group"], row["entity"], row["parameter"]): row["value"]
        for row in csv.DictReader(source)
    }


def number(group, entity, parameter):
    return float(INPUT[group, entity, parameter])


def read_values(group, entity, *parameters):
    return tuple(number(group, entity, name) for name in parameters)


WIDTH, DEPTH = read_values("field", "field", "width", "length")
ORIGIN = read_values("field", "O", "x", "y")
RADIUS, SPEED = read_values("vehicle", "vehicle", "radius", "speed")
HEIGHT = number("camera", "camera", "height")
PITCH_MIN, PITCH_MAX, PAN_SPEED, PITCH_SPEED = read_values(
    "camera", "gimbal", "elevation_min", "elevation_max", "pan_speed_max", "tilt_speed_max"
)
OBSERVE = number("observation", "joint", "duration")
BUILDINGS = tuple(
    read_values("building", f"B{i}", "x_min", "x_max", "y_min", "y_max", "height")
    for i in range(1, 6)
)
VEHICLES = tuple(read_values("vehicle", f"V{i}", "initial_x", "initial_y") for i in range(1, 6))


def target(azimuth, radius, height):
    angle = radians(azimuth)
    return ORIGIN[0] + radius * cos(angle), ORIGIN[1] + radius * sin(angle), height


TARGETS = {
    f"T{i}": target(*read_values("alert", f"T{i}", "azimuth", "horizontal_range", "altitude"))
    for i in range(1, 4)
}


def segment_hits_box(start, end, bounds):
    """Closed segment and closed box intersection in 2D or 3D."""
    entry, exit_ = 0.0, 1.0
    for a, b, (low, high) in zip(start, end, bounds, strict=True):
        delta = b - a
        if abs(delta) < 1e-12:
            if not low <= a <= high:
                return False
            continue
        t1, t2 = sorted(((low - a) / delta, (high - a) / delta))
        entry, exit_ = max(entry, t1), min(exit_, t2)
        if entry > exit_ + 1e-12:
            return False
    return True


def in_field(point):
    x, y = point
    return RADIUS <= x <= WIDTH - RADIUS and RADIUS <= y <= DEPTH - RADIUS


def vehicle_fits(point):
    x, y = point
    return in_field(point) and all(
        hypot(max(x0 - x, x - x1, 0), max(y0 - y, y - y1, 0)) >= RADIUS - 1e-10
        for x0, x1, y0, y1, _ in BUILDINGS
    )


def angles(point, goal):
    dx, dy, dz = goal[0] - point[0], goal[1] - point[1], goal[2] - HEIGHT
    return degrees(atan2(dy, dx)), degrees(atan2(dz, hypot(dx, dy)))


def visible(point, goal):
    pitch = angles(point, goal)[1]
    return (
        vehicle_fits(point)
        and PITCH_MIN - 1e-9 <= pitch <= PITCH_MAX + 1e-9
        and not any(
            segment_hits_box((*point, HEIGHT), goal, ((x0, x1), (y0, y1), (0, z)))
            for x0, x1, y0, y1, z in BUILDINGS
        )
    )


def slew_time(point, goal):
    pan, pitch = angles(point, goal)
    return max(abs(pan) / PAN_SPEED, abs(pitch) / PITCH_SPEED)


def minimum_radius(goal):
    return (goal[2] - HEIGHT) / tan(radians(PITCH_MAX))


ROAD_BLOCKS = tuple(
    ((x0 - RADIUS, x1 + RADIUS), (y0 - RADIUS, y1 + RADIUS))
    for x0, x1, y0, y1, _ in BUILDINGS
)


def road_clear(start, end):
    return all(not segment_hits_box(start, end, obstacle) for obstacle in ROAD_BLOCKS)


WAYPOINTS = tuple(
    (x, y) for (x0, x1), (y0, y1) in ROAD_BLOCKS
    for x in (x0 - 1e-3, x1 + 1e-3) for y in (y0 - 1e-3, y1 + 1e-3)
    if in_field((x, y)) and road_clear((x, y), (x, y))
)


def waypoint_routes():
    size = len(WAYPOINTS)
    weights = [[float("inf")] * size for _ in range(size)]
    paths = [[()] * size for _ in range(size)]
    for i, start in enumerate(WAYPOINTS):
        for j, end in enumerate(WAYPOINTS):
            if road_clear(start, end):
                weights[i][j] = dist(start, end)
                paths[i][j] = (start,) if i == j else (start, end)
    for k in range(size):
        for i in range(size):
            for j in range(size):
                candidate = weights[i][k] + weights[k][j]
                if candidate < weights[i][j]:
                    weights[i][j] = candidate
                    paths[i][j] = paths[i][k] + paths[k][j][1:]
    return weights, paths


ROAD_COST, ROAD_PATH = waypoint_routes()


@cache
def connections(point):
    return tuple(
        (i, dist(point, waypoint))
        for i, waypoint in enumerate(WAYPOINTS) if road_clear(point, waypoint)
    )


@cache
def route(start, end):
    if road_clear(start, end):
        return dist(start, end), (start, end)
    best, points = float("inf"), ()
    for i, a in connections(start):
        for j, b in connections(end):
            cost = a + ROAD_COST[i][j] + b
            if cost < best:
                best, points = cost, (start, *ROAD_PATH[i][j], end)
    return best, points


def route_position(points, distance):
    for start, end in zip(points, points[1:]):
        leg = dist(start, end)
        if leg > 0 and distance <= leg:
            fraction = max(0.0, distance / leg)
            return tuple(a + fraction * (b - a) for a, b in zip(start, end, strict=True))
        distance -= leg
    return points[-1]


def ring(goal, radius, step):
    for heading in range(0, 360, step):
        angle = radians(heading)
        yield goal[0] + radius * cos(angle), goal[1] + radius * sin(angle)


@cache
def candidate_stations(goal):
    base_radius = minimum_radius(goal)
    points = [
        point for offset in (0, 1, 3, 7, 12, 20, 32)
        for point in ring(goal, base_radius + offset, 15)
    ]
    points.extend((x, y) for x in range(4, int(WIDTH), 8) for y in range(4, int(DEPTH), 8))
    return tuple(point for point in points if visible(point, goal) and road_clear(point, point))

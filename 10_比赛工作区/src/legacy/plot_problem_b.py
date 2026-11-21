"""Vector figures from Problem B inputs and results. AI-assisted visualization (OpenAI Codex)."""

from itertools import groupby
from math import atan2, cos, degrees, floor, pi, sin

from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen.canvas import Canvas

from problem_b_geometry import BUILDINGS, DEPTH, ROOT, TARGETS, VEHICLES, WIDTH, number, visible


FIGURES = ROOT / "figures"
NAVY = HexColor("#122B40")
MUTED = HexColor("#455D71")
TEAL = HexColor("#0B6C70")
TEAL_LIGHT = HexColor("#D7ECE7")
BLUE = HexColor("#315E92")
RUST = HexColor("#AB452C")
PURPLE = HexColor("#675283")
OCHRE = HexColor("#826021")
GRID = HexColor("#DBE5ED")
WASH = HexColor("#F2F6F9")
BUILDING = HexColor("#899AAD")
ROUTE_STYLES = ((TEAL, ()), (RUST, (6, 2)), (PURPLE, (2, 2)), (BLUE, (6, 2, 2, 2)), (OCHRE, (4, 2)))


def label(pdf, x, y, value, *, size=12, color=NAVY, align="left", bold=False):
    pdf.setFillColor(color)
    pdf.setFont("TitleTimes" if bold else "BodyTimes", size)
    draw = {"left": pdf.drawString, "center": pdf.drawCentredString,
            "right": pdf.drawRightString}[align]
    draw(x, y, str(value))


def figure(name, width, height):
    return Canvas(str(FIGURES / name), pagesize=(width, height), invariant=1, pageCompression=1)


def segment(pdf, a, b, color=GRID, width=.75, dash=()):
    pdf.setStrokeColor(color)
    pdf.setLineWidth(width)
    pdf.setDash(dash)
    pdf.line(*a, *b)
    pdf.setDash()


def rectangle(pdf, x, y, w, h, fill):
    pdf.setFillColor(fill)
    pdf.rect(x, y, w, h, fill=1, stroke=0)


def dot(pdf, point, color, *, radius=3, hollow=False):
    pdf.setFillColor(white if hollow else color)
    pdf.setStrokeColor(color)
    pdf.setLineWidth(1.35)
    pdf.circle(*point, radius, fill=1, stroke=int(hollow))


def axes(pdf, x, y, w, h, x_range, y_range, xticks, yticks, x_label, y_label):
    xmin, xmax = x_range
    ymin, ymax = y_range

    def point(a, b):
        return x + w * (a - xmin) / (xmax - xmin), y + h * (b - ymin) / (ymax - ymin)

    rectangle(pdf, x, y, w, h, WASH)
    for tick, text in xticks:
        gx, _ = point(tick, ymin)
        segment(pdf, (gx, y), (gx, y + h))
        label(pdf, gx, y - 15, text, align="center", color=MUTED)
    for tick, text in yticks:
        _, gy = point(xmin, tick)
        segment(pdf, (x, gy), (x + w, gy))
        label(pdf, x - 6, gy - 4, text, align="right", color=MUTED)
    segment(pdf, (x, y), (x + w, y), MUTED, .85)
    segment(pdf, (x, y), (x, y + h), MUTED, .85)
    label(pdf, x + w / 2, y - 34, x_label, align="center", bold=True)
    if y_label:
        label(pdf, x, y + h + 13, y_label, bold=True)
    return point


def map_axes(pdf):
    ticks = [(n, n) for n in range(0, 101, 25)]
    return axes(pdf, 36, 47, 235, 235, (0, WIDTH), (0, DEPTH),
                ticks, ticks, "East (m)", "North (m)")


def draw_buildings(pdf, point):
    for i, (left, right, bottom, top, _) in enumerate(BUILDINGS, 1):
        x, y = point(left, bottom)
        end_x, end_y = point(right, top)
        rectangle(pdf, x, y, end_x - x, end_y - y, BUILDING)
        label(pdf, (x + end_x) / 2, (y + end_y) / 2 - 4, f"B{i}", align="center", color=NAVY)


def draw_map(p1, p2):
    pdf = figure("b_geometry.pdf", 455, 319)
    point = map_axes(pdf)
    grid = range(1, int(WIDTH))
    for north in range(1, int(DEPTH)):
        for observed, cells in groupby(grid, key=lambda east: visible((east, north), TARGETS["T1"])):
            if observed:
                run = list(cells)
                x, y = point(run[0] - .5, north - .5)
                xx, yy = point(run[-1] + .5, north + .5)
                rectangle(pdf, x, y, xx - x, yy - y, TEAL_LIGHT)
    draw_buildings(pdf, point)
    for name in ("T1", "T2", "T3"):
        x, y = point(*TARGETS[name][:2])
        dot(pdf, (x, y), NAVY)
        label(pdf, x + 7, y + (8 if name == "T1" else 3), name, bold=True)
    selected = point(float(p1["x_m"]), float(p1["y_m"]))
    dot(pdf, selected, RUST, radius=4.5, hollow=True)
    segment(pdf, selected, point(*TARGETS["T1"][:2]), RUST, 1.25)
    label(pdf, 300, 278, "T1 visibility", bold=True, size=14)
    rectangle(pdf, 301, 251, 11, 11, TEAL_LIGHT)
    label(pdf, 320, 251, "Observable grid (1 m)")
    dot(pdf, (306, 235), RUST, hollow=True)
    label(pdf, 320, 231, "Selected station")
    label(pdf, 300, 210, f"Range  {float(p1['range_m']):.3f} m", color=MUTED)
    segment(pdf, (300, 195), (441, 195))
    label(pdf, 300, 175, "T2 local geometry", bold=True, size=14)
    label(pdf, 300, 158, "Horizontal view", color=MUTED)
    rectangle(pdf, 300, 55, 141, 94, WASH)
    stations = [(float(p2[f"x_{i}_m"]), float(p2[f"y_{i}_m"])) for i in (1, 2)]
    target = TARGETS["T2"][:2]
    xs, ys = zip(*stations, target)
    mid_x, mid_y = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    scale = 1 / max((max(xs) - min(xs)) / 79, (max(ys) - min(ys)) / 64)

    def inset(x, y):
        return 372 + scale * (x - mid_x), 102 + scale * (y - mid_y)

    a, b = (inset(*station) for station in stations)
    q = inset(*target)
    segment(pdf, a, b, MUTED, 1.1, (3, 2))
    segment(pdf, a, q, TEAL, 1.65)
    segment(pdf, b, q, TEAL, 1.65)
    for i, xy in enumerate((a, b), 1):
        dot(pdf, xy, TEAL, hollow=True)
        label(pdf, xy[0] - 8, xy[1] - 3, f"S{i}", align="right", bold=True)
    dot(pdf, q, NAVY)
    label(pdf, q[0] + 7, q[1] + 1, "T2", bold=True)
    start = atan2(a[1] - q[1], a[0] - q[0])
    end = atan2(b[1] - q[1], b[0] - q[0])
    sweep = (end - start + pi) % (2 * pi) - pi
    radius = min(13, scale * float(p2["baseline_m"]) / 4)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(.9)
    pdf.arc(q[0] - radius, q[1] - radius, q[0] + radius, q[1] + radius,
            degrees(start), degrees(sweep))
    angle = start + sweep / 2
    label(pdf, q[0] + (radius + 9) * cos(angle), q[1] + (radius + 9) * sin(angle) - 4,
          f"{float(p2['crossing_deg']):g}°", color=TEAL, align="center", bold=True)
    label(pdf, 300, 34, f"Baseline {float(p2['baseline_m']):.2f} m", color=MUTED)
    pdf.save()


def draw_routes(visits):
    pdf = figure("b_routes.pdf", 455, 319)
    point = map_axes(pdf)
    draw_buildings(pdf, point)
    for v in visits:
        color, dash = ROUTE_STYLES[v["vehicle"]]
        for a, b in zip(v["path"], v["path"][1:]):
            segment(pdf, point(*a), point(*b), color, 2, dash)
        dot(pdf, point(*v["station"]), color, radius=4, hollow=True)
    for i, vehicle in enumerate(VEHICLES):
        color, _ = ROUTE_STYLES[i]
        x, y = point(*vehicle)
        dot(pdf, (x, y), color)
        label(pdf, x + 6, y - 13 if i == 0 else y + 4, f"V{i + 1}", bold=True, color=color)
    label(pdf, 299, 276, "Vehicle and alert order", bold=True, size=14)
    for i, (color, dash) in enumerate(ROUTE_STYLES):
        y = 252 - i * 20
        own = sorted((visit for visit in visits if visit["vehicle"] == i), key=lambda visit: visit["start"])
        alerts = " → ".join(visit["alert"] for visit in own)
        segment(pdf, (301, y + 4), (325, y + 4), color, 2, dash)
        label(pdf, 331, y, f"V{i + 1}", bold=True)
        label(pdf, 357, y, alerts)
        for previous, current in zip(own, own[1:]):
            if previous["station"] == current["station"]:
                dot(pdf, point(*current["station"]), color, radius=1.8)
    segment(pdf, (300, 155), (449, 155))
    dot(pdf, (307, 137), MUTED)
    dot(pdf, (307, 117), MUTED, radius=4, hollow=True)
    dot(pdf, (307, 97), MUTED, radius=4, hollow=True)
    dot(pdf, (307, 97), MUTED, radius=1.8)
    label(pdf, 322, 133, "Starting point")
    label(pdf, 322, 113, "Observation station")
    label(pdf, 322, 93, "Reused station")
    pdf.save()


def draw_timeline(rows):
    pdf = figure("b_timeline.pdf", 455, 309)
    start_limit = max(float(row["reset"]) for row in rows) + .75
    x0, x1 = 72, 435
    vehicles = range(len(VEHICLES))
    ticks = range(0, floor(start_limit) + 1, 5)

    def scale(t):
        return x0 + (x1 - x0) * t / start_limit

    phases = [
        ("Drive", "depart", "arrival", HexColor("#819DB8")),
        ("Slew", "arrival", "ready", HexColor("#DFAB68")),
        ("Wait", "ready", "start", HexColor("#CED6DF")),
        ("Observe", "start", "end", TEAL),
        ("Reset", "end", "reset", RUST),
    ]
    for i, (name, _, _, color) in enumerate(phases):
        x = 38 + i * 82
        rectangle(pdf, x, 286, 9, 9, color)
        label(pdf, x + 15, 285, name)
    for index, (policy, name) in enumerate((("beam", "Beam search"), ("nearest", "Nearest assignment"))):
        top = 249 - index * 117
        series = [row for row in rows if row["policy"] == policy]
        latest = max(float(row["start"]) for row in series)
        label(pdf, 16, top + 13, name, bold=True, size=14)
        label(pdf, x1, top + 13, f"Last start {latest:.2f} s", align="right", color=TEAL, bold=True)
        for i in vehicles:
            y = top - 17 * i
            rectangle(pdf, x0, y - 4, x1 - x0, 11, WASH if i % 2 == 0 else white)
            label(pdf, 64, y - 2, f"V{i + 1}", align="right", color=MUTED)
        for tick in ticks:
            segment(pdf, (scale(tick), top - 73), (scale(tick), top + 8))
        for row in series:
            y = top - 17 * int(row["vehicle"])
            for _, left, right, color in phases:
                a, b = scale(float(row[left])), scale(float(row[right]))
                if a == b:
                    continue
                rectangle(pdf, a, y - 4, b - a, 11, color)
                if left == "start":
                    label(pdf, (a + b) / 2, y - 2, row["alert"], align="center", color=white, bold=True)
        x = scale(latest)
        for i in vehicles:
            y = top - 17 * i
            segment(pdf, (x, y + 8), (x, y + 12), NAVY, 1)
        segment(pdf, (x, top - 74), (x, top - 73), NAVY, 1)
    for tick in ticks:
        label(pdf, scale(tick), 37, tick, align="center", color=MUTED)
    label(pdf, (x0 + x1) / 2, 16, "Time since first alert (s)", align="center", bold=True)
    pdf.save()


def draw_coverage(rows, threshold, audit):
    pdf = figure("b_coverage.pdf", 455, 263)
    tolerance = number("p3", "error", "absolute_error_max")
    requirement = number("p3", "error", "coverage_min")
    point = axes(pdf, 58, 52, 374, 161, (0, 120), (.70, 1.0),
                 [(x, x) for x in range(0, 121, 20)],
                 [(p / 100, f"{p}%") for p in (70, 80, 90, 100)],
                 "Cumulative travel (m)", f"Probability within ±{tolerance:g}°")
    segment(pdf, point(0, requirement), point(120, requirement), RUST, 1, (5, 3))
    segment(pdf, point(threshold, .70), point(threshold, requirement), MUTED, 1, (2, 3))
    path = pdf.beginPath()
    for i, row in enumerate(rows):
        xy = point(float(row["path_m"]), float(row["coverage"]))
        (path.moveTo if i == 0 else path.lineTo)(*xy)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(2.2)
    pdf.drawPath(path)
    for distance, estimate, low, high in audit:
        a, b = point(distance, low), point(distance, high)
        dot(pdf, point(distance, estimate), RUST, radius=2.5, hollow=True)
        segment(pdf, a, b, RUST, .8)
        for x, y in (a, b):
            segment(pdf, (x - 4, y), (x + 4, y), RUST, .8)
    label(pdf, *point(threshold + 3, .74), f"{threshold:.2f} m", color=TEAL, bold=True)
    label(pdf, *point(3, requirement - .029), f"{requirement:.0%} requirement", color=RUST)
    label(pdf, 431, 229, "Curve: quadrature · rings: Monte Carlo", align="right", color=MUTED)
    pdf.save()


def draw_parameter_region(p3):
    cap = float(p3["sigma_cap_m"])
    distance = float(p3["parameter_check_distance_m"])
    slope = cap / distance
    pdf = figure("b_parameters.pdf", 455, 263)
    point = axes(pdf, 52, 52, 378, 158, (0, .025), (0, 2),
                 [(k * .005, f"{k * .005:.3f}") for k in range(6)],
                 [(k / 2, f"{k / 2:.1f}") for k in range(5)],
                 "Growth coefficient b (m/m)", "Intercept a (m)")
    path = pdf.beginPath()
    path.moveTo(*point(0, 0))
    path.lineTo(*point(0, cap))
    path.lineTo(*point(slope, 0))
    path.close()
    pdf.setFillColor(TEAL_LIGHT)
    pdf.drawPath(path, fill=1, stroke=0)
    segment(pdf, point(0, cap), point(slope, 0), TEAL, 2)
    dot(pdf, point(0, cap), TEAL)
    dot(pdf, point(slope, 0), TEAL)
    label(pdf, *point(.002, .28), "Admissible pairs", color=TEAL, bold=True)
    label(pdf, *point(.0088, 1.53), f"a + {distance:.0f}b = {cap:.4f} m", bold=True)
    pdf.save()


def draw_disturbances(rows):
    cases = (
        ("new_1", "New alert 1"), ("failure_V1", "V1 failure"), ("failure_V5", "V5 failure"),
        ("outage_upper_time", "Outage only"), ("new_failure_V1", "New + V1 failure"),
        ("failure_outage_V1", "V1 failure + outage"), ("new_outage", "New + outage"),
        ("all_V1", "All three, V1"), ("all_duration_sensitivity", "All three, V2"),
    )
    pdf = figure("b_disturbances.pdf", 455, 324)
    lookup = {(r["scenario"], r["policy"]): r for r in rows}
    x0, x1 = 157, 310
    latest_left, latest_right = 379, 442
    top, spacing = 262, 24
    ticks = (0, .25, .5, .75, 1)

    def scale(value):
        return x0 + (x1 - x0) * value

    label(pdf, 16, 301, "Selected scenarios", bold=True)
    label(pdf, (x0 + x1) / 2, 301, "Completion rate", align="center", bold=True)
    label(pdf, 393, 301, "Latest start (s)", align="center", bold=True)
    label(pdf, latest_left, 283, "Keep", align="right", color=MUTED)
    label(pdf, latest_right, 283, "Replan", align="right", color=MUTED)
    for i, _ in enumerate(cases):
        if i % 2 == 0:
            rectangle(pdf, 12, top - i * spacing - 8, 431, 21, WASH)
    for tick in ticks:
        x = scale(tick)
        segment(pdf, (x, top - (len(cases) - 1) * spacing - 8), (x, top + 13))
        label(pdf, x, 45, f"{tick:.0%}", align="center", color=MUTED)
    for i, (name, display) in enumerate(cases):
        y = top - i * spacing
        keep = lookup[name, "keep"]
        replan = lookup[name, "reschedule"]
        if name in {"outage_upper_time", "all_V1", "all_duration_sensitivity"}:
            display += f" ({float(keep['recovery_s']):g} s recovery)"
        label(pdf, 17, y - 2, display, size=11)
        a, b = (scale(float(row["completion_ratio"])) for row in (keep, replan))
        segment(pdf, (a, y + 2), (b, y + 2), MUTED, 1.2)
        dot(pdf, (a, y + 2), RUST, radius=4.5, hollow=True)
        dot(pdf, (b, y + 2), TEAL, radius=2.5 if a == b else 3.6)
        first, second = float(keep["latest_start_s"]), float(replan["latest_start_s"])
        comparable = all(row["successes"] == row["alerts"] for row in (keep, replan))
        for index, (x, row, time) in enumerate(((latest_left, keep, first), (latest_right, replan, second))):
            complete = row["successes"] == row["alerts"]
            slower = index == 1 and comparable and second > first
            label(pdf, x, y - 2, f"{time:.2f}" if complete else f"{time:g}*",
                  align="right", color=RUST if slower else MUTED, bold=slower)
    segment(pdf, (13, 35), (442, 35))
    dot(pdf, (23, 17), RUST, hollow=True)
    label(pdf, 32, 13, "Keep plan")
    dot(pdf, (104, 17), TEAL)
    label(pdf, 113, 13, "Reschedule")
    label(pdf, 442, 13, "* Window cap because an alert remains incomplete", align="right", color=MUTED, size=11)
    pdf.save()

"""Vector figures generated from Problem B inputs and verified outputs."""

from math import floor

from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen.canvas import Canvas

from problem_b_geometry import BUILDINGS, DEPTH, ROOT, TARGETS, VEHICLES, WIDTH, visible


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
PALETTE = (TEAL, RUST, PURPLE, BLUE, OCHRE)


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
    for east in range(1, int(WIDTH)):
        for north in range(1, int(DEPTH)):
            if visible((east, north), TARGETS["T1"]):
                x, y = point(east - .5, north - .5)
                xx, yy = point(east + .5, north + .5)
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
    label(pdf, 320, 251, "Observable")
    dot(pdf, (306, 235), RUST, hollow=True)
    label(pdf, 320, 231, "Selected station")
    label(pdf, 300, 210, f"Range  {float(p1['range_m']):.3f} m", color=MUTED)
    segment(pdf, (300, 195), (441, 195))
    label(pdf, 300, 175, "T2 local geometry", bold=True, size=14)
    label(pdf, 300, 158, "Horizontal view", color=MUTED)
    rectangle(pdf, 300, 49, 141, 100, WASH)
    stations = [(float(p2[f"x_{i}_m"]), float(p2[f"y_{i}_m"])) for i in (1, 2)]
    target = TARGETS["T2"][:2]
    mid_y = sum(s[1] for s in stations) / 2

    def inset(x, y):
        return 339 + 8.9 * (x - stations[0][0]), 98 + 8.9 * (y - mid_y)

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
    label(pdf, 387, 64, f"{float(p2['crossing_deg']):.0f}°", color=TEAL, bold=True)
    pdf.save()


def draw_routes(visits):
    pdf = figure("b_routes.pdf", 455, 319)
    point = map_axes(pdf)
    draw_buildings(pdf, point)
    for v in visits:
        color = PALETTE[v["vehicle"]]
        for a, b in zip(v["path"], v["path"][1:]):
            segment(pdf, point(*a), point(*b), color, 2)
        dot(pdf, point(*v["station"]), color, radius=4, hollow=True)
    # The nominal task list interleaves vehicles, so inspect each vehicle's visits.
    for i, color in enumerate(PALETTE):
        own = [visit for visit in visits if visit["vehicle"] == i]
        for previous, current in zip(own, own[1:]):
            if previous["station"] == current["station"]:
                x, y = point(*current["station"])
                label(pdf, x + 8, y + 8, f"{previous['alert']} / {current['alert']}",
                      size=11, color=color, bold=True)
    for i, vehicle in enumerate(VEHICLES):
        x, y = point(*vehicle)
        dot(pdf, (x, y), PALETTE[i])
        label(pdf, x + 6, y + 4, f"V{i + 1}", bold=True, color=PALETTE[i])
    label(pdf, 299, 276, "Vehicle routes", bold=True, size=14)
    for i, color in enumerate(PALETTE):
        y = 252 - i * 20
        segment(pdf, (301, y + 4), (319, y + 4), color, 2)
        label(pdf, 327, y, f"Vehicle {i + 1}")
    segment(pdf, (300, 155), (441, 155))
    dot(pdf, (307, 136), MUTED)
    dot(pdf, (307, 114), MUTED, hollow=True)
    label(pdf, 322, 132, "Starting point")
    label(pdf, 322, 110, "Observation station")
    pdf.save()


def draw_timeline(rows):
    pdf = figure("b_timeline.pdf", 455, 309)
    start_limit = max(float(row["reset"]) for row in rows) + .75
    x0, x1 = 72, 435

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
        for i in range(5):
            y = top - 17 * i
            rectangle(pdf, x0, y - 4, x1 - x0, 11, WASH if i % 2 == 0 else white)
            label(pdf, 64, y - 2, f"V{i + 1}", align="right", color=MUTED)
        for tick in range(0, floor(start_limit) + 1, 5):
            segment(pdf, (scale(tick), top - 73), (scale(tick), top + 8))
        segment(pdf, (scale(latest), top - 74), (scale(latest), top + 8), NAVY, .9, (2, 2))
        for row in series:
            y = top - 17 * int(row["vehicle"])
            for _, left, right, color in phases:
                a, b = scale(float(row[left])), scale(float(row[right]))
                rectangle(pdf, a, y - 4, b - a, 11, color)
                if left == "start":
                    label(pdf, (a + b) / 2, y - 2, row["alert"], align="center", color=white, bold=True)
    for tick in range(0, floor(start_limit) + 1, 5):
        label(pdf, scale(tick), 37, tick, align="center", color=MUTED)
    label(pdf, (x0 + x1) / 2, 16, "Time since first alert (s)", align="center", bold=True)
    pdf.save()


def draw_coverage(rows, threshold, audit):
    pdf = figure("b_coverage.pdf", 455, 263)
    point = axes(pdf, 58, 52, 374, 161, (0, 120), (.70, 1.0),
                 [(x, x) for x in range(0, 121, 20)],
                 [(p / 100, f"{p}%") for p in (70, 80, 90, 100)],
                 "Cumulative travel (m)", "Probability within ±5°")
    segment(pdf, point(0, .95), point(120, .95), RUST, 1, (5, 3))
    segment(pdf, point(threshold, .70), point(threshold, .95), MUTED, 1, (2, 3))
    path = pdf.beginPath()
    for i, row in enumerate(rows):
        xy = point(float(row["path_m"]), float(row["coverage"]))
        (path.moveTo if i == 0 else path.lineTo)(*xy)
    pdf.setStrokeColor(TEAL)
    pdf.setLineWidth(2.2)
    pdf.drawPath(path)
    for distance, estimate, low, high in audit:
        a, b = point(distance, low), point(distance, high)
        segment(pdf, a, b, RUST, 1.1)
        dot(pdf, point(distance, estimate), RUST, radius=3.4, hollow=True)
    label(pdf, *point(threshold + 3, .74), f"{threshold:.2f} m", color=TEAL, bold=True)
    label(pdf, *point(3, .921), "95% requirement", color=RUST)
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
    dot(pdf, point(0, cap), TEAL, hollow=True)
    dot(pdf, point(slope, 0), TEAL, hollow=True)
    label(pdf, *point(.002, .28), "Admissible pairs", color=TEAL, bold=True)
    label(pdf, *point(.0088, 1.53), f"a + {distance:.0f}b = {cap:.4f} m", bold=True)
    pdf.save()


def draw_disturbances(rows):
    cases = (
        ("new_1", "New alert"), ("failure_V1", "V1 failure"), ("failure_V5", "V5 failure"),
        ("outage_upper_time", "Outage"), ("new_failure_V1", "New + V1 failure"),
        ("failure_outage_V1", "V1 failure + outage"), ("new_outage", "New + outage"),
        ("all_V1", "All three, V1"), ("all_duration_sensitivity", "Longer outage, all three"),
    )
    pdf = figure("b_disturbances.pdf", 455, 307)
    lookup = {(r["scenario"], r["policy"]): r for r in rows}
    x0, x1 = 158, 309

    def scale(value):
        return x0 + (x1 - x0) * (value - .45) / .55

    label(pdf, 16, 288, "Scenario", bold=True)
    label(pdf, 239, 288, "Completion", align="center", bold=True)
    label(pdf, 442, 288, "Last start (s)", align="right", bold=True)
    for i, (name, display) in enumerate(cases):
        y = 255 - i * 24
        if i % 2 == 0:
            rectangle(pdf, 12, y - 8, 431, 21, WASH)
        label(pdf, 17, y - 2, display, size=11)
        keep = lookup[name, "keep"]
        replan = lookup[name, "reschedule"]
        a, b = (scale(float(row["completion_ratio"])) for row in (keep, replan))
        segment(pdf, (a, y + 2), (b, y + 2), MUTED, 1.2)
        dot(pdf, (a, y + 2), RUST, radius=4, hollow=True)
        dot(pdf, (b, y + 2), TEAL, radius=3 if a == b else 4)
        first, second = float(keep["latest_start_s"]), float(replan["latest_start_s"])
        label(pdf, 440, y - 2, f"{first:.2f} → {second:.2f}", align="right",
              color=RUST if first < second else MUTED, bold=first < second)
    for proportion in (.5, .75, 1):
        label(pdf, scale(proportion), 46, f"{proportion:.0%}", align="center", color=MUTED)
    segment(pdf, (13, 35), (442, 35))
    dot(pdf, (23, 17), RUST, hollow=True)
    label(pdf, 32, 13, "Keep plan")
    dot(pdf, (104, 17), TEAL)
    label(pdf, 113, 13, "Reschedule")
    label(pdf, 442, 13, "Reported time: keep → reschedule", align="right", color=MUTED, size=11)
    pdf.save()

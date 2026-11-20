"""Generate an English draft and vector figures. AI-assisted (OpenAI Codex)."""

import csv
from collections import Counter
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from problem_b_geometry import BUILDINGS, ROOT, TARGETS, VEHICLES, visible


FIGURES, PAPER, RESULTS = (ROOT / name for name in ("figures", "paper", "results"))
INK = colors.HexColor("#172D43")
TEAL = colors.HexColor("#136C74")
RED = colors.HexColor("#B24933")
EQUATIONS = {
    "Observation Region and Station Selection": (
        "r ≥ (H − h) / tan βmax,     Q = 1/r",
        r"r \ge (H-h)/\tan\beta_{\max},\qquad Q=1/r",
    ),
    "Dual-Station Localization for T2": (
        "RMS ≈ σθ √(r₁² + r₂²) / |sin γ|",
        r"\operatorname{RMS}\approx"
        r"\frac{\sigma_\theta\sqrt{r_1^2+r_2^2}}{|\sin\gamma|}",
    ),
    "Multi-Alert Vehicle Scheduling": (
        "tstart = max(tready,1, tready,2),     objective = min max tstart",
        r"t_{\mathrm{start},j}=\max_{i\in A_j}t_{\mathrm{ready},i,j},\qquad"
        r"\min\max_j t_{\mathrm{start},j}",
    ),
    "Horizontal Pointing Error": (
        "Δψ = wrap(atan2(−Y, r − X) + ε₀ + εc)",
        r"\Delta\psi=\operatorname{wrap}\left(\operatorname{atan2}(-Y,r-X)"
        r"+\epsilon_0+\epsilon_c\right)",
    ),
    "Rescheduling After Disturbances": (
        "η = k/N; maximize η, then minimize tlast",
        r"\operatorname{lex\,max}\;(\eta,-t_{\rm last}),\qquad\eta=k/N",
    ),
}


def read(name):
    with (RESULTS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def fmt(value, digits=2):
    return f"{float(value):.{digits}f}"


def base_chart(name, x_max, y_max, x_label, y_label, width=440, height=250):
    chart = canvas.Canvas(str(FIGURES / name), pagesize=(width, height))
    chart.setStrokeColor(INK)
    chart.setFillColor(INK)
    chart.setFont("Times-Roman", 11)
    chart.line(43, 31, width - 16, 31)
    chart.line(43, 31, 43, height - 25)
    chart.drawCentredString(width / 2, 8, x_label)
    chart.drawString(43, height - 16, y_label)

    def point(x, y):
        return 43 + x / x_max * (width - 59), 31 + y / y_max * (height - 56)

    return chart, point


def draw_map(p1, p2):
    chart, point = base_chart("b_geometry.pdf", 100, 100, "East (m)", "North (m)", 300, 297)
    for n in range(0, 101, 20):
        x, y0 = point(n, 0)
        x0, y = point(0, n)
        chart.drawCentredString(x, y0 - 13, str(n))
        chart.drawRightString(x0 - 5, y - 3, str(n))
    chart.setFillColor(colors.HexColor("#D0E8E5"))
    for x in range(1, 100):
        for y in range(1, 100):
            if visible((x, y), TARGETS["T1"]):
                chart.rect(*point(x - .5, y - .5), 2.41, 2.41, fill=1, stroke=0)
    chart.setFillColor(colors.HexColor("#4B5563"))
    for i, (left, right, bottom, top, _) in enumerate(BUILDINGS, 1):
        x, y = point(left, bottom)
        right_x, top_y = point(right, top)
        chart.rect(x, y, right_x - x, top_y - y, fill=1, stroke=0)
        chart.setFillColor(colors.white)
        chart.drawCentredString((x + right_x) / 2, (y + top_y) / 2 - 3, f"B{i}")
        chart.setFillColor(colors.HexColor("#4B5563"))
    chart.setFillColor(INK)
    for i, vehicle in enumerate(VEHICLES, 1):
        x, y = point(*vehicle)
        chart.circle(x, y, 2, stroke=0, fill=1)
        chart.drawString(x + 3, y + 4, f"V{i}")
    chart.setFillColor(RED)
    for label, goal in TARGETS.items():
        x, y = point(*goal[:2])
        chart.circle(x, y, 3, stroke=0, fill=1)
        chart.drawString(x + 4, y - 10, label)
    chart.setStrokeColor(RED)
    chart.circle(*point(float(p1["x_m"]), float(p1["y_m"])), 4, stroke=1, fill=0)
    chart.setStrokeColor(TEAL)
    for index in (1, 2):
        station = point(float(p2[f"x_{index}_m"]), float(p2[f"y_{index}_m"]))
        chart.line(*station, *point(*TARGETS["T2"][:2]))
        chart.circle(*station, 2.5, stroke=1, fill=0)
    chart.save()


def draw_timeline(rows):
    last_reset = max(float(row["reset"]) for row in rows)
    chart, point = base_chart("b_timeline.pdf", last_reset + 1, 11.5, "Time (s)", "Timeline")
    bands = [("travel", "depart", "arrival", colors.HexColor("#B8CBDD")),
             ("slew", "arrival", "ready", colors.HexColor("#E9BB84")),
             ("wait", "ready", "start", colors.HexColor("#DDDDE0")),
             ("observe", "start", "end", TEAL), ("reset", "end", "reset", RED)]
    for tick in range(0, int(last_reset) + 1, 5):
        x, y = point(tick, 0)
        chart.drawCentredString(x, y - 13, str(tick))
    for index, (label, _, _, fill) in enumerate(bands):
        x = 127 + 59 * index
        chart.setFillColor(fill)
        chart.rect(x, 233, 8, 8, stroke=0, fill=1)
        chart.setFillColor(INK)
        chart.drawString(x + 10, 233, label)
    for policy, offset in (("beam", 6), ("nearest", 0)):
        for vehicle in range(5):
            _, y = point(0, offset + 5 - vehicle)
            chart.setFillColor(INK)
            chart.drawRightString(39, y - 3, f"{policy[0].upper()}-V{vehicle + 1}")
        for row in rows:
            if row["policy"] != policy:
                continue
            y_index = offset + 5 - int(row["vehicle"])
            for _, start, end, fill in bands:
                x, y = point(float(row[start]), y_index)
                next_x, _ = point(float(row[end]), y_index)
                chart.setFillColor(fill)
                chart.rect(x, y - 4, next_x - x, 8, stroke=0, fill=1)
                if start == "start":
                    chart.setFillColor(colors.white)
                    chart.setFont("Times-Roman", 8)
                    chart.drawCentredString((x + next_x) / 2, y - 2.6, row["alert"])
                    chart.setFont("Times-Roman", 11)
    chart.save()


def draw_coverage(rows):
    chart, point = base_chart("b_coverage.pdf", 120, .55, "Cumulative travel (m)", "Coverage")
    for y in (.5, .6, .7, .8, .9, 1):
        x, yy = point(0, y - .45)
        chart.drawRightString(x - 5, yy - 3, f"{y:.1f}")
    for x_tick in range(0, 121, 20):
        x, y = point(x_tick, 0)
        chart.drawCentredString(x, y - 13, str(x_tick))
    chart.setStrokeColor(RED)
    chart.setDash(4, 3)
    chart.line(*point(0, .50), *point(120, .50))
    chart.setDash()
    chart.setStrokeColor(TEAL)
    chart.setLineWidth(2)
    path = chart.beginPath()
    for i, row in enumerate(rows):
        where = point(float(row["path_m"]), float(row["coverage"]) - .45)
        (path.moveTo if i == 0 else path.lineTo)(*where)
    chart.drawPath(path)
    chart.save()


def draw_disturbances(rows):
    names = ("new_1", "failure_V1", "failure_V5", "outage_upper_time", "new_failure_V1",
             "failure_outage_V1", "new_outage", "all_V1", "all_duration_sensitivity")
    chart, point = base_chart("b_disturbances.pdf", 9, 1.1, "Scenario index", "Completion ratio")
    for tick in range(6):
        x, y = point(0, tick / 5)
        chart.drawRightString(x - 5, y - 3, f"{tick / 5:.1f}")
    for i, name in enumerate(names):
        chart.setFillColor(INK)
        x, _ = point(i + .5, 0)
        chart.drawCentredString(x, 17, str(i + 1))
        for row in rows:
            if row["scenario"] == name:
                left = x + (-14 if row["policy"] == "keep" else 1)
                _, top = point(i, float(row["completion_ratio"]))
                chart.setFillColor(RED if row["policy"] == "keep" else TEAL)
                chart.rect(left, 31, 13, top - 31, stroke=0, fill=1)
    chart.setFillColor(RED)
    chart.drawString(313, 231, "Keep")
    chart.setFillColor(TEAL)
    chart.drawString(350, 231, "Reschedule")
    chart.save()
    return names


def sections(p1, p2, timings, p3, p4, cases, audit):
    latest = {
        policy: max(float(row["start"]) for row in timings if row["policy"] == policy)
        for policy in ("beam", "nearest")
    }
    outcomes = {}
    for row in p4:
        outcomes.setdefault(row["scenario"], {})[row["policy"]] = (
            float(row["completion_ratio"]), -float(row["latest_start_s"])
        )
    counts = Counter(
        "better" if v["reschedule"] > v["keep"] else "worse" if v["reschedule"] < v["keep"] else "tied"
        for v in outcomes.values()
    )
    mc_rms, mc_threshold, mc_check = audit[:3]
    adverse = next(((name, pair) for name, pair in outcomes.items()
                    if pair["reschedule"] < pair["keep"]), None)
    adverse_text = (
        f"In {adverse[0]}, the fixed plan gives a completion ratio of "
        f"{fmt(adverse[1]['keep'][0])} and a latest start of {fmt(-adverse[1]['keep'][1])} s. "
        f"Replanning gives {fmt(adverse[1]['reschedule'][0])} and "
        f"{fmt(-adverse[1]['reschedule'][1])} s. Canceling a viable assignment can waste prior positioning."
        if adverse else
        "A replan can still worsen performance outside the selected test cases if it cancels viable assignments."
    )
    summary = (
        f"An observation and dispatch prototype was evaluated on the Problem B field. The shortest "
        f"feasible horizontal observation range for T1 is {fmt(p1['range_m'], 3)} m. For T2, the "
        f"selected stations give a first-order horizontal RMS error of {fmt(p2['horizontal_rms_m'], 4)} m. "
        f"The beam-search schedule starts its last observation at {fmt(latest['beam'])} s compared "
        f"with {fmt(latest['nearest'])} s under the nearest-arrival rule. The pointing error allowance "
        f"is met up to about {fmt(p3['path_cap_m'], 1)} m of travel. Across {len(outcomes)} selected "
        f"disturbance cases, replanning improves {counts['better']}, ties {counts['tied']}, and worsens "
        f"{counts['worse']} by the prescribed ranking."
    )
    body = [
        ("Observation Region and Station Selection", [
            "Position is measured east and north from the southwest corner. A station is admissible when "
            "a vehicle disc fits within the field without entering a building, its finite camera-to-target "
            "segment misses every closed building prism, and the target elevation is within the gimbal limits. "
            "A slab intersection retains contact at a single parameter value, which makes tangency occluding [1].",
            "With the target above the camera, the upper elevation limit implies that the horizontal distance "
            "is at least the height difference divided by the tangent of the upper limit. A feasible point "
            "on that inner circle therefore attains the upper bound on inverse-range quality. A one-degree "
            "angular sweep identifies a reproducible representative among the tied sampled stations.",
            f"The selected station is ({fmt(p1['x_m'], 3)}, {fmt(p1['y_m'], 3)}) m. Its elevation is "
            f"{fmt(p1['elevation_deg'], 1)} degrees and its inverse-range quality is "
            f"{fmt(p1['quality_m_inv'], 5)} per metre. The plotted region is a one-metre raster, "
            "while the selected station uses continuous coordinates.",
        ], "b_geometry", "Observable footprint for T1 (light teal), a selected station (red ring), and T2 viewing rays (teal)."),
        ("Dual-Station Localization for T2", [
            "Let r1 and r2 be the horizontal sensor ranges, and let gamma be the smaller angle between "
            "the two bearings. The first-order error normal to each bearing is range times the angular "
            "error in radians. The two normal equations determine the horizontal displacement. Inverting "
            "their two-by-two coefficient matrix, then taking the trace of the propagated covariance, "
            "gives sigma squared times (r1 squared plus r2 squared) divided by sin squared gamma [2].",
            "The RMS metric is the square root of that trace. Baseline, ranges, and crossing angle obey "
            "the cosine rule. The metric diverges near parallel or antiparallel bearings. An observation "
            "boundary is a separate issue because a small station shift can invalidate visibility or travel.",
            f"Vehicles V{p2['vehicle_1']} and V{p2['vehicle_2']} are assigned to "
            f"({fmt(p2['x_1_m'],3)}, {fmt(p2['y_1_m'],3)}) m and "
            f"({fmt(p2['x_2_m'],3)}, {fmt(p2['y_2_m'],3)}) m. Their travel times are "
            f"{fmt(p2['travel_1_s'])} s and {fmt(p2['travel_2_s'])} s. The baseline is "
            f"{fmt(p2['baseline_m'],3)} m, and the crossing angle is {fmt(p2['crossing_deg'],1)} degrees.",
            "Both ranges meet the pitch-imposed lower bound and the sine factor attains one. The chosen "
            "feasible pair attains the lower bound for the specified first-order RMS criterion. This claim "
            "applies to the local metric and the nominal target position.",
        ], None, None),
        ("Multi-Alert Vehicle Scheduling", [
            "Shortest routes on a waypoint graph use conservative rectangular expansions of the buildings "
            "by the disc radius. Expanded corners with a small clearance and the start and finish points "
            "form the graph. This makes each computed route feasible for the vehicle disc, while potentially "
            "excluding shorter rounded-corner paths [3].",
            "Each task selects two different vehicles and two distinct, nondegenerate stations. Driving, "
            "slewing, waiting for the partner, simultaneous observation, and reset occupy each vehicle "
            "in that order. The two gimbal axes can move together. Availability for the next drive is the "
            "end of the current task's reset.",
            "The search enumerates alert orders and retains a bounded beam of partial schedules per order. "
            "The best feasible schedule across two search budgets is carried forward to the disturbance study. "
            "The baseline visits alerts in input order and selects the pair minimizing the later driving "
            "arrival, using the same route, visibility, geometry and synchronization tests.",
            f"The last start is {fmt(latest['beam'])} s for beam search and {fmt(latest['nearest'])} s "
            f"for nearest assignment, a difference of {fmt(latest['nearest'] - latest['beam'])} s. "
            "The comparison is between evaluated feasible schedules. No global optimality claim is made.",
        ], "b_timeline", "Per-vehicle timeline for beam search (B) and nearest assignment (N)."),
        ("Horizontal Pointing Error", [
            "By rotational symmetry, put the target on the positive horizontal axis. The position error "
            "changes the bearing through atan2 of the lateral displacement and the perturbed longitudinal "
            "range. Here X and Y are the position-estimate errors along and across the nominal bearing. "
            "The two independent gimbal errors add as a normal variable. Their convolution with the "
            "position-induced angle is integrated over wrapped intervals about zero.",
            "Composite Simpson integration is applied to the standardized position variables. A "
            "normal CDF integrates the gimbal component conditional on those variables. A bisection search "
            "finds the relevant coverage crossing. An independent first-order approximation propagates the "
            "lateral position variance divided by squared range, plus the two gimbal variances [4].",
            f"The nonlinear threshold is {fmt(p3['path_cap_m'], 3)} m; the coarser integration gives "
            f"{fmt(p3['coarse_path_cap_m'], 3)} m and the linearized estimate gives "
            f"{fmt(p3['linear_path_cap_m'], 3)} m. At {fmt(p3['parameter_check_distance_m'],0)} m, "
            f"the admissible nonnegative parameters satisfy a + {fmt(p3['parameter_check_distance_m'],0)} b "
            f"no greater than approximately {fmt(p3['sigma_cap_m'], 4)} m.",
            f"The linearized variance shares near the threshold are "
            f"{fmt(100*float(p3['position_variance_share']),1)}% for the vehicle position, "
            f"{fmt(100*float(p3['zero_offset_variance_share']),1)}% for gimbal offset, and "
            f"{fmt(100*float(p3['control_variance_share']),1)}% for gimbal control.",
        ], "b_coverage", "Calculated probability of remaining within the two-sided pointing limit."),
        ("Rescheduling After Disturbances", [
            "At time zero both policies begin with the same nominal plan. In the fixed plan, a new alert "
            "remains unassigned and a scheduled observation involving a failed vehicle cannot start after "
            "failure. The surviving vehicles otherwise retain their nominal instructions. A replan first "
            "recovers positions by interpolation along the issued routes, carries forward valid observations "
            "already started, and removes the failed vehicle [5].",
            "During communication loss, the nominal instructions continue. Reassignment is available only "
            "at recovery. Surviving vehicles in interrupted pre-observation phases reset conservatively "
            "before accepting new movement. The plan ranks the number of valid observations started by "
            "the deadline first and the last observation start second.",
            "The main outage interpretation uses an absolute recovery time. The longest duration in the "
            "accompanying prose is tested separately as a sensitivity case. Failure identities are enumerated. "
            "New-alert locations are representative discrete cases, and the resulting counts are not "
            "population probabilities.",
            f"Replanning improves {counts['better']} cases, ties {counts['tied']}, and worsens "
            f"{counts['worse']}. " + adverse_text,
        ], "b_disturbances", "Completion ratios across selected cases, in order: " + ", ".join(cases) + "."),
        ("Paired Scenario Results", [
            "For each row, the completion fraction counts alert starts within the evaluation window. "
            "The last-start column follows the specified horizon convention when an alert is unfinished.",
        ], None, None),
        ("Validation, Limitations, and References", [
            "The implementation checks station visibility, collision-free route segments, joint observation "
            "start, task duration, and nonoverlapping vehicle timelines. Replans are checked against the "
            "recovery time and failed vehicle identity. The search is deterministic. Auditable numerical "
            "outputs and the full scenario timelines are stored separately. A separate seeded Monte Carlo "
            "check evaluates exact bearing intersections and the wrapped pointing error. A wider beam can "
            "perform worse under partial-plan pruning, so the best previously found feasible schedule is retained.",
            f"Across {int(mc_rms['samples']):,} draws, the exact-intersection RMS was "
            f"{fmt(mc_rms['estimate'],4)} m. Pointing coverage was {fmt(mc_threshold['estimate'],5)} at "
            f"the threshold (Wilson interval {fmt(mc_threshold['lower'],5)} to "
            f"{fmt(mc_threshold['upper'],5)}) and {fmt(mc_check['estimate'],5)} at the specified "
            f"{fmt(p3['parameter_check_distance_m'],0)} m check distance.",
            "The model treats targets as stationary, ignores interactions between moving vehicles as in the "
            "nominal timing assumptions, and uses finite station candidates. The scenario study is conditional "
            "on the stated continuation and cancellation rules. Further sensitivity checks should examine "
            "station discretization, clearance, the chosen outage interpretation, and sample coverage.",
            "[1] Liang and Barsky. A New Concept and Method for Line Clipping. ACM Transactions on Graphics, "
            "1984. doi:10.1145/357332.357333.",
            "[2] Bishop et al. Optimality Analysis of Sensor-Target Localization Geometries. Automatica, "
            "2010. doi:10.1016/j.automatica.2009.12.003.",
            "[3] Dijkstra. A Note on Two Problems in Connexion with Graphs. Numerische Mathematik, 1959. "
            "doi:10.1007/BF01386390.",
            "[4] JCGM. Guide to the Expression of Uncertainty in Measurement, Section 5, 2008. "
            "doi:10.59161/JCGM100-2008E.",
            "[5] Pillac et al. A Review of Dynamic Vehicle Routing Problems. European Journal of "
            "Operational Research, 2013. doi:10.1016/j.ejor.2012.08.015.",
            "[6] OpenAI ChatGPT (Codex, GPT-6 series), used on 20 November 2026.",
        ], None, None),
        ("AI Tool Usage Report", [
            "Tool: OpenAI ChatGPT (Codex, GPT-6 series). Date of use: 20 November 2026.",
            "Prompt summary: use the supplied Problem B statement and transcribed parameters to develop "
            "and evaluate an end-to-end prototype and produce a reproducible English draft.",
            "Output and adoption in this draft: AI assistance was used for source transcription, model "
            "and solver design, coding and validation, chart generation, interpretation, and drafting. "
            "These contributions cover all sections and the associated code and figures [6].",
            "Human revision status: this version records the AI-produced draft. Subsequent human "
            "verification, edits, or replacement analyses should be recorded in the AI-use log.",
        ], None, None),
    ]
    scenario_rows = [("Scenario", "Keep ratio", "Keep time", "Replan ratio", "Replan time")]
    scenario_rows.extend(
        (name.replace("_", " "), fmt(scores["keep"][0]), fmt(-scores["keep"][1]),
         fmt(scores["reschedule"][0]), fmt(-scores["reschedule"][1]))
        for name, scores in outcomes.items()
    )
    return summary, body, scenario_rows


def tex_escape(value):
    return "".join({"&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#"}.get(c, c) for c in value)


def write_tex(summary, body, scenario_rows):
    src = (PAPER / "main.tex").read_text(encoding="utf-8")
    boundary = src.index(r"\section{Problem Analysis}")
    clean = src[:boundary].replace("[FILL: Paper Title]", "Rapid UAV Localization via Coordinated Mobile Vehicles")
    clean = clean.replace("[FILL: Summary]", tex_escape(summary))
    clean = clean.replace("[FILL: Keywords]", "Bearing-only localization; vehicle scheduling; uncertainty; rescheduling")
    output = [clean.rstrip()]
    for title, paragraphs, figure, caption in body:
        output.extend([r"\section{" + title + "}", *(tex_escape(p) for p in paragraphs)])
        if title in EQUATIONS:
            output.append(r"\[" + EQUATIONS[title][1] + r"\]")
        if title == "Paired Scenario Results":
            output.extend([
                r"\begin{table}[htbp]", r"\centering",
                r"\caption{Completion ratios and latest-start times in seconds}",
                r"\begin{tabular}{@{}lrrrr@{}}", r"\toprule",
                " & ".join(scenario_rows[0]) + r" \\", r"\midrule",
                *(" & ".join(tex_escape(value) for value in row) + r" \\" for row in scenario_rows[1:]),
                r"\bottomrule", r"\end{tabular}", r"\end{table}",
            ])
        if figure:
            output.extend([r"\begin{figure}[htbp]", r"\centering",
                           r"\includegraphics[width=0.8\linewidth]{" + figure + "}",
                           r"\caption{" + tex_escape(caption) + "}", r"\end{figure}"])
    output.append(r"\end{document}")
    (PAPER / "B_prototype.tex").write_text("\n\n".join(output) + "\n", encoding="utf-8")


def vector_pdf_to_drawing(path, max_width):
    from io import BytesIO
    from pypdf import PdfReader
    import subprocess
    from tempfile import TemporaryDirectory

    page = PdfReader(path).pages[0]
    width, height = float(page.mediabox.width), float(page.mediabox.height)
    with TemporaryDirectory() as temporary:
        prefix = str(Path(temporary) / "figure")
        subprocess.run(["pdftoppm", "-f", "1", "-singlefile", "-r", "220",
                        "-png", str(path), prefix], check=True, capture_output=True)
        pixels = BytesIO(Path(prefix + ".png").read_bytes())
    return Image(pixels, width=min(width, max_width), height=height * min(width, max_width) / width)


def write_preview(summary, body, scenario_rows):
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("BodyTimes", str(font_dir / "times.ttf")))
    pdfmetrics.registerFont(TTFont("TitleTimes", str(font_dir / "timesbd.ttf")))
    normal = ParagraphStyle("body", fontName="BodyTimes", fontSize=12, leading=16, spaceAfter=9)
    heading = ParagraphStyle("heading", parent=normal, fontName="TitleTimes",
                             fontSize=16, leading=20, spaceAfter=14, textColor=INK)
    center = ParagraphStyle("center", parent=heading, alignment=TA_CENTER)
    displayed_math = ParagraphStyle("equation", parent=normal, alignment=TA_CENTER,
                                    textColor=TEAL, spaceAfter=12)
    document = SimpleDocTemplate(str(PAPER / "B_prototype_preview.pdf"), pagesize=A4,
                                 rightMargin=73, leftMargin=73, topMargin=78, bottomMargin=66,
                                 title="Rapid UAV Localization via Coordinated Mobile Vehicles",
                                 author="")
    story = [Spacer(1, 32), Paragraph("2026 ShuWei Cup · Problem B · SWBMCM2613050", center),
             Spacer(1, 25), Paragraph("Rapid UAV Localization via Coordinated Mobile Vehicles", center),
             Spacer(1, 24), Paragraph("Summary", heading), Paragraph(escape(summary), normal),
             Paragraph("Keywords: bearing-only localization, scheduling, rescheduling, uncertainty", normal),
             Paragraph("Team draft · generated with AI assistance · for verification", normal), PageBreak(),
             Paragraph("Content", heading)]
    for number, (title, *_) in enumerate(body, 1):
        story.append(Paragraph(f"{number}. {title} &nbsp; {number + 2}", normal))
    figure_number = 0
    for number, (title, paragraphs, figure, caption) in enumerate(body, 1):
        story.extend([PageBreak(), Paragraph(f"{number}. {title}", heading)])
        story.extend(Paragraph(escape(p), normal) for p in paragraphs)
        if title in EQUATIONS:
            story.append(Paragraph(escape(EQUATIONS[title][0]), displayed_math))
        if title == "Paired Scenario Results":
            table = Table(scenario_rows, colWidths=[158, 69, 69, 73, 73], rowHeights=17)
            table.setStyle(TableStyle([
                ("FONTNAME", (0, 0), (-1, -1), "BodyTimes"),
                ("FONTNAME", (0, 0), (-1, 0), "TitleTimes"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEABOVE", (0, 0), (-1, 0), .6, INK),
                ("LINEBELOW", (0, 0), (-1, 0), .5, INK),
                ("LINEBELOW", (0, -1), (-1, -1), .6, INK),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F4F8FA")]),
            ]))
            story.extend([Paragraph("Table 1. Completion ratios and latest-start times in seconds.", normal), table])
        if figure:
            figure_number += 1
            drawing = vector_pdf_to_drawing(FIGURES / (figure + ".pdf"), 405)
            if drawing.drawHeight > 245:
                drawing.drawWidth *= 245 / drawing.drawHeight
                drawing.drawHeight = 245
            story.extend([drawing, Paragraph(f"Figure {figure_number}. {escape(caption)}", normal)])

    def page_header(pdf, doc):
        if doc.page == 1:
            return
        pdf.setFont("BodyTimes", 12)
        pdf.drawString(73, A4[1] - 50, "Team#SWBMCM2613050")
        pdf.drawRightString(A4[0] - 73, A4[1] - 50, f"Page {doc.page} of {len(body) + 2}")
        pdf.setStrokeColor(INK)
        pdf.line(73, A4[1] - 55, A4[0] - 73, A4[1] - 55)

    document.build(story, onFirstPage=page_header, onLaterPages=page_header)
    from pypdf import PdfReader
    pages = PdfReader(PAPER / "B_prototype_preview.pdf").pages
    assert len(pages) == len(body) + 2, "Preview paginated outside planned page layout"
    assert "Team#" not in pages[0].extract_text()
    assert "Content" in pages[1].extract_text()
    assert all(f"Page {i} of {len(pages)}" in page.extract_text()
               for i, page in enumerate(pages[1:], 2))


def main():
    FIGURES.mkdir(exist_ok=True)
    p1, p2, p3 = (read(name)[0] for name in ("B_P1.csv", "B_P2_localization.csv", "B_P3.csv"))
    timings, coverage, p4 = (read(name) for name in ("B_P2_schedules.csv", "B_P3_coverage.csv", "B_P4.csv"))
    draw_map(p1, p2)
    draw_timeline(timings)
    draw_coverage(coverage)
    cases = draw_disturbances(p4)
    summary, body, scenario_rows = sections(p1, p2, timings, p3, p4, cases, read("B_validation.csv"))
    write_tex(summary, body, scenario_rows)
    write_preview(summary, body, scenario_rows)


if __name__ == "__main__":
    main()

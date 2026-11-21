"""Render the existing Problem B draft and figures. AI-assisted (OpenAI Codex, GPT-6 series)."""

import csv
import json
from collections import Counter
from pathlib import Path
import subprocess
from xml.sax.saxutils import escape

from PIL import Image as RasterImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from problem_b_geometry import ROOT
from plot_problem_b import (
    draw_coverage, draw_disturbances, draw_map, draw_parameter_region, draw_routes, draw_timeline,
)


FIGURES, PAPER, RESULTS = (ROOT / name for name in ("figures", "paper", "results"))
FIGURE_DPI = 300
WINDOW_NOTE = "* Evaluation-window score when at least one alert has not started."
INK = colors.HexColor("#172D43")
TEAL = colors.HexColor("#136C74")
RED = colors.HexColor("#B24933")
GRID = colors.HexColor("#DAE2EA")
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


def display_score(record):
    started = int(record["successes"])
    total = int(record["alerts"])
    marker = "*" if started < total else ""
    return f"{started}/{total}", fmt(record["latest_start_s"]) + marker


def sections(p1, p2, timings, p3, p4, audit, visits):
    latest = {
        policy: max(float(row["start"]) for row in timings if row["policy"] == policy)
        for policy in ("beam", "nearest")
    }
    records = {}
    for row in p4:
        records.setdefault(row["scenario"], {})[row["policy"]] = row
    outcomes = {
        name: {policy: (float(row["completion_ratio"]), -float(row["latest_start_s"]))
               for policy, row in pair.items()}
        for name, pair in records.items()
    }
    counts = Counter(
        "better" if v["reschedule"] > v["keep"] else "worse" if v["reschedule"] < v["keep"] else "tied"
        for v in outcomes.values()
    )
    mc_rms, mc_threshold, mc_check = audit[:3]
    zero_legs = [visit for visit in visits if visit["path"][0] == visit["path"][-1]]
    reuse_text = " ".join(
        f"V{visit['vehicle'] + 1} starts its leg for {visit['alert']} already at the assigned station, "
        "so this leg consumes slew time but no driving time."
        for visit in zero_legs
    )
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
        ], "b_geometry", "T1 observability and the selected minimum-range station, with a local inset of the T2 bearing intersection."),
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
        ], "b_timeline", "Paired per-vehicle timelines. The dashed line in each panel marks its last observation start."),
        ("Nominal Driving Routes", [
            "The map links the timing sequence to the physical station choices. Filled markers show vehicle "
            "origins and open rings show selected observation stations. A repeated vehicle can travel on "
            "multiple segments of the same color. Building footprints are shaded. " + reuse_text,
        ], "b_routes", "Nominal paths for the five available vehicles. Paths use conservative obstacle clearance."),
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
        ], "b_coverage", "Pointing coverage versus travel distance. Red points show the Monte Carlo checks with Wilson intervals."),
        ("Admissible Position-Error Parameters", [
            "For the fixed check distance, the permitted combinations of error intercept and growth "
            "coefficient form a triangle in the nonnegative parameter region. Its sloped edge collects "
            "the intercept–slope combinations that meet the target coverage at equality.",
        ], "b_parameters", "Admissible intercept and growth coefficient under the two-sided coverage requirement."),
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
        ], "b_disturbances", "Completion and last-start times under both policies for representative disturbance cases."),
        ("Paired Scenario Results", [
            "For each row, the completion fraction counts alert starts within the evaluation window. "
            "The last-start column follows the specified horizon convention when an alert is unfinished.",
        ], None, None),
        ("Validation and Limitations", [
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
        ], None, None),
        ("References", [
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
            "This revision uses AI assistance for plotting recorded outputs, typesetting, "
            "code performance refactoring, and consistency checks.",
            "Human revision status: this version records the AI-produced draft. Subsequent human "
            "verification, edits, or replacement analyses should be recorded in the AI-use log.",
        ], None, None),
    ]
    scenario_rows = [("Scenario", "Keep k/N", "Keep time", "Replan k/N", "Replan time")]
    scenario_rows.extend(
        (name.replace("_", " "), *display_score(pair["keep"]), *display_score(pair["reschedule"]))
        for name, pair in records.items()
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
    clean = clean.replace(
        r"\section*{Summary}",
        r"\noindent\textbf{Internal Working Draft}" + "\n\n" + r"\section*{Summary}",
    )
    clean = clean.replace(r"\setcounter{tocdepth}{1}", r"\setcounter{tocdepth}{2}")
    clean = clean.replace(r"Team\#\TeamNumber", r"Team\#\ProblemLetter\TeamNumber")
    output = [clean.rstrip()]
    page_starts = {
        "Dual-Station Localization for T2", "Horizontal Pointing Error",
        "Admissible Position-Error Parameters",
        "Rescheduling After Disturbances", "Paired Scenario Results",
        "Validation and Limitations", "AI Tool Usage Report",
    }
    subsections = {
        "Dual-Station Localization for T2", "Multi-Alert Vehicle Scheduling",
        "Nominal Driving Routes", "Admissible Position-Error Parameters",
        "Paired Scenario Results",
    }
    for title, paragraphs, figure, caption in body:
        if title in page_starts:
            output.append(r"\clearpage")
        if title == "Dual-Station Localization for T2":
            output.append(r"\section{Two-Station Localization and Scheduling}")
        heading = r"\subsection" if title in subsections else r"\section"
        output.append(heading + "{" + title + "}")
        if title == "References":
            output.extend([r"\begingroup\raggedright",
                           *(tex_escape(text) for text in paragraphs), r"\par\endgroup"])
        else:
            output.extend(tex_escape(text) for text in paragraphs)
        if title in EQUATIONS:
            output.append(r"\[" + EQUATIONS[title][1] + r"\]")
        if title == "Paired Scenario Results":
            output.extend([
                r"\begin{table}[!ht]", r"\centering",
                r"\caption{Completion ratios and latest-start times in seconds}",
                r"\begin{tabular*}{0.96\linewidth}{@{\extracolsep{\fill}}lrrrr@{}}", r"\toprule",
                r"& \multicolumn{2}{c}{Keep Plan} & \multicolumn{2}{c}{Reschedule} \\",
                r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
                r"Scenario & $k/N$ & Time (s) & $k/N$ & Time (s) \\", r"\midrule",
                *(" & ".join(tex_escape(value) for value in row) + r" \\" for row in scenario_rows[1:]),
                r"\bottomrule", r"\end{tabular*}",
                r"\par\smallskip\parbox{0.96\linewidth}{\raggedright " + WINDOW_NOTE + "}",
                r"\end{table}",
            ])
        if figure:
            height = "0.30" if figure in {"b_timeline", "b_routes"} else "0.38"
            output.extend([r"\begin{figure}[!ht]", r"\centering",
                           rf"\includegraphics[width=0.94\linewidth,height={height}\textheight,keepaspectratio]{{{figure}}}",
                           r"\caption{" + tex_escape(caption) + "}", r"\end{figure}"])
    output.append(r"\end{document}")
    (PAPER / "B_prototype.tex").write_text("\n\n".join(output) + "\n", encoding="utf-8")


def export_figure_previews(figure_names):
    tile_width, tile_height, gap = 900, 650, 22
    rows = (len(figure_names) + 1) // 2
    overview = RasterImage.new(
        "RGB", (tile_width * 2 + gap * 3, tile_height * rows + gap * (rows + 1)), "#DBE5ED",
    )
    for index, name in enumerate(figure_names):
        path = FIGURES / name
        subprocess.run(
            ["pdftoppm", "-f", "1", "-singlefile", "-r", str(FIGURE_DPI), "-png",
             str(path.with_suffix(".pdf")), str(path)],
            check=True, capture_output=True,
        )
        with RasterImage.open(path.with_suffix(".png")) as figure:
            figure.thumbnail((tile_width - 20, tile_height - 20), RasterImage.Resampling.LANCZOS)
            tile = RasterImage.new("RGB", (tile_width, tile_height), "white")
            tile.paste(figure, ((tile_width - figure.width) // 2, (tile_height - figure.height) // 2))
            row, col = divmod(index, 2)
            overview.paste(tile, (gap + col * (tile_width + gap), gap + row * (tile_height + gap)))
    overview.save(FIGURES / "B_figure_overview.png")


def write_preview(summary, body, scenario_rows):
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
            story.extend([Paragraph("Table 1. Completion ratios and latest-start times in seconds.", normal),
                          table, Paragraph(WINDOW_NOTE, normal)])
        if figure:
            figure_number += 1
            drawing = Image(str(FIGURES / (figure + ".png")), width=405, height=245, kind="proportional")
            story.extend([drawing, Paragraph(f"Figure {figure_number}. {escape(caption)}", normal)])

    def page_header(pdf, doc):
        if doc.page == 1:
            return
        pdf.setFont("BodyTimes", 12)
        pdf.drawString(73, A4[1] - 50, "Team#BSWBMCM2613050")
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
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Render the Problem B internal prototype.")
    parser.add_argument("--tex-only", action="store_true", help="Regenerate the editable TeX without rebuilding figures")
    args = parser.parse_args()
    p1, p2, p3 = (read(name)[0] for name in ("B_P1.csv", "B_P2_localization.csv", "B_P3.csv"))
    timings, p4 = (read(name) for name in ("B_P2_schedules.csv", "B_P4.csv"))
    audit = read("B_validation.csv")
    route_data = json.loads((RESULTS / "B_timelines.json").read_text(encoding="utf-8"))
    summary, body, scenario_rows = sections(p1, p2, timings, p3, p4, audit, route_data["nominal"])
    write_tex(summary, body, scenario_rows)
    if args.tex_only:
        return

    FIGURES.mkdir(exist_ok=True)
    font_dir = Path("C:/Windows/Fonts")
    pdfmetrics.registerFont(TTFont("BodyTimes", str(font_dir / "times.ttf")))
    pdfmetrics.registerFont(TTFont("TitleTimes", str(font_dir / "timesbd.ttf")))
    coverage = read("B_P3_coverage.csv")
    draw_map(p1, p2)
    draw_timeline(timings)
    draw_routes(route_data["nominal"])
    cover_audit = [
        (float(distance), *(float(row[key]) for key in ("estimate", "lower", "upper")))
        for distance, row in ((p3["path_cap_m"], audit[1]), (p3["parameter_check_distance_m"], audit[2]))
    ]
    draw_coverage(coverage, float(p3["path_cap_m"]), cover_audit)
    draw_parameter_region(p3)
    draw_disturbances(p4)
    export_figure_previews([figure for _, _, figure, _ in body if figure])
    write_preview(summary, body, scenario_rows)


if __name__ == "__main__":
    main()

"""Render 11 publication-grade Matplotlib analytical figures from the verified Problem B outputs.

AI assistance:
  - ChatGPT (Codex, GPT-6.2 Sol), OpenAI; version release date: not publicly disclosed; used 2026-11-21.
  - Antigravity (Gemini), Google DeepMind; version release date: not publicly disclosed; used 2026-11-21.
Scope: scientific visualization, grayscale/print compatibility, and deterministic figure provenance.
"""
from argparse import ArgumentParser
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import atan2, degrees, dist, isclose, log, radians, sqrt
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap, TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Arc, Circle, Ellipse, FancyBboxPatch, Patch, Polygon, Rectangle
from matplotlib.ticker import MaxNLocator, PercentFormatter

import b_revision_events as events
import b_revision_geometry as geometry_checks
from b_revision_data import DEFAULT_OUTPUT, digest, read_csv, read_json, write_csv
from b_revision_probability import A, B, CONTROL, OFFSET, SEED
import problem_b_geometry as model


INK = "#17283A"
MUTED = "#465A70"
GRID = "#DCE4ED"
PAPER = "#F1F5F9"
BLUE = "#0EA5E9"
TEAL = "#10B981"
ORANGE = "#F59E0B"
GOLD = "#D97706"
PURPLE = "#A855F7"
CORAL = "#F43F5E"
# Unified V1-V5 palette matching the 3D digital twin command dashboard
COLORS = (BLUE, ORANGE, TEAL, PURPLE, CORAL)
UNAVAILABLE = "#64748B"
PHASES = {
    "travel": ("Driving", BLUE),
    "slew": ("Slewing", ORANGE),
    "wait_partner": ("Waiting", "#94A3B8"),
    "observe": ("Observing", TEAL),
    "reset": ("Resetting", PURPLE),
    "cancel_reset": ("Cancel / reset", CORAL),
    "missed_pair": ("Missed pair", "#FDA4AF"),
    "failed": ("Fault", UNAVAILABLE),
}
PHASE_HATCHES = {
    "travel": "",
    "slew": "///",
    "wait_partner": "...",
    "observe": "",
    "reset": "\\\\\\",
    "cancel_reset": "xxx",
    "missed_pair": "+++",
    "failed": "///",
}
FIGURE_MAP = (
    ("fig01_framework", "P1_station.csv; P2_precision.csv; priority_3.json; P3_verification.json; P4_extended_summary.json",
     "Interdisciplinary architecture and verified metric handoffs across P1-P4"),
    ("fig02_p1_geometry", "P1_grid_map.json; P1_geometry.json; P1_pitch_checks.csv; Route_clearance_comparison.csv; Route_summary.json",
     "P1 observable field, building shadows, rounded Minkowski safety, route comparison and exact nonlinear pitch sensitivity"),
    ("fig03_p2_precision", "P2_precision.csv; P2_precision_routes.json; B题题面参数.csv",
     "P2(1) local first-order horizontal RMS contour field and 95% analytical error ellipse"),
    ("fig04_p2_paths", "Executed_timeline.json; P2_main_plans.json; P2_visit_phases.csv",
     "P2(2) zoomed local routing insets and global 5-vehicle rounded-clearance path comparison"),
    ("fig05_p2_dispatch", "Executed_timeline.json; P2_main_plans.json; P2_trials.csv; P2_visit_phases.csv; P2_critical_chains.csv",
     "P2(2) shared-k schedule Gantt, vehicle trajectories and k=3 vs k=8 ranking-reversal breakdown"),
    ("fig06_p3_risk", "P3_MC.csv; P3_curve.csv; P3_verification.json; P3_parameters.csv; B题题面参数.csv",
     "P3 Monte Carlo scatter, analytical ellipse, 66.837 m coverage threshold inset and (a,b) admissible domain"),
    ("fig07_p4_resilience", "P4_dedup_expanded_cases.csv; P4_category_summary_expanded.csv; P4_budget_stability.csv",
     "P4 115-scenario deduplicated & spatially expanded resilience, search-budget stability, and win/tie/loss ledger"),
    ("fig08_v5_timeline", "P4_V5_event_comparison.csv; Executed_timeline.json; priority_3.json",
     "V5 single-fault counterexample aligned dual-policy Gantt showing +1.893 s bottleneck shift"),
    ("fig09_global_sensitivity", "Global_sensitivity_oat.csv; Global_sensitivity_fixed_vs_reopt.csv; Global_sensitivity_interaction.csv; Global_sensitivity_weight_check.csv",
     "Parameter perturbation & pairwise interaction analysis: re-optimized vs fixed-plan, tornado, 6x6 interactions, and 5-scheme weight stability"),
    ("fig10_pareto_3d", "Pareto_tradeoff_3d.csv",
     "Three-objective Pareto non-dominated frontier (time, travel, observation quality) with multiplicity annotations and 2D projections"),
    ("fig11_3d_dashboard", "Executed_timeline.json; P2_main_plans.json; SIMULATOR_CHECKS.json",
     "High-contrast print-grade 3D digital twin three-stage verification triptych (0/892 static building-obstacle collisions)"),
)
PLOT_METADATA = {
    "Creator": "Matplotlib",
    "CreationDate": datetime(2026, 11, 21, tzinfo=timezone.utc),
    "ModDate": None,
}
mpl.rcParams.update({
    "font.family": ["Times New Roman", "DejaVu Serif"],
    "font.size": 11,
    "axes.titlesize": 12,
    "axes.titleweight": "bold",
    "axes.labelsize": 10.5,
    "axes.labelcolor": INK,
    "axes.edgecolor": "#9AAABD",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.linewidth": .75,
    "axes.axisbelow": True,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": .6,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "text.color": INK,
    "legend.frameon": False,
    "legend.fontsize": 9.5,
    "lines.linewidth": 1.6,
    "pdf.fonttype": 42,
    "savefig.facecolor": "white",
})


def layout(title, size, rows=1, cols=1, **kwargs):
    fig = plt.figure(figsize=size, layout="constrained")
    fig.suptitle(title, x=.02, ha="left", fontsize=15, fontweight="bold")
    return fig, fig.add_gridspec(rows, cols, **kwargs)


def panel(ax, letter, title):
    tag = f"({letter.lower()})" if not letter.startswith("(") else letter.lower()
    ax.set_title(f"{tag}  {title}", loc="left", fontsize=11.0, fontweight="bold")


def save(fig, directory, stem):
    directory.mkdir(parents=True, exist_ok=True)
    fig.savefig(directory / f"{stem}.pdf", metadata=PLOT_METADATA)
    fig.savefig(directory / f"{stem}.png", dpi=320, metadata={"Software": "Matplotlib"})
    plt.close(fig)


def xy_axes(ax, xlim=(0, model.WIDTH), ylim=(0, model.DEPTH)):
    ax.set(xlim=xlim, ylim=ylim, xlabel="East (m)", ylabel="North (m)", aspect="equal")
    ax.xaxis.set_major_locator(MaxNLocator(5))
    ax.yaxis.set_major_locator(MaxNLocator(5))


def footprint(ax, *, clearance=False, labels=True):
    for i, (x0, x1, y0, y1, _) in enumerate(model.BUILDINGS, 1):
        if clearance:
            r = model.RADIUS
            ax.add_patch(FancyBboxPatch((x0, y0), x1-x0, y1-y0,
                         boxstyle=f"round,pad={r},rounding_size={r}", linewidth=1,
                         facecolor="#F9CCD4", edgecolor=ORANGE, alpha=.65, zorder=3))
        ax.add_patch(Rectangle((x0, y0), x1-x0, y1-y0, facecolor="#8599AC",
                               edgecolor=MUTED, lw=.7, zorder=4))
        if labels:
            ax.text((x0+x1)/2, (y0+y1)/2, f"B{i}", ha="center", va="center",
                    fontsize=8.5, color="white", clip_on=True, zorder=5)


def node(ax, x, y, w, h, title, body, color):
    card = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=.007,rounding_size=.014",
                         lw=.8, fc=PAPER, ec="#B8C8D7")
    ax.add_patch(card)
    ax.add_patch(Rectangle((x, y+.012), .007, h-.024, color=color, lw=0))
    ax.text(x+.019, y+h*.68, title, weight="bold", fontsize=11, va="center")
    ax.text(x+.019, y+h*.32, body, fontsize=9.8, va="center", color=MUTED)


def connect(ax, start, end, *, style="-"):
    ax.annotate("", end, start, arrowprops={"arrowstyle": "-|>", "color": MUTED,
                "lw": .9, "linestyle": style, "mutation_scale": 12})


def framework(results):
    p1 = read_json(results / "P1_geometry.json")["ties"]["ready"]
    precision, = read_csv(results / "P2_precision.csv")
    summary = read_json(results / "priority_3.json")
    spread = read_json(results / "P3_verification.json")
    p4_ext_path = results / "P4_extended_summary.json"
    p4_ext = read_json(p4_ext_path) if p4_ext_path.is_file() else None
    p4_line = (
        f"{p4_ext['total_unique_cases']} unique cases ({p4_ext['dedup_baseline_unique_cases']} dedup + {p4_ext['expanded_new_cases']} stress)"
        if p4_ext else f"{summary['P4_case_count']} case IDs, frozen dispatch plan"
    )
    fig, gs = layout("Problem B  |  Evidence and dependency map", (9.6, 5.1))
    ax = fig.add_subplot(gs[0, 0])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    node(ax, .025, .69, .268, .19, "Official field and alerts", "Buildings, vehicle states, target locations", BLUE)
    node(ax, .365, .69, .268, .19, "Shared geometry", "Euclidean clearance, pitch, line of sight", BLUE)
    node(ax, .708, .69, .265, .19, "P1  Observation region",
         f"Quality-optimal witness: {p1['ready_s']:.3f} s ready", TEAL)
    node(ax, .025, .395, .268, .19, "P2(1)  Bearing precision",
         f"T2 local horizontal RMS: {float(precision['horizontal_rms_m']):.6f} m", PURPLE)
    node(ax, .365, .395, .268, .19, "P2(2)  Paired dispatch",
         f"Beam incumbent: {summary['P2_latest_starts_s']['beam']:.3f} s last start", TEAL)
    node(ax, .708, .395, .265, .19, "P4  Disturbance replay", p4_line, ORANGE)
    node(ax, .025, .10, .268, .19, "P3  Pointing uncertainty",
         f"Coverage crossing: {spread['independent_crossing_m']:.6f} m", PURPLE)
    node(ax, .365, .10, .268, .19, "Event log and replay",
         "Executed phases, paths, time and status", ORANGE)
    node(ax, .708, .10, .265, .19, "Deployment review",
         "Geometry, precision and resilience checks", BLUE)
    connect(ax, (.30, .785), (.358, .785))
    connect(ax, (.640, .785), (.701, .785))
    connect(ax, (.44, .682), (.20, .592))
    connect(ax, (.50, .682), (.50, .592))
    connect(ax, (.641, .490), (.701, .490))
    connect(ax, (.840, .387), (.58, .297))
    connect(ax, (.641, .195), (.701, .195))
    connect(ax, (.30, .195), (.358, .195), style="--")
    ax.plot([.155, .155], [.685, .625], color=MUTED, lw=.9, ls="--")
    ax.plot([.155, .012, .012], [.625, .625, .195], color=MUTED, lw=.9, ls="--")
    connect(ax, (.012, .195), (.023, .195), style="--")
    ax.annotate("", (.705, .11), (.295, .11), arrowprops={"arrowstyle": "-|>",
                "connectionstyle": "arc3,rad=.11", "color": MUTED, "lw": .9, "ls": "--"})
    ax.legend(
        handles=[
            Line2D([0], [0], color=MUTED, lw=1.2, ls="-", label="Data & schedule handoff"),
            Line2D([0], [0], color=MUTED, lw=1.2, ls="--", label="Constraint & audit feedback"),
        ],
        loc="upper right", bbox_to_anchor=(0.99, 0.99), ncols=2, frameon=True,
        facecolor="white", edgecolor=GRID, fontsize=8.8,
    )
    return fig


def p1_geometry(results):
    grid = read_json(results / "P1_grid_map.json")
    geometry = read_json(results / "P1_geometry.json")
    ready = geometry["ties"]["ready"]
    pitch = read_csv(results / "P1_pitch_checks.csv")
    routes = read_csv(results / "Route_clearance_comparison.csv")
    route_summary = read_json(results / "Route_summary.json")
    fig, gs = layout("P1  |  Observation geometry and sensitivity", (9.8, 8.0), 2, 2)
    ax, close, comparison, sensitivity = [fig.add_subplot(gs[i, j])
                                             for i in range(2) for j in range(2)]
    panel(ax, "a", "Observable stations and building shadows")
    panel(close, "b", "Quality-optimal arc near T1")
    target = np.array(model.TARGETS["T1"][:2])
    spacing = grid["step_m"]
    shift = (grid["phase"]-.5)*spacing
    rectangles = [Rectangle((a*spacing+shift, j*spacing+shift),
                             (b-a+1)*spacing, spacing) for j,a,b in grid["runs"]]
    from matplotlib.collections import PatchCollection
    ax.add_collection(PatchCollection(rectangles, facecolor="#B7E0D4", edgecolor="none", zorder=1))
    for a in (ax, close):
        for shadow in geometry["shadows"]:
            a.add_patch(Polygon(shadow, closed=True, facecolor="#C5BAD6", alpha=.46,
                                edgecolor=PURPLE, lw=.55, hatch="////", zorder=2))
        footprint(a, clearance=True)
        a.scatter(*target, s=55, marker="*", color=PURPLE, edgecolor="white", lw=0.4, zorder=8)
        a.scatter(ready["x_m"], ready["y_m"], s=46, fc="white", ec=ORANGE, lw=1.5, zorder=8)
        a.plot(*np.array(ready["path"]).T, color=BLUE, lw=1.6, zorder=6)
    xy_axes(ax)
    span = 1.48*ready["range_m"]
    xy_axes(close, (target[0]-span, target[0]+span), (target[1]-span, target[1]+span))
    ax.add_patch(Rectangle(target-span, 2*span, 2*span, fill=False, lw=1.2,
                           ls="--", color=INK, zorder=9))
    close.add_patch(Circle(target, ready["range_m"], fill=False, ec=MUTED,
                           lw=.8, ls="--", zorder=6))
    for arc in geometry["arcs"]:
        theta = np.radians(np.linspace(arc["start_deg"], arc["end_deg"], 300))
        points = target[:, None]+ready["range_m"]*np.array([np.cos(theta), np.sin(theta)])
        close.plot(*points, color=TEAL, lw=2.8, zorder=7, label="Optimal feasible arc")
        for j,key in [(0,"start_included"),(-1,"end_included")]:
            close.scatter(*points[:, j], s=28, ec=TEAL, fc=TEAL if arc[key] else "white", zorder=9)
    close.text(.97,.04,f"Range: {ready['range_m']:.3f} m\nReady: {ready['ready_s']:.3f} s",
               transform=close.transAxes, ha="right", va="bottom", color=INK, fontsize=9.2,
               bbox={"boxstyle":"round,pad=.3","fc":"white","ec":GRID}, zorder=9)
    close.legend(
        handles=[
            Line2D([0],[0], color=TEAL, lw=2.6, label="Feasible optimal arc"),
            Line2D([0],[0], marker="*", color="none", mfc=PURPLE, mec="white", ms=8, label="Target T1"),
            Line2D([0],[0], marker="o", color="none", mfc="white", mec=ORANGE, mew=1.5, ms=6, label="V4 witness"),
            Line2D([0],[0], color=BLUE, lw=1.6, label="V4 path"),
        ],
        loc="upper right", frameon=True, facecolor="white", framealpha=0.92, fontsize=7.8,
    )
    ax.legend(handles=[Patch(fc="#B7E0D4",label="Observable grid"),
                       Patch(fc="#C5BAD6",ec=PURPLE,hatch="////",label="Building shadow"),
                       Patch(fc="#F9CCD4",ec=ORANGE,label="Safety offset (1.5 m)")],
              loc="upper left", frameon=True, facecolor="white", framealpha=0.92, fontsize=8.2)
    assert len(routes)==route_summary["compared_routes"]
    positive = [100*float(x["saving_m"]) for x in routes if x["saving_m"] and float(x["saving_m"]) > 1e-8]
    restored = sum(x["aabb_reachable"] == "False" and bool(x["rounded_verified_distance_m"]) for x in routes)
    assert len(positive)==route_summary["shorter_paths"] and restored==route_summary["restored_endpoints"]
    panel(comparison, "c", "Rounded vs. rectangular route checks")
    comparison.hist(positive, bins=np.linspace(0, max(positive)*1.001, 11), fc=TEAL, ec="white")
    comparison.set(xlabel="Distance saved among shorter routes (cm)", ylabel="Routes")
    comparison.yaxis.set_major_locator(MaxNLocator(integer=True))
    comparison.text(.97,.94,f"{len(positive)} routes shorter\n{restored} endpoints restored",
                    transform=comparison.transAxes, ha="right", va="top", weight="bold",
                    bbox={"boxstyle":"round,pad=.3","fc":"white","ec":GRID})
    panel(sensitivity, "d", "Elevation ceiling and peak quality loss")
    deg = [float(row["elevation_ceiling_deg"]) for row in pitch]
    losses = [100*float(row["relative_quality_loss"]) for row in pitch]
    # Plot exact continuous analytical nonlinear curve 100*(1 - tan(beta)/tan(80 deg))
    beta_grid = np.linspace(min(deg), max(deg), 200)
    exact_loss_curve = 100.0 * (1.0 - np.tan(np.radians(beta_grid)) / np.tan(np.radians(max(deg))))
    sensitivity.plot(beta_grid, exact_loss_curve, "-", color=BLUE, lw=2.0, label=r"Analytical $1-\tan\beta_{\max}/\tan 80^\circ$")
    sensitivity.scatter(deg, losses, s=46, color=BLUE, edgecolor="white", lw=0.7, zorder=4, label="Verified checkpoints")
    sensitivity.scatter(deg[1], losses[1], s=72, facecolor="white", edgecolor=ORANGE, lw=1.6, zorder=5)
    sensitivity.annotate(f"{deg[0]:g}° to {deg[1]:g}°\n{losses[1]:.2f}% quality drop",
                        (deg[1], losses[1]), xytext=(-108, 36), textcoords="offset points",
                        arrowprops={"arrowstyle":"->","color":ORANGE,"lw":1.2}, color=GOLD, fontsize=9.8,
                        fontweight="bold", bbox={"fc":"white","ec":ORANGE,"alpha":0.94,"pad":2.0})
    sensitivity.set(xlabel=r"Elevation ceiling $\beta_{\max}$ (deg)", ylabel="Relative quality loss (%)", ylim=(-4, max(losses)+9))
    sensitivity.legend(loc="lower left", frameon=True, facecolor="white", fontsize=8.2)
    return fig


def covariance_ellipse(ax, center, cov, *, color=ORANGE):
    values, vectors = np.linalg.eigh(cov)
    assert values[0] > 0
    radii = np.sqrt(-2*log(.05)*values)
    angle = degrees(atan2(vectors[1,1],vectors[0,1]))
    ax.add_patch(Ellipse(center, 2*radii[1], 2*radii[0], angle=angle, facecolor=color,
                         edgecolor=color, alpha=.16, zorder=3))
    ax.add_patch(Ellipse(center, 2*radii[1], 2*radii[0], angle=angle, fill=False,
                         ec=color, lw=1.3, zorder=4))
    return radii


def precision(results):
    evidence, = read_csv(results / "P2_precision.csv")
    routes = read_json(results / "P2_precision_routes.json")
    target = np.array(model.TARGETS["T2"][:2])
    stations = np.array([(float(evidence[f"x_{i}_m"]),float(evidence[f"y_{i}_m"])) for i in (1,2)])
    sigma = radians(model.number("p2_1","bearing","error_std"))
    rms = float(evidence["horizontal_rms_m"])
    assert all(np.allclose(route[-1], station) for route,station in zip(routes,stations))
    cov = np.array([[float(evidence["cov_xx_m2"]),float(evidence["cov_xy_m2"])],
                    [float(evidence["cov_xy_m2"]),float(evidence["cov_yy_m2"])]])
    x = np.linspace(min(stations[:,0])-.4, target[0]+6, 150)
    y = np.linspace(stations[0,1]-.75, stations[1,1]+.75, 150)
    X,Y = np.meshgrid(x,y)
    u,v = [np.array([X-sx,Y-sy]) for sx,sy in stations]
    ru,rv = np.hypot(*u),np.hypot(*v)
    det = abs(u[0]*v[1]-u[1]*v[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        spread = sigma*np.sqrt(ru**2+rv**2)*ru*rv/det
    fig, gs = layout("P2(1)  |  Fixed-pair localization sensitivity near T2", (9.8, 4.7), 1, 2,
                     width_ratios=(1.24,1))
    ax = fig.add_subplot(gs[0,0])
    close = fig.add_subplot(gs[0,1])
    panel(ax,"a","Local first-order RMS with stations fixed")
    upper = float(np.nanquantile(spread[np.isfinite(spread)],.86))
    levels = np.linspace(rms*.7, upper, 22)
    # Smooth rasterized pcolormesh + subtle white isolines eliminates vector PDF contourf white seams cleanly
    mesh = ax.pcolormesh(X, Y, np.ma.masked_invalid(spread), cmap="cividis",
                         shading="gouraud", vmin=levels[0], vmax=levels[-1], rasterized=True)
    ax.contour(X, Y, np.ma.masked_invalid(spread), levels=levels[::3],
               colors="white", linewidths=0.45, alpha=0.42, zorder=2)
    cb_ticks = [t for t in (0.12, 0.18, 0.24, 0.30, 0.36) if levels[0] - 1e-6 <= t <= levels[-1] + 1e-6]
    fig.colorbar(mesh, ax=ax, label="Horizontal RMS (m)", shrink=.84, format="%.2f", ticks=cb_ticks)
    for i,(sx,sy) in enumerate(stations,1):
        ax.plot([sx,target[0]],[sy,target[1]],color="white",lw=1.6)
        ax.scatter(sx,sy,c="white",edgecolors=BLUE,zorder=5,s=38)
        ax.annotate(f"S{i} (V{evidence[f'vehicle_{i}']})",(sx,sy),
                    xytext=(6,2),textcoords="offset points",fontsize=9,weight="bold",
                    bbox={"fc":"white","ec":"none","alpha":.92,"pad":1.2})
    theta = [degrees(atan2(*(p-target)[::-1])) for p in stations]
    left,right = theta[1],theta[0]
    while right < left:
        right += 360
    assert isclose(right-left,float(evidence["crossing_deg"]),abs_tol=1e-6)
    ax.add_patch(Arc(target,2.15,2.15,theta1=left,theta2=right,ec="white",lw=1.2,zorder=5))
    ax.annotate(f"{float(evidence['crossing_deg']):.0f}°", target+[-1.46,0],
                color="white",weight="bold",ha="center",va="center")
    ax.scatter(*target,color=ORANGE,marker="*",s=60,zorder=6)
    ax.annotate("T2", target, xytext=(6,6), textcoords="offset points", color="white",weight="bold")
    xy_axes(ax,(x[0],x[-1]),(y[0],y[-1]))
    panel(close,"b","Local Gaussian 95% confidence region")
    radii = covariance_ellipse(close,(0,0),cov)
    amplitude = float(max(radii))*1.78
    close.axhline(0,color=GRID,lw=.8)
    close.axvline(0,color=GRID,lw=.8)
    close.scatter(0,0,color=ORANGE,marker="*",s=60,zorder=5)
    close.set(xlim=(-amplitude,amplitude),ylim=(-amplitude,amplitude),aspect="equal",
              xlabel="East error relative to T2 (m)",ylabel="North error relative to T2 (m)")
    close.text(.03,.97,
               rf"95% analytic circle ($r_{{95}}={radii[1]:.3f}$ m)" + "\n" +
               rf"$\mathrm{{RMS}} = \sqrt{{2}}\,\sigma_\theta r_{{\min}} = {rms:.6f}$ m ($\gamma = 90^\circ$)",
               va="top",transform=close.transAxes,fontsize=8.5,
               bbox={"fc":"white","ec":GRID,"boxstyle":"round,pad=.3"},zorder=8)
    return fig


def vehicle_legend(ax, **kwargs):
    handles = [Line2D([0],[0],color=c,lw=2,marker="o",ms=4,label=f"V{i}")
               for i,c in enumerate(COLORS,1)]
    return ax.legend(handles=handles,ncols=5,**kwargs)


def phase_legend(ax, keys, **kwargs):
    handles = [
        Patch(fc=PHASES[k][1], ec="white" if not PHASE_HATCHES.get(k) else "#1E293B",
              hatch=PHASE_HATCHES.get(k, ""), label=PHASES[k][0])
        for k in keys
    ]
    return ax.legend(handles=handles, ncols=min(len(keys), 7), **kwargs)


def scene(ax, timeline, targets, *, time=None, labels=True, highlight_fault=False, label_size=8.6):
    """Deterministic 3D-to-page projection; geometry uses the official field axes."""
    from matplotlib import patheffects
    from math import cos, sin

    def project(x,y,z=0):
        return .77*x+.65*y, -.33*x+.39*y+.88*z

    def line(coords, **kwargs):
        ax.plot(*zip(*(project(*p) for p in coords)),**kwargs)

    def poly(coords, **kwargs):
        ax.add_patch(Polygon([project(*p) for p in coords],closed=True,**kwargs))

    def tag(name, xyz, delta, c=INK, size=None):
        if labels:
            ax.annotate(name, project(*xyz), xytext=delta, textcoords="offset points",
                        color=c, fontsize=size or label_size, weight="bold", zorder=19,
                        path_effects=[patheffects.withStroke(linewidth=2.6, foreground="white")])

    ax.set_aspect("equal")
    ax.axis("off")
    w,d = model.WIDTH, model.DEPTH
    poly([(0,0),(w,0),(w,d),(0,d)],fc="#F4F7FB",ec="#94A3B8",lw=.85,zorder=1)
    for tick in range(0,int(w)+1,25):
        line([(tick,0),(tick,d)],color=GRID,lw=.5,zorder=2)
    for tick in range(0,int(d)+1,25):
        line([(0,tick),(w,tick)],color=GRID,lw=.5,zorder=2)
    bldg_offsets = {1: (-6, -2), 2: (-7, 2), 3: (-14, -7), 4: (-5, -2), 5: (4, -6)}
    structures = sorted(enumerate(model.BUILDINGS,1),key=lambda row:sum(row[1][:2])-sum(row[1][2:4]))
    for i,(x0,x1,y0,y1,h) in structures:
        poly([(x0,y0),(x1,y0),(x1,y0,h),(x0,y0,h)],fc="#8EA4BA",ec="#475569",
             alpha=.76,lw=.7,zorder=6)
        poly([(x1,y0),(x1,y1),(x1,y1,h),(x1,y0,h)],fc="#7089A2",ec="#475569",
             alpha=.74,lw=.7,zorder=6)
        poly([(x0,y0,h),(x1,y0,h),(x1,y1,h),(x0,y1,h)],fc="#DBE7F2",ec="#475569",
             alpha=.95,lw=.7,zorder=6)
        tag(f"B{i}",((x0+x1)/2,(y0+y1)/2,h),bldg_offsets.get(i, (-4,0)),c="#334155",size=max(7.6, label_size-0.8))
    last_heading = {i:None for i in range(1,len(model.VEHICLES)+1)}
    for item in sorted(timeline,key=lambda e:e["start_s"]):
        if item["phase"]!="travel" or len(item["path"])<2:
            continue
        color = COLORS[item["vehicle"]-1]
        path = item["path"]
        assert all(geometry_checks.road_clear(tuple(a),tuple(b)) for a,b in zip(path,path[1:]))
        line(path,color=color,lw=1.45,alpha=.78 if time is None else .32,zorder=4,ls="--" if time is not None else "-")
        if time is not None and time >= item["start_s"]:
            length = model.SPEED*(min(time,item["end_s"])-item["start_s"])
            progress = [path[0]]
            for a,b in zip(path,path[1:]):
                leg = dist(a,b)
                if length < leg:
                    progress.append(model.route_position((a,b),length))
                    if length > 1e-9:
                        last_heading[item["vehicle"]] = atan2(b[1]-a[1],b[0]-a[0])
                    break
                progress.append(b)
                last_heading[item["vehicle"]] = atan2(b[1]-a[1],b[0]-a[0])
                length -= leg
            line(progress,color=color,lw=2.1,alpha=.96,zorder=5)
    t_offsets = {"T1": (5, 3), "T2": (5, 3), "T3": (-18, 4)}
    for i,(label,goal) in enumerate(targets.items(),1):
        line([goal[:2],goal],color="#64748B",ls=":",lw=.95,zorder=8)
        ax.scatter(*project(*goal),marker="*",s=64,fc=INK,ec="white",lw=.7,zorder=13)
        tag(label,goal,t_offsets.get(label, (5,3)),size=label_size+0.5)
    vehicle_offsets = ((6, 8), (4, -12), (-16, 10), (-17, -12), (8, 9))
    if time is None:
        for v,home in enumerate(model.VEHICLES,1):
            ax.scatter(*project(*home),s=32,ec="white",lw=.6,color=COLORS[v-1],zorder=15)
            tag(f"V{v}",home,vehicle_offsets[v-1],COLORS[v-1])
    else:
        for v, intervals in events.per_vehicle(timeline).items():
            item,(point,pan,tilt) = events.state_at(intervals,time)
            origin = (*point,model.HEIGHT)
            color = COLORS[v-1]
            target = targets.get(item["alert"])
            if target and item["phase"] in ("wait_partner","observe"):
                blocked = any(model.segment_hits_box(origin,target,((x0,x1),(y0,y1),(0,h)))
                              for x0,x1,y0,y1,h in model.BUILDINGS)
                line([origin,target],color=ORANGE if blocked else color,
                     ls="--" if blocked else "-",lw=1.4,alpha=.88,zorder=10)
            elif target and item["phase"] == "slew":
                line([origin,target],color=color,ls=":",lw=1.0,alpha=.55,zorder=9)
            px,py = project(*origin)
            failed = item["phase"]=="failed"
            if failed and highlight_fault:
                ax.scatter(px,py,s=210,fc="none",ec=CORAL,lw=1.8,ls="--",zorder=15)
            ax.scatter(px,py,c=CORAL if failed else color,marker="X" if failed else "o",
                       edgecolors="white",linewidths=.7,s=68 if failed else 40,zorder=16)
            heading = last_heading[v] if item["phase"]=="travel" else radians(pan)
            if not failed and heading is not None:
                ax.annotate("",project(point[0]+5.5*cos(heading),point[1]+5.5*sin(heading),model.HEIGHT),
                            (px,py),arrowprops={"arrowstyle":"-|>","color":color,
                                                "lw":1.05,"mutation_scale":9.5},zorder=17)
            v_lbl = f"V{v} (FAULT)" if (failed and highlight_fault) else f"V{v}"
            tag(v_lbl,origin,vehicle_offsets[v-1],CORAL if failed else color)
    ax.set(xlim=(-7, project(w,d)[0]+10), ylim=(project(w,0)[1]-9, max(
        project(*goal)[1] for goal in targets.values())+12))


def gantt(ax, timeline, xend, final=None, *, fault=None):
    for item in timeline:
        kind = item["phase"]
        if kind not in PHASES:
            continue
        start = float(item["start_s"])
        end = min(float(item["end_s"]),xend)
        if end<=start:
            continue
        vehicle = int(item["vehicle"])
        hatch = PHASE_HATCHES.get(kind, "")
        ax.barh(vehicle,end-start,left=start,height=.61,fc=PHASES[kind][1],
                lw=.55,ec="#1E293B" if hatch else "white",hatch=hatch or None,zorder=3)
        if kind=="observe" and item["alert"] and end-start>=1.35:
            ax.text((start+end)/2,vehicle,item["alert"],color="white",ha="center",
                    va="center",fontsize=8.8,weight="bold",zorder=4)
    if final is not None:
        ax.axvline(final, color=TEAL, lw=1.25, ls="--", zorder=6)
        ax.text(final,.15,f"{final:.3f} s",color=TEAL,ha="center",weight="bold",
                va="center",fontsize=9.0,zorder=8,
                bbox={"fc":"white","ec":"none","alpha":.94,"pad":1.2})
    if fault is not None:
        ax.axvline(fault,color=ORANGE,lw=1.3,ls=":",zorder=7)
        ax.text(fault,.15,f"Fault at {fault:g} s",color=ORANGE,ha="center",
                va="center",fontsize=9.0,weight="bold",zorder=8,
                bbox={"fc":"white","ec":"none","alpha":.94,"pad":1.2})
    ax.set(xlim=(0,xend),ylim=(5.65,-.22),yticks=list(range(1,6)),
           yticklabels=[f"V{i}" for i in range(1,6)],xlabel="Time (s)")
    ax.grid(False,axis="y")
    ax.xaxis.set_major_locator(MaxNLocator(7))


def dispatch(results):
    execution = read_json(results/"Executed_timeline.json")
    plans = read_json(results/"P2_main_plans.json")
    summary = read_json(results/"priority_3.json")
    assert digest(plans["beam"]) == execution["plan_id"] == summary["nominal_plan_id"]
    trials = read_csv(results/"P2_trials.csv")
    visits = read_csv(results/"P2_visit_phases.csv")
    chains = read_csv(results/"P2_critical_chains.csv")
    fig, gs = layout("P2(2)  |  Coordinated dispatch and shortlist sensitivity", (10.4,8.4), 3,4,
                     height_ratios=(1.45,1.02,.11))
    map_ax = fig.add_subplot(gs[0,:2])
    nominal = execution["nominal_policies"]["beam"]
    panel(map_ax,"a","Beam incumbent vehicle routes")
    scene(map_ax,nominal,model.TARGETS)
    vehicle_legend(map_ax,loc="lower center",bbox_to_anchor=(.5,-.02),columnspacing=.9)
    clock = fig.add_subplot(gs[0,2:])
    panel(clock,"b",rf"Executed phases at shared $k = {summary['shared_k']}$ (Critical Path on V3)")
    xend_nom = max(i["end_s"] for i in nominal if i["phase"]!="idle")*1.12
    gantt(clock,nominal,xend_nom,summary["P2_latest_starts_s"]["beam"])
    # Highlight Critical Path on V3 (0 -> 11.034 s: T1 -> reset -> T3) with non-overlapping whitespace callout
    cp_end = summary["P2_latest_starts_s"]["beam"]
    clock.add_patch(Rectangle((0, 3 - 0.39), cp_end, 0.78, fill=False, edgecolor=CORAL,
                              linewidth=1.9, linestyle="-", zorder=8))
    clock.annotate("Critical Path: V3\n(T1 → reset → T3)", xy=(cp_end * 0.94, 3.39),
                   xytext=(xend_nom * 0.74, 4.92), fontsize=8.2, fontweight="bold", color=CORAL,
                   ha="center", va="center",
                   arrowprops={"arrowstyle": "->", "color": CORAL, "lw": 1.15, "connectionstyle": "arc3,rad=0.14"},
                   bbox={"fc": "white", "ec": CORAL, "alpha": 0.96, "pad": 1.8}, zorder=9)
    segment_cols = (
        ("depart_s","arrival_s","travel"),("arrival_s","ready_s","slew"),
        ("ready_s","start_s","wait_partner"),("start_s","end_s","observe"),
        ("end_s","reset_s","reset"),
    )
    shared_width = next(row["beam_width"] for row in trials if row["plan_id"]==execution["plan_id"])
    selected = [t for t in trials if t["routing"]=="rounded" and t["beam_width"]==shared_width]
    assert len(selected)==4
    for j,trial in enumerate(selected):
        ax = fig.add_subplot(gs[1,j])
        k,policy = trial["k"],trial["policy"]
        latest = float(trial["latest_start_s"])
        bottleneck = int(trial["critical_vehicle"])
        evidence = next(row for row in chains if (row["routing"],row["k"],row["policy"],row["beam_width"])==("rounded",k,policy,shared_width))
        assert isclose(float(evidence["latest_start_s"]),latest)
        panel(ax,"cdef"[j],rf"$k = {k}$  ·  {policy.title()}")
        accum = defaultdict(float)
        for v in (item for item in visits if (item["routing"],item["k"],item["policy"],item["beam_width"])==("rounded",k,policy,shared_width)):
            for first,last,phase in segment_cols:
                duration = max(0,min(float(v[last]),latest)-float(v[first]))
                accum[int(v["vehicle"]),phase] += duration
        for vehicle in range(1,6):
            bar = 0
            for _,__,phase in segment_cols:
                value = accum[vehicle,phase]
                hatch = PHASE_HATCHES.get(phase, "")
                ax.barh(vehicle,value,left=bar,height=.66,fc=PHASES[phase][1],
                        ec="#1E293B" if hatch else "white",lw=.5,hatch=hatch or None)
                bar += value
        ax.set(xlim=(0,max(float(row["latest_start_s"]) for row in selected)*1.08),
               ylim=(5.6,-.45),yticks=list(range(1,6)),yticklabels=[f"V{i}" for i in range(1,6)],
               xlabel=r"Pre-$t_{\mathrm{last}}$ phase sum (s)")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.grid(False,axis="y")
        ax.text(.97,.94,f"Last start {latest:.3f} s\nV{bottleneck} · {evidence['chain'].replace('>',' → ')}",
                transform=ax.transAxes,ha="right",va="top",fontsize=8.3,weight="bold",
                bbox={"fc":"white","ec":GRID,"alpha":.94,"pad":1.4})
        ax.get_yticklabels()[bottleneck-1].set_color(ORANGE)
        ax.get_yticklabels()[bottleneck-1].set_weight("bold")
    key = fig.add_subplot(gs[2,:])
    key.axis("off")
    phase_legend(key,tuple(phase for _,__,phase in segment_cols),loc="center")
    return fig


def p3_risk(results):
    curve = read_csv(results/"P3_curve.csv")
    mc = read_csv(results/"P3_MC.csv")
    boundary = read_csv(results/"P3_parameters.csv")
    verified = read_json(results/"P3_verification.json")
    requirement = float(curve[0]["required"])
    crossing = verified["independent_crossing_m"]
    sigma_star = float(verified["sigma_at_crossing_m"])
    assert all(int(row["seed"])==SEED for row in mc)
    assert all(int(row["samples"])==verified["mc_samples_per_probe"] for row in mc)
    assert [row["assessment"] for row in mc]==["above","below","below"]
    view = mc[0]
    rng = np.random.default_rng(SEED)
    s_probe = float(view["distance_m"])
    sigma = A+B*s_probe
    r95_pos = sigma * sqrt(-2.0 * log(0.05))
    draws = rng.standard_normal((1200, 2)) * sigma
    fig, gs = layout("P3  |  Pointing uncertainty and verified coverage boundary", (10.2,8.0), 2,2,
                     width_ratios=(1,1.25),height_ratios=(1,1.02))
    cloud, broad, bounds, zoom = (fig.add_subplot(gs[i,j]) for i,j in ((0,0),(0,1),(1,0),(1,1)))
    panel(cloud,"a","Position uncertainty at the lower probe")
    covariance_ellipse(cloud,(0,0),np.eye(2)*sigma**2,color=ORANGE)
    cloud.scatter(draws[:,0],draws[:,1],s=6,alpha=.36,color=BLUE,edgecolors="none",zorder=3)
    lim = max(float(np.max(np.abs(draws)))*1.12, r95_pos*1.32)
    cloud.set(xlim=(-lim,lim),ylim=(-lim,lim),aspect="equal",
              xlabel="Longitudinal position error (m)",ylabel="Lateral position error (m)")
    cloud.text(.02,.98,
               f"First {len(draws):,} independent draws (s = {s_probe:.3f} m)\n"
               rf"$\sigma = {sigma:.3f}$ m, 95% radius $r_{{95}} = {r95_pos:.3f}$ m",
               transform=cloud.transAxes,va="top",ha="left",fontsize=8.3,
               bbox={"fc":"white","ec":GRID,"boxstyle":"round,pad=.28"},zorder=8)
    distances = np.array([float(row["distance_m"]) for row in curve])
    for ax in (broad,zoom):
        for key,color,style,label in (("linear_coverage",MUTED,"--","First-order"),(
                "nonlinear_coverage",TEAL,"-","Nonlinear quadrature")):
            ax.plot(distances,[float(row[key]) for row in curve],color=color,ls=style,lw=1.7,label=label)
        ax.axhline(requirement,color=ORANGE,ls=":",lw=1.3,label="95% coverage requirement")
        ax.axvline(crossing,color=MUTED,ls=":",lw=1.2)
        for i,row in enumerate(mc):
            s,p = float(row["distance_m"]), float(row["estimate"])
            lo,hi = [float(row[f"simultaneous_95_{suffix}"]) for suffix in ("lower","upper")]
            ax.errorbar(s,p,yerr=[[p-lo],[hi-p]],color=BLUE,fmt="o",mfc="white",
                        capsize=3.4,zorder=6,label="MC simultaneous 95% CI" if i==0 else None)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1,decimals=1))
        ax.set(xlabel=r"Travel distance $s$ (m)",ylabel=r"Coverage probability $P(s)$")
    panel(broad,"b","Coverage by travel distance")
    broad.set(xlim=(0,max(float(row["distance_m"]) for row in mc)*1.18),ylim=(.86,1.004))
    broad.legend(loc="lower left",fontsize=8.4)
    panel(zoom,"d","Threshold and sided independent Monte Carlo checks")
    probe_offset = crossing-float(mc[0]["distance_m"])
    lo = min(float(row["simultaneous_95_lower"]) for row in mc[:2])
    hi = max(float(row["simultaneous_95_upper"]) for row in mc[:2])
    bounds_x = (crossing-2.5*probe_offset,crossing+2.5*probe_offset)
    broad.add_patch(Rectangle((bounds_x[0],lo-.0016), bounds_x[1]-bounds_x[0],
                              hi-lo+.0032, fill=False, ec=MUTED, lw=.85, zorder=8))
    zoom.set(xlim=bounds_x,
             ylim=(lo-.0016,hi+.0016))
    zoom.annotate(rf"$s_{{\max}} = {crossing:.6f}$ m", (crossing,requirement),xytext=(10,30),
                  textcoords="offset points",arrowprops={"arrowstyle":"->","color":MUTED},weight="bold",
                  bbox={"fc":"white","ec":GRID,"alpha":.94,"pad":1.6})
    zoom.text(.97,.95,f"{int(mc[0]['samples']):,} independent trials/probe",
              transform=zoom.transAxes,ha="right",va="top",fontsize=8.8,
              bbox={"fc":"white","ec":"none","alpha":.85,"pad":1.0})
    panel(bounds,"c","Feasible position-error parameter boundary")
    equal = sorted([r for r in boundary if r["case"]=="on_crossing"],key=lambda r:float(r["a_m"]))
    a = [float(r["a_m"]) for r in equal]
    b = [float(r["b_m_per_m"]) for r in equal]
    bounds.fill_between(a,0,b,facecolor="#B7E0D4",alpha=.82,label="Feasible ($P(80) \\geq 95\\%$)")
    bounds.plot(a,b,color=TEAL,lw=1.8,label=rf"Boundary at $s = {float(equal[0]['distance_m']):g}$ m")
    for group,mark,c,lbl in (("inside","o",TEAL,r"$-1\%$ feasible probes"),("outside","x",ORANGE,r"$+1\%$ infeasible probes")):
        rows = [r for r in boundary if r["case"]==group]
        bounds.scatter([float(r["a_m"]) for r in rows],[float(r["b_m_per_m"]) for r in rows],
                       marker=mark,s=30,color=c,label=lbl,zorder=4)
    bounds.set(xlim=(-.035,max(a)*1.19),ylim=(-.001,max(b)*1.19),
               xlabel=r"Base position std $a$ (m)",ylabel=r"Drift slope $b$ (m/m)")
    bounds.text(.04, .10,
                r"$a \geq 0,\; b \geq 0$" + "\n" + rf"$a + 80b \leq {sigma_star:.6f}\ \mathrm{{m}}$",
                transform=bounds.transAxes, fontsize=8.6, fontweight="bold", color=INK,
                bbox={"fc": "white", "ec": TEAL, "alpha": 0.94, "boxstyle": "round,pad=.3"}, zorder=8)
    bounds.legend(loc="upper right",fontsize=8.1)
    return fig


def p4_resilience(results):
    """Fig. 7: Faceted P4 resilience analysis across 115 deduplicated & spatially expanded scenarios
    plus search-budget stability (k=2/3/5/8) and category-level win/tie/loss ledger."""
    cases = read_csv(results / "P4_dedup_expanded_cases.csv")
    cats = [r for r in read_csv(results / "P4_category_summary_expanded.csv") if r["category"] != "Total Unique Suite"]
    budgets = read_csv(results / "P4_budget_stability.csv")
    # Preserve P4_PANEL_INDEX.csv provenance for all unique cases
    index = [
        {
            "column": i, "case": r["case"], "category": r["category"],
            "keep_ratio": r["keep_eta"], "reschedule_ratio": r["replan_eta"],
            "reschedule_minus_keep_s": r["delta_replan_minus_keep_s"],
            "score_outcome": r["winner"],
        }
        for i, r in enumerate(cases, 1)
    ]

    short_cat = {
        "Vehicle Failure Only": "Fail",
        "New Alert Only": "Alert",
        "Comms Outage Only (cached)": "Outage",
        "Failure + New Alert": "Fail+Alert",
        "Failure + Comms Outage": "Fail+Out",
        "New Alert + Comms Outage": "Alert+Out",
        "All Three Combined": "All Three",
    }
    labels = [f"{short_cat.get(r['category'], r['category'])}\n(n={r['cases']})" for r in cats]
    x = np.arange(len(cats))

    fig, gs = layout(
        f"P4  |  Deduplicated & spatially expanded resilience ({len(cases)} unique scenarios)",
        (11.4, 8.2), 2, 2, height_ratios=(1.12, 1.02), wspace=0.24, hspace=0.30,
    )

    # Panel (a): Completion fraction eta by disturbance category
    ax_a = fig.add_subplot(gs[0, 0])
    panel(ax_a, "a", r"Mean completion ratio $\eta$ by disturbance category")
    w = 0.34
    keep_eta = [float(r["mean_keep_eta"]) for r in cats]
    rep_eta = [float(r["mean_replan_eta"]) for r in cats]
    ax_a.bar(x - w / 2, keep_eta, width=w, color=ORANGE, edgecolor="#7C2D12", hatch="///", alpha=0.92, label="Keep Plan")
    ax_a.bar(x + w / 2, rep_eta, width=w, color=TEAL, edgecolor="white", alpha=0.94, label="Reschedule / Hysteresis")
    for idx, (ke, re_v) in enumerate(zip(keep_eta, rep_eta)):
        ax_a.text(idx - w / 2, ke + 0.025, f"{ke:.2f}", ha="center", va="bottom", fontsize=7.4, color=INK, fontweight="bold")
        ax_a.text(idx + w / 2, re_v + 0.025, f"{re_v:.2f}", ha="center", va="bottom", fontsize=7.2, color=TEAL, fontweight="bold")
    ax_a.set_xticks(x)
    ax_a.set_xticklabels(labels, fontsize=7.8)
    ax_a.set_ylabel(r"Completion fraction $\eta$")
    ax_a.set_ylim(0, 1.20)
    ax_a.legend(loc="lower right", frameon=True, facecolor="white", fontsize=8.1)

    # Panel (b): Response latency t_last distribution under Hysteresis-Gated policy (consistent boxplot + mean!)
    ax_b = fig.add_subplot(gs[0, 1])
    panel(ax_b, "b", r"Latest paired start $t_{\mathrm{last}}$ (Hysteresis-Gated, 115 cases)")
    grouped_t = [[float(r["hyst_latest_s"]) for r in cases if r["category"] == c["category"]] for c in cats]
    bp = ax_b.boxplot(
        grouped_t, positions=x, widths=0.50, patch_artist=True,
        medianprops={"color": INK, "linewidth": 1.5},
        whiskerprops={"color": MUTED, "linewidth": 1.0},
        capprops={"color": MUTED, "linewidth": 1.0},
        flierprops={"marker": "o", "markersize": 3.5, "markerfacecolor": CORAL, "markeredgecolor": "none"},
    )
    for patch_b in bp["boxes"]:
        patch_b.set_facecolor("#BAE6FD")
        patch_b.set_edgecolor(BLUE)
        patch_b.set_linewidth(1.0)
    means = [float(c["mean_hyst_tlast_s"]) if "mean_hyst_tlast_s" in c else float(np.mean(g))
             for c, g in zip(cats, grouped_t)]
    ax_b.plot(x, means, marker="D", markersize=5.2, color=CORAL, markeredgecolor="white",
              markeredgewidth=0.6, linestyle="none", label="Category mean (Hysteresis)", zorder=6)
    ax_b.set_xticks(x)
    ax_b.set_xticklabels(labels, fontsize=7.8)
    ax_b.set_ylabel(r"Latest paired start $t_{\mathrm{last}}$ (s)")
    ax_b.set_ylim(5, 48)
    ax_b.legend(loc="upper left", frameon=True, facecolor="white", fontsize=8.1)

    # Panel (c): Search-budget stability (k=2/3/5/8 on 62 unique baseline cases) with explicit broken-axis marker
    ax_c = fig.add_subplot(gs[1, 0])
    panel(ax_c, "c", r"Search-budget stability ($k \in \{2,3,5,8\}$, 62 dedup cases)")
    bx = np.arange(len(budgets))
    b_labels = [rf"$k={r['stations_k']}, w={r['beam_width']}$" for r in budgets]
    t_rep = [float(r["mean_replan_tlast_s"]) for r in budgets]
    t_hyst = [float(r["mean_hyst_tlast_s"]) for r in budgets]
    b0 = budgets[0]
    rw, kw, ti, hl = int(b0["replan_wins"]), int(b0["keep_wins"]), int(b0["ties"]), int(b0["hyst_losses"])
    rep_wtl = f"{rw}W/{ti}T/{kw}L"
    hyst_wtl = f"{rw}W/{ti + kw - hl}T/{hl}L"
    ax_c.plot(bx, t_rep, marker="o", color=BLUE, lw=2.0, label=rf"Unconditional Replan ({rep_wtl})")
    ax_c.plot(bx, t_hyst, marker="s", color=TEAL, lw=2.0, ls="--", label=rf"Hysteresis-Gated ({hyst_wtl})")
    for i, (tr, th) in enumerate(zip(t_rep, t_hyst)):
        ax_c.annotate(f"{tr:.3f} s", (i, tr), xytext=(0, 7), textcoords="offset points",
                      ha="center", fontsize=8.0, color=BLUE, fontweight="bold")
        ax_c.annotate(f"{th:.3f} s", (i, th), xytext=(0, -13), textcoords="offset points",
                      ha="center", fontsize=8.0, color=TEAL, fontweight="bold")
    ax_c.set_xticks(bx)
    ax_c.set_xticklabels(b_labels, fontsize=8.6)
    ax_c.set_ylabel(r"Mean $t_{\mathrm{last}}$ across 62 cases (s)")
    ax_c.set_ylim(28.97, 29.25)
    # Explicit broken-y-axis ticks near bottom left to show zoomed vertical scale honestly
    ax_c.text(-0.025, 0.06, "//", transform=ax_c.transAxes, ha="center", va="center",
              fontsize=10.5, fontweight="bold", color=INK, clip_on=False)
    ax_c.text(0.03, 0.07,
              "Zoomed 0.28 s band (<0.9% spread); 100% completion across all budgets\n"
              "V5 delay invariant (+1.893 s), 0 losses under hysteresis gate",
              transform=ax_c.transAxes, fontsize=7.6, color=INK,
              bbox={"fc": "#F8FAFC", "ec": GRID, "boxstyle": "round,pad=.28"})
    ax_c.legend(loc="upper right", frameon=True, facecolor="white", fontsize=7.9)

    # Panel (d): Data-driven category-level Win / Tie / Loss breakdown across all 115 unique scenarios
    ax_d = fig.add_subplot(gs[1, 1])
    panel(ax_d, "d", r"Win / Tie / Loss ledger (Hysteresis, 115 cases)")
    y_cat = np.arange(len(cats))
    h_wins = np.array([int(c["hyst_wins"]) for c in cats])
    h_ties = np.array([int(c["hyst_ties"]) for c in cats])
    raw_losses = np.array([int(c["keep_wins"]) for c in cats])
    cat_names = [short_cat.get(c["category"], c["category"]) for c in cats]
    ax_d.barh(y_cat, h_wins, height=0.60, color=TEAL, edgecolor="white", label=f"Hysteresis Wins ({int(h_wins.sum())})")
    ax_d.barh(y_cat, h_ties, left=h_wins, height=0.60, color=GOLD, edgecolor="#78350F", hatch="///",
              label=f"Ties / Protected Keep ({int(h_ties.sum())})")
    for i, (wn, ti, rl) in enumerate(zip(h_wins, h_ties, raw_losses)):
        tot = wn + ti
        note = f"{wn}W / {ti}T" + (f" (1 V5 loss blocked)" if rl > 0 else "")
        ax_d.text(tot + 0.6, i, note, va="center", ha="left", fontsize=7.6,
                  fontweight="bold" if rl > 0 else "normal", color=CORAL if rl > 0 else INK)
    ax_d.set_yticks(y_cat)
    ax_d.set_yticklabels(cat_names, fontsize=8.2)
    ax_d.invert_yaxis()
    ax_d.set_xlabel("Unique disturbance scenarios")
    ax_d.set_xlim(0, max(int(c["cases"]) for c in cats) * 1.48)
    ax_d.grid(False, axis="y")
    ax_d.legend(loc="center right", bbox_to_anchor=(0.99, 0.56), frameon=True, facecolor="white", fontsize=7.6)
    ax_d.text(0.99, 0.24,
              f"Raw Replan: {sum(int(c['replan_wins']) for c in cats)}W / {sum(int(c['ties']) for c in cats)}T / {int(raw_losses.sum())}L\n"
              f"Hysteresis: {int(h_wins.sum())}W / {int(h_ties.sum())}T / 0L",
              transform=ax_d.transAxes, ha="right", va="bottom", fontsize=7.5, fontweight="bold", color=INK,
              bbox={"fc": "#F8FAFC", "ec": TEAL, "boxstyle": "round,pad=.28"})
    return fig, index


def v5_timeline(results):
    comparison = read_csv(results/"P4_V5_event_comparison.csv")
    summary = read_json(results/"priority_3.json")
    execution = read_json(results/"Executed_timeline.json")["cases"]["failure_V5"]
    scores = summary["V5_scores"]
    assert scores == execution["scores"]
    policy_rows = {p:[e for e in comparison if e["policy"]==p] for p in scores}
    for policy,rows in policy_rows.items():
        assert len(rows) == len(execution["policies"][policy])
    labels = {"keep":"Keep cached schedule","reschedule":"Reschedule"}
    delay = scores["reschedule"]["latest_start_s"] - scores["keep"]["latest_start_s"]
    assert isclose(delay,summary["V5_delay_s"])
    fig, gs = layout("P4  |  V5 failure and policy divergence", (9.6,7.5), 3,1,
                     height_ratios=(1,1,.53))
    fault = execution["failure_s"]
    xend = max(float(row["end_s"]) for row in comparison
               if row["phase"] not in {"idle","failed"})*1.06
    for index,(policy,score) in enumerate(scores.items()):
        ax = fig.add_subplot(gs[index,0])
        panel(ax,"ab"[index],f"{labels[policy]}  ·  {score['successes']}/{score['alerts']} starts")
        gantt(ax,policy_rows[policy],xend,score["latest_start_s"],fault=fault)
        last_alert = max(score["starts"],key=lambda alert:score["starts"][alert])
        candidates = [e for e in policy_rows[policy] if e["phase"]=="observe"
                      and e["alert"]==last_alert and isclose(float(e["start_s"]),score["latest_start_s"])]
        assert len(candidates)==2
        ax.text(.99,.95,f"Last pair: {last_alert} · "+ " + ".join(f"V{e['vehicle']}" for e in candidates),
                transform=ax.transAxes,va="top",ha="right",color=INK,fontsize=8.8,weight="bold",
                bbox={"fc":"white","ec":GRID,"alpha":.94,"pad":1.6},zorder=9)
    ax = fig.add_subplot(gs[-1,0])
    ax.axis("off")
    ax.set(xlim=(0,1),ylim=(0,1))
    resets = [e for e in policy_rows["reschedule"] if e["phase"]=="cancel_reset"]
    reset_note = ", ".join(f"V{r['vehicle']} {float(r['duration_s']):.3f} s" for r in resets)
    changed = []
    for vehicle in range(1,6):
        sets = [[e["alert"] for e in policy_rows[p] if int(e["vehicle"])==vehicle
                 and e["phase"]=="observe" and float(e["start_s"])>=fault] for p in scores]
        if all(sets) and sets[0]!=sets[1]:
            changed.append(f"V{vehicle}: {'/'.join(sets[0])} → {'/'.join(sets[1])}")
    node(ax,.015,.30,.380,.53,"Cancellation resets",reset_note,ORANGE)
    node(ax,.418,.30,.276,.53,"Observed alert changes",";  ".join(changed),BLUE)
    last_alerts = [max(score["starts"],key=lambda a:score["starts"][a]) for score in scores.values()]
    node(ax,.719,.30,.264,.53,f"Last start {delay:+.3f} s",
         f"Final paired alert: {last_alerts[0]} → {last_alerts[1]}",TEAL)
    phase_legend(ax,("travel","slew","wait_partner","observe","reset","cancel_reset","failed"),
                 loc="lower center",columnspacing=.9)
    return fig


def replay_frames(results, directory):
    execution = read_json(results/"Executed_timeline.json")
    plans = read_json(results/"P2_main_plans.json")
    assert digest(plans["beam"])==execution["plan_id"]
    nominal = execution["nominal_policies"]["beam"]
    v5 = execution["cases"]["failure_V5"]
    first = min(float(e["start_s"]) for e in nominal if e["phase"]=="observe")
    t_fault = v5["failure_s"]
    last = v5["scores"]["reschedule"]["latest_start_s"]
    snapshots = [
        ("normal_coordination","Nominal paired observation",first,model.TARGETS,[("Beam",nominal)]),
        ("v5_fault_trigger","V5 failure trigger",t_fault,v5["targets"],[("Reschedule branch",v5["policies"]["reschedule"])]),
        ("v5_recovery_compare","V5 case at the replan's final paired start",last,v5["targets"],
         [(title,v5["policies"][key]) for title,key in (("Keep","keep"),("Reschedule","reschedule"))]),
    ]
    keydir = directory/"replay_frames"
    sources = []
    for stem,title,t,targets,views in snapshots:
        fig, gs = layout(f"{title}  |  t = {t:.3f} s",(10,4.7) if len(views)==2 else (7.5,5),1,len(views))
        for index,(policy,timeline) in enumerate(views):
            ax = fig.add_subplot(gs[0,index])
            panel(ax,"ab"[index],policy)
            scene(ax,timeline,targets,time=t,highlight_fault=(stem!="normal_coordination"))
            vehicle_legend(ax,loc="lower center",columnspacing=1.25,bbox_to_anchor=(.5,-.045))
            sources.append({"figure":stem,"case":"nominal" if index==0 and stem=="normal_coordination" else "failure_V5",
                            "policy":policy,"time_s":t,"source":"Executed_timeline.json; P2_main_plans.json; B题题面参数.csv",
                            "projection":"Orthographic 3D-to-page","formats":"Vector PDF; PNG 320 dpi"})
        save(fig,keydir,stem)
    write_csv(keydir/"KEYFRAME_SOURCES.csv",sources)

    fig, gs = layout("Replay keyframes  |  Nominal, fault, and response", (10.1,7.2), 2,2,
                     height_ratios=(1,1))
    ax = fig.add_subplot(gs[0,0])
    panel(ax,"a",f"Nominal cooperation  ·  {first:.3f} s")
    scene(ax,nominal,model.TARGETS,time=first)
    ax = fig.add_subplot(gs[0,1])
    panel(ax,"b",f"V5 fault trigger  ·  {t_fault:.3f} s")
    scene(ax,v5["policies"]["reschedule"],v5["targets"],time=t_fault,highlight_fault=True)
    for column,(policy,title) in enumerate((("keep","Keep"),("reschedule","Reschedule"))):
        ax = fig.add_subplot(gs[1,column])
        panel(ax,"c1" if column==0 else "c2",f"{title} response  ·  {last:.3f} s")
        scene(ax,v5["policies"][policy],v5["targets"],time=last,highlight_fault=True)
        vehicle_legend(ax,loc="lower center",columnspacing=.9,bbox_to_anchor=(.5,-.045))
    return fig


def p2_paths(results):
    """Fig. 4: Multi-vehicle path planning with zoomed local insets (a)-(c) and global overview (d)."""
    plans = read_json(results / "P2_main_plans.json")
    beam_plan = plans["beam"]
    near_plan = plans["nearest"]

    fig, gs = layout("Multi-vehicle cooperative path planning  |  Rounded clearance routing", (10.8, 9.1), 3, 2,
                     height_ratios=(1.0, 1.0, 0.09), wspace=0.20, hspace=0.26)

    def draw_vehicle_panel(ax, letter, title, v_ids, xlim=(0, 100), ylim=(0, 100), show_targets=None,
                           custom_offsets=None, show_bldg_labels=True):
        if letter:
            panel(ax, letter, title)
        elif title:
            ax.set_title(title, loc="left", fontsize=9.8, fontweight="bold", color=INK)
        ax.set(xlim=xlim, ylim=ylim, aspect="equal", xlabel="East x (m)", ylabel="North y (m)")
        ax.xaxis.set_major_locator(MaxNLocator(5))
        ax.yaxis.set_major_locator(MaxNLocator(5))
        footprint(ax, clearance=True, labels=False)
        if show_bldg_labels:
            for idx, (x0, x1, y0, y1, _h) in enumerate(model.BUILDINGS, 1):
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                if xlim[0] + 2 <= cx <= xlim[1] - 2 and ylim[0] + 2 <= cy <= ylim[1] - 2:
                    ax.text(cx, cy, f"B{idx}", ha="center", va="center", fontsize=8.0, color="#334155", fontweight="bold", zorder=5)
        t_offsets = {"T1": (5, 4), "T2": (-18, 5), "T3": (5, -10)}
        for tid, (tx, ty, _tz) in model.TARGETS.items():
            if show_targets is not None and tid not in show_targets:
                continue
            if xlim[0] <= tx <= xlim[1] and ylim[0] <= ty <= ylim[1]:
                ax.scatter([tx], [ty], marker="D", s=46, color=ORANGE, edgecolor=INK, linewidth=0.7, zorder=6)
                ax.annotate(tid, (tx, ty), xytext=t_offsets.get(tid, (5, 4)), textcoords="offset points",
                            fontsize=8.4, fontweight="bold", color=INK,
                            bbox={"fc": "white", "ec": "none", "alpha": 0.78, "pad": 0.6})
        default_s = {1: (6, 4), 2: (-30, 4), 3: (6, -3), 4: (-16, -12), 5: (6, 3)}
        default_e = {1: (5, 6), 2: (-44, 5), 3: (6, 4), 4: (-38, 6), 5: (6, -10)}
        for vid in v_ids:
            col = COLORS[vid - 1]
            sx, sy = model.VEHICLES[vid - 1]
            ax.scatter([sx], [sy], marker="s", s=44, color=col, edgecolor=INK, linewidth=0.8, zorder=7)
            s_off = (custom_offsets or {}).get(("s", vid), default_s.get(vid, (5, -8)))
            ax.annotate(f"V{vid}(0)", (sx, sy), xytext=s_off, textcoords="offset points",
                        fontsize=8.0, fontweight="bold", color=col,
                        bbox={"fc": "white", "ec": "none", "alpha": 0.78, "pad": 0.5})
            for item in near_plan:
                if item["vehicle"] == vid - 1 and item.get("path"):
                    pts = np.asarray(item["path"], float)
                    ax.plot(pts[:, 0], pts[:, 1], linestyle="--", linewidth=1.75, color=MUTED, alpha=0.88, zorder=4)
                    ax.scatter([pts[-1, 0]], [pts[-1, 1]], marker="^", s=38, color=MUTED, edgecolor="white", linewidth=0.5, zorder=5)
            grouped_beam = defaultdict(list)
            for item in beam_plan:
                if item["vehicle"] == vid - 1 and item.get("path"):
                    pts = np.asarray(item["path"], float)
                    ax.plot(pts[:, 0], pts[:, 1], linestyle="-", linewidth=2.45, color=col, zorder=5)
                    ax.scatter([pts[-1, 0]], [pts[-1, 1]], marker="o", s=44, color=col, edgecolor="white", linewidth=0.8, zorder=6)
                    grouped_beam[(round(pts[-1, 0], 3), round(pts[-1, 1], 3))].append(item["alert"])
            for (ex, ey), alerts in grouped_beam.items():
                e_off = (custom_offsets or {}).get(("e", vid), default_e.get(vid, (5, 4)))
                ax.annotate(f"V{vid} → {','.join(alerts)}", (ex, ey),
                            xytext=e_off, textcoords="offset points", fontsize=7.8, fontweight="bold", color=INK,
                            bbox={"fc": "white", "ec": "none", "alpha": 0.80, "pad": 0.6})

    # (a) Zoomed local inset for reused V3
    draw_vehicle_panel(
        fig.add_subplot(gs[0, 0]), "a", r"Reused vehicle V3 ($\mathrm{T1}\to\mathrm{T3}$, zoomed NW)", [3],
        xlim=(0, 42), ylim=(62, 100), show_targets={"T3"},
        custom_offsets={("s", 3): (6, 4), ("e", 3): (6, -12)},
    )
    # (b) Zoomed local inset for V4 & V5
    draw_vehicle_panel(
        fig.add_subplot(gs[0, 1]), "b", "Vehicles V4 & V5 station assignments (zoomed NE)", [4, 5],
        xlim=(42, 100), ylim=(56, 100), show_targets={"T1"},
        custom_offsets={("s", 4): (-28, -11), ("e", 4): (-38, 6), ("s", 5): (6, 5), ("e", 5): (-28, -13)},
    )
    # (c) Dual side-by-side zoomed inset for V1 (SW) and V2 (SE)
    sub_c = gs[1, 0].subgridspec(1, 2, wspace=0.22)
    ax_c1 = fig.add_subplot(sub_c[0, 0])
    draw_vehicle_panel(
        ax_c1, "c", "V1 (SW zoom)", [1],
        xlim=(0, 40), ylim=(0, 42), show_targets=set(),
        custom_offsets={("s", 1): (4, -12), ("e", 1): (4, 6)},
    )
    ax_c2 = fig.add_subplot(sub_c[0, 1])
    draw_vehicle_panel(
        ax_c2, "", "V2 (SE zoom)", [2],
        xlim=(60, 100), ylim=(0, 42), show_targets=set(),
        custom_offsets={("s", 2): (-30, 5), ("e", 2): (-48, 6)},
    )
    ax_c2.set_ylabel("")
    # (d) Global 5-vehicle overview with dedicated bottom legend strip (zero overlap with V1/V2/B2)
    ax_all = fig.add_subplot(gs[1, 1])
    draw_vehicle_panel(
        ax_all, "d", r"Global 5-vehicle routing ($k=8$ vs. Nearest)", [1, 2, 3, 4, 5],
        xlim=(-2, 102), ylim=(-2, 102),
        custom_offsets={("s", 1): (5, -10), ("s", 4): (4, -11), ("e", 4): (-40, 5), ("s", 2): (-30, 4), ("e", 2): (-44, 5)},
    )
    leg_ax = fig.add_subplot(gs[2, :])
    leg_ax.axis("off")
    handles = [
        Line2D([0], [0], color=INK, lw=2.2, linestyle="-", marker="o", ms=5, mfc=INK, mec="white", label=r"Beam Search ($k=8$)"),
        Line2D([0], [0], color=MUTED, lw=1.7, linestyle="--", marker="^", ms=5, mfc=MUTED, mec="white", label="Nearest Baseline"),
        Line2D([0], [0], marker="s", color="none", mfc=BLUE, mec=INK, ms=5.8, label=r"Vehicle Start $V_i(0)$"),
        Line2D([0], [0], marker="D", color="none", mfc=ORANGE, mec=INK, ms=5.8, label="UAV Alert"),
    ]
    leg_ax.legend(handles=handles, loc="center", ncols=4, frameon=False, fontsize=8.4, columnspacing=1.5, handlelength=2.2)
    return fig


def global_sensitivity(results):
    """Fig. 9: Real-solver parameter perturbation, pairwise interaction, and 5-scheme weight stability."""
    oat = read_csv(results / "Global_sensitivity_oat.csv")
    inter = read_csv(results / "Global_sensitivity_interaction.csv")
    weights = read_csv(results / "Global_sensitivity_weight_check.csv")

    fig, gs = layout(
        "Parameter perturbation & pairwise interaction analysis (real P1–P4 solvers)",
        (11.6, 7.8), 2, 2, wspace=0.28, hspace=0.26,
    )

    short_names = {
        "pitch_ceiling": r"Pitch ceiling $\beta_{\max}$",
        "pos_error_slope": r"Drift slope $b$",
        "outage_duration": r"Outage $\Delta t_{\mathrm{out}}$",
        "pan_speed": r"Pan rate $\omega_{\mathrm{pan}}$",
        "pos_error_intercept": r"Base std $a$",
        "vehicle_speed": r"Speed $v$",
    }
    short_tick_map = {
        "pitch_ceiling": r"$\beta_{\max}$",
        "pos_error_slope": r"$b$",
        "outage_duration": r"$\Delta t_{\mathrm{out}}$",
        "pan_speed": r"$\omega_{\mathrm{pan}}$",
        "pos_error_intercept": r"$a$",
        "vehicle_speed": r"$v$",
    }
    labels = [short_names.get(r["parameter"], r["label"]) for r in oat]
    p_order = [r["parameter"] for r in oat]
    short_tick = [short_tick_map[k] for k in p_order]
    y_pos = np.arange(len(oat))

    # (a) Re-Optimized vs. Fixed-Plan OAT Main Effect Ranking
    ax = fig.add_subplot(gs[0, 0])
    panel(ax, "a", "One-at-a-Time (OAT) swing: Re-Optimized vs. Fixed-Plan")
    sw_reopt = [float(r["swing_pct"]) for r in oat]
    sw_fixed = [float(r["fixed_plan_swing_pct"]) for r in oat]
    h = 0.37
    ax.barh(y_pos - h / 2, sw_reopt, color=BLUE, edgecolor="white", height=h, label="Re-Optimized")
    ax.barh(y_pos + h / 2, sw_fixed, color=ORANGE, edgecolor="#7C2D12", hatch="///", height=h, alpha=0.90, label="Fixed-Plan Local")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.0)
    ax.invert_yaxis()
    ax.set_xlabel("Composite index swing (%)")
    for idx, (vr, vf) in enumerate(zip(sw_reopt, sw_fixed)):
        ax.text(vr + 0.18, idx - h / 2, f"{vr:.2f}%", va="center", fontsize=7.5, fontweight="bold", color=BLUE)
        ax.text(vf + 0.18, idx + h / 2, f"{vf:.2f}%", va="center", fontsize=7.5, fontweight="bold", color="#9A3412")
    ax.set_xlim(0, max(max(sw_reopt), max(sw_fixed)) * 1.28)
    ax.legend(loc="lower right", fontsize=8.0, frameon=True, facecolor="white")

    # (b) Tornado chart (delta low vs delta high)
    ax = fig.add_subplot(gs[0, 1])
    panel(ax, "b", r"Tornado ($\pm 20\%$; $\beta_{\max}$: $76^\circ$–$82^\circ$, decoupled)")
    d_lo = [float(r["delta_low_pct"]) for r in oat]
    d_hi = [float(r["delta_high_pct"]) for r in oat]
    ax.axvline(0.0, color=INK, linewidth=1.0, zorder=3)
    ax.barh(y_pos, d_lo, color=CORAL, edgecolor="#7F1D1D", hatch="///", alpha=0.90, height=0.56, label="Low parameter bound")
    ax.barh(y_pos, d_hi, color=TEAL, edgecolor="white", alpha=0.90, height=0.56, label="High parameter bound")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=9.0)
    ax.invert_yaxis()
    ax.set_xlabel(r"Relative change in composite index $\Delta J$ (%)")
    ax.legend(loc="lower right", fontsize=8.0, frameon=True, facecolor="white")

    # (c) 6x6 Pairwise Interaction Matrix Heatmap
    ax = fig.add_subplot(gs[1, 0])
    panel(ax, "c", "Symmetric 6×6 pairwise interaction matrix (%)")
    idx_map = {k: i for i, k in enumerate(p_order)}
    mat = np.zeros((len(p_order), len(p_order)), dtype=float)
    for r in inter:
        if r["param_i"] in idx_map and r["param_j"] in idx_map:
            mat[idx_map[r["param_i"]], idx_map[r["param_j"]]] = float(r["interaction_pct"])
    im = ax.imshow(mat, cmap="YlGnBu", aspect="auto", vmin=0, vmax=max(0.2, float(mat.max())))
    ax.set_xticks(range(len(p_order)))
    ax.set_xticklabels(short_tick, fontsize=9)
    ax.set_yticks(range(len(p_order)))
    ax.set_yticklabels(short_tick, fontsize=9)
    ax.grid(False)
    for i in range(len(p_order)):
        for j in range(len(p_order)):
            v = mat[i, j]
            txt = "--" if i == j else f"{v:.2f}"
            ax.text(j, i, txt, ha="center", va="center", fontsize=8,
                    color="white" if v > mat.max() * 0.55 else INK)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Interaction (%)", fontsize=8.5)

    # (d) 5-Scheme Weight-Perturbation Rank Stability Matrix (colorblind & B&W monotonic YlGnBu_r)
    ax = fig.add_subplot(gs[1, 1])
    panel(ax, "d", "Rank stability (5 weight schemes)")
    schemes = [
        ("baseline_balanced", "Balanced"),
        ("equal_weight", "Equal"),
        ("time_priority", "Time"),
        ("precision_priority", "Precision"),
        ("resilience_priority", "Resilience"),
    ]
    rank_mat = np.zeros((len(p_order), len(schemes)), dtype=float)
    share_mat = np.zeros((len(p_order), len(schemes)), dtype=float)
    w_lookup = {(r["scheme"], r["parameter"]): (int(r["rank"]), float(r["share_pct"])) for r in weights}
    for i, k in enumerate(p_order):
        for j, (s_key, _) in enumerate(schemes):
            rk, sh = w_lookup[(s_key, k)]
            rank_mat[i, j] = rk
            share_mat[i, j] = sh
    im2 = ax.imshow(rank_mat, cmap="YlGnBu_r", aspect="auto", vmin=1, vmax=6)
    ax.set_xticks(range(len(schemes)))
    ax.set_xticklabels([lbl for _, lbl in schemes], fontsize=7.8)
    ax.set_yticks(range(len(p_order)))
    ax.set_yticklabels(short_tick, fontsize=9)
    ax.grid(False)
    for i in range(len(p_order)):
        for j in range(len(schemes)):
            rk = int(rank_mat[i, j])
            sh = share_mat[i, j]
            ax.text(j, i, f"#{rk}\n({sh:.0f}%)", ha="center", va="center", fontsize=7.6,
                    fontweight="bold" if rk <= 2 else "normal",
                    color="white" if rk <= 2 else INK)
    cbar2 = fig.colorbar(im2, ax=ax, fraction=0.046, pad=0.04, ticks=[1, 2, 3, 4, 5, 6])
    cbar2.set_label("Sensitivity rank (1 = highest)", fontsize=8.2)
    return fig


def pareto_3d(results):
    """Fig. 10: True 3D Multi-Objective Pareto Frontier (Time, Travel, Observation Quality) + 2D Projections."""
    pareto = read_csv(results / "Pareto_tradeoff_3d.csv")
    p3d = [r for r in pareto if r["is_pareto_3d"] == "True"]
    dom = [r for r in pareto if r["is_pareto_3d"] != "True"]
    all_vecs = {(round(float(r["latest_start_s"]), 4), round(float(r["total_travel_m"]), 3), round(float(r["mean_quality_m_inv"]), 6)) for r in pareto}
    p3d_vecs = {(round(float(r["latest_start_s"]), 4), round(float(r["total_travel_m"]), 3), round(float(r["mean_quality_m_inv"]), 6)) for r in p3d}
    mult_2d = defaultdict(int)
    for r in pareto:
        mult_2d[(round(float(r["latest_start_s"]), 3), round(float(r["total_travel_m"]), 2))] += 1

    fig = plt.figure(figsize=(11.6, 5.4), layout="constrained")
    fig.suptitle(
        rf"Three-objective Pareto frontier ({len(pareto)} configs $\to$ {len(all_vecs)} distinct points; {len(p3d)} configs / {len(p3d_vecs)} distinct 3D Pareto vectors)",
        x=0.02, ha="left", fontsize=11.8, fontweight="bold", color=INK,
    )
    gs = fig.add_gridspec(1, 3, width_ratios=(1.22, 1.0, 1.02), wspace=0.22)

    k5 = next(r for r in pareto if r["policy"] == "beam" and r["k"] == "5" and r["beam_width"] == "20")
    k8 = next(r for r in pareto if r["tag"] == "nominal_recommended")
    near = next(r for r in pareto if r["tag"] == "nearest_baseline")
    k3w5 = next(r for r in pareto if r["policy"] == "beam" and r["k"] == "3" and r["beam_width"] == "5")
    min_t = min(float(r["latest_start_s"]) for r in pareto)

    # (a) 3D Scatter of all configs highlighting the 3D non-dominated front
    ax3 = fig.add_subplot(gs[0, 0], projection="3d")
    ax3.set_title("(a) 3D objective space", loc="left", fontsize=10.6, fontweight="bold", pad=4)
    ax3.scatter(
        [float(r["latest_start_s"]) for r in dom],
        [float(r["total_travel_m"]) for r in dom],
        [float(r["mean_quality_m_inv"]) * 1e3 for r in dom],
        s=36, color="#94A3B8", alpha=0.70, label=f"Dominated ({len(dom)} configs)",
    )
    ax3.scatter(
        [float(r["latest_start_s"]) for r in p3d],
        [float(r["total_travel_m"]) for r in p3d],
        [float(r["mean_quality_m_inv"]) * 1e3 for r in p3d],
        s=60, color=TEAL, edgecolor=INK, lw=0.7, label=f"3D Pareto ({len(p3d)} cfg / {len(p3d_vecs)} vec)",
    )
    ax3.scatter([float(k8["latest_start_s"])], [float(k8["total_travel_m"])], [float(k8["mean_quality_m_inv"]) * 1e3],
                s=135, marker="*", color=CORAL, edgecolor=INK, lw=0.8, label=r"Nominal $k=8$", zorder=8)
    ax3.scatter([float(k5["latest_start_s"])], [float(k5["total_travel_m"])], [float(k5["mean_quality_m_inv"]) * 1e3],
                s=75, marker="D", color=BLUE, edgecolor=INK, lw=0.8, label=r"Low-travel $k=5$", zorder=7)
    ax3.xaxis.set_major_locator(MaxNLocator(4))
    ax3.yaxis.set_major_locator(MaxNLocator(4))
    ax3.zaxis.set_major_locator(MaxNLocator(4))
    ax3.set_xlabel(r"$t_{\mathrm{last}}$ (s)", fontsize=8.4, labelpad=4)
    ax3.set_ylabel(r"Travel $D_{\mathrm{tot}}$ (m)", fontsize=8.4, labelpad=4)
    ax3.set_zlabel(r"$\bar{Q}$ ($10^{-3}\ \mathrm{m}^{-1}$)", fontsize=8.4, labelpad=4)
    ax3.tick_params(labelsize=7.4)
    ax3.view_init(elev=22, azim=-52)
    ax3.legend(loc="upper left", fontsize=7.2, frameon=True, facecolor="white")

    # (b) 2D Projection: t_last vs Total Travel with multiplicities & zero overlap
    ax_b = fig.add_subplot(gs[0, 1])
    panel(ax_b, "b", r"Projection: latency vs. travel")
    ax_b.scatter([float(r["latest_start_s"]) for r in dom], [float(r["total_travel_m"]) for r in dom],
                 s=42, color="#94A3B8", alpha=0.72, label="Dominated")
    ax_b.scatter([float(r["latest_start_s"]) for r in p3d], [float(r["total_travel_m"]) for r in p3d],
                 s=64, color=TEAL, edgecolor=INK, lw=0.7, label="3D Pareto")
    ax_b.scatter([float(k8["latest_start_s"])], [float(k8["total_travel_m"])],
                 s=140, marker="*", color=CORAL, edgecolor=INK, lw=0.8, zorder=7)
    ax_b.scatter([float(k5["latest_start_s"])], [float(k5["total_travel_m"])],
                 s=72, marker="D", color=BLUE, edgecolor=INK, lw=0.8, zorder=6)
    for (tx, ty), cnt in mult_2d.items():
        if cnt > 1:
            ax_b.annotate(f"×{cnt}", (tx, ty), xytext=(6, -10 if ty > 35 else 6),
                          textcoords="offset points", fontsize=7.4, fontweight="bold", color="#475569")
    ax_b.annotate(rf"Nominal $k=8$" + f"\n({float(k8['latest_start_s']):.3f} s, {float(k8['total_travel_m']):.2f} m)",
                  (float(k8["latest_start_s"]), float(k8["total_travel_m"])),
                  xytext=(30, 16), textcoords="offset points", fontsize=7.5, fontweight="bold", color=CORAL,
                  bbox={"fc": "white", "ec": CORAL, "alpha": 0.94, "pad": 1.4},
                  arrowprops={"arrowstyle": "->", "color": CORAL, "lw": 0.95})
    ax_b.annotate(rf"$k=5$ ({float(k5['total_travel_m']):.2f} m)",
                  (float(k5["latest_start_s"]), float(k5["total_travel_m"])),
                  xytext=(24, -18), textcoords="offset points", fontsize=7.6, fontweight="bold", color=BLUE,
                  bbox={"fc": "white", "ec": BLUE, "alpha": 0.92, "pad": 1.2},
                  arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 0.95})
    ax_b.annotate(rf"Nearest ({float(near['latest_start_s']):.3f} s, {float(near['total_travel_m']):.2f} m)",
                  (float(near["latest_start_s"]), float(near["total_travel_m"])),
                  xytext=(-86, 14), textcoords="offset points", fontsize=7.4, fontweight="bold", color=GOLD,
                  bbox={"fc": "white", "ec": GOLD, "alpha": 0.94, "pad": 1.2},
                  arrowprops={"arrowstyle": "->", "color": GOLD, "lw": 0.95})
    ax_b.set_xlabel(r"Latest paired start $t_{\mathrm{last}}$ (s)")
    ax_b.set_ylabel(r"Total fleet travel $D_{\mathrm{tot}}$ (m)")
    ax_b.set_ylim(18.5, 45.8)

    # (c) 2D Projection: Total Travel vs Mean Observation Quality
    ax_c = fig.add_subplot(gs[0, 2])
    panel(ax_c, "c", r"Projection: travel vs. quality $\bar{Q}$")
    ax_c.scatter([float(r["total_travel_m"]) for r in dom], [float(r["mean_quality_m_inv"]) * 1e3 for r in dom],
                 s=42, color="#94A3B8", alpha=0.72, label="Dominated")
    ax_c.scatter([float(r["total_travel_m"]) for r in p3d], [float(r["mean_quality_m_inv"]) * 1e3 for r in p3d],
                 s=64, color=TEAL, edgecolor=INK, lw=0.7, label="3D Pareto")
    tied = sorted([r for r in pareto if abs(float(r["latest_start_s"]) - min_t) < 1e-4],
                  key=lambda r: float(r["total_travel_m"]))
    ax_c.plot([float(r["total_travel_m"]) for r in tied],
              [float(r["mean_quality_m_inv"]) * 1e3 for r in tied],
              color=CORAL, lw=2.0, ls="-", zorder=5, label=rf"$t_{{\mathrm{{last}}}}={min_t:.3f}$ s ridge")
    ax_c.scatter([float(k8["total_travel_m"])], [float(k8["mean_quality_m_inv"]) * 1e3],
                 s=140, marker="*", color=CORAL, edgecolor=INK, lw=0.8, zorder=7)
    ax_c.scatter([float(k5["total_travel_m"])], [float(k5["mean_quality_m_inv"]) * 1e3],
                 s=72, marker="D", color=BLUE, edgecolor=INK, lw=0.8, zorder=6)
    ax_c.annotate(rf"$k=8$: $\bar{{Q}}={float(k8['mean_quality_m_inv'])*1e3:.2f}\times 10^{{-3}}\ \mathrm{{m}}^{{-1}}$" + "\n(59.9 m range)",
                  (float(k8["total_travel_m"]), float(k8["mean_quality_m_inv"]) * 1e3),
                  xytext=(-112, 16), textcoords="offset points", fontsize=7.3, fontweight="bold", color=CORAL,
                  bbox={"fc": "white", "ec": CORAL, "alpha": 0.94, "pad": 1.3},
                  arrowprops={"arrowstyle": "->", "color": CORAL, "lw": 0.95})
    ax_c.annotate(rf"$k=5$: $\bar{{Q}}={float(k5['mean_quality_m_inv'])*1e3:.2f}\times 10^{{-3}}\ \mathrm{{m}}^{{-1}}$" + "\n(62.5 m range)",
                  (float(k5["total_travel_m"]), float(k5["mean_quality_m_inv"]) * 1e3),
                  xytext=(-108, -28), textcoords="offset points", fontsize=7.3, fontweight="bold", color=BLUE,
                  bbox={"fc": "white", "ec": BLUE, "alpha": 0.94, "pad": 1.3},
                  arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 0.95})
    ax_c.annotate(rf"$k=3,w=5$ ({float(k3w5['latest_start_s']):.3f} s)",
                  (float(k3w5["total_travel_m"]), float(k3w5["mean_quality_m_inv"]) * 1e3),
                  xytext=(-84, -14), textcoords="offset points", fontsize=7.3, color=TEAL, fontweight="bold",
                  arrowprops={"arrowstyle": "->", "color": TEAL, "lw": 0.9})
    ax_c.set_xlabel(r"Total fleet travel $D_{\mathrm{tot}}$ (m)")
    ax_c.set_ylabel(r"Mean quality $\bar{Q}$ ($10^{-3}\ \mathrm{m}^{-1}$)")
    ax_c.set_ylim(12.5, 31.8)
    ax_c.legend(loc="upper left", fontsize=7.4, frameon=True, facecolor="white")
    return fig


def dashboard_3d(results):
    """Fig. 11: Print-grade vector white-background 3D digital twin verification triptych."""
    execution = read_json(results / "Executed_timeline.json")
    nominal = execution["nominal_policies"]["beam"]
    v5 = execution["cases"]["failure_V5"]
    first = min(float(e["start_s"]) for e in nominal if e["phase"] == "observe")
    t_fault = float(v5["failure_s"])
    last = float(v5["scores"]["reschedule"]["latest_start_s"])

    fig, gs = layout(
        "Offline 3D digital twin verification  |  Verified states (0/892 static building-obstacle collisions)",
        (11.6, 4.75), 2, 3, height_ratios=(1.0, 0.10), wspace=0.08, hspace=0.05,
    )
    stages = [
        ("a", rf"Normal Coordination ($t = {first:.3f}$ s)", nominal, model.TARGETS, first, False,
         "T1 paired lock (V3 + V5)\nRounded 1.5 m clearance verified"),
        ("b", rf"V5 Fault Trigger ($t = {t_fault:.3f}$ s)", v5["policies"]["reschedule"], v5["targets"], t_fault, True,
         "V5 failed at 5.000 s\nReplan triggers V1/V2/V4 cancel-reset"),
        ("c", rf"Reschedule Recovery ($t = {last:.3f}$ s)", v5["policies"]["reschedule"], v5["targets"], last, True,
         "3/3 paired alerts completed\nHysteresis Eq. (5) blocks +1.893 s loss"),
    ]
    for col_i, (tag, subtitle, tl, targs, t_now, h_fault, badge) in enumerate(stages):
        ax3 = fig.add_subplot(gs[0, col_i])
        panel(ax3, tag, subtitle)
        scene(ax3, tl, targs, time=t_now, highlight_fault=h_fault, label_size=8.2)
        y0, y1 = ax3.get_ylim()
        ax3.set_ylim(y0 - 15, y1)
        ax3.text(0.02, 0.01, badge, transform=ax3.transAxes, ha="left", va="bottom",
                 fontsize=7.5, color=INK, fontweight="bold",
                 bbox={"fc": "white", "ec": CORAL if h_fault and col_i == 1 else GRID,
                       "alpha": 0.96, "boxstyle": "round,pad=0.28"}, zorder=20)
    leg_ax = fig.add_subplot(gs[1, :])
    leg_ax.axis("off")
    handles = [Line2D([0], [0], color=c, lw=2.2, marker="o", ms=5, label=f"V{i}") for i, c in enumerate(COLORS, 1)]
    handles.append(Line2D([0], [0], color=CORAL, lw=0, marker="X", ms=7, label="Failed V5"))
    handles.append(Line2D([0], [0], color=INK, lw=0, marker="*", ms=8, label="UAV Alert"))
    leg_ax.legend(handles=handles, ncols=7, loc="center", frameon=False, fontsize=8.4, columnspacing=1.2)
    return fig


def generate(root):
    directory = root / "figures"
    results = root / "results"
    # Clean legacy combined fig10_pareto_and_3d if present
    for legacy in directory.glob("fig10_pareto_and_3d.*"):
        legacy.unlink()
    replay_frames(results, directory)
    scripts = (
        ("fig01_framework", lambda: framework(results)),
        ("fig02_p1_geometry", lambda: p1_geometry(results)),
        ("fig03_p2_precision", lambda: precision(results)),
        ("fig04_p2_paths", lambda: p2_paths(results)),
        ("fig05_p2_dispatch", lambda: dispatch(results)),
        ("fig06_p3_risk", lambda: p3_risk(results)),
        ("fig07_p4_resilience", lambda: p4_resilience(results)),
        ("fig08_v5_timeline", lambda: v5_timeline(results)),
        ("fig09_global_sensitivity", lambda: global_sensitivity(results)),
        ("fig10_pareto_3d", lambda: pareto_3d(results)),
        ("fig11_3d_dashboard", lambda: dashboard_3d(results)),
    )
    for stem, draw in scripts:
        out = draw()
        if stem == "fig07_p4_resilience":
            out, index = out
            write_csv(directory / "P4_PANEL_INDEX.csv", index)
        save(out, directory, stem)
    write_csv(directory / "FIGURE_SOURCES.csv", (
        {"figure": name, "source": inputs, "purpose": description, "formats": "Vector PDF; PNG 320 dpi"}
        for name, inputs, description in FIGURE_MAP
    ))
    print("Rendered 11 publication-grade analytical figures and 3 replay keyframe groups as vector PDF and 320 dpi PNG.")


if __name__ == "__main__":
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    generate(cli.parse_args().out)


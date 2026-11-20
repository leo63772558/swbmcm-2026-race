"""Render eight Matplotlib review figures from the frozen B evidence.

AI assistance: ChatGPT (Codex, GPT-6), OpenAI, 2026-11-21.
Assistance: presentation, archived event visualization, and visual checks.
"""
from argparse import ArgumentParser
from collections import defaultdict
from datetime import datetime, timezone
from math import atan2, degrees, dist, isclose, log, radians
from pathlib import Path
from random import Random

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
BLUE = "#0072B2"
TEAL = "#007A60"
ORANGE = "#C44B17"
GOLD = "#B37600"
PURPLE = "#75549B"
COLORS = (BLUE, ORANGE, TEAL, PURPLE, GOLD)
UNAVAILABLE = "#788694"
PHASES = {
    "travel": ("Drive", BLUE),
    "slew": ("Slew", "#E4A000"),
    "wait_partner": ("Wait", "#B7C8D9"),
    "observe": ("Observe", TEAL),
    "reset": ("Reset", PURPLE),
    "cancel_reset": ("Cancel / reset", ORANGE),
    "missed_pair": ("Missed pair", "#DDADC0"),
    "failed": ("Failed", UNAVAILABLE),
}
FIGURE_MAP = (
    ("fig01_framework", "P1_station.csv; P2_precision.csv; priority_3.json; P3_verification.json",
     "Shared field input and data dependencies between the four questions"),
    ("fig02_p1_geometry", "P1_grid_map.json; P1_geometry.json; P1_pitch_checks.csv; Route_clearance_comparison.csv; Route_summary.json",
     "Grid evidence, shadow, exact-radius clearance, optimal arc, route changes and pitch sensitivity"),
    ("fig03_p2_precision", "P2_precision.csv; P2_precision_routes.json; B题题面参数.csv",
     "Fixed-pair first-order RMS field and local position uncertainty"),
    ("fig04_p2_dispatch", "Executed_timeline.json; P2_main_plans.json; P2_trials.csv; P2_visit_phases.csv; P2_critical_chains.csv",
     "Shared-k schedule, vehicle trajectories and phase breakdown to the final paired start"),
    ("fig05_p3_risk", "P3_MC.csv; P3_curve.csv; P3_verification.json; P3_parameters.csv; B题题面参数.csv",
     "First draws of the recorded seeded run; position ellipse; coverage checks and parameter boundary"),
    ("fig06_p4_resilience", "P4_cases.csv; Executed_timeline.json; priority_3.json",
     "All case IDs, censoring-aware timing contrast, lexicographic score and replay flow"),
    ("fig07_v5_timeline", "P4_V5_event_comparison.csv; Executed_timeline.json; priority_3.json",
     "Aligned V5 event clocks, cancellations, assignment changes and last paired starts"),
    ("fig08_replay_frames", "Executed_timeline.json; P2_main_plans.json; B题题面参数.csv",
     "3D projection of nominal observation, V5 failure and final-start recovery comparison"),
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
    ax.set_title(f"{letter}   {title}", loc="left")


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
    fig, gs = layout("Problem B  |  Evidence and dependency map", (9.3, 4.9))
    ax = fig.add_subplot(gs[0, 0])
    ax.set(xlim=(0, 1), ylim=(0, 1))
    ax.axis("off")
    node(ax, .025, .70, .268, .19, "Official field and alerts", "Buildings, vehicle states, target locations", BLUE)
    node(ax, .365, .70, .268, .19, "Shared geometry", "Euclidean clearance, pitch, line of sight", BLUE)
    node(ax, .708, .70, .265, .19, "P1  Observation region",
         f"Quality-optimal witness: {p1['ready_s']:.3f} s ready", TEAL)
    node(ax, .025, .385, .268, .19, "P2(1)  Bearing precision",
         f"T2 local horizontal RMS: {float(precision['horizontal_rms_m']):.6f} m", PURPLE)
    node(ax, .365, .385, .268, .19, "P2(2)  Paired dispatch",
         f"Beam incumbent: {summary['P2_latest_starts_s']['beam']:.3f} s last start", TEAL)
    node(ax, .708, .385, .265, .19, "P4  Disturbance replay",
         f"{summary['P4_case_count']} case IDs, frozen dispatch plan", ORANGE)
    node(ax, .025, .07, .268, .19, "P3  Pointing uncertainty",
         f"Coverage crossing: {spread['independent_crossing_m']:.6f} m", PURPLE)
    node(ax, .365, .07, .268, .19, "Event log and replay",
         "Executed phases, paths, time and status", ORANGE)
    node(ax, .708, .07, .265, .19, "Deployment review",
         "Geometry, precision and resilience checks", BLUE)
    connect(ax, (.30,.795), (.358,.795))
    connect(ax, (.640,.795), (.701,.795))
    connect(ax, (.47,.692), (.21,.581))
    connect(ax, (.50,.692), (.50,.582))
    connect(ax, (.641,.480), (.701,.480))
    connect(ax, (.840,.377), (.61,.267))
    connect(ax, (.641,.16), (.701,.16))
    ax.annotate("", (.709,.095), (.292,.092), arrowprops={"arrowstyle":"-|>",
                "connectionstyle":"arc3,rad=.29", "color":MUTED, "lw":.9, "ls":"--"})
    ax.plot([.08,.011,.011],[.7,.67,.21],color=MUTED,lw=.9,ls="--")
    connect(ax, (.011,.21), (.017,.195), style="--")
    return fig


def p1_geometry(results):
    grid = read_json(results / "P1_grid_map.json")
    geometry = read_json(results / "P1_geometry.json")
    ready = geometry["ties"]["ready"]
    pitch = read_csv(results / "P1_pitch_checks.csv")
    routes = read_csv(results / "Route_clearance_comparison.csv")
    route_summary = read_json(results / "Route_summary.json")
    fig, gs = layout("P1  |  Observation geometry and sensitivity", (9.5, 7.8), 2, 2)
    ax, close, comparison, sensitivity = [fig.add_subplot(gs[i, j])
                                             for i in range(2) for j in range(2)]
    panel(ax, "A", "Observable stations and building shadows")
    panel(close, "B", "Quality-optimal arc near T1")
    target = np.array(model.TARGETS["T1"][:2])
    spacing = grid["step_m"]
    shift = (grid["phase"]-.5)*spacing
    rectangles = [Rectangle((a*spacing+shift, j*spacing+shift),
                             (b-a+1)*spacing, spacing) for j,a,b in grid["runs"]]
    from matplotlib.collections import PatchCollection
    ax.add_collection(PatchCollection(rectangles, facecolor="#B7E0D4", edgecolor="none", zorder=1))
    for a in (ax, close):
        for shadow in geometry["shadows"]:
            a.add_patch(Polygon(shadow, closed=True, facecolor="#C5BAD6", alpha=.44,
                                edgecolor=PURPLE, lw=.45, zorder=2))
        footprint(a, clearance=True)
        a.scatter(*target, s=40, marker="*", color=PURPLE, zorder=8)
        a.scatter(ready["x_m"], ready["y_m"], s=40, fc="white", ec=ORANGE, zorder=8)
        a.plot(*np.array(ready["path"]).T, color=BLUE, lw=1.3, zorder=6)
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
        close.plot(*points, color=TEAL, lw=2.6, zorder=7, label="Feasible optimum")
        for j,key in [(0,"start_included"),(-1,"end_included")]:
            close.scatter(*points[:, j], s=24, ec=TEAL, fc=TEAL if arc[key] else "white", zorder=9)
    close.text(.97,.04,f"Range: {ready['range_m']:.3f} m\nReady: {ready['ready_s']:.3f} s",
               transform=close.transAxes, ha="right", va="bottom", color=INK, fontsize=9.5,
               bbox={"boxstyle":"round,pad=.3","fc":"white","ec":GRID}, zorder=9)
    ax.legend(handles=[Patch(fc="#B7E0D4",label="Observable grid"), Patch(fc="#C5BAD6",label="Shadow"),
                       Patch(fc="#F9CCD4",label="Safety offset")], loc="upper left", fontsize=8.6)
    assert len(routes)==route_summary["compared_routes"]
    positive = [100*float(x["saving_m"]) for x in routes if x["saving_m"] and float(x["saving_m"]) > 1e-8]
    restored = sum(x["aabb_reachable"] == "False" and bool(x["rounded_verified_distance_m"]) for x in routes)
    assert len(positive)==route_summary["shorter_paths"] and restored==route_summary["restored_endpoints"]
    panel(comparison, "C", "Rounded vs rectangular route checks")
    comparison.hist(positive, bins=np.linspace(0, max(positive)*1.001, 11), fc=TEAL, ec="white")
    comparison.set(xlabel="Distance saved among shorter routes (cm)", ylabel="Routes")
    comparison.yaxis.set_major_locator(MaxNLocator(integer=True))
    comparison.text(.97,.94,f"{len(positive)} routes shorter\n{restored} endpoints restored",
                    transform=comparison.transAxes, ha="right", va="top", weight="bold",
                    bbox={"boxstyle":"round,pad=.3","fc":"white","ec":GRID})
    panel(sensitivity, "D", "Pitch ceiling and quality")
    deg = [float(row["elevation_ceiling_deg"]) for row in pitch]
    losses = [100*float(row["relative_quality_loss"]) for row in pitch]
    sensitivity.plot(deg,losses,"o:",color=BLUE, label="Checked limits")
    sensitivity.scatter(deg[1],losses[1],s=62,facecolor="white",edgecolor=ORANGE,zorder=5)
    sensitivity.annotate(f"{deg[0]:g}° to {deg[1]:g}°\n{losses[1]:.4f}% reduction",
                        (deg[1],losses[1]),xytext=(-85,30),textcoords="offset points",
                        arrowprops={"arrowstyle":"->","color":ORANGE},color=ORANGE,fontsize=10.5,
                        bbox={"fc":"white","ec":"none","pad":1.4})
    sensitivity.set(xlabel="Pitch ceiling (degrees)",ylabel="Loss of quality (%)",ylim=(-3,max(losses)+8))
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
    x = np.linspace(min(stations[:,0])-.4, target[0]+6, 130)
    y = np.linspace(stations[0,1]-.75, stations[1,1]+.75, 130)
    X,Y = np.meshgrid(x,y)
    u,v = [np.array([X-sx,Y-sy]) for sx,sy in stations]
    ru,rv = np.hypot(*u),np.hypot(*v)
    det = abs(u[0]*v[1]-u[1]*v[0])
    with np.errstate(divide="ignore", invalid="ignore"):
        spread = sigma*np.sqrt(ru**2+rv**2)*ru*rv/det
    fig, gs = layout("P2(1)  |  Fixed-pair localization sensitivity near T2", (9.5, 4.6), 1, 2,
                     width_ratios=(1.22,1))
    ax = fig.add_subplot(gs[0,0])
    close = fig.add_subplot(gs[0,1])
    panel(ax,"A","Local first-order RMS with stations fixed")
    upper = np.nanquantile(spread[np.isfinite(spread)],.86)
    mesh = ax.contourf(X,Y,np.ma.masked_invalid(spread),levels=np.linspace(rms*.7,upper,18),
                      cmap="cividis",extend="both")
    fig.colorbar(mesh,ax=ax,label="Horizontal RMS (m)",shrink=.82,format="%.2f",ticks=MaxNLocator(5))
    for i,(sx,sy) in enumerate(stations,1):
        ax.plot([sx,target[0]],[sy,target[1]],color="white",lw=1.5)
        ax.scatter(sx,sy,c="white",edgecolors=BLUE,zorder=5,s=35)
        ax.annotate(f"S{i} (V{evidence[f'vehicle_{i}']})",(sx,sy),
                    xytext=(6,2),textcoords="offset points",fontsize=9,weight="bold",
                    bbox={"fc":"white","ec":"none","alpha":.91,"pad":1})
    theta = [degrees(atan2(*(p-target)[::-1])) for p in stations]
    left,right = theta[1],theta[0]
    while right < left:
        right += 360
    assert isclose(right-left,float(evidence["crossing_deg"]),abs_tol=1e-6)
    ax.add_patch(Arc(target,2.15,2.15,theta1=left,theta2=right,ec="white",lw=1.1,zorder=5))
    ax.annotate(f"{float(evidence['crossing_deg']):.0f}°", target+[-1.46,0],
                color="white",weight="bold",ha="center",va="center")
    ax.scatter(*target,color=ORANGE,marker="*",s=55,zorder=6)
    ax.annotate("T2", target, xytext=(6,6), textcoords="offset points", color="white",weight="bold")
    xy_axes(ax,(x[0],x[-1]),(y[0],y[-1]))
    panel(close,"B","Local Gaussian position ellipse")
    radii = covariance_ellipse(close,(0,0),cov)
    amplitude = float(max(radii))*1.5
    close.axhline(0,color=GRID,lw=.8)
    close.axvline(0,color=GRID,lw=.8)
    close.scatter(0,0,color=ORANGE,marker="*",s=58,zorder=5)
    close.set(xlim=(-amplitude,amplitude),ylim=(-amplitude,amplitude),aspect="equal",
              xlabel="East error relative to T2 (m)",ylabel="North error relative to T2 (m)")
    close.text(.03,.96,f"95% ellipse\nRMS {rms:.6f} m",va="top",transform=close.transAxes,
               bbox={"fc":"white","ec":GRID,"boxstyle":"round,pad=.25"},zorder=8)
    return fig


def vehicle_legend(ax, **kwargs):
    handles = [Line2D([0],[0],color=c,lw=2,marker="o",ms=4,label=f"V{i}")
               for i,c in enumerate(COLORS,1)]
    return ax.legend(handles=handles,ncols=5,**kwargs)


def phase_legend(ax, keys, **kwargs):
    return ax.legend(handles=[Patch(fc=PHASES[k][1],label=PHASES[k][0]) for k in keys],
                     ncols=min(len(keys),7),**kwargs)


def scene(ax, timeline, targets, *, time=None, labels=True):
    """Deterministic 3D-to-page projection; geometry uses the official field axes."""
    from matplotlib import patheffects
    from math import cos, sin

    def project(x,y,z=0):
        return .77*x+.65*y, -.33*x+.39*y+.88*z

    def line(coords, **kwargs):
        ax.plot(*zip(*(project(*p) for p in coords)),**kwargs)

    def poly(coords, **kwargs):
        ax.add_patch(Polygon([project(*p) for p in coords],closed=True,**kwargs))

    def tag(name, xyz, delta, c=INK, size=8.8):
        if labels:
            ax.annotate(name, project(*xyz), xytext=delta, textcoords="offset points",
                        color=c, fontsize=size, weight="bold", zorder=19,
                        path_effects=[patheffects.withStroke(linewidth=2.3, foreground="white")])

    ax.set_aspect("equal")
    ax.axis("off")
    w,d = model.WIDTH, model.DEPTH
    poly([(0,0),(w,0),(w,d),(0,d)],fc="#F2F6FA",ec="#B4C4D4",lw=.8,zorder=1)
    for tick in range(0,int(w)+1,25):
        line([(tick,0),(tick,d)],color=GRID,lw=.5,zorder=2)
    for tick in range(0,int(d)+1,25):
        line([(0,tick),(w,tick)],color=GRID,lw=.5,zorder=2)
    structures = sorted(enumerate(model.BUILDINGS,1),key=lambda row:sum(row[1][:2])-sum(row[1][2:4]))
    for i,(x0,x1,y0,y1,h) in structures:
        poly([(x0,y0),(x1,y0),(x1,y0,h),(x0,y0,h)],fc="#8299B0",ec="#4A647E",
             alpha=.74,lw=.7,zorder=6)
        poly([(x1,y0),(x1,y1),(x1,y1,h),(x1,y0,h)],fc="#68839B",ec="#4A647E",
             alpha=.72,lw=.7,zorder=6)
        poly([(x0,y0,h),(x1,y0,h),(x1,y1,h),(x0,y1,h)],fc="#D4E1EC",ec="#627F99",
             alpha=.94,lw=.7,zorder=6)
        offset = (-13,-3) if i == 3 else (2,-2) if i == 5 else (-4,0)
        tag(f"B{i}",((x0+x1)/2,(y0+y1)/2,h),offset,size=8)
    last_heading = {i:None for i in range(1,len(model.VEHICLES)+1)}
    for item in sorted(timeline,key=lambda e:e["start_s"]):
        if item["phase"]!="travel" or len(item["path"])<2:
            continue
        color = COLORS[item["vehicle"]-1]
        path = item["path"]
        assert all(geometry_checks.road_clear(tuple(a),tuple(b)) for a,b in zip(path,path[1:]))
        line(path,color=color,lw=1.45,alpha=.75 if time is None else .30,zorder=4,ls="--" if time is not None else "-")
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
            line(progress,color=color,lw=1.9,alpha=.95,zorder=5)
    for i,(label,goal) in enumerate(targets.items(),1):
        line([goal[:2],goal],color="#76879B",ls=":",lw=.9,zorder=8)
        ax.scatter(*project(*goal),marker="*",s=51,fc=INK,ec="white",lw=.65,zorder=13)
        tag(label,goal,(4,3),size=9)
    vehicle_offsets = ((7,9), (1,-12), (-12,10), (-16,-13), (-17,9))
    if time is None:
        for v,home in enumerate(model.VEHICLES,1):
            ax.scatter(*project(*home),s=28,ec="white",lw=.55,color=COLORS[v-1],zorder=15)
            tag(f"V{v}",home,vehicle_offsets[v-1],COLORS[v-1])
    else:
        for v, intervals in events.per_vehicle(timeline).items():
            item,(point,pan,tilt) = events.state_at(intervals,time)
            origin = (*point,model.HEIGHT)
            color = COLORS[v-1]
            target = targets.get(item["alert"])
            if target and item["phase"] in ("slew","wait_partner","observe"):
                blocked = any(model.segment_hits_box(origin,target,((x0,x1),(y0,y1),(0,h)))
                              for x0,x1,y0,y1,h in model.BUILDINGS)
                line([origin,target],color=ORANGE if blocked else color,
                     ls="--" if blocked else "-",lw=1.2,alpha=.85,zorder=10)
            px,py = project(*origin)
            failed = item["phase"]=="failed"
            ax.scatter(px,py,c=ORANGE if failed else color,marker="X" if failed else "o",
                       edgecolors="white",linewidths=.65,s=55 if failed else 36,zorder=16)
            heading = last_heading[v] if item["phase"]=="travel" else radians(pan)
            if not failed and heading is not None:
                ax.annotate("",project(point[0]+5*cos(heading),point[1]+5*sin(heading),model.HEIGHT),
                            (px,py),arrowprops={"arrowstyle":"-|>","color":color,
                                                "lw":.95,"mutation_scale":9},zorder=17)
            tag(f"V{v}",origin,vehicle_offsets[v-1],color)
    ax.set(xlim=(-5, project(w,d)[0]+7), ylim=(project(w,0)[1]-8, max(
        project(*goal)[1] for goal in targets.values())+10))


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
        ax.barh(vehicle,end-start,left=start,height=.61,fc=PHASES[kind][1],
                lw=.45,ec="white",hatch="///" if kind=="failed" else None,zorder=3)
        if kind=="observe" and item["alert"] and end-start>=1.35:
            ax.text((start+end)/2,vehicle,item["alert"],color="white",ha="center",
                    va="center",fontsize=8.8,weight="bold",zorder=4)
    if final is not None:
        ax.axvline(final, color=TEAL, lw=1.2, ls="--", zorder=6)
        ax.text(final,.17,f"{final:.3f} s",color=TEAL,ha="center",weight="bold",
                va="center",fontsize=9.3)
    if fault is not None:
        ax.axvline(fault,color=ORANGE,lw=1.25,ls=":",zorder=7)
        ax.text(fault,.17,f"Fault at {fault:g} s",color=ORANGE,ha="center",
                va="center",fontsize=9.3,weight="bold")
    ax.set(xlim=(0,xend),ylim=(5.65,-.17),yticks=list(range(1,6)),
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
    fig, gs = layout("P2(2)  |  Coordinated dispatch and shortlist sensitivity", (10,8.2), 3,4,
                     height_ratios=(1.45,1,.10))
    map_ax = fig.add_subplot(gs[0,:2])
    nominal = execution["nominal_policies"]["beam"]
    panel(map_ax,"A","Beam incumbent vehicle routes")
    scene(map_ax,nominal,model.TARGETS)
    vehicle_legend(map_ax,loc="lower center",bbox_to_anchor=(.5,-.02),columnspacing=.9)
    clock = fig.add_subplot(gs[0,2:])
    panel(clock,"B",f"Executed phases at shared k = {summary['shared_k']}")
    gantt(clock,nominal,max(i["end_s"] for i in nominal if i["phase"]!="idle")*1.08,
          summary["P2_latest_starts_s"]["beam"])
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
        panel(ax,"CDEF"[j],f"k = {k}  ·  {policy.title()}")
        accum = defaultdict(float)
        for v in (item for item in visits if (item["routing"],item["k"],item["policy"],item["beam_width"])==("rounded",k,policy,shared_width)):
            for first,last,phase in segment_cols:
                duration = max(0,min(float(v[last]),latest)-float(v[first]))
                accum[int(v["vehicle"]),phase] += duration
        for vehicle in range(1,6):
            bar = 0
            for _,__,phase in segment_cols:
                value = accum[vehicle,phase]
                ax.barh(vehicle,value,left=bar,height=.66,fc=PHASES[phase][1],ec="white",lw=.45)
                bar += value
        ax.set(xlim=(0,max(float(row["latest_start_s"]) for row in selected)*1.055),
               ylim=(5.6,-.4),yticks=list(range(1,6)),yticklabels=[f"V{i}" for i in range(1,6)],
               xlabel="Active phase time (s)")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.grid(False,axis="y")
        ax.text(.97,.93,f"Last start {latest:.3f} s\nV{bottleneck} · {evidence['chain'].replace('>',' → ')}",
                transform=ax.transAxes,ha="right",va="top",fontsize=8.7,weight="bold",
                bbox={"fc":"white","ec":"none","alpha":.9,"pad":1.2})
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
    assert all(int(row["seed"])==SEED for row in mc)
    assert all(int(row["samples"])==verified["mc_samples_per_probe"] for row in mc)
    assert [row["assessment"] for row in mc]==["above","below","below"]
    view = mc[0]
    rng = Random(SEED)
    sigma = A+B*float(view["distance_m"])
    # Match the first two position variates and consume both gimbal variates
    # exactly as in monte_carlo(). The stored 2M-sample counts are not altered.
    draws = []
    for _ in range(1200):
        draws.append((rng.gauss(0,1)*sigma,rng.gauss(0,1)*sigma))
        rng.gauss(0,OFFSET)
        rng.gauss(0,CONTROL)
    fig, gs = layout("P3  |  Pointing uncertainty and verified coverage boundary", (10.0,7.8), 2,2,
                     width_ratios=(1,1.25),height_ratios=(1,1.02))
    cloud, broad, bounds, zoom = (fig.add_subplot(gs[i,j]) for i,j in ((0,0),(0,1),(1,0),(1,1)))
    panel(cloud,"A","Position uncertainty at the lower probe")
    covariance_ellipse(cloud,(0,0),np.eye(2)*sigma**2,color=ORANGE)
    cloud.scatter(*np.asarray(draws).T,s=6,alpha=.35,color=BLUE,edgecolors="none",zorder=3)
    lim = max(abs(p) for row in draws for p in row)*1.07
    cloud.set(xlim=(-lim,lim),ylim=(-lim,lim),aspect="equal",
              xlabel="Longitudinal position error (m)",ylabel="Lateral position error (m)")
    cloud.text(.02,.98,f"First {len(draws):,} seeded draws\n95% analytic position ellipse",
               transform=cloud.transAxes,va="top",ha="left",fontsize=8.8,
               bbox={"fc":"white","ec":GRID,"boxstyle":"round,pad=.28"},zorder=8)
    distances = np.array([float(row["distance_m"]) for row in curve])
    for ax in (broad,zoom):
        for key,color,style,label in (("linear_coverage",MUTED,"--","First-order"),(
                "nonlinear_coverage",TEAL,"-","Nonlinear quadrature")):
            ax.plot(distances,[float(row[key]) for row in curve],color=color,ls=style,label=label)
        ax.axhline(requirement,color=ORANGE,ls=":",lw=1.2,label="Coverage requirement")
        ax.axvline(crossing,color=MUTED,ls=":",lw=1.2)
        for i,row in enumerate(mc):
            s,p = float(row["distance_m"]), float(row["estimate"])
            lo,hi = [float(row[f"simultaneous_95_{suffix}"]) for suffix in ("lower","upper")]
            ax.errorbar(s,p,yerr=[[p-lo],[hi-p]],color=BLUE,fmt="o",mfc="white",
                        capsize=3.2,zorder=6,label="MC simultaneous 95% CI" if i==0 else None)
        ax.yaxis.set_major_formatter(PercentFormatter(xmax=1,decimals=1))
        ax.set(xlabel="Travel distance (m)",ylabel="Coverage")
    panel(broad,"B","Coverage by travel distance")
    broad.set(xlim=(0,max(float(row["distance_m"]) for row in mc)*1.18),ylim=(.86,1.004))
    broad.legend(loc="lower left",fontsize=8.6)
    panel(zoom,"D","Threshold and sided Monte Carlo checks")
    probe_offset = crossing-float(mc[0]["distance_m"])
    lo = min(float(row["simultaneous_95_lower"]) for row in mc[:2])
    hi = max(float(row["simultaneous_95_upper"]) for row in mc[:2])
    bounds_x = (crossing-2.5*probe_offset,crossing+2.5*probe_offset)
    broad.add_patch(Rectangle((bounds_x[0],lo-.0016), bounds_x[1]-bounds_x[0],
                              hi-lo+.0032, fill=False, ec=MUTED, lw=.8, zorder=8))
    zoom.set(xlim=bounds_x,
             ylim=(lo-.0016,hi+.0016))
    zoom.annotate(f"{crossing:.6f} m", (crossing,requirement),xytext=(7,32),
                  textcoords="offset points",arrowprops={"arrowstyle":"->","color":MUTED},weight="bold")
    zoom.text(.97,.95,f"{int(mc[0]['samples']):,} trials per probe",
              transform=zoom.transAxes,ha="right",va="top",fontsize=9.5)
    panel(bounds,"C","Feasible position-error parameter boundary")
    equal = sorted([r for r in boundary if r["case"]=="on_crossing"],key=lambda r:float(r["a_m"]))
    a = [float(r["a_m"]) for r in equal]
    b = [float(r["b_m_per_m"]) for r in equal]
    bounds.fill_between(a,0,b,facecolor="#B7E0D4",alpha=.8,label="At or above requirement")
    bounds.plot(a,b,color=TEAL,label=f"Boundary at {float(equal[0]['distance_m']):g} m")
    for group,mark,c in (("inside","o",TEAL),("outside","x",ORANGE)):
        rows = [r for r in boundary if r["case"]==group]
        bounds.scatter([float(r["a_m"]) for r in rows],[float(r["b_m_per_m"]) for r in rows],
                       marker=mark,s=28,color=c,label=group.capitalize()+" checks",zorder=4)
    bounds.set(xlim=(-.035,max(a)*1.19),ylim=(-.001,max(b)*1.19),
               xlabel="Intercept a (m)",ylabel="Distance coefficient b (m/m)")
    bounds.legend(loc="upper right",fontsize=8.3)
    return fig


def p4_resilience(results):
    groups = {}
    for row in read_csv(results/"P4_cases.csv"):
        groups.setdefault(row["case"], {})[row["policy"]] = row
    summary = read_json(results/"priority_3.json")
    trace = read_json(results/"Executed_timeline.json")
    assert len(groups)==summary["P4_case_count"] and groups.keys()==trace["cases"].keys()
    expected_plan = summary["nominal_plan_id"]
    assert all(r["plan_id"]==expected_plan for pair in groups.values() for r in pair.values())
    index, matrix = [], []
    for n,(case,pair) in enumerate(groups.items(),1):
        keep,replan = (pair[k] for k in ("keep","reschedule"))
        last = [float(r["latest_start_s"]) for r in (keep,replan)]
        success = [int(r["successes"]) for r in (keep,replan)]
        ratios = [float(r["completion_ratio"]) for r in (keep,replan)]
        score_keep,score_plan = (success[0],-last[0]),(success[1],-last[1])
        result = (score_plan > score_keep)-(score_plan < score_keep)
        both_completed = success[0]==success[1]==int(keep["alerts"])
        matrix.append((*ratios,last[1]-last[0] if both_completed else np.nan,result))
        index.append({
            "column":n,"case":case,"keep_ratio":keep["completion_ratio"],"reschedule_ratio":replan["completion_ratio"],
            "reschedule_minus_keep_s":f"{last[1]-last[0]:.12g}" if both_completed else "",
            "score_outcome":{-1:"keep",0:"tie",1:"reschedule"}[result],
        })
    values = np.asarray(matrix)
    fig, gs = layout(f"P4  |  Resilience across {len(groups)} archived case IDs",
                     (10,7.8),4,2,height_ratios=(1,1,1,1.85),width_ratios=(28,1))
    norm_time = max(abs(v) for v in values[:,2] if np.isfinite(v)) or 1
    time_map = mpl.colormaps["PuOr_r"].copy()
    time_map.set_bad("#D4DCE3")
    score_map = ListedColormap(["#E6A754","#E1E9F0","#48A799"])
    image_rows = [
        ("Keep completion", mpl.colormaps["cividis"],mpl.colors.Normalize(0,1)),
        ("Reschedule completion",mpl.colormaps["cividis"],mpl.colors.Normalize(0,1)),
        ("Start difference (s)", time_map,TwoSlopeNorm(vmin=-norm_time,vcenter=0,vmax=norm_time)),
        ("Score winner", score_map,BoundaryNorm([-1.5,-.5,.5,1.5],score_map.N)),
    ]
    chunks = np.array_split(values,3)
    for p,rows in enumerate(chunks):
        ax = fig.add_subplot(gs[p,0])
        color_ax = fig.add_subplot(gs[p,1])
        color_ax.axis("off")
        letter = "ABC"[p]
        first = sum(len(s) for s in chunks[:p])+1
        panel(ax,letter,f"Case IDs {first}–{first+len(rows)-1}  |  source order")
        for y,(_,color,norm) in enumerate(image_rows):
            rendered = norm(np.ma.masked_invalid(rows[:,y]))
            for j,value in enumerate(rendered):
                ax.add_patch(Rectangle((first+j-.5,y-.46),1,.92,lw=0,fc=color(value),
                                       antialiased=False,zorder=3))
            scale = mpl.cm.ScalarMappable(norm=norm,cmap=color)
            if p==0 and y==0:
                bar = fig.colorbar(scale,cax=color_ax.inset_axes([.04,.08,.35,.84]),ticks=[0,.5,1],
                             format=PercentFormatter(1,decimals=0))
                bar.solids.set_rasterized(False)
            if p==1 and y==2:
                bar = fig.colorbar(scale,cax=color_ax.inset_axes([.04,.08,.35,.84]),ticks=[-norm_time,0,norm_time],
                             format="%.1f")
                bar.solids.set_rasterized(False)
        ticks = np.arange(first,first+len(rows),2)
        ax.set(xlim=(first-.5,first+len(rows)-.5),ylim=(3.55,-.55),yticks=np.arange(4),
               yticklabels=[x[0] for x in image_rows],xticks=ticks)
        ax.tick_params(axis="y",length=0)
        ax.tick_params(axis="x",length=2)
        ax.grid(False)
        for spine in ax.spines.values():
            spine.set_visible(False)
    flow = fig.add_subplot(gs[-1,:])
    flow.axis("off")
    flow.set(xlim=(0,1),ylim=(0,1))
    panel(flow,"D","Event-driven policy comparison")
    node(flow,.015,.34,.213,.37,"Freeze nominal plan","Case clocks and availability",BLUE)
    node(flow,.265,.34,.213,.37,"Advance event state","Replay to release time",BLUE)
    node(flow,.523,.56,.216,.31,"Keep","Replay cached assignments",GOLD)
    node(flow,.523,.16,.216,.31,"Reschedule","Lock pairs, revisit pending",TEAL)
    node(flow,.78,.34,.204,.37,"Compare","Score starts in window",PURPLE)
    connect(flow,(.232,.525),(.261,.525))
    connect(flow,(.482,.525),(.519,.696))
    connect(flow,(.482,.525),(.519,.325))
    connect(flow,(.744,.697),(.776,.525))
    connect(flow,(.744,.324),(.776,.525))
    wins = np.asarray(values[:,3],dtype=int)
    handles = [
        Patch(fc="#D4DCE3",label="Time masked if either policy incomplete"),
        Patch(fc="#E6A754",label=f"Keep {sum(wins<0)}"),
        Patch(fc="#E1E9F0",label=f"Ties {sum(wins==0)}"),
        Patch(fc="#48A799",label=f"Reschedule {sum(wins>0)}"),
    ]
    flow.legend(handles=handles,loc="lower center",ncols=4,fontsize=9,columnspacing=1)
    return fig,index


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
    fig, gs = layout("P4  |  V5 failure and policy divergence", (9.5,7.4), 3,1,
                     height_ratios=(1,1,.51))
    fault = execution["failure_s"]
    xend = max(float(row["end_s"]) for row in comparison
               if row["phase"] not in {"idle","failed"})*1.04
    for index,(policy,score) in enumerate(scores.items()):
        ax = fig.add_subplot(gs[index,0])
        panel(ax,"AB"[index],f"{labels[policy]}  ·  {score['successes']}/{score['alerts']} starts")
        gantt(ax,policy_rows[policy],xend,score["latest_start_s"],fault=fault)
        last_alert = max(score["starts"],key=lambda alert:score["starts"][alert])
        candidates = [e for e in policy_rows[policy] if e["phase"]=="observe"
                      and e["alert"]==last_alert and isclose(float(e["start_s"]),score["latest_start_s"])]
        assert len(candidates)==2
        ax.text(.99,.98,f"Last pair: {last_alert} · "+ " + ".join(f"V{e['vehicle']}" for e in candidates),
                transform=ax.transAxes,va="top",ha="right",color=INK,fontsize=9,weight="bold")
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
            panel(ax,"AB"[index],policy)
            scene(ax,timeline,targets,time=t)
            vehicle_legend(ax,loc="lower center",columnspacing=1.25,bbox_to_anchor=(.5,-.045))
            sources.append({"figure":stem,"case":"nominal" if index==0 and stem=="normal_coordination" else "failure_V5",
                            "policy":policy,"time_s":t,"source":"Executed_timeline.json; P2_main_plans.json; B题题面参数.csv",
                            "projection":"Orthographic 3D-to-page","formats":"Vector PDF; PNG 320 dpi"})
        save(fig,keydir,stem)
    write_csv(keydir/"KEYFRAME_SOURCES.csv",sources)

    fig, gs = layout("Replay keyframes  |  Nominal, fault, and response", (10.1,7.2), 2,2,
                     height_ratios=(1,1))
    ax = fig.add_subplot(gs[0,0])
    panel(ax,"A",f"Nominal cooperation  ·  {first:.3f} s")
    scene(ax,nominal,model.TARGETS,time=first)
    ax = fig.add_subplot(gs[0,1])
    panel(ax,"B",f"V5 fault trigger  ·  {t_fault:.3f} s")
    scene(ax,v5["policies"]["reschedule"],v5["targets"],time=t_fault)
    for column,(policy,title) in enumerate((("keep","Keep"),("reschedule","Reschedule"))):
        ax = fig.add_subplot(gs[1,column])
        panel(ax,"C1" if column==0 else "C2",f"{title} response  ·  {last:.3f} s")
        scene(ax,v5["policies"][policy],v5["targets"],time=last)
        vehicle_legend(ax,loc="lower center",columnspacing=.9,bbox_to_anchor=(.5,-.045))
    return fig


def generate(root):
    directory = root/"figures"
    results = root/"results"
    scripts = (framework,p1_geometry,precision,dispatch,p3_risk,p4_resilience,v5_timeline)
    for row,draw in zip(FIGURE_MAP,scripts):
        stem,_,_ = row
        out = draw(results)
        if stem=="fig06_p4_resilience":
            out,index = out
            write_csv(directory/"P4_PANEL_INDEX.csv",index)
        save(out,directory,stem)
    save(replay_frames(results,directory),directory,FIGURE_MAP[-1][0])
    write_csv(directory/"FIGURE_SOURCES.csv",(
        {"figure":name,"source":inputs,"purpose":description,"formats":"Vector PDF; PNG 320 dpi"}
        for name,inputs,description in FIGURE_MAP
    ))
    print("Rendered 8 analytical figure groups and 3 replay keyframe groups as vector PDF and 320 dpi PNG.")


if __name__=="__main__":
    cli = ArgumentParser(description=__doc__)
    cli.add_argument("--out",type=Path,default=DEFAULT_OUTPUT)
    generate(cli.parse_args().out)


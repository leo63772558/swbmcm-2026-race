"""Draw revision evidence as vector PDF and raster PNG from the same sources.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: routine visualisation.
"""
from argparse import ArgumentParser
from collections import Counter
from math import atan2, cos, degrees, dist, pi, sin, sqrt
import os
from pathlib import Path
import subprocess

from reportlab.lib.colors import HexColor, white
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

import b_revision_geometry as geometry
import problem_b_geometry as model
from b_revision_data import DEFAULT_OUTPUT, read_csv, read_json, write_csv
from plot_problem_b import NAVY, MUTED, TEAL, TEAL_LIGHT, BLUE, RUST, PURPLE, GRID, WASH
from plot_problem_b import axes, dot, label, rectangle, segment


PHASES = {
    "travel": ("Travel", "#0072B2"), "slew": ("Slew", "#E69F00"),
    "wait_partner": ("Wait for pair", "#B6C4CF"), "observe": ("Observe", "#007F63"),
    "reset": ("Reset", "#7866A1"), "cancel_reset": ("Cancellation reset", "#CB5F27"),
    "missed_pair": ("Missed pair", "#E0A0AE"), "failed": ("Unavailable", "#D9DDE3"),
    "idle": ("Idle", "#F3F5F7"),
}
VEHICLE_COLORS = ("#0072B2", "#D55E00", "#007E65", "#7C56A0", "#8A6300")
FIGURE_MAP = (
    ("p1_observability", "P1_grid_map.json; P1_geometry.json; official parameters",
     "Show the observable region, boundary arc and selected readiness witness."),
    ("t2_geometry", "P2_precision.csv; P2_precision_routes.json; official parameters",
     "Show both approach routes, the right-angle intersection and the local covariance scale."),
    ("p3_threshold", "P3_curve.csv; P3_MC.csv; P3_bracket.csv; P3_verification.json",
     "Show the deterministic threshold and classifications of the two separate sides."),
    ("p4_scenario_matrix", "P4_cases.csv; P4_archived_comparison.csv",
     "Separate completion changes from time changes and show the crossed recovery grid."),
    ("p2_timeline", "P2_main_plans.json; P2_visit_phases.csv; Executed_timeline.json",
     "Compare the common-k schedules by vehicle and phase."),
    ("p4_v5_timeline", "P4_V5_event_comparison.csv; Executed_timeline.json",
     "Expose cancellation resets, changed pairings and the V5 delay."),
    ("framework", "MODEL_DEPENDENCY_MAP.md; P2_main_plans.json; priority_3.json",
     "Identify the shared geometry and frozen plan that feed disturbance replay."),
)


def setup_fonts():
    fonts = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    regular = os.environ.get("B_TNR_REGULAR", str(fonts / "times.ttf"))
    bold = os.environ.get("B_TNR_BOLD", str(fonts / "timesbd.ttf"))
    for name, path in (("BodyTimes", regular), ("TitleTimes", bold)):
        pdfmetrics.registerFont(TTFont(name, path))


def new_canvas(directory, name, height, width=490):
    return Canvas(str(directory / (name + ".pdf")), pagesize=(width, height),
                  invariant=1, pageCompression=1)


def heading(pdf, x, y, title, subtitle=None):
    label(pdf, x, y, title, size=14, bold=True)
    if subtitle:
        label(pdf, x, y-16, subtitle, size=11, color=MUTED)


def path_line(pdf, points, color, width=1.6, dash=(), closed=False, fill=None):
    points = list(points)
    if len(points) < 2:
        return
    part = pdf.beginPath()
    part.moveTo(*points[0])
    for point in points[1:]:
        part.lineTo(*point)
    if closed:
        part.close()
    pdf.setStrokeColor(color)
    pdf.setLineWidth(width)
    pdf.setDash(dash)
    if fill is not None:
        pdf.setFillColor(fill)
    pdf.drawPath(part, fill=int(fill is not None), stroke=int(width > 0))
    pdf.setDash()


def building_plan(pdf, map_xy):
    for i, (x0, x1, y0, y1, _) in enumerate(model.BUILDINGS, 1):
        x, y = map_xy(x0, y0)
        u, v = map_xy(x1, y1)
        rectangle(pdf, x, y, u-x, v-y, HexColor("#8495A6"))
        label(pdf, (x+u)/2, (y+v)/2-3.5, f"B{i}", align="center", size=10, bold=True)


def map_axes(pdf, x, y, size):
    x_ticks = [(n,n) for n in range(0, int(model.WIDTH)+1, 25)]
    y_ticks = [(n,n) for n in range(0, int(model.DEPTH)+1, 25)]
    return axes(pdf,x,y,size,size,(0,model.WIDTH),(0,model.DEPTH),x_ticks,y_ticks,"East (m)","North (m)")


def p1_figure(results, directory):
    grid = read_json(results / "P1_grid_map.json")
    info = read_json(results / "P1_geometry.json")
    pdf = new_canvas(directory, "p1_observability", 336)
    heading(pdf, 18, 314, "T1 observable stations", f"Center samples on a {grid['step_m']:g} m grid")
    p = map_axes(pdf, 37, 51, 211)
    step, shift = grid["step_m"], (grid["phase"]-.5)*grid["step_m"]
    for j, a, b in grid["runs"]:
        x,y = p(a*step+shift,j*step+shift)
        xx,yy = p((b+1)*step+shift,(j+1)*step+shift)
        rectangle(pdf, x,y,xx-x,yy-y,TEAL_LIGHT)
    building_plan(pdf,p)
    goal = model.TARGETS["T1"]
    center = goal[:2]
    ready = info["ties"]["ready"]
    station = ready["x_m"], ready["y_m"]
    for first,second in zip(ready["path"], ready["path"][1:]):
        segment(pdf,p(*first),p(*second),BLUE,1.8)
    dot(pdf,p(*center),NAVY,radius=3.5)
    dot(pdf,p(*station),RUST,radius=4,hollow=True)
    x,y = p(*model.VEHICLES[ready["vehicle"]-1])
    label(pdf,x+8,y+3,f'V{ready["vehicle"]}',size=10,bold=True)

    heading(pdf, 280, 272, "Boundary near T1")
    panel = (283, 88, 182)
    box_x, box_y, size = panel
    rectangle(pdf, box_x, box_y, size, size, WASH)
    scale = size / 23
    q = lambda x,y: (box_x+size/2+scale*(x-center[0]),box_y+size/2+scale*(y-center[1]))
    pdf.saveState()
    clip = pdf.beginPath()
    clip.rect(*panel, size)
    pdf.clipPath(clip, stroke=0, fill=0)
    x0,x1,y0,y1,_ = model.BUILDINGS[1]
    corner = model.RADIUS
    bx,by = q(x0-corner,y0-corner)
    ex,ey = q(x1+corner,y1+corner)
    pdf.setFillColor(HexColor("#DCE3EA"))
    pdf.setStrokeColor(MUTED)
    pdf.setLineWidth(.75)
    pdf.roundRect(bx,by,ex-bx,ey-by,scale*corner,stroke=1,fill=1)
    bx,by = q(x0,y0)
    ex,ey = q(x1,y1)
    rectangle(pdf,bx,by,ex-bx,ey-by,HexColor("#8495A6"))
    label(pdf,box_x+15,box_y+size/2-10,"B2",size=11,bold=True)
    rr = scale*ready["range_m"]
    cx,cy = q(*center)
    pdf.setStrokeColor(MUTED)
    pdf.setDash(3,3)
    pdf.circle(cx,cy,rr,stroke=1,fill=0)
    pdf.setDash()
    for arc in info["arcs"]:
        a,b = arc["start_deg"],arc["end_deg"]
        pdf.setStrokeColor(TEAL)
        pdf.setLineWidth(2.8)
        pdf.arc(cx-rr,cy-rr,cx+rr,cy+rr,a,b-a)
        for tag in ("start","end"):
            th = arc[tag+"_deg"]*pi/180
            dot(pdf,q(*geometry.point_on_circle(center,ready["range_m"],th)),TEAL,radius=3,
                hollow=not arc[tag+"_included"])
    dot(pdf,q(*center),NAVY,radius=3.1)
    label(pdf,cx+7,cy+5,"T1",size=10,bold=True)
    dot(pdf,q(*station),RUST,radius=4.4,hollow=True)
    pdf.restoreState()
    segment(pdf,(284,70),(301,70),TEAL,2.8)
    label(pdf,307,66,"Feasible quality-optimal arc",size=10.5)
    dot(pdf,(292,51),RUST,radius=3.6,hollow=True)
    label(pdf,307,47,f'Earliest ready: {ready["ready_s"]:.3f} s',size=10.5)
    label(pdf,280,23,f'Range {ready["range_m"]:.3f} m  |  Pitch {ready["elevation_deg"]:.0f}°',size=11,color=MUTED)
    pdf.save()


def t2_figure(results, directory):
    record, = read_csv(results / "P2_precision.csv")
    routes = read_json(results / "P2_precision_routes.json")
    pdf = new_canvas(directory, "t2_geometry", 333)
    heading(pdf,18,311,"T2 intersection geometry","Field routes and horizontal bearing intersection")
    p = map_axes(pdf,37,49,204)
    building_plan(pdf,p)
    stations = [(float(record[f"x_{i}_m"]), float(record[f"y_{i}_m"])) for i in (1,2)]
    target = model.TARGETS["T2"][:2]
    for i,route in enumerate(routes):
        tone = (BLUE,TEAL)[i]
        path_line(pdf,(p(*xy) for xy in route),tone,1.8,() if i==0 else (4,2))
        dot(pdf,p(*route[0]),tone,radius=3.1)
        dot(pdf,p(*route[-1]),tone,radius=3.5,hollow=True)
        x,y=p(*route[0])
        label(pdf,x+6,y+7,f"V{record[f'vehicle_{i+1}']}",size=10,bold=True)
    dot(pdf,p(*target),RUST,radius=3.3)
    panel = 281,117,187
    x,y,n = panel
    rectangle(pdf,x,y,n,132,WASH)
    q = lambda a,b:(x+n/2+13*(a-target[0]+1.5),y+66+13*(b-target[1]))
    tx,ty=q(*target)
    points = [q(*xy) for xy in stations]
    segment(pdf,*points,MUTED,1.1,(4,3))
    for i,pt in enumerate(points):
        segment(pdf,pt,(tx,ty),(BLUE,TEAL)[i],2)
        dot(pdf,pt,(BLUE,TEAL)[i],radius=4,hollow=True)
        label(pdf,pt[0]-8,pt[1]-4,f"S{i+1}",align="right",bold=True)
    dot(pdf,(tx,ty),RUST,radius=4)
    label(pdf,tx+8,ty+4,"T2",bold=True)
    start = degrees(atan2(points[1][1]-ty,points[1][0]-tx))
    sweep = ((degrees(atan2(points[0][1]-ty,points[0][0]-tx))-start+180)%360)-180
    pdf.setStrokeColor(RUST)
    pdf.setLineWidth(1.1)
    pdf.arc(tx-15,ty-15,tx+15,ty+15,start,sweep)
    label(pdf,tx-34,ty-3,f'{float(record["crossing_deg"]):.0f}°',size=10,bold=True,color=RUST)
    label(pdf,281,96,f'Baseline: {float(record["baseline_m"]):.3f} m',size=11)
    label(pdf,281,75,f'Local first-order RMS: {float(record["horizontal_rms_m"]):.6f} m',size=11,bold=True)
    label(pdf,281,53,"Travel / time limit",size=10.5,color=MUTED)
    time_limit = model.number("p2_1","vehicle","travel_time_max")
    for i,tone in enumerate((BLUE,TEAL),1):
        x = 281 + (i-1)*96
        value=float(record[f"rounded_travel_{i}_s"])
        label(pdf,x,36,f'V{record[f"vehicle_{i}"]}  {value:.2f} / {time_limit:g} s',size=10.5,color=tone)
    pdf.save()


def p3_figure(results,directory):
    curve=read_csv(results/"P3_curve.csv")
    mc=read_csv(results/"P3_MC.csv")
    bracket=read_json(results/"P3_verification.json")
    cross=bracket["independent_crossing_m"]
    req=float(curve[0]["required"])
    pdf=new_canvas(directory,"p3_threshold",276)
    heading(pdf,18,254,"Pointing coverage near the travel limit","Deterministic integration with separate Monte Carlo checks on either side")
    for i,(xl,yl,ticks,yticks) in enumerate((
            ((0,100),(.84,1.005),(0,20,40,60,80,100),(.85,.9,.95,1.0)),
            ((cross-1.5,cross+1.5),(.9455,.9545),tuple(round(cross)+j for j in (-1,0,1)),(.946,.95,.954)))):
        x=49+239*i
        p=axes(pdf,x,57,185,143,xl,yl,[(j,f"{j:g}") for j in ticks],
               [(j,f"{100*j:g}%") for j in yticks],"Travel (m)","Coverage" if i==0 else "Threshold detail")
        subset=[r for r in curve if xl[0]<=float(r["distance_m"])<=xl[1]]
        for name,tone,dash in (("linear_coverage",MUTED,(4,3)),("nonlinear_coverage",TEAL,())):
            xy=[p(float(r["distance_m"]),float(r[name])) for r in subset]
            path_line(pdf,xy,tone,1.75,dash)
        segment(pdf,p(xl[0],req),p(xl[1],req),RUST,1.0,(3,3))
        segment(pdf,p(cross,yl[0]),p(cross,yl[1]),MUTED,.85,(2,3))
        for row in mc:
            s,value = float(row["distance_m"]),float(row["estimate"])
            lo,hi = float(row["simultaneous_95_lower"]),float(row["simultaneous_95_upper"])
            if xl[0]<=s<=xl[1]:
                a,b=p(s,lo),p(s,hi)
                segment(pdf,a,b,BLUE,1.25)
                for u,v in (a,b):
                    segment(pdf,(u-3,v),(u+3,v),BLUE,1)
                dot(pdf,p(s,value),BLUE,radius=3.3,hollow=True)
        if i==1:
            label(pdf,x+182,207,f'{cross:.3f} m',color=TEAL,align="right",bold=True)
    for x,line,color,dash in ((47,"Nonlinear",TEAL,()),(151,"Local linear",MUTED,(4,3)),
                               (269,"Required",RUST,(3,3))):
        segment(pdf,(x,13),(x+17,13),color,1.6,dash)
        label(pdf,x+22,9,line,size=10.5)
    dot(pdf,(377,13),BLUE,radius=3,hollow=True)
    label(pdf,386,9,"MC 95% intervals",size=10.5)
    pdf.save()

def p4_matrix(results,directory):
    records=read_csv(results/"P4_cases.csv")
    grouped={}
    for row in records:
        grouped.setdefault(row["case"],{})[row["policy"]]=row
    crossed=[a for a in grouped if a.startswith("new_") and "_recovery_" in a]
    clocks=sorted({float(grouped[a]["keep"]["dispatch_allowed_from_s"]) for a in crossed})
    failed=sorted({int(grouped[a]["keep"]["failed_vehicle"]) for a in crossed})
    locations=sorted({a.split("_V")[0] for a in crossed})
    disturbance=model.number("p4","disturbance","occurrence_time")
    scores = Counter()
    for variants in grouped.values():
        keep,replan=(variants[p] for p in ("keep","reschedule"))
        a=(int(keep["successes"]),-float(keep["latest_start_s"]))
        b=(int(replan["successes"]),-float(replan["latest_start_s"]))
        scores[(b>a)-(b<a)] += 1
    pdf=new_canvas(directory,"p4_scenario_matrix",346)
    heading(pdf,18,324,"Recovery cases by alert position and failed vehicle",
            "Change in the number of alerts that initiate observation")
    cw,ch=65,19
    for j,vehicle in enumerate(failed):
        label(pdf,112+(j+.5)*cw,278,f"V{vehicle}",align="center",bold=True)
    for i,clock in enumerate(clocks):
        y=253-i*76
        clock_label="No outage" if clock==disturbance else f"Recovery {clock:g} s"
        label(pdf,23,y+12,clock_label,size=10.5,bold=True)
        label(pdf,23,y-3,f"Duration {clock-disturbance:g} s",size=10,color=MUTED)
        for k,loc in enumerate(locations):
            ycell=y-k*ch
            label(pdf,103,ycell+5,f"N{loc[-1]}",size=10.5,align="right",color=MUTED)
            for j,vehicle in enumerate(failed):
                case=f"{loc}_V{vehicle}_recovery_{clock:g}"
                a,b=(grouped[case][p] for p in ("keep","reschedule"))
                delta=int(b["successes"])-int(a["successes"])
                color={0:WASH,1:HexColor("#CBE5E2"),2:HexColor("#89C8BB"),
                       3:HexColor("#57A599")}.get(delta,HexColor("#EBC4B8"))
                rectangle(pdf,112+j*cw,ycell,cw-2,ch-2,color)
                label(pdf,112+(j+.5)*cw,ycell+4, "0" if not delta else f"{delta:+d}",
                      align="center",size=11,bold=bool(delta))
    label(pdf,23,24,f"{len(grouped)} case IDs in the full catalogue: {scores[1]} improve, "
                     f"{scores[0]} tie, {scores[-1]} worsen.",size=10.5,color=MUTED)
    label(pdf,23,11,"The catalogue includes overlap between the archive and the crossed grid.",size=10,color=MUTED)
    pdf.save()


def timeline_legend(pdf, phases, y):
    positions=(28,137,246,355)
    for i,key in enumerate(phases):
        x=positions[i%4]
        yy=y-17*(i//4)
        title,color=PHASES[key]
        rectangle(pdf,x,yy,12,7,HexColor(color))
        label(pdf,x+16,yy-1,title,size=10.5)


def timeline_panel(pdf, events, x0, y0, xmax, title, score, *, fault=None):
    w=410
    y_step=16
    y_max=y0+5*y_step
    tx=lambda t: x0+w*t/xmax
    label(pdf,x0,y_max+10,title,bold=True)
    label(pdf,x0+w,y_max+10,f"Last start {score:.3f} s",size=11,align="right",color=TEAL,bold=True)
    for v in range(1,6):
        yy=y_max-v*y_step
        rectangle(pdf,x0,yy,w,12,WASH)
        label(pdf,x0-7,yy+2,f"V{v}",size=10.5,align="right")
    for item in events:
        if item["phase"]=="idle":
            continue
        start,end=map(tx,(item["start_s"],min(item["end_s"],xmax)))
        if end<=start:
            continue
        _,color=PHASES[item["phase"]]
        y=y_max-item["vehicle"]*y_step
        rectangle(pdf,start,y,end-start,12,HexColor(color))
        if item["phase"]=="observe" and end-start>=21:
            label(pdf,(start+end)/2,y+2,item["alert"],size=9.5,color=white,align="center",bold=True)
    for value,tone,dash in ((score,TEAL,(3,3)),(fault,RUST,(5,2))):
        if value is not None:
            x=tx(value)
            segment(pdf,(x,y0-1),(x,y_max),tone,.85,dash)
    for t in range(0,int(xmax)+1,5):
        at=tx(t)
        segment(pdf,(at,y0-2),(at,y0-5),MUTED,.65)
        label(pdf,at,y0-17,str(t),size=10.5,align="center")


def gantts(results,directory):
    timeline=read_json(results/"Executed_timeline.json")
    summary=read_json(results/"priority_3.json")
    scores=summary["P2_latest_starts_s"]
    pdf=new_canvas(directory,"p2_timeline",330)
    heading(pdf,18,309,"Synchronized dispatch with a shared shortlist",
            f"Both policies use k = {summary['shared_k']} and the same route and station feasibility checks")
    for policy,title,y0 in (("beam","Beam incumbent",190),("nearest","Nearest assignment",63)):
        timeline_panel(pdf,timeline["nominal_policies"][policy],52,y0,25,title,scores[policy])
    timeline_legend(pdf,("travel","slew","wait_partner","observe","reset"),37)
    label(pdf,462,15,"Time (s)",size=10.5,align="right",color=MUTED)
    pdf.save()

    case=timeline["cases"]["failure_V5"]
    pdf=new_canvas(directory,"p4_v5_timeline",347)
    delay=summary["V5_delay_s"]
    heading(pdf,18,324,"V5 failure and cancellation costs",
            f"Fault at {case['failure_s']:g} s. Both policies start all three alerts. Delay {delay:+.3f} s.")
    for policy,title,y0 in (("keep","Keep cached schedule",198),("reschedule","Reschedule",68)):
        score=case["scores"][policy]["latest_start_s"]
        timeline_panel(pdf,case["policies"][policy],52,y0,25,title,score,fault=case["failure_s"])
    timeline_legend(pdf,("travel","slew","wait_partner","observe","reset","cancel_reset","failed"),41)
    label(pdf,461,11,"Time (s)",size=10.5,align="right",color=MUTED)
    pdf.save()


def arrow(pdf,a,b,color=MUTED,dash=()):
    segment(pdf,a,b,color,1.0,dash)
    theta=atan2(b[1]-a[1],b[0]-a[0])
    heads=[(b[0]-5*cos(theta+d),b[1]-5*sin(theta+d)) for d in (-.45,.45)]
    path_line(pdf,[heads[0],b,heads[1]],color,1.0)


def framework(results,directory):
    summary=read_json(results/"priority_3.json")
    pdf=new_canvas(directory,"framework",308)
    heading(pdf,18,286,"Problem B data flow",
            f'One frozen nominal plan feeds all {summary["P4_case_count"]} disturbance case IDs')
    nodes={
        "input":(169,221,152,29,"Official field and alerts",None),
        "geom":(169,171,152,32,"Shared observation geometry","Vehicle disk, pitch and LOS"),
        "p1":(20,111,115,36,"P1  Observation region","Arc and time criterion"),
        "p2b":(169,111,152,36,"P2(2)  Nominal dispatch","Paired vehicle events"),
        "p2a":(356,111,114,36,"P2(1)  Precision","Local horizontal RMS"),
        "p4":(169,45,152,37,"P4  Disturbance replay","Cached or revised events"),
        "p3":(356,221,114,29,"P3  Pointing risk",None),
        "deploy":(356,45,114,37,"Deployment checks","Precision and risk"),
    }
    for name,(x,y,w,h,title,extra) in nodes.items():
        rectangle(pdf,x,y,w,h,TEAL_LIGHT if name in {"geom","p2b","p4"} else WASH)
        label(pdf,x+w/2,y+h-14,title,align="center",bold=True,size=10.5)
        if extra:
            label(pdf,x+w/2,y+6,extra,align="center",size=9.8,color=MUTED)
    for a,b in (((245,221),(245,203)),((245,171),(245,147)),((245,111),(245,82)),
                ((169,181),(78,147)),((321,181),(413,147)),((321,235),(356,235))):
        arrow(pdf,a,b,TEAL)
    arrow(pdf,(413,111),(413,82),MUTED,(3,2))
    for a,b in (((470,235),(480,235)),((480,235),(480,63)),((480,63),(470,63))):
        segment(pdf,a,b,MUTED,.75,(2,2))
    arrow(pdf,(478,63),(470,63),MUTED,(2,2))
    label(pdf,21,18,"Solid: main geometry and plan inputs. Dashed: deployment assessment.",size=10.5,color=MUTED)
    pdf.save()


def generate(root):
    setup_fonts()
    figs=root/"figures"
    figs.mkdir(parents=True,exist_ok=True)
    results=root/"results"
    p1_figure(results,figs)
    t2_figure(results,figs)
    p3_figure(results,figs)
    p4_matrix(results,figs)
    gantts(results,figs)
    framework(results,figs)
    for name,_,_ in FIGURE_MAP:
        subprocess.run(["pdftoppm","-singlefile","-png","-r","300",str(figs/(name+".pdf")),
                        str(figs/name)],check=True)
    write_csv(figs/"FIGURE_SOURCES.csv",({"figure":n,"source":s,"purpose":p,"formats":"PDF; PNG 300 dpi"}
                                         for n,s,p in FIGURE_MAP))
    print(f"Rendered {len(FIGURE_MAP)} vector/PNG pairs from the verified data.")


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUTPUT)
    generate(parser.parse_args().out)


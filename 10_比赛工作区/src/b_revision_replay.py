"""Build the offline Plotly simulator and publication-resolution event frames.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: replay and graphics.
"""
from argparse import ArgumentParser
from hashlib import sha1
import json
from pathlib import Path
import shutil
import subprocess

from reportlab.lib.colors import HexColor

import b_revision_events as events
import problem_b_geometry as model
from b_revision_data import DEFAULT_OUTPUT, digest, read_json, write_csv, write_json
from b_revision_figures import PHASES, VEHICLE_COLORS, heading, new_canvas, path_line, setup_fonts
from plot_problem_b import GRID, MUTED, NAVY, TEAL, RUST, WASH, dot, label, rectangle, segment


ASSET = "plotly-gl3d.min.js"
PLOTLY_SHA1 = "ae36dd5df5923c6ca1714ac6d4a36a7ea7fe0aad"
HERE = Path(__file__).resolve().parent


def hit_building(start, target):
    for i, (x0,x1,y0,y1,h) in enumerate(model.BUILDINGS, 1):
        if model.segment_hits_box(start,target,((x0,x1),(y0,y1),(0,h))):
            return f"B{i}"
    return None


def snapshots(case, policy, t):
    rows = []
    grouped = events.per_vehicle(case["policies"][policy])
    for v, intervals in grouped.items():
        e,(xy,pan,tilt)=events.state_at(intervals,t)
        goal=case["targets"].get(e["alert"])
        blocked=hit_building((*xy,model.HEIGHT),goal) if goal else None
        rows.append({"vehicle":v,"phase":e["phase"],"point":list(xy),"pan":pan,"tilt":tilt,
                     "alert":e["alert"],"blocked_by":blocked})
    return rows


def confirmed_payload(results):
    run = read_json(results/"Executed_timeline.json")
    plans = read_json(results/"P2_main_plans.json")
    assert digest(plans["beam"]) == run["plan_id"]
    cases = dict(run["cases"])
    nominal_scores = {}
    for p in ("beam","nearest"):
        starts = {v["alert"]: v["start"] for v in plans[p]}
        nominal_scores[p] = {"starts": starts, "successes": len(starts), "alerts": len(model.TARGETS),
                             "latest_start_s": max(starts.values())}
    cases = {"nominal":{"case":"nominal","disturbance_s":None,"failure_s":None,
                        "absolute_recovery_s":None,"outage_duration_s":0,"failed_vehicle":None,
                        "new_target":None,"targets":model.TARGETS,"scores":nominal_scores,
                        "policies":run["nominal_policies"]}, **cases}
    variant = cases["failure_V5"]
    t1 = variant["disturbance_s"]
    t2 = sum(variant["scores"][p]["latest_start_s"] for p in ("keep","reschedule"))/2
    earlier = cases["all_V2"]
    rec = earlier["absolute_recovery_s"]
    keyframes = []
    for short, key, t in (
            ("v5_fault","failure_V5",t1),
            ("v5_between","failure_V5",t2),
            ("combined_recovery","all_V2",rec)):
        case=cases[key]
        keyframes.append({"label":short,"case":key,"time_s":t,
                          "snapshots":{p:snapshots(case,p,t) for p in case["policies"]}})
    assert all(x["phase"]=="failed" for x in keyframes[0]["snapshots"]["keep"] if x["vehicle"]==5)
    return {"plan_id":run["plan_id"],"input_sha256":run["input_sha256"],"cases":cases,
            "keyframes":keyframes,"phases":PHASES,"vehicle_colors":VEHICLE_COLORS,
            "policy_labels":{"keep":"Keep schedule","reschedule":"Reschedule",
                             "beam":"Beam incumbent","nearest":"Nearest assignment"},
            "field":{"width":model.WIDTH,"depth":model.DEPTH,"height":max(
                    goal[2] for c in cases.values() for goal in c["targets"].values()) + 7,
                    "camera_m":model.HEIGHT,"speed":model.SPEED,"pan_speed":model.PAN_SPEED,
                    "tilt_speed":model.PITCH_SPEED,"horizon":events.HORIZON,
                    "buildings":model.BUILDINGS,"vehicles":model.VEHICLES}}


def travelled(interval, time):
    path=interval["path"]
    length=model.SPEED*(min(time,interval["end_s"])-interval["start_s"])
    pts=[path[0]]
    for a,b in zip(path,path[1:]):
        from math import dist
        leg=dist(a,b)
        if leg>length:
            pts.append(model.route_position((a,b),length))
            break
        pts.append(b)
        length-=leg
    return pts


def scene(pdf, x, y, case, policy, t, states):
    scale=1.48
    p=lambda xw,yw,z:(x+scale*(.73*xw+.68*yw),y+scale*(-.29*xw+.31*yw+.86*z+29))
    rectangle(pdf,x-8,y-11,232,185,WASH)
    for tick in range(0,int(model.WIDTH)+1,25):
        segment(pdf,p(tick,0,0),p(tick,model.DEPTH,0),GRID,.55)
    for tick in range(0,int(model.DEPTH)+1,25):
        segment(pdf,p(0,tick,0),p(model.WIDTH,tick,0),GRID,.55)
    path_line(pdf,[p(0,0,0),p(model.WIDTH,0,0),p(model.WIDTH,model.DEPTH,0),
                   p(0,model.DEPTH,0)],MUTED,.85,closed=True)
    for e in case["policies"][policy]:
        if e["phase"]=="travel" and t>=e["start_s"]:
            path_line(pdf,(p(*q,.02) for q in travelled(e,t)),HexColor(VEHICLE_COLORS[e["vehicle"]-1]),1.3)
    scene_buildings=sorted(enumerate(model.BUILDINGS,1),key=lambda a:-sum(a[1][2:4])+sum(a[1][:2]))
    for i,(x0,x1,y0,y1,h) in scene_buildings:
        path_line(pdf,[p(x0,y0,0),p(x1,y0,0),p(x1,y0,h),p(x0,y0,h)],MUTED,.4,
                  closed=True,fill=HexColor("#BBC9D4"))
        path_line(pdf,[p(x1,y0,0),p(x1,y1,0),p(x1,y1,h),p(x1,y0,h)],MUTED,.4,
                  closed=True,fill=HexColor("#8DA3B4"))
        path_line(pdf,[p(x0,y0,h),p(x1,y0,h),p(x1,y1,h),p(x0,y1,h)],MUTED,.4,
                  closed=True,fill=HexColor("#E1E8EE"))
        xx,yy=p((x0+x1)/2,(y0+y1)/2,h)
        label(pdf,xx,yy-2,f"B{i}",size=8.9,align="center")
    for target,goal in case["targets"].items():
        if target=="T4" and t<case["disturbance_s"]:
            continue
        xx,yy=p(*goal)
        segment(pdf,p(*goal[:2],0),(xx,yy),HexColor("#A4A5B6"),.6,(2,2))
        dot(pdf,(xx,yy),HexColor("#715383"),radius=3)
        label(pdf,xx+5,yy+3,target,size=9,bold=True)
    for v in states:
        name=f"V{v['vehicle']}"
        camera=(*v["point"],model.HEIGHT)
        xx,yy=p(*camera)
        color=RUST if v["phase"]=="failed" else HexColor(VEHICLE_COLORS[v["vehicle"]-1])
        if v["alert"]:
            goal=case["targets"][v["alert"]]
            segment(pdf,p(*camera),p(*goal),RUST if v["blocked_by"] else TEAL,.75,(3,2))
        if v["phase"]=="failed":
            segment(pdf,(xx-3,yy-3),(xx+3,yy+3),RUST,1.7)
            segment(pdf,(xx-3,yy+3),(xx+3,yy-3),RUST,1.7)
        else:
            dot(pdf,(xx,yy),color,radius=3,hollow=True)
        label(pdf,xx+4,yy-8,name,size=8.5,bold=True,color=color)


def keyframe_figures(root,payload):
    directory=root/"figures"/"keyframes"
    directory.mkdir(parents=True,exist_ok=True)
    setup_fonts()
    sources=[]
    for k in payload["keyframes"]:
        label_text,id,t=k["label"],k["case"],k["time_s"]
        case=payload["cases"][id]
        pdf=new_canvas(directory,label_text,252,width=506)
        heading(pdf,17,230,("V5 disturbance replay" if id=="failure_V5" else "Combined disturbance"),
                f"Simulation time {t:.3f} s. Field scale and phase state from the event log.")
        for index,(policy,states) in enumerate(k["snapshots"].items()):
            x=18+index*248
            s=case["scores"][policy]
            n=sum(start<=t for start in s["starts"].values())
            scene(pdf,x,24,case,policy,t,states)
            label(pdf,x,190,f'{payload["policy_labels"][policy]}   {n}/{s["alerts"]} started',size=11,bold=True)
        label(pdf,17,8,"Dashed green: clear LOS probe. Dashed red: building contact. Cross: failure.",
              size=10.5,color=MUTED)
        pdf.save()
        subprocess.run(["pdftoppm","-singlefile","-png","-r","300",str(directory/(label_text+".pdf")),
                        str(directory/label_text)],check=True)
        sources.append({"file":label_text,"case":id,"simulation_time_s":t,
                        "data":"Executed_timeline.json","render":"Python 3D projection, PDF and PNG at 300 dpi"})
    write_csv(directory/"KEYFRAME_SOURCES.csv",sources)


def generate(out,plotly_path,license_path):
    browser=out/"simulator"
    assets=browser/"assets"
    assets.mkdir(parents=True,exist_ok=True)
    source=plotly_path.read_bytes().rstrip(b"\r\n")
    assert sha1(f"blob {len(source)}\0".encode()+source).hexdigest()==PLOTLY_SHA1
    (assets/ASSET).write_bytes(source)
    if license_path.resolve() != (assets/"PLOTLY_LICENSE.txt").resolve():
        shutil.copyfile(license_path,assets/"PLOTLY_LICENSE.txt")
    (assets/"PLOTLY_SOURCE.txt").write_text(
        "Plotly.js v2.35.2 gl3d distribution; upstream MIT license.\n"
        "https://github.com/plotly/plotly.js/blob/v2.35.2/dist/plotly-gl3d.min.js\n"
        f"Git blob SHA-1: {PLOTLY_SHA1}\n",encoding="utf-8")
    payload=confirmed_payload(out/"results")
    write_json(browser/"KEYFRAME_STATES.json",payload["keyframes"])
    template=(HERE/"b_replay_template.html").read_text(encoding="utf-8")
    logic=(HERE/"b_replay.js").read_text(encoding="utf-8")
    assert "</script" not in logic.lower()
    compact=json.dumps(payload,ensure_ascii=True,separators=(",",":"),allow_nan=False).replace("<","\\u003c")
    html=template.replace("__DATA__",compact).replace("__LOGIC__",logic)
    (browser/"B_Simulator.html").write_text(html,encoding="utf-8")
    keyframe_figures(out,payload)
    write_json(out/"results"/"priority_4.json",{"interactive_cases":len(payload["cases"]),
                 "keyframes":len(payload["keyframes"]),"plan_id":payload["plan_id"],
                 "pinned_plotly_git_blob":PLOTLY_SHA1})
    print(f"Offline Plotly replay: {len(payload['cases'])} cases, {len(payload['keyframes'])} keyframes")


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument("--plotly",type=Path,required=True)
    parser.add_argument("--plotly-license",type=Path,required=True)
    opts=parser.parse_args()
    generate(opts.out,opts.plotly,opts.plotly_license)

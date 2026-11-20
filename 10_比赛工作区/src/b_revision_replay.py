"""Build self-contained offline WebGL/Canvas replay from the verified intervals.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: replay and graphics.
"""
from argparse import ArgumentParser
from hashlib import sha1
import json
from pathlib import Path
import shutil

import b_revision_events as events
import problem_b_geometry as model
from b_revision_data import DEFAULT_OUTPUT, digest, read_json, write_json


ASSET = "plotly-gl3d.min.js"
PLOTLY_SHA1 = "ae36dd5df5923c6ca1714ac6d4a36a7ea7fe0aad"
HERE = Path(__file__).resolve().parent


PHASES = {
    "travel": ("Travel", "#0072B2"), "slew": ("Slew", "#E69F00"),
    "wait_partner": ("Wait for pair", "#B6C4CF"), "observe": ("Observe", "#007F63"),
    "reset": ("Reset", "#7866A1"), "cancel_reset": ("Cancellation reset", "#CB5F27"),
    "missed_pair": ("Missed pair", "#E0A0AE"), "failed": ("Unavailable", "#D9DDE3"),
    "idle": ("Idle", "#F3F5F7"),
}
VEHICLE_COLORS = ("#0072B2", "#D55E00", "#007E65", "#7C56A0", "#8A6300")


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
    logic="\n".join((HERE/name).read_text(encoding="utf-8") for name in
                    ("b_replay_render.js","b_replay.js"))
    runtime=source.decode("utf-8")
    assert "</script" not in logic.lower() and "</script" not in runtime.lower()
    compact=json.dumps(payload,ensure_ascii=True,separators=(",",":"),allow_nan=False).replace("<","\\u003c")
    html=template.replace("__DATA__",compact).replace("__LOGIC__",logic).replace("__PLOTLY__",runtime)
    (browser/"B_Simulator.html").write_text(html,encoding="utf-8",newline="\n")
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

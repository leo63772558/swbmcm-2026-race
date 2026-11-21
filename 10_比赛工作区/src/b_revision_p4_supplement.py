"""Supplemental P4 replay experiments. AI-assisted audit, OpenAI Codex, 2026-11-21."""
from collections import Counter
from dataclasses import replace
from math import dist
from random import Random
from statistics import mean, median, quantiles

from b_revision_data import read_json, write_csv, write_json
from b_revision_p4_extended import (
    HYSTERESIS_THRESHOLDS_S, _compare_score, _evaluate_cases, _load_nominal_visits,
    _select_score,
)
from b_revision_probability import wilson
import problem_b_geometry as model
import solve_problem_b as solver


SEED = 20261121
SIZE = 200
POLICIES = ("keep", "replan", "selector")


def summarize(rows):
    table = []
    for policy in POLICIES:
        samples = [row for row in rows if row["policy"] == policy]
        counts = Counter(row["outcome"] for row in samples)
        for metric in ("eta", "latest_s"):
            values = [row[metric] for row in samples]
            cuts = quantiles(values, n=100, method="inclusive")
            table.append({"policy": policy, "metric": metric, "mean": mean(values),
                          "median": median(values), "iqr": cuts[74]-cuts[24], "p95": cuts[94]})
        for outcome in ("win", "tie", "loss"):
            lo, hi = wilson(counts[outcome], len(samples), 1.959963984540054)
            table.append({"policy": policy, "metric": outcome, "rate": counts[outcome]/len(samples),
                          "wilson95": [lo, hi]})
    return table


def _archived_scenario_state(plan, t, failed, disturbance):
    """Restore the 643c22a resource clocks for its frozen Monte Carlo benchmark."""
    states = list(solver.INITIAL)
    for vehicle in range(len(solver.VEHICLES)):
        if vehicle == failed:
            states[vehicle] = None
            continue
        active = sorted((v for v in plan if v.vehicle == vehicle), key=lambda v: v.depart)
        for visit in active:
            if t < visit.depart:
                states[vehicle] = (states[vehicle][0], t)
                break
            if t < visit.arrival:
                states[vehicle] = (solver.route_position(visit.path, (t - visit.depart) * solver.SPEED), t)
                break
            if t >= visit.reset:
                states[vehicle] = (visit.station, t)
                continue
            partner_failed = any(v.alert == visit.alert and v.vehicle == failed for v in plan)
            valid_start = not partner_failed or visit.start < disturbance
            if visit.start < t and valid_start:
                release = visit.reset
            else:
                # Cancel a not-yet-started observation, returning the head to park.
                release = t + min(max(0.0, t - visit.arrival), visit.ready - visit.arrival)
            states[vehicle] = (visit.station, release)
            break
        else:
            states[vehicle] = (states[vehicle][0], t)
    return tuple(states)


def stress_cases(out, nominal):
    rng = Random(SEED)
    rows = []
    for i in range(SIZE):
        t = rng.uniform(1, 12)
        outage = rng.choice((0.0, rng.uniform(1, 25)))
        failed = rng.choice((None, *range(len(model.VEHICLES))))
        target = (model.target(rng.uniform(0,360), rng.uniform(30,50),
                               model.number("p4", "new_alert", "altitude"))
                  if rng.random() < 0.5 else None)
        _, keep, replan = _evaluate_cases(
            nominal, [("random", f"mc_{i+1:03}", target, failed, t+outage)],
            2, 3, disturbance=t, state_at_release=_archived_scenario_state,
        )[0]
        for policy, score in zip(POLICIES, (keep, replan, _select_score(keep,replan,0)), strict=True):
            verdict = _compare_score(keep, score, "win")
            rows.append({"trial": i+1, "policy": policy, "disturbance_s": t, "outage_s": outage,
                         "failed_vehicle": "" if failed is None else failed+1,
                         "target_x_m": target[0] if target else "", "target_y_m": target[1] if target else "",
                         "eta": score[1], "latest_s": score[2],
                         "outcome": "loss" if verdict == "keep" else verdict})
    write_csv(out/"P4_monte_carlo.csv", rows)
    write_json(out/"P4_monte_carlo_summary.json", {"seed": SEED, "trials": SIZE, "statistics": summarize(rows)})


def delay_study(out, nominal):
    cases = []
    for delay in HYSTERESIS_THRESHOLDS_S:
        delayed = [replace(v, **{key: getattr(v,key)+delay for key in
                    ("depart","arrival","ready","start","end","reset")}) for v in nominal]
        _, keep, replan = _evaluate_cases(delayed, [("delay","held",None,None,0.0)],
                                         8, 20, disturbance=0.0)[0]
        assert keep[1] == replan[1] == 1
        cases.append((delay,keep,replan))
    write_csv(out/"P4_equal_completion_cases.csv", [
        {"hold_s": delay, "keep_latest_s": k[2], "replan_latest_s": r[2], "gain_s": k[2]-r[2]}
        for delay,k,r in cases])
    write_csv(out/"P4_equal_completion_sweep.csv", [
        {"threshold_s": threshold, "trigger_rate": mean(_select_score(k,r,threshold) != k for _,k,r in cases),
         "mean_saving_s": mean(k[2]-_select_score(k,r,threshold)[2] for _,k,r in cases)}
        for threshold in HYSTERESIS_THRESHOLDS_S])


def motions(event):
    lo, hi = event["start_s"], event["end_s"]
    if hi <= lo:
        return
    path = event["path"]
    if event["phase"] != "travel" or len(path) < 2:
        yield lo, hi, event["position"], (0.0, 0.0)
        return
    clock = event["phase_start_s"]
    for a,b in zip(path,path[1:]):
        length = dist(a,b)
        if not length:
            continue
        end = clock + length/model.SPEED
        start = max(lo,clock)
        if start < min(hi,end):
            vel = tuple((y-x)*model.SPEED/length for x,y in zip(a,b))
            yield start, min(hi,end), tuple(x+v*(start-clock) for x,v in zip(a,vel)), vel
        clock = end


def overlap_min(a,b):
    alo,ahi,pa,va = a
    blo,bhi,pb,vb = b
    lo,hi = max(alo,blo),min(ahi,bhi)
    if hi < lo:
        return None
    offset = [x+u*(lo-alo)-y-v*(lo-blo) for x,u,y,v in zip(pa,va,pb,vb)]
    velocity = [u-v for u,v in zip(va,vb)]
    speed2 = sum(v*v for v in velocity)
    dt = min(hi-lo,max(0.0,-sum(x*v for x,v in zip(offset,velocity))/speed2)) if speed2 else 0.0
    return dist([x+dt*v for x,v in zip(offset, velocity)], (0,0)), lo+dt


def clearance(out):
    timeline = read_json(out/"Executed_timeline.json")
    scenarios = {"nominal":timeline["nominal_policies"],
                 **{key:case["policies"] for key,case in timeline["cases"].items()}}
    rows = []
    for case, policies in scenarios.items():
        for policy, events in policies.items():
            by_vehicle = {v: sorted(piece for e in events if e["vehicle"]==v for piece in motions(e))
                          for v in range(1,len(model.VEHICLES)+1)}
            hits = [(result[0],result[1],v,w)
                    for v,pieces in by_vehicle.items() for w,others in by_vehicle.items() if v<w
                    for a in pieces for b in others if (result:=overlap_min(a,b)) is not None]
            minimum,t,v,w=min(hits)
            rows.append({"case":case,"policy":policy,"distance_m":minimum,"time_s":t,
                         "vehicle_1":v,"vehicle_2":w,"margin_m":minimum-2*model.RADIUS})
    write_csv(out/"P4_vehicle_clearance.csv",rows)
    return {"checked_replays":len(rows),"minimum":min(rows,key=lambda r:r["distance_m"]),
            "replays_below_diameter":sum(r["margin_m"] < -1e-9 for r in rows),
            "method":"continuous piecewise linear relative-motion minimization"}


def main(out):
    nominal = _load_nominal_visits(out)
    delay_study(out,nominal)
    stress_cases(out,nominal)
    write_json(out/"P4_vehicle_clearance.json",clearance(out))

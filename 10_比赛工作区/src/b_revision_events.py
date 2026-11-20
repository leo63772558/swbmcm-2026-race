"""Compile executed intervals from the recorded routes and chosen event clocks.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: event data processing.
"""
from collections import defaultdict
from math import copysign, dist

import problem_b_geometry as model


TIME_TOL = 1e-8
WINDOW_START, HORIZON, INCOMPLETE = model.read_values(
    "p4", "evaluation", "window_start", "window_end", "incomplete_latest_start")


def at_rate(value, rate, duration, *, returning=False):
    magnitude = max(0, abs(value)-rate*duration) if returning else min(abs(value), rate*duration)
    return copysign(magnitude, value)


def event(vehicle, phase, start, end, position, *, alert=None, origin="cached",
          path=(), aim=(0.0, 0.0), phase_start=None):
    return {
        "vehicle": vehicle, "phase": phase, "start_s": start, "end_s": end,
        "position": position, "alert": alert, "origin": origin,
        "path": path, "aim_deg": aim, "phase_start_s": start if phase_start is None else phase_start,
    }


def state_of(interval, time):
    phase = interval["phase"]
    elapsed = min(max(time, interval["start_s"]), interval["end_s"]) - interval["phase_start_s"]
    point = interval["position"] if phase != "travel" else model.route_position(
        interval["path"], elapsed*model.SPEED)
    pan, pitch = interval["aim_deg"]
    if phase == "slew":
        pan = at_rate(pan, model.PAN_SPEED, elapsed)
        pitch = at_rate(pitch, model.PITCH_SPEED, elapsed)
    elif phase in {"reset", "cancel_reset"}:
        pan = at_rate(pan, model.PAN_SPEED, elapsed, returning=True)
        pitch = at_rate(pitch, model.PITCH_SPEED, elapsed, returning=True)
    elif phase in {"travel", "idle", "failed"}:
        pan, pitch = 0.0, 0.0
    return tuple(point), pan, pitch


def visits_to_events(visits, targets, starts, *, origin="cached", expire=None):
    events = []
    for v in visits:
        cap = min(HORIZON, expire(v)) if expire is not None else HORIZON
        aim = model.angles(v.station, targets[v.alert])
        phases = (
            ("travel", v.depart, v.arrival),
            ("slew", v.arrival, v.ready),
            ("wait_partner", v.ready, v.start),
            ("observe" if v.alert in starts else "missed_pair", v.start, v.end),
            ("reset", v.end, v.reset),
        )
        for phase, start, end in phases:
            if start < min(end, cap):
                events.append(event(v.vehicle + 1, phase, start, min(end, cap), v.station,
                                    alert=v.alert, origin=origin, path=v.path if phase == "travel" else (),
                                    aim=aim))
    return events


def per_vehicle(events):
    grouped = defaultdict(list)
    for item in events:
        grouped[item["vehicle"]].append(item)
    return {vehicle: sorted(items, key=lambda v: (v["start_s"], v["end_s"]))
            for vehicle, items in grouped.items()}


def fill_idle(events, *, failure_s=None, failed=None):
    groups = per_vehicle(events)
    timeline = []
    for v, home in enumerate(model.VEHICLES, 1):
        cursor, point = WINDOW_START, home
        for item in groups.get(v, ()):
            assert item["start_s"] >= cursor - TIME_TOL, ("overlapping phases", v, item, cursor)
            if item["start_s"] > cursor:
                timeline.append(event(v, "idle", cursor, item["start_s"], point, origin="idle"))
            next_point = state_of(item, item["start_s"])[0]
            assert dist(point, next_point) < TIME_TOL, ("position discontinuity", v, item, point)
            timeline.append(item)
            cursor, point = item["end_s"], state_of(item, item["end_s"])[0]
        if v == failed:
            assert cursor <= failure_s
            if cursor < failure_s:
                timeline.append(event(v, "idle", cursor, failure_s, point, origin="idle"))
            timeline.append(event(v, "failed", failure_s, HORIZON, point, origin="disturbance"))
        elif cursor < HORIZON:
            timeline.append(event(v, "idle", cursor, HORIZON, point, origin="idle"))
    return timeline


def state_at(items, time):
    active = next((p for p in items if p["start_s"] <= time < p["end_s"]), None)
    if active is None:
        active = items[-1]
        assert time == active["end_s"]
    return active, state_of(active, time)


def verify_observations(events, expected):
    actual = defaultdict(set)
    for item in events:
        if item["phase"] == "observe":
            actual[item["alert"], item["start_s"]].add(item["vehicle"])
    paired = {alert: t for (alert, t), cars in actual.items() if len(cars) == 2}
    expected_in_window = {name: t for name, t in expected.items() if WINDOW_START <= t < HORIZON}
    assert paired == expected_in_window, ("actual starts disagree with recorded score", paired, expected)
    return paired


def nominal_events(plan, starts):
    timeline = fill_idle(visits_to_events(plan, model.TARGETS, starts, origin="nominal"))
    verify_observations(timeline, starts)
    return timeline


def scenario_events(plan, revised, parameters, targets, locked, kept, states, updated):
    rec = parameters["dispatch_allowed_from_s"]
    fault = parameters["failure_s"]
    failed = parameters["failed_vehicle"]

    def fault_cap(v):
        return fault if v.vehicle+1 == failed else HORIZON

    def original_prefix_cap(v):
        cap = fault_cap(v)
        return cap if v.alert in locked else min(rec, cap)

    keep_history = fill_idle(visits_to_events(plan, targets, kept, expire=fault_cap),
                             failure_s=fault, failed=failed)
    prefixes = visits_to_events(plan, targets, locked, expire=original_prefix_cap)
    before = per_vehicle(prefixes)
    cancellation = []
    for v, current in enumerate(states, 1):
        if current is None:
            assert v == failed
            continue
        position, release = current
        ordered = before.get(v, ())
        active = next((e for e in ordered if e["start_s"] <= rec < e["end_s"]), None)
        if active is None and ordered and ordered[-1]["end_s"] == rec:
            active = ordered[-1]
        reached, pan, pitch = state_of(active, rec) if active else (
            state_of(ordered[-1], ordered[-1]["end_s"])[0] if ordered else model.VEHICLES[v-1], 0, 0)
        assert dist(position, reached) < TIME_TOL
        if active and active["alert"] in locked:
            continue
        reset_s = max(abs(pan)/model.PAN_SPEED, abs(pitch)/model.PITCH_SPEED)
        assert release >= rec + reset_s - TIME_TOL, ("insufficient parking time", v, release, reset_s)
        if reset_s > TIME_TOL:
            cancellation.append(event(v, "cancel_reset", rec, rec+reset_s, position,
                                      alert=active["alert"], origin="cancellation", aim=(pan, pitch)))
    replan_history = fill_idle(
        prefixes + cancellation + visits_to_events(revised, targets, updated, origin="replan"),
        failure_s=fault, failed=failed)
    verify_observations(keep_history, kept)
    verify_observations(replan_history, updated)
    return {"keep": keep_history, "reschedule": replan_history}

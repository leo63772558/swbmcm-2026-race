/* AI assistance: Antigravity (Gemini) & ChatGPT (Codex), 2026-11-21.
 * Interactive digital twin controller over verified event intervals.
 */
"use strict";

const data = JSON.parse(document.getElementById("payload").textContent);
const $ = id => document.getElementById(id);
const scenarioNames = Object.keys(data.cases);
let selected = "failure_V5";
let currentPolicy = "keep";
let time = data.cases[selected].disturbance_s;
let playing = false;
let playbackSpeed = 1.0;
let lastDraw = 0;
let drawInProgress = null;
let drawPending = false;
let autoTourActive = false;
let autoTourTimer = null;
let autoTourStage = "idle";
let tourFaultPulse = false;

function fmt(x, places = 2) { return Number(x).toFixed(places); }
function positionPath(path, length) {
  let left = length;
  let a = path[0];
  for (const b of path.slice(1)) {
    const distance = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (distance && left <= distance) {
      const f = Math.max(0, left / distance);
      return [a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])];
    }
    left -= distance;
    a = b;
  }
  return a;
}
function rate(value, speed, elapsed, returning) {
  const magnitude = returning ? Math.max(0, Math.abs(value) - speed * elapsed)
    : Math.min(Math.abs(value), speed * elapsed);
  return Math.sign(value) * magnitude;
}
function stateOf(event, at) {
  const elapsed = Math.min(event.end_s, Math.max(event.start_s, at)) - event.phase_start_s;
  const goes = event.phase === "travel";
  const point = goes ? positionPath(event.path, elapsed * data.field.speed) : event.position;
  let [pan, tilt] = event.aim_deg;
  if (event.phase === "slew" || event.phase === "reset" || event.phase === "cancel_reset") {
    const back = event.phase !== "slew";
    pan = rate(pan, data.field.pan_speed, elapsed, back);
    tilt = rate(tilt, data.field.tilt_speed, elapsed, back);
  } else if (goes || event.phase === "idle" || event.phase === "failed") {
    pan = tilt = 0;
  }
  return { vehicle: event.vehicle, phase: event.phase, point, pan, tilt, alert: event.alert };
}
function stateFor(caseId, policy, at) {
  const phases = data.cases[caseId].policies[policy];
  return data.field.vehicles.map((_, i) => {
    const records = phases.filter(e => e.vehicle === i + 1);
    const event = records.find(e => e.start_s <= at && at < e.end_s) || records.at(-1);
    return stateOf(event, at);
  });
}
function hitBuilding(a, b) {
  for (let i = 0; i < data.field.buildings.length; i++) {
    const [x0, x1, y0, y1, h] = data.field.buildings[i];
    let lo = 0, hi = 1;
    const bounds = [[x0, x1], [y0, y1], [0, h]];
    for (let k = 0; k < 3; k++) {
      const [min, max] = bounds[k];
      const step = b[k] - a[k];
      if (Math.abs(step) < 1e-12) {
        if (a[k] < min || a[k] > max) { lo = 2; break; }
      } else {
        const one = (min - a[k]) / step, two = (max - a[k]) / step;
        lo = Math.max(lo, Math.min(one, two));
        hi = Math.min(hi, Math.max(one, two));
      }
    }
    if (lo <= hi + 1e-12) return "B" + (i + 1);
  }
  return null;
}
function titleCase(s) { return s.replaceAll("_", " ").replace(/^\w/, x => x.toUpperCase()); }
function node(tag, text, className = "") {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  el.className = className;
  return el;
}

function makeScore(record) {
  const box = $("score");
  box.replaceChildren();
  for (const [p, s] of Object.entries(record.scores)) {
    const wrap = node("article", undefined, "kpi-card");
    const count = Object.values(s.starts).filter(t => t <= time && t < data.field.horizon).length;
    const pct = s.alerts ? Math.round((count / s.alerts) * 100) : 0;
    const track = node("div", undefined, "progress-track");
    const fill = node("div", undefined, "progress-fill");
    fill.style.width = pct + "%";
    track.append(fill);
    wrap.append(
      node("div", data.policy_labels[p], "metric"),
      node("strong", count + " / " + s.alerts + " started"),
      node("small", "Window " + s.successes + "/" + s.alerts + " · last " + fmt(s.latest_start_s, 3) + " s"),
      track
    );
    box.append(wrap);
  }
}

function updateEventLog(record) {
  const log = $("eventLog");
  if (!log) return;
  log.replaceChildren();
  const items = [];
  if (record.disturbance_s !== null) {
    const label = record.failed_vehicle ? "FAULT: V" + record.failed_vehicle + " offline"
      : record.new_target ? "ALERT: New target T4 spawned"
      : "COMMS: Dispatch link outage";
    items.push({ t: record.disturbance_s, text: label, fault: true });
    if (record.absolute_recovery_s !== null) {
      items.push({ t: record.absolute_recovery_s, text: "COMMS: Link restored (outage " + fmt(record.outage_duration_s, 1) + " s)", fault: false });
    }
  }
  const starts = record.scores[currentPolicy].starts;
  for (const [alertId, tStart] of Object.entries(starts)) {
    if (tStart < data.field.horizon) {
      items.push({ t: tStart, text: alertId + " dual-observation started (" + data.policy_labels[currentPolicy] + ")", fault: false });
    }
  }
  items.sort((a, b) => a.t - b.t);
  for (const item of items) {
    const li = node("li", "[" + fmt(item.t, 3) + " s] " + item.text, item.fault ? "fault" : "");
    if (item.t > time + 1e-9) li.style.opacity = "0.45";
    log.append(li);
  }
}

function makeTimelines() {
  const record = data.cases[selected], box = $("timelines");
  box.replaceChildren();
  const last = Math.max(...Object.values(record.policies).flat()
    .filter(e => !["idle", "failed"].includes(e.phase)).map(e => e.end_s), record.absolute_recovery_s || 0);
  const end = Math.min(data.field.horizon, Math.max(25, 5 * Math.ceil(last / 5)));
  $("period").textContent = "0–" + end + " s";
  for (const [policy, rows] of Object.entries(record.policies)) {
    const div = node("div", undefined, "policy");
    const header = node("h3");
    header.append(node("span", data.policy_labels[policy]),
      node("small", fmt(record.scores[policy].latest_start_s, 3) + " s", "hint"));
    const lanes = node("div", undefined, "lanes");
    for (let v = 1; v <= data.field.vehicles.length; v++) {
      const track = node("div", undefined, "track");
      for (const e of rows.filter(e => e.vehicle === v && e.phase !== "idle")) {
        const left = (e.start_s / end) * 100, width = (Math.min(e.end_s, end) / end) * 100 - left;
        if (left >= 100 || width <= 0) continue;
        const bar = node("div", undefined, "bar");
        bar.title = (e.alert || "") + " " + data.phases[e.phase][0] + " " + fmt(e.start_s) + "–" + fmt(e.end_s) + " s";
        bar.style.cssText = "left:" + left + "%;width:" + width + "%;background:" + data.phases[e.phase][1];
        track.append(bar);
      }
      if (record.disturbance_s !== null && record.disturbance_s <= end) {
        const pin = node("div", undefined, "event-pin");
        pin.style.left = (record.disturbance_s / end) * 100 + "%";
        pin.title = "Disturbance at " + fmt(record.disturbance_s, 3) + " s";
        track.append(pin);
      }
      const cursor = node("div", undefined, "pin");
      cursor.dataset.range = end;
      track.append(cursor);
      track.addEventListener("pointerdown", e => {
        stopAutoTour(true);
        const rect = track.getBoundingClientRect();
        setTime(Math.max(0, Math.min(end, ((e.clientX - rect.left) / rect.width) * end)));
      });
      lanes.append(node("span", "V" + v), track);
    }
    const ticks = node("div", undefined, "ticks");
    for (let i = 0; i <= 4; i++) ticks.append(node("span", fmt((i * end) / 4, end % 4 === 0 ? 0 : 1)));
    lanes.append(ticks);
    div.append(header, lanes);
    box.append(div);
  }
}

function updateStates(states) {
  const rows = $("states");
  rows.replaceChildren();
  for (const s of states) {
    const li = node("li");
    const badge = node("span", undefined, "veh-badge");
    const dot = node("i", undefined, "veh-dot");
    dot.style.backgroundColor = data.vehicle_colors[s.vehicle - 1];
    const pill = node("span", data.phases[s.phase][0] + (s.alert ? " · " + s.alert : ""), "phase-pill");
    pill.style.backgroundColor = data.phases[s.phase][1];
    if (["idle", "wait_partner", "reset", "failed"].includes(s.phase)) pill.style.color = "#F8FAFC";
    badge.append(dot, document.createTextNode("V" + s.vehicle), pill);
    li.append(badge, node("small", fmt(s.point[0], 1) + ", " + fmt(s.point[1], 1) + " · " +
      fmt(s.pan, 0) + "°, " + fmt(s.tilt, 0) + "°"));
    rows.append(li);
  }
  $("viewPolicy").textContent = data.policy_labels[currentPolicy];
}

async function drawOnce() {
  const record = data.cases[selected], states = stateFor(selected, currentPolicy, time);
  const frame = frameGeometry(record, states);
  $("clock").textContent = fmt(time, 3) + " s";
  $("time").value = time;
  document.querySelectorAll(".pin").forEach(p =>
    p.style.left = Math.min(100, (time * 100) / Number(p.dataset.range)) + "%");
  makeScore(record);
  updateStates(states);
  updateEventLog(record);
  const afterEvent = record.disturbance_s !== null && time >= record.disturbance_s;
  $("branch").dataset.active = String(afterEvent);
  const eventLabel = record.failed_vehicle ? "V" + record.failed_vehicle + " failure"
    : record.new_target ? "New target" : "Communication outage";
  $("branch").textContent = afterEvent ?
    eventLabel + " at " + fmt(record.disturbance_s, 3) + " s" +
      (frame.branch.length ? " · alternate policy dashed" : "") : "Nominal corridor active";
  if ($("faultBanner")) {
    $("faultBanner").dataset.active = String(afterEvent);
    $("faultBanner").dataset.pulse = String(Boolean(afterEvent && tourFaultPulse));
    $("faultBanner").textContent = afterEvent ? "ALERT · " + eventLabel + " @ t = " + fmt(record.disturbance_s, 2) + " s" : "";
  }
  if ($("hudScenario")) {
    $("hudScenario").textContent = "Scenario: " + (selected === "nominal" ? "Nominal Coordination" : selected) +
      " · " + data.policy_labels[currentPolicy] + " · t = " + fmt(time, 2) + " s";
  }
  const rendered = { time: String(time), case: selected, policy: currentPolicy, drawnCamera: cameraMode };
  try {
    await renderField(frame);
    Object.assign($("field").dataset, rendered);
    window.BReplayRendered = true;
  } catch (e) {
    playing = false;
    $("renderer").textContent = "The browser could not initialize field rendering.";
    console.error(e);
  }
}

function draw() {
  drawPending = true;
  if (!drawInProgress) {
    drawInProgress = (async () => {
      try {
        while (drawPending) { drawPending = false; await drawOnce(); }
      } finally { drawInProgress = null; }
    })();
  }
  return drawInProgress;
}

function setTime(t) {
  time = Math.max(0, Math.min(data.field.horizon, t));
  if (time === data.field.horizon) {
    playing = false;
    $("play").textContent = "Play";
  }
  return draw();
}

function setCase(id, policy, t) {
  playing = false;
  $("play").textContent = "Play";
  selected = id; $("case").value = id;
  const p = $("policy"); p.replaceChildren();
  for (const name of Object.keys(data.cases[id].policies)) {
    const opt = node("option", data.policy_labels[name]); opt.value = name; p.append(opt);
  }
  currentPolicy = policy || p.options[0].value; p.value = currentPolicy;
  makeTimelines();
  return setTime(t === undefined ? 0 : t);
}

function setCamera(mode) {
  cameraMode = mode;
  cameraRevision++;
  for (const view of ["iso", "top", "follow"]) $(view).setAttribute("aria-pressed", String(mode === view));
  $("field").dataset.camera = mode;
  return draw();
}

function playStep(frameTime) {
  if (!playing) return;
  if (!lastDraw) lastDraw = frameTime;
  if (frameTime - lastDraw >= 90) {
    setTime(time + ((frameTime - lastDraw) / 1000) * playbackSpeed);
    lastDraw = frameTime;
  }
  if (playing) requestAnimationFrame(playStep);
}

for (const id of scenarioNames) {
  const title = id === "nominal" ? "Nominal comparison" : id === "failure_V5" ? "V5 failure" : titleCase(id);
  const opt = node("option", title); opt.value = id; $("case").append(opt);
}
for (let i = 0; i < data.field.vehicles.length; i++) {
  const label = "V" + (i + 1);
  const opt = node("option", label);
  opt.value = i + 1;
  $("tracked").append(opt);
  const span = node("span"), chip = node("i");
  chip.style.backgroundColor = data.vehicle_colors[i];
  span.append(chip, document.createTextNode(label));
  $("routes").append(span);
}
const v5 = data.cases.failure_V5;
const bookmarks = [
  ["Nominal observation", "nominal", "beam", Math.min(...Object.values(data.cases.nominal.scores.beam.starts))],
  ["V5 fault", "failure_V5", "keep", v5.disturbance_s],
  ["V5 recovery", "failure_V5", "reschedule", v5.scores.reschedule.latest_start_s],
];
for (const [title, id, policy, at] of bookmarks) {
  const button = node("button", title);
  button.type = "button";
  button.title = fmt(at, 3) + " s";
  button.addEventListener("click", () => { stopAutoTour(true); setCase(id, policy, at); });
  $("bookmarks").append(button);
}
for (const [label, color] of Object.values(data.phases)) {
  if (label === "Standby") continue;
  const span = node("span");
  const chip = node("i"); chip.style.backgroundColor = color;
  span.append(chip, document.createTextNode(label)); $("phases").append(span);
}
function stopAutoTour(clearCaption = true) {
  autoTourActive = false;
  tourFaultPulse = false;
  autoTourStage = "idle";
  if (autoTourTimer !== null) { clearTimeout(autoTourTimer); autoTourTimer = null; }
  const btn = $("autoTourBtn");
  if (btn) {
    btn.dataset.active = "false";
    btn.setAttribute("aria-pressed", "false");
    btn.textContent = "▶ Auto-Tour: V5 Fault & Dual-Strategy Demo";
  }
  const cap = $("tourCaption");
  if (cap && clearCaption) { cap.dataset.active = "false"; cap.textContent = ""; }
  $("field").dataset.autotour = "idle";
  if ($("faultBanner")) $("faultBanner").dataset.pulse = "false";
}

function setTourCaption(text) {
  const cap = $("tourCaption");
  if (!cap) return;
  cap.dataset.active = "true";
  cap.textContent = text;
}

async function startAutoTour() {
  if (autoTourActive) { stopAutoTour(true); await draw(); return; }
  stopAutoTour(false);
  autoTourActive = true;
  playing = false;
  $("play").textContent = "Play";
  const btn = $("autoTourBtn");
  if (btn) {
    btn.dataset.active = "true";
    btn.setAttribute("aria-pressed", "true");
    btn.textContent = "⏹ Stop Auto-Tour";
  }
  $("field").dataset.autotour = "active";
  if ($("dualOverlay")) $("dualOverlay").checked = true;
  if ($("los")) $("los").checked = true;
  if ($("bldgTrans")) $("bldgTrans").checked = true;
  const v5Case = data.cases.failure_V5;
  const tT1 = v5Case.scores.keep.starts.T1;
  const tFault = v5Case.disturbance_s;
  const tKeep = v5Case.scores.keep.latest_start_s;
  const tReplan = v5Case.scores.reschedule.latest_start_s;
  cameraMode = "iso";
  cameraRevision++;
  for (const view of ["iso", "top", "follow"]) $(view).setAttribute("aria-pressed", String(view === "iso"));
  $("field").dataset.camera = "iso";
  await setCase("failure_V5", "reschedule", 0);
  if (!autoTourActive) return;
  autoTourStage = "approach";
  setTourCaption("Phase 1/3 · Nominal approach (45° urban view): T1 paired observation locks at " + fmt(tT1, 3) + " s.");

  const stepMs = 80;
  const simStep = 0.55;
  const advance = async () => {
    if (!autoTourActive) return;
    if (autoTourStage === "approach") {
      const nextT = Math.min(tFault, time + simStep);
      await setTime(nextT);
      if (!autoTourActive) return;
      if (nextT >= tFault - 1e-6) {
        autoTourStage = "fault_pause";
        tourFaultPulse = true;
        $("field").dataset.autotour = "fault_highlight";
        setTourCaption("Phase 2/3 · V5 FAULT @ t = " + fmt(tFault, 3) + " s! Red pulse alert & dual-policy divergence (Keep vs. Reschedule).");
        await draw();
        if (!autoTourActive) return;
        autoTourTimer = setTimeout(() => {
          if (!autoTourActive) return;
          autoTourStage = "recovery";
          $("field").dataset.autotour = "recovery";
          setTourCaption("Phase 3/3 · Dual-strategy divergence: Keep finishes T3 @ " + fmt(tKeep, 3) +
            " s vs. Reschedule T2 @ " + fmt(tReplan, 3) + " s (+" + fmt(tReplan - tKeep, 3) + " s cancel-reset penalty).");
          autoTourTimer = setTimeout(advance, stepMs);
        }, 900);
        return;
      }
      autoTourTimer = setTimeout(advance, stepMs);
    } else if (autoTourStage === "recovery") {
      const nextT = Math.min(tReplan, time + simStep);
      await setTime(nextT);
      if (!autoTourActive) return;
      if (nextT >= tReplan - 1e-6) {
        autoTourStage = "complete";
        tourFaultPulse = false;
        if ($("faultBanner")) $("faultBanner").dataset.pulse = "false";
        $("field").dataset.autotour = "complete";
        setTourCaption("Demo complete · Keep " + fmt(tKeep, 3) + " s vs. Reschedule " + fmt(tReplan, 3) +
          " s (+" + fmt(tReplan - tKeep, 3) + " s). Dashed slate connectors mark Keep baseline station offset.");
        autoTourActive = false;
        if (btn) {
          btn.dataset.active = "false";
          btn.setAttribute("aria-pressed", "false");
          btn.textContent = "▶ Auto-Tour: V5 Fault & Dual-Strategy Demo";
        }
        await draw();
        return;
      }
      autoTourTimer = setTimeout(advance, stepMs);
    }
  };
  autoTourTimer = setTimeout(advance, stepMs);
}

$("case").addEventListener("change", e => { stopAutoTour(true); setCase(e.target.value); });
for (const mode of ["iso", "top", "follow"]) $(mode).addEventListener("click", () => setCamera(mode));
$("tracked").addEventListener("change", () => setCamera("follow"));
$("policy").addEventListener("change", e => { stopAutoTour(true); currentPolicy = e.target.value; draw(); });
$("time").addEventListener("input", e => { stopAutoTour(true); setTime(Number(e.target.value)); });
$("los").addEventListener("change", draw);
if ($("p1layer")) $("p1layer").addEventListener("change", draw);
if ($("dualOverlay")) $("dualOverlay").addEventListener("change", draw);
if ($("bldgTrans")) $("bldgTrans").addEventListener("change", draw);
if ($("speed")) $("speed").addEventListener("change", e => { playbackSpeed = Number(e.target.value) || 1.0; });
if ($("autoTourBtn")) $("autoTourBtn").addEventListener("click", startAutoTour);
$("play").addEventListener("click", () => {
  stopAutoTour(true);
  if (!playing && time === data.field.horizon) time = 0;
  playing = !playing; lastDraw = 0;
  $("play").textContent = playing ? "Pause" : "Play";
  if (playing) requestAnimationFrame(playStep);
});
$("event").addEventListener("click", () => {
  stopAutoTour(true);
  const c = data.cases[selected];
  const bounds = Object.values(c.policies).flat().flatMap(e => [e.start_s, e.end_s]);
  bounds.push(c.disturbance_s, c.absolute_recovery_s);
  setTime(Math.min(...bounds.filter(x => x !== null && x > time + 1e-9), data.field.horizon));
});
$("export").addEventListener("click", () => {
  if (!window.BReplayRendered) return;
  const filename = "B_" + selected + "_" + currentPolicy + "_" + fmt(time, 3) + "s";
  if (activeRenderer === "webgl") {
    window.Plotly.downloadImage($("plot3d"), { format: "png", width: 1800, height: 1250, filename });
  } else if (activeRenderer === "canvas") {
    const canvas = node("canvas");
    drawCanvas(canvas, frameGeometry(data.cases[selected], stateFor(selected, currentPolicy, time)), 900, 625, 2);
    const link = node("a");
    link.download = filename + ".png"; link.href = canvas.toDataURL("image/png"); link.click();
  }
});
$("field").addEventListener("webglcontextlost", e => {
  e.preventDefault();
  activeRenderer = "canvas";
  draw();
}, true);
window.addEventListener("resize", () => { if (activeRenderer === "canvas") draw(); });
if ($("hudMetrics") && data.p1_overlay) {
  $("hudMetrics").textContent = "P2(1) RMS: " + fmt(data.p1_overlay.p2_rms_m, 6) + " m · Safety r = " +
    fmt(data.p1_overlay.vehicle_radius_m, 1) + " m";
}
$("provenance").textContent = "Source: verified event intervals · nominal plan " + data.plan_id.slice(0, 12) +
  " · field parameter SHA-256 " + data.input_sha256.slice(0, 12) + " · dark digital twin v2";
window.BReplay = { stateFor, setCase, setCamera, hitBuilding, startAutoTour, stopAutoTour, checkedKeyframes: data.keyframes, bookmarks };
$("field").dataset.camera = "iso";
setCase(selected, currentPolicy, time);

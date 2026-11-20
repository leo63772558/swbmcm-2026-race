/* AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
 * Public model release date not verified. Interactive rendering of recorded data. */
"use strict";

const data = JSON.parse(document.getElementById("payload").textContent);
const $ = id => document.getElementById(id);
const scenarioNames = Object.keys(data.cases);
let selected = "failure_V5";
let currentPolicy = "keep";
let time = data.cases[selected].disturbance_s;
let playing = false;
let lastDraw = 0;
let drawInProgress = null;
let drawPending = false;

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
function titleCase(s) { return s.replaceAll("_"," ").replace(/^\w/, x => x.toUpperCase()); }
function node(tag, text, className = "") {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  el.className = className;
  return el;
}
function makeScore(record) {
  const box=$("score");
  box.replaceChildren();
  for (const [p,s] of Object.entries(record.scores)) {
    const wrap=node("article");
    const count=Object.values(s.starts).filter(t => t <= time && t < data.field.horizon).length;
    wrap.append(node("div",data.policy_labels[p]+" • at replay time","metric"),
      node("strong",count+" / "+s.alerts+" started"),
      node("small","Window score "+s.successes+"/"+s.alerts+" • last "+fmt(s.latest_start_s)+" s","hint"));
    box.append(wrap);
  }
  if (record.disturbance_s !== null) {
    const wrap=node("article"), clock=record.absolute_recovery_s;
    wrap.append(node("div","Disturbance and communication","metric"),
      node("strong",record.failed_vehicle ? "V"+record.failed_vehicle+" failure" :
        record.new_target ? "New target" : "Outage"),
      node("small",clock === null ? "Event at "+fmt(record.disturbance_s)+" s • link active"
        : "Recovery "+fmt(clock)+" s • duration "+fmt(record.outage_duration_s)+" s","hint"));
    box.append(wrap);
  }
}
function makeTimelines() {
  const record=data.cases[selected], box=$("timelines");
  box.replaceChildren();
  const last=Math.max(...Object.values(record.policies).flat()
    .filter(e=>!["idle","failed"].includes(e.phase)).map(e=>e.end_s),record.absolute_recovery_s || 0);
  const end=Math.min(data.field.horizon,Math.max(25,5*Math.ceil(last/5)));
  $("period").textContent="0–"+end+" s • shared clock";
  for (const [policy,rows] of Object.entries(record.policies)) {
    const div=node("div",undefined,"policy");
    const header=node("h3");
    header.append(node("span",data.policy_labels[policy]),
      node("small",fmt(record.scores[policy].latest_start_s,3)+" s last start","hint"));
    const lanes=node("div",undefined,"lanes");
    for (let v=1;v<=data.field.vehicles.length;v++) {
      const track=node("div",undefined,"track");
      for (const e of rows.filter(e=>e.vehicle===v && e.phase!=="idle")) {
        const left=e.start_s/end*100, width=Math.min(e.end_s,end)/end*100-left;
        if (left>=100 || width<=0) continue;
        const bar=node("div",undefined,"bar");
        bar.title=(e.alert||"")+" "+data.phases[e.phase][0]+" "+fmt(e.start_s)+"–"+fmt(e.end_s)+" s";
        bar.style.cssText="left:"+left+"%;width:"+width+"%;background:"+data.phases[e.phase][1];
        track.append(bar);
      }
      if (record.disturbance_s !== null && record.disturbance_s <= end) {
        const pin=node("div",undefined,"event-pin");
        pin.style.left=record.disturbance_s/end*100+"%";
        pin.title="Disturbance at "+fmt(record.disturbance_s,3)+" s";
        track.append(pin);
      }
      const cursor=node("div",undefined,"pin");
      cursor.dataset.range=end;
      track.append(cursor);
      track.addEventListener("pointerdown", e => {
        const rect=track.getBoundingClientRect();
        setTime(Math.max(0,Math.min(end,(e.clientX-rect.left)/rect.width*end)));
      });
      lanes.append(node("span","V"+v), track);
    }
    const ticks=node("div",undefined,"ticks");
    for (let i=0;i<=4;i++) ticks.append(node("span",fmt(i*end/4, (end%4===0 ? 0 : 1))));
    lanes.append(ticks);
    div.append(header,lanes);
    box.append(div);
  }
}
function updateStates(states) {
  const rows=$("states");
  rows.replaceChildren();
  for (const s of states) {
    const e=node("li");
    const text="V"+s.vehicle+"  "+data.phases[s.phase][0]+(s.alert?" · "+s.alert:"");
    e.append(node("strong",text),node("small",fmt(s.point[0],1)+", "+fmt(s.point[1],1)+" m   /   "+
      fmt(s.pan,0)+"°, "+fmt(s.tilt,0)+"°"));
    rows.append(e);
  }
  $("viewPolicy").textContent=data.policy_labels[currentPolicy];
}
async function drawOnce() {
  const record=data.cases[selected], states=stateFor(selected,currentPolicy,time);
  const frame=frameGeometry(record,states);
  $("clock").textContent=fmt(time,3)+" s";
  $("time").value=time;
  document.querySelectorAll(".pin").forEach(p =>
    p.style.left=Math.min(100,time*100/Number(p.dataset.range))+"%");
  makeScore(record);
  updateStates(states);
  const afterEvent=record.disturbance_s !== null && time >= record.disturbance_s;
  $("branch").dataset.active=String(afterEvent);
  const eventLabel=record.failed_vehicle ? "V"+record.failed_vehicle+" failure" :
    record.new_target ? "New target" : "Communication outage";
  $("branch").textContent=afterEvent ?
    eventLabel+" at "+fmt(record.disturbance_s,3)+" s"+
      (frame.branch.length ? " · other policy paths dotted" : "") : "";
  const rendered = {time:String(time),case:selected,policy:currentPolicy,drawnCamera:cameraMode};
  try {
    await renderField(frame);
    Object.assign($("field").dataset,rendered);
    window.BReplayRendered=true;
  } catch (e) {
    playing=false;
    $("renderer").textContent="The browser could not initialize field rendering.";
    console.error(e);
  }
}
function draw() {
  drawPending=true;
  if (!drawInProgress) {
    drawInProgress=(async () => {
      try {
        while (drawPending) { drawPending=false; await drawOnce(); }
      } finally { drawInProgress=null; }
    })();
  }
  return drawInProgress;
}
function setTime(t) {
  time=Math.max(0,Math.min(data.field.horizon,t));
  if (time===data.field.horizon) {
    playing=false;
    $("play").textContent="Play";
  }
  return draw();
}
function setCase(id, policy, t) {
  playing=false;
  $("play").textContent="Play";
  selected=id; $("case").value=id;
  const p=$("policy"); p.replaceChildren();
  for (const name of Object.keys(data.cases[id].policies)) {
    const opt=node("option",data.policy_labels[name]); opt.value=name; p.append(opt);
  }
  currentPolicy=policy || p.options[0].value; p.value=currentPolicy;
  makeTimelines();
  return setTime(t===undefined ? 0 : t);
}
function setCamera(mode) {
  cameraMode=mode;
  cameraRevision++;
  for (const view of ["iso","top","follow"]) $(view).setAttribute("aria-pressed",String(mode===view));
  $("field").dataset.camera=mode;
  return draw();
}
function playStep(frameTime) {
  if (!playing) return;
  if (!lastDraw) lastDraw=frameTime;
  if (frameTime-lastDraw>=125) {
    setTime(time+(frameTime-lastDraw)/1000);
    lastDraw=frameTime;
  }
  if (playing) requestAnimationFrame(playStep);
}
for (const id of scenarioNames) {
  const title=id==="nominal"?"Nominal comparison":id==="failure_V5"?"V5 failure":titleCase(id);
  const opt=node("option",title); opt.value=id; $("case").append(opt);
}
for (let i=0;i<data.field.vehicles.length;i++) {
  const label="V"+(i+1);
  const opt=node("option",label);
  opt.value=i+1;
  $("tracked").append(opt);
  const span=node("span"), chip=node("i");
  chip.style.backgroundColor=data.vehicle_colors[i];
  span.append(chip,document.createTextNode(label));
  $("routes").append(span);
}
const v5 = data.cases.failure_V5;
const bookmarks = [
  ["Nominal observation","nominal","beam",Math.min(...Object.values(data.cases.nominal.scores.beam.starts))],
  ["V5 fault","failure_V5","keep",v5.disturbance_s],
  ["V5 recovery","failure_V5","reschedule",v5.scores.reschedule.latest_start_s]
];
for (const [title,id,policy,at] of bookmarks) {
  const button=node("button",title);
  button.type="button";
  button.title=fmt(at,3)+" s";
  button.addEventListener("click",()=>setCase(id,policy,at));
  $("bookmarks").append(button);
}
for (const [label,color] of Object.values(data.phases)) {
  if (label==="Idle") continue;
  const span=node("span");
  const chip=node("i"); chip.style.backgroundColor=color;
  span.append(chip,document.createTextNode(label)); $("phases").append(span);
}
$("case").addEventListener("change",e=>setCase(e.target.value));
for (const mode of ["iso","top","follow"]) $(mode).addEventListener("click",()=>setCamera(mode));
$("tracked").addEventListener("change",()=>setCamera("follow"));
$("policy").addEventListener("change",e=>{currentPolicy=e.target.value;draw();});
$("time").addEventListener("input",e=>setTime(Number(e.target.value)));
$("los").addEventListener("change",draw);
$("play").addEventListener("click",()=> {
  if (!playing && time===data.field.horizon) time=0;
  playing=!playing; lastDraw=0;
  $("play").textContent=playing?"Pause":"Play";
  if (playing) requestAnimationFrame(playStep);
});
$("event").addEventListener("click",()=> {
  const c=data.cases[selected];
  const bounds=Object.values(c.policies).flat().flatMap(e=>[e.start_s,e.end_s]);
  bounds.push(c.disturbance_s,c.absolute_recovery_s);
  setTime(Math.min(...bounds.filter(x=>x!==null && x>time+1e-9),data.field.horizon));
});
$("export").addEventListener("click",()=> {
  if (!window.BReplayRendered) return;
  const filename="B_"+selected+"_"+currentPolicy+"_"+fmt(time,3)+"s";
  if (activeRenderer==="webgl") {
    window.Plotly.downloadImage($("plot3d"),{format:"png",width:1800,height:1250,filename});
  } else if (activeRenderer==="canvas") {
    const canvas=node("canvas");
    drawCanvas(canvas,frameGeometry(data.cases[selected],stateFor(selected,currentPolicy,time)),900,625,2);
    const link=node("a");
    link.download=filename+".png"; link.href=canvas.toDataURL("image/png"); link.click();
  }
});
$("field").addEventListener("webglcontextlost",e=>{
  e.preventDefault();
  activeRenderer="canvas";
  draw();
},true);
window.addEventListener("resize",()=>{if (activeRenderer==="canvas") draw();});
$("provenance").textContent="Source: verified event intervals • nominal plan "+data.plan_id.slice(0,12)+
  " • field parameter SHA-256 "+data.input_sha256.slice(0,12)+" • team review edition";
window.BReplay={stateFor, setCase, setCamera, hitBuilding, checkedKeyframes:data.keyframes, bookmarks};
$("field").dataset.camera="iso";
setCase(selected,currentPolicy,time);

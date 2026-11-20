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
let drawInProgress = false;
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
function traceXY(points, opts) {
  return { type: "scatter3d", x: points.map(q => q && q[0]), y: points.map(q => q && q[1]),
    z: points.map(q => q && q[2]), showlegend: false, ...opts };
}
function cube(box, i) {
  const [x0, x1, y0, y1, h] = box;
  return { type: "mesh3d", name: "B" + (i + 1), flatshading: true,
    x: [x0,x1,x1,x0,x0,x1,x1,x0], y: [y0,y0,y1,y1,y0,y0,y1,y1], z: [0,0,0,0,h,h,h,h],
    i:[0,0,4,4,0,0,1,1,2,2,3,3], j:[1,2,5,6,1,5,2,6,3,7,0,4], k:[2,3,6,7,5,4,6,5,7,6,4,7],
    color: "#93a7b5", opacity: .92, hovertemplate: "B" + (i + 1) + " • " + h + " m<extra></extra>",
    lighting: { ambient: .74, diffuse: .8, specular: .13, roughness: .8 },
    lightposition: { x: 100, y: -50, z: 150 }, showlegend: false };
}
function traversedPoints(events, at) {
  const points = [];
  for (const event of events) {
    if (event.phase !== "travel" || at < event.start_s) continue;
    let remain = data.field.speed * (Math.min(at, event.end_s) - event.start_s);
    let a = event.path[0];
    points.push([...a,.18]);
    for (const b of event.path.slice(1)) {
      const d = Math.hypot(b[0]-a[0], b[1]-a[1]);
      if (d > remain) {
        points.push([...positionPath([a,b], remain), .18]);
        break;
      }
      points.push([...b,.18]);
      remain -= d;
      a = b;
    }
    points.push(null);
  }
  return points;
}
function buildTraces(record, states) {
  const { buildings, width, depth, camera_m } = data.field;
  const traces = buildings.map(cube);
  traces.push(traceXY([[0,0,0],[width,0,0],[width,depth,0],[0,depth,0],[0,0,0]],
    { mode:"lines", line:{ color:"#476474", width:4 }, hoverinfo:"skip" }));
  traces.push(traceXY(buildings.map(([a,b,c,d,h]) => [(a+b)/2,(c+d)/2,h+.9]),
    { mode:"text", text:buildings.map((_,i) => "B"+(i+1)), textfont:{color:"#1c3043",size:12}, hoverinfo:"skip" }));
  for (const [alert, point] of Object.entries(record.targets)) {
    if (alert === "T4" && time < record.disturbance_s) continue;
    const start = record.scores[currentPolicy].starts[alert];
    const done = start !== undefined && start <= time && start < data.field.horizon;
    traces.push(traceXY([[point[0],point[1],0],point],
      { mode:"lines", line:{ color:"#a58cae", width:1, dash:"dot" }, hoverinfo:"skip" }));
    traces.push(traceXY([point], { mode:"markers+text", text: [alert], textposition:"top center",
      textfont:{size:13,color:"#392a43"}, marker:{size:7, color:done?"#08745e":"#80618a", symbol:"diamond"},
      hovertemplate: alert+" • "+point[2]+" m<extra></extra>" }));
  }
  for (const state of states) {
    const color = data.vehicle_colors[state.vehicle-1];
    const name = "V" + state.vehicle;
    const related = record.policies[currentPolicy].filter(e => e.vehicle === state.vehicle);
    traces.push(traceXY(traversedPoints(related,time),
      { mode:"lines", line:{color,width:5}, hoverinfo:"skip" }));
    const failed = state.phase === "failed";
    traces.push(traceXY([[...state.point,.4]],
      { mode:"markers+text", text:[name], textposition:"top center", textfont:{size:13,color:"#142b3a"},
        marker:{size:6, color:failed?"#a52c40":color, symbol:failed?"x":"circle"},
        hovertemplate: name+" • "+data.phases[state.phase][0]+"<extra></extra>" }));
    if (failed || !state.alert) continue;
    const camera = [...state.point,camera_m];
    const az = state.pan * Math.PI / 180, el = state.tilt * Math.PI / 180;
    const projected = [camera[0]+5*Math.cos(el)*Math.cos(az),
      camera[1]+5*Math.cos(el)*Math.sin(az),camera[2]+5*Math.sin(el)];
    traces.push(traceXY([camera,projected],
      { mode:"lines", line:{color:"#263e53",width:4}, hoverinfo:"skip" }));
    if ($("los").checked) {
      const target = record.targets[state.alert];
      if (!target || (state.alert==="T4" && time<record.disturbance_s)) continue;
      const blocked = hitBuilding(camera,target);
      traces.push(traceXY([camera,target],{mode:"lines",
        line:{width:3, color:blocked?"#a52c40":"#086f66",dash:"dash"},name:name+" → "+state.alert,
        hovertemplate:name+" → "+state.alert+" • "+(blocked ? blocked+" contact" : "clear")+"<extra></extra>"}));
    }
  }
  return traces;
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
async function draw() {
  if (drawInProgress) {drawPending=true; return;}
  drawInProgress=true;
  const record=data.cases[selected], states=stateFor(selected,currentPolicy,time);
  $("clock").textContent=fmt(time,3)+" s";
  $("time").value=time;
  document.querySelectorAll(".pin").forEach(p =>
    p.style.left=Math.min(100,time*100/Number(p.dataset.range))+"%");
  makeScore(record);
  updateStates(states);
  try {
    await Plotly.react("scene",buildTraces(record,states),{
      showlegend:false, margin:{l:0,r:0,b:0,t:14}, paper_bgcolor:"#ffffff", uirevision:"fixed-camera",
      scene:{
        xaxis:{ title:"East (m)",range:[0,data.field.width],backgroundcolor:"#f5f8fb",showbackground:true },
        yaxis:{ title:"North (m)",range:[0,data.field.depth],backgroundcolor:"#f5f8fb",showbackground:true },
        zaxis:{ title:"Height (m)",range:[0,data.field.height],backgroundcolor:"#f5f8fb",showbackground:true },
        aspectmode:"data", camera:{eye:{x:1.48,y:-1.68,z:1.16},up:{x:0,y:0,z:1}},
      }}, {responsive:true,displaylogo:false,modeBarButtonsToRemove:["toImage"]});
    window.BReplayRendered=true;
  } catch (e) {
    playing=false;
    $("scene").replaceChildren(node("p","The 3D view requires WebGL. Timeline and vehicle states remain available.","error"));
    console.error(e);
  } finally {
    drawInProgress=false;
    if (drawPending) { drawPending=false; draw(); }
  }
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
  selected=id; $("case").value=id;
  const p=$("policy"); p.replaceChildren();
  for (const name of Object.keys(data.cases[id].policies)) {
    const opt=node("option",data.policy_labels[name]); opt.value=name; p.append(opt);
  }
  currentPolicy=policy || p.options[0].value; p.value=currentPolicy;
  makeTimelines();
  return setTime(t===undefined ? 0 : t);
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
for (const [label,color] of Object.values(data.phases)) {
  if (label==="Idle") continue;
  const span=node("span");
  const chip=node("i"); chip.style.backgroundColor=color;
  span.append(chip,document.createTextNode(label)); $("phases").append(span);
}
$("case").addEventListener("change",e=>setCase(e.target.value));
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
  if (window.BReplayRendered) Plotly.downloadImage("scene",{format:"png",width:1800,height:1250,
    filename:"B_"+selected+"_"+currentPolicy+"_"+fmt(time,3)+"s"});
});
$("provenance").textContent="Source: verified event intervals • nominal plan "+data.plan_id.slice(0,12)+
  " • field parameter SHA-256 "+data.input_sha256.slice(0,12)+" • team review edition";
window.BReplay={stateFor, setCase, hitBuilding, checkedKeyframes:data.keyframes};
setCase(selected,currentPolicy,time);

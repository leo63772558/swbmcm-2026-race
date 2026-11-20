/* Display geometry only. AI assistance: ChatGPT (Codex, GPT-6.2 Sol), 2026-11-21. */

const INK = "#243c54";
const CLEAR = "#086f66";
const BLOCKED = "#a52c40";
const BRANCH = "#57647b";
const TARGET = "#715486";
const VIEW_X = 1.26, VIEW_Y = -1.64;
const VIEW_RADIUS = Math.hypot(VIEW_X,VIEW_Y);
let cameraMode = "iso";
let cameraRevision = 0;
let activeRenderer = "";

function traveledPath(event, at) {
  const points = [event.path[0]];
  let length = (Math.min(at, event.end_s) - event.phase_start_s) * data.field.speed;
  for (const b of event.path.slice(1)) {
    const a = points.at(-1);
    const leg = Math.hypot(b[0]-a[0], b[1]-a[1]);
    if (leg > length) {
      points.push(positionPath([a,b], length));
      break;
    }
    points.push(b);
    length -= leg;
  }
  return points;
}

function headingAt(related, point) {
  const travel = related.filter(e => e.phase === "travel" && e.start_s <= time).at(-1);
  if (!travel) return null;
  const path = traveledPath(travel, time);
  const [x,y] = path.at(-1);
  const prev = path.findLast(([px,py]) => Math.hypot(x-px,y-py) > 1e-9);
  const next = travel.path.find((p,i) => i > 0 && Math.hypot(p[0]-x,p[1]-y) > 1e-9);
  // At the first instant of travel, use the first distinct waypoint.
  const dx = prev ? x-prev[0] : next ? next[0]-x : 0;
  const dy = prev ? y-prev[1] : next ? next[1]-y : 0;
  const norm = Math.hypot(dx, dy);
  if (!norm) return null;
  const [px,py] = point, u=dx/norm, v=dy/norm;
  const z=.35, tip=[px+3*u,py+3*v,z];
  return [[px+1.8*u-v,py+1.8*v+u,z],tip,[px+1.8*u+v,py+1.8*v-u,z]];
}

function frameGeometry(record, states) {
  const {buildings,width,depth,camera_m} = data.field;
  const boxes = buildings.map(([a,b,c,d,h], i) => ({
    points:[[a,c,0],[b,c,0],[b,d,0],[a,d,0],[a,c,h],[b,c,h],[b,d,h],[a,d,h]],
    label:"B"+(i+1), roof:[(a+b)/2,(c+d)/2,h], h
  }));
  const targets = Object.entries(record.targets).filter(([id]) =>
    id !== "T4" || time >= record.disturbance_s).map(([id,point]) => {
      const observed = record.scores[currentPolicy].starts[id];
      return {id,point,started:observed <= time && observed < data.field.horizon};
    });
  const rows = record.policies[currentPolicy];
  let branch = [];
  if (record.disturbance_s !== null && time >= record.disturbance_s) {
    const other = currentPolicy === "keep" ? "reschedule" : "keep";
    const signature = e => JSON.stringify([e.vehicle,e.alert,e.start_s,e.end_s,e.path]);
    const inView = new Set(rows.filter(e => e.phase === "travel").map(signature));
    branch = record.policies[other].filter(e => e.phase === "travel" &&
      e.end_s > record.disturbance_s && !inView.has(signature(e)));
  }
  const vehicles = states.map(state => {
    const related = rows.filter(e => e.vehicle === state.vehicle);
    const tracks = related.filter(e => e.phase === "travel" && time >= e.start_s)
      .map(e => traveledPath(e,time).map(q => [...q,.12]));
    const failed = state.phase === "failed";
    const target = targets.find(t => t.id === state.alert);
    const camera = [...state.point,camera_m];
    const az = state.pan * Math.PI / 180, el = state.tilt * Math.PI / 180;
    const aim = [camera[0]+5*Math.cos(el)*Math.cos(az),
      camera[1]+5*Math.cos(el)*Math.sin(az),camera[2]+5*Math.sin(el)];
    return {
      id:state.vehicle, name:"V"+state.vehicle, point:[...state.point,.4],
      color:data.vehicle_colors[state.vehicle-1], tracks, camera, aim, failed,
      heading:failed ? null : headingAt(related,state.point),
      hasAim:!failed && state.phase !== "travel" && state.alert,
      sight:!failed && target && $("los").checked ? {
        target, blocked:hitBuilding(camera,target.point)
      } : null
    };
  });
  return {boxes, targets, vehicles, width,depth, branch, alternate:branch.map(e => ({
    vehicle:e.vehicle,path:e.path.map(point => [...point,.2])
  }))};
}

function sceneRanges(frame) {
  if (cameraMode !== "follow") return [[0,frame.width],[0,frame.depth]];
  const tracked = frame.vehicles.find(v => v.id === Number($("tracked").value)) || frame.vehicles[0];
  return [frame.width,frame.depth].map((extent,i) => {
    const span = Math.min(65,extent);
    const min = Math.min(extent-span,Math.max(0,tracked.point[i]-span/2));
    return [min,min+span];
  });
}

function traceXY(points, opts) {
  return {type:"scatter3d", x:points.map(q => q?.[0] ?? null),
    y:points.map(q => q?.[1] ?? null),z:points.map(q => q?.[2] ?? null),showlegend:false,...opts};
}

function lineTrace(points, color, width, dash="solid", extra={}) {
  return traceXY(points,{mode:"lines",line:{color,width,dash},hoverinfo:"skip",...extra});
}

function buildTraces(frame) {
  const traces = [];
  for (const {points,label,h} of frame.boxes) {
    const [a,b,c,d] = points.slice(4);
    traces.push({
      ...traceXY(points,{}),type:"mesh3d",name:label,
      i:[4,4,0,0,1,1,2,2,3,3],j:[5,6,1,5,2,6,3,7,0,4],k:[6,7,5,4,6,5,7,6,4,7],
      flatshading:true,color:"#839fb6",opacity:.68,
      lighting:{ambient:.72,diffuse:.8,specular:.06,roughness:.85},
      hovertemplate:label+" · "+h+" m<extra></extra>"
    });
    traces.push(lineTrace([a,b,c,d,a],"#44627a",3));
  }
  const {width,depth} = frame;
  traces.push(lineTrace([[0,0,0],[width,0,0],[width,depth,0],[0,depth,0],[0,0,0]],"#8da1af",2));
  for (const item of frame.alternate) traces.push(lineTrace(item.path,BRANCH,3,"dot"));
  for (const v of frame.vehicles) {
    traces.push(lineTrace(v.tracks.flatMap(track => [...track,null]),v.color,5));
    if (v.heading) traces.push(lineTrace(v.heading,v.color,5));
    if (v.hasAim) traces.push(lineTrace([v.camera,v.aim],INK,4));
    if (v.sight) {
      const {target,blocked} = v.sight;
      traces.push(lineTrace([v.camera,target.point],blocked?BLOCKED:CLEAR,3,blocked?"dash":"solid"));
    }
  }
  traces.push(traceXY(frame.boxes.map(b => b.roof),{
    mode:"text",text:frame.boxes.map(b => b.label),textposition:"top center",
    textfont:{color:INK,size:11},hoverinfo:"skip"
  }));
  for (const {id,point,started} of frame.targets) {
    traces.push(lineTrace([[point[0],point[1],0],point],"#a58cae",2,"dot"));
    traces.push(traceXY([point],{mode:"markers+text",text:[id],textposition:"top center",
      textfont:{size:13,color:TARGET},marker:{size:7,color:started?CLEAR:TARGET,symbol:"diamond"},
      hovertemplate:id+" · "+point[2]+" m<extra></extra>"}));
  }
  for (const v of frame.vehicles) {
    const placements=["top right","top left","bottom right","bottom left","top right"];
    traces.push(traceXY([v.point],{mode:"markers+text",text:[v.name],
      textposition:placements[v.id-1],textfont:{size:13,color:v.failed?BLOCKED:INK},
      marker:{size:v.failed?9:6,color:v.failed?BLOCKED:v.color,symbol:v.failed?"x":"circle",
        line:{color:"#ffffff",width:1}},hovertemplate:v.name+"<extra></extra>"}));
  }
  return traces;
}

function plotlyLayout(frame) {
  const [x,y] = sceneRanges(frame);
  const eye = cameraMode === "top" ? {x:0,y:0,z:2.7} : {x:VIEW_X,y:VIEW_Y,z:VIEW_RADIUS};
  const axisOpts = {showbackground:true,backgroundcolor:"#f6f9fb",gridcolor:"#dfe7ec",
    showspikes:false,tickfont:{size:10},nticks:6};
  return {
    margin:{l:0,r:0,b:0,t:0},paper_bgcolor:"#fff",showlegend:false,
    uirevision:cameraRevision,scene:{
      xaxis:{...axisOpts,title:"East (m)",range:x},yaxis:{...axisOpts,title:"North (m)",range:y},
      zaxis:{...axisOpts,title:"Height (m)",range:[0,data.field.height]},
      aspectmode:"data",camera:{eye,up:cameraMode==="top"?{x:0,y:1,z:0}:{x:0,y:0,z:1},
        projection:{type:"orthographic"}}
    }
  };
}

function projector(frame, width, height) {
  const top = cameraMode === "top", s=Math.SQRT1_2;
  const project = ([x,y,z]) => top ? [x,-y] :
    [(-VIEW_Y*x+VIEW_X*y)/VIEW_RADIUS,s*((VIEW_X*x+VIEW_Y*y)/VIEW_RADIUS-z)];
  const ranges = sceneRanges(frame);
  const corners = ranges[0].flatMap(x => ranges[1].flatMap(y => [0,data.field.height].map(z => project([x,y,z]))));
  const [minX,maxX] = [Math.min,Math.max].map(f => f(...corners.map(p=>p[0])));
  const [minY,maxY] = [Math.min,Math.max].map(f => f(...corners.map(p=>p[1])));
  const pad = 27;
  const scale=Math.max(.1,Math.min((width-2*pad)/(maxX-minX),(height-2*pad)/(maxY-minY)));
  return point => {
    const [x,y]=project(point);
    return [width/2+(x-(minX+maxX)/2)*scale,height/2+(y-(minY+maxY)/2)*scale];
  };
}

function drawCanvas(canvas, frame, width, height, scale) {
  canvas.width = Math.round(width*scale);
  canvas.height = Math.round(height*scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw Error("Canvas 2D is unavailable");
  ctx.scale(scale,scale);
  ctx.fillStyle="#fff"; ctx.fillRect(0,0,width,height);
  ctx.lineJoin="round"; ctx.lineCap="round";
  const p = projector(frame,width,height);
  function shape(points, stroke, weight, dash=[], fill=null) {
    ctx.beginPath();
    const pixels=points.map(p);
    ctx.moveTo(...pixels[0]);
    for (const point of pixels.slice(1)) ctx.lineTo(...point);
    if (fill) { ctx.closePath(); ctx.fillStyle=fill; ctx.fill(); }
    ctx.lineWidth=weight; ctx.strokeStyle=stroke; ctx.setLineDash(dash); ctx.stroke();
  }
  const {width:w,depth:d} = frame;
  shape([[0,0,0],[w,0,0],[w,d,0],[0,d,0]],"#91a8ba",1.4,[],"#f3f7fb");
  for (let x=25; x<w; x+=25) shape([[x,0,0],[x,d,0]],"#d8e4ed",1);
  for (let y=25; y<d; y+=25) shape([[0,y,0],[w,y,0]],"#d8e4ed",1);
  for (const item of frame.alternate) shape(item.path,BRANCH,1.6,[1,4]);
  for (const v of frame.vehicles) for (const track of v.tracks) shape(track,v.color,2.5);
  const depthKey = ({roof:[x,y]}) => VIEW_X*x+VIEW_Y*y;
  const ordered = [...frame.boxes].sort((a,b)=>depthKey(a)-depthKey(b));
  for (const box of ordered) {
    const faces = cameraMode==="top" ? [[[4,5,6,7],"rgba(205,222,232,.84)"]] : [
      [[0,1,5,4],"rgba(128,160,183,.73)"],[[1,2,6,5],"rgba(153,179,197,.70)"],
      [[4,5,6,7],"rgba(205,222,232,.86)"]];
    for (const [face,fill] of faces) shape(face.map(i => box.points[i]),"#517089",1.1,[],fill);
  }
  for (const target of frame.targets) shape([[...target.point.slice(0,2),0],target.point],"#876d99",1.1,[2,4]);
  for (const v of frame.vehicles) {
    if (v.sight) shape([v.camera,v.sight.target.point],v.sight.blocked?BLOCKED:CLEAR,
      v.sight.blocked?1.6:2.1,v.sight.blocked?[6,4]:[]);
    if (v.heading) shape(v.heading,v.color,2.4);
    if (v.hasAim) shape([v.camera,v.aim],INK,2.3);
  }
  const labels = [], markers = [];
  for (const {id,point,started} of frame.targets) {
    const [x,y]=p(point);
    ctx.beginPath(); ctx.moveTo(x,y-6); ctx.lineTo(x+6,y); ctx.lineTo(x,y+6);
    ctx.lineTo(x-6,y); ctx.closePath(); ctx.fillStyle=started?CLEAR:TARGET; ctx.fill();
    markers.push({x,y}); labels.push({x,y,text:id,color:TARGET});
  }
  for (const v of frame.vehicles) {
    const [x,y]=p(v.point);
    ctx.setLineDash([]);
    if (v.failed) {
      ctx.strokeStyle=BLOCKED; ctx.lineWidth=2.5;
      ctx.beginPath(); ctx.moveTo(x-5,y-5); ctx.lineTo(x+5,y+5);
      ctx.moveTo(x-5,y+5); ctx.lineTo(x+5,y-5); ctx.stroke();
    } else {
      ctx.beginPath(); ctx.arc(x,y,5.3,0,2*Math.PI);
      ctx.fillStyle=v.color; ctx.fill();
      ctx.strokeStyle="#fff"; ctx.lineWidth=1.25; ctx.stroke();
    }
    markers.push({x,y}); labels.push({x,y,text:v.name,color:v.failed?BLOCKED:v.color});
  }
  for (const box of frame.boxes) {
    const [x,y]=p(box.roof);
    labels.push({x,y,text:box.label,color:INK});
  }
  ctx.font='600 12px "Segoe UI", sans-serif'; ctx.textBaseline="middle";
  const used = markers.map(({x,y}) => [x-5,y-5,10,10]);
  const fits = ([x,y,w,h]) => x>=3 && y>=3 && x+w<width-3 && y+h<height-3 &&
    used.every(([u,v,m,n]) => x+w<=u || u+m<=x || y+h<=v || v+n<=y);
  for (const {x,y,text,color} of labels) {
    const w = Math.ceil(ctx.measureText(text).width)+6, h=15;
    const options = [[-w/2,-24],[8,-h/2],[-w-8,-h/2],[-w/2,8],[12,-25],[-w-12,-25],
      [14,7],[-w-14,7],[-w/2,-42]];
    const slot = options.map(([dx,dy]) => [x+dx,y+dy,w,h]).find(fits);
    if (!slot) continue;
    used.push(slot);
    ctx.fillStyle="rgba(255,255,255,.9)"; ctx.fillRect(...slot);
    ctx.fillStyle=color; ctx.fillText(text,slot[0]+3,slot[1]+h/2);
  }
}

function supportsWebGL() {
  try {
    const canvas=document.createElement("canvas");
    const test=canvas.getContext("webgl");
    if (test) test.getExtension("WEBGL_lose_context")?.loseContext();
    return Boolean(test && window.Plotly);
  } catch (_) { return false; }
}

function showCanvas(frame) {
  const field=$("field");
  const canvas=$("canvasScene");
  $("plot3d").hidden=true;
  canvas.hidden=false;
  drawCanvas(canvas,frame,field.clientWidth,field.clientHeight,window.devicePixelRatio || 1);
  $("renderer").textContent="Canvas · isometric fallback";
  $("field").dataset.renderer="canvas";
  activeRenderer="canvas";
}

async function renderField(frame) {
  if (activeRenderer === "canvas") { showCanvas(frame); return; }
  if (!activeRenderer && !supportsWebGL()) { showCanvas(frame); return; }
  const scene = $("plot3d");
  const previous = activeRenderer;
  try {
    scene.hidden=false;
    await window.Plotly.react(scene,buildTraces(frame),plotlyLayout(frame),
      {responsive:true,displaylogo:false,modeBarButtonsToRemove:["toImage"]});
    if (!scene.querySelector(".gl-container canvas")) throw Error("Plotly did not create a WebGL canvas");
    if (previous === "webgl" && activeRenderer === "canvas") return;
    $("canvasScene").hidden=true;
    $("renderer").textContent="WebGL · interactive 3D";
    $("field").dataset.renderer="webgl";
    activeRenderer="webgl";
  } catch (_) {
    showCanvas(frame);
  }
}

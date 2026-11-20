/* Dark sci-fi 3D WebGL & 2.5D isometric Canvas renderer.
 * AI assistance: Antigravity (Gemini) & ChatGPT (Codex), 2026-11-21.
 * Display geometry only; all trajectories and LOS checks use verified solver intervals.
 */

const BG_DARK = "#0B1020";
const GRID_DARK = "#1E293B";
const INK_LIGHT = "#E2E8F0";
const CLEAR = "#2DD4BF";
const BLOCKED = "#F43F5E";
const BRANCH = "#94A3B8";
const TARGET = "#F59E0B";
const TARGET_OK = "#10B981";
const BLDG_EDGE = "#38BDF8";
const BLDG_MESH = "#0EA5E9";
const VIEW_X = 1.24, VIEW_Y = -1.62;
const VIEW_RADIUS = Math.hypot(VIEW_X, VIEW_Y);
let cameraMode = "iso";
let cameraRevision = 0;
let activeRenderer = "";

function traveledPath(event, at) {
  const points = [event.path[0]];
  let length = (Math.min(at, event.end_s) - event.phase_start_s) * data.field.speed;
  for (const b of event.path.slice(1)) {
    const a = points.at(-1);
    const leg = Math.hypot(b[0] - a[0], b[1] - a[1]);
    if (leg > length) {
      points.push(positionPath([a, b], length));
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
  const [x, y] = path.at(-1);
  const prev = path.findLast(([px, py]) => Math.hypot(x - px, y - py) > 1e-9);
  const next = travel.path.find((p, i) => i > 0 && Math.hypot(p[0] - x, p[1] - y) > 1e-9);
  const dx = prev ? x - prev[0] : next ? next[0] - x : 0;
  const dy = prev ? y - prev[1] : next ? next[1] - y : 0;
  const norm = Math.hypot(dx, dy);
  if (!norm) return null;
  const [px, py] = point, u = dx / norm, v = dy / norm;
  const z = 0.45, tip = [px + 3.2 * u, py + 3.2 * v, z];
  return [[px + 1.8 * u - 1.1 * v, py + 1.8 * v + 1.1 * u, z], tip, [px + 1.8 * u + 1.1 * v, py + 1.8 * v - 1.1 * u, z]];
}

function circleRing(cx, cy, z, radius, steps = 28) {
  const pts = [];
  for (let i = 0; i <= steps; i++) {
    const a = (2 * Math.PI * i) / steps;
    pts.push([cx + radius * Math.cos(a), cy + radius * Math.sin(a), z]);
  }
  return pts;
}

function roundedRectRing(x0, x1, y0, y1, r, z = 0.08) {
  const pts = [];
  const corners = [
    [x1, y1, 0, Math.PI / 2],
    [x0, y1, Math.PI / 2, Math.PI],
    [x0, y0, Math.PI, 1.5 * Math.PI],
    [x1, y0, 1.5 * Math.PI, 2 * Math.PI],
  ];
  for (const [cx, cy, a0, a1] of corners) {
    for (let i = 0; i <= 6; i++) {
      const a = a0 + ((a1 - a0) * i) / 6;
      pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a), z]);
    }
  }
  pts.push(pts[0]);
  return pts;
}

function firstHitPoint(a, b) {
  let bestT = Infinity;
  let hitLabel = null;
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
    if (lo <= hi + 1e-12 && lo < bestT) {
      bestT = Math.max(0, lo);
      hitLabel = "B" + (i + 1);
    }
  }
  if (!hitLabel) return null;
  return {
    label: hitLabel,
    point: [a[0] + bestT * (b[0] - a[0]), a[1] + bestT * (b[1] - a[1]), a[2] + bestT * (b[2] - a[2])],
  };
}

function coneRibs(origin, targetPt) {
  const dx = targetPt[0] - origin[0], dy = targetPt[1] - origin[1], dz = targetPt[2] - origin[2];
  const dist = Math.hypot(dx, dy, dz);
  if (dist < 1e-6) return [];
  const ux = dx / dist, uy = dy / dist, uz = dz / dist;
  // Orthogonal basis around LOS vector
  const ref = Math.abs(uz) < 0.9 ? [0, 0, 1] : [1, 0, 0];
  let px = uy * ref[2] - uz * ref[1];
  let py = uz * ref[0] - ux * ref[2];
  let pz = ux * ref[1] - uy * ref[0];
  const pn = Math.hypot(px, py, pz) || 1;
  px /= pn; py /= pn; pz /= pn;
  const qx = uy * pz - uz * py, qy = uz * px - ux * pz, qz = ux * py - uy * px;
  const coneLen = Math.min(dist * 0.42, 16);
  const coneRad = coneLen * Math.tan(0.14);
  const cx = origin[0] + ux * coneLen, cy = origin[1] + uy * coneLen, cz = origin[2] + uz * coneLen;
  const ring = [];
  for (let i = 0; i <= 12; i++) {
    const ang = (2 * Math.PI * i) / 12;
    const ca = Math.cos(ang), sa = Math.sin(ang);
    ring.push([cx + coneRad * (ca * px + sa * qx), cy + coneRad * (ca * py + sa * qy), cz + coneRad * (ca * pz + sa * qz)]);
  }
  const ribs = [ring];
  for (let i = 0; i < 12; i += 3) ribs.push([origin, ring[i]]);
  return ribs;
}

function frameGeometry(record, states) {
  const { buildings, width, depth, camera_m } = data.field;
  const boxes = buildings.map(([a, b, c, d, h], i) => ({
    bounds: [a, b, c, d, h],
    points: [[a, c, 0], [b, c, 0], [b, d, 0], [a, d, 0], [a, c, h], [b, c, h], [b, d, h], [a, d, h]],
    label: "B" + (i + 1) + " · " + h + "m",
    shortLabel: "B" + (i + 1),
    roof: [(a + b) / 2, (c + d) / 2, h],
    h,
  }));
  const targets = Object.entries(record.targets).filter(([id]) =>
    id !== "T4" || time >= record.disturbance_s
  ).map(([id, point]) => {
    const observed = record.scores[currentPolicy].starts[id];
    return { id, point, started: observed <= time && observed < data.field.horizon };
  });
  const rows = record.policies[currentPolicy];
  const showDual = $("dualOverlay") ? $("dualOverlay").checked : true;
  let branch = [];
  if (showDual && record.disturbance_s !== null && time >= record.disturbance_s) {
    const other = currentPolicy === "keep" ? "reschedule" : "keep";
    const signature = e => JSON.stringify([e.vehicle, e.alert, e.start_s, e.end_s, e.path]);
    const inView = new Set(rows.filter(e => e.phase === "travel").map(signature));
    branch = record.policies[other].filter(e => e.phase === "travel" &&
      e.end_s > record.disturbance_s && !inView.has(signature(e)));
  }
  const showLos = $("los") ? $("los").checked : true;
  const vehicles = states.map(state => {
    const related = rows.filter(e => e.vehicle === state.vehicle);
    const tracks = related.filter(e => e.phase === "travel" && time >= e.start_s)
      .map(e => traveledPath(e, time).map(q => [...q, 0.2]));
    const failed = state.phase === "failed";
    const target = targets.find(t => t.id === state.alert);
    const camera = [...state.point, camera_m];
    const az = state.pan * Math.PI / 180, el = state.tilt * Math.PI / 180;
    const aim = [
      camera[0] + 5.5 * Math.cos(el) * Math.cos(az),
      camera[1] + 5.5 * Math.cos(el) * Math.sin(az),
      camera[2] + 5.5 * Math.sin(el),
    ];
    const blocked = (!failed && target && showLos) ? hitBuilding(camera, target.point) : null;
    const hitInfo = blocked ? firstHitPoint(camera, target.point) : null;
    return {
      id: state.vehicle, name: "V" + state.vehicle, point: [...state.point, 0.5],
      phase: state.phase, color: data.vehicle_colors[state.vehicle - 1],
      tracks, camera, aim, failed,
      heading: failed ? null : headingAt(related, state.point),
      hasAim: !failed && state.phase !== "travel" && state.alert,
      sight: (!failed && target && showLos) ? {
        target, blocked, hitPoint: hitInfo ? hitInfo.point : null,
        cone: coneRibs(camera, target.point),
      } : null,
    };
  });
  return {
    boxes, targets, vehicles, width, depth, branch,
    showP1: $("p1layer") ? $("p1layer").checked : false,
    translucent: $("bldgTrans") ? $("bldgTrans").checked : true,
    alternate: branch.map(e => ({ vehicle: e.vehicle, path: e.path.map(point => [...point, 0.28]) })),
  };
}

function sceneRanges(frame) {
  if (cameraMode !== "follow") return [[0, frame.width], [0, frame.depth]];
  const tracked = frame.vehicles.find(v => v.id === Number($("tracked").value)) || frame.vehicles[0];
  return [frame.width, frame.depth].map((extent, i) => {
    const span = Math.min(65, extent);
    const min = Math.min(extent - span, Math.max(0, tracked.point[i] - span / 2));
    return [min, min + span];
  });
}

function traceXY(points, opts) {
  return {
    type: "scatter3d",
    x: points.map(q => q?.[0] ?? null),
    y: points.map(q => q?.[1] ?? null),
    z: points.map(q => q?.[2] ?? null),
    showlegend: false,
    ...opts,
  };
}

function lineTrace(points, color, width, dash = "solid", extra = {}) {
  return traceXY(points, { mode: "lines", line: { color, width, dash }, hoverinfo: "skip", ...extra });
}

function buildTraces(frame) {
  const traces = [];
  const { width, depth } = frame;
  // Subtle dark-tech ground grid & perimeter
  const gridPts = [];
  for (let x = 0; x <= width; x += 25) gridPts.push([x, 0, 0.02], [x, depth, 0.02], null);
  for (let y = 0; y <= depth; y += 25) gridPts.push([0, y, 0.02], [width, y, 0.02], null);
  traces.push(lineTrace(gridPts, "rgba(56,189,248,0.16)", 1.5));
  traces.push(lineTrace([[0, 0, 0.05], [width, 0, 0.05], [width, depth, 0.05], [0, depth, 0.05], [0, 0, 0.05]], "rgba(56,189,248,0.55)", 2.5));

  // Optional P1 real observability + rounded Minkowski safety layer
  if (frame.showP1 && data.p1_overlay) {
    const ov = data.p1_overlay;
    if (ov.feasible_xy.length) {
      traces.push(traceXY(ov.feasible_xy.map(q => [q[0], q[1], 0.06]), {
        mode: "markers", marker: { size: 2.6, color: "rgba(16,185,129,0.48)", symbol: "square" }, hoverinfo: "skip",
      }));
    }
    if (ov.occluded_xy.length) {
      traces.push(traceXY(ov.occluded_xy.map(q => [q[0], q[1], 0.06]), {
        mode: "markers", marker: { size: 2.3, color: "rgba(244,63,94,0.34)", symbol: "square" }, hoverinfo: "skip",
      }));
    }
    if (ov.optimal_arc.length) {
      traces.push(lineTrace(ov.optimal_arc.map(q => [q[0], q[1], 0.14]), "#38BDF8", 5));
    }
    const r = ov.vehicle_radius_m || 1.5;
    const safePts = [];
    for (const box of frame.boxes) {
      const [a, b, c, d] = box.bounds;
      safePts.push(...roundedRectRing(a, b, c, d, r, 0.1), null);
    }
    traces.push(lineTrace(safePts, "rgba(56,189,248,0.55)", 2, "dash"));
  }

  // Five buildings: translucent glowing cyan blocks + bright wireframe roof & vertical edges
  const bOpacity = frame.translucent ? 0.36 : 0.78;
  for (const { points, shortLabel, h } of frame.boxes) {
    const [a, b, c, d] = points.slice(4);
    traces.push({
      ...traceXY(points, {}),
      type: "mesh3d",
      name: shortLabel,
      i: [4, 4, 0, 0, 1, 1, 2, 2, 3, 3],
      j: [5, 6, 1, 5, 2, 6, 3, 7, 0, 4],
      k: [6, 7, 5, 4, 6, 5, 7, 6, 4, 7],
      flatshading: true,
      color: BLDG_MESH,
      opacity: bOpacity,
      lighting: { ambient: 0.65, diffuse: 0.85, specular: 0.25, roughness: 0.5 },
      hovertemplate: shortLabel + " · " + h + " m<extra></extra>",
    });
    // Wireframe roof + 4 vertical corner ribs
    const wire = [
      a, b, c, d, a, null,
      points[0], a, null, points[1], b, null, points[2], c, null, points[3], d,
    ];
    traces.push(lineTrace(wire, BLDG_EDGE, 2.5));
  }

  // Dual-policy alternate diverging routes (dashed slate)
  for (const item of frame.alternate) {
    traces.push(lineTrace(item.path, BRANCH, 3.5, "dash"));
  }

  // Vehicles: glowing trails, heading arrows, FOV cones, LOS rays & occlusion markers
  for (const v of frame.vehicles) {
    const trail = v.tracks.flatMap(track => [...track, null]);
    if (trail.length) {
      traces.push(lineTrace(trail, v.color, 5.5));
    }
    if (v.heading) traces.push(lineTrace(v.heading, v.color, 5));
    if (v.hasAim) traces.push(lineTrace([v.camera, v.aim], "#E0F2FE", 3.5));
    if (v.sight) {
      const { target, blocked, hitPoint, cone } = v.sight;
      const losColor = blocked ? BLOCKED : CLEAR;
      traces.push(lineTrace([v.camera, target.point], losColor, blocked ? 3 : 3.5, blocked ? "dash" : "solid"));
      if (cone && cone.length) {
        const conePts = cone.flatMap(seg => [...seg, null]);
        traces.push(lineTrace(conePts, blocked ? "rgba(244,63,94,0.35)" : "rgba(45,212,191,0.32)", 1.5));
      }
      if (hitPoint) {
        traces.push(traceXY([hitPoint], {
          mode: "markers", marker: { size: 6, color: BLOCKED, symbol: "x" },
          hovertemplate: "Occluded on " + blocked + "<extra></extra>",
        }));
      }
    }
    if (v.failed) {
      traces.push(lineTrace(circleRing(v.point[0], v.point[1], 0.35, 4.2, 24), BLOCKED, 3));
      traces.push(lineTrace(circleRing(v.point[0], v.point[1], 0.35, 7.2, 24), "rgba(244,63,94,0.45)", 2, "dash"));
    }
  }

  // Building height labels
  traces.push(traceXY(frame.boxes.map(b => [b.roof[0], b.roof[1], b.roof[2] + 1.2]), {
    mode: "text", text: frame.boxes.map(b => b.label), textposition: "top center",
    textfont: { color: "#BAE6FD", size: 11 }, hoverinfo: "skip",
  }));

  // Hovering UAV targets with glowing vertical drop lines and pulsing alert rings
  for (const { id, point, started } of frame.targets) {
    const tCol = started ? TARGET_OK : TARGET;
    traces.push(lineTrace([[point[0], point[1], 0], point], started ? "rgba(16,185,129,0.55)" : "rgba(245,158,11,0.55)", 2, "dot"));
    traces.push(lineTrace(circleRing(point[0], point[1], point[2], 3.2, 24), tCol, 2));
    traces.push(lineTrace(circleRing(point[0], point[1], 0.15, 2.6, 20), started ? "rgba(16,185,129,0.38)" : "rgba(245,158,11,0.38)", 1.5));
    traces.push(traceXY([point], {
      mode: "markers+text", text: [id], textposition: "top center",
      textfont: { size: 13, color: tCol },
      marker: { size: 7.5, color: tCol, symbol: "diamond", line: { color: "#FFFFFF", width: 1 } },
      hovertemplate: id + " · " + point[2] + " m<extra></extra>",
    }));
  }

  // Vehicle markers + labels
  const placements = ["top right", "top left", "bottom right", "bottom left", "top right"];
  for (const v of frame.vehicles) {
    traces.push(traceXY([v.point], {
      mode: "markers+text", text: [v.name], textposition: placements[v.id - 1],
      textfont: { size: 13, color: v.failed ? BLOCKED : v.color },
      marker: {
        size: v.failed ? 9.5 : 7,
        color: v.failed ? BLOCKED : v.color,
        symbol: v.failed ? "x" : "circle",
        line: { color: "#F8FAFC", width: 1.2 },
      },
      hovertemplate: v.name + " (" + v.phase + ")<extra></extra>",
    }));
  }
  return traces;
}

function plotlyLayout(frame) {
  const [x, y] = sceneRanges(frame);
  const eye = cameraMode === "top" ? { x: 0, y: 0, z: 2.65 } : { x: VIEW_X, y: VIEW_Y, z: VIEW_RADIUS * 0.92 };
  const axisOpts = {
    showbackground: true, backgroundcolor: "#0F172A", gridcolor: GRID_DARK,
    zerolinecolor: "#334155", linecolor: "#334155", showspikes: false,
    tickfont: { size: 10, color: "#94A3B8" }, titlefont: { size: 11, color: "#CBD5E1" }, nticks: 6,
  };
  return {
    margin: { l: 0, r: 0, b: 0, t: 0 },
    paper_bgcolor: BG_DARK,
    plot_bgcolor: BG_DARK,
    showlegend: false,
    uirevision: cameraRevision,
    scene: {
      bgcolor: BG_DARK,
      xaxis: { ...axisOpts, title: "East x (m)", range: x },
      yaxis: { ...axisOpts, title: "North y (m)", range: y },
      zaxis: { ...axisOpts, title: "Altitude z (m)", range: [0, data.field.height] },
      aspectmode: "data",
      camera: {
        eye,
        up: cameraMode === "top" ? { x: 0, y: 1, z: 0 } : { x: 0, y: 0, z: 1 },
        projection: { type: "orthographic" },
      },
    },
  };
}

function projector(frame, width, height) {
  const top = cameraMode === "top", s = Math.SQRT1_2;
  const project = ([x, y, z]) => top ? [x, -y] :
    [(-VIEW_Y * x + VIEW_X * y) / VIEW_RADIUS, s * ((VIEW_X * x + VIEW_Y * y) / VIEW_RADIUS - z)];
  const ranges = sceneRanges(frame);
  const corners = ranges[0].flatMap(x => ranges[1].flatMap(y => [0, data.field.height].map(z => project([x, y, z]))));
  const [minX, maxX] = [Math.min, Math.max].map(f => f(...corners.map(p => p[0])));
  const [minY, maxY] = [Math.min, Math.max].map(f => f(...corners.map(p => p[1])));
  const pad = 32;
  const scale = Math.max(0.1, Math.min((width - 2 * pad) / (maxX - minX), (height - 2 * pad) / (maxY - minY)));
  return point => {
    const [x, y] = project(point);
    return [width / 2 + (x - (minX + maxX) / 2) * scale, height / 2 + (y - (minY + maxY) / 2) * scale];
  };
}

function drawCanvas(canvas, frame, width, height, scale) {
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw Error("Canvas 2D is unavailable");
  ctx.scale(scale, scale);
  // Deep-space dark gradient backdrop
  const grad = ctx.createRadialGradient(width * 0.45, height * 0.35, 40, width * 0.5, height * 0.5, Math.max(width, height) * 0.8);
  grad.addColorStop(0, "#131F3A");
  grad.addColorStop(1, BG_DARK);
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, width, height);
  ctx.lineJoin = "round"; ctx.lineCap = "round";
  const p = projector(frame, width, height);

  function shape(points, stroke, weight, dash = [], fill = null) {
    if (!points || points.length < 2) return;
    ctx.beginPath();
    const pixels = points.map(p);
    ctx.moveTo(...pixels[0]);
    for (const point of pixels.slice(1)) ctx.lineTo(...point);
    if (fill) { ctx.closePath(); ctx.fillStyle = fill; ctx.fill(); }
    if (stroke) { ctx.lineWidth = weight; ctx.strokeStyle = stroke; ctx.setLineDash(dash); ctx.stroke(); }
  }

  const { width: w, depth: d } = frame;
  shape([[0, 0, 0], [w, 0, 0], [w, d, 0], [0, d, 0]], "rgba(56,189,248,0.55)", 1.6, [], "rgba(15,23,42,0.92)");
  for (let x = 25; x < w; x += 25) shape([[x, 0, 0], [x, d, 0]], "rgba(56,189,248,0.14)", 1);
  for (let y = 25; y < d; y += 25) shape([[0, y, 0], [w, y, 0]], "rgba(56,189,248,0.14)", 1);

  // Optional P1 observability & rounded safety ground overlay
  if (frame.showP1 && data.p1_overlay) {
    const ov = data.p1_overlay;
    ctx.fillStyle = "rgba(16,185,129,0.42)";
    for (const [x, y] of ov.feasible_xy) {
      const [px, py] = p([x, y, 0]);
      ctx.fillRect(px - 1.5, py - 1.5, 3, 3);
    }
    ctx.fillStyle = "rgba(244,63,94,0.30)";
    for (const [x, y] of ov.occluded_xy) {
      const [px, py] = p([x, y, 0]);
      ctx.fillRect(px - 1.2, py - 1.2, 2.4, 2.4);
    }
    if (ov.optimal_arc.length) shape(ov.optimal_arc.map(q => [q[0], q[1], 0.1]), "#38BDF8", 2.6);
    const r = ov.vehicle_radius_m || 1.5;
    for (const box of frame.boxes) {
      const [a, b, c, dd] = box.bounds;
      shape(roundedRectRing(a, b, c, dd, r, 0.1), "rgba(56,189,248,0.5)", 1.2, [4, 3]);
    }
  }

  for (const item of frame.alternate) shape(item.path, BRANCH, 1.8, [5, 4]);
  for (const v of frame.vehicles) {
    for (const track of v.tracks) shape(track, v.color, 2.8);
  }

  // Depth-sorted translucent glowing buildings
  const depthKey = ({ roof: [x, y] }) => VIEW_X * x + VIEW_Y * y;
  const ordered = [...frame.boxes].sort((a, b) => depthKey(a) - depthKey(b));
  const alphaTop = frame.translucent ? 0.34 : 0.78;
  const alphaSide = frame.translucent ? 0.24 : 0.65;
  for (const box of ordered) {
    const faces = cameraMode === "top"
      ? [[[4, 5, 6, 7], `rgba(14,165,233,${alphaTop})`]]
      : [
          [[0, 1, 5, 4], `rgba(2,132,199,${alphaSide})`],
          [[1, 2, 6, 5], `rgba(14,165,233,${alphaSide + 0.06})`],
          [[4, 5, 6, 7], `rgba(56,189,248,${alphaTop})`],
        ];
    for (const [face, fill] of faces) shape(face.map(i => box.points[i]), BLDG_EDGE, 1.2, [], fill);
  }

  for (const target of frame.targets) {
    const tCol = target.started ? TARGET_OK : TARGET;
    shape([[...target.point.slice(0, 2), 0], target.point], tCol, 1.2, [3, 4]);
    shape(circleRing(target.point[0], target.point[1], target.point[2], 3.2, 24), tCol, 1.4);
  }

  for (const v of frame.vehicles) {
    if (v.sight) {
      const losCol = v.sight.blocked ? BLOCKED : CLEAR;
      if (v.sight.cone) {
        for (const rib of v.sight.cone) shape(rib, v.sight.blocked ? "rgba(244,63,94,0.28)" : "rgba(45,212,191,0.28)", 1);
      }
      shape([v.camera, v.sight.target.point], losCol, v.sight.blocked ? 1.8 : 2.3, v.sight.blocked ? [6, 4] : []);
      if (v.sight.hitPoint) {
        const [hx, hy] = p(v.sight.hitPoint);
        ctx.setLineDash([]); ctx.strokeStyle = BLOCKED; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.moveTo(hx - 4, hy - 4); ctx.lineTo(hx + 4, hy + 4);
        ctx.moveTo(hx - 4, hy + 4); ctx.lineTo(hx + 4, hy - 4); ctx.stroke();
      }
    }
    if (v.heading) shape(v.heading, v.color, 2.6);
    if (v.hasAim) shape([v.camera, v.aim], "#E0F2FE", 2.2);
    if (v.failed) {
      shape(circleRing(v.point[0], v.point[1], 0.35, 4.2, 24), BLOCKED, 2.0);
      shape(circleRing(v.point[0], v.point[1], 0.35, 7.2, 24), "rgba(244,63,94,0.45)", 1.3, [4, 4]);
    }
  }

  const labels = [], markers = [];
  for (const { id, point, started } of frame.targets) {
    const [x, y] = p(point);
    const tCol = started ? TARGET_OK : TARGET;
    ctx.setLineDash([]);
    ctx.beginPath(); ctx.moveTo(x, y - 6.5); ctx.lineTo(x + 6.5, y); ctx.lineTo(x, y + 6.5);
    ctx.lineTo(x - 6.5, y); ctx.closePath(); ctx.fillStyle = tCol; ctx.fill();
    ctx.strokeStyle = "#F8FAFC"; ctx.lineWidth = 1; ctx.stroke();
    markers.push({ x, y }); labels.push({ x, y, text: id, color: tCol });
  }
  for (const v of frame.vehicles) {
    const [x, y] = p(v.point);
    ctx.setLineDash([]);
    if (v.failed) {
      ctx.strokeStyle = BLOCKED; ctx.lineWidth = 2.8;
      ctx.beginPath(); ctx.moveTo(x - 5.5, y - 5.5); ctx.lineTo(x + 5.5, y + 5.5);
      ctx.moveTo(x - 5.5, y + 5.5); ctx.lineTo(x + 5.5, y - 5.5); ctx.stroke();
    } else {
      ctx.beginPath(); ctx.arc(x, y, 5.5, 0, 2 * Math.PI);
      ctx.fillStyle = v.color; ctx.fill();
      ctx.strokeStyle = "#F8FAFC"; ctx.lineWidth = 1.4; ctx.stroke();
    }
    markers.push({ x, y }); labels.push({ x, y, text: v.name, color: v.failed ? BLOCKED : v.color });
  }
  for (const box of frame.boxes) {
    const [x, y] = p([box.roof[0], box.roof[1], box.roof[2] + 1.2]);
    labels.push({ x, y, text: box.label, color: "#BAE6FD" });
  }

  ctx.font = '600 11.5px "Segoe UI", sans-serif'; ctx.textBaseline = "middle";
  const used = markers.map(({ x, y }) => [x - 6, y - 6, 12, 12]);
  const fits = ([x, y, bw, bh]) => x >= 4 && y >= 4 && x + bw < width - 4 && y + bh < height - 4 &&
    used.every(([u, v, m, n]) => x + bw <= u || u + m <= x || y + bh <= v || v + n <= y);
  for (const { x, y, text, color } of labels) {
    const bw = Math.ceil(ctx.measureText(text).width) + 8, bh = 16;
    const options = [[-bw / 2, -24], [9, -bh / 2], [-bw - 9, -bh / 2], [-bw / 2, 9],
      [13, -24], [-bw - 13, -24], [14, 8], [-bw - 14, 8], [-bw / 2, -42]];
    const slot = options.map(([dx, dy]) => [x + dx, y + dy, bw, bh]).find(fits);
    if (!slot) continue;
    used.push(slot);
    ctx.fillStyle = "rgba(11,16,32,0.88)"; ctx.fillRect(...slot);
    ctx.strokeStyle = "rgba(56,189,248,0.28)"; ctx.lineWidth = 0.8; ctx.strokeRect(...slot);
    ctx.fillStyle = color; ctx.fillText(text, slot[0] + 4, slot[1] + bh / 2);
  }
}

function supportsWebGL() {
  try {
    const canvas = document.createElement("canvas");
    const test = canvas.getContext("webgl");
    if (test) test.getExtension("WEBGL_lose_context")?.loseContext();
    return Boolean(test && window.Plotly);
  } catch (_) { return false; }
}

function showCanvas(frame) {
  const field = $("field");
  const canvas = $("canvasScene");
  $("plot3d").hidden = true;
  canvas.hidden = false;
  drawCanvas(canvas, frame, field.clientWidth || 900, field.clientHeight || 625, window.devicePixelRatio || 1);
  $("renderer").textContent = "Canvas 2.5D · dark isometric fallback";
  $("field").dataset.renderer = "canvas";
  activeRenderer = "canvas";
}

async function renderField(frame) {
  if (activeRenderer === "canvas") { showCanvas(frame); return; }
  if (!activeRenderer && !supportsWebGL()) { showCanvas(frame); return; }
  const scene = $("plot3d");
  const previous = activeRenderer;
  try {
    scene.hidden = false;
    await window.Plotly.react(scene, buildTraces(frame), plotlyLayout(frame),
      { responsive: true, displaylogo: false, modeBarButtonsToRemove: ["toImage"] });
    if (!scene.querySelector(".gl-container canvas")) throw Error("Plotly did not create a WebGL canvas");
    if (previous === "webgl" && activeRenderer === "canvas") return;
    $("canvasScene").hidden = true;
    $("renderer").textContent = "WebGL 3D · dark digital twin";
    $("field").dataset.renderer = "webgl";
    activeRenderer = "webgl";
  } catch (_) {
    showCanvas(frame);
  }
}

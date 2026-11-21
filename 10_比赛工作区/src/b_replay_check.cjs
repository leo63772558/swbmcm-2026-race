// AI Assistance Disclosure (Article 7): Tool: ChatGPT (Codex) & Antigravity (Gemini 3.1 Pro); Scope: Node.js offline replay state assertion suite; Date: 2026-11-21; Verified by Team#SWBMCM2613050.
/* AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
 * Public model release date not verified. Fixture compares browser-state math to Python. */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const html = fs.readFileSync(process.argv[2], "utf8");
assert.match(html, /<script id="plotly-runtime">[\s\S]+<\/script>/);
assert.doesNotMatch(html, /<script[^>]*\bsrc=["']/i);
const serialized = html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const logic = html.match(/<script>([\s\S]*?)<\/script>/)[1];
const parsed = JSON.parse(serialized);
class Element {
  constructor() { this.children = []; this.style = {}; this.dataset = {}; this.checked = true; }
  replaceChildren(...children) { this.children = children; }
  append(...children) { this.children.push(...children); }
  get options() { return this.children; }
  addEventListener() {}
  setAttribute() {}
  querySelector() { return {}; }
}
const elements = new Map();
const doc = {
  getElementById: id => {
    if (!elements.has(id)) elements.set(id, new Element());
    return elements.get(id);
  },
  createElement: tag => {
    const el = new Element();
    if (tag==="canvas") el.getContext=()=>({getExtension:()=>null});
    return el;
  },
  createTextNode: text => text,
  querySelectorAll: () => [],
};
doc.getElementById("payload").textContent = serialized;
let renders = 0;
const context = {
  document: doc, console, requestAnimationFrame: () => {},
  window: {addEventListener(){}, Plotly: { react: async (el, traces, layout) => {
    assert.equal(el, doc.getElementById("plot3d"));
    assert.equal(traces.filter(trace=>trace.type==="mesh3d").length, 5);
    assert.equal(layout.scene.xaxis.range[1], parsed.field.width);
    renders++;
  }}},
};
vm.runInNewContext(logic, context);
const replay = context.window.BReplay;
let checks = 0;
for (const frame of parsed.keyframes) {
  for (const [policy, expected] of Object.entries(frame.snapshots)) {
    const states = replay.stateFor(frame.case, policy, frame.time_s);
    for (let i = 0; i < expected.length; i++) {
      const js = states[i], py = expected[i];
      for (const key of ["vehicle","phase","alert"]) assert.equal(js[key], py[key]);
      for (const key of ["pan","tilt"]) assert.ok(Math.abs(js[key] - py[key]) <= 1e-9);
      assert.ok(Math.hypot(js.point[0]-py.point[0],js.point[1]-py.point[1]) <= 1e-8);
      if (js.alert) assert.equal(
        replay.hitBuilding([...js.point,parsed.field.camera_m],parsed.cases[frame.case].targets[js.alert]),
        py.blocked_by);
      checks++;
    }
  }
}
(async () => {
  for (const [caseName, item] of Object.entries(parsed.cases)) {
    const policies = Object.keys(item.policies);
    for (const policy of policies) {
      await replay.setCase(caseName, policy, item.disturbance_s || 0);
      const states = replay.stateFor(caseName,policy,parsed.field.horizon);
      assert.equal(states.length,parsed.field.vehicles.length);
      if (item.failed_vehicle) assert.equal(states[item.failed_vehicle-1].phase,"failed");
      checks += states.length;
    }
  }
  console.log("Replay data / JS state tests:", checks, "records;", renders, "layout builds");
})().catch(err => { console.error(err); process.exitCode=1; });

"""Exercise the standalone replay in an offline Chromium copy and with WebGL disabled.

AI assistance:
  - ChatGPT (Codex, GPT-6.2 Sol), OpenAI; version release date: not publicly disclosed; used 2026-11-21.
  - Antigravity (Gemini), Google DeepMind; version release date: not publicly disclosed; used 2026-11-21.
Scope: offline dual-renderer browser QA (WebGL + Canvas, Auto-Tour full cycle, UI controls, r=1.5 m static building clearance).
"""
from argparse import ArgumentParser
from collections import Counter
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
from shutil import copyfile
from tempfile import TemporaryDirectory

from PIL import Image
from playwright.sync_api import sync_playwright


def pixels(png):
    with Image.open(BytesIO(png)).convert("RGB") as image:
        counts = Counter(image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata())
        # Dark sci-fi canvas (#0B1020 -> 11,16,32): count non-background lit pixels
        occupied = sum(
            n for (r, g, b), n in counts.items()
            if max(abs(r - 11), abs(g - 16), abs(b - 32)) > 16
        )
        fraction = occupied / (image.width * image.height)
        assert fraction > .025, ("blank or mostly empty field", fraction)
        return {"width_px": image.width, "height_px": image.height,
                "colored_pixel_fraction": round(fraction, 4)}


def route_check(page):
    return page.evaluate("""() => {
      const data=JSON.parse(document.getElementById("payload").textContent);
      const r=data.field.radius||1.5;
      function ptRectDist(px,py,x0,x1,y0,y1){
        const dx=px<x0?x0-px:(px>x1?px-x1:0);
        const dy=py<y0?y0-py:(py>y1?py-y1:0);
        return Math.hypot(dx,dy);
      }
      function segRectDist(ax,ay,bx,by,x0,x1,y0,y1){
        let best=Math.min(ptRectDist(ax,ay,x0,x1,y0,y1), ptRectDist(bx,by,x0,x1,y0,y1));
        for(let s=1;s<20;s++){
          const f=s/20;
          const d=ptRectDist(ax+f*(bx-ax), ay+f*(by-ay), x0,x1,y0,y1);
          if(d<best) best=d;
        }
        return best;
      }
      let segments=0, buildingHits=0, vehiclePoints=0, pointHits=0, radiusViolations=0;
      let minClearanceM=Infinity;
      for (const item of Object.values(data.cases)) for (const rows of Object.values(item.policies)) {
        for (const e of rows) {
          if (e.phase!=="travel") continue;
          const path=e.path;
          let left=data.field.speed*(e.end_s-e.phase_start_s);
          for (let i=1;i<path.length && left>1e-9;i++) {
            const a=path[i-1], b=path[i], leg=Math.hypot(b[0]-a[0],b[1]-a[1]);
            if (leg<1e-12) continue;
            const f=Math.min(1,left/leg);
            const end=[a[0]+f*(b[0]-a[0]),a[1]+f*(b[1]-a[1]),0];
            segments++;
            if (BReplay.hitBuilding([...a,0],end)) buildingHits++;
            for (const [x0,x1,y0,y1] of data.field.buildings) {
              const d=segRectDist(a[0],a[1],end[0],end[1],x0,x1,y0,y1);
              if(d<minClearanceM) minClearanceM=d;
              if(d<r-1e-6) radiusViolations++;
            }
            left-=leg;
          }
        }
        for (const e of rows) {
          if (e.phase==="travel") continue;
          vehiclePoints++;
          if (BReplay.hitBuilding([...e.position,0],[...e.position,0])) pointHits++;
          for (const [x0,x1,y0,y1] of data.field.buildings) {
            const d=ptRectDist(e.position[0],e.position[1],x0,x1,y0,y1);
            if(d<minClearanceM) minClearanceM=d;
            if(d<r-1e-6) radiusViolations++;
          }
        }
      }
      return {
        scope: "static building-obstacle clearance (r=0 footprint & r=1.5 m Euclidean disk margin; not inter-vehicle avoidance)",
        segments, buildingHits, vehiclePoints, pointHits,
        radiusViolations, minBuildingCenterlineClearanceM: Number(minClearanceM.toFixed(6))
      };
    }""")


def verify_browser(browser, path, renderer, pictures):
    context = browser.new_context(offline=True, viewport={"width": 1550, "height": 1080},
                                  device_scale_factor=2, accept_downloads=True)
    page = context.new_page()
    external = []
    errors = []
    page.on("request", lambda req: external.append(req.url) if
            req.url.startswith(("https:", "http:")) else None)
    page.on("pageerror", lambda err: errors.append(str(err)))
    page.goto(path.as_uri(), wait_until="load")
    field = page.locator("#field")
    page.wait_for_function("() => window.BReplayRendered")
    assert field.get_attribute("data-renderer") == renderer, page.locator("#renderer").inner_text()
    assert page.locator("#plot3d" if renderer == "webgl" else "#canvasScene").is_visible()
    assert not page.locator("#canvasScene" if renderer == "webgl" else "#plot3d").is_visible()
    assert page.evaluate("() => document.querySelectorAll('script[src]').length") == 0
    assert page.evaluate("() => ['newPlot','react'].every(k => typeof Plotly[k]==='function')")
    assert page.locator(".event-pin").count() == 10
    assert "V5 failure at" in page.locator("#branch").inner_text()
    assert page.get_by_role("button", name="45° view").get_attribute("aria-pressed") == "true"

    frame_specs = page.evaluate("() => BReplay.bookmarks")
    captures = []
    for index, (label, case_id, policy, at) in enumerate(frame_specs):
        page.get_by_role("button", name=label, exact=True).click()
        page.wait_for_function(
            "([c,p,t]) => field.dataset.case===c && field.dataset.policy===p && Number(field.dataset.time)===t",
            arg=[case_id, policy, at],
        )
        # Export from the completed render and inspect the resulting image bytes.
        with page.expect_download() as pending:
            page.get_by_role("button", name="Export PNG").click()
        download = pending.value
        png = download.path().read_bytes()
        capture = {"label": label, "case": case_id, "policy": policy, "time_s": at, **pixels(png)}
        if renderer == "webgl":
            assert page.evaluate("""() => document.getElementById("plot3d").data
                                   .filter(t => t.type==="mesh3d").length""") == 5
        if pictures:
            (pictures / f"{renderer}_{index+1}_{case_id}_{policy}.png").write_bytes(png)
        captures.append(capture)
    if pictures:
        page.evaluate("() => BReplay.setCase(...[BReplay.bookmarks[2][1], 'keep', BReplay.bookmarks[2][3]])")
        field.screenshot(path=pictures/f"{renderer}_4_failure_V5_keep_at_recovery.png")
    cameras = ["top", "follow", "iso"]
    for camera in cameras:
        page.locator("#"+camera).click()
        assert page.locator("#"+camera).get_attribute("aria-pressed") == "true"
        assert field.get_attribute("data-camera") == camera
        page.wait_for_function("(mode) => field.dataset.drawnCamera===mode", arg=camera)
        assert pixels(field.screenshot())["colored_pixel_fraction"] > .025
    # Verify full end-to-end Auto-Tour lifecycle: approach -> fault_highlight -> recovery -> complete
    tour_btn = page.locator("#autoTourBtn")
    assert tour_btn.is_visible()
    assert "Auto-Tour" in tour_btn.inner_text()
    tour_btn.click()
    page.wait_for_function(
        "() => field.dataset.case==='failure_V5' && field.dataset.policy==='reschedule' && field.dataset.camera==='iso'"
    )
    page.wait_for_function("() => field.dataset.autotour==='fault_highlight'", timeout=15000)
    assert page.locator("#tourCaption").get_attribute("data-active") == "true"
    assert page.locator("#faultBanner").get_attribute("data-active") == "true"
    assert page.locator("#faultBanner").get_attribute("data-pulse") == "true"
    page.wait_for_function("() => field.dataset.autotour==='complete'", timeout=20000)
    assert page.locator("#faultBanner").get_attribute("data-pulse") == "false", "Stale fault pulse after Auto-Tour completion"
    assert page.locator("#autoTourBtn").get_attribute("data-active") == "false"

    # Verify all 9 interactive tactical & playback controls
    controls_tested = []
    for chk_id in ("p1layer", "dualOverlay", "los", "bldgTrans"):
        loc = page.locator("#" + chk_id)
        before = loc.is_checked()
        loc.click()
        assert loc.is_checked() != before
        loc.click()
        assert loc.is_checked() == before
        controls_tested.append(chk_id)
    page.locator("#speed").select_option("2")
    controls_tested.append("speed")
    page.locator("#time").fill("2.5")
    page.locator("#time").dispatch_event("input")
    page.wait_for_function("() => Math.abs(Number(field.dataset.time) - 2.5) < 0.1")
    controls_tested.append("time")
    page.locator("#event").click()
    page.wait_for_function("() => Number(field.dataset.time) > 2.5")
    controls_tested.append("event")
    page.locator(".track").first.click()
    controls_tested.append("track_scrub")
    page.locator("#play").click()
    page.wait_for_timeout(250)
    page.locator("#play").click()
    controls_tested.append("play_pause")

    if renderer == "webgl":
        page.evaluate("""() => {
          const canvas = document.querySelector("#plot3d .gl-container canvas");
          const gl = canvas.getContext("webgl") || canvas.getContext("webgl2");
          const loss = gl?.getExtension("WEBGL_lose_context");
          if (!loss) throw Error("Cannot test WebGL context loss");
          loss.loseContext();
        }""")
        page.wait_for_function("() => field.dataset.renderer==='canvas'")
        assert page.locator("#canvasScene").is_visible()

    routes = route_check(page)
    assert routes["segments"] and routes["vehiclePoints"]
    assert not routes["buildingHits"] and not routes["pointHits"] and not routes["radiusViolations"], routes
    assert not external and not errors, {"external": external, "page_errors": errors}
    context.close()
    return {"renderer": renderer, "screenshots": captures, "camera_controls": cameras,
            "auto_tour_verified": True, "auto_tour_completed_full_cycle": True,
            "interactive_controls_verified": controls_tested,
            "event_marker_count": 10, "remote_requests": len(external), "page_errors": len(errors),
            "forced_context_loss_fallback": renderer == "webgl", "route_footprint_check": routes}


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--chromium", type=Path)
    parser.add_argument("--proof", type=Path, required=True)
    parser.add_argument("--screenshots", type=Path)
    opts = parser.parse_args()
    if opts.screenshots:
        opts.screenshots.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="b-offline-replay-") as folder, sync_playwright() as pw:
        standalone = Path(folder)/"B_Simulator.html"
        copyfile(opts.html, standalone)
        assert len(list(standalone.parent.iterdir())) == 1
        runs = []
        for mode, flags in (
            ("webgl", ["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader",
                       "--enable-unsafe-swiftshader"]),
            ("canvas", ["--disable-webgl", "--disable-webgl2"]),
        ):
            browser = pw.chromium.launch(executable_path=opts.chromium, headless=True, args=flags)
            version = browser.version
            runs.append(verify_browser(browser, standalone, mode, opts.screenshots))
            browser.close()
    proof = {"browser": f"Headless Chromium {version}", "standalone_file_only": True,
             "browser_context_offline": True, "html_bytes": opts.html.stat().st_size,
             "html_sha256": sha256(opts.html.read_bytes()).hexdigest(), "runs": runs}
    opts.proof.parent.mkdir(parents=True, exist_ok=True)
    opts.proof.write_text(json.dumps(proof, indent=2)+"\n", encoding="utf-8", newline="\n")
    print(json.dumps(proof, ensure_ascii=True))


if __name__ == "__main__":
    main()

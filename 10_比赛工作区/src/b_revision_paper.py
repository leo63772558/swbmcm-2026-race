"""Generate evidence macros, compile the English team review and verify its PDF.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: data binding and typesetting.
"""
from argparse import ArgumentParser
from os.path import relpath
from pathlib import Path
from shutil import which
import re
import subprocess

from PIL import Image
from pypdf import PdfReader

from b_revision_data import DEFAULT_OUTPUT, read_csv, read_json, write_csv, write_json


TEAM_NUMBER = "SWBMCM2613050"


def metrics(root):
    results = root/"results"
    paper = root/"paper"
    source = []
    def add(name, value, from_file, key, field, digits=None):
        rendered = str(value) if digits is None else f"{float(value):.{digits}f}"
        source.append({"macro":name,"rendered":rendered,"source_file":"results/"+from_file,
                       "record":key,"field":field,"raw":value})
    p1 = {x["tie"]:x for x in read_csv(results/"P1_station.csv")}
    for macro,field,num in (("MinRange","range_m",6),("MaxPitch","elevation_deg",0),
                            ("Quality","quality_m_inv",6),("ReadyTime","ready_s",6),
                            ("StationX","x_m",6),("StationY","y_m",6),
                            ("ArrivalTime","arrival_s",6),("ReadyAngle","azimuth_deg",3)):
        add(macro,p1["ready"][field],"P1_station.csv","tie=ready",field,num)
    add("AltArrival",p1["arrival"]["arrival_s"],"P1_station.csv","tie=arrival","arrival_s",6)
    arc, = read_csv(results/"P1_arc.csv")
    for macro,field in (("ArcStart","start_deg"),("ArcEnd","end_deg"),("ArcLength","length_m")):
        add(macro,arc[field],"P1_arc.csv","first row",field,6)
    areas = read_csv(results/"P1_area.csv")
    a = next(r for r in areas if r["step_m"]=="0.1")
    add("GridArea",a["intersection_area_m2"],"P1_area.csv","step_m=0.1 phase=0.5","intersection_area_m2",1)
    loss = read_csv(results/"P1_pitch_checks.csv")[1]
    add("PitchLoss",100*float(loss["relative_quality_loss"]),"P1_pitch_checks.csv",
        f'ceiling={loss["elevation_ceiling_deg"]}',"100*relative_quality_loss",4)
    branches=read_csv(results/"P1_ready_branches.csv")
    for letter,row in zip("ABCD",branches,strict=True):
        sel=f'from_deg={row["from_deg"]}'
        for macro, field, digits in (("From","from_deg",3),("To","to_deg",3),
                                     ("BranchBest","feasible_ready_s",6),("At","argmin_grid_deg",3)):
            add(macro+letter,row[field],"P1_ready_branches.csv",sel,field,digits)
    p2, = read_csv(results/"P2_precision.csv")
    for macro,field,digits in (("FirstRMS","horizontal_rms_m",6),("BaseLength","baseline_m",3),
                               ("Crossing","crossing_deg",0),("TravelFirst","rounded_travel_1_s",3),
                               ("TravelSecond","rounded_travel_2_s",3)):
        add(macro,p2[field],"P2_precision.csv","first row",field,digits)
    trials = [r for r in read_csv(results/"P2_trials.csv") if r["routing"]=="rounded" and r["beam_width"]=="20"]
    for k,label in (("3","Three"),("8","Eight")):
        for policy,name in (("beam","Beam"),("nearest","Nearest")):
            r = next(v for v in trials if v["k"]==k and v["policy"]==policy)
            add(name+label,r["latest_start_s"],"P2_trials.csv",f"rounded; k={k}; {policy}","latest_start_s",3)
    p3=read_json(results/"P3_verification.json")
    for name,field,digits in (("TravelThreshold","archived_distance_m",3),
                              ("IntegratedCrossing","independent_crossing_m",6),
                              ("SigmaCrossing","sigma_at_crossing_m",6),
                              ("FarBound","tail_probability_upper_bound",4)):
        add(name,p3[field],"P3_verification.json","root",field,digits)
    for i, name in enumerate(("BracketLow","BracketHigh")):
        add(name,p3["bracket_m"][i],"P3_verification.json","root",f"bracket_m[{i}]",6)
    run = read_json(results/"priority_3.json")
    for name,field,places in (("CaseCount","P4_case_count",None),("VFiveDelay","V5_delay_s",3)):
        add(name,run[field],"priority_3.json","root",field,places)
    for policy,name in (("keep","KeepLast"),("reschedule","ReplanLast")):
        add(name,run["V5_scores"][policy]["latest_start_s"],"priority_3.json",
            f"V5_scores.{policy}","latest_start_s",3)
    routing = read_json(results/"Route_summary.json")
    for name, field, places in (("RouteCount","compared_routes",None),("ShortenedCount","shorter_paths",None),
                                ("RestoredCount","restored_endpoints",None),
                                ("SavingsMax","maximum_saving_m",5)):
        add(name,routing[field],"Route_summary.json","root",field,places)
    write_csv(paper/"NUMBER_PROVENANCE.csv",source)
    macro_lines = [f"\\newcommand{{\\B{r['macro']}}}{{{r['rendered']}}}" for r in source]
    (paper/"B_review_metrics.tex").write_text(
        "% Automatically generated from NUMBER_PROVENANCE.csv.\n"+"\n".join(macro_lines)+"\n",encoding="utf-8")
    return source


def compile_tex(path,bundle):
    engine = which("tectonic")
    if not engine:
        raise RuntimeError("Tectonic unavailable; source can also be compiled with XeLaTeX.")
    command = [engine,"--untrusted","--only-cached","--keep-logs","--keep-intermediates"]
    if bundle:
        command.extend(["--bundle",Path(relpath(bundle.resolve(), path.parent.resolve())).as_posix()])
    command.append(path.name)
    proc = subprocess.run(command,cwd=path.parent,check=False,capture_output=True,text=True,
                          encoding="utf-8",errors="replace",timeout=120)
    (path.parent/(path.stem+"_compile.txt")).write_text(proc.stdout+proc.stderr,encoding="utf-8")
    if proc.returncode:
        raise RuntimeError(f"Tectonic failed ({proc.returncode}): {proc.stderr[-2000:]}")
    return path.with_suffix(".pdf")


def inspect_pdf(path, qa, *, paper=True):
    reader = PdfReader(path)
    assert 0<len(reader.pages)<=25 and not reader.attachments
    assert not (reader.metadata.author if reader.metadata else None)
    qa.mkdir(parents=True,exist_ok=True)
    subprocess.run(["pdftoppm","-r","140","-png",str(path),str(qa/path.stem)],check=True)
    logs = []
    text_pages = []
    for i,page in enumerate(reader.pages,start=1):
        width,height = map(float,(page.mediabox.width,page.mediabox.height))
        assert abs(width-595.276)<.35 and abs(height-841.89)<.35, (i,width,height)
        text = page.extract_text() or ""
        cleaned = re.sub(r"\s+","",text)
        assert len(cleaned)>60 and "\ufffd" not in text and not re.search(r"[\u3400-\u9fff]",text), i
        if paper:
            assert (f"Team#{TEAM_NUMBER}" in cleaned) == (i>1)
            if i>1:
                assert f"Page{i}of{len(reader.pages)}" in cleaned, (i,cleaned[:100])
            if i==1:
                assert "Summary" in text and "Keywords" in text
            if i==2:
                assert "Content" in text
        fonts = page["/Resources"]["/Font"].get_object()
        names = sorted({str(font.get_object().get("/BaseFont","")) for font in fonts.values()})
        assert any("TimesNewRoman" in name for name in names), (i,names)
        pngs = sorted(qa.glob(path.stem+"-*.png"))
        assert len(pngs)==len(reader.pages)
        with Image.open(pngs[i-1]) as png:
            mask = png.convert("L").point(lambda v:255 if v<180 else 0)
            bounds = mask.getbbox()
            assert bounds and bounds[0]>25 and bounds[1]>25 and bounds[2]<png.width-24 and bounds[3]<png.height-24
        logs.append({"page":i,"text_characters":len(cleaned),"fonts":names,"raster_bbox_px":bounds})
        text_pages.append(cleaned)
    if paper:
        all_text = "".join(text_pages)
        assert all(section in all_text for section in ("Teamreviewcopy","References",
                                    "SensitivityAnalysis","StrengthsandWeaknesses","AIUsageDisclosure"))
        assert "[FILL" not in all_text
        numbers=read_csv(path.parent/"NUMBER_PROVENANCE.csv")
        linked = [r for r in numbers if not r["macro"].startswith(("From","To","At","Branch"))]
        omitted = [r["macro"] for r in linked if r["rendered"] not in all_text]
        assert not omitted, ("Review evidence absent from typeset paper",omitted)
    texlog=path.with_suffix(".log").read_text(encoding="utf-8",errors="replace")
    assert not re.search(r"Overfull \\[hv]box|Missing character:|LaTeX Warning: (?:Reference|Citation).*undefined",
                         texlog), f"Formatting report requires attention for {path.name}"
    return {"file":path.name,"page_count":len(reader.pages),"pages":logs}


def generate(root,bundle):
    source=metrics(root)
    output=root/"paper"
    qa=root/"qa"
    paper=inspect_pdf(compile_tex(output/"B_submission.tex",bundle),qa)
    p1=inspect_pdf(compile_tex(output/"P1_ERRATA.tex",bundle),qa,paper=False)
    # The errata tables are also tied to the generated values.
    errata_text="".join(re.sub(r"\s+","",p.extract_text() or "")
                        for p in PdfReader(output/"P1_ERRATA.pdf").pages)
    assert all(r["rendered"] in errata_text for r in source
               if r["macro"].startswith(("From","To","At","Branch")))
    write_json(qa/"PDF_CHECKS.json",{"paper":paper,"p1_errata":p1,"bound_numbers":len(source)})
    print(f"Paper {paper['page_count']} pages; P1 errata {p1['page_count']} pages; {len(source)} bound metrics")


if __name__=="__main__":
    parser=ArgumentParser(description=__doc__)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument("--bundle",type=Path)
    options=parser.parse_args()
    generate(options.out,options.bundle)

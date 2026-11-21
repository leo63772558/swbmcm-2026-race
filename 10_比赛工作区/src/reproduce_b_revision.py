"""Run the ordered B engineering review from a worktree or review archive.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
Public model release date was not verified. Assistance: rerun automation.
"""
from argparse import ArgumentParser
from hashlib import sha256
from pathlib import Path
from shutil import copyfile, copytree, which
import subprocess
from time import perf_counter

from pypdf import PdfReader

import b_hardcore_audit
import b_revision_correctness
import b_revision_experiments
import b_revision_figures
import b_revision_p4_extended
import b_revision_paper
import b_revision_replay
import b_revision_sensitivity_pareto
import b_revision_validation
from b_revision_data import DEFAULT_OUTPUT, file_hash, read_json, write_json
from problem_b_geometry import ROOT


def content_hash(path):
    """Use the repository's LF convention for generated CSVs across checkouts."""
    if path.suffix.lower() in (".csv", ".json", ".html", ".txt"):
        return sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    return file_hash(path)


def compare(reference, rerun, tex):
    matched = []
    expected = [
        *sorted((reference/"results").glob("*")),
        *sorted((reference/"figures").glob("fig[0-9][0-9]_*")),
        *sorted((reference/"figures"/"replay_frames").rglob("*")),
        reference/"figures"/"FIGURE_SOURCES.csv",
        reference/"figures"/"P4_PANEL_INDEX.csv",
        reference/"simulator"/"B_Simulator.html",
        reference/"simulator"/"KEYFRAME_STATES.json",
    ]
    for old in expected:
        if not old.is_file():
            continue
        rel = old.relative_to(reference)
        new = rerun/rel
        assert new.is_file() and content_hash(old)==content_hash(new), f"Reproduced file differs: {rel}"
        matched.append(rel.as_posix())
    text_matches=[]
    if tex:
        for name in ("B_submission.pdf","P1_ERRATA.pdf"):
            old=PdfReader(reference/"paper"/name)
            new=PdfReader(rerun/"paper"/name)
            assert [p.extract_text() for p in old.pages] == [p.extract_text() for p in new.pages]
            text_matches.append(name)
    return matched,text_matches


def main(out, reference, bundle):
    out=out.resolve()
    reference=reference.resolve()
    if out.exists() or out.is_relative_to(ROOT/"data") or out.is_relative_to(ROOT/"results"):
        raise ValueError("Choose a fresh directory outside the source data and baseline results.")
    out.mkdir(parents=True)
    results=out/"results"
    times={}
    for name,stage in (("1_correctness",b_revision_correctness.main),
                       ("2_validation",b_revision_validation.main),
                       ("3_experiments",b_revision_experiments.main),
                       ("3b_sensitivity_pareto",b_revision_sensitivity_pareto.main),
                       ("3c_p4_extended",b_revision_p4_extended.main)):
        tick=perf_counter()
        stage(results)
        times[name]=round(perf_counter()-tick,3)
    tick=perf_counter()
    assets=reference/"simulator"/"assets"
    b_revision_replay.generate(out,assets/b_revision_replay.ASSET,assets/"PLOTLY_LICENSE.txt")
    captures_src = reference/"figures"/"replay_frames"/"browser_captures"
    if captures_src.is_dir():
        copytree(captures_src, out/"figures"/"replay_frames"/"browser_captures", dirs_exist_ok=True)
    b_revision_figures.generate(out)
    node=which("node")
    if not node:
        raise RuntimeError("Node.js required for replay consistency check")
    subprocess.run([node,str(ROOT/"src"/"b_replay_check.cjs"),str(out/"simulator"/"B_Simulator.html")],check=True)
    times["4_visuals"]=round(perf_counter()-tick,3)
    compile_pdf = bool(bundle) or bool(which("xelatex"))
    if compile_pdf:
        tick=perf_counter()
        dest=out/"paper"
        dest.mkdir()
        for file in ("B_submission.tex","P1_ERRATA.tex"):
            copyfile(reference/"paper"/file,dest/file)
        team_src = reference/"paper"/"team"
        if team_src.is_dir():
            copytree(team_src, dest/"team", dirs_exist_ok=True)
        b_revision_paper.generate(out,bundle)
        b_hardcore_audit.main(out)
        times["5_pdf"]=round(perf_counter()-tick,3)
    matches,text_matches=compare(reference,out,compile_pdf)
    qa={"byte_matches":len(matches),"matched_artifacts":matches,"pdf_text_matches":text_matches,
        "wall_seconds":times,"plan_id":read_json(results/"priority_3.json")["nominal_plan_id"]}
    write_json(out/"REPRODUCTION_CHECK.json",qa)
    print("Review archive reproduced:",len(matches),"byte matches and",len(text_matches),"PDF content matches.")


if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=ROOT/"_b_rerun")
    p.add_argument("--reference",type=Path,default=ROOT/"artifacts" if (ROOT/"artifacts").is_dir() else DEFAULT_OUTPUT)
    p.add_argument("--tex-bundle",type=Path)
    args=p.parse_args()
    main(args.out,args.reference,args.tex_bundle)

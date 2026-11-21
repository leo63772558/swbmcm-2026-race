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
import b_revision_corner_routes
import b_revision_correctness
import b_revision_experiments
import b_revision_figures
import b_revision_p4_extended
import b_revision_p2_tradeoffs
import b_revision_paper
import b_revision_replay
import b_revision_sensitivity_pareto
import b_revision_validation
from b_revision_data import DEFAULT_OUTPUT, file_hash, read_json, write_json
from problem_b_geometry import ROOT


MANIFEST_NAME = "REPRODUCIBILITY_MANIFEST.json"
FIGURES = (
    "framework", "p1_geometry", "p2_precision", "p2_paths", "p2_dispatch",
    "p3_risk", "p4_resilience", "v5_timeline", "global_sensitivity", "pareto_3d",
    "3d_dashboard",
)
KEYFRAMES = ("normal_coordination", "v5_fault_trigger", "v5_recovery_compare")
CAPTURE_STEMS = (
    "1_nominal_beam", "2_failure_V5_keep", "3_failure_V5_reschedule",
    "4_failure_V5_keep_at_recovery",
)
FROZEN_INPUTS = tuple(
    f"figures/replay_frames/browser_captures/{renderer}_{stem}.png"
    for renderer in ("webgl", "canvas") for stem in CAPTURE_STEMS
) + (
    f"simulator/assets/{b_revision_replay.ASSET}",
    "simulator/assets/PLOTLY_LICENSE.txt",
)
PDF_NAMES = ("paper/B_submission.pdf", "paper/P1_ERRATA.pdf")
BASE_ARTIFACTS = (
    "figures/FIGURE_SOURCES.csv",
    "figures/P4_PANEL_INDEX.csv",
    "figures/replay_frames/KEYFRAME_SOURCES.csv",
    "paper/B_review_metrics.tex",
    "paper/B_review_tables.tex",
    "paper/NUMBER_PROVENANCE.csv",
    "simulator/B_Simulator.html",
    "simulator/KEYFRAME_STATES.json",
    "simulator/assets/PLOTLY_SOURCE.txt",
) + tuple(
    f"figures/fig{number:02d}_{stem}.{suffix}"
    for number, stem in enumerate(FIGURES, 1) for suffix in ("pdf", "png")
) + tuple(
    f"figures/replay_frames/{stem}.{suffix}"
    for stem in KEYFRAMES for suffix in ("pdf", "png")
)


def required_hash(root, rel):
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(f"Missing mandatory artifact: {path}")
    return file_hash(path)


def result_paths(root):
    paths = sorted(path.relative_to(root).as_posix() for path in (root / "results").iterdir())
    if not paths:
        raise ValueError(f"No mandatory results in {root / 'results'}")
    return paths


def pdf_text_hashes(path):
    return [
        sha256((page.extract_text() or "").encode("utf-8")).hexdigest()
        for page in PdfReader(path).pages
    ]


def verify_pdf_text(root, rel, expected, label):
    actual = pdf_text_hashes(root / rel)
    if len(actual) != len(expected):
        raise ValueError(f"{label} PDF page count differs: {rel} ({len(actual)} versus {len(expected)})")
    different_pages = [
        str(i) for i, (a, b) in enumerate(zip(actual, expected, strict=True), 1) if a != b
    ]
    if different_pages:
        raise ValueError(f"{label} PDF text differs: {rel}, pages {', '.join(different_pages)}")


def build_manifest(root):
    manifest = {
        "artifacts_sha256": {
            rel: required_hash(root, rel) for rel in [*result_paths(root), *BASE_ARTIFACTS]
        },
        "frozen_inputs_sha256": {rel: required_hash(root, rel) for rel in FROZEN_INPUTS},
        "paper_files": {
            rel: {"sha256": required_hash(root, rel), "page_text_sha256": pdf_text_hashes(root / rel)}
            for rel in PDF_NAMES
        },
    }
    write_json(root / MANIFEST_NAME, manifest)
    return manifest


def load_manifest(reference):
    manifest = read_json(reference / MANIFEST_NAME)
    expected_keys = {
        "artifacts_sha256": set(result_paths(reference)) | set(BASE_ARTIFACTS),
        "frozen_inputs_sha256": set(FROZEN_INPUTS),
        "paper_files": set(PDF_NAMES),
    }
    for group, expected in expected_keys.items():
        actual = set(manifest[group])
        if actual != expected:
            raise ValueError(f"{group}: missing {sorted(expected - actual)}; unexpected {sorted(actual - expected)}")
        for rel, record in manifest[group].items():
            expected_hash = record["sha256"] if group == "paper_files" else record
            if required_hash(reference, rel) != expected_hash:
                raise ValueError(f"Reference SHA-256 differs: {rel}")
            if group == "paper_files":
                verify_pdf_text(reference, rel, record["page_text_sha256"], "Reference")
    return manifest


def compare(rerun, manifest):
    artifacts = manifest["artifacts_sha256"]
    papers = manifest["paper_files"]
    expected_hashes = {**artifacts, **{rel: record["sha256"] for rel, record in papers.items()}}
    expected_results = {rel for rel in artifacts if rel.startswith("results/")}
    actual_results = {
        path.relative_to(rerun).as_posix() for path in (rerun / "results").iterdir()
    } if (rerun / "results").is_dir() else set()
    unexpected = sorted(actual_results - expected_results)
    missing, different = [], []
    for rel, expected_hash in sorted(expected_hashes.items()):
        path = rerun / rel
        if not path.is_file():
            missing.append(rel)
        elif file_hash(path) != expected_hash:
            different.append(rel)
    problems = []
    if missing:
        problems.append(f"Missing mandatory artifacts: {', '.join(missing)}")
    if unexpected:
        problems.append(f"Unexpected reproduced results: {', '.join(unexpected)}")
    if different:
        problems.append(f"Reproduced SHA-256 differs: {', '.join(different)}")
    if problems:
        raise ValueError("\n".join(problems))

    for rel, record in papers.items():
        verify_pdf_text(rerun, rel, record["page_text_sha256"], "Reproduced")
    return sorted(artifacts), sorted(Path(rel).name for rel in papers)


def main(out, reference, bundle):
    out=out.resolve()
    reference=reference.resolve()
    if out.exists() or out.is_relative_to(ROOT/"data") or out.is_relative_to(ROOT/"results"):
        raise ValueError("Choose a fresh directory outside the source data and baseline results.")
    b_revision_paper.tex_engine(bundle)
    if not which("pdftoppm"):
        raise RuntimeError("Poppler pdftoppm is required for PDF layout checks")
    node = which("node")
    if not node:
        raise RuntimeError("Node.js required for replay consistency check")
    manifest = load_manifest(reference)
    out.mkdir(parents=True)
    results=out/"results"
    times={}
    for name,stage in (("1_correctness",b_revision_correctness.main),
                       ("2_validation",b_revision_validation.main),
                       ("3_experiments",b_revision_experiments.main),
                       ("3b_sensitivity_pareto",b_revision_sensitivity_pareto.main),
                       ("3c_p4_extended",b_revision_p4_extended.main),
                       ("3d_corner_routes",b_revision_corner_routes.main),
                       ("3e_dispatch_tradeoffs",b_revision_p2_tradeoffs.main)):
        tick=perf_counter()
        stage(results)
        times[name]=round(perf_counter()-tick,3)
    tick=perf_counter()
    assets=reference/"simulator"/"assets"
    b_revision_replay.generate(out,assets/b_revision_replay.ASSET,assets/"PLOTLY_LICENSE.txt")
    captures_src = reference/"figures"/"replay_frames"/"browser_captures"
    copytree(captures_src, out/"figures"/"replay_frames"/"browser_captures")
    b_revision_figures.generate(out)
    subprocess.run([node,str(ROOT/"src"/"b_replay_check.cjs"),str(out/"simulator"/"B_Simulator.html")],check=True)
    times["4_visuals"]=round(perf_counter()-tick,3)
    tick=perf_counter()
    dest=out/"paper"
    dest.mkdir()
    for file in ("B_submission.tex","P1_ERRATA.tex"):
        copyfile(reference/"paper"/file,dest/file)
    copytree(reference/"paper"/"team", dest/"team")
    b_revision_paper.generate(out,bundle)
    b_hardcore_audit.main(out)
    times["5_pdf"]=round(perf_counter()-tick,3)
    matches, pdf_matches = compare(out, manifest)
    qa = {
        "byte_matches": len(matches),
        "matched_artifacts": matches,
        "pdf_binary_match_count": len(pdf_matches),
        "pdf_binary_matches": pdf_matches,
        "pdf_text_matches": pdf_matches,
        "verified_frozen_inputs": sorted(manifest["frozen_inputs_sha256"]),
        "wall_seconds": times,
        "plan_id": read_json(results / "priority_3.json")["nominal_plan_id"],
    }
    write_json(out / "REPRODUCTION_CHECK.json", qa)
    print(f"Review archive reproduced: {len(matches)} artifact SHA-256 matches and "
          f"{len(pdf_matches)} PDF SHA-256 and per-page text matches.")



if __name__=="__main__":
    p=ArgumentParser(description=__doc__)
    p.add_argument("--out",type=Path,default=ROOT/"_b_rerun")
    p.add_argument("--reference",type=Path,default=ROOT/"artifacts" if (ROOT/"artifacts").is_dir() else DEFAULT_OUTPUT)
    p.add_argument("--tex-bundle",type=Path)
    args=p.parse_args()
    main(args.out,args.reference,args.tex_bundle)

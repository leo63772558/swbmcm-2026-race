"""Build and independently check the anonymous B engineering review archives.

AI assistance: ChatGPT (Codex, GPT-6.2 Sol), OpenAI, used 2026-11-21.
This workflow packages existing data and does not alter numerical evidence.
"""
from argparse import ArgumentParser
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from shutil import copyfile
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import re
import subprocess
import sys

from pypdf import PdfReader

from b_revision_data import DEFAULT_OUTPUT, file_hash, read_json, write_json
from problem_b_geometry import ROOT


BASELINE = "9c2fef86ae38a5b6b472c7750d2451faf9df5d27"
STEM = "BSWBMCM2613050"
LIMIT = 20_000_000
BEIJING = timezone(timedelta(hours=8))
SOURCE_NAMES = (
    "problem_b_geometry.py", "solve_problem_b.py", "check_problem_b.py",
    "check_b_p4_cross.py", "reproduce_b_revision.py",
    "package_b_revision.py",
)
REFERENCE_NAMES = (
    "B_P1.csv", "B_P2_localization.csv", "B_P2_fairness.csv", "B_P3.csv", "B_P4.csv",
)
DOCUMENTS = (
    "TEAM_HANDOFF_CHECKLIST.md", "VERIFY_REPORT.md", "IMPROVEMENT_BACKLOG.md",
    "REPRODUCE.md", "AI_USAGE_LOG.csv", "requirements-review.txt",
)
PRIVATE_PATH = re.compile(r"cns|signed|签名|参赛信息|payment|\.library-transfer", re.IGNORECASE)


def file_manifest(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), "Duplicate archive entries"
        for name in names:
            member = PurePosixPath(name)
            assert member.parts and not (member.is_absolute() or ".." in member.parts
                                         or "\\" in name or ":" in member.parts[0]), name
            assert not PRIVATE_PATH.search(name), name
        assert archive.testzip() is None
        return {name: sha256(archive.read(name)).hexdigest() for name in names}


def write_zip(path, entries):
    with ZipFile(path, "x") as archive:
        for name, source in sorted(entries.items()):
            member = ZipInfo(name, (2026, 11, 21, 0, 0, 0))
            archive.writestr(member, source.read_bytes(), compress_type=ZIP_DEFLATED, compresslevel=8)
    assert path.stat().st_size < LIMIT, f"{path.name} exceeds {LIMIT:,} bytes"
    return file_manifest(path)


def support_entries(review):
    entries = {
        **{path.relative_to(ROOT).as_posix(): path
           for path in (ROOT / "data").glob("B题题面*") if path.is_file()},
        **{f"results/{name}": ROOT / "results" / name for name in REFERENCE_NAMES},
        **{f"src/{name}": ROOT / "src" / name for name in SOURCE_NAMES},
        **{f"src/{path.name}": path for pattern in ("b_revision_*.py", "b_replay*")
           for path in (ROOT / "src").glob(pattern) if path.is_file()},
        **{name: review / name for name in DOCUMENTS},
    }
    figure_dir = review / "figures"
    paper_dir = review / "paper"
    files = [
        *(review / "results").glob("*"),
        *figure_dir.glob("fig[0-9][0-9]_*"),
        *figure_dir.glob("FIGURE_SOURCES.csv"),
        *figure_dir.glob("P4_PANEL_INDEX.csv"),
        *(figure_dir / "replay_frames").rglob("*"),
        *(review / "simulator").rglob("*"),
        *(path for path in paper_dir.rglob("*") if path.suffix in (".tex", ".pdf", ".bib", ".md", ".csv")),
        *(path for path in (review / "qa").glob("*.json") if path.name != "REPRODUCTION_CHECK.json"),
    ]
    entries.update({f"artifacts/{path.relative_to(review).as_posix()}": path
                    for path in files if path.is_file()})
    assert len(list(figure_dir.glob("fig[0-9][0-9]_*.pdf"))) == 10
    assert len(list(figure_dir.glob("fig[0-9][0-9]_*.png"))) == 10
    assert (review / "qa" / "SIMULATOR_CHECKS.json").is_file()
    return entries


def inspect_paper(path):
    paper = PdfReader(path)
    assert not (paper.metadata and paper.metadata.author) and not paper.attachments
    assert 2 < len(paper.pages) <= 25
    page_one = re.sub(r"\s+", "", paper.pages[0].extract_text() or "")
    assert "Summary" in page_one and "Keywords" in page_one
    assert path.stat().st_size < LIMIT
    return {"file": "paper/B_submission.pdf", "pages": len(paper.pages),
            "bytes": path.stat().st_size, "sha256": file_hash(path),
            "empty_author_metadata": True, "attachments": 0,
            "in_requested_page_range": 14 <= len(paper.pages) <= 25}


def inspect_replay(review):
    evidence = read_json(review / "qa" / "SIMULATOR_CHECKS.json")
    simulator = review / "simulator" / "B_Simulator.html"
    assert evidence["html_sha256"] == file_hash(simulator)
    assert evidence["standalone_file_only"] and evidence["browser_context_offline"]
    renderers = {run["renderer"]: run for run in evidence["runs"]}
    assert set(renderers) == {"webgl", "canvas"}
    assert renderers["webgl"]["forced_context_loss_fallback"]
    for run in renderers.values():
        assert run["remote_requests"] == run["page_errors"] == 0
        assert set(run["camera_controls"]) == {"top", "follow", "iso"}
        assert len(run["screenshots"]) == 3
        assert run["route_footprint_check"]["buildingHits"] == 0
        assert run["route_footprint_check"]["pointHits"] == 0


def build(review, bundle=None):
    review = review.resolve()
    bundle = bundle.resolve(strict=True) if bundle else None
    paper = review / "paper" / "B_submission.pdf"
    paper_info = inspect_paper(paper)
    inspect_replay(review)
    dependencies = ("matplotlib", "numpy", "pypdf", "Pillow")
    (review / "requirements-review.txt").write_text(
        "\n".join(f"{name}=={version(name)}" for name in dependencies) + "\n", encoding="utf-8"
    )
    with TemporaryDirectory(prefix=".swb-b-review-", dir=review.parent) as folder:
        temp = Path(folder)
        payload = support_entries(review)
        seed = temp / "staged.zip"
        write_zip(seed, payload)
        extracted = temp / "clean"
        with ZipFile(seed) as archive:
            archive.extractall(extracted)
        rerun = temp / "rerun"
        cmd = [sys.executable, "-B", str(extracted / "src" / "reproduce_b_revision.py"), "--out", str(rerun)]
        if bundle:
            cmd.extend(["--tex-bundle", str(bundle)])
        subprocess.run(cmd, cwd=extracted, check=True)
        proof = rerun / "REPRODUCTION_CHECK.json"
        results = read_json(proof)
        assert len(results["pdf_text_matches"]) == 2
        upload = temp / (STEM + "fj.zip")
        manifest = write_zip(upload, {**payload, "qa/REPRODUCTION_CHECK.json": proof})
        acceptance = temp / "RELEASE_ACCEPTANCE.json"
        write_json(acceptance, {
            "status": "team_review_edition",
            "submission_authorized": False,
            "baseline_commit": BASELINE,
            "checked_at_beijing": datetime.now(BEIJING).isoformat(),
            "content_lock_beijing": "2026-11-24T09:00:00+08:00",
            "submission_deadline_beijing": "2026-11-24T10:00:00+08:00",
            "paper": paper_info,
            "support": {"filename": upload.name, "bytes": upload.stat().st_size,
                        "sha256": file_hash(upload), "member_count": len(manifest),
                        "crc_passed": True, "member_sha256": manifest},
            "reproduction": results,
        })
        engineering = temp / "SWB_2026_B_Engineering_Review.zip"
        write_zip(engineering, {
            "B_submission_review.pdf": paper,
            "P1_ERRATA.pdf": review / "paper" / "P1_ERRATA.pdf",
            **{name: review / name for name in DOCUMENTS},
            acceptance.name: acceptance,
            upload.name: upload,
        })
        copyfile(proof, review / "qa" / proof.name)
        for path in (upload, acceptance, engineering):
            copyfile(path, review / path.name)
        print(f"{upload.name}: {len(manifest)} files, {upload.stat().st_size:,} bytes")
        print(f"{engineering.name}: {engineering.stat().st_size:,} bytes")
        print(f"Reviewed paper: {paper_info['pages']} A4 pages")


if __name__ == "__main__":
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bundle", type=Path, default=None)
    arguments = parser.parse_args()
    build(arguments.review, arguments.bundle)

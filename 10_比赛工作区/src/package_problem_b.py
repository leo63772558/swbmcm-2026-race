"""Stage the B paper and its matching support ZIP in a separate directory.

OpenAI Codex (GPT-6 series) assisted with the packaging checks.
"""

from argparse import ArgumentParser
from pathlib import Path, PurePosixPath, PureWindowsPath
from shutil import copyfile
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile

from pypdf import PdfReader
from pypdf.errors import PdfReadError


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
TEAM = "SWBMCM2613050"
STEM = "B" + TEAM
MAX_BYTES = 20_000_000
DRAFT_DISCLOSURE = "this version records the ai-produced draft"
PROTOTYPE_RESULTS = (
    "B_P1.csv", "B_P2_localization.csv", "B_P2_schedules.csv", "B_P3.csv",
    "B_P3_coverage.csv", "B_P4.csv", "B_validation.csv", "B_timelines.json",
)
PROTOTYPE_FIGURES = (
    "b_coverage.pdf", "b_disturbances.pdf", "b_geometry.pdf", "b_parameters.pdf",
    "b_routes.pdf", "b_timeline.pdf",
)
PROTOTYPE_PREVIEWS = (
    *(name.removesuffix(".pdf") + ".png" for name in PROTOTYPE_FIGURES),
    "B_figure_overview.png",
)
PROTOTYPE_AUDITS = (
    ("check_b_p2_fairness.py", ("B_P2_fairness.csv",)),
    ("check_b_p3_margin.py", ("B_P3_margin.csv",)),
    ("check_b_p4_cross.py", ("B_P4_cross.csv", "B_P4_cross_timelines.json")),
    ("check_b_p4_replay.py", ("B_P4_replay.csv",)),
)


def check_size(path):
    if not 0 < path.stat().st_size < MAX_BYTES:
        raise ValueError(f"File must be nonempty and smaller than 20 MB: {path.name}")


def create_prototype_archive(path):
    entries = [
        ROOT / "data" / "B题题面参数.csv",
        *(ROOT / "paper" / name for name in ("B_prototype.tex", "main.tex", "B_reproduce.md")),
        *(ROOT / "results" / name for name in PROTOTYPE_RESULTS),
        *(ROOT / "figures" / name for name in (*PROTOTYPE_FIGURES, *PROTOTYPE_PREVIEWS)),
        *(ROOT / "src" / name for name in (
            "problem_b_geometry.py", "solve_problem_b.py", "check_problem_b.py",
            "plot_problem_b.py", "render_problem_b.py", "package_problem_b.py", "verify_handoff.py",
        )),
        *(ROOT / "src" / script for script, _ in PROTOTYPE_AUDITS),
        *(ROOT / "results" / name for _, results in PROTOTYPE_AUDITS for name in results),
    ]
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            archive.write(entry, entry.relative_to(ROOT).as_posix())


def verify_archive(path, *, prototype):
    check_size(path)
    with ZipFile(path) as archive:
        files = set()
        for entry in archive.infolist():
            name = entry.orig_filename
            windows_path = PureWindowsPath(name)
            relative_path = PurePosixPath(name.replace("\\", "/"))
            if (
                "\x00" in name or windows_path.anchor or relative_path.is_absolute()
                or ".." in relative_path.parts
                or stat.S_ISLNK(entry.external_attr >> 16)
            ):
                raise ValueError(f"Unsafe ZIP entry: {name!r}")
            leaf = relative_path.name.casefold()
            if leaf.startswith(STEM.casefold() + "cns") or "承诺书" in leaf:
                raise ValueError("The commitment form must be kept outside the support ZIP.")
            if not prototype and leaf in {"b_prototype.tex", "b_prototype.pdf", "b_prototype_preview.pdf"}:
                raise ValueError("The support ZIP contains a prototype manuscript.")
            if not entry.is_dir():
                key = relative_path.as_posix().casefold()
                if key in files:
                    raise ValueError(f"Duplicate ZIP entry: {name!r}")
                files.add(key)
        if not files:
            raise ValueError("The support ZIP contains no files.")
        damaged = archive.testzip()
        if damaged is not None:
            raise ValueError(f"Invalid CRC in ZIP entry: {damaged!r}")


def verify_manuscript(path, *, prototype):
    check_size(path)
    with path.open("rb") as file:
        pdf = PdfReader(file)
        if pdf.is_encrypted or len(pdf.pages) < 3:
            raise ValueError("Expected an unencrypted manuscript with cover, contents and main text.")
        if pdf.metadata is not None and (pdf.metadata.author or "").strip():
            raise ValueError("Clear the PDF's Author metadata.")
        if len(pdf.attachments):
            raise ValueError("Keep embedded files outside the manuscript PDF.")
        page_texts = [page.extract_text() or "" for page in pdf.pages]
    if "Summary" not in page_texts[0] or "Content" not in page_texts[1]:
        raise ValueError("Expected a Summary cover and separate Content page.")
    report_pages = [" ".join(text.split()) for text in page_texts[2:]]
    if not any("AI Tool Usage Report" in text for text in report_pages):
        raise ValueError("The manuscript is missing the AI Tool Usage Report.")
    if not prototype and any(DRAFT_DISCLOSURE in text.casefold() for text in report_pages):
        raise ValueError("The manuscript identifies itself as the AI-produced prototype.")


def run_pdf_qa(path, report_dir, counted_pages):
    checker = ROOT.parent / "11_质量检查" / "scripts" / "pdf_qa.py"
    if not checker.is_file():
        checker = ROOT.parent / "03_code" / "tests" / "pdf_qa.py"
    command = [
        sys.executable, str(checker), "--pdf", str(path), "--team", TEAM, "--letter", "B",
        "--strict", "--out", str(report_dir),
    ]
    if counted_pages is not None:
        command.extend(("--counted-pages", str(counted_pages)))
    if subprocess.run(command).returncode:
        report_path = report_dir / "PDF_QA_REPORT.md"
        if report_path.is_file():
            print(report_path.read_text(encoding="utf-8"), file=sys.stderr)
        raise ValueError("The manuscript did not pass strict PDF QA.")


def stage(paper, support, output, *, prototype, counted_pages):
    if output.exists() or output.is_symlink():
        raise ValueError(f"Choose a new output directory: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".b-paper-", dir=output.parent) as tmp:
        scratch = Path(tmp)
        candidate = scratch / "candidate"
        candidate.mkdir()
        staged_paper = candidate / f"{STEM}.pdf"
        staged_archive = candidate / f"{STEM}fj.zip"
        check_size(paper)
        copyfile(paper, staged_paper)
        verify_manuscript(staged_paper, prototype=prototype)
        if prototype:
            create_prototype_archive(staged_archive)
        else:
            check_size(support)
            copyfile(support, staged_archive)
        verify_archive(staged_archive, prototype=prototype)
        if not prototype:
            run_pdf_qa(staged_paper, scratch / "qa", counted_pages)
        candidate.rename(output)


def main():
    parser = ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--paper", type=Path, help="Compiled team manuscript PDF")
    mode.add_argument("--prototype", action="store_true", help="Reproduce the internal work package")
    parser.add_argument("--support", type=Path, help="Matching team support ZIP")
    parser.add_argument("--out", type=Path, help="New staging directory")
    parser.add_argument("--counted-pages", type=int, help="Last physical page counted toward the 25-page limit")
    args = parser.parse_args()
    if args.prototype and (args.support is not None or args.counted_pages is not None):
        parser.error("--support and --counted-pages are available with --paper.")
    if not args.prototype and args.support is None:
        parser.error("--paper requires --support from the same revision.")
    paper = args.paper or ROOT / "paper" / "B_prototype.pdf"
    output = args.out or SUBMISSION / ("prototype" if args.prototype else "final")
    try:
        stage(paper, args.support, output, prototype=args.prototype, counted_pages=args.counted_pages)
    except (OSError, ValueError, BadZipFile, PdfReadError, RuntimeError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Staged {'the internal work package' if args.prototype else 'the checked PDF and ZIP'} in {output}")


if __name__ == "__main__":
    main()

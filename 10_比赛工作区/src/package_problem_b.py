"""Stage the draft paper and reproducibility archive for handoff (OpenAI Codex)."""

from argparse import ArgumentParser
from pathlib import Path
from shutil import copyfile
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
TEAM = "SWBMCM2613050"
STEM = "B" + TEAM
MAX_BYTES = 20_000_000


def stage_paper(source):
    pdf = PdfReader(source)
    pages = pdf.pages
    assert 3 <= len(pages) <= 25
    for page in pages:
        assert float(page.mediabox.width) <= 595.29
        assert float(page.mediabox.height) <= 841.90
    for page, required in zip(pages[:2], ("Summary", "Content")):
        assert required in page.extract_text()
    assert f"Team#{TEAM}" not in pages[0].extract_text()
    for index, page in enumerate(pages[1:], 2):
        text = page.extract_text()
        assert f"Team#{TEAM}" in text
        assert f"Page {index} of {len(pages)}" in text
    assert all("[FILL:" not in page.extract_text() for page in pages)
    assert not pdf.attachments
    assert "AI Tool Usage Report" in pages[-1].extract_text()
    assert pdf.metadata is not None and not (pdf.metadata.author or "").strip()
    for page in pages:
        fonts = page["/Resources"]["/Font"]
        times = [reference.get_object() for reference in fonts.values()
                 if "TimesNewRoman" in str(reference.get_object().get("/BaseFont", ""))]
        assert times, "Missing Times New Roman in page resources"
        for font in times:
            descriptor_owner = font["/DescendantFonts"][0].get_object() if "/DescendantFonts" in font else font
            descriptor = descriptor_owner["/FontDescriptor"]
            assert any(kind in descriptor for kind in ("/FontFile", "/FontFile2", "/FontFile3"))
    destination = SUBMISSION / (STEM + ".pdf")
    copyfile(source, destination)
    assert destination.stat().st_size < MAX_BYTES


def stage_archive():
    root_paper = ROOT / "paper"
    entries = [
        ROOT / "data" / "B题题面参数.csv",
        root_paper / "B_prototype.tex",
        root_paper / "main.tex",
        root_paper / "B_reproduce.md",
        ROOT / "results" / "B_timelines.json",
        *sorted((ROOT / "results").glob("B_*.csv")),
        *sorted((ROOT / "figures").glob("b_*.pdf")),
    ]
    entries.extend(ROOT / "src" / name for name in (
        "problem_b_geometry.py", "solve_problem_b.py", "check_problem_b.py",
        "plot_problem_b.py", "render_problem_b.py", "package_problem_b.py", "verify_handoff.py",
    ))
    path = SUBMISSION / (STEM + "fj.zip")
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for entry in entries:
            archive.write(entry, entry.relative_to(ROOT).as_posix())
    with ZipFile(path) as archive:
        assert archive.testzip() is None
        assert len(archive.namelist()) == len(entries)
        assert all("cns" not in name and "signature" not in name.lower()
                   for name in archive.namelist())
    assert path.stat().st_size < MAX_BYTES


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--paper", type=Path, default=ROOT / "paper" / "B_prototype.pdf",
                        help="Path to the compiled manuscript PDF")
    args = parser.parse_args()
    SUBMISSION.mkdir(exist_ok=True)
    stage_paper(args.paper)
    stage_archive()

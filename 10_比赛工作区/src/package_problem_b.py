"""Stage the draft paper and reproducibility archive for handoff (OpenAI Codex)."""

from pathlib import Path
from shutil import copyfile
from zipfile import ZIP_DEFLATED, ZipFile

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
SUBMISSION = ROOT / "submission"
TEAM = "SWBMCM2613050"
STEM = "B" + TEAM
MAX_BYTES = 20_000_000


def stage_paper():
    source = ROOT / "paper" / "B_prototype_preview.pdf"
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
        "render_problem_b.py", "package_problem_b.py",
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
    SUBMISSION.mkdir(exist_ok=True)
    stage_paper()
    stage_archive()

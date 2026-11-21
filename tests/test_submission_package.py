from __future__ import annotations

import csv
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest
from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent
REVIEW_DIR = REPO / "10_比赛工作区" / "submission" / "b_revision_20261121"
PDF_PATH = REVIEW_DIR / "paper" / "B_submission.pdf"
ZIP_PATH = REVIEW_DIR / "BSWBMCM2613050fj.zip"

FORBIDDEN_IDENTITY_TOKENS = [
    "黄俊斌",
    "胡允贤",
    "李丞渊",
    "LEI SENG UN",
    "南京大学",
    "华南理工",
    "华中科技",
]

FORBIDDEN_PAPER_TOKENS = [
    "Drafting Blueprint",
    "Author input pending",
    "[FILL",
    "TODO",
    "Sobol",
    "??",
    "Missing section file",
]


def test_submission_pdf_format_figures_and_anonymity():
    """Verify the 24-page paper, official page structure, and anonymity."""
    assert PDF_PATH.is_file()
    reader = PdfReader(PDF_PATH)
    assert len(reader.pages) == 24
    assert not (reader.metadata and reader.metadata.get("/Author")), "PDF Author metadata must be empty"

    pages_text = [p.extract_text() or "" for p in reader.pages]
    for idx, (page, txt) in enumerate(zip(reader.pages, pages_text, strict=True), start=1):
        assert abs(float(page.mediabox.width) - 595.28) < 1, f"Page {idx} width must be A4"
        assert abs(float(page.mediabox.height) - 841.89) < 1, f"Page {idx} height must be A4"
        assert len(txt.strip()) > 80, f"Page {idx} appears empty or nearly blank"

    header = "Team#BSWBMCM2613050"
    compact_pages = [re.sub(r"\s+", "", page) for page in pages_text]
    assert all(header not in page for page in compact_pages[:2])
    for label in ("Problem Chosen", "2026", "ShuWei Cup", "Summary Sheet", "Team Control Number", "SWBMCM2613050", "Keywords"):
        assert label in " ".join(pages_text[0].split())
    assert "Content" in pages_text[1]
    assert not re.search(r"Station-\s*ing|Admissi-\s*ble", pages_text[1], re.IGNORECASE)
    for number, page in enumerate(compact_pages[2:], start=1):
        assert header in page and f"Page{number}of22" in page

    full_text = "\n".join(pages_text)
    for fig_idx in range(1, 12):
        assert f"Figure {fig_idx}." in full_text, f"Missing Figure {fig_idx}. in B_submission.pdf"
    assert "AI Tool Usage Report" in " ".join(pages_text[-1].split())

    for bad in FORBIDDEN_PAPER_TOKENS:
        assert bad not in full_text, f"Forbidden draft/inaccurate token found in PDF: {bad}"
    for leak in FORBIDDEN_IDENTITY_TOKENS:
        assert leak not in full_text, f"Anonymity violation in B_submission.pdf: {leak}"


def test_ai_usage_logs_strict_11_columns_and_report_exists():
    """All AI_USAGE_LOG CSVs strictly obey 11-column schema with zero personal name leaks; standalone report exists."""
    report = REVIEW_DIR / "AI_Usage_Report.md"
    assert report.is_file()
    report_text = report.read_text(encoding="utf-8")
    assert "SWBMCM2613050" in report_text and len(report_text) > 1000
    for leak in FORBIDDEN_IDENTITY_TOKENS:
        assert leak not in report_text, f"Anonymity violation in AI_Usage_Report.md: {leak}"

    csv_paths = [
        REVIEW_DIR / "AI_USAGE_LOG.csv",
        REPO / "08_ai-log" / "AI_USAGE_LOG.csv",
        REPO / "12_AI使用记录" / "AI_USAGE_LOG_比赛版.csv",
    ]
    for path in csv_paths:
        assert path.is_file(), f"Missing AI log: {path}"
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        assert len(rows) >= 2
        assert len(rows[0]) == 11, f"Header in {path} does not have 11 columns"
        for line_no, row in enumerate(rows[1:], start=2):
            assert len(row) == 11, f"{path} line {line_no} has {len(row)} columns (expected 11): {row}"
            joined = ",".join(row)
            for leak in FORBIDDEN_IDENTITY_TOKENS:
                assert leak not in joined, f"Anonymity violation in {path} line {line_no}: {leak}"


def test_code_readmes_anonymized_and_run_all_fail_fast():
    """03_code READMEs contain zero real names; 03_code/run_all.py --list reports all stages READY."""
    for readme in (REPO / "03_code").rglob("README.md"):
        txt = readme.read_text(encoding="utf-8")
        for leak in FORBIDDEN_IDENTITY_TOKENS:
            assert leak not in txt, f"Anonymity violation in {readme}: {leak}"

    proc = subprocess.run(
        [sys.executable, str(REPO / "03_code" / "run_all.py"), "--list"],
        cwd=str(REPO),
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    assert proc.returncode == 0, f"run_all.py --list failed: {proc.stderr}"
    assert "MISSING" not in proc.stdout
    assert proc.stdout.count("[READY]") == 9


def test_supporting_zip_size_contents_and_full_anonymity_scan():
    """BSWBMCM2613050fj.zip is <20 MB, contains AI_Usage_Report.md, and has zero identity leaks across all members."""
    assert ZIP_PATH.is_file(), f"Missing supporting package: {ZIP_PATH}"
    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    assert size_mb < 20.0, f"ZIP exceeds 20 MB limit: {size_mb:.2f} MB"

    text_exts = {".md", ".txt", ".csv", ".json", ".py", ".tex", ".html", ".cjs", ".js"}
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = set(zf.namelist())
        assert "AI_Usage_Report.md" in names
        assert "AI_USAGE_LOG.csv" in names
        assert "artifacts/paper/B_submission.pdf" in names

        # Verify AI_USAGE_LOG.csv inside ZIP strictly obeys 11-column schema
        import io
        zip_ai_rows = list(csv.reader(io.StringIO(zf.read("AI_USAGE_LOG.csv").decode("utf-8-sig"))))
        assert len(zip_ai_rows) >= 2
        for line_no, row in enumerate(zip_ai_rows, start=1):
            assert len(row) == 11, f"ZIP AI_USAGE_LOG.csv line {line_no} has {len(row)} columns"

        for member in zf.namelist():
            ext = Path(member).suffix.lower()
            if ext in text_exts:
                content = zf.read(member).decode("utf-8", errors="ignore")
                for leak in FORBIDDEN_IDENTITY_TOKENS:
                    assert leak not in content, f"Anonymity leak ({leak}) in ZIP member {member}"
            elif ext == ".pdf":
                import io
                reader = PdfReader(io.BytesIO(zf.read(member)))
                pdf_text = "\n".join((p.extract_text() or "") for p in reader.pages)
                for leak in FORBIDDEN_IDENTITY_TOKENS:
                    assert leak not in pdf_text, f"Anonymity leak ({leak}) in ZIP PDF {member}"


def test_reproduction_manifest_requires_every_artifact(tmp_path, monkeypatch):
    import reproduce_b_revision as reproduce

    reference = tmp_path / "reference"
    rerun = tmp_path / "rerun"
    result = "results/observations.csv"
    for root in (reference, rerun):
        (root / "results").mkdir(parents=True)
        (root / result).write_bytes(b"time\n2.5\n")
    monkeypatch.setattr(reproduce, "BASE_ARTIFACTS", ())
    monkeypatch.setattr(reproduce, "FROZEN_INPUTS", ())
    monkeypatch.setattr(reproduce, "PDF_NAMES", ())
    reproduce.build_manifest(reference)
    manifest = reproduce.load_manifest(reference)
    assert reproduce.compare(rerun, manifest) == ([result], [])

    (rerun / result).write_bytes(b"time\r\n2.5\r\n")
    with pytest.raises(ValueError, match="Reproduced SHA-256 differs"):
        reproduce.compare(rerun, manifest)
    (reference / result).unlink()
    with pytest.raises(ValueError, match="No mandatory results"):
        reproduce.load_manifest(reference)


def test_reproduction_requires_tex_engine(monkeypatch):
    from b_revision_paper import tex_engine

    monkeypatch.setattr("b_revision_paper.which", lambda name: name if name == "tectonic" else None)
    assert tex_engine(None) == ("tectonic", "tectonic")
    monkeypatch.setattr("b_revision_paper.which", lambda name: None)
    with pytest.raises(RuntimeError, match="Neither XeLaTeX nor Tectonic"):
        tex_engine(None)

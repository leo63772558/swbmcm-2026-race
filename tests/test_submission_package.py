# AI Assistance Disclosure (Article 7):
# - Tool: OpenAI ChatGPT (Codex, GPT-5.4 / GPT-6.2 Sol); Google Antigravity (Gemini 3.1 Pro)
# - Scope: Submission package, format, citation-order, and hashed anonymity verification tests
# - Date: 2026-11-21
# - Team Verification: Compliance criteria verified against 2026 ShuWei Cup official rules by Team#SWBMCM2613050.
from __future__ import annotations

import csv
import hashlib
import io
import re
import subprocess
import sys
import zipfile
from pathlib import Path

from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent
REVIEW_DIR = REPO / "10_比赛工作区" / "submission" / "b_revision_20261121"
PDF_PATH = REVIEW_DIR / "paper" / "B_submission.pdf"
ZIP_PATH = REVIEW_DIR / "BSWBMCM2613050fj.zip"
ROOT_PDF = REPO / "10_比赛工作区" / "submission" / "BSWBMCM2613050.pdf"
ROOT_ZIP = REPO / "10_比赛工作区" / "submission" / "BSWBMCM2613050fj.zip"

# Hashed (length, sha256[:20]) identity tokens — zero plaintext personal/school strings in source
FORBIDDEN_IDENTITY_HASHES: dict[int, set[str]] = {
    3: {"1d513e6435bfb82e9502", "a980d03cc6786769e038", "7a29cfdfd68ffb5846e6"},
    4: {"0b7a026f0901b771e10c", "5c1b89f334374fd7a1cc", "e6baba79b1da022f4216"},
    11: {"2b11c894b4bd4dc45dc8"},
}

FORBIDDEN_PAPER_TOKENS = [
    "Drafting Blueprint",
    "Author input pending",
    "[FILL",
    "TODO",
    "Sobol",
]

FORBIDDEN_ZIP_INTERNAL_MEMOS = {
    "TEAM_HANDOFF_CHECKLIST.md",
    "VERIFY_REPORT.md",
    "IMPROVEMENT_BACKLOG.md",
    "FINAL_JUDGE_REVIEW.md",
    "artifacts/paper/B_submission.pdf",
    "artifacts/paper/B_review_tables.tex",
}


def _has_identity_leak(text: str) -> str | None:
    """Scan text against hashed identity tokens without storing plaintext identifiers."""
    n = len(text)
    for length, targets in FORBIDDEN_IDENTITY_HASHES.items():
        if n < length:
            continue
        for i in range(n - length + 1):
            ch = text[i]
            if length == 11 and not ("A" <= ch <= "Z"):
                continue
            if length in (3, 4) and ord(ch) < 0x4E00:
                continue
            sub = text[i : i + length]
            h = hashlib.sha256(sub.encode("utf-8")).hexdigest()[:20]
            if h in targets:
                return f"len={length},hash={h}"
    return None


def test_submission_pdf_format_figures_and_anonymity():
    """B_submission.pdf obeys <=25 main pages A4, Page 1 no header, Page 2 Content, 11 figures, zero leaks."""
    assert PDF_PATH.is_file()
    reader = PdfReader(PDF_PATH)
    total_pages = len(reader.pages)
    assert total_pages >= 3
    assert not (reader.metadata and reader.metadata.get("/Author")), "PDF Author metadata must be empty"
    assert not reader.attachments, "Official rule forbids embedded PDF attachments"

    # Verify every page is A4 (595.28 x 841.89 pt within 1 pt tolerance)
    for idx, page in enumerate(reader.pages, start=1):
        w = float(page.mediabox.width)
        h = float(page.mediabox.height)
        assert abs(w - 595.276) < 1.5 and abs(h - 841.89) < 1.5, f"Page {idx} is not A4 ({w:.1f}x{h:.1f})"

    pages_text = [p.extract_text() or "" for p in reader.pages]
    for idx, txt in enumerate(pages_text, start=1):
        assert len(txt.strip()) > 80, f"Page {idx} appears empty or nearly blank"

    # Locate optional Appendix start (exempt from 25-page main cap per official format & AI rules)
    appendix_idx = next(
        (i for i, txt in enumerate(pages_text) if i >= 2 and re.search(r"Appendix\s+[A-Z]\s*:", txt)),
        None,
    )
    main_pages = total_pages if appendix_idx is None else appendix_idx
    assert 3 <= main_pages <= 25, f"Main body has {main_pages} pages (official limit <= 25)"
    assert appendix_idx is not None, "Expected Appendix A & Appendix B (AI Tool Usage Report) appended"

    assert "Team#SWBMCM2613050" not in pages_text[0], "Page 1 Summary Sheet must not have Team# header"
    assert "Summary" in pages_text[0]
    assert "Content" in pages_text[1]
    for idx in range(1, total_pages):
        assert "Team#SWBMCM2613050" in pages_text[idx], f"Missing Team# header on page {idx + 1}"
        assert f"Page {idx + 1} of {total_pages}" in pages_text[idx], f"Missing dynamic Page N of M on page {idx + 1}"

    full_text = "\n".join(pages_text)
    for fig_idx in range(1, 12):
        assert f"Figure {fig_idx}." in full_text, f"Missing Figure {fig_idx}. in B_submission.pdf"
    assert "Appendix B: AI Tool Usage Report" in full_text

    for bad in FORBIDDEN_PAPER_TOKENS:
        assert bad not in full_text, f"Forbidden draft/inaccurate token found in PDF: {bad}"
    leak = _has_identity_leak(full_text)
    assert leak is None, f"Anonymity violation in B_submission.pdf: {leak}"

    # Verify canonical root submission PDF matches revision PDF byte-for-byte
    assert ROOT_PDF.is_file(), f"Missing canonical root submission PDF: {ROOT_PDF}"
    assert ROOT_PDF.read_bytes() == PDF_PATH.read_bytes(), "Root BSWBMCM2613050.pdf out of sync with B_submission.pdf"


def test_ai_usage_logs_strict_11_columns_and_report_exists():
    """All 3 AI_USAGE_LOG CSVs are unified, strictly 11-column, and zero-leak; standalone report exists."""
    report = REVIEW_DIR / "AI_Usage_Report.md"
    assert report.is_file()
    report_text = report.read_text(encoding="utf-8")
    assert "SWBMCM2613050" in report_text and len(report_text) > 1000
    assert "b_revision_simulator.py" not in report_text, "Stale broken path in AI_Usage_Report.md"
    assert _has_identity_leak(report_text) is None, "Anonymity violation in AI_Usage_Report.md"

    csv_paths = [
        REVIEW_DIR / "AI_USAGE_LOG.csv",
        REPO / "08_ai-log" / "AI_USAGE_LOG.csv",
        REPO / "12_AI使用记录" / "AI_USAGE_LOG_比赛版.csv",
    ]
    normalized_contents = []
    for path in csv_paths:
        assert path.is_file(), f"Missing AI log: {path}"
        raw = path.read_text(encoding="utf-8-sig")
        normalized_contents.append(raw.replace("\r\n", "\n").strip())
        rows = list(csv.reader(io.StringIO(raw)))
        assert len(rows) >= 2
        assert len(rows[0]) == 11, f"Header in {path} does not have 11 columns"
        for line_no, row in enumerate(rows[1:], start=2):
            assert len(row) == 11, f"{path} line {line_no} has {len(row)} columns (expected 11): {row}"
            assert _has_identity_leak(",".join(row)) is None, f"Anonymity violation in {path} line {line_no}"
    assert len(set(normalized_contents)) == 1, "The three AI_USAGE_LOG CSV files are not unified!"


def test_code_readmes_anonymized_and_run_all_fail_fast():
    """03_code READMEs contain zero leaks; 03_code/run_all.py --list reports all 7 stages READY."""
    for readme in (REPO / "03_code").rglob("README.md"):
        txt = readme.read_text(encoding="utf-8")
        assert _has_identity_leak(txt) is None, f"Anonymity violation in {readme}"

    proc = subprocess.run(
        [sys.executable, str(REPO / "03_code" / "run_all.py"), "--list"],
        cwd=str(REPO),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"run_all.py --list failed: {proc.stderr}"
    assert "MISSING" not in proc.stdout
    assert proc.stdout.count("[READY]") == 7


def test_supporting_zip_size_contents_and_full_anonymity_scan():
    """BSWBMCM2613050fj.zip is <20 MB, excludes internal memos/duplicate PDF, and has zero identity leaks."""
    assert ZIP_PATH.is_file(), f"Missing supporting package: {ZIP_PATH}"
    assert ROOT_ZIP.is_file(), f"Missing canonical root ZIP: {ROOT_ZIP}"
    assert ROOT_ZIP.read_bytes() == ZIP_PATH.read_bytes(), "Root BSWBMCM2613050fj.zip out of sync"

    size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
    assert size_mb < 20.0, f"ZIP exceeds 20 MB limit: {size_mb:.2f} MB"

    text_exts = {".md", ".txt", ".csv", ".json", ".py", ".tex", ".html", ".cjs", ".js"}
    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = set(zf.namelist())
        assert "AI_Usage_Report.md" in names
        assert "AI_USAGE_LOG.csv" in names
        assert "REPRODUCE.md" in names
        assert "artifacts/simulator/B_Simulator.html" in names
        for forbidden in FORBIDDEN_ZIP_INTERNAL_MEMOS:
            assert forbidden not in names, f"Internal handoff/duplicate file leaked into official ZIP: {forbidden}"
        assert not any("B题题面-全文" in n for n in names), "Raw problem text should not be in official ZIP"

        # Verify AI_USAGE_LOG.csv inside ZIP strictly obeys 11-column schema
        zip_ai_rows = list(csv.reader(io.StringIO(zf.read("AI_USAGE_LOG.csv").decode("utf-8-sig"))))
        assert len(zip_ai_rows) >= 2
        for line_no, row in enumerate(zip_ai_rows, start=1):
            assert len(row) == 11, f"ZIP AI_USAGE_LOG.csv line {line_no} has {len(row)} columns"

        for member in zf.namelist():
            ext = Path(member).suffix.lower()
            if ext in text_exts:
                content = zf.read(member).decode("utf-8", errors="ignore")
                leak = _has_identity_leak(content)
                assert leak is None, f"Anonymity leak ({leak}) in ZIP member {member}"
            elif ext == ".pdf":
                reader = PdfReader(io.BytesIO(zf.read(member)))
                pdf_text = "\n".join((p.extract_text() or "") for p in reader.pages)
                leak = _has_identity_leak(pdf_text)
                assert leak is None, f"Anonymity leak ({leak}) in ZIP PDF {member}"

from __future__ import annotations

import csv
import io
import json
import os
import re
import subprocess
import sys
import zipfile
from hashlib import sha256
from pathlib import Path, PurePosixPath

import pytest
from pypdf import PdfReader

REPO = Path(__file__).resolve().parent.parent
REVIEW_DIR = REPO / "10_比赛工作区" / "submission" / "b_revision_20261121"
PDF_PATH = REVIEW_DIR / "paper" / "B_submission.pdf"
ZIP_PATH = REVIEW_DIR / "BSWBMCM2613050fj.zip"
MANIFEST_NAME = "REPRODUCIBILITY_MANIFEST.json"
PROOF_NAME = "qa/REPRODUCTION_CHECK.json"
ABSOLUTE_PERSONAL_PATH = re.compile(
    r"\b[a-z]:[/\\]+(?:users|workbuddy|codex)[/\\]+|/(?:users|home)/[\w.-]+/",
    re.IGNORECASE,
)

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
    for number, page in enumerate(compact_pages[2:], start=3):
        assert header in page and f"Page{number}of24" in page

    full_text = "\n".join(pages_text)
    for fig_idx in range(1, 12):
        assert f"Figure {fig_idx}." in full_text, f"Missing Figure {fig_idx}. in B_submission.pdf"
    assert "AI Tool Usage Report" in " ".join(pages_text[-1].split())
    assert "python 03_code/run_all.py" in " ".join(full_text.split())
    assert not ABSOLUTE_PERSONAL_PATH.search(full_text)
    assert not re.search(r"[\u3400-\u9fff]", full_text)

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

    _check_run_all_listing(REPO)


def _check_run_all_listing(root):
    proc = subprocess.run(
        [sys.executable, "-B", str(root / "03_code" / "run_all.py"), "--list"],
        cwd=root,
        capture_output=True,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, f"run_all.py --list failed: {proc.stderr}"
    assert "MISSING" not in proc.stdout
    assert proc.stdout.count("[READY]") == 9


def test_supporting_zip_contents_hashes_and_full_anonymity_scan(tmp_path):
    """Check the sealed ZIP, its manifest, and the extracted entry point."""
    assert ZIP_PATH.is_file(), f"Missing supporting package: {ZIP_PATH}"
    size = ZIP_PATH.stat().st_size
    assert size < 20_000_000, f"ZIP exceeds the size limit: {size:,} bytes"

    acceptance = json.loads((REVIEW_DIR / "RELEASE_ACCEPTANCE.json").read_text(encoding="utf-8"))
    support = acceptance["support"]
    assert support["filename"] == ZIP_PATH.name
    assert support["bytes"] == size
    assert support["sha256"] == sha256(ZIP_PATH.read_bytes()).hexdigest()
    assert support["crc_passed"] is True
    text_exts = {".md", ".txt", ".csv", ".json", ".py", ".tex", ".bib", ".html", ".cjs", ".js"}
    with zipfile.ZipFile(ZIP_PATH) as zf:
        entries = zf.namelist()
        names = set(entries)
        assert len(entries) == len(names) == support["member_count"]
        assert {
            "03_code/run_all.py", "requirements.txt", "AI_Usage_Report.md", "AI_USAGE_LOG.csv",
            f"artifacts/{MANIFEST_NAME}", "artifacts/paper/B_submission.pdf",
        } <= names
        assert PROOF_NAME not in names, "Seal the support ZIP before recording the clean-room proof"
        for member in ("AI_Usage_Report.md", "AI_USAGE_LOG.csv"):
            assert zf.read(member) == (REVIEW_DIR / member).read_bytes()
        ledger_rows = list(csv.reader(io.StringIO(zf.read("AI_USAGE_LOG.csv").decode("utf-8-sig"))))
        assert len(ledger_rows) >= 2 and all(len(row) == 11 for row in ledger_rows)
        manifest_bytes = zf.read(f"artifacts/{MANIFEST_NAME}")
        assert manifest_bytes == (REVIEW_DIR / MANIFEST_NAME).read_bytes()
        manifest = json.loads(manifest_bytes)
        assert zf.read("artifacts/paper/B_submission.pdf") == PDF_PATH.read_bytes()

        hashes = {}
        for member in entries:
            path = PurePosixPath(member)
            assert path.parts and not path.is_absolute() and ".." not in path.parts
            assert "\\" not in member and ":" not in path.parts[0]
            assert all(leak not in member for leak in FORBIDDEN_IDENTITY_TOKENS)
            # ZipFile.read verifies the member CRC while retrieving the hash input.
            data = zf.read(member)
            hashes[member] = sha256(data).hexdigest()
            ext = Path(member).suffix.lower()
            if ext in text_exts:
                content = data.decode("utf-8-sig", errors="ignore")
            elif ext == ".pdf":
                reader = PdfReader(io.BytesIO(data))
                pages = [(page.extract_text() or "") for page in reader.pages]
                content = "\n".join(pages) + "\n" + str(reader.metadata)
                paper_record = manifest["paper_files"].get(member.removeprefix("artifacts/"))
                if paper_record:
                    page_hashes = [sha256(page.encode("utf-8")).hexdigest() for page in pages]
                    assert page_hashes == paper_record["page_text_sha256"], member
            else:
                continue
            assert not ABSOLUTE_PERSONAL_PATH.search(content), f"Personal path in ZIP member {member}"
            for leak in FORBIDDEN_IDENTITY_TOKENS:
                assert leak not in content, f"Anonymity leak ({leak}) in ZIP member {member}"

        assert hashes == support["member_sha256"]
        for group in ("artifacts_sha256", "frozen_inputs_sha256"):
            assert manifest[group]
            for path, digest in manifest[group].items():
                assert hashes[f"artifacts/{path}"] == digest, path
        assert set(manifest["paper_files"]) == {"paper/B_submission.pdf", "paper/P1_ERRATA.pdf"}
        for path, record in manifest["paper_files"].items():
            assert hashes[f"artifacts/{path}"] == record["sha256"], path
        assert acceptance["paper"]["sha256"] == hashes["artifacts/paper/B_submission.pdf"]
        assert acceptance["paper"]["pages"] == 24
        zf.extractall(tmp_path)

    _check_run_all_listing(tmp_path)

    proof = json.loads((REVIEW_DIR / PROOF_NAME).read_text(encoding="utf-8"))
    assert proof == acceptance["reproduction"]
    assert proof["byte_matches"] == len(manifest["artifacts_sha256"])
    assert proof["matched_artifacts"] == sorted(manifest["artifacts_sha256"])
    assert proof["verified_frozen_inputs"] == sorted(manifest["frozen_inputs_sha256"])
    pdf_names = sorted(Path(path).name for path in manifest["paper_files"])
    assert proof["pdf_text_matches"] == pdf_names
    assert proof["pdf_binary_matches"] == pdf_names
    assert proof["pdf_binary_match_count"] == len(pdf_names)
    assert set(proof["wall_seconds"]) == {
        "1_correctness", "2_validation", "3_experiments", "3b_sensitivity_pareto",
        "3c_p4_extended", "3d_corner_routes", "3e_dispatch_tradeoffs", "4_visuals", "5_pdf",
    }


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

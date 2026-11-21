"""Regenerate numeric evidence from the archive and record handoff checks."""

import argparse
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from pypdf import PdfReader

from package_problem_b import PROTOTYPE_AUDITS, PROTOTYPE_FIGURES, PROTOTYPE_PREVIEWS, PROTOTYPE_RESULTS, STEM, SUBMISSION


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def fresh_reproduction(archive_path):
    tracked = [
        *(f"results/{name}" for name in PROTOTYPE_RESULTS),
        *(f"figures/{name}" for name in PROTOTYPE_FIGURES),
    ]
    commands = ["solve_problem_b.py", "check_problem_b.py", "render_problem_b.py"]
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        with ZipFile(archive_path) as archive:
            filenames = archive.namelist()
            if "paper/B_prototype.tex" in filenames:
                tracked.append("paper/B_prototype.tex")
            assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in filenames)
            tracked.extend(f"figures/{name}" for name in PROTOTYPE_PREVIEWS if f"figures/{name}" in filenames)
            for script, outputs in PROTOTYPE_AUDITS:
                if f"src/{script}" in filenames:
                    commands.append(script)
                    tracked.extend(f"results/{name}" for name in outputs)
            expected = {name: hashlib.sha256(archive.read(name)).hexdigest() for name in tracked}
            archive.extractall(target)
        for name in commands:
            subprocess.run([sys.executable, str(target / "src" / name)], cwd=target, check=True)
        for name, checksum in expected.items():
            assert digest(target / name) == checksum, name
        return len(tracked)


def verify_paper(path, log, toc):
    reader = PdfReader(path)
    assert reader.metadata and "xdvipdfmx" in reader.metadata.producer
    assert not reader.metadata.author
    assert not re.search(r"Overfull|Undefined control sequence|undefined references",
                         log.read_text(encoding="utf-8", errors="replace"))
    pages = [page.extract_text() for page in reader.pages]
    entries = re.findall(r"\\contentsline \{(?:sub)?section\}\{\\numberline \{([\d.]+)\}(.+?)\}\{(\d+)\}",
                         toc.read_text(encoding="utf-8"))
    assert entries and all(3 <= int(page) <= len(pages) and heading.split()[0] in pages[int(page) - 1]
                           for _, heading, page in entries)
    assert re.findall(r"Figure\s+([1-6])\.", "\n".join(pages)) == list("123456")
    assert "Table 1." in "\n".join(pages)
    assert all(595.27 <= float(p.mediabox.width) <= 595.29 and
               841.88 <= float(p.mediabox.height) <= 841.90 for p in reader.pages)
    assert "AI Tool Usage Report" in pages[-1]
    return len(pages), len(entries)


def tool_version(command, flag="--version"):
    result = subprocess.run([command, flag], capture_output=True, text=True, check=True)
    return (result.stdout or result.stderr).strip().splitlines()[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reproduce-zip", type=Path, help="Reproduce a trusted internal ZIP without recompiling the PDF")
    parser.add_argument("--bundle", type=Path, default=SUBMISSION, help="Directory containing the numbered PDF and ZIP")
    parser.add_argument("--tex-log", type=Path)
    parser.add_argument("--tex-toc", type=Path)
    args = parser.parse_args()
    if args.reproduce_zip is not None:
        if args.tex_log or args.tex_toc:
            parser.error("--reproduce-zip runs separately from the PDF build checks.")
        count = fresh_reproduction(args.reproduce_zip)
        print(f"Verified {count} byte-identical files in the trusted internal ZIP.")
        return
    if args.tex_log is None or args.tex_toc is None:
        parser.error("Provide --tex-log and --tex-toc to verify a compiled bundle.")
    paper = args.bundle / f"{STEM}.pdf"
    archive = args.bundle / f"{STEM}fj.zip"
    pages, toc_entries = verify_paper(paper, args.tex_log, args.tex_toc)
    reproduced = fresh_reproduction(archive)
    members = {}
    with ZipFile(archive) as support:
        for entry in support.infolist():
            if not entry.is_dir():
                content = support.read(entry)
                members[entry.filename] = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
    manifest = {
        "problem": "B",
        "build": {
            "python": platform.python_version(), "platform": platform.system(),
            "tex": tool_version("tectonic"), "poppler": tool_version("pdftoppm", "-v"),
            "libraries": {name: version(name) for name in ("pypdf", "reportlab", "Pillow")},
        },
        "bundle_files": {
            file.name: {"bytes": file.stat().st_size, "sha256": digest(file)} for file in (paper, archive)
        },
        "archive_members": members,
        "checks": {"paper_pages": pages, "toc_entries": toc_entries,
                   "byte_identical_reproduced_files": reproduced},
    }
    (args.bundle / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (args.bundle / "VERIFY_REPORT.md").write_text(
        f"# B 题交接验收\n\n"
        f"- **完整重跑通过。** 在干净目录解压并重跑求解、复核及绘图，{reproduced} 份产物"
        "与压缩包内的对应文件逐字节一致。\n"
        f"- **PDF 结构通过。** 论文是 XeTeX 的 {pages} 页 A4 输出。"
        f"检查了 {toc_entries} 个目录条目、图表编号、匿名作者字段和最后的 AI 报告。"
        "TeX 日志没有文字溢出、未定义宏或未解析引用。\n"
        "- **数值复核完成。** 固定种子验证精确交会误差与包角覆盖率，"
        "并核对每个扰动案例的事件、失效车辆与评分。参见 results/B_validation.csv。\n"
        "- **结论范围。** P2(2) 和 P4 是有限候选上的可行调度，尚无连续空间全局最优性证明。"
        "P4 的结果针对列出的案例和断联口径。\n"
        "- **交接状态。** 上述为技术验收结果。队员核查和 AI 申报由队伍负责，承诺书另行保管。\n\n"
        "验收结构参考 [HowToCompeteBetter 的 Codex 指南](https://github.com/Rain-dust/HowToCompeteBetter/blob/main/book/04-用Codex完成数模.md)。\n",
        encoding="utf-8",
    )
    print(f"Verified {pages} compiled pages, {toc_entries} TOC entries and {reproduced} reproduced files.")


if __name__ == "__main__":
    main()

"""Regenerate numeric evidence from the archive and record handoff checks."""

import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from pypdf import PdfReader

from package_problem_b import ROOT, STEM, SUBMISSION


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def fresh_reproduction(archive_path):
    with tempfile.TemporaryDirectory() as directory:
        target = Path(directory)
        with ZipFile(archive_path) as archive:
            filenames = archive.namelist()
            assert all(not Path(name).is_absolute() and ".." not in Path(name).parts for name in filenames)
            archive.extractall(target)
        for name in ("solve_problem_b.py", "check_problem_b.py", "render_problem_b.py"):
            subprocess.run([sys.executable, str(target / "src" / name)], cwd=target, check=True)
        tracked = [
            *sorted((ROOT / "results").glob("B_*.csv")),
            ROOT / "results" / "B_timelines.json",
            ROOT / "paper" / "B_prototype.tex",
            *sorted((ROOT / "figures").glob("b_*.pdf")),
        ]
        for original in tracked:
            assert digest(original) == digest(target / original.relative_to(ROOT)), original
        return len(tracked)


def verify_paper(path, log, toc):
    reader = PdfReader(path)
    assert reader.metadata and "xdvipdfmx" in reader.metadata.producer
    assert not reader.metadata.author
    assert not re.search(r"Overfull|Undefined control sequence|undefined references",
                         log.read_text(encoding="utf-8", errors="replace"))
    pages = [page.extract_text() for page in reader.pages]
    entries = re.findall(r"\\contentsline \{section\}\{\\numberline \{(\d+)\}(.+?)\}\{(\d+)\}\{section",
                         toc.read_text(encoding="utf-8"))
    assert entries and all(3 <= int(page) <= len(pages) and heading.split()[0] in pages[int(page) - 1]
                           for _, heading, page in entries)
    assert re.findall(r"Figure\s+([1-6])\.", "\n".join(pages)) == list("123456")
    assert "Table 1." in "\n".join(pages)
    assert all(595.27 <= float(p.mediabox.width) <= 595.29 and
               841.88 <= float(p.mediabox.height) <= 841.90 for p in reader.pages)
    assert "AI Tool Usage Report" in pages[-1]
    return len(pages), len(entries)


def tool_version(command):
    return subprocess.run([command, "--version"], capture_output=True, text=True,
                          check=True).stdout.strip().splitlines()[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tex-log", type=Path, required=True)
    parser.add_argument("--tex-toc", type=Path, required=True)
    args = parser.parse_args()
    paper = SUBMISSION / f"{STEM}.pdf"
    archive = SUBMISSION / f"{STEM}fj.zip"
    pages, toc_entries = verify_paper(paper, args.tex_log, args.tex_toc)
    reproduced = fresh_reproduction(archive)
    inputs = [ROOT / "data" / "B题题面参数.csv"]
    outputs = [paper, archive, ROOT / "paper" / "B_prototype.tex",
               ROOT / "paper" / "main.tex", ROOT / "results" / "B_timelines.json",
               ROOT / "figures" / "B_figure_overview.png",
               *sorted((ROOT / "src").glob("*problem_b*.py")),
               *sorted((ROOT / "results").glob("B_*.csv")),
               *sorted((ROOT / "figures").glob("b_*.pdf"))]

    def inventory(files):
        return {p.relative_to(ROOT).as_posix(): {"bytes": p.stat().st_size, "sha256": digest(p)} for p in files}

    manifest = {
        "problem": "B",
        "build": {"python": platform.python_version(), "tex": tool_version("tectonic")},
        "inputs": inventory(inputs), "outputs": inventory(outputs),
        "checks": {"paper_pages": pages, "toc_entries": toc_entries,
                   "byte_identical_reproduced_files": reproduced},
    }
    (SUBMISSION / "RUN_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (SUBMISSION / "VERIFY_REPORT.md").write_text(
        f"# B 题交接验收\n\n"
        f"- **完整重跑通过。** 在干净目录解压并重跑求解、独立复核及绘图，{reproduced} 份结果、"
        "源稿和矢量图与交付版本逐字节一致。\n"
        f"- **LaTeX 编译通过。** 论文是 XeTeX 的 {pages} 页 A4 输出。"
        f"检查了 {toc_entries} 个目录条目、图表编号、匿名作者字段和最后的 AI 报告。"
        "TeX 日志没有文字溢出、未定义宏或未解析引用。\n"
        "- **版面目视检查完成。** 渲染查看了全部页面及六张矢量图的总览。"
        "打包脚本也检查了摘要与目录页、自动页码及 Times New Roman 字体嵌入。\n"
        "- **数值独立核对完成。** 固定种子验证精确交会误差与包角覆盖率，"
        "并核对每个扰动案例的事件、失效车辆与评分。参见 results/B_validation.csv。\n"
        "- **结论范围。** P2(2) 和 P4 是有限候选上的可行调度，尚无连续空间全局最优性证明。"
        "P4 的结果针对列出的案例和断联口径。\n"
        "- **交接状态。** 承诺书为已签 Word 的复排版本，需以原 Word 核对版式。"
        "已签文件单独保管。未执行官网上传。\n\n"
        "验收结构参考 [HowToCompeteBetter 的 Codex 指南](https://github.com/Rain-dust/HowToCompeteBetter/blob/main/book/04-用Codex完成数模.md)。\n",
        encoding="utf-8",
    )
    print(f"Verified {pages} compiled pages, {toc_entries} TOC entries and {reproduced} reproduced files.")


if __name__ == "__main__":
    main()

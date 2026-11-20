"""
从 B 题 PDF 抽出题面插图（Figure 1 场地布置、Figure 2 双站交会几何等）。

用途：建模和写论文时经常要单独看题图；队友在 GitHub 上也能直接预览，
不必装 PDF 阅读器。抽出的是 PDF 内嵌位图，画质与原件一致。

运行：python scripts/extract_problem_figures.py
"""

from __future__ import annotations

from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "01_problem" / "B-problem.pdf"
OUT = ROOT / "01_problem" / "figures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(PDF)
    print(f"{PDF.name}: {doc.page_count} pages")

    total = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        for idx, info in enumerate(page.get_images(full=True)):
            xref = info[0]
            img = doc.extract_image(xref)
            ext = img["ext"]
            # 过滤掉 1×1 之类的装饰性小图
            if img["width"] < 80 or img["height"] < 80:
                continue
            name = f"p{pno + 1:02d}-fig{idx + 1}.{ext}"
            (OUT / name).write_bytes(img["image"])
            total += 1
            print(f"  {name}  {img['width']}x{img['height']}  {len(img['image']) // 1024} KB")

    doc.close()
    if total == 0:
        print("  未抽到位图（题面图可能是矢量绘制），改用整页渲染：")
        doc = pymupdf.open(PDF)
        for pno in range(doc.page_count):
            pix = doc[pno].get_pixmap(dpi=200)
            name = f"p{pno + 1:02d}-page.png"
            pix.save(OUT / name)
            print(f"  {name}  {pix.width}x{pix.height}")
        doc.close()
    print(f"done: {total} image(s)")


if __name__ == "__main__":
    main()

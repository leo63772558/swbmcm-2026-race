"""PDF 逐页质量检查（排版 / 视觉 / 合规）。

用法:
    python pdf_qa.py <pdf> [--team SWBMCM2613050] [--out ../reports] [--strict]
    （正文之后有附录或 AI 使用报告时，可用 --counted-pages 指定最后一个计入页数的物理页）
    （--letter 已弃用：官方 Word 模板页眉不含题号字母，检查器自动兼容带/不带字母两种写法）

对齐 2026-11-05 官方《论文格式规范》+ Word 模板：
    * 第 1 页摘要页无页眉；第 2 页 Content 目录专用页；第 3 页起正文
    * 核对页顶队号与连续页码，兼容从第 3 页正文重新编号的官方 LaTeX 版式
    * 全文 12pt Times New Roman、全英文、≤25 页（附录页数不限）
    * PDF 不得夹带程序文件；图表内不得有中文字体

检查项（每条给出 严重/一般/可优化 分级 + 证据 + 页码）:
    C1 页眉合规（摘要页无页眉；第 2 页起队号 + Page N of M；M 为自动域真实总页数）
    C2 文本越界（超出左右/上下页边距）
    C3 页边距被占满导致视觉过密（文字块覆盖率）
    C4 空白页 / 近乎空白页
    C5 字体是否嵌入（非嵌入字体在评委机器上会变形）
    C6 位图分辨率（< 200 dpi 判为模糊）
    C7 未解析引用（"??"）与未定义参考文献
    C8 图表编号连续性（Fig./Table 序号跳号）
    C9 文本块重叠（视觉重影/压字）
    C10 元数据泄漏（作者/标题含姓名或校名）
    C11 页数统计与 ≤25 页硬上限（含摘要页 + 目录页）
    C12 第 2 页 Content 目录专用页
    C13 12pt Times New Roman 正文字号/字体
    C14 PDF 夹带程序文件 / 图表内中文字符
    C15 A4 页面
    C16 未填写的模板占位符
输出: <out>/PDF_QA_REPORT.md + <out>/pages/page-XX.png
"""
from __future__ import annotations

import os
import re
import sys
from argparse import ArgumentParser
from collections import Counter

try:
    import pymupdf
except ImportError:  # pragma: no cover
    import fitz as pymupdf

SEV_ORDER = {"严重": 0, "一般": 1, "可优化": 2}
MARGIN_PT = 8.0          # 允许的字形外扩容差
DPI_MIN = 200
MAX_PAGES = 25           # 官方硬上限：≤25 页（含摘要页 + 目录页），附录页数不限
HEADER_HEIGHT_PT = 72.0
A4_SIDES_PT = (210 * 72 / 25.4, 297 * 72 / 25.4)
PAGE_SIZE_TOL_PT = 0.5
BODY_PT = 12.0           # 官方强制正文字号
BODY_PT_TOL = 0.5
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def analyze(pdf_path: str, team: str, letter: str, out_dir: str, counted_pages: int | None = None) -> dict:
    doc = pymupdf.open(pdf_path)
    issues: list[dict] = []

    def add(sev, code, page, msg, evidence=""):
        issues.append({"severity": sev, "code": code, "page": page, "msg": msg, "evidence": evidence})

    pages = doc.page_count
    if counted_pages is None:
        counted_pages = pages
    elif not 3 <= counted_pages <= pages:
        doc.close()
        raise ValueError(f"计入正文的页数须在 3 到实际物理总页数 {pages} 之间")
    # 官方 Word 模板页眉为 Team#SWBMCM2613050（不含题号字母）；规范示例带字母。
    # 题号字母按可选项处理，两种写法都判合规（与 build.sh 的 [ABCD]? 一致）。
    prefix = re.escape(letter) if letter else "[A-D]"
    header_re = re.compile(rf"\bTeam\s*#\s*(?:{prefix})?{re.escape(team)}\b")
    page_no_re = re.compile(r"\bPage\s*(\d+)\s*of\s*(\d+)\b")
    headers = []
    for page in doc:
        top = pymupdf.Rect(0, 0, page.rect.width, min(HEADER_HEIGHT_PT, page.rect.height))
        text = page.get_text(clip=top * page.derotation_matrix)
        numbers = [(int(n), int(total)) for n, total in page_no_re.findall(text)]
        headers.append((bool(header_re.search(text)), numbers))
    # 官方 LaTeX 样例从物理第 3 页重新编号，目录页无页眉。
    restart_from_body = pages >= 3 and headers[2][1] == [(1, pages - 2)]
    expected_headers = max(pages - (2 if restart_from_body else 1), 0)

    fonts_all = set()
    embedded = {}
    captions = {"Fig.": [], "Table": []}
    hdr_ok = 0
    body_chars = 0        # 全文文本字符数
    times12_chars = 0     # 12pt Times 系正文字符数
    cjk_hits = 0          # 中文字符数

    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        w, h = page.rect.width, page.rect.height

        # C1 只检查页顶，正文里关于页码的叙述不参与校验。
        has_team, numbers = headers[i - 1]
        if i == 1:
            if has_team or numbers:
                add("严重", "C1", 1, "摘要页应为无页眉页，但页顶检测到队号或页码")
        elif i == 2 and restart_from_body:
            if has_team or numbers:
                add("严重", "C1", i, "正文从第 3 页重新编号时，目录页应采用相同的 LaTeX 版式",
                    "官方样例的目录页不显示页眉")
        else:
            number = i - 2 if restart_from_body else i
            total = pages - 2 if restart_from_body else pages
            if has_team and numbers == [(number, total)]:
                hdr_ok += 1
            else:
                add("严重", "C1", i, "页顶的队号或页码缺失、重复或错误",
                    f"应为 Team#{team}、Page {number} of {total}；检出页码={numbers}")

        # C15 核对物理纸张尺寸，避免页面裁切掩盖纸张设置错误。
        media_sides = sorted((page.mediabox.width, page.mediabox.height))
        if any(abs(actual - expected) > PAGE_SIZE_TOL_PT
               for actual, expected in zip(media_sides, A4_SIDES_PT)):
            add("严重", "C15", i, "页面物理尺寸不是 A4",
                f"短边 {media_sides[0]:.2f} pt，长边 {media_sides[1]:.2f} pt")

        if re.search(r"\[\s*FILL\b", text, re.IGNORECASE):
            add("严重", "C16", i, "页面仍有 [FILL 模板占位符")

        # C14：全英文及文件附件。
        cjk_hits += len(CJK_RE.findall(text))
        if next(page.annots(types=(pymupdf.PDF_ANNOT_FILE_ATTACHMENT,)), None) is not None:
            add("严重", "C14", i, "页面注释中附有文件")

        # C4 空白页（以「无文本块」为准：matplotlib 空白页也会嵌一张背景图，用 get_images() 会漏检）
        if len(text.strip()) < 20 and not page.get_text("blocks"):
            add("一般", "C4", i, "空白或近乎空白的页面", f"文本字符数={len(text.strip())}")

        # C2 文本越界 / C3 密度
        blocks = page.get_text("blocks")
        text_area = 0.0
        for b in blocks:
            x0, y0, x1, y1 = b[:4]
            if x0 < MARGIN_PT or x1 > w - MARGIN_PT or y0 < MARGIN_PT or y1 > h - MARGIN_PT:
                snippet = b[4].strip().replace("\n", " ")[:60]
                add("一般", "C2", i, "文本块超出安全页边距", f"bbox=({x0:.0f},{y0:.0f},{x1:.0f},{y1:.0f}) 内容: {snippet}")
            text_area += max(0.0, (x1 - x0)) * max(0.0, (y1 - y0))
        density = text_area / (w * h)
        if density > 0.72:
            add("可优化", "C3", i, "版面文字密度偏高，可能显得拥挤", f"覆盖率={density:.0%}")

        # C5 字体
        for f in page.get_fonts(full=True):
            name = f[3]
            fonts_all.add(name)
            embedded.setdefault(name, bool(f[1]) and f[1] != "")

        # C13：统计 12pt Times New Roman 正文占比
        for blk in page.get_text("dict")["blocks"]:
            for ln in blk.get("lines", []):
                for sp in ln.get("spans", []):
                    n = len(sp["text"].strip())
                    if not n:
                        continue
                    body_chars += n
                    if "Times" in sp["font"] and abs(sp["size"] - BODY_PT) <= BODY_PT_TOL:
                        times12_chars += n

        # C6 图片分辨率
        for img in page.get_images(full=True):
            xref = img[0]
            try:
                info = doc.extract_image(xref)
                px_w = info.get("width", 0)
                # 用图片在页面上的显示尺寸估算 dpi
                rects = page.get_image_rects(xref)
                if rects and px_w:
                    shown_in = max(rects[0].width, 1) / 72.0
                    dpi = px_w / shown_in
                    if dpi < DPI_MIN:
                        add("一般", "C6", i, "位图分辨率偏低（打印可能模糊）",
                            f"xref={xref} 约 {dpi:.0f} dpi（建议 ≥300）")
            except Exception:  # noqa: BLE001
                pass

        # C7 未解析引用（交叉引用 ?? / 文献引用 [?] / 空括号 []）
        if "??" in text:
            add("严重", "C7", i, "存在未解析的交叉引用（显示为 ??）", "需再编译一次或检查 \\label/\\ref")
        if "[?]" in text or re.search(r"\[\s*\]", text):
            add("严重", "C7", i, "存在未解析的文献引用（显示为 [?] 或 []）",
                "bibtex 未取到条目：检查 .bib 路径、编译顺序（xelatex→bibtex→xelatex×2）")

        # C8 图表编号
        for m in re.finditer(r"(?:Figure|Fig\.)\s*(\d+)", text):
            captions["Fig."].append(int(m.group(1)))
        for m in re.finditer(r"Table\s*(\d+)", text):
            captions["Table"].append(int(m.group(1)))

        # C9 文本块重叠
        for a in range(len(blocks)):
            for b in range(a + 1, len(blocks)):
                ba, bb = blocks[a], blocks[b]
                ix = min(ba[2], bb[2]) - max(ba[0], bb[0])
                iy = min(ba[3], bb[3]) - max(ba[1], bb[1])
                if ix <= 0 or iy <= 0:
                    continue
                area_a = max(0.0, (ba[2] - ba[0])) * max(0.0, (ba[3] - ba[1]))
                area_b = max(0.0, (bb[2] - bb[0])) * max(0.0, (bb[3] - bb[1]))
                small = min(area_a, area_b) or 1.0
                ratio = (ix * iy) / small
                # 只报"实质重叠"：重叠面积占较小块 35% 以上，且不是上下标这类极小片段
                if ratio > 0.35 and min(len(ba[4].strip()), len(bb[4].strip())) > 8:
                    add("一般", "C9", i, "两段文本块疑似重叠（可能压字）",
                        f"重叠占比 {ratio:.0%}: «{ba[4].strip()[:25]}» / «{bb[4].strip()[:25]}»")
                    break
            else:
                continue
            break

    # C10 元数据
    meta = doc.metadata or {}
    # 身份信息 + 官方 Word 模板自带的往届/WPS 元数据残留（清洗版模板已全部清空，
    # 这里用于兜住「误用官方原件直接导 PDF」的情形）
    leak_words = [
        "Nanjing", "南京", "University", "李丞渊", "LEI SENG", "SENG UN",
        "WONG CHON PAN", "WU WAN IN", "黄俊斌", "胡允贤",
        "South China University", "Huazhong University",
        "kev", "模竞", "番茄花园", "Toll Plaza", "hdid", "KSO",
        "SWBMCM2600001", "202200000001", "文本框",
    ]
    for k in ("author", "title", "subject", "creator", "producer"):
        v = (meta.get(k) or "")
        for lw in leak_words:
            if lw.lower() in v.lower():
                add("严重", "C10", 0, f"PDF 元数据 {k} 含身份信息", v[:80])

    # C11 页数 / ≤25 页硬上限
    if pages < 3:
        add("一般", "C11", 0, "页数过少，可能内容不完整", f"共 {pages} 页")
    if counted_pages > MAX_PAGES:
        add("严重", "C11", 0,
            f"计入页数 {counted_pages} 超过官方 ≤{MAX_PAGES} 页上限（含摘要页和目录页）",
            "末尾有附录或 AI 使用报告时，人工复核分界后用 --counted-pages 指定最后一个计入页")

    # C12 第 2 页 Content 目录专用页
    if pages >= 2:
        p2 = doc[1].get_text()
        if not re.search(r"(?m)^\s*Content\s*$", p2):
            add("严重", "C12", 2, "第 2 页应为 Content 目录专用页，但未检出 Content 标题",
                "官方规范第二条：第 2 页整页目录，第 3 页起才是正文")

    # C13 12pt Times New Roman
    if body_chars:
        ratio = times12_chars / body_chars
        if not any("Times" in f for f in fonts_all):
            add("严重", "C13", 0, "正文未检出 Times New Roman 字体",
                f"检出字体：{', '.join(sorted(fonts_all))[:120]}")
        elif ratio < 0.30:
            add("严重", "C13", 0, "12pt Times New Roman 正文占比过低，字号/字体可能不符官方强制要求",
                f"12pt Times 字符占比={ratio:.0%}（阈值 ≥30%）")

    # C14 PDF 不得夹带程序文件 / 全英文
    try:
        n_emb = doc.embfile_count()
    except Exception:  # noqa: BLE001
        n_emb = 0
    if n_emb > 0:
        add("严重", "C14", 0, f"PDF 夹带 {n_emb} 个嵌入文件（官方禁止夹带程序文件/工具软件）",
            "源码应放附录文本或 …fj.zip 支撑材料")
    if cjk_hits > 0:
        add("一般", "C14", 0, f"全文检出 {cjk_hits} 个中文字符（官方要求全英文、图表内不得出现中文字体）",
            "逐处核对图表标签、图例、表头")

    # 字体嵌入汇总
    for name, emb in embedded.items():
        if not emb:
            add("一般", "C5", 0, f"字体未嵌入：{name}", "换机器打开可能变形/替换字形")

    # 图号跳号
    for kind, seq in captions.items():
        if seq:
            uniq = sorted(set(seq))
            gaps = [n for n in range(min(uniq), max(uniq) + 1) if n not in uniq]
            if gaps:
                add("可优化", "C8", 0, f"{kind} 编号可能不连续", f"缺失: {gaps}")

    # 渲染页面
    page_dir = os.path.join(out_dir, "pages")
    os.makedirs(page_dir, exist_ok=True)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=110)
        pix.save(os.path.join(page_dir, f"page-{i:02d}.png"))

    issues.sort(key=lambda d: (SEV_ORDER[d["severity"]], d["code"], d["page"]))
    doc.close()
    return {"pdf": pdf_path, "pages": pages, "counted_pages": counted_pages,
            "hdr_ok": hdr_ok, "expected_headers": expected_headers, "issues": issues,
            "fonts": sorted(fonts_all), "page_dir": page_dir,
            "meta": meta, "size_mb": round(os.path.getsize(pdf_path) / 1048576, 2)}


def write_report(res: dict, out_dir: str, pdf_name: str) -> str:
    cnt = Counter(i["severity"] for i in res["issues"])
    expect_hdr = res["expected_headers"]
    lines = [
        f"# PDF 逐页质量检查报告 · `{pdf_name}`",
        "",
        f"> 检查时间：{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}　·　"
        f"物理页数：**{res['pages']}**　·　计入页数：**{res['counted_pages']}**　·　"
        f"页眉合规：**{res['hdr_ok']}/{expect_hdr}**　·　大小：**{res['size_mb']} MB**",
        "",
        "## 1. 结论",
        "",
        "| 级别 | 数量 | 含义 |",
        "|---|---|---|",
        f"| 🔴 严重 | {cnt.get('严重', 0)} | 直接影响评审或不符规范，必须修 |",
        f"| 🟠 一般 | {cnt.get('一般', 0)} | 影响观感/可读性，应修 |",
        f"| 🟡 可优化 | {cnt.get('可优化', 0)} | 锦上添花，时间允许再处理 |",
        "",
    ]
    if cnt.get("严重", 0) == 0 and cnt.get("一般", 0) == 0:
        lines += ["**判定：通过。** 未发现排版层面的严重或一般问题。", ""]
    else:
        lines += ["**判定：需修改后复检。** 明细见下节。", ""]

    lines += ["## 2. 问题明细（按级别排序）", ""]
    if res["issues"]:
        lines += ["| 级别 | 编号 | 页码 | 问题 | 证据 |", "|---|---|---|---|---|"]
        for it in res["issues"]:
            pg = "全文" if it["page"] == 0 else f"P{it['page']}"
            ev = it["evidence"].replace("|", "\\|")[:90]
            lines.append(f"| {it['severity']} | {it['code']} | {pg} | {it['msg']} | {ev} |")
    else:
        lines.append("无。")
    lines += ["", "## 3. 检查项覆盖", "",
              "| 编号 | 检查内容 |", "|---|---|",
              "| C1 | 页顶队号及连续页码；兼容从正文重新编号的官方 LaTeX 版式 |",
              "| C2 | 文本越界（超出安全页边距） |",
              "| C3 | 文字密度（过密观感） |",
              "| C4 | 空白/近空白页 |",
              "| C5 | 字体嵌入 |",
              "| C6 | 位图分辨率 ≥200 dpi |",
              "| C7 | 未解析交叉引用 `??` |",
              "| C8 | 图表编号连续性 |",
              "| C9 | 文本块重叠 |",
              "| C10 | 元数据身份泄漏 |",
              "| C11 | 页数合理性与 ≤25 页硬上限（含摘要页 + 目录页） |",
              "| C12 | 第 2 页 `Content` 目录专用页 |",
              "| C13 | 12pt Times New Roman 正文字号/字体 |",
              "| C14 | PDF 内嵌文件、附件注释及中文字符 |",
              "| C15 | A4 物理页面尺寸 |",
              "| C16 | 未填写的模板占位符 |",
              ""]
    lines += ["## 4. 使用到的字体", "",
              "、".join(f"`{f}`" for f in res["fonts"]) or "（未检出）", ""]
    lines += ["## 5. 逐页图像", "",
              f"已渲染到 `{os.path.relpath(res['page_dir'], out_dir)}/page-XX.png`，"
              "请人工抽检：图例是否被裁、公式是否溢出、表格是否跨页断裂、空白是否合理。", ""]

    path = os.path.join(out_dir, "PDF_QA_REPORT.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path


def main() -> int:
    parser = ArgumentParser(description="检查参赛论文 PDF 的排版与匿名信息。")
    input_pdf = parser.add_mutually_exclusive_group(required=True)
    input_pdf.add_argument("source", nargs="?", help="待检查的 PDF")
    input_pdf.add_argument("--pdf", help="待检查的 PDF")
    parser.add_argument("--team", default="SWBMCM2613050")
    parser.add_argument("--letter", default="", help="兼容旧命令")
    parser.add_argument("--strict", action="store_true", help="发现严重问题时返回退出码 1")
    parser.add_argument("--counted-pages", type=int, help="人工确认的最后一个计入页数的物理页")
    parser.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "reports", "pdf_qa"
    ))
    args = parser.parse_args()
    pdf = args.pdf or args.source
    out_dir = args.out
    os.makedirs(out_dir, exist_ok=True)

    try:
        res = analyze(pdf, args.team, args.letter, out_dir, args.counted_pages)
    except ValueError as exc:
        parser.error(str(exc))
    rep = write_report(res, out_dir, os.path.basename(pdf))
    cnt = Counter(i["severity"] for i in res["issues"])
    expect_hdr = res["expected_headers"]
    print(f"[QA] {res['pages']} pages, 页眉合规 {res['hdr_ok']}/{expect_hdr}, "
          f"严重={cnt.get('严重',0)} 一般={cnt.get('一般',0)} 可优化={cnt.get('可优化',0)}")
    print(f"[QA] report -> {rep}")
    return 1 if args.strict and cnt["严重"] else 0


if __name__ == "__main__":
    sys.exit(main())

"""
统一复现入口（严格 Fail-Fast，零静默跳过）：
直接桥接 `10_比赛工作区/src/reproduce_b_revision.py`，完整执行：
  1. P1 几何与圆角净距正确性 (`b_revision_correctness.py`)
  2. P2/P3 数值与 3x2M 蒙特卡洛独立校验 (`b_revision_validation.py`)
  3. P2(2) k=3 vs k=8 调度对比与 P4 73 场景实验 (`b_revision_experiments.py`)
  4. 真实求解器参数扰动、5 组权重稳定性与 3D Pareto (`b_revision_sensitivity_pareto.py`)
  5. P4 去重 (62) + 扩充 (115) 唯一场景与 k=2/3/5/8 预算稳定性 (`b_revision_p4_extended.py`)
  6. 11 组 Matplotlib 高清科研图 + 暗黑 3D 数字孪生回放校验 (`b_revision_figures.py` / `b_revision_replay.py`)
  7. XeLaTeX 论文编译 + 6 项硬核审计（含 1,000 配对 / 4,200 顺序精确 B&B）+ 逐文件哈希复跑核对

用法：
    python 03_code/run_all.py                      # 在临时洁净目录跑通全链路并自动核对哈希
    python 03_code/run_all.py --out <全新输出目录>   # 输出并保留至指定全新洁净目录
    python 03_code/run_all.py --list               # 列出全部 7 个强制执行阶段
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
REPO = CODE_DIR.parent
SRC_DIR = REPO / "10_比赛工作区" / "src"
REPRO_SCRIPT = SRC_DIR / "reproduce_b_revision.py"
DEFAULT_REF = REPO / "10_比赛工作区" / "submission" / "b_revision_20261121"

PIPELINE_STAGES = [
    ("1_correctness", "10_比赛工作区/src/b_revision_correctness.py", "P1 可观测区域、圆角 Minkowski 净距与 readiness-first 校验"),
    ("2_validation", "10_比赛工作区/src/b_revision_validation.py", "P2(1) 有限差分雅可比与 P3 3x2M Bonferroni-Wilson 独立校验"),
    ("3_experiments", "10_比赛工作区/src/b_revision_experiments.py", "P2(2) k=3 vs k=8 同池调度与 P4 73 归档场景对照"),
    ("3b_sensitivity_pareto", "10_比赛工作区/src/b_revision_sensitivity_pareto.py", "真实 P1-P4 参数扰动、Fixed vs ReOpt、5 权重稳定性与 3D Pareto"),
    ("3c_p4_extended", "10_比赛工作区/src/b_revision_p4_extended.py", "P4 去重 (62) + 扩充 (115) 唯一场景与 k=2/3/5/8 预算稳定性"),
    ("4_visuals", "10_比赛工作区/src/b_revision_figures.py", "11 组 PDF/PNG 顶刊图 + 离线 3D 数字孪生回放与 Node 一致性核验"),
    ("5_pdf_and_audit", "10_比赛工作区/src/b_hardcore_audit.py", "XeLaTeX 论文编译 + 6 项硬核审计（含 1,000 配对 / 4,200 顺序精确 B&B）"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="SWBMCM2613050 Problem B strict fail-fast clean-room reproduction entry.")
    ap.add_argument("--out", type=Path, help="Fresh output directory for clean-room rerun (preserved after run).")
    ap.add_argument("--reference", type=Path, default=DEFAULT_REF, help="Reference submission directory for hash/PDF check.")
    ap.add_argument("--tex-bundle", type=Path, help="Optional XeLaTeX bundle directory.")
    ap.add_argument("--keep-temp", action="store_true", help="Keep auto-created temporary output directory.")
    ap.add_argument("--list", action="store_true", help="List all mandatory pipeline stages and exit.")
    args = ap.parse_args()

    # Fail-fast check that every required pipeline module exists
    missing = [rel for _, rel, _ in PIPELINE_STAGES if not (REPO / rel).is_file()]
    if not REPRO_SCRIPT.is_file():
        missing.insert(0, str(REPRO_SCRIPT.relative_to(REPO)))

    if args.list:
        for key, rel, desc in PIPELINE_STAGES:
            status = "READY" if (REPO / rel).is_file() else "MISSING"
            print(f"  [{status}] {key:<22} {desc} ({rel})")
        return 1 if missing else 0

    if missing:
        print("FATAL: Missing mandatory pipeline file(s); refusing to skip silently:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 2

    if not args.reference.is_dir():
        print(f"FATAL: Reference directory not found: {args.reference}", file=sys.stderr)
        return 2

    auto_temp_root: Path | None = None
    if args.out is not None:
        out_dir = args.out.resolve()
        if out_dir.exists():
            print(f"FATAL: --out directory already exists (must be a fresh directory): {out_dir}", file=sys.stderr)
            return 2
    else:
        auto_temp_root = Path(tempfile.mkdtemp(prefix="swbmcm_b_runall_"))
        out_dir = auto_temp_root / "clean_rerun"

    cmd = [
        sys.executable,
        "-B",
        str(REPRO_SCRIPT),
        "--out",
        str(out_dir),
        "--reference",
        str(args.reference.resolve()),
    ]
    if args.tex_bundle is not None:
        cmd.extend(["--tex-bundle", str(args.tex_bundle.resolve())])

    print(f"Repository : {REPO}")
    print(f"Reference  : {args.reference.resolve()}")
    print(f"Clean Out  : {out_dir}")
    print(f"Command    : {' '.join(cmd)}\n")

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(cmd, cwd=str(REPO), check=False)
        elapsed = time.perf_counter() - t0
        if proc.returncode != 0:
            print(f"\nFAIL: Reproduction pipeline exited with code {proc.returncode} after {elapsed:.2f}s.", file=sys.stderr)
            return proc.returncode
        check_json = out_dir / "REPRODUCTION_CHECK.json"
        if not check_json.is_file():
            print(f"\nFAIL: Missing REPRODUCTION_CHECK.json at {check_json}.", file=sys.stderr)
            return 3
        print(f"\nPASS: Full clean-room reproduction & hash/PDF verification succeeded in {elapsed:.2f}s.")
        print(f"Check file : {check_json}")
        return 0
    finally:
        if auto_temp_root is not None and not args.keep_temp:
            shutil.rmtree(auto_temp_root, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())

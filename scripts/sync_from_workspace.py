"""
把主工作区（D:\\WorkBuddy\\数维杯）的比赛产物同步到本仓库。

用途：如果继续在主工作区干活（那里有 Word 模板、官方规则原件），
用这个脚本把产物单向推到仓库，再提交。**只复制，不删除**。

用法：
    python scripts/sync_from_workspace.py                 # 复制 + 显示 git status
    python scripts/sync_from_workspace.py --commit "..."  # 复制 + 提交 + 推送
    python scripts/sync_from_workspace.py --dry-run       # 只看会复制什么

不会覆盖仓库里的文档（README.md / notes.md 等），因为只映射产物子目录。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKSPACE = Path(r"D:\WorkBuddy\数维杯")
RACE = WORKSPACE / "10_比赛工作区"

# (源目录, 目标目录)
MAPPINGS = [
    (RACE / "src",     REPO / "03_code"),
    (RACE / "results", REPO / "04_results"),
    (RACE / "figures", REPO / "05_figures"),
    (RACE / "paper",   REPO / "06_paper"),
]

# 不覆盖仓库侧的说明文件
SKIP_NAMES = {"README.md", "notes.md", "run_all.py", ".gitkeep"}

# 额外单文件：(源文件, 目标文件)
FILES = [
    (WORKSPACE / "12_AI使用记录" / "AI_USAGE_LOG_比赛版.csv",
     REPO / "08_ai-log" / "AI_USAGE_LOG.csv"),
]


def iter_files(src: Path):
    for p in src.rglob("*"):
        if not p.is_file():
            continue
        if p.name in SKIP_NAMES:
            continue
        if "__pycache__" in p.parts:
            continue
        if p.suffix in {".pyc", ".aux", ".log", ".out", ".toc"}:
            continue
        yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--commit", help="提交信息；给了就自动 add+commit+push")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not WORKSPACE.exists():
        print(f"主工作区不存在：{WORKSPACE}")
        return 1

    copied = 0
    for src_dir, dst_dir in MAPPINGS:
        if not src_dir.exists():
            continue
        for f in iter_files(src_dir):
            rel = f.relative_to(src_dir)
            dst = dst_dir / rel
            if args.dry_run:
                print(f"  would copy  {src_dir.name}/{rel}  ->  {dst.relative_to(REPO)}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dst)
                print(f"  copied  {src_dir.name}/{rel}  ->  {dst.relative_to(REPO)}")
            copied += 1

    for src, dst in FILES:
        if not src.exists():
            continue
        if args.dry_run:
            print(f"  would copy  {src.name}  ->  {dst.relative_to(REPO)}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            print(f"  copied  {src.name}  ->  {dst.relative_to(REPO)}")
        copied += 1

    print(f"\n共 {copied} 个文件")
    if args.dry_run or copied == 0:
        return 0

    print("\n--- git status ---")
    subprocess.run(["git", "-C", str(REPO), "status", "--short"], check=False)

    if args.commit:
        subprocess.run(["git", "-C", str(REPO), "add", "-A"], check=True)
        c = subprocess.run(["git", "-C", str(REPO), "commit", "-m", args.commit], check=False)
        if c.returncode != 0:
            print("提交未执行（可能无变更或提交失败），跳过推送。")
            return c.returncode
        subprocess.run(["git", "-C", str(REPO), "push"], check=True)
        print("\n已提交并推送。")
    else:
        print("\n下一步：git add -A && git commit -m \"...\" && git push")
    return 0


if __name__ == "__main__":
    sys.exit(main())

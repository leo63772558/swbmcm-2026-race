"""
统一入口：跑出全部结果与图。

约定：每一问在自己的目录下放一个 run.py 作为入口函数 run()，
本脚本按 P1 → P2(1) → P2(2) → P3 → P4 的顺序调用。
哪一问还没写就不跑，只提示，不算失败。

用法：
    python 03_code/run_all.py            # 跑全部
    python 03_code/run_all.py --only P2  # 只跑 P2 下所有子任务
    python 03_code/run_all.py --list     # 只看有哪些任务
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
import traceback
from pathlib import Path

CODE_DIR = Path(__file__).resolve().parent
REPO = CODE_DIR.parent

# 执行顺序即依赖顺序：P1 的可观测区域是 P2 的可行域，P2(2) 的方案是 P4 的基线
TASKS = [
    ("P1",   "P1/run.py",     "P1 可观测区域与最优站位"),
    ("P2.1", "P2/run_p2_1.py", "P2(1) 双站精度模型与最优站点对"),
    ("P2.2", "P2/run_p2_2.py", "P2(2) 车辆复用与路径"),
    ("P3",   "P3/run.py",     "P3 误差传播与允许行程"),
    ("P4",   "P4/run.py",     "P4 扰动重调度与方案对比"),
]


def load_run(dotted: str):
    """按仓库相对路径加载模块，并从模块里取 run()。"""
    path = CODE_DIR / dotted
    if not path.exists():
        return None
    mod_name = dotted.replace("/", ".").replace("\\", ".").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module                 # 让模块内的相对导入能找到自己
    sys.path.insert(0, str(CODE_DIR))              # 允许 `from common import ...`
    spec.loader.exec_module(module)
    return getattr(module, "run", None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="只跑指定前缀，如 P2 / P3 / P4.1")
    ap.add_argument("--list", action="store_true", help="只列出任务")
    args = ap.parse_args()

    tasks = TASKS
    if args.only:
        tasks = [t for t in TASKS if t[0].startswith(args.only)]

    if args.list:
        for key, rel, desc in tasks:
            mark = "ready" if (CODE_DIR / rel).exists() else "todo "
            print(f"  [{mark}] {key:<6} {desc}  ({rel})")
        return 0

    print(f"repo: {REPO}")
    print(f"running {len(tasks)} task(s)\n")

    done, skipped, failed = [], [], []

    for key, rel, desc in tasks:
        print(f"[{key}] {desc}")
        try:
            run = load_run(rel)
        except Exception:
            print("   -> import 失败：")
            traceback.print_exc()
            failed.append(key)
            continue
        if run is None:
            print(f"   -> 跳过（{rel} 还没写）")
            skipped.append(key)
            continue
        t0 = time.perf_counter()
        try:
            run()
        except Exception:
            print("   -> 运行失败：")
            traceback.print_exc()
            failed.append(key)
            continue
        print(f"   -> ok  ({time.perf_counter() - t0:.1f}s)")
        done.append(key)

    print("\n" + "=" * 52)
    print(f"完成 {len(done)}  跳过 {len(skipped)}  失败 {len(failed)}")
    if done:
        print("  完成：" + ", ".join(done))
    if skipped:
        print("  跳过：" + ", ".join(skipped))
    if failed:
        print("  失败：" + ", ".join(failed))
    print("=" * 52)

    print(f"\n结果目录：{REPO / '04_results'}")
    print(f"图片目录：{REPO / '05_figures'}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

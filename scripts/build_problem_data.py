"""
从 B 题题面生成结构化数据表。

为什么要有这个脚本：题面里的坐标、建筑包络、参数全部来自 PDF 表格与正文，
手工敲进 CSV 极易出错，而且无法审计。这里把题面数值集中在一处，
由脚本算出目标坐标，任何人可以复核一遍。

数据来源：01_problem/B-problem.md（题面文本）与 01_problem/B-problem.pdf
运行：python scripts/build_problem_data.py
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "01_problem" / "data"

# ---------------------------------------------------------------- 题面原始数值
# 场地与中心
FIELD_SIZE = 100.0            # 正方形场地边长 100 m × 100 m
DISPATCH_CENTER = (50.0, 50.0)

# Table 1 —— 建筑平面范围与高度（题面 Table 1 原文）
# (id, x_min, x_max, y_min, y_max, height_m)
BUILDINGS = [
    ("B1", 22.0, 34.0, 16.0, 26.0, 20.0),
    ("B2", 63.0, 79.0, 59.0, 71.0, 28.0),
    ("B3", 10.0, 24.0, 65.0, 76.0, 12.0),
    ("B4", 72.0, 86.0, 22.0, 34.0, 24.0),
    ("B5", 41.0, 51.0, 38.0, 46.0, 32.0),
]

# 五辆待命观测车初始位置（题面正文）
VEHICLES = [
    ("V1", 15.0, 14.0),
    ("V2", 88.0, 10.0),
    ("V3", 14.0, 86.0),
    ("V4", 88.0, 68.0),
    ("V5", 50.0, 93.0),
]

# 基准告警：(id, theta_deg, R_m, H_m)  theta 为自正东逆时针的方位角
ALERTS = [
    ("T1", 30.0, 40.0, 45.0),
    ("T2", 150.0, 45.0, 35.0),
    ("T3", 285.0, 38.0, 55.0),
]

# 模型参数（题面正文）
PARAMS = [
    ("field_side", FIELD_SIZE, "m", "场地为 100 m × 100 m 正方形，原点在西南角"),
    ("dispatch_center_x", DISPATCH_CENTER[0], "m", "调度中心 O = (50, 50)"),
    ("dispatch_center_y", DISPATCH_CENTER[1], "m", "调度中心 O = (50, 50)"),
    ("vehicle_radius", 1.5, "m", "观测车等效半径 1.5 m，不得越界、不得进入建筑内部"),
    ("vehicle_speed", 3.0, "m/s", "匀速 3 m/s，忽略加减速、转向与避碰时间"),
    ("camera_height", 2.0, "m", "相机安装于等效圆盘几何中心，离地 2 m"),
    ("gimbal_elev_min", -10.0, "deg", "云台可行俯仰角范围下界"),
    ("gimbal_elev_max", 80.0, "deg", "云台可行俯仰角范围上界"),
    ("gimbal_max_rate", 30.0, "deg/s", "方位轴与俯仰轴最大角速度，两轴可同时转动"),
    ("joint_observation", 5.0, "s", "两车到位并完成指向后的联合观测时长"),
    ("travel_limit_P2", 30.0, "s", "P2(1) 中单车从初始位置到观测站的行程上限"),
    ("azimuth_sigma", 1.0, "deg", "P2 两车方位角测量误差独立同分布 N(0, 1°²)"),
    ("eval_window_P4", 60.0, "s", "P4 评价窗口 t ∈ [0, 60] s"),
    ("disturbance_time_P4", 5.0, "s", "P4 扰动发生时刻 t = 5 s"),
]


def target_xy(theta_deg: float, R: float) -> tuple[float, float]:
    """由告警 (theta, R) 换算水平坐标，题面定义：(50 + R cosθ, 50 + R sinθ)。"""
    t = math.radians(theta_deg)
    return (DISPATCH_CENTER[0] + R * math.cos(t),
            DISPATCH_CENTER[1] + R * math.sin(t))


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    print(f"  wrote {path.relative_to(ROOT)}  ({len(rows)} rows)")


def main() -> None:
    print("building problem data ...")

    write_csv(OUT / "buildings.csv",
              ["id", "x_min_m", "x_max_m", "y_min_m", "y_max_m", "height_m"],
              [list(b) for b in BUILDINGS])

    write_csv(OUT / "vehicles.csv",
              ["id", "x0_m", "y0_m"],
              [list(v) for v in VEHICLES])

    alert_rows = []
    for aid, theta, R, H in ALERTS:
        x, y = target_xy(theta, R)
        alert_rows.append([aid, theta, R, H, round(x, 4), round(y, 4)])
    write_csv(OUT / "alerts.csv",
              ["id", "theta_deg", "R_m", "H_m", "x_target_m", "y_target_m"],
              alert_rows)

    write_csv(OUT / "params.csv",
              ["name", "value", "unit", "note"],
              [list(p) for p in PARAMS])

    # 自检：场地不变量
    for bid, x0, x1, y0, y1, h in BUILDINGS:
        assert 0 <= x0 < x1 <= FIELD_SIZE, f"{bid} x 范围越界"
        assert 0 <= y0 < y1 <= FIELD_SIZE, f"{bid} y 范围越界"
        assert h > 0, f"{bid} 高度必须为正"
    for vid, x, y in VEHICLES:
        assert 0 <= x <= FIELD_SIZE and 0 <= y <= FIELD_SIZE, f"{vid} 初始位置越界"
    print("  invariant checks: PASS")


if __name__ == "__main__":
    main()

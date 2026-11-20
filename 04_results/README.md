# 04_results — 结果表（正文数字的唯一来源）

> **正文与图表里的每一个数字，都必须能追到这里的某个 CSV。禁止手打。**

## 命名约定

| 文件 | 由谁生成 | 内容 |
|---|---|---|
| `p1_observable_region.csv` | `P1/run.py` | 可观测区域的网格点（x, y, 是否可观测） |
| `p1_best_station.csv` | `P1/run.py` | 最优站点坐标、r、仰角、Q |
| `p2_1_station_pair.csv` | `P2/run_p2_1.py` | T2 的最优两站、基线、交会角、行程时间、精度指标 |
| `p2_2_schedule.csv` | `P2/run_p2_2.py` | 三告警的观测开始时刻、t_max |
| `p2_2_timeline.csv` | `P2/run_p2_2.py` | 每辆车的完整时间轴事件 |
| `p2_2_heuristic_compare.csv` | `P2/run_p2_2.py` | 与最近分配启发式的对比 |
| `p3_max_distance.csv` | `P3/run.py` | 满足 0.95 的最大允许行程、对应 σ |
| `p3_ab_feasible.csv` | `P3/run.py` | 80 m 时 (a, b) 的可行域边界 |
| `p3_error_contrib.csv` | `P3/run.py` | 三个误差源的相对贡献 |
| `p4_scenarios.csv` | `P4/run.py` | 各场景的 (η, t_last) |
| `p4_compare.csv` | `P4/run.py` | 重调度 vs 保留原方案 |

## 规矩

- **CSV 由脚本生成，不要手改**。要改结果就改算法再重跑
- 每个 CSV 第一行是表头，列名带单位（`x_m`、`t_s`、`theta_deg`）
- 浮点保留到"够写论文"的位数即可（一般 4 位），不要留 17 位
- `notes.md` 记录**每次运行的关键结论与 seed**，供人复盘

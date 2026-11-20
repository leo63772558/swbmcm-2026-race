# P1 代码

**负责人**：黄俊斌（电气）　**建模文档**：`02_model/P1.md`

**入口**：`run.py`，暴露一个 `run()` 函数（`run_all.py` 会调它）

| 项 | 内容 |
|---|---|
| 输入 | `01_problem/data/{buildings,vehicles,alerts,params}.csv`、`03_code/common/` 的几何函数 |
| 输出 | `04_results/p1_observable_region.csv`、`04_results/p1_best_station.csv`、`05_figures/fig-p1-observable-region.{pdf,png}` |
| 怎么跑 | `python 03_code/run_all.py --only P1` |

## 要实现的东西

1. 在场地内做网格（或更精细的搜索），对每个候选站点判定是否**同时**满足三条约束
2. 计算 `Q = 1/r`，找最大点；写出同分时的 tie-breaking
3. 画可观测区域图（题目明确要求"illustrate your result with a plot"）

## 注意

- 车体是**圆盘**（半径 1.5 m），不是点
- **相切即遮挡**
- 仰角须在 [−10°, 80°]

写完把本文件的输入/输出/命令三行改成实际值。

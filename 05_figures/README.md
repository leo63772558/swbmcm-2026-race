# 05_figures — 论文用图

> **只放由脚本生成的图。** 手工 P 的图不可复现，也不算完成。

## 规矩

| 规矩 | 说明 |
|---|---|
| 双格式 | 每张图同时出 `.pdf`（进论文，矢量清晰）和 `.png`（快看，300 dpi） |
| 命名 | `fig-<问号>-<内容>.pdf`，例：`fig-p1-observable-region.pdf` |
| 脚本 | 出图脚本在 `03_code/P*/`，改图只改脚本 |
| 图标题在下 | 论文里图题在图**下方**，表题在表**上方**（官方规范，别搞反） |
| 无中文字体 | 图里不能出现中文，坐标轴、图例、标注全部英文（PDF 里夹中文字体会被扣分） |
| 字号 | 图内文字 ≥ 9 pt，缩到论文栏宽后仍要能看清 |
| 配色 | 同一含义在图间保持一致（如"可观测区域"永远同一个颜色） |

## 计划中的图

⬜ `fig-p1-observable-region` — T1 的可观测区域 + 最优点位
⬜ `fig-p2-intersection-geometry` — 两站交会几何、基线、交会角示意（可参考题面 Figure 2）
⬜ `fig-p2-accuracy-vs-angle` — 精度指标随交会角变化（展示退化）
⬜ `fig-p2-2-gantt` — 五辆车的时间轴甘特图
⬜ `fig-p3-psi-distribution` — `Δψ` 的分布与 ±5° 区间
⬜ `fig-p3-error-contribution` — 三个误差源的相对贡献
⬜ `fig-p4-scenarios` — 各场景 (η, t_last) 对比

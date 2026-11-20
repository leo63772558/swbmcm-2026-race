# 01 · 全局假设与简化

> **必须队员自己写。** 每条假设都要写清三件事：假设什么、为什么可以这么假设、不这样假设的代价是什么。
> 论文里的模型假设章节直接由此改写（注意用自己的语言，别整段搬，AIGC 检测看的是正文）。

## 格式

```
### A1 <一句话假设>
- 依据：<题面哪句话 / 物理常识 / 计算量约束>
- 影响：<它简化掉了什么，哪些结论依赖它>
- 若放宽：<会多出什么复杂度，大概什么量级>
```

## 题面已明确允许的简化（可直接引用题面，不算自作主张）

| 简化 | 题面出处 |
|---|---|
| 忽略加减速、转向、避碰耗时 | 「The constant travel speed is 3 m/s. Acceleration, deceleration, vehicle steering, and collision-avoidance time are neglected.」 |
| 目标在部署阶段视为静止 | 「All targets are treated as stationary for the deployment phase studied in this problem.」 |
| 计算采用标称参数（P3 误差场景除外） | 「All computations adopt nominal parameters, except for the error-case scenarios specified in Problem 3.」 |
| 目标高度由告警直接给出，不参与交会解算 | 「The target altitude is provided directly by the alert message and is not solved through intersection.」 |

## 需要队员补的假设（这些没有标准答案）

⬜ A1 建筑视为**实心**轴对齐长方体，无孔洞、无悬挑
⬜ A2 观测车圆盘不侵入建筑，但可以贴边（距离恰好 1.5 m 算可行？还是必须严格大于？）
⬜ A3 视线遮挡只看建筑，不考虑地形起伏与植被（题面也的确没给）
⬜ A4 车辆之间不互相遮挡视线
⬜ A5 云台转向与车辆行驶不能并行（题面：行驶中云台保持正东水平）
⬜ A6 P2(2) / P4 中车辆在站点等待另一辆车时，等待时长是否计入目标
⬜ A7 P4 新告警的 H 固定 50 m，是否影响其可观测区域（是：高度变，仰角约束变）
⬜ A8 通信中断期间车辆"继续执行原任务"——是否意味着中断期间不能重新分配任何车
⬜ A9 失效车辆在 t=5 s 立即消失，其已完成的观测仍有效
⬜ A10 数值计算精度（网格分辨率、蒙特卡洛样本量）及其对结论稳定性的影响

> 写完在每条后面标 `[队员姓名缩写 日期]`，方便追溯是谁定的口径。

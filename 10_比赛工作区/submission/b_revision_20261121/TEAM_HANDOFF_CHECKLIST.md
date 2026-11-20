# B 题队员独立签收清单

状态为工程交接，队员独立推导、求解、解释、成稿和签收尚待完成。角色列只用于分工。正式论文与支撑材料保持匿名。

| 签收项 | 交接稿位置 | 具体待完成证据 | 可对照的文件 | 签收 |
|---|---|---|---|---|
| 总体建模 | Summary、Introduction、Assumptions、Cross-Problem Framework | 独立列出题设、假设、选择依据与跨问接口。自写摘要、关键词和正文。核对统一符号表里的角度约定、单位、下标和时间零点 | `paper/B_submission.tex`；Fig. 1 | [ ] |
| P1 观测域 | P1 Geometry | 独立定义车盘、闭棱柱视线与俯仰约束。证明等号归属、可行见证、最优半径及弧端归属。若主张唯一最快，须独立证明 | `paper/P1_ERRATA.pdf`；`P1_arc.csv`、`P1_ready_branches.csv`、`P1_station.csv` | [ ] |
| P1 路由与敏感性 | P1、Sensitivity Analysis | 校核圆角与保守矩形的 100/5 对照，明确图上绕路是可行上界、面积和连通性属于数值估计。复算 80°→79° 的变化分母 | `Route_clearance_comparison.csv`、`P1_pitch_checks.csv`、Fig. 2 | [ ] |
| P2(1) 站对 | P2 Localization | 独立推导角度雅可比、坐标协方差和下界取等。核对双车 30 s、两条有限视线、二维 RMS、椭圆适用范围与退化角 | `P2_precision.csv`、`P2_precision_routes.json`、Fig. 3 | [ ] |
| P2(2) 指派 | P2 Scheduling | 独立设计算法及复用时序。对照排名反转证据核对 k=3 与 k=8 的站位可用性和关键链，说明搜索范围 | `P2_trials.csv`、`P2_station_ranks.csv`、`P2_visit_phases.csv`、`P2_critical_chains.csv`、Fig. 4 | [ ] |
| P3 阈值 | P3 Error Propagation | 独立推导包角误差和连续最大性，检查高里程无二次可行段需要的条件，完成 80 m 参数范围与误差源解释。分列积分夹逼与三组抽样的用途 | `P3_bracket.csv`、`P3_MC.csv`、`P3_ablation.csv`、`P3_parameters.csv`、Fig. 5 | [ ] |
| P4 信息与时钟 | P4 Rescheduling | 独立说明扰动、绝对恢复、历时与末端。核对缓存全计划和仅当前任务两支，明确失效、动作取消、已开测锁定的含义 | `P4_clock_checks.json`、`P4_cases.csv`、`P4_instruction_sensitivity.csv`、Fig. 6 | [ ] |
| P4 V5 机理 | V5 Failure Case | 独立解释 T1 锁定、V1/V2/V4 取消回正和重指派、T2 成为末次开测，复算 3/3 与时间差 | `P4_V5_event_comparison.csv`、`Executed_timeline.json`、Fig. 7–8 | [ ] |
| 实验与结论 | Sensitivity Analysis、Strengths and Weaknesses、Conclusion | 由队员解释正负对照、重复场景和外推边界。逐条核对结论与自主结果，完成英文润色及相互复核 | `NUMBER_PROVENANCE.csv`、`FIGURE_SOURCES.csv`、`VERIFY_REPORT.md` | [ ] |
| 披露与引用 | References、AI Usage Disclosure | 核对历史原型和本轮台账，逐处记录真实采纳与人工修改。核阅候选文献原文，只将实际引用过的文献按出现顺序纳入 References | `paper/` 的文献索引、`AI_USAGE_LOG.csv`、官方 AI 规定第 1–8 条 | [ ] |
| 编译与提交 | 全文、三份独立文件 | 补齐独立作品后替换交接稿的 Author input pending 提示，使用同版脚本重跑 PDF QA。确认签名件签全并核查上传回执 | `REPRODUCE.md`、`RELEASE_ACCEPTANCE.json`、官方提交流程 | [ ] |

## 核对用数据摘录

- P1 主口径按就绪优先。并列提供纯到达时间的候选，避免把 2.397866 s 行车和 5.064533 s 就绪相混。一般绕路已逐段量净距，队员若主张连续最短需独立证书。
- P2(2) 共用到达筛选且束宽 20。k=8 时有两处被 k=3 拒绝的站，V1–T2 的到达序为 8，V2–T3 为 5。k=3 的 V3 先 T3 后 T1，累计等待约 1.063 s，k=8 的 V3 先 T1 后 T3，关键链上无等待。最近分配的关键车是 V5，两个 k 下同为 11.724422 s。把站位筛选和束内剪枝分别解释。
- P3 的数值交点约 66.837258 m。两侧各 200 万抽样用于验证阈值分侧；有限样本不负责给连续最大性证明。
- P4 的 V5 单故障比较中，T1 在 5 s 前成对开测。保留策略的最后开测由 T3 决定，重排策略改派 V3 后由 T2 决定。把取消回正耗时、改派就绪与官方首开测计分逐车核对。

队员最迟在北京时间 **2026-11-24 09:00** 锁定内容。平台正式提交最晚 **10:00**，由团队在队伍账号内核对并留存回执。只在工作区或私人组内处理未公开赛题成果。

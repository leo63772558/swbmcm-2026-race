# B 题项目审计

**结论：现有成果达到可复跑的研究原型水平。应优先补队员独立证据、统一 P1 与 P2/P4 口径、填齐结果到图表的接口。** 当前 PDF/ZIP 已具备技术交接条件，但正文末页明确写明模型与求解设计、解释和正文均有 AI 参与，独立参赛工作尚无可核验证据。实跑通过与竞赛合规是两个独立验收条件。

审计快照为北京时间 2026-11-21 约 02:50 开始，距 11-24 09:00 约 78 小时。题号 B。阶段为已有全链原型后的拆题、数值验证及改稿准备。工作根为 `10_比赛工作区/`。本次交付为本目录八件套。官方题面、历史包、签名文件及论文源稿保持原样。

## 1. 资料来源和版本

| 等级 | 核查对象 | 当前状态 |
|---|---|---|
| 1 | 赛题包 `B题/2026_“ShuWei Cup”B_Problem.pdf`，共 5 页 | 已读取并与转录对照。内置 Table 1、车位、告警、噪声、时钟等，无 B 专属附件；A 表或 C 数据不适用 |
| 1 | 官方原件中的格式规范、提交流程、AI 规定；[开赛公告](https://www.nmmcm.org.cn/News/225.html)与[赛题发布](https://www.nmmcm.org.cn/Awards/228.html) | 已回查：09:00 停止作答，10:00 最晚提交。公开竞赛入口能定位，队伍管理页需队员登录核对 |
| 2 | `data/B题题面参数.csv` 与 `data/B题题面-全文.txt` | PDF 提取文本有数学字形丢失。主要数值已与原始 PDF 比较。参数表把 P4 的冲突分别存为 `conflict`，无必要采购外部数据 |
| 3 | 队员独立推导、决策、实际运行和人工修改 | 本轮未定位具备来源记录的独立证据，队员可补交。此缺口不能用自动验收报告填平 |
| 4 | `src/` → `results/` → `figures/` 与候选 ZIP | 已核验目录、摘要、40 归档成员清单、两主件摘要、26 逐字节同一复现产物 |
| 5 | [p1.pdf](https://chatgpt.com/library?file_id=libfile_bc14e4b890808191962a55cb5240b040)、`B_submission.tex`、原型及当前候选，旧审计文档 | P1 独立研究文档约 10 页。部分数值只能追到 PDF，尤其细网格、路径图、敏感性表缺原脚本。候选稿与原型多个版本并存 |
| 6 | [粘贴的文本 (1).txt](https://chatgpt.com/library?file_id=libfile_6c54ee48087c8191b311fa156c86e229)、[仿真构图参考](https://chatgpt.com/library?file_id=libfile_51c94a9009188191a404a3753d03a849) | 已检查。方法候选、图样、工程工作量只能作参考，不能作参数、证明或结果 |

赛题包和官方原件中的提交说明、Word 模板、LaTeX ZIP 字节相同。格式规范两个版本 SHA 不同，第一条可见文本差异为第 2 条对首页模板名称的指向，首页/目录/页数要求在两版本中一致。使用开赛题包的当前说明与仓库裁决文件，内部页眉按 `Team#SWBMCM2613050`。现稿页眉是 `Team#BSWBMCM2613050`；官方材料中的示例有不同拼接方式，定稿前以队员核对的系统/已发布要求和项目选定版本统一。

### 现有正式命名物的冲突

| 版本目录（均为 submission 的子目录或本身） | 论文页数及 SHA 前缀 | ZIP 字节及成员 | 状态 |
|---|---|---|---|
| 根目录 | 12 / `731ac53d864f` | 608755 / 25 | 历史，不与新候选混配 |
| prototype | 11 / `20c7093f21a4` | 611023 / 25 | 历史 |
| prototype-evidence | 11 / `19012cb9082d` | 1779837 / 41 | 证据版；同 PDF 不同包 |
| prototype-handoff | 11 / `19012cb9082d` | 1780756 / 41 | 工作交接版 |
| prototype-refined | 11 / `19012cb9082d` | 1759974 / 32 | 同 PDF 过去的包 |
| submission-candidate | 11 / `db4c59919f5d` | 1772247 / 40 | 本次技术基线；仍需独立定稿 |

`paper/B_prototype.pdf` 同 handoff PDF。13 页 `B_prototype_preview.pdf` 是预览版本。当前候选 PDF 来源为 `paper/B_submission.tex`，候选 ZIP 只包含 `paper/main.tex`，故“26 文件可复跑”**不涵盖该候选 PDF 的源码重编译**。必要的编译源和日志应在队员正式定稿后成套保存。已签承诺书单独留存，本轮只核了命名和 PDF 字节大小，队员自行查三方签名和身份字段。

## 2. 文件与工程审计

| 类别 | 重要文件或分组 | 核查结论 |
|---|---|---|
| 控制 | 根 `AGENTS.md`、`00_指挥中心/AGENT_INSTRUCTIONS.md`、`PROGRESS.md`、开工指令两份 | 历史说明含静态资料口径，需以官方题面、当前版本和可运行实证覆盖 |
| 题面 | 5 页 B 题原件、结构化 CSV、全文转录 | 输入分为标称、推得、冲突。当前求解器直接读取转录 CSV，未发现从主结果 CSV 反读求解的设计 |
| 核心原型 | `problem_b_geometry.py`、`solve_problem_b.py` | 共用几何核、有缓存、无额外大型依赖。LOS slab 与车体欧氏距与题意一致至浮点容差。路径由保守矩形路网构成。路线函数本身未显式检查场界端点，正常调用的静态候选在场域内，P4 由合法路径插值；保护公开接口可作为工程工单 |
| 复核 | `check_problem_b.py`、P2 fairness、P3 margin、P4 cross/replay、历史 review evidence | 两套名义方案、28 配对、45 交叉、P3 5 点均已实跑。大量检查共用几何核。所谓独立在部分情况下是评分或实现路径不同，不能保证输入/几何独立 |
| 结果 | P1 和 T2 各 1 行、P2 两策略 12 行、fairness 8、P3 曲线 61、P4 56、cross 90、replay 70、validation 7；两时间线 JSON | 重要数值在 CSV。P1 的面积和连续圆弧证书没有当前同源 CSV。P2 不同预算重算具有对照意义，不能混同为同一轨迹 |
| 出图 | `plot_problem_b.py`、`render_problem_b.py`、六张 PDF/PNG、总览图 | 现代风格已成型。字体、尺寸和图面有效，但 P1、P4 的证据表达尚不完整。实时画面尚无实现 |
| 论文 | `main.tex`、`B_prototype.tex`、`B_submission.tex`、`B_reproduce.md` | 渲染脚本可生成原型正文。团队正式稿须独立。保留布局技术和引用框架可降低工程返工 |
| 打包 | `package_problem_b.py`、`verify_handoff.py`、各阶段清单 | 复跑可接受。现有 README 说明初步齐全；必须修清正式 TeX 与复跑产物的对应信息 |
| 日志 | `B_评审证据核对.md/.csv`、候选清单、验收报告、历史渲染日志 | 同一条审计文档混了历史分支和现行计划。V5 单故障变差为当前 1.893 s、历史 3.961 s，后者不能合并进当前主文。未发现 p1.pdf 的配套原始日志 |
| 环境 | `13_环境备份/requirements.txt`、本机 Python、ReportLab/Pillow/pypdf、Poppler、Tectonic | 实际 Python 3.14.7，候选结果环境记录良好。通用依赖表偏大。当前 Python 的 PDF 专用工具缺 PyMuPDF，需与已有出图环境分别记录 |

**结果追踪方式。** 正式稿中每一数字建立键到行的对应表，至少包括数字名、配置/策略、输入哈希、输出文件与字段、生成程序版本、单位与舍入。代码变动时先保存独立版本目录和指纹，再在新目录执行，避免 `render_problem_b.py` 生成产物覆盖历史。测试区分解析可行性、边界夹具、数据一致性与完整复现四类。

## 3. 数学与统计问题

| 等级 | 位置 | 原结论与问题 |
|---|---|---|
| P0 | `p1.pdf` p.2 A4、p.5 Table 3、p.9 | 集合闭性误判、分支最小值自相矛盾和 1.5%/° 误述，见 [P1 专项](P1_REVIEW.md) |
| P0 | `B_submission.tex` pp.4、10 对应 `check_problem_b.py:51` | 一阶 RMS 与测试样本 RMS 口径必须严格区分。无截断高斯下角差的密度延伸到交点分母接近零的位置。有限样本一致性不能证明未截断交会的二阶矩 |
| P0 | `solve_problem_b.py:240–338` 与题面 p.5 | 恢复状态用完整缓存假设推进。失联后仍启动已缓存任务会改变锁定集合。失败配对的继续等待/回零、重调度恢复同刻、0–60 窗口须裁决。现有页面只能支持这组假设下的结果 |
| P1 | `solve_problem_b.py:120–179`、`B_P2_fairness.csv` | 优化与基线原筛选不同，补充公平对照可复跑。固定预算 k=8 领先、k=3 排名反转。现有属于有限候选可行上界；未见当前基线匹配的连续证书 |
| P1 | `solve_problem_b.py:181–237`、`B_P3.csv` | 二重 Simpson、条件 CDF、包角，64/128 得同报数。bisection 最大性需单调或全域论证；一阶分量归因别当成精确贡献。水平横向误差正负与导出公式口径需一致 |
| P1 | P4 实验矩阵与图 | 已覆盖单、组合和五辆故障车。45 对仍是三位置的网格，公式与文字时钟混入时只能按分支比较。历史分支未经同口径回溯，须明确名义计划身份 |
| P1 | 源码导出 | P4 轨迹 JSON 里名义在途段不是实际执行事件的完整日志，尤其失败车辆取消和回零姿态。独立回放应能复原名义/新计划、实际事件和未执行的区别 |
| P2 | 披露与程序注释 | 末页真实标注主要 AI 作用。现有程式注释的模型标识和版本发布日期完整性不足，正式参考文献及正文对应标注需逐项对照官方 §§3、5–8 |

## 图表审查

已逐张目审候选同版的六张图。现有低饱和配色、统一衬线字体、矢量导出可继承。选择终稿插图时在实际印刷宽度检验最小图例，保证深浅/线型在灰度也可辨。每张图建立结果行、假设和目的的映射。

| 图 | 已有证据与问题 | 处理、来源与解释 |
|---|---|---|
| b_geometry | 1 m 栅格轮廓及 T2 小图都挤在一图；最优点有，圆角/阴影/俯仰层与全弧缺 | **重做为 P1、P2(1) 两图**。P1 来自验收后的三约束与统计数据，B2 局部说明哪条边截断；T2 用 B_P2_localization 和轨迹，配双站边界、角、基线及可选椭圆。明确落在俯仰上限 |
| b_routes | 色线和点一致，原点/站点对比好，但只展示名义计划，短路线难辨 | 保留总图样式，补最近基线小面板和关键车局部框。读取 B_timelines JSON，同站复用明确标为 0 m |
| b_timeline | 两策略五车时间轴、阶段图例易读，启动点标清；复用原因没见于主图 | 保留。用 B_P2_schedules 同版绘制，增加一条引出线说明关键车辆的等待与复位。公平筛选对照另出小表并指明配置 |
| b_coverage | 曲线与两点范围，阈值边眼睛难读，题意关心 80 m | **改为双面板**，左全域覆盖，右阈值前后放大。读取 B_P3_coverage、B_P3_margin、B_validation，把完整 Wilson 区间标清，80 m 给独立标注 |
| b_parameters | 三角区域、轴范围与单位清楚，标称点和可行距离的解释不明显 | 保留简洁结构，叠加标称参数点、80 m 界线标签和截距，数值取 B_P3 与官方 CSV。若图足够，贡献比例独立小表 |
| b_disturbances | 图分完成率与时间，星号提醒 60 s 截尾。单幅只选代表行，不显示恢复过程 | **保留为摘要图，补两幅关键证据**：匹配情景小矩阵和单组事件双甘特。从 B_P4、cross、replay、JSON 读数。一个组合收益加一个 V5 变差或持平，明确不同颜色的含义。只在全完成配对讨论净时间差 |

图统一用 m、s、°、m⁻¹，2D 地图等轴。建议一组机制主色配每任务图案/线型，建筑浅灰，遮挡虚线，恢复时间竖线，失败深红。使用 [仿真构思图](https://chatgpt.com/library?file_id=libfile_51c94a9009188191a404a3753d03a849) 的分屏思想，将视觉密度放到结果和事件。避免把外部图中的诸如行人、多模态感知或城市纹理当作赛题数据。

## 4. 论文与提交项目

- **已通过基础结构检查。** 11 页 A4，首页无页眉且有摘要与关键词，第二页 Content，正文第三页开始。从 2 到 11 页的计页连续，分图在下、表题在上。PDF 无附件，元数据作者为空，无模板占位符。渲染预览未见空白页或大处溢出。正文 Times New Roman，公式使用 Computer Modern 子集，须按本项目严格字体口径在终稿核对兼容版式及 12 pt。候选稿 p.7 内容较少，p.1 与 p.11 留白大，p.9 表较密。
- **缺的研究内容。** 现有正文第 3 页直接进入 P1，缺简要 Introduction、问题树、假设和符号汇总；核心公式未连续编号；P1 的独立弧证书、P2 基线贡献、P3 阈值与分量区间、P4 逐事件解释未形成完整证据段，缺独立结论及集中敏感性。对四问写清原题给定、建模假设、结果有效范围。团队选择适当页数，不要求写满 25 页。
- **参考文献。** 本轮直接 DOI 成功打开 Dijkstra 和 BIPM JCGM；其余 DOI 入口有检索抓取限制，队员应核对原出版社或存档；引用顺序、书籍页码、AI 条目和对应段逐项确认。保留代码来源与匿名性。文件名、ZIP 成员、作者身份与签名分别审核。
- **提交。** 论文 `BSWBMCM2613050.pdf`，承诺书 `BSWBMCM2613050cns.pdf` 或 JPG/PNG，支撑 `BSWBMCM2613050fj.zip` 或 RAR，分别按 <20 MB 的项目口径。支撑材料本可选，但使用代码时须保证全部所用可运行源码能按规定从附录或支撑取得。AI 报告放正文末或参考文献后，不计正文上限。系统点击提交并看到已提交；系统与备用邮箱择一。详见[官方提交流程](https://www.nmmcm.org.cn/News/222.html)。
- **截止核验。** [官方开赛公告](https://www.nmmcm.org.cn/static/upload/file/20261119/1795079874140244.pdf)明确 09:00 停止作答、10:00 关闭系统与备用邮箱。早版提交流程写 10:00 结束，赛时照较晚发布公告执行。已查看[官方系统入口](https://www.mojinghub.com/competitions/swbmcm/2026)的公开页面；登录报名账号内的提交页和时钟由队员确认。

## 5. 十项验收结论

| 问题 | 审计答复 |
|---|---|
| 当前水平 | 可复跑、排版清楚的全链研究原型。核心论证和成果来源未到可参评状态 |
| 已完成 | 题面转录，P1 候选，P2 T2 一阶站对，双政策名义排程，P3 阈值实验，28+45 配对 P4，六张矢量图及 11 页候选包 |
| 主要漏洞 | P1 相切拓扑和表内矛盾，P2 误差指标和配置反转，P4 双时钟与断联状态语义，AI 核心来源 |
| 先投时间 | 队员独立推导/求解与假设确认，P1 边界，P2 同口径证据，P4 可重放事件，然后 P3 证书 |
| 统一框架 | 公共几何＋P2(2)→P4 已成链；P2(1)、P3 是独立模块及可选诊断 |
| COMSOL | 暂不用。缺可校准的连续场科学问题 |
| 仿真系统 | 基于真实 CSV/JSON 与规则校验的 Python 事件回放，三维展示用 Plotly。优先三种可说明机制的真实案例 |
| 图表 | 重做 P1/P2 几何和 P3 覆盖；为 P4 补情景矩阵和逐车事件；保留路线、甘特、参数域的视觉基底 |
| 论文 | 缺独立作者证据、各问证书、说明书、符号、图表数字映射和术语统一；末页披露需与最终事实一致 |
| 离最终作品 | 先把数学与真实结果关闭，再做图文、同源编译、可复跑支撑材料和队员系统核验 |

## 附录：第一轮文件清单

以下是项目内可见常规文件的递归清单，以路径为键，供查重和交接。赛题包、竞赛工作区、已编号各工作区完整列路径。工具、构建缓存和签名缓存不展开，外部资料库未遍历。此列表在报告创建后生成，排除本轮交付目录和隐式工具目录。


<details>
<summary>展开文件清单</summary>

- `AGENTS.md`
- `README.md`
- `00_指挥中心/AGENT_INSTRUCTIONS.md`
- `00_指挥中心/B题-开工指令-2026-11-20.md`
- `00_指挥中心/B题开工指令-v2-仓库版-2026-11-20.md`
- `00_指挥中心/PROGRESS.md`
- `00_指挥中心/README.md`
- `00_指挥中心/TODO.md`
- `00_指挥中心/quickstart_competition.py`
- `00_指挥中心/三人协同作战流水线与防崩盘SOP.md`
- `00_指挥中心/两库全库体检报告-2026-11-06.md`
- `00_指挥中心/参赛须知-队友版.md`
- `00_指挥中心/双赛口径对照表.md`
- `00_指挥中心/双赛合并作战日历.md`
- `00_指挥中心/双赛连打45小时黄金转场与防查重指南.md`
- `00_指挥中心/特等奖得分核心策略.md`
- `00_指挥中心/赛时外部权威数据检索与急救库.md`
- `00_指挥中心/赛时开场指令.md`
- `00_指挥中心/选题决策协议.md`
- `01_官方规则/2026-11-17官方二批文件核验与冲突裁决.md`
- `01_官方规则/RULES_VERIFIED.md`
- `01_官方规则/SUBMISSION_CHECKLIST.md`
- `01_官方规则/论文格式规范与Word模板-核验整理.md`
- `01_官方规则/官方原件/2026年第十二届数维杯全国大学生数学建模挑战赛(秋季赛）参赛规则.pdf`
- `01_官方规则/官方原件/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）LaTeX模版.zip`
- `01_官方规则/官方原件/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）Word模版.docx`
- `01_官方规则/官方原件/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）论文提交流程.pdf`
- `01_官方规则/官方原件/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）论文格式规范.pdf`
- `01_官方规则/官方原件/2026第十二届数维杯全国大学生数学建模挑战赛（秋季赛）参赛白皮书.pdf`
- `01_官方规则/官方原件/数维杯全国大学生数学建模挑战赛人工智能工具使用规定（2026年修订）.pdf`
- `01_官方规则/官方原件/数维杯全国大学生数学建模挑战赛章程（2026年9月修订）.pdf`
- `01_官方规则/官方原件/参考类_报名与组织/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）报名流程.pdf`
- `01_官方规则/官方原件/参考类_报名与组织/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）报名通知.pdf`
- `01_官方规则/官方原件/参考类_报名与组织/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）集体报名表.xlsx`
- `01_官方规则/官方原件/参考类_报名与组织/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）集体报名通知.pdf`
- `01_官方规则/官方原件/参考类_报名与组织/数维杯全国大学生数学建模挑战赛全国专家委员会成员名单.pdf`
- `01_官方规则/官方原件/参考类_报名与组织/数维杯全国大学生数学建模挑战赛全国组织委员会成员名单.pdf`
- `01_官方规则/官方原件/官方LaTeX模版_解压/demo.pdf`
- `01_官方规则/官方原件/官方LaTeX模版_解压/demo.tex`
- `01_官方规则/官方原件/官方LaTeX模版_解压/swmcmthesis.cfg`
- `01_官方规则/官方原件/官方LaTeX模版_解压/swmcmthesis.cls`
- `01_官方规则/官方原件/官方LaTeX模版_解压/figures/cat.pdf`
- `01_官方规则/官方原件/官方LaTeX模版_解压/figures/gongzhonghao-n.jpg`
- `02_资料索引/GitHub开源资源评估.md`
- `02_资料索引/SOURCE_OVERVIEW.md`
- `02_资料索引/build_source_index.py`
- `02_资料索引/source_index.csv`
- `03_论文分析/ANALYSIS_TEMPLATE.md`
- `03_论文分析/DEEP_DIVE_A2024.md`
- `03_论文分析/DEEP_DIVE_C2024.md`
- `03_论文分析/METHOD_USAGE.md`
- `03_论文分析/PAPER_PROFILE.md`
- `03_论文分析/README.md`
- `03_论文分析/build_paper_index.py`
- `03_论文分析/method_usage.py`
- `03_论文分析/paper_index.csv`
- `03_论文分析/text/A202111107503.txt`
- `03_论文分析/text/A2022111313915.txt`
- `03_论文分析/text/A2022111514103.txt`
- `03_论文分析/text/A2024100229348.txt`
- `03_论文分析/text/A2024110230228.txt`
- `03_论文分析/text/A2024110430327.txt`
- `03_论文分析/text/A2024111130784.txt`
- `03_论文分析/text/B202111036817.txt`
- `03_论文分析/text/B202111046836.txt`
- `03_论文分析/text/B202111077005.txt`
- `03_论文分析/text/B202111087164.txt`
- `03_论文分析/text/B202111097271.txt`
- `03_论文分析/text/B202111097411.txt`
- `03_论文分析/text/B202111107683.txt`
- `03_论文分析/text/B2022101312870.txt`
- `03_论文分析/text/B2022110613530.txt`
- `03_论文分析/text/B2022111013803.txt`
- `03_论文分析/text/B2024093029322.txt`
- `03_论文分析/text/B2024093029335.txt`
- `03_论文分析/text/B2024100129342.txt`
- `03_论文分析/text/B2024101029505.txt`
- `03_论文分析/text/C202110076198.txt`
- `03_论文分析/text/C202110286549.txt`
- `03_论文分析/text/C202111046833.txt`
- `03_论文分析/text/C202111046885.txt`
- `03_论文分析/text/C202111087175.txt`
- `03_论文分析/text/C2022110513494.txt`
- `03_论文分析/text/C2022110913725.txt`
- `03_论文分析/text/C2022111213875.txt`
- `03_论文分析/text/C2022111514190.txt`
- `03_论文分析/text/C2022111614350.txt`
- `03_论文分析/text/C2024092929266.txt`
- `03_论文分析/text/C2024101629647.txt`
- `03_论文分析/text/C2024110530377.txt`
- `03_论文分析/text/C2024110930663.txt`
- `03_论文分析/text/D202109256115.txt`
- `03_论文分析/text/D202111026764.txt`
- `03_论文分析/text/D202111056924.txt`
- `03_论文分析/text/D2022092812658.txt`
- `03_论文分析/text/D2022101212848.txt`
- `03_论文分析/text/D2022103113305.txt`
- `03_论文分析/text/D2022110713591.txt`
- `03_论文分析/text/D2022111313961.txt`
- `03_论文分析/text/D2022111414030.txt`
- `03_论文分析/text/D2024091329034.txt`
- `03_论文分析/text/D2024110230221.txt`
- `03_论文分析/text/D2024110430340.txt`
- `03_论文分析/text/D2024111231024.txt`
- `04_数学建模知识库/01_建模全流程与论文骨架.md`
- `04_数学建模知识库/02_数据预处理与EDA.md`
- `04_数学建模知识库/03_回归与曲线拟合.md`
- `04_数学建模知识库/04_时间序列预测.md`
- `04_数学建模知识库/05_分类与聚类.md`
- `04_数学建模知识库/06_评价类模型.md`
- `04_数学建模知识库/07_优化模型.md`
- `04_数学建模知识库/08_图论与路径规划.md`
- `04_数学建模知识库/09_蒙特卡洛与仿真.md`
- `04_数学建模知识库/10_微分方程与动力学.md`
- `04_数学建模知识库/11_统计检验与不确定性.md`
- `04_数学建模知识库/12_验证_灵敏度_稳健性.md`
- `04_数学建模知识库/13_模型选择决策系统.md`
- `04_数学建模知识库/14_常见失败模式.md`
- `04_数学建模知识库/README.md`
- `05_Agent技能库/SKILL_VALIDATION.md`
- `05_Agent技能库/validate_skills.py`
- `05_Agent技能库/academic-visualization/SKILL.md`
- `05_Agent技能库/competition-rule-audit/SKILL.md`
- `05_Agent技能库/data-analysis/SKILL.md`
- `05_Agent技能库/drawio-figures/SKILL.md`
- `05_Agent技能库/english-academic-writing/SKILL.md`
- `05_Agent技能库/figure-templates/SKILL.md`
- `05_Agent技能库/figure-templates/assets/previews/correlation_pairgrid_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/cv_roc_ci_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/grouped_circular_heatmap_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/grouped_corr_split_violin_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/multiclass_shap_combo_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/nature_chord_diagram_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/paired_raincloud_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/prediction_marginal_grid_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/rf_tpe_surface_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/taylor_diagram_replica.png`
- `05_Agent技能库/figure-templates/assets/previews/urban_park_cooling_combo_replica.png`
- `05_Agent技能库/figure-templates/references/figure-catalog.md`
- `05_Agent技能库/figure-templates/references/plot-recipes.md`
- `05_Agent技能库/figure-templates/scripts/render_template.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_correlation_pairgrid.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_cv_roc_ci.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_grouped_circular_heatmap.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_grouped_corr_split_violin.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_multiclass_shap_combo.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_nature_chord_diagram.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_paired_raincloud.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_prediction_marginal_grid.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_rf_tpe_surface.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_taylor_diagram.py`
- `05_Agent技能库/figure-templates/scripts/templates/make_urban_park_cooling_combo.py`
- `05_Agent技能库/final-paper-review/SKILL.md`
- `05_Agent技能库/literature-review/SKILL.md`
- `05_Agent技能库/mathematical-modeling/SKILL.md`
- `05_Agent技能库/model-selector/SKILL.md`
- `05_Agent技能库/model-validation/SKILL.md`
- `05_Agent技能库/paper-typesetting/SKILL.md`
- `05_Agent技能库/pdf-visual-qa/SKILL.md`
- `05_Agent技能库/python-modeling/SKILL.md`
- `06_Python代码工具箱/run_tests.py`
- `06_Python代码工具箱/mmkit/__init__.py`
- `06_Python代码工具箱/mmkit/classify.py`
- `06_Python代码工具箱/mmkit/cluster.py`
- `06_Python代码工具箱/mmkit/data.py`
- `06_Python代码工具箱/mmkit/demo.py`
- `06_Python代码工具箱/mmkit/dynamics.py`
- `06_Python代码工具箱/mmkit/evaluate.py`
- `06_Python代码工具箱/mmkit/graph.py`
- `06_Python代码工具箱/mmkit/optimize.py`
- `06_Python代码工具箱/mmkit/regression.py`
- `06_Python代码工具箱/mmkit/simulate.py`
- `06_Python代码工具箱/mmkit/stats.py`
- `06_Python代码工具箱/mmkit/timeseries.py`
- `06_Python代码工具箱/mmkit/viz.py`
- `06_Python代码工具箱/tests/test_all.py`
- `07_英文论文工坊/README.md`
- `07_英文论文工坊/guidelines/ENGLISH_PHRASEBOOK.md`
- `07_英文论文工坊/guidelines/PAPER_STRUCTURE.md`
- `07_英文论文工坊/guidelines/TOOLS_AND_LICENSES.md`
- `07_英文论文工坊/guidelines/VISUAL_SPEC.md`
- `07_英文论文工坊/sample_paper/paper_sample.pdf`
- `07_英文论文工坊/templates/latex/build.sh`
- `07_英文论文工坊/templates/latex/main.tex`
- `07_英文论文工坊/templates/latex/preamble.tex`
- `07_英文论文工坊/templates/latex/swbmcm_refs.bib`
- `07_英文论文工坊/templates/latex/build/bibtex.log`
- `07_英文论文工坊/templates/latex/build/latex_run.log`
- `07_英文论文工坊/templates/latex/build/main.aux`
- `07_英文论文工坊/templates/latex/build/main.bbl`
- `07_英文论文工坊/templates/latex/build/main.blg`
- `07_英文论文工坊/templates/latex/build/main.log`
- `07_英文论文工坊/templates/latex/build/main.out`
- `07_英文论文工坊/templates/latex/build/main.pdf`
- `07_英文论文工坊/templates/latex/build/main.toc`
- `07_英文论文工坊/templates/latex/figures/03_regression_residual.pdf`
- `07_英文论文工坊/templates/latex/figures/07_parameter_sensitivity.pdf`
- `07_英文论文工坊/templates/latex/figures/10_modelling_workflow.pdf`
- `07_英文论文工坊/templates/latex/figures/12_topsis_ranking.pdf`
- `07_英文论文工坊/templates/latex/sections/abstract.tex`
- `07_英文论文工坊/templates/latex/sections/appendix.tex`
- `07_英文论文工坊/templates/latex/sections/body.tex`
- `08_科研可视化/MANIFEST.csv`
- `08_科研可视化/README.md`
- `08_科研可视化/make_gallery.py`
- `08_科研可视化/data/demo_cities.csv`
- `08_科研可视化/data/demo_housing.csv`
- `08_科研可视化/data/demo_model_comparison.csv`
- `08_科研可视化/data/demo_monthly_sales.csv`
- `08_科研可视化/data/demo_sensitivity.csv`
- `08_科研可视化/data/demo_topsis.csv`
- `08_科研可视化/data/demo_weights.csv`
- `08_科研可视化/figures/01_price_distribution.pdf`
- `08_科研可视化/figures/01_price_distribution.png`
- `08_科研可视化/figures/01_price_distribution.svg`
- `08_科研可视化/figures/02_correlation_heatmap.pdf`
- `08_科研可视化/figures/02_correlation_heatmap.png`
- `08_科研可视化/figures/02_correlation_heatmap.svg`
- `08_科研可视化/figures/03_regression_residual.pdf`
- `08_科研可视化/figures/03_regression_residual.png`
- `08_科研可视化/figures/03_regression_residual.svg`
- `08_科研可视化/figures/04_forecast_with_interval.pdf`
- `08_科研可视化/figures/04_forecast_with_interval.png`
- `08_科研可视化/figures/04_forecast_with_interval.svg`
- `08_科研可视化/figures/05_prediction_interval.pdf`
- `08_科研可视化/figures/05_prediction_interval.png`
- `08_科研可视化/figures/05_prediction_interval.svg`
- `08_科研可视化/figures/06_algorithm_convergence.pdf`
- `08_科研可视化/figures/06_algorithm_convergence.png`
- `08_科研可视化/figures/06_algorithm_convergence.svg`
- `08_科研可视化/figures/07_parameter_sensitivity.pdf`
- `08_科研可视化/figures/07_parameter_sensitivity.png`
- `08_科研可视化/figures/07_parameter_sensitivity.svg`
- `08_科研可视化/figures/08_model_comparison.pdf`
- `08_科研可视化/figures/08_model_comparison.png`
- `08_科研可视化/figures/08_model_comparison.svg`
- `08_科研可视化/figures/09_network_shortest_path.pdf`
- `08_科研可视化/figures/09_network_shortest_path.png`
- `08_科研可视化/figures/09_network_shortest_path.svg`
- `08_科研可视化/figures/10_modelling_workflow.pdf`
- `08_科研可视化/figures/10_modelling_workflow.png`
- `08_科研可视化/figures/10_modelling_workflow.svg`
- `08_科研可视化/figures/11_simulation_cdf.pdf`
- `08_科研可视化/figures/11_simulation_cdf.png`
- `08_科研可视化/figures/11_simulation_cdf.svg`
- `08_科研可视化/figures/12_topsis_ranking.pdf`
- `08_科研可视化/figures/12_topsis_ranking.png`
- `08_科研可视化/figures/12_topsis_ranking.svg`
- `09_模拟训练/MOCK_PLAN.md`
- `09_模拟训练/REVIEW_TEMPLATE.md`
- `09_模拟训练/mock_01/BRIEF.md`
- `09_模拟训练/mock_01/REVIEW.md`
- `09_模拟训练/mock_01/data/county.csv`
- `09_模拟训练/mock_01/data/demand.csv`
- `09_模拟训练/mock_01/data/depot.csv`
- `09_模拟训练/mock_01/data/network.csv`
- `09_模拟训练/mock_01/figures/fig_mc_convergence.pdf`
- `09_模拟训练/mock_01/figures/fig_sensitivity_rate.pdf`
- `09_模拟训练/mock_01/figures/fig_task1_forecast.pdf`
- `09_模拟训练/mock_01/figures/fig_task1_interval.pdf`
- `09_模拟训练/mock_01/figures/fig_task2_cost_structure.pdf`
- `09_模拟训练/mock_01/figures/fig_task3_county_risk.pdf`
- `09_模拟训练/mock_01/figures/fig_task3_service_level.pdf`
- `09_模拟训练/mock_01/figures/fig_task4_ranking.pdf`
- `09_模拟训练/mock_01/figures/fig_task5_marginal_value.pdf`
- `09_模拟训练/mock_01/figures/_legacy/task1_forecast_comparison.pdf`
- `09_模拟训练/mock_01/figures/_legacy/task1_forecast_comparison.png`
- `09_模拟训练/mock_01/figures/_legacy/task4_vulnerability_top10.pdf`
- `09_模拟训练/mock_01/figures/_legacy/task4_vulnerability_top10.png`
- `09_模拟训练/mock_01/paper/MOCK_only_ASWBMCM2613050.pdf`
- `09_模拟训练/mock_01/paper/README.md`
- `09_模拟训练/mock_01/paper/build_paper.sh`
- `09_模拟训练/mock_01/paper/main.bbl`
- `09_模拟训练/mock_01/paper/main.tex`
- `09_模拟训练/mock_01/paper/preamble.tex`
- `09_模拟训练/mock_01/paper/refs.bib`
- `09_模拟训练/mock_01/paper/qa/PDF_QA_REPORT.md`
- `09_模拟训练/mock_01/paper/qa/pages/page-01.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-02.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-03.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-04.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-05.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-06.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-07.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-08.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-09.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-10.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-11.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-12.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-13.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-14.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-15.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-16.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-17.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-18.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-19.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-20.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-21.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-22.png`
- `09_模拟训练/mock_01/paper/qa/pages/page-23.png`
- `09_模拟训练/mock_01/paper/sections/abstract.tex`
- `09_模拟训练/mock_01/paper/sections/appendix.tex`
- `09_模拟训练/mock_01/paper/sections/body.tex`
- `09_模拟训练/mock_01/results/run_log.json`
- `09_模拟训练/mock_01/results/sensitivity_mc_convergence.csv`
- `09_模拟训练/mock_01/results/sensitivity_transport_rate.csv`
- `09_模拟训练/mock_01/results/summary.json`
- `09_模拟训练/mock_01/results/task1_cv_predictions.csv`
- `09_模拟训练/mock_01/results/task1_forecast_12m.csv`
- `09_模拟训练/mock_01/results/task1_forecast_interval.csv`
- `09_模拟训练/mock_01/results/task1_model_comparison.csv`
- `09_模拟训练/mock_01/results/task2_flow_detail.csv`
- `09_模拟训练/mock_01/results/task2_monthly_plan.csv`
- `09_模拟训练/mock_01/results/task3_county_path_risk.csv`
- `09_模拟训练/mock_01/results/task3_plan_comparison.csv`
- `09_模拟训练/mock_01/results/task4_rank_stability.csv`
- `09_模拟训练/mock_01/results/task4_vulnerability_ranking.csv`
- `09_模拟训练/mock_01/results/task4_weights.csv`
- `09_模拟训练/mock_01/results/task5_reinforcement_curve.csv`
- `09_模拟训练/mock_01/results/task5_selected_edges.csv`
- `09_模拟训练/mock_01/results/_legacy/task1_eval_metrics.csv`
- `09_模拟训练/mock_01/src/make_synthetic.py`
- `09_模拟训练/mock_01/src/run_all.py`
- `09_模拟训练/mock_01/src/solution_baseline.py`
- `10_比赛工作区/README.md`
- `10_比赛工作区/data/B题题面-全文.txt`
- `10_比赛工作区/data/B题题面参数.csv`
- `10_比赛工作区/figures/B_figure_overview.png`
- `10_比赛工作区/figures/b_coverage.pdf`
- `10_比赛工作区/figures/b_coverage.png`
- `10_比赛工作区/figures/b_disturbances.pdf`
- `10_比赛工作区/figures/b_disturbances.png`
- `10_比赛工作区/figures/b_geometry.pdf`
- `10_比赛工作区/figures/b_geometry.png`
- `10_比赛工作区/figures/b_parameters.pdf`
- `10_比赛工作区/figures/b_parameters.png`
- `10_比赛工作区/figures/b_routes.pdf`
- `10_比赛工作区/figures/b_routes.png`
- `10_比赛工作区/figures/b_timeline.pdf`
- `10_比赛工作区/figures/b_timeline.png`
- `10_比赛工作区/paper/B_prototype.pdf`
- `10_比赛工作区/paper/B_prototype.tex`
- `10_比赛工作区/paper/B_prototype_preview.pdf`
- `10_比赛工作区/paper/B_reproduce.md`
- `10_比赛工作区/paper/B_submission.tex`
- `10_比赛工作区/paper/main.tex`
- `10_比赛工作区/results/B_P1.csv`
- `10_比赛工作区/results/B_P2_fairness.csv`
- `10_比赛工作区/results/B_P2_localization.csv`
- `10_比赛工作区/results/B_P2_schedules.csv`
- `10_比赛工作区/results/B_P3.csv`
- `10_比赛工作区/results/B_P3_coverage.csv`
- `10_比赛工作区/results/B_P3_margin.csv`
- `10_比赛工作区/results/B_P4.csv`
- `10_比赛工作区/results/B_P4_cross.csv`
- `10_比赛工作区/results/B_P4_cross_timelines.json`
- `10_比赛工作区/results/B_P4_replay.csv`
- `10_比赛工作区/results/B_timelines.json`
- `10_比赛工作区/results/B_validation.csv`
- `10_比赛工作区/results/B_评审证据核对.csv`
- `10_比赛工作区/results/B_评审证据核对.md`
- `10_比赛工作区/results/B题拆题.md`
- `10_比赛工作区/results/notes.md`
- `10_比赛工作区/src/check_b_p2_fairness.py`
- `10_比赛工作区/src/check_b_p3_margin.py`
- `10_比赛工作区/src/check_b_p4_cross.py`
- `10_比赛工作区/src/check_b_p4_replay.py`
- `10_比赛工作区/src/check_b_review_evidence.py`
- `10_比赛工作区/src/check_problem_b.py`
- `10_比赛工作区/src/package_problem_b.py`
- `10_比赛工作区/src/plot_problem_b.py`
- `10_比赛工作区/src/problem_b_geometry.py`
- `10_比赛工作区/src/render_problem_b.py`
- `10_比赛工作区/src/solve_problem_b.py`
- `10_比赛工作区/src/verify_handoff.py`
- `10_比赛工作区/submission/BSWBMCM2613050.pdf`
- `10_比赛工作区/submission/BSWBMCM2613050cns-signed.docx`
- `10_比赛工作区/submission/BSWBMCM2613050cns.docx`
- `10_比赛工作区/submission/BSWBMCM2613050cns.pdf`
- `10_比赛工作区/submission/BSWBMCM2613050fj.zip`
- `10_比赛工作区/submission/B题交接清单.md`
- `10_比赛工作区/submission/RUN_MANIFEST.json`
- `10_比赛工作区/submission/VERIFY_REPORT.md`
- `10_比赛工作区/submission/prototype/BSWBMCM2613050.pdf`
- `10_比赛工作区/submission/prototype/BSWBMCM2613050fj.zip`
- `10_比赛工作区/submission/prototype-evidence/BSWBMCM2613050.pdf`
- `10_比赛工作区/submission/prototype-evidence/BSWBMCM2613050fj.zip`
- `10_比赛工作区/submission/prototype-evidence/RUN_MANIFEST.json`
- `10_比赛工作区/submission/prototype-evidence/VERIFY_REPORT.md`
- `10_比赛工作区/submission/prototype-handoff/BSWBMCM2613050.pdf`
- `10_比赛工作区/submission/prototype-handoff/BSWBMCM2613050fj.zip`
- `10_比赛工作区/submission/prototype-handoff/RUN_MANIFEST.json`
- `10_比赛工作区/submission/prototype-handoff/VERIFY_REPORT.md`
- `10_比赛工作区/submission/prototype-refined/BSWBMCM2613050.pdf`
- `10_比赛工作区/submission/prototype-refined/BSWBMCM2613050fj.zip`
- `10_比赛工作区/submission/submission-candidate/BSWBMCM2613050.pdf`
- `10_比赛工作区/submission/submission-candidate/BSWBMCM2613050fj.zip`
- `10_比赛工作区/submission/submission-candidate/RUN_MANIFEST.json`
- `10_比赛工作区/submission/submission-candidate/VERIFY_REPORT.md`
- `10_比赛工作区/templates/README.md`
- `10_比赛工作区/templates/SWBMCM2613050_论文模板_已清洗_全篇A4.docx`
- `10_比赛工作区/templates/SWBMCM2613050_论文模板_已清洗_官方版式.docx`
- `10_比赛工作区/templates/build_clean_template.py`
- `11_质量检查/README.md`
- `11_质量检查/reports/test_report.md`
- `11_质量检查/reports/negative_test/bad_sample.pdf`
- `11_质量检查/reports/negative_test/qa/PDF_QA_REPORT.md`
- `11_质量检查/reports/negative_test/qa/pages/page-01.png`
- `11_质量检查/reports/negative_test/qa/pages/page-02.png`
- `11_质量检查/reports/negative_test/qa/pages/page-03.png`
- `11_质量检查/reports/pdf_qa/PDF_QA_REPORT.md`
- `11_质量检查/reports/pdf_qa/pages/page-01.png`
- `11_质量检查/reports/pdf_qa/pages/page-02.png`
- `11_质量检查/reports/pdf_qa/pages/page-03.png`
- `11_质量检查/reports/pdf_qa/pages/page-04.png`
- `11_质量检查/reports/pdf_qa/pages/page-05.png`
- `11_质量检查/reports/pdf_qa/pages/page-06.png`
- `11_质量检查/reports/pdf_qa/pages/page-07.png`
- `11_质量检查/reports/pdf_qa/pages/page-08.png`
- `11_质量检查/reports/pdf_qa/pages/page-09.png`
- `11_质量检查/reports/pdf_qa/pages/page-10.png`
- `11_质量检查/reports/pdf_qa_current/PDF_QA_REPORT.md`
- `11_质量检查/reports/pdf_qa_current/pages/page-01.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-02.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-03.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-04.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-05.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-06.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-07.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-08.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-09.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-10.png`
- `11_质量检查/reports/pdf_qa_current/pages/page-11.png`
- `11_质量检查/scripts/abstract_scorer.py`
- `11_质量检查/scripts/check_doc_refs.py`
- `11_质量检查/scripts/pdf_qa.py`
- `11_质量检查/scripts/test_negative.py`
- `12_AI使用记录/AI_USAGE_LOG.csv`
- `12_AI使用记录/AI_USAGE_LOG_比赛版.csv`
- `12_AI使用记录/README.md`
- `13_环境备份/ENV_REPORT.md`
- `13_环境备份/requirements.txt`
- `14_最终交付/FINAL_REPORT.md`
- `14_最终交付/README.md`
- `14_最终交付/备战汇报/DESIGN.md`
- `14_最终交付/备战汇报/赛前备战汇报.pptx`
- `14_最终交付/备战汇报/assets/fig_distribution.png`
- `14_最终交付/备战汇报/assets/fig_forecast.png`
- `14_最终交付/备战汇报/assets/fig_topsis.png`
- `14_最终交付/备战汇报/slides/01.slide`
- `14_最终交付/备战汇报/slides/02.slide`
- `14_最终交付/备战汇报/slides/03.slide`
- `14_最终交付/备战汇报/slides/04.slide`
- `14_最终交付/备战汇报/slides/05.slide`
- `14_最终交付/备战汇报/slides/06.slide`
- `14_最终交付/备战汇报/slides/07.slide`
- `14_最终交付/备战汇报/slides/08.slide`
- `14_最终交付/备战汇报/slides/09.slide`
- `14_最终交付/备战汇报/slides/10.slide`
- `14_最终交付/备战汇报/slides/11.slide`
- `14_最终交付/备战汇报/slides/12.slide`
- `14_最终交付/备战汇报/slides/13.slide`
- `14_最终交付/备战汇报/slides/14.slide`
- `14_最终交付/备战汇报/slides/15.slide`
- `14_最终交付/备战汇报/slides/16.slide`
- `14_最终交付/备战汇报/slides/17.slide`
- `14_最终交付/备战汇报/slides/18.slide`
- `14_最终交付/备战汇报/slides/19.slide`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）LaTeX模版.zip`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）Word模版.docx`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）承诺书.docx`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）论文提交流程.pdf`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）论文格式规范.pdf`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/~$26年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）承诺书.docx`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/A题/2026_“ShuWei Cup”A_Problem.pdf`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/A题/附件C Synthetic_Production_Data（英文版）.xlsx`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/B题/2026_“ShuWei Cup”B_Problem.pdf`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/C题/2026_“ShuWei Cup”C_Problem.pdf`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/C题/2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）C题数据集说明.pdf`
- `2026年第十二届数维杯全国大学生数学建模挑战赛（秋季赛）赛题/D题/2026_“ShuWei Cup”D_Problem.pdf`

</details>

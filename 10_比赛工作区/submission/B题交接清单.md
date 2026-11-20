# B 题交接清单

送审候选文件见 [论文 PDF](submission-candidate/BSWBMCM2613050.pdf)、[支撑 ZIP](submission-candidate/BSWBMCM2613050fj.zip) 和 [可编辑 LaTeX](../paper/B_submission.tex)。正文已接入 P2 共享筛选对照及 P4 缓存与回零口径。队员按最终采用情况核查正文与 AI 使用报告，再从同一版本导出并验收。承诺书另行保管。

**状态：队内工作稿。** 论文末页披露了 AI 对原型核心工作的参与。参赛稿须由队员独立完成核心工作、自行撰写，并据实申报 AI 辅助。当前稿的资格、题面覆盖和数值核对见 [B 题赛前复核单](../results/B_评审证据核对.md)。

最新队内版本见 [11 页 PDF](prototype-handoff/BSWBMCM2613050.pdf)、[同版支撑 ZIP](prototype-handoff/BSWBMCM2613050fj.zip) 和 [可编辑 LaTeX](../paper/B_prototype.tex)。该版页眉带 B 题号，复跑说明已固定 P2 对照配置和 P4 断联、故障与回零口径。支撑包包括共享候选池对照、P4 断联回放及 45 组交叉试验、P1 平局规则和 P3 阈值复核。[同版复跑报告](prototype-handoff/VERIFY_REPORT.md) · [文件哈希](prototype-handoff/RUN_MANIFEST.json)

## 初版归档

| 文件 | 内容与核对状态 |
|---|---|
| BSWBMCM2613050.pdf | 12 页 LaTeX 英文工作稿，含摘要、独立目录、四问、六张矢量图、28 个配对案例、复核结果、参考文献和 AI 使用报告。已核对 A4、页序、页眉、Times New Roman 嵌入和版面。 |
| BSWBMCM2613050cns.pdf | 三人签名承诺书，从已签 Word 复排为单页 PDF。已核对题号、队号、校名、日期和三处签名。提交前以原 Word 再对照一次版式。签名版材料由队长持有。 |
| BSWBMCM2613050fj.zip | 表格、求解和验算脚本、线路与逐车时间线、矢量图、LaTeX 英文源稿及复现说明。压缩包不含承诺书或签名。 |

## 接手修改

英文可编辑稿在 paper/B_prototype.tex。改稿前核对 B_validation.csv 的验证结果和 B_P4.csv 的场景参数，再确认 P4 的断联解释和任务边界事件。当前论文 PDF 已使用 Tectonic 的 XeTeX 引擎编译，目录和页码由 LaTeX 自动生成。

P2(2) 和 P4 的调度来自有限候选站、保守绕障图和束搜索。当前最好的可行方案有明确时间线，尚无连续空间全局最优性证明。P4 的场景统计描述所测样本，未估计随机风险。

所有数值改动都应先重跑模型和检查程序，再更新论文、附录和图表。AI 使用说明保持与实际使用和人工修改一致。三份文件按官网字段分别上传，最终由队长确认。

初版的数值、排版和重跑检查见 [初版复跑报告](VERIFY_REPORT.md)。初版的输入、源码和产物哈希见 [初版清单](RUN_MANIFEST.json)。队员完成正式稿后，打包入口接收同一版本的 PDF 和支撑 ZIP，并在新目录验收两份文件。[复现与打包说明](../paper/B_reproduce.md)

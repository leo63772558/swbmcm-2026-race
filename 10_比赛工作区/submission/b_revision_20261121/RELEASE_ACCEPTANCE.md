# B 题候选稿封包验收

- 基线 `9c2fef8`，本轮保留队伍人工核验与改写状态。`submission_authorized: false`。
- 论文 24 页 A4。首页与末页版心填充率 94.9% 和 93.8%。三遍 XeLaTeX、逐页栅格与 125 项数值绑定检查通过。
- pytest 39 项全部通过，六项工程审计通过。
- 支撑 ZIP 有 163 个成员，大小 15,791,192 字节。SHA-256 为 `6b1e1b29a4ea0c4d156b89c892d36f1b76a342707dcd35cdad468b1737997925`。
- 从交付 ZIP 独立解压运行 `python 03_code/run_all.py`，九阶段 265.03 s 通过。94 个生成产物及两份 PDF 的 SHA-256 一致。两份 PDF 共 25 页，逐页文本一致。
- 机器可读凭证位于 `RELEASE_ACCEPTANCE.json`、`REPRODUCIBILITY_MANIFEST.json` 和 `qa/REPRODUCTION_CHECK.json`。

# 本地数据

`cazy/` 和 `peptidase/` 保存系统配置引用的 embedding 与 metadata。默认配置读取本项目中的文件。`configs/cazy_backbones.json` 使用本目录下的软链接读取显式声明的外部 embedding 源目录，详见项目 README 的“CAZy 其他 base model”。

`cazy/metadata/*.tsv` 和 `peptidase/metadata/*.tsv` 已由 Git 跟踪，克隆后即可使用。迁移项目时另行复制 embedding，保持配置中的相对路径，再从项目根目录检查：

```bash
.venv/bin/python workflows/validate.py --config configs/cazy.json
.venv/bin/python workflows/validate.py --config configs/peptidase.json
```

需要全量 ID、有限值和标签对齐检查时加 `--deep`。

`import_manifest.json` 仅保留初次复制的来源及校验记录，运行不读取。README、两套系统的 metadata TSV，以及下述 performance 报告和来源记录进入 Git；embedding 和逐样本预测 CSV 继续忽略。

二分类图另导入五条 CAZy 路线的 `non-cazy_train.embeddings.csv`，配置角色为 `non_target_train`。副本 SHA256 与原文件一致，记录在 `binary_import_manifest.json`；L2 FT-CE 原目录无该输入。

## Performance 输入

`<system>/performance/reports/` 保存原始报告和 `*_no_head.md`（绘图实际使用后者），四份报告合计 23,454 字节。`<system>/performance/predictions/` 保存六份预测 CSV，合计 17,806,296 字节，供核查使用；绘图不读取它们，克隆后无需另行复制 CSV 即可重画。

数据复制自 `/Users/lczong/Projects/01PER/Performance`，两个 `SOURCE.json` 记录源仓库提交、相对文件名、文件大小和完整 SHA-256。副本逐文件校验一致，未使用软链接。报告保持原文，其中 `provenance.json` 链接和 `src/evaluation/test_performance_report.py` 重算命令引用的文件不在源目录中；本次未迁移这些缺失文件，不能在本仓库直接执行该旧命令。旧报告内 CSV 链接的文件现位于相邻的 `predictions/` 目录。

报告数值已四舍五入到百分数小数点后两位；workflow 复用这些数值，不声称从预测重新计算得到更高精度。新增报告时更改系统配置的 `performance.report`，运行 `tables` 后再运行 `plots`；当前方法定义限于 ESM2 及其训练路线。

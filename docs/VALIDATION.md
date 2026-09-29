# 验证记录 — 2026-09-29

## 配置及数据

- CAZy：6 条 route、36 个逻辑数据集。
- Peptidase：5 条 route、25 个逻辑数据集。
- 配置所需 72 个文件已复制到新项目；约 27.51 GiB 逻辑大小。
- 所有输入路径、metadata 文件存在性、CSV 首行或 NPY header 维度检查通过。
- 复制检查：独立 inode、文件大小和首尾各 1 MiB 摘要。没有宣称此次做过全文件逐字节校验。
- 运行时无需读取旧项目。旧项目只作为一次性导入与回归基准来源。

## 自动化测试

`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`：12 项测试全部通过。

覆盖：

- 三种 chunk size 下的旧版 family silhouette、Dunn、per-family DBI、CH、类内距离与最近质心距离对照。
- 全局 silhouette、标准 DBI、CH 对照 sklearn。
- Euclidean/cosine OOD target silhouette 对照 sklearn。
- class BA 的确定值、缺类别、单标签和退化半径。
- 重合质心的自身邻居排除。
- PCA 仅在 train 拟合。
- 抽样与输入行序无关。
- NPY ID 来源顺序与行数约束、CSV 分片重复 ID、缺 metadata、外部路径拒绝。
- 缓存产物缺失和图片重绘的区分。
- 两个系统的独立分步工作流；指标与降维隔离、绘图无需原始数据、缓存复用、错误输入类型与缺上游输入报错。

工作流单元测试使用确定性二维坐标替代降维，以控制测试速度；实际降维由下面的真实数据 smoke 验证。

## 初次实现的真实数据验证记录

初次实现时运行真实数据 smoke，两套系统均使用本地 `esm2__l2-frozen-nca` 输入的真实子集：

- CAZy：CBM、GH；train 24 条、multi 8 条、unseen 16 条，各 OOD 8 条。
- Peptidase：C、M；train 24 条、multi 8 条、unseen 16 条，各 OOD 8 条。
- PCA 保留 5 维，t-SNE/UMAP 使用小样本参数，配置保存在 smoke 项目中。
- 两套系统的 overview、OOD、class BA、unseen、structure 全部成功。
- 实际调用 openTSNE 和 umap-learn，不使用 mock；每套导出 18 张 PNG（含对比图）。
- 检查了 OOD 密度图和 BA 分布图；小样本训练背景显示问题已修正后重跑。
- 绘图专用命令在配置输入指向不存在的文件时仍可使用已保存结果成功重绘，验证没有重新读取 embedding。

以下 run ID 为初次实现的历史验证记录，不作为当前入口。具体 run ID 见 [smoke_results.json](smoke_results.json)。图与中间产物位于未跟踪的 outputs/smoke/，不替代正式实验结果。

## 验证边界

没有重跑所有路线的全量实验；没有对全量数据逐行做深校验。所有正式结果应通过完整配置执行后生成。

旧图的随机样本、scanpy UMAP 布局、历史专用绘图不承诺逐像素复现。改动的抽样与统计口径详见 METHODS.md 和 DEFERRED.md。

## 分步入口验证

当前 `scripts/smoke_real_data.py` 逐步调用 PCA、sample、metrics、tsne、umap、visualization、metric-plots，覆盖两套系统的五个实验。所有运行入口位于 workflows/。

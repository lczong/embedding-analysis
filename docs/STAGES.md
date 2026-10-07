# 分步执行设计

每个实验有独立入口：workflows/ood.py、multilabel.py、overview.py、unseen.py、structure.py。
共享 PCA 入口为 workflows/pca.py。实验入口提供 metrics、tsne、umap、visualization、metric-plots 子命令（仅显示适用步骤）。

步骤只读取显式 --input 目录，将结果写入 --output；不自动运行上游。PCA 输入来自 config，其他步骤读取已保存的 PCA / coordinates / metrics 产物。指标计算不做二维降维，降维不算指标，两类绘图互不依赖。t-SNE 和 UMAP 可以分别运行并保存在不同目录。

workflows/*.sh 仅负责按顺序调用独立步骤，计算代码由 src/embedding_analysis/experiments/<实验>/ 各自管理。

## 验证

`tests/test_stages.py` 在 CAZy / peptidase 两套配置下验证：metrics 禁止调用降维；tsne / umap 禁止调用指标；两类绘图分别读取自己的产物；移走原始 data 后仍能绘图和复用已完成的指标；错误输入类型和缺少上游产物会报错。原指标回归测试保留。

真实数据小样本使用已有 `outputs/smoke/<system>/configs/<system>.json`，分别通过 `workflows/ood.sh`（CAZy）和 `workflows/multilabel.sh`（peptidase）验证实际 PCA、t-SNE、UMAP、指标和两类绘图。没有重跑生产全量数据。

## 入口清理

组合 CLI、包级命令注册、自动串联计算函数和合并绘图分支已删除。数据检查迁至 workflows/validate.py；跨路线汇总迁至 workflows/<实验>_summary.py 的 tables / plots 两个独立步骤。回归基准保留，只用于验证指标定义。

当前验证：13 项测试通过；真实小样本在两套系统上完成五个实验的适用独立步骤（含实际 t-SNE、UMAP、指标及两类绘图）；输入检查及独立汇总表、汇总图入口通过。未运行生产全量数据。

## 实验代码所有权

每个实验有自己的 workflow.py、compute.py、metrics.py 和 plotting.py（overview 无指标），各自维护输入依赖、指标定义、空间图和指标图；summary.py 也归各实验。OOD / unseen 的抽样规则放在自己的 sampling.py。

共享 prepared.py / reduction.py 负责 PCA 与二维降维，data.py / config.py / artifacts.py / runtime.py 提供不认识任何实验的底层功能。不存在集中 stages.py、workflows.py、metrics.py、plotting.py 或 shell 实验分派。

架构测试在禁止导入其他实验的条件下，分别导入每个实验全部模块，防止跨实验依赖回流。

2026-10-07：完成实验模块拆分后，`scripts/smoke_real_data.py` 通过各实验自己的入口重跑两套系统、五个实验全部适用步骤，实际运行 PCA、t-SNE、UMAP、指标计算和两类绘图。独立汇总表/图由分步测试覆盖；所有 shell 入口通过语法和帮助检查。

# 分步执行设计

每个实验有独立入口：workflows/ood.py、multilabel.py、overview.py、unseen.py、structure.py。
共享 PCA 入口为 workflows/pca.py。实验入口提供 metrics、tsne、umap、visualization、metric-plots 子命令（仅显示适用步骤）。

步骤只读取显式 --input 目录，将结果写入 --output；不自动运行上游。PCA 输入来自 config，其他步骤读取已保存的 PCA / coordinates / metrics 产物。指标计算不做二维降维，降维不算指标，两类绘图互不依赖。t-SNE 和 UMAP 可以分别运行并保存在不同目录。

workflows/*.sh 仅负责按顺序调用独立步骤，计算代码仍在 src/embedding_analysis。旧 run.py 作为兼容入口保留，不作为推荐入口。

## 验证

`tests/test_stages.py` 在 CAZy / peptidase 两套配置下验证：metrics 禁止调用降维；tsne / umap 禁止调用指标；两类绘图分别读取自己的产物；移走原始 data 后仍能绘图和复用已完成的指标；错误输入类型和缺少上游产物会报错。原指标回归测试保留。

真实数据小样本使用已有 `outputs/smoke/<system>/configs/<system>.json`，分别通过 `workflows/ood.sh`（CAZy）和 `workflows/multilabel.sh`（peptidase）验证实际 PCA、t-SNE、UMAP、指标和两类绘图。没有重跑生产全量数据。

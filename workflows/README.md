# 独立步骤和实验流程

从项目根目录运行。`.py` 是单步骤入口，`.sh` 管理各实验的执行顺序；不指定步骤只显示帮助，不会开始全量计算。

## OOD / Exp1

```bash
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca pca
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca sample
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca metrics
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca tsne
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca visualization-tsne
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca metric-plots
```

也可以单独执行 `umap` 和 `visualization-umap`，与 t-SNE 结果分别保存。`sample` 保存跨路线共同 ID 抽样清单；指标与二维降维必须读取同一份清单。sample 会读取配置中的原始 ID，其他下游步骤只读已保存的产物。

## Multilabel / Exp2

```bash
# 同系统、同路线的 PCA 可直接复用，无需再跑。
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca metrics
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca umap
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca visualization-umap
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca metric-plots
```

把 `configs/cazy.json` 换成 `configs/peptidase.json` 即切换系统。每条命令只执行指定步骤，缺上游输入会报错，不会补跑。指标与降维可以任选先后；绘图只读取对应结果，不读取原始 embedding。

## 直接指定输入和输出

```bash
.venv/bin/python workflows/multilabel.py metrics \
  --config configs/cazy.json \
  --input outputs/steps/cazy/esm2__l2-frozen-nca/pca \
  --output outputs/custom/ba-metrics

.venv/bin/python workflows/multilabel.py metric-plots \
  --config configs/cazy.json \
  --input outputs/custom/ba-metrics \
  --output outputs/custom/ba-plots
```

OOD 的 metrics / tsne / umap 额外需要 `--sampling <sample产物目录>`。路径相对项目根目录；输出必须位于配置的 output_root 下。

## 其他实验

- `overview.sh`：pca → tsne 或 umap → visualization-tsne 或 visualization-umap。
- `unseen.sh`：pca → metrics；pca → tsne 或 umap；分别画空间图和指标图。
- `structure.sh`：pca → metrics（含 centroids）→ visualization / metric-plots。它的空间图是 centroid 距离热图，不需要二维降维。

显式指定 `all` 才会编排该实验全部步骤，包含 t-SNE 和 UMAP（structure 除外）。每个脚本的第四个参数可指定输出根目录，默认 `outputs/steps/<config文件名>/<route>`。更换参数或代码后建议第四参数使用新目录；不会覆盖旧产物。相同参数、代码和输入可复用已完成步骤。失败留下的目录请检查后移走，或改用新输出目录重试。

共享计算函数位于 `src/embedding_analysis/workflows.py`：PCA、compute_metrics、compute_coordinates 互相独立。`stages.py` 只负责 CLI 和产物校验。旧 `run.py` 保留兼容，仍是旧的组合运行方式。

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

每个实验的代码放在 `src/embedding_analysis/experiments/<实验>/`：`workflow.py` 管理自己的步骤和输入依赖；`compute.py` 准备本实验数据并执行计算；`metrics.py` 定义本实验指标；`plotting.py` 绘制本实验的图；`summary.py` 负责本实验的跨路线汇总。overview 没有指标和汇总模块。

共享层仅提供数据与配置读取、PCA、t-SNE/UMAP、确定性 ID 排序和产物校验。`runtime.py` 不导入任何实验，也不选择或执行步骤。不存在集中实验注册表或跨实验分派。每个 `.sh` 自己规定执行顺序。

## 检查与汇总

输入检查：`.venv/bin/python workflows/validate.py --config configs/cazy.json`，可加 `--deep`。

汇总指标表与画汇总图也是独立步骤：

```bash
.venv/bin/python workflows/ood_summary.py tables --config configs/cazy.json \
  --inputs outputs/steps/cazy/esm2__l2-frozen-nca/ood/metrics \
  --output outputs/summary/cazy/tables
.venv/bin/python workflows/ood_summary.py plots --config configs/cazy.json \
  --input outputs/summary/cazy/tables --output outputs/summary/cazy/figures
```

`tables --inputs` 后可列出多个路线的指标目录。其他实验分别使用 `multilabel_summary.py`、`unseen_summary.py`、`structure_summary.py`；不能把不同实验混在同一汇总里。

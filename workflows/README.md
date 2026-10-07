# 实验分步操作手册

本文对应当前独立实验实现。每个实验自己管理流程、指标和绘图；公共层提供 PCA、t-SNE/UMAP、数据读写及产物校验。所有指标使用 PCA 特征计算，不使用二维图坐标。

## 目录

1. [准备环境、选择系统和路线](#准备环境选择系统和路线)
2. [命令形式与步骤依赖](#命令形式与步骤依赖)
3. [公共 PCA](#公共-pca)
4. [OOD / Exp1](#ood--exp1)
5. [Multilabel / Exp2](#multilabel--exp2)
6. [Overview：训练空间展示](#overview训练空间展示)
7. [Unseen：未见 family 分析](#unseen未见-family-分析)
8. [Structure：family 质心结构](#structurefamily-质心结构)
9. [跨路线汇总](#跨路线汇总)
10. [配置参数](#配置参数)
11. [重跑、缓存与成功检查](#重跑缓存与成功检查)
12. [常见报错](#常见报错)
13. [代码归属与验证](#代码归属与验证)

## 准备环境、选择系统和路线

在项目根目录运行本文命令：

```bash
cd /Users/lczong/Projects/01PER/OOD2/embedding_analysis
```

本机 `.venv` 和数据已经准备好。无需激活环境，入口直接使用 `.venv/bin/python`。换机器时需带上 `data/`，并按[项目 README](../README.md#移动或在其他机器安装)重建环境。

先选系统：`configs/cazy.json` 或 `configs/peptidase.json`。两者分别与同目录 `defaults.json` 合并，系统配置覆盖默认值。

先检查输入：

```bash
.venv/bin/python workflows/validate.py --config configs/cazy.json
.venv/bin/python workflows/validate.py --config configs/peptidase.json
```

默认检查路径和 embedding 维度；加 `--deep` 会读取全量数据，检查 ID、有限数值和 metadata 对齐，耗时更长。该工具只检查，不生成 PCA 或实验结果。

当前路线与可运行范围：

| route | CAZy | Peptidase |
| --- | --- | --- |
| `esm2` | 五个实验 | 没有该原始 ESM2 输入 |
| `esm2__l0-ft-ce` | 五个实验 | 五个实验 |
| `esm2__l1-ft-ce` | 五个实验 | 五个实验 |
| `esm2__l2-frozen-nca` | 五个实验 | 五个实验 |
| `esm2__l1-ft-ce__l2-frozen-nca` | 五个实验 | 只有 train；仅 overview、structure |
| `esm2__l2-ft-ce` | 五个实验 | 五个实验 |

route 从 `esm2` 起，训练阶段用 `__` 连接；`l0/l1/l2` 为二分类、大类、family，`ft/frozen` 为微调 backbone / 冻结上游表示，`ce/nca` 为训练损失。两个系统的 l1 都直接从 ESM2 训练。Peptidase 的 l0 是二分类微调结果，不是原始 ESM2。

下文完整示例统一采用 CAZy 的 `esm2__l2-frozen-nca`。换成 `configs/peptidase.json` 即运行另一系统；每条路线的 PCA 需分别准备。

## 命令形式与步骤依赖

### Shell 入口：自动填入常用目录

```bash
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca metrics
```

四个位置参数依次为 `CONFIG ROUTE STEP [OUTPUT_BASE]`。第四个参数可省略；默认根目录是 `outputs/steps/<config文件名去掉.json>/<route>`。标准配置下即 `outputs/steps/cazy/...` 或 `outputs/steps/peptidase/...`。

各实验独立入口：`ood.sh`、`multilabel.sh`、`overview.sh`、`unseen.sh`、`structure.sh`。不传步骤只显示帮助。一次调用只执行一个步骤；显式指定 `all` 才按该实验脚本顺序执行全部步骤。

```bash
# 只显示帮助
bash workflows/ood.sh

# 显式运行 OOD 全部步骤，包括 t-SNE 和 UMAP
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca all
```

`all` 只覆盖这个实验、这个系统、这条路线；不运行其他实验或所有路线，也不自动跳过失败步骤。完整 t-SNE 和精确距离计算可能耗时较长。

### Python 入口：显式指定每步输入输出

```bash
.venv/bin/python workflows/multilabel.py metrics \
  --config configs/cazy.json \
  --input outputs/steps/cazy/esm2__l2-frozen-nca/pca \
  --output outputs/custom/multilabel-metrics
```

`--input` 指向已经完成的上游产物目录，目录中必须有有效 `manifest.json`。`--output` 必须位于配置的 `output_root` 下，且与输入目录分开，不能互相嵌套。数据和产物的相对路径按配置所属项目根目录解析；`--config` 本身按命令的当前目录解析。将自定义系统配置保存在项目的 `configs/` 下，避免改变项目根目录的解析。

Python 降维子命令是 `tsne` / `umap`；绘图子命令统一为 `visualization`，由 `--input` 选择哪份二维坐标。Shell 则提供 `visualization-tsne` / `visualization-umap` 两个便捷步骤。

### 步骤依赖

```text
原始 embedding + metadata → PCA
                              ├→ metrics → metric-plots
                              ├→ tsne    → visualization-tsne
                              └→ umap    → visualization-umap

OOD 另有：原始 ID → sample → metrics / tsne / umap
Structure：PCA → metrics（含质心）→ visualization / metric-plots
```

指标、t-SNE 和 UMAP 是并列分支，可以任选先后，不要求先算指标再降维。每步只读指定产物；缺少上游会报错，不会自动补跑。两种二维方法分别拟合、分别存储，不使用彼此的结果。

## 公共 PCA

### 运行

```bash
.venv/bin/python workflows/pca.py prepare \
  --config configs/cazy.json --route esm2__l2-frozen-nca \
  --output outputs/steps/cazy/esm2__l2-frozen-nca/pca
```

等价便捷命令：

```bash
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca pca
```

输入是该 route 配置中的原始 embedding 和 metadata。处理顺序为：每条序列做 L2 归一化，在 train 上拟合 PCA，再用同一个模型转换本路线配置的其他数据集。默认保留 100 个主成分；没有把 probe 合并到 PCA 拟合中。

当前一个 `prepare` 步骤包含模型拟合及本路线全部已配置数据集的转换，没有单独的 fit / transform CLI。签名检查还会读取配置中其他路线输入文件的指纹，因此配置引用的文件也须存在。

### 输出

输出都位于 `pca/`：

| 文件 | 内容 |
| --- | --- |
| `pca_model.joblib` | L2 Normalizer 与 train-fit PCA 模型 |
| `<role>.npz` | `ids`：序列 ID；`values`：对应 float32 PCA 特征 |
| `<role>.metadata.csv` | 有配置 metadata 的角色的对齐标签；通常为 train、multi、unseen |
| `explained_variance.csv` | `component`：从 1 开始的主成分编号；`explained_variance`：单维解释方差比例；`cumulative`：累计比例 |
| `manifest.json` | 配置、路线、输入指纹、代码摘要、步骤签名和文件清单 |

角色名包括 `train`、`multi`、`unseen`、`ood`、`shuffled`、`idr`，实际文件以本路线配置为准。metadata 内部字段统一为 `sequence_id`、`class_label`、`family_label`、`dataset_role`。

同系统、同路线的这份 PCA 可供全部适用实验读取。若只跑指标，到 PCA 完成后直接运行相应 `metrics` 即可。

## OOD / Exp1

输入要求：PCA 中有 `train`、`ood`、`shuffled`、`idr`。`ood` 是 non-target，`shuffled` 是打乱序列，`idr` 是 IDR。指标只有 target silhouette，不计算 kNN OOD score。

### 逐步运行

```bash
# 1. 准备公共 PCA；已有相同产物可复用
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca pca
# 2. 固定跨路线抽样
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca sample
# 3. 只算 silhouette
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca metrics
# 4. 分别做二维降维；可以只选一种
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca tsne
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca umap
# 5. 分别读取二维坐标画空间图
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca visualization-tsne
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca visualization-umap
# 6. 只读指标表画指标图
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca metric-plots
```

`sample` 不依赖 PCA，可先执行。它对每种 OOD 角色分别取系统内各可用路线的 ID 交集，再按 seed 排序抽取至多 3145 条。CAZy l2-ft 的已有预抽样可能使共同样本少于目标数；以清单记录的实际数为准。train 保持全量。Shell 把清单放在当前路线的输出树下，但抽样依据是整个系统，并非仅这条路线。

`metrics` 把每一种 target 与 train 作为两个组计算 silhouette，仅保存 target 分数。t-SNE/UMAP 联合放入 train 和抽中的三种 target。它们与指标读取同一份清单。

### 输入与产物

以下路径相对 `outputs/steps/cazy/esm2__l2-frozen-nca/`：

| 步骤 | 读取 | 主要产物 |
| --- | --- | --- |
| `sample` | 配置内各路线的原始 ID | `ood/sample/sampling.json` |
| `metrics` | `pca/` 和 `ood/sample/` | `ood/metrics/samples.csv`、`summary.csv`、`sampling.json` |
| `tsne` / `umap` | 同上 | `ood/<方法>/coordinates.csv`、`sampling.json` |
| `visualization-<方法>` | `ood/<方法>/` | `ood/visualization-<方法>/figures/density.png`、`.pdf` |
| `metric-plots` | `ood/metrics/` | `ood/metric-plots/figures/silhouette.png`、`.pdf` |

`sampling.json` 每个角色包含 `ids`、`requested`、`actual`、`common_count` 和各路线的 `source_counts`。

`samples.csv` 字段为 `sequence_id`、`dataset_role`、`silhouette`；`summary.csv` 按 `dataset_role` 给出 `count/mean/median/std/min/max`。silhouette 范围通常为 [-1, 1]，越高表示该 target 点在这两个组之间更靠近自身组，不是 OOD 概率。

`coordinates.csv` 包含 `sequence_id`、`dataset_role`、`x`、`y`。密度图的 KDE 轮廓是样本密度值的第 90 百分位，不表示包围 90% 概率质量。

### 显式复用一份抽样清单

```bash
.venv/bin/python workflows/ood.py metrics \
  --config configs/cazy.json \
  --input outputs/steps/cazy/esm2__l2-frozen-nca/pca \
  --sampling outputs/steps/cazy/esm2__l2-frozen-nca/ood/sample \
  --output outputs/custom/ood-metrics
```

`metrics`、`tsne`、`umap` 都必须传 `--sampling`。跨路线比较时，可让各路线显式读取同一份清单。

## Multilabel / Exp2

输入要求：PCA 中有带标签的 `train` 和 `multi`。按单标签 train 的 class 计算质心，再计算 multi 的 class-level BA；不计算 family BA 或 bridge score。

### 逐步运行

```bash
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca pca
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca metrics
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca tsne
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca umap
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca visualization-tsne
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca visualization-umap
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca metric-plots
```

PCA 已准备时可以跳过第一行；t-SNE 与 UMAP 可以只选一种。二维降维联合使用 train 和 multi 全部样本，不依赖 BA 结果。

### 产物和字段

| 步骤 | 实验目录内的产物 | 说明 |
| --- | --- | --- |
| `metrics` | `metrics/scores.csv` | 每条 multi 的 `sequence_id`、`class_label`、`ba_score`、`invalid_reason` |
| `metrics` | `metrics/summary.csv` | 按 class 组合统计 `count/mean/std/min/25%/50%/75%/max` |
| `tsne` / `umap` | `<方法>/coordinates.csv` | 标签、角色及 `x/y`；每条样本一行 |
| `visualization-<方法>` | `visualization-<方法>/figures/classes.*`、`combo_<组合>.*` | 联合空间图、指定 class 组合高亮图 |
| `metric-plots` | `metric-plots/figures/ba.*` | 按 class 组合绘制 BA 分布 |

BA 越接近 1，样本越接近所属 class 质心的等权重心；分数可以为负，不是概率。定义见[计算约定](../docs/METHODS.md#class-ba)。无效值写为 NaN，原因可能为 `missing_class_centroid`、`not_multilabel`、`degenerate_radius`；CSV 中空分数并不必然是程序失败。

`min_combination_size=5` 只影响 BA 分布图纳入哪些组合，不过滤 BA 计算或二维降维。汇总的 `count` 是有效 BA 数；绘图的组合大小门槛按原始分数组的行数计算。重点组合来自系统配置 `plot.highlight_combinations`。

## Overview：训练空间展示

只读取 train PCA 和标签，不计算指标。

```bash
bash workflows/overview.sh configs/cazy.json esm2__l2-frozen-nca pca
bash workflows/overview.sh configs/cazy.json esm2__l2-frozen-nca tsne
bash workflows/overview.sh configs/cazy.json esm2__l2-frozen-nca visualization-tsne
bash workflows/overview.sh configs/cazy.json esm2__l2-frozen-nca umap
bash workflows/overview.sh configs/cazy.json esm2__l2-frozen-nca visualization-umap
```

`overview/<方法>/coordinates.csv` 保存 train 的标签及 `x/y`。`overview/visualization-<方法>/figures/classes.*`、`families.*` 分别按 class 和 family 着色。没有 `metrics`、`metric-plots` 或 summary 入口。

## Unseen：未见 family 分析

输入要求：带标签的 train 和 unseen PCA。每个 class 分开分析，默认使用前 100 个 PC。

### 逐步运行

```bash
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca pca
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca metrics
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca tsne
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca visualization-tsne
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca umap
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca visualization-umap
bash workflows/unseen.sh configs/cazy.json esm2__l2-frozen-nca metric-plots
```

指标步骤保留至少 2 条序列的 family，每个 class 从符合条件的 train family 中选至多 10 个参照，联合 unseen families 计算指标。参照选择是确定性的，写入清单。

**指标参照和图的背景不同**：指标用 sampled train families；二维图用该 class 全部 train 作背景，再加入符合大小门槛的 unseen families。降维自己准备输入，不调用指标步骤，因此指标与空间图的跳过 class 清单也可能不同。

### 产物

| 位置（相对 `unseen/`） | 内容 |
| --- | --- |
| `metrics/families.csv` | 只汇总 unseen families 的逐家族指标，附 `class_label` |
| `metrics/global.csv` | 各 class 的整体指标及上下文 |
| `metrics/reference_families.json` | 每类的 train/unseen family 列表及序列数量 |
| `metrics/skipped_classes.json` | 没有合格 train 或 unseen families 等跳过原因 |
| `metrics/<class>/joint_families.csv` | 联合空间中 train 参照与 unseen 的全部 family 指标 |
| `metrics/<class>/train_sample_families.csv` | 至少有两个参照 family 时，单独计算的 sampled-train 指标 |
| `<方法>/<class>/coordinates.csv` | 每个 class 独立的二维坐标 |
| `<方法>/skipped_visualization_classes.json` | 缺少 train 或合格 unseen 的绘图输入跳过记录 |
| `visualization-<方法>/<class>/figures/families.*` | 灰色 train 背景上的 unseen family 空间图 |
| `metric-plots/figures/silhouette_mean.*`、`dunn_cosine.*`、`legacy_pairwise_dbi.*` | 按 class 分组的指标分布图 |

### 表字段

逐 family 表主要字段：

| 字段 | 含义 |
| --- | --- |
| `family_label`、`n_sequences` | 家族及其样本数 |
| `silhouette_mean` | family 内样本的平均 cosine silhouette |
| `dunn_cosine` | 本 family 最小跨 family 距离 / 最大内部距离，使用 cosine |
| `legacy_pairwise_dbi` | 使用 family 内平均两两 Euclidean 距离作 scatter 的历史 per-family DBI 定义 |
| `ch_between`、`ch_within` | family 对类间/类内平方和的贡献 |
| `ch_per_family` | family 层级的 CH 分量比值，不是标准全局 CH |
| `intra_mean_euclidean` | family 内平均两两 Euclidean 距离 |
| `nearest_centroid_euclidean` | 到最近其他 family 质心的 Euclidean 距离 |

`global.csv` 另包含 `class_label`、`context`、`n_sequences`、`n_families`、`silhouette_cosine`、`dunn_cosine`、`davies_bouldin_euclidean`、`calinski_harabasz_euclidean`。

`context=joint_unseen_and_sampled_train` 表示联合空间；`sampled_train_only` 表示单独的 train 参照空间。不能把前者当成 unseen-only 结果。`legacy_pairwise_dbi` 也不能与标准全局 `davies_bouldin_euclidean` 混用。退化距离可能产生 NaN，详见[计算约定](../docs/METHODS.md#unseen-family)。

## Structure：family 质心结构

只需 train。默认保留至少 5 条序列的 family，并在 PCA 空间计算家族质心。每个 family 必须属于一个 class。

```bash
bash workflows/structure.sh configs/cazy.json esm2__l2-frozen-nca pca
bash workflows/structure.sh configs/cazy.json esm2__l2-frozen-nca metrics
bash workflows/structure.sh configs/cazy.json esm2__l2-frozen-nca visualization
bash workflows/structure.sh configs/cazy.json esm2__l2-frozen-nca metric-plots
```

该实验不做 t-SNE/UMAP。`visualization` 直接读取指标步骤保存的质心，画距离热图。

| 产物（相对 `structure/`） | 内容 |
| --- | --- |
| `metrics/centroids.csv` | `family_label`、`class_label`、`n_sequences`、`PC1...PCn` |
| `metrics/metrics.csv` | 长表：`metric`、`k`、`value` |
| `visualization/figures/centroid_distances.*` | family 按 class/family 排序后的 Euclidean 距离热图 |
| `metric-plots/figures/knn_class_purity.*` | 不同 k 的质心同 class 邻居比例 |

`metric` 包括 `knn_class_purity`、`class_silhouette`、`median_within_class`、`median_between_class`、`between_over_within`；只有第一个使用 `k` 字段，其他行的 `k` 为空。这里的 kNN 是 family 质心的结构指标，不是已取消的 kNN OOD score。默认 k 为 1、3、5、7、9，合格 family 数必须大于最大 k。

## 跨路线汇总

每个实验有自己的汇总工具：`ood_summary.py`、`multilabel_summary.py`、`unseen_summary.py`、`structure_summary.py`。先汇总表，再单独绘图。只汇总同一系统、同一个实验；不要混入不同 PCA 设定或不可比较的计算配置，当前工具不会替你验证这些科学参数是否一致。

以下例子要求两条路线的 OOD `metrics` 都已经完成：

```bash
.venv/bin/python workflows/ood_summary.py tables --config configs/cazy.json \
  --inputs outputs/steps/cazy/esm2__l0-ft-ce/ood/metrics \
           outputs/steps/cazy/esm2__l2-frozen-nca/ood/metrics \
  --output outputs/summary/cazy/ood/tables

.venv/bin/python workflows/ood_summary.py plots --config configs/cazy.json \
  --input outputs/summary/cazy/ood/tables \
  --output outputs/summary/cazy/ood/plots
```

`tables --inputs` 接受多个指标目录，每个目录有有效 manifest；生成加上 `route` 列的 `summary.csv`。不需要所有路线都完成，也不会自动寻找目录。

| 实验 | 汇总来源 | 比较图 |
| --- | --- | --- |
| OOD | 各路线 `metrics/summary.csv` | 各角色的平均 silhouette |
| Multilabel | 各路线 `metrics/summary.csv` | 各 class 组合的平均 BA |
| Unseen | 各路线 `metrics/families.csv` | 各 class 的 family silhouette 均值（按 family 等权） |
| Structure | 各路线 `metrics/metrics.csv` | 不同 k 的质心同 class 邻居比例 |

`plots` 输出 `comparison.png/.pdf`（按配置格式），直接放在指定输出目录中。若汇总表为空，可以成功结束但不生成图。每个输入目录只列一次，避免重复汇总。

## 配置参数

科学参数保存在 `configs/defaults.json`，可由系统配置覆盖。下表为当前默认值；更改共享 defaults 会影响两个系统。

| 配置字段 | 默认值 | 影响 |
| --- | --- | --- |
| `seed` | 42 | PCA、二维降维、OOD / family 确定性选择 |
| `preprocessing.n_components` | 100 | PCA 维数，不能大于 train 的行数与特征数的较小者 |
| `preprocessing.normalize / fit_on` | `l2 / train` | 当前实现只支持这组设置 |
| `reduction.tsne.perplexity` | 30 | t-SNE 邻域参数，须小于实际参与降维的样本数 |
| `reduction.tsne.n_iter_early / n_iter_main` | 250 / 500 | 两阶段优化迭代数 |
| `reduction.tsne.n_jobs` | 1 | t-SNE 并行度 |
| `reduction.umap.n_neighbors` | 30 | UMAP 邻居数，须小于实际参与降维的样本数 |
| `reduction.umap.min_dist / metric / n_jobs` | `0.5 / euclidean / 1` | UMAP 布局、距离和并行度 |
| `experiments.ood.target_size` | 3145 | 每种 OOD 的最大抽样数，不保证交集有这么多 |
| `experiments.ood.distance / chunk_size` | `euclidean / 512` | silhouette 距离及分块大小 |
| `experiments.multilabel.label_level` | `class` | 只支持 class BA |
| `experiments.multilabel.min_combination_size` | 5 | BA 分布图的组合大小门槛 |
| `experiments.unseen.n_pcs` | 100 | 取前多少 PC，不能超过已保存的 PCA 维数 |
| `experiments.unseen.min_family_size` | 2 | 合格 family 的最少序列数 |
| `experiments.unseen.train_family_count` | 10 | 每类最多选择多少个 train 参照 family |
| `experiments.unseen.chunk_size` | 256 | family 距离计算分块大小 |
| `experiments.structure.min_family_size / ks` | `5 / [1,3,5,7,9]` | family 门槛和质心邻居统计 |
| `plot.dpi / formats / point_size` | `180 / [png,pdf] / 3` | 导出设置及使用此参数的散点大小；OOD 点大小目前在本实验绘图代码中固定 |
| `plot.highlight_combinations` | 系统配置 | Multilabel 重点组合 |
| `class_colors` | 系统配置 | class 颜色 |

配置中仍存在 `experiments.<实验>.method` 字段，但当前独立入口不使用它选择降维：以执行的 `tsne` / `umap` 子命令为准，shell 的 `all` 会执行两种方法。

当前每个实验的多个指标仍由一个 `metrics` 步骤一起计算；一个空间绘图步骤会导出该实验适用的全部空间图，没有逐指标或逐图的选择参数。

## 重跑、缓存与成功检查

### 怎么判断成功

正常结束会输出产物目录；复用时输出 `Cached: ...`。检查该目录的 `manifest.json`，其中 `experiment`、`stage`、`route`、`config` 应对应当前任务，`artifacts` 列出完成文件及大小。绘图产物也纳入完成检查。

同时检查本节对应的关键文件：指标表是否有有效行、`sampling.json` 实际样本数、unseen 跳过记录、期望图片是否存在。退出码为 0 并不表示每个 class 都有结果；合法的空表、被跳过的 class 和无效分数需要单独查看。

### 缓存规则

只有步骤签名匹配且文件清单完整时才复用。签名包含合并配置、包内 Python 代码摘要和上游 manifest；PCA / sample 还包含配置引用的原始输入指纹。代码摘要目前覆盖整个 Python 包，配置也整体参与，因此修改其他实验代码或无关配置也可能令缓存签名变化。

原始输入指纹使用路径、大小、mtime 和文件首尾摘要，不是全文件校验和；产物完整性校验使用文件存在性和大小。不要原地修改中间产物，即使同样大小也可能被视为有效。

下游读取的是你指定的上游产物，不会检查原始 embedding 是否刚被替换，也不会自动重建 PCA。更换输入或科学设置后，应显式准备新上游，沿对应分支重跑。

### 重跑整个实验，保留原结果

第四个 shell 参数指定新的根目录；后续各步骤都传同一个新根目录：

```bash
bash workflows/ood.sh configs/cazy.json esm2__l2-frozen-nca all \
  outputs/runs/cazy-l2nca-v2
```

只给下游指定新根目录不会把旧 PCA 搬过去，会报缺上游。若要复用旧 PCA 但重算某一步，用 Python 入口的 `--input` 指向旧 PCA，`--output` 指向新目录。

### 只改样式重画

```bash
.venv/bin/python workflows/multilabel.py visualization \
  --config configs/cazy.json \
  --input outputs/steps/cazy/esm2__l2-frozen-nca/multilabel/umap \
  --output outputs/replots/cazy-multilabel-umap-v2

.venv/bin/python workflows/multilabel.py metric-plots \
  --config configs/cazy.json \
  --input outputs/steps/cazy/esm2__l2-frozen-nca/multilabel/metrics \
  --output outputs/replots/cazy-multilabel-ba-v2
```

绘图的科学设置来自上游 manifest；只有当前配置的 `plot` 和 `class_colors` 覆盖进去。例如改变 `plot.dpi` 可直接重画；改变 `min_combination_size` 属于科学配置，当前绘图入口会沿用上游记录的值，不会应用当前配置里的新值。不要手工改 manifest。

当前没有 `--force` 或覆盖选项。签名不匹配、文件缺失或失败留下的非空输出目录会被拒绝。检查后将失败目录移到别处，或选择新的输出目录，再运行该步。

## 常见报错

| 现象或报错 | 原因与处理 |
| --- | --- |
| `Incomplete upstream artifacts` | 上游没跑完、路径错误或产物缺失；先检查 manifest 和上游文件，再显式重跑 |
| `Expected ... artifacts from steps ...` | 输入类型错误，例如把 metrics 当成二维坐标；按依赖表换成正确目录 |
| `Input system mismatch` / `Input route mismatch` | 配置系统或指定 route 与产物不同；不要混用两套系统 |
| `PCA artifacts lack ...` | PCA 中没有实验所需角色；检查路线支持范围，尤其是 peptidase 的 train-only 路线 |
| OOD 要求显式上游目录 | Python 入口缺 `--sampling`；先运行 sample 并传其目录 |
| `Output is occupied ...` | 输出与本次签名不符或不完整；使用新目录，不会自动覆盖 |
| `Path leaves project` / 输出路径限制 | 输入输出不在配置所属项目中，或输出不在 `output_root` 下 |
| PCA 维数超过矩阵形状 | 样本/特征不足；降低 `n_components`，准备新 PCA，并同步检查 unseen 的 `n_pcs` |
| t-SNE perplexity / UMAP neighbors 过大 | 对当前降维数据（unseen 是每个 class）降低对应参数；总行数还须至少 4 |
| `Need >... families` | structure 的合格 family 太少；检查数据，合理降低最大 k 或 family 大小门槛 |
| ID 重复、metadata 缺失、维度不一致、train 重叠 | 修正输入和对应配置；不会静默丢弃问题行 |
| unseen 无图或部分 class 缺失 | 查看两个 skipped JSON；指标与图的纳入规则不同，不一定是失败 |
| BA 部分分数为空 | 查看 `invalid_reason`，判断是缺质心、单标签还是退化半径 |

## 代码归属与验证

| 位置 | 职责 |
| --- | --- |
| `workflows/<实验>.sh` | 本实验的路径约定、单步调用和 all 顺序 |
| `workflows/<实验>.py` | 连接到本实验 CLI 的可执行入口 |
| `src/embedding_analysis/experiments/<实验>/workflow.py` | 本实验的步骤、输入依赖与执行选择 |
| 同目录 `compute.py` | 本实验的数据组织及独立计算任务 |
| 同目录 `metrics.py` | 本实验的指标定义；overview 无此文件 |
| 同目录 `plotting.py` | 本实验的空间图、指标图和比较图 |
| 同目录 `summary.py` | 本实验跨路线汇总；overview 无此文件 |
| OOD / unseen 的 `sampling.py` | 各自的抽样策略 |
| 公共 `prepared.py`、`reduction.py` | PCA、已处理数据读取、二维降维 |
| 公共 `runtime.py`、`artifacts.py` | 参数与产物检查、缓存和完成记录；不分派实验 |

不存在中央实验注册表，不共享实验指标或绘图实现。两套系统在同一实验内复用代码，通过配置区分类别、输入和样式。

```bash
# 数值回归、输入校验、步骤隔离、实验导入隔离及汇总测试
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
# 读取真实小样本，运行两套系统的实际降维及全部适用步骤
.venv/bin/python scripts/smoke_real_data.py
```

Smoke 输出在 `outputs/smoke/` 内的独立小样本项目，不是生产全量结果。完整计算定义见 [METHODS.md](../docs/METHODS.md)，暂缓内容见 [DEFERRED.md](../docs/DEFERRED.md)，验证范围见 [VALIDATION.md](../docs/VALIDATION.md)。

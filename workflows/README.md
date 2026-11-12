# 实验分步操作手册

本文对应当前独立实验实现。每个实验自己管理流程、指标和绘图；公共层提供 PCA、t-SNE/UMAP、数据读写及产物校验。所有指标使用 PCA 特征计算，不使用二维图坐标。输出按系统、workflow、用途和 route 组织。

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
| `esm2` | 五个主实验 | 没有该原始 ESM2 输入 |
| `esm2__l0-ft-ce` | 五个主实验 | 五个主实验 |
| `esm2__l1-ft-ce` | 五个主实验 | 五个主实验 |
| `esm2__l2-frozen-nca` | 五个主实验 | 五个主实验 |
| `esm2__l1-ft-ce__l2-frozen-nca` | 五个主实验 | 只有 train；仅 overview、centroid |
| `esm2__l2-ft-ce` | 五个主实验 | 五个主实验 |

route 从 `esm2` 起，训练阶段用 `__` 连接；`l0/l1/l2` 为二分类、大类、family，`ft/frozen` 为微调 backbone / 冻结上游表示，`ce/nca` 为训练损失。两个系统的 l1 都直接从 ESM2 训练。Peptidase 的 l0 是二分类微调结果，不是原始 ESM2。

下文完整示例统一采用 CAZy 的 `esm2__l2-frozen-nca`。换成 `configs/peptidase.json` 即运行另一系统；每条路线的 PCA 需分别准备。

## 输出组织与找图

系统是第一层，CAZy 和 peptidase 的结果、缓存、索引完全分开。以下只展示存在产物时才创建的目录：

```text
outputs/
├── cazy/
│   ├── RESULTS.md
│   ├── _shared/pca/<route>/
│   ├── overview/
│   │   ├── RESULTS.md
│   │   ├── figures/index.html
│   │   ├── figures/<route>/
│   │   └── artifacts/<route>/<step>/
│   ├── boundary/
│   │   ├── figures/<route>/
│   │   ├── figures/summary/
│   │   ├── tables/<route>/
│   │   ├── tables/summary/
│   │   ├── artifacts/<route>/<step>/
│   │   ├── artifacts/summary/<step>/
│   │   └── artifacts/_shared/sample/
│   ├── binary/
│   ├── multilabel/
│   ├── unseen/
│   └── centroid/
└── peptidase/
    └── 同样的布局，按实际产物创建
```

| 用途 | 内容 | 查看入口 |
| --- | --- | --- |
| `figures` | 最终 PNG；空间图和指标图（图例随主图显示） | `<workflow>/figures/index.html` 提供图片预览 |
| `tables` | 逐样本指标、统计摘要、跨路线汇总表 | `<workflow>/RESULTS.md` 列出表格链接 |
| `artifacts` | 坐标、抽样清单、执行日志、manifest 等 | 运行检查或继续下游步骤时使用 |
| `_shared/pca` | 同系统、同路线共享的 train-only PCA | 各主实验自动查找；binary 不使用它 |

例如找 CAZy Boundary 图，直接进入 `outputs/cazy/boundary/figures/`。单路线目录中是 `tsne_balanced.png`、`tsne_per_ood_panels.png`、`silhouette.png` 等，汇总图在 `summary/silhouette.png`。默认只生成 PNG。UMAP 文件用 `umap_` 前缀，两种方法不会互相覆盖。

索引在步骤完成后自动更新；程序会打印本步骤的 checkpoint、图片目录、表格目录和预览链接。未运行的实验不创建空目录。`manifest.json` 位于 checkpoint 中，以逻辑文件名记录最终文件的相对位置、大小和 SHA256；不要手工移动单张图或修改 manifest。

## 命令形式与独立步骤

### Shell 入口

```bash
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce metrics
```

参数是 `CONFIG ROUTE STEP [VERSION]`。第四个参数是可选版本名称，不是路径。系统名称从配置中的 `system` 读取，不根据配置文件名猜测。

可用入口为 `overview.sh`、`boundary.sh`、`binary.sh`、`multilabel.sh`、`unseen.sh`、`centroid.sh`。不指定步骤时显示帮助。一次只执行一个步骤；显式指定 `all` 才执行该实验的全部步骤，空间实验会包括 t-SNE、UMAP 及两种图。

### Python 入口

```bash
.venv/bin/python workflows/boundary.py metrics --config configs/cazy.json --route esm2__l0-ft-ce
.venv/bin/python workflows/overview.py visualization --config configs/cazy.json --route esm2__l0-ft-ce --method tsne
```

默认按系统、workflow、route 自动寻找上游并决定输出位置，不再接受 `--output` 或任意输出根目录。Python 绘图子命令为 `visualization`，用 `--method tsne|umap` 选择坐标，默认 t-SNE；shell 对应 `visualization-tsne` / `visualization-umap`。

`--input` 仍可显式指定同系统、同版本的上游 checkpoint；其 manifest 必须类型正确、完整有效。例如：

```bash
.venv/bin/python workflows/overview.py visualization --config configs/cazy.json   --input outputs/cazy/overview/artifacts/esm2__l0-ft-ce/tsne
```

显式输入可从 manifest 推断 route 和降维方法。跨系统、跨版本的输入均拒绝。路径按配置所在项目根目录解析；配置文件应放在项目的 `configs/` 下。

### 依赖

```text
原始 embedding + metadata → 共享 train-only PCA
                              ├→ metrics → metric-plots
                              ├→ tsne    → visualization-tsne
                              └→ umap    → visualization-umap
Boundary：原始 ID → sample → metrics / tsne / umap
Centroid：PCA → metrics（含质心）→ visualization / metric-plots
Binary：两组 train → 独立联合 PCA → tsne / umap → visualization
```

各步骤独立，不自动补跑上游。指标计算、t-SNE 和 UMAP 是并列分支。缺上游会报错，也不会从另一个系统或默认版本借用结果。

## 公共 PCA

```bash
.venv/bin/python workflows/pca.py prepare --config configs/cazy.json --route esm2__l0-ft-ce
# 等价入口
bash workflows/overview.sh configs/cazy.json esm2__l0-ft-ce pca
```

逐行 L2 归一化，在目标 train 上拟合 PCA，再转换同路线的其他角色，默认 100 维。`non_target_train` 专供 binary 联合 PCA，公共 PCA 跳过该角色。每个 `prepare` 一起执行 fit 和 transform，不提供单独 fit/transform 子命令。

输出在 `outputs/<system>/_shared/pca/<route>/`：

| 文件 | 内容 |
| --- | --- |
| `pca_model.joblib` | L2 Normalizer 与 PCA 模型 |
| `<role>.npz` | `ids` 和 float32 `values` |
| `<role>.metadata.csv` | 对齐的 sequence_id、class_label、family_label、dataset_role |
| `explained_variance.csv` | component、explained_variance、cumulative |
| `manifest.json`、`run.log` | 配置、输入指纹、产物校验、执行记录 |

角色包括 train、multi、unseen、ood、shuffled、idr，以配置实际输入为准。同系统同路线的主实验复用此结果，binary 单独拟合。

## Overview：训练空间展示

```bash
bash workflows/overview.sh configs/cazy.json esm2__l0-ft-ce pca
bash workflows/overview.sh configs/cazy.json esm2__l0-ft-ce tsne
bash workflows/overview.sh configs/cazy.json esm2__l0-ft-ce visualization-tsne
```

只有 train，不计算指标。UMAP 可单独运行 `umap`、`visualization-umap`。

| 位置（相对 `outputs/<system>/overview/`） | 内容 |
| --- | --- |
| `figures/<route>/tsne_classes.*` | class 着色 + class 名称 |
| `figures/<route>/tsne_class_label_family.*` | class 着色 + 高频 family 名称 |
| `artifacts/<route>/tsne/coordinates.csv` | 全量 train 标签及 x/y |
| `artifacts/<route>/visualization-tsne/annotated_families.json` | 标注的 family 列表及选择比例 |

高频 family 按每个 class 内序列数排序，取 family 种类数的前 15%，向上取整；不是覆盖 15% 的序列。沿用原配色、透明散点、中位数位置标签、白色标签底及方向箭头。class 名称和序列数量的图例直接放在每张主图上方，不再单独保存图例。默认 Arial、300 dpi、12×10 英寸；密集区域的中位数标签可能重叠。

## Boundary / Exp1

```bash
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce pca
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce sample
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce metrics
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce tsne
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce visualization-tsne
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce metric-plots
```

需要 train、ood、shuffled、idr；ood 是 non-target test。`sample` 在系统内各可用 route 的 ID 交集上按 seed/role/ID 的 SHA256 排序，分别选至多 3145 条；train 全量。清单存到 `artifacts/_shared/sample/sampling.json`，所有路线共用。Python 可用 `--sampling` 指定同系统同版本的另一个合法 sample checkpoint，通常无需填写。

`metrics` 将每类 target 分别与 train 组成两个组，在 PCA 空间计算精确 Euclidean silhouette，只保存 target 的分数。t-SNE/UMAP 联合使用 train 与同一份采样清单中的三类 target。没有 kNN OOD score。

| 位置（相对 `outputs/<system>/boundary/`） | 内容 |
| --- | --- |
| `tables/<route>/silhouette_samples.csv` | sequence_id、dataset_role、silhouette |
| `tables/<route>/silhouette_summary.csv` | 按角色给出 count、mean、median、std、min、max |
| `figures/<route>/tsne_balanced.*` | BuGn train hexbin + 三类 target 散点与轮廓 |
| `figures/<route>/tsne_per_ood_panels.*` | 相同范围的三类分面，每面一类 target |
| `figures/<route>/silhouette.*` | 单路线逐样本箱线图 |
| `artifacts/<route>/tsne/coordinates.csv` | sequence_id、dataset_role、x、y |
| `artifacts/<route>/metrics/` | manifest、sampling.json、日志；统计 CSV 已发布到 tables |

balanced 的 90% 轮廓取样本密度第 10 百分位为阈值；分面的 80% 轮廓取第 20 百分位。它不是积分概率质量。silhouette 越高表示更靠近本组，不是 OOD 概率。箱线图顺序为 shuffled、IDR、non-target，保留离群点和零线，默认纵轴 [-0.2, 1]；范围外分数仍完整保存到 CSV。

## Binary：目标 / non-target train 二分类图

```bash
bash workflows/binary.sh configs/cazy.json esm2__l0-ft-ce pca
bash workflows/binary.sh configs/cazy.json esm2__l0-ft-ce tsne
bash workflows/binary.sh configs/cazy.json esm2__l0-ft-ce visualization-tsne
```

同路线的 train 与 non_target_train 全量联合 L2-normalized PCA100，再联合降至二维。它不使用 Boundary 的 test，不抽样，也不读取公共 train-only PCA。

CAZy 具备输入的路线：esm2、L0 FT-CE、L1 FT-CE、L2 frozen-NCA、L1 FT-CE → L2 frozen-NCA。L2 FT-CE 原目录没有 non-CAZy train，无法运行。Peptidase 尚未配置 non-target train。

| 位置（相对 `outputs/<system>/binary/`） | 内容 |
| --- | --- |
| `artifacts/<route>/pca/` | joint.npz、metadata.csv、pca_model.joblib、explained_variance.csv |
| `artifacts/<route>/tsne/coordinates.csv` | sequence_id、dataset_role、x、y |
| `figures/<route>/tsne_cazy_vs_noncazy.*` | 灰色 non-target、红色 target，名称标签、数量图例与箭头 |

manifest 的 `fit_on` 明确记录两组 train。默认 Arial、300 dpi、12×10 英寸。`plot.binary` 可设置字体、dpi 和类别显示名称。

## Multilabel / Exp2

```bash
bash workflows/multilabel.sh configs/cazy.json esm2__l0-ft-ce pca
bash workflows/multilabel.sh configs/cazy.json esm2__l0-ft-ce metrics
bash workflows/multilabel.sh configs/cazy.json esm2__l0-ft-ce tsne
bash workflows/multilabel.sh configs/cazy.json esm2__l0-ft-ce visualization-tsne
bash workflows/multilabel.sh configs/cazy.json esm2__l0-ft-ce metric-plots
```

需要 train 和 multi。BA 固定 class-level，用 train 单标签 class 质心与 multi 标签组合计算；多标签以 `|` 解析。没有 family BA 或 bridge score。指标使用 PCA 特征，空间图独立降维 train+multi。

| 位置（相对 `outputs/<system>/multilabel/`） | 内容 |
| --- | --- |
| `tables/<route>/ba_samples.csv` | 逐样本 BA，字段以表头为准，包括 sequence_id、class_label、ba_score |
| `tables/<route>/ba_summary.csv` | 按 class 组合统计 count、mean、std、min、25%、50%、75%、max |
| `figures/<route>/tsne_classes.*` | 单标签 class 着色，multi 灰色背景，上方/右侧 KDE |
| `figures/<route>/tsne_combo_<组合>.*` | 单个组合高亮，父 class 淡色，其余灰色，上方/右侧 KDE |
| `figures/<route>/tsne_combos_<组合>__<组合>.*` | 多个重点组合同时高亮（至少两个组合存在时生成） |
| `figures/<route>/ba.*` | 所有达标组合的 BA KDE 叠加图 |
| `figures/<route>/ba_combos/ba_combo_<组合>.*` | 每个达标组合的直方图（30 bins）＋KDE、均值和 BA=0/1 参考线 |
| `artifacts/<route>/tsne/coordinates.csv` | 二维坐标及标签 |

Multilabel 空间图沿用旧 `exp2/debug/plot_umap_multi_white.py` 的白底风格，并增加上方 KDE：单标签点较小且透明，多标签点为较大、白边圆点；CAZy 的 `CBM|GH` 为蓝色、`CBM|PL` 为红色。所有视图保留同一套完整坐标和范围，不对组合单独降维或裁剪。左下角箭头标明实际降维方法；UMAP 输出将上述 `tsne_` 前缀替换为 `umap_`。

KDE 分别沿二维坐标的 x/y 轴计算，每类独立使用 Scott 带宽、400 点网格；不按样本数量加权，不表示 PCA 空间中的指标。样本不足 10 或坐标无方差时跳过该曲线，记录在对应 visualization 步骤的 `kde_skipped.json` 中。图例包含样本数，放在上方 KDE 之外并左对齐，字号 14，按可用宽度分列。PNG 默认 300 dpi；`plot.multilabel` 管理画布、字体、KDE 最小样本数、class 顺序和组合颜色。空间图由本实验的 `spatial.py` 管理；BA 指标图由本实验的 `plotting.py` 独立管理。

BA 单路线图只画有限分数不少于 `experiments.multilabel.min_combination_size`（默认 5）的组合，KDE 使用 Scott 带宽；常数分数保留直方图/垂直线，不拟合 KDE。跨路线 `tables` 同时生成 `summary.csv` 与带 route 的逐样本 `samples.csv`；`plots` 读取后者画分组 violin，不能仅凭均值表生成分布。沿用旧版筛选：未显式指定组合时，以传入的第一条 route 为参考，只取两个 class 的组合且有效样本数 > `plot.multilabel.ba_summary_min_n`（默认 30），按参考路线频数排序。图中灰线为中位数，N 为各路线有效样本数（不一致时按图例顺序列出）。默认显示范围 `plot.multilabel.ba_summary_ylim=[-7,1]` 沿用旧图，范围外尾部仅在图中裁切，原始分数和统计表完整保留。图例均为图外上方左对齐、14 号字。

CAZy 的 `plot.multilabel.combinations` 是空间单组合图和 BA summary 共用的默认组合清单，固定为当前 ESM2 参考数据中满足上述规则的九组（顺序一致）：`CBM|GH`、`CBM|PL`、`AA|CBM`、`CBM|CE`、`GH|GT`、`CBM|GT`、`CE|GH`、`CE|PL`、`CE|GT`。九组高亮颜色在 `plot.multilabel.combo_colors` 中显式固定，按与父 class 的对比及白底可见性选择；组合顺序改变不会改变配色。空间散点、边际 KDE 和 BA KDE 叠加图共用该映射。更换数据后如需更新这份固定清单，应同步修改此配置。空间绘图只读取已有坐标，不要求先运行 BA summary；t-SNE 和 UMAP 都按此清单逐组绘图。双组合叠加图仍由 `plot.highlight_combinations` 控制。未配置共用清单的系统，空间图沿用其重点组合配置，BA summary 沿用频数筛选。

`plot.multilabel.ba_summary_groups` 配置跨路线分组。CAZy 生成两张图，共用上述九组及相同纵轴范围：

- `figures/summary/ba_ftce.*`：ESM2、L0 FT-CE、L1 FT-CE、L2 FT-CE。
- `figures/summary/ba_frozen_nca.*`：ESM2、ESM2→L2 frozen-NCA、ESM2→L1 FT-CE→L2 frozen-NCA。

只绘制 summary 输入中实际存在的路线；空组不出图。未配置分组的系统生成 `ba_all.*`。重新运行 summary `plots` 会替换旧的单张 `ba.*`。各路线 BA 的 KDE 总览仍是 `figures/<route>/ba.*`，15 张达标单组合图放入 `ba_combos/` 子目录，与仅显示九组的 summary 筛选相互独立。

## Unseen：未见 family 分析

```bash
bash workflows/unseen.sh configs/cazy.json esm2__l0-ft-ce pca
bash workflows/unseen.sh configs/cazy.json esm2__l0-ft-ce metrics
bash workflows/unseen.sh configs/cazy.json esm2__l0-ft-ce tsne
bash workflows/unseen.sh configs/cazy.json esm2__l0-ft-ce visualization-tsne
bash workflows/unseen.sh configs/cazy.json esm2__l0-ft-ce metric-plots
```

需要 train 和 unseen。每个 class 内保留至少 2 条序列的 family，从合格 train family 中确定性选择至多 10 个参照，与 unseen 联合计算指标。空间图的背景使用该 class 全部 train，并不局限于抽样参照；指标与降维各自准备输入，跳过 class 清单可能不同。

| 位置（相对 `outputs/<system>/unseen/`） | 内容 |
| --- | --- |
| `tables/<route>/families.csv` | unseen 的逐家族指标，附 class_label |
| `tables/<route>/global.csv` | class 级联合/参照上下文的整体指标 |
| `tables/<route>/<class>/joint_families.csv` | 联合空间全部 train/unseen family 指标 |
| `tables/<route>/<class>/train_sample_families.csv` | 单独的 train 参照指标，至少两个 family 时生成 |
| `artifacts/<route>/metrics/reference_families.json` | 实际参照列表和样本数 |
| `artifacts/<route>/metrics/skipped_classes.json` | 指标跳过原因 |
| `artifacts/<route>/tsne/<class>/coordinates.csv` | class 内独立二维坐标 |
| `artifacts/<route>/tsne/skipped_visualization_classes.json` | 降维跳过原因 |
| `figures/<route>/<class>/tsne_families.*` | 灰色 train 背景上的 unseen family 图 |
| `figures/<route>/silhouette_mean.*`、`dunn_cosine.*`、`legacy_pairwise_dbi.*` | family 指标分布 |

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

## Centroid：family 质心结构

```bash
bash workflows/centroid.sh configs/cazy.json esm2__l0-ft-ce pca
bash workflows/centroid.sh configs/cazy.json esm2__l0-ft-ce metrics
bash workflows/centroid.sh configs/cazy.json esm2__l0-ft-ce visualization
bash workflows/centroid.sh configs/cazy.json esm2__l0-ft-ce metric-plots
```

只需要 train，在 PCA 空间对至少 5 条序列的 family 计算质心。每个 family 必须属于一个 class。此实验不做 t-SNE/UMAP，空间展示是质心距离热图。

绘图参照旧 CAZy `metrics/src/knn_purity.py` 和 Peptidase `metrics/src/class_structure.py`：Arial、300 dpi，纯度曲线纵轴固定 0–1，粉色表示 Direct L2 NCA，红色表示 L1-conditioned L2 NCA，图内使用带边框图例。热图使用 `viridis_r`，按既有 class 顺序及 family 名称排列，带顶部/左侧 class 色带、class 分界线和稀疏 family 标签。色带与标签分别布局，避免旧图中的重叠。

可用 `plot.centroid` 覆盖 `font`、`dpi`、`purity_figsize`、`heatmap_figsize`、`class_order`、`route_labels` 和 `route_colors`；文件格式仍遵循 `plot.formats`。这些配置仅影响绘图，不改变指标。

原始 ESM2 基线使用 `esm2` route，图例显示为 `ESM2`（灰色）。与两种 NCA 路线对比时，先分别完成三个 route 的指标，再生成汇总：

```bash
bash workflows/centroid.sh configs/cazy.json esm2 all
.venv/bin/python workflows/centroid_summary.py tables --config configs/cazy.json --routes esm2 esm2__l2-frozen-nca esm2__l1-ft-ce__l2-frozen-nca
.venv/bin/python workflows/centroid_summary.py plots --config configs/cazy.json
```

| 位置（相对 `outputs/<system>/centroid/`） | 内容 |
| --- | --- |
| `artifacts/<route>/metrics/centroids.csv` | family_label、class_label、n_sequences、PC1...PCn |
| `tables/<route>/metrics.csv` | metric、k、value |
| `figures/<route>/centroid_distances.*` | 按 class/family 排序的 Euclidean 距离热图 |
| `figures/<route>/knn_class_purity.*` | 不同 k 的同 class 邻居比例 |

metric 包括 knn_class_purity、class_silhouette、median_within_class、median_between_class、between_over_within。只有第一个使用 k，其他行 k 为空。默认 k 为 1、3、5、7、9，合格 family 数需大于最大 k。这是质心结构指标，不是已取消的 kNN OOD score。

## 跨路线汇总

四个实验各有自己的 summary 入口。先完成要比较的各路线 `metrics`，再运行：

```bash
.venv/bin/python workflows/boundary_summary.py tables --config configs/cazy.json   --routes esm2__l0-ft-ce esm2__l1-ft-ce esm2__l2-ft-ce
.venv/bin/python workflows/boundary_summary.py plots --config configs/cazy.json
```

`--routes` 按传入顺序读取对应指标，不要求所有路线都完成。也可以用 `--inputs` 显式列出同系统同版本的指标 checkpoint；不能同时传两种选择参数。不要重复输入同一路线。

表格输出在 `<workflow>/tables/summary/`；manifest 在 `<workflow>/artifacts/summary/tables/`；图在 `<workflow>/figures/summary/`，绘图 manifest 在 `artifacts/summary/plots/`。

| 实验 | 汇总表 | 汇总图 |
| --- | --- | --- |
| Boundary | 带 route 的 summary.csv 与逐样本 samples.csv | silhouette.*；按路线分组的三类 target 箱线图 |
| Multilabel | 带 route 的 summary.csv 与逐样本 samples.csv | ba_ftce.*、ba_frozen_nca.*（CAZy）；双 class 组合的逐样本 BA 分组 violin |
| Unseen | 带 route 的 family 指标 summary.csv | silhouette.*；各 class 的 family silhouette 均值，family 等权 |
| Centroid | 带 route 的 metrics 长表 summary.csv | knn_class_purity.*；不同 k 的纯度 |

Overview 和 binary 没有指标汇总入口。空数据不一定生成图，应查看表头、行数和跳过记录。

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
| `experiments.boundary.target_size` | 3145 | 每种 OOD 的最大抽样数，不保证交集有这么多 |
| `experiments.boundary.distance / chunk_size` | `euclidean / 512` | silhouette 距离及分块大小 |
| `experiments.multilabel.label_level` | `class` | 只支持 class BA |
| `experiments.multilabel.min_combination_size` | 5 | BA 分布图的组合大小门槛 |
| `experiments.unseen.n_pcs` | 100 | 取前多少 PC，不能超过已保存的 PCA 维数 |
| `experiments.unseen.min_family_size` | 2 | 合格 family 的最少序列数 |
| `experiments.unseen.train_family_count` | 10 | 每类最多选择多少个 train 参照 family |
| `experiments.unseen.chunk_size` | 256 | family 距离计算分块大小 |
| `experiments.centroid.min_family_size / ks` | `5 / [1,3,5,7,9]` | family 门槛和质心邻居统计 |
| `plot.dpi / formats / point_size` | `180 / [png] / 3` | 通用导出设置；overview 和 boundary 使用下面各自的 dpi，格式仍共用 |
| `plot.overview.dpi / font / top_family_fraction` | `300 / Arial / 0.15` | overview 分辨率、字体及每类高频 family 的种类比例 |
| `plot.overview.class_order` | 系统配置 | class 绘制及图例顺序 |
| `plot.boundary.dpi / font` | `300 / Arial` | boundary 空间图及指标图导出 |
| `plot.boundary.hexbin_gridsize / hexbin_cmap / hexbin_vmax_mult` | `120 / BuGn / 1.5` | 背景密度网格、配色及 balanced 亮度；分面不使用亮度倍数 |
| `plot.boundary.point_size / alpha` | `10 / 0.55` | target 散点样式 |
| `plot.boundary.contour_percentile / panel_contour_percentile` | `90 / 80` | balanced / 分面 KDE 样本覆盖比例 |
| `plot.boundary.silhouette_single_figsize` | `[3.6, 6]` 英寸 | 单路线 silhouette 使用瘦高版式，图例置于图上方；跨路线汇总保持 10×4 英寸 |
| `plot.boundary.silhouette_ylim` | `[-0.2, 1]` | 单路线及跨路线箱线图纵轴范围 |
| `plot.boundary.role_labels` | 系统配置 | 图例和分面角色名称 |
| `plot.highlight_combinations` | 系统配置 | Multilabel 重点组合 |
| `plot.legend.fontsize` | `14` | 所有类别图例字号；图外上方左对齐，按实际宽度自动分列/换行，无边框 |
| `class_colors` | 系统配置 | class 颜色 |

配置中仍存在 `experiments.<实验>.method` 字段，但当前独立入口不使用它选择降维：以执行的 `tsne` / `umap` 子命令为准，shell 的 `all` 会执行两种方法。

当前每个实验的多个指标仍由一个 `metrics` 步骤一起计算；一个空间绘图步骤会导出该实验适用的全部空间图，没有逐指标或逐图的选择参数。

## 覆盖、缓存与版本

默认使用固定位置。签名一致、全部产物存在且大小/SHA256 匹配时打印 `Cached`；配置或代码变化、产物缺失或损坏时重算当前步骤。签名仍包含完整配置、整个包的代码摘要及上游记录，因此无关代码/配置变动也可能使某步缓存失效。

计算先写到该步骤旁边的隐藏 `.步骤.work/`；成功后发布新图表、替换 checkpoint，并清理上一版 manifest 中本步骤已不再生成的文件。例如从 PNG/PDF 改为只输出 PNG，会删除该步骤旧 PDF。其他步骤或路线的产物不清理。失败计算保留工作目录和日志，旧的完整结果保留；同一步已有进程运行时拒绝第二次执行。

原始 embedding 的输入指纹使用路径、大小、mtime 和首尾摘要；完成产物使用完整 SHA256。下游不会自动重建上游，也不会因为原始 embedding 变更自动补跑 PCA；改科学配置后应沿相应依赖分支显式重跑。

### 只改样式重画

```bash
bash workflows/overview.sh configs/cazy.json esm2__l0-ft-ce visualization-tsne
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce metric-plots
```

修改配置中的绘图选项后再运行即可原位替换，无需新建目录。绘图科学配置来自上游 manifest；当前配置只有 `plot` 和 `class_colors` 覆盖进去。因此改图的 dpi 可以直接重画，改筛选门槛等科学参数需要先重跑相应计算步骤。

### 显式保留一套新版本

```bash
bash workflows/boundary.sh configs/cazy.json esm2__l0-ft-ce all trial_v2
# Python 等价版本参数
.venv/bin/python workflows/boundary.py metrics --config configs/cazy.json --route esm2__l0-ft-ce --version trial_v2
```

版本输出为 `outputs/cazy/_versions/trial_v2/`，其中仍按 workflow/用途/route 组织；版本内有自己的共享 PCA 和索引。版本不读取默认结果，也不跨版本借用上游。版本名只允许字母、数字、下划线和连字符。

## 成功检查与常见错误

检查结束输出的路径、manifest、统计表有效行数、实际采样数量及跳过原因。退出码为 0 不意味着每个 class 都有可用结果。

| 报错 | 处理 |
| --- | --- |
| Incomplete upstream artifacts | 上游缺失、未完成或校验失败；显式运行上游 |
| Expected ... artifacts | 指定了错误类型的输入，例如把 metrics 当作 tsne |
| same system and output version / Input system mismatch | 配置与输入所属系统或版本不同，不能混用 |
| Input route mismatch | --route 与输入 manifest 不同 |
| This step is already running | 等当前执行结束，避免并发写同一步 |
| PCA artifacts lack ... | 该路线缺少实验所需角色；检查配置可用范围 |
| Route has no non_target_train embedding | binary 没有对应训练输入，不能用 test 代替 |
| PCA 维数超过矩阵形状 | 样本或维度不足；调整 n_components，并检查 unseen n_pcs |
| perplexity / neighbors 过大 | 调低降维参数；unseen 按 class 检查样本数 |
| Need >... families | centroid 合格 family 太少；检查数据或合理调整最大 k |

## 代码归属与样式来源

各实验的 `workflow.py`、`compute.py`、`metrics.py`（如有）、`plotting.py`、`summary.py`（如有）只管理本实验。`runtime.py` 与 `output.py` 负责公共路径、校验、发布和索引，不派发实验计算。PCA 与二维降维仍共享 `prepared.py` / `reduction.py`。

Overview 样式来自原 `normpca100/train_plot/src/plot_class.py` 和 `plot_class_label_family.py`；binary 来自 `plot_binary.py`；Boundary 来自 `exp1/src/plot_tsne_labels.py`、`plot_per_ood_panels.py` 及 `silhouette_balanced/src/plot_silhouette_balanced_box.py`。实现都在本项目内部，不运行或导入原目录代码。

## 图例位置

所有类别图例放在图外上方、与绘图区左边缘对齐；有标题时图例位于标题上方。根据渲染后的文字宽度安排分列，单条过长时换行，不扩展图片宽度。图例字号默认 14，无边框。Overview 图例包含 class 名称和数量，随主图保存，不再输出独立 legend 文件。Multilabel/Unseen 类别较多时完整保留图例，不再因为超过 25 类而隐藏。Boundary 分面仍使用类别标题；不需要类别图例的单曲线/箱线图维持轴标签，Centroid 热图的 colorbar 仍放右侧。

## Peptidase 当前运行范围

Peptidase 使用同一组独立 workflow，默认只保存 PNG，同时支持 `tsne`、`umap` 和对应 `visualization-*` 步骤。

- overview：配置中的五条路线。
- boundary、multilabel：L0 FT-CE、L1 FT-CE、L2 FT-CE、ESM2→L2 frozen-NCA；L1→L2 frozen-NCA 缺少相应评估数据，仅运行 overview。
- binary：目前仅 L0 FT-CE 有 non-peptidase train。输入独立复制到本项目 `data/peptidase/embeddings/esm2__l0-ft-ce/`；来源及 SHA256 在 `data/peptidase/binary_import_manifest.json`。图片名为 `tsne_peptidase_vs_nonpeptidase.png` / `umap_peptidase_vs_nonpeptidase.png`。重新传输的 CSV 已替换原损坏副本：88,642 条、1280 维，逐行数值/维度、ID 唯一性及 train ID 不重叠检查通过，复制后 SHA256 一致。旧文件仅有 5,081 行且其中 99 行字段损坏，不用于实验。

multilabel 固定六组及显示顺序：`C|M`、`C|N`、`C|S`、`N|S`、`M|S`、`S|T`。`plot.multilabel.combinations` 控制单组合空间图和 BA summary；`ba_plot_combinations` 将单路线 BA KDE 总览及 `ba_combos/` 中的图也限定到这六组（仍须满足最小有效样本数）。BA 数值照常计算全部 multi 样本，不通过绘图筛选删数据。每条路线生成 class 总览和六张单组合空间图，未启用组合叠加图。组合颜色显式固定并用于散点、边际 KDE 和 BA KDE 总览。

Peptidase 没有原始 ESM2 基线；BA summary 的 `ba_all.png` 比较上述四条有 multi 数据的路线，不伪造缺失路线。输出位于 `outputs/peptidase/`，与 CAZy 完全独立。

## 原始 ESM-1b / ESM2 650M 的 pooling 对比

`configs/cazy_raw_pooling.json` 配置四条 train-only 路线：`esm1b__pool-cls`、`esm1b__pool-residue_mean`、`esm2-650m__pool-cls`、`esm2-650m__pool-residue_mean`。输入软链接指向 `runs/embeddings/cazy/<model>/raw_pooling_20261109_130201/<pooling>/`，原始导出 manifest 保存在配置中。各组使用相同 CAZy train metadata；只读取 train，不将 test 纳入拟合。

各组独立执行 L2 normalization → train-fit PCA100 → t-SNE，seed=42、perplexity=30、250+500 iterations，均沿用 defaults 参数。每组的 class 与 class/family 图共用一份坐标，family 按每个 class 内频数排序标注前 15% 的 family 种类。独立 t-SNE 的旋转、位置和尺度不用于直接距离比较。

```bash
.venv/bin/python workflows/validate.py --config configs/cazy_raw_pooling.json --deep
bash workflows/overview.sh configs/cazy_raw_pooling.json esm1b__pool-cls pca raw-pooling-20261109
bash workflows/overview.sh configs/cazy_raw_pooling.json esm1b__pool-cls tsne raw-pooling-20261109
bash workflows/overview.sh configs/cazy_raw_pooling.json esm1b__pool-cls visualization-tsne raw-pooling-20261109
```

批处理入口 `workflows/raw_pooling.slurm` 使用 array 0–3，顺序为 ESM-1b CLS、ESM-1b residue mean、ESM2 650M CLS、ESM2 650M residue mean。输出位于 `outputs/cazy/_versions/raw-pooling-20261109/overview/figures/<route>/`，每条路线生成 `tsne_classes.png` 和 `tsne_class_label_family.png`。日志位于 `outputs/cazy/logs/raw-pooling-20261109/`。

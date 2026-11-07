# 第一阶段计算约定

## 输入与预处理

每条 route 在 train 上独立拟合 L2 Normalizer + PCA(100)，然后转换 multi/unseen/OOD。所有距离都在明确记录的 PCA 空间计算；不使用二维图坐标计算指标。缺少 ID、重复 ID、元数据不匹配、train 与 unseen/multi 重叠都会报错。

## Boundary

每个系统内，分别对 non-target、shuffled、IDR 取各可用 route 的 ID 交集，再按 seed + role + ID 的 SHA256 排序选至多 3145 条。train 全量。固定 manifest 同时用于 silhouette 和 t-SNE，跨 route 共享。小于目标数时记录 actual/common_count/source_counts。

每个 target 单独对 train 计算二组 Euclidean silhouette，仅输出 target 的分数。逐块精确计算，不构造全量两两矩阵。balanced 图的 KDE 线沿用旧版 90% 样本覆盖定义：取样本密度值的第 10 百分位作为阈值；三类分面使用 80% 样本覆盖，即第 20 百分位阈值。此定义不声称包围相应比例的积分概率质量。

## Class BA

单标签 train 的每个 class 质心为 $c_i$。对 multi 的 $k$ 个不同 class，定义：

$$
b=\frac{1}{k}\sum_i c_i,\qquad r=\frac{1}{k}\sum_i\|c_i-b\|,\qquad BA(x)=1-\frac{\|x-b\|}{r}.
$$

缺质心、只有一个 class 或半径为零时输出 NaN 及原因。不实现 family-level BA。

## Unseen family

每个 class 内保留至少 2 条序列的 unseen families，并选择至多 10 个有效 train families 作为参照。family 抽样以 seed/class/family 哈希排序；候选相同则跨 route 一致，具体参照列表写入 reference_families.json。图的灰色背景使用该 class 的全部 train，不只参照样本。

joint 指标的上下文是 unseen + sampled train。Silhouette、Dunn 使用 cosine；CH 和标准全局 Davies–Bouldin 使用 Euclidean。分家族 silhouette 的最近对照可能是另一个 unseen family，区别于 held-out 的 train-only reference 模式。

`legacy_pairwise_dbi` 保留旧 Exp3 的定义：family 内平均两两 Euclidean 距离作为 scatter，再求各家族 scatter 之和与质心距离之比的最大值。它不是标准 DBI 的分解，不能与全局 `davies_bouldin_euclidean` 混为一谈。

全局字段明确区分 `joint_unseen_and_sampled_train` 与 `sampled_train_only`。距离分块归约，避免旧代码为整个 class 分配 N×N 距离矩阵。

## Family centroid centroid

保留至少 5 条序列的 train family，计算质心。报告质心的 class silhouette、类间/类内距离中位数之比，以及 k=1,3,5,7,9 的同 class 邻居比例。排除自身按索引判断，避免重合质心时误删邻居。

## 降维、缓存与历史差异

共用 openTSNE（PCA initialization，250/500 iterations）和 umap-learn。旧 scanpy UMAP 不迁移。新的固定 ID 抽样、严格元数据校验和哈希 family 抽样可能使结果不同于旧脚本；不承诺重现所有旧图坐标。

每个独立步骤使用显式输入、输出目录。签名记录配置、代码摘要和上游 manifest；PCA / sample 另记录原始输入路径、大小、mtime 和首尾摘要（不是全文件校验和）。相同签名可复用完成产物；参数或输入变化时需指定新输出目录，不覆盖既有结果。指标、二维降维和两类绘图分别运行，任何步骤都不自动补跑上游。

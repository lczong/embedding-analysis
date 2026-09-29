# 第一阶段范围

保留一份核心实现，以系统配置切换 CAZy / peptidase。

1. 输入校验、train-fit L2 normalization + PCA。
2. 训练集 class/family 空间展示。
3. OOD silhouette 与固定样本密度展示。
4. class-level BA、组合统计与联合空间展示。
5. class 内 unseen family 质量指标与展示。
6. family centroid class purity、silhouette、类间/类内距离比。

明确排除 kNN OOD score、Leiden 搜索/聚类流程、HDBSCAN、bridge score；不实现 family-level BA。

核心内部字段为 sequence_id、class_label、family_label、dataset_role。数据的实际文件名、CSV/NPY/分片格式、NPY ID 来源、路线可用性、显示颜色由配置描述。

## 提交步骤

1. 项目边界、暂缓清单与工程骨架。
2. 输入层、两套配置、本地数据导入与校验。
3. 共享指标、降维、实验流程、绘图及 CLI。
4. 回归测试、运行验证和使用文档。

不改动原目录和历史结果。不将数据、虚拟环境或生成结果提交到 Git。

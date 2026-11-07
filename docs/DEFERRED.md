# 第一阶段未纳入的功能与差异

此文件区分用户明确取消的功能、暂缓的实验，以及已经统一但与历史结果不同的处理。原目录完整保留，不删除旧实现。

## 明确取消

| 原位置 | 处理 |
| --- | --- |
| CAZy exp1/knn_ood、pca_knn_ood、src/knn_ood_score.py | 不迁移 kNN OOD score、ROC/PR 曲线 |
| CAZy exp3/leiden_explore、Leiden clustering/reports/interactive overlays | 不迁移搜索、聚类分配、簇-家族一致性和依赖这些分配的图 |
| CAZy exp3/hdbscan_explore | 不迁移 HDBSCAN、outlier 分析、扫描 |
| CAZy exp2/src/bridge_score.py | 不迁移 bridge score |
| peptidase exp2/src/barycentric_alignment.py | 不迁移 family-level BA；实际核心为 class 级 BA |

## 暂缓，不能视为已由共享流程替代

| 功能 / 原位置 | 差异与暂缓原因 |
| --- | --- |
| CAZy held-out 全局 family quality | 全 class、全训练家族参照，与首版 class 内抽样训练家族的分析不同 |
| held-out parent_localisation / nae_local | parent class top-k support、NAE、entropy 等训练集参照定位指标；首版没有复刻 |
| held-out native_family_diagnostics | 训练/校准划分、家族尺度校准、拒绝阈值、父类支持、cohort separation 等；独立实验体系 |
| held-out NCA focused/robust comparisons | route 特定对比、稳健性分析、局部案例图 |
| held-out plot_nca_local_cases | FASTA/序列比对、MDS、Procrustes、个别 family 案例分析 |
| held-out joint PCA visualization | train+unseen 联合拟合 PCA；首版仅 train-fit PCA，防止混入评估 |
| CAZy exp3/debug_quality | Euclidean、train-only reference、全训练家族等实验口径；没有用普通 Exp3 冒充 |
| CAZy exp3/knn_family_purity | 蛋白级 family 邻域纯度暂缓；已保留的是 family 质心的 class purity，两者不同 |
| 两套 exp3 compute_train_integration | 未见家族与训练家族的蛋白级邻域整合分析暂缓 |
| CAZy train_plot/run_binary | CAZy 与 non-CAZy train 联合拟合/二分类可视化；首版 train overview 用系统内训练集 |
| CAZy exp1 raw silhouette、cosine/PCA sweep | 首版统一 PCA 空间 Euclidean OOD silhouette；原始空间及额外距离对照暂缓 |
| CAZy exp1 非 balanced / IDR-only / density-aware / contour-only / log-ratio | 已恢复 balanced density、三类分面以及单路线/跨路线 silhouette 箱线图；其余绘图变体暂缓 |
| 两套 exp2 debug/marginal/KDE/white-background/per-combination variants | 首版保留统一 class/组合散点与 BA 分布；论文特定边际 KDE、白底布局等暂缓 |
| 两套 exp3 family KDE contours、percentile sweeps、拼图、交互 HTML | 首版保留通用 family 散点及指标摘要，暂不复刻所有论文版式 |
| 两套 train_plot 的固定 level1 专用图 | 已恢复 class 名称、高频 family 名称两种 class 着色图及独立图例；固定 level1 专用版式暂缓 |
| scanpy UMAP 实现 | 首版统一 umap-learn；旧 scanpy UMAP 坐标不会等同于新坐标 |
| normalized/ 输入路线 | 用户要求不动，首版不导入/使用 |
| 未使用的 val/test、non-target train、历史采样及压缩包 | 不为首版复制；旧目录保留 |
| 跨路线成套论文对比图 | Boundary 已恢复跨路线逐样本 silhouette 箱线图；其他固定路线组合的论文图暂缓 |

## 已显式统一的差异

- 原 peptidase level0 不是 raw ESM2；两个体系 level1 都直接从 ESM2 训练。配置只使用已确认 route。
- BA 固定 class-level，训练单标签类别质心，multi 的多类别标签用 `|` 解析。
- OOD 样本先生成独立 manifest，绘图和指标共用；同一系统不同路线使用可用 ID 的交集。CAZy l2-ft 只有预抽样 OOD，交集可能小于 3145；明确记录实际数量，不伪称完整 3145。
- 不同系统的序列不同，绝不共享 CAZy 与 peptidase 的样本 ID。
- peptidase l1→l2 只有 train；仅运行 overview / centroid；请求缺少输入的实验会报错。
- NPY 本身没有 ID；从显式 ids_reference 导入并检查行数/唯一性。行序一致性仍依赖数据来源约定，不能由行数检查证明。
- 原 Exp3 的 per-family DBI 使用平均两两距离作为 scatter，与 sklearn 全局 DBI 的 centroid scatter 不同。首版保留这一历史定义并使用明确字段名；不混称标准 DBI。
- Exp3 全局 joint 指标覆盖 unseen + sampled train，不能将其命名为仅 unseen 的 global score。
- 元数据缺失/重复 ID、错误维度不再静默 inner join 丢弃；默认报错。
- 计算、降维和绘图分离；缓存记录配置与输入指纹，改参数后不会只因旧输出存在而跳过。
- CAZy 有独立 `esm2` 基线，peptidase 目前没有对应原始 embedding；首版不伪造或用 level0 代替这一基线。
- peptidase 原有 centroid silhouette 和类间/类内距离比已推广到两个系统；CAZy 原来只有 centroid kNN purity，不代表旧 CAZy 结果中已有这些新增表。

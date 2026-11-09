# Embedding analysis

论文精选子图使用独立的 [paper 入口](paper/README.md)，目前已配置 Figure 2 c/d/e、Figure 3 b–i、Figure 4 b/c/d/h/i/j/k 和 Figure 5 b/c/h/i；读取现有实验坐标与指标，支持单独或整组导出 PNG/PDF/SVG，图例独立保存。

各实验独立管理流程、指标和绘图，共享 PCA、降维及数据读写。通过 `configs/cazy.json` / `configs/peptidase.json` 切换系统。第一阶段包括 train-fit PCA、训练空间展示、OOD silhouette、class-level BA、class 内 unseen family 质量，以及 family centroid 结构分析。

不包含 kNN OOD score、Leiden、HDBSCAN 或 bridge score。BA 只按 class 计算。

- [未纳入的功能和两套系统的差异](docs/DEFERRED.md)
- [计算定义及与旧版的差异](docs/METHODS.md)

## 分步骤运行（推荐）

完整逐步操作手册见 [workflows/README.md](workflows/README.md)，包含各实验的输入依赖、完整命令、输出文件及字段、配置参数、跨路线汇总、缓存重跑与报错处理。每个实验分别管理流程，指标、t-SNE、UMAP、空间绘图和指标绘图都可以单独执行：

```bash
bash workflows/boundary.sh configs/cazy.json esm2__l2-frozen-nca pca
bash workflows/boundary.sh configs/cazy.json esm2__l2-frozen-nca sample
bash workflows/boundary.sh configs/cazy.json esm2__l2-frozen-nca metrics
bash workflows/multilabel.sh configs/cazy.json esm2__l2-frozen-nca metrics
```

下游步骤不自动运行上游；train-only PCA 可以在实验之间复用。新增 `binary` 实验使用目标与 non-target train 联合 PCA，独立保存，不能与 train-only PCA 混用。运行 `bash workflows/binary.sh configs/cazy.json esm2__l0-ft-ce pca`、`tsne`、`visualization-tsne` 三个步骤即可生成二分类图。

## 输入检查

```bash
.venv/bin/python workflows/validate.py --config configs/cazy.json
```

加 `--deep` 读取全量数据验证 ID、有限值和 metadata 对齐。大文件会耗时。
Peptidase 的 `esm2__l1-ft-ce__l2-frozen-nca` 只有 train，仅支持 overview 和 centroid。

## 配置与数据

`defaults.json` 保存共享计算参数；系统配置覆盖 metadata 列名、class 配色、route 输入和格式。内部字段统一为 sequence_id、class_label、family_label、dataset_role。实际文件路径相对新项目根目录，不能指向外部。

初次导入 72 个文件，另补入 5 份 CAZy non-target train embedding。macOS 下使用 APFS 写时复制，副本有独立 inode，不是软链接/硬链接。原两个目录、原始结果以及 normalized/ 未改动。只导入核心需要的输入；两套系统的 metadata TSV 由 Git 跟踪，embedding 和环境不进入 Git。

运行只读取本项目 `data/`。迁移机器时一并复制该目录，按配置中的相对路径放置文件，再用 `workflows/validate.py` 检查。数据来源及初次复制校验记录保留在 `data/import_manifest.json`，它不参与运行。新增二分类数据的来源与 SHA256 记录在 `data/binary_import_manifest.json`。

NPY 的 ID 来源由 `ids_reference` 显式声明。它只能检查行数和 ID 完整性，不能仅凭文件推断行序正确。当前 peptidase 数据沿用原脚本的 level0 CSV 行序约定。

## 输出与找图

系统是第一层，CAZy 与 peptidase 的输出、缓存、索引独立：

```text
outputs/<system>/RESULTS.md
outputs/<system>/<workflow>/RESULTS.md
outputs/<system>/<workflow>/figures/index.html
outputs/<system>/<workflow>/figures/<route>/
outputs/<system>/<workflow>/figures/summary/
outputs/<system>/<workflow>/tables/<route>/
outputs/<system>/<workflow>/tables/summary/
outputs/<system>/<workflow>/artifacts/<route>/<step>/
outputs/<system>/_shared/pca/<route>/
```

找图进入 `figures/`，或打开 `figures/index.html` 浏览预览；指标表在 `tables/`。坐标、manifest、采样清单和日志留在 `artifacts/`。没有产物的目录不创建。binary 的联合 PCA 位于 `binary/artifacts/<route>/pca/`。

默认原位更新当前步骤，成功后清理本步骤的旧产物；配置和产物校验一致时复用。没有日期运行目录、重画副本目录，也不再传 `--output`。每次完成打印图、表和预览链接。需要保留不同参数实验时，shell 第四个参数或 Python `--version NAME` 将结果放到该系统的 `_versions/NAME/`，版本内独立管理全部依赖。

[CAZy 结果索引](outputs/cazy/RESULTS.md)。具体文件、独立步骤、缓存与覆盖行为见 [运行手册](workflows/README.md)。

## 移动或在其他机器安装

代码、configs 和 metadata TSV 随仓库克隆。embedding 需另行复制或在服务器生成，并保持配置中的相对路径。虚拟环境依赖本机系统 Python，换机器应重新创建：

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

核心依赖不包含 FAISS、scanpy、Leiden、HDBSCAN、Biopython 或 Plotly。

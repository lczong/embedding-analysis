# Embedding analysis

Workflow 完成后可用 `.venv/bin/python paper/report.py render --system cazy --model esm1b` 生成四页 PDF 拼图（训练空间、Boundary、Multilabel、指标对比），支持其他 base model 和 Peptidase，详见 [PDF 汇总入口](paper/README.md#按-base-model-汇总四页-pdf)。

论文精选子图使用独立的 [paper 入口](paper/README.md)，目前已配置 Figure 2 c/d/e、Figure 3 b–i、Figure 4 b/c/d/i/j/k/l 和 Figure 5 b/c/d/h/i/j；读取现有实验坐标与指标，支持单独或整组导出 PNG/PDF/SVG，图例独立保存。

测试集 performance 图使用独立的 [performance workflow](workflows/README.md#performance测试集性能图)：`bash workflows/performance.sh configs/cazy.json all`（或 `configs/peptidase.json`）。读取随仓库保存的报告，每个系统生成八张 PNG 主图，legend 保留在图内，支持按图名选择；无需 embedding、PCA 或 GPU，不重新计算预测指标。

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

`defaults.json` 保存共享计算参数；系统配置覆盖 metadata 列名、class 配色、route 输入和格式。内部字段统一为 sequence_id、class_label、family_label、dataset_role。实际文件路径相对项目根目录；默认不能指向外部。新增 backbone 配置通过 `external_embedding_roots` 显式允许 `data/` 下的输入软链接读取指定源目录，输出路径仍限制在项目内。

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

## CAZy 其他 base model

`configs/cazy_backbones.json` 配置 ESM-1b 650M（1280 维）、ESM2 150M（640 维）、ESM2 35M（480 维）的 L0/L1/L2 FT-CE，共九条路线。训练层级及分析参数与原 CAZy 配置一致，复用本项目 CAZy metadata、配色和 PCA100 设置。每条路线包含 train、multi、unseen、ood、shuffled、idr、non_target_train，支持全部六个实验。

输入位于 `data/cazy/embeddings/<route>/`，是指向下列目录内具体导出批次的目录软链接：

```text
/gpfs/research/rdf/zong/CAZy-Project/protein-embedding-resolution-dev/runs/embeddings/cazy
```

ESM-1b 使用 `priority_20261108_024610`，两种 ESM2 使用 `priority_20261108_152825`。链接同时提供 CSV 和源导出 manifest；不复制或修改源数据。软链接受 Git 的 data 忽略规则管理，迁移机器时需重新建立链接，并调整配置中的允许源目录，或将数据复制到相同的项目相对路径。

```bash
.venv/bin/python workflows/validate.py --config configs/cazy_backbones.json
bash workflows/overview.sh configs/cazy_backbones.json esm1b__l0-ft-ce pca
bash workflows/overview.sh configs/cazy_backbones.json esm2-150m__l1-ft-ce pca
bash workflows/overview.sh configs/cazy_backbones.json esm2-35m__l2-ft-ce pca
```

新配置只包含这九条已有数据的路线，不依赖原 `cazy.json` 中尚未导入的 embedding。结果仍位于 `outputs/cazy/`，按完整 route 名区分；BA summary 按三个 base model 分组比较 L0/L1/L2。Boundary 的 sample 在该配置九条路线之间共享。切换 CAZy 配置后需显式重跑 sample；如需同时保留各配置的共享采样与 summary，请使用不同的 `--version`（shell 第四个参数）。

### ESM2 150M / 35M 批处理

`workflows/backbone.slurm` 接受 `sample|route|summary` 和 `esm2-150m|esm2-35m` 两个参数；route 使用 Slurm array 0–2 对应 L0–L2。四个 workflow 为 binary、overview、boundary、multilabel，包含 t-SNE、UMAP、适用指标和绘图，最后汇总 Boundary / Multilabel。此脚本不渲染 paper 子图。

为使各模型的共享采样和 summary 独立，输出使用与模型同名的版本：`outputs/cazy/_versions/esm2-150m/`、`outputs/cazy/_versions/esm2-35m/`。目录内路线名保留完整的模型前缀，例如 `esm2-150m__l0-ft-ce`。日志及 Slurm 作业号记录在 `outputs/cazy/logs/<model>/submission.json`。提交时需依次设置 sample → route array → summary 的 `afterok` 依赖。

继续某个步骤时务必保留版本参数，例如：

```bash
bash workflows/overview.sh configs/cazy_backbones.json esm2-150m__l0-ft-ce visualization-tsne esm2-150m
bash workflows/binary.sh configs/cazy_backbones.json esm2-35m__l2-ft-ce visualization-umap esm2-35m
```

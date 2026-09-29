# Embedding analysis

一套核心代码，通过 `configs/cazy.json` / `configs/peptidase.json` 切换系统。第一阶段包括 train-fit PCA、训练空间展示、OOD silhouette、class-level BA、class 内 unseen family 质量，以及 family centroid 结构分析。

不包含 kNN OOD score、Leiden、HDBSCAN 或 bridge score。BA 只按 class 计算。

- [第一阶段范围与提交步骤](docs/SCOPE.md)
- [未纳入的功能和两套系统的差异](docs/DEFERRED.md)
- [计算定义及与旧版的差异](docs/METHODS.md)
- [验证记录](docs/VALIDATION.md)

## 运行

本机已建立本目录 `.venv`，不依赖两个旧项目的 Python 环境。直接从 checkout 运行，无需安装 package：

```bash
cd /path/to/embedding_analysis
.venv/bin/python run.py validate --config configs/cazy.json
.venv/bin/python run.py validate --config configs/peptidase.json
```

`validate` 检查所有配置文件路径、metadata 是否存在和 embedding 维度。`--deep` 进一步读取全量矩阵、验证 ID、有限数值和元数据对齐；大文件会耗时。

先准备某条路线的 PCA：

```bash
.venv/bin/python run.py prepare --config configs/cazy.json \
  --route esm2__l2-frozen-nca
```

运行某个核心实验，或全部实验：

```bash
.venv/bin/python run.py run --config configs/cazy.json \
  --route esm2__l2-frozen-nca --experiment multilabel

.venv/bin/python run.py run --config configs/peptidase.json \
  --route esm2__l2-ft-ce --experiment all
```

`--experiment` 可选：`overview`、`ood`、`multilabel`、`unseen`、`structure`、`all`。

省略 `--route` 会运行配置中的所有路线；可以重复指定 `--route`。实际数据量较大，完整 t-SNE 与精确 family 距离计算会耗时，本次没有重跑全量实验。

- `--no-plots`：仍计算并保存二维坐标，只跳过图片导出。
- `--force`：重新计算选定路线的 PCA 及选定实验。
- `all`：缺输入的实验会明确写入跳过报告；显式请求缺输入的单项实验则报错。
- peptidase 的 `esm2__l1-ft-ce__l2-frozen-nca` 只有 train，因此仅支持 overview 和 structure。

按当前配置与代码版本汇总已生成结果：

```bash
.venv/bin/python run.py summarize --config configs/cazy.json
```

只重新绘图，不读取 embedding、不重新计算指标或降维：

```bash
.venv/bin/python run.py plot --config configs/cazy.json \
  --experiment multilabel \
  --run-dir outputs/cazy/esm2__l2-frozen-nca/multilabel/<run_id>
```

科学参数取自原运行的 manifest，绘图样式取自当前 config。主要颜色、标签和重点组合由系统配置控制。

## 配置与数据

`defaults.json` 保存共享计算参数；系统配置覆盖 metadata 列名、class 配色、route 输入和格式。内部字段统一为 sequence_id、class_label、family_label、dataset_role。实际文件路径相对新项目根目录，不能指向外部。

已导入配置所需的 72 个文件，约 27.51 GiB 逻辑大小。macOS 下使用 APFS 写时复制，副本有独立 inode，不是软链接/硬链接。原两个目录、原始结果以及 normalized/ 未改动。只导入核心需要的输入；数据和环境不进入 Git。

需要重新导入时：

```bash
python scripts/import_data.py --source-root /path/to/OOD2
```

详细来源与复制验证方式在未跟踪的 `data/import_manifest.json`。默认验证大小及首尾各 1 MiB 摘要；可加 `--verify-full` 做逐字节校验。原始项目路径只用于这个一次性导入工具，运行期不访问它们。

NPY 的 ID 来源由 `ids_reference` 显式声明。它只能检查行数和 ID 完整性，不能仅凭文件推断行序正确。当前 peptidase 数据沿用原脚本的 level0 CSV 行序约定。

## 输出

```text
outputs/<system>/<route>/preprocess/<run_id>/
outputs/<system>/<route>/<experiment>/<run_id>/
outputs/<system>/_sampling/<run_id>/ood.json
outputs/<system>/_runs/<run_id>/report.json
outputs/<system>/_comparison/<run_id>/
```

每次运行保存完整配置、输入指纹、代码摘要和成功产物清单。指标 CSV 与二维 coordinates.csv 独立保存。主要指标汇总：

| 实验 | 主要表 |
| --- | --- |
| OOD | samples.csv、summary.csv |
| Class BA | scores.csv、summary.csv |
| Unseen | families.csv、global.csv、reference_families.json |
| Structure | centroids.csv、metrics.csv |

OOD 抽样按每个系统各路线 ID 交集固定，因 CAZy l2-ft 原有预抽样，实际共同样本可能小于 3145；manifest 会记录实际数。新抽样不承诺复现旧图的随机样本。

## 测试

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/smoke_real_data.py
```

第一条运行输入完整性、旧指标回归、两个系统的工作流/缓存/跳过测试；其中工作流测试用确定性二维坐标替代耗时降维。第二条读取新目录的数据，建立独立的小样本项目，实际运行 PCA、openTSNE、UMAP、全部核心指标及 PNG 导出，输出在 `outputs/smoke/`，不改动主数据。

## 移动或在其他机器安装

代码和 configs 可直接移植。数据需一起携带，或通过导入工具准备。虚拟环境依赖本机系统 Python，换机器应重新创建：

```bash
python3.10 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

也可 `pip install -e .`，之后使用 `embedding-analysis` 命令。核心依赖不包含 FAISS、scanpy、Leiden、HDBSCAN、Biopython 或 Plotly。

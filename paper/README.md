# 论文子图

## 给协作者的独立包

持续协作推荐使用 **Git 分支 + PR**：代码从同一个远端仓库克隆，数据运行
`.venv/bin/python paper/export.py --data-only` 单独生成 `outputs/handoff/paper-inputs.zip`。
协作者把数据包解压到 clone 的根目录，它只写入已忽略的 `outputs/`，不会覆盖代码。
完整流程见 [HANDOFF.md](HANDOFF.md#推荐git-分支--pr-持续协作)。

运行 `.venv/bin/python paper/export.py` 生成 `outputs/handoff/paper-handoff.zip`。
包含全部论文图配置、代码、所需的源坐标/指标及 manifest，以及当前 PNG 对照图。
不包含原始 embedding、虚拟环境或 Git 历史。重复引用的输入只打包一次。
协作者解压后先看 `START_HERE.md`；详细安装和布局修改说明见 [HANDOFF.md](HANDOFF.md)。
只渲染论文图时安装 `paper/requirements.txt` 即可，无需 openTSNE 或 umap-learn。

从已完成的实验坐标和逐样本指标选择性重绘论文子图，不重新拟合 PCA 或 t-SNE/UMAP。
入口独立于 `workflows/`，现有实验绘图不受影响。

## Figure 2

| 子图 | 图类型 | 系统 / 实验 / route |
| --- | --- | --- |
| c | target / non-target train | cazy / binary / esm2__l0-ft-ce |
| d | class 着色和 class 标注 | cazy / overview / esm2__l1-ft-ce |
| e | class 着色和 family 标注 | cazy / overview / esm2__l2-ft-ce |
| f | 三任务 Macro-F1 compact 对比 | cazy / performance / summary |

c/d/e 读取现有 t-SNE 坐标。e 沿用每个 class 内按数量排名的前 15% family 种类标注规则。

在项目根目录运行：

```bash
# 只检查源产物身份、完整性、坐标字段和 ID
.venv/bin/python paper/render.py check paper/figures/figure2.json

# 导出 c、d、e、f
.venv/bin/python paper/render.py render paper/figures/figure2.json

# 只重画 e；也可以 --panel c e
.venv/bin/python paper/render.py render paper/figures/figure2.json --panel e
```

输出在 `outputs/paper/figure2/`：每张子图独立的 PNG、PDF、SVG 和 `.manifest.json`，预览集中在 `outputs/paper/preview/`，打开其中的 `index.html` 可浏览所有 Figure。
可运行 `.venv/bin/python paper/render.py preview`，仅更新预览页面，无需重新绘图。每次 render 也会自动刷新预览。
手动添加的 panel（如 `figure2/2ab.pdf`、`figure3/3a.pdf`，也支持 `a.png` / `ab.svg`）会自动放在预览最前面，并保留原文件链接。PDF 使用 Poppler 的 `pdftoppm` 生成缩略图，缓存在 `preview/assets/`；未安装时使用浏览器内嵌 PDF。

主图右下角内部标注 Level 0、Level 1、Level 2，不显示顶部标题或 c/d/e 编号。图例单独保存为 `c_legend.*`、`d_legend.*`、`e_legend.*`，同样导出三种格式。c 的图例使用 Non-CAZyme 和 CAZyme。
支持整组导出，不自动拼成整张 Figure 2。单图重画保留其他子图及其来源记录。
缺上游或校验不通过会报错，不自动运行实验。`check` 不执行绘图和字体布局检查。

## 调整内容与样式

修改 `figures/figure2.json`：

- `source` 指定 system、workflow、route、stage；可加 `version` 读取对应 `_versions/` 结果。
- `kind` 支持 `binary`、`overview_classes`、`overview_families`、`boundary_balanced`、`multilabel_combos`、`boundary_silhouette`、`multilabel_ba`、`centroid_purity`、`performance`。
- `style` 是全图默认样式；子图中的 `style` 只覆盖本子图。
- `size_inches` 控制精确画布尺寸，当前为 8 × 8.5 英寸、300 dpi。缩小到论文实际尺寸时应同时调整字体和点大小。
- `axes_rect` 是绘图区在画布中的相对位置 `[left, bottom, width, height]`，需为上方图例和编号留白。
- `title` 设置上方居中的标题，`style.title_fontsize` 设置标题字号。c/d/e 仅作为文件名和命令选择 ID。
- 不设置 `title` 时不显示标题。二分类的 `style.legend_labels` 可按 dataset_role 覆盖图例名称。
- `corner_label` 设置绘图区右下角内部文字，`style.corner_fontsize` 控制字号；不增加画布边距。
- `style.annotation_offsets` 可按标注名称设置 `[dx, dy]`（单位 pt），只移动文字。e 的 CBM5/PL33 使用小幅偏移避免重叠。
- family 子图的 `selection.top_family_fraction` 控制自动标注比例；`selection.families` 可指定准确的 family 列表，仅改变标注，所有点仍保留。
- 配色、class 顺序、二分类显示名称来自源坐标 manifest 中保存的实验配置。

PDF/SVG 中散点默认栅格化以控制体积，文字、箭头和图例保持矢量；`rasterized: false` 可导出全矢量散点。SVG 保留文字对象。主图不使用 tight 裁边，各子图画布尺寸固定；独立图例按实际内容裁边。
源实验图、原始坐标和指标均不会被改写。

## 来源与定稿

每张子图的 manifest 保存有效配置、源 checkpoint、坐标 SHA256、源 manifest 摘要、绘图代码摘要、样本数、实际标注列表与输出文件摘要。
默认每次读取指定 checkpoint 的当前结果。定稿时可把 manifest 中的 `source.coordinates_sha256` 复制到配置的相应 `source.coordinates_sha256`，锁定坐标内容；不匹配则拒绝出图。
输出目录已被 Git 忽略，代码和图配置可提交。

验证：`PYTHONPATH=src .venv/bin/python -m unittest discover -s paper/tests`。

## Figure 3

配置为 `figures/figure3.json`，输出独立保存到 `outputs/paper/figure3/`。

| 子图 | 内容 | 来源 |
| --- | --- | --- |
| b/c/d | Boundary UMAP balanced | CAZy L0/L1/L2 FT-CE |
| e/f/g | UMAP 同时高亮 CBM\|GH、CBM\|PL，含上方和右侧 KDE | CAZy L0/L1/L2 FT-CE |
| h | 逐样本 silhouette 箱线图 | Boundary summary，三个 FT-CE route |
| i | BA violin，前六个指定组合 | Multilabel summary，三个 FT-CE route |

i 的组合顺序固定为 `CBM|GH`、`CBM|PL`、`AA|CBM`、`CBM|CE`、`GH|GT`、`CBM|GT`。
这是原图前六项的明确选择，不随样本量重新排名。指标图用原有逐样本分数绘制，不用汇总均值替代分布。
b–g 右下角标注对应 Level；h 横轴和 i 独立图例统一使用 Level 0/1/2。i 不包含 ESM2，图例色块使用深色边框。所有图例单独导出。

```bash
.venv/bin/python paper/render.py check paper/figures/figure3.json
.venv/bin/python paper/render.py render paper/figures/figure3.json
.venv/bin/python paper/render.py render paper/figures/figure3.json --panel h i
```

汇总数据来源使用 `route: "summary"`、`stage: "tables"`，并通过 `selection.routes` 选择比较路线。
BA 使用 `selection.combinations` 选择组合；空组会报错，不会静默省略。
指标来源摘要记录在 `samples_sha256`，可写入 source 同名配置以锁定数据。
空间图保留完整坐标背景，KDE 和轮廓仅在绘图时计算，未重新计算实验指标。

## Figure 4

配置为 `figures/figure4.json`，输出到 `outputs/paper/figure4/`，使用 Peptidase 数据。

| 子图 | 内容 | 来源 |
| --- | --- | --- |
| b | target / non-target train t-SNE | L0 FT-CE binary |
| c | class 着色及标注 t-SNE | L1 FT-CE overview |
| d | class 着色及 family 标注 t-SNE | L2 FT-CE overview |
| e | 三任务 Macro-F1 compact 对比 | performance summary |
| i | UMAP balanced | L0 FT-CE boundary |
| j | UMAP 同时高亮 C\|N、C\|M，保留双侧 KDE | L1 FT-CE multilabel |
| k | silhouette 箱线图 | 三个 FT-CE level |
| l | BA violin | 三个 FT-CE level |

b/c/d 的图类型和 t-SNE 口径与 Figure 2 c/d/e 对应。
l 沿用 Peptidase 配置中的六个组合：`C|M`、`C|N`、`C|S`、`N|S`、`M|S`、`S|T`。
所有图例独立保存；k 横轴和 l 图例使用 Level 0/1/2，l 图例色块带深色边框。

```bash
.venv/bin/python paper/render.py render paper/figures/figure4.json
.venv/bin/python paper/render.py render paper/figures/figure4.json --panel k l
```

## Figure 5

配置为 `figures/figure5.json`，输出到 `outputs/paper/figure5/`。
b、c、h、i 复用 overview 的 t-SNE 坐标，按 class 着色并标注每个 class 中数量排名前 15% 的 family 种类。
d、j 分别读取 CAZy、Peptidase 的 centroid summary，绘制 compact kNN class purity，比较 ESM2、Direct L2 NCA、L1-conditioned L2 NCA。主图无标题和 panel 字母，三列横排 legend 单独保存；均导出 PNG/PDF/SVG。纵轴下限根据数据留白（最高为 0.55），上限为 1.02。

| 子图 | 系统 | route | 右下角文字 |
| --- | --- | --- | --- |
| b | CAZy | esm2__l2-frozen-nca | Direct L2 NCA |
| c | CAZy | esm2__l1-ft-ce__l2-frozen-nca | L1-conditioned L2 NCA |
| h | Peptidase | esm2__l2-frozen-nca | Direct L2 NCA |
| i | Peptidase | esm2__l1-ft-ce__l2-frozen-nca | L1-conditioned L2 NCA |

```bash
.venv/bin/python paper/render.py render paper/figures/figure5.json
.venv/bin/python paper/render.py render paper/figures/figure5.json --panel b c
.venv/bin/python paper/render.py render paper/figures/figure5.json --panel d j
```

d/j 的输入为 `outputs/<system>/centroid/artifacts/summary/tables`，需包含上述三个 route 的指标；paper 校验文件摘要、route 和 k 的完整性后重绘，不运行 PCA 或重新计算指标。`paper/export.py` 会自动将这两个 summary 输入加入交接包。

## Performance 论文面板

| 面板 | 系统 | performance 图名 |
| --- | --- | --- |
| Figure 2f | CAZy | `05_macro_f1_comparison` |
| Figure 4e | Peptidase | `05_macro_f1_comparison` |
| Figure 5e | CAZy | `04_level_2_nca_A_overall` |
| Figure 5k | Peptidase | `04_level_2_nca_A_overall` |

这些面板读取 `outputs/<system>/performance/artifacts/summary/tables` 的 `metrics.csv`，校验来源摘要后，复用 performance 绘图函数重绘，不复制 PNG、不重新计算指标。输入只需先运行 `performance` 的 `tables` 步骤，交接包自动包含两个系统的表格及 manifest。

保留 compact 画布（3.9 × 3.125 英寸）、原有柱宽与配色，标题为 **Test set performance**；主图不标 panel 字母、不包含 legend，横排 legend 独立保存。paper 输出 PNG/PDF/SVG，performance workflow 仍仅保存带 legend 的 PNG。05 比较三个任务各自的 ESM2 基线与对应 Level；04 比较 ESM2、Direct L2 NCA、L1-conditioned L2 NCA 的 Accuracy / Macro-F1。

```bash
.venv/bin/python paper/render.py render paper/figures/figure2.json --panel f
.venv/bin/python paper/render.py render paper/figures/figure4.json --panel e
.venv/bin/python paper/render.py render paper/figures/figure5.json --panel e k
```

`kind: performance` 使用 `selection.plot` 选择上述两种 compact 图；图形轴布局由共用的 performance builder 保持，独立 legend 的字号和列数由 paper 的 style 控制。

## 按 base model 汇总四页 PDF

`report.py` 在 workflow 完成后读取现有坐标和逐样本指标，按系统和模型导出一份四页拼图 PDF。无需重新运行 PCA、t-SNE、UMAP 或指标计算，也不依赖或改写跨路线 summary。安装主项目或 paper 的 requirements（含 `pypdf`）即可使用。

```bash
# 已完成的 ESM-1b CAZy：一条命令生成报告
.venv/bin/python paper/report.py render --system cazy --model esm1b

# 其他 base model；自动查找唯一完整的默认/命名版本
.venv/bin/python paper/report.py render --system cazy --model esm2-150m
.venv/bin/python paper/report.py render --system cazy --model esm2-35m

# Peptidase 使用同一入口，需先完成对应模型的 workflow
.venv/bin/python paper/report.py render --system peptidase --model esm1b
```

页面安排：

| 页 | 内容 | 来源选择 |
| --- | --- | --- |
| 1 | L0 Binary、L1 Class、L2 Class/Family t-SNE 横排 | Figure 2 c/d/e；Peptidase 使用 Figure 4 b/c/d |
| 2 | Boundary L0/L1/L2 UMAP 横排 | Figure 3 b/c/d 的 balanced 视图 |
| 3 | Multilabel L0/L1/L2 UMAP 横排 | CAZy 高亮 `CBM\|GH`、`CBM\|PL`；Peptidase 高亮 `C\|N`、`C\|M` |
| 4 | 三级 Silhouette 箱线图、BA violin 并排 | CAZy 使用 Figure 3 h/i 的六组 BA 组合；Peptidase 使用 Figure 4 k/l 的六组 |

图例与对应子图同页，页眉包含 system、base model 和输出版本。PDF 拼版保留矢量文字与图例；密集散点沿用论文绘图的栅格化设置。默认 200 dpi，可传 `--dpi 300`。每页另存 PNG 预览，manifest 记录源文件摘要、选图、绘图参数及页面对应关系。

输出路径包含系统、模型和版本，例如：

```text
outputs/paper/reports/cazy/esm1b/default/cazy_esm1b_default.pdf
outputs/paper/reports/cazy/esm2-150m/esm2-150m/cazy_esm2-150m_esm2-150m.pdf
outputs/paper/reports/peptidase/esm1b/default/peptidase_esm1b_default.pdf
```

`--version auto` 为默认行为：仅在一个结果版本具备全部所选来源时自动选定。多个版本均完整时要求显式指定，避免误选；不跨版本拼凑。`--version default` 强制读取未命名版本，`--version NAME` 读取指定版本。

```bash
# 只检查来源、完整性、ID、逐样本指标与所需组合
.venv/bin/python paper/report.py check --system cazy --model esm1b

# 只提取训练空间，输出一页三联图
.venv/bin/python paper/report.py render --system cazy --model esm1b \
  --panels binary_l0 classes_l1 families_l2

# 只提取指标对比，输出一页双联图
.venv/bin/python paper/report.py render --system cazy --model esm1b \
  --panels silhouette ba
```

可选 panel 名为 `binary_l0`、`classes_l1`、`families_l2`、`boundary_l0/l1/l2`、`multilabel_l0/l1/l2`、`silhouette`、`ba`（斜杠表示三个独立名称）。选中子图仍按上述四个主题分组，组内保留传入顺序；空组不输出。子集文件名附选择摘要，不覆盖完整报告。输入和代码未变时复用 PDF，可用 `--force` 强制重画。

缺少任一所选来源时，预检列出缺失路径，不生成残缺报告，也不自动启动重计算。Peptidase ESM-1b 尚无本仓库 workflow 产物时会明确报缺失；不能用 CAZy 或默认 ESM2 结果代替。

可接在现有 workflow 命令后使用 `&& .venv/bin/python paper/report.py render ...`。Slurm 环境可用下面的包装脚本，在三级任务全部成功后自动汇总 PDF：

```bash
mkdir -p outputs/paper/reports/logs
sbatch --dependency=afterok:三级任务数组ID --kill-on-invalid-dep=yes \
  --job-name=cazy-esm2-150m-pdf paper/report.slurm \
  --system cazy --model esm2-150m --version esm2-150m
```

无需等待 summary 任务，只需相关路线的坐标和 metrics 完成。报告所需最小输入是 L0 binary t-SNE、L1/L2 overview t-SNE，以及三级 boundary/multilabel UMAP 和 metrics。

### Figure 5：Direct / L1-conditioned NCA 一页双联图

使用 `--preset nca` 从两条 NCA overview t-SNE 路线取图，沿用 Figure 5 b/c（Peptidase 为 h/i）的 class 配色与每类前 15% 高频 family 标注。左侧为 `<model>__l2-frozen-nca`，右侧为 `<model>__l1-ft-ce__l2-frozen-nca`，一组一页，不运行其他实验。

```bash
.venv/bin/python paper/report.py render --system cazy --model esm1b \
  --preset nca --version nca-20261109 --dpi 300
```

另两组将 `--model` 替换为 `esm2-150m` 或 `esm2-35m`。文件名附 `_nca`，例如：

```text
outputs/paper/reports/cazy/esm1b/nca-20261109/cazy_esm1b_nca-20261109_nca.pdf
```

新训练批次使用 `configs/cazy_nca_backbones.json`：六条路线均只配置 `projected/cazy_train.embeddings.csv`，256 维，输入目录软链接位于 `data/cazy/embeddings/<route>/`。源 run 与 feature source 写入配置，metadata 沿用本仓库 CAZy train。先全量校验，再在 train 上 L2 normalize + PCA100、t-SNE，未使用 val/test 拟合。

`workflows/nca_backbones.slurm route` 使用 array 0–5，依次对应 ESM-1b direct/conditioned、ESM2 150M direct/conditioned、ESM2 35M direct/conditioned。`report` 模式生成三份单页 PDF；提交时设置 array 成功后的 `afterok` 依赖。运行版本固定为 `nca-20261109`，源训练批次为 `20261109_093908`。重画 PDF 不必重跑 t-SNE。

## NAE panels

NAE 已接入统一 renderer，使用本地 `outputs/<system>/nae/artifacts/summary/tables/` 的物理副本。代码位于 `src/embedding_analysis/experiments/nae/`；输入导入步骤见 [workflow 文档](../workflows/README.md#nae-paper-panels)。

| Figure | 系统 | Survival | Mean matrix |
| --- | --- | --- | --- |
| 2 | CAZy，ESM2/L0/L1/L2 | g、h | i_standard、i_transition |
| 4 | Peptidase，ESM2/L0/L1/L2 | f、g | h_standard、h_transition |
| 5 | CAZy，ESM2/Direct NCA/L1-conditioned NCA | f | g_standard、g_transition |
| 5 | Peptidase，同上 | l | m_standard、m_transition |

每个组件输出 PNG、SVG 和来源 manifest 到 `outputs/paper/figureN/`，survival 另有 `<panel>_legend`，矩阵组件分别保留以便拼版。原始命名及本地文件映射在 `paper/nae_panel_mapping.json`。

```bash
# 只选 NAE，无需其他 embedding/performance 输入
.venv/bin/python workflows/nae.py render --system cazy
.venv/bin/python workflows/nae.py render --system peptidase
# 也可按单个组件检查或重画
.venv/bin/python paper/render.py check paper/figures/figure2.json --panel g h i_standard i_transition
.venv/bin/python paper/render.py render paper/figures/figure5.json --panel f g_standard g_transition
# 将忽略的输入与参考 PNG 打包，解压到同版本 Git clone 即可重画
.venv/bin/python paper/export.py --nae-only --data-only
# 默认输出 outputs/handoff/nae-paper-inputs.zip
```

保留源代码的曲线方向 `P(NAE ≥ x)`、精确阈值和 x=1 满分比例；显示窗口为 [-1,1]，输入中更低的分数不被截断。均值为未加权原始均值，缺失值不填零。Survival 按 relation 求跨空间共同有效 ID；mean matrix 按相应完整 standard/transition 关系组及空间取交集，即便只显示一列也不另算 cohort。两种图、两组空间的 cohort 不强行合并。Peptidase 使用 Type 标签，沿用原始配色、矩阵尺寸和 winner 标记，不添加总标题或样本量脚注。

NAE survival 的比例可通过 panel 的 `style.survival_panel_width`（每个 relation 的画布宽度）
和 `style.survival_height` 调整，单位英寸，当前默认 4.6 × 4.2。

## 整页拼版（Figure 2–5）

准备好全部子图，以及各 Figure 目录中的 `2ab.pdf`、`3a.pdf`、`4a.pdf`、
`5a.pdf` 后运行 `.venv/bin/python paper/assemble.py`。

需要安装 `paper/requirements.txt`，以及系统 Poppler（`pdftoppm`）与 Cairo；
macOS 可使用 `brew install poppler cairo`。拼版不运行实验或重绘数据。
优先嵌入子图 PDF；仅有 SVG 的 NAE 图通过 CairoSVG 转为矢量 PDF。
源图中已有的栅格化散点保持原样，文字及其他矢量元素保留。

布局位于 `paper/layouts/figures2-5.json`：
`page_size` 和 `box: [x, y, width, height]` 单位为 PDF point，原点在页面左上角；
`labels` 单独控制 panel 字母。图片按比例适配指定区域，自动裁掉外围空白。
图例作为独立元素摆放。可用 `--layout` 指定另一份布局、`--output` 指定输出目录。

默认输出 `outputs/paper/assembled/`，包含四个单页 PDF、合并的 `figures2-5.pdf`、
四张 PNG 预览与记录输入校验值、裁切和布局的 manifest。
预览总入口自动增加默认目录下的整页文件链接。

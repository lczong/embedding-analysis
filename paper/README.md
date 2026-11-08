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

三张图都读取现有 t-SNE 坐标。e 沿用每个 class 内按数量排名的前 15% family 种类标注规则。

在项目根目录运行：

```bash
# 只检查源产物身份、完整性、坐标字段和 ID
.venv/bin/python paper/render.py check paper/figures/figure2.json

# 导出 c、d、e
.venv/bin/python paper/render.py render paper/figures/figure2.json

# 只重画 e；也可以 --panel c e
.venv/bin/python paper/render.py render paper/figures/figure2.json --panel e
```

输出在 `outputs/paper/figure2/`：每张子图独立的 PNG、PDF、SVG 和 `.manifest.json`，以及 `index.html` 预览。
主图右下角内部标注 Level 0、Level 1、Level 2，不显示顶部标题或 c/d/e 编号。图例单独保存为 `c_legend.*`、`d_legend.*`、`e_legend.*`，同样导出三种格式。c 的图例使用 Non-CAZyme 和 CAZyme。
支持整组导出，不自动拼成整张 Figure 2。单图重画保留其他子图及其来源记录。
缺上游或校验不通过会报错，不自动运行实验。`check` 不执行绘图和字体布局检查。

## 调整内容与样式

修改 `figures/figure2.json`：

- `source` 指定 system、workflow、route、stage；可加 `version` 读取对应 `_versions/` 结果。
- `kind` 支持 `binary`、`overview_classes`、`overview_families`、`boundary_balanced`、`multilabel_combos`、`boundary_silhouette`、`multilabel_ba`。
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
| h | UMAP balanced | L0 FT-CE boundary |
| i | UMAP 同时高亮 C\|N、C\|M，保留双侧 KDE | L1 FT-CE multilabel |
| j | silhouette 箱线图 | 三个 FT-CE level |
| k | BA violin | 三个 FT-CE level |

b/c/d 的图类型和 t-SNE 口径与 Figure 2 c/d/e 对应。
k 沿用 Peptidase 配置中的六个组合：`C|M`、`C|N`、`C|S`、`N|S`、`M|S`、`S|T`。
所有图例独立保存；j 横轴和 k 图例使用 Level 0/1/2，k 图例色块带深色边框。

```bash
.venv/bin/python paper/render.py render paper/figures/figure4.json
.venv/bin/python paper/render.py render paper/figures/figure4.json --panel j k
```

## Figure 5

配置为 `figures/figure5.json`，输出到 `outputs/paper/figure5/`。
四张图均复用 overview 的 t-SNE 坐标，按 class 着色并标注每个 class 中数量排名前 15% 的 family 种类。

| 子图 | 系统 | route | 右下角文字 |
| --- | --- | --- | --- |
| b | CAZy | esm2__l2-frozen-nca | Direct L2 NCA |
| c | CAZy | esm2__l1-ft-ce__l2-frozen-nca | L1-conditioned L2 NCA |
| h | Peptidase | esm2__l2-frozen-nca | Direct L2 NCA |
| i | Peptidase | esm2__l1-ft-ce__l2-frozen-nca | L1-conditioned L2 NCA |

```bash
.venv/bin/python paper/render.py render paper/figures/figure5.json
.venv/bin/python paper/render.py render paper/figures/figure5.json --panel b c
```

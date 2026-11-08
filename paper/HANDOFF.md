# 给论文图协作者

## 推荐：Git 分支 + PR 持续协作

代码和配置从同一个 Git 仓库获取，输入数据单独传输。
作者运行 `.venv/bin/python paper/export.py --data-only`，发送 `outputs/handoff/paper-inputs.zip`。
该包只包含 `outputs/` 下的输入、参考 PNG 和校验记录，解压不会覆盖 Git 跟踪的代码或配置。

协作者首次准备（把仓库地址替换成实际地址）：

```bash
git clone <仓库地址> embedding_analysis
cd embedding_analysis
python3 -m zipfile -e /path/to/paper-inputs.zip .
python3 -m venv .venv
.venv/bin/python -m pip install -r paper/requirements.txt
git switch -c paper/figure3-layout
.venv/bin/python paper/render.py check paper/figures/figure3.json
.venv/bin/python paper/render.py render paper/figures/figure3.json --panel i
```

修改后检查、提交并开 PR：

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s paper/tests
git diff --check
git diff
# 明确选择本次修改的文件，以下为配置修改的例子
git add paper/figures/figure3.json
git commit -m "Adjust Figure 3 layout"
git push -u origin paper/figure3-layout
```

在 GitHub/GitLab 上将这个分支提交为目标 `main` 的 PR/MR，附上改动说明和前后预览。
如果没有仓库写权限，使用 fork，将分支推送到自己的 fork 后向原仓库提交 PR。
作者审查、复现受影响子图并合并；协作者再从最新 main 创建下一个分支。
每次尽量围绕一个 Figure 开分支；公共绘图函数的改动需要检查其他受影响 Figure。
生成图、输入和虚拟环境不加入 Git，也不要使用 `git add -f`。

数据未变化时无需重复发送。如果增加数据来源或重新计算坐标/指标，作者重新导出数据包，并说明对应的代码提交号。
数据包中的 `outputs/handoff/INPUTS_MANIFEST.json` 记录基准提交和文件校验和。
`outputs/paper-reference/` 是打包时的对照图，不是最新渲染目录。

## 备用：独立压缩包

这个包包含 Figure 2–5 的绘图代码、配置、实际使用的坐标和逐样本指标。
无需原始 embedding、PCA 模型、UMAP/t-SNE 重算或原作者电脑上的目录。
`reference/` 保存打包时的主图和独立图例 PNG，供对照。

## 安装和运行

推荐 Python 3.11 或 3.12。在解压得到的 `paper-handoff/` 目录运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r paper/requirements.txt
.venv/bin/python paper/render.py check paper/figures/figure2.json
.venv/bin/python paper/render.py render paper/figures/figure2.json
# 只重画一张；配置文件换成 figure3/4/5.json 即可运行其他 Figure
.venv/bin/python paper/render.py render paper/figures/figure3.json --panel i
```

Windows 使用 `py -3.11 -m venv .venv` 创建环境，将 `.venv/bin/python` 换成 `.venv\Scripts\python.exe`。
输出仍在 `outputs/paper/figureN/`，打开 `index.html` 预览并下载 PNG/PDF/SVG。
先运行 `check` 验证输入，再渲染。首次安装需要网络下载 Python 依赖。

默认字体为 Arial。机器上没有 Arial 时，请安装该字体，或把配置中的 `style.font` 改成双方约定的字体。
缺字体时 Matplotlib 可能替换字体，文字宽度及布局会改变。

## 调布局改哪些文件

优先修改 `paper/figures/figureN.json`：

| 参数 | 用途 |
| --- | --- |
| style.size_inches | 最终画布宽、高（英寸） |
| style.axes_rect | 普通单绘图区的 left、bottom、width、height，均为画布比例 |
| style.legend_fontsize | 独立图例字号 |
| style.class_fontsize / family_fontsize | overview 类别和 family 文字字号 |
| style.corner_fontsize | 右下角文字字号 |
| style.point_size / point_alpha | binary/overview 的散点大小及透明度 |
| 子图 style.annotation_offsets | binary/overview 中按名称调整标注位置，单位 pt |
| 子图 corner_label | 右下角文字内容 |
| style.formats | 默认 png、pdf、svg；调试阶段可只留 png 加快导出 |

顶层 style 是默认值，每个 panel 的 style 可以单独覆盖。
部分实验复用原绘图函数，尚未把所有绘图参数提升到 JSON；不要假设上述参数控制每种图。

需要改具体画法时：

- `src/embedding_analysis/publication/panels.py`：binary/overview 的散点、family/class 文字。
- `src/embedding_analysis/publication/figures.py`：Boundary、BA、silhouette 和多标签绘图的组合逻辑。
- `src/embedding_analysis/publication/render.py`：标题、右下角文字、独立图例、导出和 HTML 预览。
- `src/embedding_analysis/experiments/multilabel/spatial.py`：多标签图主散点及双侧 KDE 的 GridSpec 布局、标签位置。此布局不使用 JSON 的 axes_rect。
- `src/embedding_analysis/experiments/boundary/plotting.py`：Boundary 背景、轮廓和 silhouette 箱线图。
- `src/embedding_analysis/experiments/multilabel/plotting.py`：BA violin 的线宽、坐标轴及样本数标注。
- `src/embedding_analysis/legend.py`：独立图例列数和换行。

## 协作约定

数据和源 manifest 请保留原样：坐标及指标有 SHA256 校验，改动后会被拒绝。
无需修改 source 里的系统或路线，也无需访问 manifest 里记录的历史原始文件路径。
保持 `paper/`、`src/`、`outputs/` 的相对结构；整个包可以移动到任何目录。

回传修改后的 `paper/figures/`、修改过的 `.py` 文件和几张最终预览即可，不用回传约 130 MiB 的输入数据。
建议列一份修改文件清单；不要整体覆盖作者仓库。SVG 文字可编辑，但默认散点是嵌入的栅格图。
在图形软件中直接编辑 SVG 的修改不会回写到 Python/JSON；需要可复现时应回传代码改动。

包根目录的 `HANDOFF_MANIFEST.json` 记录全部随包文件的 SHA256、源代码提交号和打包时的工作区状态。
完整参数和 Figure 面板映射见 `paper/README.md`。

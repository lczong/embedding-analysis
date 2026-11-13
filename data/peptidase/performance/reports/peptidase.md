# Peptidase (MEROPS protein) test set performance

- 1-NN：train 为 reference，test 为 query；原始 embedding，不额外归一化；精确 Euclidean 距离，相同距离按 reference ID 字典序裁决。
- ESM2 为原始模型；L0/L1/L2-FT 为直接从 ESM2 微调的 CE 路线。两个 L2-NCA 为既有 frozen MLP + SGD 路线。
- L0/L1 分类头复用历史逐样本预测；L2-FT 分类头以保存的 CLS embedding 输入原模型分类头，FP32、关闭 dropout（未重新运行整个 backbone，可能与端到端 BF16 推理存在微小数值差异）。
- 分类指标：accuracy、macro precision/recall/F1、weighted F1；每类 accuracy 在单标签任务中等于该类 recall。所有未定义 precision/recall/F1 记为 0。
- 二分类 AUROC/AUPRC 以酶为 positive；AUPRC 使用 average precision (AP)。1-NN 连续分数为 d_negative/(d_positive+d_negative)，d 为到各类最近训练样本的 Euclidean 距离，两者都为 0 时取 0.5；这是距离分数，不是校准概率。分类头使用保存的 positive probability。
- Family 仅在 train 已知的 test families 上报告；未知 family 的样本保留在 CSV，标为 unknown，不纳入主指标。
- Family 分箱只依赖 train family 数量：head >100，body 11–100，tail 1–10。Macro 按有 test 支持的 family 平均。分箱 precision/F1 由整个 known test 的逐类混淆统计计算后在箱内平均，保留跨箱 false positives；分箱 accuracy 为该箱样本正确率。
- 数据及模型来源：[provenance](artifacts/peptidase/provenance.json)。

## L0 binary classification

CSV：[peptidase_binary_predictions.csv](peptidase_binary_predictions.csv)；总样本 30,630，纳入指标 30,630。

| 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 | AUROC | AUPRC (AP) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| esm2_1nn | 96.39% | 96.55% | 95.62% | 96.05% | 96.37% | 99.53% | 99.71% |
| l0_ft_1nn | 99.10% | 99.02% | 99.02% | 99.02% | 99.10% | 99.93% | 99.92% |
| l0_ft_head | 99.17% | 99.06% | 99.14% | 99.10% | 99.17% | 99.95% | 99.97% |

### 各类指标

| Class | Support | 方法 | Precision | Recall / class accuracy | F1 |
| --- | --- | --- | --- | --- | --- |
| non-peptidase | 11081 | esm2_1nn | 97.07% | 92.82% | 94.90% |
| non-peptidase | 11081 | l0_ft_1nn | 98.76% | 98.74% | 98.75% |
| non-peptidase | 11081 | l0_ft_head | 98.66% | 99.04% | 98.85% |
| peptidase | 19549 | esm2_1nn | 96.03% | 98.41% | 97.21% |
| peptidase | 19549 | l0_ft_1nn | 99.28% | 99.30% | 99.29% |
| peptidase | 19549 | l0_ft_head | 99.46% | 99.24% | 99.35% |

## L1 7-class classification

CSV：[peptidase_l1_predictions.csv](peptidase_l1_predictions.csv)；总样本 19,549，纳入指标 19,549。

| 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 |
| --- | --- | --- | --- | --- | --- |
| esm2_1nn | 96.03% | 95.15% | 95.05% | 95.10% | 96.02% |
| l1_ft_1nn | 99.15% | 98.04% | 98.44% | 98.24% | 99.15% |
| l1_ft_head | 99.28% | 99.24% | 98.67% | 98.95% | 99.28% |

### 各类指标

| Class | Support | 方法 | Precision | Recall / class accuracy | F1 |
| --- | --- | --- | --- | --- | --- |
| S | 6839 | esm2_1nn | 96.25% | 96.90% | 96.58% |
| S | 6839 | l1_ft_1nn | 99.47% | 99.43% | 99.45% |
| S | 6839 | l1_ft_head | 99.39% | 99.50% | 99.44% |
| M | 6496 | esm2_1nn | 96.35% | 95.83% | 96.09% |
| M | 6496 | l1_ft_1nn | 99.35% | 99.00% | 99.17% |
| M | 6496 | l1_ft_head | 99.38% | 99.25% | 99.31% |
| C | 3755 | esm2_1nn | 94.99% | 94.89% | 94.94% |
| C | 3755 | l1_ft_1nn | 98.80% | 99.04% | 98.92% |
| C | 3755 | l1_ft_head | 98.86% | 99.09% | 98.98% |
| A | 1531 | esm2_1nn | 96.86% | 96.60% | 96.73% |
| A | 1531 | l1_ft_1nn | 98.51% | 99.15% | 98.83% |
| A | 1531 | l1_ft_head | 99.35% | 99.22% | 99.28% |
| T | 452 | esm2_1nn | 95.49% | 93.58% | 94.53% |
| T | 452 | l1_ft_1nn | 97.39% | 98.89% | 98.13% |
| T | 452 | l1_ft_head | 99.11% | 98.67% | 98.89% |
| G | 388 | esm2_1nn | 95.18% | 96.65% | 95.91% |
| G | 388 | l1_ft_1nn | 99.48% | 99.23% | 99.35% |
| G | 388 | l1_ft_head | 99.74% | 99.48% | 99.61% |
| N | 88 | esm2_1nn | 90.91% | 90.91% | 90.91% |
| N | 88 | l1_ft_1nn | 93.26% | 94.32% | 93.79% |
| N | 88 | l1_ft_head | 98.82% | 95.45% | 97.11% |

## L2 family classification

CSV：[peptidase_family_predictions.csv](peptidase_family_predictions.csv)；总样本 19,549，纳入指标 19,549。

排除未知 family：无（0 条）；macro 范围为 174 个有 test 支持的已知 families。

| 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 |
| --- | --- | --- | --- | --- | --- |
| esm2_1nn | 93.07% | 91.09% | 88.11% | 89.04% | 93.12% |
| l2_ft_1nn | 98.59% | 97.52% | 97.01% | 97.11% | 98.61% |
| l2_ft_head | 98.73% | 97.85% | 97.05% | 97.19% | 98.74% |
| l2_nca_from_esm2_1nn | 96.99% | 96.47% | 93.72% | 94.75% | 96.98% |
| l2_nca_from_l1_ft_1nn | 97.82% | 97.50% | 95.15% | 96.00% | 97.82% |

### Head / body / tail

| Bin | Test families | Test samples | 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| head | 124 | 19211 | esm2_1nn | 93.24% | 92.81% | 90.96% | 91.78% | 93.27% |
| head | 124 | 19211 | l2_ft_1nn | 98.66% | 97.95% | 97.90% | 97.89% | 98.67% |
| head | 124 | 19211 | l2_ft_head | 98.79% | 98.06% | 98.14% | 98.07% | 98.79% |
| head | 124 | 19211 | l2_nca_from_esm2_1nn | 97.09% | 97.04% | 95.72% | 96.34% | 97.05% |
| head | 124 | 19211 | l2_nca_from_l1_ft_1nn | 97.90% | 97.47% | 96.58% | 96.99% | 97.88% |
| body | 50 | 338 | esm2_1nn | 83.73% | 86.81% | 81.05% | 82.23% | 84.53% |
| body | 50 | 338 | l2_ft_1nn | 94.67% | 96.44% | 94.82% | 95.20% | 95.34% |
| body | 50 | 338 | l2_ft_head | 95.27% | 97.34% | 94.33% | 95.03% | 96.04% |
| body | 50 | 338 | l2_nca_from_esm2_1nn | 91.42% | 95.07% | 88.74% | 90.79% | 93.01% |
| body | 50 | 338 | l2_nca_from_l1_ft_1nn | 92.90% | 97.58% | 91.60% | 93.56% | 94.69% |
| tail | 0 | 0 | esm2_1nn | N/A | N/A | N/A | N/A | N/A |
| tail | 0 | 0 | l2_ft_1nn | N/A | N/A | N/A | N/A | N/A |
| tail | 0 | 0 | l2_ft_head | N/A | N/A | N/A | N/A | N/A |
| tail | 0 | 0 | l2_nca_from_esm2_1nn | N/A | N/A | N/A | N/A | N/A |
| tail | 0 | 0 | l2_nca_from_l1_ft_1nn | N/A | N/A | N/A | N/A | N/A |

## 重新计算

在仓库根目录运行（只读取上述 CSV，不需要 GPU）：

```bash
/gpfs/research/rdf/zong/envs/cazy/bin/python src/evaluation/test_performance_report.py report --dataset peptidase --output results/test_performance_20260929
```

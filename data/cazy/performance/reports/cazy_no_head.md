# CAZy test set performance

- 1-NN：train 为 reference，test 为 query；原始 embedding，不额外归一化；精确 Euclidean 距离，相同距离按 reference ID 字典序裁决。
- ESM2 为原始模型；L0/L1/L2-FT 为直接从 ESM2 微调的 CE 路线。两个 L2-NCA 为既有 frozen MLP + SGD 路线。
- 分类指标：accuracy、macro precision/recall/F1、weighted F1；每类 accuracy 在单标签任务中等于该类 recall。所有未定义 precision/recall/F1 记为 0。
- 二分类 AUROC/AUPRC 以酶为 positive；AUPRC 使用 average precision (AP)。1-NN 连续分数为 $d_{negative}/(d_{positive}+d_{negative})$，$d$ 为到各类最近训练样本的 Euclidean 距离，两者都为 0 时取 0.5；这是距离分数，不是校准概率。
- Family 仅在 train 已知的 test families 上报告；未知 family 的样本保留在 CSV，标为 unknown，不纳入主指标。
- Family 分箱只依赖 train family 数量：head >100，body 11–100，tail 1–10。Macro 按有 test 支持的 family 平均。分箱 precision/F1 由整个 known test 的逐类混淆统计计算后在箱内平均，保留跨箱 false positives；分箱 accuracy 为该箱样本正确率。
- 数据及模型来源：[provenance](artifacts/cazy/provenance.json)。

## L0 binary classification

CSV：[cazy_binary_predictions.csv](cazy_binary_predictions.csv)；总样本 49,830，纳入指标 49,830。

| 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 | AUROC | AUPRC (AP) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| esm2_1nn | 96.81% | 96.93% | 96.71% | 96.80% | 96.81% | 99.55% | 99.57% |
| l0_ft_1nn | 99.00% | 98.99% | 98.99% | 98.99% | 99.00% | 99.81% | 99.78% |

### 各类指标

| Class | Support | 方法 | Precision | Recall / class accuracy | F1 |
| --- | --- | --- | --- | --- | --- |
| non-cazy | 23421 | esm2_1nn | 98.18% | 94.98% | 96.55% |
| non-cazy | 23421 | l0_ft_1nn | 98.94% | 98.93% | 98.93% |
| cazy | 26409 | esm2_1nn | 95.68% | 98.44% | 97.04% |
| cazy | 26409 | l0_ft_1nn | 99.05% | 99.06% | 99.05% |

## L1 6-class classification

CSV：[cazy_l1_predictions.csv](cazy_l1_predictions.csv)；总样本 26,409，纳入指标 26,409。

| 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 |
| --- | --- | --- | --- | --- | --- |
| esm2_1nn | 96.09% | 90.68% | 88.22% | 89.42% | 96.06% |
| l1_ft_1nn | 99.31% | 98.45% | 98.47% | 98.46% | 99.31% |

### 各类指标

| Class | Support | 方法 | Precision | Recall / class accuracy | F1 |
| --- | --- | --- | --- | --- | --- |
| GT | 15175 | esm2_1nn | 98.83% | 99.28% | 99.06% |
| GT | 15175 | l1_ft_1nn | 99.73% | 99.66% | 99.69% |
| GH | 7697 | esm2_1nn | 94.06% | 95.05% | 94.55% |
| GH | 7697 | l1_ft_1nn | 99.10% | 99.05% | 99.08% |
| CBM | 1926 | esm2_1nn | 89.38% | 86.55% | 87.95% |
| CBM | 1926 | l1_ft_1nn | 97.94% | 98.75% | 98.35% |
| CE | 892 | esm2_1nn | 89.76% | 84.53% | 87.07% |
| CE | 892 | l1_ft_1nn | 98.33% | 98.77% | 98.55% |
| PL | 481 | esm2_1nn | 79.91% | 75.26% | 77.52% |
| PL | 481 | l1_ft_1nn | 96.85% | 95.84% | 96.34% |
| AA | 238 | esm2_1nn | 92.14% | 88.66% | 90.36% |
| AA | 238 | l1_ft_1nn | 98.74% | 98.74% | 98.74% |

## L2 family classification

CSV：[cazy_family_predictions.csv](cazy_family_predictions.csv)；总样本 26,409，纳入指标 26,407。

排除未知 family：CBM15, CBM70（2 条）；macro 范围为 375 个有 test 支持的已知 families。

| 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 |
| --- | --- | --- | --- | --- | --- |
| esm2_1nn | 88.07% | 69.52% | 66.67% | 66.67% | 88.02% |
| l2_ft_1nn | 98.20% | 91.93% | 91.64% | 91.07% | 98.20% |
| l2_nca_from_esm2_1nn | 95.20% | 88.68% | 82.00% | 84.24% | 95.09% |
| l2_nca_from_l1_ft_1nn | 96.55% | 88.47% | 83.96% | 85.41% | 96.45% |

### Head / body / tail

| Bin | Test families | Test samples | 方法 | Accuracy | Macro-P | Macro-R | Macro-F1 | Weighted-F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| head | 118 | 23929 | esm2_1nn | 90.22% | 81.33% | 79.77% | 80.33% | 89.99% |
| head | 118 | 23929 | l2_ft_1nn | 98.67% | 97.24% | 97.35% | 97.24% | 98.65% |
| head | 118 | 23929 | l2_nca_from_esm2_1nn | 96.26% | 93.31% | 92.66% | 92.88% | 95.81% |
| head | 118 | 23929 | l2_nca_from_l1_ft_1nn | 97.56% | 94.62% | 94.78% | 94.62% | 97.21% |
| body | 190 | 2330 | esm2_1nn | 68.37% | 70.06% | 64.97% | 65.73% | 70.13% |
| body | 190 | 2330 | l2_ft_1nn | 94.64% | 94.57% | 93.31% | 93.21% | 94.89% |
| body | 190 | 2330 | l2_nca_from_esm2_1nn | 86.39% | 91.91% | 82.71% | 86.07% | 89.38% |
| body | 190 | 2330 | l2_nca_from_l1_ft_1nn | 88.41% | 92.45% | 84.62% | 87.70% | 90.63% |
| tail | 67 | 148 | esm2_1nn | 50.68% | 47.20% | 48.43% | 45.30% | 50.78% |
| tail | 67 | 148 | l2_ft_1nn | 78.38% | 75.10% | 76.87% | 74.14% | 77.66% |
| tail | 67 | 148 | l2_nca_from_esm2_1nn | 62.84% | 71.39% | 61.22% | 63.85% | 67.89% |
| tail | 67 | 148 | l2_nca_from_l1_ft_1nn | 62.84% | 66.37% | 63.01% | 62.68% | 64.80% |

## 重新计算

在仓库根目录运行（只读取上述 CSV，不需要 GPU）：

```bash
/gpfs/research/rdf/zong/envs/cazy/bin/python src/evaluation/test_performance_report.py report --dataset cazy --output results/test_performance_20260929
```

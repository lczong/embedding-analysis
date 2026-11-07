# 本地数据

`cazy/` 和 `peptidase/` 保存系统配置引用的 embedding 与 metadata。运行期只读取本项目中的文件，不依赖原项目目录。

迁移项目时一并复制这些数据，保持配置中的相对路径，再从项目根目录检查：

```bash
.venv/bin/python workflows/validate.py --config configs/cazy.json
.venv/bin/python workflows/validate.py --config configs/peptidase.json
```

需要全量 ID、有限值和标签对齐检查时加 `--deep`。

`import_manifest.json` 仅保留初次复制的来源及校验记录，运行不读取。数据不进入 Git；本目录的 README 由 Git 跟踪。

二分类图另导入五条 CAZy 路线的 `non-cazy_train.embeddings.csv`，配置角色为 `non_target_train`。副本 SHA256 与原文件一致，记录在 `binary_import_manifest.json`；L2 FT-CE 原目录无该输入。

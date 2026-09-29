# 本地数据

只导入 configs 中显式列出的输入。运行期不依赖旧项目目录。

```bash
python scripts/import_data.py --source-root /path/to/OOD2
```

macOS 使用独立的 APFS 写时复制，其余系统使用普通复制。不会建立软链接或硬链接。默认校验大小及文件首尾摘要；`--verify-full` 可额外逐字节比较。`import_manifest.json` 保存来源及检查方式。

数据不进入 Git。normalized/、无关 train/val/test、历史结果、压缩包不导入。

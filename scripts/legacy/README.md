# Legacy Scripts (已废弃)

这些脚本的功能已整合到 `scrape_all.py` 和 `cli.py` 中。

保留这些文件仅供参考，请使用：

```bash
# 统一 CLI
python scripts/cli.py scrape --all --lang jp
python scripts/cli.py scrape --series OP-15 --lang en
python scripts/cli.py scrape --check-new

# 或直接使用 scrape_all.py
python scripts/scrape_all.py --all --lang jp
```

## 废弃脚本对应关系

| 旧脚本 | 替代命令 |
|--------|----------|
| `scrape_en.py` | `scrape_all.py --lang en` |
| `scrape_en_full.py` | `scrape_all.py --all --lang en` |
| `rescrape_jp.py` | `scrape_all.py --all --lang jp` |
| `full_rescrape.py` | `scrape_all.py --all --lang jp` |
| `rescrape_series.py` | `scrape_all.py --series <code>` |
| `rescrape_missing.py` | `scrape_all.py --check-new` |

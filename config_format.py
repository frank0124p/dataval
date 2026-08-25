#!/usr/bin/env python3
"""Config 格式正規化 CLI。

用法：
    python config_format.py            # 依資料夾路徑把 config 補成可載入的格式
    python config_format.py --check    # 只看會改什麼，不寫檔（exit 1 = 有待調整）

只補格式與結構（包 ```mermaid fence、補標題、補段落標題、改副檔名），
不更動任何語意內容。run.py 起跑前會自動跑同一套（可用
DATAVAL_CONFIG_FORMAT=0 關閉）。
"""
from __future__ import annotations

import os
import sys

from dataval import config_format

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(HERE, "config")


def main() -> int:
    dry = "--check" in sys.argv
    summary = config_format.run_format(CONFIG_DIR, apply=not dry)
    for line in config_format.console_lines(summary):
        print(line)
    if dry and summary["changed"]:
        print("  👉 執行 python config_format.py 套用上述調整。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

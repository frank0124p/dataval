#!/usr/bin/env python3
"""Config 檔案格式檢查 CLI（pre-run lint）。

用法：
    python config_check.py            # 檢查 config/ 全部知識輸入的格式
    python config_check.py --reset    # 清掉快取後全量重驗

驗證 erd（md/mmd）、erd/tables 用途描述、flows（md/yaml）、naming 字典與
ssot registry 是否符合各資料夾 README 的 template。結果快取在
build/config_check.json——內容沒變的檔案下次不重驗。

exit code：0 = 全部通過；1 = 有格式問題（agent 修檔迴圈以此判斷）。
run.py 啟動時也會自動跑同一套檢查（不擋報告，只提醒）。
"""
from __future__ import annotations

import os
import sys

from dataval import config_check

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(HERE, "config")
CACHE_PATH = os.path.join(HERE, "build", "config_check.json")


def main() -> int:
    if "--reset" in sys.argv and os.path.isfile(CACHE_PATH):
        os.remove(CACHE_PATH)
        print("已清除快取，全量重驗。")
    summary = config_check.run_check(CONFIG_DIR, CACHE_PATH)
    for line in config_check.console_lines(summary):
        print(line)
    return 1 if summary["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())

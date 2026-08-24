#!/usr/bin/env python3
"""輸出文件的目錄配置——**一 subject 一資料夾**，design 與 govern 分兩個根。

```text
design_doc/<subject>/    🎨 設計模式產物（設計報告、邏輯／實體設計、
                            草稿 DDL 與拆檔、relations 草稿、ETL 建議檔）
govern_doc/<subject>/    🛡 治理模式產物（三式報告與輪次版、前置檢核、
                            顧問 prompt／result、主體摘要、建議 SQL／DDL）
```

兩個根都是「文件根 `doc_root` 之下的一層」，`doc_root` 預設＝專案根：

  DATAVAL_DOC_DIR      覆寫文件根（design_doc／govern_doc 的父層）
  DATAVAL_REPORT_DIR   舊名，仍相容——設了就當文件根用

檔名維持 `<subject>.` 前綴（`order.report.html`），資料夾單獨拉出去傳給
別人時仍看得出屬於哪個 subject。

**相對連結深度**：文件在 `<root>/<doc>/<subject>/`，所以報告裡指回專案根
（config 規則檔、input）的相對路徑一律用 `ROOT_PREFIX`，不要自己寫 `../`。
"""
from __future__ import annotations

import os

#: 兩個文件根的資料夾名
DESIGN_DOC = "design_doc"
GOVERN_DOC = "govern_doc"

#: 文件位於 <root>/<doc>/<subject>/ → 回專案根要往上兩層
ROOT_PREFIX = "../../"


def doc_root(here: str) -> str:
    """文件根（design_doc／govern_doc 的父層）。預設＝專案根。"""
    return (os.environ.get("DATAVAL_DOC_DIR")
            or os.environ.get("DATAVAL_REPORT_DIR")
            or here)


def design_root(root: str) -> str:
    return os.path.join(root, DESIGN_DOC)


def govern_root(root: str) -> str:
    return os.path.join(root, GOVERN_DOC)


def _subject_dir(base: str, subject: str, create: bool) -> str:
    path = os.path.join(base, subject)
    if create:
        os.makedirs(path, exist_ok=True)
    return path


def design_dir(root: str, subject: str, create: bool = True) -> str:
    """🎨 `<root>/design_doc/<subject>/`（預設順手建好）。"""
    return _subject_dir(design_root(root), subject, create)


def govern_dir(root: str, subject: str, create: bool = True) -> str:
    """🛡 `<root>/govern_doc/<subject>/`（預設順手建好）。"""
    return _subject_dir(govern_root(root), subject, create)


def label(path: str, here: str) -> str:
    """console 顯示用的相對路徑（落在專案外就用絕對路徑，不印一串 ../）。"""
    rel = os.path.relpath(path, here)
    return path if rel.startswith("..") else rel

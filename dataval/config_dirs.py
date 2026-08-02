"""config/ 下 domain 資料夾的統一解析。

五個載入器（glossary／表用途／flows／參考 ER／run 的 ER 疊加）過去各自
維護同一段「Common 先、宣告域後、大小寫不敏感、跳過 _ 開頭、去重」的
資料夾解析——本模組是唯一實作。
"""
from __future__ import annotations
import os


def domain_folders(config_dir: str, domains: list[str] | None
                   ) -> list[tuple[str, str]]:
    """依載入順序回傳 [(資料夾名, 絕對路徑)]。

    順序：Common 恆先，之後依宣告順序；資料夾名大小寫不敏感比對、
    去重；`_` 開頭（引擎內部）不列入。config_dir 不存在回空清單。
    """
    if not os.path.isdir(config_dir):
        return []
    folders = {f.lower(): f for f in os.listdir(config_dir)
               if os.path.isdir(os.path.join(config_dir, f))
               and not f.startswith("_")}
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for want in ["Common"] + [d for d in (domains or []) if d]:
        folder = folders.get(str(want).strip().lower())
        if not folder or folder in seen:
            continue
        seen.add(folder)
        out.append((folder, os.path.join(config_dir, folder)))
    return out

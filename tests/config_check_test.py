#!/usr/bin/env python3
"""Config 格式檢查（pre-run lint）與快取的守門測試。

守的保證：
  K1 好檔通過；各類壞檔逐檔指名原因（erd 缺 fence／flow 壞圖／
     glossary 壞列／tables 檔名標題不一致或空內容）
  K2 快取：沒變的檔案不重驗；內容變了重驗；刪檔自快取移除
  K3 快取檔確定性：結果沒變時不改寫（位元組相同）
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval.config_check import run_check


def write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


GOOD_ERD = "# 模型\n\n```mermaid\nerDiagram\n  a ||--o{ b : x\n```\n"
GOOD_FLOW = "# 流程\n\n```mermaid\nflowchart LR\n  src --> orders --> rpt\n```\n"
GOOD_GLOSSARY = "## 禁用詞\n| 禁用 | 改用 |\n|---|---|\n| qty | quantity |\n"
GOOD_PURPOSE = "# orders\n訂單頭事實表。\n"


class T_K1_Checks(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cfg)
        self.cache = os.path.join(self.cfg, "_cache.json")

    def test_good_files_all_pass(self):
        write(os.path.join(self.cfg, "CRM", "erd", "core.md"), GOOD_ERD)
        write(os.path.join(self.cfg, "CRM", "erd", "tables", "orders.md"),
              GOOD_PURPOSE)
        write(os.path.join(self.cfg, "CRM", "flows", "f.md"), GOOD_FLOW)
        write(os.path.join(self.cfg, "CRM", "naming", "glossary.md"),
              GOOD_GLOSSARY)
        s = run_check(self.cfg, self.cache)
        self.assertEqual({}, s["problems"])
        self.assertEqual(4, s["total"])

    def test_bad_files_named_with_reason(self):
        write(os.path.join(self.cfg, "CRM", "erd", "no_fence.md"),
              "# 只有文字沒有圖\n")
        write(os.path.join(self.cfg, "CRM", "flows", "bad.md"),
              "# 流程\n\n```mermaid\nflowchart LR\n  只有一個節點\n```\n")
        write(os.path.join(self.cfg, "CRM", "naming", "glossary.md"),
              "## 禁用詞\n| 表頭A | 表頭B |\n|---|---|\n| 只有一欄 |\n")
        write(os.path.join(self.cfg, "CRM", "erd", "tables", "orders.md"),
              "# other_name\n內容。\n")
        write(os.path.join(self.cfg, "CRM", "erd", "tables", "empty_t.md"),
              "# empty_t\n")
        s = run_check(self.cfg, self.cache)
        self.assertEqual(5, len(s["problems"]))
        self.assertIn("mermaid", s["problems"]["CRM/erd/no_fence.md"][0])
        self.assertIn("站點連線", s["problems"]["CRM/flows/bad.md"][0])
        self.assertIn("兩欄", s["problems"]["CRM/naming/glossary.md"][0])
        self.assertIn("不一致", s["problems"]["CRM/erd/tables/orders.md"][0])
        self.assertIn("空", s["problems"]["CRM/erd/tables/empty_t.md"][0])

    def test_readme_and_engine_dir_skipped(self):
        write(os.path.join(self.cfg, "CRM", "erd", "README.md"), "說明")
        write(os.path.join(self.cfg, "_engine", "erd", "x.md"), "不掃")
        s = run_check(self.cfg, self.cache)
        self.assertEqual(0, s["total"])

    def test_orphan_files_are_flagged_not_silent(self):
        """引擎不會載入的檔案（放錯副檔名／檔名）必須點名，不得靜默忽略。"""
        write(os.path.join(self.cfg, "CRM", "flows", "wrong.yaml"), "flow: x\n")
        write(os.path.join(self.cfg, "CRM", "erd", "notes.txt"), "筆記\n")
        write(os.path.join(self.cfg, "CRM", "naming", "glossary.md"),
              GOOD_GLOSSARY)
        write(os.path.join(self.cfg, "CRM", "naming", "glossary.yaml"),
              "banned_terms: {}\n")   # 有 md 時 yaml 被忽略 → 要點名
        s = run_check(self.cfg, self.cache)
        self.assertIn("CRM/flows/wrong.yaml", s["problems"])
        self.assertIn("不會被引擎載入", s["problems"]["CRM/flows/wrong.yaml"][0])
        self.assertIn("CRM/erd/notes.txt", s["problems"])
        self.assertIn("CRM/naming/glossary.yaml", s["problems"])

    def test_naming_any_md_filename_is_loaded(self):
        """naming 字典任意檔名的 .md 都要載入（多檔合併）。"""
        from dataval.engine import load_glossary
        write(os.path.join(self.cfg, "Common", "naming", "glossary.md"),
              GOOD_GLOSSARY)
        write(os.path.join(self.cfg, "Common", "naming", "my_terms.md"),
              "## 禁用詞\n| 禁用 | 改用 |\n|---|---|\n| shp | shipment |\n")
        g = load_glossary(self.cfg, domains=[])
        self.assertEqual("quantity", g["banned_terms"]["qty"])
        self.assertEqual("shipment", g["banned_terms"]["shp"])


class T_K2_Cache(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cfg)
        self.cache = os.path.join(self.cfg, "_cache.json")
        self.erd = os.path.join(self.cfg, "CRM", "erd", "core.md")
        write(self.erd, GOOD_ERD)

    def test_unchanged_file_uses_cache(self):
        first = run_check(self.cfg, self.cache)
        self.assertEqual((1, 0), (first["checked"], first["cached"]))
        second = run_check(self.cfg, self.cache)
        self.assertEqual((0, 1), (second["checked"], second["cached"]))

    def test_changed_file_is_rechecked(self):
        run_check(self.cfg, self.cache)
        write(self.erd, "# 改壞\n沒有圖了\n")
        s = run_check(self.cfg, self.cache)
        self.assertEqual(1, s["checked"])
        self.assertIn("CRM/erd/core.md", s["problems"])
        # 修好 → 再重驗一次後轉綠
        write(self.erd, GOOD_ERD)
        s2 = run_check(self.cfg, self.cache)
        self.assertEqual({}, s2["problems"])

    def test_deleted_file_removed_from_cache(self):
        run_check(self.cfg, self.cache)
        os.remove(self.erd)
        run_check(self.cfg, self.cache)
        with open(self.cache, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual({}, data["files"])

    def test_cache_file_stable_when_nothing_changes(self):
        run_check(self.cfg, self.cache)
        with open(self.cache, "rb") as f:
            before = f.read()
        stamp = os.path.getmtime(self.cache)
        run_check(self.cfg, self.cache)
        with open(self.cache, "rb") as f:
            after = f.read()
        self.assertEqual(before, after)
        self.assertEqual(stamp, os.path.getmtime(self.cache))


if __name__ == "__main__":
    unittest.main()

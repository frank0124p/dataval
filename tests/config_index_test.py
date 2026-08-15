#!/usr/bin/env python3
"""config 知識庫總索引（config_index.py）的守門測試。

守的保證：
  I1 四大章節齊全：網域總覽／素材清單／關聯性（ER＋SSOT＋機制）／Tag 一覽
  I2 內容確定性：連跑兩次結果相同（無時間戳）
  I3 關聯性正確：ER 關係、SSOT 權威、基數記號跳脫不破表格
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import config_index  # noqa: E402


class ConfigIndexTest(unittest.TestCase):
    def test_sections_relations_and_determinism(self):
        text = config_index.generate()
        # I1 章節齊全
        self.assertIn("## 1. 網域（Product Suite）總覽", text)
        self.assertIn("root((config 知識庫))", text)         # 全景 mindmap
        self.assertIn("## 2. 素材清單", text)
        self.assertIn("### 3.1 各域 ER 參考模型", text)
        self.assertIn("### 3.2 SSOT 權威對照", text)
        self.assertIn("### 3.3 知識如何互相支撐", text)
        self.assertIn("## 4. 標記（Tag）一覽", text)
        # I3 關聯性內容
        self.assertIn("`dim_customer`", text)
        self.assertIn("客戶下訂單", text)
        self.assertIn("`customer` | `dim_customer`", text)   # SSOT 權威
        self.assertIn("\\|\\|--o{", text)                    # 基數記號已跳脫
        self.assertNotIn("| `||--o{` |", text)               # 不得裸露破表格
        # 素材與 tag
        self.assertIn("config/CRM/erd/crm_core.md", text)
        self.assertIn("`om`、`pi`", text)                    # 產品入總覽
        self.assertIn("| `L` |", text)                       # tag 定義
        self.assertIn("blocking / warning", text)
        # 重新產生指令有寫在檔頭
        self.assertIn("python config_index.py", text)
        # I2 確定性
        self.assertEqual(text, config_index.generate())


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""config 輸入 md 化的守門測試。

守的保證：
  M1 extract_mermaid：fence 取出／多 fence 合併／無 fence 原文返回
  M2 glossary.md 確定性解析（表頭跳過、分隔列跳過、標準詞清單），
     且與舊 yaml 內容等值 → naming 閘門判定不變
  M3 flows .md（mermaid flowchart）：FLOW.CONTEXT 上下游、分支圖、壞檔 FLOW.SPEC
  M4 參考表用途（erd/tables/*.md）→ ERD.TABLE_PURPOSE（顧問區 info，不擋）
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import flows
from dataval.engine import _glossary_from_md, load_config, load_glossary, validate
from dataval.er_diagram import extract_mermaid, load_table_purposes, parse_mermaid
from dataval.parser import parse_ddl

CFG = os.path.join(ROOT, "config", "_engine", "default.yaml")
KW = dict(domain_root=os.path.join(ROOT, "config"),
          rules_root=os.path.join(ROOT, "config", "Common", "knowhow_py"),
          config_dir=os.path.join(ROOT, "config"),
          production_root=os.path.join(ROOT, "production"))


def write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class T_M1_ExtractMermaid(unittest.TestCase):
    def test_fence_extracted_prose_ignored(self):
        md = "# 標題\n說明文字\n\n```mermaid\nerDiagram\n  a ||--o{ b : x\n```\n尾註"
        parsed = parse_mermaid(extract_mermaid(md))
        self.assertEqual([], parsed["errors"])
        self.assertEqual(1, len(parsed["relationships"]))

    def test_multiple_fences_merged(self):
        md = ("```mermaid\nerDiagram\n  a ||--o{ b : x\n```\n中間文字\n"
              "```mermaid\n  b ||--o{ c : y\n```")
        parsed = parse_mermaid(extract_mermaid(md))
        self.assertEqual(2, len(parsed["relationships"]))

    def test_no_fence_returns_raw(self):
        raw = "erDiagram\n  a ||--o{ b : x"
        self.assertEqual(raw, extract_mermaid(raw))


class T_M2_GlossaryMd(unittest.TestCase):
    MD = ("# 字典\n\n## 禁用詞\n| 禁用 | 改用 |\n|---|---|\n"
          "| qty | quantity |\n| amt | amount |\n\n"
          "## 別名\n| 別名 | 正規詞 |\n|---|---|\n| client | customer |\n\n"
          "## 標準詞\n- customer\n- order\n")

    def test_md_parses_sections(self):
        g = _glossary_from_md(self.MD)
        self.assertEqual({"qty": "quantity", "amt": "amount"}, g["banned_terms"])
        self.assertEqual({"client": "customer"}, g["aliases"])
        self.assertEqual(["customer", "order"], g["standard_terms"])

    def test_header_and_separator_rows_skipped(self):
        g = _glossary_from_md(self.MD)
        self.assertNotIn("禁用", g["banned_terms"])
        self.assertNotIn("---", g["banned_terms"])

    def test_md_preferred_over_yaml_and_merges_by_domain(self):
        cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg)
        write(os.path.join(cfg, "Common", "naming", "glossary.md"),
              "## 禁用詞\n| 禁用 | 改用 |\n|---|---|\n| qty | quantity |\n")
        write(os.path.join(cfg, "Common", "naming", "glossary.yaml"),
              "banned_terms:\n  qty: WRONG\n")   # md 優先，yaml 被忽略
        write(os.path.join(cfg, "SCM", "naming", "glossary.md"),
              "## 禁用詞\n| 禁用 | 改用 |\n|---|---|\n| supp | supplier |\n")
        g = load_glossary(cfg, domains=["SCM"])
        self.assertEqual("quantity", g["banned_terms"]["qty"])
        self.assertEqual("supplier", g["banned_terms"]["supp"])

    def test_repo_glossary_md_matches_previous_yaml_content(self):
        """轉換等值：現行 config 的 md 字典必須含原 yaml 的全部詞條。"""
        g = load_glossary(os.path.join(ROOT, "config"), domains=[])
        self.assertEqual("quantity", g["banned_terms"]["qty"])
        self.assertEqual("customer", g["banned_terms"]["cust"])
        self.assertEqual("address", g["banned_terms"]["addr"])
        self.assertEqual("customer", g["aliases"]["client"])
        self.assertEqual("product", g["aliases"]["sku"])
        self.assertEqual(9, len(g["banned_terms"]))
        self.assertEqual(6, len(g["aliases"]))
        self.assertEqual([], g["standard_terms"])


class T_M3_FlowsMd(unittest.TestCase):
    DDL = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x') "
           "ENGINE=MergeTree() ORDER BY (order_id);")

    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cfg)

    def test_md_flow_marks_table_with_neighbors(self):
        write(os.path.join(self.cfg, "CRM", "flows", "f.md"),
              "# 測試流程\n\n```mermaid\nflowchart LR\n"
              "  來源 --> orders --> 報表\n```\n")
        out = flows.run(parse_ddl(self.DDL), ["CRM"], self.cfg)
        ctx = [f for f in out if f.check_id == "FLOW.CONTEXT"]
        self.assertEqual(1, len(ctx))
        self.assertEqual("orders", ctx[0].target)
        self.assertEqual("advisory", ctx[0].zone)
        self.assertIn("測試流程", ctx[0].message)
        self.assertIn("來源", ctx[0].message)
        self.assertIn("報表", ctx[0].message)

    def test_branching_flow_lists_all_neighbors(self):
        write(os.path.join(self.cfg, "CRM", "flows", "f.md"),
              "# 分支\n\n```mermaid\nflowchart LR\n"
              "  a[系統A] --> orders\n  b[系統B] --> orders\n"
              "  orders --> r1[報表一]\n  orders --> r2[報表二]\n```\n")
        out = flows.run(parse_ddl(self.DDL), ["CRM"], self.cfg)
        ctx = [f for f in out if f.check_id == "FLOW.CONTEXT"]
        self.assertEqual(1, len(ctx))
        for name in ("系統A", "系統B", "報表一", "報表二"):
            self.assertIn(name, ctx[0].message)

    def test_node_labels_match_tables(self):
        write(os.path.join(self.cfg, "CRM", "flows", "f.md"),
              "# 標籤\n\n```mermaid\nflowchart LR\n"
              "  src[來源] --> o[(orders)] --> rpt[報表]\n```\n")
        out = flows.run(parse_ddl(self.DDL), ["CRM"], self.cfg)
        ctx = [f for f in out if f.check_id == "FLOW.CONTEXT"]
        self.assertEqual(1, len(ctx))
        self.assertEqual("orders", ctx[0].target)

    def test_broken_md_flow_warns_not_blocks(self):
        write(os.path.join(self.cfg, "Common", "flows", "bad.md"),
              "# 沒有圖\n只有文字。\n")
        out = flows.run(parse_ddl(self.DDL), [], self.cfg)
        spec = [f for f in out if f.check_id == "FLOW.SPEC"]
        self.assertEqual(1, len(spec))
        self.assertEqual("warning", spec[0].status)
        self.assertEqual("gating", spec[0].zone)

    def test_readme_is_skipped(self):
        write(os.path.join(self.cfg, "Common", "flows", "README.md"),
              "# 說明\n這不是流程。\n")
        out = flows.run(parse_ddl(self.DDL), [], self.cfg)
        self.assertEqual([], [f for f in out if f.check_id == "FLOW.SPEC"])


class T_M4_TablePurposes(unittest.TestCase):
    DDL = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x') "
           "ENGINE=MergeTree() ORDER BY (order_id);")

    def test_load_and_domain_override(self):
        cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg)
        write(os.path.join(cfg, "Common", "erd", "tables", "orders.md"),
              "# orders\nCommon 版描述。\n")
        write(os.path.join(cfg, "CRM", "erd", "tables", "orders.md"),
              "# orders\nCRM 版描述。\n")
        purposes = load_table_purposes(cfg, ["CRM"])
        self.assertEqual("CRM 版描述。", purposes["orders"]["purpose"])
        purposes_common = load_table_purposes(cfg, [])
        self.assertEqual("Common 版描述。", purposes_common["orders"]["purpose"])

    def test_reference_purpose_becomes_advisory_info(self):
        """本 repo 的 CRM 參考表：orders 有登錄用途 → ERD.TABLE_PURPOSE。"""
        cfg = load_config(CFG)
        _, findings, meta = validate(self.DDL, cfg, domains=["CRM"], **KW)
        hits = [f for f in findings if f.check_id == "ERD.TABLE_PURPOSE"]
        self.assertEqual(1, len(hits))
        self.assertEqual("orders", hits[0].target)
        self.assertEqual("advisory", hits[0].zone)
        self.assertEqual("info", hits[0].status)
        self.assertIn("orders", meta["reference_purposes"])
        # 顧問區資訊永不影響合規判定
        self.assertNotIn(hits[0].status, ("fail", "warning"))


if __name__ == "__main__":
    unittest.main()

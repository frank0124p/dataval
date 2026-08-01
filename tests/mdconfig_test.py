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

    def test_any_heading_level_and_synonyms_recognized(self):
        """# ～ ###### 任意層級、縮寫/同義等關鍵字變體都要能辨識。"""
        g = _glossary_from_md(
            "# 縮寫對照\n| 縮寫 | 改用 |\n|---|---|\n| shp | shipment |\n\n"
            "### 同義詞\n| 同義 | 正規 |\n|---|---|\n| client | customer |\n")
        self.assertEqual({"shp": "shipment"}, g["banned_terms"])
        self.assertEqual({"client": "customer"}, g["aliases"])

    def test_unrecognized_sections_fail_loudly(self):
        """檔內有對照表但沒有可辨識段落 → 必須報錯，不得整份靜默失效。"""
        with self.assertRaises(ValueError) as ctx:
            _glossary_from_md(
                "## 我們的命名規範\n| 詞 | 改用 |\n|---|---|\n| a | b |\n")
        self.assertIn("不會生效", str(ctx.exception))
        # 透過 loader 也要以 problem 浮出（→ SYSTEM.CONFIG_SPEC 警告）
        cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg)
        write(os.path.join(cfg, "Common", "naming", "terms.md"),
              "## 命名規範\n| 詞 | 改用 |\n|---|---|\n| a | b |\n")
        problems = []
        g = load_glossary(cfg, domains=[], problems=problems)
        self.assertEqual({}, g["banned_terms"])
        self.assertEqual(1, len(problems))
        self.assertIn("terms.md", problems[0])

    def test_prose_only_md_without_tables_is_harmless(self):
        g = _glossary_from_md("# 說明\n這份文件還沒開始寫字典。\n")
        self.assertEqual({}, g["banned_terms"])

    def test_repo_glossaries_parse_cleanly(self):
        """repo 現行字典必須可解析、無壞檔——不鎖詞條內容
        （詞條是使用者日常編輯的資料，不是引擎契約）。"""
        problems: list[str] = []
        g = load_glossary(os.path.join(ROOT, "config"), domains=["*"],
                          problems=problems)
        self.assertEqual([], problems)
        self.assertIsInstance(g["banned_terms"], dict)
        self.assertIsInstance(g["aliases"], dict)
        self.assertIsInstance(g["standard_terms"], list)


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

    def test_header_line_never_becomes_a_node(self):
        """標頭行處理：註解可在標頭前；重複標頭（多 fence 合併）要跳過，
        graph/flowchart 這些字不得被當成節點。"""
        spec = flows.parse_flow_md(
            "# 流程\n\n```mermaid\n%% 前置註解\n%%{init: {'theme':'dark'}}%%\n"
            "graph LR\n  a[來源] --> orders;\n```\n\n說明文字\n\n"
            "```mermaid\nflowchart TD\n  orders --> b[報表]\n```\n", "f")
        names = set(spec["_nodes"])
        self.assertNotIn("graph", names)
        self.assertNotIn("flowchart", names)
        self.assertEqual({"a", "orders", "b"}, names)
        self.assertEqual([("a", "orders"), ("orders", "b")], spec["_edges"])

    def test_missing_header_still_rejected(self):
        with self.assertRaises(ValueError) as ctx:
            flows.parse_flow_md(
                "# 流程\n\n```mermaid\n  a --> b\n```\n", "f")
        self.assertIn("標頭", str(ctx.exception))

    def test_trailing_semicolons_stripped(self):
        spec = flows.parse_flow_md(
            "# 流程\n\n```mermaid\nflowchart LR\n  a --> orders；\n```\n", "f")
        self.assertIn("orders", spec["_nodes"])


class T_M5_CheckOrigins(unittest.TestCase):
    """報告的「依據來源」：每筆檢查都要能回溯到 config／input 的哪裡。"""
    DDL = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x') "
           "ENGINE=MergeTree() ORDER BY (order_id);")

    def test_origins_in_all_three_report_formats(self):
        import json as _json
        from dataval.report import check_origins, to_json, to_markdown, to_html
        cfg = load_config(CFG)
        _, findings, meta = validate(self.DDL, cfg, domains=["CRM"], **KW)
        origins = check_origins(findings, meta)
        # SKILL 規則 → 規則檔實際路徑（自洽：與涵蓋清單記載的 file 一致，
        # 不鎖死特定規則檔路徑——使用者會搬移／增修規則）
        loaded = {r["id"]: r for r in meta["rule_coverage"]["loaded"]
                  if r.get("file")}
        self.assertTrue(loaded)
        sample_id, sample = sorted(loaded.items())[0]
        self.assertTrue(origins[sample_id].startswith(f"config/{sample['file']}"))
        self.assertIn("context.md", origins["BUSINESS_KEY.METADATA"])
        md = to_markdown(findings, meta)
        self.assertIn(f"依據：config/{sample['file']}", md)
        self.assertIn("依據：", to_html(findings, meta))
        payload = _json.loads(to_json(findings, meta))
        self.assertEqual(origins, payload["check_origins"])

    def test_flow_context_names_source_file(self):
        """FLOW.CONTEXT 訊息要指名流程檔——用自建流程檔測，不依賴 repo 內容。"""
        cfg_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg_dir)
        write(os.path.join(cfg_dir, "CRM", "flows", "myflow.md"),
              "# 測\n\n```mermaid\nflowchart LR\n  src --> orders --> rpt\n```\n")
        out = flows.run(parse_ddl(self.DDL), ["CRM"], cfg_dir)
        ctx = [f for f in out if f.check_id == "FLOW.CONTEXT"]
        self.assertTrue(ctx)
        self.assertIn("config/CRM/flows/myflow.md", ctx[0].message)


class T_M6_EntityReference(unittest.TestCase):
    """ER 參考模型 entity 欄位定義 → DDL 確定性對照（ERD.ENTITY_REFERENCE）。"""
    DDL = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x', "
           "amount Decimal(18,2) COMMENT 'y') "
           "ENGINE=MergeTree() PRIMARY KEY (order_id) ORDER BY (order_id);")

    def _er(self, mermaid: str) -> dict:
        parsed = parse_mermaid(mermaid, source="CRM/erd/test.md")
        for ent in parsed["entities"].values():
            ent["source"] = "CRM/erd/test.md"
        return parsed

    def test_missing_reference_column_warns(self):
        from dataval.er_diagram import entity_reference_findings
        er = self._er("erDiagram\norders {\n  UInt64 order_id PK\n"
                      "  DateTime created_at\n}\n")
        out = entity_reference_findings(parse_ddl(self.DDL), er)
        warns = [f for f in out if f.status == "warning"]
        self.assertEqual(1, len(warns))
        self.assertEqual("gating", warns[0].zone)
        self.assertIn("created_at", warns[0].message)
        self.assertIn("CRM/erd/test.md", warns[0].rationale)

    def test_all_columns_present_passes(self):
        from dataval.er_diagram import entity_reference_findings
        er = self._er("erDiagram\norders {\n  UInt64 order_id PK\n"
                      "  Decimal amount\n}\n")
        out = entity_reference_findings(parse_ddl(self.DDL), er)
        self.assertEqual(["pass"], [f.status for f in out])

    def test_pk_flag_not_in_keys_warns(self):
        from dataval.er_diagram import entity_reference_findings
        ddl = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x') "
               "ENGINE=MergeTree() ORDER BY (order_id);")  # 只有排序鍵,無 PK
        er = self._er("erDiagram\norders {\n  UInt64 order_id PK\n}\n")
        out = entity_reference_findings(parse_ddl(ddl), er)
        pk_warns = [f for f in out if "PK" in f.message]
        self.assertEqual(1, len(pk_warns))
        self.assertEqual("warning", pk_warns[0].status)

    def test_entity_without_columns_is_ignored(self):
        from dataval.er_diagram import entity_reference_findings
        er = self._er("erDiagram\n  orders ||--o{ x : y\n")
        self.assertEqual([], entity_reference_findings(parse_ddl(self.DDL), er))

    def test_domain_erd_entity_columns_merged_into_case(self):
        """merge_domain_erds 要把參考模型的 entity 欄位定義帶進來。"""
        import run as R
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        write(os.path.join(tmp, "CRM", "erd", "core.md"),
              "# 模型\n\n```mermaid\nerDiagram\norders {\n"
              "  UInt64 order_id PK\n  DateTime created_at\n}\n```\n")
        merged = R.merge_domain_erds(None, ["CRM"], {"orders"}, [], droot=tmp)
        self.assertIsNotNone(merged)
        cols = [c["name"] for c in merged["entities"]["orders"]["columns"]]
        self.assertEqual(["order_id", "created_at"], cols)
        self.assertEqual("CRM/erd/core.md",
                         merged["entities"]["orders"]["source"])


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
        """有登錄用途的表 → ERD.TABLE_PURPOSE（自洽比對 repo 現況，
        不鎖定 config 內容——使用者日常會增修參考表）。"""
        cfg = load_config(CFG)
        expected = load_table_purposes(os.path.join(ROOT, "config"), ["CRM"])
        _, findings, meta = validate(self.DDL, cfg, domains=["CRM"], **KW)
        hits = {f.target: f for f in findings
                if f.check_id == "ERD.TABLE_PURPOSE"}
        want = {"orders"} & set(expected)   # 本 DDL 只有 orders 這張表
        self.assertEqual(want, set(hits))
        for f in hits.values():
            self.assertEqual("advisory", f.zone)
            self.assertEqual("info", f.status)   # 顧問區資訊永不影響判定
        self.assertEqual(want, set(meta["reference_purposes"]))


if __name__ == "__main__":
    unittest.main()

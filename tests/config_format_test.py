#!/usr/bin/env python3
"""Config 格式正規化（config_format.py）的守門測試。

守的保證：
  N1 依資料夾補格式：erd 的圖包 ```mermaid fence、flows 補 fence 與標題、
     erd/tables 補 `# <表名>` 標題
  N2 詞彙字典救援：對照表沒有段落標題時整份不生效——依表頭關鍵字補標題，
     補完 engine 真的讀得到詞條
  N3 副檔名改名：放錯副檔名的檔案引擎根本不掃，改成正確副檔名
  N4 冪等與位元組穩定：已正確的檔案不改寫；跑第二次沒有任何動作
  N5 dry run 不寫檔
  N6 只補格式不動語意：判斷不出來的檔案不猜（留給 config_check 報）
  N7 補完的檔案能通過 config_check（兩支工具對得上）
  N8 規則檔（knowhow）：缺 category／enforcement 依檔名與資料夾補齊、
     卡控 fence 標籤正規化；補完後 compile 真的載得進來
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import config_check, config_format                 # noqa: E402
from dataval.engine import load_glossary                        # noqa: E402


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.dom = os.path.join(self.dir, "CRM")

    def path(self, *parts) -> str:
        return os.path.join(self.dom, *parts)

    def run_format(self, apply=True):
        return config_format.run_format(self.dir, apply=apply)


class T_N1_FolderShapes(Base):
    def test_erd_diagram_gets_fence(self):
        p = self.path("erd", "core.md")
        write(p, "# CRM 核心模型\n說明文字。\n\nerDiagram\n"
                 '    dim_customer ||--o{ orders : "客戶下訂單"\n')
        summary = self.run_format()
        self.assertEqual(1, len(summary["changed"]))
        text = read(p)
        self.assertIn("```mermaid\nerDiagram", text)
        self.assertTrue(text.rstrip().endswith("```"))
        self.assertIn("# CRM 核心模型", text)          # fence 外說明保留
        self.assertIn("客戶下訂單", text)               # 內容一字未動

    def test_flow_gets_fence_and_title(self):
        p = self.path("flows", "order_to_revenue.md")
        write(p, "flowchart LR\n  結帳服務 --> orders --> 營收日報\n")
        self.run_format()
        text = read(p)
        self.assertIn("# order_to_revenue", text)      # 標題用檔名補
        self.assertIn("```mermaid\nflowchart LR", text)

    def test_table_purpose_gets_title(self):
        p = self.path("erd", "tables", "orders.md")
        write(p, "訂單頭事實表。一列代表一張已成立的訂單。\n")
        self.run_format()
        text = read(p)
        self.assertTrue(text.startswith("# orders\n"))
        self.assertIn("訂單頭事實表", text)


class T_N2_GlossaryRescue(Base):
    def test_headings_added_from_table_header(self):
        p = self.path("naming", "glossary.md")
        write(p, "# 詞彙字典\n\n| 禁用 | 改用 |\n|---|---|\n| cust | customer |\n"
                 "\n| 別名 | 正規詞 |\n|---|---|\n| client | customer |\n")
        summary = self.run_format()
        text = read(p)
        self.assertIn("## 禁用詞", text)
        self.assertIn("## 別名", text)
        self.assertEqual(2, len(summary["changed"][0]["actions"]))
        # 補完之後 engine 真的讀得到（原本整份不生效）
        merged = load_glossary(self.dir, ["CRM"])
        self.assertEqual("customer", merged["banned_terms"]["cust"])
        self.assertEqual("customer", merged["aliases"]["client"])

    def test_existing_headings_untouched(self):
        p = self.path("naming", "glossary.md")
        original = ("# 字典\n\n## 禁用詞\n\n| 禁用 | 改用 |\n|---|---|\n"
                    "| cust | customer |\n")
        write(p, original)
        self.assertEqual([], self.run_format()["changed"])
        self.assertEqual(original, read(p))


class T_N3_Rename(Base):
    def test_wrong_extension_renamed(self):
        write(self.path("flows", "pipeline.yaml"), "stages:\n  - name: orders\n")
        write(self.path("erd", "core.markdown"), "```mermaid\nerDiagram\n"
                                                 "  a ||--o{ b : x\n```\n")
        summary = self.run_format()
        self.assertTrue(os.path.isfile(self.path("flows", "pipeline.flow.yaml")))
        self.assertTrue(os.path.isfile(self.path("erd", "core.md")))
        self.assertFalse(os.path.isfile(self.path("flows", "pipeline.yaml")))
        self.assertEqual({"pipeline.flow.yaml", "core.md"},
                         {os.path.basename(c["rel"]) for c in summary["changed"]})

    def test_no_clobber_when_target_exists(self):
        write(self.path("erd", "core.md"), "```mermaid\nerDiagram\n"
                                           "  a ||--o{ b : x\n```\n")
        write(self.path("erd", "core.txt"), "備忘：不要動我\n")
        self.run_format()
        self.assertTrue(os.path.isfile(self.path("erd", "core.txt")))
        self.assertIn("不要動我", read(self.path("erd", "core.txt")))


class T_N4_Idempotent(Base):
    def test_second_run_is_a_noop(self):
        write(self.path("erd", "core.md"),
              "erDiagram\n    a ||--o{ b : \"x\"\n")
        write(self.path("flows", "f.md"), "flowchart LR\n  a --> b\n")
        write(self.path("erd", "tables", "orders.md"), "訂單表。\n")
        self.assertEqual(3, len(self.run_format()["changed"]))
        snapshot = {p: read(p) for p in (
            self.path("erd", "core.md"), self.path("flows", "f.md"),
            self.path("erd", "tables", "orders.md"))}
        self.assertEqual([], self.run_format()["changed"])
        for p, text in snapshot.items():
            self.assertEqual(text, read(p))            # 位元組穩定


class T_N5_DryRun(Base):
    def test_check_mode_does_not_write(self):
        p = self.path("erd", "core.md")
        original = "erDiagram\n    a ||--o{ b : \"x\"\n"
        write(p, original)
        summary = self.run_format(apply=False)
        self.assertEqual(1, len(summary["changed"]))
        self.assertEqual(original, read(p))            # 沒有寫檔


class T_N6_NeverGuess(Base):
    def test_unrecognizable_files_left_alone(self):
        # 看不出是 mermaid 圖 → 不動（config_check 會報）
        prose = self.path("erd", "notes.md")
        write(prose, "# 一些筆記\n這裡沒有圖。\n")
        # 表頭看不出是禁用詞還是別名 → 不猜
        vague = self.path("naming", "terms.md")
        write(vague, "# 詞表\n\n| 欄位 | 說明 |\n|---|---|\n| a | b |\n")
        self.assertEqual([], self.run_format()["changed"])
        self.assertIn("這裡沒有圖", read(prose))
        self.assertIn("| a | b |", read(vague))


class T_N7_MatchesConfigCheck(Base):
    def test_formatted_files_pass_the_checker(self):
        write(self.path("erd", "core.md"),
              "erDiagram\n    dim_customer ||--o{ orders : \"下訂單\"\n")
        write(self.path("erd", "tables", "orders.md"), "訂單頭事實表。\n")
        write(self.path("flows", "flow_one.md"),
              "flowchart LR\n  結帳服務 --> orders\n")
        cache = os.path.join(self.dir, "cache.json")
        before = config_check.run_check(self.dir, cache)
        self.assertTrue(before["problems"])            # 修之前是壞的
        self.run_format()
        after = config_check.run_check(self.dir, cache)
        self.assertEqual({}, after["problems"])        # 修之後全過


class T_N8_Knowhow(Base):
    def rule(self, zone: str, name: str, text: str) -> str:
        p = self.path("knowhow", zone, name)
        write(p, text)
        return p

    def test_missing_front_matter_filled_from_name_and_folder(self):
        p = self.rule("gating", "naming_column_case.md",
                      "# 欄位名須為 snake_case\n\n## 目的\n可讀性。\n\n"
                      "## 卡控\n\n```check\nrequire: name_matches column "
                      "^[a-z][a-z0-9_]*$\n```\n")
        self.run_format()
        text = read(p)
        self.assertTrue(text.startswith("---\n"))
        self.assertIn("id: naming_column_case", text)
        self.assertIn("category: naming", text)          # 依檔名慣例推導
        self.assertIn("enforcement: warning", text)      # gating 資料夾的預設
        self.assertIn("🤖 工具補上", text)
        # 補完之後真的載得進來（原本 category 缺 → compile 會中斷）
        from dataval.skills.markdown_skill import load_markdown_skill
        skill = load_markdown_skill(p)
        self.assertEqual("naming", skill.category)
        self.assertEqual("gating", skill.zone)

    def test_advisory_folder_gets_advisory_enforcement(self):
        p = self.rule("advisory", "ssot_semantic.md",
                      "---\nid: ssot_semantic\ncategory: ssot\n---\n\n"
                      "# SSOT 語意\n\n## 卡控\n\n```check-llm\n"
                      "檢視是否有多個權威擁有者。\n```\n")
        self.run_format()
        text = read(p)
        self.assertIn("enforcement: advisory", text)
        from dataval.skills.markdown_skill import load_markdown_skill
        self.assertEqual("advisory", load_markdown_skill(p).zone)

    def test_fence_label_typos_normalized(self):
        p = self.rule("gating", "structural_order_by.md",
                      "---\nid: structural_order_by\ncategory: structural\n"
                      "enforcement: blocking\n---\n\n# 需要 ORDER BY\n\n"
                      "```checks\nrequire: has_order_by\n```\n")
        self.run_format()
        text = read(p)
        self.assertIn("```check\n", text)
        self.assertNotIn("```checks", text)

    def test_unlabelled_control_block_gets_label(self):
        p = self.rule("gating", "bp_no_float.md",
                      "---\nid: bp_no_float\ncategory: best_practice\n"
                      "enforcement: warning\n---\n\n# 金額不得用 Float\n\n"
                      "```\nrequire: column_type amount Decimal\n```\n")
        self.run_format()
        self.assertIn("```check\nrequire: column_type", read(p))

    def test_other_language_fences_untouched(self):
        original = ("---\nid: ssot_join_keys\ncategory: ssot\n"
                    "enforcement: warning\n---\n\n# Join key\n\n"
                    "```sql\nSELECT 1;\n```\n\n```check\n"
                    "require: has_column order_id\n```\n")
        p = self.rule("gating", "ssot_join_keys.md", original)
        self.assertEqual([], self.run_format()["changed"])
        self.assertEqual(original, read(p))

    def test_uninferable_category_is_left_alone(self):
        # 檔名看不出類別 → 不猜 category（compile 會 fail-closed 報）
        p = self.rule("gating", "my_custom_thing.md",
                      "# 自訂規則\n\n```check\nrequire: has_order_by\n```\n")
        self.run_format()
        text = read(p)
        self.assertNotIn("category:", text)
        self.assertIn("enforcement: warning", text)      # 這個推得出來就補

    def test_declared_values_never_overwritten(self):
        original = ("---\nid: naming_pk_suffix\ncategory: structural\n"
                    "enforcement: blocking\n---\n\n# 主鍵字尾\n\n"
                    "```check\nrequire: has_primary_key\n```\n")
        p = self.rule("gating", "naming_pk_suffix.md", original)
        self.assertEqual([], self.run_format()["changed"])
        self.assertEqual(original, read(p))              # 已宣告的一字不改


if __name__ == "__main__":
    unittest.main()

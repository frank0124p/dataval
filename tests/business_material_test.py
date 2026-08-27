#!/usr/bin/env python3
"""業務素材萬用夾（config/<域>/business/）的守門測試。

守的保證：
  B1 什麼都收：任何 mermaid 圖種類（狀態機／時序圖／旅程…）與純文字都能
     被當成素材載入，認不出的圖種類也不影響載入
  B2 進得了兩個模式：design 素材索引列得出來、govern 顧問 prompt 帶得到
  B3 自動格式化：圖沒包 fence 就包（圖種類不限）、缺標題補檔名、
     副檔名（.mmd／.txt）改成 .md
  B4 檢查寬鬆：不因格式不合而報錯，只擋「空檔」與「fence 沒收尾」
  B5 front-matter 可調：index_summary／index_stage／index_required 生效
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import config_check, config_format, design            # noqa: E402
from dataval.advisory_export import build_advisory_prompt          # noqa: E402

STATE_MD = """---
index_summary: 訂單生命週期狀態機
---

# 訂單生命週期

取消不刪除資料，以 cancelled_at 記錄時間。

```mermaid
stateDiagram-v2
    [*] --> created
    created --> paid
    created --> cancelled
```
"""


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

    def biz(self, name: str, text: str, domain: str = "CRM") -> str:
        path = os.path.join(self.dir, domain, "business", name)
        write(path, text)
        return path


class T_B1_AnythingGoes(Base):
    def test_any_diagram_kind_is_summarised(self):
        cases = {
            "state.md": "stateDiagram-v2\n  [*] --> a",
            "seq.md": "sequenceDiagram\n  A->>B: pay",
            "journey.md": "journey\n  title 下單",
            "weird.md": "someFutureDiagram\n  x --> y",     # 認不出的種類
        }
        for name, body in cases.items():
            summary = design._business_summary(
                f"# t\n\n說明文字。\n\n```mermaid\n{body}\n```\n")
            self.assertIn("說明文字。", summary, name)
        self.assertIn("狀態機", design._business_summary(
            "```mermaid\nstateDiagram-v2\n  [*] --> a\n```"))
        self.assertIn("時序圖", design._business_summary(
            "```mermaid\nsequenceDiagram\n  A->>B: x\n```"))

    def test_plain_text_only_is_fine(self):
        self.assertIn("純文字的業務規則",
                      design._business_summary("# t\n\n純文字的業務規則。\n"))

    def test_multiple_diagrams_in_one_file(self):
        summary = design._business_summary(
            "```mermaid\nstateDiagram-v2\n a\n```\n\n"
            "```mermaid\nsequenceDiagram\n b\n```\n")
        self.assertIn("狀態機／時序圖", summary)


class T_B2_ReachesBothModes(Base):
    def test_listed_in_design_material_index(self):
        self.biz("order_lifecycle.md", STATE_MD)
        entries = design.design_index(self.dir, ["CRM"])
        biz = [e for e in entries if e["kind"] == "業務素材"]
        self.assertEqual(1, len(biz))
        self.assertEqual("config/CRM/business/order_lifecycle.md",
                         biz[0]["path"])
        self.assertEqual("訂單生命週期狀態機", biz[0]["summary"])
        self.assertEqual(["L", "P"], biz[0]["stage"])

    def test_common_business_reaches_every_domain(self):
        self.biz("company_rules.md", "# 公司通則\n\n全公司適用。\n",
                 domain="Common")
        entries = design.design_index(self.dir, ["SCM"])   # 完全不同的 domain
        self.assertEqual(1, len([e for e in entries
                                 if e["kind"] == "業務素材"]))

    def test_advisory_prompt_carries_the_index(self):
        self.biz("order_lifecycle.md", STATE_MD)

        class _Schema:
            tables = []

        text = build_advisory_prompt(
            _Schema(), "ctx", name="order",
            business_materials=design.business_materials(self.dir, ["CRM"]))
        self.assertIn("## 業務素材", text)
        self.assertIn("config/CRM/business/order_lifecycle.md", text)
        self.assertIn("訂單生命週期狀態機", text)

    def test_prompt_without_materials_is_explicit(self):
        class _Schema:
            tables = []

        text = build_advisory_prompt(_Schema(), "ctx", name="order")
        self.assertIn("沒有 business/ 素材", text)
        self.assertEqual("", design.business_materials(self.dir, ["CRM"]))


class T_B3_AutoFormat(Base):
    def test_unfenced_diagram_of_any_kind_gets_fenced(self):
        path = self.biz("flow.md", "說明。\n\nsequenceDiagram\n  A->>B: x\n")
        config_format.run_format(self.dir)
        text = read(path)
        self.assertIn("```mermaid\nsequenceDiagram", text)
        self.assertIn("# flow", text)              # 缺標題也補上
        self.assertIn("說明。", text)               # 內容一字未動

    def test_extension_renamed(self):
        write(os.path.join(self.dir, "CRM", "business", "state.mmd"),
              "```mermaid\nstateDiagram-v2\n  [*] --> a\n```\n")
        config_format.run_format(self.dir)
        self.assertTrue(os.path.isfile(
            os.path.join(self.dir, "CRM", "business", "state.md")))

    def test_idempotent(self):
        path = self.biz("ok.md", STATE_MD)
        self.assertEqual([], config_format.run_format(self.dir)["changed"])
        self.assertEqual(STATE_MD, read(path))


class T_B4_LenientCheck(Base):
    def _check(self):
        return config_check.run_check(self.dir,
                                      os.path.join(self.dir, "cache.json"))

    def test_free_form_content_passes(self):
        self.biz("anything.md", "# 隨便寫\n\n沒有圖、沒有表格，就是一段話。\n")
        self.assertEqual({}, self._check()["problems"])

    def test_empty_file_is_reported(self):
        self.biz("empty.md", "\n")
        problems = self._check()["problems"]
        self.assertIn("CRM/business/empty.md", problems)
        self.assertIn("內容是空的", problems["CRM/business/empty.md"][0])

    def test_unclosed_fence_is_reported(self):
        self.biz("broken.md", "# t\n\n```mermaid\nstateDiagram-v2\n")
        problems = self._check()["problems"]["CRM/business/broken.md"]
        self.assertIn("fence 沒有成對收尾", problems[0])

    def test_non_md_extension_is_flagged_not_silently_ignored(self):
        write(os.path.join(self.dir, "CRM", "business", "notes.pdf"), "x")
        problems = self._check()["problems"]
        self.assertIn("CRM/business/notes.pdf", problems)


class T_B5_FrontMatter(Base):
    def test_stage_and_required_override(self):
        self.biz("must_read.md",
                 "---\nindex_summary: 一定要看\nindex_stage: [L]\n"
                 "index_required: true\n---\n\n# 規則\n\n內容。\n")
        entry = [e for e in design.design_index(self.dir, ["CRM"])
                 if e["kind"] == "業務素材"][0]
        self.assertEqual("一定要看", entry["summary"])
        self.assertEqual(["L"], entry["stage"])
        self.assertTrue(entry["required"])
        self.assertFalse(entry["auto_summary"])

    def test_auto_summary_when_front_matter_absent(self):
        self.biz("no_fm.md", "# 標題\n\n這段會變成自動摘要。\n")
        entry = [e for e in design.design_index(self.dir, ["CRM"])
                 if e["kind"] == "業務素材"][0]
        self.assertTrue(entry["auto_summary"])
        self.assertIn("這段會變成自動摘要。", entry["summary"])
        self.assertFalse(entry["required"])       # 預設不強制必讀


if __name__ == "__main__":
    unittest.main()

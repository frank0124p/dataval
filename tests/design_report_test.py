#!/usr/bin/env python3
"""設計 HTML 報告（design_report.py）的守門測試。

守的保證：
  R1 與 govern 報告區隔：設計報告有自己的抬頭與模式對照，
     不用治理報告的標題；不做合規判定（預檢僅供參考）
  R2 階段分區：Logical（六節＋Column Mapping）／Physical（DDL 世界）
     兩個階段各自成區、清楚分開
  R3 素材足跡：全貌都畫（①緊湊層→②必讀→③L→④P）；
     narrative.references 宣告過的檔案標亮（●＋路徑連結），
     沒讀的照樣列出（○）；必讀未宣告 → ⚠️ 提醒；分支附已讀統計
  R4 內容確定性：同輸入重產位元組相同（無時間戳）
  R5 設計問答狀態：proposed／answered（含答案）呈現
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import design, design_report                       # noqa: E402
from tests.design_test import RESULT                            # noqa: E402

ENTRIES = [
    {"kind": "參考 ER 模型", "path": "config/CRM/erd/crm_core.md",
     "summary": "實體：dim_customer、orders", "auto_summary": True,
     "stage": ["L"], "required": False},
    {"kind": "SSOT 權威登錄", "path": "config/CRM/ssot/registry.yaml",
     "summary": "（空登錄）", "auto_summary": True,
     "stage": ["L", "P"], "required": True},
    {"kind": "詞彙字典", "path": "config/CRM/naming/glossary.md",
     "summary": "禁用 0、別名 0", "auto_summary": True,
     "stage": ["P"], "required": False},
]

PREVIEW = {"compliant": False, "fail": 1, "warning": 0,
           "blocked": ["NAMING.GLOSSARY"], "warned": [],
           "origins": {"NAMING.GLOSSARY":
                       "config/Common/naming/glossary.md"}}


def render(**kw):
    args = dict(state="首稿", gate_preview=PREVIEW, answers=None,
                entries=ENTRIES, product=None, domains=["CRM"],
                ddl_diff="", files=["發票.design_story.md",
                                    "發票.logical_design.md"])
    args.update(kw)
    return design_report.to_html("發票", 1, RESULT, **args)


class T_R1_DistinctFromGovern(unittest.TestCase):
    def test_design_identity_not_govern(self):
        html = render()
        self.assertIn("🎨 設計報告（design mode） — 發票", html)
        self.assertIn("第 1 輪設計（首稿）", html)
        self.assertIn("🛡 治理報告是另一份", html)          # 模式對照
        self.assertIn("發票.report.html", html)             # 指向 govern 入口
        self.assertNotIn("資料設計驗證報告", html)          # 不冒用 govern 標題
        self.assertNotIn("判定：合規", html)                # 不做合規判定
        self.assertIn("❌ 預檢不合規", html)                # 預檢僅供參考
        self.assertIn("../config/Common/naming/glossary.md", html)  # 依據連結

    def test_no_javascript(self):
        # 設計報告刻意無 JS（純 <details>），也是與 govern 報告的區隔之一
        self.assertNotIn("<script>", render())


class T_R2_StageSeparation(unittest.TestCase):
    def test_logical_physical_sections(self):
        html = render()
        self.assertIn('class="blk stage-l"', html)
        self.assertIn('class="blk stage-p"', html)
        self.assertIn("🧠 Logical 階段", html)
        self.assertIn("🏗 Physical 階段", html)
        for head in ("1. Business Context", "2. Domain Boundary",
                     "3. Entity Overview", "4. Entity Detail",
                     "5. Metric Contracts", "6. Cross Domain Dependency",
                     "7. Column Mapping"):
            self.assertIn(head, html)
        self.assertIn("表間關係（Relations）", html)
        self.assertIn("Key 設計", html)
        self.assertIn("閘門預檢", html)
        # 欄位改名在 Column Mapping 詳實交代
        self.assertIn("✏️ 改名", html)


class T_R3_Footprint(unittest.TestCase):
    def test_full_map_with_visited_path(self):
        html = render()
        # 全貌：四層分支都在
        self.assertIn("① 內嵌緊湊層", html)
        self.assertIn("② 必讀 ✅", html)
        self.assertIn("③ logical 起草才開（L）", html)
        self.assertIn("④ physical 落地才開（P）", html)
        # 已讀（RESULT 的 narrative.references 宣告了 crm_core）→ 標亮＋連結
        self.assertIn('href="../config/CRM/erd/crm_core.md"', html)
        self.assertIn("已讀 1／1", html)                    # L 分支統計
        # 未讀的照樣列出（全貌），但不標亮
        self.assertIn('href="../config/CRM/naming/glossary.md"', html)
        self.assertIn("已讀 0／1", html)                    # P 分支統計
        # 必讀（ssot）未見於出處宣告 → ⚠️ 提醒
        self.assertIn("⚠️ 必讀未見於出處宣告", html)
        self.assertIn("彩色連線＝實際走過的路徑", html)

    def test_visited_marks(self):
        # 足跡區內（crm_core 也會出現在敘事的設計出處，須從足跡區找起）
        html = render()
        fp = html[html.find('class="mm-root"'):]
        on_pos = fp.find('href="../config/CRM/erd/crm_core.md"')
        li_start = fp.rfind("<li", 0, on_pos)
        self.assertIn('class="on"', fp[li_start:on_pos])     # 已讀 → on
        off_pos = fp.find('href="../config/CRM/naming/glossary.md"')
        li_start = fp.rfind("<li", 0, off_pos)
        self.assertIn('class="off"', fp[li_start:off_pos])   # 未讀 → off


class T_R4_Determinism(unittest.TestCase):
    def test_byte_stable(self):
        self.assertEqual(render(), render())


class T_R5_QaStates(unittest.TestCase):
    def test_proposed_and_answered(self):
        q_text = design.question_text(RESULT["open_questions"][0]).strip()
        answers = {"answers": [{"id": design.question_id(q_text),
                                "status": "answered",
                                "answer": "重開沿用新號"}]}
        html = render(answers=answers)
        self.assertIn("✅ 已答", html)
        self.assertIn("重開沿用新號", html)
        self.assertIn("⏳ 待驗證", html)      # 第二題仍是 proposed
        self.assertIn("design_answers.yaml", html)


if __name__ == "__main__":
    unittest.main()

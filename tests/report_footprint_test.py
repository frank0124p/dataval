#!/usr/bin/env python3
"""治理報告素材足跡（report._footprint_html）的守門測試。

守的保證：
  F1 全貌照畫：素材＋閘門規則＋顧問規則分支都在，含統計
  F2 走過判定：實檢過（fail／warning／pass）的規則 ●；其依據路徑
     命中的素材 ●（含 naming 字典資料夾前綴比對）；未實檢 ○
  F3 顧問規則：未補完 ⏳（○）、已補完 💡（●）
  F4 報告整體：新抬頭（🛡 治理報告）＋模式對照卡＋足跡卡出現在 to_html
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval.model import Finding, ZONE_ADVISORY, ZONE_GATING   # noqa: E402
from dataval import report                                      # noqa: E402

META = {
    "domains_loaded": ["Common", "CRM"],
    "tables": 2,
    "checking_rule_ids_loaded": ["SKILL.naming_glossary",
                                 "SKILL.pk_required", "SKILL.tips"],
    "material_index": [
        {"kind": "參考 ER 模型", "path": "config/CRM/erd/crm_core.md",
         "summary": "實體：dim_customer、orders", "auto_summary": True,
         "stage": ["L"], "required": False},
        {"kind": "詞彙字典", "path": "config/CRM/naming/glossary.md",
         "summary": "禁用 0、別名 0", "auto_summary": True,
         "stage": ["P"], "required": False},
        {"kind": "E2E 業務流程", "path": "config/CRM/flows/order_to_revenue.md",
         "summary": "訂單到營收", "auto_summary": True,
         "stage": ["L"], "required": False},
    ],
    "rule_coverage": {"loaded": [
        {"id": "SKILL.naming_glossary", "domain": "Common", "zone": "gating",
         "file": "Common/knowhow/gating/naming_glossary.md"},
        {"id": "SKILL.pk_required", "domain": "Common", "zone": "gating",
         "file": "Common/knowhow/gating/pk_required.md"},
        {"id": "SKILL.tips", "domain": "Common", "zone": "advisory",
         "file": "Common/knowhow/advisory/tips.md"},
    ]},
}

FINDINGS = [
    # naming 實檢（fail）→ 規則●；依據含 config/CRM/naming/ → 字典素材●
    Finding(check_id="SKILL.naming_glossary", category="naming",
            status="fail", target="orders.cust_nm", message="縮寫違規",
            zone=ZONE_GATING),
    # pk_required 本次無 finding → not_checked ○（靠 loaded_rule_ids 補列）
    # 顧問規則尚未補完（skipped）→ ⏳ ○
    Finding(check_id="SKILL.tips", category="best_practice",
            status="skipped", target="-", message="待 LLM 補完",
            zone=ZONE_ADVISORY),
]


class T_F1_FullMap(unittest.TestCase):
    def test_branches_and_counts(self):
        html = report._footprint_html(FINDINGS, META)
        self.assertIn("素材足跡", html)
        self.assertIn("網域知識素材", html)
        self.assertIn("用到 1／3", html)               # 只有字典被走到
        self.assertIn("閘門規則（knowhow gating）", html)
        self.assertIn("實檢 1／2", html)
        self.assertIn("顧問規則（knowhow advisory）", html)
        self.assertIn("已補完 0／1", html)
        self.assertIn("domains：Common、CRM", html)


class T_F2_WalkedDetection(unittest.TestCase):
    def test_material_and_rule_marks(self):
        html = report._footprint_html(FINDINGS, META)
        # naming 規則實檢 → ●＋規則檔連結
        pos = html.find("SKILL.naming_glossary")
        li = html.rfind("<li", 0, pos)
        self.assertIn('class="on"', html[li:pos])
        self.assertIn('href="../../config/Common/knowhow/gating/'
                      'naming_glossary.md"', html)
        # 字典素材：依據的 config/CRM/naming/ 前綴命中 → ●
        pos = html.find("config/CRM/naming/glossary.md")
        li = html.rfind("<li", 0, pos)
        self.assertIn('class="on"', html[li:pos])
        # 流程素材沒被任何實檢用到 → ○
        pos = html.find("config/CRM/flows/order_to_revenue.md")
        li = html.rfind("<li", 0, pos)
        self.assertIn('class="off"', html[li:pos])
        # 未實檢規則 ⏭️ ○
        pos = html.find("SKILL.pk_required")
        li = html.rfind("<li", 0, pos)
        self.assertIn('class="off"', html[li:pos])
        self.assertIn("⏭️", html)

    def test_advisory_done_lights_up(self):
        done = [f for f in FINDINGS if f.zone != ZONE_ADVISORY] + [
            Finding(check_id="SKILL.tips", category="best_practice",
                    status="info", target="orders", message="建議",
                    zone=ZONE_ADVISORY)]
        html = report._footprint_html(done, META)
        self.assertIn("已補完 1／1", html)
        self.assertIn("💡", html)

    def test_advisory_merged_counts_no_finding_rules(self):
        # merge_advisory 後（advisory_merged）：LLM 判無問題的顧問規則
        # 不留 findings，也必須算已補完（不能永遠 ⏳）
        gating_only = [f for f in FINDINGS if f.zone != ZONE_ADVISORY]
        meta = dict(META, advisory_merged=True)
        html = report._footprint_html(gating_only, meta)
        self.assertIn("已補完 1／1", html)
        self.assertIn("💡", html)
        self.assertNotIn("⏳", html)


class T_F4_GovernReportIntegration(unittest.TestCase):
    def test_to_html_has_new_head_and_footprint(self):
        html = report.to_html(FINDINGS, META)
        self.assertIn("🛡 治理報告（govern mode）", html)
        self.assertIn("🎨 設計報告是另一份", html)      # 模式對照
        self.assertIn("素材足跡", html)
        self.assertIn('class="mm"', html)
        # 既有功能不動：篩選、涵蓋清單入口、JS 仍在
        self.assertIn("filterRule", html)
        self.assertIn("applyFilters", html)


if __name__ == "__main__":
    unittest.main()

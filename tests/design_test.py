#!/usr/bin/env python3
"""設計模式（design mode）的守門測試。

守的保證：
  D1 模式判定：只有 context.md → design；有 <名>.sql → govern（互斥）
  D2 prompt 組裝：含 context 全文、設計約束（閘門規則）、參考模型素材
  D3 result 驗證：缺件／型別錯誤會被擋，合法結構通過
  D4 渲染與輪次：三份產物落地；內容不變同輪重渲染位元組穩定；
     內容變了輪次 +1、記 DDL 演進 diff 與 HISTORY
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import design


CONTEXT = """---
subject: 發票
domains: [CRM]
business_keys:
  invoice: [invoice_id]
---
## 這個 data subject 是什麼
發票資料。
## 粒度（每張表一行代表什麼）
invoice 一行 = 一張發票。
## 用途與消費者
對帳。
## 上下游來源
開票服務。
"""

RESULT = {
    "logical_design": {
        "business_context": "發票支撐對帳與稅務申報。",
        "domain_boundary": {
            "statement": "本主體只管發票開立與作廢，不管收款。",
            "owns": ["發票金額"],
            "references": [{"entity": "customer", "authority": "CRM.dim_customer",
                            "note": "只存鍵"}],
        },
        "entities": [{"name": "invoice", "kind": "fact", "description": "發票",
                      "grain": "一行=一張發票",
                      "attributes": [{"name": "invoice_id",
                                      "description": "發票號",
                                      "business_key": True}]}],
        "relationships": [{"from": "invoice", "to": "customer",
                           "cardinality": "N:1", "description": "開給客戶"}],
        "metric_contracts": [{"name": "開票金額", "definition": "含稅總額加總",
                              "grain": "日", "source": "invoice.total_amount",
                              "caveats": "作廢發票排除"}],
        "cross_domain_dependencies": [
            {"domain": "CRM", "entity": "dim_customer",
             "direction": "upstream", "via": "customer_id",
             "description": "客戶主檔權威在 CRM"}],
    },
    "physical_design": {
        "overview": "單表 MergeTree。",
        "tables": [{"name": "invoice", "engine": "MergeTree()",
                    "order_by": "(invoice_id)", "partition_by": "",
                    "comment": "發票表",
                    "columns": [{"name": "invoice_id", "type": "UInt64",
                                 "nullable": False, "comment": "發票號"}]}],
        "notes": ["金額用 Decimal"],
    },
    "draft_ddl": ("CREATE TABLE invoice (invoice_id UInt64 COMMENT '發票號') "
                  "ENGINE = MergeTree() ORDER BY (invoice_id);"),
    "open_questions": ["發票是否會作廢重開？"],
}


def write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class T_D1_ModeDetection(unittest.TestCase):
    def test_context_only_is_design_ddl_is_govern(self):
        root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, root)
        write(os.path.join(root, "invoice", "context.md"), CONTEXT)      # design
        write(os.path.join(root, "order", "context.md"), CONTEXT)
        write(os.path.join(root, "order", "order.sql"), "CREATE ...")    # govern
        write(os.path.join(root, "empty", "note.txt"), "x")              # 都不是
        subjects = design.find_design_subjects(root)
        self.assertEqual([("invoice", os.path.join(root, "invoice"))], subjects)


class T_D2_Prompt(unittest.TestCase):
    def test_prompt_contains_context_constraints_and_refs(self):
        compiled = os.path.join(ROOT, "build", "compiled_rules.json")
        text = design.build_design_prompt(
            "invoice", CONTEXT, os.path.join(ROOT, "config"), compiled)
        self.assertIn("design mode — invoice", text)
        self.assertIn("發票資料。", text)                       # context 全文
        self.assertIn("design_result.json", text)
        self.assertIn("設計約束", text)
        self.assertIn("structural_order_by", text)              # 閘門規則入列
        self.assertIn("參考模型素材", text)
        self.assertIn("CRM/flows/order_to_revenue.md", text)    # E2E 流程入列
        self.assertIn("CRM/ssot/registry.yaml", text)           # SSOT 權威入列
        self.assertIn("agent 不得代寫權威輸入", text)


class T_D3_ResultValidation(unittest.TestCase):
    def test_valid_result_passes(self):
        self.assertEqual([], design.validate_design_result(RESULT))

    def test_missing_and_broken_fields_fail(self):
        self.assertTrue(design.validate_design_result("not a dict"))
        bad = copy.deepcopy(RESULT)
        del bad["draft_ddl"]
        self.assertTrue(any("draft_ddl" in e or "缺少" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["logical_design"]["entities"] = []
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        del bad["logical_design"]["business_context"]
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["logical_design"]["domain_boundary"] = {"statement": ""}
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["logical_design"]["metric_contracts"] = [{"name": "x"}]
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["logical_design"]["cross_domain_dependencies"] = [{"domain": "CRM"}]
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][0]["name"] = ""
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["open_questions"] = [1]
        self.assertTrue(design.validate_design_result(bad))


class T_D4_RenderAndRounds(unittest.TestCase):
    def setUp(self):
        self.hist = tempfile.mkdtemp()
        self.rep = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.hist)
        self.addCleanup(shutil.rmtree, self.rep)

    def test_render_outputs_and_round_evolution(self):
        preview = {"compliant": True, "fail": 0, "warning": 1, "blocked": []}
        info = design.render("invoice", RESULT, CONTEXT, self.hist, self.rep,
                             gate_preview=preview)
        self.assertEqual(1, info["round"])
        self.assertTrue(info["first"])
        logical = open(os.path.join(self.rep, "invoice.logical_design.md"),
                       encoding="utf-8").read()
        self.assertIn("第 1 輪設計", logical)
        self.assertIn("invoice_id", logical)
        self.assertIn("發票是否會作廢重開？", logical)
        # 六節結構齊全
        self.assertIn("## 1. Business Context", logical)
        self.assertIn("## 2. Domain Boundary", logical)
        self.assertIn("## 3. Entity Overview", logical)
        self.assertIn("## 4. Entity Detail", logical)
        self.assertIn("## 5. Metric Contracts", logical)
        self.assertIn("## 6. Cross Domain Dependency", logical)
        self.assertIn("開票金額", logical)                      # 指標契約
        self.assertIn("CRM.dim_customer", logical)             # 領域邊界引用
        self.assertIn("upstream", logical)                     # 跨域依賴方向
        physical = open(os.path.join(self.rep, "invoice.physical_design.md"),
                        encoding="utf-8").read()
        self.assertIn("✅ 預檢合規", physical)
        self.assertIn("MergeTree()", physical)
        sql = open(os.path.join(self.rep, "invoice.design.sql"),
                   encoding="utf-8").read()
        self.assertIn("第 1 輪設計 DDL", sql)
        self.assertIn("CREATE TABLE invoice", sql)
        self.assertIn("進入 govern mode", sql)

        # 同輪重渲染：內容不變 → 輪次不動、檔案位元組穩定
        before = open(os.path.join(self.rep, "invoice.design.sql"),
                      encoding="utf-8").read()
        info2 = design.render("invoice", RESULT, CONTEXT, self.hist, self.rep,
                              gate_preview=preview)
        self.assertEqual(1, info2["round"])
        self.assertFalse(info2["changed"])
        after = open(os.path.join(self.rep, "invoice.design.sql"),
                     encoding="utf-8").read()
        self.assertEqual(before, after)

        # 設計演進：draft_ddl 變了 → 第 2 輪＋diff＋HISTORY
        evolved = copy.deepcopy(RESULT)
        evolved["draft_ddl"] = RESULT["draft_ddl"].replace(
            "invoice_id UInt64 COMMENT '發票號'",
            "invoice_id UInt64 COMMENT '發票號', amount Decimal(18,2) "
            "COMMENT '金額'")
        info3 = design.render("invoice", evolved, CONTEXT, self.hist, self.rep,
                              gate_preview=preview)
        self.assertEqual(2, info3["round"])
        self.assertTrue(info3["changed"])
        self.assertIn("amount", info3["ddl_diff"])
        physical2 = open(os.path.join(self.rep, "invoice.physical_design.md"),
                         encoding="utf-8").read()
        self.assertIn("與上一輪設計的 DDL 演進", physical2)
        history = open(os.path.join(self.hist, "invoice", "design",
                                    "HISTORY.md"), encoding="utf-8").read()
        self.assertIn("第 1 輪設計", history)
        self.assertIn("第 2 輪設計", history)
        self.assertIn("DDL 已演進", history)


if __name__ == "__main__":
    unittest.main()

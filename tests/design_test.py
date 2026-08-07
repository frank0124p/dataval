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
        "overview": "積木化：base 發票表＋wide 彙總寬表。",
        "tables": [
            {"name": "invoice", "layer": "base", "engine": "MergeTree()",
             "order_by": "(invoice_id)", "partition_by": "",
             "comment": "發票表",
             "columns": [{"name": "invoice_id", "type": "UInt64",
                          "nullable": False, "comment": "發票號"},
                         {"name": "customer_id", "type": "UInt64",
                          "nullable": False, "comment": "客戶",
                          "source": "CRM.dim_customer.customer_id"}],
             "ddl": ("CREATE TABLE invoice (invoice_id UInt64 COMMENT '發票號',"
                     " customer_id UInt64 COMMENT '客戶') "
                     "ENGINE = MergeTree() ORDER BY (invoice_id);"),
             "keys": {"business_key": ["invoice_id"],
                      "description": "發票號由開票服務保證唯一；排序鍵＝業務鍵，"
                                     "無去重需求",
                      "join_keys": [{"column": "customer_id",
                                     "references": "CRM.dim_customer.customer_id",
                                     "note": "客戶權威在 CRM"}]},
             "design_decisions": [
                 {"decision": "ORDER BY (invoice_id)",
                  "rationale": "以 business key 排序，點查發票最常見"}]},
            {"name": "invoice_wide", "layer": "wide", "engine": "MergeTree()",
             "order_by": "(invoice_id)", "partition_by": "",
             "comment": "發票寬表",
             "columns": [{"name": "invoice_id", "type": "UInt64",
                          "nullable": False, "comment": "發票號",
                          "source": "invoice.invoice_id"}],
             "ddl": ("CREATE TABLE invoice_wide (invoice_id UInt64 "
                     "COMMENT '發票號') ENGINE = MergeTree() "
                     "ORDER BY (invoice_id);"),
             "keys": {"business_key": ["invoice_id"],
                      "description": "與 invoice 1:1，唯一性繼承來源表"},
             "design_decisions": [
                 {"decision": "寬表獨立成檔",
                  "rationale": "彙總消費與明細分離，下游只讀寬表"}]},
        ],
        "table_relations": [
            {"from": "invoice_wide.invoice_id", "to": "invoice.invoice_id",
             "cardinality": "1:1", "kind": "reference", "note": "寬表對回發票"}],
        "notes": ["金額用 Decimal"],
    },
    "open_questions": [
        {"question": "發票是否會作廢重開？",
         "proposed_answer": "作廢後重開沿用新發票號，原號保留作廢紀錄。"},
        "折讓要不要獨立主體？",   # 純字串相容形
    ],
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
        for t in bad["physical_design"]["tables"]:
            t.pop("ddl", None)                      # 無逐表 ddl、無 draft_ddl
        self.assertTrue(any("設計 DDL 不可為空" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][0]["layer"] = "mega"
        self.assertTrue(any("layer" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["table_relations"] = [{"from": "a.x"}]
        self.assertTrue(any("table_relations" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        del bad["physical_design"]["tables"][0]["keys"]
        self.assertTrue(any("keys" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][0]["keys"]["business_key"] = ["nope"]
        self.assertTrue(any("不存在於 columns" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][0]["keys"]["description"] = ""
        self.assertTrue(any("description" in e
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
        del bad["physical_design"]["tables"][0]["design_decisions"]
        self.assertTrue(any("design_decisions" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][0]["design_decisions"] = [
            {"decision": "x", "rationale": ""}]
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["open_questions"] = [1]
        self.assertTrue(design.validate_design_result(bad))
        bad = copy.deepcopy(RESULT)
        bad["open_questions"] = [{"proposed_answer": "沒有題目"}]
        self.assertTrue(design.validate_design_result(bad))


class T_D5_QaLoop(unittest.TestCase):
    """設計問答迴圈：代填 → 驗證 → 下一輪帶入。"""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.path = os.path.join(self.dir, "design_answers.yaml")

    def test_merge_adds_proposed_only_once_and_keeps_existing(self):
        data, problems = design.load_design_answers(self.path)   # 檔案不存在
        self.assertEqual([], problems)
        data, added = design.merge_design_answers(
            data, RESULT["open_questions"])
        self.assertEqual(2, added)
        self.assertTrue(all(e["status"] == "proposed" for e in data["answers"]))
        self.assertEqual("作廢後重開沿用新發票號，原號保留作廢紀錄。",
                         data["answers"][0]["answer"])   # 代填答案入檔
        # 使用者驗證後重跑：同題不重複代填、既有條目不被覆寫
        data["answers"][0]["status"] = "answered"
        data["answers"][0]["answer"] = "沿用原號。"       # 使用者修改答案
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(design.answers_to_yaml(data, "invoice"))
        data2, problems = design.load_design_answers(self.path)
        self.assertEqual([], problems)
        data2, added2 = design.merge_design_answers(
            data2, RESULT["open_questions"])
        self.assertEqual(0, added2)
        self.assertEqual("沿用原號。", data2["answers"][0]["answer"])
        state = design.qa_state(data2)
        self.assertEqual(1, len(state["answered"]))
        self.assertEqual(1, len(state["proposed"]))

    def test_answered_fed_into_prompt_proposed_not(self):
        data = {"version": 1, "answers": [
            {"id": "dq-1", "question": "已答的題", "answer": "答案A",
             "status": "answered"},
            {"id": "dq-2", "question": "待驗證的題", "answer": "代填B",
             "status": "proposed"},
            {"id": "dq-3", "question": "擱置的題", "answer": "",
             "status": "deferred"},
        ]}
        compiled = os.path.join(ROOT, "build", "compiled_rules.json")
        text = design.build_design_prompt(
            "invoice", CONTEXT, os.path.join(ROOT, "config"), compiled,
            answers=data)
        self.assertIn("已答的題", text)
        self.assertIn("答案A", text)
        self.assertIn("擱置的題", text)
        self.assertNotIn("待驗證的題", text)   # proposed 不餵，避免迴聲
        self.assertNotIn("代填B", text)

    def test_broken_answers_file_reports_problem(self):
        with open(self.path, "w", encoding="utf-8") as f:
            f.write("answers: {not: [a, list}\n")
        _, problems = design.load_design_answers(self.path)
        self.assertTrue(problems)


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
        # 兩節結構＋逐表設計決策與理由
        self.assertIn("## 1. Entity Overview", physical)
        self.assertIn("## 2. Entity Detail", physical)
        self.assertIn("**設計決策與理由**", physical)
        self.assertIn("ORDER BY (invoice_id)", physical)
        self.assertIn("以 business key 排序", physical)
        sql = open(os.path.join(self.rep, "invoice.design.sql"),
                   encoding="utf-8").read()
        self.assertIn("第 1 輪設計 DDL", sql)
        self.assertIn("CREATE TABLE invoice", sql)
        self.assertIn("CREATE TABLE invoice_wide", sql)   # 合併版含全部積木
        self.assertIn("進入 govern mode", sql)
        # 血緣：來源欄＋確定性反推的去向
        self.assertIn("來源（從何處來）", physical)
        self.assertIn("CRM.dim_customer.customer_id", physical)
        self.assertIn("`invoice.invoice_id` → `invoice_wide.invoice_id`",
                      physical)
        # 積木層級與表間關係
        self.assertIn("小積木（base）", physical)
        self.assertIn("寬表（wide）", physical)
        self.assertIn("表間關係（Relations）", physical)
        self.assertIn("寬表對回發票", physical)
        # Key 設計：BK 進總覽與明細、語意與 join key 描述齊備
        self.assertIn("**Key 設計**", physical)
        self.assertIn("Business Key（一行的身分）", physical)
        self.assertIn("發票號由開票服務保證唯一", physical)
        self.assertIn("`customer_id` → `CRM.dim_customer.customer_id`",
                      physical)
        self.assertIn("排序鍵非唯一約束", physical.replace(
            "ClickHouse 排序鍵非唯一約束", "排序鍵非唯一約束"))

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

        # 設計演進：某張積木的 ddl 變了 → 第 2 輪＋diff＋HISTORY
        evolved = copy.deepcopy(RESULT)
        evolved["physical_design"]["tables"][0]["ddl"] = \
            evolved["physical_design"]["tables"][0]["ddl"].replace(
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

    def test_ddl_split_files_and_relations_draft(self):
        """逐表 DDL 拆檔＋relations 草稿；表移除後 stale 檔會清掉。"""
        info = design.render("invoice", RESULT, CONTEXT, self.hist, self.rep)
        self.assertEqual(2, info["ddl_files"])
        ddl_dir = os.path.join(self.rep, "invoice.design")
        self.assertEqual(["invoice.ddl", "invoice_wide.ddl"],
                         sorted(os.listdir(ddl_dir)))
        base = open(os.path.join(ddl_dir, "invoice.ddl"),
                    encoding="utf-8").read()
        self.assertIn("第 1 輪設計 DDL — invoice/invoice", base)
        self.assertIn("小積木（base）", base)
        self.assertIn("CREATE TABLE invoice", base)
        self.assertNotIn("CREATE TABLE invoice_wide", base)   # 一表一檔
        rel = open(os.path.join(self.rep, "invoice.design.relations.yaml"),
                   encoding="utf-8").read()
        self.assertIn("from: invoice_wide.invoice_id", rel)
        self.assertIn("cardinality: '1:1'", rel)
        # 拿掉寬表 → stale 拆檔清掉、relations 草稿移除
        shrunk = copy.deepcopy(RESULT)
        shrunk["physical_design"]["tables"] = \
            shrunk["physical_design"]["tables"][:1]
        shrunk["physical_design"]["table_relations"] = []
        design.render("invoice", shrunk, CONTEXT, self.hist, self.rep)
        self.assertEqual(["invoice.ddl"], sorted(os.listdir(ddl_dir)))
        self.assertFalse(os.path.isfile(
            os.path.join(self.rep, "invoice.design.relations.yaml")))

    def test_gate_preview_traces_to_config(self):
        """設計預檢的被卡／警告規則附依據，config 路徑轉可點連結。"""
        preview = {"compliant": False, "fail": 2, "warning": 1,
                   "blocked": ["SKILL.bp_no_float"],
                   "warned": ["SKILL.naming_glossary"],
                   "origins": {
                       "SKILL.bp_no_float":
                           "config/Common/knowhow/gating/bp_no_float.md",
                       "SKILL.naming_glossary":
                           "config/Common/knowhow/gating/naming_glossary.md"
                           "（詞彙字典：config/Common/naming/）"}}
        design.render("invoice", RESULT, CONTEXT, self.hist, self.rep,
                      gate_preview=preview)
        physical = open(os.path.join(self.rep, "invoice.physical_design.md"),
                        encoding="utf-8").read()
        self.assertIn("❌ 預檢不合規", physical)
        self.assertIn("- ❌ `SKILL.bp_no_float` — 依據：[config/Common/knowhow/"
                      "gating/bp_no_float.md](../config/Common/knowhow/gating/"
                      "bp_no_float.md)", physical)
        self.assertIn("- ⚠️ `SKILL.naming_glossary`", physical)
        self.assertIn("(../config/Common/naming/)", physical)   # 字典也可點

    def test_single_draft_ddl_compat(self):
        """相容：只有整體 draft_ddl（無逐表 ddl）→ 單檔模式、不拆檔。"""
        legacy = copy.deepcopy(RESULT)
        for t in legacy["physical_design"]["tables"]:
            t.pop("ddl", None)
        legacy["draft_ddl"] = ("CREATE TABLE invoice (invoice_id UInt64 "
                               "COMMENT 'x') ENGINE = MergeTree() "
                               "ORDER BY (invoice_id);")
        self.assertEqual([], design.validate_design_result(legacy))
        self.assertEqual(legacy["draft_ddl"], design.combined_ddl(legacy))
        info = design.render("invoice", legacy, CONTEXT, self.hist, self.rep)
        self.assertEqual(0, info["ddl_files"])


if __name__ == "__main__":
    unittest.main()

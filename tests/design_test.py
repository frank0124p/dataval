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
                          "source": "invoice.invoice_id"},
                         {"name": "buyer_id", "type": "UInt64",
                          "nullable": False, "comment": "買方（改名示意）",
                          "source": "invoice.customer_id"}],
             "ddl": ("CREATE TABLE invoice_wide (invoice_id UInt64 "
                     "COMMENT '發票號', buyer_id UInt64 COMMENT '買方') "
                     "ENGINE = MergeTree() ORDER BY (invoice_id);"),
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
    "narrative": {
        "tldr": "發票拆成 base 事實表＋日彙總寬表，對帳看明細、日報看寬表。",
        "why": "財務對帳與稅務申報需要可追溯的發票事實。",
        "how_design_thinks": "明細與彙總分層，下游各取所需。",
        "tradeoffs": [{"chose": "寬表獨立成表", "instead_of": "視圖即時算",
                       "because": "日報查詢頻繁，預算換讀取效能"}],
        "how_to_use": [{"scenario": "算某天開票金額",
                        "guidance": "直接查 invoice_wide，勿掃明細表"}],
        "pitfalls": ["別把作廢發票算進營收"],
        "lessons": ["彙總與明細分層是可複用的積木 pattern"],
        "references": [{"source": "config/CRM/erd/crm_core.md",
                        "how": "customer 實體與引用關係對齊此參考模型"}],
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
        self.assertIn("目的：", text)                            # 閘門附目的
        # 命名決策順序：字典標準詞 → 全碼全稱 → Common 命名規則
        self.assertIn("命名決策順序", text)
        self.assertIn("全碼", text)
        self.assertIn("不得自創縮寫", text)
        self.assertIn("提議把新詞登錄進字典", text)
        # 顧問區 know-how 入列（含語意描述）
        self.assertIn("設計 know-how（顧問區語意準則", text)
        self.assertIn("best_practice_semantic", text)
        self.assertIn("naming_semantic", text)
        self.assertIn("參考模型素材", text)
        self.assertIn("CRM/flows/order_to_revenue.md", text)    # E2E 流程入列
        self.assertIn("CRM/ssot/registry.yaml", text)           # SSOT 權威入列
        # 效能與正確性：字典合併只呈現一次（不逐檔重複）、
        # 顧問規則全文不重複 inline（只在緊湊 know-how 章節出現一次）
        self.assertEqual(1, text.count("詞彙字典（Common＋宣告域合併後"))
        self.assertIn("`cust`→`customer`", text)                # 合併後詞條正確
        self.assertEqual(1, text.count("依表型態的最佳實踐建議"))
        # 預設索引模式：目錄＋按需開檔、SSOT 標必讀
        self.assertIn("參考模型素材索引", text)
        self.assertIn("按需開檔，勿一次全讀", text)
        self.assertIn("✅ 必讀", text)
        # full 模式回退：素材全文 inline（ER 取 mermaid fence）
        compiled = os.path.join(ROOT, "build", "compiled_rules.json")
        full = design.build_design_prompt(
            "invoice", CONTEXT, os.path.join(ROOT, "config"), compiled,
            material_mode="full")
        self.assertIn("```mermaid", full)
        self.assertNotIn("按需開檔，勿一次全讀", full)
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
        del bad["narrative"]
        self.assertTrue(any("narrative" in e or "缺少" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["narrative"]["tradeoffs"] = []
        self.assertTrue(any("tradeoffs" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["narrative"]["how_to_use"] = [{"scenario": "x"}]
        self.assertTrue(any("how_to_use" in e
                            for e in design.validate_design_result(bad)))
        bad = copy.deepcopy(RESULT)
        bad["narrative"]["references"] = [{"source": "config/x.md"}]
        self.assertTrue(any("references" in e
                            for e in design.validate_design_result(bad)))

    def test_name_consistency_checks(self):
        """C1-C4：宣告是產物的根，DDL／欄位／source 必須與宣告一致。"""
        self.assertEqual([], design.validate_design_result(RESULT))  # 基準過
        # C1 表名不一致（宣告 vs CREATE TABLE）
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][1]["name"] = "invoice_summary"
        bad["physical_design"]["tables"][1]["keys"]["business_key"] = \
            ["invoice_id"]
        self.assertTrue(any("表名不一致" in e
                            for e in design.validate_design_result(bad)))
        # C2 欄位宣告與 ddl 漂移
        bad = copy.deepcopy(RESULT)
        del bad["physical_design"]["tables"][0]["columns"][1]  # customer_id
        self.assertTrue(any("欄位宣告與 ddl 不一致" in e
                            for e in design.validate_design_result(bad)))
        # C4 source 指向不存在的來源欄位（改名時 source 要填原欄名）
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][1]["columns"][1]["source"] = \
            "invoice.no_such_col"
        self.assertTrue(any("source" in e and "不存在" in e
                            for e in design.validate_design_result(bad)))
        # C3 單檔模式：draft_ddl 表名集合必須＝宣告集合
        bad = copy.deepcopy(RESULT)
        for t in bad["physical_design"]["tables"]:
            t.pop("ddl", None)
        bad["draft_ddl"] = ("CREATE TABLE invoice (invoice_id UInt64) "
                            "ENGINE = MergeTree() ORDER BY (invoice_id);")
        self.assertTrue(any("表名集合" in e
                            for e in design.validate_design_result(bad)))
        # C5 table_relations 端點必須存在
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["table_relations"] = [
            {"from": "invoice_wide.no_such", "to": "invoice.invoice_id",
             "cardinality": "1:1"}]
        self.assertTrue(any("table_relations" in e and "不存在" in e
                            for e in design.validate_design_result(bad)))


class T_D7_ProductPrefix(unittest.TestCase):
    """產品縮寫：registry 載入、prompt 前綴規則、逐表前綴檢查。"""

    def test_load_products_merges_common_and_domain(self):
        p = design.load_products(os.path.join(ROOT, "config"), ["CRM"])
        self.assertIn("pi", p["codes"])
        self.assertEqual("Product Insight", p["codes"]["pi"]["name"])
        self.assertEqual("CRM", p["codes"]["pi"]["domain"])
        self.assertIn("om", p["codes"])
        self.assertIn("dim", p["layers"])      # 分層前綴來自 Common
        self.assertIn("dwd", p["layers"])

    def test_prompt_prefix_rules(self):
        compiled = os.path.join(ROOT, "build", "compiled_rules.json")
        ctx_pi = CONTEXT.replace("domains: [CRM]",
                                 "domains: [CRM]\nproduct: pi")
        text = design.build_design_prompt(
            "invoice", ctx_pi, os.path.join(ROOT, "config"), compiled)
        self.assertIn("## 表命名前綴（產品縮寫）", text)
        self.assertIn("`dim_pi_customer`", text)
        self.assertIn("<分層前綴>_pi_<語意名>", text)
        # 未登錄縮寫 → 提示登錄
        ctx_zz = CONTEXT.replace("domains: [CRM]",
                                 "domains: [CRM]\nproduct: zz")
        text = design.build_design_prompt(
            "invoice", ctx_zz, os.path.join(ROOT, "config"), compiled)
        self.assertIn("未登錄", text)
        self.assertIn("提議把此縮寫登錄進註冊表", text)
        # 未宣告 → 不強制、指引宣告方式
        text = design.build_design_prompt(
            "invoice", CONTEXT, os.path.join(ROOT, "config"), compiled)
        self.assertIn("表名不強制產品前綴", text)

    def test_prefix_check_per_table(self):
        product = {"code": "pi", "name": "Product Insight",
                   "layers": ["ods", "dim", "dwd", "dws", "ads"]}
        good = copy.deepcopy(RESULT)
        for t, new in zip(good["physical_design"]["tables"],
                          ("dwd_pi_invoice", "ads_pi_invoice_wide")):
            t["name"] = new
        rows = design.product_prefix_check(good, product)
        self.assertTrue(all(r["ok"] for r in rows))
        rows = design.product_prefix_check(RESULT, product)  # 原名無前綴
        self.assertFalse(any(r["ok"] for r in rows))
        self.assertIn("_pi_", rows[0]["expected"])
        self.assertEqual([], design.product_prefix_check(RESULT, None))

    def test_rendered_prefix_section(self):
        rep, hist = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, rep)
        self.addCleanup(shutil.rmtree, hist)
        product = {"code": "pi", "name": "Product Insight",
                   "layers": ["dim", "dwd"]}
        design.render("invoice", RESULT, CONTEXT, hist, rep, product=product)
        physical = open(os.path.join(rep, "invoice.physical_design.md"),
                        encoding="utf-8").read()
        self.assertIn("## 表名產品前綴檢查（產品：`pi`", physical)
        self.assertIn("❌ `invoice` — 應為 `<dim|dwd>_pi_<語意名>`", physical)


class T_D8_MaterialIndex(unittest.TestCase):
    """素材索引：自動摘要打底、front-matter 三欄位覆蓋、審閱表、必讀防漏。"""

    def test_defaults_and_frontmatter_override(self):
        cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, cfg)
        # 無 front-matter → 自動摘要＋預設階段
        write(os.path.join(cfg, "CRM", "erd", "core.md"),
              "# 模型\n```mermaid\nerDiagram\n  customer {\n    UInt64 "
              "customer_id PK\n  }\n```\n")
        # 有 front-matter → 三欄位覆蓋
        write(os.path.join(cfg, "CRM", "flows", "o2r.md"),
              "---\nindex_summary: 訂單到營收的金流節點\nindex_stage: [L, P]\n"
              "index_required: true\n---\n# 流程\n```mermaid\nflowchart LR\n"
              "a-->b\n```\n")
        write(os.path.join(cfg, "CRM", "ssot", "registry.yaml"),
              "registry:\n  customer:\n    authoritative_table: dim_customer\n")
        entries = {e["path"]: e for e in design.design_index(cfg, ["CRM"])}
        erd = entries["config/CRM/erd/core.md"]
        self.assertTrue(erd["auto_summary"])
        self.assertIn("customer", erd["summary"])       # 自動萃取實體
        self.assertEqual(["L"], erd["stage"])           # 預設階段
        self.assertFalse(erd["required"])
        flow = entries["config/CRM/flows/o2r.md"]
        self.assertFalse(flow["auto_summary"])
        self.assertEqual("訂單到營收的金流節點", flow["summary"])
        self.assertEqual(["L", "P"], flow["stage"])
        self.assertTrue(flow["required"])
        ssot = entries["config/CRM/ssot/registry.yaml"]
        self.assertTrue(ssot["required"])               # SSOT 預設必讀
        self.assertIn("customer", ssot["summary"])

    def test_review_md(self):
        text = design.index_review_md(os.path.join(ROOT, "config"))
        self.assertIn("怎麼維護（只有三個選填欄位）", text)
        self.assertIn("index_summary:", text)
        self.assertIn("config/CRM/erd/crm_core.md", text)
        self.assertIn("🤖 自動（待人工確認）", text)

    def test_required_sources_reminder_in_story(self):
        rep, hist = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, rep)
        self.addCleanup(shutil.rmtree, hist)
        required = ["config/CRM/ssot/registry.yaml",
                    "config/CRM/erd/crm_core.md"]
        design.render("invoice", RESULT, CONTEXT, hist, rep,
                      required_sources=required)
        story = open(os.path.join(rep, "invoice.design_story.md"),
                     encoding="utf-8").read()
        # fixture 的 references 已含 crm_core.md → 只提醒漏掉的 ssot
        self.assertIn("必讀素材未見於出處宣告", story)
        self.assertIn("config/CRM/ssot/registry.yaml", story)
        self.assertNotIn("`config/CRM/erd/crm_core.md`——請確認", story)


class T_D6_CrossTableChecks(unittest.TestCase):
    """跨表比對（X1-X4）：設計內多積木一致性的確定性檢查。"""

    def _by_check(self, result):
        return {x["check"][:2]: x for x in design.cross_table_checks(result)}

    def test_all_pass_on_consistent_design(self):
        checks = self._by_check(RESULT)
        self.assertEqual("pass", checks["X1"]["status"])   # join 鍵型別一致
        self.assertEqual("pass", checks["X2"]["status"])   # source 型別相容
        self.assertEqual("pass", checks["X3"]["status"])   # 同名欄型別一致
        self.assertEqual("pass", checks["X4"]["status"])   # 無重複承載

    def test_single_table_returns_empty(self):
        solo = copy.deepcopy(RESULT)
        solo["physical_design"]["tables"] = \
            solo["physical_design"]["tables"][:1]
        self.assertEqual([], design.cross_table_checks(solo))

    def test_x1_join_key_type_mismatch(self):
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][1]["columns"][0]["type"] = "String"
        checks = self._by_check(bad)
        self.assertEqual("fail", checks["X1"]["status"])
        self.assertIn("invoice_wide.invoice_id", checks["X1"]["detail"])
        self.assertEqual("fail", checks["X3"]["status"])   # 同名欄同時被抓

    def test_x2_source_type_mismatch_warns(self):
        bad = copy.deepcopy(RESULT)
        bad["physical_design"]["tables"][1]["columns"][1]["type"] = "String"
        checks = self._by_check(bad)
        self.assertEqual("warn", checks["X2"]["status"])
        self.assertIn("buyer_id", checks["X2"]["detail"])

    def test_x4_duplicated_fact_without_lineage(self):
        bad = copy.deepcopy(RESULT)
        for i in (0, 1):   # 兩表都放 status 欄、都無 source → 重複承載
            bad["physical_design"]["tables"][i]["columns"].append(
                {"name": "status", "type": "String", "nullable": False,
                 "comment": "狀態"})
        bad["physical_design"]["tables"][0]["ddl"] = \
            bad["physical_design"]["tables"][0]["ddl"].replace(
                "customer_id UInt64 COMMENT '客戶'",
                "customer_id UInt64 COMMENT '客戶', status String COMMENT 's'")
        bad["physical_design"]["tables"][1]["ddl"] = \
            bad["physical_design"]["tables"][1]["ddl"].replace(
                "buyer_id UInt64 COMMENT '買方'",
                "buyer_id UInt64 COMMENT '買方', status String COMMENT 's'")
        checks = self._by_check(bad)
        self.assertEqual("warn", checks["X4"]["status"])
        self.assertIn("`status`", checks["X4"]["detail"])
        # Nullable 外殼不算型別不一致（X3 剝殼比對）
        self.assertEqual("pass", checks["X3"]["status"])

    def test_rendered_into_physical_design(self):
        rep, hist = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, rep)
        self.addCleanup(shutil.rmtree, hist)
        design.render("invoice", RESULT, CONTEXT, hist, rep)
        physical = open(os.path.join(rep, "invoice.physical_design.md"),
                        encoding="utf-8").read()
        self.assertIn("## 跨表比對（設計內多表一致性——確定性檢查）", physical)
        self.assertIn("✅ **X1 join 鍵型別一致", physical)
        self.assertIn("✅ **X4 同一事實重複承載", physical)
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
        # 7. Column Mapping：來源 → 本設計欄位，改名詳實交代
        self.assertIn("## 7. Column Mapping（欄位來源對應）", logical)
        self.assertIn("| `invoice.customer_id` | `invoice_wide.buyer_id` "
                      "| ✏️ 改名 |", logical)
        self.assertIn("| `invoice.invoice_id` | `invoice_wide.invoice_id` "
                      "| — |", logical)
        self.assertIn("| `CRM.dim_customer.customer_id` "
                      "| `invoice.customer_id` | — |", logical)
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
        # 設計故事（人讀版）：白話原因、取捨、實用指南＋自動決策速覽
        story = open(os.path.join(self.rep, "invoice.design_story.md"),
                     encoding="utf-8").read()
        self.assertIn("# 設計故事 — invoice（第 1 輪設計）", story)
        self.assertIn("為什麼需要這個主體", story)
        self.assertIn("關鍵取捨", story)
        self.assertIn("預算換讀取效能", story)                 # because
        self.assertIn("怎麼使用（實用指南）", story)
        self.assertIn("勿掃明細表", story)                     # guidance
        self.assertIn("常見誤用與陷阱", story)
        self.assertIn("給工程師的啟發", story)
        self.assertIn("決策速覽", story)
        self.assertIn("以 business key 排序", story)           # 自動彙整決策理由
        # 設計出處：agent 宣告（可點連結）；render 未帶素材清單時只有宣告段
        self.assertIn("設計出處", story)
        self.assertIn("[config/CRM/erd/crm_core.md](../../config/CRM/erd/"
                      "crm_core.md)", story)
        self.assertIn("對齊此參考模型", story)
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
        # relations 對象是 config 來源表：外部 source 自動衍生引用
        self.assertIn("from: invoice.customer_id", rel)
        self.assertIn("to: CRM.dim_customer.customer_id", rel)
        self.assertIn("自動衍生自欄位 source", rel)
        # 拿掉寬表與宣告 → 衍生的來源表引用仍在草稿（relations 不清空）
        shrunk = copy.deepcopy(RESULT)
        shrunk["physical_design"]["tables"] = \
            shrunk["physical_design"]["tables"][:1]
        shrunk["physical_design"]["table_relations"] = []
        design.render("invoice", shrunk, CONTEXT, self.hist, self.rep)
        self.assertEqual(["invoice.ddl"], sorted(os.listdir(ddl_dir)))
        rel2 = open(os.path.join(self.rep, "invoice.design.relations.yaml"),
                    encoding="utf-8").read()
        self.assertIn("to: CRM.dim_customer.customer_id", rel2)
        self.assertNotIn("invoice_wide", rel2)
        # 完全無關係、無外部 source → 草稿移除
        bare = copy.deepcopy(shrunk)
        for c in bare["physical_design"]["tables"][0]["columns"]:
            c.pop("source", None)
        design.render("invoice", bare, CONTEXT, self.hist, self.rep)
        self.assertFalse(os.path.isfile(
            os.path.join(self.rep, "invoice.design.relations.yaml")))

    def test_derived_relations_from_config_source(self):
        """relations 從 config 來源表產生：外部 source → N:1 reference；
        宣告過的不重複衍生；本地 source 不衍生。"""
        derived = design.derived_source_relations(RESULT)
        self.assertEqual(1, len(derived))
        self.assertEqual("invoice.customer_id", derived[0]["from"])
        self.assertEqual("CRM.dim_customer.customer_id", derived[0]["to"])
        self.assertEqual("N:1", derived[0]["cardinality"])
        self.assertEqual("reference", derived[0]["kind"])
        # all_relations＝宣告＋衍生；agent 已宣告同一條時不重複
        rels = design.all_relations(RESULT)
        self.assertEqual(2, len(rels))   # 宣告 1（wide→invoice）＋衍生 1
        dup = copy.deepcopy(RESULT)
        dup["physical_design"]["table_relations"].append(
            {"from": "invoice.customer_id",
             "to": "CRM.dim_customer.customer_id", "cardinality": "N:1"})
        self.assertEqual(2, len(design.all_relations(dup)))   # 去重
        # physical design 的關係表標示來源
        rep, hist = tempfile.mkdtemp(), tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, rep)
        self.addCleanup(shutil.rmtree, hist)
        design.render("invoice", RESULT, CONTEXT, hist, rep)
        physical = open(os.path.join(rep, "invoice.physical_design.md"),
                        encoding="utf-8").read()
        self.assertIn("🔗 自動衍生", physical)
        self.assertIn("`CRM.dim_customer.customer_id`", physical)

    def test_story_lists_config_sources(self):
        """工具紀錄的素材清單：reference_materials 掃描結果進設計出處。"""
        sources = design.reference_materials(
            os.path.join(ROOT, "config"), ["CRM"])
        kinds = {k for k, _ in sources}
        self.assertIn("參考 ER 模型", kinds)
        self.assertIn("詞彙字典", kinds)
        self.assertIn("SSOT 權威登錄", kinds)
        self.assertIn("設計約束（閘門規則）", kinds)
        self.assertIn("設計 know-how（顧問規則）", kinds)
        paths = [p for _, p in sources]
        self.assertIn("config/CRM/erd/crm_core.md", paths)
        self.assertIn("config/Common/naming/glossary.md", paths)
        self.assertIn("config/Common/knowhow/advisory/best_practice_semantic.md",
                      paths)
        design.render("invoice", RESULT, CONTEXT, self.hist, self.rep,
                      config_sources=sources)
        story = open(os.path.join(self.rep, "invoice.design_story.md"),
                     encoding="utf-8").read()
        self.assertIn("本輪設計餵入的 config 素材", story)
        self.assertIn("[config/CRM/erd/crm_core.md](../../config/CRM/erd/"
                      "crm_core.md)", story)

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
                      "gating/bp_no_float.md](../../config/Common/knowhow/gating/"
                      "bp_no_float.md)", physical)
        self.assertIn("- ⚠️ `SKILL.naming_glossary`", physical)
        self.assertIn("(../../config/Common/naming/)", physical)   # 字典也可點

    def test_single_draft_ddl_compat(self):
        """相容：只有整體 draft_ddl（無逐表 ddl）→ 單檔模式、不拆檔。"""
        legacy = copy.deepcopy(RESULT)
        for t in legacy["physical_design"]["tables"]:
            t.pop("ddl", None)
        legacy["draft_ddl"] = (
            "CREATE TABLE invoice (invoice_id UInt64 COMMENT 'x') "
            "ENGINE = MergeTree() ORDER BY (invoice_id);\n"
            "CREATE TABLE invoice_wide (invoice_id UInt64 COMMENT 'x') "
            "ENGINE = MergeTree() ORDER BY (invoice_id);")
        self.assertEqual([], design.validate_design_result(legacy))
        self.assertEqual(legacy["draft_ddl"], design.combined_ddl(legacy))
        info = design.render("invoice", legacy, CONTEXT, self.hist, self.rep)
        self.assertEqual(0, info["ddl_files"])


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""正式區資產（prodassets.py）的守門測試。

守的保證：
  P1 掃描：production/<域>/<subject>/ 的三件輸入與表名都掃得到
  P2 索引：寫進 config/Common/production/registry.md，front-matter 標必讀；
     內容確定性（沒變不改寫）；正式區空也產得出殼
  P3 複用判定：relations 三段式與設計稿欄位 source 都算數，只認確定性證據
  P4 閘門檢查：有引用 → pass、沒引用 → warning（不擋）、正式區空 → 不作用
  P5 問答題：沒引用才出題，id 格式對得上 answers.add_proposals
  P6 素材索引：registry 在 Common ⇒ 任何 domain 的設計都掃得到且標必讀
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import answers as answers_mod, design, prodassets   # noqa: E402

DDL = ("CREATE TABLE dim_customer (customer_id UInt64 COMMENT '客戶', "
       "customer_name String COMMENT '姓名') ENGINE = MergeTree() "
       "ORDER BY (customer_id);")
CONTEXT = ("---\nsubject: 客戶主檔\n---\n\n## 這個 data subject 是什麼\n"
           "客戶主檔，全公司客戶屬性的權威來源。\n")


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class Base(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)
        self.prod = os.path.join(self.dir, "production")
        self.config = os.path.join(self.dir, "config")

    def seed(self, domain="CRM", subject="dim_customer"):
        base = os.path.join(self.prod, domain, subject)
        write(os.path.join(base, f"{subject}.sql"), DDL)
        write(os.path.join(base, f"{subject}.relations.yaml"), "relations: []\n")
        write(os.path.join(base, f"{subject}.context.md"), CONTEXT)


class T_P1_Scan(Base):
    def test_scans_three_inputs_and_tables(self):
        self.seed()
        assets = prodassets.scan(self.prod)
        self.assertEqual(1, len(assets))
        asset = assets[0]
        self.assertEqual(("CRM", "dim_customer"),
                         (asset["domain"], asset["subject"]))
        self.assertEqual(["dim_customer"], asset["tables"])
        self.assertEqual({"sql", "relations", "context"}, set(asset["files"]))
        self.assertIn("客戶主檔", asset["purpose"])

    def test_empty_production(self):
        self.assertEqual([], prodassets.scan(self.prod))
        self.assertEqual([], prodassets.scan(""))


class T_P2_Registry(Base):
    def test_written_to_common_with_required_front_matter(self):
        self.seed()
        assets = prodassets.scan(self.prod)
        path, changed = prodassets.write_registry(self.config, assets)
        self.assertTrue(changed)
        self.assertTrue(path.endswith(os.path.join(
            "config", "Common", "production", "registry.md")))
        text = open(path, encoding="utf-8").read()
        self.assertIn("index_required: true", text)      # 標必讀
        self.assertIn("index_stage: [L, P]", text)
        self.assertIn("`dim_customer`", text)
        self.assertIn("production/CRM/dim_customer/dim_customer.sql", text)

    def test_deterministic_and_no_rewrite(self):
        self.seed()
        assets = prodassets.scan(self.prod)
        prodassets.write_registry(self.config, assets)
        _, changed = prodassets.write_registry(self.config, assets)
        self.assertFalse(changed)                        # 沒變就不改寫

    def test_empty_production_still_renders(self):
        path, _ = prodassets.write_registry(self.config, [])
        self.assertIn("正式區目前是空的", open(path, encoding="utf-8").read())


class T_P3_ReferenceDetection(Base):
    def setUp(self):
        super().setUp()
        self.seed()
        self.assets = prodassets.scan(self.prod)

    def test_relations_triple_counts(self):
        rels = [{"from": "orders.customer_id",
                 "to": "CRM.dim_customer.customer_id"}]
        self.assertEqual(["crm.dim_customer"],
                         prodassets.referenced_by_relations(rels, self.assets))

    def test_local_relations_do_not_count(self):
        rels = [{"from": "order_items.order_id", "to": "orders.order_id"}]
        self.assertEqual([],
                         prodassets.referenced_by_relations(rels, self.assets))

    def test_unknown_domain_table_does_not_count(self):
        rels = [{"to": "SCM.dim_product.product_id"}]
        self.assertEqual([],
                         prodassets.referenced_by_relations(rels, self.assets))

    def test_design_column_source_counts(self):
        result = {"physical_design": {"tables": [{
            "name": "orders",
            "columns": [{"name": "customer_id",
                         "source": "CRM.dim_customer.customer_id"}]}]}}
        self.assertEqual(["crm.dim_customer"],
                         prodassets.referenced_by_design(result, self.assets))


class T_P4_GatingCheck(Base):
    def test_no_reference_warns_without_blocking(self):
        self.seed()
        findings = prodassets.run(None, [], self.prod)
        self.assertEqual(1, len(findings))
        finding = findings[0]
        self.assertEqual("PRODUCTION.REUSE", finding.check_id)
        self.assertEqual("warning", finding.status)      # 提醒但不擋
        self.assertEqual("gating", finding.zone)
        self.assertIn("CRM.dim_customer", finding.message)

    def test_reference_passes(self):
        self.seed()
        rels = [{"to": "CRM.dim_customer.customer_id"}]
        finding = prodassets.run(None, rels, self.prod)[0]
        self.assertEqual("pass", finding.status)

    def test_empty_production_is_silent(self):
        self.assertEqual([], prodassets.run(None, [], self.prod))


class T_P5_Question(Base):
    def test_question_only_when_not_reused(self):
        self.seed()
        assets = prodassets.scan(self.prod)
        self.assertIsNone(prodassets.open_question("s", assets,
                                                   ["crm.dim_customer"]))
        self.assertIsNone(prodassets.open_question("s", [], []))
        question = prodassets.open_question("subscription", assets, [])
        self.assertEqual("PRODUCTION.REUSE@subscription", question["id"])
        # 直接餵得進 answers.yaml 的代填流程
        merged, added = answers_mod.add_proposals(None, [question])
        self.assertEqual(1, added)
        self.assertEqual("proposed", merged["answers"][0]["status"])
        _, again = answers_mod.add_proposals(merged, [question])
        self.assertEqual(0, again)                       # 不重複新增


class T_P6_DesignMaterial(Base):
    def test_registry_is_required_material_for_every_domain(self):
        self.seed()
        prodassets.write_registry(self.config, prodassets.scan(self.prod))
        # 另開一個與 CRM 無關的 domain，確認 Common 的資產索引照樣進索引
        write(os.path.join(self.config, "SCM", "naming", "glossary.md"),
              "# 字典\n\n## 禁用詞\n\n| 禁用 | 改用 |\n|---|---|\n| qty | quantity |\n")
        entries = design.design_index(self.config, ["SCM"])
        registry = [e for e in entries if e["kind"] == "正式區資產"]
        self.assertEqual(1, len(registry))
        self.assertTrue(registry[0]["required"])          # 必讀
        self.assertEqual(["L", "P"], registry[0]["stage"])
        self.assertIn("已核准 1 個 data subject", registry[0]["summary"])


if __name__ == "__main__":
    unittest.main()

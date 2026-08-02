#!/usr/bin/env python3
"""衍生 SQL（derivation.sql）的守門測試。

守的保證：
  D1 解析：別名還原、ON 鍵、逐欄 provenance、CREATE AS／INSERT SELECT
     取內層、SELECT * 標記、壞 SQL 報錯
  D2 對照：relations 交叉驗證（未宣告警告／未使用提示）、寬表欄位覆蓋、
     三方鍵矩陣
  D3 端到端：precheck 認得選填件；findings 為確定性閘門警告（不擋）；
     報告三式呈現
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import derivation
from dataval.model import Finding
from dataval.parser import parse_ddl

SQL = """
SELECT
  o.order_id,
  o.customer_id,
  c.customer_name,
  o.total_amount * 2 AS doubled
FROM orders AS o
LEFT JOIN dim_customer AS c ON o.customer_id = c.customer_id
"""

DDL = ("CREATE TABLE orders_wide (order_id UInt64 COMMENT 'x', "
       "customer_id UInt64 COMMENT 'y', customer_name String COMMENT 'z', "
       "doubled Decimal(18,2) COMMENT 'd') "
       "ENGINE=MergeTree() PRIMARY KEY (order_id) ORDER BY (order_id);")


class T_D1_Parse(unittest.TestCase):
    def test_aliases_keys_and_provenance(self):
        d = derivation.parse_derivation(SQL)
        self.assertEqual("orders", d["base_table"])
        self.assertEqual(["dim_customer", "orders"], d["source_tables"])
        self.assertEqual(1, len(d["joins"]))
        key = d["joins"][0]["keys"][0]
        self.assertEqual(("orders", "customer_id", "dim_customer", "customer_id"),
                         (key["left_table"], key["left_column"],
                          key["right_table"], key["right_column"]))
        by_name = {o["name"]: o for o in d["outputs"]}
        self.assertEqual("dim_customer", by_name["customer_name"]["source_table"])
        self.assertEqual("expression", by_name["doubled"]["kind"])
        self.assertFalse(d["has_star"])

    def test_create_as_and_insert_select_unwrapped(self):
        for wrapper in (f"CREATE TABLE w ENGINE=MergeTree ORDER BY tuple() AS {SQL}",
                        f"INSERT INTO w {SQL}"):
            d = derivation.parse_derivation(wrapper)
            self.assertEqual("orders", d["base_table"])

    def test_select_star_flagged(self):
        d = derivation.parse_derivation("SELECT o.* FROM orders o")
        self.assertTrue(d["has_star"])

    def test_bad_sql_raises(self):
        with self.assertRaises(Exception):
            derivation.parse_derivation("SELEC broken FROM")
        with self.assertRaises(ValueError):
            derivation.parse_derivation("SELECT 1; SELECT 2")


class T_D2_Comparisons(unittest.TestCase):
    def _relations(self, *pairs):
        out = []
        for (ft, fc, tt, tc) in pairs:
            out.append({"_from": {"scope": "local", "table": ft, "column": fc},
                        "_to": {"scope": "local", "table": tt, "column": tc}})
        return out

    def test_undeclared_join_warns_and_declared_pass(self):
        schema = parse_ddl(DDL)
        d = derivation.parse_derivation(SQL)
        # 未宣告 → 警告
        findings, meta = derivation.derivation_layer(
            schema, d, [], [], None)
        rel = [f for f in findings if f.check_id == "DERIVATION.RELATIONS"]
        self.assertEqual("warning", rel[0].status)
        self.assertIn("customer_id", rel[0].message)
        # 宣告齊 → pass；多宣告一條 → info 提示
        relations = self._relations(
            ("orders", "customer_id", "dim_customer", "customer_id"),
            ("orders", "shop_id", "dim_shop", "shop_id"))
        findings, meta = derivation.derivation_layer(
            schema, d, [], relations, None)
        statuses = {f.status for f in findings
                    if f.check_id == "DERIVATION.RELATIONS"}
        self.assertEqual({"pass", "info"}, statuses)

    def test_coverage_matches_wide_table(self):
        schema = parse_ddl(DDL)
        d = derivation.parse_derivation(SQL)
        findings, meta = derivation.derivation_layer(schema, d, [], [], None)
        cov = meta["coverage"]
        self.assertEqual("orders_wide", cov["wide_table"])
        self.assertEqual(4, cov["covered"])
        self.assertEqual([], cov["missing_in_sql"])
        self.assertIn("pass", {f.status for f in findings
                               if f.check_id == "DERIVATION.COVERAGE"})

    def test_coverage_mismatch_warns(self):
        ddl = DDL.replace("doubled Decimal(18,2) COMMENT 'd') ",
                          "doubled Decimal(18,2) COMMENT 'd', "
                          "extra_col String COMMENT 'e') ")
        findings, meta = derivation.derivation_layer(
            parse_ddl(ddl), derivation.parse_derivation(SQL), [], [], None)
        cov = [f for f in findings if f.check_id == "DERIVATION.COVERAGE"][0]
        self.assertEqual("warning", cov.status)
        self.assertIn("extra_col", cov.message)

    def test_key_matrix_three_way(self):
        schema = parse_ddl(DDL)
        d = derivation.parse_derivation(SQL)
        proposal = {"join_sql":
                    "SELECT 1 FROM orders LEFT JOIN dim_customer "
                    "ON orders.customer_id = dim_customer.customer_id"}
        _, meta = derivation.derivation_layer(
            schema, d, [],
            self._relations(("orders", "customer_id",
                             "dim_customer", "customer_id")),
            proposal)
        self.assertTrue(meta["has_proposal"])
        row = meta["key_matrix"][0]
        self.assertTrue(row["in_sql"] and row["in_relations"]
                        and row["in_proposal"])

    def test_parse_problem_becomes_warning(self):
        findings, meta = derivation.derivation_layer(
            parse_ddl(DDL), None, ["SyntaxError: x"], [], None)
        self.assertIsNone(meta)
        self.assertEqual(["DERIVATION.PARSE"], [f.check_id for f in findings])
        self.assertEqual("warning", findings[0].status)
        self.assertEqual("gating", findings[0].zone)


class T_D3_EndToEnd(unittest.TestCase):
    def test_precheck_and_reports(self):
        from dataval.precheck import run_precheck
        from dataval.report import derivation_lines, to_html, to_json
        import json as _json
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        subj = os.path.join(tmp, "wide")
        os.makedirs(subj)
        with open(os.path.join(subj, "wide.sql"), "w", encoding="utf-8") as f:
            f.write(DDL.replace("orders_wide", "wide_orders"))
        with open(os.path.join(subj, "relations.yaml"), "w",
                  encoding="utf-8") as f:
            f.write("relations: []\n")
        with open(os.path.join(subj, "context.md"), "w", encoding="utf-8") as f:
            f.write("---\nsubject: 寬表\n---\n## 粒度\n一行一單。\n")
        with open(os.path.join(subj, "derivation.sql"), "w",
                  encoding="utf-8") as f:
            f.write(SQL)
        pre = run_precheck(os.path.join(subj, "wide.sql"))
        self.assertTrue(pre.passed)
        self.assertIsNotNone(pre.derivation_data)
        self.assertIn("衍生 SQL",
                      "".join(i.label for i in pre.items))
        # 報告呈現（用 meta 直接渲染）
        meta = {"derivation": {"file": "derivation.sql", "base_table": "orders",
                               "source_tables": ["dim_customer", "orders"],
                               "join_count": 1, "output_count": 4,
                               "expression_count": 1, "sql": SQL.strip(),
                               "coverage": None, "key_matrix": [
                                   {"pair": "a.x = b.x", "in_sql": True,
                                    "in_relations": False,
                                    "in_proposal": False}],
                               "has_proposal": False}}
        md = "\n".join(derivation_lines(meta))
        self.assertIn("衍生 SQL 對照", md)
        self.assertIn("join 鍵三方對照", md)
        self.assertIn("衍生 SQL 對照", to_html([], meta))
        self.assertIn("derivation", _json.loads(to_json([], meta)))


if __name__ == "__main__":
    unittest.main()

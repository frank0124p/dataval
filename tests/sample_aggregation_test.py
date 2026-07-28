#!/usr/bin/env python3
"""樣本檢查的按欄位彙整。

守的保證：同一欄位有多筆違規樣本時，報告只出**一筆** finding
（fail 與 warning 各自一筆），訊息含筆數與違規值、evidence 保留全部——
不逐列刷版。"""
from __future__ import annotations

import importlib.util
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval.parser import parse_ddl

_RULE = os.path.join(ROOT, "config", "Common", "knowhow_py",
                     "structural_type_sample.py")
spec = importlib.util.spec_from_file_location("structural_type_sample", _RULE)
rule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rule)

DDL = """
CREATE TABLE t (
  qty UInt32,
  amount Decimal(18,2)
) ENGINE=MergeTree ORDER BY (qty)
"""


class SampleAggregationTest(unittest.TestCase):
    def _run(self, rows):
        schema = parse_ddl(DDL, sample_data={"t": rows})
        return rule.check_schema(schema, {"cfg": {}, "glossary": {}})

    def test_multiple_bad_rows_same_column_yield_one_finding(self):
        rows = [{"qty": 1.5}, {"qty": 2.5}, {"qty": 3.5}, {"qty": 4}]
        found = self._run(rows)
        fails = [f for f in found if f.status == "fail"]
        self.assertEqual(1, len(fails), [f.message for f in found])
        f = fails[0]
        self.assertEqual("t.qty", f.target)
        self.assertIn("3 筆", f.message)
        self.assertEqual([1.5, 2.5, 3.5], f.evidence)

    def test_fail_and_warning_are_separate_rows_per_column(self):
        rows = [{"qty": 1.5, "amount": "abc"}, {"qty": 2.5, "amount": "xyz"}]
        found = self._run(rows)
        fails = [f for f in found if f.status == "fail"]
        warns = [f for f in found if f.status == "warning"]
        self.assertEqual(1, len(fails))
        self.assertEqual(1, len(warns))
        self.assertEqual("t.amount", warns[0].target)
        self.assertIn("2 筆", warns[0].message)
        self.assertEqual(["abc", "xyz"], warns[0].evidence)

    def test_message_preview_caps_but_evidence_keeps_all(self):
        rows = [{"qty": i + 0.5} for i in range(8)]
        found = self._run(rows)
        f = [x for x in found if x.status == "fail"][0]
        self.assertIn("共 8 筆", f.message)
        self.assertEqual(8, len(f.evidence))

    def test_clean_samples_still_single_pass(self):
        found = self._run([{"qty": 1, "amount": "10.00"}, {"qty": 2}])
        self.assertEqual(1, len(found))
        self.assertEqual("pass", found[0].status)

    def test_no_samples_still_single_skip(self):
        found = self._run([])
        self.assertEqual(1, len(found))
        self.assertEqual("skipped", found[0].status)


if __name__ == "__main__":
    unittest.main()

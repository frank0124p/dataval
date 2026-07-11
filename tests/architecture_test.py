#!/usr/bin/env python3
"""Integration tests for domain scope, key semantics, result contract, and merge guard."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval.engine import load_config, validate
from dataval.model import Finding
from dataval.parser import parse_ddl
from dataval.report import checking_rule_summary
from merge_advisory import _gating_from_findings, _gating_from_report


CFG = os.path.join(ROOT, "config", "default.yaml")
KW = dict(skills_root=os.path.join(ROOT, "config", "skills"),
          skill_py_dir=os.path.join(ROOT, "config", "skills_py"),
          config_dir=os.path.join(ROOT, "config"),
          promoted_root=os.path.join(ROOT, "promoted"))


class ArchitectureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config(CFG)
        with open(os.path.join(ROOT, "input", "subscription.sql"),
                  encoding="utf-8") as f:
            cls.ddl = f.read()

    def test_domain_default_is_common_only(self):
        _, findings, meta = validate(self.ddl, self.cfg, domains=[], **KW)
        self.assertEqual(["common"], meta["domains_loaded"])
        self.assertEqual([], meta["domains_requested"])
        scope = [f for f in findings if f.check_id == "DOMAIN.SCOPE"]
        self.assertEqual("warning", scope[0].status)
        self.assertFalse(any("plm_" in f.check_id.lower() for f in findings))

    def test_unknown_domain_is_reported_and_skipped(self):
        _, findings, meta = validate(self.ddl, self.cfg,
                                     domains=["CRM", "DOES_NOT_EXIST"], **KW)
        self.assertEqual(["DOES_NOT_EXIST"], meta["domains_unknown"])
        self.assertIn("CRM", meta["domains_loaded"])
        scope = [f for f in findings if f.check_id == "DOMAIN.SCOPE"]
        self.assertEqual("warning", scope[0].status)
        self.assertIn("DOES_NOT_EXIST", scope[0].message)

    def test_every_loaded_rule_has_explicit_result(self):
        _, findings, meta = validate(self.ddl, self.cfg, domains=[], **KW)
        represented = {f.check_id for f in findings}
        missing = set(meta["checking_rule_ids_loaded"]) - represented
        self.assertEqual(set(), missing)
        self.assertTrue(all(f.status in {"pass", "fail", "warning", "info", "skipped"}
                            for f in findings))
        summary = checking_rule_summary(findings, meta["checking_rule_ids_loaded"])
        skipped_ids = {f.check_id for f in findings if f.status == "skipped"}
        self.assertTrue(set(summary["not_checked"]).issubset(skipped_ids))

    def test_clickhouse_keys_are_separate(self):
        inferred = parse_ddl(
            "CREATE TABLE t (customer_id UInt64, value String) "
            "ENGINE=MergeTree ORDER BY (customer_id)").tables[0]
        self.assertEqual(["customer_id"], inferred.sorting_key)
        self.assertEqual([], inferred.primary_key)
        self.assertEqual(["customer_id"], inferred.business_key)
        self.assertEqual("inferred_sorting_identifier", inferred.business_key_source)

        explicit = parse_ddl(
            "CREATE TABLE t (customer_id UInt64, created_at DateTime, "
            "PRIMARY KEY (customer_id)) ENGINE=MergeTree ORDER BY (created_at)").tables[0]
        self.assertEqual(["created_at"], explicit.sorting_key)
        self.assertEqual(["customer_id"], explicit.primary_key)
        self.assertEqual(["customer_id"], explicit.business_key)
        self.assertEqual("explicit_primary_key", explicit.business_key_source)

    def test_merge_guard_compares_complete_rule_results(self):
        finding = Finding("RULE.ONE", "structural", "pass", "t", "ok",
                          severity="info", zone="gating")
        with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8",
                                         delete=False) as f:
            json.dump({"gating_zone": {"findings": [finding.to_dict()]}}, f,
                      ensure_ascii=False)
            path = f.name
        try:
            self.assertEqual(_gating_from_report(path), _gating_from_findings([finding]))
            changed = Finding("RULE.ONE", "structural", "fail", "t", "changed",
                              severity="error", zone="gating")
            self.assertNotEqual(_gating_from_report(path), _gating_from_findings([changed]))
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

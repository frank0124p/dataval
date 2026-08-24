#!/usr/bin/env python3
"""ETL pipeline 建議檔（etl_manifest.py）的守門測試。

守的保證：
  E1 沒資訊也長殼：agent 沒給 etl_pipeline 時，每個欄位仍在檔案裡
     （值留空＋標 TODO），逐表 job 一張表一個
  E2 缺的欄位進問答區：確定性產生設計提問（含代填答案），
     全部由設計稿宣告齊了就不再發問
  E3 值的優先序：agent 宣告 ＞ context.md 推導 ＞ 工具推導；
     逐表沒覆寫就展開 pipeline 層預設（每個 job 自足）
  E4 驗證：型別錯誤、未知欄位、指向不存在的表會被擋
  E5 產物落地：render 產出 <名>.etl.yaml（design_doc/<名>/），可被 YAML 解析，
     且不影響其他產物；同輸入 → 位元組相同
  E6 純建議：ETL 區塊完全不進閘門判定（只是 design_result 的選填欄位）
"""
from __future__ import annotations

import copy
import os
import shutil
import sys
import tempfile
import unittest

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import design, etl_manifest                        # noqa: E402
from tests.design_test import CONTEXT, RESULT                   # noqa: E402

META = {"subject": "發票", "domains": ["CRM"]}

FULL_SPEC = {
    "id": "etl_inv", "product_suite": "Billing Suite",
    "namespace": "crm_billing", "platform": "clickhouse",
    "source_db": "mysql_erp", "target_db": "ch_dw",
    "write_mode": "deleteInsert", "schedule": "daily 02:00",
    "owner": "data-eng@corp",
    "resources": {"cpu": "2", "memory": "4Gi"},
    "tables": [{"table": "invoice_wide", "write_mode": "insert",
                "resources": {"memory": "8Gi"}}],
}


def with_etl(spec) -> dict:
    result = copy.deepcopy(RESULT)
    result["etl_pipeline"] = copy.deepcopy(spec)
    return result


class T_E1_ShellWhenNothingGiven(unittest.TestCase):
    def test_every_field_present_even_without_info(self):
        manifest = etl_manifest.build("invoice", RESULT, META)
        text = etl_manifest.to_yaml("invoice", 1, manifest)
        data = yaml.safe_load(text)
        # 使用者要的欄位一個都不少
        for key in ("id", "product_suite", "namespace", "platform",
                    "source_db", "target_db", "write_mode", "schedule",
                    "owner"):
            self.assertIn(key, data, key)
        self.assertEqual({"cpu": None, "memory": None}, data["resources"])
        # 沒資訊的欄位：值留空＋註解標 TODO
        self.assertIsNone(data["product_suite"])
        self.assertIn("⬅ TODO 待填：所屬 product suite", text)
        # 表名來自設計（一張表一個 ETL job）
        self.assertEqual(["invoice", "invoice_wide"],
                         [t["table"] for t in data["tables"]])

    def test_platform_and_id_derived(self):
        manifest = etl_manifest.build("invoice", RESULT, META)
        self.assertEqual("clickhouse",
                         manifest["pipeline"]["platform"]["value"])
        self.assertEqual("etl_invoice", manifest["pipeline"]["id"]["value"])
        self.assertEqual("derived", manifest["pipeline"]["id"]["origin"])
        self.assertEqual("etl_invoice.invoice_wide",
                         manifest["tables"][1]["fields"]["id"]["value"])

    def test_no_tables_still_renders(self):
        empty = copy.deepcopy(RESULT)
        empty["physical_design"]["tables"] = []
        manifest = etl_manifest.build("invoice", empty, META)
        data = yaml.safe_load(etl_manifest.to_yaml("invoice", 1, manifest))
        self.assertEqual([], data["tables"])


class T_E2_MissingFieldsBecomeQuestions(unittest.TestCase):
    def test_questions_cover_every_missing_field(self):
        manifest = etl_manifest.build("invoice", RESULT, META)
        questions = etl_manifest.open_questions("invoice", manifest, ["CRM"])
        joined = "\n".join(q["question"] for q in questions)
        for keyword in ("product suite", "namespace", "來源 DB", "更新方式",
                        "更新頻率", "CPU", "owner"):
            self.assertIn(keyword, joined, keyword)
        # 每題都附代填答案（設計問答迴圈的規矩）
        self.assertTrue(all(q["proposed_answer"].strip() for q in questions))
        # 提問文字跨輪穩定（question_id 是文字的 hash）
        self.assertEqual(
            [q["question"] for q in questions],
            [q["question"] for q in
             etl_manifest.open_questions("invoice", manifest, ["CRM"])])

    def test_no_questions_when_everything_declared(self):
        manifest = etl_manifest.build("invoice", with_etl(FULL_SPEC), META)
        self.assertEqual([], etl_manifest.open_questions("invoice", manifest))
        self.assertEqual([], manifest["missing"])

    def test_questions_merge_into_design_answers(self):
        manifest = etl_manifest.build("invoice", RESULT, META)
        data, added = design.merge_design_answers(
            {"version": 1, "answers": []},
            etl_manifest.open_questions("invoice", manifest, ["CRM"]))
        self.assertEqual(added, len(data["answers"]))
        self.assertTrue(all(e["status"] == "proposed"
                            for e in data["answers"]))
        # 再跑一次不重複代填
        _, again = design.merge_design_answers(
            data, etl_manifest.open_questions("invoice", manifest, ["CRM"]))
        self.assertEqual(0, again)


class T_E3_ValuePrecedence(unittest.TestCase):
    def test_agent_beats_context_and_derived(self):
        manifest = etl_manifest.build(
            "invoice", with_etl({"platform": "doris",
                                 "product_suite": "Ops Suite"}),
            {**META, "product": "crm"})
        self.assertEqual("doris", manifest["pipeline"]["platform"]["value"])
        self.assertEqual("Ops Suite",
                         manifest["pipeline"]["product_suite"]["value"])

    def test_context_product_fills_product_suite(self):
        manifest = etl_manifest.build("invoice", RESULT,
                                      {**META, "product": "crm"})
        suite = manifest["pipeline"]["product_suite"]
        self.assertEqual("crm", suite["value"])
        self.assertEqual("context", suite["origin"])

    def test_table_overrides_and_inheritance(self):
        manifest = etl_manifest.build("invoice", with_etl(FULL_SPEC), META)
        base, wide = manifest["tables"]
        self.assertEqual("deleteInsert",
                         base["fields"]["write_mode"]["value"])
        self.assertEqual("inherit", base["fields"]["write_mode"]["origin"])
        self.assertEqual("insert", wide["fields"]["write_mode"]["value"])
        self.assertEqual("agent", wide["fields"]["write_mode"]["origin"])
        # 每個 job 自足：沒覆寫的欄位也展開成實值
        self.assertEqual("8Gi", wide["fields"]["memory"]["value"])
        self.assertEqual("2", wide["fields"]["cpu"]["value"])
        self.assertEqual("mysql_erp", wide["fields"]["source_db"]["value"])

    def test_values_with_special_chars_are_quoted(self):
        manifest = etl_manifest.build(
            "invoice", with_etl({"schedule": "daily 02:00"}), META)
        data = yaml.safe_load(etl_manifest.to_yaml("invoice", 1, manifest))
        self.assertEqual("daily 02:00", data["schedule"])


class T_E4_Validation(unittest.TestCase):
    def test_valid_spec_passes(self):
        self.assertEqual([], etl_manifest.validate(with_etl(FULL_SPEC)))
        self.assertEqual([], design.validate_design_result(
            with_etl(FULL_SPEC)))

    def test_absent_section_is_fine(self):
        self.assertEqual([], etl_manifest.validate(RESULT))

    def test_type_and_name_errors(self):
        errors = etl_manifest.validate(with_etl({"owner": 5}))
        self.assertTrue(any("owner 必須是字串" in e for e in errors), errors)
        errors = etl_manifest.validate(with_etl({"unknown_key": "x"}))
        self.assertTrue(any("不允許的欄位" in e for e in errors), errors)
        errors = etl_manifest.validate(
            with_etl({"tables": [{"table": "no_such_table"}]}))
        self.assertTrue(any("不存在於 physical_design" in e for e in errors),
                        errors)
        errors = etl_manifest.validate(
            with_etl({"resources": {"cpu": 2}}))
        self.assertTrue(any("resources.cpu 必須是字串" in e for e in errors),
                        errors)
        errors = etl_manifest.validate({**RESULT, "etl_pipeline": "x"})
        self.assertTrue(any("必須是 object" in e for e in errors), errors)

    def test_errors_surface_through_design_validation(self):
        errors = design.validate_design_result(
            with_etl({"tables": [{"table": "ghost"}]}))
        self.assertTrue(any("不存在於 physical_design" in e for e in errors),
                        errors)


class T_E5_RenderedArtifact(unittest.TestCase):
    def setUp(self):
        self.hist = tempfile.mkdtemp()
        self.rep = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.hist)
        self.addCleanup(shutil.rmtree, self.rep)

    def _render(self, result):
        return design.render("invoice", result, CONTEXT, self.hist, self.rep)

    def test_file_written_and_parsable(self):
        info = self._render(with_etl(FULL_SPEC))
        path = os.path.join(self.rep, "invoice.etl.yaml")
        self.assertIn("invoice.etl.yaml", info["files"])
        data = yaml.safe_load(open(path, encoding="utf-8").read())
        self.assertEqual("etl_inv", data["id"])
        self.assertEqual("Billing Suite", data["product_suite"])
        self.assertEqual(1, data["design_round"])

    def test_written_even_without_etl_section(self):
        self._render(RESULT)
        text = open(os.path.join(self.rep, "invoice.etl.yaml"),
                    encoding="utf-8").read()
        self.assertIn("TODO 待填", text)
        self.assertIsNone(yaml.safe_load(text)["owner"])

    def test_deterministic_bytes(self):
        self._render(with_etl(FULL_SPEC))
        first = open(os.path.join(self.rep, "invoice.etl.yaml"), "rb").read()
        self._render(with_etl(FULL_SPEC))
        self.assertEqual(first,
                         open(os.path.join(self.rep, "invoice.etl.yaml"),
                              "rb").read())

    def test_physical_design_reports_status(self):
        self._render(RESULT)
        physical = open(os.path.join(self.rep, "invoice.physical_design.md"),
                        encoding="utf-8").read()
        self.assertIn("## ETL Pipeline 建議檔", physical)
        self.assertIn("invoice.etl.yaml", physical)
        self.assertIn("⬅ 待填", physical)
        self.assertIn("| `invoice` |", physical)


class T_E6_AdvisoryOnly(unittest.TestCase):
    def test_etl_section_does_not_touch_design_ddl(self):
        plain = design.combined_ddl(RESULT)
        self.assertEqual(plain, design.combined_ddl(with_etl(FULL_SPEC)))
        # 跨表比對與關係推導同樣不受影響
        self.assertEqual(design.cross_table_checks(RESULT),
                         design.cross_table_checks(with_etl(FULL_SPEC)))
        self.assertEqual(design.all_relations(RESULT),
                         design.all_relations(with_etl(FULL_SPEC)))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""迭代問答（Q&A Loop）測試。

守的保證：
  Q1 answers.yaml 載入與壞檔降級（選填件永不擋）
  Q2 主題比對：措辭漂移仍算已解；表名前綴寬鬆比對
  Q3 收斂判定：待答／deferred／advisory 未補完／閘門 fail 四個維度
  Q4 三式報告呈現迭代區塊；JSON 有結構化 iteration 鍵
  Q5 硬邊界：有無 answers，閘門 findings 逐字相同（兩區邊界的延伸）
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import answers as answers_mod
from dataval.engine import load_config, validate
from dataval.model import Finding, ZONE_ADVISORY, ZONE_GATING
from dataval.report import to_json, to_markdown, to_html

CFG = os.path.join(ROOT, "config", "_engine", "default.yaml")
KW = dict(domain_root=os.path.join(ROOT, "config"),
          rules_root=os.path.join(ROOT, "config", "Common", "knowhow_py"),
          config_dir=os.path.join(ROOT, "config"),
          production_root=os.path.join(ROOT, "production"))


def _llm_question(check_id: str, target: str, message: str) -> Finding:
    return Finding(check_id, "concept", "info", target, message,
                   severity="info", source="llm", zone=ZONE_ADVISORY)


class T_Q1_AnswersLoading(unittest.TestCase):
    def _write(self, text: str) -> str:
        tmp = tempfile.NamedTemporaryFile(
            "w", suffix=".yaml", delete=False, encoding="utf-8")
        tmp.write(text)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_valid_file(self):
        path = self._write(
            "iteration: 3\n"
            "answers:\n"
            "  - id: CONCEPT.SUBJECT@orders\n"
            "    answer: 一列一張訂單\n"
            "  - id: SKILL.x@t\n"
            "    status: deferred\n")
        data, problems = answers_mod.load_answers(path)
        self.assertEqual([], problems)
        self.assertEqual(3, data["iteration"])
        self.assertEqual(2, len(data["answers"]))
        self.assertEqual("answered", data["answers"][0]["status"])
        self.assertEqual("semantic", data["answers"][0]["kind"])

    def test_broken_yaml_is_skipped_not_fatal(self):
        data, problems = answers_mod.load_answers(self._write("answers: [unclosed"))
        self.assertIsNone(data)
        self.assertTrue(problems and "整份略過" in problems[0])

    def test_bad_entries_skipped_with_problems(self):
        path = self._write(
            "answers:\n"
            "  - id: no_at_sign\n"
            "    answer: x\n"
            "  - id: OK.RULE@t\n"
            "    answer: ''\n"          # answered 但空答案
            "  - id: GOOD.RULE@t\n"
            "    answer: 有效答案\n")
        data, problems = answers_mod.load_answers(path)
        self.assertEqual(1, len(data["answers"]))
        self.assertEqual("GOOD.RULE@t", data["answers"][0]["id"])
        self.assertEqual(2, len(problems))

    def test_missing_file_is_silent(self):
        data, problems = answers_mod.load_answers(
            os.path.join(tempfile.gettempdir(), "no_such_answers.yaml"))
        self.assertIsNone(data)
        self.assertEqual([], problems)


class T_Q2_TopicMatching(unittest.TestCase):
    def test_exact_and_wording_drift(self):
        # 同主題、不同措辭 → 同一題（比對只看 check_id@target）
        self.assertTrue(answers_mod.topic_matches(
            "CONCEPT.SUBJECT@orders", "CONCEPT.SUBJECT", "orders"))

    def test_table_prefix_laxness(self):
        # 答表名可涵蓋欄位級提問；反之亦然
        self.assertTrue(answers_mod.topic_matches(
            "SKILL.naming_semantic@subscription",
            "SKILL.naming_semantic", "subscription.start_dt"))
        self.assertTrue(answers_mod.topic_matches(
            "SKILL.naming_semantic@subscription.start_dt",
            "SKILL.naming_semantic", "subscription"))

    def test_no_cross_rule_or_cross_table_match(self):
        self.assertFalse(answers_mod.topic_matches(
            "CONCEPT.SUBJECT@orders", "NAME.SEMANTIC", "orders"))
        self.assertFalse(answers_mod.topic_matches(
            "CONCEPT.SUBJECT@orders", "CONCEPT.SUBJECT", "billing_event"))


class T_Q3_Convergence(unittest.TestCase):
    def _answers(self, *entries):
        return {"iteration": 2, "answers": list(entries)}

    def _entry(self, topic_id, status="answered", answer="答"):
        return {"id": topic_id, "question": "", "answer": answer,
                "kind": "semantic", "status": status, "applied_to": ""}

    def test_open_questions_block_convergence(self):
        findings = [_llm_question("CONCEPT.SUBJECT", "orders", "粒度是什麼?")]
        it = answers_mod.iteration_summary(findings, None)
        self.assertFalse(it["converged"])
        self.assertEqual(1, it["blockers"]["open_questions"])

    def test_answered_and_compliant_converges(self):
        findings = [_llm_question("CONCEPT.SUBJECT", "orders", "粒度是什麼?")]
        it = answers_mod.iteration_summary(
            findings, self._answers(self._entry("CONCEPT.SUBJECT@orders")))
        self.assertTrue(it["converged"])
        self.assertEqual(0, it["blockers"]["open_questions"])
        self.assertEqual(2, it["round"])

    def test_deferred_does_not_block_but_is_listed(self):
        findings = [_llm_question("CONCEPT.SUBJECT", "orders", "粒度?")]
        it = answers_mod.iteration_summary(
            findings, self._answers(
                self._entry("CONCEPT.SUBJECT@orders", status="deferred",
                            answer="")))
        self.assertTrue(it["converged"])
        self.assertEqual(1, len(it["deferred"]))

    def test_gating_fail_blocks_convergence(self):
        findings = [Finding("SKILL.x", "structural", "fail", "t", "壞了",
                            severity="error", source="skill", zone=ZONE_GATING)]
        it = answers_mod.iteration_summary(findings, None)
        self.assertFalse(it["converged"])
        self.assertEqual(1, it["blockers"]["gating_fails"])

    def test_pending_advisory_blocks_convergence(self):
        findings = [Finding("CONCEPT.SUBJECT", "concept", "skipped", "(schema)",
                            "未設定 LLM，略過主體性概念層。", severity="info",
                            source="llm", zone=ZONE_ADVISORY)]
        it = answers_mod.iteration_summary(findings, None)
        self.assertFalse(it["converged"])
        self.assertTrue(it["advisory_pending"])

    def test_empty_result_markers_are_not_questions(self):
        findings = [_llm_question("SKILL.x", "(schema)",
                                  "語意卡控「x」未發現建議。")]
        self.assertEqual([], answers_mod.question_topics(findings))

    def test_draft_yaml_roundtrip(self):
        findings = [_llm_question("CONCEPT.SUBJECT", "orders", '粒度"是"什麼?')]
        it = answers_mod.iteration_summary(findings, None)
        text = answers_mod.draft_yaml(it, "orders")
        import yaml
        parsed = yaml.safe_load(text)
        self.assertEqual(1, len(parsed["open_questions"]))
        self.assertEqual("CONCEPT.SUBJECT@orders",
                         parsed["open_questions"][0]["id"])

    def test_clarified_text_only_answered(self):
        text = answers_mod.clarified_text(self._answers(
            self._entry("A.B@t"), self._entry("C.D@t", status="deferred")))
        self.assertIn("A.B@t", text)
        self.assertNotIn("C.D@t", text)


class T_Q4_ReportRendering(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = load_config(CFG)
        with open(os.path.join(ROOT, "input", "order", "order.sql"),
                  encoding="utf-8") as f:
            cls.ddl = f.read()

    def test_iteration_in_all_three_reports(self):
        answers = {"iteration": 2, "answers": [
            {"id": "CONCEPT.SUBJECT@orders", "question": "粒度?",
             "answer": "一列一張訂單", "kind": "semantic",
             "status": "answered", "applied_to": ""}]}
        _, findings, meta = validate(self.ddl, self.cfg, domains=[],
                                     answers=answers, **KW)
        self.assertIn("iteration", meta)
        self.assertEqual(2, meta["iteration"]["round"])
        md = to_markdown(findings, meta)
        self.assertIn("迭代收斂", md)
        self.assertIn("CONCEPT.SUBJECT@orders", md)
        self.assertIn("迭代收斂", to_html(findings, meta))
        payload = json.loads(to_json(findings, meta))
        self.assertEqual(2, payload["iteration"]["round"])


class T_Q5_GatingInvariance(unittest.TestCase):
    """answers.yaml 是 Phase 1 的顧問區輸入：閘門 findings 必須逐字不變。"""

    def test_gating_findings_identical_with_and_without_answers(self):
        cfg = load_config(CFG)
        with open(os.path.join(ROOT, "input", "subscription",
                               "subscription.sql"), encoding="utf-8") as f:
            ddl = f.read()
        answers = {"iteration": 3, "answers": [
            {"id": "CONCEPT.SUBJECT@subscription", "question": "q",
             "answer": "a", "kind": "semantic", "status": "answered",
             "applied_to": ""}]}
        _, without_answers, _ = validate(ddl, cfg, domains=[], **KW)
        _, with_answers, _ = validate(ddl, cfg, domains=[], answers=answers, **KW)
        gate = lambda fs: [f.to_dict() for f in fs if f.zone == ZONE_GATING]
        self.assertEqual(gate(without_answers), gate(with_answers))


if __name__ == "__main__":
    unittest.main()

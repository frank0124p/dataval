#!/usr/bin/env python3
"""迭代歷史（iterations/<名>/）的守門測試。

守的保證：
  H1 每輪快照：answered/proposed/deferred 留痕、內容相同不改寫（位元組穩定）
  H2 input 變更追蹤：vs 前一輪的變更行數；首輪 baseline None
  H3 初版↔終版差異：diff 與行數、截斷標記；第 1 輪回 None
  H4 報告呈現：md 有「本輪 input 變更」與「初版↔終版」；html 卡片可摺疊
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import iterations
from dataval.report import iteration_lines, to_html


def _iter_meta(**over):
    base = {"round": 2, "max_rounds": 5, "converged": False,
            "advisory_pending": False,
            "blockers": {"open_questions": 0, "proposed_unverified": 0,
                         "gating_fails": 0},
            "open": [], "proposed": [], "answered": [], "deferred": [],
            "answers_file": "", "answers_problems": []}
    base.update(over)
    return base


class T_H1_Snapshot(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)

    def test_round_records_answer_ids_and_is_stable(self):
        it = _iter_meta(answered=[{"id": "A.B@t"}], proposed=[{"id": "C.D@t"}],
                        deferred=[{"id": "E.F@t"}])
        path = iterations.record_round(self.root, "s", 1, {"s.sql": "x"}, it,
                                       {"compliant": True, "fails": 0})
        with open(path, "rb") as f:
            before = f.read()
        stamp = os.path.getmtime(path)
        iterations.record_round(self.root, "s", 1, {"s.sql": "x"}, it,
                                {"compliant": True, "fails": 0})
        with open(path, "rb") as f:
            self.assertEqual(before, f.read())
        self.assertEqual(stamp, os.path.getmtime(path))
        import json
        data = json.load(open(path, encoding="utf-8"))
        self.assertEqual(["A.B@t"], data["answers_state"]["answered"])
        self.assertEqual(["C.D@t"], data["answers_state"]["proposed"])
        history = open(os.path.join(self.root, "s", "HISTORY.md"),
                       encoding="utf-8").read()
        self.assertIn("第 1 輪", history)
        self.assertIn("A.B@t", history)


class T_H2_InputChanges(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        iterations.record_round(
            self.root, "s", 1,
            {"s.sql": "line1\nline2\n", "context.md": "ctx\n"},
            _iter_meta(round=1), {"compliant": False, "fails": 2})

    def test_first_round_has_no_baseline(self):
        changes = iterations.input_changes(self.root, "s", 1, {"s.sql": "x"})
        self.assertIsNone(changes["baseline_round"])

    def test_changes_vs_previous_round(self):
        changes = iterations.input_changes(
            self.root, "s", 2,
            {"s.sql": "line1\nline2 modified\nline3\n",
             "context.md": "ctx\n", "answers.yaml": "answers: []\n"})
        self.assertEqual(1, changes["baseline_round"])
        by_file = {f["file"]: f for f in changes["files"]}
        self.assertEqual("changed", by_file["s.sql"]["status"])
        self.assertEqual(2, by_file["s.sql"]["added"])
        self.assertEqual(1, by_file["s.sql"]["removed"])
        self.assertEqual("unchanged", by_file["context.md"]["status"])
        self.assertEqual("added", by_file["answers.yaml"]["status"])


class T_H3_FirstLast(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root)
        iterations.record_round(self.root, "s", 1, {"s.sql": "v1\n"},
                                _iter_meta(round=1),
                                {"compliant": False, "fails": 1})

    def test_diff_first_to_current(self):
        fl = iterations.first_last_diff(self.root, "s", 3, {"s.sql": "v3\n"})
        self.assertEqual((1, 3), (fl["first_round"], fl["last_round"]))
        f = fl["files"][0]
        self.assertEqual("changed", f["status"])
        self.assertIn("-v1", f["diff"])
        self.assertIn("+v3", f["diff"])

    def test_round_one_returns_none(self):
        self.assertIsNone(
            iterations.first_last_diff(self.root, "s", 1, {"s.sql": "v1\n"}))

    def test_long_diff_truncated(self):
        current = "\n".join(f"line{i}" for i in range(300)) + "\n"
        fl = iterations.first_last_diff(self.root, "s", 2, {"s.sql": current})
        f = fl["files"][0]
        self.assertTrue(f["truncated"])
        self.assertLessEqual(len(f["diff"].splitlines()),
                             iterations.DIFF_MAX_LINES)


class T_H4_Rendering(unittest.TestCase):
    def test_md_shows_changes_and_first_last(self):
        meta = {"iteration": _iter_meta(
            converged=True,
            input_changes={"baseline_round": 1, "files": [
                {"file": "s.sql", "status": "changed", "added": 3, "removed": 1},
                {"file": "context.md", "status": "unchanged"}]},
            first_last={"first_round": 1, "last_round": 3, "files": [
                {"file": "s.sql", "status": "changed", "added": 5, "removed": 2,
                 "diff": "-old\n+new", "truncated": False}]})}
        lines = "\n".join(iteration_lines(meta))
        self.assertIn("本輪 input 變更", lines)
        self.assertIn("`s.sql`：變更（+3／−1 行）", lines)
        self.assertIn("初版（第 1 輪）↔ 終版（第 3 輪）", lines)
        self.assertIn("```diff", lines)

    def test_html_cards_are_collapsible(self):
        html = to_html([], {"iteration": _iter_meta(),
                            "rule_coverage": {"loaded": [], "not_loaded": [],
                                              "rules_total": 0,
                                              "rules_loaded_count": 0,
                                              "empty_domains": []}})
        self.assertIn("toggleCard", html)
        self.assertIn('class="bsum collapsed"', html)   # 預設收合的卡片
        self.assertIn("bs-body", html)


if __name__ == "__main__":
    unittest.main()

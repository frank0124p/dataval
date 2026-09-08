#!/usr/bin/env python3
"""顧問區重跑判定（advisory_state.py）的守門測試。

整條流程最貴的一步是 agent 的 LLM（每個主題讀 ~24K 字元、寫 ~8K 字元）。
prompt 沒變的重跑不該再付一次這個成本——但「省」不能省到拿舊建議搭新報告。

守的保證：
  A1 沒有紀錄／沒有結果 → 一律要重補（保守）
  A2 prompt 位元組相同 ＋ 結果未被改動 → 可沿用
  A3 prompt 只要變一個字 → 立刻要重補
  A4 advisory_result.json 被改動過 → 要重補（結果與紀錄對不上）
  A5 stamp 壞掉／格式版本不同 → 要重補
  A6 stamp 內容確定性（沒變不改寫，位元組穩定）
"""
from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import advisory_state                                # noqa: E402

PROMPT = "## 你要做的事\n請針對下列 schema 產生語意建議。\n"
RESULT = '{"skills": {"name_semantic": []}}\n'


class AdvisoryState(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.name = "order"

    def _write_result(self, body=RESULT):
        with io.open(advisory_state.result_path(self.tmp, self.name), "w",
                     encoding="utf-8") as handle:
            handle.write(body)

    def _write_prompt(self, body=PROMPT):
        with io.open(advisory_state.prompt_path(self.tmp, self.name), "w",
                     encoding="utf-8") as handle:
            handle.write(body)

    # A1 --------------------------------------------------------------
    def test_no_result_means_rerun(self):
        ok, why = advisory_state.reusable(self.tmp, self.name, PROMPT)
        self.assertFalse(ok)
        self.assertIn("advisory_result.json", why)

    def test_result_without_stamp_means_rerun(self):
        self._write_result()
        ok, why = advisory_state.reusable(self.tmp, self.name, PROMPT)
        self.assertFalse(ok)
        self.assertIn("合併紀錄", why)

    # A2 --------------------------------------------------------------
    def test_identical_prompt_and_untouched_result_is_reusable(self):
        self._write_result()
        advisory_state.write_stamp(self.tmp, self.name, PROMPT)
        ok, why = advisory_state.reusable(self.tmp, self.name, PROMPT)
        self.assertTrue(ok, why)

    # A3 --------------------------------------------------------------
    def test_any_prompt_change_forces_a_rerun(self):
        self._write_result()
        advisory_state.write_stamp(self.tmp, self.name, PROMPT)
        for changed in (PROMPT + " ", PROMPT.replace("語意", "語義"), ""):
            ok, why = advisory_state.reusable(self.tmp, self.name, changed)
            self.assertFalse(ok, changed)
            self.assertIn("prompt 已變", why)

    # A4 --------------------------------------------------------------
    def test_edited_result_forces_a_rerun(self):
        self._write_result()
        advisory_state.write_stamp(self.tmp, self.name, PROMPT)
        self._write_result(RESULT.replace("{", "{ ", 1))
        ok, why = advisory_state.reusable(self.tmp, self.name, PROMPT)
        self.assertFalse(ok)
        self.assertIn("已被改動", why)

    def test_deleted_result_forces_a_rerun(self):
        self._write_result()
        advisory_state.write_stamp(self.tmp, self.name, PROMPT)
        os.unlink(advisory_state.result_path(self.tmp, self.name))
        self.assertFalse(advisory_state.reusable(self.tmp, self.name, PROMPT)[0])

    # A5 --------------------------------------------------------------
    def test_broken_or_outdated_stamp_forces_a_rerun(self):
        self._write_result()
        path = advisory_state.stamp_path(self.tmp, self.name)
        for body, hint in ((" not json", "合併紀錄"),
                           (json.dumps({"version": 999}), "格式已更新")):
            with io.open(path, "w", encoding="utf-8") as handle:
                handle.write(body)
            ok, why = advisory_state.reusable(self.tmp, self.name, PROMPT)
            self.assertFalse(ok)
            self.assertIn(hint, why)

    # A6 --------------------------------------------------------------
    def test_stamp_is_deterministic(self):
        self._write_result()
        advisory_state.write_stamp(self.tmp, self.name, PROMPT)
        path = advisory_state.stamp_path(self.tmp, self.name)
        first = io.open(path, encoding="utf-8").read()
        before = os.stat(path).st_mtime_ns
        advisory_state.write_stamp(self.tmp, self.name, PROMPT)
        self.assertEqual(first, io.open(path, encoding="utf-8").read())
        self.assertEqual(before, os.stat(path).st_mtime_ns)   # 沒變就不改寫

    def test_stamp_lives_next_to_the_other_govern_outputs(self):
        self.assertTrue(advisory_state.stamp_path("/x/govern_doc/order", "order")
                        .endswith("/govern_doc/order/order.advisory_state.json"))


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
"""指定 subject 過濾（run.py select_subjects）的守門測試。

守的保證：
  F1 名稱／資料夾路徑／檔名三種寫法都能點名同一 subject
  F2 只跑點名的、其餘不動；重複點名不重複跑
  F3 對不上的指定會回報（呼叫端以此擋下執行）；空指定＝全跑
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import run as R

DDLS = [os.path.join("input", "order", "order.sql"),
        os.path.join("input", "subscription", "subscription.sql")]


class SubjectFilterTest(unittest.TestCase):
    def test_empty_selection_runs_all(self):
        selected, unknown = R.select_subjects(DDLS, [])
        self.assertEqual(DDLS, selected)
        self.assertEqual([], unknown)

    def test_name_folder_and_file_forms(self):
        for form in ("order", "input/order", "input/order/", "order.sql",
                     "input/order/order.sql"):
            selected, unknown = R.select_subjects(DDLS, [form])
            self.assertEqual([DDLS[0]], selected, form)
            self.assertEqual([], unknown, form)

    def test_only_named_subjects_selected(self):
        selected, unknown = R.select_subjects(DDLS, ["subscription"])
        self.assertEqual([DDLS[1]], selected)
        self.assertEqual([], unknown)

    def test_duplicates_collapse(self):
        selected, _ = R.select_subjects(DDLS, ["order", "input/order"])
        self.assertEqual([DDLS[0]], selected)

    def test_unknown_reported(self):
        selected, unknown = R.select_subjects(DDLS, ["order", "nosuch"])
        self.assertEqual([DDLS[0]], selected)
        self.assertEqual(["nosuch"], unknown)


if __name__ == "__main__":
    unittest.main()

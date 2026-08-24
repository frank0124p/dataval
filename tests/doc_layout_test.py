#!/usr/bin/env python3
"""文件輸出佈局（docpaths.py）的守門測試。

守的保證：
  L1 路徑組法：design_doc/<subject>/ 與 govern_doc/<subject>/ 兩個根，
     文件在 subject 資料夾內 → 回專案根固定兩層（ROOT_PREFIX）
  L2 govern 產物：三式報告、輪次版、前置檢核、顧問 prompt、主體摘要
     全部落在 govern_doc/<subject>/；不再寫舊的扁平 reports/
  L3 design 產物：設計 prompt 與設計文件落在 design_doc/<subject>/；
     跨 subject 的素材索引審閱表放設計文件根
  L4 檔名保留 <subject>. 前綴（資料夾單獨拉出去仍看得出屬於誰）
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import docpaths                                    # noqa: E402

CONTEXT = """---
subject: 發票
domains: [CRM]
---
## 這個 data subject 是什麼
發票資料。
## 粒度（每張表一行代表什麼）
invoice 一行 = 一張發票。
"""


def run(args, doc_dir, extra=None):
    env = dict(os.environ, DATAVAL_DOC_DIR=doc_dir,
               DATAVAL_ITERATIONS_DIR=os.path.join(doc_dir, "iterations"),
               PYTHONDONTWRITEBYTECODE="1", **(extra or {}))
    return subprocess.run([sys.executable, os.path.join(ROOT, "run.py")] + args,
                          cwd=ROOT, env=env, text=True, capture_output=True,
                          check=False)


class T_L1_Paths(unittest.TestCase):
    def test_two_roots_per_subject(self):
        self.assertEqual(os.path.join("/r", "design_doc", "order"),
                         docpaths.design_dir("/r", "order", create=False))
        self.assertEqual(os.path.join("/r", "govern_doc", "order"),
                         docpaths.govern_dir("/r", "order", create=False))

    def test_root_prefix_matches_depth(self):
        # <root>/<doc>/<subject>/x.html → 專案根要往上兩層
        self.assertEqual("../../", docpaths.ROOT_PREFIX)
        deep = docpaths.design_dir("/r", "order", create=False)
        self.assertEqual("/r", os.path.normpath(
            os.path.join(deep, docpaths.ROOT_PREFIX)))

    def test_doc_root_env_precedence(self):
        keep = {k: os.environ.get(k)
                for k in ("DATAVAL_DOC_DIR", "DATAVAL_REPORT_DIR")}
        try:
            os.environ.pop("DATAVAL_DOC_DIR", None)
            os.environ.pop("DATAVAL_REPORT_DIR", None)
            self.assertEqual("/here", docpaths.doc_root("/here"))
            os.environ["DATAVAL_REPORT_DIR"] = "/legacy"   # 舊名仍相容
            self.assertEqual("/legacy", docpaths.doc_root("/here"))
            os.environ["DATAVAL_DOC_DIR"] = "/new"         # 新名優先
            self.assertEqual("/new", docpaths.doc_root("/here"))
        finally:
            for k, v in keep.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v


class T_L2_GovernOutputs(unittest.TestCase):
    def test_outputs_live_in_subject_folder(self):
        with tempfile.TemporaryDirectory() as docs:
            result = run(["order"], docs)
            self.assertIn("govern_doc/order/order.report.html", result.stdout)
            folder = os.path.join(docs, "govern_doc", "order")
            for fname in ("order.report.md", "order.report.json",
                          "order.report.html", "order.round_1.report.md",
                          "order.precheck.md", "order.advisory_prompt.md",
                          "order.subject_summary.md"):
                self.assertTrue(os.path.isfile(os.path.join(folder, fname)),
                                fname)
            # 舊的扁平 reports/ 不再產生
            self.assertFalse(os.path.isdir(os.path.join(docs, "reports")))
            # 報告連回 config 的相對連結跟著多一層
            html = open(os.path.join(folder, "order.report.html"),
                        encoding="utf-8").read()
            self.assertIn('href="../../config/', html)
            self.assertNotIn('href="../config/', html)


class T_L3_DesignOutputs(unittest.TestCase):
    def test_design_prompt_and_index_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            docs = os.path.join(tmp, "docs")
            folder = os.path.join(tmp, "input", "invoice")
            os.makedirs(folder)
            with open(os.path.join(folder, "context.md"), "w",
                      encoding="utf-8") as f:
                f.write(CONTEXT)
            run(["invoice"], docs,
                {"DATAVAL_INPUT_DIR": os.path.join(tmp, "input")})
            self.assertTrue(os.path.isfile(os.path.join(
                docs, "design_doc", "invoice", "invoice.design_prompt.md")))
            # 跨 subject 的素材索引審閱表在設計文件根，不進任何 subject
            self.assertTrue(os.path.isfile(os.path.join(
                docs, "design_doc", "design_index_review.md")))
            self.assertFalse(os.path.isdir(
                os.path.join(docs, "govern_doc", "invoice")))


if __name__ == "__main__":
    unittest.main()

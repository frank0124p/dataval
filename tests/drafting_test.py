"""規則起草（drafts/）流程的守門測試。

守的保證：
  D1 未接 LLM → 產出 prompt 檔＋台帳紀錄，不產草稿本體
  D2 已接 LLM → 直接產出草稿本體
  D3 adopt：lint 通過才搬進 knowhow，履歷記 adopted 與去向
  D4 adopt：lint 失敗 → 留在 drafts、不進 knowhow
  D5 草稿標記 NEEDS_PY → 拒絕 adopt（超出宣告式能力應走 knowhow_py）
"""
import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import drafting  # noqa: E402

GOOD_DRAFT = """---
id: {rid}
category: structural
enforcement: blocking
---

# 測試規則

## 目的
測試。

## 適用情境
全部表。

## 違反後果
無。

## 修正建議
無。

## 卡控

```check
require: has_column x
```
"""


class FakeLLM:
    def complete(self, system, user):
        return GOOD_DRAFT.format(rid="llm_rule")


def lint_ok(path):
    return []


def lint_bad(path):
    return ["缺少必要章節 ## 目的"]


class DraftCase(unittest.TestCase):
    def setUp(self):
        self.drafts = tempfile.mkdtemp()
        self.domain_root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.drafts)
        self.addCleanup(shutil.rmtree, self.domain_root)


class T_D1_NoLLM(DraftCase):
    def test_prompt_file_and_ledger(self):
        out, mode = drafting.create_draft(
            self.drafts, "SCM", "gating", "r1", "需求", llm=None)
        self.assertEqual("prompt", mode)
        self.assertTrue(out.endswith("r1.prompt.md"))
        self.assertFalse(os.path.isfile(os.path.join(self.drafts, "r1.md")))
        meta = drafting.load_meta(self.drafts, "r1")
        self.assertEqual(("pending", "agent"),
                         (meta["status"], meta["source"]))
        with open(os.path.join(self.drafts, "LOG.md"), encoding="utf-8") as f:
            self.assertIn("起草 `r1`", f.read())


class T_D2_WithLLM(DraftCase):
    def test_llm_writes_draft_body(self):
        out, mode = drafting.create_draft(
            self.drafts, "SCM", "gating", "llm_rule", "需求", llm=FakeLLM())
        self.assertEqual("llm", mode)
        self.assertTrue(out.endswith("llm_rule.md"))
        self.assertEqual("llm",
                         drafting.load_meta(self.drafts, "llm_rule")["source"])


class T_D3_AdoptSuccess(DraftCase):
    def test_moves_and_records(self):
        drafting.create_draft(self.drafts, "SCM", "gating", "r2", "x", llm=None)
        with open(os.path.join(self.drafts, "r2.md"), "w",
                  encoding="utf-8") as f:
            f.write(GOOD_DRAFT.format(rid="r2"))
        dest = drafting.adopt_draft(self.drafts, self.domain_root, "r2",
                                    lint_ok)
        self.assertTrue(os.path.isfile(dest))
        self.assertIn(os.path.join("SCM", "knowhow", "gating"), dest)
        self.assertFalse(os.path.isfile(os.path.join(self.drafts, "r2.md")))
        meta = drafting.load_meta(self.drafts, "r2")
        self.assertEqual("adopted", meta["status"])
        self.assertIn("SCM/knowhow/gating/r2.md", meta["adopted_to"])


class T_D4_AdoptLintFail(DraftCase):
    def test_stays_in_drafts(self):
        drafting.create_draft(self.drafts, "SCM", "gating", "r3", "x", llm=None)
        with open(os.path.join(self.drafts, "r3.md"), "w",
                  encoding="utf-8") as f:
            f.write(GOOD_DRAFT.format(rid="r3"))
        with self.assertRaises(SystemExit) as ctx:
            drafting.adopt_draft(self.drafts, self.domain_root, "r3", lint_bad)
        self.assertIn("lint", str(ctx.exception))
        self.assertTrue(os.path.isfile(os.path.join(self.drafts, "r3.md")))
        self.assertEqual("pending",
                         drafting.load_meta(self.drafts, "r3")["status"])


class T_D5_NeedsPyRefused(DraftCase):
    def test_declarative_limit_is_respected(self):
        drafting.create_draft(self.drafts, "SCM", "gating", "r4", "x", llm=None)
        with open(os.path.join(self.drafts, "r4.md"), "w",
                  encoding="utf-8") as f:
            f.write(GOOD_DRAFT.format(rid="r4")
                    + "\n<!-- NEEDS_PY: 需跨表比對 -->\n")
        with self.assertRaises(SystemExit) as ctx:
            drafting.adopt_draft(self.drafts, self.domain_root, "r4", lint_ok)
        self.assertIn("NEEDS_PY", str(ctx.exception))


if __name__ == "__main__":
    unittest.main(verbosity=2)

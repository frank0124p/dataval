#!/usr/bin/env python3
"""建議 DDL 組建（proposal）的守門測試。

守的保證：
  P1 從參考模型組建：join 鍵推導（PK／共同 _id／推不出留 TODO）、
     寬表 DDL、欄名衝突消歧、input 未涵蓋的表列示
  P2 對比：建議欄位的 input 落點、input 獨有欄位
  P3 邊界：無錨點回 None；確定性（同輸入同輸出）；建議值＝顧問區 info
  P4 迭代紀錄：round_<N>.proposal.md 存檔、演進偵測
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval import iterations, proposal
from dataval.parser import parse_ddl


def write(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


ER_MD = """# 模型
```mermaid
erDiagram
    customer ||--o{ orders : "下單"
    orders ||--o{ order_items : "明細"
    customer {
        UInt64 customer_id PK
        String customer_name
    }
    orders {
        UInt64 order_id PK
        UInt64 customer_id
        DateTime('UTC') created_at
    }
    order_items {
        UInt64 order_item_id PK
        UInt64 order_id
        UInt32 quantity
    }
}
```
""".replace("}\n```", "```")   # 保守處理，內容以 fence 內為準

DDL = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x', "
       "customer_id UInt64 COMMENT 'y', created_at DateTime('UTC') COMMENT 'z',"
       "extra_note String COMMENT 'e') "
       "ENGINE=MergeTree() PRIMARY KEY (order_id) ORDER BY (order_id);")


class ProposalTest(unittest.TestCase):
    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.cfg)
        write(os.path.join(self.cfg, "CRM", "erd", "core.md"), ER_MD)

    def _build(self, ddl=DDL):
        return proposal.build(parse_ddl(ddl), self.cfg, ["CRM"])

    def test_join_keys_inferred_from_pk(self):
        p = self._build()
        self.assertEqual("orders", p["base_table"])
        self.assertIn("orders.customer_id = customer.customer_id", p["join_sql"])
        self.assertIn("orders.order_id = order_items.order_id", p["join_sql"])
        self.assertNotIn("TODO", p["join_sql"])

    def test_wide_ddl_with_conflict_disambiguation(self):
        p = self._build()
        self.assertIn("CREATE TABLE orders_wide", p["proposed_ddl"])
        # customer.customer_id 與 orders.customer_id 衝突 → 表前綴消歧
        self.assertIn("customer_customer_id", p["proposed_ddl"])
        self.assertIn("ORDER BY (order_id)", p["proposed_ddl"])
        self.assertIn("來源 order_items.quantity", p["proposed_ddl"])

    def test_not_in_input_listed(self):
        p = self._build()
        self.assertEqual(["customer", "order_items"], p["not_in_input"])

    def test_comparison_and_input_only(self):
        p = self._build()
        by_col = {c["column"]: c for c in p["comparison"]}
        self.assertEqual(["orders"], by_col["order_id"]["in_input"])
        self.assertEqual([], by_col["customer_name"]["in_input"])  # input 未包含
        input_only = {(c["table"], c["column"]) for c in p["input_only"]}
        self.assertIn(("orders", "extra_note"), input_only)

    def test_no_anchor_returns_none(self):
        ddl = ("CREATE TABLE unrelated (x UInt64 COMMENT 'x') "
               "ENGINE=MergeTree() ORDER BY (x);")
        self.assertIsNone(self._build(ddl))

    def test_deterministic(self):
        self.assertEqual(self._build(), self._build())

    def test_todo_when_no_key_derivable(self):
        write(os.path.join(self.cfg, "CRM", "erd", "core.md"),
              "# m\n```mermaid\nerDiagram\n  a ||--o{ b : \"關\"\n```\n")
        ddl = ("CREATE TABLE a (x UInt64 COMMENT 'x') "
               "ENGINE=MergeTree() ORDER BY (x);")
        p = proposal.build(parse_ddl(ddl), self.cfg, ["CRM"])
        self.assertIn("TODO", p["join_sql"])

    def test_proposal_evolution_diff(self):
        """演進 diff：首輪 baseline None；變更時列 SQL/DDL unified diff。"""
        hist = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, hist)
        it = {"answered": [], "proposed": [], "deferred": [],
              "converged": False, "advisory_pending": False, "blockers": {}}
        p1 = self._build()
        ev1 = iterations.proposal_evolution(hist, "s", 1, p1)
        self.assertIsNone(ev1["baseline_round"])
        iterations.record_round(hist, "s", 1, {"s.sql": "v"}, it,
                                {"compliant": True, "fails": 0}, proposal=p1)
        # 第 2 輪:模型不變 → 不變
        ev2 = iterations.proposal_evolution(hist, "s", 2, self._build())
        self.assertEqual(1, ev2["baseline_round"])
        self.assertFalse(ev2["changed"])
        # 模型演進 → diff
        write(os.path.join(self.cfg, "CRM", "erd", "core.md"),
              ER_MD.replace("UInt32 quantity",
                            "UInt32 quantity\n        Decimal(18,2) unit_price"))
        p2 = self._build()
        ev3 = iterations.proposal_evolution(hist, "s", 2, p2)
        self.assertTrue(ev3["changed"])
        self.assertIn("+  order_items.unit_price", ev3["sql_diff"])
        self.assertIn("+  unit_price Decimal(18,2)", ev3["ddl_diff"])
        # proposal.md 收錄演進段
        p2["evolution"] = ev3
        path = iterations.write_proposal_md(hist, "s", 2, p2)
        text = open(path, encoding="utf-8").read()
        self.assertIn("與第 1 輪建議相比", text)
        self.assertIn("```diff", text)

    def test_nm_relationship_warns(self):
        """N:M 關係（兩端皆多）：join 註記警示＋warnings 清單。"""
        write(os.path.join(self.cfg, "CRM", "erd", "core.md"),
              "# m\n```mermaid\nerDiagram\n"
              "    orders }o--o{ tags : \"多對多\"\n"
              "    orders {\n        UInt64 order_id PK\n    }\n"
              "    tags {\n        UInt64 tag_id PK\n    }\n```\n")
        ddl = ("CREATE TABLE orders (order_id UInt64 COMMENT 'x') "
               "ENGINE=MergeTree() PRIMARY KEY (order_id) ORDER BY (order_id);")
        p = proposal.build(parse_ddl(ddl), self.cfg, ["CRM"])
        self.assertEqual(1, len(p["warnings"]))
        self.assertIn("N:M", p["warnings"][0])
        self.assertIn("N:M", p["join_sql"])

    def test_prune_after_promotion_keeps_latest_round(self):
        hist = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, hist)
        it = {"answered": [], "proposed": [], "deferred": [],
              "converged": True, "advisory_pending": False, "blockers": {}}
        for n in (1, 2, 3):
            iterations.record_round(hist, "s", n, {"s.sql": f"v{n}"}, it,
                                    {"compliant": True, "fails": 0})
            iterations.write_delta_md(hist, "s", n, dict(it, findings_delta={},
                                                         input_changes={}))
            iterations.write_proposal_files(hist, "s", n, self._build())
        kept, removed = iterations.prune_after_promotion(hist, "s")
        self.assertEqual(3, kept)
        remaining = sorted(os.listdir(os.path.join(hist, "s")))
        self.assertIn("HISTORY.md", remaining)
        self.assertIn("round_3.json", remaining)
        self.assertIn("round_3.join.sql", remaining)
        self.assertIn("round_3.future.ddl", remaining)
        self.assertNotIn("round_1.json", remaining)
        self.assertNotIn("round_2.delta.md", remaining)
        self.assertNotIn("round_1.join.sql", remaining)
        self.assertNotIn("round_2.future.ddl", remaining)
        self.assertGreater(removed, 0)

    def test_proposal_split_files_round_in_name(self):
        """拆檔：round_<N>.join.sql／round_<N>.future.ddl，檔名與檔頭標輪次。"""
        hist = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, hist)
        paths = iterations.write_proposal_files(hist, "s", 2, self._build())
        sql_path, ddl_path = paths
        self.assertTrue(sql_path.endswith(os.path.join("s", "round_2.join.sql")))
        self.assertTrue(ddl_path.endswith(os.path.join("s", "round_2.future.ddl")))
        sql_text = open(sql_path, encoding="utf-8").read()
        self.assertIn("第 2 輪建議 Join SQL", sql_text)
        self.assertIn("FROM orders", sql_text)
        self.assertNotIn("CREATE TABLE", sql_text)   # 只含 Join SQL
        ddl_text = open(ddl_path, encoding="utf-8").read()
        self.assertIn("第 2 輪未來 DDL", ddl_text)
        self.assertIn("CREATE TABLE orders_wide", ddl_text)
        # 無建議 → 不產檔
        self.assertIsNone(iterations.write_proposal_files(hist, "s", 2, None))
        # proposal.md 指向拆檔
        md_path = iterations.write_proposal_md(hist, "s", 2, self._build())
        md_text = open(md_path, encoding="utf-8").read()
        self.assertIn("round_2.join.sql", md_text)
        self.assertIn("round_2.future.ddl", md_text)

    def test_report_outputs_round_stamped_filenames(self):
        """reports/：固定入口 <名>.report.* 之外，另存 <名>.round_<N>.report.*。"""
        import run as R
        outdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outdir)
        html = R.write_report_outputs(
            "s", 2, {".report.md": "m", ".report.json": "{}",
                     ".report.html": "<x>"}, report_dir=outdir)
        files = sorted(os.listdir(outdir))
        self.assertEqual(["s.report.html", "s.report.json", "s.report.md",
                          "s.round_2.report.html", "s.round_2.report.json",
                          "s.round_2.report.md"], files)
        self.assertTrue(html.endswith("s.round_2.report.html"))
        self.assertEqual("m", open(os.path.join(outdir, "s.round_2.report.md"),
                                   encoding="utf-8").read())

    def test_report_outputs_include_proposal_files(self):
        """有建議 DDL 時，建議 Join SQL／未來 DDL 隨報告拆檔進 reports/。"""
        import run as R
        outdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, outdir)
        R.write_report_outputs(
            "s", 3, {".report.md": "m"}, report_dir=outdir,
            proposal=self._build())
        files = sorted(os.listdir(outdir))
        self.assertIn("s.round_3.join.sql", files)
        self.assertIn("s.round_3.future.ddl", files)
        sql_text = open(os.path.join(outdir, "s.round_3.join.sql"),
                        encoding="utf-8").read()
        self.assertIn("第 3 輪建議 Join SQL", sql_text)
        self.assertIn("FROM orders", sql_text)
        self.assertIn("iterations/s/round_3.proposal.md", sql_text)
        ddl_text = open(os.path.join(outdir, "s.round_3.future.ddl"),
                        encoding="utf-8").read()
        self.assertIn("第 3 輪未來 DDL", ddl_text)
        self.assertIn("CREATE TABLE orders_wide", ddl_text)
        # 無建議 → 不產拆檔
        R.write_report_outputs("t", 1, {".report.md": "m"}, report_dir=outdir)
        self.assertNotIn("t.round_1.join.sql", sorted(os.listdir(outdir)))

    def test_report_header_shows_round(self):
        from dataval.report import to_markdown, to_html
        meta = {"iteration": {"round": 3, "max_rounds": 5}}
        md = to_markdown([], meta)
        self.assertIn("第 3 輪迭代", md.splitlines()[0])
        self.assertIn("第 3／5 輪迭代報告", md)
        html = to_html([], meta)
        self.assertIn("<title>資料設計驗證報告 — 第 3 輪迭代</title>", html)
        self.assertIn("第 3／5 輪", html)

    def test_round_proposal_md_and_evolution(self):
        hist = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, hist)
        p1 = self._build()
        it = {"answered": [], "proposed": [], "deferred": [],
              "converged": False, "advisory_pending": False, "blockers": {}}
        iterations.record_round(hist, "s", 1, {"s.sql": "v1"}, it,
                                {"compliant": True, "fails": 0}, proposal=p1)
        path = iterations.write_proposal_md(hist, "s", 1, p1)
        text = open(path, encoding="utf-8").read()
        self.assertIn("第 1 輪建議 DDL", text)
        self.assertIn("CREATE TABLE orders_wide", text)
        # 第 2 輪參考模型演進 → HISTORY 標「已演進」
        write(os.path.join(self.cfg, "CRM", "erd", "core.md"),
              ER_MD.replace("UInt32 quantity", "UInt32 quantity\n        "
                            "Decimal(18,2) unit_price"))
        p2 = self._build()
        iterations.record_round(hist, "s", 2, {"s.sql": "v1"}, it,
                                {"compliant": True, "fails": 0}, proposal=p2)
        history = open(os.path.join(hist, "s", "HISTORY.md"),
                       encoding="utf-8").read()
        self.assertIn("已演進", history)


if __name__ == "__main__":
    unittest.main()

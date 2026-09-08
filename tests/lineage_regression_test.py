#!/usr/bin/env python3
"""Lineage 回歸測試 — 七個情境守 `LINEAGE.*` 系列規則。

守的保證（每個情境一張最小 DDL，直接呼叫 validate()，零 subprocess）：

  L1 宣告有效     宣告的跨域上游存在、欄位存在、型別相容 → 合規
  L2 型別不符     宣告 String ← 上游 UInt64 → `LINEAGE.TYPE_COMPATIBILITY` 擋下
  L3 區域循環     A 宣告上游是 B、B 宣告上游是 A → `LINEAGE.CYCLE` 擋下
  L4 推論關聯     沒宣告但有共用 `*_id` → source=suggested，只提示不擋
  L5 找不到關聯   單表、沒有共用鍵 → 沒有任何關聯，且明說「沒有足夠可靠」
  L6 明確無上游   宣告 upstream: [] → source=declared，明說「已明確宣告無上游」
  L7 ER 建議      Mermaid ER 有關係但沒宣告 → source=er-diagram，
                  `LINEAGE.ER_SUGGESTION` 進顧問區（不擋）

這組原本綁在 `examples/lineage/` 的 fixture 與 legacy 輸入模式；資料夾移除後
改成自帶輸入，測的行為完全一樣。跨域上游（L1／L2）仍實檢 repo 的
`production/CRM/dim_customer`——那是這條規則真正要驗的東西。
"""
from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dataval.engine import load_config, validate                  # noqa: E402
from dataval.er_diagram import parse_mermaid                      # noqa: E402
from dataval.report import checking_rule_summary, summarize       # noqa: E402

CONFIG = os.path.join(ROOT, "config", "_engine", "default.yaml")
CONFIG_DIR = os.path.join(ROOT, "config")
PRODUCTION = os.path.join(ROOT, "production")

AUDIT = ("created_at DateTime('UTC') COMMENT '建立時間', "
         "updated_at DateTime('UTC') COMMENT '更新時間'")


def ddl(name: str, columns: str, order_by: str) -> str:
    return (f"CREATE TABLE {name} ({columns}, {AUDIT}) "
            f"ENGINE = MergeTree() ORDER BY ({order_by});")


def check(ddl_text, *, lineage=None, business_keys=None, samples=None,
          domains=None, er=None):
    """跑一次驗證，回傳 (summary, checking rule 摘要, lineage meta, meta)。"""
    schema, findings, meta = validate(
        ddl_text, load_config(CONFIG),
        sample_data=samples, business_keys=business_keys or {},
        # lineage_spec 的外殼與 relations.yaml 轉換後的形狀一致
        lineage_spec={"lineage": lineage} if lineage is not None else None,
        domains=domains or [],
        er_diagram=parse_mermaid(er) if er else None,
        domain_root=CONFIG_DIR,
        rules_root=os.path.join(CONFIG_DIR, "Common", "knowhow_py"),
        config_dir=CONFIG_DIR, production_root=PRODUCTION)
    return (summarize(findings),
            checking_rule_summary(findings, meta.get("checking_rule_ids_loaded")),
            meta.get("lineage") or {}, meta)


#: L1／L2 共用：宣告上游是 CRM 正式區的 dim_customer.customer_id
CRM_UPSTREAM = {
    "upstream": [{"domain": "CRM", "table": "dim_customer"}],
    "columns": {"customer_id": "CRM.dim_customer.customer_id"},
}


class LineageRegression(unittest.TestCase):

    def test_L1_declared_upstream_that_resolves_is_compliant(self):
        summary, rules, lineage, _ = check(
            ddl("customer_snapshot",
                "snapshot_id UInt64 COMMENT '快照唯一識別', "
                "customer_id UInt64 COMMENT '客戶唯一識別'", "snapshot_id"),
            lineage={"customer_snapshot": CRM_UPSTREAM},
            business_keys={"customer_snapshot": ["snapshot_id"]},
            domains=["CRM"],
            samples={"customer_snapshot": [
                {"snapshot_id": 1001, "customer_id": 42,
                 "created_at": "2026-07-01T00:00:00Z",
                 "updated_at": "2026-07-01T00:00:00Z"}]})
        self.assertTrue(summary["compliant"])
        self.assertEqual(lineage["source"], "declared")
        # 真的走到正式區把上游查出來了，不是「沒東西可查所以過」
        self.assertEqual(lineage["relationships"], [{
            "source": "CRM.dim_customer", "target": "customer_snapshot",
            "kind": "declared",
            "columns": [{"source": "customer_id", "target": "customer_id"}]}])
        for rule in ("LINEAGE.METADATA", "LINEAGE.UPSTREAM_EXISTS",
                     "LINEAGE.COLUMN_EXISTS", "LINEAGE.TYPE_COMPATIBILITY",
                     "LINEAGE.CYCLE", "LINEAGE.DOMAIN_SCOPE"):
            self.assertIn(rule, rules["passed"], rule)

    def test_L2_declared_upstream_with_incompatible_type_is_blocked(self):
        # 上游 CRM.dim_customer.customer_id 是 UInt64，這裡刻意宣告成 String
        _, rules, _, _ = check(
            ddl("customer_export",
                "export_id UInt64 COMMENT '匯出批次唯一識別', "
                "customer_id String COMMENT '刻意使用錯誤型別的客戶識別'",
                "export_id"),
            lineage={"customer_export": CRM_UPSTREAM},
            business_keys={"customer_export": ["export_id"]},
            domains=["CRM"],
            samples={"customer_export": [
                {"export_id": 2001, "customer_id": "42",
                 "created_at": "2026-07-02T00:00:00Z",
                 "updated_at": "2026-07-02T00:00:00Z"}]})
        self.assertIn("LINEAGE.TYPE_COMPATIBILITY", rules["failed"])

    def test_L3_local_cycle_is_blocked(self):
        text = (ddl("staged_order", "order_id UInt64 COMMENT '訂單唯一識別'",
                    "order_id")
                + "\n"
                + ddl("order_summary", "order_id UInt64 COMMENT '訂單唯一識別'",
                      "order_id"))
        _, rules, _, _ = check(
            text,
            lineage={
                "staged_order": {
                    "upstream": [{"domain": "local", "table": "order_summary"}],
                    "columns": {"order_id": "local.order_summary.order_id"}},
                "order_summary": {
                    "upstream": [{"domain": "local", "table": "staged_order"}],
                    "columns": {"order_id": "local.staged_order.order_id"}},
            },
            business_keys={"staged_order": ["order_id"],
                           "order_summary": ["order_id"]})
        self.assertIn("LINEAGE.CYCLE", rules["failed"])

    def test_L4_shared_key_without_declaration_is_only_suggested(self):
        text = (ddl("customer_reference",
                    "customer_id UInt64 COMMENT '客戶唯一識別'", "customer_id")
                + "\n"
                + ddl("customer_order",
                      "order_id UInt64 COMMENT '訂單唯一識別', "
                      "customer_id UInt64 COMMENT '下單客戶識別'", "order_id"))
        summary, _, lineage, _ = check(
            text,
            business_keys={"customer_reference": ["customer_id"],
                           "customer_order": ["order_id"]})
        self.assertEqual(lineage["source"], "suggested")
        self.assertTrue(lineage["relationships"])
        # 推論只是建議——不得因為「猜到關聯」就把設計擋下來
        self.assertTrue(summary["compliant"])

    def test_L5_no_shared_key_yields_no_relationship_and_says_so(self):
        _, _, lineage, _ = check(
            ddl("audit_log",
                "log_key String COMMENT '日誌唯一識別', "
                "message String COMMENT '日誌內容'", "log_key"),
            business_keys={"audit_log": ["log_key"]})
        self.assertEqual(lineage["relationships"], [])
        self.assertIn("沒有足夠可靠", lineage["note"])

    def test_L6_explicitly_declaring_no_upstream_is_respected(self):
        # 宣告「我就是源頭」與「還沒宣告」是兩件事，報告必須分得出來
        _, _, lineage, _ = check(
            ddl("standalone_metric",
                "metric_key String COMMENT '指標唯一識別', "
                "metric_name String COMMENT '指標名稱'", "metric_key"),
            lineage={"standalone_metric": {"upstream": [], "columns": {}}},
            business_keys={"standalone_metric": ["metric_key"]})
        self.assertEqual(lineage["source"], "declared")
        self.assertIn("已明確宣告無上游", lineage["note"])

    def test_L7_er_diagram_relationship_becomes_an_advisory_suggestion(self):
        er = """erDiagram
  CUSTOMER_ER_SOURCE ||--o{ ORDER_ER_EVENT : places
  CUSTOMER_ER_SOURCE {
    UInt64 customer_id PK
    DateTime created_at
    DateTime updated_at
  }
  ORDER_ER_EVENT {
    UInt64 order_id PK
    UInt64 customer_id FK
    DateTime created_at
    DateTime updated_at
  }
"""
        text = (ddl("customer_er_source",
                    "customer_id UInt64 COMMENT '客戶唯一識別'", "customer_id")
                + "\n"
                + ddl("order_er_event",
                      "order_id UInt64 COMMENT '訂單唯一識別', "
                      "customer_id UInt64 COMMENT '下單客戶識別'", "order_id"))
        summary, rules, lineage, meta = check(
            text, er=er,
            business_keys={"customer_er_source": ["customer_id"],
                           "order_er_event": ["order_id"]})
        self.assertEqual(lineage["source"], "er-diagram")
        self.assertEqual(meta["er_diagram"]["relationship_count"], 1)
        # ER 只能是建議：進顧問區、不擋
        self.assertIn("LINEAGE.ER_SUGGESTION", rules["advisory"])
        self.assertTrue(summary["compliant"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

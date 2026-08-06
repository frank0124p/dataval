-- =============================================================
-- 參考範例：訂單（order）data subject —— DDL 一表一檔拆放
-- 主檔（本檔）：orders（訂單主表）；同資料夾 order_items.sql：訂單明細
-- 跨 domain 引用：orders.customer_id → CRM.dim_customer.customer_id
-- 本 DDL 依 Common 基線規則撰寫，示範「合格的提交長什麼樣」。
-- =============================================================

CREATE TABLE orders (
    order_id      UInt64                  COMMENT '訂單唯一識別碼（business key）',
    customer_id   UInt64                  COMMENT '下單客戶；權威在 CRM.dim_customer',
    status        LowCardinality(String)  COMMENT '訂單狀態：created/paid/shipped/cancelled',
    currency      LowCardinality(String)  COMMENT 'ISO 4217 幣別代碼，如 TWD/USD',
    total_amount  Decimal(18, 2)          COMMENT '訂單總金額（含稅，下單當下快照值）',
    ordered_at    DateTime('UTC')         COMMENT '下單時間（業務發生時間 event time）',
    cancelled_at  Nullable(DateTime('UTC')) COMMENT '取消時間；未取消為 NULL',
    created_at    DateTime('UTC')         COMMENT '資料建立時間（稽核欄位）',
    updated_at    DateTime('UTC')         COMMENT '資料更新時間（稽核欄位）'
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(ordered_at)
ORDER BY (order_id);

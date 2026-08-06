-- 訂單明細表（order data subject 的拆檔之一；主檔為 order.sql）

CREATE TABLE order_items (
    order_item_id UInt64                  COMMENT '訂單明細唯一識別碼（business key）',
    order_id      UInt64                  COMMENT '所屬訂單；N:1 對 orders',
    product_id    UInt64                  COMMENT '商品識別碼；權威在商品主檔',
    quantity      UInt32                  COMMENT '購買數量（單位：件）',
    unit_price    Decimal(18, 2)          COMMENT '成交單價（下單當下快照值，非商品主檔現價）',
    created_at    DateTime('UTC')         COMMENT '資料建立時間（稽核欄位）',
    updated_at    DateTime('UTC')         COMMENT '資料更新時間（稽核欄位）'
) ENGINE = MergeTree()
ORDER BY (order_item_id);

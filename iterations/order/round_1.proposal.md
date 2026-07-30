# 第 1 輪建議 DDL — order（自動組建，建議值）

基底表 `orders` · 涵蓋 entity：`orders`、`dim_customer`、`order_items`

⚠️ 參考模型有、input 尚未涵蓋：`dim_customer`

## 建議 Join SQL
```sql
SELECT
  orders.order_id,
  orders.customer_id,
  orders.status,
  orders.total_amount,
  orders.ordered_at,
  dim_customer.customer_id AS dim_customer_customer_id,
  dim_customer.customer_name,
  dim_customer.customer_tier,
  dim_customer.created_at,
  order_items.order_item_id,
  order_items.order_id AS order_items_order_id,
  order_items.product_id,
  order_items.quantity,
  order_items.unit_price
FROM orders
LEFT JOIN dim_customer ON orders.customer_id = dim_customer.customer_id  -- "客戶下訂單"
LEFT JOIN order_items ON orders.order_id = order_items.order_id  -- "訂單含明細"
```

## 未來 DDL（`orders_wide`）
```sql
CREATE TABLE orders_wide (
  order_id UInt64 COMMENT '來源 orders.order_id',
  customer_id UInt64 COMMENT '來源 orders.customer_id',
  status LowCardinality(String) COMMENT '來源 orders.status',
  total_amount Decimal(18,2) COMMENT '來源 orders.total_amount',
  ordered_at DateTime('UTC') COMMENT '來源 orders.ordered_at',
  dim_customer_customer_id UInt64 COMMENT '來源 dim_customer.customer_id',
  customer_name String COMMENT '來源 dim_customer.customer_name',
  customer_tier LowCardinality(String) COMMENT '來源 dim_customer.customer_tier',
  created_at DateTime('UTC') COMMENT '來源 dim_customer.created_at',
  order_item_id UInt64 COMMENT '來源 order_items.order_item_id',
  order_items_order_id UInt64 COMMENT '來源 order_items.order_id',
  product_id UInt64 COMMENT '來源 order_items.product_id',
  quantity UInt32 COMMENT '來源 order_items.quantity',
  unit_price Decimal(18,2) COMMENT '來源 order_items.unit_price'
) ENGINE = MergeTree
ORDER BY (order_id)
COMMENT '訂單頭事實表。一列代表一張已成立的訂單，承載訂單層級的業務事實'
```

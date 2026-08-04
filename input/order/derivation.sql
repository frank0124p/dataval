-- order 寬表的衍生 SQL（這張寬表實際上是怎麼 join 出來的）。
-- 起點：第 1 輪建議 Join SQL（iterations/order/round_1.join.sql）——
-- 請以實際使用的組合 SQL 取代本檔內容後重跑 run.py。
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

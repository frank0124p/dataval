# 迭代歷史 — order

每輪由 run.py／merge_advisory.py 自動記錄；完整輸入快照見同輪 `round_<N>.json`。

## 第 1 輪 ｜ ❌ 未收斂
- 待答 0、待驗證 20、閘門 fail 0
- 代填待驗證：`CONCEPT.SUBJECT@derivation.sql`、`CONCEPT.SUBJECT@dim_customer`、`CONCEPT.SUBJECT@order_items`、`CONCEPT.SUBJECT@orders`、`CONCEPT.SUBJECT@order（未登錄主體候選）`、`NAME.SEMANTIC@order_items.product_id`、`NAME.SEMANTIC@order_items.unit_price`、`NAME.SEMANTIC@orders.ordered_at / orders.created_at / orders.updated_at`、`NAME.SEMANTIC@orders.status`、`NAME.SEMANTIC@orders.total_amount`、`SKILL.best_practice_semantic@order_items`、`SKILL.best_practice_semantic@orders.ordered_at`、`SKILL.best_practice_semantic@orders.total_amount`、`SKILL.naming_semantic@order_items.quantity`、`SKILL.naming_semantic@orders.customer_id / dim_customer.customer_id`、`SKILL.naming_semantic@orders.ordered_at`、`SKILL.ssot_semantic@derivation.sql（customer_name、customer_tier）`、`SKILL.ssot_semantic@order_items.product_id`、`SKILL.ssot_semantic@order_items.unit_price`、`SKILL.ssot_semantic@orders.currency`

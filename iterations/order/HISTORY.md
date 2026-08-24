# 迭代歷史 — order

每輪由 run.py／merge_advisory.py 自動記錄；完整輸入快照見同輪 `round_<N>.json`。

## 第 1 輪 ｜ ❌ 未收斂
- 待答 0、待驗證 20、閘門 fail 0
- 代填待驗證：`CONCEPT.SUBJECT@derivation.sql`、`CONCEPT.SUBJECT@dim_customer`、`CONCEPT.SUBJECT@order_items`、`CONCEPT.SUBJECT@orders`、`CONCEPT.SUBJECT@order（未登錄主體候選）`、`NAME.SEMANTIC@order_items.product_id`、`NAME.SEMANTIC@order_items.unit_price`、`NAME.SEMANTIC@orders.ordered_at / orders.created_at / orders.updated_at`、`NAME.SEMANTIC@orders.status`、`NAME.SEMANTIC@orders.total_amount`、`SKILL.best_practice_semantic@order_items`、`SKILL.best_practice_semantic@orders.ordered_at`、`SKILL.best_practice_semantic@orders.total_amount`、`SKILL.naming_semantic@order_items.quantity`、`SKILL.naming_semantic@orders.customer_id / dim_customer.customer_id`、`SKILL.naming_semantic@orders.ordered_at`、`SKILL.ssot_semantic@derivation.sql（customer_name、customer_tier）`、`SKILL.ssot_semantic@order_items.product_id`、`SKILL.ssot_semantic@order_items.unit_price`、`SKILL.ssot_semantic@orders.currency`

## 第 2 輪 ｜ ❌ 未收斂
- 待答 0、待驗證 13、閘門 fail 0
- 已答：`CONCEPT.SUBJECT@derivation.sql`、`CONCEPT.SUBJECT@dim_customer`、`CONCEPT.SUBJECT@orders`、`NAME.SEMANTIC@order_items.unit_price`、`NAME.SEMANTIC@orders.ordered_at / orders.created_at / orders.updated_at`、`NAME.SEMANTIC@orders.status`、`NAME.SEMANTIC@orders.total_amount`、`SKILL.best_practice_semantic@order_items`、`SKILL.best_practice_semantic@orders.total_amount`、`SKILL.naming_semantic@order_items.quantity`、`SKILL.naming_semantic@orders.ordered_at`、`SKILL.ssot_semantic@derivation.sql（customer_name、customer_tier）`、`SKILL.ssot_semantic@order_items.product_id`、`SKILL.ssot_semantic@order_items.unit_price`、`SKILL.ssot_semantic@orders.currency`
- 代填待驗證：`CONCEPT.SUBJECT@order_items`、`CONCEPT.SUBJECT@orders（取消單的母體語意）`、`CONCEPT.SUBJECT@orders（部分退貨／換貨）`、`CONCEPT.SUBJECT@order（未登錄主體候選）`、`NAME.SEMANTIC@order_items.order_item_id`、`NAME.SEMANTIC@order_items.product_id`、`NAME.SEMANTIC@orders.cancelled_at`、`SKILL.best_practice_semantic@orders.cancelled_at（Nullable 欄位策略）`、`SKILL.best_practice_semantic@orders.ordered_at`、`SKILL.naming_semantic@orders / order_items（表名與 SSOT 主體名）`、`SKILL.naming_semantic@orders.customer_id / dim_customer.customer_id`、`SKILL.ssot_semantic@orders.currency（換算基準）`、`SKILL.ssot_semantic@orders.total_amount（對外請款金額）`
- input 變更（vs 第 1 輪）：answers.yaml
- 發現變化（vs 第 1 輪）：新增 8、解決 15、狀態變化 0（明細：round_2.delta.md）
- 建議 DDL（orders_wide）：不變（round_2.proposal.md；拆檔 round_2.join.sql／round_2.future.ddl）

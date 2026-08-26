# 迭代歷史 — subscription

每輪由 run.py／merge_advisory.py 自動記錄；完整輸入快照見同輪 `round_<N>.json`。

## 第 1 輪 ｜ ❌ 未收斂
- 待答 0、待驗證 17、閘門 fail 11
- 代填待驗證：`CONCEPT.SUBJECT@billing_event`、`CONCEPT.SUBJECT@dim_customer`、`CONCEPT.SUBJECT@subscription`、`NAME.SEMANTIC@billing_event.amount`、`NAME.SEMANTIC@dim_customer`、`NAME.SEMANTIC@subscription.MonthlyPrice`、`NAME.SEMANTIC@subscription.MonthlyPrice / billing_event.amount`、`SKILL.best_practice_semantic@billing_event`、`SKILL.best_practice_semantic@dim_customer`、`SKILL.best_practice_semantic@subscription`、`SKILL.naming_semantic@billing_event.occurred_at`、`SKILL.naming_semantic@subscription.customer_id / dim_customer.customer_id / billing_event.customer_id`、`SKILL.naming_semantic@subscription.started_at / subscription.created_at`、`SKILL.ssot_semantic@dim_customer（本主體） vs CRM 客戶主檔`、`SKILL.ssot_semantic@subscription.MonthlyPrice`、`SKILL.ssot_semantic@subscription.MonthlyPrice vs billing_event.amount`、`SKILL.ssot_semantic@subscription.customer_email`

## 第 2 輪 ｜ ❌ 未收斂
- 待答 0、待驗證 18、閘門 fail 11
- 已答：`CONCEPT.SUBJECT@dim_customer`、`NAME.SEMANTIC@billing_event.amount`、`NAME.SEMANTIC@dim_customer`、`NAME.SEMANTIC@subscription.MonthlyPrice`、`NAME.SEMANTIC@subscription.MonthlyPrice / billing_event.amount`、`SKILL.best_practice_semantic@dim_customer`、`SKILL.naming_semantic@billing_event.occurred_at`、`SKILL.ssot_semantic@subscription.MonthlyPrice`、`SKILL.ssot_semantic@subscription.MonthlyPrice vs billing_event.amount`
- 代填待驗證：`CONCEPT.SUBJECT@billing_event`、`CONCEPT.SUBJECT@subscription`、`CONCEPT.SUBJECT@subscription（方案變更）`、`NAME.SEMANTIC@subscription.subscription_id`、`PRODUCTION.REUSE@subscription`、`SKILL.best_practice_semantic@billing_event`、`SKILL.best_practice_semantic@billing_event（遲到資料與封帳）`、`SKILL.best_practice_semantic@subscription`、`SKILL.naming_semantic@billing_event.event_id`、`SKILL.naming_semantic@subscription.customer_id / dim_customer.customer_id / billing_event.customer_id`、`SKILL.naming_semantic@subscription.started_at / subscription.created_at`、`SKILL.production_reuse_semantic@billing_event.customer_id ↔ CRM.orders.customer_id`、`SKILL.production_reuse_semantic@dim_customer（本地表） ↔ CRM.dim_customer（正式區）`、`SKILL.production_reuse_semantic@subscription ↔ CRM.orders（主體邊界）`、`SKILL.ssot_semantic@billing_event.amount（幣別）`、`SKILL.ssot_semantic@dim_customer.customer_tier（過渡期權威）`、`SKILL.ssot_semantic@dim_customer（本主體） vs CRM 客戶主檔`、`SKILL.ssot_semantic@subscription.customer_email`
- input 變更（vs 第 1 輪）：answers.yaml
- 發現變化（vs 第 1 輪）：新增 13、解決 16、狀態變化 0（明細：round_2.delta.md）

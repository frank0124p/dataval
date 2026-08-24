# 迭代歷史 — subscription

每輪由 run.py／merge_advisory.py 自動記錄；完整輸入快照見同輪 `round_<N>.json`。

## 第 1 輪 ｜ ❌ 未收斂
- 待答 0、待驗證 17、閘門 fail 11
- 代填待驗證：`CONCEPT.SUBJECT@billing_event`、`CONCEPT.SUBJECT@dim_customer`、`CONCEPT.SUBJECT@subscription`、`NAME.SEMANTIC@billing_event.amount`、`NAME.SEMANTIC@dim_customer`、`NAME.SEMANTIC@subscription.MonthlyPrice`、`NAME.SEMANTIC@subscription.MonthlyPrice / billing_event.amount`、`SKILL.best_practice_semantic@billing_event`、`SKILL.best_practice_semantic@dim_customer`、`SKILL.best_practice_semantic@subscription`、`SKILL.naming_semantic@billing_event.occurred_at`、`SKILL.naming_semantic@subscription.customer_id / dim_customer.customer_id / billing_event.customer_id`、`SKILL.naming_semantic@subscription.started_at / subscription.created_at`、`SKILL.ssot_semantic@dim_customer（本主體） vs CRM 客戶主檔`、`SKILL.ssot_semantic@subscription.MonthlyPrice`、`SKILL.ssot_semantic@subscription.MonthlyPrice vs billing_event.amount`、`SKILL.ssot_semantic@subscription.customer_email`

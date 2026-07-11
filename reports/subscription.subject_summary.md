# Data Subject 摘要

- 合規狀態：❌ 未通過（修正後再納入正式區）
- 關聯 domain：common
- 表數：3

## 結構摘要
- **dim_customer**（business key：customer_id；sorting key：customer_id；PRIMARY KEY：（無））：customer_id:int, customer_name:string, customer_email:string, customer_tier:string, created_at:datetime, updated_at:datetime
- **subscription**（business key：subscription_id；sorting key：subscription_id；PRIMARY KEY：（無））：subscription_id:int, customer_id:string, customer_email:string, MonthlyPrice:float, started_at:datetime, created_at:datetime
- **billing_event**（business key：event_id；sorting key：event_id；PRIMARY KEY：（無））：event_id:int, customer_id:int, amount:float, occurred_at:datetime

## 用途
（未接 LLM：用途說明待補。可由 agent 用其 LLM 依結構摘要補完。）

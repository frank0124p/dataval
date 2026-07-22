---
subject: 訂閱
business_keys:
  dim_customer: [customer_id]
  subscription: [subscription_id]
  billing_event: [event_id]
---

## 這個 data subject 是什麼

新增的 subscription 主體，跨 CRM 與 billing 兩個 domain。
本案例**刻意保留多個違規**（camelCase 欄名、金額用 Float、join key 型別
與編碼不一致、跨表重複承載 customer_email），作為工具檢核能力的示範。

## 粒度（每張表一行代表什麼）

- `dim_customer`：一行 = 一位客戶
- `subscription`：一行 = 一筆訂閱（同一客戶可有多筆，含歷史訂閱）
- `billing_event`：一行 = 一次計費事件

## 用途與消費者

訂閱營收分析與客戶帳務對帳。

## 上下游來源

客戶主檔的權威在 CRM；本主體的 subscription 與 billing_event
由訂閱服務寫入。

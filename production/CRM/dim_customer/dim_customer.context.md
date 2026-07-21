---
subject: 客戶主檔
domains: [CRM]
business_keys:
  dim_customer: [customer_id]
---

## 這個 data subject 是什麼

CRM 領域的客戶主檔，是全公司客戶識別與客戶屬性
（姓名、email）的單一真實源（SSOT）。

## 粒度（每張表一行代表什麼）

- `dim_customer`：一行 = 一位客戶。客戶屬性變更為原地更新
  （updated_at 標記），不保留歷史版本。

## 用途與消費者

所有需要客戶屬性的下游 subject 一律以 customer_id 引用本表，
不得自行複製客戶屬性。

## 上下游來源

上游為 CRM 系統的客戶註冊與維護流程；無資料面上游表。

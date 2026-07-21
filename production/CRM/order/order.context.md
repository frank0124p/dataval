---
subject: 訂單
domains: [CRM]
business_keys:
  orders: [order_id]
  order_items: [order_item_id]
---

## 這個 data subject 是什麼

電商平台的訂單資料，承載「客戶在什麼時間、以什麼幣別與金額、購買了哪些商品」
的交易事實。是營收報表、對帳與出貨流程的共同上游。

## 粒度（每張表一行代表什麼）

- `orders`：一行 = **一張訂單**（一次結帳行為）。同一客戶多次下單會產生多行。
  訂單金額 `total_amount` 是明細加總的快照值，取消訂單仍保留該行
  （以 `cancelled_at` 標記），不做物理刪除。
- `order_items`：一行 = **一張訂單中的一個商品項**。同一商品在同一訂單內
  只會有一行（數量以 `quantity` 表達，不以多行表達）。

## 用途與消費者

- 營收日報／月報（financial analytics）：依 `ordered_at` 彙總 `total_amount`
- 對帳（billing）：以 `order_id` 對應金流平台的交易紀錄
- 出貨（fulfillment）：依 `status` 驅動撿貨與物流

## 上下游來源

- 上游：結帳服務（checkout service）在交易完成時寫入
- `customer_id` 引用 CRM 領域的客戶主檔（`CRM.dim_customer`），
  本主體**只存鍵不存客戶屬性**（姓名、email 的權威在 CRM）
- `unit_price` 是下單當下的**快照**，允許與商品主檔現價不同（刻意反正規化）
- 下游：資料倉儲的營收 fact 表、BI 報表

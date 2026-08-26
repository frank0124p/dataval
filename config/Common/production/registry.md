---
index_summary: 正式區已核准 2 個 data subject、3 張表——設計新表前先讀，能複用就不要重造
index_stage: [L, P]
index_required: true
---

# 正式區資產（production assets）

> 🤖 **自動生成，勿手改**：每次 `run.py` 起跑時依 `production/` 重新產生。
> 這裡列的是**已核准上線**的 data subject——設計新表前先看這份，
> 同一件事已經有人做過就直接引用，不要在自己的主體裡重造一份。

| Domain | Subject | 表 | 用途 |
|---|---|---|---|
| `CRM` | `dim_customer` | `dim_customer` | CRM 領域的客戶主檔，是全公司客戶識別與客戶屬性 |
| `CRM` | `order` | `orders`、`order_items` | 電商平台的訂單資料，承載「客戶在什麼時間、以什麼幣別與金額、購買了哪些商品」 |

## 每個資產的三件輸入（要看細節就開這些檔）

### `CRM.dim_customer`
- DDL：`production/CRM/dim_customer/dim_customer.sql`
- 表間關聯：`production/CRM/dim_customer/dim_customer.relations.yaml`
- 語意描述：`production/CRM/dim_customer/dim_customer.context.md`

### `CRM.order`
- DDL：`production/CRM/order/order.sql`
- 表間關聯：`production/CRM/order/order.relations.yaml`
- 語意描述：`production/CRM/order/order.context.md`

## 怎麼引用（確定性寫法）

- `relations.yaml`：`to: <DOMAIN>.<表>.<欄>`（三段式）
- 設計稿欄位：`source: <DOMAIN>.<表>.<欄>`——工具會自動衍生對來源表的
  reference 關係，不必手填 table_relations
- **引用只存鍵**：外部權威的屬性（名稱、等級…）不要複製進自己的表

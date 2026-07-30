# CRM 領域核心參考模型

entity 欄位定義同時供三處使用：ERD.ENTITY_REFERENCE（DDL 欄位對照）、
建議 DDL 組建（Join SQL＋未來寬表）、LINEAGE.ER_SUGGESTION（關係比對）。

```mermaid
erDiagram
    dim_customer ||--o{ orders : "客戶下訂單"
    orders ||--o{ order_items : "訂單含明細"
    dim_customer {
        UInt64 customer_id PK
        String customer_name
        LowCardinality(String) customer_tier
        DateTime('UTC') created_at
    }
    orders {
        UInt64 order_id PK
        UInt64 customer_id
        LowCardinality(String) status
        Decimal(18,2) total_amount
        DateTime('UTC') ordered_at
    }
    order_items {
        UInt64 order_item_id PK
        UInt64 order_id
        UInt64 product_id
        UInt32 quantity
        Decimal(18,2) unit_price
    }
```

# DDL 個案設定

`input/` 只放待檢查的 DDL。每份 DDL 可在這裡放一份同名 YAML：

```text
input/order.sql
config/cases/order.yaml
```

一份 YAML 集中管理五種可選資訊：

```yaml
context: 訂單資料表的業務情境
domains: [CRM]

business_keys:
  orders: [order_id]

lineage:
  orders:
    upstream:
      - domain: CRM
        table: dim_customer
    columns:
      customer_id: CRM.dim_customer.customer_id

sample_data:
  orders:
    - order_id: 1001
      customer_id: 42
```

- `context`：供顧問區理解業務用途。
- `domains`：決定載入哪些 `config/domain/<domain>/` 與
  `production/<domain>/`；`Common` 永遠載入。
- `business_keys`：治理意義的唯一鍵，不會從 ClickHouse `ORDER BY` 或
  `PRIMARY KEY` 猜測。
- `lineage`：明確的設計期資料流向，可進閘門檢查。
- `sample_data`：少量資料，只用於型別與跨表規則檢查。

所有欄位都可省略；完整起始範本見 [`_template.yaml`](_template.yaml)。若 DDL 與設定不在
本專案預設位置，可用 `DATAVAL_CASE_CONFIG_DIR` 指定這個資料夾。

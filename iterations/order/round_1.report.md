# 資料設計驗證報告 — 第 1 輪迭代
_第 1 輪迭代存檔_<br>
**🔁 第 1／5 輪迭代報告**<br>
**判定：✅ 合規**（會擋項目 0）<br>
通過 35 · 警告 5 · 失敗 0 · 略過 6 · 提示 6<br>
閘門區 42 項 · 顧問區 10 項<br>
> 方言 clickhouse · 表數 2 · 載入 skill 27 條
> 驗證 bundle `40fd80bcb6140494`（含規則、validator 與依賴版本）

## Checking rule ID 摘要
- ❌ 擋下：（無）
- ⚠️ 警告：`SKILL.naming_glossary`、`SKILL.ssot_authority`、`SSOT.UNREGISTERED_SUBJECT`
- ✅ 通過：`BUSINESS_KEY.METADATA`、`DOMAIN.SCOPE`、`ERD.ENTITY_REFERENCE`、`LINEAGE.COLUMN_EXISTS`、`LINEAGE.CYCLE`、`LINEAGE.DOMAIN_SCOPE`、`LINEAGE.METADATA`、`LINEAGE.TYPE_COMPATIBILITY`、`LINEAGE.UPSTREAM_EXISTS`、`PRODGRAPH.CARDINALITY_CONFLICT`、`PRODGRAPH.CYCLE`、`PRODUCTION.NAMING_CONSISTENCY`、`PRODUCTION.SCOPE`、`SKILL.bp_datetime_timezone`、`SKILL.bp_lowcardinality_status`、`SKILL.bp_money_decimal`、`SKILL.bp_no_float`、`SKILL.naming_column_case`、`SKILL.naming_columns_commented`、`SKILL.naming_identifier_length`、`SKILL.naming_pk_suffix`、`SKILL.naming_reserved_words`、`SKILL.naming_table_snake_case`、`SKILL.no_future_event_time`、`SKILL.ssot_fact_duplication`、`SKILL.ssot_join_keys`、`SKILL.ssot_pii_amount_split`、`SKILL.structural_audit_columns`、`SKILL.structural_business_key`、`SKILL.structural_engine_mergetree`、`SKILL.structural_key_not_nullable`、`SKILL.structural_order_by`、`SKILL.structural_type_sample`
- ℹ️ 未實檢／略過：`SKILL.crm_baseline`、`SKILL.structural_fk_resolves`
- 💡 顧問：`CONCEPT.SUBJECT`、`ERD.TABLE_PURPOSE`、`FLOW.CONTEXT`、`PRODGRAPH.IMPACT`、`PROPOSAL.DDL`、`SKILL.best_practice_semantic`、`SKILL.naming_semantic`、`SKILL.ssot_semantic`

## 規則涵蓋清單
> 宣告域（context.md）：CRM · config 可用域：BLM、CRM、Common、FCM、PLM、SCM
> 涵蓋：載入並執行 **27** 條 ／ config 共 **40** 條

### ✅ 已載入並執行（27 條）
- `SKILL.crm_baseline`（CRM）→ ℹ️ 未實檢／略過 ｜ config/CRM/knowhow/gating/crm_baseline.md
- `SKILL.best_practice_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/best_practice_semantic.md
- `SKILL.bp_datetime_timezone`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/bp_datetime_timezone.md
- `SKILL.bp_lowcardinality_status`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/bp_lowcardinality_status.md
- `SKILL.bp_money_decimal`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/bp_money_decimal.md
- `SKILL.bp_no_float`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/bp_no_float.md
- `SKILL.naming_column_case`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_column_case.md
- `SKILL.naming_columns_commented`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_columns_commented.md
- `SKILL.naming_glossary`（Common）→ ⚠️ 警告 ｜ config/Common/knowhow/gating/naming_glossary.md
- `SKILL.naming_identifier_length`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_identifier_length.md
- `SKILL.naming_pk_suffix`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_pk_suffix.md
- `SKILL.naming_reserved_words`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_reserved_words.md
- `SKILL.naming_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/naming_semantic.md
- `SKILL.naming_table_snake_case`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_table_snake_case.md
- `SKILL.no_future_event_time`（Common）→ ✅ 通過 ｜ config/Common/knowhow_py/no_future_event_time.py
- `SKILL.ssot_authority`（Common）→ ⚠️ 警告 ｜ config/Common/knowhow_py/ssot_authority.py
- `SKILL.ssot_fact_duplication`（Common）→ ✅ 通過 ｜ config/Common/knowhow_py/ssot_fact_duplication.py
- `SKILL.ssot_join_keys`（Common）→ ✅ 通過 ｜ config/Common/knowhow_py/ssot_join_keys.py
- `SKILL.ssot_pii_amount_split`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/ssot_pii_amount_split.md
- `SKILL.ssot_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/ssot_semantic.md
- `SKILL.structural_audit_columns`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_audit_columns.md
- `SKILL.structural_business_key`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_business_key.md
- `SKILL.structural_engine_mergetree`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_engine_mergetree.md
- `SKILL.structural_fk_resolves`（Common）→ ℹ️ 未實檢／略過 ｜ config/Common/knowhow_py/structural_fk_resolves.py
- `SKILL.structural_key_not_nullable`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_key_not_nullable.md
- `SKILL.structural_order_by`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_order_by.md
- `SKILL.structural_type_sample`（Common）→ ✅ 通過 ｜ config/Common/knowhow_py/structural_type_sample.py

### ⏭️ 未載入：所屬域未在 context.md 宣告（13 條）
- **BLM**：`SKILL.blm_baseline`
- **FCM**：`SKILL.fcm_baseline`、`SKILL.fcm_master_data_semantic`
- **PLM**：`SKILL.plm_bom_needs_quantity`、`SKILL.plm_bom_structural_integrity`、`SKILL.plm_engineering_change`、`SKILL.plm_lifecycle_stage`、`SKILL.plm_part_master_baseline`、`SKILL.plm_revision_versioning`
- **SCM**：`SKILL.scm_grn_needs_po`、`SKILL.scm_po_needs_supplier`、`SKILL.scm_supplier_baseline`、`SKILL.scm_supply_semantic`
> 若這些域也應納入檢查，請在 context.md front-matter 的 `domains` 補上該域後重跑。

## 迭代收斂（第 1 輪／上限 5）
> 收斂條件：無待答問題 ＋ 閘門合規
> 目前：⏳ 顧問區尚未補完——待答題數要等補完後才能確定（閘門 fail 0 項）

### ✅ 已解（0）
（無）

### 📝 本輪 input 變更
（首輪——無前輪可比；本輪輸入已快照到 iterations/）

## 建議 DDL 對比（依參考模型自動組建；建議值，不影響判定）
> 基底表 `orders` · 涵蓋 entity：`orders`、`dim_customer`、`order_items` · 依據：CRM/erd/crm_core.md
> ⚠️ 參考模型有、但 input 尚未涵蓋的表：`dim_customer`
> 🧬 本輪為**首次產生**的建議。

### 建議 Join SQL
```sql
SELECT
  orders.order_id,
  orders.customer_id,
  orders.status,
  orders.total_amount,
  orders.ordered_at,
  dim_customer.customer_id AS dim_customer_customer_id,
  dim_customer.customer_name,
  dim_customer.customer_tier,
  dim_customer.created_at,
  order_items.order_item_id,
  order_items.order_id AS order_items_order_id,
  order_items.product_id,
  order_items.quantity,
  order_items.unit_price
FROM orders
LEFT JOIN dim_customer ON orders.customer_id = dim_customer.customer_id  -- "客戶下訂單"
LEFT JOIN order_items ON orders.order_id = order_items.order_id  -- "訂單含明細"
```

### 未來 DDL（建議：`orders_wide`）
```sql
CREATE TABLE orders_wide (
  order_id UInt64 COMMENT '來源 orders.order_id',
  customer_id UInt64 COMMENT '來源 orders.customer_id',
  status LowCardinality(String) COMMENT '來源 orders.status',
  total_amount Decimal(18,2) COMMENT '來源 orders.total_amount',
  ordered_at DateTime('UTC') COMMENT '來源 orders.ordered_at',
  dim_customer_customer_id UInt64 COMMENT '來源 dim_customer.customer_id',
  customer_name String COMMENT '來源 dim_customer.customer_name',
  customer_tier LowCardinality(String) COMMENT '來源 dim_customer.customer_tier',
  created_at DateTime('UTC') COMMENT '來源 dim_customer.created_at',
  order_item_id UInt64 COMMENT '來源 order_items.order_item_id',
  order_items_order_id UInt64 COMMENT '來源 order_items.order_id',
  product_id UInt64 COMMENT '來源 order_items.product_id',
  quantity UInt32 COMMENT '來源 order_items.quantity',
  unit_price Decimal(18,2) COMMENT '來源 order_items.unit_price'
) ENGINE = MergeTree
ORDER BY (order_id)
COMMENT '訂單頭事實表。一列代表一張已成立的訂單，承載訂單層級的業務事實'
```

### 與 input DDL 的逐欄對比
| 建議欄位 | 型別 | 來源 entity | input 落點 |
|---|---|---|---|
| `order_id` | UInt64 | `orders` | `order_items`、`orders` |
| `customer_id` | UInt64 | `orders` | `orders` |
| `status` | LowCardinality(String) | `orders` | `orders` |
| `total_amount` | Decimal(18,2) | `orders` | `orders` |
| `ordered_at` | DateTime('UTC') | `orders` | `orders` |
| `dim_customer_customer_id` | UInt64 | `dim_customer` | `orders` |
| `customer_name` | String | `dim_customer` | ❌ input 未包含 |
| `customer_tier` | LowCardinality(String) | `dim_customer` | ❌ input 未包含 |
| `created_at` | DateTime('UTC') | `dim_customer` | `order_items`、`orders` |
| `order_item_id` | UInt64 | `order_items` | `order_items` |
| `order_items_order_id` | UInt64 | `order_items` | `order_items`、`orders` |
| `product_id` | UInt64 | `order_items` | `order_items` |
| `quantity` | UInt32 | `order_items` | `order_items` |
| `unit_price` | Decimal(18,2) | `order_items` | `order_items` |

**input 獨有欄位（建議模型未涵蓋，4）**：
`orders.currency`、`orders.cancelled_at`、`orders.updated_at`、`order_items.updated_at`

## Lineage 關聯
> 關係來自 relations.yaml，並參照 ER diagram；兩者都是設計宣告，不代表已觀測到 runtime lineage。

| 來源 | 目標 | 欄位映射 | 性質 |
|---|---|---|---|
| `local.orders` | `order_items` | `order_id` → `order_id` | YAML 宣告＋ER 對應 |
| `CRM.dim_customer` | `orders` | `customer_id` → `customer_id` | YAML 明確宣告 |

## 本次卡控摘要（被哪些規則卡下來）

**警告（放行但需注意）：**
- `SKILL.naming_glossary` 命名對照詞彙字典 → order_items
- `SKILL.ssot_authority` 權威表在場檢視 → dim_customer、dim_product
- `SSOT.UNREGISTERED_SUBJECT` 未登錄主體候選 'order_item' → order_items、orders

## 結構（欄位／型別／約束）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⏭️ | 閘門 | `SKILL.crm_baseline` | `(schema)` | CRM 領域基線（範例佔位，請以實際 CRM 規範替換）：本次沒有符合適用範圍的表。 <br>_理由：示範 CRM 領域規則檔的放置位置與格式；此範例僅要求客戶主檔具備稽核欄位， 上線前應替換為真實領域規範。_ <br>_依據：config/CRM/knowhow/gating/crm_baseline.md_ | skill |
| ⏭️ | 閘門 | `SKILL.structural_fk_resolves` | `(schema)` | structural_fk_resolves：本次 schema 沒有可檢查的 FK。 <br>_依據：config/Common/knowhow_py/structural_fk_resolves.py_ | skill |
| ℹ️ | 顧問 | `ERD.TABLE_PURPOSE` | `order_items` | 參考模型記載此表用途（CRM/erd/tables/order_items.md）：訂單明細事實表。一列代表訂單內的一個品項（訂單 × 商品粒度），
記錄數量、單價與小計。必須以 order_id 掛回 orders；
商品屬性以 product_id 引用商品主檔，不得複製商品名稱等權威屬性。 請對照本次設計是否正確 reference 此表。 <br>_依據：config/<域>/erd/tables/<表名>.md（參考表用途）_ | rule |
| ℹ️ | 顧問 | `ERD.TABLE_PURPOSE` | `orders` | 參考模型記載此表用途（CRM/erd/tables/orders.md）：訂單頭事實表。一列代表一張已成立的訂單，承載訂單層級的業務事實
（下單客戶、成立時間、訂單狀態、總金額）。金額彙總的權威來源，
下游供營收日報與客服查詢使用。明細請放 order_items，不得在本表重複展開。 請對照本次設計是否正確 reference 此表。 <br>_依據：config/<域>/erd/tables/<表名>.md（參考表用途）_ | rule |
| ℹ️ | 顧問 | `FLOW.CONTEXT` | `order_items` | 此表位於 E2E 流程「訂單到營收」（共 4 站）；上游站點：orders；下游站點：營收日報。設計變更時請沿流程確認上下游影響。（依據：config/CRM/flows/order_to_revenue.md） <br>_依據：config/<域>/flows/*.md（E2E 流程）_ | rule |
| ℹ️ | 顧問 | `FLOW.CONTEXT` | `orders` | 此表位於 E2E 流程「訂單到營收」（共 4 站）；上游站點：結帳服務；下游站點：order_items。設計變更時請沿流程確認上下游影響。（依據：config/CRM/flows/order_to_revenue.md） <br>_依據：config/<域>/flows/*.md（E2E 流程）_ | rule |
| ℹ️ | 顧問 | `PROPOSAL.DDL` | `orders_wide` | 已依參考模型自動組建建議 Join SQL 與未來 DDL：基底 orders、涵蓋 3 個 entity（input 尚未涵蓋：['dim_customer']）。建議值，不影響判定；對比見報告「建議 DDL 對比」區塊。 <br>_依據：config/<域>/erd/*.md（參考模型自動組建；建議值，不影響判定）_ | rule |
| ✅ | 閘門 | `BUSINESS_KEY.METADATA` | `(schema)` | Business key metadata 已驗證：['order_items', 'orders']。 <br>_依據：input/<名>/context.md（front-matter business_keys）_ | rule |
| ✅ | 閘門 | `DOMAIN.SCOPE` | `(domains)` | Domain 範圍已明確：['CRM', 'Common']。 <br>_依據：input/<名>/context.md（front-matter domains）→ config/<域>/_ | rule |
| ✅ | 閘門 | `ERD.ENTITY_REFERENCE` | `order_items` | 參考模型 entity 欄位對照：5 欄全數存在。 <br>_理由：依據：CRM/erd/crm_core.md_ <br>_依據：config/<域>/erd/*.md（ER 參考模型 entity 欄位定義）對照本次 DDL_ | rule |
| ✅ | 閘門 | `ERD.ENTITY_REFERENCE` | `orders` | 參考模型 entity 欄位對照：5 欄全數存在。 <br>_理由：依據：CRM/erd/crm_core.md_ <br>_依據：config/<域>/erd/*.md（ER 參考模型 entity 欄位定義）對照本次 DDL_ | rule |
| ✅ | 閘門 | `SKILL.structural_audit_columns` | `2 表` | 表應有稽核欄位（created_at / updated_at）：2 表全數通過（orders、order_items） <br>_理由：稽核欄位支撐血緣追蹤與變更歷史。_ <br>_依據：config/Common/knowhow/gating/structural_audit_columns.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_business_key` | `2 表` | 表必須有 Business Key：2 表全數通過（orders、order_items） <br>_理由：每張表需要穩定的業務識別鍵，才能被正確引用、合併與去重。 ClickHouse ORDER BY 只是物理排序鍵，不等於業務唯一性。_ <br>_依據：config/Common/knowhow/gating/structural_business_key.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_engine_mergetree` | `2 表` | 明細表引擎須為 MergeTree 系列（ClickHouse）：2 表全數通過（orders、order_items） <br>_理由：明細層資料應使用 MergeTree 家族引擎（MergeTree / ReplacingMergeTree 等）。_ <br>_依據：config/Common/knowhow/gating/structural_engine_mergetree.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_key_not_nullable` | `2 表` | 鍵欄位不可為 Nullable：2 表全數通過（orders、order_items） <br>_理由：主鍵／排序鍵為 Nullable 會破壞合併與去重語意，並帶來額外標記欄位開銷。_ <br>_依據：config/Common/knowhow/gating/structural_key_not_nullable.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_order_by` | `2 表` | 表必須有 ORDER BY（ClickHouse）：2 表全數通過（orders、order_items） <br>_理由：MergeTree 家族依 ORDER BY 建立稀疏索引，缺少它等於放棄索引。_ <br>_依據：config/Common/knowhow/gating/structural_order_by.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_type_sample` | `(sample)` | 型別對樣本檢查：135 個樣本值全數通過。 <br>_依據：config/Common/knowhow_py/structural_type_sample.py_ | skill |

## 命名規則

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⚠️ | 閘門 | `SKILL.naming_glossary` | `order_items` | 命名對照詞彙字典：欄位用到別名：order_item_id（'item'） <br>**期望** 使用正規詞 ｜ **實際** order_item_id 用了別名 'item' <br>**修法** order_item_id 改用 'product' <br>_理由：欄位命名應使用公司認可的標準詞，避免縮寫與同義異名造成理解成本與整合困難。 此規則對照各 domain naming 資料夾的詞彙表（config/*/naming/*.md，md 表格； Common 恆載入、domain 疊加）做檢查，比寫一堆正則更易維護。_ <br>_依據：config/Common/knowhow/gating/naming_glossary.md ＋ config/<域>/naming/*.md（詞彙字典）_ | skill |
| ⏭️ | 顧問 | `SKILL.naming_semantic` | `(skill)` | 未接 LLM，略過語意卡控「跨表命名語意一致性（語意）」。 <br>_依據：config/Common/knowhow/advisory/naming_semantic.md_ | llm |
| ✅ | 閘門 | `PRODUCTION.NAMING_CONSISTENCY` | `(production)` | 新設計命名與 production 基準一致。 <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `SKILL.naming_column_case` | `2 表` | 欄位名須為 snake_case 全小寫：2 表全數通過（orders、order_items） <br>_理由：欄位命名樣式一致是資料字典與自動化的基礎。_ <br>_依據：config/Common/knowhow/gating/naming_column_case.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_columns_commented` | `2 表` | 所有欄位必須有 COMMENT 註解：2 表全數通過（orders、order_items） <br>_理由：欄位註解是資料字典的最小單位，中介資料平台會直接讀取。_ <br>_依據：config/Common/knowhow/gating/naming_columns_commented.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_glossary` | `1 表` | 命名對照詞彙字典：1 表全數通過（orders） <br>_理由：欄位命名應使用公司認可的標準詞，避免縮寫與同義異名造成理解成本與整合困難。 此規則對照各 domain naming 資料夾的詞彙表（config/*/naming/*.md，md 表格； Common 恆載入、domain 疊加）做檢查，比寫一堆正則更易維護。_ <br>_依據：config/Common/knowhow/gating/naming_glossary.md ＋ config/<域>/naming/*.md（詞彙字典）_ | skill |
| ✅ | 閘門 | `SKILL.naming_identifier_length` | `2 表` | 識別字長度不超過 64 字元：2 表全數通過（orders、order_items） <br>_理由：過長的表名／欄名不利閱讀與部分工具相容。_ <br>_依據：config/Common/knowhow/gating/naming_identifier_length.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_pk_suffix` | `2 表` | 主鍵欄位建議以 _id 結尾：2 表全數通過（orders、order_items） <br>_理由：可預測的鍵名（x_id）讓 join 推斷與理解更容易。_ <br>_依據：config/Common/knowhow/gating/naming_pk_suffix.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_reserved_words` | `2 表` | 欄位名避免 SQL 保留字：2 表全數通過（orders、order_items） <br>_理由：使用保留字當欄名需要跳脫，易出錯。_ <br>_依據：config/Common/knowhow/gating/naming_reserved_words.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_table_snake_case` | `2 表` | 表名須為 snake_case 全小寫：2 表全數通過（orders、order_items） <br>_理由：一致的表名讓資產可預測、可被工具處理。_ <br>_依據：config/Common/knowhow/gating/naming_table_snake_case.md_ | skill |

## 最佳實踐

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⏭️ | 顧問 | `SKILL.best_practice_semantic` | `(skill)` | 未接 LLM，略過語意卡控「依表型態的最佳實踐建議（語意）」。 <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ✅ | 閘門 | `SKILL.bp_datetime_timezone` | `2 表` | DateTime 應標明時區：2 表全數通過（orders、order_items） <br>_理由：時區不明的時間在跨區情境無法正確比較，應以 DateTime('UTC') 或註解標明。_ <br>_依據：config/Common/knowhow/gating/bp_datetime_timezone.md_ | skill |
| ✅ | 閘門 | `SKILL.bp_lowcardinality_status` | `2 表` | status 欄位須用 LowCardinality（ClickHouse）：2 表全數通過（orders、order_items） <br>_理由：低基數高重複欄位以 LowCardinality 儲存可大幅省空間與記憶體。_ <br>_依據：config/Common/knowhow/gating/bp_lowcardinality_status.md_ | skill |
| ✅ | 閘門 | `SKILL.bp_money_decimal` | `2 表` | 金額欄位必須用 Decimal：2 表全數通過（orders、order_items） <br>_理由：名稱含 amount/price/cost/fee 等的金額欄位，使用浮點數會導致對帳不平。_ <br>_依據：config/Common/knowhow/gating/bp_money_decimal.md_ | skill |
| ✅ | 閘門 | `SKILL.bp_no_float` | `2 表` | 不可使用 Float 型別：2 表全數通過（orders、order_items） <br>_理由：Float 不適合需要精確比較與彙總的數值。_ <br>_依據：config/Common/knowhow/gating/bp_no_float.md_ | skill |
| ✅ | 閘門 | `SKILL.no_future_event_time` | `(schema)` | no_future_event_time：已執行，未發現違規。 <br>_依據：config/Common/knowhow_py/no_future_event_time.py_ | skill |

## 單一真實源（跨域）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⚠️ | 閘門 | `SKILL.ssot_authority` | `dim_customer` | 權威表在場檢視：'customer' 的權威表不在本次 DDL。 <br>_理由：若它屬於另一 domain 的 schema 則屬正常。_ <br>_依據：config/Common/knowhow_py/ssot_authority.py_ | skill |
| ⚠️ | 閘門 | `SKILL.ssot_authority` | `dim_product` | 權威表在場檢視：'product' 的權威表不在本次 DDL。 <br>_理由：若它屬於另一 domain 的 schema 則屬正常。_ <br>_依據：config/Common/knowhow_py/ssot_authority.py_ | skill |
| ⚠️ | 閘門 | `SSOT.UNREGISTERED_SUBJECT` | `order_items` | 未登錄主體候選 'order_item'：此表看似其權威表（證據欄位 ['quantity', 'unit_price']），但 SSOT registry 尚未登錄。建議先登錄再上線。 <br>**期望** 'order_item' 已登錄於 ssot.registry ｜ **實際** registry 查無此主體 <br>**修法** 於 config/default.yaml 的 ssot.registry 登錄 'order_item'（權威表 order_items） <br>_理由：新 data subject 應先登錄權威表，否則跨域 SSOT 硬檢查無法涵蓋它。可由顧問區產 registry 草稿、人工確認後寫回。_ <br>_依據：config/<域>/ssot/registry.yaml（SSOT 登錄推斷）_ | rule |
| ⚠️ | 閘門 | `SSOT.UNREGISTERED_SUBJECT` | `orders` | 未登錄主體候選 'order'：此表看似其權威表（證據欄位 ['status', 'currency', 'total_amount']），但 SSOT registry 尚未登錄。建議先登錄再上線。 <br>**期望** 'order' 已登錄於 ssot.registry ｜ **實際** registry 查無此主體 <br>**修法** 於 config/default.yaml 的 ssot.registry 登錄 'order'（權威表 orders） <br>_理由：新 data subject 應先登錄權威表，否則跨域 SSOT 硬檢查無法涵蓋它。可由顧問區產 registry 草稿、人工確認後寫回。_ <br>_依據：config/<域>/ssot/registry.yaml（SSOT 登錄推斷）_ | rule |
| ⏭️ | 顧問 | `SKILL.ssot_semantic` | `(skill)` | 未接 LLM，略過語意卡控「SSOT 候選衝突偵測（語意）」。 <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ✅ | 閘門 | `PRODUCTION.SCOPE` | `(production)` | 已參照 production domain：['CRM']。 <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `SKILL.ssot_fact_duplication` | `(schema)` | ssot_fact_duplication：已執行，未發現違規。 <br>_依據：config/Common/knowhow_py/ssot_fact_duplication.py_ | skill |
| ✅ | 閘門 | `SKILL.ssot_join_keys` | `order_id` | Join key 型別一致：'order_id' 於 2 表型別一致。 <br>_依據：config/Common/knowhow_py/ssot_join_keys.py_ | skill |
| ✅ | 閘門 | `SKILL.ssot_pii_amount_split` | `2 表` | 個資與金額應分表存放：2 表全數通過（orders、order_items） <br>_理由：PII 與金額混存使權限難分級、真實源歸屬模糊。_ <br>_依據：config/Common/knowhow/gating/ssot_pii_amount_split.md_ | skill |

## 資料設計概念（主體性）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⏭️ | 顧問 | `CONCEPT.SUBJECT` | `(schema)` | 未設定 LLM，略過主體性概念層。 <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |

## Lineage 關聯治理

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ℹ️ | 顧問 | `PRODGRAPH.IMPACT` | `crm.orders` | 正式區有 1 處依賴此表：CRM/order（order_items.order_id）。此表的結構或語意變更會影響這些 subject。 <br>**修法** 變更前通知依賴方；破壞性變更應開新表版本而非原地修改。 <br>_依據：production/<域>/（正式區全域關聯圖）_ | rule |
| ✅ | 閘門 | `LINEAGE.COLUMN_EXISTS` | `(lineage)` | 所有 lineage 欄位映射都可解析。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.CYCLE` | `(lineage)` | local lineage 未形成循環。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.DOMAIN_SCOPE` | `(lineage)` | 所有外部上游 domain 都已明確選取。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.METADATA` | `(lineage)` | relations.yaml 的 lineage 格式與目標表有效。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.TYPE_COMPATIBILITY` | `(lineage)` | 所有 lineage 欄位基本型別相容。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.UPSTREAM_EXISTS` | `(lineage)` | 所有宣告的上游資料表都存在。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `PRODGRAPH.CARDINALITY_CONFLICT` | `(全域關聯圖)` | 關聯宣告與正式區既有 subject 的基數一致。 <br>_依據：production/<域>/（正式區全域關聯圖）_ | rule |
| ✅ | 閘門 | `PRODGRAPH.CYCLE` | `(全域關聯圖)` | 加入本 subject 後全域關聯圖無循環。 <br>_依據：production/<域>/（正式區全域關聯圖）_ | rule |

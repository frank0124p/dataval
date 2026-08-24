# 資料設計驗證報告 — 第 1 輪迭代
_產生時間 2026-08-24T14:40:36.546494Z_<br>
**🔁 第 1／5 輪迭代報告**<br>
**判定：✅ 合規**（會擋項目 0）<br>
通過 36 · 警告 6 · 失敗 0 · 略過 2 · 提示 22<br>
閘門區 44 項 · 顧問區 22 項<br>
> 方言 clickhouse · 表數 2 · 載入 skill 27 條
> 驗證 bundle `33dd3dfaf6486cca`（含規則、validator 與依賴版本）

## Checking rule ID 摘要
- ❌ 擋下：（無）
- ⚠️ 警告：`DERIVATION.COVERAGE`、`SKILL.naming_glossary`、`SKILL.ssot_authority`、`SSOT.UNREGISTERED_SUBJECT`
- ✅ 通過：`BUSINESS_KEY.METADATA`、`DERIVATION.RELATIONS`、`DOMAIN.SCOPE`、`ERD.ENTITY_REFERENCE`、`LINEAGE.COLUMN_EXISTS`、`LINEAGE.CYCLE`、`LINEAGE.DOMAIN_SCOPE`、`LINEAGE.METADATA`、`LINEAGE.TYPE_COMPATIBILITY`、`LINEAGE.UPSTREAM_EXISTS`、`PRODGRAPH.CARDINALITY_CONFLICT`、`PRODGRAPH.CYCLE`、`PRODUCTION.NAMING_CONSISTENCY`、`PRODUCTION.SCOPE`、`SKILL.bp_datetime_timezone`、`SKILL.bp_lowcardinality_status`、`SKILL.bp_money_decimal`、`SKILL.bp_no_float`、`SKILL.naming_column_case`、`SKILL.naming_columns_commented`、`SKILL.naming_identifier_length`、`SKILL.naming_pk_suffix`、`SKILL.naming_reserved_words`、`SKILL.naming_table_snake_case`、`SKILL.no_future_event_time`、`SKILL.ssot_fact_duplication`、`SKILL.ssot_join_keys`、`SKILL.ssot_pii_amount_split`、`SKILL.structural_audit_columns`、`SKILL.structural_business_key`、`SKILL.structural_engine_mergetree`、`SKILL.structural_key_not_nullable`、`SKILL.structural_order_by`、`SKILL.structural_type_sample`
- ℹ️ 未實檢／略過：`SKILL.crm_baseline`、`SKILL.structural_fk_resolves`
- 💡 顧問：`CONCEPT.SUBJECT`、`ERD.TABLE_PURPOSE`、`FLOW.CONTEXT`、`NAME.SEMANTIC`、`PRODGRAPH.IMPACT`、`PROPOSAL.DDL`、`SKILL.best_practice_semantic`、`SKILL.naming_semantic`、`SKILL.ssot_semantic`

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
> 目前：❌ 未收斂 —— 待答 0 題、待驗證 20 題、閘門 fail 0 項

### ❓ 待答（0）
（無）

### 🟡 待驗證：agent 代填，請確認（20）
- `NAME.SEMANTIC@orders.total_amount`（semantic）
  - Q: total_amount 的註解說明是「含稅、下單當下快照值」，但名稱本身看不出含稅與快照語意——下游在計算未稅營收或與商品現價比對時，是否可能誤用？要不要在詞彙字典（config/<域>/naming）登錄這個欄位的權威定義？
  - 代填答案: 維持欄名 total_amount，但在 naming 詞彙字典登錄定義：「訂單總金額＝含稅、下單當下快照，與商品主檔現價無關」，並要求下游計算未稅金額時另行換算。
- `NAME.SEMANTIC@order_items.unit_price`（semantic）
  - Q: unit_price 是「下單當下快照」，與商品主檔的現價欄位若同名，下游 join 之後是否容易混淆兩者？是否考慮以命名（如 snapshot／dealt 字樣）或詞彙字典明確區分？
  - 代填答案: 維持 unit_price 欄名（業界慣例為成交價），在詞彙字典標注「order_items.unit_price＝成交快照價；商品現價以商品主檔為準」，避免下游誤當現價使用。
- `CONCEPT.SUBJECT@orders`（semantic）
  - Q: 訂單的「取消」同時由 status=cancelled 與 cancelled_at 兩個欄位表達——寫入端是否保證兩者一致（status 為 cancelled 時 cancelled_at 必非 NULL，反之亦然）？下游應以哪個欄位為取消判定的權威？
  - 代填答案: 以 status 為取消判定權威、cancelled_at 僅補充取消時間；由結帳服務保證兩欄同交易寫入，並在 context.md 記載此約定。
- `CONCEPT.SUBJECT@order_items`（structural → 建議改 context.md）
  - Q: context 說「同一商品在同一訂單內只會有一行」，這代表 (order_id, product_id) 具唯一性——business key 目前登錄的是代理鍵 order_item_id，是否要把 (order_id, product_id) 一併宣告為自然鍵，讓重複檢查有依據？
  - 代填答案: 在 context.md 的 business_keys 補登 order_items: [order_id, product_id]（自然鍵），order_item_id 保留為代理識別。
- `SKILL.best_practice_semantic@orders.total_amount`（semantic）
  - Q: orders 是交易事實表，total_amount 是明細加總的快照——是否已有對帳機制（批次或檢核報表）驗證它與 order_items 的 quantity × unit_price 加總一致？允許的誤差（折扣、運費、稅）記載在哪裡？
  - 代填答案: total_amount 允許與明細加總不同（含稅與整單折扣攤提在頭表），由結帳服務保證寫入時一致；建議另建日批對帳報表監控差異。
- `SKILL.best_practice_semantic@order_items`（semantic）
  - Q: 幣別 currency 只存在 orders 頭表——明細層要計算金額時必須 join 回頭表取幣別，這是刻意的正規化設計嗎？跨幣別分析的使用情境是否已確認可接受這個 join 成本？
  - 代填答案: 是刻意設計：同一訂單必為單一幣別，幣別屬訂單層事實；下游明細分析一律以 order_id join 回 orders 取 currency。
- `SKILL.naming_semantic@orders.ordered_at`（semantic）
  - Q: ordered_at（業務發生時間）與 created_at（資料建立時間）並存——兩者的差異語意（event time vs ingest time）是否已在詞彙字典明文化，確保營收日報一律以 ordered_at 彙總、稽核追查才用 created_at？
  - 代填答案: 已依 context 約定：營收與對帳一律以 ordered_at（event time）為準；created_at／updated_at 僅稽核用。建議在 naming 詞彙字典補登此約定。
- `SKILL.ssot_semantic@order_items.unit_price`（semantic）
  - Q: unit_price 是刻意反正規化的成交快照，商品現價權威在商品主檔——這條「同名不同權威」的邊界是否已登錄到 SSOT 文件（config/<域>/ssot），避免未來有人把 order_items 當成價格權威來源？
  - 代填答案: 在 SSOT 文件登錄：價格權威＝商品主檔；order_items.unit_price 為成交快照、僅供交易重現與對帳，不得作為現價來源。
- `CONCEPT.SUBJECT@derivation.sql`（semantic）
  - Q: 衍生 SQL 以 orders LEFT JOIN order_items 展開後，寬表粒度變成「訂單 × 商品項」，且無明細的訂單也會留下一列（明細欄全 NULL）——下游對 total_amount 彙總時是否已意識到同一訂單會重複出現多列（每個品項一列）、直接 SUM 會重複計算頭表金額？
  - 代填答案: 寬表粒度定義為「訂單 × 商品項」；訂單層指標（total_amount 等）一律先以 order_id 去重（或改查 orders 頭表）再彙總，無明細訂單保留（NULL 品項欄）以維持訂單母體完整。此口徑補記於 context.md。
- `CONCEPT.SUBJECT@dim_customer`（semantic）
  - Q: 衍生 SQL join 進 dim_customer 的 customer_name／customer_tier 是「查詢當下的現值」——這與 unit_price 採「下單當下快照」的策略相反。以 customer_tier 做歷史訂單分析時，會拿到客戶現在的等級而非下單當時的等級，這是刻意的嗎？
  - 代填答案: 刻意設計：客戶屬性採現值（維度表直接 join），僅交易金額採快照；需要「下單當時等級」的分析應另建 SCD2 客戶維度，本寬表不承諾歷史屬性。此語意補記於 context.md。
- `NAME.SEMANTIC@orders.status`（semantic）
  - Q: `status` 目前承載訂單生命週期（created/paid/shipped/cancelled），其中 `paid` 屬於金流語意、`shipped` 屬於物流語意——單一欄位混合多條狀態軸，未來要新增「退款中」「部分出貨」時是否還能表達？
  - 代填答案: 目前階段維持單一 `status` 即可（訂單生命週期是線性的）；若之後出現金流與物流同時演進的需求，再拆成 `order_status` ＋ `payment_status` ＋ `fulfillment_status` 三欄，並在 context.md 記錄拆分時機。
- `NAME.SEMANTIC@orders.ordered_at / orders.created_at / orders.updated_at`（semantic）
  - Q: 三個時間欄中 `ordered_at` 是業務發生時間、`created_at`／`updated_at` 是稽核時間，但命名形式相同（都是 `_at`）——分析師只看欄名能分辨哪個可以拿來做營收歸期嗎？
  - 代填答案: 維持現有欄名（`_at` 是專案慣例），但在 context.md 的「用途與消費者」明確寫死「營收彙總一律以 `ordered_at` 為準，`created_at`／`updated_at` 僅供稽核與增量抽取」，並在 ETL／BI 語意層設為預設時間欄。
- `NAME.SEMANTIC@order_items.product_id`（structural → 建議改 order.sql）
  - Q: `customer_id` 的註解明確指出權威在 `CRM.dim_customer`，但 `product_id` 只寫「權威在商品主檔」而沒有指名 domain 與表——這個商品主檔在哪個領域、叫什麼名字？
  - 代填答案: 商品主檔權威預期在 SCM 領域（例如 `SCM.dim_product`），但該 subject 目前尚未晉升進 production。建議先在 `product_id` 的 COMMENT 與 context.md 寫明預期權威位置，待商品主檔晉升後再於 relations.yaml 補上三段式宣告。
- `CONCEPT.SUBJECT@order（未登錄主體候選）`（structural → 建議改 config/CRM/ssot/registry.yaml）
  - Q: `orders` 與 `order_items` 承載的「訂單」「訂單明細」概念目前不在 SSOT 登錄表內——這兩個主體的權威擁有者是本 subject 嗎？要不要順手登錄，讓之後的跨域引用有依據？
  - 代填答案: 是，訂單與訂單明細的權威擁有者就是本 subject。建議晉升進 production 後，於 `config/CRM/ssot/registry.yaml` 登錄 `order` → `orders`、`order_item` → `order_items`。
- `SKILL.best_practice_semantic@orders.ordered_at`（structural → 建議改 order.sql）
  - Q: 訂單是持續累積的時間序列事實，但目前沒有看到分區宣告——資料量成長後，營收日報依 `ordered_at` 掃描的成本是否還可接受？
  - 代填答案: 建議加 `PARTITION BY toYYYYMM(ordered_at)`（月分區，與月結批次的重跑單位一致），排序鍵可再評估改為 `(ordered_at, order_id)` 以利時間範圍裁剪。
- `SKILL.naming_semantic@orders.customer_id / dim_customer.customer_id`（structural → 建議改 derivation.sql）
  - Q: 衍生 SQL 把 `dim_customer.customer_id` 另取別名 `dim_customer_customer_id` 輸出——寬表裡同時出現兩個客戶鍵，讀的人分得出哪個是本表的鍵、哪個是 join 進來的嗎？
  - 代填答案: 寬表只保留 `orders.customer_id` 一個客戶鍵，`dim_customer_customer_id` 屬於 join 驗證用的暫時欄，建議從最終的寬表 SELECT 清單移除。
- `SKILL.naming_semantic@order_items.quantity`（semantic）
  - Q: `quantity` 的註解寫「單位：件」，但商品若有以重量或長度計價的品項，這個欄名與單位假設還成立嗎？是否需要一個 `unit_of_measure`？
  - 代填答案: 目前商品皆以「件」計價，維持現狀即可；若導入計重／計長商品，再新增 `unit_of_measure` 欄並回填既有資料為 `piece`。建議把這個前提寫進 context.md。
- `SKILL.ssot_semantic@derivation.sql（customer_name、customer_tier）`（semantic）
  - Q: context 明確宣告「只存鍵不存客戶屬性」，但衍生 SQL 把 `customer_name`、`customer_tier` join 進寬表——這份寬表若被物化保存，是不是就等於在本領域複製了 CRM 的權威屬性？
  - 代填答案: 這張寬表定位為查詢期的 view／臨時結果，不物化落地，因此不構成權威複製。若之後要物化，需在 context.md 註明快照語意（客戶屬性為當時值）並定義刷新頻率。
- `SKILL.ssot_semantic@order_items.product_id`（semantic）
  - Q: `product_id` 指向的商品主檔目前不在任何已晉升的 domain 內——這個 join key 能保證與未來的商品主檔指向同一實體（同編碼、同型別）嗎？
  - 代填答案: 商品編碼沿用來源系統的商品主鍵（整數、全域唯一），與未來 `SCM.dim_product.product_id` 同源。建議商品主檔晉升時立即補 relations.yaml 三段式宣告，讓引擎做型別相容實檢。
- `SKILL.ssot_semantic@orders.currency`（semantic）
  - Q: `currency` 存在訂單層級，但 `order_items.unit_price` 沒有幣別欄——明細金額的幣別是隱含沿用訂單的嗎？跨幣別報表彙總時，這個隱含關係看得出來嗎？
  - 代填答案: 是，明細幣別一律沿用所屬訂單的 `orders.currency`（一張訂單不會混幣）。建議把這條不變式寫進 context.md，並要求所有金額彙總必須先 join 訂單取幣別或先換算為本位幣。
> 驗證：到 input/<名>/answers.yaml 把 `status: proposed` 改為 `answered`（答案可修改；不想追的改 `deferred`）。待驗證不算已答，會擋收斂。

### ✅ 已解（0）
（無）

### 📝 本輪 input 變更
（首輪——無前輪可比；本輪輸入已快照到 iterations/）

## 表總覽（一 subject＝一組表）

| 表 | 來源檔 | 欄數 | Business Key | ❌ 擋 | ⚠️ 警告 | 表間關係 | 設計對照 |
|---|---|---|---|---|---|---|---|
| `orders` | order.sql | 9 | `order_id` | 0 | 1 | → CRM.dim_customer（N:1） | —（未經設計） |
| `order_items` | order.sql | 7 | `order_item_id` | 0 | 3 | → orders（N:1） | —（未經設計） |

## 設計對照（design mode 設計稿 ↔ input DDL）
> ⚠️ 此 subject **未經過設計模式**（design mode）——input DDL 為手寫直接進治理，沒有設計稿可對照。
> 建議：新主體先以 `input/<名>/context.md` 走設計流程（產生設計文件與可對照的設計稿），再定稿進治理。

## 建議 DDL 對比（依參考模型自動組建；建議值，不影響判定）
> 基底表 `orders` · 涵蓋 entity：`orders`、`dim_customer`、`order_items` · 依據：CRM/erd/crm_core.md
> 📄 本輪拆檔（隨報告產出）：`govern_doc/<名>/<名>.round_1.join.sql`（建議 Join SQL）、`<名>.round_1.future.ddl`（未來寬表 DDL）；歷史存檔另見 `iterations/<名>/`
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

## 衍生 SQL 對照（input/<名>/derivation.sql）
> 基底表 `orders` · 來源表 `dim_customer`、`order_items`、`orders` · join 2 組 · 輸出欄 14
> 對應寬表 `order_items`：欄位覆蓋 6/7；DDL 有但 SQL 沒產出：['updated_at']；SQL 產出但 DDL 沒有：['customer_id', 'customer_name', 'customer_tier', 'dim_customer_customer_id', 'order_items_order_id', 'ordered_at', 'status', 'total_amount']

### 你的 Join SQL
```sql
-- order 寬表的衍生 SQL（這張寬表實際上是怎麼 join 出來的）。
-- 起點：第 1 輪建議 Join SQL（iterations/order/round_1.join.sql）——
-- 請以實際使用的組合 SQL 取代本檔內容後重跑 run.py。
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

### join 鍵三方對照
| join 鍵 | 你的 SQL | relations.yaml | 建議 SQL |
|---|---|---|---|
| `dim_customer.customer_id = orders.customer_id` | ✅ | ✅ | ✅ |
| `order_items.order_id = orders.order_id` | ✅ | ✅ | ✅ |

## Lineage 關聯
> 關係來自 relations.yaml，並參照 ER diagram；兩者都是設計宣告，不代表已觀測到 runtime lineage。

| 來源 | 目標 | 欄位映射 | 性質 |
|---|---|---|---|
| `local.orders` | `order_items` | `order_id` → `order_id` | YAML 宣告＋ER 對應 |
| `CRM.dim_customer` | `orders` | `customer_id` → `customer_id` | YAML 明確宣告 |

## 本次卡控摘要（被哪些規則卡下來）

**警告（放行但需注意）：**
- `DERIVATION.COVERAGE` 衍生 SQL 輸出與寬表 `order_items` 欄位不一致 → order_items
- `SKILL.naming_glossary` 命名對照詞彙字典 → order_items
- `SKILL.ssot_authority` 權威表在場檢視 → dim_customer、dim_product
- `SSOT.UNREGISTERED_SUBJECT` 未登錄主體候選 'order_item' → order_items、orders

## 結構（欄位／型別／約束）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⚠️ | 閘門 | `DERIVATION.COVERAGE` | `order_items` | 衍生 SQL 輸出與寬表 `order_items` 欄位不一致：DDL 有但 SQL 沒產出 ['updated_at']；SQL 產出但 DDL 沒有 ['customer_id', 'customer_name', 'customer_tier', 'dim_customer_customer_id', 'order_items_order_id', 'ordered_at', 'status', 'total_amount']。 <br>**期望** SQL 輸出欄 ＝ 寬表 DDL 欄位 ｜ **實際** 缺 1、多 8 <br>**修法** 同步 derivation.sql 與 DDL（欄位增減要兩邊一起改） <br>_依據：input/<名>/derivation.sql（你的衍生 Join SQL）對照 relations.yaml／寬表 DDL／建議 SQL_ | rule |
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
| ℹ️ | 顧問 | `PROPOSAL.DDL` | `orders_wide` | 已依參考模型組建建議 Join SQL 與未來 DDL：基底 orders、涵蓋 3 個 entity（input 尚未涵蓋：['dim_customer']）。建議值，不影響判定；對比見報告「建議 DDL 對比」區塊。 <br>_依據：config/<域>/erd/*.md（參考模型自動組建；建議值，不影響判定）_ | rule |
| ✅ | 閘門 | `BUSINESS_KEY.METADATA` | `(schema)` | Business key metadata 已驗證：['order_items', 'orders']。 <br>_依據：input/<名>/context.md（front-matter business_keys）_ | rule |
| ✅ | 閘門 | `DERIVATION.RELATIONS` | `derivation.sql` | 衍生 SQL 的 2 組 join 鍵皆已在 relations.yaml 宣告。 <br>_依據：input/<名>/derivation.sql（你的衍生 Join SQL）對照 relations.yaml／寬表 DDL／建議 SQL_ | rule |
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
| ⚠️ | 閘門 | `SKILL.naming_glossary` | `order_items` | 命名對照詞彙字典：欄位用到別名：order_item_id（'item'） <br>**期望** 使用正規詞 ｜ **實際** order_item_id 用了別名 'item' <br>**修法** order_item_id 改用 'product' <br>_理由：欄位命名應使用公司認可的標準詞，避免縮寫與同義異名造成理解成本與整合困難。 此規則對照各 domain naming 資料夾的詞彙表（config/*/naming/*.md，md 表格； Common 恆載入、domain 疊加）做檢查，比寫一堆正則更易維護。_ <br>_依據：config/Common/knowhow/gating/naming_glossary.md（詞彙字典：config/CRM/naming/、config/Common/naming/）_ | skill |
| ✅ | 閘門 | `PRODUCTION.NAMING_CONSISTENCY` | `(production)` | 新設計命名與 production 基準一致。 <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `SKILL.naming_column_case` | `2 表` | 欄位名須為 snake_case 全小寫：2 表全數通過（orders、order_items） <br>_理由：欄位命名樣式一致是資料字典與自動化的基礎。_ <br>_依據：config/Common/knowhow/gating/naming_column_case.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_columns_commented` | `2 表` | 所有欄位必須有 COMMENT 註解：2 表全數通過（orders、order_items） <br>_理由：欄位註解是資料字典的最小單位，中介資料平台會直接讀取。_ <br>_依據：config/Common/knowhow/gating/naming_columns_commented.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_glossary` | `1 表` | 命名對照詞彙字典：1 表全數通過（orders） <br>_理由：欄位命名應使用公司認可的標準詞，避免縮寫與同義異名造成理解成本與整合困難。 此規則對照各 domain naming 資料夾的詞彙表（config/*/naming/*.md，md 表格； Common 恆載入、domain 疊加）做檢查，比寫一堆正則更易維護。_ <br>_依據：config/Common/knowhow/gating/naming_glossary.md（詞彙字典：config/CRM/naming/、config/Common/naming/）_ | skill |
| ✅ | 閘門 | `SKILL.naming_identifier_length` | `2 表` | 表名不超過 64、欄名不超過 48 字元：2 表全數通過（orders、order_items） <br>_理由：過長的表名／欄名不利閱讀、跨工具相容與下游引用。 表名上限 64 字元、欄位名上限 48 字元，超過即擋。_ <br>_依據：config/Common/knowhow/gating/naming_identifier_length.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_pk_suffix` | `2 表` | 主鍵欄位建議以 _id 結尾：2 表全數通過（orders、order_items） <br>_理由：可預測的鍵名（x_id）讓 join 推斷與理解更容易。_ <br>_依據：config/Common/knowhow/gating/naming_pk_suffix.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_reserved_words` | `2 表` | 欄位名避免 SQL 保留字：2 表全數通過（orders、order_items） <br>_理由：使用保留字當欄名需要跳脫，易出錯。_ <br>_依據：config/Common/knowhow/gating/naming_reserved_words.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_table_snake_case` | `2 表` | 表名須為 snake_case 全小寫：2 表全數通過（orders、order_items） <br>_理由：一致的表名讓資產可預測、可被工具處理。_ <br>_依據：config/Common/knowhow/gating/naming_table_snake_case.md_ | skill |

## 最佳實踐

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `order_items` | `order_items` 沒有金額小計欄（`quantity × unit_price`）——每個下游都要自己乘一次，這個計算口徑（含稅、折扣後）確定各處一致嗎？ <br>_理由：把重複的計算留給下游，等於把口徑一致性的責任分散出去；一旦有折扣或稅務調整，各報表結果就會分歧。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `orders` | `orders` 是典型的交易型事實表且帶 `updated_at`（會被更新）——目前 ENGINE 的去重與版本策略，能保證同一 `order_id` 只會查到最新版本嗎？ <br>_理由：可變更的事實表若沒有版本欄與去重策略，重跑或補寫會留下同一鍵的多個版本，讀取端必須自己 argMax，容易漏做。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `orders.ordered_at` | 訂單是持續累積的時間序列事實，但目前沒有看到分區宣告——資料量成長後，營收日報依 `ordered_at` 掃描的成本是否還可接受？ <br>_理由：沒有分區的 MergeTree 在時間範圍查詢時只能靠排序鍵裁剪，若排序鍵是 `order_id`，時間查詢會退化成全表掃描。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.naming_semantic` | `order_items.quantity` | `quantity` 的註解寫「單位：件」，但商品若有以重量或長度計價的品項，這個欄名與單位假設還成立嗎？是否需要一個 `unit_of_measure`？ <br>_理由：數量欄隱含單位假設時，一旦商品線擴張（生鮮、布料），既有資料的語意會在無聲中改變。_ <br>_依據：config/Common/knowhow/advisory/naming_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.naming_semantic` | `orders.customer_id / dim_customer.customer_id` | 衍生 SQL 把 `dim_customer.customer_id` 另取別名 `dim_customer_customer_id` 輸出——寬表裡同時出現兩個客戶鍵，讀的人分得出哪個是本表的鍵、哪個是 join 進來的嗎？ <br>_理由：join 後保留兩份同義鍵是常見的除錯殘留；留在寬表定義裡會讓下游不確定該用哪一個做關聯。_ <br>_依據：config/Common/knowhow/advisory/naming_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `derivation.sql（customer_name、customer_tier）` | context 明確宣告「只存鍵不存客戶屬性」，但衍生 SQL 把 `customer_name`、`customer_tier` join 進寬表——這份寬表若被物化保存，是不是就等於在本領域複製了 CRM 的權威屬性？ <br>_理由：查詢期 join 與物化落地是兩件事：前者不產生第二份事實，後者會，而且客戶改名後寬表不會自動跟上。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `order_items.product_id` | `product_id` 指向的商品主檔目前不在任何已晉升的 domain 內——這個 join key 能保證與未來的商品主檔指向同一實體（同編碼、同型別）嗎？ <br>_理由：模糊的 join key 在主檔補上之後才會發現編碼不一致，屆時回填成本很高。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `orders.currency` | `currency` 存在訂單層級，但 `order_items.unit_price` 沒有幣別欄——明細金額的幣別是隱含沿用訂單的嗎？跨幣別報表彙總時，這個隱含關係看得出來嗎？ <br>_理由：金額與幣別分開存放時，任何未帶幣別的加總都可能把不同幣別相加，而 schema 本身不會阻止。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
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
| ✅ | 閘門 | `PRODUCTION.SCOPE` | `(production)` | 已參照 production domain：['CRM']。 <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `SKILL.ssot_fact_duplication` | `(schema)` | ssot_fact_duplication：已執行，未發現違規。 <br>_依據：config/Common/knowhow_py/ssot_fact_duplication.py_ | skill |
| ✅ | 閘門 | `SKILL.ssot_join_keys` | `order_id` | Join key 型別一致：'order_id' 於 2 表型別一致。 <br>_依據：config/Common/knowhow_py/ssot_join_keys.py_ | skill |
| ✅ | 閘門 | `SKILL.ssot_pii_amount_split` | `2 表` | 個資與金額應分表存放：2 表全數通過（orders、order_items） <br>_理由：PII 與金額混存使權限難分級、真實源歸屬模糊。_ <br>_依據：config/Common/knowhow/gating/ssot_pii_amount_split.md_ | skill |

## 資料設計概念（主體性）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `order_items` | 粒度宣告「同一商品在同一訂單內只會有一行，數量以 quantity 表達」——若同一商品在一張訂單裡出現不同單價（例如買一送一、部分套用折扣），這個粒度還撐得住嗎？ <br>_理由：「一訂單一商品一行」的粒度在促銷場景會被打破，屆時要嘛改粒度、要嘛在欄位裡塞平均價，兩者都會影響既有下游。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `orders` | context 說取消訂單「仍保留該行、以 cancelled_at 標記」——那麼營收日報在彙總 `total_amount` 時，是以 `cancelled_at IS NULL` 過濾，還是另有沖銷邏輯？這條口徑寫在哪裡？ <br>_理由：軟刪除的事實表若沒有把「有效行」的定義寫進主體描述，每個下游都會自己實作一套過濾條件，久了口徑就會分歧。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `orders.total_amount` | `total_amount` 是「明細加總的快照值」，同時 `order_items` 又保有逐項的 `quantity × unit_price`——當兩者對不起來（例如事後調整明細）時，哪一邊是權威？ <br>_理由：同一事實同時存在彙總值與明細值時，若沒有宣告權威方與允許誤差，對帳爭議無法收斂。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `order（未登錄主體候選）` | `orders` 與 `order_items` 承載的「訂單」「訂單明細」概念目前不在 SSOT 登錄表內——這兩個主體的權威擁有者是本 subject 嗎？要不要順手登錄，讓之後的跨域引用有依據？ <br>_理由：主體沒有登錄權威擁有者時，其他領域要引用訂單資料只能各自複製，容易形成第二份事實。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `order_items.product_id` | `customer_id` 的註解明確指出權威在 `CRM.dim_customer`，但 `product_id` 只寫「權威在商品主檔」而沒有指名 domain 與表——這個商品主檔在哪個領域、叫什麼名字？ <br>_理由：跨域引用鍵若沒有指名權威位置，之後做 lineage 與影響分析時無法自動接上，只能靠人記憶。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `orders.ordered_at / orders.created_at / orders.updated_at` | 三個時間欄中 `ordered_at` 是業務發生時間、`created_at`／`updated_at` 是稽核時間，但命名形式相同（都是 `_at`）——分析師只看欄名能分辨哪個可以拿來做營收歸期嗎？ <br>_理由：業務時間與稽核時間混用是彙總報表最常見的錯誤來源（用 created_at 彙總會把補寫的歷史資料歸到錯誤的日期）。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `orders.status` | `status` 目前承載訂單生命週期（created/paid/shipped/cancelled），其中 `paid` 屬於金流語意、`shipped` 屬於物流語意——單一欄位混合多條狀態軸，未來要新增「退款中」「部分出貨」時是否還能表達？ <br>_理由：把多條獨立演進的狀態軸壓在一個欄位，狀態值會隨業務成長爆炸，且無法表示「已付款且部分出貨」這類同時成立的狀態。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `orders.total_amount` | `total_amount` 的註解說明是「含稅」，但 `order_items.unit_price` 沒有標示含稅與否——同一份 schema 內的金額欄位，是否要讓命名或註解一致地表達稅務語意？ <br>_理由：金額欄若含稅語意不一致，下游做「明細加總 vs 訂單總額」對帳時會出現無法解釋的差額，而命名本身看不出來。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |

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

# 資料設計驗證報告 — 第 2 輪迭代
_第 2 輪迭代存檔_<br>
**🔁 第 2／5 輪迭代報告**<br>
**判定：✅ 合規**（會擋項目 0）<br>
通過 37 · 警告 6 · 失敗 0 · 略過 2 · 提示 17<br>
閘門區 45 項 · 顧問區 17 項<br>
> 方言 clickhouse · 表數 2 · 載入 skill 28 條
> 驗證 bundle `f94515f069cfe10a`（含規則、validator 與依賴版本）

## Checking rule ID 摘要
- ❌ 擋下：（無）
- ⚠️ 警告：`DERIVATION.COVERAGE`、`SKILL.naming_glossary`、`SKILL.ssot_authority`、`SSOT.UNREGISTERED_SUBJECT`
- ✅ 通過：`BUSINESS_KEY.METADATA`、`DERIVATION.RELATIONS`、`DOMAIN.SCOPE`、`ERD.ENTITY_REFERENCE`、`LINEAGE.COLUMN_EXISTS`、`LINEAGE.CYCLE`、`LINEAGE.DOMAIN_SCOPE`、`LINEAGE.METADATA`、`LINEAGE.TYPE_COMPATIBILITY`、`LINEAGE.UPSTREAM_EXISTS`、`PRODGRAPH.CARDINALITY_CONFLICT`、`PRODGRAPH.CYCLE`、`PRODUCTION.NAMING_CONSISTENCY`、`PRODUCTION.REUSE`、`PRODUCTION.SCOPE`、`SKILL.bp_datetime_timezone`、`SKILL.bp_lowcardinality_status`、`SKILL.bp_money_decimal`、`SKILL.bp_no_float`、`SKILL.naming_column_case`、`SKILL.naming_columns_commented`、`SKILL.naming_identifier_length`、`SKILL.naming_pk_suffix`、`SKILL.naming_reserved_words`、`SKILL.naming_table_snake_case`、`SKILL.no_future_event_time`、`SKILL.ssot_fact_duplication`、`SKILL.ssot_join_keys`、`SKILL.ssot_pii_amount_split`、`SKILL.structural_audit_columns`、`SKILL.structural_business_key`、`SKILL.structural_engine_mergetree`、`SKILL.structural_key_not_nullable`、`SKILL.structural_order_by`、`SKILL.structural_type_sample`
- ℹ️ 未實檢／略過：`SKILL.crm_baseline`、`SKILL.structural_fk_resolves`
- 💡 顧問：`CONCEPT.SUBJECT`、`ERD.TABLE_PURPOSE`、`FLOW.CONTEXT`、`NAME.SEMANTIC`、`PRODGRAPH.IMPACT`、`PROPOSAL.DDL`、`SKILL.best_practice_semantic`、`SKILL.naming_semantic`、`SKILL.production_reuse_semantic`、`SKILL.ssot_semantic`

## 規則涵蓋清單
> 宣告域（context.md）：CRM · config 可用域：BLM、CRM、Common、FCM、PLM、SCM
> 涵蓋：載入並執行 **28** 條 ／ config 共 **41** 條

### ✅ 已載入並執行（28 條）
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
- `SKILL.production_reuse_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/production_reuse_semantic.md
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

## 迭代收斂（第 2 輪／上限 5）
> 收斂條件：無待答問題 ＋ 閘門合規
> 目前：❌ 未收斂 —— 待答 0 題、待驗證 15 題、閘門 fail 0 項

### ❓ 待答（0）
（無）

### 🟡 待驗證：agent 代填，請確認（15）
- `CONCEPT.SUBJECT@order_items`（structural → 建議改 context.md）
  - Q: context 說「同一商品在同一訂單內只會有一行」，這代表 (order_id, product_id) 具唯一性——business key 目前登錄的是代理鍵 order_item_id，是否要把 (order_id, product_id) 一併宣告為自然鍵，讓重複檢查有依據？
  - 代填答案: 在 context.md 的 business_keys 補登 order_items: [order_id, product_id]（自然鍵），order_item_id 保留為代理識別。
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
- `NAME.SEMANTIC@orders.cancelled_at`（semantic）
  - Q: `cancelled_at` 是本 schema 唯一可為 NULL 的欄位，NULL 同時代表「尚未取消」——但「訂單已取消卻沒記到時間」也會是 NULL。這兩種情況在查詢時分得開嗎？
  - 代填答案: 以 `status = 'cancelled'` 為取消判定權威（前一輪已確認），因此 `cancelled_at IS NULL 且 status = 'cancelled'` 就是資料品質異常。建議把這條不變式做成日批檢核，而非改變欄位設計。
- `NAME.SEMANTIC@order_items.order_item_id`（semantic）
  - Q: `order_item_id` 是來源系統給的自然鍵，還是 ETL 端產生的代理鍵？如果訂單重送或明細重算，同一個商品項會拿到同一個 id 嗎？
  - 代填答案: `order_item_id` 是結帳服務產生的來源穩定識別碼，重送同一筆明細會沿用同一個 id。建議把這個穩定性保證寫進 context.md，作為下游可安全 upsert 的依據。
- `CONCEPT.SUBJECT@orders（取消單的母體語意）`（semantic）
  - Q: 前一輪確認營收彙總會排除取消訂單——那「下單量」「轉換率」這類母體型指標呢？取消單要算進分母嗎？
  - 代填答案: 下單量等母體型指標**包含**取消單（下單行為確實發生），只有金額型指標排除；建議在 context.md 分開寫這兩條口徑，避免下游把營收的過濾條件套用到母體。
- `CONCEPT.SUBJECT@orders（部分退貨／換貨）`（semantic）
  - Q: `status` 只能表達整單取消，但實務上會有「退其中一個品項」——這類部分退貨的事實目前由哪個主體承載？本主體要不要負責？
  - 代填答案: 部分退貨屬於獨立的售後事實，應由另一個主體（退貨／退款事件表）承載，本主體維持下單當下快照、不回寫金額。建議在 context.md 的領域邊界明寫「本主體不承載退貨」。
- `SKILL.best_practice_semantic@orders.cancelled_at（Nullable 欄位策略）`（semantic）
  - Q: `cancelled_at` 是唯一使用 Nullable 的欄位——在 ClickHouse 中 Nullable 會多一個 null map、影響壓縮與掃描效能。這個成本在資料量放大後可接受嗎？
  - 代填答案: 目前僅一欄、且取消是低頻事件，維持 Nullable 可接受（語意最清楚）。建議設一條慣例：只有「業務上真的可能不存在」的時間欄才用 Nullable，其餘一律 NOT NULL＋預設值。
- `SKILL.naming_semantic@orders / order_items（表名與 SSOT 主體名）`（structural → 建議改 config/CRM/naming/）
  - Q: 表名用複數（`orders`、`order_items`），SSOT 的主體候選卻是單數（`order`、`order_item`）——這組單複數對應是專案慣例嗎？有寫在詞彙字典裡讓後續 subject 照做嗎？
  - 代填答案: 慣例為「主體名單數、表名複數」。建議在 `config/CRM/naming/` 的詞彙字典明文登錄這條規則，讓後續 subject 有依據可循。
- `SKILL.ssot_semantic@orders.currency（換算基準）`（semantic）
  - Q: 前一輪確認一張訂單只有單一幣別——那跨幣別的營收合計要換算成本位幣時，匯率來自哪裡？這份匯率事實的權威擁有者是誰？
  - 代填答案: 匯率不屬於本主體，權威應在財務領域的匯率主檔；營收換算一律以「下單日匯率」為準。建議在 context.md 註明此依賴，待匯率主檔晉升後於 relations.yaml 補宣告。
- `SKILL.ssot_semantic@orders.total_amount（對外請款金額）`（semantic）
  - Q: 前一輪確認 `total_amount` 是金流實際請款金額的權威——那金流平台自己那份交易金額算什麼？兩邊不一致時，對外（例如客服、發票）要以誰為準？
  - 代填答案: 對外一律以金流平台的交易紀錄為最終權威（它是真正扣款的系統）；本表的 `total_amount` 是請款當下的快照，用於分析與差異偵測。建議在 context.md 明寫這個優先序。
- `SKILL.production_reuse_semantic@orders / order_items（本主體已在正式區）`（semantic）
  - Q: 正式區的 `CRM.order` 就是本主體的已核准版本——這次 input 是既有主體的改版，不是新建。變更相對正式區版本的差異，下游（營收日報、對帳、出貨）已經評估過影響了嗎？
  - 代填答案: 本次改版與正式區版本的差異僅在補充註解與 relations 宣告，欄位與粒度不變，下游不受影響。若之後要動欄位，先以 PRODGRAPH.IMPACT 的依賴清單逐一確認。
- `SKILL.production_reuse_semantic@orders.customer_id → CRM.dim_customer`（semantic）
  - Q: 本主體已用三段式引用客戶主檔（`CRM.dim_customer`），這是正確的複用。反過來看：正式區的 `CRM.dim_customer` 有沒有哪些屬性是本主體其實需要、但目前是靠下游自己 join 取得的？要不要在 context 明寫「客戶屬性一律 join 主檔取得」的使用約定？
  - 代填答案: 是，建議在 context.md 的「用途與消費者」補一句：客戶屬性（姓名、等級、聯絡方式）一律以 customer_id join `CRM.dim_customer` 取得，本主體與其下游都不得自行複製。
> 驗證：到 input/<名>/answers.yaml 把 `status: proposed` 改為 `answered`（答案可修改；不想追的改 `deferred`）。待驗證不算已答，會擋收斂。

### ✅ 已解（15）
- `NAME.SEMANTIC@orders.total_amount`（semantic）維持欄名 total_amount，但在 naming 詞彙字典登錄定義：「訂單總金額＝含稅、下單當下快照，與商品主檔現價無關」，並要求下游計算未稅金額時另行換
- `NAME.SEMANTIC@order_items.unit_price`（semantic）維持 unit_price 欄名（業界慣例為成交價），在詞彙字典標注「order_items.unit_price＝成交快照價；商品現價以商品主檔為準」，避免下
- `CONCEPT.SUBJECT@orders`（semantic）以 status 為取消判定權威、cancelled_at 僅補充取消時間；由結帳服務保證兩欄同交易寫入，並在 context.md 記載此約定。
- `SKILL.best_practice_semantic@orders.total_amount`（semantic）total_amount 允許與明細加總不同（含稅與整單折扣攤提在頭表），由結帳服務保證寫入時一致；建議另建日批對帳報表監控差異。
- `SKILL.best_practice_semantic@order_items`（semantic）是刻意設計：同一訂單必為單一幣別，幣別屬訂單層事實；下游明細分析一律以 order_id join 回 orders 取 currency。
- `SKILL.naming_semantic@orders.ordered_at`（semantic）已依 context 約定：營收與對帳一律以 ordered_at（event time）為準；created_at／updated_at 僅稽核用。建議在 n
- `SKILL.ssot_semantic@order_items.unit_price`（semantic）在 SSOT 文件登錄：價格權威＝商品主檔；order_items.unit_price 為成交快照、僅供交易重現與對帳，不得作為現價來源。
- `CONCEPT.SUBJECT@derivation.sql`（semantic）寬表粒度定義為「訂單 × 商品項」；訂單層指標（total_amount 等）一律先以 order_id 去重（或改查 orders 頭表）再彙總，無明細訂單保
- `CONCEPT.SUBJECT@dim_customer`（semantic）刻意設計：客戶屬性採現值（維度表直接 join），僅交易金額採快照；需要「下單當時等級」的分析應另建 SCD2 客戶維度，本寬表不承諾歷史屬性。此語意補記於 c
- `NAME.SEMANTIC@orders.status`（semantic）目前階段維持單一 `status` 即可（訂單生命週期是線性的）；若之後出現金流與物流同時演進的需求，再拆成 `order_status` ＋ `payment
- `NAME.SEMANTIC@orders.ordered_at / orders.created_at / orders.updated_at`（semantic）維持現有欄名（`_at` 是專案慣例），但在 context.md 的「用途與消費者」明確寫死「營收彙總一律以 `ordered_at` 為準，`created
- `SKILL.naming_semantic@order_items.quantity`（semantic）目前商品皆以「件」計價，維持現狀即可；若導入計重／計長商品，再新增 `unit_of_measure` 欄並回填既有資料為 `piece`。建議把這個前提寫進 
- `SKILL.ssot_semantic@derivation.sql（customer_name、customer_tier）`（semantic）這張寬表定位為查詢期的 view／臨時結果，不物化落地，因此不構成權威複製。若之後要物化，需在 context.md 註明快照語意（客戶屬性為當時值）並定義刷新
- `SKILL.ssot_semantic@order_items.product_id`（semantic）商品編碼沿用來源系統的商品主鍵（整數、全域唯一），與未來 `SCM.dim_product.product_id` 同源。建議商品主檔晉升時立即補 relati
- `SKILL.ssot_semantic@orders.currency`（semantic）是，明細幣別一律沿用所屬訂單的 `orders.currency`（一張訂單不會混幣）。建議把這條不變式寫進 context.md，並要求所有金額彙總必須先 j

### 📝 本輪 input 變更
（vs 第 1 輪）
- `answers.yaml`：變更（+66／−15 行）
- `context.md`：不變
- `derivation.sql`：不變
- `order.sql`：不變
- `relations.yaml`：不變

### 🔄 與第 1 輪相比的發現變化
- 新增 11、解決 15、狀態變化 0（明細：iterations/<名>/round_2.delta.md；該輪完整報告：round_2.report.md）

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
> 📄 本輪拆檔（隨報告產出）：`govern_doc/<名>/<名>.round_2.join.sql`（建議 Join SQL）、`<名>.round_2.future.ddl`（未來寬表 DDL）；歷史存檔另見 `iterations/<名>/`
> ⚠️ 參考模型有、但 input 尚未涵蓋的表：`dim_customer`
> 🧬 與第 1 輪建議相比：**不變**。

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
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `order_items` | 明細表最主要的存取型態是「依 order_id 取回整張訂單的品項」，但排序鍵是 `order_item_id`——這個排序對主要查詢有幫助嗎？ <br>_理由：ClickHouse 的排序鍵決定資料的實體排列；若與主要查詢的過濾鍵不一致，每次查單一訂單都要掃過大量無關資料。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `orders.cancelled_at（Nullable 欄位策略）` | `cancelled_at` 是唯一使用 Nullable 的欄位——在 ClickHouse 中 Nullable 會多一個 null map、影響壓縮與掃描效能。這個成本在資料量放大後可接受嗎？ <br>_理由：少量 Nullable 欄位通常無妨，但若之後陸續增加，累積的儲存與掃描成本會超出預期，屆時再改型別要回填全表。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.naming_semantic` | `orders / order_items（表名與 SSOT 主體名）` | 表名用複數（`orders`、`order_items`），SSOT 的主體候選卻是單數（`order`、`order_item`）——這組單複數對應是專案慣例嗎？有寫在詞彙字典裡讓後續 subject 照做嗎？ <br>_理由：表名與主體名的對應若靠默契，之後不同人建表會出現 `order` 與 `orders` 並存，跨主體引用時無法確定指的是哪一個。_ <br>_依據：config/Common/knowhow/advisory/naming_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.production_reuse_semantic` | `orders / order_items（本主體已在正式區）` | 正式區的 `CRM.order` 就是本主體的已核准版本——這次 input 是既有主體的改版，不是新建。變更相對正式區版本的差異，下游（營收日報、對帳、出貨）已經評估過影響了嗎？ <br>_理由：已上線主體的改版與全新主體是兩件事：前者每一個欄位變動都有既存的下游依賴，需要先確認爆炸半徑。_ <br>_依據：config/Common/knowhow/advisory/production_reuse_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.production_reuse_semantic` | `orders.customer_id → CRM.dim_customer` | 本主體已用三段式引用客戶主檔（`CRM.dim_customer`），這是正確的複用。反過來看：正式區的 `CRM.dim_customer` 有沒有哪些屬性是本主體其實需要、但目前是靠下游自己 join 取得的？要不要在 context 明寫「客戶屬性一律 join 主檔取得」的使用約定？ <br>_理由：複用的價值要讓下游知道才成立；沒有寫下來的使用約定，下游還是可能自己複製一份客戶屬性。_ <br>_依據：config/Common/knowhow/advisory/production_reuse_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `orders.currency（換算基準）` | 前一輪確認一張訂單只有單一幣別——那跨幣別的營收合計要換算成本位幣時，匯率來自哪裡？這份匯率事實的權威擁有者是誰？ <br>_理由：匯率若沒有指定權威來源與適用時點（下單日、入帳日、月底），每個報表各自取值，跨幣別營收就無法對齊。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `orders.total_amount（對外請款金額）` | 前一輪確認 `total_amount` 是金流實際請款金額的權威——那金流平台自己那份交易金額算什麼？兩邊不一致時，對外（例如客服、發票）要以誰為準？ <br>_理由：同一筆金額在資料倉儲與金流系統各有一份時，若沒有宣告對外權威，客服與財務會拿到不同答案。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
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
| ✅ | 閘門 | `PRODUCTION.REUSE` | `(schema)` | 已引用正式區資產：`crm.dim_customer`。 <br>**期望** 新 subject 引用正式區的既有資產 ｜ **實際** 已引用 <br>_理由：複用已核准資產可避免同一事實出現第二份權威。_ <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `PRODUCTION.SCOPE` | `(production)` | 已參照 production domain：['CRM']。 <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `SKILL.ssot_fact_duplication` | `(schema)` | ssot_fact_duplication：已執行，未發現違規。 <br>_依據：config/Common/knowhow_py/ssot_fact_duplication.py_ | skill |
| ✅ | 閘門 | `SKILL.ssot_join_keys` | `order_id` | Join key 型別一致：'order_id' 於 2 表型別一致。 <br>_依據：config/Common/knowhow_py/ssot_join_keys.py_ | skill |
| ✅ | 閘門 | `SKILL.ssot_pii_amount_split` | `2 表` | 個資與金額應分表存放：2 表全數通過（orders、order_items） <br>_理由：PII 與金額混存使權限難分級、真實源歸屬模糊。_ <br>_依據：config/Common/knowhow/gating/ssot_pii_amount_split.md_ | skill |

## 資料設計概念（主體性）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `orders（取消單的母體語意）` | 前一輪確認營收彙總會排除取消訂單——那「下單量」「轉換率」這類母體型指標呢？取消單要算進分母嗎？ <br>_理由：同一張表同時服務金額型與計數型指標時，兩者的有效行定義往往不同；只定義營收口徑會讓計數型指標各自解讀。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `orders（部分退貨／換貨）` | `status` 只能表達整單取消，但實務上會有「退其中一個品項」——這類部分退貨的事實目前由哪個主體承載？本主體要不要負責？ <br>_理由：退貨事實若沒有明確歸屬，很容易被塞進訂單表（改金額或改狀態），破壞「訂單是下單當下快照」的定位。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `order_items.order_item_id` | `order_item_id` 是來源系統給的自然鍵，還是 ETL 端產生的代理鍵？如果訂單重送或明細重算，同一個商品項會拿到同一個 id 嗎？ <br>_理由：business key 若不是來源穩定值，重跑就會產生新的鍵，讓下游的增量比對與去重全部失效。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `orders.cancelled_at` | `cancelled_at` 是本 schema 唯一可為 NULL 的欄位，NULL 同時代表「尚未取消」——但「訂單已取消卻沒記到時間」也會是 NULL。這兩種情況在查詢時分得開嗎？ <br>_理由：以 NULL 承載業務狀態時，資料品質問題（漏寫）與正常狀態（未發生）會混在一起，無法用查詢區分。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |

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

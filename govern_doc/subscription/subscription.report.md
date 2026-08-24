# 資料設計驗證報告 — 第 1 輪迭代
_產生時間 2026-08-24T14:40:36.619791Z_<br>
**🔁 第 1／5 輪迭代報告**<br>
**判定：❌ 不合規**（會擋項目 11）<br>
通過 25 · 警告 12 · 失敗 11 · 略過 2 · 提示 16<br>
閘門區 50 項 · 顧問區 16 項<br>
> 方言 clickhouse · 表數 3 · 載入 skill 26 條
> 驗證 bundle `33dd3dfaf6486cca`（含規則、validator 與依賴版本）

## Checking rule ID 摘要
- ❌ 擋下：`LINEAGE.TYPE_COMPATIBILITY`、`SKILL.bp_money_decimal`、`SKILL.bp_no_float`、`SKILL.naming_column_case`、`SKILL.naming_columns_commented`、`SKILL.ssot_authority`、`SKILL.ssot_join_keys`
- ⚠️ 警告：`DOMAIN.SCOPE`、`SKILL.bp_datetime_timezone`、`SKILL.ssot_fact_duplication`、`SKILL.ssot_pii_amount_split`、`SKILL.structural_audit_columns`、`SSOT.UNREGISTERED_SUBJECT`
- ✅ 通過：`BUSINESS_KEY.METADATA`、`LINEAGE.COLUMN_EXISTS`、`LINEAGE.CYCLE`、`LINEAGE.DOMAIN_SCOPE`、`LINEAGE.METADATA`、`LINEAGE.UPSTREAM_EXISTS`、`PRODGRAPH.CARDINALITY_CONFLICT`、`PRODGRAPH.CYCLE`、`SKILL.bp_lowcardinality_status`、`SKILL.naming_glossary`、`SKILL.naming_identifier_length`、`SKILL.naming_pk_suffix`、`SKILL.naming_reserved_words`、`SKILL.naming_table_snake_case`、`SKILL.no_future_event_time`、`SKILL.structural_business_key`、`SKILL.structural_engine_mergetree`、`SKILL.structural_key_not_nullable`、`SKILL.structural_order_by`、`SKILL.structural_type_sample`
- ℹ️ 未實檢／略過：`PRODUCTION.SCOPE`、`SKILL.structural_fk_resolves`
- 💡 顧問：`CONCEPT.SUBJECT`、`NAME.SEMANTIC`、`SKILL.best_practice_semantic`、`SKILL.naming_semantic`、`SKILL.ssot_semantic`

## 規則涵蓋清單
> 宣告域（context.md）：（未指定，僅 Common） · config 可用域：BLM、CRM、Common、FCM、PLM、SCM
> 涵蓋：載入並執行 **26** 條 ／ config 共 **40** 條

### ✅ 已載入並執行（26 條）
- `SKILL.best_practice_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/best_practice_semantic.md
- `SKILL.bp_datetime_timezone`（Common）→ ⚠️ 警告 ｜ config/Common/knowhow/gating/bp_datetime_timezone.md
- `SKILL.bp_lowcardinality_status`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/bp_lowcardinality_status.md
- `SKILL.bp_money_decimal`（Common）→ ❌ 擋下 ｜ config/Common/knowhow/gating/bp_money_decimal.md
- `SKILL.bp_no_float`（Common）→ ❌ 擋下 ｜ config/Common/knowhow/gating/bp_no_float.md
- `SKILL.naming_column_case`（Common）→ ❌ 擋下 ｜ config/Common/knowhow/gating/naming_column_case.md
- `SKILL.naming_columns_commented`（Common）→ ❌ 擋下 ｜ config/Common/knowhow/gating/naming_columns_commented.md
- `SKILL.naming_glossary`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_glossary.md
- `SKILL.naming_identifier_length`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_identifier_length.md
- `SKILL.naming_pk_suffix`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_pk_suffix.md
- `SKILL.naming_reserved_words`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_reserved_words.md
- `SKILL.naming_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/naming_semantic.md
- `SKILL.naming_table_snake_case`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/naming_table_snake_case.md
- `SKILL.no_future_event_time`（Common）→ ✅ 通過 ｜ config/Common/knowhow_py/no_future_event_time.py
- `SKILL.ssot_authority`（Common）→ ❌ 擋下 ｜ config/Common/knowhow_py/ssot_authority.py
- `SKILL.ssot_fact_duplication`（Common）→ ⚠️ 警告 ｜ config/Common/knowhow_py/ssot_fact_duplication.py
- `SKILL.ssot_join_keys`（Common）→ ❌ 擋下 ｜ config/Common/knowhow_py/ssot_join_keys.py
- `SKILL.ssot_pii_amount_split`（Common）→ ⚠️ 警告 ｜ config/Common/knowhow/gating/ssot_pii_amount_split.md
- `SKILL.ssot_semantic`（Common）→ 💡 顧問 ｜ config/Common/knowhow/advisory/ssot_semantic.md
- `SKILL.structural_audit_columns`（Common）→ ⚠️ 警告 ｜ config/Common/knowhow/gating/structural_audit_columns.md
- `SKILL.structural_business_key`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_business_key.md
- `SKILL.structural_engine_mergetree`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_engine_mergetree.md
- `SKILL.structural_fk_resolves`（Common）→ ℹ️ 未實檢／略過 ｜ config/Common/knowhow_py/structural_fk_resolves.py
- `SKILL.structural_key_not_nullable`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_key_not_nullable.md
- `SKILL.structural_order_by`（Common）→ ✅ 通過 ｜ config/Common/knowhow/gating/structural_order_by.md
- `SKILL.structural_type_sample`（Common）→ ✅ 通過 ｜ config/Common/knowhow_py/structural_type_sample.py

### ⏭️ 未載入：所屬域未在 context.md 宣告（14 條）
- **BLM**：`SKILL.blm_baseline`
- **CRM**：`SKILL.crm_baseline`
- **FCM**：`SKILL.fcm_baseline`、`SKILL.fcm_master_data_semantic`
- **PLM**：`SKILL.plm_bom_needs_quantity`、`SKILL.plm_bom_structural_integrity`、`SKILL.plm_engineering_change`、`SKILL.plm_lifecycle_stage`、`SKILL.plm_part_master_baseline`、`SKILL.plm_revision_versioning`
- **SCM**：`SKILL.scm_grn_needs_po`、`SKILL.scm_po_needs_supplier`、`SKILL.scm_supplier_baseline`、`SKILL.scm_supply_semantic`
> 若這些域也應納入檢查，請在 context.md front-matter 的 `domains` 補上該域後重跑。

## 迭代收斂（第 1 輪／上限 5）
> 收斂條件：無待答問題 ＋ 閘門合規
> 目前：❌ 未收斂 —— 待答 0 題、待驗證 17 題、閘門 fail 11 項

### ❓ 待答（0）
（無）

### 🟡 待驗證：agent 代填，請確認（17）
- `NAME.SEMANTIC@subscription.MonthlyPrice`（semantic）
  - Q: MonthlyPrice 除了命名風格（閘門已列）之外，語意上也看不出幣別與含稅狀態——訂閱可能跨幣別販售嗎？若可能，是否缺一個 currency 欄位；若固定單一幣別，這個前提記載在哪裡？
  - 代填答案: 訂閱目前僅以 TWD 計價，暫不加 currency 欄位；此前提補記於 context.md 的「這個 data subject 是什麼」段落，未來跨幣別販售時再增欄。
- `NAME.SEMANTIC@billing_event.amount`（semantic）
  - Q: amount 的正負語意是什麼——退款、調整是以負值表達，還是另有事件種類區分？下游對帳加總時是否可以直接 SUM(amount)？
  - 代填答案: amount 一律為正值，扣款／退款以未來的 event_type 欄位區分；在補上 event_type 之前，下游不應直接 SUM(amount)。
- `NAME.SEMANTIC@dim_customer`（semantic）
  - Q: 三張表的命名慣例不一致：dim_customer 帶維度前綴、subscription 與 billing_event 沒有分層前綴——這是刻意的嗎？之後晉升到 production 時，要不要統一「維度表 dim_、事實／事件表不加前綴」之類的慣例並登錄到 naming 詞彙？
  - 代填答案: 統一採「維度表 dim_ 前綴、事實與事件表不加前綴」慣例，並登錄到 config/Common/naming 詞彙字典；本 subject 現有表名維持不變。
- `CONCEPT.SUBJECT@subscription`（structural → 建議改 subscription.sql）
  - Q: 一行代表「一筆訂閱（含歷史訂閱）」，但表上只有 started_at——訂閱的生命週期（生效中／已取消／已到期）與結束時間如何表達？沒有 status 或 ended_at 時，「目前有效訂閱數」這種基本指標要怎麼算？
  - 代填答案: 在 subscription 表增加 status（active/cancelled/expired）與 ended_at（Nullable）兩欄，由訂閱服務維護生命週期。
- `CONCEPT.SUBJECT@billing_event`（structural → 建議改 subscription.sql）
  - Q: 計費事件只掛 customer_id、沒有 subscription_id——同一客戶有多筆訂閱時，一次計費事件要如何歸屬到特定訂閱？「訂閱營收分析」這個用途是否其實需要訂閱粒度的歸屬？
  - 代填答案: 在 billing_event 增加 subscription_id 欄位並於 relations.yaml 宣告對 subscription 的 N:1 關聯，讓計費事件可歸屬到單筆訂閱。
- `CONCEPT.SUBJECT@dim_customer`（semantic）
  - Q: 客戶主檔權威在 CRM，本 subject 又建了一張 dim_customer——它的定位是 CRM 主檔的同步副本（只讀、欄位子集）還是新的權威？若是副本，同步頻率與允許滯後記載在哪裡？
  - 代填答案: dim_customer 定位為 CRM 客戶主檔的只讀同步副本（日批），僅保留分析需要的欄位子集；此定位與同步頻率補記於 context.md 上下游段落。
- `SKILL.best_practice_semantic@billing_event`（structural → 建議改 subscription.sql）
  - Q: billing_event 是事件表，但沒有 event_type——扣款、退款、方案調整都混在同一種事件裡嗎？事件表的最佳實踐通常需要事件種類欄位，這裡是刻意省略還是尚未設計？
  - 代填答案: 增加 event_type（LowCardinality(String)：charge/refund/adjustment）欄位，於寫入端強制枚舉值。
- `SKILL.best_practice_semantic@subscription`（structural → 建議改 subscription.sql）
  - Q: subscription 表有 created_at 但沒有 updated_at，dim_customer 兩者皆有——訂閱資料（例如未來的狀態變更）會就地更新嗎？若會，缺 updated_at 是否影響增量同步與稽核？
  - 代填答案: 為 subscription 補上 updated_at 稽核欄位，與 dim_customer 的稽核欄位慣例對齊。
- `SKILL.naming_semantic@billing_event.occurred_at`（semantic）
  - Q: subscription 用 started_at、billing_event 用 occurred_at、兩表又都有 created_at——這三種時間的語意分工（業務發生 vs 資料寫入）是否已明文化，確保營收分析一律以 occurred_at 彙總？
  - 代填答案: 約定：occurred_at／started_at 為業務發生時間（分析用），created_at 為資料寫入時間（稽核用）；登錄到 naming 詞彙字典。
- `SKILL.ssot_semantic@subscription.MonthlyPrice`（semantic）
  - Q: MonthlyPrice（訂閱月費）與 billing_event.amount（實際計費金額）之間的權威關係是什麼——月費調整後歷史事件金額不變？對帳時發現兩者不一致，以哪邊為準？
  - 代填答案: billing_event.amount 是實際請款的權威（事件快照）；MonthlyPrice 僅是目前定價，兩者允許不一致；營收一律以 billing_event 加總。此邊界登錄到 SSOT 文件。
- `NAME.SEMANTIC@subscription.MonthlyPrice / billing_event.amount`（semantic）
  - Q: 兩個金額欄一個叫 `price`、一個叫 `amount`——它們是同一條金流的兩個階段（應收 vs 實收），還是各自獨立的事實？從欄名分不出來。
  - 代填答案: 是同一條金流的兩個階段：`monthly_price` 是應收的合約定價，`amount` 是該次計費實際發生的金額。建議在 context.md 明寫這組對應關係，作為對帳口徑。
- `SKILL.best_practice_semantic@dim_customer`（semantic）
  - Q: 維度表帶了 `updated_at` 卻沒有版本或有效區間欄——客戶分級變動時，是直接覆寫舊值嗎？覆寫後過去的訂閱分析還能還原當時的分級嗎？
  - 代填答案: 目前為覆寫式（Type 1），可接受；若訂閱營收需要按「簽約當時分級」拆解，改以在事實表快照分級（Type 2 的輕量替代）處理，不建議整張表改成 Type 2。
- `SKILL.naming_semantic@subscription.customer_id / dim_customer.customer_id / billing_event.customer_id`（structural → 建議改 subscription.sql）
  - Q: 三張表都有 `customer_id`，指的確定是同一個客戶實體嗎？如果是，它們的編碼是否同源（同一份號碼、同一種格式）？
  - 代填答案: 三者都是 CRM 客戶主檔的同一份客戶編號、同源。`subscription.customer_id` 目前的型別與另外兩張表不一致，應統一為與 `dim_customer.customer_id` 相同的整數型別。
- `SKILL.naming_semantic@subscription.started_at / subscription.created_at`（structural → 建議改 subscription.sql）
  - Q: `started_at`（訂閱生效）與 `created_at`（資料建立）兩個時間欄命名形式相同——分析師要算訂閱起始時，看得出該用哪一個嗎？
  - 代填答案: `started_at` 是業務生效時間（所有訂閱期間分析一律用它），`created_at` 僅供稽核與增量抽取。建議補上 COMMENT 並寫進 context.md。
- `SKILL.ssot_semantic@subscription.customer_email`（structural → 建議改 subscription.sql）
  - Q: 客戶 email 同時存在 `dim_customer` 與 `subscription` 兩張表——當客戶更新 email 時，兩邊會同時更新嗎？如果不會，哪一邊才是對外可信的那份？
  - 代填答案: 權威在客戶主檔（CRM → `dim_customer.customer_email`）。`subscription.customer_email` 屬於重複承載，應移除；若是為了保留「訂閱當下的聯絡信箱」，則應改名為 `contact_email_at_signup` 並註明是快照。
- `SKILL.ssot_semantic@dim_customer（本主體） vs CRM 客戶主檔`（structural → 建議改 config/Common/ssot/registry.yaml）
  - Q: 同一個客戶實體在本主體與 CRM 各有一張表，看起來有兩個權威擁有者候選——SSOT 登錄上要把誰記為權威？
  - 代填答案: 唯一權威是 CRM 的客戶主檔；本主體的 `dim_customer` 登錄為副本（replica），不進 SSOT registry 的權威欄位。建議晉升前先確認 CRM 主檔已在 production，再以三段式引用取代本地副本。
- `SKILL.ssot_semantic@subscription.MonthlyPrice vs billing_event.amount`（semantic）
  - Q: 月費與實際計費金額是兩份金額事實——對帳出現差異時（例如首月比例計費、折扣、退款），要以哪一邊為準？差異要記在哪裡？
  - 代填答案: 實收以 `billing_event.amount` 為權威（它對應金流實際發生的交易）；`monthly_price` 只是應收基準。差異原因（比例計費、折扣、退款）應由 `billing_event` 的事件類型與折扣欄位交代，不在訂閱表回寫。
> 驗證：到 input/<名>/answers.yaml 把 `status: proposed` 改為 `answered`（答案可修改；不想追的改 `deferred`）。待驗證不算已答，會擋收斂。

### ✅ 已解（0）
（無）

### 📝 本輪 input 變更
（首輪——無前輪可比；本輪輸入已快照到 iterations/）

## 表總覽（一 subject＝一組表）

| 表 | 來源檔 | 欄數 | Business Key | ❌ 擋 | ⚠️ 警告 | 表間關係 | 設計對照 |
|---|---|---|---|---|---|---|---|
| `dim_customer` | subscription.sql | 6 | `customer_id` | 1 | 1 | — | —（未經設計） |
| `subscription` | subscription.sql | 6 | `subscription_id` | 5 | 4 | → dim_customer（N:1） | —（未經設計） |
| `billing_event` | subscription.sql | 4 | `event_id` | 3 | 3 | → dim_customer（N:1） | —（未經設計） |

## 設計對照（design mode 設計稿 ↔ input DDL）
> ⚠️ 此 subject **未經過設計模式**（design mode）——input DDL 為手寫直接進治理，沒有設計稿可對照。
> 建議：新主體先以 `input/<名>/context.md` 走設計流程（產生設計文件與可對照的設計稿），再定稿進治理。

## Lineage 關聯
> 關係來自 relations.yaml；這是設計宣告，不代表已觀測到執行血緣。

| 來源 | 目標 | 欄位映射 | 性質 |
|---|---|---|---|
| `local.dim_customer` | `billing_event` | `customer_id` → `customer_id` | YAML 明確宣告 |
| `local.dim_customer` | `subscription` | `customer_id` → `customer_id` | YAML 明確宣告 |

## 本次卡控摘要（被哪些規則卡下來）
**擋下（不合規的原因）：**
- `LINEAGE.TYPE_COMPATIBILITY` LINEAGE.TYPE_COMPATIBILITY → 擋下 local.dim_customer.customer_id → subscription.customer_id（lineage 來源與目標欄位型別不相容。）
- `SKILL.bp_money_decimal` 金額欄位必須用 Decimal → 擋下 billing_event、subscription（金額類欄位使用了 float：['amount']）
- `SKILL.bp_no_float` 不可使用 Float 型別 → 擋下 billing_event、subscription（使用了不建議的型別 Float：['amount']）
- `SKILL.naming_column_case` 欄位名須為 snake_case 全小寫 → 擋下 subscription（欄位名不符樣式：['MonthlyPrice']）
- `SKILL.naming_columns_commented` 所有欄位必須有 COMMENT 註解 → 擋下 billing_event、dim_customer、subscription（欄位缺少註解：['event_id', 'customer_id', 'amount', 'occurred_at']）
- `SKILL.ssot_authority` 權威唯一性 → 擋下 subscription（此表重複承載 'customer' 的權威屬性 ['customer_email']（權威表：dim_customer））
- `SKILL.ssot_join_keys` Join key 型別一致 → 擋下 customer_id（'customer_id' 跨表型別不一致 [('dim_customer', 'int'), ('subscripti）

**警告（放行但需注意）：**
- `DOMAIN.SCOPE` DOMAIN.SCOPE → (domains)
- `SKILL.bp_datetime_timezone` DateTime 應標明時區 → billing_event、dim_customer、subscription
- `SKILL.ssot_authority` 權威表在場檢視 → dim_product
- `SKILL.ssot_fact_duplication` 事實重複 → customer_email
- `SKILL.ssot_join_keys` Join key 值編碼 → customer_id
- `SKILL.ssot_pii_amount_split` 個資與金額應分表存放 → subscription
- `SKILL.structural_audit_columns` 表應有稽核欄位（created_at / updated_at） → billing_event、subscription
- `SSOT.UNREGISTERED_SUBJECT` 未登錄主體候選 'event' → billing_event、subscription

## 結構（欄位／型別／約束）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ⚠️ | 閘門 | `DOMAIN.SCOPE` | `(domains)` | 未指定 domain，依安全預設只載入 Common。 <br>**期望** 在 context.md front-matter 明確指定業務 domain ｜ **實際** 未指定 <br>**修法** 新增 domains；若確定只需共用規則可保持現狀 <br>_依據：input/<名>/context.md（front-matter domains）→ config/<域>/_ | rule |
| ⚠️ | 閘門 | `SKILL.structural_audit_columns` | `billing_event` | 表應有稽核欄位（created_at / updated_at）：缺少必要欄位 'created_at'；缺少必要欄位 'updated_at' <br>**期望** 表上有欄位 created_at；表上有欄位 updated_at ｜ **實際** 欄位不存在 <br>**修法** 新增欄位 created_at；新增欄位 updated_at <br>_理由：稽核欄位支撐血緣追蹤與變更歷史。_ <br>_依據：config/Common/knowhow/gating/structural_audit_columns.md_ | skill |
| ⚠️ | 閘門 | `SKILL.structural_audit_columns` | `subscription` | 表應有稽核欄位（created_at / updated_at）：缺少必要欄位 'updated_at' <br>**期望** 表上有欄位 updated_at ｜ **實際** 欄位不存在 <br>**修法** 新增欄位 updated_at <br>_理由：稽核欄位支撐血緣追蹤與變更歷史。_ <br>_依據：config/Common/knowhow/gating/structural_audit_columns.md_ | skill |
| ⏭️ | 閘門 | `SKILL.structural_fk_resolves` | `(schema)` | structural_fk_resolves：本次 schema 沒有可檢查的 FK。 <br>_依據：config/Common/knowhow_py/structural_fk_resolves.py_ | skill |
| ✅ | 閘門 | `BUSINESS_KEY.METADATA` | `(schema)` | Business key metadata 已驗證：['billing_event', 'dim_customer', 'subscription']。 <br>_依據：input/<名>/context.md（front-matter business_keys）_ | rule |
| ✅ | 閘門 | `SKILL.structural_audit_columns` | `1 表` | 表應有稽核欄位（created_at / updated_at）：1 表全數通過（dim_customer） <br>_理由：稽核欄位支撐血緣追蹤與變更歷史。_ <br>_依據：config/Common/knowhow/gating/structural_audit_columns.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_business_key` | `3 表` | 表必須有 Business Key：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：每張表需要穩定的業務識別鍵，才能被正確引用、合併與去重。 ClickHouse ORDER BY 只是物理排序鍵，不等於業務唯一性。_ <br>_依據：config/Common/knowhow/gating/structural_business_key.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_engine_mergetree` | `3 表` | 明細表引擎須為 MergeTree 系列（ClickHouse）：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：明細層資料應使用 MergeTree 家族引擎（MergeTree / ReplacingMergeTree 等）。_ <br>_依據：config/Common/knowhow/gating/structural_engine_mergetree.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_key_not_nullable` | `3 表` | 鍵欄位不可為 Nullable：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：主鍵／排序鍵為 Nullable 會破壞合併與去重語意，並帶來額外標記欄位開銷。_ <br>_依據：config/Common/knowhow/gating/structural_key_not_nullable.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_order_by` | `3 表` | 表必須有 ORDER BY（ClickHouse）：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：MergeTree 家族依 ORDER BY 建立稀疏索引，缺少它等於放棄索引。_ <br>_依據：config/Common/knowhow/gating/structural_order_by.md_ | skill |
| ✅ | 閘門 | `SKILL.structural_type_sample` | `(sample)` | 型別對樣本檢查：48 個樣本值全數通過。 <br>_依據：config/Common/knowhow_py/structural_type_sample.py_ | skill |

## 命名規則

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ❌ | 閘門 | `SKILL.naming_column_case` | `subscription` | 欄位名須為 snake_case 全小寫：欄位名不符樣式：['MonthlyPrice'] <br>**期望** 符合 /[a-z][a-z0-9_]*/ ｜ **實際** MonthlyPrice <br>**修法** 依樣式重新命名（snake_case 全小寫） <br>_理由：欄位命名樣式一致是資料字典與自動化的基礎。_ <br>_依據：config/Common/knowhow/gating/naming_column_case.md_ | skill |
| ❌ | 閘門 | `SKILL.naming_columns_commented` | `billing_event` | 所有欄位必須有 COMMENT 註解：欄位缺少註解：['event_id', 'customer_id', 'amount', 'occurred_at'] <br>**期望** 每個欄位都有 COMMENT ｜ **實際** 4 欄無註解 ['event_id', 'customer_id', 'amount', 'occurred_at'] <br>**修法** 為每個欄位補上 COMMENT '說明' <br>_理由：欄位註解是資料字典的最小單位，中介資料平台會直接讀取。_ <br>_依據：config/Common/knowhow/gating/naming_columns_commented.md_ | skill |
| ❌ | 閘門 | `SKILL.naming_columns_commented` | `dim_customer` | 所有欄位必須有 COMMENT 註解：欄位缺少註解：['customer_id', 'customer_name', 'customer_email', 'customer_tier', 'created_at', 'updated_at'] <br>**期望** 每個欄位都有 COMMENT ｜ **實際** 6 欄無註解 ['customer_id', 'customer_name', 'customer_email', 'customer_tier', 'created_at', 'updated_at'] <br>**修法** 為每個欄位補上 COMMENT '說明' <br>_理由：欄位註解是資料字典的最小單位，中介資料平台會直接讀取。_ <br>_依據：config/Common/knowhow/gating/naming_columns_commented.md_ | skill |
| ❌ | 閘門 | `SKILL.naming_columns_commented` | `subscription` | 所有欄位必須有 COMMENT 註解：欄位缺少註解：['subscription_id', 'customer_id', 'customer_email', 'MonthlyPrice', 'started_at', 'created_at'] <br>**期望** 每個欄位都有 COMMENT ｜ **實際** 6 欄無註解 ['subscription_id', 'customer_id', 'customer_email', 'MonthlyPrice', 'started_at', 'created_at'] <br>**修法** 為每個欄位補上 COMMENT '說明' <br>_理由：欄位註解是資料字典的最小單位，中介資料平台會直接讀取。_ <br>_依據：config/Common/knowhow/gating/naming_columns_commented.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_column_case` | `2 表` | 欄位名須為 snake_case 全小寫：2 表全數通過（dim_customer、billing_event） <br>_理由：欄位命名樣式一致是資料字典與自動化的基礎。_ <br>_依據：config/Common/knowhow/gating/naming_column_case.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_glossary` | `3 表` | 命名對照詞彙字典：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：欄位命名應使用公司認可的標準詞，避免縮寫與同義異名造成理解成本與整合困難。 此規則對照各 domain naming 資料夾的詞彙表（config/*/naming/*.md，md 表格； Common 恆載入、domain 疊加）做檢查，比寫一堆正則更易維護。_ <br>_依據：config/Common/knowhow/gating/naming_glossary.md（詞彙字典：config/Common/naming/）_ | skill |
| ✅ | 閘門 | `SKILL.naming_identifier_length` | `3 表` | 表名不超過 64、欄名不超過 48 字元：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：過長的表名／欄名不利閱讀、跨工具相容與下游引用。 表名上限 64 字元、欄位名上限 48 字元，超過即擋。_ <br>_依據：config/Common/knowhow/gating/naming_identifier_length.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_pk_suffix` | `3 表` | 主鍵欄位建議以 _id 結尾：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：可預測的鍵名（x_id）讓 join 推斷與理解更容易。_ <br>_依據：config/Common/knowhow/gating/naming_pk_suffix.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_reserved_words` | `3 表` | 欄位名避免 SQL 保留字：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：使用保留字當欄名需要跳脫，易出錯。_ <br>_依據：config/Common/knowhow/gating/naming_reserved_words.md_ | skill |
| ✅ | 閘門 | `SKILL.naming_table_snake_case` | `3 表` | 表名須為 snake_case 全小寫：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：一致的表名讓資產可預測、可被工具處理。_ <br>_依據：config/Common/knowhow/gating/naming_table_snake_case.md_ | skill |

## 最佳實踐

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ❌ | 閘門 | `SKILL.bp_money_decimal` | `billing_event` | 金額欄位必須用 Decimal：金額類欄位使用了 float：['amount'] <br>**期望** 金額類欄位為 Decimal(P,S) ｜ **實際** amount:Float64 <br>**修法** amount 改為 Decimal(18,2) <br>_理由：名稱含 amount/price/cost/fee 等的金額欄位，使用浮點數會導致對帳不平。_ <br>_依據：config/Common/knowhow/gating/bp_money_decimal.md_ | skill |
| ❌ | 閘門 | `SKILL.bp_money_decimal` | `subscription` | 金額欄位必須用 Decimal：金額類欄位使用了 float：['MonthlyPrice'] <br>**期望** 金額類欄位為 Decimal(P,S) ｜ **實際** MonthlyPrice:Float64 <br>**修法** MonthlyPrice 改為 Decimal(18,2) <br>_理由：名稱含 amount/price/cost/fee 等的金額欄位，使用浮點數會導致對帳不平。_ <br>_依據：config/Common/knowhow/gating/bp_money_decimal.md_ | skill |
| ❌ | 閘門 | `SKILL.bp_no_float` | `billing_event` | 不可使用 Float 型別：使用了不建議的型別 Float：['amount'] <br>**期望** 不使用 Float ｜ **實際** amount:Float64 <br>**修法** 數值精確性需求改用 Decimal(P,S) <br>_理由：Float 不適合需要精確比較與彙總的數值。_ <br>_依據：config/Common/knowhow/gating/bp_no_float.md_ | skill |
| ❌ | 閘門 | `SKILL.bp_no_float` | `subscription` | 不可使用 Float 型別：使用了不建議的型別 Float：['MonthlyPrice'] <br>**期望** 不使用 Float ｜ **實際** MonthlyPrice:Float64 <br>**修法** 數值精確性需求改用 Decimal(P,S) <br>_理由：Float 不適合需要精確比較與彙總的數值。_ <br>_依據：config/Common/knowhow/gating/bp_no_float.md_ | skill |
| ⚠️ | 閘門 | `SKILL.bp_datetime_timezone` | `billing_event` | DateTime 應標明時區：DateTime 未標明時區：['occurred_at'] <br>**期望** DateTime('UTC') 或註解標明時區 ｜ **實際** occurred_at <br>**修法** 改用 DateTime('UTC') 或於 COMMENT 註明時區 <br>_理由：時區不明的時間在跨區情境無法正確比較，應以 DateTime('UTC') 或註解標明。_ <br>_依據：config/Common/knowhow/gating/bp_datetime_timezone.md_ | skill |
| ⚠️ | 閘門 | `SKILL.bp_datetime_timezone` | `dim_customer` | DateTime 應標明時區：DateTime 未標明時區：['created_at', 'updated_at'] <br>**期望** DateTime('UTC') 或註解標明時區 ｜ **實際** created_at；updated_at <br>**修法** 改用 DateTime('UTC') 或於 COMMENT 註明時區 <br>_理由：時區不明的時間在跨區情境無法正確比較，應以 DateTime('UTC') 或註解標明。_ <br>_依據：config/Common/knowhow/gating/bp_datetime_timezone.md_ | skill |
| ⚠️ | 閘門 | `SKILL.bp_datetime_timezone` | `subscription` | DateTime 應標明時區：DateTime 未標明時區：['started_at', 'created_at'] <br>**期望** DateTime('UTC') 或註解標明時區 ｜ **實際** started_at；created_at <br>**修法** 改用 DateTime('UTC') 或於 COMMENT 註明時區 <br>_理由：時區不明的時間在跨區情境無法正確比較，應以 DateTime('UTC') 或註解標明。_ <br>_依據：config/Common/knowhow/gating/bp_datetime_timezone.md_ | skill |
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `billing_event` | 這是一張 append-only 的事件表，但沒有看到來源系統的事件識別碼——上游重送同一筆計費通知時，要靠什麼去重？ <br>_理由：計費事件重複寫入會直接放大營收數字，而事件表通常沒有唯一約束可以擋。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `billing_event.occurred_at` | 事件表會持續累積，目前沒有分區宣告——之後要查「某月的計費事件」時，掃描成本是否還能接受？ <br>_理由：時間序列事件表若不依事件時間分區，時間範圍查詢與月結重跑都會退化成全表操作。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.best_practice_semantic` | `dim_customer` | 維度表帶了 `updated_at` 卻沒有版本或有效區間欄——客戶分級變動時，是直接覆寫舊值嗎？覆寫後過去的訂閱分析還能還原當時的分級嗎？ <br>_理由：維度覆寫（SCD Type 1）會讓歷史報表隨維度變動而改變，這通常不是分析端預期的行為。_ <br>_依據：config/Common/knowhow/advisory/best_practice_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.naming_semantic` | `subscription.customer_id / dim_customer.customer_id / billing_event.customer_id` | 三張表都有 `customer_id`，指的確定是同一個客戶實體嗎？如果是，它們的編碼是否同源（同一份號碼、同一種格式）？ <br>_理由：同名鍵不一定同義；跨表 join 前若沒有確認編碼同源，join 會安靜地少掉一部分資料而不報錯。_ <br>_依據：config/Common/knowhow/advisory/naming_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.naming_semantic` | `subscription.started_at / subscription.created_at` | `started_at`（訂閱生效）與 `created_at`（資料建立）兩個時間欄命名形式相同——分析師要算訂閱起始時，看得出該用哪一個嗎？ <br>_理由：業務時間與稽核時間同形命名時，最容易被誤用來做期間彙總。_ <br>_依據：config/Common/knowhow/advisory/naming_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `dim_customer（本主體） vs CRM 客戶主檔` | 同一個客戶實體在本主體與 CRM 各有一張表，看起來有兩個權威擁有者候選——SSOT 登錄上要把誰記為權威？ <br>_理由：權威擁有者不唯一時，跨域引用會出現「該 join 哪一張」的分歧，影響分析也算不準。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `subscription.MonthlyPrice vs billing_event.amount` | 月費與實際計費金額是兩份金額事實——對帳出現差異時（例如首月比例計費、折扣、退款），要以哪一邊為準？差異要記在哪裡？ <br>_理由：應收與實收兩份金額若沒有宣告權威與差異來源，帳務對不平時無法定位問題出在定價、折扣還是金流。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ℹ️ | 顧問 | `SKILL.ssot_semantic` | `subscription.customer_email` | 客戶 email 同時存在 `dim_customer` 與 `subscription` 兩張表——當客戶更新 email 時，兩邊會同時更新嗎？如果不會，哪一邊才是對外可信的那份？ <br>_理由：同一事實存兩處而沒有宣告權威方時，兩份資料會逐漸分歧，而使用者無從得知自己查到的是哪一版。_ <br>_依據：config/Common/knowhow/advisory/ssot_semantic.md_ | llm |
| ✅ | 閘門 | `SKILL.bp_lowcardinality_status` | `3 表` | status 欄位須用 LowCardinality（ClickHouse）：3 表全數通過（dim_customer、subscription、billing_event） <br>_理由：低基數高重複欄位以 LowCardinality 儲存可大幅省空間與記憶體。_ <br>_依據：config/Common/knowhow/gating/bp_lowcardinality_status.md_ | skill |
| ✅ | 閘門 | `SKILL.bp_money_decimal` | `1 表` | 金額欄位必須用 Decimal：1 表全數通過（dim_customer） <br>_理由：名稱含 amount/price/cost/fee 等的金額欄位，使用浮點數會導致對帳不平。_ <br>_依據：config/Common/knowhow/gating/bp_money_decimal.md_ | skill |
| ✅ | 閘門 | `SKILL.bp_no_float` | `1 表` | 不可使用 Float 型別：1 表全數通過（dim_customer） <br>_理由：Float 不適合需要精確比較與彙總的數值。_ <br>_依據：config/Common/knowhow/gating/bp_no_float.md_ | skill |
| ✅ | 閘門 | `SKILL.no_future_event_time` | `(schema)` | no_future_event_time：已執行，未發現違規。 <br>_依據：config/Common/knowhow_py/no_future_event_time.py_ | skill |

## 單一真實源（跨域）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ❌ | 閘門 | `SKILL.ssot_authority` | `subscription` | 權威唯一性：此表重複承載 'customer' 的權威屬性 ['customer_email']（權威表：dim_customer）。應引用而非複製。 <br>**期望** 'customer' 的屬性只在權威表 dim_customer 落地 ｜ **實際** subscription 重複承載 ['customer_email'] <br>**修法** 移除 ['customer_email']，改以 customer_id 關聯 dim_customer <br>_理由：同一實體兩個擁有者破壞單一真實源。_ <br>_依據：config/Common/knowhow_py/ssot_authority.py_ | skill |
| ❌ | 閘門 | `SKILL.ssot_join_keys` | `customer_id` | Join key 型別一致：'customer_id' 跨表型別不一致 [('dim_customer', 'int'), ('subscription', 'string'), ('billing_event', 'int')]。 <br>**期望** 'customer_id' 在所有表同一 base type ｜ **實際** dim_customer:int；subscription:string；billing_event:int <br>**修法** 統一型別（建議與權威表一致） <br>_理由：型別不符的跨域 join 不安全。_ <br>_依據：config/Common/knowhow_py/ssot_join_keys.py_ | skill |
| ⚠️ | 閘門 | `SKILL.ssot_authority` | `dim_product` | 權威表在場檢視：'product' 的權威表不在本次 DDL。 <br>_理由：若它屬於另一 domain 的 schema 則屬正常。_ <br>_依據：config/Common/knowhow_py/ssot_authority.py_ | skill |
| ⚠️ | 閘門 | `SKILL.ssot_fact_duplication` | `customer_email` | 事實重複：'customer_email' 出現在 ['dim_customer', 'subscription']；宣告擁有者為 'dim_customer'，其餘表應由它同步衍生。 <br>_理由：重複事實會漂移失同步。_ <br>_依據：config/Common/knowhow_py/ssot_fact_duplication.py_ | skill |
| ⚠️ | 閘門 | `SKILL.ssot_join_keys` | `customer_id` | Join key 值編碼：'customer_id' 樣本值形態不一 {'dim_customer': 'int', 'subscription': 'digits_len7_zeropad', 'billing_event': 'int'}。 <br>_理由：編碼不一（如補零與否）會讓 join 對不上。_ <br>_依據：config/Common/knowhow_py/ssot_join_keys.py_ | skill |
| ⚠️ | 閘門 | `SKILL.ssot_pii_amount_split` | `subscription` | 個資與金額應分表存放：欄位 'customer_email' 與 'MonthlyPrice' 不應同時存在 <br>**期望** customer_email、MonthlyPrice 擇一或分表 ｜ **實際** 兩者並存 <br>**修法** 將其中一者移至其權威表，以鍵引用 <br>_理由：PII 與金額混存使權限難分級、真實源歸屬模糊。_ <br>_依據：config/Common/knowhow/gating/ssot_pii_amount_split.md_ | skill |
| ⚠️ | 閘門 | `SSOT.UNREGISTERED_SUBJECT` | `billing_event` | 未登錄主體候選 'event'：此表看似其權威表（證據欄位 ['amount', 'occurred_at']），但 SSOT registry 尚未登錄。建議先登錄再上線。 <br>**期望** 'event' 已登錄於 ssot.registry ｜ **實際** registry 查無此主體 <br>**修法** 於 config/default.yaml 的 ssot.registry 登錄 'event'（權威表 billing_event） <br>_理由：新 data subject 應先登錄權威表，否則跨域 SSOT 硬檢查無法涵蓋它。可由顧問區產 registry 草稿、人工確認後寫回。_ <br>_依據：config/<域>/ssot/registry.yaml（SSOT 登錄推斷）_ | rule |
| ⚠️ | 閘門 | `SSOT.UNREGISTERED_SUBJECT` | `subscription` | 未登錄主體候選 'subscription'：此表看似其權威表（證據欄位 ['customer_email', 'MonthlyPrice', 'started_at']），但 SSOT registry 尚未登錄。建議先登錄再上線。 <br>**期望** 'subscription' 已登錄於 ssot.registry ｜ **實際** registry 查無此主體 <br>**修法** 於 config/default.yaml 的 ssot.registry 登錄 'subscription'（權威表 subscription） <br>_理由：新 data subject 應先登錄權威表，否則跨域 SSOT 硬檢查無法涵蓋它。可由顧問區產 registry 草稿、人工確認後寫回。_ <br>_依據：config/<域>/ssot/registry.yaml（SSOT 登錄推斷）_ | rule |
| ⏭️ | 閘門 | `PRODUCTION.SCOPE` | `(production)` | 未明確指定業務 domain，不參照 production 基準區。 <br>_依據：production/<域>/（已核准 DDL 基準）_ | rule |
| ✅ | 閘門 | `SKILL.ssot_pii_amount_split` | `2 表` | 個資與金額應分表存放：2 表全數通過（dim_customer、billing_event） <br>_理由：PII 與金額混存使權限難分級、真實源歸屬模糊。_ <br>_依據：config/Common/knowhow/gating/ssot_pii_amount_split.md_ | skill |

## 資料設計概念（主體性）

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `billing_event` | 計費事件目前只掛 `customer_id`，沒有 `subscription_id`——同一位客戶有多筆訂閱時（粒度宣告允許），這次計費是哪一筆訂閱產生的？ <br>_理由：事件掛在客戶層而非合約層，會讓「單一訂閱的營收」無法計算，也無法對出哪一筆訂閱欠費。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `billing_event.amount` | 計費事件沒有事件類型欄（扣款／退款／重試失敗）——金額的正負或事件的成敗，目前是靠什麼表達？ <br>_理由：把多種事件混在同一張表卻沒有類型欄，彙總營收時會把退款與扣款相加，且無法區分失敗的請款嘗試。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `dim_customer` | context 說「客戶主檔的權威在 CRM」，但本 subject 自己也建了一張 `dim_customer`——這張表是 CRM 的唯讀副本、還是本領域自己維護的另一份客戶資料？ <br>_理由：同名維度表同時存在於兩個領域而沒有宣告主從關係時，資料不一致只是時間問題，且沒有人知道該修哪一邊。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `CONCEPT.SUBJECT` | `subscription` | 粒度宣告「一行 = 一筆訂閱（含歷史訂閱）」，但表裡只有 `started_at`，沒有結束時間或狀態欄——要怎麼分辨哪些訂閱現在還有效？ <br>_理由：含歷史的合約表若沒有結束時間或狀態，「目前有效訂閱數」這個最基本的指標就無法從表本身算出來。_ <br>_依據：顧問區 LLM（主體性概念層；情境來自 context.md）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `billing_event` | 表名 `billing_event` 沒有表達它屬於訂閱這條業務線，而同一個 subject 裡另外兩張表是 `dim_customer`、`subscription`——之後其他業務也有計費事件時，這個表名還夠指認嗎？ <br>_理由：事件表若以通用名稱命名，跨主體整合時容易與其他來源的計費事件混淆。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `dim_customer.customer_tier` | `customer_tier` 是「客戶目前的分級」還是「某個時點的分級」？訂閱營收要按分級拆解時，用的是簽約當下的分級還是查詢當下的分級？ <br>_理由：維度表的屬性若沒有時間語意，歷史分析會拿現在的分級去解釋過去的營收（緩慢變化維度的典型陷阱）。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `subscription.MonthlyPrice` | 這個欄位名稱只說了「月費」，沒有表達幣別、含稅與否，也看不出是「合約定價」還是「實際收取金額」——訂閱營收分析要用哪一個語意？ <br>_理由：訂閱制的合約定價與實收金額經常不同（折扣、比例計費、升降級），欄名若不表態，下游只能猜。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |
| ℹ️ | 顧問 | `NAME.SEMANTIC` | `subscription.MonthlyPrice / billing_event.amount` | 兩個金額欄一個叫 `price`、一個叫 `amount`——它們是同一條金流的兩個階段（應收 vs 實收），還是各自獨立的事實？從欄名分不出來。 <br>_理由：同一份 schema 內混用 price／amount 而沒有語意分工說明時，對帳的人無法判斷該把哪兩個數字相比。_ <br>_依據：顧問區 LLM（命名語意）_ | llm |

## Lineage 關聯治理

| | 區 | 檢查 | 對象 | 說明 | 來源 |
|---|---|---|---|---|---|
| ❌ | 閘門 | `LINEAGE.TYPE_COMPATIBILITY` | `local.dim_customer.customer_id → subscription.customer_id` | lineage 來源與目標欄位型別不相容。 <br>**期望** 目標基本型別 int ｜ **實際** 目標基本型別 string <br>**修法** 調整目標型別或改正 lineage 欄位映射。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.COLUMN_EXISTS` | `(lineage)` | 所有 lineage 欄位映射都可解析。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.CYCLE` | `(lineage)` | local lineage 未形成循環。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.DOMAIN_SCOPE` | `(lineage)` | 所有外部上游 domain 都已明確選取。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.METADATA` | `(lineage)` | relations.yaml 的 lineage 格式與目標表有效。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `LINEAGE.UPSTREAM_EXISTS` | `(lineage)` | 所有宣告的上游資料表都存在。 <br>_依據：input/<名>/relations.yaml（宣告關聯；外部端點對 production/）_ | rule |
| ✅ | 閘門 | `PRODGRAPH.CARDINALITY_CONFLICT` | `(全域關聯圖)` | 關聯宣告與正式區既有 subject 的基數一致。 <br>_依據：production/<域>/（正式區全域關聯圖）_ | rule |
| ✅ | 閘門 | `PRODGRAPH.CYCLE` | `(全域關聯圖)` | 加入本 subject 後全域關聯圖無循環。 <br>_依據：production/<域>/（正式區全域關聯圖）_ | rule |

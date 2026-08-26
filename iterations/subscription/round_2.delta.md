# 第 2 輪迭代變更報告 — subscription

與**第 1 輪**相比的變化；完整結果見同資料夾 `round_2.report.md`。

## 📝 input 變更
- `answers.yaml`：變更（+46／−9 行）

## 🆕 新增的發現（10）
- ℹ️ `CONCEPT.SUBJECT` `subscription.MonthlyPrice（試用與免費期）`（顧問）：試用期或優惠期的訂閱，`MonthlyPrice` 要放 0、放原價、還是放優惠價？三種做法算出來的 MRR 會完全不同。
- ℹ️ `CONCEPT.SUBJECT` `subscription（方案變更）`（顧問）：粒度說「一行 = 一筆訂閱（含歷史訂閱）」——那客戶從月繳升級成年繳、或換方案時，是改這一列的月費，還是結束舊列、開一列新的？
- ℹ️ `NAME.SEMANTIC` `dim_customer.customer_name / dim_customer.customer_email`（顧問）：客戶姓名與 email 是個資，和非個資欄位混在同一張表、命名上也沒有任何標示——授權時要怎麼只開放非個資欄位給分析使用者？
- ℹ️ `NAME.SEMANTIC` `subscription.subscription_id`（顧問）：`subscription_id` 識別的是「一份訂閱合約」還是「合約的一個版本」？客戶升級方案時，是沿用同一個 id，還是產生新的一筆？
- ⚠️ `PRODUCTION.REUSE` `(schema)`（閘門）：沒有引用任何正式區資產（正式區現有 2 個已核准主體：`CRM.dim_customer`、`CRM.order`）。組新表前請先確認這些主體是否已承載你要的事實——能引用就引用，
- ℹ️ `SKILL.best_practice_semantic` `billing_event（遲到資料與封帳）`（顧問）：計費事件常有補登與延遲入帳——月結報表出完之後才到的事件，要回頭修正已出的月份，還是計入下一期？這個規則寫在哪裡？
- ℹ️ `SKILL.best_practice_semantic` `subscription.created_at`（顧問）：訂閱合約會被更新（取消、方案變更），但表上只有 `created_at`、沒有 `updated_at`——下游要做增量抽取時，靠什麼判斷這一列被改過？
- ℹ️ `SKILL.naming_semantic` `billing_event.event_id`（顧問）：`event_id` 是本 schema 裡唯一沒有帶主體前綴的識別碼（另兩個是 `customer_id`、`subscription_id`）——之後與其他來源的事件表整合時，
- ℹ️ `SKILL.ssot_semantic` `billing_event.amount（幣別）`（顧問）：計費金額沒有幣別欄，訂閱表也沒有——目前是假設全部是同一種幣別嗎？若之後開放海外訂閱，既有資料要怎麼補回幣別？
- ℹ️ `SKILL.ssot_semantic` `dim_customer.customer_tier（過渡期權威）`（顧問）：前一輪確認本表是 CRM 的唯讀副本——但在 CRM 客戶主檔還沒晉升 production 之前，實務上大家只查得到這份副本。這段過渡期要怎麼避免它被當成權威使用？

## ✅ 解決（消失）的發現（16）
- ℹ️ `CONCEPT.SUBJECT` `billing_event`（顧問）：計費事件目前只掛 `customer_id`，沒有 `subscription_id`——同一位客戶有多筆訂閱時（粒度宣告允許），這次計費是哪一筆訂閱產生的？
- ℹ️ `CONCEPT.SUBJECT` `billing_event.amount`（顧問）：計費事件沒有事件類型欄（扣款／退款／重試失敗）——金額的正負或事件的成敗，目前是靠什麼表達？
- ℹ️ `CONCEPT.SUBJECT` `dim_customer`（顧問）：context 說「客戶主檔的權威在 CRM」，但本 subject 自己也建了一張 `dim_customer`——這張表是 CRM 的唯讀副本、還是本領域自己維護的另一份客戶資
- ℹ️ `CONCEPT.SUBJECT` `subscription`（顧問）：粒度宣告「一行 = 一筆訂閱（含歷史訂閱）」，但表裡只有 `started_at`，沒有結束時間或狀態欄——要怎麼分辨哪些訂閱現在還有效？
- ℹ️ `NAME.SEMANTIC` `billing_event`（顧問）：表名 `billing_event` 沒有表達它屬於訂閱這條業務線，而同一個 subject 裡另外兩張表是 `dim_customer`、`subscription`——之後其他
- ℹ️ `NAME.SEMANTIC` `dim_customer.customer_tier`（顧問）：`customer_tier` 是「客戶目前的分級」還是「某個時點的分級」？訂閱營收要按分級拆解時，用的是簽約當下的分級還是查詢當下的分級？
- ℹ️ `NAME.SEMANTIC` `subscription.MonthlyPrice`（顧問）：這個欄位名稱只說了「月費」，沒有表達幣別、含稅與否，也看不出是「合約定價」還是「實際收取金額」——訂閱營收分析要用哪一個語意？
- ℹ️ `NAME.SEMANTIC` `subscription.MonthlyPrice / billing_event.amount`（顧問）：兩個金額欄一個叫 `price`、一個叫 `amount`——它們是同一條金流的兩個階段（應收 vs 實收），還是各自獨立的事實？從欄名分不出來。
- ℹ️ `SKILL.best_practice_semantic` `billing_event`（顧問）：這是一張 append-only 的事件表，但沒有看到來源系統的事件識別碼——上游重送同一筆計費通知時，要靠什麼去重？
- ℹ️ `SKILL.best_practice_semantic` `billing_event.occurred_at`（顧問）：事件表會持續累積，目前沒有分區宣告——之後要查「某月的計費事件」時，掃描成本是否還能接受？
- ℹ️ `SKILL.best_practice_semantic` `dim_customer`（顧問）：維度表帶了 `updated_at` 卻沒有版本或有效區間欄——客戶分級變動時，是直接覆寫舊值嗎？覆寫後過去的訂閱分析還能還原當時的分級嗎？
- ℹ️ `SKILL.naming_semantic` `subscription.customer_id / dim_customer.customer_id / billing_event.customer_id`（顧問）：三張表都有 `customer_id`，指的確定是同一個客戶實體嗎？如果是，它們的編碼是否同源（同一份號碼、同一種格式）？
- ℹ️ `SKILL.naming_semantic` `subscription.started_at / subscription.created_at`（顧問）：`started_at`（訂閱生效）與 `created_at`（資料建立）兩個時間欄命名形式相同——分析師要算訂閱起始時，看得出該用哪一個嗎？
- ℹ️ `SKILL.ssot_semantic` `dim_customer（本主體） vs CRM 客戶主檔`（顧問）：同一個客戶實體在本主體與 CRM 各有一張表，看起來有兩個權威擁有者候選——SSOT 登錄上要把誰記為權威？
- ℹ️ `SKILL.ssot_semantic` `subscription.MonthlyPrice vs billing_event.amount`（顧問）：月費與實際計費金額是兩份金額事實——對帳出現差異時（例如首月比例計費、折扣、退款），要以哪一邊為準？差異要記在哪裡？
- ℹ️ `SKILL.ssot_semantic` `subscription.customer_email`（顧問）：客戶 email 同時存在 `dim_customer` 與 `subscription` 兩張表——當客戶更新 email 時，兩邊會同時更新嗎？如果不會，哪一邊才是對外可信的那

## 🔄 狀態變化（0）
（無）

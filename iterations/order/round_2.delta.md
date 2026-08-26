# 第 2 輪迭代變更報告 — order

與**第 1 輪**相比的變化；完整結果見同資料夾 `round_2.report.md`。

## 📝 input 變更
- `answers.yaml`：變更（+66／−15 行）

## 🆕 新增的發現（11）
- ℹ️ `CONCEPT.SUBJECT` `orders（取消單的母體語意）`（顧問）：前一輪確認營收彙總會排除取消訂單——那「下單量」「轉換率」這類母體型指標呢？取消單要算進分母嗎？
- ℹ️ `CONCEPT.SUBJECT` `orders（部分退貨／換貨）`（顧問）：`status` 只能表達整單取消，但實務上會有「退其中一個品項」——這類部分退貨的事實目前由哪個主體承載？本主體要不要負責？
- ℹ️ `NAME.SEMANTIC` `order_items.order_item_id`（顧問）：`order_item_id` 是來源系統給的自然鍵，還是 ETL 端產生的代理鍵？如果訂單重送或明細重算，同一個商品項會拿到同一個 id 嗎？
- ℹ️ `NAME.SEMANTIC` `orders.cancelled_at`（顧問）：`cancelled_at` 是本 schema 唯一可為 NULL 的欄位，NULL 同時代表「尚未取消」——但「訂單已取消卻沒記到時間」也會是 NULL。這兩種情況在查詢時分得
- ✅ `PRODUCTION.REUSE` `(schema)`（閘門）：已引用正式區資產：`crm.dim_customer`。
- ℹ️ `SKILL.best_practice_semantic` `orders.cancelled_at（Nullable 欄位策略）`（顧問）：`cancelled_at` 是唯一使用 Nullable 的欄位——在 ClickHouse 中 Nullable 會多一個 null map、影響壓縮與掃描效能。這個成本在資料
- ℹ️ `SKILL.naming_semantic` `orders / order_items（表名與 SSOT 主體名）`（顧問）：表名用複數（`orders`、`order_items`），SSOT 的主體候選卻是單數（`order`、`order_item`）——這組單複數對應是專案慣例嗎？有寫在詞彙字典裡
- ℹ️ `SKILL.production_reuse_semantic` `orders / order_items（本主體已在正式區）`（顧問）：正式區的 `CRM.order` 就是本主體的已核准版本——這次 input 是既有主體的改版，不是新建。變更相對正式區版本的差異，下游（營收日報、對帳、出貨）已經評估過影響了嗎？
- ℹ️ `SKILL.production_reuse_semantic` `orders.customer_id → CRM.dim_customer`（顧問）：本主體已用三段式引用客戶主檔（`CRM.dim_customer`），這是正確的複用。反過來看：正式區的 `CRM.dim_customer` 有沒有哪些屬性是本主體其實需要、但目
- ℹ️ `SKILL.ssot_semantic` `orders.currency（換算基準）`（顧問）：前一輪確認一張訂單只有單一幣別——那跨幣別的營收合計要換算成本位幣時，匯率來自哪裡？這份匯率事實的權威擁有者是誰？
- ℹ️ `SKILL.ssot_semantic` `orders.total_amount（對外請款金額）`（顧問）：前一輪確認 `total_amount` 是金流實際請款金額的權威——那金流平台自己那份交易金額算什麼？兩邊不一致時，對外（例如客服、發票）要以誰為準？

## ✅ 解決（消失）的發現（15）
- ℹ️ `CONCEPT.SUBJECT` `order_items`（顧問）：粒度宣告「同一商品在同一訂單內只會有一行，數量以 quantity 表達」——若同一商品在一張訂單裡出現不同單價（例如買一送一、部分套用折扣），這個粒度還撐得住嗎？
- ℹ️ `CONCEPT.SUBJECT` `orders`（顧問）：context 說取消訂單「仍保留該行、以 cancelled_at 標記」——那麼營收日報在彙總 `total_amount` 時，是以 `cancelled_at IS NUL
- ℹ️ `CONCEPT.SUBJECT` `orders.total_amount`（顧問）：`total_amount` 是「明細加總的快照值」，同時 `order_items` 又保有逐項的 `quantity × unit_price`——當兩者對不起來（例如事後調整
- ℹ️ `CONCEPT.SUBJECT` `order（未登錄主體候選）`（顧問）：`orders` 與 `order_items` 承載的「訂單」「訂單明細」概念目前不在 SSOT 登錄表內——這兩個主體的權威擁有者是本 subject 嗎？要不要順手登錄，讓之
- ℹ️ `NAME.SEMANTIC` `order_items.product_id`（顧問）：`customer_id` 的註解明確指出權威在 `CRM.dim_customer`，但 `product_id` 只寫「權威在商品主檔」而沒有指名 domain 與表——這個商
- ℹ️ `NAME.SEMANTIC` `orders.ordered_at / orders.created_at / orders.updated_at`（顧問）：三個時間欄中 `ordered_at` 是業務發生時間、`created_at`／`updated_at` 是稽核時間，但命名形式相同（都是 `_at`）——分析師只看欄名能分辨哪
- ℹ️ `NAME.SEMANTIC` `orders.status`（顧問）：`status` 目前承載訂單生命週期（created/paid/shipped/cancelled），其中 `paid` 屬於金流語意、`shipped` 屬於物流語意——單一欄
- ℹ️ `NAME.SEMANTIC` `orders.total_amount`（顧問）：`total_amount` 的註解說明是「含稅」，但 `order_items.unit_price` 沒有標示含稅與否——同一份 schema 內的金額欄位，是否要讓命名或註解
- ℹ️ `SKILL.best_practice_semantic` `orders`（顧問）：`orders` 是典型的交易型事實表且帶 `updated_at`（會被更新）——目前 ENGINE 的去重與版本策略，能保證同一 `order_id` 只會查到最新版本嗎？
- ℹ️ `SKILL.best_practice_semantic` `orders.ordered_at`（顧問）：訂單是持續累積的時間序列事實，但目前沒有看到分區宣告——資料量成長後，營收日報依 `ordered_at` 掃描的成本是否還可接受？
- ℹ️ `SKILL.naming_semantic` `order_items.quantity`（顧問）：`quantity` 的註解寫「單位：件」，但商品若有以重量或長度計價的品項，這個欄名與單位假設還成立嗎？是否需要一個 `unit_of_measure`？
- ℹ️ `SKILL.naming_semantic` `orders.customer_id / dim_customer.customer_id`（顧問）：衍生 SQL 把 `dim_customer.customer_id` 另取別名 `dim_customer_customer_id` 輸出——寬表裡同時出現兩個客戶鍵，讀的人分得
- ℹ️ `SKILL.ssot_semantic` `derivation.sql（customer_name、customer_tier）`（顧問）：context 明確宣告「只存鍵不存客戶屬性」，但衍生 SQL 把 `customer_name`、`customer_tier` join 進寬表——這份寬表若被物化保存，是不是
- ℹ️ `SKILL.ssot_semantic` `order_items.product_id`（顧問）：`product_id` 指向的商品主檔目前不在任何已晉升的 domain 內——這個 join key 能保證與未來的商品主檔指向同一實體（同編碼、同型別）嗎？
- ℹ️ `SKILL.ssot_semantic` `orders.currency`（顧問）：`currency` 存在訂單層級，但 `order_items.unit_price` 沒有幣別欄——明細金額的幣別是隱含沿用訂單的嗎？跨幣別報表彙總時，這個隱含關係看得出來嗎？

## 🔄 狀態變化（0）
（無）

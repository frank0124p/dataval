# input/ — 輸入契約（一個 data subject：三件必備＋樣本選填）

**一個 data subject 一個資料夾**，資料夾名 = subject 名。三件必備
（DDL／relations／context）缺任一件就不會產生報告（`run.py` 會先做前置檢核
並印出缺件明細，同時留檔 `reports/<名>.precheck.md`）。**樣本 `samples/` 是選填**——
沒有樣本仍會產生報告，只是樣本相關檢查（型別對樣本、join key 編碼一致、
基數實檢）因無資料而略過。整包資料夾交付即可。

```text
input/
  <名>/
    <名>.sql            DDL 主檔（ClickHouse；可含多張 CREATE TABLE）← 必備
    <表名>.sql          DDL 拆檔（選用：一表一檔，任意數量）        ← 選填
    relations.yaml      表間關聯（join 關係與基數；一份管全部表）  ← 必備
    context.md          這個 data subject 的語意描述（一份）      ← 必備
    derivation.sql      寬表的組合（Join）SQL                   ← 選填
    samples/            樣本資料資料夾                          ← 選填
      <表名>.csv        DDL 的每張表各一份，檔名 = 表名
```

範例請直接看本資料夾的 `order/`（完整參考範例）與 `subscription/`
（刻意含多個違規的示範案例）。舊式平鋪佈局（`<名>.sql`＋`<名>.samples/`＋
`<名>.relations.yaml`＋`<名>.context.md`）仍相容，但新案請用資料夾式。

---

## ① DDL — `<名>.sql`（多檔＝一組表，共同描述一個 data subject）

- ClickHouse 語法，可含多張 `CREATE TABLE`
- **多檔拆放（選用）**：`<名>.sql` 是主檔（必備、subject 的錨）；同資料夾
  其餘 `*.sql`／`*.ddl` 依檔名排序一併載入（`derivation.sql` 除外），
  效果等同寫在同一檔。例：`order/order.sql`（orders）＋
  `order/order_items.sql`（order_items）。design mode 定稿的逐表 `.ddl`
  可直接複製進來。報告「表總覽」會標示每張表的來源檔
- 建議：每個欄位都寫 `COMMENT`（`naming_columns_commented` 是會擋的規則）

## ② 樣本資料 — `samples/<表名>.csv`（選填）

- **選填**：整個 `samples/` 可不提供，或只提供部分表；缺樣本的表其樣本相關檢查
  （型別對樣本、join key 編碼、基數實檢）會略過，不擋報告，只在前置檢核列警告。
- 有提供就要對得上：檔名必須等於表名
- 首列 = 表頭，欄名須與 DDL 一致（snake_case）；表頭欄名不可出現 DDL 沒有的欄位
  （允許只給部分欄位）
- 編碼 UTF-8；**空格子 = NULL**（CSV 無法區分空字串與 NULL，一律視為 NULL）
- 布林寫 `true` / `false`；日期時間一律 ISO 8601（如 `2026-07-21T10:30:00`）
- 建議 10–100 列，涵蓋典型值與邊界值；可為 NULL 的欄位請至少給一列 NULL
- 樣本會被 `structural_type_sample`（型別對樣本）、`ssot_join_keys`
  （join key 編碼一致）與 relations 的**基數實檢**使用

## ③ 表間關聯 — `relations.yaml`

```yaml
relations:
  - from: order_items.order_id        # 「多」的一方（必須是本次 DDL 的表）
    to: orders.order_id               # 「一」的一方；跨 domain 用三段式 DOMAIN.table.col
    cardinality: "N:1"                # 1:1 | N:1 | N:M
    kind: fk                          # fk | reference | lookup（省略 = fk）
    note: 每筆明細屬於一張訂單
```

- **多表 subject 至少要宣告一條**；單表 subject 寫 `relations: []`
  表示「確認過沒有」（「沒寫」和「確認沒有」必須可區分）
- 本地端點會驗證存在於 DDL；跨 domain 端點（三段式）由引擎對
  `production/<DOMAIN>/` 的已核准 DDL 實檢（表存在、欄位存在、型別相容）
- 宣告的 cardinality 會拿樣本實檢：宣稱 `N:1` / `1:1` 但「1 的一方」
  在樣本出現重複鍵 → **閘門區會擋**（`RELATION.CARDINALITY_SAMPLE`）

## ④ 語意描述 — `context.md`

front-matter ＋ Markdown 段落。**「粒度」段落必填**——粒度不明是資料設計
最貴的錯誤，在輸入端就要求設計者寫下來，顧問區才有依據可對照檢視。

```markdown
---
subject: 訂單                  # 必填：這個 data subject 的名稱
domains: [CRM]                 # 選填：要載入的領域規則（Common 恆載入）
business_keys:                 # 選填：各表的業務識別鍵
  orders: [order_id]
---

## 這個 data subject 是什麼
（建議）一兩段講清楚它承載什麼業務事實。

## 粒度（每張表一行代表什麼）
（必填）逐表寫：一行 = 什麼。這決定所有彙總是否正確。

## 用途與消費者
（建議）誰會查、拿來做什麼決策。

## 上下游來源
（建議）資料從哪來、會流向哪。
```

---

## ⑤ 迭代問答 — `answers.yaml`（選填）

報告的顧問區會產出「給設計者思考的提問」，並由 agent **預先代填答案**：
每輪 `merge_advisory.py` 把 agent 隨提問附上的建議答案直接寫進本檔，
標 `status: proposed`（待驗證）。**你只需要驗證**——答案沒問題就把
`proposed` 改成 `answered`（答案可修改），不想追的改 `deferred`。
待驗證不算已答：不餵下一輪 prompt、會擋收斂（收斂條件：無待答＋
無待驗證＋閘門合規；上限 5 輪；狀態見報告的「迭代收斂」區塊）。

```yaml
version: 1
iteration: 2                    # 目前第幾輪（agent 開新輪時 +1；缺省 = 第 1 輪）
answers:
  - id: CONCEPT.SUBJECT@subscription      # <check_id>@<target>（代填時已填好）
    question: 一列代表一次訂閱、還是一個計費週期?   # 當時的提問（供人讀）
    answer: 一列代表一個訂閱合約;計費週期在 billing_event。
    kind: semantic              # semantic＝只澄清語意（餵顧問區）
    status: answered            # proposed（代填待驗證）→ answered | deferred（擱置）
  - id: SKILL.ssot_semantic@dim_customer.customer_name
    question: customer_name 的權威來源是否應在 CRM 主檔?
    answer: 是,已移除本表欄位,改以 customer_id 關聯。
    kind: structural            # structural＝需手動修改權威輸入後才能改 answered
    status: answered
    applied_to: subscription.sql   # 結構答案:記你改了哪個權威檔（供稽核）
```

代填只**新增**未覆蓋的主題，永不覆寫你既有的條目；answers.yaml 壞檔時
不代填（避免改寫時默默丟掉壞條目），前置檢核會列警告。

**硬邊界**：本檔只餵顧問區 prompt 與報告呈現，**永不**進閘門執行路徑。
要改變合規判定，唯一途徑是手動修改三件權威輸入。回答是「答主題」：
同一 `<check_id>@<target>` 的提問不論措辭如何變化都視為同一題；
答表名（如 `subscription`）可涵蓋該表同規則的欄位級提問。
壞檔不擋報告（前置檢核列警告並略過）。

## ⑥ 衍生 SQL — `derivation.sql`（選填，寬表 subject 建議附上）

寬表（多來源 join 整合）subject 附上「實際怎麼 join 出來」的 SQL，
引擎以 sqlglot **確定性解析**（零 LLM）並三方對照：

```sql
-- 單一 SELECT；CREATE TABLE … AS SELECT／INSERT INTO … SELECT 亦可
SELECT
  o.order_id,
  o.customer_id,
  c.customer_name
FROM orders AS o
LEFT JOIN dim_customer AS c ON o.customer_id = c.customer_id
```

- **與 relations.yaml 交叉驗證**：SQL 有 join 但未宣告 → ⚠️ 警告
  （`DERIVATION.RELATIONS`）；宣告了但 SQL 沒用 → 提示
- **與寬表 DDL 逐欄對照**：SQL 輸出欄 vs DDL 欄位缺／多 → ⚠️ 警告
  （`DERIVATION.COVERAGE`）；`SELECT *` 會提示無法逐欄對照
- **與建議 SQL 三方對照**：報告「衍生 SQL 對照」區塊呈現 join 鍵在
  「你的 SQL ↔ relations.yaml ↔ 建議 SQL」的出現矩陣
- 警告一律**不擋**合規；SQL 全文進迭代歷史（逐輪變更追蹤）
- **顧問區也會看到**：SQL 原文＋解析摘要（來源表、coverage、三方矩陣）會
  自動放進 `advisory_prompt.md` 的「衍生 SQL」區塊，agent 據此檢視 join
  邏輯的語意（粒度、LEFT JOIN 的 NULL 語意、運算欄含義）——
  **不需要**再把 join 邏輯描述進 context.md

## 前置檢核的三層

| 層 | 檢查內容 |
|---|---|
| 存在性 | 三件必備齊全（DDL／relations／context）；樣本選填，缺樣本不擋 |
| 可解析性 | DDL 可 parse；（有提供時）CSV 表頭可讀；YAML 語法正確；context 有必填段落 |
| 一致性 | （有提供時）CSV 欄名 ⊆ DDL 欄位；relations 端點存在；cardinality 值合法 |

必備件任一層不過 → 該 DDL 跳過不產報告（其他齊全的照跑），`run.py` 以
exit code 2 結束，缺件明細寫入 `reports/<名>.precheck.md`。樣本缺漏或某份 CSV
有問題 → 不擋報告，只在前置檢核列警告並略過該表的樣本。

> 相容模式：`DATAVAL_PRECHECK=legacy` 可暫時回到舊的
> `config/cases/<名>.yaml` 集中式輸入（供內部測試 fixtures 使用，不建議新案採用）。

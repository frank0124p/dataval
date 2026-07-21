# input/ — 輸入契約（一個 data subject 一組四件）

以 `<名>.sql` 為錨，**四件都要有**，缺任一件就不會產生報告
（`run.py` 會先做前置檢核並印出缺件明細，同時留檔 `reports/<名>.precheck.md`）。

```text
input/
  <名>.sql                DDL（ClickHouse；可含多張 CREATE TABLE）
  <名>.samples/           樣本資料資料夾
    <表名>.csv            DDL 的每張表各一份，檔名 = 表名
  <名>.relations.yaml     表間關聯（join 關係與基數）
  <名>.context.md         這個 data subject 的語意描述
```

範例請直接看本資料夾的 `order.*`（完整參考範例）與 `subscription.*`
（刻意含多個違規的示範案例）。

---

## ① DDL — `<名>.sql`

- ClickHouse 語法，可含多張 `CREATE TABLE`
- 建議：每個欄位都寫 `COMMENT`（`naming_columns_commented` 是會擋的規則）

## ② 樣本資料 — `<名>.samples/<表名>.csv`

- **DDL 的每張表都要有一份**；檔名必須等於表名
- 首列 = 表頭，欄名須與 DDL 一致（snake_case）；表頭欄名不可出現 DDL 沒有的欄位
  （允許只給部分欄位）
- 編碼 UTF-8；**空格子 = NULL**（CSV 無法區分空字串與 NULL，一律視為 NULL）
- 布林寫 `true` / `false`；日期時間一律 ISO 8601（如 `2026-07-21T10:30:00`）
- 建議 10–100 列，涵蓋典型值與邊界值；可為 NULL 的欄位請至少給一列 NULL
- 樣本會被 `structural_type_sample`（型別對樣本）、`ssot_join_keys`
  （join key 編碼一致）與 relations 的**基數實檢**使用

## ③ 表間關聯 — `<名>.relations.yaml`

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

## ④ 語意描述 — `<名>.context.md`

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

## 前置檢核的三層

| 層 | 檢查內容 |
|---|---|
| 存在性 | 四件齊全；DDL 每張表都有對應 CSV |
| 可解析性 | DDL 可 parse；CSV 表頭可讀；YAML 語法正確；context 有必填段落 |
| 一致性 | CSV 欄名 ⊆ DDL 欄位；relations 端點存在；cardinality 值合法 |

任何一層不過 → 該 DDL 跳過不產報告（其他齊全的照跑），`run.py` 以
exit code 2 結束，缺件明細寫入 `reports/<名>.precheck.md`。

> 相容模式：`DATAVAL_PRECHECK=legacy` 可暫時回到舊的
> `config/cases/<名>.yaml` 集中式輸入（供內部測試 fixtures 使用，不建議新案採用）。

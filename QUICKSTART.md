# 快速上手（5 分鐘）

> 這是 **dataval**：把一份 ClickHouse 資料設計丟進來，它幫你檢查合規性、產出可稽核的報告。
> 想從零開始「設計」一張表也可以——它會幫你把設計文件寫出來。
>
> 想看完整說明再讀 [`README.md`](README.md)；這一頁只講「怎麼跑起來」。

---

## 1. 安裝（一次就好）

需要 Python 3.10 以上。

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

## 2. 先跑跑看內建範例

專案已經附了兩個範例輸入，直接跑：

```bash
.venv/bin/python run.py order
```

打開 `govern_doc/order/order.report.html`（雙擊即可，單一檔案不用開伺服器），
就是一份完整的驗證報告。

---

## 你要做的是哪一件事？

| 你手上有的東西 | 走哪條路 | 產出 |
|---|---|---|
| **已經有 DDL** — 想知道設計有沒有問題 | 🛡 治理模式（下面 A） | 合規報告（Markdown／JSON／HTML） |
| **只有想法、還沒有 DDL** — 想請它幫忙設計 | 🎨 設計模式（下面 B） | 邏輯／實體設計文件＋草稿 DDL＋ETL 建議檔 |

兩者由「資料夾裡有沒有 `.sql`」自動判定，你不必下參數。

---

## A. 我已經有 DDL — 檢查它

### 步驟 1：放檔案

**規則只有一條：一個資料主題一個資料夾，資料夾名 = 主題名 = 主檔名。**

```text
input/
  my_subject/               ← 資料夾名自己取（建議英文小寫，如 order、customer）
    my_subject.sql          ← 必備｜檔名必須跟資料夾同名
    relations.yaml          ← 必備｜檔名固定，不要改
    context.md              ← 必備｜檔名固定，不要改
    samples/                ← 選填
      orders.csv            ←   檔名必須等於「表名」，不是主題名
      order_items.csv
    derivation.sql          ← 選填｜寬表實際的 Join SQL，檔名固定
```

⚠️ **最常見的錯**：資料夾叫 `my_subject/`，裡面的 SQL 卻叫 `schema.sql`
或 `ddl.sql`——這樣工具找不到它，會當作「這個主題還沒有 DDL」而跑去設計模式。
`input/my_subject/` 裡的主檔一定要是 `my_subject.sql`。

最快的做法：**把 `input/order/` 整包複製一份改名，再改內容**。

#### 各個檔案分別放什麼

**① `my_subject.sql` — 你的 DDL**

- 多張表有兩種放法，選一種就好：
  - **寫在同一個檔**：一個 `.sql` 裡放多個 `CREATE TABLE`（`input/order/order.sql` 就是這樣，裡面有 2 張表）
  - **一表一檔**：主檔 `my_subject.sql` 之外，同資料夾再放 `orders.sql`、`order_items.sql`…，工具會全部一起載入（檔名隨意，但 `derivation.sql` 是保留名稱）
- 建議每個欄位都寫 `COMMENT`——「欄位要有註解」是會擋的規則

**② `relations.yaml` — 表跟表怎麼關聯**

檔名固定叫 `relations.yaml`，一份管這個主題的所有表：

```yaml
relations:
  - from: order_items.order_id     # 「多」的一方，寫 表名.欄名
    to: orders.order_id            # 「一」的一方
    cardinality: "N:1"             # 1:1 | N:1 | N:M
```

- 只有一張表、真的沒有關聯 → 寫 `relations: []`（空的也要寫，代表「確認過沒有」）
- 要指向別的領域已上線的表 → `to` 用三段式：`CRM.dim_customer.customer_id`

**③ `context.md` — 這份資料在講什麼**

檔名固定叫 `context.md`，前面是 front-matter、後面是段落：

```markdown
---
subject: 我的主題
domains: [CRM]          # 選填：要套哪個領域的規則（config/ 下的資料夾名）
business_keys:          # 每張表的業務唯一鍵（不寫的話會被規則擋下來）
  orders: [order_id]
---

## 這個 data subject 是什麼
一兩句話說明它承載什麼業務事實。

## 粒度（每張表一行代表什麼）
orders：一行 = 一張訂單。       ← 這段必填，沒寫不會產報告
```

**④ `samples/*.csv` — 樣本資料（選填）**

- 放在 `samples/` 子資料夾底下，**檔名 = 表名**（`orders.csv` 對應 `orders` 表）
- 首列是表頭、欄名要跟 DDL 一致；空格子代表 NULL
- 可以只給部分表、也可以完全不給——沒給就是少做幾項檢查，報告照樣產出

**⑤ 不用你自己建的檔案**

`answers.yaml`（迭代問答）會由工具自動產生在同一個資料夾裡，你只要去改
裡面的 `status` 就好，不需要先手動建立。

### 步驟 2：跑

```bash
.venv/bin/python run.py my_subject     # 不加名字＝跑全部
```

報告會出現在 `govern_doc/my_subject/`：

- `my_subject.report.html` — **看這個就好**（單檔互動，可搜尋、可篩選）
- `.report.md` / `.report.json` — 人讀版／程式讀版

### 步驟 3：如果畫面要你補顧問區

結尾若印出「⚠️ 顧問區尚未補完」，代表報告的**語意建議**還沒填。
這段需要 AI 幫忙——用 Claude Code 或 opencode 打開這個專案，直接說：

> 幫我補完顧問區

它會照 `AGENTS.md` 的規矩，讀 prompt、產建議、合併回報告。
（純粹想看合規判定的話，可以忽略這段——**閘門區的判定已經完成了**，
不受顧問區影響。）

---

## B. 我還沒有 DDL — 請它幫我設計

**只放一個 `context.md`，資料夾裡不要有任何 `.sql`**：

```text
input/
  my_subject/
    context.md      ← 只有這一個檔（格式與 A 的 ③ 完全相同）
```

判定方式很單純：資料夾裡**有** `my_subject.sql` → 走治理模式；**沒有** → 走設計模式。
所以只要你還沒把 DDL 放進去，它就會幫你設計。


```bash
.venv/bin/python run.py my_subject
```

它會產出一份「設計任務」，接著用 Claude Code／opencode 說：

> 幫我完成設計

完成後 `design_doc/my_subject/` 會出現：

| 檔案 | 是什麼 |
|---|---|
| `my_subject.design_report.html` | **看這個**：一站式設計報告 |
| `my_subject.design_story.md` | 白話版：為什麼這樣設計、取捨在哪 |
| `my_subject.logical_design.md` | 邏輯設計（業務語言，給業務／分析師看） |
| `my_subject.physical_design.md` | 實體設計（表、型別、key，給工程師看） |
| `my_subject.design.sql` | 草稿 DDL，可以直接拿去用 |
| `my_subject.etl.yaml` | ETL 設定建議檔（更新頻率、資源配置、owner…） |

**設計滿意了怎麼辦**：把 `design.sql` 存成 `input/my_subject/my_subject.sql`
（順便把 `design.relations.yaml` 存成 `relations.yaml`），再跑一次 `run.py`——
它就自動變成 A 的治理模式了。

---

## 放對了嗎？檢查這五件事

1. 資料夾在 `input/` 底下，一個主題一個資料夾
2. 資料夾裡的主 SQL 檔名 **等於資料夾名**（`my_subject/my_subject.sql`）
3. `relations.yaml`、`context.md` 檔名沒有改過（沒有關聯就寫 `relations: []`）
4. `context.md` 有「粒度」那一段、front-matter 有 `business_keys`
5. 有放樣本的話，`samples/` 底下的 CSV 檔名等於**表名**

跑 `run.py` 之後如果說缺件，打開 `govern_doc/<主題>/<主題>.precheck.md`，
它會逐項列出少了什麼。

---

## 產出放在哪

```text
design_doc/<主題>/     🎨 設計文件
govern_doc/<主題>/     🛡 治理報告
```

一個主題一個資料夾，整包拿去給別人也看得懂。

---

## 你大概只會用到這幾個指令

```bash
.venv/bin/python run.py                 # 檢查全部
.venv/bin/python run.py my_subject      # 只檢查一個
.venv/bin/python merge_advisory.py      # 把 AI 補的建議合進報告
.venv/bin/python promote.py my_subject  # 合規了 → 收進正式區 production/
```

**Exit code**：`0` 全部合規 · `1` 有不合規（加 `--strict` 時）· `2` 有主題的輸入檔沒放齊。

---

## 卡住了？

| 狀況 | 怎麼辦 |
|---|---|
| 說「缺件」不產報告 | 看 `govern_doc/<主題>/<主題>.precheck.md`，缺什麼補什麼（通常是少了 `relations.yaml` 或 `context.md` 沒寫「粒度」） |
| 報告顧問區寫「待補完」 | 用 Claude Code／opencode 說「幫我補完顧問區」 |
| 想知道每條規則在檢查什麼 | 規則就是 `config/<領域>/knowhow/` 底下的 Markdown，打開就能讀 |
| 想加自己的規則 | `.venv/bin/python rules.py new Common gating my_rule`，細節見 `SKILL_AUTHORING.md` |

更完整的架構、規則系統、正式區治理與迭代問答說明 → [`README.md`](README.md)

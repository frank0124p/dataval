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

### 步驟 1：放三個檔案

一個資料主題一個資料夾，資料夾名就是主題名：

```text
input/
  my_subject/
    my_subject.sql      ← 你的 CREATE TABLE（可以多張表）
    relations.yaml      ← 表跟表怎麼關聯（沒有關聯就寫 relations: []）
    context.md          ← 這份資料在講什麼（「粒度」段落必填）
```

最快的做法：**複製 `input/order/` 改內容**，格式一眼就懂。
（`samples/*.csv` 樣本是選填，有給的話多幾項檢查。）

`relations.yaml` 長這樣：

```yaml
relations:
  - from: order_items.order_id     # 「多」的一方
    to: orders.order_id            # 「一」的一方
    cardinality: "N:1"
```

`context.md` 長這樣：

```markdown
---
subject: 我的主題
domains: [CRM]          # 選填：要套哪個領域的規則
business_keys:          # 每張表的業務唯一鍵（不寫的話會被規則擋下來）
  orders: [order_id]
---

## 這個 data subject 是什麼
一兩句話說明它承載什麼業務事實。

## 粒度（每張表一行代表什麼）
orders：一行 = 一張訂單。       ← 這段必填
```

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

只放一個 `context.md`，不要放 `.sql`：

```text
input/my_subject/
  context.md        ← 只有這一個檔
```

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

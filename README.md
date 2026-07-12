# 資料設計驗證工具（dataval）— 技術文件

把 ClickHouse DDL 丟進資料夾、跑一行指令（或對 agent 說一句話），
就會自動產生合規報告：**閘門區**（確定性規則，會擋，每次結果一致）判定合規與否，
**顧問區**（LLM 語意建議，只提示，永不影響判定）給設計者思考的提問。

> 本文件是**使用與維護**手冊。想理解專案的背景、理念與價值，
> 請讀 **`docs/專案介紹.md`**（介紹長文，適合分享給還不認識這個專案的人）。

---

## 三步開始

**1. 安裝（只需一次）**

```bash
python -m pip install -e .
```

依賴與 Python 最低版本由 `pyproject.toml` 管理（最低 3.10；CI 驗證 3.10–3.12）。

**2. 把你的 DDL 放進 `input/`**

直接把 `.sql`（或 `.ddl`）複製進去，要幾個都可以。（選用）同名附帶檔讓驗證更準：

- `<檔名>.sample.json` — 少量樣本資料：`{"表名": [{"欄位": 值}, ...]}`
- `<檔名>.context.txt` — 一句話說明這次在做什麼
- `<檔名>.domains.yaml` — 指定關聯的 domain（見「domain 選擇」）
- `<檔名>.keys.yaml` — 明確宣告各表 business key（必要治理 metadata）
- `<檔名>.lineage.yaml` — 明確宣告來源表、目標表與欄位映射（見「Lineage 關聯治理」）

**3. 產生報告**

```bash
python run.py
```

CI 要在不合規時回傳非零碼，使用 `python run.py --strict`
或設 `DATAVAL_STRICT=1`。

它會先重建結構化規則內容（有變更才寫入 `build/compiled_rules.json`），
再逐檔驗證。報告出現在 `reports/`：`.report.md`（人讀）、`.report.json`（程式）、
`.subject_summary.md`（data subject 摘要）；`.report.html`（給團隊看的完成版）
在顧問區有真實內容時產生——見下方 LLM 章節。

---

## 支援的 agent CLI：opencode 與 Claude Code

本專案同時支援兩個 agent CLI，各自有入口檔、開專案時自動讀取：

- **opencode** → 讀 `AGENTS.md`
- **Claude Code** → 讀 `CLAUDE.md`

兩者用法相同——在專案目錄對 agent 說：

> 驗證 input 裡的 DDL 並給我報告

agent 會跑完整流程（含顧問區補完）。也可以直接貼一段 DDL 請它驗證，它會存檔再跑。
差異只有一點：顧問區補完時，opencode 用它連接的 LLM 產生建議；
Claude Code **自行推理**產生建議——都走同一條補完往返。

---

## 關於 LLM 與顧問區（你大概不用特別設定）

顧問區需要 LLM。`python run.py` 是獨立程式，不會自動用到 agent 的 LLM，所以：

**未接本地 LLM 時（預設）**：run.py **先不產 HTML**（產 `.md`/`.json` 與
`reports/<名>.advisory_prompt.md`）。接著 agent 讀指示 → 產生建議寫成
`reports/<名>.advisory_result.json` → 跑 `python merge_advisory.py` ——
**HTML 在這一步才產生**，顧問區直接是真實建議、標「✅ 已由 agent 補完」。

所以使用者看到的 HTML 永遠是閘門區＋顧問區**皆有真實內容**的完成版，
不會出現「待補完」。且補完前後每條 checking rule ID 的閘門結果不變——
建議永遠不影響合規判定。

**有本地 LLM 時**：設環境變數 `DATAVAL_LLM_BASE_URL / DATAVAL_LLM_MODEL /
DATAVAL_LLM_API_KEY`（OpenAI 相容介面），run.py 一次跑完、直接產完成版 HTML。

---

## 報告怎麼看

報告開頭就是結論：**合規 / 不合規**、幾項會擋，接著「**本次卡控摘要**」
直接列出被哪些規則卡下來（HTML 中點規則代號可篩選明細）。

每條**違規**以固定四問呈現：**哪條規則**（代號＋人話標題＋等級）、
**哪裡違反**（表.欄位）、**期望 vs 實際**（規則要求 vs 實際看到，證據並列）、
**怎麼修**（具體修正方向，由卡控動詞自動生成，或規則檔 `## 修正建議` 段覆寫）。
「為什麼有這條規則」為輔助小字。**通過的**每條規則彙總一筆，違規不會被淹沒。

HTML 報告是單一檔案（內嵌樣式與互動、無外部依賴），雙擊用瀏覽器開，適合分享團隊：
判定卡片、統計、兩區對照橫幅、搜尋、篩選（失敗/警告/閘門/顧問）、可摺疊分類、深淺色。
每條已載入規則都會有明確執行狀態：`pass / fail / warning / skipped`；
「沒有 finding」不再被當成通過。

**Checking rule ID 摘要**：報告直接列出本次「擋下、警告、通過、未實檢、顧問」
的 rule ID。不使用指紋或版本碼；規則變更直接 diff 規則檔與
`build/compiled_rules.json`，執行結果則由黃金測試比對 checking rule ID。

**Lineage 關聯**：報告另以「來源 → 目標 → 欄位映射」呈現關係，並清楚區分
`YAML 明確宣告` 與 `系統建議`。JSON 同時提供頂層 `lineage` 與
`meta.lineage`，方便後續工具讀取。

---

## 規則怎麼運作（build pipeline）

**規則只有一個家**，且撰寫與執行分兩種格式：

```
config/skills/**/*.md（撰寫格式：人讀規範＋卡控區塊）
        │  每次執行前自動 compile（結構化內容有變更才寫入）
        ▼
build/compiled_rules.json（執行格式：結構化、可 diff、以 checking rule ID 識別）
        │  引擎從這份 JSON 載入規則執行 —— 單一執行來源
        ▼
閘門區判定（零 LLM）＋ 顧問區提示
```

- 確定性規則：`config/skills/<domain>/gating/*.md`，**一條規則一個檔**。
  停用＝移走檔案；調等級＝改 `enforcement` 一個字。
- 語意規則：`config/skills/<domain>/advisory/*.md`（` ```check-llm `，只提示）。
- 跨表／需樣本的複雜規則：`config/skills_py/*.py`（一個強相關叢集一檔）。

## 5 分鐘新增一條 rule

最常見的是新增一條跨 domain 共用、可機械判斷的閘門規則。只要四步：

### 1. 產生規則檔

```bash
python rules.py new order_needs_created_at
```

這會建立：

```text
config/skills/Common/gating/order_needs_created_at.md
```

`Common/gating` 是最簡單的預設；既有的進階指令仍可指定 domain 與區域：

```bash
python rules.py new CRM gating customer_needs_name
python rules.py new CRM advisory customer_name_semantic
```

新檔會預填 `category: structural` 與 `enforcement: blocking`；不適合時直接改掉即可。
任何尚未替換的 `<範本內容>` 都會被下一步的 `check` 明確指出。

### 2. 編輯一份 Markdown

一條 rule 就是一個 Markdown 檔，只需填清楚四件事：rule ID、分類與等級、給人看的
說明、給程式執行的 `check`。例如要求每張表都有 `created_at`：

````markdown
---
id: order_needs_created_at
category: structural
enforcement: blocking
---

# 表必須記錄建立時間

## 目的
保留資料首次建立時間，讓異常追查與增量處理有一致依據。

## 適用情境
所有共用資料表。

## 違反後果
無法判斷資料何時產生，因此設為 blocking。

## 修正建議
新增 `created_at DateTime('UTC')`。

## 卡控
```check
require: has_column created_at
```
````

欄位意思：

- `id`：全專案唯一的小寫英數底線；報告會顯示為 `SKILL.<id>`。
- `category`：`structural`、`naming`、`best_practice`、`ssot` 四選一。
- `enforcement`：`blocking` 會擋、`warning` 只警告、`advisory` 只提供建議。
- `check`：確定性檢查；需要理解語意時改用 `check-llm` 並放在 `advisory/`。

### 3. 一次檢查並編譯

```bash
python rules.py check
```

`check` 會先檢查 ID、必要章節、卡控語法、domain、regex 與 metadata；全部正確後
自動更新 `build/compiled_rules.json`。有錯時會直接指出檔案與原因。

### 4. 用真實 DDL 看結果

```bash
python run.py
```

打開 `reports/<DDL名>.report.md`，搜尋 `SKILL.order_needs_created_at`：

- 表有 `created_at` → `pass`
- 表沒有且 enforcement 是 `blocking` → `fail`，整份設計不合規
- 規則不適用 → `skipped`

最後執行完整守門：

```bash
python tests/checking_verbs_test.py
python tests/architecture_test.py
python tests/golden_test.py
```

只有刻意改變既有閘門結果時，才使用 `python tests/golden_test.py --update` 更新基準並
審查 checking rule ID 差異。

日常只需記住以下指令：

```bash
python rules.py new <rule_id>                         # 預設 Common/gating
python rules.py new <domain> <gating|advisory> <id>  # 指定位置
python rules.py check                                 # 新增後通常只需跑這個
python rules.py list                                  # 查看所有規則
python rules.py lint                                  # 只檢查，不 compile
```

---

## skill 依 domain 切分

```
config/skills/
├── Common/     ← 跨 domain 共用，每次一定載入（17 條 gating 基線＋3 條 advisory）
├── PLM/        ← 產品生命週期（料件主檔/BOM 用量 gating；BOM/版次/生命週期/變更 advisory）
├── FCM/  BLM/  CRM/   ← 其他領域（依需要放規則，空目錄也可先建）
```

每個 domain 內分 `gating/`（會擋）與 `advisory/`（只提示）。
新增 domain＝建資料夾丟 `.md`，自動被掃到、不用註冊。

**每次載入哪些 domain**：`Common` 永遠載入。未指定時只載入 `Common`
並發出警告，避免無關 domain 誤擋。要指定就複製 `input/_domains.yaml.template`
成 `_domains.yaml`（整批）或
`<DDL名>.domains.yaml`（單檔），寫 `domains: [PLM, FCM]` 加自由描述。
未知 domain 會被略過並列在報告；CLI 只有明確傳 `--domains '*'` 才載入全部。

## Business Key 明確宣告

ClickHouse `ORDER BY` 是物理排序鍵，`PRIMARY KEY` 是索引語意，兩者都不證明
業務唯一性。因此 business key 只從 `<DDL名>.keys.yaml` 讀取：

```yaml
business_keys:
  dim_customer: [customer_id]
  subscription: [subscription_id]
```

可複製 `input/_keys.yaml.template`。表名或欄位不存在會由
`BUSINESS_KEY.METADATA` 擋下；未提供時 `structural_business_key` 會照實報告。

---

## 命名詞彙字典（glossary）

`config/glossary.yaml`：禁用詞→標準詞（cust→customer）、別名→正規詞（client→customer）、
標準詞白名單。naming 卡控用 `no_banned_term` / `no_alias_term` / `term_in_glossary`
三個動詞對照字典，不用寫一堆正則。production 的概念比對也用它。

## production — 已核准 DDL 的治理基準區

`production/<domain>/*.sql` 放的是**已經由 owner 核准、可代表正式環境標準**的 DDL。
它不是待驗證區，也不負責部署；它是唯讀參照基準，讓後續新設計沿用已核准的命名。

### 如何參照 production

新 DDL 必須用同名 companion 明確指定 domain：

```yaml
# input/order.domains.yaml
domains: [CRM]
```

執行 `python run.py` 時，工具會自動加入 `Common` 規則，並且**只讀取本次指定 domain**
對應的 production 目錄；上例只會參照 `production/CRM/*.sql`。指定多個 domain 時：

```yaml
domains: [CRM, FCM]
```

就會合併參照 `production/CRM/` 與 `production/FCM/`。沒有 domains companion 時不猜測
業務領域，也不掃描全部 production，而是明確回報 skipped。

### production 如何卡控

目前 production 只做一件可確定判斷的事：**已核准命名一致性**。

假設 `production/CRM/dim_customer.sql` 已使用 `customer_email`，新設計使用
`client_email`；詞彙字典又宣告 `client → customer`，兩者會被辨識為同一概念，
但名稱不同，因此 `PRODUCTION.NAMING_CONSISTENCY` 會擋下並要求沿用
`customer_email`。

報告會直接出現以下 checking rule ID：

| Rule ID | 結果 | 意思 |
|---|---|---|
| `PRODUCTION.SCOPE` | pass | 找到本次指定 domain 的 production DDL，已納入參照。 |
| `PRODUCTION.SCOPE` | skipped | 未指定 domain，或指定的 domain 尚無 production DDL。 |
| `PRODUCTION.NAMING_CONSISTENCY` | pass | 新設計與已核准命名一致。 |
| `PRODUCTION.NAMING_CONSISTENCY` | fail | 同概念使用不同名稱，會使整份設計不合規。 |
| `SYSTEM.PRODUCTION_PARSE` | fail | production DDL 本身無法解析；先修基準檔才可繼續。 |

### 何時把 DDL 放進 production

1. DDL 先放在 `input/`，完成 Business Key、domain 與所有 gating 檢查。
2. 由 domain owner 確認這份命名可作為後續標準。
3. 複製到 `production/<domain>/`，例如 `production/CRM/dim_customer.sql`。
4. 透過 PR 審查後合併；從此後該 DDL 就是此 domain 的參照基準。

草稿、實驗表、尚未核准的 DDL 不應放進 production，否則會把暫時命名變成正式卡控。

## Lineage 關聯治理

這裡治理的是**設計時宣告的 lineage**：某個目標表從哪些來源表取得資料、哪些欄位互相
對應。它可以檢查設計是否自洽，但不宣稱已觀測 Airflow、dbt、Spark 或查詢紀錄；真正的
runtime lineage 未來可以再與這份設計宣告交叉比對。

### 明確宣告關係

複製 `input/_lineage.yaml.template` 成與 DDL 同名的 companion，例如
`input/subscription.lineage.yaml`：

```yaml
lineage:
  subscription:
    upstream:
      - domain: CRM
        table: dim_customer
      - domain: local
        table: billing_event
    columns:
      customer_id: CRM.dim_customer.customer_id
      customer_email: CRM.dim_customer.customer_email
      monthly_price: local.billing_event.amount
```

- `lineage` 下一層是本次 DDL 裡的**目標表**。
- `domain: local` 表示來源也在同一份 DDL。
- 外部 domain（例如 `CRM`）必須同時由 `<DDL名>.domains.yaml` 選取，來源表必須存在於
  `production/CRM/*.sql`；因此 production 同時是外部 lineage 的可解析資產清單。
- `columns` 的左邊是目標欄位，右邊固定用 `domain.table.column`。

明確宣告後，以下 checking rule ID 會進閘門區：

| Rule ID | 檢查內容 |
|---|---|
| `LINEAGE.METADATA` | YAML 格式正確，目標表存在。 |
| `LINEAGE.DOMAIN_SCOPE` | 外部來源 domain 已由 domains YAML 選取。 |
| `LINEAGE.UPSTREAM_EXISTS` | local 或 production 中存在宣告的來源表。 |
| `LINEAGE.COLUMN_EXISTS` | 來源／目標欄位存在，來源也已列在 upstream。 |
| `LINEAGE.TYPE_COMPATIBILITY` | 欄位基本型別相容。 |
| `LINEAGE.CYCLE` | 同一份 DDL 的 local 關係沒有循環。 |
| `SYSTEM.LINEAGE_SPEC` | companion YAML 無法解析時直接擋下。 |

其中任何 `fail` 都會使設計不合規。報告的獨立 Lineage 區塊會呈現所有已宣告的關係，
即使某個欄位映射驗證失敗，仍可看出原本想表達的來源與目標。

### 沒有設定 YAML 時

工具不會把推測當成事實，也不會因此擋下：

1. 優先尋找「某表的明確 Business Key 同時出現在另一張表」的候選關係。
2. 找不到時，才以兩表共用的 `*_id` 提示可能相關，並標示方向未知。
3. 候選以 `LINEAGE.SUGGESTION` 放在顧問區，報告標示「系統建議、需 owner 確認」。
4. 若連可靠候選也沒有，建議區會說明系統沒有足夠證據，不會硬猜資料流向。

如果某表確實是獨立資料主體、沒有上游，請明確留下治理決策：

```yaml
lineage:
  standalone_table:
    upstream: []
    columns: {}
```

這樣報告會顯示「已明確宣告無上游關聯」，而不是永遠留下一個待確認的缺口。

## SSOT 未登錄主體推斷（警告放行）

表看似某主體的權威表（單一 business key `X_id`＋描述屬性）但 X 不在 registry 時，
閘門區發**警告**「先登錄再上線」（不擋），修法直接指向 registry 位置。
候選也列進 advisory prompt，agent 可產 registry 草稿、人工確認後寫回——
registry 隨驗證流程長大。

## 卡控一致性保證（checking rule ID＋黃金測試）

閘門區＝純函數 f(DDL, 規則集)：無 LLM、無網路、無時間、無隨機。
`python tests/golden_test.py` 三類守門：T1 黃金比對（閘門輸出 vs 基準，防改 A 傷 B）、
T2 確定性（連跑兩次 checking rule ID 結果一致）、T3 LLM 不可滲透
（FakeLLM 下 checking rule ID 結果不變）。
注意：黃金測試只守「基準 DDL 有踩到的規則」，新增重要規則記得讓基準覆蓋它。

## DataHub（目前未接）

`config/default.yaml` 的 `datahub.enabled: false`。接上後做必填欄位檢查
（確定性、可擋）；失聯降級成提示放行（條件式閘門），報告會標示實檢/略過/降級。
未來接上 runtime lineage 後，可與目前的設計 lineage 做一致性交叉驗證。

---

## 加入你們自己的檢查規則（skill）

每條 skill 是一份 **Markdown 規範文件**：人讀規範（目的/適用情境/違反後果/修正建議）
＋機器執行的卡控區塊（` ```check ` 確定性會擋、` ```check-llm ` 語意只提示）。

手動新增請直接照上面的「5 分鐘新增一條 rule」。也可以對 agent 說
「幫我新增一條 rule：<需求>」，它會讀 `SKILL_AUTHORING.md`、產出檔案並執行
`python rules.py check`。

完整規格（含全部卡控動詞清單、範例、自我檢查清單）見 **`SKILL_AUTHORING.md`**。
卡控動詞速查：

| 語句 | 意思 |
|---|---|
| `applies_to: name_matches "<正則>"` / `has_column <欄位>` | 限定適用的表 |
| `require: has_column <欄位>` / `column_type <欄位> <型別>` / `not_nullable <欄位>` | 欄位存在／型別／非空 |
| `require: columns_not_both <A> <B>` | A、B 不可同時存在 |
| `require: name_matches <欄位> <正則>` / `all_columns_name_match <正則>` | 欄位命名樣式 |
| `require: table_name_matches <正則>` / `identifier_max_length <n>` | 表名樣式／長度上限 |
| `require: column_commented <欄位>` / `all_columns_commented` | COMMENT 註解 |
| `require: has_business_key` / `has_primary_key` / `has_order_by` | 業務鍵／明確 PRIMARY KEY／物理排序鍵 |
| `require: no_nullable_in_key` | business / primary / sorting key 均不可 Nullable |
| `require: engine_matches <正則>` / `type_not_used <型別>` / `lowcardinality_when_present <欄位>` | 引擎／禁用型別／LowCardinality |
| `require: type_not_for_matching <欄名正則> <型別>` / `datetime_with_timezone` | 金額禁 float／時區 |
| `require: pk_ends_with <字尾>` / `columns_not_named <清單>` | 鍵名字尾／保留字 |
| `require: no_banned_term` / `no_alias_term` / `term_in_glossary` | 對照詞彙字典 |

寫錯的卡控語句不會讓整條壞掉——會被略過並在報告與 `rules.py check` 提示。
目前 lint 也會檢查重複/illegal ID、必要章節、單一 check fence、
folder/zone/enforcement、regex、Python `SKILL_META` 與 domain。
複雜到宣告式寫不出來的（跨表、遞迴、需樣本），用 Python 放 `config/skills_py/`
（`SKILL_META` ＋ `check(schema, table[, ctx])` 或跨表的 `check_schema(schema, ctx)`）。

---

## 這包工具的檔案架構（逐檔詳解）

### 根目錄 — 入口與工具

| 檔案 | 說明 |
|---|---|
| `run.py` | **日常入口**。①編譯結構化規則 ②掃 DDL 與 sample/context/domains/keys/lineage companions ③逐檔驗證 ④支援 `--strict`。未接 LLM 時不產 HTML（等補完）。 |
| `rules.py` | **規則管理工具**：`new` 建骨架、`check` 一次 lint＋compile、`list` 盤點；`lint`/`compile` 仍可分開執行。 |
| `merge_advisory.py` | **顧問區補完合併**。先以 `advisory_result.schema.json` 驗證，再直接比對合併前後 gating findings，全部一致才產生 HTML。 |
| `AGENTS.md` / `CLAUDE.md` | **雙 agent CLI 入口檔**（opencode／Claude Code 各自自動讀取，內容對齊需同步維護）：操作流程、補完往返、不可破壞保證。 |
| `SKILL_AUTHORING.md` | **「產生 skill 的 skill」**：人與 agent 共用的規則撰寫完整規格。 |
| `docs/專案介紹.md` | **介紹長文**：背景、理念、系統實際在做什麼——給要理解專案的人；本 README 給要使用維護的人。 |

### `dataval/` — 引擎（不藏規則，只有機制）

| 檔案 | 說明 |
|---|---|
| `engine.py` | **總指揮**。`validate()`：解析 → 確保 compiled 最新 → **從 build JSON 載入規則執行**（閘門零 LLM）→ 概念層 → production 對照 → 未登錄推斷 → DataHub 站 → `_enforce_zone`（第二道保險）→ 確定性排序。 |
| `parser.py` | DDL 解析（sqlglot，ClickHouse 優先、方言可換）→ Schema/Table/Column。 |
| `model.py` | 資料模型。Finding 含 zone/status/severity/expected/actual/fix。 |
| `skills/__init__.py` | **規則載入器**。執行用 `load_compiled()`（讀 build JSON、domain 過濾、py 依 manifest 載入）；工具用 `load_domains()`（直接解析 .md，供 rules.py list/lint 與 compiler）。py skill 支援 `check(schema, table[, ctx])` 與跨表的 `check_schema(schema, ctx)`。 |
| `skills/markdown_skill.py` | **卡控動詞引擎（最核心）**。解析 .md、實作所有動詞的判斷與四問輸出（期望/實際/修法）、`skill_from_compiled` 反序列化。新增動詞：`_parse_check` 加語法＋`_eval` 加判斷。 |
| `compiler.py` | **規則 compile**。序列化成 `build/compiled_rules.json`（確定性、含 domain 清單與 checking rule ID）；`ensure_compiled` 直接比對結構化內容。與執行共用同一套解析。 |
| `report.py` | 報告產生：`to_markdown`/`to_json`（兩區分段＋blocking_summary）/`to_html`（單檔互動）。 |
| `production.py` | 只讀取已指定 domain 的 production DDL，做已核准命名一致性卡控。 |
| `lineage.py` | 驗證明確 lineage 的來源、欄位、型別、domain 與循環；未設定時只產生非阻擋候選。 |
| `subject_inference.py` | SSOT 未登錄主體推斷（確定性啟發，警告放行，候選供 agent 產草稿）。 |
| `subject_summary.py` | data subject 摘要（合規狀態/domain/結構/用途）。 |
| `advisory_export.py` | 產 `advisory_prompt.md`（給 agent 的補完指示＋schema＋回填格式）。 |
| `concept.py` | 顧問區概念層（主體性提問，需 LLM）。 |
| `llm.py` | LLM 連線（`from_env`、`NullLLM` 優雅降級、`OpenAICompatLLM` 直連）。 |
| `datahub.py` | DataHub 站（目前 bypass；接上後必填檢查、失聯降級）。 |
| `cli.py` | 進階單檔入口（`--ddl --sample --domains --out-html --strict` 等）。 |

### `config/` — 規則面與設定（手寫的）

| 位置 | 說明 |
|---|---|
| `skills/<domain>/gating/*.md` | **會擋/警告的確定性規則，一條一檔**。Common 17 條基線（結構/命名/實踐/SSOT）；PLM 2 條。 |
| `skills/<domain>/advisory/*.md` | **語意規則（只提示）**。Common 3 條；PLM 4 條；FCM 1 條。 |
| `skills_py/*.py` | 跨表/需樣本的複雜規則 6 條（FK 解析、型別對樣本、SSOT 權威/join key/事實重複、事件時間）。 |
| `default.yaml` | SSOT registry（實體→權威表/鍵/屬性/attribute_owner）與 DataHub 設定。不放規則。 |
| `glossary.yaml` | 詞彙字典（禁用詞/別名/白名單）。 |
| `advisory_result.schema.json` | agent 顧問區回填的 JSON Schema；合併前強制驗證。 |
| `templates/` | 兩份空白規則範本（`rules.py new` 的骨架來源）。 |

### `build/` — build 產物（自動生成，勿手改）

| 檔案 | 說明 |
|---|---|
| `compiled_rules.json` | **規則的執行格式**。每次執行前自動由 .md compile 而成（含 domain 清單、checking rule ID 與卡控結構），**引擎實際從這份 JSON 載入規則**——單一執行來源，可直接 diff 與稽核。 |

### 輸入、production、輸出

| 位置 | 說明 |
|---|---|
| `input/` | 待驗證 DDL＋同名附帶檔（樣本/情境/domains/business keys/lineage）。內含 domains/keys/lineage 範本。 |
| `production/<domain>/*.sql` | 已核准 DDL 的唯讀參照基準；只對明確指定的 domain 做命名卡控。 |
| `reports/` | `.report.md`/`.report.json`/`.subject_summary.md`；補完後的 `.report.html`；待補完時的 `.advisory_prompt.md`。 |

### `tests/` — 守門

| 檔案 | 說明 |
|---|---|
| `golden_test.py` ＋ `golden/` | 三類守門測試與黃金基準（見「卡控一致性保證」）。 |
| `checking_verbs_test.py` | 24 個宣告式 checking 動詞＋2 個 applies_to 動詞的 pass/fail 最小測例。 |
| `architecture_test.py` | domain 安全預設、未知 domain、明確規則狀態、三種鍵語意與 advisory merge 保護。 |

GitHub Actions 會在 Python 3.10/3.11/3.12 自動執行 lint、動詞、架構、黃金與語法測試。

---

## 延後與待辦

- 擴充跨動詞、跨 domain 與大型 DDL 的整合測試
- DataHub/runtime lineage 與設計 lineage 的一致性交叉驗證
- 實踐畢業流程自動化（LLM 發現 → 人工確認 → 沉澱成確定性規則）
- 換上真實 domain 規則、調整 `default.yaml` registry 與 `glossary.yaml` 至公司實況

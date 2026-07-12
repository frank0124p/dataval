# dataval：ClickHouse DDL 資料治理

把 DDL 放進 `input/`，執行一個指令，就能得到可重複的合規判定與可讀報告。

本專案刻意維持兩個清楚區域：

- **閘門區**：確定性規則，可能擋下設計；同樣輸入永遠得到相同 checking rule ID 結果。
- **顧問區**：LLM 或啟發式建議，一律 `info`，永遠不影響合規判定。

專案背景與價值說明見 [`docs/專案介紹.md`](docs/專案介紹.md)。

## 快速開始

### 1. 建立環境

macOS／Linux 不需要系統提供 `python` 指令，直接使用 `python3` 建立專案環境：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

需要在 VS Code 使用時，專案已設定 `.venv/bin/python` 為預設 interpreter。

### 2. 放入 DDL

```text
input/order.sql
```

可選的同名 companion：

| 檔案 | 用途 |
|---|---|
| `order.sample.json` | 少量樣本，用來檢查宣告型別與 join key。 |
| `order.context.txt` | 一句話描述業務情境，供顧問區理解。 |
| `order.domains.yaml` | 指定要載入的業務 domain。 |
| `order.keys.yaml` | 明確宣告每張表的 Business Key。 |
| `order.lineage.yaml` | 宣告來源表、目標表與欄位映射。 |

`input/` 已提供 domains、keys、lineage 三份範本。

### 3. 執行

```bash
.venv/bin/python run.py
```

CI 要在不合規時失敗：

```bash
.venv/bin/python run.py --strict
```

預設掃描 `input/`、輸出到 `reports/`。測試其他資料夾時可設定：

```bash
DATAVAL_INPUT_DIR=examples/lineage/input \
DATAVAL_REPORT_DIR=examples/lineage/reports \
.venv/bin/python run.py
```

## 架構：一條主流程

```text
DDL + companions
      │
      ▼
run.py / load_input()          一次讀完 DDL、sample、domain、keys、lineage
      │
      ▼
parser.py                      SQL → Schema / Table / Column
      │
      ▼
compiler.py + skills/          Markdown 規則 → compiled_rules.json → 執行
      │
      ├── Business Key metadata
      ├── production 已核准命名
      ├── lineage 關係、欄位、型別、循環
      └── SSOT 與跨表 Python 規則
      │
      ▼
engine.py / _enforce_zone()    強制分成閘門區與顧問區
      │
      ▼
report.py                      Markdown / JSON / HTML
```

只有三個根目錄指令：

| 指令 | 用途 |
|---|---|
| `.venv/bin/python run.py` | 唯一日常驗證入口，批次掃描 DDL。 |
| `.venv/bin/python rules.py ...` | 建立、檢查與編譯規則。 |
| `.venv/bin/python merge_advisory.py` | 將 agent 建議安全合併並產生 HTML。 |

沒有第二套進階 CLI。尚未實作的外部整合也不放 placeholder，避免報告看起來像做了實際檢查。

## 規則只有一個家

```text
config/skills/<domain>/{gating,advisory}/*.md   人讀、可 diff 的規範
                         │
                         ▼ compile
build/compiled_rules.json                      執行格式，請勿手改
                         │
                         ▼
engine.py                                      只執行機制，不藏業務規則
```

- `gating/*.md` 使用 `check`：確定性，可設 blocking 或 warning。
- `advisory/*.md` 使用 `check-llm`：語意建議，永不擋。
- `config/skills_py/*.py`：只放宣告式動詞無法表達的跨表或樣本規則。

### 新增一條規則

```bash
.venv/bin/python rules.py new order_needs_created_at
```

預設建立 `config/skills/Common/gating/order_needs_created_at.md`。指定 domain／區域：

```bash
.venv/bin/python rules.py new CRM gating customer_needs_name
.venv/bin/python rules.py new CRM advisory customer_name_semantic
```

最小規則範例：

````markdown
---
id: order_needs_created_at
category: structural
enforcement: blocking
---

# 表必須記錄建立時間

## 目的
保留資料首次建立時間。

## 適用情境
所有共用資料表。

## 違反後果
無法穩定追查資料產生時間。

## 修正建議
新增 `created_at DateTime('UTC')`。

## 卡控
```check
require: has_column created_at
```
````

完成後：

```bash
.venv/bin/python rules.py check
.venv/bin/python run.py
```

完整格式與 checking verbs 見 [`SKILL_AUTHORING.md`](SKILL_AUTHORING.md)。

## Domain 與 Business Key

`Common` 每次一定載入；其餘 domain 只由 companion 明確指定：

```yaml
# input/order.domains.yaml
domains: [CRM]
```

未指定時只載入 `Common` 並提出警告，不會偷偷掃描全部 domain。未知 domain 會顯示在報告。

Business Key 必須明確宣告：

```yaml
# input/order.keys.yaml
business_keys:
  orders: [order_id]
```

ClickHouse `ORDER BY` 是排序鍵，`PRIMARY KEY` 是索引語意；兩者都不能證明業務唯一性。
表名或欄位錯誤會由 `BUSINESS_KEY.METADATA` 擋下。

## production：已核准基準

`production/<domain>/*.sql` 只放 owner 已核准、可作為正式標準的 DDL。它不負責部署，
只供新設計參照。

當 `order.domains.yaml` 指定 `CRM` 時，工具只讀 `production/CRM/`：

- `PRODUCTION.SCOPE`：是否找到本次選取 domain 的基準。
- `PRODUCTION.NAMING_CONSISTENCY`：同概念是否沿用已核准名稱。
- `SYSTEM.PRODUCTION_PARSE`：基準 DDL 無法解析時擋下。

例如 production 使用 `customer_email`，新設計使用同概念別名 `client_email`，會要求沿用
已核准名稱。詞彙正規化來自 `config/glossary.yaml`。

建議流程：新 DDL 先在 `input/` 通過 → domain owner 核准 → PR 放入
`production/<domain>/` → 後續設計開始參照。

## Lineage：設計關係

Lineage companion 描述設計意圖，不宣稱已觀測到 runtime job：

```yaml
# input/order.lineage.yaml
lineage:
  orders:
    upstream:
      - domain: CRM
        table: dim_customer
      - domain: local
        table: staged_order
    columns:
      customer_id: CRM.dim_customer.customer_id
      order_id: local.staged_order.order_id
```

- `local` 表示來源在同一份 DDL。
- 外部來源 domain 必須出現在 `.domains.yaml`，來源表必須存在於該 domain 的 production。
- `columns` 左邊是目標欄位，右邊固定為 `domain.table.column`。

明確宣告後的閘門規則：

| Checking rule ID | 檢查 |
|---|---|
| `LINEAGE.METADATA` | YAML 結構與目標表。 |
| `LINEAGE.DOMAIN_SCOPE` | 外部 domain 已選取。 |
| `LINEAGE.UPSTREAM_EXISTS` | 上游表存在。 |
| `LINEAGE.COLUMN_EXISTS` | 來源／目標欄位存在。 |
| `LINEAGE.TYPE_COMPATIBILITY` | 來源／目標基本型別相容。 |
| `LINEAGE.CYCLE` | local 關係沒有循環。 |
| `SYSTEM.LINEAGE_SPEC` | companion 無法解析。 |

沒有 lineage YAML 時不會擋：

1. 先用明確 Business Key 尋找候選關係。
2. 找不到時才用共用 `*_id` 提示，並標示方向未知。
3. `LINEAGE.SUGGESTION` 只進顧問區。
4. 沒有可靠候選時明確說「證據不足」，不硬猜。

確實沒有上游時應留下明確決策：

```yaml
lineage:
  standalone_table:
    upstream: []
    columns: {}
```

六種可執行組合見 [`examples/lineage/README.md`](examples/lineage/README.md)。

## 報告與顧問區

每個 DDL 會產生：

| 輸出 | 用途 |
|---|---|
| `<名稱>.report.md` | 人讀報告。 |
| `<名稱>.report.json` | 程式整合；包含 gating、advisory 與 lineage 結構。 |
| `<名稱>.subject_summary.md` | Data Subject 結構與用途摘要。 |
| `<名稱>.advisory_prompt.md` | 未接本地 LLM 時，交給 agent 的補完指示。 |
| `<名稱>.report.html` | 顧問區補完後產生的單檔互動報告。 |

報告直接列 checking rule ID，不使用指紋。每條失敗包含：規則、位置、期望、實際、修法。
Lineage 另以「來源 → 目標 → 欄位映射」顯示，並區分 YAML 宣告與系統建議。

### Agent 補完 HTML

未設定本地 LLM 時：

```text
run.py
  → advisory_prompt.md
  → agent 產 advisory_result.json
  → merge_advisory.py
  → report.html
```

Agent 的 JSON 會先依 `config/advisory_result.schema.json` 的契約驗證；合併前後的完整
gating findings 必須逐項相同，否則拒絕寫入。

有 OpenAI 相容的內部模型時，可設定：

```bash
export DATAVAL_LLM_BASE_URL=http://localhost:4000/v1
export DATAVAL_LLM_MODEL=company-default
export DATAVAL_LLM_API_KEY=optional
```

## 測試

```bash
.venv/bin/python tests/checking_verbs_test.py
.venv/bin/python tests/architecture_test.py
.venv/bin/python tests/golden_test.py
```

Golden 測試保證：

- 基準 DDL 的 gating findings 與 checking rule ID 摘要不漂移。
- 同樣輸入連跑兩次結果一致。
- FakeLLM 無法滲入閘門區。

只有刻意改變既有結果時才執行：

```bash
.venv/bin/python tests/golden_test.py --update
```

GitHub Actions 會在 Python 3.10、3.11、3.12 執行規則 lint、測試與語法檢查。

## 目前檔案地圖

```text
run.py / merge_advisory.py / rules.py   三個入口
dataval/
  engine.py                             主流程與兩區保護
  parser.py / model.py                  SQL 解析與資料模型
  compiler.py / skills/                 規則編譯、載入、checking verbs
  production.py / lineage.py            正式基準與設計關係
  subject_inference.py                  未登錄 SSOT 主體候選
  concept.py / llm.py                   顧問區與選用 LLM
  advisory_export.py                    Agent 補完契約
  subject_summary.py / report.py        摘要與三種報告
config/
  skills/ / skills_py/                  規則來源
  default.yaml / glossary.yaml          SSOT registry 與詞彙
  advisory_result.schema.json           Agent 回填契約
input/                                  待驗證 DDL 與 companions
production/                             已核准 DDL
examples/lineage/                       六種 lineage 組合
tests/                                  verbs、architecture、golden
```

目前刻意不包含未完成的外部 metadata 平台或 runtime lineage connector。需要時應以真實
介面、可測試的 checking rule ID 與明確失敗策略加入，而不是先放永遠 bypass 的模組。

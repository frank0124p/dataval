# dataval：ClickHouse DDL 資料治理

本地端的資料設計驗證工具。輸入一組 data subject（DDL＋樣本＋關聯＋語意描述），
輸出合規報告（Markdown / JSON / HTML）。核心設計：

- **兩區架構**：閘門區（確定性、可重現、會擋，執行路徑零 LLM）與
  顧問區（LLM 語意建議，只提示、永不影響合規判定）。`_enforce_zone` 在程式層強制此邊界。
- **四類檢查**：結構、命名、最佳實踐、SSOT。
- **policy-as-code**：規則以 Markdown 撰寫（人讀的規範＋機器執行的卡控區塊同檔），
  compile 成 `build/compiled_rules.json` 後執行。
- **正式區治理**：通過驗證的 subject 晉升進 `production/`，帶晉升記錄與雙碼；
  subject 之間的關聯合併成全域 lineage 圖，支援循環偵測、基數矛盾、影響分析與全區健檢。

## 快速開始

### 1. 建立環境

```bash
python3 -m venv .venv
.venv/bin/pip install sqlglot pyyaml
```

### 2. 準備輸入（一個 data subject 一組四件）

以 `<名>.sql` 為錨，**四件都要有**，缺任一件不會產生報告：

```text
input/
  <名>.sql                DDL（ClickHouse；可含多張 CREATE TABLE）
  <名>.samples/<表名>.csv  樣本資料，DDL 每張表各一份（表頭=欄名）
  <名>.relations.yaml     表間關聯（from / to / cardinality）
  <名>.context.md         語意描述（front-matter＋段落，「粒度」必填）
```

格式細節與慣例（CSV 的 NULL 表示法、relations 的三段式跨 domain 引用、
context 的必填段落）見 **`input/README.md`**。本資料夾附兩個範例：
`order.*`（合格提交的完整參考）與 `subscription.*`（刻意含違規的示範）。

### 3. 執行

```bash
.venv/bin/python run.py
```

`run.py` 是唯一日常入口，零參數自動掃 `input/`：

1. **前置檢核**（存在 → 可解析 → 一致三層）：四件不齊的 DDL 直接跳過、
   印出缺件檢核表、留檔 `reports/<名>.precheck.md`，並以 **exit code 2** 結束。
2. 檢核通過 → 跑閘門區全部確定性規則 → 產出三式報告到 `reports/`：
   `<名>.report.md`（人讀）、`.report.json`（程式讀）、`.report.html`
   （單檔互動，直接雙擊開瀏覽器）。
3. 未接 LLM 時另產 `<名>.advisory_prompt.md` 供 agent 補完顧問區
   （見「Agent 補完顧問區」）。

exit code：`0` 全部合規；`1`（`--strict`）存在不合規；`2` 有輸入不齊全的 subject。

## 架構：一條主流程

```text
input/（四件套）
  → 前置檢核（precheck.py：存在／可解析／一致，缺件即止）
  → parser.py（sqlglot，ClickHouse 優先、方言可換）
  → 規則 compile（.md → build/compiled_rules.json，有變更才重建）
  → 閘門區：compiled 規則（.md 卡控動詞）＋ config/rules/*.py（程式式）
            ＋ business key／production 基準／lineage／全域關聯圖／SSOT 推斷
  → 顧問區：check-llm 語意規則＋概念層（concept.py，主體性提問）
  → _enforce_zone（第二道保險：LLM 產出強制降為 info）
  → reports/（md / json / html ＋ subject_summary ＋ precheck）
```

閘門區的保證由測試守護（見「測試」）：同一輸入＋同一規則集，
checking rule ID 結果必須一致；LLM 存在與否不得改變閘門判定。

## 規則只有一個家

| 位置 | 內容 |
|---|---|
| `config/domain/<域>/gating/*.md` | 會擋／警告的確定性規則，一條一檔。`Common/` 為跨域基線（結構 5、命名 7、最佳實踐 4、SSOT 1），`PLM/` 等領域按需載入 |
| `config/domain/<域>/advisory/*.md` | 語意規則（` ```check-llm `，只提示） |
| `config/rules/*.py` | 程式式規則（跨表／需樣本的複雜邏輯，6 條） |
| `config/glossary.yaml` | 詞彙字典（禁用詞／別名／白名單） |
| `config/default.yaml` | SSOT registry 與 DataHub 設定（不放規則） |
| `config/cases/<名>.yaml` | 個案補充設定（選配；四件輸入為權威來源） |
| `build/compiled_rules.json` | 規則的**執行格式**（自動生成，勿手改） |

新增規則：`python rules.py new <域> <gating|advisory> <rule_id>`，
格式與允許的卡控動詞以 `SKILL_AUTHORING.md` 為準。
新增 domain 只需建資料夾放 `.md`，自動遞迴掃描。

## 輸入四件的角色

| 件 | 誰提供 | 被誰消費 |
|---|---|---|
| DDL | 資料設計者 | 全部規則 |
| 樣本 CSV | 資料設計者 | 型別對樣本、join key 編碼一致、**relations 基數實檢** |
| relations.yaml | 資料設計者 | 轉為 declared lineage（表存在／欄位存在／型別相容／循環，會擋）；基數對樣本矛盾 → `RELATION.CARDINALITY_SAMPLE` 會擋；晉升後成為全域圖的邊 |
| context.md | 資料設計者＋領域負責人 | front-matter（subject／domains／business_keys）進引擎；「粒度」等段落餵顧問區與概念層 |

## 正式區（production/）

正式區存放**已核准的 data subject**，一 subject 一資料夾：

```text
production/
  <DOMAIN>/
    <subject>/
      <subject>.sql              已核准 DDL
      <subject>.relations.yaml   關聯宣告（全域 lineage 圖的邊）
      <subject>.context.md       語意描述（粒度宣告留檔）
      _promotion.yaml            晉升記錄（日期、卡控結果碼、規則版本碼、樣本 hash）
```

樣本**不進**正式區（驗證證據非正式資產）；晉升記錄存各 CSV 的 SHA256 供追溯。
舊式平鋪 `production/<域>/*.sql` 仍相容載入，健檢會提醒遷移。

### 晉升：promote.py

```bash
.venv/bin/python run.py                 # 先驗證
.venv/bin/python promote.py <名>        # 合規才能晉升
.venv/bin/python promote.py <名> --update   # 重新晉升（保留前版記錄）
```

晉升前提是最新報告 `summary.compliant == true`，不合規會被拒絕。
晉升記錄的兩碼提供因果保證：

- **卡控結果碼** = 閘門區 findings（rule｜status｜target）排序後的 SHA256
- **規則版本碼** = `build/compiled_rules.json` 內容的 SHA256

### 正式區給新 subject 的檢查

新 subject 驗證時，除了既有的命名基準比對（`PRODUCTION.NAMING_CONSISTENCY`）
與 lineage 上游實檢，還會對照**全域關聯圖**（`dataval/prodgraph.py`）：

| Checking rule | 等級 | 內容 |
|---|---|---|
| `PRODGRAPH.CYCLE` | 會擋 | 本 subject 加入後，跨 subject 關聯圖出現循環 |
| `PRODGRAPH.CARDINALITY_CONFLICT` | 會擋 | 同一對端點在正式區已有不同的 cardinality 宣告 |
| `PRODGRAPH.IMPACT` | 資訊 | 本 DDL 定義的表在正式區有誰依賴（改動的爆炸半徑） |

### 全區健檢：production_audit.py

```bash
.venv/bin/python production_audit.py
```

不是驗新 subject，而是掃整個正式區：三件齊全、DDL 可解析、
斷鏈（關聯指向的上游表不存在於任何 subject）、全域循環、基數矛盾，
以及**規則版本碼 drift**——晉升時的規則版本 ≠ 現行版本的 subject 會被標記
「建議重驗」。輸出 `reports/production_audit.md`；有 fail 時 exit code 1。

## Lineage 能力總覽

- **宣告面（單 subject）**：relations.yaml → declared lineage。本地端點驗存在；
  跨 domain 端點（`DOMAIN.table.col`）對 `production/<DOMAIN>/` 實檢
  表存在、欄位存在、型別相容；local 循環與 domain scope 會擋。
- **實檢面**：宣告 `N:1`／`1:1` 但「1 的一方」樣本出現重複鍵 → 會擋。
- **全域面（跨 subject）**：正式區所有 relations 合併成 DAG——循環、
  基數矛盾會擋；影響分析列出依賴者；健檢抓斷鏈。
- **建議面**：未宣告時，以 business key／共用 `*_id`／Mermaid ER diagram
  （`config/er_diagrams/<名>.mmd`）產生保守的候選關係，只提示不擋。

## 報告與顧問區

三式報告皆分兩區呈現，合規判定只由閘門區決定。HTML 為單檔互動
（判定卡片、搜尋、fail/warning 篩選、摺疊分類）。

### Agent 補完顧問區

`run.py` 是獨立 subprocess，不繼承 agent 的 LLM——這是刻意的隔離邊界，
確保閘門區在 agent session 內也零 LLM。未設 `DATAVAL_LLM_BASE_URL` 時：

1. `run.py` 產出 `reports/<名>.advisory_prompt.md`
2. agent（opencode 讀 `AGENTS.md`；Claude Code 讀 `CLAUDE.md`）用自身 LLM
   產出 `<名>.advisory_result.json`
3. `python merge_advisory.py` 合併並重繪三式報告
4. `python merge_advisory.py --status` exit 0 = 顧問區全數補完

直連 LLM 可設 `DATAVAL_LLM_BASE_URL / DATAVAL_LLM_MODEL / DATAVAL_LLM_API_KEY`。

## 測試

```bash
.venv/bin/python -m unittest discover -s tests -p "*_test.py"
```

| 套件 | 守的保證 |
|---|---|
| `golden_test.py` | T1 golden 比對、T2 確定性、T3 LLM 不可滲透閘門 |
| `architecture_test.py` | 兩區邊界、輸入契約、strict exit code、lineage 案例組合 |
| `checking_verbs_test.py` | 每個卡控動詞的判斷邏輯 |
| `precheck_test.py` | P1 四件齊全通過、P2 缺件攔截、P3 基數對樣本矛盾會擋、P4 CSV 轉型慣例 |
| `prodgraph_test.py` | G1 全域循環會擋、G2 基數矛盾會擋、G3 影響分析、G4 健檢（斷鏈／drift／legacy）、G5 晉升閘門與雙碼 |

只有刻意改變結果時才使用 `tests/golden_test.py --update`。

## 環境變數

| 變數 | 用途 |
|---|---|
| `DATAVAL_INPUT_DIR` / `DATAVAL_REPORT_DIR` / `DATAVAL_PRODUCTION_DIR` | 覆寫三個資料夾位置 |
| `DATAVAL_PRECHECK=legacy` | 回到舊的 `config/cases` 集中式輸入（內部 fixtures 用，不建議新案） |
| `DATAVAL_STRICT=1` | 等同 `--strict` |
| `DATAVAL_LLM_BASE_URL` 等 | 直連 LLM（見上節） |

## 檔案地圖

```text
run.py                  日常入口（前置檢核 → 驗證 → 三式報告）
promote.py              晉升合規 subject 到正式區（附雙碼晉升記錄）
production_audit.py     正式區全區健檢
merge_advisory.py       顧問區補完合併（--status 為完成閘門）
rules.py                規則管理 CLI（list / new / lint / compile）
dataval/
  engine.py             主流程與 _enforce_zone
  precheck.py           輸入前置檢核（四件套三層檢核）
  prodgraph.py          正式區全域關聯圖（循環／矛盾／影響／健檢）
  parser.py / model.py  DDL 解析與資料模型
  skills/               規則載入與卡控動詞引擎
  compiler.py           .md → compiled JSON
  lineage.py / production.py / subject_inference.py / concept.py
  report.py / advisory_export.py / subject_summary.py / llm.py / datahub.py
input/                  輸入契約（見 input/README.md）
config/                 規則與設定（規則唯一的家）
production/             正式區（一 subject 一資料夾）
build/                  compile 產物（自動生成）
reports/                報告輸出
tests/                  五組守門測試
```

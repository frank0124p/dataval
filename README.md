# dataval — ClickHouse DDL 資料治理工具

> 本地端、可重現的資料設計驗證引擎。輸入一組 data subject（DDL＋關聯＋語意描述，樣本選填），
> 輸出可稽核的合規報告（Markdown / JSON / HTML）。

一句話：**閘門用確定性規則，LLM 只進顧問區。** 合規判定永遠零 LLM，同一輸入永遠同一結果。

---

## 核心設計

- **兩區架構**
  - **閘門區**：確定性、可重現、會擋合規判定，執行路徑完全不碰 LLM。
  - **顧問區**：LLM 語意建議，一律 `info`，只提示、**永不影響**合規判定。
  - `_enforce_zone` 在程式層強制此邊界——即使 LLM 產出被標成 blocking，也會被降回 info。
- **四類檢查**：結構 · 命名 · 最佳實踐 · SSOT。
- **Policy-as-code**：規則以 Markdown 撰寫（人讀規範＋機器執行的卡控區塊同檔），
  compile 成 `build/compiled_rules.json` 後執行。
- **正式區治理**：通過驗證的 subject 晉升進 `production/`，帶晉升記錄與雙碼；
  跨 subject 的關聯合併成全域 lineage 圖，支援循環偵測、基數矛盾、影響分析與全區健檢。

---

## 快速開始

### 1. 建立環境

需要 **Python 3.10 以上**。使用專案 metadata 安裝，避免繞過 sqlglot／PyYAML
的相容版本範圍：

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

需要逐版完全一致的依賴時，可改用：

```bash
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -e . --no-deps
```

### 2. 準備輸入（一個 data subject＝三件必備＋樣本選填）

以 `<名>.sql` 為錨，**三件必備缺一不可**（缺任一件不會產生報告）；
樣本是**選填**，沒有樣本仍會產生報告，只是樣本相關檢查會略過：

```text
input/
  <名>/
    <名>.sql            DDL（ClickHouse；可含多張 CREATE TABLE）  ← 必備
    relations.yaml      表間關聯（from / to / cardinality）      ← 必備
    context.md          語意描述（front-matter＋段落，「粒度」必填）← 必備
    samples/<表名>.csv   樣本資料，DDL 每張表各一份（表頭＝欄名）  ← 選填
    answers.yaml        迭代問答的答案（merge_advisory 自動產生）  ← 選填
    derivation.sql      寬表實際的 Join SQL（三方對照＋餵顧問區）  ← 選填
```

格式細節與慣例（CSV 的 NULL 表示法、relations 的三段式跨 domain 引用、
context 的必填段落）見 **`input/README.md`**。附兩個範例：
`order/`（合格提交的完整參考）與 `subscription/`（刻意含違規的示範）。

### 3. 執行

```bash
.venv/bin/python run.py            # 跑 input/ 下所有 subject
.venv/bin/python run.py order      # 只跑指定 subject（可多個；
                                   #   也接受 input/order 或 order.sql 寫法）
```

`merge_advisory.py` 也吃相同的 subject 參數（含 `--status`），
只合併／檢查點名的 subject。

### 兩種模式：🎨 design 與 🛡 govern（run.py 自動判定、console 標示）

| | 🎨 design mode | 🛡 govern mode |
|---|---|---|
| 判定 | `input/<名>/` 只有 `context.md`、還沒有 DDL | `input/<名>/<名>.sql` 存在 |
| 做什麼 | 從語意描述**設計**：產出邏輯設計、實體設計文件與草稿 DDL | **治理**：閘門檢核＋顧問區＋迭代問答 |
| 產出 | `reports/<名>.design_report.html`（**設計 HTML 報告**：紫色系、與治理報告視覺區隔；敘事→Logical→Physical 分區＋素材足跡 mindmap，另存輪次版 `<名>.design_round_<N>.report.html`）、`<名>.design_story.md`（**人讀版**：白話設計原因／取捨／實用指南）、`.logical_design.md`、`.physical_design.md`（含欄位血緣：從何處來／去到何處）、`.design.sql`（草稿 DDL 附閘門預檢）＋積木化逐表拆檔 `<名>.design/*.ddl` 與 relations 草稿、`.etl.yaml`（**ETL pipeline 建議檔**，獨立產物） | 三式報告（HTML 含 🗺 素材足跡 mindmap：本次實檢走過哪些 config 沿路徑標亮）、建議 SQL/DDL 拆檔、迭代收斂 |
| 演進 | 設計輪次記錄在 `iterations/<名>/design/`（每輪快照＋DDL 演進 diff＋HISTORY.md） | 治理迭代由 `answers.yaml` 的 `iteration` 驅動 |

**元件定義**（logical vs physical 的邊界檢驗：內容換一個資料庫仍不變
→ logical；會變 → physical。實體與表不必 1:1——寬表／彙總層只存在於
physical）：

| 產物 | 定位 |
|---|---|
| `design_report.html` | **設計 HTML 報告**（一站式入口）：敘事／🧠 Logical 階段／🏗 Physical 階段分區呈現，末尾附**素材足跡 mindmap**——漸進式揭露全貌照畫，本輪實際讀過的素材（`narrative.references` 宣告）沿路徑標亮，必讀漏宣告會 ⚠️。與 🛡 治理報告（`<名>.report.html`，合規判定）是兩份不同的東西 |
| `design_story.md` | **白話敘事**：為什麼、取捨、怎麼用＋**設計出處**（哪個想法來自哪個 config，可點連結） |
| `logical_design.md` | **業務共識**：實體／粒度／關係／指標口徑／領域邊界——與技術無關，讀者是業務與分析師 |
| `physical_design.md` | **落地方案**：表／型別／key／ENGINE／分區／血緣——全是技術決定、逐表附理由，讀者是工程師 |
| `design.sql`＋`<名>.design/*.ddl` | 草稿 DDL（全量＋積木逐表拆檔） |
| `design.relations.yaml` | relations 草稿（定稿直接沿用） |
| `design_answers.yaml` | 設計問答（迭代驗證迴圈） |
| `etl.yaml` | **ETL pipeline 建議檔**：未來系統內 ETL 需要的設定（詳見下節）。與其他產物零關聯的獨立建議值 |

design 流程與治理同一套「零 LLM ＋ agent 補語意」架構：`run.py` 依
context.md ＋ config 參考素材（erd 參考模型／表用途／naming 詞彙／
flows E2E 流程／ssot 權威登錄）＋閘門規則清單（設計約束）產
`reports/<名>.design_prompt.md`——素材採**索引制**（預設）：prompt 只給
目錄（路徑＋摘要＋L/P 階段＋必讀標記），agent 按需開檔，context 最小化；
`DATAVAL_DESIGN_PROMPT=full` 可回退全文模式。索引摘要可在素材檔
front-matter 用三個選填欄位維護（`index_summary`／`index_stage`／
`index_required`，不填用 🤖 自動摘要），curation 狀態見每次 run 產出的
`reports/design_index_review.md` 審閱表 → agent 依 prompt 與
`config/_engine/design_result.schema.json` 產出 `<名>.design_result.json` →
重跑 `run.py <名>` 確定性渲染設計文件並對草稿 DDL 做閘門預檢。
設計迭代走**問答迴圈**（與治理迭代同一套驗證哲學）：agent 的每題設計
提問附代填答案，自動寫進 `input/<名>/design_answers.yaml` 標
`status: proposed`（待驗證）；你驗證（改 answered，答案可修改；不追改
deferred）後重跑，已答條目自動帶入下一輪設計 prompt（已澄清、勿重問、
依答案修設計）→ 設計演進、輪次 +1。重要決定建議一併回寫 `context.md`。

設計定稿後由**使用者**把 `design.sql` 存成 `input/<名>/<名>.sql`
（＋補 `relations.yaml`，可直接沿用 relations 草稿），subject 自動切換為
govern mode——設計輪次與治理迭代是兩條獨立的演進軸。
**streamline**：進 govern 後，「建議 DDL 對比」自動以**設計最終輪**為基準
（設計是治理的上游——input 與設計稿的落差逐欄呈現）；
參考模型組建僅在沒有設計歷史的 subject 使用。

#### 🔧 ETL pipeline 建議檔（`reports/<名>.etl.yaml`）

design mode 順手產出的一份**建議檔**，給未來系統內的 ETL 用：

| 欄位 | 內容 |
|---|---|
| `id` | ETL pipeline 識別碼（沒給時工具推導 `etl_<主體>`，標 🤖 請確認） |
| `product_suite` · `namespace` | 這個 data subject 屬於哪個產品線、放哪個命名空間 |
| `source_db` · `target_db` · `platform` | 來源 DB、目標 DB、用在哪個 database（ex: clickhouse） |
| `write_mode` | 更新方式：`insert`／`deleteInsert`／`upsert`／`replace`／`append` |
| `schedule` · `resources.cpu` · `resources.memory` | 更新頻率與資源配置 |
| `owner` | 對應負責人／團隊 |
| `tables[]` | **一張表一個 ETL job**：表名＋逐表覆寫（沒覆寫就展開 pipeline 層預設，每個 job 自足可讀） |

三件事讓它好用：

- **零關聯**：不進閘門、不影響任何合規判定、不被其他產物消費——純建議值，
  拿去改壞了也不會動到設計或治理結果。
- **沒資訊也長殼**：agent 只填 `context.md`／素材裡真的講了的欄位；其餘欄位
  仍留在檔案裡（值留空＋註解標 `⬅ TODO 待填`），直接就是可改的骨架。
- **缺的欄位進問答區**：工具確定性把缺口轉成設計提問（附建議答案）寫進
  `input/<名>/design_answers.yaml`（`status: proposed`）——你在那裡填、驗證
  （proposed → answered），下一輪設計自動補進 etl.yaml。

填寫狀態同時呈現在設計 HTML 報告與 `physical_design.md`（已填幾／缺哪些）。

**config 知識庫總索引**：`python config_index.py` → 產生
`docs/素材索引.generated.md`——一份 md 看清整個 config（各域素材清單、
ER 關係、SSOT 權威對照、所有標記的意義）。新增或修改 config 文件後
隨時重跑（內容確定性，沒變不改寫）。

`run.py` 是唯一日常入口，零參數自動掃 `input/`：

1. **前置檢核**（存在 → 可解析 → 一致，三層）：三件必備不齊的 DDL 直接跳過、
   印出缺件檢核表、留檔 `reports/<名>.precheck.md`，並以 **exit code 2** 結束。
   樣本缺漏或有問題不擋，只降為警告並略過該表。
2. 檢核通過 → 跑閘門區全部確定性規則 → 產出三式報告到 `reports/`：
   `<名>.report.md`（人讀）、`.report.json`（程式讀）、`.report.html`（單檔互動，雙擊即開）。
   同時另存 `<名>.round_<N>.report.*`——檔名標明第幾輪迭代，每輪各留一份；
   `<名>.report.*` 永遠是最新輪的固定入口。有建議 DDL 的 subject，
   **建議 Join SQL 與未來寬表 DDL 也隨報告拆檔產出**：
   `<名>.round_<N>.join.sql`、`<名>.round_<N>.future.ddl`（可直接使用）。
3. 未接 LLM 時另產 `<名>.advisory_prompt.md`，供 agent 補完顧問區（見下文）。

**Exit code**：`0` 全部合規 · `1`（`--strict`）存在不合規 · `2` 有輸入不齊全的 subject。

---

## 架構：一條主流程

```text
input/（三件必備＋樣本選填）
  → 前置檢核（precheck.py：存在／可解析／一致，必備缺件即止；樣本缺漏只警告）
  → parser.py（sqlglot，ClickHouse 優先、方言可換）
  → 規則 compile（.md → build/compiled_rules.json，有變更才重建）
  → 閘門區：compiled 規則（.md 卡控動詞）＋ config/Common/knowhow_py/*.py（程式式）
            ＋ business key／production 基準／lineage／全域關聯圖／SSOT 推斷
  → 顧問區：check-llm 語意規則＋概念層（concept.py，主體性提問）
  → _enforce_zone（第二道保險：LLM 產出強制降為 info）
  → reports/（md / json / html ＋ subject_summary ＋ precheck）
```

閘門區的保證由測試守護（見「測試」）：**同一輸入＋同一規則集，checking rule ID 結果必須一致；
LLM 存在與否不得改變閘門判定。**

---

## 輸入各件的角色

| 件 | 必備？ | 誰提供 | 被誰消費 |
|---|---|---|---|
| `<名>.sql` DDL | 必備 | 資料設計者 | 全部規則 |
| `samples/*.csv` | **選填** | 資料設計者 | 型別對樣本、join key 編碼一致、**relations 基數實檢**（缺樣本時這些檢查略過） |
| `relations.yaml` | 必備 | 資料設計者 | 轉為 declared lineage（表／欄位存在、型別相容、循環 → 會擋）；基數對樣本矛盾 → `RELATION.CARDINALITY_SAMPLE` 會擋（缺樣本時不觸發）；晉升後成為全域圖的邊 |
| `context.md` | 必備 | 資料設計者＋領域負責人 | front-matter（subject／domains／business_keys）進引擎；「粒度」等段落餵顧問區與概念層 |

---

## 規則系統

### 規則只有一個家

第一層目錄即領域（`Common` 永遠載入，其餘按 case 的 `domains` 指定）：

| 位置 | 內容 |
|---|---|
| `config/<域>/knowhow/gating/*.md` | 會擋／警告的確定性規則，一條一檔。`Common/` 為跨域基線（結構 5、命名 7、最佳實踐 4、SSOT 1），`PLM/` 等領域按需載入 |
| `config/<域>/knowhow/advisory/*.md` | 語意規則（`` ```check-llm ``，只提示） |
| `config/Common/knowhow_py/*.py` | 程式式規則（跨表／需樣本的複雜邏輯，6 條） |
| `config/<域>/naming/*.md` | 詞彙字典（禁用詞／別名／白名單，Markdown 表格；任意檔名、多檔合併；按域合併，Common 為基底；舊式 glossary.yaml 相容） |
| `config/<域>/ssot/` | SSOT registry（按域合併，Common 為基底） |
| `config/<域>/erd/*.md` | 領域參考 ER 模型（Markdown ＋ ```mermaid；舊式 .mmd 相容） |
| `config/<域>/erd/tables/*.md` | 參考表用途描述（檔名＝表名；input 新表對照 reference 驗證） |
| `config/<域>/flows/*.md` | E2E 流程（Markdown ＋ ```mermaid flowchart；舊式 .flow.yaml 相容） |
| `config/<域>/cases/<名>.yaml` | per-DDL 個案補充設定（選配；四件輸入為權威來源） |
| `config/_engine/default.yaml` | SSOT registry 與 DataHub 設定（不放規則） |
| `build/compiled_rules.json` | 規則的**執行格式**（自動生成，勿手改） |

新增規則：`python rules.py new <域> <gating|advisory> <rule_id>`，
格式與允許的卡控動詞以 `SKILL_AUTHORING.md` 為準。新增 domain 只需建資料夾放 `.md`，自動遞迴掃描。

### 規則起草（drafts/）— LLM 幫你寫規則，不是 LLM 執行檢查

```bash
python rules.py draft <域> <gating|advisory> <rule_id> "<自然語言需求>"
python rules.py adopt <rule_id>     # 人審後採用；lint 通過才進 knowhow
```

未接 LLM 時產出 `drafts/<id>.prompt.md` 交 agent 生成草稿。全程留紀錄：
`drafts/LOG.md`＋`<id>.draft.yaml` 記「怎麼來的」（需求、來源、狀態、去向），
adopt 生效後 `rules_history/` 記「何時生效、內容為何」，以 rule_id 互相對照。
**邊界不變：LLM 只出現在撰寫時；進了 knowhow 的執行永遠確定性。**

### 規則版控（rules_history/）

`run.py` 每次啟動自動 compile；規則集有變時自動在 `rules_history/` 記一筆：
`CHANGELOG.md`（人讀摘要，最新在上）＋ `<時間>_<版本碼>.json`（自足快照，含逐條差異與完整清單）。
差異分三類：➕ 新增 · ➖ 移除 · ✏️ 修改（欄位級 from→to，例如 enforcement 從 warning 改 blocking）；
純搬檔不算規則變更。版本碼與晉升記錄、健檢的規則版本碼**同源**，drift 發生時可回這裡查「差在哪幾條」。

---

## 正式區（production/）

存放**已核准的 data subject**，一 subject 一資料夾：

```text
production/
  <DOMAIN>/
    <subject>/
      <subject>.sql              已核准 DDL
      <subject>.relations.yaml   關聯宣告（全域 lineage 圖的邊）
      <subject>.context.md       語意描述（粒度宣告留檔）
      _promotion.yaml            晉升記錄（日期、卡控結果碼、驗證 bundle、四件輸入 hash）
```

樣本**不進**正式區（驗證證據非正式資產）；晉升記錄存各 CSV 的 SHA256 供追溯。
舊式平鋪 `production/<域>/*.sql` 仍相容載入，健檢會提醒遷移。

### 晉升：promote.py

```bash
.venv/bin/python run.py                     # 先驗證
.venv/bin/python promote.py <名>            # 合規才能晉升
.venv/bin/python promote.py <名> --update   # 重新晉升（保留前版記錄）
```

晉升前提是最新報告 `summary.compliant == true`，且四件輸入與驗證 bundle
必須和產報告當下完全相同；任何內容或規則在報告後變更都會被拒絕。晉升記錄的兩碼提供因果保證：

- **卡控結果碼** = 閘門區 findings（rule｜status｜severity｜target）排序後的 SHA256
- **驗證 bundle／規則版本碼** = `build/compiled_rules.json` 的 SHA256；內容涵蓋
  宣告式規則、Python 規則原始碼、內建 validator 與 parser 依賴版本

### 正式區給新 subject 的檢查

新 subject 驗證時，除既有的命名基準比對（`PRODUCTION.NAMING_CONSISTENCY`）
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

不是驗新 subject，而是掃整個正式區：三件齊全、DDL 可解析、斷鏈（關聯指向的上游表不存在）、
全域循環、基數矛盾，以及**規則版本碼 drift**——晉升時規則版本 ≠ 現行版本的 subject 會被標記
「建議重驗」。輸出 `reports/production_audit.md`；有 fail 時 exit code 1。

---

## Lineage 能力總覽

- **宣告面（單 subject）**：`relations.yaml` → declared lineage。本地端點驗存在；
  跨 domain 端點（`DOMAIN.table.col`）對 `production/<DOMAIN>/` 實檢表存在、欄位存在、
  型別相容；local 循環與 domain scope 會擋。
- **實檢面**：宣告 `N:1`／`1:1` 但「1 的一方」樣本出現重複鍵 → 會擋。
- **全域面（跨 subject）**：正式區所有 relations 合併成 DAG——循環、基數矛盾會擋；
  影響分析列出依賴者；健檢抓斷鏈。
- **建議面**：未宣告時，以 business key／共用 `*_id`／Mermaid ER diagram
  產生保守的候選關係，只提示不擋。

---

## 報告與顧問區

三式報告皆分兩區呈現，合規判定只由閘門區決定。HTML 為單檔互動
（判定卡片、搜尋、fail/warning 篩選、摺疊分類）。

### Agent 補完顧問區

`run.py` 是獨立 subprocess，**不繼承 agent 的 LLM**——這是刻意的隔離邊界，
確保閘門區在 agent session 內也零 LLM。未設 `DATAVAL_LLM_BASE_URL` 時：

1. `run.py` 產出 `reports/<名>.advisory_prompt.md`
2. agent（opencode 讀 `AGENTS.md`；Claude Code 讀 `CLAUDE.md`）用自身 LLM 產出 `<名>.advisory_result.json`
3. `python merge_advisory.py` 合併並重繪三式報告
4. `python merge_advisory.py --status` → exit 0 = 顧問區全數補完

合併程式與 `run.py` 共用同一套四件輸入載入流程，並逐項比較合併前後的
gating findings，不一致就**拒絕寫入**。`--status` 在任一報告仍待補時回傳非零。
直連 LLM 可設 `DATAVAL_LLM_BASE_URL / DATAVAL_LLM_MODEL / DATAVAL_LLM_API_KEY`。

### 迭代問答收斂（answers.yaml）

顧問區的提問會由 agent **預先代填答案**，你只做驗證，逐輪收斂：

```text
① run.py                    產報告與 advisory_prompt（零 LLM，不代填）
② agent 補顧問區            advisory_result.json 每題提問附 proposed_answer
③ merge_advisory.py         把代填答案自動寫進 input/<名>/answers.yaml
                            （status: proposed 待驗證），console 印
                            「待答 X、待驗證 Y（本次代填 Z）→ 是否收斂」
④ 你驗證                    到 input/<名>/answers.yaml：答案沒問題把
                            proposed 改 answered（可修改答案）；不追的改 deferred
⑤ 說「繼續」→ 回到 ①       agent 把 iteration +1 重跑；已答主題不再重問
```

- **收斂條件**：無待答＋無待驗證＋閘門合規；上限 **5 輪**。
  狀態見報告「迭代收斂」區塊與 `report.json` 的 `iteration` 鍵。
- **待驗證不算已答**：`proposed` 擋收斂、不餵下一輪 prompt——
  agent 的猜測未經你確認前不會迴聲放大；只有 `answered` 計入。
- **代填只新增**未覆蓋的主題、永不覆寫你既有條目；`structural` 答案
  仍須由你手動修改權威輸入。answers.yaml 格式見 `input/README.md`。
- ②③ 沒跑完就不會有代填——`answers.yaml` 是 ③ 產生的，不是 run.py。
- **迭代問答以 agent 路徑為準**：直連 LLM（`DATAVAL_LLM_BASE_URL`）能填
  顧問區建議，但不會產生代填答案（proposed）——完整迴圈請走
  opencode／Claude Code 路徑。
- 晉升時迭代狀態會寫進 `_promotion.yaml`；`promote.py --require-converged`
  可要求「收斂才可晉升」；晉升成功後自動精簡該 subject 的迭代歷史
  （保留 HISTORY.md 與最終輪）。
- **迭代歷史**：每輪自動存檔到 `iterations/<名>/`——
  `round_<N>.json`（輸入全文＋findings＋回答狀態快照）、
  `round_<N>.report.md`（該輪完整報告存檔，檔名與內容都標明輪次）、
  `round_<N>.delta.md`（**變更報告：只列有改動的地方**——相對前一輪
  新增／解決／狀態變化的發現與 input 變更）；有建議 DDL 的 subject 另存
  `round_<N>.proposal.md` 與拆檔 `round_<N>.join.sql`／`round_<N>.future.ddl`。
  人讀摘要見 `HISTORY.md`。
  報告「迭代收斂」區塊帶變更摘要；**收斂那一輪**另附
  「初版 ↔ 終版 input 差異」diff。
- **建議 DDL 對比**：依 context 宣告的域，從參考模型
  （`config/<域>/erd` 的 entity 欄位＋關係＋表用途）自動組建
  **建議 Join SQL 與未來寬表 DDL**，與 input DDL 逐欄對比
  （input 落點／未包含欄位／input 獨有欄位）。純建議值（顧問區），
  每輪隨 input 演進重組並存檔 `iterations/<名>/round_<N>.proposal.md`，
  並拆檔為可直接使用的 `round_<N>.join.sql`（建議 Join SQL）與
  `round_<N>.future.ddl`（未來 DDL），檔名與檔頭都標明輪次；
  同名拆檔也隨報告產出到 `reports/<名>.round_<N>.join.sql`／`.future.ddl`。
  參考模型 entity 沒定義欄位時會以 TODO 佔位提示補齊。

---

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
| `domains_layout_test.py` | C1 領域佈局、C2 規則載入、C3 詞彙合併、C4 流程載入 |
| `etl_manifest_test.py` | E1 沒資訊也長殼、E2 缺口轉設計提問、E3 值的優先序與逐表覆寫、E4 驗證、E5 產物落地與確定性、E6 純建議不碰設計結果 |
| `drafting_test.py` · `rules_history_test.py` | 起草流程與規則版控 |

只有刻意改變結果時才使用 `tests/golden_test.py --update`。

---

## 環境變數

| 變數 | 用途 |
|---|---|
| `DATAVAL_INPUT_DIR` / `DATAVAL_REPORT_DIR` / `DATAVAL_PRODUCTION_DIR` | 覆寫三個資料夾位置 |
| `DATAVAL_PRECHECK=legacy` | 回到舊的 `config/cases` 集中式輸入（內部 fixtures 用，不建議新案） |
| `DATAVAL_STRICT=1` | 等同 `--strict` |
| `DATAVAL_CONFIG_CHECK=1` | 啟用 run.py 啟動時的 config 格式檢查（預設停用；隨時可手動跑 `python config_check.py`） |
| `DATAVAL_LLM_BASE_URL` 等 | 直連 LLM（見「Agent 補完顧問區」） |

---

## 檔案地圖

```text
run.py                  日常入口（前置檢核 → 驗證 → 三式報告）
promote.py              晉升合規 subject 到正式區（附雙碼晉升記錄）
production_audit.py     正式區全區健檢
merge_advisory.py       顧問區補完合併（--status 為完成閘門）
rules.py                規則管理 CLI（list / new / lint / compile / docs / draft / adopt）
dataval/
  engine.py             主流程與 _enforce_zone
  precheck.py           輸入前置檢核（四件套三層檢核）
  prodgraph.py          正式區全域關聯圖（循環／矛盾／影響／健檢）
  parser.py / model.py  DDL 解析與資料模型
  compiler.py           .md → compiled JSON
  drafting.py           規則起草流程（draft / adopt）
  rules_history.py      規則版控（compile 時自動記錄）
  lineage.py / production.py / subject_inference.py / concept.py
  er_diagram.py / flows.py
  design.py / design_report.py   設計模式（prompt／驗證／渲染／HTML 報告）
  etl_manifest.py       ETL pipeline 建議檔（沒資訊長殼＋缺口轉設計提問）
  answers.py            迭代問答（answers.yaml 載入／代填合併／收斂計算）
  report.py / advisory_export.py / subject_summary.py / llm.py
input/                  輸入契約（見 input/README.md）
config/                 第一層即領域：Common / BLM / SCM / PLM / FCM / CRM
  <域>/knowhow/         規則（gating／advisory .md；Common 另有 knowhow_py）
  <域>/naming/          詞彙字典（按域合併，Common 為基底）
  <域>/ssot/            SSOT registry（按域合併，Common 為基底）
  <域>/erd/             領域參考 ER 模型（Mermaid）
  <域>/flows/           E2E 流程（YAML）
  <域>/cases/           per-DDL 個案補充
  _engine/              引擎層（default.yaml、templates、schema、er_diagrams、fixtures）
production/             正式區（一 subject 一資料夾）
build/                  compile 產物（自動生成）
reports/                報告輸出
rules_history/          規則版控（自動維護）
drafts/                 規則起草暫存與紀錄
tests/                  守門測試
```

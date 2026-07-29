# Agent 操作規範

這是 ClickHouse DDL 資料治理工具。完整使用方式見 `README.md`；新增規則時再讀
`SKILL_AUTHORING.md`。

## 驗證 DDL 並輸出報告（標準流程）

使用者說「檢查 input／跑檢查／產生報告／輸出報告」等，都是要一份**完整報告**。
一份完整報告 = 閘門區 ＋ **已補完的顧問區**。請完整跑完以下三步，缺一不可：

```bash
.venv/bin/python run.py            # ① 閘門區＋產出報告骨架與 advisory_prompt
# ② run.py 若在結尾印出「⚠️ 顧問區尚未補完」，你（agent）必須用自身 LLM，
#    對每個列出的主題讀 reports/<名>.advisory_prompt.md，依其格式與 schema
#    產出 reports/<名>.advisory_result.json（顧問建議一律 info、繁中、提問語氣）
.venv/bin/python merge_advisory.py           # ③ 把建議合回三式報告＋HTML
.venv/bin/python merge_advisory.py --status  # 驗收：exit 0 = 顧問區全數補完
```

**沒有做完 ②③ 就把報告交給使用者 = 交付不完整的報告**（HTML 顧問區只會顯示
「待補完」、report 顯示未接 LLM）。除非本機設了 `DATAVAL_LLM_BASE_URL`
讓 `run.py` 直接填顧問區（此時 run.py 不會印待補提示，跳過 ②③ 即可）。
詳細補完格式見下方「補完顧問區」。

新 DDL 使用一 subject 一資料夾：三件必備 `input/<名稱>/<名稱>.sql`、
`relations.yaml`、`context.md`，外加選填的 `samples/<表>.csv`（缺樣本仍會產報告，
只是樣本相關檢查略過）。`context.md` 的 front-matter
是 domains 與 business_keys 的權威來源；`relations.yaml` 是明確 lineage 宣告。
`config/<域>/cases/<名稱>.yaml` 只保留相容模式與內部 fixture 的補充資料。

Mermaid ER 參考模型放在 `config/<域>/erd/*.md`（```mermaid fence；舊式 .mmd
相容）；參考表用途放 `config/<域>/erd/tables/<表名>.md`——input 新表對得上
參考表時，報告出 `ERD.TABLE_PURPOSE`，顧問區並判讀是否正確 reference。
E2E 流程放 `config/<域>/flows/*.md`（```mermaid flowchart）；詞彙字典放
`config/<域>/naming/*.md`（Markdown 表格，任意檔名、多檔合併）。個案圖可放
`config/<域>/cases/<名稱>.mmd`。ER 關係只能轉成 lineage 顧問候選；沒有
`relations.yaml` 明確宣告時，不得把 ER association 說成已確認的資料流向。

`Common` 永遠載入；其他 domain 只由 `context.md` 的 `domains` 指定。不得把 ClickHouse
`ORDER BY` 或 `PRIMARY KEY` 當成 Business Key。外部 lineage 來源必須存在於已選
domain 的 `production/`；沒有 YAML 時只能把推測稱為建議，不能說成已確認血緣。

## Config 格式檢查（選用，預設停用）

檢查 config/ 知識輸入的格式（erd／erd/tables／flows／naming／ssot 是否
符合各資料夾 README 的 template）。**目前預設停用**——啟用方式：
環境變數 `DATAVAL_CONFIG_CHECK=1`（或改 run.py 內的預設值）。
不論開關，隨時可單獨執行：

```bash
.venv/bin/python config_check.py           # exit 0 = 全過；1 = 有格式問題
.venv/bin/python config_check.py --reset   # 清快取全量重驗（極少需要）
```

**有快取、不用重新跑**：結果與檔案 SHA256 存 `build/config_check.json`，
內容沒變的檔案下次直接沿用結果——agent 不需要每輪自己重讀 config 驗格式，
看 run.py 開頭那一行摘要即可。

Agent 的義務：檢查列出 ❌ 時，**依該資料夾 README 的 template 修正該檔**
（只修格式與結構，不得更動語意內容——詞條、關係、用途描述的實質內容
要動須經使用者同意），修完重跑 `config_check.py` 確認轉綠。不得忽略 ❌
繼續交付報告。

## 補完顧問區

這是「輸出報告」的必要環節，不是選配。`run.py` 是零 LLM 的閘門區行程，語意
建議（check-llm 規則、命名語意、主體性概念）需要 agent 用**自身 LLM** 補上。
`run.py` 結尾若印出待補主題清單，代表顧問區還沒填。Agent 應：

1. 對每個待補主題讀取 `reports/<名稱>.advisory_prompt.md`。
2. 依其中格式與 `config/_engine/advisory_result.schema.json`，用自身 LLM 產生
   `reports/<名稱>.advisory_result.json`（繁體中文、對設計者的提問語氣、不下結論）。
   **每題建議都要附 `proposed_answer` 代填答案**（見下方「迭代問答迴圈」），
   否則 merge 後 `input/<名>/answers.yaml` 不會有待驗證條目。
3. 執行 `.venv/bin/python merge_advisory.py`（會把建議合回 md／json／html）。
4. 執行 `.venv/bin/python merge_advisory.py --status` 驗收（exit 0 = 全數補完）；
   確認 `.report.html` 顧問區顯示真實建議，閘門結果不變。

顧問建議一律是 `info`，永遠不能改變合規判定。合併程式會逐項比較合併前後的
gating findings，不一致就拒絕寫入。若本機設了 `DATAVAL_LLM_BASE_URL`，`run.py`
會在單次執行直接填顧問區，這時不需要上面的手動補完。

## 迭代問答迴圈（answers.yaml）

顧問區的提問可由使用者回答後重跑，逐輪收斂（收斂＝**無待答＋無待驗證＋
閘門合規**；上限 **5 輪**）。狀態見報告「迭代收斂」區塊與 `report.json` 的 `iteration` 鍵。
Agent 在每輪的義務：

1. **提問時一併代填答案**：advisory_result.json 的每題建議都要附
   `proposed_answer`（繁中、依 context 與 schema 推測）與 `proposed_kind`
   （semantic｜structural；structural 一併填 `proposed_applied_to`）。
   `merge_advisory.py` 會把代填答案寫進 `input/<名>/answers.yaml`
   標 `status: proposed`（待驗證）。
2. **待驗證不算已答**：proposed 不餵下一輪 prompt、擋收斂。
   使用者驗證＝把 `proposed` 改成 `answered`（答案可修改）或 `deferred`。
   **agent 不得自行把 proposed 改成 answered**——只有使用者本人動手、
   或使用者在對話中明確指示（如「第 1、3 題 OK」）時代改。
3. **每輪必須回報使用者**：第幾輪／待答幾題／**待驗證幾題**／已解幾題／
   閘門 fail 幾項／是否收斂，並提醒到 `input/<名>/answers.yaml` 驗證。
   達 5 輪上限仍未收斂 → 明確提醒「建議收斂範圍或人工決策」。
4. `kind: structural` 的答案必須由使用者手動修改權威輸入（.sql／
   relations.yaml／context.md）後才能改 answered，agent 不得代改權威輸入。
5. 使用者說繼續時：把 `answers.yaml` 的 `iteration` +1 後重跑整套標準流程
   （run.py → 補顧問區 → merge_advisory.py）。已答主題不得再以任何措辭重問。

**硬邊界不變**：answers.yaml 只餵顧問區 prompt 與報告呈現，永不進閘門執行路徑。

## 新增規則

```bash
.venv/bin/python rules.py new <rule_id>
.venv/bin/python rules.py check
.venv/bin/python run.py
```

指定 domain／區域時使用：

```bash
.venv/bin/python rules.py new <domain> <gating|advisory> <rule_id>
```

規則格式、允許的 checking verbs 與檢查清單以 `SKILL_AUTHORING.md` 為準。

### 由 LLM 起草規則（drafts/ 流程）

使用者以自然語言描述規則需求時，走起草流程而非直接寫進 knowhow：

```bash
.venv/bin/python rules.py draft <域> <gating|advisory> <rule_id> "<需求描述>"
```

未接本地 LLM 時會產出 `drafts/<rule_id>.prompt.md`；agent 依該檔的 system
指引產出 `drafts/<rule_id>.md`（只含規則內容本身）。**必須提示使用者人工
審閱草稿**，確認後執行：

```bash
.venv/bin/python rules.py adopt <rule_id>
```

adopt 會先 lint，通過才搬進 `config/<域>/knowhow/`；草稿標記
`NEEDS_PY` 表示超出宣告式能力，須改寫成 knowhow_py 程式式規則。
全程紀錄：`drafts/LOG.md`（怎麼來的）＋ `rules_history/`（何時生效）。
agent 不得跳過 draft/adopt 直接把 LLM 生成的規則寫入 knowhow。

## 不可破壞的保證

1. 閘門只用確定性規則；LLM 只能進顧問區。
2. 同一 DDL＋規則集，checking rule ID 結果必須一致。
3. DDL 個案補充設定放 `config/<域>/cases/`；Domain 知識放 `config/<域>/`
   （knowhow／naming／ssot／erd／flows）；Python 規則放
   `config/Common/knowhow_py/`；Mermaid ER diagram 放 `config/<域>/erd/`。引擎只提供機制。
4. `run.py` 是唯一日常入口；預設掃 `input/`，可用 `DATAVAL_INPUT_DIR` 切換範例。
   每個 data subject 需要**三件必備輸入**（`<名>.sql`、`relations.yaml`、
   `context.md`），一 subject 一資料夾（`input/<名>/`，格式見 `input/README.md`）。
   **樣本 `samples/<表>.csv` 是選填**——沒有樣本仍會產生報告，只是樣本相關檢查
   （型別對樣本、join key 編碼、基數實檢）略過。
   `run.py` 先做前置檢核，缺**必備件**的 DDL **不會產生報告**並以 exit code 2 結束；
   此時 agent 必須把 `reports/<名>.precheck.md` 的缺件明細轉告使用者、
   請使用者補齊後重跑，**不可**自行代填語意描述或關聯。樣本缺漏只是警告，不需補齊。
5. 改動後執行 checking verbs、architecture、golden 三組測試；只有刻意改變結果時才
   使用 `tests/golden_test.py --update`。

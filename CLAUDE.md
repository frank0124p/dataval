# CLAUDE.md — 給 Claude Code 的操作指南

這個專案是**本地資料設計驗證工具**（ClickHouse DDL → 合規報告）。
本檔是 Claude Code 的入口；opencode 的對應檔是 `AGENTS.md`（內容需保持同步）。
先讀 `README.md`（含逐檔詳解）與 `SKILL_AUTHORING.md` 了解全貌。

## 日常操作

當使用者要求「驗證 DDL」「產生報告」「跑檢查」時：

```bash
python run.py            # 零參數：掃 input/ 全部 DDL，報告出到 reports/
```

它會先重建結構化規則內容（有變更才寫入 `build/compiled_rules.json`），
再逐檔驗證。使用者貼新 DDL 時，先存成 `input/<適當名稱>.sql` 再跑。
不需詢問參數；LLM 與 DataHub 缺少時自動降級。

其他常用指令：

```bash
python rules.py list                     # 盤點所有規則
python rules.py new <id>                 # 預設新增 Common/gating 規則
python rules.py new <domain> <gating|advisory> <id>   # 指定位置
python rules.py check                    # 一站式 lint＋compile
python tests/golden_test.py              # 三類守門測試（改規則後必跑）
python merge_advisory.py                 # 顧問區補完合併
```

## 顧問區補完（你自己就是 LLM，直接補）

run.py 是獨立子程序、沒有 LLM 連線。未接本地 LLM 時它**不會產生 HTML**
（只有 .md/.json 與 `reports/<名>.advisory_prompt.md`）——HTML 在你補完並合併後
才產生，使用者看到的 HTML 永遠是兩區皆有真實內容的完成版。**你不需要外接任何 LLM**：

1. 讀 `reports/<名>.advisory_prompt.md`（schema、情境、待補語意 skill 清單）。
2. 依它的三個面向（命名語意／主體性概念／各 domain 語意 skill）**自行推理**產生建議，
   措辭一律「給設計者思考的提問」，不下結論。
3. 寫成 `reports/<名>.advisory_result.json`（格式見 prompt 檔）。
4. 跑 `python merge_advisory.py` —— 此步驟才會產生 `.report.html`，顧問區為你的真實建議。**在此之前不要把 HTML 呈現給使用者。**

顧問區永不影響合規判定；補完前後每條 checking rule ID 的閘門結果不變。

## 呈現結果

把 `reports/<名>.report.md` 摘要給使用者：先講**合規判定**與**被哪些規則卡下來**
（每條違規含期望 vs 實際與修法）。想分享團隊時指向 `.report.html`（瀏覽器開啟）。

## domain 選擇

skill 依 domain 分在 `config/skills/<domain>/`。Common 一律載入；其餘由
`input/_domains.yaml` 或 `input/<DDL名>.domains.yaml` 指定（沒有就只載入 Common 並警告）。
`production/<domain>/*.sql` 是已核准 DDL 的唯讀命名基準，只參照明確指定的 domain。
使用者說明了領域歸屬（如「這是 PLM 料件主檔」）就幫他建對應的 `.domains.yaml`。
每份 DDL 也應有 `<名>.keys.yaml` 明確宣告 business key；不得把 ORDER BY
或 ClickHouse PRIMARY KEY 當成業務唯一性。
已知來源關係時用 `<名>.lineage.yaml` 宣告 target、upstream 與
`domain.table.column` 欄位映射；外部來源必須已選 domain 且存在於 production。
沒有 YAML 時，Business Key／共用 `*_id` 產生的 lineage 只能稱為顧問區候選；
確實沒有上游則以 `upstream: []` 明確宣告。

## 產生新的 skill

使用者要「新增一條 skill／把 know-how 變成檢查」時，讀 `SKILL_AUTHORING.md` 照規格產出：
判斷 gating（```check，會擋）或 advisory（```check-llm，只提示）；```check 只能用
第 3 節清單的卡控動詞；用 `rules.py new <id>` 建骨架（需要時指定 domain/zone）；
跑 `rules.py check` 與 `run.py` 確認；
回報這條會擋還是只提示。

## 改程式碼時：不可破壞的架構保證

1. **兩區分離**：閘門（確定性、會擋）／顧問（LLM、只提示）。LLM 輸出永不影響判定。
2. **閘門一致性**：同一 DDL＋規則集 ⇒ 每條 checking rule ID 的結果不變，
   與 LLM、次數、merge 前後無關。報告直接列出通過、警告與擋下的 rule ID。
3. **無人可跑**：不接 LLM、不接 DataHub 也能產出完整合規判定。
4. **規則只有一個家**：確定性規則在 `config/skills/`（一條一檔）、複雜規則在
   `config/skills_py/`；Python 引擎不藏規則。閘門路徑零 LLM。
5. **skill 格式與補完往返不變**：.md 規範文件格式、advisory_prompt → result → merge。
6. **run.py 零參數流程不破壞**。

改動後必跑 `python tests/golden_test.py`；行為刻意演化才用 `--update` 重建基準，
並讓基準 DDL 覆蓋新規則（黃金測試只守基準有踩到的規則）。pyflakes 保持乾淨。

## 快速地圖與待辦

- 引擎／兩區／rule ID 結果：`dataval/engine.py`；卡控動詞：`dataval/skills/markdown_skill.py`
  （`_parse_check` 加語法、`_eval` 加判斷）；報告：`dataval/report.py`；
  compile：`dataval/compiler.py`；正式基準：`production.py`；lineage：`lineage.py`；
  推斷：`subject_inference.py`。
- 待辦：每條 gating 動詞補「該擋／不該擋」最小 DDL 測例；DataHub/runtime lineage
  與設計 lineage 交叉驗證；實踐畢業流程（LLM 發現→人工確認→沉澱成規則）自動化。

執行環境：Python 3.10–3.12，依賴見 `pyproject.toml`。DataHub 目前 bypass。

# AGENTS.md — 給 opencode agent 的指示

（Claude Code 的對應檔是 `CLAUDE.md`；兩檔操作內容需保持同步。）

這個專案是資料設計驗證工具。當使用者要求「驗證 DDL」「產生報告」「跑檢查」
或類似意圖時，執行以下單一指令（不需參數）：

    python run.py

它會掃 input/ 裡的 .sql / .ddl、載入 skill 規則，把報告寫到 reports/
（每個 DDL 對應 <名稱>.report.md、.report.json 與 .report.html）。

## 重要：顧問區補完（你來當 LLM 橋樑）

run.py 是獨立子程序，不會繼承你的 LLM 連線。未接本地 LLM 時它**不會產生 HTML**
（只有 .md/.json 與 reports/<名>.advisory_prompt.md）——HTML 在你補完建議並合併後
才產生，因此使用者看到的 HTML 永遠是兩區皆有真實內容的完成版。

請你（你本來就連得到 LLM）完成補完：
1. 讀 reports/<名>.advisory_prompt.md（含 schema、情境、待補的語意 skill 清單）。
2. 用你的 LLM 依它的三個面向（命名語意／主體性概念／各 domain 語意 skill）產生建議。
3. 把結果寫成 reports/<名>.advisory_result.json（格式見 advisory_prompt.md）。
4. 跑 `python merge_advisory.py` —— 此步驟才會產生 .report.html，顧問區為你的真實建議、標「✅ 已由 agent 補完」。**在此之前不要把 HTML 呈現給使用者。**

注意：顧問區一律只提示、永不改變合規判定。補完前後，
每條 checking rule ID 的閘門結果必須完全相同——你的建議不會、也不能影響「合規/不合規」。

## 呈現

完成後把 reports/<名稱>.report.md（含你補完的顧問區）呈現給使用者；
若使用者想分享或方便團隊查看，指向 reports/<名稱>.report.html（可在瀏覽器開啟、支援篩選與搜尋）。
重點摘要「合規判定」與「會擋的項目」。

若使用者貼了新的 DDL，先存成 input/<適當名稱>.sql 再執行 python run.py。
不需要詢問參數；LLM 與 DataHub 缺少時都會自動降級。

## domain 選擇

skill 依 domain 分在 config/skills/<domain>/。Common 一律載入；其餘 domain 由
input/_domains.yaml 或 input/<DDL名>.domains.yaml 指定（沒有就只載入 Common 並警告）。
production/<domain>/*.sql 是已核准 DDL 的唯讀命名基準；只有明確指定的 domain 會被參照。
若使用者描述了這份設計屬於哪些 domain（例如「這是 PLM 的料件主檔」），
可據此建立對應的 .domains.yaml（domains: [PLM]），讓載入更精準。
未知 domain 不得靜默忽略；報告必須列出並略過該 domain。
每份 DDL 以 `<名>.keys.yaml` 明確宣告 business key；ORDER BY/PRIMARY KEY
只是物理與索引語意，不可自動當成 business key。

## 產生新的 skill

當使用者要「新增一條 skill / 把某條 know-how 變成檢查」時，
請讀專案根目錄的 SKILL_AUTHORING.md，照它的規格產出 skill .md：
- 判斷該用 gating（```check，會擋）或 advisory（```check-llm，只提示）。
- ```check 只能用 SKILL_AUTHORING.md 第 3 節清單裡的卡控動詞。
- 用 templates/ 下的空白範本當骨架。
- 一般共用閘門直接用 `python rules.py new <id>`；指定位置才用
  `python rules.py new <domain> <zone> <id>`。
- 填完後跑 `python rules.py check` 與 `python run.py`。
- 回報這條 skill 會擋還是只提示、屬於哪一區。

## 其他常用指令

```
python rules.py list          # 盤點所有規則
python rules.py check         # 新增後的一站式 lint＋compile
python tests/golden_test.py   # 三類守門測試（改規則後必跑）
```

改動規則屬刻意演化時，跑 `python tests/golden_test.py --update` 重建基準。
